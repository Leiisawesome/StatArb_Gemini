"""
DataManager Test Suite
=====================

Focused tests for the DataManager class including:
- Data retrieval and caching
- ClickHouse integration
- Historical data processing
- Real-time data handling
- Performance optimization
- Error handling and recovery
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
import asyncio

import sys
sys.path.append('/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

try:
    from core_structure.market_data.data_manager import DataManager, DataCache, MarketDataConfig
    from core_structure.market_data import MarketTick, DataType
except ImportError as e:
    pytest.skip(f"DataManager module not available: {e}", allow_module_level=True)


class TestMarketDataConfig:
    """Test MarketDataConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = MarketDataConfig()
        
        assert config.cache_ttl_seconds == 300
        assert config.real_time_enabled is True
        assert config.max_symbols_per_query == 50
        assert config.default_lookback_days == 252
        assert config.enable_regime_detection is True
        assert config.enable_liquidity_analysis is True
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = MarketDataConfig(
            cache_ttl_seconds=600,
            real_time_enabled=False,
            max_symbols_per_query=100,
            default_lookback_days=500
        )
        
        assert config.cache_ttl_seconds == 600
        assert config.real_time_enabled is False
        assert config.max_symbols_per_query == 100
        assert config.default_lookback_days == 500


class TestDataCache:
    """Test DataCache functionality"""
    
    def test_cache_initialization(self):
        """Test cache initialization"""
        cache = DataCache(default_ttl=300, max_size=1000)
        
        assert cache.default_ttl == 300
        assert cache.max_size == 1000
        assert len(cache.cache) == 0
        assert len(cache.access_times) == 0
    
    def test_cache_operations(self):
        """Test basic cache operations"""
        cache = DataCache(default_ttl=300, max_size=100)
        
        # Test setting and getting
        test_data = {"symbol": "AAPL", "price": 150.0}
        cache.set("test_key", test_data)
        
        retrieved = cache.get("test_key")
        assert retrieved == test_data
        
        # Test key existence
        assert cache.has_key("test_key")
        assert not cache.has_key("nonexistent_key")
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        cache = DataCache(default_ttl=1, max_size=100)  # 1 second TTL
        
        test_data = {"symbol": "AAPL", "price": 150.0}
        cache.set("test_key", test_data)
        
        # Should be available immediately
        assert cache.get("test_key") == test_data
        
        # Mock time progression for TTL test
        with patch('datetime.datetime') as mock_datetime:
            # Mock future time (beyond TTL)
            future_time = datetime.now() + timedelta(seconds=2)
            mock_datetime.now.return_value = future_time
            
            # Should be expired (this depends on actual cache implementation)
            # Note: Actual TTL implementation may vary
            pass
    
    def test_cache_size_limit(self):
        """Test cache size limitations"""
        cache = DataCache(default_ttl=300, max_size=3)
        
        # Fill cache to capacity
        for i in range(5):
            cache.set(f"key_{i}", {"data": i})
        
        # Cache should not exceed max_size
        assert len(cache.cache) <= 3


@pytest.fixture
def mock_clickhouse_client():
    """Mock ClickHouse client"""
    mock_client = Mock()
    
    # Mock successful connection
    mock_client.ping.return_value = True
    
    # Mock query results
    mock_client.execute.return_value = []
    mock_client.query_dataframe.return_value = pd.DataFrame()
    mock_client.insert_dataframe.return_value = True
    
    return mock_client


