# Limit Monitor API Documentation
**File:** `core_engine/risk/limit_monitor.py`  
**Total Lines:** 669  
**Statements:** 392  
**Current Coverage:** 41%  
**Target Coverage:** 75%+  
**Pre-Read Date:** Phase 6 Day 2

---

## 📋 Overview

**Purpose:** Real-time risk limit monitoring and alerting system with comprehensive limit types.

**Key Responsibilities:**
- Define and manage risk limits across multiple dimensions
- Real-time monitoring of portfolio metrics against limits
- Breach detection and alert generation
- Alert suppression to prevent spam
- Performance metrics tracking
- Comprehensive reporting capabilities

**Architecture Highlights:**
- Thread-safe operations with locking
- Vectorized numpy calculations (6x faster)
- Configurable monitoring intervals
- Deque-based breach storage (10,000 max)
- Alert handler registration pattern
- Automated monitoring loop

---

## 📦 Enums

### `LimitType` (19 values)
Types of risk limits that can be monitored.

```python
class LimitType(Enum):
    POSITION_SIZE = "position_size"              # Individual position size
    SECTOR_EXPOSURE = "sector_exposure"          # Sector concentration
    REGIONAL_EXPOSURE = "regional_exposure"      # Geographic exposure
    CURRENCY_EXPOSURE = "currency_exposure"      # Currency exposure
    TOTAL_LEVERAGE = "total_leverage"            # Portfolio leverage
    NET_EXPOSURE = "net_exposure"                # Net long/short exposure
    GROSS_EXPOSURE = "gross_exposure"            # Total exposure
    VAR_LIMIT = "var_limit"                      # Value at Risk limit
    CONCENTRATION = "concentration"              # Top N position concentration
    CORRELATION = "correlation"                  # Correlation limits
    VOLATILITY = "volatility"                    # Portfolio volatility
    DRAWDOWN = "drawdown"                        # Maximum drawdown
    LIQUIDITY = "liquidity"                      # Liquidity requirements
    CREDIT_RATING = "credit_rating"              # Credit rating constraints
    DURATION = "duration"                        # Duration limits (bonds)
    DELTA = "delta"                              # Options delta
    GAMMA = "gamma"                              # Options gamma
    VEGA = "vega"                                # Options vega
    THETA = "theta"                              # Options theta
```

### `LimitScope` (6 values)
Scope of limit application.

```python
class LimitScope(Enum):
    PORTFOLIO = "portfolio"          # Portfolio-wide limit
    STRATEGY = "strategy"            # Strategy-specific limit
    ACCOUNT = "account"              # Account-level limit
    TRADER = "trader"                # Individual trader limit
    DESK = "desk"                    # Trading desk limit
    LEGAL_ENTITY = "legal_entity"    # Legal entity limit
```

### `LimitOperator` (8 values)
Comparison operators for limit evaluation.

```python
class LimitOperator(Enum):
    LESS_THAN = "lt"                 # current < threshold
    LESS_EQUAL = "le"                # current <= threshold
    GREATER_THAN = "gt"              # current > threshold
    GREATER_EQUAL = "ge"             # current >= threshold
    EQUAL = "eq"                     # current == threshold
    NOT_EQUAL = "ne"                 # current != threshold
    BETWEEN = "between"              # min <= current <= max
    NOT_BETWEEN = "not_between"      # NOT (min <= current <= max)
```

### `AlertSeverity` (4 values)
Alert severity levels.

```python
class AlertSeverity(Enum):
    INFO = "info"                    # Informational
    WARNING = "warning"              # Warning threshold breached
    CRITICAL = "critical"            # Critical threshold breached
    BREACH = "breach"                # Full limit breach
```

---

## 📐 Dataclasses

### `RiskLimit` (16 fields)
Risk limit definition.

