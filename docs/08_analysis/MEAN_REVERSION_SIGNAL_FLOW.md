# Mean Reversion Strategy - Complete Signal Generation Flow

**Date:** 2024-11-24  
**Strategy:** `EnhancedMeanReversionStrategy`  
**File:** `core_engine/trading/strategies/implementations/mean_reversion/enhanced_mean_reversion.py`

---

## 📊 Signal Generation Flow Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    PHASE 0-4: DATA PIPELINE (Rule 3)                 │
│                    Enriched DataFrame with indicators                │
│  [timestamp, OHLCV, zscore, RSI_14, bb_position, ATR, ...]         │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│                  ENTRY POINT: generate_signals()                     │
│                  Called by: StrategyManager                          │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STEP 1: Symbol Loop                                                │
│  for symbol in ['AAPL', 'TSLA', 'NVDA']:                            │
│      signals += await _generate_symbol_signals(symbol)              │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STEP 2: Mode Selection (Historical vs Live)                        │
│                                                                      │
│  if config.scan_all_bars:                                           │
│      # HISTORICAL MODE (Backtesting)                                │
│      for idx in range(lookback_period, data_length, scan_interval): │
│          signal = await _evaluate_bar_at_index(symbol, idx)         │
│  else:                                                               │
│      # LIVE MODE (Production)                                       │
│      signal = await _evaluate_bar_at_index(symbol, -1)  # Last bar  │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STEP 3: Extract Pre-Calculated Indicators (Rule 3 Compliance)      │
│                                                                      │
│  # READ from enriched DataFrame (NO calculation!)                   │
│  zscore = data['zscore'].iloc[idx]         # Z-score of price       │
│  rsi = data['RSI_14'].iloc[idx]            # RSI indicator          │
│  bb_position = data['bb_position'].iloc[idx]  # Bollinger position  │
│  current_price = data['close'].iloc[idx]                            │
│                                                                      │
│  # Handle NaN values with forward-fill                              │
│  zscore = zscore_series.ffill().iloc[idx]                           │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STEP 4: Get Regime-Adjusted Thresholds (Regime-First)              │
│                                                                      │
│  thresholds = _get_regime_adjusted_thresholds(symbol)               │
│                                                                      │
│  # Base thresholds (from config)                                    │
│  zscore_entry_threshold: 2.0    # Default: 2 std devs               │
│  rsi_oversold: 30               # Default: RSI < 30                 │
│  rsi_overbought: 70             # Default: RSI > 70                 │
│                                                                      │
│  # Regime adjustments (if unfavorable regime)                       │
│  if regime in ['extreme_volatility', 'crisis', 'trending']:         │
│      adjustment_factor = 0.8  # Make entry EASIER (lower threshold) │
│      zscore_threshold *= adjustment_factor  # 2.0 → 1.6             │
│      rsi_oversold *= 1.2  # 30 → 36 (easier to trigger)            │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STEP 5: Apply Regime Filter (Optional)                             │
│                                                                      │
│  if config.enable_regime_filter:  # Default: false in Phase 1       │
│      if not _is_regime_favorable(symbol):                           │
│          return None  # Skip signal generation                      │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STEP 6: Check Entry Conditions (CORE ALPHA LOGIC) ⭐               │
│                                                                      │
│  # OVERSOLD BUY SIGNAL (3 conditions)                               │
│  if (zscore < -2.0 AND                     # Price < mean - 2σ      │
│      rsi < 30 AND                          # RSI oversold           │
│      bb_position < 0.2):                   # Below lower BB         │
│                                                                      │
│      → GENERATE BUY SIGNAL                                          │
│                                                                      │
│  # OVERBOUGHT SELL SIGNAL (3 conditions)                            │
│  elif (zscore > 2.0 AND                    # Price > mean + 2σ      │
│        rsi > 70 AND                        # RSI overbought         │
│        bb_position > 0.8):                 # Above upper BB         │
│                                                                      │
│      → GENERATE SELL SIGNAL                                         │
│                                                                      │
│  else:                                                               │
│      → NO SIGNAL (neutral conditions)                               │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STEP 7: Calculate Signal Confidence                                │
│                                                                      │
│  confidence = _calculate_signal_confidence(symbol, signal_type)     │
│                                                                      │
│  Factors:                                                           │
│  - Z-score magnitude: abs(zscore) / threshold                       │
│  - RSI extremity: (30 - rsi) / 30 for oversold                     │
│  - BB position: distance from bands                                 │
│  - Regime confidence: from regime engine                            │
│  - Volume confirmation: volume > avg_volume                         │
│                                                                      │
│  Weighted average → confidence: 0.0 to 1.0                          │
│                                                                      │
│  if confidence < 0.6:  # Min confidence threshold                   │
│      return None  # Reject weak signal                              │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STEP 8: Create StrategySignal Object                               │
│                                                                      │
│  signal = StrategySignal(                                           │
│      strategy_id="mean_reversion_1",                                │
│      symbol="AAPL",                                                 │
│      signal_type=SignalType.BUY,  # or SELL                         │
│      strength=0.85,  # abs(zscore) / threshold                      │
│      confidence=0.72,  # From Step 7                                │
│      target_weight=0.05,  # 5% of portfolio (PERCENTAGE) ⭐         │
│      quantity_type="PERCENTAGE",  # Critical for engine             │
│      timestamp=datetime.now(),                                      │
│      additional_data={                                              │
│          'signal_reason': 'oversold_mean_reversion',                │
│          'zscore': -2.3,                                            │
│          'rsi': 27.5,                                               │
│          'bb_position': 0.15,                                       │
│          'entry_price': 439.01,                                     │
│          'bar_index': 1250                                          │
│      }                                                               │
│  )                                                                   │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  OUTPUT: List[StrategySignal]                                       │
│                                                                      │
│  [                                                                   │
│      StrategySignal(AAPL, BUY, 0.05, confidence=0.72),             │
│      StrategySignal(TSLA, SELL, 0.05, confidence=0.68),            │
│      StrategySignal(NVDA, BUY, 0.05, confidence=0.81)              │
│  ]                                                                   │
│                                                                      │
│  → Passed to StrategyManager for aggregation (Phase 6, Rule 4)     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 Detailed Component Breakdown

