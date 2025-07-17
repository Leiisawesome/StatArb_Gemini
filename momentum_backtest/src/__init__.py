"""
Main __init__.py for momentum backtest production system
"""

__version__ = "1.0.0"
__author__ = "StatArb Research Team"
__description__ = "Production-grade momentum trading backtesting framework"

# Core imports for easy access
from .config import ConfigManager, load_config, PRESET_CONFIGS
from .strategy import ModernMomentumStrategy, BaseStrategy
from .backtesting import MomentumBacktest, BacktestResults
from .risk import RiskManager
from .utils import PerformanceAnalyzer
from .data.clickhouse_connector import ClickHouseDataLoader

__all__ = [
    'ConfigManager',
    'load_config', 
    'PRESET_CONFIGS',
    'ModernMomentumStrategy',
    'BaseStrategy',
    'MomentumBacktest',
    'BacktestResults',
    'RiskManager',
    'PerformanceAnalyzer',
    'ClickHouseDataLoader'
]

# Version info
VERSION_INFO = {
    'major': 1,
    'minor': 0,
    'patch': 0,
    'release': 'stable'
}

def get_version():
    """Get version string"""
    return f"{VERSION_INFO['major']}.{VERSION_INFO['minor']}.{VERSION_INFO['patch']}"

def print_system_info():
    """Print system information"""
    print(f"Momentum Backtest System v{get_version()}")
    print(f"Description: {__description__}")
    print(f"Author: {__author__}")
    print("="*50)
    print("Available Components:")
    print("- ConfigManager: Configuration management with environment support")
    print("- ModernMomentumStrategy: Modern multi-timeframe momentum with volatility scaling")
    print("- MomentumBacktest: Complete backtesting engine with risk management")
    print("- RiskManager: Position sizing and portfolio risk controls")
    print("- PerformanceAnalyzer: Comprehensive performance metrics calculation")
    print("- ClickHouseDataLoader: High-performance database integration")
    print("="*50)
