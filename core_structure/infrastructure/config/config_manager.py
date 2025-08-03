"""
Configuration management system with environment handling and dynamic settings
"""
from typing import Dict, Any, Optional, Union
import os
import json
import yaml
from pathlib import Path
import logging
from functools import lru_cache
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Configuration management system that handles:
    - Environment-specific settings
    - Secure credentials
    - Dynamic configuration updates
    - Feature flags
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Optional directory containing config files
        """
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.env = os.getenv("APP_ENV", "development")
        
        # Load environment variables
        self._load_env_vars()
        
        # Load configuration files
        self._config = self._load_config()
        
        # Dynamic settings
        self._dynamic_settings = {}
        
        # Feature flags
        self._feature_flags = self._load_feature_flags()
    
    def _load_env_vars(self):
        """Load environment variables from .env file"""
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
        
        # Load environment-specific .env file
        env_specific_file = Path(f".env.{self.env}")
        if env_specific_file.exists():
            load_dotenv(env_specific_file, override=True)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from files"""
        config = {}
        
        # Load base config
        base_config = self.config_dir / "base_config.yaml"
        if base_config.exists():
            with open(base_config) as f:
                config.update(yaml.safe_load(f))
        
        # Load environment-specific config
        env_config = self.config_dir / f"{self.env}_config.yaml"
        if env_config.exists():
            with open(env_config) as f:
                config.update(yaml.safe_load(f))
        
        # Load local overrides (not version controlled)
        local_config = self.config_dir / "local_config.yaml"
        if local_config.exists():
            with open(local_config) as f:
                config.update(yaml.safe_load(f))
        
        return config
    
    def _load_feature_flags(self) -> Dict[str, bool]:
        """Load feature flags configuration"""
        feature_flags_file = self.config_dir / "feature_flags.yaml"
        if not feature_flags_file.exists():
            return {}
        
        with open(feature_flags_file) as f:
            return yaml.safe_load(f)
    
    @lru_cache(maxsize=100)
    def get_database_config(self) -> Dict[str, Any]:
        """
        Get database configuration
        
        Returns:
            Dict containing database configuration
        """
        db_config = self._config.get('database', {})
        
        # Override with environment variables if present
        env_mapping = {
            'DB_HOST': 'host',
            'DB_PORT': 'port',
            'DB_NAME': 'database',
            'DB_USER': 'user',
            'DB_PASSWORD': 'password',
            # Also support CLICKHOUSE_ prefix
            'CLICKHOUSE_HOST': 'host',
            'CLICKHOUSE_PORT': 'port',
            'CLICKHOUSE_DATABASE': 'database',
            'CLICKHOUSE_USER': 'user',
            'CLICKHOUSE_PASSWORD': 'password'
        }
        
        for env_var, config_key in env_mapping.items():
            if os.getenv(env_var):
                db_config[config_key] = os.getenv(env_var)
        
        return db_config
    
    def get_strategy_settings(self, strategy_name: str) -> Dict[str, Any]:
        """
        Get strategy-specific settings
        
        Args:
            strategy_name: Name of the trading strategy
            
        Returns:
            Dict containing strategy settings
        """
        return self._config.get('strategies', {}).get(strategy_name, {})
    
    def get_feature_flag(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled
        
        Args:
            flag_name: Name of the feature flag
            
        Returns:
            Boolean indicating if feature is enabled
        """
        return self._feature_flags.get(flag_name, False)
    
    def update_dynamic_setting(
        self,
        key: str,
        value: Any,
        persist: bool = False
    ) -> None:
        """
        Update a dynamic setting
        
        Args:
            key: Setting key
            value: Setting value
            persist: Whether to persist the setting to disk
        """
        self._dynamic_settings[key] = value
        
        if persist:
            dynamic_settings_file = self.config_dir / "dynamic_settings.json"
            with open(dynamic_settings_file, 'w') as f:
                json.dump(self._dynamic_settings, f, indent=2)
    
    def get_dynamic_setting(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get a dynamic setting value
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value
        """
        return self._dynamic_settings.get(key, default)
    
    def reload_config(self) -> None:
        """Reload configuration from disk"""
        self._config = self._load_config()
        self._feature_flags = self._load_feature_flags()
        
        # Clear cached values
        self.get_database_config.cache_clear()
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """
        Get monitoring configuration
        
        Returns:
            Dict containing monitoring settings
        """
        return self._config.get('monitoring', {})
    
    def get_messaging_config(self) -> Dict[str, Any]:
        """
        Get messaging configuration
        
        Returns:
            Dict containing messaging settings
        """
        return self._config.get('messaging', {})
    
    def get_ai_config(self) -> Dict[str, Any]:
        """
        Get AI/LLM configuration
        
        Returns:
            Dict containing AI-related settings
        """
        return self._config.get('ai', {})
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access to configuration"""
        return self._config.get(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with default
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self._config.get(key, default)
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get complete configuration
        
        Returns:
            Complete configuration dictionary
        """
        return self._config.copy() 