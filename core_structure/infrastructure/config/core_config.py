"""
Core Configuration System for StatArb Trading System
===================================================

This module consolidates base configuration framework, environment management,
and validation logic into a unified core configuration system.

Consolidated from:
- base_config.py (388 lines) - Base configuration framework
- env_config.py (186 lines) - Environment-specific settings  
- config_validator.py (330 lines) - Configuration validation logic
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum
import yaml
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Core Enums and Types
# =============================================================================

class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ValidationError:
    """Configuration validation error"""
    field: str
    message: str
    value: Any


# =============================================================================
# Base Configuration Framework
# =============================================================================

@dataclass
class BaseConfig(ABC):
    """Base configuration class with common functionality"""
    
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    config_version: str = "1.0.0"
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization validation"""
        self.validate()
    
    @abstractmethod
    def validate(self) -> None:
        """Validate configuration parameters"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result
    
    def to_yaml(self) -> str:
        """Convert config to YAML string"""
        return yaml.dump(self.to_dict(), default_flow_style=False)
    
    def to_json(self) -> str:
        """Convert config to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create config from dictionary"""
        # Handle enum conversions
        if 'environment' in data and isinstance(data['environment'], str):
            data['environment'] = Environment(data['environment'])
        if 'log_level' in data and isinstance(data['log_level'], str):
            data['log_level'] = LogLevel(data['log_level'])
        if 'last_updated' in data and isinstance(data['last_updated'], str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        return cls(**data)
    
    @classmethod
    def from_yaml_file(cls, file_path: Union[str, Path]):
        """Load config from YAML file"""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_json_file(cls, file_path: Union[str, Path]):
        """Load config from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def save_to_yaml(self, file_path: Union[str, Path]) -> None:
        """Save config to YAML file"""
        with open(file_path, 'w') as f:
            f.write(self.to_yaml())
    
    def save_to_json(self, file_path: Union[str, Path]) -> None:
        """Save config to JSON file"""
        with open(file_path, 'w') as f:
            f.write(self.to_json())
    
    def get_env_var(self, key: str, default: Any = None) -> Any:
        """Get environment variable with fallback"""
        return os.getenv(key, default)
    
    def merge_with(self, other_config: 'BaseConfig') -> None:
        """Merge with another config (other takes precedence)"""
        for key, value in other_config.__dict__.items():
            if hasattr(self, key):
                setattr(self, key, value)


# =============================================================================
# Environment Configuration Management
# =============================================================================

def load_env_file(env_file: str = ".env") -> Dict[str, str]:
    """
    Load environment variables from a .env file
    
    Args:
        env_file: Path to the environment file
        
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    env_path = Path(env_file)
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars


def get_api_key(service: str, env_file: Optional[str] = None) -> Optional[str]:
    """
    Get API key for a service from environment variables
    
    Args:
        service: Service name (e.g., 'polygon', 'alpha_vantage')
        env_file: Optional path to .env file
        
    Returns:
        API key if found, None otherwise
    """
    # Map service names to environment variable names
    service_map = {
        'polygon': 'POLYGON_API_KEY',
        'alpha_vantage': 'ALPHA_VANTAGE_API_KEY',
        'iex': 'IEX_API_KEY',
        'quandl': 'QUANDL_API_KEY'
    }
    
    env_var = service_map.get(service.lower())
    if not env_var:
        return None
    
    # Try to get from OS environment first
    api_key = os.getenv(env_var)
    
    # If not found and env_file specified, try loading from file
    if not api_key and env_file:
        env_vars = load_env_file(env_file)
        api_key = env_vars.get(env_var)
    
    return api_key


def get_database_config(env_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Get database configuration from environment
    
    Args:
        env_file: Optional path to .env file
        
    Returns:
        Database configuration dictionary
    """
    # Load from .env file if specified
    env_vars = {}
    if env_file:
        env_vars = load_env_file(env_file)
    
    # Get values from environment or .env file
    def get_env(key: str, default: Any = None) -> Any:
        return os.getenv(key, env_vars.get(key, default))
    
    config = {
        'host': get_env('CLICKHOUSE_HOST', 'localhost'),
        'port': int(get_env('CLICKHOUSE_PORT', 9000)),
        'database': get_env('CLICKHOUSE_DATABASE', 'polygon_data'),
        'user': get_env('CLICKHOUSE_USER', 'default'),
        'password': get_env('CLICKHOUSE_PASSWORD', ''),
        'pool_size': int(get_env('CLICKHOUSE_POOL_SIZE', 5))
    }
    
    return config


