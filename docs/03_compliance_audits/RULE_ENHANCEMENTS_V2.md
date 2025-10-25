# Rule Enhancements v2.0 - Institutional Requirements
## Based on Trading Desk Assessment

**Date:** October 25, 2025  
**Status:** IN PROGRESS  
**Purpose:** Enhance Rules 1-7 with institutional trading requirements

---

## Enhancement Summary

### Critical Additions (From Assessment Gaps)
1. **Pre-Trade Compliance Framework** (Rule 4)
2. **Circuit Breakers & Kill Switches** (Rule 4)
3. **Real-Time P&L Tracking** (Rule 7)
4. **Position Reconciliation** (Rule 7)
5. **Intraday Risk Monitoring** (Rule 4)
6. **Fast Regime Detection** (Rule 2)
7. **Order Rejection Handling** (Rule 7)
8. **Position Aging Tracking** (Rule 7)

---

## Rule 4 Enhancements: Pre-Trade Compliance & Circuit Breakers

### NEW SECTION: Phase 7A - Pre-Trade Compliance (CRITICAL)

**Insert After Phase 7, Before Component Responsibility Matrix**

```markdown
## Phase 7A: Pre-Trade Compliance Checks (CRITICAL) 🔴

**Component:** PreTradeComplianceChecker (NEW)  
**File:** `core_engine/system/compliance_checker.py`  
**Authority:** GOVERNANCE_CONTROL  
**Responsibility:** Verify regulatory compliance BEFORE authorization

### Why Compliance Checks are Critical

**Real-World Requirements:**
- SEC Regulation SHO (short selling)
- Hard-to-borrow availability
- Restricted securities lists
- Insider trading blackout periods
- Pattern day trading rules (Reg T)
- Large position reporting (13D/G filings)

**Failure Impact:**
- SEC violations and fines ($100K+)
- Failed trades (hard-to-borrow rejections)
- Regulatory sanctions
- Compliance department escalation

### Compliance Check Pipeline

```
TradingDecisionRequest
         ↓
┌────────────────────────────────────────────┐
│ PreTradeComplianceChecker (NEW)           │
│                                            │
│ Checks (ALL MANDATORY):                   │
│ 1. ✅ Restricted Securities List          │
│ 2. ✅ Hard-to-Borrow Availability (shorts)│
│ 3. ✅ Insider Blackout Periods            │
│ 4. ✅ 13D/G Filing Triggers (5%+)         │
│ 5. ✅ Pattern Day Trading Rules           │
│ 6. ✅ Reg SHO Short Selling               │
│ 7. ✅ Concentration Reporting             │
│                                            │
│ Output: ComplianceResult                  │
│   - approved: bool                        │
│   - reason: str (if rejected)             │
│   - requires_manual_review: bool          │
└────────────────────────────────────────────┘
         ↓
   IF approved → CentralRiskManager (Phase 7)
   IF rejected → Reject with compliance reason
```

### Implementation: PreTradeComplianceChecker

```python
from dataclasses import dataclass
from typing import List, Optional, Set
from datetime import datetime, timedelta

@dataclass
class ComplianceResult:
    """Result of pre-trade compliance check"""
    approved: bool
    rejection_reason: Optional[str] = None
    requires_manual_review: bool = False
    compliance_checks_performed: List[str] = None
    warnings: List[str] = None

