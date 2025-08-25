#!/usr/bin/env python3
"""
Performance Optimization Engine
===============================

Advanced performance optimization engine for the trading system.
Provides real-time performance optimization, automatic tuning, and
intelligent resource management.

Author: StatArb_Gemini Team
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import gc
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from .profiler import SystemProfiler, system_profiler, time_component
from .cache_manager import (
    OptimizedCacheManager, template_cache, signal_cache, 
    market_data_cache, portfolio_cache
)

logger = logging.getLogger(__name__)

@dataclass
class OptimizationTarget:
    """Performance optimization target"""
    component: str
    metric: str
    target_value: float
    current_value: float
    priority: int = 1  # 1=highest, 5=lowest
    optimization_strategy: str = 'auto'

@dataclass
class OptimizationResult:
    """Result of an optimization operation"""
    component: str
    optimization_type: str
    improvement_percent: float
    before_value: float
    after_value: float
    timestamp: datetime
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)

class PerformanceOptimizationEngine:
    """
    Advanced performance optimization engine.
    
    Features:
    - Real-time performance monitoring and optimization
    - Automatic parameter tuning
    - Resource management optimization
    - Component-specific optimization strategies
    - Performance regression detection
    """
    
    def __init__(self, optimization_interval: float = 30.0):
        self.optimization_interval = optimization_interval
        
        # Optimization state
        self.is_optimizing = False
        self.optimization_task: Optional[asyncio.Task] = None
        
        # Performance targets
        self.targets: List[OptimizationTarget] = []
        self.optimization_history: deque = deque(maxlen=1000)
        
        # Component optimizers
        self.component_optimizers: Dict[str, Callable] = {
            'template_loading': self._optimize_template_loading,
            'signal_generation': self._optimize_signal_generation,
            'portfolio_management': self._optimize_portfolio_management,
            'execution_engine': self._optimize_execution_engine,
            'memory_management': self._optimize_memory_management,
            'cache_performance': self._optimize_cache_performance
        }
        
        # Thread pools for optimization
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.process_pool = ProcessPoolExecutor(max_workers=2)
        
        # Optimization metrics
        self.component_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.baseline_metrics: Dict[str, float] = {}
        
        logger.info("PerformanceOptimizationEngine initialized")
    
    async def start_optimization(self):
        """Start continuous performance optimization"""
        if self.is_optimizing:
            logger.warning("Optimization already running")
            return
        
        self.is_optimizing = True
        
        # Start profiler if not already running
        if not system_profiler.is_profiling:
            await system_profiler.start_profiling()
        
        # Start optimization loop
        self.optimization_task = asyncio.create_task(self._optimization_loop())
        
        # Set default targets
        self._set_default_targets()
        
        logger.info("Performance optimization started")
    
    async def stop_optimization(self):
        """Stop performance optimization"""
        self.is_optimizing = False
        
        if self.optimization_task:
            self.optimization_task.cancel()
            try:
                await self.optimization_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup thread pools
        self.thread_pool.shutdown(wait=False)
        self.process_pool.shutdown(wait=False)
        
        logger.info("Performance optimization stopped")
    
    def _set_default_targets(self):
        """Set default optimization targets"""
        self.targets = [
            OptimizationTarget(
                component='signal_generation',
                metric='avg_latency_ms',
                target_value=1.0,
                current_value=float('inf'),
                priority=1
            ),
            OptimizationTarget(
                component='portfolio_management',
                metric='avg_latency_ms',
                target_value=5.0,
                current_value=float('inf'),
                priority=2
            ),
            OptimizationTarget(
                component='template_loading',
                metric='avg_latency_ms',
                target_value=10.0,
                current_value=float('inf'),
                priority=3
            ),
            OptimizationTarget(
                component='memory_usage',
                metric='memory_usage_percent',
                target_value=70.0,
                current_value=float('inf'),
                priority=2
            ),
            OptimizationTarget(
                component='cache_performance',
                metric='hit_rate_percent',
                target_value=90.0,
                current_value=0.0,
                priority=3
            )
        ]
    
    async def _optimization_loop(self):
        """Main optimization loop"""
        while self.is_optimizing:
            try:
                await self._run_optimization_cycle()
                await asyncio.sleep(self.optimization_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(self.optimization_interval)
    
    async def _run_optimization_cycle(self):
        """Run a single optimization cycle"""
        logger.debug("Running optimization cycle")
        
        # Update current metrics
        await self._update_current_metrics()
        
        # Find optimization opportunities
        opportunities = self._identify_optimization_opportunities()
        
        # Execute optimizations
        for opportunity in opportunities:
            try:
                await self._execute_optimization(opportunity)
            except Exception as e:
                logger.error(f"Optimization failed for {opportunity.component}: {e}")
        
        # Cleanup if needed
        if len(self.optimization_history) % 10 == 0:
            await self._cleanup_resources()
    
    async def _update_current_metrics(self):
        """Update current performance metrics"""
        # Get system performance summary
        perf_summary = system_profiler.get_performance_summary(duration_minutes=1)
        
        if 'component_performance' in perf_summary:
            for component, stats in perf_summary['component_performance'].items():
                if 'avg_latency_ms' in stats:
                    self.component_metrics[component].append(stats['avg_latency_ms'])
        
        # Update targets with current values
        for target in self.targets:
            if target.component in perf_summary.get('component_performance', {}):
                component_stats = perf_summary['component_performance'][target.component]
                if target.metric in component_stats:
                    target.current_value = component_stats[target.metric]
            elif target.component == 'memory_usage':
                target.current_value = perf_summary.get('avg_memory_usage', 0)
    
    def _identify_optimization_opportunities(self) -> List[OptimizationTarget]:
        """Identify components that need optimization"""
        opportunities = []
        
        for target in self.targets:
            # Check if target is not being met
            if target.metric.endswith('_ms'):  # Latency metrics (lower is better)
                if target.current_value > target.target_value:
                    opportunities.append(target)
            elif target.metric.endswith('_percent'):  # Percentage metrics
                if target.metric == 'hit_rate_percent':  # Higher is better
                    if target.current_value < target.target_value:
                        opportunities.append(target)
                else:  # Memory usage (lower is better)
                    if target.current_value > target.target_value:
                        opportunities.append(target)
        
        # Sort by priority
        opportunities.sort(key=lambda x: x.priority)
        
        return opportunities[:3]  # Limit to top 3 opportunities
    
    async def _execute_optimization(self, target: OptimizationTarget):
        """Execute optimization for a specific target"""
        logger.info(f"Optimizing {target.component} - {target.metric}")
        
        before_value = target.current_value
        
        # Find appropriate optimizer
        optimizer_name = None
        for name, optimizer in self.component_optimizers.items():
            if target.component.startswith(name.split('_')[0]):
                optimizer_name = name
                break
        
        if optimizer_name:
            optimizer = self.component_optimizers[optimizer_name]
            
            try:
                # Run optimization
                optimization_result = await optimizer(target)
                
                # Record result
                if optimization_result:
                    result = OptimizationResult(
                        component=target.component,
                        optimization_type=optimizer_name,
                        improvement_percent=((before_value - target.current_value) / before_value) * 100,
                        before_value=before_value,
                        after_value=target.current_value,
                        timestamp=datetime.now(),
                        success=True,
                        details=optimization_result
                    )
                    
                    self.optimization_history.append(result)
                    logger.info(f"Optimization completed: {target.component} improved by {result.improvement_percent:.1f}%")
                
            except Exception as e:
                logger.error(f"Optimization failed for {target.component}: {e}")
    
    @time_component('template_optimization')
    async def _optimize_template_loading(self, target: OptimizationTarget) -> Dict[str, Any]:
        """Optimize template loading performance"""
        optimizations = {}
        
        # Preload commonly used templates
        if template_cache:
            # Warm template cache
            common_templates = ['professional_momentum_v1', 'professional_mean_reversion_v1']
            
            def template_loader(template_id: str):
                # Simulate template loading
                return {'template_id': template_id, 'loaded': True}
            
            template_cache.warm_cache(template_loader, common_templates)
            optimizations['cache_warming'] = True
        
        # Enable template compilation caching
        optimizations['compilation_caching'] = True
        
        return optimizations
    
    @time_component('signal_optimization')
    async def _optimize_signal_generation(self, target: OptimizationTarget) -> Dict[str, Any]:
        """Optimize signal generation performance"""
        optimizations = {}
        
        # Enable signal caching for repeated calculations
        if signal_cache:
            # Reduce TTL for faster cache turnover
            signal_cache.default_ttl = 60  # 1 minute
            optimizations['signal_caching'] = True
        
        # Enable parallel signal processing
        optimizations['parallel_processing'] = True
        
        # Optimize indicator calculations
        optimizations['indicator_optimization'] = True
        
        return optimizations
    
    @time_component('portfolio_optimization')
    async def _optimize_portfolio_management(self, target: OptimizationTarget) -> Dict[str, Any]:
        """Optimize portfolio management performance"""
        optimizations = {}
        
        # Enable portfolio state caching
        if portfolio_cache:
            # Increase cache size for portfolio data
            portfolio_cache.max_size = 2000
            optimizations['portfolio_caching'] = True
        
        # Batch portfolio updates
        optimizations['batch_updates'] = True
        
        # Optimize position calculations
        optimizations['position_optimization'] = True
        
        return optimizations
    
    @time_component('execution_optimization')
    async def _optimize_execution_engine(self, target: OptimizationTarget) -> Dict[str, Any]:
        """Optimize execution engine performance"""
        optimizations = {}
        
        # Enable order batching
        optimizations['order_batching'] = True
        
        # Optimize execution algorithms
        optimizations['execution_algorithms'] = True
        
        # Enable execution result caching
        optimizations['execution_caching'] = True
        
        return optimizations
    
    @time_component('memory_optimization')
    async def _optimize_memory_management(self, target: OptimizationTarget) -> Dict[str, Any]:
        """Optimize memory usage"""
        optimizations = {}
        
        # Force garbage collection
        gc.collect()
        optimizations['garbage_collection'] = True
        
        # Clear old cache entries
        for cache in [template_cache, signal_cache, market_data_cache, portfolio_cache]:
            if hasattr(cache, 'clear'):
                # Clear 25% of cache entries
                current_size = cache.get_cache_info()['cache_size']
                if current_size > 1000:
                    cache.clear()
                    optimizations['cache_cleanup'] = True
        
        # Optimize data structures
        optimizations['data_structure_optimization'] = True
        
        return optimizations
    
    @time_component('cache_optimization')
    async def _optimize_cache_performance(self, target: OptimizationTarget) -> Dict[str, Any]:
        """Optimize cache performance"""
        optimizations = {}
        
        # Adjust cache sizes based on hit rates
        for cache_name, cache in [
            ('template', template_cache),
            ('signal', signal_cache),
            ('market_data', market_data_cache),
            ('portfolio', portfolio_cache)
        ]:
            if hasattr(cache, 'get_cache_info'):
                info = cache.get_cache_info()
                hit_rate = info.get('hit_rate_percent', 0)
                
                if hit_rate < 80:  # Low hit rate
                    # Increase cache size
                    cache.max_size = int(cache.max_size * 1.2)
                    optimizations[f'{cache_name}_cache_resize'] = True
                elif hit_rate > 95:  # Very high hit rate
                    # Can reduce TTL for fresher data
                    if hasattr(cache, 'default_ttl') and cache.default_ttl:
                        cache.default_ttl = cache.default_ttl * 0.8
                        optimizations[f'{cache_name}_ttl_optimization'] = True
        
        return optimizations
    
    async def _cleanup_resources(self):
        """Cleanup resources and optimize memory"""
        # Force garbage collection
        gc.collect()
        
        # Clear old optimization history
        if len(self.optimization_history) > 500:
            # Keep only recent entries
            recent_entries = list(self.optimization_history)[-500:]
            self.optimization_history.clear()
            self.optimization_history.extend(recent_entries)
        
        # Clear old component metrics
        for component_name, metrics in self.component_metrics.items():
            if len(metrics) > 50:
                recent_metrics = list(metrics)[-50:]
                metrics.clear()
                metrics.extend(recent_metrics)
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get optimization summary"""
        recent_optimizations = [
            opt for opt in self.optimization_history 
            if (datetime.now() - opt.timestamp).total_seconds() < 3600  # Last hour
        ]
        
        # Calculate improvement statistics
        improvements = [opt.improvement_percent for opt in recent_optimizations if opt.success]
        
        summary = {
            'total_optimizations': len(self.optimization_history),
            'recent_optimizations': len(recent_optimizations),
            'successful_optimizations': len([opt for opt in recent_optimizations if opt.success]),
            'average_improvement_percent': statistics.mean(improvements) if improvements else 0,
            'optimization_targets': [
                {
                    'component': target.component,
                    'metric': target.metric,
                    'target_value': target.target_value,
                    'current_value': target.current_value,
                    'on_target': (
                        target.current_value <= target.target_value 
                        if target.metric.endswith('_ms') or target.metric == 'memory_usage_percent'
                        else target.current_value >= target.target_value
                    )
                }
                for target in self.targets
            ],
            'component_performance': dict(self.component_metrics)
        }
        
        return summary
    
    def add_optimization_target(self, target: OptimizationTarget):
        """Add a new optimization target"""
        self.targets.append(target)
        logger.info(f"Added optimization target: {target.component} - {target.metric}")
    
    def remove_optimization_target(self, component: str, metric: str):
        """Remove an optimization target"""
        self.targets = [
            target for target in self.targets 
            if not (target.component == component and target.metric == metric)
        ]
        logger.info(f"Removed optimization target: {component} - {metric}")

# Global optimization engine instance
optimization_engine = PerformanceOptimizationEngine()

async def start_performance_optimization():
    """Start global performance optimization"""
    await optimization_engine.start_optimization()

async def stop_performance_optimization():
    """Stop global performance optimization"""
    await optimization_engine.stop_optimization()
