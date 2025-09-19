"""
Data Engine - Cache Manager
Advanced caching system with intelligent eviction, compression, and distributed caching support
"""

import logging
import threading
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque, OrderedDict
import json
import pickle
import hashlib
import gzip
import weakref
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache storage levels"""
    L1_MEMORY = "l1_memory"
    L2_COMPRESSED = "l2_compressed"
    L3_DISK = "l3_disk"
    L4_DISTRIBUTED = "l4_distributed"


class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    SIZE_BASED = "size_based"
    PRIORITY_BASED = "priority_based"
    ADAPTIVE = "adaptive"


class CacheStrategy(Enum):
    """Cache storage strategies"""
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    WRITE_AROUND = "write_around"
    READ_THROUGH = "read_through"
    CACHE_ASIDE = "cache_aside"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    cache_level: CacheLevel
    
    # Metadata
    creation_time: datetime
    last_access_time: datetime
    access_count: int
    priority: int
    
    # Size and compression
    original_size_bytes: int
    compressed_size_bytes: Optional[int] = None
    is_compressed: bool = False
    
    # TTL and expiration
    ttl_seconds: Optional[float] = None
    expiry_time: Optional[datetime] = None
    
    # Content metadata
    content_type: str = "unknown"
    checksum: Optional[str] = None
    
    # Performance tracking
    compression_time_ms: float = 0.0
    decompression_time_ms: float = 0.0


@dataclass
class CacheStatistics:
    """Cache performance statistics"""
    # Hit/miss statistics
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Performance metrics
    average_response_time_ms: float = 0.0
    compression_ratio: float = 0.0
    
    # Storage statistics
    total_entries: int = 0
    total_size_bytes: int = 0
    memory_usage_bytes: int = 0
    disk_usage_bytes: int = 0
    
    # Level-specific statistics
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    l4_hits: int = 0
    
    # Eviction statistics
    evictions_total: int = 0
    evictions_by_policy: Dict[str, int] = field(default_factory=dict)
    
    # Error statistics
    compression_errors: int = 0
    decompression_errors: int = 0
    storage_errors: int = 0
    
    last_update: datetime = field(default_factory=datetime.now)


class CacheBackend(ABC):
    """Abstract cache backend interface"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache backend"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in cache backend"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache backend"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache backend"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all entries from cache backend"""
        pass
    
    @abstractmethod
    def get_size(self) -> int:
        """Get backend storage size in bytes"""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache = OrderedDict()
        self._lock = threading.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                value = self._cache.pop(key)
                self._cache[key] = value
                return value
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in memory cache"""
        try:
            with self._lock:
                # Remove if exists
                if key in self._cache:
                    del self._cache[key]
                
                # Add new entry
                self._cache[key] = value
                
                # Evict if necessary
                while len(self._cache) > self.max_size:
                    self._cache.popitem(last=False)  # Remove least recently used
                
                return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from memory cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache"""
        with self._lock:
            return key in self._cache
    
    async def clear(self) -> bool:
        """Clear memory cache"""
        with self._lock:
            self._cache.clear()
            return True
    
    def get_size(self) -> int:
        """Get memory cache size"""
        with self._lock:
            return len(self._cache)


