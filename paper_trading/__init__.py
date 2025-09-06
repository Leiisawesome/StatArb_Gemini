"""
Paper Trading System for StatArb Gemini
=======================================

Professional paper trading implementation with IBKR integration.
Bridges backtesting strategies to live trading environment.

Features:
- IBKR paper trading integration
- Real-time strategy execution
- Multi-strategy coordination
- Comprehensive risk management
- Real-time monitoring and alerting

Author: Pro Quant Desk Trader
"""

__version__ = "1.0.0"
__author__ = "Pro Quant Desk Trader"

# Paper trading components
from .config import PaperTradingConfig
from .strategy_bridge import StrategyBridgeFactory

__all__ = [
    'PaperTradingConfig',
    'StrategyBridgeFactory'
]
