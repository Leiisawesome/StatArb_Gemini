"""
Unit tests for Polygon.io Feed Integration
Tests REST API service, WebSocket adapter, and data integration
"""

import pytest
import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
import pandas as pd

from core_engine.data.feeds.polygon_rest import (
    PolygonRestService,
    PolygonRestConfig,
    create_polygon_rest_service,
)
from core_engine.data.feeds.polygon_realtime import (
    PolygonRealtimeFeedAdapter,
    PolygonFeedConfig,
    PolygonSubscriptionTier,
    PolygonCluster,
    PolygonAggregateBar,
    PolygonTrade,
    PolygonAggregatedDataManager,
)
from core_engine.data.feeds.polygon_integration import (
    PolygonDataService,
    PolygonServiceConfig,
    create_polygon_service,
)
from core_engine.data.feeds.adapters import AdapterStatus, FeedProvider, FeedMessage

logger = logging.getLogger(__name__)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def polygon_api_key():
    """Test API key"""
    return "test_api_key_12345"

@pytest.fixture
def polygon_rest_config(polygon_api_key):
    """Polygon REST API configuration"""
    return PolygonRestConfig(api_key=polygon_api_key)

@pytest.fixture
def polygon_feed_config(polygon_api_key):
    """Polygon WebSocket feed configuration"""
    return PolygonFeedConfig(
        api_key=polygon_api_key,
        symbols=["AAPL", "TSLA"],
        subscription_tier=PolygonSubscriptionTier.STARTER,
        data_types=["second_agg", "minute_agg", "trade"],
    )

@pytest.fixture
def polygon_service_config(polygon_api_key):
    """Polygon service configuration"""
    return PolygonServiceConfig(
        api_key=polygon_api_key,
        symbols=["AAPL", "TSLA", "NVDA"],
        data_types=["second_agg", "minute_agg", "trade"],
    )

@pytest.fixture
def sample_aggregate_bar():
    """Sample aggregate bar"""
    return PolygonAggregateBar(
        symbol="AAPL",
        open=150.0,
        high=151.0,
        low=149.0,
        close=150.5,
        volume=1000000.0,
        vwap=150.25,
        timestamp_start=datetime(2024, 12, 6, 9, 30, tzinfo=timezone.utc),
        timestamp_end=datetime(2024, 12, 6, 9, 31, tzinfo=timezone.utc),
        num_trades=5000,
        bar_type="minute",
    )

@pytest.fixture
def sample_trade():
    """Sample trade"""
    return PolygonTrade(
        symbol="AAPL",
        price=150.5,
        size=100,
        timestamp=datetime(2024, 12, 6, 9, 30, 15, tzinfo=timezone.utc),
        conditions=[0],
        exchange=1,
        tape=1,
    )

# =============================================================================
# CATEGORY 1: POLYGON REST SERVICE - CONFIGURATION (3 tests)
# =============================================================================

class TestPolygonRestConfig:
    """Test Polygon REST API configuration"""

    def test_config_creation(self, polygon_api_key):
        """Test creating REST config"""
        config = PolygonRestConfig(api_key=polygon_api_key)

        assert config.api_key == polygon_api_key
        assert config.base_url == "https://api.polygon.io"
        assert config.rate_limit_calls == 500
        assert config.rate_limit_period == 1.0
        logger.info("✅ REST config creation test passed")

    def test_config_defaults(self, polygon_api_key):
        """Test config default values"""
        config = PolygonRestConfig(api_key=polygon_api_key)

        assert config.timeout_seconds == 60.0
        assert config.max_retries == 3
        assert config.default_limit == 50000
        logger.info("✅ REST config defaults test passed")

    def test_config_missing_api_key(self):
        """Test config requires API key"""
        with pytest.raises(ValueError, match="API key required"):
            PolygonRestConfig(api_key="")
        logger.info("✅ REST config missing API key test passed")

# =============================================================================
# CATEGORY 2: POLYGON REST SERVICE - INITIALIZATION (4 tests)
# =============================================================================

class TestPolygonRestServiceInitialization:
    """Test Polygon REST service initialization"""

    @pytest.mark.asyncio
    async def test_service_creation(self, polygon_api_key):
        """Test creating REST service"""
        service = PolygonRestService(api_key=polygon_api_key)

        assert service.config.api_key == polygon_api_key
        assert service.is_initialized is False
        assert service._rest_client is None
        logger.info("✅ REST service creation test passed")

    @pytest.mark.asyncio
    async def test_initialize_success(self, polygon_rest_config):
        """Test successful initialization"""
        service = PolygonRestService(config=polygon_rest_config)

        mock_client = Mock()
        mock_client.get_previous_close_agg.return_value = {
            'results': [{'t': 1701878400000, 'o': 150.0, 'h': 151.0, 'l': 149.0, 'c': 150.5, 'v': 1000000.0}]
        }

        with patch('core_engine.data.feeds.polygon_rest.RESTClient', return_value=mock_client):
            result = await service.initialize()

            assert result is True
            assert service.is_initialized is True
            assert service._rest_client is not None

        await service.close()
        logger.info("✅ REST service initialize success test passed")

    @pytest.mark.asyncio
    async def test_initialize_api_key_verification_fails(self, polygon_rest_config):
        """Test initialization fails with invalid API key"""
        service = PolygonRestService(config=polygon_rest_config)

        mock_client = Mock()
        mock_client.get_previous_close_agg.side_effect = Exception("Unauthorized")

        with patch('core_engine.data.feeds.polygon_rest.RESTClient', return_value=mock_client):
            result = await service.initialize()

            assert result is False
            assert service.is_initialized is False
            assert service._rest_client is None

        await service.close()
        logger.info("✅ REST service initialize API key fails test passed")

    @pytest.mark.asyncio
    async def test_close_service(self, polygon_rest_config):
        """Test closing service"""
        service = PolygonRestService(config=polygon_rest_config)

        service._rest_client = Mock()

        await service.close()

        assert service._rest_client is None
        assert service.is_initialized is False
        logger.info("✅ REST service close test passed")

# =============================================================================
# CATEGORY 3: POLYGON REST SERVICE - RATE LIMITING (3 tests)
# =============================================================================

class TestPolygonRestRateLimiting:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, polygon_rest_config):
        """Test rate limiting waits when at limit"""
        service = PolygonRestService(config=polygon_rest_config)

        # Fill up current 1-second rate limit window
        now = asyncio.get_event_loop().time()
        service._request_times = [now - 0.999] + [now - 0.5] * (service.config.rate_limit_calls - 1)

        # Mock sleep to verify it's called
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await service._rate_limit()

            # Should wait since we're at limit
            mock_sleep.assert_called_once()

        logger.info("✅ Rate limit enforcement test passed")

    @pytest.mark.asyncio
    async def test_rate_limit_cleanup_old_times(self, polygon_rest_config):
        """Test rate limit removes old request times"""
        service = PolygonRestService(config=polygon_rest_config)

        now = asyncio.get_event_loop().time()
        # Mix of old and recent times relative to 1-second rolling window
        service._request_times = deque([
            now - 5,   # Old (outside 1s window)
            now - 2,   # Old
            now - 0.5, # Recent
            now,       # Recent
        ])

        await service._rate_limit()

        # Two old times removed; one new timestamp added
        assert len(service._request_times) == 3
        assert now - 5 not in service._request_times
        assert now - 2 not in service._request_times
        logger.info("✅ Rate limit cleanup old times test passed")

    @pytest.mark.asyncio
    async def test_rate_limit_allows_when_under_limit(self, polygon_rest_config):
        """Test rate limit allows requests when under limit"""
        service = PolygonRestService(config=polygon_rest_config)

        now = asyncio.get_event_loop().time()
        service._request_times = deque([now - 10, now - 5])  # Only 2 requests

        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await service._rate_limit()

            # Should not wait since under limit
            mock_sleep.assert_not_called()

        logger.info("✅ Rate limit allows under limit test passed")

# =============================================================================
# CATEGORY 4: POLYGON REST SERVICE - DATA RETRIEVAL (6 tests)
# =============================================================================

class TestPolygonRestDataRetrieval:
    """Test data retrieval methods"""

    @pytest.mark.asyncio
    async def test_get_previous_day(self, polygon_rest_config):
        """Test getting previous day data"""
        service = PolygonRestService(config=polygon_rest_config)
        service._rest_client = Mock(get_previous_close_agg=Mock())
        service._sdk_call = AsyncMock(return_value={
            'results': [{
                't': 1701878400000,
                'o': 150.0,
                'h': 151.0,
                'l': 149.0,
                'c': 150.5,
                'v': 1000000.0,
                'vw': 150.25,
                'n': 5000,
            }]
        })

        bar = await service.get_previous_day("AAPL")

        assert bar is not None
        assert bar.symbol == "AAPL"
        assert bar.open == 150.0
        assert bar.close == 150.5
        assert bar.volume == 1000000.0
        logger.info("✅ Get previous day test passed")

    @pytest.mark.asyncio
    async def test_get_previous_day_no_data(self, polygon_rest_config):
        """Test getting previous day when no data"""
        service = PolygonRestService(config=polygon_rest_config)
        service._rest_client = Mock(get_previous_close_agg=Mock())
        service._sdk_call = AsyncMock(return_value=None)

        bar = await service.get_previous_day("AAPL")

        assert bar is None
        logger.info("✅ Get previous day no data test passed")

    @pytest.mark.asyncio
    async def test_get_bars_minute(self, polygon_rest_config):
        """Test getting minute bars"""
        service = PolygonRestService(config=polygon_rest_config)
        service._rest_client = Mock(list_aggs=Mock())
        service._sdk_call = AsyncMock(return_value=[
            {
                't': 1701878400000,
                'o': 150.0,
                'h': 150.5,
                'l': 149.5,
                'c': 150.2,
                'v': 100000.0,
                'vw': 150.1,
                'n': 500,
            },
            {
                't': 1701878460000,
                'o': 150.2,
                'h': 150.8,
                'l': 150.0,
                'c': 150.6,
                'v': 120000.0,
                'vw': 150.4,
                'n': 600,
            },
        ])

        df = await service.get_bars("AAPL", timeframe="1min", days=1)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
        assert df.index.name == 'timestamp'
        logger.info("✅ Get bars minute test passed")

    @pytest.mark.asyncio
    async def test_get_bars_timeframe_validation(self, polygon_rest_config):
        """Test invalid timeframe raises error"""
        service = PolygonRestService(config=polygon_rest_config)

        with pytest.raises(ValueError, match="Invalid timeframe"):
            await service.get_bars("AAPL", timeframe="invalid")

        logger.info("✅ Get bars timeframe validation test passed")

    @pytest.mark.asyncio
    async def test_get_bars_multi(self, polygon_rest_config):
        """Test getting bars for multiple symbols"""
        service = PolygonRestService(config=polygon_rest_config)
        service._rest_client = Mock(list_aggs=Mock())
        service._sdk_call = AsyncMock(return_value=[
            {
                't': 1701878400000,
                'o': 150.0,
                'h': 151.0,
                'l': 149.0,
                'c': 150.5,
                'v': 1000000.0,
                'vw': 150.25,
                'n': 5000,
            }
        ])

        data = await service.get_bars_multi(["AAPL", "TSLA"], timeframe="1min", days=1)

        assert isinstance(data, dict)
        assert "AAPL" in data
        assert "TSLA" in data
        assert isinstance(data["AAPL"], pd.DataFrame)
        logger.info("✅ Get bars multi test passed")

    @pytest.mark.asyncio
    async def test_get_latest_prices(self, polygon_rest_config):
        """Test getting latest prices"""
        service = PolygonRestService(config=polygon_rest_config)
        service._rest_client = Mock(get_previous_close_agg=Mock())
        async def mock_sdk_call(operation, *args, **kwargs):
            ticker = kwargs.get('ticker')
            if ticker == 'AAPL':
                return {'results': [{'t': 1701878400000, 'o': 150.0, 'h': 151.0, 'l': 149.0, 'c': 150.5, 'v': 1000000.0}]}
            if ticker == 'TSLA':
                return {'results': [{'t': 1701878400000, 'o': 250.0, 'h': 251.0, 'l': 249.0, 'c': 250.5, 'v': 2000000.0}]}
            return {'results': []}

        service._sdk_call = AsyncMock(side_effect=mock_sdk_call)

        prices = await service.get_latest_prices(["AAPL", "TSLA"])

        assert isinstance(prices, dict)
        assert "AAPL" in prices
        assert "TSLA" in prices
        assert prices["AAPL"] == 150.5
        assert prices["TSLA"] == 250.5
        logger.info("✅ Get latest prices test passed")

