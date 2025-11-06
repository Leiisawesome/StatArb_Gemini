# Expert Review: Signal Moment Pre-Action Checklist

**Date:** November 6, 2025  
**Reviewer:** 3rd Party Trading Expert  
**Framework Version:** Phase 0-11 Complete  
**Status:** Gap Analysis & Recommendations

---

## Executive Summary

This document reviews the expert's comprehensive checklist of state variables and constraints that must be evaluated **at the signal moment** (when a momentum indicator flips to "buy" or "sell") before taking action. The review compares the expert's recommendations against the current StatArb_Gemini framework implementation.

**Overall Assessment:** The framework has **strong coverage** (70-80%) of the expert's recommendations, with **critical gaps** in real-time market microstructure data, order book depth, and intraday position aging.

---

## 1. Current Positions ✅ **PARTIALLY IMPLEMENTED**

### Expert Requirements:
- Side (long/short/flat)
- Size (quantity, notional, % of portfolio)
- Average entry price and realized/unrealized P&L
- Open orders for that instrument
- Time-in-position (how long the position has been open)
- Position limits (per instrument and portfolio)

### Current Implementation Status:

**✅ IMPLEMENTED:**
- **Side & Size:** `CentralRiskManager.current_positions` tracks position quantities
- **Entry Price:** `EnhancedMomentumStrategy.active_positions` stores `entry_price` and `entry_time`
- **P&L Tracking:** `RealTimePnLTracker` (Rule 4 enhancement) tracks unrealized P&L
- **Position Limits:** `CentralRiskManager._check_position_limits()` enforces per-instrument and portfolio limits
- **Time-in-Position:** `EnhancedMomentumStrategy._close_position()` calculates `holding_period_hours`

**❌ MISSING:**
- **Open Orders Tracking:** No centralized tracking of pending orders per instrument
- **Realized P&L:** While unrealized P&L is tracked, realized P&L calculation is not explicitly exposed at signal moment
- **Notional Value:** Position size is tracked in shares, but notional value (% of portfolio) is calculated on-demand, not cached

**📍 LOCATION:**
- Position tracking: `core_engine/system/central_risk_manager.py` (lines 1270-1300)
- Strategy position tracking: `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py` (lines 90-95)
- P&L tracking: `core_engine/system/central_risk_manager.py` (via `pnl_tracker`)

**🔧 RECOMMENDATION:**
1. Add `open_orders` tracking to `CentralRiskManager` (per symbol)
2. Expose `get_position_summary(symbol)` method that returns all position state at once
3. Cache notional value (% of portfolio) in position tracking

---

## 2. Market State ⚠️ **PARTIALLY IMPLEMENTED**

### Expert Requirements:
- Current price (last trade), bid/ask, and best bid/ask sizes
- Recent liquidity and volume (e.g., volume in last N minutes)
- Spread and expected slippage given order size
- Volatility estimate (e.g., ATR or realized vol over lookback)

### Current Implementation Status:

**✅ IMPLEMENTED:**
- **Current Price:** `TradingDecisionRequest.current_price` is populated
- **Volatility Estimate:** `TradingDecisionRequest.volatility_estimate` is set
- **Liquidity Assessment:** `EnhancedTradingEngine._assess_liquidity()` evaluates liquidity
- **Expected Slippage:** `EnhancedTradingEngine._estimate_market_impact()` calculates slippage
- **ATR:** Available in enriched data (`ATR_14`)

**❌ MISSING:**
- **Bid/Ask & Best Bid/Ask Sizes:** Not captured in `TradingDecisionRequest` or execution planning
- **Order Book Depth:** No order book analytics at signal moment
- **Recent Volume:** Volume is available in enriched data, but "volume in last N minutes" is not explicitly calculated
- **Spread Calculation:** Spread is not explicitly calculated or stored

**📍 LOCATION:**
- Market data: `core_engine/trading/engine.py` (lines 1158-1196)
- Liquidity assessment: `core_engine/trading/engine.py` (lines 1198-1250)
- Market impact: `core_engine/trading/engine.py` (lines 1252-1350)

