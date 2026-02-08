"""
Execution Engine - Execution Validator
Comprehensive execution validation, compliance checking, and quality assurance
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationCategory(Enum):
    """Validation categories"""
    PRE_TRADE = "pre_trade"
    REAL_TIME = "real_time"
    POST_TRADE = "post_trade"
    COMPLIANCE = "compliance"
    RISK = "risk"
    PERFORMANCE = "performance"

class ValidationAction(Enum):
    """Actions to take on validation failure"""
    LOG_ONLY = "log_only"
    WARN = "warn"
    BLOCK = "block"
    CANCEL = "cancel"
    REDUCE_SIZE = "reduce_size"
    ALERT = "alert"

@dataclass
class ValidationRule:
    """Execution validation rule"""
    rule_id: str
    rule_name: str
    description: str
    category: ValidationCategory
    severity: ValidationSeverity
    action: ValidationAction

    # Rule parameters
    enabled: bool = True
    priority: int = 1

    # Thresholds
    numeric_threshold: Optional[float] = None
    percentage_threshold: Optional[float] = None
    time_threshold: Optional[timedelta] = None

    # Constraints
    symbols: Optional[List[str]] = None
    strategies: Optional[List[str]] = None
    venues: Optional[List[str]] = None

    # Timing
    market_hours_only: bool = False
    business_days_only: bool = False

    # Custom validation function
    custom_validator: Optional[Callable] = None

    # Metadata
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)

@dataclass
class ValidationResult:
    """Result of validation check"""
    rule_id: str
    rule_name: str
    category: ValidationCategory
    severity: ValidationSeverity
    action: ValidationAction

    # Result details
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    # Context
    execution_id: Optional[str] = None
    order_id: Optional[str] = None
    symbol: Optional[str] = None

    # Timing
    check_time: datetime = field(default_factory=datetime.now)

    # Actions taken
    action_taken: Optional[str] = None
    action_details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionContext:
    """Execution context for validation"""
    execution_id: str
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: Optional[float] = None

    # Execution details
    order_type: str = "LIMIT"
    time_in_force: str = "DAY"
    venue: Optional[str] = None

    # Strategy context
    strategy_id: Optional[str] = None
    portfolio_id: Optional[str] = None

    # Market context
    current_price: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    spread: Optional[float] = None
    volatility: Optional[float] = None

    # Risk context
    current_position: float = 0.0
    notional_exposure: float = 0.0
    portfolio_value: Optional[float] = None

    # Timing context
    submission_time: datetime = field(default_factory=datetime.now)
    expected_execution_time: Optional[datetime] = None

    # Previous executions
    recent_executions: List[Dict[str, Any]] = field(default_factory=list)

class PreTradeValidator:
    """Pre-trade execution validation"""

    def __init__(self):
        self.rules = {}
        self._load_default_pre_trade_rules()

    def _load_default_pre_trade_rules(self) -> None:
        """Load default pre-trade validation rules"""

        rules = [
            ValidationRule(
                rule_id="order_size_limit",
                rule_name="Order Size Limit",
                description="Validate order size doesn't exceed limits",
                category=ValidationCategory.PRE_TRADE,
                severity=ValidationSeverity.ERROR,
                action=ValidationAction.BLOCK,
                numeric_threshold=1_000_000  # 1M shares
            ),
            ValidationRule(
                rule_id="notional_limit",
                rule_name="Notional Amount Limit",
                description="Validate notional amount doesn't exceed limits",
                category=ValidationCategory.PRE_TRADE,
                severity=ValidationSeverity.ERROR,
                action=ValidationAction.BLOCK,
                numeric_threshold=100_000_000  # $100M
            ),
            ValidationRule(
                rule_id="price_reasonableness",
                rule_name="Price Reasonableness Check",
                description="Validate order price is reasonable vs market",
                category=ValidationCategory.PRE_TRADE,
                severity=ValidationSeverity.WARNING,
                action=ValidationAction.WARN,
                percentage_threshold=0.05  # 5% from market
            ),
            ValidationRule(
                rule_id="market_hours",
                rule_name="Market Hours Check",
                description="Validate order submitted during market hours",
                category=ValidationCategory.PRE_TRADE,
                severity=ValidationSeverity.WARNING,
                action=ValidationAction.WARN,
                market_hours_only=True
            ),
            ValidationRule(
                rule_id="position_concentration",
                rule_name="Position Concentration Check",
                description="Validate position doesn't exceed concentration limits",
                category=ValidationCategory.PRE_TRADE,
                severity=ValidationSeverity.ERROR,
                action=ValidationAction.REDUCE_SIZE,
                percentage_threshold=0.1  # 10% of portfolio
            ),
            ValidationRule(
                rule_id="duplicate_order",
                rule_name="Duplicate Order Check",
                description="Check for potential duplicate orders",
                category=ValidationCategory.PRE_TRADE,
                severity=ValidationSeverity.WARNING,
                action=ValidationAction.WARN,
                time_threshold=timedelta(seconds=30)
            )
        ]

        for rule in rules:
            self.rules[rule.rule_id] = rule

    def validate_execution(self, context: ExecutionContext) -> List[ValidationResult]:
        """Validate execution against pre-trade rules"""

        results = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            if rule.category != ValidationCategory.PRE_TRADE:
                continue

            # Apply rule filters
            if not self._rule_applies(rule, context):
                continue

            # Run validation
            result = self._apply_rule(rule, context)
            results.append(result)

        return results

    def _rule_applies(self, rule: ValidationRule, context: ExecutionContext) -> bool:
        """Check if rule applies to execution context"""

        # Symbol filter
        if rule.symbols and context.symbol not in rule.symbols:
            return False

        # Strategy filter
        if rule.strategies and context.strategy_id not in rule.strategies:
            return False

        # Venue filter
        if rule.venues and context.venue not in rule.venues:
            return False

        # Market hours filter
        if rule.market_hours_only:
            if not self._is_market_hours(context.submission_time):
                return False

        # Business days filter
        if rule.business_days_only:
            if context.submission_time.weekday() >= 5:  # Weekend
                return False

        return True

    def _apply_rule(self, rule: ValidationRule, context: ExecutionContext) -> ValidationResult:
        """Apply validation rule to execution context"""

        result = ValidationResult(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            category=rule.category,
            severity=rule.severity,
            action=rule.action,
            execution_id=context.execution_id,
            order_id=context.order_id,
            symbol=context.symbol,
            passed=True,
            message="Validation passed"
        )

        try:
            if rule.rule_id == "order_size_limit":
                result = self._validate_order_size(rule, context, result)
            elif rule.rule_id == "notional_limit":
                result = self._validate_notional_limit(rule, context, result)
            elif rule.rule_id == "price_reasonableness":
                result = self._validate_price_reasonableness(rule, context, result)
            elif rule.rule_id == "market_hours":
                result = self._validate_market_hours(rule, context, result)
            elif rule.rule_id == "position_concentration":
                result = self._validate_position_concentration(rule, context, result)
            elif rule.rule_id == "duplicate_order":
                result = self._validate_duplicate_order(rule, context, result)
            elif rule.custom_validator:
                result = rule.custom_validator(rule, context, result)

        except Exception as e:
            result.passed = False
            result.message = f"Validation error: {str(e)}"
            result.details = {"error": str(e)}

        return result

    def _validate_order_size(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        result: ValidationResult
    ) -> ValidationResult:
        """Validate order size"""

        if rule.numeric_threshold and context.quantity > rule.numeric_threshold:
            result.passed = False
            result.message = f"Order size {context.quantity:,.0f} exceeds limit {rule.numeric_threshold:,.0f}"
            result.details = {
                "order_quantity": context.quantity,
                "limit": rule.numeric_threshold,
                "excess": context.quantity - rule.numeric_threshold
            }

        return result

    def _validate_notional_limit(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        result: ValidationResult
    ) -> ValidationResult:
        """Validate notional amount"""

        if context.price:
            notional = context.quantity * context.price

            if rule.numeric_threshold and notional > rule.numeric_threshold:
                result.passed = False
                result.message = f"Notional ${notional:,.2f} exceeds limit ${rule.numeric_threshold:,.2f}"
                result.details = {
                    "notional": notional,
                    "limit": rule.numeric_threshold,
                    "excess": notional - rule.numeric_threshold
                }

        return result

    def _validate_price_reasonableness(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        result: ValidationResult
    ) -> ValidationResult:
        """Validate price reasonableness"""

        if not context.price or not context.current_price:
            return result

        price_deviation = abs(context.price - context.current_price) / context.current_price

        if rule.percentage_threshold and price_deviation > rule.percentage_threshold:
            result.passed = False
            result.message = (
                f"Order price ${context.price:.2f} deviates {price_deviation:.2%} "
                f"from market ${context.current_price:.2f}"
            )
            result.details = {
                "order_price": context.price,
                "market_price": context.current_price,
                "deviation": price_deviation,
                "threshold": rule.percentage_threshold
            }

        return result

    def _validate_market_hours(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        result: ValidationResult
    ) -> ValidationResult:
        """Validate market hours"""

        if not self._is_market_hours(context.submission_time):
            try:
                from core_engine.config.component_config import RiskConfig
                cfg = RiskConfig()
                hours_str = f"{cfg.market_open_hour:02d}:{cfg.market_open_minute:02d}-{cfg.market_close_hour:02d}:{cfg.market_close_minute:02d} ET"
            except Exception:
                hours_str = "09:30-16:00 ET"
            result.passed = False
            result.message = f"Order submitted outside market hours: {context.submission_time.strftime('%H:%M:%S')}"
            result.details = {
                "submission_time": context.submission_time.isoformat(),
                "market_hours": hours_str
            }

        return result

    def _validate_position_concentration(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        result: ValidationResult
    ) -> ValidationResult:
        """Validate position concentration"""

        if not context.portfolio_value:
            return result

        # Calculate new position after execution
        if context.side == 'BUY':
            new_position_value = context.current_position + (context.quantity * (context.price or context.current_price or 0))
        else:
            new_position_value = context.current_position - (context.quantity * (context.price or context.current_price or 0))

        concentration = abs(new_position_value) / context.portfolio_value

        if rule.percentage_threshold and concentration > rule.percentage_threshold:
            result.passed = False
            result.message = (
                f"Position concentration {concentration:.2%} exceeds limit "
                f"{rule.percentage_threshold:.2%}"
            )
            result.details = {
                "new_position_value": new_position_value,
                "portfolio_value": context.portfolio_value,
                "concentration": concentration,
                "limit": rule.percentage_threshold
            }

        return result

    def _validate_duplicate_order(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        result: ValidationResult
    ) -> ValidationResult:
        """Validate for duplicate orders"""

        if not rule.time_threshold:
            return result

        # Check recent executions for potential duplicates
        cutoff_time = context.submission_time - rule.time_threshold

        for recent in context.recent_executions:
            if recent.get('symbol') == context.symbol and recent.get('side') == context.side:
                recent_time = recent.get('submission_time')
                if isinstance(recent_time, str):
                    recent_time = datetime.fromisoformat(recent_time)

                if recent_time and recent_time >= cutoff_time:
                    # Check if quantities are similar (within 10%)
                    recent_qty = recent.get('quantity', 0)
                    if abs(recent_qty - context.quantity) / context.quantity < 0.1:
                        result.passed = False
                        result.message = (
                            f"Potential duplicate order detected: similar order "
                            f"submitted {(context.submission_time - recent_time).total_seconds():.0f}s ago"
                        )
                        result.details = {
                            "recent_order_time": recent_time.isoformat(),
                            "time_difference": (context.submission_time - recent_time).total_seconds(),
                            "threshold_seconds": rule.time_threshold.total_seconds()
                        }
                        break

        return result

    def _is_market_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is during market hours.

        Market hours are configurable via RiskConfig fields:
        market_open_hour/minute and market_close_hour/minute.
        Defaults: 09:30 - 16:00 ET.
        """
        try:
            from core_engine.config.component_config import RiskConfig
            cfg = RiskConfig()
            open_h, open_m = cfg.market_open_hour, cfg.market_open_minute
            close_h, close_m = cfg.market_close_hour, cfg.market_close_minute
        except Exception:
            open_h, open_m = 9, 30
            close_h, close_m = 16, 0

        time_part = timestamp.time()
        market_open = datetime.min.time().replace(hour=open_h, minute=open_m)
        market_close = datetime.min.time().replace(hour=close_h, minute=close_m)

        # Check weekday and time
        return (
            timestamp.weekday() < 5 and  # Monday-Friday
            market_open <= time_part <= market_close
        )

