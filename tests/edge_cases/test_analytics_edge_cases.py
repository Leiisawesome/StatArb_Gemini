"""
Edge Case Tests for Analytics Components
=======================================

Comprehensive test suite for edge cases, error scenarios, and extreme
market conditions to ensure robustness of the analytics system.
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any
import warnings

# Suppress warnings during edge case tests
warnings.filterwarnings('ignore')

# Import analytics components
from core_structure.analytics.core_analytics import CoreAnalyticsEngine, PerformanceMetrics
from core_structure.analytics.monitoring_analytics import MonitoringAnalyticsEngine, AlertSeverity
from core_structure.analytics.market_condition_analytics import (
    MarketConditionAnalyticsEngine, MarketCondition, MarketConditionState
)
from core_structure.analytics.research_analytics import ResearchAnalyticsEngine

# ================================================================================
# FIXTURES FOR EDGE CASES
# ================================================================================

@pytest.fixture
def empty_data():
    """Empty dataset"""
    return pd.DataFrame()


@pytest.fixture
def single_row_data():
    """Single row dataset"""
    return pd.DataFrame({
        'timestamp': [datetime.now()],
        'symbol': ['TEST'],
        'close': [100.0],
        'volume': [1000],
        'returns': [0.01]
    })


@pytest.fixture
def nan_data():
    """Dataset with NaN values"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    data = pd.DataFrame({
        'timestamp': dates,
        'symbol': 'TEST',
        'close': np.random.randn(100) * 10 + 100,
        'volume': np.random.randint(1000, 10000, 100),
        'returns': np.random.randn(100) * 0.02
    })
    
    # Introduce NaN values at various positions
    data.loc[10:15, 'close'] = np.nan
    data.loc[30:32, 'volume'] = np.nan
    data.loc[50, 'returns'] = np.nan
    
    return data


@pytest.fixture
def infinite_data():
    """Dataset with infinite values"""
    dates = pd.date_range(start='2024-01-01', periods=50, freq='1H')
    data = pd.DataFrame({
        'timestamp': dates,
        'symbol': 'TEST',
        'close': np.random.randn(50) * 10 + 100,
        'volume': np.random.randint(1000, 10000, 50),
        'returns': np.random.randn(50) * 0.02
    })
    
    # Introduce infinite values
    data.loc[10, 'close'] = np.inf
    data.loc[20, 'returns'] = -np.inf
    data.loc[30, 'volume'] = np.inf
    
    return data


@pytest.fixture
def extreme_volatility_data():
    """Dataset with extreme volatility (black swan events)"""
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='1H')
    
    # Normal volatility most of the time
    normal_returns = np.random.normal(0.001, 0.01, 950)
    
    # Extreme events (black swan)
    extreme_returns = np.array([
        -0.20, -0.15, -0.25, 0.18, -0.12,  # Market crash
        0.15, 0.12, 0.08, 0.22, -0.08,    # Recovery spike
        -0.30, 0.25, -0.18, 0.15, -0.10,  # High volatility
        0.35, -0.28, 0.20, -0.15, 0.12,   # More extreme moves
        -0.40, 0.30, -0.22, 0.18, -0.14,  # Flash crash
        0.28, -0.20, 0.15, -0.12, 0.08,   # Recovery
        -0.18, 0.22, -0.15, 0.12, -0.08,  # Continued volatility
        0.25, -0.18, 0.14, -0.10, 0.06,   # Stabilization
        -0.12, 0.15, -0.08, 0.05, -0.03,  # Return to normal
        0.08, -0.06, 0.04, -0.02, 0.01    # Final normalization
    ])
    
    all_returns = np.concatenate([normal_returns, extreme_returns])
    np.random.shuffle(all_returns)  # Mix extreme events throughout
    
    # Generate prices from returns
    base_price = 100.0
    prices = base_price * np.exp(np.cumsum(all_returns))
    
    return pd.DataFrame({
        'timestamp': dates,
        'symbol': 'EXTREME',
        'close': prices,
        'volume': np.random.randint(1000000, 100000000, len(dates)),  # High volume during extreme events
        'returns': all_returns
    })