```python
@dataclass
class RiskLimit:
    limit_id: str                              # Unique limit identifier
    name: str                                  # Human-readable limit name
    limit_type: LimitType                      # Type of limit (enum)
    scope: LimitScope                          # Scope of application (enum)
    scope_identifier: str                      # Portfolio ID, strategy name, symbol, etc.
    operator: LimitOperator                    # Comparison operator (enum)
    threshold_value: Union[float, List[float]] # Threshold (single or range for BETWEEN)
    warning_threshold: Optional[float] = None  # Optional warning level
    currency: str = "USD"                      # Currency denomination
    is_percentage: bool = False                # Is threshold a percentage
    is_active: bool = True                     # Is limit currently active
    description: str = ""                      # Limit description
    created_by: str = ""                       # Creator identifier
    created_at: datetime = field(...)          # Creation timestamp
    last_updated: datetime = field(...)        # Last update timestamp
    metadata: Dict[str, Any] = field(...)      # Additional metadata
```

### `LimitBreach` (14 fields)
Risk limit breach event.

```python
@dataclass
class LimitBreach:
    limit_id: str                              # Associated limit ID
    limit_name: str                            # Limit name
    current_value: float                       # Current measured value
    threshold_value: Union[float, List[float]] # Threshold that was breached
    breach_amount: float                       # Absolute breach amount
    breach_percentage: float                   # Breach as percentage
    severity: AlertSeverity                    # Breach severity (enum)
    scope: LimitScope                          # Scope of breach
    scope_identifier: str                      # Specific identifier (symbol, strategy, etc.)
    description: str                           # Breach description
    timestamp: datetime = field(...)           # Breach timestamp
    acknowledged: bool = False                 # Has breach been acknowledged
    acknowledged_by: str = ""                  # Who acknowledged
    acknowledged_at: Optional[datetime] = None # When acknowledged
    metadata: Dict[str, Any] = field(...)      # Additional metadata
```

### `MonitoringMetrics` (9 fields)
Monitoring system metrics.

```python
@dataclass
class MonitoringMetrics:
    total_limits: int                          # Total number of limits
    active_limits: int                         # Number of active limits
    current_breaches: int                      # Current breach count
    warning_alerts: int                        # Warning-level alerts
    critical_alerts: int                       # Critical-level alerts
    breach_alerts: int                         # Full breach alerts
    checks_per_second: float                   # Monitoring throughput
    last_check_time: datetime                  # Last check timestamp
    system_health: str                         # "HEALTHY", "WARNING", or "CRITICAL"
```

---

## 🏛️ Main Class: `LimitMonitor`

### Class-Level Attributes
```python
self.config: Dict[str, Any]                    # Configuration dictionary
self._lock: threading.Lock                     # Thread safety lock
self._limits: Dict[str, RiskLimit]             # Registered limits by ID
self._breaches: deque[LimitBreach]             # Breach history (max 10,000)
self._alert_handlers: List[Callable]           # Registered alert handlers
self._monitoring_active: bool                  # Monitoring state flag
self._monitoring_task: Optional[asyncio.Task]  # Background monitoring task

# Configuration
self.check_interval: int                       # Check interval in seconds (default: 30)
self.breach_retention_days: int                # Breach retention days (default: 30)
self.enable_real_time_alerts: bool             # Enable real-time alerts (default: True)

# Metrics
self._check_count: int                         # Total checks performed
self._last_check_time: Optional[datetime]      # Last check timestamp
self._performance_metrics: deque               # Performance history (max 1,000)

# Alert suppression
self._alert_suppression: Dict[str, datetime]   # Suppression tracker
self.alert_suppression_window: int             # Suppression window minutes (default: 5)
```

---

## 🔧 Methods

### Lifecycle Methods

#### `__init__(config: Optional[Dict[str, Any]] = None)`
Initialize limit monitor with configuration.

```python
def __init__(self, config: Optional[Dict[str, Any]] = None):
    """Initialize limit monitor"""
```

**Behavior:**
- Stores config (default: {})
- Creates thread lock for safety
- Initializes empty limits dict
- Creates deque for breaches (maxlen=10,000)
- Initializes empty alert handlers list
- Sets monitoring_active = False
- Extracts config values:
  - check_interval_seconds (default: 30)
  - breach_retention_days (default: 30)
  - enable_real_time_alerts (default: True)
  - alert_suppression_minutes (default: 5)
- Initializes metrics tracking
- Logs initialization

**Testing:**
- [x] Test initialization with default config
- [x] Test initialization with custom config
- [x] Verify all attributes initialized
- [x] Test config extraction

---

### Limit Management Methods

#### `add_limit(limit: RiskLimit) -> None`
Add a new risk limit to monitoring.

