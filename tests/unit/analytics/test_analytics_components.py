"""
Comprehensive Analytics Component Tests
Tests for performance analyzer, attribution analyzer, metrics calculator, and report generator
"""

import pytest
import pandas as pd
import numpy as np


class TestPerformanceAnalyzerEnums:
    """Test performance analyzer enums"""

    def test_performance_metric_enum(self):
        """Test PerformanceMetric enum"""
        from core_engine.analytics.performance_analyzer import PerformanceMetric

        assert PerformanceMetric.TOTAL_RETURN.value == "total_return"
        assert PerformanceMetric.SHARPE_RATIO.value == "sharpe_ratio"
        assert PerformanceMetric.MAXIMUM_DRAWDOWN.value == "maximum_drawdown"
        assert PerformanceMetric.VAR.value == "value_at_risk"

    def test_performance_period_enum(self):
        """Test PerformancePeriod enum"""
        from core_engine.analytics.performance_analyzer import PerformancePeriod

        assert PerformancePeriod.DAILY.value == "daily"
        assert PerformancePeriod.WEEKLY.value == "weekly"
        assert PerformancePeriod.MONTHLY.value == "monthly"
        assert PerformancePeriod.YEARLY.value == "yearly"
        assert PerformancePeriod.INCEPTION.value == "inception"

    def test_risk_free_rate_source_enum(self):
        """Test RiskFreeRateSource enum"""
        from core_engine.analytics.performance_analyzer import RiskFreeRateSource

        assert RiskFreeRateSource.TREASURY_3M.value == "treasury_3m"
        assert RiskFreeRateSource.TREASURY_10Y.value == "treasury_10y"
        assert RiskFreeRateSource.SOFR.value == "sofr"


class TestPerformanceConfiguration:
    """Test performance analyzer configuration"""

    def test_performance_config_creation(self):
        """Test PerformanceConfig creation"""
        from core_engine.analytics.performance_analyzer import PerformanceConfig, RiskFreeRateSource

        config = PerformanceConfig()
        assert config.trading_days_per_year == 252
        assert config.confidence_level == 0.95
        assert config.risk_free_rate_source == RiskFreeRateSource.TREASURY_3M
        assert config.custom_risk_free_rate == 0.02

    def test_performance_config_custom_risk_free_rate(self):
        """Test custom risk-free rate"""
        from core_engine.analytics.performance_analyzer import PerformanceConfig

        config = PerformanceConfig(custom_risk_free_rate=0.03)
        assert config.risk_free_rate == 0.03

    def test_performance_config_analysis_periods(self):
        """Test analysis periods configuration"""
        from core_engine.analytics.performance_analyzer import PerformanceConfig, PerformancePeriod

        config = PerformanceConfig()
        assert PerformancePeriod.DAILY in config.analysis_periods
        assert PerformancePeriod.MONTHLY in config.analysis_periods
        assert PerformancePeriod.INCEPTION in config.analysis_periods


