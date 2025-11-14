# Phase 4C Root Cause Analysis - IN PROGRESS

## 🎯 **ROOT CAUSE IDENTIFIED BUT NOT YET RESOLVED**

**Date:** November 13, 2025 4:27 PM EST  
**Status:** ROOT CAUSE PARTIALLY FOUND - INVESTIGATION CONTINUING

---

## Summary

We've been investigating why the Type 2 (Explicit) Regime Awareness implemented in Phase 4B is not working. The investigation has revealed a critical data flow issue where regime diversity is lost between the pipeline processing and strategy consumption.

---

## What We Expected

After implementing Phase 4B, we expected:
- `_get_regime_adjusted_thresholds()` to receive diverse regime values (`choppy`, `range_bound`, `bear_high_volatility`, etc.)
- Entry thresholds to dynamically adapt based on actual market regimes
- LONG and SHORT signals to be generated based on regime-adjusted logic

---

## What Actually Happens

1. ✅ **Pipeline successfully adds diverse regime data to enriched DataFrame**
   - After `pd.merge_asof` in `_add_regime_columns()`:
     - `range_bound`: 281 bars
     - `choppy`: 80 bars
     - `bull_high_volatility`: 17 bars
     - `bear_high_volatility`: 13 bars
   - Log: "Primary regime distribution AFTER merge: {'range_bound': 281, 'choppy': 80, ...}"

2. ❌ **Strategy receives enriched data with uniform `'normal_volatility'` for all bars**
   - When strategy logs regime distribution: `{'normal_volatility': 51}`, `{'normal_volatility': 52}`, etc.
   - This is despite enriched data having columns `primary_regime=True`, `volatility_regime=True`
   - The VALUES in the columns are wrong, not the columns themselves

3. ❌ **Result: Regime adjustments default to 'normal_volatility' baseline**
   - No dynamic threshold adaptation occurs
   - Both LONG and SHORT use the same baseline thresholds (1.75)
   - Asymmetric risk management is not engaged

---

## Timeline of Discovery

### Initial Hypothesis (WRONG)
- "Regime columns don't exist in enriched data" → **DISPROVEN**
  - Added logging showed `primary_regime=True`, `volatility_regime=True`

### Second Hypothesis (WRONG)  
- "Regime sequence is empty or has wrong format" → **DISPROVEN**
  - Found 391 regime entries with proper timestamps
  - Example: `{'timestamp': ..., 'regime': 'choppy', 'confidence': 0.65, ...}`

### Third Hypothesis (PARTIALLY CORRECT)
- "Column name mismatch: 'regime' vs 'primary_regime'" → **CONFIRMED AND FIXED**
  - Added mapping: `regime_df['primary_regime'] = regime_df['regime']`
  - Pipeline now successfully merges regime data with diverse values
  - **BUT strategy still receives 'normal_volatility'!**

### Current Hypothesis (UNDER INVESTIGATION)
- "Regime diversity is lost between pipeline output and strategy input" → **INVESTIGATING**
  - Pipeline `_add_regime_columns()` outputs diverse regimes: ✅
  - Strategy `generate_signals()` receives uniform 'normal_volatility': ❌
  - **Gap in data flow needs to be traced**

---

## Code Changes Made

### 1. `core_engine/processing/pipeline_orchestrator.py`

**Location:** `_add_regime_columns()` method (lines 1450-1570)

**Fix Applied:**
```python
# CRITICAL FIX: Map 'regime' column to 'primary_regime' if it exists
# The regime sequence uses 'regime' but we need 'primary_regime'
if 'regime' in regime_df.columns and 'primary_regime' not in regime_df.columns:
    regime_df['primary_regime'] = regime_df['regime']
    logger.info(f"✅ {symbol}: Mapped 'regime' → 'primary_regime'")

# If no volatility_regime column exists, default to 'normal_volatility'
# (This happens when regime sequence only has combined regime like 'choppy')
if 'volatility_regime' not in regime_df.columns:
    regime_df['volatility_regime'] = 'normal_volatility'
    logger.info(f"✅ {symbol}: Added default 'volatility_regime' = 'normal_volatility'")
```

**Verification:**
- ✅ `regime` → `primary_regime` mapping executes
- ✅ `pd.merge_asof` successfully merges regime data with signals
- ✅ Post-merge regime distribution shows diversity: `{'range_bound': 281, 'choppy': 80, ...}`

