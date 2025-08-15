"""
Memory Optimizer
===============

High-performance memory optimization for efficient memory usage patterns,
garbage collection optimization, and memory leak prevention.

Author: Pro Quant Desk Trader
"""

import gc
import sys
import logging
import psutil
import threading
import weakref
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class MemoryOptimizationConfig:
    """Configuration for memory optimization"""
    enable_gc_optimization: bool = True
    enable_object_pooling: bool = True
    enable_memory_monitoring: bool = True
    enable_weak_references: bool = True
    gc_threshold_ratio: float = 0.8  # Trigger GC at 80% memory usage
    max_cache_size_mb: int = 500
    memory_warning_threshold_mb: int = 1000
    enable_memory_profiling: bool = False

@dataclass
class MemoryOptimizationResult:
    """Result of memory optimization"""
    initial_memory_mb: float
    optimized_memory_mb: float
    memory_savings_mb: float
    memory_savings_percent: float
    gc_collections_before: int
    gc_collections_after: int
    optimization_techniques: List[str] = field(default_factory=list)
    memory_metrics: Dict[str, float] = field(default_factory=dict)

class ObjectPool:
    """Thread-safe object pool for reusing expensive objects"""
    
    def __init__(self, factory_func, max_size: int = 100):
        self.factory_func = factory_func
        self.max_size = max_size
        self._pool = []
        self._lock = threading.RLock()
    
    def acquire(self):
        """Acquire an object from the pool"""
        with self._lock:
            if self._pool:
                return self._pool.pop()
            else:
                return self.factory_func()
    
    def release(self, obj):
        """Return an object to the pool"""
        with self._lock:
            if len(self._pool) < self.max_size:
                # Reset object state if needed
                if hasattr(obj, 'reset'):
                    obj.reset()
                self._pool.append(obj)

