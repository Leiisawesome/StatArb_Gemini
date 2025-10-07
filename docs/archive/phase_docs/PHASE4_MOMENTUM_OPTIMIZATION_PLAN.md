# Phase 4: Momentum Strategy Optimization Plan

## Executive Summary

**Status:** IN PROGRESS  
**Start Date:** October 6, 2025  
**Target Completion:** TBD  
**Priority:** HIGH - Most viable strategy for 1-minute data

## Current Assessment

### Baseline Test Results (Jan 2-31, 2024, NVDA/TSLA/AAPL)
- **Total Trades:** 0
- **Signals Generated:** 0
- **Root Cause:** Parameters optimized for daily data, not 1-minute intraday

### Diagnostic Analysis
```
🔍 [NVDA] Momentum Check (1-min data):
   short_momentum: -0.0034 (need > 0.02)    ❌ 2% in 10 bars = IMPOSSIBLE
   medium_momentum: -0.0045 (need > 0)      ❌ Negative
   long_momentum: -0.0045 (need > 0)        ❌ Negative
   adx: 39.39 (need > 25.0)                 ✅ Strong trend detected!
   volume_ratio: 0.62 (need > 1.2)          ❌ Need 20% above avg volume
```

### Key Finding
✅ **ADX works well** (39.39 > 25) - Trend detection is functional  
❌ **Momentum thresholds too high** - 2% in 10-50 minutes is unrealistic  
❌ **Volume threshold too strict** - 1.2x average is hard to meet on 1-min bars  
❌ **All 3 momentum periods must align** - Too restrictive

---

## Phase 4 Strategy

### Objective
Optimize Momentum strategy parameters for **1-minute intraday data** to achieve:
- **Sharpe Ratio:** > 1.2
- **Win Rate:** > 52%
- **Max Drawdown:** < 15%
- **Trade Frequency:** 3-10 trades/day per symbol

### Approach
**4-Step Optimization Process:**
1. **Quick Test**: Relaxed parameters to prove strategy works
2. **Parameter Grid Search**: Systematic optimization
3. **Multi-Symbol Validation**: Test across NVDA, TSLA, AAPL, SPY
4. **Production Config**: Final optimized parameters

---

## Task 4.1: Quick Validation Test ⏳

### Objective
Prove the strategy logic works with **dramatically relaxed** parameters.

### Test Configuration
```python
# RELAXED PARAMETERS FOR 1-MINUTE DATA
MomentumConfig(
    # Momentum thresholds (1-minute appropriate)
    short_period=10,              # 10 minutes
    medium_period=20,             # 20 minutes
    long_period=50,               # 50 minutes
    momentum_threshold=0.002,     # 0.2% (vs 2.0% default) ✅
    
    # Trend quality
    adx_period=14,                # Keep default
    adx_threshold=20.0,           # Lower from 25 ✅
    
    # Volume confirmation
    volume_ma_period=20,          # Keep default
    volume_threshold=1.0,         # Lower from 1.2 ✅
    
    # Position sizing
    base_position_pct=0.03,       # 3%
    max_position_pct=0.08,        # 8%
    
    # Risk management
    momentum_stop_pct=0.02,       # 2% stop (tighter)
    trailing_stop_pct=0.01,       # 1% trailing stop
    profit_target_ratio=2.0,      # 2:1 reward/risk
)
```

### Success Criteria
- ✅ Generate **at least 5 signals** over 1 month
- ✅ Execute **at least 3 trades**
- ✅ Win rate > 40%
- ✅ No catastrophic losses (> -10% single trade)

### Expected Timeline
- **Duration:** 15-30 minutes
- **Test Period:** Jan 2-31, 2024 (1 month)
- **Symbols:** NVDA, TSLA, AAPL

---

## Task 4.2: Parameter Grid Search 📊

### Objective
Systematically find optimal parameter combinations for 1-minute data.

### Grid Search Parameters
```python
parameter_grid = {
    'momentum_threshold': [0.001, 0.002, 0.003, 0.005],  # 0.1% to 0.5%
    'adx_threshold': [15.0, 20.0, 25.0],                 # Trend strength
    'volume_threshold': [0.8, 1.0, 1.2, 1.5],           # Volume filter
    'stop_loss_pct': [0.01, 0.02, 0.03],                # Stop loss
    'profit_target_ratio': [1.5, 2.0, 2.5, 3.0],        # Risk/reward
}
```

### Optimization Metric
**Composite Score** (same as Phase 3):
```python
score = (
    sharpe_ratio * 0.40 +
    total_return * 0.30 +
    win_rate * 0.20 +
    (1 - abs(max_drawdown)) * 0.10
)
```

### Grid Search Process
1. Test all combinations (4 × 3 × 4 × 3 × 4 = **576 configurations**)
2. Rank by composite score
3. Select top 10 configurations
4. Validate on out-of-sample data

### Expected Timeline
- **Duration:** 4-6 hours (automated)
- **Test Period:** Jan 2024 (training), Feb 2024 (validation)

---

## Task 4.3: Multi-Symbol Validation 🎯

### Objective
Validate optimized parameters work across different asset types.

### Test Assets
```python
test_sets = {
    'high_volatility': ['NVDA', 'TSLA', 'AMD'],
    'tech_giants': ['AAPL', 'MSFT', 'GOOGL'],
    'stable_large_caps': ['SPY', 'JPM', 'JNJ'],
}
```

