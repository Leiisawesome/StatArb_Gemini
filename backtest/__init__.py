"""
Institutional Backtest Application
===================================

Production-grade backtesting system built using core_engine "Lego Bricks"
following the 13 Rules and institutional-backtest-workflow.mdc.

This application orchestrates all 9 core_engine components to provide:
- Regime-First market analysis (Rule 2 Regime-First)
- Liquidity-aware execution (Rule 7 Section B)
- Multi-strategy coordination (Rule 5)
- Centralized risk management (Rule 4)
- Comprehensive performance analytics (Rule 6)

Usage:
    from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
    from core_engine.config import BacktestConfig, BacktestMode
    
    config = BacktestConfig.from_dict({
        "backtest_name": "My Backtest",
        "symbols": ["AAPL"],
        "start_date": "2024-01-01",
        "end_date": "2024-03-31"
    })
    engine = InstitutionalBacktestEngine(config)
    await engine.initialize()
    results = await engine.run_backtest()
    report = engine.generate_report()
"""

__version__ = "1.0.0"
__author__ = "StatArb_Gemini Team"

# Phase 1: Configuration system (CENTRALIZED - using core_engine configs per Rule 1, Section 7)
from core_engine.config import BacktestConfig, BacktestMode

# Phase 2.1: Main engine skeleton (available)
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine

__all__ = [
    'InstitutionalBacktestEngine',
    'BacktestConfig',
    'BacktestMode',
]


