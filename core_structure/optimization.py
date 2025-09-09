#!/usr/bin/env python3
"""
Advanced Performance Optimization - Phase 4 Enhancement
=======================================================

Advanced optimization features enabled by the streamlined architecture.
Provides intelligent caching, parallel processing, memory optimization,
and adaptive performance tuning.

Author: Professional Trading System Architecture - Phase 4 Optimization
Version: 7.0.0 (Advanced Optimization)
"""

import asyncio
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import weakref
import gc
import psutil
import functools

logger = logging.getLogger(__name__)

# ================================================================================
# OPTIMIZATION ENUMS AND TYPES
# ================================================================================

class OptimizationLevel(Enum):
    """Optimization levels"""
    BASIC = "basic"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"

class CacheStrategy(Enum):
    """Cache strategies"""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    ADAPTIVE = "adaptive"

T = TypeVar('T')

# ================================================================================
# INTELLIGENT CACHING SYSTEM
# ================================================================================

@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with metadata"""
    value: T
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds
    
    def touch(self) -> None:
        """Update access metadata"""
        self.last_accessed = datetime.now()
        self.access_count += 1

class IntelligentCache(Generic[T]):
    """
    Intelligent caching system with adaptive strategies
    """
    
    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.strategy = strategy
        self.default_ttl = default_ttl
        
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._access_order = deque()  # For LRU
        self._frequency_counter = defaultdict(int)  # For LFU
        self._lock = threading.RLock()
        
        # Adaptive strategy parameters
        self._hit_rate = 0.0
        self._total_requests = 0
        self._hits = 0
        
        logger.debug(f"Initialized IntelligentCache: max_size={max_size}, strategy={strategy.value}")
    
    def get(self, key: str) -> Optional[T]:
        """Get value from cache"""
        with self._lock:
            self._total_requests += 1
            
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                return None
            
            # Update access metadata
            entry.touch()
            self._hits += 1
            self._hit_rate = self._hits / self._total_requests
            
            # Update strategy-specific data
            if self.strategy == CacheStrategy.LRU:
                self._access_order.remove(key)
                self._access_order.append(key)
            elif self.strategy == CacheStrategy.LFU:
                self._frequency_counter[key] += 1
            
            return entry.value
    
    def put(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """Put value in cache"""
        with self._lock:
            # Use provided TTL or default
            effective_ttl = ttl or self.default_ttl
            
            # Create cache entry
            entry = CacheEntry(
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl_seconds=effective_ttl
            )
            
            # Check if we need to evict
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_one()
            
            # Store entry
            self._cache[key] = entry
            
            # Update strategy-specific data
            if self.strategy == CacheStrategy.LRU:
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
            elif self.strategy == CacheStrategy.LFU:
                self._frequency_counter[key] = 1
    
    def _evict_one(self) -> None:
        """Evict one entry based on strategy"""
        if not self._cache:
            return
        
        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used
            if self._access_order:
                key_to_remove = self._access_order.popleft()
                if key_to_remove in self._cache:
                    del self._cache[key_to_remove]
        
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            if self._frequency_counter:
                key_to_remove = min(self._frequency_counter, key=self._frequency_counter.get)
                del self._cache[key_to_remove]
                del self._frequency_counter[key_to_remove]
        
        elif self.strategy == CacheStrategy.TTL:
            # Remove expired entries first, then oldest
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            if expired_keys:
                key_to_remove = expired_keys[0]
            else:
                key_to_remove = min(self._cache, key=lambda k: self._cache[k].created_at)
            del self._cache[key_to_remove]
        
        elif self.strategy == CacheStrategy.ADAPTIVE:
            # Adaptive strategy based on hit rate
            if self._hit_rate > 0.8:  # High hit rate, use LRU
                if self._access_order:
                    key_to_remove = self._access_order.popleft()
                    if key_to_remove in self._cache:
                        del self._cache[key_to_remove]
            else:  # Low hit rate, use TTL
                expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
                if expired_keys:
                    key_to_remove = expired_keys[0]
                else:
                    key_to_remove = min(self._cache, key=lambda k: self._cache[k].created_at)
                del self._cache[key_to_remove]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._frequency_counter.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': self._hit_rate,
                'total_requests': self._total_requests,
                'hits': self._hits,
                'strategy': self.strategy.value
            }

# ================================================================================
# PERFORMANCE MONITORING
# ================================================================================

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    thread_count: int = 0
    gc_collections: int = 0
    cache_hit_rate: float = 0.0
    average_response_time_ms: float = 0.0
    throughput_per_second: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

class PerformanceMonitor:
    """
    Advanced performance monitoring system
    """
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.monitoring_interval = monitoring_interval
        self._metrics_history: deque = deque(maxlen=1000)
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Response time tracking
        self._response_times: deque = deque(maxlen=100)
        self._request_count = 0
        self._start_time = time.time()
        
        logger.info("Performance monitor initialized")
    
    def start_monitoring(self) -> None:
        """Start performance monitoring"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        
        logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                metrics = self._collect_metrics()
                self._metrics_history.append(metrics)
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        process = psutil.Process()
        
        # CPU and memory
        cpu_usage = process.cpu_percent()
        memory_info = process.memory_info()
        memory_usage_mb = memory_info.rss / 1024 / 1024
        memory_usage_percent = process.memory_percent()
        
        # Thread count
        thread_count = process.num_threads()
        
        # Garbage collection
        gc_collections = sum(gc.get_stats()[i]['collections'] for i in range(len(gc.get_stats())))
        
        # Response time
        avg_response_time = np.mean(self._response_times) if self._response_times else 0.0
        
        # Throughput
        elapsed_time = time.time() - self._start_time
        throughput = self._request_count / elapsed_time if elapsed_time > 0 else 0.0
        
        return PerformanceMetrics(
            cpu_usage=cpu_usage,
            memory_usage_mb=memory_usage_mb,
            memory_usage_percent=memory_usage_percent,
            thread_count=thread_count,
            gc_collections=gc_collections,
            average_response_time_ms=avg_response_time,
            throughput_per_second=throughput
        )
    
    def record_request(self, response_time_ms: float) -> None:
        """Record a request response time"""
        self._response_times.append(response_time_ms)
        self._request_count += 1
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get current performance metrics"""
        if self._metrics_history:
            return self._metrics_history[-1]
        return None
    
    def get_metrics_history(self, minutes: int = 10) -> List[PerformanceMetrics]:
        """Get metrics history for specified minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self._metrics_history if m.timestamp >= cutoff_time]