```python
def add_limit(self, limit: RiskLimit) -> None:
    """Add a new risk limit"""
```

**Behavior:**
- Acquires lock for thread safety
- Adds limit to _limits dict by limit_id
- Logs addition
- Thread-safe operation

**Testing:**
- [x] Test adding limit
- [x] Test adding multiple limits
- [x] Test thread safety (concurrent adds)
- [x] Verify limit stored correctly

---

#### `update_limit(limit_id: str, updates: Dict[str, Any]) -> None`
Update existing risk limit.

```python
def update_limit(self, limit_id: str, updates: Dict[str, Any]) -> None:
    """Update existing risk limit"""
```

**Behavior:**
- Acquires lock
- Checks if limit_id exists (raises ValueError if not)
- Iterates through updates dict
- Sets attributes if they exist on limit object
- Updates last_updated timestamp
- Logs update
- Thread-safe operation

**Testing:**
- [x] Test successful update
- [x] Test limit not found (ValueError)
- [x] Test updating multiple fields
- [x] Test last_updated timestamp
- [x] Test invalid field (ignored)

---

#### `remove_limit(limit_id: str) -> None`
Remove risk limit from monitoring.

```python
def remove_limit(self, limit_id: str) -> None:
    """Remove risk limit"""
```

**Behavior:**
- Acquires lock
- Checks if limit exists
- Deletes from _limits dict
- Logs removal
- Silently succeeds if limit doesn't exist

**Testing:**
- [x] Test successful removal
- [x] Test removing non-existent limit (no error)
- [x] Verify limit removed from dict

---

#### `get_limit(limit_id: str) -> Optional[RiskLimit]`
Get risk limit by ID.

```python
def get_limit(self, limit_id: str) -> Optional[RiskLimit]:
    """Get risk limit by ID"""
```

**Behavior:**
- Acquires lock
- Returns limit from _limits dict or None

**Testing:**
- [x] Test getting existing limit
- [x] Test getting non-existent limit (returns None)
- [x] Verify correct limit returned

---

#### `get_all_limits(scope: Optional[LimitScope] = None) -> List[RiskLimit]`
Get all risk limits, optionally filtered by scope.

```python
def get_all_limits(self, scope: Optional[LimitScope] = None) -> List[RiskLimit]:
    """Get all risk limits, optionally filtered by scope"""
```

**Behavior:**
- Acquires lock
- Converts _limits dict values to list
- If scope provided: filters list by scope
- Returns filtered list

**Testing:**
- [x] Test getting all limits (no filter)
- [x] Test filtering by scope
- [x] Test with empty limits
- [x] Test with multiple scopes

---

### Core Monitoring Methods

#### `async check_limits(portfolio_data, positions, market_data) -> List[LimitBreach]`
**CRITICAL METHOD** - Check all active limits against current portfolio state.

```python
async def check_limits(
    self,
    portfolio_data: Dict[str, Any],
    positions: Dict[str, Any],
    market_data: Optional[Dict[str, Any]] = None
) -> List[LimitBreach]:
    """Check all active limits against current portfolio state"""
```

**Behavior:**
1. Records start time for performance tracking
2. Gets all active limits (is_active=True) with lock
3. For each active limit:
   - Calls _check_single_limit() async
   - Catches exceptions per limit
   - Collects breaches
4. Stores all breaches via _store_breach()
5. Updates performance metrics:
   - Increments check_count
   - Records timestamp
   - Records check time, limits checked, breaches found
6. If enable_real_time_alerts: calls _send_breach_alerts()
7. Logs check summary (debug level)
8. Returns list of breaches
9. On exception: Logs error and re-raises

**Testing:**
- [x] Test with no active limits
- [x] Test with no breaches
- [x] Test with multiple breaches
- [x] Test performance metrics update
- [x] Test alert sending (if enabled)
- [x] Test exception handling per limit
- [x] Test exception in main flow

---

#### `async _check_single_limit(...) -> Optional[LimitBreach]`
Check individual limit against current data.

```python
async def _check_single_limit(
    self,
    limit: RiskLimit,
    portfolio_data: Dict[str, Any],
    positions: Dict[str, Any],
    market_data: Optional[Dict[str, Any]]
) -> Optional[LimitBreach]:
    """Check individual limit against current data"""
```

