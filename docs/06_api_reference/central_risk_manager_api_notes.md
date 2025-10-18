# Central Risk Manager API Documentation
## Phase 7 Week 1 Day 1 - System Module Testing

**File**: `core_engine/system/central_risk_manager.py`  
**Lines**: 2047  
**Purpose**: Central governance hub for ALL trading decisions in the system

---

## 📋 Overview

The `CentralRiskManager` is the **architectural centerpiece** of the TradeDesk system. It implements the central governance pattern where:

- **WHAT (StrategyManager)**: Determines trading strategies → submits to RiskManager
- **HOW (TradingEngine)**: Plans execution methodology → under RiskManager control  
- **ACTION (UnifiedExecutionEngine)**: Executes trades → requires RiskManager authorization
- **MONITORING**: Continuous risk monitoring and dynamic limit adjustment

**Key Principle**: No component can execute trades independently - all flow through CentralRiskManager authorization.

---

## 🏗️ Class Structure

### Main Classes

#### 1. `TradingDecisionType` (Enum)
Types of trading decisions requiring authorization:
- `STRATEGY_ACTIVATION`
- `STRATEGY_DEACTIVATION` 
- `POSITION_ENTRY`
- `POSITION_EXIT`
- `POSITION_ADJUSTMENT`
- `PORTFOLIO_REBALANCING`
- `EMERGENCY_LIQUIDATION`
- `RISK_LIMIT_ADJUSTMENT`

#### 2. `AuthorizationLevel` (Enum)
Authorization levels for decisions:
- `AUTOMATIC` - Auto-approved within normal parameters
- `STANDARD` - Normal review process
- `ELEVATED` - Requires elevated review
- `EMERGENCY` - Emergency authorization
- `REJECTED` - Authorization denied

#### 3. `TradingDecisionRequest` (@dataclass)
Request for trading decision authorization

**Key Fields**:
```python
request_id: str  # Auto-generated UUID
decision_type: TradingDecisionType
strategy_id: str
symbol: str
side: str  # buy/sell/hold
quantity: float
expected_return: float
confidence: float  # Signal confidence (0-1)

# Risk context
current_position: float
portfolio_impact: float
risk_score: float

# Market context
market_regime: str
regime_confidence: float
volatility_estimate: float

# Timing
urgency: ExecutionUrgency
max_execution_time: int  # seconds

# Metadata
created_at: datetime
requesting_component: str
justification: str
metadata: Dict[str, Any]
```

**Important Metadata Fields**:
- `available_cash`: Required for BUY orders (cash availability check)
- `price`: Required for quantity calculations
- `volatility_estimate`: Used for volatility-based scaling

#### 4. `TradingAuthorization` (@dataclass)
Authorization result for trading decisions

**Key Fields**:
```python
authorization_id: str  # Auto-generated UUID
request_id: str  # Links to original request

# Authorization result
authorization_level: AuthorizationLevel
authorized_quantity: float  # May be less than requested
max_quantity: float

# Risk constraints
position_limit: float
risk_budget_allocation: float
max_market_impact: float

# Execution constraints
allowed_algorithms: List[ExecutionAlgorithm]
max_execution_time: int
venue_restrictions: List[str]

# Authorization metadata
risk_manager_id: str = "central_risk_manager"
authorized_at: datetime
expires_at: datetime  # 1 hour default

# Conditions and restrictions
conditions: List[str]
restrictions: List[str]
monitoring_requirements: List[str]

# Validation
is_valid: bool
rejection_reason: str
```

#### 5. `RiskManagerConfig` (@dataclass)
Configuration for the central risk manager

**Key Settings**:
```python
# Risk limits
max_position_size: float = 0.10  # 10% max position
max_daily_var: float = 0.05  # 5% daily VaR
max_total_risk: float = 0.20  # 20% total portfolio risk
position_concentration_limit: float = 0.15  # 15% per position
strategy_allocation_limit: float = 0.33  # 33% per strategy

# Signal confidence requirements
min_signal_confidence: float = 0.6  # Minimum for authorization
high_confidence_threshold: float = 0.8  # High confidence
extreme_confidence_threshold: float = 0.9  # Extreme confidence

# Authorization thresholds
auto_approval_threshold: float = 0.01  # 1% auto-approve
elevated_review_threshold: float = 0.05  # 5% elevated review
emergency_threshold: float = 0.10  # 10% emergency

# Execution settings
default_execution_algorithm: ExecutionAlgorithm = ADAPTIVE
max_execution_time: int = 3600  # 1 hour

# Monitoring
real_time_monitoring: bool = True
monitoring_frequency: int = 1  # seconds

# Regime integration
regime_risk_multipliers: Dict[str, float] = {
    'bull_market': 0.8,
    'bear_market': 1.3,
    'high_volatility': 1.5,
    'low_volatility': 0.7,
    'crisis': 2.0,
    'sideways': 1.0
}
```

