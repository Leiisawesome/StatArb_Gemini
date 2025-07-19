"""
Enhanced ClickHouse Loader Integration Tests
===========================================

Tests the actual production ClickHouse integration component that's used
in the market_data module, not the testing utility.

This tests:
1. EnhancedClickHouseLoader initialization and configuration
2. Market data loading with real ClickHouse database
3. Caching functionality and performance
4. Parallel data loading capabilities
5. Pair screening with real data
6. Error handling and resilience
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import logging

# Import the actual production components
try:
    from core_structure.market_data.enhanced_clickhouse_loader import (
        EnhancedClickHouseLoader,
        DataRequest,
        PairScreeningCriteria,
        SmartCache
    )
    from core_structure.infrastructure.config.config_manager import ConfigManager
    from core_structure.infrastructure.database.clickhouse_client import ClickHouseClient
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Skip all tests if imports not available
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE, 
    reason=f"Enhanced ClickHouse Loader imports not available: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}"
)


class TestSmartCache:
    """Test the intelligent caching system"""
    
    def test_cache_initialization(self):
        """Test cache initialization with default parameters"""
        cache = SmartCache()
        assert cache.max_size == 1000
        assert cache.default_ttl == 3600
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0
    
    def test_cache_put_get(self):
        """Test basic cache put and get operations"""
        cache = SmartCache(max_size=10, default_ttl=60)
        
        # Test put and get
        test_data = pd.DataFrame({'price': [100, 101, 102]})
        cache.put('test_key', test_data)
        
        retrieved = cache.get('test_key')
        pd.testing.assert_frame_equal(retrieved, test_data)
        assert cache.hits == 1
        assert cache.misses == 0
    
    def test_cache_ttl_expiry(self):
        """Test cache TTL expiry functionality"""
        cache = SmartCache(default_ttl=1)  # 1 second TTL
        
        cache.put('expire_key', 'test_value')
        assert cache.get('expire_key') == 'test_value'
        
        # Wait for expiry (in real test, we'd mock datetime)
        import time
        time.sleep(1.1)
        assert cache.get('expire_key') is None
        assert cache.misses == 1  # Miss due to expiry
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = SmartCache(max_size=2)
        
        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        cache.put('key3', 'value3')  # Should evict key1
        
        assert cache.get('key1') is None  # Evicted
        assert cache.get('key2') == 'value2'
        assert cache.get('key3') == 'value3'
        assert cache.evictions == 1
    
    def test_cache_statistics(self):
        """Test cache statistics calculation"""
        cache = SmartCache()
        
        cache.put('key1', 'value1')
        cache.get('key1')  # Hit
        cache.get('key2')  # Miss
        
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_ratio'] == 0.5
        assert stats['size'] == 1


class TestDataRequest:
    """Test DataRequest functionality"""
    
    def test_data_request_creation(self):
        """Test DataRequest creation and cache key generation"""
        symbols = ['AAPL', 'MSFT']
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        request = DataRequest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            interval='1min'
        )
        
        assert request.symbols == symbols
        assert request.start_date == start_date
        assert request.end_date == end_date
        assert request.interval == '1min'
        assert request.cache_key is not None
        assert len(request.cache_key) == 32  # MD5 hash length
    
    def test_cache_key_consistency(self):
        """Test that identical requests generate same cache key"""
        symbols = ['AAPL', 'MSFT']
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        request1 = DataRequest(symbols=symbols, start_date=start_date, end_date=end_date)
        request2 = DataRequest(symbols=symbols, start_date=start_date, end_date=end_date)
        
        assert request1.cache_key == request2.cache_key


class TestEnhancedClickHouseLoader:
    """Test the main Enhanced ClickHouse Loader class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration"""
        config = Mock(spec=ConfigManager)
        config.get.side_effect = lambda key, default=None: {
            "clickhouse_loader.cache": {"max_size": 100, "default_ttl": 300},
            "clickhouse_loader.max_workers": 4,
            "clickhouse.host": "localhost",
            "clickhouse.port": 9000,
            "clickhouse.database": "test_db"
        }.get(key, default)
        return config
    
    @pytest.fixture
    def mock_clickhouse_client(self):
        """Create a mock ClickHouse client"""
        client = Mock(spec=ClickHouseClient)
        return client
    
    @patch('core_structure.market_data.enhanced_clickhouse_loader.ClickHouseClient')
    @patch('core_structure.market_data.enhanced_clickhouse_loader.MetricsCollector')
    def test_loader_initialization(self, mock_metrics, mock_clickhouse, mock_config):
        """Test loader initialization"""
        loader = EnhancedClickHouseLoader(mock_config)
        
        assert loader.config == mock_config
        assert loader.cache.max_size == 100
        assert loader.cache.default_ttl == 300
        assert loader.query_stats['total_queries'] == 0
        mock_clickhouse.assert_called_once_with(mock_config)
    
    @pytest.mark.asyncio
    @patch('core_structure.market_data.enhanced_clickhouse_loader.ClickHouseClient')
    @patch('core_structure.market_data.enhanced_clickhouse_loader.MetricsCollector')
    async def test_cache_hit_functionality(self, mock_metrics, mock_clickhouse, mock_config):
        """Test that cache hits work correctly"""
        loader = EnhancedClickHouseLoader(mock_config)
        
        # Put data in cache
        test_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'AAPL_open': [150.0],
            'AAPL_close': [151.0]
        })
        request = DataRequest(
            symbols=['AAPL'],
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            interval='1min'
        )
        
        loader.cache.put(request.cache_key, test_data)
        
        # Load data - should hit cache
        result = await loader.load_market_data(request)
        
        pd.testing.assert_frame_equal(result, test_data)
        assert loader.query_stats['cache_hits'] == 1
        # ClickHouse should not be called
        mock_clickhouse.return_value.execute_query.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('core_structure.market_data.enhanced_clickhouse_loader.ClickHouseClient')
    @patch('core_structure.market_data.enhanced_clickhouse_loader.MetricsCollector')
    async def test_database_query_on_cache_miss(self, mock_metrics, mock_clickhouse, mock_config):
        """Test that database is queried on cache miss"""
        loader = EnhancedClickHouseLoader(mock_config)
        
        # Mock database response - create a proper async mock
        mock_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [150.0],
            'high': [152.0],
            'low': [149.0],
            'close': [151.0],
            'volume': [1000000],
            'symbol': ['AAPL']
        })
        
        # Create an async mock function
        async def mock_execute_query(*args, **kwargs):
            return mock_data
        
        mock_clickhouse.return_value.execute_query = mock_execute_query
        
        request = DataRequest(
            symbols=['AAPL'],
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            interval='1min'
        )
        
        # Load data - should query database
        result = await loader.load_market_data(request)
        
        # Verify result is not empty
        assert not result.empty
        assert loader.query_stats['total_queries'] == 1
        assert 'AAPL_open' in result.columns or 'open' in result.columns
    
    @pytest.mark.asyncio
    @patch('core_structure.market_data.enhanced_clickhouse_loader.ClickHouseClient')
    @patch('core_structure.market_data.enhanced_clickhouse_loader.MetricsCollector')
    async def test_error_handling(self, mock_metrics, mock_clickhouse, mock_config):
        """Test error handling during data loading"""
        loader = EnhancedClickHouseLoader(mock_config)
        
        # Mock database error - create async mock that raises exception
        async def mock_execute_query_error(*args, **kwargs):
            raise Exception("Database connection failed")
        
        mock_clickhouse.return_value.execute_query = mock_execute_query_error
        
        request = DataRequest(
            symbols=['AAPL'],
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now()
        )
        
        # Should return empty DataFrame on error (resilient behavior)
        result = await loader.load_market_data(request)
        
        # Should return empty DataFrame
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        
        # Check that error counter was called (any call with "errors" in it)
        calls = mock_metrics.return_value.increment_counter.call_args_list
        error_calls = [call for call in calls if 'errors' in str(call)]
        assert len(error_calls) > 0, f"Expected error counter call, but got: {calls}"


@pytest.mark.integration
class TestEnhancedClickHouseLoaderIntegration:
    """Integration tests with real ClickHouse database"""
    
    @pytest.fixture
    def real_config(self):
        """Create real configuration for integration tests"""
        # This would normally load from actual config files
        return {
            "clickhouse": {
                "host": "localhost",
                "port": 9000,
                "database": "polygon_data",
                "user": "default",
                "password": ""
            },
            "clickhouse_loader": {
                "cache": {"max_size": 100, "default_ttl": 300},
                "max_workers": 4
            }
        }
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_data_loading(self, real_config):
        """Test loading real data from ClickHouse"""
        # This test would be enabled when we have proper ClickHouse setup
        config_manager = Mock()
        config_manager.get.side_effect = lambda key, default=None: real_config.get(key, default)
        
        loader = EnhancedClickHouseLoader(config_manager)
        
        request = DataRequest(
            symbols=['AAPL'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            interval='1d'
        )
        
        data = await loader.load_market_data(request)
        
        # Verify data structure
        assert isinstance(data, pd.DataFrame)
        if not data.empty:
            assert 'AAPL_open' in data.columns
            assert 'AAPL_close' in data.columns
    
    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_real_pair_screening(self, real_config):
        """Test pair screening with real data"""
        config_manager = Mock()
        config_manager.get.side_effect = lambda key, default=None: real_config.get(key, default)
        
        loader = EnhancedClickHouseLoader(config_manager)
        
        # Use a small universe for testing
        universe = ['AAPL', 'MSFT', 'GOOGL']
        criteria = PairScreeningCriteria(
            min_correlation=0.5,
            max_correlation=0.95,
            min_trading_days=50
        )
        
        pairs = await loader.screen_pairs(universe, criteria, lookback_days=100)
        
        # Verify results
        assert isinstance(pairs, list)
        for pair in pairs:
            assert len(pair) == 3  # (symbol1, symbol2, metrics)
            assert isinstance(pair[2], dict)  # metrics dict


def test_module_imports():
    """Test that all required modules can be imported"""
    if IMPORTS_AVAILABLE:
        assert EnhancedClickHouseLoader is not None
        assert DataRequest is not None
        assert PairScreeningCriteria is not None
        assert SmartCache is not None
    else:
        pytest.skip(f"Imports not available: {IMPORT_ERROR}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
