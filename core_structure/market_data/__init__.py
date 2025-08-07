"""
Enhanced Unified Market Data System
==================================

Professional market data management system consolidating all data functionality:
- ClickHouse integration for high-performance data storage
- Real-time data streaming and processing
- Data quality monitoring and validation
- Market regime detection and liquidity analysis
- AI-ready data preparation and feature engineering
- Unified data management with caching and streaming
"""

from .enhanced_data_manager import (
    EnhancedDataManager,
    DataQualityMonitor,
    DataStreamManager,
    DataCache,
    MarketDataConfig,
    DataQualityThresholds,
    DataStreamConfig
)

# Legacy exports for backward compatibility
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
    'EnhancedDataManager',
    'DataQualityMonitor',
    'DataStreamManager',
    'DataCache',
    'MarketDataConfig',
    'DataQualityThresholds',
    'DataStreamConfig',
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