class PreTradeComplianceChecker:
    """
    Pre-trade compliance engine (INSTITUTIONAL REQUIREMENT)
    
    Performs regulatory compliance checks BEFORE risk authorization.
    ALL trades must pass compliance before proceeding to risk checks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Restricted Securities Lists
        self.restricted_list: Set[str] = set()  # Internal restricted list
        self.watch_list: Set[str] = set()       # Compliance watch list
        
        # Hard-to-Borrow
        self.hard_to_borrow: Set[str] = set()   # Current HTB list
        self.locate_cache: Dict[str, datetime] = {}  # Share locate cache
        
        # Insider Trading Controls
        self.blackout_periods: Dict[str, tuple] = {}  # symbol → (start, end)
        
        # Pattern Day Trading
        self.recent_day_trades: List[Dict] = []  # Last 5 days of trades
        
        # Large Position Tracking
        self.shares_outstanding: Dict[str, float] = {}  # symbol → shares
        
        logger.info("✅ PreTradeComplianceChecker initialized")
    
    async def check_pre_trade_compliance(
        self,
        request: 'TradingDecisionRequest'
    ) -> ComplianceResult:
        """
        Perform comprehensive pre-trade compliance checks
        
        MANDATORY: Must be called BEFORE risk authorization
        
        Returns ComplianceResult with approval/rejection
        """
        checks_performed = []
        warnings = []
        
        try:
            # CHECK 1: Restricted Securities List
            if request.symbol in self.restricted_list:
                return ComplianceResult(
                    approved=False,
                    rejection_reason=f"{request.symbol} on restricted securities list",
                    compliance_checks_performed=['restricted_list']
                )
            checks_performed.append('restricted_list')
            
            # CHECK 2: Watch List (warning only)
            if request.symbol in self.watch_list:
                warnings.append(f"{request.symbol} on compliance watch list")
            
            # CHECK 3: Short Selling Compliance (Reg SHO)
            if request.side.lower() == 'sell':
                short_check = await self._check_short_selling_compliance(request)
                if not short_check.approved:
                    return short_check
                checks_performed.append('short_selling')
            
            # CHECK 4: Insider Blackout Periods
            blackout_check = self._check_blackout_period(request.symbol)
            if not blackout_check.approved:
                return blackout_check
            checks_performed.append('blackout_period')
            
            # CHECK 5: 13D/G Filing Triggers
            filing_check = await self._check_large_position_reporting(request)
            if not filing_check.approved:
                return filing_check
            checks_performed.append('13d_filing')
            
            # CHECK 6: Pattern Day Trading Rules
            pdt_check = self._check_pattern_day_trading(request)
            if not pdt_check.approved:
                return pdt_check
            checks_performed.append('pattern_day_trading')
            
            # CHECK 7: Concentration Reporting
            concentration_check = self._check_concentration_limits(request)
            if not concentration_check.approved:
                warnings.append(concentration_check.rejection_reason)
            checks_performed.append('concentration')
            
            # ALL CHECKS PASSED
            logger.info(
                f"✅ Compliance approved: {request.symbol} {request.side} "
                f"{request.quantity} ({len(checks_performed)} checks passed)"
            )
            
            return ComplianceResult(
                approved=True,
                compliance_checks_performed=checks_performed,
                warnings=warnings if warnings else None
            )
            
        except Exception as e:
            logger.error(f"Compliance check failed: {e}")
            return ComplianceResult(
                approved=False,
                rejection_reason=f"Compliance system error: {str(e)}",
                compliance_checks_performed=checks_performed
            )
    
    async def _check_short_selling_compliance(
        self,
        request: 'TradingDecisionRequest'
    ) -> ComplianceResult:
        """
        Check short selling compliance (Reg SHO)
        
        Requirements:
        - Must locate shares before shorting
        - Check hard-to-borrow list
        - Verify not on threshold securities list
        """
        # Check if we have a position (not a short if we own it)
        if hasattr(request, 'current_position') and request.current_position > 0:
            return ComplianceResult(approved=True)  # Selling long position, OK
        
        # This is a short sale - check hard-to-borrow
        if request.symbol in self.hard_to_borrow:
            # Check if we have a valid locate
            if request.symbol in self.locate_cache:
                locate_time = self.locate_cache[request.symbol]
                if datetime.now() - locate_time < timedelta(hours=24):
                    return ComplianceResult(approved=True)  # Valid locate
            
            # No valid locate - reject short
            return ComplianceResult(
                approved=False,
                rejection_reason=f"{request.symbol} is hard-to-borrow, no valid locate"
            )
        
        return ComplianceResult(approved=True)
    
    def _check_blackout_period(self, symbol: str) -> ComplianceResult:
        """
        Check insider trading blackout periods
        
        Prevents trading during:
        - Earnings blackouts
        - Material non-public information periods
        - Corporate action blackouts
        """
        if symbol in self.blackout_periods:
            start, end = self.blackout_periods[symbol]
            if start <= datetime.now() <= end:
                return ComplianceResult(
                    approved=False,
                    rejection_reason=f"{symbol} in insider blackout period until {end}"
                )
        
        return ComplianceResult(approved=True)
    
    async def _check_large_position_reporting(
        self,
        request: 'TradingDecisionRequest'
    ) -> ComplianceResult:
        """
        Check if trade triggers 13D/G filing requirements
        
        SEC requires disclosure when position exceeds 5% of shares outstanding
        """
        if request.symbol not in self.shares_outstanding:
            return ComplianceResult(approved=True)  # Unknown shares, allow
        
        total_shares = self.shares_outstanding[request.symbol]
        current_position = getattr(request, 'current_position', 0.0)
        new_position = current_position + request.quantity
        
        position_pct = new_position / total_shares
        
        if position_pct > 0.05:  # 5% threshold
            return ComplianceResult(
                approved=False,
                rejection_reason=(
                    f"Position would exceed 5% of {request.symbol} "
                    f"({position_pct:.2%}), requires 13D/G filing"
                ),
                requires_manual_review=True
            )
        
        return ComplianceResult(approved=True)
    
    def _check_pattern_day_trading(
        self,
        request: 'TradingDecisionRequest'
    ) -> ComplianceResult:
        """
        Check pattern day trading rules (Reg T)
        
        Pattern Day Trader: 4+ day trades in 5 business days
        Requires $25K minimum account balance
        """
        # Count day trades in last 5 business days
        five_days_ago = datetime.now() - timedelta(days=5)
        recent_day_trades = [
            t for t in self.recent_day_trades
            if t['timestamp'] >= five_days_ago and t['symbol'] == request.symbol
        ]
        
        if len(recent_day_trades) >= 4:
            # Check account balance
            if self.account_value < 25000:
                return ComplianceResult(
                    approved=False,
                    rejection_reason=(
                        "Pattern day trading limit reached (4 trades in 5 days). "
                        "Requires $25K minimum account balance."
                    )
                )
        
        return ComplianceResult(approved=True)
    
    def _check_concentration_limits(
        self,
        request: 'TradingDecisionRequest'
    ) -> ComplianceResult:
        """Check if position exceeds concentration thresholds"""
        # This is a warning, not a hard rejection
        return ComplianceResult(approved=True)
```

### Integration with CentralRiskManager

```python
class CentralRiskManager:
    """Enhanced with pre-trade compliance"""
    
    def __init__(self, config):
        super().__init__(config)
        
        # NEW: Pre-trade compliance checker
        self.compliance_checker = PreTradeComplianceChecker(config)
    
    async def authorize_trading_decision(
        self,
        request: TradingDecisionRequest
    ) -> TradingAuthorization:
        """
        Authorize trading decision with compliance checks
        
        NEW FLOW:
        1. Pre-trade compliance checks (FIRST)
        2. Risk authorization checks (SECOND)
        """
        
        # STEP 1: PRE-TRADE COMPLIANCE (NEW - MANDATORY)
        compliance_result = await self.compliance_checker.check_pre_trade_compliance(request)
        
        if not compliance_result.approved:
            # REJECT: Compliance violation
            return TradingAuthorization(
                authorization_id=str(uuid.uuid4()),
                request_id=request.request_id,
                authorization_level=AuthorizationLevel.REJECTED,
                authorized=False,
                authorized_quantity=0.0,
                authorization_timestamp=datetime.now(),
                risk_budget_allocated=0.0,
                rejection_reason=f"COMPLIANCE: {compliance_result.rejection_reason}",
                expiry_time=datetime.now()
            )
        
        # Log compliance warnings if any
        if compliance_result.warnings:
            for warning in compliance_result.warnings:
                logger.warning(f"⚠️ Compliance warning: {warning}")
        
        # STEP 2: RISK AUTHORIZATION (existing logic)
        # ... continue with normal risk checks ...
        
        return authorization
```

### MANDATORY: All Trades Flow Through Compliance

```python
# CORRECT FLOW (MANDATORY):
request = TradingDecisionRequest(...)
         ↓
compliance_check = await compliance_checker.check(request)  # FIRST
         ↓
if approved:
    authorization = await risk_manager.authorize(request)  # SECOND
         ↓
    execution = await execution_engine.execute(authorization)  # THIRD
```

### Compliance Configuration

```python
@dataclass
class ComplianceConfig:
    """Configuration for compliance checks"""
    
    # Restricted Lists
    restricted_securities_file: str = "config/restricted_list.txt"
    watch_list_file: str = "config/watch_list.txt"
    
    # Hard-to-Borrow
    htb_refresh_interval_minutes: int = 60
    locate_validity_hours: int = 24
    
    # Blackout Periods
    earnings_blackout_days_before: int = 2
    earnings_blackout_days_after: int = 1
    
    # Pattern Day Trading
    pdt_lookback_days: int = 5
    pdt_minimum_balance: float = 25000.0
    
    # Large Position Reporting
    filing_threshold_pct: float = 0.05  # 5%
    concentration_warning_pct: float = 0.03  # 3%
```
```

---

### NEW SECTION: Phase 7B - Circuit Breakers & Kill Switches (CRITICAL)

**Insert After Pre-Trade Compliance**

```markdown
## Phase 7B: Circuit Breakers & Kill Switches (CRITICAL) 🔴

**Component:** TradingCircuitBreakers (NEW)  
**File:** `core_engine/system/circuit_breakers.py`  
**Authority:** SYSTEM_CONTROL  
**Responsibility:** Emergency trading halt and risk containment

### Why Circuit Breakers are Critical

**Real-World Protection:**
- Prevent system runaway (e.g., 1000 orders/second)
- Auto-halt on large losses (e.g., -2% daily limit)
- Protect against flash crashes
- Emergency position flattening
- Regulatory requirement for automated trading

**Failure Impact:**
- Catastrophic losses (no stop mechanism)
- Broker penalties (excessive order flow)
- System shutdown by exchange
- Reputation damage
- Potential SEC investigation

### Circuit Breaker Levels

```
Level 1: WARNING (Yellow)
- Approaching limits
- Increase monitoring
- Alert risk team

Level 2: CAUTION (Orange)
- Limit breached
- Reduce trading activity
- Manual review required

Level 3: HALT (Red)
- Emergency halt all trading
- Cancel all orders
- Optional: Flatten positions
- Notify management
```

### Implementation: TradingCircuitBreakers

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional
import asyncio

class CircuitBreakerLevel(Enum):
    """Circuit breaker alert levels"""
    NORMAL = "normal"        # Green - all systems operational
    WARNING = "warning"      # Yellow - approaching limits
    CAUTION = "caution"      # Orange - limit breached
    HALT = "halt"           # Red - trading halted
    EMERGENCY = "emergency"  # Critical - system shutdown

@dataclass
class CircuitBreakerStatus:
    """Current circuit breaker status"""
    level: CircuitBreakerLevel
    reason: str
    triggered_at: datetime
    breakers_triggered: List[str]
    can_trade: bool
    requires_manual_override: bool

class TradingCircuitBreakers:
    """
    Trading circuit breakers and kill switches
    
    INSTITUTIONAL REQUIREMENT: Must have emergency stops
    
    Implements multiple layers of protection:
    - Order rate limiting
    - Daily loss limits
    - Drawdown limits
    - Position concentration
    - Manual kill switch
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # System State
        self.system_halted = False
        self.manual_override = False
        self.halt_reason = None
        self.halt_timestamp = None
        
        # Thresholds (configurable)
        self.max_orders_per_second = config.get('max_orders_per_second', 10)
        self.max_daily_loss = config.get('max_daily_loss', 0.02)  # 2%
        self.max_drawdown_from_high = config.get('max_drawdown', 0.05)  # 5%
        self.max_position_concentration = config.get('max_concentration', 0.25)  # 25%
        
        # Tracking
        self.orders_last_second = 0
        self.orders_timestamps: List[datetime] = []
        self.daily_pnl = 0.0
        self.daily_high_pnl = 0.0
        self.portfolio_value = 0.0
        
        # Circuit breaker history
        self.breaker_history: List[Dict] = []
        
        logger.info("✅ TradingCircuitBreakers initialized")
    
    async def check_circuit_breakers(
        self,
        current_pnl: float = None,
        portfolio_value: float = None
    ) -> CircuitBreakerStatus:
        """
        Check all circuit breakers
        
        MANDATORY: Must be called BEFORE every trade
        
        Returns CircuitBreakerStatus indicating if trading is allowed
        """
        triggered_breakers = []
        
        # Update state
        if current_pnl is not None:
            self.daily_pnl = current_pnl
            if current_pnl > self.daily_high_pnl:
                self.daily_high_pnl = current_pnl
        
        if portfolio_value is not None:
            self.portfolio_value = portfolio_value
        
        # BREAKER 1: Manual Kill Switch (highest priority)
        if self.system_halted or self.manual_override:
            return CircuitBreakerStatus(
                level=CircuitBreakerLevel.HALT,
                reason="Manual kill switch activated",
                triggered_at=self.halt_timestamp,
                breakers_triggered=['manual_halt'],
                can_trade=False,
                requires_manual_override=True
            )
        
        # BREAKER 2: Order Rate Limiting
        order_rate_status = self._check_order_rate_limit()
        if order_rate_status:
            triggered_breakers.append('order_rate')
            if order_rate_status.level == CircuitBreakerLevel.HALT:
                await self.halt_system("Excessive order rate")
                return order_rate_status
        
        # BREAKER 3: Daily Loss Limit
        loss_limit_status = self._check_daily_loss_limit()
        if loss_limit_status:
            triggered_breakers.append('daily_loss')
            if loss_limit_status.level == CircuitBreakerLevel.HALT:
                await self.halt_system(f"Daily loss limit exceeded: {self.daily_pnl:.2%}")
                return loss_limit_status
        
        # BREAKER 4: Drawdown from High
        drawdown_status = self._check_drawdown_limit()
        if drawdown_status:
            triggered_breakers.append('drawdown')
            if drawdown_status.level == CircuitBreakerLevel.HALT:
                await self.halt_system(f"Excessive drawdown from high")
                return drawdown_status
        
        # BREAKER 5: Position Concentration
        # (checked per-trade, not global)
        
        # System operational
        return CircuitBreakerStatus(
            level=CircuitBreakerLevel.NORMAL,
            reason="All systems operational",
            triggered_at=datetime.now(),
            breakers_triggered=[],
            can_trade=True,
            requires_manual_override=False
        )
    
    def _check_order_rate_limit(self) -> Optional[CircuitBreakerStatus]:
        """
        Check order rate limiting
        
        Prevents: Runaway strategy sending excessive orders
        Threshold: 10 orders per second (default)
        """
        now = datetime.now()
        
        # Clean old timestamps (older than 1 second)
        self.orders_timestamps = [
            ts for ts in self.orders_timestamps
            if (now - ts).total_seconds() < 1.0
        ]
        
        orders_per_second = len(self.orders_timestamps)
        
        if orders_per_second >= self.max_orders_per_second:
            logger.critical(
                f"🔴 CIRCUIT BREAKER: Order rate {orders_per_second}/sec "
                f"exceeds limit {self.max_orders_per_second}/sec"
            )
            return CircuitBreakerStatus(
                level=CircuitBreakerLevel.HALT,
                reason=f"Order rate exceeded: {orders_per_second}/sec",
                triggered_at=now,
                breakers_triggered=['order_rate'],
                can_trade=False,
                requires_manual_override=True
            )
        
        # Warning at 80% of limit
        elif orders_per_second >= self.max_orders_per_second * 0.8:
            logger.warning(
                f"⚠️ Order rate approaching limit: {orders_per_second}/"
                f"{self.max_orders_per_second}/sec"
            )
            return CircuitBreakerStatus(
                level=CircuitBreakerLevel.WARNING,
                reason=f"Order rate high: {orders_per_second}/sec",
                triggered_at=now,
                breakers_triggered=[],
                can_trade=True,
                requires_manual_override=False
            )
        
        return None
    
    def _check_daily_loss_limit(self) -> Optional[CircuitBreakerStatus]:
        """
        Check daily loss limit
        
        Prevents: Catastrophic daily losses
        Threshold: -2% of portfolio (default)
        """
        if self.portfolio_value == 0:
            return None
        
        max_loss_dollars = self.max_daily_loss * self.portfolio_value
        
        if self.daily_pnl < -max_loss_dollars:
            logger.critical(
                f"🔴 CIRCUIT BREAKER: Daily loss ${-self.daily_pnl:,.2f} "
                f"exceeds limit ${max_loss_dollars:,.2f} ({self.max_daily_loss:.1%})"
            )
            return CircuitBreakerStatus(
                level=CircuitBreakerLevel.HALT,
                reason=f"Daily loss limit exceeded: ${-self.daily_pnl:,.2f}",
                triggered_at=datetime.now(),
                breakers_triggered=['daily_loss'],
                can_trade=False,
                requires_manual_override=True
            )
        
        # Warning at 80% of limit
        elif self.daily_pnl < -max_loss_dollars * 0.8:
            logger.warning(
                f"⚠️ Daily loss approaching limit: ${-self.daily_pnl:,.2f} / "
                f"${max_loss_dollars:,.2f}"
            )
            return CircuitBreakerStatus(
                level=CircuitBreakerLevel.WARNING,
                reason=f"Daily loss high: ${-self.daily_pnl:,.2f}",
                triggered_at=datetime.now(),
                breakers_triggered=[],
                can_trade=True,
                requires_manual_override=False
            )
        
        return None
    
    def _check_drawdown_limit(self) -> Optional[CircuitBreakerStatus]:
        """
        Check drawdown from intraday high
        
        Prevents: Excessive intraday losses after gains
        Threshold: -5% from high (default)
        """
        if self.daily_high_pnl <= 0:
            return None  # No gains yet today
        
        drawdown = self.daily_high_pnl - self.daily_pnl
        drawdown_pct = drawdown / abs(self.daily_high_pnl)
        
        if drawdown_pct > self.max_drawdown_from_high:
            logger.critical(
                f"🔴 CIRCUIT BREAKER: Drawdown {drawdown_pct:.1%} from high "
                f"exceeds limit {self.max_drawdown_from_high:.1%}"
            )
            return CircuitBreakerStatus(
                level=CircuitBreakerLevel.HALT,
                reason=f"Excessive drawdown: {drawdown_pct:.1%} from ${self.daily_high_pnl:,.2f}",
                triggered_at=datetime.now(),
                breakers_triggered=['drawdown'],
                can_trade=False,
                requires_manual_override=True
            )
        
        # Warning at 80% of limit
        elif drawdown_pct > self.max_drawdown_from_high * 0.8:
            logger.warning(
                f"⚠️ Drawdown approaching limit: {drawdown_pct:.1%}"
            )
            return CircuitBreakerStatus(
                level=CircuitBreakerLevel.WARNING,
                reason=f"Drawdown high: {drawdown_pct:.1%}",
                triggered_at=datetime.now(),
                breakers_triggered=[],
                can_trade=True,
                requires_manual_override=False
            )
        
        return None
    
    async def halt_system(self, reason: str):
        """
        Emergency system halt (kill switch)
        
        Actions:
        1. Set halt flag
        2. Cancel all pending orders
        3. Optional: Flatten all positions
        4. Notify risk team
        5. Log halt event
        """
        self.system_halted = True
        self.halt_reason = reason
        self.halt_timestamp = datetime.now()
        
        logger.critical(f"🛑 SYSTEM HALTED: {reason}")
        
        # Cancel all orders
        await self._cancel_all_orders()
        
        # Optional: Flatten positions (configurable)
        if self.config.get('flatten_on_halt', False):
            await self._flatten_all_positions()
        
        # Notify risk team
        await self._notify_risk_team(reason)
        
        # Log halt event
        self.breaker_history.append({
            'timestamp': self.halt_timestamp,
            'reason': reason,
            'daily_pnl': self.daily_pnl,
            'portfolio_value': self.portfolio_value
        })
    
    async def _cancel_all_orders(self):
        """Cancel all pending orders"""
        logger.critical("🛑 Cancelling all pending orders")
        # Implementation would cancel orders via broker API
        pass
    
    async def _flatten_all_positions(self):
        """Emergency position flattening (optional)"""
        logger.critical("🛑 Flattening all positions")
        # Implementation would liquidate all positions
        pass
    
    async def _notify_risk_team(self, reason: str):
        """Send emergency notification to risk team"""
        logger.critical(f"📧 Notifying risk team: {reason}")
        # Implementation would send email/SMS/Slack alert
        pass
    
    def register_order(self):
        """Register an order (for rate limiting)"""
        self.orders_timestamps.append(datetime.now())
    
    def resume_trading(self, override_code: str):
        """
        Resume trading after halt (requires manual override)
        
        Safety: Requires human authorization code
        """
        if self._validate_override_code(override_code):
            self.system_halted = False
            self.manual_override = False
            self.halt_reason = None
            logger.warning("⚠️ Trading resumed via manual override")
            return True
        else:
            logger.error("❌ Invalid override code")
            return False
