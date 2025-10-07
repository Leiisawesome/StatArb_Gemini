# Phase 5: 5-Minute Timeframe Testing - BLOCKED

**Date**: October 6, 2025  
**Status**: ❌ **BLOCKED BY INFRASTRUCTURE BUG**  
**Blocker**: Data Manager timeframe parameter ignored

## Summary

Attempted to test Mean Reversion strategy on 5-minute data to determine if performance improves on longer timeframes. **Testing FAILED due to core engine bug.**

## Root Cause

**File**: `core_engine/data/manager.py` line 923  
**Issue**: The `timeframe` parameter in `get_historical_data()` is **ignored**

```python
def get_historical_data(self, symbol: str, start_date: datetime, 
                      end_date: datetime, timeframe: str = "1d") -> pd.DataFrame:
    # ... validation code ...
    
    df = self.get_market_data(symbol)  # ❌ IGNORES timeframe parameter!
    return df
```

**Result**: ALL data requests return **1-minute bars** regardless of requested timeframe.

## Impact

- ❌ **Cannot test 5-minute data**
- ❌ **Cannot test 15-minute data**
- ❌ **Cannot test any timeframe except 1-minute**
- ❌ **Blocks multi-timeframe strategy optimization**

## Required Fix

### Step 1: Pass timeframe parameter
```python
df = self.get_market_data(symbol, timeframe=timeframe)  # ✅ Pass parameter
```

### Step 2: Add aggregation method
```python
def _aggregate_to_timeframe(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Aggregate 1-minute data to target timeframe"""
    resample_rules = {
        '1min': '1T', '5min': '5T', '15min': '15T',
        '30min': '30T', '1h': '1H', '1d': '1D'
    }
    rule = resample_rules.get(timeframe, '1T')
    
    return df.resample(rule).agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).dropna()
```

### Step 3: Apply aggregation if needed
```python
# In get_historical_data()
df = self.get_market_data(symbol, timeframe=timeframe)

# If only 1-min data exists, aggregate to target timeframe
if timeframe != "1min" and df is not None:
    df = self._aggregate_to_timeframe(df, timeframe)

return df
```

## Error Messages

```
❌ Market data loading failed: 'NoneType' object has no attribute 'get_historical_data'
```

This error occurred because:
1. `ComprehensiveStrategyTester` has `self.data_manager = None`
2. `test_strategy()` calls `load_market_data()` 
3. `load_market_data()` tries to call `self.data_manager.get_historical_data()`
4. But data_manager was never initialized

## Why 1-Minute Test Works But 5-Minute Fails

**1-Minute Test**: Works because default data is 1-minute, so ignoring timeframe parameter doesn't matter

**5-Minute Test**: Fails because:
1. Requests 5-minute data
2. Data manager ignores timeframe parameter
3. Returns 1-minute data
4. But data_manager isn't even initialized for framework test

## Attempted Fix

Created test file: `tests/strategy_assessment/run_mean_reversion_5min_test.py`

**Status**: ❌ Cannot run until data manager bug is fixed

## Estimated Fix Time

According to Phase 4 documentation: **5-6 hours** to:
1. Fix data manager timeframe bug
2. Implement aggregation method  
3. Test across all timeframes
4. Validate data integrity

## Recommendation

### Option A: Fix Data Manager Now (5-6 hours)
**Pros**: Enables multi-timeframe testing  
**Cons**: Delays strategy optimization

### Option B: Move to Next Strategy (RECOMMENDED)
**Pros**: Continue strategy optimization momentum  
**Cons**: Mean Reversion performance on longer timeframes unknown

### Option C: Quick Workaround
Use a simplified test that manually aggregates data **outside** the framework  
**Pros**: Fast answer on whether timeframe matters  
**Cons**: Hacky, not using proper framework

## Decision Matrix

| Option | Time | Benefits | Recommendation |
|--------|------|----------|----------------|
| Fix Data Manager | 5-6 hrs | Multi-timeframe support | ⚠️ Later |
| Test Next Strategy | 1-2 hrs | Continue optimization | ✅ **DO THIS** |
| Manual Workaround | 30 min | Quick answer | ⚠️ If really needed |

## Current Status

### Completed ✅
- ✅ 1-minute testing (BASELINE, CONSERVATIVE, AGGRESSIVE)
- ✅ Regime filter impact analysis  
- ✅ Identified infrastructure blocker
- ✅ Created 5-minute test file (ready when bug fixed)
- ✅ Comprehensive cleanup completed

### Blocked ❌
- ❌ 5-minute data testing
- ❌ 15-minute data testing
- ❌ Multi-timeframe comparison
- ❌ Timeframe-dependent strategy analysis

### Next Steps 🎯
**RECOMMENDED: Move to Option B - Test Next Strategy**

1. ✅ Document this blocker (this file)
2. ✅ Clean up codebase (completed)
3. 🎯 **Test Trend Following or Breakout on 1-minute data**
4. 🎯 **Build strategy comparison matrix**
5. 📋 Fix data manager infrastructure later (separate task)

## Conclusion

Mean Reversion on 1-minute data shows:
- ❌ Negative risk-adjusted returns (Sharpe: -20 to -103)
- ❌ Low win rates (10% to 32%)
- ✅ Regime filtering helps but not enough

**Without 5-minute testing, we cannot determine if:**
- Strategy is fundamentally flawed
- OR just unsuitable for 1-minute timeframes

**DECISION**: Don't spend 5-6 hours fixing infrastructure for one strategy that's already showing poor performance. **Move to testing other strategies**, then fix data manager as a separate infrastructure improvement task.

---

**Status**: Testing BLOCKED by infrastructure bug  
**Recommended**: Test next strategy on 1-minute data  
**Infrastructure Fix**: Required but not urgent (5-6 hours)
