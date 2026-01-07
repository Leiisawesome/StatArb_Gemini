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

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Callable
from zoneinfo import ZoneInfo

from core_engine.data.feeds.adapters import FeedMessage
from core_engine.system.event_dispatcher import DeterministicEventDispatcher, EventType
from core_engine.system.idempotency import IdGenerator
from core_engine.system.session_gate import TradingSessionGate, GateDecision

logger = logging.getLogger(__name__)


@dataclass
class BridgeStats:
    bars_enqueued: int = 0
    quotes_enqueued: int = 0
    trades_enqueued: int = 0
    dropped: int = 0
    skipped_market_hours: int = 0


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
        session_gate: Optional[TradingSessionGate] = None,
        filter_market_hours: bool = True,
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
        self._session_gate = session_gate
        self._filter_market_hours = filter_market_hours

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "bars_enqueued": self._stats.bars_enqueued,
            "quotes_enqueued": self._stats.quotes_enqueued,
            "trades_enqueued": self._stats.trades_enqueued,
            "dropped": self._stats.dropped,
            "skipped_before_start": self._skipped_before_start,
            "skipped_market_hours": self._stats.skipped_market_hours,
        }

    def on_feed_message(self, msg: FeedMessage) -> None:
        """
        FeedMessage handler suitable for HistoricalReplayFeedAdapter.add_message_handler().

        Note: DeterministicEventDispatcher.enqueue() is thread-safe.
        """
        ts = msg.timestamp
        if ts.tzinfo is None:
            # CRITICAL: US Equity data is typically stored in Eastern Time.
            # If naive, treat as America/New_York to ensure session gate parity with backtest.
            try:
                ts = ts.replace(tzinfo=ZoneInfo("America/New_York"))
            except Exception:
                ts = ts.replace(tzinfo=timezone.utc)

        event_type = self._map_type(msg.message_type)
        if event_type is None:
            return

        # Market Hours Filtering (Consistency with Backtest)
        # If session_gate is provided and filter_market_hours is True, we only allow RTH data.
        if self._filter_market_hours and self._session_gate:
            res = self._session_gate.check(ts, msg.symbol)
            if res.decision == GateDecision.REJECT:
                self._stats.skipped_market_hours += 1
                return

        # Optional debug fast-forward: ignore bars until a configured start timestamp.
        # This keeps reproductions to a few seconds while preserving determinism inside the window.
        if event_type == EventType.BAR and self._start_at_timestamp is not None and ts < self._start_at_timestamp:
            self._skipped_before_start += 1
            
            # Enqueue a heartbeat to keep watchdog alive during fast-forward
            # We use a low-priority SYSTEM event that the engine will ignore but watchdog will see
            self._dispatcher.enqueue(
                event_type=EventType.SYSTEM,
                payload={'type': 'heartbeat', 'reason': 'fast_forward', 'timestamp': ts.isoformat()},
                market_timestamp=ts,
                event_id=f"heartbeat-{ts.timestamp()}-{msg.symbol}"
            )
            return

        payload = self._normalize_payload(msg)
        # Ensure payload timestamp is timezone-consistent with the market timestamp we enqueue.
        # Without this, warmup bars (tz-aware) + replay bars (tz-naive) can mix in buffers and
        # break indicator sorting/comparisons.
        payload["timestamp"] = ts
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


