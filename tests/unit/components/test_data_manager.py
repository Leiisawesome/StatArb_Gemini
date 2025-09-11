#!/usr/bin/env python3
"""
Test Suite for Data Manager
===========================

Comprehensive test coverage for the unified data manager including:
- Data processing and validation
- Backtesting data provider functionality
- Real-time data streaming
- Data quality monitoring
- Multi-source data integration
- Error handling and edge cases

Author: Test Coverage Implementation - Phase 3
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum

# Import data manager classes
from core_structure.components.market_data.core.data_manager import (
    DataManager,
    DataStatus,
    ProcessingMode,
    DataQualityThresholds,
    DataStreamConfig,
    MarketDataConfig
)

# Mock external dependencies
try:
    from core_structure.infrastructure import (
        ClickHouseClient,
        MetricsCollector,
        MessageBus,
        ConfigManager
    )
    INFRASTRUCTURE_AVAILABLE = True
except ImportError:
    INFRASTRUCTURE_AVAILABLE = False
    ClickHouseClient = Mock()
    MetricsCollector = Mock()
    MessageBus = Mock()
    ConfigManager = Mock()


class TestDataStatus:
    """Test cases for DataStatus enum"""

    def test_data_status_values(self):
        """Test data status enum values"""
        assert DataStatus.VALID.value == "valid"
        assert DataStatus.STALE.value == "stale"
        assert DataStatus.INVALID.value == "invalid"
        assert DataStatus.MISSING.value == "missing"
        assert DataStatus.PROCESSING.value == "processing"


class TestProcessingMode:
    """Test cases for ProcessingMode enum"""

    def test_processing_mode_values(self):
        """Test processing mode enum values"""
        assert ProcessingMode.REALTIME.value == "realtime"
        assert ProcessingMode.BATCH.value == "batch"
        assert ProcessingMode.BACKTEST.value == "backtest"
        assert ProcessingMode.VALIDATION.value == "validation"


class TestDataQualityThresholds:
    """Test cases for DataQualityThresholds dataclass"""

    def test_default_thresholds(self):
        """Test default data quality thresholds"""
        thresholds = DataQualityThresholds()

        assert thresholds.max_price_change == 0.1
        assert thresholds.max_volume == 1000000
        assert thresholds.max_staleness == 300
        assert thresholds.min_data_points == 10
        assert thresholds.price_precision == 4
        assert thresholds.volume_precision == 0

    def test_custom_thresholds(self):
        """Test custom data quality thresholds"""
        thresholds = DataQualityThresholds(
            max_price_change=0.05,
            max_volume=500000,
            max_staleness=600,
            min_data_points=20,
            price_precision=6,
            volume_precision=2
        )

        assert thresholds.max_price_change == 0.05
        assert thresholds.max_volume == 500000
        assert thresholds.max_staleness == 600
        assert thresholds.min_data_points == 20
        assert thresholds.price_precision == 6
        assert thresholds.volume_precision == 2


class TestDataStreamConfig:
    """Test cases for DataStreamConfig dataclass"""

    def test_default_stream_config(self):
        """Test default data stream configuration"""
        config = DataStreamConfig(symbols=["AAPL", "GOOGL"])

        assert config.symbols == ["AAPL", "GOOGL"]
        assert config.interval == "1m"
        assert config.include_depth == False
        assert config.include_volume == True
        assert config.buffer_size == 1000
        assert config.reconnect_attempts == 3
        assert config.max_latency_ms == 100
        assert config.quality_checks == True

    def test_custom_stream_config(self):
        """Test custom data stream configuration"""
        config = DataStreamConfig(
            symbols=["AAPL", "GOOGL", "MSFT"],
            interval="5m",
            include_depth=True,
            include_volume=False,
            buffer_size=2000,
            reconnect_attempts=5,
            max_latency_ms=200,
            quality_checks=False
        )

        assert config.symbols == ["AAPL", "GOOGL", "MSFT"]
        assert config.interval == "5m"
        assert config.include_depth == True
        assert config.include_volume == False
        assert config.buffer_size == 2000
        assert config.reconnect_attempts == 5
        assert config.max_latency_ms == 200
        assert config.quality_checks == False


class TestMarketDataConfig:
    """Test cases for MarketDataConfig dataclass"""

    def test_default_market_data_config(self):
        """Test default market data configuration"""
        config = MarketDataConfig()

        assert config.cache_ttl_seconds == 300
        assert config.real_time_enabled == True
        assert config.max_symbols_per_query == 50
        assert config.default_lookback_days == 252
        assert config.processing_mode == ProcessingMode.REALTIME
        assert isinstance(config.quality_thresholds, DataQualityThresholds)
        assert config.stream_config is None
        assert config.enable_preprocessing == True
        assert config.enable_validation == True

    def test_custom_market_data_config(self):
        """Test custom market data configuration"""
        quality_thresholds = DataQualityThresholds(max_price_change=0.05)
        stream_config = DataStreamConfig(symbols=["AAPL"])

        config = MarketDataConfig(
            cache_ttl_seconds=600,
            real_time_enabled=False,
            max_symbols_per_query=100,
            default_lookback_days=500,
            processing_mode=ProcessingMode.BATCH,
            quality_thresholds=quality_thresholds,
            stream_config=stream_config,
            enable_preprocessing=False,
            enable_validation=False
        )

        assert config.cache_ttl_seconds == 600
        assert config.real_time_enabled == False
        assert config.max_symbols_per_query == 100
        assert config.default_lookback_days == 500
        assert config.processing_mode == ProcessingMode.BATCH
        assert config.quality_thresholds.max_price_change == 0.05
        assert config.stream_config.symbols == ["AAPL"]
        assert config.enable_preprocessing == False
        assert config.enable_validation == False


class TestDataManager:
    """Test cases for DataManager class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = MarketDataConfig()
        self.data_manager = DataManager(self.config)

        # Mock infrastructure components
        if not INFRASTRUCTURE_AVAILABLE:
            self.data_manager.clickhouse_client = Mock()
            self.data_manager.metrics_collector = Mock()
            self.data_manager.message_bus = Mock()
            self.data_manager.config_manager = Mock()

    def test_initialization(self):
        """Test data manager initialization"""
        assert self.data_manager.config == self.config
        assert isinstance(self.data_manager.data_cache, dict)
        assert len(self.data_manager.data_cache) == 0
        assert isinstance(self.data_manager.data_status, dict)
        assert len(self.data_manager.data_status) == 0

    def test_validate_data_quality_valid_data(self):
        """Test data quality validation with valid data"""
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(105, 115, 100),
            'low': np.random.uniform(95, 105, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })

        is_valid, issues = self.data_manager.validate_data_quality("AAPL", data)

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_data_quality_stale_data(self):
        """Test data quality validation with stale data"""
        # Create data that's too old
        old_timestamp = datetime.now() - timedelta(seconds=400)  # Older than max_staleness
        data = pd.DataFrame({
            'timestamp': [old_timestamp],
            'open': [100.0],
            'high': [105.0],
            'low': [95.0],
            'close': [102.0],
            'volume': [5000]
        })

        is_valid, issues = self.data_manager.validate_data_quality("AAPL", data)

        assert is_valid is False
        assert len(issues) > 0
        assert any("stale" in issue.lower() for issue in issues)

    def test_validate_data_quality_extreme_price_change(self):
        """Test data quality validation with extreme price changes"""
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=3, freq='1min'),
            'open': [100.0, 100.0, 100.0],
            'high': [105.0, 105.0, 105.0],
            'low': [95.0, 95.0, 95.0],
            'close': [100.0, 200.0, 100.0],  # 100% price change
            'volume': [5000, 5000, 5000]
        })

        is_valid, issues = self.data_manager.validate_data_quality("AAPL", data)

        assert is_valid is False
        assert len(issues) > 0

    def test_validate_data_quality_insufficient_data(self):
        """Test data quality validation with insufficient data points"""
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='1min'),  # Less than min_data_points
            'open': np.random.uniform(100, 110, 5),
            'high': np.random.uniform(105, 115, 5),
            'low': np.random.uniform(95, 105, 5),
            'close': np.random.uniform(100, 110, 5),
            'volume': np.random.randint(1000, 10000, 5)
        })

        is_valid, issues = self.data_manager.validate_data_quality("AAPL", data)

        assert is_valid is False
        assert len(issues) > 0

    def test_preprocess_data(self):
        """Test data preprocessing"""
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(105, 115, 100),
            'low': np.random.uniform(95, 105, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })

        processed_data = self.data_manager.preprocess_data("AAPL", data)

        assert isinstance(processed_data, pd.DataFrame)
        assert len(processed_data) == len(data)
        # Check that required columns exist
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            assert col in processed_data.columns

    def test_get_market_data_from_cache(self):
        """Test getting market data from cache"""
        symbol = "AAPL"
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1min'),
            'close': np.random.uniform(100, 110, 10),
            'volume': np.random.randint(1000, 10000, 10)
        })

        # Cache the data
        self.data_manager.data_cache[symbol] = data
        self.data_manager.data_status[symbol] = DataStatus.VALID

        retrieved_data = self.data_manager.get_market_data(symbol)

        assert retrieved_data is not None
        pd.testing.assert_frame_equal(retrieved_data, data)

    def test_get_market_data_cache_miss(self):
        """Test getting market data when not in cache"""
        symbol = "AAPL"

        # Mock the data fetching method
        with patch.object(self.data_manager, '_fetch_market_data', return_value=pd.DataFrame()) as mock_fetch:
            retrieved_data = self.data_manager.get_market_data(symbol)

            mock_fetch.assert_called_once_with(symbol)
            assert retrieved_data is not None

    def test_update_market_data(self):
        """Test updating market data"""
        symbol = "AAPL"
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1min'),
            'close': np.random.uniform(100, 110, 10),
            'volume': np.random.randint(1000, 10000, 10)
        })

        self.data_manager.update_market_data(symbol, data)

        assert symbol in self.data_manager.data_cache
        assert symbol in self.data_manager.data_status
        assert self.data_manager.data_status[symbol] == DataStatus.VALID

    def test_get_historical_data(self):
        """Test getting historical data"""
        symbol = "AAPL"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        # Mock historical data fetching
        mock_data = pd.DataFrame({
            'timestamp': pd.date_range(start_date, end_date, freq='1D'),
            'close': np.random.uniform(100, 110, 31),
            'volume': np.random.randint(1000, 10000, 31)
        })

        with patch.object(self.data_manager, '_fetch_historical_data', return_value=mock_data) as mock_fetch:
            data = self.data_manager.get_historical_data(symbol, start_date, end_date)

            mock_fetch.assert_called_once_with(symbol, start_date, end_date)
            assert isinstance(data, pd.DataFrame)
            assert len(data) > 0

    def test_get_real_time_data(self):
        """Test getting real-time data"""
        symbols = ["AAPL", "GOOGL"]

        # Mock real-time data fetching
        mock_data = {
            "AAPL": pd.DataFrame({
                'timestamp': [datetime.now()],
                'price': [150.0],
                'volume': [1000]
            }),
            "GOOGL": pd.DataFrame({
                'timestamp': [datetime.now()],
                'price': [2800.0],
                'volume': [500]
            })
        }

        with patch.object(self.data_manager, '_fetch_real_time_data', return_value=mock_data) as mock_fetch:
            data = self.data_manager.get_real_time_data(symbols)

            mock_fetch.assert_called_once_with(symbols)
            assert isinstance(data, dict)
            assert len(data) == 2
            assert "AAPL" in data
            assert "GOOGL" in data

    def test_aggregate_time_series(self):
        """Test time series aggregation"""
        # Create minute-level data
        timestamps = pd.date_range('2024-01-01 09:30:00', periods=60, freq='1min')
        data = pd.DataFrame({
            'timestamp': timestamps,
            'close': np.random.uniform(100, 110, 60),
            'volume': np.random.randint(100, 1000, 60)
        })

        # Aggregate to 5-minute bars
        aggregated = self.data_manager.aggregate_time_series(data, '5min')

        assert isinstance(aggregated, pd.DataFrame)
        assert len(aggregated) == 12  # 60 minutes / 5 minutes
        assert 'close' in aggregated.columns
        assert 'volume' in aggregated.columns

    def test_resample_data(self):
        """Test data resampling"""
        # Create irregular timestamp data
        timestamps = pd.to_datetime(['2024-01-01 09:30:00', '2024-01-01 09:31:15',
                                   '2024-01-01 09:32:30', '2024-01-01 09:33:45'])
        data = pd.DataFrame({
            'timestamp': timestamps,
            'close': [100.0, 101.0, 102.0, 103.0],
            'volume': [1000, 1100, 1200, 1300]
        })

        resampled = self.data_manager.resample_data(data, '1min')

        assert isinstance(resampled, pd.DataFrame)
        assert len(resampled) >= len(data)

    def test_merge_data_sources(self):
        """Test merging data from multiple sources"""
        source1 = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='1D'),
            'close': [100, 101, 102, 103, 104],
            'source': ['source1'] * 5
        })

        source2 = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='1D'),
            'close': [100.1, 101.1, 102.1, 103.1, 104.1],
            'source': ['source2'] * 5
        })

        merged = self.data_manager.merge_data_sources([source1, source2])

        assert isinstance(merged, pd.DataFrame)
        assert len(merged) == 5
        assert 'close' in merged.columns

    def test_calculate_technical_indicators(self):
        """Test technical indicator calculation"""
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50, freq='1D'),
            'close': np.random.uniform(100, 110, 50),
            'high': np.random.uniform(105, 115, 50),
            'low': np.random.uniform(95, 105, 50),
            'volume': np.random.randint(1000, 10000, 50)
        })

        indicators = ['SMA_20', 'RSI', 'MACD']

        data_with_indicators = self.data_manager.calculate_technical_indicators(data, indicators)

        assert isinstance(data_with_indicators, pd.DataFrame)
        assert len(data_with_indicators) == len(data)
        # Check that some indicators were added
        assert len(data_with_indicators.columns) >= len(data.columns)

    def test_detect_data_anomalies(self):
        """Test data anomaly detection"""
        # Create data with an anomaly
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1D'),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })
        # Add an anomaly
        data.loc[50, 'close'] = 500.0  # Extreme price

        anomalies = self.data_manager.detect_data_anomalies(data)

        assert isinstance(anomalies, list)
        assert len(anomalies) > 0  # Should detect the anomaly

    def test_get_data_quality_report(self):
        """Test data quality report generation"""
        symbol = "AAPL"
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1D'),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })

        self.data_manager.update_market_data(symbol, data)

        report = self.data_manager.get_data_quality_report(symbol)

        assert isinstance(report, dict)
        assert 'symbol' in report
        assert 'status' in report
        assert 'issues' in report
        assert 'metrics' in report

    def test_clear_cache(self):
        """Test cache clearing"""
        # Add some data to cache
        self.data_manager.data_cache["AAPL"] = pd.DataFrame()
        self.data_manager.data_status["AAPL"] = DataStatus.VALID

        assert len(self.data_manager.data_cache) > 0

        self.data_manager.clear_cache()

        assert len(self.data_manager.data_cache) == 0
        assert len(self.data_manager.data_status) == 0

    def test_get_cache_info(self):
        """Test cache information retrieval"""
        # Add some data to cache
        self.data_manager.data_cache["AAPL"] = pd.DataFrame({'close': [100, 101, 102]})
        self.data_manager.data_status["AAPL"] = DataStatus.VALID

        cache_info = self.data_manager.get_cache_info()

        assert isinstance(cache_info, dict)
        assert 'total_symbols' in cache_info
        assert 'cache_size_mb' in cache_info
        assert cache_info['total_symbols'] == 1


