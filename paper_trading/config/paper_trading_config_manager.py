"""
Paper Trading Configuration Manager
==================================

Manages configuration for paper trading system, extending the unified
configuration system with paper trading specific settings.

Features:
- IBKR connection configuration
- Strategy-specific live trading parameters
- Risk management settings
- Monitoring and alerting configuration
- Environment-specific overrides

Author: Pro Quant Desk Trader
"""

import os
import yaml
import logging
from datetime import datetime, time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

# Import base configuration system
try:
    from testing_framework.config.unified_config_manager import (
        UnifiedConfigManager, BacktestConfigFactory, Environment,
        BacktestConfig, StrategyType
    )
except ImportError:
    # Fallback for development
    UnifiedConfigManager = None
    BacktestConfigFactory = None
    Environment = None
    BacktestConfig = None
    StrategyType = None

logger = logging.getLogger(__name__)

class TradingEnvironment(Enum):
    """Trading environment types"""
    PAPER = "paper"
    LIVE = "live"
    SIMULATION = "simulation"

@dataclass
class IBKRConnectionConfig:
    """IBKR connection configuration"""
    host: str = "127.0.0.1"
    port: int = 7497  # Paper trading port
    client_id: int = 1
    account_id: str = ""
    connection_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 2.0
    heartbeat_interval: int = 30
    max_requests_per_second: int = 50
    max_orders_per_second: int = 5

@dataclass
class RiskLimits:
    """Risk management limits"""
    max_total_exposure: float = 0.95
    max_single_position: float = 0.20
    max_sector_exposure: float = 0.40
    max_correlation_threshold: float = 0.7
    max_daily_loss: float = 0.02
    max_daily_trades: int = 100
    max_position_value: float = 50000
    min_position_value: float = 1000
    portfolio_stop_loss: float = 0.05

@dataclass
class StrategyAllocation:
    """Strategy allocation configuration"""
    momentum_strategy: float = 0.40
    mean_reversion_strategy: float = 0.40
    pairs_trading_strategy: float = 0.20
    
    def __post_init__(self):
        """Validate allocations sum to 1.0"""
        total = self.momentum_strategy + self.mean_reversion_strategy + self.pairs_trading_strategy
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Strategy allocations must sum to 1.0, got {total}")

@dataclass
class LiveStrategyConfig:
    """Live strategy configuration"""
    strategy_id: str
    enable_strategy: bool = True
    max_positions: int = 5
    position_size_method: str = "volatility_adjusted"
    signal_frequency: str = "1min"
    execution_delay: int = 5
    max_drawdown: float = 0.10
    correlation_limit: float = 0.6
    rebalance_frequency: str = "daily"

@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    performance_update_frequency: int = 60
    risk_check_frequency: int = 30
    system_check_frequency: int = 10
    enable_alerts: bool = True
    alert_channels: Dict[str, bool] = field(default_factory=lambda: {
        'console': True, 'email': False, 'slack': False
    })

@dataclass
class PaperTradingConfig:
    """Complete paper trading configuration"""
    # Environment settings
    environment: TradingEnvironment = TradingEnvironment.PAPER
    enable_trading: bool = True
    enable_monitoring: bool = True
    
    # IBKR connection
    ibkr: IBKRConnectionConfig = field(default_factory=IBKRConnectionConfig)
    
    # Risk management
    risk_limits: RiskLimits = field(default_factory=RiskLimits)
    
    # Strategy allocation
    strategy_allocation: StrategyAllocation = field(default_factory=StrategyAllocation)
    
    # Strategy configurations
    momentum_config: LiveStrategyConfig = field(default_factory=lambda: LiveStrategyConfig(
        strategy_id="live_momentum_v1",
        max_positions=5,
        signal_frequency="1min"
    ))
    
    mean_reversion_config: LiveStrategyConfig = field(default_factory=lambda: LiveStrategyConfig(
        strategy_id="live_mean_reversion_v1",
        max_positions=8,
        signal_frequency="5min"
    ))
    
    pairs_trading_config: LiveStrategyConfig = field(default_factory=lambda: LiveStrategyConfig(
        strategy_id="live_pairs_trading_v1",
        max_positions=6,  # 3 pairs = 6 positions
        signal_frequency="5min",
        execution_delay=15
    ))
    
    # Monitoring
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Capital allocation
    initial_capital: float = 100000.0
    
    # Market hours
    market_start_time: str = "09:30:00"
    market_end_time: str = "16:00:00"
    timezone: str = "US/Eastern"

