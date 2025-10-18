# VaR Calculator API Testing Notes
**File:** core_engine/risk/var_calculator.py  
**Total Lines:** 646  
**Target Coverage:** 70%+ (Stretch: 80%+)  
**Current Baseline:** 35% (268 statements)

---

## File Overview

### Purpose
Comprehensive Value at Risk (VaR) calculator providing:
- Multiple VaR calculation methodologies (Historical, Parametric, Monte Carlo, Cornish-Fisher, Filtered Historical)
- Conditional VaR (CVaR / Expected Shortfall) calculation
- Comprehensive risk metrics (volatility, max drawdown, Sharpe/Sortino ratios, beta, etc.)
- Stress testing with predefined scenarios (2008 Crisis, COVID-19, Rate Shocks)
- Portfolio risk analysis with benchmark comparison

### Key Features
1. **5 VaR Methods:** Historical, Parametric, Monte Carlo, Cornish-Fisher, Filtered Historical
2. **Risk Metrics:** VaR, CVaR, volatility, drawdown, Sharpe, Sortino, skewness, kurtosis
3. **Stress Testing:** Predefined scenarios + custom scenario support
4. **Benchmarking:** Beta and tracking error calculation
5. **History Tracking:** Calculation audit trail

---

## Enums (2 types)

### 1. VarMethod (6 values)
```python
class VarMethod(Enum):
    HISTORICAL = "historical"                 # Historical simulation
    PARAMETRIC = "parametric"                 # Normal distribution assumption
    MONTE_CARLO = "monte_carlo"              # Monte Carlo simulation
    CORNISH_FISHER = "cornish_fisher"        # Accounts for skew/kurtosis
    FILTERED_HISTORICAL = "filtered_historical"  # Volatility-weighted
    EVT = "extreme_value_theory"             # Extreme value theory (not implemented)
```

**Testing Strategy:**
- Test all enum values exist
- Validate string values
- Test method selection in calculations
- EVT method should raise ValueError (not implemented)
- **Expected Coverage:** 100%

### 2. RiskMeasure (6 values)
```python
class RiskMeasure(Enum):
    VAR = "var"                              # Value at Risk
    CVAR = "cvar"                            # Conditional VaR (Expected Shortfall)
    MAX_DRAWDOWN = "max_drawdown"           # Maximum drawdown
    VOLATILITY = "volatility"                # Standard deviation
    BETA = "beta"                            # Market beta
    TRACKING_ERROR = "tracking_error"        # vs benchmark
```

**Testing Strategy:**
- Test all risk measure values
- Validate enum strings
- **Expected Coverage:** 100%

---

## Dataclasses (3 types)

### 1. VarResult
```python
@dataclass
class VarResult:
    var_value: float                         # VaR amount
    confidence_level: float                  # e.g., 0.95, 0.99
    method: VarMethod                        # Calculation method
    time_horizon: int                        # Days (typically 1)
    currency: str = "USD"                    # Currency
    timestamp: datetime                      # Calculation time
    metadata: Dict[str, Any]                 # Method-specific info
```

**Testing Strategy:**
- Test dataclass creation
- Validate all field types
- Test with various confidence levels (0.95, 0.99, 0.999)
- Test different time horizons (1, 10, 21 days)
- **Expected Coverage:** 100%

### 2. RiskMetrics
```python
@dataclass
class RiskMetrics:
    var_1d: Dict[float, float]              # Confidence level → VaR
    cvar_1d: Dict[float, float]             # Confidence level → CVaR
    volatility_daily: float                  # Daily volatility
    volatility_annual: float                 # Annualized volatility
    max_drawdown: float                      # Maximum drawdown
    beta: Optional[float] = None            # Portfolio beta
    tracking_error: Optional[float] = None  # Tracking error
    sharpe_ratio: Optional[float] = None    # Sharpe ratio
    sortino_ratio: Optional[float] = None   # Sortino ratio
    skewness: Optional[float] = None        # Return skewness
    kurtosis: Optional[float] = None        # Excess kurtosis
    timestamp: datetime                      # Calculation time
```

