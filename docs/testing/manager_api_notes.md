# Risk Manager API Documentation
**File:** `core_engine/risk/manager.py`  
**Total Lines:** 485  
**Statements:** 227  
**Current Coverage:** 0%  
**Target Coverage:** 70%+  
**Pre-Read Date:** Phase 6 Day 1

---

## 📋 Overview

**Purpose:** Central governance hub for all trading decisions in the Core Engine architecture.

**Role:** Risk Manager sits at the center of the institutional control flow:
1. **StrategyManager (WHAT)** → Submits trade requests
2. **Risk Manager (CONTROL)** → Analyzes and authorizes
3. **TradingEngine (HOW)** → Receives authorization
4. **ExecutionEngine (ACTION)** → Executes with risk token

**Key Responsibilities:**
- Trade authorization (all trades flow through here)
- Risk analysis and limit monitoring
- Position tracking and portfolio metrics
- Real-time risk monitoring
- Component integration (TradingEngine, StrategyManager, ExecutionEngine)

---

## 📦 Enums

### `RiskDecision` (4 values)
Authorization decision types returned from risk analysis.

```python
class RiskDecision(str, Enum):
    APPROVE = "approve"     # Trade approved, proceed with execution
    REJECT = "reject"       # Trade rejected, do not execute
    MODIFY = "modify"       # Trade approved with modifications (quantity adjustment)
    MONITOR = "monitor"     # Trade approved but requires close monitoring
```

**Testing Notes:**
- All 4 values must be valid strings
- Test enum access and comparison
- Verify serialization behavior

---

## 📐 Dataclasses

### `TradeRequest` (9 fields)
Incoming trade request from StrategyManager for risk authorization.

```python
@dataclass
class TradeRequest:
    request_id: str              # Unique request identifier
    symbol: str                  # Trading symbol (e.g., "AAPL")
    strategy: str                # Strategy name (e.g., "momentum", "mean_reversion")
    signal_type: str             # Signal type (e.g., "ENTRY", "EXIT", "SCALE")
    quantity: float              # Requested trade quantity
    confidence: float            # Strategy confidence score (0.0 - 1.0)
    expected_return: float       # Expected return from trade
    risk_score: float            # Pre-calculated risk score (0.0 - 1.0)
    timestamp: datetime          # Request timestamp
```

**Testing Notes:**
- Validate all required fields
- Test quantity bounds (positive values)
- Verify confidence and risk_score ranges (0.0 - 1.0)
- Test timestamp handling
- Validate string field formats (symbol, strategy)

---

### `RiskAuthorizationResult` (8 fields)
Authorization result returned to TradingEngine with risk token.

```python
@dataclass
class RiskAuthorizationResult:
    request_id: str              # Original request ID (correlation)
    decision: RiskDecision       # Authorization decision (enum)
    authorized_quantity: float   # Approved quantity (may differ from request)
    risk_level: RiskLevel        # Assessed risk level
    conditions: List[str]        # Any conditions for execution (e.g., ["Monitor closely"])
    reason: str                  # Explanation for decision
    token: str                   # Authorization token (UUID) for execution validation
    expires_at: datetime         # Token expiration timestamp
```

**Testing Notes:**
- Validate decision enum type
- Test authorized_quantity adjustments (may be < requested)
- Verify token is valid UUID format
- Test expiration logic (expires_at must be future)
- Validate conditions list (can be empty)
- Test all risk levels (LOW, MEDIUM, HIGH)

---

### `RiskManagerConfig` (7 fields)
Configuration parameters for risk manager behavior.

```python
@dataclass
class RiskManagerConfig:
    max_position_size: float = 0.10              # 10% max position size
    max_daily_var: float = 0.05                  # 5% daily Value-at-Risk limit
    max_total_risk: float = 0.20                 # 20% total portfolio risk limit
    position_concentration_limit: float = 0.15   # 15% concentration limit per position
    strategy_allocation_limit: float = 0.33      # 33% allocation limit per strategy
    enable_real_time_monitoring: bool = True     # Enable continuous risk monitoring
    authorization_timeout: int = 300             # Authorization token timeout (seconds)
```

**Testing Notes:**
- Test default values (all have defaults)
- Validate percentage ranges (0.0 - 1.0 for most)
- Test boolean flag behavior
- Verify timeout in seconds (integer)
- Test extreme values (0.0, 1.0, very large numbers)
- Validate configuration immutability after initialization

