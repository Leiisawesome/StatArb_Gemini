"""
Data Feeds Module - Real-time and Historical Data Feed Management
=================================================================

Provides production-ready feed adapters for various data sources.

Components:
    - FeedManager: Orchestrates multiple data feeds
    - FeedAdapterFactory: Creates type-specific feed adapters
    - DataFeedAdapter: Abstract base for all adapters
    - SimulatedFeedAdapter: Testing adapter with configurable data generation
    - AlpacaFeedAdapter: Alpaca Markets integration
    - PolygonFeedAdapter: Polygon.io integration
    - InteractiveBrokersFeedAdapter: Interactive Brokers integration

Usage:
    from core_engine.data.feeds import FeedAdapterFactory, FeedAdapterConfig
    
    # Create an adapter via factory
    config = FeedAdapterConfig(
        provider="alpaca",
        url="wss://stream.data.alpaca.markets/v2",
        api_key="your-api-key",
        symbols=["NVDA", "TSLA"]
    )
    
    adapter = FeedAdapterFactory.create_adapter(config)
    
    # Connect and subscribe
    await adapter.connect()
    await adapter.subscribe("NVDA")

Architecture Compliance:
    - Rule 1 (Component Integration): All adapters implement ISystemComponent
    - Rule 3 (Unified Data Flow): Consistent interface across all feed types
    - Rule 6 (Error Handling): Comprehensive error handling with circuit breakers

Author: StatArb_Gemini Core Engine
Version: 2.0.0 (Production-Ready Adapters)
"""

from .manager import (
    FeedConfiguration,
    FeedManager,
)

from .adapters import (
    # Configuration
    FeedAdapterConfig,
    
    # Enums
    AdapterStatus,
    FeedProvider,
    
    # Data Structures
    FeedMessage,
    
    # Base Classes
    DataFeedAdapter,
    
    # Concrete Adapters
    SimulatedFeedAdapter,
    AlpacaFeedAdapter,
    PolygonFeedAdapter,
    InteractiveBrokersFeedAdapter,
    
    # Factory
    FeedAdapterFactory,
)

__all__ = [
    # ===== FEED MANAGER =====
    'FeedConfiguration',
    'FeedManager',
    
    # ===== ADAPTER CONFIGURATION =====
    'FeedAdapterConfig',
    
    # ===== ENUMS =====
    'AdapterStatus',
    'FeedProvider',
    
    # ===== DATA STRUCTURES =====
    'FeedMessage',
    
    # ===== BASE CLASSES =====
    'DataFeedAdapter',
    
    # ===== CONCRETE ADAPTERS =====
    'SimulatedFeedAdapter',
    'AlpacaFeedAdapter',
    'PolygonFeedAdapter',
    'InteractiveBrokersFeedAdapter',
    
    # ===== FACTORY =====
    'FeedAdapterFactory',
]
