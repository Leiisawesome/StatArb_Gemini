"""
Data Brick - Unified Data Flow and Management
==============================================

Provides unified access to market data, alternative data, and data validation
with centralized configuration management (Rule 1, Section 7).

Core Components:
    - ClickHouseDataManager: Primary data access and management
    - LiquidityAssessmentEngine: Liquidity risk assessment
    - DataValidator: Data quality validation and error detection
    - FeedManager: Real-time and historical data feed management

Configuration:
    All configuration centralized in core_engine.config.DataConfig
    Uses composition pattern with sub-configs for modularity.

Architecture Compliance:
    - Rule 1 (Component Integration): All components implement ISystemComponent
    - Rule 3 (Unified Data Flow): Single authority for all data access
    - Rule 7 (Configuration): Centralized DataConfig in core_engine/config/

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Centralized Configuration)
"""

# ============================================================================
# PRIMARY DATA MANAGER (RULE 3: SINGLE DATA AUTHORITY)
# ============================================================================

from .manager import (
    ClickHouseDataManager,
    ClickHouseDataConfig,  # DEPRECATED - use DataConfig from core_engine.config
)

# ============================================================================
# DATA TYPES & ENUMS (RULE 3: UNIFIED DATA FLOW)
# ============================================================================

from core_engine.type_definitions.data import (
    MarketData,
    DataSource,
    DataType,
    DataQuality,
)

# ============================================================================
# DATA FEEDS
# ============================================================================

from .feeds.manager import (
    FeedConfiguration,  # Per-feed config (instance-level, not system-wide)
    FeedManager,
)

from .feeds.adapters import (
    # Configuration
    FeedAdapterConfig,

    # Enums
    AdapterStatus,
    FeedProvider,

    # Data Structures
    FeedMessage,

    # Base Classes
    DataFeedAdapter as BaseFeedAdapter,  # Alias to avoid conflict with sources.market_data.DataFeedAdapter

    # Concrete Adapters
    SimulatedFeedAdapter,
    AlpacaFeedAdapter,
    PolygonFeedAdapter,
    InteractiveBrokersFeedAdapter,

    # Factory
    FeedAdapterFactory,
)

# ============================================================================
# POLYGON.IO REAL-TIME (Production WebSocket)
# ============================================================================

from .feeds.polygon_realtime import (
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

from .feeds.polygon_integration import (
    PolygonServiceConfig,
    PolygonDataService,
    create_polygon_service,
)

from .feeds.polygon_rest import (
    PolygonRestConfig,
    PolygonRestService,
    AggregateBar,
    create_polygon_rest_service,
)

# ============================================================================
# DATA VALIDATION
# ============================================================================

from .validation.validator import (
    ValidationConfiguration,  # DEPRECATED - use DataValidationConfig from core_engine.config
    # DataValidator,  # May need to be added if class exists
)

# ============================================================================
# LIQUIDITY ASSESSMENT
# ============================================================================

from .liquidity_engine import (
    LiquidityRegime,
    LiquidityAssessmentEngine,
)

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # ===== PRIMARY DATA MANAGER =====
    'ClickHouseDataManager',
    'ClickHouseDataConfig',  # DEPRECATED

    # ===== DATA TYPES & ENUMS =====
    'MarketData',
    'DataSource',
    'DataType',
    'DataQuality',

    # ===== DATA FEEDS =====
    'FeedConfiguration',
    'FeedManager',

    # Feed Adapters - Configuration
    'FeedAdapterConfig',
    'AdapterStatus',
    'FeedProvider',
    'FeedMessage',

    # Feed Adapters - Classes
    'BaseFeedAdapter',  # Alias for DataFeedAdapter from feeds.adapters
    'SimulatedFeedAdapter',
    'AlpacaFeedAdapter',
    'PolygonFeedAdapter',
    'InteractiveBrokersFeedAdapter',
    'FeedAdapterFactory',

    # ===== POLYGON.IO REAL-TIME (Production) =====
    'PolygonFeedConfig',
    'PolygonSubscriptionTier',
    'PolygonCluster',
    'PolygonAggregateBar',
    'PolygonTrade',
    'PolygonQuote',
    'PolygonRealtimeFeedAdapter',
    'PolygonAggregatedDataManager',
    'PolygonServiceConfig',
    'PolygonDataService',
    'create_polygon_service',
    # REST API (Stock Starter)
    'PolygonRestConfig',
    'PolygonRestService',
    'AggregateBar',
    'create_polygon_rest_service',

    # ===== DATA VALIDATION =====
    'ValidationConfiguration',  # DEPRECATED

    # ===== LIQUIDITY ASSESSMENT =====
    'LiquidityRegime',
    'LiquidityAssessmentEngine',
]

# ============================================================================
# DEPRECATION NOTICES
# ============================================================================

"""
DEPRECATED CONFIGURATIONS (Rule 1, Section 7):

The following config classes are deprecated and will be removed in a future version.
Please migrate to centralized configuration:

    from core_engine.config import DataConfig

    # Create centralized config
    data_config = DataConfig(
        symbols=['NVDA', 'TSLA', 'AAPL'],
        interval='1min',
        connection=ConnectionConfig(clickhouse_host='localhost'),
        caching=CachingConfig(enable_caching=True),
        validation=DataValidationConfig(quality_threshold=0.95)
    )

DEPRECATED Classes:
    - ClickHouseDataConfig → Use DataConfig from core_engine.config
    - ValidationConfiguration → Use DataValidationConfig from core_engine.config

See: core_engine/config/component_config.py for the new centralized configs.
See: docs/03_compliance_audits/2025-10-21_data_config_analysis.md for migration guide.
"""

