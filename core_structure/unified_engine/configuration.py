"""
Unified Configuration System - Phase 1 Consolidation
===================================================

Single source of truth for all system configuration, consolidating:
- core_structure/infrastructure/config/unified_config_manager.py
- trade_engine/configuration/unified_config_manager.py

Author: Professional Trading System Architecture  
Version: 1.0 (Unified Consolidation)
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import logging
from functools import lru_cache
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ================================================================================
# UNIFIED CONFIGURATION ENUMS AND TYPES
# ================================================================================

class Environment(Enum):
    """Unified environment types"""
    DEVELOPMENT = "development"
    BACKTESTING = "backtesting" 
    PAPER_TRADING = "paper_trading"
    PRODUCTION = "production"
    TESTING = "testing"

class TradingMode(Enum):
    """Trading execution modes"""
    BACKTESTING = "backtesting"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    SIMULATION = "simulation"

# ================================================================================
# UNIFIED CONFIGURATION DATA CLASSES
# ================================================================================

@dataclass
class UnifiedStrategyConfig:
    """Unified strategy configuration combining all previous strategy configs"""
    # Basic Strategy Info
    strategy_id: str
    strategy_name: str
    strategy_type: str
    version: str = "1.0.0"
    enabled: bool = True
    
    # Strategy Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    signal_params: Dict[str, Any] = field(default_factory=dict)
    
    # Risk Configuration
    risk_params: Dict[str, Any] = field(default_factory=lambda: {
        'max_position_size': 0.1,
        'stop_loss_threshold': 0.05,
        'confidence_threshold': 0.6
    })
    
    # Execution Configuration  
    execution_params: Dict[str, Any] = field(default_factory=lambda: {
        'position_sizing_method': 'fixed',
        'execution_algorithm': 'TWAP'
    })
    
    # Metadata
    symbols: List[str] = field(default_factory=list)
    timeframes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedStrategyConfig':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class UnifiedRiskConfig:
    """Unified risk management configuration"""
    # Portfolio Risk Limits
    max_portfolio_risk: float = 0.02
    max_position_size: float = 0.1
    max_drawdown: float = 0.15
    target_volatility: float = 0.15
    
    # Position Risk Limits
    stop_loss_percentage: float = 0.05
    take_profit_percentage: float = 0.15
    max_daily_loss: float = 0.02
    correlation_threshold: float = 0.95
    
    # Risk Calculation Methods
    position_sizing_method: str = "fixed"
    risk_budget_per_trade: float = 0.01
    var_confidence_level: float = 0.95
    
    def validate(self) -> bool:
        """Validate risk configuration parameters"""
        if not 0.0 < self.max_position_size <= 1.0:
            raise ValueError("max_position_size must be between 0.0 and 1.0")
        if self.stop_loss_percentage <= 0.0:
            raise ValueError("stop_loss_percentage must be positive")
        if self.risk_budget_per_trade <= 0.0:
            raise ValueError("risk_budget_per_trade must be positive")
        return True

@dataclass
class UnifiedExecutionConfig:
    """Unified execution configuration"""
    # Commission and Costs
    commission_rate: float = 0.0005
    commission_per_share: float = 0.001
    slippage_bps: float = 2.0
    market_impact_factor: float = 0.1
    
    # Execution Settings
    execution_delay_ms: float = 100.0
    order_timeout_seconds: float = 30.0
    fill_probability: float = 0.95
    default_execution_algorithm: str = "TWAP"
    
    # Order Management
    max_order_value: float = 1_000_000
    min_order_size: float = 1.0
    batch_size: int = 50
    
    def validate(self) -> bool:
        """Validate execution configuration"""
        if self.commission_rate < 0.0:
            raise ValueError("commission_rate must be non-negative")
        if not 0.0 < self.fill_probability <= 1.0:
            raise ValueError("fill_probability must be between 0.0 and 1.0")
        return True

@dataclass
class UnifiedDatabaseConfig:
    """Unified database configuration"""
    # ClickHouse Configuration
    host: str = "localhost"
    port: int = 9000
    database: str = "polygon_data"
    user: str = "default"
    password: str = ""
    
    # Connection Pool Settings
    pool_size: int = 5
    max_connections: int = 10
    connection_timeout: int = 30
    
    # Performance Settings
    max_execution_time: int = 300
    slow_query_threshold_ms: int = 1000
    enable_query_cache: bool = True
    cache_size_mb: int = 512
    
    def get_connection_string(self) -> str:
        """Get database connection string"""
        return f"clickhouse://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass
class UnifiedSystemConfig:
    """Unified system configuration"""
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_detailed_logging: bool = False
    log_file_rotation_mb: int = 100
    log_backup_count: int = 5
    
    # Performance Settings
    max_memory_usage_mb: int = 2048
    enable_performance_tracking: bool = True
    data_cache_size: int = 10000
    
    # Engine Settings
    max_concurrent_strategies: int = 10
    max_processing_time_ms: int = 1000
    enable_monitoring: bool = True
    
    def validate(self) -> bool:
        """Validate system configuration"""
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_log_levels:
            raise ValueError(f"log_level must be one of {valid_log_levels}")
        if self.max_memory_usage_mb <= 0:
            raise ValueError("max_memory_usage_mb must be positive")
        return True

@dataclass
class UnifiedTradingConfig:
    """Unified trading configuration"""
    # Trading Period
    start_date: str
    end_date: str
    trading_mode: TradingMode = TradingMode.PAPER_TRADING
    
    # Capital Management
    initial_capital: float = 10_000_000
    currency: str = "USD"
    
    # Market Data
    data_frequency: str = "1min"
    market_sessions: List[str] = field(default_factory=lambda: ["regular"])
    
    # Real-time Settings
    real_time: bool = False
    live_data_feed: str = "polygon"
    
    def validate(self) -> bool:
        """Validate trading configuration"""
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        return True

# ================================================================================
# UNIFIED CONFIGURATION CONTAINER
# ================================================================================

@dataclass
class UnifiedConfig:
    """
    Master configuration container combining all configuration domains.
    Single source of truth for the entire trading system.
    """
    # Environment and Trading
    environment: Environment
    trading: UnifiedTradingConfig
    
    # Core System Components
    system: UnifiedSystemConfig = field(default_factory=UnifiedSystemConfig)
    database: UnifiedDatabaseConfig = field(default_factory=UnifiedDatabaseConfig)
    risk: UnifiedRiskConfig = field(default_factory=UnifiedRiskConfig)
    execution: UnifiedExecutionConfig = field(default_factory=UnifiedExecutionConfig)
    
    # Strategy Management
    strategies: Dict[str, UnifiedStrategyConfig] = field(default_factory=dict)
    
    # Feature Flags and Extensions
    features: Dict[str, bool] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    messaging: Dict[str, Any] = field(default_factory=dict)
    ai: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    
    def validate_all(self) -> bool:
        """Validate all configuration sections"""
        try:
            self.system.validate()
            self.risk.validate()
            self.execution.validate()
            self.trading.validate()
            
            # Validate all strategies
            for strategy_id, strategy_config in self.strategies.items():
                if not strategy_config.strategy_id:
                    raise ValueError(f"Strategy {strategy_id} missing strategy_id")
            
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'environment': self.environment.value,
            'trading': asdict(self.trading),
            'system': asdict(self.system),
            'database': asdict(self.database),
            'risk': asdict(self.risk),
            'execution': asdict(self.execution),
            'strategies': {k: v.to_dict() for k, v in self.strategies.items()},
            'features': self.features,
            'monitoring': self.monitoring,
            'messaging': self.messaging,
            'ai': self.ai,
            'created_at': self.created_at.isoformat(),
            'version': self.version
        }
    
    def save_to_file(self, filepath: str) -> None:
        """Save configuration to YAML file"""
        config_dict = self.to_dict()
        with open(filepath, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
        logger.info(f"Configuration saved to {filepath}")
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'UnifiedConfig':
        """Load configuration from YAML file"""
        with open(filepath, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls.from_dict(config_dict)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'UnifiedConfig':
        """Create configuration from dictionary"""
        # Parse strategies
        strategies = {}
        for strategy_id, strategy_data in config_dict.get('strategies', {}).items():
            strategies[strategy_id] = UnifiedStrategyConfig.from_dict(strategy_data)
        
        return cls(
            environment=Environment(config_dict['environment']),
            trading=UnifiedTradingConfig(**config_dict['trading']),
            system=UnifiedSystemConfig(**config_dict.get('system', {})),
            database=UnifiedDatabaseConfig(**config_dict.get('database', {})),
            risk=UnifiedRiskConfig(**config_dict.get('risk', {})),
            execution=UnifiedExecutionConfig(**config_dict.get('execution', {})),
            strategies=strategies,
            features=config_dict.get('features', {}),
            monitoring=config_dict.get('monitoring', {}),
            messaging=config_dict.get('messaging', {}),
            ai=config_dict.get('ai', {}),
            version=config_dict.get('version', '1.0.0')
        )

# ================================================================================
# UNIFIED CONFIGURATION MANAGER
# ================================================================================

class UnifiedConfigurationManager:
    """
    Professional configuration manager consolidating all previous managers.
    Single source of truth for configuration management across the system.
    """
    
    def __init__(
        self,
        config_file_path: Optional[str] = None,
        environment: str = "development",
        config_dir: Optional[str] = None
    ):
        """Initialize unified configuration manager"""
        self.logger = logging.getLogger(__name__)
        self.environment = Environment(environment)
        self.config_dir = Path(config_dir) if config_dir else Path("configs")
        self.config_file_path = config_file_path
        
        # Load environment variables
        self._load_env_vars()
        
        # Configuration cache
        self._config_cache: Optional[UnifiedConfig] = None
        self._last_load_time: Optional[datetime] = None
        
        # Load configuration
        self._load_configuration()
        
        self.logger.info(f"UnifiedConfigurationManager initialized for environment: {environment}")
    
    def _load_env_vars(self) -> None:
        """Load environment variables from .env files"""
        # Load base .env file
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
        
        # Load environment-specific .env file
        env_specific_file = Path(f".env.{self.environment.value}")
        if env_specific_file.exists():
            load_dotenv(env_specific_file, override=True)
    
    def _load_configuration(self) -> None:
        """Load configuration from files"""
        try:
            if self.config_file_path and Path(self.config_file_path).exists():
                # Load from specific file
                self._config_cache = UnifiedConfig.load_from_file(self.config_file_path)
            else:
                # Load from default configuration hierarchy
                self._config_cache = self._load_default_configuration()
            
            # Validate configuration
            self._config_cache.validate_all()
            self._last_load_time = datetime.now()
            
            self.logger.info("Configuration loaded and validated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_default_configuration(self) -> UnifiedConfig:
        """Load default configuration for the environment"""
        # Create default trading config
        trading_config = UnifiedTradingConfig(
            start_date="2024-01-01",
            end_date="2024-12-31",
            trading_mode=TradingMode.PAPER_TRADING if self.environment != Environment.PRODUCTION else TradingMode.LIVE_TRADING
        )
        
        # Create base configuration
        config = UnifiedConfig(
            environment=self.environment,
            trading=trading_config
        )
        
        # Apply environment-specific overrides
        if self.environment == Environment.PRODUCTION:
            config.system.log_level = "WARNING"
            config.execution.commission_rate = 0.005  # Higher commission in production
        elif self.environment == Environment.DEVELOPMENT:
            config.system.log_level = "DEBUG"
            config.system.enable_detailed_logging = True
        
        return config
    
    def get_config(self) -> UnifiedConfig:
        """Get current unified configuration"""
        if self._config_cache is None:
            raise RuntimeError("Configuration not loaded")
        return self._config_cache
    
    def get_strategy_config(self, strategy_id: str) -> Optional[UnifiedStrategyConfig]:
        """Get configuration for specific strategy"""
        config = self.get_config()
        return config.strategies.get(strategy_id)
    
    def add_strategy_config(self, strategy_config: UnifiedStrategyConfig) -> None:
        """Add or update strategy configuration"""
        config = self.get_config()
        config.strategies[strategy_config.strategy_id] = strategy_config
        self.logger.info(f"Added strategy configuration: {strategy_config.strategy_id}")
    
    def get_database_config(self) -> UnifiedDatabaseConfig:
        """Get database configuration with environment variable overrides"""
        config = self.get_config()
        db_config = config.database
        
        # Override with environment variables if present
        if os.getenv('DB_HOST'):
            db_config.host = os.getenv('DB_HOST')
        if os.getenv('DB_PORT'):
            db_config.port = int(os.getenv('DB_PORT'))
        if os.getenv('DB_NAME'):
            db_config.database = os.getenv('DB_NAME')
        if os.getenv('DB_USER'):
            db_config.user = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            db_config.password = os.getenv('DB_PASSWORD')
        
        return db_config
    
    def reload_configuration(self) -> None:
        """Reload configuration from files"""
        self._load_configuration()
        self.logger.info("Configuration reloaded")
    
    def save_configuration(self, filepath: Optional[str] = None) -> None:
        """Save current configuration to file"""
        config = self.get_config()
        save_path = filepath or self.config_file_path or f"unified_config_{self.environment.value}.yaml"
        config.save_to_file(save_path)
    
    def create_backtesting_config(
        self,
        strategy_configs: List[UnifiedStrategyConfig],
        start_date: str,
        end_date: str
    ) -> UnifiedConfig:
        """Create configuration optimized for backtesting"""
        trading_config = UnifiedTradingConfig(
            start_date=start_date,
            end_date=end_date,
            trading_mode=TradingMode.BACKTESTING,
            real_time=False
        )
        
        config = UnifiedConfig(
            environment=Environment.BACKTESTING,
            trading=trading_config
        )
        
        # Add strategies
        for strategy_config in strategy_configs:
            config.strategies[strategy_config.strategy_id] = strategy_config
        
        return config
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get configuration performance summary"""
        config = self.get_config()
        return {
            'environment': config.environment.value,
            'strategies_count': len(config.strategies),
            'last_load_time': self._last_load_time.isoformat() if self._last_load_time else None,
            'config_version': config.version,
            'trading_mode': config.trading.trading_mode.value,
            'initial_capital': config.trading.initial_capital,
            'max_strategies': config.system.max_concurrent_strategies
        }

    def _create_default_trading_config(self, trading_mode: TradingMode) -> Dict[str, Any]:
        """Create default trading configuration for specified mode"""
        return {
            "mode": trading_mode,
            "start_date": "2024-01-01", 
            "end_date": "2024-12-31",
            "initial_capital": 1000000.0,
            "commission_rate": 0.001,
            "slippage_rate": 0.0001
        }

# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_unified_config_manager(
    environment: str = "development",
    config_file: Optional[str] = None
) -> UnifiedConfigurationManager:
    """Factory function to create unified configuration manager"""
    return UnifiedConfigurationManager(
        config_file_path=config_file,
        environment=environment
    )

def create_default_strategy_config(
    strategy_id: str,
    strategy_name: str,
    strategy_type: str,
    parameters: Optional[Dict[str, Any]] = None
) -> UnifiedStrategyConfig:
    """Factory function to create default strategy configuration"""
    return UnifiedStrategyConfig(
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        strategy_type=strategy_type,
        parameters=parameters or {},
        signal_params=parameters or {}
    )
