# Phase 4B: Type 2 Explicit Regime Awareness Implementation

**Date:** 2025-11-13  
**Status:** ✅ IMPLEMENTED (with limitation noted)  
**Enhancement:** Added regime-adjusted entry thresholds to EnhancedMomentumStrategy

---

## Overview

Implemented **Type 2 (Explicit) Regime Awareness** for entry logic, where thresholds adapt based on current market regime to implement asymmetric risk management.

### Type 1 vs Type 2 Regime Awareness

| Type | Description | Implementation Status |
|------|-------------|----------------------|
| **Type 1: Implicit (Inherited)** | Base indicators adapt calculation parameters to regime | ✅ Already implemented in `EnhancedTechnicalIndicators` |
| **Type 2: Explicit (Direct)** | Entry/exit logic adapts thresholds/weights to regime | ✅ **NEW - Implemented in Phase 4B** |

---

## Implementation Details

### 1. New Method: `_get_regime_adjusted_thresholds()`

**File:** `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py`  
**Lines:** 1421-1500

```python
def _get_regime_adjusted_thresholds(
    self,
    current_bar: pd.Series
) -> Dict[str, float]:
    """
    Get regime-adjusted entry thresholds (Type 2 Explicit Regime Awareness)
    
    Threshold Philosophy:
    - Base thresholds: ±1.75 composite_z (Phase 4A baseline)
    - Bear regimes: Easier SHORT (0.75×), Harder LONG (1.5×)
    - Bull regimes: Easier LONG (0.75×), Harder SHORT (1.5×)
    - High volatility: Stricter on both sides (1.2×)
    """
```

### 2. Regime-Based Adjustments

#### Bear Regimes (Favor SHORT, skeptical of LONG)
- **Regimes:** `bear_market`, `bear_high_volatility`, `bear_low_volatility`
- **LONG threshold:** `1.75 × 1.5 = 2.625` (50% harder to go long)
- **SHORT threshold:** `1.75 × 0.75 = 1.3125` (25% easier to go short)
- **Rationale:** Avoid catching falling knives, favor trend

#### Bull Regimes (Favor LONG, skeptical of SHORT)
- **Regimes:** `bull_market`, `bull_high_volatility`, `bull_low_volatility`
- **LONG threshold:** `1.75 × 0.75 = 1.3125` (25% easier to go long)
- **SHORT threshold:** `1.75 × 1.5 = 2.625` (50% harder to go short)
- **Rationale:** Avoid fighting the trend, favor momentum

#### Sideways Regimes (Neutral but cautious)
- **Regimes:** `sideways`, `choppy`, `range_bound`
- **Both thresholds:** `1.75 × 1.1 = 1.925` (10% stricter)
- **Rationale:** Avoid whipsaws in range-bound markets

#### Normal/Trending Regimes (Standard)
- **Both thresholds:** `1.75` (unchanged)
- **Rationale:** Standard momentum strategy behavior

### 3. Volatility Overlay Adjustments

Applied on top of primary regime adjustments:

#### High Volatility
- **Regimes:** `high_volatility`, `extreme_volatility`
- **Both thresholds:** `× 1.2` (20% stricter)
- **Rationale:** Avoid noise and false breakouts

#### Low Volatility
- **Regimes:** `low_volatility`, `very_low_volatility`
- **Both thresholds:** `× 0.9` (10% more lenient)
- **Rationale:** Less noise, clearer signals

### 4. Example Threshold Calculations

```
Bear Market + High Volatility:
  LONG: 1.75 × 1.5 × 1.2 = 3.15 (very hard to go long)
  SHORT: 1.75 × 0.75 × 1.2 = 1.575 (easier to go short)

Bull Market + Low Volatility:
  LONG: 1.75 × 0.75 × 0.9 = 1.18125 (easy to go long)
  SHORT: 1.75 × 1.5 × 0.9 = 2.3625 (hard to go short)

Sideways + Normal Volatility:
  LONG: 1.75 × 1.1 = 1.925 (slightly stricter)
  SHORT: 1.75 × 1.1 = 1.925 (slightly stricter)
```

---

## Modified Methods

### Enhanced `_check_composite_entry()`

**File:** `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py`  
**Lines:** 1506-1577

**Key Changes:**
1. Calls `_get_regime_adjusted_thresholds()` to get adaptive thresholds
2. Uses `long_threshold` and `short_threshold` instead of fixed `self.config.composite_z_entry`
3. Logs the regime adjustment reason for transparency

```python
# Phase 4B: Get regime-adjusted thresholds
thresholds = self._get_regime_adjusted_thresholds(current_bar)
long_threshold = thresholds['long_threshold']
short_threshold = thresholds['short_threshold']
adjustment_reason = thresholds['adjustment_reason']

# LONG entry: Strong upward momentum (regime-adjusted threshold)
if (composite_z > long_threshold and
    composite_pct > self.config.composite_pct_entry):
    logger.info(
        f"🟢 {symbol} LONG entry: composite_z={composite_z:.2f} > {long_threshold:.2f} "
        f"(regime-adjusted from {self.config.composite_z_entry:.2f}, reason: {adjustment_reason})"
    )
    return True, SignalType.BUY
```

