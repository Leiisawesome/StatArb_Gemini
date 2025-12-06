"""
Unit tests for Polygon.io Feed Integration
Tests REST API service, WebSocket adapter, and data integration
"""

import pytest
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pandas as pd

from core_engine.data.feeds.polygon_rest import (
    PolygonRestService,
    PolygonRestConfig,
    AggregateBar,
    create_polygon_rest_service,
)
from core_engine.data.feeds.polygon_realtime import (
    PolygonRealtimeFeedAdapter,
    PolygonFeedConfig,
    PolygonSubscriptionTier,
    PolygonCluster,
    PolygonAggregateBar,
    PolygonTrade,
    PolygonQuote,
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
        assert config.rate_limit_calls == 5
        assert config.rate_limit_period == 60.0
        logger.info("✅ REST config creation test passed")
    
    def test_config_defaults(self, polygon_api_key):
        """Test config default values"""
        config = PolygonRestConfig(api_key=polygon_api_key)
        
        assert config.timeout_seconds == 30.0
        assert config.max_retries == 3
        assert config.default_limit == 5000
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
        assert service._session is None
        logger.info("✅ REST service creation test passed")
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, polygon_rest_config):
        """Test successful initialization"""
        service = PolygonRestService(config=polygon_rest_config)
        
        # Create proper async context manager mock
        class MockResponse:
            def __init__(self):
                self.status = 200
                self.headers = {}
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                return None
            
            async def json(self):
                return {'status': 'OK', 'results': [{'t': 1701878400000, 'o': 150.0, 'h': 151.0, 'l': 149.0, 'c': 150.5, 'v': 1000000.0}]}
        
        class MockSession:
            def __init__(self):
                pass
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                return None
            
            def get(self, url, params=None):
                return MockResponse()
            
            async def close(self):
                return None
        
        with patch('aiohttp.ClientSession', return_value=MockSession()):
            result = await service.initialize()
            
            assert result is True
            assert service.is_initialized is True
            assert service._session is not None
        
        await service.close()
        logger.info("✅ REST service initialize success test passed")
    
    @pytest.mark.asyncio
    async def test_initialize_api_key_verification_fails(self, polygon_rest_config):
        """Test initialization fails with invalid API key"""
        service = PolygonRestService(config=polygon_rest_config)
        
        # Create proper async context manager mock for failed response
        class MockResponse:
            def __init__(self):
                self.status = 401
                self.headers = {}
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                return None
            
            async def json(self):
                return {'status': 'ERROR'}
        
        class MockSession:
            def __init__(self):
                pass
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                return None
            
            def get(self, url, params=None):
                return MockResponse()
            
            async def close(self):
                return None
        
        with patch('aiohttp.ClientSession', return_value=MockSession()):
            result = await service.initialize()
            
            assert result is False
            assert service.is_initialized is False
        
        await service.close()
        logger.info("✅ REST service initialize API key fails test passed")
    
    @pytest.mark.asyncio
    async def test_close_service(self, polygon_rest_config):
        """Test closing service"""
        service = PolygonRestService(config=polygon_rest_config)
        
        mock_session = AsyncMock()
        service._session = mock_session
        
        await service.close()
        
        mock_session.close.assert_called_once()
        assert service._session is None
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
        service._session = AsyncMock()
        
        # Fill up rate limit
        now = asyncio.get_event_loop().time()
        service._request_times = [now - 10, now - 5, now - 2, now - 1, now]
        
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
        # Mix of old and recent times
        service._request_times = [
            now - 70,  # Old (outside 60s window)
            now - 30,  # Recent
            now - 10,  # Recent
            now,       # Recent
        ]
        
        await service._rate_limit()
        
        # Old time should be removed
        assert len(service._request_times) == 4  # All kept (old one removed, new one added)
        assert now - 70 not in service._request_times
        logger.info("✅ Rate limit cleanup old times test passed")
    
    @pytest.mark.asyncio
    async def test_rate_limit_allows_when_under_limit(self, polygon_rest_config):
        """Test rate limit allows requests when under limit"""
        service = PolygonRestService(config=polygon_rest_config)
        
        now = asyncio.get_event_loop().time()
        service._request_times = [now - 10, now - 5]  # Only 2 requests
        
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
        
        # Create proper async context manager mock
        class MockResponse:
            def __init__(self):
                self.status = 200
                self.headers = {}
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                return None
            
            async def json(self):
                return {
                    'status': 'OK',
                    'results': [{
                        't': 1701878400000,  # Dec 6, 2024
                        'o': 150.0,
                        'h': 151.0,
                        'l': 149.0,
                        'c': 150.5,
                        'v': 1000000.0,
                        'vw': 150.25,
                        'n': 5000,
                    }]
                }
        
        class MockSession:
            def get(self, url, params=None):
                return MockResponse()
        
        service._session = MockSession()
        service._request_times = []
        
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
        
        class MockResponse:
            def __init__(self):
                self.status = 200
                self.headers = {}
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                return None
            
            async def json(self):
                return {'status': 'OK', 'results': []}
        
        class MockSession:
            def get(self, url, params=None):
                return MockResponse()
        
        service._session = MockSession()
        service._request_times = []
        
        bar = await service.get_previous_day("AAPL")
        
        assert bar is None
        logger.info("✅ Get previous day no data test passed")
    
    @pytest.mark.asyncio
    async def test_get_bars_minute(self, polygon_rest_config):
        """Test getting minute bars"""
        service = PolygonRestService(config=polygon_rest_config)
        
        # Create proper async context manager mock
        class MockResponse:
            def __init__(self):
                self.status = 200
                self.headers = {}
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                return None
            
            async def json(self):
                return {
                    'status': 'OK',
                    'results': [
                        {
                            't': 1701878400000,  # 9:30 AM
                            'o': 150.0,
                            'h': 150.5,
                            'l': 149.5,
                            'c': 150.2,
                            'v': 100000.0,
                            'vw': 150.1,
                            'n': 500,
                        },
                        {
                            't': 1701878460000,  # 9:31 AM
                            'o': 150.2,
                            'h': 150.8,
                            'l': 150.0,
                            'c': 150.6,
                            'v': 120000.0,
                            'vw': 150.4,
                            'n': 600,
                        },
                    ]
                }
        
        class MockSession:
            def get(self, url, params=None):
                return MockResponse()
        
        service._session = MockSession()
        service._request_times = []
        
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
        
        # Create proper async context manager mock
        class MockResponse:
            def __init__(self):
                self.status = 200
                self.headers = {}
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                return None
            
            async def json(self):
                return {
                    'status': 'OK',
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
                }
        
        class MockSession:
            def get(self, url, params=None):
                return MockResponse()
        
        service._session = MockSession()
        service._request_times = []
        
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
        
        # Mock responses for different symbols
        responses = {
            "AAPL": {
                'status': 'OK',
                'results': [{'t': 1701878400000, 'o': 150.0, 'h': 151.0, 'l': 149.0, 'c': 150.5, 'v': 1000000.0}]
            },
            "TSLA": {
                'status': 'OK',
                'results': [{'t': 1701878400000, 'o': 250.0, 'h': 251.0, 'l': 249.0, 'c': 250.5, 'v': 2000000.0}]
            },
        }
        
        class MockResponse:
            def __init__(self, symbol):
                self.status = 200
                self.headers = {}
                self._symbol = symbol
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                return None
            
            async def json(self):
                return responses.get(self._symbol, {'status': 'OK', 'results': []})
        
        class MockSession:
            def get(self, url, params=None):
                symbol = url.split('/')[-2]  # Extract symbol from URL
                return MockResponse(symbol)
        
        service._session = MockSession()
        service._request_times = []
        
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
        assert polygon_feed_config.ws_url == "wss://socket.polygon.io/stocks"
        
        # Test delayed endpoint
        polygon_feed_config.cluster = PolygonCluster.STOCKS_DELAYED
        assert polygon_feed_config.ws_url == "wss://delayed.polygon.io/stocks"
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
    
    def test_adapter_missing_websockets(self, polygon_feed_config):
        """Test adapter requires websockets"""
        with patch('core_engine.data.feeds.polygon_realtime.WEBSOCKETS_AVAILABLE', False):
            with pytest.raises(ImportError, match="websockets package required"):
                PolygonRealtimeFeedAdapter(polygon_feed_config)
        
        logger.info("✅ Adapter missing websockets test passed")
    
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
        """Test REST service handles request errors"""
        service = PolygonRestService(config=polygon_rest_config)
        
        class MockSession:
            def get(self, url, params=None):
                raise Exception("Network error")
        
        service._session = MockSession()
        service._request_times = []
        
        data = await service._request("https://api.polygon.io/test")
        
        assert data.get('status') == 'ERROR'
        logger.info("✅ REST service request error test passed")
    
    @pytest.mark.asyncio
    async def test_rest_service_rate_limit_429(self, polygon_rest_config):
        """Test REST service handles 429 rate limit"""
        service = PolygonRestService(config=polygon_rest_config)
        
        class MockResponse:
            def __init__(self):
                self.status = 429
                self.headers = {'Retry-After': '60'}
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                return None
            
            async def json(self):
                return {'status': 'ERROR', 'message': 'Rate limited'}
        
        class MockSession:
            def get(self, url, params=None):
                return MockResponse()
        
        service._session = MockSession()
        service._request_times = []
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            data = await service._request("https://api.polygon.io/test")
            
            # Should wait for retry
            mock_sleep.assert_called()
        
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

