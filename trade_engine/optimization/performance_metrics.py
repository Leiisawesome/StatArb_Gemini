"""
Performance Metrics Module for Trade Engine Optimization
========================================================

This module provides comprehensive performance monitoring and metrics collection
for the optimization framework. Tracks cache efficiency, execution times, and
system performance improvements.

Author: StatArb_Gemini Optimization Team
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import json

logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    """Single point-in-time performance measurement"""
    timestamp: datetime
    cycle_num: int
    execution_time_ms: float
    cache_hit_rate: float
    calculations_saved: int
    memory_usage_mb: Optional[float] = None


@dataclass
class PerformanceWindow:
    """Performance metrics over a time window"""
    start_time: datetime
    end_time: datetime
    total_cycles: int
    avg_execution_time_ms: float
    min_execution_time_ms: float
    max_execution_time_ms: float
    avg_cache_hit_rate: float
    total_calculations_saved: int
    performance_improvement_factor: float


class PerformanceTracker:
    """
    Advanced performance tracking for optimization systems.
    
    Provides real-time monitoring, historical analysis, and performance
    trend detection for the trade engine optimization framework.
    """
    
    def __init__(self, window_size: int = 100, alert_threshold_ms: float = 10.0):
        self.window_size = window_size
        self.alert_threshold_ms = alert_threshold_ms
        
        # Performance data storage
        self.snapshots: deque = deque(maxlen=window_size)
        self.execution_times: deque = deque(maxlen=window_size)
        self.cache_hit_rates: deque = deque(maxlen=window_size)
        
        # Cumulative metrics
        self.total_cycles = 0
        self.total_execution_time_ms = 0
        self.total_cache_hits = 0
        self.total_cache_requests = 0
        
        # Performance alerts
        self.alert_callbacks = []
        self.performance_alerts = []
        
        # Baseline for comparison
        self.baseline_performance: Optional[PerformanceWindow] = None
        
        logger.info(f"PerformanceTracker initialized with {window_size} sample window")
    
    def record_cycle_performance(
        self,
        cycle_num: int,
        execution_time_ms: float,
        cache_hits: int,
        cache_requests: int,
        calculations_saved: int = 0,
        memory_usage_mb: Optional[float] = None
    ):
        """Record performance metrics for a single cycle"""
        
        timestamp = datetime.now()
        cache_hit_rate = (cache_hits / cache_requests * 100) if cache_requests > 0 else 0
        
        # Create performance snapshot
        snapshot = PerformanceSnapshot(
            timestamp=timestamp,
            cycle_num=cycle_num,
            execution_time_ms=execution_time_ms,
            cache_hit_rate=cache_hit_rate,
            calculations_saved=calculations_saved,
            memory_usage_mb=memory_usage_mb
        )
        
        # Store snapshot
        self.snapshots.append(snapshot)
        self.execution_times.append(execution_time_ms)
        self.cache_hit_rates.append(cache_hit_rate)
        
        # Update cumulative metrics
        self.total_cycles += 1
        self.total_execution_time_ms += execution_time_ms
        self.total_cache_hits += cache_hits
        self.total_cache_requests += cache_requests
        
        # Check for performance alerts
        self._check_performance_alerts(snapshot)
        
        logger.debug(f"Recorded cycle {cycle_num}: {execution_time_ms:.2f}ms, {cache_hit_rate:.1f}% cache hit rate")
    
    def get_current_performance(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self.snapshots:
            return {}
        
        recent_execution_times = list(self.execution_times)[-10:]  # Last 10 cycles
        recent_cache_rates = list(self.cache_hit_rates)[-10:]
        
        return {
            'total_cycles': self.total_cycles,
            'avg_execution_time_ms': statistics.mean(recent_execution_times) if recent_execution_times else 0,
            'min_execution_time_ms': min(recent_execution_times) if recent_execution_times else 0,
            'max_execution_time_ms': max(recent_execution_times) if recent_execution_times else 0,
            'avg_cache_hit_rate': statistics.mean(recent_cache_rates) if recent_cache_rates else 0,
            'overall_cache_hit_rate': (self.total_cache_hits / self.total_cache_requests * 100) if self.total_cache_requests > 0 else 0,
            'total_calculations_saved': sum(s.calculations_saved for s in self.snapshots),
            'performance_improvement_factor': self._calculate_improvement_factor()
        }
    
    def get_performance_window(self, minutes: int = 10) -> PerformanceWindow:
        """Get performance metrics for a specific time window"""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes)
        
        # Filter snapshots in the time window
        window_snapshots = [
            s for s in self.snapshots 
            if start_time <= s.timestamp <= end_time
        ]
        
        if not window_snapshots:
            return PerformanceWindow(
                start_time=start_time,
                end_time=end_time,
                total_cycles=0,
                avg_execution_time_ms=0,
                min_execution_time_ms=0,
                max_execution_time_ms=0,
                avg_cache_hit_rate=0,
                total_calculations_saved=0,
                performance_improvement_factor=1.0
            )
        
        execution_times = [s.execution_time_ms for s in window_snapshots]
        cache_rates = [s.cache_hit_rate for s in window_snapshots]
        
        return PerformanceWindow(
            start_time=start_time,
            end_time=end_time,
            total_cycles=len(window_snapshots),
            avg_execution_time_ms=statistics.mean(execution_times),
            min_execution_time_ms=min(execution_times),
            max_execution_time_ms=max(execution_times),
            avg_cache_hit_rate=statistics.mean(cache_rates),
            total_calculations_saved=sum(s.calculations_saved for s in window_snapshots),
            performance_improvement_factor=self._calculate_improvement_factor(window_snapshots)
        )
    
    def set_baseline_performance(self, baseline_execution_time_ms: float):
        """Set baseline performance for comparison"""
        self.baseline_execution_time_ms = baseline_execution_time_ms
        logger.info(f"Baseline performance set: {baseline_execution_time_ms:.2f}ms")
    
    def _calculate_improvement_factor(self, snapshots: Optional[List[PerformanceSnapshot]] = None) -> float:
        """Calculate performance improvement factor compared to baseline"""
        if not hasattr(self, 'baseline_execution_time_ms') or not self.baseline_execution_time_ms:
            return 1.0
        
        if snapshots is None:
            snapshots = list(self.snapshots)
        
        if not snapshots:
            return 1.0
        
        current_avg = statistics.mean([s.execution_time_ms for s in snapshots])
        return self.baseline_execution_time_ms / current_avg if current_avg > 0 else 1.0
    
    def _check_performance_alerts(self, snapshot: PerformanceSnapshot):
        """Check for performance alerts and trigger callbacks"""
        alerts = []
        
        # Execution time alert
        if snapshot.execution_time_ms > self.alert_threshold_ms:
            alerts.append(f"High execution time: {snapshot.execution_time_ms:.2f}ms (threshold: {self.alert_threshold_ms}ms)")
        
        # Cache hit rate alert
        if snapshot.cache_hit_rate < 50:
            alerts.append(f"Low cache hit rate: {snapshot.cache_hit_rate:.1f}% (cycle {snapshot.cycle_num})")
        
        # Performance degradation alert
        if len(self.execution_times) >= 10:
            recent_avg = statistics.mean(list(self.execution_times)[-10:])
            older_avg = statistics.mean(list(self.execution_times)[-20:-10]) if len(self.execution_times) >= 20 else recent_avg
            
            if recent_avg > older_avg * 1.5:  # 50% degradation
                alerts.append(f"Performance degradation detected: {recent_avg:.2f}ms vs {older_avg:.2f}ms")
        
        # Store alerts and trigger callbacks
        for alert in alerts:
            self.performance_alerts.append((datetime.now(), alert))
            logger.warning(f"PERFORMANCE ALERT: {alert}")
            
            for callback in self.alert_callbacks:
                try:
                    callback(alert, snapshot)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback):
        """Add a callback function for performance alerts"""
        self.alert_callbacks.append(callback)
    
    def get_performance_trends(self, window_minutes: int = 30) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        window = self.get_performance_window(window_minutes)
        
        if len(self.snapshots) < 10:
            return {'status': 'insufficient_data', 'message': 'Need at least 10 cycles for trend analysis'}
        
        # Calculate trends
        recent_snapshots = list(self.snapshots)[-20:]  # Last 20 cycles
        execution_times = [s.execution_time_ms for s in recent_snapshots]
        cache_rates = [s.cache_hit_rate for s in recent_snapshots]
        
        # Simple linear trend calculation
        def calculate_trend(values):
            if len(values) < 2:
                return 0
            x = list(range(len(values)))
            n = len(values)
            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(x[i] * values[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0
            return slope
        
        execution_trend = calculate_trend(execution_times)
        cache_trend = calculate_trend(cache_rates)
        
        return {
            'status': 'analysis_complete',
            'window_minutes': window_minutes,
            'execution_time_trend': {
                'slope': execution_trend,
                'direction': 'improving' if execution_trend < 0 else 'degrading' if execution_trend > 0 else 'stable',
                'current_avg': statistics.mean(execution_times),
                'trend_magnitude': abs(execution_trend)
            },
            'cache_rate_trend': {
                'slope': cache_trend,
                'direction': 'improving' if cache_trend > 0 else 'degrading' if cache_trend < 0 else 'stable',
                'current_avg': statistics.mean(cache_rates),
                'trend_magnitude': abs(cache_trend)
            },
            'overall_performance': window.__dict__
        }
    
    def export_performance_data(self, filepath: str):
        """Export performance data to JSON file"""
        data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_cycles': self.total_cycles,
            'window_size': self.window_size,
            'snapshots': [
                {
                    'timestamp': s.timestamp.isoformat(),
                    'cycle_num': s.cycle_num,
                    'execution_time_ms': s.execution_time_ms,
                    'cache_hit_rate': s.cache_hit_rate,
                    'calculations_saved': s.calculations_saved,
                    'memory_usage_mb': s.memory_usage_mb
                }
                for s in self.snapshots
            ],
            'performance_alerts': [
                {
                    'timestamp': alert[0].isoformat(),
                    'message': alert[1]
                }
                for alert in self.performance_alerts
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Performance data exported to {filepath}")
    
    def log_performance_summary(self):
        """Log a comprehensive performance summary"""
        current_perf = self.get_current_performance()
        trends = self.get_performance_trends()
        
        logger.info("🎯 PERFORMANCE TRACKER SUMMARY:")
        logger.info(f"  • Total Cycles Tracked: {current_perf.get('total_cycles', 0)}")
        logger.info(f"  • Avg Execution Time: {current_perf.get('avg_execution_time_ms', 0):.2f}ms")
        logger.info(f"  • Overall Cache Hit Rate: {current_perf.get('overall_cache_hit_rate', 0):.1f}%")
        logger.info(f"  • Performance Improvement: {current_perf.get('performance_improvement_factor', 1):.2f}x")
        
        if trends['status'] == 'analysis_complete':
            logger.info("📈 PERFORMANCE TRENDS:")
            exec_trend = trends['execution_time_trend']
            cache_trend = trends['cache_rate_trend']
            logger.info(f"  • Execution Time: {exec_trend['direction']} (slope: {exec_trend['slope']:.3f})")
            logger.info(f"  • Cache Efficiency: {cache_trend['direction']} (slope: {cache_trend['slope']:.3f})")
        
        if self.performance_alerts:
            logger.info(f"⚠️  Recent Alerts: {len(self.performance_alerts)} performance alerts recorded")


# Convenience functions for easy integration
def create_performance_tracker(window_size: int = 100, alert_threshold_ms: float = 10.0) -> PerformanceTracker:
    """Create a configured PerformanceTracker instance"""
    return PerformanceTracker(window_size=window_size, alert_threshold_ms=alert_threshold_ms)


def log_optimization_comparison(baseline_time_ms: float, optimized_time_ms: float, cache_hit_rate: float):
    """Log a performance comparison between baseline and optimized execution"""
    improvement_factor = baseline_time_ms / optimized_time_ms if optimized_time_ms > 0 else 1.0
    improvement_percentage = (1 - optimized_time_ms / baseline_time_ms) * 100 if baseline_time_ms > 0 else 0
    
    logger.info("🚀 OPTIMIZATION PERFORMANCE COMPARISON:")
    logger.info(f"  • Baseline Execution: {baseline_time_ms:.2f}ms")
    logger.info(f"  • Optimized Execution: {optimized_time_ms:.2f}ms")
    logger.info(f"  • Performance Improvement: {improvement_factor:.2f}x ({improvement_percentage:.1f}% faster)")
    logger.info(f"  • Cache Hit Rate: {cache_hit_rate:.1f}%")
    
    if improvement_factor >= 2.0:
        logger.info("  🎉 EXCELLENT: 2x+ performance improvement achieved!")
    elif improvement_factor >= 1.5:
        logger.info("  ✅ GOOD: Significant performance improvement achieved!")
    elif improvement_factor >= 1.2:
        logger.info("  👍 DECENT: Moderate performance improvement achieved!")
    else:
        logger.warning("  ⚠️  REVIEW: Limited performance improvement - check optimization strategy")
