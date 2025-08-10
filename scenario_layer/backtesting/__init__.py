"""
Historical Backtesting Engine
============================

Professional backtesting engine with:
- Historical data replay with configurable speed
- Strategy performance analysis with risk metrics
- Walk-forward analysis and parameter optimization
- Production-grade performance monitoring

Author: Pro Quant Desk Trader
"""

from .historical_backtesting_engine import (
    HistoricalBacktestingEngine,
    BacktestConfig,
    BacktestResult,
    BacktestMetrics,
    BacktestStatus,
    TimeRange,
    DataReplayMode,
    create_training_config,
    create_out_of_sample_config
)

__all__ = [
    'HistoricalBacktestingEngine',
    'BacktestConfig',
    'BacktestResult',
    'BacktestMetrics',
    'BacktestStatus',
    'TimeRange',
    'DataReplayMode',
    'create_training_config',
    'create_out_of_sample_config'
]