### 1. Entry Conditions (ALPHA LOGIC)

#### OVERSOLD BUY Signal

**Conditions (ALL must be true):**

```python
# Condition 1: Z-Score Oversold
zscore < -2.0  # Price is 2 standard deviations BELOW mean
               # Example: If mean=$440, σ=$10, zscore=-2.3 → price=$417

# Condition 2: RSI Oversold
rsi < 30       # RSI momentum indicator shows oversold
               # Example: RSI=27.5 → Strong selling pressure

# Condition 3: Bollinger Band Position
bb_position < 0.2  # Price near or below lower Bollinger Band
                   # Example: bb_position=0.15 → 15% from lower to upper band
```

**Economic Intuition:**
- Price has deviated significantly from statistical mean
- Momentum indicators confirm oversold condition
- Technical levels (Bollinger Bands) support reversal
- **Thesis:** Price will revert to mean due to statistical gravity

#### OVERBOUGHT SELL Signal

**Conditions (ALL must be true):**

```python
# Condition 1: Z-Score Overbought
zscore > 2.0   # Price is 2 standard deviations ABOVE mean
               # Example: If mean=$440, σ=$10, zscore=2.5 → price=$465

# Condition 2: RSI Overbought
rsi > 70       # RSI momentum indicator shows overbought
               # Example: RSI=78.2 → Strong buying pressure (exhaustion)

# Condition 3: Bollinger Band Position
bb_position > 0.8  # Price near or above upper Bollinger Band
                   # Example: bb_position=0.85 → 85% from lower to upper band
```

**Economic Intuition:**
- Price has extended significantly above mean
- Momentum indicators suggest overbought exhaustion
- Technical levels indicate potential reversal
- **Thesis:** Price will revert to mean due to profit-taking

---

