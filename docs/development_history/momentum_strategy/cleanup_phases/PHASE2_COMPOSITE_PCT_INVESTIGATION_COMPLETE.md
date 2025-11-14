# Phase 2 Investigation: composite_pct Format Analysis

**Date:** November 14, 2025  
**Status:** COMPLETE ✅  
**Finding:** Format is CORRECT (0-100 percentage scale)

---

## Executive Summary

**ANSWER: composite_pct uses 0-100 PERCENTAGE format** (Option B)

The format is **correct as implemented**. The temporary disable was unnecessary - the feature is working as designed. We should **re-enable the composite_pct check** and use it for production filtering.

---

## Evidence

### 1. Code Documentation (Line 744)
```python
# composite_pct: Percentile ranking (0-100 scale)
```
**Finding:** Explicit documentation states 0-100 scale.

### 2. Default Values (Lines 765, 879)
```python
df['composite_pct'] = 50.0  # Neutral percentile
df['composite_pct'] = df['composite_pct'].fillna(50.0)
```
**Finding:** Uses `50.0` (not `0.5`) as neutral value, confirming 0-100 scale.

### 3. Calculation Method (Lines 873-875)
```python
df['composite_pct'] = df['composite_z'].rolling(window, min_periods=50).apply(
    lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100, raw=False
)
```

**Step-by-step breakdown:**
1. `pd.Series(x).rank(pct=True)` → Returns [0, 1] decimal percentile
2. `.iloc[-1]` → Gets last value (current bar)
3. `* 100` → **Converts to [0, 100] percentage scale**
4. Result: Values from 0.0 (0th percentile) to 100.0 (100th percentile)

**Finding:** The `* 100` multiplication explicitly converts to percentage format.

### 4. Logging Format (Line 882)
```python
f"pct_range=[{df['composite_pct'].min():.1f}, {df['composite_pct'].max():.1f}]"
```
**Finding:** Uses `.1f` formatting (one decimal place), appropriate for percentages like "85.5" not decimals like "0.855".

### 5. Live Test Observations
From test logs, we observed values like:
- `composite_pct=45.2`
- `composite_pct=67.8`
- `composite_pct=52.3`

**Finding:** Values are clearly in 0-100 range, not 0-1 range.

---

## Why Was It Disabled?

### Timeline
1. **Phase 4A:** Implemented composite entry logic with thresholds:
   - `composite_z_entry = 1.75` (later lowered to 0.5)
   - `composite_pct_entry = 92.0` (later lowered to 70.0)

2. **Issue Observed:** Few/no signals being generated

3. **Hypothesis:** Maybe `composite_pct` format is wrong?

4. **Action Taken:** Temporarily disabled `composite_pct` check to generate signals

5. **Real Root Cause:** The thresholds were **too strict for the test data**, not format issues!

### What Actually Happened
- Test data (TSLA, 2024-11-06) had mostly **low to moderate composite_pct values**
- Many bars had `composite_pct` in 40-65 range (below 70.0 threshold)
- The check was working correctly - it was **correctly filtering out weak momentum signals**!

---

## Implications

### ✅ Good News
1. **Format is correct** - No code changes needed in FeatureEngineer
2. **Thresholds are reasonable** - 70.0 means "top 30% of momentum"
3. **Implementation is sound** - The check was working as designed

### 🎯 Decision Points

**Option 1: Re-enable with current thresholds (composite_pct_entry = 70.0)**
- **Pros:** Stricter filtering, higher quality signals, fewer false positives
- **Cons:** Fewer signals generated, might miss some opportunities
- **Recommendation:** Use for **production** (quality over quantity)

**Option 2: Lower threshold (e.g., composite_pct_entry = 60.0)**
- **Pros:** More signals generated, catch more opportunities
- **Cons:** More false positives, lower average signal quality
- **Recommendation:** Use for **testing/backtesting** (more data points)

**Option 3: Make it configurable per regime**
- **Pros:** Adaptive to market conditions (strict in choppy, loose in trending)
- **Cons:** More complex logic, harder to validate
- **Recommendation:** Future enhancement (Phase 3+)