@pytest.fixture
def flat_market_data():
    """Dataset with no volatility (flat market)"""
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='1H')
    
    return pd.DataFrame({
        'timestamp': dates,
        'symbol': 'FLAT',
        'close': [100.0] * len(dates),  # Perfectly flat
        'volume': [1000] * len(dates),  # Constant volume
        'returns': [0.0] * len(dates)   # No returns
    })


@pytest.fixture
def corrupted_data():
    """Dataset with various data corruption issues"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    
    data = pd.DataFrame({
        'timestamp': dates,
        'symbol': 'CORRUPT',
        'close': np.random.randn(100) * 10 + 100,
        'volume': np.random.randint(1000, 10000, 100),
        'returns': np.random.randn(100) * 0.02
    })
    
    # Introduce various corruptions
    data.loc[10, 'close'] = -100  # Negative price
    data.loc[20, 'volume'] = -1000  # Negative volume
    data.loc[30, 'timestamp'] = 'invalid_date'  # Invalid timestamp
    data.loc[40, 'symbol'] = None  # Missing symbol
    data.loc[50, 'close'] = 'not_a_number'  # Non-numeric price
    
    return data


# ================================================================================
# CORE ANALYTICS EDGE CASES
# ================================================================================

@pytest.mark.edge_cases
class TestCoreAnalyticsEdgeCases:
    """Edge case tests for CoreAnalyticsEngine"""
    
    def test_empty_data_handling(self, empty_data):
        """Test handling of empty datasets"""
        engine = CoreAnalyticsEngine()
        
        with pytest.raises((ValueError, IndexError, KeyError)):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    engine.analyze_performance(pd.Series(dtype=float))
                )
            finally:
                loop.close()
    
    def test_single_point_data(self, single_row_data):
        """Test handling of single data point"""
        engine = CoreAnalyticsEngine()
        
        returns = single_row_data['returns']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_performance(returns)
            )
            
            # Should handle gracefully with limited metrics
            assert isinstance(result, PerformanceMetrics)
            assert result.total_return is not None
            # Volatility and ratios might be zero or NaN for single point
        finally:
            loop.close()
    
    def test_nan_data_handling(self, nan_data):
        """Test handling of NaN values in data"""
        engine = CoreAnalyticsEngine()
        
        returns = nan_data['returns']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_performance(returns)
            )
            
            # Should handle NaN values gracefully
            assert isinstance(result, PerformanceMetrics)
            # Results should be finite numbers or NaN, not causing crashes
            assert not np.isinf(result.total_return) if not np.isnan(result.total_return) else True
        finally:
            loop.close()
    
    def test_infinite_data_handling(self, infinite_data):
        """Test handling of infinite values"""
        engine = CoreAnalyticsEngine()
        
        returns = infinite_data['returns']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_performance(returns)
            )
            
            # Should handle infinite values without crashing
            assert isinstance(result, PerformanceMetrics)
            # Check that infinite values don't propagate to all metrics
        finally:
            loop.close()
    
    def test_extreme_volatility_handling(self, extreme_volatility_data):
        """Test handling of extreme market volatility"""
        engine = CoreAnalyticsEngine()
        
        returns = extreme_volatility_data['returns']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_performance(returns)
            )
            
            # Should handle extreme volatility
            assert isinstance(result, PerformanceMetrics)
            assert result.volatility > 0
            # Max drawdown should be substantial
            assert result.max_drawdown < -0.1  # At least 10% drawdown
            # Sharpe ratio might be very negative
        finally:
            loop.close()
    
    def test_flat_market_handling(self, flat_market_data):
        """Test handling of flat market with zero volatility"""
        engine = CoreAnalyticsEngine()
        
        returns = flat_market_data['returns']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_performance(returns)
            )
            
            # Should handle zero volatility
            assert isinstance(result, PerformanceMetrics)
            assert result.volatility == 0.0 or np.isclose(result.volatility, 0.0)
            assert result.total_return == 0.0 or np.isclose(result.total_return, 0.0)
            # Sharpe ratio should be undefined (0/0) or handled gracefully
        finally:
            loop.close()


# ================================================================================
# MARKET CONDITION ANALYTICS EDGE CASES
# ================================================================================

@pytest.mark.edge_cases
class TestMarketConditionAnalyticsEdgeCases:
    """Edge case tests for MarketConditionAnalyticsEngine"""
    
    def test_insufficient_data_regime_detection(self, single_row_data):
        """Test regime detection with insufficient data"""
        mock_db = Mock()
        mock_db.execute_query = AsyncMock(return_value=[])
        mock_db.insert_data = AsyncMock(return_value=True)
        
        engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_current_market_condition(single_row_data)
            )
            
            # Should handle gracefully or return default regime
            assert isinstance(result, MarketConditionState)
            # Confidence should be low
            assert result.confidence <= 0.5
        finally:
            loop.close()
    
    def test_extreme_market_regime_detection(self, extreme_volatility_data):
        """Test regime detection during extreme market conditions"""
        mock_db = Mock()
        mock_db.execute_query = AsyncMock(return_value=[])
        mock_db.insert_data = AsyncMock(return_value=True)
        
        engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_current_market_condition(extreme_volatility_data)
            )
            
            # Should detect crisis or high volatility regime
            assert isinstance(result, MarketConditionState)
            assert result.primary_condition in [
                MarketCondition.HIGH_VOLATILITY,
                MarketCondition.CRISIS_MODE,
                MarketCondition.TRANSITION
            ]
            assert result.market_stress > 0.7  # High stress during extreme events
        finally:
            loop.close()
    
    def test_flat_market_regime_detection(self, flat_market_data):
        """Test regime detection in flat market conditions"""
        mock_db = Mock()
        mock_db.execute_query = AsyncMock(return_value=[])
        mock_db.insert_data = AsyncMock(return_value=True)
        
        engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_current_market_condition(flat_market_data)
            )
            
            # Should detect low volatility or sideways regime
            assert isinstance(result, MarketConditionState)
            assert result.primary_condition in [
                MarketCondition.LOW_VOLATILITY,
                MarketCondition.SIDEWAYS_RANGE
            ]
            assert result.volatility_regime == "low"
        finally:
            loop.close()
    
    def test_corrupted_data_handling(self, corrupted_data):
        """Test handling of corrupted market data"""
        mock_db = Mock()
        mock_db.execute_query = AsyncMock(return_value=[])
        mock_db.insert_data = AsyncMock(return_value=True)
        
        engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Should either handle gracefully or raise appropriate error
            with pytest.raises((ValueError, TypeError, KeyError)):
                loop.run_until_complete(
                    engine.analyze_current_market_condition(corrupted_data)
                )
        finally:
            loop.close()
    
    def test_database_connection_failure(self, extreme_volatility_data):
        """Test handling of database connection failures"""
        # Mock database that fails
        mock_db = Mock()
        mock_db.execute_query = AsyncMock(side_effect=Exception("Database connection failed"))
        mock_db.insert_data = AsyncMock(side_effect=Exception("Database connection failed"))
        
        engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Should continue to work without database persistence
            result = loop.run_until_complete(
                engine.analyze_current_market_condition(extreme_volatility_data)
            )
            
            # Analysis should still work, just without persistence
            assert isinstance(result, MarketConditionState)
        finally:
            loop.close()


# ================================================================================
# MONITORING ANALYTICS EDGE CASES
# ================================================================================

@pytest.mark.edge_cases
class TestMonitoringAnalyticsEdgeCases:
    """Edge case tests for MonitoringAnalyticsEngine"""
    
    def test_anomaly_detection_empty_data(self, empty_data):
        """Test anomaly detection with empty data"""
        engine = MonitoringAnalyticsEngine()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.detect_anomalies(empty_data, "empty_test")
            )
            
            # Should return empty list or handle gracefully
            assert isinstance(result, list)
            assert len(result) == 0
        finally:
            loop.close()
    
    def test_anomaly_detection_extreme_data(self, extreme_volatility_data):
        """Test anomaly detection with extreme volatility data"""
        engine = MonitoringAnalyticsEngine()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.detect_anomalies(extreme_volatility_data, "extreme_test")
            )
            
            # Should detect multiple anomalies
            assert isinstance(result, list)
            assert len(result) > 0  # Should find anomalies in extreme data
        finally:
            loop.close()
    
    def test_alert_system_overload(self):
        """Test alert system under high load"""
        engine = MonitoringAnalyticsEngine()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Create many alerts rapidly
            for i in range(1000):
                loop.run_until_complete(
                    engine.create_alert(
                        alert_type="overload_test",
                        severity=AlertSeverity.LOW,
                        message=f"Alert {i}",
                        data={"test_id": i}
                    )
                )
            
            # System should handle high alert volume
            assert len(engine.alerts) == 1000
        finally:
            loop.close()
    
    def test_alert_handler_failure(self):
        """Test handling of alert handler failures"""
        engine = MonitoringAnalyticsEngine()
        
        # Add a handler that always fails
        def failing_handler(alert):
            raise Exception("Handler failed")
        
        engine.alert_handlers.append(failing_handler)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Should not crash when handler fails
            loop.run_until_complete(
                engine.create_alert(
                    alert_type="handler_test",
                    severity=AlertSeverity.HIGH,
                    message="Test alert",
                    data={}
                )
            )
            
            # Alert should still be created despite handler failure
            assert len(engine.alerts) == 1
        finally:
            loop.close()


# ================================================================================
# HISTORICAL ANALYTICS EDGE CASES
# ================================================================================

@pytest.mark.edge_cases
class TestHistoricalAnalyticsEdgeCases:
    """Edge case tests for Historical Analytics framework"""
    
    def test_missing_data_files(self, tmp_path):
        """Test handling of missing data files"""
        from core_structure.analytics.historical_analytics.data_ingestion import HistoricalDataManager
        
        # Point to non-existent file
        nonexistent_file = tmp_path / "nonexistent.csv"
        
        data_manager = HistoricalDataManager(str(nonexistent_file))
        
        from core_structure.analytics.historical_analytics.data_types import HistoricalPeriod
        period = HistoricalPeriod(
            name="test_period",
            start_date="2023-01-01",
            end_date="2023-06-30",
            regime_hint="trending_bull"
        )
        
        # Should raise appropriate error for missing file
        with pytest.raises((FileNotFoundError, IOError, pd.errors.EmptyDataError)):
            data_manager.load_period_data(period)
    
    def test_invalid_date_ranges(self, tmp_path):
        """Test handling of invalid date ranges"""
        from core_structure.analytics.historical_analytics.data_types import HistoricalPeriod
        
        # Test invalid date range (end before start)
        with pytest.raises((ValueError, Exception)):
            period = HistoricalPeriod(
                name="invalid_period",
                start_date="2023-12-31",
                end_date="2023-01-01",  # End before start
                regime_hint="trending_bull"
            )
    
    def test_future_date_handling(self, tmp_path):
        """Test handling of future dates in historical analysis"""
        from core_structure.analytics.historical_analytics.data_types import HistoricalPeriod
        
        # Create period with future dates
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        period = HistoricalPeriod(
            name="future_period",
            start_date=future_date,
            end_date=future_date,
            regime_hint="trending_bull"
        )
        
        # Should handle gracefully (might return empty data or warning)
        assert period.start_date == future_date


# ================================================================================
# INTEGRATION EDGE CASES
# ================================================================================

@pytest.mark.edge_cases
class TestAnalyticsIntegrationEdgeCases:
    """Edge case tests for integrated analytics scenarios"""
    
    def test_component_failure_isolation(self, extreme_volatility_data):
        """Test that component failures don't cascade"""
        # Create engines with one that will fail
        core_engine = CoreAnalyticsEngine()
        monitoring_engine = MonitoringAnalyticsEngine()
        
        # Mock a failing database
        mock_db = Mock()
        mock_db.execute_query = AsyncMock(side_effect=Exception("DB Error"))
        mock_db.insert_data = AsyncMock(side_effect=Exception("DB Error"))
        
        market_engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
        
        returns = extreme_volatility_data['returns']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Core analytics should work despite market engine DB issues
            result = loop.run_until_complete(
                core_engine.analyze_performance(returns)
            )
            
            assert isinstance(result, PerformanceMetrics)
            
            # Monitoring should also work
            anomalies = loop.run_until_complete(
                monitoring_engine.detect_anomalies(extreme_volatility_data, "isolation_test")
            )
            
            assert isinstance(anomalies, list)
        finally:
            loop.close()
    
    def test_concurrent_access_thread_safety(self, extreme_volatility_data):
        """Test thread safety under concurrent access"""
        import threading
        import concurrent.futures
        
        engine = CoreAnalyticsEngine()
        results = []
        errors = []
        
        def analyze_data(thread_id):
            try:
                returns = extreme_volatility_data['returns'] + np.random.normal(0, 0.001, len(extreme_volatility_data))
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        engine.analyze_performance(returns)
                    )
                    results.append((thread_id, result))
                finally:
                    loop.close()
            except Exception as e:
                errors.append((thread_id, e))
        
        # Run concurrent analyses
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(analyze_data, i) for i in range(10)]
            concurrent.futures.wait(futures)
        
        # Should handle concurrent access safely
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 10
    
    def test_memory_exhaustion_handling(self):
        """Test handling of memory exhaustion scenarios"""
        engine = CoreAnalyticsEngine()
        
        # Try to create very large dataset that might exhaust memory
        try:
            # Generate extremely large returns series
            large_returns = pd.Series(np.random.normal(0.001, 0.02, 10_000_000))
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    engine.analyze_performance(large_returns)
                )
                
                # If it succeeds, check result is valid
                assert isinstance(result, PerformanceMetrics)
            finally:
                loop.close()
                
        except MemoryError:
            # Memory exhaustion should be handled gracefully
            pytest.skip("Memory exhaustion test - insufficient system memory")
        except Exception as e:
            # Other errors should not occur
            pytest.fail(f"Unexpected error during memory test: {e}")


