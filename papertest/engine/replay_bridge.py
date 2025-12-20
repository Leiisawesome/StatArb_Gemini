"""
ReplayToDispatcherBridge
=======================

Bridges core_engine's HistoricalReplayFeedAdapter (FeedMessage callbacks)
into the DeterministicEventDispatcher as BAR/QUOTE/TRADE events.

This is the authoritative ingestion edge for papertest: it preserves
market timestamps, adds deterministic event IDs, and relies on the dispatcher
for ordering, conflation, and backpressure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Callable

from core_engine.data.feeds.adapters import FeedMessage
from core_engine.system.event_dispatcher import DeterministicEventDispatcher, EventType
from core_engine.system.idempotency import IdGenerator


@dataclass
class BridgeStats:
    bars_enqueued: int = 0
    quotes_enqueued: int = 0
    trades_enqueued: int = 0
    dropped: int = 0


class ReplayToDispatcherBridge:
    def __init__(
        self,
        dispatcher: DeterministicEventDispatcher,
        id_generator: IdGenerator,
        enqueue_timeout: Optional[float] = None,
        start_at_timestamp: Optional[datetime] = None,
        stop_after_bars: Optional[int] = None,
        stop_at_timestamp: Optional[datetime] = None,
        stop_callback: Optional[Callable[[], None]] = None,
    ):
        self._dispatcher = dispatcher
        self._ids = id_generator
        self._timeout = enqueue_timeout
        self._stats = BridgeStats()
        self._start_at_timestamp = start_at_timestamp
        self._skipped_before_start = 0
        self._stop_after_bars = int(stop_after_bars) if stop_after_bars else None
        self._stop_at_timestamp = stop_at_timestamp
        self._stop_callback = stop_callback
        self._stop_requested = False

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "bars_enqueued": self._stats.bars_enqueued,
            "quotes_enqueued": self._stats.quotes_enqueued,
            "trades_enqueued": self._stats.trades_enqueued,
            "dropped": self._stats.dropped,
            "skipped_before_start": self._skipped_before_start,
        }

    def on_feed_message(self, msg: FeedMessage) -> None:
        """
        FeedMessage handler suitable for HistoricalReplayFeedAdapter.add_message_handler().

        Note: DeterministicEventDispatcher.enqueue() is thread-safe.
        """
        ts = msg.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        event_type = self._map_type(msg.message_type)
        if event_type is None:
            return

        # Optional debug fast-forward: ignore bars until a configured start timestamp.
        # This keeps reproductions to a few seconds while preserving determinism inside the window.
        if event_type == EventType.BAR and self._start_at_timestamp is not None and ts < self._start_at_timestamp:
            self._skipped_before_start += 1
            return

        payload = self._normalize_payload(msg)
        market_ts_ns = int(ts.timestamp() * 1_000_000_000)
        event_id = self._ids.generate_event_id(event_type.name, market_ts_ns, msg.symbol)

        ok = self._dispatcher.enqueue(
            event_type=event_type,
            payload=payload,
            market_timestamp=ts,
            symbol=msg.symbol,
            event_id=event_id,
            timeout=self._timeout,
        )

        if not ok:
            self._stats.dropped += 1
            return

        if event_type == EventType.BAR:
            self._stats.bars_enqueued += 1
            self._maybe_stop(ts)
        elif event_type == EventType.QUOTE:
            self._stats.quotes_enqueued += 1
        elif event_type == EventType.TRADE:
            self._stats.trades_enqueued += 1

    def _maybe_stop(self, ts: datetime) -> None:
        """
        Optional early-stop hook for fast debugging.

        This is intentionally best-effort: it requests stop once a condition is met.
        """
        if self._stop_requested:
            return
        if self._stop_after_bars is not None and self._stats.bars_enqueued >= self._stop_after_bars:
            self._stop_requested = True
            if self._stop_callback:
                self._stop_callback()
            return
        if self._stop_at_timestamp is not None and ts >= self._stop_at_timestamp:
            self._stop_requested = True
            if self._stop_callback:
                self._stop_callback()
            return

    @staticmethod
    def _map_type(message_type: str) -> Optional[EventType]:
        mt = (message_type or "").lower()
        if mt == "bar":
            return EventType.BAR
        if mt == "quote":
            return EventType.QUOTE
        if mt == "trade":
            return EventType.TRADE
        return None

    @staticmethod
    def _normalize_payload(msg: FeedMessage) -> Dict[str, Any]:
        data = dict(msg.data or {})
        # Ensure symbol/timestamp present for downstream consumers
        data.setdefault("symbol", msg.symbol)
        data.setdefault("timestamp", msg.timestamp)
        # Normalize OHLCV naming (PaperTradingEngine uses open/high/low/close/volume)
        # Keep any extra fields (vwap, transactions, etc.)
        return data