class MemoryOptimizer:
    """
    High-performance memory optimizer that implements advanced memory
    management techniques for optimal memory usage in the core engine.
    """
    
    def __init__(self, config: Optional[MemoryOptimizationConfig] = None):
        self.config = config or MemoryOptimizationConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Memory monitoring
        self.process = psutil.Process()
        self.initial_memory = self._get_memory_usage()
        
        # Object pools for common objects
        self.object_pools: Dict[str, ObjectPool] = {}
        
        # Weak reference tracking
        if self.config.enable_weak_references:
            self.weak_refs: Set[weakref.ref] = set()
        
        # Memory metrics tracking
        self.memory_metrics = {
            'peak_memory_mb': 0.0,
            'gc_collections': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'objects_pooled': 0
        }
        
        # Setup garbage collection optimization
        if self.config.enable_gc_optimization:
            self._optimize_garbage_collection()
        
        self.logger.info(f"MemoryOptimizer initialized - Initial memory: {self.initial_memory:.2f}MB")
    
    def optimize_core_engine_memory(self, core_engine) -> MemoryOptimizationResult:
        """
        Optimize memory usage across all core engine components
        """
        self.logger.info("Starting core engine memory optimization")
        
        # Capture initial state
        initial_memory = self._get_memory_usage()
        initial_gc_collections = self._get_gc_collections()
        
        optimization_techniques = []
        
        # 1. Optimize data structures
        if self.config.enable_object_pooling:
            self._optimize_data_structures(core_engine)
            optimization_techniques.append("data_structure_optimization")
        
        # 2. Implement object pooling
        self._implement_object_pooling(core_engine)
        optimization_techniques.append("object_pooling")
        
        # 3. Optimize caching strategies
        self._optimize_caching_strategies(core_engine)
        optimization_techniques.append("caching_optimization")
        
        # 4. Implement weak references
        if self.config.enable_weak_references:
            self._implement_weak_references(core_engine)
            optimization_techniques.append("weak_references")
        
        # 5. Optimize garbage collection
        if self.config.enable_gc_optimization:
            self._optimize_component_gc(core_engine)
            optimization_techniques.append("gc_optimization")
        
        # Force garbage collection to measure actual memory usage
        gc.collect()
        
        # Capture final state
        final_memory = self._get_memory_usage()
        final_gc_collections = self._get_gc_collections()
        
        # Calculate results
        memory_savings = initial_memory - final_memory
        memory_savings_percent = (memory_savings / initial_memory) * 100 if initial_memory > 0 else 0
        
        result = MemoryOptimizationResult(
            initial_memory_mb=initial_memory,
            optimized_memory_mb=final_memory,
            memory_savings_mb=memory_savings,
            memory_savings_percent=memory_savings_percent,
            gc_collections_before=initial_gc_collections,
            gc_collections_after=final_gc_collections,
            optimization_techniques=optimization_techniques,
            memory_metrics=self.memory_metrics.copy()
        )
        
        self.logger.info(f"Memory optimization completed: {memory_savings:.2f}MB saved "
                        f"({memory_savings_percent:.1f}% reduction)")
        
        return result
    
    def _optimize_data_structures(self, core_engine):
        """Optimize data structures for memory efficiency"""
        self.logger.info("Optimizing data structures")
        
        # Optimize signal generator data structures
        if hasattr(core_engine, 'signal_generator'):
            self._optimize_signal_generator_memory(core_engine.signal_generator)
        
        # Optimize execution engine data structures
        if hasattr(core_engine, 'execution_engine'):
            self._optimize_execution_engine_memory(core_engine.execution_engine)
        
        # Optimize portfolio manager data structures
        if hasattr(core_engine, 'portfolio_manager'):
            self._optimize_portfolio_manager_memory(core_engine.portfolio_manager)
    
    def _implement_object_pooling(self, core_engine):
        """Implement object pooling for frequently created objects"""
        self.logger.info("Implementing object pooling")
        
        # Create pools for common objects
        self.object_pools['trading_signals'] = ObjectPool(
            lambda: {'symbol': '', 'signal': 0.0, 'confidence': 0.0}, 
            max_size=1000
        )
        
        self.object_pools['execution_results'] = ObjectPool(
            lambda: {'order_id': '', 'status': '', 'filled_qty': 0, 'avg_price': 0.0},
            max_size=500
        )
        
        self.object_pools['risk_metrics'] = ObjectPool(
            lambda: {'var': 0.0, 'expected_shortfall': 0.0, 'max_drawdown': 0.0},
            max_size=200
        )
        
        # Replace object creation with pool usage in components
        self._replace_object_creation_with_pools(core_engine)
    
    def _optimize_caching_strategies(self, core_engine):
        """Optimize caching strategies to reduce memory footprint"""
        self.logger.info("Optimizing caching strategies")
        
        # Implement LRU cache with memory limits
        if hasattr(core_engine, 'data_manager'):
            self._implement_memory_limited_cache(core_engine.data_manager)
        
        # Implement time-based cache expiration
        if hasattr(core_engine, 'signal_generator'):
            self._implement_time_based_cache_expiration(core_engine.signal_generator)
    
    def _implement_weak_references(self, core_engine):
        """Implement weak references to prevent memory leaks"""
        self.logger.info("Implementing weak references")
        
        # Replace strong references with weak references where appropriate
        if hasattr(core_engine, 'active_strategies'):
            self._convert_to_weak_references(core_engine.active_strategies)
    
    def _optimize_component_gc(self, core_engine):
        """Optimize garbage collection for individual components"""
        self.logger.info("Optimizing component garbage collection")
        
        # Add cleanup methods to components
        for component_name in ['signal_generator', 'execution_engine', 'risk_manager', 
                              'portfolio_manager', 'data_manager']:
            if hasattr(core_engine, component_name):
                component = getattr(core_engine, component_name)
                self._add_cleanup_method(component)
    
    def _optimize_signal_generator_memory(self, signal_generator):
        """Optimize signal generator memory usage"""
        # Replace large data structures with memory-efficient alternatives
        if hasattr(signal_generator, 'indicator_cache'):
            # Convert to numpy arrays for better memory efficiency
            original_cache = signal_generator.indicator_cache
            
            def memory_efficient_cache_get(key):
                # Use numpy arrays instead of lists for better memory efficiency
                if key in original_cache:
                    data = original_cache[key]
                    if isinstance(data, list):
                        return np.array(data, dtype=np.float32)
                    return data
                return None
            
            signal_generator.get_cached_indicator = memory_efficient_cache_get
    
    def _optimize_execution_engine_memory(self, execution_engine):
        """Optimize execution engine memory usage"""
        # Implement circular buffer for order history
        if hasattr(execution_engine, 'order_history'):
            max_history = 10000  # Limit order history size
            
            def add_to_limited_history(order):
                if not hasattr(execution_engine, '_limited_order_history'):
                    execution_engine._limited_order_history = []
                
                execution_engine._limited_order_history.append(order)
                if len(execution_engine._limited_order_history) > max_history:
                    execution_engine._limited_order_history.pop(0)
            
            execution_engine.add_order_to_history = add_to_limited_history
    
    def _optimize_portfolio_manager_memory(self, portfolio_manager):
        """Optimize portfolio manager memory usage"""
        # Use memory-efficient data structures for position tracking
        if hasattr(portfolio_manager, 'positions'):
            # Convert position data to more memory-efficient format
            original_update = getattr(portfolio_manager, 'update_position', None)
            
            if original_update:
                def memory_efficient_update(symbol, quantity, price):
                    # Use compact data representation
                    if not hasattr(portfolio_manager, '_compact_positions'):
                        portfolio_manager._compact_positions = {}
                    
                    # Store as tuple instead of dict for memory efficiency
                    portfolio_manager._compact_positions[symbol] = (quantity, price, datetime.now())
                    
                portfolio_manager.update_position = memory_efficient_update
    
    def _implement_memory_limited_cache(self, data_manager):
        """Implement memory-limited cache"""
        cache_size_limit = self.config.max_cache_size_mb * 1024 * 1024  # Convert to bytes
        
        if hasattr(data_manager, 'cache'):
            original_cache = data_manager.cache
            
            def memory_aware_cache_set(key, value):
                # Check memory usage before adding to cache
                current_memory = self._get_memory_usage() * 1024 * 1024  # Convert to bytes
                
                if current_memory < cache_size_limit:
                    original_cache[key] = value
                    self.memory_metrics['cache_hits'] += 1
                else:
                    # Remove oldest entries if memory limit exceeded
                    if len(original_cache) > 100:
                        # Remove 20% of oldest entries
                        keys_to_remove = list(original_cache.keys())[:len(original_cache) // 5]
                        for k in keys_to_remove:
                            del original_cache[k]
                    self.memory_metrics['cache_misses'] += 1
            
            data_manager.cache_set = memory_aware_cache_set
    
    def _implement_time_based_cache_expiration(self, signal_generator):
        """Implement time-based cache expiration"""
        cache_ttl = timedelta(minutes=5)  # 5-minute TTL
        
        if hasattr(signal_generator, 'indicator_cache'):
            # Add timestamp tracking to cache entries
            if not hasattr(signal_generator, '_cache_timestamps'):
                signal_generator._cache_timestamps = {}
            
            original_get = getattr(signal_generator, 'get_cached_indicator', None)
            
            if original_get:
                def time_aware_cache_get(key):
                    now = datetime.now()
                    
                    if key in signal_generator._cache_timestamps:
                        if now - signal_generator._cache_timestamps[key] > cache_ttl:
                            # Expire old cache entry
                            if key in signal_generator.indicator_cache:
                                del signal_generator.indicator_cache[key]
                            del signal_generator._cache_timestamps[key]
                            return None
                    
                    return original_get(key)
                
                signal_generator.get_cached_indicator = time_aware_cache_get
    
    def _convert_to_weak_references(self, strategy_dict):
        """Convert strong references to weak references"""
        if isinstance(strategy_dict, dict):
            # Convert strategy references to weak references
            weak_strategies = {}
            for key, strategy in strategy_dict.items():
                if hasattr(strategy, '__weakref__'):
                    weak_ref = weakref.ref(strategy, self._cleanup_weak_ref)
                    weak_strategies[key] = weak_ref
                    self.weak_refs.add(weak_ref)
                else:
                    weak_strategies[key] = strategy
            
            strategy_dict.clear()
            strategy_dict.update(weak_strategies)
    
    def _add_cleanup_method(self, component):
        """Add cleanup method to component"""
        def cleanup():
            # Clear any large data structures
            for attr_name in dir(component):
                if not attr_name.startswith('_'):
                    attr = getattr(component, attr_name)
                    if isinstance(attr, (list, dict)) and len(attr) > 1000:
                        if isinstance(attr, list):
                            attr.clear()
                        elif isinstance(attr, dict):
                            attr.clear()
        
        component.cleanup_memory = cleanup
    
    def _replace_object_creation_with_pools(self, core_engine):
        """Replace direct object creation with object pool usage"""
        # This would require more specific knowledge of the codebase
        # For now, we'll add a method to access pools
        core_engine._object_pools = self.object_pools
        
        def get_pooled_object(pool_name):
            if pool_name in self.object_pools:
                obj = self.object_pools[pool_name].acquire()
                self.memory_metrics['objects_pooled'] += 1
                return obj
            return None
        
        def return_pooled_object(pool_name, obj):
            if pool_name in self.object_pools:
                self.object_pools[pool_name].release(obj)
        
        core_engine.get_pooled_object = get_pooled_object
        core_engine.return_pooled_object = return_pooled_object
    
    def _optimize_garbage_collection(self):
        """Optimize garbage collection settings"""
        # Adjust GC thresholds for better performance
        gc.set_threshold(700, 10, 10)  # More aggressive collection
        
        # Enable automatic garbage collection
        gc.enable()
        
        self.logger.info("Garbage collection optimized")
    
    def _cleanup_weak_ref(self, weak_ref):
        """Cleanup callback for weak references"""
        self.weak_refs.discard(weak_ref)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert bytes to MB
        except:
            return 0.0
    
    def _get_gc_collections(self) -> int:
        """Get total garbage collections"""
        return sum(gc.get_stats()[i]['collections'] for i in range(len(gc.get_stats())))
    
    def monitor_memory_usage(self):
        """Monitor memory usage and trigger optimization if needed"""
        current_memory = self._get_memory_usage()
        
        if current_memory > self.memory_metrics['peak_memory_mb']:
            self.memory_metrics['peak_memory_mb'] = current_memory
        
        if current_memory > self.config.memory_warning_threshold_mb:
            self.logger.warning(f"High memory usage detected: {current_memory:.2f}MB")
            
            # Trigger aggressive garbage collection
            gc.collect()
            
            # Clear object pools if memory is critically high
            if current_memory > self.config.memory_warning_threshold_mb * 1.5:
                for pool in self.object_pools.values():
                    pool._pool.clear()
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory usage report"""
        current_memory = self._get_memory_usage()
        
        return {
            'current_memory_mb': current_memory,
            'initial_memory_mb': self.initial_memory,
            'memory_increase_mb': current_memory - self.initial_memory,
            'peak_memory_mb': self.memory_metrics['peak_memory_mb'],
            'gc_collections': self._get_gc_collections(),
            'active_weak_refs': len(self.weak_refs),
            'object_pools': {name: len(pool._pool) for name, pool in self.object_pools.items()},
            'cache_metrics': {
                'cache_hits': self.memory_metrics['cache_hits'],
                'cache_misses': self.memory_metrics['cache_misses'],
                'hit_rate': (self.memory_metrics['cache_hits'] / 
                           max(1, self.memory_metrics['cache_hits'] + self.memory_metrics['cache_misses'])) * 100
            }
        }
