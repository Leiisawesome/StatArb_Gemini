"""
Simplified Alpha Components - v5.0 Refactored
==============================================

This module implements the expert-recommended simplification of the alpha system.

Key Changes from v4.0:
1. UNIFIED REVERSAL SCORE: Replaces multiplicative SMS + 5-factor exhaustion + ERAR
   with a single additive model using 4 orthogonal features
2. REGIME-CONDITIONED Z-SCORE: Uses median/MAD instead of mean/std, with volatility floor
3. SIMPLE EDGE RATIO: Replaces complex ERAR CVaR modeling with simple heuristic

Design Philosophy (per expert review):
- "If it can't make money without stacked filters, there is no real edge."
- "Mean reversion succeeds because it's simple, fast, and brutally disciplined."
- Features must be ORTHOGONAL, not correlated versions of the same signal.

4 Orthogonal Dimensions:
1. STRETCH: Regime-adjusted z-score (distance from fair value)
2. EXHAUSTION: Volume-weighted momentum decay (using RSI momentum only)
3. FLOW: Order flow imbalance (volume direction)
4. VOLATILITY: ATR compression ratio

Author: StatArb_Gemini Architecture Compliance
Version: 5.0.0 (Expert Review Simplification)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# UNIFIED REVERSAL SCORE (Replaces SMS + 5-factor + ERAR)
# =============================================================================

@dataclass
class UnifiedReversalScore:
    """
    Unified Reversal Score using 4 orthogonal features with additive model.
    
    Replaces:
    - Multiplicative SMS (fragile, one weak factor zeros everything)
    - 5-factor exhaustion score (correlated indicators)
    - ERAR (false precision with garbage data)
    
    Formula (additive, robust):
        score = w_stretch × stretch_norm + 
                w_exhaustion × exhaustion_norm + 
                w_flow × flow_norm + 
                w_volatility × vol_norm
    
    Each factor is normalized to [0, 1] with sigmoid smoothing.
    """
    
    # Default weights (sum to 1.0)
    WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        'stretch': 0.35,      # Distance from fair value (primary signal)
        'exhaustion': 0.30,   # Momentum decay
        'flow': 0.20,         # Order flow direction
        'volatility': 0.15    # Volatility state
    })
    
    # Regime-adaptive weights (slight adjustment)
    REGIME_WEIGHTS: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'low_vol': {'stretch': 0.40, 'exhaustion': 0.25, 'flow': 0.20, 'volatility': 0.15},
        'normal': {'stretch': 0.35, 'exhaustion': 0.30, 'flow': 0.20, 'volatility': 0.15},
        'high_vol': {'stretch': 0.30, 'exhaustion': 0.30, 'flow': 0.25, 'volatility': 0.15},
        'crisis': {'stretch': 0.25, 'exhaustion': 0.35, 'flow': 0.25, 'volatility': 0.15}
    })
    
    def compute(
        self,
        stretch: float,
        exhaustion: float,
        flow: float,
        volatility: float,
        regime: str = 'normal'
    ) -> Tuple[float, Dict[str, float]]:
        """
        Compute unified reversal score.
        
        Args:
            stretch: Regime-adjusted z-score magnitude [0, 5+]
            exhaustion: Momentum exhaustion signal [0, 1]
            flow: Order flow signal [-1, 1] (positive = favorable)
            volatility: Volatility compression ratio [0.5, 2.0] (lower = better)
            regime: Market regime for weight selection
            
        Returns:
            Tuple of (score [0, 1], component breakdown)
        """
        weights = self.REGIME_WEIGHTS.get(regime, self.WEIGHTS)
        
        # Normalize each factor to [0, 1] with sigmoid smoothing
        stretch_norm = self._sigmoid_normalize(stretch, threshold=2.0, steepness=1.5)
        exhaustion_norm = np.clip(exhaustion, 0.0, 1.0)
        flow_norm = self._sigmoid_normalize(flow + 1.0, threshold=1.0, steepness=2.0)  # Shift to [0, 2]
        vol_norm = self._sigmoid_normalize(2.0 - volatility, threshold=0.5, steepness=2.0)  # Lower vol = higher score
        
        # Additive combination (robust - one weak factor doesn't kill signal)
        score = (
            weights['stretch'] * stretch_norm +
            weights['exhaustion'] * exhaustion_norm +
            weights['flow'] * flow_norm +
            weights['volatility'] * vol_norm
        )
        
        breakdown = {
            'stretch_raw': stretch,
            'stretch_norm': stretch_norm,
            'stretch_contrib': weights['stretch'] * stretch_norm,
            'exhaustion_raw': exhaustion,
            'exhaustion_norm': exhaustion_norm,
            'exhaustion_contrib': weights['exhaustion'] * exhaustion_norm,
            'flow_raw': flow,
            'flow_norm': flow_norm,
            'flow_contrib': weights['flow'] * flow_norm,
            'volatility_raw': volatility,
            'volatility_norm': vol_norm,
            'volatility_contrib': weights['volatility'] * vol_norm,
            'total_score': score
        }
        
        return np.clip(score, 0.0, 1.0), breakdown
    
    @staticmethod
    def _sigmoid_normalize(x: float, threshold: float, steepness: float) -> float:
        """Apply sigmoid normalization centered at threshold."""
        return 1.0 / (1.0 + np.exp(-steepness * (x - threshold)))
    
    def should_trade(self, score: float, threshold: float = 0.5) -> bool:
        """Check if score meets trading threshold."""
        return score >= threshold


# =============================================================================
# REGIME-CONDITIONED Z-SCORE (Robust alternative to rolling mean/std)
# =============================================================================

@dataclass
class RegimeAdjustedZScore:
    """
    Regime-conditioned z-score using median/MAD.
    
    Problems with naive rolling z-score:
    - Assumes stationarity (volatility clusters violate this)
    - Mean drifts, std explodes/collapses
    - Heavy-tailed distributions cause spurious extremes
    - Volatility compression → fake extreme z-scores
    
    Fixes:
    1. Median/MAD instead of mean/std (robust to outliers)
    2. Regime-conditioned expansion of threshold when vol compressed
    3. Volatility floor to prevent signal explosion
    """
    
    # Scaling factor: MAD to std (for normal distribution, MAD ≈ 0.6745 * std)
    MAD_SCALE: float = 1.4826  # 1/0.6745
    
    # Volatility floor: minimum vol ratio before threshold expansion
    VOL_FLOOR: float = 0.5
    
    def compute(
        self,
        prices: np.ndarray,
        lookback: int = 20,
        current_atr: float = None,
        baseline_atr: float = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Compute regime-adjusted z-score.
        
        Args:
            prices: Price array (most recent at end)
            lookback: Lookback period for median/MAD
            current_atr: Current ATR (for regime conditioning)
            baseline_atr: Baseline ATR (for regime conditioning)
            
        Returns:
            Tuple of (zscore, diagnostics dict)
        """
        if len(prices) < lookback:
            return 0.0, {'error': 'insufficient_data'}
        
        window = prices[-lookback:]
        current_price = prices[-1]
        
        # Robust center: median instead of mean
        median = np.median(window)
        
        # Robust spread: MAD instead of std
        mad = np.median(np.abs(window - median))
        scaled_mad = mad * self.MAD_SCALE  # Scale to std-equivalent
        
        # Volatility floor: prevent division by tiny number
        if scaled_mad < 0.001 * median:  # Less than 0.1% of price
            scaled_mad = 0.001 * median
        
        # Base z-score
        zscore = (current_price - median) / scaled_mad
        
        # Regime conditioning: expand threshold when vol compressed
        vol_ratio = 1.0
        if current_atr is not None and baseline_atr is not None and baseline_atr > 0:
            vol_ratio = current_atr / baseline_atr
            # Floor the vol ratio to prevent signal explosion
            vol_ratio = max(vol_ratio, self.VOL_FLOOR)
            # Adjust spread for regime
            adjusted_spread = scaled_mad * vol_ratio
            zscore = (current_price - median) / adjusted_spread
        
        diagnostics = {
            'median': median,
            'mad': mad,
            'scaled_mad': scaled_mad,
            'vol_ratio': vol_ratio,
            'raw_zscore': (current_price - median) / scaled_mad,
            'adjusted_zscore': zscore
        }
        
        return zscore, diagnostics