```

### Integration with CentralRiskManager

```python
class CentralRiskManager:
    """Enhanced with circuit breakers"""
    
    def __init__(self, config):
        super().__init__(config)
        
        # NEW: Circuit breakers
        self.circuit_breakers = TradingCircuitBreakers(config)
    
    async def authorize_trading_decision(
        self,
        request: TradingDecisionRequest
    ) -> TradingAuthorization:
        """
        Authorize with circuit breaker checks
        
        NEW FLOW:
        1. Circuit breaker checks (FIRST)
        2. Pre-trade compliance (SECOND)
        3. Risk authorization (THIRD)
        """
        
        # STEP 0: CIRCUIT BREAKER CHECKS (FIRST - HIGHEST PRIORITY)
        breaker_status = await self.circuit_breakers.check_circuit_breakers(
            current_pnl=self.daily_pnl,
            portfolio_value=self.portfolio_value
        )
        
        if not breaker_status.can_trade:
            # REJECT: Circuit breaker triggered
            return TradingAuthorization(
                authorization_id=str(uuid.uuid4()),
                request_id=request.request_id,
                authorization_level=AuthorizationLevel.REJECTED,
                authorized=False,
                authorized_quantity=0.0,
                authorization_timestamp=datetime.now(),
                risk_budget_allocated=0.0,
                rejection_reason=f"CIRCUIT BREAKER: {breaker_status.reason}",
                expiry_time=datetime.now()
            )
        
        # Register order for rate limiting
        self.circuit_breakers.register_order()
        
        # STEP 1: Compliance checks
        # ... (as before)
        
        # STEP 2: Risk checks
        # ... (as before)
        
        return authorization