---

## 🔌 Interfaces

### `IRiskSubscriber`
Interface for components that subscribe to risk events.

```python
class IRiskSubscriber(Protocol):
    async def on_risk_limit_breach(self, risk_event: Dict[str, Any]) -> None:
        """Called when a risk limit is breached"""
        ...
```

**Testing Notes:**
- Test subscriber registration via `subscribe()`
- Verify notification on risk breach
- Test multiple subscribers
- Test subscriber error handling (one failing shouldn't affect others)

---

## 🏛️ Main Class: `RiskManager`

### Class-Level Attributes
```python
self.config: RiskManagerConfig                    # Configuration parameters
self.unified_risk_manager: Optional[Any]          # Optional sophisticated risk calculator
self.trading_engine: Optional[Any]                # Linked TradingEngine (HOW)
self.strategy_manager: Optional[Any]              # Linked StrategyManager (WHAT)
self.execution_engine: Optional[Any]              # Linked ExecutionEngine (ACTION)
self.subscribers: List[IRiskSubscriber]           # Risk event subscribers
self.active_positions: Dict[str, Position]        # Current positions by symbol
self.pending_authorizations: Dict[str, RiskAuthorizationResult]  # Active auth tokens
self.risk_metrics: Optional[RiskMetrics]          # Portfolio risk metrics
self.daily_pnl: float = 0.0                       # Current daily P&L
self.portfolio_value: float = 0.0                 # Total portfolio value
self.position_limits: Dict[str, float] = {}       # Per-symbol position limits
self.is_initialized: bool = False                 # Initialization flag
self.is_running: bool = False                     # Running state flag
self.monitoring_task: Optional[asyncio.Task] = None  # Background monitoring task
```

---

## 🔧 Methods

### Lifecycle Methods

#### `__init__(config: RiskManagerConfig, unified_risk_manager: Optional[Any] = None)`
Initialize risk manager with configuration.

```python
def __init__(self, config: RiskManagerConfig, unified_risk_manager: Optional[Any] = None):
    """Initialize Risk Manager with configuration"""
```

**Behavior:**
- Stores config and optional unified_risk_manager
- Initializes all component references to None
- Creates empty collections (positions, authorizations, subscribers)
- Sets initial state flags (is_initialized=False, is_running=False)

**Testing:**
- [x] Test initialization with default config
- [x] Test initialization with custom config
- [x] Test with and without unified_risk_manager
- [x] Verify all attributes initialized correctly
- [x] Test config immutability

---

#### `async initialize() -> bool`
Perform async initialization of risk manager.

```python
async def initialize(self) -> bool:
    """Initialize core risk management"""
```

**Behavior:**
- Logs initialization start
- Sets `is_initialized = True`
- Logs success
- Returns `True` on success

**Testing:**
- [x] Test successful initialization
- [x] Verify is_initialized flag set to True
- [x] Test double initialization (should be idempotent)
- [x] Test initialization before any component linking

---

#### `async start() -> bool`
Start risk manager and begin real-time monitoring.

```python
async def start(self) -> bool:
    """Start the Risk Manager"""
```

**Behavior:**
- Checks `is_initialized` is True (raises if False)
- Logs start message
- If `config.enable_real_time_monitoring` is True:
  - Creates background task for `_run_risk_monitoring()`
  - Stores task reference in `monitoring_task`
- Sets `is_running = True`
- Returns `True` on success
- Raises exception on failure

**Testing:**
- [x] Test successful start after initialization
- [x] Verify monitoring task created when enabled
- [x] Test start without initialization (should raise)
- [x] Test with monitoring disabled
- [x] Verify is_running flag set to True
- [x] Test double start (idempotence)

---

#### `async stop() -> bool`
Stop risk manager and cancel monitoring.

```python
async def stop(self) -> bool:
    """Stop risk monitoring"""
```

**Behavior:**
- Logs stop message
- If `monitoring_task` exists:
  - Cancels the task
  - Waits for `asyncio.CancelledError`
  - Sets `monitoring_task = None`
- Sets `is_running = False`
- Returns `True` on success
- Returns `False` on exception (logs error)

**Testing:**
- [x] Test successful stop after start
- [x] Verify monitoring task cancelled
- [x] Test stop without start (should be safe)
- [x] Verify is_running flag set to False
- [x] Test stop with no monitoring task

---

### Component Integration Methods

#### `set_trading_engine(trading_engine: Any)`
Link TradingEngine to risk manager.

```python
def set_trading_engine(self, trading_engine: Any):
    """Set trading engine (HOW component)"""
```

**Behavior:**
- Stores reference to trading_engine
- Logs linkage message

**Testing:**
- [x] Test setting trading engine
- [x] Verify reference stored correctly
- [x] Test replacing existing engine
- [x] Test setting to None

---

#### `set_strategy_manager(strategy_manager: Any)`
Link StrategyManager to risk manager.

```python
def set_strategy_manager(self, strategy_manager: Any):
    """Set strategy manager (WHAT component)"""
```

**Behavior:**
- Stores reference to strategy_manager
- Logs linkage message

**Testing:**
- [x] Test setting strategy manager
- [x] Verify reference stored correctly
- [x] Test replacing existing manager
- [x] Test setting to None

---

#### `set_execution_engine(execution_engine: Any)`
Link ExecutionEngine to risk manager.

```python
def set_execution_engine(self, execution_engine: Any):
    """Set execution engine (ACTION component)"""
```

**Behavior:**
- Stores reference to execution_engine
- Logs linkage message

**Testing:**
- [x] Test setting execution engine
- [x] Verify reference stored correctly
- [x] Test replacing existing engine
- [x] Test setting to None

---

#### `subscribe(subscriber: IRiskSubscriber)`
Register risk event subscriber.

```python
def subscribe(self, subscriber: IRiskSubscriber):
    """Subscribe to risk events"""
```

**Behavior:**
- Appends subscriber to subscribers list
- Logs registration

**Testing:**
- [x] Test adding subscriber
- [x] Test multiple subscribers
- [x] Verify subscriber receives events
- [x] Test duplicate subscriber

---

### Core Authorization Methods

#### `async authorize_trade(trade_request: TradeRequest) -> RiskAuthorizationResult`
**CRITICAL METHOD** - All trades must flow through this authorization.

```python
async def authorize_trade(self, trade_request: TradeRequest) -> RiskAuthorizationResult:
    """
    Central trade authorization - all trades must flow through here
    """
```

**Behavior:**
1. Logs authorization request
2. Generates UUID for authorization token
3. Calls `_analyze_trade_risk(trade_request)` for risk analysis
4. Calls `_make_authorization_decision(trade_request, risk_analysis)` for decision
5. Creates `RiskAuthorizationResult`:
   - Uses decision from step 4
   - Sets authorized_quantity (may differ from request)
   - Includes risk_level from analysis
   - Adds any conditions
   - Sets token and expiration (now + authorization_timeout)
6. Stores result in `pending_authorizations[token]`
7. Logs APPROVE (✅) or REJECT (⛔) decision
8. Returns authorization result
9. On exception: Returns REJECT result with error reason

**Testing:**
- [x] Test successful trade approval
- [x] Test trade rejection (high risk)
- [x] Test quantity modification (MODIFY decision)
- [x] Test authorization token generation (UUID format)
- [x] Test expiration timestamp calculation
- [x] Test authorization storage in pending_authorizations
- [x] Test with unified_risk_manager present
- [x] Test with unified_risk_manager absent (fallback)
- [x] Test exception handling (returns REJECT)
- [x] Test position limit checks
- [x] Test concentration limit checks

---

#### `async validate_execution(auth_token: str, execution_details: Dict[str, Any]) -> bool`
Validate execution against issued authorization.

```python
async def validate_execution(self, auth_token: str, execution_details: Dict[str, Any]) -> bool:
    """Validate execution against authorization"""
```

**Behavior:**
1. Checks if auth_token exists in pending_authorizations
   - Returns False if not found (logs warning)
2. Retrieves authorization result
3. Checks if authorization expired (datetime.now() > expires_at)
   - Removes expired auth and returns False
4. Validates execution details:
   - Checks execution quantity ≤ authorized_quantity
   - Returns False if exceeded
5. Removes used authorization from pending_authorizations
6. Logs successful validation
7. Returns True on success
8. On exception: Logs error and returns False

**Testing:**
- [x] Test valid execution within limits
- [x] Test invalid token (not in pending)
- [x] Test expired authorization
- [x] Test quantity exceeding authorized amount
- [x] Test authorization removal after use (single-use)
- [x] Test exception handling
- [x] Test with empty execution_details
- [x] Test with missing quantity in execution_details

---

#### `async update_position(symbol: str, position_update: Dict[str, Any])`
Update position information from execution.

```python
async def update_position(self, symbol: str, position_update: Dict[str, Any]):
    """Update position information from execution"""
```

**Behavior:**
1. If symbol exists in active_positions:
   - Updates existing position:
     - quantity += quantity_change (from update dict)
     - Updates market_value, unrealized_pnl
     - Sets last_update = now
2. If symbol doesn't exist:
   - Creates new Position object with:
     - symbol, quantity, entry_price, current_price
     - market_value, unrealized_pnl
     - entry_time = now, last_update = now
   - Adds to active_positions
3. Calls `_update_risk_metrics()` to recalculate portfolio
4. Logs position update
5. On exception: Logs error

**Testing:**
- [x] Test updating existing position
- [x] Test creating new position
- [x] Test quantity accumulation (multiple updates)
- [x] Test position closure (quantity = 0)
- [x] Test market_value updates
- [x] Test unrealized_pnl tracking
- [x] Test timestamp updates
- [x] Verify _update_risk_metrics() called
- [x] Test exception handling

---

### Internal Risk Analysis Methods

#### `async _analyze_trade_risk(trade_request: TradeRequest) -> Any`
Perform comprehensive trade risk analysis.

```python
async def _analyze_trade_risk(self, trade_request: TradeRequest) -> Any:
    """Perform comprehensive trade risk analysis"""
```

**Behavior:**
1. If unified_risk_manager exists:
   - Delegates to unified_risk_manager.analyze_trade_risk()
   - Passes symbol, quantity, strategy, confidence
2. If unified_risk_manager is None:
   - Returns fallback basic analysis:
     - risk_level = MEDIUM
     - position_impact = 0.05
     - portfolio_impact = 0.02
     - concentration_risk = 0.03

**Testing:**
- [x] Test with unified_risk_manager (mock delegation)
- [x] Test fallback analysis (no unified_risk_manager)
- [x] Verify fallback values (MEDIUM risk, specific impacts)
- [x] Test integration with authorize_trade

---

#### `async _make_authorization_decision(trade_request: TradeRequest, risk_analysis: Any) -> Any`
Make final authorization decision based on risk analysis.

```python
async def _make_authorization_decision(self, trade_request: TradeRequest, risk_analysis: Any) -> Any:
    """Make final authorization decision"""
```

**Behavior:**
1. **Position Limit Check:**
   - Gets current position for symbol
   - Calculates position_size = abs(quantity * current_price)
   - If position_size > max_position_size * portfolio_value:
     - Returns REJECT decision with reason "Position size limit exceeded"

2. **Risk Level Check:**
   - If risk_level == HIGH:
     - Returns REJECT decision with reason "High risk level"

3. **Approval with Adjustment:**
   - Sets authorized_quantity = requested quantity
   - If risk_level == MEDIUM:
     - Reduces authorized_quantity by 50% (quantity * 0.5)
     - Adds condition "Monitor closely"
   - Returns APPROVE decision with authorized_quantity

**Testing:**
- [x] Test position limit rejection
- [x] Test high risk rejection
- [x] Test approval with full quantity (low risk)
- [x] Test quantity reduction (medium risk)
- [x] Test conditions added for medium risk
- [x] Test with no existing position
- [x] Test boundary cases (exactly at limit)

---

### Monitoring Methods

#### `async _run_risk_monitoring()`
Continuous background risk monitoring loop.

```python
async def _run_risk_monitoring(self):
    """Run continuous risk monitoring"""
```

**Behavior:**
- Logs monitoring start
- Runs infinite loop while `is_running` is True:
  - Calls `_update_risk_metrics()`
  - Calls `_check_risk_limits()`
  - Sleeps for 60 seconds
  - Catches `asyncio.CancelledError` to break loop
  - Catches other exceptions: Logs error, sleeps 30 seconds, continues

**Testing:**
- [x] Test monitoring task creation
- [x] Test monitoring loop execution
- [x] Test cancellation (asyncio.CancelledError)
- [x] Test exception handling (continues after error)
- [x] Verify 60-second interval
- [x] Test integration with start/stop

---

#### `async _update_risk_metrics()`
Update portfolio risk metrics using vectorized calculations.

```python
async def _update_risk_metrics(self):
    """Update portfolio risk metrics"""
```

**Behavior:**
1. If active_positions exist:
   - Uses numpy for vectorized calculation (6x faster):
     - Extracts market_values array from all positions
     - Extracts unrealized_pnls array from all positions
     - Calculates total_value = market_values.sum()
     - Calculates total_pnl = unrealized_pnls.sum()
2. If no active_positions:
   - Sets total_value = 0, total_pnl = 0
3. Updates self.portfolio_value and self.daily_pnl
4. If unified_risk_manager exists:
   - Calls unified_risk_manager.calculate_portfolio_risk(positions)
   - Updates self.risk_metrics
5. On exception: Logs error

**Testing:**
- [x] Test with multiple positions (numpy calculation)
- [x] Test with no positions (zero values)
- [x] Test with single position
- [x] Test portfolio_value calculation
- [x] Test daily_pnl calculation
- [x] Test with unified_risk_manager
- [x] Test without unified_risk_manager
- [x] Test exception handling

---

#### `async _check_risk_limits()`
Check for risk limit breaches.

```python
async def _check_risk_limits(self):
    """Check for risk limit breaches"""
```

**Behavior:**
1. **Daily VaR Check:**
   - If abs(daily_pnl) > max_daily_var * portfolio_value:
     - Calls `_handle_risk_breach()` with event:
       - type: 'daily_var_breach'
       - current_pnl, limit, severity: 'high'

2. **Position Concentration Check:**
   - For each position in active_positions:
     - Calculates position_pct = market_value / portfolio_value
     - If position_pct > position_concentration_limit:
       - Calls `_handle_risk_breach()` with event:
         - type: 'concentration_breach'
         - symbol, concentration, limit, severity: 'medium'

3. On exception: Logs error

**Testing:**
- [x] Test daily VaR breach detection
- [x] Test concentration breach detection
- [x] Test with no breaches (normal operation)
- [x] Test multiple simultaneous breaches
- [x] Test boundary cases (exactly at limit)
- [x] Test exception handling

---

#### `async _handle_risk_breach(risk_event: Dict[str, Any])`
Handle risk limit breach by notifying subscribers.

```python
async def _handle_risk_breach(self, risk_event: Dict[str, Any]):
    """Handle risk limit breach"""
```

**Behavior:**
1. Logs warning with risk_event details
2. For each subscriber in subscribers list:
   - Calls subscriber.on_risk_limit_breach(risk_event)
   - Catches exceptions: Logs error (doesn't stop other notifications)

**Testing:**
- [x] Test subscriber notification
- [x] Test multiple subscribers
- [x] Test subscriber exception handling (continues)
- [x] Test with no subscribers
- [x] Test event data passed correctly

---

### Status Methods

#### `get_risk_status() -> Dict[str, Any]`
Get comprehensive risk status snapshot.

```python
def get_risk_status(self) -> Dict[str, Any]:
    """Get comprehensive risk status"""
```

**Behavior:**
Returns dictionary with:
- `initialized`: bool (is_initialized flag)
- `running`: bool (is_running flag)
- `portfolio_value`: float (current portfolio value)
- `daily_pnl`: float (current daily P&L)
- `active_positions`: int (count of active positions)
- `pending_authorizations`: int (count of pending authorizations)
- `daily_var_utilization`: float (abs(daily_pnl) / (max_daily_var * portfolio_value))
- `max_position_concentration`: float (max position as % of portfolio)
- `components_linked`: dict with:
  - `trading_engine`: bool (not None)
  - `strategy_manager`: bool (not None)
  - `execution_engine`: bool (not None)

**Testing:**
- [x] Test with initialized manager
- [x] Test with running manager
- [x] Test with linked components
- [x] Test with positions
- [x] Test with pending authorizations
- [x] Test VaR utilization calculation
- [x] Test max concentration calculation
- [x] Test empty state (no positions)

---

## 🎯 Test Categories

### Category 1: Enums and Dataclasses (5 tests)
- Test RiskDecision enum values
- Test TradeRequest creation and validation
- Test RiskAuthorizationResult creation
- Test RiskManagerConfig defaults
- Test IRiskSubscriber interface

### Category 2: Initialization and Configuration (4 tests)
- Test __init__ with various configs
- Test async initialize()
- Test start() with monitoring enabled/disabled
- Test stop() lifecycle

### Category 3: Component Integration (4 tests)
- Test set_trading_engine()
- Test set_strategy_manager()
- Test set_execution_engine()
- Test subscribe() and notifications

### Category 4: Trade Authorization (6 tests)
- Test authorize_trade() approval (low risk)
- Test authorize_trade() rejection (high risk)
- Test authorize_trade() quantity modification (medium risk)
- Test position limit enforcement
- Test with/without unified_risk_manager
- Test exception handling

### Category 5: Execution Validation (4 tests)
- Test validate_execution() success
- Test invalid token
- Test expired authorization
- Test quantity exceeding limit

### Category 6: Position Management (4 tests)
- Test update_position() for new position
- Test update_position() for existing position
- Test position closure
- Test risk metrics update trigger

### Category 7: Risk Monitoring (4 tests)
- Test _run_risk_monitoring() loop
- Test _update_risk_metrics() calculations
- Test _check_risk_limits() breach detection
- Test _handle_risk_breach() notifications

### Category 8: Status and Integration (3 tests)
- Test get_risk_status() output
- Test full lifecycle (init → start → authorize → stop)
- Test error recovery scenarios

**Total Estimated Tests:** ~34 tests (Target: 25-28 for 70%+ coverage)

---

## 🧪 Testing Strategy

### Phase 1: Basic Structure (5 tests)
Focus on enums, dataclasses, and basic initialization.
- Coverage Target: 20-25%

### Phase 2: Core Authorization (8 tests)
Test trade authorization and validation flows.
- Coverage Target: 45-50%

### Phase 3: Position and Risk (8 tests)
Test position management and risk calculations.
- Coverage Target: 65-70%

### Phase 4: Monitoring and Integration (8 tests)
Test background monitoring and full lifecycle.
- Coverage Target: 75-80% (Stretch goal)

### Phase 5: Edge Cases and Error Handling (5 tests)
Test exception handling, boundary conditions, error recovery.
- Coverage Target: 70%+ (Maintain quality)

---

## 🔍 Key Testing Considerations

### Mock Requirements
- **unified_risk_manager**: Mock for risk analysis delegation
- **TradingEngine, StrategyManager, ExecutionEngine**: Component references
- **IRiskSubscriber**: Mock subscriber for event notifications
- **asyncio.sleep**: Mock for monitoring loop testing
- **datetime.now()**: Consider mocking for expiration tests

### Async Testing
- All major methods are async (use pytest-asyncio)
- Test asyncio task management (monitoring_task)
- Test task cancellation (CancelledError)
- Test async lifecycle (initialize → start → stop)

### State Management
- Test initialization flags (is_initialized, is_running)
- Test state transitions (not initialized → initialized → running → stopped)
- Test pending_authorizations lifecycle (add → validate → remove)
- Test active_positions updates

### Edge Cases
- Empty positions (portfolio_value = 0)
- Zero quantity trades
- Expired authorizations
- Invalid tokens
- Position at exact limit
- Missing optional components

### Performance Considerations
- Numpy vectorization (6x faster)
- Background monitoring (60-second intervals)
- Authorization timeout (300 seconds default)
- Efficient position lookup (dict-based)

---

## 📊 Expected Coverage Distribution

| Method/Category | Statements | Coverage Target |
|-----------------|-----------|-----------------|
| __init__ | ~20 | 90%+ |
| Lifecycle (initialize, start, stop) | ~30 | 85%+ |
| Component integration | ~15 | 90%+ |
| authorize_trade | ~40 | 80%+ |
| validate_execution | ~25 | 85%+ |
| update_position | ~25 | 75%+ |
| _analyze_trade_risk | ~12 | 90%+ |
| _make_authorization_decision | ~25 | 80%+ |
| _run_risk_monitoring | ~15 | 70%+ |
| _update_risk_metrics | ~20 | 75%+ |
| _check_risk_limits | ~20 | 75%+ |
| _handle_risk_breach | ~10 | 80%+ |
| get_risk_status | ~15 | 90%+ |

**Total:** ~227 statements → **70%+ coverage target** = ~160 statements covered

---

## ✅ Pre-Read Complete

**File Understanding:** Complete (485/485 lines)
**API Documentation:** Complete (this document)
**Next Step:** Create comprehensive test suite (test_manager.py)
**Expected Outcome:** 70%+ coverage, 0 API issues, 25-28 tests

This comprehensive API documentation provides complete reference for test creation with zero ambiguity.