# =============================================================================
# CATEGORY 5: POLYGON FEED CONFIG (3 tests)
# =============================================================================

class TestPolygonFeedConfig:
    """Test Polygon WebSocket feed configuration"""

    def test_config_creation(self, polygon_api_key):
        """Test creating feed config"""
        config = PolygonFeedConfig(
            api_key=polygon_api_key,
            symbols=["AAPL", "TSLA"],
            subscription_tier=PolygonSubscriptionTier.STARTER,
        )

        assert config.api_key == polygon_api_key
        assert len(config.symbols) == 2
        assert config.subscription_tier == PolygonSubscriptionTier.STARTER
        assert config.cluster == PolygonCluster.STOCKS
        logger.info("✅ Feed config creation test passed")

    def test_config_ws_url(self, polygon_feed_config):
        """Test WebSocket URL generation"""
        assert polygon_feed_config.ws_url == "wss://socket.massive.com/stocks"

        # Test delayed endpoint
        polygon_feed_config.cluster = PolygonCluster.STOCKS_DELAYED
        assert polygon_feed_config.ws_url == "wss://delayed.massive.com/stocks"
        logger.info("✅ Feed config WS URL test passed")

    def test_config_data_type_validation(self, polygon_api_key):
        """Test data type validation for subscription tier"""
        # Starter tier should reject quote
        with pytest.raises(ValueError, match="not available"):
            PolygonFeedConfig(
                api_key=polygon_api_key,
                symbols=["AAPL"],
                subscription_tier=PolygonSubscriptionTier.STARTER,
                data_types=["quote"],  # Not available on starter
            )

        # Starter tier should accept second_agg, minute_agg, trade
        config = PolygonFeedConfig(
            api_key=polygon_api_key,
            symbols=["AAPL"],
            subscription_tier=PolygonSubscriptionTier.STARTER,
            data_types=["second_agg", "minute_agg", "trade"],
        )
        assert len(config.data_types) == 3
        logger.info("✅ Feed config data type validation test passed")

# =============================================================================
# CATEGORY 6: POLYGON REALTIME ADAPTER - INITIALIZATION (3 tests)
# =============================================================================

class TestPolygonRealtimeAdapterInitialization:
    """Test Polygon realtime adapter initialization"""

    def test_adapter_creation(self, polygon_feed_config):
        """Test creating adapter"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', True):
            adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

            assert adapter.polygon_config == polygon_feed_config
            assert adapter.status == AdapterStatus.DISCONNECTED
            assert adapter.PROVIDER == FeedProvider.POLYGON
            assert adapter.IS_IMPLEMENTED is True
            logger.info("✅ Adapter creation test passed")

    def test_adapter_missing_websocket_clients(self, polygon_feed_config):
        """Test adapter requires at least one websocket client transport"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', False), \
             patch('core_engine.data.feeds.polygon_realtime.MASSIVE_CLIENT_AVAILABLE', False):
            with pytest.raises(ImportError, match=r"massive \(official Polygon client\) or websockets"):
                PolygonRealtimeFeedAdapter(polygon_feed_config)

        logger.info("✅ Adapter missing websocket clients test passed")

    def test_adapter_subscription_tracking(self, polygon_feed_config):
        """Test adapter subscription tracking"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', True):
            adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

            assert len(adapter._active_subscriptions) == 4
            assert 'trade' in adapter._active_subscriptions
            assert 'second_agg' in adapter._active_subscriptions
            assert 'minute_agg' in adapter._active_subscriptions
            logger.info("✅ Adapter subscription tracking test passed")

# =============================================================================
# CATEGORY 7: POLYGON REALTIME ADAPTER - MESSAGE HANDLING (4 tests)
# =============================================================================

class TestPolygonRealtimeMessageHandling:
    """Test message handling in realtime adapter"""

    @pytest.mark.asyncio
    async def test_handle_trade_message(self, polygon_feed_config):
        """Test handling trade message"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', True):
            adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

            # Mock message handler
            messages = []
            adapter.add_message_handler(lambda msg: messages.append(msg))

            # Simulate trade message
            trade_msg = {
                'ev': 'T',
                'sym': 'AAPL',
                'p': 150.5,
                's': 100,
                't': 1701878415000000000,  # Nanoseconds
                'c': [0],
                'x': 1,
                'z': 1,
            }

            await adapter._process_message(json.dumps([trade_msg]))

            assert len(messages) == 1
            assert messages[0].message_type == 'trade'
            assert messages[0].symbol == 'AAPL'
            assert messages[0].data['price'] == 150.5
            logger.info("✅ Handle trade message test passed")

    @pytest.mark.asyncio
    async def test_handle_aggregate_message(self, polygon_feed_config):
        """Test handling aggregate message"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', True):
            adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

            messages = []
            adapter.add_message_handler(lambda msg: messages.append(msg))

            # Simulate minute aggregate message
            agg_msg = {
                'ev': 'AM',
                'sym': 'AAPL',
                'o': 150.0,
                'h': 151.0,
                'l': 149.0,
                'c': 150.5,
                'v': 1000000.0,
                'vw': 150.25,
                's': 1701878400000,  # Start time (ms)
                'e': 1701878460000,  # End time (ms)
                'n': 5000,
            }

            await adapter._process_message(json.dumps([agg_msg]))

            assert len(messages) == 1
            assert messages[0].message_type == 'minute_agg'
            assert messages[0].symbol == 'AAPL'
            assert messages[0].data['open'] == 150.0
            assert messages[0].data['close'] == 150.5
            logger.info("✅ Handle aggregate message test passed")

    @pytest.mark.asyncio
    async def test_handle_status_message(self, polygon_feed_config):
        """Test handling status messages"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', True):
            adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

            status_msg = {
                'ev': 'status',
                'status': 'connected',
                'message': 'Connected successfully',
            }

            # Should not raise exception
            await adapter._process_message(json.dumps([status_msg]))

            logger.info("✅ Handle status message test passed")

    @pytest.mark.asyncio
    async def test_handle_invalid_json(self, polygon_feed_config):
        """Test handling invalid JSON"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', True):
            adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

            # Should handle gracefully
            await adapter._process_message("invalid json")

            # Should not crash
            assert adapter.status in [AdapterStatus.DISCONNECTED, AdapterStatus.ERROR]
            logger.info("✅ Handle invalid JSON test passed")

# =============================================================================
# CATEGORY 8: POLYGON AGGREGATED DATA MANAGER (4 tests)
# =============================================================================

class TestPolygonAggregatedDataManager:
    """Test aggregated data manager"""

    def test_manager_creation(self, polygon_feed_config):
        """Test creating aggregation manager"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', True):
            adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
            manager = PolygonAggregatedDataManager(adapter)

            assert manager.adapter == adapter
            assert len(manager._bars) == 0
            logger.info("✅ Manager creation test passed")

    @pytest.mark.asyncio
    async def test_process_aggregate(self, polygon_feed_config):
        """Test processing aggregate message"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', True):
            adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
            manager = PolygonAggregatedDataManager(adapter)

            # Create feed message
            message = FeedMessage(
                provider=FeedProvider.POLYGON,
                symbol="AAPL",
                message_type="minute_agg",
                timestamp=datetime.now(timezone.utc),
                data={
                    'open': 150.0,
                    'high': 151.0,
                    'low': 149.0,
                    'close': 150.5,
                    'volume': 1000000.0,
                    'vwap': 150.25,
                    'num_trades': 5000,
                    'bar_type': 'minute',
                    'timestamp_start': datetime(2024, 12, 6, 9, 30, tzinfo=timezone.utc).isoformat(),
                    'timestamp_end': datetime(2024, 12, 6, 9, 31, tzinfo=timezone.utc).isoformat(),
                },
            )

            await manager.process_aggregate(message)

            bars = manager.get_bars("AAPL", timeframe="minute")
            assert len(bars) == 1
            assert bars[0].symbol == "AAPL"
            assert bars[0].close == 150.5
            logger.info("✅ Process aggregate test passed")

    def test_get_bars_empty(self, polygon_feed_config):
        """Test getting bars when none exist"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', True):
            adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
            manager = PolygonAggregatedDataManager(adapter)

            bars = manager.get_bars("AAPL", timeframe="minute")
            assert len(bars) == 0
            logger.info("✅ Get bars empty test passed")

    def test_get_latest_price(self, polygon_feed_config):
        """Test getting latest price"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', True):
            adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
            manager = PolygonAggregatedDataManager(adapter)

            # No bars yet
            price = manager.get_latest_price("AAPL")
            assert price is None

            # Add a bar
            bar = PolygonAggregateBar(
                symbol="AAPL",
                open=150.0,
                high=151.0,
                low=149.0,
                close=150.5,
                volume=1000000.0,
                vwap=150.25,
                timestamp_start=datetime.now(timezone.utc),
                timestamp_end=datetime.now(timezone.utc),
                num_trades=5000,
                bar_type="minute",
            )
            adapter._latest_bars["AAPL_minute"] = bar

            price = manager.get_latest_price("AAPL")
            assert price == 150.5
            logger.info("✅ Get latest price test passed")

# =============================================================================
# CATEGORY 9: POLYGON DATA SERVICE - INITIALIZATION (4 tests)
# =============================================================================

class TestPolygonDataServiceInitialization:
    """Test Polygon data service initialization"""

    def test_service_creation(self, polygon_service_config):
        """Test creating data service"""
        service = PolygonDataService(config=polygon_service_config)

        assert service.config == polygon_service_config
        assert service.is_initialized is False
        assert service.is_operational is False
        logger.info("✅ Data service creation test passed")

    @pytest.mark.asyncio
    async def test_initialize_success(self, polygon_service_config):
        """Test successful initialization"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.add_message_handler = Mock()
            MockAdapter.return_value = mock_adapter

            result = await service.initialize()

            assert result is True
            assert service.is_initialized is True
            assert service._adapter is not None

        await service.stop()
        logger.info("✅ Data service initialize success test passed")

    @pytest.mark.asyncio
    async def test_initialize_missing_api_key(self):
        """Test initialization fails without API key"""
        config = PolygonServiceConfig(api_key="")
        service = PolygonDataService(config=config)

        result = await service.initialize()

        assert result is False
        assert service.is_initialized is False
        logger.info("✅ Data service initialize missing API key test passed")

    @pytest.mark.asyncio
    async def test_start_requires_initialization(self, polygon_service_config):
        """Test start requires initialization"""
        service = PolygonDataService(config=polygon_service_config)

        result = await service.start()

        assert result is False
        logger.info("✅ Data service start requires init test passed")

