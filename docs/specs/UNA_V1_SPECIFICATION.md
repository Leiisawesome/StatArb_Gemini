# Unified Novel Alpha (UNA) V1 Specification

**Version:** 1.0.0-DRAFT  
**Date:** December 5, 2025  
**Author:** StatArb_Gemini Team  
**Status:** DRAFT - Under Review

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Core Philosophy](#2-core-philosophy)
3. [Architecture Overview](#3-architecture-overview)
4. [Layer 1: Regime Engine](#4-layer-1-regime-engine)
5. [Layer 2: Force Analyzer](#5-layer-2-force-analyzer)
6. [Layer 3: Exhaustion Detector](#6-layer-3-exhaustion-detector)
7. [Layer 4: Multi-Timeframe Confluence](#7-layer-4-multi-timeframe-confluence)
8. [Layer 5: Signal Generator](#8-layer-5-signal-generator)
9. [Layer 6: Risk Filter](#9-layer-6-risk-filter)
10. [Position Management](#10-position-management)
11. [Exit Logic](#11-exit-logic)
12. [Failure Modes & Circuit Breakers](#12-failure-modes--circuit-breakers)
13. [Performance Metrics](#13-performance-metrics)
14. [Implementation Roadmap](#14-implementation-roadmap)
15. [Appendix](#15-appendix)

---

## 1. Executive Summary

### 1.1 What is UNA?

The **Unified Novel Alpha (UNA)** is a next-generation trading strategy that combines:
- **Trend Detection** (from Momentum strategies) - Understanding directional force
- **Exhaustion Detection** (from Mean Reversion strategies) - Timing entries at inflection points
- **Regime Awareness** - Adapting tactics to market conditions

### 1.2 Core Problem Statement

| Current Approach | Problem |
|------------------|---------|
| Pure Momentum | Enters late, buys high, sells low |
| Pure Mean Reversion | Catches falling knives, no trend filter |
| Static Parameters | Doesn't adapt to changing market conditions |

### 1.3 UNA Solution

> **"Identify the dominant market force, anticipate its exhaustion, and enter at the inflection point - with tactics adapted to the current regime."**

### 1.4 Target Performance Metrics

| Metric | Target | Stretch Goal |
|--------|--------|--------------|
| Sharpe Ratio | > 1.5 | > 2.0 |
| Win Rate | > 55% | > 60% |
| Profit Factor | > 1.5 | > 2.0 |
| Max Drawdown | < 10% | < 7% |
| Daily Hit Rate | > 60% | > 70% |
| Avg Trade Duration | 30-120 min | Optimized per regime |

---

## 2. Core Philosophy

### 2.1 The Force Model

Markets are driven by **forces** - aggregated buying and selling pressure. UNA's edge comes from:

1. **Detecting Force Direction** - Which side (buyers/sellers) is dominant?
2. **Measuring Force Strength** - How strong is the dominant force?
3. **Anticipating Force Exhaustion** - When will the dominant force run out of fuel?
4. **Entering at Inflection** - Position before the force reverses

### 2.2 Why This Works

```
Traditional Momentum:
Price: 100 → 105 → 110 → 115 (BUY signal at 115!)
Result: Bought near top, loses money

UNA Approach:
Price: 100 → 105 → 110 → 115 → 112 (pullback detected)
       ↑ Force = BULLISH (trend confirmed)
                           ↑ Selling force EXHAUSTING
       BUY at 112 → Ride to 120+
Result: Better entry, captures continuation
```

### 2.3 Key Principles

1. **Never chase** - Enter at pullbacks/exhaustion, not breakouts
2. **Regime-first** - Adapt tactics to market conditions
3. **Quality over quantity** - Fewer, higher-quality signals
4. **Exit is paramount** - 80% of edge is in exit logic
5. **Cost-aware** - Only trade when expected value > costs

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           UNA V1 ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    LAYER 1: REGIME ENGINE                           │   │
│   │  Trend Regime │ Volatility Regime │ Liquidity Regime │ Market Phase│   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    LAYER 2: FORCE ANALYZER                          │   │
│   │  Force Direction │ Force Strength │ Force Acceleration │ Force Source│  │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                  LAYER 3: EXHAUSTION DETECTOR                       │   │
│   │  Exhaustion Score │ Divergence │ Volume Profile │ Candle Analysis   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │               LAYER 4: MULTI-TIMEFRAME CONFLUENCE                   │   │
│   │  HTF Trend │ MTF Structure │ LTF Entry │ Confluence Score           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                   LAYER 5: SIGNAL GENERATOR                         │   │
│   │  Tactics Matrix │ Signal Type │ Quality Score │ Position Sizing     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     LAYER 6: RISK FILTER                            │   │
│   │  Position Limits │ Correlation │ Cost Analysis │ Circuit Breakers   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│                        AUTHORIZED SIGNAL OUTPUT                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Layer 1: Regime Engine

### 4.1 Purpose

Classify current market conditions to select appropriate tactics.

### 4.2 Regime Types

#### 4.2.1 Trend Regime

| State | Criteria | Implication |
|-------|----------|-------------|
| **STRONG_TREND** | ADX > 30, SMA_50 slope > 0.1%/bar | Use trend-following tactics |
| **WEAK_TREND** | 20 < ADX < 30 | Hybrid tactics |
| **RANGING** | ADX < 20, price within 2 ATR band | Mean reversion tactics |
| **CHOPPY** | ADX < 15, frequent direction changes | Reduce trading or sit out |

**Calculation:**
```python
def classify_trend_regime(adx: float, sma_slope: float, direction_changes: int) -> TrendRegime:
    if adx > 30 and abs(sma_slope) > 0.001:
        return TrendRegime.STRONG_TREND
    elif adx > 20:
        return TrendRegime.WEAK_TREND
    elif direction_changes > 5:  # per 20 bars
        return TrendRegime.CHOPPY
    else:
        return TrendRegime.RANGING
```

#### 4.2.2 Volatility Regime

| State | Criteria | Position Sizing Multiplier |
|-------|----------|---------------------------|
| **LOW_VOL** | ATR < 50th percentile (252-day) | 1.2x |
| **NORMAL_VOL** | ATR 50th-75th percentile | 1.0x |
| **HIGH_VOL** | ATR 75th-95th percentile | 0.7x |
| **EXTREME_VOL** | ATR > 95th percentile | 0.4x |

**Calculation:**
```python
def classify_volatility_regime(current_atr: float, atr_history: pd.Series) -> VolatilityRegime:
    percentile = stats.percentileofscore(atr_history, current_atr)
    
    if percentile < 50:
        return VolatilityRegime.LOW_VOL
    elif percentile < 75:
        return VolatilityRegime.NORMAL_VOL
    elif percentile < 95:
        return VolatilityRegime.HIGH_VOL
    else:
        return VolatilityRegime.EXTREME_VOL
```

#### 4.2.3 Liquidity Regime

| State | Criteria | Impact |
|-------|----------|--------|
| **HIGH_LIQUIDITY** | Volume > 150% of avg, tight spreads | Normal execution |
| **NORMAL_LIQUIDITY** | Volume 75-150% of avg | Normal execution |
| **LOW_LIQUIDITY** | Volume 25-75% of avg | Reduce size, wider stops |
| **ILLIQUID** | Volume < 25% of avg | No new entries |

#### 4.2.4 Market Phase (Wyckoff-Inspired)

| Phase | Characteristics | UNA Action |
|-------|----------------|------------|
| **ACCUMULATION** | Range-bound, declining volume, support holding | Prepare for long |
| **MARKUP** | Rising prices, increasing volume | Long bias |
| **DISTRIBUTION** | Range-bound, declining volume at highs | Prepare for short |
| **MARKDOWN** | Falling prices, increasing volume | Short bias or cash |

### 4.3 Regime Transition Detection

Not just current state, but **probability of transition**:

```python
@dataclass
class RegimeState:
    trend_regime: TrendRegime
    volatility_regime: VolatilityRegime
    liquidity_regime: LiquidityRegime
    market_phase: MarketPhase
    
    # Transition probabilities
    trend_transition_prob: float  # 0-1, probability of regime change
    vol_expansion_prob: float     # 0-1, probability of vol spike
    
    # Duration
    regime_duration_bars: int     # How long in current regime
    avg_regime_duration: int      # Historical average
```

### 4.4 Regime Output

```python
@dataclass
class RegimeContext:
    # Current states
    trend_regime: TrendRegime
    volatility_regime: VolatilityRegime
    liquidity_regime: LiquidityRegime
    market_phase: MarketPhase
    
    # Derived settings
    recommended_tactic: Tactic  # TREND_FOLLOW, MEAN_REVERT, HYBRID, DEFENSIVE
    position_size_multiplier: float  # 0.4 - 1.2
    stop_distance_multiplier: float  # 1.0 - 2.0
    entry_threshold_multiplier: float  # 0.8 - 1.5
    
    # Confidence
    regime_confidence: float  # 0-1, how confident in classification
    transition_risk: float  # 0-1, risk of imminent regime change
```

---

## 5. Layer 2: Force Analyzer

### 5.1 Purpose

Quantify the **dominant force** driving price movement.

### 5.2 Force Definition

**Force** = Aggregated directional pressure from market participants

### 5.3 Force Components

#### 5.3.1 Force Direction

| Direction | Criteria |
|-----------|----------|
| **BULLISH** | Net buying pressure dominant |
| **BEARISH** | Net selling pressure dominant |
| **NEUTRAL** | Balanced, no clear dominance |

#### 5.3.2 Force Strength (0-100 Scale)

Composite of multiple indicators:

```python
def calculate_force_strength(data: pd.DataFrame) -> float:
    """
    Calculate force strength on 0-100 scale.
    Higher = stronger directional force.
    """
    components = []
    weights = []
    
    # 1. ADX Component (25% weight)
    # ADX measures trend strength regardless of direction
    adx_score = min(data['adx'].iloc[-1] / 50 * 100, 100)  # Normalize to 0-100
    components.append(adx_score)
    weights.append(0.25)
    
    # 2. Momentum Magnitude Component (25% weight)
    # Absolute momentum relative to historical
    mom_percentile = stats.percentileofscore(
        abs(data['momentum_20']), 
        abs(data['momentum_20'].iloc[-1])
    )
    components.append(mom_percentile)
    weights.append(0.25)
    
    # 3. Volume Confirmation Component (20% weight)
    # Is volume confirming the move?
    volume_ratio = data['volume'].iloc[-1] / data['volume'].rolling(20).mean().iloc[-1]
    volume_score = min(volume_ratio * 50, 100)  # 2x avg volume = 100
    components.append(volume_score)
    weights.append(0.20)
    
    # 4. Price Velocity Component (15% weight)
    # Rate of price change
    returns_5 = data['close'].pct_change(5).iloc[-1]
    velocity_percentile = stats.percentileofscore(
        abs(data['close'].pct_change(5)),
        abs(returns_5)
    )
    components.append(velocity_percentile)
    weights.append(0.15)
    
    # 5. Directional Consistency Component (15% weight)
    # Are consecutive bars moving same direction?
    signs = np.sign(data['close'].diff().tail(10))
    consistency = abs(signs.sum()) / len(signs) * 100
    components.append(consistency)
    weights.append(0.15)
    
    # Weighted average
    force_strength = sum(c * w for c, w in zip(components, weights))
    
    return round(force_strength, 2)
```

#### 5.3.3 Force Acceleration

| State | Criteria | Implication |
|-------|----------|-------------|
| **ACCELERATING** | Force strength increasing | Trend strengthening |
| **STEADY** | Force strength stable | Trend continuing |
| **DECELERATING** | Force strength decreasing | Potential exhaustion |
| **REVERSING** | Force direction changing | Inflection point |

```python
def calculate_force_acceleration(force_history: List[float], lookback: int = 5) -> ForceAcceleration:
    """
    Calculate force acceleration (2nd derivative of force).
    """
    if len(force_history) < lookback:
        return ForceAcceleration.STEADY
    
    recent = force_history[-lookback:]
    
    # Linear regression slope of force strength
    x = np.arange(lookback)
    slope = np.polyfit(x, recent, 1)[0]
    
    if slope > 2:
        return ForceAcceleration.ACCELERATING
    elif slope < -2:
        return ForceAcceleration.DECELERATING
    elif abs(recent[-1] - recent[0]) > 20:  # Direction flip
        return ForceAcceleration.REVERSING
    else:
        return ForceAcceleration.STEADY
```

### 5.4 Force Output

```python
@dataclass
class ForceAnalysis:
    direction: ForceDirection  # BULLISH, BEARISH, NEUTRAL
    strength: float  # 0-100
    acceleration: ForceAcceleration  # ACCELERATING, STEADY, DECELERATING, REVERSING
    
    # Components breakdown
    adx_component: float
    momentum_component: float
    volume_component: float
    velocity_component: float
    consistency_component: float
    
    # Confidence
    analysis_confidence: float  # 0-1
```

---

## 6. Layer 3: Exhaustion Detector

### 6.1 Purpose

Detect when the dominant force is **running out of fuel** - the optimal entry point.

### 6.2 Exhaustion Score (0-100)

Composite score where **higher = more exhausted** (ready for reversal).

```python
def calculate_exhaustion_score(
    data: pd.DataFrame, 
    force: ForceAnalysis,
    regime: RegimeContext
) -> float:
    """
    Calculate exhaustion score on 0-100 scale.
    Higher = force more exhausted, reversal more likely.
    """
    components = []
    weights = []
    
    # 1. Z-Score Dislocation (25% weight)
    # How far from mean?
    zscore = (data['close'].iloc[-1] - data['close'].rolling(30).mean().iloc[-1]) / \
             data['close'].rolling(30).std().iloc[-1]
    zscore_score = min(abs(zscore) / 3 * 100, 100)  # 3 sigma = 100
    components.append(zscore_score)
    weights.append(0.25)
    
    # 2. RSI Extreme (20% weight)
    rsi = data['rsi'].iloc[-1]
    if force.direction == ForceDirection.BULLISH:
        # Bullish force exhaustion = overbought RSI
        rsi_score = max(0, (rsi - 50) / 50 * 100)  # RSI 100 = score 100
    else:
        # Bearish force exhaustion = oversold RSI
        rsi_score = max(0, (50 - rsi) / 50 * 100)  # RSI 0 = score 100
    components.append(rsi_score)
    weights.append(0.20)
    
    # 3. Volume Divergence (20% weight)
    # Price making new high/low but volume declining?
    price_new_extreme = _check_price_extreme(data, lookback=10)
    volume_declining = data['volume'].iloc[-1] < data['volume'].rolling(10).mean().iloc[-1] * 0.8
    
    if price_new_extreme and volume_declining:
        divergence_score = 80
    elif price_new_extreme:
        divergence_score = 40
    else:
        divergence_score = 20
    components.append(divergence_score)
    weights.append(0.20)
    
    # 4. Momentum Divergence (15% weight)
    # Price making new high but momentum lower?
    price_higher = data['close'].iloc[-1] > data['close'].iloc[-5]
    mom_lower = data['momentum_10'].iloc[-1] < data['momentum_10'].iloc[-5]
    
    if (price_higher and mom_lower) or (not price_higher and not mom_lower):
        mom_div_score = 70
    else:
        mom_div_score = 30
    components.append(mom_div_score)
    weights.append(0.15)
    
    # 5. Candle Body Analysis (10% weight)
    # Shrinking bodies = exhaustion
    body_size = abs(data['close'].iloc[-1] - data['open'].iloc[-1])
    avg_body = abs(data['close'] - data['open']).rolling(20).mean().iloc[-1]
    
    if body_size < avg_body * 0.5:
        candle_score = 80  # Small body = exhaustion
    elif body_size < avg_body * 0.8:
        candle_score = 50
    else:
        candle_score = 20
    components.append(candle_score)
    weights.append(0.10)
    
    # 6. Force Deceleration Bonus (10% weight)
    if force.acceleration == ForceAcceleration.DECELERATING:
        decel_score = 80
    elif force.acceleration == ForceAcceleration.REVERSING:
        decel_score = 100
    else:
        decel_score = 20
    components.append(decel_score)
    weights.append(0.10)
    
    # Weighted average
    exhaustion_score = sum(c * w for c, w in zip(components, weights))
    
    return round(exhaustion_score, 2)
```

### 6.3 Exhaustion Thresholds

| Score Range | Interpretation | Action |
|-------------|----------------|--------|
| 0-30 | Force still strong | No entry signal |
| 30-50 | Force weakening | Monitor closely |
| 50-70 | Moderate exhaustion | Entry candidate (lower confidence) |
| 70-85 | Strong exhaustion | High-quality entry signal |
| 85-100 | Extreme exhaustion | Strongest signal (may be late) |

### 6.4 Exhaustion Output

```python
@dataclass
class ExhaustionAnalysis:
    exhaustion_score: float  # 0-100
    exhaustion_level: ExhaustionLevel  # NONE, MODERATE, STRONG, EXTREME
    
    # Component breakdown
    zscore_component: float
    rsi_component: float
    volume_divergence: float
    momentum_divergence: float
    candle_component: float
    deceleration_component: float
    
    # Signals
    divergence_detected: bool
    reversal_candle_present: bool
    
    # Timing
    bars_since_exhaustion_start: int
```

---

## 7. Layer 4: Multi-Timeframe Confluence

### 7.1 Purpose

Ensure signals align across multiple timeframes for higher probability.

### 7.2 Timeframe Hierarchy

| Level | Timeframe | Purpose |
|-------|-----------|---------|
| **HTF (Higher)** | Daily / 4H | Trend direction, major levels |
| **MTF (Medium)** | 1H / 15min | Structure, support/resistance |
| **LTF (Lower)** | 5min / 1min | Entry timing, micro-structure |

### 7.3 Confluence Scoring

```python
def calculate_confluence_score(
    htf_analysis: TimeframeAnalysis,
    mtf_analysis: TimeframeAnalysis,
    ltf_analysis: TimeframeAnalysis,
    proposed_direction: ForceDirection
) -> float:
    """
    Calculate confluence score (0-100).
    Higher = more timeframes agree with proposed trade direction.
    """
    score = 0
    
    # HTF Alignment (40% weight)
    if htf_analysis.trend_direction == proposed_direction:
        score += 40
    elif htf_analysis.trend_direction == ForceDirection.NEUTRAL:
        score += 20  # Neutral is partial alignment
    # else: opposing HTF trend = 0 points
    
    # MTF Structure (30% weight)
    if mtf_analysis.at_support and proposed_direction == ForceDirection.BULLISH:
        score += 30  # Buying at support
    elif mtf_analysis.at_resistance and proposed_direction == ForceDirection.BEARISH:
        score += 30  # Selling at resistance
    elif mtf_analysis.trend_direction == proposed_direction:
        score += 20  # At least trend aligns
    
    # LTF Entry (30% weight)
    if ltf_analysis.entry_trigger_present:
        score += 20
    if ltf_analysis.trend_direction == proposed_direction:
        score += 10
    
    return score
```

### 7.4 Confluence Thresholds

| Score | Interpretation | Action |
|-------|----------------|--------|
| < 40 | Poor confluence | No trade |
| 40-60 | Moderate confluence | Trade with reduced size |
| 60-80 | Good confluence | Normal trade |
| 80-100 | Excellent confluence | Consider larger size |

### 7.5 Confluence Output

```python
@dataclass
class ConfluenceAnalysis:
    confluence_score: float  # 0-100
    confluence_level: ConfluenceLevel  # POOR, MODERATE, GOOD, EXCELLENT
    
    # Timeframe details
    htf_trend: ForceDirection
    htf_at_level: bool  # At major S/R
    
    mtf_trend: ForceDirection
    mtf_structure: str  # 'support', 'resistance', 'middle'
    
    ltf_trend: ForceDirection
    ltf_entry_trigger: bool
    
    # Conflicts
    timeframe_conflicts: List[str]  # Any conflicting signals
```

---

## 8. Layer 5: Signal Generator

### 8.1 Purpose

Combine all layers to generate final trading signals.

### 8.2 Tactics Matrix

Based on regime, select which tactic to apply:

| Trend Regime | Volatility | Tactic | Entry Style |
|--------------|------------|--------|-------------|
| STRONG_TREND | LOW/NORMAL | TREND_FOLLOW | Buy pullbacks to SMA |
| STRONG_TREND | HIGH | TREND_FOLLOW_CAUTIOUS | Tighter stops, smaller size |
| WEAK_TREND | LOW/NORMAL | HYBRID | Exhaustion at S/R levels |
| WEAK_TREND | HIGH | DEFENSIVE | Minimal trading |
| RANGING | LOW/NORMAL | MEAN_REVERT | Fade extremes |
| RANGING | HIGH | DEFENSIVE | Wait for clarity |
| CHOPPY | ANY | NO_TRADE | Sit out |

### 8.3 Signal Types

```python
class SignalType(Enum):
    BUY = "buy"           # New long position
    SCALE_IN = "scale_in" # Add to existing long
    HOLD = "hold"         # No action
    SCALE_OUT = "scale_out"  # Partial exit
    SELL = "sell"         # Full exit or new short
```

### 8.4 Signal Generation Logic

```python
def generate_signal(
    regime: RegimeContext,
    force: ForceAnalysis,
    exhaustion: ExhaustionAnalysis,
    confluence: ConfluenceAnalysis,
    current_position: Optional[Position]
) -> Signal:
    """
    Master signal generation logic.
    """
    
    # Step 1: Check if trading is allowed
    if regime.recommended_tactic == Tactic.NO_TRADE:
        return Signal(type=SignalType.HOLD, reason="Regime unfavorable")
    
    if confluence.confluence_score < 40:
        return Signal(type=SignalType.HOLD, reason="Poor confluence")
    
    # Step 2: Select tactic based on regime
    tactic = regime.recommended_tactic
    
    # Step 3: Generate signal based on tactic
    if tactic == Tactic.TREND_FOLLOW:
        return _generate_trend_follow_signal(force, exhaustion, confluence, current_position)
    
    elif tactic == Tactic.MEAN_REVERT:
        return _generate_mean_revert_signal(force, exhaustion, confluence, current_position)
    
    elif tactic == Tactic.HYBRID:
        return _generate_hybrid_signal(force, exhaustion, confluence, current_position, regime)
    
    elif tactic == Tactic.DEFENSIVE:
        return _generate_defensive_signal(current_position)
    
    return Signal(type=SignalType.HOLD, reason="No signal conditions met")


def _generate_hybrid_signal(
    force: ForceAnalysis,
    exhaustion: ExhaustionAnalysis,
    confluence: ConfluenceAnalysis,
    current_position: Optional[Position],
    regime: RegimeContext
) -> Signal:
    """
    HYBRID tactic: Use trend for direction, exhaustion for timing.
    This is UNA's primary edge.
    """
    
    # No position: Look for entry
    if current_position is None:
        
        # LONG ENTRY CONDITIONS:
        # 1. HTF trend is bullish (or neutral)
        # 2. Force direction is bullish
        # 3. Selling force is exhausting (we're at a pullback)
        # 4. Confluence is adequate
        
        bullish_entry = (
            force.direction == ForceDirection.BULLISH and
            exhaustion.exhaustion_score > 50 and  # Countertrend move exhausting
            confluence.confluence_score >= 50 and
            regime.market_phase in [MarketPhase.ACCUMULATION, MarketPhase.MARKUP]
        )
        
        if bullish_entry:
            quality = _calculate_signal_quality(force, exhaustion, confluence)
            
            return Signal(
                type=SignalType.BUY,
                direction=ForceDirection.BULLISH,
                quality_score=quality,
                confidence=min(exhaustion.exhaustion_score / 100, confluence.confluence_score / 100),
                reason="Hybrid: Pullback exhaustion in uptrend",
                entry_style="exhaustion_in_trend"
            )
        
        # SHORT ENTRY CONDITIONS (mirror of long)
        bearish_entry = (
            force.direction == ForceDirection.BEARISH and
            exhaustion.exhaustion_score > 50 and
            confluence.confluence_score >= 50 and
            regime.market_phase in [MarketPhase.DISTRIBUTION, MarketPhase.MARKDOWN]
        )
        
        if bearish_entry:
            quality = _calculate_signal_quality(force, exhaustion, confluence)
            
            return Signal(
                type=SignalType.SELL,
                direction=ForceDirection.BEARISH,
                quality_score=quality,
                confidence=min(exhaustion.exhaustion_score / 100, confluence.confluence_score / 100),
                reason="Hybrid: Rally exhaustion in downtrend",
                entry_style="exhaustion_in_trend"
            )
    
    # Has position: Check for scale-in or exit
    else:
        return _check_position_management(current_position, force, exhaustion, confluence)
    
    return Signal(type=SignalType.HOLD, reason="No entry conditions met")
```

### 8.5 Signal Quality Score

```python
def _calculate_signal_quality(
    force: ForceAnalysis,
    exhaustion: ExhaustionAnalysis,
    confluence: ConfluenceAnalysis
) -> float:
    """
    Calculate signal quality score (0-100).
    Higher = higher quality signal.
    """
    
    # Force clarity (20%)
    force_score = force.strength if force.direction != ForceDirection.NEUTRAL else 0
    
    # Exhaustion strength (35%)
    exhaustion_score = exhaustion.exhaustion_score
    
    # Confluence (30%)
    confluence_score = confluence.confluence_score
    
    # Timing bonus (15%)
    timing_bonus = 0
    if exhaustion.divergence_detected:
        timing_bonus += 50
    if exhaustion.reversal_candle_present:
        timing_bonus += 50
    
    # Weighted average
    quality = (
        force_score * 0.20 +
        exhaustion_score * 0.35 +
        confluence_score * 0.30 +
        timing_bonus * 0.15
    )
    
    return round(quality, 2)
```

### 8.6 Signal Output

```python
@dataclass
class Signal:
    type: SignalType  # BUY, SCALE_IN, HOLD, SCALE_OUT, SELL
    direction: Optional[ForceDirection]
    
    # Quality metrics
    quality_score: float  # 0-100
    confidence: float  # 0-1
    
    # Position sizing recommendation
    recommended_size_pct: float  # % of portfolio
    
    # Risk parameters
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    risk_reward_ratio: Optional[float]
    
    # Metadata
    reason: str
    entry_style: str  # 'exhaustion_in_trend', 'mean_revert', 'breakout', etc.
    timestamp: datetime
    
    # Layers that contributed
    regime_context: RegimeContext
    force_analysis: ForceAnalysis
    exhaustion_analysis: ExhaustionAnalysis
    confluence_analysis: ConfluenceAnalysis
```

---

## 9. Layer 6: Risk Filter

### 9.1 Purpose

Final gate before signal execution - ensure risk parameters are acceptable.

### 9.2 Risk Checks

```python
def apply_risk_filter(
    signal: Signal,
    portfolio: Portfolio,
    risk_limits: RiskLimits
) -> Tuple[bool, Signal, str]:
    """
    Apply risk filters to signal.
    Returns: (approved, modified_signal, rejection_reason)
    """
    
    # Check 1: Position limit
    if signal.type == SignalType.BUY:
        current_exposure = portfolio.get_exposure(signal.symbol)
        if current_exposure >= risk_limits.max_position_pct:
            return False, signal, "Position limit reached"
    
    # Check 2: Correlation check
    if signal.type in [SignalType.BUY, SignalType.SCALE_IN]:
        correlation = portfolio.calculate_correlation_with_existing(signal.symbol)
        if correlation > risk_limits.max_correlation:
            # Reduce size instead of reject
            signal.recommended_size_pct *= 0.5
    
    # Check 3: Cost-benefit analysis
    expected_profit = signal.recommended_size_pct * signal.confidence * 0.02  # Assume 2% target
    expected_cost = calculate_transaction_cost(signal)
    
    if expected_profit < expected_cost * 2:
        return False, signal, f"Expected profit ({expected_profit:.4f}) < 2x cost ({expected_cost:.4f})"
    
    # Check 4: Circuit breaker status
    if circuit_breaker.is_active():
        return False, signal, "Circuit breaker active"
    
    # Check 5: Daily loss limit
    if portfolio.daily_pnl < risk_limits.max_daily_loss:
        return False, signal, "Daily loss limit reached"
    
    # Check 6: Quality threshold
    if signal.quality_score < risk_limits.min_signal_quality:
        return False, signal, f"Quality score ({signal.quality_score}) below threshold"
    
    return True, signal, "Approved"
```

### 9.3 Risk Limits Configuration

```python
@dataclass
class RiskLimits:
    # Position limits
    max_position_pct: float = 0.10  # 10% max per position
    max_portfolio_exposure: float = 0.80  # 80% max total exposure
    max_correlation: float = 0.70  # Max correlation with existing positions
    
    # Loss limits
    max_daily_loss: float = -0.02  # -2% daily loss limit
    max_drawdown: float = -0.10  # -10% max drawdown
    
    # Signal quality
    min_signal_quality: float = 50.0  # Minimum quality score
    min_confluence: float = 40.0  # Minimum confluence score
    
    # Execution
    max_slippage_bps: float = 10.0  # Max acceptable slippage
```

---

## 10. Position Management

### 10.1 Position Sizing

```python
def calculate_position_size(
    signal: Signal,
    portfolio: Portfolio,
    regime: RegimeContext,
    risk_limits: RiskLimits
) -> float:
    """
    Calculate position size as % of portfolio.
    """
    
    # Base size from signal
    base_size = signal.recommended_size_pct
    
    # Adjust for regime
    regime_multiplier = regime.position_size_multiplier
    
    # Adjust for signal quality
    quality_multiplier = signal.quality_score / 100
    
    # Adjust for confluence
    confluence_multiplier = signal.confluence_analysis.confluence_score / 100
    
    # Calculate final size
    final_size = base_size * regime_multiplier * quality_multiplier * confluence_multiplier
    
    # Apply limits
    final_size = min(final_size, risk_limits.max_position_pct)
    
    # Ensure we have enough capital
    available_capital = portfolio.available_cash / portfolio.total_value
    final_size = min(final_size, available_capital * 0.95)  # Keep 5% buffer
    
    return round(final_size, 4)
```

### 10.2 Scale-In Rules

| Condition | Scale-In Size | Total Max Position |
|-----------|---------------|-------------------|
| Price moves in favor 1%, exhaustion still high | 50% of initial | 150% of initial |
| Price moves in favor 2%, trend confirmed | 50% of initial | 200% of initial |
| Max 2 scale-ins per position | - | 200% of initial |

```python
def check_scale_in(
    position: Position,
    current_price: float,
    exhaustion: ExhaustionAnalysis,
    regime: RegimeContext
) -> Optional[Signal]:
    """
    Check if scale-in is appropriate.
    """
    
    # Already at max scale-ins?
    if position.scale_in_count >= 2:
        return None
    
    # Price moved in favor?
    pnl_pct = position.unrealized_pnl_pct
    
    if pnl_pct < 0.01:  # Need at least 1% profit
        return None
    
    # Still have exhaustion (pullback in the move)?
    if exhaustion.exhaustion_score < 40:
        return None
    
    # Regime still favorable?
    if regime.recommended_tactic in [Tactic.DEFENSIVE, Tactic.NO_TRADE]:
        return None
    
    # Scale-in approved
    return Signal(
        type=SignalType.SCALE_IN,
        direction=position.direction,
        recommended_size_pct=position.size_pct * 0.5,  # 50% of original
        reason=f"Scale-in: +{pnl_pct:.1%} profit, exhaustion={exhaustion.exhaustion_score:.0f}"
    )
```

### 10.3 Position Tracking

```python
@dataclass
class Position:
    symbol: str
    direction: ForceDirection  # BULLISH = long, BEARISH = short
    
    # Size
    quantity: float
    size_pct: float  # % of portfolio
    
    # Entry
    entry_price: float
    entry_time: datetime
    entry_signal: Signal
    
    # Scale-ins
    scale_in_count: int = 0
    avg_entry_price: float = 0.0
    
    # Current state
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    # Stops
    initial_stop: float = 0.0
    current_stop: float = 0.0  # May trail
    take_profit: float = 0.0
    
    # Tracking
    high_water_mark: float = 0.0
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0
    holding_duration_bars: int = 0
```

---

## 11. Exit Logic

### 11.1 Exit Priority Order

Exits are checked in priority order - first matching rule triggers exit:

| Priority | Exit Type | Trigger | Action |
|----------|-----------|---------|--------|
| 1 | **Emergency Stop** | Circuit breaker / system halt | Immediate market exit |
| 2 | **Hard Stop Loss** | Price hits initial stop | Market exit |
| 3 | **Trailing Stop** | Price hits trailing stop | Market exit |
| 4 | **Take Profit** | Price hits target | Limit exit |
| 5 | **Regime Exit** | Regime turns unfavorable | Orderly exit |
| 6 | **Exhaustion Exit** | Opposite exhaustion detected | Orderly exit |
| 7 | **Time Exit** | Max holding period | Orderly exit |
| 8 | **EOD Exit** | End of day (if intraday) | Market exit |

### 11.2 Exit Implementation

```python
async def check_exits(
    position: Position,
    current_data: pd.DataFrame,
    regime: RegimeContext,
    force: ForceAnalysis,
    exhaustion: ExhaustionAnalysis
) -> Optional[Signal]:
    """
    Check all exit conditions in priority order.
    """
    
    current_price = current_data['close'].iloc[-1]
    
    # Priority 1: Emergency (handled by circuit breaker)
    
    # Priority 2: Hard Stop Loss
    if position.direction == ForceDirection.BULLISH:
        if current_price <= position.initial_stop:
            return Signal(
                type=SignalType.SELL,
                reason="Hard stop loss hit",
                urgency="immediate"
            )
    else:  # Short
        if current_price >= position.initial_stop:
            return Signal(
                type=SignalType.BUY,  # Cover
                reason="Hard stop loss hit",
                urgency="immediate"
            )
    
    # Priority 3: Trailing Stop
    if position.current_stop != position.initial_stop:
        if position.direction == ForceDirection.BULLISH:
            if current_price <= position.current_stop:
                return Signal(
                    type=SignalType.SELL,
                    reason=f"Trailing stop hit at {position.current_stop:.2f}",
                    urgency="immediate"
                )
    
    # Priority 4: Take Profit
    if position.direction == ForceDirection.BULLISH:
        if current_price >= position.take_profit:
            return Signal(
                type=SignalType.SELL,
                reason="Take profit target reached",
                urgency="normal"
            )
    
    # Priority 5: Regime Exit
    if regime.recommended_tactic in [Tactic.NO_TRADE, Tactic.DEFENSIVE]:
        if regime.transition_risk > 0.7:
            return Signal(
                type=SignalType.SELL if position.direction == ForceDirection.BULLISH else SignalType.BUY,
                reason=f"Regime exit: {regime.trend_regime.value}, transition_risk={regime.transition_risk:.2f}",
                urgency="normal"
            )
    
    # Priority 6: Exhaustion Exit (opposite force exhausting)
    if position.direction == ForceDirection.BULLISH:
        # Exit long when buying force exhausts (at a high)
        if force.direction == ForceDirection.BULLISH and exhaustion.exhaustion_score > 70:
            if position.unrealized_pnl_pct > 0:  # Only if profitable
                return Signal(
                    type=SignalType.SELL,
                    reason=f"Exhaustion exit: score={exhaustion.exhaustion_score:.0f}",
                    urgency="normal"
                )
    
    # Priority 7: Time Exit
    if position.holding_duration_bars > MAX_HOLDING_BARS:
        return Signal(
            type=SignalType.SELL if position.direction == ForceDirection.BULLISH else SignalType.BUY,
            reason=f"Time exit: held {position.holding_duration_bars} bars",
            urgency="normal"
        )
    
    # Priority 8: EOD Exit (if configured)
    if is_near_market_close() and config.enable_eod_exit:
        return Signal(
            type=SignalType.SELL if position.direction == ForceDirection.BULLISH else SignalType.BUY,
            reason="EOD liquidation",
            urgency="normal"
        )
    
    return None  # No exit
```

### 11.3 Trailing Stop Logic

```python
def update_trailing_stop(
    position: Position,
    current_price: float,
    atr: float,
    config: TrailingStopConfig
) -> float:
    """
    Update trailing stop based on price movement.
    """
    
    if position.direction == ForceDirection.BULLISH:
        # Long position
        # Activate trailing stop after X ATR profit
        profit_atr = (current_price - position.entry_price) / atr
        
        if profit_atr >= config.activation_atr:
            # Trailing stop = high_water_mark - (trail_distance * ATR)
            new_stop = position.high_water_mark - (config.trail_distance_atr * atr)
            
            # Only move stop UP, never down
            if new_stop > position.current_stop:
                return new_stop
    
    else:
        # Short position (mirror logic)
        profit_atr = (position.entry_price - current_price) / atr
        
        if profit_atr >= config.activation_atr:
            new_stop = position.low_water_mark + (config.trail_distance_atr * atr)
            
            if new_stop < position.current_stop:
                return new_stop
    
    return position.current_stop  # No change


@dataclass
class TrailingStopConfig:
    activation_atr: float = 2.0  # Activate after 2 ATR profit
    trail_distance_atr: float = 1.5  # Trail 1.5 ATR behind
```

### 11.4 Scale-Out Rules

```python
def check_scale_out(
    position: Position,
    current_price: float,
    config: ScaleOutConfig
) -> Optional[Signal]:
    """
    Check if partial profit taking is appropriate.
    """
    
    pnl_pct = position.unrealized_pnl_pct
    
    # Scale out at predefined R-multiples
    if position.direction == ForceDirection.BULLISH:
        risk = position.entry_price - position.initial_stop
        reward = current_price - position.entry_price
        r_multiple = reward / risk if risk > 0 else 0
        
        # First scale-out at 1R
        if r_multiple >= 1.0 and position.scale_out_count == 0:
            return Signal(
                type=SignalType.SCALE_OUT,
                recommended_size_pct=position.size_pct * 0.33,  # Exit 1/3
                reason=f"Scale-out at {r_multiple:.1f}R"
            )
        
        # Second scale-out at 2R
        if r_multiple >= 2.0 and position.scale_out_count == 1:
            return Signal(
                type=SignalType.SCALE_OUT,
                recommended_size_pct=position.size_pct * 0.50,  # Exit half of remaining
                reason=f"Scale-out at {r_multiple:.1f}R"
            )
    
    return None
```

---

## 12. Failure Modes & Circuit Breakers

### 12.1 Circuit Breaker Triggers

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Daily Loss | > -2% | Halt new entries |
| Drawdown | > -5% | Halt trading, alert |
| Drawdown | > -10% | Flatten all positions |
| Order Rate | > 10/second | Throttle |
| Consecutive Losses | > 5 | Review required |
| Flash Crash | > 5% move in 5 min | Halt + flatten |

### 12.2 Circuit Breaker Implementation

```python
@dataclass
class CircuitBreakerState:
    is_active: bool = False
    trigger_reason: Optional[str] = None
    trigger_time: Optional[datetime] = None
    
    # Levels
    level: CircuitBreakerLevel = CircuitBreakerLevel.NORMAL
    
    # Actions
    new_entries_allowed: bool = True
    exits_allowed: bool = True
    position_reduction_required: bool = False
    flatten_required: bool = False


class CircuitBreakerLevel(Enum):
    NORMAL = "normal"
    WARNING = "warning"  # Approaching limits
    CAUTION = "caution"  # At limits, no new entries
    HALT = "halt"  # Flatten positions
    EMERGENCY = "emergency"  # System shutdown


def check_circuit_breakers(
    portfolio: Portfolio,
    market_data: pd.DataFrame,
    config: CircuitBreakerConfig
) -> CircuitBreakerState:
    """
    Check all circuit breaker conditions.
    """
    
    state = CircuitBreakerState()
    
    # Check daily loss
    if portfolio.daily_pnl_pct <= config.daily_loss_halt:
        state.level = CircuitBreakerLevel.CAUTION
        state.new_entries_allowed = False
        state.trigger_reason = f"Daily loss {portfolio.daily_pnl_pct:.2%} exceeded limit"
    
    # Check drawdown
    if portfolio.current_drawdown <= config.drawdown_flatten:
        state.level = CircuitBreakerLevel.HALT
        state.flatten_required = True
        state.trigger_reason = f"Drawdown {portfolio.current_drawdown:.2%} exceeded flatten limit"
    
    # Check for flash crash
    if market_data is not None:
        recent_move = market_data['close'].pct_change(5).iloc[-1]  # 5-bar move
        if abs(recent_move) > config.flash_crash_threshold:
            state.level = CircuitBreakerLevel.HALT
            state.flatten_required = True
            state.trigger_reason = f"Flash crash detected: {recent_move:.2%} in 5 bars"
    
    # Check order rate (would need order tracking)
    # ... implementation ...
    
    state.is_active = state.level != CircuitBreakerLevel.NORMAL
    
    return state
```

### 12.3 Recovery Procedures

| Scenario | Recovery Steps |
|----------|----------------|
| Daily Loss Halt | Wait until next trading day |
| Drawdown Caution | Reduce position sizes 50%, review signals |
| Drawdown Halt | Flatten all, 24-hour cooldown, full review |
| Flash Crash | Flatten, wait for volatility to normalize |
| System Error | Halt trading, technical review |

---

## 13. Performance Metrics

### 13.1 Key Performance Indicators (KPIs)

```python
@dataclass
class PerformanceMetrics:
    # Returns
    total_return: float
    annualized_return: float
    daily_returns: List[float]
    
    # Risk-Adjusted
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Drawdown
    max_drawdown: float
    avg_drawdown: float
    drawdown_duration_days: int
    
    # Trade Statistics
    total_trades: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    
    # Execution Quality
    avg_slippage_bps: float
    avg_fill_rate: float
    
    # Signal Quality
    signal_hit_rate_by_quality: Dict[str, float]  # {'high': 0.65, 'medium': 0.55}
    avg_signal_quality: float
    
    # Regime Performance
    performance_by_regime: Dict[str, float]  # {'STRONG_TREND': 0.03, 'RANGING': 0.01}
```

### 13.2 Success Criteria

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| Sharpe Ratio | 1.0 | 1.5 | 2.0+ |
| Win Rate | 50% | 55% | 60%+ |
| Profit Factor | 1.3 | 1.5 | 2.0+ |
| Max Drawdown | < 15% | < 10% | < 7% |
| Avg Trade Duration | 30-180 min | 45-120 min | Optimized |
| Signal Quality Corr | > 0.3 | > 0.5 | > 0.7 |

### 13.3 Monitoring Dashboard

Required real-time metrics:
- Current P&L (daily, weekly, monthly)
- Current drawdown
- Active positions summary
- Signal quality distribution (last 20 signals)
- Regime status
- Circuit breaker status

---

## 14. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

| Task | Priority | Status |
|------|----------|--------|
| Define data structures (dataclasses) | P0 | TODO |
| Implement Regime Engine | P0 | TODO |
| Unit tests for Regime Engine | P0 | TODO |
| Implement Force Analyzer | P0 | TODO |
| Unit tests for Force Analyzer | P0 | TODO |

### Phase 2: Core Logic (Week 3-4)

| Task | Priority | Status |
|------|----------|--------|
| Implement Exhaustion Detector | P0 | TODO |
| Implement Multi-Timeframe Confluence | P1 | TODO |
| Implement Signal Generator | P0 | TODO |
| Implement Risk Filter | P0 | TODO |
| Integration tests | P0 | TODO |

### Phase 3: Position Management (Week 5)

| Task | Priority | Status |
|------|----------|--------|
| Position sizing logic | P0 | TODO |
| Scale-in logic | P1 | TODO |
| Exit priority system | P0 | TODO |
| Trailing stop logic | P1 | TODO |
| Scale-out logic | P1 | TODO |

### Phase 4: Safety & Monitoring (Week 6)

| Task | Priority | Status |
|------|----------|--------|
| Circuit breakers | P0 | TODO |
| Performance tracking | P0 | TODO |
| Logging & audit trail | P0 | TODO |
| Alerting system | P1 | TODO |

### Phase 5: Backtesting & Optimization (Week 7-8)

| Task | Priority | Status |
|------|----------|--------|
| Historical backtest | P0 | TODO |
| Parameter optimization | P1 | TODO |
| Walk-forward validation | P1 | TODO |
| Stress testing | P1 | TODO |
| Performance report | P0 | TODO |

### Phase 6: Paper Trading (Week 9-10)

| Task | Priority | Status |
|------|----------|--------|
| Paper trading integration | P0 | TODO |
| Live monitoring | P0 | TODO |
| Performance comparison | P0 | TODO |
| Final adjustments | P1 | TODO |

---

## 15. Appendix

### A. Configuration File Template

```yaml
# UNA V1 Configuration
una_config:
  version: "1.0.0"
  
  # Regime Engine
  regime:
    trend:
      strong_trend_adx: 30
      weak_trend_adx: 20
      choppy_direction_changes: 5
    volatility:
      low_percentile: 50
      high_percentile: 75
      extreme_percentile: 95
    liquidity:
      high_volume_ratio: 1.5
      low_volume_ratio: 0.5
  
  # Force Analyzer
  force:
    weights:
      adx: 0.25
      momentum: 0.25
      volume: 0.20
      velocity: 0.15
      consistency: 0.15
  
  # Exhaustion Detector
  exhaustion:
    weights:
      zscore: 0.25
      rsi: 0.20
      volume_divergence: 0.20
      momentum_divergence: 0.15
      candle: 0.10
      deceleration: 0.10
    thresholds:
      moderate: 50
      strong: 70
      extreme: 85
  
  # Signal Generator
  signals:
    min_confluence: 40
    min_quality: 50
    
  # Position Management
  position:
    base_size_pct: 0.05
    max_size_pct: 0.10
    max_scale_ins: 2
    scale_in_size_ratio: 0.5
  
  # Exits
  exits:
    initial_stop_atr: 2.0
    trailing_activation_atr: 2.0
    trailing_distance_atr: 1.5
    take_profit_atr: 4.0
    max_holding_bars: 200
    enable_eod_exit: true
  
  # Risk
  risk:
    max_daily_loss: -0.02
    max_drawdown: -0.10
    flatten_drawdown: -0.15
    max_correlation: 0.70
```

### B. Signal Quality Lookup Table

| Force Strength | Exhaustion Score | Confluence | Quality Score | Recommendation |
|----------------|------------------|------------|---------------|----------------|
| > 70 | > 70 | > 70 | 85+ | Strong trade |
| > 70 | > 70 | 50-70 | 70-85 | Good trade |
| > 70 | 50-70 | > 70 | 65-75 | Moderate trade |
| 50-70 | > 70 | > 70 | 60-70 | Moderate trade |
| < 50 | ANY | ANY | < 50 | No trade |
| ANY | < 50 | ANY | < 50 | No trade |
| ANY | ANY | < 40 | < 40 | No trade |

### C. Regime-Tactics Decision Matrix

| Trend | Volatility | Liquidity | Tactic | Position Mult | Notes |
|-------|------------|-----------|--------|---------------|-------|
| STRONG | LOW | HIGH | TREND_FOLLOW | 1.2 | Best conditions |
| STRONG | LOW | NORMAL | TREND_FOLLOW | 1.0 | Good conditions |
| STRONG | NORMAL | HIGH | TREND_FOLLOW | 1.0 | Good conditions |
| STRONG | NORMAL | NORMAL | TREND_FOLLOW | 0.9 | Normal |
| STRONG | HIGH | ANY | TREND_CAUTIOUS | 0.7 | Wider stops |
| WEAK | LOW | HIGH | HYBRID | 1.0 | UNA sweet spot |
| WEAK | LOW | NORMAL | HYBRID | 0.9 | UNA sweet spot |
| WEAK | NORMAL | ANY | HYBRID | 0.8 | Selective |
| WEAK | HIGH | ANY | DEFENSIVE | 0.5 | Minimal trading |
| RANGING | LOW | HIGH | MEAN_REVERT | 1.0 | Good for MR |
| RANGING | LOW | NORMAL | MEAN_REVERT | 0.9 | Good for MR |
| RANGING | NORMAL | ANY | MEAN_REVERT | 0.7 | Careful |
| RANGING | HIGH | ANY | DEFENSIVE | 0.4 | Avoid |
| CHOPPY | ANY | ANY | NO_TRADE | 0.0 | Sit out |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0-DRAFT | 2025-12-05 | StatArb Team | Initial draft |

---

**END OF SPECIFICATION**