class RealTimeValidator:
    """Real-time execution validation during trading"""

    def __init__(self):
        self.rules = {}
        self._load_default_realtime_rules()

    def _load_default_realtime_rules(self) -> None:
        """Load default real-time validation rules"""

        rules = [
            ValidationRule(
                rule_id="execution_speed",
                rule_name="Execution Speed Check",
                description="Monitor execution speed for performance",
                category=ValidationCategory.REAL_TIME,
                severity=ValidationSeverity.WARNING,
                action=ValidationAction.ALERT,
                time_threshold=timedelta(seconds=10)
            ),
            ValidationRule(
                rule_id="slippage_monitor",
                rule_name="Slippage Monitoring",
                description="Monitor execution slippage",
                category=ValidationCategory.REAL_TIME,
                severity=ValidationSeverity.WARNING,
                action=ValidationAction.ALERT,
                percentage_threshold=0.01  # 1%
            ),
            ValidationRule(
                rule_id="fill_rate_monitor",
                rule_name="Fill Rate Monitoring",
                description="Monitor order fill rates",
                category=ValidationCategory.REAL_TIME,
                severity=ValidationSeverity.INFO,
                action=ValidationAction.LOG_ONLY,
                percentage_threshold=0.5  # 50% minimum fill rate
            ),
            ValidationRule(
                rule_id="market_impact_monitor",
                rule_name="Market Impact Monitoring",
                description="Monitor market impact of executions",
                category=ValidationCategory.REAL_TIME,
                severity=ValidationSeverity.WARNING,
                action=ValidationAction.ALERT,
                percentage_threshold=0.005  # 0.5%
            )
        ]

        for rule in rules:
            self.rules[rule.rule_id] = rule

    def validate_ongoing_execution(
        self,
        context: ExecutionContext,
        execution_metrics: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate ongoing execution"""

        results = []

        for rule in self.rules.values():
            if not rule.enabled or rule.category != ValidationCategory.REAL_TIME:
                continue

            result = self._apply_realtime_rule(rule, context, execution_metrics)
            results.append(result)

        return results

    def _apply_realtime_rule(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        metrics: Dict[str, Any]
    ) -> ValidationResult:
        """Apply real-time validation rule"""

        result = ValidationResult(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            category=rule.category,
            severity=rule.severity,
            action=rule.action,
            execution_id=context.execution_id,
            order_id=context.order_id,
            symbol=context.symbol,
            passed=True,
            message="Real-time validation passed"
        )

        try:
            if rule.rule_id == "execution_speed":
                result = self._validate_execution_speed(rule, context, metrics, result)
            elif rule.rule_id == "slippage_monitor":
                result = self._validate_slippage(rule, context, metrics, result)
            elif rule.rule_id == "fill_rate_monitor":
                result = self._validate_fill_rate(rule, context, metrics, result)
            elif rule.rule_id == "market_impact_monitor":
                result = self._validate_market_impact(rule, context, metrics, result)

        except Exception as e:
            result.passed = False
            result.message = f"Real-time validation error: {str(e)}"

        return result

    def _validate_execution_speed(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        metrics: Dict[str, Any],
        result: ValidationResult
    ) -> ValidationResult:
        """Validate execution speed"""

        execution_time = metrics.get('execution_time_seconds', 0)

        if rule.time_threshold and execution_time > rule.time_threshold.total_seconds():
            result.passed = False
            result.message = f"Slow execution: {execution_time:.1f}s exceeds {rule.time_threshold.total_seconds():.1f}s threshold"
            result.details = {
                "execution_time": execution_time,
                "threshold": rule.time_threshold.total_seconds()
            }

        return result

    def _validate_slippage(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        metrics: Dict[str, Any],
        result: ValidationResult
    ) -> ValidationResult:
        """Validate execution slippage"""

        slippage = metrics.get('slippage', 0)

        if rule.percentage_threshold and abs(slippage) > rule.percentage_threshold:
            result.passed = False
            result.message = f"High slippage: {slippage:.2%} exceeds {rule.percentage_threshold:.2%} threshold"
            result.details = {
                "slippage": slippage,
                "threshold": rule.percentage_threshold
            }

        return result

    def _validate_fill_rate(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        metrics: Dict[str, Any],
        result: ValidationResult
    ) -> ValidationResult:
        """Validate fill rate"""

        fill_rate = metrics.get('fill_rate', 1.0)

        if rule.percentage_threshold and fill_rate < rule.percentage_threshold:
            result.passed = False
            result.message = f"Low fill rate: {fill_rate:.2%} below {rule.percentage_threshold:.2%} threshold"
            result.details = {
                "fill_rate": fill_rate,
                "threshold": rule.percentage_threshold
            }

        return result

    def _validate_market_impact(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        metrics: Dict[str, Any],
        result: ValidationResult
    ) -> ValidationResult:
        """Validate market impact"""

        market_impact = metrics.get('market_impact', 0)

        if rule.percentage_threshold and abs(market_impact) > rule.percentage_threshold:
            result.passed = False
            result.message = f"High market impact: {market_impact:.2%} exceeds {rule.percentage_threshold:.2%} threshold"
            result.details = {
                "market_impact": market_impact,
                "threshold": rule.percentage_threshold
            }

        return result

class PostTradeValidator:
    """Post-trade execution validation and compliance"""

    def __init__(self):
        self.rules = {}
        self._load_default_post_trade_rules()

    def _load_default_post_trade_rules(self) -> None:
        """Load default post-trade validation rules"""

        rules = [
            ValidationRule(
                rule_id="best_execution",
                rule_name="Best Execution Analysis",
                description="Analyze if best execution was achieved",
                category=ValidationCategory.POST_TRADE,
                severity=ValidationSeverity.INFO,
                action=ValidationAction.LOG_ONLY
            ),
            ValidationRule(
                rule_id="transaction_cost_analysis",
                rule_name="Transaction Cost Analysis",
                description="Analyze transaction costs",
                category=ValidationCategory.POST_TRADE,
                severity=ValidationSeverity.INFO,
                action=ValidationAction.LOG_ONLY
            ),
            ValidationRule(
                rule_id="venue_performance",
                rule_name="Venue Performance Analysis",
                description="Analyze execution venue performance",
                category=ValidationCategory.POST_TRADE,
                severity=ValidationSeverity.INFO,
                action=ValidationAction.LOG_ONLY
            ),
            ValidationRule(
                rule_id="regulatory_reporting",
                rule_name="Regulatory Reporting Check",
                description="Check regulatory reporting requirements",
                category=ValidationCategory.COMPLIANCE,
                severity=ValidationSeverity.ERROR,
                action=ValidationAction.ALERT
            )
        ]

        for rule in rules:
            self.rules[rule.rule_id] = rule

    def validate_completed_execution(
        self,
        context: ExecutionContext,
        execution_results: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate completed execution"""

        results = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            if rule.category not in [ValidationCategory.POST_TRADE, ValidationCategory.COMPLIANCE]:
                continue

            result = self._apply_post_trade_rule(rule, context, execution_results)
            results.append(result)

        return results

    def _apply_post_trade_rule(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        results: Dict[str, Any]
    ) -> ValidationResult:
        """Apply post-trade validation rule"""

        result = ValidationResult(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            category=rule.category,
            severity=rule.severity,
            action=rule.action,
            execution_id=context.execution_id,
            order_id=context.order_id,
            symbol=context.symbol,
            passed=True,
            message="Post-trade validation passed"
        )

        try:
            if rule.rule_id == "best_execution":
                result = self._analyze_best_execution(rule, context, results, result)
            elif rule.rule_id == "transaction_cost_analysis":
                result = self._analyze_transaction_costs(rule, context, results, result)
            elif rule.rule_id == "venue_performance":
                result = self._analyze_venue_performance(rule, context, results, result)
            elif rule.rule_id == "regulatory_reporting":
                result = self._check_regulatory_reporting(rule, context, results, result)

        except Exception as e:
            result.passed = False
            result.message = f"Post-trade validation error: {str(e)}"

        return result

    def _analyze_best_execution(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        results: Dict[str, Any],
        result: ValidationResult
    ) -> ValidationResult:
        """Analyze best execution"""

        # Simple best execution analysis
        avg_price = results.get('avg_execution_price', 0)
        market_price = context.current_price or 0

        if market_price > 0:
            execution_quality = abs(avg_price - market_price) / market_price

            result.details = {
                "avg_execution_price": avg_price,
                "market_price_at_arrival": market_price,
                "execution_quality": execution_quality,
                "assessment": "good" if execution_quality < 0.001 else "needs_review"
            }

            result.message = f"Best execution analysis: {execution_quality:.4f} price deviation"

        return result

    def _analyze_transaction_costs(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        results: Dict[str, Any],
        result: ValidationResult
    ) -> ValidationResult:
        """Analyze transaction costs"""

        total_slippage = results.get('total_slippage', 0)
        market_impact = results.get('market_impact', 0)
        commission = results.get('commission', 0)

        notional = context.quantity * (context.price or context.current_price or 0)
        total_cost_bps = 0

        if notional > 0:
            total_cost_bps = ((abs(total_slippage) + abs(market_impact)) * notional + commission) / notional * 10000

        result.details = {
            "slippage_bps": total_slippage * 10000,
            "market_impact_bps": market_impact * 10000,
            "commission": commission,
            "total_cost_bps": total_cost_bps
        }

        result.message = f"Transaction cost analysis: {total_cost_bps:.1f} bps total cost"

        return result

    def _analyze_venue_performance(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        results: Dict[str, Any],
        result: ValidationResult
    ) -> ValidationResult:
        """Analyze venue performance"""

        venue_breakdown = results.get('venue_breakdown', {})

        if venue_breakdown:
            best_venue = min(venue_breakdown.items(), key=lambda x: x[1].get('avg_slippage', float('inf')))
            worst_venue = max(venue_breakdown.items(), key=lambda x: x[1].get('avg_slippage', 0))

            result.details = {
                "venues_used": list(venue_breakdown.keys()),
                "best_venue": best_venue[0],
                "best_venue_slippage": best_venue[1].get('avg_slippage', 0),
                "worst_venue": worst_venue[0],
                "worst_venue_slippage": worst_venue[1].get('avg_slippage', 0)
            }

            result.message = f"Venue performance: {len(venue_breakdown)} venues used"

        return result

    def _check_regulatory_reporting(
        self,
        rule: ValidationRule,
        context: ExecutionContext,
        results: Dict[str, Any],
        result: ValidationResult
    ) -> ValidationResult:
        """Check regulatory reporting requirements"""

        # Simple regulatory check
        notional = context.quantity * (context.price or context.current_price or 0)

        # Example: Large trade reporting threshold
        if notional > 10_000_000:  # $10M threshold
            result.details = {
                "notional": notional,
                "requires_reporting": True,
                "reporting_type": "large_trade"
            }
            result.message = "Large trade reporting required"
        else:
            result.details = {
                "notional": notional,
                "requires_reporting": False
            }
            result.message = "No special reporting required"

        return result

class ExecutionValidator:
    """
    Advanced Execution Validator

    Comprehensive validation system for trade execution with pre-trade,
    real-time, and post-trade validation capabilities.
    """

    def __init__(self):
        """Initialize execution validator"""

        # Validation engines
        self.pre_trade_validator = PreTradeValidator()
        self.realtime_validator = RealTimeValidator()
        self.post_trade_validator = PostTradeValidator()

        # Validation history
        self._validation_history = []
        self._failed_validations = defaultdict(list)

        # Configuration
        self.block_on_critical = True
        self.alert_on_warnings = True

        # Callbacks
        self._validation_callbacks = []

        # Threading
        # NOTE: threading.Lock intentionally kept (not asyncio.Lock) because this lock
        # is used in sync methods (validate_pre_trade, validate_real_time,
        # validate_post_trade, get_validation_summary, get_validation_history).
        # No async methods use this lock, so there is no event loop blocking issue.
        self._lock = threading.Lock()

        logger.info("Execution Validator initialized")

    def validate_pre_trade(self, context: ExecutionContext) -> Tuple[bool, List[ValidationResult]]:
        """Perform pre-trade validation"""

        try:
            results = self.pre_trade_validator.validate_execution(context)

            # Process results
            critical_failures = [r for r in results if not r.passed and r.severity == ValidationSeverity.CRITICAL]
            error_failures = [r for r in results if not r.passed and r.severity == ValidationSeverity.ERROR]

            # Determine if execution should be blocked
            should_block = False
            if self.block_on_critical and (critical_failures or error_failures):
                should_block = True

            # Store results
            with self._lock:
                self._validation_history.extend(results)
                for result in results:
                    if not result.passed:
                        self._failed_validations[result.rule_id].append(result)

            # Trigger callbacks
            for result in results:
                self._trigger_validation_callbacks(result)

            logger.info(f"Pre-trade validation completed for {context.execution_id}: {len(results)} checks")

            return not should_block, results

        except Exception as e:
            logger.error(f"Error in pre-trade validation: {e}")
            return False, []

    def validate_real_time(
        self,
        context: ExecutionContext,
        execution_metrics: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Perform real-time validation during execution"""

        try:
            results = self.realtime_validator.validate_ongoing_execution(context, execution_metrics)

            # Store results
            with self._lock:
                self._validation_history.extend(results)
                for result in results:
                    if not result.passed:
                        self._failed_validations[result.rule_id].append(result)

            # Trigger callbacks
            for result in results:
                self._trigger_validation_callbacks(result)

            logger.debug(f"Real-time validation completed for {context.execution_id}: {len(results)} checks")

            return results

        except Exception as e:
            logger.error(f"Error in real-time validation: {e}")
            return []

    def validate_post_trade(
        self,
        context: ExecutionContext,
        execution_results: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Perform post-trade validation and analysis"""

        try:
            results = self.post_trade_validator.validate_completed_execution(context, execution_results)

            # Store results
            with self._lock:
                self._validation_history.extend(results)
                for result in results:
                    if not result.passed:
                        self._failed_validations[result.rule_id].append(result)

            # Trigger callbacks
            for result in results:
                self._trigger_validation_callbacks(result)

            logger.info(f"Post-trade validation completed for {context.execution_id}: {len(results)} checks")

            return results

        except Exception as e:
            logger.error(f"Error in post-trade validation: {e}")
            return []

    def add_custom_rule(self, rule: ValidationRule) -> None:
        """Add custom validation rule"""

        if rule.category == ValidationCategory.PRE_TRADE:
            self.pre_trade_validator.rules[rule.rule_id] = rule
        elif rule.category == ValidationCategory.REAL_TIME:
            self.realtime_validator.rules[rule.rule_id] = rule
        elif rule.category in [ValidationCategory.POST_TRADE, ValidationCategory.COMPLIANCE]:
            self.post_trade_validator.rules[rule.rule_id] = rule

        logger.info(f"Added custom validation rule: {rule.rule_id}")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove validation rule"""

        removed = False

        if rule_id in self.pre_trade_validator.rules:
            del self.pre_trade_validator.rules[rule_id]
            removed = True

        if rule_id in self.realtime_validator.rules:
            del self.realtime_validator.rules[rule_id]
            removed = True

        if rule_id in self.post_trade_validator.rules:
            del self.post_trade_validator.rules[rule_id]
            removed = True

        if removed:
            logger.info(f"Removed validation rule: {rule_id}")

        return removed

    def add_validation_callback(self, callback: Callable[[ValidationResult], None]) -> None:
        """Add callback for validation events"""
        self._validation_callbacks.append(callback)

    def _trigger_validation_callbacks(self, result: ValidationResult) -> None:
        """Trigger validation callbacks"""

        for callback in self._validation_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in validation callback: {e}")

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation summary statistics"""

        with self._lock:
            total_validations = len(self._validation_history)
            failed_validations = len([r for r in self._validation_history if not r.passed])

            # Group by category
            category_stats = defaultdict(lambda: {'total': 0, 'failed': 0})
            for result in self._validation_history:
                category_stats[result.category.value]['total'] += 1
                if not result.passed:
                    category_stats[result.category.value]['failed'] += 1

            # Group by severity
            severity_stats = defaultdict(lambda: {'total': 0, 'failed': 0})
            for result in self._validation_history:
                severity_stats[result.severity.value]['total'] += 1
                if not result.passed:
                    severity_stats[result.severity.value]['failed'] += 1

            return {
                'total_validations': total_validations,
                'failed_validations': failed_validations,
                'success_rate': (total_validations - failed_validations) / total_validations if total_validations > 0 else 0,
                'category_breakdown': dict(category_stats),
                'severity_breakdown': dict(severity_stats),
                'most_failed_rules': self._get_most_failed_rules()
            }

    def _get_most_failed_rules(self) -> List[Dict[str, Any]]:
        """Get rules with most failures"""

        rule_failures = [
            {
                'rule_id': rule_id,
                'failure_count': len(failures),
                'latest_failure': max(f.check_time for f in failures) if failures else None
            }
            for rule_id, failures in self._failed_validations.items()
        ]

        # Sort by failure count
        rule_failures.sort(key=lambda x: x['failure_count'], reverse=True)

        return rule_failures[:10]  # Top 10

    def get_validation_history(
        self,
        execution_id: Optional[str] = None,
        rule_id: Optional[str] = None,
        category: Optional[ValidationCategory] = None,
        failed_only: bool = False
    ) -> List[ValidationResult]:
        """Get validation history with filtering"""

        with self._lock:
            results = self._validation_history.copy()

        # Apply filters
        if execution_id:
            results = [r for r in results if r.execution_id == execution_id]

        if rule_id:
            results = [r for r in results if r.rule_id == rule_id]

        if category:
            results = [r for r in results if r.category == category]

        if failed_only:
            results = [r for r in results if not r.passed]

        # Sort by check time (most recent first)
        results.sort(key=lambda x: x.check_time, reverse=True)

        return results

    def generate_validation_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive validation report"""

        # Filter by date range
        history = self._validation_history
        if start_date or end_date:
            history = [
                r for r in history
                if (not start_date or r.check_time >= start_date) and
                   (not end_date or r.check_time <= end_date)
            ]

        if not history:
            return {'report_period': 'No data', 'total_validations': 0}

        # Calculate metrics
        total_validations = len(history)
        failed_validations = len([r for r in history if not r.passed])
        success_rate = (total_validations - failed_validations) / total_validations

        # Group by various dimensions
        category_breakdown = defaultdict(lambda: {'total': 0, 'failed': 0, 'success_rate': 0})
        severity_breakdown = defaultdict(lambda: {'total': 0, 'failed': 0, 'success_rate': 0})
        daily_breakdown = defaultdict(lambda: {'total': 0, 'failed': 0, 'success_rate': 0})

        for result in history:
            # Category breakdown
            category_breakdown[result.category.value]['total'] += 1
            if not result.passed:
                category_breakdown[result.category.value]['failed'] += 1

            # Severity breakdown
            severity_breakdown[result.severity.value]['total'] += 1
            if not result.passed:
                severity_breakdown[result.severity.value]['failed'] += 1

            # Daily breakdown
            day = result.check_time.strftime('%Y-%m-%d')
            daily_breakdown[day]['total'] += 1
            if not result.passed:
                daily_breakdown[day]['failed'] += 1

        # Calculate success rates
        for breakdown in [category_breakdown, severity_breakdown, daily_breakdown]:
            for key, stats in breakdown.items():
                stats['success_rate'] = (stats['total'] - stats['failed']) / stats['total'] if stats['total'] > 0 else 0

        return {
            'report_period': f"{start_date or 'Beginning'} to {end_date or 'Present'}",
            'total_validations': total_validations,
            'failed_validations': failed_validations,
            'overall_success_rate': success_rate,
            'category_breakdown': dict(category_breakdown),
            'severity_breakdown': dict(severity_breakdown),
            'daily_breakdown': dict(daily_breakdown),
            'most_failed_rules': self._get_most_failed_rules(),
            'validation_trend': self._calculate_validation_trend(history)
        }

    def _calculate_validation_trend(self, history: List[ValidationResult]) -> Dict[str, float]:
        """Calculate validation trend over time"""

        if len(history) < 2:
            return {'trend': 0, 'description': 'Insufficient data'}

        # Sort by time
        sorted_history = sorted(history, key=lambda x: x.check_time)

        # Split into first and second half
        mid_point = len(sorted_history) // 2
        first_half = sorted_history[:mid_point]
        second_half = sorted_history[mid_point:]

        # Calculate success rates
        first_half_success = len([r for r in first_half if r.passed]) / len(first_half)
        second_half_success = len([r for r in second_half if r.passed]) / len(second_half)

        trend = second_half_success - first_half_success

        if trend > 0.05:
            description = "Improving"
        elif trend < -0.05:
            description = "Declining"
        else:
            description = "Stable"

        return {
            'trend': trend,
            'description': description,
            'first_half_success_rate': first_half_success,
            'second_half_success_rate': second_half_success
        }

    def start(self) -> None:
        """Start execution validator"""
        logger.info("Execution Validator started")

    def stop(self) -> None:
        """Stop execution validator"""
        logger.info("Execution Validator stopped")