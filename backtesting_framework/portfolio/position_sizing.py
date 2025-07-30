#!/usr/bin/env python3
"""
Dynamic Position Sizing
Phase 2: Core System Integration - Batch 3
"""

import logging
from typing import Dict, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class PositionSizing:
    """Dynamic position sizing using various methods"""
    
    def __init__(self, portfolio_value: float = 100000):
        self.portfolio_value = portfolio_value
        self.risk_free_rate = 0.02  # 2% risk-free rate
        self.max_position_size = 0.1  # 10% max position size
        self.max_portfolio_risk = 0.02  # 2% max portfolio risk
        
        logger.info(f"Initialized PositionSizing with ${portfolio_value:,.2f} portfolio")
    
    def kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate Kelly criterion position size"""
        if avg_loss == 0:
            return 0.0
        
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        
        # Apply constraints
        kelly_fraction = max(0.0, min(kelly_fraction, self.max_position_size))
        
        logger.debug(f"Kelly criterion: {kelly_fraction:.3f} (win_rate: {win_rate:.2f})")
        return kelly_fraction
    
    def volatility_based_sizing(self, volatility: float, target_volatility: float = 0.15) -> float:
        """Calculate position size based on volatility"""
        if volatility <= 0:
            return 0.0
        
        # Inverse volatility sizing
        position_size = target_volatility / volatility
        
        # Apply constraints
        position_size = max(0.0, min(position_size, self.max_position_size))
        
        logger.debug(f"Volatility-based sizing: {position_size:.3f} (vol: {volatility:.3f})")
        return position_size
    
    def risk_parity_sizing(self, volatilities: Dict[str, float], 
                          target_risk: float = 0.02) -> Dict[str, float]:
        """Calculate risk parity position sizes"""
        if not volatilities:
            return {}
        
        # Calculate inverse volatility weights
        inv_vols = {symbol: 1/vol for symbol, vol in volatilities.items() if vol > 0}
        total_inv_vol = sum(inv_vols.values())
        
        if total_inv_vol == 0:
            return {}
        
        # Calculate weights
        weights = {symbol: inv_vol/total_inv_vol for symbol, inv_vol in inv_vols.items()}
        
        # Scale to target risk
        position_sizes = {}
        for symbol, weight in weights.items():
            position_size = weight * target_risk / volatilities[symbol]
            position_size = max(0.0, min(position_size, self.max_position_size))
            position_sizes[symbol] = position_size
        
        logger.debug(f"Risk parity sizing calculated for {len(position_sizes)} symbols")
        return position_sizes
    
    def signal_strength_sizing(self, signal_strength: float, 
                             base_position_size: float = 0.05) -> float:
        """Calculate position size based on signal strength"""
        # Normalize signal strength to [0, 1]
        normalized_signal = min(abs(signal_strength), 1.0)
        
        # Scale position size by signal strength
        position_size = base_position_size * normalized_signal
        
        # Apply constraints
        position_size = max(0.0, min(position_size, self.max_position_size))
        
        logger.debug(f"Signal strength sizing: {position_size:.3f} (signal: {signal_strength:.3f})")
        return position_size
    
    def calculate_position_size(self, symbol: str, signal_strength: float,
                              volatility: float = None, win_rate: float = None,
                              avg_win: float = None, avg_loss: float = None,
                              method: str = "signal_strength") -> float:
        """Calculate position size using specified method"""
        
        if method == "kelly" and all(v is not None for v in [win_rate, avg_win, avg_loss]):
            return self.kelly_criterion(win_rate, avg_win, avg_loss)
        elif method == "volatility" and volatility is not None:
            return self.volatility_based_sizing(volatility)
        elif method == "signal_strength":
            return self.signal_strength_sizing(signal_strength)
        else:
            # Default to signal strength
            return self.signal_strength_sizing(signal_strength)
    
    def get_sizing_summary(self) -> Dict:
        """Get position sizing configuration summary"""
        return {
            'portfolio_value': self.portfolio_value,
            'max_position_size': self.max_position_size,
            'max_portfolio_risk': self.max_portfolio_risk,
            'risk_free_rate': self.risk_free_rate,
            'methods_available': ['kelly', 'volatility', 'signal_strength', 'risk_parity']
        } 