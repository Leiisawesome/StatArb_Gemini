# Enhanced Risk Manager API Testing Notes
**File:** core_engine/risk/manager_enhanced.py  
**Total Lines:** 538  
**Target Coverage:** 70%+ (Stretch: 80%+)  
**Current Baseline:** 54% (243 statements)

---

## File Overview

### Purpose
Comprehensive risk management system integrating all risk components:
- **Exposure Calculation:** Asset, sector, country, currency exposures
- **VaR Analysis:** Value at Risk and risk metrics
- **Stress Testing:** Multiple crisis scenarios
- **Limit Monitoring:** Risk limit enforcement with alerts
- **Correlation Analysis:** Correlation regime detection

### Key Features
1. **Unified Risk Assessment:** Single entry point for comprehensive risk calculation
2. **Real-Time Monitoring:** Automated risk monitoring loop
3. **Alert System:** Multi-level alert handling (WARNING, CRITICAL)
4. **Risk Scoring:** Overall risk score (0-100) with weighted components
5. **Snapshot History:** Risk data retention (30 days default)
6. **Component Integration:** Orchestrates 5 risk subsystems

---

## Dataclasses (2 types)

### 1. RiskSnapshot
```python
@dataclass
class RiskSnapshot:
    timestamp: datetime                                    # When snapshot was taken
    portfolio_value: float                                # Total portfolio value
    exposures: Dict[ExposureType, ExposureBreakdown]     # All exposure types
    risk_metrics: RiskMetrics                            # VaR, CVaR, volatility, etc.
    correlation_matrix: CorrelationMatrix                # Asset correlations
    stress_test_results: Dict[str, PortfolioStressResult] # Stress test outcomes
    limit_breaches: List[LimitBreach]                    # Current breaches
    regime_status: str                                    # "LOW", "NORMAL", "HIGH", "CRISIS"
    risk_score: float                                     # Overall score 0-100
    metadata: Dict[str, Any] = field(default_factory=dict) # Calculation details
```

**Testing Strategy:**
- Test dataclass creation with all fields
- Validate timestamp generation
- Test metadata storage
- **Expected Coverage:** 100%

### 2. RiskAlert
```python
@dataclass
class RiskAlert:
    alert_id: str                                        # Unique alert ID
    alert_type: str                                      # "HIGH_RISK_SCORE", "CRISIS_REGIME", etc.
    severity: AlertSeverity                             # WARNING, CRITICAL
    message: str                                         # Human-readable message
    details: Dict[str, Any]                            # Additional alert data
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False                          # Alert acknowledgment status
```

**Testing Strategy:**
- Test alert creation
- Validate severity levels
- Test acknowledged flag
- **Expected Coverage:** 100%

---

## Main Class: EnhancedRiskManager

### Initialization

#### `__init__(config: Optional[Dict[str, Any]] = None)`
**Purpose:** Initialize enhanced risk manager with all components

**Configuration Options:**
```python
config = {
    'exposure_config': {},           # ExposureCalculator config
    'var_config': {},               # VarCalculator config  
    'stress_config': {},            # StressTester config
    'limit_config': {},             # LimitMonitor config
    'correlation_config': {},       # CorrelationAnalyzer config
    'calculation_interval_seconds': 300,  # 5 minutes default
    'snapshot_retention_days': 30,
    'enable_real_time_monitoring': True,
    'risk_weights': {               # Risk score component weights
        'var': 0.25,
        'stress_test': 0.25,
        'correlation': 0.20,
        'concentration': 0.15,
        'limits': 0.15
    }
}
```

**Internal Components:**
- `self.exposure_calculator`: ExposureCalculator instance
- `self.var_calculator`: VarCalculator instance
- `self.stress_tester`: StressTester instance
- `self.limit_monitor`: LimitMonitor instance
- `self.correlation_analyzer`: CorrelationAnalyzer instance

