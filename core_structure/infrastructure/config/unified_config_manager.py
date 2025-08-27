"""
Unified Configuration Management System
======================================

Professional configuration management system consolidating all configuration functionality.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
from functools import lru_cache
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    BACKTESTING = "backtesting"
    PRODUCTION = "production"
    REAL_TIME = "real_time"
    TESTING = "testing"

@dataclass
class StrategyConfig:
    """Strategy-specific configuration"""
    name: str
    version: str = "1.0.0"
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_limits: Dict[str, float] = field(default_factory=dict)
    timeframes: List[str] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'version': self.version,
            'parameters': self.parameters,
            'risk_limits': self.risk_limits,
            'timeframes': self.timeframes,
            'symbols': self.symbols
        }

@dataclass
class TrainingConfig:
    """Training period configuration"""
    start_date: str
    end_date: str
    validation_split: float = 0.2
    parameter_optimization: bool = True
    optimization_method: str = "grid_search"
    optimization_metrics: List[str] = field(default_factory=lambda: ["sharpe_ratio", "max_drawdown"])

@dataclass
class TradingConfig:
    """Trading period configuration"""
    start_date: str
    end_date: str
    real_time: bool = False
    execution_mode: str = "simulation"
    position_sizing: str = "fixed"

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 9000
    database: str = "polygon_data"
    user: str = "default"
    password: str = ""
    pool_size: int = 5
    max_execution_time: int = 300
    slow_query_threshold_ms: int = 1000

@dataclass
class PortfolioRiskConfig:
    """Portfolio-level risk management configuration
    
    Note: For signal-level risk config, see signal_generation/risk_management.py
    For enterprise risk config, see infrastructure/config/risk_config.py
    """
    max_position_size: float = 0.1
    stop_loss_threshold: float = 0.05
    daily_var_limit: float = 0.02
    correlation_threshold: float = 0.95
    max_drawdown: float = 0.20
    target_volatility: float = 0.15

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_rotation_mb: int = 100
    backup_count: int = 5
    console: bool = True

@dataclass
class UnifiedConfig:
    """Unified configuration system"""
    environment: Environment
    strategy: StrategyConfig
    trading: TradingConfig
    training: Optional[TrainingConfig] = None
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    risk: PortfolioRiskConfig = field(default_factory=PortfolioRiskConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    data_feeds: Dict[str, Any] = field(default_factory=dict)
    execution: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    messaging: Dict[str, Any] = field(default_factory=dict)
    ai: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, bool] = field(default_factory=dict)
    market_data: Dict[str, Any] = field(default_factory=dict)
    
    def save_to_file(self, filepath: str):
        """Save configuration to file"""
        config_dict = {
            'environment': self.environment.value,
            'strategy': self.strategy.to_dict(),
            'training': self.training.__dict__ if self.training else None,
            'trading': self.trading.__dict__,
            'database': self.database.__dict__,
            'risk': self.risk.__dict__,
            'logging': self.logging.__dict__,
            'data_feeds': self.data_feeds,
            'execution': self.execution,
            'monitoring': self.monitoring,
            'messaging': self.messaging,
            'ai': self.ai,
            'features': self.features,
            'market_data': self.market_data
        }
        
        with open(filepath, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'UnifiedConfig':
        """Load configuration from file"""
        with open(filepath, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        return cls._from_dict(config_dict)
    
    @classmethod
    def _from_dict(cls, config_dict: Dict[str, Any]) -> 'UnifiedConfig':
        """Create config from dictionary"""
        return cls(
            environment=Environment(config_dict['environment']),
            strategy=StrategyConfig(**config_dict['strategy']),
            training=TrainingConfig(**config_dict['training']) if config_dict.get('training') else None,
            trading=TradingConfig(**config_dict['trading']),
            database=DatabaseConfig(**config_dict.get('database', {})),
            risk=PortfolioRiskConfig(**config_dict.get('risk', {})),
            logging=LoggingConfig(**config_dict.get('logging', {})),
            data_feeds=config_dict.get('data_feeds', {}),
            execution=config_dict.get('execution', {}),
            monitoring=config_dict.get('monitoring', {}),
            messaging=config_dict.get('messaging', {}),
            ai=config_dict.get('ai', {}),
            features=config_dict.get('features', {}),
            market_data=config_dict.get('market_data', {})
        )

class UnifiedConfigManager:
    """Unified configuration management system"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path("configs")
        self.env = os.getenv("APP_ENV", "development")
        
        # Load environment variables
        self._load_env_vars()
        
        # Load configuration files
        self._config = self._load_config()
        
        # Dynamic settings
        self._dynamic_settings = {}
        
        # Feature flags
        self._feature_flags = self._load_feature_flags()
        
        logger.info(f"Initialized UnifiedConfigManager for environment: {self.env}")
    
    def _load_env_vars(self):
        """Load environment variables from .env file"""
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
        
        # Load environment-specific .env file
        env_specific_file = Path(f".env.{self.env}")
        if env_specific_file.exists():
            load_dotenv(env_specific_file, override=True)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from files"""
        config = {}
        
        # Load base config
        base_config = self.config_dir / "base_config.yaml"
        if base_config.exists():
            with open(base_config) as f:
                config.update(yaml.safe_load(f))
        
        # Load environment-specific config
        env_config = self.config_dir / f"{self.env}_config.yaml"
        if env_config.exists():
            with open(env_config) as f:
                config.update(yaml.safe_load(f))
        
        # Load local overrides (not version controlled)
        local_config = self.config_dir / "local_config.yaml"
        if local_config.exists():
            with open(local_config) as f:
                config.update(yaml.safe_load(f))
        
        return config
    
    def _load_feature_flags(self) -> Dict[str, bool]:
        """Load feature flags configuration"""
        feature_flags_file = self.config_dir / "feature_flags.yaml"
        if not feature_flags_file.exists():
            return {}
        
        with open(feature_flags_file) as f:
            return yaml.safe_load(f)
    
    def create_backtesting_config(self, strategy_name: str, 
                                training_start: str, training_end: str,
                                validation_start: str, validation_end: str) -> UnifiedConfig:
        """Create backtesting configuration"""
        
        strategy_config = StrategyConfig(
            name=strategy_name,
            parameters=self._get_strategy_parameters(strategy_name),
            risk_limits=self._get_risk_limits(),
            symbols=self._get_default_symbols()
        )
        
        training_config = TrainingConfig(
            start_date=training_start,
            end_date=training_end
        )
        
        trading_config = TradingConfig(
            start_date=validation_start,
            end_date=validation_end,
            real_time=False,
            execution_mode="simulation"
        )
        
        return UnifiedConfig(
            environment=Environment.BACKTESTING,
            strategy=strategy_config,
            training=training_config,
            trading=trading_config,
            database=self._get_database_config(),
            risk=self._get_risk_config(),
            logging=self._get_logging_config(),
            data_feeds=self._get_backtesting_data_feeds(),
            execution=self._get_execution_config(),
            monitoring=self._get_monitoring_config(),
            messaging=self._get_messaging_config(),
            ai=self._get_ai_config(),
            features=self._get_feature_flags(),
            market_data=self._get_market_data_config()
        )
    
    def create_real_time_config(self, strategy_name: str, 
                              trading_start: str) -> UnifiedConfig:
        """Create real-time configuration"""
        
        strategy_config = StrategyConfig(
            name=strategy_name,
            parameters=self._get_strategy_parameters(strategy_name),
            risk_limits=self._get_risk_limits(),
            symbols=self._get_default_symbols()
        )
        
        trading_config = TradingConfig(
            start_date=trading_start,
            end_date="",  # Ongoing
            real_time=True,
            execution_mode="simulation"
        )
        
        return UnifiedConfig(
            environment=Environment.REAL_TIME,
            strategy=strategy_config,
            trading=trading_config,
            database=self._get_database_config(),
            risk=self._get_risk_config(),
            logging=self._get_logging_config(),
            data_feeds=self._get_real_time_data_feeds(),
            execution=self._get_execution_config(),
            monitoring=self._get_monitoring_config(),
            messaging=self._get_messaging_config(),
            ai=self._get_ai_config(),
            features=self._get_feature_flags(),
            market_data=self._get_market_data_config()
        )
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        db_config = self._config.get('database', {})
        
        # Override with environment variables if present
        if os.getenv('DB_HOST'):
            db_config['host'] = os.getenv('DB_HOST')
        if os.getenv('DB_PORT'):
            db_config['port'] = int(os.getenv('DB_PORT'))
        if os.getenv('DB_NAME'):
            db_config['database'] = os.getenv('DB_NAME')
        if os.getenv('DB_USER'):
            db_config['user'] = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            db_config['password'] = os.getenv('DB_PASSWORD')
        
        return db_config
    
    def get_strategy_settings(self, strategy_name: str) -> Dict[str, Any]:
        """Get strategy-specific settings"""
        strategies = self._config.get('strategies', {})
        return strategies.get(strategy_name, {})
    
    def get_feature_flag(self, flag_name: str) -> bool:
        """Get feature flag value"""
        return self._feature_flags.get(flag_name, False)
    
    def update_dynamic_setting(self, key: str, value: Any, persist: bool = False) -> None:
        """Update dynamic setting"""
        self._dynamic_settings[key] = value
        
        if persist:
            # Save to persistent storage
            self._save_dynamic_settings()
    
    def get_dynamic_setting(self, key: str, default: Any = None) -> Any:
        """Get dynamic setting"""
        return self._dynamic_settings.get(key, default)
    
    def reload_config(self) -> None:
        """Reload configuration from files"""
        self._config = self._load_config()
        self._feature_flags = self._load_feature_flags()
        logger.info("Configuration reloaded")
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self._config.get('monitoring', {})
    
    def get_messaging_config(self) -> Dict[str, Any]:
        """Get messaging configuration"""
        return self._config.get('messaging', {})
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration"""
        return self._config.get('ai', {})
    
    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        return self._config.copy()
    
    def _get_strategy_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """Get strategy parameters"""
        strategy_settings = self.get_strategy_settings(strategy_name)
        return strategy_settings.get('parameters', {})
    
    def _get_risk_limits(self) -> Dict[str, float]:
        """Get risk limits"""
        risk_config = self._config.get('risk_management', {})
        return {
            'max_position_size': risk_config.get('max_position_size', 0.1),
            'stop_loss_threshold': risk_config.get('stop_loss_threshold', 0.05),
            'daily_var_limit': risk_config.get('daily_var_limit', 0.02),
            'correlation_threshold': risk_config.get('correlation_threshold', 0.95)
        }
    
    def _get_default_symbols(self) -> List[str]:
        """Get default symbols"""
        return self._config.get('market_data', {}).get('default_symbols', ["SPY", "QQQ", "IWM"])
    
    def _get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        db_config = self.get_database_config()
        return DatabaseConfig(**db_config)
    
    def _get_risk_config(self) -> PortfolioRiskConfig:
        """Get risk configuration"""
        risk_config = self._config.get('risk_management', {})
        return PortfolioRiskConfig(**risk_config)
    
    def _get_logging_config(self) -> LoggingConfig:
        """Get logging configuration"""
        logging_config = self._config.get('logging', {})
        return LoggingConfig(**logging_config)
    
    def _get_backtesting_data_feeds(self) -> Dict[str, Any]:
        """Get backtesting data feeds configuration"""
        return {
            'source': 'historical',
            'symbols': self._get_default_symbols(),
            'frequency': 'daily',
            'fields': ['open', 'high', 'low', 'close', 'volume']
        }
    
    def _get_real_time_data_feeds(self) -> Dict[str, Any]:
        """Get real-time data feeds configuration"""
        return {
            'source': 'real_time',
            'symbols': self._get_default_symbols(),
            'frequency': 'minute',
            'fields': ['open', 'high', 'low', 'close', 'volume']
        }
    
    def _get_execution_config(self) -> Dict[str, Any]:
        """Get execution configuration"""
        return {
            'commission_rate': 0.0005,
            'slippage': 0.0001,
            'execution_delay_ms': 100
        }
    
    def _get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self._config.get('monitoring', {})
    
    def _get_messaging_config(self) -> Dict[str, Any]:
        """Get messaging configuration"""
        return self._config.get('messaging', {})
    
    def _get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration"""
        return self._config.get('ai', {})
    
    def _get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags"""
        return self._config.get('features', {})
    
    def _get_market_data_config(self) -> Dict[str, Any]:
        """Get market data configuration"""
        return self._config.get('market_data', {})
    
    def _save_dynamic_settings(self):
        """Save dynamic settings to persistent storage"""
        # Implementation for persistent storage
        pass
    
    def __getitem__(self, key: str) -> Any:
        """Get configuration value by key"""
        return self._config[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key with default"""
        return self._config.get(key, default) 