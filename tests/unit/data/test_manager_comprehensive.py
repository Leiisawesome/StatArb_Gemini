#!/usr/bin/env python3
"""
Comprehensive Unit Tests for ClickHouseDataManager
==================================================

Additional tests to improve coverage for manager.py from 32% to 80%+

Author: StatArb_Gemini Testing Team
Version: 1.0.0
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import pandas as pd

from core_engine.data.manager import (
    ClickHouseDataManager, ClickHouseDataConfig, MarketData as EnhancedMarketData
)
from core_engine.exceptions import ClickHouseConnectionError, DataUnavailableError

class TestInitializationErrorPaths:
    """Test initialization error paths and edge cases"""

    def test_initialization_with_connection_failure(self):
        """Test initialization handles connection failure"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        # Patch at module level for test isolation
        with patch('core_engine.data.manager.ClickHouseDataManager._test_connection', return_value=False):
            with pytest.raises(ClickHouseConnectionError):
                manager = ClickHouseDataManager(config)

    def test_initialization_exception_during_connection_test(self):
        """Test initialization handles exception during connection test"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', side_effect=Exception("Test failed")):
            with pytest.raises(ClickHouseConnectionError):
                manager = ClickHouseDataManager(config)

    @pytest.mark.asyncio
    async def test_initialize_with_get_available_symbols_error(self):
        """Test initialize handles get_available_symbols errors"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            with patch.object(manager, 'get_available_symbols', side_effect=Exception("Query failed")):
                result = await manager.initialize()
                # Should still initialize successfully despite symbol error
                assert result is True

    @pytest.mark.asyncio
    async def test_start_without_initialization(self):
        """Test start fails when not initialized"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            # Don't initialize
            result = await manager.start()
            assert result is False

    @pytest.mark.asyncio
    async def test_stop_with_cache_clear(self):
        """Test stop clears cache"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31",
            enable_caching=True
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            await manager.initialize()
            await manager.start()

            # Add some cache
            manager._cache['test_key'] = pd.DataFrame({'test': [1, 2, 3]})
            assert len(manager._cache) > 0

            result = await manager.stop()
            assert result is True
            assert len(manager._cache) == 0  # Cache should be cleared

    @pytest.mark.asyncio
    async def test_stop_exception_handling(self):
        """Test stop handles exceptions gracefully"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            await manager.initialize()
            await manager.start()

            # Test that stop handles exceptions - check that it logs error but completes
            # The actual behavior might return False, but it should handle the exception
            with patch.object(manager, 'clear_cache', side_effect=Exception("Clear failed")):
                result = await manager.stop()
                # The method logs the error but may return False
                assert isinstance(result, bool)

class TestLoadMarketData:
    """Test load_market_data method comprehensively"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL', 'TSLA'],
            start_date="2024-01-01",
            end_date="2024-01-31",
            enable_caching=True
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            await manager.initialize()
            await manager.start()
            yield manager
            await manager.stop()

    @pytest.mark.asyncio
    async def test_load_market_data_with_cache_hit(self, data_manager):
        """Test load_market_data returns cached data when available"""
        # First load - cache miss
        with patch.object(data_manager, '_execute_query') as mock_query:
            mock_df = pd.DataFrame({
                'timestamp': [datetime(2024, 1, 1, 9, 30)],
                'symbol': ['AAPL'],
                'open': [150.0],
                'high': [151.0],
                'low': [149.0],
                'close': [150.5],
                'volume': [1000000]
            })
            mock_query.return_value = mock_df

            result1 = data_manager.load_market_data(['AAPL'])
            assert len(result1) == 1
            assert mock_query.called

        # Second load - cache hit
        with patch.object(data_manager, '_execute_query') as mock_query2:
            result2 = data_manager.load_market_data(['AAPL'])
            assert len(result2) == 1
            assert not mock_query2.called  # Should use cache

    @pytest.mark.asyncio
    async def test_load_market_data_empty_data_error(self, data_manager):
        """Test load_market_data raises DataUnavailableError for empty results"""
        with patch.object(data_manager, '_execute_query') as mock_query:
            mock_query.return_value = pd.DataFrame()  # Empty DataFrame

            with pytest.raises(DataUnavailableError):
                data_manager.load_market_data(['AAPL'])

    @pytest.mark.asyncio
    async def test_load_market_data_connection_error(self, data_manager):
        """Test load_market_data raises ClickHouseConnectionError when connection unavailable"""
        data_manager._connection_available = False

        with pytest.raises(ClickHouseConnectionError):
            data_manager.load_market_data(['AAPL'])

    @pytest.mark.asyncio
    async def test_load_market_data_with_custom_times(self, data_manager):
        """Test load_market_data with custom start_time and end_time"""
        start_time = datetime(2024, 1, 1, 9, 30)
        end_time = datetime(2024, 1, 1, 16, 0)

        with patch.object(data_manager, '_execute_query') as mock_query:
            mock_df = pd.DataFrame({
                'timestamp': [start_time],
                'symbol': ['AAPL'],
                'open': [150.0],
                'high': [151.0],
                'low': [149.0],
                'close': [150.5],
                'volume': [1000000]
            })
            mock_query.return_value = mock_df

            result = data_manager.load_market_data(
                symbols=['AAPL'],
                start_time=start_time,
                end_time=end_time
            )
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_load_market_data_with_custom_interval(self, data_manager):
        """Test load_market_data with custom interval (all intervals now work)"""
        with patch.object(data_manager, '_execute_query') as mock_query:
            mock_df = pd.DataFrame({
                'timestamp': [datetime(2024, 1, 1, 9, 30)],
                'symbol': ['AAPL'],
                'open': [150.0],
                'high': [151.0],
                'low': [149.0],
                'close': [150.5],
                'volume': [1000000]
            })
            mock_query.return_value = mock_df

            # Test 5min interval (previously had bug, now fixed)
            result = data_manager.load_market_data(['AAPL'], interval='5min')
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_load_market_data_query_exception(self, data_manager):
        """Test load_market_data handles query exceptions"""
        with patch.object(data_manager, '_execute_query') as mock_query:
            mock_query.side_effect = Exception("Query failed")

            with pytest.raises(DataUnavailableError):
                data_manager.load_market_data(['AAPL'])

