from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import yaml
import json
import os
from pathlib import Path
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Environment(Enum):
    DEVELOPMENT = "development"
    BACKTESTING = "backtesting"
    PRODUCTION = "production"
    REAL_TIME = "real_time"

@dataclass
class StrategyConfig:
    """Strategy-specific configuration"""
    name: str
    version: str
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
    optimization_method: str = "grid_search"  # grid_search, bayesian, genetic
    optimization_metrics: List[str] = field(default_factory=lambda: ["sharpe_ratio", "max_drawdown"])
    
@dataclass
class TradingConfig:
    """Trading period configuration"""
    start_date: str
    end_date: str
    real_time: bool = False
    execution_mode: str = "simulation"  # simulation, paper, live
    position_sizing: str = "fixed"  # fixed, kelly, volatility_targeting

@dataclass
class EnhancedConfig:
    """Enhanced unified configuration"""
    environment: Environment
    strategy: StrategyConfig
    trading: TradingConfig
    training: Optional[TrainingConfig] = None
    database: Dict[str, Any] = field(default_factory=dict)
    data_feeds: Dict[str, Any] = field(default_factory=dict)
    execution: Dict[str, Any] = field(default_factory=dict)
    risk_management: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)
    
    def save_to_file(self, filepath: str):
        """Save configuration to file"""
        config_dict = {
            'environment': self.environment.value,
            'strategy': self.strategy.to_dict(),
            'training': self.training.__dict__ if self.training else None,
            'trading': self.trading.__dict__,
            'database': self.database,
            'data_feeds': self.data_feeds,
            'execution': self.execution,
            'risk_management': self.risk_management,
            'logging': self.logging
        }
        
        with open(filepath, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'EnhancedConfig':
        """Load configuration from file"""
        with open(filepath, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        return cls._from_dict(config_dict)
    
    @classmethod
    def _from_dict(cls, config_dict: Dict[str, Any]) -> 'EnhancedConfig':
        """Create config from dictionary"""
        return cls(
            environment=Environment(config_dict['environment']),
            strategy=StrategyConfig(**config_dict['strategy']),
            training=TrainingConfig(**config_dict['training']) if config_dict.get('training') else None,
            trading=TradingConfig(**config_dict['trading']),
            database=config_dict.get('database', {}),
            data_feeds=config_dict.get('data_feeds', {}),
            execution=config_dict.get('execution', {}),
            risk_management=config_dict.get('risk_management', {}),
            logging=config_dict.get('logging', {})
        )

class EnhancedConfigManager:
    """Enhanced configuration manager with parameter persistence"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Use absolute path to the strategies config directory
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.config_dir = Path(base_dir) / "backtesting_framework" / "configs" / "strategies"
        else:
            self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.current_config: Optional[EnhancedConfig] = None
        
    def create_step1_backtesting_config(self, strategy_name: str, 
                                       training_start: str, training_end: str,
                                       validation_start: str, validation_end: str) -> EnhancedConfig:
        """Create Step 1 backtesting configuration (historical data)"""
        
        # Load base strategy config
        strategy_config = self._load_strategy_config(strategy_name)
        
        config = EnhancedConfig(
            environment=Environment.BACKTESTING,
            strategy=strategy_config,
            training=TrainingConfig(
                start_date=training_start,
                end_date=training_end,
                parameter_optimization=True,
                optimization_method="grid_search"
            ),
            trading=TradingConfig(
                start_date=validation_start,
                end_date=validation_end,
                real_time=False,
                execution_mode="simulation"
            ),
            database=self._get_database_config(),
            data_feeds=self._get_step1_data_feeds_config(),
            execution=self._get_execution_config(),
            risk_management=self._get_risk_config(),
            logging=self._get_logging_config()
        )
        
        return config
    
    def create_step2_realtime_config(self, strategy_name: str, 
                                    trading_start: str) -> EnhancedConfig:
        """Create Step 2 real-time configuration (Polygon.io data)"""
        
        # Load optimized parameters from Step 1
        optimized_params = self._load_optimized_parameters(strategy_name)
        
        strategy_config = self._load_strategy_config(strategy_name)
        strategy_config.parameters.update(optimized_params)
        
        config = EnhancedConfig(
            environment=Environment.REAL_TIME,
            strategy=strategy_config,
            trading=TradingConfig(
                start_date=trading_start,
                end_date="",  # Ongoing
                real_time=True,
                execution_mode="simulation"  # Change to "paper" or "live" when ready
            ),
            database=self._get_database_config(),
            data_feeds=self._get_step2_data_feeds_config(),
            execution=self._get_execution_config(),
            risk_management=self._get_risk_config(),
            logging=self._get_logging_config()
        )
        
        return config
    
    def create_real_time_config(self, strategy_name: str, 
                               trading_start: str) -> EnhancedConfig:
        """Create real-time configuration"""
        
        # Load optimized parameters from training
        optimized_params = self._load_optimized_parameters(strategy_name)
        
        strategy_config = self._load_strategy_config(strategy_name)
        strategy_config.parameters.update(optimized_params)
        
        config = EnhancedConfig(
            environment=Environment.REAL_TIME,
            strategy=strategy_config,
            trading=TradingConfig(
                start_date=trading_start,
                end_date="",  # Ongoing
                real_time=True,
                execution_mode="simulation"  # Change to "paper" or "live" when ready
            ),
            database=self._get_database_config(),
            data_feeds=self._get_data_feeds_config(),
            execution=self._get_execution_config(),
            risk_management=self._get_risk_config(),
            logging=self._get_logging_config()
        )
        
        return config
    
    def save_optimized_parameters(self, strategy_name: str, 
                                 parameters: Dict[str, Any],
                                 performance_metrics: Dict[str, float]):
        """Save optimized parameters from training"""
        
        param_file = self.config_dir / f"{strategy_name}_optimized_params.json"
        
        param_data = {
            'parameters': parameters,
            'performance_metrics': performance_metrics,
            'optimization_date': datetime.now().isoformat(),
            'training_period': {
                'start': self.current_config.training.start_date,
                'end': self.current_config.training.end_date
            }
        }
        
        with open(param_file, 'w') as f:
            json.dump(param_data, f, indent=2)
        
        logger.info(f"Saved optimized parameters for {strategy_name} to {param_file}")
    
    def _load_optimized_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """Load optimized parameters from training"""
        
        param_file = self.config_dir / f"{strategy_name}_optimized_params.json"
        
        if not param_file.exists():
            logger.warning(f"No optimized parameters found for {strategy_name}")
            return {}
        
        with open(param_file, 'r') as f:
            param_data = json.load(f)
        
        logger.info(f"Loaded optimized parameters for {strategy_name}")
        return param_data.get('parameters', {})
    
    def _load_strategy_config(self, strategy_name: str) -> StrategyConfig:
        """Load strategy configuration"""
        
        strategy_file = self.config_dir / f"{strategy_name}_strategy.yaml"
        if not strategy_file.exists():
            # Try without _strategy suffix for compatibility
            strategy_file = self.config_dir / f"{strategy_name}.yaml"
        if not strategy_file.exists():
            raise FileNotFoundError(f"Strategy config not found: {strategy_file}")
        
        with open(strategy_file, 'r') as f:
            strategy_dict = yaml.safe_load(f)
        # Only keep fields expected by StrategyConfig
        allowed_fields = {'name', 'version', 'parameters', 'risk_limits', 'timeframes', 'symbols'}
        filtered = {k: v for k, v in strategy_dict.items() if k in allowed_fields}
        return StrategyConfig(**filtered)
    
    def _get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            'clickhouse': {
                'host': 'localhost',
                'port': 9000,
                'database': 'market_data',
                'user': 'default',
                'password': ''
            }
        }
    
    def _get_step1_data_feeds_config(self) -> Dict[str, Any]:
        """Get Step 1 data feeds configuration (historical data only)"""
        return {
            'clickhouse': {
                'historical_data': True,
                'real_time_updates': False,
                'data_source': 'local',
                'cache_enabled': True
            },
            'polygon': {
                'enabled': False,  # Not used in Step 1
                'api_key': os.getenv('POLYGON_API_KEY')
            }
        }
    
    def _get_step2_data_feeds_config(self) -> Dict[str, Any]:
        """Get Step 2 data feeds configuration (real-time data)"""
        return {
            'polygon': {
                'api_key': os.getenv('POLYGON_API_KEY'),
                'websocket_url': 'wss://socket.polygon.io/stocks',
                'rate_limit': 1000,  # Unlimited with starter plan
                'real_time_delay': 15,  # 15-minute delay
                'enabled': True
            },
            'clickhouse': {
                'historical_data': False,  # Not used in Step 2
                'real_time_updates': False,
                'data_source': 'polygon'
            }
        }
    
    def _get_data_feeds_config(self) -> Dict[str, Any]:
        """Get general data feeds configuration"""
        return {
            'polygon': {
                'api_key': os.getenv('POLYGON_API_KEY'),
                'websocket_url': 'wss://socket.polygon.io/stocks',
                'rate_limit': 1000,
                'real_time_delay': 15,
                'enabled': True
            },
            'clickhouse': {
                'historical_data': True,
                'real_time_updates': False,
                'data_source': 'local',
                'cache_enabled': True
            }
        }
    
    def _get_execution_config(self) -> Dict[str, Any]:
        """Get execution configuration with enhanced transaction cost modeling"""
        return {
            'simulation': {
                'enabled': True,
                'initial_capital': 10_000_000,
                'commission_rate': 0.001,  # 10 bps
                'slippage': 0.0001,        # 1 bp
                'market_impact': 0.0002,   # 2 bps (simple linear model)
                'min_trade_size': 1000,    # $1K minimum trade
                'max_trade_size': 1000000  # $1M maximum trade
            },
            'paper_trading': {
                'enabled': False,
                'broker': 'alpaca',
                'api_key': os.getenv('ALPACA_API_KEY'),
                'secret_key': os.getenv('ALPACA_SECRET_KEY'),
                'commission_rate': 0.0005,  # 5 bps for paper trading
                'slippage': 0.0001
            },
            'live_trading': {
                'enabled': False,
                'broker': 'alpaca',
                'api_key': os.getenv('ALPACA_LIVE_API_KEY'),
                'secret_key': os.getenv('ALPACA_LIVE_SECRET_KEY'),
                'commission_rate': 0.0005,  # 5 bps for live trading
                'slippage': 0.0001
            }
        }
    
    def _get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration"""
        return {
            'position_limits': {
                'max_position_size': 5_000_000,  # $5M per position
                'max_portfolio_concentration': 0.2,  # 20% max concentration
                'max_daily_trades': 100
            },
            'risk_limits': {
                'max_daily_loss': 0.02,  # 2% daily loss limit
                'max_drawdown': 0.15,  # 15% max drawdown
                'var_limit': 0.01  # 1% VaR limit
            },
            'stop_loss': {
                'enabled': True,
                'percentage': 0.05,  # 5% stop loss
                'trailing': True
            }
        }
    
    def _get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            'level': 'INFO',
            'file': 'logs/trading.log',
            'max_size': '100MB',
            'backup_count': 5,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        } 