"""
Performance Analytics

Basic performance analytics for trading strategies.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .strategy_monitor import PerformanceMetrics, HealthStatus, Alert


@dataclass
class PerformanceReport:
    """Performance report"""
    strategy_id: str
    report_period: str
    start_time: datetime
    end_time: datetime
    total_executions: int
    success_rate: float
    error_rate: float
    avg_execution_time: float
    avg_memory_usage: float
    avg_cpu_usage: float
    health_score: float
    alert_count: int
    performance_trend: str
    recommendations: List[str] = field(default_factory=list)


class PerformanceAnalytics:
    """Performance analytics engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_performance_report(self, strategy_id: str, 
                                  performance_metrics: List[PerformanceMetrics],
                                  health_statuses: List[HealthStatus],
                                  alerts: List[Alert],
                                  period_hours: int = 24) -> PerformanceReport:
        """Generate performance report"""
        if not performance_metrics:
            return self._create_empty_report(strategy_id, period_hours)
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=period_hours)
        
        # Filter metrics for the period
        period_metrics = [
            m for m in performance_metrics
            if start_time <= m.timestamp <= end_time
        ]
        
        if not period_metrics:
            return self._create_empty_report(strategy_id, period_hours)
        
        # Calculate basic metrics
        total_executions = sum(m.total_executions for m in period_metrics)
        success_count = sum(m.success_count for m in period_metrics)
        error_count = sum(m.error_count for m in period_metrics)
        
        success_rate = success_count / total_executions if total_executions > 0 else 0.0
        error_rate = error_count / total_executions if total_executions > 0 else 0.0
        
        # Calculate execution time
        execution_times = [m.execution_time for m in period_metrics if m.execution_time > 0]
        avg_execution_time = float(np.mean(execution_times)) if execution_times else 0.0
        
        # Calculate resource usage
        memory_usage = [m.memory_usage for m in period_metrics]
        cpu_usage = [m.cpu_usage for m in period_metrics]
        
        avg_memory_usage = float(np.mean(memory_usage)) if memory_usage else 0.0
        avg_cpu_usage = float(np.mean(cpu_usage)) if cpu_usage else 0.0
        
        # Calculate health score
        health_scores = [h.health_score for h in health_statuses if start_time <= h.timestamp <= end_time]
        avg_health_score = float(np.mean(health_scores)) if health_scores else 100.0
        
        # Calculate alert count
        period_alerts = [a for a in alerts if start_time <= a.timestamp <= end_time]
        alert_count = len(period_alerts)
        
        # Determine performance trend
        performance_trend = self._determine_performance_trend(period_metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            success_rate, error_rate, avg_execution_time, avg_health_score, alert_count
        )
        
        return PerformanceReport(
            strategy_id=strategy_id,
            report_period=f"{period_hours}h",
            start_time=start_time,
            end_time=end_time,
            total_executions=total_executions,
            success_rate=success_rate,
            error_rate=error_rate,
            avg_execution_time=avg_execution_time,
            avg_memory_usage=avg_memory_usage,
            avg_cpu_usage=avg_cpu_usage,
            health_score=avg_health_score,
            alert_count=alert_count,
            performance_trend=performance_trend,
            recommendations=recommendations
        )
    
    def calculate_performance_score(self, performance_metrics: List[PerformanceMetrics],
                                  health_statuses: List[HealthStatus],
                                  alerts: List[Alert]) -> float:
        """Calculate overall performance score (0-100)"""
        if not performance_metrics:
            return 0.0
        
        # Calculate component scores
        execution_score = self._calculate_execution_score(performance_metrics)
        health_score = self._calculate_health_score(health_statuses)
        alert_score = self._calculate_alert_score(alerts)
        
        # Weighted average
        overall_score = (
            execution_score * 0.4 +
            health_score * 0.4 +
            alert_score * 0.2
        )
        
        return max(0.0, min(100.0, overall_score))
    
    def _create_empty_report(self, strategy_id: str, period_hours: int) -> PerformanceReport:
        """Create empty performance report"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=period_hours)
        
        return PerformanceReport(
            strategy_id=strategy_id,
            report_period=f"{period_hours}h",
            start_time=start_time,
            end_time=end_time,
            total_executions=0,
            success_rate=0.0,
            error_rate=0.0,
            avg_execution_time=0.0,
            avg_memory_usage=0.0,
            avg_cpu_usage=0.0,
            health_score=100.0,
            alert_count=0,
            performance_trend='stable',
            recommendations=['No data available for analysis']
        )
    
    def _determine_performance_trend(self, metrics: List[PerformanceMetrics]) -> str:
        """Determine performance trend"""
        if len(metrics) < 2:
            return 'stable'
        
        success_rates = [m.success_rate for m in metrics]
        if len(success_rates) >= 2:
            success_trend = np.polyfit(range(len(success_rates)), success_rates, 1)[0]
            if success_trend > 0.01:
                return 'improving'
            elif success_trend < -0.01:
                return 'declining'
        
        return 'stable'
    
    def _generate_recommendations(self, success_rate: float, error_rate: float,
                                avg_execution_time: float, health_score: float,
                                alert_count: int) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        
        if success_rate < 0.9:
            recommendations.append("Low success rate - review strategy logic")
        
        if error_rate > 0.1:
            recommendations.append("High error rate - investigate error sources")
        
        if avg_execution_time > 0.5:
            recommendations.append("High execution time - optimize performance")
        
        if health_score < 70:
            recommendations.append("Poor health score - investigate stability")
        
        if alert_count > 5:
            recommendations.append("High alert count - review monitoring")
        
        if not recommendations:
            recommendations.append("Strategy performing well")
        
        return recommendations
    
    def _calculate_execution_score(self, metrics: List[PerformanceMetrics]) -> float:
        """Calculate execution score"""
        if not metrics:
            return 100.0
        
        success_rates = [m.success_rate for m in metrics]
        avg_success_rate = float(np.mean(success_rates)) if success_rates else 0.0
        return avg_success_rate * 100
    
    def _calculate_health_score(self, health_statuses: List[HealthStatus]) -> float:
        """Calculate health score"""
        if not health_statuses:
            return 100.0
        
        health_scores = [h.health_score for h in health_statuses]
        return float(np.mean(health_scores))
    
    def _calculate_alert_score(self, alerts: List[Alert]) -> float:
        """Calculate alert score"""
        if not alerts:
            return 100.0
        
        total_penalty = 0
        for alert in alerts:
            if alert.level.value == 'critical':
                total_penalty += 20
            elif alert.level.value == 'error':
                total_penalty += 10
            elif alert.level.value == 'warning':
                total_penalty += 5
        
        return max(0.0, 100.0 - total_penalty)
