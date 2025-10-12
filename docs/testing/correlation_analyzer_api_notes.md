# Correlation Analyzer API Testing Notes
**File:** core_engine/risk/correlation_analyzer.py  
**Total Lines:** 636  
**Target Coverage:** 70%+ (Stretch: 80%+)  
**Current Baseline:** 35% (296 statements)

---

## File Overview

### Purpose
Advanced correlation analysis system providing:
- Multiple correlation calculation methods (Pearson, Spearman, Kendall, EWMA, DCC, Shrinkage)
- Dynamic correlation matrix computation with eigenvalue analysis
- Correlation regime detection (Low, Normal, High, Crisis)
- Tail dependence analysis for extreme event correlation
- Stress testing scenarios for correlation breakdown/spike
- Statistical analysis and historical tracking

### Key Features
1. **Multi-method correlation**: 6 different calculation methods
2. **Matrix validation**: Eigenvalue analysis, condition number, positive definiteness
3. **Regime detection**: Automatic regime classification with probability
4. **Tail dependence**: Upper/lower tail dependence analysis
5. **Stress testing**: Multiple scenario-based stress tests
6. **Caching & History**: Performance optimization and audit trail

---

## Enums (2 types)

### 1. CorrelationMethod (6 values)
```python
class CorrelationMethod(Enum):
    PEARSON = "pearson"      # Standard Pearson correlation
    SPEARMAN = "spearman"    # Rank-based Spearman correlation
    KENDALL = "kendall"      # Kendall tau correlation
    EWMA = "ewma"            # Exponentially weighted moving average
    DCC = "dcc"              # Dynamic conditional correlation
    SHRINKAGE = "shrinkage"  # Ledoit-Wolf shrinkage estimator
```

**Testing Strategy:**
- Test all 6 enum values exist
- Validate string values
- Test method selection in calculations
- **Expected Coverage:** 100%

### 2. CorrelationRegime (4 values)
```python
class CorrelationRegime(Enum):
    LOW = "low"          # Low correlation regime (<30%)
    NORMAL = "normal"    # Normal correlation regime (30-60%)
    HIGH = "high"        # High correlation regime (60-80%)
    CRISIS = "crisis"    # Crisis regime (>80%)
```

**Testing Strategy:**
- Test all 4 regime values
- Test regime detection logic
- Test regime transitions
- **Expected Coverage:** 100%

---

## Dataclasses (4 types)

### 1. CorrelationResult
```python
@dataclass
class CorrelationResult:
    asset1: str                                    # First asset identifier
    asset2: str                                    # Second asset identifier
    correlation: float                             # Correlation coefficient
    method: CorrelationMethod                      # Calculation method used
    confidence_interval: Tuple[float, float]       # CI bounds
    p_value: float                                 # Statistical significance
    sample_size: int                               # Number of observations
    timestamp: datetime                            # Calculation time
    metadata: Dict[str, Any]                       # Additional info
```

**Testing Strategy:**
- Test dataclass creation with all fields
- Validate field types
- Test with various correlation values (-1 to 1)
- Test confidence interval calculation
- **Expected Coverage:** 100%

### 2. CorrelationMatrix
```python
@dataclass
class CorrelationMatrix:
    matrix: pd.DataFrame                          # The correlation matrix
    method: CorrelationMethod                     # Calculation method
    calculation_time: datetime                    # When calculated
    eigenvalues: List[float]                      # Matrix eigenvalues
    condition_number: float                       # Condition number (stability)
    assets: List[str]                             # Asset identifiers
    sample_period: Tuple[datetime, datetime]      # Data period
    is_positive_definite: bool                    # Matrix validity
    metadata: Dict[str, Any]                      # Additional info
```

**Testing Strategy:**
- Test dataclass with real matrix
- Validate eigenvalue calculation
- Test condition number computation
- Test positive definiteness check
- **Expected Coverage:** 100%