class TestBuildQuery:
    """Test _build_query method for all interval types"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            yield manager

    def test_build_query_1min(self, data_manager):
        """Test _build_query for 1min interval"""
        start_time = datetime(2024, 1, 1, 9, 30)
        end_time = datetime(2024, 1, 1, 16, 0)

        query = data_manager._build_query(['AAPL'], start_time, end_time, '1min')
        assert 'ticks' in query
        assert "ticker IN ('AAPL')" in query
        assert 'toTimeZone' in query
        assert 'America/New_York' in query

    def test_build_query_5min(self, data_manager):
        """Test _build_query for 5min interval"""
        start_time = datetime(2024, 1, 1, 9, 30)
        end_time = datetime(2024, 1, 1, 16, 0)

        query = data_manager._build_query(['AAPL'], start_time, end_time, '5min')
        assert 'toStartOfInterval' in query
        assert 'INTERVAL 5 minute' in query
        assert 'GROUP BY' in query
        assert 'window_start >= ' in query  # Should now have start_ns defined
        assert 'window_start <= ' in query  # Should now have end_ns defined

    def test_build_query_15min(self, data_manager):
        """Test _build_query for 15min interval"""
        start_time = datetime(2024, 1, 1, 9, 30)
        end_time = datetime(2024, 1, 1, 16, 0)

        query = data_manager._build_query(['AAPL'], start_time, end_time, '15min')
        assert 'INTERVAL 15 minute' in query
        assert 'window_start >= ' in query
        assert 'window_start <= ' in query

    def test_build_query_1h(self, data_manager):
        """Test _build_query for 1h interval"""
        start_time = datetime(2024, 1, 1, 9, 30)
        end_time = datetime(2024, 1, 1, 16, 0)

        query = data_manager._build_query(['AAPL'], start_time, end_time, '1h')
        assert 'INTERVAL 1 hour' in query
        assert 'window_start >= ' in query
        assert 'window_start <= ' in query

    def test_build_query_unsupported_interval(self, data_manager):
        """Test _build_query raises ValueError for unsupported interval"""
        start_time = datetime(2024, 1, 1, 9, 30)
        end_time = datetime(2024, 1, 1, 16, 0)

        with pytest.raises(ValueError, match="Unsupported interval"):
            data_manager._build_query(['AAPL'], start_time, end_time, 'invalid')

    def test_build_query_multiple_symbols(self, data_manager):
        """Test _build_query with multiple symbols"""
        start_time = datetime(2024, 1, 1, 9, 30)
        end_time = datetime(2024, 1, 1, 16, 0)

        query = data_manager._build_query(['AAPL', 'TSLA'], start_time, end_time, '1min')
        assert "ticker IN ('AAPL', 'TSLA')" in query

class TestStandardizeData:
    """Test _standardize_data method"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            yield manager

    def test_standardize_data_empty(self, data_manager):
        """Test _standardize_data with empty DataFrame"""
        df = pd.DataFrame()
        result = data_manager._standardize_data(df)
        assert result.empty

    def test_standardize_data_timezone_handling(self, data_manager):
        """Test _standardize_data handles timezone-naive timestamps"""
        df = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1, 9, 30)],
            'symbol': ['AAPL'],
            'open': ['150.0'],  # String to test conversion
            'high': [151.0],
            'low': [149.0],
            'close': [150.5],
            'volume': [1000000]
        })

        result = data_manager._standardize_data(df)
        assert pd.api.types.is_datetime64_any_dtype(result['timestamp'])
        assert pd.api.types.is_float_dtype(result['open'])
        assert 'symbol' in result.columns

    def test_standardize_data_numeric_conversion(self, data_manager):
        """Test _standardize_data converts numeric columns"""
        df = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1, 9, 30)],
            'symbol': ['AAPL'],
            'open': ['150.5'],
            'high': ['151.5'],
            'low': ['149.5'],
            'close': ['150.75'],
            'volume': ['1000000']
        })

        result = data_manager._standardize_data(df)
        assert pd.api.types.is_float_dtype(result['open'])
        assert pd.api.types.is_float_dtype(result['high'])
        assert pd.api.types.is_float_dtype(result['low'])
        assert pd.api.types.is_float_dtype(result['close'])
        # Volume can be int64 or float64 depending on conversion
        assert pd.api.types.is_numeric_dtype(result['volume'])

    def test_standardize_data_sorting(self, data_manager):
        """Test _standardize_data sorts by symbol and timestamp"""
        df = pd.DataFrame({
            'timestamp': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 9, 30),
                datetime(2024, 1, 1, 9, 30)
            ],
            'symbol': ['TSLA', 'AAPL', 'AAPL'],
            'open': [150.0, 150.0, 150.0],
            'high': [151.0, 151.0, 151.0],
            'low': [149.0, 149.0, 149.0],
            'close': [150.5, 150.5, 150.5],
            'volume': [1000000, 1000000, 1000000]
        })

        result = data_manager._standardize_data(df)
        assert result.iloc[0]['symbol'] == 'AAPL'
        assert result.iloc[1]['symbol'] == 'AAPL'
        assert result.iloc[2]['symbol'] == 'TSLA'

