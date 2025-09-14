#!/usr/bin/env python3
"""
Analytics Database Connection Pool
=================================

Specialized database connection pool for analytics workloads with:
- Connection pooling for high-frequency analytics operations
- Batch operation optimization
- Connection health monitoring
- Automatic retry and failover logic

Author: Professional Trading System Architecture
Version: 1.0.0
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import threading
from collections import deque
import queue

# Import existing database infrastructure
from ..infrastructure.database.database_system import DatabaseManager, DatabaseConfig

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolConfig:
    """Configuration for analytics database connection pool"""
    pool_size: int = 15  # Larger pool for analytics workloads
    max_overflow: int = 25  # Allow bursts during heavy analytics
    pool_timeout: int = 30  # Connection acquisition timeout
    health_check_interval: int = 60  # Health check frequency in seconds
    retry_attempts: int = 3  # Number of retry attempts for failed operations
    connection_lifetime: int = 3600  # Max connection lifetime in seconds
    batch_size: int = 1000  # Default batch size for bulk operations


class AnalyticsConnectionPool:
    """
    Specialized connection pool for analytics operations with enhanced features:
    - Connection lifecycle management
    - Health monitoring and automatic recovery
    - Batch operation optimization
    - Performance metrics tracking
    """
    
    def __init__(self, database_manager: DatabaseManager, 
                 config: Optional[ConnectionPoolConfig] = None):
        """Initialize analytics connection pool"""
        self.database_manager = database_manager
        self.config = config or ConnectionPoolConfig()
        
        # Connection pool management
        self._available_connections = asyncio.Queue(maxsize=self.config.pool_size)
        self._overflow_connections = deque()
        self._connection_timestamps = {}
        self._connection_health = {}
        self._pool_lock = asyncio.Lock()
        
        # Metrics tracking
        self._active_connections = 0
        self._total_requests = 0
        self._failed_requests = 0
        self._pool_wait_times = deque(maxlen=1000)
        
        # Background tasks
        self._health_check_task = None
        self._cleanup_task = None
        self._running = False
        
        logger.info(f"AnalyticsConnectionPool initialized: pool_size={self.config.pool_size}, "
                   f"max_overflow={self.config.max_overflow}")
    
    async def start(self) -> None:
        """Start the connection pool and background tasks"""
        if self._running:
            return
            
        self._running = True
        
        # Pre-populate the connection pool
        await self._populate_pool()
        
        # Start background health monitoring
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("AnalyticsConnectionPool started")
    
    async def stop(self) -> None:
        """Stop the connection pool and cleanup resources"""
        self._running = False
        
        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Close all connections
        await self._cleanup_all_connections()
        
        logger.info("AnalyticsConnectionPool stopped")
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Get a database connection from the pool
        
        Usage:
            async with pool.get_connection() as conn:
                result = await conn.execute(query)
        """
        start_time = time.time()
        connection = None
        
        try:
            # Acquire connection from pool
            connection = await self._acquire_connection()
            
            # Track wait time
            wait_time = time.time() - start_time
            self._pool_wait_times.append(wait_time)
            
            # Yield connection for use
            yield connection
            
        except Exception as e:
            self._failed_requests += 1
            logger.error(f"Error with pooled connection: {e}")
            raise
        finally:
            # Return connection to pool
            if connection:
                await self._release_connection(connection)
    
    async def execute_batch(self, queries: List[str], 
                          params_list: Optional[List[Dict]] = None) -> List[Any]:
        """
        Execute multiple queries in a single connection for efficiency
        
        Args:
            queries: List of SQL queries to execute
            params_list: Optional list of parameters for each query
            
        Returns:
            List of query results
        """
        if not queries:
            return []
        
        params_list = params_list or [{}] * len(queries)
        results = []
        
        async with self.get_connection() as conn:
            for i, query in enumerate(queries):
                try:
                    params = params_list[i] if i < len(params_list) else {}
                    result = await conn.execute(query, params)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch query {i} failed: {e}")
                    results.append(None)
        
        return results
    
    async def execute_with_retry(self, query: str, params: Optional[Dict] = None,
                               max_retries: Optional[int] = None) -> Any:
        """
        Execute query with automatic retry logic
        
        Args:
            query: SQL query to execute
            params: Query parameters
            max_retries: Maximum retry attempts (defaults to config value)
            
        Returns:
            Query result
        """
        max_retries = max_retries or self.config.retry_attempts
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                async with self.get_connection() as conn:
                    return await conn.execute(query, params or {})
                    
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                    logger.warning(f"Query attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Query failed after {max_retries + 1} attempts: {e}")
        
        raise last_error
    
    async def _acquire_connection(self):
        """Acquire a connection from the pool"""
        self._total_requests += 1
        
        try:
            # Try to get from main pool (non-blocking)
            connection = self._available_connections.get_nowait()
            self._active_connections += 1
            return connection
            
        except asyncio.QueueEmpty:
            # Main pool is empty, check overflow
            async with self._pool_lock:
                if len(self._overflow_connections) < self.config.max_overflow:
                    # Create overflow connection
                    connection = self.database_manager
                    self._overflow_connections.append(connection)
                    self._connection_timestamps[id(connection)] = time.time()
                    self._active_connections += 1
                    return connection
        
        # Pool and overflow are full, wait for connection
        try:
            connection = await asyncio.wait_for(
                self._available_connections.get(),
                timeout=self.config.pool_timeout
            )
            self._active_connections += 1
            return connection
            
        except asyncio.TimeoutError:
            raise RuntimeError(f"Pool timeout: no connection available after {self.config.pool_timeout}s")
    
    async def _release_connection(self, connection):
        """Release a connection back to the pool"""
        self._active_connections = max(0, self._active_connections - 1)
        
        # Check if this is an overflow connection
        conn_id = id(connection)
        if conn_id in self._connection_timestamps:
            async with self._pool_lock:
                if connection in self._overflow_connections:
                    # Remove from overflow if connection is old
                    age = time.time() - self._connection_timestamps[conn_id]
                    if age > self.config.connection_lifetime:
                        self._overflow_connections.remove(connection)
                        del self._connection_timestamps[conn_id]
                        return  # Don't return to pool, let it be garbage collected
        
        # Return to main pool if space available
        try:
            self._available_connections.put_nowait(connection)
        except asyncio.QueueFull:
            # Pool is full, connection will be discarded
            pass
    
    async def _populate_pool(self) -> None:
        """Pre-populate the connection pool"""
        for _ in range(self.config.pool_size):
            try:
                # Use the same database manager instance (it handles connection pooling internally)
                connection = self.database_manager
                await self._available_connections.put(connection)
            except Exception as e:
                logger.error(f"Failed to populate connection pool: {e}")
                break
    
    async def _health_check_loop(self) -> None:
        """Background task for health monitoring"""
        while self._running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _cleanup_loop(self) -> None:
        """Background task for connection cleanup"""
        while self._running:
            try:
                await self._cleanup_expired_connections()
                await asyncio.sleep(300)  # Run every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(60)
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on database connections"""
        try:
            health_status = await self.database_manager.health_check()
            self._connection_health.update(health_status)
            
            if not all(health_status.values()):
                logger.warning(f"Database health check failed: {health_status}")
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _cleanup_expired_connections(self) -> None:
        """Clean up expired overflow connections"""
        current_time = time.time()
        expired_connections = []
        
        async with self._pool_lock:
            for connection in list(self._overflow_connections):
                conn_id = id(connection)
                if conn_id in self._connection_timestamps:
                    age = current_time - self._connection_timestamps[conn_id]
                    if age > self.config.connection_lifetime:
                        expired_connections.append((connection, conn_id))
            
            # Remove expired connections
            for connection, conn_id in expired_connections:
                self._overflow_connections.remove(connection)
                del self._connection_timestamps[conn_id]
        
        if expired_connections:
            logger.debug(f"Cleaned up {len(expired_connections)} expired connections")
    
    async def _cleanup_all_connections(self) -> None:
        """Clean up all connections during shutdown"""
        # Clear the queue
        while not self._available_connections.empty():
            try:
                self._available_connections.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        # Clear overflow connections
        async with self._pool_lock:
            self._overflow_connections.clear()
            self._connection_timestamps.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        avg_wait_time = (
            sum(self._pool_wait_times) / len(self._pool_wait_times)
            if self._pool_wait_times else 0
        )
        
        return {
            'pool_size': self.config.pool_size,
            'active_connections': self._active_connections,
            'available_connections': self._available_connections.qsize(),
            'overflow_connections': len(self._overflow_connections),
            'total_requests': self._total_requests,
            'failed_requests': self._failed_requests,
            'failure_rate': (
                self._failed_requests / self._total_requests
                if self._total_requests > 0 else 0
            ),
            'average_wait_time_ms': avg_wait_time * 1000,
            'health_status': self._connection_health.copy()
        }


# Singleton instance for analytics modules
_analytics_pool = None
_pool_lock = threading.Lock()


async def get_analytics_pool(database_manager: DatabaseManager,
                           config: Optional[ConnectionPoolConfig] = None) -> AnalyticsConnectionPool:
    """
    Get or create the analytics connection pool singleton
    
    Args:
        database_manager: Database manager instance
        config: Optional pool configuration
        
    Returns:
        Analytics connection pool instance
    """
    global _analytics_pool
    
    with _pool_lock:
        if _analytics_pool is None:
            _analytics_pool = AnalyticsConnectionPool(database_manager, config)
            await _analytics_pool.start()
    
    return _analytics_pool


async def shutdown_analytics_pool() -> None:
    """Shutdown the analytics connection pool"""
    global _analytics_pool
    
    with _pool_lock:
        if _analytics_pool:
            await _analytics_pool.stop()
            _analytics_pool = None


# Context manager for easy usage
@asynccontextmanager
async def analytics_db_connection(database_manager: DatabaseManager):
    """
    Context manager for analytics database connections
    
    Usage:
        async with analytics_db_connection(db_manager) as conn:
            result = await conn.execute(query)
    """
    pool = await get_analytics_pool(database_manager)
    async with pool.get_connection() as conn:
        yield conn


# Utility functions for common analytics operations
async def execute_analytics_query(database_manager: DatabaseManager,
                                query: str,
                                params: Optional[Dict] = None) -> Any:
    """Execute a single analytics query with connection pooling"""
    async with analytics_db_connection(database_manager) as conn:
        return await conn.execute(query, params or {})


async def execute_analytics_batch(database_manager: DatabaseManager,
                                queries: List[str],
                                params_list: Optional[List[Dict]] = None) -> List[Any]:
    """Execute multiple analytics queries in batch"""
    pool = await get_analytics_pool(database_manager)
    return await pool.execute_batch(queries, params_list)


__all__ = [
    'AnalyticsConnectionPool',
    'ConnectionPoolConfig',
    'get_analytics_pool',
    'shutdown_analytics_pool',
    'analytics_db_connection',
    'execute_analytics_query',
    'execute_analytics_batch'
]