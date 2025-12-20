"""
RiskBudgetState - Daily/Per-Trade Risk Budget Tracking
======================================================

Tracks risk budget consumption for P&L-aware risk management:
- Daily risk budget (total $ at risk per day)
- Per-trade risk limits
- Used vs available risk budget
- Integration with position stops

Design (from plan Section 5.7 - Gate 5):
- max_loss_this_trade = candidate_quantity × per_share_loss
- daily_risk_budget = portfolio_value × daily_risk_budget_pct
- used_risk_budget = sum(max_loss for open positions with stops)
- available_risk = daily_risk_budget - used_risk_budget

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 3)
"""

from dataclasses import dataclass
from datetime import datetime, date, timezone
from typing import Any, Dict, Optional
import logging
import threading

logger = logging.getLogger(__name__)

@dataclass
class PositionRisk:
    """Risk information for a single position."""
    symbol: str
    side: str  # 'long' or 'short'
    quantity: float
    entry_price: float
    effective_stop_price: float
    max_loss: float  # quantity × |entry - stop|
    opened_at: datetime
    strategy_id: str = ""

@dataclass
class RiskBudgetSnapshot:
    """Snapshot of risk budget state at a point in time."""
    timestamp: datetime
    portfolio_value: float
    daily_risk_budget: float
    used_risk_budget: float
    available_risk: float
    per_trade_limit: float
    positions_at_risk: int
    daily_risk_budget_pct: float
    per_trade_risk_pct: float

