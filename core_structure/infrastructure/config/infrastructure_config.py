"""
Infrastructure Configuration System for StatArb Trading System
============================================================

This module consolidates infrastructure configurations including database,
logging, monitoring, and system management into a unified infrastructure system.

Consolidated from:
- database_config.py (380 lines) - Database connection and settings
- unified_config_manager.py (463 lines) - Unified configuration management
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime, timedelta
import os
import yaml
import json
import logging
from .core_config import BaseConfig, Environment

logger = logging.getLogger(__name__)

# =============================================================================
# Database Configuration System
# =============================================================================

@dataclass
class ClickHouseConfig(BaseConfig):
    """ClickHouse database configuration"""
    
    # Connection settings
    host: str = "localhost"
    port: int = 9000
    database: str = "trading"
    username: str = "default"
    password: str = ""
    
    # HTTP interface settings
    http_port: int = 8123
    use_http: bool = False
    
    # SSL settings
    use_ssl: bool = False
    ssl_ca_cert: Optional[str] = None
    ssl_client_cert: Optional[str] = None
    ssl_client_key: Optional[str] = None
    verify_ssl: bool = True
    
    # Connection pooling
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    # Query optimization
    max_query_size: int = 65536
    max_result_rows: int = 1000000
    max_execution_time: int = 300
    send_progress_in_http_headers: bool = True
    
    # Compression
    compression: str = "lz4"  # none, lz4, zstd
    compress_block_size: int = 65536
    
    # Advanced settings
    distributed_product_mode: str = "deny"  # deny, local, global, allow
    max_threads: int = 4
    max_memory_usage: int = 10000000000  # 10GB
    
    # Backup and replication
    backup_enabled: bool = False
    backup_schedule: str = "0 2 * * *"  # Daily at 2 AM
    replication_enabled: bool = False
    replica_hosts: List[str] = field(default_factory=list)
    
    # Monitoring
    enable_query_log: bool = True
    slow_query_threshold: float = 5.0  # seconds
    
    def validate(self) -> None:
        """Validate ClickHouse configuration"""
        if not self.host:
            raise ValueError("ClickHouse host is required")
        
        if self.port <= 0 or self.port > 65535:
            raise ValueError("ClickHouse port must be between 1 and 65535")
        
        if self.http_port <= 0 or self.http_port > 65535:
            raise ValueError("ClickHouse HTTP port must be between 1 and 65535")
        
        if not self.database:
            raise ValueError("ClickHouse database name is required")
        
        if self.pool_size <= 0:
            raise ValueError("Pool size must be positive")
        
        if self.max_overflow < 0:
            raise ValueError("Max overflow cannot be negative")
        
        if self.compression not in ["none", "lz4", "zstd"]:
            raise ValueError("Invalid compression type")
        
        if self.max_execution_time <= 0:
            raise ValueError("Max execution time must be positive")
    
    def get_connection_string(self) -> str:
        """Get ClickHouse connection string"""
        if self.use_http:
            protocol = "https" if self.use_ssl else "http"
            return f"{protocol}://{self.username}:{self.password}@{self.host}:{self.http_port}/{self.database}"
        else:
            return f"clickhouse://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def get_client_settings(self) -> Dict[str, Any]:
        """Get ClickHouse client settings"""
        return {
            'max_query_size': self.max_query_size,
            'max_result_rows': self.max_result_rows,
            'max_execution_time': self.max_execution_time,
            'compression': self.compression,
            'compress_block_size': self.compress_block_size,
            'max_threads': self.max_threads,
            'max_memory_usage': self.max_memory_usage
        }


@dataclass
class RedisConfig(BaseConfig):
    """Redis cache configuration"""
    
    # Connection settings
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    
    # Connection pooling
    max_connections: int = 20
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    # SSL settings
    use_ssl: bool = False
    ssl_keyfile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_ca_certs: Optional[str] = None
    ssl_check_hostname: bool = False
    
    # Timeout settings
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = field(default_factory=dict)
    
    # Memory and persistence
    maxmemory_policy: str = "allkeys-lru"
    save_enabled: bool = True
    save_seconds: int = 300
    save_changes: int = 1
    
    # Cache settings
    default_ttl: int = 3600  # 1 hour
    max_key_size: int = 512
    max_value_size: int = 1048576  # 1MB
    
    def validate(self) -> None:
        """Validate Redis configuration"""
        if not self.host:
            raise ValueError("Redis host is required")
        
        if self.port <= 0 or self.port > 65535:
            raise ValueError("Redis port must be between 1 and 65535")
        
        if self.database < 0:
            raise ValueError("Redis database must be non-negative")
        
        if self.max_connections <= 0:
            raise ValueError("Max connections must be positive")
        
        if self.socket_timeout <= 0:
            raise ValueError("Socket timeout must be positive")


@dataclass
class PostgreSQLConfig(BaseConfig):
    """PostgreSQL database configuration"""
    
    # Connection settings
    host: str = "localhost"
    port: int = 5432
    database: str = "trading"
    username: str = "postgres"
    password: str = ""
    
    # SSL settings
    sslmode: str = "prefer"  # disable, allow, prefer, require, verify-ca, verify-full
    sslcert: Optional[str] = None
    sslkey: Optional[str] = None
    sslrootcert: Optional[str] = None
    
    # Connection pooling
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    
    # Query settings
    statement_timeout: int = 300000  # 5 minutes in ms
    lock_timeout: int = 30000  # 30 seconds in ms
    idle_in_transaction_session_timeout: int = 600000  # 10 minutes in ms
    
    # Performance tuning
    shared_buffers: str = "256MB"
    effective_cache_size: str = "1GB"
    work_mem: str = "4MB"
    maintenance_work_mem: str = "64MB"
    
    def validate(self) -> None:
        """Validate PostgreSQL configuration"""
        if not self.host:
            raise ValueError("PostgreSQL host is required")
        
        if self.port <= 0 or self.port > 65535:
            raise ValueError("PostgreSQL port must be between 1 and 65535")
        
        if not self.database:
            raise ValueError("PostgreSQL database name is required")
        
        if self.pool_size <= 0:
            raise ValueError("Pool size must be positive")
        
        valid_ssl_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        if self.sslmode not in valid_ssl_modes:
            raise ValueError(f"Invalid SSL mode. Must be one of: {valid_ssl_modes}")


# =============================================================================
# Logging Configuration System
# =============================================================================

@dataclass
class LoggingConfig(BaseConfig):
    """Comprehensive logging configuration"""
    
    # Basic settings
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    
    # File logging
    enable_file_logging: bool = True
    log_directory: str = "logs"
    log_filename: str = "trading_system.log"
    max_file_size_mb: int = 100
    backup_count: int = 5
    
    # Console logging
    enable_console_logging: bool = True
    console_level: str = "INFO"
    console_format: Optional[str] = None
    
    # Structured logging
    enable_json_logging: bool = False
    include_extra_fields: bool = True
    
    # Performance logging
    enable_performance_logging: bool = True
    performance_log_file: str = "performance.log"
    slow_operation_threshold_ms: int = 1000
    
    # Error logging
    enable_error_logging: bool = True
    error_log_file: str = "errors.log"
    include_stack_trace: bool = True
    
    # Audit logging
    enable_audit_logging: bool = True
    audit_log_file: str = "audit.log"
    audit_events: List[str] = field(default_factory=lambda: [
        "trade_execution", "order_placement", "risk_breach", 
        "configuration_change", "system_startup", "system_shutdown"
    ])
    
    # Remote logging
    enable_remote_logging: bool = False
    remote_log_endpoint: Optional[str] = None
    remote_log_api_key: Optional[str] = None
    
    # Log rotation
    rotation_policy: str = "size"  # size, time, none
    rotation_when: str = "midnight"  # for time-based rotation
    rotation_interval: int = 1
    
    def validate(self) -> None:
        """Validate logging configuration"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        
        if self.console_level not in valid_levels:
            raise ValueError(f"Invalid console log level. Must be one of: {valid_levels}")
        
        if self.max_file_size_mb <= 0:
            raise ValueError("Max file size must be positive")
        
        if self.backup_count < 0:
            raise ValueError("Backup count cannot be negative")
        
        valid_rotations = ["size", "time", "none"]
        if self.rotation_policy not in valid_rotations:
            raise ValueError(f"Invalid rotation policy. Must be one of: {valid_rotations}")


