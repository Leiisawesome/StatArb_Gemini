"""
Real-Time P&L Tracker - Performance Monitoring System
Tracks mark-to-market P&L, intraday high-water mark, and strategy attribution.

Architecture Compliance (Tier-1 Rules):
- Rule 6: Operations & Recovery - Section 2 (Real-Time P&L Monitoring)
  - Tick-level P&L updates on every market data tick
  - Integration with Rule 3 circuit breakers (Phase 9)
  - Strategy and position attribution for Rule 4 analytics

P&L Tracking:
1. Unrealized P&L - Mark-to-market on every price tick
2. Realized P&L - Updated on position closes
3. Total P&L - Realized + Unrealized
4. Intraday High - Peak P&L during trading day
5. Drawdown - Current P&L - Intraday High
6. Position Attribution - P&L by symbol
7. Strategy Attribution - P&L by strategy

Update Frequency:
- Market Data Tick: Update unrealized P&L
- Position Close: Update realized P&L
- Every Second: Update aggregates
- Daily Reset: Reset intraday metrics

Integration with Circuit Breakers (Rule 3, Phase 9):
- Feeds daily P&L to circuit breaker loss limit (-2%)
- Feeds drawdown to circuit breaker drawdown limit (-5%)

Migration: December 2025 - Former Rule 7 content now Rule 6, Section 2.

Author: Trading System Team
Date: December 6, 2025
Version: 2.0 (Rules Migration)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class PnLSnapshot:
    """
    Point-in-time P&L snapshot

    Attributes:
        timestamp: Snapshot timestamp
        realized_pnl: Realized P&L (closed positions)
        unrealized_pnl: Unrealized P&L (mark-to-market)
        total_pnl: Total P&L (realized + unrealized)
        intraday_high: Intraday high-water mark
        current_drawdown: Current drawdown from high
        portfolio_value: Total portfolio value
    """
    timestamp: datetime
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    intraday_high: float
    current_drawdown: float
    portfolio_value: float

    # Attribution
    position_pnl: Dict[str, float] = field(default_factory=dict)
    strategy_pnl: Dict[str, float] = field(default_factory=dict)

class RealTimePnLTracker:
    """
    Real-Time P&L Tracker

    Monitors portfolio P&L in real-time with:
    - Tick-by-tick unrealized P&L updates
    - Position-level attribution
    - Strategy-level attribution
    - Intraday high-water mark tracking
    - Drawdown monitoring

    Integration: Called by CentralRiskManager on price updates and position changes
    """

    def __init__(self, risk_manager, config: Optional[Dict] = None):
        """
        Initialize P&L tracker

        Args:
            risk_manager: CentralRiskManager instance
            config: Configuration dictionary
        """
        self.risk_manager = risk_manager
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # P&L State
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.total_pnl = 0.0

        # Intraday Tracking
        self.intraday_high = 0.0
        self.intraday_high_timestamp: Optional[datetime] = None
        self.current_drawdown = 0.0

        # Attribution
        self.position_pnl: Dict[str, float] = {}  # symbol → P&L
        self.strategy_pnl: Dict[str, float] = {}  # strategy_id → P&L
        self.position_cost_basis: Dict[str, float] = {}  # symbol → avg cost
        self.position_strategy_map: Dict[str, str] = {}  # symbol → strategy_id

        # History
        self.pnl_history: List[PnLSnapshot] = []
        self.max_history_size = self.config.get('max_history_size', 1000)

        # Daily Reset
        self.last_reset_date = datetime.now().date()
        self.daily_start_value: Optional[float] = None

        # Statistics
        self.total_updates = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        self.logger.info("✅ RealTimePnLTracker initialized")
        self.logger.info(f"   Max History Size: {self.max_history_size}")

    def set_risk_manager(self, risk_manager) -> None:
        """
        Inject the risk manager after construction.

        This is needed because in backtest mode, the P&L tracker is created
        before the CentralRiskManager, so we inject it after both are created.

        Args:
            risk_manager: CentralRiskManager instance
        """
        self.risk_manager = risk_manager
        self.logger.info("✅ RiskManager injected into RealTimePnLTracker")

    async def update_market_data(self, symbol: str, price: float, timestamp: datetime):
        """
        Update P&L based on new market price

        Called on every price tick for held positions

        Args:
            symbol: Trading symbol
            price: Current market price
            timestamp: Price timestamp
        """
        self.total_updates += 1

        # Check if daily reset needed
        await self._check_daily_reset()

        # Update unrealized P&L for this position
        if symbol in self.risk_manager.current_positions:
            position = self.risk_manager.current_positions[symbol]

            if abs(position) > 0.001:  # Has position
                # Calculate P&L
                cost_basis = self.position_cost_basis.get(symbol, price)
                position_pnl = (price - cost_basis) * position

                # Update position P&L
                old_pnl = self.position_pnl.get(symbol, 0.0)
                self.position_pnl[symbol] = position_pnl

                # Update total unrealized P&L
                self.unrealized_pnl += (position_pnl - old_pnl)

                # Note: Strategy P&L is only updated on position close (realized P&L)

        # Update total P&L
        self._update_total_pnl()

        # Update intraday high
        self._update_intraday_high(timestamp)

        # Log periodically (every 100 updates)
        if self.total_updates % 100 == 0:
            self.logger.debug(
                f"P&L Update #{self.total_updates}: "
                f"Realized: ${self.realized_pnl:,.0f}, "
                f"Unrealized: ${self.unrealized_pnl:,.0f}, "
                f"Total: ${self.total_pnl:,.0f}, "
                f"Drawdown: {self.current_drawdown:.2%}"
            )

    async def update_position_close(
        self,
        symbol: str,
        quantity: float,
        exit_price: float,
        strategy_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Update P&L when position is closed

        Called by CentralRiskManager when positions are closed

        Args:
            symbol: Trading symbol
            quantity: Quantity closed (always positive)
            exit_price: Exit price
            strategy_id: Strategy that closed the position
            timestamp: Close timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.total_trades += 1

        # Calculate realized P&L
        cost_basis = self.position_cost_basis.get(symbol, exit_price)
        trade_pnl = (exit_price - cost_basis) * quantity

        # Update realized P&L
        self.realized_pnl += trade_pnl

        # Update statistics
        if trade_pnl > 0:
            self.winning_trades += 1
        elif trade_pnl < 0:
            self.losing_trades += 1

        # Update strategy attribution
        if strategy_id:
            self.strategy_pnl[strategy_id] = self.strategy_pnl.get(strategy_id, 0.0) + trade_pnl

        # Update position P&L (remove unrealized, add to realized)
        if symbol in self.position_pnl:
            unrealized_before = self.position_pnl[symbol]
            self.unrealized_pnl -= unrealized_before
            del self.position_pnl[symbol]

        # Update total P&L
        self._update_total_pnl()

        # Update intraday high
        self._update_intraday_high(timestamp)

        self.logger.info(
            f"💰 Position closed: {symbol} | "
            f"Qty: {quantity:.2f} @ ${exit_price:.2f} | "
            f"Trade P&L: ${trade_pnl:,.0f} | "
            f"Total P&L: ${self.total_pnl:,.0f}"
        )

    async def update_position_entry(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        strategy_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Update tracking when new position is entered

        Args:
            symbol: Trading symbol
            quantity: Position quantity
            entry_price: Entry price
            strategy_id: Strategy opening the position
            timestamp: Entry timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Update cost basis
        # Get position BEFORE this entry was added (subtract quantity to get prior position)
        current_position_after = self.risk_manager.current_positions.get(symbol, 0.0)
        prior_position = current_position_after - quantity

        if symbol in self.position_cost_basis and abs(prior_position) > 0.001:
            # Adding to existing position - use averaging logic
            current_cost = self.position_cost_basis[symbol]

            # Calculate new average cost
            total_cost = (current_cost * prior_position) + (entry_price * quantity)
            new_position = prior_position + quantity
            self.position_cost_basis[symbol] = total_cost / new_position if abs(new_position) > 0.001 else entry_price
        else:
            # NEW position (prior was 0 or no prior cost basis) - use entry price directly
            self.position_cost_basis[symbol] = entry_price

        # Map position to strategy
        if strategy_id:
            self.position_strategy_map[symbol] = strategy_id

        self.logger.info(
            f"📈 Position entry: {symbol} | "
            f"Qty: {quantity:.2f} @ ${entry_price:.2f} | "
            f"Cost Basis: ${self.position_cost_basis[symbol]:.2f}"
        )

    def _update_total_pnl(self):
        """Update total P&L"""
        self.total_pnl = self.realized_pnl + self.unrealized_pnl

    def _update_intraday_high(self, timestamp: datetime):
        """Update intraday high-water mark"""
        if self.total_pnl > self.intraday_high:
            self.intraday_high = self.total_pnl
            self.intraday_high_timestamp = timestamp
            self.current_drawdown = 0.0
        else:
            # Calculate drawdown from high
            if self.intraday_high > 0:
                self.current_drawdown = (self.total_pnl - self.intraday_high) / self.intraday_high
            else:
                self.current_drawdown = 0.0

    async def _check_daily_reset(self):
        """Check if daily reset is needed"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            await self.daily_reset()

    async def daily_reset(self):
        """Reset daily tracking (call at start of trading day)"""
        self.logger.info("📅 Daily P&L reset: Resetting intraday metrics")

        # Reset intraday metrics
        self.intraday_high = self.total_pnl
        self.intraday_high_timestamp = datetime.now()
        self.current_drawdown = 0.0

        # Set daily start value
        self.daily_start_value = self.risk_manager.portfolio_value

        self.last_reset_date = datetime.now().date()

    def get_current_snapshot(self) -> PnLSnapshot:
        """Get current P&L snapshot"""
        snapshot = PnLSnapshot(
            timestamp=datetime.now(),
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
            total_pnl=self.total_pnl,
            intraday_high=self.intraday_high,
            current_drawdown=self.current_drawdown,
            portfolio_value=self.risk_manager.portfolio_value,
            position_pnl=dict(self.position_pnl),
            strategy_pnl=dict(self.strategy_pnl)
        )

        # Add to history
        self.pnl_history.append(snapshot)

        # Maintain history size
        if len(self.pnl_history) > self.max_history_size:
            self.pnl_history = self.pnl_history[-self.max_history_size:]

        return snapshot

    def get_position_pnl(self, symbol: str) -> float:
        """Get P&L for specific position"""
        return self.position_pnl.get(symbol, 0.0)

    def get_strategy_pnl(self, strategy_id: str) -> float:
        """Get P&L for specific strategy"""
        return self.strategy_pnl.get(strategy_id, 0.0)

    def get_top_positions(self, count: int = 10) -> List[tuple]:
        """
        Get top positions by P&L

        Returns:
            List of (symbol, pnl) tuples sorted by P&L
        """
        sorted_positions = sorted(
            self.position_pnl.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_positions[:count]

    def get_bottom_positions(self, count: int = 10) -> List[tuple]:
        """
        Get worst positions by P&L

        Returns:
            List of (symbol, pnl) tuples sorted by P&L (worst first)
        """
        sorted_positions = sorted(
            self.position_pnl.items(),
            key=lambda x: x[1]
        )
        return sorted_positions[:count]

    # Statistics and Reporting

    def get_pnl_statistics(self) -> Dict:
        """Get P&L statistics"""
        win_rate = self.winning_trades / max(1, self.total_trades)

        return {
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'total_pnl': self.total_pnl,
            'intraday_high': self.intraday_high,
            'current_drawdown': self.current_drawdown,
            'current_drawdown_pct': self.current_drawdown,
            'portfolio_value': self.risk_manager.portfolio_value,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'avg_win': self.realized_pnl / max(1, self.winning_trades) if self.winning_trades > 0 else 0,
            'total_updates': self.total_updates,
            'positions_tracked': len(self.position_pnl),
            'strategies_tracked': len(self.strategy_pnl)
        }

    def generate_pnl_report(self) -> str:
        """Generate P&L report"""
        stats = self.get_pnl_statistics()

        report = [
            "=" * 60,
            "REAL-TIME P&L REPORT",
            "=" * 60,
            f"Portfolio Value:       ${stats['portfolio_value']:,.0f}",
            "",
            "P&L BREAKDOWN:",
            f"  Realized P&L:        ${stats['realized_pnl']:,.0f}",
            f"  Unrealized P&L:      ${stats['unrealized_pnl']:,.0f}",
            f"  Total P&L:           ${stats['total_pnl']:,.0f}",
            "",
            "INTRADAY METRICS:",
            f"  Intraday High:       ${stats['intraday_high']:,.0f}",
            f"  Current Drawdown:    {stats['current_drawdown_pct']:.2%}",
            "",
            "TRADING STATISTICS:",
            f"  Total Trades:        {stats['total_trades']:,}",
            f"  Winning Trades:      {stats['winning_trades']:,}",
            f"  Losing Trades:       {stats['losing_trades']:,}",
            f"  Win Rate:            {stats['win_rate']:.1%}",
            f"  Avg Win:             ${stats['avg_win']:,.0f}",
            "",
            "ATTRIBUTION:",
            f"  Positions Tracked:   {stats['positions_tracked']}",
            f"  Strategies Tracked:  {stats['strategies_tracked']}",
            ""
        ]

        # Top positions
        if self.position_pnl:
            report.append("TOP POSITIONS (P&L):")
            top_positions = self.get_top_positions(5)
            for symbol, pnl in top_positions:
                report.append(f"  {symbol:8s}: ${pnl:>10,.0f}")
            report.append("")

        # Strategy attribution
        if self.strategy_pnl:
            report.append("STRATEGY ATTRIBUTION:")
            sorted_strategies = sorted(
                self.strategy_pnl.items(),
                key=lambda x: x[1],
                reverse=True
            )
            for strategy_id, pnl in sorted_strategies[:5]:
                report.append(f"  {strategy_id:30s}: ${pnl:>10,.0f}")
            report.append("")

        report.append("=" * 60)

        return "\n".join(report)

    def get_pnl_series(self, minutes: int = 60) -> List[PnLSnapshot]:
        """
        Get P&L time series for last N minutes

        Args:
            minutes: Number of minutes to look back

        Returns:
            List of PnL snapshots
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        return [
            snapshot for snapshot in self.pnl_history
            if snapshot.timestamp >= cutoff_time
        ]