### 2. Indicator Sources (Rule 3 Compliance)

**CRITICAL:** Strategy does NOT calculate indicators. All values are **READ** from pre-calculated enriched DataFrame.

```python
# ✅ CORRECT: Reading pre-calculated values
zscore = data['zscore'].iloc[idx]         # Calculated by FeatureEngineer (Phase 3)
rsi = data['RSI_14'].iloc[idx]            # Calculated by TechnicalIndicators (Phase 2)
bb_position = data['bb_position'].iloc[idx]  # Calculated by FeatureEngineer (Phase 3)

# ❌ WRONG: Calculating indicators (Rule 3 violation)
# zscore = (price - mean) / std_dev  # This should NEVER happen in strategy!
# rsi = calculate_rsi(data['close'], 14)  # This should NEVER happen in strategy!
```

**Pipeline Flow (from Rule 3):**

```
Phase 1: DataManager loads raw OHLCV
         ↓
Phase 2: TechnicalIndicators calculates RSI_14, ATR, etc.
         ↓
Phase 3: FeatureEngineer calculates zscore, bb_position, etc.
         ↓
Phase 4: SignalGenerator adds preliminary signals
         ↓
Phase 5: Strategy (THIS COMPONENT) applies alpha logic
```

---

### 3. Regime-Aware Thresholds

**Base Thresholds (from config):**
- `zscore_entry_threshold: 2.0`
- `rsi_oversold: 30`
- `rsi_overbought: 70`

**Regime Adjustments:**

```python
# Unfavorable regimes (harder to mean revert)
unfavorable = ['extreme_volatility', 'crisis', 'trending']

if regime in unfavorable:
    # Make entry EASIER by relaxing thresholds
    adjustment_factor = 0.8
    
    zscore_threshold = 2.0 * 0.8 = 1.6  # Lower barrier (easier to trigger)
    rsi_oversold = 30 * 1.2 = 36        # Higher oversold threshold
    rsi_overbought = 70 * 0.8 = 56      # Lower overbought threshold
```

**Intuition:**
- In trending markets, mean reversion is weaker
- Relaxing thresholds allows catching stronger reversals only
- Prevents trading weak reversions that fail in trends

---

### 4. Confidence Scoring

**Multi-Factor Confidence Calculation:**

```python
def _calculate_signal_confidence(self, symbol: str, signal_type: MeanReversionSignal) -> float:
    """
    Calculate signal confidence from multiple factors
    
    Weights:
    - Z-score magnitude: 40%
    - RSI extremity: 25%
    - BB position: 15%
    - Volume confirmation: 10%
    - Regime confidence: 10%
    """
    
    # Factor 1: Z-score strength (0.0-1.0)
    zscore_strength = min(abs(zscore) / zscore_threshold, 1.0)
    # Example: abs(-2.3) / 2.0 = 1.15 → capped at 1.0
    
    # Factor 2: RSI extremity (0.0-1.0)
    if signal_type == OVERSOLD_BUY:
        rsi_strength = (30 - rsi) / 30  # Lower RSI = higher confidence
        # Example: (30 - 27.5) / 30 = 0.083
    else:  # OVERBOUGHT_SELL
        rsi_strength = (rsi - 70) / 30  # Higher RSI = higher confidence
        # Example: (78.2 - 70) / 30 = 0.273
    
    # Factor 3: Bollinger Band position (0.0-1.0)
    if signal_type == OVERSOLD_BUY:
        bb_strength = 1.0 - bb_position  # Lower = higher confidence
        # Example: 1.0 - 0.15 = 0.85
    else:  # OVERBOUGHT_SELL
        bb_strength = bb_position  # Higher = higher confidence
        # Example: 0.85
    
    # Factor 4: Volume confirmation (0.0-1.0)
    volume_ratio = current_volume / avg_volume
    volume_strength = min(volume_ratio, 2.0) / 2.0
    # Example: 1.5M / 1.2M = 1.25 → 1.25 / 2.0 = 0.625
    
    # Factor 5: Regime confidence (0.0-1.0)
    regime_strength = regime_context.confidence if regime_context else 0.5
    # Example: 0.72
    
    # Weighted average
    confidence = (
        zscore_strength * 0.40 +    # 1.0 * 0.40 = 0.40
        rsi_strength * 0.25 +        # 0.083 * 0.25 = 0.021
        bb_strength * 0.15 +         # 0.85 * 0.15 = 0.128
        volume_strength * 0.10 +     # 0.625 * 0.10 = 0.063
        regime_strength * 0.10       # 0.72 * 0.10 = 0.072
    )
    # = 0.40 + 0.021 + 0.128 + 0.063 + 0.072 = 0.684
    
    return confidence  # 0.684 (68.4% confidence)
```