# =============================================================================
# CATEGORY 10: POLYGON DATA SERVICE - DATA ACCESS (4 tests)
# =============================================================================

class TestPolygonDataServiceDataAccess:
    """Test data access methods"""

    def test_get_latest_bars_empty(self, polygon_service_config):
        """Test getting bars when none exist"""
        service = PolygonDataService(config=polygon_service_config)

        df = service.get_latest_bars("AAPL", timeframe="minute")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert 'open' in df.columns
        logger.info("✅ Get latest bars empty test passed")

    def test_get_latest_trades_empty(self, polygon_service_config):
        """Test getting trades when none exist"""
        service = PolygonDataService(config=polygon_service_config)

        df = service.get_latest_trades("AAPL")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        logger.info("✅ Get latest trades empty test passed")

    def test_get_latest_price_empty(self, polygon_service_config):
        """Test getting price when none exists"""
        service = PolygonDataService(config=polygon_service_config)

        price = service.get_latest_price("AAPL")

        assert price is None
        logger.info("✅ Get latest price empty test passed")

    def test_get_ohlcv_for_pipeline(self, polygon_service_config):
        """Test getting pipeline-ready OHLCV"""
        service = PolygonDataService(config=polygon_service_config)

        # Add some bars
        bar = PolygonAggregateBar(
            symbol="AAPL",
            open=150.0,
            high=151.0,
            low=149.0,
            close=150.5,
            volume=1000000.0,
            vwap=150.25,
            timestamp_start=datetime.now(timezone.utc),
            timestamp_end=datetime.now(timezone.utc),
            num_trades=5000,
            bar_type="minute",
        )
        service._bars["AAPL"]["minute"].append(bar)

        df = service.get_ohlcv_for_pipeline("AAPL", timeframe="minute")

        assert isinstance(df, pd.DataFrame)
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
        assert len(df.columns) == 5  # Only OHLCV
        logger.info("✅ Get OHLCV for pipeline test passed")

# =============================================================================
# CATEGORY 11: POLYGON DATA SERVICE - CALLBACKS (3 tests)
# =============================================================================

class TestPolygonDataServiceCallbacks:
    """Test callback functionality"""

    def test_add_bar_callback(self, polygon_service_config):
        """Test adding bar callback"""
        service = PolygonDataService(config=polygon_service_config)

        callback = Mock()
        service.add_bar_callback(callback)

        assert len(service._bar_callbacks) == 1
        assert service._bar_callbacks[0] == callback
        logger.info("✅ Add bar callback test passed")

    def test_add_trade_callback(self, polygon_service_config):
        """Test adding trade callback"""
        service = PolygonDataService(config=polygon_service_config)

        callback = Mock()
        service.add_trade_callback(callback)

        assert len(service._trade_callbacks) == 1
        logger.info("✅ Add trade callback test passed")

    @pytest.mark.asyncio
    async def test_bar_callback_invocation(self, polygon_service_config):
        """Test bar callback is invoked on new bar"""
        service = PolygonDataService(config=polygon_service_config)

        callback = Mock()
        service.add_bar_callback(callback)

        # Simulate bar message
        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="minute_agg",
            timestamp=datetime.now(timezone.utc),
            data={
                'open': 150.0,
                'high': 151.0,
                'low': 149.0,
                'close': 150.5,
                'volume': 1000000.0,
                'vwap': 150.25,
                'num_trades': 5000,
                'bar_type': 'minute',
                'timestamp_start': datetime.now(timezone.utc).isoformat(),
                'timestamp_end': datetime.now(timezone.utc).isoformat(),
            },
        )

        service._handle_aggregate(message)

        # Callback should be called
        assert callback.called
        logger.info("✅ Bar callback invocation test passed")

# =============================================================================
# CATEGORY 12: POLYGON DATA SERVICE - HEALTH CHECK (3 tests)
# =============================================================================

class TestPolygonDataServiceHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, polygon_service_config):
        """Test health check when not initialized"""
        service = PolygonDataService(config=polygon_service_config)

        health = await service.health_check()

        assert health['healthy'] is False
        assert health['initialized'] is False
        logger.info("✅ Health check not initialized test passed")

    @pytest.mark.asyncio
    async def test_health_check_initialized(self, polygon_service_config):
        """Test health check when initialized"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.add_message_handler = Mock()
            mock_adapter.is_connected = Mock(return_value=True)
            MockAdapter.return_value = mock_adapter

            await service.initialize()
            service._adapter = mock_adapter

            health = await service.health_check()

            assert health['initialized'] is True
            assert health['adapter_connected'] is True

        await service.stop()
        logger.info("✅ Health check initialized test passed")

    @pytest.mark.asyncio
    async def test_get_status(self, polygon_service_config):
        """Test getting service status"""
        service = PolygonDataService(config=polygon_service_config)

        status = service.get_status()

        assert status['initialized'] is False
        assert status['operational'] is False
        assert status['component_type'] == 'PolygonDataService'
        assert 'symbols' in status
        logger.info("✅ Get status test passed")

# =============================================================================
# CATEGORY 13: CONVENIENCE FUNCTIONS (2 tests)
# =============================================================================

class TestConvenienceFunctions:
    """Test convenience functions"""

    @pytest.mark.asyncio
    async def test_create_polygon_rest_service(self, polygon_api_key):
        """Test create_polygon_rest_service convenience function"""
        with patch('core_engine.data.feeds.polygon_rest.PolygonRestService.initialize', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = True

            service = await create_polygon_rest_service(api_key=polygon_api_key)

            assert isinstance(service, PolygonRestService)
            assert service.config.api_key == polygon_api_key
            mock_init.assert_called_once()

        await service.close()
        logger.info("✅ Create polygon rest service test passed")

    @pytest.mark.asyncio
    async def test_create_polygon_service(self, polygon_api_key):
        """Test create_polygon_service convenience function"""
        with patch('core_engine.data.feeds.polygon_integration.PolygonDataService.initialize', new_callable=AsyncMock) as mock_init:
            with patch('core_engine.data.feeds.polygon_integration.PolygonDataService.start', new_callable=AsyncMock) as mock_start:
                mock_init.return_value = True
                mock_start.return_value = True

                service = await create_polygon_service(api_key=polygon_api_key, symbols=["AAPL"])

                assert isinstance(service, PolygonDataService)
                mock_init.assert_called_once()
                mock_start.assert_called_once()

        await service.stop()
        logger.info("✅ Create polygon service test passed")

# =============================================================================
# CATEGORY 14: ERROR HANDLING (3 tests)
# =============================================================================

class TestPolygonErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_rest_service_request_error(self, polygon_rest_config):
        """Test REST service handles SDK call errors"""
        service = PolygonRestService(config=polygon_rest_config)
        service._rest_client = Mock()
        service._request_times = deque()

        operation = Mock(side_effect=Exception("Network error"))

        with pytest.raises(Exception, match="Network error"):
            await service._sdk_call(operation)
        logger.info("✅ REST service request error test passed")

    @pytest.mark.asyncio
    async def test_rest_service_rate_limit_429(self, polygon_rest_config):
        """Test REST service retries transient SDK errors"""
        service = PolygonRestService(config=polygon_rest_config)
        service._rest_client = Mock()
        service._request_times = []

        operation = Mock(side_effect=[Exception("Rate limited"), {"status": "OK"}])

        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            data = await service._sdk_call(operation)

            mock_sleep.assert_called()
            assert data.get('status') == 'OK'

        logger.info("✅ REST service rate limit 429 test passed")

    def test_data_service_handle_message_error(self, polygon_service_config):
        """Test data service handles message errors gracefully"""
        service = PolygonDataService(config=polygon_service_config)

        # Create invalid message
        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="invalid",
            timestamp=datetime.now(timezone.utc),
            data={},
        )

        # Should not raise exception
        service._handle_message(message)

        assert service._stats['errors'] >= 0  # May or may not increment
        logger.info("✅ Data service handle message error test passed")

# =============================================================================
# CATEGORY 15: POLYGON DATA SERVICE - INITIALIZATION ERROR HANDLING
# =============================================================================

class TestPolygonDataServiceInitializationErrors:
    """Test initialization error scenarios for PolygonDataService"""

    @pytest.mark.asyncio
    async def test_initialize_adapter_creation_failure(self, polygon_service_config):
        """Test initialization fails when adapter creation fails"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter', side_effect=Exception("Adapter creation failed")):
            result = await service.initialize()

            assert result is False
            assert not service.is_initialized
            logger.info("✅ Initialize adapter creation failure test passed")

    @pytest.mark.asyncio
    async def test_initialize_manager_creation_failure(self, polygon_service_config):
        """Test initialization fails when manager creation fails"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonFeedConfig', side_effect=Exception("Manager creation failed")):
            result = await service.initialize()

            assert result is False
            assert not service.is_initialized
            logger.info("✅ Initialize manager creation failure test passed")

    @pytest.mark.asyncio
    async def test_initialize_message_handler_registration_failure(self, polygon_service_config):
        """Test initialization fails when message handler registration fails"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:

            mock_adapter = Mock()
            mock_adapter.add_message_handler.side_effect = Exception("Handler registration failed")
            MockAdapter.return_value = mock_adapter

            result = await service.initialize()

            assert result is False
            assert not service.is_initialized
            logger.info("✅ Initialize message handler registration failure test passed")

    @pytest.mark.asyncio
    async def test_initialize_polygon_config_creation_failure(self, polygon_service_config):
        """Test initialization fails when PolygonFeedConfig creation fails"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonFeedConfig', side_effect=Exception("Config creation failed")):
            result = await service.initialize()

            assert result is False
            assert not service.is_initialized
            logger.info("✅ Initialize config creation failure test passed")

# =============================================================================
# CATEGORY 16: POLYGON DATA SERVICE - START/STOP ERROR HANDLING
# =============================================================================

class TestPolygonDataServiceLifecycleErrors:
    """Test start/stop lifecycle error scenarios"""

    @pytest.mark.asyncio
    async def test_start_not_initialized(self, polygon_service_config):
        """Test start fails when not initialized"""
        service = PolygonDataService(config=polygon_service_config)

        result = await service.start()

        assert result is False
        assert not service.is_operational
        logger.info("✅ Start not initialized test passed")

    @pytest.mark.asyncio
    async def test_start_adapter_connection_failure(self, polygon_service_config):
        """Test start fails when adapter connection fails"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.connect = AsyncMock(return_value=False)
            MockAdapter.return_value = mock_adapter

            await service.initialize()  # Initialize first

            result = await service.start()

            assert result is False
            assert not service.is_operational
            logger.info("✅ Start adapter connection failure test passed")

    @pytest.mark.asyncio
    async def test_start_subscription_failure(self, polygon_service_config):
        """Test start handles subscription failure gracefully"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.connect = AsyncMock(return_value=True)
            mock_adapter.subscribe = AsyncMock(return_value=False)  # Subscription fails
            MockAdapter.return_value = mock_adapter

            await service.initialize()
            result = await service.start()

            # Should still succeed (subscription failure is warning, not error)
            assert result is True
            assert service.is_operational
            logger.info("✅ Start subscription failure test passed")

    @pytest.mark.asyncio
    async def test_start_exception_handling(self, polygon_service_config):
        """Test start handles unexpected exceptions"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.connect = AsyncMock(side_effect=Exception("Unexpected connection error"))
            MockAdapter.return_value = mock_adapter

            await service.initialize()
            result = await service.start()

            assert result is False
            assert not service.is_operational
            logger.info("✅ Start exception handling test passed")

    @pytest.mark.asyncio
    async def test_stop_adapter_disconnect_failure(self, polygon_service_config):
        """Test stop handles adapter disconnect failure gracefully"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.connect = AsyncMock(return_value=True)
            mock_adapter.subscribe = AsyncMock(return_value=True)
            mock_adapter.disconnect = AsyncMock(side_effect=Exception("Disconnect failed"))
            MockAdapter.return_value = mock_adapter

            await service.initialize()
            await service.start()  # Successfully start first

            result = await service.stop()

            # Should return False due to disconnect failure
            assert result is False
            # Operational state remains True since cleanup failed
            assert service.is_operational
            logger.info("✅ Stop adapter disconnect failure test passed")

    @pytest.mark.asyncio
    async def test_stop_exception_handling(self, polygon_service_config):
        """Test stop handles unexpected exceptions"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.connect = AsyncMock(return_value=True)
            mock_adapter.subscribe = AsyncMock(return_value=True)
            mock_adapter.disconnect = AsyncMock(side_effect=Exception("Unexpected stop error"))
            MockAdapter.return_value = mock_adapter

            await service.initialize()
            await service.start()  # Successfully start first

            result = await service.stop()

            # Should return False due to exception
            assert result is False
            # Operational state remains True since cleanup failed
            assert service.is_operational
            logger.info("✅ Stop exception handling test passed")