---

## 🔧 Core Methods

### Initialization & Lifecycle

#### `__init__(config: Optional[Dict[str, Any]] = None)`
Initialize central risk manager

**Initializes**:
- Configuration from `RiskManagerConfig`
- Authorization tracking dictionaries
- Position and strategy allocation tracking
- Risk metrics and limits
- Threading locks for concurrent access

**Important State Variables**:
- `pending_requests`: Active authorization requests
- `active_authorizations`: Valid authorizations
- `authorization_history`: Historical record
- `current_positions`: Real-time position tracking
- `strategy_allocations`: Strategy capital allocation
- `risk_limits`: Dynamic risk limits
- `authorization_audit`: Audit trail
- `escalation_audit`: Escalation history

#### `async initialize(execution_config: Optional[Dict[str, Any]] = None) -> bool`
Initialize the central risk manager and all controlled components

**Actions**:
1. Initializes `UnifiedExecutionEngine` under RiskManager control
2. Starts continuous monitoring if enabled
3. Sets operational flags

**Returns**: `True` on success, `False` on failure

#### `set_controlled_components(strategy_manager, trading_engine, regime_engine)`
Set components under RiskManager control

**Purpose**: Register the WHAT/HOW/ACTION components with the governance hub

---

### Core Authorization Flow

#### `async authorize_trading_decision(request: TradingDecisionRequest) -> TradingAuthorization`
**THE CENTRAL METHOD** - All trading decisions flow through here

**Flow**:
1. Check emergency mode (reject if active)
2. Store pending request
3. Perform comprehensive risk assessment (`_assess_trading_request`)
4. Store authorization if approved
5. Add to history
6. Return authorization result

**Thread-Safe**: Uses `authorization_lock`

**Returns**: `TradingAuthorization` with decision

**Risk Assessment Includes**:
- Risk impact calculation
- Position limit check
- Concentration check
- Strategy limit check
- Regime adjustment
- Signal confidence validation (NEW: from test findings)

#### `async _assess_trading_request(request: TradingDecisionRequest) -> TradingAuthorization`
**PRIVATE** - Comprehensive risk assessment

**Checks Performed**:
1. **Risk Impact**: `_calculate_risk_impact(request)`
2. **Position Limits**: `_check_position_limits(request)`
3. **Concentration**: `_check_concentration_limits(request)`
4. **Strategy Allocation**: `_check_strategy_limits(request)`
5. **Regime Adjustment**: `_get_regime_risk_adjustment(request)`

**Determines**:
- Authorization level
- Authorized quantity (may reduce requested)
- Risk constraints
- Execution constraints
- Monitoring requirements

---

### Authorized Quantity Calculation (CRITICAL)

#### `_calculate_authorized_quantity(request, risk_impact, regime_adjustment) -> float`
**ARCHITECTURAL FIX** - Enhanced with cash and position validation

**Critical Features**:

1. **Cash Availability Check (BUY Orders)**:
   ```python
   available_cash = request.metadata.get('available_cash', portfolio_value * 0.95)
   price = request.metadata.get('price', 100.0)
   required_cash = authorized_qty * price
   
   if required_cash > available_cash:
       max_affordable_qty = available_cash / price
       authorized_qty = max_affordable_qty  # Cap by cash
   ```

2. **Position-Aware SELL Orders**:
   ```python
   current_position = self.current_positions.get(symbol, 0.0)
   
   if current_position <= 0:
       return 0.0  # No position to sell
   else:
       max_sellable = abs(current_position)
       if authorized_qty > max_sellable:
           authorized_qty = max_sellable  # Cap by position
   ```

3. **Risk-Based Adjustment**:
   - Reduces quantity for high risk (>auto_approval_threshold)
   - Reduction factor: `min(0.5, (risk_impact - threshold) * 2)`

4. **Regime-Based Scaling**:
   - **High Volatility** (>0.30): Up to 60% reduction
   - **Low Volatility** (<0.10): 10% increase
   - **High Risk Regime**: 20% reduction
   - **Low Risk Regime**: 10% increase

5. **Final Constraints**:
   - Re-check cash for BUY orders
   - Re-check position for SELL orders
   - Round to 2 decimal places

**Returns**: Authorized quantity (0.0 if constraints violated)

---

### Execution Integration

