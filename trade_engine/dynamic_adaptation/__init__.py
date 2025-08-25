"""
Dynamic Parameter Adaptation System for Trade Engine.

This module provides real-time parameter optimization, validation, and rollback
capabilities for trading strategies. It integrates with the template system to
ensure parameter changes remain within defined bounds while optimizing for
performance.

Key Components:
- RealTimeParameterOptimizer: Core optimization engine
- ParameterValidator: Bounds and constraint validation
- AdaptationRollbackManager: Performance monitoring and rollback
- AdaptationMetrics: Performance tracking and analysis
"""

from .parameter_optimizer import RealTimeParameterOptimizer, ParameterOptimizationResult
from .parameter_validator import ParameterValidator, ValidationResult
from .adaptation_rollback import AdaptationRollbackManager, AdaptationSnapshot, RollbackDecision
from .adaptation_metrics import AdaptationMetrics, PerformanceSnapshot
from .adaptation_config import AdaptationConfig, AdaptationTriggers, AdaptationMode, AdaptationBounds

__all__ = [
    'RealTimeParameterOptimizer',
    'ParameterOptimizationResult', 
    'ParameterValidator',
    'ValidationResult',
    'AdaptationRollbackManager',
    'AdaptationSnapshot',
    'RollbackDecision',
    'AdaptationMetrics',
    'PerformanceSnapshot',
    'AdaptationConfig',
    'AdaptationTriggers',
    'AdaptationMode',
    'AdaptationBounds'
]
