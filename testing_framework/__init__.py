"""
Testing Framework for StatArb Gemini
====================================

Focused testing infrastructure for core trading strategies.

This framework includes:
- Advanced momentum strategy backtesting with risk management
- Mean reversion strategy backtesting
- Real ClickHouse data integration
- Performance metrics and validation

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
    "strategy_backtesting": "Core strategy backtesting with real data",
    "momentum": "Advanced momentum strategy testing",
    "mean_reversion": "Mean reversion strategy testing"
}

# Available test suites
AVAILABLE_TESTS = {
    "advanced_momentum_backtest": {
        "description": "Advanced momentum strategy with comprehensive risk management",
        "category": "momentum",
        "file": "advanced_momentum_backtest.py"
    },
    "mean_reversion_strategy_backtest": {
        "description": "Mean reversion strategy backtesting",
        "category": "mean_reversion", 
        "file": "mean_reversion_strategy_backtest.py"
    }
}
