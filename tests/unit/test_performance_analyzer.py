"""
Comprehensive Unit Tests for PerformanceAnalyzer
===============================================

Tests for the PerformanceAnalyzer component, focusing on:
- ISystemComponent interface compliance
- Performance metrics calculation
- Risk-adjusted metrics and analytics
- Benchmark comparison and analysis
- Caching and performance optimization
- Error handling and recovery

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.2 Enhancement)
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import the component under test
from core_engine.analytics.performance_analyzer import (
    PerformanceAnalyzer,
    PerformanceConfig,
    PerformanceMetrics,
    PerformanceMetric,
    PerformancePeriod,
    RiskMetricsCalculator,
    BenchmarkAnalyzer,
    TradingMetricsCalculator
)


@pytest.fixture
def performance_config():
    """Configuration for performance analyzer"""
    return PerformanceConfig(
        custom_risk_free_rate=0.02,
        confidence_level=0.95,
        enable_caching=True,
        cache_ttl=3600,
        default_benchmark="SPY",
        attribution_frequency="daily"
    )


@pytest.fixture
def sample_returns():
    """Sample return series for testing"""
    np.random.seed(42)  # For reproducible tests
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    returns = np.random.normal(0.001, 0.02, len(dates))  # Daily returns with 1% annual return, 20% volatility
    return pd.Series(returns, index=dates, name='returns')


@pytest.fixture
def sample_benchmark_returns():
    """Sample benchmark return series for testing"""
    np.random.seed(43)  # Different seed for benchmark
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    returns = np.random.normal(0.0008, 0.015, len(dates))  # Slightly lower return and volatility
    return pd.Series(returns, index=dates, name='benchmark_returns')


@pytest.fixture
def mock_risk_calculator():
    """Mock risk calculator for testing"""
    calculator = Mock(spec=RiskMetricsCalculator)
    calculator.calculate_var = Mock(return_value=0.05)
    calculator.calculate_cvar = Mock(return_value=0.07)
    calculator.calculate_maximum_drawdown = Mock(return_value=0.15)
    calculator.health_check = AsyncMock(return_value={'healthy': True})
    return calculator


@pytest.fixture
def mock_benchmark_analyzer():
    """Mock benchmark analyzer for testing"""
    analyzer = Mock(spec=BenchmarkAnalyzer)
    analyzer.calculate_beta = Mock(return_value=1.2)
    analyzer.calculate_alpha = Mock(return_value=0.02)
    analyzer.calculate_tracking_error = Mock(return_value=0.05)
    analyzer.health_check = AsyncMock(return_value={'healthy': True})
    return analyzer


@pytest.fixture
def mock_trading_calculator():
    """Mock trading calculator for testing"""
    calculator = Mock(spec=TradingMetricsCalculator)
    calculator.calculate_win_rate = Mock(return_value=0.65)
    calculator.calculate_profit_factor = Mock(return_value=1.8)
    calculator.health_check = AsyncMock(return_value={'healthy': True})
    return calculator


@pytest.fixture
def performance_analyzer(performance_config, mock_risk_calculator, mock_benchmark_analyzer, mock_trading_calculator):
    """PerformanceAnalyzer instance for testing"""
    analyzer = PerformanceAnalyzer(performance_config)
    analyzer.risk_calculator = mock_risk_calculator
    analyzer.benchmark_analyzer = mock_benchmark_analyzer
    analyzer.trading_calculator = mock_trading_calculator
    return analyzer


class TestPerformanceAnalyzerInterface:
    """Test ISystemComponent interface compliance"""
    
    def test_initialization(self, performance_config):
        """Test PerformanceAnalyzer initialization"""
        analyzer = PerformanceAnalyzer(performance_config)
        
        assert analyzer.config == performance_config
        assert not analyzer.is_initialized
        assert not analyzer.is_operational
        assert analyzer.component_id is None
        assert analyzer.risk_calculator is not None
        assert analyzer.benchmark_analyzer is not None
        assert analyzer.trading_calculator is not None
        assert len(analyzer._performance_cache) == 0
        assert len(analyzer._audit_trail) == 0
    
    @pytest.mark.asyncio
    async def test_initialize_method(self, performance_analyzer):
        """Test initialize method"""
        result = await performance_analyzer.initialize()
        
        assert result is True
        assert performance_analyzer.is_initialized
        assert performance_analyzer.last_error is None
    
    @pytest.mark.asyncio
    async def test_start_method(self, performance_analyzer):
        """Test start method"""
        # Initialize first
        await performance_analyzer.initialize()
        
        result = await performance_analyzer.start()
        
        assert result is True
        assert performance_analyzer.is_operational
    
    @pytest.mark.asyncio
    async def test_start_without_initialization(self, performance_analyzer):
        """Test start method without initialization"""
        result = await performance_analyzer.start()
        
        assert result is False
        assert not performance_analyzer.is_operational
    
    @pytest.mark.asyncio
    async def test_stop_method(self, performance_analyzer):
        """Test stop method"""
        # Initialize and start first
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # Add some data to cache
        performance_analyzer._performance_cache['test'] = {'data': 'test'}
        
        result = await performance_analyzer.stop()
        
        assert result is True
        assert not performance_analyzer.is_operational
        assert len(performance_analyzer._performance_cache) == 0  # Cache should be cleared
    
    @pytest.mark.asyncio
    async def test_health_check(self, performance_analyzer):
        """Test health check method"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        health = await performance_analyzer.health_check()
        
        assert isinstance(health, dict)
        assert 'healthy' in health
        assert 'initialized' in health
        assert 'operational' in health
        assert 'component_type' in health
        assert health['component_type'] == 'PerformanceAnalyzer'
        assert health['initialized'] is True
        assert health['operational'] is True
        assert 'calculators_status' in health
    
    def test_get_status(self, performance_analyzer):
        """Test get_status method"""
        status = performance_analyzer.get_status()
        
        assert isinstance(status, dict)
        assert 'component_type' in status
        assert 'initialized' in status
        assert 'operational' in status
        assert 'cache_size' in status
        assert 'config' in status
        assert status['component_type'] == 'PerformanceAnalyzer'


