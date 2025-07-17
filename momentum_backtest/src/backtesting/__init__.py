"""
Backtesting module containing backtesting engine and results management
"""

# Import from clean implementation
from .clean_backtest import MomentumBacktest, BacktestResults

__all__ = ['MomentumBacktest', 'BacktestResults']
