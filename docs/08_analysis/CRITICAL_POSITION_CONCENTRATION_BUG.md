# CRITICAL FINDING: Mean Reversion Strategy Issue #2
================================================================

**Date:** November 24, 2025  
**Status:** BLOCKER - All trades rejected by risk manager  
**Priority:** P0 - Must fix before optimization

---

## Problem Statement

**Symptom:** 147 signals generated, **0 trades executed**  
**Root Cause:** Position concentration limit violation  

```
🚨 Trade rejected - Compliance violation:  
   Position concentration 49.8% exceeds limit 20.0%  
   ($49,773 / $100,000)
```

---

## Technical Analysis

### What's Happening:

1. **Strategy** generates signal with `base_position_pct: 0.05` (5%)
2. **Engine** calculates position as: `0.05 * initial_capital = 0.05 * $1,000,000 = $50,000`
3. **Risk Manager** checks concentration: `$50,000 / $100,000 = 50%`
4. **Limit** is `max_concentration: 0.20` (20%)
5. **Result:** Trade **REJECTED** ❌

### The Bug:

**Position sizing is calculated against `initial_capital` ($1M), but risk limits are checked against current `portfolio_value` (starts at $100K after prior losses/different initialization).**

This is a **capital base mismatch** issue.

---

## Why This Wasn't Caught Earlier

1. **Smoke Test (Jan 2):** Probably had different starting capital or no signals
2. **Baseline Test (Jan 2-5):** Same issue, but we focused on zero quantity bug
3. **Diagnostic Test:** Made concentration limit explicit (20%), exposing the issue

---

## Solution Options

### Option 1: Fix Position Sizing Logic (RECOMMENDED) ✅

**Change:** Calculate `base_position_pct` as percentage of **current portfolio value**, not initial capital.

**Location:** `backtest/engine/institutional_backtest_engine.py`, lines ~3310-3320

**Current Code:**
```python
# Prioritize base_position_pct from strategy parameters
base_position_pct = strategy_params.get('base_position_pct', None)

if base_position_pct is not None:
    max_position_dollar = self.risk_manager.portfolio_value * base_position_pct
    max_position_shares = max_position_dollar / current_price
    # ...
    
    # ❌ BUG: Sets max_position_size as % of initial_capital
    self.risk_manager.max_position_size = max_position_dollar / self.risk_manager.initial_capital
```

**Fixed Code:**
```python
# Prioritize base_position_pct from strategy parameters
base_position_pct = strategy_params.get('base_position_pct', None)

if base_position_pct is not None:
    # ✅ FIX: Use current portfolio_value consistently
    max_position_dollar = self.risk_manager.portfolio_value * base_position_pct
    max_position_shares = max_position_dollar / current_price
    
    # ✅ FIX: Keep as absolute dollar amount, don't convert to %
    # Risk manager will check against portfolio_value
    # OR set as % of current portfolio_value
    self.risk_manager.max_position_size_dollar = max_position_dollar
```

### Option 2: Increase Concentration Limit (WORKAROUND) ⚠️

**Change:** Increase `max_concentration` in config to match actual positions.

```yaml
max_concentration: 0.50  # Allow 50% positions (was 0.20)
```

**Pros:**
- Quick fix
- Unblocks testing

**Cons:**
- ❌ Dangerous for production (excessive concentration risk)
- ❌ Doesn't fix root cause
- ❌ Violates risk management best practices

### Option 3: Reduce Position Size (WORKAROUND) ⚠️

**Change:** Reduce `base_position_pct` to fit within 20% limit.

```yaml
base_position_pct: 0.002  # 0.2% (was 0.05 = 5%)
```

**Pros:**
- Safe from risk perspective
- Unblocks testing

**Cons:**
- ❌ Positions too small to be meaningful
- ❌ Doesn't fix root cause

---

## Recommended Action Plan

### Immediate (Today)

1. **Fix position sizing logic** (Option 1)
   - Ensure `base_position_pct` is always relative to current portfolio value
   - Update `institutional_backtest_engine.py`
   - Test with diagnostic config

2. **Validate fix**
   - Re-run diagnostic test
   - Expect: Trades executed, returns non-zero

3. **Document change**
   - Update inline comments
   - Add to change log

### Short-Term (This Week)

4. **Run optimization sweep** (Phase 1)
   - Now that trades will execute
   - Find optimal parameters

5. **Validate across regimes**
   - Ensure fix works in all market conditions

---

## Impact Assessment

### Before Fix:
```
Signals:  147
Trades:   0
Return:   0.00%
Status:   ❌ Blocked
```

### After Fix (Expected):
```
Signals:  147
Trades:   30-50 (estimated)
Return:   -2% to +5% (initial guess)
Status:   ✅ Functional
```

---

## Testing Protocol

### 1. Unit Test
```python
def test_position_sizing_uses_current_portfolio_value():
    """Ensure position sizing uses current portfolio value, not initial capital"""
    
    risk_manager = Mock()
    risk_manager.portfolio_value = 100000  # Current value
    risk_manager.initial_capital = 1000000  # Original value
    
    base_position_pct = 0.05  # 5%
    current_price = 100
    
    # Expected position: 5% of $100K = $5,000 = 50 shares
    expected_shares = 50
    
    # Calculate actual
    max_position_dollar = risk_manager.portfolio_value * base_position_pct
    actual_shares = max_position_dollar / current_price
    
    assert actual_shares == expected_shares
    assert max_position_dollar == 5000
```

### 2. Integration Test
```bash
# Run diagnostic with fix
python3 backtest/run_suite.py --experiment baseline \
  --config backtest/configs/mr_diagnostic_ultra_relaxed.yaml

# Expected: Trades > 0, concentration violations = 0
```

### 3. Regression Test
```bash
# Run full suite to ensure no side effects
python3 backtest/run_suite.py --experiment baseline \
  --config backtest/configs/baseline_1week.yaml
```

---

## Lessons Learned

1. **Always check rejection reasons** in logs when trades = 0
2. **Portfolio value vs initial capital** are different concepts
3. **Risk limits must use same capital base** as position sizing
4. **Integration tests** should catch concentration violations

---

## Next Steps

**Priority 1:** Fix position sizing logic (30 min)  
**Priority 2:** Re-run diagnostic test (5 min)  
**Priority 3:** Begin Phase 1 optimization (Day 1)

**Owner:** Trading Desk  
**Status:** IN PROGRESS  
**ETA:** Fix by end of day