**🔧 RECOMMENDATION:**
1. **CRITICAL:** Add bid/ask and order book depth to `TradingDecisionRequest`
2. Add `calculate_recent_volume(symbol, minutes)` to data manager
3. Add `calculate_spread(symbol)` method that uses bid/ask from market data
4. Enhance `_assess_liquidity()` to include order book depth analysis

---

## 3. Entry Reference ✅ **FULLY IMPLEMENTED**

### Expert Requirements:
- Price when current position was built (entry price)
- Price when last scaling occurred (if laddered entries)
- Historical peak/until-now high/low while position open

### Current Implementation Status:

**✅ IMPLEMENTED:**
- **Entry Price:** `EnhancedMomentumStrategy.active_positions[symbol]['entry_price']` stores entry price
- **Entry Time:** `EnhancedMomentumStrategy.active_positions[symbol]['entry_time']` stores entry timestamp
- **Historical High/Low:** Can be calculated from `market_data` DataFrame (position tracking has access to price history)

**⚠️ PARTIALLY IMPLEMENTED:**
- **Laddered Entries:** Position tracking supports adding to positions (`on_position_opened` handles position additions), but "last scaling price" is not explicitly tracked separately

**📍 LOCATION:**
- Entry tracking: `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py` (lines 91-95, 700-750)

**🔧 RECOMMENDATION:**
1. Add `last_scale_price` and `last_scale_time` to position tracking for laddered entries
2. Add `position_high` and `position_low` tracking to `active_positions` dict

---

## 4. Strategy Risk & Rule Set ✅ **FULLY IMPLEMENTED**

### Expert Requirements:
- Take-profit and stop-loss rules (absolute or volatility scaled)
- Maximum drawdown allowed for the trade / per day
- Max position age (intraday: close by X minutes to close)
- Max new exposure allowed (e.g., net exposure cap)

### Current Implementation Status:

**✅ IMPLEMENTED:**
- **Take-Profit & Stop-Loss:** `EnhancedMomentumStrategy.stop_losses`, `profit_targets`, `trailing_stops` are fully implemented
- **Stop-Loss Activation:** `_check_exit_conditions()` checks stop-loss and take-profit triggers
- **Volatility Scaling:** Stop-losses can be volatility-scaled (ATR-based)
- **Max Position Age:** `PositionAgingMonitor` (Rule 7 enhancement) enforces strategy-specific holding limits
- **Max Exposure:** `CentralRiskManager._check_position_limits()` enforces `max_position_size` and `position_concentration_limit`
- **Daily Drawdown:** `TradingCircuitBreakers` (Rule 4 enhancement) enforces daily loss limits

**📍 LOCATION:**
- Stop-loss/take-profit: `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py` (lines 93-95, 800-900)
- Position aging: `core_engine/system/position_aging_monitor.py` (Rule 7 enhancement)
- Circuit breakers: `core_engine/system/circuit_breakers.py` (Rule 4 enhancement)

**🔧 RECOMMENDATION:**
1. ✅ **NO ACTION NEEDED** - This category is fully implemented

---

## 5. Portfolio-Level Context ✅ **FULLY IMPLEMENTED**

### Expert Requirements:
- Current portfolio net exposure and risk budget left
- Correlation / concentration with other positions
- Cash/leverage available

### Current Implementation Status:

**✅ IMPLEMENTED:**
- **Net Exposure:** `CentralRiskManager.portfolio_value` tracks total portfolio value
- **Risk Budget:** `CentralRiskManager._calculate_risk_impact()` calculates risk budget allocation
- **Concentration:** `CentralRiskManager._check_concentration_limits()` enforces concentration limits
- **Cash Available:** `CentralRiskManager.available_cash` tracks available cash
- **Portfolio Metrics:** `CentralRiskManager._update_portfolio_metrics()` calculates portfolio-level metrics

