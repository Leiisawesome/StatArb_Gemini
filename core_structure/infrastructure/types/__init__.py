"""
Canonical Type Definitions
=========================

Centralized location for all shared types to eliminate duplicates.
"""

from .order_types import OrderType, OrderSide, OrderStatus, Order, Fill, TimeInForce, ExecutionStrategy
from .strategy_types import StrategyType, StrategyConfig, Position
from .market_types import MarketRegime, RegimeInfo, RegimeConfidence, RegimeType
from .monitoring_types import AlertLevel, PerformanceMetric

__all__ = [
    'OrderType', 'OrderSide', 'OrderStatus', 'Order', 'Fill', 'TimeInForce', 'ExecutionStrategy',
    'StrategyType', 'StrategyConfig', 'Position',
    'MarketRegime', 'RegimeInfo', 'RegimeConfidence', 'RegimeType',
    'AlertLevel', 'PerformanceMetric'
]
