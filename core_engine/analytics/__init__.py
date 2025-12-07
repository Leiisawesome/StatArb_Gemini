"""
Analytics Engine - Component Initialization
Unified imports and component registry for the analytics engine
"""

# === CORE METRICS (Single Source of Truth) ===
from .core_metrics import (
    # VaR metrics
    calculate_var,
    calculate_cvar,
    VarMethod,
    # Risk-adjusted returns
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_information_ratio,
    # Drawdown metrics
    calculate_drawdown,
    # Volatility metrics
    calculate_volatility,
    calculate_downside_volatility,
    # Return metrics
    calculate_annualized_return,
    calculate_total_return,
    # Higher moments
    calculate_skewness,
    calculate_kurtosis,
    # Benchmark-relative
    calculate_beta,
    calculate_alpha,
    calculate_tracking_error
)

from .performance_analyzer import (
    PerformanceAnalyzer,
    PerformanceConfig,
    PerformanceMetrics
)

from .attribution_analyzer import (
    AttributionAnalyzer,
    AttributionConfig,
    AttributionResult
)

from .metrics_calculator import (
    EnhancedMetricsCalculator,
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
    EnhancedAnalyticsManager,
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
    'metrics_calculator': EnhancedMetricsCalculator,
    'report_generator': ReportGenerator,
    'benchmark_analyzer': BenchmarkAnalyzer,
    'manager': EnhancedAnalyticsManager
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

    return EnhancedAnalyticsManager(config)

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

    return EnhancedMetricsCalculator(config)

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
    # === CORE METRICS (Single Source of Truth) ===
    # VaR functions
    'calculate_var',
    'calculate_cvar',
    'VarMethod',
    # Risk-adjusted returns
    'calculate_sharpe_ratio',
    'calculate_sortino_ratio',
    'calculate_calmar_ratio',
    'calculate_information_ratio',
    # Drawdown
    'calculate_drawdown',
    # Volatility
    'calculate_volatility',
    'calculate_downside_volatility',
    # Returns
    'calculate_annualized_return',
    'calculate_total_return',
    # Higher moments
    'calculate_skewness',
    'calculate_kurtosis',
    # Benchmark-relative
    'calculate_beta',
    'calculate_alpha',
    'calculate_tracking_error',

    # Core classes
    'EnhancedAnalyticsManager',
    'PerformanceAnalyzer',
    'AttributionAnalyzer',
    'EnhancedMetricsCalculator',
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