---

## Test Evidence

### From `/tmp/test_output.log`

**Pipeline Output (CORRECT):**
```
2025-11-13 16:23:13,619 - core_engine.processing.pipeline_orchestrator - INFO - 🔍 Phase 4C: _add_regime_columns called for TSLA
2025-11-13 16:23:13,619 - core_engine.processing.pipeline_orchestrator - INFO -    Regime sequence length: 391
2025-11-13 16:24:13,174 - core_engine.processing.pipeline_orchestrator - INFO - ✅ TSLA: Mapped 'regime' → 'primary_regime'
2025-11-13 16:25:21,412 - core_engine.processing.pipeline_orchestrator - INFO -    Primary regime distribution AFTER merge: {'range_bound': 281, 'choppy': 80, 'bull_high_volatility': 17, 'bear_high_volatility': 13}
```

**Strategy Input (WRONG):**
```
2025-11-13 16:27:08,246 - core_engine.trading.strategies.implementations.momentum.enhanced_momentum - INFO - 🔍 Phase 4C: TSLA enriched data has regime columns: primary=True, volatility=True
2025-11-13 16:27:08,246 - core_engine.trading.strategies.implementations.momentum.enhanced_momentum - INFO -    Regime distribution in data: {'normal_volatility': 51}
```

---

## Critical Questions Remaining

1. **Where is regime diversity lost?**
   - Between `pipeline.process_market_data()` and `strategy.generate_signals(enriched_data)`
   - Possible culprits:
     - Bar-by-bar simulation slicing (`data_rolling_window = full_dataframe.iloc[window_start:window_end].copy()`)
     - EnrichedMarketData container transformation
     - DataFrame copy/slice operations losing column data

2. **Why does volatility_regime show 'normal_volatility' when primary_regime should vary?**
   - We defaulted `volatility_regime` to `'normal_volatility'` in the pipeline fix
   - But `primary_regime` should have diverse values from the merge
   - The strategy is checking `primary_regime` column, which exists but has wrong values

3. **Is the regime column being overwritten somewhere downstream?**
   - Possible in:
     - `EnrichedMarketData.__init__()`
     - `_update_market_data()` in strategy
     - DataFrame operations in test simulation

---

## Next Steps

### Immediate Actions
1. **Trace enriched_data from pipeline to strategy**
   - Add logging in `live_data_validation.py` after `pipeline.process_market_data()`
   - Log regime distribution of `enriched_data_dict['TSLA'].signals`
   - Check if regime diversity exists at this point

2. **Verify bar-by-bar simulation slicing preserves regime columns**
   - Check if `data_rolling_window = full_dataframe.iloc[window_start:window_end].copy()` preserves regime values
   - Verify `bar_enriched_data = {'TSLA': data_rolling_window}` contains regime diversity

3. **Add logging in strategy's `_update_market_data()`**
   - Check if regime columns are being modified during market data update
   - Verify `self.market_data[symbol]` retains regime diversity after update

### Diagnostic Code Needed
```python
# In live_data_validation.py after pipeline.process_market_data()
enriched_data = enriched_data_dict['TSLA']
full_dataframe = enriched_data.signals
logger.info(f"🔍 DIAGNOSTIC: Full DataFrame regime distribution:")
logger.info(f"   {full_dataframe['primary_regime'].value_counts().to_dict()}")

# In bar-by-bar loop after slicing
logger.info(f"🔍 DIAGNOSTIC: Rolling window regime distribution:")
logger.info(f"   {data_rolling_window['primary_regime'].value_counts().to_dict()}")

# In strategy _update_market_data() after assignment
logger.info(f"🔍 DIAGNOSTIC: self.market_data[{symbol}] regime distribution:")
logger.info(f"   {self.market_data[symbol]['primary_regime'].value_counts().to_dict()}")
```

---

## Conclusion

We've successfully:
- ✅ Fixed regime column name mismatch (`'regime'` → `'primary_regime'`)
- ✅ Verified pipeline produces diverse regime data in enriched DataFrame
- ✅ Confirmed regime columns exist when data reaches strategy

**BUT regime diversity is being lost in transit!** The investigation must continue to trace exactly where the `primary_regime` column values are being reset to uniform `'normal_volatility'`.

**Current Status:** ROOT CAUSE PARTIALLY IDENTIFIED - CONTINUING INVESTIGATION