class TestDataManagerIntegration:
    """Integration tests for data manager"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = MarketDataConfig()
        self.data_manager = DataManager(self.config)

    def test_end_to_end_data_pipeline(self):
        """Test end-to-end data pipeline"""
        symbol = "AAPL"

        # 1. Fetch data
        with patch.object(self.data_manager, '_fetch_market_data') as mock_fetch:
            mock_data = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
                'open': np.random.uniform(100, 110, 100),
                'high': np.random.uniform(105, 115, 100),
                'low': np.random.uniform(95, 105, 100),
                'close': np.random.uniform(100, 110, 100),
                'volume': np.random.randint(1000, 10000, 100)
            })
            mock_fetch.return_value = mock_data

            data = self.data_manager.get_market_data(symbol)

            assert isinstance(data, pd.DataFrame)
            assert len(data) == 100

        # 2. Process data
        processed_data = self.data_manager.preprocess_data(symbol, data)

        assert isinstance(processed_data, pd.DataFrame)
        assert len(processed_data) == len(data)

        # 3. Validate data
        is_valid, issues = self.data_manager.validate_data_quality(symbol, processed_data)

        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)

    def test_multi_symbol_data_handling(self):
        """Test handling multiple symbols"""
        symbols = ["AAPL", "GOOGL", "MSFT"]

        # Mock data for each symbol
        mock_data = {}
        for symbol in symbols:
            mock_data[symbol] = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=50, freq='1D'),
                'close': np.random.uniform(100, 200, 50),
                'volume': np.random.randint(1000, 10000, 50)
            })

        with patch.object(self.data_manager, '_fetch_real_time_data', return_value=mock_data):
            data = self.data_manager.get_real_time_data(symbols)

            assert isinstance(data, dict)
            assert len(data) == 3
            for symbol in symbols:
                assert symbol in data
                assert isinstance(data[symbol], pd.DataFrame)

    def test_data_transformation_pipeline(self):
        """Test data transformation pipeline"""
        # Create raw data
        raw_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(105, 115, 100),
            'low': np.random.uniform(95, 105, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })

        # Apply transformations
        # 1. Preprocessing
        processed = self.data_manager.preprocess_data("TEST", raw_data)

        # 2. Technical indicators
        with_indicators = self.data_manager.calculate_technical_indicators(
            processed, ['SMA_20', 'RSI']
        )

        # 3. Aggregation
        aggregated = self.data_manager.aggregate_time_series(with_indicators, '5min')

        assert isinstance(aggregated, pd.DataFrame)
        assert len(aggregated) < len(raw_data)  # Should be aggregated

    def test_error_handling_and_recovery(self):
        """Test error handling and recovery"""
        symbol = "AAPL"

        # Test with invalid data fetch
        with patch.object(self.data_manager, '_fetch_market_data', side_effect=Exception("Network error")):
            data = self.data_manager.get_market_data(symbol)

            # Should handle error gracefully
            assert data is not None  # Could be empty DataFrame or cached data

    def test_performance_under_load(self):
        """Test performance under load"""
        symbols = [f"STOCK_{i:03d}" for i in range(100)]

        # Mock bulk data fetch
        mock_data = {}
        for symbol in symbols:
            mock_data[symbol] = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=10, freq='1D'),
                'close': np.random.uniform(100, 110, 10),
                'volume': np.random.randint(1000, 10000, 10)
            })

        with patch.object(self.data_manager, '_fetch_real_time_data', return_value=mock_data):
            import time
            start_time = time.time()

            data = self.data_manager.get_real_time_data(symbols)

            end_time = time.time()
            duration = end_time - start_time

            assert isinstance(data, dict)
            assert len(data) == 100
            assert duration < 5.0  # Should complete within 5 seconds


class TestDataManagerEdgeCases:
    """Test edge cases for data manager"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = MarketDataConfig()
        self.data_manager = DataManager(self.config)

    def test_empty_data_handling(self):
        """Test handling of empty data"""
        empty_data = pd.DataFrame()

        # Should handle empty data gracefully
        is_valid, issues = self.data_manager.validate_data_quality("EMPTY", empty_data)

        assert is_valid is False
        assert len(issues) > 0

    def test_single_row_data(self):
        """Test handling of single row data"""
        single_row_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'close': [100.0],
            'volume': [1000]
        })

        is_valid, issues = self.data_manager.validate_data_quality("SINGLE", single_row_data)

        # May or may not be valid depending on thresholds
        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)

    def test_extreme_values_handling(self):
        """Test handling of extreme values"""
        extreme_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1D'),
            'close': [100, 1e10, 200, 1e-10, 150, 300, 1e15, 175, 400, 125],  # Extreme values
            'volume': [1000, 1e12, 2000, 1, 1500, 3000, 1e10, 1750, 4000, 1250]
        })

        is_valid, issues = self.data_manager.validate_data_quality("EXTREME", extreme_data)

        # Should detect anomalies
        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)

    def test_missing_columns_handling(self):
        """Test handling of missing columns"""
        missing_columns_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1D'),
            'close': np.random.uniform(100, 110, 10)
            # Missing volume and other required columns
        })

        processed = self.data_manager.preprocess_data("MISSING", missing_columns_data)

        # Should handle missing columns gracefully
        assert isinstance(processed, pd.DataFrame)

    def test_nan_values_handling(self):
        """Test handling of NaN values"""
        nan_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1D'),
            'close': [100, np.nan, 102, np.nan, 104, 105, np.nan, 107, 108, 109],
            'volume': [1000, 1100, np.nan, 1300, 1400, np.nan, 1600, 1700, 1800, 1900]
        })

        processed = self.data_manager.preprocess_data("NAN", nan_data)

        # Should handle NaN values
        assert isinstance(processed, pd.DataFrame)
        assert len(processed) == len(nan_data)

    def test_duplicate_timestamps_handling(self):
        """Test handling of duplicate timestamps"""
        duplicate_data = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 1), datetime(2024, 1, 1), datetime(2024, 1, 2)],
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })

        processed = self.data_manager.preprocess_data("DUPLICATE", duplicate_data)

        # Should handle duplicates
        assert isinstance(processed, pd.DataFrame)

    def test_unsorted_timestamps_handling(self):
        """Test handling of unsorted timestamps"""
        unsorted_data = pd.DataFrame({
            'timestamp': [datetime(2024, 1, 3), datetime(2024, 1, 1), datetime(2024, 1, 2)],
            'close': [103, 101, 102],
            'volume': [1300, 1100, 1200]
        })

        processed = self.data_manager.preprocess_data("UNSORTED", unsorted_data)

        # Should sort timestamps
        assert isinstance(processed, pd.DataFrame)
        if len(processed) > 1:
            assert processed['timestamp'].is_monotonic_increasing

    def test_very_large_dataset_handling(self):
        """Test handling of very large datasets"""
        # Create a large dataset
        large_data = pd.DataFrame({
            'timestamp': pd.date_range('2020-01-01', periods=100000, freq='1min'),
            'close': np.random.uniform(100, 110, 100000),
            'volume': np.random.randint(1000, 10000, 100000)
        })

        processed = self.data_manager.preprocess_data("LARGE", large_data)

        # Should handle large datasets
        assert isinstance(processed, pd.DataFrame)
        assert len(processed) == len(large_data)

    def test_concurrent_data_access(self):
        """Test concurrent data access"""
        import threading
        import time

        results = []

        def access_data(symbol):
            data = self.data_manager.get_market_data(symbol)
            results.append(data is not None)

        # Create multiple threads accessing data concurrently
        symbols = [f"CONCURRENT_{i}" for i in range(20)]
        threads = []

        for symbol in symbols:
            thread = threading.Thread(target=access_data, args=(symbol,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All should complete successfully
        assert len(results) == 20
        assert all(results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