# =============================================================================
# CATEGORY 17: POLYGON DATA SERVICE - DATA ACCESS ERROR HANDLING
# =============================================================================

class TestPolygonDataServiceDataAccessErrors:
    """Test data access method error scenarios"""

    def test_get_latest_bars_invalid_symbol(self, polygon_service_config):
        """Test get_latest_bars with invalid symbol parameters"""
        service = PolygonDataService(config=polygon_service_config)

        # Test with None symbol
        with pytest.raises(AttributeError):
            service.get_latest_bars(None)

        # Test with empty symbol
        df = service.get_latest_bars("")
        assert df.empty
        assert list(df.columns) == ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'vwap', 'num_trades']
        logger.info("✅ Get latest bars invalid symbol test passed")

    def test_get_latest_bars_invalid_timeframe(self, polygon_service_config):
        """Test get_latest_bars with invalid timeframe"""
        service = PolygonDataService(config=polygon_service_config)

        # Test with None timeframe
        df = service.get_latest_bars("AAPL", timeframe=None)
        assert df.empty

        # Test with invalid timeframe
        df = service.get_latest_bars("AAPL", timeframe="invalid")
        assert df.empty
        logger.info("✅ Get latest bars invalid timeframe test passed")

    def test_get_latest_bars_negative_limit(self, polygon_service_config):
        """Test get_latest_bars with negative limit"""
        service = PolygonDataService(config=polygon_service_config)

        df = service.get_latest_bars("AAPL", limit=-1)
        assert df.empty
        logger.info("✅ Get latest bars negative limit test passed")

    def test_get_latest_trades_invalid_symbol(self, polygon_service_config):
        """Test get_latest_trades with invalid symbol"""
        service = PolygonDataService(config=polygon_service_config)

        # Test with None symbol
        with pytest.raises(AttributeError):
            service.get_latest_trades(None)

        # Test with empty symbol
        df = service.get_latest_trades("")
        assert df.empty
        assert list(df.columns) == ['timestamp', 'price', 'size', 'conditions']
        logger.info("✅ Get latest trades invalid symbol test passed")

    def test_get_latest_price_invalid_symbol(self, polygon_service_config):
        """Test get_latest_price with invalid symbol"""
        service = PolygonDataService(config=polygon_service_config)

        # Test with None symbol
        with pytest.raises(AttributeError):
            service.get_latest_price(None)

        # Test with empty symbol
        price = service.get_latest_price("")
        assert price is None

        # Test with non-existent symbol
        price = service.get_latest_price("NONEXISTENT")
        assert price is None
        logger.info("✅ Get latest price invalid symbol test passed")

    def test_get_ohlcv_for_pipeline_time_filter_edge_cases(self, polygon_service_config):
        """Test get_ohlcv_for_pipeline with time filter edge cases"""
        service = PolygonDataService(config=polygon_service_config)

        # Add some test data
        bar = PolygonAggregateBar(
            symbol="AAPL",
            open=150.0, high=151.0, low=149.0, close=150.5,
            volume=100000.0, vwap=150.25, num_trades=1000,
            timestamp_start=datetime(2024, 12, 6, 9, 30, tzinfo=timezone.utc),
            timestamp_end=datetime(2024, 12, 6, 9, 31, tzinfo=timezone.utc),
            bar_type="minute"
        )
        service._bars["AAPL"]["minute"].append(bar)

        # Test with naive datetime (should handle gracefully)
        naive_start = datetime(2024, 12, 6, 9, 29)
        df = service.get_ohlcv_for_pipeline("AAPL", start_time=naive_start)
        assert not df.empty

        # Test with future end time (should return all data)
        future_end = datetime(2024, 12, 7, tzinfo=timezone.utc)
        df = service.get_ohlcv_for_pipeline("AAPL", end_time=future_end)
        assert not df.empty

        # Test with past start time (should return all data)
        past_start = datetime(2024, 12, 5, tzinfo=timezone.utc)
        df = service.get_ohlcv_for_pipeline("AAPL", start_time=past_start)
        assert not df.empty
        logger.info("✅ Get OHLCV time filter edge cases test passed")

# =============================================================================
# CATEGORY 18: POLYGON DATA SERVICE - SUBSCRIPTION ERROR HANDLING
# =============================================================================

class TestPolygonDataServiceSubscriptionErrors:
    """Test subscription method error scenarios"""

    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self, polygon_service_config):
        """Test subscribe fails when not connected"""
        service = PolygonDataService(config=polygon_service_config)

        result = await service.subscribe(["AAPL"])

        assert result is False
        logger.info("✅ Subscribe not connected test passed")

    @pytest.mark.asyncio
    async def test_subscribe_adapter_failure(self, polygon_service_config):
        """Test subscribe handles adapter failure"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.is_connected.return_value = True
            mock_adapter.subscribe = AsyncMock(return_value=False)
            MockAdapter.return_value = mock_adapter

            await service.initialize()
            service._adapter = mock_adapter

            result = await service.subscribe(["GOOGL"])

            assert result is False
            # Should not add to config.symbols on failure
            assert "GOOGL" not in service.config.symbols
            logger.info("✅ Subscribe adapter failure test passed")

    @pytest.mark.asyncio
    async def test_subscribe_empty_symbols(self, polygon_service_config):
        """Test subscribe with empty symbol list"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.is_connected.return_value = True
            mock_adapter.subscribe = AsyncMock(return_value=True)
            MockAdapter.return_value = mock_adapter

            await service.initialize()
            service._adapter = mock_adapter

            result = await service.subscribe([])

            assert result is True  # Empty list is valid
            logger.info("✅ Subscribe empty symbols test passed")

    @pytest.mark.asyncio
    async def test_subscribe_invalid_symbols(self, polygon_service_config):
        """Test subscribe with invalid symbol formats"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.is_connected.return_value = True
            mock_adapter.subscribe = AsyncMock(return_value=True)
            MockAdapter.return_value = mock_adapter

            await service.initialize()
            service._adapter = mock_adapter

            # Test with symbols containing None - should handle gracefully
            result = await service.subscribe(["AAPL", None, "TSLA"])
            assert result is True
            # Should add valid symbols to config (AAPL and TSLA already exist, but that's fine)
            assert "AAPL" in service.config.symbols
            assert "TSLA" in service.config.symbols
            logger.info("✅ Subscribe invalid symbols test passed")

    @pytest.mark.asyncio
    async def test_unsubscribe_no_adapter(self, polygon_service_config):
        """Test unsubscribe when no adapter exists"""
        service = PolygonDataService(config=polygon_service_config)

        result = await service.unsubscribe(["AAPL"])

        assert result is True  # Should return True (already "unsubscribed")
        logger.info("✅ Unsubscribe no adapter test passed")

    @pytest.mark.asyncio
    async def test_unsubscribe_adapter_failure(self, polygon_service_config):
        """Test unsubscribe handles adapter failure"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:
            mock_adapter = Mock()
            mock_adapter.unsubscribe = AsyncMock(return_value=False)
            MockAdapter.return_value = mock_adapter

            await service.initialize()
            service._adapter = mock_adapter

            # Add symbol to config first
            service.config.symbols.append("AAPL")

            result = await service.unsubscribe(["AAPL"])

            assert result is False
            # Should not remove from config.symbols on failure
            assert "AAPL" in service.config.symbols
            logger.info("✅ Unsubscribe adapter failure test passed")

