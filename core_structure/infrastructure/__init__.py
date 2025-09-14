"""
Infrastructure layer for StatArb system
Provides core services and utilities for the application
"""

from core_structure.infrastructure.database.database_system import DatabaseManager
from core_structure.infrastructure.monitoring.monitoring_system import MetricsCollector
from core_structure.infrastructure.config import UnifiedConfigManager as ConfigManager
from core_structure.infrastructure.messaging.messaging_system import MessageBus, Message

# Canonical types to eliminate duplicates
from core_structure.infrastructure.types import (
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