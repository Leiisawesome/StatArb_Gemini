"""
Trading Circuit Breakers - System Safety Requirement
Emergency protection mechanisms to prevent catastrophic losses and system runaway.

Architecture Compliance (Tier-1 Rules):
- Rule 3: Risk & Compliance Governance - Phase 9 (Circuit Breaker Validation)
  - 5 mandatory circuit breaker mechanisms
  - Final safety check before execution (feeds into Phase 10)
  - Integration with Rule 6 P&L tracking for threshold checks

Circuit Breaker Mechanisms (5 per Rule 3):
1. Manual Kill Switch - Instant trading halt with authorization code
2. Order Rate Limiting - Maximum orders per second/minute (default: 10/sec)
3. Daily Loss Limit - Auto-halt on portfolio loss (default: -2%)
4. Drawdown from High - Auto-halt on intraday drawdown (default: -5%)
5. Position Concentration - Per-trade validation

Circuit Breaker Levels:
- NORMAL (🟢): All systems operational
- WARNING (🟡): Approaching limits (80% threshold)
- CAUTION (🟠): Limit breached
- HALT (🔴): Trading stopped
- EMERGENCY (⚫): System shutdown

Migration: December 2025 - Former Rule 4 Phase 7B content now Rule 3, Phase 9.

Author: Trading System Team
Date: December 6, 2025
Version: 2.0 (Rules Migration)
"""

import logging
import asyncio
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

# Import standard interfaces
try:
    from .interfaces import IRegimeSubscriber
except ImportError:
    from abc import ABC, abstractmethod
    class IRegimeSubscriber(ABC):
        @abstractmethod
        async def on_regime_change(self, regime_state: Any) -> None:
            pass

# Import regime definitions
from ..type_definitions.regime import MarketRegimeState

logger = logging.getLogger(__name__)

class CircuitBreakerLevel(Enum):
    """Circuit breaker alert levels"""
    NORMAL = "normal"           # 🟢 All systems operational
    WARNING = "warning"         # 🟡 Approaching limits (80%)
    CAUTION = "caution"         # 🟠 Limit breached
    HALT = "halt"              # 🔴 Trading stopped
    EMERGENCY = "emergency"     # ⚫ System shutdown

class CircuitBreakerType(Enum):
    """Types of circuit breakers"""
    MANUAL_KILL_SWITCH = "manual_kill_switch"
    ORDER_RATE_LIMIT = "order_rate_limit"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    DRAWDOWN_LIMIT = "drawdown_limit"
    POSITION_CONCENTRATION = "position_concentration"