**Behavior:**
1. Calls _calculate_limit_value() to get current value
2. Returns None if value is None
3. Calls _evaluate_limit_breach() to check breach
4. If breached:
   - Calculates breach_amount (handles BETWEEN operator)
   - Calculates breach_percentage
   - Creates LimitBreach object
   - Returns breach
5. Returns None if not breached
6. On exception: Logs error, returns None

**Testing:**
- [x] Test no breach
- [x] Test breach detected
- [x] Test BETWEEN operator breach
- [x] Test breach metrics calculation
- [x] Test value calculation None
- [x] Test exception handling

---

### Value Calculation Methods

#### `async _calculate_limit_value(...) -> Optional[float]`
Calculate current value for specific limit type.

```python
async def _calculate_limit_value(
    self,
    limit: RiskLimit,
    portfolio_data: Dict[str, Any],
    positions: Dict[str, Any],
    market_data: Optional[Dict[str, Any]]
) -> Optional[float]:
    """Calculate current value for specific limit type"""
```

**Behavior:**
- Dispatches to appropriate calculation method based on limit_type:
  - TOTAL_LEVERAGE → _calculate_total_leverage()
  - NET_EXPOSURE → _calculate_net_exposure()
  - GROSS_EXPOSURE → _calculate_gross_exposure()
  - POSITION_SIZE → _calculate_position_size()
  - SECTOR_EXPOSURE → _calculate_sector_exposure()
  - VAR_LIMIT → portfolio_data.get('var_1d_99', 0)
  - CONCENTRATION → _calculate_concentration()
  - VOLATILITY → portfolio_data.get('volatility_annual', 0)
  - DRAWDOWN → portfolio_data.get('max_drawdown', 0)
  - Other → Logs warning, returns None

**Testing:**
- [x] Test TOTAL_LEVERAGE calculation
- [x] Test NET_EXPOSURE calculation
- [x] Test GROSS_EXPOSURE calculation
- [x] Test POSITION_SIZE calculation
- [x] Test SECTOR_EXPOSURE calculation
- [x] Test VAR_LIMIT (from portfolio_data)
- [x] Test CONCENTRATION calculation
- [x] Test VOLATILITY (from portfolio_data)
- [x] Test DRAWDOWN (from portfolio_data)
- [x] Test unsupported limit type

---

#### Specific Calculation Methods

**`_calculate_total_leverage(portfolio_data, positions) -> float`**
- Uses numpy vectorization (6x faster)
- Calculates: sum(abs(market_values)) / total_value
- Returns 0 if no positions or total_value=0

**`_calculate_net_exposure(portfolio_data, positions) -> float`**
- Uses numpy vectorization (6x faster)
- Calculates: abs(sum(market_values)) / total_value
- Returns 0 if no positions or total_value=0

**`_calculate_gross_exposure(portfolio_data, positions) -> float`**
- Uses numpy vectorization (6x faster)
- Calculates: sum(abs(market_values)) / total_value
- Returns 0 if no positions or total_value=0

**`_calculate_position_size(symbol, positions) -> float`**
- Returns abs(positions[symbol].market_value) if exists
- Returns 0 if symbol not in positions

**`_calculate_sector_exposure(sector, positions, portfolio_data) -> float`**
- Uses numpy vectorization with filtering
- Filters positions by sector (case-insensitive)
- Calculates: sum(sector_position_values) / total_value
- Returns 0 if no positions or total_value=0

**`_calculate_concentration(identifier, positions, portfolio_data) -> float`**
- Uses numpy vectorization and sorting
- Sorts positions by size (descending)
- Calculates top N concentration (N from identifier, default 10)
- Calculates: sum(top_N_values) / total_value
- Returns 0 if no positions or total_value=0

**Testing for all:**
- [x] Test normal calculation
- [x] Test empty positions
- [x] Test zero total_value
- [x] Test numpy vectorization

---

### Breach Evaluation Methods

#### `_evaluate_limit_breach(limit, current_value) -> Tuple[bool, AlertSeverity]`
Evaluate if limit is breached and determine severity.

```python
def _evaluate_limit_breach(self, limit: RiskLimit, current_value: float) -> Tuple[bool, AlertSeverity]:
    """Evaluate if limit is breached and determine severity"""
```

