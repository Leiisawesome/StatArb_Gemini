"""
Performance Optimization Module for Analytics
============================================

Phase 3: Performance Optimizations
- Numpy vectorization for mathematical operations
- Parallel processing for independent calculations
- Memory-efficient data processing
- Intelligent caching with performance monitoring

Author: Professional Trading System Architecture
Version: 1.0.0 (Phase 3: Performance Optimizations)
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable, Iterator
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import wraps, lru_cache
import threading
import time
import psutil
import gc
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance optimization metrics"""
    execution_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    vectorization_ratio: float = 0.0
    cache_hit_ratio: float = 0.0
    parallel_efficiency: float = 0.0
    

class VectorizedCalculations:
    """
    High-performance vectorized calculations using numpy
    
    Replaces scalar operations with efficient vector computations
    for significant performance improvements.
    """
    
    @staticmethod
    def vectorized_returns_analysis(returns: np.ndarray) -> Dict[str, float]:
        """
        Vectorized analysis of returns series
        
        Args:
            returns: Numpy array of returns
            
        Returns:
            Dictionary of calculated metrics
        """
        if len(returns) == 0:
            return {}
        
        # Remove NaN values efficiently
        clean_returns = returns[~np.isnan(returns)]
        if len(clean_returns) == 0:
            return {}
        
        # Vectorized basic calculations
        total_return = np.prod(1 + clean_returns) - 1
        mean_return = np.mean(clean_returns)
        std_return = np.std(clean_returns, ddof=1)
        
        # Annualized metrics (vectorized)
        annualized_return = (1 + mean_return) ** 252 - 1
        volatility = std_return * np.sqrt(252)
        
        # Risk metrics (vectorized)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0.0
        
        # Downside deviation (vectorized)
        negative_returns = clean_returns[clean_returns < 0]
        downside_std = np.std(negative_returns, ddof=1) if len(negative_returns) > 0 else 0.0
        sortino_ratio = annualized_return / (downside_std * np.sqrt(252)) if downside_std > 0 else 0.0
        
        # VaR calculations (vectorized)
        var_95 = np.percentile(clean_returns, 5) if len(clean_returns) >= 20 else 0.0
        var_returns = clean_returns[clean_returns <= var_95] if var_95 < 0 else np.array([])
        cvar_95 = np.mean(var_returns) if len(var_returns) > 0 else 0.0
        
        # Distribution metrics (vectorized)
        from scipy import stats
        skewness = stats.skew(clean_returns) if len(clean_returns) >= 3 else 0.0
        kurtosis = stats.kurtosis(clean_returns) if len(clean_returns) >= 4 else 0.0
        
        # Win rate (vectorized)
        win_rate = np.mean(clean_returns > 0) if len(clean_returns) > 0 else 0.0
        
        return {
            'total_return': float(total_return),
            'annualized_return': float(annualized_return),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'var_95': float(var_95),
            'cvar_95': float(cvar_95),
            'skewness': float(skewness),
            'kurtosis': float(kurtosis),
            'win_rate': float(win_rate)
        }
    
    @staticmethod
    def vectorized_drawdown_analysis(returns: np.ndarray) -> Dict[str, float]:
        """
        Vectorized drawdown analysis
        
        Args:
            returns: Numpy array of returns
            
        Returns:
            Dictionary of drawdown metrics
        """
        if len(returns) == 0:
            return {}
        
        clean_returns = returns[~np.isnan(returns)]
        if len(clean_returns) == 0:
            return {}
        
        # Vectorized cumulative returns
        cumulative_returns = np.cumprod(1 + clean_returns)
        
        # Vectorized rolling maximum
        rolling_max = np.maximum.accumulate(cumulative_returns)
        
        # Vectorized drawdowns
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        
        # Metrics
        max_drawdown = np.min(drawdowns)
        avg_drawdown = np.mean(drawdowns[drawdowns < 0]) if np.any(drawdowns < 0) else 0.0
        
        # Drawdown duration analysis
        is_drawdown = drawdowns < -0.001  # 0.1% threshold
        drawdown_periods = []
        current_period = 0
        
        for in_dd in is_drawdown:
            if in_dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0
        
        if current_period > 0:
            drawdown_periods.append(current_period)
        
        max_drawdown_duration = np.max(drawdown_periods) if drawdown_periods else 0
        avg_drawdown_duration = np.mean(drawdown_periods) if drawdown_periods else 0
        
        # Calmar ratio
        annualized_return = (1 + np.mean(clean_returns)) ** 252 - 1
        calmar_ratio = annualized_return / abs(max_drawdown) if abs(max_drawdown) > 1e-8 else 0.0
        
        return {
            'max_drawdown': float(max_drawdown),
            'avg_drawdown': float(avg_drawdown),
            'max_drawdown_duration': int(max_drawdown_duration),
            'avg_drawdown_duration': float(avg_drawdown_duration),
            'calmar_ratio': float(calmar_ratio)
        }
    
    @staticmethod
    def vectorized_correlation_analysis(returns_matrix: np.ndarray) -> Dict[str, Any]:
        """
        Vectorized correlation analysis for multiple assets
        
        Args:
            returns_matrix: 2D numpy array where each column is an asset's returns
            
        Returns:
            Dictionary of correlation metrics
        """
        if returns_matrix.size == 0 or returns_matrix.ndim != 2:
            return {}
        
        # Remove rows with any NaN values
        clean_matrix = returns_matrix[~np.isnan(returns_matrix).any(axis=1)]
        
        if len(clean_matrix) == 0:
            return {}
        
        # Vectorized correlation matrix
        correlation_matrix = np.corrcoef(clean_matrix.T)
        
        # Extract upper triangle (excluding diagonal)
        n_assets = correlation_matrix.shape[0]
        upper_triangle = correlation_matrix[np.triu_indices(n_assets, k=1)]
        
        # Correlation statistics
        avg_correlation = np.mean(upper_triangle)
        max_correlation = np.max(upper_triangle)
        min_correlation = np.min(upper_triangle)
        correlation_std = np.std(upper_triangle)
        
        # Eigenvalue analysis for portfolio risk
        eigenvalues = np.linalg.eigvals(correlation_matrix)
        condition_number = np.max(eigenvalues) / np.min(eigenvalues) if np.min(eigenvalues) > 0 else np.inf
        
        return {
            'correlation_matrix': correlation_matrix.tolist(),
            'avg_correlation': float(avg_correlation),
            'max_correlation': float(max_correlation),
            'min_correlation': float(min_correlation),
            'correlation_std': float(correlation_std),
            'condition_number': float(condition_number),
            'eigenvalues': eigenvalues.tolist()
        }
    
    @staticmethod
    def calculate_rolling_features(data: np.ndarray, window: int = 5) -> List[np.ndarray]:
        """
        Calculate rolling statistics features for each column in data
        Returns list of feature matrices for each column
        """
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        rolling_features = []
        
        for col_idx in range(data.shape[1]):
            col_data = data[:, col_idx]
            n_samples = len(col_data)
            
            # Initialize feature arrays
            rolling_mean = np.zeros(n_samples)
            rolling_std = np.zeros(n_samples)
            rolling_min = np.zeros(n_samples)
            rolling_max = np.zeros(n_samples)
            
            # Vectorized rolling computation
            for i in range(n_samples):
                start_idx = max(0, i - window + 1)
                window_data = col_data[start_idx:i+1]
                
                rolling_mean[i] = np.mean(window_data)
                rolling_std[i] = np.std(window_data)
                rolling_min[i] = np.min(window_data)
                rolling_max[i] = np.max(window_data)
            
            # Stack features for this column
            col_features = np.column_stack([
                rolling_mean, rolling_std, rolling_min, rolling_max
            ])
            rolling_features.append(col_features)
        
        return rolling_features
    
    @staticmethod
    def calculate_rolling_z_scores(data: np.ndarray, window: int = 5) -> np.ndarray:
        """
        Calculate rolling z-scores for data using vectorized operations
        """
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        n_samples, n_cols = data.shape
        z_scores = np.zeros_like(data)
        
        for col_idx in range(n_cols):
            col_data = data[:, col_idx]
            
            for i in range(n_samples):
                start_idx = max(0, i - window + 1)
                window_data = col_data[start_idx:i+1]
                
                mean_val = np.mean(window_data)
                std_val = np.std(window_data)
                
                # Avoid division by zero
                if std_val > 1e-8:
                    z_scores[i, col_idx] = (col_data[i] - mean_val) / std_val
                else:
                    z_scores[i, col_idx] = 0.0
        
        return z_scores


