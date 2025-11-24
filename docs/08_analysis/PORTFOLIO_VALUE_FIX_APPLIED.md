# ANSWER: Yes, $100,000 is a Preset Default - FIXED! ✅
================================================================

**Date:** November 24, 2025  
**Status:** PARTIALLY FIXED - Progress made, still debugging

---

## Your Question

> "is the portfolio: $100,000 preset?"

## Answer: Yes, it WAS a Preset Default (Now Fixed)

**Location:** `core_engine/system/compliance_checker.py`, line 108

**The Hardcoded Default:**
```python
self.portfolio_value = self.config.get('portfolio_value', 100000.0)
                                                        ↑
                                                  Default: $100K
```

**Why This Caused the Bug:**

1. Backtest config sets `initial_capital: 1000000` ($1M)
2. Strategy calculates position: `5% * $1M = $50,000`
3. ComplianceChecker falls back to default: `portfolio_value = $100,000`
4. Concentration check: `$50,000 / $100,000 = 50%` ❌ (exceeds 20%)

---

## The Fix Applied

**File:** `backtest/engine/institutional_backtest_engine.py`  
**Lines:** 2187-2188

**Before:**
```python
compliance_config = {
    'account_equity': 100000.0,  # ❌ Hardcoded
```

**After:**
```python
compliance_config = {
    'account_equity': self.config.initial_capital,  # ✅ Uses actual config
    'portfolio_value': self.config.initial_capital,  # ✅ Explicit setting
```

---

## Results After Fix

### Test #1 (Ultra-Relaxed, Before Fix)
```
Signals:          147
Trades Attempted: 147
Trades Executed:  0 ❌
Rejection:        Position concentration 50% > 20% ($50K / $100K)
```

### Test #2 (Ultra-Relaxed, After Fix)
```
Signals:          147
Trades Attempted: 147
Trades Executed:  3 ✅ (PROGRESS!)
Rejection:        Position limit exceeded; Concentration limit exceeded (still failing most)
```

**Progress:** Went from 0 to 3 trades! The fix helped, but there's still another issue.

---

## Remaining Issue

Even after fixing the $100K default, we're still getting:
- **Rejection:** "Position limit exceeded; Concentration limit exceeded"

**Why?**

The `CentralRiskManager` has its OWN checks (separate from ComplianceChecker):

1. **ComplianceChecker** (fixed) ✅
   - Uses `portfolio_value` from config
   - Now correctly set to $1M

2. **CentralRiskManager** (still an issue) ⚠️
   - Lines 1275-1295: `_check_position_limits()`
   - Lines 1297-1317: `_check_concentration_limits()`
   - Uses `self.portfolio_value` (initialized from `initial_capital`)
   - Checks: `position_pct <= self.max_position_size` (10%)
   - Checks: `concentration <= self.position_concentration_limit` (15%)

**Current Position Calculation:**
```
Position: 119 shares * $419/share = $49,861
Portfolio: $1,000,000
Percentage: 4.99% (should pass 10% limit)
Concentration: 4.99% (should pass 15% limit)
```

**But it's still failing!** This suggests either:
1. The `portfolio_value` in RiskManager is still wrong
2. The limits are being set differently than expected
3. There's a calculation error in the checks

---

## Next Steps

### Option 1: Deep Dive into RiskManager (Thorough)
- Add logging to see actual values in `_check_position_limits()`
- Print `self.portfolio_value`, `self.max_position_size`, `position_pct`
- Identify exact failure point

### Option 2: Further Relax Limits (Workaround)
- Create config with even more relaxed limits:
  - `max_position_size: 1.0` (100% - unlimited)
  - `max_concentration: 1.0` (100% - unlimited)
- If this works, we know it's a limit calculation issue

### Option 3: Incremental Testing (Balanced)
- Test with increasing position sizes:
  - 1% → 2% → 5% → 10%
- Find the exact threshold where it fails

---

## Recommendation

Let's try **Option 2** (further relax limits) to confirm the hypothesis:

### Create: `backtest/configs/mr_diagnostic_no_limits_v2.yaml`
```yaml
experiment_name: "MR_Diagnostic_NoLimits_V2"
symbols: ["TSLA"]
start_date: "2024-12-20"
end_date: "2024-12-20"

initial_capital: 1000000

# COMPLETELY RELAX ALL LIMITS
max_position_size: 1.0           # 100% (was 0.10)
max_concentration: 1.0           # 100% (was 0.20)

strategy:
  type: "mean_reversion"
  parameters:
    base_position_pct: 0.05      # Back to 5%
    zscore_entry_threshold: 1.0
    rsi_oversold: 45
    scan_all_bars: true
    enable_regime_filter: false
```

**Expected Outcome:**
- If trades execute: ✅ Confirms it's a limit issue
- If still blocked: ❌ Deeper problem in logic

---

## Summary

1. **Your Question:** Yes, $100K was a hardcoded default ✅
2. **Fix Applied:** Use `self.config.initial_capital` instead ✅
3. **Progress Made:** 0 → 3 trades executed ✅
4. **Remaining Issue:** Still rejecting most trades ⚠️
5. **Next Step:** Further relax limits to isolate issue

**Would you like me to proceed with Option 2 (no limits config)?**


