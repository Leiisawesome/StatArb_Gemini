# Backtest Engine Fallback Mechanisms Audit

**Date:** November 25, 2025  
**Auditor:** StatArb_Gemini System Architect  
**Status:** 🔴 CRITICAL COMPLIANCE ISSUES FOUND

---

## Executive Summary

**Finding:** Multiple fallback mechanisms identified in backtest engines that violate the fundamental principle of backtesting: **"Backtest should fail cleanly, not silently degrade."**

**Risk Level:** 🔴 **CRITICAL** - Silent fallbacks can produce misleading backtest results  
**Recommendation:** Remove ALL fallback mechanisms and replace with explicit error handling

---

## Audit Scope

### Files Audited
1. `/backtest/engine/historical_execution_simulator.py` (912 lines)
2. `/backtest/engine/institutional_backtest_engine.py` (3889 lines)
3. `/backtest/engine/vectorized_engine.py` (not fully reviewed)
4. `/backtest/engine/strategy_optimizer.py` (not fully reviewed)

### Audit Criteria
- ❌ Fallback to default values
- ❌ Silent exception handling with fallback
- ❌ `.get()` with default values for critical data
- ❌ Conditional fallback logic
- ❌ "Graceful degradation" patterns

---

## 🔴 CRITICAL FINDINGS

### Finding #1: Exception Handling with Fallback Fill
**File:** `historical_execution_simulator.py`  
**Lines:** 350-356  
**Severity:** 🔴 CRITICAL

```python
# CURRENT CODE (VIOLATES PRINCIPLE)
except Exception as e:
    logger.error(f"Error simulating fill for {symbol}: {e}", exc_info=True)
    # Return fallback fill with conservative costs
    return self._create_fallback_fill(
        symbol, side, quantity, decision_price, market_data,
        authorization_id, strategy_id
    )
```

**Issue:**
- Silently catches ALL exceptions and returns a "fallback fill" with conservative costs
- Masks real errors in execution simulation
- Produces unrealistic backtest results (20 bps "fallback" cost vs actual calculated cost)
- User never knows the real simulation failed

**Impact:**
- Backtest appears successful but uses wrong execution costs
- Performance metrics are invalid
- Production deployment based on this backtest will fail unexpectedly

**Recommendation:**
```python
# CORRECT CODE (FAIL CLEANLY)
except Exception as e:
    logger.error(f"❌ BACKTEST FAILED: Error simulating fill for {symbol}: {e}", exc_info=True)
    raise BacktestExecutionError(
        f"Execution simulation failed for {symbol} {side} {quantity}. "
        f"Cannot continue backtest with invalid data. Error: {str(e)}"
    ) from e
```

---

### Finding #2: Asset Class Fallback
**File:** `historical_execution_simulator.py`  
**Lines:** 266-273  
**Severity:** 🟠 HIGH

```python
# CURRENT CODE (VIOLATES PRINCIPLE)
try:
    from core_engine.data.market_calendar import MarketCalendar
    calendar = MarketCalendar()
    asset_class = calendar.get_asset_class(symbol)
    asset_class_name = asset_class.name
except ImportError:
    asset_class_name = 'US_EQUITY'  # Fallback
```

**Issue:**
- Falls back to 'US_EQUITY' if market calendar import fails
- Wrong asset class means wrong commission model (crypto uses % vs equity uses $/share)
- Silent failure means wrong costs applied

**Impact:**
- Crypto backtest might use equity commission model (drastically underestimating costs)
- Equity-only backtests might "work" but hide missing dependency

**Recommendation:**
```python
# CORRECT CODE (FAIL CLEANLY)
try:
    from core_engine.data.market_calendar import MarketCalendar
    calendar = MarketCalendar()
    asset_class = calendar.get_asset_class(symbol)
    asset_class_name = asset_class.name
except ImportError as e:
    raise BacktestConfigurationError(
        f"❌ BACKTEST FAILED: MarketCalendar not available. "
        f"Cannot determine asset class for {symbol}. This is REQUIRED for correct commission calculation."
    ) from e
except Exception as e:
    raise BacktestDataError(
        f"❌ BACKTEST FAILED: Cannot determine asset class for {symbol}. "
        f"Asset class is REQUIRED for commission calculation. Error: {str(e)}"
    ) from e
```