**Testing Strategy:**
- Test comprehensive metrics calculation
- Validate all metrics present
- Test with/without benchmark
- **Expected Coverage:** 100%

### 3. StressTestScenario
```python
@dataclass
class StressTestScenario:
    name: str                                # Scenario name
    description: str                         # Description
    factor_shocks: Dict[str, float]         # Factor → shock %
    correlation_changes: Optional[Dict[Tuple[str, str], float]] = None
    volatility_multipliers: Optional[Dict[str, float]] = None
```

**Testing Strategy:**
- Test scenario creation
- Test predefined scenarios (2008, COVID, rate shock)
- Test custom scenarios
- **Expected Coverage:** 100%

---

## Main Class: VarCalculator

### Initialization

#### `__init__(config: Optional[Dict[str, Any]] = None)`
**Purpose:** Initialize VaR calculator with configuration

**Parameters:**
- `config`: Optional configuration dictionary

**Configuration Options:**
- `confidence_levels`: List of confidence levels (default: [0.95, 0.99, 0.999])
- `time_horizon_days`: Default time horizon (default: 1)
- `lookback_window_days`: Historical data window (default: 252)
- `min_observations`: Minimum data points (default: 50)
- `monte_carlo_simulations`: Number of MC simulations (default: 10,000)
- `risk_free_rate_annual`: Annual risk-free rate (default: 0.02)

**Internal State:**
- `_lock`: Threading lock for thread safety
- `_price_cache`: Dict for caching prices
- `_covariance_cache`: Dict for caching covariance matrices
- `_calculation_history`: Deque (maxlen=1000) for audit trail
- `_stress_scenarios`: Dict of predefined stress scenarios

**Behavior:**
- Loads 3 default stress scenarios:
  - `crisis_2008`: 2008 Financial Crisis (40% equity drop, 500bp credit widening)
  - `covid_2020`: COVID-19 March 2020 (35% equity drop, 60% oil drop)
  - `rate_shock`: Interest rate shock (200bp rate increase)

**Testing Strategy:**
- Test default initialization
- Test custom configuration for each parameter
- Test default stress scenarios loaded
- Validate all config defaults
- **Expected Coverage:** ~95%

---

### Core VaR Calculation Methods

#### `async calculate_var(returns, method=HISTORICAL, confidence_levels=None, time_horizon=1) -> Dict[float, VarResult]`
**Purpose:** Calculate VaR using specified method

**Parameters:**
- `returns`: pd.Series or pd.DataFrame of returns
- `method`: VarMethod enum (default: HISTORICAL)
- `confidence_levels`: List of confidence levels (default: [0.95, 0.99, 0.999])
- `time_horizon`: Time horizon in days (default: 1)

**Returns:** Dict mapping confidence_level → VarResult

**Behavior:**
- Validates sufficient data (len >= min_observations)
- Routes to appropriate calculation method
- Stores calculation in history
- Logs calculation time
- Handles both pd.Series and pd.DataFrame inputs

**Supported Methods:**
1. HISTORICAL: Historical simulation
2. PARAMETRIC: Normal distribution VaR
3. MONTE_CARLO: Monte Carlo simulation
4. CORNISH_FISHER: Adjusted for skew/kurtosis
5. FILTERED_HISTORICAL: Volatility-weighted historical
6. EVT: Not implemented (raises ValueError)

**Error Handling:**
- ValueError if insufficient data
- ValueError if unsupported method
- Logs and re-raises exceptions

**Testing Strategy:**
- Test all 5 implemented methods
- Test with various confidence levels
- Test with different time horizons (1, 10, 21 days)
- Test insufficient data error
- Test unsupported method error (EVT)
- Test history tracking
- Test both Series and DataFrame inputs
- **Expected Coverage:** ~90%

---

#### `async _calculate_historical_var(returns, confidence_levels, time_horizon) -> Dict[float, VarResult]`
**Purpose:** Historical simulation VaR (non-parametric)

**Parameters:**
- `returns`: Return series or DataFrame
- `confidence_levels`: List of confidence levels
- `time_horizon`: Days

**Returns:** Dict of VarResults