**Internal State:**
- `self._lock`: Threading lock for thread safety
- `self._risk_snapshots`: Deque (maxlen=1000) for snapshots
- `self._risk_alerts`: Deque (maxlen=1000) for alerts
- `self._alert_handlers`: List of alert callback functions
- `self._monitoring_active`: Boolean monitoring state
- `self._monitoring_task`: asyncio.Task for monitoring loop

**Setup:**
- Registers `_handle_limit_alert` with limit_monitor

**Testing Strategy:**
- Test default initialization
- Test custom configuration for each component
- Test risk_weights customization
- Test component initialization
- Validate internal state setup
- **Expected Coverage:** ~90%

---

### Core Risk Calculation

#### `async calculate_comprehensive_risk(positions, portfolio_value, returns_data, market_data) -> RiskSnapshot`
**Purpose:** Calculate complete risk assessment across all components

**Parameters:**
- `positions`: Dict[str, Any] - Current portfolio positions
- `portfolio_value`: float - Total portfolio value
- `returns_data`: Optional[pd.DataFrame] - Historical returns
- `market_data`: Optional[Dict[str, Any]] - Current market data

**Returns:** RiskSnapshot with all risk metrics

**Process:**
1. **Calculate Exposures:** Calls `exposure_calculator.calculate_exposures()`
2. **Calculate Risk Metrics:** Calls `var_calculator.calculate_comprehensive_risk_metrics()` if returns_data available
3. **Calculate Correlations:** Calls `correlation_analyzer.calculate_correlation_matrix()` if multiple assets
4. **Run Stress Tests:** Calls `_run_key_stress_tests()` for 4 scenarios
5. **Check Limits:** Calls `limit_monitor.check_limits()`
6. **Detect Regime:** Calls `correlation_analyzer.detect_correlation_regime()`
7. **Calculate Risk Score:** Calls `_calculate_risk_score()`
8. **Store Snapshot:** Calls `_store_risk_snapshot()`
9. **Check Alerts:** Calls `_check_risk_alerts()`

**Metadata Captured:**
- `calculation_time`: Total calculation duration
- `positions_count`: Number of positions
- `returns_data_available`: Boolean flag

**Testing Strategy:**
- Test with full data (all components)
- Test with minimal data (positions only)
- Test with missing returns_data (None)
- Test with single asset (no correlation)
- Test error handling
- Mock all risk component calls
- **Expected Coverage:** ~85%

---

#### `async _run_key_stress_tests(positions, portfolio_value) -> Dict[str, PortfolioStressResult]`
**Purpose:** Run predefined stress test scenarios

**Key Scenarios:**
1. `financial_crisis_2008`
2. `covid_pandemic_2020`
3. `rate_shock`
4. `geopolitical_crisis`

**Returns:** Dict mapping scenario_name → PortfolioStressResult

