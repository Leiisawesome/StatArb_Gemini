# execution_validator.py - Complete API Reference

**File**: `core_engine/trading/execution/execution_validator.py`  
**Total Lines**: 1,247  
**Current Coverage**: 48% (245 lines covered, 267 missing per coverage report)  
**Target Coverage**: 65%+  
**Documentation Date**: Phase 5 Week 2 Day 6

---

## 1. ENUMS (3)

### 1.1 ValidationSeverity
```python
class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

**Purpose**: Define validation severity levels for execution checks

**Values**:
- `INFO`: Informational checks, no action needed
- `WARNING`: Warning level, should be monitored
- `ERROR`: Error level, may block execution
- `CRITICAL`: Critical issues, should block execution

---

### 1.2 ValidationCategory
```python
class ValidationCategory(Enum):
    PRE_TRADE = "pre_trade"
    REAL_TIME = "real_time"
    POST_TRADE = "post_trade"
    COMPLIANCE = "compliance"
    RISK = "risk"
    PERFORMANCE = "performance"
```

**Purpose**: Categorize validation checks by execution phase

**Values**:
- `PRE_TRADE`: Before execution submission
- `REAL_TIME`: During active execution
- `POST_TRADE`: After execution completion
- `COMPLIANCE`: Regulatory compliance checks
- `RISK`: Risk management checks
- `PERFORMANCE`: Performance analysis checks

---

### 1.3 ValidationAction
```python
class ValidationAction(Enum):
    LOG_ONLY = "log_only"
    WARN = "warn"
    BLOCK = "block"
    CANCEL = "cancel"
    REDUCE_SIZE = "reduce_size"
    ALERT = "alert"
```

**Purpose**: Define actions to take when validation fails

**Values**:
- `LOG_ONLY`: Just log the failure
- `WARN`: Generate warning
- `BLOCK`: Block execution from proceeding
- `CANCEL`: Cancel execution
- `REDUCE_SIZE`: Reduce order size
- `ALERT`: Send alert notification

---

## 2. DATACLASSES (3)

### 2.1 ValidationRule
```python
@dataclass
class ValidationRule:
    # Rule identification
    rule_id: str
    rule_name: str
    description: str
    
    # Rule classification
    category: ValidationCategory
    severity: ValidationSeverity
    action: ValidationAction
    
    # Rule configuration
    enabled: bool = True
    priority: int = 0
    
    # Thresholds
    numeric_threshold: Optional[float] = None
    percentage_threshold: Optional[float] = None
    time_threshold: Optional[timedelta] = None
    
    # Constraints
    symbols: Optional[List[str]] = None
    strategies: Optional[List[str]] = None
    venues: Optional[List[str]] = None
    
    # Timing rules
    market_hours_only: bool = False
    business_days_only: bool = False
    
    # Custom validator
    custom_validator: Optional[Callable] = None
    
    # Metadata
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
```

**Purpose**: Define validation rule configuration

**Key Fields**:
- **Identification**: rule_id, rule_name, description
- **Classification**: category, severity, action
- **Config**: enabled (default True), priority (default 0)
- **Thresholds**: numeric_threshold, percentage_threshold, time_threshold (all Optional)
- **Constraints**: symbols, strategies, venues (all Optional Lists)
- **Timing**: market_hours_only (default False), business_days_only (default False)
- **Custom**: custom_validator (Optional Callable)
- **Metadata**: created_by, created_at (auto), last_modified (auto)

---

### 2.2 ValidationResult
```python
@dataclass
class ValidationResult:
    # Rule reference
    rule_id: str
    rule_name: str
    category: ValidationCategory
    severity: ValidationSeverity
    action: ValidationAction
    
    # Result
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
```

**Purpose**: Store validation check results

**Key Fields**:
- **Rule Reference**: rule_id, rule_name, category, severity, action
- **Result**: passed (bool), message (str), details (dict, default empty)
- **Context**: execution_id, order_id, symbol (all Optional)
- **Timing**: check_time (auto-generated)
- **Actions**: action_taken (Optional str), action_details (dict, default empty)

---

### 2.3 ExecutionContext
```python
@dataclass
class ExecutionContext:
    # Core execution info
    execution_id: str
    order_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    price: Optional[float] = None
    
    # Order details
    order_type: str = 'MARKET'
    time_in_force: str = 'DAY'
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
    
    # History
    recent_executions: List[Dict[str, Any]] = field(default_factory=list)
