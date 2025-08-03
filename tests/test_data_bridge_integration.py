"""
Test suite for DataBridge integration

This module tests the DataBridge functionality including:
- Data retrieval from production and backtesting sources
- Data quality monitoring and reporting
- Data consistency validation
- Regime detection integration
- Performance optimization
- Error handling and recovery
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import logging

from core_structure.market_data.data_bridge import (
    DataBridge, DataBridgeConfig, DataMode, DataQualityLevel,
    DataBridgeResult, DataQualityReport, DataConsistencyReport,
    create_data_bridge, get_data_for_backtesting
)


class MockDataManager:
    """Mock DataManager for testing"""
    
    def __init__(self):
        self.mock_data = self._create_mock_data()
    
    def _create_mock_data(self):
        """Create mock market data"""
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        data = {
            'timestamp': dates,
            'open': np.random.uniform(100, 200, len(dates)),
            'high': np.random.uniform(150, 250, len(dates)),
            'low': np.random.uniform(50, 150, len(dates)),
            'close': np.random.uniform(100, 200, len(dates)),
            'volume': np.random.uniform(1000000, 5000000, len(dates))
        }
        return pd.DataFrame(data)
    
    async def get_market_data(self, symbol, start_time=None, end_time=None, data_type="ohlcv"):
        """Mock market data retrieval"""
        return self.mock_data.copy()
    
    async def get_historical_data(self, symbol, start_time=None, end_time=None, data_type="ohlcv"):
        """Mock historical data retrieval"""
        return self.mock_data.copy()


class MockDataProcessor:
    """Mock DataProcessor for testing"""
    
    def __init__(self):
        pass
    
    async def process_data(self, data):
        """Mock data processing"""
        return data


class MockDataQualityMonitor:
    """Mock DataQualityMonitor for testing"""
    
    def __init__(self):
        pass
    
    async def check_quality(self, data):
        """Mock quality check"""
        return {
            'quality_score': 0.85,
            'issues': [],
            'recommendations': []
        }


class MockMarketDataAnalytics:
    """Mock MarketDataAnalytics for testing"""
    
    def __init__(self):
        pass
    
    async def analyze_data(self, data):
        """Mock data analysis"""
        return {
            'analysis_score': 0.9,
            'insights': []
        }


class MockPerformanceIntegration:
    """Mock PerformanceIntegration for testing"""
    
    def __init__(self):
        pass
    
    async def track_performance(self, metrics):
        """Mock performance tracking"""
        return True


class TestDataBridgeInitialization:
    """Test DataBridge initialization and configuration"""
    
    def test_default_initialization(self):
        """Test DataBridge initialization with default config"""
        bridge = DataBridge()
        assert bridge.config.data_mode == DataMode.BACKTESTING
        assert bridge.config.enable_data_quality_monitoring is True
        assert bridge.config.enable_regime_detection is True
        assert bridge.config.enable_performance_tracking is True
    
    def test_custom_initialization(self):
        """Test DataBridge initialization with custom config"""
        config = DataBridgeConfig(
            data_mode=DataMode.PRODUCTION,
            enable_data_quality_monitoring=False,
            min_data_quality_score=0.8
        )
        bridge = DataBridge(config)
        assert bridge.config.data_mode == DataMode.PRODUCTION
        assert bridge.config.enable_data_quality_monitoring is False
        assert bridge.config.min_data_quality_score == 0.8
    
    @patch('core_structure.market_data.data_bridge.DataManager')
    @patch('core_structure.market_data.data_bridge.DataProcessor')
    def test_component_initialization(self, mock_processor, mock_manager):
        """Test core component initialization"""
        mock_manager.return_value = MockDataManager()
        mock_processor.return_value = MockDataProcessor()
        
        bridge = DataBridge()
        assert hasattr(bridge, 'data_manager')
        assert hasattr(bridge, 'data_processor')
    
    def test_factory_function(self):
        """Test create_data_bridge factory function"""
        config = DataBridgeConfig(data_mode=DataMode.SIMULATION)
        bridge = create_data_bridge(config)
        assert isinstance(bridge, DataBridge)
        assert bridge.config.data_mode == DataMode.SIMULATION


class TestDataBridgeDataRetrieval:
    """Test DataBridge data retrieval functionality"""
    
    @pytest.fixture
    def bridge(self):
        """Create DataBridge instance for testing"""
        with patch('core_structure.market_data.data_bridge.DataManager', return_value=MockDataManager()), \
             patch('core_structure.market_data.data_bridge.DataProcessor', return_value=MockDataProcessor()), \
             patch('core_structure.market_data.data_bridge.DataQualityMonitor', return_value=MockDataQualityMonitor()), \
             patch('core_structure.market_data.data_bridge.MarketDataAnalytics', return_value=MockMarketDataAnalytics()), \
             patch('core_structure.market_data.data_bridge.PerformanceIntegration', return_value=MockPerformanceIntegration()):
            return DataBridge()
    
    @pytest.mark.asyncio
    async def test_get_market_data_backtesting(self, bridge):
        """Test market data retrieval in backtesting mode"""
        result = await bridge.get_market_data("AAPL", data_type="ohlcv")
        
        assert isinstance(result, DataBridgeResult)
        assert result.symbol == "AAPL"
        assert result.data_type == "ohlcv"
        assert isinstance(result.data, pd.DataFrame)
        assert result.source == "backtesting"
        assert result.quality_score > 0
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_get_market_data_production(self, bridge):
        """Test market data retrieval in production mode"""
        bridge.config.data_mode = DataMode.PRODUCTION
        result = await bridge.get_market_data("AAPL", data_type="ohlcv")
        
        assert isinstance(result, DataBridgeResult)
        assert result.symbol == "AAPL"
        assert result.source == "production"
        assert isinstance(result.data, pd.DataFrame)
    
    @pytest.mark.asyncio
    async def test_get_market_data_with_timestamps(self, bridge):
        """Test market data retrieval with specific timestamps"""
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 15)
        
        result = await bridge.get_market_data(
            "AAPL",
            start_time=start_time,
            end_time=end_time,
            data_type="ohlcv"
        )
        
        assert isinstance(result, DataBridgeResult)
        assert result.data_type == "ohlcv"
        assert isinstance(result.data, pd.DataFrame)
    
    @pytest.mark.asyncio
    async def test_get_market_data_caching(self, bridge):
        """Test market data caching functionality"""
        # First request
        result1 = await bridge.get_market_data("AAPL")
        
        # Second request (should be cached)
        result2 = await bridge.get_market_data("AAPL")
        
        assert result1.symbol == result2.symbol
        assert result1.data_type == result2.data_type
        # Second request should be faster due to caching
        assert result2.processing_time_ms < result1.processing_time_ms
    
    @pytest.mark.asyncio
    async def test_get_market_data_error_handling(self, bridge):
        """Test error handling in market data retrieval"""
        # Mock data manager to raise exception
        bridge.data_manager.get_market_data = AsyncMock(side_effect=Exception("Data source error"))
        
        result = await bridge.get_market_data("INVALID_SYMBOL")
        
        assert isinstance(result, DataBridgeResult)
        assert result.error_message is not None
        assert result.quality_score == 0.0
        assert result.source == "fallback"


class TestDataBridgeQualityMonitoring:
    """Test DataBridge data quality monitoring functionality"""
    
    @pytest.fixture
    def bridge(self):
        """Create DataBridge instance for testing"""
        with patch('core_structure.market_data.data_bridge.DataManager', return_value=MockDataManager()), \
             patch('core_structure.market_data.data_bridge.DataProcessor', return_value=MockDataProcessor()), \
             patch('core_structure.market_data.data_bridge.DataQualityMonitor', return_value=MockDataQualityMonitor()), \
             patch('core_structure.market_data.data_bridge.MarketDataAnalytics', return_value=MockMarketDataAnalytics()), \
             patch('core_structure.market_data.data_bridge.PerformanceIntegration', return_value=MockPerformanceIntegration()):
            return DataBridge()
    
    @pytest.mark.asyncio
    async def test_get_data_quality_report(self, bridge):
        """Test data quality report generation"""
        result = await bridge.get_data_quality_report("AAPL")
        
        assert isinstance(result, DataQualityReport)
        assert result.overall_quality_score > 0
        assert result.completeness_score > 0
        assert result.accuracy_score > 0
        assert result.consistency_score > 0
        assert result.timeliness_score > 0
        assert isinstance(result.quality_level, DataQualityLevel)
        assert isinstance(result.issues, list)
        assert isinstance(result.recommendations, list)
    
    @pytest.mark.asyncio
    async def test_get_data_quality_report_disabled(self, bridge):
        """Test data quality report when monitoring is disabled"""
        bridge.config.enable_data_quality_monitoring = False
        
        with pytest.raises(ValueError, match="Data quality monitoring is disabled"):
            await bridge.get_data_quality_report("AAPL")
    
    def test_calculate_completeness(self, bridge):
        """Test completeness calculation"""
        # Create test data with missing values
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10),
            'close': [100, 101, np.nan, 103, 104, 105, np.nan, 107, 108, 109],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        })
        
        completeness = bridge._calculate_completeness(data)
        assert 0 <= completeness <= 1
        assert completeness < 1.0  # Should be less than 1 due to missing values
    
    def test_calculate_accuracy(self, bridge):
        """Test accuracy calculation"""
        # Create test data with some issues
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10),
            'close': [100, 101, -1, 103, 104, 105, 1000, 107, 108, 109],  # Negative and outlier
            'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        })
        
        accuracy = bridge._calculate_accuracy(data)
        assert 0 <= accuracy <= 1
        assert accuracy < 1.0  # Should be less than 1 due to data issues
    
    def test_calculate_consistency(self, bridge):
        """Test consistency calculation"""
        # Create test data with irregular intervals
        timestamps = pd.date_range('2024-01-01', periods=10, freq='D')
        timestamps[5] = timestamps[5] + timedelta(hours=2)  # Irregular interval
        
        data = pd.DataFrame({
            'timestamp': timestamps,
            'close': np.random.uniform(100, 200, 10),
            'volume': np.random.uniform(1000, 2000, 10)
        })
        
        consistency = bridge._calculate_consistency(data)
        assert 0 <= consistency <= 1
    
    def test_calculate_timeliness(self, bridge):
        """Test timeliness calculation"""
        # Create test data with old timestamps
        old_timestamps = pd.date_range('2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'timestamp': old_timestamps,
            'close': np.random.uniform(100, 200, 10),
            'volume': np.random.uniform(1000, 2000, 10)
        })
        
        timeliness = bridge._calculate_timeliness(data)
        assert 0 <= timeliness <= 1
        assert timeliness < 1.0  # Should be less than 1 due to old data
    
    def test_identify_data_issues(self, bridge):
        """Test data issue identification"""
        # Create test data with various issues
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10),
            'close': [100, 101, np.nan, 103, -1, 105, 1000, 107, 108, 109],  # Missing, negative, outlier
            'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        })
        
        issues = bridge._identify_data_issues(data, 0.7)
        assert isinstance(issues, list)
        assert len(issues) > 0  # Should identify issues
    
    def test_generate_quality_recommendations(self, bridge):
        """Test quality recommendation generation"""
        issues = ["Missing 2 values in close", "Found 1 negative/zero prices"]
        
        recommendations = bridge._generate_quality_recommendations(issues, 0.7)
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0


class TestDataBridgeConsistencyValidation:
    """Test DataBridge data consistency validation functionality"""
    
    @pytest.fixture
    def bridge(self):
        """Create DataBridge instance for testing"""
        with patch('core_structure.market_data.data_bridge.DataManager', return_value=MockDataManager()), \
             patch('core_structure.market_data.data_bridge.DataProcessor', return_value=MockDataProcessor()), \
             patch('core_structure.market_data.data_bridge.DataQualityMonitor', return_value=MockDataQualityMonitor()), \
             patch('core_structure.market_data.data_bridge.MarketDataAnalytics', return_value=MockMarketDataAnalytics()), \
             patch('core_structure.market_data.data_bridge.PerformanceIntegration', return_value=MockPerformanceIntegration()):
            return DataBridge()
    
    @pytest.mark.asyncio
    async def test_validate_data_consistency(self, bridge):
        """Test data consistency validation"""
        # Create test data
        timestamps = pd.date_range('2024-01-01', periods=10, freq='D')
        production_data = pd.DataFrame({
            'timestamp': timestamps,
            'close': np.random.uniform(100, 200, 10),
            'volume': np.random.uniform(1000, 2000, 10)
        })
        
        backtesting_data = pd.DataFrame({
            'timestamp': timestamps,
            'close': production_data['close'] + np.random.uniform(-1, 1, 10),  # Slight differences
            'volume': production_data['volume'] + np.random.uniform(-100, 100, 10)
        })
        
        result = await bridge.validate_data_consistency("AAPL", production_data, backtesting_data)
        
        assert isinstance(result, DataConsistencyReport)
        assert 0 <= result.consistency_score <= 1
        assert result.production_data_points == 10
        assert result.backtesting_data_points == 10
        assert isinstance(result.issues, list)
        assert isinstance(result.recommendations, list)
    
    @pytest.mark.asyncio
    async def test_validate_data_consistency_disabled(self, bridge):
        """Test data consistency validation when disabled"""
        bridge.config.validate_data_consistency = False
        
        production_data = pd.DataFrame({'timestamp': [], 'close': [], 'volume': []})
        backtesting_data = pd.DataFrame({'timestamp': [], 'close': [], 'volume': []})
        
        with pytest.raises(ValueError, match="Data consistency validation is disabled"):
            await bridge.validate_data_consistency("AAPL", production_data, backtesting_data)
    
    @pytest.mark.asyncio
    async def test_validate_data_consistency_missing_data(self, bridge):
        """Test data consistency validation with missing data"""
        timestamps = pd.date_range('2024-01-01', periods=10, freq='D')
        production_data = pd.DataFrame({
            'timestamp': timestamps,
            'close': np.random.uniform(100, 200, 10),
            'volume': np.random.uniform(1000, 2000, 10)
        })
        
        # Backtesting data with fewer points
        backtesting_data = pd.DataFrame({
            'timestamp': timestamps[:8],  # Missing 2 points
            'close': np.random.uniform(100, 200, 8),
            'volume': np.random.uniform(1000, 2000, 8)
        })
        
        result = await bridge.validate_data_consistency("AAPL", production_data, backtesting_data)
        
        assert result.missing_data_points > 0
        assert result.consistency_score < 1.0
    
    def test_align_data_by_timestamp(self, bridge):
        """Test data alignment by timestamp"""
        timestamps1 = pd.date_range('2024-01-01', periods=10, freq='D')
        timestamps2 = pd.date_range('2024-01-03', periods=8, freq='D')  # Overlapping
        
        data1 = pd.DataFrame({
            'timestamp': timestamps1,
            'close': np.random.uniform(100, 200, 10)
        })
        
        data2 = pd.DataFrame({
            'timestamp': timestamps2,
            'close': np.random.uniform(100, 200, 8)
        })
        
        result = bridge._align_data_by_timestamp(data1, data2)
        
        assert result is not None
        prod_aligned, backtest_aligned = result
        assert len(prod_aligned) == len(backtest_aligned)
        assert len(prod_aligned) == 8  # Should match overlapping period


class TestDataBridgeRegimeDetection:
    """Test DataBridge regime detection functionality"""
    
    @pytest.fixture
    def bridge(self):
        """Create DataBridge instance for testing"""
        with patch('core_structure.market_data.data_bridge.DataManager', return_value=MockDataManager()), \
             patch('core_structure.market_data.data_bridge.DataProcessor', return_value=MockDataProcessor()), \
             patch('core_structure.market_data.data_bridge.DataQualityMonitor', return_value=MockDataQualityMonitor()), \
             patch('core_structure.market_data.data_bridge.MarketDataAnalytics', return_value=MockMarketDataAnalytics()), \
             patch('core_structure.market_data.data_bridge.PerformanceIntegration', return_value=MockPerformanceIntegration()):
            return DataBridge()
    
    @pytest.mark.asyncio
    async def test_get_regime_data(self, bridge):
        """Test regime data retrieval"""
        result = await bridge.get_regime_data("AAPL")
        
        assert isinstance(result, DataBridgeResult)
        assert result.data_type == "regime_data"
        assert isinstance(result.data, dict)
        assert "volatility" in result.data
        assert "trend" in result.data
        assert "volume_regime" in result.data
        assert "returns" in result.data
    
    @pytest.mark.asyncio
    async def test_get_regime_data_disabled(self, bridge):
        """Test regime data retrieval when disabled"""
        bridge.config.enable_regime_detection = False
        
        with pytest.raises(ValueError, match="Regime detection is disabled"):
            await bridge.get_regime_data("AAPL")
    
    def test_calculate_regime_indicators(self, bridge):
        """Test regime indicators calculation"""
        # Create test data
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='D'),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000, 2000, 100)
        })
        
        regime_data = bridge._calculate_regime_indicators(data)
        
        assert isinstance(regime_data, dict)
        assert "volatility" in regime_data
        assert "trend" in regime_data
        assert "volume_regime" in regime_data
        assert "returns" in regime_data
        assert len(regime_data["volatility"]) > 0
        assert len(regime_data["trend"]) > 0
    
    def test_calculate_regime_indicators_empty_data(self, bridge):
        """Test regime indicators calculation with empty data"""
        empty_data = pd.DataFrame()
        
        regime_data = bridge._calculate_regime_indicators(empty_data)
        
        assert isinstance(regime_data, dict)
        assert len(regime_data) == 0
    
    def test_calculate_regime_indicators_missing_columns(self, bridge):
        """Test regime indicators calculation with missing columns"""
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='D'),
            'close': np.random.uniform(100, 200, 100)
            # Missing volume column
        })
        
        regime_data = bridge._calculate_regime_indicators(data)
        
        assert isinstance(regime_data, dict)
        assert "volatility" in regime_data
        assert "trend" in regime_data
        assert "volume_regime" in regime_data
        assert "returns" in regime_data


class TestDataBridgePerformance:
    """Test DataBridge performance and statistics"""
    
    @pytest.fixture
    def bridge(self):
        """Create DataBridge instance for testing"""
        with patch('core_structure.market_data.data_bridge.DataManager', return_value=MockDataManager()), \
             patch('core_structure.market_data.data_bridge.DataProcessor', return_value=MockDataProcessor()), \
             patch('core_structure.market_data.data_bridge.DataQualityMonitor', return_value=MockDataQualityMonitor()), \
             patch('core_structure.market_data.data_bridge.MarketDataAnalytics', return_value=MockMarketDataAnalytics()), \
             patch('core_structure.market_data.data_bridge.PerformanceIntegration', return_value=MockPerformanceIntegration()):
            return DataBridge()
    
    def test_get_performance_stats(self, bridge):
        """Test performance statistics retrieval"""
        stats = bridge.get_performance_stats()
        
        assert isinstance(stats, dict)
        assert "total_requests" in stats
        assert "production_requests" in stats
        assert "backtesting_requests" in stats
        assert "cached_requests" in stats
        assert "errors" in stats
        assert "avg_processing_time" in stats
        assert "total_data_points" in stats
    
    def test_clear_cache(self, bridge):
        """Test cache clearing functionality"""
        # Add some data to cache
        bridge._data_cache["test_key"] = ("test_data", datetime.now())
        assert len(bridge._data_cache) > 0
        
        # Clear cache
        bridge.clear_cache()
        assert len(bridge._data_cache) == 0
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self, bridge):
        """Test performance tracking during operations"""
        initial_stats = bridge.get_performance_stats()
        
        # Perform operations
        await bridge.get_market_data("AAPL")
        await bridge.get_market_data("GOOGL")
        
        final_stats = bridge.get_performance_stats()
        
        assert final_stats["total_requests"] > initial_stats["total_requests"]
        assert final_stats["total_data_points"] > initial_stats["total_data_points"]
        assert final_stats["avg_processing_time"] > 0


class TestDataBridgeConvenienceFunctions:
    """Test DataBridge convenience functions"""
    
    def test_get_data_for_backtesting(self):
        """Test convenience function for backtesting data retrieval"""
        with patch('core_structure.market_data.data_bridge.DataManager', return_value=MockDataManager()), \
             patch('core_structure.market_data.data_bridge.DataProcessor', return_value=MockDataProcessor()), \
             patch('core_structure.market_data.data_bridge.DataQualityMonitor', return_value=MockDataQualityMonitor()), \
             patch('core_structure.market_data.data_bridge.MarketDataAnalytics', return_value=MockMarketDataAnalytics()), \
             patch('core_structure.market_data.data_bridge.PerformanceIntegration', return_value=MockPerformanceIntegration()):
            
            data = get_data_for_backtesting("AAPL")
            
            assert isinstance(data, pd.DataFrame)
            assert not data.empty
    
    def test_get_data_for_backtesting_with_timestamps(self):
        """Test convenience function with timestamps"""
        with patch('core_structure.market_data.data_bridge.DataManager', return_value=MockDataManager()), \
             patch('core_structure.market_data.data_bridge.DataProcessor', return_value=MockDataProcessor()), \
             patch('core_structure.market_data.data_bridge.DataQualityMonitor', return_value=MockDataQualityMonitor()), \
             patch('core_structure.market_data.data_bridge.MarketDataAnalytics', return_value=MockMarketDataAnalytics()), \
             patch('core_structure.market_data.data_bridge.PerformanceIntegration', return_value=MockPerformanceIntegration()):
            
            start_time = datetime(2024, 1, 1)
            end_time = datetime(2024, 1, 15)
            
            data = get_data_for_backtesting("AAPL", start_time, end_time)
            
            assert isinstance(data, pd.DataFrame)
            assert not data.empty


class TestDataBridgeIntegration:
    """Test DataBridge integration scenarios"""
    
    @pytest.fixture
    def bridge(self):
        """Create DataBridge instance for testing"""
        with patch('core_structure.market_data.data_bridge.DataManager', return_value=MockDataManager()), \
             patch('core_structure.market_data.data_bridge.DataProcessor', return_value=MockDataProcessor()), \
             patch('core_structure.market_data.data_bridge.DataQualityMonitor', return_value=MockDataQualityMonitor()), \
             patch('core_structure.market_data.data_bridge.MarketDataAnalytics', return_value=MockMarketDataAnalytics()), \
             patch('core_structure.market_data.data_bridge.PerformanceIntegration', return_value=MockPerformanceIntegration()):
            return DataBridge()
    
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self, bridge):
        """Test complete DataBridge workflow"""
        # 1. Get market data
        market_data_result = await bridge.get_market_data("AAPL")
        assert isinstance(market_data_result, DataBridgeResult)
        assert market_data_result.symbol == "AAPL"
        
        # 2. Get quality report
        quality_report = await bridge.get_data_quality_report("AAPL")
        assert isinstance(quality_report, DataQualityReport)
        assert quality_report.overall_quality_score > 0
        
        # 3. Get regime data
        regime_result = await bridge.get_regime_data("AAPL")
        assert isinstance(regime_result, DataBridgeResult)
        assert regime_result.data_type == "regime_data"
        
        # 4. Check performance stats
        stats = bridge.get_performance_stats()
        assert stats["total_requests"] >= 3  # At least 3 requests made
    
    @pytest.mark.asyncio
    async def test_multiple_symbols_integration(self, bridge):
        """Test DataBridge with multiple symbols"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        
        for symbol in symbols:
            result = await bridge.get_market_data(symbol)
            assert result.symbol == symbol
            assert isinstance(result.data, pd.DataFrame)
        
        stats = bridge.get_performance_stats()
        assert stats["total_requests"] == len(symbols)
        assert stats["backtesting_requests"] == len(symbols)
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, bridge):
        """Test error recovery in integration scenarios"""
        # Mock data manager to fail for specific symbol
        original_method = bridge.data_manager.get_market_data
        
        def failing_method(symbol, **kwargs):
            if symbol == "FAILING_SYMBOL":
                raise Exception("Simulated failure")
            return original_method(symbol, **kwargs)
        
        bridge.data_manager.get_market_data = AsyncMock(side_effect=failing_method)
        
        # This should not raise an exception but return fallback data
        result = await bridge.get_market_data("FAILING_SYMBOL")
        assert result.error_message is not None
        assert result.source == "fallback"
        
        # Normal symbols should still work
        result = await bridge.get_market_data("AAPL")
        assert result.error_message is None
        assert result.source == "backtesting"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 