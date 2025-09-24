"""
Trading Desk Engines
===================

This package contains trading execution engines that compose core_engine components:

- institutional_backtest_engine: Institutional-grade backtesting
- paper_trading_engine: Paper trading simulation (future)
- live_trading_engine: Live trading execution (future)

All engines follow the same architectural patterns and use core_engine components
for consistent behavior across backtesting, paper trading, and live trading environments.

Author: StatArb_Gemini Trading Desk
Version: 1.0.0
"""

from .backtest_types import (
    BacktestConfig,
    BacktestResult,
    BacktestMode,
    ExecutionModel,
    CommissionModel,
    SlippageModel
)
from .institutional_backtest_engine import (
    InstitutionalBacktestEngine,
    InstitutionalBacktestConfig,
    InstitutionalBacktestResult
)

__all__ = [
    'InstitutionalBacktestEngine',
    'BacktestConfig',
    'BacktestResult',
    'BacktestMode',
    'ExecutionModel'
]