**Behavior:**
1. Initializes: is_breached=False, severity=INFO
2. If warning_threshold exists:
   - Compares value > warning_threshold
   - If true: is_breached=True, severity=WARNING
3. Compares value against threshold with operator:
   - If breached:
     - is_breached=True
     - severity=CRITICAL (or BREACH if warning already set)
4. Returns (is_breached, severity)

**Testing:**
- [x] Test no breach
- [x] Test warning threshold breach
- [x] Test main threshold breach
- [x] Test both thresholds breached
- [x] Test severity escalation

---

#### `_compare_values(current, threshold, operator) -> bool`
Compare current value against threshold using specified operator.

```python
def _compare_values(self, current: float, threshold: Union[float, List[float]], operator: LimitOperator) -> bool:
    """Compare current value against threshold using specified operator"""
```

**Behavior:**
- LESS_THAN: current < threshold
- LESS_EQUAL: current <= threshold
- GREATER_THAN: current > threshold
- GREATER_EQUAL: current >= threshold
- EQUAL: abs(current - threshold) < 1e-10
- NOT_EQUAL: abs(current - threshold) >= 1e-10
- BETWEEN: threshold[0] <= current <= threshold[1]
- NOT_BETWEEN: NOT (threshold[0] <= current <= threshold[1])
- Returns False for unknown operators

**Testing:**
- [x] Test all 8 operators
- [x] Test EQUAL with epsilon tolerance
- [x] Test BETWEEN with range
- [x] Test edge cases

---

### Breach Storage and Alert Methods

#### `_store_breach(breach: LimitBreach) -> None`
Store breach in memory and clean up old breaches.

```python
def _store_breach(self, breach: LimitBreach) -> None:
    """Store breach in memory and clean up old breaches"""
```

**Behavior:**
- Appends breach to _breaches deque (with lock)
- Calculates cutoff time (now - breach_retention_days)
- Filters _breaches to remove old entries
- Recreates deque with filtered breaches (maxlen=10,000)

**Testing:**
- [x] Test breach storage
- [x] Test old breach cleanup
- [x] Test deque max size
- [x] Test retention period

---

#### `async _send_breach_alerts(breaches: List[LimitBreach]) -> None`
Send alerts for limit breaches with suppression.

```python
async def _send_breach_alerts(self, breaches: List[LimitBreach]) -> None:
    """Send alerts for limit breaches"""
```

**Behavior:**
1. For each breach:
   - Creates suppression_key: "{limit_id}_{severity}"
   - Checks if key in _alert_suppression
   - If suppressed recently (within window): skip
   - For each registered alert handler:
     - Calls handler(breach) async
     - Catches exceptions per handler
   - Updates _alert_suppression[key] = now

**Testing:**
- [x] Test alert sending
- [x] Test multiple handlers
- [x] Test handler exception
- [x] Test alert suppression
- [x] Test suppression window expiry

---

#### `add_alert_handler(handler: Callable) -> None`
Add alert handler function.

```python
def add_alert_handler(self, handler: Callable[[LimitBreach], None]) -> None:
    """Add alert handler function"""
```

**Testing:**
- [x] Test adding handler
- [x] Test multiple handlers
- [x] Verify handler called on alert

---

#### `remove_alert_handler(handler: Callable) -> None`
Remove alert handler function.

```python
def remove_alert_handler(self, handler: Callable[[LimitBreach], None]) -> None:
    """Remove alert handler function"""
```

**Testing:**
- [x] Test removing handler
- [x] Test removing non-existent handler (safe)

---

### Breach Query Methods

#### `get_current_breaches(severity: Optional[AlertSeverity] = None) -> List[LimitBreach]`
Get current limit breaches (last hour).

```python
def get_current_breaches(self, severity: Optional[AlertSeverity] = None) -> List[LimitBreach]:
    """Get current limit breaches"""
```

**Behavior:**
- Gets all breaches with lock
- Filters by severity if provided
- Filters to recent (last hour)
- Returns filtered list

**Testing:**
- [x] Test getting all breaches
- [x] Test filtering by severity
- [x] Test time filtering (last hour)
- [x] Test empty breaches

---

#### `acknowledge_breach(breach_id: str, acknowledged_by: str) -> None`
Acknowledge a limit breach.