**📍 LOCATION:**
- Portfolio tracking: `core_engine/system/central_risk_manager.py` (lines 145-200, 1245-1300)
- Risk budget: `core_engine/system/central_risk_manager.py` (lines 1245-1268)

**🔧 RECOMMENDATION:**
1. ✅ **NO ACTION NEEDED** - This category is fully implemented

---

## 6. Execution Constraints ⚠️ **PARTIALLY IMPLEMENTED**

### Expert Requirements:
- Minimum order size and lot-size rounding
- Market hours / tradeable window (intraday only?)
- Any scheduled news events / market open/close proximity

### Current Implementation Status:

**✅ IMPLEMENTED:**
- **Execution Time Limits:** `TradingAuthorization.max_execution_time` sets execution time constraints
- **Algorithm Selection:** `EnhancedTradingEngine._select_execution_algorithm()` chooses execution algorithm based on constraints

**❌ MISSING:**
- **Minimum Order Size:** Not enforced in `TradingDecisionRequest` validation
- **Lot-Size Rounding:** Quantity is not rounded to lot sizes
- **Market Hours:** No market hours validation (e.g., "intraday only" constraint)
- **News Events:** No scheduled news event checking
- **Market Open/Close Proximity:** No validation of proximity to market open/close

**📍 LOCATION:**
- Execution constraints: `core_engine/trading/engine.py` (lines 1024-1152)
- Request validation: `core_engine/system/central_risk_manager.py` (lines 1102-1108)

**🔧 RECOMMENDATION:**
1. **HIGH PRIORITY:** Add `minimum_order_size` and `lot_size` to `TradingDecisionRequest`
2. Add `round_to_lot_size(quantity, lot_size)` helper function
3. Add `is_market_hours(symbol, timestamp)` validation
4. Add `check_news_events(symbol, timestamp)` integration (if news feed available)
5. Add `proximity_to_market_close(timestamp)` check for intraday-only strategies

---

## 7. Performance Objective ⚠️ **PARTIALLY IMPLEMENTED**

### Expert Requirements:
- Intraday goal (e.g., target return per day, target Sharpe on intraday signals, maximum intraday drawdown)
- Whether the strategy is aggressive (capture momentum early) or conservative (wait for confirmation)

### Current Implementation Status:

**✅ IMPLEMENTED:**
- **Intraday Drawdown:** `TradingCircuitBreakers` tracks intraday high-water mark and drawdown
- **Strategy Aggressiveness:** `MomentumConfig.enable_regime_adjusted_thresholds` allows strategy to be more/less aggressive based on regime
- **Confidence Thresholds:** Strategy confidence thresholds can be adjusted for aggressiveness

**❌ MISSING:**
- **Target Return Per Day:** No explicit daily return target tracking
- **Target Sharpe on Intraday Signals:** No Sharpe ratio calculation for intraday signals
- **Aggressive vs Conservative Mode:** While regime-adjusted thresholds exist, there's no explicit "aggressive" vs "conservative" mode flag

**📍 LOCATION:**
- Circuit breakers: `core_engine/system/circuit_breakers.py` (Rule 4 enhancement)
- Regime adjustment: `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py` (lines 477-534)

**🔧 RECOMMENDATION:**
1. Add `daily_return_target` and `intraday_sharpe_target` to strategy config
2. Add `strategy_mode` enum: `AGGRESSIVE` vs `CONSERVATIVE` with explicit threshold differences
3. Track intraday performance metrics separately from daily metrics

---

## Implementation Priority Matrix

### 🔴 **CRITICAL GAPS** (Must Address for Production)
1. **Bid/Ask & Order Book Depth** (Category 2)
   - Impact: Cannot assess true market liquidity without order book data
   - Effort: Medium (requires market data feed integration)
   - Priority: P0

2. **Minimum Order Size & Lot-Size Rounding** (Category 6)
   - Impact: Orders may be rejected by broker if not properly sized
   - Effort: Low (simple validation)
   - Priority: P0

3. **Market Hours Validation** (Category 6)
   - Impact: May attempt to trade outside market hours
   - Effort: Low (calendar integration)
   - Priority: P0