### 3. RegimeDetectionResult
```python
@dataclass
class RegimeDetectionResult:
    current_regime: CorrelationRegime                    # Current regime
    regime_probability: float                            # Probability [0-1]
    regime_duration: timedelta                           # Time in regime
    last_regime_change: datetime                         # Last change time
    regime_history: List[Tuple[datetime, CorrelationRegime]]  # History
    confidence: float                                    # Detection confidence
    metadata: Dict[str, Any]                            # Additional info
```

**Testing Strategy:**
- Test regime detection output
- Validate probability calculations
- Test regime duration tracking
- Test history management
- **Expected Coverage:** 100%

### 4. TailDependenceResult
```python
@dataclass
class TailDependenceResult:
    asset1: str                          # First asset
    asset2: str                          # Second asset
    upper_tail_dependence: float         # Upper tail coefficient
    lower_tail_dependence: float         # Lower tail coefficient
    tail_correlation: float              # Correlation in extremes
    extreme_percentile: float = 0.05     # Threshold (default 5%)
    timestamp: datetime                  # Calculation time
```

**Testing Strategy:**
- Test tail dependence calculation
- Validate upper/lower tail values
- Test with different percentiles
- Test extreme event correlation
- **Expected Coverage:** 100%

---

## Main Class: CorrelationAnalyzer

### Initialization

#### `__init__(config: Optional[Dict[str, Any]] = None)`
**Purpose:** Initialize correlation analyzer with configuration

**Parameters:**
- `config`: Optional configuration dictionary

**Configuration Options:**
- `ewma_lambda`: EWMA decay factor (default: 0.94)
- `min_observations`: Minimum data points (default: 50)
- `regime_detection_window`: Window for regime detection (default: 60)
- `tail_threshold`: Tail percentile threshold (default: 0.05)
- `cache_ttl_seconds`: Cache TTL (default: 300)
- `regime_thresholds`: Dict with 'low', 'normal', 'high', 'crisis' thresholds

**Internal State:**
- `_lock`: Threading lock for thread safety
- `_correlation_cache`: Dict for caching results
- `_regime_history`: Deque (maxlen=1000) for regime tracking
- `_calculation_history`: Deque (maxlen=1000) for calculation audit
- `_current_regime`: Current regime state
- `_regime_start_time`: When current regime started

**Testing Strategy:**
- Test default initialization
- Test custom configuration
- Test all config parameters
- Validate default values
- Test thread safety initialization
- **Expected Coverage:** ~95%

---

### Core Calculation Methods

#### `async calculate_correlation_matrix(returns: pd.DataFrame, method: CorrelationMethod = PEARSON, min_periods: Optional[int] = None) -> CorrelationMatrix`
**Purpose:** Calculate full correlation matrix using specified method

**Parameters:**
- `returns`: DataFrame of asset returns (datetime index, asset columns)
- `method`: Correlation method to use (default: PEARSON)
- `min_periods`: Minimum observations required (default: self.min_observations)

**Returns:** CorrelationMatrix with:
- Correlation matrix as DataFrame
- Eigenvalues (sorted descending)
- Condition number (max/min eigenvalue)
- Positive definiteness flag
- Sample period (first and last timestamp)
- Metadata (calculation time, sample size, etc.)

**Behavior:**
- Validates sufficient data (len >= min_periods)
- Filters to numeric columns only
- Routes to appropriate calculation method
- Calculates eigenvalues using np.linalg.eigvals
- Checks positive definiteness (all eigenvalues > 1e-12)
- Stores calculation in history
- Logs calculation details

**Error Handling:**
- ValueError if insufficient data
- ValueError if unsupported method
- Logs and re-raises exceptions

**Testing Strategy:**
- Test all 6 correlation methods
- Test with various data sizes
- Test minimum observations validation
- Test eigenvalue calculation
- Test condition number computation
- Test positive definiteness detection
- Test non-numeric column filtering
- Test calculation history storage
- Test error cases (insufficient data, invalid method)
- **Expected Coverage:** ~90%

---

