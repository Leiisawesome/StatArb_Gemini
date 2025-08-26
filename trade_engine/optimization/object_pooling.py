"""
Object Pooling System for Hot Path Optimization
===============================================

High-performance object pooling to reduce memory allocations and GC pressure
in the trade_engine + core_structure architecture hot paths.

Author: Pro Quant Desk Trader
"""

import threading
import time
import weakref
import logging
from typing import Dict, List, Optional, TypeVar, Generic, Callable, Type, Any
from collections import deque
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import gc

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class PoolStatistics:
    """Statistics for object pool performance"""
    pool_name: str
    total_created: int = 0
    total_acquired: int = 0
    total_returned: int = 0
    total_destroyed: int = 0
    current_size: int = 0
    peak_size: int = 0
    hit_rate: float = 0.0
    avg_acquisition_time_ms: float = 0.0
    memory_saved_mb: float = 0.0

class PoolableObject(ABC):
    """Base class for objects that can be pooled"""
    
    def __init__(self):
        self._pool_ref: Optional[weakref.ref] = None
        self._in_use = False
        self._creation_time = time.time()
        self._usage_count = 0
    
    @abstractmethod
    def reset(self) -> None:
        """Reset object state for reuse"""
        pass
    
    @abstractmethod
    def is_reusable(self) -> bool:
        """Check if object can be reused"""
        return True
    
    def _mark_in_use(self):
        """Mark object as in use"""
        self._in_use = True
        self._usage_count += 1
    
    def _mark_available(self):
        """Mark object as available"""
        self._in_use = False

class ObjectPool(Generic[T]):
    """High-performance object pool with threading support"""
    
    def __init__(
        self,
        pool_name: str,
        factory_func: Callable[[], T],
        reset_func: Optional[Callable[[T], None]] = None,
        max_size: int = 1000,
        min_size: int = 10,
        max_idle_time: float = 300.0,  # 5 minutes
        enable_statistics: bool = True
    ):
        self.pool_name = pool_name
        self.factory_func = factory_func
        self.reset_func = reset_func
        self.max_size = max_size
        self.min_size = min_size
        self.max_idle_time = max_idle_time
        self.enable_statistics = enable_statistics
        
        # Thread-safe pool storage
        self._available_objects: deque[T] = deque()
        self._all_objects: weakref.WeakSet[T] = weakref.WeakSet()
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = PoolStatistics(pool_name=pool_name)
        self._acquisition_times: List[float] = []
        
        # Cleanup thread
        self._cleanup_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Pre-populate pool
        self._populate_initial_objects()
        self._start_cleanup_thread()
        
        logger.info(f"ObjectPool '{pool_name}' initialized with {len(self._available_objects)} objects")
    
    def acquire(self) -> T:
        """Acquire an object from the pool"""
        start_time = time.time()
        
        with self._lock:
            # Try to get from available objects
            if self._available_objects:
                obj = self._available_objects.popleft()
                if self._is_object_valid(obj):
                    self._prepare_object_for_use(obj)
                    self._update_acquisition_stats(start_time, True)
                    return obj
            
            # Create new object if pool is not at max capacity
            if len(self._all_objects) < self.max_size:
                obj = self._create_new_object()
                self._prepare_object_for_use(obj)
                self._update_acquisition_stats(start_time, False)
                return obj
            
            # Pool is full, wait for an object to become available
            # In production, you might want to implement a more sophisticated waiting mechanism
            logger.warning(f"Pool '{self.pool_name}' is at max capacity, creating temporary object")
            obj = self.factory_func()
            self._update_acquisition_stats(start_time, False)
            return obj
    
    def release(self, obj: T) -> None:
        """Release an object back to the pool"""
        if obj is None:
            return
        
        with self._lock:
            # Reset object if reset function is provided
            if self.reset_func:
                try:
                    self.reset_func(obj)
                except Exception as e:
                    logger.error(f"Error resetting object in pool '{self.pool_name}': {e}")
                    self._destroy_object(obj)
                    return
            
            # Check if object is reusable
            if hasattr(obj, 'is_reusable') and not obj.is_reusable():
                self._destroy_object(obj)
                return
            
            # Add back to available objects if pool not full
            if len(self._available_objects) < self.max_size:
                if hasattr(obj, '_mark_available'):
                    obj._mark_available()
                self._available_objects.append(obj)
                self.stats.total_returned += 1
            else:
                self._destroy_object(obj)
    
    def _populate_initial_objects(self):
        """Pre-populate pool with initial objects"""
        for _ in range(self.min_size):
            obj = self._create_new_object()
            self._available_objects.append(obj)
    
    def _create_new_object(self) -> T:
        """Create a new object and track it"""
        obj = self.factory_func()
        self._all_objects.add(obj)
        
        # Set pool reference if object supports it
        if hasattr(obj, '_pool_ref'):
            obj._pool_ref = weakref.ref(self)
        
        self.stats.total_created += 1
        self.stats.current_size = len(self._all_objects)
        self.stats.peak_size = max(self.stats.peak_size, self.stats.current_size)
        
        return obj
    
    def _prepare_object_for_use(self, obj: T):
        """Prepare object for use"""
        if hasattr(obj, '_mark_in_use'):
            obj._mark_in_use()
        self.stats.total_acquired += 1
    
    def _is_object_valid(self, obj: T) -> bool:
        """Check if object is still valid for use"""
        if hasattr(obj, 'is_reusable'):
            return obj.is_reusable()
        return True
    
    def _destroy_object(self, obj: T):
        """Destroy an object and update statistics"""
        try:
            if obj in self._all_objects:
                self._all_objects.remove(obj)
            self.stats.total_destroyed += 1
            self.stats.current_size = len(self._all_objects)
        except Exception as e:
            logger.error(f"Error destroying object in pool '{self.pool_name}': {e}")
    
    def _update_acquisition_stats(self, start_time: float, was_from_pool: bool):
        """Update acquisition statistics"""
        if not self.enable_statistics:
            return
        
        acquisition_time_ms = (time.time() - start_time) * 1000
        self._acquisition_times.append(acquisition_time_ms)
        
        # Keep only last 1000 measurements
        if len(self._acquisition_times) > 1000:
            self._acquisition_times = self._acquisition_times[-1000:]
        
        # Update average
        self.stats.avg_acquisition_time_ms = sum(self._acquisition_times) / len(self._acquisition_times)
        
        # Update hit rate
        if self.stats.total_acquired > 0:
            pool_hits = self.stats.total_acquired - self.stats.total_created
            self.stats.hit_rate = pool_hits / self.stats.total_acquired
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        while not self._shutdown_event.wait(60):  # Run every minute
            try:
                self._cleanup_idle_objects()
            except Exception as e:
                logger.error(f"Error in cleanup loop for pool '{self.pool_name}': {e}")
    
    def _cleanup_idle_objects(self):
        """Clean up idle objects that have exceeded max idle time"""
        current_time = time.time()
        
        with self._lock:
            # Remove objects that have been idle too long
            objects_to_remove = []
            
            for obj in list(self._available_objects):
                if hasattr(obj, '_creation_time'):
                    idle_time = current_time - obj._creation_time
                    if idle_time > self.max_idle_time and len(self._available_objects) > self.min_size:
                        objects_to_remove.append(obj)
            
            for obj in objects_to_remove:
                self._available_objects.remove(obj)
                self._destroy_object(obj)
    
    def get_statistics(self) -> PoolStatistics:
        """Get current pool statistics"""
        with self._lock:
            self.stats.current_size = len(self._all_objects)
            
            # Estimate memory saved (rough calculation)
            if self.stats.total_created > 0:
                avg_object_size_mb = 0.001  # Assume 1KB per object
                objects_reused = self.stats.total_acquired - self.stats.total_created
                self.stats.memory_saved_mb = objects_reused * avg_object_size_mb
            
            return self.stats
    
    def shutdown(self):
        """Shutdown the pool and cleanup resources"""
        self._shutdown_event.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
        
        with self._lock:
            self._available_objects.clear()
            self._all_objects.clear()
        
        logger.info(f"ObjectPool '{self.pool_name}' shutdown complete")