#### `async execute_authorized_trade(authorization, execution_params) -> ExecutionResult`
Execute trade using UnifiedExecutionEngine with RiskManager authorization

**Flow**:
1. Validate authorization
2. Create `ExecutionAuthorization` for UnifiedExecutionEngine
3. Create `ExecutionRequest`
4. Execute through UnifiedExecutionEngine
5. Post-execution monitoring

**Returns**: `ExecutionResult` from execution engine

---

### Position Tracking (NEW: Enhanced)

#### `update_position(symbol: str, side: str, quantity: float, price: float = 0.0)`
Manual position update for external position tracking

**Updates**:
- `current_positions[symbol]` based on side (buy/sell)
- Risk metrics via `_update_risk_metrics()`

**Logging**: Detailed position change logging

#### `get_current_position(symbol: str) -> float`
Get current position for symbol

#### `get_all_positions() -> Dict[str, float]`
Get all current positions (copy)

#### `async _post_execution_monitoring(authorization, result)`
**ENHANCED** - Real-time position tracking and risk updates

**Actions**:
1. Extract trade details from authorization/result
2. Update position tracking
3. Update risk metrics
4. Check post-execution risk limits
5. Trigger risk reduction if needed

---

### Risk Assessment Methods

#### `_calculate_risk_impact(request: TradingDecisionRequest) -> float`
Calculate risk impact of trading request

**Formula**:
```python
position_impact = (quantity * price) / portfolio_value
volatility_adjustment = max(1.0, volatility_estimate)
regime_multiplier = regime_risk_multipliers[market_regime]
total_impact = position_impact * volatility_adjustment * regime_multiplier
```

#### `_check_position_limits(request: TradingDecisionRequest) -> bool`
Check if request violates position limits

**Logic**:
```python
new_position = current_position + quantity
position_pct = abs(new_position * price) / portfolio_value
return position_pct <= max_position_size
```

#### `_check_concentration_limits(request) -> bool`
Check concentration limits (similar to position limits)

#### `_check_strategy_limits(request) -> bool`
Check strategy allocation limits

#### `_get_regime_risk_adjustment(request) -> float`
Get regime-based risk adjustment

**Formula**:
```python
regime_multiplier = regime_risk_multipliers[market_regime]
confidence_adjustment = max(0.5, regime_confidence)
return regime_multiplier * confidence_adjustment
```

---

### Authorization Level Determination

#### `_determine_authorization_level(risk_impact, position_check, concentration_check, strategy_check, regime_adjustment, request) -> AuthorizationLevel`
**ENHANCED** - Signal confidence validation

**Rejection Conditions**:
- Position/concentration/strategy check fails
- Signal confidence < min_signal_confidence (0.6)

**Confidence-Based Logic**:
- **Extreme confidence (0.9+)**: Automatic if risk <= elevated_threshold
- **High confidence (0.8+)**: Automatic if risk <= 2x auto_threshold
- **Standard**: Risk-based thresholds

**Risk Thresholds**:
- `<= 0.01`: AUTOMATIC
- `<= 0.05`: STANDARD
- `<= 0.10`: ELEVATED
- `> 0.10`: EMERGENCY

---

### Monitoring & Control

#### `async _continuous_monitoring()`
Continuous risk monitoring loop (runs if `real_time_monitoring=True`)

**Actions (every `monitoring_frequency` seconds)**:
1. Monitor positions (`_monitor_positions`)
2. Monitor authorizations (`_monitor_authorizations`)
3. Check portfolio risk limits (`_check_portfolio_risk_limits`)
4. Update risk metrics (`_update_risk_metrics`)

#### `_update_risk_metrics()`
Update current risk metrics

**Calculates**:
- Total exposure
- Max concentration
- Position count
- Net exposure

#### `async _check_post_execution_risk_limits(symbol, new_position)`
Check risk limits after position update

**Triggers**:
- Warning if position exceeds limits
- Automatic risk reduction if needed

#### `async _trigger_risk_reduction(symbol, current_pct, limit_pct)`
Trigger automatic risk reduction measures

---

### Emergency Control

#### `emergency_shutdown() -> bool`
Emergency shutdown of all trading operations

**Actions**:
1. Set `emergency_mode = True`
2. Set `is_operational = False`
3. Cancel all active authorizations
4. Stop monitoring task

**Result**: All subsequent authorization requests are REJECTED

#### `resume_operations() -> bool`
Resume normal operations after emergency shutdown

**Actions**:
1. Clear `emergency_mode`
2. Set `is_operational = True`
3. Clear active authorizations
4. Resume normal processing

