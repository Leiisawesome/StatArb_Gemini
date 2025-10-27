"""
Backtest Configuration Module
==============================

Configuration management for institutional backtesting.

PHASE 1 COMPLETE: ✅ Centralized configuration (Rule 1, Section 7)
All configuration now sourced from core_engine/config/ for consistency.

Usage:
    from core_engine.config import BacktestConfig, BacktestMode
    
    config = BacktestConfig(
        backtest_name="My Backtest",
        symbols=["AAPL"],
        start_date="2024-01-01",
        end_date="2024-03-31"
    )
"""

# PHASE 1: Configuration now centralized in core_engine/config/
# Import from core_engine for consistency (Rule 1, Section 7)
from core_engine.config import BacktestConfig, BacktestMode

__all__ = [
    'BacktestConfig',
    'BacktestMode',
]