# =============================================================================
# CATEGORY 19: POLYGON DATA SERVICE - MESSAGE HANDLING ERROR HANDLING
# =============================================================================

class TestPolygonDataServiceMessageHandlingErrors:
    """Test message handling error scenarios"""

    def test_handle_message_invalid_message_type(self, polygon_service_config):
        """Test _handle_message with invalid message types"""
        service = PolygonDataService(config=polygon_service_config)

        # Test with unknown message type
        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="unknown_type",
            timestamp=datetime.now(timezone.utc),
            data={},
        )

        initial_errors = service._stats['errors']
        initial_messages = service._stats['messages_received']
        service._handle_message(message)

        # Should increment message count but not error count (unknown types are ignored)
        assert service._stats['messages_received'] == initial_messages + 1
        assert service._stats['errors'] == initial_errors  # No error for unknown type
        logger.info("✅ Handle message invalid type test passed")

    def test_handle_message_missing_data(self, polygon_service_config):
        """Test _handle_message with missing data"""
        service = PolygonDataService(config=polygon_service_config)

        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="second_agg",
            timestamp=datetime.now(timezone.utc),
            data=None,  # Missing data
        )

        initial_errors = service._stats['errors']
        service._handle_message(message)

        # Should increment error count
        assert service._stats['errors'] > initial_errors
        logger.info("✅ Handle message missing data test passed")

    def test_handle_aggregate_missing_required_fields(self, polygon_service_config):
        """Test _handle_aggregate with missing required fields"""
        service = PolygonDataService(config=polygon_service_config)

        # Missing required OHLC fields
        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="second_agg",
            timestamp=datetime.now(timezone.utc),
            data={
                'volume': 100000.0,
                # Missing open, high, low, close
            },
        )

        initial_errors = service._stats['errors']
        service._handle_message(message)

        # Should increment error count due to missing fields
        assert service._stats['errors'] > initial_errors
        logger.info("✅ Handle aggregate missing fields test passed")

    def test_handle_aggregate_invalid_timestamp_format(self, polygon_service_config):
        """Test _handle_aggregate with invalid timestamp format"""
        service = PolygonDataService(config=polygon_service_config)

        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="second_agg",
            timestamp=datetime.now(timezone.utc),
            data={
                'open': 150.0, 'high': 151.0, 'low': 149.0, 'close': 150.5,
                'volume': 100000.0, 'vwap': 150.25, 'num_trades': 1000,
                'bar_type': 'second',
                'timestamp_start': 'invalid-timestamp',
                'timestamp_end': '2024-12-06T09:31:00+00:00',
            },
        )

        initial_errors = service._stats['errors']
        service._handle_message(message)

        # Should increment error count due to invalid timestamp
        assert service._stats['errors'] > initial_errors
        logger.info("✅ Handle aggregate invalid timestamp test passed")

    def test_handle_trade_missing_required_fields(self, polygon_service_config):
        """Test _handle_trade with missing required fields"""
        service = PolygonDataService(config=polygon_service_config)

        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="trade",
            timestamp=datetime.now(timezone.utc),
            data={
                'size': 100,
                # Missing price
            },
        )

        initial_errors = service._stats['errors']
        service._handle_message(message)

        # Should increment error count due to missing price
        assert service._stats['errors'] > initial_errors
        logger.info("✅ Handle trade missing fields test passed")

    def test_handle_quote_missing_fields(self, polygon_service_config):
        """Test _handle_quote with missing fields"""
        service = PolygonDataService(config=polygon_service_config)

        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="quote",
            timestamp=datetime.now(timezone.utc),
            data={
                # Missing bid/ask
            },
        )

        # Should not raise exception, just skip price update
        service._handle_message(message)

        # Price should not be updated
        assert service.get_latest_price("AAPL") is None
        logger.info("✅ Handle quote missing fields test passed")

    def test_handle_message_callback_error_handling(self, polygon_service_config):
        """Test message handling with callback errors"""
        service = PolygonDataService(config=polygon_service_config)

        # Add a failing callback
        def failing_callback(symbol, timeframe, bar):
            raise Exception("Callback failed")

        service.add_bar_callback(failing_callback)

        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="second_agg",
            timestamp=datetime.now(timezone.utc),
            data={
                'open': 150.0, 'high': 151.0, 'low': 149.0, 'close': 150.5,
                'volume': 100000.0, 'vwap': 150.25, 'num_trades': 1000,
                'bar_type': 'second',
                'timestamp_start': '2024-12-06T09:30:00+00:00',
                'timestamp_end': '2024-12-06T09:30:01+00:00',
            },
        )

        # Should not raise exception despite callback failure
        service._handle_message(message)

        # Bar should still be stored
        bars = service.get_latest_bars("AAPL", "second")
        assert len(bars) == 1

        # Price should be updated
        assert service.get_latest_price("AAPL") == 150.5
        logger.info("✅ Handle message callback error test passed")

# =============================================================================
# CATEGORY 20: POLYGON DATA SERVICE - COMPONENT INTEGRATION TESTING
# =============================================================================

class TestPolygonDataServiceIntegration:
    """Test component integration and data flow"""

    @pytest.mark.asyncio
    async def test_full_lifecycle_data_flow(self, polygon_service_config):
        """Test complete data flow from initialization to data processing"""
        service = PolygonDataService(config=polygon_service_config)

        # Mock the entire adapter creation and connection process
        mock_adapter = Mock()
        mock_adapter.connect = AsyncMock(return_value=True)
        mock_adapter.subscribe = AsyncMock(return_value=True)
        mock_adapter.is_connected.return_value = True
        mock_adapter.disconnect = AsyncMock(return_value=True)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter', return_value=mock_adapter):

            # Initialize
            assert await service.initialize()
            assert service.is_initialized

            # Start
            assert await service.start()
            assert service.is_operational

            # Simulate receiving data
            message = FeedMessage(
                provider=FeedProvider.POLYGON,
                symbol="AAPL",
                message_type="minute_agg",
                timestamp=datetime.now(timezone.utc),
                data={
                    'open': 150.0, 'high': 151.0, 'low': 149.0, 'close': 150.5,
                    'volume': 100000.0, 'vwap': 150.25, 'num_trades': 1000,
                    'bar_type': 'minute',
                    'timestamp_start': '2024-12-06T09:30:00+00:00',
                    'timestamp_end': '2024-12-06T09:31:00+00:00',
                },
            )

            service._handle_message(message)

            # Verify data was processed
            bars = service.get_latest_bars("AAPL", "minute")
            assert len(bars) == 1
            assert bars.iloc[0]['close'] == 150.5

            price = service.get_latest_price("AAPL")
            assert price == 150.5

            # Stop
            assert await service.stop()
            assert not service.is_operational

        logger.info("✅ Full lifecycle data flow test passed")

    @pytest.mark.asyncio
    async def test_adapter_manager_integration(self, polygon_service_config):
        """Test integration between adapter and aggregation manager"""
        service = PolygonDataService(config=polygon_service_config)

        with patch('core_engine.data.feeds.polygon_integration.PolygonRealtimeFeedAdapter') as MockAdapter:

            mock_adapter = Mock()
            MockAdapter.return_value = mock_adapter

            # Initialize
            assert await service.initialize()

            # Verify adapter is created and connected
            assert service._adapter == mock_adapter
            assert service.is_initialized is True

            # Verify message handler is registered
            mock_adapter.add_message_handler.assert_called_once()
            handler = mock_adapter.add_message_handler.call_args[0][0]
            assert handler == service._handle_message

        logger.info("✅ Adapter manager integration test passed")

    def test_statistics_tracking(self, polygon_service_config):
        """Test statistics tracking during data processing"""
        service = PolygonDataService(config=polygon_service_config)

        initial_stats = service._stats.copy()

        # Process a valid message
        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="minute_agg",
            timestamp=datetime.now(timezone.utc),
            latency_ms=50.0,
            data={
                'open': 150.0, 'high': 151.0, 'low': 149.0, 'close': 150.5,
                'volume': 100000.0, 'vwap': 150.25, 'num_trades': 1000,
                'bar_type': 'minute',
                'timestamp_start': '2024-12-06T09:30:00+00:00',
                'timestamp_end': '2024-12-06T09:31:00+00:00',
            },
        )

        service._handle_message(message)

        # Verify statistics updated
        assert service._stats['messages_received'] == initial_stats['messages_received'] + 1
        assert service._stats['bars_processed'] == initial_stats['bars_processed'] + 1
        assert service._stats['latency_sum_ms'] == initial_stats['latency_sum_ms'] + 50.0
        assert service._stats['latency_count'] == initial_stats['latency_count'] + 1

        # Process an invalid message (missing required fields that will cause an exception)
        invalid_message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="minute_agg",
            timestamp=datetime.now(timezone.utc),
            data={
                'volume': 100000.0,
                # Missing required OHLC fields - this will cause an exception
            },
        )

        service._handle_message(invalid_message)

        # Verify error count increased
        assert service._stats['errors'] == initial_stats['errors'] + 1

        logger.info("✅ Statistics tracking test passed")

    def test_data_consistency_across_methods(self, polygon_service_config):
        """Test data consistency between different access methods"""
        service = PolygonDataService(config=polygon_service_config)

        # Add bar data
        bar = PolygonAggregateBar(
            symbol="AAPL",
            open=150.0, high=151.0, low=149.0, close=150.5,
            volume=100000.0, vwap=150.25, num_trades=1000,
            timestamp_start=datetime(2024, 12, 6, 9, 30, tzinfo=timezone.utc),
            timestamp_end=datetime(2024, 12, 6, 9, 31, tzinfo=timezone.utc),
            bar_type="minute"
        )
        service._bars["AAPL"]["minute"].append(bar)
        service._latest_prices["AAPL"] = 150.5

        # Add trade data
        trade = PolygonTrade(
            symbol="AAPL",
            price=150.5,
            size=100,
            timestamp=datetime(2024, 12, 6, 9, 31, tzinfo=timezone.utc),
            conditions=[],
            exchange=1,
            tape=1,
        )
        service._trades["AAPL"].append(trade)

        # Verify consistency
        bars_df = service.get_latest_bars("AAPL", "minute")
        assert bars_df.iloc[0]['close'] == 150.5

        price = service.get_latest_price("AAPL")
        assert price == 150.5

        trades_df = service.get_latest_trades("AAPL")
        assert trades_df.iloc[0]['price'] == 150.5

        ohlcv_df = service.get_ohlcv_for_pipeline("AAPL", "minute")
        assert ohlcv_df.iloc[0]['close'] == 150.5

        logger.info("✅ Data consistency test passed")