class TestPerformanceMetricsCalculation:
    """Test performance metrics calculation"""
    
    @pytest.mark.asyncio
    async def test_analyze_performance_basic(self, performance_analyzer, sample_returns):
        """Test basic performance analysis"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        result = await performance_analyzer.analyze_performance(
            returns=sample_returns,
            symbol="AAPL"
        )
        
        assert isinstance(result, PerformanceMetrics)
        assert result.symbol == "AAPL"
        assert result.total_return is not None
        assert result.annualized_return is not None
        assert result.volatility is not None
        assert result.sharpe_ratio is not None
    
    @pytest.mark.asyncio
    async def test_analyze_performance_with_benchmark(self, performance_analyzer, sample_returns, sample_benchmark_returns):
        """Test performance analysis with benchmark"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        result = await performance_analyzer.analyze_performance(
            returns=sample_returns,
            symbol="AAPL",
            benchmark_returns=sample_benchmark_returns
        )
        
        assert isinstance(result, PerformanceMetrics)
        assert result.symbol == "AAPL"
        assert result.beta is not None
        assert result.alpha is not None
        assert result.tracking_error is not None
        assert result.information_ratio is not None
    
    @pytest.mark.asyncio
    async def test_analyze_performance_empty_returns(self, performance_analyzer):
        """Test performance analysis with empty returns"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        empty_returns = pd.Series([], dtype=float)
        
        result = await performance_analyzer.analyze_performance(
            returns=empty_returns,
            symbol="EMPTY"
        )
        
        assert isinstance(result, PerformanceMetrics)
        assert result.symbol == "EMPTY"
        # Should handle empty returns gracefully
    
    @pytest.mark.asyncio
    async def test_performance_metrics_calculation(self, performance_analyzer, sample_returns):
        """Test specific performance metrics calculation"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # Test individual metric calculations
        total_return = performance_analyzer.calculate_total_return(sample_returns)
        volatility = performance_analyzer.calculate_volatility(sample_returns)
        sharpe_ratio = performance_analyzer.calculate_sharpe_ratio(sample_returns)
        
        assert isinstance(total_return, (int, float))
        assert isinstance(volatility, (int, float))
        assert isinstance(sharpe_ratio, (int, float))
        assert volatility > 0  # Volatility should be positive
    
    @pytest.mark.asyncio
    async def test_risk_adjusted_metrics(self, performance_analyzer, sample_returns):
        """Test risk-adjusted metrics calculation"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # Test risk-adjusted metrics
        sortino_ratio = performance_analyzer.calculate_sortino_ratio(sample_returns)
        calmar_ratio = performance_analyzer.calculate_calmar_ratio(sample_returns)
        
        assert isinstance(sortino_ratio, (int, float))
        assert isinstance(calmar_ratio, (int, float))


class TestCachingAndPerformance:
    """Test caching and performance optimization"""
    
    @pytest.mark.asyncio
    async def test_performance_caching(self, performance_analyzer, sample_returns):
        """Test performance analysis caching"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # First analysis should populate cache
        result1 = await performance_analyzer.analyze_performance(
            returns=sample_returns,
            symbol="AAPL"
        )
        
        cache_size_after_first = len(performance_analyzer._performance_cache)
        
        # Second analysis should use cache (if caching is enabled)
        result2 = await performance_analyzer.analyze_performance(
            returns=sample_returns,
            symbol="AAPL"
        )
        
        assert isinstance(result1, PerformanceMetrics)
        assert isinstance(result2, PerformanceMetrics)
        assert result1.symbol == result2.symbol
        
        # Cache size should not increase for same analysis
        if performance_analyzer.config.enable_caching:
            assert len(performance_analyzer._performance_cache) == cache_size_after_first
    
    @pytest.mark.asyncio
    async def test_cache_clearing(self, performance_analyzer, sample_returns):
        """Test cache clearing functionality"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # Populate cache
        await performance_analyzer.analyze_performance(
            returns=sample_returns,
            symbol="AAPL"
        )
        
        initial_cache_size = len(performance_analyzer._performance_cache)
        
        # Stop should clear cache
        await performance_analyzer.stop()
        
        assert len(performance_analyzer._performance_cache) == 0
        if initial_cache_size > 0:
            assert len(performance_analyzer._performance_cache) < initial_cache_size
    
    @pytest.mark.asyncio
    async def test_large_cache_health_warning(self, performance_analyzer):
        """Test health warning for large cache"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # Simulate large cache
        for i in range(10001):  # Exceed the 10000 limit
            performance_analyzer._performance_cache[f'key_{i}'] = {'data': f'value_{i}'}
        
        health = await performance_analyzer.health_check()
        
        assert health['healthy'] is False
        assert 'warning' in health
        assert 'cache size' in health['warning'].lower()


