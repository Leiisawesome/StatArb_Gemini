"""
Testing Framework for StatArb Gemini
====================================

Comprehensive testing infrastructure for the statistical arbitrage trading system.

This framework includes:
- Multi-strategy backtesting with real ClickHouse data
- End-to-end system validation
- Performance metrics calculation and validation
- Time-series backtesting with proper signal generation

Author: Pro Quant Desk Trader
"""

from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

__version__ = "1.0.0"
__author__ = "Pro Quant Desk Trader"

# Test categories
TEST_CATEGORIES = {
    "multi_strategy": "Multi-strategy backtesting with real data",
    "end_to_end": "Comprehensive end-to-end system validation",
    "performance": "Performance metrics and analytics validation",
    "integration": "System integration and data flow validation"
}

# Available test suites
AVAILABLE_TESTS = {
    "multi_strategy_backtest_real_data": {
        "description": "Real multi-strategy backtesting with ClickHouse data",
        "category": "multi_strategy",
        "file": "multi_strategy_backtest_real_data.py"
    },
    "comprehensive_end_to_end_test_suite": {
        "description": "Comprehensive end-to-end system validation",
        "category": "end_to_end", 
        "file": "comprehensive_end_to_end_test_suite.py"
    }
}
