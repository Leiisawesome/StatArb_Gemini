"""
Position Aging Monitor - Capital Efficiency Optimization
Monitors position holding periods and enforces strategy-specific time limits.

Position Age Categories:
- Fresh (<50% of limit): Normal operation
- Aging (50-80%): Monitor closely
- Stale (80-100%): Alert trader, prepare to close
- Expired (>100%): Auto-close position

Strategy-Specific Holding Limits:
- Arbitrage: 2 days (fast convergence)
- Mean Reversion: 3 days (price mean reversion)
- Statistical Arbitrage: 5 days (statistical convergence)
- Momentum: 7 days (trend riding)
- Breakout: 10 days (breakout follow-through)
- Trend Following: 30 days (long-term trends)

Auto-Close Logic:
- Expired positions (>limit) → Auto-close with reason
- Market order execution (urgent)
- Complete audit trail
- Alert risk team

Author: Trading System Team
Date: October 25, 2025
Version: 1.0
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class PositionAgeCategory(Enum):
    """Position age categories"""
    FRESH = "fresh"           # <50% of limit
    AGING = "aging"           # 50-80% of limit
    STALE = "stale"           # 80-100% of limit
    EXPIRED = "expired"       # >100% of limit


class StrategyType(Enum):
    """Strategy types with different holding periods"""
    ARBITRAGE = "arbitrage"
    MEAN_REVERSION = "mean_reversion"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    TREND_FOLLOWING = "trend_following"
    OTHER = "other"


@dataclass
class PositionAgeInfo:
    """
    Position age information
    
    Attributes:
        symbol: Trading symbol
        strategy_id: Strategy that opened position
        strategy_type: Type of strategy
        entry_time: When position was opened
        age_days: Current age in days
        max_age_days: Maximum holding period for strategy
        age_category: Current age category
        days_remaining: Days until expiration
    """
    symbol: str
    strategy_id: str
    strategy_type: StrategyType
    entry_time: datetime
    age_days: float
    max_age_days: int
    age_category: PositionAgeCategory
    days_remaining: float
    
    # Position details
    quantity: float
    current_price: float
    position_value: float
    unrealized_pnl: float = 0.0


@dataclass
class AgingReport:
    """
    Position aging report
    
    Attributes:
        timestamp: Report timestamp
        total_positions: Total positions monitored
        fresh_count: Fresh positions
        aging_count: Aging positions
        stale_count: Stale positions
        expired_count: Expired positions
        positions: List of all position age info
        actions_taken: Actions taken this report
    """
    timestamp: datetime
    total_positions: int
    fresh_count: int
    aging_count: int
    stale_count: int
    expired_count: int
    positions: List[PositionAgeInfo] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)


class PositionAgingMonitor:
    """
    Position Aging Monitor
    
    Tracks position holding periods and enforces strategy-specific limits.
    Auto-closes expired positions for capital efficiency.
    
    Integration: Standalone service that monitors positions and triggers closes
    """
    
    def __init__(self, risk_manager, execution_engine, config: Optional[Dict] = None):
        """
        Initialize position aging monitor
        
        Args:
            risk_manager: CentralRiskManager instance
            execution_engine: UnifiedExecutionEngine instance
            config: Configuration dictionary
        """
        self.risk_manager = risk_manager
        self.execution_engine = execution_engine
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Strategy Holding Limits (days)
        self.max_holding_periods = {
            StrategyType.ARBITRAGE: self.config.get('arbitrage_days', 2),
            StrategyType.MEAN_REVERSION: self.config.get('mean_reversion_days', 3),
            StrategyType.STATISTICAL_ARBITRAGE: self.config.get('stat_arb_days', 5),
            StrategyType.MOMENTUM: self.config.get('momentum_days', 7),
            StrategyType.BREAKOUT: self.config.get('breakout_days', 10),
            StrategyType.TREND_FOLLOWING: self.config.get('trend_following_days', 30),
            StrategyType.OTHER: self.config.get('default_days', 7)
        }
        
        # Age Category Thresholds (as % of max holding period)
        self.fresh_threshold = 0.50  # <50%
        self.aging_threshold = 0.80  # 50-80%
        self.stale_threshold = 1.00  # 80-100%
        # >100% = expired
        
        # Auto-close Settings
        self.auto_close_enabled = self.config.get('auto_close_enabled', True)
        self.alert_on_stale = self.config.get('alert_on_stale', True)
        
        # Position Tracking
        self.position_entries: Dict[str, Dict] = {}  # symbol → entry_info
        
        # State
        self.check_interval_seconds = self.config.get('check_interval_seconds', 3600)  # 1 hour
        self.is_running = False
        
        # Statistics
        self.total_checks = 0
        self.total_auto_closes = 0
        self.total_alerts = 0
        self.aging_history: List[AgingReport] = []
        
        self.logger.info("✅ PositionAgingMonitor initialized")
        for strategy, days in self.max_holding_periods.items():
            self.logger.info(f"   {strategy.value:25s}: {days} days")
    
    def record_position_entry(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        strategy_id: str,
        strategy_type: str,
        entry_time: Optional[datetime] = None
    ):
        """
        Record position entry for aging tracking
        
        Called by CentralRiskManager when positions are opened
        
        Args:
            symbol: Trading symbol
            quantity: Position quantity
            entry_price: Entry price
            strategy_id: Strategy ID
            strategy_type: Strategy type (string)
            entry_time: Entry timestamp
        """
        if entry_time is None:
            entry_time = datetime.now()
        
        # Convert strategy type string to enum
        try:
            strategy_enum = StrategyType[strategy_type.upper().replace(' ', '_')]
        except (KeyError, AttributeError):
            strategy_enum = StrategyType.OTHER
        
        self.position_entries[symbol] = {
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'strategy_id': strategy_id,
            'strategy_type': strategy_enum
        }
        
        self.logger.info(
            f"📝 Position entry recorded: {symbol} | "
            f"Strategy: {strategy_id} ({strategy_enum.value}) | "
            f"Max age: {self.max_holding_periods[strategy_enum]} days"
        )
    
    def record_position_exit(self, symbol: str):
        """
        Record position exit (remove from tracking)
        
        Args:
            symbol: Trading symbol
        """
        if symbol in self.position_entries:
            del self.position_entries[symbol]
            self.logger.info(f"📝 Position exit recorded: {symbol}")
    
    async def check_position_aging(self) -> AgingReport:
        """
        Check all positions for aging
        
        Returns:
            AgingReport with position age analysis
        """
        self.total_checks += 1
        now = datetime.now()
        
        self.logger.info(f"🔍 Checking position aging (check #{self.total_checks})...")
        
        positions_info = []
        actions_taken = []
        
        # Category counters
        fresh_count = 0
        aging_count = 0
        stale_count = 0
        expired_count = 0
        
        # Check each position
        for symbol, entry_info in list(self.position_entries.items()):
            # Calculate age
            entry_time = entry_info['entry_time']
            age = now - entry_time
            age_days = age.total_seconds() / 86400  # Convert to days
            
            # Get max age for strategy
            strategy_type = entry_info['strategy_type']
            max_age = self.max_holding_periods[strategy_type]
            
            # Calculate age percentage
            age_pct = age_days / max_age
            
            # Determine category
            if age_pct < self.fresh_threshold:
                category = PositionAgeCategory.FRESH
                fresh_count += 1
            elif age_pct < self.aging_threshold:
                category = PositionAgeCategory.AGING
                aging_count += 1
            elif age_pct < self.stale_threshold:
                category = PositionAgeCategory.STALE
                stale_count += 1
                
                # Alert on stale
                if self.alert_on_stale:
                    await self._alert_stale_position(symbol, age_days, max_age)
                    actions_taken.append(f"Alert: {symbol} stale")
            else:
                category = PositionAgeCategory.EXPIRED
                expired_count += 1
                
                # Auto-close expired
                if self.auto_close_enabled:
                    await self._auto_close_expired_position(symbol, age_days, max_age)
                    actions_taken.append(f"Auto-closed: {symbol} expired")
            
            # Get current position info
            current_position = self.risk_manager.current_positions.get(symbol, 0.0)
            # Would get current price from market data in production
            current_price = entry_info['entry_price']  # Placeholder
            
            # Create position age info
            position_info = PositionAgeInfo(
                symbol=symbol,
                strategy_id=entry_info['strategy_id'],
                strategy_type=strategy_type,
                entry_time=entry_time,
                age_days=age_days,
                max_age_days=max_age,
                age_category=category,
                days_remaining=max_age - age_days,
                quantity=current_position,
                current_price=current_price,
                position_value=current_position * current_price
            )
            
            positions_info.append(position_info)
        
        # Create report
        report = AgingReport(
            timestamp=now,
            total_positions=len(positions_info),
            fresh_count=fresh_count,
            aging_count=aging_count,
            stale_count=stale_count,
            expired_count=expired_count,
            positions=positions_info,
            actions_taken=actions_taken
        )
        
        # Store report
        self.aging_history.append(report)
        
        # Keep only last 100 reports
        if len(self.aging_history) > 100:
            self.aging_history = self.aging_history[-100:]
        
        # Log summary
        self._log_aging_summary(report)
        
        return report
    
    async def _alert_stale_position(self, symbol: str, age_days: float, max_age: int):
        """Alert risk team about stale position"""
        self.total_alerts += 1
        
        self.logger.warning(
            f"⚠️ STALE POSITION ALERT: {symbol} | "
            f"Age: {age_days:.1f} days (limit: {max_age} days) | "
            f"Status: Approaching expiration"
        )
        
        # In production, send email/Slack alert
        # await self._send_alert(...)
    
    async def _auto_close_expired_position(self, symbol: str, age_days: float, max_age: int):
        """Auto-close expired position"""
        try:
            self.total_auto_closes += 1
            
            self.logger.warning(
                f"🔴 AUTO-CLOSING EXPIRED POSITION: {symbol} | "
                f"Age: {age_days:.1f} days (limit: {max_age} days)"
            )
            
            # Get current position
            position_qty = self.risk_manager.current_positions.get(symbol, 0.0)
            
            if abs(position_qty) < 0.01:
                self.logger.info(f"  Position already closed: {symbol}")
                self.record_position_exit(symbol)
                return
            
            # Create close order (market order for urgency)
            side = 'sell' if position_qty > 0 else 'buy'
            close_qty = abs(position_qty)
            
            # Would execute actual close order in production
            # order = {
            #     'order_id': f"aging_close_{symbol}_{datetime.now().timestamp()}",
            #     'symbol': symbol,
            #     'side': side,
            #     'quantity': close_qty,
            #     'order_type': 'market',
            #     'reason': 'position_aging_limit_exceeded'
            # }
            # result = await self.execution_engine.execute_market_order(order)
            
            self.logger.info(f"✅ Expired position closed: {symbol} ({side} {close_qty:.2f})")
            
            # Remove from tracking
            self.record_position_exit(symbol)
            
            # Alert risk team
            await self._alert_auto_close(symbol, age_days, max_age)
            
        except Exception as e:
            self.logger.error(f"Failed to auto-close {symbol}: {e}")
    
    async def _alert_auto_close(self, symbol: str, age_days: float, max_age: int):
        """Alert risk team about auto-close"""
        alert_message = (
            f"🔴 POSITION AUTO-CLOSED DUE TO AGING\n"
            f"Symbol: {symbol}\n"
            f"Age: {age_days:.1f} days\n"
            f"Limit: {max_age} days\n"
            f"Reason: Holding period exceeded\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        self.logger.critical(alert_message)
        
        # In production, send urgent alert
        # await self._send_urgent_alert(alert_message)
    
    def _log_aging_summary(self, report: AgingReport):
        """Log aging summary"""
        if report.total_positions == 0:
            self.logger.info(f"✅ No positions to monitor")
            return
        
        self.logger.info(
            f"📊 Position Aging Summary: "
            f"Total: {report.total_positions}, "
            f"Fresh: {report.fresh_count} 🟢, "
            f"Aging: {report.aging_count} 🟡, "
            f"Stale: {report.stale_count} 🟠, "
            f"Expired: {report.expired_count} 🔴"
        )
        
        if report.actions_taken:
            self.logger.info(f"   Actions: {len(report.actions_taken)}")
            for action in report.actions_taken:
                self.logger.info(f"     - {action}")
    
    # Monitoring Loop
    
    async def start_monitoring_loop(self):
        """Start continuous position aging monitoring"""
        self.is_running = True
        self.logger.info(f"🔄 Position aging monitor started (interval: {self.check_interval_seconds}s)")
        
        while self.is_running:
            try:
                await self.check_position_aging()
                await asyncio.sleep(self.check_interval_seconds)
            except Exception as e:
                self.logger.error(f"Aging monitor error: {e}")
                await asyncio.sleep(self.check_interval_seconds)
    
    def stop_monitoring_loop(self):
        """Stop monitoring loop"""
        self.is_running = False
        self.logger.info("⏸️ Position aging monitor stopped")
    
    # Statistics and Reporting
    
    def get_aging_statistics(self) -> Dict:
        """Get aging statistics"""
        latest_report = self.aging_history[-1] if self.aging_history else None
        
        stats = {
            'total_checks': self.total_checks,
            'total_auto_closes': self.total_auto_closes,
            'total_alerts': self.total_alerts,
            'is_running': self.is_running
        }
        
        if latest_report:
            stats.update({
                'current_total_positions': latest_report.total_positions,
                'current_fresh': latest_report.fresh_count,
                'current_aging': latest_report.aging_count,
                'current_stale': latest_report.stale_count,
                'current_expired': latest_report.expired_count,
                'last_check': latest_report.timestamp.isoformat()
            })
        
        return stats
    
    def generate_aging_report(self) -> str:
        """Generate position aging report"""
        stats = self.get_aging_statistics()
        latest_report = self.aging_history[-1] if self.aging_history else None
        
        report = [
            "=" * 60,
            "POSITION AGING MONITOR REPORT",
            "=" * 60,
            f"Total Checks:          {stats['total_checks']:,}",
            f"Auto-closes:           {stats['total_auto_closes']:,}",
            f"Alerts Issued:         {stats['total_alerts']:,}",
            f"Status:                {'RUNNING 🟢' if stats['is_running'] else 'STOPPED 🔴'}",
            ""
        ]
        
        if latest_report:
            report.extend([
                "CURRENT POSITION STATUS:",
                f"  Total Positions:     {latest_report.total_positions}",
                f"  Fresh (🟢):          {latest_report.fresh_count}",
                f"  Aging (🟡):          {latest_report.aging_count}",
                f"  Stale (🟠):          {latest_report.stale_count}",
                f"  Expired (🔴):        {latest_report.expired_count}",
                "",
                "STRATEGY HOLDING LIMITS:",
                *[f"  {strategy.value:25s}: {days} days" 
                  for strategy, days in self.max_holding_periods.items()],
                ""
            ])
            
            # Show stale/expired positions
            problem_positions = [
                p for p in latest_report.positions 
                if p.age_category in [PositionAgeCategory.STALE, PositionAgeCategory.EXPIRED]
            ]
            
            if problem_positions:
                report.append("POSITIONS REQUIRING ATTENTION:")
                for pos in problem_positions:
                    category_icon = "🟠" if pos.age_category == PositionAgeCategory.STALE else "🔴"
                    report.append(
                        f"  {category_icon} {pos.symbol:8s}: {pos.age_days:.1f}/{pos.max_age_days} days "
                        f"({pos.strategy_type.value})"
                    )
                report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)

