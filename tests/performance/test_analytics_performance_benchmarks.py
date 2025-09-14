"""
Enhanced Performance Benchmarks for Analytics Components
=======================================================

Comprehensive performance testing to identify bottlenecks and ensure
the analytics system meets institutional-grade performance requirements.
"""

import pytest
import asyncio
import time
import threading
import numpy as np
import pandas as pd
import psutil
import gc
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from typing import Dict, List, Any
import logging

# Suppress warnings during performance tests
warnings.filterwarnings('ignore')

# Import analytics components
from core_structure.analytics.core_analytics import CoreAnalyticsEngine, PerformanceMetrics
from core_structure.analytics.monitoring_analytics import MonitoringAnalyticsEngine
from core_structure.analytics.market_condition_analytics import MarketConditionAnalyticsEngine
from core_structure.analytics.research_analytics import ResearchAnalyticsEngine

# Configure logging for performance tests
logging.getLogger().setLevel(logging.WARNING)

# ================================================================================
# FIXTURES AND UTILITIES
# ================================================================================

@pytest.fixture
def performance_timer():
    """Performance timer fixture"""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            gc.collect()  # Clean up before timing
            self.start_time = time.perf_counter()
        
        def stop(self):
            self.end_time = time.perf_counter()
        
        @property
        def elapsed_seconds(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
        
        @property
        def elapsed_ms(self):
            if self.elapsed_seconds:
                return self.elapsed_seconds * 1000
            return None
    
    return Timer()


@pytest.fixture
def large_market_data():
    """Generate large market dataset for performance testing"""
    # Generate 1 year of minute-level data for 100 symbols
    date_range = pd.date_range(start='2023-01-01', end='2023-12-31', freq='1min')
    symbols = [f"STOCK_{i:03d}" for i in range(100)]
    
    data = []
    for symbol in symbols:
        # Generate realistic price data
        n_periods = len(date_range)
        base_price = np.random.uniform(50, 500)
        returns = np.random.normal(0, 0.001, n_periods)  # 0.1% volatility per minute
        prices = base_price * np.exp(np.cumsum(returns))
        
        symbol_data = pd.DataFrame({
            'timestamp': date_range,
            'symbol': symbol,
            'open': prices * (1 + np.random.normal(0, 0.0001, n_periods)),
            'high': prices * (1 + np.random.uniform(0, 0.002, n_periods)),
            'low': prices * (1 - np.random.uniform(0, 0.002, n_periods)),
            'close': prices,
            'volume': np.random.randint(1000, 100000, n_periods),
            'returns': returns
        })
        data.append(symbol_data)
    
    return pd.concat(data, ignore_index=True)


@pytest.fixture
def memory_monitor():
    """Memory monitoring fixture"""
    class MemoryMonitor:
        def __init__(self):
            self.process = psutil.Process()
            self.start_memory = None
            self.peak_memory = None
        
        def start(self):
            gc.collect()
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            self.peak_memory = self.start_memory
        
        def update_peak(self):
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            if current_memory > self.peak_memory:
                self.peak_memory = current_memory
        
        @property
        def memory_used_mb(self):
            if self.start_memory:
                current = self.process.memory_info().rss / 1024 / 1024
                return current - self.start_memory
            return None
        
        @property
        def peak_memory_mb(self):
            return self.peak_memory
    
    return MemoryMonitor()


# ================================================================================
# CORE ANALYTICS PERFORMANCE TESTS
# ================================================================================

@pytest.mark.performance
class TestCoreAnalyticsPerformance:
    """Performance tests for CoreAnalyticsEngine"""
    
    def test_performance_analysis_speed(self, performance_timer, large_market_data):
        """Test performance analysis computation speed"""
        engine = CoreAnalyticsEngine()
        
        # Generate returns series from large dataset
        symbol_data = large_market_data[large_market_data['symbol'] == 'STOCK_001']
        returns = symbol_data['returns']
        
        performance_timer.start()
        
        # Run performance analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_performance(returns)
            )
        finally:
            loop.close()
        
        performance_timer.stop()
        
        # Performance should complete within reasonable time
        assert performance_timer.elapsed_seconds < 1.0, f"Analysis took {performance_timer.elapsed_seconds:.3f}s"
        assert isinstance(result, PerformanceMetrics)
        assert result.total_return is not None
    
    def test_bulk_performance_analysis(self, performance_timer, large_market_data):
        """Test bulk performance analysis for multiple symbols"""
        engine = CoreAnalyticsEngine()
        
        symbols = large_market_data['symbol'].unique()[:10]  # Test with 10 symbols
        
        performance_timer.start()
        
        results = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for symbol in symbols:
                symbol_data = large_market_data[large_market_data['symbol'] == symbol]
                returns = symbol_data['returns']
                result = loop.run_until_complete(
                    engine.analyze_performance(returns)
                )
                results.append(result)
        finally:
            loop.close()
        
        performance_timer.stop()
        
        # Bulk analysis should scale linearly
        assert performance_timer.elapsed_seconds < 5.0, f"Bulk analysis took {performance_timer.elapsed_seconds:.3f}s"
        assert len(results) == len(symbols)
    
    def test_cache_performance(self, performance_timer, large_market_data):
        """Test caching effectiveness for repeated analyses"""
        engine = CoreAnalyticsEngine()
        
        symbol_data = large_market_data[large_market_data['symbol'] == 'STOCK_001']
        returns = symbol_data['returns']
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # First run (cold cache)
            performance_timer.start()
            result1 = loop.run_until_complete(
                engine.analyze_performance(returns)
            )
            performance_timer.stop()
            first_run_time = performance_timer.elapsed_seconds
            
            # Second run (warm cache)
            performance_timer.start()
            result2 = loop.run_until_complete(
                engine.analyze_performance(returns)
            )
            performance_timer.stop()
            second_run_time = performance_timer.elapsed_seconds
            
        finally:
            loop.close()
        
        # Cache should provide significant speedup
        assert second_run_time < first_run_time / 2, "Cache not providing expected speedup"
    
    def test_concurrent_analysis_performance(self, performance_timer, large_market_data):
        """Test concurrent analysis performance"""
        engine = CoreAnalyticsEngine()
        
        symbols = large_market_data['symbol'].unique()[:5]
        
        async def analyze_symbol(symbol):
            symbol_data = large_market_data[large_market_data['symbol'] == symbol]
            returns = symbol_data['returns']
            return await engine.analyze_performance(returns)
        
        performance_timer.start()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            tasks = [analyze_symbol(symbol) for symbol in symbols]
            results = loop.run_until_complete(asyncio.gather(*tasks))
        finally:
            loop.close()
        
        performance_timer.stop()
        
        # Concurrent execution should be faster than sequential
        assert performance_timer.elapsed_seconds < 3.0, f"Concurrent analysis took {performance_timer.elapsed_seconds:.3f}s"
        assert len(results) == len(symbols)


