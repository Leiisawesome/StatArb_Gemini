"""
Optimization Module - Performance & Efficiency
==============================================

This module contains all performance optimization features for the UnifiedTradingEngine.
Consolidates hot path optimization, memory management, and async features.

Components:
- performance.py: Hot path optimization and performance monitoring
- memory.py: Memory management and object pooling
- async_features.py: Asynchronous optimization and concurrency

Author: Professional Trading System Architecture
Version: PRODUCTION (Reorganized)
"""

# Performance Optimizations
from .performance import (
    optimize_signal_generation, 
    optimize_order_execution, 
    optimize_portfolio_update, 
    optimize_risk_calculation,
    performance_monitor, 
    PerformanceMonitor,
    get_performance_summary, 
    get_cache_statistics, 
    clear_all_caches,
    batch_processor, 
    CircularBuffer, 
    FastDataFrame
)

# Memory Management
from .memory import (
    PoolManager,
    MemoryMonitor,
    MemoryOptimizer,
    ObjectPool,
    PoolStatistics
)

# Async Features
from .async_features import (
    AsyncPerformanceMonitor,
    ConcurrencyLimiter,
    AsyncBatchProcessor,
    AsyncEventBus,
    AsyncTradingOperations,
    AsyncTaskManager
)

__all__ = [
    # Performance
    'optimize_signal_generation',
    'optimize_order_execution', 
    'optimize_portfolio_update',
    'optimize_risk_calculation',
    'performance_monitor',
    'get_performance_summary',
    'get_cache_statistics',
    'clear_all_caches',
    'batch_processor',
    'CircularBuffer',
    'FastDataFrame',
    'PerformanceMonitor',
    
    # Memory
    'PoolManager',
    'MemoryMonitor',
    'MemoryOptimizer',
    'ObjectPool',
    'PoolStatistics',
    
    # Async
    'AsyncPerformanceMonitor',
    'ConcurrencyLimiter',
    'AsyncBatchProcessor', 
    'AsyncEventBus',
    'AsyncTradingOperations',
    'AsyncTaskManager'
]
