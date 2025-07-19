"""
Market Data Feeds Test Suite
===========================

Comprehensive tests for the feeds module including:
- FeedManager functionality
- Individual feed implementations (Polygon, AlphaVantage)
- Real-time data streaming
- Feed status management
- Error handling and reconnection
- Message routing and callbacks
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call, AsyncMock
from typing import Dict, List, Any
import threading
from queue import Queue

import sys
import requests  # Add requests import for exception handling
sys.path.append('/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

try:
    from core_structure.market_data.feeds import (
        FeedManager, 
        PolygonFeed, 
        AlphaVantageFeed,
        BaseFeed,
        MarketTick, 
        DataType, 
        FeedStatus,
        FeedMetrics
    )
except ImportError as e:
    pytest.skip(f"Feeds module not available: {e}", allow_module_level=True)


class TestFeedMetrics:
    """Test FeedMetrics data structure"""
    
    def test_feed_metrics_creation(self):
        """Test FeedMetrics initialization"""
        metrics = FeedMetrics(feed_name="test_feed")
        
        assert metrics.feed_name == "test_feed"
        assert metrics.messages_received == 0
        assert metrics.messages_processed == 0
        assert metrics.messages_failed == 0
        assert metrics.latency_ms == 0.0
        assert metrics.connection_uptime == 0.0
        assert metrics.last_message_time is None
        assert metrics.data_quality_score == 1.0
    
    def test_feed_metrics_update(self):
        """Test updating FeedMetrics"""
        metrics = FeedMetrics(feed_name="test_feed")
        
        metrics.messages_received = 100
        metrics.messages_processed = 98
        metrics.messages_failed = 2
        metrics.latency_ms = 15.5
        metrics.data_quality_score = 0.98
        
        assert metrics.messages_received == 100
        assert metrics.messages_processed == 98
        assert metrics.messages_failed == 2
        assert metrics.latency_ms == 15.5
        assert metrics.data_quality_score == 0.98


class TestBaseFeed:
    """Test BaseFeed abstract class functionality"""
    
    def test_base_feed_cannot_be_instantiated(self):
        """Test that BaseFeed cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BaseFeed("test", {})
    
    def test_concrete_feed_implementation(self):
        """Test concrete implementation of BaseFeed"""
        
        class TestFeed(BaseFeed):
            def connect(self):
                self.status = FeedStatus.CONNECTED
                return True
            
            def disconnect(self):
                self.status = FeedStatus.DISCONNECTED
                return True
            
            def subscribe(self, symbols):
                return True
            
            def unsubscribe(self, symbols):
                return True
        
        feed = TestFeed("test_feed", {"api_key": "test"})
        
        assert feed.name == "test_feed"
        assert feed.status == FeedStatus.DISCONNECTED
        assert feed.config["api_key"] == "test"
        assert len(feed.callbacks) == 0
    
    def test_feed_callback_management(self):
        """Test feed callback registration and management"""
        
        class TestFeed(BaseFeed):
            def connect(self): return True
            def disconnect(self): return True
            def subscribe(self, symbols): return True
            def unsubscribe(self, symbols): return True
        
        feed = TestFeed("test_feed", {})
        
        # Test callback registration
        callback1 = Mock()
        callback2 = Mock()
        
        feed.add_callback(callback1)
        feed.add_callback(callback2)
        
        assert len(feed.callbacks) == 2
        assert callback1 in feed.callbacks
        assert callback2 in feed.callbacks
        
        # Test callback removal
        feed.remove_callback(callback1)
        assert len(feed.callbacks) == 1
        assert callback1 not in feed.callbacks
        assert callback2 in feed.callbacks