```

### Manual Kill Switch API

```python
class SystemKillSwitch:
    """Manual kill switch interface"""
    
    def __init__(self, circuit_breakers: TradingCircuitBreakers):
        self.circuit_breakers = circuit_breakers
    
    async def emergency_halt(self, reason: str, auth_code: str):
        """
        Manual emergency halt
        
        Requires authorization code for safety
        """
        if self._validate_auth_code(auth_code):
            await self.circuit_breakers.halt_system(f"MANUAL HALT: {reason}")
            return True
        return False
    
    async def resume_trading(self, override_code: str):
        """Resume trading after halt"""
        return self.circuit_breakers.resume_trading(override_code)
```
```

---

## Rule 7 Enhancements: Real-Time P&L, Reconciliation & Execution Quality

### NEW SECTION: Phase 10A - Real-Time P&L Tracking (HIGH PRIORITY) 🟠

**Insert After Phase 10, Before Phase 11**

```markdown
## Phase 10A: Real-Time P&L Tracking (HIGH PRIORITY) 🟠

**Component:** RealTimePnLTracker (NEW)  
**File:** `core_engine/system/pnl_tracker.py`  
**Authority:** GOVERNANCE_CONTROL  
**Responsibility:** Track mark-to-market P&L in real-time

### Why Real-Time P&L is Critical

**Institutional Requirements:**
- Mark-to-market P&L updates every tick
- Position-level P&L attribution  
- Strategy-level P&L attribution
- Intraday high-water mark tracking
- Drawdown monitoring from high
- Risk alerts on excessive losses

**Failure Impact:**
- Poor risk monitoring (don't know current losses)
- Delayed response to losing positions
- Inability to enforce intraday risk limits
- Regulatory reporting issues
- Trader dashboard shows stale data

### Real-Time P&L Architecture

```
Market Data Tick
         ↓
