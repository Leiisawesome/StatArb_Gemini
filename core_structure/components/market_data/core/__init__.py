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

# WebSocket diversification
try:
    from .websocket_diversification import (
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
    
    from .websocket_integration import (
        IntegrationConfig,
        MarketDataUpdate,
        WebSocketStrategyIntegration,
        WebSocketPaperTradingIntegration,
        create_websocket_integration
    )
    
    WEBSOCKET_AVAILABLE = True
    
except ImportError:
    WEBSOCKET_AVAILABLE = False

# ClickHouse integration
try:
    from .enhanced_clickhouse_loader import EnhancedClickHouseLoader
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False

# Backtesting data
try:
    from .backtesting_data_provider import BacktestingDataProvider
    BACKTESTING_AVAILABLE = True
except ImportError:
    BACKTESTING_AVAILABLE = False

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
    
    # WebSocket diversification (if available)
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
    
    # WebSocket integration (if available)
    'IntegrationConfig',
    'MarketDataUpdate',
    'WebSocketStrategyIntegration',
    'WebSocketPaperTradingIntegration',
    'create_websocket_integration',
    
    # Availability flags
    'WEBSOCKET_AVAILABLE',
    'CLICKHOUSE_AVAILABLE',
    'BACKTESTING_AVAILABLE'
]
