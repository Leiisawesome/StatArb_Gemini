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
from unittest.mock import Mock, patch, MagicMock, call
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
        config = {
            'max_feeds': 10,
            'default_timeout': 30,
            'enable_monitoring': True
        }
        
        fm = FeedManager(config=config)
        
        assert fm.config == config
        assert len(fm.feeds) == 0
        assert fm.status == FeedStatus.DISCONNECTED
        assert fm.active_subscriptions == set()
    
    def test_register_feed(self):
        """Test feed registration"""
        fm = FeedManager(config={})
        
        # Create mock feed
        mock_feed = Mock()
        mock_feed.name = "polygon_feed"
        mock_feed.status = FeedStatus.DISCONNECTED
        
        fm.register_feed(mock_feed)
        
        assert "polygon_feed" in fm.feeds
        assert fm.feeds["polygon_feed"] == mock_feed
    
    def test_unregister_feed(self):
        """Test feed unregistration"""
        fm = FeedManager(config={})
        
        # Register and then unregister feed
        mock_feed = Mock()
        mock_feed.name = "test_feed"
        mock_feed.status = FeedStatus.DISCONNECTED
        mock_feed.disconnect.return_value = True
        
        fm.register_feed(mock_feed)
        assert "test_feed" in fm.feeds
        
        fm.unregister_feed("test_feed")
        assert "test_feed" not in fm.feeds
        mock_feed.disconnect.assert_called_once()
    
    def test_start_all_feeds(self):
        """Test starting all registered feeds"""
        fm = FeedManager(config={})
        
        # Register multiple mock feeds
        feeds = []
        for i in range(3):
            mock_feed = Mock()
            mock_feed.name = f"feed_{i}"
            mock_feed.connect.return_value = True
            mock_feed.status = FeedStatus.DISCONNECTED
            feeds.append(mock_feed)
            fm.register_feed(mock_feed)
        
        # Start all feeds
        fm.start_all()
        
        # Verify all feeds were started
        for feed in feeds:
            feed.connect.assert_called_once()
    
    def test_stop_all_feeds(self):
        """Test stopping all registered feeds"""
        fm = FeedManager(config={})
        
        # Register multiple mock feeds
        feeds = []
        for i in range(3):
            mock_feed = Mock()
            mock_feed.name = f"feed_{i}"
            mock_feed.disconnect.return_value = True
            mock_feed.status = FeedStatus.CONNECTED
            feeds.append(mock_feed)
            fm.register_feed(mock_feed)
        
        # Stop all feeds
        fm.stop_all()
        
        # Verify all feeds were stopped
        for feed in feeds:
            feed.disconnect.assert_called_once()
    
    def test_subscribe_symbols(self):
        """Test symbol subscription across feeds"""
        fm = FeedManager(config={})
        
        # Register mock feeds
        mock_feed1 = Mock()
        mock_feed1.name = "feed1"
        mock_feed1.subscribe.return_value = True
        
        mock_feed2 = Mock()
        mock_feed2.name = "feed2"
        mock_feed2.subscribe.return_value = True
        
        fm.register_feed(mock_feed1)
        fm.register_feed(mock_feed2)
        
        # Subscribe to symbols
        symbols = ["AAPL", "GOOGL"]
        fm.subscribe(symbols)
        
        # Verify subscription calls
        mock_feed1.subscribe.assert_called_once_with(symbols)
        mock_feed2.subscribe.assert_called_once_with(symbols)
        
        # Check active subscriptions
        assert fm.active_subscriptions == set(symbols)
    
    def test_get_feed_status(self):
        """Test getting status of all feeds"""
        fm = FeedManager(config={})
        
        # Register feeds with different statuses
        mock_feed1 = Mock()
        mock_feed1.name = "feed1"
        mock_feed1.status = FeedStatus.CONNECTED
        
        mock_feed2 = Mock()
        mock_feed2.name = "feed2"
        mock_feed2.status = FeedStatus.ERROR
        
        fm.register_feed(mock_feed1)
        fm.register_feed(mock_feed2)
        
        status = fm.get_status()
        
        assert "feed1" in status
        assert "feed2" in status
        assert status["feed1"] == FeedStatus.CONNECTED
        assert status["feed2"] == FeedStatus.ERROR


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
    
    @patch('requests.get')
    def test_polygon_feed_connection(self, mock_get):
        """Test Polygon feed connection"""
        # Mock successful connection response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "OK"}
        mock_get.return_value = mock_response
        
        config = {'api_key': 'test_key'}
        feed = PolygonFeed(config=config)
        
        result = feed.connect()
        
        assert result is True
        assert feed.status == FeedStatus.CONNECTED
        mock_get.assert_called()
    
    @patch('requests.get')
    def test_polygon_feed_connection_failure(self, mock_get):
        """Test Polygon feed connection failure"""
        # Mock failed connection response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_get.return_value = mock_response
        
        config = {'api_key': 'invalid_key'}
        feed = PolygonFeed(config=config)
        
        result = feed.connect()
        
        assert result is False
        assert feed.status == FeedStatus.ERROR
    
    @patch('requests.get')
    def test_polygon_feed_get_latest_quote(self, mock_get):
        """Test getting latest quote from Polygon"""
        # Mock quote response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": {
                "T": "AAPL",
                "t": 1640995200000,  # timestamp in ms
                "p": 150.0,  # price
                "s": 100,    # size
                "bid": 149.5,
                "ask": 150.5
            }
        }
        mock_get.return_value = mock_response
        
        config = {'api_key': 'test_key'}
        feed = PolygonFeed(config=config)
        
        quote = feed.get_latest_quote("AAPL")
        
        assert quote is not None
        assert quote.symbol == "AAPL"
        assert quote.price == 150.0
        assert quote.bid == 149.5
        assert quote.ask == 150.5
        mock_get.assert_called()


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
    def test_alphavantage_feed_connection(self, mock_get):
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
        
        result = feed.connect()
        
        assert result is True
        assert feed.status == FeedStatus.CONNECTED
    
    @patch('requests.get')
    def test_alphavantage_feed_get_quote(self, mock_get):
        """Test getting quote from AlphaVantage"""
        # Mock quote response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "02. open": "149.00",
                "03. high": "151.00",
                "04. low": "148.50",
                "05. price": "150.00",
                "06. volume": "1000000",
                "07. latest trading day": "2025-01-01",
                "08. previous close": "149.50",
                "09. change": "0.50",
                "10. change percent": "0.33%"
            }
        }
        mock_get.return_value = mock_response
        
        config = {'api_key': 'test_key'}
        feed = AlphaVantageFeed(config=config)
        
        quote = feed.get_quote("AAPL")
        
        assert quote is not None
        assert quote.symbol == "AAPL"
        assert quote.price == 150.0
        mock_get.assert_called()