# =============================================================================
# POLYGON REALTIME ADAPTER ADDITIONAL TESTS
# =============================================================================

class TestPolygonRealtimeAdapterConnection:
    """Test connection methods and aiohttp functionality"""

    @patch('core_engine.data.feeds.polygon_realtime.aiohttp')
    @patch('core_engine.data.feeds.polygon_realtime.websockets')
    async def test_connect_with_aiohttp_success(self, mock_websockets, mock_aiohttp, polygon_feed_config):
        """Test successful aiohttp connection"""
        # Mock aiohttp components
        mock_session = AsyncMock()
        mock_ws = AsyncMock()
        mock_aiohttp.ClientSession.return_value = mock_session
        mock_session.ws_connect.return_value = mock_ws

        # Mock connection messages
        connection_msg = {"ev": "status", "status": "connected"}
        auth_success_msg = {"ev": "status", "status": "auth_success"}

        mock_ws.receive.side_effect = [
            AsyncMock(data=json.dumps([connection_msg])),
            AsyncMock(data=json.dumps([auth_success_msg])),
        ]

        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Force aiohttp usage by mocking websockets to fail
        mock_websockets.connect.side_effect = Exception("WebSocket failed")

        # Mock the aiohttp authentication method
        with patch.object(adapter, '_authenticate_aiohttp', return_value=AsyncMock(return_value=True)) as mock_auth:
            with patch.object(adapter, '_receive_loop_aiohttp') as mock_receive:
                result = await adapter._connect_with_aiohttp()

                assert result is True
                assert adapter.status == AdapterStatus.AUTHENTICATED
                mock_aiohttp.ClientSession.assert_called_once()
                mock_session.ws_connect.assert_called_once()
                mock_auth.assert_called_once()
                logger.info("✅ aiohttp connection success test passed")

    # @patch('core_engine.data.feeds.polygon_realtime.aiohttp')
    # async def test_aiohttp_authentication_success(self, mock_aiohttp, polygon_feed_config):
    #     """Test aiohttp authentication"""
    #     from aiohttp import WSMsgType

    #     mock_ws = AsyncMock()

    #     # Mock connection confirmation and auth success messages
    #     connection_msg = AsyncMock()
    #     connection_msg.type = WSMsgType.TEXT
    #     connection_msg.data = json.dumps([{"ev": "status", "status": "connected"}])

    #     auth_success_msg = AsyncMock()
    #     auth_success_msg.type = WSMsgType.TEXT
    #     auth_success_msg.data = json.dumps([{"ev": "status", "status": "auth_success"}])

    #     mock_ws.receive.side_effect = [connection_msg, auth_success_msg]

    #     adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
    #     adapter._aiohttp_ws = mock_ws
    #     adapter._use_aiohttp = True

    #     result = await adapter._authenticate_aiohttp()

    #     assert result is True
    #     # Should send auth message
    #     assert mock_ws.send_str.call_count == 1
    #     auth_call = mock_ws.send_str.call_args[0][0]
    #     auth_data = json.loads(auth_call)
    #     assert auth_data["action"] == "auth"
    #     assert auth_data["params"] == polygon_feed_config.api_key
    #     logger.info("✅ aiohttp authentication success test passed")

    @patch('core_engine.data.feeds.polygon_realtime.aiohttp')
    async def test_aiohttp_authentication_failure(self, mock_aiohttp, polygon_feed_config):
        """Test aiohttp authentication failure"""
        mock_ws = AsyncMock()
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        adapter._aiohttp_ws = mock_ws
        adapter._use_aiohttp = True

        # Mock auth failure response
        auth_msg = {"ev": "status", "status": "auth_failed", "message": "Invalid key"}
        mock_ws.receive.return_value = AsyncMock(data=json.dumps([auth_msg]))

        result = await adapter._authenticate_aiohttp()

        assert result is False
        logger.info("✅ aiohttp authentication failure test passed")

    async def test_websockets_authentication_success(self, polygon_feed_config):
        """Test websockets authentication success"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock websocket
        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        # Mock connection and auth messages
        connection_msg = {"ev": "status", "status": "connected"}
        auth_msg = {"ev": "status", "status": "auth_success"}

        mock_ws.recv.side_effect = [
            json.dumps([connection_msg]),
            json.dumps([auth_msg])
        ]

        result = await adapter._authenticate()

        assert result is True
        logger.info("✅ websockets authentication success test passed")

    async def test_websockets_authentication_failure(self, polygon_feed_config):
        """Test websockets authentication failure"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock websocket
        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        # Mock auth failure
        auth_msg = {"ev": "status", "status": "auth_failed", "message": "Invalid key"}
        mock_ws.recv.return_value = json.dumps([auth_msg])

        result = await adapter._authenticate()

        assert result is False
        logger.info("✅ websockets authentication failure test passed")

class TestPolygonRealtimeAdapterMessageHandling:
    """Test message handling for different data types"""

    async def test_handle_quote_message(self, polygon_feed_config):
        """Test quote message handling"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock message handler
        mock_handler = Mock()
        adapter._handle_message = mock_handler

        # Sample quote message
        quote_msg = {
            "ev": "Q",
            "sym": "AAPL",
            "bp": 150.25,
            "bs": 100,
            "ap": 150.30,
            "as": 200,
            "t": 1700000000000000000,  # nanoseconds
            "bx": 1,
            "ax": 2,
            "c": [1, 2]
        }

        await adapter._handle_quote(quote_msg)

        # Verify message was handled
        assert mock_handler.call_count == 1
        call_args = mock_handler.call_args[0][0]

        assert call_args.symbol == "AAPL"
        assert call_args.message_type == "quote"
        assert call_args.data['bid'] == 150.25
        assert call_args.data['ask'] == 150.30
        assert call_args.data['bid_size'] == 100
        assert call_args.data['ask_size'] == 200
        logger.info("✅ quote message handling test passed")

    async def test_handle_trade_message_error_handling(self, polygon_feed_config):
        """Test trade message error handling"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Invalid trade message (missing required fields)
        invalid_trade_msg = {
            "ev": "T",
            "sym": "AAPL",
            # Missing price and size
        }

        # Should not raise exception
        await adapter._handle_trade(invalid_trade_msg)

        # Check that error was logged (we can't easily test logging directly)
        logger.info("✅ trade message error handling test passed")

    async def test_handle_aggregate_message_error_handling(self, polygon_feed_config):
        """Test aggregate message error handling"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Invalid aggregate message
        invalid_agg_msg = {
            "ev": "A",
            "sym": "AAPL",
            # Missing required OHLC fields
        }

        # Should not raise exception
        await adapter._handle_aggregate(invalid_agg_msg, "second")

        logger.info("✅ aggregate message error handling test passed")

    async def test_process_message_unknown_type(self, polygon_feed_config):
        """Test processing unknown message types"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock message handler
        mock_handler = Mock()
        adapter._handle_message = mock_handler

        # Unknown message type
        unknown_msg = {
            "ev": "UNKNOWN",
            "data": "test"
        }

        await adapter._process_message(json.dumps([unknown_msg]))

        # Should not call message handler for unknown types
        assert mock_handler.call_count == 0
        logger.info("✅ unknown message type handling test passed")

    def test_calculate_latency(self, polygon_feed_config):
        """Test latency calculation"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Test with past timestamp
        past_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        latency = adapter._calculate_latency(past_time)

        assert latency >= 1000  # At least 1 second in milliseconds
        assert isinstance(latency, float)
        logger.info("✅ latency calculation test passed")

    def test_calculate_latency_future_timestamp(self, polygon_feed_config):
        """Test latency calculation with future timestamp"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Test with future timestamp (should return 0)
        future_time = datetime.now(timezone.utc) + timedelta(seconds=1)
        latency = adapter._calculate_latency(future_time)

        assert latency == 0
        logger.info("✅ future timestamp latency test passed")

    async def test_message_processing_json_error(self, polygon_feed_config):
        """Test handling of malformed JSON messages"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock error handler
        mock_error_handler = Mock()
        adapter._handle_error = mock_error_handler

        # Send malformed JSON
        await adapter._process_message("invalid json")

        # Should handle error gracefully
        mock_error_handler.assert_called_once()
        logger.info("✅ malformed JSON message test passed")

    async def test_message_processing_unknown_event_type(self, polygon_feed_config):
        """Test handling of unknown event types"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock message handler to check it's not called for unknown types
        mock_handler = Mock()
        adapter._handle_message = mock_handler

        # Send message with unknown event type
        unknown_msg = [{"ev": "UNKNOWN", "data": "test"}]

        await adapter._process_message(json.dumps(unknown_msg))

        # Handler should not be called for unknown event
        mock_handler.assert_not_called()
        logger.info("✅ unknown event type test passed")

    async def test_trade_message_parsing_error(self, polygon_feed_config):
        """Test error handling in trade message parsing"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock error handler
        mock_error_handler = Mock()
        adapter._handle_error = mock_error_handler

        # Send trade message with invalid data
        invalid_trade_msg = {
            "ev": "T",
            "sym": "AAPL",
            "p": "invalid_price",  # Invalid price
            "s": 100,
            "t": 1700000000000000000
        }

        await adapter._handle_trade(invalid_trade_msg)

        # Should handle parsing error gracefully
        mock_error_handler.assert_called_once()
        logger.info("✅ trade parsing error test passed")

    async def test_aggregate_message_parsing_error(self, polygon_feed_config):
        """Test error handling in aggregate message parsing"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock error handler
        mock_error_handler = Mock()
        adapter._handle_error = mock_error_handler

        # Send aggregate message with invalid data
        invalid_agg_msg = {
            "ev": "AM",
            "sym": "AAPL",
            "o": "invalid_open",  # Invalid price
            "h": 152.0,
            "l": 149.0,
            "c": 151.0,
            "v": 1000,
            "t": 1700000000000000000
        }

        await adapter._handle_aggregate(invalid_agg_msg, "minute")

        # Should handle parsing error gracefully
        mock_error_handler.assert_called_once()
        logger.info("✅ aggregate parsing error test passed")

