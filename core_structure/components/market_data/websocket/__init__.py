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

# Import main components - MANDATORY (NO FALLBACKS)
from .websocket_diversification import (
    WebSocketDiversificationManager,
    WebSocketSource,
    SourceConfig,
    SourcePriority,
    DataType
)

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
