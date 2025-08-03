"""
Unified Database Management Layer

Provides a single interface for all database operations including:
- ClickHouse for time-series market data
- Redis for caching and real-time data
- Unified query interface with automatic optimization
- Connection pooling and health monitoring

Author: Pro Quant Desk Trader
"""

from typing import Dict, List, Optional, Any, Union
import asyncio
import logging
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass

from .clickhouse_client import ClickHouseClient
from .redis_client import RedisClient
from .cache_strategy import CacheStrategy
from ..config import ConfigManager
from ..monitoring import MetricsCollector

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration container"""
    clickhouse: Dict[str, Any]
    redis: Dict[str, Any]
    cache: Dict[str, Any]

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
        self.metrics = MetricsCollector()
        
        # Initialize database clients
        self.clickhouse = ClickHouseClient(self.config.clickhouse)
        self.redis = RedisClient(self.config.redis)
        self.cache_strategy = CacheStrategy(self.config.cache)
        
        logger.info("DatabaseManager initialized with unified interface")
    
    def _load_default_config(self) -> DatabaseConfig:
        """Load default database configuration"""
        config_manager = ConfigManager()
        return DatabaseConfig(
            clickhouse=config_manager.get_database_config().get('clickhouse', {}),
            redis=config_manager.get_database_config().get('redis', {}),
            cache=config_manager.get_database_config().get('cache', {})
        )
    
    async def get_market_data(self, 
                            symbols: List[str], 
                            start_date: datetime, 
                            end_date: datetime,
                            use_cache: bool = True) -> pd.DataFrame:
        """
        Unified market data retrieval with intelligent caching
        
        Args:
            symbols: List of trading symbols
            start_date: Start date for data
            end_date: End date for data
            use_cache: Whether to use Redis cache
            
        Returns:
            DataFrame with market data
        """
        cache_key = self._generate_cache_key('market_data', symbols, start_date, end_date)
        
        # Try cache first if enabled
        if use_cache:
            cached_data = await self.redis.get_dataframe(cache_key)
            if cached_data is not None:
                self.metrics.increment_counter('database_cache_hit')
                return cached_data
        
        # Fetch from ClickHouse
        data = await self.clickhouse.get_market_data(symbols, start_date, end_date)
        
        # Cache result if enabled
        if use_cache and not data.empty:
            cache_ttl = self.cache_strategy.get_ttl('market_data')
            await self.redis.set_dataframe(cache_key, data, ttl=cache_ttl)
            self.metrics.increment_counter('database_cache_miss')
        
        return data
    
    async def get_real_time_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get real-time market data from Redis cache
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            Dictionary with real-time data
        """
        real_time_data = {}
        
        for symbol in symbols:
            cache_key = f"realtime:{symbol}"
            data = await self.redis.get_json(cache_key)
            if data:
                real_time_data[symbol] = data
        
        return real_time_data
    
    async def store_real_time_data(self, symbol: str, data: Dict[str, Any]):
        """
        Store real-time market data in Redis
        
        Args:
            symbol: Trading symbol
            data: Real-time data to store
        """
        cache_key = f"realtime:{symbol}"
        ttl = self.cache_strategy.get_ttl('realtime')
        await self.redis.set_json(cache_key, data, ttl=ttl)
    
    async def get_signals(self, 
                         strategy: str, 
                         symbols: List[str], 
                         start_date: datetime,
                         end_date: datetime) -> pd.DataFrame:
        """
        Get trading signals with caching
        
        Args:
            strategy: Strategy name
            symbols: List of symbols
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with signals
        """
        cache_key = self._generate_cache_key('signals', [strategy] + symbols, start_date, end_date)
        
        # Check cache first
        cached_signals = await self.redis.get_dataframe(cache_key)
        if cached_signals is not None:
            return cached_signals
        
        # Query from ClickHouse
        signals = await self.clickhouse.get_signals(strategy, symbols, start_date, end_date)
        
        # Cache results
        if not signals.empty:
            cache_ttl = self.cache_strategy.get_ttl('signals')
            await self.redis.set_dataframe(cache_key, signals, ttl=cache_ttl)
        
        return signals
    
    async def store_signals(self, signals: pd.DataFrame, strategy: str):
        """
        Store trading signals in ClickHouse
        
        Args:
            signals: DataFrame with signals
            strategy: Strategy name
        """
        await self.clickhouse.insert_signals(signals, strategy)
        
        # Invalidate related cache entries
        await self._invalidate_cache_pattern(f"signals:{strategy}:*")
    
    async def get_portfolio_data(self, 
                               portfolio_id: str, 
                               start_date: datetime,
                               end_date: datetime) -> pd.DataFrame:
        """
        Get portfolio data with caching
        
        Args:
            portfolio_id: Portfolio identifier
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with portfolio data
        """
        cache_key = f"portfolio:{portfolio_id}:{start_date.isoformat()}:{end_date.isoformat()}"
        
        # Check cache
        cached_data = await self.redis.get_dataframe(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Query database
        data = await self.clickhouse.get_portfolio_data(portfolio_id, start_date, end_date)
        
        # Cache results
        if not data.empty:
            cache_ttl = self.cache_strategy.get_ttl('portfolio')
            await self.redis.set_dataframe(cache_key, data, ttl=cache_ttl)
        
        return data
    
    async def store_execution_data(self, execution_data: Dict[str, Any]):
        """
        Store execution data in ClickHouse
        
        Args:
            execution_data: Execution information
        """
        await self.clickhouse.insert_execution_data(execution_data)
    
    async def get_performance_metrics(self, 
                                    strategy: str, 
                                    start_date: datetime,
                                    end_date: datetime) -> Dict[str, Any]:
        """
        Get performance metrics with intelligent caching
        
        Args:
            strategy: Strategy name
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with performance metrics
        """
        cache_key = f"performance:{strategy}:{start_date.isoformat()}:{end_date.isoformat()}"
        
        # Check cache
        cached_metrics = await self.redis.get_json(cache_key)
        if cached_metrics is not None:
            return cached_metrics
        
        # Calculate metrics from database
        metrics = await self.clickhouse.calculate_performance_metrics(strategy, start_date, end_date)
        
        # Cache results
        cache_ttl = self.cache_strategy.get_ttl('performance')
        await self.redis.set_json(cache_key, metrics, ttl=cache_ttl)
        
        return metrics
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Perform health check on all database connections
        
        Returns:
            Dictionary with health status
        """
        health_status = {}
        
        try:
            # Check ClickHouse
            await self.clickhouse.ping()
            health_status['clickhouse'] = True
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            health_status['clickhouse'] = False
        
        try:
            # Check Redis
            await self.redis.ping()
            health_status['redis'] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health_status['redis'] = False
        
        health_status['overall'] = all(health_status.values())
        
        return health_status
    
    def is_connected(self) -> bool:
        """
        Check if database connections are available
        
        Returns:
            Boolean indicating if connections are available
        """
        try:
            # For now, return True as a mock implementation
            # In production, this would check actual connection status
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    def _generate_cache_key(self, 
                           data_type: str, 
                           identifiers: List[str], 
                           start_date: datetime, 
                           end_date: datetime) -> str:
        """Generate cache key for data requests"""
        ids_str = "_".join(sorted(identifiers))
        return f"{data_type}:{ids_str}:{start_date.isoformat()}:{end_date.isoformat()}"
    
    async def _invalidate_cache_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        await self.redis.delete_pattern(pattern)
    
    async def close(self):
        """Close all database connections"""
        await self.clickhouse.close()
        await self.redis.close()
        logger.info("DatabaseManager connections closed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
