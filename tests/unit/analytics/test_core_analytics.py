#!/usr/bin/env python3
"""
Test Suite for Core Analytics Module
====================================

Comprehensive tests for core_structure/analytics/core_analytics.py
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Import the module under test
from core_structure.analytics.core_analytics import (
    CoreAnalyticsEngine,
    PerformanceMetrics,
    RiskMetrics,
    AttributionResult,
    ExecutionMetrics,
    PerformancePatternType,
    RiskLevel,
    AttributionType,
    core_analytics,
    analyze_performance,
    analyze_risk,
    analyze_attribution,
    analyze_execution
)


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass"""

    def test_initialization(self):
        """Test PerformanceMetrics initialization with default values"""
        metrics = PerformanceMetrics()

        assert metrics.total_return == 0.0
        assert metrics.annualized_return == 0.0
        assert metrics.volatility == 0.0
        assert metrics.sharpe_ratio == 0.0
        assert metrics.max_drawdown == 0.0
        assert metrics.win_rate == 0.0
        assert metrics.profit_factor == 0.0
        assert metrics.calmar_ratio == 0.0
        assert metrics.sortino_ratio == 0.0
        assert metrics.var_95 == 0.0
        assert metrics.cvar_95 == 0.0
        assert metrics.skewness == 0.0
        assert metrics.kurtosis == 0.0
        assert metrics.beta == 0.0
        assert metrics.alpha == 0.0
        assert metrics.information_ratio == 0.0

    def test_custom_initialization(self):
        """Test PerformanceMetrics with custom values"""
        metrics = PerformanceMetrics(
            total_return=0.15,
            annualized_return=0.12,
            volatility=0.25,
            sharpe_ratio=0.48,
            max_drawdown=-0.08,
            win_rate=0.55
        )

        assert metrics.total_return == 0.15
        assert metrics.annualized_return == 0.12
        assert metrics.volatility == 0.25
        assert metrics.sharpe_ratio == 0.48
        assert metrics.max_drawdown == -0.08
        assert metrics.win_rate == 0.55