```python
def acknowledge_breach(self, breach_id: str, acknowledged_by: str) -> None:
    """Acknowledge a limit breach"""
```

**Behavior:**
- Acquires lock
- Iterates through _breaches
- Finds matching breach (limit_id, not acknowledged, recent)
- Sets: acknowledged=True, acknowledged_by, acknowledged_at=now
- Logs acknowledgment
- Breaks after first match

**Testing:**
- [x] Test acknowledging breach
- [x] Test double acknowledgment (ignored)
- [x] Test non-existent breach (no error)
- [x] Verify fields updated

---

### Metrics and Monitoring Methods

#### `get_monitoring_metrics() -> MonitoringMetrics`
Get monitoring system metrics.

```python
def get_monitoring_metrics(self) -> MonitoringMetrics:
    """Get monitoring system metrics"""
```

**Behavior:**
- Acquires lock
- Counts total_limits and active_limits
- Gets current breach counts by severity
- Calculates checks_per_second from recent performance metrics
- Determines system_health:
  - "CRITICAL" if breach_alerts > 0
  - "WARNING" if critical_alerts > 5
  - "HEALTHY" otherwise
- Returns MonitoringMetrics dataclass

**Testing:**
- [x] Test with no breaches (HEALTHY)
- [x] Test with warnings (HEALTHY)
- [x] Test with critical alerts (WARNING)
- [x] Test with breach alerts (CRITICAL)
- [x] Test checks_per_second calculation
- [x] Test with empty metrics

---

### Automated Monitoring Methods

#### `async start_monitoring(check_function: Callable) -> None`
Start automated monitoring loop.

```python
async def start_monitoring(self, check_function: Callable[[], Dict[str, Any]]) -> None:
    """Start automated monitoring"""
```

**Behavior:**
- Checks if already monitoring (logs warning, returns)
- Sets _monitoring_active = True
- Creates task: _monitoring_loop(check_function)
- Stores task in _monitoring_task
- Logs start

**Testing:**
- [x] Test starting monitoring
- [x] Test double start (warning)
- [x] Verify task created
- [x] Verify monitoring_active flag

---

#### `async stop_monitoring() -> None`
Stop automated monitoring loop.

```python
async def stop_monitoring(self) -> None:
    """Stop automated monitoring"""
```

**Behavior:**
- Sets _monitoring_active = False
- If monitoring_task exists:
  - Cancels task
  - Awaits task (catches CancelledError)
- Logs stop

**Testing:**
- [x] Test stopping monitoring
- [x] Test stop without start (safe)
- [x] Verify task cancelled
- [x] Verify monitoring_active flag

---

#### `async _monitoring_loop(check_function: Callable) -> None`
Main monitoring loop (background task).

```python
async def _monitoring_loop(self, check_function: Callable[[], Dict[str, Any]]) -> None:
    """Main monitoring loop"""
```

**Behavior:**
- While _monitoring_active:
  - Calls check_function() to get data
  - Extracts portfolio_data, positions, market_data
  - Calls check_limits()
  - Sleeps for check_interval seconds
  - Catches CancelledError: breaks
  - Catches other exceptions: logs error, sleeps, continues

**Testing:**
- [x] Test loop execution
- [x] Test cancellation
- [x] Test exception handling
- [x] Test check interval

---

#### `async cleanup() -> None`
Cleanup resources.

```python
async def cleanup(self) -> None:
    """Cleanup resources"""
```

**Behavior:**
- Calls stop_monitoring()
- Logs cleanup completion

**Testing:**
- [x] Test cleanup
- [x] Verify monitoring stopped

---

## 🎯 Test Categories

### Category 1: Enums and Dataclasses (5 tests)
- Test LimitType enum (19 values)
- Test LimitScope enum (6 values)
- Test LimitOperator enum (8 values)
- Test AlertSeverity enum (4 values)
- Test RiskLimit dataclass creation
- Test LimitBreach dataclass creation
- Test MonitoringMetrics dataclass creation

### Category 2: Initialization (3 tests)
- Test default initialization
- Test custom configuration
- Test attribute initialization

### Category 3: Limit Management (6 tests)
- Test add_limit
- Test update_limit
- Test remove_limit
- Test get_limit
- Test get_all_limits (no filter)
- Test get_all_limits (with scope filter)

