#!/usr/bin/env python3
"""
Unified Configuration - Core Configuration Classes
=================================================

Master configuration system consolidating all fragmented configuration across the StatArb system.
Provides type-safe, validated, hierarchical configuration with professional enterprise features.

CONSOLIDATION TARGET:
- Replaces 6+ competing "unified" configuration managers
- Eliminates 78+ scattered UnifiedConfig references  
- Provides single source of truth for all system configuration

Author: Professional Trading System Architecture
Version: 3.0.0 (True Unification)
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Type, TypeVar, Generic
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timezone
from abc import ABC, abstractmethod
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# ================================================================================
# CORE ENUMS AND TYPES
# ================================================================================

class Environment(Enum):
    """Canonical environment enumeration - single source of truth"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    BACKTESTING = "backtesting"
    PAPER_TRADING = "paper_trading"
    STAGING = "staging"
    PRODUCTION = "production"
    
    @classmethod
    def from_string(cls, env_str: str) -> 'Environment':
        """Convert string to Environment enum with validation"""
        try:
            return cls(env_str.lower())
        except ValueError:
            raise ValueError(f"Invalid environment: {env_str}. Valid options: {[e.value for e in cls]}")
    
    @property
    def is_production(self) -> bool:
        return self == Environment.PRODUCTION
    
    @property
    def is_live_trading(self) -> bool:
        return self in [Environment.PRODUCTION, Environment.PAPER_TRADING]
    
    @property
    def requires_security(self) -> bool:
        return self in [Environment.PRODUCTION, Environment.STAGING]

class TradingMode(Enum):
    """Trading execution modes"""
    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"
    SIMULATION = "simulation"
    
    # Backward compatibility aliases
    PAPER_TRADING = "paper"
    LIVE_TRADING = "live"
    BACKTESTING = "backtest"
    
class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ConfigurationError(Exception):
    """Base exception for configuration errors"""
    pass

class ValidationError(ConfigurationError):
    """Configuration validation error"""
    pass

# ================================================================================
# BASE CONFIGURATION FRAMEWORK
# ================================================================================

T = TypeVar('T', bound='BaseConfig')

@dataclass
class ConfigMetadata:
    """Configuration metadata for tracking and validation"""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "3.0.0"
    source_file: Optional[str] = None
    environment: Optional[Environment] = None
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    def mark_updated(self):
        """Mark configuration as updated"""
        self.updated_at = datetime.now(timezone.utc)
    
    def add_validation_error(self, error: str):
        """Add validation error"""
        self.validation_errors.append(error)
        self.validated = False
    
    def clear_validation_errors(self):
        """Clear validation errors"""
        self.validation_errors.clear()
        self.validated = True

class BaseConfig(ABC):
    """
    Abstract base class for all configuration objects.
    Provides common validation, serialization, and metadata functionality.
    """
    
    def __init__(self):
        self._metadata = ConfigMetadata()
    
    @property
    def metadata(self) -> ConfigMetadata:
        """Get configuration metadata"""
        return self._metadata
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate configuration - must be implemented by subclasses"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        if hasattr(self, '__dataclass_fields__'):
            return asdict(self)
        else:
            # Fallback for non-dataclass configs
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def from_dict(self, data: Dict[str, Any]) -> 'BaseConfig':
        """Create configuration from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self
    
    def save_to_file(self, filepath: Union[str, Path]) -> None:
        """Save configuration to file"""
        filepath = Path(filepath)
        data = self.to_dict()
        
        if filepath.suffix.lower() in ['.yaml', '.yml']:
            with open(filepath, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)
        elif filepath.suffix.lower() == '.json':
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported file format: {filepath.suffix}")
        
        self._metadata.source_file = str(filepath)
        self._metadata.mark_updated()
    
    @classmethod
    def load_from_file(cls: Type[T], filepath: Union[str, Path]) -> T:
        """Load configuration from file"""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        if filepath.suffix.lower() in ['.yaml', '.yml']:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
        elif filepath.suffix.lower() == '.json':
            with open(filepath, 'r') as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {filepath.suffix}")
        
        instance = cls()
        instance.from_dict(data)
        instance._metadata.source_file = str(filepath)
        return instance

# ================================================================================
# VALIDATION FRAMEWORK
# ================================================================================

@dataclass
class ValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        """Add validation error"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add validation warning"""
        self.warnings.append(warning)
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

