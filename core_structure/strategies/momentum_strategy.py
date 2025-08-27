"""
Momentum Strategy Implementation - Extracted from Core Engine
===========================================================

Professional momentum strategy implementation following clean architecture.
Extracted from unified_core_engine.py to eliminate strategy logic contamination.

Author: Professional Trading System Architecture
Version: 2.0.0
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

from ..strategy_interfaces import BaseStrategy, StrategyType, StrategyContext, StrategyMetrics
from ..signal_generation.signal_generator import TradingSignal, SignalType, SignalStrength


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
        
        # Get strategy parameters
        entry_threshold = self._config.get('entry_threshold', 0.001)
        exit_threshold = self._config.get('exit_threshold', 0.001)
        confidence_threshold = self._config.get('confidence_threshold', 0.5)
        
        # Process each symbol in market data
        for symbol in market_data.columns:
            if symbol.endswith('_momentum') or symbol.endswith('_confidence'):
                continue  # Skip metadata columns
                
            symbol_data = market_data[symbol].dropna()
            if symbol_data.empty:
                continue
            
            # Extract momentum signals
            momentum_col = f"{symbol}_momentum"
            confidence_col = f"{symbol}_confidence"
            
            if momentum_col not in market_data.columns:
                continue
            
            momentum_value = market_data[momentum_col].iloc[-1] if not market_data[momentum_col].empty else 0.0
            confidence_value = market_data[confidence_col].iloc[-1] if confidence_col in market_data.columns else 0.5
            
            # Skip low confidence signals
            if confidence_value < confidence_threshold:
                continue
            
            # Check if we have an existing position
            has_position = symbol in portfolio_state.get('positions', {})
            
            # Generate signal based on position state
            if has_position:
                signal = self._process_exit_signal(
                    symbol, momentum_value, confidence_value, 
                    exit_threshold, timestamp, symbol_data
                )
            else:
                signal = self._process_entry_signal(
                    symbol, momentum_value, confidence_value,
                    entry_threshold, timestamp
                )
            
            if signal:
                signals.append(signal)
        
        return signals
    
    def _process_entry_signal(self, symbol: str, momentum_value: float, 
                            confidence: float, entry_threshold: float,
                            timestamp: datetime) -> Optional[TradingSignal]:
        """Process momentum entry signals"""
        momentum_strength = abs(momentum_value)
        
        # Check if momentum exceeds entry threshold
        if momentum_strength < entry_threshold:
            return None
        
        # Dynamic position sizing based on momentum strength
        base_position_size = self._config.get('base_position_size', 0.2)
        max_position_size = self._config.get('max_position_size', 0.5)
        
        if momentum_strength > 0.005:
            dynamic_position_size = min(max_position_size, base_position_size + momentum_strength * 20)
        elif momentum_strength > 0.003:
            dynamic_position_size = min(0.4, base_position_size + momentum_strength * 15)
        else:
            dynamic_position_size = base_position_size
        
        # Determine signal direction
        signal_type = SignalType.LONG if momentum_value >= 0 else SignalType.SHORT
        
        # Determine signal strength
        if momentum_strength > 0.004:
            strength = SignalStrength.STRONG
        elif momentum_strength > 0.002:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK
        
        return TradingSignal(
            symbol_pair=symbol,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            position_size=dynamic_position_size,
            entry_price=0.0,  # Will be filled by execution engine
            timestamp=timestamp,
            metadata={
                'signal_source': 'momentum_entry',
                'entry_reason': f'momentum_strength_{momentum_value:.6f}',
                'momentum': momentum_value,
                'dynamic_position_size': dynamic_position_size,
                'strategy_id': self.strategy_id,
                'strategy_type': 'momentum',
                'is_exit_signal': False
            }
        )
    
    def _process_exit_signal(self, symbol: str, momentum_value: float,
                           confidence: float, exit_threshold: float,
                           timestamp: datetime, symbol_data: pd.Series) -> Optional[TradingSignal]:
        """Process momentum exit signals"""
        momentum_strength = abs(momentum_value)
        
        # Check for momentum reversal
        should_exit = momentum_strength >= exit_threshold
        
        # Additional exit conditions
        price_change = self._calculate_price_change(symbol_data)
        volatility = self._calculate_volatility(symbol_data)
        
        # Enhanced exit logic
        enhanced_exit_threshold = exit_threshold * (1 + volatility * 0.5)
        if momentum_strength >= enhanced_exit_threshold or abs(price_change) > 0.03:
            should_exit = True
        
        if not should_exit:
            return None
        
        # Determine exit signal strength
        if momentum_strength > 0.002 or abs(price_change) > 0.05:
            strength = SignalStrength.STRONG
        else:
            strength = SignalStrength.MODERATE
        
        return TradingSignal(
            symbol_pair=symbol,
            signal_type=SignalType.CLOSE_LONG,  # Simplified - should determine from position
            strength=strength,
            confidence=confidence,
            position_size=1.0,  # Close full position
            entry_price=0.0,
            timestamp=timestamp,
            metadata={
                'signal_source': 'momentum_exit',
                'exit_reason': f'momentum_reversal_{momentum_value:.6f}',
                'momentum': momentum_value,
                'price_change': price_change,
                'volatility': volatility,
                'strategy_id': self.strategy_id,
                'strategy_type': 'momentum',
                'is_exit_signal': True
            }
        )
    
    def _calculate_price_change(self, symbol_data: pd.Series) -> float:
        """Calculate recent price change"""
        if len(symbol_data) < 2:
            return 0.0
        
        recent_price = symbol_data.iloc[-1]
        previous_price = symbol_data.iloc[-2]
        
        if previous_price == 0:
            return 0.0
        
        return (recent_price - previous_price) / previous_price
    
    def _calculate_volatility(self, symbol_data: pd.Series, window: int = 10) -> float:
        """Calculate rolling volatility"""
        if len(symbol_data) < window:
            return 0.01  # Default low volatility
        
        returns = symbol_data.pct_change().dropna()
        if len(returns) < 2:
            return 0.01
        
        return returns.tail(window).std()
    
    def get_strategy_specific_metrics(self) -> Dict[str, Any]:
        """Get momentum-specific performance metrics"""
        base_metrics = self.get_strategy_metrics()
        
        # Calculate momentum-specific metrics
        momentum_signals = [s for s in self._last_signals if 'momentum' in s.metadata]
        entry_signals = [s for s in momentum_signals if not s.metadata.get('is_exit_signal', False)]
        exit_signals = [s for s in momentum_signals if s.metadata.get('is_exit_signal', False)]
        
        return {
            'base_metrics': base_metrics,
            'momentum_specific': {
                'total_momentum_signals': len(momentum_signals),
                'entry_signals': len(entry_signals),
                'exit_signals': len(exit_signals),
                'average_momentum_strength': self._calculate_average_momentum(),
                'signal_distribution': self._get_signal_strength_distribution()
            }
        }
    
    def _calculate_average_momentum(self) -> float:
        """Calculate average momentum from recent signals"""
        momentum_values = [
            s.metadata.get('momentum', 0.0) 
            for s in self._last_signals 
            if 'momentum' in s.metadata
        ]
        
        if not momentum_values:
            return 0.0
        
        return sum(abs(v) for v in momentum_values) / len(momentum_values)
    
    def _get_signal_strength_distribution(self) -> Dict[str, int]:
        """Get distribution of signal strengths"""
        distribution = {'STRONG': 0, 'MODERATE': 0, 'WEAK': 0}
        
        for signal in self._last_signals:
            strength_name = signal.strength.name if hasattr(signal.strength, 'name') else str(signal.strength)
            if strength_name in distribution:
                distribution[strength_name] += 1
        
        return distribution