---

### Finding #3: Strategy Generation Fallback Chain
**File:** `institutional_backtest_engine.py`  
**Lines:** 3096-3174  
**Severity:** 🔴 CRITICAL

```python
# CURRENT CODE (VIOLATES PRINCIPLE)
# Fallback to pipeline signal generator only if enriched data fails
try:
    # Try strategy manager first
    ...
except Exception as e:
    # Fallback to on-the-fly calculation if pre-calculated data not available
    try:
        # Fallback: create enriched data on-the-fly
        ...
    except Exception as e:
        logger.error(f"Fallback strategy generation failed: {e}", exc_info=True)
        # Final fallback to pipeline signal generator only as last resort
        ...
```

**Issue:**
- Three-level fallback chain silently degrades strategy generation
- If strategy manager fails, falls back to on-the-fly enrichment
- If that fails, falls back to pipeline signal generator only
- User never knows which code path executed
- Different code paths produce different signals = invalid backtest

**Impact:**
- Backtest can succeed while using completely different strategy logic than intended
- Results are meaningless because signal generation method is unknown
- Cannot reproduce results in production

**Recommendation:**
```python
# CORRECT CODE (FAIL CLEANLY)
try:
    # ONLY try the configured strategy generation method
    if self.strategy_manager:
        signals_df = await self._generate_strategy_signals(...)
    else:
        raise BacktestConfigurationError(
            "❌ BACKTEST FAILED: StrategyManager not initialized but required for backtest. "
            "Cannot generate signals without properly configured strategies."
        )
except Exception as e:
    logger.error(f"❌ BACKTEST FAILED: Strategy signal generation failed: {e}", exc_info=True)
    raise BacktestExecutionError(
        f"Strategy signal generation failed at bar {self.current_bar_index}. "
        f"Cannot continue backtest with invalid signals. Error: {str(e)}"
    ) from e

# NO FALLBACKS - if it fails, the backtest fails
```

---

### Finding #4: Price Fallback for Position Sizing
**File:** `institutional_backtest_engine.py`  
**Lines:** 3207-3208  
**Severity:** 🟠 HIGH

```python
# CURRENT CODE (VIOLATES PRINCIPLE)
# Fallback: use the most recent available price
current_price = current_bar.get('close', most_recent_price)
```

**Issue:**
- If current bar has no 'close' price, uses "most recent" price
- Position sizing calculated with wrong price = wrong quantity
- Silent substitution of stale data

**Impact:**
- Wrong position sizes executed in backtest
- Real production system would reject trade (no current price available)
- Backtest shows successful trades that wouldn't execute in production

**Recommendation:**
```python
# CORRECT CODE (FAIL CLEANLY)
current_price = current_bar.get('close', None)
if current_price is None or current_price <= 0:
    raise BacktestDataError(
        f"❌ BACKTEST FAILED: No valid 'close' price available for {symbol} at bar {self.current_bar_index}. "
        f"Cannot calculate position size without current price. Bar data: {current_bar}"
    )
```

---

### Finding #5: Fallback Position Sizing Parameters
**File:** `institutional_backtest_engine.py`  
**Lines:** 3331-3350  
**Severity:** 🟡 MEDIUM

```python
# CURRENT CODE (VIOLATES PRINCIPLE)
# Fallback: Use strategy config or global max_position_size
base_position_pct = signal_row.get('target_weight', None)
if base_position_pct is None:
    strategy_params = self.config.strategies[0].get('parameters', {})
    base_position_pct = strategy_params.get('base_position_pct', None)
    if base_position_pct is None:
        # Fallback to strategy-level max_position_size
        position_size_pct = self.config.strategies[0].get('max_position_size', self.config.max_position_size)
```

