"""
Template Performance Integrator
===============================

Integrates template performance tracking with the core engine,
providing real-time performance analytics and optimization feedback.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque

from strategy_layer.template_integration import TemplatePerformanceTracker
from .template_core_engine import TemplateEngineConfig, TemplateExecutionResult

logger = logging.getLogger(__name__)

class PerformanceMetric(Enum):
    """Performance metrics tracked"""
    EXECUTION_TIME = "execution_time"
    SUCCESS_RATE = "success_rate"
    SIGNAL_QUALITY = "signal_quality"
    POSITION_ACCURACY = "position_accuracy"
    RISK_ADJUSTED_RETURN = "risk_adjusted_return"
    LATENCY = "latency"
    THROUGHPUT = "throughput"

@dataclass
class PerformanceSnapshot:
    """Performance snapshot for a template"""
    template_id: str
    timestamp: datetime
    metrics: Dict[PerformanceMetric, float] = field(default_factory=dict)
    
    # Execution context
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    execution_mode: str = "single"
    
    # Template-specific data
    category_performance_score: float = 0.0
    inheritance_impact: Dict[str, float] = field(default_factory=dict)

class TemplatePerformanceIntegrator:
    """
    Integrates template performance tracking with core engine operations,
    providing real-time analytics and optimization feedback.
    """
    
    def __init__(self, performance_tracker: TemplatePerformanceTracker,
                 config: TemplateEngineConfig):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.performance_tracker = performance_tracker
        self.config = config
        
        # Performance data storage
        self.performance_history: deque = deque(maxlen=10000)
        self.real_time_metrics: Dict[str, Dict[PerformanceMetric, float]] = defaultdict(dict)
        self.category_benchmarks: Dict[str, Dict[PerformanceMetric, float]] = defaultdict(dict)
        
        # Performance analytics
        self.performance_trends: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self.optimization_recommendations: Dict[str, List[str]] = defaultdict(list)
        
        self.logger.info("TemplatePerformanceIntegrator initialized")
    
    async def initialize(self):
        """Initialize performance integrator"""
        
        self.logger.info("Initializing template performance integrator")
        
        # Setup performance monitoring
        await self._setup_performance_monitoring()
        
        # Initialize category benchmarks
        await self._initialize_category_benchmarks()
        
        self.logger.info("Template performance integrator initialization completed")
    
    async def update_template_performance(self, result: TemplateExecutionResult):
        """Update template performance with execution result"""
        
        try:
            # Create performance snapshot
            snapshot = PerformanceSnapshot(
                template_id=result.template_id,
                timestamp=datetime.now(),
                category_performance_score=result.category_performance_score,
                inheritance_impact=result.inheritance_impact
            )
            
            # Calculate performance metrics
            snapshot.metrics = await self._calculate_performance_metrics(result)
            
            # Store in history
            self.performance_history.append(snapshot)
            
            # Update real-time metrics
            await self._update_real_time_metrics(result.template_id, snapshot.metrics)
            
            # Update performance tracker
            await self._sync_with_performance_tracker(result, snapshot)
            
            # Analyze trends and generate recommendations
            await self._analyze_performance_trends(result.template_id)
            
        except Exception as e:
            self.logger.error(f"Failed to update template performance: {e}")
    
    async def _calculate_performance_metrics(self, result: TemplateExecutionResult) -> Dict[PerformanceMetric, float]:
        """Calculate comprehensive performance metrics"""
        
        metrics = {}
        
        # Execution time metric
        metrics[PerformanceMetric.EXECUTION_TIME] = result.execution_time_ms
        
        # Success rate (binary for single execution)
        metrics[PerformanceMetric.SUCCESS_RATE] = 1.0 if result.success else 0.0
        
        # Signal quality metric
        if result.signals:
            signal_strength = sum(abs(signal) for signal in result.signals.values())
            signal_count = len(result.signals)
            metrics[PerformanceMetric.SIGNAL_QUALITY] = signal_strength / max(signal_count, 1)
        else:
            metrics[PerformanceMetric.SIGNAL_QUALITY] = 0.0
        
        # Position accuracy (simplified calculation)
        if result.positions:
            position_strength = sum(abs(pos) for pos in result.positions.values())
            position_count = len(result.positions)
            metrics[PerformanceMetric.POSITION_ACCURACY] = position_strength / max(position_count, 1)
        else:
            metrics[PerformanceMetric.POSITION_ACCURACY] = 0.0
        
        # Latency metric
        metrics[PerformanceMetric.LATENCY] = result.execution_latency_ms
        
        # Processing efficiency as throughput proxy
        if result.execution_time_ms > 0:
            operations_per_second = 1000.0 / result.execution_time_ms
            metrics[PerformanceMetric.THROUGHPUT] = operations_per_second
        else:
            metrics[PerformanceMetric.THROUGHPUT] = 0.0
        
        # Risk-adjusted return (placeholder - would need market data)
        metrics[PerformanceMetric.RISK_ADJUSTED_RETURN] = result.category_performance_score
        
        return metrics
    
    async def _update_real_time_metrics(self, template_id: str, metrics: Dict[PerformanceMetric, float]):
        """Update real-time metrics with exponential smoothing"""
        
        alpha = 0.1  # Smoothing factor
        
        for metric, value in metrics.items():
            current_value = self.real_time_metrics[template_id].get(metric, value)
            smoothed_value = (1 - alpha) * current_value + alpha * value
            self.real_time_metrics[template_id][metric] = smoothed_value
    
    async def _sync_with_performance_tracker(self, result: TemplateExecutionResult, snapshot: PerformanceSnapshot):
        """Sync performance data with the strategy layer performance tracker"""
        
        try:
            # Convert to format expected by performance tracker
            performance_data = {
                'template_id': result.template_id,
                'execution_timestamp': snapshot.timestamp,
                'execution_time_ms': result.execution_time_ms,
                'success': result.success,
                'signals': result.signals,
                'positions': result.positions,
                'performance_score': result.category_performance_score,
                'errors': result.errors
            }
            
            # Update performance tracker (sync call)
            self.performance_tracker.update_performance(result.template_id, performance_data)
            
        except Exception as e:
            self.logger.warning(f"Failed to sync with performance tracker: {e}")
    
    async def _analyze_performance_trends(self, template_id: str):
        """Analyze performance trends for template"""
        
        # Get recent performance data
        recent_snapshots = [
            snap for snap in list(self.performance_history)[-100:]  # Last 100 snapshots
            if snap.template_id == template_id
        ]
        
        if len(recent_snapshots) < 5:
            return  # Need minimum data for trend analysis
        
        # Analyze trends for each metric
        for metric in PerformanceMetric:
            values = [snap.metrics.get(metric, 0.0) for snap in recent_snapshots]
            
            if len(values) >= 5:
                # Calculate trend
                trend = await self._calculate_trend(values)
                self.performance_trends[template_id][metric.value].append(trend)
                
                # Keep limited history
                if len(self.performance_trends[template_id][metric.value]) > 50:
                    self.performance_trends[template_id][metric.value].pop(0)
        
        # Generate optimization recommendations
        await self._generate_optimization_recommendations(template_id)
    
    async def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend coefficient (-1 to 1)"""
        
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        x = np.arange(len(values))
        y = np.array(values)
        
        if np.std(y) == 0:
            return 0.0
        
        correlation = np.corrcoef(x, y)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    async def _generate_optimization_recommendations(self, template_id: str):
        """Generate optimization recommendations based on performance trends"""
        
        recommendations = []
        trends = self.performance_trends[template_id]
        
        # Check execution time trend
        if PerformanceMetric.EXECUTION_TIME.value in trends:
            exec_time_trend = trends[PerformanceMetric.EXECUTION_TIME.value]
            if exec_time_trend and exec_time_trend[-1] > 0.3:  # Increasing trend
                recommendations.append("Consider optimizing execution path or using inheritance mode")
        
        # Check success rate trend
        if PerformanceMetric.SUCCESS_RATE.value in trends:
            success_trend = trends[PerformanceMetric.SUCCESS_RATE.value]
            if success_trend and success_trend[-1] < -0.3:  # Decreasing trend
                recommendations.append("Review template parameters or consider category batch execution")
        
        # Check signal quality trend
        if PerformanceMetric.SIGNAL_QUALITY.value in trends:
            signal_trend = trends[PerformanceMetric.SIGNAL_QUALITY.value]
            if signal_trend and signal_trend[-1] < -0.2:  # Decreasing trend
                recommendations.append("Signal quality declining - review market data inputs")
        
        # Update recommendations
        self.optimization_recommendations[template_id] = recommendations[-5:]  # Keep last 5
    
    async def _setup_performance_monitoring(self):
        """Setup real-time performance monitoring"""
        
        # Initialize monitoring for common metrics
        for metric in PerformanceMetric:
            # Setup metric-specific monitoring parameters
            pass
    
    async def _initialize_category_benchmarks(self):
        """Initialize performance benchmarks for each category"""
        
        from strategy_templates.base import TemplateCategory
        
        # Set category-specific performance benchmarks
        self.category_benchmarks = {
            TemplateCategory.BASE.value: {
                PerformanceMetric.EXECUTION_TIME: 50.0,  # 50ms target
                PerformanceMetric.SUCCESS_RATE: 0.95,    # 95% success rate
                PerformanceMetric.SIGNAL_QUALITY: 0.7,   # 0.7 signal strength
                PerformanceMetric.LATENCY: 20.0          # 20ms latency
            },
            TemplateCategory.SPECIFIC.value: {
                PerformanceMetric.EXECUTION_TIME: 100.0,  # 100ms target
                PerformanceMetric.SUCCESS_RATE: 0.90,     # 90% success rate
                PerformanceMetric.SIGNAL_QUALITY: 0.8,    # 0.8 signal strength
                PerformanceMetric.LATENCY: 40.0           # 40ms latency
            },
            TemplateCategory.COMPOSITE.value: {
                PerformanceMetric.EXECUTION_TIME: 200.0,  # 200ms target
                PerformanceMetric.SUCCESS_RATE: 0.85,     # 85% success rate
                PerformanceMetric.SIGNAL_QUALITY: 0.9,    # 0.9 signal strength
                PerformanceMetric.LATENCY: 80.0           # 80ms latency
            }
        }
    
    async def get_template_performance_summary(self, template_id: str) -> Dict[str, Any]:
        """Get comprehensive performance summary for template"""
        
        # Get real-time metrics
        current_metrics = self.real_time_metrics.get(template_id, {})
        
        # Get recent performance history
        recent_snapshots = [
            snap for snap in list(self.performance_history)[-50:]
            if snap.template_id == template_id
        ]
        
        # Calculate statistics
        stats = {}
        if recent_snapshots:
            for metric in PerformanceMetric:
                values = [snap.metrics.get(metric, 0.0) for snap in recent_snapshots]
                if values:
                    stats[metric.value] = {
                        'current': current_metrics.get(metric, 0.0),
                        'avg': np.mean(values),
                        'std': np.std(values),
                        'min': np.min(values),
                        'max': np.max(values),
                        'trend': self.performance_trends[template_id].get(metric.value, [0.0])[-1] if self.performance_trends[template_id].get(metric.value) else 0.0
                    }
        
        # Get recommendations
        recommendations = self.optimization_recommendations.get(template_id, [])
        
        return {
            'template_id': template_id,
            'current_metrics': {metric.value: value for metric, value in current_metrics.items()},
            'statistics': stats,
            'recommendations': recommendations,
            'data_points': len(recent_snapshots),
            'last_updated': recent_snapshots[-1].timestamp if recent_snapshots else None
        }
    
    async def get_category_performance_comparison(self) -> Dict[str, Any]:
        """Get performance comparison across categories"""
        
        from strategy_templates.base import TemplateCategory
        
        category_stats = {}
        
        for category in TemplateCategory:
            # Get templates in category
            category_templates = [
                snap.template_id for snap in self.performance_history
                if snap.template_id.startswith(category.value.lower())  # Simplified category detection
            ]
            
            if not category_templates:
                continue
            
            # Calculate category averages
            category_snapshots = [
                snap for snap in self.performance_history
                if snap.template_id in set(category_templates)
            ]
            
            if category_snapshots:
                avg_metrics = {}
                for metric in PerformanceMetric:
                    values = [snap.metrics.get(metric, 0.0) for snap in category_snapshots]
                    if values:
                        avg_metrics[metric.value] = {
                            'avg': np.mean(values),
                            'std': np.std(values),
                            'benchmark': self.category_benchmarks.get(category.value, {}).get(metric, 0.0)
                        }
                
                category_stats[category.value] = {
                    'template_count': len(set(category_templates)),
                    'data_points': len(category_snapshots),
                    'avg_metrics': avg_metrics
                }
        
        return category_stats
    
    async def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """Get performance alerts for templates below benchmarks"""
        
        alerts = []
        
        for template_id, metrics in self.real_time_metrics.items():
            # Determine template category (simplified)
            template_category = None
            for cat in ['base', 'specific', 'composite']:
                if cat in template_id.lower():
                    template_category = cat
                    break
            
            if not template_category:
                continue
            
            # Check against benchmarks
            benchmarks = self.category_benchmarks.get(template_category, {})
            
            for metric, current_value in metrics.items():
                benchmark_value = benchmarks.get(metric)
                
                if benchmark_value is not None:
                    # Check for performance degradation
                    if metric in [PerformanceMetric.SUCCESS_RATE, PerformanceMetric.SIGNAL_QUALITY]:
                        # Higher is better
                        if current_value < benchmark_value * 0.8:  # 20% below benchmark
                            alerts.append({
                                'template_id': template_id,
                                'metric': metric.value,
                                'current_value': current_value,
                                'benchmark_value': benchmark_value,
                                'severity': 'warning' if current_value > benchmark_value * 0.6 else 'critical',
                                'message': f"{metric.value} below benchmark"
                            })
                    
                    elif metric in [PerformanceMetric.EXECUTION_TIME, PerformanceMetric.LATENCY]:
                        # Lower is better
                        if current_value > benchmark_value * 1.5:  # 50% above benchmark
                            alerts.append({
                                'template_id': template_id,
                                'metric': metric.value,
                                'current_value': current_value,
                                'benchmark_value': benchmark_value,
                                'severity': 'warning' if current_value < benchmark_value * 2.0 else 'critical',
                                'message': f"{metric.value} above benchmark"
                            })
        
        return alerts
    
    async def export_performance_data(self, template_id: Optional[str] = None,
                                    start_time: Optional[datetime] = None,
                                    end_time: Optional[datetime] = None) -> pd.DataFrame:
        """Export performance data as DataFrame"""
        
        # Filter data
        snapshots = list(self.performance_history)
        
        if template_id:
            snapshots = [snap for snap in snapshots if snap.template_id == template_id]
        
        if start_time:
            snapshots = [snap for snap in snapshots if snap.timestamp >= start_time]
        
        if end_time:
            snapshots = [snap for snap in snapshots if snap.timestamp <= end_time]
        
        # Convert to DataFrame
        data = []
        for snap in snapshots:
            row = {
                'template_id': snap.template_id,
                'timestamp': snap.timestamp,
                'category_performance_score': snap.category_performance_score
            }
            
            # Add metrics
            for metric, value in snap.metrics.items():
                row[metric.value] = value
            
            # Add inheritance impact
            for parent, impact in snap.inheritance_impact.items():
                row[f'inheritance_{parent}'] = impact
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    async def shutdown(self):
        """Shutdown performance integrator"""
        
        self.logger.info("Shutting down template performance integrator")
        
        # Clear data structures
        self.performance_history.clear()
        self.real_time_metrics.clear()
        self.performance_trends.clear()
        self.optimization_recommendations.clear()
        
        self.logger.info("Template performance integrator shutdown completed")