**Algorithm:**
1. Convert DataFrame to portfolio returns if needed (sum across columns)
2. Scale returns by sqrt(time_horizon) for multi-day horizon
3. For each confidence level:
   - Calculate quantile = 1 - confidence_level
   - VaR = -percentile(returns, quantile * 100)

**Formula:** VaR_α = -Quantile(R, 1-α) * sqrt(T)

**Testing Strategy:**
- Test with various confidence levels
- Test time horizon scaling
- Test DataFrame vs Series input
- Validate VaR always positive
- **Expected Coverage:** ~95%

---

#### `async _calculate_parametric_var(returns, confidence_levels, time_horizon) -> Dict[float, VarResult]`
**Purpose:** Parametric VaR (assumes normal distribution)

**Parameters:**
- `returns`: Return series or DataFrame
- `confidence_levels`: List of confidence levels
- `time_horizon`: Days

**Returns:** Dict of VarResults

**Algorithm:**
1. Calculate mean and std of returns
2. Scale for time horizon: mean*T, std*sqrt(T)
3. For each confidence level:
   - z_score = norm.ppf(1 - confidence_level)
   - VaR = -(scaled_mean + z_score * scaled_std)

**Formula:** VaR_α = -(μT + z_α * σ√T)

**Testing Strategy:**
- Test with various confidence levels
- Test z-score calculation
- Test mean/std extraction
- Verify time scaling
- **Expected Coverage:** ~95%

---

#### `async _calculate_monte_carlo_var(returns, confidence_levels, time_horizon) -> Dict[float, VarResult]`
**Purpose:** Monte Carlo simulation VaR

**Parameters:**
- `returns`: Return series or DataFrame
- `confidence_levels`: List of confidence levels
- `time_horizon`: Days

**Returns:** Dict of VarResults

**Algorithm:**
1. Estimate mean and std from historical returns
2. Generate N random simulations (default: 10,000)
   - np.random.normal(mean*T, std*sqrt(T), N)
   - Uses seed=42 for reproducibility
3. For each confidence level:
   - VaR = -percentile(simulations, (1-α)*100)

**Testing Strategy:**
- Test with default 10,000 simulations
- Test with custom simulation count
- Verify seed for reproducibility
- Test various confidence levels
- **Expected Coverage:** ~95%

---

#### `async _calculate_cornish_fisher_var(returns, confidence_levels, time_horizon) -> Dict[float, VarResult]`
**Purpose:** Cornish-Fisher expansion VaR (accounts for non-normality)

**Parameters:**
- `returns`: Return series or DataFrame
- `confidence_levels`: List of confidence levels
- `time_horizon`: Days

**Returns:** Dict of VarResults

**Algorithm:**
1. Calculate mean, std, skewness, kurtosis
2. For each confidence level:
   - z = norm.ppf(1 - confidence_level)
   - z_cf = z + (z²-1)*S/6 + (z³-3z)*K/24 - (2z³-5z)*S²/36
   - VaR = -(scaled_mean + z_cf * scaled_std)

**Formula:** Modified z-score adjusts for skewness (S) and excess kurtosis (K)

**Testing Strategy:**
- Test with skewed distributions
- Test with high kurtosis
- Verify adjustment calculation
- Compare with parametric VaR
- **Expected Coverage:** ~92%

---

#### `async _calculate_filtered_historical_var(returns, confidence_levels, time_horizon) -> Dict[float, VarResult]`
**Purpose:** Volatility-weighted historical VaR (EWMA)

**Parameters:**
- `returns`: Return series or DataFrame
- `confidence_levels`: List of confidence levels
- `time_horizon`: Days

**Returns:** Dict of VarResults

**Algorithm:**
1. Calculate exponential weights with lambda=0.94
2. Weight returns: weighted_returns = returns * sqrt(weights)
3. Apply historical VaR on weighted returns

**Formula:** Recent observations get higher weight

**Testing Strategy:**
- Test weight calculation
- Test lambda factor (0.94)
- Compare with unweighted historical
- **Expected Coverage:** ~90%

---

### Risk Metrics Calculation

#### `async calculate_comprehensive_risk_metrics(returns, benchmark_returns=None) -> RiskMetrics`
**Purpose:** Calculate full suite of risk metrics