class PaperTradingConfigManager:
    """
    Configuration manager for paper trading system
    
    Extends the unified configuration system with paper trading specific
    settings and provides integration with IBKR and live trading parameters.
    """
    
    def __init__(self, config_file: str = "paper_trading_config.yaml",
                 environment: TradingEnvironment = TradingEnvironment.PAPER):
        """
        Initialize paper trading configuration manager
        
        Args:
            config_file: Path to paper trading configuration file
            environment: Trading environment (paper/live/simulation)
        """
        self.logger = logging.getLogger(__name__)
        self.environment = environment
        
        # Load paper trading configuration
        config_path = Path(__file__).parent / config_file
        self.config = self._load_paper_trading_config(config_path)
        
        # Initialize base configuration manager for strategy configs
        self.base_config_manager = UnifiedConfigManager(
            environment=Environment.DEVELOPMENT  # Map to base environment
        )
        
        self.logger.info(f"✅ Paper trading configuration loaded")
        self.logger.info(f"🌍 Environment: {environment.value}")
    
    def _load_paper_trading_config(self, config_path: Path) -> Dict[str, Any]:
        """Load paper trading configuration from YAML"""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            # Validate required sections
            required_sections = ['paper_trading', 'ibkr', 'risk_management', 'strategies']
            missing = [section for section in required_sections if section not in config]
            if missing:
                raise ValueError(f"Missing required configuration sections: {missing}")
            
            return config
            
        except FileNotFoundError:
            self.logger.error(f"❌ Paper trading configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"❌ Invalid YAML configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"❌ Configuration loading failed: {e}")
            raise
    
    def get_paper_trading_config(self) -> PaperTradingConfig:
        """Get complete paper trading configuration"""
        try:
            # Extract configuration sections
            paper_config = self.config.get('paper_trading', {})
            ibkr_config = self.config.get('ibkr', {})
            risk_config = self.config.get('risk_management', {})
            strategy_config = self.config.get('strategies', {})
            
            # Build IBKR connection config
            ibkr_conn = IBKRConnectionConfig(
                host=ibkr_config.get('connection', {}).get('host', '127.0.0.1'),
                port=ibkr_config.get('connection', {}).get('port', 7497),
                client_id=ibkr_config.get('connection', {}).get('client_id', 1),
                account_id=ibkr_config.get('connection', {}).get('account_id', ''),
                connection_timeout=ibkr_config.get('connection_timeout', 30),
                retry_attempts=ibkr_config.get('retry_attempts', 3),
                max_requests_per_second=ibkr_config.get('max_requests_per_second', 50),
                max_orders_per_second=ibkr_config.get('max_orders_per_second', 5)
            )
            
            # Build risk limits
            portfolio_limits = risk_config.get('portfolio', {})
            daily_limits = risk_config.get('daily_limits', {})
            position_limits = risk_config.get('position_limits', {})
            
            risk_limits = RiskLimits(
                max_total_exposure=portfolio_limits.get('max_total_exposure', 0.95),
                max_single_position=portfolio_limits.get('max_single_position', 0.20),
                max_sector_exposure=portfolio_limits.get('max_sector_exposure', 0.40),
                max_correlation_threshold=portfolio_limits.get('max_correlation_threshold', 0.7),
                max_daily_loss=daily_limits.get('max_daily_loss', 0.02),
                max_daily_trades=daily_limits.get('max_daily_trades', 100),
                max_position_value=position_limits.get('max_position_value', 50000),
                min_position_value=position_limits.get('min_position_value', 1000),
                portfolio_stop_loss=risk_config.get('stop_loss', {}).get('portfolio_stop_loss', 0.05)
            )
            
            # Build strategy allocation
            allocation_config = strategy_config.get('allocation', {})
            strategy_allocation = StrategyAllocation(
                momentum_strategy=allocation_config.get('momentum_strategy', 0.40),
                mean_reversion_strategy=allocation_config.get('mean_reversion_strategy', 0.40),
                pairs_trading_strategy=allocation_config.get('pairs_trading_strategy', 0.20)
            )
            
            # Build individual strategy configs
            momentum_cfg = strategy_config.get('momentum', {})
            momentum_config = LiveStrategyConfig(
                strategy_id=momentum_cfg.get('strategy_id', 'live_momentum_v1'),
                enable_strategy=momentum_cfg.get('enable_strategy', True),
                max_positions=momentum_cfg.get('max_positions', 5),
                position_size_method=momentum_cfg.get('position_size_method', 'volatility_adjusted'),
                signal_frequency=momentum_cfg.get('signal_frequency', '1min'),
                execution_delay=momentum_cfg.get('execution_delay', 5),
                max_drawdown=momentum_cfg.get('max_drawdown', 0.10),
                correlation_limit=momentum_cfg.get('correlation_limit', 0.6),
                rebalance_frequency=momentum_cfg.get('rebalance_frequency', 'daily')
            )
            
            mean_rev_cfg = strategy_config.get('mean_reversion', {})
            mean_reversion_config = LiveStrategyConfig(
                strategy_id=mean_rev_cfg.get('strategy_id', 'live_mean_reversion_v1'),
                enable_strategy=mean_rev_cfg.get('enable_strategy', True),
                max_positions=mean_rev_cfg.get('max_positions', 8),
                position_size_method=mean_rev_cfg.get('position_size_method', 'equal_weight'),
                signal_frequency=mean_rev_cfg.get('signal_frequency', '5min'),
                execution_delay=mean_rev_cfg.get('execution_delay', 10),
                max_drawdown=mean_rev_cfg.get('max_drawdown', 0.08),
                correlation_limit=mean_rev_cfg.get('correlation_limit', 0.5),
                rebalance_frequency=mean_rev_cfg.get('rebalance_frequency', 'intraday')
            )
            
            pairs_cfg = strategy_config.get('pairs_trading', {})
            pairs_trading_config = LiveStrategyConfig(
                strategy_id=pairs_cfg.get('strategy_id', 'live_pairs_trading_v1'),
                enable_strategy=pairs_cfg.get('enable_strategy', True),
                max_positions=pairs_cfg.get('max_pairs', 3) * 2,  # pairs = 2 positions each
                position_size_method=pairs_cfg.get('position_size_method', 'risk_parity'),
                signal_frequency=pairs_cfg.get('signal_frequency', '5min'),
                execution_delay=pairs_cfg.get('execution_delay', 15),
                max_drawdown=pairs_cfg.get('max_drawdown', 0.06),
                correlation_limit=pairs_cfg.get('correlation_limit', 0.3),
                rebalance_frequency=pairs_cfg.get('rebalance_frequency', 'continuous')
            )
            
            # Build monitoring config
            monitoring_cfg = self.config.get('monitoring', {})
            monitoring_config = MonitoringConfig(
                performance_update_frequency=monitoring_cfg.get('performance', {}).get('update_frequency', 60),
                risk_check_frequency=monitoring_cfg.get('risk', {}).get('check_frequency', 30),
                system_check_frequency=monitoring_cfg.get('system', {}).get('check_frequency', 10),
                enable_alerts=self.config.get('alerts', {}).get('trade_alerts', {}).get('enable', True),
                alert_channels=self.config.get('alerts', {}).get('channels', {
                    'console': True, 'email': False, 'slack': False
                })
            )
            
            # Create complete configuration
            return PaperTradingConfig(
                environment=self.environment,
                enable_trading=paper_config.get('enable_trading', True),
                enable_monitoring=paper_config.get('enable_monitoring', True),
                ibkr=ibkr_conn,
                risk_limits=risk_limits,
                strategy_allocation=strategy_allocation,
                momentum_config=momentum_config,
                mean_reversion_config=mean_reversion_config,
                pairs_trading_config=pairs_trading_config,
                monitoring=monitoring_config,
                initial_capital=100000.0,  # Default capital
                market_start_time=paper_config.get('market_hours', {}).get('start_time', '09:30:00'),
                market_end_time=paper_config.get('market_hours', {}).get('end_time', '16:00:00'),
                timezone=paper_config.get('market_hours', {}).get('timezone', 'US/Eastern')
            )
            
        except Exception as e:
            self.logger.error(f"❌ Failed to build paper trading configuration: {e}")
            raise
    
    def get_strategy_backtest_config(self, strategy_type: StrategyType, 
                                   overrides: Dict[str, Any] = None) -> BacktestConfig:
        """
        Get backtest configuration for a strategy type
        
        This bridges the paper trading config with the unified backtest config
        system to maintain compatibility with existing strategy implementations.
        """
        try:
            # Map strategy types to configuration paths
            strategy_map = {
                StrategyType.MOMENTUM: "momentum.momentum_single_tsla",
                StrategyType.MEAN_REVERSION: "mean_reversion.mean_reversion_conservative", 
                StrategyType.PAIRS_TRADING: "pairs_trading.pairs_etf_conservative"
            }
            
            if strategy_type not in strategy_map:
                raise ValueError(f"Unsupported strategy type: {strategy_type}")
            
            strategy_path = strategy_map[strategy_type]
            
            # Get base configuration
            config = self.base_config_manager.get_strategy_config(strategy_path, overrides)
            
            # Override with paper trading specific settings
            paper_config = self.get_paper_trading_config()
            config.initial_capital = paper_config.initial_capital
            
            return config
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get strategy backtest config: {e}")
            raise
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Validate paper trading configuration"""
        validation_results = {
            'ibkr_config_valid': False,
            'risk_limits_valid': False,
            'strategy_allocation_valid': False,
            'monitoring_config_valid': False,
            'overall_valid': False
        }
        
        try:
            config = self.get_paper_trading_config()
            
            # Validate IBKR configuration
            if config.ibkr.host and config.ibkr.port > 0:
                validation_results['ibkr_config_valid'] = True
            
            # Validate risk limits
            if (0 < config.risk_limits.max_total_exposure <= 1.0 and
                0 < config.risk_limits.max_single_position <= 1.0):
                validation_results['risk_limits_valid'] = True
            
            # Validate strategy allocation
            total_allocation = (config.strategy_allocation.momentum_strategy +
                              config.strategy_allocation.mean_reversion_strategy +
                              config.strategy_allocation.pairs_trading_strategy)
            if abs(total_allocation - 1.0) < 0.01:
                validation_results['strategy_allocation_valid'] = True
            
            # Validate monitoring configuration
            if config.monitoring.performance_update_frequency > 0:
                validation_results['monitoring_config_valid'] = True
            
            # Overall validation
            validation_results['overall_valid'] = all([
                validation_results['ibkr_config_valid'],
                validation_results['risk_limits_valid'],
                validation_results['strategy_allocation_valid'],
                validation_results['monitoring_config_valid']
            ])
            
        except Exception as e:
            self.logger.error(f"❌ Configuration validation failed: {e}")
        
        return validation_results
    
    def get_ibkr_connection_config(self) -> Dict[str, Any]:
        """Get IBKR connection configuration for broker integration"""
        config = self.get_paper_trading_config()
        
        return {
            'host': config.ibkr.host,
            'port': config.ibkr.port,
            'client_id': config.ibkr.client_id,
            'account_id': config.ibkr.account_id,
            'paper_trading': config.environment == TradingEnvironment.PAPER,
            'connection_timeout': config.ibkr.connection_timeout,
            'retry_attempts': config.ibkr.retry_attempts,
            'retry_delay': config.ibkr.retry_delay,
            'max_requests_per_second': config.ibkr.max_requests_per_second,
            'max_orders_per_second': config.ibkr.max_orders_per_second
        }

def load_paper_trading_config(environment: str = "paper") -> PaperTradingConfig:
    """
    Convenience function to load paper trading configuration
    
    Args:
        environment: Trading environment (paper/live/simulation)
    
    Returns:
        Complete paper trading configuration
    """
    env = TradingEnvironment(environment)
    manager = PaperTradingConfigManager(environment=env)
    return manager.get_paper_trading_config()

def validate_paper_trading_setup() -> Dict[str, Any]:
    """
    Validate paper trading setup and return status
    
    Returns:
        Dictionary with validation results and setup status
    """
    manager = PaperTradingConfigManager()
    validation_results = manager.validate_configuration()
    
    return {
        'ready': validation_results['overall_valid'],
        'validation_results': validation_results,
        'config_manager': manager
    }