### Category 4: Value Calculations (9 tests)
- Test total leverage calculation
- Test net exposure calculation
- Test gross exposure calculation
- Test position size calculation
- Test sector exposure calculation
- Test concentration calculation
- Test VAR/volatility/drawdown (from portfolio_data)
- Test empty positions handling
- Test zero total_value handling

### Category 5: Breach Detection (5 tests)
- Test _evaluate_limit_breach (no breach)
- Test _evaluate_limit_breach (warning)
- Test _evaluate_limit_breach (critical)
- Test _compare_values (all operators)
- Test breach calculation logic

### Category 6: Monitoring Core (5 tests)
- Test check_limits (no breaches)
- Test check_limits (with breaches)
- Test _check_single_limit
- Test performance metrics tracking
- Test exception handling in checks

### Category 7: Breach Management (5 tests)
- Test _store_breach
- Test old breach cleanup
- Test get_current_breaches
- Test acknowledge_breach
- Test breach filtering

### Category 8: Alert System (4 tests)
- Test add_alert_handler
- Test remove_alert_handler
- Test _send_breach_alerts
- Test alert suppression

### Category 9: Automated Monitoring (4 tests)
- Test start_monitoring
- Test stop_monitoring
- Test _monitoring_loop
- Test cleanup

### Category 10: Metrics and Reporting (2 tests)
- Test get_monitoring_metrics
- Test system health determination

**Total Estimated Tests:** ~48 tests (Target: 30 for 75%+ coverage)

---

## 🧪 Testing Strategy

### Phase 1: Enums and Basic Structure (8 tests)
- Enums, dataclasses, initialization
- Coverage Target: 20%

### Phase 2: Limit Management (6 tests)
- CRUD operations on limits
- Coverage Target: 35%

### Phase 3: Value Calculations (9 tests)
- All calculation methods
- Coverage Target: 55%

### Phase 4: Breach Detection and Monitoring (10 tests)
- Core monitoring logic
- Coverage Target: 70%

### Phase 5: Alerts and Automation (8 tests)
- Alert system and automated monitoring
- Coverage Target: 80%+ (Stretch)

### Phase 6: Edge Cases (7 tests)
- Error handling, edge cases
- Coverage Target: 75%+ (Maintain)

---

## 🔍 Key Testing Considerations

### Mock Requirements
- **check_function**: Mock for automated monitoring
- **alert_handler**: Mock callable for alert testing
- **portfolio_data, positions, market_data**: Test data dictionaries
- **asyncio.sleep**: Mock for monitoring loop testing
- **datetime.now()**: Consider mocking for time-sensitive tests

### Thread Safety
- Use locks appropriately in tests
- Test concurrent access scenarios
- Verify thread-safe operations

### Async Testing
- All monitoring methods are async
- Use pytest-asyncio
- Test task cancellation

### Numpy Vectorization
- Test with actual numpy arrays
- Verify 6x performance claims (optional)
- Test empty array handling

### Edge Cases
- Empty positions
- Zero total_value
- None values
- Invalid limit types
- Concurrent modifications
- Alert suppression edge cases
- Deque overflow (10,000 limit)

---

## 📊 Expected Coverage Distribution

| Method/Category | Statements | Coverage Target |
|-----------------|-----------|-----------------|
| __init__ | ~30 | 90%+ |
| Limit CRUD | ~45 | 90%+ |
| check_limits | ~35 | 85%+ |
| _check_single_limit | ~30 | 85%+ |
| _calculate_limit_value | ~25 | 90%+ |
| Calculation methods | ~80 | 80%+ |
| _evaluate_limit_breach | ~15 | 90%+ |
| _compare_values | ~20 | 95%+ |
| Breach management | ~30 | 85%+ |
| Alert system | ~35 | 80%+ |
| Automated monitoring | ~40 | 75%+ |
| Metrics | ~20 | 85%+ |

**Total:** ~392 statements → **75%+ coverage target** = ~295 statements covered

---

## ✅ Pre-Read Complete

**File Understanding:** Complete (669/669 lines)
**API Documentation:** Complete (this document)
**Next Step:** Create comprehensive test suite (test_limit_monitor.py)
**Expected Outcome:** 75%+ coverage, 0 API issues, ~30-35 tests
