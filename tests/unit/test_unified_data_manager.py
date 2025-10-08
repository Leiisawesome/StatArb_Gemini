"""
Comprehensive Unit Tests for UnifiedDataManager (ClickHouseDataManager)
======================================================================

Professional test suite following institutional testing standards.
Tests all critical functionality including data loading, caching, validation,
connection handling, and ISystemComponent compliance.

Author: StatArb_Gemini Testing Framework
Version: 1.0.0 (Professional Testing Standards)
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import logging

# Import the components under test
from core_engine.data.manager import (
    ClickHouseDataManager, ClickHouseDataConfig, EnhancedMarketData
)

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Module-level fixtures
@pytest.fixture
def data_config() -> ClickHouseDataConfig:
    """Standard data manager configuration for testing"""
    return ClickHouseDataConfig(
        symbols=['AAPL', 'MSFT', 'GOOGL'],
        start_date="2024-01-01",
        end_date="2024-01-01",
        interval="1min",
        clickhouse_host="localhost",
        clickhouse_port=8123,
        enable_caching=True,
        cache_ttl=300
    )

@pytest.fixture
def data_manager(data_config) -> ClickHouseDataManager:
    """Initialize ClickHouseDataManager for testing"""
    return ClickHouseDataManager(data_config)

@pytest.fixture
def sample_market_data() -> pd.DataFrame:
    """Sample market data for testing"""
    timestamps = pd.date_range('2024-01-01 09:30:00', periods=100, freq='1min')
    data = []
    
    for i, ts in enumerate(timestamps):
        base_price = 150.0 + i * 0.1
        data.append({
            'timestamp': ts,
            'symbol': 'AAPL',
            'open': base_price,
            'high': base_price + 0.5,
            'low': base_price - 0.5,
            'close': base_price + 0.2,
            'volume': 1000 + i * 10,
            'transactions': 50 + i
        })
    
    return pd.DataFrame(data)


class TestClickHouseDataConfig:
    """Test suite for ClickHouseDataConfig"""
    
    def test_config_initialization_default(self):
        """Test default configuration initialization"""
        config = ClickHouseDataConfig()
        
        # Check default values
        assert config.interval == "1min"
        assert config.clickhouse_host == "localhost"
        assert config.clickhouse_port == 8123
        assert config.enable_caching is True
        assert len(config.symbols) > 0  # Should have default symbols
        
        logger.info("✅ Default config initialization test passed")
    
    def test_config_date_range_validation(self):
        """Test date range validation"""
        # Valid date range
        config = ClickHouseDataConfig(
            start_date="2024-01-01",
            end_date="2024-01-02"
        )
        assert config.start_date == "2024-01-01"
        assert config.end_date == "2024-01-02"
        
        # Invalid date range (start > end)
        with pytest.raises(ValueError, match="start_date.*must be.*end_date"):
            ClickHouseDataConfig(
                start_date="2024-01-02",
                end_date="2024-01-01"
            )
        
        logger.info("✅ Date range validation test passed")
    
    def test_config_backward_compatibility(self):
        """Test backward compatibility with target_date"""
        config = ClickHouseDataConfig(target_date="2024-01-15")
        
        # Should set both start_date and end_date to target_date
        assert config.start_date == "2024-01-15"
        assert config.end_date == "2024-01-15"
        
        logger.info("✅ Backward compatibility test passed")


class TestClickHouseDataManager:
    """Comprehensive test suite for ClickHouseDataManager"""
    
    # ========================================
    # INITIALIZATION AND LIFECYCLE TESTS
    # ========================================
    
    def test_initialization(self, data_config):
        """Test ClickHouseDataManager initialization"""
        data_manager = ClickHouseDataManager(data_config)
        
        # Verify configuration
        assert data_manager.enhanced_config.symbols == ['AAPL', 'MSFT', 'GOOGL']
        assert data_manager.enhanced_config.interval == "1min"
        
        # Verify initial state
        assert not data_manager.is_initialized
        assert not data_manager.is_operational
        
        # Verify collections are initialized
        assert isinstance(data_manager.subscribers, list)
        assert isinstance(data_manager._cache, dict)
        assert isinstance(data_manager._cache_timestamps, dict)
        
        logger.info("✅ Initialization test passed")
    
    @pytest.mark.asyncio
    async def test_component_lifecycle(self, data_manager):
        """Test ISystemComponent lifecycle methods"""
        
        # Test initialization
        result = await data_manager.initialize()
        assert result is True
        assert data_manager.is_initialized
        
        # Test start
        result = await data_manager.start()
        assert result is True
        assert data_manager.is_operational
        
        # Test health check
        health = await data_manager.health_check()
        assert health['healthy'] is True
        assert health['initialized'] is True
        assert health['operational'] is True
        assert health['component_type'] == 'ClickHouseDataManager'
        
        # Test status
        status = data_manager.get_status()
        assert status['component_type'] == 'ClickHouseDataManager'
        assert status['operational'] is True
        
        # Test stop
        result = await data_manager.stop()
        assert result is True
        assert not data_manager.is_operational
        
        logger.info("✅ Component lifecycle test passed")
    
    # ========================================
    # CONNECTION AND CONFIGURATION TESTS
    # ========================================
    
    @patch('requests.post')
    def test_connection_test_success(self, mock_post, data_manager):
        """Test successful ClickHouse connection"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "1"
        mock_post.return_value = mock_response
        
        result = data_manager._test_connection()
        assert result is True
        
        logger.info("✅ Connection test success passed")
    
    @patch('requests.post')
    def test_connection_test_failure(self, mock_post, data_manager):
        """Test ClickHouse connection failure"""
        # Mock connection failure
        mock_post.side_effect = Exception("Connection refused")
        
        result = data_manager._test_connection()
        assert result is False
        
        logger.info("✅ Connection test failure passed")
    
    # ========================================
    # DATA LOADING TESTS
    # ========================================
    
    @patch.object(ClickHouseDataManager, '_execute_query')
    def test_load_market_data_success(self, mock_execute, data_manager, sample_market_data):
        """Test successful market data loading"""
        mock_execute.return_value = sample_market_data
        
        # Force connection available for this test
        data_manager._connection_available = True
        data_manager._use_synthetic_data = False
        
        result = data_manager.load_market_data(
            symbols=['AAPL'],
            start_time=datetime(2024, 1, 1, 9, 30),
            end_time=datetime(2024, 1, 1, 16, 0),
            interval='1min'
        )
        
        assert not result.empty
        assert 'AAPL' in result['symbol'].values
        assert len(result) == len(sample_market_data)
        
        logger.info("✅ Market data loading success test passed")
    
    def test_synthetic_data_generation(self, data_manager):
        """Test synthetic data generation"""
        # Force synthetic data mode
        data_manager._use_synthetic_data = True
        
        result = data_manager.load_market_data(
            symbols=['AAPL', 'MSFT'],
            start_time=datetime(2024, 1, 1, 9, 30),
            end_time=datetime(2024, 1, 1, 10, 30),
            interval='1min'
        )
        
        assert not result.empty
        assert set(result['symbol'].unique()) == {'AAPL', 'MSFT'}
        
        # Check data structure
        required_columns = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        assert all(col in result.columns for col in required_columns)
        
        # Check price relationships
        assert (result['high'] >= result['low']).all()
        assert (result['close'] >= result['low']).all()
        assert (result['close'] <= result['high']).all()
        
        logger.info("✅ Synthetic data generation test passed")
    
    def test_data_caching(self, data_manager):
        """Test data caching functionality"""
        # Enable caching
        data_manager.enhanced_config.enable_caching = True
        data_manager._use_synthetic_data = True
        
        # First load - should cache
        result1 = data_manager.load_market_data(
            symbols=['AAPL'],
            start_time=datetime(2024, 1, 1, 9, 30),
            end_time=datetime(2024, 1, 1, 10, 30),
            interval='1min'
        )
        
        # Check cache
        assert len(data_manager._cache) > 0
        
        # Second load - should use cache
        result2 = data_manager.load_market_data(
            symbols=['AAPL'],
            start_time=datetime(2024, 1, 1, 9, 30),
            end_time=datetime(2024, 1, 1, 10, 30),
            interval='1min'
        )
        
        # Results should be identical (from cache)
        pd.testing.assert_frame_equal(result1, result2)
        
        logger.info("✅ Data caching test passed")
    
    # ========================================
    # DATA VALIDATION TESTS
    # ========================================
    
    def test_data_validation_valid_data(self, data_manager, sample_market_data):
        """Test data validation with valid data"""
        validation_result = data_manager.validate_data(sample_market_data)
        
        assert validation_result['valid'] is True
        assert validation_result['score'] > 0.9
        assert len(validation_result['issues']) == 0
        assert validation_result['metrics']['total_records'] == len(sample_market_data)
        
        logger.info("✅ Data validation (valid data) test passed")
    
    def test_data_validation_invalid_data(self, data_manager):
        """Test data validation with invalid data"""
        # Create invalid data
        invalid_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'symbol': ['AAPL'],
            'open': [100.0],
            'high': [99.0],  # Invalid: high < low
            'low': [101.0],
            'close': [102.0],  # Invalid: close > high
            'volume': [-100]  # Invalid: negative volume
        })
        
        validation_result = data_manager.validate_data(invalid_data)
        
        assert validation_result['valid'] is False
        assert validation_result['score'] < 0.7
        assert len(validation_result['issues']) > 0
        
        logger.info("✅ Data validation (invalid data) test passed")
    
    def test_data_validation_empty_data(self, data_manager):
        """Test data validation with empty data"""
        empty_data = pd.DataFrame()
        
        validation_result = data_manager.validate_data(empty_data)
        
        assert validation_result['valid'] is False
        assert validation_result['score'] == 0.0
        assert 'Empty dataset' in validation_result['issues']
        
        logger.info("✅ Data validation (empty data) test passed")
    
    # ========================================
    # CORE ENGINE INTERFACE TESTS
    # ========================================
    
    def test_get_market_data_interface(self, data_manager):
        """Test core engine compatible get_market_data interface"""
        # Force synthetic data for consistent testing
        data_manager._use_synthetic_data = True
        
        result = data_manager.get_market_data('AAPL')
        
        if result is not None:
            # Should return DataFrame with timestamp as column (not index)
            assert 'timestamp' in result.columns
            
            # Should have OHLCV columns
            expected_columns = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            assert all(col in result.columns for col in expected_columns)
            
            # Should have data
            assert len(result) > 0
            
            # Timestamp column should be datetime
            assert pd.api.types.is_datetime64_any_dtype(result['timestamp'])
        
        logger.info("✅ Core engine interface test passed")
    
    def test_get_current_price(self, data_manager):
        """Test current price retrieval"""
        # Force synthetic data
        data_manager._use_synthetic_data = True
        
        price = data_manager.get_current_price('AAPL')
        
        if price is not None:
            assert isinstance(price, float)
            assert price > 0
        
        logger.info("✅ Current price test passed")
    
    def test_get_multiple_prices(self, data_manager):
        """Test multiple price retrieval"""
        # Force synthetic data
        data_manager._use_synthetic_data = True
        
        prices = data_manager.get_multiple_prices(['AAPL', 'MSFT'])
        
        assert isinstance(prices, dict)
        # Should have prices for available symbols
        for symbol, price in prices.items():
            assert isinstance(price, float)
            assert price > 0
        
        logger.info("✅ Multiple prices test passed")
    
    # ========================================
    # SUBSCRIBER PATTERN TESTS
    # ========================================
    
    def test_subscriber_management(self, data_manager):
        """Test subscriber pattern functionality"""
        # Create mock subscriber
        mock_subscriber = Mock()
        mock_subscriber.on_market_data = Mock()
        
        # Add subscriber
        data_manager.add_subscriber(mock_subscriber)
        assert mock_subscriber in data_manager.subscribers
        
        # Remove subscriber
        data_manager.remove_subscriber(mock_subscriber)
        assert mock_subscriber not in data_manager.subscribers
        
        logger.info("✅ Subscriber management test passed")
    
    @pytest.mark.asyncio
    async def test_subscriber_notification(self, data_manager):
        """Test subscriber notification"""
        # Create mock subscriber
        mock_subscriber = Mock()
        mock_subscriber.on_market_data = Mock()
        
        data_manager.add_subscriber(mock_subscriber)
        
        # Create test market data
        market_data = EnhancedMarketData(
            symbol='AAPL',
            timestamp=datetime.now(),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000
        )
        
        # Notify subscribers
        await data_manager.notify_subscribers(market_data)
        
        # Verify notification was called
        mock_subscriber.on_market_data.assert_called_once_with(market_data)
        
        logger.info("✅ Subscriber notification test passed")
    
    # ========================================
    # CACHE MANAGEMENT TESTS
    # ========================================
    
    def test_cache_management(self, data_manager):
        """Test cache management functionality"""
        # Add some data to cache
        data_manager._cache['test_key'] = pd.DataFrame({'test': [1, 2, 3]})
        data_manager._cache_timestamps['test_key'] = datetime.now()
        
        # Check cache stats
        stats = data_manager.get_cache_stats()
        assert stats['cache_size'] > 0
        assert 'test_key' in stats['cache_keys']
        
        # Clear cache
        data_manager.clear_cache()
        assert len(data_manager._cache) == 0
        assert len(data_manager._cache_timestamps) == 0
        
        logger.info("✅ Cache management test passed")
    
    def test_cache_expiration(self, data_manager):
        """Test cache expiration logic"""
        # Set short cache TTL
        data_manager.enhanced_config.cache_ttl = 1  # 1 second
        
        # Add expired cache entry
        cache_key = "test_expired"
        data_manager._cache[cache_key] = pd.DataFrame({'test': [1]})
        data_manager._cache_timestamps[cache_key] = datetime.now() - timedelta(seconds=2)
        
        # Should not be cached (expired)
        assert not data_manager._is_cached(cache_key)
        
        # Add fresh cache entry
        fresh_key = "test_fresh"
        data_manager._cache[fresh_key] = pd.DataFrame({'test': [1]})
        data_manager._cache_timestamps[fresh_key] = datetime.now()
        
        # Should be cached (fresh)
        assert data_manager._is_cached(fresh_key)
        
        logger.info("✅ Cache expiration test passed")
    
    # ========================================
    # ERROR HANDLING TESTS
    # ========================================
    
    @patch.object(ClickHouseDataManager, '_execute_query')
    def test_query_error_handling(self, mock_execute, data_manager):
        """Test error handling in query execution"""
        # Mock query failure
        mock_execute.side_effect = Exception("Query failed")
        
        # Force real connection mode to trigger query
        data_manager._connection_available = True
        data_manager._use_synthetic_data = False
        
        # Should fall back to synthetic data
        result = data_manager.load_market_data(
            symbols=['AAPL'],
            start_time=datetime(2024, 1, 1, 9, 30),
            end_time=datetime(2024, 1, 1, 10, 30),
            interval='1min'
        )
        
        # Should still return data (synthetic fallback)
        assert not result.empty
        
        logger.info("✅ Query error handling test passed")
    
    def test_invalid_interval_handling(self, data_manager):
        """Test handling of invalid intervals"""
        with pytest.raises(ValueError, match="Unsupported interval"):
            data_manager._generate_synthetic_data(
                symbols=['AAPL'],
                start_time=datetime(2024, 1, 1, 9, 30),
                end_time=datetime(2024, 1, 1, 10, 30),
                interval='invalid_interval'
            )
        
        logger.info("✅ Invalid interval handling test passed")
    
    # ========================================
    # PERFORMANCE TESTS
    # ========================================
    
    def test_large_data_handling(self, data_manager):
        """Test handling of large datasets"""
        # Force synthetic data for consistent testing
        data_manager._use_synthetic_data = True
        
        # Load data for multiple symbols over longer period
        result = data_manager.load_market_data(
            symbols=['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN'],
            start_time=datetime(2024, 1, 1, 9, 30),
            end_time=datetime(2024, 1, 1, 16, 0),
            interval='1min'
        )
        
        # Should handle large dataset
        assert not result.empty
        assert len(result) > 1000  # Should have substantial data
        
        # Validate data structure
        validation_result = data_manager.validate_data(result)
        assert validation_result['valid'] is True
        
        logger.info("✅ Large data handling test passed")
    
    @pytest.mark.asyncio
    async def test_concurrent_data_access(self, data_manager):
        """Test concurrent data access"""
        # Force synthetic data
        data_manager._use_synthetic_data = True
        
        # Create multiple concurrent data requests
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        tasks = []
        
        for symbol in symbols:
            task = asyncio.create_task(
                asyncio.to_thread(
                    data_manager.load_market_data,
                    symbols=[symbol],
                    start_time=datetime(2024, 1, 1, 9, 30),
                    end_time=datetime(2024, 1, 1, 10, 30),
                    interval='1min'
                )
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        # Verify all requests completed successfully
        assert len(results) == len(symbols)
        for result in results:
            assert not result.empty
        
        logger.info("✅ Concurrent data access test passed")


class TestEnhancedMarketData:
    """Test suite for EnhancedMarketData"""
    
    def test_enhanced_market_data_creation(self):
        """Test EnhancedMarketData creation and conversion"""
        enhanced_data = EnhancedMarketData(
            symbol='AAPL',
            timestamp=datetime(2024, 1, 1, 10, 0),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
            transactions=50,
            source='clickhouse'
        )
        
        # Test attributes
        assert enhanced_data.symbol == 'AAPL'
        assert enhanced_data.transactions == 50
        assert enhanced_data.source == 'clickhouse'
        
        # Test conversion to core format
        core_data = enhanced_data.to_core_format()
        assert core_data.symbol == 'AAPL'
        assert core_data.volume == 1000
        
        logger.info("✅ EnhancedMarketData test passed")


class TestDataManagerIntegration:
    """Integration tests for data manager with other components"""
    
    @pytest.mark.asyncio
    async def test_full_data_pipeline(self, data_config):
        """Test complete data pipeline from initialization to data delivery"""
        # Initialize data manager
        data_manager = ClickHouseDataManager(data_config)
        
        # Force synthetic data for consistent testing
        data_manager._use_synthetic_data = True
        
        # Test full lifecycle
        await data_manager.initialize()
        await data_manager.start()
        
        # Load data
        result = data_manager.load_market_data(
            symbols=['AAPL'],
            start_time=datetime(2024, 1, 1, 9, 30),
            end_time=datetime(2024, 1, 1, 10, 30),
            interval='1min'
        )
        
        # Validate data
        validation_result = data_manager.validate_data(result)
        assert validation_result['valid'] is True
        
        # Test core engine interface
        market_data = data_manager.get_market_data('AAPL')
        assert market_data is not None
        
        # Test health check
        health = await data_manager.health_check()
        assert health['healthy'] is True
        
        # Cleanup
        await data_manager.stop()
        
        logger.info("✅ Full data pipeline integration test passed")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