# ================================================================================
# MARKET CONDITION ANALYTICS PERFORMANCE TESTS
# ================================================================================

@pytest.mark.performance
class TestMarketConditionAnalyticsPerformance:
    """Performance tests for MarketConditionAnalyticsEngine"""
    
    def test_regime_detection_speed(self, performance_timer, large_market_data):
        """Test regime detection computation speed"""
        # Mock dependencies
        mock_db = Mock()
        mock_db.execute_query = AsyncMock(return_value=[])
        mock_db.insert_data = AsyncMock(return_value=True)
        
        engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
        
        # Use subset of data for regime detection
        symbol_data = large_market_data[large_market_data['symbol'] == 'STOCK_001'].iloc[:1000]
        
        performance_timer.start()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.analyze_current_market_condition(symbol_data)
            )
        finally:
            loop.close()
        
        performance_timer.stop()
        
        # Regime detection should be fast
        assert performance_timer.elapsed_seconds < 2.0, f"Regime detection took {performance_timer.elapsed_seconds:.3f}s"
    
    def test_real_time_update_performance(self, performance_timer, large_market_data):
        """Test real-time market condition updates"""
        mock_db = Mock()
        mock_db.execute_query = AsyncMock(return_value=[])
        mock_db.insert_data = AsyncMock(return_value=True)
        
        engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
        
        # Simulate real-time updates
        updates = []
        for i in range(100):
            update_data = large_market_data.iloc[i:i+10]
            updates.append(update_data)
        
        performance_timer.start()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for update in updates[:10]:  # Test with 10 updates
                loop.run_until_complete(
                    engine.analyze_current_market_condition(update)
                )
        finally:
            loop.close()
        
        performance_timer.stop()
        
        # Real-time updates should be very fast
        avg_time_per_update = performance_timer.elapsed_seconds / 10
        assert avg_time_per_update < 0.1, f"Average update time: {avg_time_per_update:.3f}s"
    
    def test_memory_usage_regime_detection(self, memory_monitor, large_market_data):
        """Test memory usage during regime detection"""
        mock_db = Mock()
        mock_db.execute_query = AsyncMock(return_value=[])
        mock_db.insert_data = AsyncMock(return_value=True)
        
        engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
        
        memory_monitor.start()
        
        # Process multiple symbols
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for symbol in large_market_data['symbol'].unique()[:5]:
                symbol_data = large_market_data[large_market_data['symbol'] == symbol].iloc[:500]
                loop.run_until_complete(
                    engine.analyze_current_market_condition(symbol_data)
                )
                memory_monitor.update_peak()
        finally:
            loop.close()
        
        # Memory usage should be reasonable
        assert memory_monitor.memory_used_mb < 500, f"Memory usage: {memory_monitor.memory_used_mb:.1f}MB"


