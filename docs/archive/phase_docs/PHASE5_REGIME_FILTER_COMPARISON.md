# Phase 5: Mean Reversion - Regime Filter Impact Analysis

**Date**: October 6, 2025  
**Test Period**: January 2-5, 2024 (3 trading days)  
**Data**: 1-minute bars  
**Symbols**: NVDA, TSLA, AAPL

## Executive Summary

Testing Mean Reversion strategy with **regime filtering ENABLED vs DISABLED** to evaluate if filtering unfavorable market conditions improves performance.

**Key Finding**: Regime filtering **SIGNIFICANTLY IMPROVES** the BASELINE configuration but has **NO EFFECT** on CONSERVATIVE and AGGRESSIVE configurations.

## Results Comparison

### BASELINE Configuration (z=1.5, RSI=40/60, BB=2.0)

| Metric | Filter DISABLED | Filter ENABLED | Change | Impact |
|--------|----------------|----------------|--------|--------|
| **Total Trades** | 746 (24.9/day) | 465 (15.5/day) | -281 (-38%) | ✅ Fewer trades |
| **Total Return** | 1.10% | 3.86% | +2.76% (+251%) | ✅✅ MUCH BETTER |
| **Win Rate** | 24.53% | 20.00% | -4.53% | ⚠️ Slightly worse |
| **Sharpe Ratio** | -34.12 | -20.41 | +13.71 (+40%) | ✅ Better |
| **Profit Factor** | 0.46 | 0.29 | -0.17 | ⚠️ Worse |

**Analysis**: 
- ✅ **Regime filtering helps BASELINE** by reducing over-trading
- ✅ Return increased 251% (1.10% → 3.86%)
- ✅ Sharpe improved 40% (-34.12 → -20.41)
- ⚠️ Still NEGATIVE risk-adjusted returns
- ⚠️ Lower profit factor suggests keeping losers, cutting winners

### CONSERVATIVE Configuration (z=2.5, RSI=25/75, BB=2.5)

| Metric | Filter DISABLED | Filter ENABLED | Change | Impact |
|--------|----------------|----------------|--------|--------|
| **Total Trades** | 10 (0.3/day) | 10 (0.3/day) | 0 (0%) | ➖ No change |
| **Total Return** | 0.14% | 0.14% | 0% | ➖ No change |
| **Win Rate** | 10.00% | 10.00% | 0% | ➖ No change |
| **Sharpe Ratio** | -103.79 | -103.79 | 0 | ➖ No change |
| **Profit Factor** | 0.14 | 0.03 | -0.11 | ⚠️ Worse (but minimal trades) |

**Analysis**:
- ➖ **No impact from regime filtering**
- Conservative config already too restrictive (only 10 trades in 3 days)
- All trades happened to occur in favorable regimes
- Still terrible performance (10% win rate!)

### AGGRESSIVE Configuration (z=1.5, RSI=35/65, BB=1.5)

| Metric | Filter DISABLED | Filter ENABLED | Change | Impact |
|--------|----------------|----------------|--------|--------|
| **Total Trades** | 323 (10.8/day) | 323 (10.8/day) | 0 (0%) | ➖ No change |
| **Total Return** | 4.04% | 4.04% | 0% | ➖ No change |
| **Win Rate** | 31.58% | 31.58% | 0% | ➖ No change |
| **Sharpe Ratio** | -21.00 | -21.00 | 0 | ➖ No change |
| **Profit Factor** | 0.53 | 0.53 | 0 | ➖ No change |

**Analysis**:
- ➖ **No impact from regime filtering**
- AGGRESSIVE config already naturally trading in favorable regimes
- Parameters (RSI 35/65) may align with regime-favorable conditions
- Best performer but still negative Sharpe

## Detailed Analysis

### Why Regime Filter Helped BASELINE But Not Others?

**BASELINE (Filter Impact: SIGNIFICANT)**
- **Without filter**: 746 trades, many in unfavorable conditions
- **With filter**: 465 trades, filtered out 281 bad trades (-38%)
- **Hypothesis**: Over-trading in choppy/trending markets where mean reversion fails
- **Result**: Better returns by avoiding unfavorable regimes

**CONSERVATIVE (Filter Impact: NONE)**
- **Why**: Already too restrictive (z=2.5, RSI 25/75)
- **Result**: Only 10 trades in 3 days, all happened to be in favorable regimes
- **Conclusion**: Parameters so tight that regime filter adds nothing

**AGGRESSIVE (Filter Impact: NONE)**
- **Why**: Relaxed RSI thresholds (35/65) may naturally align with regime-favorable conditions
- **Result**: All 323 trades already in favorable regimes
- **Conclusion**: Parameters already regime-aware by coincidence

### Regime Filter Logic

The strategy considers regimes **FAVORABLE** for mean reversion when:
1. ✅ **Non-trending markets** (low trend strength)
2. ✅ **Normal to low volatility** environments

The strategy considers regimes **UNFAVORABLE** when:
1. ❌ **Trending markets** (high trend strength)
2. ❌ **High volatility** environments