┌────────────────────────────────────────────┐
│ RealTimePnLTracker (NEW)                  │
│                                            │
│ Updates (EVERY TICK):                     │
│ 1. Unrealized P&L (mark-to-market)        │
│ 2. Realized P&L (closed positions)        │
│ 3. Total P&L (realized + unrealized)      │
│ 4. Intraday high-water mark              │
│ 5. Drawdown from high                     │
│ 6. Position-level P&L                     │
│ 7. Strategy-level P&L                     │
│                                            │
│ Output: P&LSnapshot                        │
│   - current_pnl: float                    │
│   - daily_high: float                     │
│   - drawdown_pct: float                   │
│   - by_position: Dict[symbol, float]      │
│   - by_strategy: Dict[strategy_id, float] │
└────────────────────────────────────────────┘
         ↓
   Circuit Breakers (use for loss limits)
   Risk Monitoring (use for alerts)
   Trader Dashboard (use for display)
```

### Implementation: RealTimePnLTracker

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class PnLSnapshot:
    """Real-time P&L snapshot"""
    timestamp: datetime
    
    # Total P&L
    realized_pnl: float          # Closed positions
    unrealized_pnl: float        # Open positions (mark-to-market)
    total_pnl: float             # Realized + Unrealized
    
    # Intraday Tracking
    daily_high_pnl: float        # Highest total P&L today
    drawdown_from_high: float    # $ drawdown from high
    drawdown_pct: float          # % drawdown from high
    
    # Attribution
    pnl_by_position: Dict[str, float]      # Symbol → P&L
    pnl_by_strategy: Dict[str, float]      # Strategy → P&L
    
    # Position Details
    position_count: int          # Number of open positions
    largest_winner: tuple        # (symbol, pnl)
    largest_loser: tuple         # (symbol, pnl)

class RealTimePnLTracker:
    """
    Real-time P&L tracking (INSTITUTIONAL REQUIREMENT)
    
    Updates mark-to-market P&L on every price tick.
    Required for:
    - Circuit breaker loss limits
    - Intraday risk monitoring
    - Trader dashboards
    - Regulatory reporting
    """
    
    def __init__(self):
        # Position Tracking
        self.positions: Dict[str, float] = {}         # symbol → quantity
        self.position_cost_basis: Dict[str, float] = {}  # symbol → avg entry price
        self.position_strategies: Dict[str, str] = {}    # symbol → strategy_id
        
        # P&L Tracking
        self.realized_pnl = 0.0         # Closed positions
        self.unrealized_pnl = 0.0       # Open positions
        self.daily_high_pnl = 0.0       # Intraday high
        self.daily_start_pnl = 0.0      # Start of day P&L
        
        # Strategy Attribution
        self.strategy_pnl: Dict[str, float] = {}
        self.strategy_realized_pnl: Dict[str, float] = {}
        
        # History
        self.pnl_history: List[PnLSnapshot] = []
        
        logger.info("✅ RealTimePnLTracker initialized")
    
    async def update_real_time_pnl(
        self,
        current_prices: Dict[str, float]
    ) -> PnLSnapshot:
        """
        Update P&L based on current market prices
        
        MANDATORY: Called on every price tick for accurate mark-to-market
        
        Args:
            current_prices: Dict[symbol → current price]
            
        Returns:
            PnLSnapshot with complete P&L breakdown
        """
        # Calculate unrealized P&L (mark-to-market)
        self.unrealized_pnl = 0.0
        pnl_by_position = {}
        
        for symbol, position in self.positions.items():
            if position == 0:
                continue
            
            entry_price = self.position_cost_basis.get(symbol, 0.0)
            current_price = current_prices.get(symbol, entry_price)
            
            # Position P&L = (current_price - entry_price) * quantity
            position_pnl = (current_price - entry_price) * position
            
            self.unrealized_pnl += position_pnl
            pnl_by_position[symbol] = position_pnl
        
        # Total P&L
        total_pnl = self.realized_pnl + self.unrealized_pnl
        
        # Update intraday high
        if total_pnl > self.daily_high_pnl:
            self.daily_high_pnl = total_pnl
        
        # Calculate drawdown from high
        if self.daily_high_pnl > 0:
            drawdown = self.daily_high_pnl - total_pnl
            drawdown_pct = drawdown / abs(self.daily_high_pnl)
        else:
            drawdown = 0.0
            drawdown_pct = 0.0
        
        # Strategy attribution
        pnl_by_strategy = self._calculate_strategy_pnl(pnl_by_position)
        
        # Find largest winner/loser
        if pnl_by_position:
            largest_winner = max(pnl_by_position.items(), key=lambda x: x[1])
            largest_loser = min(pnl_by_position.items(), key=lambda x: x[1])
        else:
            largest_winner = ('N/A', 0.0)
            largest_loser = ('N/A', 0.0)
        
        # Create snapshot
        snapshot = PnLSnapshot(
            timestamp=datetime.now(),
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
            total_pnl=total_pnl,
            daily_high_pnl=self.daily_high_pnl,
            drawdown_from_high=drawdown,
            drawdown_pct=drawdown_pct,
            pnl_by_position=pnl_by_position,
            pnl_by_strategy=pnl_by_strategy,
            position_count=len([p for p in self.positions.values() if p != 0]),
            largest_winner=largest_winner,
            largest_loser=largest_loser
        )
        
        # Store in history (keep last 1000 snapshots)
        self.pnl_history.append(snapshot)
        if len(self.pnl_history) > 1000:
            self.pnl_history = self.pnl_history[-1000:]
        
        # Log significant events
        if drawdown_pct > 0.03:  # 3% drawdown
            logger.warning(
                f"⚠️ Drawdown {drawdown_pct:.1%} from high "
                f"(${drawdown:,.2f} from ${self.daily_high_pnl:,.2f})"
            )
        
        return snapshot
    
    def on_position_entry(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        strategy_id: str
    ):
        """
        Record position entry
        
        Updates cost basis for P&L calculation
        """
        current_position = self.positions.get(symbol, 0.0)
        current_cost_basis = self.position_cost_basis.get(symbol, 0.0)
        
        # Update position
        new_position = current_position + quantity
        
        # Update cost basis (weighted average)
        if new_position != 0:
            total_cost = (current_position * current_cost_basis) + (quantity * entry_price)
            new_cost_basis = total_cost / new_position
        else:
            new_cost_basis = 0.0
        
        self.positions[symbol] = new_position
        self.position_cost_basis[symbol] = new_cost_basis
        self.position_strategies[symbol] = strategy_id
        
        logger.info(
            f"📊 Position entry: {symbol} {quantity} @ ${entry_price:.2f} "
            f"(new position: {new_position}, cost basis: ${new_cost_basis:.2f})"
        )
    
    def on_position_exit(
        self,
        symbol: str,
        quantity: float,
        exit_price: float
    ) -> float:
        """
        Record position exit and calculate realized P&L
        
        Returns: Realized P&L from this exit
        """
        entry_price = self.position_cost_basis.get(symbol, 0.0)
        
        # Calculate realized P&L
        realized_pnl = (exit_price - entry_price) * quantity
        
        # Update realized P&L totals
        self.realized_pnl += realized_pnl
        
        # Update strategy P&L
        strategy_id = self.position_strategies.get(symbol, 'unknown')
        if strategy_id not in self.strategy_realized_pnl:
            self.strategy_realized_pnl[strategy_id] = 0.0
        self.strategy_realized_pnl[strategy_id] += realized_pnl
        
        # Update position
        current_position = self.positions.get(symbol, 0.0)
        new_position = current_position - quantity
        self.positions[symbol] = new_position
        
        # If position closed, remove cost basis
        if abs(new_position) < 0.01:
            self.positions.pop(symbol, None)
            self.position_cost_basis.pop(symbol, None)
            self.position_strategies.pop(symbol, None)
        
        logger.info(
            f"💰 Position exit: {symbol} {quantity} @ ${exit_price:.2f} "
            f"(realized P&L: ${realized_pnl:,.2f})"
        )
        
        return realized_pnl
    
    def _calculate_strategy_pnl(
        self,
        pnl_by_position: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate P&L attribution by strategy"""
        strategy_pnl = {}
        
        for symbol, position_pnl in pnl_by_position.items():
            strategy_id = self.position_strategies.get(symbol, 'unknown')
            
            if strategy_id not in strategy_pnl:
                strategy_pnl[strategy_id] = 0.0
            
            # Add unrealized P&L
            strategy_pnl[strategy_id] += position_pnl
            
            # Add realized P&L
            realized = self.strategy_realized_pnl.get(strategy_id, 0.0)
            if realized != 0:
                strategy_pnl[strategy_id] += realized
        
        return strategy_pnl
    
    def reset_daily(self):
        """Reset daily P&L tracking (called at market open)"""
        self.daily_start_pnl = self.realized_pnl + self.unrealized_pnl
        self.daily_high_pnl = 0.0
        logger.info("🔄 Daily P&L tracking reset")
```