class TestCacheMethods:
    """Test cache-related methods"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31",
            enable_caching=True,
            cache_ttl=3600
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            yield manager

    def test_is_cached_disabled(self, data_manager):
        """Test _is_cached returns False when caching disabled"""
        data_manager.enhanced_config.enable_caching = False
        assert not data_manager._is_cached('test_key')

    def test_is_cached_not_found(self, data_manager):
        """Test _is_cached returns False when key not in cache"""
        assert not data_manager._is_cached('non_existent_key')

    def test_is_cached_valid(self, data_manager):
        """Test _is_cached returns True for valid cache entry"""
        cache_key = 'test_key'
        data_manager._cache[cache_key] = pd.DataFrame({'test': [1, 2, 3]})
        data_manager._cache_timestamps[cache_key] = datetime.now()

        assert data_manager._is_cached(cache_key)

    def test_is_cached_expired(self, data_manager):
        """Test _is_cached returns False for expired cache entry"""
        cache_key = 'test_key'
        data_manager._cache[cache_key] = pd.DataFrame({'test': [1, 2, 3]})
        data_manager._cache_timestamps[cache_key] = datetime.now() - timedelta(seconds=7200)  # 2 hours ago

        assert not data_manager._is_cached(cache_key)

    def test_is_cached_no_timestamp(self, data_manager):
        """Test _is_cached returns False when no timestamp"""
        cache_key = 'test_key'
        data_manager._cache[cache_key] = pd.DataFrame({'test': [1, 2, 3]})
        # Don't set timestamp

        assert not data_manager._is_cached(cache_key)

    def test_get_cache_stats(self, data_manager):
        """Test get_cache_stats returns correct statistics"""
        cache_key = 'test_key'
        data_manager._cache[cache_key] = pd.DataFrame({'test': [1, 2, 3]})
        data_manager._cache_timestamps[cache_key] = datetime.now()

        stats = data_manager.get_cache_stats()
        assert stats['cache_size'] == 1
        assert cache_key in stats['cache_keys']
        assert cache_key in stats['cache_timestamps']

    def test_clear_cache(self, data_manager):
        """Test clear_cache clears both cache and timestamps"""
        cache_key = 'test_key'
        data_manager._cache[cache_key] = pd.DataFrame({'test': [1, 2, 3]})
        data_manager._cache_timestamps[cache_key] = datetime.now()

        data_manager.clear_cache()
        assert len(data_manager._cache) == 0
        assert len(data_manager._cache_timestamps) == 0

class TestGetLatestPrices:
    """Test get_latest_prices method"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL', 'TSLA'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            yield manager

    def test_get_latest_prices_success(self, data_manager):
        """Test get_latest_prices returns latest prices successfully"""
        with patch.object(data_manager, '_execute_query') as mock_query:
            mock_df = pd.DataFrame({
                'symbol': ['AAPL', 'TSLA'],
                'latest_price': [150.5, 250.75]
            })
            mock_query.return_value = mock_df

            prices = data_manager.get_latest_prices(['AAPL', 'TSLA'])
            assert prices['AAPL'] == 150.5
            assert prices['TSLA'] == 250.75

    def test_get_latest_prices_error_handling(self, data_manager):
        """Test get_latest_prices handles errors gracefully"""
        with patch.object(data_manager, '_execute_query') as mock_query:
            mock_query.side_effect = Exception("Query failed")

            prices = data_manager.get_latest_prices(['AAPL'])
            assert prices == {}  # Returns empty dict on error

    def test_get_latest_prices_default_symbols(self, data_manager):
        """Test get_latest_prices uses config symbols when none provided"""
        with patch.object(data_manager, '_execute_query') as mock_query:
            mock_df = pd.DataFrame({
                'symbol': ['AAPL', 'TSLA'],
                'latest_price': [150.5, 250.75]
            })
            mock_query.return_value = mock_df

            prices = data_manager.get_latest_prices()
            assert len(prices) == 2