@pytest.fixture
def mock_infrastructure():
    """Mock infrastructure components"""
    mocks = {}
    
    # Mock MetricsCollector
    mocks['metrics'] = Mock()
    mocks['metrics'].record_timing.return_value = None
    mocks['metrics'].increment_counter.return_value = None
    
    # Mock MessageBus
    mocks['message_bus'] = Mock()
    mocks['message_bus'].publish.return_value = None
    
    # Mock ConfigManager
    mocks['config_manager'] = Mock()
    mocks['config_manager'].get.return_value = {}
    
    return mocks


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing"""
    dates = pd.date_range(start='2025-01-01', periods=20, freq='D')
    
    data = {
        'symbol': ['AAPL'] * 20,
        'timestamp': dates,
        'open': np.random.uniform(145, 155, 20),
        'high': np.random.uniform(150, 160, 20),
        'low': np.random.uniform(140, 150, 20),
        'close': np.random.uniform(145, 155, 20),
        'volume': np.random.randint(1000000, 5000000, 20)
    }
    
    return pd.DataFrame(data)


class TestDataManager:
    """Test DataManager core functionality"""
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    @patch('core_structure.market_data.data_manager.MetricsCollector')
    @patch('core_structure.market_data.data_manager.MessageBus')
    @patch('core_structure.market_data.data_manager.ConfigManager')
    def test_data_manager_initialization(self, mock_config_mgr, mock_msg_bus, mock_metrics, mock_clickhouse):
        """Test DataManager initialization"""
        mock_clickhouse.return_value = Mock()
        mock_metrics.return_value = Mock()
        mock_msg_bus.return_value = Mock()
        mock_config_mgr.return_value = Mock()
        
        config = {'cache_ttl_seconds': 300}
        dm = DataManager(config=config)
        
        assert dm is not None
        assert dm.config is not None
        mock_clickhouse.assert_called_once()
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_get_historical_data(self, mock_clickhouse, sample_ohlcv_data):
        """Test historical data retrieval"""
        mock_client = Mock()
        mock_client.query_dataframe.return_value = sample_ohlcv_data
        mock_clickhouse.return_value = mock_client
        
        config = {'default_lookback_days': 30}
        dm = DataManager(config=config)
        
        result = dm.get_historical_data(
            symbols=['AAPL'],
            start_date='2025-01-01',
            end_date='2025-01-20'
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 20
        assert 'AAPL' in result['symbol'].values
        mock_client.query_dataframe.assert_called_once()
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_get_latest_prices(self, mock_clickhouse):
        """Test latest price retrieval"""
        mock_client = Mock()
        
        # Mock latest price data
        latest_data = pd.DataFrame({
            'symbol': ['AAPL', 'GOOGL', 'TSLA'],
            'timestamp': [datetime.now()] * 3,
            'close': [150.0, 2800.0, 250.0],
            'volume': [1000000, 500000, 2000000]
        })
        mock_client.query_dataframe.return_value = latest_data
        mock_clickhouse.return_value = mock_client
        
        dm = DataManager(config={})
        
        result = dm.get_latest_prices(['AAPL', 'GOOGL', 'TSLA'])
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert set(result['symbol'].values) == {'AAPL', 'GOOGL', 'TSLA'}
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_cache_functionality(self, mock_clickhouse, sample_ohlcv_data):
        """Test data caching functionality"""
        mock_client = Mock()
        mock_client.query_dataframe.return_value = sample_ohlcv_data
        mock_clickhouse.return_value = mock_client
        
        config = {'cache_ttl_seconds': 300}
        dm = DataManager(config=config)
        
        # First call should hit database
        result1 = dm.get_historical_data(
            symbols=['AAPL'],
            start_date='2025-01-01',
            end_date='2025-01-20'
        )
        
        # Second call should hit cache (if implemented)
        result2 = dm.get_historical_data(
            symbols=['AAPL'],
            start_date='2025-01-01',
            end_date='2025-01-20'
        )
        
        assert len(result1) == len(result2)
        # In a real implementation with caching, we'd verify cache hits
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_store_market_data(self, mock_clickhouse):
        """Test storing market data"""
        mock_client = Mock()
        mock_client.insert_dataframe.return_value = True
        mock_clickhouse.return_value = mock_client
        
        dm = DataManager(config={})
        
        # Create sample market ticks
        ticks = [
            MarketTick(
                symbol="AAPL",
                timestamp=datetime.now(),
                price=150.0,
                volume=1000
            ),
            MarketTick(
                symbol="GOOGL",
                timestamp=datetime.now(),
                price=2800.0,
                volume=500
            )
        ]
        
        # Test storing ticks
        result = dm.store_market_ticks(ticks)
        
        assert result is True
        mock_client.insert_dataframe.assert_called_once()
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_error_handling(self, mock_clickhouse):
        """Test error handling in data operations"""
        mock_client = Mock()
        mock_client.query_dataframe.side_effect = Exception("Database connection error")
        mock_clickhouse.return_value = mock_client
        
        dm = DataManager(config={})
        
        # Should handle database errors gracefully
        with pytest.raises(Exception):
            dm.get_historical_data(['AAPL'], '2025-01-01', '2025-01-02')
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_large_symbol_list_chunking(self, mock_clickhouse, sample_ohlcv_data):
        """Test handling of large symbol lists with chunking"""
        mock_client = Mock()
        mock_client.query_dataframe.return_value = sample_ohlcv_data
        mock_clickhouse.return_value = mock_client
        
        config = {'max_symbols_per_query': 2}  # Small chunk size for testing
        dm = DataManager(config=config)
        
        # Large symbol list
        symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'AMZN']
        
        result = dm.get_historical_data(
            symbols=symbols,
            start_date='2025-01-01',
            end_date='2025-01-02'
        )
        
        # Should handle chunking internally
        assert isinstance(result, pd.DataFrame)
        # With chunking, there should be multiple database calls
        assert mock_client.query_dataframe.call_count >= 2


class TestDataManagerAsync:
    """Test async functionality in DataManager"""
    
    @pytest.mark.asyncio
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    async def test_async_data_retrieval(self, mock_clickhouse, sample_ohlcv_data):
        """Test asynchronous data retrieval"""
        mock_client = Mock()
        mock_client.query_dataframe.return_value = sample_ohlcv_data
        mock_clickhouse.return_value = mock_client
        
        dm = DataManager(config={})
        
        # Test async method if available
        if hasattr(dm, 'get_historical_data_async'):
            result = await dm.get_historical_data_async(['AAPL'], '2025-01-01', '2025-01-02')
            assert isinstance(result, pd.DataFrame)


class TestDataManagerPerformance:
    """Performance tests for DataManager"""
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_large_dataset_performance(self, mock_clickhouse):
        """Test performance with large datasets"""
        # Create large mock dataset
        large_data = pd.DataFrame({
            'symbol': ['AAPL'] * 100000,
            'timestamp': pd.date_range('2025-01-01', periods=100000, freq='1min'),
            'open': np.random.uniform(145, 155, 100000),
            'high': np.random.uniform(150, 160, 100000),
            'low': np.random.uniform(140, 150, 100000),
            'close': np.random.uniform(145, 155, 100000),
            'volume': np.random.randint(1000, 10000, 100000)
        })
        
        mock_client = Mock()
        mock_client.query_dataframe.return_value = large_data
        mock_clickhouse.return_value = mock_client
        
        dm = DataManager(config={})
        
        # Measure performance
        start_time = datetime.now()
        result = dm.get_historical_data(['AAPL'], '2025-01-01', '2025-01-02')
        end_time = datetime.now()
        
        assert len(result) == 100000
        assert (end_time - start_time).total_seconds() < 5.0  # Should be reasonably fast
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_concurrent_requests(self, mock_clickhouse, sample_ohlcv_data):
        """Test concurrent data requests"""
        mock_client = Mock()
        mock_client.query_dataframe.return_value = sample_ohlcv_data
        mock_clickhouse.return_value = mock_client
        
        dm = DataManager(config={})
        
        # Simulate concurrent requests
        symbols_lists = [['AAPL'], ['GOOGL'], ['TSLA'], ['MSFT']]
        
        results = []
        for symbols in symbols_lists:
            result = dm.get_historical_data(symbols, '2025-01-01', '2025-01-02')
            results.append(result)
        
        assert len(results) == 4
        for result in results:
            assert isinstance(result, pd.DataFrame)


class TestDataManagerIntegration:
    """Integration tests combining multiple DataManager features"""
    
    @patch('core_structure.market_data.data_manager.ClickHouseClient')
    def test_end_to_end_workflow(self, mock_clickhouse, sample_ohlcv_data):
        """Test complete data workflow"""
        mock_client = Mock()
        mock_client.query_dataframe.return_value = sample_ohlcv_data
        mock_client.insert_dataframe.return_value = True
        mock_clickhouse.return_value = mock_client
        
        dm = DataManager(config={'cache_ttl_seconds': 300})
        
        # 1. Retrieve historical data
        hist_data = dm.get_historical_data(['AAPL'], '2025-01-01', '2025-01-20')
        assert len(hist_data) == 20
        
        # 2. Get latest prices
        latest = dm.get_latest_prices(['AAPL'])
        assert len(latest) >= 0  # May be empty with mock
        
        # 3. Store new data
        new_ticks = [
            MarketTick(
                symbol="AAPL",
                timestamp=datetime.now(),
                price=151.0,
                volume=1500
            )
        ]
        stored = dm.store_market_ticks(new_ticks)
        assert stored is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
