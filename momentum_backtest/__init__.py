"""
Momentum Backtest - Production Ready Trading Strategy Framework
================================================================

A comprehensive momentum trading strategy backtesting system with:
- Configurable training/testing periods
- Real-time ClickHouse data integration  
- Production-grade risk management
- Comprehensive performance analytics

Quick Start:
-----------
>>> from momentum_backtest import ConfigManager, MomentumStrategy, MomentumBacktest, RiskManager
>>> config = ConfigManager(environment="development")
>>> strategy = MomentumStrategy(config.get_all())
>>> risk_manager = RiskManager(config.get_all())
>>> backtest = MomentumBacktest(strategy, risk_manager, config.get_all())
>>> # Load your data and run: results = backtest.run(training_data, testing_data)

Main Components:
---------------
- ConfigManager: Production configuration management with presets
- MomentumStrategy: Academic-standard momentum trading strategy
- MomentumBacktest: Production backtesting engine with risk management
- RiskManager: Position sizing and portfolio risk controls
- PerformanceAnalyzer: Comprehensive performance metrics and analytics
- ClickHouseDataLoader: High-performance database integration
"""

__version__ = "1.0.0"
__author__ = "StatArb_Gemini Team"

# Core imports for easy access
from .src.backtesting import MomentumBacktest, BacktestResults
from .src.data import ClickHouseDataLoader
from .src.strategy import MomentumStrategy, BaseStrategy
from .src.utils import PerformanceAnalyzer
from .src.risk import RiskManager
from .src.config import ConfigManager, load_config, PRESET_CONFIGS

# Version info
__all__ = [
    'MomentumBacktest',
    'BacktestResults',
    'ClickHouseDataLoader', 
    'MomentumStrategy',
    'BaseStrategy',
    'PerformanceAnalyzer',
    'RiskManager',
    'ConfigManager',
    'load_config',
    'PRESET_CONFIGS',
    '__version__',
    '__author__'
]

# Configuration defaults - use ConfigManager.load_config() for production
DEFAULT_CONFIG = {
    'data': {
        'training_start': '2023-01-01',
        'training_end': '2023-12-31',
        'testing_start': '2024-01-01', 
        'testing_end': '2024-06-30',
        'max_symbols': 20,
        'min_periods': 30
    },
    'strategy': {
        'momentum_window': 60,
        'rebalance_frequency': 'monthly',
        'risk_adjustment': True
    },
    'backtesting': {
        'initial_capital': 100000.0,
        'commission_rate': 0.001,
        'market_impact': 0.0005
    },
    'risk_management': {
        'max_position_size': 0.45,
        'cash_reserve_ratio': 0.10,
        'max_leverage': 2.0
    }
}