# ================================================================================
# PARALLEL PROCESSING OPTIMIZATION
# ================================================================================

class ParallelProcessor:
    """
    Advanced parallel processing with adaptive thread/process management
    """
    
    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.STANDARD):
        self.optimization_level = optimization_level
        
        # Determine optimal worker counts
        cpu_count = psutil.cpu_count()
        
        if optimization_level == OptimizationLevel.BASIC:
            self.thread_workers = min(4, cpu_count)
            self.process_workers = 1
        elif optimization_level == OptimizationLevel.STANDARD:
            self.thread_workers = min(8, cpu_count)
            self.process_workers = min(2, cpu_count // 2)
        elif optimization_level == OptimizationLevel.AGGRESSIVE:
            self.thread_workers = min(16, cpu_count * 2)
            self.process_workers = min(4, cpu_count)
        else:  # MAXIMUM
            self.thread_workers = cpu_count * 2
            self.process_workers = cpu_count
        
        # Create thread and process pools
        self._thread_executor = ThreadPoolExecutor(max_workers=self.thread_workers)
        self._process_executor = ProcessPoolExecutor(max_workers=self.process_workers)
        
        logger.info(f"Parallel processor initialized: {self.thread_workers} threads, {self.process_workers} processes")
    
    def process_parallel_io(self, tasks: List[Callable], use_processes: bool = False) -> List[Any]:
        """Process I/O bound tasks in parallel"""
        executor = self._process_executor if use_processes else self._thread_executor
        
        futures = [executor.submit(task) for task in tasks]
        results = []
        
        for future in futures:
            try:
                result = future.result(timeout=30)  # 30 second timeout
                results.append(result)
            except Exception as e:
                logger.error(f"Parallel task failed: {e}")
                results.append(None)
        
        return results
    
    def process_parallel_cpu(self, func: Callable, data_chunks: List[Any]) -> List[Any]:
        """Process CPU-bound tasks in parallel using processes"""
        futures = [self._process_executor.submit(func, chunk) for chunk in data_chunks]
        results = []
        
        for future in futures:
            try:
                result = future.result(timeout=60)  # 60 second timeout for CPU tasks
                results.append(result)
            except Exception as e:
                logger.error(f"Parallel CPU task failed: {e}")
                results.append(None)
        
        return results
    
    def shutdown(self) -> None:
        """Shutdown parallel processors"""
        self._thread_executor.shutdown(wait=True)
        self._process_executor.shutdown(wait=True)
        logger.info("Parallel processors shutdown")

# ================================================================================
# MEMORY OPTIMIZATION
# ================================================================================

class MemoryOptimizer:
    """
    Advanced memory optimization and management
    """
    
    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.STANDARD):
        self.optimization_level = optimization_level
        self._weak_references: Dict[str, weakref.ref] = {}
        self._memory_threshold_mb = 1000  # 1GB threshold
        
        # Configure garbage collection
        if optimization_level in [OptimizationLevel.AGGRESSIVE, OptimizationLevel.MAXIMUM]:
            gc.set_threshold(700, 10, 10)  # More aggressive GC
        
        logger.info(f"Memory optimizer initialized: level={optimization_level.value}")
    
    def optimize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize pandas DataFrame memory usage"""
        if df.empty:
            return df
        
        original_memory = df.memory_usage(deep=True).sum()
        
        # Optimize numeric columns
        for col in df.select_dtypes(include=['int64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='integer')
        
        for col in df.select_dtypes(include=['float64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='float')
        
        # Optimize object columns
        for col in df.select_dtypes(include=['object']).columns:
            if df[col].nunique() / len(df) < 0.5:  # If less than 50% unique values
                df[col] = df[col].astype('category')
        
        optimized_memory = df.memory_usage(deep=True).sum()
        reduction = (original_memory - optimized_memory) / original_memory * 100
        
        logger.debug(f"DataFrame memory optimized: {reduction:.1f}% reduction")
        return df
    
    def create_weak_reference(self, key: str, obj: Any) -> None:
        """Create weak reference to object"""
        self._weak_references[key] = weakref.ref(obj)
    
    def get_weak_reference(self, key: str) -> Optional[Any]:
        """Get object from weak reference"""
        if key in self._weak_references:
            ref = self._weak_references[key]
            obj = ref()
            if obj is None:
                del self._weak_references[key]
            return obj
        return None
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return statistics"""
        before_counts = [len(gc.get_objects())]
        
        collected = []
        for generation in range(3):
            collected.append(gc.collect(generation))
        
        after_counts = [len(gc.get_objects())]
        
        return {
            'objects_before': before_counts[0],
            'objects_after': after_counts[0],
            'objects_collected': sum(collected),
            'generation_0': collected[0],
            'generation_1': collected[1],
            'generation_2': collected[2]
        }
    
    def check_memory_usage(self) -> Dict[str, float]:
        """Check current memory usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    
    def should_optimize_memory(self) -> bool:
        """Check if memory optimization is needed"""
        memory_usage = self.check_memory_usage()
        return memory_usage['rss_mb'] > self._memory_threshold_mb

# ================================================================================
# ADAPTIVE PERFORMANCE TUNING
# ================================================================================

class AdaptivePerformanceTuner:
    """
    Adaptive performance tuning system that adjusts parameters based on system performance
    """
    
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.performance_monitor = performance_monitor
        self._tuning_history: List[Dict[str, Any]] = []
        self._current_config: Dict[str, Any] = {
            'cache_size': 1000,
            'thread_pool_size': 8,
            'batch_size': 100,
            'optimization_level': OptimizationLevel.STANDARD
        }
        
        logger.info("Adaptive performance tuner initialized")
    
    def tune_performance(self) -> Dict[str, Any]:
        """Perform adaptive performance tuning"""
        current_metrics = self.performance_monitor.get_current_metrics()
        if not current_metrics:
            return self._current_config
        
        # Analyze performance and adjust parameters
        adjustments = {}
        
        # CPU-based adjustments
        if current_metrics.cpu_usage > 80:
            # High CPU usage - reduce parallelism
            adjustments['thread_pool_size'] = max(4, self._current_config['thread_pool_size'] - 2)
            adjustments['batch_size'] = max(50, self._current_config['batch_size'] - 25)
        elif current_metrics.cpu_usage < 30:
            # Low CPU usage - increase parallelism
            adjustments['thread_pool_size'] = min(16, self._current_config['thread_pool_size'] + 2)
            adjustments['batch_size'] = min(200, self._current_config['batch_size'] + 25)
        
        # Memory-based adjustments
        if current_metrics.memory_usage_percent > 80:
            # High memory usage - reduce cache size
            adjustments['cache_size'] = max(500, self._current_config['cache_size'] - 200)
        elif current_metrics.memory_usage_percent < 40:
            # Low memory usage - increase cache size
            adjustments['cache_size'] = min(2000, self._current_config['cache_size'] + 200)
        
        # Response time-based adjustments
        if current_metrics.average_response_time_ms > 1000:
            # Slow response times - optimize more aggressively
            adjustments['optimization_level'] = OptimizationLevel.AGGRESSIVE
        elif current_metrics.average_response_time_ms < 100:
            # Fast response times - can reduce optimization overhead
            adjustments['optimization_level'] = OptimizationLevel.STANDARD
        
        # Apply adjustments
        if adjustments:
            self._current_config.update(adjustments)
            self._tuning_history.append({
                'timestamp': datetime.now(),
                'metrics': current_metrics,
                'adjustments': adjustments
            })
            
            logger.info(f"Performance tuning applied: {adjustments}")
        
        return self._current_config
    
    def get_tuning_recommendations(self) -> List[str]:
        """Get performance tuning recommendations"""
        current_metrics = self.performance_monitor.get_current_metrics()
        if not current_metrics:
            return []
        
        recommendations = []
        
        if current_metrics.cpu_usage > 90:
            recommendations.append("Consider reducing concurrent operations or upgrading CPU")
        
        if current_metrics.memory_usage_percent > 90:
            recommendations.append("Consider increasing available memory or optimizing data structures")
        
        if current_metrics.average_response_time_ms > 2000:
            recommendations.append("Consider optimizing algorithms or adding caching")
        
        if current_metrics.cache_hit_rate < 0.5:
            recommendations.append("Consider adjusting cache strategy or increasing cache size")
        
        return recommendations

# ================================================================================
# INTEGRATED OPTIMIZATION MANAGER
# ================================================================================

class OptimizationManager:
    """
    Integrated optimization manager that coordinates all optimization systems
    """
    
    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.STANDARD):
        self.optimization_level = optimization_level
        
        # Initialize optimization components
        self.cache = IntelligentCache(max_size=1000, strategy=CacheStrategy.ADAPTIVE)
        self.performance_monitor = PerformanceMonitor()
        self.parallel_processor = ParallelProcessor(optimization_level)
        self.memory_optimizer = MemoryOptimizer(optimization_level)
        self.adaptive_tuner = AdaptivePerformanceTuner(self.performance_monitor)
        
        # Start monitoring
        self.performance_monitor.start_monitoring()
        
        logger.info(f"Optimization manager initialized: level={optimization_level.value}")
    
    def optimize_system(self) -> Dict[str, Any]:
        """Perform comprehensive system optimization"""
        optimization_start = time.time()
        
        # Adaptive tuning
        tuning_config = self.adaptive_tuner.tune_performance()
        
        # Memory optimization if needed
        gc_stats = None
        if self.memory_optimizer.should_optimize_memory():
            gc_stats = self.memory_optimizer.force_garbage_collection()
        
        # Get current performance metrics
        current_metrics = self.performance_monitor.get_current_metrics()
        cache_stats = self.cache.get_stats()
        
        optimization_time = (time.time() - optimization_start) * 1000
        
        return {
            'optimization_time_ms': optimization_time,
            'tuning_config': tuning_config,
            'performance_metrics': current_metrics,
            'cache_stats': cache_stats,
            'gc_stats': gc_stats,
            'recommendations': self.adaptive_tuner.get_tuning_recommendations()
        }
    
    def shutdown(self) -> None:
        """Shutdown optimization manager"""
        self.performance_monitor.stop_monitoring()
        self.parallel_processor.shutdown()
        logger.info("Optimization manager shutdown")

# ================================================================================
# DECORATORS FOR AUTOMATIC OPTIMIZATION
# ================================================================================

def cached(cache: IntelligentCache, ttl: Optional[float] = None):
    """Decorator for automatic caching"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.put(key, result, ttl)
            return result
        
        return wrapper
    return decorator

def performance_monitored(monitor: PerformanceMonitor):
    """Decorator for automatic performance monitoring"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                response_time = (time.time() - start_time) * 1000
                monitor.record_request(response_time)
        
        return wrapper
    return decorator

# ================================================================================
# EXPORTS
# ================================================================================

__all__ = [
    # Core Classes
    'OptimizationManager',
    'IntelligentCache',
    'PerformanceMonitor',
    'ParallelProcessor',
    'MemoryOptimizer',
    'AdaptivePerformanceTuner',
    
    # Data Structures
    'PerformanceMetrics',
    'CacheEntry',
    
    # Enums
    'OptimizationLevel',
    'CacheStrategy',
    
    # Decorators
    'cached',
    'performance_monitored',
]