# =============================================================================
# SIMPLE EDGE RATIO (Replaces complex ERAR)
# =============================================================================

@dataclass
class SimpleEdgeRatio:
    """
    Simple edge ratio heuristic.
    
    Why this replaces ERAR:
    - Expected return estimation on short-horizon MR is garbage
    - CVaR on small samples is garbage squared
    - Skew estimation at short horizon is not statistically stable
    - MR edges are small; expectancy comes from frequency × tight execution
    
    Simple formula:
        edge_ratio = (avg_win × win_rate) / (avg_loss × (1 - win_rate))
        
    If edge_ratio < 1.2, don't trade (insufficient edge).
    """
    
    # Trade history for rolling calculation
    trade_pnls: list = field(default_factory=list)
    
    # Configuration
    min_trades: int = 10  # Minimum trades for valid estimate
    lookback: int = 50    # Rolling window for edge calculation
    
    def update(self, pnl: float):
        """Add trade PnL to history."""
        self.trade_pnls.append(pnl)
        # Keep only lookback window
        if len(self.trade_pnls) > self.lookback:
            self.trade_pnls = self.trade_pnls[-self.lookback:]
    
    def compute(self) -> Tuple[float, Dict[str, float]]:
        """
        Compute simple edge ratio.
        
        Returns:
            Tuple of (edge_ratio, diagnostics)
        """
        if len(self.trade_pnls) < self.min_trades:
            return 1.5, {'status': 'insufficient_data', 'trades': len(self.trade_pnls)}
        
        wins = [p for p in self.trade_pnls if p > 0]
        losses = [p for p in self.trade_pnls if p <= 0]
        
        win_rate = len(wins) / len(self.trade_pnls) if self.trade_pnls else 0.5
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = abs(np.mean(losses)) if losses else 1.0
        
        # Prevent division by zero
        if avg_loss < 0.01:
            avg_loss = 0.01
        if win_rate >= 1.0:
            win_rate = 0.99
        
        # Edge ratio formula
        edge_ratio = (avg_win * win_rate) / (avg_loss * (1 - win_rate))
        
        diagnostics = {
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'edge_ratio': edge_ratio,
            'trades': len(self.trade_pnls)
        }
        
        return edge_ratio, diagnostics
    
    def should_trade(self, threshold: float = 1.2) -> bool:
        """Check if edge ratio meets minimum threshold."""
        ratio, _ = self.compute()
        return ratio >= threshold


