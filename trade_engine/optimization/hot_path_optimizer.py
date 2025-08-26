"""
Hot Path Optimizer for Trading Cycle
====================================

Ultra-high-performance optimization for the most critical trading cycle paths
in the trade_engine + core_structure architecture.

Author: Pro Quant Desk Trader
"""

import asyncio
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from collections import deque
from functools import wraps
import weakref
import sys
import cProfile
import pstats
from io import StringIO

logger = logging.getLogger(__name__)

@dataclass
class HotPathMetrics:
    """Metrics for hot path execution"""
    path_name: str
    total_executions: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    last_execution_time_ms: float = 0.0
    error_count: int = 0
    optimization_applied: bool = False
    cache_hits: int = 0
    cache_misses: int = 0

@dataclass
class ExecutionContext:
    """Context for hot path execution"""
    execution_id: str
    path_name: str
    start_time: float
    parameters: Dict[str, Any]
    cached_results: Optional[Any] = None
    optimization_flags: Dict[str, bool] = field(default_factory=dict)

class HotPathCache:
    """High-performance cache for hot path results"""
    
    def __init__(self, max_size: int = 10000, ttl_seconds: float = 60.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._access_order: deque = deque()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value with TTL check"""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                
                # Check TTL
                if time.time() - timestamp <= self.ttl_seconds:
                    # Update access order
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    
                    self._hits += 1
                    return value
                else:
                    # Expired
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)
            
            self._misses += 1
            return None
    
    def put(self, key: str, value: Any) -> None:
        """Put value in cache with LRU eviction"""
        with self._lock:
            current_time = time.time()
            
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                if self._access_order:
                    oldest_key = self._access_order.popleft()
                    if oldest_key in self._cache:
                        del self._cache[oldest_key]
            
            # Store value with timestamp
            self._cache[key] = (value, current_time)
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    def clear(self) -> None:
        """Clear all cached values"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'size': len(self._cache),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
            'max_size': self.max_size
        }

