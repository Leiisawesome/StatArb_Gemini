from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import logging

from .indicators.enhanced_technical_indicators import (
    EnhancedTechnicalIndicatorEngine, AcademicMomentumConfig
)

logger = logging.getLogger(__name__)

@dataclass
class AcademicSignalConfig:
    """Academic signal generation configuration"""
    
    # Multi-horizon momentum weights (Moskowitz et al., 2012)
    short_term_weight: float = 0.2
    medium_term_weight: float = 0.3
    long_term_weight: float = 0.3
    intermediate_weight: float = 0.2
    
    # Volume weighting (Gervais et al., 2001)
    volume_weight: float = 0.3
    volume_threshold: float = 1_000_000
    
    # Regime-dependent weights (Cooper et al., 2004)
    bull_market_weight: float = 1.2
    bear_market_weight: float = 0.8
    high_volatility_weight: float = 0.5
    crash_weight: float = 0.0
    
    # Macro factor weights (Chordia & Shivakumar, 2002)
    gdp_weight: float = 0.2
    inflation_weight: float = 0.1
    interest_rate_weight: float = 0.1
    
    # Signal combination
    signal_threshold: float = 0.7
    confirmation_weight: float = 0.4
    divergence_weight: float = 0.3

class EnhancedSignalGenerator:
    """Enhanced signal generator with latest academic foundations"""
    
    def __init__(self, config: AcademicSignalConfig):
        self.config = config
        self.indicator_engine = EnhancedTechnicalIndicatorEngine(AcademicMomentumConfig())
        
    def generate_academic_momentum_signals(self, data: Dict[str, pd.DataFrame], 
                                         spy_data: pd.DataFrame) -> Dict[str, float]:
        """Generate momentum signals based on latest academic research"""
        
        # Calculate all academic momentum indicators
        academic_indicators = self.indicator_engine.calculate_academic_momentum_signals(data, spy_data)
        
        # Combine signals using academic weights
        combined_signals = {}
        
        for symbol, indicators in academic_indicators.items():
            if symbol == 'SPY':
                continue
                
            # Multi-horizon momentum combination (Moskowitz et al., 2012)
            multi_horizon_signal = self._combine_multi_horizon_signals(indicators)
            
            # Volume-weighted adjustment (Gervais et al., 2001)
            volume_adjusted_signal = self._apply_volume_weighting(indicators, multi_horizon_signal)
            
            # Regime-dependent adjustment (Cooper et al., 2004)
            regime_adjusted_signal = self._apply_regime_adjustment(indicators, volume_adjusted_signal)
            
            # Macro factor adjustment (Chordia & Shivakumar, 2002)
            macro_adjusted_signal = self._apply_macro_adjustment(indicators, regime_adjusted_signal)
            
            # Final signal combination
            final_signal = self._combine_academic_signals(indicators, macro_adjusted_signal)
            
            combined_signals[symbol] = final_signal
        
        return combined_signals
    
    def _combine_multi_horizon_signals(self, indicators: Dict[str, float]) -> float:
        """Combine multi-horizon momentum signals (Moskowitz et al., 2012)"""
        
        short_term = indicators.get('momentum_1w', 0)
        medium_term = indicators.get('momentum_1m', 0)
        long_term = indicators.get('momentum_3m', 0)
        intermediate = indicators.get('momentum_6m', 0)
        
        combined = (
            short_term * self.config.short_term_weight +
            medium_term * self.config.medium_term_weight +
            long_term * self.config.long_term_weight +
            intermediate * self.config.intermediate_weight
        )
        
        return combined
    
    def _apply_volume_weighting(self, indicators: Dict[str, float], 
                               base_signal: float) -> float:
        """Apply volume weighting (Gervais et al., 2001)"""
        
        volume_momentum = indicators.get('volume_weighted_momentum', 0)
        high_volume_premium = indicators.get('high_volume_momentum', 0)
        
        volume_adjustment = (
            volume_momentum * self.config.volume_weight +
            high_volume_premium * self.config.volume_weight
        )
        
        return base_signal + volume_adjustment
    
    def _apply_regime_adjustment(self, indicators: Dict[str, float], 
                                base_signal: float) -> float:
        """Apply regime-dependent adjustment (Cooper et al., 2004)"""
        
        regime = indicators.get('market_regime', 'bull_market')
        
        if regime == 'bull_market':
            weight = self.config.bull_market_weight
        elif regime == 'bear_market':
            weight = self.config.bear_market_weight
        elif regime == 'high_volatility':
            weight = self.config.high_volatility_weight
        elif regime == 'momentum_crash':
            weight = self.config.crash_weight
        else:
            weight = 1.0
        
        return base_signal * weight
    
    def _apply_macro_adjustment(self, indicators: Dict[str, float], 
                               base_signal: float) -> float:
        """Apply macro factor adjustment (Chordia & Shivakumar, 2002)"""
        
        gdp_adjustment = indicators.get('gdp_adjustment', 0)
        inflation_adjustment = indicators.get('inflation_adjustment', 0)
        interest_rate_adjustment = indicators.get('interest_rate_adjustment', 0)
        
        macro_adjustment = (
            gdp_adjustment * self.config.gdp_weight +
            inflation_adjustment * self.config.inflation_weight +
            interest_rate_adjustment * self.config.interest_rate_weight
        )
        
        return base_signal + macro_adjustment
    
    def _combine_academic_signals(self, indicators: Dict[str, float], 
                                 base_signal: float) -> float:
        """Combine all academic signals with confirmation and divergence"""
        
        # Base academic signal
        academic_signal = base_signal
        
        # Confirmation signals
        crash_protected = indicators.get('crash_protected_momentum', 0)
        regime_adjusted = indicators.get('regime_adjusted_momentum', 0)
        
        confirmation_signal = (crash_protected + regime_adjusted) / 2
        
        # Divergence signals (when different horizons disagree)
        short_term = indicators.get('momentum_1w', 0)
        long_term = indicators.get('momentum_3m', 0)
        divergence = abs(short_term - long_term)
        
        # Final combination
        final_signal = (
            academic_signal * (1 - self.config.confirmation_weight - self.config.divergence_weight) +
            confirmation_signal * self.config.confirmation_weight +
            divergence * self.config.divergence_weight
        )
        
        return final_signal 