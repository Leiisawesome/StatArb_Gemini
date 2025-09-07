#!/usr/bin/env python3
"""
Unified Configuration Manager - Professional Configuration Management
===================================================================

Enterprise-grade configuration management system providing:
- Single source of truth for all system configuration
- Hot-reload capabilities with change notifications
- Environment-specific configuration management
- Secure credential handling and validation
- Performance-optimized caching and persistence

Consolidates 8+ competing configuration managers into one unified system.

Author: Professional Trading System Architecture
Version: 3.0.0 (Unified Management)
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable, Type, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock, Event
from functools import lru_cache
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    # Watchdog not available - file watching will be disabled
    Observer = None
    FileSystemEventHandler = None
    WATCHDOG_AVAILABLE = False
import threading
import time

from .unified_config import UnifiedConfig, Environment, TradingMode, ConfigurationError, ValidationError
from .config_domains import *

logger = logging.getLogger(__name__)

# ================================================================================
# CONFIGURATION CHANGE EVENTS
# ================================================================================

@dataclass
class ConfigChangeEvent:
    """Configuration change event"""
    timestamp: datetime
    config_path: str
    change_type: str  # 'created', 'modified', 'deleted'
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

class ConfigFileWatcher(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """File system watcher for configuration changes"""
    
    def __init__(self, config_manager: 'UnifiedConfigManager'):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
    
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory and event.src_path.endswith(('.yaml', '.yml', '.json')):
            self.logger.info(f"Configuration file modified: {event.src_path}")
            self.config_manager._handle_file_change(event.src_path, 'modified')
    
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory and event.src_path.endswith(('.yaml', '.yml', '.json')):
            self.logger.info(f"Configuration file created: {event.src_path}")
            self.config_manager._handle_file_change(event.src_path, 'created')
    
    def on_deleted(self, event):
        """Handle file deletion events"""
        if not event.is_directory and event.src_path.endswith(('.yaml', '.yml', '.json')):
            self.logger.info(f"Configuration file deleted: {event.src_path}")
            self.config_manager._handle_file_change(event.src_path, 'deleted')

# ================================================================================
# CONFIGURATION LOADING AND PERSISTENCE
# ================================================================================

class ConfigLoader:
    """Configuration file loading utilities"""
    
    @staticmethod
    def load_from_file(filepath: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from file"""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        try:
            if filepath.suffix.lower() in ['.yaml', '.yml']:
                with open(filepath, 'r') as f:
                    return yaml.safe_load(f) or {}
            elif filepath.suffix.lower() == '.json':
                with open(filepath, 'r') as f:
                    return json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {filepath.suffix}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {filepath}: {e}")
    
    @staticmethod
    def load_from_directory(directory: Union[str, Path]) -> Dict[str, Any]:
        """Load all configuration files from directory"""
        directory = Path(directory)
        config_data = {}
        
        if not directory.exists():
            return config_data
        
        for config_file in directory.glob('*.yaml'):
            try:
                file_data = ConfigLoader.load_from_file(config_file)
                config_name = config_file.stem
                config_data[config_name] = file_data
            except Exception as e:
                logger.warning(f"Failed to load config file {config_file}: {e}")
        
        for config_file in directory.glob('*.yml'):
            try:
                file_data = ConfigLoader.load_from_file(config_file)
                config_name = config_file.stem
                config_data[config_name] = file_data
            except Exception as e:
                logger.warning(f"Failed to load config file {config_file}: {e}")
        
        return config_data

