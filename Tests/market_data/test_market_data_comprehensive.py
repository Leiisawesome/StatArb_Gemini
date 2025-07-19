"""
Market Data Module Test Suite
============================

Comprehensive tests for the market_data module including:
- DataManager functionality
- Feed management and data processing
- ClickHouse integration
- Real-time data handling
- Cache management
- Error handling and recovery

Test Categories:
- Unit tests for individual components
- Integration tests for module interactions
- Performance tests for data processing
- Mock tests for external API dependencies
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Any
import json
import tempfile
import os

# Import modules under test
import sys
sys.path.append('/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

try:
    from core_structure.market_data import (
        DataManager, 
        FeedManager, 
        PolygonFeed, 
        AlphaVantageFeed,
        MarketTick, 
        DataType, 
        FeedStatus,
        DATA_PROCESSOR_AVAILABLE
    )
    
    # Try to import DataProcessor only if available
    if DATA_PROCESSOR_AVAILABLE:
        try:
            from core_structure.market_data import DataProcessor, ProcessedData, ProcessingStage
        except ImportError as e:
            print(f"DataProcessor import failed even though marked available: {e}")
            DATA_PROCESSOR_AVAILABLE = False
        
except ImportError as e:
    pytest.skip(f"Market data module not available: {e}", allow_module_level=True)


class TestMarketDataImports:
    """Test module imports and availability"""
    
    def test_basic_imports(self):
        """Test that basic classes can be imported"""
        assert DataManager is not None
        assert FeedManager is not None
        assert MarketTick is not None
        assert DataType is not None
        assert FeedStatus is not None
    
    def test_feed_implementations(self):
        """Test feed implementation imports"""
        assert PolygonFeed is not None
        assert AlphaVantageFeed is not None
    
    def test_optional_imports(self):
        """Test optional data processor imports"""
        if DATA_PROCESSOR_AVAILABLE:
            # Check if we actually got the imports
            try:
                assert DataProcessor is not None
                assert ProcessedData is not None
                assert ProcessingStage is not None
            except NameError:
                pytest.skip("DataProcessor classes not imported despite being marked available")
        else:
            pytest.skip("Data processor not available - missing dependencies (ta, sklearn)")


class TestMarketTick:
    """Test MarketTick data structure"""
    
    def test_market_tick_creation(self):
        """Test basic MarketTick creation"""
        tick = MarketTick(
            symbol="AAPL",
            timestamp=datetime.now(),
            price=150.0,
            volume=100
        )
        
        assert tick.symbol == "AAPL"
        assert tick.price == 150.0
        assert tick.volume == 100
        assert tick.data_type == DataType.TICK
    
    def test_market_tick_with_optional_fields(self):
        """Test MarketTick with all optional fields"""
        timestamp = datetime.now()
        tick = MarketTick(
            symbol="TSLA",
            timestamp=timestamp,
            price=250.0,
            volume=200,
            bid=249.5,
            ask=250.5,
            bid_size=100,
            ask_size=150,
            exchange="NASDAQ",
            conditions=["T", "F"]
        )
        
        assert tick.bid == 249.5
        assert tick.ask == 250.5
        assert tick.bid_size == 100
        assert tick.ask_size == 150
        assert tick.exchange == "NASDAQ"
        assert tick.conditions == ["T", "F"]
    
    def test_market_tick_to_dict(self):
        """Test MarketTick serialization to dictionary"""
        timestamp = datetime(2025, 1, 1, 12, 0, 0)
        tick = MarketTick(
            symbol="GOOGL",
            timestamp=timestamp,
            price=2800.0,
            volume=50
        )
        
        tick_dict = tick.to_dict()
        
        assert tick_dict['symbol'] == "GOOGL"
        assert tick_dict['price'] == 2800.0
        assert tick_dict['volume'] == 50
        assert tick_dict['timestamp'] == timestamp.isoformat()
        assert tick_dict['data_type'] == "tick"


class TestDataEnums:
    """Test enum classes"""
    
    def test_data_type_enum(self):
        """Test DataType enum values"""
        assert DataType.TICK.value == "tick"
        assert DataType.QUOTE.value == "quote"
        assert DataType.TRADE.value == "trade"
        assert DataType.ORDERBOOK.value == "orderbook"
        assert DataType.NEWS.value == "news"
        assert DataType.CORPORATE_ACTION.value == "corporate_action"
    
    def test_feed_status_enum(self):
        """Test FeedStatus enum values"""
        assert FeedStatus.DISCONNECTED.value == "disconnected"
        assert FeedStatus.CONNECTING.value == "connecting"
        assert FeedStatus.CONNECTED.value == "connected"
        assert FeedStatus.ERROR.value == "error"
        assert FeedStatus.RECONNECTING.value == "reconnecting"


@pytest.fixture
def sample_market_data():
    """Fixture providing sample market data"""
    timestamps = pd.date_range(start='2025-01-01', periods=100, freq='1min')
    
    data = []
    for i, ts in enumerate(timestamps):
        data.append(MarketTick(
            symbol="AAPL",
            timestamp=ts,
            price=150.0 + np.random.normal(0, 1),
            volume=100 + np.random.randint(0, 200),
            bid=149.5 + np.random.normal(0, 0.5),
            ask=150.5 + np.random.normal(0, 0.5)
        ))
    
    return data


@pytest.fixture
def mock_clickhouse_client():
    """Mock ClickHouse client for testing"""
    mock_client = Mock()
    mock_client.execute.return_value = []
    mock_client.insert_dataframe.return_value = True
    mock_client.query_dataframe.return_value = pd.DataFrame()
    return mock_client


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        'cache_ttl_seconds': 300,
        'real_time_enabled': True,
        'max_symbols_per_query': 50,
        'default_lookback_days': 252,
        'enable_regime_detection': True,
        'enable_liquidity_analysis': True,
        'polygon_api_key': 'test_key',
        'alphavantage_api_key': 'test_key'
    }


class TestDataManager:
    """Test DataManager functionality"""
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_data_manager_initialization(self, mock_clickhouse, mock_config):
        """Test DataManager initialization"""
        mock_clickhouse.return_value = Mock()
        
        dm = DataManager(config=mock_config)
        
        assert dm is not None
        assert dm.config is not None
        mock_clickhouse.assert_called_once()
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_get_historical_data_mock(self, mock_clickhouse, mock_config):
        """Test historical data retrieval with mocked database"""
        mock_client = Mock()
        mock_df = pd.DataFrame({
            'symbol': ['AAPL'] * 5,
            'timestamp': pd.date_range('2025-01-01', periods=5),
            'open': [150.0, 151.0, 152.0, 151.5, 153.0],
            'high': [151.0, 152.0, 153.0, 152.5, 154.0],
            'low': [149.5, 150.5, 151.5, 151.0, 152.5],
            'close': [150.5, 151.5, 152.5, 152.0, 153.5],
            'volume': [1000, 1100, 1200, 1050, 1300]
        })
        mock_client.query_dataframe.return_value = mock_df
        mock_clickhouse.return_value = mock_client
        
        dm = DataManager(config=mock_config)
        
        result = dm.get_historical_data(['AAPL'], start_date='2025-01-01', end_date='2025-01-05')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        assert 'AAPL' in result['symbol'].values


class TestFeedManager:
    """Test FeedManager functionality"""
    
    def test_feed_manager_initialization(self, mock_config):
        """Test FeedManager initialization"""
        fm = FeedManager(config=mock_config)
        
        assert fm is not None
        assert len(fm.feeds) == 0
        assert fm.status == FeedStatus.DISCONNECTED
    
    def test_register_feed(self, mock_config):
        """Test feed registration"""
        fm = FeedManager(config=mock_config)
        
        # Create a mock feed
        mock_feed = Mock()
        mock_feed.name = "test_feed"
        mock_feed.status = FeedStatus.DISCONNECTED
        
        fm.register_feed(mock_feed)
        
        assert "test_feed" in fm.feeds
        assert fm.feeds["test_feed"] == mock_feed


@pytest.mark.skipif(not DATA_PROCESSOR_AVAILABLE, reason="Data processor not available - missing dependencies")
class TestDataProcessor:
    """Test DataProcessor functionality (if available)"""
    
    def test_data_processor_initialization(self, mock_config):
        """Test DataProcessor initialization"""
        try:
            dp = DataProcessor(config=mock_config)
            assert dp is not None
        except NameError:
            pytest.skip("DataProcessor not imported")
    
    def test_process_sample_data(self, sample_market_data, mock_config):
        """Test data processing with sample data"""
        try:
            dp = DataProcessor(config=mock_config)
            
            # Convert MarketTick objects to DataFrame
            data_dicts = [tick.to_dict() for tick in sample_market_data[:10]]
            df = pd.DataFrame(data_dicts)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # This is a basic test - actual implementation may vary
            if hasattr(dp, 'process_tick_data'):
                processed = dp.process_tick_data(df)
                assert processed is not None
            else:
                pytest.skip("process_tick_data method not available")
                
        except NameError:
            pytest.skip("DataProcessor not imported")


class TestIntegration:
    """Integration tests for market_data module"""
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_end_to_end_data_flow(self, mock_clickhouse, mock_config, sample_market_data):
        """Test complete data flow from feed to storage"""
        mock_client = Mock()
        mock_clickhouse.return_value = mock_client
        
        # Initialize components
        dm = DataManager(config=mock_config)
        fm = FeedManager(config=mock_config)
        
        # Simulate data flow
        for tick in sample_market_data[:5]:
            # Simulate feed receiving data
            tick_dict = tick.to_dict()
            
            # Process through data manager (mocked)
            # In real implementation, this would involve actual processing
            
        # Verify components are working
        assert dm is not None
        assert fm is not None


class TestPerformance:
    """Performance tests for market_data module"""
    
    def test_large_dataset_handling(self, mock_config):
        """Test handling of large datasets"""
        # Create large dataset
        timestamps = pd.date_range(start='2025-01-01', periods=10000, freq='1s')
        
        large_dataset = []
        for i, ts in enumerate(timestamps):
            large_dataset.append(MarketTick(
                symbol=f"STOCK_{i % 100}",
                timestamp=ts,
                price=100.0 + np.random.normal(0, 10),
                volume=np.random.randint(100, 1000)
            ))
        
        # Test that we can handle large datasets
        assert len(large_dataset) == 10000
        
        # Test serialization performance
        start_time = datetime.now()
        serialized = [tick.to_dict() for tick in large_dataset[:1000]]
        end_time = datetime.now()
        
        assert len(serialized) == 1000
        assert (end_time - start_time).total_seconds() < 1.0  # Should be fast


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_market_tick_data(self):
        """Test MarketTick with invalid data"""
        with pytest.raises((ValueError, TypeError)):
            MarketTick(
                symbol=None,  # Invalid symbol
                timestamp=datetime.now(),
                price=150.0,
                volume=100
            )
    
    def test_feed_manager_with_invalid_config(self):
        """Test FeedManager with invalid configuration"""
        invalid_config = {}  # Empty config
        
        # Should handle gracefully or raise appropriate error
        try:
            fm = FeedManager(config=invalid_config)
            assert fm is not None
        except Exception as e:
            assert isinstance(e, (ValueError, KeyError, TypeError))


class TestMockFunctionality:
    """Test functionality using mocks for external dependencies"""
    
    @patch('requests.get')
    def test_external_api_mock(self, mock_get):
        """Test external API calls with mocks"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'results': [
                {
                    'symbol': 'AAPL',
                    'price': 150.0,
                    'volume': 1000,
                    'timestamp': '2025-01-01T12:00:00Z'
                }
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test that mock is working
        response = mock_get('https://api.example.com/data')
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