**Behavior:**
- Iterates through key_scenarios list
- Calls `stress_tester.run_stress_test()` for each
- Logs warnings for failed scenarios (doesn't raise)
- Returns partial results if some fail

**Testing Strategy:**
- Test with all scenarios succeeding
- Test with some scenarios failing
- Test empty positions
- Mock stress_tester.run_stress_test()
- **Expected Coverage:** ~90%

---

#### `_calculate_risk_score(...) -> float`
**Purpose:** Calculate overall risk score (0-100, higher = riskier)

**Parameters:**
- `exposures`: Dict of exposure breakdowns
- `risk_metrics`: Optional RiskMetrics
- `stress_results`: Dict of stress test results
- `limit_breaches`: List of breaches
- `regime_status`: str ("LOW", "NORMAL", "HIGH", "CRISIS")

**Returns:** float (0-100)

**Components (weighted):**

1. **VaR Component (25% weight):**
   - Uses risk_metrics.var_1d[0.99]
   - Formula: `min(100, abs(var_99) * 10)`

2. **Stress Test Component (25% weight):**
   - Uses worst scenario PnL percentage
   - Formula: `min(100, abs(worst_pnl_pct))`

3. **Correlation/Regime Component (20% weight):**
   - Regime scores: LOW=20, NORMAL=40, HIGH=70, CRISIS=100

4. **Concentration Component (15% weight):**
   - Uses max single name exposure percentage
   - Formula: `min(100, max_concentration * 2)` (50% → 100 score)

5. **Limit Breach Component (15% weight):**
   - Critical breach: 50 points each
   - Warning breach: 25 points each
   - Formula: `min(100, critical*50 + warning*25)`

**Final:** Sum of weighted components, clamped to [0, 100]

**Testing Strategy:**
- Test with all components present
- Test with missing components (None)
- Test high risk scenario (score > 80)
- Test low risk scenario (score < 30)
- Test weight customization
- Validate score bounds (0-100)
- **Expected Coverage:** ~95%

---

### Snapshot & Alert Management

#### `_store_risk_snapshot(snapshot: RiskSnapshot) -> None`
**Purpose:** Store snapshot and cleanup old ones

**Behavior:**
- Appends snapshot to `_risk_snapshots` deque (thread-safe)
- Removes snapshots older than `snapshot_retention_days` (30 default)
- Uses threading lock for thread safety

**Testing Strategy:**
- Test snapshot storage
- Test retention cleanup
- Test thread safety
- **Expected Coverage:** ~95%

---

#### `async _check_risk_alerts(snapshot: RiskSnapshot) -> None`
**Purpose:** Generate alerts based on snapshot conditions

**Alert Conditions:**

1. **High Risk Score (CRITICAL):**
   - Condition: `risk_score > 80`
   - alert_type: "HIGH_RISK_SCORE"

2. **Crisis Regime (CRITICAL):**
   - Condition: `regime_status == "CRISIS"`
   - alert_type: "CRISIS_REGIME"

3. **Extreme Stress Loss (WARNING):**
   - Condition: `stress_test_pnl_percentage < -20%`
   - alert_type: "EXTREME_STRESS_LOSS"
   - Generated for each extreme scenario

**Testing Strategy:**
- Test high risk score alert
- Test crisis regime alert
- Test extreme stress loss alert
- Test multiple alerts generated
- Test no alerts (normal conditions)
- **Expected Coverage:** ~90%

---

#### `async _handle_limit_alert(breach: LimitBreach) -> None`
**Purpose:** Handle alert from limit monitor

**Behavior:**
- Creates RiskAlert from LimitBreach
- alert_type: "LIMIT_BREACH"
- Includes limit_id, current_value, threshold, breach_amount
- Calls `_send_risk_alert()`

**Testing Strategy:**
- Test limit breach alert creation
- Test alert sending
- Mock _send_risk_alert
- **Expected Coverage:** 100%

---

#### `async _send_risk_alert(alert: RiskAlert) -> None`
**Purpose:** Send alert to all registered handlers

**Behavior:**
- Stores alert in `_risk_alerts` deque (thread-safe)
- Iterates through `_alert_handlers`
- Calls each handler with alert
- Logs errors if handler fails (doesn't raise)

**Testing Strategy:**
- Test alert storage
- Test handler invocation
- Test multiple handlers
- Test handler failure (error handling)
- **Expected Coverage:** ~95%

---

#### `add_alert_handler(handler: Callable[[RiskAlert], None]) -> None`
**Purpose:** Register alert callback function

**Testing Strategy:**
- Test adding handler
- Test multiple handlers
- Validate handler is callable
- **Expected Coverage:** 100%

---

#### `remove_alert_handler(handler: Callable[[RiskAlert], None]) -> None`
**Purpose:** Unregister alert callback

**Testing Strategy:**
- Test removing existing handler
- Test removing non-existent handler
- **Expected Coverage:** 100%

---

### Query Methods

#### `get_latest_risk_snapshot() -> Optional[RiskSnapshot]`
**Purpose:** Get most recent snapshot

**Returns:** Latest RiskSnapshot or None if no snapshots

**Testing Strategy:**
- Test with snapshots present
- Test with no snapshots (empty)
- Test thread safety
- **Expected Coverage:** 100%

---

#### `get_risk_snapshots(hours: int = 24) -> List[RiskSnapshot]`
**Purpose:** Get snapshots from time period

**Testing Strategy:**
- Test with default 24 hours
- Test with custom time period
- Test with no snapshots in range
- **Expected Coverage:** 100%

---

#### `get_recent_alerts(hours: int = 24) -> List[RiskAlert]`
**Purpose:** Get alerts from time period

**Testing Strategy:**
- Test with recent alerts
- Test with no alerts in range
- Test time filtering
- **Expected Coverage:** 100%

---

### Limit Management Methods

#### `async add_risk_limit(limit: RiskLimit) -> None`
**Purpose:** Add new risk limit

**Testing Strategy:**
- Test adding limit
- Verify limit_monitor.add_limit() called
- **Expected Coverage:** 100%

---

#### `async update_risk_limit(limit_id: str, updates: Dict[str, Any]) -> None`
**Purpose:** Update existing limit

**Testing Strategy:**
- Test updating limit
- Verify limit_monitor.update_limit() called
- **Expected Coverage:** 100%

---

#### `async remove_risk_limit(limit_id: str) -> None`
**Purpose:** Remove risk limit

**Testing Strategy:**
- Test removing limit
- Verify limit_monitor.remove_limit() called
- **Expected Coverage:** 100%

---

#### `get_all_risk_limits() -> List[RiskLimit]`
**Purpose:** Get all configured limits

**Testing Strategy:**
- Test retrieving limits
- Verify limit_monitor.get_all_limits() called
- **Expected Coverage:** 100%

---

#### `get_current_limit_breaches() -> List[LimitBreach]`
**Purpose:** Get active breaches

**Testing Strategy:**
- Test retrieving breaches
- Verify limit_monitor.get_current_breaches() called
- **Expected Coverage:** 100%

---

### Monitoring Methods

#### `async start_monitoring(data_provider: Callable[[], Dict[str, Any]]) -> None`
**Purpose:** Start automated risk monitoring loop

**Behavior:**
- Sets `_monitoring_active = True`
- Creates asyncio task for `_monitoring_loop()`
- Prevents duplicate start (warns if already active)

**Testing Strategy:**
- Test starting monitoring
- Test duplicate start (should warn)
- Verify monitoring_task created
- Mock data_provider
- **Expected Coverage:** ~90%

---

#### `async stop_monitoring() -> None`
**Purpose:** Stop monitoring loop

**Behavior:**
- Sets `_monitoring_active = False`
- Cancels `_monitoring_task`
- Handles CancelledError

**Testing Strategy:**
- Test stopping monitoring
- Test stop when not running
- Verify task cancellation
- **Expected Coverage:** ~95%

---

#### `async _monitoring_loop(data_provider: Callable[[], Dict[str, Any]]) -> None`
**Purpose:** Main monitoring loop (runs continuously)

**Process:**
1. Call `data_provider()` to get current data
2. Extract positions, portfolio_value, returns_data, market_data
3. Call `calculate_comprehensive_risk()`
4. Sleep for `risk_calculation_interval` seconds
5. Repeat until `_monitoring_active = False`

**Error Handling:**
- Catches CancelledError (breaks loop)
- Catches general exceptions (logs, continues after sleep)

**Testing Strategy:**
- Test monitoring loop execution
- Test data provider calls
- Test calculation calls
- Test error handling
- Test cancellation
- Mock sleep to avoid delays
- **Expected Coverage:** ~85%

---

### Summary Methods

#### `get_risk_summary() -> Dict[str, Any]`
**Purpose:** Get comprehensive risk summary

**Returns:**
```python
{
    'timestamp': datetime,
    'portfolio_value': float,
    'risk_score': float,
    'regime_status': str,
    'limit_breaches': int,
    'recent_alerts': int,
    'var_metrics': {
        'var_95': float,
        'var_99': float,
        'volatility': float
    },
    'worst_stress_scenario': {
        'scenario': str,
        'pnl_percentage': float,
        'pnl_amount': float
    },
    'top_exposures': List[Dict] (top 10)
}
```

**Testing Strategy:**
- Test with full snapshot
- Test with no snapshot (returns status message)
- Test var_metrics extraction
- Test worst scenario calculation
- Test top exposures calculation
- **Expected Coverage:** ~90%

---

#### `_get_worst_stress_scenario(stress_results) -> Dict[str, Any]`
**Purpose:** Find worst stress test result

**Returns:** Dict with scenario, pnl_percentage, pnl_amount

**Testing Strategy:**
- Test with multiple scenarios
- Test with empty results
- Test finding minimum PnL
- **Expected Coverage:** 100%

---

#### `_get_top_exposures(exposures) -> List[Dict[str, Any]]`
**Purpose:** Get top 10 exposures by absolute percentage

**Returns:** List of dicts with type, identifier, value, percentage

**Testing Strategy:**
- Test with multiple exposure types
- Test sorting by absolute percentage
- Test top 10 limit
- Test with < 10 exposures
- **Expected Coverage:** ~95%

---

### Cleanup

#### `async cleanup() -> None`
**Purpose:** Cleanup all components

**Process:**
1. Stop monitoring loop
2. Cleanup exposure_calculator
3. Cleanup var_calculator
4. Cleanup stress_tester
5. Cleanup limit_monitor
6. Cleanup correlation_analyzer

**Testing Strategy:**
- Test cleanup execution
- Verify all components cleaned
- Test cleanup when monitoring active
- **Expected Coverage:** 100%

---

## Test Categories (8 categories, ~27 tests)

### Category 1: Dataclasses (2 tests)
1. Test RiskSnapshot creation
2. Test RiskAlert creation

**Expected Coverage:** 100% of dataclasses

---

### Category 2: Initialization (2 tests)
1. Test default initialization
2. Test custom configuration

**Expected Coverage:** ~90% of __init__

---

### Category 3: Comprehensive Risk Calculation (5 tests)
1. Test with full data (all components)
2. Test with minimal data (positions only)
3. Test with missing returns_data
4. Test with single asset (no correlation)
5. Test error handling

**Expected Coverage:** ~85% of calculate_comprehensive_risk

---

### Category 4: Risk Scoring (3 tests)
1. Test high risk scenario (score > 80)
2. Test low risk scenario
3. Test with missing components

**Expected Coverage:** ~95% of _calculate_risk_score

---

### Category 5: Alerts (5 tests)
1. Test high risk score alert
2. Test crisis regime alert
3. Test extreme stress loss alert
4. Test alert handler registration
5. Test limit breach alert

**Expected Coverage:** ~90% of alert methods

---

### Category 6: Snapshot & Query Methods (4 tests)
1. Test snapshot storage and retrieval
2. Test snapshot time filtering
3. Test alert retrieval
4. Test snapshot cleanup

**Expected Coverage:** ~95% of query methods

---

### Category 7: Monitoring (3 tests)
1. Test start/stop monitoring
2. Test monitoring loop execution
3. Test monitoring error handling

**Expected Coverage:** ~85% of monitoring methods

---

### Category 8: Summary & Limits (3 tests)
1. Test risk summary generation
2. Test limit management methods
3. Test cleanup method

**Expected Coverage:** ~90% of utility methods

---

## Testing Strategy Summary

### Mock Requirements
- **ExposureCalculator:** Mock calculate_exposures()
- **VarCalculator:** Mock calculate_comprehensive_risk_metrics()
- **StressTester:** Mock run_stress_test()
- **LimitMonitor:** Mock check_limits(), add_limit(), etc.
- **CorrelationAnalyzer:** Mock calculate_correlation_matrix(), detect_correlation_regime()
- **asyncio.sleep:** Mock to avoid delays in monitoring tests

### Test Data Patterns
```python
# Sample positions
positions = {
    'AAPL': {'symbol': 'AAPL', 'quantity': 100, 'market_value': 15000},
    'GOOGL': {'symbol': 'GOOGL', 'quantity': 50, 'market_value': 12500}
}

# Sample returns data
returns_data = pd.DataFrame({
    'AAPL': [0.01, -0.02, 0.015],
    'GOOGL': [0.005, -0.01, 0.02]
})

# Mock risk metrics
risk_metrics = RiskMetrics(
    var_1d={0.95: 1000, 0.99: 1500},
    cvar_1d={0.95: 1200, 0.99: 1800},
    volatility_daily=0.01,
    volatility_annual=0.16,
    max_drawdown=-0.15,
    ...
)

# Mock stress result
stress_result = PortfolioStressResult(
    scenario_name='financial_crisis_2008',
    total_pnl=-5000,
    total_pnl_percentage=-20.0,
    ...
)
```

### Coverage Targets
| Component | Target | Stretch |
|-----------|--------|---------|
| Dataclasses | 100% | 100% |
| Initialization | 90% | 95% |
| Risk Calculation | 85% | 90% |
| Risk Scoring | 95% | 98% |
| Alerts | 90% | 95% |
| Query Methods | 95% | 98% |
| Monitoring | 85% | 90% |
| Utilities | 90% | 95% |
| **OVERALL** | **70%+** | **80%+** |

### Known Challenges
1. **Component Integration:** Requires extensive mocking of 5 risk components
2. **Async Operations:** All major methods are async
3. **Monitoring Loop:** Needs careful mocking of asyncio.sleep and task management
4. **Thread Safety:** Uses threading.Lock for snapshot/alert storage
5. **Time-Based Filtering:** Snapshot/alert retrieval by time period

### Dependencies to Import
```python
import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from collections import deque

from core_engine.risk.manager_enhanced import (
    EnhancedRiskManager,
    RiskSnapshot,
    RiskAlert
)
from core_engine.risk.exposure_calculator import ExposureType, ExposureBreakdown
from core_engine.risk.var_calculator import RiskMetrics
from core_engine.risk.stress_tester import PortfolioStressResult
from core_engine.risk.limit_monitor import LimitBreach, AlertSeverity, RiskLimit
from core_engine.risk.correlation_analyzer import CorrelationMatrix
```

---

## Expected Coverage Distribution

### High Coverage Areas (95%+)
- Dataclasses
- Risk scoring calculation
- Snapshot storage and retrieval
- Alert handler management
- Limit management methods
- Cleanup method

### Medium-High Coverage Areas (85-95%)
- Comprehensive risk calculation
- Monitoring loop
- Alert generation
- Risk summary methods

### Medium Coverage Areas (70-85%)
- Some error handling paths
- Edge cases in monitoring
- Complex integration scenarios

### Areas Likely to Miss Coverage
- Some exception logging paths
- Rare race conditions
- Component initialization failures
- Deep monitoring error scenarios

---

## Pre-Read Assessment

**File Complexity:** Medium-High
- 538 lines, well-structured
- 2 dataclasses, 1 main class
- 25+ methods (mix of sync/async)
- Heavy component integration
- Monitoring loop with asyncio

**Testing Approach:**
- Extensive mocking of 5 risk components
- Focus on orchestration logic, not component internals
- Test risk score calculation thoroughly
- Validate alert generation logic
- Test monitoring start/stop carefully
- Mock asyncio.sleep to avoid delays

**Estimated Test Count:** ~27 tests
**Estimated Coverage:** 70-80%
**Estimated Time:** 3-4 hours

**Risk Areas:**
- Component integration complexity
- Async monitoring loop testing
- Thread-safe snapshot/alert storage
- Time-based filtering edge cases

**Confidence:** HIGH - Clear orchestration logic, good separation of concerns, straightforward testing with proper mocking