**Issue:**
- Multi-level fallback chain for position sizing
- If signal has no target_weight, tries strategy params
- If strategy params missing, uses max_position_size
- If that's missing, uses global max_position_size
- Final size might be completely different from intended

**Impact:**
- Position sizes in backtest don't match strategy design
- Can't reproduce backtest because actual sizing logic is unknown

**Recommendation:**
```python
# CORRECT CODE (FAIL CLEANLY)
# Position sizing MUST be explicit in signal
base_position_pct = signal_row.get('target_weight', None)
if base_position_pct is None:
    raise BacktestConfigurationError(
        f"❌ BACKTEST FAILED: Signal for {symbol} missing 'target_weight'. "
        f"Position sizing MUST be explicit in backtest. Signal: {signal_row}"
    )

# Validate position size is reasonable
if not (0.0 < base_position_pct <= 1.0):
    raise BacktestDataError(
        f"❌ BACKTEST FAILED: Invalid target_weight {base_position_pct} for {symbol}. "
        f"Must be between 0.0 and 1.0. Signal: {signal_row}"
    )
```

---

### Finding #6: Market Data .get() with Defaults
**File:** `institutional_backtest_engine.py`  
**Lines:** 3467, 3487-3506  
**Severity:** 🟠 HIGH

```python
# CURRENT CODE (VIOLATES PRINCIPLE)
current_price = auth_trade.get('current_price', current_bar.get('close', 0))
...
'volatility': current_bar.get('volatility', 0.02)  # 2% default
'volume': current_bar.get('volume', 0)
```

**Issue:**
- If market data fields are missing, uses default values
- Execution simulation with fabricated data (e.g., 2% volatility assumption)
- Volume=0 default would cause division errors or infinite participation rate

**Impact:**
- Execution costs calculated with wrong market data
- Backtest shows realistic costs but based on fabricated volatility/volume
- Production system wouldn't have these defaults

**Recommendation:**
```python
# CORRECT CODE (FAIL CLEANLY)
# CRITICAL: All market data MUST be present for execution simulation
required_fields = ['close', 'volume', 'volatility', 'high', 'low']
missing_fields = [f for f in required_fields if f not in current_bar or current_bar[f] is None]
if missing_fields:
    raise BacktestDataError(
        f"❌ BACKTEST FAILED: Missing required market data for {symbol} at bar {self.current_bar_index}. "
        f"Missing fields: {missing_fields}. Cannot simulate execution without complete market data. "
        f"Available data: {list(current_bar.keys())}"
    )

# Now safe to access without defaults
current_price = current_bar['close']
volatility = current_bar['volatility']
volume = current_bar['volume']
```

---

### Finding #7: Regime Context Fallbacks
**File:** `institutional_backtest_engine.py`  
**Lines:** 327-329, 375-382, 3476  
**Severity:** 🟡 MEDIUM

```python
# CURRENT CODE (VIOLATES PRINCIPLE)
primary_regime = new_regime_context.get('primary_regime', 'unknown')
confidence = new_regime_context.get('confidence', 0.0)
volatility_regime = regime_context.get('volatility_regime', 'normal_volatility')
```

**Issue:**
- Falls back to 'unknown', 0.0, or 'normal_volatility' if regime detection fails
- Regime-aware strategies will use wrong regime assumptions
- Risk multipliers based on wrong regime

**Impact:**
- Strategy selection based on wrong regime
- Risk limits based on wrong regime
- Backtest shows strategy working in all regimes but using fabricated regime data

**Recommendation:**
```python
# CORRECT CODE (FAIL CLEANLY)
if 'primary_regime' not in new_regime_context:
    raise BacktestDataError(
        f"❌ BACKTEST FAILED: Regime detection failed - no 'primary_regime' in context. "
        f"Regime-First architecture requires valid regime at all times. "
        f"Context: {new_regime_context}"
    )

primary_regime = new_regime_context['primary_regime']
confidence = new_regime_context.get('confidence', None)
if confidence is None or confidence < 0.5:
    raise BacktestDataError(
        f"❌ BACKTEST FAILED: Regime confidence too low ({confidence}). "
        f"Cannot run backtest with unreliable regime detection. Minimum confidence: 0.5"
    )
```

