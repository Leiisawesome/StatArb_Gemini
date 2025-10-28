"""
Strategy Execution Testing Framework
====================================

Comprehensive testing framework for validating strategy signal generation,
execution pipeline, and performance attribution in StatArb_Gemini.

This framework provides:
- StrategyTestEngine: Main testing orchestration
- SignalValidator: Signal quality assessment
- ExecutionSimulator: Realistic trade execution
- PerformanceAttributor: P&L attribution engine

Usage:
    from tests.strategy_execution.framework import StrategyTestEngine, SignalValidator

    # Create test engine
    test_engine = StrategyTestEngine(test_config)

    # Run comprehensive validation
    results = await test_engine.test_strategy_execution(strategy, config, market_data)

Author: StatArb_Gemini Phase 7 Strategy Validation
Version: 1.0.0
"""

from .strategy_test_engine import (
    StrategyTestEngine,
    SignalValidator,
    ExecutionSimulator,
    PerformanceAttributor,
    StrategyTestConfig,
    TestResult
)

__all__ = [
    'StrategyTestEngine',
    'SignalValidator',
    'ExecutionSimulator',
    'PerformanceAttributor',
    'StrategyTestConfig',
    'TestResult'
]