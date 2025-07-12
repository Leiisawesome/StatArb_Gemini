"""
Backtesting module for enhanced pair trading system.

This module provides comprehensive backtesting capabilities including:
- Walk forward analysis with rolling windows
- Out-of-sample testing
- Parameter optimization
- Performance validation
"""

from .walk_forward import WalkForwardAnalyzer, WalkForwardConfig, WalkForwardResult

__all__ = [
    'WalkForwardAnalyzer',
    'WalkForwardConfig', 
    'WalkForwardResult'
]

# BacktestEngine imports are commented out due to dependency issues
# from .engine import BacktestEngine, BacktestConfig, BacktestResult 