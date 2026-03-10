"""Forward drift labeling for transition and state outcomes."""

from __future__ import annotations

from typing import Iterable

from l1_microstructure.events import BookSnapshot, MarketEvent, QuoteEvent, TradeEvent

from .interfaces import DriftLabel, HorizonLabelRequest


class ForwardDriftLabeler:
    def label(self, request: HorizonLabelRequest, events: Iterable[MarketEvent]) -> DriftLabel:
        resolve_ns = request.start_timestamp_ns + request.horizon_ns
        latest_price = request.reference_price
        latest_timestamp = request.start_timestamp_ns
        for event in sorted(events, key=lambda current: current.timestamp_ns):
            if event.symbol != request.symbol:
                continue
            if event.timestamp_ns < request.start_timestamp_ns:
                continue
            event_price = self._price_for_event(event)
            if event_price is None:
                continue
            latest_price = event_price
            latest_timestamp = event.timestamp_ns
            if event.timestamp_ns >= resolve_ns:
                return self._build_label(request, latest_timestamp, latest_price, censored=False)
        return self._build_label(request, latest_timestamp, latest_price, censored=True)

    @staticmethod
    def _price_for_event(event: MarketEvent) -> float | None:
        if isinstance(event, QuoteEvent):
            return BookSnapshot.from_quote(event).microprice
        if isinstance(event, TradeEvent):
            return event.price
        return None

    @staticmethod
    def _build_label(request: HorizonLabelRequest, end_timestamp_ns: int, end_price: float, censored: bool) -> DriftLabel:
        realized_drift_bps = 0.0
        if request.reference_price > 0:
            realized_drift_bps = ((end_price - request.reference_price) / request.reference_price) * 10_000.0
        return DriftLabel(
            symbol=request.symbol,
            start_timestamp_ns=request.start_timestamp_ns,
            end_timestamp_ns=end_timestamp_ns,
            realized_drift_bps=float(realized_drift_bps),
            censored=censored,
            metadata=dict(request.metadata),
        )