class TestBenchmarkAnalysis:
    """Test benchmark analysis functionality"""
    
    @pytest.mark.asyncio
    async def test_benchmark_comparison(self, performance_analyzer, sample_returns, sample_benchmark_returns):
        """Test benchmark comparison analysis"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        result = await performance_analyzer.analyze_performance(
            returns=sample_returns,
            symbol="AAPL",
            benchmark_returns=sample_benchmark_returns
        )
        
        # Should have benchmark-related metrics
        assert result.beta is not None
        assert result.alpha is not None
        assert result.tracking_error is not None
        
        # Mock should have been called
        performance_analyzer.benchmark_analyzer.calculate_beta.assert_called()
        performance_analyzer.benchmark_analyzer.calculate_alpha.assert_called()
        performance_analyzer.benchmark_analyzer.calculate_tracking_error.assert_called()
    
    @pytest.mark.asyncio
    async def test_benchmark_data_storage(self, performance_analyzer, sample_benchmark_returns):
        """Test benchmark data storage"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # Store benchmark data
        performance_analyzer._benchmark_data['SPY'] = sample_benchmark_returns
        
        status = performance_analyzer.get_status()
        assert status['benchmark_data_size'] == 1
        
        health = await performance_analyzer.health_check()
        assert health['benchmark_data_size'] == 1


