"""
Core Structure Dynamic Parameter Adaptation System
=================================================

Real-time parameter optimization, validation, and rollback capabilities
integrated into core_structure optimization framework.

Enhanced with Complete Threshold Dynamization:
- AdaptiveThresholdManager: Intelligent threshold adaptation
- Regime-aware threshold adjustments
- Performance-based threshold optimization
- Complete replacement of fixed thresholds

Migration Summary:
- Moved from trade_engine/dynamic_adaptation to core_structure/optimization/dynamic_adaptation
- Full integration with unified optimization framework
- Enhanced performance through core_structure infrastructure
- Added comprehensive adaptive threshold system

Key Components:
- RealTimeParameterOptimizer: Core optimization engine
- AdaptiveThresholdManager: Complete threshold dynamization
- AdaptiveThresholdIntegration: System integration layer
- ParameterValidator: Bounds and constraint validation
- AdaptationRollbackManager: Performance monitoring and rollback
- AdaptationMetrics: Performance tracking and analysis

Author: Professional Trading System Architecture
Version: 3.0.0 (Complete Threshold Dynamization)
"""

from .parameter_optimizer import RealTimeParameterOptimizer, ParameterOptimizationResult
from .parameter_validator import ParameterValidator, ValidationResult
from .adaptation_rollback import AdaptationRollbackManager, AdaptationSnapshot, RollbackDecision
from .adaptation_metrics import AdaptationMetrics, PerformanceSnapshot
from .adaptation_config import AdaptationConfig, AdaptationTriggers, AdaptationMode, AdaptationBounds
from .adaptive_threshold_manager import (
    AdaptiveThresholdManager, 
    AdaptiveThreshold, 
    ThresholdBounds, 
    ThresholdType
)
from .adaptive_threshold_integration import (
    AdaptiveThresholdIntegration,
    AdaptiveThresholdPerformanceMonitor,
    setup_adaptive_thresholds,
    enable_adaptive_thresholds_for_strategy,
    update_strategy_thresholds_from_performance
)

__all__ = [
    # Core optimization
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
    'AdaptationBounds',
    
    # Adaptive thresholds
    'AdaptiveThresholdManager',
    'AdaptiveThreshold',
    'ThresholdBounds',
    'ThresholdType',
    'AdaptiveThresholdIntegration',
    'AdaptiveThresholdPerformanceMonitor',
    
    # Integration utilities
    'setup_adaptive_thresholds',
    'enable_adaptive_thresholds_for_strategy', 
    'update_strategy_thresholds_from_performance'
]

# Version information
__version__ = "3.0.0"
__adaptive_thresholds_version__ = "1.0.0"

def get_adaptive_threshold_info():
    """Get information about the adaptive threshold system."""
    return {
        'version': __version__,
        'adaptive_thresholds_version': __adaptive_thresholds_version__,
        'features': [
            'Complete threshold dynamization',
            'Regime-aware adaptations', 
            'Performance-based optimization',
            'Real-time threshold updates',
            'Rollback support',
            'Configuration backup/restore'
        ],
        'supported_threshold_types': [threshold_type.value for threshold_type in ThresholdType],
        'supported_strategies': ['momentum', 'mean_reversion', 'pairs_trading'],
        'integration_ready': True
    }

# Version information
__version__ = "3.0.0"
__author__ = "Professional Trading System Architecture"
__description__ = "Complete Threshold Dynamization System"
