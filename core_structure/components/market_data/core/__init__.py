"""
Market Data Core Module
======================

Core market data functionality including:
- Data feeds and providers
- WebSocket diversification
- Data validation and monitoring
- ClickHouse integration

Author: StatArb_Gemini
"""

# Core data feeds
from .data_feeds import (
    DataType,
    FeedStatus, 
    DataSource,
    MarketDataPoint,
    FeedMetrics,
    BaseFeed,
    FeedConfig,
    ClickHouseDataProvider
)

# Data management
from .data_manager import DataManager
from .data_validation_monitor import DataValidationMonitor

# WebSocket diversification - MANDATORY (NO FALLBACKS)
from ..websocket.websocket_diversification import (
    WebSocketSource,
    SourcePriority,
    DataQuality,
    SourceConfig,
    SourceMetrics,
    WebSocketMessage,
    WebSocketSourceManager,
    AlpacaWebSocketManager,
    PolygonWebSocketManager,
    WebSocketDiversificationManager,
    create_websocket_diversification_manager
)

from ..websocket.websocket_integration import (
    IntegrationConfig,
    MarketDataUpdate,
    WebSocketStrategyIntegration,
    WebSocketPaperTradingIntegration,
    create_websocket_integration
)

# ClickHouse integration - MANDATORY (NO FALLBACKS)
from .enhanced_clickhouse_loader import EnhancedClickHouseLoader

# Backtesting data - MANDATORY (NO FALLBACKS)
from .backtesting_data_provider import BacktestingDataProvider

__all__ = [
    # Core data feeds
    'DataType',
    'FeedStatus', 
    'DataSource',
    'MarketDataPoint',
    'FeedMetrics',
    'BaseFeed',
    'FeedConfig',
    'ClickHouseDataProvider',
    
    # Data management
    'DataManager',
    'DataValidationMonitor',
    
    # WebSocket diversification
    'WebSocketSource',
    'SourcePriority',
    'DataQuality',
    'SourceConfig',
    'SourceMetrics',
    'WebSocketMessage',
    'WebSocketSourceManager',
    'AlpacaWebSocketManager',
    'PolygonWebSocketManager',
    'WebSocketDiversificationManager',
    'create_websocket_diversification_manager',
    
    # WebSocket integration
    'IntegrationConfig',
    'MarketDataUpdate',
    'WebSocketStrategyIntegration',
    'WebSocketPaperTradingIntegration',
    'create_websocket_integration',
    
    # ClickHouse integration
    'EnhancedClickHouseLoader',
    
    # Backtesting data
    'BacktestingDataProvider'
]
