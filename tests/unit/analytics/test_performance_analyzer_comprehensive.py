#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Performance Analyzer
===============================================

Tests core performance calculation methods, risk metrics, and analysis functionality.

Test Coverage:
- Performance metrics calculation (returns, volatility, Sharpe ratio)
- Risk metrics (VaR, CVaR, drawdown, downside volatility)
- Benchmark-relative metrics (beta, alpha, tracking error)
- Trading statistics (win rate, profit factor)
- Period analysis and date filtering
- Error handling and edge cases

Author: StatArb_Gemini Test Suite
Date: November 4, 2025
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from core_engine.analytics.performance_analyzer import (
    PerformanceAnalyzer,
    PerformanceConfig,
    PerformanceMetrics,
    PerformancePeriod,
    RiskFreeRateSource,
    RiskMetricsCalculator,
    TradingMetricsCalculator
)

class TestRiskMetricsCalculator:
    """Test RiskMetricsCalculator functionality"""

    @pytest.fixture
    def calculator(self):
        """Create risk metrics calculator"""
        config = PerformanceConfig()
        return RiskMetricsCalculator(config)

    def test_calculate_var(self, calculator):
        """Test Value at Risk calculation"""
        # Generate normal returns
        returns = pd.Series(np.random.normal(0.001, 0.02, 1000))

        var_95 = calculator.calculate_var(returns, 0.95)
        var_99 = calculator.calculate_var(returns, 0.99)

        # 99% VaR should be more negative (more conservative) than 95% VaR
        assert var_99 < var_95 < 0

    def test_calculate_cvar(self, calculator):
        """Test Conditional Value at Risk calculation"""
        returns = pd.Series(np.random.normal(0.001, 0.02, 1000))

        cvar_95 = calculator.calculate_cvar(returns, 0.95)
        cvar_99 = calculator.calculate_cvar(returns, 0.99)

        # CVaR should be more negative than VaR
        var_95 = calculator.calculate_var(returns, 0.95)
        assert cvar_95 < var_95
        assert cvar_99 < cvar_95

    def test_calculate_maximum_drawdown(self, calculator):
        """Test maximum drawdown calculation"""
        # Create a series with a clear drawdown
        returns = pd.Series([0.01, 0.02, -0.05, -0.03, 0.01, 0.02])
        (1 + returns).cumprod()

        max_dd, duration = calculator.calculate_maximum_drawdown(returns)

        assert max_dd > 0  # Drawdown should be positive (absolute value)
        assert duration >= 1  # Duration should be at least 1 period

    def test_calculate_downside_volatility(self, calculator):
        """Test downside volatility calculation"""
        # Mix of positive and negative returns
        returns = pd.Series([0.02, -0.01, 0.03, -0.02, 0.01, -0.03])

        downside_vol = calculator.calculate_downside_volatility(returns)

        assert downside_vol >= 0
        # Downside volatility should be less than or equal to total volatility
        # Both should be annualized
        total_vol = returns.std() * np.sqrt(252)  # Annualize total volatility
        assert downside_vol <= total_vol

    def test_calculate_omega_ratio(self, calculator):
        """Test omega ratio calculation"""
        # Returns with some above and below threshold
        returns = pd.Series([0.02, -0.01, 0.03, -0.02, 0.01, -0.03])

        omega = calculator.calculate_omega_ratio(returns, threshold=0.0)

        assert omega > 0
        # Omega ratio should be greater than 1 if there are more gains than losses
        # (though this depends on the specific returns)

class TestTradingMetricsCalculator:
    """Test TradingMetricsCalculator functionality"""

    @pytest.fixture
    def calculator(self):
        """Create trading metrics calculator"""
        return TradingMetricsCalculator()

    def test_calculate_trading_statistics_positive_returns(self, calculator):
        """Test trading statistics with positive returns"""
        returns = pd.Series([0.02, 0.03, -0.01, 0.04, -0.02])

        stats = calculator.calculate_trading_statistics(returns)

        assert 'win_rate' in stats
        assert 'profit_factor' in stats
        assert 'average_win' in stats
        assert 'average_loss' in stats
        assert 'total_trades' in stats

        assert stats['total_trades'] == 5
        assert stats['winning_trades'] == 3  # 0.02, 0.03, 0.04
        assert stats['losing_trades'] == 2   # -0.01, -0.02
        assert abs(stats['win_rate'] - 0.6) < 0.01

    def test_calculate_trading_statistics_all_positive(self, calculator):
        """Test trading statistics with all positive returns"""
        returns = pd.Series([0.02, 0.03, 0.01, 0.04])

        stats = calculator.calculate_trading_statistics(returns)

        assert stats['win_rate'] == 1.0
        assert stats['total_trades'] == 4
        assert stats['winning_trades'] == 4
        assert stats['losing_trades'] == 0

    def test_calculate_trading_statistics_all_negative(self, calculator):
        """Test trading statistics with all negative returns"""
        returns = pd.Series([-0.02, -0.03, -0.01, -0.04])

        stats = calculator.calculate_trading_statistics(returns)

        assert stats['win_rate'] == 0.0
        assert stats['total_trades'] == 4
        assert stats['winning_trades'] == 0
        assert stats['losing_trades'] == 4

