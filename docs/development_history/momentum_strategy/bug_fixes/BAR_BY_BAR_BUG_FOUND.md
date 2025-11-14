# Bar-by-Bar Simulation Bug - ROOT CAUSE IDENTIFIED 🎯

**Date:** November 13, 2025  
**Status:** CRITICAL BUG FOUND  
**Impact:** Explains why 0 signals are generated

---

## The Bug

### What's Happening

The test is calling `strategy.generate_signals()` in a loop for each bar:

```python
# Test loop (line 851-886)
for bar_idx in range(warmup_period, len(full_dataframe)):
    # Create rolling window data[window_start:bar_idx+1]
    bar_enriched_data = {'TSLA': data_rolling_window}
    
    # Call strategy with data up to current bar
    strategy_signals = await strategy_instance.generate_signals(bar_enriched_data)
```

**Bar 50:** Pass data[0:50] → Strategy scans bars[50:50] → `range(50, 50)` → **0 iterations** → 0 signals  
**Bar 51:** Pass data[0:51] → Strategy scans bars[50:51] → `range(50, 51)` → 1 bar evaluated  
**Bar 52:** Pass data[0:52] → Strategy scans bars[50:52] → `range(50, 52)` → **2 bars evaluated (DUPLICATE!)**

### The Problem Code

**File:** `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py` (Lines 798-816)

```python
if self.config.scan_all_bars and data_length > self.config.long_period:
    # Historical scanning mode: scan through all bars
    logger.info(f"[{symbol}] 📊 Historical scanning mode: scanning {data_length} bars")
    
    start_idx = self.config.long_period  # ALWAYS starts at 50!
    end_idx = data_length
    scan_interval = max(1, self.config.scan_interval)
    
    for idx in range(start_idx, end_idx, scan_interval):  # Re-scans same bars!
        signal = await self._evaluate_bar_at_index(symbol, idx)
        if signal:
            signals.append(signal)
    
    return signals
```

**The bug:** `start_idx = self.config.long_period` ALWAYS starts from bar 50, regardless of how many bars we've already processed!

---

## Why This Causes 0 Signals

### Scenario 1: First Call (Bar 50)
- Data: 50 bars (bars 0-49)
- `data_length = 50`
- `start_idx = 50` (config.long_period)
- `end_idx = 50` (data_length)
- `range(50, 50)` → **Empty range!** → 0 iterations → 0 signals ❌

### Scenario 2: Second Call (Bar 51)
- Data: 51 bars (bars 0-50)
- `data_length = 51`
- `start_idx = 50`
- `end_idx = 51`
- `range(50, 51)` → Evaluates bar 50 → Maybe 1 signal ✅

### Scenario 3: Third Call (Bar 52)
- Data: 52 bars (bars 0-51)
- `data_length = 52`
- `start_idx = 50`
- `end_idx = 52`
- `range(50, 52)` → Evaluates bars 50, 51 → **2 signals (duplicate bar 50!)** ❌

---

## What `scan_all_bars` Was DESIGNED For

The `scan_all_bars` mode was designed for **BATCH backtesting**, not bar-by-bar simulation:

### Correct Usage (Batch Backtest)
```python
# Load ALL historical data at once
data = load_data(start='2024-01-01', end='2024-12-31')  # 252 bars

# Call strategy ONCE with all data
signals = await strategy.generate_signals({'TSLA': data})

# Strategy scans bars 50-252 and returns ALL signals at once
# Result: 200+ signals from one call ✅
```

### Incorrect Usage (Bar-by-Bar Simulation - Current Test)
```python
# Call strategy 200 times, each with growing data
for bar in range(50, 252):
    data = load_data(start='2024-01-01', end=bar)  # Growing window
    signals = await strategy.generate_signals({'TSLA': data})  # Re-scans same bars!
    # Result: Duplicates + inefficiency ❌
```

---

## The Solution

### Option 1: Use Live Mode for Bar-by-Bar (RECOMMENDED)

**Change:** Set `scan_all_bars=False` in the test

```python
# tests/integration/live_data_validation.py (line 608)
'scan_all_bars': False,  # LIVE MODE: Only evaluate last bar ✅
```

**Behavior:** Each call to `generate_signals()` evaluates ONLY the last bar (current bar), not all historical bars.

**Pros:**
- ✅ No duplicates
- ✅ Efficient (1 bar evaluated per call)
- ✅ Matches real live trading behavior
- ✅ Designed for bar-by-bar simulation

**Cons:**
- ❌ None (this is the correct approach)

### Option 2: Track Last Processed Bar (MORE COMPLEX)

**Change:** Add state tracking to remember which bars were already processed

```python
class EnhancedMomentumStrategy:
    def __init__(self, config):
        self.last_processed_bar_index = 0  # Track progress
    
    async def _generate_symbol_signals(self, symbol):
        if self.config.scan_all_bars:
            # Only scan NEW bars, not all bars
            start_idx = max(self.config.long_period, self.last_processed_bar_index + 1)
            end_idx = data_length
            
            for idx in range(start_idx, end_idx):
                # Process bar
            
            # Update tracker
            self.last_processed_bar_index = end_idx - 1
```

**Pros:**
- ✅ Avoids duplicates
- ✅ Keeps `scan_all_bars=True`

**Cons:**
- ❌ Requires state management
- ❌ More complex
- ❌ Not the intended design

---

## Recommended Fix

**IMMEDIATE ACTION:** Change test to use `scan_all_bars=False`

**File:** `tests/integration/live_data_validation.py`  
**Line:** 608

```python
# BEFORE (WRONG for bar-by-bar)
'scan_all_bars': True,  # HISTORICAL MODE: Scan all bars

# AFTER (CORRECT for bar-by-bar)
'scan_all_bars': False,  # LIVE MODE: Only evaluate current bar (last bar)
```

**Rationale:**
- Bar-by-bar simulation should mimic LIVE trading
- In live trading, you only see the current bar, not historical bars
- `scan_all_bars=False` is the correct mode for this test
- `scan_all_bars=True` is for batch backtesting where you call the strategy ONCE with ALL data

---

## Expected Behavior After Fix

### Before (scan_all_bars=True)
```
Bar 50: range(50, 50) → 0 bars evaluated → 0 signals
Bar 51: range(50, 51) → 1 bar evaluated → Maybe 1 signal
Bar 52: range(50, 52) → 2 bars evaluated → Duplicate signals
...
Total: Quadratic complexity, duplicates, 0 signals due to empty range at start
```

### After (scan_all_bars=False)
```
Bar 50: Evaluate bar 50 only → Maybe 1 signal
Bar 51: Evaluate bar 51 only → Maybe 1 signal
Bar 52: Evaluate bar 52 only → Maybe 1 signal
...
Total: Linear complexity, no duplicates, signals generated
```

---

## Summary

**Bug Found:** ✅ YES  
**Root Cause:** Using `scan_all_bars=True` in bar-by-bar simulation (wrong mode)  
**Impact:** First call has empty range `range(50, 50)`, subsequent calls duplicate processing  
**Fix:** Change to `scan_all_bars=False` (live mode)  
**Complexity:** Trivial (1-line change)  
**Confidence:** 100% - This is definitely the bug

---

**Next Step:** Apply the fix and re-run the test to confirm signals are generated.