```

**Purpose**: Complete execution context for validation

**Key Fields**:
- **Core**: execution_id, order_id, symbol, side ('BUY'/'SELL'), quantity, price (Optional)
- **Order**: order_type (default 'MARKET'), time_in_force (default 'DAY'), venue (Optional)
- **Strategy**: strategy_id, portfolio_id (both Optional)
- **Market**: current_price, bid_price, ask_price, spread, volatility (all Optional)
- **Risk**: current_position (default 0.0), notional_exposure (default 0.0), portfolio_value (Optional)
- **Timing**: submission_time (auto), expected_execution_time (Optional)
- **History**: recent_executions (List of dicts, default empty)

---

## 3. PRE-TRADE VALIDATOR

### 3.1 PreTradeValidator Class
```python
class PreTradeValidator:
    """Pre-trade execution validation"""
    
    def __init__(self):
        self.rules = {}
        self._load_default_pre_trade_rules()
```

**Purpose**: Validate executions before submission

**Attributes**:
- `rules`: Dict[str, ValidationRule] - Validation rules keyed by rule_id

**Default Rules Loaded**:
1. `order_size_limit`: Block if quantity > 1M shares (ERROR, BLOCK)
2. `notional_limit`: Block if notional > $100M (ERROR, BLOCK)
3. `price_reasonableness`: Warn if price > 5% from market (WARNING, WARN)
4. `market_hours`: Warn if outside market hours (WARNING, WARN)
5. `position_concentration`: Reduce if position > 10% of portfolio (ERROR, REDUCE_SIZE)
6. `duplicate_order`: Warn if similar order within 30s (WARNING, WARN)

---

### 3.2 validate_execution()
```python
def validate_execution(self, context: ExecutionContext) -> List[ValidationResult]:
    """Validate execution against pre-trade rules"""
```

**Purpose**: Run all enabled pre-trade validation rules

**Parameters**:
- `context`: ExecutionContext - Execution to validate

**Returns**: `List[ValidationResult]` - Results from all applicable rules

**Process**:
1. Iterate through all rules
2. Skip disabled rules
3. Skip non-PRE_TRADE category rules
4. Check if rule applies (via `_rule_applies()`)
5. Apply rule (via `_apply_rule()`)
6. Collect and return all results

---

### 3.3 _rule_applies()
```python
def _rule_applies(self, rule: ValidationRule, context: ExecutionContext) -> bool:
    """Check if rule applies to execution context"""
```

**Purpose**: Filter rules based on constraints

**Checks**:
- **Symbol filter**: Skip if rule.symbols defined and context.symbol not in list
- **Strategy filter**: Skip if rule.strategies defined and context.strategy_id not in list
- **Venue filter**: Skip if rule.venues defined and context.venue not in list
- **Market hours**: Skip if rule.market_hours_only and not in market hours
- **Business days**: Skip if rule.business_days_only and weekend

**Returns**: `bool` - True if rule should be applied

---

### 3.4 _apply_rule()
```python
def _apply_rule(self, rule: ValidationRule, context: ExecutionContext) -> ValidationResult:
    """Apply validation rule to execution context"""