#### `async _calculate_ewma_correlation(returns: pd.DataFrame) -> pd.DataFrame`
**Purpose:** Calculate exponentially weighted moving average correlation

**Parameters:**
- `returns`: DataFrame of asset returns

**Returns:** DataFrame correlation matrix

**Behavior:**
- Uses pandas ewm() with alpha = 1 - self.ewma_lambda
- Calculates EWMA covariance matrix
- Extracts most recent covariance (last N rows)
- Converts covariance to correlation using standard deviation normalization
- Formula: corr = cov / (std1 * std2)

**Testing Strategy:**
- Test EWMA calculation with sample data
- Verify lambda parameter usage
- Test min_periods parameter
- Validate correlation range [-1, 1]
- **Expected Coverage:** ~90%

---

#### `async _calculate_shrinkage_correlation(returns: pd.DataFrame) -> pd.DataFrame`
**Purpose:** Calculate Ledoit-Wolf shrinkage estimator correlation

**Parameters:**
- `returns`: DataFrame of asset returns

**Returns:** DataFrame correlation matrix

**Behavior:**
- Calculates sample correlation matrix
- Creates identity matrix as target
- Applies shrinkage: (1-α)*sample + α*target
- Uses constant shrinkage intensity (0.2)
- Reduces estimation error in high-dimensional cases

**Testing Strategy:**
- Test shrinkage calculation
- Verify shrinkage intensity (0.2)
- Test target matrix (identity)
- Validate result is valid correlation matrix
- **Expected Coverage:** ~85%

---

#### `async calculate_pairwise_correlation(asset1_returns: pd.Series, asset2_returns: pd.Series, method: CorrelationMethod = PEARSON, confidence_level: float = 0.95) -> CorrelationResult`
**Purpose:** Calculate correlation between two assets with statistical inference

**Parameters:**
- `asset1_returns`: First asset return series
- `asset2_returns`: Second asset return series
- `method`: Correlation method (default: PEARSON)
- `confidence_level`: Confidence level for CI (default: 0.95)

**Returns:** CorrelationResult with:
- Correlation coefficient
- P-value for significance test
- Confidence interval using Fisher transformation
- Sample size
- Metadata

**Behavior:**
- Aligns series (drops NaN values)
- Validates minimum observations
- Calculates correlation based on method:
  - PEARSON: stats.pearsonr()
  - SPEARMAN: spearmanr()
  - KENDALL: kendalltau()
  - Other: defaults to Pearson
- Computes confidence interval using Fisher z-transformation:
  - z = 0.5 * ln((1+r)/(1-r))
  - SE = 1/sqrt(n-3)
  - CI_z = z ± z_score * SE
  - Transform back: r = (e^(2z) - 1) / (e^(2z) + 1)

**Error Handling:**
- ValueError if insufficient aligned data
- Logs and re-raises exceptions

**Testing Strategy:**
- Test all correlation methods (Pearson, Spearman, Kendall)
- Test confidence interval calculation
- Test Fisher transformation
- Test with various confidence levels (0.90, 0.95, 0.99)
- Test p-value calculation
- Test data alignment (mismatched indices)
- Test insufficient data error
- Test perfect correlation (1.0)
- Test zero correlation
- Test negative correlation
- **Expected Coverage:** ~92%

---

### Regime Detection Methods

#### `async detect_correlation_regime(correlation_matrix: pd.DataFrame, returns: pd.DataFrame) -> RegimeDetectionResult`
**Purpose:** Detect current correlation regime and track changes

**Parameters:**
- `correlation_matrix`: Full correlation matrix
- `returns`: Asset returns DataFrame (for context)

**Returns:** RegimeDetectionResult with regime info

**Behavior:**
- Extracts upper triangle of correlation matrix (excluding diagonal)
- Calculates average pairwise correlation
- Classifies regime based on thresholds:
  - LOW: avg_corr < 0.3
  - NORMAL: 0.3 ≤ avg_corr < 0.6
  - HIGH: 0.6 ≤ avg_corr < 0.8
  - CRISIS: avg_corr ≥ 0.8
