"""
Strategy Assessment Testing Module
==================================

Professional strategy assessment and optimization testing framework.

This module provides:
- Comprehensive backtesting infrastructure
- Strategy testing and validation
- Performance analysis and ranking
- Optimization recommendations

Author: StatArb_Gemini Strategy Optimization
Version: 1.0.0 (Phase 1 Implementation)
"""

from .backtesting_framework import (
    ProfessionalBacktester,
    BacktestConfig,
    PerformanceMetrics,
    Trade,
    MarketRegime
)

from .strategy_tester import (
    ComprehensiveStrategyTester,
    StrategyTestConfig,
    StrategyTestResult
)

__all__ = [
    'ProfessionalBacktester',
    'BacktestConfig',
    'PerformanceMetrics',
    'Trade',
    'MarketRegime',
    'ComprehensiveStrategyTester',
    'StrategyTestConfig',
    'StrategyTestResult'
]

__version__ = '1.0.0'
