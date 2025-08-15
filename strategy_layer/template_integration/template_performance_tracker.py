"""
Template Performance Tracker
============================

Performance tracking and analytics system for template-based strategies
with inheritance-aware metrics and optimization feedback.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import json

from strategy_layer.base import StrategyResult
from strategy_templates.base import TemplateRegistry, BaseTemplate

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for a strategy"""
    strategy_id: str
    template_id: str
    total_executions: int = 0
    successful_executions: int = 0
    average_execution_time_ms: float = 0.0
    average_signals_per_execution: float = 0.0
    average_positions_per_execution: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    last_execution: Optional[datetime] = None
    performance_trend: str = "stable"  # improving, degrading, stable
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TemplatePerformanceStats:
    """Aggregated performance statistics for a template"""
    template_id: str
    instance_count: int = 0
    total_executions: int = 0
    aggregate_success_rate: float = 0.0
    average_execution_time_ms: float = 0.0
    best_performing_instance: Optional[str] = None
    worst_performing_instance: Optional[str] = None
    inheritance_impact: Dict[str, Any] = field(default_factory=dict)
    category_performance: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InheritancePerformanceAnalysis:
    """Analysis of performance impact from template inheritance"""
    base_template_id: str
    derived_template_ids: List[str] = field(default_factory=list)
    performance_improvement: float = 0.0  # % improvement over base
    inheritance_overhead_ms: float = 0.0
    optimization_suggestions: List[str] = field(default_factory=list)

