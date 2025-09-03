"""
Performance Optimizations - Phase 2 Integration
==============================================

High-performance optimizations integrated into the unified trading engine.
Consolidates and enhances optimizations (formerly from trade_engine/optimization, now archived).

Features:
- Hot path optimization with caching
- Function-level performance decorators
- Intelligent caching strategies
- Real-time performance monitoring
- Memory-efficient data structures

Author: Professional Trading System Architecture
Version: 2.0 (Integrated Performance)
"""

import time
import asyncio
import logging
from functools import wraps, lru_cache
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

logger = logging.getLogger(__name__)

# ================================================================================
# PERFORMANCE METRICS AND MONITORING
# ================================================================================

@dataclass
class PerformanceMetrics:
    """Performance metrics for hot path functions"""
    function_name: str
    total_calls: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    error_count: int = 0
    last_call_time: Optional[datetime] = None
    
    def update(self, execution_time_ms: float, cache_hit: bool = False, error: bool = False):
        """Update metrics with new execution data"""
        self.total_calls += 1
        self.total_time_ms += execution_time_ms
        self.min_time_ms = min(self.min_time_ms, execution_time_ms)
        self.max_time_ms = max(self.max_time_ms, execution_time_ms)
        self.last_call_time = datetime.now()
        
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            
        if error:
            self.error_count += 1
    
    def get_average_time_ms(self) -> float:
        """Get average execution time"""
        return self.total_time_ms / self.total_calls if self.total_calls > 0 else 0.0
    
    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate"""
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / total_requests if total_requests > 0 else 0.0

class PerformanceMonitor:
    """Real-time performance monitoring for hot paths"""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.lock = threading.RLock()
        self._enabled = True
        
    def record_execution(self, function_name: str, execution_time_ms: float, 
                        cache_hit: bool = False, error: bool = False):
        """Record function execution metrics"""
        if not self._enabled:
            return
            
        with self.lock:
            if function_name not in self.metrics:
                self.metrics[function_name] = PerformanceMetrics(function_name)
            
            self.metrics[function_name].update(execution_time_ms, cache_hit, error)
    
    def get_metrics(self, function_name: str) -> Optional[PerformanceMetrics]:
        """Get metrics for specific function"""
        with self.lock:
            return self.metrics.get(function_name)
    
    def get_all_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Get all performance metrics"""
        with self.lock:
            return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset all performance metrics"""
        with self.lock:
            self.metrics.clear()
    
    def get_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        with self.lock:
            if not self.metrics:
                return "No performance data available"
            
            report = []
            report.append("=" * 80)
            report.append("HOT PATH PERFORMANCE REPORT")
            report.append("=" * 80)
            
            # Sort by total time (most expensive first)
            sorted_metrics = sorted(
                self.metrics.values(), 
                key=lambda m: m.total_time_ms, 
                reverse=True
            )
            
            for metrics in sorted_metrics:
                report.append(f"🔥 {metrics.function_name}:")
                report.append(f"  • Total Calls: {metrics.total_calls:,}")
                report.append(f"  • Avg Time: {metrics.get_average_time_ms():.2f}ms")
                report.append(f"  • Min/Max: {metrics.min_time_ms:.2f}ms / {metrics.max_time_ms:.2f}ms")
                report.append(f"  • Cache Hit Rate: {metrics.get_cache_hit_rate():.1%}")
                report.append(f"  • Error Rate: {metrics.error_count/metrics.total_calls:.1%}")
                report.append(f"  • Total Time: {metrics.total_time_ms:.2f}ms")
                report.append("")
            
            report.append("=" * 80)
            return "\n".join(report)

# Global performance monitor
performance_monitor = PerformanceMonitor()

# ================================================================================
# INTELLIGENT CACHING SYSTEM
# ================================================================================

class IntelligentCache:
    """High-performance caching system with TTL and LRU eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry_time)
        self.access_order = deque()  # For LRU tracking
        self.lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            value, expiry_time = self.cache[key]
            
            # Check if expired
            if time.time() > expiry_time:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
                self.misses += 1
                return None
            
            # Update access order for LRU
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            
            self.hits += 1
            return value
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Put value in cache"""
        with self.lock:
            ttl = ttl or self.default_ttl
            expiry_time = time.time() + ttl
            
            # Remove if already exists
            if key in self.cache:
                if key in self.access_order:
                    self.access_order.remove(key)
            
            # Evict if at capacity
            while len(self.cache) >= self.max_size:
                self._evict_lru()
            
            self.cache[key] = (value, expiry_time)
            self.access_order.append(key)
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if self.access_order:
            lru_key = self.access_order.popleft()
            if lru_key in self.cache:
                del self.cache[lru_key]
                self.evictions += 1
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'evictions': self.evictions
            }

# Global cache instances
signal_cache = IntelligentCache(max_size=500, default_ttl=60.0)  # 1 minute TTL for signals
execution_cache = IntelligentCache(max_size=200, default_ttl=30.0)  # 30 second TTL for executions
portfolio_cache = IntelligentCache(max_size=100, default_ttl=120.0)  # 2 minute TTL for portfolio

# ================================================================================
# HOT PATH OPTIMIZATION DECORATORS
# ================================================================================

def optimize_hot_path(cache_key_func: Optional[Callable] = None, 
                     cache_ttl: float = 60.0,
                     cache_instance: Optional[IntelligentCache] = None):
    """
    Decorator for optimizing hot path functions with caching and monitoring.
    
    Args:
        cache_key_func: Function to generate cache key from args
        cache_ttl: Cache time-to-live in seconds
        cache_instance: Specific cache instance to use
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            function_name = f"{func.__module__}.{func.__name__}"
            cache_hit = False
            error = False
            
            try:
                # Try cache first if cache key function provided
                if cache_key_func and cache_instance:
                    cache_key = cache_key_func(*args, **kwargs)
                    cached_result = cache_instance.get(cache_key)
                    
                    if cached_result is not None:
                        cache_hit = True
                        execution_time = (time.perf_counter() - start_time) * 1000
                        performance_monitor.record_execution(function_name, execution_time, cache_hit)
                        return cached_result
                
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Cache result if caching enabled
                if cache_key_func and cache_instance:
                    cache_key = cache_key_func(*args, **kwargs)
                    cache_instance.put(cache_key, result, cache_ttl)
                
                return result
                
            except Exception as e:
                error = True
                raise
            finally:
                execution_time = (time.perf_counter() - start_time) * 1000
                performance_monitor.record_execution(function_name, execution_time, cache_hit, error)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            function_name = f"{func.__module__}.{func.__name__}"
            cache_hit = False
            error = False
            
            try:
                # Try cache first if cache key function provided
                if cache_key_func and cache_instance:
                    cache_key = cache_key_func(*args, **kwargs)
                    cached_result = cache_instance.get(cache_key)
                    
                    if cached_result is not None:
                        cache_hit = True
                        execution_time = (time.perf_counter() - start_time) * 1000
                        performance_monitor.record_execution(function_name, execution_time, cache_hit)
                        return cached_result
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache result if caching enabled
                if cache_key_func and cache_instance:
                    cache_key = cache_key_func(*args, **kwargs)
                    cache_instance.put(cache_key, result, cache_ttl)
                
                return result
                
            except Exception as e:
                error = True
                raise
            finally:
                execution_time = (time.perf_counter() - start_time) * 1000
                performance_monitor.record_execution(function_name, execution_time, cache_hit, error)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# ================================================================================