@dataclass
class CircuitBreakerStatus:
    """
    Current status of circuit breakers

    Attributes:
        level: Current alert level
        can_trade: Whether trading is allowed
        triggered_breakers: List of triggered breakers
        warnings: Active warnings
        halt_reason: Reason for halt if applicable
        halt_timestamp: When halt was triggered
    """
    level: CircuitBreakerLevel
    can_trade: bool
    triggered_breakers: List[CircuitBreakerType] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    halt_reason: Optional[str] = None
    halt_timestamp: Optional[datetime] = None

    # Detailed status per breaker
    kill_switch_active: bool = False
    order_rate_status: Dict = field(default_factory=dict)
    loss_limit_status: Dict = field(default_factory=dict)
    drawdown_status: Dict = field(default_factory=dict)
    concentration_status: Dict = field(default_factory=dict)

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breakers"""

    # Order Rate Limiting
    max_orders_per_second: int = 10
    max_orders_per_minute: int = 100

    # Loss Limits
    daily_loss_limit_pct: float = -0.02  # -2% of portfolio
    warning_threshold_pct: float = 0.80  # Warning at 80% of limit

    # Drawdown Limits
    max_drawdown_from_high_pct: float = -0.05  # -5% from intraday high

    # Position Concentration
    max_position_concentration: float = 0.20  # 20% max per position

    # External Safety Signals (NEW: Phase 3)
    external_kill_switch_path: str = ".emergency_stop"
    external_check_interval_seconds: int = 5

    # Emergency Actions
    cancel_pending_orders_on_halt: bool = True
    flatten_positions_on_emergency: bool = False  # Optional

    # Alerting
    enable_email_alerts: bool = True
    enable_sms_alerts: bool = False
    enable_slack_alerts: bool = False

class TradingCircuitBreakers(IRegimeSubscriber):
    """
    Trading Circuit Breakers - System Safety

    Implements 5 emergency protection mechanisms to prevent
    catastrophic losses and system runaway.

    Regime-Aware Integration:
    - Implements IRegimeSubscriber to dynamically scale safety thresholds.
    - Tighter limits in high-volatility/low-confidence regimes.
    - Relaxation in normal/stable regimes.

    Integration: Called at START of CentralRiskManager.authorize_trading_decision()
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breakers

        Args:
            config: Circuit breaker configuration
        """
        self.config = config or CircuitBreakerConfig()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Current regime state
        self.current_regime: Optional[MarketRegimeState] = None
        self._original_loss_limit = self.config.daily_loss_limit_pct
        self._original_drawdown_limit = self.config.max_drawdown_from_high_pct
        self._original_concentration_limit = self.config.max_position_concentration

        # Circuit Breaker State
        self.current_level = CircuitBreakerLevel.NORMAL
        self.can_trade = True
        self.triggered_breakers: Set[CircuitBreakerType] = set()

        # Manual Kill Switch
        self.kill_switch_active = False
        self.kill_switch_timestamp: Optional[datetime] = None
        self.kill_switch_user: Optional[str] = None
        self.authorization_code = os.environ.get("CIRCUIT_BREAKER_OVERRIDE_CODE", "")  # Must be set via environment variable

        # Order Rate Limiting
        self.orders_last_second = deque(maxlen=self.config.max_orders_per_second * 2)
        self.orders_last_minute = deque(maxlen=self.config.max_orders_per_minute * 2)
        self.order_count = 0

        # Loss Tracking
        self.portfolio_start_value: Optional[float] = None
        self.portfolio_current_value: Optional[float] = None
        self.daily_pnl: float = 0.0
        self.daily_pnl_pct: float = 0.0

        # Drawdown Tracking
        self.intraday_high_value: Optional[float] = None
        self.intraday_high_timestamp: Optional[datetime] = None
        self.current_drawdown_pct: float = 0.0

        # Statistics
        self.total_checks = 0
        self.halts_triggered = 0
        self.warnings_issued = 0
        self.breaker_history: List[Dict] = []

        # Daily reset
        self.last_reset_date = datetime.now().date()

        self.logger.info("✅ TradingCircuitBreakers initialized")
        self.logger.info(f"   Order Rate Limit: {self.config.max_orders_per_second}/sec")
        self.logger.info(f"   Daily Loss Limit: {self.config.daily_loss_limit_pct:.1%}")
        self.logger.info(f"   Drawdown Limit: {self.config.max_drawdown_from_high_pct:.1%}")

    async def on_regime_change(self, regime_state: Any) -> None:
        """
        Dynamically adjust circuit breaker thresholds based on market regime.
        
        High risk regime (multiplier < 1.0) -> Tighter (less negative) limits.
        Low risk regime (multiplier > 1.0) -> Relaxed (more negative) limits.
        """
        regime_id = getattr(regime_state, 'regime_id', getattr(regime_state, 'primary_regime', 'unknown'))
        multiplier = getattr(regime_state, 'risk_multiplier', 1.0)
        
        self.logger.info(f"⚠️ CircuitBreakers adapting to regime: {regime_id} (Multiplier: {multiplier:.2f})")
        
        # Scale thresholds (keeping their sign)
        # Loss limit: -2% * 0.5 = -1% (Tighter)
        self.config.daily_loss_limit_pct = self._original_loss_limit * multiplier
        
        # Drawdown limit: -5% * 0.5 = -2.5% (Tighter)
        self.config.max_drawdown_from_high_pct = self._original_drawdown_limit * multiplier
        
        # Concentration limit: 20% * 0.5 = 10% (Tighter)
        self.config.max_position_concentration = self._original_concentration_limit * multiplier
        
        self.logger.info(f"✅ Scaled thresholds: Loss {self.config.daily_loss_limit_pct:.1%}, Drawdown {self.config.max_drawdown_from_high_pct:.1%}, Conc {self.config.max_position_concentration:.1%}")

    async def check_circuit_breakers(
        self,
        portfolio_value: Optional[float] = None,
        symbol: Optional[str] = None,
        position_value: Optional[float] = None
    ) -> CircuitBreakerStatus:
        """
        Check all circuit breakers

        Args:
            portfolio_value: Current portfolio value
            symbol: Symbol being traded (for concentration check)
            position_value: Value of position being added

        Returns:
            CircuitBreakerStatus with current state
        """
        self.total_checks += 1

        # Check if daily reset needed
        await self._check_daily_reset()

        # Update portfolio tracking
        if portfolio_value is not None:
            await self._update_portfolio_tracking(portfolio_value)

        warnings = []
        triggered = []

        try:
            # BREAKER 0: External Signal Watcher (Priority 0 - Phase 3)
            external_halt = await self._check_external_kill_switch()
            if external_halt:
                return self._create_halt_status(
                    CircuitBreakerType.MANUAL_KILL_SWITCH,
                    f"External kill switch triggered via file: {self.config.external_kill_switch_path}"
                )

            # BREAKER 1: Manual Kill Switch (highest internal priority)
            if self.kill_switch_active:
                return self._create_halt_status(
                    CircuitBreakerType.MANUAL_KILL_SWITCH,
                    f"Manual kill switch activated by {self.kill_switch_user} at {self.kill_switch_timestamp}"
                )

            # BREAKER 2: Order Rate Limiting
            order_rate_result = await self._check_order_rate_limit()
            if order_rate_result['breached']:
                triggered.append(CircuitBreakerType.ORDER_RATE_LIMIT)
                return self._create_halt_status(
                    CircuitBreakerType.ORDER_RATE_LIMIT,
                    order_rate_result['reason']
                )
            elif order_rate_result.get('warning'):
                warnings.append(order_rate_result['warning'])

            # BREAKER 3: Daily Loss Limit
            if self.portfolio_start_value and portfolio_value:
                loss_limit_result = await self._check_daily_loss_limit(portfolio_value)
                if loss_limit_result['breached']:
                    triggered.append(CircuitBreakerType.DAILY_LOSS_LIMIT)
                    return self._create_halt_status(
                        CircuitBreakerType.DAILY_LOSS_LIMIT,
                        loss_limit_result['reason']
                    )
                elif loss_limit_result.get('warning'):
                    warnings.append(loss_limit_result['warning'])

            # BREAKER 4: Drawdown from High
            if self.intraday_high_value and portfolio_value:
                drawdown_result = await self._check_drawdown_limit(portfolio_value)
                if drawdown_result['breached']:
                    triggered.append(CircuitBreakerType.DRAWDOWN_LIMIT)
                    return self._create_halt_status(
                        CircuitBreakerType.DRAWDOWN_LIMIT,
                        drawdown_result['reason']
                    )
                elif drawdown_result.get('warning'):
                    warnings.append(drawdown_result['warning'])

            # BREAKER 5: Position Concentration
            if symbol and position_value and portfolio_value:
                concentration_result = await self._check_position_concentration(
                    symbol, position_value, portfolio_value
                )
                if concentration_result['breached']:
                    triggered.append(CircuitBreakerType.POSITION_CONCENTRATION)
                    return self._create_halt_status(
                        CircuitBreakerType.POSITION_CONCENTRATION,
                        concentration_result['reason']
                    )
                elif concentration_result.get('warning'):
                    warnings.append(concentration_result['warning'])

            # All checks passed - determine level based on warnings
            if warnings:
                self.warnings_issued += len(warnings)
                level = CircuitBreakerLevel.WARNING
                self.logger.warning(f"⚠️ Circuit breaker warnings: {len(warnings)}")
            else:
                level = CircuitBreakerLevel.NORMAL

            return CircuitBreakerStatus(
                level=level,
                can_trade=True,
                warnings=warnings,
                order_rate_status=order_rate_result,
                loss_limit_status=loss_limit_result if self.portfolio_start_value else {},
                drawdown_status=drawdown_result if self.intraday_high_value else {}
            )

        except Exception as e:
            self.logger.error(f"Circuit breaker check error: {e}")
            # On error, halt trading for safety
            return self._create_halt_status(
                CircuitBreakerType.MANUAL_KILL_SWITCH,
                f"Circuit breaker system error: {str(e)}"
            )

    async def _check_external_kill_switch(self) -> bool:
        """Check for external kill switch signal (Phase 3)"""
        try:
            # Check if override file exists in workspace root
            # Using path from config, default: .emergency_stop
            kill_file = Path(self.config.external_kill_switch_path)
            
            if kill_file.exists():
                if not self.kill_switch_active:
                    self.logger.critical(f"🛑 EXTERNAL KILL SWITCH DETECTED: {kill_file.absolute()}")
                    self.kill_switch_active = True
                    self.kill_switch_user = "EXTERNAL_OPERATIONS"
                    self.kill_switch_timestamp = datetime.now()
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Error checking external kill switch: {e}")
            return False

    async def _check_order_rate_limit(self) -> Dict:
        """Check order rate limiting"""
        now = datetime.now()

        # Remove old orders
        one_second_ago = now - timedelta(seconds=1)
        one_minute_ago = now - timedelta(minutes=1)

        # Count orders in last second
        orders_last_sec = sum(1 for t in self.orders_last_second if t > one_second_ago)
        # Count orders in last minute
        orders_last_min = sum(1 for t in self.orders_last_minute if t > one_minute_ago)

        # Check per-second limit
        if orders_last_sec >= self.config.max_orders_per_second:
            return {
                'breached': True,
                'reason': (
                    f"Order rate limit exceeded: {orders_last_sec} orders/second "
                    f"(limit: {self.config.max_orders_per_second})"
                ),
                'orders_per_second': orders_last_sec,
                'orders_per_minute': orders_last_min
            }

        # Check per-minute limit
        if orders_last_min >= self.config.max_orders_per_minute:
            return {
                'breached': True,
                'reason': (
                    f"Order rate limit exceeded: {orders_last_min} orders/minute "
                    f"(limit: {self.config.max_orders_per_minute})"
                ),
                'orders_per_second': orders_last_sec,
                'orders_per_minute': orders_last_min
            }

        # Warning at 80% of limit
        warning_threshold = self.config.max_orders_per_second * self.config.warning_threshold_pct
        warning = None
        if orders_last_sec >= warning_threshold:
            warning = f"Approaching order rate limit: {orders_last_sec}/{self.config.max_orders_per_second} orders/sec"

        return {
            'breached': False,
            'orders_per_second': orders_last_sec,
            'orders_per_minute': orders_last_min,
            'warning': warning
        }

    async def _check_daily_loss_limit(self, portfolio_value: float) -> Dict:
        """Check daily loss limit"""
        if not self.portfolio_start_value:
            return {'breached': False}

        self.daily_pnl = portfolio_value - self.portfolio_start_value
        self.daily_pnl_pct = self.daily_pnl / self.portfolio_start_value

        # Check if loss limit breached
        if self.daily_pnl_pct <= self.config.daily_loss_limit_pct:
            return {
                'breached': True,
                'reason': (
                    f"Daily loss limit breached: {self.daily_pnl_pct:.2%} loss "
                    f"(limit: {self.config.daily_loss_limit_pct:.2%}), "
                    f"${self.daily_pnl:,.0f} lost"
                ),
                'daily_pnl': self.daily_pnl,
                'daily_pnl_pct': self.daily_pnl_pct
            }

        # Warning at 80% of limit
        warning_level = self.config.daily_loss_limit_pct * self.config.warning_threshold_pct
        warning = None
        # Use small tolerance for floating point comparison
        tolerance = 1e-10
        if self.daily_pnl_pct <= warning_level + tolerance:
            warning = (
                f"Approaching daily loss limit: {self.daily_pnl_pct:.2%} "
                f"(limit: {self.config.daily_loss_limit_pct:.2%})"
            )

        return {
            'breached': False,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': self.daily_pnl_pct,
            'warning': warning
        }

    async def _check_drawdown_limit(self, portfolio_value: float) -> Dict:
        """Check drawdown from intraday high"""
        if not self.intraday_high_value:
            return {'breached': False}

        self.current_drawdown_pct = (portfolio_value - self.intraday_high_value) / self.intraday_high_value

        # Check if drawdown limit breached
        if self.current_drawdown_pct <= self.config.max_drawdown_from_high_pct:
            return {
                'breached': True,
                'reason': (
                    f"Drawdown limit breached: {self.current_drawdown_pct:.2%} from high "
                    f"(limit: {self.config.max_drawdown_from_high_pct:.2%}), "
                    f"High: ${self.intraday_high_value:,.0f}, Current: ${portfolio_value:,.0f}"
                ),
                'current_drawdown_pct': self.current_drawdown_pct,
                'intraday_high': self.intraday_high_value
            }

        # Warning at 80% of limit
        warning_level = self.config.max_drawdown_from_high_pct * self.config.warning_threshold_pct
        warning = None
        # Use small tolerance for floating point comparison
        tolerance = 1e-10
        if self.current_drawdown_pct <= warning_level + tolerance:
            warning = (
                f"Approaching drawdown limit: {self.current_drawdown_pct:.2%} from high "
                f"(limit: {self.config.max_drawdown_from_high_pct:.2%})"
            )

        return {
            'breached': False,
            'current_drawdown_pct': self.current_drawdown_pct,
            'intraday_high': self.intraday_high_value,
            'warning': warning
        }

    async def _check_position_concentration(
        self,
        symbol: str,
        position_value: float,
        portfolio_value: float
    ) -> Dict:
        """Check position concentration"""
        concentration = position_value / portfolio_value

        if concentration > self.config.max_position_concentration:
            return {
                'breached': True,
                'reason': (
                    f"Position concentration limit breached for {symbol}: {concentration:.1%} "
                    f"(limit: {self.config.max_position_concentration:.1%})"
                ),
                'concentration': concentration
            }

        # Warning at 80% of limit
        warning_level = self.config.max_position_concentration * self.config.warning_threshold_pct
        warning = None
        if concentration > warning_level:
            warning = f"High concentration for {symbol}: {concentration:.1%}"

        return {
            'breached': False,
            'concentration': concentration,
            'warning': warning
        }

    def _create_halt_status(
        self,
        breaker_type: CircuitBreakerType,
        reason: str
    ) -> CircuitBreakerStatus:
        """Create halt status and execute emergency actions"""
        self.can_trade = False
        self.current_level = CircuitBreakerLevel.HALT
        self.triggered_breakers.add(breaker_type)
        self.halts_triggered += 1

        halt_timestamp = datetime.now()

        # Record in history
        self.breaker_history.append({
            'timestamp': halt_timestamp,
            'breaker_type': breaker_type.value,
            'reason': reason,
            'portfolio_value': self.portfolio_current_value,
            'daily_pnl_pct': self.daily_pnl_pct
        })

        # Log critical alert
        self.logger.critical(f"🔴 CIRCUIT BREAKER HALT: {reason}")

        # Execute emergency actions
        asyncio.create_task(self._execute_emergency_actions(breaker_type, reason))

        return CircuitBreakerStatus(
            level=CircuitBreakerLevel.HALT,
            can_trade=False,
            triggered_breakers=[breaker_type],
            halt_reason=reason,
            halt_timestamp=halt_timestamp
        )

    async def _execute_emergency_actions(self, breaker_type: CircuitBreakerType, reason: str):
        """Execute emergency actions on halt"""
        try:
            self.logger.warning("⚠️ Executing emergency actions...")

            # Action 1: Cancel pending orders (if enabled)
            if self.config.cancel_pending_orders_on_halt:
                self.logger.info("   - Cancelling all pending orders")
                # Would call order management system here

            # Action 2: Flatten positions (if enabled and emergency)
            if self.config.flatten_positions_on_emergency and breaker_type == CircuitBreakerType.MANUAL_KILL_SWITCH:
                self.logger.warning("   - Emergency position flattening requested")
                # Would call position management system here

            # Action 3: Send alerts
            await self._send_circuit_breaker_alerts(breaker_type, reason)

            self.logger.info("✅ Emergency actions completed")

        except Exception as e:
            self.logger.error(f"Emergency action error: {e}")

    async def _send_circuit_breaker_alerts(self, breaker_type: CircuitBreakerType, reason: str):
        """Send circuit breaker alerts"""
        alert_message = (
            f"🔴 CIRCUIT BREAKER ALERT\n"
            f"Type: {breaker_type.value}\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Portfolio: ${self.portfolio_current_value:,.0f}\n"
            f"Daily P&L: {self.daily_pnl_pct:.2%}"
        )

        if self.config.enable_email_alerts:
            self.logger.info("   - Sending email alert")
            # Would send email here

        if self.config.enable_sms_alerts:
            self.logger.info("   - Sending SMS alert")
            # Would send SMS here (Twilio)

        if self.config.enable_slack_alerts:
            self.logger.info("   - Sending Slack alert")
            # Would send Slack webhook here

        self.logger.info(f"Alert message: {alert_message}")

    async def _update_portfolio_tracking(self, portfolio_value: float):
        """Update portfolio value tracking"""
        self.portfolio_current_value = portfolio_value

        # Set start value if not set
        if self.portfolio_start_value is None:
            self.portfolio_start_value = portfolio_value
            self.logger.info(f"Portfolio start value set: ${portfolio_value:,.0f}")

        # Update intraday high
        if self.intraday_high_value is None or portfolio_value > self.intraday_high_value:
            self.intraday_high_value = portfolio_value
            self.intraday_high_timestamp = datetime.now()

    async def _check_daily_reset(self):
        """Check if daily reset is needed"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            await self.daily_reset()

    async def daily_reset(self):
        """Reset daily tracking (call at start of trading day)"""
        self.logger.info("📅 Daily reset: Resetting intraday metrics")

        # Reset P&L tracking
        self.portfolio_start_value = self.portfolio_current_value
        self.daily_pnl = 0.0
        self.daily_pnl_pct = 0.0

        # Reset drawdown tracking
        self.intraday_high_value = self.portfolio_current_value
        self.intraday_high_timestamp = datetime.now()
        self.current_drawdown_pct = 0.0

        # Reset order tracking
        self.orders_last_second.clear()
        self.orders_last_minute.clear()

        self.last_reset_date = datetime.now().date()

    # Manual Control Methods

    def activate_kill_switch(self, user: str, authorization_code: str) -> bool:
        """
        Activate manual kill switch

        Args:
            user: User activating kill switch
            authorization_code: Authorization code for verification

        Returns:
            bool: Whether activation was successful
        """
        if authorization_code != self.authorization_code:
            self.logger.error(f"⛔ Kill switch activation DENIED: Invalid authorization code from {user}")
            return False

        self.kill_switch_active = True
        self.kill_switch_timestamp = datetime.now()
        self.kill_switch_user = user
        self.can_trade = False

        self.logger.critical(
            f"🔴 KILL SWITCH ACTIVATED by {user} at {self.kill_switch_timestamp}"
        )

        # Execute emergency actions
        asyncio.create_task(self._execute_emergency_actions(
            CircuitBreakerType.MANUAL_KILL_SWITCH,
            f"Manual kill switch activated by {user}"
        ))

        return True

    def deactivate_kill_switch(self, user: str, authorization_code: str) -> bool:
        """
        Deactivate manual kill switch

        Args:
            user: User deactivating kill switch
            authorization_code: Authorization code for verification

        Returns:
            bool: Whether deactivation was successful
        """
        if authorization_code != self.authorization_code:
            self.logger.error(f"⛔ Kill switch deactivation DENIED: Invalid authorization code from {user}")
            return False

        self.kill_switch_active = False
        self.can_trade = True
        self.triggered_breakers.discard(CircuitBreakerType.MANUAL_KILL_SWITCH)

        self.logger.warning(f"🟢 Kill switch DEACTIVATED by {user} at {datetime.now()}")

        return True

    def record_order_attempt(self):
        """Record order attempt for rate limiting"""
        now = datetime.now()
        self.orders_last_second.append(now)
        self.orders_last_minute.append(now)
        self.order_count += 1

    # Statistics and Reporting

    def get_circuit_breaker_statistics(self) -> Dict:
        """Get circuit breaker statistics"""
        return {
            'total_checks': self.total_checks,
            'halts_triggered': self.halts_triggered,
            'warnings_issued': self.warnings_issued,
            'current_level': self.current_level.value,
            'can_trade': self.can_trade,
            'kill_switch_active': self.kill_switch_active,
            'portfolio_value': self.portfolio_current_value,
            'daily_pnl_pct': self.daily_pnl_pct,
            'current_drawdown_pct': self.current_drawdown_pct,
            'orders_per_second': len([t for t in self.orders_last_second
                                     if t > datetime.now() - timedelta(seconds=1)]),
            'triggered_breakers': [b.value for b in self.triggered_breakers],
            'breaker_history_count': len(self.breaker_history)
        }

    def generate_circuit_breaker_report(self) -> str:
        """Generate circuit breaker report"""
        stats = self.get_circuit_breaker_statistics()

        report = [
            "=" * 60,
            "CIRCUIT BREAKER REPORT",
            "=" * 60,
            f"Current Level:     {stats['current_level'].upper()} {'🔴' if not stats['can_trade'] else '🟢'}",
            f"Trading Enabled:   {'NO 🔴' if not stats['can_trade'] else 'YES 🟢'}",
            f"Kill Switch:       {'ACTIVE 🔴' if stats['kill_switch_active'] else 'Inactive'}",
            "",
            f"Total Checks:      {stats['total_checks']:,}",
            f"Halts Triggered:   {stats['halts_triggered']}",
            f"Warnings Issued:   {stats['warnings_issued']}",
            "",
            "CURRENT METRICS:",
            f"  Portfolio Value:  ${stats['portfolio_value']:,.0f}" if stats['portfolio_value'] else "  Portfolio Value:  N/A",
            f"  Daily P&L:        {stats['daily_pnl_pct']:.2%}",
            f"  Drawdown:         {stats['current_drawdown_pct']:.2%}",
            f"  Order Rate:       {stats['orders_per_second']}/sec",
            "",
            "TRIGGERED BREAKERS:",
        ]

        # Add triggered breakers
        if stats['triggered_breakers']:
            report.extend([f"  - {breaker}" for breaker in stats['triggered_breakers']])
        else:
            report.append("  None")

        report.append("=" * 60)

        return "\n".join(report)

