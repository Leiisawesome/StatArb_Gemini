"""
Test suite for market data components
"""
import pytest
import pandas as pd
from typing import Dict
from datetime import datetime, timedelta

try:
    import clickhouse_driver
except ImportError:
    clickhouse_driver = None

from tests.utils.test_helpers import (
    PerformanceMonitor,
    performance_test,
    DataValidation,
    generate_test_data
)

class TestMarketDataFeeds:
    """Test suite for market data feed components"""
    
    @pytest.fixture(scope="class")
    def market_data_feed(self, test_config):
        """Initialize market data feed for testing"""
        from enhanced_pair_backtester.data.market_data_feeds import MarketDataFeed
        return MarketDataFeed(
            symbols=test_config["market_data"]["test_symbols"],
            config=test_config
        )
    
    @pytest.mark.integration
    def test_data_feed_initialization(self, market_data_feed, test_config):
        """Test market data feed initialization"""
        assert market_data_feed is not None
        assert hasattr(market_data_feed, 'fetch_data')
    
    @performance_test(latency_threshold_ms=200)
    def test_data_fetch_performance(self, market_data_feed, test_config):
        """Test market data fetch performance"""
        symbols = test_config["market_data"]["test_symbols"]
        timeframe = test_config["market_data"]["test_timeframe"]
        
        monitor = PerformanceMonitor()
        with monitor:
            data = market_data_feed.fetch_data(symbols, timeframe)
        
        # Validate data structure
        assert DataValidation.validate_market_data(data)
        
        # Check performance metrics
        stats = monitor.get_statistics()
        assert stats['latency']['mean'] < 200, "Data fetch latency too high"
        assert stats['memory']['mean'] < 100, "Memory usage too high"
    
    @pytest.mark.integration
    def test_real_time_updates(self, market_data_feed):
        """Test real-time market data updates"""
        def callback(update):
            assert 'symbol' in update
            assert 'price' in update
            assert 'timestamp' in update
        
        market_data_feed.subscribe_updates(callback)
        # Wait for some updates
        import time
        time.sleep(1)
        market_data_feed.unsubscribe_updates(callback)

class TestDataProcessor:
    """Test suite for data processing components"""
    
    @pytest.fixture(scope="class")
    def data_processor(self, test_config):
        """Initialize data processor for testing"""
        from enhanced_pair_backtester.data.data_processor import DataProcessor
        return DataProcessor(config=test_config)
    
    @pytest.mark.integration
    def test_data_cleaning(self, data_processor):
        """Test data cleaning functionality"""
        # Generate test data with some anomalies
        raw_data = generate_test_data()
        raw_data['TEST1'].loc[raw_data['TEST1'].index[0], 'close'] = float('nan')
        
        cleaned_data = data_processor.clean_data(raw_data)
        assert not cleaned_data['TEST1'].isnull().any().any()
    
    @performance_test(latency_threshold_ms=100)
    def test_feature_engineering(self, data_processor):
        """Test feature engineering performance"""
        raw_data = generate_test_data()
        
        monitor = PerformanceMonitor()
        with monitor:
            processed_data = data_processor.engineer_features(raw_data)
        
        # Validate processed data
        assert 'returns' in processed_data['TEST1'].columns
        assert 'volatility' in processed_data['TEST1'].columns
        
        # Check performance
        stats = monitor.get_statistics()
        assert stats['latency']['mean'] < 100, "Feature engineering latency too high"

@pytest.mark.skipif(clickhouse_driver is None, reason="clickhouse_driver not installed")
class TestClickHouseIntegration:
    """Test suite for ClickHouse integration"""
    
    @pytest.fixture(scope="class")
    def clickhouse_client(self, test_config):
        """Initialize ClickHouse client for testing"""
        client = clickhouse_driver.Client(
            host=test_config["clickhouse"]["host"],
            database=test_config["clickhouse"]["database"]
        )
        return client
    
    @pytest.mark.integration
    def test_database_connection(self, clickhouse_client):
        """Test ClickHouse database connection"""
        result = clickhouse_client.execute("SELECT 1")
        assert result == [(1,)]
    
    @performance_test(latency_threshold_ms=500)
    def test_data_insertion(self, clickhouse_client):
        """Test data insertion performance"""
        test_data = generate_test_data(n_days=10)
        
        monitor = PerformanceMonitor()
        with monitor:
            for symbol, df in test_data.items():
                data = df.reset_index().to_dict('records')
                clickhouse_client.execute(
                    "INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume) VALUES",
                    data
                )
        
        # Verify insertion
        result = clickhouse_client.execute(
            "SELECT COUNT(*) FROM market_data WHERE symbol = 'TEST1'"
        )
        assert result[0][0] == len(test_data['TEST1'])
    
    @pytest.mark.integration
    def test_query_performance(self, clickhouse_client):
        """Test query performance"""
        monitor = PerformanceMonitor()
        with monitor:
            result = clickhouse_client.execute("""
                SELECT 
                    symbol,
                    toStartOfDay(timestamp) as date,
                    argMax(close, timestamp) as close
                FROM market_data
                WHERE symbol IN ('TEST1', 'TEST2')
                GROUP BY symbol, date
                ORDER BY symbol, date
            """)
        
        stats = monitor.get_statistics()
        assert stats['latency']['mean'] < 1000, "Query latency too high"

def test_end_to_end_data_flow(test_config):
    """End-to-end test for market data flow"""
    from enhanced_pair_backtester.data.market_data_feeds import MarketDataFeed
    from enhanced_pair_backtester.data.data_processor import DataProcessor
    
    # Initialize components
    feed = MarketDataFeed(
        symbols=test_config["market_data"]["test_symbols"],
        config=test_config
    )
    processor = DataProcessor(config=test_config)
    
    # Test data flow
    raw_data = feed.fetch_data(['TEST1', 'TEST2'], '1d')
    assert DataValidation.validate_market_data(raw_data)
    
    processed_data = processor.process_data(raw_data)
    assert 'returns' in processed_data['TEST1'].columns
    assert 'volatility' in processed_data['TEST1'].columns
    
    # Validate final output
    for symbol, df in processed_data.items():
        assert not df.isnull().any().any()
        assert (df['high'] >= df['low']).all()
        assert (df['volume'] >= 0).all() 