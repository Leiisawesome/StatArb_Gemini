"""
Testing Framework Configuration Manager
======================================

Centralized configuration management for all backtesting parameters,
trading periods, universe selection, and test scenarios.

Features:
- YAML-based configuration with validation
- Easy parameter overrides for different test scenarios  
- Automatic date/time handling with timezone support
- Configuration inheritance and merging
- Environment-specific overrides
"""

import os
import yaml
import logging
from datetime import datetime, time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path

@dataclass
class TradingPeriod:
    """Trading period configuration"""
    start_date: str
    end_date: str
    start_time: str = "09:30:00"
    end_time: str = "16:00:00"
    timezone: str = "US/Eastern"
    description: str = ""
    
    def to_datetime_range(self):
        """Convert to datetime objects"""
        from datetime import datetime
        start_dt = datetime.strptime(f"{self.start_date} {self.start_time}", "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(f"{self.end_date} {self.end_time}", "%Y-%m-%d %H:%M:%S")
        return start_dt, end_dt

@dataclass  
class StrategyConfig:
    """Strategy configuration"""
    template: str
    symbols: List[str]
    period: str
    interval: str = "1min"
    capital: float = 100000.0
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

@dataclass
class UniverseConfig:
    """Universe configuration"""
    symbols: List[str]
    categories: Dict[str, List[str]]

@dataclass
class TestRiskConfig:
    """Risk management configuration for backtesting scenarios"""
    max_portfolio_risk: float = 0.02
    max_position_size: float = 0.20
    max_drawdown_limit: float = 0.10
    atr_multiplier: float = 2.0
    trailing_stop_enabled: bool = True
    trailing_stop_pct: float = 0.02

# Backward compatibility alias
RiskConfig = TestRiskConfig

class TestConfigManager:
    """
    Central configuration manager for testing framework
    
    Features:
    - Load and validate YAML configuration
    - Provide easy access to trading periods, universe, strategies
    - Support configuration overrides and environment-specific settings
    - Automatic validation and error handling
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Default config path
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                "test_config.yaml"
            )
        
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            self.logger.info(f"✅ Loaded test configuration from {self.config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load config from {self.config_path}: {e}")
            # Return minimal default config
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return minimal default configuration"""
        return {
            'universe': {
                'symbols': ['TSLA'],
                'categories': {'default': ['TSLA']}
            },
            'trading_periods': {
                'single_day': {
                    'start_date': '2024-12-20',
                    'end_date': '2024-12-20',
                    'start_time': '09:30:00',
                    'end_time': '16:00:00',
                    'timezone': 'US/Eastern'
                }
            },
            'data': {
                'default_interval': '1min',
                'validation': {'enable_validation': True}
            },
            'strategies': {},
            'risk_management': {
                'global': {
                    'max_portfolio_risk': 0.02,
                    'max_position_size': 0.20
                }
            }
        }
    
    def _validate_config(self):
        """Validate configuration structure"""
        required_sections = ['universe', 'trading_periods', 'data', 'strategies']
        
        for section in required_sections:
            if section not in self.config:
                self.logger.warning(f"⚠️  Missing config section: {section}")
    
    # =============================================================================
    # UNIVERSE METHODS
    # =============================================================================
    
    def get_universe(self) -> UniverseConfig:
        """Get universe configuration"""
        universe_data = self.config.get('universe', {})
        return UniverseConfig(
            symbols=universe_data.get('symbols', ['TSLA']),
            categories=universe_data.get('categories', {})
        )
    
    def get_symbols(self, category: Optional[str] = None) -> List[str]:
        """Get symbols, optionally filtered by category"""
        universe = self.get_universe()
        
        if category is None:
            return universe.symbols
        
        if category in universe.categories:
            return universe.categories[category]
        
        self.logger.warning(f"⚠️  Category '{category}' not found, returning default symbols")
        return universe.symbols
    
    # =============================================================================
    # TRADING PERIOD METHODS  
    # =============================================================================
    
    def get_trading_period(self, period_name: str = "single_day") -> TradingPeriod:
        """Get trading period configuration"""
        periods = self.config.get('trading_periods', {})
        
        if period_name not in periods:
            self.logger.warning(f"⚠️  Period '{period_name}' not found, using 'single_day'")
            period_name = "single_day"
        
        period_data = periods.get(period_name, periods.get('single_day', {}))
        
        return TradingPeriod(
            start_date=period_data.get('start_date', '2024-12-20'),
            end_date=period_data.get('end_date', '2024-12-20'),
            start_time=period_data.get('start_time', '09:30:00'),
            end_time=period_data.get('end_time', '16:00:00'),
            timezone=period_data.get('timezone', 'US/Eastern'),
            description=period_data.get('description', '')
        )
    
    def list_available_periods(self) -> List[str]:
        """List all available trading periods"""
        return list(self.config.get('trading_periods', {}).keys())
    
    # =============================================================================
    # STRATEGY METHODS
    # =============================================================================
    
    def get_strategy_config(self, strategy_name: str) -> StrategyConfig:
        """Get strategy configuration"""
        strategies = self.config.get('strategies', {})
        
        if strategy_name not in strategies:
            raise ValueError(f"Strategy '{strategy_name}' not found in config")
        
        strategy_data = strategies[strategy_name]
        
        return StrategyConfig(
            template=strategy_data.get('template', 'default'),
            symbols=strategy_data.get('symbols', ['TSLA']),
            period=strategy_data.get('period', 'single_day'),
            interval=strategy_data.get('interval', '1min'),
            capital=strategy_data.get('capital', 100000.0),
            parameters=strategy_data.get('parameters', {})
        )
    
    def list_available_strategies(self) -> List[str]:
        """List all available strategies"""
        return list(self.config.get('strategies', {}).keys())
    
    # =============================================================================
    # RISK MANAGEMENT METHODS
    # =============================================================================
    
    def get_risk_config(self) -> TestRiskConfig:
        """Get risk configuration"""
        risk_params = self.config.get('risk', {})
        
        return TestRiskConfig(
            max_portfolio_risk=risk_params.get('max_portfolio_risk', 0.02),
            max_position_size=risk_params.get('max_position_size', 0.20),
            max_drawdown_limit=risk_params.get('max_drawdown_limit', 0.10),
            atr_multiplier=risk_params.get('stop_loss', {}).get('atr_multiplier', 2.0),
            trailing_stop_enabled=risk_params.get('stop_loss', {}).get('trailing_stop_enabled', True),
            trailing_stop_pct=risk_params.get('stop_loss', {}).get('trailing_stop_pct', 0.02)
        )
    
    # =============================================================================
    # DATA METHODS
    # =============================================================================
    
    def get_default_interval(self) -> str:
        """Get default data interval"""
        return self.config.get('data', {}).get('default_interval', '1min')
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get data validation configuration"""
        return self.config.get('data', {}).get('validation', {})
    
    # =============================================================================
    # SCENARIO METHODS
    # =============================================================================
    
    def get_scenario_config(self, scenario_name: str) -> Dict[str, Any]:
        """Get test scenario configuration"""
        scenarios = self.config.get('scenarios', {})
        
        if scenario_name not in scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found in config")
        
        return scenarios[scenario_name]
    
    def list_available_scenarios(self) -> List[str]:
        """List all available scenarios"""
        return list(self.config.get('scenarios', {}).keys())
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def override_config(self, overrides: Dict[str, Any]):
        """Override configuration values"""
        def deep_update(base_dict, update_dict):
            for key, value in update_dict.items():
                if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value
        
        deep_update(self.config, overrides)
        self.logger.info("✅ Configuration overrides applied")
    
    def get_full_config(self) -> Dict[str, Any]:
        """Get complete configuration"""
        return self.config.copy()
    
    def save_config(self, output_path: str):
        """Save current configuration to file"""
        with open(output_path, 'w') as file:
            yaml.dump(self.config, file, default_flow_style=False, indent=2)
        
        self.logger.info(f"✅ Configuration saved to {output_path}")

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def load_test_config(config_path: Optional[str] = None) -> TestConfigManager:
    """Load test configuration (convenience function)"""
    return TestConfigManager(config_path)

def get_quick_test_config() -> Dict[str, Any]:
    """Get configuration for quick testing"""
    return {
        'symbols': ['TSLA'],
        'period': 'single_day',
        'interval': '1min',
        'capital': 100000.0
    }

def get_comprehensive_test_config() -> Dict[str, Any]:
    """Get configuration for comprehensive testing"""
    return {
        'symbols': ['TSLA', 'AAPL', 'MSFT'],
        'period': 'one_week', 
        'interval': '1min',
        'capital': 300000.0
    }

# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example usage
    config_manager = TestConfigManager()
    
    # Get trading period
    period = config_manager.get_trading_period("single_day")
    print(f"Trading Period: {period.start_date} to {period.end_date}")
    
    # Get strategy config
    try:
        strategy = config_manager.get_strategy_config("advanced_momentum")
        print(f"Strategy: {strategy.template} with symbols {strategy.symbols}")
    except ValueError as e:
        print(f"Strategy config error: {e}")
    
    # Get universe
    universe = config_manager.get_universe()
    print(f"Available symbols: {universe.symbols}")
    
    # List available configurations
    print(f"Available periods: {config_manager.list_available_periods()}")
    print(f"Available strategies: {config_manager.list_available_strategies()}")
