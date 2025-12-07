"""
Unit tests for Feed Manager
Tests feed management, WebSocket/HTTP feeds, subscriptions, and monitoring
"""

import pytest
import logging
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from core_engine.data.feeds.manager import (
    FeedManager,
    FeedConfiguration,
    FeedMessage,
    FeedStatistics,
    FeedType,
    FeedStatus,
    DataFormat,
    SubscriptionType,
    DataFeed,
    WebSocketFeed,
    HTTPFeed
)

logger = logging.getLogger(__name__)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def feed_config():
    """Create basic feed configuration"""
    return FeedConfiguration(
        feed_id="test_feed",
        feed_type=FeedType.MARKET_DATA,
        name="Test Feed",
        description="Test data feed",
        url="wss://test.example.com/feed",
        protocol="websocket",
        port=443,
        api_key="test_api_key",
        data_format=DataFormat.JSON,
        subscription_type=SubscriptionType.REAL_TIME,
        symbols=["AAPL", "MSFT"],
        fields=["price", "volume"]
    )


@pytest.fixture
def http_feed_config():
    """Create HTTP feed configuration"""
    return FeedConfiguration(
        feed_id="http_test_feed",
        feed_type=FeedType.MARKET_DATA,
        name="HTTP Test Feed",
        description="HTTP polling feed",
        url="https://api.example.com/data",
        protocol="http",
        api_key="test_key",
        data_format=DataFormat.JSON
    )


@pytest.fixture
def feed_manager():
    """Create feed manager instance"""
    manager = FeedManager()
    return manager


@pytest.fixture
def sample_feed_message():
    """Create sample feed message"""
    return FeedMessage(
        feed_id="test_feed",
        message_id="msg_123",
        timestamp=datetime.now(),
        sequence_number=1,
        message_type="data",
        symbol="AAPL",
        data={"price": 150.25, "volume": 1000},
        latency_ms=5.0
    )


# =============================================================================
# CATEGORY 1: FEED CONFIGURATION (3 tests)
# =============================================================================

class TestFeedConfiguration:
    """Test feed configuration"""

    def test_feed_config_creation(self, feed_config):
        """Test creating feed configuration"""
        assert feed_config.feed_id == "test_feed"
        assert feed_config.feed_type == FeedType.MARKET_DATA
        assert feed_config.protocol == "websocket"
        assert feed_config.api_key == "test_api_key"
        assert len(feed_config.symbols) == 2
        logger.info("✅ Feed config creation test passed")

    def test_feed_config_defaults(self):
        """Test feed configuration default values"""
        config = FeedConfiguration(
            feed_id="minimal_feed",
            feed_type=FeedType.NEWS,
            name="Minimal",
            description="Minimal config",
            url="https://example.com",
            protocol="http"
        )

        assert config.connect_timeout == 30.0
        assert config.reconnect_interval == 5.0
        assert config.buffer_size == 10000
        assert config.enable_data_validation is True
        logger.info("✅ Feed config defaults test passed")

    def test_feed_config_custom_params(self, feed_config):
        """Test custom parameters in feed config"""
        feed_config.custom_params = {'retry_count': 5, 'debug': True}

        assert feed_config.custom_params['retry_count'] == 5
        assert feed_config.custom_params['debug'] is True
        logger.info("✅ Feed config custom params test passed")


# =============================================================================
# CATEGORY 2: FEED MESSAGE (3 tests)
# =============================================================================

class TestFeedMessage:
    """Test feed message functionality"""

    def test_feed_message_creation(self, sample_feed_message):
        """Test creating feed message"""
        assert sample_feed_message.feed_id == "test_feed"
        assert sample_feed_message.message_id == "msg_123"
        assert sample_feed_message.symbol == "AAPL"
        assert sample_feed_message.data["price"] == 150.25
        assert sample_feed_message.latency_ms == 5.0
        logger.info("✅ Feed message creation test passed")

    def test_feed_message_timestamps(self, sample_feed_message):
        """Test feed message timestamp handling"""
        assert sample_feed_message.timestamp is not None
        assert sample_feed_message.received_timestamp is not None
        assert isinstance(sample_feed_message.timestamp, datetime)
        logger.info("✅ Feed message timestamps test passed")

    def test_feed_message_validation_status(self, sample_feed_message):
        """Test feed message validation status"""
        assert sample_feed_message.validation_status == "pending"

        # Update validation status
        sample_feed_message.validation_status = "valid"
        assert sample_feed_message.validation_status == "valid"
        logger.info("✅ Feed message validation status test passed")


# =============================================================================
# CATEGORY 3: FEED STATISTICS (3 tests)
# =============================================================================

