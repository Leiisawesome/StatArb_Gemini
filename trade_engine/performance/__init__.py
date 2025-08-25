"""
Performance optimization module for the trade engine.

This module provides comprehensive performance optimization capabilities including:
- Template loading and caching optimization
- Signal generation performance tuning
- Memory usage optimization
- Real-time performance monitoring
"""

from .optimization_engine import PerformanceOptimizationEngine
from .profiler import SystemProfiler
from .cache_manager import OptimizedCacheManager

__all__ = [
    'PerformanceOptimizationEngine',
    'SystemProfiler', 
    'OptimizedCacheManager'
]
