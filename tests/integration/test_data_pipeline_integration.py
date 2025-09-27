#!/usr/bin/env python3
"""
Data Pipeline Integration Tests
===============================

Comprehensive integration tests for the data pipeline components:
- DataManager ↔ DataProvider integration
- Data validation and processing workflows
- ClickHouse integration and data persistence
- Real-time data streaming and subscription patterns
- Data quality monitoring and error handling

These tests validate end-to-end data flow from external sources through
processing pipelines to storage and consumption by trading components.

Author: StatArb_Gemini Integration Test Suite
Version: 1.0.0
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os
import warnings

warnings.filterwarnings('ignore')

from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import FeatureEngineer
from core_engine.type_definitions.data import MarketData, DataConfig, DataProvider


class TestDataPipelineIntegration:
    """Integration tests for complete data pipeline workflows"""

    @pytest.fixture
    def clickhouse_config(self):
        """Create ClickHouse configuration for testing"""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        return ClickHouseDataConfig(
            symbols=["AAPL", "MSFT", "NVDA"],
            start_date=yesterday,
            end_date=today,
            interval="1min",
            clickhouse_host="localhost",
            clickhouse_port=8123,
            clickhouse_database="test_db",
            enable_caching=False,
            cache_ttl=300
        )

    @pytest.fixture
    def mock_data_provider(self):
        """Create mock data provider for testing"""
        provider = Mock(spec=DataProvider)

        # Mock market data generation
        async def mock_get_historical_data(symbol: str, start_date: datetime, end_date: datetime):
            dates = pd.date_range(start_date, end_date, freq='1min')
            np.random.seed(42)

            # Generate realistic OHLCV data
            base_price = 100.0
            returns = np.random.normal(0.0001, 0.01, len(dates))
            prices = base_price * np.exp(np.cumsum(returns))

            data = pd.DataFrame({
                'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
                'high': prices * (1 + np.random.normal(0.001, 0.003, len(dates))),
                'low': prices * (1 + np.random.normal(-0.003, 0.001, len(dates))),
                'close': prices,
                'volume': np.random.uniform(1000, 10000, len(dates)),
                'timestamp': dates
            })
            data.set_index('timestamp', inplace=True)
            return data

        provider.get_historical_data = AsyncMock(side_effect=mock_get_historical_data)
        provider.get_real_time_data = AsyncMock()
        provider.subscribe_symbol = AsyncMock(return_value=True)
        provider.unsubscribe_symbol = AsyncMock(return_value=True)

        return provider

    @pytest.fixture
    def data_manager(self, clickhouse_config, mock_data_provider):
        """Create DataManager instance for testing"""
        manager = ClickHouseDataManager(clickhouse_config)
        manager.data_provider = mock_data_provider
        return manager

    @pytest.mark.asyncio
    async def test_data_loading_and_validation_pipeline(self, data_manager, mock_data_provider):
        """Test complete data loading and validation pipeline"""
        symbol = "AAPL"
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        # Load data through the pipeline
        data = data_manager.get_historical_data(symbol, start_date, end_date)

        # Verify data was returned and has expected structure
        assert isinstance(data, pd.DataFrame)
        assert not data.empty
        assert all(col in data.columns for col in ['open', 'high', 'low', 'close', 'volume'])

        # Verify data contains the requested symbol
        if 'symbol' in data.columns:
            assert symbol in data['symbol'].values

        # Validate data structure
        assert isinstance(data, pd.DataFrame)
        assert not data.empty
        assert all(col in data.columns for col in ['open', 'high', 'low', 'close', 'volume'])

        # Validate data quality
        assert data['close'].notna().all()
        assert (data['high'] >= data['close']).all()
        assert (data['low'] <= data['close']).all()
        assert (data['volume'] > 0).all()

    @pytest.mark.asyncio
    async def test_data_processing_pipeline_integration(self, data_manager):
        """Test data processing pipeline with indicators and features"""
        # Generate test data
        symbol = "TSLA"
        dates = pd.date_range('2023-01-01', periods=100, freq='h')
        np.random.seed(42)

        base_price = 200.0
        returns = np.random.normal(0.0002, 0.02, len(dates))
        prices = base_price * np.exp(np.cumsum(returns))

        market_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.005, len(dates))),
            'high': prices * (1 + np.random.normal(0.002, 0.008, len(dates))),
            'low': prices * (1 + np.random.normal(-0.008, 0.002, len(dates))),
            'close': prices,
            'volume': np.random.uniform(10000, 100000, len(dates)),
            'symbol': symbol
        })

        # Process through indicators engine
        indicators_engine = EnhancedTechnicalIndicators()
        processed_data = indicators_engine.calculate_all_indicators(market_data)

        # Verify indicators were added (check that some indicators are present)
        indicator_columns = [col for col in processed_data.columns if col not in market_data.columns]
        assert len(indicator_columns) > 0, "No indicator columns were added"

        # Check for some common indicators that should be present with 100 data points
        common_indicators = ['sma_20', 'ema_9', 'rsi', 'macd', 'bb_upper']
        found_indicators = [ind for ind in common_indicators if ind in processed_data.columns]
        assert len(found_indicators) > 0, f"No expected indicators found. Available: {indicator_columns}"

        # Process through feature engineering
        feature_engineer = FeatureEngineer()
        features = feature_engineer.create_features(processed_data)

        # Verify features were created
        assert len(features) > 0
        assert isinstance(features, pd.DataFrame)

        # Verify data integrity maintained
        assert len(processed_data) == len(features)
        assert processed_data.index.equals(features.index)

    @pytest.mark.asyncio
    async def test_real_time_data_subscription_workflow(self, data_manager):
        """Test real-time data subscription and streaming workflow"""
        symbol = "GOOGL"

        # Create a mock subscriber
        mock_subscriber = Mock()
        mock_subscriber.on_market_data = AsyncMock()

        # Subscribe to real-time data using the subscriber pattern
        data_manager.add_subscriber(mock_subscriber)
        assert mock_subscriber in data_manager.subscribers

        # Simulate receiving real-time data by calling get_market_data
        market_data = data_manager.get_market_data(symbol)

        # Verify data was retrieved
        assert market_data is not None
        assert isinstance(market_data, pd.DataFrame)
        assert not market_data.empty

        # Remove subscriber
        data_manager.remove_subscriber(mock_subscriber)
        assert mock_subscriber not in data_manager.subscribers

    @pytest.mark.asyncio
    async def test_data_quality_monitoring_integration(self, data_manager):
        """Test data quality monitoring and validation integration"""
        # Create test data with quality issues
        dates = pd.date_range('2023-01-01', periods=50, freq='h')

        # Data with missing values and outliers
        data_with_issues = pd.DataFrame({
            'timestamp': dates,
            'symbol': ['TEST'] * 50,
            'open': [100.0] * 25 + [np.nan] * 25,  # Missing values
            'high': [105.0] * 24 + [1000.0] + [105.0] * 25,  # Outlier
            'low': [95.0] * 50,
            'close': [102.0] * 50,
            'volume': [10000] * 50
        })

        # Process through data quality checks using validate_data method
        quality_report = data_manager.validate_data(data_with_issues)

        # Verify quality issues were detected
        assert isinstance(quality_report, dict)
        assert 'valid' in quality_report
        assert 'score' in quality_report
        assert 'issues' in quality_report
        assert 'metrics' in quality_report

        # Verify missing values detected (should have null values and reduced score)
        assert quality_report['score'] < 1.0  # Score should be reduced due to null values
        assert len(quality_report['issues']) > 0  # Should have detected issues
        assert 'null values' in ' '.join(quality_report['issues'])  # Should mention null values

    @pytest.mark.asyncio
    async def test_data_persistence_and_retrieval_integration(self, data_manager):
        """Test data caching and retrieval functionality"""
        symbol = "MSFT"

        # Load data (which gets cached)
        market_data = data_manager.get_market_data(symbol)
        assert market_data is not None

        # Check cache stats
        cache_stats = data_manager.get_cache_stats()
        assert isinstance(cache_stats, dict)
        assert 'cache_size' in cache_stats
        assert cache_stats['cache_size'] > 0  # Should have cached data

        # Load same data again (should use cache)
        market_data_cached = data_manager.get_market_data(symbol)
        assert market_data_cached is not None

        # Verify cache stats updated
        cache_stats_after = data_manager.get_cache_stats()
        assert cache_stats_after['cache_size'] >= cache_stats['cache_size']

        # Clear cache
        data_manager.clear_cache()
        cache_stats_cleared = data_manager.get_cache_stats()
        assert cache_stats_cleared['cache_size'] == 0
        # In real implementation, would verify data integrity

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_integration(self, data_manager):
        """Test error handling and recovery in data pipeline"""
        # Test validation with empty DataFrame
        empty_df = pd.DataFrame()
        validation_result = data_manager.validate_data(empty_df)

        # Verify error handling for empty data
        assert isinstance(validation_result, dict)
        assert not validation_result['valid']
        assert validation_result['score'] == 0.0
        assert 'Empty dataset' in validation_result['issues']

        # Test validation with malformed data (invalid price relationships)
        malformed_df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'symbol': ['TEST'],
            'open': [100.0],
            'high': [90.0],  # High < close, invalid relationship
            'low': [95.0],
            'close': [102.0],  # Close > high, invalid
            'volume': [-1000]  # Negative volume
        })

        validation_result_malformed = data_manager.validate_data(malformed_df)

        # Verify error handling for malformed data
        assert isinstance(validation_result_malformed, dict)
        assert validation_result_malformed['score'] < 1.0  # Should have reduced score
        assert len(validation_result_malformed['issues']) > 0  # Should detect issues

    @pytest.mark.asyncio
    async def test_concurrent_data_loading_integration(self, data_manager):
        """Test concurrent data loading for multiple symbols"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]

        # Load data concurrently for multiple symbols
        import asyncio
        tasks = [
            asyncio.to_thread(data_manager.get_market_data, symbol)
            for symbol in symbols
        ]

        results = await asyncio.gather(*tasks)

        # Verify all requests completed
        assert len(results) == len(symbols)
        for i, result in enumerate(results):
            assert result is not None
            assert isinstance(result, pd.DataFrame)
            # Note: Results might be empty due to synthetic data generation, but structure should be correct
