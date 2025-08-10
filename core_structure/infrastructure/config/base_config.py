"""
Base Configuration Classes for StatArb Trading System

This module provides structured configuration dataclasses with validation,
environment variable support, and type safety for all system components.
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
    
    def save_to_file(self, file_path: Union[str, Path], format: str = "yaml"):
        """Save config to file"""
        file_path = Path(file_path)
        
        if format.lower() == "yaml":
            with open(file_path, 'w') as f:
                f.write(self.to_yaml())
        elif format.lower() == "json":
            with open(file_path, 'w') as f:
                f.write(self.to_json())
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_env_var(self, key: str, default: Any = None, 
                   cast_type: type = str) -> Any:
        """Get environment variable with type casting"""
        value = os.getenv(key, default)
        
        if value is None:
            return default
        
        try:
            if cast_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif cast_type == int:
                return int(value)
            elif cast_type == float:
                return float(value)
            elif cast_type == list:
                return value.split(',') if value else []
            else:
                return cast_type(value)
        except (ValueError, TypeError):
            return default
    
    def merge_with_env_vars(self, prefix: str = "") -> None:
        """Merge configuration with environment variables"""
        for field_name in self.__dataclass_fields__:
            env_var_name = f"{prefix}{field_name.upper()}"
            if env_var_name in os.environ:
                field_type = self.__dataclass_fields__[field_name].type
                env_value = self.get_env_var(env_var_name, cast_type=field_type)
                setattr(self, field_name, env_value)


@dataclass
class SystemConfig(BaseConfig):
    """System-wide configuration"""
    
    # System identification
    system_name: str = "StatArb_Gemini"
    instance_id: str = field(default_factory=lambda: f"instance_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # Performance settings
    max_workers: int = 4
    memory_limit_gb: int = 8
    cpu_cores: int = 4
    
    # Monitoring and health checks
    health_check_interval: int = 30  # seconds
    metrics_collection_interval: int = 60  # seconds
    
    # Error handling
    max_retries: int = 3
    retry_delay: float = 1.0
    circuit_breaker_threshold: int = 5
    
    # File paths
    data_directory: str = "/data"
    logs_directory: str = "/logs"
    config_directory: str = "/config"
    
    def validate(self) -> None:
        """Validate system configuration"""
        if self.max_workers <= 0:
            raise ValueError("max_workers must be positive")
        
        if self.memory_limit_gb <= 0:
            raise ValueError("memory_limit_gb must be positive")
        
        if self.cpu_cores <= 0:
            raise ValueError("cpu_cores must be positive")
        
        if self.health_check_interval <= 0:
            raise ValueError("health_check_interval must be positive")


@dataclass 
class SecurityConfig(BaseConfig):
    """Security configuration"""
    
    # Authentication
    jwt_secret_key: str = field(default="your-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # API security
    api_rate_limit: int = 1000  # requests per hour
    max_request_size_mb: int = 10
    
    # Encryption
    encryption_key: Optional[str] = None
    hash_algorithm: str = "sha256"
    
    # Network security
    allowed_hosts: List[str] = field(default_factory=lambda: ["localhost", "127.0.0.1"])
    cors_origins: List[str] = field(default_factory=list)
    
    # Data protection
    mask_sensitive_data: bool = True
    data_retention_days: int = 365
    
    def validate(self) -> None:
        """Validate security configuration"""
        if len(self.jwt_secret_key) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        
        if self.jwt_expiration_hours <= 0:
            raise ValueError("JWT expiration must be positive")
        
        if self.api_rate_limit <= 0:
            raise ValueError("API rate limit must be positive")


@dataclass
class NotificationConfig(BaseConfig):
    """Notification and alerting configuration"""
    
    # Email settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    
    # Slack settings
    slack_webhook_url: str = ""
    slack_channel: str = "#trading-alerts"
    
    # Alert settings
    enable_email_alerts: bool = False
    enable_slack_alerts: bool = False
    enable_sms_alerts: bool = False
    
    # Alert thresholds
    critical_error_threshold: int = 1
    performance_degradation_threshold: float = 0.1  # 10% degradation
    
    # Recipients
    alert_recipients: List[str] = field(default_factory=list)
    critical_recipients: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Validate notification configuration"""
        if self.enable_email_alerts and not self.smtp_host:
            raise ValueError("SMTP host required for email alerts")
        
        if self.enable_slack_alerts and not self.slack_webhook_url:
            raise ValueError("Slack webhook URL required for Slack alerts")
        
        if self.smtp_port <= 0 or self.smtp_port > 65535:
            raise ValueError("SMTP port must be between 1 and 65535")


