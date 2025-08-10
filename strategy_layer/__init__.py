"""
Trading Strategy Layer

A comprehensive strategy layer that provides centralized strategy definition, 
management, optimization, and execution capabilities using JSON-based definitions 
and modular building blocks.

Author: Pro Quant Desk Trader
"""

from .base import (
    StrategyDefinition,
    StrategyConfig,
    StrategyResult,
    BaseConfig,
    ParserConfig
)

from .parsers import (
    StrategyParser,
    SchemaValidator
)

from .builders import (
    StrategyBuilder,
    StrategyFactory
)

from .blocks import (
    SignalGenerator,
    PositionSizer,
    RiskManager,
    EntryExitLogic
)

from .strategies import (
    MomentumStrategyDefinition,
    PairTradingStrategyDefinition,
    MeanReversionStrategyDefinition
)

from .optimization import (
    ParameterOptimizer,
    GeneticOptimizer,
    BayesianOptimizer,
    GridSearchOptimizer,
    RandomSearchOptimizer
)

from .validation import (
    StrategyValidator,
    ParameterValidator
)

from .deployment import (
    StrategyDeployer,
    DeploymentConfig,
    DeploymentResult,
    DeploymentInfo,
    DeploymentStatus,
    EnvironmentType,
    EnvironmentManager,
    EnvironmentConfig
)

from .monitoring import (
    StrategyMonitor,
    MonitoringConfig,
    PerformanceMetrics,
    HealthStatus,
    Alert,
    MonitorStatus,
    AlertLevel,
    PerformanceAnalytics,
    PerformanceReport
)

from .testing import (
    StrategyTestSuite,
    TestResult,
    RegressionTestSuite,
    RegressionTestResult
)

from .registry import StrategyRegistry

__all__ = [
    # Base classes
    'StrategyDefinition',
    'StrategyConfig', 
    'StrategyResult',
    'BaseConfig',
    'ParserConfig',
    
    # Parsers
    'StrategyParser',
    'SchemaValidator',
    
    # Builders
    'StrategyBuilder',
    'StrategyFactory',
    
    # Building blocks
    'SignalGenerator',
    'PositionSizer',
    'RiskManager',
    'EntryExitLogic',
    
    # Strategies
    'MomentumStrategyDefinition',
    'PairTradingStrategyDefinition',
    'MeanReversionStrategyDefinition',
    
    # Optimization
    'ParameterOptimizer',
    'GeneticOptimizer',
    'BayesianOptimizer',
    'GridSearchOptimizer',
    'RandomSearchOptimizer',
    
    # Validation
    'StrategyValidator',
    'ParameterValidator',
    
    # Testing
    'StrategyTestSuite',
    'TestResult',
    'RegressionTestSuite',
    'RegressionTestResult',
    
    # Deployment
    'StrategyDeployer',
    'DeploymentConfig',
    'DeploymentResult',
    'DeploymentInfo',
    'DeploymentStatus',
    'EnvironmentType',
    'EnvironmentManager',
    'EnvironmentConfig',
    
    # Monitoring
    'StrategyMonitor',
    'MonitoringConfig',
    'PerformanceMetrics',
    'HealthStatus',
    'Alert',
    'MonitorStatus',
    'AlertLevel',
    'PerformanceAnalytics',
    'PerformanceReport',
    
    # Registry
    'StrategyRegistry'
]

__version__ = "1.0.0"
__author__ = "Pro Quant Desk Trader"
