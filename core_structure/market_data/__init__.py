"""
Market Data Module
Enhanced market data processing with real-time feeds and AI integration
"""

from .data_manager import DataManager
from .feeds import (
    FeedManager, PolygonFeed, AlphaVantageFeed, 
    MarketTick, DataType, FeedStatus
)

# Note: data_processor imports optional dependencies (ta, sklearn)
# Import only if needed to avoid dependency issues
try:
    from .data_processor import DataProcessor, ProcessedData, ProcessingStage
    DATA_PROCESSOR_AVAILABLE = True
except ImportError as e:
    DATA_PROCESSOR_AVAILABLE = False
    print(f"Data processor not available due to missing dependencies: {e}")

__all__ = [
    'DataManager',
    'FeedManager', 
    'PolygonFeed', 
    'AlphaVantageFeed',
    'MarketTick',
    'DataType', 
    'FeedStatus',
    'DATA_PROCESSOR_AVAILABLE'
]

# Conditionally add data processor exports
if DATA_PROCESSOR_AVAILABLE:
    __all__.extend(['DataProcessor', 'ProcessedData', 'ProcessingStage']) 