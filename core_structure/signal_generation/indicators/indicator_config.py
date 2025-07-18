"""
Configuration Management for Technical Indicators
================================================

Centralized configuration for technical indicators, streaming,
and database connections. Preserves our production settings
while integrating with new_structure config system.

Author: Pro Trading System
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import os
import json

class IndicatorProfile(Enum):
    """Predefined indicator calculation profiles"""
    FAST = "fast"          # Quick calculations, fewer indicators
    STANDARD = "standard"   # Balanced performance and coverage
    COMPREHENSIVE = "comprehensive"  # All 105+ indicators
    CUSTOM = "custom"      # User-defined configuration

@dataclass
class IndicatorSettings:
    """Core indicator calculation settings"""
    
    # Calculation profile
    profile: IndicatorProfile = IndicatorProfile.STANDARD
    
    # Moving average periods
    sma_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 50, 100, 200])
    ema_periods: List[int] = field(default_factory=lambda: [12, 26, 50])
    
    # Momentum indicators
    rsi_periods: List[int] = field(default_factory=lambda: [7, 14, 21])
    stochastic_k_period: int = 14
    stochastic_d_period: int = 3
    williams_r_period: int = 14
    
    # Volatility indicators
    bollinger_period: int = 20
    bollinger_std: float = 2.0
    atr_periods: List[int] = field(default_factory=lambda: [7, 14, 21])
    
    # Trend indicators
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    adx_period: int = 14
    
    # Volume indicators
    volume_ma_periods: List[int] = field(default_factory=lambda: [10, 20, 50])
    
    # Custom thresholds
    overbought_rsi: float = 70.0
    oversold_rsi: float = 30.0
    strong_trend_adx: float = 25.0
    high_volatility_threshold: float = 0.03
    low_volatility_threshold: float = 0.01
    
    # Performance settings
    enable_parallel_calculation: bool = True
    max_workers: int = 4
    enable_caching: bool = True
    cache_ttl_seconds: int = 300

@dataclass
class StreamingSettings:
    """Real-time streaming configuration"""
    
    # Polygon API settings
    polygon_api_key: str = ""
    websocket_url: str = "wss://socket.polygon.io/stocks"
    
    # Connection settings
    max_reconnect_attempts: int = 5
    reconnect_delay_seconds: int = 5
    heartbeat_interval_seconds: int = 30
    connection_timeout_seconds: int = 30
    
    # SSL settings (our fixes)
    enable_ssl_verification: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    
    # Data buffering
    buffer_size: int = 1000
    min_data_points_for_indicators: int = 50
    max_data_points_in_memory: int = 5000
    
    # Subscription settings
    auto_subscribe_on_connect: bool = True
    subscription_batch_size: int = 10
    subscription_delay_ms: int = 100
    
    # Performance settings
    enable_compression: bool = True
    message_queue_size: int = 10000
    enable_message_filtering: bool = True
    
    # Callback settings
    max_callback_workers: int = 2
    callback_timeout_seconds: int = 5

@dataclass
class DatabaseSettings:
    """Database configuration for indicators"""
    
    # ClickHouse settings
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_database: str = "trading"
    clickhouse_username: str = "default"
    clickhouse_password: str = ""
    
    # Connection pool settings
    max_connections: int = 10
    connection_timeout: int = 10
    query_timeout: int = 30
    
    # Data management
    enable_data_compression: bool = True
    batch_insert_size: int = 1000
    auto_create_tables: bool = True
    
    # Retention policies
    historical_data_retention_days: int = 1095  # 3 years
    indicator_data_retention_days: int = 365    # 1 year
    real_time_data_retention_hours: int = 24    # 24 hours
    
    # Performance settings
    enable_parallel_queries: bool = True
    max_query_workers: int = 4
    enable_query_caching: bool = True
    cache_size_mb: int = 512

@dataclass
class PerformanceSettings:
    """Performance optimization settings"""
    
    # Memory management
    max_memory_usage_mb: int = 2048
    garbage_collection_threshold: int = 1000
    enable_memory_monitoring: bool = True
    
    # CPU usage
    max_cpu_usage_percent: float = 80.0
    enable_cpu_monitoring: bool = True
    
    # Logging and monitoring
    enable_performance_logging: bool = True
    log_slow_calculations: bool = True
    slow_calculation_threshold_ms: int = 1000
    
    # Alerting
    enable_performance_alerts: bool = True
    memory_alert_threshold_mb: int = 1500
    cpu_alert_threshold_percent: float = 90.0

class IndicatorConfigManager:
    """
    Central configuration manager for technical indicators
    Integrates with new_structure config system while preserving our settings
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager"""
        self.config_file = config_file or "indicator_config.json"
        
        # Load configuration
        self.indicator_settings = IndicatorSettings()
        self.streaming_settings = StreamingSettings()
        self.database_settings = DatabaseSettings()
        self.performance_settings = PerformanceSettings()
        
        # Load from file if exists
        self.load_configuration()
        
        # Override with environment variables
        self.load_from_environment()
    
    def load_configuration(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Update settings from file
                if 'indicators' in config_data:
                    self._update_dataclass(self.indicator_settings, config_data['indicators'])
                
                if 'streaming' in config_data:
                    self._update_dataclass(self.streaming_settings, config_data['streaming'])
                
                if 'database' in config_data:
                    self._update_dataclass(self.database_settings, config_data['database'])
                
                if 'performance' in config_data:
                    self._update_dataclass(self.performance_settings, config_data['performance'])
                    
        except Exception as e:
            print(f"Warning: Could not load configuration file: {e}")
    
    def load_from_environment(self):
        """Load configuration from environment variables"""
        # Polygon API Key
        api_key = os.getenv('POLYGON_API_KEY')
        if api_key:
            self.streaming_settings.polygon_api_key = api_key
        
        # ClickHouse settings
        ch_host = os.getenv('CLICKHOUSE_HOST')
        if ch_host:
            self.database_settings.clickhouse_host = ch_host
        
        ch_port = os.getenv('CLICKHOUSE_PORT')
        if ch_port:
            self.database_settings.clickhouse_port = int(ch_port)
        
        ch_database = os.getenv('CLICKHOUSE_DATABASE')
        if ch_database:
            self.database_settings.clickhouse_database = ch_database
        
        # SSL verification
        ssl_verify = os.getenv('ENABLE_SSL_VERIFICATION')
        if ssl_verify:
            self.streaming_settings.enable_ssl_verification = ssl_verify.lower() == 'true'
    
    def save_configuration(self):
        """Save current configuration to file"""
        try:
            config_data = {
                'indicators': self._dataclass_to_dict(self.indicator_settings),
                'streaming': self._dataclass_to_dict(self.streaming_settings),
                'database': self._dataclass_to_dict(self.database_settings),
                'performance': self._dataclass_to_dict(self.performance_settings)
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def get_profile_settings(self, profile: IndicatorProfile) -> IndicatorSettings:
        """Get settings for specific indicator profile"""
        settings = IndicatorSettings()
        
        if profile == IndicatorProfile.FAST:
            # Minimal indicators for speed
            settings.sma_periods = [20, 50]
            settings.ema_periods = [12, 26]
            settings.rsi_periods = [14]
            settings.atr_periods = [14]
            settings.volume_ma_periods = [20]
            settings.enable_parallel_calculation = True
            settings.max_workers = 2
            
        elif profile == IndicatorProfile.STANDARD:
            # Balanced configuration (default)
            pass
            
        elif profile == IndicatorProfile.COMPREHENSIVE:
            # All indicators
            settings.sma_periods = [5, 10, 15, 20, 30, 50, 100, 200]
            settings.ema_periods = [8, 12, 20, 26, 50, 100]
            settings.rsi_periods = [7, 14, 21, 30]
            settings.atr_periods = [7, 14, 21, 30]
            settings.volume_ma_periods = [5, 10, 20, 50, 100]
            settings.enable_parallel_calculation = True
            settings.max_workers = 8
        
        return settings
    
    def validate_configuration(self) -> List[str]:
        """Validate current configuration and return list of issues"""
        issues = []
        
        # Check required fields
        if not self.streaming_settings.polygon_api_key:
            issues.append("Polygon API key is required for streaming")
        
        # Check database connectivity
        if not self.database_settings.clickhouse_host:
            issues.append("ClickHouse host is required")
        
        # Check performance settings
        if self.performance_settings.max_memory_usage_mb < 512:
            issues.append("Memory allocation too low, minimum 512MB recommended")
        
        # Check streaming settings
        if self.streaming_settings.buffer_size < 100:
            issues.append("Buffer size too small, minimum 100 recommended")
        
        return issues
    
    def get_production_config(self) -> Dict[str, Any]:
        """Get production-ready configuration"""
        return {
            'indicators': self.get_profile_settings(IndicatorProfile.STANDARD),
            'streaming': StreamingSettings(
                polygon_api_key=self.streaming_settings.polygon_api_key,
                enable_ssl_verification=True,  # Enable for production
                buffer_size=2000,
                max_reconnect_attempts=10,
                enable_compression=True
            ),
            'database': DatabaseSettings(
                clickhouse_host=self.database_settings.clickhouse_host,
                max_connections=20,
                enable_data_compression=True,
                enable_parallel_queries=True
            ),
            'performance': PerformanceSettings(
                max_memory_usage_mb=4096,
                enable_performance_logging=True,
                enable_performance_alerts=True
            )
        }
    
    def _update_dataclass(self, dataclass_instance, data_dict):
        """Update dataclass instance with dictionary data"""
        for key, value in data_dict.items():
            if hasattr(dataclass_instance, key):
                # Handle enum values
                field_type = type(getattr(dataclass_instance, key))
                if hasattr(field_type, '__members__'):  # It's an enum
                    if isinstance(value, str):
                        setattr(dataclass_instance, key, field_type(value))
                    else:
                        setattr(dataclass_instance, key, value)
                else:
                    setattr(dataclass_instance, key, value)
    
    def _dataclass_to_dict(self, dataclass_instance) -> Dict:
        """Convert dataclass to dictionary"""
        result = {}
        for field_name in dataclass_instance.__dataclass_fields__:
            value = getattr(dataclass_instance, field_name)
            
            # Handle enum values
            if hasattr(value, 'value'):
                result[field_name] = value.value
            else:
                result[field_name] = value
        
        return result

# Global configuration instance
config_manager = IndicatorConfigManager()

# Export commonly used configurations
def get_default_indicator_config():
    """Get default indicator configuration"""
    from technical_indicators import IndicatorConfig
    
    return IndicatorConfig(
        clickhouse_host=config_manager.database_settings.clickhouse_host,
        clickhouse_port=config_manager.database_settings.clickhouse_port,
        clickhouse_database=config_manager.database_settings.clickhouse_database,
        polygon_api_key=config_manager.streaming_settings.polygon_api_key,
        enable_caching=config_manager.performance_settings.enable_performance_logging
    )

def get_streaming_config():
    """Get streaming configuration"""
    from polygon_streaming import StreamingConfig
    
    return StreamingConfig(
        polygon_api_key=config_manager.streaming_settings.polygon_api_key,
        websocket_url=config_manager.streaming_settings.websocket_url,
        max_reconnect_attempts=config_manager.streaming_settings.max_reconnect_attempts,
        reconnect_delay=config_manager.streaming_settings.reconnect_delay_seconds,
        enable_ssl_verification=config_manager.streaming_settings.enable_ssl_verification,
        buffer_size=config_manager.streaming_settings.buffer_size,
        min_data_points=config_manager.streaming_settings.min_data_points_for_indicators
    )