```

**Purpose**: Execute specific validation rule

**Process**:
1. Create ValidationResult with initial "passed" state
2. Route to specific validator based on rule_id
3. Catch exceptions and mark as failed
4. Return result

**Rule Routing**:
- `order_size_limit` → `_validate_order_size()`
- `notional_limit` → `_validate_notional_limit()`
- `price_reasonableness` → `_validate_price_reasonableness()`
- `market_hours` → `_validate_market_hours()`
- `position_concentration` → `_validate_position_concentration()`
- `duplicate_order` → `_validate_duplicate_order()`
- Custom rules → `rule.custom_validator()`

---

### 3.5 Validation Methods

#### _validate_order_size()
```python
def _validate_order_size(
    self, rule: ValidationRule, context: ExecutionContext, result: ValidationResult
) -> ValidationResult:
```
**Check**: quantity > numeric_threshold  
**Failure**: "Order size {qty} exceeds limit {threshold}"  
**Details**: order_quantity, limit, excess

---

#### _validate_notional_limit()
```python
def _validate_notional_limit(
    self, rule: ValidationRule, context: ExecutionContext, result: ValidationResult
) -> ValidationResult:
```
**Check**: (quantity * price) > numeric_threshold  
**Failure**: "Notional ${notional} exceeds limit ${threshold}"  
**Details**: notional, limit, excess

---

#### _validate_price_reasonableness()
```python
def _validate_price_reasonableness(
    self, rule: ValidationRule, context: ExecutionContext, result: ValidationResult
) -> ValidationResult:
```
**Check**: abs(price - current_price) / current_price > percentage_threshold  
**Failure**: "Order price ${price} deviates {deviation}% from market ${current_price}"  
**Details**: order_price, market_price, deviation, threshold

---

#### _validate_market_hours()
```python
def _validate_market_hours(
    self, rule: ValidationRule, context: ExecutionContext, result: ValidationResult
) -> ValidationResult:
```
**Check**: submission_time outside 9:30 AM - 4:00 PM ET, Mon-Fri  
**Failure**: "Order submitted outside market hours: {time}"  
**Details**: submission_time (ISO), market_hours ("09:30-16:00 ET")

---

#### _validate_position_concentration()
```python
def _validate_position_concentration(
    self, rule: ValidationRule, context: ExecutionContext, result: ValidationResult
) -> ValidationResult:
```
**Check**: abs(new_position_value) / portfolio_value > percentage_threshold  
**Calculation**:
- BUY: new_position = current_position + (quantity * price)
- SELL: new_position = current_position - (quantity * price)
- concentration = abs(new_position) / portfolio_value

**Failure**: "Position concentration {concentration}% exceeds limit {threshold}%"  
**Details**: new_position_value, portfolio_value, concentration, limit

---

#### _validate_duplicate_order()
```python
def _validate_duplicate_order(
    self, rule: ValidationRule, context: ExecutionContext, result: ValidationResult
) -> ValidationResult:
```
**Check**: Recent executions within time_threshold with:
- Same symbol
- Same side
- Similar quantity (within 10%)

**Failure**: "Potential duplicate order detected: similar order submitted {seconds}s ago"  
**Details**: recent_order_time (ISO), time_difference (seconds), threshold_seconds

---

### 3.6 _is_market_hours()
```python
def _is_market_hours(self, timestamp: datetime) -> bool:
    """Check if timestamp is during market hours"""
```

**Market Hours**: 9:30 AM - 4:00 PM ET, Monday-Friday

**Returns**: `bool` - True if within market hours

---

## 4. REAL-TIME VALIDATOR

### 4.1 RealTimeValidator Class
```python
class RealTimeValidator:
    """Real-time execution validation during trading"""
    
    def __init__(self):
        self.rules = {}
        self._load_default_realtime_rules()
```

**Purpose**: Monitor execution performance in real-time

**Default Rules**:
1. `execution_speed`: Alert if execution > 10 seconds (WARNING, ALERT)
2. `slippage_monitor`: Alert if slippage > 1% (WARNING, ALERT)
3. `fill_rate_monitor`: Log if fill rate < 50% (INFO, LOG_ONLY)
4. `market_impact_monitor`: Alert if market impact > 0.5% (WARNING, ALERT)

---

### 4.2 validate_ongoing_execution()
```python
def validate_ongoing_execution(
    self, context: ExecutionContext, execution_metrics: Dict[str, Any]
) -> List[ValidationResult]:
```

**Purpose**: Validate execution during active trading

**Parameters**:
- `context`: ExecutionContext - Execution context
- `execution_metrics`: Dict with keys:
  - `execution_time_seconds`: float
  - `slippage`: float (percentage)
  - `fill_rate`: float (percentage)
  - `market_impact`: float (percentage)

**Returns**: `List[ValidationResult]` - Real-time validation results

---

### 4.3 Real-Time Validation Methods

#### _validate_execution_speed()
**Check**: execution_time_seconds > time_threshold.total_seconds()  
**Failure**: "Slow execution: {time}s exceeds {threshold}s threshold"  
**Details**: execution_time, threshold

#### _validate_slippage()
**Check**: abs(slippage) > percentage_threshold  
**Failure**: "High slippage: {slippage}% exceeds {threshold}% threshold"  
**Details**: slippage, threshold

#### _validate_fill_rate()
**Check**: fill_rate < percentage_threshold  
**Failure**: "Low fill rate: {fill_rate}% below {threshold}% threshold"  
**Details**: fill_rate, threshold

#### _validate_market_impact()
**Check**: abs(market_impact) > percentage_threshold  
**Failure**: "High market impact: {market_impact}% exceeds {threshold}% threshold"  
**Details**: market_impact, threshold

---

## 5. POST-TRADE VALIDATOR

### 5.1 PostTradeValidator Class
```python
class PostTradeValidator:
    """Post-trade execution validation and compliance"""
    
    def __init__(self):
        self.rules = {}
        self._load_default_post_trade_rules()