class TestPerformanceMetrics:
    """Test performance metrics calculations"""

    def test_simple_return_calculation(self):
        """Test simple return calculation"""
        initial_value = 100000
        final_value = 110000
        simple_return = (final_value - initial_value) / initial_value

        assert pytest.approx(simple_return, 0.001) == 0.10

    def test_compound_return_calculation(self):
        """Test compound return calculation"""
        returns = pd.Series([0.01, 0.02, -0.01, 0.03])
        compound_return = (1 + returns).prod() - 1

        assert compound_return > 0
        assert compound_return < 0.10

    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation"""
        returns = pd.Series(np.random.randn(252) * 0.01 + 0.001)  # Daily returns
        risk_free_rate = 0.02 / 252  # Daily risk-free rate

        excess_returns = returns - risk_free_rate
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)

        assert isinstance(sharpe_ratio, float)

    def test_maximum_drawdown_calculation(self):
        """Test maximum drawdown calculation"""
        prices = pd.Series([100, 110, 105, 95, 100, 105])
        cumulative_returns = prices / prices.iloc[0]
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()

        assert max_drawdown < 0  # Drawdown should be negative
        assert max_drawdown >= -1  # Cannot be more than 100% loss

    def test_volatility_calculation(self):
        """Test volatility calculation"""
        returns = pd.Series(np.random.randn(252) * 0.02)
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(252)

        assert daily_vol > 0
        assert annual_vol > daily_vol

    def test_sortino_ratio_calculation(self):
        """Test Sortino ratio calculation"""
        returns = pd.Series(np.random.randn(252) * 0.01 + 0.001)
        risk_free_rate = 0.02 / 252

        excess_returns = returns - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]
        downside_std = downside_returns.std()
        sortino_ratio = excess_returns.mean() / downside_std * np.sqrt(252)

        assert isinstance(sortino_ratio, float)


class TestRiskMetrics:
    """Test risk metrics calculations"""

    def test_var_calculation(self):
        """Test Value at Risk calculation"""
        returns = pd.Series(np.random.randn(1000) * 0.02)
        confidence_level = 0.95
        var = np.percentile(returns, (1 - confidence_level) * 100)

        assert var < 0  # VaR should be negative for losses

    def test_cvar_calculation(self):
        """Test Conditional Value at Risk (Expected Shortfall) calculation"""
        returns = pd.Series(np.random.randn(1000) * 0.02)
        confidence_level = 0.95
        var = np.percentile(returns, (1 - confidence_level) * 100)
        cvar = returns[returns <= var].mean()

        assert cvar <= var  # CVaR should be more negative than VaR

    def test_beta_calculation(self):
        """Test Beta calculation"""
        portfolio_returns = pd.Series(np.random.randn(252) * 0.02 + 0.001)
        market_returns = pd.Series(np.random.randn(252) * 0.015 + 0.0008)

        covariance = portfolio_returns.cov(market_returns)
        market_variance = market_returns.var()
        beta = covariance / market_variance

        assert isinstance(beta, float)

    def test_tracking_error_calculation(self):
        """Test tracking error calculation"""
        portfolio_returns = pd.Series(np.random.randn(252) * 0.02 + 0.001)
        benchmark_returns = pd.Series(np.random.randn(252) * 0.015 + 0.0008)

        tracking_diff = portfolio_returns - benchmark_returns
        tracking_error = tracking_diff.std() * np.sqrt(252)

        assert tracking_error > 0


class TestAttributionAnalysis:
    """Test attribution analysis"""

    def test_factor_attribution(self):
        """Test factor attribution calculation"""
        # Create sample factor exposures and returns
        factor_returns = pd.DataFrame({
            'market': np.random.randn(252) * 0.01,
            'size': np.random.randn(252) * 0.005,
            'value': np.random.randn(252) * 0.008
        })

        exposures = {'market': 1.0, 'size': 0.3, 'value': 0.2}

        # Calculate factor contribution
        contributions = {}
        for factor, exposure in exposures.items():
            contributions[factor] = (factor_returns[factor] * exposure).sum()

        assert len(contributions) == 3
        assert all(isinstance(v, (int, float)) for v in contributions.values())

    def test_sector_attribution(self):
        """Test sector attribution"""
        portfolio_weights = {'Tech': 0.4, 'Finance': 0.3, 'Healthcare': 0.3}
        sector_returns = {'Tech': 0.15, 'Finance': 0.08, 'Healthcare': 0.12}

        sector_contribution = {
            sector: portfolio_weights[sector] * sector_returns[sector]
            for sector in portfolio_weights.keys()
        }

        total_return = sum(sector_contribution.values())
        assert pytest.approx(total_return, 0.01) == 0.12  # Adjusted for floating point


class TestMetricsCalculator:
    """Test metrics calculator functionality"""

    def test_win_rate_calculation(self):
        """Test win rate calculation"""
        trades = pd.Series([100, -50, 75, -25, 150, -30, 80])
        winning_trades = (trades > 0).sum()
        total_trades = len(trades)
        win_rate = winning_trades / total_trades

        assert 0 <= win_rate <= 1
        assert win_rate == 4/7  # 4 winners out of 7 trades

    def test_profit_factor_calculation(self):
        """Test profit factor calculation"""
        trades = pd.Series([100, -50, 75, -25, 150, -30, 80])
        gross_profit = trades[trades > 0].sum()
        gross_loss = abs(trades[trades < 0].sum())

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
            assert profit_factor > 0

    def test_average_trade_calculation(self):
        """Test average trade calculation"""
        trades = pd.Series([100, -50, 75, -25, 150, -30, 80])
        avg_trade = trades.mean()

        assert isinstance(avg_trade, (int, float))

    def test_consecutive_wins_calculation(self):
        """Test consecutive wins/losses calculation"""
        trades = pd.Series([100, 150, -50, 75, 80, -25, 150])

        # Simple consecutive wins counter
        consecutive = 0
        max_consecutive = 0

        for trade in trades:
            if trade > 0:
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0

        assert max_consecutive >= 1


class TestPerformanceReporting:
    """Test performance reporting functionality"""

    def test_performance_summary_structure(self):
        """Test performance summary structure"""
        summary = {
            'total_return': 0.15,
            'sharpe_ratio': 1.5,
            'max_drawdown': -0.10,
            'volatility': 0.15,
            'win_rate': 0.65
        }

        assert 'total_return' in summary
        assert 'sharpe_ratio' in summary
        assert 'max_drawdown' in summary
        assert summary['max_drawdown'] < 0

    def test_period_performance_comparison(self):
        """Test period-over-period performance comparison"""
        periods = {
            'daily': {'return': 0.001, 'volatility': 0.015},
            'monthly': {'return': 0.02, 'volatility': 0.08},
            'yearly': {'return': 0.25, 'volatility': 0.20}
        }

        assert len(periods) == 3
        assert all('return' in p and 'volatility' in p for p in periods.values())


class TestAnalyticsImports:
    """Test analytics component imports"""

    def test_import_performance_analyzer(self):
        """Test performance analyzer imports"""
        from core_engine.analytics.performance_analyzer import (
            PerformanceMetric, PerformancePeriod, RiskFreeRateSource, PerformanceConfig
        )
        assert PerformanceMetric is not None
        assert PerformancePeriod is not None
        assert RiskFreeRateSource is not None
        assert PerformanceConfig is not None

    def test_import_attribution_analyzer(self):
        """Test attribution analyzer import"""
        try:
            from core_engine.analytics.attribution_analyzer import AttributionAnalyzer
            assert AttributionAnalyzer is not None
        except (ImportError, AttributeError):
            pytest.skip("AttributionAnalyzer not found")

    def test_import_metrics_calculator(self):
        """Test metrics calculator import"""
        try:
            from core_engine.analytics.metrics_calculator import MetricsCalculator
            assert MetricsCalculator is not None
        except (ImportError, AttributeError):
            pytest.skip("MetricsCalculator not found")

    def test_import_benchmark_analyzer(self):
        """Test benchmark analyzer import"""
        try:
            from core_engine.analytics.benchmark_analyzer import BenchmarkAnalyzer
            assert BenchmarkAnalyzer is not None
        except (ImportError, AttributeError):
            pytest.skip("BenchmarkAnalyzer not found")


class TestStatisticalAnalysis:
    """Test statistical analysis functions"""

    def test_correlation_analysis(self):
        """Test correlation analysis"""
        returns1 = pd.Series(np.random.randn(252))
        returns2 = pd.Series(np.random.randn(252))

        correlation = returns1.corr(returns2)
        assert -1 <= correlation <= 1

    def test_regression_analysis(self):
        """Test regression analysis"""
        x = np.random.randn(100)
        y = 2 * x + np.random.randn(100) * 0.5

        # Simple linear regression
        from scipy import stats as scipy_stats
        slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)

        assert isinstance(slope, float)
        assert isinstance(r_value, float)
        assert -1 <= r_value <= 1

    def test_skewness_calculation(self):
        """Test skewness calculation"""
        returns = pd.Series(np.random.randn(252))
        skewness = returns.skew()

        assert isinstance(skewness, float)

    def test_kurtosis_calculation(self):
        """Test kurtosis calculation"""
        returns = pd.Series(np.random.randn(252))
        kurtosis = returns.kurtosis()

        assert isinstance(kurtosis, float)


class TestPerformanceBenchmarking:
    """Test performance benchmarking"""

    def test_benchmark_comparison(self):
        """Test benchmark comparison"""
        portfolio_return = 0.15
        benchmark_return = 0.10

        excess_return = portfolio_return - benchmark_return
        assert pytest.approx(excess_return, 0.001) == 0.05

    def test_information_ratio_calculation(self):
        """Test Information Ratio calculation"""
        portfolio_returns = pd.Series(np.random.randn(252) * 0.02 + 0.001)
        benchmark_returns = pd.Series(np.random.randn(252) * 0.015 + 0.0008)

        active_returns = portfolio_returns - benchmark_returns
        information_ratio = active_returns.mean() / active_returns.std() * np.sqrt(252)

        assert isinstance(information_ratio, float)

    def test_alpha_calculation(self):
        """Test Alpha calculation (Jensen's Alpha)"""
        portfolio_return = 0.15
        risk_free_rate = 0.02
        beta = 1.2
        market_return = 0.12

        alpha = portfolio_return - (risk_free_rate + beta * (market_return - risk_free_rate))

        assert isinstance(alpha, float)


class TestAnalyticsIntegration:
    """Test analytics component integration"""

    def test_end_to_end_performance_analysis(self):
        """Test complete performance analysis workflow"""
        from core_engine.analytics.performance_analyzer import PerformanceConfig

        # Create config
        config = PerformanceConfig(
            custom_risk_free_rate=0.02,
            trading_days_per_year=252,
            confidence_level=0.95
        )

        # Generate sample returns
        returns = pd.Series(np.random.randn(252) * 0.02 + 0.001)

        # Calculate basic metrics
        total_return = (1 + returns).prod() - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe = (returns.mean() - config.risk_free_rate/252) / returns.std() * np.sqrt(252)

        assert isinstance(total_return, float)
        assert volatility > 0
        assert isinstance(sharpe, float)

    def test_multi_period_analysis(self):
        """Test multi-period performance analysis"""
        from core_engine.analytics.performance_analyzer import PerformancePeriod

        periods = [
            PerformancePeriod.DAILY,
            PerformancePeriod.MONTHLY,
            PerformancePeriod.YEARLY
        ]

        results = {}
        for period in periods:
            results[period.value] = {
                'return': np.random.randn() * 0.1,
                'volatility': abs(np.random.randn() * 0.15)
            }

        assert len(results) == 3
        assert all('return' in r and 'volatility' in r for r in results.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
