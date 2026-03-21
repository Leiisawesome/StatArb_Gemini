"""Forward drift labeling for transition and state outcomes."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import Iterable

import numpy as np

from l1_microstructure.events import BookSnapshot, MarketEvent, QuoteEvent, TradeEvent

from .interfaces import DriftLabel, HorizonLabelRequest


class ForwardDriftLabeler:
    """Forward drift labeler with optional pre-indexed events for O(log n) lookups."""

    def __init__(self, preindexed_events: dict[str, list[MarketEvent]] | None = None):
        self._preindexed = preindexed_events

    def label(self, request: HorizonLabelRequest, events: Iterable[MarketEvent] | None = None) -> DriftLabel:
        # Use pre-indexed events if available, otherwise fall back to iterable
        event_list = self._get_event_list(request.symbol, events)
        if event_list is None:
            # Fall back to original behavior
            return self._label_slow(request, events)

        return self._label_fast(request, event_list)

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

    def _label_fast(self, request: HorizonLabelRequest, events: list[MarketEvent]) -> DriftLabel:
        """O(log n) labeling using binary search."""
        if not events:
            return self._build_label(request, request.start_timestamp_ns, request.reference_price, censored=True)

        # Extract timestamps for binary search
        timestamps = np.array([e.timestamp_ns for e in events], dtype=np.int64)

        # Find start index (first event >= start_timestamp_ns)
        start_idx = bisect_left(timestamps, request.start_timestamp_ns)
        resolve_ns = request.start_timestamp_ns + request.horizon_ns

        # Find end index (first event >= resolve_ns)
        end_idx = bisect_right(timestamps, resolve_ns - 1)

        if start_idx >= len(events):
            return self._build_label(request, request.start_timestamp_ns, request.reference_price, censored=True)

        # Find the last price before or at resolve_ns
        latest_price = request.reference_price
        latest_timestamp = request.start_timestamp_ns

        for i in range(start_idx, min(end_idx, len(events))):
            event = events[i]
            event_price = self._price_for_event(event)
            if event_price is not None:
                latest_price = event_price
                latest_timestamp = event.timestamp_ns

        # Check if we found an event at or past resolve_ns
        censored = end_idx >= len(events) or events[min(end_idx, len(events) - 1)].timestamp_ns < resolve_ns

        return self._build_label(request, latest_timestamp, latest_price, censored)

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