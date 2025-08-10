"""
Strategy Testing Module

Comprehensive testing framework for trading strategies.

Author: Pro Quant Desk Trader
"""

# Import testing components
from .strategy_test_suite import (
    StrategyTestSuite,
    TestResult
)

from .regression_test_suite import (
    RegressionTestSuite,
    RegressionTestResult
)

__all__ = [
    # Test suites
    'StrategyTestSuite',
    'TestResult',
    'RegressionTestSuite',
    'RegressionTestResult'
]