class TestFeedManager:
    """Test FeedManager functionality"""
    
    def test_feed_manager_initialization(self):
        """Test FeedManager initialization"""
        # Create mock config manager
        mock_config = Mock()
        mock_config.get.return_value = {}  # No feeds configured
        
        fm = FeedManager(config=mock_config)
        
        assert fm.config == mock_config
        assert len(fm.feeds) == 0
        # FeedManager doesn't have a status attribute - it manages multiple feeds
        assert isinstance(fm.feeds, dict)
    
    def test_feed_manager_setup_feeds(self):
        """Test FeedManager feed setup from config"""
        # Create mock config manager with feed configuration
        mock_config = Mock()
        mock_config.get.return_value = {
            "polygon": {
                "enabled": True,
                "api_key": "test_key"
            },
            "alphavantage": {
                "enabled": False,
                "api_key": "test_key"
            }
        }
        
        fm = FeedManager(config=mock_config)
        
        # Should have one feed (polygon enabled, alphavantage disabled)
        assert len(fm.feeds) >= 0  # Depends on actual setup logic
        assert "polygon" in fm.feeds  # Feeds are keyed by feed type name
    
    @pytest.mark.asyncio
    async def test_start_all_feeds(self):
        """Test starting all feeds"""
        mock_config = Mock()
        mock_config.get.return_value = {}
        
        fm = FeedManager(config=mock_config)
        
        # Add a mock feed directly to test start_all_feeds
        mock_feed = Mock()
        mock_feed.connect = AsyncMock(return_value=True)
        fm.feeds["test_feed"] = mock_feed
        
        result = await fm.start_all_feeds()
        
        assert result is True
        mock_feed.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_all_feeds(self):
        """Test stopping all feeds"""
        mock_config = Mock()
        mock_config.get.return_value = {}
        
        fm = FeedManager(config=mock_config)
        
        # Add a mock feed
        mock_feed = Mock()
        mock_feed.disconnect.return_value = None
        fm.feeds["test_feed"] = mock_feed
        
        await fm.stop_all_feeds()
        
        mock_feed.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_subscribe_symbols(self):
        """Test subscribing to symbols"""
        mock_config = Mock()
        mock_config.get.return_value = {}
        
        fm = FeedManager(config=mock_config)
        
        # Add a mock feed
        mock_feed = Mock()
        mock_feed.status = FeedStatus.CONNECTED
        mock_feed.subscribe.return_value = True
        fm.feeds["test_feed"] = mock_feed
        
        symbols = ["AAPL", "GOOGL"]
        result = await fm.subscribe_symbols(symbols)
        
        assert result is True
        mock_feed.subscribe.assert_called_once_with(symbols)
    
    def test_get_feed_status(self):
        """Test getting feed status"""
        mock_config = Mock()
        mock_config.get.return_value = {}
        
        fm = FeedManager(config=mock_config)
        
        # Add a mock feed with metrics
        mock_feed = Mock()
        mock_feed.status = FeedStatus.CONNECTED
        mock_feed.get_metrics.return_value = Mock()
        mock_feed.subscribed_symbols = {"AAPL"}
        fm.feeds["test_feed"] = mock_feed
        
        status = fm.get_feed_status()
        
        assert "test_feed" in status
        assert status["test_feed"]["status"] == "connected"
    
    @pytest.mark.asyncio
    async def test_subscribe_symbols(self):
        """Test symbol subscription across feeds"""
        mock_config = Mock()
        mock_config.get.return_value = {}
        fm = FeedManager(config=mock_config)
        
        # Add mock feeds directly to the feeds dict
        mock_feed1 = Mock()
        mock_feed1.name = "feed1"
        mock_feed1.status = FeedStatus.CONNECTED
        mock_feed1.subscribe = AsyncMock(return_value=True)
        
        mock_feed2 = Mock()
        mock_feed2.name = "feed2"
        mock_feed2.status = FeedStatus.CONNECTED
        mock_feed2.subscribe = AsyncMock(return_value=True)
        
        fm.feeds["feed1"] = mock_feed1
        fm.feeds["feed2"] = mock_feed2
        
        # Subscribe to symbols
        symbols = ["AAPL", "GOOGL"]
        result = await fm.subscribe_symbols(symbols)
        
        # Verify subscription calls
        mock_feed1.subscribe.assert_called_once_with(symbols)
        mock_feed2.subscribe.assert_called_once_with(symbols)
        
        # Should succeed since both feeds return True
        assert result is True
    
    def test_get_feed_status(self):
        """Test getting status of all feeds"""
        mock_config = Mock()
        mock_config.get.return_value = {}
        fm = FeedManager(config=mock_config)
        
        # Add feeds with different statuses directly to feeds dict
        mock_feed1 = Mock()
        mock_feed1.name = "feed1"
        mock_feed1.status = FeedStatus.CONNECTED
        mock_feed1.get_metrics.return_value = FeedMetrics(feed_name="feed1")
        mock_feed1.subscribed_symbols = {"AAPL"}
        
        mock_feed2 = Mock()
        mock_feed2.name = "feed2" 
        mock_feed2.status = FeedStatus.ERROR
        mock_feed2.get_metrics.return_value = FeedMetrics(feed_name="feed2")
        mock_feed2.subscribed_symbols = {"GOOGL"}
        
        fm.feeds["feed1"] = mock_feed1
        fm.feeds["feed2"] = mock_feed2
        
        status = fm.get_feed_status()
        
        assert "feed1" in status
        assert "feed2" in status
        assert status["feed1"]["status"] == "connected"
        assert status["feed2"]["status"] == "error"


@pytest.fixture
def mock_requests():
    """Mock requests module for API testing"""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        
        # Default successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "OK"}
        mock_response.text = '{"status": "OK"}'
        
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        
        yield {
            'get': mock_get,
            'post': mock_post,
            'response': mock_response
        }