# =============================================================================
# Monitoring Configuration System
# =============================================================================

@dataclass
class MonitoringConfig(BaseConfig):
    """System monitoring configuration"""
    
    # General monitoring
    enable_monitoring: bool = True
    monitoring_interval_seconds: int = 60
    health_check_interval_seconds: int = 30
    
    # Performance monitoring
    enable_performance_monitoring: bool = True
    cpu_threshold_percent: float = 80.0
    memory_threshold_percent: float = 85.0
    disk_threshold_percent: float = 90.0
    
    # Application monitoring
    enable_application_monitoring: bool = True
    response_time_threshold_ms: int = 5000
    error_rate_threshold_percent: float = 5.0
    
    # Database monitoring
    enable_database_monitoring: bool = True
    db_connection_threshold: int = 80
    slow_query_threshold_seconds: float = 5.0
    
    # Trading monitoring
    enable_trading_monitoring: bool = True
    position_limit_threshold_percent: float = 90.0
    pnl_threshold_percent: float = -5.0  # -5% daily loss
    
    # Alerting
    enable_alerting: bool = True
    alert_channels: List[str] = field(default_factory=lambda: ["email", "slack"])
    email_recipients: List[str] = field(default_factory=list)
    slack_webhook: Optional[str] = None
    
    # Metrics collection
    enable_metrics_collection: bool = True
    metrics_retention_days: int = 30
    metrics_aggregation_intervals: List[int] = field(default_factory=lambda: [60, 300, 3600])  # 1m, 5m, 1h
    
    def validate(self) -> None:
        """Validate monitoring configuration"""
        if self.monitoring_interval_seconds <= 0:
            raise ValueError("Monitoring interval must be positive")
        
        if self.cpu_threshold_percent <= 0 or self.cpu_threshold_percent > 100:
            raise ValueError("CPU threshold must be between 0 and 100")
        
        if self.memory_threshold_percent <= 0 or self.memory_threshold_percent > 100:
            raise ValueError("Memory threshold must be between 0 and 100")
        
        if self.metrics_retention_days <= 0:
            raise ValueError("Metrics retention days must be positive")