```

**Purpose**: Analyze completed executions

**Default Rules**:
1. `best_execution`: Analyze execution quality (INFO, LOG_ONLY)
2. `transaction_cost_analysis`: Calculate total costs (INFO, LOG_ONLY)
3. `venue_performance`: Compare venue performance (INFO, LOG_ONLY)
4. `regulatory_reporting`: Check reporting requirements (ERROR, ALERT)

---

### 5.2 validate_completed_execution()
```python
def validate_completed_execution(
    self, context: ExecutionContext, execution_results: Dict[str, Any]
) -> List[ValidationResult]:
```

**Purpose**: Validate and analyze completed execution

**Parameters**:
- `context`: ExecutionContext - Execution context
- `execution_results`: Dict with keys:
  - `avg_execution_price`: float
  - `total_slippage`: float
  - `market_impact`: float
  - `commission`: float
  - `venue_breakdown`: Dict[venue, metrics]

**Returns**: `List[ValidationResult]` - Post-trade analysis results

---

### 5.3 Post-Trade Analysis Methods

#### _analyze_best_execution()
**Calculates**: execution_quality = abs(avg_price - market_price) / market_price  
**Message**: "Best execution analysis: {quality} price deviation"  
**Details**: avg_execution_price, market_price_at_arrival, execution_quality, assessment ("good" if < 0.1%, else "needs_review")

#### _analyze_transaction_costs()
**Calculates**: total_cost_bps = ((slippage + market_impact) * notional + commission) / notional * 10000  
**Message**: "Transaction cost analysis: {cost} bps total cost"  
**Details**: slippage_bps, market_impact_bps, commission, total_cost_bps

#### _analyze_venue_performance()
**Finds**: Best and worst performing venues by avg_slippage  
**Message**: "Venue performance: {count} venues used"  
**Details**: venues_used (list), best_venue, best_venue_slippage, worst_venue, worst_venue_slippage

#### _check_regulatory_reporting()
**Check**: notional > $10M (large trade reporting threshold)  
**Message**: "Large trade reporting required" or "No special reporting required"  
**Details**: notional, requires_reporting (bool), reporting_type (if applicable)

---

## 6. EXECUTION VALIDATOR (Main Class)

### 6.1 ExecutionValidator Class
```python
class ExecutionValidator:
    """
    Advanced Execution Validator
    
    Comprehensive validation system for trade execution with pre-trade,
    real-time, and post-trade validation capabilities.
    """
    
    def __init__(self):
        """Initialize execution validator"""
