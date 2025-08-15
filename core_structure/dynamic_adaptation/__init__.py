"""
Dynamic Adaptation Module - Complete Template-Aware Dynamic Adaptation System
==============================================================================

Comprehensive dynamic adaptation capabilities for the trading system with full template inheritance support.
Provides runtime strategy evolution across all system components with unified coordination.

Phase 3 Complete Implementation:
- Week 21-22: Foundation components (5 modules)
- Week 23-24: Component-specific adaptations (4 modules)  
- Week 25: Unified integration (1 module)
Total: 10 dynamic adaptation modules

Author: Pro Quant Desk Trader
"""

# Foundation Components (Week 21-22)
from .dynamic_adaptation_framework import (
    DynamicAdaptationFramework, AdaptationFrameworkConfig,
    AdaptationTrigger, AdaptationMode, AdaptationResult
)

from .performance_adaptation import (
    PerformanceAdaptation, PerformanceAdaptationConfig,
    PerformanceDegradationLevel, PerformanceThreshold
)

from .market_regime_adaptation import (
    MarketRegimeAdaptation, MarketRegimeConfig,
    MarketRegime, RegimeTransition, RegimeAdaptationRule
)

from .parameter_optimizer import (
    ParameterOptimizer, OptimizationConfig,
    OptimizationMethod, ParameterBounds, OptimizationResult
)

from .adaptation_coordinator import (
    AdaptationCoordinator, CoordinatorConfig,
    AdaptationPriority, AdaptationConflictResolution
)

# Component-Specific Adaptations (Week 23-24)
from .dynamic_signal_generation import (
    DynamicSignalGeneration, SignalGenerationConfig, SignalAdaptationMode,
    IndicatorType, IndicatorConfig
)

from .dynamic_risk_control import (
    DynamicRiskControl, RiskControlConfig, RiskAdaptationMode,
    RiskParameters, RiskAdaptationResult
)

from .dynamic_portfolio_management import (
    DynamicPortfolioManagement, PortfolioConfig, PortfolioAdaptationMode,
    PortfolioParameters, PortfolioMetrics, PortfolioAdaptationResult
)

from .dynamic_execution_control import (
    DynamicExecutionControl, ExecutionConfig, ExecutionAdaptationMode,
    ExecutionParameters, ExecutionMetrics, ExecutionAdaptationResult, OrderType, ExecutionAlgorithm
)

# Unified Integration (Week 25)
from .unified_dynamic_adaptation_manager import (
    UnifiedDynamicAdaptationManager, IntegrationConfig, AdaptationIntegrationMode, 
    IntegrationResult, SystemMetrics
)

__all__ = [
    # Foundation Components (Week 21-22)
    'DynamicAdaptationFramework',
    'AdaptationFrameworkConfig',
    'AdaptationTrigger',
    'AdaptationMode',
    'AdaptationResult',
    
    'PerformanceAdaptation',
    'PerformanceAdaptationConfig',
    'PerformanceDegradationLevel',
    'PerformanceThreshold',
    
    'MarketRegimeAdaptation',
    'MarketRegimeConfig',
    'MarketRegime',
    'RegimeTransition',
    'RegimeAdaptationRule',
    
    'ParameterOptimizer',
    'OptimizationConfig',
    'OptimizationMethod',
    'ParameterBounds',
    'OptimizationResult',
    
    'AdaptationCoordinator',
    'CoordinatorConfig',
    'AdaptationPriority',
    'AdaptationConflictResolution',
    
    # Component-Specific Adaptations (Week 23-24)
    'DynamicSignalGeneration',
    'SignalGenerationConfig',
    'SignalAdaptationMode',
    'IndicatorType',
    'IndicatorConfig',
    
    'DynamicRiskControl',
    'RiskControlConfig', 
    'RiskAdaptationMode',
    'RiskParameters',
    'RiskAdaptationResult',
    
    'DynamicPortfolioManagement',
    'PortfolioConfig',
    'PortfolioAdaptationMode',
    'PortfolioParameters',
    'PortfolioMetrics',
    'PortfolioAdaptationResult',
    
    'DynamicExecutionControl',
    'ExecutionConfig',
    'ExecutionAdaptationMode',
    'ExecutionParameters',
    'ExecutionMetrics',
    'ExecutionAdaptationResult',
    'OrderType',
    'ExecutionAlgorithm',
    
    # Unified Integration (Week 25)
    'UnifiedDynamicAdaptationManager',
    'IntegrationConfig',
    'AdaptationIntegrationMode',
    'IntegrationResult',
    'SystemMetrics'
]