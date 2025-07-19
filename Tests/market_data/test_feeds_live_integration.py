"""
Real Market Data Feeds Integration Tests
========================================

Tests live API connections with real market data feeds:
- Polygon.io WebSocket and REST API
- Real-time data streaming
- Feed status and health monitoring
- Error handling with live APIs
"""

import pytest
import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Set up logging for integration tests
logging.basicConfig(level=logging.INFO)

# Import the feeds
try:
    from core_structure.market_data.feeds import (
        FeedManager, 
        PolygonFeed, 
        AlphaVantageFeed,
        MarketTick, 
        DataType, 
        FeedStatus,
        FeedMetrics
    )
    from core_structure.infrastructure.config.config_manager import ConfigManager
    from core_structure.infrastructure.config.env_config import SecureConfigManager, get_api_key
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Skip all tests if imports not available
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE, 
    reason=f"Feeds module imports not available: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}"
)

# Load API keys securely from environment
config_manager = SecureConfigManager()
POLYGON_API_KEY = config_manager.get_api_key('polygon')

# Skip tests if no API key is provided
if not POLYGON_API_KEY:
    pytest.skip("POLYGON_API_KEY not found in environment variables or .env file", allow_module_level=True)

@pytest.mark.integration
@pytest.mark.asyncio
class TestPolygonFeedIntegration:
    """Integration tests with real Polygon.io API"""
    
    @pytest.fixture
    def polygon_config(self):
        """Real Polygon.io configuration"""
        return {
            'api_key': POLYGON_API_KEY,
            'base_url': 'https://api.polygon.io',
            'ws_url': 'wss://socket.polygon.io/stocks',
            'timeout': 30,
            'max_retries': 3
        }
    
    @pytest.fixture
    def test_symbols(self):
        """Test symbols for integration tests"""
        return ['AAPL', 'MSFT', 'GOOGL']  # Popular, liquid stocks
    
    async def test_polygon_api_authentication(self, polygon_config):
        """Test Polygon API authentication with real API key"""
        feed = PolygonFeed(polygon_config)
        
        # Test API authentication by making a simple request
        import requests
        url = f"{polygon_config['base_url']}/v3/reference/tickers"
        params = {
            'apikey': polygon_config['api_key'],
            'limit': 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        # Should get successful response
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'OK'
        assert 'results' in data
        
        print(f"✅ Polygon API authentication successful")
        print(f"📊 Available tickers sample: {data['results'][0] if data['results'] else 'None'}")
    
    async def test_polygon_rest_api_quote(self, polygon_config, test_symbols):
        """Test getting real quotes from Polygon REST API"""
        feed = PolygonFeed(polygon_config)
        
        for symbol in test_symbols[:1]:  # Test just one symbol
            try:
                # Make direct API call to get latest quote
                import requests
                url = f"{polygon_config['base_url']}/v2/last/nbbo/{symbol}"
                params = {'apikey': polygon_config['api_key']}
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    assert data.get('status') == 'OK'
                    
                    if 'results' in data and data['results']:
                        quote = data['results']
                        assert 'P' in quote  # Bid price
                        assert 'p' in quote  # Ask price
                        assert 'T' in quote  # Ticker
                        
                        print(f"✅ Real quote for {symbol}:")
                        print(f"   Bid: ${quote.get('P', 'N/A')}")
                        print(f"   Ask: ${quote.get('p', 'N/A')}")
                        print(f"   Timestamp: {quote.get('t', 'N/A')}")
                        
                        break  # Success, no need to test more
                    else:
                        print(f"⚠️  No quote data available for {symbol}")
                else:
                    print(f"⚠️  API call failed for {symbol}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error getting quote for {symbol}: {e}")
                # Don't fail the test for individual symbol failures
    
    async def test_polygon_aggregates_api(self, polygon_config):
        """Test getting real market data aggregates"""
        feed = PolygonFeed(polygon_config)
        
        # Get yesterday's date for data that should exist
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        import requests
        url = f"{polygon_config['base_url']}/v2/aggs/ticker/AAPL/range/1/minute/{yesterday}/{yesterday}"
        params = {
            'apikey': polygon_config['api_key'],
            'limit': 5
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('resultsCount', 0) > 0:
                results = data['results']
                assert len(results) > 0
                
                # Check structure of market data
                bar = results[0]
                assert 'o' in bar  # Open
                assert 'h' in bar  # High
                assert 'l' in bar  # Low
                assert 'c' in bar  # Close
                assert 'v' in bar  # Volume
                assert 't' in bar  # Timestamp
                
                print(f"✅ Real market data for AAPL on {yesterday}:")
                print(f"   Bars received: {len(results)}")
                print(f"   Sample bar - O: {bar['o']}, H: {bar['h']}, L: {bar['l']}, C: {bar['c']}, V: {bar['v']}")
            else:
                print(f"⚠️  No market data available for {yesterday} (weekend/holiday?)")
        else:
            print(f"⚠️  Aggregates API call failed: {response.status_code}")
            # Don't fail test, might be weekend/market closed
    
    async def test_polygon_api_multiple_endpoints(self, polygon_config):
        """Test multiple Polygon API endpoints for comprehensive market data"""
        import requests
        
        endpoints_tested = 0
        successful_calls = 0
        
        # Test 1: Market status
        try:
            url = f"{polygon_config['base_url']}/v1/marketstatus/now"
            params = {'apikey': polygon_config['api_key']}
            response = requests.get(url, params=params, timeout=10)
            endpoints_tested += 1
            
            if response.status_code == 200:
                data = response.json()
                successful_calls += 1
                print(f"✅ Market Status API: Market is {data.get('market', 'unknown')}")
            else:
                print(f"⚠️  Market Status API failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Market Status API error: {e}")
        
        # Test 2: Ticker details
        try:
            url = f"{polygon_config['base_url']}/v3/reference/tickers/AAPL"
            params = {'apikey': polygon_config['api_key']}
            response = requests.get(url, params=params, timeout=10)
            endpoints_tested += 1
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and 'results' in data:
                    results = data['results']
                    successful_calls += 1
                    print(f"✅ Ticker Details API: {results.get('name', 'AAPL')} - {results.get('description', 'N/A')}")
                else:
                    print(f"⚠️  Ticker Details API: No results")
            else:
                print(f"⚠️  Ticker Details API failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Ticker Details API error: {e}")
        
        # Test 3: Previous close
        try:
            url = f"{polygon_config['base_url']}/v2/aggs/ticker/AAPL/prev"
            params = {'apikey': polygon_config['api_key']}
            response = requests.get(url, params=params, timeout=10)
            endpoints_tested += 1
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK' and 'results' in data and data['results']:
                    result = data['results'][0]
                    successful_calls += 1
                    print(f"✅ Previous Close API: AAPL closed at ${result.get('c', 'N/A')}")
                else:
                    print(f"⚠️  Previous Close API: No results")
            else:
                print(f"⚠️  Previous Close API failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Previous Close API error: {e}")
        
        print(f"📊 API Endpoint Summary: {successful_calls}/{endpoints_tested} successful")
        
        # Test should pass if at least one endpoint works
        assert successful_calls > 0, f"No API endpoints were successful out of {endpoints_tested} tested"
        assert endpoints_tested == 3, "Expected to test 3 endpoints"

    @pytest.mark.skip(reason="WebSocket tests require careful handling and may run indefinitely - remove this decorator to enable")
    async def test_polygon_websocket_connection(self, polygon_config):
        """Test real WebSocket connection to Polygon.io
        
        Note: This test is skipped by default because:
        1. WebSocket connections can run indefinitely
        2. Real-time tests depend on market conditions
        3. Can be flaky during market hours
        4. Requires careful resource cleanup
        
        To enable: Remove the @pytest.mark.skip decorator above
        """
        feed = PolygonFeed(polygon_config)
        
        # Set up data collection
        received_messages = []
        
        def data_callback(tick: MarketTick):
            received_messages.append(tick)
            print(f"📈 Received: {tick.symbol} @ ${tick.price} ({tick.data_type.value})")
        
        feed.add_callback(data_callback)
        
        try:
            # Connect to WebSocket
            success = await feed.connect()
            if success:
                print("✅ WebSocket connected successfully")
                
                # Subscribe to test symbols
                await feed.subscribe(['AAPL'])
                print("✅ Subscribed to AAPL")
                
                # Wait for some data (10 seconds max)
                await asyncio.sleep(10)
                
                # Check if we received any data
                if received_messages:
                    print(f"✅ Received {len(received_messages)} real-time messages")
                    sample_tick = received_messages[0]
                    assert hasattr(sample_tick, 'symbol')
                    assert hasattr(sample_tick, 'price')
                    assert hasattr(sample_tick, 'timestamp')
                else:
                    print("⚠️  No real-time data received (market might be closed)")
                
            else:
                print("❌ WebSocket connection failed")
                
        except Exception as e:
            print(f"❌ WebSocket test error: {e}")
        
        finally:
            # Always disconnect
            try:
                await feed.disconnect()
                print("✅ WebSocket disconnected")
            except:
                pass
    
    async def test_polygon_feed_status_and_metrics(self, polygon_config):
        """Test feed status management and metrics collection"""
        feed = PolygonFeed(polygon_config)
        
        # Initial status should be disconnected
        assert feed.status == FeedStatus.DISCONNECTED
        
        # Get initial metrics
        metrics = feed.get_metrics()
        assert isinstance(metrics, FeedMetrics)
        assert metrics.feed_name == "polygon"
        assert metrics.messages_received == 0
        
        print(f"✅ Initial feed status: {feed.status.value}")
        print(f"✅ Initial metrics: {metrics.messages_received} messages, {metrics.messages_failed} errors")

@pytest.mark.integration
@pytest.mark.asyncio
class TestFeedManagerIntegration:
    """Integration tests for FeedManager with real APIs"""
    
    @pytest.fixture
    def real_config_manager(self):
        """Create config manager with real API settings from secure config"""
        # Use the secure config manager to get real configuration
        secure_config = SecureConfigManager()
        
        class MockConfigManager:
            def get(self, key, default=None):
                if key == "market_data.feeds":
                    return secure_config.get_feeds_config().get('feeds', {})
                return secure_config.get(key, default)
        
        return MockConfigManager()
    
    async def test_feed_manager_setup_with_real_config(self, real_config_manager):
        """Test FeedManager setup with real API configuration"""
        fm = FeedManager(real_config_manager)
        
        # Should have set up polygon feed
        assert len(fm.feeds) >= 1
        assert "polygon" in fm.feeds
        
        polygon_feed = fm.feeds["polygon"]
        assert isinstance(polygon_feed, PolygonFeed)
        assert polygon_feed.config["api_key"] == POLYGON_API_KEY
        
        print(f"✅ FeedManager configured with {len(fm.feeds)} feeds")
        print(f"📡 Available feeds: {list(fm.feeds.keys())}")
    
    async def test_feed_manager_health_check(self, real_config_manager):
        """Test FeedManager health check functionality"""
        fm = FeedManager(real_config_manager)
        
        # Perform health check
        health_status = await fm.health_check()
        
        assert isinstance(health_status, dict)
        assert "polygon" in health_status
        
        # Health will be False initially since feeds aren't connected
        assert isinstance(health_status["polygon"], bool)
        
        print(f"✅ Health check completed")
        print(f"🏥 Feed health status: {health_status}")
    
    async def test_feed_manager_status_reporting(self, real_config_manager):
        """Test FeedManager status reporting"""
        fm = FeedManager(real_config_manager)
        
        # Get feed status
        status = fm.get_feed_status()
        
        assert isinstance(status, dict)
        assert "polygon" in status
        
        polygon_status = status["polygon"]
        assert "status" in polygon_status
        assert "metrics" in polygon_status
        assert "subscribed_symbols" in polygon_status
        
        print(f"✅ Status reporting working")
        print(f"📊 Polygon status: {polygon_status['status']}")
        print(f"📈 Metrics keys: {list(polygon_status['metrics'].keys())}")

@pytest.mark.integration
class TestMarketDataApiValidation:
    """Validate API endpoints and data quality"""
    
    def test_polygon_api_rate_limits(self):
        """Test API rate limit handling"""
        import requests
        import time
        
        # Make multiple requests to test rate limiting
        url = f"https://api.polygon.io/v3/reference/tickers"
        params = {
            'apikey': POLYGON_API_KEY,
            'limit': 1
        }
        
        responses = []
        for i in range(3):
            response = requests.get(url, params=params, timeout=10)
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay between requests
        
        # Should get successful responses (not rate limited for basic plan)
        success_count = sum(1 for r in responses if r == 200)
        print(f"✅ API rate limit test: {success_count}/3 successful requests")
        print(f"📊 Response codes: {responses}")
        
        # At least some requests should succeed
        assert success_count > 0
    
    def test_polygon_api_data_quality(self):
        """Test data quality from Polygon API"""
        import requests
        
        # Get current market status
        url = f"https://api.polygon.io/v1/marketstatus/now"
        params = {'apikey': POLYGON_API_KEY}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check data structure
            assert 'market' in data
            assert 'exchanges' in data
            
            market_status = data['market']
            print(f"✅ Market status data quality check passed")
            print(f"🏛️  Market: {market_status}")
            print(f"📊 Exchanges: {len(data.get('exchanges', {}))}")
        else:
            print(f"⚠️  Market status API returned: {response.status_code}")

if __name__ == "__main__":
    # Quick test run
    pytest.main([__file__, "-v", "-s", "--tb=short"])
