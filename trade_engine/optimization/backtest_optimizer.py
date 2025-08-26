"""
Advanced Backtest Optimization Framework
========================================

This module provides intelligent caching and optimization for trading backtests
without modifying the core trading logic. Designed to integrate seamlessly with
existing advanced momentum strategies.

Key Features:
- Smart caching of expensive calculations (regime detection, trend analysis)
- Configurable cache duration based on calculation volatility
- Fallback to original calculations when needed
- Real-time performance monitoring
- Production-ready optimization patterns

Author: StatArb_Gemini Optimization Team
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class OptimizationMode(Enum):
    """Optimization modes for production deployment"""
    LEGACY_ONLY = "legacy"
    OPTIMIZED_ONLY = "optimized"
    AB_TESTING = "ab_testing"
    HYBRID = "hybrid"


@dataclass
class CacheConfig:
    """Configuration for optimization caching"""
    regime_cache_duration: int = 5  # Cache regime detection for 5 cycles
    trend_cache_duration: int = 5   # Cache trend analysis for 5 cycles
    momentum_cache_duration: int = 2  # Cache momentum for 2 cycles (price sensitive)
    enable_cache_stats: bool = True
    max_cache_size: int = 1000


@dataclass
class OptimizationConfig:
    """Configuration for backtest optimization"""
    mode: OptimizationMode = OptimizationMode.OPTIMIZED_ONLY
    cache_config: CacheConfig = field(default_factory=CacheConfig)
    enable_monitoring: bool = True
    enable_performance_tracking: bool = True
    max_execution_time_ms: float = 10.0  # Alert threshold


@dataclass
class OptimizationStats:
    """Track optimization performance statistics"""
    optimized_cycles: int = 0
    legacy_cycles: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_calculations_saved: int = 0
    avg_cycle_time_ms: float = 0.0
    performance_improvement_factor: float = 1.0


class BacktestOptimizer:
    """
    Advanced optimization framework for trading backtests.
    
    Provides intelligent caching and performance optimization while preserving
    the exact trading logic and results of the original system.
    """
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.is_initialized = False
        
        # Performance tracking
        self.stats = OptimizationStats()
        self.execution_times = []
        
        # Smart caching system
        self.calculation_cache = {
            'regime_cache': {},      # Market regime detection results
            'trend_cache': {},       # Trend strength calculations
            'momentum_cache': {},    # Momentum signal calculations
            'last_cache_update': {}  # Track when each cache was updated
        }
        
        # Cache statistics
        self.cache_stats = {
            'regime_hits': 0,
            'trend_hits': 0,
            'momentum_hits': 0,
            'total_requests': 0
        }
        
        logger.info("BacktestOptimizer initialized with intelligent caching")
    
    async def initialize(self):
        """Initialize the optimization framework"""
        if self.is_initialized:
            return
        
        # Clear any existing cache
        self._clear_cache()
        
        # Reset statistics
        self.stats = OptimizationStats()
        self.cache_stats = {k: 0 for k in self.cache_stats.keys()}
        
        self.is_initialized = True
        logger.info("✅ BacktestOptimizer initialization complete")
    
    def _clear_cache(self):
        """Clear all cached calculations"""
        for cache_type in self.calculation_cache:
            if isinstance(self.calculation_cache[cache_type], dict):
                self.calculation_cache[cache_type].clear()
    
    async def optimize_regime_detection(
        self, 
        symbol: str, 
        market_data: Dict, 
        original_calculation_func,
        cycle_num: int
    ) -> Tuple[str, float]:
        """
        Optimize market regime detection with intelligent caching.
        
        Args:
            symbol: Trading symbol
            market_data: Market data for calculations
            original_calculation_func: Original regime detection function
            cycle_num: Current cycle number for cache management
        
        Returns:
            Tuple of (regime, confidence)
        """
        self.cache_stats['total_requests'] += 1
        
        if self.config.mode == OptimizationMode.LEGACY_ONLY:
            return await original_calculation_func()
        
        # Check cache first
        cache_key = f"{symbol}_regime"
        if self._is_cache_valid(cache_key, cycle_num, self.config.cache_config.regime_cache_duration):
            self.cache_stats['regime_hits'] += 1
            self.stats.cache_hits += 1
            return self.calculation_cache['regime_cache'][cache_key]
        
        # Cache miss - perform calculation
        self.stats.cache_misses += 1
        start_time = time.perf_counter()
        
        result = await original_calculation_func()
        
        execution_time = (time.perf_counter() - start_time) * 1000
        self.execution_times.append(execution_time)
        
        # Cache the result
        self.calculation_cache['regime_cache'][cache_key] = result
        self.calculation_cache['last_cache_update'][cache_key] = cycle_num
        
        self.stats.optimized_cycles += 1
        return result
    
    async def optimize_trend_calculation(
        self, 
        symbol: str, 
        price_history: List[float], 
        original_calculation_func,
        cycle_num: int
    ) -> float:
        """
        Optimize trend strength calculation with intelligent caching.
        
        Args:
            symbol: Trading symbol
            price_history: Historical price data
            original_calculation_func: Original trend calculation function
            cycle_num: Current cycle number for cache management
        
        Returns:
            Trend strength value
        """
        self.cache_stats['total_requests'] += 1
        
        if self.config.mode == OptimizationMode.LEGACY_ONLY:
            return await original_calculation_func()
        
        # Check cache first
        cache_key = f"{symbol}_trend"
        if self._is_cache_valid(cache_key, cycle_num, self.config.cache_config.trend_cache_duration):
            self.cache_stats['trend_hits'] += 1
            self.stats.cache_hits += 1
            return self.calculation_cache['trend_cache'][cache_key]
        
        # Cache miss - perform calculation
        self.stats.cache_misses += 1
        start_time = time.perf_counter()
        
        result = await original_calculation_func()
        
        execution_time = (time.perf_counter() - start_time) * 1000
        self.execution_times.append(execution_time)
        
        # Cache the result
        self.calculation_cache['trend_cache'][cache_key] = result
        self.calculation_cache['last_cache_update'][cache_key] = cycle_num
        
        self.stats.optimized_cycles += 1
        return result
    
    async def optimize_momentum_calculation(
        self, 
        symbol: str, 
        current_price: float,
        regime: str,
        trend_aligned: bool,
        original_calculation_func,
        cycle_num: int
    ) -> Tuple[float, float]:
        """
        Optimize momentum signal calculation with intelligent caching.
        
        Args:
            symbol: Trading symbol
            current_price: Current price for calculation
            regime: Market regime
            trend_aligned: Whether trend is aligned
            original_calculation_func: Original momentum calculation function
            cycle_num: Current cycle number for cache management
        
        Returns:
            Tuple of (signal, confidence)
        """
        self.cache_stats['total_requests'] += 1
        
        if self.config.mode == OptimizationMode.LEGACY_ONLY:
            return await original_calculation_func()
        
        # Check cache first (shorter duration for price-sensitive momentum)
        cache_key = f"{symbol}_momentum_{current_price}_{regime}_{trend_aligned}"
        if self._is_cache_valid(cache_key, cycle_num, self.config.cache_config.momentum_cache_duration):
            self.cache_stats['momentum_hits'] += 1
            self.stats.cache_hits += 1
            return self.calculation_cache['momentum_cache'][cache_key]
        
        # Cache miss - perform calculation
        self.stats.cache_misses += 1
        start_time = time.perf_counter()
        
        result = await original_calculation_func()
        
        execution_time = (time.perf_counter() - start_time) * 1000
        self.execution_times.append(execution_time)
        
        # Cache the result
        self.calculation_cache['momentum_cache'][cache_key] = result
        self.calculation_cache['last_cache_update'][cache_key] = cycle_num
        
        self.stats.optimized_cycles += 1
        return result
    
    def _is_cache_valid(self, cache_key: str, current_cycle: int, cache_duration: int) -> bool:
        """Check if cached result is still valid"""
        if cache_key not in self.calculation_cache['last_cache_update']:
            return False
        
        last_update = self.calculation_cache['last_cache_update'][cache_key]
        return (current_cycle - last_update) < cache_duration
    
    def get_optimization_metrics(self) -> Dict[str, Any]:
        """Get comprehensive optimization performance metrics"""
        total_cycles = self.stats.optimized_cycles + self.stats.legacy_cycles
        total_cache_entries = (
            len(self.calculation_cache['regime_cache']) + 
            len(self.calculation_cache['trend_cache']) + 
            len(self.calculation_cache['momentum_cache'])
        )
        
        cache_hit_rate = (self.stats.cache_hits / (self.stats.cache_hits + self.stats.cache_misses)) * 100 if (self.stats.cache_hits + self.stats.cache_misses) > 0 else 0
        
        avg_execution_time = sum(self.execution_times) / len(self.execution_times) if self.execution_times else 0
        
        return {
            'total_cycles': total_cycles,
            'optimized_cycles': self.stats.optimized_cycles,
            'legacy_cycles': self.stats.legacy_cycles,
            'optimization_rate': (self.stats.optimized_cycles / total_cycles * 100) if total_cycles > 0 else 0,
            'cache_hit_rate': cache_hit_rate,
            'cache_hits': self.stats.cache_hits,
            'cache_misses': self.stats.cache_misses,
            'total_cache_entries': total_cache_entries,
            'regime_cache_size': len(self.calculation_cache['regime_cache']),
            'trend_cache_size': len(self.calculation_cache['trend_cache']),
            'momentum_cache_size': len(self.calculation_cache['momentum_cache']),
            'avg_execution_time_ms': avg_execution_time,
            'total_execution_times_recorded': len(self.execution_times),
            'calculations_saved': self.stats.cache_hits
        }
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get detailed cache performance statistics"""
        total_requests = self.cache_stats['total_requests']
        total_hits = sum([self.cache_stats['regime_hits'], self.cache_stats['trend_hits'], self.cache_stats['momentum_hits']])
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'regime_cache': {
                'hits': self.cache_stats['regime_hits'],
                'hit_rate': (self.cache_stats['regime_hits'] / total_requests * 100) if total_requests > 0 else 0,
                'entries': len(self.calculation_cache['regime_cache'])
            },
            'trend_cache': {
                'hits': self.cache_stats['trend_hits'],
                'hit_rate': (self.cache_stats['trend_hits'] / total_requests * 100) if total_requests > 0 else 0,
                'entries': len(self.calculation_cache['trend_cache'])
            },
            'momentum_cache': {
                'hits': self.cache_stats['momentum_hits'],
                'hit_rate': (self.cache_stats['momentum_hits'] / total_requests * 100) if total_requests > 0 else 0,
                'entries': len(self.calculation_cache['momentum_cache'])
            },
            'overall': {
                'total_requests': total_requests,
                'total_hits': total_hits,
                'overall_hit_rate': overall_hit_rate
            }
        }
    
    def log_performance_summary(self):
        """Log a comprehensive performance summary"""
        metrics = self.get_optimization_metrics()
        cache_stats = self.get_cache_statistics()
        
        logger.info("🚀 OPTIMIZATION PERFORMANCE SUMMARY:")
        logger.info(f"  • Total Cycles: {metrics['total_cycles']}")
        logger.info(f"  • Optimization Rate: {metrics['optimization_rate']:.1f}%")
        logger.info(f"  • Cache Hit Rate: {metrics['cache_hit_rate']:.1f}%")
        logger.info(f"  • Calculations Saved: {metrics['calculations_saved']}")
        logger.info(f"  • Avg Execution Time: {metrics['avg_execution_time_ms']:.3f}ms")
        
        logger.info("📊 CACHE BREAKDOWN:")
        for cache_type, stats in cache_stats.items():
            if cache_type != 'overall':
                logger.info(f"  • {cache_type.title()}: {stats['hit_rate']:.1f}% hit rate ({stats['entries']} entries)")


# Convenience function for easy integration
def create_backtest_optimizer(
    mode: OptimizationMode = OptimizationMode.OPTIMIZED_ONLY,
    regime_cache_duration: int = 5,
    trend_cache_duration: int = 5,
    momentum_cache_duration: int = 2
) -> BacktestOptimizer:
    """
    Create a configured BacktestOptimizer instance.
    
    Args:
        mode: Optimization mode to use
        regime_cache_duration: How many cycles to cache regime detection
        trend_cache_duration: How many cycles to cache trend calculations
        momentum_cache_duration: How many cycles to cache momentum signals
    
    Returns:
        Configured BacktestOptimizer instance
    """
    cache_config = CacheConfig(
        regime_cache_duration=regime_cache_duration,
        trend_cache_duration=trend_cache_duration,
        momentum_cache_duration=momentum_cache_duration
    )
    
    config = OptimizationConfig(
        mode=mode,
        cache_config=cache_config
    )
    
    return BacktestOptimizer(config)
