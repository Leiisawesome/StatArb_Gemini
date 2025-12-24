"""
PolygonToDispatcherBridge
=========================

Bridges `core_engine.data.feeds.polygon_integration.PolygonDataService` callbacks
into `core_engine.system.event_dispatcher.DeterministicEventDispatcher` as BAR/TRADE
events with:

- Strict per-symbol bar monotonicity enforcement (drop out-of-order bars)
- Deterministic event IDs (IdGenerator)
- Data-age fields for ops visibility and safety gating:
  - source_timestamp (provider time)
  - received_timestamp (local wall clock)
  - data_age_seconds = received - source

Notes
-----
Polygon Starter is typically 15-minute delayed. This bridge does NOT attempt to
“correct” delay—only to preserve timestamps and quantify staleness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core_engine.system.event_dispatcher import DeterministicEventDispatcher, EventType
from core_engine.system.idempotency import IdGenerator


@dataclass
class BridgeStats:
    bars_enqueued: int = 0
    trades_enqueued: int = 0
    dropped_before_min_ts: int = 0
    dropped_out_of_order_bars: int = 0
    dropped_enqueue_failed: int = 0


class PolygonToDispatcherBridge:
    """
    Convert PolygonDataService callbacks to dispatcher events.

    This object is intentionally synchronous: PolygonDataService calls callbacks
    from its own ingestion path. `DeterministicEventDispatcher.enqueue()` is
    thread-safe.
    """

    def __init__(
        self,
        dispatcher: DeterministicEventDispatcher,
        id_generator: IdGenerator,
        enqueue_timeout: Optional[float] = None,
        min_source_timestamp: Optional[datetime] = None,
    ):
        self._dispatcher = dispatcher
        self._ids = id_generator
        self._timeout = enqueue_timeout
        # Global cutoff (applies to all symbols) and optional per-symbol cutoffs.
        self._min_ts = min_source_timestamp
        self._min_ts_by_symbol: Dict[str, datetime] = {}

        self._stats = BridgeStats()
        self._last_bar_ts_by_symbol: Dict[str, datetime] = {}

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "bars_enqueued": self._stats.bars_enqueued,
            "trades_enqueued": self._stats.trades_enqueued,
            "dropped_before_min_ts": self._stats.dropped_before_min_ts,
            "dropped_out_of_order_bars": self._stats.dropped_out_of_order_bars,
            "dropped_enqueue_failed": self._stats.dropped_enqueue_failed,
        }

    def last_bar_timestamp(self, symbol: str) -> Optional[datetime]:
        """Last accepted BAR source timestamp for a symbol (post-monotonicity filter)."""
        sym = (symbol or "").upper()
        return self._last_bar_ts_by_symbol.get(sym)

    def set_min_source_timestamp(self, ts: Optional[datetime], symbol: Optional[str] = None) -> None:
        """
        Set a lower bound on accepted provider timestamps.

        Used after REST warmup: ignore WS events at or before warmup end timestamp.
        """
        if symbol is None:
            self._min_ts = ts
            return
        sym = (symbol or "").upper()
        if not sym:
            return
        if ts is None:
            self._min_ts_by_symbol.pop(sym, None)
        else:
            self._min_ts_by_symbol[sym] = _ensure_tz(ts)

    def _get_min_ts_for_symbol(self, symbol: str) -> Optional[datetime]:
        sym = (symbol or "").upper()
        if sym in self._min_ts_by_symbol:
            return self._min_ts_by_symbol[sym]
        return _ensure_tz(self._min_ts) if self._min_ts is not None else None

    # ---------------------------------------------------------------------
    # PolygonDataService callback adapters
    # ---------------------------------------------------------------------

    def on_bar(self, symbol: str, timeframe: str, bar: Any) -> None:
        """
        Callback signature compatible with PolygonDataService.add_bar_callback().

        Args:
            symbol: Symbol (string)
            timeframe: 'minute' or 'second' (string)
            bar: PolygonAggregateBar (duck-typed)
        """
        sym = (symbol or "").upper()
        source_ts = getattr(bar, "timestamp_end", None) or getattr(bar, "timestamp", None)
        if source_ts is None:
            return

        source_ts = _ensure_tz(source_ts)
        min_ts = self._get_min_ts_for_symbol(sym)
        if min_ts is not None and source_ts <= min_ts:
            self._stats.dropped_before_min_ts += 1
            return

        # Enforce per-symbol monotonic bars (drop out-of-order/duplicate bars)
        last_ts = self._last_bar_ts_by_symbol.get(sym)
        if last_ts is not None and source_ts <= last_ts:
            self._stats.dropped_out_of_order_bars += 1
            return
        self._last_bar_ts_by_symbol[sym] = source_ts

        received_ts = datetime.now(timezone.utc)
        payload = self._normalize_bar_payload(sym, timeframe, bar, source_ts, received_ts)
        market_ts_ns = int(source_ts.timestamp() * 1_000_000_000)
        event_id = self._ids.generate_event_id(EventType.BAR.name, market_ts_ns, sym)

        ok = self._dispatcher.enqueue(
            event_type=EventType.BAR,
            payload=payload,
            market_timestamp=source_ts,
            symbol=sym,
            event_id=event_id,
            timeout=self._timeout,
        )
        if not ok:
            self._stats.dropped_enqueue_failed += 1
            return
        self._stats.bars_enqueued += 1

    def on_trade(self, symbol: str, trade: Any) -> None:
        """
        Callback signature compatible with PolygonDataService.add_trade_callback().

        Args:
            symbol: Symbol (string)
            trade: PolygonTrade (duck-typed)
        """
        sym = (symbol or "").upper()
        source_ts = getattr(trade, "timestamp", None)
        if source_ts is None:
            return
        source_ts = _ensure_tz(source_ts)

        min_ts = self._get_min_ts_for_symbol(sym)
        if min_ts is not None and source_ts <= min_ts:
            self._stats.dropped_before_min_ts += 1
            return

        received_ts = datetime.now(timezone.utc)
        payload = self._normalize_trade_payload(sym, trade, source_ts, received_ts)
        market_ts_ns = int(source_ts.timestamp() * 1_000_000_000)
        event_id = self._ids.generate_event_id(EventType.TRADE.name, market_ts_ns, sym)

        ok = self._dispatcher.enqueue(
            event_type=EventType.TRADE,
            payload=payload,
            market_timestamp=source_ts,
            symbol=sym,
            event_id=event_id,
            timeout=self._timeout,
        )
        if not ok:
            self._stats.dropped_enqueue_failed += 1
            return
        self._stats.trades_enqueued += 1

    # ---------------------------------------------------------------------
    # Payload normalization
    # ---------------------------------------------------------------------

    @staticmethod
    def _normalize_bar_payload(
        symbol: str,
        timeframe: str,
        bar: Any,
        source_ts: datetime,
        received_ts: datetime,
    ) -> Dict[str, Any]:
        data_age = (received_ts - source_ts).total_seconds()
        payload: Dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": source_ts,
            "open": float(getattr(bar, "open", 0.0) or 0.0),
            "high": float(getattr(bar, "high", 0.0) or 0.0),
            "low": float(getattr(bar, "low", 0.0) or 0.0),
            "close": float(getattr(bar, "close", 0.0) or 0.0),
            "volume": float(getattr(bar, "volume", 0.0) or 0.0),
            # extras (non-breaking for engine)
            "vwap": getattr(bar, "vwap", None),
            "num_trades": getattr(bar, "num_trades", None),
            "source_timestamp": source_ts,
            "received_timestamp": received_ts,
            "data_age_seconds": float(data_age),
        }
        return payload

    @staticmethod
    def _normalize_trade_payload(
        symbol: str,
        trade: Any,
        source_ts: datetime,
        received_ts: datetime,
    ) -> Dict[str, Any]:
        data_age = (received_ts - source_ts).total_seconds()
        price = getattr(trade, "price", None)
        size = getattr(trade, "size", None)
        payload: Dict[str, Any] = {
            "symbol": symbol,
            "timestamp": source_ts,
            # Engine reads payload.get('price') or payload.get('last_price')
            "price": float(price) if price is not None else None,
            "last_price": float(price) if price is not None else None,
            "size": float(size) if size is not None else None,
            # extras
            "conditions": getattr(trade, "conditions", None),
            "exchange": getattr(trade, "exchange", None),
            "tape": getattr(trade, "tape", None),
            "source_timestamp": source_ts,
            "received_timestamp": received_ts,
            "data_age_seconds": float(data_age),
        }
        return payload


def _ensure_tz(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