### Integration with CentralRiskManager

```python
class CentralRiskManager:
    """Enhanced with real-time P&L tracking"""
    
    def __init__(self, config):
        super().__init__(config)
        
        # NEW: Real-time P&L tracker
        self.pnl_tracker = RealTimePnLTracker()
    
    def update_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        strategy_id: str,
        timestamp: datetime
    ):
        """
        Update position with P&L tracking
        
        ENHANCED: Now updates real-time P&L
        """
        # Update positions (existing logic)
        # ...
        
        # NEW: Update P&L tracking
        if side.lower() == 'buy':
            self.pnl_tracker.on_position_entry(symbol, quantity, price, strategy_id)
        elif side.lower() == 'sell':
            realized_pnl = self.pnl_tracker.on_position_exit(symbol, quantity, price)
            logger.info(f"💰 Realized P&L: ${realized_pnl:,.2f}")
    
    async def get_current_pnl(self, current_prices: Dict[str, float]) -> PnLSnapshot:
        """Get current P&L snapshot (called every tick)"""
        return await self.pnl_tracker.update_real_time_pnl(current_prices)
```

### Real-Time P&L Dashboard

```python
class PnLDashboard:
    """Real-time P&L monitoring dashboard"""
    
    def __init__(self, pnl_tracker: RealTimePnLTracker):
        self.pnl_tracker = pnl_tracker
    
    async def display_current_pnl(self) -> str:
        """Display current P&L status"""
        snapshot = self.pnl_tracker.pnl_history[-1]
        
        return f"""
        📊 REAL-TIME P&L DASHBOARD
        ═══════════════════════════════════════
        Total P&L:        ${snapshot.total_pnl:>12,.2f}
        Realized P&L:     ${snapshot.realized_pnl:>12,.2f}
        Unrealized P&L:   ${snapshot.unrealized_pnl:>12,.2f}
        
        Daily High:       ${snapshot.daily_high_pnl:>12,.2f}
        Drawdown:         ${snapshot.drawdown_from_high:>12,.2f} ({snapshot.drawdown_pct:.1%})
        
        Open Positions:   {snapshot.position_count}
        Largest Winner:   {snapshot.largest_winner[0]}: ${snapshot.largest_winner[1]:,.2f}
        Largest Loser:    {snapshot.largest_loser[0]}: ${snapshot.largest_loser[1]:,.2f}
        
        BY STRATEGY:
        {self._format_strategy_pnl(snapshot.pnl_by_strategy)}
        """
    
    def _format_strategy_pnl(self, strategy_pnl: Dict[str, float]) -> str:
        lines = []
        for strategy_id, pnl in sorted(strategy_pnl.items(), key=lambda x: -x[1]):
            lines.append(f"  {strategy_id:<30} ${pnl:>12,.2f}")
        return "\n".join(lines)
```
```

---

### NEW SECTION: Phase 10B - Position Reconciliation (HIGH PRIORITY) 🟠

**Insert After Real-Time P&L**

```markdown
## Phase 10B: Position Reconciliation with Broker (HIGH PRIORITY) 🟠