# =============================================================================
# Message Queue Configuration System
# =============================================================================

@dataclass
class MessageQueueConfig(BaseConfig):
    """Message queue configuration for asynchronous processing"""
    
    # Queue settings
    provider: str = "redis"  # redis, rabbitmq, kafka
    host: str = "localhost"
    port: int = 6379
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Queue configuration
    default_queue: str = "trading_tasks"
    priority_queue: str = "priority_tasks"
    dead_letter_queue: str = "failed_tasks"
    
    # Worker settings
    max_workers: int = 4
    worker_timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 60
    
    # Message settings
    message_ttl_seconds: int = 3600
    max_message_size_kb: int = 1024
    enable_message_compression: bool = True
    
    # Monitoring
    enable_queue_monitoring: bool = True
    queue_size_threshold: int = 1000
    processing_time_threshold_seconds: int = 30
    
    def validate(self) -> None:
        """Validate message queue configuration"""
        valid_providers = ["redis", "rabbitmq", "kafka"]
        if self.provider not in valid_providers:
            raise ValueError(f"Invalid provider. Must be one of: {valid_providers}")
        
        if self.max_workers <= 0:
            raise ValueError("Max workers must be positive")
        
        if self.worker_timeout_seconds <= 0:
            raise ValueError("Worker timeout must be positive")


# =============================================================================
# Unified Infrastructure Configuration
# =============================================================================