---

## Current Limitation (Known Issue)

### Regime Data Not in Enriched Bars ⚠️

**Issue:** The `current_bar` doesn't contain regime information (`primary_regime`, `volatility_regime`)

**Root Cause:** The `ProcessingPipelineOrchestrator` processes data through:
1. Data Loading → Indicators → Features → Signals
2. But **regime information is calculated separately** and not merged into bar data

**Current Behavior:**
```python
# In _get_regime_adjusted_thresholds():
primary_regime = current_bar.get('primary_regime', 'normal_volatility')
# ↑ This defaults to 'normal_volatility' because regime columns don't exist!
```

**Impact:**
- The code runs without errors (graceful fallback to default)
- But **ALL entries use 'normal_volatility' thresholds** (standard 1.75)
- **No actual regime adaptation is happening yet** ⚠️

---

## Solution Required (Future Phase 4C)

### Option 1: Add Regime Columns to Enriched Data
**Modify `ProcessingPipelineOrchestrator` to:**
1. Calculate regimes for each bar timestamp
2. Add `primary_regime` and `volatility_regime` columns to enriched DataFrame
3. These columns then flow naturally to the strategy

**Implementation:**
```python
# In ProcessingPipelineOrchestrator.process_market_data():
enriched_df = signals_df.copy()

# Add regime information to each bar
for timestamp in enriched_df.index:
    regime = regime_engine.get_regime_at_timestamp(symbol, timestamp)
    if regime:
        enriched_df.loc[timestamp, 'primary_regime'] = regime.primary_regime.value
        enriched_df.loc[timestamp, 'volatility_regime'] = regime.volatility_regime.value
```

### Option 2: Pass Regime Engine Reference to Strategy
**Allow strategy to query regime directly:**
```python
# In _check_composite_entry():
regime = self.regime_engine.get_regime_at_timestamp(symbol, current_bar.name)
if regime:
    primary_regime = regime.primary_regime.value
    volatility_regime = regime.volatility_regime.value
```

**Recommendation:** Option 1 is cleaner (regime becomes part of data pipeline)

---

## Testing Status

### Test Environment
- **Data:** TSLA 2024-12-20 (391 bars, 1-minute frequency)
- **Test File:** `tests/integration/live_data_validation.py`

### Test Results

```
Regime Distribution:
  range_bound: 260 bars (78.3%)
  choppy: 48 bars (14.5%)
  bull_high_volatility: 16 bars (4.8%)
  bear_high_volatility: 8 bars (2.4%)

Strategy Signals Generated: 0
```

**Analysis:**
1. ✅ Code executes without errors
2. ⚠️ Regime columns not in enriched data → defaults to 'normal_volatility'
3. ⚠️ No actual regime adaptation occurring (but infrastructure is ready)
4. ⚠️ 0 signals due to strict thresholds + uniformly negative composite_z

---

## Benefits of Type 2 Regime Awareness

### 1. Asymmetric Risk Management
- Don't fight the trend (harder SHORT in bull, harder LONG in bear)
- Avoid catching falling knives (much harder LONG in bear regimes)
- Ride momentum (easier LONG in bull, easier SHORT in bear)

### 2. Volatility Adaptation
- Stricter in high volatility → fewer false breakouts
- More lenient in low volatility → capture cleaner signals

### 3. Whipsaw Avoidance
- Stricter thresholds in choppy/sideways markets
- Reduces noise trading in range-bound conditions

### 4. Dynamic Risk-Reward
- Thresholds adjust to market conditions
- Better risk-adjusted returns over full market cycle

---

## Code Quality

### Compliance
- ✅ Follows Rule 2 (Regime-First Principle)
- ✅ Uses centralized config (`self.config.composite_z_entry`)
- ✅ Comprehensive logging with regime adjustment reasons
- ✅ Graceful fallback to defaults if regime data unavailable

### Documentation
- ✅ Detailed docstrings explaining threshold philosophy
- ✅ Clear rationale for each regime adjustment multiplier
- ✅ Example calculations provided

### Testing
- ⚠️ Infrastructure tested (no errors)
- ⚠️ Actual regime adaptation not yet tested (awaiting Phase 4C)

---

## Next Steps

### Phase 4C: Enable Regime Data in Pipeline (HIGH PRIORITY)
1. Modify `ProcessingPipelineOrchestrator` to add regime columns
2. Verify regime columns appear in enriched data
3. Re-test to confirm regime-adjusted thresholds are applied
4. Verify different signals in different regimes

### Phase 4D: Advanced Enhancements (MEDIUM PRIORITY)
1. Add regime-aware signal weights (not just thresholds)
2. Consider regime transition detection (avoid entries during transitions)
3. Add regime confidence weighting (stricter if regime confidence is low)

---

## Summary

✅ **Type 2 Explicit Regime Awareness implemented**  
⚠️ **Awaiting regime data integration to activate** (Phase 4C)  
✅ **Infrastructure ready for immediate activation** once data flows correctly  

**Key Achievement:** Entry logic now has the **capability** for regime-aware threshold adjustment, implementing institutional-grade asymmetric risk management.

**Remaining Work:** Connect regime data to strategy execution (data pipeline enhancement).

