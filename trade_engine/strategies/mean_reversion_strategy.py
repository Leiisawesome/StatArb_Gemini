"""
Mean Reversion Strategy Implementation - Clean Architecture
========================================================

Professional mean reversion strategy implementation following clean architecture.
Extracted from unified_core_engine.py to eliminate strategy logic contamination.

Author: Professional Trading System Architecture
Version: 2.0.0
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from core_structure.strategy_interfaces import BaseStrategy, StrategyType, StrategyContext, StrategyMetrics
from core_structure.components.signal_generation.signal_generator import TradingSignal, SignalType, SignalStrength


class MeanReversionStrategy(BaseStrategy):
    """
    Clean mean reversion strategy implementation.
    
    Handles all mean reversion logic that was previously
    embedded in the core engine.
    """
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MEAN_REVERSION
    
    @property
    def required_indicators(self) -> List[str]:
        return ['z_score', 'mean', 'std', 'bollinger_bands', 'rsi']
    
    def get_strategy_name(self) -> str:
        return "Mean Reversion Strategy"
    
    def _get_required_parameters(self) -> List[str]:
        return [
            'z_score_threshold', 'exit_z_score', 'position_sizing_method',
            'max_position_size', 'lookback_period', 'bollinger_std'
        ]
    
    async def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate mean reversion trading signals"""
        signals = []
        
        # Extract market data and portfolio state
        market_data = context.market_data
        portfolio_state = context.portfolio_state
        timestamp = context.timestamp
        
        try:
            if len(market_data) < 20:  # Need sufficient data for mean reversion
                return signals
            
            # Extract mean reversion indicators
            current_price = market_data['close'].iloc[-1] if 'close' in market_data.columns else 0
            
            # Calculate Z-score if not available
            if 'z_score' in market_data.columns:
                current_z_score = market_data['z_score'].iloc[-1]
            else:
                # Calculate z-score from price data
                lookback_period = self._config.get('lookback_period', 20)
                prices = market_data['close'].tail(lookback_period)
                mean_price = prices.mean()
                std_price = prices.std()
                current_z_score = (current_price - mean_price) / std_price if std_price > 0 else 0
            
            # Get configuration parameters
            z_score_threshold = self._config.get('z_score_threshold', 2.0)
            exit_z_score = self._config.get('exit_z_score', 0.5)
            max_position_size = self._config.get('max_position_size', 0.03)
            
            # Calculate confidence based on z-score magnitude
            confidence = min(abs(current_z_score) / z_score_threshold, 1.0) if z_score_threshold > 0 else 0.5
            
            # Generate signal based on z-score deviation
            if abs(current_z_score) > z_score_threshold:
                # Mean reversion: buy when price is below mean (negative z-score), sell when above
                signal_type = SignalType.BUY if current_z_score < -z_score_threshold else SignalType.SELL
                
                # Stronger signals for larger deviations
                signal_strength = SignalStrength.STRONG if abs(current_z_score) > z_score_threshold * 1.5 else SignalStrength.MEDIUM
                
                # Position size based on z-score magnitude and confidence
                position_size = min(
                    confidence * max_position_size,
                    max_position_size
                )
                
                signal = TradingSignal(
                    symbol=getattr(market_data, 'symbol', 'UNKNOWN'),
                    signal_type=signal_type,
                    strength=signal_strength,
                    confidence=confidence,
                    timestamp=timestamp,
                    price_target=None,  # Will be calculated by execution engine
                    stop_loss=None,     # Will be calculated by risk management
                    position_size=position_size,
                    metadata={
                        'strategy_type': 'mean_reversion',
                        'z_score': current_z_score,
                        'z_score_threshold': z_score_threshold,
                        'lookback_period': self._config.get('lookback_period', 20),
                        'strategy_id': self.strategy_id
                    }
                )
                
                signals.append(signal)
            
            # Exit signal for existing positions
            elif abs(current_z_score) <= exit_z_score:
                # Check if we have existing position to close
                symbol = getattr(market_data, 'symbol', 'UNKNOWN')
                if symbol in portfolio_state.positions:
                    signal = TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.EXIT,
                        strength=SignalStrength.MEDIUM,
                        confidence=0.8,
                        timestamp=timestamp,
                        price_target=current_price,
                        stop_loss=None,
                        position_size=0,  # Close position
                        metadata={
                            'strategy_type': 'mean_reversion',
                            'z_score': current_z_score,
                            'exit_threshold': exit_z_score,
                            'exit_reason': 'mean_reversion_exit',
                            'strategy_id': self.strategy_id
                        }
                    )
                    
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            # Return empty signals on error
            return []
