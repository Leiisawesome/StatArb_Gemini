"""
Momentum Strategy Implementation - Clean Architecture
================================================

Professional momentum strategy implementation following clean architecture.
Extracted from unified_core_engine.py to eliminate strategy logic contamination.

Author: Professional Trading System Architecture
Version: 2.0.0
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

from core_structure.strategy_interfaces import BaseStrategy, StrategyType, StrategyContext, StrategyMetrics
from core_structure.components.signal_generation.signal_generator import TradingSignal, SignalType, SignalStrength


class MomentumStrategy(BaseStrategy):
    """
    Clean momentum strategy implementation.
    
    Handles all momentum-specific logic that was previously
    embedded in the core engine.
    """
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MOMENTUM
    
    @property
    def required_indicators(self) -> List[str]:
        return ['momentum', 'confidence', 'price', 'volume']
    
    def get_strategy_name(self) -> str:
        return "Momentum Strategy"
    
    def _get_required_parameters(self) -> List[str]:
        return [
            'entry_threshold', 'exit_threshold', 'position_sizing_method',
            'max_position_size', 'confidence_threshold'
        ]
    
    async def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate momentum-based trading signals"""
        signals = []
        
        # Extract market data and portfolio state
        market_data = context.market_data
        portfolio_state = context.portfolio_state
        timestamp = context.timestamp
        
        try:
            if len(market_data) < 5:
                return signals
            
            # Extract momentum indicators from market data
            if 'momentum' in market_data.columns:
                current_momentum = market_data['momentum'].iloc[-1]
                momentum_confidence = market_data.get('confidence', pd.Series([0.5] * len(market_data))).iloc[-1]
                
                # Get price and volume data
                current_price = market_data['close'].iloc[-1] if 'close' in market_data.columns else 0
                current_volume = market_data['volume'].iloc[-1] if 'volume' in market_data.columns else 0
                
                # Entry threshold from config
                entry_threshold = self._config.get('entry_threshold', 0.02)
                confidence_threshold = self._config.get('confidence_threshold', 0.6)
                max_position_size = self._config.get('max_position_size', 0.05)
                
                # Generate signal if momentum exceeds threshold
                if abs(current_momentum) > entry_threshold and momentum_confidence > confidence_threshold:
                    signal_type = SignalType.BUY if current_momentum > 0 else SignalType.SELL
                    signal_strength = SignalStrength.STRONG if abs(current_momentum) > entry_threshold * 2 else SignalStrength.MEDIUM
                    
                    # Calculate position size based on momentum strength and confidence
                    position_size = min(
                        momentum_confidence * max_position_size,
                        max_position_size
                    )
                    
                    signal = TradingSignal(
                        symbol=getattr(market_data, 'symbol', 'UNKNOWN'),
                        signal_type=signal_type,
                        strength=signal_strength,
                        confidence=momentum_confidence,
                        timestamp=timestamp,
                        price_target=None,  # Will be set by execution engine
                        stop_loss=None,     # Will be calculated by risk management
                        position_size=position_size,
                        metadata={
                            'strategy_type': 'momentum',
                            'momentum_value': current_momentum,
                            'entry_threshold': entry_threshold,
                            'strategy_id': self.strategy_id
                        }
                    )
                    
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            # Return empty signals on error
            return []