class CompressedCacheBackend(CacheBackend):
    """Compressed cache backend using gzip"""
    
    def __init__(self, max_size: int = 5000):
        self.max_size = max_size
        self._cache = OrderedDict()
        self._lock = threading.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get and decompress value"""
        with self._lock:
            if key in self._cache:
                compressed_data = self._cache.pop(key)
                self._cache[key] = compressed_data  # Move to end
                
                try:
                    # Decompress
                    decompressed_data = gzip.decompress(compressed_data)
                    return pickle.loads(decompressed_data)
                except Exception as e:
                    logger.error(f"Decompression error for key {key}: {e}")
                    return None
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Compress and set value"""
        try:
            # Serialize and compress
            serialized_data = pickle.dumps(value)
            compressed_data = gzip.compress(serialized_data)
            
            with self._lock:
                # Remove if exists
                if key in self._cache:
                    del self._cache[key]
                
                # Add compressed entry
                self._cache[key] = compressed_data
                
                # Evict if necessary
                while len(self._cache) > self.max_size:
                    self._cache.popitem(last=False)
                
                return True
        except Exception as e:
            logger.error(f"Compression error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete compressed value"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if compressed key exists"""
        with self._lock:
            return key in self._cache
    
    async def clear(self) -> bool:
        """Clear compressed cache"""
        with self._lock:
            self._cache.clear()
            return True
    
    def get_size(self) -> int:
        """Get compressed cache size"""
        with self._lock:
            return sum(len(data) for data in self._cache.values())


class CacheManager:
    """
    Advanced multi-level cache manager
    
    Provides intelligent caching with multiple storage levels,
    compression, TTL management, and adaptive eviction policies.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize cache manager"""
        self.config = config or {}
        self._lock = threading.Lock()
        
        # Cache configuration
        self.enable_l1_memory = self.config.get('enable_l1_memory', True)
        self.enable_l2_compressed = self.config.get('enable_l2_compressed', True)
        self.enable_l3_disk = self.config.get('enable_l3_disk', False)
        self.enable_l4_distributed = self.config.get('enable_l4_distributed', False)
        
        # Size limits
        self.l1_max_size = self.config.get('l1_max_size', 1000)
        self.l2_max_size = self.config.get('l2_max_size', 5000)
        self.l3_max_size_mb = self.config.get('l3_max_size_mb', 1000)
        
        # Cache backends
        self._backends = {}
        self._initialize_backends()
        
        # Cache entries metadata
        self._entries_metadata = {}
        
        # Statistics
        self._statistics = CacheStatistics()
        
        # Eviction policies
        self.default_eviction_policy = EvictionPolicy(
            self.config.get('default_eviction_policy', 'lru')
        )
        
        # TTL settings
        self.default_ttl_seconds = self.config.get('default_ttl_seconds', 3600)  # 1 hour
        self.enable_auto_ttl = self.config.get('enable_auto_ttl', True)
        
        # Compression settings
        self.compression_threshold_bytes = self.config.get('compression_threshold_bytes', 1024)
        self.compression_level = self.config.get('compression_level', 6)
        
        # Access tracking
        self._access_patterns = defaultdict(lambda: {'count': 0, 'last_access': datetime.now()})
        
        # Background tasks
        self._cleanup_tasks = []
        
        # Performance monitoring
        self._performance_history = deque(maxlen=1000)
        
        # Start background tasks
        asyncio.create_task(self._start_background_tasks())
        
        logger.info("CacheManager initialized")
    
    def _initialize_backends(self) -> None:
        """Initialize cache backends"""
        
        if self.enable_l1_memory:
            self._backends[CacheLevel.L1_MEMORY] = MemoryCacheBackend(self.l1_max_size)
        
        if self.enable_l2_compressed:
            self._backends[CacheLevel.L2_COMPRESSED] = CompressedCacheBackend(self.l2_max_size)
        
        # L3 and L4 would be implemented with disk and distributed backends
        # For now, we'll use simulated backends
        
        logger.info(f"Initialized {len(self._backends)} cache backends")
    
    async def get(
        self,
        key: str,
        default: Any = None,
        update_access: bool = True
    ) -> Any:
        """
        Get value from cache with multi-level lookup
        
        Args:
            key: Cache key
            default: Default value if not found
            update_access: Whether to update access statistics
            
        Returns:
            Cached value or default
        """
        
        start_time = time.time()
        
        try:
            # Update statistics
            with self._lock:
                self._statistics.total_requests += 1
            
            # Check each cache level in order
            for level in [CacheLevel.L1_MEMORY, CacheLevel.L2_COMPRESSED, 
                         CacheLevel.L3_DISK, CacheLevel.L4_DISTRIBUTED]:
                
                backend = self._backends.get(level)
                if not backend:
                    continue
                
                # Try to get from this level
                value = await backend.get(key)
                
                if value is not None:
                    # Cache hit
                    await self._handle_cache_hit(key, level, value, update_access)
                    
                    # Promote to higher levels if needed
                    await self._promote_cache_entry(key, value, level)
                    
                    # Update performance metrics
                    response_time = (time.time() - start_time) * 1000
                    await self._update_performance_metrics(response_time, hit=True)
                    
                    return value
            
            # Cache miss
            await self._handle_cache_miss(key)
            
            # Update performance metrics
            response_time = (time.time() - start_time) * 1000
            await self._update_performance_metrics(response_time, hit=False)
            
            return default
            
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        priority: int = 0,
        cache_level: Optional[CacheLevel] = None
    ) -> bool:
        """
        Set value in cache with intelligent level selection
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            priority: Cache priority (higher = more important)
            cache_level: Specific cache level to use
            
        Returns:
            True if successfully cached
        """
        
        try:
            # Determine TTL
            effective_ttl = ttl or self.default_ttl_seconds
            if self.enable_auto_ttl:
                effective_ttl = await self._calculate_adaptive_ttl(key, value)
            
            # Calculate value size
            value_size = self._calculate_value_size(value)
            
            # Determine target cache level
            if cache_level:
                target_level = cache_level
            else:
                target_level = await self._select_cache_level(value_size, priority)
            
            # Create cache entry metadata
            entry_metadata = CacheEntry(
                key=key,
                value=value,
                cache_level=target_level,
                creation_time=datetime.now(),
                last_access_time=datetime.now(),
                access_count=1,
                priority=priority,
                original_size_bytes=value_size,
                ttl_seconds=effective_ttl,
                expiry_time=datetime.now() + timedelta(seconds=effective_ttl) if effective_ttl else None,
                content_type=self._determine_content_type(value),
                checksum=self._calculate_checksum(value)
            )
            
            # Store in target level
            backend = self._backends.get(target_level)
            if backend:
                success = await backend.set(key, value, effective_ttl)
                
                if success:
                    # Store metadata
                    with self._lock:
                        self._entries_metadata[key] = entry_metadata
                    
                    # Update access patterns
                    self._access_patterns[key]['count'] += 1
                    self._access_patterns[key]['last_access'] = datetime.now()
                    
                    logger.debug(f"Cached {key} in {target_level.value} (size: {value_size} bytes)")
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from all cache levels"""
        
        success = False
        
        try:
            # Remove from all levels
            for backend in self._backends.values():
                if await backend.delete(key):
                    success = True
            
            # Remove metadata
            with self._lock:
                self._entries_metadata.pop(key, None)
                self._access_patterns.pop(key, None)
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in any cache level"""
        
        try:
            for backend in self._backends.values():
                if await backend.exists(key):
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    async def clear(self, cache_level: Optional[CacheLevel] = None) -> bool:
        """Clear cache entries"""
        
        try:
            if cache_level:
                # Clear specific level
                backend = self._backends.get(cache_level)
                if backend:
                    return await backend.clear()
                return False
            else:
                # Clear all levels
                success = True
                for backend in self._backends.values():
                    if not await backend.clear():
                        success = False
                
                # Clear metadata
                with self._lock:
                    self._entries_metadata.clear()
                    self._access_patterns.clear()
                
                return success
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    async def _handle_cache_hit(
        self,
        key: str,
        level: CacheLevel,
        value: Any,
        update_access: bool
    ) -> None:
        """Handle cache hit"""
        
        with self._lock:
            self._statistics.cache_hits += 1
            
            # Update level-specific hits
            if level == CacheLevel.L1_MEMORY:
                self._statistics.l1_hits += 1
            elif level == CacheLevel.L2_COMPRESSED:
                self._statistics.l2_hits += 1
            elif level == CacheLevel.L3_DISK:
                self._statistics.l3_hits += 1
            elif level == CacheLevel.L4_DISTRIBUTED:
                self._statistics.l4_hits += 1
        
        if update_access:
            # Update entry metadata
            metadata = self._entries_metadata.get(key)
            if metadata:
                metadata.last_access_time = datetime.now()
                metadata.access_count += 1
            
            # Update access patterns
            self._access_patterns[key]['count'] += 1
            self._access_patterns[key]['last_access'] = datetime.now()
    
    async def _handle_cache_miss(self, key: str) -> None:
        """Handle cache miss"""
        
        with self._lock:
            self._statistics.cache_misses += 1
    
    async def _promote_cache_entry(
        self,
        key: str,
        value: Any,
        current_level: CacheLevel
    ) -> None:
        """Promote cache entry to higher levels based on access patterns"""
        
        # Get access pattern
        access_info = self._access_patterns.get(key)
        if not access_info:
            return
        
        # Check if promotion is warranted
        access_count = access_info['count']
        recent_access = (datetime.now() - access_info['last_access']).total_seconds() < 300  # 5 minutes
        
        # Promotion thresholds
        if access_count >= 5 and recent_access:
            # Promote to L1 if currently in L2 or lower
            if current_level != CacheLevel.L1_MEMORY:
                l1_backend = self._backends.get(CacheLevel.L1_MEMORY)
                if l1_backend:
                    await l1_backend.set(key, value)
        
        elif access_count >= 3 and recent_access:
            # Promote to L2 if currently in L3 or lower
            if current_level in [CacheLevel.L3_DISK, CacheLevel.L4_DISTRIBUTED]:
                l2_backend = self._backends.get(CacheLevel.L2_COMPRESSED)
                if l2_backend:
                    await l2_backend.set(key, value)
    
    async def _select_cache_level(self, value_size: int, priority: int) -> CacheLevel:
        """Select optimal cache level for value"""
        
        # High priority or small size -> L1
        if priority >= 5 or value_size < 1024:  # < 1KB
            if self.enable_l1_memory:
                return CacheLevel.L1_MEMORY
        
        # Medium size -> L2 compressed
        if value_size < 100 * 1024:  # < 100KB
            if self.enable_l2_compressed:
                return CacheLevel.L2_COMPRESSED
        
        # Large size -> L3 disk
        if self.enable_l3_disk:
            return CacheLevel.L3_DISK
        
        # Default to L2 if available, otherwise L1
        if self.enable_l2_compressed:
            return CacheLevel.L2_COMPRESSED
        elif self.enable_l1_memory:
            return CacheLevel.L1_MEMORY
        else:
            return CacheLevel.L3_DISK
    
    async def _calculate_adaptive_ttl(self, key: str, value: Any) -> float:
        """Calculate adaptive TTL based on access patterns"""
        
        access_info = self._access_patterns.get(key)
        base_ttl = self.default_ttl_seconds
        
        if access_info:
            access_count = access_info['count']
            
            # More accessed items get longer TTL
            if access_count >= 10:
                return base_ttl * 3  # 3x longer
            elif access_count >= 5:
                return base_ttl * 2  # 2x longer
            elif access_count >= 2:
                return base_ttl * 1.5  # 1.5x longer
        
        return base_ttl
    
    def _calculate_value_size(self, value: Any) -> int:
        """Calculate value size in bytes"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value.encode('utf-8') if isinstance(value, str) else value)
            else:
                # Estimate using pickle serialization
                return len(pickle.dumps(value))
        except Exception:
            return 1024  # Default estimate
    
    def _determine_content_type(self, value: Any) -> str:
        """Determine content type of value"""
        if isinstance(value, str):
            return "string"
        elif isinstance(value, bytes):
            return "bytes"
        elif isinstance(value, dict):
            return "dict"
        elif isinstance(value, list):
            return "list"
        elif isinstance(value, pd.DataFrame):
            return "dataframe"
        elif isinstance(value, np.ndarray):
            return "numpy_array"
        else:
            return "object"
    
    def _calculate_checksum(self, value: Any) -> str:
        """Calculate checksum for value integrity"""
        try:
            serialized = pickle.dumps(value)
            return hashlib.md5(serialized).hexdigest()
        except Exception:
            return ""
    
    async def _update_performance_metrics(self, response_time_ms: float, hit: bool) -> None:
        """Update performance metrics"""
        
        with self._lock:
            # Update average response time
            total_requests = self._statistics.total_requests
            current_avg = self._statistics.average_response_time_ms
            
            self._statistics.average_response_time_ms = (
                (current_avg * (total_requests - 1) + response_time_ms) / total_requests
            )
        
        # Store performance history
        self._performance_history.append({
            'timestamp': datetime.now(),
            'response_time_ms': response_time_ms,
            'hit': hit
        })
    
    async def _start_background_tasks(self) -> None:
        """Start background maintenance tasks"""
        
        self._cleanup_tasks = [
            asyncio.create_task(self._expire_entries()),
            asyncio.create_task(self._update_statistics()),
            asyncio.create_task(self._adaptive_eviction()),
            asyncio.create_task(self._performance_monitoring())
        ]
        
        logger.info("Started cache background tasks")
    
    async def _expire_entries(self) -> None:
        """Expire old cache entries"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.now()
                expired_keys = []
                
                # Find expired entries
                with self._lock:
                    for key, metadata in self._entries_metadata.items():
                        if metadata.expiry_time and current_time > metadata.expiry_time:
                            expired_keys.append(key)
                
                # Remove expired entries
                for key in expired_keys:
                    await self.delete(key)
                    logger.debug(f"Expired cache key: {key}")
                
                if expired_keys:
                    logger.info(f"Expired {len(expired_keys)} cache entries")
                
            except Exception as e:
                logger.error(f"Error in cache expiration: {e}")
                await asyncio.sleep(60)
    
    async def _update_statistics(self) -> None:
        """Update cache statistics"""
        
        while True:
            try:
                await asyncio.sleep(300)  # Update every 5 minutes
                
                with self._lock:
                    # Update total entries and size
                    self._statistics.total_entries = len(self._entries_metadata)
                    
                    total_size = 0
                    for metadata in self._entries_metadata.values():
                        total_size += metadata.original_size_bytes
                    
                    self._statistics.total_size_bytes = total_size
                    
                    # Update memory usage
                    self._statistics.memory_usage_bytes = sum(
                        backend.get_size() for level, backend in self._backends.items()
                        if level in [CacheLevel.L1_MEMORY, CacheLevel.L2_COMPRESSED]
                    )
                    
                    # Update last update time
                    self._statistics.last_update = datetime.now()
                
            except Exception as e:
                logger.error(f"Error updating cache statistics: {e}")
                await asyncio.sleep(300)
    
    async def _adaptive_eviction(self) -> None:
        """Perform adaptive cache eviction"""
        
        while True:
            try:
                await asyncio.sleep(600)  # Check every 10 minutes
                
                # Check if eviction is needed based on cache size or memory pressure
                current_memory_usage = self._statistics.memory_usage_bytes
                memory_threshold = 500 * 1024 * 1024  # 500MB threshold
                
                if current_memory_usage > memory_threshold:
                    await self._perform_eviction()
                
            except Exception as e:
                logger.error(f"Error in adaptive eviction: {e}")
                await asyncio.sleep(600)
    
    async def _perform_eviction(self) -> None:
        """Perform cache eviction based on policy"""
        
        eviction_count = 0
        
        try:
            # Get candidates for eviction
            candidates = []
            
            with self._lock:
                for key, metadata in self._entries_metadata.items():
                    # Calculate eviction score
                    score = await self._calculate_eviction_score(key, metadata)
                    candidates.append((key, score))
            
            # Sort by eviction score (lower score = more likely to evict)
            candidates.sort(key=lambda x: x[1])
            
            # Evict bottom 10%
            evict_count = max(1, len(candidates) // 10)
            
            for key, _ in candidates[:evict_count]:
                await self.delete(key)
                eviction_count += 1
            
            with self._lock:
                self._statistics.evictions_total += eviction_count
                policy_key = self.default_eviction_policy.value
                self._statistics.evictions_by_policy[policy_key] = (
                    self._statistics.evictions_by_policy.get(policy_key, 0) + eviction_count
                )
            
            logger.info(f"Evicted {eviction_count} cache entries")
            
        except Exception as e:
            logger.error(f"Error performing eviction: {e}")
    
    async def _calculate_eviction_score(self, key: str, metadata: CacheEntry) -> float:
        """Calculate eviction score for entry (lower = more likely to evict)"""
        
        score = 0.0
        current_time = datetime.now()
        
        # Time-based factors
        age_hours = (current_time - metadata.creation_time).total_seconds() / 3600
        last_access_hours = (current_time - metadata.last_access_time).total_seconds() / 3600
        
        # LRU component
        score += last_access_hours * 10
        
        # Age component
        score += age_hours * 5
        
        # Access frequency component (higher frequency = higher score = less likely to evict)
        access_rate = metadata.access_count / max(1, age_hours)
        score -= access_rate * 20
        
        # Priority component
        score -= metadata.priority * 10
        
        # Size component (larger items slightly more likely to evict)
        size_mb = metadata.original_size_bytes / (1024 * 1024)
        score += size_mb * 2
        
        return max(0, score)
    
    async def _performance_monitoring(self) -> None:
        """Monitor cache performance and adjust parameters"""
        
        while True:
            try:
                await asyncio.sleep(900)  # Check every 15 minutes
                
                # Calculate hit rate
                total_requests = self._statistics.total_requests
                hit_rate = self._statistics.cache_hits / total_requests if total_requests > 0 else 0
                
                # Log performance metrics
                logger.info(f"Cache performance: {hit_rate:.1%} hit rate, "
                           f"{self._statistics.average_response_time_ms:.2f}ms avg response time")
                
                # Adaptive adjustments
                if hit_rate < 0.7:  # Low hit rate
                    logger.warning("Low cache hit rate detected")
                    # Could trigger cache warming or parameter adjustment
                
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(900)
    
    def get_statistics(self) -> CacheStatistics:
        """Get cache statistics"""
        with self._lock:
            # Calculate hit rate
            total_requests = self._statistics.total_requests
            if total_requests > 0:
                hit_rate = self._statistics.cache_hits / total_requests
            else:
                hit_rate = 0.0
            
            # Create updated statistics
            stats = CacheStatistics(
                total_requests=self._statistics.total_requests,
                cache_hits=self._statistics.cache_hits,
                cache_misses=self._statistics.cache_misses,
                average_response_time_ms=self._statistics.average_response_time_ms,
                compression_ratio=self._statistics.compression_ratio,
                total_entries=len(self._entries_metadata),
                total_size_bytes=sum(m.original_size_bytes for m in self._entries_metadata.values()),
                memory_usage_bytes=self._statistics.memory_usage_bytes,
                disk_usage_bytes=self._statistics.disk_usage_bytes,
                l1_hits=self._statistics.l1_hits,
                l2_hits=self._statistics.l2_hits,
                l3_hits=self._statistics.l3_hits,
                l4_hits=self._statistics.l4_hits,
                evictions_total=self._statistics.evictions_total,
                evictions_by_policy=self._statistics.evictions_by_policy.copy(),
                compression_errors=self._statistics.compression_errors,
                decompression_errors=self._statistics.decompression_errors,
                storage_errors=self._statistics.storage_errors,
                last_update=datetime.now()
            )
            
            return stats
    
    def get_cache_entries(self, cache_level: Optional[CacheLevel] = None) -> List[CacheEntry]:
        """Get cache entries metadata"""
        
        with self._lock:
            entries = list(self._entries_metadata.values())
            
            if cache_level:
                entries = [entry for entry in entries if entry.cache_level == cache_level]
            
            return entries
    
    def get_access_patterns(self, top_n: int = 20) -> Dict[str, Dict[str, Any]]:
        """Get top access patterns"""
        
        # Sort by access count
        sorted_patterns = sorted(
            self._access_patterns.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        return dict(sorted_patterns[:top_n])
    
    async def warmup_cache(
        self,
        keys_values: Dict[str, Any],
        cache_level: Optional[CacheLevel] = None
    ) -> int:
        """Warm up cache with predefined key-value pairs"""
        
        success_count = 0
        
        for key, value in keys_values.items():
            try:
                if await self.set(key, value, cache_level=cache_level):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error warming up cache key {key}: {e}")
        
        logger.info(f"Cache warmup completed: {success_count}/{len(keys_values)} entries")
        
        return success_count
    
    async def cleanup(self) -> None:
        """Cleanup cache manager resources"""
        
        # Cancel background tasks
        for task in self._cleanup_tasks:
            task.cancel()
        
        # Clear all caches
        await self.clear()
        
        logger.info("CacheManager cleanup completed")