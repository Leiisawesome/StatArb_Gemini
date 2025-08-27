"""
Infrastructure layer for StatArb system
Provides core services and utilities for the application
"""

from .database.clickhouse_client import ClickHouseClient
from .monitoring.metrics_collector import MetricsCollector
from .config import UnifiedConfigManager as ConfigManager
from .messaging.message_bus import MessageBus, Message

# Canonical types to eliminate duplicates
from .types import (
    OrderType, OrderSide, OrderStatus, Order, Fill, TimeInForce, ExecutionStrategy,
    StrategyType,
    StrategyConfig,
    Position, MarketRegime, RegimeInfo, RegimeConfidence, RegimeType, 
    AlertLevel, PerformanceMetric
)

__all__ = [
    'ClickHouseClient',
    'MetricsCollector', 
    'ConfigManager',
    'MessageBus',
    'Message',
    # Canonical types
    'OrderType', 'OrderSide', 'OrderStatus', 'Order', 'Fill', 'TimeInForce', 'ExecutionStrategy',
    'StrategyConfig', 'MarketRegime', 'RegimeInfo', 'RegimeConfidence', 'RegimeType',
    'AlertLevel', 'PerformanceMetric'
]

__version__ = "1.0.0" 