class ParallelProcessor:
    """
    Parallel processing for independent analytics calculations
    
    Uses asyncio and concurrent.futures for optimal performance
    across CPU-bound and I/O-bound operations.
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize parallel processor
        
        Args:
            max_workers: Maximum number of worker threads/processes
        """
        self.max_workers = max_workers or min(4, psutil.cpu_count())
        self.thread_executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=self.max_workers)
        
        logger.info(f"ParallelProcessor initialized with {self.max_workers} workers")
    
    async def parallel_analytics(self, datasets: List[Tuple[str, np.ndarray]], 
                                calculation_func: Callable) -> Dict[str, Any]:
        """
        Run analytics calculations in parallel across multiple datasets
        
        Args:
            datasets: List of (name, data) tuples
            calculation_func: Function to apply to each dataset
            
        Returns:
            Dictionary mapping dataset names to results
        """
        if not datasets:
            return {}
        
        # Create tasks for parallel execution
        tasks = []
        for name, data in datasets:
            task = asyncio.get_event_loop().run_in_executor(
                self.thread_executor, 
                calculation_func, 
                data
            )
            tasks.append((name, task))
        
        # Gather results
        results = {}
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Error in parallel calculation for {name}: {e}")
                results[name] = {}
        
        return results
    
    async def parallel_vectorized_analysis(self, datasets: Dict[str, np.ndarray]) -> Dict[str, Dict[str, Any]]:
        """
        Run vectorized analysis in parallel across multiple datasets
        
        Args:
            datasets: Dictionary mapping names to numpy arrays
            
        Returns:
            Dictionary of analysis results
        """
        if not datasets:
            return {}
        
        # Prepare tasks
        dataset_items = list(datasets.items())
        
        # Parallel returns analysis
        returns_tasks = await self.parallel_analytics(
            dataset_items, 
            VectorizedCalculations.vectorized_returns_analysis
        )
        
        # Parallel drawdown analysis
        drawdown_tasks = await self.parallel_analytics(
            dataset_items,
            VectorizedCalculations.vectorized_drawdown_analysis
        )
        
        # Combine results
        combined_results = {}
        for name in datasets.keys():
            combined_results[name] = {
                'returns_analysis': returns_tasks.get(name, {}),
                'drawdown_analysis': drawdown_tasks.get(name, {})
            }
        
        return combined_results
    
    def cleanup(self):
        """Clean up executor resources"""
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)