class TestFeedStatistics:
    """Test feed statistics"""

    def test_feed_statistics_creation(self):
        """Test creating feed statistics"""
        stats = FeedStatistics(feed_id="test_feed")

        assert stats.feed_id == "test_feed"
        assert stats.total_messages == 0
        assert stats.total_connections == 0
        assert stats.average_latency_ms == 0.0
        logger.info("✅ Feed statistics creation test passed")

    def test_feed_statistics_message_tracking(self):
        """Test message statistics tracking"""
        stats = FeedStatistics(feed_id="test_feed")

        stats.total_messages = 100
        stats.valid_messages = 95
        stats.invalid_messages = 5

        assert stats.total_messages == 100
        assert stats.valid_messages == 95
        assert stats.invalid_messages == 5
        logger.info("✅ Feed statistics message tracking test passed")

    def test_feed_statistics_performance_metrics(self):
        """Test performance metrics in statistics"""
        stats = FeedStatistics(feed_id="test_feed")

        stats.average_latency_ms = 10.5
        stats.message_rate_per_second = 150.0
        stats.bytes_received = 1024 * 1024  # 1MB

        assert stats.average_latency_ms == 10.5
        assert stats.message_rate_per_second == 150.0
        assert stats.bytes_received == 1024 * 1024
        logger.info("✅ Feed statistics performance metrics test passed")


# =============================================================================
# CATEGORY 4: FEED MANAGER INITIALIZATION (3 tests)
# =============================================================================

class TestFeedManagerInitialization:
    """Test feed manager initialization"""

    def test_feed_manager_creation(self, feed_manager):
        """Test creating feed manager"""
        assert feed_manager is not None
        assert len(feed_manager._feeds) == 0
        assert len(feed_manager._feed_configs) == 0
        logger.info("✅ Feed manager creation test passed")

    def test_feed_manager_config(self):
        """Test feed manager with custom config"""
        config = {'monitoring_interval': 30}
        manager = FeedManager(config=config)

        assert manager._monitoring_interval == 30
        logger.info("✅ Feed manager config test passed")

    def test_feed_manager_supported_types(self, feed_manager):
        """Test supported feed types"""
        assert 'websocket' in feed_manager._feed_types
        assert 'http' in feed_manager._feed_types
        assert feed_manager._feed_types['websocket'] == WebSocketFeed
        assert feed_manager._feed_types['http'] == HTTPFeed
        logger.info("✅ Feed manager supported types test passed")


# =============================================================================
# CATEGORY 5: FEED REGISTRATION (3 tests)
# =============================================================================

class TestFeedRegistration:
    """Test feed registration"""

    def test_register_feed(self, feed_manager, feed_config):
        """Test registering a feed"""
        success = feed_manager.register_feed(feed_config)

        assert success is True
        assert feed_config.feed_id in feed_manager._feed_configs
        assert feed_manager._feed_configs[feed_config.feed_id] == feed_config
        logger.info("✅ Register feed test passed")

    def test_register_multiple_feeds(self, feed_manager, feed_config, http_feed_config):
        """Test registering multiple feeds"""
        success1 = feed_manager.register_feed(feed_config)
        success2 = feed_manager.register_feed(http_feed_config)

        assert success1 and success2
        assert len(feed_manager._feed_configs) == 2
        logger.info("✅ Register multiple feeds test passed")

    def test_get_registered_feeds(self, feed_manager, feed_config):
        """Test getting registered feed list"""
        feed_manager.register_feed(feed_config)

        registered = feed_manager.get_registered_feeds()

        assert len(registered) == 1
        assert feed_config.feed_id in registered
        logger.info("✅ Get registered feeds test passed")


# =============================================================================
# CATEGORY 6: MESSAGE HANDLING (4 tests)
# =============================================================================

class TestMessageHandling:
    """Test message handling functionality"""

    def test_add_global_message_handler(self, feed_manager):
        """Test adding global message handler"""
        handler = Mock()

        feed_manager.add_message_handler(handler)

        assert len(feed_manager._global_message_handlers) == 1
        assert feed_manager._global_message_handlers[0] == handler
        logger.info("✅ Add global message handler test passed")

    def test_add_feed_specific_message_handler(self, feed_manager, feed_config):
        """Test adding feed-specific message handler"""
        feed_manager.register_feed(feed_config)
        handler = Mock()

        feed_manager.add_message_handler(handler, feed_id=feed_config.feed_id)

        assert feed_config.feed_id in feed_manager._message_handlers
        assert len(feed_manager._message_handlers[feed_config.feed_id]) == 1
        logger.info("✅ Add feed-specific message handler test passed")

    def test_route_message_to_global_handler(self, feed_manager, sample_feed_message):
        """Test routing message to global handler"""
        handler = Mock()
        feed_manager.add_message_handler(handler)

        feed_manager._route_message(sample_feed_message)

        handler.assert_called_once_with(sample_feed_message)
        logger.info("✅ Route message to global handler test passed")

    def test_route_message_to_feed_handler(self, feed_manager, sample_feed_message):
        """Test routing message to feed-specific handler"""
        handler = Mock()
        feed_manager.add_message_handler(handler, feed_id=sample_feed_message.feed_id)

        feed_manager._route_message(sample_feed_message)

        handler.assert_called_once_with(sample_feed_message)
        logger.info("✅ Route message to feed handler test passed")


# =============================================================================
# CATEGORY 7: ERROR HANDLING (3 tests)
# =============================================================================

