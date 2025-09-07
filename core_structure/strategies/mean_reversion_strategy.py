#!/usr/bin/env python3
"""
Unified Mean Reversion Strategy - Consolidated Implementation
============================================================

Consolidated mean reversion strategy combining functionality from:
- trade_engine/strategies/mean_reversion_strategy.py
- trade_engine/templates/mean_reversion_template.py
- Enhanced with unified strategy system features

This implementation provides comprehensive mean reversion trading
with statistical analysis, Bollinger Bands, RSI, and Z-score analysis.

Author: Professional Trading System Architecture
Version: 2.0.0 (Unified)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import unified strategy framework
from .unified_strategy_system import (
    EnhancedBaseStrategy, TemplateBasedStrategy, StrategyParameters,
    UnifiedStrategyConfig, StrategyResult, StrategyStatus
)

# Import base interfaces
from ..interfaces.strategy_interfaces import StrategyType, StrategyContext, StrategyMetrics

# Import signal types
from ..components.signal_generation import TradingSignal, SignalType, SignalStrength

logger = logging.getLogger(__name__)

# ================================================================================
# MEAN REVERSION STRATEGY IMPLEMENTATION
# ================================================================================

class MeanReversionStrategy(EnhancedBaseStrategy):
    """
    Unified mean reversion strategy implementation.
    
    Features:
    - Z-score based mean reversion analysis
    - Bollinger Bands integration
    - RSI confirmation
    - Statistical significance testing
    - Dynamic position sizing based on deviation magnitude
    """
    
    # Class metadata
    SUPPORTED_MODES = ["backtest", "paper_trading", "live_trading"]
    STRATEGY_VERSION = "2.0.0"
    
    def __init__(self, strategy_id: str, config: UnifiedStrategyConfig):
        super().__init__(strategy_id, config)
        
        # Mean reversion specific parameters
        self.lookback_period = getattr(self.parameters, 'lookback_period', 20)
        self.z_score_threshold = getattr(self.parameters, 'z_score_threshold', 2.0)
        self.exit_z_score = getattr(self.parameters, 'exit_z_score', 0.5)
        self.bollinger_std = getattr(self.parameters, 'bollinger_std', 2.0)
        
        # Enhanced parameters
        self.rsi_period = getattr(self.parameters, 'rsi_period', 14)
        self.rsi_oversold = getattr(self.parameters, 'rsi_oversold', 30)
        self.rsi_overbought = getattr(self.parameters, 'rsi_overbought', 70)
        self.volume_confirmation = getattr(self.parameters, 'volume_confirmation', True)
        self.min_volume_ratio = getattr(self.parameters, 'min_volume_ratio', 0.8)
        
        logger.info(f"Mean reversion strategy initialized: {strategy_id}")
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MEAN_REVERSION
    
    @property
    def required_indicators(self) -> List[str]:
        return ['close', 'volume', 'high', 'low']
    
    def _get_required_parameters(self) -> List[str]:
        return [
            'z_score_threshold', 'exit_z_score', 'lookback_period',
            'bollinger_std', 'position_size'
        ]
    
    async def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate mean reversion trading signals"""
        signals = []
        
        try:
            market_data = context.market_data
            
            if len(market_data) < max(self.lookback_period, self.rsi_period):
                logger.debug(f"Insufficient data for mean reversion analysis: {len(market_data)}")
                return signals
            
            # Calculate mean reversion indicators
            indicators = self._calculate_indicators(market_data)
            
            # Check for mean reversion signal
            signal = self._evaluate_mean_reversion(context, market_data, indicators)
            
            if signal:
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Mean reversion signal generation failed: {e}")
            return []
    
    def _calculate_indicators(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all required indicators for mean reversion analysis"""
        try:
            prices = market_data['close']
            indicators = {}
            
            # Calculate rolling statistics
            rolling_mean = prices.rolling(window=self.lookback_period).mean()
            rolling_std = prices.rolling(window=self.lookback_period).std()
            
            # Z-score calculation
            current_price = prices.iloc[-1]
            current_mean = rolling_mean.iloc[-1]
            current_std = rolling_std.iloc[-1]
            
            if current_std > 0:
                z_score = (current_price - current_mean) / current_std
            else:
                z_score = 0.0
            
            indicators['z_score'] = z_score
            indicators['rolling_mean'] = current_mean
            indicators['rolling_std'] = current_std
            
            # Bollinger Bands
            upper_band = current_mean + (self.bollinger_std * current_std)
            lower_band = current_mean - (self.bollinger_std * current_std)
            
            indicators['bollinger_upper'] = upper_band
            indicators['bollinger_lower'] = lower_band
            indicators['bollinger_position'] = (current_price - lower_band) / (upper_band - lower_band) if upper_band != lower_band else 0.5
            
            # RSI calculation
            if len(prices) >= self.rsi_period:
                rsi = self._calculate_rsi(prices, self.rsi_period)
                indicators['rsi'] = rsi
            else:
                indicators['rsi'] = 50.0  # Neutral RSI
            
            # Volume analysis
            if 'volume' in market_data.columns and len(market_data) >= 10:
                recent_volume = market_data['volume'].iloc[-5:].mean()
                avg_volume = market_data['volume'].iloc[-20:].mean() if len(market_data) >= 20 else recent_volume
                indicators['volume_ratio'] = recent_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                indicators['volume_ratio'] = 1.0
            
            return indicators
            
        except Exception as e:
            logger.error(f"Indicator calculation failed: {e}")
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> float:
        """Calculate RSI (Relative Strength Index)"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
            
        except Exception as e:
            logger.error(f"RSI calculation failed: {e}")
            return 50.0
    
    def _evaluate_mean_reversion(self, 
                                context: StrategyContext,
                                market_data: pd.DataFrame,
                                indicators: Dict[str, Any]) -> Optional[TradingSignal]:
        """Evaluate mean reversion conditions and generate signal"""
        try:
            z_score = indicators.get('z_score', 0.0)
            rsi = indicators.get('rsi', 50.0)
            bollinger_position = indicators.get('bollinger_position', 0.5)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            
            # Check for extreme deviations
            signal_type = None
            confidence = 0.0
            
            # Oversold conditions (potential buy signal)
            if (z_score <= -self.z_score_threshold and 
                rsi <= self.rsi_oversold and
                bollinger_position <= 0.1):
                
                signal_type = SignalType.BUY
                # Confidence increases with more extreme values
                confidence = min(0.95, 0.6 + (abs(z_score) - self.z_score_threshold) * 0.1)
                
            # Overbought conditions (potential sell signal)
            elif (z_score >= self.z_score_threshold and
                  rsi >= self.rsi_overbought and
                  bollinger_position >= 0.9):
                
                signal_type = SignalType.SELL
                confidence = min(0.95, 0.6 + (abs(z_score) - self.z_score_threshold) * 0.1)
            
            # No signal if conditions not met
            if signal_type is None:
                return None
            
            # Volume confirmation
            if self.volume_confirmation and volume_ratio < self.min_volume_ratio:
                logger.debug(f"Signal filtered out due to low volume: {volume_ratio:.2f}")
                return None
            
            # Determine signal strength based on deviation magnitude
            deviation_magnitude = abs(z_score)
            if deviation_magnitude > self.z_score_threshold * 2:
                strength = SignalStrength.STRONG
            elif deviation_magnitude > self.z_score_threshold * 1.5:
                strength = SignalStrength.MEDIUM
            else:
                strength = SignalStrength.WEAK
            
            # Calculate position size based on confidence and deviation
            base_position_size = self.parameters.position_size
            deviation_factor = min(2.0, deviation_magnitude / self.z_score_threshold)
            adjusted_position_size = base_position_size * confidence * (deviation_factor / 2.0)
            adjusted_position_size = min(adjusted_position_size, self.parameters.max_position_size)
            
            # Create signal
            signal = TradingSignal(
                symbol=getattr(context, 'symbol', 'UNKNOWN'),
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                timestamp=context.timestamp or datetime.now(),
                quantity=adjusted_position_size,
                metadata={
                    'strategy_type': 'mean_reversion',
                    'strategy_id': self.strategy_id,
                    'z_score': z_score,
                    'rsi': rsi,
                    'bollinger_position': bollinger_position,
                    'volume_ratio': volume_ratio,
                    'indicators': indicators,
                    'thresholds': {
                        'z_score_threshold': self.z_score_threshold,
                        'exit_z_score': self.exit_z_score,
                        'rsi_oversold': self.rsi_oversold,
                        'rsi_overbought': self.rsi_overbought
                    }
                }
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Mean reversion evaluation failed: {e}")
            return None

# ================================================================================
# TEMPLATE-BASED MEAN REVERSION STRATEGY
# ================================================================================

class TemplateMeanReversionStrategy(TemplateBasedStrategy):
    """
    Template-based mean reversion strategy.
    
    Integrates template configuration from the legacy template system
    while using the unified strategy framework.
    """
    
    def __init__(self, strategy_id: str, config: UnifiedStrategyConfig, template_config: Dict[str, Any]):
        super().__init__(strategy_id, config, template_config)
        
        # Parse mean reversion specific template config
        self._parse_mean_reversion_template()
        
        logger.info(f"Template mean reversion strategy initialized: {strategy_id}")
    
    def _parse_mean_reversion_template(self):
        """Parse mean reversion specific template configuration"""
        try:
            # Extract mean reversion parameters from template
            mr_config = self.template_config.get('mean_reversion', {})
            
            # Set mean reversion specific parameters
            for param in ['z_score_threshold', 'exit_z_score', 'lookback_period', 'bollinger_std']:
                if param in mr_config:
                    setattr(self.parameters, param, mr_config[param])
            
            # Set RSI parameters
            rsi_config = mr_config.get('rsi', {})
            for param in ['rsi_period', 'rsi_oversold', 'rsi_overbought']:
                if param in rsi_config:
                    setattr(self.parameters, param, rsi_config[param])
            
            # Set volume parameters
            volume_config = mr_config.get('volume', {})
            for param in ['volume_confirmation', 'min_volume_ratio']:
                if param in volume_config:
                    setattr(self.parameters, param, volume_config[param])
            
        except Exception as e:
            logger.error(f"Mean reversion template parsing failed: {e}")
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MEAN_REVERSION
    
    @property
    def required_indicators(self) -> List[str]:
        base_indicators = ['close', 'volume', 'high', 'low']
        return base_indicators + self.parameters.custom_indicators

# ================================================================================
# STRATEGY REGISTRATION
# ================================================================================

def register_mean_reversion_strategies():
    """Register mean reversion strategy variants"""
    try:
        from .unified_strategy_registry import register_strategy
        
        # Register main mean reversion strategy
        register_strategy(
            strategy_type=StrategyType.MEAN_REVERSION,
            strategy_class=MeanReversionStrategy,
            name="Mean Reversion Strategy",
            description="Statistical mean reversion strategy with Z-score, Bollinger Bands, and RSI",
            version="2.0.0",
            author="Professional Trading System Architecture"
        )
        
        # Register template-based variant
        register_strategy(
            strategy_type=StrategyType.MEAN_REVERSION,
            strategy_class=TemplateMeanReversionStrategy,
            name="Template Mean Reversion Strategy",
            description="Template-based mean reversion strategy with configurable parameters",
            version="2.0.0",
            author="Professional Trading System Architecture"
        )
        
        logger.info("Mean reversion strategies registered successfully")
        return True
        
    except Exception as e:
        logger.error(f"Mean reversion strategy registration failed: {e}")
        return False

# Auto-register on module import
_registration_success = register_mean_reversion_strategies()

logger.info("Unified Mean Reversion Strategy loaded successfully")