**Confidence Threshold:**
```python
if confidence < 0.6:  # 60% minimum
    return None  # Reject signal
```

---

### 5. Position Sizing (Target Weight)

**Output Signal Structure:**

```python
signal = StrategySignal(
    symbol="AAPL",
    signal_type=SignalType.BUY,
    target_weight=0.05,  # 5% of portfolio ← PERCENTAGE ⭐
    quantity_type="PERCENTAGE",  # Critical flag for engine
    # ...
)
```

**Conversion to Shares (happens in InstitutionalBacktestEngine):**

```python
# In institutional_backtest_engine.py (Phase 8):
if quantity_type == "PERCENTAGE" and target_weight > 0:
    portfolio_value = risk_manager.portfolio_value  # $1,000,000
    dollar_amount = target_weight * portfolio_value  # 0.05 * $1M = $50,000
    quantity = dollar_amount / current_price  # $50,000 / $439.01 = 113.89
    quantity = max(1, int(quantity))  # Floor to 113 shares
```

**Why Percentage Instead of Shares?**

1. **Portfolio-Relative:** Automatically scales with account size
2. **Risk-Aware:** 5% position is same risk whether $100K or $1M portfolio
3. **Rebalancing:** Easier to maintain target allocations
4. **Strategy-Agnostic:** Engine handles conversion, strategy focuses on alpha

---

### 6. Historical Scanning Mode

**Two Modes:**

#### A. Live Mode (Production)
```python
scan_all_bars: false  # Default for live trading

# Evaluates only LAST bar (current market state)
current_row = data.iloc[-1]
signal = _evaluate_bar_at_index(symbol, -1)

# Use case: Real-time trading
```

#### B. Historical Mode (Backtesting)
```python
scan_all_bars: true   # Enable for backtesting
scan_interval: 1      # Evaluate every bar (or skip bars for speed)

# Scans through ALL historical bars
for idx in range(lookback_period, data_length, scan_interval):
    signal = _evaluate_bar_at_index(symbol, idx)
    if signal:
        signals.append(signal)

# Use case: Backtesting, optimization, research
```

**Performance Optimization:**
```python
# Full scan (slow but complete)
scan_interval: 1  # Every bar → 4,680 bars/day (1-min data)

# Fast scan (faster but might miss signals)
scan_interval: 5  # Every 5th bar → 936 bars/day

# Ultra-fast scan (coarse but quick)
scan_interval: 60  # Every hour → 78 bars/day
```

---

### 7. Exit Signal Generation (Separate Method)

**Note:** Entry signals (BUY/SELL) are generated by `_generate_symbol_signals()`.  
**Exit signals** (CLOSE) are generated by `_check_exit_conditions()`.

**Exit Conditions (ANY can trigger):**

```python
async def _check_exit_conditions(self) -> None:
    """Check exit conditions for active positions"""
    
    for symbol in self.active_positions:
        current_price = data['close'].iloc[-1]
        position = self.active_positions[symbol]
        
        # Exit Condition 1: Stop Loss
        if current_price <= self.stop_losses[symbol]:
            await _close_position(symbol, reason="stop_loss")
        
        # Exit Condition 2: Profit Target
        elif current_price >= self.profit_targets[symbol]:
            await _close_position(symbol, reason="profit_target")
        
        # Exit Condition 3: Mean Reversion Complete ⭐
        elif abs(zscore) < 0.5:  # Z-score back to neutral
            await _close_position(symbol, reason="mean_reversion_complete")
        
        # Exit Condition 4: Max Holding Period
        elif holding_time > max_holding_period:
            await _close_position(symbol, reason="max_holding_period")
```