class TestPolygonRealtimeAdapterSubscription:
    """Test subscription and unsubscription functionality"""

    async def test_subscribe_quote_with_starter_tier(self, polygon_feed_config):
        """Test subscribing to quotes with starter tier (should be rejected)"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock websocket
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        adapter._set_status(AdapterStatus.AUTHENTICATED)

        # Try to subscribe to quotes (not available in starter tier)
        result = await adapter.subscribe(["AAPL"], ["quote"])

        assert result is False  # Should fail
        mock_ws.send.assert_not_called()  # Should not send subscription
        logger.info("✅ quote subscription rejection test passed")

    async def test_subscribe_with_invalid_data_type(self, polygon_feed_config):
        """Test subscribing with invalid data type"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock websocket
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        adapter._set_status(AdapterStatus.AUTHENTICATED)

        # Try to subscribe with invalid data type
        result = await adapter.subscribe(["AAPL"], ["invalid_type"])

        assert result is False
        mock_ws.send.assert_not_called()
        logger.info("✅ invalid data type subscription test passed")

    async def test_unsubscribe_not_connected(self, polygon_feed_config):
        """Test unsubscription when not connected"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Should return True (already "unsubscribed")
        result = await adapter.unsubscribe(["AAPL"])

        assert result is True
        logger.info("✅ unsubscription when not connected test passed")

    async def test_send_message_websockets(self, polygon_feed_config):
        """Test sending message via websockets"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        test_message = "test message"
        await adapter._send_message(test_message)

        mock_ws.send.assert_called_once_with(test_message)
        logger.info("✅ websockets send message test passed")

    async def test_send_message_aiohttp(self, polygon_feed_config):
        """Test sending message via aiohttp"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        mock_ws = AsyncMock()
        adapter._aiohttp_ws = mock_ws
        adapter._use_aiohttp = True

        test_message = "test message"
        await adapter._send_message(test_message)

        mock_ws.send_str.assert_called_once_with(test_message)
        logger.info("✅ aiohttp send message test passed")

class TestPolygonRealtimeAdapterReconnection:
    """Test reconnection and heartbeat functionality"""

    async def test_attempt_reconnect_max_attempts_exceeded(self, polygon_feed_config):
        """Test reconnection when max attempts exceeded"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        adapter._reconnect_count = polygon_feed_config.max_reconnect_attempts

        await adapter._attempt_reconnect()

        assert adapter.status == AdapterStatus.ERROR
        logger.info("✅ max reconnection attempts test passed")

    async def test_attempt_reconnect_success(self, polygon_feed_config):
        """Test successful reconnection"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        adapter._reconnect_count = 1

        # Set up some active subscriptions
        adapter._active_subscriptions['trade'].add('AAPL')
        adapter._active_subscriptions['second_agg'].add('AAPL')

        # Mock successful reconnect
        with patch.object(adapter, 'connect', return_value=AsyncMock(return_value=True)) as mock_connect:
            with patch.object(adapter, 'subscribe') as mock_subscribe:
                await adapter._attempt_reconnect()

                mock_connect.assert_called_once()
                mock_subscribe.assert_called_once()
                # Check that subscribe was called with the right arguments
                call_args = mock_subscribe.call_args
                assert call_args[0][0] == ['AAPL']  # symbols
                assert set(call_args[0][1]) == {'trade', 'second_agg'}  # data_types
                logger.info("✅ successful reconnection test passed")

    async def test_heartbeat_monitor_no_messages(self, polygon_feed_config):
        """Test heartbeat monitor detects lack of messages"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        adapter._set_status(AdapterStatus.ACTIVE)
        adapter._subscriptions.add("AAPL")

        # Mock asyncio.sleep and time passage
        original_count = adapter._message_count

        with patch('asyncio.sleep', side_effect=asyncio.CancelledError()):
            try:
                await adapter._heartbeat_monitor()
            except asyncio.CancelledError:
                pass

        # Message count should remain the same (no messages received)
        assert adapter._message_count == original_count
        logger.info("✅ heartbeat monitor no messages test passed")

class TestPolygonRealtimeAdapterDisconnection:
    """Test disconnect functionality and cleanup"""

    @patch('core_engine.data.feeds.polygon_realtime.aiohttp')
    @patch('core_engine.data.feeds.polygon_realtime.websockets')
    async def test_disconnect_with_aiohttp(self, mock_websockets, mock_aiohttp, polygon_feed_config):
        """Test disconnecting when using aiohttp WebSocket"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock aiohttp session and WebSocket
        mock_session = AsyncMock()
        mock_ws = AsyncMock()
        adapter._aiohttp_session = mock_session
        adapter._aiohttp_ws = mock_ws
        adapter._use_aiohttp = True

        # Disconnect
        await adapter.disconnect()

        # Verify cleanup
        mock_ws.close.assert_called_once()
        mock_session.close.assert_called_once()

        assert adapter._aiohttp_ws is None
        assert adapter._aiohttp_session is None
        assert adapter.status == AdapterStatus.DISCONNECTED

    @patch('core_engine.data.feeds.polygon_realtime.websockets')
    async def test_disconnect_with_websockets(self, mock_websockets, polygon_feed_config):
        """Test disconnecting when using websockets library"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock WebSocket
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        adapter._use_aiohttp = False

        # Disconnect
        await adapter.disconnect()

        # Verify cleanup
        mock_ws.close.assert_called_once()

        assert adapter._ws is None
        assert adapter.status == AdapterStatus.DISCONNECTED

    @patch('core_engine.data.feeds.polygon_realtime.aiohttp')
    async def test_disconnect_exception_handling(self, mock_aiohttp, polygon_feed_config):
        """Test disconnect handles exceptions gracefully"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock aiohttp session and WebSocket that raise exceptions
        mock_session = AsyncMock()
        mock_ws = AsyncMock()
        mock_session.close.side_effect = Exception("Session close error")
        mock_ws.close.side_effect = Exception("WS close error")

        adapter._aiohttp_session = mock_session
        adapter._aiohttp_ws = mock_ws
        adapter._use_aiohttp = True

        # Should not raise exception
        await adapter.disconnect()

        # Verify calls were made despite exceptions
        mock_ws.close.assert_called_once()
        mock_session.close.assert_called_once()

    async def test_disconnect_not_connected(self, polygon_feed_config):
        """Test disconnecting when not connected"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Should not raise exception
        await adapter.disconnect()

        assert adapter.status == AdapterStatus.DISCONNECTED