class TestErrorHandling:
    """Test error handling functionality"""

    def test_add_global_error_handler(self, feed_manager):
        """Test adding global error handler"""
        handler = Mock()

        feed_manager.add_error_handler(handler)

        assert len(feed_manager._global_error_handlers) == 1
        logger.info("✅ Add global error handler test passed")

    def test_add_feed_specific_error_handler(self, feed_manager, feed_config):
        """Test adding feed-specific error handler"""
        feed_manager.register_feed(feed_config)
        handler = Mock()

        feed_manager.add_error_handler(handler, feed_id=feed_config.feed_id)

        assert feed_config.feed_id in feed_manager._error_handlers
        logger.info("✅ Add feed-specific error handler test passed")

    def test_route_error_to_handler(self, feed_manager):
        """Test routing error to handler"""
        handler = Mock()
        feed_manager.add_error_handler(handler)

        error_msg = "Test error"
        exception = Exception("Test exception")

        feed_manager._route_error(error_msg, exception)

        # Should be called with feed_id, error_msg, exception
        assert handler.call_count == 1
        logger.info("✅ Route error to handler test passed")


# =============================================================================
# CATEGORY 8: FEED STATUS (3 tests)
# =============================================================================

class TestFeedStatus:
    """Test feed status management"""

    def test_get_feed_status_not_found(self, feed_manager):
        """Test getting status for non-existent feed"""
        status = feed_manager.get_feed_status("non_existent")

        assert status['feed_id'] == "non_existent"
        assert status['status'] == 'not_found'
        logger.info("✅ Get feed status (not found) test passed")

    def test_get_all_feeds_status_empty(self, feed_manager):
        """Test getting status for all feeds when none exist"""
        status = feed_manager.get_feed_status()

        assert isinstance(status, dict)
        assert len(status) == 0
        logger.info("✅ Get all feeds status (empty) test passed")

    def test_get_active_feeds_empty(self, feed_manager):
        """Test getting active feeds when none are active"""
        active = feed_manager.get_active_feeds()

        assert isinstance(active, list)
        assert len(active) == 0
        logger.info("✅ Get active feeds (empty) test passed")


# =============================================================================
# CATEGORY 9: SUBSCRIPTIONS (4 tests)
# =============================================================================

class TestSubscriptions:
    """Test subscription management"""

    def test_get_subscriptions_empty(self, feed_manager):
        """Test getting subscriptions when none exist"""
        subscriptions = feed_manager.get_subscriptions()

        assert isinstance(subscriptions, dict)
        assert len(subscriptions) == 0
        logger.info("✅ Get subscriptions (empty) test passed")

    def test_subscription_tracking(self, feed_manager):
        """Test manual subscription tracking"""
        # Manually add subscription for testing
        feed_manager._subscriptions['AAPL'].add('feed_1')
        feed_manager._subscriptions['AAPL'].add('feed_2')

        subscriptions = feed_manager.get_subscriptions()

        assert 'AAPL' in subscriptions
        assert len(subscriptions['AAPL']) == 2
        assert 'feed_1' in subscriptions['AAPL']
        assert 'feed_2' in subscriptions['AAPL']
        logger.info("✅ Subscription tracking test passed")

    def test_multiple_symbol_subscriptions(self, feed_manager):
        """Test tracking multiple symbol subscriptions"""
        feed_manager._subscriptions['AAPL'].add('feed_1')
        feed_manager._subscriptions['MSFT'].add('feed_1')
        feed_manager._subscriptions['TSLA'].add('feed_2')

        subscriptions = feed_manager.get_subscriptions()

        assert len(subscriptions) == 3
        assert 'AAPL' in subscriptions
        assert 'MSFT' in subscriptions
        assert 'TSLA' in subscriptions
        logger.info("✅ Multiple symbol subscriptions test passed")

    def test_unregister_feed_cleans_subscriptions(self, feed_manager, feed_config):
        """Test that unregistering feed cleans up subscriptions"""
        feed_manager.register_feed(feed_config)
        feed_manager._subscriptions['AAPL'].add(feed_config.feed_id)

        # Unregister should clean up
        feed_manager.unregister_feed(feed_config.feed_id)

        # Feed config should be removed
        assert feed_config.feed_id not in feed_manager._feed_configs
        logger.info("✅ Unregister feed cleans subscriptions test passed")


# =============================================================================
# CATEGORY 10: DATA FEED ABSTRACT CLASS (3 tests)
# =============================================================================

class TestDataFeedBase:
    """Test DataFeed base functionality"""

    def test_data_feed_base_initialization(self, feed_config):
        """Test DataFeed initialization via concrete class"""
        # We'll use a mock since DataFeed is abstract
        # Create a simple concrete implementation for testing
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)

        assert feed.config == feed_config
        assert feed.status == FeedStatus.DISCONNECTED
        assert feed.statistics.feed_id == feed_config.feed_id
        logger.info("✅ Data feed base initialization test passed")

    def test_add_message_handler_to_feed(self, feed_config):
        """Test adding message handler to feed"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)
        handler = Mock()

        feed.add_message_handler(handler)

        assert len(feed._message_handlers) == 1
        logger.info("✅ Add message handler to feed test passed")

    def test_feed_get_statistics(self, feed_config):
        """Test getting statistics from feed"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)

        stats = feed.get_statistics()

        assert stats.feed_id == feed_config.feed_id
        assert stats.total_messages == 0
        logger.info("✅ Feed get statistics test passed")


# =============================================================================
# CATEGORY 11: ISYSTEMCOMPONENT LIFECYCLE (6 tests)
# =============================================================================

