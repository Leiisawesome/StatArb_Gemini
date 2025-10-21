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
from .system_config import SystemConfig

# Broker configuration  
from .broker_config import (
    BrokerConfig,
    AlpacaConfig,
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
    'SystemConfig',
    
    # Broker
    'BrokerConfig', 'AlpacaConfig', 'InteractiveBrokersConfig',
    'BrokerConfigLoader', 'load_broker_config',
    'TradingMode', 'BrokerType', 'BrokerRiskLimits',
    
    # Sub-configs (reusable)
    'PositionLimits', 'RiskLimits', 'TimingConfig', 'PerformanceConfig',
    
    # Component configs (consolidated)
    'DataConfig', 'RiskConfig', 'ProcessingConfig',
    'IndicatorConfig', 'FeatureConfig', 'SignalConfig',
    'RegimeConfig', 'AnalyticsConfig', 'ExecutionConfig', 'PortfolioConfig',
    
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