# ================================================================================
# MONITORING ANALYTICS PERFORMANCE TESTS
# ================================================================================

@pytest.mark.performance
class TestMonitoringAnalyticsPerformance:
    """Performance tests for MonitoringAnalyticsEngine"""
    
    def test_anomaly_detection_speed(self, performance_timer, large_market_data):
        """Test anomaly detection computation speed"""
        engine = MonitoringAnalyticsEngine()
        
        # Use subset of data for anomaly detection
        test_data = large_market_data[large_market_data['symbol'] == 'STOCK_001'].iloc[:1000]
        
        performance_timer.start()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                engine.detect_anomalies(test_data, "price_anomalies")
            )
        finally:
            loop.close()
        
        performance_timer.stop()
        
        # Anomaly detection should be fast
        assert performance_timer.elapsed_seconds < 1.5, f"Anomaly detection took {performance_timer.elapsed_seconds:.3f}s"
    
    def test_alert_processing_throughput(self, performance_timer):
        """Test alert processing throughput"""
        engine = MonitoringAnalyticsEngine()
        
        performance_timer.start()
        
        # Generate many alerts
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for i in range(100):
                loop.run_until_complete(
                    engine.create_alert(
                        alert_type="performance",
                        severity="medium",
                        message=f"Test alert {i}",
                        data={"test_value": i}
                    )
                )
        finally:
            loop.close()
        
        performance_timer.stop()
        
        # Should process alerts quickly
        avg_time_per_alert = performance_timer.elapsed_seconds / 100
        assert avg_time_per_alert < 0.01, f"Average alert processing time: {avg_time_per_alert:.4f}s"


# ================================================================================
# HISTORICAL ANALYTICS PERFORMANCE TESTS
# ================================================================================