class ConfigPersistence:
    """Configuration persistence utilities"""
    
    @staticmethod
    def save_to_file(config_data: Dict[str, Any], filepath: Union[str, Path]) -> None:
        """Save configuration to file"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if filepath.suffix.lower() in ['.yaml', '.yml']:
                with open(filepath, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
            elif filepath.suffix.lower() == '.json':
                with open(filepath, 'w') as f:
                    json.dump(config_data, f, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported configuration file format: {filepath.suffix}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration to {filepath}: {e}")
    
    @staticmethod
    def backup_config(filepath: Union[str, Path]) -> Path:
        """Create backup of configuration file"""
        filepath = Path(filepath)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = filepath.with_suffix(f".{timestamp}{filepath.suffix}")
        
        if filepath.exists():
            import shutil
            shutil.copy2(filepath, backup_path)
            return backup_path
        
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

# ================================================================================
# ENVIRONMENT AND SECURITY MANAGEMENT
# ================================================================================

class EnvironmentManager:
    """Environment-specific configuration management"""
    
    def __init__(self):
        self._environment_configs: Dict[Environment, Dict[str, Any]] = {}
        self._current_environment = Environment.DEVELOPMENT
    
    def set_environment(self, environment: Union[str, Environment]) -> None:
        """Set current environment"""
        if isinstance(environment, str):
            environment = Environment.from_string(environment)
        
        self._current_environment = environment
        logger.info(f"Environment set to: {environment.value}")
    
    def get_environment(self) -> Environment:
        """Get current environment"""
        return self._current_environment
    
    def load_environment_config(self, environment: Environment, config_data: Dict[str, Any]) -> None:
        """Load configuration for specific environment"""
        self._environment_configs[environment] = config_data
    
    def get_environment_config(self, environment: Optional[Environment] = None) -> Dict[str, Any]:
        """Get configuration for environment"""
        env = environment or self._current_environment
        return self._environment_configs.get(env, {})
    
    def merge_environment_overrides(self, base_config: Dict[str, Any], environment: Optional[Environment] = None) -> Dict[str, Any]:
        """Merge environment-specific overrides into base configuration"""
        env = environment or self._current_environment
        env_config = self.get_environment_config(env)
        
        # Deep merge environment overrides
        merged_config = base_config.copy()
        self._deep_merge(merged_config, env_config)
        
        return merged_config
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Deep merge override dictionary into base dictionary"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

class SecureConfigManager:
    """Secure credential and sensitive configuration management"""
    
    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._encrypted_keys: List[str] = []
    
    def set_secret(self, key: str, value: str, encrypt: bool = True) -> None:
        """Set a secret value"""
        if encrypt:
            # In production, implement proper encryption
            self._secrets[key] = value  # Placeholder - implement encryption
            self._encrypted_keys.append(key)
        else:
            self._secrets[key] = value
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get a secret value"""
        return self._secrets.get(key)
    
    def load_secrets_from_env(self) -> None:
        """Load secrets from environment variables"""
        secret_prefixes = ['API_KEY_', 'SECRET_', 'PASSWORD_', 'TOKEN_']
        
        for env_var, value in os.environ.items():
            for prefix in secret_prefixes:
                if env_var.startswith(prefix):
                    secret_key = env_var.lower()
                    self.set_secret(secret_key, value)
                    break
    
    def mask_sensitive_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in configuration for logging/display"""
        masked_data = config_data.copy()
        sensitive_keys = ['password', 'api_key', 'secret', 'token', 'key']
        
        def mask_recursive(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                        data[key] = "***MASKED***"
                    elif isinstance(value, (dict, list)):
                        mask_recursive(value)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, (dict, list)):
                        mask_recursive(item)
        
        mask_recursive(masked_data)
        return masked_data

# ================================================================================
# CONFIGURATION FACTORY AND BUILDER
# ================================================================================

class ConfigBuilder:
    """Configuration builder for creating configurations programmatically"""
    
    def __init__(self):
        self._config_data: Dict[str, Any] = {}
    
    def set_environment(self, environment: Union[str, Environment]) -> 'ConfigBuilder':
        """Set environment"""
        if isinstance(environment, str):
            environment = Environment.from_string(environment)
        self._config_data['environment'] = environment
        return self
    
    def set_trading_mode(self, mode: Union[str, TradingMode]) -> 'ConfigBuilder':
        """Set trading mode"""
        if isinstance(mode, str):
            mode = TradingMode(mode.lower())
        self._config_data['trading_mode'] = mode
        return self
    
    def add_strategy(self, strategy_id: str, strategy_config: StrategyConfig) -> 'ConfigBuilder':
        """Add strategy configuration"""
        if 'strategies' not in self._config_data:
            self._config_data['strategies'] = {}
        self._config_data['strategies'][strategy_id] = strategy_config
        return self
    
    def set_trading_config(self, trading_config: TradingConfig) -> 'ConfigBuilder':
        """Set trading configuration"""
        self._config_data['trading'] = trading_config
        return self
    
    def set_risk_config(self, risk_config: RiskConfig) -> 'ConfigBuilder':
        """Set risk configuration"""
        self._config_data['risk'] = risk_config
        return self
    
    def enable_feature(self, feature_name: str) -> 'ConfigBuilder':
        """Enable a feature flag"""
        if 'features' not in self._config_data:
            self._config_data['features'] = {}
        self._config_data['features'][feature_name] = True
        return self
    
    def build(self) -> UnifiedConfig:
        """Build the unified configuration"""
        # Create base config
        config = UnifiedConfig()
        
        # Apply builder data
        for key, value in self._config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Validate and return
        config.validate()
        return config

class ConfigFactory:
    """Factory for creating common configuration patterns"""
    
    @staticmethod
    def create_development_config() -> UnifiedConfig:
        """Create development configuration"""
        return ConfigBuilder().set_environment(Environment.DEVELOPMENT).set_trading_mode(TradingMode.PAPER).build()
    
    @staticmethod
    def create_production_config() -> UnifiedConfig:
        """Create production configuration"""
        return ConfigBuilder().set_environment(Environment.PRODUCTION).set_trading_mode(TradingMode.LIVE).build()
    
    @staticmethod
    def create_backtest_config() -> UnifiedConfig:
        """Create backtesting configuration"""
        return ConfigBuilder().set_environment(Environment.BACKTESTING).set_trading_mode(TradingMode.BACKTEST).build()
    
    @staticmethod
    def create_paper_trading_config() -> UnifiedConfig:
        """Create paper trading configuration"""
        return ConfigBuilder().set_environment(Environment.PAPER_TRADING).set_trading_mode(TradingMode.PAPER).build()

# ================================================================================
# MASTER UNIFIED CONFIGURATION MANAGER
# ================================================================================

class UnifiedConfigManager:
    """
    Master unified configuration manager - single source of truth for all system configuration.
    
    Consolidates 8+ competing configuration managers into one professional system with:
    - Hot-reload capabilities
    - Environment management
    - Secure credential handling
    - Change notifications
    - Performance optimization
    """
    
    def __init__(
        self,
        config_file: Optional[Union[str, Path]] = None,
        config_directory: Optional[Union[str, Path]] = None,
        environment: Optional[Union[str, Environment]] = None,
        enable_hot_reload: bool = False,
        enable_file_watching: bool = False
    ):
        """
        Initialize unified configuration manager.
        
        Args:
            config_file: Primary configuration file path
            config_directory: Configuration directory for multiple files
            environment: Environment name or enum
            enable_hot_reload: Enable hot reloading of configuration
            enable_file_watching: Enable file system watching for changes
        """
        self.logger = logging.getLogger(__name__)
        
        # Configuration state
        self._config: Optional[UnifiedConfig] = None
        self._config_lock = Lock()
        self._config_file = Path(config_file) if config_file else None
        self._config_directory = Path(config_directory) if config_directory else None
        
        # Environment and security management
        self._environment_manager = EnvironmentManager()
        self._secure_manager = SecureConfigManager()
        
        # Hot reload and file watching
        self._enable_hot_reload = enable_hot_reload
        self._enable_file_watching = enable_file_watching
        self._file_observer: Optional[Observer] = None
        self._change_callbacks: List[Callable[[ConfigChangeEvent], None]] = []
        
        # Performance optimization
        self._cache: Dict[str, Any] = {}
        self._cache_lock = Lock()
        
        # Initialize environment
        if environment:
            if isinstance(environment, str):
                environment = Environment.from_string(environment)
            self._environment_manager.set_environment(environment)
        else:
            # Auto-detect environment from env var
            env_str = os.getenv('TRADING_ENVIRONMENT', 'development')
            environment = Environment.from_string(env_str)
            self._environment_manager.set_environment(environment)
        
        # Load secrets from environment
        self._secure_manager.load_secrets_from_env()
        
        # Load initial configuration
        self._load_configuration()
        
        # Start file watching if enabled
        if self._enable_file_watching:
            self._start_file_watching()
        
        self.logger.info(f"UnifiedConfigManager initialized for environment: {self._environment_manager.get_environment().value}")
    
    def _load_configuration(self) -> None:
        """Load configuration from files"""
        with self._config_lock:
            try:
                config_data = {}
                
                # Load from primary config file
                if self._config_file and self._config_file.exists():
                    config_data = ConfigLoader.load_from_file(self._config_file)
                
                # Load from config directory
                if self._config_directory and self._config_directory.exists():
                    dir_config = ConfigLoader.load_from_directory(self._config_directory)
                    # Merge directory configs into main config
                    for key, value in dir_config.items():
                        if key in config_data and isinstance(config_data[key], dict) and isinstance(value, dict):
                            config_data[key].update(value)
                        else:
                            config_data[key] = value
                
                # Apply environment overrides
                current_env = self._environment_manager.get_environment()
                config_data = self._environment_manager.merge_environment_overrides(config_data, current_env)
                
                # Create unified config
                if config_data:
                    self._config = UnifiedConfig()
                    self._config.from_dict(config_data)
                else:
                    # Create default config for environment
                    self._config = UnifiedConfig.create_default(current_env)
                
                # Validate configuration
                self._config.validate()
                
                # Clear cache after reload
                with self._cache_lock:
                    self._cache.clear()
                
                self.logger.info("Configuration loaded successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to load configuration: {e}")
                # Fall back to default configuration
                current_env = self._environment_manager.get_environment()
                self._config = UnifiedConfig.create_default(current_env)
                raise ConfigurationError(f"Configuration loading failed: {e}")
    
    def _start_file_watching(self) -> None:
        """Start file system watching for configuration changes"""
        if not WATCHDOG_AVAILABLE:
            self.logger.warning("Watchdog not available - file watching disabled")
            return
            
        if self._file_observer is not None:
            return
        
        try:
            self._file_observer = Observer()
            event_handler = ConfigFileWatcher(self)
            
            # Watch config file directory
            if self._config_file:
                watch_path = self._config_file.parent
                self._file_observer.schedule(event_handler, str(watch_path), recursive=False)
            
            # Watch config directory
            if self._config_directory:
                self._file_observer.schedule(event_handler, str(self._config_directory), recursive=True)
            
            self._file_observer.start()
            self.logger.info("Configuration file watching started")
            
        except Exception as e:
            self.logger.error(f"Failed to start file watching: {e}")
    
    def _stop_file_watching(self) -> None:
        """Stop file system watching"""
        if self._file_observer:
            self._file_observer.stop()
            self._file_observer.join()
            self._file_observer = None
            self.logger.info("Configuration file watching stopped")
    
    def _handle_file_change(self, filepath: str, change_type: str) -> None:
        """Handle configuration file changes"""
        if not self._enable_hot_reload:
            return
        
        try:
            # Debounce rapid file changes
            time.sleep(0.1)
            
            old_config = self._config.to_dict() if self._config else {}
            
            # Reload configuration
            self._load_configuration()
            
            new_config = self._config.to_dict() if self._config else {}
            
            # Create change event
            change_event = ConfigChangeEvent(
                timestamp=datetime.now(timezone.utc),
                config_path=filepath,
                change_type=change_type,
                old_value=old_config,
                new_value=new_config
            )
            
            # Notify callbacks
            self._notify_change_callbacks(change_event)
            
            self.logger.info(f"Configuration hot-reloaded due to {change_type} of {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle configuration file change: {e}")
    
    def _notify_change_callbacks(self, event: ConfigChangeEvent) -> None:
        """Notify all registered change callbacks"""
        for callback in self._change_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Configuration change callback failed: {e}")
    
    # ================================================================================
    # PUBLIC API
    # ================================================================================
    
    def get_config(self) -> UnifiedConfig:
        """Get current unified configuration"""
        if self._config is None:
            raise ConfigurationError("Configuration not loaded")
        return self._config
    
    def reload_config(self) -> None:
        """Manually reload configuration"""
        self._load_configuration()
    
    def save_config(self, filepath: Optional[Union[str, Path]] = None) -> None:
        """Save current configuration to file"""
        if self._config is None:
            raise ConfigurationError("No configuration to save")
        
        save_path = Path(filepath) if filepath else self._config_file
        if save_path is None:
            raise ConfigurationError("No save path specified")
        
        # Create backup
        if save_path.exists():
            ConfigPersistence.backup_config(save_path)
        
        # Save configuration
        config_data = self._config.to_dict()
        ConfigPersistence.save_to_file(config_data, save_path)
        
        self.logger.info(f"Configuration saved to {save_path}")
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        with self._config_lock:
            if self._config is None:
                raise ConfigurationError("Configuration not loaded")
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
            
            # Validate updated configuration
            self._config.validate()
            
            # Clear cache
            with self._cache_lock:
                self._cache.clear()
            
            self.logger.info("Configuration updated successfully")
    
    def get_environment(self) -> Environment:
        """Get current environment"""
        return self._environment_manager.get_environment()
    
    def set_environment(self, environment: Union[str, Environment]) -> None:
        """Set environment and reload configuration"""
        self._environment_manager.set_environment(environment)
        self._load_configuration()
    
    def add_change_callback(self, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """Add configuration change callback"""
        self._change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """Remove configuration change callback"""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get secret value"""
        return self._secure_manager.get_secret(key)
    
    def set_secret(self, key: str, value: str) -> None:
        """Set secret value"""
        self._secure_manager.set_secret(key, value)
    
    @lru_cache(maxsize=128)
    def get_cached_value(self, key: str) -> Any:
        """Get cached configuration value"""
        with self._cache_lock:
            return self._cache.get(key)
    
    def set_cached_value(self, key: str, value: Any) -> None:
        """Set cached configuration value"""
        with self._cache_lock:
            self._cache[key] = value
    
    def _create_default_trading_config(self, trading_mode):
        """Create default trading configuration - compatibility method"""
        from .config_domains import TradingConfig
        return TradingConfig()
    
    def get(self, key: str, default=None):
        """Get configuration value by key - compatibility method"""
        config = self.get_config()
        return getattr(config, key, default)
    
    def get_database_config(self):
        """Get database configuration - compatibility method"""
        config = self.get_config()
        return config.database if config.database else None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self._stop_file_watching()

