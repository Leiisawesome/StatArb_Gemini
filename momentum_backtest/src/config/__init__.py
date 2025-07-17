"""
Configuration management for production momentum trading system
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Production-grade configuration management
    
    Features:
    - Environment-based configuration loading
    - Configuration validation
    - Default fallbacks
    - Secure credential handling
    """
    
    def __init__(self, config_path: Optional[str] = None, environment: str = "development"):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to configuration file
            environment: Environment name (development, testing, production)
        """
        self.environment = environment
        self.config_path = config_path
        self._config = {}
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from multiple sources"""
        # Start with default configuration
        self._config = self._get_default_config()
        
        # Load from file if provided
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                self._merge_config(file_config)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_path}: {e}")
        
        # Apply environment-specific overrides
        self._apply_environment_config()
        
        # Load from environment variables
        self._load_from_environment()
        
        # Validate configuration
        self._validate_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "data": {
                "clickhouse": {
                    "host": "localhost",
                    "port": 9000,
                    "database": "statarb",
                    "username": "default",
                    "password": "",
                    "secure": False,
                    "settings": {
                        "max_memory_usage": "4000000000",
                        "max_execution_time": 300
                    }
                },
                "training_start": "2023-01-01",
                "training_end": "2023-12-31",
                "testing_start": "2024-01-01",
                "testing_end": "2024-03-31",
                "min_symbols": 2,
                "max_symbols": 100
            },
            "strategy": {
                "name": "momentum",
                "momentum_window": 60,
                "min_periods": 30,
                "volatility_window": 20,
                "volume_threshold": 0.5,
                "top_n_long": 1,
                "top_n_short": 1,
                "risk_adjustment": True,
                "rebalance_frequency": "monthly"
            },
            "backtesting": {
                "initial_capital": 100000.0,
                "commission_rate": 0.001,
                "market_impact": 0.0005,
                "slippage": 0.0001,
                "position_limit": 0.45,
                "cash_reserve": 0.10,
                "max_leverage": 2.0
            },
            "risk_management": {
                "max_position_size": 0.45,
                "max_portfolio_leverage": 2.0,
                "max_drawdown_threshold": 0.15,
                "stop_loss_threshold": 0.05,
                "cash_reserve_ratio": 0.10,
                "correlation_limit": 0.8,
                "concentration_limit": 0.30
            },
            "performance": {
                "benchmark_symbol": "SPY",
                "risk_free_rate": 0.02,
                "confidence_level": 0.95,
                "reporting_frequency": "daily"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file_path": "logs/momentum_backtest.log",
                "max_file_size": "10MB",
                "backup_count": 5
            },
            "output": {
                "results_directory": "results",
                "save_trades": True,
                "save_positions": True,
                "save_performance": True,
                "export_format": "csv"
            }
        }
    
    def _apply_environment_config(self):
        """Apply environment-specific configuration overrides"""
        env_configs = {
            "development": {
                "logging": {"level": "DEBUG"},
                "data": {"max_symbols": 10},
                "backtesting": {"initial_capital": 10000.0}
            },
            "testing": {
                "logging": {"level": "DEBUG"},
                "data": {
                    "training_start": "2023-01-01",
                    "training_end": "2023-06-30",
                    "testing_start": "2023-07-01",
                    "testing_end": "2023-12-31",
                    "max_symbols": 20
                },
                "backtesting": {"initial_capital": 50000.0}
            },
            "production": {
                "logging": {"level": "WARNING"},
                "backtesting": {"initial_capital": 1000000.0},
                "risk_management": {
                    "max_drawdown_threshold": 0.10,
                    "stop_loss_threshold": 0.03
                }
            }
        }
        
        if self.environment in env_configs:
            self._merge_config(env_configs[self.environment])
            logger.info(f"Applied {self.environment} environment configuration")
    
    def _load_from_environment(self):
        """Load sensitive configuration from environment variables"""
        env_mappings = {
            "CLICKHOUSE_HOST": ("data", "clickhouse", "host"),
            "CLICKHOUSE_PORT": ("data", "clickhouse", "port"),
            "CLICKHOUSE_DATABASE": ("data", "clickhouse", "database"),
            "CLICKHOUSE_USERNAME": ("data", "clickhouse", "username"),
            "CLICKHOUSE_PASSWORD": ("data", "clickhouse", "password"),
            "INITIAL_CAPITAL": ("backtesting", "initial_capital"),
            "LOG_LEVEL": ("logging", "level")
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_value(config_path, value)
        
        # Convert numeric environment variables
        numeric_vars = [
            ("CLICKHOUSE_PORT", ("data", "clickhouse", "port"), int),
            ("INITIAL_CAPITAL", ("backtesting", "initial_capital"), float)
        ]
        
        for env_var, config_path, converter in numeric_vars:
            value = os.getenv(env_var)
            if value:
                try:
                    converted_value = converter(value)
                    self._set_nested_value(config_path, converted_value)
                except ValueError:
                    logger.warning(f"Invalid numeric value for {env_var}: {value}")
    
    def _merge_config(self, override_config: Dict[str, Any]):
        """Recursively merge configuration dictionaries"""
        def merge_dict(base: dict, override: dict):
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        merge_dict(self._config, override_config)
    
    def _set_nested_value(self, path: tuple, value: Any):
        """Set nested configuration value"""
        current = self._config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _validate_config(self):
        """Validate configuration values"""
        validations = [
            self._validate_data_config,
            self._validate_strategy_config,
            self._validate_risk_config,
            self._validate_backtesting_config
        ]
        
        for validation in validations:
            try:
                validation()
            except Exception as e:
                logger.error(f"Configuration validation failed: {e}")
                raise
    
    def _validate_data_config(self):
        """Validate data configuration"""
        data_config = self._config["data"]
        
        # Validate date ranges
        try:
            train_start = datetime.strptime(data_config["training_start"], "%Y-%m-%d")
            train_end = datetime.strptime(data_config["training_end"], "%Y-%m-%d")
            test_start = datetime.strptime(data_config["testing_start"], "%Y-%m-%d")
            test_end = datetime.strptime(data_config["testing_end"], "%Y-%m-%d")
            
            if train_start >= train_end:
                raise ValueError("Training start date must be before training end date")
            if test_start >= test_end:
                raise ValueError("Testing start date must be before testing end date")
            if train_end > test_start:
                logger.warning("Training period overlaps with testing period")
                
        except ValueError as e:
            raise ValueError(f"Invalid date format in configuration: {e}")
        
        # Validate symbol limits
        if data_config["min_symbols"] < 1:
            raise ValueError("min_symbols must be at least 1")
        if data_config["max_symbols"] < data_config["min_symbols"]:
            raise ValueError("max_symbols must be >= min_symbols")
    
    def _validate_strategy_config(self):
        """Validate strategy configuration"""
        strategy_config = self._config["strategy"]
        
        if strategy_config["momentum_window"] < 1:
            raise ValueError("momentum_window must be positive")
        if strategy_config["min_periods"] < 1:
            raise ValueError("min_periods must be positive")
        if strategy_config["top_n_long"] < 0:
            raise ValueError("top_n_long must be non-negative")
        if strategy_config["top_n_short"] < 0:
            raise ValueError("top_n_short must be non-negative")
    
    def _validate_risk_config(self):
        """Validate risk management configuration"""
        risk_config = self._config["risk_management"]
        
        if not 0 < risk_config["max_position_size"] <= 1:
            raise ValueError("max_position_size must be between 0 and 1")
        if risk_config["max_portfolio_leverage"] < 1:
            raise ValueError("max_portfolio_leverage must be >= 1")
        if not 0 < risk_config["cash_reserve_ratio"] < 1:
            raise ValueError("cash_reserve_ratio must be between 0 and 1")
    
    def _validate_backtesting_config(self):
        """Validate backtesting configuration"""
        backtest_config = self._config["backtesting"]
        
        if backtest_config["initial_capital"] <= 0:
            raise ValueError("initial_capital must be positive")
        if backtest_config["commission_rate"] < 0:
            raise ValueError("commission_rate must be non-negative")
        if backtest_config["market_impact"] < 0:
            raise ValueError("market_impact must be non-negative")
    
    def get(self, *keys, default=None):
        """Get configuration value by nested keys"""
        current = self._config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def get_all(self) -> Dict[str, Any]:
        """Get complete configuration"""
        return self._config.copy()
    
    def update(self, config_update: Dict[str, Any]):
        """Update configuration with new values"""
        self._merge_config(config_update)
        self._validate_config()
    
    def save(self, output_path: str):
        """Save current configuration to file"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(self._config, f, indent=2, default=str)
            logger.info(f"Configuration saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

# Predefined configuration presets
PRESET_CONFIGS = {
    "quick_test": {
        "data": {
            "training_start": "2023-01-01",
            "training_end": "2023-03-31",
            "testing_start": "2023-04-01",
            "testing_end": "2023-06-30",
            "max_symbols": 5
        },
        "backtesting": {
            "initial_capital": 10000.0
        },
        "logging": {
            "level": "DEBUG"
        }
    },
    "extended_test": {
        "data": {
            "training_start": "2022-01-01",
            "training_end": "2023-12-31",
            "testing_start": "2024-01-01",
            "testing_end": "2024-06-30"
        }
    },
    "production_ready": {
        "backtesting": {
            "initial_capital": 1000000.0
        },
        "risk_management": {
            "max_drawdown_threshold": 0.10,
            "stop_loss_threshold": 0.03
        },
        "logging": {
            "level": "WARNING"
        }
    }
}

def load_config(config_path: Optional[str] = None, 
                environment: str = "development",
                preset: Optional[str] = None) -> ConfigManager:
    """
    Load configuration with optional preset
    
    Args:
        config_path: Path to configuration file
        environment: Environment name
        preset: Preset configuration name
    
    Returns:
        Configured ConfigManager instance
    """
    config_manager = ConfigManager(config_path, environment)
    
    if preset and preset in PRESET_CONFIGS:
        config_manager.update(PRESET_CONFIGS[preset])
        logger.info(f"Applied preset configuration: {preset}")
    
    return config_manager
