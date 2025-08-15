"""
Template Integration for Core Engine
====================================

Template-aware integration layer for the unified core engine,
providing template-compatible components with inheritance support
and three-tier category management.

Author: Pro Quant Desk Trader
"""

# Import with error handling to avoid circular dependencies
try:
    from .template_core_engine import (
        TemplateCoreEngine, TemplateEngineConfig, ExecutionMode, TemplateExecutionResult
    )
except ImportError:
    TemplateCoreEngine = None
    TemplateEngineConfig = None
    ExecutionMode = None
    TemplateExecutionResult = None

try:
    from .template_component_manager import TemplateComponentManager, ComponentRegistry
except ImportError:
    TemplateComponentManager = None
    ComponentRegistry = None

try:
    from .template_execution_coordinator import TemplateExecutionCoordinator, CoordinatorConfig
except ImportError:
    TemplateExecutionCoordinator = None
    CoordinatorConfig = None

try:
    from .template_performance_integrator import (
        TemplatePerformanceIntegrator, PerformanceSnapshot, PerformanceMetric
    )
except ImportError:
    TemplatePerformanceIntegrator = None
    PerformanceSnapshot = None
    PerformanceMetric = None

try:
    from .category_aware_core_components import (
        CategoryAwareCoreComponents, CategoryAwareComponent,
        CategoryAwareSignalProcessor, CategoryAwareRiskAnalyzer,
        ComponentAdaptationConfig, AdaptationStrategy
    )
except ImportError:
    CategoryAwareCoreComponents = None
    CategoryAwareComponent = None
    CategoryAwareSignalProcessor = None
    CategoryAwareRiskAnalyzer = None
    ComponentAdaptationConfig = None
    AdaptationStrategy = None

__all__ = [
    'TemplateCoreEngine',
    'TemplateEngineConfig',
    'ExecutionMode',
    'TemplateExecutionResult',
    'TemplateComponentManager',
    'ComponentRegistry',
    'TemplateExecutionCoordinator',
    'CoordinatorConfig',
    'TemplatePerformanceIntegrator',
    'PerformanceSnapshot',
    'PerformanceMetric',
    'CategoryAwareCoreComponents',
    'CategoryAwareComponent',
    'CategoryAwareSignalProcessor',
    'CategoryAwareRiskAnalyzer',
    'ComponentAdaptationConfig',
    'AdaptationStrategy'
]
