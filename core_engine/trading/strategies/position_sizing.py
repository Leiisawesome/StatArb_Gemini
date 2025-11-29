"""
Position Sizing - Canonical Implementation
==========================================

Single source of truth for position sizing logic.
Provides multiple sizing methodologies that strategies can use.

Professional Grade Position Sizing Methods:
1. Fixed Fraction - Simple percentage of portfolio
2. Volatility-Adjusted - Size inversely proportional to volatility
3. Kelly Criterion - Optimal sizing based on edge and win rate
4. Risk Parity - Equal risk contribution
5. Signal-Confidence Weighted - Size proportional to signal strength

Design Philosophy:
- Pure functions for simple use cases
- Class-based PositionSizer for stateful use
- All methods return position size as fraction (0.0 - 1.0)

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SizingMethod(Enum):
    """Position sizing methods"""
    FIXED_FRACTION = "fixed_fraction"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    KELLY_CRITERION = "kelly_criterion"
    RISK_PARITY = "risk_parity"
    ATR_BASED = "atr_based"


@dataclass
class SizingConfig:
    """Position sizing configuration"""
    # Base sizing
    base_position_pct: float = 0.02  # 2% base position
    max_position_pct: float = 0.10  # 10% maximum
    min_position_pct: float = 0.005  # 0.5% minimum
    
    # Volatility adjustment
    target_volatility: float = 0.15  # 15% annual target vol
    vol_lookback_days: int = 20  # Days for vol calculation
    vol_scaling_cap: float = 3.0  # Maximum vol multiplier
    
    # Kelly parameters
    kelly_fraction: float = 0.25  # Use 25% of full Kelly
    min_edge_for_kelly: float = 0.01  # 1% minimum edge
    
    # ATR-based sizing
    atr_risk_per_trade: float = 0.01  # Risk 1% per trade
    atr_period: int = 14
    
    # Risk limits
    max_portfolio_risk: float = 0.20  # 20% max portfolio risk
    position_concentration_limit: float = 0.15  # 15% per position


# =============================================================================
# PURE FUNCTIONS - Single Source of Truth
# =============================================================================

def calculate_fixed_fraction_size(
    base_fraction: float,
    confidence: float = 1.0,
    max_fraction: float = 0.10
) -> float:
    """
    Fixed fraction position sizing
    
    Most basic method - uses a fixed percentage of portfolio.
    
    Args:
        base_fraction: Base position size (0-1)
        confidence: Signal confidence multiplier (0-1)
        max_fraction: Maximum position size (0-1)
        
    Returns:
        Position size as fraction of portfolio (0-1)
    """
    size = base_fraction * confidence
    return min(max(size, 0.0), max_fraction)


def calculate_volatility_adjusted_size(
    base_fraction: float,
    current_volatility: float,
    target_volatility: float = 0.15,
    confidence: float = 1.0,
    max_fraction: float = 0.10,
    scaling_cap: float = 3.0
) -> float:
    """
    Volatility-adjusted position sizing
    
    Inversely scales position size with volatility:
    - High vol → smaller positions
    - Low vol → larger positions (capped)
    
    Args:
        base_fraction: Base position size
        current_volatility: Current annualized volatility
        target_volatility: Target volatility for scaling
        confidence: Signal confidence
        max_fraction: Maximum position size
        scaling_cap: Maximum multiplier from vol adjustment
        
    Returns:
        Position size as fraction of portfolio (0-1)
    """
    if current_volatility <= 0:
        return calculate_fixed_fraction_size(base_fraction, confidence, max_fraction)
    
    # Vol adjustment factor (inverse relationship)
    vol_ratio = target_volatility / current_volatility
    vol_multiplier = min(max(vol_ratio, 1.0 / scaling_cap), scaling_cap)
    
    size = base_fraction * vol_multiplier * confidence
    return min(max(size, 0.0), max_fraction)


def calculate_kelly_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    kelly_fraction: float = 0.25,
    max_fraction: float = 0.10,
    min_edge: float = 0.01
) -> float:
    """
    Kelly Criterion position sizing
    
    Calculates optimal bet size based on edge and win rate.
    Uses fractional Kelly for practical risk management.
    
    Kelly formula: f* = (bp - q) / b
    where:
        b = avg_win / avg_loss (reward-to-risk ratio)
        p = win rate
        q = 1 - p (loss rate)
    
    Args:
        win_rate: Historical win rate (0-1)
        avg_win: Average winning trade return
        avg_loss: Average losing trade return (positive number)
        kelly_fraction: Fraction of full Kelly to use (0-1)
        max_fraction: Maximum position size
        min_edge: Minimum edge required to trade
        
    Returns:
        Position size as fraction of portfolio (0-1)
    """
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    
    # Calculate reward-to-risk ratio
    b = abs(avg_win) / abs(avg_loss)
    p = win_rate
    q = 1 - win_rate
    
    # Full Kelly
    full_kelly = (b * p - q) / b
    
    # Check for positive edge
    if full_kelly <= min_edge:
        return 0.0
    
    # Apply fractional Kelly
    fractional_kelly = full_kelly * kelly_fraction
    
    return min(max(fractional_kelly, 0.0), max_fraction)


def calculate_atr_based_size(
    portfolio_value: float,
    entry_price: float,
    atr: float,
    risk_per_trade: float = 0.01,
    atr_multiplier: float = 2.0,
    max_fraction: float = 0.10
) -> float:
    """
    ATR-based position sizing
    
    Sizes position based on ATR to normalize risk across different volatility regimes.
    
    Position size = (Portfolio * Risk%) / (ATR * Multiplier)
    
    Args:
        portfolio_value: Total portfolio value
        entry_price: Entry price for the position
        atr: Average True Range value
        risk_per_trade: Risk per trade as fraction (0.01 = 1%)
        atr_multiplier: ATR multiplier for stop distance
        max_fraction: Maximum position size
        
    Returns:
        Position size as fraction of portfolio (0-1)
    """
    if atr <= 0 or entry_price <= 0 or portfolio_value <= 0:
        return 0.0
    
    # Dollar risk per trade
    dollar_risk = portfolio_value * risk_per_trade
    
    # Stop distance in price terms
    stop_distance = atr * atr_multiplier
    
    # Number of shares
    shares = dollar_risk / stop_distance
    
    # Position value
    position_value = shares * entry_price
    
    # As fraction of portfolio
    position_fraction = position_value / portfolio_value
    
    return min(max(position_fraction, 0.0), max_fraction)


def calculate_signal_weighted_size(
    base_fraction: float,
    signal_confidence: float,
    signal_strength: float = 1.0,
    regime_multiplier: float = 1.0,
    max_fraction: float = 0.10
) -> float:
    """
    Signal-weighted position sizing
    
    Combines signal confidence and strength with regime adjustment.
    
    Args:
        base_fraction: Base position size
        signal_confidence: Signal confidence (0-1)
        signal_strength: Signal strength multiplier
        regime_multiplier: Regime-based adjustment (0.5-1.5 typically)
        max_fraction: Maximum position size
        
    Returns:
        Position size as fraction of portfolio (0-1)
    """
    size = base_fraction * signal_confidence * signal_strength * regime_multiplier
    return min(max(size, 0.0), max_fraction)


# =============================================================================
# POSITION SIZER CLASS - Stateful Implementation
# =============================================================================

class PositionSizer:
    """
    Professional Position Sizer
    
    Stateful implementation that tracks historical performance
    for Kelly calculations and maintains consistent sizing logic.
    
    Usage:
        sizer = PositionSizer(SizingConfig())
        size = sizer.calculate_size(
            method=SizingMethod.VOLATILITY_ADJUSTED,
            signal_confidence=0.8,
            current_volatility=0.25
        )
    """
    
    def __init__(self, config: Optional[SizingConfig] = None):
        """Initialize position sizer with configuration"""
        self.config = config or SizingConfig()
        
        # Historical data for Kelly calculations
        self._trade_results: list = []
        self._win_rate: float = 0.5
        self._avg_win: float = 0.02
        self._avg_loss: float = 0.01
        
        logger.debug("PositionSizer initialized")
    
    def calculate_size(
        self,
        method: SizingMethod = SizingMethod.VOLATILITY_ADJUSTED,
        signal_confidence: float = 1.0,
        signal_strength: float = 1.0,
        current_volatility: Optional[float] = None,
        entry_price: Optional[float] = None,
        atr: Optional[float] = None,
        portfolio_value: Optional[float] = None,
        regime_multiplier: float = 1.0,
        **kwargs
    ) -> float:
        """
        Calculate position size using specified method
        
        Args:
            method: Sizing method to use
            signal_confidence: Signal confidence (0-1)
            signal_strength: Signal strength multiplier
            current_volatility: Current annualized volatility
            entry_price: Entry price for ATR-based sizing
            atr: Average True Range
            portfolio_value: Total portfolio value
            regime_multiplier: Regime adjustment factor
            **kwargs: Additional method-specific parameters
            
        Returns:
            Position size as fraction of portfolio (0-1)
        """
        try:
            if method == SizingMethod.FIXED_FRACTION:
                return calculate_fixed_fraction_size(
                    base_fraction=self.config.base_position_pct,
                    confidence=signal_confidence,
                    max_fraction=self.config.max_position_pct
                )
            
            elif method == SizingMethod.VOLATILITY_ADJUSTED:
                vol = current_volatility or 0.20  # Default 20% vol
                return calculate_volatility_adjusted_size(
                    base_fraction=self.config.base_position_pct,
                    current_volatility=vol,
                    target_volatility=self.config.target_volatility,
                    confidence=signal_confidence,
                    max_fraction=self.config.max_position_pct,
                    scaling_cap=self.config.vol_scaling_cap
                )
            
            elif method == SizingMethod.KELLY_CRITERION:
                return calculate_kelly_size(
                    win_rate=self._win_rate,
                    avg_win=self._avg_win,
                    avg_loss=self._avg_loss,
                    kelly_fraction=self.config.kelly_fraction,
                    max_fraction=self.config.max_position_pct,
                    min_edge=self.config.min_edge_for_kelly
                )
            
            elif method == SizingMethod.ATR_BASED:
                if atr is None or entry_price is None or portfolio_value is None:
                    logger.warning("ATR-based sizing requires atr, entry_price, and portfolio_value")
                    return self.config.base_position_pct
                
                return calculate_atr_based_size(
                    portfolio_value=portfolio_value,
                    entry_price=entry_price,
                    atr=atr,
                    risk_per_trade=self.config.atr_risk_per_trade,
                    max_fraction=self.config.max_position_pct
                )
            
            elif method == SizingMethod.RISK_PARITY:
                # Risk parity uses volatility-adjusted with equal risk contribution
                vol = current_volatility or 0.20
                return calculate_volatility_adjusted_size(
                    base_fraction=self.config.base_position_pct,
                    current_volatility=vol,
                    target_volatility=self.config.target_volatility,
                    confidence=signal_confidence * regime_multiplier,
                    max_fraction=self.config.max_position_pct,
                    scaling_cap=self.config.vol_scaling_cap
                )
            
            else:
                # Default to fixed fraction
                return calculate_fixed_fraction_size(
                    base_fraction=self.config.base_position_pct,
                    confidence=signal_confidence,
                    max_fraction=self.config.max_position_pct
                )
                
        except Exception as e:
            logger.error(f"Position sizing error: {e}")
            return self.config.min_position_pct
    
    def update_trade_results(self, pnl: float, is_winner: bool) -> None:
        """
        Update historical trade results for Kelly calculations
        
        Args:
            pnl: Trade P&L as return (positive or negative)
            is_winner: Whether the trade was profitable
        """
        self._trade_results.append({
            'pnl': pnl,
            'is_winner': is_winner
        })
        
        # Keep last 100 trades
        if len(self._trade_results) > 100:
            self._trade_results = self._trade_results[-100:]
        
        # Update statistics
        if len(self._trade_results) >= 10:
            wins = [t for t in self._trade_results if t['is_winner']]
            losses = [t for t in self._trade_results if not t['is_winner']]
            
            self._win_rate = len(wins) / len(self._trade_results)
            
            if wins:
                self._avg_win = np.mean([t['pnl'] for t in wins])
            if losses:
                self._avg_loss = abs(np.mean([t['pnl'] for t in losses]))
    
    def get_kelly_recommendation(self) -> Dict[str, float]:
        """Get current Kelly sizing recommendation"""
        return {
            'win_rate': self._win_rate,
            'avg_win': self._avg_win,
            'avg_loss': self._avg_loss,
            'full_kelly': calculate_kelly_size(
                self._win_rate, self._avg_win, self._avg_loss, 
                kelly_fraction=1.0, max_fraction=1.0
            ),
            'recommended_size': calculate_kelly_size(
                self._win_rate, self._avg_win, self._avg_loss,
                kelly_fraction=self.config.kelly_fraction,
                max_fraction=self.config.max_position_pct
            )
        }


# =============================================================================
# CONVENIENCE FUNCTION FOR STRATEGIES
# =============================================================================

def calculate_position_size(
    signal_confidence: float,
    base_position_pct: float = 0.02,
    max_position_pct: float = 0.10,
    current_volatility: Optional[float] = None,
    target_volatility: float = 0.15,
    method: str = "volatility_adjusted"
) -> float:
    """
    Convenience function for calculating position size
    
    This is the CANONICAL position sizing function for strategies.
    Strategies should call this instead of implementing their own.
    
    Args:
        signal_confidence: Signal confidence (0-1)
        base_position_pct: Base position size (0-1)
        max_position_pct: Maximum position size (0-1)
        current_volatility: Current annualized volatility
        target_volatility: Target volatility for scaling
        method: Sizing method ('fixed', 'volatility_adjusted')
        
    Returns:
        Position size as fraction of portfolio (0-1)
        
    Example:
        >>> size = calculate_position_size(
        ...     signal_confidence=0.8,
        ...     base_position_pct=0.02,
        ...     current_volatility=0.25
        ... )
    """
    if method == "fixed":
        return calculate_fixed_fraction_size(
            base_fraction=base_position_pct,
            confidence=signal_confidence,
            max_fraction=max_position_pct
        )
    else:
        # Default: volatility-adjusted
        vol = current_volatility or target_volatility
        return calculate_volatility_adjusted_size(
            base_fraction=base_position_pct,
            current_volatility=vol,
            target_volatility=target_volatility,
            confidence=signal_confidence,
            max_fraction=max_position_pct
        )
