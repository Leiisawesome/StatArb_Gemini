# Mean Reversion Strategy: Immediate Action Items
====================================================

**Date:** November 24, 2025  
**Status:** Active Investigation - Multiple Blockers Identified  
**Priority:** P0 - Critical for alpha optimization

---

## Current Status Summary

### Progress Today
✅ Created comprehensive optimization plan (4 phases)  
✅ Identified Bug #1: Position concentration violations  
✅ Created workaround configs  
✅ Discovered Bug #2: Position limit violations  
⏳ Working toward first profitable backtest

### Test Results Evolution

**Test 1 (Ultra-Relaxed):**
```
Signals:    147
Trades:     0
Rejection:  Position concentration 50% > 20%
Status:     BLOCKED
```

**Test 2 (Tiny Positions):**
```
Signals:    147
Trades:     87 attempted, 0 executed
Rejection:  Position limit exceeded
Status:     PARTIALLY UNBLOCKED (different error)
```

---

## Key Findings

### 1. Strategy Signal Generation Works ✅
- **147 signals** generated consistently across tests
- Entry logic is functional
- Indicators are being calculated correctly

### 2. Risk Authorization is Multi-Layered 🔍
Discovered **multiple** risk checks that can block trades:

```
Signal → Compliance Check → Position Limit Check → Concentration Check → Execution
          (7 checks)         (FAILING HERE)        (passed in Test 2)
```

### 3. Position Limit Check is Blocking
**Current Issue:** After passing compliance, hitting "Position limit exceeded"

**Possible Causes:**
1. **Max positions per symbol** exceeded
2. **Total portfolio positions** exceeded
3. **Strategy-level allocation** exceeded
4. **Position value** exceeds a different limit than concentration

---

## Recommended Next Steps

### Option A: Deep Dive into Risk Manager Logic (2-3 hours)

**Action:** Trace through `CentralRiskManager.authorize_trading_decision()` to understand ALL rejection criteria.

**Files to investigate:**
- `core_engine/system/central_risk_manager.py`
- `core_engine/system/compliance_checker.py`

**Goal:** Document every single check that can block a trade.

### Option B: Temporarily Disable Risk Checks (30 min - RISKY) ⚠️

**Action:** Create a "dev mode" config that bypasses risk checks for diagnostic purposes.

**Approach:**
```python
# In institutional_backtest_engine.py
if config.dev_mode:
    # Skip authorization, execute all signals
    for signal in signals:
        await self._execute_signal_directly(signal)
```

**Pros:**
- Quick way to test if strategy alpha logic works
- Proves signals → trades → P&L path is functional

**Cons:**
- ❌ Dangerous - bypasses all safety
- ❌ Not representative of production
- ❌ Must re-enable checks before deployment

### Option C: Incremental Config Tuning (1-2 hours) ✅ RECOMMENDED

**Action:** Systematically relax ALL risk limits to find which one is blocking.

**Step-by-step:**
1. Increase `max_position_size` to 1.0 (100%)
2. Increase `max_concentration` to 1.0 (100%)
3. Set `max_positions` to 1000 (unlimited)
4. Disable `enable_regime_filter`
5. Set `min_signal_confidence` to 0.0

**Goal:** One of these will unblock trades. Then we know the exact blocker.

---

## Proposed Diagnostic Test #3

### Config: mr_diagnostic_no_limits.yaml

```yaml
experiment_name: "MR_Diagnostic_NoLimits"
experiment_type: "baseline_backtest"

symbols: ["TSLA"]
interval: "1min"
start_date: "2024-12-20"
end_date: "2024-12-20"

# EXTREME RELAXATION - Turn off ALL limits
initial_capital: 1000000
allow_shorts: true
max_position_size: 1.0           # 100% (no limit)
max_concentration: 1.0           # 100% (no limit)

strategy:
  type: "mean_reversion"
  name: "MR_Diagnostic_NoLimits"
  allocation_pct: 1.0
  parameters:
    # Ultra-relaxed entry
    zscore_entry_threshold: 1.0
    rsi_oversold: 45
    
    # Tiny positions (to avoid cash issues)
    base_position_pct: 0.002
    max_position_pct: 1.0        # No limit
    
    # Scanning
    scan_all_bars: true
    scan_interval: 1
    enable_regime_filter: false
    
    # No stops
    stop_loss_atr_multiple: 100.0  # Effectively disabled
    max_holding_period: 1000       # Hold forever

# Minimal risk management
min_signal_confidence: 0.0       # Accept all signals

# Risk manager overrides (if supported)
risk_management:
  max_daily_trades: 1000         # No limit
  max_positions: 1000            # No limit
  position_limit: 1000000000     # No limit
```

**Expected Outcome:**
- If trades execute: ✅ Proves strategy CAN work
- If still 0 trades: 🔍 Look at execution engine

---

## What We Need from User

**Question 1:** Do you want to:
- **A)** Deep dive into risk manager to understand all checks? (Thorough but slower)
- **B)** Create "no limits" diagnostic to bypass checks? (Fast but risky)
- **C)** Continue incremental config tuning? (Balanced approach)

**Question 2:** What's the priority?
- **Speed** (get profitable backtest ASAP, even if hacky)
- **Correctness** (understand root cause before proceeding)
- **Balance** (reasonable workarounds while documenting issues)

---

## Long-Term Plan (Unchanged)

Once unblocked:
1. **Week 1:** Phase 1 optimization (parameter sweep)
2. **Week 2:** Phase 2 enhancement (volume, divergence)
3. **Week 3:** Phase 3 dynamic thresholds
4. **Week 4:** Validation and deployment

**Estimated Time to First Profitable Backtest:**
- If unblocked today: 2-3 days
- If need to refactor risk manager: 1-2 weeks

---

**Awaiting User Direction** 🎯

Please advise which path to take:
- Deep dive (thorough)
- No limits diagnostic (fast)
- Incremental tuning (balanced)

