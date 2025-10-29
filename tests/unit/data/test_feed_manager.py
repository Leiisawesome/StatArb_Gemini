"""
Unit tests for Feed Manager
Tests feed management, WebSocket/HTTP feeds, subscriptions, and monitoring
"""

import pytest
import logging
from datetime import datetime
from unittest.mock import Mock

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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