class TestFeedManagerLifecycle:
    """Test FeedManager lifecycle methods (ISystemComponent)"""

    @pytest.mark.asyncio
    async def test_initialize(self, feed_manager):
        """Test FeedManager initialization"""
        result = await feed_manager.initialize()

        assert result is True
        assert feed_manager.is_initialized is True
        assert feed_manager._performance_monitor == {}
        logger.info("✅ Initialize test passed")

    @pytest.mark.asyncio
    async def test_start_with_monitoring(self, feed_manager):
        """Test starting FeedManager with monitoring enabled"""
        await feed_manager.initialize()

        result = await feed_manager.start()

        assert result is True
        assert feed_manager.is_operational is True
        assert feed_manager._monitoring_task is not None
        assert feed_manager._health_check_task is not None

        # Cleanup
        await feed_manager.stop()
        logger.info("✅ Start with monitoring test passed")

    @pytest.mark.asyncio
    async def test_start_without_monitoring(self, feed_manager):
        """Test starting FeedManager with monitoring disabled"""
        feed_manager.config = {'enable_monitoring': False}
        await feed_manager.initialize()

        result = await feed_manager.start()

        assert result is True
        assert feed_manager.is_operational is True
        # Monitoring tasks should not be started
        assert feed_manager._monitoring_task is None

        await feed_manager.stop()
        logger.info("✅ Start without monitoring test passed")

    @pytest.mark.asyncio
    async def test_start_without_initialization(self, feed_manager):
        """Test starting FeedManager without initialization fails"""
        result = await feed_manager.start()

        assert result is False
        assert feed_manager.is_operational is False
        logger.info("✅ Start without initialization test passed")

    @pytest.mark.asyncio
    async def test_stop(self, feed_manager):
        """Test stopping FeedManager"""
        await feed_manager.initialize()
        await feed_manager.start()

        result = await feed_manager.stop()

        assert result is True
        assert feed_manager.is_operational is False
        logger.info("✅ Stop test passed")

    @pytest.mark.asyncio
    async def test_stop_cancels_monitoring(self, feed_manager):
        """Test that stop cancels monitoring tasks"""
        await feed_manager.initialize()
        await feed_manager.start()

        # Get task references before stop
        monitoring_task = feed_manager._monitoring_task
        health_task = feed_manager._health_check_task

        # Wait a bit to ensure tasks are running
        await asyncio.sleep(0.1)

        await feed_manager.stop()

        # Wait for cancellation to complete
        await asyncio.sleep(0.1)

        # Tasks should be cancelled or done
        assert monitoring_task is None or monitoring_task.cancelled() or monitoring_task.done()
        assert health_task is None or health_task.cancelled() or health_task.done()
        logger.info("✅ Stop cancels monitoring test passed")


# =============================================================================
# CATEGORY 12: HEALTH CHECK & STATUS (4 tests)
# =============================================================================

class TestFeedManagerHealthCheck:
    """Test FeedManager health check and status"""

    @pytest.mark.asyncio
    async def test_health_check_no_feeds(self, feed_manager):
        """Test health check with no feeds"""
        await feed_manager.initialize()
        await feed_manager.start()

        health = await feed_manager.health_check()

        assert health['healthy'] is True  # No feeds means 100% healthy
        assert health['total_feeds'] == 0
        assert health['active_feeds'] == 0
        assert health['health_ratio'] == 1.0

        await feed_manager.stop()
        logger.info("✅ Health check no feeds test passed")

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, feed_manager):
        """Test health check when not initialized"""
        health = await feed_manager.health_check()

        assert health['healthy'] is False
        assert health['initialized'] is False
        logger.info("✅ Health check not initialized test passed")

    @pytest.mark.asyncio
    async def test_get_status(self, feed_manager):
        """Test getting FeedManager status"""
        status = feed_manager.get_status()

        assert status['initialized'] is False
        assert status['operational'] is False
        assert status['component_type'] == 'FeedManager'
        assert status['total_feeds'] == 0
        assert status['active_feeds'] == 0
        logger.info("✅ Get status test passed")

    @pytest.mark.asyncio
    async def test_get_status_after_start(self, feed_manager):
        """Test getting status after starting"""
        await feed_manager.initialize()
        await feed_manager.start()

        status = feed_manager.get_status()

        assert status['initialized'] is True
        assert status['operational'] is True

        await feed_manager.stop()
        logger.info("✅ Get status after start test passed")


# =============================================================================
# CATEGORY 13: FEED CONNECTION/DISCONNECTION (6 tests)
# =============================================================================

