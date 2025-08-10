"""
Dynamic Position Sizing Module - Phase 1 Enhancement
Implements Kelly Criterion and volatility-adjusted position sizing
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class PositionSizingConfig:
    """Configuration for dynamic position sizing"""
    # Kelly Criterion settings
    kelly_fraction: float = 0.25  # Conservative fraction of Kelly
    max_kelly_position: float = 0.15  # Maximum position size from Kelly
    min_kelly_position: float = 0.01  # Minimum position size
    
    # Volatility adjustment settings
    target_volatility: float = 0.15  # Target portfolio volatility
    vol_adjustment_factor: float = 1.0  # Volatility adjustment multiplier
    max_vol_adjustment: float = 1.5  # Maximum volatility adjustment
    min_vol_adjustment: float = 0.5  # Minimum volatility adjustment
    
    # Risk management
    max_position_size: float = 0.25  # Maximum position size
    min_position_size: float = 0.01  # Minimum position size
    concentration_limit: float = 0.40  # Maximum concentration in single position

class DynamicPositionSizer:
    """Dynamic position sizing using Kelly Criterion and volatility adjustment"""
    
    def __init__(self, config: Optional[PositionSizingConfig] = None):
        self.config = config or PositionSizingConfig()
        self.position_history = []
        self.performance_metrics = {
            'win_rate': 0.5,  # Default 50% win rate
            'avg_win': 0.02,  # Default 2% average win
            'avg_loss': -0.015,  # Default -1.5% average loss
            'total_trades': 0
        }
    
    def calculate_kelly_position_size(
        self, 
        confidence: float,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
        max_position: Optional[float] = None
    ) -> float:
        """
        Calculate position size using Kelly Criterion with safety constraints
        
        Kelly Formula: f = (bp - q) / b
        Where: b = odds, p = win probability, q = loss probability
        """
        try:
            # Use provided values or defaults
            win_rate = win_rate or self.performance_metrics['win_rate']
            avg_win = avg_win or self.performance_metrics['avg_win']
            avg_loss = avg_loss or self.performance_metrics['avg_loss']
            max_position = max_position or self.config.max_kelly_position
            
            # Validate inputs
            if avg_win <= 0 or avg_loss >= 0:
                logger.warning("Invalid win/loss values for Kelly calculation")
                return self.config.min_kelly_position
            
            # Calculate Kelly fraction
            odds = abs(avg_win / avg_loss)
            kelly_fraction = ((win_rate * odds) - (1 - win_rate)) / odds
            
            # Apply confidence scaling and safety constraints
            adjusted_kelly = kelly_fraction * confidence * self.config.kelly_fraction
            
            # Apply bounds
            position_size = max(
                self.config.min_kelly_position,
                min(max_position, adjusted_kelly)
            )
            
            logger.debug(f"Kelly calculation: win_rate={win_rate:.3f}, "
                        f"avg_win={avg_win:.3f}, avg_loss={avg_loss:.3f}, "
                        f"kelly_fraction={kelly_fraction:.3f}, "
                        f"adjusted_kelly={adjusted_kelly:.3f}, "
                        f"final_position={position_size:.3f}")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Kelly position sizing failed: {e}")
            return self.config.min_kelly_position
    
    def calculate_volatility_adjusted_size(
        self,
        base_size: float,
        current_volatility: float,
        target_volatility: Optional[float] = None
    ) -> float:
        """
        Adjust position size based on current market volatility
        
        Args:
            base_size: Base position size (0.0 to 1.0)
            current_volatility: Current market volatility
            target_volatility: Target volatility (default from config)
        
        Returns:
            Adjusted position size
        """
        try:
            target_vol = target_volatility or self.config.target_volatility
            
            if current_volatility <= 0:
                return base_size
            
            # Calculate volatility adjustment
            vol_adjustment = target_vol / current_volatility
            
            # Apply bounds
            vol_adjustment = max(
                self.config.min_vol_adjustment,
                min(self.config.max_vol_adjustment, vol_adjustment)
            )
            
            # Apply adjustment
            adjusted_size = base_size * vol_adjustment
            
            # Ensure within overall bounds
            final_size = max(
                self.config.min_position_size,
                min(self.config.max_position_size, adjusted_size)
            )
            
            logger.debug(f"Volatility adjustment: base_size={base_size:.3f}, "
                        f"current_vol={current_volatility:.3f}, "
                        f"target_vol={target_vol:.3f}, "
                        f"vol_adjustment={vol_adjustment:.3f}, "
                        f"final_size={final_size:.3f}")
            
            return final_size
            
        except Exception as e:
            logger.error(f"Volatility adjustment failed: {e}")
            return base_size
    
    def calculate_optimal_position_size(
        self,
        confidence: float,
        volatility: float,
        risk_metrics: Dict[str, Any],
        regime: str,
        current_positions: Dict[str, float] = None
    ) -> float:
        """
        Calculate optimal position size using multiple factors
        
        Args:
            confidence: Signal confidence (0.0 to 1.0)
            volatility: Current market volatility
            risk_metrics: Risk metrics dictionary
            regime: Market regime
            current_positions: Current portfolio positions
        
        Returns:
            Optimal position size
        """
        try:
            # Start with Kelly-based sizing
            kelly_size = self.calculate_kelly_position_size(confidence)
            
            # Apply volatility adjustment
            vol_adjusted_size = self.calculate_volatility_adjusted_size(kelly_size, volatility)
            
            # Apply regime-specific adjustments
            regime_adjusted_size = self._apply_regime_adjustment(vol_adjusted_size, regime)
            
            # Apply concentration limits
            concentration_adjusted_size = self._apply_concentration_limit(
                regime_adjusted_size, current_positions or {}
            )
            
            # Final bounds check
            final_size = max(
                self.config.min_position_size,
                min(self.config.max_position_size, concentration_adjusted_size)
            )
            
            logger.debug(f"Optimal position size calculation: "
                        f"confidence={confidence:.3f}, volatility={volatility:.3f}, "
                        f"kelly_size={kelly_size:.3f}, vol_adjusted={vol_adjusted_size:.3f}, "
                        f"regime_adjusted={regime_adjusted_size:.3f}, "
                        f"final_size={final_size:.3f}")
            
            return final_size
            
        except Exception as e:
            logger.error(f"Optimal position sizing failed: {e}")
            return self.config.min_position_size
    
    def _apply_regime_adjustment(self, position_size: float, regime: str) -> float:
        """Apply regime-specific position size adjustments"""
        regime_adjustments = {
            'trending': 1.1,      # Slightly larger positions in trending markets
            'mean_reverting': 1.0, # No adjustment for mean reversion
            'volatile': 0.7,      # Smaller positions in volatile markets
            'stable': 1.05,       # Slightly larger positions in stable markets
            'unknown': 0.9        # Slightly smaller positions when regime is unknown
        }
        
        adjustment = regime_adjustments.get(regime.lower(), 1.0)
        return position_size * adjustment
    
    def _apply_concentration_limit(
        self, 
        position_size: float, 
        current_positions: Dict[str, float]
    ) -> float:
        """Apply concentration limits to prevent over-concentration"""
        if not current_positions:
            return position_size
        
        # Calculate current portfolio concentration
        total_exposure = sum(current_positions.values())
        
        # Check if adding this position would exceed concentration limit
        if total_exposure + position_size > self.config.concentration_limit:
            # Reduce position size to stay within limits
            max_additional_size = self.config.concentration_limit - total_exposure
            return max(self.config.min_position_size, max_additional_size)
        
        return position_size
    
    def update_performance_metrics(
        self,
        trade_result: Dict[str, Any]
    ) -> None:
        """Update performance metrics based on trade results"""
        try:
            # Extract trade information
            pnl = trade_result.get('pnl', 0.0)
            is_winning = pnl > 0
            
            # Update metrics
            self.performance_metrics['total_trades'] += 1
            
            # Update win rate
            if is_winning:
                self.performance_metrics['win_rate'] = (
                    (self.performance_metrics['win_rate'] * (self.performance_metrics['total_trades'] - 1) + 1) /
                    self.performance_metrics['total_trades']
                )
            else:
                self.performance_metrics['win_rate'] = (
                    (self.performance_metrics['win_rate'] * (self.performance_metrics['total_trades'] - 1)) /
                    self.performance_metrics['total_trades']
                )
            
            # Update average win/loss (simplified exponential moving average)
            alpha = 0.1  # Learning rate
            if is_winning:
                self.performance_metrics['avg_win'] = (
                    (1 - alpha) * self.performance_metrics['avg_win'] + alpha * pnl
                )
            else:
                self.performance_metrics['avg_loss'] = (
                    (1 - alpha) * self.performance_metrics['avg_loss'] + alpha * pnl
                )
            
            logger.debug(f"Updated performance metrics: "
                        f"win_rate={self.performance_metrics['win_rate']:.3f}, "
                        f"avg_win={self.performance_metrics['avg_win']:.3f}, "
                        f"avg_loss={self.performance_metrics['avg_loss']:.3f}")
            
        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance metrics summary"""
        return {
            'win_rate': self.performance_metrics['win_rate'],
            'avg_win': self.performance_metrics['avg_win'],
            'avg_loss': self.performance_metrics['avg_loss'],
            'total_trades': self.performance_metrics['total_trades'],
            'profit_factor': (
                abs(self.performance_metrics['avg_win']) / abs(self.performance_metrics['avg_loss'])
                if self.performance_metrics['avg_loss'] != 0 else float('inf')
            )
        }
