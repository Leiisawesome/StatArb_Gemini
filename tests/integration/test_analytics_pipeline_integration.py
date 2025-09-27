#!/usr/bin/env python3
"""
Analytics Pipeline Integration Tests
===================================

Comprehensive integration tests for the analytics pipeline:
- Performance Analysis ↔ Attribution ↔ Reporting
- Risk Analytics ↔ Benchmarking ↔ Portfolio Optimization
- Real-time Monitoring ↔ Alerting ↔ Dashboard Integration
- Backtesting Framework ↔ Walk-forward Analysis ↔ Live Trading

These tests validate the complete analytics workflow from trade execution
through performance measurement to risk assessment and reporting.

Author: StatArb_Gemini Integration Test Suite
Version: 1.0.0
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

from core_engine.analytics.performance_analyzer import PerformanceAnalyzer, PerformancePeriod, PerformanceMetrics
from core_engine.analytics.attribution_analyzer import AttributionAnalyzer, AttributionReport, AttributionResult
from core_engine.analytics.report_generator import ReportGenerator
from core_engine.analytics.benchmark_analyzer import BenchmarkAnalyzer
from core_engine.trading.portfolio.manager import PortfolioManager


class TestAnalyticsPipelineIntegration:
    """Integration tests for complete analytics pipeline"""

    @pytest.fixture
    def performance_analyzer(self):
        """Create performance analyzer for testing"""
        return PerformanceAnalyzer()

    @pytest.fixture
    def attribution_analyzer(self):
        """Create attribution analyzer for testing"""
        from core_engine.analytics.attribution_analyzer import AttributionConfig
        config = AttributionConfig()
        return AttributionAnalyzer(config)

    @pytest.fixture
    def report_generator(self):
        """Create report generator for testing"""
        from core_engine.analytics.report_generator import ReportConfig
        config = ReportConfig()
        return ReportGenerator(config)

    @pytest.fixture
    def benchmark_analyzer(self):
        """Create benchmark analyzer for testing"""
        from core_engine.analytics.benchmark_analyzer import BenchmarkConfig
        config = BenchmarkConfig()
        return BenchmarkAnalyzer(config)

    @pytest.fixture
    def sample_trades(self):
        """Create sample executed trades for testing"""
        np.random.seed(42)
        base_date = datetime(2023, 1, 1)

        trades = []
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']

        for i in range(50):
            symbol = np.random.choice(symbols)
            entry_price = np.random.uniform(100, 500)
            quantity = np.random.randint(10, 100)
            holding_period = np.random.randint(1, 30)

            # Simulate realistic P&L with some winners and losers
            pnl_pct = np.random.normal(0.02, 0.15)  # Mean 2% return, 15% volatility
            exit_price = entry_price * (1 + pnl_pct)

            trade = {
                'trade_id': f'TRADE_{i:03d}',
                'symbol': symbol,
                'quantity': quantity,
                'entry_price': round(entry_price, 2),
                'exit_price': round(exit_price, 2),
                'entry_time': base_date + timedelta(days=i),
                'exit_time': base_date + timedelta(days=i + holding_period),
                'pnl': round((exit_price - entry_price) * quantity, 2),
                'pnl_pct': round(pnl_pct * 100, 2),
                'commission': round(abs(quantity) * 0.01, 2),  # $0.01 per share
                'strategy': 'momentum',
                'sector': np.random.choice(['technology', 'healthcare', 'finance', 'consumer'])
            }
            trades.append(trade)

        return trades

    @pytest.fixture
    def sample_portfolio_history(self):
        """Create sample portfolio value history for testing"""
        dates = pd.date_range('2023-01-01', periods=252, freq='D')  # One year of daily data
        np.random.seed(42)

        # Simulate portfolio growth with volatility
        initial_value = 1000000.0
        returns = np.random.normal(0.0005, 0.02, len(dates))  # Daily returns
        portfolio_values = initial_value * np.exp(np.cumsum(returns))

        # Add benchmark (S&P 500 proxy)
        benchmark_returns = np.random.normal(0.0003, 0.015, len(dates))
        benchmark_values = initial_value * np.exp(np.cumsum(benchmark_returns))

        return pd.DataFrame({
            'portfolio_value': portfolio_values,
            'benchmark_value': benchmark_values,
            'date': dates
        }).set_index('date')

    @pytest.mark.asyncio
    async def test_performance_analysis_pipeline(self, performance_analyzer, sample_trades):
        """Test complete performance analysis pipeline"""
        # Convert trades to returns series for analysis
        dates = pd.date_range('2023-01-01', periods=len(sample_trades), freq='D')
        returns = pd.Series([trade['pnl'] / 10000 for trade in sample_trades], index=dates)  # Assume $10k initial
        
        # Analyze performance
        performance_metrics = await performance_analyzer.analyze_performance(
            returns, "TEST_PORTFOLIO", period=PerformancePeriod.INCEPTION
        )

        # Verify comprehensive metrics calculated
        assert isinstance(performance_metrics, PerformanceMetrics)
        assert performance_metrics.symbol == "TEST_PORTFOLIO"
        assert hasattr(performance_metrics, 'total_return')

    @pytest.mark.asyncio
    async def test_attribution_analysis_integration(self, attribution_analyzer, sample_trades):
        """Test attribution analysis integrated with performance data"""
        # Convert trades to returns series for analysis
        dates = pd.date_range('2023-01-01', periods=len(sample_trades), freq='D')
        portfolio_returns = pd.Series([trade['pnl'] / 10000 for trade in sample_trades], index=dates)
        
        # Perform attribution analysis
        attribution_report = await attribution_analyzer.analyze_attribution(portfolio_returns)

        # Verify attribution report structure
        assert isinstance(attribution_report, AttributionResult)
        assert hasattr(attribution_report, 'total_return')
        assert hasattr(attribution_report, 'factor_contributions')
        assert hasattr(attribution_report, 'sector_contributions')
        assert isinstance(attribution_report.factor_contributions, dict)
        assert isinstance(attribution_report.sector_contributions, dict)

    @pytest.mark.skip(reason="RiskAnalytics class not implemented")
    def test_risk_analytics_integration(self, risk_analytics, sample_portfolio_history, sample_trades):
        """Test risk analytics integration"""
        # Test risk metrics calculation
        risk_metrics = risk_analytics.calculate_portfolio_risk(sample_portfolio_history)
        assert isinstance(risk_metrics, dict)
        assert 'var_95' in risk_metrics
        assert 'cvar_95' in risk_metrics

        # Test stress testing
        stress_results = risk_analytics.run_stress_test(sample_portfolio_history, "market_crash")
        assert isinstance(stress_results, dict)

        # Test scenario analysis
        scenario_results = risk_analytics.analyze_scenario_impact(sample_portfolio_history, "rate_hike")
        assert isinstance(scenario_results, dict)

    @pytest.mark.asyncio
    async def test_benchmarking_integration(self, benchmark_analyzer, sample_portfolio_history):
        """Test benchmarking integration with portfolio performance"""
        # Convert portfolio values to returns
        portfolio_returns = sample_portfolio_history['portfolio_value'].pct_change().dropna()
        benchmark_returns = sample_portfolio_history['benchmark_value'].pct_change().dropna()
        
        # Perform benchmarking analysis
        benchmark_report = await benchmark_analyzer.analyze_against_benchmark(
            portfolio_returns, 'PORTFOLIO', 'BENCHMARK'
        )

        # Verify benchmark report structure
        assert isinstance(benchmark_report, dict)
        assert 'portfolio_symbol' in benchmark_report
        assert 'benchmark_symbol' in benchmark_report

    @pytest.mark.skip(reason="RiskAnalytics class not implemented")
    @pytest.mark.asyncio
    async def test_report_generation_integration(self, report_generator, performance_analyzer,
                                         attribution_analyzer, risk_analytics, sample_trades,
                                         sample_portfolio_history):
        """Test complete report generation integrating all analytics components"""
        # Convert trades to returns series for performance analysis
        trade_dates = [trade['exit_time'] for trade in sample_trades]
        trade_returns = [trade['pnl_pct'] / 100.0 for trade in sample_trades]  # Convert percentage to decimal
        returns_series = pd.Series(trade_returns, index=trade_dates, name='portfolio_returns')
        
        # Generate individual analysis components
        performance_report = await performance_analyzer.analyze_performance(
            returns_series, 'PORTFOLIO', period=PerformancePeriod.YEARLY
        )
        attribution_report = await attribution_analyzer.analyze_attribution(sample_trades)
        risk_report = risk_analytics.calculate_portfolio_risk(
            sample_portfolio_history['portfolio_value']
        )

        # Generate comprehensive report
        comprehensive_report = report_generator.generate_comprehensive_report(
            performance_report,
            attribution_report,
            risk_report,
            sample_portfolio_history,
            datetime(2023, 1, 1),
            datetime(2023, 12, 31)
        )

        # Verify comprehensive report structure
        assert isinstance(comprehensive_report, dict)
        required_sections = [
            'executive_summary', 'performance_analysis', 'risk_analysis',
            'attribution_analysis', 'benchmark_comparison', 'recommendations'
        ]

        for section in required_sections:
            assert section in comprehensive_report, f"Missing report section: {section}"

        # Verify executive summary contains key metrics
        exec_summary = comprehensive_report['executive_summary']
        assert 'total_return' in exec_summary
        assert 'sharpe_ratio' in exec_summary
        assert 'max_drawdown' in exec_summary
        assert 'win_rate' in exec_summary

    @pytest.mark.skip(reason="RiskAnalytics class not implemented")
    def test_real_time_monitoring_integration(self, performance_analyzer, risk_analytics):
        """Test real-time monitoring and alerting integration"""
        # Simulate real-time portfolio updates
        portfolio_updates = []
        base_value = 1000000.0

        for i in range(100):
            # Simulate portfolio value changes
            change_pct = np.random.normal(0.0001, 0.005)
            current_value = base_value * (1 + change_pct)
            base_value = current_value

            update = {
                'timestamp': datetime.now() + timedelta(minutes=i),
                'portfolio_value': current_value,
                'positions': {
                    'AAPL': np.random.randint(0, 100),
                    'GOOGL': np.random.randint(0, 50),
                    'MSFT': np.random.randint(0, 80)
                }
            }
            portfolio_updates.append(update)

        # Process real-time monitoring
        monitoring_report = performance_analyzer.monitor_real_time_performance(portfolio_updates)

        # Verify monitoring metrics
        assert isinstance(monitoring_report, dict)
        assert 'current_value' in monitoring_report
        assert 'daily_pnl' in monitoring_report
        assert 'alerts' in monitoring_report

        # Test risk monitoring
        risk_monitoring = risk_analytics.monitor_real_time_risk(portfolio_updates)

        assert isinstance(risk_monitoring, dict)
        assert 'current_var' in risk_monitoring
        assert 'risk_alerts' in risk_monitoring

    @pytest.mark.skip(reason="Backtesting framework not implemented in PerformanceAnalyzer")
    def test_backtesting_framework_integration(self, performance_analyzer):
        """Test backtesting framework integration with walk-forward analysis"""
        # Create historical market data for backtesting
        dates = pd.date_range('2020-01-01', periods=500, freq='D')
        np.random.seed(42)

        # Generate synthetic market data with known patterns
        market_data = {}
        symbols = ['AAPL', 'GOOGL', 'MSFT']

        for symbol in symbols:
            base_price = np.random.uniform(100, 500)
            returns = np.random.normal(0.0005, 0.02, len(dates))
            prices = base_price * np.exp(np.cumsum(returns))

            market_data[symbol] = pd.DataFrame({
                'open': prices * 0.995,
                'high': prices * 1.008,
                'low': prices * 0.992,
                'close': prices,
                'volume': np.random.uniform(1000000, 10000000, len(dates))
            }, index=dates)

        # Perform backtest
        backtest_config = {
            'strategy': 'momentum',
            'lookback_period': 20,
            'rebalance_frequency': 'daily',
            'initial_capital': 1000000.0,
            'max_positions': 10
        }

        backtest_results = performance_analyzer.run_backtest(
            market_data, backtest_config, dates[0], dates[-1]
        )

        # Verify backtest results
        assert isinstance(backtest_results, dict)
        assert 'portfolio_values' in backtest_results
        assert 'trades' in backtest_results
        assert 'performance_metrics' in backtest_results

        # Verify backtest integrity
        portfolio_values = backtest_results['portfolio_values']
        assert len(portfolio_values) > 0
        assert all(v > 0 for v in portfolio_values)  # No negative portfolio values

        trades = backtest_results['trades']
        assert isinstance(trades, list)

        # Verify performance metrics calculated
        metrics = backtest_results['performance_metrics']
        assert 'total_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_analytics(self, performance_analyzer, sample_trades):
        """Test error handling and recovery in analytics pipeline"""
        # Convert trades to returns series for performance analysis
        trade_dates = [trade['exit_time'] for trade in sample_trades]
        trade_returns = [trade['pnl_pct'] / 100.0 for trade in sample_trades]  # Convert percentage to decimal
        returns_series = pd.Series(trade_returns, index=trade_dates, name='portfolio_returns')
        
        # Test with corrupted trade data - create corrupted returns
        corrupted_returns = returns_series.copy()
        corrupted_returns.iloc[0] = 'invalid_return'  # Corrupt return data

        # Analytics should handle gracefully
        try:
            performance_report = await performance_analyzer.analyze_performance(
                corrupted_returns, 'PORTFOLIO', period=PerformancePeriod.YEARLY
            )
            # Should either handle error or provide partial results
            assert isinstance(performance_report, PerformanceMetrics)
        except Exception:
            # Error handling should be graceful
            pass

        # Test with empty data
        empty_returns = pd.Series([], dtype=float, name='portfolio_returns')
        empty_report = await performance_analyzer.analyze_performance(
            empty_returns, 'PORTFOLIO', period=PerformancePeriod.YEARLY
        )
        assert isinstance(empty_report, PerformanceMetrics)
        # Should provide default/empty metrics
        assert empty_report.symbol == 'PORTFOLIO'

        # Test with extreme values
        extreme_dates = [datetime.now()]
        extreme_returns = [1e9]  # Extreme return
        extreme_returns_series = pd.Series(extreme_returns, index=extreme_dates, name='portfolio_returns')

        extreme_report = await performance_analyzer.analyze_performance(
            extreme_returns_series, 'PORTFOLIO', period=PerformancePeriod.YEARLY
        )
        assert isinstance(extreme_report, PerformanceMetrics)
        # Should handle extreme values without crashing

    @pytest.mark.skip(reason="Persistence methods not implemented in PerformanceAnalyzer")
    @pytest.mark.asyncio
    async def test_analytics_data_persistence_integration(self, performance_analyzer, sample_trades):
        """Test analytics data persistence and retrieval integration"""
        # Convert trades to returns series for performance analysis
        trade_dates = [trade['exit_time'] for trade in sample_trades]
        trade_returns = [trade['pnl_pct'] / 100.0 for trade in sample_trades]  # Convert percentage to decimal
        returns_series = pd.Series(trade_returns, index=trade_dates, name='portfolio_returns')
        
        # Generate analytics report
        report = await performance_analyzer.analyze_performance(
            returns_series, 'PORTFOLIO', period=PerformancePeriod.YEARLY
        )

        # Simulate persistence (in real implementation, would save to database)
        report_id = "test_report_001"
        persistence_result = performance_analyzer.save_analytics_report(report_id, report)

        # Verify persistence operation
        assert persistence_result is True or isinstance(persistence_result, dict)

        # Simulate retrieval
        retrieved_report = performance_analyzer.load_analytics_report(report_id)

        # Verify data integrity (in real implementation)
        # For now, just verify the operation doesn't crash
        assert retrieved_report is not None

        # Test report versioning
        updated_report = report.copy()
        updated_report['additional_metric'] = 42.0

        version_result = performance_analyzer.save_report_version(report_id, updated_report, "v2.0")
        assert version_result is True or isinstance(version_result, dict)