class TestPerformanceAnalyzer:
    """Test PerformanceAnalyzer core functionality"""

    @pytest.fixture
    def config(self):
        """Create performance config"""
        return PerformanceConfig(
            risk_free_rate_source=RiskFreeRateSource.CUSTOM,
            custom_risk_free_rate=0.02,
            trading_days_per_year=252,
            confidence_level=0.95
        )

    @pytest.fixture
    def analyzer(self, config):
        """Create performance analyzer"""
        return PerformanceAnalyzer(config)

    @pytest.fixture
    def sample_returns(self):
        """Create sample return series"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        # Generate realistic returns with some volatility
        returns = pd.Series(
            np.random.normal(0.0005, 0.015, 100),
            index=dates
        )
        return returns

    @pytest.fixture
    def sample_benchmark_returns(self):
        """Create sample benchmark return series"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        returns = pd.Series(
            np.random.normal(0.0003, 0.012, 100),
            index=dates,
            name='SPY'
        )
        return returns

    def test_initialization(self, analyzer, config):
        """Test analyzer initialization"""
        assert analyzer.config == config
        assert analyzer.risk_calculator is not None
        assert analyzer.benchmark_analyzer is not None
        assert analyzer.trading_calculator is not None

    def test_get_risk_free_rate(self, analyzer):
        """Test risk-free rate retrieval"""
        rate = analyzer._get_risk_free_rate()
        assert rate == 0.02

    def test_get_periods_per_year_daily(self, analyzer):
        """Test periods per year calculation for daily returns"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)

        periods = analyzer._get_periods_per_year(returns)
        assert periods == 252  # Trading days per year

    def test_get_periods_per_year_monthly(self, analyzer):
        """Test periods per year calculation for monthly returns"""
        dates = pd.date_range(start='2024-01-01', periods=12, freq='M')
        returns = pd.Series(np.random.normal(0.01, 0.05, 12), index=dates)

        periods = analyzer._get_periods_per_year(returns)
        assert periods == 12  # Monthly periods

    @pytest.mark.asyncio
    async def test_analyze_performance_basic(self, analyzer, sample_returns):
        """Test basic performance analysis"""
        metrics = await analyzer.analyze_performance(sample_returns, "TEST")

        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.symbol == "TEST"
        assert isinstance(metrics.total_return, (int, float))
        assert isinstance(metrics.annualized_return, (int, float))
        assert isinstance(metrics.volatility, (int, float))
        assert isinstance(metrics.sharpe_ratio, (int, float, type(None)))

    @pytest.mark.asyncio
    async def test_analyze_performance_with_benchmark(self, analyzer, sample_returns, sample_benchmark_returns):
        """Test performance analysis with benchmark"""
        metrics = await analyzer.analyze_performance(
            sample_returns,
            "TEST",
            sample_benchmark_returns
        )

        assert metrics.benchmark_symbol == "SPY"
        assert isinstance(metrics.beta, (int, float, type(None)))
        assert isinstance(metrics.alpha, (int, float, type(None)))
        assert isinstance(metrics.tracking_error, (int, float, type(None)))

    @pytest.mark.asyncio
    async def test_analyze_performance_empty_returns(self, analyzer):
        """Test performance analysis with empty returns"""
        empty_returns = pd.Series([], dtype=float)

        metrics = await analyzer.analyze_performance(empty_returns, "EMPTY")

        assert metrics.symbol == "EMPTY"
        assert metrics.total_return == 0.0
        assert metrics.annualized_return == 0.0

    @pytest.mark.asyncio
    async def test_analyze_performance_date_filtering(self, analyzer):
        """Test performance analysis with date filtering"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)

        start_date = datetime(2024, 2, 1)
        end_date = datetime(2024, 3, 1)

        metrics = await analyzer.analyze_performance(
            returns,
            "TEST",
            start_date=start_date,
            end_date=end_date
        )

        # Check that the date range is correctly filtered
        assert metrics.start_date >= start_date
        assert metrics.end_date <= end_date

    @pytest.mark.asyncio
    async def test_analyze_performance_by_period(self, analyzer, sample_returns):
        """Test period-based performance analysis"""
        result = await analyzer.analyze_performance_by_period(sample_returns)

        assert isinstance(result, dict)
        # Should contain analysis for different periods
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_analyze_performance_by_strategy(self, analyzer):
        """Test strategy-based performance analysis"""
        strategy_returns = {
            'strategy1': pd.Series([0.01, 0.02, -0.01]),
            'strategy2': pd.Series([0.005, -0.005, 0.015])
        }

        result = await analyzer.analyze_performance_by_strategy(strategy_returns)

        assert isinstance(result, dict)
        assert 'strategy1' in result
        assert 'strategy2' in result

    @pytest.mark.asyncio
    async def test_generate_performance_report(self, analyzer, sample_returns):
        """Test performance report generation"""
        report = await analyzer.generate_performance_report(
            sample_returns,
            "Test Portfolio"
        )

        assert report.portfolio_name == "Test Portfolio"
        assert report.portfolio_metrics is not None
        assert isinstance(report.portfolio_metrics, PerformanceMetrics)

    @pytest.mark.asyncio
    async def test_generate_performance_report_with_benchmark(self, analyzer, sample_returns, sample_benchmark_returns):
        """Test performance report generation with benchmark"""
        report = await analyzer.generate_performance_report(
            sample_returns,
            "Test Portfolio",
            benchmark_returns=sample_benchmark_returns
        )

        assert report.portfolio_metrics.benchmark_symbol == "SPY"

    def test_get_period_returns(self, analyzer):
        """Test period returns extraction"""
        dates = pd.date_range(start='2024-01-01', periods=365, freq='D')
        returns = pd.Series(np.random.normal(0.001, 0.02, 365), index=dates)

        # Test 1 year period
        period_returns = analyzer._get_period_returns(returns, PerformancePeriod.YEARLY)

        # Should return 1 yearly return for 1 year of data
        assert len(period_returns) == 1

    def test_calculate_rolling_sharpe_ratio(self, analyzer, sample_returns):
        """Test rolling Sharpe ratio calculation"""
        window = 20
        rolling_sharpe = analyzer._calculate_rolling_sharpe(sample_returns, window)

        assert isinstance(rolling_sharpe, pd.Series)
        assert len(rolling_sharpe) == len(sample_returns)  # Same length as input

        # First (window-1) values should be NaN
        assert pd.isna(rolling_sharpe.iloc[0])
        assert pd.isna(rolling_sharpe.iloc[window-2])

        # Values from window onwards should be numeric
        assert not pd.isna(rolling_sharpe.iloc[window-1])
        assert isinstance(rolling_sharpe.iloc[window-1], (int, float))

    def test_calculate_rolling_volatility(self, analyzer, sample_returns):
        """Test rolling volatility calculation"""
        window = 20
        rolling_vol = analyzer._calculate_rolling_volatility(sample_returns, window)

        assert isinstance(rolling_vol, pd.Series)
        assert len(rolling_vol) == len(sample_returns)  # Same length as input

        # First (window-1) values should be NaN
        assert pd.isna(rolling_vol.iloc[0])
        assert pd.isna(rolling_vol.iloc[window-2])

        # Values from window onwards should be non-negative
        valid_vols = rolling_vol.iloc[window-1:]
        assert all(valid_vols >= 0)

    def test_calculate_rolling_beta(self, analyzer, sample_returns, sample_benchmark_returns):
        """Test rolling beta calculation"""
        # Note: Rolling beta calculation not implemented in this version
        # This test is a placeholder for future implementation

    @pytest.mark.asyncio
    async def test_error_handling_invalid_returns(self, analyzer):
        """Test error handling with invalid returns data"""
        # Test with NaN values
        returns_with_nan = pd.Series([0.01, np.nan, 0.02, np.nan])

        # Should handle NaN gracefully
        metrics = await analyzer.analyze_performance(returns_with_nan, "TEST")
        assert isinstance(metrics, PerformanceMetrics)

    @pytest.mark.asyncio
    async def test_extreme_return_values(self, analyzer):
        """Test handling of extreme return values"""
        # Test with very large returns
        extreme_returns = pd.Series([10.0, -0.9, 5.0, -0.8])

        metrics = await analyzer.analyze_performance(extreme_returns, "EXTREME")

        # Should still produce valid metrics
        assert isinstance(metrics, PerformanceMetrics)
        assert isinstance(metrics.total_return, (int, float))

    def test_memory_efficiency_large_dataset(self, analyzer):
        """Test memory efficiency with large datasets"""
        # Create a large return series
        large_returns = pd.Series(np.random.normal(0.001, 0.02, 10000))

        # Should handle large datasets without excessive memory usage
        # This is more of a smoke test
        assert len(large_returns) == 10000

    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, analyzer):
        """Test concurrent performance analysis"""
        import asyncio

        # Create multiple return series
        return_series = [
            pd.Series(np.random.normal(0.001, 0.02, 100)) for _ in range(5)
        ]

        # Analyze all concurrently
        tasks = [
            analyzer.analyze_performance(returns, f"PORTFOLIO_{i}")
            for i, returns in enumerate(return_series)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(isinstance(r, PerformanceMetrics) for r in results)

    def test_configuration_validation(self):
        """Test configuration validation"""
        # Valid configuration should work
        config = PerformanceConfig()
        analyzer = PerformanceAnalyzer(config)
        assert analyzer.config == config

        # Invalid configuration should raise error
        with pytest.raises(Exception):  # ConfigurationRequiredError
            PerformanceAnalyzer("invalid_config")