class TestFeedConnection:
    """Test feed connection and disconnection"""

    @pytest.mark.asyncio
    async def test_connect_feed_not_registered(self, feed_manager):
        """Test connecting to non-registered feed fails"""
        result = await feed_manager.connect_feed("non_existent")

        assert result is False
        logger.info("✅ Connect feed not registered test passed")

    @pytest.mark.asyncio
    async def test_connect_feed_unsupported_protocol(self, feed_manager):
        """Test connecting with unsupported protocol fails"""
        config = FeedConfiguration(
            feed_id="test_feed",
            feed_type=FeedType.MARKET_DATA,
            name="Test",
            description="Test",
            url="test://example.com",
            protocol="unsupported"
        )
        feed_manager.register_feed(config)

        result = await feed_manager.connect_feed(config.feed_id)

        assert result is False
        logger.info("✅ Connect feed unsupported protocol test passed")

    @pytest.mark.asyncio
    async def test_connect_feed_websocket_mock(self, feed_manager, feed_config):
        """Test connecting WebSocket feed with mocked connection"""
        feed_manager.register_feed(feed_config)

        # Create a mock feed instance
        mock_feed = Mock()
        mock_feed.connect = AsyncMock(return_value=True)
        mock_feed.is_connected = AsyncMock(return_value=True)
        mock_feed.add_message_handler = Mock()
        mock_feed.add_error_handler = Mock()
        mock_feed.status = FeedStatus.CONNECTED

        # Replace the feed class in the dictionary with a factory that returns our mock
        original_ws_class = feed_manager._feed_types['websocket']
        feed_manager._feed_types['websocket'] = lambda config: mock_feed

        try:
            result = await feed_manager.connect_feed(feed_config.feed_id)

            assert result is True
            assert feed_config.feed_id in feed_manager._feeds
        finally:
            # Restore original
            feed_manager._feed_types['websocket'] = original_ws_class

        logger.info("✅ Connect WebSocket feed mock test passed")

    @pytest.mark.asyncio
    async def test_connect_feed_connection_fails(self, feed_manager, feed_config):
        """Test feed connection failure handling"""
        feed_manager.register_feed(feed_config)

        # Mock WebSocketFeed with failed connection
        with patch('core_engine.data.feeds.manager.WebSocketFeed') as MockWSFeed:
            mock_feed = Mock()
            mock_feed.connect = AsyncMock(return_value=False)
            mock_feed.add_message_handler = Mock()
            mock_feed.add_error_handler = Mock()
            MockWSFeed.return_value = mock_feed

            result = await feed_manager.connect_feed(feed_config.feed_id)

            assert result is False
            logger.info("✅ Connect feed connection fails test passed")

    @pytest.mark.asyncio
    async def test_disconnect_feed_not_connected(self, feed_manager):
        """Test disconnecting feed that's not connected"""
        result = await feed_manager.disconnect_feed("non_existent")

        assert result is True  # Should succeed gracefully
        logger.info("✅ Disconnect feed not connected test passed")

    @pytest.mark.asyncio
    async def test_disconnect_feed(self, feed_manager, feed_config):
        """Test disconnecting connected feed"""
        feed_manager.register_feed(feed_config)

        # Mock feed connection
        with patch('core_engine.data.feeds.manager.WebSocketFeed') as MockWSFeed:
            mock_feed = Mock()
            mock_feed.connect = AsyncMock(return_value=True)
            mock_feed.disconnect = AsyncMock(return_value=True)
            mock_feed.add_message_handler = Mock()
            mock_feed.add_error_handler = Mock()
            MockWSFeed.return_value = mock_feed

            # Connect
            await feed_manager.connect_feed(feed_config.feed_id)

            # Disconnect
            result = await feed_manager.disconnect_feed(feed_config.feed_id)

            assert result is True
            assert feed_config.feed_id not in feed_manager._feeds
            logger.info("✅ Disconnect feed test passed")


# =============================================================================
# CATEGORY 14: SYMBOL SUBSCRIPTION (6 tests)
# =============================================================================