class ConfigValidator:
    """
    Professional configuration validation system.
    Provides comprehensive validation with detailed error reporting.
    """
    
    @staticmethod
    def validate_positive_number(value: Union[int, float], name: str, result: ValidationResult):
        """Validate that a number is positive"""
        if not isinstance(value, (int, float)):
            result.add_error(f"{name} must be a number, got {type(value).__name__}")
        elif value <= 0:
            result.add_error(f"{name} must be positive, got {value}")
    
    @staticmethod
    def validate_non_negative_number(value: Union[int, float], name: str, result: ValidationResult):
        """Validate that a number is non-negative"""
        if not isinstance(value, (int, float)):
            result.add_error(f"{name} must be a number, got {type(value).__name__}")
        elif value < 0:
            result.add_error(f"{name} must be non-negative, got {value}")
    
    @staticmethod
    def validate_percentage(value: float, name: str, result: ValidationResult):
        """Validate that a value is a valid percentage (0-100)"""
        if not isinstance(value, (int, float)):
            result.add_error(f"{name} must be a number, got {type(value).__name__}")
        elif not 0 <= value <= 100:
            result.add_error(f"{name} must be between 0 and 100, got {value}")
    
    @staticmethod
    def validate_ratio(value: float, name: str, result: ValidationResult):
        """Validate that a value is a valid ratio (0-1)"""
        if not isinstance(value, (int, float)):
            result.add_error(f"{name} must be a number, got {type(value).__name__}")
        elif not 0 <= value <= 1:
            result.add_error(f"{name} must be between 0 and 1, got {value}")
    
    @staticmethod
    def validate_required_string(value: str, name: str, result: ValidationResult):
        """Validate that a string is not empty"""
        if not isinstance(value, str):
            result.add_error(f"{name} must be a string, got {type(value).__name__}")
        elif not value.strip():
            result.add_error(f"{name} cannot be empty")
    
    @staticmethod
    def validate_file_path(path: Union[str, Path], name: str, result: ValidationResult, must_exist: bool = True):
        """Validate file path"""
        try:
            path_obj = Path(path)
            if must_exist and not path_obj.exists():
                result.add_error(f"{name} file does not exist: {path}")
        except Exception as e:
            result.add_error(f"{name} invalid path: {e}")
    
    @staticmethod
    def validate_environment_config(env: Environment, config: BaseConfig, result: ValidationResult):
        """Validate configuration for specific environment"""
        if env.requires_security:
            # Production/staging specific validations
            if hasattr(config, 'debug') and getattr(config, 'debug', False):
                result.add_warning(f"Debug mode enabled in {env.value} environment")
            
            if hasattr(config, 'log_level') and getattr(config, 'log_level') == LogLevel.DEBUG:
                result.add_warning(f"Debug logging enabled in {env.value} environment")

# ================================================================================
# MASTER UNIFIED CONFIGURATION
# ================================================================================

