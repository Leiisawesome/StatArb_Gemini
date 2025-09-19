"""
Testing Framework for StatArb Gemini
====================================

Focused testing infrastructure for core trading strategies.

This framework includes:
- Advanced momentum strategy backtesting with risk management
- Mean reversion strategy backtesting
- Pairs trading strategy backtesting
- Real ClickHouse data integration
- Performance metrics and validation
- Integration with 10-component architecture

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
    "mean_reversion": "Mean reversion strategy testing",
    "pairs_trading": "Pairs trading strategy testing"
}

# Available test suites for 10-component architecture integration
AVAILABLE_TESTS = {
    "advanced_momentum_backtest": {
        "description": "Advanced momentum strategy with comprehensive risk management",
        "category": "momentum",
        "file": "advanced_momentum_backtest.py",
        "integration_ready": True
    },
    "advanced_mean_reversion_backtest": {
        "description": "Mean reversion strategy backtesting",
        "category": "mean_reversion", 
        "file": "advanced_mean_reversion_backtest.py",
        "integration_ready": True
    },
    "advanced_pairs_trading_backtest": {
        "description": "Pairs trading strategy backtesting",
        "category": "pairs_trading",
        "file": "advanced_pairs_trading_backtest.py", 
        "integration_ready": True
    }
}

# 10-Component Architecture Integration Points
COMPONENT_INTEGRATION = {
    "SystemOrchestrator": "Central coordination and message routing",
    "MarketDataSource": "Real-time and historical data feeds", 
    "UnifiedDataManager": "Data processing and validation",
    "UnifiedRegimeEngine": "Market condition detection",
    "AdvancedRiskManager": "Central risk authority and governance",
    "RealTimeTradingEngine": "Live trading execution", 
    "StrategyManager": "Strategy lifecycle management",
    "UnifiedExecutionEngine": "Order execution and fills",
    "PortfolioManager": "Position and portfolio tracking",
    "PerformanceMonitor": "Real-time performance analytics"
}