---

## 🟡 MEDIUM-PRIORITY FINDINGS

### Finding #8: Signal Field .get() with Defaults
**File:** `institutional_backtest_engine.py`  
**Lines:** 3284-3291  
**Severity:** 🟡 MEDIUM

```python
symbol = signal_row.get('symbol', self.config.symbols[0])
signal_type = signal_row.get('signal', 'HOLD')
confidence = signal_row.get('confidence', 0.5)
```

**Recommendation:** Require explicit fields in signals, fail if missing

---

### Finding #9: Rejection Statistics .get() with Defaults
**File:** `institutional_backtest_engine.py`  
**Lines:** 2596-2598, 3561  
**Severity:** 🟢 LOW (acceptable for statistics)

```python
retry_stats[retry_count] = retry_stats.get(retry_count, 0) + 1
```

**Note:** This is acceptable - statistics can use defaults for counters

---

## Summary Statistics

| Category | Count | Severity Distribution |
|----------|-------|----------------------|
| **Total Issues Found** | 9 | 🔴 Critical: 3, 🟠 High: 3, 🟡 Medium: 3 |
| **Must Fix** | 6 | Critical + High severity |
| **Should Fix** | 3 | Medium severity |
| **Acceptable** | 1 | Low severity (statistics) |

---

## 🎯 REMEDIATION PLAN

### Phase 1: Critical Fixes (IMMEDIATE)
**Estimated Time:** 4-6 hours

1. **Remove `_create_fallback_fill()` method entirely**
   - Replace with explicit exception propagation
   - Add custom exceptions: `BacktestExecutionError`, `BacktestDataError`, `BacktestConfigurationError`

2. **Remove asset class fallback**
   - Make MarketCalendar import mandatory
   - Fail explicitly if asset class cannot be determined

3. **Remove strategy generation fallback chain**
   - Single code path for signal generation
   - Fail if strategy manager not initialized properly

4. **Remove price fallback in position sizing**
   - Require valid current price for all trades
   - Fail if price data is incomplete

### Phase 2: High-Priority Fixes (WITHIN 24 HOURS)
**Estimated Time:** 3-4 hours

5. **Remove market data .get() defaults**
   - Validate all required fields present before execution simulation
   - Fail with descriptive error listing missing fields

6. **Remove position sizing fallback chain**
   - Require explicit target_weight in all signals
   - No multi-level fallback logic

### Phase 3: Medium-Priority Fixes (WITHIN 1 WEEK)
**Estimated Time:** 2-3 hours

7. **Remove regime context fallbacks**
   - Require valid regime at all times (Rule 2 - Regime-First)
   - Fail if regime confidence too low

8. **Remove signal field .get() defaults**
   - Require explicit signal fields
   - Validate signal structure before processing

---

## 🛠️ IMPLEMENTATION STRATEGY

### Step 1: Create Custom Exception Classes

```python
# File: backtest/exceptions.py

class BacktestError(Exception):
    """Base exception for all backtest errors"""
    pass

class BacktestDataError(BacktestError):
    """Raised when market data is missing, invalid, or incomplete"""
    pass

class BacktestConfigurationError(BacktestError):
    """Raised when backtest configuration is invalid"""
    pass

class BacktestExecutionError(BacktestError):
    """Raised when backtest execution fails"""
    pass

class BacktestValidationError(BacktestError):
    """Raised when backtest validation fails"""
    pass
```

### Step 2: Add Validation Helper Methods