# Concrete poolable objects for trading system

class PoolableSignal(PoolableObject):
    """Poolable trading signal object"""
    
    def __init__(self):
        super().__init__()
        self.symbol: str = ""
        self.signal_type: str = ""
        self.strength: float = 0.0
        self.confidence: float = 0.0
        self.timestamp: float = 0.0
        self.metadata: Dict[str, Any] = {}
    
    def reset(self):
        """Reset signal for reuse"""
        self.symbol = ""
        self.signal_type = ""
        self.strength = 0.0
        self.confidence = 0.0
        self.timestamp = 0.0
        self.metadata.clear()
    
    def is_reusable(self) -> bool:
        """Check if signal can be reused"""
        return self._usage_count < 100  # Limit reuse to prevent memory leaks

class PoolableOrder(PoolableObject):
    """Poolable order object"""
    
    def __init__(self):
        super().__init__()
        self.order_id: str = ""
        self.symbol: str = ""
        self.side: str = ""
        self.quantity: float = 0.0
        self.price: float = 0.0
        self.order_type: str = ""
        self.status: str = ""
        self.timestamp: float = 0.0
        self.execution_results: List[Any] = []
    
    def reset(self):
        """Reset order for reuse"""
        self.order_id = ""
        self.symbol = ""
        self.side = ""
        self.quantity = 0.0
        self.price = 0.0
        self.order_type = ""
        self.status = ""
        self.timestamp = 0.0
        self.execution_results.clear()
    
    def is_reusable(self) -> bool:
        """Check if order can be reused"""
        return self._usage_count < 50  # Limit reuse

