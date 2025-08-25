"""
Adaptive Anti-Churning System
============================

Dynamic parameter adjustment for anti-churning mechanisms based on:
1. Market volatility (realized vs implied)
2. Price momentum strength
3. Opportunity cost analysis
4. Risk-adjusted performance metrics

Author: Pro Quant Infrastructure Team
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from .dynamic_adaptation_framework import DynamicAdaptationFramework, AdaptationTrigger, AdaptationMode


class MarketRegimeType(Enum):
    """Market regime classification for anti-churning adaptation"""
    TRENDING_LOW_VOL = "trending_low_vol"      # Strong trend, low volatility
    TRENDING_HIGH_VOL = "trending_high_vol"    # Strong trend, high volatility  
    RANGING_LOW_VOL = "ranging_low_vol"        # Sideways, low volatility
    RANGING_HIGH_VOL = "ranging_high_vol"      # Sideways, high volatility
    BREAKOUT = "breakout"                      # Price breakout/breakdown
    MEAN_REVERSION = "mean_reversion"          # Strong mean reversion


@dataclass
class AdaptiveAntiChurningConfig:
    """Configuration for adaptive anti-churning parameters"""
    
    # Base parameters (ULTRA-AGGRESSIVE for breakout capture)
    base_holding_minutes: int = 1    # Ultra-short for breakout capture
    base_cooldown_minutes: int = 0.5 # Ultra-short cooldown (30 seconds)
    
    # Regime-specific multipliers (ULTRA-AGGRESSIVE for breakout capture)
    regime_holding_multipliers: Dict[MarketRegimeType, float] = field(default_factory=lambda: {
        MarketRegimeType.TRENDING_LOW_VOL: 0.5,    # 30 seconds - ultra-fast trend capture
        MarketRegimeType.TRENDING_HIGH_VOL: 0.2,   # 12 seconds - immediate trend response
        MarketRegimeType.RANGING_LOW_VOL: 1.0,     # 1 minute - still responsive
        MarketRegimeType.RANGING_HIGH_VOL: 0.5,    # 30 seconds - quick response
        MarketRegimeType.BREAKOUT: 0.1,            # 6 seconds - instant breakout capture
        MarketRegimeType.MEAN_REVERSION: 0.3,      # 18 seconds - very quick mean reversion
    })
    
    regime_cooldown_multipliers: Dict[MarketRegimeType, float] = field(default_factory=lambda: {
        MarketRegimeType.TRENDING_LOW_VOL: 0.2,    # 6 seconds - instant re-entry
        MarketRegimeType.TRENDING_HIGH_VOL: 0.1,   # 3 seconds - ultra-fast re-entry
        MarketRegimeType.RANGING_LOW_VOL: 1.0,     # 30 seconds - still quick
        MarketRegimeType.RANGING_HIGH_VOL: 0.5,    # 15 seconds - fast cooldown
        MarketRegimeType.BREAKOUT: 0.05,           # 1.5 seconds - immediate re-entry for breakouts
        MarketRegimeType.MEAN_REVERSION: 0.3,      # 9 seconds - very quick re-entry
    })
    
    # Momentum-based adjustments
    momentum_strength_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'very_strong': 0.015,    # >1.5% momentum
        'strong': 0.010,         # >1.0% momentum  
        'moderate': 0.005,       # >0.5% momentum
        'weak': 0.002,           # >0.2% momentum
    })
    
    momentum_adjustment_factors: Dict[str, float] = field(default_factory=lambda: {
        'very_strong': 0.1,      # 10% of base time
        'strong': 0.2,           # 20% of base time
        'moderate': 0.5,         # 50% of base time
        'weak': 0.8,             # 80% of base time
    })
    
    # Volatility-based adjustments
    volatility_percentile_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'extreme_high': 95,      # >95th percentile
        'high': 80,              # >80th percentile
        'normal': 50,            # >50th percentile
        'low': 20,               # >20th percentile
    })
    
    volatility_adjustment_factors: Dict[str, float] = field(default_factory=lambda: {
        'extreme_high': 0.1,     # 10% of base time - very responsive
        'high': 0.3,             # 30% of base time
        'normal': 1.0,           # 100% of base time
        'low': 1.5,              # 150% of base time - more conservative
    })
    
    # Opportunity cost thresholds
    max_opportunity_cost_bps: int = 50        # Max 50bps opportunity cost before override
    price_move_significance_threshold: float = 0.005  # 0.5% price move significance
    
    # Safety limits
    min_holding_seconds: int = 30             # Absolute minimum 30 seconds
    max_holding_minutes: int = 120            # Absolute maximum 2 hours
    min_cooldown_seconds: int = 10            # Absolute minimum 10 seconds  
    max_cooldown_minutes: int = 60            # Absolute maximum 1 hour


class AdaptiveAntiChurningSystem:
    """
    Dynamic anti-churning system that adapts parameters based on market conditions
    """
    
    def __init__(self, config: Optional[AdaptiveAntiChurningConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or AdaptiveAntiChurningConfig()
        
        # State tracking
        self.current_regime: Optional[MarketRegimeType] = None
        self.volatility_history: List[float] = []
        self.momentum_history: List[float] = []
        self.price_history: List[float] = []
        self.opportunity_cost_history: List[float] = []
        
        # Performance tracking
        self.parameter_performance: Dict[str, List[float]] = {
            'holding_period': [],
            'cooldown_period': [],
            'regime_classification': []
        }
        
        self.logger.info("Adaptive Anti-Churning System initialized")
    
    def classify_market_regime(self, 
                             market_data: Dict[str, Any], 
                             momentum_strength: float,
                             trend_strength: float) -> MarketRegimeType:
        """
        Classify current market regime for parameter adaptation
        """
        try:
            # Extract market indicators
            volatility = market_data.get('volatility', 0.0)
            price_position = market_data.get('price_position', 0.5)
            volume_ratio = market_data.get('volume_ratio', 1.0)
            
            # Classify volatility
            is_high_vol = volatility > np.percentile(self.volatility_history[-100:], 70) if len(self.volatility_history) > 100 else volatility > 0.02
            
            # Classify trend
            is_trending = trend_strength > 0.3 and abs(momentum_strength) > 0.008
            
            # Classify breakout
            is_breakout = (price_position > 0.9 or price_position < 0.1) and abs(momentum_strength) > 0.012 and volume_ratio > 1.5
            
            # Classify mean reversion opportunity
            is_mean_reversion = abs(price_position - 0.5) > 0.3 and abs(momentum_strength) < 0.005
            
            # Regime classification logic
            if is_breakout:
                regime = MarketRegimeType.BREAKOUT
            elif is_mean_reversion:
                regime = MarketRegimeType.MEAN_REVERSION
            elif is_trending:
                regime = MarketRegimeType.TRENDING_HIGH_VOL if is_high_vol else MarketRegimeType.TRENDING_LOW_VOL
            else:
                regime = MarketRegimeType.RANGING_HIGH_VOL if is_high_vol else MarketRegimeType.RANGING_LOW_VOL
            
            self.current_regime = regime
            self.logger.debug(f"Market regime classified as: {regime.value}")
            
            return regime
            
        except Exception as e:
            self.logger.error(f"Error classifying market regime: {e}")
            return MarketRegimeType.RANGING_LOW_VOL  # Conservative default
    
    def calculate_adaptive_holding_period(self,
                                        market_data: Dict[str, Any],
                                        momentum_strength: float,
                                        trend_strength: float,
                                        symbol: str) -> timedelta:
        """
        Calculate adaptive holding period based on current market conditions
        """
        try:
            # Classify market regime
            regime = self.classify_market_regime(market_data, momentum_strength, trend_strength)
            
            # Base holding period
            base_minutes = self.config.base_holding_minutes
            
            # Apply regime multiplier
            regime_multiplier = self.config.regime_holding_multipliers.get(regime, 1.0)
            
            # Apply momentum adjustment
            momentum_factor = self._get_momentum_adjustment_factor(momentum_strength)
            
            # Apply volatility adjustment
            volatility_factor = self._get_volatility_adjustment_factor(market_data.get('volatility', 0.02))
            
            # Calculate final holding period
            adjusted_minutes = base_minutes * regime_multiplier * momentum_factor * volatility_factor
            
            # Apply safety limits
            adjusted_minutes = max(self.config.min_holding_seconds / 60, 
                                 min(adjusted_minutes, self.config.max_holding_minutes))
            
            holding_period = timedelta(minutes=adjusted_minutes)
            
            self.logger.debug(f"Adaptive holding period for {symbol}: {holding_period} "
                            f"(regime={regime.value}, momentum_factor={momentum_factor:.2f}, "
                            f"vol_factor={volatility_factor:.2f})")
            
            return holding_period
            
        except Exception as e:
            self.logger.error(f"Error calculating adaptive holding period: {e}")
            return timedelta(minutes=self.config.base_holding_minutes)
    
    def calculate_adaptive_cooldown_period(self,
                                         market_data: Dict[str, Any],
                                         momentum_strength: float,
                                         trend_strength: float,
                                         opportunity_cost_bps: float,
                                         symbol: str) -> timedelta:
        """
        Calculate adaptive cooldown period with opportunity cost override
        """
        try:
            # Check for opportunity cost override
            if opportunity_cost_bps > self.config.max_opportunity_cost_bps:
                self.logger.info(f"Opportunity cost override: {opportunity_cost_bps:.1f}bps > {self.config.max_opportunity_cost_bps}bps")
                return timedelta(seconds=self.config.min_cooldown_seconds)
            
            # Classify market regime
            regime = self.classify_market_regime(market_data, momentum_strength, trend_strength)
            
            # Base cooldown period
            base_minutes = self.config.base_cooldown_minutes
            
            # Apply regime multiplier
            regime_multiplier = self.config.regime_cooldown_multipliers.get(regime, 1.0)
            
            # Apply momentum adjustment
            momentum_factor = self._get_momentum_adjustment_factor(momentum_strength)
            
            # Apply volatility adjustment
            volatility_factor = self._get_volatility_adjustment_factor(market_data.get('volatility', 0.02))
            
            # Calculate final cooldown period
            adjusted_minutes = base_minutes * regime_multiplier * momentum_factor * volatility_factor
            
            # Apply safety limits
            adjusted_minutes = max(self.config.min_cooldown_seconds / 60,
                                 min(adjusted_minutes, self.config.max_cooldown_minutes))
            
            cooldown_period = timedelta(minutes=adjusted_minutes)
            
            self.logger.debug(f"Adaptive cooldown period for {symbol}: {cooldown_period} "
                            f"(regime={regime.value}, opp_cost={opportunity_cost_bps:.1f}bps)")
            
            return cooldown_period
            
        except Exception as e:
            self.logger.error(f"Error calculating adaptive cooldown period: {e}")
            return timedelta(minutes=self.config.base_cooldown_minutes)
    
    def calculate_opportunity_cost(self,
                                 current_price: float,
                                 entry_price: float,
                                 optimal_exit_price: float,
                                 position_size: float) -> float:
        """
        Calculate opportunity cost of holding vs optimal exit in basis points
        """
        try:
            if entry_price <= 0 or current_price <= 0:
                return 0.0
            
            # Current P&L
            current_pnl_pct = (current_price - entry_price) / entry_price
            
            # Optimal P&L
            optimal_pnl_pct = (optimal_exit_price - entry_price) / entry_price
            
            # Opportunity cost in percentage points
            opportunity_cost_pct = optimal_pnl_pct - current_pnl_pct
            
            # Convert to basis points
            opportunity_cost_bps = opportunity_cost_pct * 10000
            
            return max(0, opportunity_cost_bps)  # Only positive opportunity costs
            
        except Exception as e:
            self.logger.error(f"Error calculating opportunity cost: {e}")
            return 0.0
    
    def _get_momentum_adjustment_factor(self, momentum_strength: float) -> float:
        """Get adjustment factor based on momentum strength"""
        abs_momentum = abs(momentum_strength)
        
        if abs_momentum >= self.config.momentum_strength_thresholds['very_strong']:
            return self.config.momentum_adjustment_factors['very_strong']
        elif abs_momentum >= self.config.momentum_strength_thresholds['strong']:
            return self.config.momentum_adjustment_factors['strong']
        elif abs_momentum >= self.config.momentum_strength_thresholds['moderate']:
            return self.config.momentum_adjustment_factors['moderate']
        else:
            return self.config.momentum_adjustment_factors['weak']
    
    def _get_volatility_adjustment_factor(self, current_volatility: float) -> float:
        """Get adjustment factor based on volatility percentile"""
        if len(self.volatility_history) < 50:
            return 1.0  # Default until we have enough history
        
        volatility_percentile = (np.searchsorted(sorted(self.volatility_history[-200:]), current_volatility) / 
                               len(self.volatility_history[-200:])) * 100
        
        if volatility_percentile >= self.config.volatility_percentile_thresholds['extreme_high']:
            return self.config.volatility_adjustment_factors['extreme_high']
        elif volatility_percentile >= self.config.volatility_percentile_thresholds['high']:
            return self.config.volatility_adjustment_factors['high']
        elif volatility_percentile >= self.config.volatility_percentile_thresholds['normal']:
            return self.config.volatility_adjustment_factors['normal']
        else:
            return self.config.volatility_adjustment_factors['low']
    
    def update_market_data(self, market_data: Dict[str, Any]):
        """Update market data history for adaptive calculations"""
        try:
            if 'volatility' in market_data:
                self.volatility_history.append(market_data['volatility'])
                if len(self.volatility_history) > 1000:
                    self.volatility_history = self.volatility_history[-500:]  # Keep last 500
            
            if 'momentum' in market_data:
                self.momentum_history.append(market_data['momentum'])
                if len(self.momentum_history) > 1000:
                    self.momentum_history = self.momentum_history[-500:]
            
            if 'price' in market_data:
                self.price_history.append(market_data['price'])
                if len(self.price_history) > 1000:
                    self.price_history = self.price_history[-500:]
                    
        except Exception as e:
            self.logger.error(f"Error updating market data: {e}")