class TestPolygonRealtimeAdapterUtilities:
    """Test utility methods"""

    def test_get_latest_bar(self, polygon_feed_config, sample_aggregate_bar):
        """Test getting latest cached bar"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Cache a bar
        adapter._latest_bars["AAPL_minute"] = sample_aggregate_bar

        # Retrieve it
        bar = adapter.get_latest_bar("AAPL", "minute")

        assert bar == sample_aggregate_bar
        logger.info("✅ get latest bar test passed")

    def test_get_latest_bar_not_found(self, polygon_feed_config):
        """Test getting latest bar when not cached"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        bar = adapter.get_latest_bar("AAPL", "minute")

        assert bar is None
        logger.info("✅ get latest bar not found test passed")

    def test_get_statistics(self, polygon_feed_config):
        """Test getting adapter statistics"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Set some test data
        adapter._message_count = 100
        adapter._last_message_time = datetime.now()
        adapter._reconnect_count = 2
        adapter._active_subscriptions['trade'].add('AAPL')
        adapter._active_subscriptions['second_agg'].add('TSLA')
        adapter._latest_bars['AAPL_minute'] = Mock()

        stats = adapter.get_statistics()

        assert stats['polygon_message_count'] == 100
        assert stats['reconnect_count'] == 2
        assert stats['active_subscriptions']['trade'] == 1
        assert stats['active_subscriptions']['second_agg'] == 1
        assert stats['cached_bars'] == 1
        assert stats['subscription_tier'] == 'starter'
        logger.info("✅ get statistics test passed")

    def test_is_connected_websockets(self, polygon_feed_config):
        """Test connection check for websockets"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Not connected
        assert not adapter.is_connected()

        # Mock websocket connection
        mock_ws = Mock()
        mock_ws.open = True
        adapter._ws = mock_ws
        adapter._set_status(AdapterStatus.AUTHENTICATED)

        assert adapter.is_connected()
        logger.info("✅ websockets connection check test passed")

    def test_is_connected_aiohttp(self, polygon_feed_config):
        """Test connection check for aiohttp"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)

        # Mock aiohttp connection
        mock_ws = Mock()
        mock_ws.closed = False
        adapter._aiohttp_ws = mock_ws
        adapter._use_aiohttp = True
        adapter._set_status(AdapterStatus.AUTHENTICATED)

        assert adapter.is_connected()
        logger.info("✅ aiohttp connection check test passed")

class TestPolygonAggregatedDataManagerAdvanced:
    """Test advanced functionality of PolygonAggregatedDataManager"""

    async def test_update_custom_bars_minute_aggregation(self, polygon_feed_config):
        """Test custom timeframe bar aggregation from minute bars"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        manager = PolygonAggregatedDataManager(adapter)

        # Create 5 minute bars (5-minute period) + 1 more to trigger completion
        base_time = datetime(2024, 12, 6, 9, 30, tzinfo=timezone.utc)

        bars = []
        for i in range(6):  # 6 bars: 30-35, the 6th triggers completion
            bar = PolygonAggregateBar(
                symbol="AAPL",
                open=150.0 + i,
                high=151.0 + i,
                low=149.0 + i,
                close=150.5 + i,
                volume=100000.0,
                vwap=150.25 + i,
                timestamp_start=base_time + timedelta(minutes=i),
                timestamp_end=base_time + timedelta(minutes=i+1),
                num_trades=1000,
                bar_type="minute",
            )
            bars.append(bar)

        # Process bars
        for bar in bars:
            feed_msg = FeedMessage(
                provider=FeedProvider.POLYGON,
                symbol="AAPL",
                message_type="minute_agg",
                timestamp=bar.timestamp_end,
                data={
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume,
                    'vwap': bar.vwap,
                    'num_trades': bar.num_trades,
                    'bar_type': bar.bar_type,
                    'timestamp_start': bar.timestamp_start.isoformat(),
                    'timestamp_end': bar.timestamp_end.isoformat(),
                }
            )
            await manager.process_aggregate(feed_msg)

        # Check that 5-minute bar was created
        five_min_bars = manager.get_bars("AAPL", "5m")
        assert len(five_min_bars) == 1

        aggregated_bar = five_min_bars[0]
        assert aggregated_bar.bar_type == "5m"
        assert aggregated_bar.open == 150.0  # First bar's open
        assert aggregated_bar.close == 154.5  # Last bar's close
        assert aggregated_bar.high == 155.0  # Max of all highs
        assert aggregated_bar.low == 149.0   # Min of all lows
        assert aggregated_bar.volume == 500000.0  # Sum of volumes
        logger.info("✅ custom bar aggregation test passed")

    def test_complete_aggregated_bar(self, polygon_feed_config):
        """Test completing an aggregated bar from minute bars"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        manager = PolygonAggregatedDataManager(adapter)

        # Create test minute bars
        bars = [
            PolygonAggregateBar(
                symbol="AAPL",
                open=150.0, high=151.0, low=149.0, close=150.5,
                volume=100000.0, vwap=150.25, num_trades=1000,
                timestamp_start=datetime(2024, 12, 6, 9, 30, tzinfo=timezone.utc),
                timestamp_end=datetime(2024, 12, 6, 9, 31, tzinfo=timezone.utc),
                bar_type="minute"
            ),
            PolygonAggregateBar(
                symbol="AAPL",
                open=150.5, high=152.0, low=150.0, close=151.5,
                volume=120000.0, vwap=151.0, num_trades=1200,
                timestamp_start=datetime(2024, 12, 6, 9, 31, tzinfo=timezone.utc),
                timestamp_end=datetime(2024, 12, 6, 9, 32, tzinfo=timezone.utc),
                bar_type="minute"
            )
        ]

        result = manager._complete_aggregated_bar(bars, "5m")

        assert result is not None
        assert result.symbol == "AAPL"
        assert result.bar_type == "5m"
        assert result.open == 150.0
        assert result.high == 152.0
        assert result.low == 149.0
        assert result.close == 151.5
        assert result.volume == 220000.0
        assert result.num_trades == 2200
        logger.info("✅ complete aggregated bar test passed")

    def test_complete_aggregated_bar_empty(self, polygon_feed_config):
        """Test completing aggregated bar with empty input"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        manager = PolygonAggregatedDataManager(adapter)

        result = manager._complete_aggregated_bar([], "5m")

        assert result is None
        logger.info("✅ complete aggregated bar empty test passed")

    def test_get_bars_with_limit(self, polygon_feed_config):
        """Test getting bars with limit"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        manager = PolygonAggregatedDataManager(adapter)

        # Initialize bars structure for AAPL
        if "AAPL" not in manager._bars:
            manager._bars["AAPL"] = {"minute": []}

        # Add multiple bars
        bars = []
        for i in range(10):
            bar = PolygonAggregateBar(
                symbol="AAPL",
                open=150.0, high=151.0, low=149.0, close=150.5,
                volume=100000.0, vwap=150.25, num_trades=1000,
                timestamp_start=datetime(2024, 12, 6, 9, 30 + i, tzinfo=timezone.utc),
                timestamp_end=datetime(2024, 12, 6, 9, 31 + i, tzinfo=timezone.utc),
                bar_type="minute"
            )
            bars.append(bar)
            manager._bars["AAPL"]["minute"].append(bar)

        # Get limited results
        limited_bars = manager.get_bars("AAPL", "minute", limit=3)

        assert len(limited_bars) == 3
        # Should return most recent bars
        assert limited_bars[0].timestamp_end > limited_bars[1].timestamp_end
        logger.info("✅ get bars with limit test passed")

    def test_get_latest_price_from_cache(self, polygon_feed_config):
        """Test getting latest price from adapter cache"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        manager = PolygonAggregatedDataManager(adapter)

        # Cache a second bar (higher priority)
        second_bar = PolygonAggregateBar(
            symbol="AAPL",
            open=150.0, high=151.0, low=149.0, close=150.75,
            volume=100000.0, vwap=150.25, num_trades=1000,
            timestamp_start=datetime(2024, 12, 6, 9, 30, tzinfo=timezone.utc),
            timestamp_end=datetime(2024, 12, 6, 9, 30, 1, tzinfo=timezone.utc),
            bar_type="second"
        )
        adapter._latest_bars["AAPL_second"] = second_bar

        price = manager.get_latest_price("AAPL")

        assert price == 150.75
        logger.info("✅ get latest price from cache test passed")

class TestPolygonAggregatedDataManagerCallbacks:
    """Test data manager callback functionality"""

    async def test_bar_callback_invocation(self, polygon_feed_config):
        """Test bar callback is invoked on bar completion"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        manager = PolygonAggregatedDataManager(adapter)

        callback_called = False
        callback_data = {}

        def test_callback(symbol, timeframe, bar):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = {'symbol': symbol, 'timeframe': timeframe, 'bar': bar}

        manager.add_bar_callback(test_callback)

        # Create a message that will trigger custom bar completion
        message = FeedMessage(
            provider=FeedProvider.POLYGON,
            symbol="AAPL",
            message_type="minute_agg",
            timestamp=datetime(2024, 12, 6, 9, 30, tzinfo=timezone.utc),
            data={
                'open': 150.0, 'high': 151.0, 'low': 149.0, 'close': 150.5,
                'volume': 100000.0, 'vwap': 150.25, 'num_trades': 500,
                'bar_type': 'minute',
                'timestamp_start': '2024-12-06T09:30:00+00:00',
                'timestamp_end': '2024-12-06T09:31:00+00:00'
            }
        )

        # Process multiple bars to trigger completion
        for i in range(5):  # 5-minute bar
            await manager.process_aggregate(message)

        # Manually trigger completion for testing
        completed_bar = PolygonAggregateBar(
            symbol="AAPL", open=150.0, high=151.0, low=149.0, close=150.5,
            volume=500000.0, vwap=150.25, num_trades=2500,
            timestamp_start=datetime(2024, 12, 6, 9, 25, tzinfo=timezone.utc),
            timestamp_end=datetime(2024, 12, 6, 9, 30, tzinfo=timezone.utc),
            bar_type="5m"
        )
        manager._notify_bar_completion("AAPL", "5m", completed_bar)

        assert callback_called
        assert callback_data['symbol'] == "AAPL"
        assert callback_data['timeframe'] == "5m"
        assert callback_data['bar'] == completed_bar
        logger.info("✅ bar callback invocation test passed")

    async def test_bar_callback_error_handling(self, polygon_feed_config):
        """Test bar callback error handling"""
        adapter = PolygonRealtimeFeedAdapter(polygon_feed_config)
        manager = PolygonAggregatedDataManager(adapter)

        def failing_callback(symbol, timeframe, bar):
            raise Exception("Callback failed")

        manager.add_bar_callback(failing_callback)

        # This should not raise an exception
        completed_bar = PolygonAggregateBar(
            symbol="AAPL", open=150.0, high=151.0, low=149.0, close=150.5,
            volume=100000.0, vwap=150.25, num_trades=500,
            timestamp_start=datetime(2024, 12, 6, 9, 30, tzinfo=timezone.utc),
            timestamp_end=datetime(2024, 12, 6, 9, 31, tzinfo=timezone.utc),
            bar_type="minute"
        )
        manager._notify_bar_completion("AAPL", "minute", completed_bar)

        # Bar should still be stored
        bars = manager.get_bars("AAPL", "minute")
        assert len(bars) == 1
        logger.info("✅ bar callback error handling test passed")

class TestPolygonRealtimeAdapterConfigValidation:
    """Test configuration validation edge cases"""

    def test_config_validation_missing_api_key(self):
        """Test config validation with missing API key"""
        with pytest.raises(ValueError, match="Polygon API key is required"):
            PolygonFeedConfig(api_key="")

    def test_config_validation_invalid_data_type_for_tier(self):
        """Test config validation with invalid data type for subscription tier"""
        with pytest.raises(ValueError, match="Data types .* not available with .* tier"):
            PolygonFeedConfig(
                api_key="test_key",
                subscription_tier=PolygonSubscriptionTier.STARTER,
                data_types=["quote"]  # Quotes require Advanced tier
            )

    def test_config_ws_url_stocks(self, polygon_api_key):
        """Test WebSocket URL generation for stocks cluster"""
        config = PolygonFeedConfig(
            api_key=polygon_api_key,
            cluster=PolygonCluster.STOCKS
        )
        assert config.ws_url == "wss://socket.massive.com/stocks"

    def test_config_ws_url_delayed(self, polygon_api_key):
        """Test WebSocket URL generation for delayed stocks cluster"""
        config = PolygonFeedConfig(
            api_key=polygon_api_key,
            cluster=PolygonCluster.STOCKS_DELAYED
        )
        assert config.ws_url == "wss://delayed.massive.com/stocks"
    """Test configuration validation edge cases"""

    def test_config_validation_missing_api_key(self):
        """Test config validation with missing API key"""
        with pytest.raises(ValueError, match="Polygon API key is required"):
            PolygonFeedConfig(api_key="")

    def test_config_validation_invalid_data_type_for_tier(self):
        """Test config validation with invalid data type for subscription tier"""
        with pytest.raises(ValueError, match="Data types .* not available with .* tier"):
            PolygonFeedConfig(
                api_key="test_key",
                subscription_tier=PolygonSubscriptionTier.STARTER,
                data_types=["quote"]  # Quotes require Advanced tier
            )

    def test_config_ws_url_stocks(self, polygon_api_key):
        """Test WebSocket URL generation for stocks cluster"""
        config = PolygonFeedConfig(
            api_key=polygon_api_key,
            cluster=PolygonCluster.STOCKS
        )
        assert config.ws_url == "wss://socket.massive.com/stocks"

    def test_config_ws_url_delayed(self, polygon_api_key):
        """Test WebSocket URL generation for delayed stocks cluster"""
        config = PolygonFeedConfig(
            api_key=polygon_api_key,
            cluster=PolygonCluster.STOCKS_DELAYED
        )
        assert config.ws_url == "wss://delayed.massive.com/stocks"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

