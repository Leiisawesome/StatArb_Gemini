"""
Institutional Backtest Application
===================================

Production-grade backtesting system built using core_engine "Lego Bricks"
following the 13 Rules and institutional-backtest-workflow.mdc.

This application orchestrates all 9 core_engine components to provide:
- Regime-First market analysis (Rule 13)
- Liquidity-aware execution (Rule 12)
- Multi-strategy coordination (Rule 8)
- Centralized risk management (Rule 4)
- Comprehensive performance analytics (Rule 9)

Usage:
    from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
    from backtest.config.backtest_config import BacktestConfiguration
    
    config = BacktestConfiguration.from_json("my_backtest.json")
    engine = InstitutionalBacktestEngine(config)
    await engine.initialize()
    results = await engine.run_backtest()
    report = engine.generate_report()
"""

__version__ = "1.0.0"
__author__ = "StatArb_Gemini Team"

# Phase 1: Configuration system (available)
from backtest.config.backtest_config import BacktestConfiguration

# Phase 2.1: Main engine skeleton (available)
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine

__all__ = [
    'InstitutionalBacktestEngine',
    'BacktestConfiguration',
]

