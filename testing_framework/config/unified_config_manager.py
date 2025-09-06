"""
Unified Backtest Configuration Manager
====================================

Centralized configuration management system that eliminates hardcoded parameters
and provides a scalable, flexible approach to backtest configuration.

Features:
- Unified configuration schema for all strategy types
- Environment-specific overrides (dev/test/prod)
- Configuration validation and error handling
- Dynamic parameter resolution and inheritance
- Test scenario management
- Configuration-driven backtest factory
"""

import os
import yaml
import logging
from datetime import datetime, time, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

class StrategyType(Enum):
    """Supported strategy types"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    ARBITRAGE = "arbitrage"

class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

@dataclass
class TradingPeriod:
    """Trading period configuration with timezone support"""
    start_date: str
    end_date: str
    start_time: str = "09:30:00"
    end_time: str = "16:00:00"
    timezone: str = "US/Eastern"
    description: str = ""
    
    def to_datetime_range(self) -> Tuple[datetime, datetime]:
        """Convert to timezone-aware datetime objects"""
        import pytz
        tz = pytz.timezone(self.timezone)
        
        start_dt = datetime.strptime(f"{self.start_date} {self.start_time}", "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(f"{self.end_date} {self.end_time}", "%Y-%m-%d %H:%M:%S")
        
        start_dt = tz.localize(start_dt)
        end_dt = tz.localize(end_dt)
        
        return start_dt, end_dt

@dataclass
class UniverseConfig:
    """Trading universe configuration"""
    name: str
    symbols: List[str] = field(default_factory=list)
    symbol_pairs: List[Tuple[str, str]] = field(default_factory=list)
    categories: Dict[str, List[str]] = field(default_factory=dict)
    description: str = ""

@dataclass
class StrategyParameters:
    """Strategy-specific parameters with validation"""
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get parameter with default fallback"""
        return self.parameters.get(key, default)
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update parameters with new values"""
        self.parameters.update(updates)
    
    def validate_required(self, required_keys: List[str]) -> None:
        """Validate that required parameters are present"""
        missing = [key for key in required_keys if key not in self.parameters]
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

@dataclass
class BacktestConfig:
    """Complete backtest configuration"""
    # Strategy identification
    strategy_name: str
    strategy_type: StrategyType
    
    # Trading universe
    symbols: List[str] = field(default_factory=list)
    symbol_pairs: List[Tuple[str, str]] = field(default_factory=list)
    
    # Time configuration
    period: TradingPeriod = None
    interval: str = "5min"
    
    # Capital and risk
    initial_capital: float = 100000.0
    max_position_size: float = 0.20
    risk_limit: float = 0.02
    slippage: float = 0.0005
    
    # Strategy parameters
    parameters: StrategyParameters = field(default_factory=StrategyParameters)
    
    # Metadata
    description: str = ""
    test_name: str = ""
    environment: Environment = Environment.DEVELOPMENT

class UnifiedConfigManager:
    """
    Unified configuration manager for all backtest types
    
    Eliminates hardcoded parameters and provides centralized configuration
    management with validation, inheritance, and environment support.
    """
    
    def __init__(self, config_file: str = "unified_backtest_config.yaml", 
                 environment: Environment = Environment.DEVELOPMENT):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to unified configuration file
            environment: Current environment (dev/test/prod)
        """
        self.logger = logging.getLogger(__name__)
        self.environment = environment
        
        # Load configuration
        config_path = Path(__file__).parent / config_file
        self.config = self._load_config(config_path)
        
        # Apply environment overrides
        self._apply_environment_overrides()
        
        self.logger.info(f"✅ Unified configuration loaded from {config_path}")
        self.logger.info(f"🌍 Environment: {environment.value}")
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load and validate YAML configuration"""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            # Validate required sections
            required_sections = ['global', 'universes', 'periods', 'strategies']
            missing = [section for section in required_sections if section not in config]
            if missing:
                raise ValueError(f"Missing required configuration sections: {missing}")
            
            return config
            
        except FileNotFoundError:
            self.logger.error(f"❌ Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"❌ Invalid YAML configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"❌ Configuration loading failed: {e}")
            raise
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment-specific configuration overrides"""
        env_config = self.config.get('environments', {}).get(self.environment.value, {})
        
        for section, overrides in env_config.items():
            if section in self.config:
                self._deep_update(self.config[section], overrides)
        
        if env_config:
            self.logger.info(f"📝 Applied {self.environment.value} environment overrides")
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """Recursively update nested dictionaries"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    # =============================================================================
    # UNIVERSE MANAGEMENT
    # =============================================================================
    
    def get_universe(self, universe_path: str) -> UniverseConfig:
        """
        Get trading universe configuration
        
        Args:
            universe_path: Dot-notation path (e.g., 'single_assets.tech_stocks')
        
        Returns:
            UniverseConfig with symbols and metadata
        """
        try:
            # Parse universe path
            parts = universe_path.split('.')
            universe_data = self.config['universes']
            
            for part in parts:
                universe_data = universe_data[part]
            
            # Handle different universe types
            if isinstance(universe_data, list):
                if all(isinstance(item, list) and len(item) == 2 for item in universe_data):
                    # Pairs universe
                    return UniverseConfig(
                        name=universe_path,
                        symbol_pairs=[(pair[0], pair[1]) for pair in universe_data],
                        description=f"Pairs universe: {universe_path}"
                    )
                else:
                    # Single asset universe
                    return UniverseConfig(
                        name=universe_path,
                        symbols=universe_data,
                        description=f"Single asset universe: {universe_path}"
                    )
            else:
                raise ValueError(f"Invalid universe format: {universe_path}")
                
        except KeyError:
            self.logger.error(f"❌ Universe not found: {universe_path}")
            raise ValueError(f"Universe '{universe_path}' not found in configuration")
    
    def list_universes(self) -> Dict[str, List[str]]:
        """List all available universes by category"""
        universes = {}
        
        for category, universe_dict in self.config['universes'].items():
            universes[category] = list(universe_dict.keys())
        
        return universes
    
    # =============================================================================
    # PERIOD MANAGEMENT
    # =============================================================================
    
    def get_period(self, period_name: str) -> TradingPeriod:
        """Get trading period configuration"""
        periods = self.config.get('periods', {})
        
        if period_name not in periods:
            available = list(periods.keys())
            raise ValueError(f"Period '{period_name}' not found. Available: {available}")
        
        period_data = periods[period_name]
        
        return TradingPeriod(
            start_date=period_data['start_date'],
            end_date=period_data['end_date'],
            start_time=period_data.get('start_time', '09:30:00'),
            end_time=period_data.get('end_time', '16:00:00'),
            timezone=period_data.get('timezone', self.config['global']['default_timezone']),
            description=period_data.get('description', '')
        )
    
    def list_periods(self) -> List[str]:
        """List all available trading periods"""
        return list(self.config.get('periods', {}).keys())
    
    # =============================================================================
    # STRATEGY CONFIGURATION
    # =============================================================================
    
    def get_strategy_config(self, strategy_path: str, overrides: Dict[str, Any] = None) -> BacktestConfig:
        """
        Get complete strategy configuration with inheritance and overrides
        
        Args:
            strategy_path: Dot-notation path (e.g., 'momentum.momentum_single_tsla')
            overrides: Optional parameter overrides
        
        Returns:
            Complete BacktestConfig ready for backtesting
        """
        try:
            # Parse strategy path
            parts = strategy_path.split('.')
            if len(parts) != 2:
                raise ValueError(f"Invalid strategy path format: {strategy_path}")
            
            strategy_type_name, strategy_name = parts
            strategy_data = self.config['strategies'][strategy_type_name][strategy_name]
            
            # Get strategy type
            strategy_type = StrategyType(strategy_data['type'])
            
            # Get universe configuration
            universe_path = strategy_data.get('universe')
            universe_config = self.get_universe(universe_path) if universe_path else None
            
            # Get period configuration
            period_name = strategy_data.get('period', 'quick_test')
            period_config = self.get_period(period_name)
            
            # Build base configuration
            config = BacktestConfig(
                strategy_name=strategy_name,
                strategy_type=strategy_type,
                period=period_config,
                interval=strategy_data.get('interval', self.config['global']['default_interval']),
                initial_capital=strategy_data.get('capital', self.config['global']['default_capital']),
                max_position_size=strategy_data.get('max_position_size', self.config['global']['default_max_position_size']),
                risk_limit=strategy_data.get('risk_limit', self.config['global']['default_risk_limit']),
                slippage=strategy_data.get('slippage', self.config['global']['default_slippage']),
                environment=self.environment,
                test_name=strategy_data.get('test_name', strategy_name)
            )
            
            # Set symbols based on universe and strategy configuration
            if 'symbols' in strategy_data:
                config.symbols = strategy_data['symbols']
            elif universe_config and universe_config.symbols:
                config.symbols = universe_config.symbols
            
            # Set symbol pairs for pairs trading
            if 'symbol_pairs' in strategy_data:
                config.symbol_pairs = [tuple(pair) for pair in strategy_data['symbol_pairs']]
            elif universe_config and universe_config.symbol_pairs:
                config.symbol_pairs = universe_config.symbol_pairs
            
            # Set strategy parameters
            parameters = strategy_data.get('parameters', {})
            config.parameters = StrategyParameters(parameters)
            
            # Apply overrides
            if overrides:
                self._apply_overrides(config, overrides)
            
            # Validate configuration
            self._validate_config(config)
            
            return config
            
        except KeyError as e:
            self.logger.error(f"❌ Strategy configuration error: {e}")
            raise ValueError(f"Strategy '{strategy_path}' not found or incomplete")
    
    def _apply_overrides(self, config: BacktestConfig, overrides: Dict[str, Any]) -> None:
        """Apply configuration overrides"""
        for key, value in overrides.items():
            if key == 'period' and isinstance(value, str):
                config.period = self.get_period(value)
            elif key == 'parameters' and isinstance(value, dict):
                config.parameters.update(value)
            elif hasattr(config, key):
                setattr(config, key, value)
            else:
                self.logger.warning(f"⚠️  Unknown override parameter: {key}")
    
    def _validate_config(self, config: BacktestConfig) -> None:
        """Validate backtest configuration"""
        # Validate symbols
        if not config.symbols and not config.symbol_pairs:
            raise ValueError("Configuration must specify either symbols or symbol_pairs")
        
        # Validate pairs trading specific requirements
        if config.strategy_type == StrategyType.PAIRS_TRADING:
            if not config.symbol_pairs:
                raise ValueError("Pairs trading strategy requires symbol_pairs")
        
        # Validate capital
        if config.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        
        # Validate period
        if not config.period:
            raise ValueError("Trading period must be specified")
    
    def list_strategies(self) -> Dict[str, List[str]]:
        """List all available strategies by type"""
        strategies = {}
        
        for strategy_type, strategy_dict in self.config['strategies'].items():
            strategies[strategy_type] = list(strategy_dict.keys())
        
        return strategies
    
    # =============================================================================
    # TEST SCENARIO MANAGEMENT
    # =============================================================================
    
    def get_test_scenario(self, scenario_name: str) -> List[BacktestConfig]:
        """
        Get test scenario with multiple strategy configurations
        
        Args:
            scenario_name: Name of test scenario
        
        Returns:
            List of BacktestConfig objects for the scenario
        """
        scenarios = self.config.get('test_scenarios', {})
        
        if scenario_name not in scenarios:
            available = list(scenarios.keys())
            raise ValueError(f"Test scenario '{scenario_name}' not found. Available: {available}")
        
        scenario_configs = []
        
        for test_config in scenarios[scenario_name]:
            strategy_path = test_config['strategy']
            overrides = test_config.get('override', {})
            
            config = self.get_strategy_config(strategy_path, overrides)
            scenario_configs.append(config)
        
        return scenario_configs
    
    def list_test_scenarios(self) -> List[str]:
        """List all available test scenarios"""
        return list(self.config.get('test_scenarios', {}).keys())
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_global_defaults(self) -> Dict[str, Any]:
        """Get global default configuration"""
        return self.config.get('global', {})
    
    def export_config_summary(self) -> Dict[str, Any]:
        """Export configuration summary for debugging"""
        return {
            'environment': self.environment.value,
            'universes': self.list_universes(),
            'periods': self.list_periods(),
            'strategies': self.list_strategies(),
            'test_scenarios': self.list_test_scenarios(),
            'global_defaults': self.get_global_defaults()
        }

# =============================================================================
# CONFIGURATION FACTORY
# =============================================================================

class BacktestConfigFactory:
    """Factory for creating backtest configurations"""
    
    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        """Initialize factory with configuration manager"""
        self.config_manager = UnifiedConfigManager(environment=environment)
        self.logger = logging.getLogger(__name__)
    
    def create_single_strategy_config(self, strategy_path: str, 
                                    overrides: Dict[str, Any] = None) -> BacktestConfig:
        """Create configuration for a single strategy"""
        return self.config_manager.get_strategy_config(strategy_path, overrides)
    
    def create_scenario_configs(self, scenario_name: str) -> List[BacktestConfig]:
        """Create configurations for a test scenario"""
        return self.config_manager.get_test_scenario(scenario_name)
    
    def create_comparison_configs(self, strategy_paths: List[str], 
                                common_overrides: Dict[str, Any] = None) -> List[BacktestConfig]:
        """Create configurations for strategy comparison"""
        configs = []
        
        for strategy_path in strategy_paths:
            config = self.config_manager.get_strategy_config(strategy_path, common_overrides)
            configs.append(config)
        
        return configs
    
    def create_multi_timeframe_configs(self, strategy_path: str, 
                                     intervals: List[str]) -> List[BacktestConfig]:
        """Create configurations for multi-timeframe analysis"""
        configs = []
        
        for interval in intervals:
            overrides = {
                'interval': interval,
                'test_name': f"{strategy_path}_{interval}"
            }
            config = self.config_manager.get_strategy_config(strategy_path, overrides)
            configs.append(config)
        
        return configs

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def load_config(strategy_path: str, environment: str = "development", 
                overrides: Dict[str, Any] = None) -> BacktestConfig:
    """
    Convenience function to load a single strategy configuration
    
    Args:
        strategy_path: Strategy path (e.g., 'momentum.momentum_single_tsla')
        environment: Environment name
        overrides: Optional parameter overrides
    
    Returns:
        BacktestConfig ready for use
    """
    env = Environment(environment)
    factory = BacktestConfigFactory(env)
    return factory.create_single_strategy_config(strategy_path, overrides)

def load_scenario(scenario_name: str, environment: str = "development") -> List[BacktestConfig]:
    """
    Convenience function to load a test scenario
    
    Args:
        scenario_name: Test scenario name
        environment: Environment name
    
    Returns:
        List of BacktestConfig objects
    """
    env = Environment(environment)
    factory = BacktestConfigFactory(env)
    return factory.create_scenario_configs(scenario_name)
