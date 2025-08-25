#!/usr/bin/env python3
"""
Optimized Cache Manager
======================

High-performance caching system optimized for trading system components.
Provides intelligent caching strategies, automatic cache warming, and
performance-optimized data structures.

Author: StatArb_Gemini Team
"""

import asyncio
import logging
import time
import weakref
from typing import Dict, Any, Optional, Callable, Union, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
import hashlib
import pickle
import json
from functools import wraps
import gc

logger = logging.getLogger(__name__)

@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_gets: int = 0
    total_sets: int = 0
    avg_get_time_ms: float = 0.0
    avg_set_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cache_size: int = 0

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds
    
    def touch(self):
        """Update last accessed time"""
        self.last_accessed = datetime.now()
        self.access_count += 1

class OptimizedCacheManager:
    """
    High-performance cache manager with multiple eviction strategies.
    
    Features:
    - LRU, LFU, and TTL-based eviction
    - Automatic cache warming
    - Performance monitoring
    - Memory usage optimization
    - Thread-safe operations
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: Optional[float] = None,
        eviction_strategy: str = 'lru',  # 'lru', 'lfu', 'ttl'
        enable_metrics: bool = True,
        cleanup_interval: float = 60.0
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.eviction_strategy = eviction_strategy
        self.enable_metrics = enable_metrics
        self.cleanup_interval = cleanup_interval
        
        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: OrderedDict = OrderedDict()  # For LRU
        self._lock = threading.RLock()
        
        # Metrics
        self.metrics = CacheMetrics()
        self._timing_data: List[float] = []
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._should_cleanup = True
        
        logger.info(f"OptimizedCacheManager initialized (strategy: {eviction_strategy}, max_size: {max_size})")
    
    async def start_cache_manager(self):
        """Start the cache manager and cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Cache manager started")
    
    async def stop_cache_manager(self):
        """Stop the cache manager"""
        self._should_cleanup = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache manager stopped")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        start_time = time.perf_counter()
        
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                # Check if expired
                if entry.is_expired():
                    del self._cache[key]
                    if key in self._access_order:
                        del self._access_order[key]
                    
                    if self.enable_metrics:
                        self.metrics.misses += 1
                        self.metrics.evictions += 1
                    
                    return default
                
                # Update access info
                entry.touch()
                
                # Update LRU order
                if self.eviction_strategy == 'lru':
                    self._access_order.move_to_end(key)
                
                if self.enable_metrics:
                    self.metrics.hits += 1
                    self._record_timing('get', start_time)
                
                return entry.value
            else:
                if self.enable_metrics:
                    self.metrics.misses += 1
                
                return default
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache"""
        start_time = time.perf_counter()
        
        # Calculate size
        size_bytes = self._calculate_size(value)
        
        with self._lock:
            # Create entry
            entry = CacheEntry(
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl_seconds=ttl or self.default_ttl,
                size_bytes=size_bytes
            )
            
            # If key exists, remove from access order
            if key in self._cache:
                if key in self._access_order:
                    del self._access_order[key]
            
            # Add to cache
            self._cache[key] = entry
            self._access_order[key] = True
            
            # Check if we need to evict
            if len(self._cache) > self.max_size:
                self._evict_entries()
            
            if self.enable_metrics:
                self.metrics.total_sets += 1
                self._record_timing('set', start_time)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    del self._access_order[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            
            if self.enable_metrics:
                self.metrics.evictions += self.metrics.cache_size
                self.metrics.cache_size = 0
    
    def _evict_entries(self):
        """Evict entries based on strategy"""
        target_size = int(self.max_size * 0.8)  # Evict to 80% capacity
        
        if self.eviction_strategy == 'lru':
            self._evict_lru(target_size)
        elif self.eviction_strategy == 'lfu':
            self._evict_lfu(target_size)
        elif self.eviction_strategy == 'ttl':
            self._evict_expired()
            if len(self._cache) > target_size:
                self._evict_lru(target_size)  # Fallback to LRU
    
    def _evict_lru(self, target_size: int):
        """Evict least recently used entries"""
        while len(self._cache) > target_size and self._access_order:
            oldest_key = next(iter(self._access_order))
            del self._cache[oldest_key]
            del self._access_order[oldest_key]
            
            if self.enable_metrics:
                self.metrics.evictions += 1
    
    def _evict_lfu(self, target_size: int):
        """Evict least frequently used entries"""
        # Sort by access count
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].access_count
        )
        
        evict_count = len(self._cache) - target_size
        for i in range(evict_count):
            key, _ = sorted_entries[i]
            del self._cache[key]
            if key in self._access_order:
                del self._access_order[key]
            
            if self.enable_metrics:
                self.metrics.evictions += 1
    
    def _evict_expired(self):
        """Evict expired entries"""
        expired_keys = []
        
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            if key in self._access_order:
                del self._access_order[key]
            
            if self.enable_metrics:
                self.metrics.evictions += 1
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, tuple)):
                return sum(self._calculate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(self._calculate_size(k) + self._calculate_size(v) 
                          for k, v in value.items())
            else:
                # Fallback to pickle size
                return len(pickle.dumps(value))
        except:
            return 100  # Default estimate
    
    def _record_timing(self, operation: str, start_time: float):
        """Record operation timing"""
        duration_ms = (time.perf_counter() - start_time) * 1000
        self._timing_data.append(duration_ms)
        
        # Keep only recent timings
        if len(self._timing_data) > 1000:
            self._timing_data = self._timing_data[-1000:]
        
        # Update metrics
        if self._timing_data:
            if operation == 'get':
                self.metrics.avg_get_time_ms = sum(self._timing_data) / len(self._timing_data)
            elif operation == 'set':
                self.metrics.avg_set_time_ms = sum(self._timing_data) / len(self._timing_data)
    
    async def _cleanup_loop(self):
        """Periodic cleanup of expired entries"""
        while self._should_cleanup:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                with self._lock:
                    self._evict_expired()
                    self._update_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    def _update_metrics(self):
        """Update cache metrics"""
        if not self.enable_metrics:
            return
        
        self.metrics.cache_size = len(self._cache)
        self.metrics.total_gets = self.metrics.hits + self.metrics.misses
        
        # Calculate memory usage
        total_size = sum(entry.size_bytes for entry in self._cache.values())
        self.metrics.memory_usage_mb = total_size / (1024 * 1024)
    
    def get_metrics(self) -> CacheMetrics:
        """Get current cache metrics"""
        with self._lock:
            self._update_metrics()
            return self.metrics
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information"""
        with self._lock:
            hit_rate = (self.metrics.hits / max(self.metrics.total_gets, 1)) * 100
            
            return {
                'cache_size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate_percent': hit_rate,
                'eviction_strategy': self.eviction_strategy,
                'memory_usage_mb': self.metrics.memory_usage_mb,
                'metrics': self.metrics
            }
    
    def warm_cache(self, warming_function: Callable[[str], Any], keys: List[str]):
        """Warm cache with pre-computed values"""
        logger.info(f"Warming cache with {len(keys)} keys")
        
        for key in keys:
            try:
                value = warming_function(key)
                self.set(key, value)
            except Exception as e:
                logger.warning(f"Failed to warm cache key {key}: {e}")
        
        logger.info(f"Cache warming completed. Cache size: {len(self._cache)}")