# SPECIALIZED TRADING OPTIMIZATIONS
# ================================================================================

def signal_generation_cache_key(*args, **kwargs) -> str:
    """Generate cache key for signal generation"""
    # Use market data hash and strategy config as key
    market_data = args[0] if args else kwargs.get('market_data')
    strategy_config = args[1] if len(args) > 1 else kwargs.get('strategy_config', {})
    
    if hasattr(market_data, 'index') and len(market_data) > 0:
        # Use last timestamp and data shape as key components
        last_timestamp = str(market_data.index[-1]) if hasattr(market_data.index[-1], '__str__') else 'no_timestamp'
        data_shape = f"{len(market_data)}x{len(market_data.columns) if hasattr(market_data, 'columns') else 0}"
        config_hash = str(hash(frozenset(strategy_config.items()) if isinstance(strategy_config, dict) else strategy_config))
        return f"signals_{last_timestamp}_{data_shape}_{config_hash}"
    
    return f"signals_default_{time.time()}"

def execution_cache_key(*args, **kwargs) -> str:
    """Generate cache key for execution results"""
    signals = args[0] if args else kwargs.get('signals', [])
    strategy_config = args[1] if len(args) > 1 else kwargs.get('strategy_config', {})
    
    if signals:
        # Use signal count and config as key
        signal_count = len(signals)
        config_hash = str(hash(frozenset(strategy_config.items()) if isinstance(strategy_config, dict) else strategy_config))
        return f"execution_{signal_count}_{config_hash}"
    
    return f"execution_default_{time.time()}"