### Validation Criteria
- ✅ Positive Sharpe > 1.0 on at least 2/3 symbols per set
- ✅ Consistent performance across volatility regimes
- ✅ Max drawdown < 20% on all symbols
- ✅ No single symbol dominates returns

### Expected Timeline
- **Duration:** 1-2 hours
- **Test Period:** Q1 2024

---

## Task 4.4: Feature Enhancement 🚀

### Advanced Momentum Features
Based on master plan Section 4.1-4.4, implement:

**4.4.1: Multi-Factor Momentum Scoring**
```python
momentum_factors = {
    'price_momentum': calculate_price_momentum(),      # Weight: 30%
    'volume_momentum': calculate_volume_momentum(),    # Weight: 20%
    'trend_strength': calculate_adx_strength(),        # Weight: 20%
    'momentum_acceleration': calculate_2nd_derivative(), # Weight: 15%
    'relative_momentum': calculate_relative_strength(), # Weight: 15%
}

# Combined score (0-100)
momentum_score = sum(factor * weight for factor, weight in momentum_factors.items())

# Entry threshold: momentum_score > 70
```

**4.4.2: Multi-Timeframe Alignment**
```python
timeframe_hierarchy = {
    'primary': '1min',      # Execution timeframe
    'secondary': '5min',    # Confirmation
    'tertiary': '15min',    # Trend direction
}

# Entry rule: All 3 timeframes bullish
# Hold rule: At least 2 timeframes aligned
# Exit rule: Primary timeframe reverses
```

**4.4.3: Momentum Decay Detection**
```python
exit_signals = {
    'momentum_decay': momentum_20 < 0.5 * peak_momentum,
    'volume_exhaustion': current_volume < 0.8 * avg_volume,
    'trend_weakening': adx < 0.8 * peak_adx,
    'relative_weakness': underperforming_market_by > 0.02,
    'time_based': holding_period > 200 bars and flat_returns,
}

# Exit if any 2 conditions met
```

**4.4.4: Volatility-Adjusted Position Sizing**
```python
base_position = 0.03  # 3%
atr_scalar = target_volatility / current_atr
adjusted_position = base_position * atr_scalar

# Momentum strength scaling
if momentum_score > 80:
    adjusted_position *= 1.2
elif momentum_score < 50:
    adjusted_position *= 0.8

# Cap at max_position
final_position = min(adjusted_position, 0.08)
```

### Expected Timeline
- **Duration:** 2-3 days
- **Implementation:** After Task 4.3 validation

---

## Task 4.5: Production Backtest 📈

### Objective
Final validation with optimized parameters and enhanced features.

### Test Configuration
- **Period:** Q1-Q2 2024 (6 months)
- **Symbols:** NVDA, TSLA, AAPL, MSFT, AMD
- **Capital:** $100,000
- **Parameters:** Best config from Task 4.2

### Success Criteria (Institutional Standards)
- ✅ **Sharpe Ratio:** > 1.5
- ✅ **Annual Return:** > 20%
- ✅ **Win Rate:** > 55%
- ✅ **Max Drawdown:** < 15%
- ✅ **Profit Factor:** > 1.5
- ✅ **Calmar Ratio:** > 1.0

### Expected Timeline
- **Duration:** 1 hour
- **Generate:** Full performance report, regime analysis, trade log

---

## Success Metrics

### Baseline (Current)
- **Trades:** 0
- **Sharpe:** 0.00
- **Return:** 0.00%
- **Max DD:** 0.00%

### Target (Phase 4 Complete)
- **Trades:** 100+ over 1 month
- **Sharpe:** > 1.5
- **Return:** > 20% annualized
- **Max DD:** < 15%
- **Win Rate:** > 55%

---

## Next Steps

### Immediate (Task 4.1)
1. Update `strategy_config_factory.py` with relaxed 1-min parameters
2. Run quick validation test (Jan 2024, 3 symbols)
3. Verify signals are generated and trades executed
4. Analyze initial results

### Follow-up (Tasks 4.2-4.5)
- Based on Task 4.1 results, proceed to parameter grid search
- Implement multi-symbol validation
- Add advanced momentum features
- Final production backtest

---

## Notes

### Key Insights
- **1-minute vs Daily data:** Parameters must be scaled ~50-100x lower
  - Daily: 2% momentum over 10-50 days = reasonable
  - 1-minute: 2% momentum over 10-50 minutes = rare event
  
- **ADX works well:** Trend detection is functional at 1-minute
  - Strong trends (ADX > 25) are detectable
  - May want to lower to ADX > 20 for more signals
  
- **Volume confirmation:** 1.2x threshold might be too strict
  - Consider lowering to 1.0x or removing entirely
  - Volume is more sporadic on 1-minute bars

### Lessons from Phase 3 (Statistical Arbitrage)
- ✅ **Start with relaxed parameters** to prove strategy works
- ✅ **Add comprehensive debug logging** early
- ✅ **Test multiple timeframes** (1min, 5min, 15min)
- ✅ **Validate on multiple assets** before declaring success
- ❌ **Avoid over-optimization** on single pair/timeframe

---

**Status:** Ready to proceed with Task 4.1 (Quick Validation Test)