# ================================================================================
# ALIASES AND COMPATIBILITY
# ================================================================================

# Alias for backward compatibility
ConfigWatcher = ConfigFileWatcher

# ================================================================================
# CONVENIENCE FUNCTIONS
# ================================================================================

# Global configuration manager instance
_global_config_manager: Optional[UnifiedConfigManager] = None
_global_config_lock = Lock()

def get_config_manager() -> UnifiedConfigManager:
    """Get global configuration manager instance"""
    global _global_config_manager
    
    if _global_config_manager is None:
        with _global_config_lock:
            if _global_config_manager is None:
                _global_config_manager = UnifiedConfigManager()
    
    return _global_config_manager

def get_config() -> UnifiedConfig:
    """Get current unified configuration"""
    return get_config_manager().get_config()

def load_config(config_file: Union[str, Path]) -> UnifiedConfig:
    """Load configuration from file"""
    manager = UnifiedConfigManager(config_file=config_file)
    return manager.get_config()

def save_config(config: UnifiedConfig, filepath: Union[str, Path]) -> None:
    """Save configuration to file"""
    config.save_to_file(filepath)

def validate_config(config: UnifiedConfig) -> bool:
    """Validate configuration"""
    return config.validate()

def get_environment() -> Environment:
    """Get current environment"""
    return get_config_manager().get_environment()

