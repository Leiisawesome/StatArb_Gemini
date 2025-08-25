"""
Unified Configuration Manager
============================

Centralized configuration management system that provides single source
of truth for all system configuration parameters.

Author: Professional Trading System Architecture
Version: 1.0.0
"""

from typing import Dict, Any, Optional, Union, List
import yaml
import json
import os
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from datetime import datetime

from ..interfaces import ConfigurationInterface, ConfigurationError, INTERFACE_VERSION


@dataclass
class StrategyConfig:
    """Strategy configuration data class."""
    strategy_name: str
    parameters: Dict[str, Any]
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RiskConfig:
    """Risk management configuration data class."""
    max_position_size: float = 0.1
    max_portfolio_allocation: float = 0.2
    stop_loss_percentage: float = 0.05
    take_profit_percentage: float = 0.15
    max_daily_loss: float = 0.02
    position_sizing_method: str = "fixed"
    risk_budget_per_trade: float = 0.01


@dataclass
class ExecutionConfig:
    """Execution configuration data class."""
    commission_per_share: float = 0.001
    slippage_bps: float = 2.0
    market_impact_factor: float = 0.1
    execution_delay_ms: float = 100.0
    order_timeout_seconds: float = 30.0
    fill_probability: float = 0.95


@dataclass
class SystemConfig:
    """System-wide configuration data class."""
    log_level: str = "INFO"
    max_memory_usage_mb: int = 1024
    enable_performance_tracking: bool = True
    enable_detailed_logging: bool = False
    data_cache_size: int = 10000


