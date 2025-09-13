"""
Consolidated Technical Indicators Engine
=======================================

Unified technical indicators combining:
- All technical indicators from indicators/ directory
- Custom indicators and signal processing
- Performance-optimized calculations
- Extensible indicator framework

This module consolidates indicator functionality from:
- technical_indicators.py
- custom_indicators.py
- signal_processing.py

Author: GitHub Copilot Architecture Simplification
Version: 4.0 (Consolidated)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import json
from collections import defaultdict, deque

# Core infrastructure imports
try:
    from core_structure.infrastructure.config import UnifiedConfigManager as ConfigManager
    from core_structure.infrastructure.message_bus import MessageBus
    from core_structure.infrastructure.metrics_collector import MetricsCollector
except ImportError:
    ConfigManager = None
    MessageBus = None
    MetricsCollector = None

# Technical analysis with graceful fallback
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False

# Scientific computing
try:
    from scipy import signal as scipy_signal
    from scipy.stats import zscore, percentileofscore
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class IndicatorType(Enum):
    """Technical indicator categories"""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    OVERLAP = "overlap"
    CUSTOM = "custom"
    STATISTICAL = "statistical"

class IndicatorStatus(Enum):
    """Indicator calculation status"""
    SUCCESS = "success"
    INSUFFICIENT_DATA = "insufficient_data"
    CALCULATION_ERROR = "calculation_error"
    INVALID_PARAMETERS = "invalid_parameters"

@dataclass
class IndicatorConfig:
    """Configuration for technical indicators with adaptive thresholds support"""
    # Performance settings
    enable_parallel_calculation: bool = True
    max_parallel_indicators: int = 8
    calculation_timeout_ms: int = 100
    cache_indicators: bool = True
    cache_ttl_seconds: int = 300
    
    # Default parameters (now used as fallbacks when adaptive thresholds unavailable)
    default_periods: Dict[str, int] = field(default_factory=lambda: {
        'sma': 20, 'ema': 20, 'rsi': 14, 'macd_fast': 12,
        'macd_slow': 26, 'macd_signal': 9, 'bb_period': 20,
        'atr': 14, 'adx': 14, 'stoch_k': 14, 'stoch_d': 3
    })
    
    # Default thresholds (now used as fallbacks when adaptive thresholds unavailable)
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    stoch_overbought: float = 80.0
    stoch_oversold: float = 20.0
    
    # Volume analysis
    volume_ma_period: int = 20
    volume_spike_threshold: float = 2.0
    
    # Custom indicators
    enable_custom_indicators: bool = True
    custom_lookback_window: int = 50
    
    # Adaptive threshold support
    enable_adaptive_thresholds: bool = True
    threshold_manager: Optional[Any] = None  # Reference to AdaptiveThresholdManager
    
    def get_rsi_thresholds(self, regime_name: Optional[str] = None) -> Dict[str, float]:
        """Get RSI thresholds - adaptive if available, otherwise defaults"""
        if self.enable_adaptive_thresholds and self.threshold_manager:
            return self.threshold_manager.get_adaptive_rsi_thresholds(regime_name)
        return {
            'overbought': self.rsi_overbought,
            'oversold': self.rsi_oversold,
            'momentum_upper': 70.0,
            'momentum_lower': 50.0,
            'bearish_upper': 50.0,
            'bearish_lower': 30.0
        }
    
    def get_stoch_thresholds(self, regime_name: Optional[str] = None) -> Dict[str, float]:
        """Get Stochastic thresholds - adaptive if available, otherwise defaults"""
        if self.enable_adaptive_thresholds and self.threshold_manager:
            return {
                'overbought': self.threshold_manager.get_threshold_value('stoch_overbought', regime_name),
                'oversold': self.threshold_manager.get_threshold_value('stoch_oversold', regime_name)
            }
        return {
            'overbought': self.stoch_overbought,
            'oversold': self.stoch_oversold
        }
    
    def get_technical_params(self, regime_name: Optional[str] = None) -> Dict[str, Union[int, float]]:
        """Get technical indicator parameters - adaptive if available, otherwise defaults"""
        if self.enable_adaptive_thresholds and self.threshold_manager:
            return self.threshold_manager.get_adaptive_technical_indicator_params(regime_name)
        return {
            'rsi_period': self.default_periods['rsi'],
            'bb_period': self.default_periods['bb_period'],
            'bb_std_multiplier': 2.0,
            'macd_fast': self.default_periods['macd_fast'],
            'macd_slow': self.default_periods['macd_slow'],
            'macd_signal': self.default_periods['macd_signal']
        }

@dataclass
class IndicatorResult:
    """Technical indicator result"""
    name: str
    indicator_type: IndicatorType
    values: Union[pd.Series, Dict[str, pd.Series]]
    current_value: Optional[float]
    signal: Optional[str]  # buy, sell, neutral
    signal_strength: float  # -1 to 1
    status: IndicatorStatus
    calculation_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        values_dict = {}
        if isinstance(self.values, pd.Series):
            values_dict = {'values': self.values.to_dict()}
        elif isinstance(self.values, dict):
            values_dict = {k: v.to_dict() if isinstance(v, pd.Series) else v 
                          for k, v in self.values.items()}
        
        return {
            'name': self.name,
            'indicator_type': self.indicator_type.value,
            'values': values_dict,
            'current_value': self.current_value,
            'signal': self.signal,
            'signal_strength': self.signal_strength,
            'status': self.status.value,
            'calculation_time': self.calculation_time,
            'metadata': self.metadata
        }

class TechnicalIndicatorsEngine:
    """
    Consolidated Technical Indicators Engine
    
    Unified technical indicator calculations with optimized
    performance and extensible indicator framework.
    """
    
    def __init__(self, config: Optional[IndicatorConfig] = None):
        """Initialize technical indicators engine"""
        self.config = config or IndicatorConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # State management
        self._indicator_cache = {}
        self._calculation_times = {}
        self._lock = threading.Lock()
        
        # Performance tracking
        self.performance_metrics = {
            'indicators_calculated': 0,
            'successful_calculations': 0,
            'avg_calculation_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'last_update': datetime.now()
        }
        
        self.logger.info(f"TechnicalIndicatorsEngine initialized with caching: {self.config.cache_indicators}")
    
    def calculate_indicator(self, 
                          name: str,
                          market_data: pd.DataFrame,
                          **kwargs) -> Optional[IndicatorResult]:
        """
        Calculate single technical indicator
        
        Args:
            name: Indicator name (e.g., 'sma', 'rsi', 'macd')
            market_data: OHLCV data
            **kwargs: Indicator-specific parameters
            
        Returns:
            Indicator result or None if calculation fails
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if self.config.cache_indicators:
                cache_key = self._get_cache_key(name, market_data, kwargs)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    self.performance_metrics['cache_hits'] += 1
                    return cached_result
                else:
                    self.performance_metrics['cache_misses'] += 1
            
            # Validate input data
            if not self._validate_market_data(market_data):
                return IndicatorResult(
                    name=name,
                    indicator_type=IndicatorType.TREND,
                    values=pd.Series(),
                    current_value=None,
                    signal=None,
                    signal_strength=0.0,
                    status=IndicatorStatus.INSUFFICIENT_DATA,
                    calculation_time=time.time() - start_time
                )
            
            # Calculate indicator
            result = self._calculate_single_indicator(name, market_data, **kwargs)
            
            if result:
                result.calculation_time = time.time() - start_time
                
                # Cache result
                if self.config.cache_indicators:
                    self._cache_result(cache_key, result)
                
                # Update metrics
                self._update_calculation_metrics(result)
                
                self.logger.debug(f"Calculated {name}: current_value={result.current_value}, "
                                f"signal={result.signal}, time={result.calculation_time:.3f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating indicator {name}: {e}")
            return None
    
    def calculate_indicators_batch(self, 
                                 indicators: List[str],
                                 market_data: pd.DataFrame,
                                 parameters: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, IndicatorResult]:
        """
        Calculate multiple indicators in batch
        
        Args:
            indicators: List of indicator names
            market_data: OHLCV data
            parameters: Optional parameters for each indicator
            
        Returns:
            Dictionary of indicator results
        """
        try:
            parameters = parameters or {}
            results = {}
            
            if self.config.enable_parallel_calculation and len(indicators) > 1:
                # Parallel calculation
                with ThreadPoolExecutor(max_workers=self.config.max_parallel_indicators) as executor:
                    futures = {}
                    
                    for indicator in indicators:
                        params = parameters.get(indicator, {})
                        future = executor.submit(self.calculate_indicator, indicator, market_data, **params)
                        futures[future] = indicator
                    
                    for future in futures:
                        indicator = futures[future]
                        try:
                            result = future.result(timeout=self.config.calculation_timeout_ms / 1000.0)
                            if result:
                                results[indicator] = result
                        except Exception as e:
                            self.logger.warning(f"Error calculating {indicator} in batch: {e}")
            else:
                # Sequential calculation
                for indicator in indicators:
                    params = parameters.get(indicator, {})
                    result = self.calculate_indicator(indicator, market_data, **params)
                    if result:
                        results[indicator] = result
            
            self.logger.info(f"Calculated {len(results)}/{len(indicators)} indicators in batch")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch indicator calculation: {e}")
            return {}
    
    def _validate_market_data(self, market_data: pd.DataFrame) -> bool:
        """Validate market data for indicator calculation"""
        if market_data.empty:
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in market_data.columns for col in required_columns):
            self.logger.warning("Missing required OHLCV columns")
            return False
        
        if len(market_data) < 2:
            return False
        
        return True
    
    def _calculate_single_indicator(self, 
                                  name: str,
                                  market_data: pd.DataFrame,
                                  **kwargs) -> Optional[IndicatorResult]:
        """Calculate single indicator with fallback methods"""
        try:
            # Get indicator type
            indicator_type = self._get_indicator_type(name)
            
            # Try different calculation methods
            if TALIB_AVAILABLE:
                result = self._calculate_with_talib(name, market_data, **kwargs)
                if result:
                    result.indicator_type = indicator_type
                    return result
            
            if TA_AVAILABLE:
                result = self._calculate_with_ta(name, market_data, **kwargs)
                if result:
                    result.indicator_type = indicator_type
                    return result
            
            # Manual implementation fallback
            result = self._calculate_manual(name, market_data, **kwargs)
            if result:
                result.indicator_type = indicator_type
                return result
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in single indicator calculation for {name}: {e}")
            return None
    
    def _calculate_with_talib(self, 
                            name: str,
                            market_data: pd.DataFrame,
                            **kwargs) -> Optional[IndicatorResult]:
        """Calculate indicator using TA-Lib"""
        try:
            high = market_data['high'].values
            low = market_data['low'].values
            close = market_data['close'].values
            volume = market_data['volume'].values
            
            if name.lower() == 'sma':
                period = kwargs.get('period', self.config.default_periods['sma'])
                values = talib.SMA(close, timeperiod=period)
                
            elif name.lower() == 'ema':
                period = kwargs.get('period', self.config.default_periods['ema'])
                values = talib.EMA(close, timeperiod=period)
                
            elif name.lower() == 'rsi':
                period = kwargs.get('period', self.config.default_periods['rsi'])
                values = talib.RSI(close, timeperiod=period)
                
            elif name.lower() == 'macd':
                fast = kwargs.get('fast_period', self.config.default_periods['macd_fast'])
                slow = kwargs.get('slow_period', self.config.default_periods['macd_slow'])
                signal_period = kwargs.get('signal_period', self.config.default_periods['macd_signal'])
                
                macd_line, signal_line, histogram = talib.MACD(close, fastperiod=fast, slowperiod=slow, signalperiod=signal_period)
                values = {
                    'macd': pd.Series(macd_line, index=market_data.index),
                    'signal': pd.Series(signal_line, index=market_data.index),
                    'histogram': pd.Series(histogram, index=market_data.index)
                }
                
            elif name.lower() == 'bbands':
                period = kwargs.get('period', self.config.default_periods['bb_period'])
                std_dev = kwargs.get('std_dev', 2.0)
                
                upper, middle, lower = talib.BBANDS(close, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
                values = {
                    'upper': pd.Series(upper, index=market_data.index),
                    'middle': pd.Series(middle, index=market_data.index),
                    'lower': pd.Series(lower, index=market_data.index)
                }
                
            elif name.lower() == 'atr':
                period = kwargs.get('period', self.config.default_periods['atr'])
                values = talib.ATR(high, low, close, timeperiod=period)
                
            elif name.lower() == 'adx':
                period = kwargs.get('period', self.config.default_periods['adx'])
                values = talib.ADX(high, low, close, timeperiod=period)
                
            elif name.lower() == 'stoch':
                k_period = kwargs.get('k_period', self.config.default_periods['stoch_k'])
                d_period = kwargs.get('d_period', self.config.default_periods['stoch_d'])
                
                slowk, slowd = talib.STOCH(high, low, close, fastk_period=k_period, slowk_period=d_period, slowd_period=d_period)
                values = {
                    'slowk': pd.Series(slowk, index=market_data.index),
                    'slowd': pd.Series(slowd, index=market_data.index)
                }
                
            else:
                return None
            
            # Create result
            if isinstance(values, dict):
                current_value = None
                signal, signal_strength = self._generate_signal_multi(name, values)
            else:
                values_series = pd.Series(values, index=market_data.index)
                current_value = float(values_series.iloc[-1]) if not pd.isna(values_series.iloc[-1]) else None
                signal, signal_strength = self._generate_signal_single(name, values_series, market_data)
                values = values_series
            
            return IndicatorResult(
                name=name,
                indicator_type=self._get_indicator_type(name),
                values=values,
                current_value=current_value,
                signal=signal,
                signal_strength=signal_strength,
                status=IndicatorStatus.SUCCESS,
                calculation_time=0.0,  # Will be set by caller
                metadata={'method': 'talib', 'parameters': kwargs}
            )
            
        except Exception as e:
            self.logger.debug(f"TA-Lib calculation failed for {name}: {e}")
            return None
    
    def _calculate_with_ta(self, 
                         name: str,
                         market_data: pd.DataFrame,
                         **kwargs) -> Optional[IndicatorResult]:
        """Calculate indicator using ta library"""
        try:
            if name.lower() == 'sma':
                period = kwargs.get('period', self.config.default_periods['sma'])
                values = ta.trend.sma_indicator(market_data['close'], window=period)
                
            elif name.lower() == 'ema':
                period = kwargs.get('period', self.config.default_periods['ema'])
                values = ta.trend.ema_indicator(market_data['close'], window=period)
                
            elif name.lower() == 'rsi':
                period = kwargs.get('period', self.config.default_periods['rsi'])
                values = ta.momentum.rsi(market_data['close'], window=period)
                
            elif name.lower() == 'macd':
                fast = kwargs.get('fast_period', self.config.default_periods['macd_fast'])
                slow = kwargs.get('slow_period', self.config.default_periods['macd_slow'])
                signal_period = kwargs.get('signal_period', self.config.default_periods['macd_signal'])
                
                values = {
                    'macd': ta.trend.macd(market_data['close'], window_fast=fast, window_slow=slow),
                    'signal': ta.trend.macd_signal(market_data['close'], window_fast=fast, window_slow=slow, window_sign=signal_period),
                    'histogram': ta.trend.macd_diff(market_data['close'], window_fast=fast, window_slow=slow, window_sign=signal_period)
                }
                
            elif name.lower() == 'bbands':
                period = kwargs.get('period', self.config.default_periods['bb_period'])
                std_dev = kwargs.get('std_dev', 2.0)
                
                values = {
                    'upper': ta.volatility.bollinger_hband(market_data['close'], window=period, window_dev=std_dev),
                    'middle': ta.volatility.bollinger_mavg(market_data['close'], window=period),
                    'lower': ta.volatility.bollinger_lband(market_data['close'], window=period, window_dev=std_dev)
                }
                
            elif name.lower() == 'atr':
                period = kwargs.get('period', self.config.default_periods['atr'])
                values = ta.volatility.average_true_range(market_data['high'], market_data['low'], market_data['close'], window=period)
                
            else:
                return None
            
            # Create result (similar to talib method)
            if isinstance(values, dict):
                current_value = None
                signal, signal_strength = self._generate_signal_multi(name, values)
            else:
                current_value = float(values.iloc[-1]) if not pd.isna(values.iloc[-1]) else None
                signal, signal_strength = self._generate_signal_single(name, values, market_data)
            
            return IndicatorResult(
                name=name,
                indicator_type=self._get_indicator_type(name),
                values=values,
                current_value=current_value,
                signal=signal,
                signal_strength=signal_strength,
                status=IndicatorStatus.SUCCESS,
                calculation_time=0.0,
                metadata={'method': 'ta', 'parameters': kwargs}
            )
            
        except Exception as e:
            self.logger.debug(f"ta library calculation failed for {name}: {e}")
            return None
    
    def _calculate_manual(self, 
                        name: str,
                        market_data: pd.DataFrame,
                        **kwargs) -> Optional[IndicatorResult]:
        """Manual indicator calculation as fallback"""
        try:
            close = market_data['close']
            
            if name.lower() == 'sma':
                period = kwargs.get('period', self.config.default_periods['sma'])
                values = close.rolling(window=period).mean()
                
            elif name.lower() == 'ema':
                period = kwargs.get('period', self.config.default_periods['ema'])
                values = close.ewm(span=period).mean()
                
            elif name.lower() == 'rsi':
                period = kwargs.get('period', self.config.default_periods['rsi'])
                values = self._manual_rsi(close, period)
                
            elif name.lower() == 'atr':
                period = kwargs.get('period', self.config.default_periods['atr'])
                values = self._manual_atr(market_data, period)
                
            else:
                return None
            
            current_value = float(values.iloc[-1]) if not pd.isna(values.iloc[-1]) else None
            signal, signal_strength = self._generate_signal_single(name, values, market_data)
            
            return IndicatorResult(
                name=name,
                indicator_type=self._get_indicator_type(name),
                values=values,
                current_value=current_value,
                signal=signal,
                signal_strength=signal_strength,
                status=IndicatorStatus.SUCCESS,
                calculation_time=0.0,
                metadata={'method': 'manual', 'parameters': kwargs}
            )
            
        except Exception as e:
            self.logger.debug(f"Manual calculation failed for {name}: {e}")
            return None
    
    def _manual_rsi(self, close: pd.Series, period: int) -> pd.Series:
        """Manual RSI calculation"""
        try:
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"Error in manual RSI calculation: {e}")
            return pd.Series([np.nan] * len(close), index=close.index)
    
    def _manual_atr(self, market_data: pd.DataFrame, period: int) -> pd.Series:
        """Manual ATR calculation"""
        try:
            high = market_data['high']
            low = market_data['low']
            close = market_data['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean()
            
            return atr
            
        except Exception as e:
            self.logger.error(f"Error in manual ATR calculation: {e}")
            return pd.Series([np.nan] * len(market_data), index=market_data.index)
    
    def _generate_signal_single(self, 
                              name: str,
                              values: pd.Series,
                              market_data: pd.DataFrame) -> Tuple[Optional[str], float]:
        """Generate trading signal for single-value indicators"""
        try:
            if values.empty or pd.isna(values.iloc[-1]):
                return None, 0.0
            
            current_value = values.iloc[-1]
            close = market_data['close'].iloc[-1]
            
            if name.lower() == 'rsi':
                if current_value > self.config.rsi_overbought:
                    return 'sell', min(1.0, (current_value - self.config.rsi_overbought) / 20.0)
                elif current_value < self.config.rsi_oversold:
                    return 'buy', min(1.0, (self.config.rsi_oversold - current_value) / 20.0)
                else:
                    return 'neutral', 0.0
            
            elif name.lower() in ['sma', 'ema']:
                # Price vs moving average
                if close > current_value:
                    strength = min(1.0, (close - current_value) / current_value * 20)
                    return 'buy', strength
                elif close < current_value:
                    strength = min(1.0, (current_value - close) / current_value * 20)
                    return 'sell', strength
                else:
                    return 'neutral', 0.0
            
            elif name.lower() == 'atr':
                # ATR doesn't generate direct signals, just neutral
                return 'neutral', 0.0
            
            else:
                return 'neutral', 0.0
                
        except Exception as e:
            self.logger.warning(f"Error generating signal for {name}: {e}")
            return None, 0.0
    
    def _generate_signal_multi(self, 
                             name: str,
                             values: Dict[str, pd.Series]) -> Tuple[Optional[str], float]:
        """Generate trading signal for multi-value indicators"""
        try:
            if name.lower() == 'macd':
                macd = values.get('macd')
                signal_line = values.get('signal')
                histogram = values.get('histogram')
                
                if macd is not None and signal_line is not None:
                    macd_current = macd.iloc[-1]
                    signal_current = signal_line.iloc[-1]
                    
                    if pd.isna(macd_current) or pd.isna(signal_current):
                        return None, 0.0
                    
                    if macd_current > signal_current:
                        strength = min(1.0, abs(macd_current - signal_current) * 100)
                        return 'buy', strength
                    elif macd_current < signal_current:
                        strength = min(1.0, abs(signal_current - macd_current) * 100)
                        return 'sell', strength
                    else:
                        return 'neutral', 0.0
            
            elif name.lower() == 'bbands':
                upper = values.get('upper')
                middle = values.get('middle')
                lower = values.get('lower')
                
                if all(v is not None for v in [upper, middle, lower]):
                    # This would need current price to generate proper signal
                    return 'neutral', 0.0
            
            elif name.lower() == 'stoch':
                slowk = values.get('slowk')
                slowd = values.get('slowd')
                
                if slowk is not None:
                    k_current = slowk.iloc[-1]
                    if not pd.isna(k_current):
                        if k_current > self.config.stoch_overbought:
                            return 'sell', min(1.0, (k_current - self.config.stoch_overbought) / 20.0)
                        elif k_current < self.config.stoch_oversold:
                            return 'buy', min(1.0, (self.config.stoch_oversold - k_current) / 20.0)
            
            return 'neutral', 0.0
            
        except Exception as e:
            self.logger.warning(f"Error generating multi-signal for {name}: {e}")
            return None, 0.0
    
    def _get_indicator_type(self, name: str) -> IndicatorType:
        """Get indicator type based on name"""
        trend_indicators = ['sma', 'ema', 'macd', 'adx']
        momentum_indicators = ['rsi', 'stoch', 'cci', 'williams_r']
        volatility_indicators = ['atr', 'bbands', 'keltner']
        volume_indicators = ['obv', 'vwap', 'mfi']
        
        name_lower = name.lower()
        
        if name_lower in trend_indicators:
            return IndicatorType.TREND
        elif name_lower in momentum_indicators:
            return IndicatorType.MOMENTUM
        elif name_lower in volatility_indicators:
            return IndicatorType.VOLATILITY
        elif name_lower in volume_indicators:
            return IndicatorType.VOLUME
        else:
            return IndicatorType.CUSTOM
    
    def _get_cache_key(self, 
                      name: str,
                      market_data: pd.DataFrame,
                      kwargs: Dict[str, Any]) -> str:
        """Generate cache key for indicator result"""
        try:
            # Use last timestamp and hash of parameters
            last_timestamp = market_data.index[-1].isoformat()
            data_hash = str(hash(tuple(market_data.tail(1).values.flatten())))
            params_str = json.dumps(kwargs, sort_keys=True, default=str)
            
            return f"{name}_{last_timestamp}_{data_hash}_{hash(params_str)}"
            
        except Exception as e:
            self.logger.warning(f"Error generating cache key: {e}")
            return f"{name}_{time.time()}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[IndicatorResult]:
        """Get cached indicator result"""
        try:
            with self._lock:
                if cache_key in self._indicator_cache:
                    cached_time, result = self._indicator_cache[cache_key]
                    if datetime.now() - cached_time < timedelta(seconds=self.config.cache_ttl_seconds):
                        return result
                    else:
                        # Remove expired cache entry
                        del self._indicator_cache[cache_key]
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error accessing cache: {e}")
            return None
    
    def _cache_result(self, cache_key: str, result: IndicatorResult):
        """Cache indicator result"""
        try:
            with self._lock:
                self._indicator_cache[cache_key] = (datetime.now(), result)
                
                # Limit cache size
                if len(self._indicator_cache) > 1000:
                    # Remove oldest entries
                    sorted_cache = sorted(self._indicator_cache.items(), 
                                        key=lambda x: x[1][0])
                    for key, _ in sorted_cache[:100]:  # Remove oldest 100
                        del self._indicator_cache[key]
                        
        except Exception as e:
            self.logger.warning(f"Error caching result: {e}")
    
    def _update_calculation_metrics(self, result: IndicatorResult):
        """Update calculation performance metrics"""
        self.performance_metrics['indicators_calculated'] += 1
        
        if result.status == IndicatorStatus.SUCCESS:
            self.performance_metrics['successful_calculations'] += 1
            
            # Update rolling average of calculation time
            total_successful = self.performance_metrics['successful_calculations']
            old_avg_time = self.performance_metrics['avg_calculation_time']
            self.performance_metrics['avg_calculation_time'] = (
                (old_avg_time * (total_successful - 1) + result.calculation_time) / total_successful
            )
        
        self.performance_metrics['last_update'] = datetime.now()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get calculation performance metrics"""
        return self.performance_metrics.copy()
    
    def clear_cache(self):
        """Clear indicator cache"""
        with self._lock:
            self._indicator_cache.clear()
        
        self.logger.info("Indicator cache cleared")

# Backward compatibility aliases
TechnicalIndicators = TechnicalIndicatorsEngine
CustomIndicators = TechnicalIndicatorsEngine
SignalProcessor = TechnicalIndicatorsEngine

__all__ = [
    'TechnicalIndicatorsEngine',
    'TechnicalIndicators',  # Backward compatibility
    'CustomIndicators',  # Backward compatibility
    'SignalProcessor',  # Backward compatibility
    'IndicatorResult',
    'IndicatorType',
    'IndicatorStatus',
    'IndicatorConfig'
]