@dataclass
class UnifiedConfig(BaseConfig):
    """
    Master unified configuration class - single source of truth for entire system.
    
    Consolidates all configuration domains into one coherent, validated structure.
    Replaces all fragmented configuration systems across the codebase.
    """
    
    # ================================
    # CORE SYSTEM CONFIGURATION
    # ================================
    environment: Environment = Environment.DEVELOPMENT
    trading_mode: TradingMode = TradingMode.PAPER
    
    # ================================
    # DOMAIN CONFIGURATIONS
    # ================================
    # These will be populated by config_domains.py
    trading: Optional['TradingConfig'] = None
    risk: Optional['RiskConfig'] = None
    system: Optional['SystemConfig'] = None
    database: Optional['DatabaseConfig'] = None
    logging: Optional['LoggingConfig'] = None
    monitoring: Optional['MonitoringConfig'] = None
    ai: Optional['AIConfig'] = None
    market_data: Optional['MarketDataConfig'] = None
    
    # ================================
    # STRATEGY CONFIGURATIONS
    # ================================
    strategies: Dict[str, 'StrategyConfig'] = field(default_factory=dict)
    
    # ================================
    # FEATURE FLAGS AND EXTENSIONS
    # ================================
    features: Dict[str, bool] = field(default_factory=dict)
    experimental: Dict[str, Any] = field(default_factory=dict)
    
    # ================================
    # METADATA AND VERSIONING
    # ================================
    config_version: str = "3.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Initialize configuration after creation"""
        super().__init__()
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Initialize default configurations for all domains"""
        # Import here to avoid circular imports
        from .config_domains import (
            TradingConfig, RiskConfig, SystemConfig, DatabaseConfig,
            LoggingConfig, MonitoringConfig, AIConfig, MarketDataConfig
        )
        
        # Initialize domain configs if not provided
        if self.trading is None:
            self.trading = TradingConfig()
        if self.risk is None:
            self.risk = RiskConfig()
        if self.system is None:
            self.system = SystemConfig()
        if self.database is None:
            self.database = DatabaseConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()
        if self.ai is None:
            self.ai = AIConfig()
        if self.market_data is None:
            self.market_data = MarketDataConfig()
    
    def validate(self) -> bool:
        """Comprehensive validation of entire configuration"""
        result = ValidationResult(is_valid=True)
        
        # Validate core configuration
        if not isinstance(self.environment, Environment):
            result.add_error("environment must be a valid Environment enum")
        
        if not isinstance(self.trading_mode, TradingMode):
            result.add_error("trading_mode must be a valid TradingMode enum")
        
        # Validate domain configurations
        domain_configs = [
            ('trading', self.trading),
            ('risk', self.risk),
            ('system', self.system),
            ('database', self.database),
            ('logging', self.logging),
            ('monitoring', self.monitoring),
            ('ai', self.ai),
            ('market_data', self.market_data),
        ]
        
        for domain_name, domain_config in domain_configs:
            if domain_config is not None:
                try:
                    if hasattr(domain_config, 'validate'):
                        domain_config.validate()
                except Exception as e:
                    result.add_error(f"{domain_name} configuration validation failed: {e}")
        
        # Validate strategies
        for strategy_id, strategy_config in self.strategies.items():
            try:
                if hasattr(strategy_config, 'validate'):
                    strategy_config.validate()
            except Exception as e:
                result.add_error(f"Strategy {strategy_id} validation failed: {e}")
        
        # Environment-specific validation
        ConfigValidator.validate_environment_config(self.environment, self, result)
        
        # Update metadata
        self._metadata.validation_errors = result.errors
        self._metadata.validated = result.is_valid
        
        if not result.is_valid:
            error_msg = f"Configuration validation failed: {'; '.join(result.errors)}"
            logger.error(error_msg)
            raise ValidationError(error_msg)
        
        if result.has_warnings:
            logger.warning(f"Configuration warnings: {'; '.join(result.warnings)}")
        
        return True
    
    def get_strategy_config(self, strategy_id: str) -> Optional['StrategyConfig']:
        """Get configuration for specific strategy"""
        return self.strategies.get(strategy_id)
    
    def add_strategy_config(self, strategy_id: str, config: 'StrategyConfig'):
        """Add strategy configuration"""
        self.strategies[strategy_id] = config
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_strategy_config(self, strategy_id: str) -> bool:
        """Remove strategy configuration"""
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def enable_feature(self, feature_name: str):
        """Enable a feature flag"""
        self.features[feature_name] = True
        self.updated_at = datetime.now(timezone.utc)
    
    def disable_feature(self, feature_name: str):
        """Disable a feature flag"""
        self.features[feature_name] = False
        self.updated_at = datetime.now(timezone.utc)
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self.features.get(feature_name, False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        data = super().to_dict()
        
        # Convert enums to strings
        data['environment'] = self.environment.value
        data['trading_mode'] = self.trading_mode.value
        
        # Convert datetime objects
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        
        # Convert domain configs
        for domain in ['trading', 'risk', 'system', 'database', 'logging', 'monitoring', 'ai', 'market_data']:
            domain_config = getattr(self, domain)
            if domain_config is not None and hasattr(domain_config, 'to_dict'):
                data[domain] = domain_config.to_dict()
        
        # Convert strategy configs
        data['strategies'] = {
            strategy_id: strategy_config.to_dict() if hasattr(strategy_config, 'to_dict') else strategy_config
            for strategy_id, strategy_config in self.strategies.items()
        }
        
        return data
    
    @classmethod
    def create_default(cls, environment: Environment = Environment.DEVELOPMENT) -> 'UnifiedConfig':
        """Create default configuration for specified environment"""
        config = cls(environment=environment)
        
        # Set environment-specific defaults
        if environment == Environment.PRODUCTION:
            config.trading_mode = TradingMode.LIVE
            config.logging.log_level = LogLevel.INFO
            config.system.debug = False
        elif environment == Environment.PAPER_TRADING:
            config.trading_mode = TradingMode.PAPER
            config.logging.log_level = LogLevel.INFO
        elif environment == Environment.BACKTESTING:
            config.trading_mode = TradingMode.BACKTEST
            config.logging.log_level = LogLevel.WARNING
        else:  # Development, Testing
            config.trading_mode = TradingMode.PAPER
            config.logging.log_level = LogLevel.DEBUG
            config.system.debug = True
        
        return config

# ================================================================================
# CONVENIENCE FUNCTIONS
# ================================================================================

@lru_cache(maxsize=1)
def get_default_config() -> UnifiedConfig:
    """Get default configuration (cached)"""
    env_str = os.getenv('TRADING_ENVIRONMENT', 'development')
    environment = Environment.from_string(env_str)
    return UnifiedConfig.create_default(environment)

def create_config_for_environment(environment: Union[str, Environment]) -> UnifiedConfig:
    """Create configuration for specific environment"""
    if isinstance(environment, str):
        environment = Environment.from_string(environment)
    return UnifiedConfig.create_default(environment)

# ================================================================================
# MODULE VALIDATION
# ================================================================================

def __validate_unified_config():
    """Validate unified config module integrity"""
    try:
        # Test basic functionality
        config = UnifiedConfig()
        config.validate()
        
        # Test serialization
        data = config.to_dict()
        assert isinstance(data, dict)
        
        logger.info("Unified configuration module validation passed")
        return True
    except Exception as e:
        logger.error(f"Unified configuration module validation failed: {e}")
        raise ConfigurationError(f"Module validation failed: {e}")

# Run validation on import
__validate_unified_config()