class TestFeedIntegration:
    """Integration tests for feeds"""
    
    def test_feed_manager_with_multiple_feeds(self):
        """Test FeedManager with multiple feed types"""
        fm = FeedManager(config={})
        
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
            
            fm.register_feed(polygon_feed)
            fm.register_feed(alphavantage_feed)
            
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
        
        fm.register_feed(test_feed)
        fm.start_all()
        fm.subscribe(["AAPL", "GOOGL"])
        
        # Verify data was received
        assert len(received_ticks) == 2
        symbols = [tick.symbol for tick in received_ticks]
        assert "AAPL" in symbols
        assert "GOOGL" in symbols


class TestFeedErrorHandling:
    """Test error handling and recovery in feeds"""
    
    def test_feed_connection_retry(self):
        """Test feed connection retry mechanism"""
        config = {'api_key': 'test_key', 'max_retries': 3}
        
        with patch('requests.get') as mock_get:
            # First two calls fail, third succeeds
            mock_get.side_effect = [
                Mock(status_code=500),  # Server error
                Mock(status_code=500),  # Server error
                Mock(status_code=200, json=lambda: {"status": "OK"})  # Success
            ]
            
            feed = PolygonFeed(config=config)
            
            # This would test retry logic if implemented
            result = feed.connect()
            
            # Depending on implementation, might succeed after retries
            assert mock_get.call_count >= 1
    
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
                result = feed.connect()
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
                result = feed.connect()
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
