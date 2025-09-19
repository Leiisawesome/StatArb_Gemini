"""
Analytics Engine - Component Initialization
Unified imports and component registry for the analytics engine
"""

from .performance_analyzer import (
    PerformanceAnalyzer,
    PerformanceConfig,
    PerformanceMetrics,
    RiskMetrics,
    DrawdownAnalysis
)

from .attribution_analyzer import (
    AttributionAnalyzer,
    AttributionConfig,
    AttributionResult,
    FactorAttribution,
    SectorAttribution
)

from .metrics_calculator import (
    MetricsCalculator,
    MetricConfig,
    MetricResult,
    MetricsBundle,
    MetricCategory,
    MetricFrequency
)

from .report_generator import (
    ReportGenerator,
    ReportConfig,
    ReportData,
    ReportFormat,
    ChartConfig,
    ChartType
)

from .benchmark_analyzer import (
    BenchmarkAnalyzer,
    BenchmarkConfig,
    BenchmarkData,
    ComparisonResult,
    FactorAnalysisResult
)

from .manager_enhanced import (
    AnalyticsManager,
    AnalyticsConfig,
    AnalyticsTask,
    AnalyticsResults,
    AnalyticsMode,
    AnalyticsPriority
)

# Version information
__version__ = "1.0.0"
__author__ = "StatArb Analytics Team"

# Component registry
ANALYTICS_COMPONENTS = {
    'performance_analyzer': PerformanceAnalyzer,
    'attribution_analyzer': AttributionAnalyzer,
    'metrics_calculator': MetricsCalculator,
    'report_generator': ReportGenerator,
    'benchmark_analyzer': BenchmarkAnalyzer,
    'manager': AnalyticsManager
}

# Configuration registry
ANALYTICS_CONFIGS = {
    'performance_config': PerformanceConfig,
    'attribution_config': AttributionConfig,
    'metrics_config': MetricConfig,
    'report_config': ReportConfig,
    'benchmark_config': BenchmarkConfig,
    'analytics_config': AnalyticsConfig
}

# Default configurations
DEFAULT_ANALYTICS_CONFIG = AnalyticsConfig()
DEFAULT_PERFORMANCE_CONFIG = PerformanceConfig()
DEFAULT_ATTRIBUTION_CONFIG = AttributionConfig()
DEFAULT_METRICS_CONFIG = MetricConfig()
DEFAULT_REPORT_CONFIG = ReportConfig()
DEFAULT_BENCHMARK_CONFIG = BenchmarkConfig()

def create_analytics_manager(config=None):
    """
    Factory function to create analytics manager with default or custom configuration
    
    Args:
        config: AnalyticsConfig instance or None for default
        
    Returns:
        AnalyticsManager instance
    """
    if config is None:
        config = DEFAULT_ANALYTICS_CONFIG
    
    return AnalyticsManager(config)

def create_performance_analyzer(config=None):
    """
    Factory function to create performance analyzer
    
    Args:
        config: PerformanceConfig instance or None for default
        
    Returns:
        PerformanceAnalyzer instance
    """
    if config is None:
        config = DEFAULT_PERFORMANCE_CONFIG
    
    return PerformanceAnalyzer(config)

def create_attribution_analyzer(config=None):
    """
    Factory function to create attribution analyzer
    
    Args:
        config: AttributionConfig instance or None for default
        
    Returns:
        AttributionAnalyzer instance
    """
    if config is None:
        config = DEFAULT_ATTRIBUTION_CONFIG
    
    return AttributionAnalyzer(config)

def create_metrics_calculator(config=None):
    """
    Factory function to create metrics calculator
    
    Args:
        config: MetricConfig instance or None for default
        
    Returns:
        MetricsCalculator instance
    """
    if config is None:
        config = DEFAULT_METRICS_CONFIG
    
    return MetricsCalculator(config)

def create_report_generator(config=None):
    """
    Factory function to create report generator
    
    Args:
        config: ReportConfig instance or None for default
        
    Returns:
        ReportGenerator instance
    """
    if config is None:
        config = DEFAULT_REPORT_CONFIG
    
    return ReportGenerator(config)

def create_benchmark_analyzer(config=None):
    """
    Factory function to create benchmark analyzer
    
    Args:
        config: BenchmarkConfig instance or None for default
        
    Returns:
        BenchmarkAnalyzer instance
    """
    if config is None:
        config = DEFAULT_BENCHMARK_CONFIG
    
    return BenchmarkAnalyzer(config)

# Convenience imports for common use cases
__all__ = [
    # Core classes
    'AnalyticsManager',
    'PerformanceAnalyzer', 
    'AttributionAnalyzer',
    'MetricsCalculator',
    'ReportGenerator',
    'BenchmarkAnalyzer',
    
    # Configuration classes
    'AnalyticsConfig',
    'PerformanceConfig',
    'AttributionConfig', 
    'MetricConfig',
    'ReportConfig',
    'BenchmarkConfig',
    
    # Data classes
    'AnalyticsResults',
    'AnalyticsTask',
    'PerformanceMetrics',
    'AttributionResult',
    'MetricResult',
    'MetricsBundle',
    'ReportData',
    'BenchmarkData',
    'ComparisonResult',
    'FactorAnalysisResult',
    
    # Enums
    'AnalyticsMode',
    'AnalyticsPriority',
    'MetricCategory',
    'MetricFrequency',
    'ReportFormat',
    'ChartType',
    
    # Factory functions
    'create_analytics_manager',
    'create_performance_analyzer',
    'create_attribution_analyzer',
    'create_metrics_calculator',
    'create_report_generator',
    'create_benchmark_analyzer',
    
    # Default configs
    'DEFAULT_ANALYTICS_CONFIG',
    'DEFAULT_PERFORMANCE_CONFIG',
    'DEFAULT_ATTRIBUTION_CONFIG',
    'DEFAULT_METRICS_CONFIG',
    'DEFAULT_REPORT_CONFIG',
    'DEFAULT_BENCHMARK_CONFIG',
    
    # Registries
    'ANALYTICS_COMPONENTS',
    'ANALYTICS_CONFIGS'
]