@dataclass
class InfrastructureConfig(BaseConfig):
    """Consolidated infrastructure configuration"""
    
    # Database configurations
    clickhouse: ClickHouseConfig = field(default_factory=ClickHouseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    postgresql: PostgreSQLConfig = field(default_factory=PostgreSQLConfig)
    
    # System configurations
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    message_queue: MessageQueueConfig = field(default_factory=MessageQueueConfig)
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=dict)
    
    # Environment-specific overrides
    environment_overrides: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate all infrastructure configurations"""
        self.clickhouse.validate()
        self.redis.validate()
        self.postgresql.validate()
        self.logging.validate()
        self.monitoring.validate()
        self.message_queue.validate()


# =============================================================================
# Configuration Management System
# =============================================================================

class InfrastructureConfigManager:
    """Unified infrastructure configuration management system"""
    
    def __init__(self, config_dir: Optional[str] = None, environment: Environment = Environment.DEVELOPMENT):
        self.config_dir = Path(config_dir) if config_dir else Path("configs")
        self.environment = environment
        
        # Initialize configurations
        self._config = self._load_config()
        
        # Dynamic settings
        self._dynamic_settings = {}
        
        # Feature flags
        self._feature_flags = self._load_feature_flags()
        
        logger.info(f"Initialized InfrastructureConfigManager for environment: {self.environment.value}")
    
    def _load_config(self) -> InfrastructureConfig:
        """Load configuration from files and environment"""
        # Start with default configuration
        config = InfrastructureConfig(environment=self.environment)
        
        # Load base configuration file
        base_config_file = self.config_dir / "infrastructure.yaml"
        if base_config_file.exists():
            config = self._merge_config_from_file(config, base_config_file)
        
        # Load environment-specific configuration
        env_config_file = self.config_dir / f"infrastructure.{self.environment.value}.yaml"
        if env_config_file.exists():
            config = self._merge_config_from_file(config, env_config_file)
        
        # Apply environment variable overrides
        config = self._apply_env_overrides(config)
        
        return config
    
    def _merge_config_from_file(self, config: InfrastructureConfig, file_path: Path) -> InfrastructureConfig:
        """Merge configuration from YAML file"""
        try:
            with open(file_path, 'r') as f:
                file_config = yaml.safe_load(f)
            
            # Merge configurations (file config takes precedence)
            return self._deep_merge_configs(config, file_config)
        
        except Exception as e:
            logger.warning(f"Failed to load config file {file_path}: {e}")
            return config
    
    def _apply_env_overrides(self, config: InfrastructureConfig) -> InfrastructureConfig:
        """Apply environment variable overrides"""
        # ClickHouse overrides
        if os.getenv('CLICKHOUSE_HOST'):
            config.clickhouse.host = os.getenv('CLICKHOUSE_HOST')
        if os.getenv('CLICKHOUSE_PORT'):
            config.clickhouse.port = int(os.getenv('CLICKHOUSE_PORT'))
        if os.getenv('CLICKHOUSE_DATABASE'):
            config.clickhouse.database = os.getenv('CLICKHOUSE_DATABASE')
        if os.getenv('CLICKHOUSE_USERNAME'):
            config.clickhouse.username = os.getenv('CLICKHOUSE_USERNAME')
        if os.getenv('CLICKHOUSE_PASSWORD'):
            config.clickhouse.password = os.getenv('CLICKHOUSE_PASSWORD')
        
        # Redis overrides
        if os.getenv('REDIS_HOST'):
            config.redis.host = os.getenv('REDIS_HOST')
        if os.getenv('REDIS_PORT'):
            config.redis.port = int(os.getenv('REDIS_PORT'))
        if os.getenv('REDIS_PASSWORD'):
            config.redis.password = os.getenv('REDIS_PASSWORD')
        
        # Logging overrides
        if os.getenv('LOG_LEVEL'):
            config.logging.level = os.getenv('LOG_LEVEL')
        if os.getenv('LOG_DIRECTORY'):
            config.logging.log_directory = os.getenv('LOG_DIRECTORY')
        
        return config
    
    def _deep_merge_configs(self, base_config: InfrastructureConfig, override_dict: Dict[str, Any]) -> InfrastructureConfig:
        """Deep merge configuration dictionaries"""
        # This is a simplified merge - in production, use a proper deep merge utility
        for key, value in override_dict.items():
            if hasattr(base_config, key):
                if isinstance(value, dict) and hasattr(getattr(base_config, key), '__dict__'):
                    # Merge nested configuration objects
                    nested_config = getattr(base_config, key)
                    for nested_key, nested_value in value.items():
                        if hasattr(nested_config, nested_key):
                            setattr(nested_config, nested_key, nested_value)
                else:
                    setattr(base_config, key, value)
        
        return base_config
    
    def _load_feature_flags(self) -> Dict[str, bool]:
        """Load feature flags from configuration"""
        return self._config.features.copy()
    
    def get_config(self) -> InfrastructureConfig:
        """Get the current infrastructure configuration"""
        return self._config
    
    def get_feature_flag(self, flag_name: str, default: bool = False) -> bool:
        """Get feature flag value"""
        return self._feature_flags.get(flag_name, default)
    
    def set_feature_flag(self, flag_name: str, value: bool) -> None:
        """Set feature flag value"""
        self._feature_flags[flag_name] = value
        self._config.features[flag_name] = value
    
    def get_dynamic_setting(self, key: str, default: Any = None) -> Any:
        """Get dynamic setting value"""
        return self._dynamic_settings.get(key, default)
    
    def set_dynamic_setting(self, key: str, value: Any) -> None:
        """Set dynamic setting value"""
        self._dynamic_settings[key] = value
    
    def save_config(self, file_path: Optional[Path] = None) -> None:
        """Save current configuration to file"""
        if file_path is None:
            file_path = self.config_dir / f"infrastructure.{self.environment.value}.yaml"
        
        config_dict = self._config.to_dict()
        
        with open(file_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
        
        logger.info(f"Configuration saved to {file_path}")
    
    def reload_config(self) -> None:
        """Reload configuration from files"""
        self._config = self._load_config()
        self._feature_flags = self._load_feature_flags()
        logger.info("Configuration reloaded")


# =============================================================================
# Infrastructure Configuration Factory
# =============================================================================

class InfrastructureConfigFactory:
    """Factory for creating infrastructure configurations"""
    
    @staticmethod
    def create_development_config() -> InfrastructureConfig:
        """Create development environment configuration"""
        config = InfrastructureConfig(environment=Environment.DEVELOPMENT)
        
        # Development-specific settings
        config.logging.level = "DEBUG"
        config.logging.enable_console_logging = True
        config.monitoring.monitoring_interval_seconds = 30
        config.clickhouse.pool_size = 5
        config.redis.max_connections = 10
        
        return config
    
    @staticmethod
    def create_production_config() -> InfrastructureConfig:
        """Create production environment configuration"""
        config = InfrastructureConfig(environment=Environment.PRODUCTION)
        
        # Production-specific settings
        config.logging.level = "INFO"
        config.logging.enable_file_logging = True
        config.logging.enable_audit_logging = True
        config.monitoring.enable_alerting = True
        config.clickhouse.pool_size = 20
        config.clickhouse.backup_enabled = True
        config.redis.max_connections = 50
        config.postgresql.pool_size = 30
        
        return config
    
    @staticmethod
    def create_testing_config() -> InfrastructureConfig:
        """Create testing environment configuration"""
        config = InfrastructureConfig(environment=Environment.TESTING)
        
        # Testing-specific settings
        config.logging.level = "WARNING"
        config.monitoring.enable_monitoring = False
        config.clickhouse.database = "trading_test"
        config.redis.database = 1
        config.postgresql.database = "trading_test"
        
        return config


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Database configurations
    'ClickHouseConfig',
    'RedisConfig',
    'PostgreSQLConfig',
    
    # System configurations
    'LoggingConfig',
    'MonitoringConfig',
    'MessageQueueConfig',
    
    # Consolidated configuration
    'InfrastructureConfig',
    'InfrastructureConfigManager',
    'InfrastructureConfigFactory'
]