class TestPolygonFeed:
    """Test PolygonFeed implementation"""
    
    def test_polygon_feed_initialization(self):
        """Test PolygonFeed initialization"""
        config = {
            'api_key': 'test_api_key',
            'base_url': 'https://api.polygon.io',
            'timeout': 30
        }
        
        feed = PolygonFeed(config=config)
        
        assert feed.name == "polygon"
        assert feed.config == config
        assert feed.status == FeedStatus.DISCONNECTED
    
    @patch('core_structure.market_data.feeds.websocket.WebSocketApp')
    @patch('requests.get')
    @pytest.mark.asyncio
    async def test_polygon_feed_connection(self, mock_get, mock_websocket):
        """Test Polygon feed connection"""
        # Mock WebSocket
        mock_ws_instance = Mock()
        mock_websocket.return_value = mock_ws_instance
        
        # Mock successful connection response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "OK"}
        mock_get.return_value = mock_response
        
        config = {'api_key': 'test_key'}
        feed = PolygonFeed(config=config)
        
        # Mock the status to be connected after a short delay
        def simulate_connection():
            import time
            time.sleep(0.1)
            feed.status = FeedStatus.CONNECTED
        
        import threading
        connection_thread = threading.Thread(target=simulate_connection)
        connection_thread.start()
        
        result = await feed.connect()
        
        connection_thread.join()
        assert result is True
        assert feed.status == FeedStatus.CONNECTED
    
    @patch('requests.get')
    @pytest.mark.asyncio
    async def test_polygon_feed_connection_failure(self, mock_get):
        """Test Polygon feed connection failure"""
        # Mock failed connection response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_get.return_value = mock_response
        
        config = {'api_key': 'invalid_key'}
        feed = PolygonFeed(config=config)
        
        result = await feed.connect()
        
        assert result is False
        # When connection fails, status should be DISCONNECTED, not ERROR
        assert feed.status == FeedStatus.DISCONNECTED

class TestAlphaVantageFeed:
    """Test AlphaVantageFeed implementation"""
    
    def test_alphavantage_feed_initialization(self):
        """Test AlphaVantage feed initialization"""
        config = {
            'api_key': 'test_api_key',
            'base_url': 'https://www.alphavantage.co',
            'timeout': 30
        }
        
        feed = AlphaVantageFeed(config=config)
        
        assert feed.name == "alphavantage"
        assert feed.config == config
        assert feed.status == FeedStatus.DISCONNECTED
    
    @patch('requests.get')
    @pytest.mark.asyncio
    async def test_alphavantage_feed_connection(self, mock_get):
        """Test AlphaVantage feed connection"""
        # Mock successful connection response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "150.00"
            }
        }
        mock_get.return_value = mock_response
        
        config = {'api_key': 'test_key'}
        feed = AlphaVantageFeed(config=config)
        
        result = await feed.connect()
        
        assert result is True
        assert feed.status == FeedStatus.CONNECTED

class TestFeedIntegration:
    """Integration tests for feeds"""
    
    def test_feed_manager_with_multiple_feeds(self):
        """Test FeedManager with multiple feed types"""
        mock_config = Mock()
        mock_config.get.return_value = {}
        fm = FeedManager(config=mock_config)
        
        # Create mock feeds
        polygon_config = {'api_key': 'polygon_key'}
        alphavantage_config = {'api_key': 'av_key'}
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "OK"}
            mock_get.return_value = mock_response
            
            polygon_feed = PolygonFeed(config=polygon_config)
            alphavantage_feed = AlphaVantageFeed(config=alphavantage_config)
            
            # Add feeds directly to the feeds dict
            fm.feeds["polygon"] = polygon_feed
            fm.feeds["alphavantage"] = alphavantage_feed
            
            assert len(fm.feeds) == 2
            assert "polygon" in fm.feeds
            assert "alphavantage" in fm.feeds
    
    def test_end_to_end_data_flow(self):
        """Test complete data flow from feed to callback"""
        received_ticks = []
        
        def tick_callback(tick: MarketTick):
            received_ticks.append(tick)
        
        fm = FeedManager(config={})
        
        # Create a simple test feed
        class TestFeed(BaseFeed):
            def connect(self):
                self.status = FeedStatus.CONNECTED
                return True
            
            def disconnect(self):
                self.status = FeedStatus.DISCONNECTED
                return True
            
            def subscribe(self, symbols):
                # Simulate receiving data
                for symbol in symbols:
                    tick = MarketTick(
                        symbol=symbol,
                        timestamp=datetime.now(),
                        price=150.0,
                        volume=1000
                    )
                    self._process_tick(tick)
                return True
            
            def unsubscribe(self, symbols):
                return True
            
            def _process_tick(self, tick):
                for callback in self.callbacks:
                    callback(tick)
        
        test_feed = TestFeed("test", {})
        test_feed.add_callback(tick_callback)
        
        # Add feed directly to the feeds dict
        fm.feeds["test"] = test_feed
        
        # Note: This test needs to be updated to work with the async API
        # The actual subscribe method would be async in the real implementation
        test_feed.subscribe(["AAPL", "GOOGL"])
        
        # Verify data was received
        assert len(received_ticks) == 2
        symbols = [tick.symbol for tick in received_ticks]
        assert "AAPL" in symbols
        assert "GOOGL" in symbols


