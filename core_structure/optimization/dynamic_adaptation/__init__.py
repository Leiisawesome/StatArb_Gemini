"""
Core Structure Dynamic Parameter Adaptation System
=================================================

Real-time parameter optimization, validation, and rollback capabilities
integrated into core_structure optimization framework.

Migration Summary:
- Moved from trade_engine/dynamic_adaptation to core_structure/optimization/dynamic_adaptation
- Full integration with unified optimization framework
- Enhanced performance through core_structure infrastructure

Key Components:
- RealTimeParameterOptimizer: Core optimization engine
- ParameterValidator: Bounds and constraint validation
- AdaptationRollbackManager: Performance monitoring and rollback
- AdaptationMetrics: Performance tracking and analysis

Author: Professional Trading System Architecture
Version: 2.0.0 (Core Structure Integrated)
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