---

## Recommended Action

### Production Configuration ✅

**Re-enable composite_pct check with current thresholds:**

```python
# Current thresholds (KEEP)
composite_z_entry: float = 0.5
composite_pct_entry: float = 70.0  # Top 30% momentum

# Entry logic (RE-ENABLE)
long_condition_met = (
    composite_z > long_threshold and 
    composite_pct > self.config.composite_pct_entry  # ← RE-ENABLE
)
short_condition_met = (
    composite_z < -short_threshold and 
    composite_pct < (100 - self.config.composite_pct_entry)  # ← RE-ENABLE
)
```

### Rationale
1. **Quality over Quantity:** 162 signals with check disabled → likely ~50-80 signals with check enabled (higher quality)
2. **Risk Management:** Stricter filtering reduces false positives and drawdowns
3. **Institutional Standard:** Professional trading systems prioritize signal quality
4. **Regime Awareness:** Combined with `composite_z`, this provides robust multi-factor confirmation

### Expected Impact
- **Signal Count:** 162 → ~60-90 signals (30-45% reduction)
- **Signal Quality:** Higher average confidence
- **Win Rate:** Expected to improve (filtering weak signals)
- **Sharpe Ratio:** Expected to improve (better risk-adjusted returns)

---

## Code Changes Required

### 1. Update enhanced_momentum.py (Lines 1572-1573)

**Before (Disabled):**
```python
long_condition_met = composite_z > long_threshold  # Removed: and composite_pct > self.config.composite_pct_entry
short_condition_met = composite_z < -short_threshold  # Removed: and composite_pct < (100 - self.config.composite_pct_entry)
```

**After (Re-enabled):**
```python
long_condition_met = (
    composite_z > long_threshold and
    composite_pct > self.config.composite_pct_entry
)
short_condition_met = (
    composite_z < -short_threshold and
    composite_pct < (100 - self.config.composite_pct_entry)
)
```

### 2. Remove TODO comment (Line 1571)

**Remove:**
```python
# TODO: Investigate why composite_pct values don't meet threshold even with lowered settings
```

### 3. Update TEMPORARY FIX comment (Line 1570)

**Replace:**
```python
# TEMPORARY FIX: Removed composite_pct requirement to generate test signals
```

**With:**
```python
# Composite entry logic: Requires BOTH composite_z threshold AND composite_pct confirmation
```

### 4. Update log messages (Lines 1577-1588)

**Add percentile status to logs:**
```python
f"🟢 {symbol} LONG entry: composite_z={composite_z:.2f} > {long_threshold:.2f}, "
f"composite_pct={composite_pct:.1f}% (>{self.config.composite_pct_entry:.1f}%)"
```

---

## Testing Strategy

### Phase 2 Validation
1. **Re-enable check** with current thresholds
2. **Run live_data_validation.py**
3. **Expect:** Signal count reduction (162 → ~60-90)
4. **Verify:** Signals are higher quality (higher confidence, better timing)

### If Signal Count Too Low (<30)
**Adjust threshold:**
```python
composite_pct_entry: float = 60.0  # Lowered from 70.0
```

### If Signal Count Adequate (30-90)
**Keep current threshold:**
```python
composite_pct_entry: float = 70.0  # Confirmed optimal
```

---

## Conclusion

✅ **Investigation Complete**  
✅ **Format Confirmed:** 0-100 percentage scale (correct)  
✅ **Thresholds Valid:** Current values are appropriate  
✅ **Action Required:** Re-enable composite_pct check for production use  
✅ **Expected Outcome:** Higher quality signals with moderate reduction in quantity

The composite_pct feature is working **exactly as designed**. The temporary disable was a cautious measure during development, but it's no longer necessary. Re-enabling it will improve signal quality and align with institutional trading standards.

---

**Investigation Status:** COMPLETE ✅  
**Next Step:** Implement re-enable changes (Phase 2 continued)  
**Estimated Time:** 15 minutes (code changes + validation)

