"""
Core Engine Configuration Module
=================================

Centralized configuration management with consolidated configs.

Phase 4 Consolidation: 70 configs → 25 configs (-64%)
Architecture: Composition pattern with reusable sub-configs
"""

# Master configuration orchestrator
from .unified_config import (
    UnifiedConfig,
    ConfigFormat,
    ConfigSource,
    get_config,
    init_config,
    config_get,
    config_set,
    config_section
)

# System-wide configuration
from .system_config import SystemConfig, BacktestConfig, BacktestMode

# Broker configuration
from .broker_config import (
    BrokerConfig,
    InteractiveBrokersConfig,
    BrokerConfigLoader,
    TradingMode,
    BrokerType,
    RiskLimits as BrokerRiskLimits,  # Alias to avoid conflict
    load_broker_config
)

# Component configurations (CONSOLIDATED - Phase 4)
from .component_config import (
    # Sub-configs (reusable building blocks)
    PositionLimits,
    RiskLimits,
    TimingConfig,
    PerformanceConfig,

    # Data brick sub-configs (Phase 1)
    ConnectionConfig,
    CachingConfig,
    DataValidationConfig,
    FeedManagementConfig,
    DataPerformanceConfig,

    # Domain configs
    DataConfig,
    RiskConfig,
    ProcessingConfig,
    IndicatorConfig,
    FeatureConfig,
    SignalConfig,
    RegimeConfig,
    AnalyticsConfig,
    ExecutionConfig,
    PortfolioConfig,

    # Risk utility configs (Phase 5 - Risk Brick Enhancement)
    ExposureConfig,
    VarConfig,
    StressTestConfig,
    LimitConfig,
    CorrelationConfig,

    # Analytics brick configs (Phase 5 - Analytics Enhancement)
    PerformanceAnalyticsConfig,
    MetricsCalculatorConfig,
    AttributionAnalyticsConfig,
    BenchmarkAnalyticsConfig,
    ReportGenerationConfig,

    # Broker brick configs (Phase 6 - Broker Enhancement)
    BrokerConnectionConfig,
    BrokerSessionConfig,
    BrokerSystemConfig,  # Renamed from BrokerConfig to avoid collision with broker_config.py

    # Backward compatibility
    LegacyDataConfig,
    LegacyRiskConfig,
    LegacyProcessingConfig,

    # Utilities
    create_default_config_set,
    validate_config_compatibility
)

# Strategy configurations (NEW - Phase 4)
from .strategies import (
    StrategyType,
    BaseStrategyConfig,
    StrategyConfig,  # Backward compatibility alias
    MomentumConfig,
    MeanReversionConfig,
    StatisticalArbitrageConfig,
    FactorConfig,
    MultiAssetConfig,
    TrendFollowingConfig,
    BreakoutConfig,
    PairsConfig,
    VolatilityConfig,
    ArbitrageConfig,
    create_strategy_config,
    get_all_strategy_configs
)

__all__ = [
    # Unified config
    'UnifiedConfig', 'ConfigFormat', 'ConfigSource',
    'get_config', 'init_config',
    'config_get', 'config_set', 'config_section',

    # System
    'SystemConfig', 'BacktestConfig', 'BacktestMode',

    # Broker
    'BrokerConfig', 'AlpacaConfig', 'InteractiveBrokersConfig',
    'BrokerConfigLoader', 'load_broker_config',
    'TradingMode', 'BrokerType', 'BrokerRiskLimits',

    # Sub-configs (reusable)
    'PositionLimits', 'RiskLimits', 'TimingConfig', 'PerformanceConfig',

    # Data brick sub-configs (Phase 1)
    'ConnectionConfig', 'CachingConfig', 'DataValidationConfig',
    'FeedManagementConfig', 'DataPerformanceConfig',

    # Component configs (consolidated)
    'DataConfig', 'RiskConfig', 'ProcessingConfig',
    'IndicatorConfig', 'FeatureConfig', 'SignalConfig',
    'RegimeConfig', 'AnalyticsConfig', 'ExecutionConfig', 'PortfolioConfig',

    # Risk utility configs (Phase 5 - Risk Brick Enhancement)
    'ExposureConfig', 'VarConfig', 'StressTestConfig', 'LimitConfig', 'CorrelationConfig',

    # Analytics brick configs (Phase 5 - Analytics Enhancement)
    'PerformanceAnalyticsConfig', 'MetricsCalculatorConfig', 'AttributionAnalyticsConfig',
    'BenchmarkAnalyticsConfig', 'ReportGenerationConfig',

    # Broker brick configs (Phase 6 - Broker Enhancement)
    'BrokerConnectionConfig', 'BrokerSessionConfig', 'BrokerSystemConfig',

    # Backward compatibility
    'LegacyDataConfig', 'LegacyRiskConfig', 'LegacyProcessingConfig',

    # Strategies
    'StrategyType', 'BaseStrategyConfig', 'StrategyConfig',
    'MomentumConfig', 'MeanReversionConfig', 'StatisticalArbitrageConfig',
    'FactorConfig', 'MultiAssetConfig', 'TrendFollowingConfig',
    'BreakoutConfig', 'PairsConfig', 'VolatilityConfig', 'ArbitrageConfig',
    'create_strategy_config', 'get_all_strategy_configs',

    # Utilities
    'create_default_config_set', 'validate_config_compatibility'
]

