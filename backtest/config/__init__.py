"""
Backtest Configuration Module
==============================

Configuration management for institutional backtesting.

Provides comprehensive configuration classes for:
- Data configuration (ClickHouse, symbols, date ranges)
- Strategy configuration (strategy types, parameters, allocations)
- Risk configuration (position limits, VaR, drawdown limits)
- Execution configuration (liquidity, costs, slippage)
- Analytics configuration (metrics, attribution, reporting)
"""

from backtest.config.backtest_config import (
    BacktestConfiguration,
    BacktestMode,
    DataConfig,
    StrategyConfig,
    RiskConfig,
    ExecutionConfig,
    AnalyticsConfig,
)

__all__ = [
    'BacktestConfiguration',
    'BacktestMode',
    'DataConfig',
    'StrategyConfig',
    'RiskConfig',
    'ExecutionConfig',
    'AnalyticsConfig',
]

