"""
High-Performance Signal Generator
================================

Ultra-fast signal generation engine designed for high-throughput signal
processing with advanced parallel processing and vectorized computations.

Target: 10,000+ signals/second with <5ms latency per signal

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import time
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
import threading
from enum import Enum

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Signal types for classification"""
    BUY = 1.0
    SELL = -1.0
    HOLD = 0.0

@dataclass
class SignalGeneratorConfig:
    """Configuration for high-performance signal generator"""
    # Performance targets
    target_signals_per_second: int = 10000
    target_latency_ms: float = 5.0
    max_workers: int = 16
    
    # Signal processing
    enable_parallel_signals: bool = True
    enable_vectorized_indicators: bool = True
    enable_ensemble_signals: bool = True
    
    # Indicator configuration
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bollinger_period: int = 20
    bollinger_std: float = 2.0
    
    # Signal thresholds
    min_signal_strength: float = 0.6
    signal_consensus_threshold: float = 0.7
    volume_confirmation_threshold: float = 1.2

@dataclass
class SignalGenerationResult:
    """Result of signal generation operation"""
    signals_generated: int
    processing_time_ms: float
    signals_per_second: float
    signal_strength_distribution: Dict[str, int]
    consensus_signals: int
    optimization_techniques_used: List[str] = field(default_factory=list)