def get_feeds_config(env_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Get market data feeds configuration
    
    Args:
        env_file: Optional path to .env file
        
    Returns:
        Feeds configuration dictionary
    """
    polygon_key = get_api_key('polygon', env_file)
    alpha_vantage_key = get_api_key('alpha_vantage', env_file)
    
    config = {
        'feeds': {}
    }
    
    # Add Polygon feed if API key available
    if polygon_key:
        config['feeds']['polygon'] = {
            'enabled': True,
            'api_key': polygon_key,
            'base_url': 'https://api.polygon.io',
            'ws_url': 'wss://socket.polygon.io/stocks',
            'timeout': 30,
            'max_retries': 3
        }
    
    # Add Alpha Vantage feed if API key available
    if alpha_vantage_key:
        config['feeds']['alpha_vantage'] = {
            'enabled': True,
            'api_key': alpha_vantage_key,
            'base_url': 'https://www.alphavantage.co',
            'timeout': 30,
            'poll_interval': 60
        }
    
    return config


class SecureConfigManager:
    """
    Secure configuration manager that loads from environment variables
    """
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self._load_env_file()
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        if os.path.exists(self.env_file):
            env_vars = load_env_file(self.env_file)
            for key, value in env_vars.items():
                if key not in os.environ:  # Don't override existing env vars
                    os.environ[key] = value
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for a service"""
        return get_api_key(service, self.env_file)
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return get_database_config(self.env_file)
    
    def get_feeds_config(self) -> Dict[str, Any]:
        """Get feeds configuration"""
        return get_feeds_config(self.env_file)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        # Handle nested keys like 'market_data.feeds'
        if '.' in key:
            parts = key.split('.')
            if parts[0] == 'market_data' and parts[1] == 'feeds':
                return self.get_feeds_config().get('feeds', {})
        
        # Handle database config
        if key == 'database':
            return self.get_database_config()
        
        # Default behavior - get from environment
        return os.getenv(key, default)


# =============================================================================
# Configuration Validation System
# =============================================================================

class ConfigValidator:
    """Configuration validation and schema checking"""
    
    def __init__(self):
        self.schemas = self._load_validation_schemas()
    
    def validate_strategy_config(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate strategy configuration"""
        errors = []
        
        # Required fields
        required_fields = ['name', 'version', 'parameters', 'risk_limits', 'timeframes', 'symbols']
        for field in required_fields:
            if field not in config:
                errors.append(ValidationError(field, f"Required field missing: {field}", None))
        
        # Parameter validation
        if 'parameters' in config:
            param_errors = self._validate_parameters(config['parameters'])
            errors.extend(param_errors)
        
        # Risk limits validation
        if 'risk_limits' in config:
            risk_errors = self._validate_risk_limits(config['risk_limits'])
            errors.extend(risk_errors)
        
        return errors
    
    def _validate_parameters(self, parameters: Dict[str, Any]) -> List[ValidationError]:
        """Validate strategy parameters based on academic research"""
        errors = []
        
        # Multi-horizon momentum parameters (Moskowitz et al., 2012)
        if 'momentum_lookback_short' in parameters:
            value = parameters['momentum_lookback_short']
            if not (1 <= value <= 50):
                errors.append(ValidationError(
                    'momentum_lookback_short', 
                    f"Value {value} out of academic range [1, 50] days", 
                    value
                ))
        
        if 'momentum_lookback_medium' in parameters:
            value = parameters['momentum_lookback_medium']
            if not (20 <= value <= 100):
                errors.append(ValidationError(
                    'momentum_lookback_medium', 
                    f"Value {value} out of academic range [20, 100] days", 
                    value
                ))
        
        if 'momentum_lookback_long' in parameters:
            value = parameters['momentum_lookback_long']
            if not (50 <= value <= 150):
                errors.append(ValidationError(
                    'momentum_lookback_long', 
                    f"Value {value} out of academic range [50, 150] days", 
                    value
                ))
        
        # Volume parameters (Gervais et al., 2001)
        if 'volume_weight' in parameters:
            value = parameters['volume_weight']
            if not (0.0 <= value <= 1.0):
                errors.append(ValidationError(
                    'volume_weight', 
                    f"Value {value} out of range [0.0, 1.0]", 
                    value
                ))
        
        if 'volume_threshold' in parameters:
            value = parameters['volume_threshold']
            if not (100000 <= value <= 10000000):  # $100K to $10M
                errors.append(ValidationError(
                    'volume_threshold', 
                    f"Value {value} out of reasonable range [$100K, $10M]", 
                    value
                ))
        
        # Regime detection parameters (Cooper et al., 2004)
        if 'regime_lookback' in parameters:
            value = parameters['regime_lookback']
            if not (100 <= value <= 500):
                errors.append(ValidationError(
                    'regime_lookback', 
                    f"Value {value} out of range [100, 500] days", 
                    value
                ))
        
        # Cross-correlation parameters (Menchero et al., 2011)
        if 'correlation_threshold' in parameters:
            value = parameters['correlation_threshold']
            if not (0.1 <= value <= 0.95):
                errors.append(ValidationError(
                    'correlation_threshold', 
                    f"Value {value} out of range [0.1, 0.95]", 
                    value
                ))
        
        # Portfolio optimization parameters (Markowitz, 1952)
        if 'rebalance_frequency' in parameters:
            value = parameters['rebalance_frequency']
            if value not in ['daily', 'weekly', 'monthly', 'quarterly']:
                errors.append(ValidationError(
                    'rebalance_frequency', 
                    f"Value {value} not in allowed options", 
                    value
                ))
        
        return errors
    
    def _validate_risk_limits(self, risk_limits: Dict[str, Any]) -> List[ValidationError]:
        """Validate risk management limits"""
        errors = []
        
        # Position size limits
        if 'max_position_size' in risk_limits:
            value = risk_limits['max_position_size']
            if not (0.01 <= value <= 0.20):  # 1% to 20%
                errors.append(ValidationError(
                    'max_position_size', 
                    f"Value {value} out of range [0.01, 0.20]", 
                    value
                ))
        
        if 'max_portfolio_leverage' in risk_limits:
            value = risk_limits['max_portfolio_leverage']
            if not (1.0 <= value <= 3.0):
                errors.append(ValidationError(
                    'max_portfolio_leverage', 
                    f"Value {value} out of range [1.0, 3.0]", 
                    value
                ))
        
        # Drawdown limits
        if 'max_drawdown' in risk_limits:
            value = risk_limits['max_drawdown']
            if not (0.05 <= value <= 0.30):  # 5% to 30%
                errors.append(ValidationError(
                    'max_drawdown', 
                    f"Value {value} out of range [0.05, 0.30]", 
                    value
                ))
        
        # VaR limits
        if 'var_limit' in risk_limits:
            value = risk_limits['var_limit']
            if not (0.01 <= value <= 0.10):  # 1% to 10%
                errors.append(ValidationError(
                    'var_limit', 
                    f"Value {value} out of range [0.01, 0.10]", 
                    value
                ))
        
        return errors
    
    def validate_database_config(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate database configuration"""
        errors = []
        
        required_fields = ['host', 'port', 'database', 'user']
        for field in required_fields:
            if field not in config:
                errors.append(ValidationError(field, f"Required field missing: {field}", None))
        
        # Port validation
        if 'port' in config:
            port = config['port']
            if not (1 <= port <= 65535):
                errors.append(ValidationError(
                    'port', 
                    f"Port {port} out of valid range [1, 65535]", 
                    port
                ))
        
        # Pool size validation
        if 'pool_size' in config:
            pool_size = config['pool_size']
            if not (1 <= pool_size <= 50):
                errors.append(ValidationError(
                    'pool_size', 
                    f"Pool size {pool_size} out of reasonable range [1, 50]", 
                    pool_size
                ))
        
        return errors
    
    def validate_trading_config(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate trading configuration"""
        errors = []
        
        # Market hours validation
        if 'market_open' in config and 'market_close' in config:
            open_time = config['market_open']
            close_time = config['market_close']
            
            # Validate format and logical consistency
            if isinstance(open_time, str) and isinstance(close_time, str):
                try:
                    from datetime import datetime
                    open_dt = datetime.strptime(open_time, "%H:%M")
                    close_dt = datetime.strptime(close_time, "%H:%M")
                    
                    if open_dt >= close_dt:
                        errors.append(ValidationError(
                            'market_hours', 
                            "Market close time must be after open time", 
                            (open_time, close_time)
                        ))
                except ValueError as e:
                    errors.append(ValidationError(
                        'market_hours', 
                        f"Invalid time format: {e}", 
                        (open_time, close_time)
                    ))
        
        return errors
    
    def _load_validation_schemas(self) -> Dict[str, Any]:
        """Load validation schemas (placeholder for future schema definitions)"""
        return {
            'strategy': {},
            'risk': {},
            'database': {},
            'trading': {}
        }


# =============================================================================
# Main Configuration Classes
# =============================================================================

@dataclass
class SystemConfig(BaseConfig):
    """Core system configuration"""
    
    # System identification
    system_name: str = "StatArb_Trading_System"
    version: str = "2.0.0"
    
    # Environment settings
    workspace_root: str = ""
    data_directory: str = "data"
    logs_directory: str = "logs"
    temp_directory: str = "temp"
    
    # Security settings
    enable_secure_mode: bool = True
    api_rate_limit: int = 1000
    session_timeout: timedelta = timedelta(hours=8)
    
    # Performance settings
    max_workers: int = 4
    cache_size: int = 1000
    memory_limit_gb: int = 8
    
    def validate(self) -> None:
        """Validate system configuration"""
        validator = ConfigValidator()
        errors = []
        
        # Validate workspace root exists
        if self.workspace_root and not os.path.exists(self.workspace_root):
            errors.append(ValidationError(
                'workspace_root',
                f"Workspace root does not exist: {self.workspace_root}",
                self.workspace_root
            ))
        
        # Validate numeric limits
        if self.max_workers < 1:
            errors.append(ValidationError(
                'max_workers',
                f"max_workers must be >= 1, got {self.max_workers}",
                self.max_workers
            ))
        
        if self.memory_limit_gb < 1:
            errors.append(ValidationError(
                'memory_limit_gb',
                f"memory_limit_gb must be >= 1, got {self.memory_limit_gb}",
                self.memory_limit_gb
            ))
        
        if errors:
            error_messages = [f"{err.field}: {err.message}" for err in errors]
            raise ValueError(f"Configuration validation failed: {', '.join(error_messages)}")


# =============================================================================
# Core Configuration Factory
# =============================================================================

class CoreConfigFactory:
    """Factory for creating and managing core configurations"""
    
    @staticmethod
    def create_system_config(
        environment: Environment = Environment.DEVELOPMENT,
        workspace_root: Optional[str] = None
    ) -> SystemConfig:
        """Create a system configuration"""
        
        if workspace_root is None:
            workspace_root = os.getcwd()
        
        return SystemConfig(
            environment=environment,
            workspace_root=workspace_root,
            debug=(environment == Environment.DEVELOPMENT),
            log_level=LogLevel.DEBUG if environment == Environment.DEVELOPMENT else LogLevel.INFO
        )
    
    @staticmethod
    def load_from_env(env_file: str = ".env") -> SystemConfig:
        """Load configuration from environment variables"""
        config_manager = SecureConfigManager(env_file)
        
        return SystemConfig(
            environment=Environment(os.getenv('ENVIRONMENT', 'development')),
            workspace_root=os.getenv('WORKSPACE_ROOT', os.getcwd()),
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            max_workers=int(os.getenv('MAX_WORKERS', '4')),
            memory_limit_gb=int(os.getenv('MEMORY_LIMIT_GB', '8'))
        )


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Enums
    'Environment',
    'LogLevel',
    
    # Base classes
    'BaseConfig',
    'ValidationError',
    
    # Environment management
    'load_env_file',
    'get_api_key',
    'get_database_config',
    'get_feeds_config',
    'SecureConfigManager',
    
    # Validation
    'ConfigValidator',
    
    # Core configuration
    'SystemConfig',
    'CoreConfigFactory'
]