class HotPathOptimizer:
    """
    Ultra-high-performance optimizer for critical trading paths.
    
    Features:
    - Execution path caching
    - Pre-compiled execution plans
    - Async batch processing
    - Memory optimization
    - Real-time performance monitoring
    """
    
    def __init__(self):
        self.metrics: Dict[str, HotPathMetrics] = {}
        self.cache = HotPathCache()
        self.compiled_paths: Dict[str, Callable] = {}
        self.optimization_enabled = True
        self.profiling_enabled = False
        self._execution_contexts: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._lock = threading.RLock()
        
        # Pre-allocated objects for hot paths
        self._preallocated_contexts: deque = deque(maxlen=1000)
        self._context_pool_lock = threading.Lock()
        
        logger.info("HotPathOptimizer initialized")
    
    def optimize_path(self, path_name: str):
        """Decorator to optimize a hot path function"""
        def decorator(func: Callable) -> Callable:
            # Register the path
            if path_name not in self.metrics:
                self.metrics[path_name] = HotPathMetrics(path_name=path_name)
            
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    return await self._execute_optimized_async(path_name, func, *args, **kwargs)
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    return self._execute_optimized_sync(path_name, func, *args, **kwargs)
                return sync_wrapper
        
        return decorator
    
    async def _execute_optimized_async(
        self, 
        path_name: str, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """Execute async function with optimizations"""
        context = self._create_execution_context(path_name, args, kwargs)
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(path_name, args, kwargs)
            cached_result = self.cache.get(cache_key)
            
            if cached_result is not None:
                self.metrics[path_name].cache_hits += 1
                return cached_result
            
            self.metrics[path_name].cache_misses += 1
            
            # Execute with optimization
            start_time = time.perf_counter()
            
            if self.profiling_enabled:
                # Profile execution
                profiler = cProfile.Profile()
                profiler.enable()
                
                result = await func(*args, **kwargs)
                
                profiler.disable()
                self._analyze_profile(path_name, profiler)
            else:
                result = await func(*args, **kwargs)
            
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Update metrics
            self._update_metrics(path_name, execution_time_ms, True)
            
            # Cache result if it's cacheable
            if self._is_result_cacheable(result):
                self.cache.put(cache_key, result)
            
            return result
            
        except Exception as e:
            self.metrics[path_name].error_count += 1
            logger.error(f"Error in hot path '{path_name}': {e}")
            raise
        finally:
            self._cleanup_execution_context(context)
    
    def _execute_optimized_sync(
        self, 
        path_name: str, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """Execute sync function with optimizations"""
        context = self._create_execution_context(path_name, args, kwargs)
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(path_name, args, kwargs)
            cached_result = self.cache.get(cache_key)
            
            if cached_result is not None:
                self.metrics[path_name].cache_hits += 1
                return cached_result
            
            self.metrics[path_name].cache_misses += 1
            
            # Execute with optimization
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Update metrics
            self._update_metrics(path_name, execution_time_ms, True)
            
            # Cache result if it's cacheable
            if self._is_result_cacheable(result):
                self.cache.put(cache_key, result)
            
            return result
            
        except Exception as e:
            self.metrics[path_name].error_count += 1
            logger.error(f"Error in hot path '{path_name}': {e}")
            raise
        finally:
            self._cleanup_execution_context(context)
    
    def _create_execution_context(
        self, 
        path_name: str, 
        args: tuple, 
        kwargs: dict
    ) -> ExecutionContext:
        """Create execution context with object pooling"""
        with self._context_pool_lock:
            if self._preallocated_contexts:
                context = self._preallocated_contexts.popleft()
                # Reset context
                context.execution_id = f"{path_name}_{int(time.time() * 1000000)}"
                context.path_name = path_name
                context.start_time = time.perf_counter()
                context.parameters = {'args': args, 'kwargs': kwargs}
                context.cached_results = None
                context.optimization_flags.clear()
            else:
                context = ExecutionContext(
                    execution_id=f"{path_name}_{int(time.time() * 1000000)}",
                    path_name=path_name,
                    start_time=time.perf_counter(),
                    parameters={'args': args, 'kwargs': kwargs}
                )
        
        self._execution_contexts[context.execution_id] = context
        return context
    
    def _cleanup_execution_context(self, context: ExecutionContext):
        """Cleanup execution context and return to pool"""
        try:
            if context.execution_id in self._execution_contexts:
                del self._execution_contexts[context.execution_id]
            
            # Return to pool if there's space
            with self._context_pool_lock:
                if len(self._preallocated_contexts) < 100:  # Limit pool size
                    self._preallocated_contexts.append(context)
        except Exception as e:
            logger.error(f"Error cleaning up execution context: {e}")
    
    def _generate_cache_key(self, path_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key for function arguments"""
        try:
            # Simple hash-based key generation
            # In production, you might want more sophisticated key generation
            key_data = f"{path_name}_{str(args)}_{str(sorted(kwargs.items()))}"
            return str(hash(key_data))
        except Exception:
            # Fallback for unhashable arguments
            return f"{path_name}_{id(args)}_{id(kwargs)}"
    
    def _is_result_cacheable(self, result: Any) -> bool:
        """Check if result should be cached"""
        # Don't cache None, large objects, or exceptions
        if result is None:
            return False
        
        try:
            # Rough size check (you might want more sophisticated sizing)
            if sys.getsizeof(result) > 10000:  # 10KB limit
                return False
            return True
        except Exception:
            return False
    
    def _update_metrics(self, path_name: str, execution_time_ms: float, success: bool):
        """Update execution metrics"""
        with self._lock:
            metrics = self.metrics[path_name]
            
            if success:
                metrics.total_executions += 1
                metrics.total_time_ms += execution_time_ms
                metrics.avg_time_ms = metrics.total_time_ms / metrics.total_executions
                metrics.min_time_ms = min(metrics.min_time_ms, execution_time_ms)
                metrics.max_time_ms = max(metrics.max_time_ms, execution_time_ms)
                metrics.last_execution_time_ms = execution_time_ms
    
    def _analyze_profile(self, path_name: str, profiler: cProfile.Profile):
        """Analyze profiling results"""
        try:
            s = StringIO()
            ps = pstats.Stats(profiler, stream=s)
            ps.sort_stats('cumulative')
            ps.print_stats(10)  # Top 10 functions
            
            profile_output = s.getvalue()
            logger.debug(f"Profile for {path_name}:\n{profile_output}")
            
        except Exception as e:
            logger.error(f"Error analyzing profile for {path_name}: {e}")
    
    async def optimize_batch_execution(
        self, 
        path_name: str, 
        func: Callable,
        batch_data: List[Tuple[tuple, dict]],
        batch_size: int = 100
    ) -> List[Any]:
        """Optimize batch execution of function calls"""
        results = []
        
        # Process in optimized batches
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i:i + batch_size]
            
            # Execute batch in parallel
            tasks = []
            for args, kwargs in batch:
                if asyncio.iscoroutinefunction(func):
                    task = asyncio.create_task(
                        self._execute_optimized_async(path_name, func, *args, **kwargs)
                    )
                else:
                    # For sync functions, run in executor
                    loop = asyncio.get_event_loop()
                    task = loop.run_in_executor(
                        None, 
                        lambda: self._execute_optimized_sync(path_name, func, *args, **kwargs)
                    )
                tasks.append(task)
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
        
        return results
    
    def precompile_path(self, path_name: str, func: Callable) -> None:
        """Pre-compile a hot path for maximum performance"""
        try:
            # This is a placeholder for actual compilation logic
            # In practice, you might use techniques like:
            # - JIT compilation
            # - Bytecode optimization
            # - Function specialization
            
            self.compiled_paths[path_name] = func
            
            if path_name in self.metrics:
                self.metrics[path_name].optimization_applied = True
            
            logger.info(f"Pre-compiled hot path: {path_name}")
            
        except Exception as e:
            logger.error(f"Error pre-compiling path {path_name}: {e}")
    
    def get_path_metrics(self, path_name: str) -> Optional[HotPathMetrics]:
        """Get metrics for a specific path"""
        return self.metrics.get(path_name)
    
    def get_all_metrics(self) -> Dict[str, HotPathMetrics]:
        """Get metrics for all paths"""
        return self.metrics.copy()
    
    def get_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        report = []
        report.append("=" * 80)
        report.append("HOT PATH OPTIMIZER PERFORMANCE REPORT")
        report.append("=" * 80)
        
        # Overall statistics
        total_executions = sum(m.total_executions for m in self.metrics.values())
        total_time_ms = sum(m.total_time_ms for m in self.metrics.values())
        
        report.append(f"Total Executions: {total_executions}")
        report.append(f"Total Time: {total_time_ms:.2f}ms")
        report.append(f"Average Time per Execution: {total_time_ms/total_executions:.2f}ms" if total_executions > 0 else "Average Time per Execution: N/A")
        report.append("")
        
        # Cache statistics
        cache_stats = self.cache.get_stats()
        report.append("CACHE STATISTICS")
        report.append("-" * 40)
        report.append(f"Cache Size: {cache_stats['size']}/{cache_stats['max_size']}")
        report.append(f"Cache Hits: {cache_stats['hits']}")
        report.append(f"Cache Misses: {cache_stats['misses']}")
        report.append(f"Hit Rate: {cache_stats['hit_rate']:.2%}")
        report.append("")
        
        # Per-path metrics
        report.append("PATH PERFORMANCE METRICS")
        report.append("-" * 40)
        
        # Sort paths by total time (highest impact first)
        sorted_paths = sorted(
            self.metrics.items(), 
            key=lambda x: x[1].total_time_ms, 
            reverse=True
        )
        
        for path_name, metrics in sorted_paths:
            cache_hit_rate = metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses) if (metrics.cache_hits + metrics.cache_misses) > 0 else 0.0
            
            report.append(f"📊 {path_name}:")
            report.append(f"  • Executions: {metrics.total_executions}")
            report.append(f"  • Total Time: {metrics.total_time_ms:.2f}ms")
            report.append(f"  • Avg Time: {metrics.avg_time_ms:.2f}ms")
            report.append(f"  • Min/Max Time: {metrics.min_time_ms:.2f}ms / {metrics.max_time_ms:.2f}ms")
            report.append(f"  • Cache Hit Rate: {cache_hit_rate:.2%}")
            report.append(f"  • Errors: {metrics.error_count}")
            report.append(f"  • Optimized: {'✅' if metrics.optimization_applied else '❌'}")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def clear_cache(self):
        """Clear all caches"""
        self.cache.clear()
        logger.info("Hot path cache cleared")
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self._lock:
            for metrics in self.metrics.values():
                metrics.total_executions = 0
                metrics.total_time_ms = 0.0
                metrics.avg_time_ms = 0.0
                metrics.min_time_ms = float('inf')
                metrics.max_time_ms = 0.0
                metrics.error_count = 0
                metrics.cache_hits = 0
                metrics.cache_misses = 0
        
        logger.info("Hot path metrics reset")
    
    def enable_profiling(self):
        """Enable detailed profiling for all hot paths"""
        self.profiling_enabled = True
        logger.info("Hot path profiling enabled")
    
    def disable_profiling(self):
        """Disable detailed profiling"""
        self.profiling_enabled = False
        logger.info("Hot path profiling disabled")

# Global optimizer instance
_global_optimizer: Optional[HotPathOptimizer] = None

def get_hot_path_optimizer() -> HotPathOptimizer:
    """Get the global hot path optimizer"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = HotPathOptimizer()
    return _global_optimizer

def optimize_hot_path(path_name: str):
    """Convenience decorator for optimizing hot paths"""
    return get_hot_path_optimizer().optimize_path(path_name)

# Pre-defined optimized decorators for common trading operations
def optimize_signal_generation(func):
    """Optimize signal generation hot path"""
    return optimize_hot_path("signal_generation")(func)

def optimize_order_execution(func):
    """Optimize order execution hot path"""
    return optimize_hot_path("order_execution")(func)

def optimize_portfolio_update(func):
    """Optimize portfolio update hot path"""
    return optimize_hot_path("portfolio_update")(func)

def optimize_risk_calculation(func):
    """Optimize risk calculation hot path"""
    return optimize_hot_path("risk_calculation")(func)
