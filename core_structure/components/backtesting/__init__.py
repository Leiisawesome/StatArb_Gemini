"""
Core Backtesting System
=======================

Professional backtesting system with:
- Realistic execution simulation using unified execution engine
- Consistent portfolio management across backtesting and live trading
- Advanced market condition modeling
- Comprehensive performance attribution
- Risk management integration
- Strategy-level performance tracking

This module provides institutional-grade backtesting that accurately
predicts live trading performance by using the same execution and
portfolio management systems as live trading.
"""

from .realistic_backtest_engine import (
    RealisticBacktestEngine,
    BacktestConfig,
    BacktestResult,
    create_realistic_backtest
)

__all__ = [
    'RealisticBacktestEngine',
    'BacktestConfig', 
    'BacktestResult',
    'create_realistic_backtest'
]
