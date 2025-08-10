"""
Signal Generator Building Block

Signal generation building blocks for technical indicators and signal processing.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field

from strategy_layer.base import StrategyError


@dataclass
class SignalConfig:
    """Configuration for signal generation"""
    indicator_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    threshold: Optional[float] = None
    smoothing: Optional[str] = None
    lookback_period: int = 20
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'indicator_type': self.indicator_type,
            'parameters': self.parameters,
            'weight': self.weight,
            'threshold': self.threshold,
            'smoothing': self.smoothing,
            'lookback_period': self.lookback_period
        }


class BaseIndicator(ABC):
    """Base class for technical indicators"""
    
    def __init__(self, config: SignalConfig):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._validate_config()
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """Calculate indicator values"""
        pass
    
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> float:
        """Generate trading signal from indicator"""
        pass
    
    def _validate_config(self):
        """Validate indicator configuration"""
        if not self.config.indicator_type:
            raise StrategyError("Indicator type is required")
        
        if self.config.weight < 0 or self.config.weight > 1:
            raise StrategyError("Weight must be between 0 and 1")
    
    def _smooth_signal(self, signal: pd.Series) -> pd.Series:
        """Apply smoothing to signal"""
        if not self.config.smoothing:
            return signal
        
        if self.config.smoothing == 'sma':
            return signal.rolling(window=self.config.lookback_period).mean()
        elif self.config.smoothing == 'ema':
            return signal.ewm(span=self.config.lookback_period).mean()
        elif self.config.smoothing == 'median':
            return signal.rolling(window=self.config.lookback_period).median()
        else:
            self.logger.warning(f"Unknown smoothing method: {self.config.smoothing}")
            return signal


class RSIIndicator(BaseIndicator):
    """Relative Strength Index (RSI) indicator"""
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """Calculate RSI values"""
        try:
            close_prices = data['close']
            period = self.config.parameters.get('period', 14)
            
            # Calculate price changes
            delta = close_prices.diff()
            
            # Separate gains and losses
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Calculate average gains and losses
            avg_gains = gains.rolling(window=period).mean()
            avg_losses = losses.rolling(window=period).mean()
            
            # Calculate RS and RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return pd.Series(index=data.index, dtype=float)
    
    def generate_signal(self, data: pd.DataFrame) -> float:
        """Generate RSI-based signal"""
        try:
            rsi = self.calculate(data)
            if rsi.empty:
                return 0.0
            
            current_rsi = rsi.iloc[-1]
            
            # Generate signal based on RSI levels
            if current_rsi < 30:  # Oversold
                signal = 1.0
            elif current_rsi > 70:  # Overbought
                signal = -1.0
            else:
                # Normalize signal between -1 and 1
                signal = (50 - current_rsi) / 50
            
            # Apply threshold if specified
            if self.config.threshold:
                if abs(signal) < self.config.threshold:
                    signal = 0.0
            
            return signal * self.config.weight
            
        except Exception as e:
            self.logger.error(f"Error generating RSI signal: {e}")
            return 0.0


class MACDIndicator(BaseIndicator):
    """Moving Average Convergence Divergence (MACD) indicator"""
    
    def calculate(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD values (MACD line, signal line, histogram)"""
        try:
            close_prices = data['close']
            fast_period = self.config.parameters.get('fast', 12)
            slow_period = self.config.parameters.get('slow', 26)
            signal_period = self.config.parameters.get('signal', 9)
            
            # Calculate fast and slow EMAs
            ema_fast = close_prices.ewm(span=fast_period).mean()
            ema_slow = close_prices.ewm(span=slow_period).mean()
            
            # Calculate MACD line
            macd_line = ema_fast - ema_slow
            
            # Calculate signal line
            signal_line = macd_line.ewm(span=signal_period).mean()
            
            # Calculate histogram
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
            
        except Exception as e:
            self.logger.error(f"Error calculating MACD: {e}")
            empty_series = pd.Series(index=data.index, dtype=float)
            return empty_series, empty_series, empty_series
    
    def generate_signal(self, data: pd.DataFrame) -> float:
        """Generate MACD-based signal"""
        try:
            macd_line, signal_line, histogram = self.calculate(data)
            
            if macd_line.empty or signal_line.empty:
                return 0.0
            
            # Current values
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_histogram = histogram.iloc[-1]
            
            # Previous values
            prev_macd = macd_line.iloc[-2] if len(macd_line) > 1 else current_macd
            prev_signal = signal_line.iloc[-2] if len(signal_line) > 1 else current_signal
            prev_histogram = histogram.iloc[-2] if len(histogram) > 1 else current_histogram
            
            # Generate signal based on MACD crossovers and histogram
            signal = 0.0
            
            # MACD line crossover
            if current_macd > current_signal and prev_macd <= prev_signal:
                signal = 1.0  # Bullish crossover
            elif current_macd < current_signal and prev_macd >= prev_signal:
                signal = -1.0  # Bearish crossover
            
            # Histogram momentum
            if current_histogram > prev_histogram and current_histogram > 0:
                signal += 0.5  # Increasing positive histogram
            elif current_histogram < prev_histogram and current_histogram < 0:
                signal -= 0.5  # Decreasing negative histogram
            
            # Normalize signal
            signal = max(-1.0, min(1.0, signal))
            
            # Apply threshold if specified
            if self.config.threshold:
                if abs(signal) < self.config.threshold:
                    signal = 0.0
            
            return signal * self.config.weight
            
        except Exception as e:
            self.logger.error(f"Error generating MACD signal: {e}")
            return 0.0


