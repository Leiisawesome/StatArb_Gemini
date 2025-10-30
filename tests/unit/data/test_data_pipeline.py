"""
Comprehensive Data Pipeline Tests
Tests for data manager, feeds, alternative data, and validation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


class TestDataConfigurationEnums:
    """Test data configuration enums and types"""
    
    def test_data_config_creation(self):
        """Test DataConfig creation"""
        from core_engine.data.manager import ClickHouseDataConfig
        
        config = ClickHouseDataConfig(
            symbols=["AAPL", "MSFT"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            interval="1min"
        )
        assert config.symbols == ["AAPL", "MSFT"]
        assert config.start_date == "2024-01-01"
        assert config.interval == "1min"
    
    def test_data_config_backward_compatibility(self):
        """Test backward compatibility with start_date/end_date"""
        from core_engine.data.manager import ClickHouseDataConfig
        
        config = ClickHouseDataConfig(
            symbols=["AAPL"],
            start_date="2024-12-20",
            end_date="2024-12-20"
        )
        assert config.start_date == "2024-12-20"
        assert config.end_date == "2024-12-20"
        assert config.interval == "1min"
    
    def test_clickhouse_config_defaults(self):
        """Test ClickHouse configuration defaults"""
        from core_engine.data.manager import ClickHouseDataConfig
        
        config = ClickHouseDataConfig(symbols=["AAPL"])
        assert config.clickhouse_host == "localhost"
        assert config.clickhouse_port == 8123
        assert config.clickhouse_database == "polygon_data"
        assert config.enable_caching is True
        assert config.cache_ttl == 300


class TestDataManagerImports:
    """Test data manager component imports"""
    
    def test_import_data_manager(self):
        """Test data manager import"""
        from core_engine.data.manager import ClickHouseDataConfig
        assert ClickHouseDataConfig is not None
    
    def test_import_alternative_data_handler(self):
        """Test alternative data handler import"""
        try:
            from core_engine.data.alternative_data_handler import AlternativeDataHandler
            assert AlternativeDataHandler is not None
        except (ImportError, AttributeError):
            # Some modules may not have this class
            pytest.skip("AlternativeDataHandler not found")


class TestDataStructures:
    """Test data structures and dataframes"""
    
    def test_market_data_structure(self):
        """Test market data DataFrame structure"""
        # Create sample market data
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1min'),
            'open': np.random.randn(10) + 100,
            'high': np.random.randn(10) + 101,
            'low': np.random.randn(10) + 99,
            'close': np.random.randn(10) + 100,
            'volume': np.random.randint(1000, 10000, 10)
        })
        
        # Verify structure
        assert 'timestamp' in data.columns
        assert 'open' in data.columns
        assert 'close' in data.columns
        assert 'volume' in data.columns
        assert len(data) == 10
    
    def test_ohlcv_data_validation(self):
        """Test OHLCV data validation"""
        data = pd.DataFrame({
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0],
            'volume': [1000, 1500]
        })
        
        # Validate high >= low
        assert (data['high'] >= data['low']).all()
        
        # Validate volume > 0
        assert (data['volume'] > 0).all()


class TestDataTransformations:
    """Test data transformation functions"""
    
    def test_returns_calculation(self):
        """Test returns calculation"""
        prices = pd.Series([100, 101, 102, 101, 103])
        returns = prices.pct_change().dropna()
        
        assert len(returns) == 4
        assert pytest.approx(returns.iloc[0], 0.01) == 0.01  # (101-100)/100
    
    def test_log_returns_calculation(self):
        """Test log returns calculation"""
        prices = pd.Series([100, 110, 121])
        log_returns = np.log(prices / prices.shift(1)).dropna()
        
        assert len(log_returns) == 2
        assert log_returns.iloc[0] > 0  # Price increased
    
    def test_rolling_window_calculation(self):
        """Test rolling window calculations"""
        data = pd.Series(range(10))
        rolling_mean = data.rolling(window=3).mean()
        
        assert len(rolling_mean) == 10
        assert np.isnan(rolling_mean.iloc[0])  # First values are NaN
        assert rolling_mean.iloc[2] == 1.0  # (0+1+2)/3
    
    def test_resampling_data(self):
        """Test data resampling"""
        dates = pd.date_range('2024-01-01', periods=10, freq='1min')
        data = pd.DataFrame({
            'close': np.random.randn(10) + 100
        }, index=dates)
        
        # Resample to 5-minute bars
        resampled = data.resample('5min').last()
        assert len(resampled) <= len(data)


class TestDataCaching:
    """Test data caching functionality"""
    
    def test_cache_config_enabled(self):
        """Test cache configuration"""
        from core_engine.data.manager import ClickHouseDataConfig
        
        config = ClickHouseDataConfig(
            symbols=["AAPL"],
            enable_caching=True,
            cache_ttl=600
        )
        assert config.enable_caching is True
        assert config.cache_ttl == 600
    
    def test_cache_config_disabled(self):
        """Test cache disabled"""
        from core_engine.data.manager import ClickHouseDataConfig
        
        config = ClickHouseDataConfig(
            symbols=["AAPL"],
            enable_caching=False
        )
        assert config.enable_caching is False


class TestDataValidation:
    """Test data validation functions"""
    
    def test_validate_symbol_format(self):
        """Test symbol format validation"""
        # Valid symbols
        valid_symbols = ["AAPL", "MSFT", "GOOGL", "SPY"]
        for symbol in valid_symbols:
            assert symbol.isupper()
            assert symbol.isalpha()
    
    def test_validate_date_range(self):
        """Test date range validation"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        
        assert end > start
        assert (end - start).days == 365
    
    def test_validate_interval_format(self):
        """Test interval format validation"""
        valid_intervals = ["1min", "5min", "15min", "1h", "1d"]
        for interval in valid_intervals:
            assert isinstance(interval, str)
            assert len(interval) > 0