def portfolio_cache_key(*args, **kwargs) -> str:
    """Generate cache key for portfolio updates"""
    execution_results = args[0] if args else kwargs.get('execution_results', [])
    
    if execution_results:
        # Use execution count and total value as key
        exec_count = len(execution_results)
        total_value = sum(getattr(result, 'filled_quantity', 0) * getattr(result, 'average_price', 0) 
                         for result in execution_results if hasattr(result, 'filled_quantity'))
        return f"portfolio_{exec_count}_{total_value:.2f}"
    
    return f"portfolio_default_{time.time()}"

# Specialized optimization decorators
def optimize_signal_generation(func):
    """Optimize signal generation with intelligent caching"""
    return optimize_hot_path(
        cache_key_func=signal_generation_cache_key,
        cache_ttl=30.0,  # 30 second cache for signals
        cache_instance=signal_cache
    )(func)

def optimize_order_execution(func):
    """Optimize order execution with short-term caching"""
    return optimize_hot_path(
        cache_key_func=execution_cache_key,
        cache_ttl=15.0,  # 15 second cache for executions
        cache_instance=execution_cache
    )(func)

def optimize_portfolio_update(func):
    """Optimize portfolio updates with medium-term caching"""
    return optimize_hot_path(
        cache_key_func=portfolio_cache_key,
        cache_ttl=60.0,  # 1 minute cache for portfolio
        cache_instance=portfolio_cache
    )(func)

def optimize_risk_calculation(func):
    """Optimize risk calculations with caching"""
    return optimize_hot_path(
        cache_key_func=lambda *args, **kwargs: f"risk_{hash(str(args))}_{hash(str(kwargs))}",
        cache_ttl=45.0,  # 45 second cache for risk calculations
        cache_instance=signal_cache  # Reuse signal cache for risk
    )(func)

# ================================================================================
# BATCH PROCESSING OPTIMIZATIONS
# ================================================================================

class BatchProcessor:
    """High-performance batch processor for trading operations"""
    
    def __init__(self, batch_size: int = 50, max_workers: int = 4):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def process_signals_batch(self, signals: List[Any], processor_func: Callable) -> List[Any]:
        """Process signals in optimized batches"""
        if not signals:
            return []
        
        # Split into batches
        batches = [signals[i:i + self.batch_size] for i in range(0, len(signals), self.batch_size)]
        
        # Process batches in parallel
        tasks = []
        for batch in batches:
            if asyncio.iscoroutinefunction(processor_func):
                task = asyncio.create_task(processor_func(batch))
            else:
                task = asyncio.get_event_loop().run_in_executor(
                    self.executor, processor_func, batch
                )
            tasks.append(task)
        
        # Wait for all batches to complete
        batch_results = await asyncio.gather(*tasks)
        
        # Flatten results
        results = []
        for batch_result in batch_results:
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)
        
        return results
    
    def shutdown(self):
        """Shutdown the batch processor"""
        self.executor.shutdown(wait=True)

# ================================================================================
# MEMORY-EFFICIENT DATA STRUCTURES
# ================================================================================