# ================================================================================
# ERROR RECOVERY TESTS
# ================================================================================

@pytest.mark.edge_cases
class TestErrorRecovery:
    """Test error recovery and graceful degradation"""
    
    def test_partial_data_recovery(self, corrupted_data):
        """Test recovery from partially corrupted data"""
        # Create a dataset where some rows are valid
        mixed_data = corrupted_data.copy()
        
        # Fix some rows to be valid
        mixed_data.loc[0:50, 'close'] = np.random.randn(51) * 10 + 100
        mixed_data.loc[0:50, 'volume'] = np.random.randint(1000, 10000, 51)
        mixed_data.loc[0:50, 'returns'] = np.random.randn(51) * 0.02
        
        engine = CoreAnalyticsEngine()
        
        # Should be able to work with partial valid data
        valid_returns = mixed_data.loc[0:50, 'returns']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_performance(valid_returns)
            )
            
            assert isinstance(result, PerformanceMetrics)
        finally:
            loop.close()
    
    def test_graceful_degradation_insufficient_data(self):
        """Test graceful degradation when data is insufficient"""
        engine = CoreAnalyticsEngine()
        
        # Very small dataset
        tiny_returns = pd.Series([0.01, -0.005, 0.002])
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_performance(tiny_returns)
            )
            
            # Should still provide basic metrics
            assert isinstance(result, PerformanceMetrics)
            assert result.total_return is not None
            # Some metrics might be NaN or simplified
        finally:
            loop.close()
    
    def test_configuration_error_handling(self):
        """Test handling of invalid configuration"""
        # Test with invalid configuration
        engine = CoreAnalyticsEngine(config={
            'invalid_setting': 'invalid_value',
            'cache_ttl': -1,  # Invalid negative TTL
            'analysis_window': 0  # Invalid zero window
        })
        
        # Should initialize with default values or handle gracefully
        assert engine is not None
        
        # Should still be able to perform analysis
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_performance(returns)
            )
            
            assert isinstance(result, PerformanceMetrics)
        finally:
            loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "edge_cases"])