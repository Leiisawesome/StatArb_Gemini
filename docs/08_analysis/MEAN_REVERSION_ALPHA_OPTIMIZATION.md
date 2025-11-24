# Mean Reversion Strategy: Alpha Logic Optimization Plan
==============================================================

**Date:** November 24, 2025  
**Status:** ACTIVE - Strategy Optimization Phase  
**Current Performance:** 0% return (baseline needs improvement)  

## Executive Summary

With the core_engine and backtest suite validated, **strategy alpha optimization** is now the critical path to profitability. This document outlines a systematic approach to optimize the Mean Reversion strategy's alpha logic.

**Current Status:** Strategy generates signals but produces 0% returns across all experiments.  
**Root Cause:** Entry/exit logic may be too conservative or poorly calibrated.  
**Goal:** Optimize alpha logic to achieve consistent positive returns with acceptable risk.

---

## Part 1: Current Alpha Logic Analysis

### 1.1 Entry Logic (OVERSOLD BUY)

**Current Conditions:**
```python
if (zscore < -zscore_entry_threshold and    # Default: -2.0
    rsi < rsi_oversold and                  # Default: 30
    bb_position < 0.2):                     # Near lower Bollinger Band
```

**Issues Identified:**
- ❌ **Triple Confluence Too Strict**: Requires 3 conditions simultaneously
- ❌ **RSI Threshold Too Extreme**: RSI < 30 only happens in severe oversold (rare)
- ❌ **Z-score -2.0 Too Conservative**: Misses moderate mean reversion opportunities
- ❌ **Bollinger < 0.2 Too Narrow**: Only captures extreme band touches

**Expected Behavior:**
- Should trigger when price deviates significantly from mean
- But current thresholds are **too restrictive** for intraday 1-minute data

### 1.2 Exit Logic (TAKE PROFIT)

**Current Conditions:**
```python
if zscore > zscore_exit_threshold:  # Default: 0.5
    # Exit when price reverts toward mean
```

**Issues Identified:**
- ❌ **Exit Too Early**: Z-score 0.5 is barely back to mean
- ❌ **Leaves Alpha on Table**: Doesn't capture full mean reversion move
- ❌ **No Profit Target**: Missing explicit profit-taking mechanism
- ❌ **No Stop Loss**: Missing downside protection (relies on time stop only)

### 1.3 Position Sizing Logic

**Current Formula:**
```python
position_size = base_position_pct * volatility_adjustment * confidence_adjustment
# Default: 2% * (volatility_target/current_vol) * signal_confidence
```

**Issues Identified:**
- ✅ **Volatility Scaling**: Good - adjusts for volatility
- ⚠️ **Base 2% Too Small**: For $1M portfolio, only $20K position
- ⚠️ **Confidence Penalty**: Further reduces already-small positions
- ❌ **No Kelly Criterion**: Missing optimal sizing based on win rate/reward

### 1.4 Confidence Calculation

**Current Weights:**
```python
confidence = (
    0.4 * zscore_confidence +      # Z-score distance
    0.3 * rsi_confidence +         # RSI extreme
    0.2 * bollinger_confidence +   # Bollinger position
    0.1 * regime_confidence        # Regime favorability
)
```

**Issues Identified:**
- ✅ **Multi-Factor**: Good - considers multiple signals
- ⚠️ **Equal Weighting Sub-Optimal**: Not all factors equally predictive
- ❌ **Missing Volume**: No volume confirmation in confidence
- ❌ **Missing Momentum**: No momentum divergence check

---

## Part 2: Optimization Strategy

### 2.1 Phase 1: Relaxation Testing (Quick Wins)

**Objective:** Find optimal thresholds by systematically relaxing current parameters.

**Parameter Sweep Experiment:**
```yaml
# backtest/configs/mr_optimization_relaxation.yaml
parameter_grid:
  zscore_entry_threshold: [1.5, 2.0, 2.5]      # Test more aggressive entries
  zscore_exit_threshold: [0.3, 0.5, 0.7]       # Test earlier/later exits
  rsi_oversold: [35, 40, 45]                    # Relax RSI threshold
  rsi_overbought: [55, 60, 65]                  # Relax RSI threshold
  base_position_pct: [0.03, 0.05, 0.07]        # Test larger position sizes
```

**Expected Outcome:**
- Identify which parameters are **too conservative**
- Find optimal balance between signal frequency and quality
- Target: **10+ trades per day** with **win rate > 55%**

### 2.2 Phase 2: Indicator Enhancement (Medium Term)

**New Alpha Signals to Add:**

