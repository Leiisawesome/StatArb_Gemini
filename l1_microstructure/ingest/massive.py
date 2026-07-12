"""Official Massive ingest sources."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
import heapq
import json
import os
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

from dotenv import dotenv_values

from l1_microstructure.events import MarketEvent, QuoteEvent, TradeEvent, event_sort_key

from ._massive_support import _EASTERN, MassiveEventFilterMixin, MassiveFilterConfig
from .interfaces import (
    EventNormalizer,
    HistoricalBatchRequest,
    LiveSubscriptionRequest,
    MarketDataSource,
    SessionFilter,
)

RestClientFactory = Callable[["MassiveRESTConfig"], Any]
WebSocketClientFactory = Callable[["MassiveWebSocketConfig", LiveSubscriptionRequest], Any]


def _normalize_api_key_candidate(candidate: object | None) -> str | None:
    if candidate is None:
        return None
    value = str(candidate).strip()
    if not value:
        return None
    if any(character.isspace() for character in value):
        return None
    if "MASSIVE_API_KEY=" in value:
        return None
    return value


def _resolve_massive_api_key(explicit_api_key: str | None) -> str | None:
    explicit_key = _normalize_api_key_candidate(explicit_api_key)
    if explicit_key:
        return explicit_key

    massive_env_key = _normalize_api_key_candidate(os.environ.get("MASSIVE_API_KEY"))
    if massive_env_key:
        return massive_env_key

    repo_env = Path(__file__).resolve().parents[2] / ".env"
    if repo_env.exists():
        values = dotenv_values(repo_env)
        massive_repo_key = _normalize_api_key_candidate(values.get("MASSIVE_API_KEY"))
        if massive_repo_key:
            return massive_repo_key
    return None


@dataclass(frozen=True, slots=True)
class MassiveRESTConfig:
    api_key: str | None = None
    base_url: str = "https://api.massive.com"
    connect_timeout: float = 10.0
    read_timeout: float = 10.0
    num_pools: int = 10
    retries: int = 3
    pagination: bool = True
    verbose: bool = False
    trace: bool = False


@dataclass(frozen=True, slots=True)
class MassiveWebSocketConfig:
    endpoint: str = "wss://socket.massive.com/stocks"
    api_key: str | None = None
    raw_subscriptions: tuple[str, ...] = ()
    verbose: bool = False
    max_reconnects: int | None = 5
    connect_kwargs: dict[str, object] = field(default_factory=dict)


class MassiveRESTDataSource(MassiveEventFilterMixin, MarketDataSource):
    def __init__(
        self,
        rest_config: MassiveRESTConfig | None = None,
        normalizer: EventNormalizer | None = None,
        session_filter: SessionFilter | None = None,
        filter_config: MassiveFilterConfig | None = None,
        client_factory: RestClientFactory | None = None,
    ):
        self.rest_config = rest_config or MassiveRESTConfig()
        self.client_factory = client_factory or self._default_rest_client_factory
        self._initialize_massive_event_filters(normalizer, session_filter, filter_config)

    def load_historical(self, request: HistoricalBatchRequest) -> Iterable[MarketEvent]:
        self._reset_halt_state()
        timestamp_gte, timestamp_lte = self._historical_time_bounds(request)
        symbols = set(request.symbols)

        def _fetch_symbol(symbol: str) -> list[MarketEvent]:
            # Each worker creates its own client to avoid sharing connection pools
            # across threads.  Filter state is read-only after _reset_halt_state().
            client = self.client_factory(self.rest_config)
            events: list[MarketEvent] = []
            if request.include_quotes:
                for quote in client.list_quotes(
                    symbol,
                    timestamp_gte=timestamp_gte,
                    timestamp_lte=timestamp_lte,
                    sort="timestamp",
                    order="asc",
                    limit=50_000,
                ):
                    event = self._normalize_vendor_payload(self._quote_payload_from_rest(symbol, quote))
                    if event is not None:
                        events.append(event)
            if request.include_trades:
                for trade in client.list_trades(
                    symbol,
                    timestamp_gte=timestamp_gte,
                    timestamp_lte=timestamp_lte,
                    sort="timestamp",
                    order="asc",
                    limit=50_000,
                ):
                    event = self._normalize_vendor_payload(self._trade_payload_from_rest(symbol, trade))
                    if event is not None:
                        events.append(event)
            # Per-symbol events are already nearly sorted (asc from API); finalize sort.
            return sorted(events, key=event_sort_key)

        num_workers = min(len(request.symbols), 8)
        per_symbol: dict[str, list[MarketEvent]] = {}
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(_fetch_symbol, sym): sym for sym in request.symbols}
            for future in as_completed(futures):
                per_symbol[futures[future]] = future.result()

        # heapq.merge lazily merges pre-sorted per-symbol lists — O(N log S) total
        # where S = number of symbols, avoiding full in-memory sort.
        for event in heapq.merge(*per_symbol.values(), key=event_sort_key):
            if event.symbol not in symbols:
                continue
            if not self.session_filter.accepts(event.symbol, event.timestamp_ns):
                continue
            if isinstance(event, QuoteEvent) and not request.include_quotes:
                continue
            if isinstance(event, TradeEvent) and not request.include_trades:
                continue
            event_date = (
                datetime.fromtimestamp(event.timestamp_ns / 1_000_000_000.0, tz=timezone.utc)
                .astimezone(_EASTERN)
                .date()
            )
            if event_date != request.trade_date:
                continue
            yield event

    def subscribe_live(self, request: LiveSubscriptionRequest) -> Iterable[MarketEvent]:
        raise NotImplementedError("MassiveRESTDataSource does not support live subscriptions")

    def _normalize_vendor_payload(self, payload: dict[str, Any]) -> MarketEvent | None:
        if not self._payload_is_eligible(payload):
            return None
        event = self.normalizer.normalize(payload)
        if event is None or not self._event_is_eligible(event):
            return None
        return event

    @staticmethod
    def _quote_payload_from_rest(symbol: str, quote: Any) -> dict[str, Any]:
        return {
            "ev": "Q",
            "sym": symbol,
            "t": getattr(quote, "sip_timestamp", None) or getattr(quote, "participant_timestamp", None),
            "bp": getattr(quote, "bid_price", None),
            "ap": getattr(quote, "ask_price", None),
            "bs": getattr(quote, "bid_size", None),
            "as": getattr(quote, "ask_size", None),
            "bx": getattr(quote, "bid_exchange", None),
            "ax": getattr(quote, "ask_exchange", None),
            "q": getattr(quote, "sequence_number", None),
            "c": getattr(quote, "conditions", None),
            "i": getattr(quote, "indicators", None),
            "trft": getattr(quote, "trf_timestamp", None),
        }

    @staticmethod
    def _trade_payload_from_rest(symbol: str, trade: Any) -> dict[str, Any]:
        return {
            "ev": "T",
            "sym": symbol,
            "t": getattr(trade, "sip_timestamp", None) or getattr(trade, "participant_timestamp", None),
            "p": getattr(trade, "price", None),
            "s": getattr(trade, "size", None),
            "x": getattr(trade, "exchange", None),
            "q": getattr(trade, "sequence_number", None),
            "c": getattr(trade, "conditions", None),
            "i": getattr(trade, "id", None),
            "trfi": getattr(trade, "trf_id", None),
            "trft": getattr(trade, "trf_timestamp", None),
            "correction": getattr(trade, "correction", None),
        }

    @staticmethod
    def _historical_time_bounds(request: HistoricalBatchRequest) -> tuple[int, int]:
        start_dt = datetime.combine(request.trade_date, time.min, tzinfo=_EASTERN)
        start_ns = int(start_dt.astimezone(timezone.utc).timestamp() * 1_000_000_000)
        end_ns = start_ns + int(timedelta(days=1).total_seconds() * 1_000_000_000) - 1
        if request.start_ns is not None:
            start_ns = max(start_ns, int(request.start_ns))
        if request.end_ns is not None:
            end_ns = min(end_ns, int(request.end_ns))
        return start_ns, end_ns

    @staticmethod
    def _default_rest_client_factory(config: MassiveRESTConfig) -> Any:
        try:
            from massive import RESTClient
        except ImportError as exc:
            raise RuntimeError("massive client is required for MassiveRESTDataSource") from exc

        api_key = _resolve_massive_api_key(config.api_key)
        if api_key is None:
            raise RuntimeError("MASSIVE_API_KEY is required for MassiveRESTDataSource")

        return RESTClient(
            api_key=api_key,
            connect_timeout=config.connect_timeout,
            read_timeout=config.read_timeout,
            num_pools=config.num_pools,
            retries=config.retries,
            base=config.base_url,
            pagination=config.pagination,
            verbose=config.verbose,
            trace=config.trace,
        )


class MassiveWebSocketDataSource(MassiveEventFilterMixin, MarketDataSource):
    def __init__(
        self,
        websocket_config: MassiveWebSocketConfig,
        normalizer: EventNormalizer | None = None,
        session_filter: SessionFilter | None = None,
        filter_config: MassiveFilterConfig | None = None,
        client_factory: WebSocketClientFactory | None = None,
    ):
        self.websocket_config = websocket_config
        self.client_factory = client_factory or self._default_websocket_client_factory
        self._initialize_massive_event_filters(normalizer, session_filter, filter_config)

    def load_historical(self, request: HistoricalBatchRequest) -> Iterable[MarketEvent]:
        raise NotImplementedError("MassiveWebSocketDataSource does not support historical loading")

    def subscribe_live(self, request: LiveSubscriptionRequest) -> Iterable[MarketEvent]:
        self._reset_halt_state()
        client = self.client_factory(self.websocket_config, request)
        event_queue: Queue[tuple[str, Any]] = Queue()
        sentinel = object()
        symbols = set(request.symbols)

        def handle_msg(message: str | bytes) -> None:
            try:
                for payload in self._decode_message(message):
                    halt_signal = self._halt_signal(payload)
                    if halt_signal is not None:
                        self._apply_halt_signal(halt_signal)
                        continue
                    auction_signal = self._auction_signal(payload)
                    if auction_signal is not None:
                        self._apply_auction_signal(auction_signal)
                        continue
                    if not self._payload_is_eligible(payload):
                        continue
                    event = self.normalizer.normalize(payload)
                    if event is None:
                        continue
                    if event.symbol not in symbols:
                        continue
                    if isinstance(event, QuoteEvent) and not request.include_quotes:
                        continue
                    if isinstance(event, TradeEvent) and not request.include_trades:
                        continue
                    if not self.session_filter.accepts(event.symbol, event.timestamp_ns):
                        continue
                    if not self._event_is_eligible(event):
                        continue
                    event_queue.put(("event", event))
            except BaseException as exc:
                event_queue.put(("error", exc))

        def run_client() -> None:
            try:
                client.run(handle_msg=handle_msg, **dict(self.websocket_config.connect_kwargs))
            except BaseException as exc:
                event_queue.put(("error", exc))
            finally:
                event_queue.put(("done", sentinel))

        thread = Thread(target=run_client, daemon=True)
        thread.start()

        try:
            while True:
                kind, payload = event_queue.get()
                if kind == "event":
                    yield payload
                    continue
                if kind == "error":
                    raise payload
                break
        finally:
            try:
                asyncio.run(client.close())
            except BaseException:
                pass
            thread.join(timeout=1.0)

    @staticmethod
    def _decode_message(message: Any) -> list[dict[str, Any]]:
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        if isinstance(message, str):
            decoded = json.loads(message)
        else:
            decoded = message
        if isinstance(decoded, dict):
            return [decoded]
        if isinstance(decoded, list):
            return [payload for payload in decoded if isinstance(payload, dict)]
        return []

    @staticmethod
    def _default_websocket_client_factory(config: MassiveWebSocketConfig, request: LiveSubscriptionRequest) -> Any:
        try:
            from massive import WebSocketClient
        except ImportError as exc:
            raise RuntimeError("massive client is required for MassiveWebSocketDataSource") from exc

        api_key = _resolve_massive_api_key(config.api_key)
        if api_key is None:
            raise RuntimeError("MASSIVE_API_KEY is required for MassiveWebSocketDataSource")

        secure, feed, market = MassiveWebSocketDataSource._parse_endpoint(config.endpoint)
        subscriptions = list(config.raw_subscriptions) or MassiveWebSocketDataSource._subscriptions_for_request(request)
        return WebSocketClient(
            api_key=api_key,
            feed=feed,
            market=market,
            raw=True,
            verbose=config.verbose,
            subscriptions=subscriptions,
            max_reconnects=config.max_reconnects,
            secure=secure,
        )

    @staticmethod
    def _parse_endpoint(endpoint: str) -> tuple[bool, str, str]:
        parsed = urlparse(endpoint)
        secure = parsed.scheme != "ws"
        feed = parsed.netloc or parsed.path
        market = parsed.path.strip("/") or "stocks"
        if "/" in feed:
            feed, _, trailing_market = feed.partition("/")
            market = trailing_market or market
        return secure, feed, market

    @staticmethod
    def _subscriptions_for_request(request: LiveSubscriptionRequest) -> list[str]:
        subscriptions: list[str] = []
        for symbol in request.symbols:
            if request.include_quotes:
                subscriptions.append(f"Q.{symbol}")
            if request.include_trades:
                subscriptions.append(f"T.{symbol}")
        return subscriptions