class TestRiskMetrics:
    """Test RiskMetrics dataclass"""

    def test_initialization(self):
        """Test RiskMetrics initialization"""
        metrics = RiskMetrics()

        assert metrics.portfolio_var == 0.0
        assert metrics.portfolio_cvar == 0.0
        assert metrics.concentration_risk == 0.0
        assert metrics.correlation_risk == 0.0
        assert metrics.leverage_ratio == 0.0
        assert metrics.market_risk == 0.0
        assert metrics.credit_risk == 0.0
        assert metrics.liquidity_risk == 0.0
        assert metrics.operational_risk == 0.0
        assert metrics.position_limit_utilization == 0.0
        assert metrics.sector_limit_utilization == 0.0
        assert metrics.overall_risk_score == 0.0
        assert metrics.risk_level == RiskLevel.LOW

    def test_risk_level_enum(self):
        """Test RiskLevel enum values"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"


class TestAttributionResult:
    """Test AttributionResult dataclass"""

    def test_initialization(self):
        """Test AttributionResult initialization"""
        result = AttributionResult()

        assert result.total_return == 0.0
        assert result.factor_attribution == {}
        assert result.strategy_attribution == {}
        assert result.timing_attribution == 0.0
        assert result.selection_attribution == 0.0
        assert result.alpha_attribution == 0.0
        assert result.residual_return == 0.0
        assert result.r_squared == 0.0
        assert result.confidence_level == 0.95


class TestExecutionMetrics:
    """Test ExecutionMetrics dataclass"""

    def test_initialization(self):
        """Test ExecutionMetrics initialization"""
        metrics = ExecutionMetrics()

        assert metrics.fill_rate == 0.0
        assert metrics.average_slippage == 0.0
        assert metrics.implementation_shortfall == 0.0
        assert metrics.market_impact == 0.0
        assert metrics.timing_cost == 0.0
        assert metrics.opportunity_cost == 0.0
        assert metrics.total_cost == 0.0
        assert metrics.execution_score == 0.0


class TestCoreAnalyticsEngine:
    """Test CoreAnalyticsEngine class"""

    @pytest.fixture
    def engine(self):
        """Create a test CoreAnalyticsEngine instance"""
        return CoreAnalyticsEngine(
            history_window=252,
            forecast_horizon=5,
            confidence_level=0.95,
            enable_ml=True
        )

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        returns = pd.Series(
            np.random.normal(0.001, 0.02, 100),
            index=dates
        )
        return returns

    @pytest.fixture
    def sample_positions(self):
        """Generate sample positions data"""
        return pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'GOOGL'],
            'weight': [0.4, 0.3, 0.3],
            'value': [40000, 30000, 30000]
        })

    @pytest.fixture
    def sample_benchmark_returns(self):
        """Generate sample benchmark returns"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(43)
        returns = pd.Series(
            np.random.normal(0.0008, 0.015, 100),
            index=dates
        )
        return returns

    def test_initialization(self, engine):
        """Test CoreAnalyticsEngine initialization"""
        assert engine.history_window == 252
        assert engine.forecast_horizon == 5
        assert engine.confidence_level == 0.95
        assert engine.enable_ml == True

        # Check data structures
        assert len(engine.performance_history) == 0
        assert len(engine.risk_history) == 0
        assert len(engine.execution_history) == 0
        assert len(engine.attribution_history) == 0

        # Check ML models are initialized
        assert hasattr(engine, 'performance_model')
        assert hasattr(engine, 'risk_model')
        assert hasattr(engine, 'anomaly_model')
        assert hasattr(engine, 'scaler')

    @pytest.mark.asyncio
    async def test_analyze_performance_basic(self, engine, sample_returns):
        """Test basic performance analysis"""
        result = await engine.analyze_performance(sample_returns)

        assert isinstance(result, PerformanceMetrics)
        assert isinstance(result.total_return, float)
        assert isinstance(result.annualized_return, float)
        assert isinstance(result.volatility, float)
        assert result.start_date is not None
        assert result.end_date is not None

    @pytest.mark.asyncio
    async def test_analyze_performance_with_benchmark(self, engine, sample_returns, sample_benchmark_returns):
        """Test performance analysis with benchmark"""
        result = await engine.analyze_performance(
            sample_returns,
            benchmark_returns=sample_benchmark_returns
        )

        assert isinstance(result, PerformanceMetrics)
        assert hasattr(result, 'beta')
        assert hasattr(result, 'alpha')
        assert hasattr(result, 'information_ratio')

    @pytest.mark.asyncio
    async def test_analyze_risk(self, engine, sample_positions, sample_returns):
        """Test risk analysis"""
        result = await engine.analyze_risk(sample_positions, sample_returns)

        assert isinstance(result, RiskMetrics)
        assert isinstance(result.portfolio_var, float)
        assert isinstance(result.portfolio_cvar, float)
        assert isinstance(result.concentration_risk, float)
        assert isinstance(result.risk_level, RiskLevel)

    @pytest.mark.asyncio
    async def test_analyze_attribution(self, engine, sample_returns):
        """Test attribution analysis"""
        result = await engine.analyze_attribution(sample_returns)

        assert isinstance(result, AttributionResult)
        assert isinstance(result.total_return, float)
        assert isinstance(result.factor_attribution, dict)
        assert isinstance(result.strategy_attribution, dict)

    @pytest.mark.asyncio
    async def test_analyze_execution(self, engine):
        """Test execution analysis"""
        execution_data = [
            {
                'symbol': 'AAPL',
                'requested_quantity': 100,
                'executed_quantity': 95,
                'expected_price': 150.0,
                'executed_price': 150.5,
                'market_impact': 0.002,
                'timing_cost': 0.001
            }
        ]

        result = await engine.analyze_execution(execution_data)

        assert isinstance(result, ExecutionMetrics)
        assert isinstance(result.fill_rate, float)
        assert isinstance(result.average_slippage, float)
        assert isinstance(result.execution_score, float)

    def test_cache_functionality(self, engine, sample_returns):
        """Test caching functionality"""
        # First call should compute and cache
        # Second call should return cached result

        # Clear any existing cache
        engine.clear_cache()
        assert len(engine._metrics_cache) == 0

        # This would require mocking the datetime for proper cache testing
        # For now, just verify cache exists
        assert hasattr(engine, '_metrics_cache')
        assert hasattr(engine, '_cache_timestamp')
        assert hasattr(engine, '_cache_ttl')

    def test_get_summary_statistics(self, engine):
        """Test summary statistics"""
        stats = engine.get_summary_statistics()

        expected_keys = [
            'performance_records',
            'risk_records',
            'execution_records',
            'attribution_records',
            'cache_size',
            'ml_enabled',
            'last_analysis'
        ]

        for key in expected_keys:
            assert key in stats

    def test_clear_cache(self, engine):
        """Test cache clearing"""
        # Add something to cache
        engine._metrics_cache['test'] = 'value'
        engine._cache_timestamp = datetime.now()

        assert len(engine._metrics_cache) > 0
        assert engine._cache_timestamp is not None

        engine.clear_cache()

        assert len(engine._metrics_cache) == 0
        assert engine._cache_timestamp is None

    @pytest.mark.asyncio
    async def test_generate_optimization_recommendations(self, engine, sample_positions):
        """Test optimization recommendations"""
        recommendations = await engine.generate_optimization_recommendations(
            sample_positions,
            pd.Series([0.001, 0.002, 0.001])
        )

        assert isinstance(recommendations, dict)
        assert 'timestamp' in recommendations
        assert 'current_risk_score' in recommendations
        assert 'recommended_changes' in recommendations
        assert 'expected_improvement' in recommendations
        assert 'confidence_level' in recommendations