# Decorator for caching function results
def cached(
    cache_manager: OptimizedCacheManager,
    ttl: Optional[float] = None,
    key_func: Optional[Callable] = None
):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5('|'.join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
            
            # Compute and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

# Global cache managers for different components
template_cache = OptimizedCacheManager(
    max_size=5000,
    default_ttl=3600,  # 1 hour
    eviction_strategy='lru'
)

signal_cache = OptimizedCacheManager(
    max_size=10000,
    default_ttl=300,   # 5 minutes
    eviction_strategy='lru'
)

market_data_cache = OptimizedCacheManager(
    max_size=20000,
    default_ttl=60,    # 1 minute
    eviction_strategy='ttl'
)

portfolio_cache = OptimizedCacheManager(
    max_size=1000,
    default_ttl=30,    # 30 seconds
    eviction_strategy='lru'
)

async def start_all_cache_managers():
    """Start all global cache managers"""
    await template_cache.start_cache_manager()
    await signal_cache.start_cache_manager()
    await market_data_cache.start_cache_manager()
    await portfolio_cache.start_cache_manager()
    logger.info("All cache managers started")

async def stop_all_cache_managers():
    """Stop all global cache managers"""
    await template_cache.stop_cache_manager()
    await signal_cache.stop_cache_manager()
    await market_data_cache.stop_cache_manager()
    await portfolio_cache.stop_cache_manager()
    logger.info("All cache managers stopped")