**Parameters:**
- `returns`: pd.Series or pd.DataFrame of returns
- `benchmark_returns`: Optional benchmark for beta/tracking error

**Returns:** RiskMetrics object

**Metrics Calculated:**
1. **VaR (1-day):** For default confidence levels (95%, 99%, 99.9%)
2. **CVaR (1-day):** Expected Shortfall = mean of returns beyond VaR
3. **Volatility Daily:** std(returns)
4. **Volatility Annual:** daily_vol * sqrt(252)
5. **Max Drawdown:** Maximum peak-to-trough decline
6. **Beta:** covariance(portfolio, benchmark) / variance(benchmark)
7. **Tracking Error:** std(portfolio - benchmark) * sqrt(252)
8. **Sharpe Ratio:** (mean_excess_return / std) * sqrt(252)
9. **Sortino Ratio:** (mean_excess_return / downside_std) * sqrt(252)
10. **Skewness:** Third moment (asymmetry)
11. **Kurtosis:** Fourth moment (tail fatness, excess)

**Testing Strategy:**
- Test all 11 metrics calculated
- Test with benchmark (beta, tracking error)
- Test without benchmark (beta=None)
- Test Sharpe calculation with risk-free rate
- Test Sortino with downside deviation
- Test edge cases (zero volatility)
- **Expected Coverage:** ~90%

---

#### `_calculate_max_drawdown(returns: pd.Series) -> float`
**Purpose:** Calculate maximum drawdown

**Algorithm:**
1. Calculate cumulative returns: (1 + returns).cumprod()
2. Calculate running maximum: cumulative.expanding().max()
3. Calculate drawdown: (cumulative - running_max) / running_max
4. Return minimum drawdown (most negative)

**Formula:** MDD = min((Pt - Peak) / Peak)

**Testing Strategy:**
- Test with declining series (should have large drawdown)
- Test with increasing series (should have small drawdown)
- Test with constant series (zero drawdown)
- **Expected Coverage:** 100%

---

#### `_calculate_beta(portfolio_returns, benchmark_returns) -> float`
**Purpose:** Calculate portfolio beta relative to benchmark

**Algorithm:**
1. Align returns (drop NaN)
2. Calculate covariance(portfolio, benchmark)
3. Calculate variance(benchmark)
4. Beta = covariance / variance

**Formula:** β = Cov(Rp, Rb) / Var(Rb)

**Edge Cases:**
- If < 2 observations: return 1.0
- If benchmark variance = 0: return 1.0

**Testing Strategy:**
- Test with correlated returns
- Test with uncorrelated returns
- Test insufficient data edge case
- Test zero variance edge case
- **Expected Coverage:** ~95%

---

### Stress Testing

#### `async stress_test_portfolio(positions, scenario_name, portfolio_value) -> Dict[str, float]`
**Purpose:** Run stress test on portfolio using predefined scenario

**Parameters:**
- `positions`: Dict[str, Any] of position data
  - Each position should have: market_value, asset_type, sector
- `scenario_name`: Name of scenario ('crisis_2008', 'covid_2020', 'rate_shock', or custom)
- `portfolio_value`: Current portfolio value

**Returns:** Dict with:
- `portfolio_pnl`: Total P&L under stress
- `portfolio_return_pct`: Return percentage
- `stressed_portfolio_value`: New portfolio value
- `position_details`: Per-position stress results

**Algorithm:**
1. Get scenario from _stress_scenarios
2. For each position:
   - Determine stress factor based on asset_type and scenario
   - Calculate stressed_value = current_value * (1 + stress_factor)
   - Calculate P&L
3. Aggregate portfolio results

**Testing Strategy:**
- Test all 3 default scenarios
- Test custom scenario
- Test various asset types (EQUITY, BOND, COMMODITY, FX)
- Test unknown scenario error
- Test empty portfolio
- **Expected Coverage:** ~88%

---

#### `_get_stress_factor_for_position(position, scenario) -> float`
**Purpose:** Get stress factor for individual position

