"""
Unified Configuration Management - Core Engine
==============================================

Centralized configuration management system with environment-specific overrides.
Supports YAML, JSON, and environment variable configurations.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum
import yaml

from core_engine.utils.config import deep_merge
from core_engine.config.yaml_loader import load_with_includes

logger = logging.getLogger(__name__)

class ConfigFormat(Enum):
    """Supported configuration formats"""
    YAML = "yaml"
    JSON = "json"
    ENV = "env"

@dataclass
class ConfigSource:
    """Configuration source metadata"""
    path: Optional[Path] = None
    format: ConfigFormat = ConfigFormat.YAML
    priority: int = 100  # Higher priority overrides lower
    required: bool = False

@dataclass
class UnifiedConfig:
    """
    Unified configuration management system

    Supports hierarchical configuration loading with environment overrides.
    Configuration sources are loaded in priority order (higher priority wins).
    """

    # Configuration sources
    sources: List[ConfigSource] = field(default_factory=list)

    # Loaded configuration
    _config: Dict[str, Any] = field(default_factory=dict)
    _loaded: bool = False

    def add_source(self, path: Union[str, Path], format: ConfigFormat = ConfigFormat.YAML,
                  priority: int = 100, required: bool = False) -> 'UnifiedConfig':
        """Add a configuration source"""
        source = ConfigSource(
            path=Path(path) if path else None,
            format=format,
            priority=priority,
            required=required
        )
        self.sources.append(source)
        self.sources.sort(key=lambda s: s.priority, reverse=True)  # Higher priority first
        return self

    def add_env_source(self, prefix: str = "", priority: int = 200) -> 'UnifiedConfig':
        """Add environment variables as configuration source"""
        source = ConfigSource(
            path=None,
            format=ConfigFormat.ENV,
            priority=priority,
            required=False
        )
        # Store prefix in path for env vars
        source.path = Path(prefix) if prefix else None
        self.sources.append(source)
        self.sources.sort(key=lambda s: s.priority, reverse=True)
        return self

    def load(self) -> Dict[str, Any]:
        """Load configuration from all sources"""
        if self._loaded:
            return self._config.copy()

        config = {}

        # Sort sources by priority ascending: low priority first, high priority last
        # so that high priority sources override lower ones in the deep_merge loop.
        sorted_sources = sorted(self.sources, key=lambda s: s.priority)

        for source in sorted_sources:
            try:
                source_config = self._load_source(source)
                if source_config:
                    # Deep merge with higher priority sources overriding lower
                    config = deep_merge(config, source_config)
            except Exception as e:
                if source.required:
                    raise RuntimeError(f"Failed to load required config source {source.path}: {e}")
                else:
                    logger.warning(f"Failed to load config source {source.path}: {e}")

        self._config = config
        self._loaded = True
        logger.info(f"Configuration loaded from {len(self.sources)} sources (priority-ordered)")
        return config.copy()

    def _load_source(self, source: ConfigSource) -> Dict[str, Any]:
        """Load configuration from a single source"""
        if source.format == ConfigFormat.ENV:
            return self._load_env_config(source.path.name if source.path else "")
        elif source.format == ConfigFormat.YAML:
            return self._load_yaml_config(source.path)
        elif source.format == ConfigFormat.JSON:
            return self._load_json_config(source.path)
        else:
            raise ValueError(f"Unsupported config format: {source.format}")

    def _load_yaml_config(self, path: Optional[Path]) -> Dict[str, Any]:
        """Load YAML configuration file with recursive includes"""
        if not path or not path.exists():
            return {}

        try:
            return load_with_includes(path)
        except Exception as e:
            logger.error(f"Failed to load YAML with includes from {path}: {e}")
            # Fallback to simple load if include loader fails
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}

    def _load_json_config(self, path: Optional[Path]) -> Dict[str, Any]:
        """Load JSON configuration file"""
        if not path or not path.exists():
            return {}

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_env_config(self, prefix: str = "") -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        prefix_upper = prefix.upper() + "_" if prefix else ""

        for key, value in os.environ.items():
            if key.startswith(prefix_upper):
                # Remove prefix and convert to nested dict
                config_key = key[len(prefix_upper):].lower()
                self._set_nested_config(config, config_key.split('_'), value)

        return config

    def _set_nested_config(self, config: Dict[str, Any], keys: List[str], value: str):
        """Set a nested configuration value"""
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Try to convert value to appropriate type
        final_key = keys[-1]
        current[final_key] = self._convert_value(value)

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        if value is None:
            return None
        
        # String case-insensitive match
        v_lower = value.lower().strip()
        
        # None/Null conversion
        if v_lower in ('none', 'null', ''):
            return None

        # Boolean conversion
        if v_lower in ('true', 'yes', 'on', '1'):
            return True
        elif v_lower in ('false', 'no', 'off', '0'):
            return False

        # Numeric conversion
        try:
            if '.' in value or 'e' in v_lower:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        return value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        if not self._loaded:
            self.load()

        keys = key.split('.')
        current = self._config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def set(self, key: str, value: Any):
        """Set configuration value"""
        keys = key.split('.')
        current = self._config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

    def reload(self):
        """Reload configuration from sources"""
        self._loaded = False
        self._config.clear()
        return self.load()

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get configuration section"""
        value = self.get(section, {})
        return value if isinstance(value, dict) else {}

# Global configuration instance
_config = UnifiedConfig()

def get_config() -> UnifiedConfig:
    """Get the global configuration instance"""
    return _config

def init_config(config_dir: Optional[Union[str, Path]] = None,
               env_prefix: str = "CORE_ENGINE") -> UnifiedConfig:
    """
    Initialize global configuration

    Args:
        config_dir: Directory containing configuration files
        env_prefix: Environment variable prefix
    """
    global _config

    # Reset config
    _config = UnifiedConfig()

    # Add default configuration sources
    if config_dir:
        config_path = Path(config_dir)

        # Base configuration
        _config.add_source(config_path / "config.yaml", ConfigFormat.YAML, priority=50)
        _config.add_source(config_path / "config.json", ConfigFormat.JSON, priority=50)

        # Environment-specific configuration
        env = os.getenv("CORE_ENGINE_ENV", "development").lower()
        _config.add_source(config_path / f"config.{env}.yaml", ConfigFormat.YAML, priority=75)
        _config.add_source(config_path / f"config.{env}.json", ConfigFormat.JSON, priority=75)

    # Environment variables (highest priority)
    _config.add_env_source(env_prefix, priority=200)

    # Load configuration
    _config.load()

    logger.info("Configuration initialized")
    return _config

# Convenience functions
def config_get(key: str, default: Any = None) -> Any:
    """Get configuration value"""
    return get_config().get(key, default)

def config_set(key: str, value: Any):
    """Set configuration value"""
    get_config().set(key, value)

def config_section(section: str) -> Dict[str, Any]:
    """Get configuration section"""
    return get_config().get_section(section)