def set_environment(environment: Union[str, Environment]) -> None:
    """Set current environment"""
    get_config_manager().set_environment(environment)

def is_production() -> bool:
    """Check if running in production environment"""
    return get_environment() == Environment.PRODUCTION

def is_development() -> bool:
    """Check if running in development environment"""
    return get_environment() == Environment.DEVELOPMENT

def get_api_key(key_name: str) -> Optional[str]:
    """Get API key from secure configuration"""
    return get_config_manager().get_secret(key_name)

def get_database_url() -> str:
    """Get database URL from configuration"""
    config = get_config()
    if config.database and config.database.clickhouse:
        ch_config = config.database.clickhouse
        return f"clickhouse://{ch_config.username}:{ch_config.password}@{ch_config.host}:{ch_config.port}/{ch_config.database}"
    raise ConfigurationError("Database configuration not found")

def get_secret(key: str) -> Optional[str]:
    """Get secret value"""
    return get_config_manager().get_secret(key)

# ================================================================================
# MODULE VALIDATION
# ================================================================================

def __validate_config_manager():
    """Validate configuration manager module integrity"""
    try:
        # Test basic functionality
        manager = UnifiedConfigManager()
        config = manager.get_config()
        assert isinstance(config, UnifiedConfig)
        
        # Test factory methods
        dev_config = ConfigFactory.create_development_config()
        assert dev_config.environment == Environment.DEVELOPMENT
        
        logger.info("Configuration manager module validation passed")
        return True
    except Exception as e:
        logger.error(f"Configuration manager module validation failed: {e}")
        raise ConfigurationError(f"Module validation failed: {e}")

# Run validation on import
__validate_config_manager()