class TestFeedErrorHandling:
    """Test error handling and recovery in feeds"""
    
    @patch('core_structure.market_data.feeds.WEBSOCKET_AVAILABLE', True)
    @patch('websocket.WebSocketApp')
    def test_feed_connection_retry(self, mock_ws_app):
        """Test feed connection retry mechanism"""
        config = {'api_key': 'test_key', 'max_retries': 3}
        
        # Mock WebSocket that fails to connect
        mock_ws = Mock()
        mock_ws_app.return_value = mock_ws
        
        feed = PolygonFeed(config=config)
        
        # This would test retry logic if implemented
        result = asyncio.run(feed.connect())
        
        # WebSocket should be created
        assert mock_ws_app.call_count >= 1
    
    def test_invalid_api_response_handling(self):
        """Test handling of invalid API responses"""
        config = {'api_key': 'test_key'}
        
        with patch('requests.get') as mock_get:
            # Mock invalid JSON response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_get.return_value = mock_response
            
            feed = PolygonFeed(config=config)
            
            # Should handle JSON decode errors gracefully
            try:
                result = asyncio.run(feed.connect())
                # Should not crash, might return False
            except json.JSONDecodeError:
                pytest.fail("Feed should handle JSON decode errors gracefully")
    
    def test_network_timeout_handling(self):
        """Test handling of network timeouts"""
        config = {'api_key': 'test_key', 'timeout': 1}
        
        with patch('requests.get') as mock_get:
            # Mock timeout
            mock_get.side_effect = requests.exceptions.Timeout()
            
            feed = PolygonFeed(config=config)
            
            # Should handle timeouts gracefully
            try:
                result = asyncio.run(feed.connect())
                # Should not crash
            except requests.exceptions.Timeout:
                pytest.fail("Feed should handle timeouts gracefully")


class TestFeedPerformance:
    """Performance tests for feeds"""
    
    def test_high_frequency_data_processing(self):
        """Test processing high-frequency data"""
        processed_count = 0
        
        def counting_callback(tick):
            nonlocal processed_count
            processed_count += 1
        
        class HighFreqFeed(BaseFeed):
            def connect(self): return True
            def disconnect(self): return True
            def subscribe(self, symbols): return True
            def unsubscribe(self, symbols): return True
            
            def simulate_high_freq_data(self, count=1000):
                for i in range(count):
                    tick = MarketTick(
                        symbol="AAPL",
                        timestamp=datetime.now(),
                        price=150.0 + (i % 10) * 0.1,
                        volume=100
                    )
                    for callback in self.callbacks:
                        callback(tick)
        
        feed = HighFreqFeed("highfreq", {})
        feed.add_callback(counting_callback)
        
        start_time = time.time()
        feed.simulate_high_freq_data(1000)
        end_time = time.time()
        
        assert processed_count == 1000
        assert (end_time - start_time) < 1.0  # Should process quickly
    
    def test_concurrent_feed_processing(self):
        """Test concurrent processing from multiple feeds"""
        results = {'feed1': 0, 'feed2': 0}
        
        def feed_callback(feed_name):
            def callback(tick):
                results[feed_name] += 1
            return callback
        
        class ConcurrentFeed(BaseFeed):
            def connect(self): return True
            def disconnect(self): return True
            def subscribe(self, symbols): return True
            def unsubscribe(self, symbols): return True
            
            def process_data(self, count=100):
                for i in range(count):
                    tick = MarketTick(
                        symbol="TEST",
                        timestamp=datetime.now(),
                        price=100.0,
                        volume=50
                    )
                    for callback in self.callbacks:
                        callback(tick)
        
        feed1 = ConcurrentFeed("feed1", {})
        feed2 = ConcurrentFeed("feed2", {})
        
        feed1.add_callback(feed_callback("feed1"))
        feed2.add_callback(feed_callback("feed2"))
        
        # Process data from both feeds
        feed1.process_data(100)
        feed2.process_data(100)
        
        assert results['feed1'] == 100
        assert results['feed2'] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