class TestSymbolSubscription:
    """Test symbol subscription and unsubscription"""

    @pytest.mark.asyncio
    async def test_subscribe_symbol_no_feeds(self, feed_manager):
        """Test subscribing when no feeds are connected"""
        result = await feed_manager.subscribe_symbol("AAPL")

        assert result is False
        logger.info("✅ Subscribe symbol no feeds test passed")

    @pytest.mark.asyncio
    async def test_subscribe_symbol_mock_feed(self, feed_manager, feed_config):
        """Test subscribing to symbol on mock feed"""
        feed_manager.register_feed(feed_config)

        # Create mock feed
        mock_feed = Mock()
        mock_feed.connect = AsyncMock(return_value=True)
        mock_feed.is_connected = AsyncMock(return_value=True)
        mock_feed.subscribe = AsyncMock(return_value=True)
        mock_feed.add_message_handler = Mock()
        mock_feed.add_error_handler = Mock()
        mock_feed.status = FeedStatus.CONNECTED

        # Replace feed class in dictionary
        original_ws_class = feed_manager._feed_types['websocket']
        feed_manager._feed_types['websocket'] = lambda config: mock_feed

        try:
            # Connect feed
            await feed_manager.connect_feed(feed_config.feed_id)

            # Subscribe to symbol
            result = await feed_manager.subscribe_symbol("AAPL", feed_ids=[feed_config.feed_id])

            assert result is True
            subscriptions = feed_manager.get_subscriptions()
            assert "AAPL" in subscriptions
            assert feed_config.feed_id in subscriptions["AAPL"]
        finally:
            feed_manager._feed_types['websocket'] = original_ws_class

        logger.info("✅ Subscribe symbol mock feed test passed")

    @pytest.mark.asyncio
    async def test_subscribe_symbol_all_feeds(self, feed_manager, feed_config, http_feed_config):
        """Test subscribing to symbol across all feeds"""
        feed_manager.register_feed(feed_config)
        feed_manager.register_feed(http_feed_config)

        # Create mock feeds
        mock_ws_feed = Mock()
        mock_ws_feed.connect = AsyncMock(return_value=True)
        mock_ws_feed.is_connected = AsyncMock(return_value=True)
        mock_ws_feed.subscribe = AsyncMock(return_value=True)
        mock_ws_feed.add_message_handler = Mock()
        mock_ws_feed.add_error_handler = Mock()
        mock_ws_feed.status = FeedStatus.CONNECTED

        mock_http_feed = Mock()
        mock_http_feed.connect = AsyncMock(return_value=True)
        mock_http_feed.is_connected = AsyncMock(return_value=True)
        mock_http_feed.subscribe = AsyncMock(return_value=True)
        mock_http_feed.add_message_handler = Mock()
        mock_http_feed.add_error_handler = Mock()
        mock_http_feed.status = FeedStatus.CONNECTED

        # Replace feed classes in dictionary
        original_ws_class = feed_manager._feed_types['websocket']
        original_http_class = feed_manager._feed_types['http']
        feed_manager._feed_types['websocket'] = lambda config: mock_ws_feed
        feed_manager._feed_types['http'] = lambda config: mock_http_feed

        try:
            # Connect both feeds
            await feed_manager.connect_feed(feed_config.feed_id)
            await feed_manager.connect_feed(http_feed_config.feed_id)

            # Subscribe to symbol (should subscribe to all feeds)
            result = await feed_manager.subscribe_symbol("AAPL")

            assert result is True
            subscriptions = feed_manager.get_subscriptions()
            assert feed_config.feed_id in subscriptions.get("AAPL", [])
            assert http_feed_config.feed_id in subscriptions.get("AAPL", [])
        finally:
            feed_manager._feed_types['websocket'] = original_ws_class
            feed_manager._feed_types['http'] = original_http_class

        logger.info("✅ Subscribe symbol all feeds test passed")

    @pytest.mark.asyncio
    async def test_unsubscribe_symbol(self, feed_manager, feed_config):
        """Test unsubscribing from symbol"""
        feed_manager.register_feed(feed_config)

        # Manually add subscription
        feed_manager._subscriptions['AAPL'].add(feed_config.feed_id)

        # Mock feed
        with patch('core_engine.data.feeds.manager.WebSocketFeed') as MockWSFeed:
            mock_feed = Mock()
            mock_feed.unsubscribe = AsyncMock(return_value=True)
            MockWSFeed.return_value = mock_feed
            feed_manager._feeds[feed_config.feed_id] = mock_feed

            result = await feed_manager.unsubscribe_symbol("AAPL", feed_ids=[feed_config.feed_id])

            assert result is True
            subscriptions = feed_manager.get_subscriptions()
            assert feed_config.feed_id not in subscriptions.get("AAPL", [])
            logger.info("✅ Unsubscribe symbol test passed")

    @pytest.mark.asyncio
    async def test_unsubscribe_symbol_removes_empty(self, feed_manager):
        """Test unsubscribing removes empty subscription entries"""
        feed_manager._subscriptions['AAPL'].add('feed_1')

        # Mock feed
        mock_feed = Mock()
        mock_feed.unsubscribe = AsyncMock(return_value=True)
        feed_manager._feeds['feed_1'] = mock_feed

        await feed_manager.unsubscribe_symbol("AAPL", feed_ids=['feed_1'])

        # Subscription should be removed entirely
        assert "AAPL" not in feed_manager.get_subscriptions()
        logger.info("✅ Unsubscribe removes empty subscription test passed")

    @pytest.mark.asyncio
    async def test_unsubscribe_symbol_not_subscribed(self, feed_manager):
        """Test unsubscribing from symbol that's not subscribed"""
        result = await feed_manager.unsubscribe_symbol("NONEXISTENT")

        # Should succeed gracefully
        assert result is False
        logger.info("✅ Unsubscribe symbol not subscribed test passed")


# =============================================================================
# CATEGORY 15: DATA FEED MESSAGE STATISTICS (4 tests)
# =============================================================================

class TestFeedMessageStatistics:
    """Test feed message statistics updating"""

    def test_update_message_statistics(self, feed_config):
        """Test updating message statistics"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)

        # Create message with latency
        message = FeedMessage(
            feed_id=feed_config.feed_id,
            message_id="msg_1",
            timestamp=datetime.now(),
            sequence_number=1,
            message_type="data",
            symbol="AAPL",
            data={"price": 150.0},
            latency_ms=10.0
        )

        # Handle message (triggers statistics update)
        feed._handle_message(message)

        stats = feed.get_statistics()
        assert stats.total_messages == 1
        assert stats.average_latency_ms == 10.0
        assert stats.first_message_time == message.timestamp
        assert stats.last_message_time == message.timestamp
        logger.info("✅ Update message statistics test passed")

    def test_update_message_statistics_average_latency(self, feed_config):
        """Test average latency calculation with multiple messages"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)

        # Send multiple messages with different latencies
        for i in range(3):
            message = FeedMessage(
                feed_id=feed_config.feed_id,
                message_id=f"msg_{i}",
                timestamp=datetime.now(),
                sequence_number=i,
                message_type="data",
                symbol="AAPL",
                data={"price": 150.0 + i},
                latency_ms=10.0 + i * 5.0
            )
            feed._handle_message(message)

        stats = feed.get_statistics()
        assert stats.total_messages == 3
        # Average should be (10 + 15 + 20) / 3 = 15.0
        assert abs(stats.average_latency_ms - 15.0) < 0.01
        logger.info("✅ Update message statistics average latency test passed")

    def test_message_rate_calculation(self, feed_config):
        """Test message rate calculation"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)

        base_time = datetime.now()

        # Send messages with timestamps
        for i in range(5):
            message = FeedMessage(
                feed_id=feed_config.feed_id,
                message_id=f"msg_{i}",
                timestamp=base_time,
                sequence_number=i,
                message_type="data",
                symbol="AAPL",
                data={"price": 150.0}
            )
            feed._handle_message(message)

        stats = feed.get_statistics()
        assert stats.total_messages == 5
        # Rate should be calculated
        assert stats.message_rate_per_second >= 0
        logger.info("✅ Message rate calculation test passed")

    def test_get_recent_messages(self, feed_config):
        """Test getting recent messages from buffer"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)

        # Add messages
        for i in range(10):
            message = FeedMessage(
                feed_id=feed_config.feed_id,
                message_id=f"msg_{i}",
                timestamp=datetime.now(),
                sequence_number=i,
                message_type="data",
                symbol="AAPL",
                data={"price": 150.0 + i}
            )
            feed._handle_message(message)

        # Get recent messages
        recent = feed.get_recent_messages(count=5)

        assert len(recent) == 5
        # Should be last 5 messages
        assert recent[-1].data["price"] == 159.0
        logger.info("✅ Get recent messages test passed")