class TemplatePerformanceTracker:
    """
    Tracks and analyzes performance of template-based strategies with
    inheritance-aware metrics and optimization recommendations.
    """
    
    def __init__(self, template_registry: TemplateRegistry):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        
        # Performance data storage
        self.strategy_metrics: Dict[str, PerformanceMetrics] = {}
        self.template_stats: Dict[str, TemplatePerformanceStats] = {}
        self.execution_history: deque = deque(maxlen=10000)  # Rolling window
        
        # Performance tracking configuration
        self.tracking_window_hours = 24
        self.trend_analysis_window = 100  # Last N executions for trend analysis
        self.performance_alert_thresholds = {
            'success_rate_min': 0.85,
            'execution_time_max_ms': 1000,
            'error_rate_max': 0.15
        }
        
        # Inheritance analysis
        self.inheritance_performance: Dict[str, InheritancePerformanceAnalysis] = {}
        
        self.logger.info("TemplatePerformanceTracker initialized")
    
    def update_performance(self, template_id: str, performance_data: Dict[str, Any]):
        """Update performance metrics for a template"""
        try:
            # Check if template exists
            template = self.template_registry.get_template(template_id)
            if not template:
                self.logger.warning(f"Template {template_id} not found for performance update")
                return
            
            # Create or update template stats
            if template_id not in self.template_stats:
                self.template_stats[template_id] = TemplatePerformanceStats(template_id=template_id)
            
            stats = self.template_stats[template_id]
            
            # Update basic metrics if provided
            if 'success_rate' in performance_data:
                stats.aggregate_success_rate = performance_data['success_rate']
            if 'execution_time_ms' in performance_data:
                stats.average_execution_time_ms = performance_data['execution_time_ms']
            if 'execution_count' in performance_data:
                stats.total_executions += performance_data['execution_count']
                
            self.logger.debug(f"Updated performance for template {template_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update performance for {template_id}: {e}")
    
    def record_execution(self, instance_id: str, template_id: str, 
                        result: StrategyResult, execution_time_ms: float):
        """
        Record execution performance for a strategy instance
        """
        try:
            # Record execution in history
            execution_record = {
                'timestamp': datetime.now(),
                'instance_id': instance_id,
                'template_id': template_id,
                'execution_time_ms': execution_time_ms,
                'signal_count': len(result.signals),
                'position_count': len(result.positions),
                'success': len(result.errors) == 0,
                'error_count': len(result.errors),
                'warning_count': len(result.warnings)
            }
            
            self.execution_history.append(execution_record)
            
            # Update strategy metrics
            self._update_strategy_metrics(instance_id, template_id, execution_record)
            
            # Update template statistics
            self._update_template_stats(template_id, execution_record)
            
            # Analyze inheritance impact
            self._analyze_inheritance_performance(template_id)
            
            self.logger.debug(f"Recorded execution for instance {instance_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to record execution for {instance_id}: {e}")
    
    def get_strategy_performance(self, instance_id: str) -> Optional[PerformanceMetrics]:
        """Get performance metrics for a specific strategy instance"""
        return self.strategy_metrics.get(instance_id)
    
    def get_template_performance(self, template_id: str) -> Optional[TemplatePerformanceStats]:
        """Get aggregated performance statistics for a template"""
        return self.template_stats.get(template_id)
    
    def get_top_performing_strategies(self, limit: int = 10) -> List[Tuple[str, PerformanceMetrics]]:
        """Get top performing strategy instances"""
        
        # Sort by success rate, then by execution time
        sorted_strategies = sorted(
            self.strategy_metrics.items(),
            key=lambda x: (x[1].success_rate, -x[1].average_execution_time_ms),
            reverse=True
        )
        
        return sorted_strategies[:limit]
    
    def get_top_performing_templates(self, limit: int = 10) -> List[Tuple[str, TemplatePerformanceStats]]:
        """Get top performing templates"""
        
        sorted_templates = sorted(
            self.template_stats.items(),
            key=lambda x: (x[1].aggregate_success_rate, -x[1].average_execution_time_ms),
            reverse=True
        )
        
        return sorted_templates[:limit]
    
    def analyze_performance_trends(self, instance_id: str) -> Dict[str, Any]:
        """Analyze performance trends for a strategy instance"""
        
        # Get recent executions for this instance
        recent_executions = [
            ex for ex in list(self.execution_history)
            if ex['instance_id'] == instance_id
        ][-self.trend_analysis_window:]
        
        if len(recent_executions) < 10:
            return {
                'trend': 'insufficient_data',
                'confidence': 0.0,
                'analysis': 'Need at least 10 executions for trend analysis'
            }
        
        # Analyze execution time trend
        execution_times = [ex['execution_time_ms'] for ex in recent_executions]
        success_rates = []
        
        # Calculate rolling success rates
        window_size = min(10, len(recent_executions) // 3)
        for i in range(len(recent_executions) - window_size + 1):
            window = recent_executions[i:i + window_size]
            success_rate = sum(1 for ex in window if ex['success']) / len(window)
            success_rates.append(success_rate)
        
        # Determine trends
        time_trend = self._calculate_trend(execution_times)
        success_trend = self._calculate_trend(success_rates) if success_rates else 0
        
        # Overall assessment
        if success_trend > 0.1 and time_trend < -0.1:
            trend = "improving"
            confidence = min(abs(success_trend) + abs(time_trend), 1.0)
        elif success_trend < -0.1 or time_trend > 0.1:
            trend = "degrading"
            confidence = min(abs(success_trend) + abs(time_trend), 1.0)
        else:
            trend = "stable"
            confidence = 0.5
        
        return {
            'trend': trend,
            'confidence': confidence,
            'execution_time_trend': time_trend,
            'success_rate_trend': success_trend,
            'analysis': f"Performance is {trend} with {confidence:.1%} confidence",
            'recommendations': self._generate_performance_recommendations(instance_id, trend)
        }
    
    def analyze_inheritance_impact(self, template_id: str) -> InheritancePerformanceAnalysis:
        """Analyze performance impact of template inheritance"""
        
        template = self.template_registry.get_template(template_id)
        if not template:
            return InheritancePerformanceAnalysis(base_template_id=template_id)
        
        # Get inheritance chain
        parent_templates = template.metadata.parent_templates
        if not parent_templates:
            # This is a base template
            return self._analyze_base_template_performance(template_id)
        
        # Analyze derived template performance
        return self._analyze_derived_template_performance(template_id, parent_templates)
    
    def get_category_performance_comparison(self) -> Dict[str, Dict[str, float]]:
        """Compare performance across template categories"""
        
        category_metrics = defaultdict(list)
        
        # Group templates by category
        for template_id, stats in self.template_stats.items():
            template = self.template_registry.get_template(template_id)
            if template:
                category = template.metadata.category.value
                category_metrics[category].append(stats)
        
        # Calculate aggregate metrics per category
        comparison = {}
        for category, stats_list in category_metrics.items():
            if not stats_list:
                continue
            
            avg_success_rate = statistics.mean(s.aggregate_success_rate for s in stats_list)
            avg_execution_time = statistics.mean(s.average_execution_time_ms for s in stats_list)
            total_executions = sum(s.total_executions for s in stats_list)
            template_count = len(stats_list)
            
            comparison[category] = {
                'average_success_rate': avg_success_rate,
                'average_execution_time_ms': avg_execution_time,
                'total_executions': total_executions,
                'template_count': template_count,
                'executions_per_template': total_executions / template_count if template_count > 0 else 0
            }
        
        return comparison
    
    def generate_optimization_report(self, template_id: str) -> Dict[str, Any]:
        """Generate comprehensive optimization report for a template"""
        
        template_stats = self.get_template_performance(template_id)
        if not template_stats:
            return {'error': 'Template performance data not found'}
        
        inheritance_analysis = self.analyze_inheritance_impact(template_id)
        
        # Get performance alerts
        alerts = self._check_performance_alerts(template_id)
        
        # Get optimization suggestions
        suggestions = self._generate_optimization_suggestions(template_id)
        
        return {
            'template_id': template_id,
            'performance_summary': {
                'success_rate': template_stats.aggregate_success_rate,
                'execution_time_ms': template_stats.average_execution_time_ms,
                'total_executions': template_stats.total_executions,
                'instance_count': template_stats.instance_count
            },
            'inheritance_impact': {
                'performance_improvement': inheritance_analysis.performance_improvement,
                'overhead_ms': inheritance_analysis.inheritance_overhead_ms,
                'suggestions': inheritance_analysis.optimization_suggestions
            },
            'performance_alerts': alerts,
            'optimization_suggestions': suggestions,
            'category_ranking': self._get_template_category_ranking(template_id)
        }
    
    def _update_strategy_metrics(self, instance_id: str, template_id: str, 
                               execution_record: Dict[str, Any]):
        """Update performance metrics for a strategy instance"""
        
        if instance_id not in self.strategy_metrics:
            self.strategy_metrics[instance_id] = PerformanceMetrics(
                strategy_id=instance_id,
                template_id=template_id
            )
        
        metrics = self.strategy_metrics[instance_id]
        
        # Update execution counts
        metrics.total_executions += 1
        if execution_record['success']:
            metrics.successful_executions += 1
        
        # Update timing metrics
        new_time = execution_record['execution_time_ms']
        if metrics.total_executions == 1:
            metrics.average_execution_time_ms = new_time
        else:
            # Running average
            metrics.average_execution_time_ms = (
                (metrics.average_execution_time_ms * (metrics.total_executions - 1) + new_time) /
                metrics.total_executions
            )
        
        # Update signal and position metrics
        signal_count = execution_record['signal_count']
        position_count = execution_record['position_count']
        
        metrics.average_signals_per_execution = (
            (metrics.average_signals_per_execution * (metrics.total_executions - 1) + signal_count) /
            metrics.total_executions
        )
        
        metrics.average_positions_per_execution = (
            (metrics.average_positions_per_execution * (metrics.total_executions - 1) + position_count) /
            metrics.total_executions
        )
        
        # Update rates
        metrics.success_rate = metrics.successful_executions / metrics.total_executions
        metrics.error_rate = 1.0 - metrics.success_rate
        metrics.last_execution = execution_record['timestamp']
        
        # Update performance trend
        metrics.performance_trend = self._determine_performance_trend(instance_id)
    
    def _update_template_stats(self, template_id: str, execution_record: Dict[str, Any]):
        """Update aggregated statistics for a template"""
        
        if template_id not in self.template_stats:
            self.template_stats[template_id] = TemplatePerformanceStats(template_id=template_id)
        
        stats = self.template_stats[template_id]
        
        # Update execution count
        stats.total_executions += 1
        
        # Count unique instances using this template
        instances = set(
            ex['instance_id'] for ex in self.execution_history
            if ex['template_id'] == template_id
        )
        stats.instance_count = len(instances)
        
        # Calculate aggregate success rate for this template
        template_executions = [
            ex for ex in self.execution_history
            if ex['template_id'] == template_id
        ]
        
        if template_executions:
            successful = sum(1 for ex in template_executions if ex['success'])
            stats.aggregate_success_rate = successful / len(template_executions)
            
            # Calculate average execution time
            stats.average_execution_time_ms = statistics.mean(
                ex['execution_time_ms'] for ex in template_executions
            )
            
            # Find best and worst performing instances
            instance_performance = defaultdict(list)
            for ex in template_executions:
                instance_performance[ex['instance_id']].append(ex['success'])
            
            instance_success_rates = {
                instance_id: sum(successes) / len(successes)
                for instance_id, successes in instance_performance.items()
            }
            
            if instance_success_rates:
                stats.best_performing_instance = max(instance_success_rates, key=instance_success_rates.get)
                stats.worst_performing_instance = min(instance_success_rates, key=instance_success_rates.get)
    
    def _analyze_inheritance_performance(self, template_id: str):
        """Analyze inheritance performance impact"""
        
        template = self.template_registry.get_template(template_id)
        if not template or not template.metadata.parent_templates:
            return
        
        # Get performance data for this template and its parents
        current_stats = self.template_stats.get(template_id)
        if not current_stats:
            return
        
        parent_performance = []
        for parent_id in template.metadata.parent_templates:
            parent_stats = self.template_stats.get(parent_id)
            if parent_stats:
                parent_performance.append(parent_stats)
        
        if not parent_performance:
            return
        
        # Calculate performance improvement
        avg_parent_success_rate = statistics.mean(s.aggregate_success_rate for s in parent_performance)
        performance_improvement = current_stats.aggregate_success_rate - avg_parent_success_rate
        
        # Calculate inheritance overhead
        avg_parent_execution_time = statistics.mean(s.average_execution_time_ms for s in parent_performance)
        inheritance_overhead = current_stats.average_execution_time_ms - avg_parent_execution_time
        
        # Store analysis
        self.inheritance_performance[template_id] = InheritancePerformanceAnalysis(
            base_template_id=template.metadata.parent_templates[0],
            derived_template_ids=[template_id],
            performance_improvement=performance_improvement,
            inheritance_overhead_ms=inheritance_overhead,
            optimization_suggestions=self._generate_inheritance_suggestions(
                performance_improvement, inheritance_overhead
            )
        )
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend slope for a series of values"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x = list(range(n))
        
        # Calculate linear regression slope
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope / max(abs(y_mean), 1.0)  # Normalize by mean
    
    def _determine_performance_trend(self, instance_id: str) -> str:
        """Determine performance trend for an instance"""
        
        recent_executions = [
            ex for ex in list(self.execution_history)[-50:]  # Last 50 executions
            if ex['instance_id'] == instance_id
        ]
        
        if len(recent_executions) < 10:
            return "stable"
        
        # Analyze success rate trend
        success_values = [1.0 if ex['success'] else 0.0 for ex in recent_executions]
        success_trend = self._calculate_trend(success_values)
        
        if success_trend > 0.1:
            return "improving"
        elif success_trend < -0.1:
            return "degrading"
        else:
            return "stable"
    
    def _check_performance_alerts(self, template_id: str) -> List[Dict[str, Any]]:
        """Check for performance alerts"""
        
        alerts = []
        stats = self.template_stats.get(template_id)
        
        if not stats:
            return alerts
        
        # Check success rate
        if stats.aggregate_success_rate < self.performance_alert_thresholds['success_rate_min']:
            alerts.append({
                'type': 'low_success_rate',
                'severity': 'high',
                'message': f"Success rate {stats.aggregate_success_rate:.1%} below threshold {self.performance_alert_thresholds['success_rate_min']:.1%}",
                'value': stats.aggregate_success_rate,
                'threshold': self.performance_alert_thresholds['success_rate_min']
            })
        
        # Check execution time
        if stats.average_execution_time_ms > self.performance_alert_thresholds['execution_time_max_ms']:
            alerts.append({
                'type': 'high_execution_time',
                'severity': 'medium',
                'message': f"Execution time {stats.average_execution_time_ms:.1f}ms above threshold {self.performance_alert_thresholds['execution_time_max_ms']}ms",
                'value': stats.average_execution_time_ms,
                'threshold': self.performance_alert_thresholds['execution_time_max_ms']
            })
        
        return alerts
    
    def _generate_optimization_suggestions(self, template_id: str) -> List[str]:
        """Generate optimization suggestions for a template"""
        
        suggestions = []
        stats = self.template_stats.get(template_id)
        
        if not stats:
            return suggestions
        
        # Performance-based suggestions
        if stats.aggregate_success_rate < 0.9:
            suggestions.append("Consider reviewing risk management parameters to improve success rate")
        
        if stats.average_execution_time_ms > 500:
            suggestions.append("Optimize signal generation logic to reduce execution time")
        
        if stats.instance_count < 3:
            suggestions.append("Consider creating more instances to improve statistical reliability")
        
        # Template-specific suggestions
        template = self.template_registry.get_template(template_id)
        if template:
            if len(template.metadata.parent_templates) > 2:
                suggestions.append("Review inheritance chain - complex inheritance may impact performance")
            
            if len(template.components) < 3:
                suggestions.append("Consider adding more components for better strategy completeness")
        
        return suggestions
    
    def _generate_performance_recommendations(self, instance_id: str, trend: str) -> List[str]:
        """Generate performance recommendations based on trend"""
        
        recommendations = []
        
        if trend == "degrading":
            recommendations.extend([
                "Review recent parameter changes",
                "Check for data quality issues",
                "Consider reducing position sizes temporarily",
                "Review risk management settings"
            ])
        elif trend == "improving":
            recommendations.extend([
                "Monitor performance to maintain improvement",
                "Consider scaling up position sizes gradually",
                "Document successful parameter changes"
            ])
        else:  # stable
            recommendations.extend([
                "Performance is stable - consider optimization experiments",
                "Test parameter variations in small increments"
            ])
        
        return recommendations
    
    def _generate_inheritance_suggestions(self, performance_improvement: float, 
                                        overhead_ms: float) -> List[str]:
        """Generate suggestions for inheritance optimization"""
        
        suggestions = []
        
        if performance_improvement < 0:
            suggestions.append("Inheritance is reducing performance - consider simplifying template hierarchy")
        
        if overhead_ms > 100:
            suggestions.append("High inheritance overhead detected - optimize component merging logic")
        
        if performance_improvement > 0.1:
            suggestions.append("Inheritance is improving performance - consider applying similar patterns to other templates")
        
        return suggestions
    
    def _analyze_base_template_performance(self, template_id: str) -> InheritancePerformanceAnalysis:
        """Analyze performance of base template"""
        
        # Find all templates that inherit from this base template
        derived_templates = []
        for tid, template in self.template_registry.templates.items():
            if template_id in template.metadata.parent_templates:
                derived_templates.append(tid)
        
        return InheritancePerformanceAnalysis(
            base_template_id=template_id,
            derived_template_ids=derived_templates,
            optimization_suggestions=[
                f"Base template with {len(derived_templates)} derived templates"
            ]
        )
    
    def _analyze_derived_template_performance(self, template_id: str, 
                                            parent_templates: List[str]) -> InheritancePerformanceAnalysis:
        """Analyze performance of derived template"""
        
        return InheritancePerformanceAnalysis(
            base_template_id=parent_templates[0],
            derived_template_ids=[template_id],
            optimization_suggestions=["Derived template performance analysis"]
        )
    
    def _get_template_category_ranking(self, template_id: str) -> Dict[str, Any]:
        """Get ranking of template within its category"""
        
        template = self.template_registry.get_template(template_id)
        if not template:
            return {}
        
        category = template.metadata.category.value
        
        # Get all templates in same category
        category_templates = []
        for tid, stats in self.template_stats.items():
            tmpl = self.template_registry.get_template(tid)
            if tmpl and tmpl.metadata.category.value == category:
                category_templates.append((tid, stats))
        
        # Sort by performance
        category_templates.sort(key=lambda x: x[1].aggregate_success_rate, reverse=True)
        
        # Find ranking
        for i, (tid, _) in enumerate(category_templates):
            if tid == template_id:
                return {
                    'rank': i + 1,
                    'total_in_category': len(category_templates),
                    'percentile': ((len(category_templates) - i) / len(category_templates)) * 100
                }
        
        return {}