#### `shutdown()`
Graceful shutdown of risk manager

---

### Orchestrator Integration (ISystemComponent)

#### `register_with_orchestrator(orchestrator) -> str`
Register component with HierarchicalSystemOrchestrator

**Registration Details**:
- **Layer**: `ComponentLayer.GOVERNANCE`
- **Authority**: `AuthorityLevel.GOVERNANCE_CONTROL`
- **Init Order**: 5 (early initialization)

**Returns**: `component_id`

#### `async start() -> bool`
Start component operations

#### `async stop() -> bool`
Stop component operations

#### `async health_check() -> Dict[str, Any]`
Perform health check

**Returns**:
```python
{
    'healthy': bool,
    'initialized': bool,
    'operational': bool,
    'component_type': 'CentralRiskManager',
    'active_authorizations': int,
    'pending_requests': int,
    'current_var': float,
    'portfolio_value': float,
    'total_positions': int,
    'execution_engine_available': bool
}
```

#### `get_status() -> Dict[str, Any]`
Get component status (detailed)

---

### Standardized Data Flow Methods

#### Data Consumption (from other components)

**From Strategies**:
- `process_decisions(decisions) -> List[Any]`
- `handle_decisions(decisions) -> List[Any]`
- `process_regime_adjusted_strategies(strategy_data) -> Dict`
- `handle_strategy_risk_context(risk_context) -> Dict`
- `evaluate_regime_risk(regime_strategy_data) -> Dict`
- `consume_regime_strategies(regime_strategies) -> Dict`

**From Risk/Portfolio**:
- `validate_risk(risk_data) -> Dict`
- `check_limits(limit_data) -> Dict`
- `process_risk_metrics(risk_metrics) -> Dict`
- `handle_risk(risk_data) -> Dict`
- `analyze_risk(risk_data) -> Dict`

#### Data Production (to Analytics)
- `calculate_metrics(risk_data) -> Dict`
- `analyze_performance(performance_data) -> Dict`
- `generate_analytics(analytics_data) -> Dict`
- `produce_analytics(data) -> Dict`
- `create_performance_analytics(data) -> Dict`

---

### Callback & Event Methods

#### Risk Callbacks
- `set_risk_callbacks(components: List[Any])`
- `on_risk_limit_breach(risk_data: Dict)`
- `on_emergency_shutdown(shutdown_reason: str)`

#### Event Subscription
- `subscribe(subscriber)` - Subscribe to risk events
- `notify_regime_change(regime_analysis)` - Notify regime changes

#### Analytics Callbacks
- `set_analytics_callbacks(analytics_callback: Callable)`
- `on_performance_update(performance_data: Dict)`
- `notify_analytics(analytics_data: Dict)`

---

### Authorization & Audit

#### Authorization Methods
- `authorize_operation(operation: str, details: Dict) -> bool`
- `check_authority_level(required_level: str) -> bool`
- `validate_permissions(permission: str, context: Dict) -> bool`

#### Audit Trail
- `log_authorization(authorization_event: Dict) -> bool`
- `audit_authorization(authorization_id: str) -> Dict`
- `track_authorization(authorization_id: str) -> Dict`

**Properties**:
- `authorization_audit_trail: List[Dict]` - Full audit trail

---

### Risk Management Operations

#### Risk Authorization
```python
async def authorize_risk_operation(risk_operation: Dict) -> Dict:
    """Authorize risk operations through central governance"""
```

**Required Fields**:
- `operation_type`: Type of risk operation
- `risk_severity`: Risk severity level
- `impact_assessment`: Risk impact assessment
- `requester`: Requesting component

**Returns**:
```python
{
    'authorized': bool,
    'authorization_level': str,
    'risk_score': float,
    'limits_check': dict,
    'timestamp': str,
    'authorization_id': str  # if authorized
}
```

#### Risk Escalation
```python
async def escalate_risk_authorization(escalation_request: Dict) -> Dict:
    """Escalate risk authorization to higher authority"""
```

**Required Fields**:
- `operation`: Operation requiring escalation
- `current_level`: Current authorization level
- `escalation_reason`: Reason for escalation
- `risk_assessment`: Updated risk assessment

**Returns**: Escalation result with target level

#### Risk Reporting
```python
async def generate_risk_report() -> Dict:
    """Generate comprehensive risk report"""
```

**Report Contains**:
- Current risk metrics
- Risk assessment
- Compliance status
- Action items
- Recommendations

---

### Position Authorization

```python
async def authorize_position(position_request: Dict) -> bool:
    """Authorize a position through central risk management"""
```