# =============================================================================
# CATEGORY 16: FEED STATUS HANDLERS (3 tests)
# =============================================================================

class TestFeedStatusHandling:
    """Test feed status change handling"""

    def test_add_status_handler(self, feed_config):
        """Test adding status change handler"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)
        handler = Mock()

        feed.add_status_handler(handler)

        assert len(feed._status_handlers) == 1

        # Trigger status change
        feed._set_status(FeedStatus.CONNECTING)

        handler.assert_called_once_with(FeedStatus.CONNECTING)
        logger.info("✅ Add status handler test passed")

    def test_status_handler_error_handling(self, feed_config):
        """Test status handler error doesn't break feed"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)

        def failing_handler(status):
            raise Exception("Handler error")

        feed.add_status_handler(failing_handler)

        # Should not raise exception
        feed._set_status(FeedStatus.CONNECTING)

        assert feed.status == FeedStatus.CONNECTING
        logger.info("✅ Status handler error handling test passed")

    def test_set_status_only_on_change(self, feed_config):
        """Test status only changes when different"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)
        handler = Mock()

        feed.add_status_handler(handler)

        # Set same status twice
        feed._set_status(FeedStatus.DISCONNECTED)
        feed._set_status(FeedStatus.DISCONNECTED)

        # Handler should only be called once (on first change from initial state)
        # Actually, initial state is DISCONNECTED, so handler might be called twice
        # But if we change, then set same, it shouldn't be called again
        feed._set_status(FeedStatus.CONNECTING)
        handler.reset_mock()
        feed._set_status(FeedStatus.CONNECTING)  # Same status

        # Handler shouldn't be called again for same status
        handler.assert_not_called()
        logger.info("✅ Set status only on change test passed")


# =============================================================================
# CATEGORY 17: CLEANUP & MONITORING (4 tests)
# =============================================================================

class TestCleanupAndMonitoring:
    """Test cleanup and monitoring functionality"""

    @pytest.mark.asyncio
    async def test_cleanup(self, feed_manager):
        """Test FeedManager cleanup"""
        await feed_manager.initialize()
        await feed_manager.start()

        # Add mock feed
        mock_feed = Mock()
        mock_feed.disconnect = AsyncMock(return_value=True)
        feed_manager._feeds['test_feed'] = mock_feed

        await feed_manager.cleanup()

        # Wait a bit for tasks to be cancelled
        await asyncio.sleep(0.1)

        # Monitoring should be stopped (tasks cancelled or done)
        if feed_manager._monitoring_task:
            assert feed_manager._monitoring_task.cancelled() or feed_manager._monitoring_task.done()
        # Feed should be disconnected
        mock_feed.disconnect.assert_called_once()
        logger.info("✅ Cleanup test passed")

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, feed_manager):
        """Test stopping monitoring"""
        await feed_manager.initialize()
        await feed_manager.start()

        monitoring_task = feed_manager._monitoring_task
        health_task = feed_manager._health_check_task

        # Wait a bit to ensure tasks are running
        await asyncio.sleep(0.1)

        await feed_manager.stop_monitoring()

        # Wait for cancellation
        await asyncio.sleep(0.1)

        # Tasks should be cancelled or done
        assert monitoring_task is None or monitoring_task.cancelled() or monitoring_task.done()
        assert health_task is None or health_task.cancelled() or health_task.done()
        logger.info("✅ Stop monitoring test passed")

    @pytest.mark.asyncio
    async def test_performance_monitoring_timeout(self, feed_manager):
        """Test performance monitoring with timeout"""
        await feed_manager.initialize()
        feed_manager._monitoring_interval = 0.1  # Short interval for testing

        # Start monitoring
        task = asyncio.create_task(feed_manager._performance_monitoring())

        # Wait a bit then cancel
        await asyncio.sleep(0.2)
        task.cancel()

        # Should complete without error
        try:
            await task
        except asyncio.CancelledError:
            pass

        logger.info("✅ Performance monitoring timeout test passed")

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, feed_manager):
        """Test health check monitoring with timeout"""
        await feed_manager.initialize()

        # Start health check
        task = asyncio.create_task(feed_manager._health_check())

        # Wait a bit then cancel
        await asyncio.sleep(0.1)
        task.cancel()

        # Should complete without error
        try:
            await task
        except asyncio.CancelledError:
            pass

        logger.info("✅ Health check timeout test passed")


# =============================================================================
# CATEGORY 18: ERROR HANDLING SCENARIOS (4 tests)
# =============================================================================

class TestErrorHandlingScenarios:
    """Test error handling in various scenarios"""

    @pytest.mark.asyncio
    async def test_connect_feed_exception(self, feed_manager, feed_config):
        """Test exception handling during feed connection"""
        feed_manager.register_feed(feed_config)

        # Mock feed that raises exception
        with patch('core_engine.data.feeds.manager.WebSocketFeed') as MockWSFeed:
            MockWSFeed.side_effect = Exception("Connection error")

            result = await feed_manager.connect_feed(feed_config.feed_id)

            assert result is False
            logger.info("✅ Connect feed exception test passed")

    @pytest.mark.asyncio
    async def test_disconnect_feed_exception(self, feed_manager, feed_config):
        """Test exception handling during feed disconnection"""
        # Add feed that raises exception on disconnect
        mock_feed = Mock()
        mock_feed.disconnect = AsyncMock(side_effect=Exception("Disconnect error"))
        feed_manager._feeds[feed_config.feed_id] = mock_feed

        result = await feed_manager.disconnect_feed(feed_config.feed_id)

        # Should handle gracefully
        assert result is False
        logger.info("✅ Disconnect feed exception test passed")

    def test_message_handler_exception(self, feed_manager, sample_feed_message):
        """Test exception in message handler doesn't break routing"""
        handler1 = Mock()
        handler2 = Mock(side_effect=Exception("Handler error"))
        handler3 = Mock()

        feed_manager.add_message_handler(handler1)
        feed_manager.add_message_handler(handler2)
        feed_manager.add_message_handler(handler3)

        # Should route to all handlers despite exception
        feed_manager._route_message(sample_feed_message)

        handler1.assert_called_once()
        handler2.assert_called_once()
        handler3.assert_called_once()  # Should still be called
        logger.info("✅ Message handler exception test passed")

    def test_error_handler_exception(self, feed_manager):
        """Test exception in error handler doesn't break routing"""
        handler1 = Mock()
        handler2 = Mock(side_effect=Exception("Handler error"))
        handler3 = Mock()

        feed_manager.add_error_handler(handler1)
        feed_manager.add_error_handler(handler2)
        feed_manager.add_error_handler(handler3)

        error_msg = "Test error"
        exception = Exception("Test exception")

        # Should route to all handlers despite exception
        feed_manager._route_error(error_msg, exception)

        assert handler1.call_count == 1
        assert handler2.call_count == 1
        assert handler3.call_count == 1  # Should still be called
        logger.info("✅ Error handler exception test passed")


