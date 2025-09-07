#!/usr/bin/env python3
"""
Testing Framework Configuration Manager - Backward Compatibility Layer
=====================================================================

This module provides backward compatibility for the testing framework configuration manager.
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
    UnifiedConfigManager,
    ConfigFactory,
    get_config,
    Environment,
    TradingMode,
)

class TestConfigManager:
    """Legacy test config manager - redirects to unified system"""
    
    def __init__(self):
        self._unified_manager = UnifiedConfigManager()
    
    def get_config(self):
        """Get test configuration"""
        return ConfigFactory.create_development_config()
    
    def load_config(self, config_file: str = None):
        """Load configuration from file"""
        if config_file:
            self._unified_manager = UnifiedConfigManager(config_file=config_file)
        return self.get_config()
    
    def get_strategy_config(self, strategy_id: str):
        """Get strategy configuration"""
        config = self.get_config()
        return config.get_strategy_config(strategy_id)
    
    def _create_default_trading_config(self, trading_mode):
        """Create default trading configuration"""
        from core_structure.configuration import TradingConfig
        return TradingConfig()
    
    def list_available_strategies(self):
        """List available strategies"""
        config = self.get_config()
        return list(config.strategies.keys())
    
    def get_trading_period(self, period_name: str):
        """Get trading period configuration"""
        from datetime import datetime, timedelta
        # Default trading period for backtesting
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        return TradingPeriod(start_date, end_date)

class TradingPeriod:
    """Legacy trading period - placeholder"""
    def __init__(self, start_date=None, end_date=None):
        self.start_date = start_date
        self.end_date = end_date

class StrategyConfig:
    """Legacy strategy config - redirects to unified system"""
    def __init__(self, **kwargs):
        config = get_config()
        self.__dict__.update(kwargs)

__all__ = ["TestConfigManager", "TradingPeriod", "StrategyConfig"]