class CircularBuffer:
    """Memory-efficient circular buffer for market data"""
    
    def __init__(self, size: int):
        self.size = size
        self.buffer = [None] * size
        self.head = 0
        self.count = 0
        self.lock = threading.RLock()
    
    def append(self, item: Any) -> None:
        """Add item to buffer"""
        with self.lock:
            self.buffer[self.head] = item
            self.head = (self.head + 1) % self.size
            self.count = min(self.count + 1, self.size)
    
    def get_latest(self, n: int = 1) -> List[Any]:
        """Get latest n items"""
        with self.lock:
            if n <= 0 or self.count == 0:
                return []
            
            n = min(n, self.count)
            items = []
            
            for i in range(n):
                idx = (self.head - 1 - i) % self.size
                if self.buffer[idx] is not None:
                    items.append(self.buffer[idx])
            
            return list(reversed(items))
    
    def get_all(self) -> List[Any]:
        """Get all items in chronological order"""
        return self.get_latest(self.count)
    
    def clear(self) -> None:
        """Clear the buffer"""
        with self.lock:
            self.buffer = [None] * self.size
            self.head = 0
            self.count = 0

class FastDataFrame:
    """Memory-efficient alternative to pandas DataFrame for hot paths"""
    
    def __init__(self, data: Dict[str, List[Any]]):
        self.data = data
        self.columns = list(data.keys())
        self.length = len(next(iter(data.values()))) if data else 0
    
    def __getitem__(self, key: str) -> List[Any]:
        """Get column data"""
        return self.data[key]
    
    def get_last(self, column: str) -> Any:
        """Get last value in column"""
        if column in self.data and self.data[column]:
            return self.data[column][-1]
        return None
    
    def get_slice(self, start: int, end: int) -> 'FastDataFrame':
        """Get slice of data"""
        sliced_data = {}
        for col, values in self.data.items():
            sliced_data[col] = values[start:end]
        return FastDataFrame(sliced_data)
    
    def to_pandas(self) -> pd.DataFrame:
        """Convert to pandas DataFrame when needed"""
        return pd.DataFrame(self.data)

# ================================================================================
# PERFORMANCE UTILITIES
# ================================================================================

def get_cache_statistics() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all cache instances"""
    return {
        'signal_cache': signal_cache.get_stats(),
        'execution_cache': execution_cache.get_stats(),
        'portfolio_cache': portfolio_cache.get_stats()
    }

def clear_all_caches() -> None:
    """Clear all performance caches"""
    signal_cache.clear()
    execution_cache.clear()
    portfolio_cache.clear()
    logger.info("All performance caches cleared")

def get_performance_summary() -> Dict[str, Any]:
    """Get comprehensive performance summary"""
    cache_stats = get_cache_statistics()
    perf_metrics = performance_monitor.get_all_metrics()
    
    # Calculate aggregate statistics
    total_calls = sum(m.total_calls for m in perf_metrics.values())
    total_time = sum(m.total_time_ms for m in perf_metrics.values())
    total_cache_hits = sum(stats['hits'] for stats in cache_stats.values())
    total_cache_requests = sum(stats['hits'] + stats['misses'] for stats in cache_stats.values())
    
    return {
        'total_function_calls': total_calls,
        'total_execution_time_ms': total_time,
        'average_execution_time_ms': total_time / total_calls if total_calls > 0 else 0.0,
        'cache_hit_rate': total_cache_hits / total_cache_requests if total_cache_requests > 0 else 0.0,
        'monitored_functions': len(perf_metrics),
        'cache_statistics': cache_stats,
        'top_functions_by_time': sorted(
            [(name, m.total_time_ms) for name, m in perf_metrics.items()],
            key=lambda x: x[1], reverse=True
        )[:5]
    }

# Global batch processor
batch_processor = BatchProcessor()

# Cleanup function
def cleanup_performance_resources():
    """Cleanup performance optimization resources"""
    batch_processor.shutdown()
    clear_all_caches()
    performance_monitor.reset_metrics()
    logger.info("Performance optimization resources cleaned up")