class RiskBudgetState:
    """
    Tracks risk budget consumption for position sizing decisions.

    Features:
    - Daily risk budget tracking (resets at market open)
    - Per-position max loss tracking
    - Available risk calculation for new trades
    - Integration with stop prices for accurate risk

    Thread-safe for concurrent position updates.
    """

    def __init__(
        self,
        daily_risk_budget_pct: float = 0.01,  # 1% of portfolio per day
        per_trade_risk_pct: float = 0.005,    # 0.5% per trade
    ):
        """
        Initialize risk budget state.

        Args:
            daily_risk_budget_pct: Max % of portfolio at risk per day
            per_trade_risk_pct: Max % of portfolio at risk per trade
        """
        self._daily_risk_pct = daily_risk_budget_pct
        self._per_trade_pct = per_trade_risk_pct

        # Current portfolio value (updated externally)
        self._portfolio_value: float = 0.0

        # Position risk tracking
        self._positions: Dict[str, PositionRisk] = {}

        # Current trading day
        self._current_date: Optional[date] = None

        # Daily realized losses (for budget tracking)
        self._daily_realized_loss: float = 0.0

        # Lock for thread safety
        # NOTE: This must be re-entrant because some methods call other methods that also acquire the lock.
        # Using a non-reentrant Lock would deadlock (e.g., check_trade_risk -> get_available_risk -> get_used_risk_budget).
        self._lock = threading.RLock()

        # Stats
        self._stats = {
            'positions_tracked': 0,
            'trades_sized_down': 0,
            'trades_rejected': 0,
            'budget_resets': 0,
        }

    def update_portfolio_value(self, value: float) -> None:
        """Update current portfolio value."""
        with self._lock:
            self._portfolio_value = value

    def get_portfolio_value(self) -> float:
        """Get current portfolio value."""
        return self._portfolio_value

    def _check_date_reset(self) -> None:
        """Check if we need to reset for a new trading day."""
        today = date.today()
        if self._current_date != today:
            self._daily_realized_loss = 0.0
            self._current_date = today
            self._stats['budget_resets'] += 1
            logger.info(f"Risk budget reset for new trading day: {today}")

    def add_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_price: float,
        strategy_id: str = "",
    ) -> None:
        """
        Add or update a position's risk tracking.

        Args:
            symbol: Position symbol
            side: 'long' or 'short'
            quantity: Position size
            entry_price: Entry/fill price
            stop_price: Stop price for max loss calculation
            strategy_id: Strategy that opened position
        """
        with self._lock:
            self._check_date_reset()

            # Calculate max loss
            if side == 'long':
                per_share_loss = max(0, entry_price - stop_price)
            else:
                per_share_loss = max(0, stop_price - entry_price)

            max_loss = quantity * per_share_loss

            position = PositionRisk(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                effective_stop_price=stop_price,
                max_loss=max_loss,
                opened_at=datetime.now(timezone.utc),
                strategy_id=strategy_id,
            )

            self._positions[symbol] = position
            self._stats['positions_tracked'] = len(self._positions)

            logger.debug(
                f"Position risk tracked: {symbol} {side} {quantity} @ {entry_price}, "
                f"stop={stop_price}, max_loss=${max_loss:.2f}"
            )

    def update_position_stop(self, symbol: str, new_stop: float) -> None:
        """Update stop price for a position (trailing stop, etc.)."""
        with self._lock:
            if symbol not in self._positions:
                return

            pos = self._positions[symbol]

            # Recalculate max loss
            if pos.side == 'long':
                per_share_loss = max(0, pos.entry_price - new_stop)
            else:
                per_share_loss = max(0, new_stop - pos.entry_price)

            pos.effective_stop_price = new_stop
            pos.max_loss = pos.quantity * per_share_loss

    def remove_position(self, symbol: str, realized_pnl: float = 0.0) -> None:
        """
        Remove a closed position from tracking.

        Args:
            symbol: Position symbol
            realized_pnl: Realized P&L from closing (negative = loss)
        """
        with self._lock:
            if symbol in self._positions:
                del self._positions[symbol]
                self._stats['positions_tracked'] = len(self._positions)

            # Track realized losses for daily budget
            if realized_pnl < 0:
                self._daily_realized_loss += abs(realized_pnl)

    def get_used_risk_budget(self) -> float:
        """Get total risk budget currently in use (sum of position max losses)."""
        with self._lock:
            self._check_date_reset()
            return sum(pos.max_loss for pos in self._positions.values())

    def get_daily_risk_budget(self) -> float:
        """Get total daily risk budget in dollars."""
        return self._portfolio_value * self._daily_risk_pct

    def get_available_risk(self) -> float:
        """Get remaining risk budget for new trades."""
        daily_budget = self.get_daily_risk_budget()
        used = self.get_used_risk_budget()
        realized = self._daily_realized_loss
        return max(0, daily_budget - used - realized)

    def get_per_trade_limit(self) -> float:
        """Get max risk allowed for a single trade."""
        return self._portfolio_value * self._per_trade_pct

    def check_trade_risk(
        self,
        candidate_quantity: float,
        estimated_fill_price: float,
        effective_stop_price: float,
        side: str,
    ) -> Dict[str, Any]:
        """
        Check if a proposed trade fits within risk budget.

        Args:
            candidate_quantity: Proposed trade size
            estimated_fill_price: Expected fill price
            effective_stop_price: Stop price for risk calculation
            side: 'buy'/'long' or 'sell'/'short'

        Returns:
            Dict with:
            - allowed: bool - Whether trade is allowed
            - max_quantity: float - Max quantity within budget
            - resize_reason: str - If resized, why
            - max_loss: float - Max loss for proposed trade
        """
        with self._lock:
            self._check_date_reset()

            # Calculate per-share loss
            if side in ('buy', 'long'):
                per_share_loss = max(0, estimated_fill_price - effective_stop_price)
            else:
                per_share_loss = max(0, effective_stop_price - estimated_fill_price)

            max_loss = candidate_quantity * per_share_loss

            available = self.get_available_risk()
            per_trade_limit = self.get_per_trade_limit()

            result = {
                'allowed': True,
                'max_quantity': candidate_quantity,
                'resize_reason': '',
                'max_loss': max_loss,
                'available_risk': available,
                'per_trade_limit': per_trade_limit,
            }

            # Check per-trade limit
            if max_loss > per_trade_limit:
                if per_share_loss > 0:
                    max_qty = per_trade_limit / per_share_loss
                    result['max_quantity'] = min(result['max_quantity'], max_qty)
                    result['resize_reason'] = f"Per-trade limit: ${per_trade_limit:.2f}"
                    self._stats['trades_sized_down'] += 1

            # Check daily budget
            if max_loss > available:
                if per_share_loss > 0:
                    max_qty = available / per_share_loss
                    result['max_quantity'] = min(result['max_quantity'], max_qty)
                    result['resize_reason'] = f"Daily budget: ${available:.2f} available"
                    self._stats['trades_sized_down'] += 1

            # If max_quantity is too small, reject
            if result['max_quantity'] <= 0:
                result['allowed'] = False
                result['resize_reason'] = "No risk budget available"
                self._stats['trades_rejected'] += 1

            return result

    def get_snapshot(self) -> RiskBudgetSnapshot:
        """Get current risk budget state snapshot."""
        with self._lock:
            self._check_date_reset()
            return RiskBudgetSnapshot(
                timestamp=datetime.now(timezone.utc),
                portfolio_value=self._portfolio_value,
                daily_risk_budget=self.get_daily_risk_budget(),
                used_risk_budget=self.get_used_risk_budget(),
                available_risk=self.get_available_risk(),
                per_trade_limit=self.get_per_trade_limit(),
                positions_at_risk=len(self._positions),
                daily_risk_budget_pct=self._daily_risk_pct,
                per_trade_risk_pct=self._per_trade_pct,
            )

    def get_position_risks(self) -> Dict[str, PositionRisk]:
        """Get all tracked position risks."""
        with self._lock:
            return dict(self._positions)

    def get_stats(self) -> Dict[str, int]:
        """Get risk budget statistics."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset statistics."""
        for key in self._stats:
            self._stats[key] = 0

    def get_state_for_checkpoint(self) -> Dict[str, Any]:
        """Get state for checkpointing."""
        with self._lock:
            return {
                'daily_risk_pct': self._daily_risk_pct,
                'per_trade_pct': self._per_trade_pct,
                'portfolio_value': self._portfolio_value,
                'current_date': self._current_date.isoformat() if self._current_date else None,
                'daily_realized_loss': self._daily_realized_loss,
                'positions': {
                    sym: {
                        'side': pos.side,
                        'quantity': pos.quantity,
                        'entry_price': pos.entry_price,
                        'effective_stop_price': pos.effective_stop_price,
                        'max_loss': pos.max_loss,
                        'opened_at': pos.opened_at.isoformat(),
                        'strategy_id': pos.strategy_id,
                    }
                    for sym, pos in self._positions.items()
                }
            }

    def restore_from_checkpoint(self, state: Dict[str, Any]) -> None:
        """Restore state from checkpoint."""
        with self._lock:
            self._daily_risk_pct = state.get('daily_risk_pct', self._daily_risk_pct)
            self._per_trade_pct = state.get('per_trade_pct', self._per_trade_pct)
            self._portfolio_value = state.get('portfolio_value', 0.0)

            current_date_str = state.get('current_date')
            self._current_date = date.fromisoformat(current_date_str) if current_date_str else None

            self._daily_realized_loss = state.get('daily_realized_loss', 0.0)

            self._positions.clear()
            for sym, pos_data in state.get('positions', {}).items():
                self._positions[sym] = PositionRisk(
                    symbol=sym,
                    side=pos_data['side'],
                    quantity=pos_data['quantity'],
                    entry_price=pos_data['entry_price'],
                    effective_stop_price=pos_data['effective_stop_price'],
                    max_loss=pos_data['max_loss'],
                    opened_at=datetime.fromisoformat(pos_data['opened_at']),
                    strategy_id=pos_data.get('strategy_id', ''),
                )

            logger.info(
                f"Restored risk budget state: {len(self._positions)} positions, "
                f"${self._daily_realized_loss:.2f} realized loss"
            )

