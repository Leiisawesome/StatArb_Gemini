"""
High-Performance Data Manager
============================

Ultra-fast data manager designed to achieve sub-millisecond market data
processing latency through vectorization, parallel processing, and
intelligent caching strategies.

Target: <1ms market data processing latency

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import time
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import threading
from functools import lru_cache
import pickle
import zlib

logger = logging.getLogger(__name__)

@dataclass
class DataManagerConfig:
    """Configuration for high-performance data manager"""
    # Core performance settings
    target_latency_ms: float = 1.0
    max_workers: int = 8
    enable_vectorization: bool = True
    enable_parallel_processing: bool = True
    
    # Caching configuration
    enable_intelligent_caching: bool = True
    cache_size: int = 50000
    cache_ttl_seconds: int = 300
    enable_compression: bool = True
    
    # Memory optimization
    enable_memory_mapping: bool = True
    chunk_size: int = 10000
    enable_lazy_loading: bool = True
    
    # Real-time processing
    enable_streaming: bool = True
    stream_buffer_size: int = 1000
    batch_processing_size: int = 5000

@dataclass
class DataProcessingResult:
    """Result of data processing operation"""
    processing_time_ms: float
    data_points_processed: int
    cache_hit_rate: float
    throughput_ops_per_second: float
    memory_usage_mb: float
    optimization_techniques_used: List[str] = field(default_factory=list)

class VectorizedDataProcessor:
    """Ultra-fast vectorized data processing engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_market_ticks(self, ticks: np.ndarray) -> np.ndarray:
        """Process market ticks using vectorized operations"""
        if len(ticks) == 0:
            return np.array([])
        
        # Vectorized OHLC calculation
        prices = ticks[:, 0] if ticks.ndim > 1 else ticks
        volumes = ticks[:, 1] if ticks.ndim > 1 and ticks.shape[1] > 1 else np.ones_like(prices)
        
        # Ultra-fast moving averages using convolution
        if len(prices) >= 20:
            ma_fast = np.convolve(prices, np.ones(5)/5, mode='same')
            ma_slow = np.convolve(prices, np.ones(20)/20, mode='same')
            
            # Vectorized signal calculation
            signals = np.where(ma_fast > ma_slow, 1.0, -1.0)
            
            # Volume-weighted adjustments
            vwap = np.cumsum(prices * volumes) / np.cumsum(volumes)
            
            return np.column_stack([prices, ma_fast, ma_slow, signals, vwap])
        else:
            return np.column_stack([prices, prices, prices, np.zeros_like(prices), prices])
    
    def calculate_technical_indicators(self, data: np.ndarray) -> Dict[str, np.ndarray]:
        """Calculate technical indicators using vectorized operations"""
        if len(data) == 0:
            return {}
        
        prices = data[:, 0] if data.ndim > 1 else data
        
        # RSI calculation (vectorized)
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        if len(gains) >= 14:
            avg_gains = np.convolve(gains, np.ones(14)/14, mode='same')
            avg_losses = np.convolve(losses, np.ones(14)/14, mode='same')
            rs = avg_gains / (avg_losses + 1e-10)  # Avoid division by zero
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = np.full_like(prices[1:], 50.0)
        
        # MACD calculation (vectorized)
        if len(prices) >= 26:
            ema_fast = self._exponential_moving_average(prices, 12)
            ema_slow = self._exponential_moving_average(prices, 26)
            macd_line = ema_fast - ema_slow
            signal_line = self._exponential_moving_average(macd_line, 9)
            macd_histogram = macd_line - signal_line
        else:
            macd_line = np.zeros_like(prices)
            signal_line = np.zeros_like(prices)
            macd_histogram = np.zeros_like(prices)
        
        return {
            'rsi': np.pad(rsi, (1, 0), mode='edge'),
            'macd': macd_line,
            'macd_signal': signal_line,
            'macd_histogram': macd_histogram
        }
    
    def _exponential_moving_average(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA using vectorized operations"""
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        # Vectorized EMA calculation
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        
        return ema

class IntelligentCache:
    """High-performance intelligent caching system"""
    
    def __init__(self, max_size: int = 50000, ttl_seconds: int = 300, enable_compression: bool = True):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_compression = enable_compression
        
        self._cache: Dict[str, Tuple[Any, datetime, int]] = {}
        self._access_counts: Dict[str, int] = {}
        self._lock = threading.RLock()
        
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache with LRU and TTL logic"""
        with self._lock:
            if key in self._cache:
                data, timestamp, access_count = self._cache[key]
                
                # Check TTL
                if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                    # Update access count
                    self._access_counts[key] = access_count + 1
                    self._cache[key] = (data, timestamp, access_count + 1)
                    
                    self.hits += 1
                    
                    # Decompress if needed
                    if self.enable_compression and isinstance(data, bytes):
                        return pickle.loads(zlib.decompress(data))
                    return data
                else:
                    # Remove expired item
                    del self._cache[key]
                    del self._access_counts[key]
            
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any) -> None:
        """Put item in cache with compression and size management"""
        with self._lock:
            # Compress if enabled
            if self.enable_compression:
                try:
                    compressed_value = zlib.compress(pickle.dumps(value))
                    stored_value = compressed_value
                except:
                    stored_value = value
            else:
                stored_value = value
            
            # Check if cache is full
            if len(self._cache) >= self.max_size:
                self._evict_least_recently_used()
            
            # Store with timestamp and access count
            self._cache[key] = (stored_value, datetime.now(), 1)
            self._access_counts[key] = 1
    
    def _evict_least_recently_used(self) -> None:
        """Evict least recently used items"""
        if not self._cache:
            return
        
        # Find items with lowest access count
        min_access_count = min(self._access_counts.values())
        lru_keys = [k for k, count in self._access_counts.items() if count == min_access_count]
        
        # Remove oldest among LRU items
        oldest_key = min(lru_keys, key=lambda k: self._cache[k][1])
        del self._cache[oldest_key]
        del self._access_counts[oldest_key]
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate"""
        total = self.hits + self.misses
        return (self.hits / total) * 100 if total > 0 else 0.0
    
    def clear(self) -> None:
        """Clear all cached items"""
        with self._lock:
            self._cache.clear()
            self._access_counts.clear()
            self.hits = 0
            self.misses = 0

class HighPerformanceDataManager:
    """
    Ultra-fast data manager designed to achieve sub-millisecond latency
    for market data processing through advanced optimization techniques.
    """
    
    def __init__(self, config: Optional[DataManagerConfig] = None):
        self.config = config or DataManagerConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # High-performance components
        self.vectorized_processor = VectorizedDataProcessor()
        self.intelligent_cache = IntelligentCache(
            max_size=self.config.cache_size,
            ttl_seconds=self.config.cache_ttl_seconds,
            enable_compression=self.config.enable_compression
        )
        
        # Thread pool for parallel processing
        if self.config.enable_parallel_processing:
            self.executor = ThreadPoolExecutor(
                max_workers=self.config.max_workers,
                thread_name_prefix="HighPerfData"
            )
        else:
            self.executor = None
        
        # Performance tracking
        self.processing_times: List[float] = []
        self.total_data_points = 0
        
        # Streaming buffers
        if self.config.enable_streaming:
            self.stream_buffer: List[Any] = []
            self.buffer_lock = threading.Lock()
        
        self.logger.info(f"HighPerformanceDataManager initialized - Target: <{self.config.target_latency_ms}ms")
    
    def process_market_data(self, symbols: Union[str, List[str]], data: Union[Dict, pd.DataFrame, np.ndarray]) -> DataProcessingResult:
        """
        Process market data with sub-millisecond latency target
        """
        start_time = time.perf_counter()
        optimization_techniques = []
        
        try:
            # Convert input to standardized format
            if isinstance(symbols, str):
                symbols = [symbols]
            
            # Check cache first
            if self.config.enable_intelligent_caching:
                cache_key = self._generate_cache_key(symbols, data)
                cached_result = self.intelligent_cache.get(cache_key)
                if cached_result is not None:
                    optimization_techniques.append("intelligent_caching")
                    return self._create_result(start_time, cached_result, optimization_techniques)
            
            # Process data using vectorized operations
            if self.config.enable_vectorization:
                processed_data = self._vectorized_process(data)
                optimization_techniques.append("vectorization")
            else:
                processed_data = self._standard_process(data)
            
            # Apply parallel processing for multiple symbols
            if len(symbols) > 1 and self.config.enable_parallel_processing and self.executor:
                processed_data = self._parallel_process_symbols(symbols, processed_data)
                optimization_techniques.append("parallel_processing")
            
            # Cache the result
            if self.config.enable_intelligent_caching:
                self.intelligent_cache.put(cache_key, processed_data)
                optimization_techniques.append("result_caching")
            
            return self._create_result(start_time, processed_data, optimization_techniques)
            
        except Exception as e:
            self.logger.error(f"High-performance data processing failed: {e}")
            # Fallback to standard processing
            return self._fallback_process(symbols, data, start_time)
    
    def _vectorized_process(self, data: Any) -> np.ndarray:
        """Process data using vectorized operations"""
        # Convert to numpy array for vectorized processing
        if isinstance(data, pd.DataFrame):
            data_array = data.values
        elif isinstance(data, dict):
            # Convert dict to array (assuming price data)
            if 'prices' in data:
                data_array = np.array(data['prices'])
            elif 'close' in data:
                data_array = np.array(data['close'])
            else:
                data_array = np.array(list(data.values()))
        elif isinstance(data, list):
            data_array = np.array(data)
        else:
            data_array = data
        
        # Ensure data is 2D for processing
        if data_array.ndim == 1:
            data_array = data_array.reshape(-1, 1)
        
        # Process using vectorized operations
        processed = self.vectorized_processor.process_market_ticks(data_array)
        
        # Calculate technical indicators
        indicators = self.vectorized_processor.calculate_technical_indicators(processed)
        
        return processed
    
    def _parallel_process_symbols(self, symbols: List[str], data: np.ndarray) -> Dict[str, np.ndarray]:
        """Process multiple symbols in parallel"""
        if not self.executor:
            return {symbol: data for symbol in symbols}
        
        # Split data for parallel processing
        chunk_size = max(1, len(data) // len(symbols))
        futures = []
        
        for i, symbol in enumerate(symbols):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(data))
            symbol_data = data[start_idx:end_idx]
            
            future = self.executor.submit(self._process_symbol_chunk, symbol, symbol_data)
            futures.append((symbol, future))
        
        # Collect results
        results = {}
        for symbol, future in futures:
            try:
                results[symbol] = future.result(timeout=0.5)  # 0.5s timeout for ultra-fast processing
            except Exception as e:
                self.logger.warning(f"Parallel processing failed for {symbol}: {e}")
                results[symbol] = data  # Fallback to original data
        
        return results
    
    def _process_symbol_chunk(self, symbol: str, data: np.ndarray) -> np.ndarray:
        """Process a chunk of data for a specific symbol"""
        # Apply symbol-specific processing
        if len(data) > 0:
            # Calculate symbol-specific indicators
            processed = self.vectorized_processor.process_market_ticks(data)
            return processed
        return data
    
    def _standard_process(self, data: Any) -> Any:
        """Standard data processing (fallback)"""
        # Simple processing for fallback
        if isinstance(data, (list, np.ndarray)):
            return np.array(data)
        elif isinstance(data, pd.DataFrame):
            return data.values
        else:
            return data
    
    def _generate_cache_key(self, symbols: List[str], data: Any) -> str:
        """Generate cache key for data"""
        # Create a hash-based cache key
        symbols_str = "_".join(sorted(symbols))
        
        if isinstance(data, np.ndarray):
            data_hash = hash(data.tobytes())
        elif isinstance(data, pd.DataFrame):
            data_hash = hash(data.values.tobytes())
        elif isinstance(data, dict):
            data_hash = hash(str(sorted(data.items())))
        else:
            data_hash = hash(str(data))
        
        return f"{symbols_str}_{data_hash}"
    
    def _create_result(self, start_time: float, processed_data: Any, optimization_techniques: List[str]) -> DataProcessingResult:
        """Create processing result with performance metrics"""
        processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
        
        # Update performance tracking
        self.processing_times.append(processing_time)
        if len(self.processing_times) > 1000:  # Keep only recent 1000 measurements
            self.processing_times = self.processing_times[-1000:]
        
        # Calculate data points processed
        if isinstance(processed_data, np.ndarray):
            data_points = processed_data.size
        elif isinstance(processed_data, dict):
            data_points = sum(arr.size if isinstance(arr, np.ndarray) else len(arr) for arr in processed_data.values())
        elif hasattr(processed_data, '__len__'):
            data_points = len(processed_data)
        else:
            data_points = 1
        
        self.total_data_points += data_points
        
        # Calculate throughput
        throughput = (data_points / (processing_time / 1000)) if processing_time > 0 else 0
        
        # Get cache hit rate
        cache_hit_rate = self.intelligent_cache.get_hit_rate()
        
        # Estimate memory usage
        memory_usage = self._estimate_memory_usage()
        
        return DataProcessingResult(
            processing_time_ms=processing_time,
            data_points_processed=data_points,
            cache_hit_rate=cache_hit_rate,
            throughput_ops_per_second=throughput,
            memory_usage_mb=memory_usage,
            optimization_techniques_used=optimization_techniques
        )
    
    def _fallback_process(self, symbols: List[str], data: Any, start_time: float) -> DataProcessingResult:
        """Fallback processing when high-performance methods fail"""
        self.logger.warning("Using fallback processing")
        
        # Simple fallback processing
        if isinstance(data, (list, tuple)):
            processed_data = np.array(data)
        elif isinstance(data, pd.DataFrame):
            processed_data = data.values
        else:
            processed_data = data
        
        return self._create_result(start_time, processed_data, ["fallback_processing"])
    
    def _estimate_memory_usage(self) -> float:
        """Estimate current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        if not self.processing_times:
            return {}
        
        return {
            'average_latency_ms': np.mean(self.processing_times),
            'min_latency_ms': np.min(self.processing_times),
            'max_latency_ms': np.max(self.processing_times),
            'p95_latency_ms': np.percentile(self.processing_times, 95),
            'p99_latency_ms': np.percentile(self.processing_times, 99),
            'total_data_points_processed': self.total_data_points,
            'cache_hit_rate': self.intelligent_cache.get_hit_rate(),
            'target_latency_ms': self.config.target_latency_ms,
            'target_achieved': np.mean(self.processing_times) < self.config.target_latency_ms
        }
    
    def reset_performance_tracking(self) -> None:
        """Reset performance tracking metrics"""
        self.processing_times.clear()
        self.total_data_points = 0
        self.intelligent_cache.clear()
        self.logger.info("Performance tracking metrics reset")
    
    def __del__(self):
        """Cleanup resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
