"""
Cache Strategy Implementation for StatArb Trading System

This module provides intelligent caching strategies with TTL management,
cache warming, and performance optimization for different data types.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass
import json
import hashlib

logger = logging.getLogger(__name__)


class CacheType(Enum):
    """Cache types with different TTL and strategies"""
    MARKET_DATA = "market_data"
    SIGNALS = "signals"
    ANALYTICS = "analytics"
    CONFIG = "config"
    MODEL_PREDICTIONS = "model_predictions"
    RISK_METRICS = "risk_metrics"
    PORTFOLIO_STATE = "portfolio_state"


@dataclass
class CacheConfig:
    """Cache configuration for different data types"""
    ttl_seconds: int
    max_size: Optional[int] = None
    compression: bool = False
    warm_on_startup: bool = False
    invalidation_strategy: str = "ttl"  # ttl, manual, event_driven
    priority: int = 1  # 1=low, 5=high


class CacheStrategy:
    """
    Intelligent cache strategy manager with TTL, warming, and invalidation.
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.cache_configs = self._initialize_cache_configs()
        self.cache_stats = {}
        self._warming_tasks = {}
        
    def _initialize_cache_configs(self) -> Dict[CacheType, CacheConfig]:
        """Initialize cache configurations for different data types"""
        return {
            CacheType.MARKET_DATA: CacheConfig(
                ttl_seconds=60,  # 1 minute for real-time data
                max_size=10000,
                compression=True,
                warm_on_startup=True,
                priority=5
            ),
            CacheType.SIGNALS: CacheConfig(
                ttl_seconds=300,  # 5 minutes for signals
                max_size=5000,
                compression=True,
                warm_on_startup=True,
                priority=4
            ),
            CacheType.ANALYTICS: CacheConfig(
                ttl_seconds=3600,  # 1 hour for analytics
                max_size=1000,
                compression=True,
                warm_on_startup=False,
                priority=2
            ),
            CacheType.CONFIG: CacheConfig(
                ttl_seconds=86400,  # 24 hours for config
                max_size=100,
                compression=False,
                warm_on_startup=True,
                priority=3
            ),
            CacheType.MODEL_PREDICTIONS: CacheConfig(
                ttl_seconds=900,  # 15 minutes for model predictions
                max_size=2000,
                compression=True,
                warm_on_startup=False,
                priority=4
            ),
            CacheType.RISK_METRICS: CacheConfig(
                ttl_seconds=1800,  # 30 minutes for risk metrics
                max_size=500,
                compression=True,
                warm_on_startup=True,
                priority=3
            ),
            CacheType.PORTFOLIO_STATE: CacheConfig(
                ttl_seconds=60,  # 1 minute for portfolio state
                max_size=100,
                compression=False,
                warm_on_startup=True,
                priority=5
            )
        }
    
    def get_cache_key(self, cache_type: CacheType, identifier: str, 
                     timestamp: Optional[datetime] = None) -> str:
        """Generate standardized cache keys"""
        if timestamp:
            # For time-based data, include timestamp in key
            time_str = timestamp.strftime("%Y%m%d_%H%M%S")
            base_key = f"{cache_type.value}:{identifier}:{time_str}"
        else:
            base_key = f"{cache_type.value}:{identifier}"
        
        # Hash long keys to keep them manageable
        if len(base_key) > 100:
            key_hash = hashlib.md5(base_key.encode()).hexdigest()
            return f"{cache_type.value}:hash:{key_hash}"
        
        return base_key
    
    async def get(self, cache_type: CacheType, identifier: str, 
                  timestamp: Optional[datetime] = None) -> Optional[Any]:
        """Get item from cache with automatic deserialization"""
        key = self.get_cache_key(cache_type, identifier, timestamp)
        
        try:
            cached_data = await self.redis_client.get(key)
            if cached_data is None:
                self._update_cache_stats(cache_type, "miss")
                return None
            
            # Deserialize based on cache type
            if self.cache_configs[cache_type].compression:
                # Decompress if needed (implement compression logic)
                pass
            
            data = json.loads(cached_data)
            self._update_cache_stats(cache_type, "hit")
            
            logger.debug(f"Cache hit for {key}")
            return data
            
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            self._update_cache_stats(cache_type, "error")
            return None
    
    async def set(self, cache_type: CacheType, identifier: str, data: Any,
                  timestamp: Optional[datetime] = None, 
                  custom_ttl: Optional[int] = None) -> bool:
        """Set item in cache with automatic serialization and TTL"""
        key = self.get_cache_key(cache_type, identifier, timestamp)
        config = self.cache_configs[cache_type]
        
        try:
            # Serialize data
            serialized_data = json.dumps(data, default=str)
            
            # Compress if needed
            if config.compression:
                # Implement compression logic
                pass
            
            # Set TTL
            ttl = custom_ttl or config.ttl_seconds
            
            # Store in Redis
            await self.redis_client.setex(key, ttl, serialized_data)
            
            # Check cache size limits
            if config.max_size:
                await self._enforce_cache_size_limit(cache_type, config.max_size)
            
            logger.debug(f"Cache set for {key} with TTL {ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False
    
    async def delete(self, cache_type: CacheType, identifier: str,
                    timestamp: Optional[datetime] = None) -> bool:
        """Delete item from cache"""
        key = self.get_cache_key(cache_type, identifier, timestamp)
        
        try:
            result = await self.redis_client.delete(key)
            logger.debug(f"Cache delete for {key}: {result}")
            return bool(result)
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False
    
    async def invalidate_pattern(self, cache_type: CacheType, 
                               pattern: str) -> int:
        """Invalidate all cache keys matching a pattern"""
        search_pattern = f"{cache_type.value}:{pattern}*"
        
        try:
            keys = await self.redis_client.keys(search_pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries for pattern {search_pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation error for pattern {search_pattern}: {e}")
            return 0
    
    async def warm_cache(self, cache_type: CacheType, 
                        data_loader: Callable) -> bool:
        """Warm cache with initial data"""
        config = self.cache_configs[cache_type]
        
        if not config.warm_on_startup:
            return True
        
        try:
            logger.info(f"Warming cache for {cache_type.value}")
            
            # Load initial data
            initial_data = await data_loader(cache_type)
            
            if initial_data:
                for identifier, data in initial_data.items():
                    await self.set(cache_type, identifier, data)
            
            logger.info(f"Cache warming completed for {cache_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Cache warming failed for {cache_type.value}: {e}")
            return False
    
    async def start_cache_warming(self, data_loaders: Dict[CacheType, Callable]):
        """Start cache warming for all configured cache types"""
        warming_tasks = []
        
        for cache_type, data_loader in data_loaders.items():
            if self.cache_configs[cache_type].warm_on_startup:
                task = asyncio.create_task(
                    self.warm_cache(cache_type, data_loader)
                )
                warming_tasks.append(task)
                self._warming_tasks[cache_type] = task
        
        if warming_tasks:
            await asyncio.gather(*warming_tasks, return_exceptions=True)
    
    async def _enforce_cache_size_limit(self, cache_type: CacheType, 
                                      max_size: int):
        """Enforce cache size limits using LRU eviction"""
        pattern = f"{cache_type.value}:*"
        
        try:
            keys = await self.redis_client.keys(pattern)
            
            if len(keys) > max_size:
                # Get TTL for each key and sort by remaining time
                key_ttls = []
                for key in keys:
                    ttl = await self.redis_client.ttl(key)
                    key_ttls.append((key, ttl))
                
                # Sort by TTL (ascending) and remove oldest
                key_ttls.sort(key=lambda x: x[1])
                keys_to_remove = [k[0] for k in key_ttls[:len(keys) - max_size]]
                
                if keys_to_remove:
                    await self.redis_client.delete(*keys_to_remove)
                    logger.info(f"Evicted {len(keys_to_remove)} entries from {cache_type.value} cache")
        
        except Exception as e:
            logger.error(f"Cache size enforcement error for {cache_type.value}: {e}")
    
    def _update_cache_stats(self, cache_type: CacheType, operation: str):
        """Update cache statistics"""
        if cache_type not in self.cache_stats:
            self.cache_stats[cache_type] = {
                "hits": 0, "misses": 0, "errors": 0, "sets": 0
            }
        
        if operation in self.cache_stats[cache_type]:
            self.cache_stats[cache_type][operation] += 1
    
    def get_cache_stats(self) -> Dict[str, Dict[str, int]]:
        """Get cache performance statistics"""
        stats = {}
        for cache_type, type_stats in self.cache_stats.items():
            total_requests = type_stats["hits"] + type_stats["misses"]
            hit_rate = (type_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            stats[cache_type.value] = {
                **type_stats,
                "hit_rate_percent": round(hit_rate, 2)
            }
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform cache health check"""
        health_status = {
            "status": "healthy",
            "redis_connected": False,
            "cache_stats": self.get_cache_stats(),
            "warming_tasks": {}
        }
        
        try:
            # Check Redis connection
            await self.redis_client.ping()
            health_status["redis_connected"] = True
            
            # Check warming task status
            for cache_type, task in self._warming_tasks.items():
                health_status["warming_tasks"][cache_type.value] = {
                    "done": task.done(),
                    "cancelled": task.cancelled()
                }
        
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status


class CacheDecorator:
    """Decorator for automatic caching of function results"""
    
    def __init__(self, cache_strategy: CacheStrategy, cache_type: CacheType,
                 ttl: Optional[int] = None):
        self.cache_strategy = cache_strategy
        self.cache_type = cache_type
        self.ttl = ttl
    
    def __call__(self, func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and args
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache first
            cached_result = await self.cache_strategy.get(
                self.cache_type, cache_key
            )
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            await self.cache_strategy.set(
                self.cache_type, cache_key, result, custom_ttl=self.ttl
            )
            
            return result
        
        return wrapper


# Usage example decorator
def cached(cache_type: CacheType, ttl: Optional[int] = None):
    """Decorator factory for caching function results"""
    def decorator(func: Callable) -> Callable:
        # This would be initialized with actual cache_strategy instance
        # cache_decorator = CacheDecorator(cache_strategy, cache_type, ttl)
        # return cache_decorator(func)
        return func  # Placeholder implementation
    return decorator