@pytest.mark.performance
class TestHistoricalAnalyticsPerformance:
    """Performance tests for Historical Analytics framework"""
    
    def test_data_loading_performance(self, performance_timer, tmp_path):
        """Test historical data loading performance"""
        from core_structure.analytics.historical_analytics.data_ingestion import HistoricalDataManager
        
        # Create temporary test data file
        test_data_file = tmp_path / "test_data.csv"
        
        # Generate test data
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='1H')
        test_data = pd.DataFrame({
            'timestamp': dates,
            'symbol': 'TEST',
            'close': 100 + np.random.randn(len(dates)),
            'volume': np.random.randint(1000, 10000, len(dates))
        })
        test_data.to_csv(test_data_file, index=False)
        
        data_manager = HistoricalDataManager(str(test_data_file))
        
        performance_timer.start()
        
        # Load data for a period
        from core_structure.analytics.historical_analytics.data_types import HistoricalPeriod
        period = HistoricalPeriod(
            name="test_period",
            start_date="2023-01-01",
            end_date="2023-06-30",
            regime_hint="trending_bull"
        )
        
        dataset = data_manager.load_period_data(period)
        
        performance_timer.stop()
        
        # Data loading should be fast
        assert performance_timer.elapsed_seconds < 5.0, f"Data loading took {performance_timer.elapsed_seconds:.3f}s"
        assert dataset is not None
    
    def test_bulk_period_analysis_performance(self, performance_timer, tmp_path):
        """Test performance of analyzing multiple historical periods"""
        from core_structure.analytics.historical_analytics.engine import HistoricalAnalyticsEngine
        
        # Create temporary test data
        test_data_file = tmp_path / "bulk_test_data.csv"
        
        # Generate 2 years of hourly data
        dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='1H')
        symbols = ['SPY', 'QQQ', 'IWM']
        
        all_data = []
        for symbol in symbols:
            symbol_data = pd.DataFrame({
                'timestamp': dates,
                'symbol': symbol,
                'close': 100 + np.random.randn(len(dates)).cumsum() * 0.1,
                'volume': np.random.randint(10000, 100000, len(dates))
            })
            all_data.append(symbol_data)
        
        bulk_data = pd.concat(all_data, ignore_index=True)
        bulk_data.to_csv(test_data_file, index=False)
        
        # Create temporary output directory
        output_dir = tmp_path / "outputs"
        engine = HistoricalAnalyticsEngine(
            data_source_path=str(test_data_file),
            output_base_dir=str(output_dir)
        )
        
        performance_timer.start()
        
        # Define multiple periods
        from core_structure.analytics.historical_analytics.data_types import HistoricalPeriod
        periods = [
            HistoricalPeriod("period_1", "2022-01-01", "2022-06-30", "trending_bull"),
            HistoricalPeriod("period_2", "2022-07-01", "2022-12-31", "high_volatility"),
            HistoricalPeriod("period_3", "2023-01-01", "2023-06-30", "trending_bear"),
        ]
        
        # Load data for all periods
        datasets = {}
        for period in periods:
            datasets[period.name] = engine.data_manager.load_period_data(period, symbols)
        
        performance_timer.stop()
        
        # Bulk analysis should complete in reasonable time
        assert performance_timer.elapsed_seconds < 15.0, f"Bulk analysis took {performance_timer.elapsed_seconds:.3f}s"
        assert len(datasets) == len(periods)


# ================================================================================
# INTEGRATION PERFORMANCE TESTS
# ================================================================================