**Mapping Logic:**
- EQUITY/STOCK → scenario.factor_shocks['EQUITY']
- BOND/FIXED_INCOME → scenario.factor_shocks['RATES']
- COMMODITY → scenario.factor_shocks['OIL'] or ['COMMODITIES']
- FX → scenario.factor_shocks['FX']
- Unknown → 0.0

**Testing Strategy:**
- Test each asset type mapping
- Test oil vs general commodity
- Test unknown asset type
- **Expected Coverage:** ~92%

---

#### `add_stress_scenario(scenario: StressTestScenario) -> None`
**Purpose:** Add custom stress test scenario

**Testing Strategy:**
- Test adding custom scenario
- Test scenario retrieval after adding
- **Expected Coverage:** 100%

---

#### `get_stress_scenarios() -> Dict[str, StressTestScenario]`
**Purpose:** Get all available stress scenarios

**Returns:** Copy of _stress_scenarios dict

**Testing Strategy:**
- Test returns all default scenarios
- Test returns added custom scenarios
- **Expected Coverage:** 100%

---

### Utility Methods

#### `get_calculation_history() -> List[Dict[str, Any]]`
**Purpose:** Get VaR calculation history

**Returns:** List of calculation records

**Thread Safety:** Uses self._lock

**Testing Strategy:**
- Test history retrieval
- Test after multiple calculations
- Test thread safety
- **Expected Coverage:** 100%

---

#### `async cleanup() -> None`
**Purpose:** Cleanup resources

**Testing Strategy:**
- Test cleanup execution
- **Expected Coverage:** 100%

---

## Test Categories (9 categories, ~28 tests)

### Category 1: Enums and Dataclasses (5 tests)
1. Test VarMethod enum values (6)
2. Test RiskMeasure enum values (6)
3. Test VarResult dataclass
4. Test RiskMetrics dataclass
5. Test StressTestScenario dataclass

**Expected Coverage:** 100% of enums and dataclasses

---

### Category 2: Initialization (3 tests)
1. Test default initialization
2. Test custom configuration (all parameters)
3. Test default stress scenarios loaded

**Expected Coverage:** ~95% of __init__ and _load_default_scenarios

---

### Category 3: Historical VaR (3 tests)
1. Test historical VaR calculation
2. Test with multiple confidence levels
3. Test time horizon scaling

**Expected Coverage:** ~95% of _calculate_historical_var

---

### Category 4: Parametric VaR (2 tests)
1. Test parametric VaR calculation
2. Test z-score for various confidence levels

**Expected Coverage:** ~95% of _calculate_parametric_var

---

### Category 5: Monte Carlo VaR (2 tests)
1. Test Monte Carlo VaR
2. Test reproducibility (seed=42)

**Expected Coverage:** ~95% of _calculate_monte_carlo_var

---

### Category 6: Cornish-Fisher VaR (2 tests)
1. Test Cornish-Fisher VaR with skewed data
2. Test adjustment vs parametric VaR

**Expected Coverage:** ~92% of _calculate_cornish_fisher_var

---

### Category 7: Filtered Historical VaR (2 tests)
1. Test filtered historical VaR
2. Test exponential weighting

**Expected Coverage:** ~90% of _calculate_filtered_historical_var

---

### Category 8: Comprehensive Risk Metrics (4 tests)
1. Test all metrics calculation
2. Test with benchmark (beta, tracking error)
3. Test without benchmark
4. Test max drawdown calculation

**Expected Coverage:** ~90% of calculate_comprehensive_risk_metrics, _calculate_max_drawdown, _calculate_beta

---

### Category 9: Stress Testing (4 tests)
1. Test 2008 crisis scenario
2. Test COVID-19 scenario
3. Test rate shock scenario
4. Test custom scenario
5. Test stress factor mapping

**Expected Coverage:** ~88% of stress_test_portfolio, _get_stress_factor_for_position, add/get scenarios

---

### Category 10: Integration and Edge Cases (1 test)
1. Test calculate_var main method with all methods
2. Test insufficient data error
3. Test unsupported method error
4. Test calculation history

**Expected Coverage:** ~90% of calculate_var, get_calculation_history, cleanup

---

## Testing Strategy Summary