**Component:** PositionReconciliation (NEW)  
**File:** `core_engine/system/position_reconciliation.py`  
**Authority:** GOVERNANCE_CONTROL  
**Responsibility:** Ensure internal positions match broker positions

### Why Position Reconciliation is Critical

**Real-World Risk:**
- Internal position tracking can drift from broker
- Partial fills not properly recorded
- Corporate actions (splits, dividends) not reflected
- Manual trades outside system
- System bugs causing position errors

**Failure Impact:**
- Trade on wrong positions (think you have 100, actually have 0)
- Risk calculations based on incorrect positions
- Regulatory violations (position limit breaches)
- Failed trades (insufficient position to sell)
- P&L inaccuracies

### Reconciliation Architecture

```
Every 5 Minutes:
         ↓
┌────────────────────────────────────────────┐
│ PositionReconciliation (NEW)               │
│                                            │
│ Process:                                   │
│ 1. Get broker positions (API call)        │
│ 2. Get internal positions                 │
│ 3. Compare all symbols                    │
│ 4. Identify discrepancies                 │
│ 5. Log and alert discrepancies            │
│ 6. Auto-correct OR escalate               │
│                                            │
│ Output: ReconciliationReport              │
│   - matching_positions: List[str]         │
│   - discrepancies: List[Discrepancy]      │
│   - total_discrepancy_value: float        │
│   - action_taken: str                     │
└────────────────────────────────────────────┘
         ↓
   IF discrepancies → Alert risk team
   IF large discrepancy → Auto-correct to broker
```

### Implementation: PositionReconciliation

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class PositionDiscrepancy:
    """Position mismatch between internal and broker"""
    symbol: str
    internal_position: float
    broker_position: float
    difference: float
    difference_pct: float
    market_value_difference: float
    severity: str  # 'minor', 'moderate', 'severe'

@dataclass
class ReconciliationReport:
    """Position reconciliation report"""
    timestamp: datetime
    matching_positions: List[str]
    discrepancies: List[PositionDiscrepancy]
    total_symbols_checked: int
    total_discrepancy_value: float
    action_taken: str
    
    @property
    def has_discrepancies(self) -> bool:
        return len(self.discrepancies) > 0

