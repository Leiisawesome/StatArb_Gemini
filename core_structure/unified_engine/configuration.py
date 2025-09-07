#!/usr/bin/env python3
"""
Unified Engine Configuration - Backward Compatibility Layer
==========================================================

This module provides backward compatibility for the legacy unified engine configuration.
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
    UnifiedConfig,
    UnifiedConfigManager,
    Environment,
    TradingMode,
    ConfigurationError,
    ValidationError,
    get_config,
    load_config,
    save_config,
)

# Legacy aliases
Config = UnifiedConfig
ConfigManager = UnifiedConfigManager
UnifiedConfigurationManager = UnifiedConfigManager

# Legacy configuration classes for compatibility
class UnifiedTradingConfig:
    """Legacy unified trading config - redirects to unified system"""
    def __init__(self):
        config = get_config()
        if config.trading:
            self.__dict__.update(config.trading.to_dict())

class UnifiedSystemConfig:
    """Legacy unified system config - redirects to unified system"""
    def __init__(self):
        config = get_config()
        if config.system:
            self.__dict__.update(config.system.to_dict())

class UnifiedDatabaseConfig:
    """Legacy unified database config - redirects to unified system"""
    def __init__(self):
        config = get_config()
        if config.database:
            self.__dict__.update(config.database.to_dict())

class UnifiedRiskConfig:
    """Legacy unified risk config - redirects to unified system"""
    def __init__(self):
        config = get_config()
        if config.risk:
            self.__dict__.update(config.risk.to_dict())

class UnifiedExecutionConfig:
    """Legacy unified execution config - redirects to unified system"""
    def __init__(self):
        config = get_config()
        if config.trading and config.trading.execution:
            self.__dict__.update(config.trading.execution.to_dict())

class UnifiedStrategyConfig:
    """Legacy unified strategy config - redirects to unified system"""
    def __init__(self, strategy_id: str = ""):
        self.strategy_id = strategy_id
        config = get_config()
        if strategy_id and strategy_id in config.strategies:
            self.__dict__.update(config.strategies[strategy_id].to_dict())

__all__ = [
    "UnifiedConfig",
    "UnifiedConfigManager",
    "Environment",
    "TradingMode",
    "ConfigurationError",
    "ValidationError",
    "get_config",
    "load_config",
    "save_config",
    "Config",
    "ConfigManager",
    "UnifiedConfigurationManager",
    "UnifiedTradingConfig",
    "UnifiedSystemConfig",
    "UnifiedDatabaseConfig",
    "UnifiedRiskConfig",
    "UnifiedExecutionConfig",
    "UnifiedStrategyConfig",
]