- Detects regime changes (comparison with self._current_regime)
- Updates regime history on change
- Calculates regime duration (now - self._regime_start_time)
- Computes regime probability using _calculate_regime_probability()
- Calculates confidence using _calculate_regime_confidence()
- Returns last 10 regime changes

**State Management:**
- Updates self._current_regime
- Updates self._regime_start_time
- Appends to self._regime_history

**Testing Strategy:**
- Test all 4 regime classifications
- Test regime change detection
- Test regime history tracking
- Test with various average correlations
- Test duration calculation
- Test probability calculation
- Test confidence calculation
- Test no regime change scenario
- **Expected Coverage:** ~88%

---

#### `_calculate_regime_probability(avg_correlation: float, regime: CorrelationRegime) -> float`
**Purpose:** Calculate probability of being in specified regime

**Parameters:**
- `avg_correlation`: Average pairwise correlation
- `regime`: Target regime

**Returns:** Probability [0.0-1.0]

**Behavior:**
- **LOW regime:**
  - If avg_corr < threshold_low: 1.0 - (avg_corr / threshold_low)
  - Else: decay to 0 as move to NORMAL threshold
  
- **NORMAL regime:**
  - If in [threshold_low, threshold_normal]: 1.0 - distance_from_center
  - Else: 0.0
  
- **HIGH regime:**
  - If in [threshold_normal, threshold_high]: 1.0 - distance_from_center
  - Else: 0.0
  
- **CRISIS regime:**
  - If avg_corr >= threshold_high: (avg_corr - threshold_high) / (1.0 - threshold_high)
  - Else: 0.0

**Testing Strategy:**
- Test each regime probability calculation
- Test boundary conditions at thresholds
- Test center of each regime
- Test outside regime ranges
- Test probability range [0.0-1.0]
- **Expected Coverage:** ~95%

---

#### `_calculate_regime_confidence(regime_duration: timedelta, avg_correlation: float) -> float`
**Purpose:** Calculate confidence in regime detection

**Parameters:**
- `regime_duration`: Time in current regime
- `avg_correlation`: Average correlation value

**Returns:** Confidence [0.1-1.0]

**Behavior:**
- **Duration confidence:** min(1.0, hours / 24) - full confidence after 24 hours
- **Correlation confidence:** min(1.0, |avg_corr - 0.5| * 2) - max at extremes (0 or 1)
- **Overall confidence:** (duration_conf + corr_conf) / 2
- **Bounded:** max(0.1, min(1.0, overall_confidence))

**Testing Strategy:**
- Test with various durations (1 hour, 12 hours, 24+ hours)
- Test with extreme correlations (near 0, near 1)
- Test with mid-range correlations
- Test confidence bounds [0.1-1.0]
- **Expected Coverage:** ~90%

---

### Tail Dependence Analysis

#### `async calculate_tail_dependence(asset1_returns: pd.Series, asset2_returns: pd.Series, threshold_percentile: float = 0.05) -> TailDependenceResult`
**Purpose:** Calculate tail dependence for extreme event correlation

**Parameters:**
- `asset1_returns`: First asset return series
- `asset2_returns`: Second asset return series
- `threshold_percentile`: Tail threshold (default: 0.05 = 5%)

**Returns:** TailDependenceResult with tail coefficients

**Behavior:**
- Aligns series (drops NaN)
- Validates minimum observations
- Calculates threshold_count = n * threshold_percentile
- **Upper tail dependence:**
  - Find upper quantile for each asset (1 - percentile)
  - Count joint occurrences (both > threshold)
  - upper_tail_dep = both_upper / threshold_count
- **Lower tail dependence:**
  - Find lower quantile for each asset (percentile)
  - Count joint occurrences (both < threshold)
  - lower_tail_dep = both_lower / threshold_count
