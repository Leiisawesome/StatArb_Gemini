"""
Unified Database Infrastructure
==============================

Phase 5C Infrastructure Consolidation - Database Module
Consolidated database functionality into a unified system.

This module provides comprehensive database capabilities including:
- High-performance ClickHouse operations for time-series data
- Redis caching with intelligent TTL management
- Unified database management with connection pooling
- Advanced caching strategies with warming and invalidation

Consolidated Components:
- database_system: Unified database management (from clickhouse_client + redis_client + database_manager + cache_strategy)

Legacy Support:
- Individual component imports maintained for backward compatibility
"""

# Phase 5C Consolidated System
from .database_system import (
    DatabaseManager,
    ClickHouseClient,
    RedisClient,
    CacheStrategy,
    DatabaseSystemFactory,
    DatabaseConfig,
    CacheConfig,
    CacheType,
    with_metrics,
    with_cache
)

# Legacy backward compatibility imports
# Note: These now reference the consolidated modules
from .database_system import DatabaseManager, ClickHouseClient, RedisClient

__all__ = [
    # Core Systems
    'DatabaseManager',
    'ClickHouseClient', 
    'RedisClient',
    'CacheStrategy',
    
    # Factory
    'DatabaseSystemFactory',
    
    # Configuration
    'DatabaseConfig',
    'CacheConfig',
    
    # Types
    'CacheType',
    
    # Decorators
    'with_metrics',
    'with_cache'
] 