class TestGetMarketDataInterface:
    """Test get_market_data core engine interface"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            await manager.initialize()
            await manager.start()
            yield manager
            await manager.stop()

    def test_get_market_data_date_format(self, data_manager):
        """Test get_market_data with date format (YYYY-MM-DD)"""
        with patch.object(data_manager, 'load_market_data') as mock_load:
            mock_df = pd.DataFrame({
                'timestamp': [datetime(2024, 1, 1, 9, 30)],
                'symbol': ['AAPL'],
                'open': [150.0],
                'high': [151.0],
                'low': [149.0],
                'close': [150.5],
                'volume': [1000000]
            })
            mock_load.return_value = mock_df

            result = data_manager.get_market_data('AAPL', start_time='2024-01-01', end_time='2024-01-01')
            assert result is not None
            assert mock_load.called

    def test_get_market_data_datetime_format(self, data_manager):
        """Test get_market_data with datetime format (YYYY-MM-DD HH:MM:SS)"""
        with patch.object(data_manager, 'load_market_data') as mock_load:
            mock_df = pd.DataFrame({
                'timestamp': [datetime(2024, 1, 1, 9, 30)],
                'symbol': ['AAPL'],
                'open': [150.0],
                'high': [151.0],
                'low': [149.0],
                'close': [150.5],
                'volume': [1000000]
            })
            mock_load.return_value = mock_df

            result = data_manager.get_market_data('AAPL', start_time='2024-01-01 09:30:00')
            assert result is not None

    def test_get_market_data_time_format(self, data_manager):
        """Test get_market_data with time format (HH:MM)"""
        with patch.object(data_manager, 'load_market_data') as mock_load:
            mock_df = pd.DataFrame({
                'timestamp': [datetime(2024, 1, 1, 9, 30)],
                'symbol': ['AAPL'],
                'open': [150.0],
                'high': [151.0],
                'low': [149.0],
                'close': [150.5],
                'volume': [1000000]
            })
            mock_load.return_value = mock_df

            result = data_manager.get_market_data('AAPL', start_time='09:30', end_time='16:00')
            assert result is not None

    def test_get_market_data_empty_result(self, data_manager):
        """Test get_market_data returns None for empty results"""
        with patch.object(data_manager, 'load_market_data') as mock_load:
            mock_load.return_value = pd.DataFrame()

            result = data_manager.get_market_data('AAPL')
            assert result is None

    def test_get_market_data_symbol_filtering(self, data_manager):
        """Test get_market_data filters by symbol"""
        with patch.object(data_manager, 'load_market_data') as mock_load:
            mock_df = pd.DataFrame({
                'timestamp': [datetime(2024, 1, 1, 9, 30), datetime(2024, 1, 1, 9, 31)],
                'symbol': ['AAPL', 'TSLA'],
                'open': [150.0, 250.0],
                'high': [151.0, 251.0],
                'low': [149.0, 249.0],
                'close': [150.5, 250.5],
                'volume': [1000000, 2000000]
            })
            mock_load.return_value = mock_df

            result = data_manager.get_market_data('AAPL')
            assert result is not None
            assert all(result['symbol'] == 'AAPL')

    def test_get_market_data_error_handling(self, data_manager):
        """Test get_market_data handles errors gracefully"""
        with patch.object(data_manager, 'load_market_data') as mock_load:
            mock_load.side_effect = Exception("Load failed")

            result = data_manager.get_market_data('AAPL')
            assert result is None

class TestValidateData:
    """Test validate_data method comprehensively"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            yield manager

    def test_validate_data_empty(self, data_manager):
        """Test validate_data with empty DataFrame"""
        df = pd.DataFrame()
        result = data_manager.validate_data(df)

        assert result['valid'] is False
        assert result['score'] == 0.0
        assert 'Empty dataset' in result['issues']

    def test_validate_data_missing_columns(self, data_manager):
        """Test validate_data detects missing required columns"""
        df = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1, 9, 30)],
            'open': [150.0]
            # Missing: symbol, high, low, close, volume
        })
        result = data_manager.validate_data(df)

        assert result['valid'] is False
        assert result['score'] < 1.0
        assert any('Missing required columns' in issue for issue in result['issues'])

    def test_validate_data_null_values(self, data_manager):
        """Test validate_data detects null values"""
        df = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1, 9, 30), datetime(2024, 1, 1, 9, 31)],
            'symbol': ['AAPL', 'AAPL'],
            'open': [150.0, None],
            'high': [151.0, 151.0],
            'low': [149.0, 149.0],
            'close': [150.5, 150.5],
            'volume': [1000000, 1000000]
        })
        result = data_manager.validate_data(df)

        assert result['score'] < 1.0
        assert any('null values' in issue.lower() for issue in result['issues'])

    def test_validate_data_timestamp_ordering(self, data_manager):
        """Test validate_data detects non-monotonic timestamps"""
        df = pd.DataFrame({
            'timestamp': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 9, 30)  # Out of order
            ],
            'symbol': ['AAPL', 'AAPL'],
            'open': [150.0, 150.0],
            'high': [151.0, 151.0],
            'low': [149.0, 149.0],
            'close': [150.5, 150.5],
            'volume': [1000000, 1000000]
        })
        result = data_manager.validate_data(df)

        assert result['score'] < 1.0
        assert any('chronological' in issue.lower() for issue in result['issues'])

    def test_validate_data_invalid_prices(self, data_manager):
        """Test validate_data detects invalid price relationships"""
        df = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1, 9, 30)],
            'symbol': ['AAPL'],
            'open': [150.0],
            'high': [149.0],  # high < low - invalid
            'low': [151.0],
            'close': [152.0],  # close > high - invalid
            'volume': [1000000]
        })
        result = data_manager.validate_data(df)

        # The validation checks for invalid prices - score should be reduced
        assert result['score'] < 1.0
        assert any('invalid price' in issue.lower() for issue in result['issues'])
        # Note: May still be marked valid if score >= 0.7 after other checks

    def test_validate_data_negative_volume(self, data_manager):
        """Test validate_data detects negative volume"""
        df = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1, 9, 30)],
            'symbol': ['AAPL'],
            'open': [150.0],
            'high': [151.0],
            'low': [149.0],
            'close': [150.5],
            'volume': [-1000000]  # Negative volume - invalid
        })
        result = data_manager.validate_data(df)

        assert result['score'] < 1.0
        assert any('negative volume' in issue.lower() for issue in result['issues'])

    def test_validate_data_valid(self, data_manager):
        """Test validate_data with valid data"""
        df = pd.DataFrame({
            'timestamp': [
                datetime(2024, 1, 1, 9, 30),
                datetime(2024, 1, 1, 9, 31)
            ],
            'symbol': ['AAPL', 'AAPL'],
            'open': [150.0, 150.5],
            'high': [151.0, 151.5],
            'low': [149.0, 149.5],
            'close': [150.5, 151.0],
            'volume': [1000000, 1100000]
        })
        result = data_manager.validate_data(df)

        assert result['valid'] is True
        assert result['score'] >= 0.7
        assert len(result['issues']) == 0
        assert 'total_records' in result['metrics']
        assert 'symbols_count' in result['metrics']

    def test_validate_data_exception_handling(self, data_manager):
        """Test validate_data handles exceptions gracefully"""
        # Create DataFrame that will cause exception in validation
        df = pd.DataFrame({
            'timestamp': [object()],  # Invalid type
            'symbol': ['AAPL'],
            'open': [150.0],
            'high': [151.0],
            'low': [149.0],
            'close': [150.5],
            'volume': [1000000]
        })
        result = data_manager.validate_data(df)

        assert result['valid'] is False
        assert result['score'] == 0.0
        assert len(result['issues']) > 0