- **Tail correlation:**
  - Filter to extreme events (either asset in tail)
  - Calculate correlation on extreme events only
  - If < 5 extreme events: return 0.0

**Testing Strategy:**
- Test upper tail dependence calculation
- Test lower tail dependence calculation
- Test tail correlation in extremes
- Test with various percentiles (0.01, 0.05, 0.10)
- Test with insufficient data
- Test with perfect tail dependence
- Test with zero tail dependence
- Test edge case (< 5 extreme events)
- **Expected Coverage:** ~88%

---

### Stress Testing

#### `async stress_test_correlations(correlation_matrix: pd.DataFrame, stress_scenarios: Dict[str, float]) -> Dict[str, pd.DataFrame]`
**Purpose:** Apply stress scenarios to correlation matrix

**Parameters:**
- `correlation_matrix`: Base correlation matrix
- `stress_scenarios`: Dict of {scenario_name: stress_factor}

**Returns:** Dict of {scenario_name: stressed_matrix}

**Supported Scenarios:**
1. **"correlation_breakdown":** All correlations → 0 (identity matrix)
2. **"correlation_spike":** Increase correlations towards ±1
   - Positive correlations move towards +1
   - Negative correlations move towards -1
   - Formula: corr + (sign - corr) * stress_factor
3. **"sector_contagion":** Within-sector correlation spike
   - Currently: multiplies all correlations by (1 + stress_factor)
4. **Default:** Multiply all correlations by stress_factor

**Post-Processing:**
- Clips all values to [-0.99, 0.99]
- Ensures diagonal = 1.0 (self-correlation)

**Testing Strategy:**
- Test correlation_breakdown scenario
- Test correlation_spike scenario (positive and negative)
- Test sector_contagion scenario
- Test custom scenario (default behavior)
- Test multiple scenarios simultaneously
- Test stress_factor edge cases (0, 0.5, 1.0, 2.0)
- Test matrix validity after stress
- Test diagonal preservation
- **Expected Coverage:** ~85%

---

### Statistical Analysis

#### `get_correlation_statistics(correlation_matrix: pd.DataFrame) -> Dict[str, float]`
**Purpose:** Calculate summary statistics for correlation matrix

**Parameters:**
- `correlation_matrix`: Correlation matrix to analyze

**Returns:** Dict with statistics:
- `mean_correlation`: Mean of all pairwise correlations
- `median_correlation`: Median correlation
- `std_correlation`: Standard deviation
- `min_correlation`: Minimum correlation
- `max_correlation`: Maximum correlation
- `positive_correlations`: Proportion > 0
- `high_correlations`: Proportion > 0.7
- `negative_correlations`: Proportion < 0
- `near_zero_correlations`: Proportion |r| < 0.1

**Behavior:**
- Extracts upper triangle (excluding diagonal)
- Filters non-zero values
- Calculates descriptive statistics
- Calculates proportions for various thresholds
- Returns empty dict if no correlations

**Testing Strategy:**
- Test with various correlation matrices
- Test all 9 statistics calculations
- Test with all positive correlations
- Test with all negative correlations
- Test with mixed correlations
- Test with high correlations
- Test with near-zero correlations
- Test empty matrix handling
- **Expected Coverage:** ~90%

---

### History and Cache Management

#### `get_calculation_history() -> List[Dict[str, Any]]`
**Purpose:** Retrieve correlation calculation history

**Returns:** List of calculation records with:
- timestamp
- method
- assets (count)
- sample_size
- calculation_time
- condition_number

**Thread Safety:** Uses self._lock

**Testing Strategy:**
- Test history retrieval
- Test thread safety
- Test history after multiple calculations
- Test empty history
- **Expected Coverage:** 100%

---

#### `get_regime_history() -> List[Tuple[datetime, CorrelationRegime]]`
**Purpose:** Retrieve correlation regime change history

**Returns:** List of (timestamp, regime) tuples

**Thread Safety:** Uses self._lock