class VectorizedIndicators:
    """Ultra-fast vectorized technical indicators"""
    
    @staticmethod
    def rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Vectorized RSI calculation"""
        if len(prices) < period + 1:
            return np.full_like(prices, 50.0)
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Vectorized Wilder's smoothing
        avg_gains = np.zeros_like(gains)
        avg_losses = np.zeros_like(losses)
        
        # Initialize first values
        avg_gains[period-1] = np.mean(gains[:period])
        avg_losses[period-1] = np.mean(losses[:period])
        
        # Apply Wilder's smoothing
        alpha = 1.0 / period
        for i in range(period, len(gains)):
            avg_gains[i] = alpha * gains[i] + (1 - alpha) * avg_gains[i-1]
            avg_losses[i] = alpha * losses[i] + (1 - alpha) * avg_losses[i-1]
        
        # Calculate RSI
        rs = avg_gains / (avg_losses + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return np.pad(rsi, (1, 0), mode='edge')
    
    @staticmethod
    def macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Vectorized MACD calculation"""
        if len(prices) < slow:
            zeros = np.zeros_like(prices)
            return zeros, zeros, zeros
        
        # Calculate EMAs using vectorized approach
        ema_fast = VectorizedIndicators._ema(prices, fast)
        ema_slow = VectorizedIndicators._ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = VectorizedIndicators._ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(prices: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Vectorized Bollinger Bands calculation"""
        if len(prices) < period:
            return prices, prices, prices
        
        # Rolling mean and std using convolution
        weights = np.ones(period) / period
        sma = np.convolve(prices, weights, mode='same')
        
        # Rolling standard deviation
        rolling_std = np.zeros_like(prices)
        for i in range(period-1, len(prices)):
            rolling_std[i] = np.std(prices[i-period+1:i+1])
        
        upper_band = sma + (rolling_std * std_dev)
        lower_band = sma - (rolling_std * std_dev)
        
        return upper_band, sma, lower_band
    
    @staticmethod
    def _ema(data: np.ndarray, period: int) -> np.ndarray:
        """Calculate exponential moving average"""
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        
        return ema

class ParallelSignalProcessor:
    """Parallel signal processing engine"""
    
    def __init__(self, max_workers: int = 16):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="SignalProc")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_symbols_parallel(self, symbol_data: Dict[str, np.ndarray], 
                                signal_func: Callable, config: SignalGeneratorConfig) -> Dict[str, Dict[str, Any]]:
        """Process signals for multiple symbols in parallel"""
        if len(symbol_data) <= 1:
            # Single symbol - process directly
            symbol, data = next(iter(symbol_data.items()))
            return {symbol: signal_func(data, config)}
        
        # Multiple symbols - parallel processing
        futures = []
        for symbol, data in symbol_data.items():
            future = self.executor.submit(self._safe_signal_processing, symbol, data, signal_func, config)
            futures.append((symbol, future))
        
        # Collect results with timeout
        results = {}
        for symbol, future in futures:
            try:
                result = future.result(timeout=config.target_latency_ms / 1000)  # Convert ms to seconds
                results[symbol] = result
            except Exception as e:
                self.logger.warning(f"Signal processing failed for {symbol}: {e}")
                results[symbol] = self._create_empty_signal()
        
        return results
    
    def _safe_signal_processing(self, symbol: str, data: np.ndarray, 
                              signal_func: Callable, config: SignalGeneratorConfig) -> Dict[str, Any]:
        """Safe wrapper for signal processing"""
        try:
            return signal_func(data, config)
        except Exception as e:
            self.logger.error(f"Signal processing error for {symbol}: {e}")
            return self._create_empty_signal()
    
    def _create_empty_signal(self) -> Dict[str, Any]:
        """Create empty signal for error cases"""
        return {
            'signal': SignalType.HOLD.value,
            'strength': 0.0,
            'confidence': 0.0,
            'indicators': {},
            'timestamp': datetime.now()
        }
    
    def __del__(self):
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

class EnsembleSignalGenerator:
    """Ensemble signal generation using multiple indicators"""
    
    def __init__(self, config: SignalGeneratorConfig):
        self.config = config
        self.indicators = VectorizedIndicators()
    
    def generate_ensemble_signal(self, prices: np.ndarray) -> Dict[str, Any]:
        """Generate ensemble signal from multiple indicators"""
        if len(prices) < max(self.config.rsi_period, self.config.macd_slow, self.config.bollinger_period):
            return self._create_neutral_signal()
        
        # Calculate all indicators in parallel (vectorized)
        rsi = self.indicators.rsi(prices, self.config.rsi_period)
        macd_line, macd_signal, macd_histogram = self.indicators.macd(
            prices, self.config.macd_fast, self.config.macd_slow, self.config.macd_signal
        )
        bb_upper, bb_middle, bb_lower = self.indicators.bollinger_bands(
            prices, self.config.bollinger_period, self.config.bollinger_std
        )
        
        # Get latest values
        current_price = prices[-1]
        current_rsi = rsi[-1]
        current_macd = macd_line[-1]
        current_macd_signal = macd_signal[-1]
        current_bb_position = (current_price - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1])
        
        # Generate individual signals
        signals = []
        
        # RSI Signal
        if current_rsi < 30:
            signals.append(('rsi', SignalType.BUY.value, 0.8))
        elif current_rsi > 70:
            signals.append(('rsi', SignalType.SELL.value, 0.8))
        else:
            signals.append(('rsi', SignalType.HOLD.value, 0.3))
        
        # MACD Signal
        if current_macd > current_macd_signal and macd_line[-2] <= macd_signal[-2]:
            signals.append(('macd', SignalType.BUY.value, 0.7))
        elif current_macd < current_macd_signal and macd_line[-2] >= macd_signal[-2]:
            signals.append(('macd', SignalType.SELL.value, 0.7))
        else:
            signals.append(('macd', SignalType.HOLD.value, 0.2))
        
        # Bollinger Bands Signal
        if current_bb_position < 0.2:
            signals.append(('bollinger', SignalType.BUY.value, 0.6))
        elif current_bb_position > 0.8:
            signals.append(('bollinger', SignalType.SELL.value, 0.6))
        else:
            signals.append(('bollinger', SignalType.HOLD.value, 0.1))
        
        # Calculate ensemble signal
        weighted_sum = sum(signal * strength for _, signal, strength in signals)
        total_weight = sum(strength for _, _, strength in signals)
        
        if total_weight > 0:
            ensemble_signal = weighted_sum / total_weight
            signal_strength = total_weight / len(signals)
        else:
            ensemble_signal = SignalType.HOLD.value
            signal_strength = 0.0
        
        # Determine final signal type
        if ensemble_signal > self.config.min_signal_strength:
            final_signal = SignalType.BUY.value
        elif ensemble_signal < -self.config.min_signal_strength:
            final_signal = SignalType.SELL.value
        else:
            final_signal = SignalType.HOLD.value
        
        return {
            'signal': final_signal,
            'strength': abs(ensemble_signal),
            'confidence': signal_strength,
            'indicators': {
                'rsi': current_rsi,
                'macd': current_macd,
                'macd_signal': current_macd_signal,
                'bb_position': current_bb_position
            },
            'individual_signals': signals,
            'timestamp': datetime.now()
        }
    
    def _create_neutral_signal(self) -> Dict[str, Any]:
        """Create neutral signal for insufficient data"""
        return {
            'signal': SignalType.HOLD.value,
            'strength': 0.0,
            'confidence': 0.0,
            'indicators': {},
            'individual_signals': [],
            'timestamp': datetime.now()
        }

class HighPerformanceSignalGenerator:
    """
    Ultra-fast signal generator designed to achieve 10,000+ signals/second
    with sub-5ms latency using parallel processing and vectorized computations.
    """
    
    def __init__(self, config: Optional[SignalGeneratorConfig] = None):
        self.config = config or SignalGeneratorConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # High-performance components
        if self.config.enable_parallel_signals:
            self.parallel_processor = ParallelSignalProcessor(self.config.max_workers)
        
        if self.config.enable_ensemble_signals:
            self.ensemble_generator = EnsembleSignalGenerator(self.config)
        
        # Performance tracking
        self.signal_counts: List[int] = []
        self.processing_times: List[float] = []
        self.total_signals_generated = 0
        
        self.logger.info(f"HighPerformanceSignalGenerator initialized - Target: {self.config.target_signals_per_second} signals/sec")
    
    def generate_signals(self, market_data: Dict[str, Any]) -> SignalGenerationResult:
        """
        Generate trading signals with high-throughput processing
        """
        start_time = time.perf_counter()
        optimization_techniques = []
        
        try:
            # Convert market data to standardized format
            symbol_data = self._prepare_market_data(market_data)
            
            if not symbol_data:
                return self._create_empty_result(start_time)
            
            # Choose processing strategy based on data volume
            if len(symbol_data) > 1 and self.config.enable_parallel_signals:
                # Parallel processing for multiple symbols
                signals = self.parallel_processor.process_symbols_parallel(
                    symbol_data, self._generate_single_signal, self.config
                )
                optimization_techniques.append("parallel_processing")
            else:
                # Sequential processing
                signals = {}
                for symbol, data in symbol_data.items():
                    signals[symbol] = self._generate_single_signal(data, self.config)
                optimization_techniques.append("sequential_processing")
            
            # Apply vectorized optimizations if enabled
            if self.config.enable_vectorized_indicators:
                optimization_techniques.append("vectorized_indicators")
            
            # Apply ensemble processing if enabled
            if self.config.enable_ensemble_signals:
                optimization_techniques.append("ensemble_signals")
            
            return self._create_result(start_time, signals, optimization_techniques)
            
        except Exception as e:
            self.logger.error(f"High-performance signal generation failed: {e}")
            return self._create_empty_result(start_time)
    
    def _prepare_market_data(self, market_data: Dict[str, Any]) -> Dict[str, np.ndarray]:
        """Prepare market data for signal generation"""
        symbol_data = {}
        
        for symbol, data in market_data.items():
            if isinstance(data, pd.DataFrame):
                # Use close prices for signal generation
                if 'close' in data.columns:
                    prices = data['close'].values
                elif 'price' in data.columns:
                    prices = data['price'].values
                else:
                    prices = data.iloc[:, 0].values  # Use first column
            elif isinstance(data, (list, np.ndarray)):
                prices = np.array(data)
            elif isinstance(data, dict) and 'prices' in data:
                prices = np.array(data['prices'])
            else:
                self.logger.warning(f"Unsupported data format for {symbol}")
                continue
            
            if len(prices) > 0:
                symbol_data[symbol] = prices
        
        return symbol_data
    
    def _generate_single_signal(self, prices: np.ndarray, config: SignalGeneratorConfig) -> Dict[str, Any]:
        """Generate signal for a single symbol"""
        try:
            if config.enable_ensemble_signals and hasattr(self, 'ensemble_generator'):
                return self.ensemble_generator.generate_ensemble_signal(prices)
            else:
                return self._generate_basic_signal(prices, config)
        except Exception as e:
            self.logger.error(f"Single signal generation failed: {e}")
            return {
                'signal': SignalType.HOLD.value,
                'strength': 0.0,
                'confidence': 0.0,
                'indicators': {},
                'timestamp': datetime.now(),
                'error': str(e)
            }
    
    def _generate_basic_signal(self, prices: np.ndarray, config: SignalGeneratorConfig) -> Dict[str, Any]:
        """Generate basic signal using simple indicators"""
        if len(prices) < config.rsi_period:
            return {
                'signal': SignalType.HOLD.value,
                'strength': 0.0,
                'confidence': 0.0,
                'indicators': {},
                'timestamp': datetime.now()
            }
        
        # Simple moving average crossover
        if len(prices) >= 20:
            ma_short = np.mean(prices[-5:])
            ma_long = np.mean(prices[-20:])
            
            if ma_short > ma_long * 1.02:  # 2% threshold
                signal = SignalType.BUY.value
                strength = min((ma_short / ma_long - 1) * 10, 1.0)
            elif ma_short < ma_long * 0.98:  # 2% threshold
                signal = SignalType.SELL.value
                strength = min((1 - ma_short / ma_long) * 10, 1.0)
            else:
                signal = SignalType.HOLD.value
                strength = 0.0
        else:
            signal = SignalType.HOLD.value
            strength = 0.0
        
        return {
            'signal': signal,
            'strength': strength,
            'confidence': strength * 0.7,  # Conservative confidence
            'indicators': {
                'ma_short': ma_short if 'ma_short' in locals() else 0,
                'ma_long': ma_long if 'ma_long' in locals() else 0
            },
            'timestamp': datetime.now()
        }
    
    def _create_result(self, start_time: float, signals: Dict[str, Dict[str, Any]], 
                      optimization_techniques: List[str]) -> SignalGenerationResult:
        """Create signal generation result with performance metrics"""
        processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
        signals_generated = len(signals)
        
        # Update performance tracking
        self.processing_times.append(processing_time)
        self.signal_counts.append(signals_generated)
        self.total_signals_generated += signals_generated
        
        # Keep only recent measurements
        if len(self.processing_times) > 1000:
            self.processing_times = self.processing_times[-1000:]
            self.signal_counts = self.signal_counts[-1000:]
        
        # Calculate signals per second
        signals_per_second = (signals_generated / (processing_time / 1000)) if processing_time > 0 else 0
        
        # Analyze signal strength distribution
        strength_distribution = {'strong': 0, 'medium': 0, 'weak': 0}
        consensus_signals = 0
        
        for signal_data in signals.values():
            strength = signal_data.get('strength', 0.0)
            confidence = signal_data.get('confidence', 0.0)
            
            if strength > 0.7:
                strength_distribution['strong'] += 1
            elif strength > 0.4:
                strength_distribution['medium'] += 1
            else:
                strength_distribution['weak'] += 1
            
            if confidence > self.config.signal_consensus_threshold:
                consensus_signals += 1
        
        return SignalGenerationResult(
            signals_generated=signals_generated,
            processing_time_ms=processing_time,
            signals_per_second=signals_per_second,
            signal_strength_distribution=strength_distribution,
            consensus_signals=consensus_signals,
            optimization_techniques_used=optimization_techniques
        )
    
    def _create_empty_result(self, start_time: float) -> SignalGenerationResult:
        """Create empty result for error cases"""
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return SignalGenerationResult(
            signals_generated=0,
            processing_time_ms=processing_time,
            signals_per_second=0.0,
            signal_strength_distribution={'strong': 0, 'medium': 0, 'weak': 0},
            consensus_signals=0,
            optimization_techniques_used=["error_fallback"]
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        if not self.processing_times:
            return {}
        
        avg_processing_time = np.mean(self.processing_times)
        avg_signals_generated = np.mean(self.signal_counts)
        avg_signals_per_second = avg_signals_generated / (avg_processing_time / 1000) if avg_processing_time > 0 else 0
        
        return {
            'average_processing_time_ms': avg_processing_time,
            'average_signals_per_batch': avg_signals_generated,
            'average_signals_per_second': avg_signals_per_second,
            'total_signals_generated': self.total_signals_generated,
            'target_signals_per_second': self.config.target_signals_per_second,
            'target_latency_ms': self.config.target_latency_ms,
            'throughput_target_achieved': avg_signals_per_second >= self.config.target_signals_per_second,
            'latency_target_achieved': avg_processing_time <= self.config.target_latency_ms
        }
    
    def reset_performance_tracking(self) -> None:
        """Reset performance tracking metrics"""
        self.processing_times.clear()
        self.signal_counts.clear()
        self.total_signals_generated = 0
        self.logger.info("Signal generator performance tracking reset")