```python
# File: backtest/utils/validation.py

def validate_market_data(bar: Dict[str, Any], symbol: str, bar_index: int) -> None:
    """
    Validate that market data bar contains all required fields
    
    Raises:
        BacktestDataError: If any required field is missing or invalid
    """
    required_fields = {
        'close': (float, lambda x: x > 0),
        'volume': (float, lambda x: x >= 0),
        'volatility': (float, lambda x: 0 < x < 1),
        'high': (float, lambda x: x > 0),
        'low': (float, lambda x: x > 0),
        'timestamp': (datetime, lambda x: True)
    }
    
    errors = []
    for field, (expected_type, validator) in required_fields.items():
        if field not in bar:
            errors.append(f"Missing field '{field}'")
        elif bar[field] is None:
            errors.append(f"Field '{field}' is None")
        elif not isinstance(bar[field], expected_type):
            errors.append(f"Field '{field}' has wrong type (expected {expected_type.__name__})")
        elif not validator(bar[field]):
            errors.append(f"Field '{field}' failed validation (value: {bar[field]})")
    
    if errors:
        raise BacktestDataError(
            f"❌ BACKTEST FAILED: Invalid market data for {symbol} at bar {bar_index}\n"
            f"Errors:\n" + "\n".join(f"  - {e}" for e in errors) + "\n"
            f"Available fields: {list(bar.keys())}"
        )

def validate_signal(signal: Dict[str, Any], bar_index: int) -> None:
    """
    Validate that signal contains all required fields
    
    Raises:
        BacktestValidationError: If signal is invalid
    """
    required_fields = {
        'symbol': str,
        'signal': str,
        'confidence': float,
        'target_weight': float
    }
    
    errors = []
    for field, expected_type in required_fields.items():
        if field not in signal:
            errors.append(f"Missing field '{field}'")
        elif signal[field] is None:
            errors.append(f"Field '{field}' is None")
        elif not isinstance(signal[field], expected_type):
            errors.append(f"Field '{field}' has wrong type (expected {expected_type.__name__})")
    
    # Additional validations
    if 'confidence' in signal and not (0.0 <= signal['confidence'] <= 1.0):
        errors.append(f"confidence must be in [0, 1], got {signal['confidence']}")
    
    if 'target_weight' in signal and not (0.0 <= signal['target_weight'] <= 1.0):
        errors.append(f"target_weight must be in [0, 1], got {signal['target_weight']}")
    
    if errors:
        raise BacktestValidationError(
            f"❌ BACKTEST FAILED: Invalid signal at bar {bar_index}\n"
            f"Errors:\n" + "\n".join(f"  - {e}" for e in errors) + "\n"
            f"Signal: {signal}"
        )
```

### Step 3: Replace Fallback Patterns with Validation

**BEFORE:**
```python
current_price = current_bar.get('close', 0)
volatility = current_bar.get('volatility', 0.02)
```

**AFTER:**
```python
from backtest.utils.validation import validate_market_data

# Validate BEFORE accessing
validate_market_data(current_bar, symbol, self.current_bar_index)

# Now safe to access directly
current_price = current_bar['close']
volatility = current_bar['volatility']
```

---

## 📋 TESTING STRATEGY

### Test 1: Missing Data Test
```python
def test_backtest_fails_on_missing_price_data():
    """Backtest should FAIL if price data is incomplete"""
    
    # Create data with missing 'close' field
    incomplete_data = pd.DataFrame({
        'timestamp': [datetime.now()],
        'volume': [1000000],
        # 'close' is MISSING
    })
    
    engine = InstitutionalBacktestEngine(config)
    
    # Backtest MUST fail, not silently continue
    with pytest.raises(BacktestDataError, match="Missing field 'close'"):
        await engine.run_backtest()
```

### Test 2: Invalid Regime Test
```python
def test_backtest_fails_on_invalid_regime():
    """Backtest should FAIL if regime detection fails"""
    
    # Mock regime engine to return invalid regime
    mock_regime = {'primary_regime': None, 'confidence': 0.2}
    
    engine = InstitutionalBacktestEngine(config)
    engine.regime_engine.get_current_regime = lambda: mock_regime
    
    # Backtest MUST fail
    with pytest.raises(BacktestDataError, match="Regime confidence too low"):
        await engine.run_backtest()
```