class BollingerBandsIndicator(BaseIndicator):
    """Bollinger Bands indicator"""
    
    def calculate(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands (upper, middle, lower)"""
        try:
            close_prices = data['close']
            period = self.config.parameters.get('period', 20)
            std_dev = self.config.parameters.get('std_dev', 2)
            
            # Calculate middle band (SMA)
            middle_band = close_prices.rolling(window=period).mean()
            
            # Calculate standard deviation
            rolling_std = close_prices.rolling(window=period).std()
            
            # Calculate upper and lower bands
            upper_band = middle_band + (rolling_std * std_dev)
            lower_band = middle_band - (rolling_std * std_dev)
            
            return upper_band, middle_band, lower_band
            
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {e}")
            empty_series = pd.Series(index=data.index, dtype=float)
            return empty_series, empty_series, empty_series
    
    def generate_signal(self, data: pd.DataFrame) -> float:
        """Generate Bollinger Bands-based signal"""
        try:
            upper_band, middle_band, lower_band = self.calculate(data)
            
            if upper_band.empty or middle_band.empty or lower_band.empty:
                return 0.0
            
            current_price = data['close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_middle = middle_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            # Calculate %B (position within bands)
            if current_upper != current_lower:
                percent_b = (current_price - current_lower) / (current_upper - current_lower)
            else:
                percent_b = 0.5
            
            # Generate signal based on %B
            if percent_b > 1.0:  # Above upper band
                signal = -1.0  # Bearish
            elif percent_b < 0.0:  # Below lower band
                signal = 1.0  # Bullish
            else:
                # Normalize signal between -1 and 1
                signal = (percent_b - 0.5) * 2
            
            # Apply threshold if specified
            if self.config.threshold:
                if abs(signal) < self.config.threshold:
                    signal = 0.0
            
            return signal * self.config.weight
            
        except Exception as e:
            self.logger.error(f"Error generating Bollinger Bands signal: {e}")
            return 0.0


class ZScoreIndicator(BaseIndicator):
    """Z-Score indicator for pair trading"""
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """Calculate Z-Score values"""
        try:
            # For pair trading, we need two price series
            if 'price1' not in data.columns or 'price2' not in data.columns:
                self.logger.error("Z-Score requires price1 and price2 columns")
                return pd.Series(index=data.index, dtype=float)
            
            price1 = data['price1']
            price2 = data['price2']
            period = self.config.parameters.get('period', 20)
            
            # Calculate spread
            spread = price1 - price2
            
            # Calculate rolling mean and standard deviation
            rolling_mean = spread.rolling(window=period).mean()
            rolling_std = spread.rolling(window=period).std()
            
            # Calculate Z-Score
            z_score = (spread - rolling_mean) / rolling_std
            
            return z_score
            
        except Exception as e:
            self.logger.error(f"Error calculating Z-Score: {e}")
            return pd.Series(index=data.index, dtype=float)
    
    def generate_signal(self, data: pd.DataFrame) -> float:
        """Generate Z-Score-based signal"""
        try:
            z_score = self.calculate(data)
            
            if z_score.empty:
                return 0.0
            
            current_z_score = z_score.iloc[-1]
            
            # Generate signal based on Z-Score levels
            if current_z_score > 2.0:  # Overvalued
                signal = -1.0  # Short signal
            elif current_z_score < -2.0:  # Undervalued
                signal = 1.0  # Long signal
            else:
                # Normalize signal between -1 and 1
                signal = -current_z_score / 2.0
            
            # Apply threshold if specified
            if self.config.threshold:
                if abs(signal) < self.config.threshold:
                    signal = 0.0
            
            return signal * self.config.weight
            
        except Exception as e:
            self.logger.error(f"Error generating Z-Score signal: {e}")
            return 0.0


class SignalGenerator:
    """Main signal generator that combines multiple indicators"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.indicators = {}
        self._setup_indicators()
    
    def _setup_indicators(self):
        """Setup indicators from configuration"""
        try:
            indicators_config = self.config.get('indicators', [])
            
            for indicator_config in indicators_config:
                indicator_type = indicator_config.get('type')
                signal_config = SignalConfig(
                    indicator_type=indicator_type,
                    parameters=indicator_config.get('parameters', {}),
                    weight=indicator_config.get('weight', 1.0),
                    threshold=indicator_config.get('threshold'),
                    smoothing=indicator_config.get('smoothing'),
                    lookback_period=indicator_config.get('lookback_period', 20)
                )
                
                # Create indicator instance
                indicator = self._create_indicator(signal_config)
                if indicator:
                    self.indicators[indicator_config.get('name', indicator_type)] = indicator
            
            self.logger.info(f"Setup {len(self.indicators)} indicators")
            
        except Exception as e:
            self.logger.error(f"Error setting up indicators: {e}")
    
    def _create_indicator(self, config: SignalConfig) -> Optional[BaseIndicator]:
        """Create indicator instance based on type"""
        try:
            indicator_type = config.indicator_type.lower()
            
            if indicator_type == 'rsi':
                return RSIIndicator(config)
            elif indicator_type == 'macd':
                return MACDIndicator(config)
            elif indicator_type == 'bollinger_bands':
                return BollingerBandsIndicator(config)
            elif indicator_type == 'zscore':
                return ZScoreIndicator(config)
            else:
                self.logger.warning(f"Unknown indicator type: {indicator_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating indicator {config.indicator_type}: {e}")
            return None
    
    def generate_signals(self, data: pd.DataFrame) -> Dict[str, float]:
        """Generate signals from all indicators"""
        try:
            signals = {}
            
            for name, indicator in self.indicators.items():
                try:
                    signal = indicator.generate_signal(data)
                    signals[name] = signal
                except Exception as e:
                    self.logger.error(f"Error generating signal for {name}: {e}")
                    signals[name] = 0.0
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            return {}
    
    def combine_signals(self, signals: Dict[str, float], method: str = 'weighted_average') -> float:
        """Combine multiple signals into a single signal"""
        try:
            if not signals:
                return 0.0
            
            if method == 'weighted_average':
                # Weighted average based on indicator weights
                total_weight = 0.0
                weighted_sum = 0.0
                
                for name, signal in signals.items():
                    if name in self.indicators:
                        weight = self.indicators[name].config.weight
                        weighted_sum += signal * weight
                        total_weight += weight
                
                if total_weight > 0:
                    return weighted_sum / total_weight
                else:
                    return np.mean(list(signals.values()))
            
            elif method == 'majority_vote':
                # Majority vote (positive vs negative signals)
                positive_signals = sum(1 for s in signals.values() if s > 0)
                negative_signals = sum(1 for s in signals.values() if s < 0)
                
                if positive_signals > negative_signals:
                    return 1.0
                elif negative_signals > positive_signals:
                    return -1.0
                else:
                    return 0.0
            
            elif method == 'max':
                # Maximum absolute signal
                return max(signals.values(), key=abs)
            
            elif method == 'min':
                # Minimum absolute signal
                return min(signals.values(), key=abs)
            
            else:
                self.logger.warning(f"Unknown signal combination method: {method}")
                return np.mean(list(signals.values()))
                
        except Exception as e:
            self.logger.error(f"Error combining signals: {e}")
            return 0.0
    
    def generate_combined_signal(self, data: pd.DataFrame) -> float:
        """Generate combined signal from all indicators"""
        try:
            # Generate individual signals
            signals = self.generate_signals(data)
            
            # Combine signals
            combination_method = self.config.get('signal_combination', 'weighted_average')
            combined_signal = self.combine_signals(signals, combination_method)
            
            # Apply overall threshold if specified
            overall_threshold = self.config.get('signal_thresholds', {}).get('entry_threshold')
            if overall_threshold and abs(combined_signal) < overall_threshold:
                combined_signal = 0.0
            
            return combined_signal
            
        except Exception as e:
            self.logger.error(f"Error generating combined signal: {e}")
            return 0.0
