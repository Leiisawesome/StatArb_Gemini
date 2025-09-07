#!/usr/bin/env python3
"""
Paper Trading Configuration Manager - Backward Compatibility Placeholder
=======================================================================

This module provides backward compatibility for paper trading configuration management.
All configuration functionality has been consolidated into the unified configuration system.

MIGRATION NOTICE:
The configuration system has been unified and moved to:
core_structure/configuration/

Author: Professional Trading System Architecture
Version: 3.0.0 (Compatibility Placeholder)
"""

# Backward compatibility imports from unified configuration system
from core_structure.configuration import (
    UnifiedConfigManager,
    ConfigFactory,
    get_config,
)

class PaperTradingConfigManager:
    """Legacy paper trading config manager - redirects to unified system"""
    
    def __init__(self):
        self._unified_manager = UnifiedConfigManager()
    
    def get_config(self):
        """Get paper trading configuration"""
        return ConfigFactory.create_paper_trading_config()
    
    def load_config(self, config_file: str = None):
        """Load configuration from file"""
        if config_file:
            self._unified_manager = UnifiedConfigManager(config_file=config_file)
        return self.get_config()

class LiveStrategyConfig:
    """Legacy live strategy config - placeholder"""
    def __init__(self):
        config = get_config()
        self.strategies = config.strategies

class TradingEnvironment:
    """Legacy trading environment - placeholder"""
    def __init__(self):
        config = get_config()
        self.environment = config.environment

__all__ = ["PaperTradingConfigManager", "LiveStrategyConfig", "TradingEnvironment"]