### Mock Requirements
- **pandas.DataFrame/Series**: Use real pandas with sample data
- **numpy**: Use real numpy for calculations
- **scipy.stats**: Use real scipy (norm.ppf)
- **datetime**: Use real datetime
- **logging**: Let it log or mock if needed

### Test Data Patterns
```python
# Sample returns (100 days)
np.random.seed(42)
returns = pd.Series(
    np.random.normal(0.0005, 0.01, 100),  # Mean 0.05%, Std 1%
    index=pd.date_range('2024-01-01', periods=100, freq='D')
)

# Sample portfolio returns (DataFrame)
portfolio_returns = pd.DataFrame({
    'AAPL': np.random.normal(0.0006, 0.012, 100),
    'GOOGL': np.random.normal(0.0004, 0.010, 100),
    'MSFT': np.random.normal(0.0005, 0.011, 100)
}, index=pd.date_range('2024-01-01', periods=100, freq='D'))

# Sample positions for stress testing
positions = {
    'AAPL': {'market_value': 100000, 'asset_type': 'EQUITY', 'sector': 'TECH'},
    'XOM': {'market_value': 50000, 'asset_type': 'EQUITY', 'sector': 'ENERGY'},
    'TLT': {'market_value': 75000, 'asset_type': 'BOND', 'sector': 'TREASURY'}
}
```

### Coverage Targets
| Component | Target | Stretch |
|-----------|--------|---------|
| Enums/Dataclasses | 100% | 100% |
| Initialization | 95% | 98% |
| Historical VaR | 93% | 97% |
| Parametric VaR | 93% | 97% |
| Monte Carlo VaR | 93% | 97% |
| Cornish-Fisher VaR | 90% | 95% |
| Filtered Historical VaR | 88% | 93% |
| Risk Metrics | 88% | 92% |
| Stress Testing | 85% | 90% |
| Utility Methods | 100% | 100% |
| **OVERALL** | **70%+** | **80%+** |

### Known Challenges
1. **EVT method:** Not implemented, should raise ValueError
2. **scipy.stats compatibility:** May have Python 3.13 issues (from Day 3 experience)
3. **Cornish-Fisher formula:** Complex multi-term equation
4. **Stress test mapping:** Multiple asset type branches
5. **Beta calculation edge cases:** Zero variance, insufficient data

### Dependencies to Import
```python
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from core_engine.risk.var_calculator import (
    VarCalculator,
    VarMethod,
    RiskMeasure,
    VarResult,
    RiskMetrics,
    StressTestScenario
)
```

---

## Expected Coverage Distribution

### High Coverage Areas (95%+)
- Enums and dataclasses
- Initialization
- Historical VaR
- Parametric VaR
- Monte Carlo VaR
- Max drawdown calculation
- Utility methods

### Medium-High Coverage Areas (85-95%)
- Cornish-Fisher VaR
- Filtered Historical VaR
- Risk metrics calculation
- Beta calculation
- Stress testing

### Medium Coverage Areas (70-85%)
- Stress factor mapping (many branches)
- Error handling paths
- Edge cases in risk metrics

### Areas Likely to Miss Coverage
- EVT method (not implemented)
- Some error logging paths
- Cache usage (if implemented but not exercised)
- Some asset type edge cases in stress testing

---

## Pre-Read Assessment

**File Complexity:** Medium-High
- 646 lines, well-structured
- 2 enums, 3 dataclasses, 1 main class
- 15+ methods (5 VaR methods, risk metrics, stress testing)
- Mix of sync and async methods
- Financial calculations require understanding

**Testing Approach:**
- Use real pandas/numpy/scipy
- Generate realistic return distributions
- Test all VaR methods systematically
- Validate mathematical correctness
- Test edge cases (zero vol, insufficient data)
- Compare methods (parametric vs MC vs historical)

**Estimated Test Count:** ~28 tests
**Estimated Coverage:** 70-80%
**Estimated Time:** 3-4 hours

**Risk Areas:**
- Cornish-Fisher formula complexity
- Stress test asset type mapping
- Beta calculation edge cases
- scipy compatibility (Python 3.13 issue from Day 3)

**Confidence:** HIGH - Clear financial logic, good separation of VaR methods, straightforward risk metrics
