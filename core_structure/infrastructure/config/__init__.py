#!/usr/bin/env python3
"""
Infrastructure Configuration - Backward Compatibility Layer
==========================================================

This module provides backward compatibility for the legacy infrastructure configuration system.
All configuration functionality has been consolidated into the unified configuration system.

MIGRATION NOTICE:
The configuration system has been unified and moved to:
core_structure/configuration/

Legacy imports are maintained for backward compatibility.

Author: Professional Trading System Architecture
Version: 3.0.0 (Compatibility Layer)
"""

# Backward compatibility imports from unified configuration system
from core_structure.configuration import (
    # Core Configuration Classes
    UnifiedConfig,
    ConfigurationError,
    ValidationError,
    Environment,
    TradingMode,
    LogLevel,
    BaseConfig,
    ConfigValidator,
    
    # Domain Configurations
    TradingConfig,
    RiskConfig,
    SystemConfig,
    DatabaseConfig,
    LoggingConfig,
    MonitoringConfig,
    AIConfig,
    MarketDataConfig,
    StrategyConfig,
    
    # Configuration Management
    UnifiedConfigManager,
    ConfigFactory,
    ConfigBuilder,
    
    # Convenience Functions
    get_config,
    load_config,
    save_config,
    validate_config,
    get_environment,
    set_environment,
    is_production,
    is_development,
    get_api_key,
    get_database_url,
    get_secret,
)

# Legacy aliases for smooth migration
Config = UnifiedConfig
ConfigManager = UnifiedConfigManager
InfrastructureConfig = SystemConfig
BusinessConfig = TradingConfig

# Legacy function aliases
get_database_config = get_database_url
get_feeds_config = lambda: get_config().market_data if get_config().market_data else {}
load_env_file = lambda: None  # Environment loading is now automatic

# Backward compatibility for specific legacy imports
CoreConfigFactory = ConfigFactory
SecureConfigManager = UnifiedConfigManager
InfrastructureConfigManager = UnifiedConfigManager
InfrastructureConfigFactory = ConfigFactory

# Legacy configuration classes for compatibility
class ClickHouseConfig:
    """Legacy ClickHouse config - redirects to unified system"""
    def __init__(self):
        config = get_config()
        if config.database and config.database.clickhouse:
            self.__dict__.update(config.database.clickhouse.to_dict())

class RedisConfig:
    """Legacy Redis config - redirects to unified system"""
    def __init__(self):
        config = get_config()
        if config.database and config.database.redis:
            self.__dict__.update(config.database.redis.to_dict())

class PostgreSQLConfig:
    """Legacy PostgreSQL config - placeholder"""
    def __init__(self):
        pass

class MessageQueueConfig:
    """Legacy message queue config - placeholder"""
    def __init__(self):
        pass

# Legacy risk configuration aliases
PositionRiskConfig = lambda: get_config().risk.position if get_config().risk else None
PortfolioRiskConfig = lambda: get_config().risk.portfolio if get_config().risk else None
MarketRiskConfig = lambda: get_config().risk.market if get_config().risk else None

# Legacy business configuration aliases
MarketConfig = lambda: get_config().market_data if get_config().market_data else None
ExecutionConfig = lambda: get_config().trading.execution if get_config().trading else None
PortfolioConfig = lambda: get_config().trading.portfolio if get_config().trading else None

# Legacy AI configuration aliases
ModelConfig = lambda: get_config().ai.models if get_config().ai else {}
LLMConfig = lambda: get_config().ai.llm if get_config().ai else None
AIAgentConfig = lambda: get_config().ai if get_config().ai else None

__all__ = [
    # Core Configuration Framework
    "UnifiedConfig",
    "ConfigurationError",
    "ValidationError", 
    "Environment",
    "TradingMode",
    "LogLevel",
    "BaseConfig",
    "ConfigValidator",
    
    # Domain Configurations
    "TradingConfig",
    "RiskConfig",
    "SystemConfig", 
    "DatabaseConfig",
    "LoggingConfig",
    "MonitoringConfig",
    "AIConfig",
    "MarketDataConfig",
    "StrategyConfig",
    
    # Configuration Management
    "UnifiedConfigManager",
    "ConfigFactory",
    "ConfigBuilder",
    
    # Convenience Functions
    "get_config",
    "load_config",
    "save_config", 
    "validate_config",
    "get_environment",
    "set_environment",
    "is_production",
    "is_development",
    "get_api_key",
    "get_database_url",
    "get_secret",
    
    # Legacy Compatibility
    "Config",
    "ConfigManager",
    "InfrastructureConfig",
    "BusinessConfig",
    "CoreConfigFactory",
    "SecureConfigManager",
    "InfrastructureConfigManager",
    "InfrastructureConfigFactory",
    "ClickHouseConfig",
    "RedisConfig",
    "PostgreSQLConfig",
    "MessageQueueConfig",
    "PositionRiskConfig",
    "PortfolioRiskConfig",
    "MarketRiskConfig",
    "MarketConfig",
    "ExecutionConfig",
    "PortfolioConfig",
    "ModelConfig",
    "LLMConfig",
    "AIAgentConfig",
    "get_database_config",
    "get_feeds_config",
    "load_env_file",
]
