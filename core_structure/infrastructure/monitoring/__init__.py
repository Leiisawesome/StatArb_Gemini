"""
Real-Time Performance Monitoring Infrastructure
==============================================

This module provides real-time monitoring, continuous optimization,
and auto-tuning capabilities for the unified core engine.

Components:
- MetricsCollector: Core metrics collection system (legacy)
- RealTimeMonitor: Live performance tracking and alerting
- ContinuousOptimizer: Dynamic parameter tuning
- AutoTuner: Automated performance optimization
- PerformanceDashboard: Real-time metrics visualization
"""

# Legacy metrics collector
from .metrics_collector import MetricsCollector

# New monitoring infrastructure
from .real_time_monitor import RealTimeMonitor, MonitorConfig, MetricType, AlertLevel, PerformanceAlert
from .continuous_optimizer import ContinuousOptimizer, OptimizerConfig, Parameter, ParameterType  
from .auto_tuner import AutoTuner, AutoTunerConfig, TuningMode
from .performance_dashboard import PerformanceDashboard, DashboardConfig

__all__ = [
    'MetricsCollector',
    'RealTimeMonitor',
    'MonitorConfig',
    'MetricType',
    'AlertLevel', 
    'PerformanceAlert',
    'ContinuousOptimizer',
    'OptimizerConfig',
    'Parameter',
    'ParameterType',
    'AutoTuner', 
    'AutoTunerConfig',
    'TuningMode',
    'PerformanceDashboard',
    'DashboardConfig'
]