### 🟠 **HIGH PRIORITY GAPS** (Should Address Soon)
4. **Open Orders Tracking** (Category 1)
   - Impact: May over-allocate capital if pending orders not tracked
   - Effort: Medium (requires order state management)
   - Priority: P1

5. **Recent Volume Calculation** (Category 2)
   - Impact: Liquidity assessment may be stale
   - Effort: Low (data aggregation)
   - Priority: P1

6. **Spread Calculation** (Category 2)
   - Impact: Execution cost estimation incomplete
   - Effort: Low (bid-ask calculation)
   - Priority: P1

### 🟡 **MEDIUM PRIORITY GAPS** (Nice to Have)
7. **Laddered Entry Tracking** (Category 3)
   - Impact: Position scaling history not fully tracked
   - Effort: Low (add fields to position dict)
   - Priority: P2

8. **Position High/Low Tracking** (Category 3)
   - Impact: Cannot assess position performance vs historical peak
   - Effort: Low (add fields to position dict)
   - Priority: P2

9. **Daily Return Target** (Category 7)
   - Impact: No explicit daily performance goal
   - Effort: Medium (requires performance tracking enhancement)
   - Priority: P2

---

## Current Framework Strengths

### ✅ **What We Do Well:**
1. **Comprehensive Risk Management:** Position limits, concentration limits, risk budget allocation
2. **Regime-Aware Processing:** Strategy adapts to market conditions
3. **Stop-Loss & Take-Profit:** Fully implemented with volatility scaling
4. **Portfolio-Level Context:** Complete portfolio tracking and risk metrics
5. **Execution Planning:** Liquidity assessment and market impact estimation
6. **Circuit Breakers:** Daily loss limits and drawdown protection

### ⚠️ **Areas for Improvement:**
1. **Real-Time Market Microstructure:** Missing bid/ask, order book depth
2. **Order State Management:** No tracking of pending orders
3. **Market Hours Validation:** No trading window enforcement
4. **Lot-Size Handling:** No rounding to exchange lot sizes

---

## Recommended Implementation Roadmap

### **Sprint 1: Critical Market Data (2-3 days)**
- Add bid/ask to `TradingDecisionRequest`
- Add order book depth assessment
- Add spread calculation
- Add recent volume calculation (last N minutes)

### **Sprint 2: Execution Constraints (1-2 days)**
- Add minimum order size validation
- Add lot-size rounding
- Add market hours validation
- Add proximity-to-close check

### **Sprint 3: Order State Management (2-3 days)**
- Add `open_orders` tracking to `CentralRiskManager`
- Add order state machine (PENDING → FILLED → CANCELLED)
- Update position calculations to account for pending orders

### **Sprint 4: Enhanced Position Tracking (1 day)**
- Add `last_scale_price` and `last_scale_time`
- Add `position_high` and `position_low` tracking
- Enhance `get_position_summary()` method

### **Sprint 5: Performance Objectives (2 days)**
- Add daily return target tracking
- Add intraday Sharpe calculation
- Add explicit `strategy_mode` (AGGRESSIVE vs CONSERVATIVE)

---

## Conclusion

The StatArb_Gemini framework has **strong foundational coverage** (70-80%) of the expert's recommendations, with particular strength in:
- Risk management and position limits
- Stop-loss and take-profit mechanisms
- Portfolio-level context and risk budget allocation
- Regime-aware strategy adaptation

**Critical gaps** exist in:
- Real-time market microstructure data (bid/ask, order book depth)
- Execution constraints (lot sizes, market hours)
- Order state management (pending orders tracking)

**Estimated Effort:** 8-12 days of development to address all critical and high-priority gaps.

**Recommendation:** Prioritize Sprint 1 (Market Data) and Sprint 2 (Execution Constraints) for production readiness, as these are fundamental to accurate execution cost estimation and order validation.

---

**Last Updated:** November 6, 2025  
**Status:** Review Complete - Implementation Roadmap Defined

