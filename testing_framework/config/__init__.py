#!/usr/bin/env python3
"""
Testing Framework Configuration - Backward Compatibility Layer
=============================================================

This module provides backward compatibility for the legacy testing framework configuration system.
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
    ConfigFactory,
    Environment,
    TradingMode,
    get_config,
    load_config,
)

# Legacy aliases for testing
TestConfig = UnifiedConfig
TestConfigManager = UnifiedConfigManager
ConfigManager = UnifiedConfigManager

# Create testing-specific factory methods
def create_test_config():
    """Create configuration for testing"""
    return ConfigFactory.create_development_config()

def create_backtest_config():
    """Create configuration for backtesting"""
    return ConfigFactory.create_backtest_config()

__all__ = [
    "UnifiedConfig",
    "UnifiedConfigManager",
    "ConfigFactory",
    "Environment", 
    "TradingMode",
    "get_config",
    "load_config",
    "TestConfig",
    "TestConfigManager",
    "ConfigManager",
    "create_test_config",
    "create_backtest_config",
]
