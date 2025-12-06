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
    - PolygonFeedAdapter: Polygon.io stub (basic)
    - PolygonRealtimeFeedAdapter: Polygon.io production WebSocket adapter
    - InteractiveBrokersFeedAdapter: Interactive Brokers integration

Polygon.io Real-Time Integration:
    For Stock Starter subscription (real-time aggregated data):
    
    from core_engine.data.feeds import (
        PolygonRealtimeFeedAdapter,
        PolygonFeedConfig,
        PolygonSubscriptionTier,
    )
    
    config = PolygonFeedConfig(
        api_key="your_polygon_api_key",
        symbols=["AAPL", "TSLA", "NVDA"],
        subscription_tier=PolygonSubscriptionTier.STARTER,
        data_types=["second_agg", "minute_agg", "trade"],
    )
    
    adapter = PolygonRealtimeFeedAdapter(config)
    await adapter.connect()
    await adapter.subscribe(["AAPL", "TSLA"], ["second_agg", "minute_agg"])

Architecture Compliance:
    - Rule 1 (Component Integration): All adapters implement ISystemComponent
    - Rule 3 (Unified Data Flow): Consistent interface across all feed types
    - Rule 6 (Error Handling): Comprehensive error handling with circuit breakers

Author: StatArb_Gemini Core Engine
Version: 2.1.0 (Production Polygon.io Real-Time)
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
    PolygonFeedAdapter,  # Basic stub
    InteractiveBrokersFeedAdapter,
    
    # Factory
    FeedAdapterFactory,
)

# ============================================================================
# POLYGON.IO REAL-TIME ADAPTER (Production)
# ============================================================================

from .polygon_realtime import (
    # Configuration
    PolygonFeedConfig,
    PolygonSubscriptionTier,
    PolygonCluster,
    
    # Data Structures
    PolygonAggregateBar,
    PolygonTrade,
    PolygonQuote,
    
    # Production Adapter
    PolygonRealtimeFeedAdapter,
    PolygonAggregatedDataManager,
)

# ============================================================================
# POLYGON.IO DATA INTEGRATION SERVICE
# ============================================================================

from .polygon_integration import (
    PolygonServiceConfig,
    PolygonDataService,
    create_polygon_service,
)

# ============================================================================
# POLYGON.IO REST API (Stock Starter - Historical Data)
# ============================================================================

from .polygon_rest import (
    PolygonRestConfig,
    PolygonRestService,
    AggregateBar,
    create_polygon_rest_service,
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
    'PolygonFeedAdapter',  # Basic stub
    'InteractiveBrokersFeedAdapter',
    
    # ===== POLYGON.IO REAL-TIME (Production) =====
    'PolygonFeedConfig',
    'PolygonSubscriptionTier',
    'PolygonCluster',
    'PolygonAggregateBar',
    'PolygonTrade',
    'PolygonQuote',
    'PolygonRealtimeFeedAdapter',
    'PolygonAggregatedDataManager',
    
    # ===== POLYGON.IO DATA SERVICE =====
    'PolygonServiceConfig',
    'PolygonDataService',
    'create_polygon_service',
    
    # ===== POLYGON.IO REST API (Stock Starter) =====
    'PolygonRestConfig',
    'PolygonRestService',
    'AggregateBar',
    'create_polygon_rest_service',
    
    # ===== FACTORY =====
    'FeedAdapterFactory',
]
