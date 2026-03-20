from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from l1_microstructure.events import MarketEvent, QuoteEvent, TradeEvent
from l1_microstructure.ingest._massive_support import _EASTERN, MassiveEventFilterMixin, MassiveFilterConfig
from l1_microstructure.ingest.interfaces import EventNormalizer, HistoricalBatchRequest, LiveSubscriptionRequest, MarketDataSource, SessionFilter


class FixtureMarketDataSource(MassiveEventFilterMixin, MarketDataSource):
    def __init__(
        self,
        payloads: Iterable[dict[str, Any] | MarketEvent],
        normalizer: EventNormalizer | None = None,
        session_filter: SessionFilter | None = None,
        filter_config: MassiveFilterConfig | None = None,
    ):
        self._initialize_massive_event_filters(normalizer, session_filter, filter_config)
        self._events = self._normalize_payloads(payloads)

    def load_historical(self, request: HistoricalBatchRequest) -> Iterable[MarketEvent]:
        symbols = set(request.symbols)
        start_ns = request.start_ns if request.start_ns is not None else -1
        end_ns = request.end_ns if request.end_ns is not None else 2**63 - 1
        for event in self._events:
            if event.symbol not in symbols:
                continue
            if event.timestamp_ns < start_ns or event.timestamp_ns > end_ns:
                continue
            if not self.session_filter.accepts(event.symbol, event.timestamp_ns):
                continue
            if isinstance(event, QuoteEvent) and not request.include_quotes:
                continue
            if isinstance(event, TradeEvent) and not request.include_trades:
                continue
            event_date = datetime.fromtimestamp(event.timestamp_ns / 1_000_000_000.0, tz=timezone.utc).astimezone(_EASTERN).date()
            if event_date != request.trade_date:
                continue
            yield event

    def subscribe_live(self, request: LiveSubscriptionRequest) -> Iterable[MarketEvent]:
        symbols = set(request.symbols)
        for event in self._events:
            if event.symbol not in symbols:
                continue
            if not self.session_filter.accepts(event.symbol, event.timestamp_ns):
                continue
            if isinstance(event, QuoteEvent) and not request.include_quotes:
                continue
            if isinstance(event, TradeEvent) and not request.include_trades:
                continue
            yield event