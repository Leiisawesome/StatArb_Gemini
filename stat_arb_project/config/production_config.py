"""
Production Configuration System
Handles environment-based configuration with validation.
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "stat_arb"
    username: str = "postgres"
    password: str = ""
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        return cls(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'stat_arb'),
            username=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '')
        )

@dataclass
class RedisConfig:
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            password=os.getenv('REDIS_PASSWORD'),
            db=int(os.getenv('REDIS_DB', '0'))
        )

@dataclass
class TradingConfig:
    """Trading configuration."""
    initial_capital: float = 1000000.0
    max_position_size: float = 0.15
    max_leverage: float = 2.0
    target_volatility: float = 0.12
    entry_threshold: float = 2.0
    exit_threshold: float = 0.5
    stop_loss: float = 0.05
    take_profit: float = 0.10
    
    @classmethod
    def from_env(cls) -> 'TradingConfig':
        return cls(
            initial_capital=float(os.getenv('INITIAL_CAPITAL', '1000000.0')),
            max_position_size=float(os.getenv('MAX_POSITION_SIZE', '0.15')),
            max_leverage=float(os.getenv('MAX_LEVERAGE', '2.0')),
            target_volatility=float(os.getenv('TARGET_VOLATILITY', '0.12')),
            entry_threshold=float(os.getenv('ENTRY_THRESHOLD', '2.0')),
            exit_threshold=float(os.getenv('EXIT_THRESHOLD', '0.5')),
            stop_loss=float(os.getenv('STOP_LOSS', '0.05')),
            take_profit=float(os.getenv('TAKE_PROFIT', '0.10'))
        )

@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    file_path: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format=os.getenv('LOG_FORMAT', 'json'),
            file_path=os.getenv('LOG_FILE_PATH')
        )

@dataclass
class ProductionConfig:
    """Main production configuration."""
    environment: str = "production"
    debug: bool = False
    database: DatabaseConfig = None
    redis: RedisConfig = None
    trading: TradingConfig = None
    logging: LoggingConfig = None
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig.from_env()
        if self.redis is None:
            self.redis = RedisConfig.from_env()
        if self.trading is None:
            self.trading = TradingConfig.from_env()
        if self.logging is None:
            self.logging = LoggingConfig.from_env()
    
    @classmethod
    def from_env(cls) -> 'ProductionConfig':
        return cls(
            environment=os.getenv('ENVIRONMENT', 'production'),
            debug=os.getenv('DEBUG', 'false').lower() == 'true'
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> 'ProductionConfig':
        """Load configuration from YAML file."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Override with environment variables
        config_data.update(cls._get_env_overrides())
        
        return cls(**config_data)
    
    @staticmethod
    def _get_env_overrides() -> Dict[str, Any]:
        """Get configuration overrides from environment variables."""
        overrides = {}
        
        # Database overrides
        if os.getenv('DB_HOST'):
            overrides.setdefault('database', {})['host'] = os.getenv('DB_HOST')
        if os.getenv('DB_PORT'):
            overrides.setdefault('database', {})['port'] = int(os.getenv('DB_PORT'))
        
        # Trading overrides
        if os.getenv('INITIAL_CAPITAL'):
            overrides.setdefault('trading', {})['initial_capital'] = float(os.getenv('INITIAL_CAPITAL'))
        if os.getenv('MAX_POSITION_SIZE'):
            overrides.setdefault('trading', {})['max_position_size'] = float(os.getenv('MAX_POSITION_SIZE'))
        
        return overrides
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'environment': self.environment,
            'debug': self.debug,
            'database': {
                'host': self.database.host,
                'port': self.database.port,
                'database': self.database.database,
                'username': self.database.username,
                'password': '***' if self.database.password else None
            },
            'redis': {
                'host': self.redis.host,
                'port': self.redis.port,
                'password': '***' if self.redis.password else None,
                'db': self.redis.db
            },
            'trading': {
                'initial_capital': self.trading.initial_capital,
                'max_position_size': self.trading.max_position_size,
                'max_leverage': self.trading.max_leverage,
                'target_volatility': self.trading.target_volatility,
                'entry_threshold': self.trading.entry_threshold,
                'exit_threshold': self.trading.exit_threshold,
                'stop_loss': self.trading.stop_loss,
                'take_profit': self.trading.take_profit
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format,
                'file_path': self.logging.file_path
            }
        }

def get_config(config_path: Optional[str] = None) -> ProductionConfig:
    """
    Get production configuration.
    
    Args:
        config_path: Optional path to YAML configuration file
        
    Returns:
        Production configuration object
    """
    if config_path:
        return ProductionConfig.from_file(config_path)
    else:
        return ProductionConfig.from_env() 