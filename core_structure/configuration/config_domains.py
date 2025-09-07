#!/usr/bin/env python3
"""
Configuration Domains - Domain-Specific Configuration Classes
============================================================

Professional domain-specific configuration classes for the unified configuration system.
Consolidates all scattered configuration logic into organized, validated domains.

DOMAINS COVERED:
- Trading Configuration (strategies, execution, portfolio)
- Risk Management Configuration (position, portfolio, market risk)
- System Infrastructure Configuration (logging, monitoring, performance)
- Database Configuration (ClickHouse, Redis, PostgreSQL)
- AI/ML Configuration (models, LLM, pipelines)
- Market Data Configuration (feeds, sources, caching)

Author: Professional Trading System Architecture
Version: 3.0.0 (Domain Consolidation)
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from pathlib import Path
from decimal import Decimal
import logging

from .unified_config import BaseConfig, Environment, TradingMode, LogLevel, ConfigValidator, ValidationResult

logger = logging.getLogger(__name__)

# ================================================================================
# TRADING DOMAIN CONFIGURATION
# ================================================================================

@dataclass
class StrategyConfig(BaseConfig):
    """Individual strategy configuration"""
    strategy_id: str = ""
    strategy_type: str = ""
    enabled: bool = True
    
    # Strategy Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Risk Parameters
    max_position_size: float = 100000.0
    max_daily_loss: float = 5000.0
    stop_loss_percentage: float = 2.0
    take_profit_percentage: float = 4.0
    
    # Execution Parameters
    execution_mode: str = "market"
    slippage_tolerance: float = 0.001
    max_order_size: float = 10000.0
    
    # Timing Parameters
    entry_delay_seconds: int = 0
    exit_delay_seconds: int = 0
    rebalance_frequency: str = "daily"
    
    def validate(self) -> bool:
        """Validate strategy configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_required_string(self.strategy_id, "strategy_id", result)
        ConfigValidator.validate_required_string(self.strategy_type, "strategy_type", result)
        ConfigValidator.validate_positive_number(self.max_position_size, "max_position_size", result)
        ConfigValidator.validate_positive_number(self.max_daily_loss, "max_daily_loss", result)
        ConfigValidator.validate_percentage(self.stop_loss_percentage, "stop_loss_percentage", result)
        ConfigValidator.validate_percentage(self.take_profit_percentage, "take_profit_percentage", result)
        
        if not result.is_valid:
            raise ValueError(f"Strategy configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class ExecutionConfig(BaseConfig):
    """Order execution configuration"""
    # Execution Settings
    default_order_type: str = "market"
    enable_smart_routing: bool = True
    max_slippage_bps: int = 10
    
    # Timing Settings
    market_open_delay_seconds: int = 30
    market_close_buffer_seconds: int = 300
    order_timeout_seconds: int = 30
    
    # Risk Controls
    enable_pre_trade_risk_check: bool = True
    enable_position_limits: bool = True
    enable_concentration_limits: bool = True
    
    # Performance Settings
    batch_order_size: int = 100
    concurrent_orders_limit: int = 50
    
    def validate(self) -> bool:
        """Validate execution configuration"""
        result = ValidationResult(is_valid=True)
        
        valid_order_types = ["market", "limit", "stop", "stop_limit"]
        if self.default_order_type not in valid_order_types:
            result.add_error(f"default_order_type must be one of {valid_order_types}")
        
        ConfigValidator.validate_positive_number(self.max_slippage_bps, "max_slippage_bps", result)
        ConfigValidator.validate_positive_number(self.order_timeout_seconds, "order_timeout_seconds", result)
        ConfigValidator.validate_positive_number(self.batch_order_size, "batch_order_size", result)
        ConfigValidator.validate_positive_number(self.concurrent_orders_limit, "concurrent_orders_limit", result)
        
        if not result.is_valid:
            raise ValueError(f"Execution configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class PortfolioConfig(BaseConfig):
    """Portfolio management configuration"""
    # Capital Settings
    initial_capital: float = 1000000.0
    max_capital_utilization: float = 0.95
    cash_reserve_percentage: float = 0.05
    
    # Position Settings
    max_positions: int = 50
    max_position_concentration: float = 0.10
    max_sector_concentration: float = 0.25
    
    # Rebalancing Settings
    rebalance_frequency: str = "daily"
    rebalance_threshold: float = 0.05
    enable_auto_rebalancing: bool = True
    
    # Performance Settings
    benchmark_symbol: str = "SPY"
    performance_calculation_frequency: str = "daily"
    
    def validate(self) -> bool:
        """Validate portfolio configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_positive_number(self.initial_capital, "initial_capital", result)
        ConfigValidator.validate_ratio(self.max_capital_utilization, "max_capital_utilization", result)
        ConfigValidator.validate_ratio(self.cash_reserve_percentage, "cash_reserve_percentage", result)
        ConfigValidator.validate_positive_number(self.max_positions, "max_positions", result)
        ConfigValidator.validate_ratio(self.max_position_concentration, "max_position_concentration", result)
        ConfigValidator.validate_ratio(self.max_sector_concentration, "max_sector_concentration", result)
        
        if self.max_capital_utilization + self.cash_reserve_percentage > 1.0:
            result.add_error("max_capital_utilization + cash_reserve_percentage cannot exceed 1.0")
        
        if not result.is_valid:
            raise ValueError(f"Portfolio configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class TradingConfig(BaseConfig):
    """Master trading configuration combining all trading-related settings"""
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    
    # Trading Session Settings
    market_hours_start: str = "09:30"
    market_hours_end: str = "16:00"
    timezone: str = "America/New_York"
    
    # Trading Controls
    enable_trading: bool = True
    enable_short_selling: bool = True
    enable_options_trading: bool = False
    enable_futures_trading: bool = False
    
    # Market Data Settings
    data_frequency: str = "1min"
    lookback_periods: int = 252
    
    def validate(self) -> bool:
        """Validate trading configuration"""
        result = ValidationResult(is_valid=True)
        
        # Validate sub-configurations
        try:
            self.execution.validate()
            self.portfolio.validate()
        except ValueError as e:
            result.add_error(str(e))
        
        # Validate time format
        try:
            from datetime import datetime
            datetime.strptime(self.market_hours_start, "%H:%M")
            datetime.strptime(self.market_hours_end, "%H:%M")
        except ValueError:
            result.add_error("market_hours_start and market_hours_end must be in HH:MM format")
        
        ConfigValidator.validate_positive_number(self.lookback_periods, "lookback_periods", result)
        
        if not result.is_valid:
            raise ValueError(f"Trading configuration validation failed: {'; '.join(result.errors)}")
        
        return True

# ================================================================================
# RISK MANAGEMENT DOMAIN CONFIGURATION
# ================================================================================

@dataclass
class PositionRiskConfig(BaseConfig):
    """Individual position risk configuration"""
    max_position_value: float = 100000.0
    max_position_percentage: float = 0.05
    stop_loss_percentage: float = 0.02
    take_profit_percentage: float = 0.04
    
    # Dynamic Risk Controls
    volatility_adjustment: bool = True
    correlation_adjustment: bool = True
    
    def validate(self) -> bool:
        """Validate position risk configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_positive_number(self.max_position_value, "max_position_value", result)
        ConfigValidator.validate_ratio(self.max_position_percentage, "max_position_percentage", result)
        ConfigValidator.validate_ratio(self.stop_loss_percentage, "stop_loss_percentage", result)
        ConfigValidator.validate_ratio(self.take_profit_percentage, "take_profit_percentage", result)
        
        if not result.is_valid:
            raise ValueError(f"Position risk configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class PortfolioRiskConfig(BaseConfig):
    """Portfolio-level risk configuration"""
    max_portfolio_var: float = 0.02
    max_drawdown_percentage: float = 0.10
    max_leverage: float = 1.0
    
    # Concentration Limits
    max_single_position: float = 0.10
    max_sector_exposure: float = 0.25
    max_country_exposure: float = 0.50
    
    # Risk Monitoring
    var_confidence_level: float = 0.95
    var_calculation_window: int = 252
    stress_test_scenarios: List[str] = field(default_factory=lambda: ["market_crash", "sector_rotation"])
    
    def validate(self) -> bool:
        """Validate portfolio risk configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_ratio(self.max_portfolio_var, "max_portfolio_var", result)
        ConfigValidator.validate_ratio(self.max_drawdown_percentage, "max_drawdown_percentage", result)
        ConfigValidator.validate_positive_number(self.max_leverage, "max_leverage", result)
        ConfigValidator.validate_ratio(self.max_single_position, "max_single_position", result)
        ConfigValidator.validate_ratio(self.max_sector_exposure, "max_sector_exposure", result)
        ConfigValidator.validate_ratio(self.max_country_exposure, "max_country_exposure", result)
        ConfigValidator.validate_ratio(self.var_confidence_level, "var_confidence_level", result)
        ConfigValidator.validate_positive_number(self.var_calculation_window, "var_calculation_window", result)
        
        if not result.is_valid:
            raise ValueError(f"Portfolio risk configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class MarketRiskConfig(BaseConfig):
    """Market-wide risk configuration"""
    # Market Condition Monitoring
    volatility_threshold: float = 0.25
    correlation_threshold: float = 0.80
    liquidity_threshold: float = 0.10
    
    # Circuit Breakers
    enable_volatility_circuit_breaker: bool = True
    enable_drawdown_circuit_breaker: bool = True
    enable_correlation_circuit_breaker: bool = True
    
    # Risk Adjustments
    volatility_scaling: bool = True
    regime_detection: bool = True
    
    def validate(self) -> bool:
        """Validate market risk configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_positive_number(self.volatility_threshold, "volatility_threshold", result)
        ConfigValidator.validate_ratio(self.correlation_threshold, "correlation_threshold", result)
        ConfigValidator.validate_ratio(self.liquidity_threshold, "liquidity_threshold", result)
        
        if not result.is_valid:
            raise ValueError(f"Market risk configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class RiskConfig(BaseConfig):
    """Master risk management configuration"""
    position: PositionRiskConfig = field(default_factory=PositionRiskConfig)
    portfolio: PortfolioRiskConfig = field(default_factory=PortfolioRiskConfig)
    market: MarketRiskConfig = field(default_factory=MarketRiskConfig)
    
    # Global Risk Settings
    enable_risk_management: bool = True
    risk_calculation_frequency: str = "real_time"
    risk_reporting_frequency: str = "daily"
    
    def validate(self) -> bool:
        """Validate risk configuration"""
        result = ValidationResult(is_valid=True)
        
        # Validate sub-configurations
        try:
            self.position.validate()
            self.portfolio.validate()
            self.market.validate()
        except ValueError as e:
            result.add_error(str(e))
        
        valid_frequencies = ["real_time", "minute", "hourly", "daily"]
        if self.risk_calculation_frequency not in valid_frequencies:
            result.add_error(f"risk_calculation_frequency must be one of {valid_frequencies}")
        
        if not result.is_valid:
            raise ValueError(f"Risk configuration validation failed: {'; '.join(result.errors)}")
        
        return True

# ================================================================================
# SYSTEM INFRASTRUCTURE DOMAIN CONFIGURATION
# ================================================================================

@dataclass
class LoggingConfig(BaseConfig):
    """Logging system configuration"""
    log_level: LogLevel = LogLevel.INFO
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File Logging
    enable_file_logging: bool = True
    log_file_path: str = "logs/trading_system.log"
    max_log_file_size: int = 100 * 1024 * 1024  # 100MB
    log_file_backup_count: int = 5
    
    # Console Logging
    enable_console_logging: bool = True
    console_log_level: LogLevel = LogLevel.INFO
    
    # Structured Logging
    enable_json_logging: bool = False
    enable_performance_logging: bool = True
    
    def validate(self) -> bool:
        """Validate logging configuration"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(self.log_level, LogLevel):
            result.add_error("log_level must be a valid LogLevel enum")
        
        if not isinstance(self.console_log_level, LogLevel):
            result.add_error("console_log_level must be a valid LogLevel enum")
        
        ConfigValidator.validate_positive_number(self.max_log_file_size, "max_log_file_size", result)
        ConfigValidator.validate_positive_number(self.log_file_backup_count, "log_file_backup_count", result)
        
        if not result.is_valid:
            raise ValueError(f"Logging configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class MonitoringConfig(BaseConfig):
    """System monitoring configuration"""
    # Performance Monitoring
    enable_performance_monitoring: bool = True
    performance_collection_interval: int = 60  # seconds
    
    # Health Checks
    enable_health_checks: bool = True
    health_check_interval: int = 30  # seconds
    
    # Alerting
    enable_alerting: bool = True
    alert_channels: List[str] = field(default_factory=lambda: ["email", "slack"])
    
    # Metrics Collection
    enable_metrics_collection: bool = True
    metrics_retention_days: int = 30
    
    def validate(self) -> bool:
        """Validate monitoring configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_positive_number(self.performance_collection_interval, "performance_collection_interval", result)
        ConfigValidator.validate_positive_number(self.health_check_interval, "health_check_interval", result)
        ConfigValidator.validate_positive_number(self.metrics_retention_days, "metrics_retention_days", result)
        
        valid_channels = ["email", "slack", "discord", "sms", "webhook"]
        for channel in self.alert_channels:
            if channel not in valid_channels:
                result.add_error(f"Invalid alert channel: {channel}. Valid channels: {valid_channels}")
        
        if not result.is_valid:
            raise ValueError(f"Monitoring configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class SystemConfig(BaseConfig):
    """System infrastructure configuration"""
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # System Settings
    debug: bool = False
    enable_profiling: bool = False
    max_memory_usage_mb: int = 4096
    max_cpu_usage_percentage: int = 80
    
    # Threading and Concurrency
    max_worker_threads: int = 10
    enable_async_processing: bool = True
    
    # Caching
    enable_caching: bool = True
    cache_size_mb: int = 512
    cache_ttl_seconds: int = 3600
    
    def validate(self) -> bool:
        """Validate system configuration"""
        result = ValidationResult(is_valid=True)
        
        # Validate sub-configurations
        try:
            self.logging.validate()
            self.monitoring.validate()
        except ValueError as e:
            result.add_error(str(e))
        
        ConfigValidator.validate_positive_number(self.max_memory_usage_mb, "max_memory_usage_mb", result)
        ConfigValidator.validate_percentage(self.max_cpu_usage_percentage, "max_cpu_usage_percentage", result)
        ConfigValidator.validate_positive_number(self.max_worker_threads, "max_worker_threads", result)
        ConfigValidator.validate_positive_number(self.cache_size_mb, "cache_size_mb", result)
        ConfigValidator.validate_positive_number(self.cache_ttl_seconds, "cache_ttl_seconds", result)
        
        if not result.is_valid:
            raise ValueError(f"System configuration validation failed: {'; '.join(result.errors)}")
        
        return True

# ================================================================================
# DATABASE DOMAIN CONFIGURATION
# ================================================================================

@dataclass
class ClickHouseConfig(BaseConfig):
    """ClickHouse database configuration"""
    host: str = "localhost"
    port: int = 9000
    database: str = "trading_data"
    username: str = "default"
    password: str = ""
    
    # Connection Settings
    connection_timeout: int = 30
    max_connections: int = 10
    
    # Performance Settings
    batch_size: int = 10000
    compression: bool = True
    
    def validate(self) -> bool:
        """Validate ClickHouse configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_required_string(self.host, "host", result)
        ConfigValidator.validate_positive_number(self.port, "port", result)
        ConfigValidator.validate_required_string(self.database, "database", result)
        ConfigValidator.validate_positive_number(self.connection_timeout, "connection_timeout", result)
        ConfigValidator.validate_positive_number(self.max_connections, "max_connections", result)
        ConfigValidator.validate_positive_number(self.batch_size, "batch_size", result)
        
        if not (1 <= self.port <= 65535):
            result.add_error("port must be between 1 and 65535")
        
        if not result.is_valid:
            raise ValueError(f"ClickHouse configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class RedisConfig(BaseConfig):
    """Redis cache configuration"""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    
    # Connection Settings
    connection_timeout: int = 5
    max_connections: int = 20
    
    # Cache Settings
    default_ttl: int = 3600
    max_memory_policy: str = "allkeys-lru"
    
    def validate(self) -> bool:
        """Validate Redis configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_required_string(self.host, "host", result)
        ConfigValidator.validate_positive_number(self.port, "port", result)
        ConfigValidator.validate_non_negative_number(self.database, "database", result)
        ConfigValidator.validate_positive_number(self.connection_timeout, "connection_timeout", result)
        ConfigValidator.validate_positive_number(self.max_connections, "max_connections", result)
        ConfigValidator.validate_positive_number(self.default_ttl, "default_ttl", result)
        
        if not (1 <= self.port <= 65535):
            result.add_error("port must be between 1 and 65535")
        
        valid_policies = ["noeviction", "allkeys-lru", "volatile-lru", "allkeys-random", "volatile-random", "volatile-ttl"]
        if self.max_memory_policy not in valid_policies:
            result.add_error(f"max_memory_policy must be one of {valid_policies}")
        
        if not result.is_valid:
            raise ValueError(f"Redis configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class DatabaseConfig(BaseConfig):
    """Master database configuration"""
    clickhouse: ClickHouseConfig = field(default_factory=ClickHouseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    
    # Database Selection
    primary_database: str = "clickhouse"
    cache_database: str = "redis"
    
    # Connection Pooling
    enable_connection_pooling: bool = True
    pool_size: int = 10
    
    def validate(self) -> bool:
        """Validate database configuration"""
        result = ValidationResult(is_valid=True)
        
        # Validate sub-configurations
        try:
            self.clickhouse.validate()
            self.redis.validate()
        except ValueError as e:
            result.add_error(str(e))
        
        valid_databases = ["clickhouse", "postgresql", "sqlite"]
        if self.primary_database not in valid_databases:
            result.add_error(f"primary_database must be one of {valid_databases}")
        
        valid_caches = ["redis", "memcached", "none"]
        if self.cache_database not in valid_caches:
            result.add_error(f"cache_database must be one of {valid_caches}")
        
        ConfigValidator.validate_positive_number(self.pool_size, "pool_size", result)
        
        if not result.is_valid:
            raise ValueError(f"Database configuration validation failed: {'; '.join(result.errors)}")
        
        return True
    
    def get(self, key: str, default=None):
        """Get configuration value by key - compatibility method"""
        return getattr(self, key, default)

# ================================================================================
# AI/ML DOMAIN CONFIGURATION
# ================================================================================

@dataclass
class ModelConfig(BaseConfig):
    """ML model configuration"""
    model_name: str = ""
    model_type: str = ""
    model_path: Optional[str] = None
    
    # Training Parameters
    training_data_path: Optional[str] = None
    validation_split: float = 0.2
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    
    # Inference Parameters
    prediction_threshold: float = 0.5
    enable_model_monitoring: bool = True
    
    def validate(self) -> bool:
        """Validate model configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_required_string(self.model_name, "model_name", result)
        ConfigValidator.validate_required_string(self.model_type, "model_type", result)
        ConfigValidator.validate_ratio(self.validation_split, "validation_split", result)
        ConfigValidator.validate_positive_number(self.batch_size, "batch_size", result)
        ConfigValidator.validate_positive_number(self.epochs, "epochs", result)
        ConfigValidator.validate_positive_number(self.learning_rate, "learning_rate", result)
        ConfigValidator.validate_ratio(self.prediction_threshold, "prediction_threshold", result)
        
        if not result.is_valid:
            raise ValueError(f"Model configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class LLMConfig(BaseConfig):
    """Large Language Model configuration"""
    provider: str = "openai"
    model_name: str = "gpt-4"
    api_key: Optional[str] = None
    
    # Generation Parameters
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 0.9
    
    # Rate Limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 40000
    
    def validate(self) -> bool:
        """Validate LLM configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_required_string(self.provider, "provider", result)
        ConfigValidator.validate_required_string(self.model_name, "model_name", result)
        ConfigValidator.validate_positive_number(self.max_tokens, "max_tokens", result)
        ConfigValidator.validate_positive_number(self.temperature, "temperature", result)
        ConfigValidator.validate_ratio(self.top_p, "top_p", result)
        ConfigValidator.validate_positive_number(self.requests_per_minute, "requests_per_minute", result)
        ConfigValidator.validate_positive_number(self.tokens_per_minute, "tokens_per_minute", result)
        
        if not result.is_valid:
            raise ValueError(f"LLM configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class AIConfig(BaseConfig):
    """Master AI/ML configuration"""
    # Model Configurations
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # AI Features
    enable_ai_signals: bool = False
    enable_sentiment_analysis: bool = False
    enable_news_analysis: bool = False
    
    # Performance Settings
    gpu_enabled: bool = False
    max_concurrent_predictions: int = 10
    
    def validate(self) -> bool:
        """Validate AI configuration"""
        result = ValidationResult(is_valid=True)
        
        # Validate sub-configurations
        try:
            self.llm.validate()
            for model_name, model_config in self.models.items():
                model_config.validate()
        except ValueError as e:
            result.add_error(str(e))
        
        ConfigValidator.validate_positive_number(self.max_concurrent_predictions, "max_concurrent_predictions", result)
        
        if not result.is_valid:
            raise ValueError(f"AI configuration validation failed: {'; '.join(result.errors)}")
        
        return True

# ================================================================================
# MARKET DATA DOMAIN CONFIGURATION
# ================================================================================

@dataclass
class DataFeedConfig(BaseConfig):
    """Individual data feed configuration"""
    provider: str = ""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # Data Settings
    symbols: List[str] = field(default_factory=list)
    data_types: List[str] = field(default_factory=lambda: ["trades", "quotes"])
    frequency: str = "1min"
    
    # Connection Settings
    max_connections: int = 5
    timeout_seconds: int = 30
    retry_attempts: int = 3
    
    def validate(self) -> bool:
        """Validate data feed configuration"""
        result = ValidationResult(is_valid=True)
        
        ConfigValidator.validate_required_string(self.provider, "provider", result)
        ConfigValidator.validate_positive_number(self.max_connections, "max_connections", result)
        ConfigValidator.validate_positive_number(self.timeout_seconds, "timeout_seconds", result)
        ConfigValidator.validate_positive_number(self.retry_attempts, "retry_attempts", result)
        
        valid_frequencies = ["1sec", "1min", "5min", "15min", "1hour", "1day"]
        if self.frequency not in valid_frequencies:
            result.add_error(f"frequency must be one of {valid_frequencies}")
        
        if not result.is_valid:
            raise ValueError(f"Data feed configuration validation failed: {'; '.join(result.errors)}")
        
        return True

@dataclass
class MarketDataConfig(BaseConfig):
    """Master market data configuration"""
    # Data Feeds
    feeds: Dict[str, DataFeedConfig] = field(default_factory=dict)
    primary_feed: str = ""
    
    # Data Storage
    enable_data_storage: bool = True
    storage_format: str = "parquet"
    compression: str = "snappy"
    
    # Data Processing
    enable_real_time_processing: bool = True
    batch_processing_interval: int = 60  # seconds
    
    # Data Quality
    enable_data_validation: bool = True
    outlier_detection: bool = True
    
    def validate(self) -> bool:
        """Validate market data configuration"""
        result = ValidationResult(is_valid=True)
        
        # Validate sub-configurations
        try:
            for feed_name, feed_config in self.feeds.items():
                feed_config.validate()
        except ValueError as e:
            result.add_error(str(e))
        
        if self.primary_feed and self.primary_feed not in self.feeds and len(self.feeds) > 0:
            result.add_error(f"primary_feed '{self.primary_feed}' not found in feeds configuration")
        
        valid_formats = ["parquet", "csv", "json", "avro"]
        if self.storage_format not in valid_formats:
            result.add_error(f"storage_format must be one of {valid_formats}")
        
        valid_compression = ["none", "gzip", "snappy", "lz4", "brotli"]
        if self.compression not in valid_compression:
            result.add_error(f"compression must be one of {valid_compression}")
        
        ConfigValidator.validate_positive_number(self.batch_processing_interval, "batch_processing_interval", result)
        
        if not result.is_valid:
            raise ValueError(f"Market data configuration validation failed: {'; '.join(result.errors)}")
        
        return True

# ================================================================================
# MODULE VALIDATION
# ================================================================================

def __validate_config_domains():
    """Validate configuration domains module integrity"""
    try:
        # Test each domain configuration
        trading_config = TradingConfig()
        trading_config.validate()
        
        risk_config = RiskConfig()
        risk_config.validate()
        
        system_config = SystemConfig()
        system_config.validate()
        
        database_config = DatabaseConfig()
        database_config.validate()
        
        ai_config = AIConfig()
        ai_config.validate()
        
        market_data_config = MarketDataConfig()
        market_data_config.validate()
        
        logger.info("Configuration domains module validation passed")
        return True
    except Exception as e:
        logger.error(f"Configuration domains module validation failed: {e}")
        raise ValueError(f"Module validation failed: {e}")

# Run validation on import
__validate_config_domains()
