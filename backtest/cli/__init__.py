"""
Institutional Backtest CLI

Professional command-line interface for running institutional-grade backtests.

Usage:
    python -m backtest.cli.main [command] [options]

Or use the shortcut:
    backtest [command] [options]
"""

from backtest.cli.main import BacktestCLI, main
from backtest.cli.interactive import InteractiveBacktestCLI
from backtest.cli.config_builder import ConfigurationBuilder

__all__ = [
    'BacktestCLI',
    'InteractiveBacktestCLI',
    'ConfigurationBuilder',
    'main'
]
