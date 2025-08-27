"""
Mean Reversion Strategy Implementation - Extracted from Core Engine
================================================================

Professional mean reversion strategy implementation following clean architecture.
Extracted from unified_core_engine.py to eliminate strategy logic contamination.

Author: Professional Trading System Architecture
Version: 2.0.0
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from ..strategy_interfaces import BaseStrategy, StrategyType, StrategyContext, StrategyMetrics
from ..signal_generation.signal_generator import TradingSignal, SignalType, SignalStrength


class MeanReversionStrategy(BaseStrategy):
    """
    Clean mean reversion strategy implementation.
    
    Handles all mean reversion-specific logic that was previously
    embedded in the core engine.
    """
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MEAN_REVERSION
    
    @property
    def required_indicators(self) -> List[str]:
        return [
            'MA_MeanReversion', 'BB_MeanReversion', 'RSI_MeanReversion',
            'price', 'volume', 'volatility'
        ]
    
    def _get_required_parameters(self) -> List[str]:
        return [
            'ma_weight', 'bb_weight', 'rsi_weight', 'entry_threshold',
            'exit_threshold', 'position_size', 'confidence_threshold'
        ]
    
    async def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate mean reversion trading signals"""
        signals = []
        
        # Extract context
        market_data = context.market_data
        portfolio_state = context.portfolio_state
        timestamp = context.timestamp
        
        # Get strategy parameters with defaults
        ma_weight = self._config.get('ma_weight', 0.2)
        bb_weight = self._config.get('bb_weight', 0.5)
        rsi_weight = self._config.get('rsi_weight', 0.3)
        entry_threshold = self._config.get('entry_threshold', 0.3)
        exit_threshold = self._config.get('exit_threshold', 0.2)
        confidence_threshold = self._config.get('confidence_threshold', 0.5)
        
        # Process each symbol
        for symbol in self._get_tradeable_symbols(market_data):
            # Extract mean reversion indicators
            mr_indicators = self._extract_mean_reversion_indicators(market_data, symbol)
            
            if not mr_indicators:
                continue
            
            # Calculate composite signal
            composite_signal = self._calculate_composite_signal(
                mr_indicators, ma_weight, bb_weight, rsi_weight
            )
            
            # Calculate confidence
            confidence = self._calculate_signal_confidence(mr_indicators, composite_signal)
            
            # Skip low confidence signals
            if confidence < confidence_threshold:
                continue
            
            # Check position state
            has_position = symbol in portfolio_state.get('positions', {})
            
            # Generate appropriate signal
            if has_position:
                signal = self._process_exit_signal(
                    symbol, composite_signal, mr_indicators, confidence,
                    exit_threshold, timestamp
                )
            else:
                signal = self._process_entry_signal(
                    symbol, composite_signal, mr_indicators, confidence,
                    entry_threshold, timestamp
                )
            
            if signal:
                signals.append(signal)
        
        return signals
    
    def _get_tradeable_symbols(self, market_data: pd.DataFrame) -> List[str]:
        """Extract tradeable symbols from market data"""
        symbols = set()
        
        for col in market_data.columns:
            if col.endswith(('_MA_MeanReversion', '_BB_MeanReversion', '_RSI_MeanReversion')):
                symbol = col.split('_')[0]
                symbols.add(symbol)
        
        return list(symbols)
    
    def _extract_mean_reversion_indicators(self, market_data: pd.DataFrame, 
                                         symbol: str) -> Optional[Dict[str, float]]:
        """Extract mean reversion indicators for a symbol"""
        indicators = {}
        
        # Define indicator column names
        ma_col = f"{symbol}_MA_MeanReversion"
        bb_col = f"{symbol}_BB_MeanReversion"
        rsi_col = f"{symbol}_RSI_MeanReversion"
        
        try:
            # Extract latest values
            if ma_col in market_data.columns:
                indicators['ma_signal'] = float(market_data[ma_col].iloc[-1])
            
            if bb_col in market_data.columns:
                indicators['bb_signal'] = float(market_data[bb_col].iloc[-1])
            
            if rsi_col in market_data.columns:
                indicators['rsi_signal'] = float(market_data[rsi_col].iloc[-1])
            
            # Require at least one indicator
            if not indicators:
                return None
            
            return indicators
            
        except (IndexError, ValueError, KeyError):
            return None
    
    def _calculate_composite_signal(self, indicators: Dict[str, float],
                                  ma_weight: float, bb_weight: float, 
                                  rsi_weight: float) -> float:
        """Calculate weighted composite mean reversion signal"""
        ma_signal = indicators.get('ma_signal', 0.0)
        bb_signal = indicators.get('bb_signal', 0.0)
        rsi_signal = indicators.get('rsi_signal', 0.0)
        
        # Normalize weights
        total_weight = ma_weight + bb_weight + rsi_weight
        if total_weight == 0:
            return 0.0
        
        ma_weight /= total_weight
        bb_weight /= total_weight
        rsi_weight /= total_weight
        
        # Calculate weighted composite
        composite = (bb_signal * bb_weight + 
                    rsi_signal * rsi_weight + 
                    ma_signal * ma_weight)
        
        return composite
    
    def _calculate_signal_confidence(self, indicators: Dict[str, float],
                                   composite_signal: float) -> float:
        """Calculate signal confidence based on indicator agreement"""
        signals = list(indicators.values())
        
        if not signals:
            return 0.0
        
        # Base confidence from composite strength
        base_confidence = min(0.95, 0.5 + abs(composite_signal))
        
        # Adjust for indicator agreement
        signal_directions = [1 if s > 0 else -1 if s < 0 else 0 for s in signals]
        agreement = abs(sum(signal_directions)) / len(signal_directions)
        
        # Boost confidence when indicators agree
        confidence_boost = agreement * 0.2
        final_confidence = min(0.95, base_confidence + confidence_boost)
        
        return final_confidence
    
    def _process_entry_signal(self, symbol: str, composite_signal: float,
                            indicators: Dict[str, float], confidence: float,
                            entry_threshold: float, timestamp: datetime) -> Optional[TradingSignal]:
        """Process mean reversion entry signals"""
        
        # Check entry conditions
        bb_signal = indicators.get('bb_signal', 0.0)
        rsi_signal = indicators.get('rsi_signal', 0.0)
        
        # Enhanced entry logic - multiple conditions
        strong_bb_signal = bb_signal > 0.5
        strong_rsi_signal = rsi_signal > 0.25
        strong_composite = composite_signal > entry_threshold
        
        should_enter = strong_bb_signal or strong_composite or strong_rsi_signal
        
        if not should_enter:
            return None
        
        # Determine signal strength
        if composite_signal > 0.4:
            strength = SignalStrength.STRONG
        elif composite_signal > 0.25:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK
        
        # Position sizing based on signal strength
        base_position_size = self._config.get('position_size', 0.25)
        if composite_signal > 0.5:
            position_size = min(0.4, base_position_size * 1.5)
        else:
            position_size = base_position_size
        
        return TradingSignal(
            symbol_pair=symbol,
            signal_type=SignalType.LONG,  # Mean reversion typically goes long
            strength=strength,
            confidence=confidence,
            position_size=position_size,
            entry_price=0.0,
            timestamp=timestamp,
            metadata={
                'signal_source': 'mean_reversion',
                'ma_signal': indicators.get('ma_signal', 0.0),
                'bb_signal': indicators.get('bb_signal', 0.0),
                'rsi_signal': indicators.get('rsi_signal', 0.0),
                'composite_signal': composite_signal,
                'strategy_id': self.strategy_id,
                'strategy_type': 'mean_reversion',
                'is_exit_signal': False,
                'entry_conditions': {
                    'strong_bb': strong_bb_signal,
                    'strong_rsi': strong_rsi_signal,
                    'strong_composite': strong_composite
                }
            }
        )
    
    def _process_exit_signal(self, symbol: str, composite_signal: float,
                           indicators: Dict[str, float], confidence: float,
                           exit_threshold: float, timestamp: datetime) -> Optional[TradingSignal]:
        """Process mean reversion exit signals"""
        
        # Exit when mean reversion signal weakens
        should_exit = composite_signal < exit_threshold
        
        # Additional exit conditions
        bb_signal = indicators.get('bb_signal', 0.0)
        rsi_signal = indicators.get('rsi_signal', 0.0)
        
        # Exit if all indicators turn negative
        all_negative = all(signal < 0.1 for signal in indicators.values())
        
        if should_exit or all_negative:
            return TradingSignal(
                symbol_pair=symbol,
                signal_type=SignalType.CLOSE_LONG,
                strength=SignalStrength.MODERATE,
                confidence=confidence,
                position_size=1.0,  # Close full position
                entry_price=0.0,
                timestamp=timestamp,
                metadata={
                    'signal_source': 'mean_reversion_exit',
                    'exit_reason': 'signal_weakness' if should_exit else 'all_indicators_negative',
                    'ma_signal': indicators.get('ma_signal', 0.0),
                    'bb_signal': bb_signal,
                    'rsi_signal': rsi_signal,
                    'composite_signal': composite_signal,
                    'strategy_id': self.strategy_id,
                    'strategy_type': 'mean_reversion',
                    'is_exit_signal': True
                }
            )
        
        return None
    
    def get_strategy_specific_metrics(self) -> Dict[str, Any]:
        """Get mean reversion specific metrics"""
        base_metrics = self.get_strategy_metrics()
        
        # Calculate mean reversion specific metrics
        mr_signals = [s for s in self._last_signals if s.metadata.get('strategy_type') == 'mean_reversion']
        entry_signals = [s for s in mr_signals if not s.metadata.get('is_exit_signal', False)]
        exit_signals = [s for s in mr_signals if s.metadata.get('is_exit_signal', False)]
        
        return {
            'base_metrics': base_metrics,
            'mean_reversion_specific': {
                'total_mr_signals': len(mr_signals),
                'entry_signals': len(entry_signals),
                'exit_signals': len(exit_signals),
                'average_composite_signal': self._calculate_average_composite_signal(),
                'indicator_performance': self._get_indicator_performance()
            }
        }
    
    def _calculate_average_composite_signal(self) -> float:
        """Calculate average composite signal strength"""
        composite_values = [
            s.metadata.get('composite_signal', 0.0)
            for s in self._last_signals
            if 'composite_signal' in s.metadata
        ]
        
        if not composite_values:
            return 0.0
        
        return sum(composite_values) / len(composite_values)
    
    def _get_indicator_performance(self) -> Dict[str, float]:
        """Get performance breakdown by indicator"""
        ma_values = []
        bb_values = []
        rsi_values = []
        
        for signal in self._last_signals:
            metadata = signal.metadata
            if 'ma_signal' in metadata:
                ma_values.append(abs(metadata['ma_signal']))
            if 'bb_signal' in metadata:
                bb_values.append(abs(metadata['bb_signal']))
            if 'rsi_signal' in metadata:
                rsi_values.append(abs(metadata['rsi_signal']))
        
        return {
            'average_ma_strength': sum(ma_values) / len(ma_values) if ma_values else 0.0,
            'average_bb_strength': sum(bb_values) / len(bb_values) if bb_values else 0.0,
            'average_rsi_strength': sum(rsi_values) / len(rsi_values) if rsi_values else 0.0
        }
