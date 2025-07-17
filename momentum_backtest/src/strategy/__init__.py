"""
Strategy module containing trading strategy implementations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging
from abc import ABC, abstractmethod

# Import modern momentum strategy
from .modern_momentum import ModernMomentumStrategy

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize strategy with configuration"""
        self.config = config
        self.strategy_config = config.get('strategy', {})
        
    @abstractmethod
    def generate_signals(self, 
                        data: pd.DataFrame, 
                        current_date: pd.Timestamp) -> Dict[str, str]:
        """
        Generate trading signals based on market data
        
        Args:
            data: Historical market data
            current_date: Current trading date
            
        Returns:
            Dictionary mapping symbols to signal directions ('BUY', 'SELL', 'HOLD')
        """
        pass
    
    @abstractmethod
    def get_target_positions(self, 
                           signals: Dict[str, str], 
                           current_date: pd.Timestamp) -> Dict[str, float]:
        """
        Convert signals to target position weights
        
        Args:
            signals: Trading signals from generate_signals
            current_date: Current trading date
            
        Returns:
            Dictionary mapping symbols to target weights (0.0 to 1.0)
        """
        pass

__all__ = ['BaseStrategy', 'ModernMomentumStrategy']