class PoolableMarketData(PoolableObject):
    """Poolable market data object"""
    
    def __init__(self):
        super().__init__()
        self.symbol: str = ""
        self.timestamp: float = 0.0
        self.open_price: float = 0.0
        self.high_price: float = 0.0
        self.low_price: float = 0.0
        self.close_price: float = 0.0
        self.volume: float = 0.0
        self.bid: float = 0.0
        self.ask: float = 0.0
        self.additional_data: Dict[str, Any] = {}
    
    def reset(self):
        """Reset market data for reuse"""
        self.symbol = ""
        self.timestamp = 0.0
        self.open_price = 0.0
        self.high_price = 0.0
        self.low_price = 0.0
        self.close_price = 0.0
        self.volume = 0.0
        self.bid = 0.0
        self.ask = 0.0
        self.additional_data.clear()
    
    def is_reusable(self) -> bool:
        """Check if market data can be reused"""
        return True  # Market data is always reusable

class PoolManager:
    """Global manager for all object pools"""
    
    def __init__(self):
        self.pools: Dict[str, ObjectPool] = {}
        self._lock = threading.RLock()
        
        # Initialize default pools
        self._initialize_default_pools()
        
        logger.info("PoolManager initialized")
    
    def _initialize_default_pools(self):
        """Initialize default pools for common objects"""
        # Signal pool
        self.pools['signals'] = ObjectPool(
            pool_name='signals',
            factory_func=PoolableSignal,
            reset_func=lambda obj: obj.reset(),
            max_size=5000,
            min_size=100
        )
        
        # Order pool
        self.pools['orders'] = ObjectPool(
            pool_name='orders',
            factory_func=PoolableOrder,
            reset_func=lambda obj: obj.reset(),
            max_size=2000,
            min_size=50
        )
        
        # Market data pool
        self.pools['market_data'] = ObjectPool(
            pool_name='market_data',
            factory_func=PoolableMarketData,
            reset_func=lambda obj: obj.reset(),
            max_size=10000,
            min_size=200
        )
    
    def get_pool(self, pool_name: str) -> Optional[ObjectPool]:
        """Get pool by name"""
        with self._lock:
            return self.pools.get(pool_name)
    
    def create_pool(
        self,
        pool_name: str,
        factory_func: Callable[[], T],
        reset_func: Optional[Callable[[T], None]] = None,
        max_size: int = 1000,
        min_size: int = 10
    ) -> ObjectPool[T]:
        """Create a new pool"""
        with self._lock:
            if pool_name in self.pools:
                logger.warning(f"Pool '{pool_name}' already exists")
                return self.pools[pool_name]
            
            pool = ObjectPool(
                pool_name=pool_name,
                factory_func=factory_func,
                reset_func=reset_func,
                max_size=max_size,
                min_size=min_size
            )
            
            self.pools[pool_name] = pool
            logger.info(f"Created new pool: {pool_name}")
            return pool
    
    def get_signal(self) -> PoolableSignal:
        """Get a signal object from pool"""
        return self.pools['signals'].acquire()
    
    def release_signal(self, signal: PoolableSignal):
        """Release signal back to pool"""
        self.pools['signals'].release(signal)
    
    def get_order(self) -> PoolableOrder:
        """Get an order object from pool"""
        return self.pools['orders'].acquire()
    
    def release_order(self, order: PoolableOrder):
        """Release order back to pool"""
        self.pools['orders'].release(order)
    
    def get_market_data(self) -> PoolableMarketData:
        """Get a market data object from pool"""
        return self.pools['market_data'].acquire()
    
    def release_market_data(self, market_data: PoolableMarketData):
        """Release market data back to pool"""
        self.pools['market_data'].release(market_data)
    
    def get_all_statistics(self) -> Dict[str, PoolStatistics]:
        """Get statistics for all pools"""
        with self._lock:
            return {
                name: pool.get_statistics()
                for name, pool in self.pools.items()
            }
    
    def shutdown_all_pools(self):
        """Shutdown all pools"""
        with self._lock:
            for pool in self.pools.values():
                pool.shutdown()
            self.pools.clear()
        
        logger.info("All pools shut down")

# Global pool manager instance
_global_pool_manager: Optional[PoolManager] = None

def get_pool_manager() -> PoolManager:
    """Get the global pool manager"""
    global _global_pool_manager
    if _global_pool_manager is None:
        _global_pool_manager = PoolManager()
    return _global_pool_manager

# Convenience functions
def get_signal() -> PoolableSignal:
    """Get a pooled signal object"""
    return get_pool_manager().get_signal()

def release_signal(signal: PoolableSignal):
    """Release signal back to pool"""
    get_pool_manager().release_signal(signal)

def get_order() -> PoolableOrder:
    """Get a pooled order object"""
    return get_pool_manager().get_order()

def release_order(order: PoolableOrder):
    """Release order back to pool"""
    get_pool_manager().release_order(order)

def get_market_data() -> PoolableMarketData:
    """Get a pooled market data object"""
    return get_pool_manager().get_market_data()

def release_market_data(market_data: PoolableMarketData):
    """Release market data back to pool"""
    get_pool_manager().release_market_data(market_data)