# =============================================================================
# EXHAUSTION CALCULATOR (Simplified - single measure)
# =============================================================================

def compute_momentum_exhaustion(
    rsi: float,
    rsi_prev: float,
    is_oversold: bool
) -> float:
    """
    Compute momentum exhaustion using RSI momentum only.
    
    Why only RSI momentum:
    - RSI, MACD histogram, stochastic are all ~80% correlated
    - Using all three is triple-counting the same effect
    - RSI momentum (direction change) is the most reliable exhaustion signal
    
    Args:
        rsi: Current RSI value
        rsi_prev: Previous RSI value
        is_oversold: True if looking for bullish exhaustion
        
    Returns:
        Exhaustion score [0, 1]
    """
    base = 0.3  # Neutral baseline
    
    # RSI extremity
    if is_oversold:
        if rsi < 20:
            base += 0.3  # Extreme oversold
        elif rsi < 30:
            base += 0.2  # Oversold
    else:
        if rsi > 80:
            base += 0.3  # Extreme overbought
        elif rsi > 70:
            base += 0.2  # Overbought
    
    # RSI momentum reversal (the key signal)
    rsi_change = rsi - rsi_prev
    if is_oversold and rsi_change > 0:
        # RSI rising from oversold = bullish exhaustion
        base += min(rsi_change / 10.0, 0.3)
    elif not is_oversold and rsi_change < 0:
        # RSI falling from overbought = bearish exhaustion
        base += min(abs(rsi_change) / 10.0, 0.3)
    
    return np.clip(base, 0.0, 1.0)


def compute_flow_signal(
    volume_ratio: float,
    price_change_pct: float,
    is_oversold: bool
) -> float:
    """
    Compute order flow signal from volume and price action.
    
    For mean reversion:
    - Low volume at extremes = noise, will revert (favorable)
    - High volume breakout = information, don't fade (unfavorable)
    - Volume climax (high volume + price reversal) = exhaustion (favorable)
    
    Args:
        volume_ratio: Current volume / average volume
        price_change_pct: Price change percentage (positive = up)
        is_oversold: True if looking for long entry
        
    Returns:
        Flow signal [-1, 1] (positive = favorable for reversion)
    """
    # Base: low volume = favorable
    if volume_ratio < 0.8:
        flow = 0.5  # Low volume extreme = noise
    elif volume_ratio > 2.0:
        # High volume - check if it's breakout or climax
        if is_oversold and price_change_pct > 0:
            flow = 0.7  # Selling climax with bounce = favorable
        elif not is_oversold and price_change_pct < 0:
            flow = 0.7  # Buying climax with reversal = favorable
        else:
            flow = -0.5  # High volume continuation = unfavorable
    else:
        flow = 0.0  # Neutral
    
    return np.clip(flow, -1.0, 1.0)


