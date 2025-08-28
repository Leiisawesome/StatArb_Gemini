"""
Infrastructure layer for StatArb system
Provides core services and utilities for the application
"""

from .database.database_system import DatabaseManager
from .monitoring.monitoring_system import MetricsCollector
from .config import UnifiedConfigManager as ConfigManager
from .messaging.messaging_system import MessageBus, Message

# Canonical types to eliminate duplicates
from .types import (
    OrderType, OrderSide, OrderStatus, Order, Fill, TimeInForce, ExecutionStrategy,
    StrategyType,
    StrategyConfig,
    Position, MarketRegime, RegimeInfo, RegimeConfidence, RegimeType, 
    AlertLevel, PerformanceMetric
)

__all__ = [
    'DatabaseManager',
    'MetricsCollector', 
    'ConfigManager',
    'MessageBus',
    'Message',
    # Canonical types
    'OrderType', 'OrderSide', 'OrderStatus', 'Order', 'Fill', 'TimeInForce', 'ExecutionStrategy',
    'StrategyType', 'StrategyConfig', 'Position', 'MarketRegime', 'RegimeInfo', 'RegimeConfidence', 'RegimeType',
    'AlertLevel', 'PerformanceMetric'
]

__version__ = "1.0.0" 