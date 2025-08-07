"""
Infrastructure layer for StatArb system
Provides core services and utilities for the application
"""

from .database.clickhouse_client import ClickHouseClient
from .monitoring.metrics_collector import MetricsCollector
from .config import UnifiedConfigManager as ConfigManager
from .messaging.message_bus import MessageBus, Message

__all__ = [
    'ClickHouseClient',
    'MetricsCollector', 
    'ConfigManager',
    'MessageBus',
    'Message'
]

__version__ = "1.0.0" 