@pytest.mark.performance
class TestAnalyticsIntegrationPerformance:
    """Performance tests for integrated analytics workflows"""
    
    def test_full_analytics_pipeline_performance(self, performance_timer, large_market_data):
        """Test end-to-end analytics pipeline performance"""
        # Initialize all engines
        core_engine = CoreAnalyticsEngine()
        monitoring_engine = MonitoringAnalyticsEngine()
        
        mock_db = Mock()
        mock_db.execute_query = AsyncMock(return_value=[])
        mock_db.insert_data = AsyncMock(return_value=True)
        
        market_engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
        
        # Use sample of data
        sample_data = large_market_data[large_market_data['symbol'] == 'STOCK_001'].iloc[:500]
        returns = sample_data['returns']
        
        performance_timer.start()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Run complete analytics pipeline
            perf_result = loop.run_until_complete(
                core_engine.analyze_performance(returns)
            )
            
            market_condition = loop.run_until_complete(
                market_engine.analyze_current_market_condition(sample_data)
            )
            
            anomalies = loop.run_until_complete(
                monitoring_engine.detect_anomalies(sample_data, "integration_test")
            )
            
        finally:
            loop.close()
        
        performance_timer.stop()
        
        # Full pipeline should complete in reasonable time
        assert performance_timer.elapsed_seconds < 5.0, f"Full pipeline took {performance_timer.elapsed_seconds:.3f}s"
    
    def test_concurrent_analytics_engines(self, performance_timer, large_market_data):
        """Test concurrent operation of multiple analytics engines"""
        sample_data = large_market_data[large_market_data['symbol'] == 'STOCK_001'].iloc[:300]
        returns = sample_data['returns']
        
        async def run_analytics():
            # Initialize engines
            core_engine = CoreAnalyticsEngine()
            monitoring_engine = MonitoringAnalyticsEngine()
            
            mock_db = Mock()
            mock_db.execute_query = AsyncMock(return_value=[])
            mock_db.insert_data = AsyncMock(return_value=True)
            
            market_engine = MarketConditionAnalyticsEngine(database_manager=mock_db)
            
            # Run all analytics concurrently
            tasks = [
                core_engine.analyze_performance(returns),
                market_engine.analyze_current_market_condition(sample_data),
                monitoring_engine.detect_anomalies(sample_data, "concurrent_test")
            ]
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        performance_timer.start()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(run_analytics())
        finally:
            loop.close()
        
        performance_timer.stop()
        
        # Concurrent execution should be efficient
        assert performance_timer.elapsed_seconds < 3.0, f"Concurrent analytics took {performance_timer.elapsed_seconds:.3f}s"
        assert len(results) == 3
        assert not any(isinstance(r, Exception) for r in results)


# ================================================================================
# STRESS TESTS
# ================================================================================

@pytest.mark.performance
@pytest.mark.stress
class TestAnalyticsStress:
    """Stress tests for analytics components"""
    
    def test_high_frequency_updates_stress(self, performance_timer):
        """Test system under high-frequency market data updates"""
        engine = MonitoringAnalyticsEngine()
        
        # Generate rapid updates
        updates_per_second = 100
        duration_seconds = 5
        total_updates = updates_per_second * duration_seconds
        
        performance_timer.start()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for i in range(total_updates):
                loop.run_until_complete(
                    engine.create_alert(
                        alert_type="high_frequency_test",
                        severity="low",
                        message=f"Update {i}",
                        data={"update_id": i, "timestamp": time.time()}
                    )
                )
        finally:
            loop.close()
        
        performance_timer.stop()
        
        # System should handle high-frequency updates
        actual_rate = total_updates / performance_timer.elapsed_seconds
        assert actual_rate > 50, f"Update rate too low: {actual_rate:.1f} updates/sec"
    
    def test_memory_leak_detection(self, memory_monitor):
        """Test for memory leaks during extended operation"""
        engine = CoreAnalyticsEngine()
        
        memory_monitor.start()
        
        # Generate data repeatedly
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for i in range(50):
                # Generate fresh data each iteration
                returns = pd.Series(np.random.normal(0.001, 0.02, 1000))
                loop.run_until_complete(engine.analyze_performance(returns))
                
                if i % 10 == 0:
                    memory_monitor.update_peak()
                    gc.collect()  # Force garbage collection
        finally:
            loop.close()
        
        # Memory usage should not grow excessively
        memory_growth = memory_monitor.memory_used_mb
        assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.1f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])