**Exit Condition 3 is the ALPHA EXIT:**
- Entry: Price at -2.0 std devs (oversold)
- Exit: Price at -0.5 std devs (near mean)
- **Profit:** Captured the reversion from extreme to neutral

---

## 🎯 Example: Complete Signal Generation

**Market State:**
- Symbol: AAPL
- Current Price: $417.25
- Mean Price (20-bar): $440.00
- Std Dev: $10.00

**Calculated Indicators (from enriched data):**
```python
zscore = (417.25 - 440.00) / 10.00 = -2.275
rsi = 27.5  # Oversold momentum
bb_position = 0.15  # 15% from lower to upper Bollinger Band
volume_ratio = 1.5  # 50% above average volume
```

**Signal Generation Steps:**

```
STEP 1: Check Entry Conditions
  ✅ zscore (-2.275) < -2.0 → TRUE (2.3 std devs below mean)
  ✅ rsi (27.5) < 30 → TRUE (oversold)
  ✅ bb_position (0.15) < 0.2 → TRUE (near lower band)
  
  → ALL CONDITIONS MET → GENERATE BUY SIGNAL

STEP 2: Calculate Confidence
  zscore_strength = 2.275 / 2.0 = 1.138 → cap at 1.0
  rsi_strength = (30 - 27.5) / 30 = 0.083
  bb_strength = 1.0 - 0.15 = 0.85
  volume_strength = min(1.5, 2.0) / 2.0 = 0.75
  regime_strength = 0.72
  
  confidence = (1.0*0.40 + 0.083*0.25 + 0.85*0.15 + 0.75*0.10 + 0.72*0.10)
             = 0.40 + 0.021 + 0.128 + 0.075 + 0.072
             = 0.696 (69.6%) ✅ > 60% threshold

STEP 3: Create Signal
  StrategySignal(
      symbol='AAPL',
      signal_type=SignalType.BUY,
      strength=1.0,  # Capped zscore strength
      confidence=0.696,
      target_weight=0.05,  # 5% of portfolio
      quantity_type='PERCENTAGE',
      timestamp=datetime(2024, 1, 15, 10, 30, 0),
      additional_data={
          'signal_reason': 'oversold_mean_reversion',
          'zscore': -2.275,
          'rsi': 27.5,
          'bb_position': 0.15,
          'entry_price': 417.25
      }
  )

STEP 4: Convert to Shares (in engine)
  portfolio_value = $1,000,000
  dollar_amount = 0.05 * $1,000,000 = $50,000
  quantity = $50,000 / $417.25 = 119.86
  quantity = int(119.86) = 119 shares
  
  → Trade Request: BUY 119 shares of AAPL @ $417.25
```

---

## 🔧 Key Configuration Parameters

```yaml
# Core Parameters
lookback_period: 20              # Bars for mean/std calculation
zscore_entry_threshold: 2.0      # Entry at 2 std devs
zscore_exit_threshold: 0.5       # Exit at 0.5 std devs

# RSI Parameters
rsi_period: 14                   # RSI lookback
rsi_oversold: 30                 # Oversold threshold
rsi_overbought: 70               # Overbought threshold

# Bollinger Bands
bb_period: 20                    # BB lookback
bb_std_dev: 2.0                  # BB std dev multiplier

# Position Sizing
base_position_pct: 0.05          # 5% base position
max_position_pct: 0.30           # 30% max position

# Risk Management
stop_loss_atr_multiple: 2.0      # Stop loss = entry - 2*ATR
profit_target_ratio: 2.0         # Profit = 2x risk
max_holding_period: 50           # Max 50 bars

# Confidence
min_confidence: 0.60             # 60% minimum confidence

# Regime
enable_regime_filter: false      # Regime filtering (disabled Phase 1)
regime_adjustment_factor: 0.8    # Threshold adjustment

# Scanning
scan_all_bars: true              # Historical scanning (backtest mode)
scan_interval: 1                 # Evaluate every bar
```