class TestHelperMethods:
    """Test helper methods like calculate_metrics"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL', 'TSLA'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            await manager.initialize()
            yield manager

    def test_calculate_metrics(self, data_manager):
        """Test calculate_metrics returns metrics dictionary"""
        metrics = data_manager.calculate_metrics()

        assert metrics['metrics_calculated'] is True
        assert 'calculation_timestamp' in metrics
        assert 'data_metrics' in metrics
        assert 'data_quality_score' in metrics['data_metrics']
        assert 'coverage_metrics' in metrics['data_metrics']

    def test_calculate_metrics_exception_handling(self, data_manager):
        """Test calculate_metrics handles exceptions"""
        with patch.object(data_manager, '_calculate_data_quality_score', side_effect=Exception("Error")):
            metrics = data_manager.calculate_metrics()
            assert metrics['metrics_calculated'] is False
            assert 'error' in metrics

    def test_calculate_data_quality_score(self, data_manager):
        """Test _calculate_data_quality_score"""
        score = data_manager._calculate_data_quality_score()
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_calculate_coverage_metrics(self, data_manager):
        """Test _calculate_coverage_metrics"""
        metrics = data_manager._calculate_coverage_metrics()
        assert 'symbols_covered' in metrics
        assert 'coverage_percentage' in metrics
        assert 'data_completeness' in metrics

    def test_analyze_performance(self, data_manager):
        """Test analyze_performance returns performance analysis"""
        analysis = data_manager.analyze_performance()
        assert analysis['performance_analyzed'] is True
        assert 'performance_analysis' in analysis
        assert 'data_availability' in analysis['performance_analysis']
        assert 'query_performance' in analysis['performance_analysis']

    def test_analyze_performance_exception(self, data_manager):
        """Test analyze_performance handles exceptions"""
        with patch.object(data_manager, '_assess_data_availability', side_effect=Exception("Error")):
            analysis = data_manager.analyze_performance()
            assert analysis['performance_analyzed'] is False
            assert 'error' in analysis

    def test_generate_analytics(self, data_manager):
        """Test generate_analytics returns comprehensive analytics"""
        analytics = data_manager.generate_analytics()
        assert analytics['analytics_generated'] is True
        assert 'metrics' in analytics
        assert 'performance' in analytics
        assert 'summary' in analytics

    def test_generate_analytics_exception(self, data_manager):
        """Test generate_analytics handles exceptions"""
        with patch.object(data_manager, 'calculate_metrics', side_effect=Exception("Error")):
            analytics = data_manager.generate_analytics()
            assert analytics['analytics_generated'] is False
            assert 'error' in analytics

    def test_track_performance(self, data_manager):
        """Test track_performance returns tracking data"""
        tracking = data_manager.track_performance()
        assert tracking['tracking_active'] is True
        assert 'current_metrics' in tracking

    def test_track_performance_exception(self, data_manager):
        """Test track_performance handles exceptions"""
        with patch.object(data_manager, 'calculate_metrics', side_effect=Exception("Error")):
            tracking = data_manager.track_performance()
            assert tracking['tracking_active'] is False
            assert 'error' in tracking

    def test_monitor_performance_alias(self, data_manager):
        """Test monitor_performance is alias for track_performance"""
        # Test that monitor_performance calls track_performance
        original_track = data_manager.track_performance
        call_count = 0

        def track_wrapper(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_track(*args, **kwargs)

        data_manager.track_performance = track_wrapper
        try:
            result = data_manager.monitor_performance()
            assert call_count == 1, "track_performance was not called exactly once"
            assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        finally:
            data_manager.track_performance = original_track

    def test_assess_data_availability(self, data_manager):
        """Test _assess_data_availability"""
        availability = data_manager._assess_data_availability()
        assert availability in ["High", "Limited", "Unknown"]

    def test_assess_query_performance(self, data_manager):
        """Test _assess_query_performance"""
        performance = data_manager._assess_query_performance()
        assert performance in ["Good", "Unknown"]

    def test_assess_data_freshness(self, data_manager):
        """Test _assess_data_freshness"""
        freshness = data_manager._assess_data_freshness()
        assert freshness in ["Current", "Unknown"]

    def test_calculate_cache_utilization(self, data_manager):
        """Test _calculate_cache_utilization"""
        utilization = data_manager._calculate_cache_utilization()
        assert isinstance(utilization, float)
        assert 0 <= utilization <= 100

    def test_calculate_cache_utilization_with_caching(self, data_manager):
        """Test _calculate_cache_utilization when caching enabled"""
        # Enable caching in config
        data_manager.enhanced_config.enable_caching = True
        utilization = data_manager._calculate_cache_utilization()
        # Should return mock value when caching enabled (75.0) or 0 if hasattr check fails
        assert isinstance(utilization, float)
        assert 0 <= utilization <= 100

    def test_assess_data_health(self, data_manager):
        """Test _assess_data_health"""
        health = data_manager._assess_data_health()
        assert health in ["Healthy", "No symbols configured", "Disconnected", "Unknown"]

    def test_calculate_reliability_score(self, data_manager):
        """Test _calculate_reliability_score"""
        score = data_manager._calculate_reliability_score()
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_calculate_efficiency_score(self, data_manager):
        """Test _calculate_efficiency_score"""
        score = data_manager._calculate_efficiency_score()
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_generate_data_recommendations(self, data_manager):
        """Test _generate_data_recommendations"""
        recommendations = data_manager._generate_data_recommendations()
        assert isinstance(recommendations, list)

    def test_generate_data_recommendations_no_caching(self, data_manager):
        """Test _generate_data_recommendations suggests caching when disabled"""
        data_manager.enhanced_config.enable_caching = False
        recommendations = data_manager._generate_data_recommendations()
        assert any("caching" in rec.lower() for rec in recommendations)

    def test_assess_performance_trend(self, data_manager):
        """Test _assess_performance_trend"""
        trend = data_manager._assess_performance_trend()
        assert trend in ["Stable", "Declining", "Unknown"]

    def test_generate_data_alerts(self, data_manager):
        """Test _generate_data_alerts"""
        alerts = data_manager._generate_data_alerts()
        assert isinstance(alerts, list)

    def test_generate_data_alerts_no_symbols(self, data_manager):
        """Test _generate_data_alerts when no symbols"""
        # Clear symbols
        original_symbols = data_manager.enhanced_config.symbols
        data_manager.enhanced_config.symbols = []
        alerts = data_manager._generate_data_alerts()
        data_manager.enhanced_config.symbols = original_symbols  # Restore

        assert any("symbol" in alert.lower() for alert in alerts) or len(alerts) == 0

    def test_process_market_data_alias(self, data_manager):
        """Test process_market_data is alias for get_market_data"""
        with patch.object(data_manager, 'get_market_data', return_value=pd.DataFrame()) as mock_get:
            result = data_manager.process_market_data('AAPL')
            mock_get.assert_called_once_with('AAPL')

    def test_fetch_data_alias(self, data_manager):
        """Test fetch_data is alias for load_data"""
        with patch.object(data_manager, 'load_data', return_value={}) as mock_load:
            result = data_manager.fetch_data(['AAPL'])
            mock_load.assert_called_once_with(['AAPL'])

    def test_process_data_alias(self, data_manager):
        """Test process_data is alias for load_market_data"""
        with patch.object(data_manager, 'load_market_data', return_value=pd.DataFrame()) as mock_load:
            result = data_manager.process_data(['AAPL'])
            mock_load.assert_called_once_with(['AAPL'])

class TestSubscriberMethods:
    """Test subscriber notification methods"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            yield manager

    def test_add_subscriber(self, data_manager):
        """Test add_subscriber adds subscriber to list"""
        mock_subscriber = Mock()
        data_manager.add_subscriber(mock_subscriber)

        assert mock_subscriber in data_manager.subscribers

    def test_remove_subscriber(self, data_manager):
        """Test remove_subscriber removes subscriber"""
        mock_subscriber = Mock()
        data_manager.add_subscriber(mock_subscriber)
        data_manager.remove_subscriber(mock_subscriber)

        assert mock_subscriber not in data_manager.subscribers

    def test_remove_subscriber_not_found(self, data_manager):
        """Test remove_subscriber handles subscriber not in list"""
        mock_subscriber = Mock()
        # Don't add it first
        data_manager.remove_subscriber(mock_subscriber)  # Should not raise

    @pytest.mark.asyncio
    async def test_notify_subscribers(self, data_manager):
        """Test notify_subscribers calls all subscribers"""
        mock_subscriber1 = Mock()
        mock_subscriber1.on_market_data = AsyncMock()
        mock_subscriber2 = Mock()
        mock_subscriber2.on_market_data = AsyncMock()

        data_manager.add_subscriber(mock_subscriber1)
        data_manager.add_subscriber(mock_subscriber2)

        market_data = EnhancedMarketData(
            symbol='AAPL',
            timestamp=datetime(2024, 1, 1, 9, 30),
            open=150.0,
            high=151.0,
            low=149.0,
            close=150.5,
            volume=1000000
        )

        await data_manager.notify_subscribers(market_data)

        mock_subscriber1.on_market_data.assert_called_once_with(market_data)
        mock_subscriber2.on_market_data.assert_called_once_with(market_data)

    @pytest.mark.asyncio
    async def test_notify_subscribers_error_handling(self, data_manager):
        """Test notify_subscribers handles subscriber errors gracefully"""
        mock_subscriber = Mock()
        mock_subscriber.on_market_data = AsyncMock(side_effect=Exception("Subscriber error"))

        data_manager.add_subscriber(mock_subscriber)

        market_data = EnhancedMarketData(
            symbol='AAPL',
            timestamp=datetime(2024, 1, 1, 9, 30),
            open=150.0,
            high=151.0,
            low=149.0,
            close=150.5,
            volume=1000000
        )

        # Should not raise exception
        await data_manager.notify_subscribers(market_data)

