"""
Memory Management and Object Pooling - Phase 2 Batch 2
======================================================

Enterprise-grade memory management system for high-frequency trading.
Eliminates garbage collection overhead through intelligent object pooling.

Features:
- Thread-safe object pools for trading objects
- Memory-efficient data structures
- Garbage collection optimization
- Memory usage monitoring and alerts
- Automatic pool sizing and management

Author: Professional Trading System Architecture
Version: 2.0 (Memory Optimized)
"""

import threading
import time
import logging
from typing import Dict, Any, Optional, List, Type, TypeVar, Generic, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from abc import ABC, abstractmethod
import weakref
import gc
import psutil
import os

logger = logging.getLogger(__name__)

T = TypeVar('T')

# ================================================================================
# OBJECT POOL STATISTICS AND MONITORING
# ================================================================================

@dataclass
class PoolStatistics:
    """Statistics for object pool performance"""
    pool_name: str
    current_size: int = 0
    peak_size: int = 0
    total_created: int = 0
    total_acquired: int = 0
    total_released: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage_bytes: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_efficiency_rate(self) -> float:
        """Get pool efficiency (reuse rate)"""
        if self.total_acquired == 0:
            return 0.0
        return (self.total_acquired - self.total_created) / self.total_acquired
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate"""
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / total_requests if total_requests > 0 else 0.0

class MemoryMonitor:
    """System memory monitoring for trading applications"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        baseline_info = self.get_current_memory_usage()
        self.baseline_memory = baseline_info['rss_mb']
        self.peak_memory = self.baseline_memory
        self.gc_collections = 0
        self.last_gc_time = time.time()
        
    def get_current_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics"""
        memory_info = self.process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': self.process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get comprehensive memory summary"""
        current = self.get_current_memory_usage()
        self.peak_memory = max(self.peak_memory, current['rss_mb'])
        
        return {
            'current_memory_mb': current['rss_mb'],
            'peak_memory_mb': self.peak_memory,
            'baseline_memory_mb': self.baseline_memory,
            'memory_growth_mb': current['rss_mb'] - self.baseline_memory,
            'memory_percent': current['percent'],
            'available_memory_mb': current['available_mb'],
            'gc_collections': gc.get_count(),
            'gc_collections_delta': sum(gc.get_count()) - self.gc_collections
        }
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return statistics"""
        before_count = sum(gc.get_count())
        before_memory = self.get_current_memory_usage()['rss_mb']
        
        collected = gc.collect()
        
        after_memory = self.get_current_memory_usage()['rss_mb']
        after_count = sum(gc.get_count())
        
        self.gc_collections = after_count
        self.last_gc_time = time.time()
        
        return {
            'objects_collected': collected,
            'memory_freed_mb': before_memory - after_memory,
            'gc_count_before': before_count,
            'gc_count_after': after_count
        }

# Global memory monitor
memory_monitor = MemoryMonitor()

# ================================================================================
# GENERIC OBJECT POOL
# ================================================================================

class ObjectPool(Generic[T]):
    """
    Thread-safe generic object pool for high-performance object reuse.
    
    Features:
    - Thread-safe operations with minimal locking
    - Automatic pool sizing based on usage patterns
    - Memory usage tracking and optimization
    - Configurable object validation and cleanup
    """
    
    def __init__(
        self,
        factory: Callable[[], T],
        reset_func: Optional[Callable[[T], None]] = None,
        validate_func: Optional[Callable[[T], bool]] = None,
        initial_size: int = 10,
        max_size: int = 100,
        auto_resize: bool = True,
        name: str = "ObjectPool"
    ):
        """
        Initialize object pool.
        
        Args:
            factory: Function to create new objects
            reset_func: Function to reset objects before reuse
            validate_func: Function to validate objects before reuse
            initial_size: Initial pool size
            max_size: Maximum pool size
            auto_resize: Enable automatic pool resizing
            name: Pool name for monitoring
        """
        self.factory = factory
        self.reset_func = reset_func
        self.validate_func = validate_func
        self.max_size = max_size
        self.auto_resize = auto_resize
        self.name = name
        
        # Thread-safe pool storage
        self._pool: deque = deque()
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = PoolStatistics(pool_name=name)
        
        # Pre-populate pool
        self._populate_pool(initial_size)
        
        logger.info(f"ObjectPool '{name}' initialized with {initial_size} objects")
    
    def _populate_pool(self, count: int) -> None:
        """Pre-populate pool with objects"""
        with self._lock:
            for _ in range(count):
                try:
                    obj = self.factory()
                    self._pool.append(obj)
                    self.stats.total_created += 1
                    self.stats.current_size += 1
                except Exception as e:
                    logger.error(f"Failed to create object for pool '{self.name}': {e}")
                    break
            
            self.stats.peak_size = max(self.stats.peak_size, self.stats.current_size)
    
    def acquire(self) -> T:
        """
        Acquire an object from the pool.
        Creates new object if pool is empty and within limits.
        """
        with self._lock:
            self.stats.total_acquired += 1
            
            # Try to get from pool first
            if self._pool:
                obj = self._pool.popleft()
                self.stats.current_size -= 1
                self.stats.cache_hits += 1
                
                # Validate object if validator provided
                if self.validate_func and not self.validate_func(obj):
                    # Object invalid, create new one
                    obj = self._create_new_object()
                
                # Reset object if reset function provided
                if self.reset_func:
                    try:
                        self.reset_func(obj)
                    except Exception as e:
                        logger.warning(f"Failed to reset object in pool '{self.name}': {e}")
                        obj = self._create_new_object()
                
                return obj
            
            # Pool empty, create new object
            self.stats.cache_misses += 1
            return self._create_new_object()
    
    def _create_new_object(self) -> T:
        """Create a new object using the factory"""
        try:
            obj = self.factory()
            self.stats.total_created += 1
            return obj
        except Exception as e:
            logger.error(f"Failed to create new object for pool '{self.name}': {e}")
            raise
    
    def release(self, obj: T) -> None:
        """
        Release an object back to the pool.
        Object is added to pool if within size limits.
        """
        if obj is None:
            return
        
        with self._lock:
            self.stats.total_released += 1
            
            # Add to pool if not at capacity
            if self.stats.current_size < self.max_size:
                # Validate object before adding to pool
                if self.validate_func and not self.validate_func(obj):
                    logger.debug(f"Object failed validation, not returned to pool '{self.name}'")
                    return
                
                self._pool.append(obj)
                self.stats.current_size += 1
                self.stats.peak_size = max(self.stats.peak_size, self.stats.current_size)
            
            # Auto-resize if enabled and usage patterns suggest it
            if self.auto_resize and self.stats.total_acquired > 100:
                self._auto_resize_pool()
    
    def _auto_resize_pool(self) -> None:
        """Automatically resize pool based on usage patterns"""
        efficiency = self.stats.get_efficiency_rate()
        
        # If efficiency is high and we're often empty, increase size
        if efficiency > 0.8 and self.stats.current_size == 0:
            new_size = min(self.max_size, int(self.stats.peak_size * 1.2))
            if new_size > self.stats.current_size:
                self._populate_pool(new_size - self.stats.current_size)
                logger.debug(f"Auto-resized pool '{self.name}' to {new_size} objects")
    
    def clear(self) -> None:
        """Clear all objects from the pool"""
        with self._lock:
            self._pool.clear()
            self.stats.current_size = 0
            logger.info(f"Cleared pool '{self.name}'")
    
    def get_statistics(self) -> PoolStatistics:
        """Get current pool statistics"""
        with self._lock:
            self.stats.last_updated = datetime.now()
            return self.stats
    
    def resize(self, new_max_size: int) -> None:
        """Resize the pool maximum size"""
        with self._lock:
            old_max = self.max_size
            self.max_size = new_max_size
            
            # Trim pool if new size is smaller
            while self.stats.current_size > new_max_size and self._pool:
                self._pool.popleft()
                self.stats.current_size -= 1
            
            logger.info(f"Resized pool '{self.name}' from {old_max} to {new_max_size}")

# ================================================================================
# TRADING-SPECIFIC OBJECT POOLS
# ================================================================================

# Trading Signal Pool Objects
@dataclass
class PooledTradingSignal:
    """Memory-efficient trading signal for object pooling"""
    symbol: str = ""
    signal_type: str = ""
    strength: float = 0.0
    confidence: float = 0.0
    timestamp: float = 0.0
    position_size: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def reset(self) -> None:
        """Reset signal for reuse"""
        self.symbol = ""
        self.signal_type = ""
        self.strength = 0.0
        self.confidence = 0.0
        self.timestamp = 0.0
        self.position_size = 0.0
        self.metadata.clear()
    
    def populate(self, symbol: str, signal_type: str, strength: float, 
                confidence: float, position_size: float = 0.0, **kwargs) -> None:
        """Populate signal with data"""
        self.symbol = symbol
        self.signal_type = signal_type
        self.strength = strength
        self.confidence = confidence
        self.timestamp = time.time()
        self.position_size = position_size
        self.metadata.update(kwargs)

# Order Pool Objects
@dataclass
class PooledOrder:
    """Memory-efficient order object for pooling"""
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    quantity: float = 0.0
    price: float = 0.0
    order_type: str = ""
    status: str = ""
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def reset(self) -> None:
        """Reset order for reuse"""
        self.order_id = ""
        self.symbol = ""
        self.side = ""
        self.quantity = 0.0
        self.price = 0.0
        self.order_type = ""
        self.status = ""
        self.timestamp = 0.0
        self.metadata.clear()
    
    def populate(self, order_id: str, symbol: str, side: str, quantity: float,
                price: float = 0.0, order_type: str = "MARKET", **kwargs) -> None:
        """Populate order with data"""
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.order_type = order_type
        self.status = "PENDING"
        self.timestamp = time.time()
        self.metadata.update(kwargs)

# Market Data Pool Objects
@dataclass
class PooledMarketData:
    """Memory-efficient market data object for pooling"""
    symbol: str = ""
    timestamp: float = 0.0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    close_price: float = 0.0
    volume: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def reset(self) -> None:
        """Reset market data for reuse"""
        self.symbol = ""
        self.timestamp = 0.0
        self.open_price = 0.0
        self.high_price = 0.0
        self.low_price = 0.0
        self.close_price = 0.0
        self.volume = 0.0
        self.metadata.clear()
    
    def populate(self, symbol: str, ohlcv: List[float], timestamp: float = None, **kwargs) -> None:
        """Populate with OHLCV data"""
        self.symbol = symbol
        self.timestamp = timestamp or time.time()
        if len(ohlcv) >= 5:
            self.open_price, self.high_price, self.low_price, self.close_price, self.volume = ohlcv[:5]
        self.metadata.update(kwargs)

# ================================================================================
# POOL MANAGER AND FACTORY
# ================================================================================

class PoolManager:
    """
    Central manager for all object pools in the trading system.
    Provides unified access and monitoring for all pools.
    """
    
    def __init__(self):
        self.pools: Dict[str, ObjectPool] = {}
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize standard trading pools
        self._initialize_standard_pools()
        
        self.logger.info("PoolManager initialized with standard trading pools")
    
    def _initialize_standard_pools(self) -> None:
        """Initialize standard object pools for trading operations"""
        
        # Trading Signal Pool
        self.pools['trading_signals'] = ObjectPool(
            factory=lambda: PooledTradingSignal(),
            reset_func=lambda obj: obj.reset(),
            validate_func=lambda obj: hasattr(obj, 'reset'),
            initial_size=50,
            max_size=200,
            name="TradingSignals"
        )
        
        # Order Pool
        self.pools['orders'] = ObjectPool(
            factory=lambda: PooledOrder(),
            reset_func=lambda obj: obj.reset(),
            validate_func=lambda obj: hasattr(obj, 'reset'),
            initial_size=30,
            max_size=150,
            name="Orders"
        )
        
        # Market Data Pool
        self.pools['market_data'] = ObjectPool(
            factory=lambda: PooledMarketData(),
            reset_func=lambda obj: obj.reset(),
            validate_func=lambda obj: hasattr(obj, 'reset'),
            initial_size=100,
            max_size=500,
            name="MarketData"
        )
        
        # Generic Dictionary Pool (for metadata, configs, etc.)
        self.pools['dictionaries'] = ObjectPool(
            factory=lambda: {},
            reset_func=lambda obj: obj.clear(),
            validate_func=lambda obj: isinstance(obj, dict),
            initial_size=20,
            max_size=100,
            name="Dictionaries"
        )
        
        # List Pool (for collections)
        self.pools['lists'] = ObjectPool(
            factory=lambda: [],
            reset_func=lambda obj: obj.clear(),
            validate_func=lambda obj: isinstance(obj, list),
            initial_size=20,
            max_size=100,
            name="Lists"
        )
    
    def get_pool(self, pool_name: str) -> Optional[ObjectPool]:
        """Get a specific object pool by name"""
        with self.lock:
            return self.pools.get(pool_name)
    
    def register_pool(self, name: str, pool: ObjectPool) -> None:
        """Register a new object pool"""
        with self.lock:
            self.pools[name] = pool
            self.logger.info(f"Registered new pool: {name}")
    
    def get_all_statistics(self) -> Dict[str, PoolStatistics]:
        """Get statistics for all pools"""
        with self.lock:
            return {name: pool.get_statistics() for name, pool in self.pools.items()}
    
    def clear_all_pools(self) -> None:
        """Clear all object pools"""
        with self.lock:
            for pool in self.pools.values():
                pool.clear()
            self.logger.info("Cleared all object pools")
    
    def shutdown_all_pools(self) -> None:
        """Shutdown all pools and cleanup resources"""
        with self.lock:
            self.clear_all_pools()
            self.pools.clear()
            self.logger.info("Shutdown all object pools")
    
    def get_memory_report(self) -> str:
        """Generate comprehensive memory and pool report"""
        memory_summary = memory_monitor.get_memory_summary()
        pool_stats = self.get_all_statistics()
        
        report = []
        report.append("=" * 80)
        report.append("MEMORY MANAGEMENT REPORT")
        report.append("=" * 80)
        
        # Memory Overview
        report.append("SYSTEM MEMORY")
        report.append("-" * 40)
        report.append(f"Current Memory: {memory_summary['current_memory_mb']:.1f} MB")
        report.append(f"Peak Memory: {memory_summary['peak_memory_mb']:.1f} MB")
        report.append(f"Memory Growth: {memory_summary['memory_growth_mb']:.1f} MB")
        report.append(f"Memory Usage: {memory_summary['memory_percent']:.1f}%")
        report.append(f"Available Memory: {memory_summary['available_memory_mb']:.1f} MB")
        report.append(f"GC Collections: {memory_summary['gc_collections']}")
        report.append("")
        
        # Pool Statistics
        report.append("OBJECT POOL STATISTICS")
        report.append("-" * 40)
        
        total_objects = 0
        total_created = 0
        total_acquired = 0
        
        for pool_name, stats in pool_stats.items():
            efficiency = stats.get_efficiency_rate()
            hit_rate = stats.get_hit_rate()
            
            report.append(f"📦 {pool_name}:")
            report.append(f"  • Current Size: {stats.current_size}")
            report.append(f"  • Peak Size: {stats.peak_size}")
            report.append(f"  • Total Created: {stats.total_created}")
            report.append(f"  • Total Acquired: {stats.total_acquired}")
            report.append(f"  • Efficiency: {efficiency:.1%}")
            report.append(f"  • Hit Rate: {hit_rate:.1%}")
            report.append("")
            
            total_objects += stats.current_size
            total_created += stats.total_created
            total_acquired += stats.total_acquired
        
        # Summary
        overall_efficiency = (total_acquired - total_created) / total_acquired if total_acquired > 0 else 0.0
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Pooled Objects: {total_objects}")
        report.append(f"Total Objects Created: {total_created}")
        report.append(f"Total Objects Acquired: {total_acquired}")
        report.append(f"Overall Pool Efficiency: {overall_efficiency:.1%}")
        report.append("")
        
        report.append("=" * 80)
        return "\n".join(report)
    
    def optimize_pools(self) -> Dict[str, Any]:
        """Optimize all pools and return optimization results"""
        results = {}
        
        with self.lock:
            # Force garbage collection before optimization
            gc_results = memory_monitor.force_garbage_collection()
            results['garbage_collection'] = gc_results
            
            # Optimize each pool
            pool_optimizations = {}
            for name, pool in self.pools.items():
                stats_before = pool.get_statistics()
                
                # Auto-resize based on usage patterns
                if hasattr(pool, '_auto_resize_pool'):
                    pool._auto_resize_pool()
                
                stats_after = pool.get_statistics()
                
                pool_optimizations[name] = {
                    'size_before': stats_before.current_size,
                    'size_after': stats_after.current_size,
                    'efficiency': stats_after.get_efficiency_rate(),
                    'hit_rate': stats_after.get_hit_rate()
                }
            
            results['pool_optimizations'] = pool_optimizations
            
            self.logger.info("Pool optimization completed")
            return results

# Global pool manager instance
pool_manager = PoolManager()

# ================================================================================
# CONVENIENCE FUNCTIONS FOR OBJECT ACQUISITION
# ================================================================================

def get_trading_signal() -> PooledTradingSignal:
    """Get a trading signal object from the pool"""
    return pool_manager.get_pool('trading_signals').acquire()

def release_trading_signal(signal: PooledTradingSignal) -> None:
    """Release a trading signal back to the pool"""
    pool_manager.get_pool('trading_signals').release(signal)

def get_order() -> PooledOrder:
    """Get an order object from the pool"""
    return pool_manager.get_pool('orders').acquire()

def release_order(order: PooledOrder) -> None:
    """Release an order back to the pool"""
    pool_manager.get_pool('orders').release(order)

def get_market_data() -> PooledMarketData:
    """Get a market data object from the pool"""
    return pool_manager.get_pool('market_data').acquire()

def release_market_data(data: PooledMarketData) -> None:
    """Release market data back to the pool"""
    pool_manager.get_pool('market_data').release(data)

def get_dictionary() -> Dict[str, Any]:
    """Get a dictionary from the pool"""
    return pool_manager.get_pool('dictionaries').acquire()

def release_dictionary(dictionary: Dict[str, Any]) -> None:
    """Release a dictionary back to the pool"""
    pool_manager.get_pool('dictionaries').release(dictionary)

def get_list() -> List[Any]:
    """Get a list from the pool"""
    return pool_manager.get_pool('lists').acquire()

def release_list(lst: List[Any]) -> None:
    """Release a list back to the pool"""
    pool_manager.get_pool('lists').release(lst)

# ================================================================================
# MEMORY OPTIMIZATION UTILITIES
# ================================================================================

class MemoryOptimizer:
    """Advanced memory optimization utilities for trading systems"""
    
    @staticmethod
    def optimize_garbage_collection() -> Dict[str, Any]:
        """Optimize garbage collection settings for trading workloads"""
        # Get current GC thresholds
        original_thresholds = gc.get_threshold()
        
        # Set more aggressive thresholds for trading (lower latency)
        # Reduce gen0 threshold to collect more frequently but with smaller pauses
        new_thresholds = (500, 8, 8)  # More frequent, smaller collections
        gc.set_threshold(*new_thresholds)
        
        # Force a full collection
        collected = gc.collect()
        
        return {
            'original_thresholds': original_thresholds,
            'new_thresholds': new_thresholds,
            'objects_collected': collected,
            'optimization_applied': True
        }
    
    @staticmethod
    def get_object_references(obj: Any) -> Dict[str, int]:
        """Get reference count information for debugging memory leaks"""
        import sys
        
        return {
            'reference_count': sys.getrefcount(obj),
            'object_id': id(obj),
            'object_type': type(obj).__name__,
            'object_size': sys.getsizeof(obj)
        }
    
    @staticmethod
    def find_memory_leaks() -> List[Dict[str, Any]]:
        """Identify potential memory leaks in the system"""
        # Get all objects in memory
        all_objects = gc.get_objects()
        
        # Count objects by type
        type_counts = {}
        for obj in all_objects:
            obj_type = type(obj).__name__
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        # Find types with unusually high counts (potential leaks)
        suspicious_types = []
        for obj_type, count in type_counts.items():
            if count > 1000:  # Threshold for suspicious object count
                suspicious_types.append({
                    'type': obj_type,
                    'count': count,
                    'potential_leak': count > 5000
                })
        
        return sorted(suspicious_types, key=lambda x: x['count'], reverse=True)

# Global memory optimizer
memory_optimizer = MemoryOptimizer()

# ================================================================================
# CONTEXT MANAGERS FOR AUTOMATIC RESOURCE MANAGEMENT
# ================================================================================

class PooledObjectContext:
    """Context manager for automatic pool object management"""
    
    def __init__(self, pool_name: str, pool_manager_instance: PoolManager = None):
        self.pool_name = pool_name
        self.pool_manager = pool_manager_instance or pool_manager
        self.obj = None
    
    def __enter__(self):
        pool = self.pool_manager.get_pool(self.pool_name)
        if pool:
            self.obj = pool.acquire()
            return self.obj
        raise RuntimeError(f"Pool '{self.pool_name}' not found")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.obj is not None:
            pool = self.pool_manager.get_pool(self.pool_name)
            if pool:
                pool.release(self.obj)

# Convenience context managers
def pooled_signal():
    """Context manager for pooled trading signal"""
    return PooledObjectContext('trading_signals')

def pooled_order():
    """Context manager for pooled order"""
    return PooledObjectContext('orders')

def pooled_market_data():
    """Context manager for pooled market data"""
    return PooledObjectContext('market_data')

# ================================================================================
# CLEANUP AND SHUTDOWN
# ================================================================================

def cleanup_memory_resources():
    """Cleanup all memory management resources"""
    pool_manager.shutdown_all_pools()
    
    # Force final garbage collection
    memory_optimizer.optimize_garbage_collection()
    
    logger.info("Memory management resources cleaned up")