@dataclass
class MonitoringConfig(BaseConfig):
    """Monitoring and observability configuration"""
    
    # Metrics collection
    enable_metrics: bool = True
    metrics_port: int = 9090
    metrics_path: str = "/metrics"
    
    # Prometheus settings
    prometheus_enabled: bool = False
    prometheus_endpoint: str = "http://localhost:9090"
    
    # Grafana settings
    grafana_enabled: bool = False
    grafana_endpoint: str = "http://localhost:3000"
    
    # Health checks
    health_check_endpoints: List[str] = field(default_factory=lambda: ["/health", "/ready"])
    deep_health_check_interval: int = 300  # seconds
    
    # Performance monitoring
    track_response_times: bool = True
    track_memory_usage: bool = True
    track_cpu_usage: bool = True
    
    # Alerting thresholds
    response_time_threshold_ms: int = 1000
    memory_usage_threshold_percent: int = 80
    cpu_usage_threshold_percent: int = 75
    
    def validate(self) -> None:
        """Validate monitoring configuration"""
        if self.metrics_port <= 0 or self.metrics_port > 65535:
            raise ValueError("Metrics port must be between 1 and 65535")
        
        if not self.metrics_path.startswith("/"):
            raise ValueError("Metrics path must start with /")
        
        if self.response_time_threshold_ms <= 0:
            raise ValueError("Response time threshold must be positive")


class ConfigurationManager:
    """Centralized configuration management"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "config"
        self.configs: Dict[str, BaseConfig] = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files"""
        if not self.config_dir.exists():
            return
        
        config_files = {
            'system': 'system_config.yaml',
            'security': 'security_config.yaml', 
            'notification': 'notification_config.yaml',
            'monitoring': 'monitoring_config.yaml'
        }
        
        for config_name, filename in config_files.items():
            config_path = self.config_dir / filename
            if config_path.exists():
                try:
                    if config_name == 'system':
                        self.configs[config_name] = SystemConfig.from_yaml_file(config_path)
                    elif config_name == 'security':
                        self.configs[config_name] = SecurityConfig.from_yaml_file(config_path)
                    elif config_name == 'notification':
                        self.configs[config_name] = NotificationConfig.from_yaml_file(config_path)
                    elif config_name == 'monitoring':
                        self.configs[config_name] = MonitoringConfig.from_yaml_file(config_path)
                except Exception as e:
    
    def get_config(self, config_type: str) -> Optional[BaseConfig]:
        """Get configuration by type"""
        return self.configs.get(config_type)
    
    def set_config(self, config_type: str, config: BaseConfig):
        """Set configuration"""
        self.configs[config_type] = config
    
    def save_all_configs(self):
        """Save all configurations to files"""
        self.config_dir.mkdir(exist_ok=True)
        
        config_files = {
            'system': 'system_config.yaml',
            'security': 'security_config.yaml',
            'notification': 'notification_config.yaml', 
            'monitoring': 'monitoring_config.yaml'
        }
        
        for config_type, filename in config_files.items():
            if config_type in self.configs:
                config_path = self.config_dir / filename
                self.configs[config_type].save_to_file(config_path, "yaml")
    
    def validate_all_configs(self) -> Dict[str, Optional[str]]:
        """Validate all configurations"""
        validation_results = {}
        
        for config_type, config in self.configs.items():
            try:
                config.validate()
                validation_results[config_type] = None
            except Exception as e:
                validation_results[config_type] = str(e)
        
        return validation_results
    
    def get_merged_config(self) -> Dict[str, Any]:
        """Get all configurations merged into a single dictionary"""
        merged = {}
        for config_type, config in self.configs.items():
            merged[config_type] = config.to_dict()
        return merged