1. **Volume Confirmation**
   ```python
   # Add volume spike detection
   volume_ratio = current_volume / avg_volume_20
   if volume_ratio > 1.5:  # 50% above average
       confidence += 0.1  # Boost confidence
   ```

2. **Momentum Divergence**
   ```python
   # Check if RSI diverges from price (classic reversal signal)
   if price_making_new_low and rsi_not_making_new_low:
       # Bullish divergence - strong buy signal
       confidence += 0.15
   ```

3. **Liquidity Check**
   ```python
   # Only trade when spread is tight
   if bid_ask_spread_bps < 10:  # Spread < 10 bps
       # Good liquidity
   else:
       return None  # Skip trade
   ```

### 2.3 Phase 3: Dynamic Thresholds (Advanced)

**Regime-Adaptive Entry/Exit:**

```python
# Adjust thresholds based on recent volatility
recent_volatility = atr_14 / price
volatility_regime = classify_volatility(recent_volatility)

if volatility_regime == "LOW":
    zscore_entry_threshold = 1.5  # More aggressive in low vol
    rsi_oversold = 40
elif volatility_regime == "HIGH":
    zscore_entry_threshold = 2.5  # More conservative in high vol
    rsi_oversold = 25
```

**Time-of-Day Filters:**

```python
# Mean reversion works better in certain hours
current_hour = datetime.now().hour

if current_hour in [10, 11, 14, 15]:  # Active trading hours
    # Higher confidence
    confidence_multiplier = 1.1
elif current_hour in [9, 16]:  # Market open/close
    # Lower confidence (more noise)
    confidence_multiplier = 0.8
```

### 2.4 Phase 4: Machine Learning Enhancement (Long Term)

**Feature Engineering for ML Model:**

1. **Price Features:**
   - Z-score (current)
   - Rate of change of Z-score (new)
   - Distance from VWAP (new)
   - Intraday high/low ratio (new)

2. **Volume Features:**
   - Volume ratio (new)
   - Volume momentum (new)
   - Volume-weighted price momentum (new)

3. **Microstructure Features:**
   - Bid-ask spread (new)
   - Order book imbalance (new)
   - Trade size distribution (new)

**Model Approach:**
- Train XGBoost classifier to predict **reversion probability**
- Use probability as confidence score
- Target: **win rate > 60%** with ML-enhanced signals

---

## Part 3: Testing & Validation Protocol

### 3.1 Optimization Workflow

```
1. Baseline Run (Current Parameters)
   ├── Document: return, Sharpe, trades, win rate
   └── Establish performance floor

2. Parameter Sweep (Phase 1)
   ├── Test 27-81 combinations
   ├── Identify top 5 parameter sets
   └── Run walk-forward validation

3. Indicator Enhancement (Phase 2)
   ├── Add volume, divergence, liquidity
   ├── Re-run parameter sweep
   └── Compare to baseline

4. Dynamic Thresholds (Phase 3)
   ├── Implement regime-adaptive logic
   ├── Test across different market regimes
   └── Validate out-of-sample

5. Production Deployment
   └── Champion/challenger framework
```

### 3.2 Success Metrics

**Minimum Viable Strategy (MVS):**
- ✅ **Return:** > 5% annually (intraday)
- ✅ **Sharpe Ratio:** > 1.0
- ✅ **Win Rate:** > 55%
- ✅ **Max Drawdown:** < 10%
- ✅ **Trade Frequency:** 5-20 trades/day

**Stretch Goals:**
- 🎯 **Return:** > 15% annually
- 🎯 **Sharpe Ratio:** > 2.0
- 🎯 **Win Rate:** > 60%
- 🎯 **Max Drawdown:** < 5%

### 3.3 Risk Controls (Non-Negotiable)

```yaml
# Always enforce these regardless of optimization
max_position_size: 0.10          # Never exceed 10% per position
max_daily_trades: 50             # Cap at 50 trades/day
max_consecutive_losses: 5        # Stop after 5 losses in a row
max_daily_loss: 0.02             # -2% daily loss limit
min_sharpe_ratio: 0.5            # Below this = pause strategy
```

---

## Part 4: Implementation Roadmap

### Week 1: Quick Wins (Relaxation Testing)

**Day 1-2:**
- [ ] Create `mr_optimization_relaxation.yaml` config
- [ ] Run parameter sweep (27-81 combinations)
- [ ] Identify top 5 parameter sets

**Day 3-4:**
- [ ] Run walk-forward validation on top 5
- [ ] Calculate parameter stability metrics
- [ ] Select champion parameter set

**Day 5:**
- [ ] Run regime-specific tests
- [ ] Validate performance across regimes
- [ ] Document findings

### Week 2: Indicator Enhancement

