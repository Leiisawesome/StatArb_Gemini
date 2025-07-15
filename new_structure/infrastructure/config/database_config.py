"""
Database Configuration for StatArb Trading System

This module provides database-specific configuration classes for ClickHouse,
Redis, PostgreSQL, and other data stores with connection pooling and optimization.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from .base_config import BaseConfig


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
            "max_query_size": self.max_query_size,
            "max_result_rows": self.max_result_rows,
            "max_execution_time": self.max_execution_time,
            "send_progress_in_http_headers": self.send_progress_in_http_headers,
            "compression": self.compression,
            "compress_block_size": self.compress_block_size,
            "distributed_product_mode": self.distributed_product_mode,
            "max_threads": self.max_threads,
            "max_memory_usage": self.max_memory_usage
        }


@dataclass
class RedisConfig(BaseConfig):
    """Redis database configuration"""
    
    # Connection settings
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    username: Optional[str] = None
    
    # SSL settings
    use_ssl: bool = False
    ssl_ca_cert: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_check_hostname: bool = True
    
    # Connection pooling
    max_connections: int = 50
    retry_on_timeout: bool = True
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = field(default_factory=dict)
    
    # Redis configuration
    decode_responses: bool = True
    encoding: str = "utf-8"
    encoding_errors: str = "strict"
    
    # Cluster settings
    cluster_enabled: bool = False
    cluster_nodes: List[Dict[str, Union[str, int]]] = field(default_factory=list)
    skip_full_coverage_check: bool = False
    max_connections_per_node: int = 50
    
    # Sentinel settings
    sentinel_enabled: bool = False
    sentinels: List[Dict[str, Union[str, int]]] = field(default_factory=list)
    sentinel_service_name: str = "mymaster"
    sentinel_socket_timeout: float = 0.1
    
    # Performance settings
    health_check_interval: int = 30
    max_idle_connections: int = 10
    retry_on_error: List[str] = field(default_factory=lambda: ["LOADING", "BUSY"])
    
    # Memory optimization
    max_memory_policy: str = "allkeys-lru"
    maxmemory_samples: int = 5
    
    def validate(self) -> None:
        """Validate Redis configuration"""
        if not self.host:
            raise ValueError("Redis host is required")
        
        if self.port <= 0 or self.port > 65535:
            raise ValueError("Redis port must be between 1 and 65535")
        
        if self.database < 0:
            raise ValueError("Redis database number cannot be negative")
        
        if self.max_connections <= 0:
            raise ValueError("Max connections must be positive")
        
        if self.socket_timeout <= 0:
            raise ValueError("Socket timeout must be positive")
        
        if self.cluster_enabled and not self.cluster_nodes:
            raise ValueError("Cluster nodes required when cluster is enabled")
        
        if self.sentinel_enabled and not self.sentinels:
            raise ValueError("Sentinels required when sentinel is enabled")
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get Redis connection parameters"""
        params = {
            "host": self.host,
            "port": self.port,
            "db": self.database,
            "password": self.password,
            "username": self.username,
            "socket_timeout": self.socket_timeout,
            "socket_connect_timeout": self.socket_connect_timeout,
            "socket_keepalive": self.socket_keepalive,
            "socket_keepalive_options": self.socket_keepalive_options,
            "retry_on_timeout": self.retry_on_timeout,
            "decode_responses": self.decode_responses,
            "encoding": self.encoding,
            "encoding_errors": self.encoding_errors,
            "health_check_interval": self.health_check_interval,
            "ssl": self.use_ssl,
            "ssl_ca_certs": self.ssl_ca_cert,
            "ssl_certfile": self.ssl_cert,
            "ssl_keyfile": self.ssl_key,
            "ssl_check_hostname": self.ssl_check_hostname,
        }
        
        # Remove None values
        return {k: v for k, v in params.items() if v is not None}


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
    statement_timeout: int = 300000  # milliseconds
    idle_in_transaction_session_timeout: int = 600000  # milliseconds
    application_name: str = "StatArb_Gemini"
    
    # Performance settings
    shared_buffers: str = "256MB"
    effective_cache_size: str = "1GB"
    maintenance_work_mem: str = "64MB"
    checkpoint_completion_target: float = 0.9
    wal_buffers: str = "16MB"
    default_statistics_target: int = 100
    
    # Logging
    log_statement: str = "none"  # none, ddl, mod, all
    log_min_duration_statement: int = 1000  # milliseconds
    
    def validate(self) -> None:
        """Validate PostgreSQL configuration"""
        if not self.host:
            raise ValueError("PostgreSQL host is required")
        
        if self.port <= 0 or self.port > 65535:
            raise ValueError("PostgreSQL port must be between 1 and 65535")
        
        if not self.database:
            raise ValueError("PostgreSQL database name is required")
        
        if not self.username:
            raise ValueError("PostgreSQL username is required")
        
        if self.pool_size <= 0:
            raise ValueError("Pool size must be positive")
        
        if self.sslmode not in ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]:
            raise ValueError("Invalid SSL mode")
        
        if self.statement_timeout <= 0:
            raise ValueError("Statement timeout must be positive")
    
    def get_connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class DatabaseConfig(BaseConfig):
    """Combined database configuration"""
    
    # Primary databases
    clickhouse: ClickHouseConfig = field(default_factory=ClickHouseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    postgresql: Optional[PostgreSQLConfig] = field(default_factory=PostgreSQLConfig)
    
    # Database selection
    primary_timeseries_db: str = "clickhouse"
    primary_cache_db: str = "redis"
    primary_metadata_db: str = "postgresql"
    
    # Connection management
    connection_timeout: float = 30.0
    read_timeout: float = 60.0
    write_timeout: float = 30.0
    
    # Backup settings
    auto_backup: bool = False
    backup_schedule: str = "0 3 * * *"  # Daily at 3 AM
    backup_retention_days: int = 30
    
    # Monitoring
    enable_connection_monitoring: bool = True
    slow_query_threshold: float = 5.0
    connection_pool_monitoring: bool = True
    
    # Migration settings
    auto_migrate: bool = False
    migration_timeout: int = 300
    
    def validate(self) -> None:
        """Validate database configuration"""
        # Validate individual database configs
        self.clickhouse.validate()
        self.redis.validate()
        if self.postgresql:
            self.postgresql.validate()
        
        # Validate database selections
        valid_timeseries_dbs = ["clickhouse"]
        if self.primary_timeseries_db not in valid_timeseries_dbs:
            raise ValueError(f"Invalid timeseries DB: {self.primary_timeseries_db}")
        
        valid_cache_dbs = ["redis"]
        if self.primary_cache_db not in valid_cache_dbs:
            raise ValueError(f"Invalid cache DB: {self.primary_cache_db}")
        
        valid_metadata_dbs = ["postgresql", "clickhouse"]
        if self.primary_metadata_db not in valid_metadata_dbs:
            raise ValueError(f"Invalid metadata DB: {self.primary_metadata_db}")
        
        # Validate timeouts
        if self.connection_timeout <= 0:
            raise ValueError("Connection timeout must be positive")
        
        if self.read_timeout <= 0:
            raise ValueError("Read timeout must be positive")
        
        if self.write_timeout <= 0:
            raise ValueError("Write timeout must be positive")
        
        if self.backup_retention_days <= 0:
            raise ValueError("Backup retention days must be positive")
    
    def get_database_config(self, db_type: str) -> Optional[BaseConfig]:
        """Get specific database configuration"""
        configs = {
            "clickhouse": self.clickhouse,
            "redis": self.redis,
            "postgresql": self.postgresql
        }
        return configs.get(db_type.lower())
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for all databases"""
        info = {
            "clickhouse": {
                "connection_string": self.clickhouse.get_connection_string(),
                "settings": self.clickhouse.get_client_settings()
            },
            "redis": {
                "connection_params": self.redis.get_connection_params()
            }
        }
        
        if self.postgresql:
            info["postgresql"] = {
                "connection_string": self.postgresql.get_connection_string()
            }
        
        return info