### Test 3: Strategy Generation Failure Test
```python
def test_backtest_fails_on_strategy_generation_error():
    """Backtest should FAIL if strategy signal generation fails"""
    
    # Mock strategy manager to raise exception
    def failing_generate():
        raise RuntimeError("Strategy calculation error")
    
    engine = InstitutionalBacktestEngine(config)
    engine.strategy_manager.generate_signals = failing_generate
    
    # Backtest MUST fail, not fall back to alternative method
    with pytest.raises(BacktestExecutionError, match="Strategy signal generation failed"):
        await engine.run_backtest()
```

---

## 💡 DESIGN PRINCIPLES FOR BACKTESTING

### Principle 1: Fail Fast, Fail Loudly
- **Never** silently continue with degraded data
- **Always** propagate exceptions to the top level
- **Provide** detailed error messages with context

### Principle 2: No Fabricated Data
- **Never** use default values for missing market data
- **Never** substitute stale data for current data
- **Always** require complete, valid data at every bar

### Principle 3: Single Code Path
- **Never** have multiple fallback paths for the same operation
- **Always** use one explicit, well-defined algorithm
- **Fail** if prerequisites for that algorithm are not met

### Principle 4: Explicit Over Implicit
- **Never** infer missing configuration from context
- **Always** require explicit parameters
- **Fail** if required configuration is missing

### Principle 5: Production Parity
- **Backtest** should fail in the same ways production would fail
- **Never** make backtests more "robust" than production
- **Expose** all failure modes during backtesting, not production

---

## ✅ ACCEPTANCE CRITERIA

The remediation is COMPLETE when:

1. ✅ Zero `_create_fallback_*()` methods exist
2. ✅ Zero `except Exception: return fallback` patterns
3. ✅ Zero `.get(field, default)` for critical data fields
4. ✅ All required data validated BEFORE use
5. ✅ All tests pass with explicit failure on missing data
6. ✅ Code review confirms no silent degradation paths
7. ✅ Documentation updated with "fail-fast" philosophy

---

## 📚 REFERENCES

### Industry Standards
- **"Fooled by Randomness"** (Taleb) - Silent failures produce misleading confidence
- **"Evidence-Based Technical Analysis"** (Aronson) - Backtesting pitfalls
- **CFA Institute**: Backtesting standards require data integrity

### Internal Documents
- Rule 3: Unified Data Flow Pipeline (requires valid data)
- Rule 4: Risk Governance (authorization must use real market data)
- Rule 7: Execution Management (execution simulation requires complete market data)

---

## 🚨 RISK ASSESSMENT

### Current State Risk: 🔴 **CRITICAL**

**Likelihood of Impact:** HIGH (80-90%)
- Fallbacks are actively used in normal execution
- Missing data is common in historical datasets
- Multiple silent failure paths exist

**Business Impact:** CRITICAL
- Backtest results are unreliable
- Strategy performance is overstated (optimistic costs)
- Production deployment risk is hidden
- Regulatory compliance issues (if reporting backtest results)

### Post-Remediation Risk: 🟢 **LOW**

**Likelihood of Impact:** LOW (5-10%)
- Explicit validation catches all data issues
- No silent failures possible
- All errors are logged and reported

**Business Impact:** LOW
- Early detection of data issues
- Reliable backtest results
- High confidence in production deployment

---

## 🔄 CHANGE LOG

| Date | Version | Change Description |
|------|---------|-------------------|
| 2025-11-25 | 1.0 | Initial audit completed - 9 findings identified |
| TBD | 2.0 | Phase 1 critical fixes completed |
| TBD | 3.0 | Phase 2 high-priority fixes completed |
| TBD | 4.0 | Phase 3 medium-priority fixes completed |
| TBD | 5.0 | All acceptance criteria met - audit closed |

---

**END OF AUDIT REPORT**

