# ExposureCalculator API Documentation
## Complete Reference for Testing

**File**: `core_engine/risk/exposure_calculator.py`  
**Lines**: 684  
**Current Coverage**: 72% (316 statements, 89 missed)  
**Target Coverage**: 80%+  
**Estimated Tests**: 30-35 tests across 7 categories

---

## 📋 Table of Contents

1. [Enums](#enums)
2. [Dataclasses](#dataclasses)
3. [Class Overview](#class-overview)
4. [Initialization](#initialization)
5. [Core Methods](#core-methods)
6. [Exposure Calculation Methods](#exposure-calculation-methods)
7. [Limit Management](#limit-management)
8. [Utility Methods](#utility-methods)
9. [Test Categories](#test-categories)

---

## 1. Enums

### ExposureType (9 values)
```python
class ExposureType(Enum):
    MARKET = "market"           # Overall market exposure
    SECTOR = "sector"           # Sector-level exposure
    REGION = "region"           # Geographic exposure
    CURRENCY = "currency"       # Currency exposure
    FACTOR = "factor"           # Factor exposure (value, growth, momentum, etc.)
    SINGLE_NAME = "single_name" # Individual position concentration
    CREDIT = "credit"           # Credit exposure (not implemented)
    DURATION = "duration"       # Duration exposure (not implemented)
    VOLATILITY = "volatility"   # Volatility exposure (not implemented)
```

**Testing Notes**:
- CREDIT, DURATION, VOLATILITY log warnings (unsupported)
- All other types have full implementations

### ExposureDirection (4 values)
```python
class ExposureDirection(Enum):
    LONG = "long"     # Long positions
    SHORT = "short"   # Short positions
    NET = "net"       # Net (long - short)
    GROSS = "gross"   # Gross (long + short)
```

---

## 2. Dataclasses

### ExposureItem
**Purpose**: Individual exposure entry

```python
@dataclass
class ExposureItem:
    identifier: str                    # Symbol, sector, region, etc.
    exposure_type: ExposureType        # Type of exposure
    value: float                       # Exposure value in currency
    percentage: float                  # Percentage of portfolio
    currency: str = "USD"              # Currency
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Testing Focus**:
- Required fields: identifier, exposure_type, value, percentage
- Optional fields: currency, timestamp, metadata
- Used in all exposure calculation results

### ExposureBreakdown
**Purpose**: Comprehensive exposure summary

```python
@dataclass
class ExposureBreakdown:
    total_exposure: float      # Total exposure (usually same as gross)
    long_exposure: float       # Long positions total
    short_exposure: float      # Short positions total
    net_exposure: float        # Long - short
    gross_exposure: float      # Long + short
    exposures: List[ExposureItem] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
```

**Testing Focus**:
- All 5 exposure calculations tested
- exposures list contains ExposureItem objects
- Relationships: net = long - short, gross = long + short

### ExposureLimit
**Purpose**: Limit definition for exposure monitoring

```python
@dataclass
class ExposureLimit:
    exposure_type: ExposureType    # Type of exposure to limit
    identifier: str                # Specific identifier (sector, symbol, etc.)
    max_exposure: float            # Maximum allowed exposure
    warning_threshold: float       # Warning level
    currency: str = "USD"          # Currency
    is_percentage: bool = True     # True = percentage, False = absolute value
```

**Testing Focus**:
- Both percentage and absolute limits
- Warning vs critical thresholds
- Limit key format: f"{exposure_type.value}_{identifier}"

### ExposureViolation
**Purpose**: Limit breach information

```python
@dataclass
class ExposureViolation:
    exposure_item: ExposureItem       # The exposure causing violation
    limit: ExposureLimit              # The limit that was breached
    violation_amount: float           # Amount of violation
    violation_percentage: float       # Violation as percentage
    severity: str                     # "WARNING" or "CRITICAL"
    timestamp: datetime = field(default_factory=datetime.now)
```

**Testing Focus**:
- WARNING severity: current_level > warning_threshold
- CRITICAL severity: current_level > max_exposure
- Violation calculations tested

---

## 3. Class Overview

### ExposureCalculator

**Purpose**: Comprehensive position exposure analysis

**Key Features**:
1. Multiple exposure types (market, sector, region, currency, factor, single-name)
2. Exposure limit monitoring with violations
3. Thread-safe operations
4. Calculation caching (5-minute TTL)
5. Calculation history tracking (1000 records)

**State**:
```python
self._lock = threading.Lock()                    # Thread safety
self._exposure_cache = {}                        # Cache for calculations
self._cache_ttl = 300                            # 5 minutes default
self._limits = {}                                # Exposure limits
self._violations = []                            # Recent violations
self._calculation_history = deque(maxlen=1000)  # Calculation records

self.include_derivatives = True                  # Include derivatives
self.include_cash = False                        # Include cash positions
self.base_currency = 'USD'                       # Base currency

self._factor_loadings = {}                       # Factor loadings
self._sector_mappings = {}                       # Symbol -> sector
self._geographic_mappings = {}                   # Symbol -> region
```

---

## 4. Initialization

### `__init__(config: Optional[Dict[str, Any]] = None)`

**Signature**:
```python
def __init__(self, config: Optional[Dict[str, Any]] = None):
```

**Parameters**:
- `config`: Optional configuration dictionary
  - `cache_ttl_seconds` (int): Cache TTL (default: 300)
  - `include_derivatives` (bool): Include derivatives (default: True)
  - `include_cash` (bool): Include cash (default: False)
  - `base_currency` (str): Base currency (default: 'USD')

**Initializes**:
- Thread lock
- Exposure cache
- Limits and violations storage
- Calculation history
- Sector mappings (9 hardcoded symbols)
- Geographic mappings (9 hardcoded symbols)

**Logs**: "ExposureCalculator initialized"

**Testing**:
```python
# Test 1: Default initialization
calculator = ExposureCalculator()
assert calculator.include_derivatives is True
assert calculator.include_cash is False
assert calculator.base_currency == 'USD'

# Test 2: Custom configuration
config = {
    'cache_ttl_seconds': 600,
    'include_derivatives': False,
    'include_cash': True,
    'base_currency': 'EUR'
}
calculator = ExposureCalculator(config)
assert calculator._cache_ttl == 600
assert calculator.include_derivatives is False
```

---

## 5. Core Methods

### `calculate_exposures(positions, portfolio_value, exposure_types=None)`

**Signature**:
```python
async def calculate_exposures(
    self,
    positions: Dict[str, Any],
    portfolio_value: float,
    exposure_types: Optional[List[ExposureType]] = None
) -> Dict[ExposureType, ExposureBreakdown]:
```

**Parameters**:
- `positions`: Dict[str, position_data] - Portfolio positions
- `portfolio_value`: Total portfolio value
- `exposure_types`: List of exposure types to calculate (default: all)

**Returns**:
- Dict[ExposureType, ExposureBreakdown]

**Behavior**:
1. If exposure_types is None, calculates all types
2. Thread-safe with `self._lock`
3. Calls `_calculate_exposure_type` for each type
4. Records calculation in history (timestamp, count, value, time)
5. Logs: f"Calculated {len} exposure types in {time:.3f}s"

**Testing**:
```python
# Test 1: All exposure types
positions = {'AAPL': {'quantity': 100, 'market_value': 15000}}
result = await calculator.calculate_exposures(positions, 100000)
assert ExposureType.MARKET in result
assert ExposureType.SECTOR in result

# Test 2: Specific exposure types
result = await calculator.calculate_exposures(
    positions, 100000,
    exposure_types=[ExposureType.MARKET, ExposureType.SINGLE_NAME]
)
assert len(result) == 2

# Test 3: Empty positions
result = await calculator.calculate_exposures({}, 100000)
for breakdown in result.values():
    assert breakdown.total_exposure == 0
```

---

## 6. Exposure Calculation Methods

### Private Method: `_calculate_exposure_type(exposure_type, positions, portfolio_value)`

**Dispatcher method** - routes to specific calculators

**Supported Types**:
1. MARKET → `_calculate_market_exposure`
2. SECTOR → `_calculate_sector_exposure`
3. REGION → `_calculate_regional_exposure`
4. CURRENCY → `_calculate_currency_exposure`
5. FACTOR → `_calculate_factor_exposure`
6. SINGLE_NAME → `_calculate_single_name_exposure`
7. Others → Logs warning, returns empty breakdown

### `_calculate_market_exposure(positions, portfolio_value)`

**Purpose**: Overall market exposure (long/short/net/gross)

**Algorithm**:
```python
For each position:
    If quantity > 0: total_long += market_value
    If quantity < 0: total_short += abs(market_value)
    Create ExposureItem for MARKET

net_exposure = total_long - total_short
gross_exposure = total_long + total_short
```

**Returns**: ExposureBreakdown with market aggregates

**Testing**:
```python
# Test: Mixed long/short positions
positions = {
    'AAPL': {'quantity': 100, 'market_value': 15000},   # Long
    'MSFT': {'quantity': -50, 'market_value': -7500}    # Short
}
result = await calculator._calculate_market_exposure(positions, 100000)
assert result.long_exposure == 15000
assert result.short_exposure == 7500
assert result.net_exposure == 7500
assert result.gross_exposure == 22500
```

### `_calculate_sector_exposure(positions, portfolio_value)`

**Purpose**: Sector-level exposure breakdown

**Uses**: `self._sector_mappings` (9 hardcoded stocks)

**Algorithm**:
```python
sector_exposures = defaultdict(float)
For each position:
    sector = _sector_mappings.get(symbol, 'Unknown')
    sector_exposures[sector] += market_value

Create ExposureItem for each sector
```

**Sectors** (from mappings):
- Technology: AAPL, MSFT, GOOGL
- Consumer Discretionary: TSLA
- Financials: JPM, BAC
- Energy: XOM
- Healthcare: JNJ
- Consumer Staples: PG

**Testing**:
```python
# Test: Sector aggregation
positions = {
    'AAPL': {'quantity': 100, 'market_value': 15000},
    'MSFT': {'quantity': 50, 'market_value': 10000}
}
result = await calculator._calculate_sector_exposure(positions, 100000)
tech_exposure = [e for e in result.exposures if e.identifier == 'Technology'][0]
assert tech_exposure.value == 25000  # AAPL + MSFT
```

### `_calculate_regional_exposure(positions, portfolio_value)`

**Purpose**: Geographic exposure breakdown

**Uses**: `self._geographic_mappings` (9 hardcoded stocks → "North America")

**Algorithm**: Same as sector, but groups by region

**Testing**:
```python
# Test: Regional aggregation
positions = {'AAPL': {'quantity': 100, 'market_value': 15000}}
result = await calculator._calculate_regional_exposure(positions, 100000)
na_exposure = [e for e in result.exposures if e.identifier == 'North America'][0]
assert na_exposure.value == 15000
```

### `_calculate_currency_exposure(positions, portfolio_value)`

**Purpose**: Currency exposure breakdown

**Uses**: `position.get('currency', 'USD')` for each position

**Algorithm**: Groups positions by currency

**Testing**:
```python
# Test: Multi-currency
positions = {
    'AAPL': {'quantity': 100, 'market_value': 15000, 'currency': 'USD'},
    'ASML': {'quantity': 20, 'market_value': 5000, 'currency': 'EUR'}
}
result = await calculator._calculate_currency_exposure(positions, 100000)
assert len(result.exposures) == 2  # USD and EUR
```

### `_calculate_factor_exposure(positions, portfolio_value)`

**Purpose**: Factor-based exposure (value, growth, momentum, etc.)

**Factors**:
- Value
- Growth
- Momentum
- Quality
- Size
- Volatility

**Algorithm**:
```python
For each position:
    factor_loadings = _get_factor_loadings(symbol)  # Random in current impl
    For each factor:
        factor_exposures[factor] += market_value * loading

Filter factors with abs(value) > 0.01
Create ExposureItem for each significant factor
```

**Testing**:
```python
# Test: Factor exposure calculation
positions = {'AAPL': {'quantity': 100, 'market_value': 15000}}
result = await calculator._calculate_factor_exposure(positions, 100000)
# Note: Loadings are random, so test structure not values
assert all(e.exposure_type == ExposureType.FACTOR for e in result.exposures)
```

### `_calculate_single_name_exposure(positions, portfolio_value)`

**Purpose**: Individual position concentration

**Algorithm**:
```python
For each position:
    Create ExposureItem with symbol as identifier
Sort by absolute value (largest first)
```

**Testing**:
```python
# Test: Single name concentration
positions = {
    'AAPL': {'quantity': 100, 'market_value': 15000},
    'MSFT': {'quantity': 50, 'market_value': 10000}
}
result = await calculator._calculate_single_name_exposure(positions, 100000)
assert len(result.exposures) == 2
assert result.exposures[0].identifier == 'AAPL'  # Sorted by size
assert result.exposures[0].percentage == 15.0    # 15000/100000 * 100
```

---

## 7. Limit Management

### `check_exposure_limits(exposures, portfolio_value)`

**Signature**:
```python
async def check_exposure_limits(
    self,
    exposures: Dict[ExposureType, ExposureBreakdown],
    portfolio_value: float
) -> List[ExposureViolation]:
```

**Purpose**: Check all exposures against configured limits

**Algorithm**:
```python
For each exposure_type and breakdown:
    For each exposure_item:
        limit_key = f"{exposure_type.value}_{identifier}"
        If limit exists:
            violation = _check_single_limit(item, limit, portfolio_value)
            If violation: append to list

Store violations (keep last 24 hours only)
Return violations
```

**Testing**:
```python
# Test: Limit violation detection
calculator.set_exposure_limit(ExposureLimit(
    exposure_type=ExposureType.SINGLE_NAME,
    identifier='AAPL',
    max_exposure=10.0,      # 10%
    warning_threshold=8.0   # 8%
))

positions = {'AAPL': {'quantity': 100, 'market_value': 12000}}
exposures = await calculator.calculate_exposures(positions, 100000)
violations = await calculator.check_exposure_limits(exposures, 100000)

assert len(violations) == 1
assert violations[0].severity == 'CRITICAL'  # 12% > 10%
```

### `_check_single_limit(exposure_item, limit, portfolio_value)`

**Returns**: Optional[ExposureViolation]

**Logic**:
```python
If limit.is_percentage:
    current_level = (exposure_value / portfolio_value) * 100
Else:
    current_level = exposure_value

If current_level > max_exposure:
    Return CRITICAL violation
Elif current_level > warning_threshold:
    Return WARNING violation
Else:
    Return None
```

**Testing**:
```python
# Test 1: Critical violation
item = ExposureItem('AAPL', ExposureType.SINGLE_NAME, 12000, 12.0)
limit = ExposureLimit(ExposureType.SINGLE_NAME, 'AAPL', 10.0, 8.0)
violation = calculator._check_single_limit(item, limit, 100000)
assert violation.severity == 'CRITICAL'

# Test 2: Warning violation
item = ExposureItem('MSFT', ExposureType.SINGLE_NAME, 9000, 9.0)
violation = calculator._check_single_limit(item, limit, 100000)
assert violation.severity == 'WARNING'

# Test 3: No violation
item = ExposureItem('GOOGL', ExposureType.SINGLE_NAME, 5000, 5.0)
violation = calculator._check_single_limit(item, limit, 100000)
assert violation is None
```

### `set_exposure_limit(limit: ExposureLimit)`

**Purpose**: Add/update exposure limit

**Thread-safe**: Uses `self._lock`

**Logs**: f"Set exposure limit: {limit_key} = {max_exposure}"

**Testing**:
```python
limit = ExposureLimit(
    exposure_type=ExposureType.SECTOR,
    identifier='Technology',
    max_exposure=50.0,
    warning_threshold=40.0
)
calculator.set_exposure_limit(limit)

limits = calculator.get_exposure_limits()
assert 'sector_Technology' in limits
```

### `remove_exposure_limit(exposure_type: ExposureType, identifier: str)`

**Purpose**: Remove exposure limit

**Logs**: f"Removed exposure limit: {limit_key}"

**Testing**:
```python
calculator.remove_exposure_limit(ExposureType.SECTOR, 'Technology')
limits = calculator.get_exposure_limits()
assert 'sector_Technology' not in limits
```

### `get_exposure_limits()`

**Returns**: Dict[str, ExposureLimit] (copy)

**Thread-safe**: Uses `self._lock`

### `get_exposure_violations(severity: Optional[str] = None)`

**Returns**: List[ExposureViolation]

**Parameters**:
- `severity`: Optional filter ("WARNING" or "CRITICAL")

**Testing**:
```python
# Test: Filter by severity
violations = calculator.get_exposure_violations(severity='CRITICAL')
assert all(v.severity == 'CRITICAL' for v in violations)
```

---

## 8. Utility Methods

### `_get_factor_loadings(symbol: str)`

**Returns**: Dict[str, float]

**Current Implementation**: Returns random loadings (simplified)

**Production**: Would query risk model database

**Testing**: Test structure, not values (random)

### `_should_include_position(position: Dict[str, Any])`

**Returns**: bool

**Exclusion Rules**:
1. Cash positions (if `include_cash=False`)
2. Derivatives (if `include_derivatives=False`)
3. Zero quantity positions

**Testing**:
```python
# Test 1: Cash exclusion
position = {'asset_type': 'CASH', 'quantity': 1000}
calculator.include_cash = False
assert calculator._should_include_position(position) is False

# Test 2: Derivative exclusion
position = {'asset_type': 'OPTION', 'quantity': 10}
calculator.include_derivatives = False
assert calculator._should_include_position(position) is False

# Test 3: Zero quantity
position = {'quantity': 0}
assert calculator._should_include_position(position) is False
```

### `_load_sector_mappings()`

**Returns**: Dict[str, str]

**Hardcoded Mappings** (9 symbols):
- AAPL, MSFT, GOOGL → Technology
- TSLA → Consumer Discretionary
- JPM, BAC → Financials
- XOM → Energy
- JNJ → Healthcare
- PG → Consumer Staples

### `_load_geographic_mappings()`

**Returns**: Dict[str, str]

**Hardcoded Mappings**: All 9 symbols → "North America"

### `get_calculation_history()`

**Returns**: List[Dict[str, Any]]

**History Record Structure**:
```python
{
    'timestamp': datetime,
    'positions_count': int,
    'portfolio_value': float,
    'exposure_types': List[str],
    'calculation_time': float
}
```

**Max Size**: 1000 records (deque)

**Testing**:
```python
await calculator.calculate_exposures(positions, 100000)
history = calculator.get_calculation_history()
assert len(history) > 0
assert 'timestamp' in history[0]
assert 'calculation_time' in history[0]
```

### `clear_cache()`

**Purpose**: Clear exposure calculation cache

**Logs**: "Exposure calculation cache cleared"

**Testing**:
```python
calculator.clear_cache()
assert len(calculator._exposure_cache) == 0
```

### `cleanup()`

**Signature**:
```python
async def cleanup(self) -> None:
```

**Purpose**: Cleanup resources (currently just logs)

**Logs**: "ExposureCalculator cleanup completed"

---

## 9. Test Categories

### Estimated Test Plan: 30-35 tests across 7 categories

#### Category 1: Enums and Dataclasses (3 tests)
- **test_exposure_type_enum_values**: All 9 values exist
- **test_exposure_direction_enum_values**: All 4 values exist
- **test_dataclass_creation**: ExposureItem, ExposureBreakdown, ExposureLimit, ExposureViolation

#### Category 2: Initialization (3 tests)
- **test_default_initialization**: Default config values
- **test_custom_configuration**: Custom cache_ttl, include_derivatives, include_cash, base_currency
- **test_sector_and_geographic_mappings_loaded**: 9 symbols mapped

#### Category 3: Market Exposure (4 tests)
- **test_market_exposure_long_positions**: Only long positions
- **test_market_exposure_short_positions**: Only short positions
- **test_market_exposure_mixed_positions**: Long and short mix
- **test_market_exposure_empty_positions**: Empty portfolio

#### Category 4: Sector/Region/Currency Exposure (6 tests)
- **test_sector_exposure_single_sector**: All same sector
- **test_sector_exposure_multiple_sectors**: Mixed sectors
- **test_regional_exposure_calculation**: Geographic grouping
- **test_currency_exposure_single_currency**: All USD
- **test_currency_exposure_multiple_currencies**: USD + EUR
- **test_unknown_sector_mapping**: Symbol not in mappings

#### Category 5: Factor and Single Name Exposure (4 tests)
- **test_factor_exposure_calculation**: Factor loading application
- **test_factor_exposure_threshold_filtering**: Filter small exposures
- **test_single_name_exposure_sorted**: Largest first
- **test_single_name_concentration**: Percentage calculations

#### Category 6: Exposure Limits and Violations (7 tests)
- **test_set_and_get_exposure_limit**: Limit management
- **test_remove_exposure_limit**: Limit removal
- **test_check_limits_critical_violation**: Exceeds max_exposure
- **test_check_limits_warning_violation**: Exceeds warning_threshold
- **test_check_limits_no_violation**: Within limits
- **test_percentage_vs_absolute_limits**: Both limit types
- **test_violation_history_cleanup**: 24-hour retention

#### Category 7: Calculate Exposures Integration (4-5 tests)
- **test_calculate_all_exposure_types**: All types at once
- **test_calculate_specific_exposure_types**: Subset of types
- **test_calculation_history_tracking**: History recorded
- **test_unsupported_exposure_types**: CREDIT, DURATION, VOLATILITY warnings
- **test_should_include_position_filters**: Cash, derivatives, zero quantity

---

## 🎯 Coverage Target Calculation

**Current**: 72% (316 statements, 89 missed)  
**Target**: 80%+ (need to cover +25 statements)

**Strategy**:
1. **Core exposure calculations** (market, sector, region, currency, single_name): ~40 statements
2. **Limit checking** (check_exposure_limits, _check_single_limit): ~30 statements
3. **Utility methods** (_should_include_position, mappings): ~15 statements
4. **Initialization and cleanup**: ~10 statements

**Total estimated new coverage**: ~95 statements → 72% + 8% = **80%+** ✅

---

## 📝 Testing Notes

### Mock Strategy
- No external dependencies to mock
- Sector/geographic mappings are hardcoded
- Factor loadings are random (test structure not values)

### Position Data Structure
```python
position = {
    'quantity': int,          # Required
    'market_value': float,    # Required
    'asset_type': str,        # Optional (STOCK, OPTION, FUTURE, SWAP, CASH)
    'currency': str           # Optional (default: USD)
}
```

### Edge Cases to Test
1. Empty positions
2. Zero quantity positions
3. Cash positions with include_cash=False
4. Derivatives with include_derivatives=False
5. Unknown symbols (sector/region mappings)
6. Zero portfolio value (avoid division by zero)
7. Unsupported exposure types (CREDIT, DURATION, VOLATILITY)

### Thread Safety
- All public methods use `self._lock` where needed
- Test concurrent access if time permits

### Calculation History
- Deque with maxlen=1000
- Test FIFO behavior with >1000 calculations if needed

---

## ✅ API Verification Checklist

- [x] All enums documented (ExposureType, ExposureDirection)
- [x] All dataclasses documented (4 total)
- [x] Initialization parameters documented
- [x] All public methods documented (9 methods)
- [x] All private calculation methods documented (6 exposure types)
- [x] Limit management methods documented (5 methods)
- [x] Utility methods documented (5 methods)
- [x] Test categories planned (7 categories, 30-35 tests)
- [x] Coverage strategy documented (72% → 80%+)

---

*Document created for Phase 6 Week 2 Day 7 testing*  
*Target: 80%+ coverage through comprehensive exposure calculation testing*