class PositionReconciliation:
    """
    Position reconciliation engine (INSTITUTIONAL REQUIREMENT)
    
    Reconciles internal positions with broker every 5 minutes.
    Critical for detecting position drift and ensuring accuracy.
    """
    
    def __init__(self, broker_api, risk_manager):
        self.broker_api = broker_api
        self.risk_manager = risk_manager
        
        # Configuration
        self.tolerance = 0.01  # 0.01 share tolerance
        self.reconciliation_interval = 300  # 5 minutes
        
        # Tracking
        self.reconciliation_history: List[ReconciliationReport] = []
        self.last_reconciliation: Optional[datetime] = None
        
        logger.info("✅ PositionReconciliation initialized")
    
    async def reconcile_positions(self) -> ReconciliationReport:
        """
        Reconcile internal positions with broker
        
        MANDATORY: Run every 5 minutes during trading
        
        Returns: ReconciliationReport with any discrepancies found
        """
        try:
            # Step 1: Get broker positions
            broker_positions = await self._get_broker_positions()
            
            # Step 2: Get internal positions
            internal_positions = self.risk_manager.current_positions.copy()
            
            # Step 3: Find all symbols (union of both)
            all_symbols = set(broker_positions.keys()) | set(internal_positions.keys())
            
            # Step 4: Check each symbol
            discrepancies = []
            matching = []
            
            for symbol in all_symbols:
                internal_pos = internal_positions.get(symbol, 0.0)
                broker_pos = broker_positions.get(symbol, 0.0)
                
                diff = abs(internal_pos - broker_pos)
                
                if diff > self.tolerance:
                    # DISCREPANCY FOUND
                    current_price = await self._get_current_price(symbol)
                    market_value_diff = diff * current_price
                    
                    diff_pct = (diff / max(abs(internal_pos), abs(broker_pos), 1.0)) * 100
                    
                    # Determine severity
                    if market_value_diff > 10000:  # $10K+ difference
                        severity = 'severe'
                    elif market_value_diff > 1000:  # $1K-$10K
                        severity = 'moderate'
                    else:
                        severity = 'minor'
                    
                    discrepancy = PositionDiscrepancy(
                        symbol=symbol,
                        internal_position=internal_pos,
                        broker_position=broker_pos,
                        difference=diff,
                        difference_pct=diff_pct,
                        market_value_difference=market_value_diff,
                        severity=severity
                    )
                    
                    discrepancies.append(discrepancy)
                    
                    logger.error(
                        f"🔴 Position discrepancy: {symbol} "
                        f"Internal={internal_pos:.2f}, Broker={broker_pos:.2f}, "
                        f"Diff={diff:.2f} (${market_value_diff:,.2f})"
                    )
                else:
                    matching.append(symbol)
            
            # Step 5: Calculate total discrepancy value
            total_discrepancy_value = sum(d.market_value_difference for d in discrepancies)
            
            # Step 6: Take action on discrepancies
            action_taken = await self._handle_discrepancies(discrepancies)
            
            # Create report
            report = ReconciliationReport(
                timestamp=datetime.now(),
                matching_positions=matching,
                discrepancies=discrepancies,
                total_symbols_checked=len(all_symbols),
                total_discrepancy_value=total_discrepancy_value,
                action_taken=action_taken
            )
            
            # Store history
            self.reconciliation_history.append(report)
            self.last_reconciliation = datetime.now()
            
            # Log summary
            if discrepancies:
                logger.error(
                    f"🔴 Reconciliation FAILED: {len(discrepancies)} discrepancies "
                    f"(${total_discrepancy_value:,.2f} total)"
                )
            else:
                logger.info(
                    f"✅ Reconciliation PASSED: {len(matching)} positions match"
                )
            
            return report
            
        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            return ReconciliationReport(
                timestamp=datetime.now(),
                matching_positions=[],
                discrepancies=[],
                total_symbols_checked=0,
                total_discrepancy_value=0.0,
                action_taken=f"ERROR: {str(e)}"
            )
    
    async def _get_broker_positions(self) -> Dict[str, float]:
        """Get current positions from broker API"""
        try:
            positions = await self.broker_api.get_positions()
            return {pos['symbol']: pos['quantity'] for pos in positions}
        except Exception as e:
            logger.error(f"Failed to get broker positions: {e}")
            return {}
    
    async def _get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        try:
            quote = await self.broker_api.get_quote(symbol)
            return quote['price']
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
            return 100.0  # Fallback
    
    async def _handle_discrepancies(
        self,
        discrepancies: List[PositionDiscrepancy]
    ) -> str:
        """
        Handle position discrepancies
        
        Strategy:
        - Minor: Log and monitor
        - Moderate: Alert risk team
        - Severe: Auto-correct to broker + alert
        """
        if not discrepancies:
            return "No action needed"
        
        actions = []
        
        for disc in discrepancies:
            if disc.severity == 'severe':
                # Auto-correct to broker (trust broker over internal)
                await self._auto_correct_position(disc)
                actions.append(f"Auto-corrected {disc.symbol} to broker position")
                
                # Alert risk team
                await self._alert_risk_team(disc)
                actions.append(f"Alerted risk team about {disc.symbol}")
                
            elif disc.severity == 'moderate':
                # Alert only
                await self._alert_risk_team(disc)
                actions.append(f"Alerted risk team about {disc.symbol}")
                
            else:  # minor
                # Log only
                actions.append(f"Logged minor discrepancy in {disc.symbol}")
        
        return "; ".join(actions)
    
    async def _auto_correct_position(self, disc: PositionDiscrepancy):
        """
        Auto-correct internal position to match broker
        
        CRITICAL DECISION: Trust broker over internal tracking
        """
        logger.critical(
            f"🔧 Auto-correcting position: {disc.symbol} "
            f"{disc.internal_position} → {disc.broker_position}"
        )
        
        # Update internal position to broker position
        self.risk_manager.current_positions[disc.symbol] = disc.broker_position
        
        # Log correction
        self.risk_manager.position_history.append({
            'timestamp': datetime.now(),
            'symbol': disc.symbol,
            'action': 'reconciliation_correction',
            'previous_position': disc.internal_position,
            'new_position': disc.broker_position,
            'difference': disc.difference
        })
    
    async def _alert_risk_team(self, disc: PositionDiscrepancy):
        """Send alert to risk team"""
        logger.critical(
            f"📧 Risk team alert: Position discrepancy in {disc.symbol} "
            f"(${disc.market_value_difference:,.2f} difference)"
        )
        # Implementation would send email/SMS/Slack
```

### Automated Reconciliation Schedule

```python
class ReconciliationScheduler:
    """Automated position reconciliation"""
    
    def __init__(self, reconciliation: PositionReconciliation):
        self.reconciliation = reconciliation
        self.running = False
    
    async def start_reconciliation_loop(self):
        """Run reconciliation every 5 minutes"""
        self.running = True
        
        while self.running:
            try:
                # Reconcile positions
                report = await self.reconciliation.reconcile_positions()
                
                # If severe discrepancies, increase frequency
                if any(d.severity == 'severe' for d in report.discrepancies):
                    logger.warning("⚠️ Severe discrepancies - increasing reconciliation frequency")
                    await asyncio.sleep(60)  # Check every minute
                else:
                    await asyncio.sleep(300)  # Normal: every 5 minutes
                    
            except Exception as e:
                logger.error(f"Reconciliation loop error: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute
```
```

---

## Next Steps

1. ✅ Document Rule 4 enhancements (compliance + circuit breakers)
2. ✅ Document Rule 7 enhancements (P&L + reconciliation) 
3. ⏳ Document Rule 7 enhancements (order rejection + position aging)
4. ⏳ Document Rule 2 enhancements (fast regime detection)
5. ⏳ Update actual rule files with enhancements
6. ⏳ Re-audit core_engine against enhanced rules

---

**Status:** Rules 4 & 7 (partial) enhancements documented
**Next:** Complete Rule 7 enhancements, then Rules 1, 2, 5