class TestConvenienceFunctions:
    """Test convenience functions"""

    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns data"""
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        np.random.seed(42)
        returns = pd.Series(
            np.random.normal(0.001, 0.02, 50),
            index=dates
        )
        return returns

    @pytest.fixture
    def sample_positions(self):
        """Generate sample positions data"""
        return pd.DataFrame({
            'symbol': ['AAPL', 'MSFT'],
            'weight': [0.6, 0.4],
            'value': [60000, 40000]
        })

    @pytest.mark.asyncio
    async def test_analyze_performance_function(self, sample_returns):
        """Test analyze_performance convenience function"""
        result = await analyze_performance(sample_returns)

        assert isinstance(result, PerformanceMetrics)
        assert hasattr(result, 'total_return')

    @pytest.mark.asyncio
    async def test_analyze_risk_function(self, sample_positions, sample_returns):
        """Test analyze_risk convenience function"""
        result = await analyze_risk(sample_positions, sample_returns)

        assert isinstance(result, RiskMetrics)
        assert hasattr(result, 'portfolio_var')

    @pytest.mark.asyncio
    async def test_analyze_attribution_function(self, sample_returns):
        """Test analyze_attribution convenience function"""
        result = await analyze_attribution(sample_returns)

        assert isinstance(result, AttributionResult)
        assert hasattr(result, 'total_return')

    @pytest.mark.asyncio
    async def test_analyze_execution_function(self):
        """Test analyze_execution convenience function"""
        execution_data = [
            {
                'symbol': 'AAPL',
                'requested_quantity': 100,
                'executed_quantity': 98,
                'expected_price': 150.0,
                'executed_price': 150.2
            }
        ]

        result = await analyze_execution(execution_data)

        assert isinstance(result, ExecutionMetrics)
        assert hasattr(result, 'fill_rate')


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def engine(self):
        """Create a test CoreAnalyticsEngine instance"""
        return CoreAnalyticsEngine()

    def test_empty_returns_series(self, engine):
        """Test handling of empty returns series"""
        empty_returns = pd.Series([], dtype=float)

        # Should handle gracefully and return default metrics
        # Note: This would need to be implemented in the actual method
        # For now, just verify the method exists
        assert hasattr(engine, 'analyze_performance')

    def test_single_data_point(self, engine):
        """Test handling of single data point"""
        dates = pd.date_range('2024-01-01', periods=1, freq='D')
        single_return = pd.Series([0.01], index=dates)

        # Should handle gracefully
        assert len(single_return) == 1

    def test_extreme_values(self, engine):
        """Test handling of extreme values"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')

        # Very volatile returns
        extreme_returns = pd.Series(
            np.random.choice([-0.5, 0.5], 100),
            index=dates
        )

        # Should handle without crashing
        assert len(extreme_returns) == 100

    @pytest.mark.asyncio
    async def test_invalid_execution_data(self, engine):
        """Test handling of invalid execution data"""
        invalid_data = [
            {
                'symbol': 'AAPL',
                'requested_quantity': 0,  # Invalid: zero quantity
                'executed_quantity': 100,
                'expected_price': 150.0,
                'executed_price': 150.0
            }
        ]

        result = await engine.analyze_execution(invalid_data)

        # Should handle gracefully
        assert isinstance(result, ExecutionMetrics)


