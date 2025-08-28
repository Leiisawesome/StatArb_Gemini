"""
Unified Database System for StatArb Trading System
================================================

Phase 5C Infrastructure Consolidation - Database Module
Consolidates database functionality into a unified system.

Consolidated from:
- clickhouse_client.py (304 lines) - ClickHouse time-series database client
- redis_client.py (352 lines) - Redis caching and real-time data client
- database_manager.py (322 lines) - Unified database management layer
- cache_strategy.py (373 lines) - Intelligent caching strategies

This module provides comprehensive database capabilities including:
- High-performance ClickHouse operations for time-series data
- Redis caching with intelligent TTL management
- Unified database management with connection pooling
- Advanced caching strategies with warming and invalidation
- Connection health monitoring and failover support
"""

import asyncio
import json
import pickle
import logging
import hashlib
import time
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from clickhouse_driver import Client
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# =============================================================================
# Cache Strategy System
# =============================================================================

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


@dataclass
class DatabaseConfig:
    """Database configuration container"""
    clickhouse: Dict[str, Any]
    redis: Dict[str, Any]
    cache: Dict[str, Any]


# =============================================================================
# Performance Decorators
# =============================================================================

def with_metrics(func):
    """Decorator to track query metrics"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(self, *args, **kwargs)
            if hasattr(self, 'metrics') and self.metrics:
                self.metrics.record_metric(
                    f"{self.__class__.__name__.lower()}_{func.__name__}",
                    (time.perf_counter() - start_time) * 1000
                )
            return result
        except Exception as e:
            if hasattr(self, 'metrics') and self.metrics:
                self.metrics.increment_counter(f"{self.__class__.__name__.lower()}_error_{func.__name__}")
            raise
    return wrapper


def with_cache(cache_type: CacheType, ttl_seconds: Optional[int] = None):
    """Decorator to add caching to methods"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate cache key
            cache_key = f"{cache_type.value}:{func.__name__}:{hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()}"
            
            # Try to get from cache
            if hasattr(self, 'cache_strategy'):
                cached_result = await self.cache_strategy.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Execute function
            result = await func(self, *args, **kwargs)
            
            # Store in cache
            if hasattr(self, 'cache_strategy'):
                ttl = ttl_seconds or self.cache_strategy.cache_configs.get(cache_type, CacheConfig(300)).ttl_seconds
                await self.cache_strategy.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# =============================================================================
# Cache Strategy System
# =============================================================================