class TestErrorHandling:
    """Test error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_initialization_error_handling(self, performance_config):
        """Test initialization error handling"""
        analyzer = PerformanceAnalyzer(performance_config)
        
        # Mock calculator initialization failure
        analyzer.risk_calculator.initialize = AsyncMock(return_value=False)
        
        result = await analyzer.initialize()
        
        assert result is False
        assert analyzer.last_error is not None
    
    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, performance_analyzer):
        """Test health check error handling"""
        await performance_analyzer.initialize()
        
        # Mock an error in health check
        with patch.object(performance_analyzer, '_performance_cache', side_effect=Exception("Mock error")):
            health = await performance_analyzer.health_check()
        
        # Should handle error gracefully
        assert isinstance(health, dict)
        assert 'healthy' in health
        if not health['healthy']:
            assert 'error' in health
    
    @pytest.mark.asyncio
    async def test_calculator_health_failure(self, performance_analyzer):
        """Test handling of calculator health failures"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # Mock calculator health failure
        performance_analyzer.risk_calculator.health_check = AsyncMock(return_value={'healthy': False})
        
        health = await performance_analyzer.health_check()
        
        assert health['healthy'] is False
        assert 'calculators_status' in health
        assert health['calculators_status']['risk_calculator']['healthy'] is False
    
    @pytest.mark.asyncio
    async def test_performance_analysis_error_handling(self, performance_analyzer):
        """Test error handling in performance analysis"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # Test with invalid data
        invalid_returns = pd.Series([np.inf, np.nan, -np.inf])
        
        # Should handle invalid data gracefully
        result = await performance_analyzer.analyze_performance(
            returns=invalid_returns,
            symbol="INVALID"
        )
        
        assert isinstance(result, PerformanceMetrics)
        assert result.symbol == "INVALID"


class TestAuditTrail:
    """Test audit trail functionality"""
    
    def test_audit_trail_initialization(self, performance_analyzer):
        """Test audit trail initialization"""
        assert hasattr(performance_analyzer, '_audit_trail')
        assert isinstance(performance_analyzer._audit_trail, list)
        assert len(performance_analyzer._audit_trail) == 0
    
    def test_audit_trail_status_reporting(self, performance_analyzer):
        """Test audit trail in status reporting"""
        # Add some audit entries
        performance_analyzer._audit_trail.append({'action': 'test', 'timestamp': datetime.now()})
        
        status = performance_analyzer.get_status()
        assert status['audit_trail_size'] == 1
        
        # Health check should also report audit trail size
        health = asyncio.run(performance_analyzer.health_check())
        assert health['audit_trail_size'] == 1


class TestPerformanceAnalyzerIntegration:
    """Integration tests for performance analyzer"""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, performance_analyzer, sample_returns):
        """Test complete performance analyzer lifecycle"""
        # Initialize
        assert await performance_analyzer.initialize() is True
        assert performance_analyzer.is_initialized is True
        
        # Start
        assert await performance_analyzer.start() is True
        assert performance_analyzer.is_operational is True
        
        # Perform analysis
        result = await performance_analyzer.analyze_performance(
            returns=sample_returns,
            symbol="AAPL"
        )
        assert isinstance(result, PerformanceMetrics)
        
        # Check health
        health = await performance_analyzer.health_check()
        assert health['healthy'] is True
        
        # Check status
        status = performance_analyzer.get_status()
        assert status['initialized'] is True
        assert status['operational'] is True
        
        # Stop
        assert await performance_analyzer.stop() is True
        assert performance_analyzer.is_operational is False
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, performance_analyzer, sample_returns):
        """Test concurrent performance analysis"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # Create multiple analysis tasks
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        tasks = []
        
        for symbol in symbols:
            task = performance_analyzer.analyze_performance(
                returns=sample_returns,
                symbol=symbol
            )
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify all results
        assert len(results) == 3
        for i, result in enumerate(results):
            assert isinstance(result, PerformanceMetrics)
            assert result.symbol == symbols[i]
    
    @pytest.mark.asyncio
    async def test_performance_with_different_periods(self, performance_analyzer, sample_returns):
        """Test performance analysis with different time periods"""
        await performance_analyzer.initialize()
        await performance_analyzer.start()
        
        # Test different periods
        periods = [PerformancePeriod.DAILY, PerformancePeriod.MONTHLY, PerformancePeriod.YEARLY]
        
        for period in periods:
            result = await performance_analyzer.analyze_performance(
                returns=sample_returns,
                symbol="AAPL",
                period=period
            )
            
            assert isinstance(result, PerformanceMetrics)
            assert result.period == period
            assert result.symbol == "AAPL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