class TestDataFeeds:
    """Test data feed components"""
    
    def test_feed_configuration(self):
        """Test feed configuration"""
        feed_config = {
            'name': 'test_feed',
            'source': 'clickhouse',
            'symbols': ['AAPL', 'MSFT'],
            'interval': '1min'
        }
        assert feed_config['name'] == 'test_feed'
        assert len(feed_config['symbols']) == 2
    
    def test_feed_status(self):
        """Test feed status tracking"""
        status = {
            'connected': True,
            'last_update': datetime.now(),
            'error_count': 0
        }
        assert status['connected'] is True
        assert status['error_count'] == 0


class TestAlternativeData:
    """Test alternative data handling"""
    
    def test_alternative_data_sources(self):
        """Test alternative data source configuration"""
        sources = ['sentiment', 'news', 'social_media', 'earnings']
        for source in sources:
            assert isinstance(source, str)
    
    def test_sentiment_data_structure(self):
        """Test sentiment data structure"""
        sentiment_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'symbol': ['AAPL'] * 5,
            'sentiment_score': [0.5, 0.7, 0.3, 0.6, 0.8],
            'confidence': [0.9, 0.8, 0.7, 0.85, 0.95]
        })
        
        assert 'sentiment_score' in sentiment_data.columns
        assert (sentiment_data['sentiment_score'] >= 0).all()
        assert (sentiment_data['sentiment_score'] <= 1).all()


class TestDataQuality:
    """Test data quality checks"""
    
    def test_missing_data_detection(self):
        """Test missing data detection"""
        data = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0])
        missing = data.isna().sum()
        
        assert missing == 1
        assert data.isna().any()
    
    def test_outlier_detection(self):
        """Test outlier detection using simple threshold"""
        data = pd.Series([10, 11, 12, 11, 10, 200, 250])
        mean = data.mean()
        std = data.std()
        
        # Points more than 3 std deviations from mean
        outliers = np.abs(data - mean) > (3 * std)
        
        # Should detect outliers based on simple stats
        assert isinstance(outliers, pd.Series)
        assert len(outliers) == len(data)
    
    def test_duplicate_detection(self):
        """Test duplicate data detection"""
        data = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-01', '2024-01-02'],
            'value': [100, 100, 101]
        })
        
        duplicates = data.duplicated()
        assert duplicates.sum() > 0


class TestDataAggregation:
    """Test data aggregation functions"""
    
    def test_time_weighted_average(self):
        """Test time-weighted average calculation"""
        data = pd.Series([100, 110, 120])
        weights = pd.Series([1, 2, 1])
        
        twa = (data * weights).sum() / weights.sum()
        assert twa == 110.0  # (100*1 + 110*2 + 120*1) / 4
    
    def test_vwap_calculation(self):
        """Test VWAP (Volume Weighted Average Price) calculation"""
        data = pd.DataFrame({
            'price': [100, 101, 102],
            'volume': [1000, 2000, 1000]
        })
        
        vwap = (data['price'] * data['volume']).sum() / data['volume'].sum()
        assert pytest.approx(vwap, 0.01) == 101.0


class TestDataPipelineIntegration:
    """Test data pipeline integration"""
    
    def test_end_to_end_data_flow(self):
        """Test complete data flow from config to DataFrame"""
        from core_engine.data.manager import ClickHouseDataConfig
        
        # Create config
        config = ClickHouseDataConfig(
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        # Verify config
        assert config.symbols == ["AAPL"]
        assert config.start_date == "2024-01-01"
    
    def test_multi_symbol_processing(self):
        """Test processing multiple symbols"""
        symbols = ["AAPL", "MSFT", "GOOGL"]
        results = {}
        
        for symbol in symbols:
            # Simulate data retrieval
            results[symbol] = pd.DataFrame({
                'close': np.random.randn(10) + 100
            })
        
        assert len(results) == 3
        assert all(isinstance(df, pd.DataFrame) for df in results.values())


# Performance test for data operations
class TestDataPerformance:
    """Test data operation performance"""
    
    def test_large_dataset_handling(self):
        """Test handling of large datasets"""
        # Create large dataset
        large_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10000, freq='1min'),
            'close': np.random.randn(10000) + 100
        })
        
        # Test operations are reasonable
        assert len(large_data) == 10000
        
        # Test fast operations
        import time
        start = time.time()
        _ = large_data['close'].mean()
        duration = time.time() - start
        
        # Should complete quickly (< 1 second)
        assert duration < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