def compute_volatility_signal(
    current_atr: float,
    baseline_atr: float
) -> float:
    """
    Compute volatility signal (compression ratio).
    
    Lower volatility compression = more favorable for mean reversion.
    
    Args:
        current_atr: Recent ATR (e.g., 5-bar)
        baseline_atr: Baseline ATR (e.g., 20-bar)
        
    Returns:
        Volatility compression ratio [0.5, 2.0]
    """
    if baseline_atr <= 0:
        return 1.0
    
    ratio = current_atr / baseline_atr
    return np.clip(ratio, 0.5, 2.0)


# =============================================================================
# THESIS INVALIDATION CHECKER (For exit logic)
# =============================================================================

@dataclass
class ThesisInvalidation:
    """
    Check if mean reversion thesis is invalidated.
    
    Exit conditions (NOT PnL-based):
    1. TIME: Position held too long (thesis expired)
    2. TREND: Trend accelerated instead of reverting
    3. REGIME: Volatility regime shifted significantly
    
    NOT exit conditions:
    - PnL-based stops (fight the alpha)
    - Z-score returning to normal (may still have room to run)
    """
    
    max_hold_bars: int = 20  # Maximum bars to hold
    trend_acceleration_threshold: float = 1.5  # ADX increase threshold
    regime_shift_threshold: float = 2.0  # Vol ratio change threshold
    
    def is_invalidated(
        self,
        bars_held: int,
        entry_adx: float,
        current_adx: float,
        entry_vol_ratio: float,
        current_vol_ratio: float,
        position_direction: int  # 1 for long, -1 for short
    ) -> Tuple[bool, str]:
        """
        Check if thesis is invalidated.
        
        Args:
            bars_held: Number of bars position has been held
            entry_adx: ADX at entry
            current_adx: Current ADX
            entry_vol_ratio: Vol ratio at entry
            current_vol_ratio: Current vol ratio
            position_direction: 1 for long, -1 for short
            
        Returns:
            Tuple of (is_invalidated, reason)
        """
        # 1. Time expiry
        if bars_held >= self.max_hold_bars:
            return True, f"time_expiry ({bars_held} >= {self.max_hold_bars} bars)"
        
        # 2. Trend acceleration (thesis was: trend exhausted, but trend got stronger)
        adx_change = current_adx - entry_adx
        if adx_change > self.trend_acceleration_threshold:
            return True, f"trend_accelerated (ADX +{adx_change:.1f})"
        
        # 3. Regime shift (volatility exploded)
        vol_change = current_vol_ratio / entry_vol_ratio if entry_vol_ratio > 0 else 1.0
        if vol_change > self.regime_shift_threshold:
            return True, f"regime_shift (vol_ratio x{vol_change:.1f})"
        
        return False, ""


# =============================================================================
# STRUCTURE CONFIRMATION (For entry logic)
# =============================================================================

def check_structure_confirmation(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    direction: str = 'long'
) -> Tuple[bool, str]:
    """
    Check for price structure confirmation before entry.
    
    Why this matters:
    - Don't bottom-tick turns with indicator crossovers
    - Wait for structure confirmation (small lag, big win rate improvement)
    - Higher low (for long) or lower high (for short) is the key
    
    Args:
        highs: Recent high prices (at least 6 bars)
        lows: Recent low prices (at least 6 bars)
        closes: Recent close prices (at least 6 bars)
        direction: 'long' or 'short'
        
    Returns:
        Tuple of (is_confirmed, reason)
    """
    if len(lows) < 6 or len(highs) < 6:
        return False, "insufficient_data"
    
    if direction == 'long':
        # Higher low pattern: recent low > prior low
        recent_low = np.min(lows[-3:])
        prior_low = np.min(lows[-6:-3])
        current_close = closes[-1]
        
        # Allow 0.2% tolerance for "higher low"
        tolerance = 0.002 * prior_low
        
        if recent_low >= prior_low - tolerance and current_close > recent_low:
            return True, f"higher_low (recent={recent_low:.2f} >= prior={prior_low:.2f})"
        else:
            return False, f"no_higher_low (recent={recent_low:.2f} < prior={prior_low:.2f})"
    
    else:  # short
        # Lower high pattern: recent high < prior high
        recent_high = np.max(highs[-3:])
        prior_high = np.max(highs[-6:-3])
        current_close = closes[-1]
        
        tolerance = 0.002 * prior_high
        
        if recent_high <= prior_high + tolerance and current_close < recent_high:
            return True, f"lower_high (recent={recent_high:.2f} <= prior={prior_high:.2f})"
        else:
            return False, f"no_lower_high (recent={recent_high:.2f} > prior={prior_high:.2f})"
