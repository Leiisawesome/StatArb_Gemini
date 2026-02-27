"""
Event-level filter for shadow trading system.

Applies spread_ratio filter, NBBO integrity checks, inventory cap check,
and staleness check on detected imbalance events. Implements the 200ms
entry delay measured from exchange_timestamp.

Spec: v1.7-SHADOW
Build Plan: v4-FINAL, Step 2
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional

from core_engine.microstructure.shadow.constants import (
    CLIP_SIZE,
    ENTRY_DELAY_MS,
    LOCKED_CROSSED_ALERT_RATE,
    MIN_QUOTE_UPDATES_IN_WINDOW,
    NET_INVENTORY_CAP_BPS,
    ODD_LOT_DOMINANCE_FLAG_PCT,
    QUOTE_STALENESS_MAX_MS,
    SHOCK_ONLY,
    SPREAD_RATIO_COMPETITIVE_MAX,
    SPREAD_RATIO_SHOCK_MIN,
)
from core_engine.microstructure.shadow.types import (
    ImbalanceEvent,
    NBBOIntegrityReport,
    Quote,
    SubStrategy,
    TradeSignal,
)

logger = logging.getLogger(__name__)


@dataclass
class _QuoteWindow:
    """Tracks recent quotes for staleness and integrity checks."""
    recent_quotes: Deque[Quote] = field(default_factory=lambda: deque(maxlen=500))
    total_evaluations: int = 0
    locked_crossed_rejections: int = 0
    stale_rejections: int = 0
    flickering_rejections: int = 0
    odd_lot_quotes: int = 0
    total_quotes_tracked: int = 0


class InventoryTracker:
    """Tracks net directional inventory across all open positions.

    Per v1.7 spec Section 4.1:
        net_inventory_bps = sum(position_direction × current_spread_bps)
    Each position's contribution is its spread at entry (directional).
    The ±6 bps cap limits aggregate directional risk to ~3 concurrent
    same-direction positions with typical spreads.
    """

    def __init__(self, portfolio_value: float) -> None:
        self._portfolio_value = portfolio_value
        self._positions: Dict[str, List[_InventoryEntry]] = {}

    def get_net_inventory_bps(self) -> float:
        total = 0.0
        for entries in self._positions.values():
            for e in entries:
                direction = 1.0 if e.side == "BUY" else -1.0
                total += direction * e.spread_bps
        return total

    def add_position(
        self, symbol: str, side: str, shares: int, price: float,
        spread_bps: float = 0.0,
    ) -> None:
        if symbol not in self._positions:
            self._positions[symbol] = []
        self._positions[symbol].append(
            _InventoryEntry(side=side, shares=shares, current_price=price,
                            spread_bps=spread_bps)
        )

    def remove_position(self, symbol: str, side: str) -> None:
        if symbol in self._positions:
            self._positions[symbol] = [
                e for e in self._positions[symbol] if e.side != side
            ]
            if not self._positions[symbol]:
                del self._positions[symbol]

    def update_price(self, symbol: str, price: float) -> None:
        if symbol in self._positions:
            for e in self._positions[symbol]:
                e.current_price = price

    def has_open_position(self, symbol: str) -> bool:
        return symbol in self._positions and len(self._positions[symbol]) > 0

    def position_count(self, symbol: str) -> int:
        return len(self._positions.get(symbol, []))

    def would_breach_cap(
        self, symbol: str, side: str, shares: int, price: float,
        spread_bps: float = 0.0,
    ) -> bool:
        """Check if adding a new position would breach the inventory cap."""
        current = self.get_net_inventory_bps()
        direction = 1.0 if side == "BUY" else -1.0
        delta = direction * spread_bps
        return abs(current + delta) > NET_INVENTORY_CAP_BPS


@dataclass
class _InventoryEntry:
    side: str
    shares: int
    current_price: float
    spread_bps: float = 0.0


class EventLevelFilter:
    """Applies spread_ratio filter, NBBO integrity, and inventory checks.

    For each ImbalanceEvent:
    1. Wait 200ms from exchange_timestamp (not system clock)
    2. Read current NBBO quote
    3. Check NBBO integrity (locked/crossed, staleness, flickering)
    4. Compute spread_ratio = current_spread / baseline_spread
    5. v1.8: SHOCK_ONLY — accept only if spread_ratio > 2.0
       (v1.7: accept if < 1.0 competitive or > 2.0 shock)
    6. Check net inventory cap (±6 bps)
    7. Check per-symbol position limit (max 1 open)
    """

    def __init__(self, inventory_tracker: InventoryTracker) -> None:
        self._inventory = inventory_tracker
        self._quote_windows: Dict[str, _QuoteWindow] = {}
        self._baseline_spreads: Dict[str, float] = {}

        # Statistics
        self._total_events: int = 0
        self._accepted: int = 0
        self._rejected_deadzone: int = 0
        self._rejected_inventory: int = 0
        self._rejected_position: int = 0
        self._rejected_nbbo: int = 0
        self._rejected_staleness: int = 0

    def set_baseline_spread(self, symbol: str, baseline: float) -> None:
        """Set the rolling 20-day median spread for a symbol."""
        self._baseline_spreads[symbol] = baseline

    def record_quote(self, quote: Quote) -> None:
        """Track incoming quotes for integrity monitoring."""
        symbol = quote.symbol
        if symbol not in self._quote_windows:
            self._quote_windows[symbol] = _QuoteWindow()
        w = self._quote_windows[symbol]
        w.recent_quotes.append(quote)
        w.total_quotes_tracked += 1

        if quote.bid_size < 100 or quote.ask_size < 100:
            w.odd_lot_quotes += 1

    def evaluate(
        self,
        event: ImbalanceEvent,
        current_quote: Quote,
    ) -> Optional[TradeSignal]:
        """Evaluate an imbalance event for trade signal generation.

        This is the synchronous core; the 200ms delay is handled by the engine.
        """
        self._total_events += 1
        symbol = event.symbol
        w = self._quote_windows.get(symbol, _QuoteWindow())
        w.total_evaluations += 1

        # 1. NBBO integrity: locked/crossed
        if current_quote.is_locked or current_quote.is_crossed:
            w.locked_crossed_rejections += 1
            self._rejected_nbbo += 1
            logger.debug("Rejected %s: locked/crossed market", symbol)
            return None

        # 2. Quote staleness
        quote_age_ms = (event.event_timestamp_ns + ENTRY_DELAY_MS * 1_000_000
                        - current_quote.timestamp_ns) / 1_000_000
        if quote_age_ms > QUOTE_STALENESS_MAX_MS:
            w.stale_rejections += 1
            self._rejected_staleness += 1
            logger.debug(
                "Rejected %s: stale quote (%.1fms > %dms)",
                symbol, quote_age_ms, QUOTE_STALENESS_MAX_MS,
            )
            return None

        # 3. Quote flickering (too few updates in 200ms window)
        entry_ts_ns = event.event_timestamp_ns + ENTRY_DELAY_MS * 1_000_000
        window_start_ns = event.event_timestamp_ns
        updates_in_window = sum(
            1 for q in w.recent_quotes
            if window_start_ns <= q.timestamp_ns <= entry_ts_ns
        )
        if updates_in_window < MIN_QUOTE_UPDATES_IN_WINDOW:
            w.flickering_rejections += 1
            self._rejected_nbbo += 1
            logger.debug(
                "Rejected %s: flickering (%d updates < %d required)",
                symbol, updates_in_window, MIN_QUOTE_UPDATES_IN_WINDOW,
            )
            return None

        # 4. Spread ratio computation
        baseline = self._baseline_spreads.get(symbol, 0.0)
        if baseline <= 0:
            logger.warning("No baseline spread for %s, using current spread", symbol)
            baseline = current_quote.spread
            if baseline <= 0:
                self._rejected_nbbo += 1
                return None

        spread_ratio = current_quote.spread / baseline

        # 5. Dead zone + shock-only filter
        if SHOCK_ONLY:
            if spread_ratio < SPREAD_RATIO_SHOCK_MIN:
                self._rejected_deadzone += 1
                logger.debug(
                    "Rejected %s: shock-only mode (spread_ratio=%.3f < %.1f)",
                    symbol, spread_ratio, SPREAD_RATIO_SHOCK_MIN,
                )
                return None
        elif SPREAD_RATIO_COMPETITIVE_MAX <= spread_ratio <= SPREAD_RATIO_SHOCK_MIN:
            self._rejected_deadzone += 1
            logger.debug(
                "Rejected %s: dead zone (spread_ratio=%.3f)",
                symbol, spread_ratio,
            )
            return None

        # 6. Per-symbol position limit
        if self._inventory.has_open_position(symbol):
            self._rejected_position += 1
            logger.debug("Rejected %s: position limit (already open)", symbol)
            return None

        # 7. Determine side (provide liquidity AGAINST imbalance)
        if event.flow_imbalance > 0:
            side = "SELL"
            limit_price = current_quote.ask_price
        else:
            side = "BUY"
            limit_price = current_quote.bid_price

        # 8. Inventory cap check
        entry_spread_bps = current_quote.spread_bps
        if self._inventory.would_breach_cap(
            symbol, side, CLIP_SIZE, limit_price, spread_bps=entry_spread_bps
        ):
            self._rejected_inventory += 1
            logger.debug(
                "Rejected %s: inventory cap would be breached (net=%.2f bps)",
                symbol, self._inventory.get_net_inventory_bps(),
            )
            return None

        sub_strategy = (
            SubStrategy.SHOCK if SHOCK_ONLY
            else (SubStrategy.COMPETITIVE if spread_ratio < SPREAD_RATIO_COMPETITIVE_MAX
                  else SubStrategy.SHOCK)
        )

        # Compute spread trajectory (at event_end, +100ms, +200ms)
        spread_t0 = event.ask_at_end - event.bid_at_end if event.bid_at_end > 0 else 0.0
        spread_trajectory = [
            spread_t0 / ((event.bid_at_end + event.ask_at_end) / 2) * 10_000 if event.bid_at_end > 0 else 0.0,
            current_quote.spread_bps,
            current_quote.spread_bps,
        ]

        self._accepted += 1

        signal = TradeSignal(
            symbol=symbol,
            event=event,
            sub_strategy=sub_strategy,
            side=side,
            limit_price=limit_price,
            spread_ratio=spread_ratio,
            baseline_spread=baseline,
            quote_at_entry=current_quote,
            quote_age_ms=quote_age_ms,
            entry_timestamp_ns=entry_ts_ns,
            spread_trajectory=spread_trajectory,
        )

        logger.info(
            "Signal accepted: %s %s spread_ratio=%.3f sub=%s side=%s price=%.2f",
            symbol, sub_strategy.value, spread_ratio, sub_strategy.value,
            side, limit_price,
        )

        return signal

    def get_nbbo_integrity_stats(self) -> NBBOIntegrityReport:
        """Aggregate NBBO integrity statistics across all symbols."""
        total_eval = sum(w.total_evaluations for w in self._quote_windows.values())
        total_lc = sum(w.locked_crossed_rejections for w in self._quote_windows.values())
        total_quotes = sum(w.total_quotes_tracked for w in self._quote_windows.values())
        total_odd = sum(w.odd_lot_quotes for w in self._quote_windows.values())

        locked_crossed_rate = total_lc / total_eval if total_eval > 0 else 0.0
        odd_lot_ratio = total_odd / total_quotes if total_quotes > 0 else 0.0

        per_symbol = {}
        for sym, w in self._quote_windows.items():
            if w.total_evaluations > 0:
                per_symbol[sym] = w.locked_crossed_rejections / w.total_evaluations

        return NBBOIntegrityReport(
            locked_crossed_rate=locked_crossed_rate,
            quote_update_frequency=0.0,  # computed by engine from quote stream
            odd_lot_dominance_ratio=odd_lot_ratio,
            locked_crossed_by_symbol=per_symbol,
        )

    @property
    def baseline_spreads(self) -> Dict[str, float]:
        return dict(self._baseline_spreads)

    def reset_daily(self) -> None:
        """Reset daily-scoped counters. Call after generating daily report."""
        self._total_events = 0
        self._accepted = 0
        self._rejected_deadzone = 0
        self._rejected_inventory = 0
        self._rejected_position = 0
        self._rejected_nbbo = 0
        self._rejected_staleness = 0

        for w in self._quote_windows.values():
            w.total_evaluations = 0
            w.locked_crossed_rejections = 0
            w.stale_rejections = 0
            w.flickering_rejections = 0
            w.odd_lot_quotes = 0
            w.total_quotes_tracked = 0

    @property
    def rejection_counts(self) -> Dict[str, int]:
        return {
            "total_events": self._total_events,
            "accepted": self._accepted,
            "rejected_deadzone": self._rejected_deadzone,
            "rejected_inventory": self._rejected_inventory,
            "rejected_position": self._rejected_position,
            "rejected_nbbo": self._rejected_nbbo,
            "rejected_staleness": self._rejected_staleness,
        }