class IntelligentCache:
    """
    Intelligent caching system with performance monitoring
    
    Features:
    - LRU cache with TTL
    - Memory usage monitoring
    - Cache hit ratio tracking
    - Automatic cache invalidation
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        Initialize intelligent cache
        
        Args:
            max_size: Maximum cache size
            ttl_seconds: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.access_times: Dict[str, float] = {}
        self.hit_count = 0
        self.miss_count = 0
        self._lock = threading.Lock()
        
        logger.info(f"IntelligentCache initialized: max_size={max_size}, ttl={ttl_seconds}s")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            current_time = time.time()
            
            if key in self.cache:
                value, timestamp = self.cache[key]
                
                # Check TTL
                if current_time - timestamp < self.ttl_seconds:
                    self.access_times[key] = current_time
                    self.hit_count += 1
                    return value
                else:
                    # Expired, remove
                    del self.cache[key]
                    if key in self.access_times:
                        del self.access_times[key]
            
            self.miss_count += 1
            return None
    
    def put(self, key: str, value: Any):
        """Put value in cache"""
        with self._lock:
            current_time = time.time()
            
            # Check cache size and evict LRU if needed
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
            
            self.cache[key] = (value, current_time)
            self.access_times[key] = current_time
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times, key=self.access_times.get)
        if lru_key in self.cache:
            del self.cache[lru_key]
        del self.access_times[lru_key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_ratio = self.hit_count / total_requests if total_requests > 0 else 0.0
        
        return {
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_ratio': hit_ratio,
            'ttl_seconds': self.ttl_seconds
        }
    
    def clear(self):
        """Clear cache"""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()
            self.hit_count = 0
            self.miss_count = 0


class PerformanceProfiler:
    """
    Performance profiling and monitoring system
    
    Tracks execution times, memory usage, and optimization metrics
    across all analytics operations.
    """
    
    def __init__(self):
        """Initialize performance profiler"""
        self.metrics: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        self.active_profiles: Dict[str, float] = {}
        self._lock = threading.Lock()
        
        logger.info("PerformanceProfiler initialized")
    
    def start_profiling(self, operation_name: str) -> str:
        """Start profiling an operation"""
        profile_id = f"{operation_name}_{int(time.time() * 1000000)}"
        self.active_profiles[profile_id] = time.time()
        return profile_id
    
    def end_profiling(self, profile_id: str, 
                     vectorization_ratio: float = 0.0,
                     cache_hit_ratio: float = 0.0,
                     parallel_efficiency: float = 0.0) -> PerformanceMetrics:
        """End profiling and record metrics"""
        if profile_id not in self.active_profiles:
            logger.warning(f"Profile ID {profile_id} not found")
            return PerformanceMetrics()
        
        # Calculate execution time
        start_time = self.active_profiles.pop(profile_id)
        execution_time = time.time() - start_time
        
        # Get memory and CPU usage
        process = psutil.Process()
        memory_usage_mb = process.memory_info().rss / 1024 / 1024
        cpu_usage_percent = process.cpu_percent()
        
        # Create metrics
        metrics = PerformanceMetrics(
            execution_time=execution_time,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent,
            vectorization_ratio=vectorization_ratio,
            cache_hit_ratio=cache_hit_ratio,
            parallel_efficiency=parallel_efficiency
        )
        
        # Extract operation name
        operation_name = profile_id.split('_')[0]
        
        with self._lock:
            self.metrics[operation_name].append(metrics)
            
            # Keep only last 100 measurements per operation
            if len(self.metrics[operation_name]) > 100:
                self.metrics[operation_name] = self.metrics[operation_name][-100:]
        
        return metrics
    
    def get_performance_summary(self) -> Dict[str, Dict[str, float]]:
        """Get performance summary across all operations"""
        summary = {}
        
        with self._lock:
            for operation, metric_list in self.metrics.items():
                if not metric_list:
                    continue
                
                execution_times = [m.execution_time for m in metric_list]
                memory_usages = [m.memory_usage_mb for m in metric_list]
                
                summary[operation] = {
                    'avg_execution_time': np.mean(execution_times),
                    'min_execution_time': np.min(execution_times),
                    'max_execution_time': np.max(execution_times),
                    'std_execution_time': np.std(execution_times),
                    'avg_memory_usage_mb': np.mean(memory_usages),
                    'avg_vectorization_ratio': np.mean([m.vectorization_ratio for m in metric_list]),
                    'avg_cache_hit_ratio': np.mean([m.cache_hit_ratio for m in metric_list]),
                    'avg_parallel_efficiency': np.mean([m.parallel_efficiency for m in metric_list]),
                    'sample_count': len(metric_list)
                }
        
        return summary


class MemoryOptimizer:
    """
    Memory optimization utilities for large dataset processing
    
    Features:
    - Chunk processing for large arrays
    - Memory usage monitoring
    - Lazy evaluation patterns
    - Garbage collection optimization
    """
    
    @staticmethod
    def chunk_processor(data: np.ndarray, chunk_size: int = 10000) -> Iterator[np.ndarray]:
        """
        Process large arrays in chunks to manage memory usage
        
        Args:
            data: Large numpy array to process
            chunk_size: Size of each chunk
            
        Yields:
            Chunks of the original array
        """
        if data.size == 0:
            return
        
        # Flatten if multidimensional for consistent chunking
        original_shape = data.shape
        if data.ndim > 1:
            data_flat = data.reshape(-1)
            total_elements = data_flat.size
        else:
            data_flat = data
            total_elements = data.size
        
        # Process in chunks
        for start_idx in range(0, total_elements, chunk_size):
            end_idx = min(start_idx + chunk_size, total_elements)
            chunk = data_flat[start_idx:end_idx]
            
            # Reshape chunk if original was multidimensional
            if data.ndim > 1:
                # Calculate chunk shape maintaining original structure
                elements_in_chunk = end_idx - start_idx
                if data.ndim == 2:
                    rows_in_chunk = min(elements_in_chunk // original_shape[1], 
                                      original_shape[0] - start_idx // original_shape[1])
                    chunk = chunk.reshape(rows_in_chunk, original_shape[1])
                else:
                    # For higher dimensions, keep it flat for simplicity
                    pass
            
            yield chunk
    
    @staticmethod
    def memory_efficient_calculation(data: np.ndarray, 
                                   calculation_func: Callable,
                                   chunk_size: int = 10000,
                                   reduce_func: Callable = np.concatenate) -> Any:
        """
        Perform memory-efficient calculations on large datasets
        
        Args:
            data: Large dataset
            calculation_func: Function to apply to each chunk
            chunk_size: Size of processing chunks
            reduce_func: Function to combine chunk results
            
        Returns:
            Combined result from all chunks
        """
        if data.size == 0:
            return None
        
        results = []
        memory_before = psutil.Process().memory_info().rss
        
        try:
            for chunk in MemoryOptimizer.chunk_processor(data, chunk_size):
                chunk_result = calculation_func(chunk)
                if chunk_result is not None:
                    results.append(chunk_result)
                
                # Optional garbage collection for large chunks
                if len(results) % 10 == 0:
                    gc.collect()
            
            # Combine results
            if results:
                if reduce_func == np.concatenate and all(isinstance(r, np.ndarray) for r in results):
                    final_result = np.concatenate(results, axis=0)
                elif reduce_func == np.mean:
                    final_result = np.mean(results)
                elif reduce_func == np.sum:
                    final_result = np.sum(results)
                else:
                    final_result = reduce_func(results)
            else:
                final_result = None
            
            memory_after = psutil.Process().memory_info().rss
            memory_used = (memory_after - memory_before) / 1024 / 1024  # MB
            
            logger.debug(f"Memory-efficient calculation used {memory_used:.2f} MB")
            return final_result
            
        except Exception as e:
            logger.error(f"Error in memory-efficient calculation: {e}")
            return None
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Get current memory usage statistics"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / 1024 / 1024
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {}
    
    @staticmethod
    def optimize_memory_usage():
        """Optimize current memory usage through garbage collection"""
        before_memory = MemoryOptimizer.get_memory_usage()
        
        # Force garbage collection
        gc.collect()
        
        after_memory = MemoryOptimizer.get_memory_usage()
        
        if before_memory and after_memory:
            memory_freed = before_memory.get('rss_mb', 0) - after_memory.get('rss_mb', 0)
            logger.info(f"Memory optimization freed {memory_freed:.2f} MB")
        
        return after_memory


class LazyEvaluator:
    """
    Lazy evaluation patterns for deferred computation
    
    Reduces memory usage by computing values only when needed
    """
    
    def __init__(self):
        self._computed_values = {}
        self._computation_functions = {}
    
    def register_computation(self, key: str, computation_func: Callable, *args, **kwargs):
        """
        Register a computation to be evaluated lazily
        
        Args:
            key: Unique key for the computation
            computation_func: Function to execute when value is needed
            *args, **kwargs: Arguments for the computation function
        """
        self._computation_functions[key] = (computation_func, args, kwargs)
        # Remove any previously computed value
        if key in self._computed_values:
            del self._computed_values[key]
    
    def get_value(self, key: str) -> Any:
        """
        Get computed value, calculating if necessary
        
        Args:
            key: Key of the computation
            
        Returns:
            Computed value
        """
        if key not in self._computed_values:
            if key in self._computation_functions:
                func, args, kwargs = self._computation_functions[key]
                try:
                    self._computed_values[key] = func(*args, **kwargs)
                    logger.debug(f"Lazy evaluation computed: {key}")
                except Exception as e:
                    logger.error(f"Error in lazy evaluation for {key}: {e}")
                    return None
            else:
                logger.warning(f"No computation registered for key: {key}")
                return None
        
        return self._computed_values[key]
    
    def clear_cache(self, key: str = None):
        """Clear cached values"""
        if key:
            self._computed_values.pop(key, None)
        else:
            self._computed_values.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_values': len(self._computed_values),
            'registered_computations': len(self._computation_functions),
            'cached_keys': list(self._computed_values.keys())
        }


# Global instances for performance optimization
vectorized_calc = VectorizedCalculations()
parallel_processor = ParallelProcessor()
intelligent_cache = IntelligentCache()
performance_profiler = PerformanceProfiler()
memory_optimizer = MemoryOptimizer()
lazy_evaluator = LazyEvaluator()


def performance_optimized(cache_key_func: Optional[Callable] = None,
                         vectorization_ratio: float = 0.0,
                         enable_parallel: bool = False):
    """
    Decorator for performance-optimized functions
    
    Args:
        cache_key_func: Function to generate cache key
        vectorization_ratio: Ratio of vectorized operations (0-1)
        enable_parallel: Whether to enable parallel processing hints
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Start profiling
            profile_id = performance_profiler.start_profiling(func.__name__)
            
            # Check cache if key function provided
            cache_hit = False
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
                cached_result = intelligent_cache.get(cache_key)
                if cached_result is not None:
                    cache_hit = True
                    performance_profiler.end_profiling(
                        profile_id,
                        vectorization_ratio=vectorization_ratio,
                        cache_hit_ratio=1.0,
                        parallel_efficiency=1.0 if enable_parallel else 0.0
                    )
                    return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            if cache_key_func and result is not None:
                intelligent_cache.put(cache_key, result)
            
            # End profiling
            cache_stats = intelligent_cache.get_stats()
            performance_profiler.end_profiling(
                profile_id,
                vectorization_ratio=vectorization_ratio,
                cache_hit_ratio=cache_stats['hit_ratio'],
                parallel_efficiency=1.0 if enable_parallel else 0.0
            )
            
            return result
        
        return wrapper
    return decorator


def cleanup_performance_resources():
    """Clean up performance optimization resources"""
    try:
        parallel_processor.cleanup()
        intelligent_cache.clear()
        gc.collect()
        logger.info("Performance optimization resources cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up performance resources: {e}")