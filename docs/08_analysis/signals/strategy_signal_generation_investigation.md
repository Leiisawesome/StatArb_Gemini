# Strategy Signal Generation Investigation: 0 Signals Issue

## Problem Statement
The integration test shows 0 strategy signals generated despite the pipeline processing data successfully and preliminary signals being generated (26 signals from Phase 5).

## Root Cause Analysis

### 1. **Rolling Window Chronological Processing**

The test processes data chronologically using rolling windows:
- **Rolling window size:** 200 bars
- **Warmup period:** 50 bars  
- **Processing mode:** Bar-by-bar from bar 50 to end

**Key Code:**
```python
# Line 676-691: Rolling window creation
for bar_idx in range(warmup_period, len(full_dataframe)):
    window_start = max(0, bar_idx - rolling_window_size + 1)
    window_end = bar_idx + 1
    data_rolling_window = full_dataframe.iloc[window_start:window_end].copy()
    
    bar_enriched_data = {'TSLA': data_rolling_window}
    strategy_signals = await strategy_instance.generate_signals(bar_enriched_data)
```

### 2. **Strategy Processing Logic**

**Momentum Strategy (enhanced_momentum.py):**

1. **Data Length Check (Line 386):**
   ```python
   if symbol in self.market_data and len(self.market_data[symbol]) > self.config.long_period:
   ```
   - Requires data length > `long_period` (50 bars)
   - Rolling window of 200 bars should satisfy this ✅

2. **Scan Mode (Line 755):**
   ```python
   if self.config.scan_all_bars and data_length > self.config.long_period:
       # Historical scanning mode
   else:
       # Live mode: Evaluate only current bar (iloc[-1])
   ```
   - Test config: `scan_all_bars: False` (Line 485)
   - **Result:** Strategy only evaluates `iloc[-1]` (last bar in rolling window)

3. **Momentum Value Extraction (Lines 992-1013):**
   ```python
   short_momentum_col = f'momentum_{self.config.short_period}'  # momentum_10
   short_momentum_series = data[short_momentum_col].dropna()
   short_momentum = short_momentum_series.iloc[-1] if len(short_momentum_series) > 0 else 0.0
   ```
   - **Issue:** If ALL momentum values in the window are NaN, `dropna()` returns empty series
   - **Fallback:** Returns 0.0, which likely doesn't meet momentum thresholds

### 3. **Momentum Feature Creation (FeatureEngineer)**

**File:** `core_engine/processing/features/engineer.py`, Line 637-643

```python
def _create_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
    for period in [10, 20, 50]:
        if len(df) > period:
            df[f'momentum_{period}'] = df['close'].pct_change(period)
```

**Key Issue:**
- `pct_change(period)` creates NaN for the first `period` bars
- `momentum_10`: NaN for first 10 bars
- `momentum_20`: NaN for first 20 bars  
- `momentum_50`: NaN for first 50 bars

**In Rolling Window Context:**
- Window starts at `max(0, bar_idx - 200 + 1)`
- For early bars (e.g., bar_idx=100), window might be `[0:101]`
- If the window has 101 bars but momentum_50 needs 50 bars of history, the first 50 bars will have NaN
- **But the last bar should have valid momentum values** (if window is large enough)

### 4. **Critical Issue: NaN Momentum Values at Last Bar**

**Hypothesis:** The last bar in the rolling window (`iloc[-1]`) has NaN momentum values, causing strategy conditions to fail.

**Possible Causes:**
1. **Insufficient lookback in rolling window:** If window starts too early, first bars have NaN, but if window is too small, last bar might also have NaN
2. **Data processing issue:** FeatureEngineer might not be filling NaN values correctly
3. **Index alignment:** Rolling window slicing might create alignment issues

### 5. **Test Output Analysis**

From test logs:
```
✅ momentum_10: NaN
✅ momentum_20: NaN  
✅ momentum_50: NaN
```

**This confirms:** The last bar in the enriched DataFrame has NaN momentum values, which explains why strategies can't generate signals.

## Solution Approaches

### Option 1: Fix Momentum Feature Creation (RECOMMENDED)

**Problem:** Momentum features have NaN at the last bar even when enough history exists.

**Fix:** Ensure FeatureEngineer properly handles edge cases:
- Use forward-fill for momentum features (carry last valid value forward)
- Or calculate momentum using `.shift(-period)` to align with current bar

### Option 2: Improve Strategy NaN Handling

**Problem:** Strategy falls back to 0.0 when all momentum values are NaN.

**Fix:** Strategy should use last valid value from the entire DataFrame, not just the rolling window:
- Check if momentum at `iloc[-1]` is NaN
- If NaN, look back further in the window for last valid value
- Use that value instead of defaulting to 0.0

### Option 3: Adjust Rolling Window Size

**Problem:** Rolling window might be too small for momentum_50 calculation.

**Fix:** Increase rolling window size to ensure all momentum features have valid values:
- Current: 200 bars
- Recommended: 250+ bars (to ensure momentum_50 has valid values)

### Option 4: Enable Historical Scanning in Test

**Problem:** `scan_all_bars=False` only evaluates last bar, which might have NaN.

**Fix:** Change test config to `scan_all_bars=True` to evaluate all bars in window:
- Strategy will scan through all bars and find valid momentum values
- More realistic for backtesting scenarios

## Recommended Fix

**Primary Fix:** Modify `_analyze_symbol_momentum` to use forward-fill for momentum values:

```python
# In enhanced_momentum.py, _analyze_symbol_momentum method
if short_momentum_col in data.columns:
    # Forward-fill NaN values to use last valid momentum
    short_momentum_series = data[short_momentum_col].fillna(method='ffill')
    short_momentum = short_momentum_series.iloc[-1] if len(short_momentum_series) > 0 else 0.0
```

**Secondary Fix:** Ensure FeatureEngineer creates momentum features correctly with proper forward-fill.

## Verification Steps

1. Add logging to show momentum values at last bar in rolling window
2. Verify momentum features are created correctly in FeatureEngineer
3. Test with different rolling window sizes
4. Compare results with `scan_all_bars=True` vs `False`

## Next Steps

1. ✅ Identify root cause (NaN momentum values)
2. ⏳ Implement fix (forward-fill momentum values)
3. ⏳ Test with diagnostic script
4. ⏳ Verify signal generation works
5. ⏳ Update integration test if needed

