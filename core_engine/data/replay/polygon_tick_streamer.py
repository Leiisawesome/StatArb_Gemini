#!/usr/bin/env python3
"""
Polygon Historical Tick Streamer
================================

Backtest-only data source that pulls historical second snapshots from
PolygonRestService and replays them as live-style feed messages.

Design goals:
    - Reuse core_engine.data.feeds.polygon_rest as the only pull layer
    - Emit standardized FeedMessage objects (trade/quote/bar)
    - Preserve event-time ordering for multi-symbol replay
    - Allow configurable playback speed (realtime, accelerated, instant)
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Set

import pandas as pd

from core_engine.data.feeds.adapters import (
    AdapterStatus,
    DataFeedAdapter,
    FeedAdapterConfig,
    FeedMessage,
    FeedProvider,
)
from core_engine.data.feeds.polygon_rest import PolygonRestService, create_polygon_rest_service

logger = logging.getLogger(__name__)


@dataclass
class PolygonTickStreamerConfig:
    """Configuration for PolygonHistoricalTickStreamer."""

    symbols: List[str]
    start_time: datetime
    end_time: datetime

    api_key: str = field(default_factory=lambda: os.getenv("POLYGON_API_KEY", ""))
    adapter_name: str = "polygon-historical-tick-streamer"

    # Replay timing:
    #   1.0 = realtime, 2.0 = 2x faster, inf = instant replay
    playback_speed: float = 1.0

    # Data pull behavior
    forward_fill_quotes: bool = True
    forward_fill_trades: bool = False
    max_pages: int = 50
    limit_per_page: int = 50000

    # Emitted stream types
    emit_trade: bool = True
    emit_quote: bool = True
    emit_second_agg: bool = True
    emit_minute_agg: bool = False

    # Canonical behavior mode:
    #   True  -> payload fields mirror websocket live adapter schema only
    #   False -> include additional replay-enriched convenience fields
    strict_live_parity: bool = True

    # Microstructure fidelity mode:
    #   False -> use compact snapshot schema only
    #   True  -> request and propagate richer trade/quote microstructure fields
    full_fidelity: bool = False

    def __post_init__(self) -> None:
        if not self.symbols:
            raise ValueError("symbols cannot be empty")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be earlier than end_time")
        if not self.api_key:
            raise ValueError("Polygon API key required")

        speed = float(self.playback_speed)
        if speed <= 0 and not math.isinf(speed):
            raise ValueError("playback_speed must be > 0 or infinity")


class PolygonHistoricalTickStreamer(DataFeedAdapter):
    """
    Historical tick streamer powered by PolygonRestService snapshots.

    Pull phase:
        get_trade_quote_snapshots_1s(symbol, start_time, end_time)
    Replay phase:
        emit FeedMessage events second-by-second by event timestamp.
    """

    IS_IMPLEMENTED = True
    PROVIDER = FeedProvider.POLYGON
    SUPPORTED_DATA_TYPES = ["trade", "quote", "second_agg", "minute_agg"]

    def __init__(self, config: PolygonTickStreamerConfig):
        base_config = FeedAdapterConfig(
            provider=FeedProvider.POLYGON,
            name=config.adapter_name,
            api_key=config.api_key,
            provider_config={"backtest_only": True},
        )
        super().__init__(base_config)

        self.streamer_config = config
        self._rest_service: Optional[PolygonRestService] = None
        self._stream_task: Optional[asyncio.Task] = None
        self._stream_done = asyncio.Event()
        self._stop_requested = False
        self._snapshot_data: Dict[str, pd.DataFrame] = {}

    async def connect(self) -> bool:
        try:
            self._set_status(AdapterStatus.CONNECTING)
            self._rest_service = await create_polygon_rest_service(api_key=self.streamer_config.api_key)
            self._stats["connection_time"] = datetime.now().isoformat()
            self._set_status(AdapterStatus.CONNECTED)
            self.logger.info(
                "Connected PolygonHistoricalTickStreamer for %d symbols",
                len(self.streamer_config.symbols),
            )
            return True
        except Exception as exc:
            self._handle_error(exc)
            self._set_status(AdapterStatus.ERROR)
            return False

    async def disconnect(self) -> None:
        self._stop_requested = True

        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass

        if self._rest_service is not None:
            await self._rest_service.close()
            self._rest_service = None

        self._snapshot_data.clear()
        self._subscriptions.clear()
        self._set_status(AdapterStatus.DISCONNECTED)

    async def subscribe(self, symbols: List[str], data_types: List[str]) -> bool:
        if not self.is_connected() or self._rest_service is None:
            self.logger.error("Cannot subscribe before connect()")
            return False

        requested = {symbol.upper() for symbol in symbols}
        allowed = {symbol.upper() for symbol in self.streamer_config.symbols}
        unknown = requested - allowed
        if unknown:
            self.logger.error("Requested symbols outside config scope: %s", sorted(unknown))
            return False

        valid_types = [data_type for data_type in data_types if data_type in self.SUPPORTED_DATA_TYPES]
        if not valid_types:
            self.logger.error("No valid data types requested. Supported: %s", self.SUPPORTED_DATA_TYPES)
            return False

        self._subscriptions.update(requested)
        self._set_status(AdapterStatus.SUBSCRIBING)

        try:
            await self._prepare_snapshot_data(symbols=sorted(self._subscriptions))
            self._stop_requested = False
            self._stream_done.clear()

            if self._stream_task is None or self._stream_task.done():
                self._stream_task = asyncio.create_task(self._run_stream(valid_types=valid_types))

            self._set_status(AdapterStatus.ACTIVE)
            return True
        except Exception as exc:
            self._handle_error(exc)
            self._set_status(AdapterStatus.ERROR)
            return False

    async def unsubscribe(self, symbols: List[str]) -> bool:
        for symbol in symbols:
            self._subscriptions.discard(symbol.upper())

        if not self._subscriptions:
            self._stop_requested = True
        return True

    def is_connected(self) -> bool:
        return self.status in {
            AdapterStatus.CONNECTED,
            AdapterStatus.SUBSCRIBING,
            AdapterStatus.ACTIVE,
        }

    async def wait_until_complete(self, timeout: Optional[float] = None) -> bool:
        try:
            await asyncio.wait_for(self._stream_done.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def _prepare_snapshot_data(self, symbols: Sequence[str]) -> None:
        if self._rest_service is None:
            raise RuntimeError("REST service is not initialized")

        self._snapshot_data.clear()

        for symbol in symbols:
            snapshot_df = await self._rest_service.get_trade_quote_snapshots_1s(
                symbol=symbol,
                start=self.streamer_config.start_time,
                end=self.streamer_config.end_time,
                forward_fill_quotes=self.streamer_config.forward_fill_quotes,
                forward_fill_trades=self.streamer_config.forward_fill_trades,
                limit=self.streamer_config.limit_per_page,
                max_pages=self.streamer_config.max_pages,
                full_fidelity=self.streamer_config.full_fidelity,
            )

            if snapshot_df is None or snapshot_df.empty:
                self.logger.warning("No snapshot data pulled for %s", symbol)
                continue

            self._snapshot_data[symbol.upper()] = snapshot_df.sort_index()

        if not self._snapshot_data:
            raise RuntimeError("No snapshot data available for requested symbols/time range")

    async def _run_stream(self, valid_types: List[str]) -> None:
        allowed_types = set(valid_types)
        timeline = self._build_timeline()
        minute_state: Dict[str, Dict[str, object]] = {}

        previous_ts: Optional[datetime] = None

        try:
            for ts in timeline:
                if self._stop_requested:
                    break

                if previous_ts is not None:
                    await self._sleep_for_gap(previous_ts, ts)

                for symbol, snapshot_df in self._snapshot_data.items():
                    if ts not in snapshot_df.index:
                        continue

                    row = snapshot_df.loc[ts]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[-1]

                    for message in self._row_to_messages(
                        symbol=symbol,
                        timestamp=ts,
                        row=row,
                        allowed_types=allowed_types,
                        minute_state=minute_state,
                    ):
                        self._handle_message(message)

                previous_ts = ts

            if "minute_agg" in allowed_types and self.streamer_config.emit_minute_agg:
                for symbol, state in minute_state.items():
                    minute_message = self._build_minute_agg_message(symbol=symbol, state=state)
                    if minute_message is not None:
                        self._handle_message(minute_message)

            self._set_status(AdapterStatus.CONNECTED)
        except asyncio.CancelledError:
            self.logger.debug("Polygon historical tick stream cancelled")
            raise
        except Exception as exc:
            self._handle_error(exc)
            self._set_status(AdapterStatus.ERROR)
        finally:
            self._stream_done.set()

    def _build_timeline(self) -> List[datetime]:
        all_timestamps: Set[datetime] = set()
        for snapshot_df in self._snapshot_data.values():
            all_timestamps.update(snapshot_df.index.tolist())
        return sorted(all_timestamps)

    async def _sleep_for_gap(self, previous_ts: datetime, current_ts: datetime) -> None:
        speed = float(self.streamer_config.playback_speed)
        if math.isinf(speed):
            return

        gap_seconds = (current_ts - previous_ts).total_seconds()
        if gap_seconds <= 0:
            return

        wait_seconds = gap_seconds / speed
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

    def _row_to_messages(
        self,
        symbol: str,
        timestamp: datetime,
        row: pd.Series,
        allowed_types: Set[str],
        minute_state: Dict[str, Dict[str, object]],
    ) -> List[FeedMessage]:
        messages: List[FeedMessage] = []

        trade_price = self._safe_float(row.get("trade_price"), default=None)
        trade_size = self._safe_int(row.get("trade_size"), default=0)
        trade_exchange = self._safe_int(row.get("trade_exchange"), default=0)
        trade_count = self._safe_int(row.get("trade_count"), default=0)
        trade_tape = self._safe_int(row.get("trade_tape"), default=0)
        trade_sequence_number = self._safe_optional_int(row.get("trade_sequence_number"))
        trade_conditions = self._safe_int_list(row.get("trade_conditions"))

        quote_bid = self._safe_float(row.get("quote_bid"), default=None)
        quote_ask = self._safe_float(row.get("quote_ask"), default=None)
        quote_bid_size = self._safe_int(row.get("quote_bid_size"), default=0)
        quote_ask_size = self._safe_int(row.get("quote_ask_size"), default=0)
        quote_count = self._safe_int(row.get("quote_count"), default=0)
        quote_bid_exchange = self._safe_int(row.get("quote_bid_exchange"), default=0)
        quote_ask_exchange = self._safe_int(row.get("quote_ask_exchange"), default=0)
        quote_conditions = self._safe_int_list(row.get("quote_conditions"))
        quote_age_ms = self._safe_float(row.get("quote_age_ms"), default=None)
        spread_raw = self._safe_float(row.get("spread"), default=None)

        has_trade = trade_count > 0 and trade_price is not None
        has_quote = quote_bid is not None and quote_ask is not None
        spread = (quote_ask - quote_bid) if has_quote else spread_raw
        event_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)

        if self.streamer_config.emit_trade and "trade" in allowed_types and has_trade:
            trade_data = {
                "price": float(trade_price),
                "size": int(trade_size),
                "conditions": trade_conditions,
                "exchange": int(trade_exchange),
                "tape": int(trade_tape),
            }
            if not self.streamer_config.strict_live_parity:
                trade_data["trade_count"] = trade_count

            messages.append(
                FeedMessage(
                    provider=FeedProvider.POLYGON,
                    symbol=symbol,
                    message_type="trade",
                    timestamp=event_ts,
                    data=trade_data,
                    sequence_number=trade_sequence_number,
                    latency_ms=0.0,
                    raw_data=None,
                )
            )

        if self.streamer_config.emit_quote and "quote" in allowed_types and has_quote:
            quote_data = {
                "bid": float(quote_bid),
                "bid_size": int(quote_bid_size),
                "ask": float(quote_ask),
                "ask_size": int(quote_ask_size),
                "bid_exchange": int(quote_bid_exchange),
                "ask_exchange": int(quote_ask_exchange),
                "conditions": quote_conditions,
            }
            if not self.streamer_config.strict_live_parity:
                quote_data.update(
                    {
                        "spread": float(spread) if spread is not None else 0.0,
                        "quote_count": quote_count,
                        "is_stale": quote_count == 0,
                    }
                )
                if quote_age_ms is not None:
                    quote_data["quote_age_ms"] = float(quote_age_ms)

            messages.append(
                FeedMessage(
                    provider=FeedProvider.POLYGON,
                    symbol=symbol,
                    message_type="quote",
                    timestamp=event_ts,
                    data=quote_data,
                    latency_ms=0.0,
                    raw_data=None,
                )
            )

        close_price: Optional[float] = None
        if has_trade:
            close_price = float(trade_price)
        elif has_quote:
            close_price = (float(quote_bid) + float(quote_ask)) / 2.0

        if close_price is not None:
            volume_value = float(trade_size) if has_trade else 0.0
            second_start = event_ts
            second_end = second_start + timedelta(seconds=1)

            if self.streamer_config.emit_second_agg and "second_agg" in allowed_types:
                messages.append(
                    FeedMessage(
                        provider=FeedProvider.POLYGON,
                        symbol=symbol,
                        message_type="second_agg",
                        timestamp=second_end,
                        data={
                            "open": close_price,
                            "high": close_price,
                            "low": close_price,
                            "close": close_price,
                            "volume": volume_value,
                            "vwap": close_price,
                            "num_trades": trade_count,
                            "bar_type": "second",
                            "timestamp_start": second_start.isoformat(),
                            "timestamp_end": second_end.isoformat(),
                            "otc": False,
                        },
                        latency_ms=0.0,
                        raw_data=None,
                    )
                )

            if self.streamer_config.emit_minute_agg and "minute_agg" in allowed_types:
                minute_bucket = second_start.replace(second=0, microsecond=0)
                prior_state = minute_state.get(symbol)

                if prior_state is not None and prior_state["minute_start"] != minute_bucket:
                    prior_message = self._build_minute_agg_message(symbol=symbol, state=prior_state)
                    if prior_message is not None:
                        messages.append(prior_message)
                    prior_state = None

                if prior_state is None:
                    minute_state[symbol] = {
                        "minute_start": minute_bucket,
                        "open": close_price,
                        "high": close_price,
                        "low": close_price,
                        "close": close_price,
                        "volume": volume_value,
                        "num_trades": trade_count,
                    }
                else:
                    prior_state["high"] = max(float(prior_state["high"]), close_price)
                    prior_state["low"] = min(float(prior_state["low"]), close_price)
                    prior_state["close"] = close_price
                    prior_state["volume"] = float(prior_state["volume"]) + volume_value
                    prior_state["num_trades"] = int(prior_state["num_trades"]) + trade_count

        return messages

    @staticmethod
    def _safe_float(value: object, default: Optional[float]) -> Optional[float]:
        if value is None:
            return default
        try:
            if pd.isna(value):
                return default
        except TypeError:
            pass
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: object, default: int) -> int:
        if value is None:
            return default
        try:
            if pd.isna(value):
                return default
        except TypeError:
            pass
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_optional_int(value: object) -> Optional[int]:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int_list(value: object) -> List[int]:
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            return []

        normalized: List[int] = []
        for item in value:
            try:
                if pd.isna(item):
                    continue
            except TypeError:
                pass

            try:
                normalized.append(int(item))
            except (TypeError, ValueError):
                continue
        return normalized

    def _build_minute_agg_message(self, symbol: str, state: Dict[str, object]) -> Optional[FeedMessage]:
        minute_start = state.get("minute_start")
        if not isinstance(minute_start, datetime):
            return None

        minute_end = minute_start + timedelta(minutes=1)
        open_price = float(state.get("open", 0.0) or 0.0)
        high_price = float(state.get("high", open_price) or open_price)
        low_price = float(state.get("low", open_price) or open_price)
        close_price = float(state.get("close", open_price) or open_price)
        volume_value = float(state.get("volume", 0.0) or 0.0)
        trade_count = int(state.get("num_trades", 0) or 0)

        return FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol=symbol,
            message_type="minute_agg",
            timestamp=minute_end,
            data={
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume_value,
                "vwap": close_price,
                "num_trades": trade_count,
                "bar_type": "minute",
                "timestamp_start": minute_start.isoformat(),
                "timestamp_end": minute_end.isoformat(),
                "otc": False,
            },
            latency_ms=0.0,
            raw_data=None,
        )


async def create_polygon_tick_streamer(config: PolygonTickStreamerConfig) -> PolygonHistoricalTickStreamer:
    """Create and connect a PolygonHistoricalTickStreamer."""
    streamer = PolygonHistoricalTickStreamer(config)
    connected = await streamer.connect()
    if not connected:
        raise RuntimeError("Failed to connect PolygonHistoricalTickStreamer")
    return streamer


__all__ = [
    "PolygonTickStreamerConfig",
    "PolygonHistoricalTickStreamer",
    "create_polygon_tick_streamer",
]