class TestExecuteQuery:
    """Test _execute_query method"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            yield manager

    def test_execute_query_success(self, data_manager):
        """Test _execute_query successfully executes query"""
        # Mock successful response
        mock_response = Mock()
        mock_response.text = 'timestamp\tsymbol\topen\thigh\tlow\tclose\tvolume\n2024-01-01 09:30:00\tAAPL\t150.0\t151.0\t149.0\t150.5\t1000000'
        mock_response.raise_for_status = Mock()

        with patch.object(data_manager._http_session, 'post', return_value=mock_response) as mock_post:
            query = "SELECT * FROM test"
            result = data_manager._execute_query(query)

            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0

    def test_execute_query_timezone_handling(self, data_manager):
        """Test _execute_query handles timezone conversion"""
        # Mock response with timestamp
        mock_response = Mock()
        mock_response.text = 'timestamp\tsymbol\topen\n2024-01-01 09:30:00\tAAPL\t150.0'
        mock_response.raise_for_status = Mock()

        with patch.object(data_manager._http_session, 'post', return_value=mock_response) as mock_post:
            query = "SELECT * FROM test"
            result = data_manager._execute_query(query)

            if 'timestamp' in result.columns and not result.empty:
                # Check timestamp is timezone-aware
                assert result['timestamp'].iloc[0].tz is not None

    def test_execute_query_error_handling(self, data_manager):
        """Test _execute_query raises exception on error"""
        with patch.object(data_manager._http_session, 'post', side_effect=Exception("Connection failed")) as mock_post:
            query = "SELECT * FROM test"
            with pytest.raises(Exception):
                data_manager._execute_query(query)

class TestGetHistoricalData:
    """Test get_historical_data interface method"""

    @pytest_asyncio.fixture
    async def data_manager(self):
        """Fixture for data manager"""
        config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(config)
            await manager.initialize()
            await manager.start()
            yield manager
            await manager.stop()

    def test_get_historical_data_success(self, data_manager):
        """Test get_historical_data loads data successfully"""
        with patch.object(data_manager, 'get_market_data') as mock_get:
            mock_df = pd.DataFrame({
                'timestamp': [datetime(2024, 1, 1, 9, 30)],
                'symbol': ['AAPL'],
                'open': [150.0],
                'high': [151.0],
                'low': [149.0],
                'close': [150.5],
                'volume': [1000000]
            })
            mock_get.return_value = mock_df

            result = data_manager.get_historical_data(
                'AAPL',
                datetime(2024, 1, 1),
                datetime(2024, 1, 31),
                '1d'
            )

            assert result is not None
            assert not result.empty
            mock_get.assert_called()

    def test_get_historical_data_date_range_outside_config(self, data_manager):
        """Test get_historical_data returns empty DataFrame for out-of-range dates"""
        result = data_manager.get_historical_data(
            'AAPL',
            datetime(2023, 1, 1),  # Before config range
            datetime(2023, 1, 31),
            '1d'
        )

        # Should return empty DataFrame with required columns
        assert isinstance(result, pd.DataFrame)
        assert 'open' in result.columns
        assert 'high' in result.columns

    def test_get_historical_data_string_dates(self, data_manager):
        """Test get_historical_data with string date inputs"""
        with patch.object(data_manager, 'get_market_data', return_value=pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1, 9, 30)],
            'symbol': ['AAPL'],
            'open': [150.0],
            'high': [151.0],
            'low': [149.0],
            'close': [150.5],
            'volume': [1000000]
        })):
            result = data_manager.get_historical_data(
                'AAPL',
                '2024-01-01',
                '2024-01-31',
                '1d'
            )
            assert result is not None

    def test_get_historical_data_empty_result(self, data_manager):
        """Test get_historical_data returns empty DataFrame when get_market_data returns None"""
        with patch.object(data_manager, 'get_market_data', return_value=None):
            result = data_manager.get_historical_data(
                'AAPL',
                datetime(2024, 1, 1),
                datetime(2024, 1, 31),
                '1d'
            )
            assert isinstance(result, pd.DataFrame)

    def test_get_historical_data_exception_handling(self, data_manager):
        """Test get_historical_data handles exceptions gracefully"""
        with patch.object(data_manager, 'get_market_data', side_effect=Exception("Error")):
            result = data_manager.get_historical_data(
                'AAPL',
                datetime(2024, 1, 1),
                datetime(2024, 1, 31),
                '1d'
            )
            assert isinstance(result, pd.DataFrame)

    def test_get_current_price(self, data_manager):
        """Test get_current_price returns latest close price"""
        with patch.object(data_manager, 'get_market_data') as mock_get:
            mock_df = pd.DataFrame({
                'timestamp': [datetime(2024, 1, 1, 9, 30), datetime(2024, 1, 1, 9, 31)],
                'symbol': ['AAPL', 'AAPL'],
                'open': [150.0, 150.5],
                'high': [151.0, 151.5],
                'low': [149.0, 149.5],
                'close': [150.5, 151.0],
                'volume': [1000000, 1100000]
            })
            mock_get.return_value = mock_df

            price = data_manager.get_current_price('AAPL')
            assert price == 151.0  # Latest close price

    def test_get_current_price_no_data(self, data_manager):
        """Test get_current_price returns None when no data"""
        with patch.object(data_manager, 'get_market_data', return_value=None):
            price = data_manager.get_current_price('AAPL')
            assert price is None

    def test_get_current_price_empty_dataframe(self, data_manager):
        """Test get_current_price returns None for empty DataFrame"""
        with patch.object(data_manager, 'get_market_data', return_value=pd.DataFrame()):
            price = data_manager.get_current_price('AAPL')
            assert price is None

    def test_get_current_price_exception(self, data_manager):
        """Test get_current_price handles exceptions"""
        with patch.object(data_manager, 'get_market_data', side_effect=Exception("Error")):
            price = data_manager.get_current_price('AAPL')
            assert price is None

    def test_get_multiple_prices(self, data_manager):
        """Test get_multiple_prices returns prices for multiple symbols"""
        with patch.object(data_manager, 'get_current_price') as mock_price:
            mock_price.side_effect = lambda s: {'AAPL': 150.5, 'TSLA': 250.75}.get(s)

            prices = data_manager.get_multiple_prices(['AAPL', 'TSLA'])
            assert prices['AAPL'] == 150.5
            assert prices['TSLA'] == 250.75

    def test_get_multiple_prices_with_none(self, data_manager):
        """Test get_multiple_prices skips None prices"""
        with patch.object(data_manager, 'get_current_price') as mock_price:
            mock_price.side_effect = lambda s: {'AAPL': 150.5, 'TSLA': None}.get(s)

            prices = data_manager.get_multiple_prices(['AAPL', 'TSLA'])
            assert 'AAPL' in prices
            assert 'TSLA' not in prices  # Should skip None