**Day 1-2:**
- [ ] Implement volume confirmation logic
- [ ] Implement momentum divergence detection
- [ ] Implement liquidity filters

**Day 3-4:**
- [ ] Re-run parameter sweep with new indicators
- [ ] Compare to baseline (Week 1)
- [ ] Measure improvement delta

**Day 5:**
- [ ] Run full validation suite
- [ ] Update strategy documentation
- [ ] Deploy to staging

### Week 3: Dynamic Thresholds

**Day 1-3:**
- [ ] Implement regime-adaptive thresholds
- [ ] Implement time-of-day filters
- [ ] Test across historical regimes

**Day 4-5:**
- [ ] Run Monte Carlo simulations
- [ ] Stress test under extreme conditions
- [ ] Final validation

### Week 4: Production Prep

**Day 1-2:**
- [ ] Set up champion/challenger framework
- [ ] Implement real-time monitoring
- [ ] Create performance dashboards

**Day 3-5:**
- [ ] Paper trade for 3 days
- [ ] Review all trades manually
- [ ] Final go/no-go decision

---

## Part 5: Expected Outcomes

### Baseline (Current)
```
Return:          0.00%
Sharpe:          0.00
Trades:          0-10/day
Win Rate:        N/A
Max Drawdown:    0.00%
Status:          ❌ Not viable
```

### After Phase 1 (Relaxation)
```
Return:          3-8%
Sharpe:          0.5-1.0
Trades:          10-30/day
Win Rate:        52-58%
Max Drawdown:    5-8%
Status:          ⚠️ Marginal
```

### After Phase 2 (Enhancement)
```
Return:          8-15%
Sharpe:          1.0-1.5
Trades:          15-40/day
Win Rate:        56-62%
Max Drawdown:    4-7%
Status:          ✅ Viable
```

### After Phase 3 (Dynamic)
```
Return:          12-20%
Sharpe:          1.5-2.5
Trades:          20-50/day
Win Rate:        58-65%
Max Drawdown:    3-6%
Status:          ✅ Production-ready
```

---

## Part 6: Technical Debt & Maintenance

### Code Quality Checklist

- [ ] All logic in `enhanced_mean_reversion.py`
- [ ] All config in `core_engine/config/strategies.py`
- [ ] Zero hardcoded parameters
- [ ] Comprehensive logging
- [ ] Unit tests for all logic changes
- [ ] Integration tests for parameter changes

### Documentation Requirements

- [ ] Update strategy README
- [ ] Document all parameter changes
- [ ] Record optimization results
- [ ] Create parameter sensitivity analysis
- [ ] Maintain change log

### Monitoring & Alerts

- [ ] Real-time Sharpe ratio monitoring
- [ ] Trade frequency alerts (too high/low)
- [ ] Win rate degradation alerts
- [ ] Drawdown alerts (approaching limits)
- [ ] Parameter drift detection

---

## Appendix A: Quick Start Commands

### Run Baseline Test
```bash
# 1-week baseline
python3 backtest/run_suite.py --experiment baseline --config backtest/configs/baseline_1week.yaml
```

### Run Parameter Sweep (Phase 1)
```bash
# Create optimization config first
python3 backtest/run_suite.py --experiment parameter_sweep --config backtest/configs/mr_optimization_relaxation.yaml
```

### Run Walk-Forward Validation
```bash
python3 backtest/run_suite.py --experiment walk_forward --config backtest/configs/mr_walk_forward_optimized.yaml
```

### Compare Results
```bash
# View experiment summary
cat backtest/results/experiment_summary.csv | grep -i "mean_reversion\|baseline"
```

---

## Appendix B: Research References

**Academic Papers:**
1. Lo & MacKinlay (1990) - "When Are Contrarian Profits Due to Stock Market Overreaction?"
2. Poterba & Summers (1988) - "Mean Reversion in Stock Prices"
3. Jegadeesh & Titman (1993) - "Returns to Buying Winners and Selling Losers"

**Practitioner Insights:**
1. WorldQuant - "101 Formulaic Alphas" (Alpha #1: Mean Reversion)
2. AQR - "Value and Momentum Everywhere"
3. DE Shaw - Statistical Arbitrage Research

**Industry Benchmarks:**
- Intraday Mean Reversion Sharpe: 1.5-2.0 (top quartile)
- Win Rate: 55-65% (institutional)
- Average Trade Duration: 30-90 minutes
- Position Turnover: 10-20x annual

---

**Next Steps:** Begin Phase 1 (Relaxation Testing) tomorrow.

**Owner:** Trading Desk  
**Reviewers:** Risk Management, Quantitative Research  
**Approval Required:** CIO sign-off before Phase 3 deployment

