"""Forward drift labeling for transition and state outcomes."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import Iterable

from l1_microstructure.events import BookSnapshot, MarketEvent, QuoteEvent, TradeEvent

from .interfaces import DriftLabel, HorizonLabelRequest


class ForwardDriftLabeler:
    """Forward drift labeler with optional pre-indexed events for O(log n) lookups."""

    def __init__(self, preindexed_events: dict[str, list[MarketEvent]] | None = None):
        self._preindexed = preindexed_events
        self._timestamps_by_symbol = {
            symbol: tuple(event.timestamp_ns for event in events)
            for symbol, events in (preindexed_events or {}).items()
        }

    def label(self, request: HorizonLabelRequest, events: Iterable[MarketEvent] | None = None) -> DriftLabel:
        # Use pre-indexed events if available, otherwise fall back to iterable
        event_list = self._get_event_list(request.symbol, events)
        if event_list is None:
            # Fall back to original behavior
            return self._label_slow(request, events)

        timestamps = self._timestamps_by_symbol.get(request.symbol)
        if timestamps is None:
            timestamps = tuple(event.timestamp_ns for event in event_list)
        return self._label_fast(request, event_list, timestamps)

    def _get_event_list(self, symbol: str, events: Iterable[MarketEvent] | None) -> list[MarketEvent] | None:
        """Get pre-indexed event list if available."""
        if self._preindexed is not None and symbol in self._preindexed:
            return self._preindexed[symbol]
        if events is not None and hasattr(events, '__iter__'):
            # Check if it's already a list
            if isinstance(events, list):
                return events
            # Convert to list and check if we should cache
            return list(events)
        return None

    def _label_fast(
        self,
        request: HorizonLabelRequest,
        events: list[MarketEvent],
        timestamps: tuple[int, ...],
    ) -> DriftLabel:
        """O(log n) labeling using binary search — semantically identical to _label_slow."""
        if not events:
            return self._build_label(request, request.start_timestamp_ns, request.reference_price, censored=True)

        # Find start index (first event with ts >= start_timestamp_ns)
        start_idx = bisect_left(timestamps, request.start_timestamp_ns)
        resolve_ns = request.start_timestamp_ns + request.horizon_ns
        # First event with ts >= resolve_ns (the "uncensored trigger" position)
        resolve_idx = bisect_left(timestamps, resolve_ns)

        if start_idx >= len(events):
            return self._build_label(request, request.start_timestamp_ns, request.reference_price, censored=True)

        latest_price = request.reference_price
        latest_timestamp = request.start_timestamp_ns

        # Accumulate the running price up to (but not including) resolve_ns
        for i in range(start_idx, min(resolve_idx, len(events))):
            event = events[i]
            if event.symbol != request.symbol:
                continue
            event_price = self._price_for_event(event)
            if event_price is not None:
                latest_price = event_price
                latest_timestamp = event.timestamp_ns

        # Scan from resolve_idx for the first same-symbol priced event:
        # that event triggers censored=False (mirrors _label_slow's early-return).
        for i in range(resolve_idx, len(events)):
            event = events[i]
            if event.symbol != request.symbol:
                continue
            event_price = self._price_for_event(event)
            if event_price is not None:
                return self._build_label(request, event.timestamp_ns, event_price, censored=False)

        return self._build_label(request, latest_timestamp, latest_price, censored=True)

    def _label_slow(self, request: HorizonLabelRequest, events: Iterable[MarketEvent]) -> DriftLabel:
        """Original O(n) labeling for backward compatibility."""
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