# =============================================================================
# CATEGORY 19: DATA FEED BASE CLASS ADVANCED (3 tests)
# =============================================================================

class TestDataFeedAdvanced:
    """Test advanced DataFeed base class functionality"""

    def test_feed_handle_error(self, feed_config):
        """Test feed error handling"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)
        error_handler = Mock()

        feed.add_error_handler(error_handler)

        error_msg = "Test error"
        exception = Exception("Test exception")
        feed._handle_error(error_msg, exception)

        error_handler.assert_called_once_with(error_msg, exception)
        assert feed.statistics.connection_errors == 1
        logger.info("✅ Feed handle error test passed")

    def test_feed_buffer_limit(self, feed_config):
        """Test feed message buffer respects size limit"""
        # Set small buffer size
        feed_config.buffer_size = 5

        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)

        # Add more messages than buffer size
        for i in range(10):
            message = FeedMessage(
                feed_id=feed_config.feed_id,
                message_id=f"msg_{i}",
                timestamp=datetime.now(),
                sequence_number=i,
                message_type="data",
                symbol="AAPL",
                data={"price": 150.0}
            )
            feed._handle_message(message)

        # Buffer should only contain last 5 messages
        recent = feed.get_recent_messages(count=10)
        assert len(recent) == 5
        logger.info("✅ Feed buffer limit test passed")

    def test_feed_message_sequence_tracking(self, feed_config):
        """Test feed sequence number tracking"""
        class TestFeed(DataFeed):
            async def connect(self): return True
            async def disconnect(self): return True
            async def subscribe(self, symbols, fields=None): return True
            async def unsubscribe(self, symbols=None): return True
            async def is_connected(self): return True

        feed = TestFeed(feed_config)

        # Send messages with sequence numbers
        for seq in range(1, 6):
            message = FeedMessage(
                feed_id=feed_config.feed_id,
                message_id=f"msg_{seq}",
                timestamp=datetime.now(),
                sequence_number=seq,
                message_type="data",
                symbol="AAPL",
                data={"price": 150.0}
            )
            feed._handle_message(message)

        # Statistics should track all messages
        stats = feed.get_statistics()
        assert stats.total_messages == 5
        logger.info("✅ Feed message sequence tracking test passed")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