---

## 📈 Performance Characteristics

### Expected Signal Frequency

**1-minute data (390 bars/day):**
- **Oversold signals:** 2-5 per day per symbol (0.5-1.3%)
- **Overbought signals:** 2-5 per day per symbol (0.5-1.3%)
- **Total:** ~12-30 signals per day (3 symbols)

**Why so infrequent?**
- Requires 3 conditions to align (zscore AND rsi AND bb_position)
- Confidence filter (60% minimum)
- Mean reversion is a rare statistical event (2+ std devs)

### Trade Duration

**Typical holding period:**
- **Entry:** Price at -2.0 std devs (oversold)
- **Exit:** Price at -0.5 std devs (near mean)
- **Duration:** 15-50 bars (15-50 minutes on 1-min data)
- **Movement:** ~1.5 std devs = $15 on $10 std dev stock

### Win Rate Expectations

**Academic benchmarks:**
- **Win rate:** 55-65% (mean reversion edge)
- **Profit factor:** 1.5-2.0 (2:1 reward/risk)
- **Sharpe ratio:** 1.0-2.0 (strong risk-adjusted returns)

---

## 🚨 Known Issues (Phase 1)

### Issue #1: Position Tracking Disconnect ⚠️
**Status:** FIXED (temporarily disabled check)  
**File:** Line 641-642  
**Problem:** Strategy's `active_positions` not synchronized with `CentralRiskManager`  
**Impact:** Strategy skips new signals if internal dict has symbol  
**Temporary Fix:** Removed position check to allow continuous signals  
**Production Fix:** Implement position update callbacks (see `WHY_STRATEGY_TRACKS_POSITIONS.md`)

### Issue #2: Exit Signal Integration ⚠️
**Status:** NEEDS REFACTORING  
**Problem:** Exit signals generated separately in `_check_exit_conditions()`  
**Impact:** Exit signals not passed through main signal flow  
**Recommendation:** Refactor to **Approach 3: Continuous Signal Stream**  
**Production Fix:** Generate both entry AND exit signals in `generate_signals()`

---

## 📚 Academic Foundations

### Statistical Mean Reversion
- **Ornstein-Uhlenbeck Process:** dX = θ(μ - X)dt + σdW
- **Half-life:** Time for price to revert halfway to mean
- **Speed of mean reversion:** θ parameter

### Bollinger Bands
- **John Bollinger (1980s):** Price envelope based on volatility
- **Lower band:** mean - 2σ (oversold)
- **Upper band:** mean + 2σ (overbought)
- **Squeeze:** Low volatility precedes expansion

### RSI (Relative Strength Index)
- **J. Welles Wilder (1978):** Momentum oscillator
- **Oversold:** RSI < 30 (strong selling pressure)
- **Overbought:** RSI > 70 (strong buying pressure)
- **Divergence:** Price vs RSI divergence signals reversals

---

## 🎯 Summary

**Signal Generation is a 8-Step Process:**

1. ✅ **Loop through symbols** (AAPL, TSLA, NVDA)
2. ✅ **Select mode** (Historical scan vs Live evaluation)
3. ✅ **Extract pre-calculated indicators** (Rule 3 compliance)
4. ✅ **Get regime-adjusted thresholds** (Regime-First principle)
5. ✅ **Apply regime filter** (Optional)
6. ✅ **Check entry conditions** (CORE ALPHA: 3-factor confluence)
7. ✅ **Calculate confidence** (5-factor weighted average)
8. ✅ **Create StrategySignal** (With percentage position sizing)

**Output:** `List[StrategySignal]` → Passed to StrategyManager (Phase 6, Rule 4)

**Key Insight:** Strategy is a **stateless signal generator** that reads pre-calculated indicators and applies alpha logic. It does NOT manage positions (that's `CentralRiskManager`'s job per Rule 4).