class UnifiedConfigurationManager(ConfigurationInterface):
    """
    Professional-grade configuration management system.
    
    This manager provides centralized configuration for all system components
    with validation, caching, and hot-reload capabilities.
    
    Features:
    - Single source of truth for all configuration
    - Type-safe configuration with validation
    - Environment-specific configuration overrides
    - Configuration change notifications
    - Performance optimized with caching
    """
    
    def __init__(
        self,
        config_file_path: Optional[str] = None,
        environment: str = "development",
        enable_hot_reload: bool = False
    ):
        """
        Initialize configuration manager.
        
        Args:
            config_file_path: Path to configuration file (YAML or JSON)
            environment: Environment name (development, staging, production)
            enable_hot_reload: Enable hot reloading of configuration
        """
        self.logger = logging.getLogger(__name__)
        self.environment = environment
        self.enable_hot_reload = enable_hot_reload
        
        # Configuration storage
        self._config_cache: Dict[str, Any] = {}
        self._config_file_path = config_file_path
        self._last_config_load_time = None
        self._config_change_callbacks: List[callable] = []
        
        # Default configurations
        self._default_configs = self._initialize_default_configs()
        
        # Load configuration
        self._load_configuration()
        
        self.logger.info(f"UnifiedConfigurationManager initialized for environment: {environment}")
    
    def _initialize_default_configs(self) -> Dict[str, Any]:
        """Initialize default configuration values."""
        return {
            'risk': asdict(RiskConfig()),
            'execution': asdict(ExecutionConfig()),
            'system': asdict(SystemConfig()),
            'strategies': {
                'momentum': {
                    'lookback_period': 20,
                    'threshold': 0.01,
                    'confidence_threshold': 0.6,
                    'position_size': 0.05,
                    'entry_filters': {
                        'min_volume': 1000000,
                        'min_price': 5.0,
                        'max_volatility': 0.3
                    },
                    'exit_rules': {
                        'profit_target': 0.15,
                        'stop_loss': 0.05,
                        'max_holding_days': 30
                    }
                },
                'mean_reversion': {
                    'lookback_period': 30,
                    'threshold': 2.0,  # Z-score threshold for mean reversion
                    'zscore_threshold': 2.0,
                    'confidence_threshold': 0.7,
                    'position_size': 0.03,
                    'mean_calculation_method': 'sma'
                }
            }
        }
    
    def _load_configuration(self) -> None:
        """Load configuration from file and merge with defaults."""
        try:
            # Start with defaults
            self._config_cache = self._default_configs.copy()
            
            # Load from file if provided
            if self._config_file_path and os.path.exists(self._config_file_path):
                file_config = self._load_config_file(self._config_file_path)
                self._merge_configurations(self._config_cache, file_config)
                self._last_config_load_time = datetime.now()
                self.logger.info(f"Configuration loaded from {self._config_file_path}")
            
            # Apply environment-specific overrides
            self._apply_environment_overrides()
            
            # Validate configuration
            self._validate_all_configuration()
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration loading failed: {e}")
    
    def _load_config_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        file_path = Path(file_path)
        
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif file_path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    raise ConfigurationError(f"Unsupported config file format: {file_path.suffix}")
                    
        except Exception as e:
            raise ConfigurationError(f"Failed to load config file {file_path}: {e}")
    
    def _merge_configurations(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> None:
        """Recursively merge configuration dictionaries."""
        for key, value in override_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self._merge_configurations(base_config[key], value)
            else:
                base_config[key] = value
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment-specific configuration overrides."""
        env_overrides = {
            'production': {
                'system': {
                    'log_level': 'WARNING',
                    'enable_detailed_logging': False
                },
                'execution': {
                    'commission_per_share': 0.005,  # Higher commission in production
                    'slippage_bps': 3.0
                }
            },
            'development': {
                'system': {
                    'log_level': 'DEBUG',
                    'enable_detailed_logging': True
                },
                'execution': {
                    'commission_per_share': 0.001,  # Lower commission for testing
                    'slippage_bps': 1.0
                }
            }
        }
        
        if self.environment in env_overrides:
            self._merge_configurations(self._config_cache, env_overrides[self.environment])
            self.logger.info(f"Applied {self.environment} environment overrides")
    
    def _validate_all_configuration(self) -> None:
        """Validate all configuration sections."""
        try:
            # Validate risk configuration
            risk_config = RiskConfig(**self._config_cache.get('risk', {}))
            self._validate_risk_config(risk_config)
            
            # Validate execution configuration
            execution_config = ExecutionConfig(**self._config_cache.get('execution', {}))
            self._validate_execution_config(execution_config)
            
            # Validate system configuration
            system_config = SystemConfig(**self._config_cache.get('system', {}))
            self._validate_system_config(system_config)
            
            # Validate strategy configurations
            for strategy_name, strategy_config in self._config_cache.get('strategies', {}).items():
                self._validate_strategy_config(strategy_name, strategy_config)
            
            self.logger.info("All configuration validation passed")
            
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
    
    def _validate_risk_config(self, risk_config: RiskConfig) -> None:
        """Validate risk management configuration."""
        if not 0.0 < risk_config.max_position_size <= 1.0:
            raise ConfigurationError("max_position_size must be between 0.0 and 1.0")
        
        if not 0.0 < risk_config.max_portfolio_allocation <= 1.0:
            raise ConfigurationError("max_portfolio_allocation must be between 0.0 and 1.0")
        
        if risk_config.stop_loss_percentage <= 0.0:
            raise ConfigurationError("stop_loss_percentage must be positive")
        
        if risk_config.risk_budget_per_trade <= 0.0:
            raise ConfigurationError("risk_budget_per_trade must be positive")
    
    def _validate_execution_config(self, execution_config: ExecutionConfig) -> None:
        """Validate execution configuration."""
        if execution_config.commission_per_share < 0.0:
            raise ConfigurationError("commission_per_share must be non-negative")
        
        if execution_config.slippage_bps < 0.0:
            raise ConfigurationError("slippage_bps must be non-negative")
        
        if not 0.0 < execution_config.fill_probability <= 1.0:
            raise ConfigurationError("fill_probability must be between 0.0 and 1.0")
    
    def _validate_system_config(self, system_config: SystemConfig) -> None:
        """Validate system configuration."""
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if system_config.log_level not in valid_log_levels:
            raise ConfigurationError(f"log_level must be one of {valid_log_levels}")
        
        if system_config.max_memory_usage_mb <= 0:
            raise ConfigurationError("max_memory_usage_mb must be positive")
    
    def _validate_strategy_config(self, strategy_name: str, strategy_config: Dict[str, Any]) -> None:
        """Validate strategy-specific configuration."""
        required_fields = ['lookback_period', 'threshold', 'confidence_threshold', 'position_size']
        
        for field in required_fields:
            if field not in strategy_config:
                raise ConfigurationError(f"Strategy {strategy_name} missing required field: {field}")
        
        # Validate numerical ranges
        if strategy_config['lookback_period'] <= 0:
            raise ConfigurationError(f"Strategy {strategy_name}: lookback_period must be positive")
        
        if not 0.0 < strategy_config['confidence_threshold'] <= 1.0:
            raise ConfigurationError(f"Strategy {strategy_name}: confidence_threshold must be between 0.0 and 1.0")
        
        if not 0.0 < strategy_config['position_size'] <= 1.0:
            raise ConfigurationError(f"Strategy {strategy_name}: position_size must be between 0.0 and 1.0")
    
    # Interface Implementation
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for a specific strategy."""
        strategies_config = self._config_cache.get('strategies', {})
        
        if strategy_name not in strategies_config:
            self.logger.warning(f"Strategy {strategy_name} not found in configuration, using default")
            return self._default_configs['strategies'].get('momentum', {})
        
        return strategies_config[strategy_name].copy()
    
    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration."""
        return self._config_cache.get('risk', {}).copy()
    
    def get_execution_config(self) -> Dict[str, Any]:
        """Get execution engine configuration."""
        return self._config_cache.get('execution', {}).copy()
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration."""
        return self._config_cache.get('system', {}).copy()
    
    def validate_configuration(self) -> bool:
        """Validate all configuration parameters."""
        try:
            self._validate_all_configuration()
            return True
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
    
    # Additional Configuration Management Methods
    
    def get_all_configuration(self) -> Dict[str, Any]:
        """Get complete configuration."""
        return self._config_cache.copy()
    
    def update_strategy_config(self, strategy_name: str, updates: Dict[str, Any]) -> None:
        """Update strategy configuration dynamically."""
        if 'strategies' not in self._config_cache:
            self._config_cache['strategies'] = {}
        
        if strategy_name not in self._config_cache['strategies']:
            self._config_cache['strategies'][strategy_name] = {}
        
        # Merge updates
        self._merge_configurations(self._config_cache['strategies'][strategy_name], updates)
        
        # Validate updated configuration
        self._validate_strategy_config(strategy_name, self._config_cache['strategies'][strategy_name])
        
        # Notify callbacks
        self._notify_config_change('strategy', strategy_name, updates)
        
        self.logger.info(f"Updated configuration for strategy {strategy_name}")
    
    def reload_configuration(self) -> None:
        """Reload configuration from file."""
        if self._config_file_path:
            self._load_configuration()
            self._notify_config_change('system', 'reload', {})
            self.logger.info("Configuration reloaded")
    
    def register_change_callback(self, callback: callable) -> None:
        """Register callback for configuration changes."""
        self._config_change_callbacks.append(callback)
    
    def _notify_config_change(self, section: str, key: str, changes: Dict[str, Any]) -> None:
        """Notify registered callbacks of configuration changes."""
        for callback in self._config_change_callbacks:
            try:
                callback(section, key, changes)
            except Exception as e:
                self.logger.error(f"Configuration change callback failed: {e}")
    
    def export_configuration(self, output_path: str, format: str = 'yaml') -> None:
        """Export current configuration to file."""
        try:
            with open(output_path, 'w') as f:
                if format.lower() == 'yaml':
                    yaml.dump(self._config_cache, f, default_flow_style=False, indent=2)
                elif format.lower() == 'json':
                    json.dump(self._config_cache, f, indent=2)
                else:
                    raise ValueError(f"Unsupported format: {format}")
            
            self.logger.info(f"Configuration exported to {output_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to export configuration: {e}")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration."""
        return {
            'environment': self.environment,
            'config_file_path': self._config_file_path,
            'last_load_time': self._last_config_load_time,
            'strategies_count': len(self._config_cache.get('strategies', {})),
            'hot_reload_enabled': self.enable_hot_reload,
            'interface_version': INTERFACE_VERSION,
            'total_config_sections': len(self._config_cache)
        }
