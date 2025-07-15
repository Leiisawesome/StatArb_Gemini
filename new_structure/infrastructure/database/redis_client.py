"""
Redis client for caching and real-time data storage

Provides high-performance Redis operations including:
- DataFrame serialization/deserialization
- JSON data storage
- Pattern-based cache invalidation
- Connection pooling and health monitoring

Author: Pro Quant Desk Trader
"""

import json
import pickle
import logging
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import redis.asyncio as redis
from datetime import timedelta

logger = logging.getLogger(__name__)

class RedisClient:
    """
    High-performance Redis client with DataFrame support
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Redis client
        
        Args:
            config: Redis configuration dictionary
        """
        self.config = config or {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'decode_responses': False,
            'max_connections': 20
        }
        
        self.pool = redis.ConnectionPool(**self.config)
        self.client = redis.Redis(connection_pool=self.pool)
        
        logger.info(f"RedisClient initialized with {self.config['host']}:{self.config['port']}")
    
    async def ping(self) -> bool:
        """Test Redis connection"""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    async def get_dataframe(self, key: str) -> Optional[pd.DataFrame]:
        """
        Retrieve DataFrame from Redis
        
        Args:
            key: Cache key
            
        Returns:
            DataFrame if found, None otherwise
        """
        try:
            data = await self.client.get(key)
            if data is None:
                return None
            
            # Deserialize DataFrame
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Error retrieving DataFrame from Redis key {key}: {e}")
            return None
    
    async def set_dataframe(self, 
                          key: str, 
                          df: pd.DataFrame, 
                          ttl: Optional[int] = None) -> bool:
        """
        Store DataFrame in Redis
        
        Args:
            key: Cache key
            df: DataFrame to store
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            # Serialize DataFrame
            serialized_data = pickle.dumps(df)
            
            if ttl:
                await self.client.setex(key, ttl, serialized_data)
            else:
                await self.client.set(key, serialized_data)
            
            return True
        except Exception as e:
            logger.error(f"Error storing DataFrame to Redis key {key}: {e}")
            return False
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve JSON data from Redis
        
        Args:
            key: Cache key
            
        Returns:
            Dictionary if found, None otherwise
        """
        try:
            data = await self.client.get(key)
            if data is None:
                return None
            
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error retrieving JSON from Redis key {key}: {e}")
            return None
    
    async def set_json(self, 
                      key: str, 
                      data: Dict[str, Any], 
                      ttl: Optional[int] = None) -> bool:
        """
        Store JSON data in Redis
        
        Args:
            key: Cache key
            data: Dictionary to store
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            json_data = json.dumps(data, default=str)
            
            if ttl:
                await self.client.setex(key, ttl, json_data)
            else:
                await self.client.set(key, json_data)
            
            return True
        except Exception as e:
            logger.error(f"Error storing JSON to Redis key {key}: {e}")
            return False
    
    async def get_string(self, key: str) -> Optional[str]:
        """
        Retrieve string from Redis
        
        Args:
            key: Cache key
            
        Returns:
            String if found, None otherwise
        """
        try:
            data = await self.client.get(key)
            return data.decode('utf-8') if data else None
        except Exception as e:
            logger.error(f"Error retrieving string from Redis key {key}: {e}")
            return None
    
    async def set_string(self, 
                        key: str, 
                        value: str, 
                        ttl: Optional[int] = None) -> bool:
        """
        Store string in Redis
        
        Args:
            key: Cache key
            value: String to store
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            if ttl:
                await self.client.setex(key, ttl, value)
            else:
                await self.client.set(key, value)
            
            return True
        except Exception as e:
            logger.error(f"Error storing string to Redis key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis
        
        Args:
            key: Key to delete
            
        Returns:
            True if successful
        """
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting Redis key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete keys matching pattern
        
        Args:
            pattern: Pattern to match (supports * wildcards)
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = await self.client.keys(pattern)
            if keys:
                return await self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error deleting Redis pattern {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis
        
        Args:
            key: Key to check
            
        Returns:
            True if key exists
        """
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Error checking Redis key existence {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for key
        
        Args:
            key: Key to set expiration
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            return bool(await self.client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Error setting expiration for Redis key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """
        Get remaining time to live for key
        
        Args:
            key: Key to check
            
        Returns:
            TTL in seconds (-1 if no expiration, -2 if key doesn't exist)
        """
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for Redis key {key}: {e}")
            return -2
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment counter in Redis
        
        Args:
            key: Counter key
            amount: Amount to increment by
            
        Returns:
            New counter value
        """
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing Redis counter {key}: {e}")
            return 0
    
    async def get_info(self) -> Dict[str, Any]:
        """
        Get Redis server information
        
        Returns:
            Dictionary with Redis info
        """
        try:
            info = await self.client.info()
            return {
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory'),
                'used_memory_human': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses'),
                'uptime_in_seconds': info.get('uptime_in_seconds')
            }
        except Exception as e:
            logger.error(f"Error getting Redis info: {e}")
            return {}
    
    async def flush_db(self) -> bool:
        """
        Clear all keys in current database
        
        Returns:
            True if successful
        """
        try:
            await self.client.flushdb()
            logger.warning("Redis database flushed")
            return True
        except Exception as e:
            logger.error(f"Error flushing Redis database: {e}")
            return False
    
    async def close(self):
        """Close Redis connection"""
        try:
            await self.client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
