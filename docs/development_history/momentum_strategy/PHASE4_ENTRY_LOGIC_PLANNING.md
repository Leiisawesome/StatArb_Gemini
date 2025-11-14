# Phase 4: Entry Logic Redesign - PLANNING

**Date:** November 13, 2025  
**Status:** PLANNING  
**Prerequisite:** Phase 3 (Exit Logic) COMPLETE ✅  
**Goal:** Generate balanced BUY/SELL signals

---

## Problem Statement

**Current Issue:** Strategy generates 0 BUY signals due to overly strict entry conditions.

**Root Cause:** OLD entry logic requires 4 out of 6 conditions to be met, but only 0-1 conditions are being satisfied.

**Impact:** 
- No positions opened
- No exits triggered (exit logic can't be tested)
- System produces 0 strategy signals (only 26 preliminary signals)

---

## Current Entry Logic (OLD - Too Strict)

**Location:** `enhanced_momentum.py` lines 835-880

**6 Conditions Required (need >= 4):**
1. `abs(short_momentum) > momentum_threshold` (0.02)
2. `abs(medium_momentum) > 0`
3. `abs(long_momentum) > 0`
4. `adx > adx_threshold` (25.0)
5. `volume_ratio > volume_threshold` (1.2)
6. `trend_strength > 0`

**Why It Fails:**
- Thresholds too high for current market conditions
- Requires simultaneous alignment across 3 timeframes
- ADX > 25 is very strong trend requirement
- Volume ratio > 1.2 is 20% above average (rare)

---

## Solution Options

### Option A: Composite Signal Entry (Quick Fix) ⭐ RECOMMENDED

**Approach:** Use same logic as exits (composite_z + composite_pct)

**Implementation:**
```python
# ENTRY conditions (aligned with EXIT logic)
def _check_composite_entry(self, symbol: str, current_bar: pd.Series) -> bool:
    """Check composite signal entry conditions"""
    
    composite_z = current_bar.get('composite_z', 0)
    composite_pct = current_bar.get('composite_pct', 50)
    
    # LONG entry: Strong upward momentum
    if composite_z > self.config.composite_z_entry:  # 1.75
        if composite_pct > self.config.composite_pct_entry:  # 92
            return True, SignalType.BUY
    
    # SHORT entry: Strong downward momentum
    if composite_z < -self.config.composite_z_entry:  # -1.75
        if composite_pct < (100 - self.config.composite_pct_entry):  # 8
            return True, SignalType.SELL
    
    return False, None
```

**Config Parameters to Add:**
```python
composite_z_entry: 1.75       # Entry Z-score (stronger than exit 0.7)
composite_pct_entry: 92.0     # Entry percentile (stronger than exit 55)
```

**Benefits:**
- ✅ Quick to implement (~50 lines)
- ✅ Aligned with exit logic (consistent approach)
- ✅ Uses existing composite signals
- ✅ Should generate entry signals immediately

**Drawbacks:**
- ⚠️ Less sophisticated than full hybrid
- ⚠️ Doesn't use winsorization or MAD

---

### Option B: Relax Current Conditions (Temporary)

**Approach:** Lower thresholds and reduce required conditions

**Changes:**
```python
# Relax thresholds
momentum_threshold: 0.01    # was 0.02 (50% reduction)
adx_threshold: 20.0         # was 25.0 (20% reduction)
volume_threshold: 1.0       # was 1.2 (17% reduction)

# Relax requirement
required_conditions = 2     # was 4 (need 2/6 instead of 4/6)
```

**Benefits:**
- ✅ Minimal code changes
- ✅ Quick to test

**Drawbacks:**
- ❌ Not a principled solution
- ❌ May generate too many signals
- ❌ Doesn't address architectural issues

---

### Option C: Full Hybrid Entry (Comprehensive) 🎯 ULTIMATE GOAL

**Approach:** Implement complete hybrid entry from original prompt

**Features:**
1. **Winsorized features** (outlier-resistant)
2. **MAD-based Z-scores** (robust statistics)
3. **Multi-bucket composite scoring** (10 momentum indicators)
4. **Percentile ranking** (relative strength)
5. **Weighted aggregation** (intelligent combination)

**Implementation Complexity:** ~300 lines of code

**Benefits:**
- ✅ Institutional-grade entry logic
- ✅ Outlier-resistant
- ✅ Sophisticated signal combination
- ✅ Matches exit logic sophistication

**Drawbacks:**
- ⚠️ Most complex option
- ⚠️ Requires more testing
- ⚠️ Longer development time

---

## Recommended Approach

**Two-Phase Implementation:**

### Phase 4A: Quick Fix (Option A) ⚡
1. Implement composite signal entry (~1 hour)
2. Test with live_data_validation.py
3. Verify BUY/SELL balance
4. Get immediate functionality

### Phase 4B: Comprehensive Upgrade (Option C) 🎯
1. Implement full hybrid entry (~4 hours)
2. Add winsorization and MAD
3. Complete multi-bucket scoring
4. Full testing and validation

**Timeline:**
- Phase 4A: 1 hour (immediate results)
- Phase 4B: 4 hours (production-grade)
- Total: 5 hours

---

## Expected Outcomes

### After Phase 4A (Quick Fix)
- ✅ BUY signals generated (expect 5-10 per dataset)
- ✅ SELL signals generated (via Phase 3 exit logic)
- ✅ Full trade cycle operational
- ✅ Can test exit logic end-to-end

### After Phase 4B (Comprehensive)
- ✅ Institutional-grade entry logic
- ✅ Outlier-resistant signal generation
- ✅ Sophisticated composite scoring
- ✅ Production-ready system

---

## Implementation Plan (Phase 4A)

### Step 1: Add Config Parameters
```python
# In MomentumConfig (core_engine/config/strategies.py)
composite_z_entry: float = 1.75       # Entry Z-score threshold
composite_pct_entry: float = 92.0     # Entry percentile threshold
```

### Step 2: Implement Entry Method
```python
# In enhanced_momentum.py
def _check_composite_entry(self, symbol: str, current_bar: pd.Series) -> Tuple[bool, Optional[SignalType]]:
    """Check composite signal entry conditions (Phase 4A)"""
    # Implementation here (~30 lines)
```

### Step 3: Replace OLD Entry Logic
```python
# In _generate_symbol_signals() around line 835
# REPLACE: 6-condition logic
# WITH: _check_composite_entry() call
```

### Step 4: Test
```bash
python3 tests/integration/live_data_validation.py
# Expect: 5-10 BUY signals + corresponding SELL signals from exits
```

---

## Success Criteria

### Phase 4A Success Metrics
- ✅ At least 3 BUY signals generated per dataset
- ✅ Exit logic triggers (SELL signals generated)
- ✅ No linter errors
- ✅ BUY/SELL ratio between 0.5-2.0 (reasonable balance)

### Phase 4B Success Metrics
- ✅ Institutional-grade entry logic
- ✅ Winsorization operational
- ✅ MAD-based Z-scores working
- ✅ 10-indicator composite scoring
- ✅ Full documentation

---

## Risk Assessment

### Low Risk (Phase 4A)
- Simple logic change
- Uses existing composite signals
- Easy to revert if issues
- Quick validation

### Medium Risk (Phase 4B)
- More complex implementation
- New statistical methods
- Requires thorough testing
- Longer development time

---

## Files to Modify

### Phase 4A (Quick Fix)
1. **`core_engine/config/strategies.py`**
   - Add 2 config parameters (composite_z_entry, composite_pct_entry)

2. **`core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py`**
   - Add `_check_composite_entry()` method (~30 lines)
   - Replace OLD entry logic in `_generate_symbol_signals()` (~10 lines)
   - Total: ~40 lines changed

### Phase 4B (Comprehensive)
1. **`core_engine/config/strategies.py`**
   - Add winsorization config
   - Add MAD config
   - Add bucket weights

2. **`enhanced_momentum.py`**
   - Add winsorization method (~50 lines)
   - Add MAD calculation (~30 lines)
   - Add multi-bucket scoring (~100 lines)
   - Update entry logic (~50 lines)
   - Total: ~230 lines new code

---

## Questions for User

1. **Do you want to proceed with Phase 4A (quick fix) first?**
   - Pro: Immediate results, can test exit logic
   - Con: Not as sophisticated as Phase 4B

2. **Or jump directly to Phase 4B (comprehensive)?**
   - Pro: Production-grade from start
   - Con: Longer development time

3. **Or do something else entirely?**
   - Fix other issues first?
   - Different approach to entry logic?

---

## Ready to Proceed

**Phase 3 Foundation is Solid:**
- ✅ Exit logic production-ready
- ✅ Position tracking enhanced
- ✅ Config parameters in place
- ✅ No blocking technical debt

**Choose Next Step:**
- [ ] Phase 4A: Quick composite entry (1 hour)
- [ ] Phase 4B: Full hybrid entry (4 hours)
- [ ] Both: Phase 4A then 4B (5 hours)
- [ ] Other: Different direction

**Awaiting your decision to proceed!** 🚀