```

**Attributes**:
- `pre_trade_validator`: PreTradeValidator instance
- `realtime_validator`: RealTimeValidator instance
- `post_trade_validator`: PostTradeValidator instance
- `_validation_history`: List[ValidationResult] - All validation results
- `_failed_validations`: defaultdict(list) - Failed validations by rule_id
- `block_on_critical`: bool (default True) - Block execution on critical failures
- `alert_on_warnings`: bool (default True) - Generate alerts for warnings
- `_validation_callbacks`: List[Callable] - Validation event callbacks
- `_lock`: threading.Lock - Thread safety

---

### 6.2 validate_pre_trade()
```python
def validate_pre_trade(self, context: ExecutionContext) -> Tuple[bool, List[ValidationResult]]:
```

**Purpose**: Perform comprehensive pre-trade validation

**Returns**: `(should_proceed: bool, results: List[ValidationResult])`

**Process**:
1. Call `pre_trade_validator.validate_execution(context)`
2. Identify critical and error failures
3. Determine if should block (if block_on_critical and failures exist)
4. Store results in history
5. Store failed validations
6. Trigger callbacks for each result
7. Return (not should_block, results)

**Thread-Safe**: Uses `self._lock` for history updates

---

### 6.3 validate_real_time()
```python
def validate_real_time(
    self, context: ExecutionContext, execution_metrics: Dict[str, Any]
) -> List[ValidationResult]:
```

**Purpose**: Monitor execution during active trading

**Parameters**:
- `context`: ExecutionContext
- `execution_metrics`: Dict with execution performance metrics

**Returns**: `List[ValidationResult]`

**Process**:
1. Call `realtime_validator.validate_ongoing_execution()`
2. Store results in history (thread-safe)
3. Store failed validations
4. Trigger callbacks
5. Return results

---

### 6.4 validate_post_trade()
```python
def validate_post_trade(
    self, context: ExecutionContext, execution_results: Dict[str, Any]
) -> List[ValidationResult]:
```

**Purpose**: Analyze completed execution

**Parameters**:
- `context`: ExecutionContext
- `execution_results`: Dict with execution outcome data

**Returns**: `List[ValidationResult]`

**Process**:
1. Call `post_trade_validator.validate_completed_execution()`
2. Store results in history (thread-safe)
3. Store failed validations
4. Trigger callbacks
5. Return results

---

### 6.5 Rule Management

#### add_custom_rule()
```python
def add_custom_rule(self, rule: ValidationRule) -> None:
```
**Purpose**: Add custom validation rule  
**Routes to**: Appropriate validator based on rule.category

#### remove_rule()
```python
def remove_rule(self, rule_id: str) -> bool:
```
**Purpose**: Remove validation rule from all validators  
**Returns**: `bool` - True if rule was found and removed

---

### 6.6 Callback Management

#### add_validation_callback()
```python
def add_validation_callback(self, callback: Callable[[ValidationResult], None]) -> None:
```
**Purpose**: Register callback for validation events  
**Signature**: `callback(result: ValidationResult) -> None`

#### _trigger_validation_callbacks()
```python
def _trigger_validation_callbacks(self, result: ValidationResult) -> None:
```
**Purpose**: Execute all registered callbacks  
**Error Handling**: Logs errors, doesn't re-raise

---

### 6.7 Reporting and Analytics

#### get_validation_summary()
```python
def get_validation_summary(self) -> Dict[str, Any]:
```

**Returns**:
```python
{
    'total_validations': int,
    'failed_validations': int,
    'success_rate': float,
    'category_breakdown': {
        category: {'total': int, 'failed': int}
    },
    'severity_breakdown': {
        severity: {'total': int, 'failed': int}
    },
    'most_failed_rules': List[Dict]
}
```

**Thread-Safe**: Uses `self._lock`

---

#### get_validation_history()
```python
def get_validation_history(
    self,
    execution_id: Optional[str] = None,
    rule_id: Optional[str] = None,
    category: Optional[ValidationCategory] = None,
    failed_only: bool = False
) -> List[ValidationResult]:
```

**Purpose**: Get filtered validation history

**Filters**:
- `execution_id`: Filter by execution
- `rule_id`: Filter by rule
- `category`: Filter by category
- `failed_only`: Only failed validations

**Returns**: Sorted by check_time (most recent first)

**Thread-Safe**: Uses `self._lock`

---

#### generate_validation_report()
```python
def generate_validation_report(
    self,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
```

**Purpose**: Generate comprehensive validation report

**Returns**:
```python
{
    'report_period': str,
    'total_validations': int,
    'failed_validations': int,
    'overall_success_rate': float,
    'category_breakdown': {
        category: {'total': int, 'failed': int, 'success_rate': float}
    },
    'severity_breakdown': {
        severity: {'total': int, 'failed': int, 'success_rate': float}
    },
    'daily_breakdown': {
        'YYYY-MM-DD': {'total': int, 'failed': int, 'success_rate': float}
    },
    'most_failed_rules': List[Dict],
    'validation_trend': {
        'trend': float,
        'description': str,  # "Improving", "Declining", "Stable"
        'first_half_success_rate': float,
        'second_half_success_rate': float
    }
}
```

**Date Filtering**: Filters by result.check_time

---

#### _calculate_validation_trend()
```python
def _calculate_validation_trend(self, history: List[ValidationResult]) -> Dict[str, float]:
```

**Purpose**: Calculate validation trend over time

**Method**:
1. Split history into first and second half by time
2. Calculate success rates for each half
3. trend = second_half_success - first_half_success
4. Classify: "Improving" (>0.05), "Declining" (<-0.05), "Stable"

**Returns**: trend, description, first_half_success_rate, second_half_success_rate

---

#### _get_most_failed_rules()
```python
def _get_most_failed_rules(self) -> List[Dict[str, Any]]:
```

**Purpose**: Identify rules with most failures

**Returns**: Top 10 rules by failure count
```python
[
    {
        'rule_id': str,
        'failure_count': int,
        'latest_failure': datetime
    },
    ...
]
```

**Sorted**: By failure_count descending

---

### 6.8 Lifecycle Methods

#### start()
```python
def start(self) -> None:
```
**Purpose**: Start validator (logs info message)

#### stop()
```python
def stop(self) -> None:
```
**Purpose**: Stop validator (logs info message)

---

## 7. TESTING STRATEGY

### 7.1 Test Categories (8)

1. **Enums** (3 tests)
   - ValidationSeverity values
   - ValidationCategory values
   - ValidationAction values

2. **Dataclasses** (3 tests)
   - ValidationRule initialization with defaults
   - ValidationResult with auto-generated fields
   - ExecutionContext comprehensive fields

3. **PreTradeValidator** (8 tests)
   - Order size validation (pass/fail)
   - Notional limit validation
   - Price reasonableness check
   - Market hours validation
   - Position concentration check
   - Duplicate order detection
   - Rule filtering (_rule_applies)
   - Default rule loading

4. **RealTimeValidator** (5 tests)
   - Execution speed monitoring
   - Slippage validation
   - Fill rate monitoring
   - Market impact validation
   - Default rule loading

5. **PostTradeValidator** (5 tests)
   - Best execution analysis
   - Transaction cost calculation
   - Venue performance comparison
   - Regulatory reporting check
   - Default rule loading

6. **ExecutionValidator Core** (6 tests)
   - Initialization
   - Pre-trade validation with blocking
   - Real-time validation
   - Post-trade validation
   - Custom rule management (add/remove)
   - Callback system

7. **History & Reporting** (4 tests)
   - Validation history with filtering
   - Validation summary statistics
   - Report generation with date range
   - Trend calculation

8. **Thread Safety** (1 test)
   - Concurrent validation calls

**Total Estimated Tests**: 35

---

## 8. KEY PATTERNS FOR TESTING

### 8.1 Validation Flow
```python
context = ExecutionContext(...)
validator = ExecutionValidator()

# Pre-trade
should_proceed, results = validator.validate_pre_trade(context)

# Real-time
metrics = {'execution_time_seconds': 5, 'slippage': 0.005, ...}
results = validator.validate_real_time(context, metrics)

# Post-trade
exec_results = {'avg_execution_price': 100.5, ...}
results = validator.validate_post_trade(context, exec_results)
```

### 8.2 Custom Rules
```python
rule = ValidationRule(
    rule_id="custom",
    rule_name="Custom Rule",
    description="Test",
    category=ValidationCategory.PRE_TRADE,
    severity=ValidationSeverity.WARNING,
    action=ValidationAction.WARN,
    numeric_threshold=1000
)
validator.add_custom_rule(rule)
```

### 8.3 Result Checking
```python
result = results[0]
assert result.passed is False
assert result.severity == ValidationSeverity.ERROR
assert 'exceeds' in result.message
assert 'limit' in result.details
```

---

## 9. COVERAGE TARGETS

**Current**: 48% (245 lines covered, 267 missing)  
**Target**: 65%+  
**Gap**: 17 percentage points

**Priority Areas** (likely uncovered):
1. Pre-trade validation methods (6 validators)
2. Real-time validation methods (4 validators)
3. Post-trade analysis methods (4 validators)
4. Rule filtering logic
5. History management
6. Report generation
7. Trend calculation
8. Callback system
9. Thread-safe operations

**Expected Result**: 35 tests targeting these areas should achieve 65%+ coverage

---

## END OF API DOCUMENTATION
