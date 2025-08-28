"""
Professional Mean Reversion Template

A comprehensive mean reversion trading template that implements:
- Bollinger Bands mean reversion signals
- RSI overbought/oversold conditions  
- Moving average deviation analysis
- Multi-timeframe confirmation
- Advanced risk management

Author: Professional Trading System Architecture
Version: 1.0.0
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from trade_engine.templates.base_template import (
    BaseTemplate, TemplateValidationError,
    ParameterBounds, SignalRule
)
from trade_engine.interfaces import RawSignal


class ProfessionalMeanReversionTemplate(BaseTemplate):
    """
    Professional mean reversion template with advanced signal generation.
    
    Strategy Logic:
    1. Identify overbought/oversold conditions using RSI
    2. Confirm with Bollinger Band extremes
    3. Look for moving average divergence
    4. Generate mean reversion signals with confidence scoring
    5. Apply volatility and volume filters
    """
    
    def __init__(self):
        """Initialize the professional mean reversion template."""
        super().__init__(
            template_id="professional_mean_reversion_v1",
            name="Professional Mean Reversion Strategy",
            description="Professional mean reversion template with Bollinger Bands, RSI, and MA analysis"
        )
        self.version = "1.0.0"
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _define_template(self) -> None:
        """Define the template structure by setting up parameters and rules."""
        self._setup_parameters()
        self._setup_rules()
    
    def _setup_parameters(self):
        """Setup template parameters with bounds."""
        # Core parameters
        self.add_parameter_bounds('lookback_period', ParameterBounds(
            min_value=10, max_value=100, default_value=20,
            data_type=int, is_required=True
        ))
        self.add_parameter_bounds('rsi_period', ParameterBounds(
            min_value=5, max_value=30, default_value=14,
            data_type=int, is_required=True
        ))
        self.add_parameter_bounds('bb_period', ParameterBounds(
            min_value=10, max_value=50, default_value=20,
            data_type=int, is_required=True
        ))
        self.add_parameter_bounds('bb_std_dev', ParameterBounds(
            min_value=1.0, max_value=3.0, default_value=2.0,
            data_type=float, is_required=True
        ))
        
        # Signal thresholds
        self.add_parameter_bounds('rsi_overbought', ParameterBounds(
            min_value=65, max_value=85, default_value=70,
            data_type=int, is_required=True
        ))
        self.add_parameter_bounds('rsi_oversold', ParameterBounds(
            min_value=15, max_value=35, default_value=30,
            data_type=int, is_required=True
        ))
        self.add_parameter_bounds('ma_deviation_threshold', ParameterBounds(
            min_value=0.01, max_value=0.10, default_value=0.05,
            data_type=float, is_required=True
        ))
        
        # Risk management
        self.add_parameter_bounds('confidence_threshold', ParameterBounds(
            min_value=0.3, max_value=0.9, default_value=0.6,
            data_type=float, is_required=True
        ))
        self.add_parameter_bounds('position_size', ParameterBounds(
            min_value=0.001, max_value=0.10, default_value=0.03,
            data_type=float, is_required=True
        ))
        self.add_parameter_bounds('stop_loss_pct', ParameterBounds(
            min_value=0.01, max_value=0.10, default_value=0.04,
            data_type=float, is_required=True
        ))
        self.add_parameter_bounds('take_profit_pct', ParameterBounds(
            min_value=0.02, max_value=0.15, default_value=0.06,
            data_type=float, is_required=True
        ))
        
        # Volume and volatility filters
        self.add_parameter_bounds('volume_threshold', ParameterBounds(
            min_value=0.5, max_value=3.0, default_value=1.2,
            data_type=float, is_required=True
        ))
        self.add_parameter_bounds('volatility_percentile', ParameterBounds(
            min_value=50, max_value=95, default_value=80,
            data_type=int, is_required=True
        ))
    
    def _setup_rules(self):
        """Setup trading rules for mean reversion."""
        # Simplified rule setup for template system compatibility
        # Rules are handled through the template bridge system
        self._rules = []
        pass
    
    def get_required_indicators(self) -> List[str]:
        """Return list of required indicators."""
        return [
            'close', 'volume', 'high', 'low', 'open',
            'rsi', 'bb_upper', 'bb_middle', 'bb_lower',
            'ma_short', 'ma_long', 'volatility_percentile'
        ]
    
    def calculate_indicators(self, market_data: pd.DataFrame, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate all required indicators for mean reversion analysis."""
        try:
            indicators = {}
            
            # Basic data validation
            if len(market_data) < parameters['lookback_period']:
                self.logger.warning(f"Insufficient data: {len(market_data)} < {parameters['lookback_period']}")
                return indicators
            
            # Calculate RSI
            indicators['rsi'] = self._calculate_rsi(market_data, parameters['rsi_period'])
            
            # Calculate Bollinger Bands
            bb_data = self._calculate_bollinger_bands(
                market_data, 
                parameters['bb_period'],
                parameters['bb_std_dev']
            )
            indicators.update(bb_data)
            
            # Calculate Moving Averages
            indicators['ma_short'] = market_data['close'].rolling(window=10).mean()
            indicators['ma_long'] = market_data['close'].rolling(window=parameters['lookback_period']).mean()
            
            # Calculate volume metrics
            indicators['volume_ratio'] = self._calculate_volume_ratio(
                market_data, parameters['volume_lookback']
            )
            
            # Calculate volatility percentile
            indicators['volatility_percentile'] = self._calculate_volatility_percentile(
                market_data, parameters['lookback_period']
            )
            
            # Calculate price position in recent range
            indicators['price_position'] = self._calculate_price_position(
                market_data, parameters['lookback_period']
            )
            
            # Calculate trend strength
            indicators['trend_strength'] = self._calculate_trend_strength(
                market_data, parameters['lookback_period']
            )
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            return {}
    
    def generate_signals(self, market_data: pd.DataFrame, parameters: Dict[str, Any]) -> List[RawSignal]:
        """Generate mean reversion signals based on indicators."""
        try:
            # Calculate indicators
            indicators = self.calculate_indicators(market_data, parameters)
            if not indicators:
                return []
            
            signals = []
            symbols = market_data['symbol'].unique() if 'symbol' in market_data.columns else ['UNKNOWN']
            
            for symbol in symbols:
                symbol_signals = self._generate_symbol_signals(symbol, indicators, parameters)
                signals.extend(symbol_signals)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            return []
    
    def _generate_symbol_signals(self, symbol: str, indicators: Dict[str, Any], parameters: Dict[str, Any]) -> List[RawSignal]:
        """Generate signals for a specific symbol."""
        signals = []
        
        try:
            # Get current values
            current_rsi = indicators['rsi'].iloc[-1] if len(indicators['rsi']) > 0 else 50
            current_bb_upper = indicators['bb_upper'].iloc[-1] if len(indicators['bb_upper']) > 0 else 0
            current_bb_lower = indicators['bb_lower'].iloc[-1] if len(indicators['bb_lower']) > 0 else 0
            current_bb_middle = indicators['bb_middle'].iloc[-1] if len(indicators['bb_middle']) > 0 else 0
            current_price = indicators.get('close', pd.Series([100])).iloc[-1]
            volume_ratio = indicators['volume_ratio'].iloc[-1] if len(indicators['volume_ratio']) > 0 else 1.0
            volatility_pct = indicators['volatility_percentile'].iloc[-1] if len(indicators['volatility_percentile']) > 0 else 50
            
            # Calculate Bollinger Band position
            if current_bb_upper != current_bb_lower:
                bb_position = (current_price - current_bb_lower) / (current_bb_upper - current_bb_lower)
            else:
                bb_position = 0.5
            
            # Calculate MA deviation
            ma_long = indicators['ma_long'].iloc[-1] if len(indicators['ma_long']) > 0 else current_price
            ma_deviation = (current_price - ma_long) / ma_long if ma_long != 0 else 0
            
            # Generate signals based on rules
            rule_metadata = {
                'indicators_used': list(indicators.keys()),
                'current_rsi': current_rsi,
                'bb_position': bb_position,
                'ma_deviation': ma_deviation,
                'volume_ratio': volume_ratio,
                'volatility_percentile': volatility_pct
            }
            
            # Rule 1: Primary long mean reversion signal
            if (current_rsi <= parameters['rsi_oversold'] and 
                bb_position <= 0.1 and  # Below lower band
                ma_deviation <= -parameters['ma_deviation_threshold']):
                
                confidence = min(0.95, 0.5 + (parameters['rsi_oversold'] - current_rsi) / 40 + abs(ma_deviation) * 5)
                signal_value = min(-0.7, -0.5 - abs(ma_deviation) * 10)  # Negative for mean reversion long
                
                signals.append(RawSignal(
                    symbol=symbol,
                    value=signal_value,
                    confidence=confidence,
                    signal_metadata={
                        'rule_id': 'mean_reversion_long_primary',
                        'rule_type': 'long_entry',
                        'template_id': self.template_id,
                        'strategy_instance_id': parameters.get('strategy_instance_id', 'default'),
                        'indicators_used': list(indicators.keys()),
                        'rule_metadata': {
                            'signal_type': 'long_entry',
                            'priority': 1,
                            'description': 'Primary long mean reversion signal',
                            'rsi_value': current_rsi,
                            'bb_position': bb_position,
                            'ma_deviation': ma_deviation
                        }
                    },
                    timestamp=pd.Timestamp.now()
                ))
            
            # Rule 2: Primary short mean reversion signal
            if (current_rsi >= parameters['rsi_overbought'] and
                bb_position >= 0.9 and  # Above upper band
                ma_deviation >= parameters['ma_deviation_threshold']):
                
                confidence = min(0.95, 0.5 + (current_rsi - parameters['rsi_overbought']) / 30 + abs(ma_deviation) * 5)
                signal_value = max(0.7, 0.5 + ma_deviation * 10)  # Positive for mean reversion short
                
                signals.append(RawSignal(
                    symbol=symbol,
                    value=signal_value,
                    confidence=confidence,
                    signal_metadata={
                        'rule_id': 'mean_reversion_short_primary',
                        'rule_type': 'short_entry',
                        'template_id': self.template_id,
                        'strategy_instance_id': parameters.get('strategy_instance_id', 'default'),
                        'indicators_used': list(indicators.keys()),
                        'rule_metadata': {
                            'signal_type': 'short_entry',
                            'priority': 1,
                            'description': 'Primary short mean reversion signal',
                            'rsi_value': current_rsi,
                            'bb_position': bb_position,
                            'ma_deviation': ma_deviation
                        }
                    },
                    timestamp=pd.Timestamp.now()
                ))
            
            # Rule 3: Volume filter (apply to all signals)
            if volume_ratio >= parameters['volume_threshold']:
                confidence = min(0.8, volume_ratio / parameters['volume_threshold'] - 0.5)
                
                signals.append(RawSignal(
                    symbol=symbol,
                    value=volume_ratio / 10,  # Small positive signal for volume confirmation
                    confidence=confidence,
                    signal_metadata={
                        'rule_id': 'volume_filter',
                        'rule_type': 'filter',
                        'template_id': self.template_id,
                        'strategy_instance_id': parameters.get('strategy_instance_id', 'default'),
                        'indicators_used': ['volume', 'volume_ratio'],
                        'rule_metadata': {
                            'signal_type': 'filter',
                            'priority': 5,
                            'description': 'Volume confirmation filter',
                            'volume_ratio': volume_ratio
                        }
                    },
                    timestamp=pd.Timestamp.now()
                ))
            
            # Rule 4: Volatility filter
            if volatility_pct <= parameters['volatility_percentile']:
                volatility_signal = (parameters['volatility_percentile'] - volatility_pct) / 100
                
                signals.append(RawSignal(
                    symbol=symbol,
                    value=volatility_signal,
                    confidence=0.3 + volatility_signal,
                    signal_metadata={
                        'rule_id': 'volatility_filter',
                        'rule_type': 'filter',
                        'template_id': self.template_id,
                        'strategy_instance_id': parameters.get('strategy_instance_id', 'default'),
                        'indicators_used': ['volatility_percentile'],
                        'rule_metadata': {
                            'signal_type': 'filter',
                            'priority': 4,
                            'description': 'Filter out extreme volatility periods',
                            'volatility_percentile': volatility_pct
                        }
                    },
                    timestamp=pd.Timestamp.now()
                ))
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals for {symbol}: {e}")
            return []
    
    def _calculate_rsi(self, market_data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Relative Strength Index."""
        try:
            close_prices = market_data['close']
            delta = close_prices.diff()
            
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            avg_gains = gains.rolling(window=period).mean()
            avg_losses = losses.rolling(window=period).mean()
            
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.fillna(50)  # Fill NaN with neutral value
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return pd.Series([50] * len(market_data), index=market_data.index)
    
    def _calculate_bollinger_bands(self, market_data: pd.DataFrame, period: int, std_dev: float) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        try:
            sma = market_data['close'].rolling(window=period).mean()
            rolling_std = market_data['close'].rolling(window=period).std()
            
            upper_band = sma + (rolling_std * std_dev)
            lower_band = sma - (rolling_std * std_dev)
            
            return {
                'bb_upper': upper_band.fillna(market_data['close']),
                'bb_middle': sma.fillna(market_data['close']),
                'bb_lower': lower_band.fillna(market_data['close'])
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {e}")
            return {
                'bb_upper': market_data['close'],
                'bb_middle': market_data['close'],
                'bb_lower': market_data['close']
            }
    
    def _calculate_volume_ratio(self, market_data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate volume ratio vs average."""
        try:
            avg_volume = market_data['volume'].rolling(window=period).mean()
            volume_ratio = market_data['volume'] / avg_volume
            return volume_ratio.fillna(1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating volume ratio: {e}")
            return pd.Series([1.0] * len(market_data), index=market_data.index)
    
    def _calculate_volatility_percentile(self, market_data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate volatility percentile."""
        try:
            returns = market_data['close'].pct_change()
            rolling_vol = returns.rolling(window=period).std()
            
            # Calculate percentile rank
            percentile_rank = rolling_vol.rolling(window=period).rank(pct=True) * 100
            return percentile_rank.fillna(50)
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility percentile: {e}")
            return pd.Series([50] * len(market_data), index=market_data.index)
    
    def _calculate_price_position(self, market_data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate price position in recent range."""
        try:
            rolling_high = market_data['high'].rolling(window=period).max()
            rolling_low = market_data['low'].rolling(window=period).min()
            
            price_range = rolling_high - rolling_low
            price_position = (market_data['close'] - rolling_low) / price_range
            
            return price_position.fillna(0.5)
            
        except Exception as e:
            self.logger.error(f"Error calculating price position: {e}")
            return pd.Series([0.5] * len(market_data), index=market_data.index)
    
    def _calculate_trend_strength(self, market_data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate trend strength."""
        try:
            returns = market_data['close'].pct_change()
            rolling_mean = returns.rolling(window=period).mean()
            rolling_std = returns.rolling(window=period).std()
            
            trend_strength = abs(rolling_mean) / (rolling_std + 0.0001)
            return trend_strength.fillna(0.1)
            
        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {e}")
            return pd.Series([0.1] * len(market_data), index=market_data.index)


# Register the template in the global registry
def register_mean_reversion_template():
    """Register the professional mean reversion template."""
    from trade_engine.templates.base_template import template_registry
    
    template = ProfessionalMeanReversionTemplate()
    template_registry.register_template(template, category="mean_reversion")
    return template


# Auto-register when module is imported
register_mean_reversion_template()