**Testing Strategy:**
- Test history retrieval
- Test thread safety
- Test after regime changes
- Test empty history
- **Expected Coverage:** 100%

---

#### `clear_cache() -> None`
**Purpose:** Clear correlation calculation cache

**Behavior:**
- Acquires lock
- Clears self._correlation_cache dict
- Logs action

**Thread Safety:** Uses self._lock

**Testing Strategy:**
- Test cache clearing
- Test thread safety
- Test cache after clear
- **Expected Coverage:** 100%

---

#### `async cleanup() -> None`
**Purpose:** Cleanup resources

**Behavior:**
- Logs cleanup completion
- Currently minimal cleanup needed

**Testing Strategy:**
- Test cleanup execution
- Test idempotency (multiple calls)
- **Expected Coverage:** 100%

---

## Test Categories (10 categories, ~35 tests)

### Category 1: Enums and Dataclasses (6 tests)
1. Test CorrelationMethod enum values
2. Test CorrelationRegime enum values
3. Test CorrelationResult dataclass
4. Test CorrelationMatrix dataclass
5. Test RegimeDetectionResult dataclass
6. Test TailDependenceResult dataclass

**Expected Coverage:** 100% of dataclasses and enums

---

### Category 2: Initialization and Configuration (3 tests)
1. Test default initialization
2. Test custom configuration (all parameters)
3. Test state initialization (locks, caches, history)

**Expected Coverage:** ~95% of __init__

---

### Category 3: Correlation Matrix Calculation (6 tests)
1. Test Pearson correlation matrix
2. Test Spearman correlation matrix
3. Test Kendall correlation matrix
4. Test EWMA correlation matrix
5. Test Shrinkage correlation matrix
6. Test eigenvalue and condition number calculation
7. Test insufficient data error
8. Test non-numeric column filtering

**Expected Coverage:** ~90% of calculate_correlation_matrix, _calculate_ewma_correlation, _calculate_shrinkage_correlation

---

### Category 4: Pairwise Correlation (4 tests)
1. Test Pearson pairwise correlation
2. Test Spearman and Kendall methods
3. Test confidence interval calculation (Fisher transform)
4. Test data alignment with mismatched indices
5. Test insufficient data error

**Expected Coverage:** ~92% of calculate_pairwise_correlation

---

### Category 5: Regime Detection (5 tests)
1. Test LOW regime detection
2. Test NORMAL regime detection
3. Test HIGH regime detection
4. Test CRISIS regime detection
5. Test regime change detection and history
6. Test regime probability calculation
7. Test regime confidence calculation

**Expected Coverage:** ~90% of detect_correlation_regime, _calculate_regime_probability, _calculate_regime_confidence

---

### Category 6: Tail Dependence (3 tests)
1. Test upper tail dependence calculation
2. Test lower tail dependence calculation
3. Test tail correlation in extreme events
4. Test various percentile thresholds

**Expected Coverage:** ~88% of calculate_tail_dependence

---

### Category 7: Stress Testing (4 tests)
1. Test correlation_breakdown scenario
2. Test correlation_spike scenario
3. Test sector_contagion scenario
4. Test multiple scenarios
5. Test matrix validity after stress

**Expected Coverage:** ~85% of stress_test_correlations

---

### Category 8: Statistical Analysis (2 tests)
1. Test correlation statistics calculation (all 9 metrics)
2. Test with various correlation patterns

**Expected Coverage:** ~90% of get_correlation_statistics

---

### Category 9: History and Cache (3 tests)
1. Test calculation history
2. Test regime history
3. Test cache clearing

**Expected Coverage:** 100% of get_calculation_history, get_regime_history, clear_cache

---

### Category 10: Cleanup and Edge Cases (2 tests)
1. Test cleanup
2. Test error handling and logging

**Expected Coverage:** 100% of cleanup, ~80% of error paths

---

## Testing Strategy Summary