**Required Fields**:
- `symbol`: Trading symbol
- `quantity`: Position size
- `value`: Position value
- `risk_level`: Risk assessment

#### Risk Limit Validation

```python
async def validate_risk_limits(portfolio_risk: Dict) -> Dict:
    """Validate portfolio risk against established limits"""
```

**Validates**:
- Exposure limits
- VaR limits
- Concentration limits

**Returns**:
```python
{
    'within_limits': bool,
    'violations': List[Dict],
    'exposure_ratio': float,
    'validation_timestamp': str,
    'recommendations': List[str]  # if violations
}
```

---

## 🔄 Integration Points

### With Risk Module (Phase 6 Complete)
- Uses risk calculation methods from `core_engine.risk.*`
- Integrates with `manager.py`, `manager_enhanced.py`, `exposure_calculator.py`, etc.
- Can leverage VaR, correlation, limit monitoring capabilities

### With UnifiedExecutionEngine
- Creates `ExecutionAuthorization` objects
- Delegates execution to `unified_execution_engine.execute_authorized_trade()`
- Receives `ExecutionResult` for post-execution monitoring

### With StrategyManager (WHAT)
- Receives trading signals via `TradingDecisionRequest`
- Validates strategy allocations
- Tracks strategy performance

### With TradingEngine (HOW)
- Controls execution methodology
- Approves execution algorithms
- Sets execution constraints

### With RegimeEngine
- Receives regime context for risk adjustments
- Applies regime-specific risk multipliers
- Adjusts authorization based on market conditions

### With Orchestrator
- Registers as GOVERNANCE layer component
- Receives system-wide coordination
- Participates in lifecycle management

---

## 🎯 Test Strategy

### Test Categories (30-35 tests planned)

1. **Initialization (3-4 tests)**
   - Default configuration
   - Custom configuration
   - Component registration
   - Failed initialization

2. **Authorization Flow (8-10 tests)**
   - Basic authorization (buy/sell)
   - Signal confidence validation (new)
   - Cash availability check
   - Position availability check
   - Rejected authorizations
   - Emergency mode rejection
   - Authorization expiry

3. **Risk Assessment (6-8 tests)**
   - Risk impact calculation
   - Position limit checks
   - Concentration checks
   - Strategy limit checks
   - Regime adjustments
   - Confidence-based levels

4. **Quantity Calculation (6-8 tests)**
   - Cash-constrained BUY orders
   - Position-constrained SELL orders
   - Volatility scaling
   - Regime scaling
   - Risk reduction
   - Precision rounding

5. **Position Tracking (3-4 tests)**
   - Position updates
   - Post-execution monitoring
   - Risk limit breaches
   - Risk reduction triggers

6. **Emergency Control (2-3 tests)**
   - Emergency shutdown
   - Resume operations
   - Graceful shutdown

7. **Integration (2-3 tests)**
   - Orchestrator integration
   - Health checks
   - Status reporting

---

## 📝 Key Testing Insights

### From Phase 6 Learnings

1. **Pre-Read Strategy**: Complete file understanding before testing
2. **Fixture Accuracy**: Use metadata correctly in requests
3. **Cash/Position Constraints**: Critical for realistic authorization
4. **Signal Confidence**: New requirement from test findings (0.6 minimum)
5. **Precision**: Round quantities to 2 decimals

### Critical Test Data

**Request Metadata Must Include**:
```python
metadata = {
    'available_cash': 950000.0,  # For BUY orders
    'price': 100.0,               # For quantity calculations
    'volatility_estimate': 0.15   # For volatility scaling
}
```

**Typical Request**:
```python
request = TradingDecisionRequest(
    decision_type=TradingDecisionType.POSITION_ENTRY,
    strategy_id="test_strategy",
    symbol="AAPL",
    side="buy",
    quantity=100.0,
    confidence=0.85,  # >= 0.6 required!
    market_regime="low_volatility",
    regime_confidence=0.9,
    volatility_estimate=0.10,
    current_position=0.0,  # For SELL: must have position
    metadata={
        'available_cash': 950000.0,
        'price': 100.0
    }
)
```

---

## 🚀 Phase 7 Day 1 Complete Understanding

**File Complexity**: HIGH (2047 lines, multiple integration points)

**Key Architecture**:
- Central governance hub pattern
- All trading flows through authorization
- Integration with 5+ major components
- Real-time monitoring and position tracking
- Emergency control mechanisms

**Ready for Phase 3**: Test creation with accurate fixtures

**Target Coverage**: 85%+ (following Phase 6 success pattern)

---

*API Documentation Complete - Ready for Test Creation* ✅