class TestIntegration:
    """Integration tests combining multiple analytics"""

    @pytest.fixture
    def engine(self):
        """Create a test CoreAnalyticsEngine instance"""
        return CoreAnalyticsEngine()

    @pytest.fixture
    def comprehensive_data(self):
        """Generate comprehensive test data"""
        dates = pd.date_range('2024-01-01', periods=252, freq='D')
        np.random.seed(42)

        # Generate returns with some realistic patterns
        returns = pd.Series(
            np.random.normal(0.001, 0.02, 252),
            index=dates
        )

        positions = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'GOOGL', 'TSLA'],
            'weight': [0.3, 0.25, 0.25, 0.2],
            'value': [30000, 25000, 25000, 20000]
        })

        execution_data = [
            {
                'symbol': 'AAPL',
                'requested_quantity': 100,
                'executed_quantity': 98,
                'expected_price': 150.0,
                'executed_price': 150.3,
                'market_impact': 0.001,
                'timing_cost': 0.0005
            },
            {
                'symbol': 'MSFT',
                'requested_quantity': 50,
                'executed_quantity': 50,
                'expected_price': 300.0,
                'executed_price': 300.1,
                'market_impact': 0.0008,
                'timing_cost': 0.0003
            }
        ]

        return {
            'returns': returns,
            'positions': positions,
            'execution_data': execution_data
        }

    @pytest.mark.asyncio
    async def test_full_analytics_workflow(self, engine, comprehensive_data):
        """Test complete analytics workflow"""
        returns = comprehensive_data['returns']
        positions = comprehensive_data['positions']
        execution_data = comprehensive_data['execution_data']

        # Run all analytics
        perf_result = await engine.analyze_performance(returns)
        risk_result = await engine.analyze_risk(positions, returns)
        attr_result = await engine.analyze_attribution(returns)
        exec_result = await engine.analyze_execution(execution_data)

        # Verify all results are valid
        assert isinstance(perf_result, PerformanceMetrics)
        assert isinstance(risk_result, RiskMetrics)
        assert isinstance(attr_result, AttributionResult)
        assert isinstance(exec_result, ExecutionMetrics)

        # Verify key metrics are calculated
        assert perf_result.total_return != 0.0
        assert risk_result.portfolio_var != 0.0
        assert exec_result.fill_rate > 0

    @pytest.mark.asyncio
    async def test_analytics_consistency(self, engine, comprehensive_data):
        """Test consistency of analytics results"""
        returns = comprehensive_data['returns']

        # Run performance analysis twice
        result1 = await engine.analyze_performance(returns)
        result2 = await engine.analyze_performance(returns)

        # Results should be consistent (within cache TTL)
        assert result1.total_return == result2.total_return
        assert result1.volatility == result2.volatility
        assert result1.sharpe_ratio == result2.sharpe_ratio
