================================================================================
🔍 OPTION 1: DEBUG STRATEGY SIGNAL GENERATION - EXECUTION PLAN
================================================================================

DATE: 2025-10-18
STATUS: 🟢 EXECUTING - Systematic Strategy Debugging

================================================================================
🎯 OBJECTIVE
================================================================================

Identify why the Momentum strategy generates ZERO trades despite 4.1% of bars (457 bars) meeting all 6 conditions in the condition analysis.

================================================================================
🔍 ROOT CAUSE HYPOTHESIS
================================================================================

**PRIMARY HYPOTHESIS:** Disconnect between feature engineer output and strategy signal generation logic

**Evidence:**
1. ✅ Core engine creates features correctly: `momentum_10`, `momentum_20`, `momentum_50`, `adx`, `trend_strength`
2. ✅ Condition analysis shows 457 bars meet all 6 conditions (4.1%)
3. ❌ Strategy generates ZERO trades in backtest

**Suspected Issues:**
1. Strategy calculates its own momentum (`momentum_short`, `momentum_medium`, `momentum_long`)
2. Strategy's own calculations may differ from feature engineer
3. Strategy may have additional hidden conditions not visible in condition analysis
4. Threshold misalignment between condition analysis and strategy code

================================================================================
📋 DEBUGGING EXECUTION PLAN
================================================================================

### Phase 1: Trace Strategy Momentum Calculations (30 min)
**Goal:** Understand how strategy calculates its momentum values

1. Extract strategy's momentum calculation logic (lines 500-506)
2. Compare with feature engineer's momentum calculation
3. Identify any discrepancies in formulas or parameters

### Phase 2: Instrument Strategy Signal Generation (45 min)
**Goal:** Add comprehensive logging to strategy's `generate_signals` method

1. Add logging at line 395 (bullish momentum check entry)
2. Log each of the 6 conditions individually
3. Log actual feature values vs thresholds
4. Identify which condition(s) are failing

### Phase 3: Run Instrumented Backtest (15 min)
**Goal:** Collect actual runtime data from instrumented strategy

1. Run backtest on NVDA 2023 Q1 with instrumented strategy
2. Capture detailed logs of condition checks
3. Count how many bars reach each condition checkpoint

### Phase 4: Analyze Results & Fix (30 min)
**Goal:** Based on logs, identify exact failure point and implement fix

1. Analyze which conditions are blocking signals
2. Determine if issue is calculation, threshold, or logic
3. Implement targeted fix
4. Verify fix generates trades

================================================================================
🔧 IMPLEMENTATION STEPS
================================================================================

### Step 1: Create Strategy Diagnostic Script
```
File: backtest/optimization/diagnose_strategy_signals.py
Purpose: Directly test strategy signal generation with known-good data
```

### Step 2: Add Strategy Instrumentation
```
File: core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py
Method: generate_signals() (lines 395-461)
Add: Detailed logging of each condition check
```

### Step 3: Run Diagnostic Backtest
```
Script: backtest/optimization/run_momentum_baseline.py
Period: NVDA 2023 Q1 (highest momentum period)
Log Level: DEBUG
```

### Step 4: Analyze & Fix
Based on logs, implement one of:
- Adjust thresholds if too strict
- Fix calculation if formula mismatch
- Remove redundant conditions if over-constrained

================================================================================
✅ SUCCESS CRITERIA
================================================================================

1. **Identify Exact Failure Point:** Know which specific condition(s) block signals
2. **Understand Root Cause:** Know WHY those conditions fail (threshold/calculation/logic)
3. **Generate Trades:** After fix, strategy generates >10 trades on NVDA 2023 Q1
4. **Validation:** Trades align with condition analysis (457 qualifying bars → ~100-200 trades)

================================================================================
📊 EXPECTED OUTCOMES
================================================================================

**Best Case:** Simple threshold issue, easy fix, trades generated immediately
**Likely Case:** Logic mismatch between condition analysis and strategy, requires code adjustment
**Worst Case:** Fundamental disconnect, requires strategy refactoring

**Timeline:** 2 hours total (systematic debugging)
**Risk:** Low - we have comprehensive data and logging framework

================================================================================
🚀 EXECUTION STATUS
================================================================================

- [x] Phase A.1: Add ADX indicator to core engine
- [x] Phase A.2: Add momentum features to feature engineer
- [x] Verify core engine fixes work correctly
- [x] Run condition analysis (confirmed 457 bars meet all conditions)
- [ ] **CURRENT:** Phase 1 - Trace strategy momentum calculations
- [ ] Phase 2 - Instrument strategy signal generation
- [ ] Phase 3 - Run instrumented backtest
- [ ] Phase 4 - Analyze results & implement fix

================================================================================