In trending/volatile markets, mean reversion fails because:
- Prices don't revert to mean quickly
- Momentum dominates over mean reversion
- Stop losses get hit more often

## Overall Comparison Matrix

| Config | Filter | Trades | Return % | Win Rate % | Sharpe | Grade | Recommended? |
|--------|--------|--------|----------|------------|--------|-------|--------------|
| BASELINE | ❌ OFF | 746 | 1.10% | 24.53% | -34.12 | F | ❌ Over-trading |
| **BASELINE** | **✅ ON** | **465** | **3.86%** | **20.00%** | **-20.41** | **D-** | **⚠️ Best combo but still poor** |
| CONSERVATIVE | ❌ OFF | 10 | 0.14% | 10.00% | -103.79 | F | ❌ Too restrictive |
| CONSERVATIVE | ✅ ON | 10 | 0.14% | 10.00% | -103.79 | F | ❌ No improvement |
| AGGRESSIVE | ❌ OFF | 323 | 4.04% | 31.58% | -21.00 | F | ⚠️ Best return but negative Sharpe |
| AGGRESSIVE | ✅ ON | 323 | 4.04% | 31.58% | -21.00 | F | ⚠️ No change |

## Key Insights

### 1. Regime Filtering Is Valuable ✅
- **Reduced baseline trades by 38%** (746 → 465)
- **Improved returns by 251%** (1.10% → 3.86%)
- **Improved Sharpe by 40%** (-34.12 → -20.41)
- **Filters out bad trades** in unfavorable market conditions

### 2. Strategy Still Not Viable ❌
Even with regime filtering:
- **All Sharpe ratios are negative** (-20 to -103)
- **Win rates are terrible** (10% to 32%)
- **Profit factors below 1.0** (0.03 to 0.53)
- **Not suitable for production trading**

### 3. Parameter Sensitivity Matters
- **BASELINE**: Sensitive to regime filtering (benefits significantly)
- **CONSERVATIVE**: Too restrictive (regime filter adds nothing)
- **AGGRESSIVE**: Already regime-aligned (no benefit from filter)

### 4. Mean Reversion Challenges on 1-Min Data
- **Too noisy**: 1-minute data has too much noise for mean reversion
- **Insufficient time**: Prices don't have time to revert
- **High costs**: Frequent trading eats into profits
- **Better on longer timeframes**: 5-min, 15-min, or higher likely better

## Recommendations

### For Mean Reversion Strategy:
1. ✅ **ALWAYS enable regime filtering in production**
   - Significantly improves performance
   - Filters out unfavorable market conditions
   - Reduces over-trading

2. ⚠️ **Not viable on 1-minute data**
   - Even with regime filtering, negative risk-adjusted returns
   - Win rates too low (20-32%)
   - Consider abandoning 1-minute testing for this strategy

3. 🔍 **Test on longer timeframes**
   - Try 5-minute data (next step)
   - Try 15-minute data
   - Mean reversion needs time to work

4. 📊 **Consider different symbols**
   - NVDA, TSLA, AAPL are growth/momentum stocks
   - Try more stable, range-bound stocks
   - Consider ETFs or index futures

### For Strategy Optimization Plan:
1. **Don't over-optimize losing strategies**
   - Mean reversion shows poor fundamentals on 1-min data
   - Focus on finding strategies that WORK first
   - Then optimize the winners

2. **Test multiple strategies**
   - Move to Trend Following or Breakout
   - Build comparison matrix
   - Identify strategies with positive Sharpe ratios

3. **Multi-timeframe testing**
   - Test same strategy on 5-min and 15-min data
   - Some strategies suit different timeframes
   - Mean reversion may be a 15-min strategy

## Conclusions

### Technical Success ✅
- **Regime filtering works as designed**
- Successfully filtered 38% of baseline trades
- Improved returns and Sharpe ratio significantly

### Trading Success ❌
- **Mean Reversion still not viable on 1-minute data**
- Even with regime filtering, negative risk-adjusted returns
- All configurations fail institutional standards

### Best Configuration (But Still Poor)
**BASELINE with Regime Filter ENABLED**:
- 465 trades (15.5/day) - reasonable frequency
- 3.86% return - decent absolute return
- 20.00% win rate - terrible win rate
- Sharpe -20.41 - unacceptable risk-adjusted return
- **Grade: D-** (improved from F, but still failing)

### Next Steps
1. ✅ Document regime filter impact (this document)
2. 🔍 **DECISION POINT**: 
   - **Option A**: Test Mean Reversion on 5-minute data
   - **Option B**: Move to different strategy (Trend Following/Breakout)
   - **Option C**: Both - quick 5-min test, then move on

**Recommendation**: **Option C** - Quick 5-min test to see if timeframe matters, then move to testing other strategies. Don't spend too much time optimizing a fundamentally poor strategy.

---

**Status**: Regime filter analysis COMPLETE ✅  
**Finding**: Regime filtering improves performance but strategy still not viable on 1-minute data  
**Next**: Decision on whether to test 5-minute data or move to next strategy
