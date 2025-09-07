#!/usr/bin/env python3
"""
Paper Trading Configuration - Backward Compatibility Layer
=========================================================

This module provides backward compatibility for the legacy paper trading configuration system.
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

# Legacy aliases for paper trading
PaperTradingConfig = UnifiedConfig
PaperTradingConfigManager = UnifiedConfigManager

# Create paper trading specific factory method
def create_paper_trading_config():
    """Create configuration for paper trading"""
    return ConfigFactory.create_paper_trading_config()

__all__ = [
    "UnifiedConfig",
    "UnifiedConfigManager",
    "ConfigFactory",
    "Environment",
    "TradingMode", 
    "get_config",
    "load_config",
    "PaperTradingConfig",
    "PaperTradingConfigManager",
    "create_paper_trading_config",
]
