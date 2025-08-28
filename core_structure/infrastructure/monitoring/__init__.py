"""
Real-Time Performance Monitoring Infrastructure
==============================================

Phase 5B Infrastructure Consolidation - Monitoring Module
Consolidated monitoring functionality into unified systems.

This module provides real-time monitoring, continuous optimization,
and auto-tuning capabilities for the unified core engine.

Consolidated Components:
- optimization_system: Unified optimization and auto-tuning (from continuous_optimizer + auto_tuner)
- monitoring_system: Unified monitoring and visualization (from performance_dashboard + real_time_monitor + metrics_collector)

Legacy Support:
- Individual component imports maintained for backward compatibility
"""

# Phase 5B Consolidated Systems
from .optimization_system import (
    ContinuousOptimizer,
    AutoTuner,
    OptimizationSystemFactory,
    OptimizerConfig,
    AutoTunerConfig,
    Parameter,
    ParameterType,
    OptimizationStrategy,
    TuningMode,
    TuningPhase
)

from .monitoring_system import (
    MetricsCollector,
    RealTimeMonitor,
    PerformanceDashboard,
    MonitoringSystemFactory,
    MonitorConfig,
    DashboardConfig,
    MetricsConfig,
    MetricType,
    AlertLevel,
    DashboardMode,
    MonitoringStatus,
    PerformanceAlert,
    DashboardMetric,
    SystemHealth,
    MetricValue
)

# Legacy backward compatibility imports
# Note: These now reference the consolidated modules
from .optimization_system import ContinuousOptimizer, AutoTuner
from .monitoring_system import MetricsCollector, RealTimeMonitor, PerformanceDashboard

__all__ = [
    # Consolidated System Factories
    'OptimizationSystemFactory',
    'MonitoringSystemFactory',
    
    # Optimization System Components
    'ContinuousOptimizer',
    'AutoTuner',
    'OptimizerConfig',
    'AutoTunerConfig',
    'Parameter',
    'ParameterType',
    'OptimizationStrategy',
    'TuningMode',
    'TuningPhase',
    
    # Monitoring System Components
    'MetricsCollector',
    'RealTimeMonitor',
    'PerformanceDashboard',
    'MonitorConfig',
    'DashboardConfig',
    'MetricsConfig',
    'MetricType',
    'AlertLevel',
    'DashboardMode',
    'MonitoringStatus',
    'PerformanceAlert',
    'DashboardMetric',
    'SystemHealth',
    'MetricValue'
]