"""
Trade Execution Module

This module provides professional-grade trade execution capabilities with:
- Realistic transaction costs and slippage modeling
- Market impact estimation
- Order management and tracking
- Risk-aware position sizing
- Execution quality metrics
"""

from .execution_engine import ExecutionEngine, Trade, OrderStatus, ExecutionResult
from .market_impact import MarketImpactModel, SlippageModel
from .order_management import OrderManager, Order, OrderType

__all__ = [
    'ExecutionEngine',
    'Trade', 
    'OrderStatus',
    'ExecutionResult',
    'MarketImpactModel',
    'SlippageModel', 
    'OrderManager',
    'Order',
    'OrderType'
] 