class CacheStrategy:
    """
    Intelligent cache strategy manager with TTL, warming, and invalidation.
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.cache_configs = self._initialize_cache_configs()
        self.cache_stats = {}
        self._warming_tasks = []
        
        logger.info("CacheStrategy initialized with intelligent TTL management")
    
    def _initialize_cache_configs(self) -> Dict[CacheType, CacheConfig]:
        """Initialize cache configurations for different data types"""
        return {
            CacheType.MARKET_DATA: CacheConfig(
                ttl_seconds=300,  # 5 minutes
                max_size=10000,
                compression=True,
                warm_on_startup=True,
                priority=5
            ),
            CacheType.SIGNALS: CacheConfig(
                ttl_seconds=60,   # 1 minute
                max_size=5000,
                compression=False,
                warm_on_startup=True,
                priority=4
            ),
            CacheType.ANALYTICS: CacheConfig(
                ttl_seconds=900,  # 15 minutes
                max_size=1000,
                compression=True,
                warm_on_startup=False,
                priority=3
            ),
            CacheType.CONFIG: CacheConfig(
                ttl_seconds=3600, # 1 hour
                max_size=100,
                compression=False,
                warm_on_startup=True,
                priority=5
            ),
            CacheType.MODEL_PREDICTIONS: CacheConfig(
                ttl_seconds=120,  # 2 minutes
                max_size=2000,
                compression=True,
                warm_on_startup=False,
                priority=4
            ),
            CacheType.RISK_METRICS: CacheConfig(
                ttl_seconds=180,  # 3 minutes
                max_size=1000,
                compression=False,
                warm_on_startup=True,
                priority=4
            ),
            CacheType.PORTFOLIO_STATE: CacheConfig(
                ttl_seconds=30,   # 30 seconds
                max_size=500,
                compression=False,
                warm_on_startup=True,
                priority=5
            )
        }
    
    async def get(self, key: str, cache_type: Optional[CacheType] = None) -> Any:
        """Get value from cache with decompression if needed"""
        try:
            raw_value = await self.redis_client.get(key)
            if raw_value is None:
                self._update_stats('miss', cache_type)
                return None
            
            # Deserialize based on cache type
            config = self.cache_configs.get(cache_type) if cache_type else None
            if config and config.compression:
                value = pickle.loads(raw_value)
            else:
                try:
                    value = json.loads(raw_value.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    value = pickle.loads(raw_value)
            
            self._update_stats('hit', cache_type)
            return value
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self._update_stats('error', cache_type)
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, 
                  cache_type: Optional[CacheType] = None) -> bool:
        """Set value in cache with compression if configured"""
        try:
            # Determine TTL
            if ttl_seconds is None and cache_type:
                config = self.cache_configs.get(cache_type)
                ttl_seconds = config.ttl_seconds if config else 300
            ttl_seconds = ttl_seconds or 300
            
            # Serialize based on cache type
            config = self.cache_configs.get(cache_type) if cache_type else None
            if config and config.compression:
                serialized_value = pickle.dumps(value)
            else:
                try:
                    serialized_value = json.dumps(value).encode('utf-8')
                except (TypeError, ValueError):
                    serialized_value = pickle.dumps(value)
            
            # Store with TTL
            await self.redis_client.setex(key, ttl_seconds, serialized_value)
            self._update_stats('set', cache_type)
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            self._update_stats('error', cache_type)
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern"""
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache keys matching pattern: {pattern}")
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation error for pattern {pattern}: {e}")
            return 0
    
    async def warm_cache(self, cache_type: CacheType, data_loader: Callable) -> None:
        """Warm cache with frequently accessed data"""
        try:
            config = self.cache_configs.get(cache_type)
            if not config or not config.warm_on_startup:
                return
            
            logger.info(f"Warming cache for {cache_type.value}")
            data = await data_loader()
            
            if isinstance(data, dict):
                for key, value in data.items():
                    cache_key = f"{cache_type.value}:warm:{key}"
                    await self.set(cache_key, value, config.ttl_seconds, cache_type)
            
            logger.info(f"Cache warming completed for {cache_type.value}")
            
        except Exception as e:
            logger.error(f"Cache warming error for {cache_type.value}: {e}")
    
    def _update_stats(self, operation: str, cache_type: Optional[CacheType]) -> None:
        """Update cache statistics"""
        key = cache_type.value if cache_type else 'unknown'
        if key not in self.cache_stats:
            self.cache_stats[key] = {'hits': 0, 'misses': 0, 'sets': 0, 'errors': 0}
        
        if operation in self.cache_stats[key]:
            self.cache_stats[key][operation] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_stats = {'total_hits': 0, 'total_misses': 0, 'total_sets': 0, 'total_errors': 0}
        
        for cache_type, stats in self.cache_stats.items():
            for op, count in stats.items():
                total_stats[f'total_{op}'] += count
        
        # Calculate hit rate
        total_requests = total_stats['total_hits'] + total_stats['total_misses']
        hit_rate = (total_stats['total_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_rate_percent': hit_rate,
            'by_type': self.cache_stats,
            'totals': total_stats
        }


# =============================================================================
# Redis Client System
# =============================================================================

class RedisClient:
    """
    High-performance Redis client with DataFrame support and connection pooling
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize Redis client with connection pooling"""
        self.config = config or {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'decode_responses': False,
            'max_connections': 20,
            'socket_keepalive': True,
            'socket_keepalive_options': {},
            'health_check_interval': 30
        }
        
        self.pool = redis.ConnectionPool(**self.config)
        self.client = redis.Redis(connection_pool=self.pool)
        self.metrics = None  # Will be set by DatabaseManager
        
        logger.info(f"RedisClient initialized with {self.config['host']}:{self.config['port']}")
    
    async def ping(self) -> bool:
        """Test Redis connection"""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    @with_metrics
    async def get(self, key: str) -> Optional[bytes]:
        """Get value from Redis"""
        return await self.client.get(key)
    
    @with_metrics
    async def set(self, key: str, value: Union[str, bytes], ex: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        return await self.client.set(key, value, ex=ex)
    
    @with_metrics
    async def setex(self, key: str, seconds: int, value: Union[str, bytes]) -> bool:
        """Set value with expiration time"""
        return await self.client.setex(key, seconds, value)
    
    @with_metrics
    async def delete(self, *keys: str) -> int:
        """Delete keys from Redis"""
        return await self.client.delete(*keys)
    
    @with_metrics
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        return await self.client.keys(pattern)
    
    @with_metrics
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await self.client.exists(key) > 0
    
    @with_metrics
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        return await self.client.ttl(key)
    
    # DataFrame operations
    async def set_dataframe(self, key: str, df: pd.DataFrame, ttl_seconds: Optional[int] = None) -> bool:
        """Store DataFrame in Redis with optional TTL"""
        try:
            serialized_df = pickle.dumps(df)
            if ttl_seconds:
                return await self.setex(key, ttl_seconds, serialized_df)
            else:
                return await self.set(key, serialized_df)
        except Exception as e:
            logger.error(f"Error storing DataFrame {key}: {e}")
            return False
    
    async def get_dataframe(self, key: str) -> Optional[pd.DataFrame]:
        """Retrieve DataFrame from Redis"""
        try:
            data = await self.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving DataFrame {key}: {e}")
            return None
    
    # JSON operations
    async def set_json(self, key: str, data: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Store JSON data in Redis"""
        try:
            json_data = json.dumps(data)
            if ttl_seconds:
                return await self.setex(key, ttl_seconds, json_data)
            else:
                return await self.set(key, json_data)
        except Exception as e:
            logger.error(f"Error storing JSON {key}: {e}")
            return False
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Retrieve JSON data from Redis"""
        try:
            data = await self.get(key)
            if data:
                return json.loads(data.decode('utf-8'))
            return None
        except Exception as e:
            logger.error(f"Error retrieving JSON {key}: {e}")
            return None
    
    async def close(self) -> None:
        """Close Redis connection"""
        await self.client.close()


# =============================================================================
# ClickHouse Client System
# =============================================================================

class ClickHouseClient:
    """High-performance ClickHouse client with connection pooling and query optimization"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {
            'host': 'localhost',
            'port': 9000,
            'database': 'trading',
            'user': 'default',
            'password': '',
            'connect_timeout': 10,
            'send_receive_timeout': 300,
            'sync_request_timeout': 5,
            'compress_block_size': 1048576,
            'settings': {
                'max_execution_time': 300,
                'max_memory_usage': 2000000000,  # 2GB
                'use_uncompressed_cache': 1
            }
        }
        
        # Ensure required keys exist with defaults
        required_defaults = {
            'host': 'localhost',
            'port': 9000,
            'database': 'trading',
            'user': 'default',
            'password': ''
        }
        
        for key, default_value in required_defaults.items():
            if key not in self.config:
                self.config[key] = default_value
                logger.warning(f"Missing '{key}' in ClickHouse config, using default: {default_value}")
        
        # Initialize connection pool
        self.client = Client(**self.config)
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="clickhouse-")
        self.metrics = None  # Will be set by DatabaseManager
        
        logger.info(f"ClickHouseClient initialized with {self.config['host']}:{self.config['port']}")
    
    @with_metrics
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[List]:
        """Execute query and return raw results"""
        try:
            return self.client.execute(query, params or {})
        except Exception as e:
            logger.error(f"ClickHouse query error: {e}")
            logger.error(f"Query: {query}")
            raise
    
    @with_metrics
    def query_dataframe(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """Execute query and return results as DataFrame"""
        try:
            result = self.client.execute(query, params or {}, with_column_types=True)
            if not result:
                return pd.DataFrame()
            
            data, columns_with_types = result
            columns = [col[0] for col in columns_with_types]
            
            return pd.DataFrame(data, columns=columns)
        except Exception as e:
            logger.error(f"ClickHouse DataFrame query error: {e}")
            logger.error(f"Query: {query}")
            raise
    
    @with_metrics
    def insert_dataframe(self, table: str, df: pd.DataFrame, batch_size: int = 10000) -> bool:
        """Insert DataFrame into ClickHouse table in batches"""
        try:
            if df.empty:
                logger.warning(f"Empty DataFrame provided for table {table}")
                return True
            
            # Convert DataFrame to list of tuples for ClickHouse
            data = df.values.tolist()
            
            # Insert in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                query = f"INSERT INTO {table} VALUES"
                self.client.execute(query, batch)
            
            logger.info(f"Inserted {len(data)} rows into {table}")
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse insert error for table {table}: {e}")
            raise
    
    @with_metrics
    def get_market_data(self, symbol: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Get market data for symbol within time range"""
        query = """
        SELECT timestamp, symbol, price, volume, bid, ask
        FROM market_data 
        WHERE symbol = %(symbol)s 
          AND timestamp >= %(start_time)s 
          AND timestamp <= %(end_time)s
        ORDER BY timestamp
        """
        
        params = {
            'symbol': symbol,
            'start_time': start_time,
            'end_time': end_time
        }
        
        return self.query_dataframe(query, params)
    
    @with_metrics
    def get_latest_prices(self, symbols: List[str]) -> pd.DataFrame:
        """Get latest prices for multiple symbols"""
        query = """
        SELECT symbol, 
               argMax(price, timestamp) as latest_price,
               argMax(volume, timestamp) as latest_volume,
               argMax(timestamp, timestamp) as last_update
        FROM market_data
        WHERE symbol IN %(symbols)s
        GROUP BY symbol
        """
        
        return self.query_dataframe(query, {'symbols': symbols})
    
    def test_connection(self) -> bool:
        """Test ClickHouse connection"""
        try:
            result = self.execute_query("SELECT 1")
            return result == [[1]]
        except Exception as e:
            logger.error(f"ClickHouse connection test failed: {e}")
            return False
    
    def close(self) -> None:
        """Close ClickHouse connection and thread pool"""
        try:
            self.client.disconnect()
            self.executor.shutdown(wait=True)
        except Exception as e:
            logger.error(f"Error closing ClickHouse client: {e}")


# =============================================================================
# Unified Database Manager
# =============================================================================

class DatabaseManager:
    """
    Unified database management system providing:
    - Unified interface for all data access
    - Intelligent caching with Redis
    - Connection pooling and optimization
    - Health monitoring and failover
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize database manager with configuration"""
        self.config = config or self._load_default_config()
        self.metrics = None  # Will be injected from monitoring system
        
        # Initialize database clients
        self.clickhouse = ClickHouseClient(self.config.clickhouse)
        self.redis = RedisClient(self.config.redis)
        self.cache_strategy = CacheStrategy(self.redis)
        
        # Set metrics reference for clients
        if self.metrics:
            self.clickhouse.metrics = self.metrics
            self.redis.metrics = self.metrics
        
        # Health monitoring
        self._health_status = {
            'clickhouse': False,
            'redis': False,
            'last_check': None
        }
        
        logger.info("DatabaseManager initialized with ClickHouse, Redis, and intelligent caching")
    
    def _load_default_config(self) -> DatabaseConfig:
        """Load default database configuration"""
        try:
            from ..config import UnifiedConfigManager as ConfigManager
            config_manager = ConfigManager()
            
            return DatabaseConfig(
                clickhouse=config_manager.get_database_config(),
                redis={
                    'host': 'localhost',
                    'port': 6379,
                    'db': 0,
                    'decode_responses': False,
                    'max_connections': 20
                },
                cache={
                    'default_ttl': 300,
                    'max_memory': '1gb',
                    'compression': True
                }
            )
        except Exception as e:
            logger.warning(f"Could not load config, using defaults: {e}")
            return DatabaseConfig(
                clickhouse={'host': 'localhost', 'database': 'trading'},
                redis={'host': 'localhost', 'port': 6379, 'db': 0},
                cache={'default_ttl': 300}
            )
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all database connections"""
        try:
            # Test ClickHouse
            ch_healthy = self.clickhouse.test_connection()
            
            # Test Redis
            redis_healthy = await self.redis.ping()
            
            self._health_status = {
                'clickhouse': ch_healthy,
                'redis': redis_healthy,
                'last_check': datetime.now()
            }
            
            if self.metrics:
                self.metrics.set_gauge('database_clickhouse_healthy', 1 if ch_healthy else 0)
                self.metrics.set_gauge('database_redis_healthy', 1 if redis_healthy else 0)
            
            return self._health_status
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {'clickhouse': False, 'redis': False, 'last_check': datetime.now()}
    
    # Market Data Operations
    @with_cache(CacheType.MARKET_DATA, 300)
    async def get_market_data(self, symbol: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Get market data with intelligent caching"""
        return self.clickhouse.get_market_data(symbol, start_time, end_time)
    
    @with_cache(CacheType.MARKET_DATA, 60)
    async def get_latest_prices(self, symbols: List[str]) -> pd.DataFrame:
        """Get latest prices with short-term caching"""
        return self.clickhouse.get_latest_prices(symbols)
    
    async def store_market_data(self, df: pd.DataFrame) -> bool:
        """Store market data in ClickHouse"""
        try:
            success = self.clickhouse.insert_dataframe('market_data', df)
            
            # Invalidate related cache entries
            if success:
                symbols = df['symbol'].unique() if 'symbol' in df.columns else []
                for symbol in symbols:
                    await self.cache_strategy.invalidate_pattern(f"market_data:*{symbol}*")
            
            return success
        except Exception as e:
            logger.error(f"Error storing market data: {e}")
            return False
    
    # Signal Operations
    @with_cache(CacheType.SIGNALS, 60)
    async def get_signals(self, strategy: str, symbol: str, limit: int = 100) -> pd.DataFrame:
        """Get trading signals with caching"""
        query = """
        SELECT timestamp, symbol, signal_type, strength, metadata
        FROM trading_signals
        WHERE strategy = %(strategy)s AND symbol = %(symbol)s
        ORDER BY timestamp DESC
        LIMIT %(limit)s
        """
        
        params = {'strategy': strategy, 'symbol': symbol, 'limit': limit}
        return self.clickhouse.query_dataframe(query, params)
    
    async def store_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Store trading signal"""
        try:
            query = """
            INSERT INTO trading_signals 
            (timestamp, strategy, symbol, signal_type, strength, metadata)
            VALUES
            """
            
            data = [(
                signal_data.get('timestamp', datetime.now()),
                signal_data['strategy'],
                signal_data['symbol'],
                signal_data['signal_type'],
                signal_data['strength'],
                json.dumps(signal_data.get('metadata', {}))
            )]
            
            self.clickhouse.client.execute(query, data)
            
            # Invalidate signal cache
            symbol = signal_data['symbol']
            strategy = signal_data['strategy']
            await self.cache_strategy.invalidate_pattern(f"signals:*{strategy}*{symbol}*")
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing signal: {e}")
            return False
    
    # Analytics Operations
    @with_cache(CacheType.ANALYTICS, 900)
    async def get_performance_metrics(self, strategy: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Get performance metrics with long-term caching"""
        query = """
        SELECT 
            avg(pnl) as avg_pnl,
            sum(pnl) as total_pnl,
            stdDev(pnl) as pnl_std,
            count(*) as trade_count,
            sum(if(pnl > 0, 1, 0)) / count(*) as win_rate
        FROM strategy_performance
        WHERE strategy = %(strategy)s
          AND date >= %(start_date)s
          AND date <= %(end_date)s
        """
        
        params = {'strategy': strategy, 'start_date': start_date, 'end_date': end_date}
        result = self.clickhouse.query_dataframe(query, params)
        
        if not result.empty:
            return result.iloc[0].to_dict()
        return {}
    
    # Configuration Operations
    async def get_config(self, config_type: str, key: str) -> Optional[Any]:
        """Get configuration with Redis caching"""
        cache_key = f"config:{config_type}:{key}"
        
        # Try cache first
        cached_value = await self.cache_strategy.get(cache_key, CacheType.CONFIG)
        if cached_value is not None:
            return cached_value
        
        # Query ClickHouse
        query = "SELECT value FROM system_config WHERE type = %(type)s AND key = %(key)s"
        result = self.clickhouse.query_dataframe(query, {'type': config_type, 'key': key})
        
        if not result.empty:
            value = result.iloc[0]['value']
            # Store in cache
            await self.cache_strategy.set(cache_key, value, cache_type=CacheType.CONFIG)
            return value
        
        return None
    
    async def set_config(self, config_type: str, key: str, value: Any) -> bool:
        """Set configuration and update cache"""
        try:
            # Update ClickHouse
            query = """
            INSERT INTO system_config (type, key, value, updated_at)
            VALUES (%(type)s, %(key)s, %(value)s, %(updated_at)s)
            """
            
            params = {
                'type': config_type,
                'key': key,
                'value': json.dumps(value) if not isinstance(value, str) else value,
                'updated_at': datetime.now()
            }
            
            self.clickhouse.execute_query(query, params)
            
            # Update cache
            cache_key = f"config:{config_type}:{key}"
            await self.cache_strategy.set(cache_key, value, cache_type=CacheType.CONFIG)
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting config {config_type}:{key}: {e}")
            return False
    
    # Utility Methods
    async def warm_caches(self) -> None:
        """Warm up caches with frequently accessed data"""
        try:
            logger.info("Starting cache warming process")
            
            # Warm market data cache
            await self.cache_strategy.warm_cache(
                CacheType.MARKET_DATA,
                lambda: self._load_recent_market_data()
            )
            
            # Warm config cache
            await self.cache_strategy.warm_cache(
                CacheType.CONFIG,
                lambda: self._load_system_configs()
            )
            
            logger.info("Cache warming completed")
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
    
    async def _load_recent_market_data(self) -> Dict[str, Any]:
        """Load recent market data for cache warming"""
        try:
            query = """
            SELECT symbol, argMax(price, timestamp) as price
            FROM market_data
            WHERE timestamp >= now() - INTERVAL 1 HOUR
            GROUP BY symbol
            """
            
            result = self.clickhouse.query_dataframe(query)
            return result.set_index('symbol')['price'].to_dict()
        except Exception:
            return {}
    
    async def _load_system_configs(self) -> Dict[str, Any]:
        """Load system configurations for cache warming"""
        try:
            query = "SELECT type, key, value FROM system_config WHERE active = 1"
            result = self.clickhouse.query_dataframe(query)
            
            configs = {}
            for _, row in result.iterrows():
                config_key = f"{row['type']}:{row['key']}"
                configs[config_key] = row['value']
            
            return configs
        except Exception:
            return {}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        return self.cache_strategy.get_stats()
    
    async def close(self) -> None:
        """Close all database connections"""
        try:
            await self.redis.close()
            self.clickhouse.close()
            logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")


# =============================================================================
# Database System Factory
# =============================================================================

class DatabaseSystemFactory:
    """Factory for creating database system components"""
    
    @staticmethod
    def create_production_database_system() -> DatabaseManager:
        """Create database system for production environment"""
        config = DatabaseConfig(
            clickhouse={
                'host': 'clickhouse.prod.local',
                'port': 9000,
                'database': 'trading_prod',
                'user': 'trading_user',
                'password': 'secure_password',
                'connect_timeout': 10,
                'send_receive_timeout': 600,
                'settings': {
                    'max_execution_time': 600,
                    'max_memory_usage': 4000000000,  # 4GB
                    'use_uncompressed_cache': 1,
                    'max_threads': 8
                }
            },
            redis={
                'host': 'redis.prod.local',
                'port': 6379,
                'db': 0,
                'password': 'redis_password',
                'max_connections': 50,
                'socket_keepalive': True,
                'health_check_interval': 30
            },
            cache={
                'default_ttl': 300,
                'max_memory': '2gb',
                'compression': True
            }
        )
        
        return DatabaseManager(config)
    
    @staticmethod
    def create_development_database_system() -> DatabaseManager:
        """Create database system for development environment"""
        config = DatabaseConfig(
            clickhouse={
                'host': 'localhost',
                'port': 9000,
                'database': 'polygon_data',
                'user': 'default',
                'password': '',
                'connect_timeout': 5,
                'send_receive_timeout': 60,
                'settings': {
                    'max_execution_time': 60,
                    'max_memory_usage': 1000000000,  # 1GB
                }
            },
            redis={
                'host': 'localhost',
                'port': 6379,
                'db': 1,  # Use different DB for dev
                'max_connections': 10
            },
            cache={
                'default_ttl': 60,
                'compression': False
            }
        )
        
        return DatabaseManager(config)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Core Systems
    'DatabaseManager',
    'ClickHouseClient',
    'RedisClient',
    'CacheStrategy',
    
    # Configuration
    'DatabaseConfig',
    'CacheConfig',
    
    # Enums
    'CacheType',
    
    # Factory
    'DatabaseSystemFactory',
    
    # Decorators
    'with_metrics',
    'with_cache'
]