### Mock Requirements
- **pandas.DataFrame/Series**: Use real pandas objects with sample data
- **numpy arrays**: Use real numpy for calculations
- **datetime**: Use real datetime, no mocking needed
- **scipy.stats functions**: Use real scipy (pearsonr, spearmanr, kendalltau)
- **logging**: Mock logger if needed, or let it log

### Test Data Patterns
```python
# Sample returns DataFrame
returns = pd.DataFrame({
    'AAPL': [0.01, -0.02, 0.015, -0.01, 0.02] * 20,  # 100 observations
    'GOOGL': [0.015, -0.015, 0.01, -0.005, 0.025] * 20,
    'MSFT': [0.012, -0.018, 0.014, -0.008, 0.022] * 20
}, index=pd.date_range('2024-01-01', periods=100, freq='D'))

# Sample correlation matrix
corr_matrix = pd.DataFrame({
    'AAPL': [1.0, 0.7, 0.6],
    'GOOGL': [0.7, 1.0, 0.8],
    'MSFT': [0.6, 0.8, 1.0]
}, index=['AAPL', 'GOOGL', 'MSFT'])
```

### Coverage Targets
| Component | Target | Stretch |
|-----------|--------|---------|
| Enums/Dataclasses | 100% | 100% |
| Initialization | 95% | 100% |
| Correlation Calculation | 88% | 92% |
| Pairwise Correlation | 90% | 95% |
| Regime Detection | 88% | 92% |
| Tail Dependence | 85% | 90% |
| Stress Testing | 82% | 88% |
| Statistics | 88% | 92% |
| History/Cache | 100% | 100% |
| Cleanup | 100% | 100% |
| **OVERALL** | **70%+** | **80%+** |

### Known Challenges
1. **EWMA calculation**: Requires understanding pandas ewm() behavior
2. **Fisher transformation**: Need accurate math for confidence intervals
3. **Eigenvalue calculation**: Use numpy, no mocking needed
4. **Regime probabilities**: Complex logic with multiple branches
5. **Tail dependence**: Requires sufficient sample data
6. **Stress testing**: Multiple scenario branches

### Dependencies to Import in Tests
```python
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from core_engine.risk.correlation_analyzer import (
    CorrelationAnalyzer,
    CorrelationMethod,
    CorrelationRegime,
    CorrelationResult,
    CorrelationMatrix,
    RegimeDetectionResult,
    TailDependenceResult
)
```

---

## Expected Coverage Distribution

### High Coverage Areas (90%+)
- Enums and dataclasses
- Initialization
- Pairwise correlation
- Statistics calculation
- History/cache management
- Cleanup

### Medium-High Coverage Areas (80-90%)
- Correlation matrix calculation
- Regime detection
- Tail dependence
- EWMA/Shrinkage methods

### Medium Coverage Areas (70-80%)
- Stress testing (many scenarios)
- Error handling paths
- Edge cases in complex calculations

### Areas Likely to Miss Coverage
- DCC method (not implemented, would raise error)
- Sector mapping in contagion scenario
- Some error logging paths
- Cache TTL logic (if implemented but not visible)

---

## Pre-Read Assessment

**File Complexity:** Medium-High
- 636 lines, well-structured
- 2 enums, 4 dataclasses, 1 main class
- 15+ public/private methods
- Mix of sync and async methods
- Statistical calculations require understanding
- Thread safety with locks

**Testing Approach:**
- Use real pandas/numpy/scipy (no mocking scientific libraries)
- Focus on mathematical correctness
- Test all correlation methods
- Test all regime classifications
- Test edge cases (empty data, extreme values)
- Validate statistical properties (p-values, CIs)

**Estimated Test Count:** ~35 tests
**Estimated Coverage:** 70-80%
**Estimated Time:** 3-4 hours

**Risk Areas:**
- Fisher transformation math (must be exact)
- Eigenvalue interpretation
- Regime probability calculation (many branches)
- EWMA/shrinkage implementation details
- Tail dependence edge cases

**Confidence:** HIGH - Well-structured code, clear mathematical operations, good separation of concerns
