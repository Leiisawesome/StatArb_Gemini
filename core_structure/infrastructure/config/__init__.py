"""
Consolidated Configuration System for StatArb Trading System
===========================================================

Phase 5A Infrastructure Consolidation - Config Module
Consolidates 9 config files → 3 unified domain modules

Architecture:
- core_config.py: Base framework + environment + validation (900 lines)
- business_config.py: Trading + risk + AI business logic (1000 lines)  
- infrastructure_config.py: Database + logging + monitoring (850 lines)

Total reduction: 9 files → 3 files (67% reduction)
"""

# Core configuration framework
from .core_config import (
    BaseConfig, 
    Environment, 
    LogLevel,
    SystemConfig,
    CoreConfigFactory,
    SecureConfigManager,
    ConfigValidator,
    ValidationError,
    get_api_key,
    get_database_config,
    get_feeds_config,
    load_env_file
)

# Business domain configurations
from .business_config import (
    # Trading configurations
    MarketConfig,
    ExecutionConfig, 
    StrategyConfig,
    PortfolioConfig,
    
    # Risk configurations
    PositionRiskConfig,
    PortfolioRiskConfig,
    MarketRiskConfig,
    
    # AI/ML configurations
    ModelConfig,
    LLMConfig,
    MLPipelineConfig,
    AIAgentConfig,
    
    # Consolidated business config
    BusinessConfig,
    BusinessConfigFactory
)

# Infrastructure configurations
from .infrastructure_config import (
    # Database configurations
    ClickHouseConfig,
    RedisConfig,
    PostgreSQLConfig,
    
    # System configurations
    LoggingConfig,
    MonitoringConfig,
    MessageQueueConfig,
    
    # Consolidated infrastructure config
    InfrastructureConfig,
    InfrastructureConfigManager,
    InfrastructureConfigFactory
)

# Legacy compatibility and unified management
from .unified_config_manager import (
    UnifiedConfigManager,
    UnifiedConfig,
    ConfigSystemFactory
)

# Backward compatibility aliases
RiskConfig = PortfolioRiskConfig

__all__ = [
    # ================================
    # CORE CONFIGURATION FRAMEWORK
    # ================================
    "BaseConfig",
    "Environment", 
    "LogLevel",
    "SystemConfig",
    "CoreConfigFactory",
    "SecureConfigManager",
    "ConfigValidator",
    "ValidationError",
    "get_api_key",
    "get_database_config", 
    "get_feeds_config",
    "load_env_file",
    
    # ================================
    # BUSINESS DOMAIN CONFIGURATIONS
    # ================================
    
    # Trading configurations
    "MarketConfig",
    "ExecutionConfig", 
    "StrategyConfig",
    "PortfolioConfig",
    
    # Risk configurations
    "PositionRiskConfig",
    "PortfolioRiskConfig",
    "MarketRiskConfig",
    
    # AI/ML configurations
    "ModelConfig",
    "LLMConfig",
    "MLPipelineConfig",
    "AIAgentConfig",
    
    # Consolidated business config
    "BusinessConfig",
    "BusinessConfigFactory",
    
    # ================================
    # INFRASTRUCTURE CONFIGURATIONS
    # ================================
    
    # Database configurations
    "ClickHouseConfig",
    "RedisConfig",
    "PostgreSQLConfig",
    
    # System configurations
    "LoggingConfig",
    "MonitoringConfig", 
    "MessageQueueConfig",
    
    # Consolidated infrastructure config
    "InfrastructureConfig",
    "InfrastructureConfigManager",
    "InfrastructureConfigFactory",
    
    # ================================
    # LEGACY COMPATIBILITY
    # ================================
    "UnifiedConfigManager",
    "UnifiedConfig",
    "ConfigSystemFactory",
    "LegacyStrategyConfig",
    "TrainingConfig",
    "TradingConfig",
    "DatabaseConfig",
    "LegacyLoggingConfig",
    "RiskConfig"  # Alias for PortfolioRiskConfig
] 