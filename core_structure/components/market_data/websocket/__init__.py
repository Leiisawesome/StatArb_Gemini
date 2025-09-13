"""
WebSocket Market Data Integration
================================

WebSocket-based market data feeds with multi-source diversification,
automatic failover, and quality monitoring.

Components:
- WebSocket diversification manager
- Multi-source data integration
- Quality monitoring and failover
"""

# Import main components
try:
    from .websocket_diversification import (
        WebSocketDiversificationManager,
        WebSocketSource,
        SourceConfig,
        SourcePriority,
        DataType
    )
except ImportError:
    # Fallback if websocket_diversification is not available
    WebSocketDiversificationManager = None
    WebSocketSource = None
    SourceConfig = None
    SourcePriority = None
    DataType = None

try:
    from .websocket_integration import (
        WebSocketPaperTradingIntegration,
        MarketDataUpdate
    )
    # WebSocketIntegration is not available, so we don't import it
except ImportError:
    WebSocketPaperTradingIntegration = None
    MarketDataUpdate = None

__all__ = [
    # Diversification
    'WebSocketDiversificationManager',
    'WebSocketSource',
    'SourceConfig', 
    'SourcePriority',
    'DataType',
    
    # Integration
    'MarketDataUpdate',
    'WebSocketPaperTradingIntegration'
]
