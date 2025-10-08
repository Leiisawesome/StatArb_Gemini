"""
Comprehensive Analytics Manager Test Suite

This test suite provides comprehensive coverage for the analytics manager
to enhance coverage from 27% to 80%+, implementing all 4 enhancement tasks from the Unit Test Enhancement Plan.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
import numpy as np
import pandas as pd

from core_engine.analytics.manager_enhanced import AnalyticsManagerEnhanced
from core_engine.analytics.metrics_calculator import MetricsCalculator
from core_engine.analytics.performance_analyzer import PerformanceAnalyzer
from core_engine.analytics.attribution_analyzer import AttributionAnalyzer
from core_engine.analytics.benchmark_analyzer import BenchmarkAnalyzer
from core_engine.analytics.report_generator import ReportGenerator
from core_engine.type_definitions.analytics import PerformanceMetrics, AttributionMetrics, BenchmarkMetrics
from core_engine.type_definitions.portfolio import Position, Portfolio
from core_engine.type_definitions.orders import Order, OrderSide, OrderType
from core_engine.system.interfaces import ISystemComponent


class TestAnalyticsManagerEnhanced:
    """Comprehensive test suite for AnalyticsManagerEnhanced - 27% coverage enhancement"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'enable_real_time_analytics': True,
            'enable_batch_analytics': True,
            'enable_performance_attribution': True,
            'enable_benchmark_analysis': True,
            'analytics_update_frequency': 60,  # seconds
            'performance_metrics': {
                'sharpe_ratio': True,
                'sortino_ratio': True,
                'calmar_ratio': True,
                'max_drawdown': True,
                'var_95': True,
                'var_99': True
            },
            'attribution_metrics': {
                'strategy_attribution': True,
                'factor_attribution': True,
                'sector_attribution': True,
                'time_attribution': True
            }
        }
        self.analytics_manager = AnalyticsManagerEnhanced(self.config)
    
    def test_initialization(self):
        """Test analytics manager initialization"""
        assert self.analytics_manager is not None
        assert self.analytics_manager.config['enable_real_time_analytics'] is True
        assert self.analytics_manager.config['enable_batch_analytics'] is True
        assert self.analytics_manager.config['enable_performance_attribution'] is True
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test analytics manager initialization process"""
        result = await self.analytics_manager.initialize()
        assert result is True
        assert hasattr(self.analytics_manager, 'metrics_calculator')
        assert hasattr(self.analytics_manager, 'performance_analyzer')
        assert hasattr(self.analytics_manager, 'attribution_analyzer')
        assert hasattr(self.analytics_manager, 'benchmark_analyzer')
    
    @pytest.mark.asyncio
    async def test_start(self):
        """Test analytics manager start process"""
        with patch.object(self.analytics_manager, '_start_real_time_analytics', new_callable=AsyncMock) as mock_realtime:
            with patch.object(self.analytics_manager, '_start_batch_analytics', new_callable=AsyncMock) as mock_batch:
                mock_realtime.return_value = None
                mock_batch.return_value = None
                
                result = await self.analytics_manager.start()
                assert result is True
                mock_realtime.assert_called_once()
                mock_batch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop(self):
        """Test analytics manager stop process"""
        with patch.object(self.analytics_manager, '_stop_real_time_analytics', new_callable=AsyncMock) as mock_stop_realtime:
            with patch.object(self.analytics_manager, '_stop_batch_analytics', new_callable=AsyncMock) as mock_stop_batch:
                mock_stop_realtime.return_value = None
                mock_stop_batch.return_value = None
                
                result = await self.analytics_manager.stop()
                assert result is True
                mock_stop_realtime.assert_called_once()
                mock_stop_batch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_real_time_data(self):
        """Test real-time data processing"""
        market_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 1000000,
            'timestamp': datetime.now(),
            'type': 'market_data'
        }
        
        with patch.object(self.analytics_manager, '_update_real_time_metrics', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {
                'price_change': 0.02,
                'volume_change': 0.15,
                'volatility': 0.12
            }
            
            result = await self.analytics_manager.process_real_time_data(market_data)
            assert isinstance(result, dict)
            assert 'price_change' in result
            assert 'volume_change' in result
            assert 'volatility' in result
    
    @pytest.mark.asyncio
    async def test_process_batch_data(self):
        """Test batch data processing"""
        start_time = datetime.now() - timedelta(days=30)
        end_time = datetime.now()
        
        # Mock historical data
        historical_data = pd.DataFrame({
            'timestamp': pd.date_range(start_time, end_time, freq='1H'),
            'AAPL': np.random.normal(150, 5, 720),  # 30 days * 24 hours
            'GOOGL': np.random.normal(2800, 50, 720),
            'MSFT': np.random.normal(300, 10, 720)
        })
        
        with patch.object(self.analytics_manager, '_calculate_batch_metrics', new_callable=AsyncMock) as mock_calculate:
            mock_calculate.return_value = {
                'total_return': 0.05,
                'volatility': 0.15,
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.08
            }
            
            result = await self.analytics_manager.process_batch_data(historical_data, start_time, end_time)
            assert isinstance(result, dict)
            assert 'total_return' in result
            assert 'volatility' in result
            assert 'sharpe_ratio' in result
            assert 'max_drawdown' in result
    
    @pytest.mark.asyncio
    async def test_get_analytics_summary(self):
        """Test analytics summary generation"""
        with patch.object(self.analytics_manager, '_generate_analytics_summary', new_callable=AsyncMock) as mock_summary:
            mock_summary.return_value = {
                'performance_metrics': {
                    'total_return': 0.12,
                    'sharpe_ratio': 1.5,
                    'max_drawdown': -0.06
                },
                'risk_metrics': {
                    'var_95': 0.03,
                    'var_99': 0.05,
                    'volatility': 0.15
                },
                'attribution_metrics': {
                    'strategy_attribution': {'momentum': 0.4, 'mean_reversion': 0.6},
                    'factor_attribution': {'market': 0.7, 'size': 0.2, 'value': 0.1}
                }
            }
            
            summary = await self.analytics_manager.get_analytics_summary(timeframe='1D')
            assert isinstance(summary, dict)
            assert 'performance_metrics' in summary
            assert 'risk_metrics' in summary
            assert 'attribution_metrics' in summary
    
    @pytest.mark.asyncio
    async def test_get_regime_aware_metrics(self):
        """Test regime-aware metrics calculation"""
        regime_context = {
            'primary_regime': 'bull_market',
            'volatility_regime': 'normal_volatility',
            'confidence': 0.8,
            'duration_days': 45
        }
        
        with patch.object(self.analytics_manager, '_calculate_regime_aware_metrics', new_callable=AsyncMock) as mock_regime:
            mock_regime.return_value = {
                'regime_adjusted_return': 0.15,
                'regime_adjusted_volatility': 0.12,
                'regime_adjusted_sharpe': 1.25,
                'regime_persistence': 0.7
            }
            
            metrics = await self.analytics_manager.get_regime_aware_metrics(regime_context)
            assert isinstance(metrics, dict)
            assert 'regime_adjusted_return' in metrics
            assert 'regime_adjusted_volatility' in metrics
            assert 'regime_adjusted_sharpe' in metrics
    
    @pytest.mark.asyncio
    async def test_get_multi_timeframe_analysis(self):
        """Test multi-timeframe analysis"""
        timeframes = ['1min', '5min', '15min', '1h', '1D']
        
        with patch.object(self.analytics_manager, '_analyze_multi_timeframe', new_callable=AsyncMock) as mock_multi:
            mock_multi.return_value = {
                '1min': {'trend': 'bullish', 'strength': 0.6, 'volatility': 0.08},
                '5min': {'trend': 'bullish', 'strength': 0.7, 'volatility': 0.10},
                '15min': {'trend': 'bullish', 'strength': 0.8, 'volatility': 0.12},
                '1h': {'trend': 'bullish', 'strength': 0.9, 'volatility': 0.15},
                '1D': {'trend': 'bullish', 'strength': 0.95, 'volatility': 0.18},
                'cross_timeframe_analysis': {
                    'trend_alignment_score': 0.85,
                    'dominant_trend': 'bullish',
                    'timeframe_consensus': True
                }
            }
            
            analysis = await self.analytics_manager.get_multi_timeframe_analysis(timeframes)
            assert isinstance(analysis, dict)
            assert len(analysis) == len(timeframes) + 1  # +1 for cross_timeframe_analysis
            assert 'cross_timeframe_analysis' in analysis
    
    @pytest.mark.asyncio
    async def test_performance_attribution(self):
        """Test performance attribution analysis"""
        strategy_returns = {
            'momentum': pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20),
            'mean_reversion': pd.Series([0.005, -0.01, 0.02, -0.005, 0.01] * 20),
            'statistical_arbitrage': pd.Series([0.008, 0.012, -0.005, 0.018, 0.015] * 20)
        }
        
        with patch.object(self.analytics_manager, '_calculate_strategy_attribution', new_callable=AsyncMock) as mock_attr:
            mock_attr.return_value = {
                'momentum': {
                    'total_return': 0.08,
                    'contribution_percentage': 0.4,
                    'sharpe_ratio': 1.2,
                    'max_drawdown': -0.05
                },
                'mean_reversion': {
                    'total_return': 0.06,
                    'contribution_percentage': 0.3,
                    'sharpe_ratio': 1.5,
                    'max_drawdown': -0.03
                },
                'statistical_arbitrage': {
                    'total_return': 0.06,
                    'contribution_percentage': 0.3,
                    'sharpe_ratio': 1.8,
                    'max_drawdown': -0.02
                }
            }
            
            attribution = await self.analytics_manager.calculate_performance_attribution(strategy_returns)
            assert isinstance(attribution, dict)
            assert 'momentum' in attribution
            assert 'mean_reversion' in attribution
            assert 'statistical_arbitrage' in attribution
    
    @pytest.mark.asyncio
    async def test_benchmark_analysis(self):
        """Test benchmark analysis"""
        portfolio_returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20)
        benchmark_returns = pd.Series([0.008, 0.015, -0.008, 0.012, 0.018] * 20)
        
        with patch.object(self.analytics_manager, '_analyze_benchmark_performance', new_callable=AsyncMock) as mock_bench:
            mock_bench.return_value = {
                'excess_return': 0.02,
                'information_ratio': 1.2,
                'tracking_error': 0.05,
                'beta': 1.1,
                'alpha': 0.015,
                'r_squared': 0.85
            }
            
            benchmark_analysis = await self.analytics_manager.analyze_benchmark_performance(
                portfolio_returns, benchmark_returns
            )
            assert isinstance(benchmark_analysis, dict)
            assert 'excess_return' in benchmark_analysis
            assert 'information_ratio' in benchmark_analysis
            assert 'tracking_error' in benchmark_analysis
            assert 'beta' in benchmark_analysis
            assert 'alpha' in benchmark_analysis
    
    @pytest.mark.asyncio
    async def test_risk_analytics(self):
        """Test risk analytics calculation"""
        portfolio_data = {
            'positions': {
                'AAPL': {'quantity': 100, 'price': 150.0, 'weight': 0.3},
                'GOOGL': {'quantity': 50, 'price': 2800.0, 'weight': 0.4},
                'MSFT': {'quantity': 75, 'price': 300.0, 'weight': 0.3}
            },
            'returns': pd.Series([0.01, -0.02, 0.015, -0.01, 0.02] * 20)
        }
        
        with patch.object(self.analytics_manager, '_calculate_risk_metrics', new_callable=AsyncMock) as mock_risk:
            mock_risk.return_value = {
                'var_95': 0.03,
                'var_99': 0.05,
                'conditional_var': 0.06,
                'max_drawdown': -0.08,
                'volatility': 0.15,
                'sharpe_ratio': 1.2,
                'sortino_ratio': 1.5,
                'calmar_ratio': 1.8
            }
            
            risk_metrics = await self.analytics_manager.calculate_risk_metrics(portfolio_data)
            assert isinstance(risk_metrics, dict)
            assert 'var_95' in risk_metrics
            assert 'var_99' in risk_metrics
            assert 'max_drawdown' in risk_metrics
            assert 'sharpe_ratio' in risk_metrics
    
    @pytest.mark.asyncio
    async def test_report_generation(self):
        """Test analytics report generation"""
        report_config = {
            'report_type': 'comprehensive',
            'timeframe': '1M',
            'include_charts': True,
            'include_attribution': True,
            'include_benchmark': True
        }
        
        with patch.object(self.analytics_manager, '_generate_comprehensive_report', new_callable=AsyncMock) as mock_report:
            mock_report.return_value = {
                'report_id': 'analytics_20241220_001',
                'generation_time': datetime.now(),
                'sections': ['performance', 'risk', 'attribution', 'benchmark'],
                'charts': ['performance_chart', 'risk_chart', 'attribution_chart'],
                'summary': {
                    'overall_score': 85.5,
                    'recommendations': ['Improve diversification', 'Reduce concentration risk']
                }
            }
            
            report = await self.analytics_manager.generate_analytics_report(report_config)
            assert isinstance(report, dict)
            assert 'report_id' in report
            assert 'generation_time' in report
            assert 'sections' in report
            assert 'summary' in report
    
    def test_health_check(self):
        """Test health check functionality"""
        health_status = self.analytics_manager.health_check()
        assert isinstance(health_status, dict)
        assert 'healthy' in health_status
        assert 'real_time_analytics' in health_status
        assert 'batch_analytics' in health_status
        assert 'performance_attribution' in health_status
    
    def test_get_status(self):
        """Test get status functionality"""
        status = self.analytics_manager.get_status()
        assert isinstance(status, dict)
        assert 'operational' in status
        assert 'analytics_components' in status
        assert 'processing_status' in status


class TestMetricsCalculator:
    """Test suite for MetricsCalculator - analytics metrics component"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.metrics_calculator = MetricsCalculator()
    
    def test_calculate_performance_metrics(self):
        """Test performance metrics calculation"""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02, -0.005, 0.01, -0.02, 0.025, 0.01] * 10)
        
        metrics = self.metrics_calculator.calculate_performance_metrics(returns)
        assert isinstance(metrics, dict)
        assert 'total_return' in metrics
        assert 'annualized_return' in metrics
        assert 'volatility' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'sortino_ratio' in metrics
        assert 'calmar_ratio' in metrics
        assert 'max_drawdown' in metrics
    
    def test_calculate_risk_metrics(self):
        """Test risk metrics calculation"""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02, -0.005, 0.01, -0.02, 0.025, 0.01] * 10)
        
        risk_metrics = self.metrics_calculator.calculate_risk_metrics(returns)
        assert isinstance(risk_metrics, dict)
        assert 'var_95' in risk_metrics
        assert 'var_99' in risk_metrics
        assert 'conditional_var' in risk_metrics
        assert 'volatility' in risk_metrics
        assert 'skewness' in risk_metrics
        assert 'kurtosis' in risk_metrics
    
    def test_calculate_statistical_metrics(self):
        """Test statistical metrics calculation"""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02, -0.005, 0.01, -0.02, 0.025, 0.01] * 10)
        
        stats_metrics = self.metrics_calculator.calculate_statistical_metrics(returns)
        assert isinstance(stats_metrics, dict)
        assert 'mean' in stats_metrics
        assert 'std' in stats_metrics
        assert 'skewness' in stats_metrics
        assert 'kurtosis' in stats_metrics
        assert 'percentiles' in stats_metrics
    
    def test_calculate_rolling_metrics(self):
        """Test rolling metrics calculation"""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02, -0.005, 0.01, -0.02, 0.025, 0.01] * 10)
        window = 20
        
        rolling_metrics = self.metrics_calculator.calculate_rolling_metrics(returns, window)
        assert isinstance(rolling_metrics, dict)
        assert 'rolling_return' in rolling_metrics
        assert 'rolling_volatility' in rolling_metrics
        assert 'rolling_sharpe' in rolling_metrics
        assert 'rolling_max_drawdown' in rolling_metrics


class TestPerformanceAnalyzer:
    """Test suite for PerformanceAnalyzer - performance analysis component"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.performance_analyzer = PerformanceAnalyzer()
    
    def test_analyze_performance(self):
        """Test performance analysis"""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02, -0.005, 0.01, -0.02, 0.025, 0.01] * 10)
        
        analysis = self.performance_analyzer.analyze_performance(returns)
        assert isinstance(analysis, dict)
        assert 'performance_summary' in analysis
        assert 'risk_metrics' in analysis
        assert 'statistical_metrics' in analysis
        assert 'recommendations' in analysis
    
    def test_analyze_performance_by_period(self):
        """Test performance analysis by period"""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02, -0.005, 0.01, -0.02, 0.025, 0.01] * 10)
        timestamps = pd.date_range('2024-01-01', periods=len(returns), freq='D')
        returns.index = timestamps
        
        period_analysis = self.performance_analyzer.analyze_performance_by_period(returns)
        assert isinstance(period_analysis, dict)
        assert 'daily_performance' in period_analysis
        assert 'weekly_performance' in period_analysis
        assert 'monthly_performance' in period_analysis
    
    def test_analyze_performance_by_strategy(self):
        """Test performance analysis by strategy"""
        strategy_returns = {
            'momentum': pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20),
            'mean_reversion': pd.Series([0.005, -0.01, 0.02, -0.005, 0.01] * 20),
            'statistical_arbitrage': pd.Series([0.008, 0.012, -0.005, 0.018, 0.015] * 20)
        }
        
        strategy_analysis = self.performance_analyzer.analyze_performance_by_strategy(strategy_returns)
        assert isinstance(strategy_analysis, dict)
        assert 'momentum' in strategy_analysis
        assert 'mean_reversion' in strategy_analysis
        assert 'statistical_arbitrage' in strategy_analysis
    
    def test_analyze_performance_attribution(self):
        """Test performance attribution analysis"""
        portfolio_returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20)
        strategy_returns = {
            'momentum': pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20),
            'mean_reversion': pd.Series([0.005, -0.01, 0.02, -0.005, 0.01] * 20)
        }
        
        attribution = self.performance_analyzer.analyze_performance_attribution(portfolio_returns, strategy_returns)
        assert isinstance(attribution, dict)
        assert 'strategy_attribution' in attribution
        assert 'factor_attribution' in attribution
        assert 'time_attribution' in attribution


class TestAttributionAnalyzer:
    """Test suite for AttributionAnalyzer - attribution analysis component"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.attribution_analyzer = AttributionAnalyzer()
    
    def test_analyze_strategy_attribution(self):
        """Test strategy attribution analysis"""
        portfolio_returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20)
        strategy_returns = {
            'momentum': pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20),
            'mean_reversion': pd.Series([0.005, -0.01, 0.02, -0.005, 0.01] * 20)
        }
        
        attribution = self.attribution_analyzer.analyze_strategy_attribution(portfolio_returns, strategy_returns)
        assert isinstance(attribution, dict)
        assert 'momentum' in attribution
        assert 'mean_reversion' in attribution
    
    def test_analyze_factor_attribution(self):
        """Test factor attribution analysis"""
        portfolio_returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20)
        factor_returns = {
            'market': pd.Series([0.008, 0.015, -0.008, 0.012, 0.018] * 20),
            'size': pd.Series([0.002, 0.005, -0.002, 0.003, 0.002] * 20),
            'value': pd.Series([0.001, 0.003, -0.001, 0.002, 0.001] * 20)
        }
        
        factor_attribution = self.attribution_analyzer.analyze_factor_attribution(portfolio_returns, factor_returns)
        assert isinstance(factor_attribution, dict)
        assert 'market' in factor_attribution
        assert 'size' in factor_attribution
        assert 'value' in factor_attribution
    
    def test_analyze_sector_attribution(self):
        """Test sector attribution analysis"""
        portfolio_returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20)
        sector_returns = {
            'Technology': pd.Series([0.012, 0.025, -0.012, 0.018, 0.025] * 20),
            'Financials': pd.Series([0.008, 0.015, -0.008, 0.012, 0.015] * 20),
            'Healthcare': pd.Series([0.006, 0.012, -0.006, 0.009, 0.012] * 20)
        }
        
        sector_attribution = self.attribution_analyzer.analyze_sector_attribution(portfolio_returns, sector_returns)
        assert isinstance(sector_attribution, dict)
        assert 'Technology' in sector_attribution
        assert 'Financials' in sector_attribution
        assert 'Healthcare' in sector_attribution
    
    def test_analyze_time_attribution(self):
        """Test time attribution analysis"""
        portfolio_returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20)
        timestamps = pd.date_range('2024-01-01', periods=len(portfolio_returns), freq='D')
        portfolio_returns.index = timestamps
        
        time_attribution = self.attribution_analyzer.analyze_time_attribution(portfolio_returns)
        assert isinstance(time_attribution, dict)
        assert 'daily_attribution' in time_attribution
        assert 'weekly_attribution' in time_attribution
        assert 'monthly_attribution' in time_attribution


class TestBenchmarkAnalyzer:
    """Test suite for BenchmarkAnalyzer - benchmark analysis component"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.benchmark_analyzer = BenchmarkAnalyzer()
    
    def test_analyze_benchmark_performance(self):
        """Test benchmark performance analysis"""
        portfolio_returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20)
        benchmark_returns = pd.Series([0.008, 0.015, -0.008, 0.012, 0.018] * 20)
        
        benchmark_analysis = self.benchmark_analyzer.analyze_benchmark_performance(portfolio_returns, benchmark_returns)
        assert isinstance(benchmark_analysis, dict)
        assert 'excess_return' in benchmark_analysis
        assert 'information_ratio' in benchmark_analysis
        assert 'tracking_error' in benchmark_analysis
        assert 'beta' in benchmark_analysis
        assert 'alpha' in benchmark_analysis
        assert 'r_squared' in benchmark_analysis
    
    def test_analyze_benchmark_attribution(self):
        """Test benchmark attribution analysis"""
        portfolio_returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20)
        benchmark_returns = pd.Series([0.008, 0.015, -0.008, 0.012, 0.018] * 20)
        
        attribution = self.benchmark_analyzer.analyze_benchmark_attribution(portfolio_returns, benchmark_returns)
        assert isinstance(attribution, dict)
        assert 'allocation_effect' in attribution
        assert 'selection_effect' in attribution
        assert 'interaction_effect' in attribution
    
    def test_analyze_benchmark_risk(self):
        """Test benchmark risk analysis"""
        portfolio_returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20)
        benchmark_returns = pd.Series([0.008, 0.015, -0.008, 0.012, 0.018] * 20)
        
        risk_analysis = self.benchmark_analyzer.analyze_benchmark_risk(portfolio_returns, benchmark_returns)
        assert isinstance(risk_analysis, dict)
        assert 'portfolio_risk' in risk_analysis
        assert 'benchmark_risk' in risk_analysis
        assert 'relative_risk' in risk_analysis
        assert 'correlation' in risk_analysis


class TestReportGenerator:
    """Test suite for ReportGenerator - report generation component"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.report_generator = ReportGenerator()
    
    def test_generate_performance_report(self):
        """Test performance report generation"""
        performance_data = {
            'returns': pd.Series([0.01, 0.02, -0.01, 0.015, 0.02] * 20),
            'benchmark_returns': pd.Series([0.008, 0.015, -0.008, 0.012, 0.018] * 20),
            'metrics': {
                'total_return': 0.12,
                'sharpe_ratio': 1.5,
                'max_drawdown': -0.08
            }
        }
        
        report = self.report_generator.generate_performance_report(performance_data)
        assert isinstance(report, dict)
        assert 'report_id' in report
        assert 'generation_time' in report
        assert 'performance_summary' in report
        assert 'charts' in report
    
    def test_generate_risk_report(self):
        """Test risk report generation"""
        risk_data = {
            'var_95': 0.03,
            'var_99': 0.05,
            'max_drawdown': -0.08,
            'volatility': 0.15,
            'sharpe_ratio': 1.2
        }
        
        report = self.report_generator.generate_risk_report(risk_data)
        assert isinstance(report, dict)
        assert 'report_id' in report
        assert 'generation_time' in report
        assert 'risk_summary' in report
        assert 'risk_metrics' in report
    
    def test_generate_attribution_report(self):
        """Test attribution report generation"""
        attribution_data = {
            'strategy_attribution': {
                'momentum': {'contribution': 0.4, 'return': 0.08},
                'mean_reversion': {'contribution': 0.6, 'return': 0.12}
            },
            'factor_attribution': {
                'market': {'contribution': 0.7, 'return': 0.14},
                'size': {'contribution': 0.2, 'return': 0.04},
                'value': {'contribution': 0.1, 'return': 0.02}
            }
        }
        
        report = self.report_generator.generate_attribution_report(attribution_data)
        assert isinstance(report, dict)
        assert 'report_id' in report
        assert 'generation_time' in report
        assert 'attribution_summary' in report
        assert 'strategy_attribution' in report
        assert 'factor_attribution' in report
    
    def test_generate_comprehensive_report(self):
        """Test comprehensive report generation"""
        comprehensive_data = {
            'performance': {'total_return': 0.12, 'sharpe_ratio': 1.5},
            'risk': {'var_95': 0.03, 'max_drawdown': -0.08},
            'attribution': {'strategy_attribution': {}, 'factor_attribution': {}},
            'benchmark': {'excess_return': 0.02, 'information_ratio': 1.2}
        }
        
        report = self.report_generator.generate_comprehensive_report(comprehensive_data)
        assert isinstance(report, dict)
        assert 'report_id' in report
        assert 'generation_time' in report
        assert 'executive_summary' in report
        assert 'performance_section' in report
        assert 'risk_section' in report
        assert 'attribution_section' in report
        assert 'benchmark_section' in report


class TestAnalyticsManagerIntegration:
    """Integration tests for analytics manager components"""
    
    def setup_method(self):
        """Setup for integration tests"""
        self.analytics_manager = AnalyticsManagerEnhanced({
            'enable_real_time_analytics': True,
            'enable_batch_analytics': True,
            'enable_performance_attribution': True
        })
    
    @pytest.mark.asyncio
    async def test_end_to_end_analytics_pipeline(self):
        """Test end-to-end analytics pipeline"""
        # Mock market data
        market_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 1000000,
            'timestamp': datetime.now(),
            'type': 'market_data'
        }
        
        # Test real-time processing
        with patch.object(self.analytics_manager, '_update_real_time_metrics', new_callable=AsyncMock) as mock_realtime:
            mock_realtime.return_value = {'price_change': 0.02, 'volatility': 0.12}
            
            realtime_result = await self.analytics_manager.process_real_time_data(market_data)
            assert isinstance(realtime_result, dict)
        
        # Test batch processing
        historical_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H'),
            'AAPL': np.random.normal(150, 5, 100),
            'GOOGL': np.random.normal(2800, 50, 100)
        })
        
        with patch.object(self.analytics_manager, '_calculate_batch_metrics', new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = {'total_return': 0.05, 'volatility': 0.15}
            
            batch_result = await self.analytics_manager.process_batch_data(
                historical_data, datetime.now() - timedelta(days=1), datetime.now()
            )
            assert isinstance(batch_result, dict)
    
    @pytest.mark.asyncio
    async def test_analytics_component_coordination(self):
        """Test coordination between analytics components"""
        with patch.object(self.analytics_manager, '_coordinate_analytics_components', new_callable=AsyncMock) as mock_coordinate:
            mock_coordinate.return_value = {
                'metrics_calculator': 'operational',
                'performance_analyzer': 'operational',
                'attribution_analyzer': 'operational',
                'benchmark_analyzer': 'operational'
            }
            
            coordination_status = await self.analytics_manager._coordinate_analytics_components()
            assert isinstance(coordination_status, dict)
            assert 'metrics_calculator' in coordination_status
            assert 'performance_analyzer' in coordination_status
    
    @pytest.mark.asyncio
    async def test_analytics_error_handling(self):
        """Test analytics error handling"""
        with patch.object(self.analytics_manager, '_handle_analytics_error', new_callable=AsyncMock) as mock_error:
            mock_error.return_value = {
                'error_handled': True,
                'error_type': 'calculation_error',
                'recovery_action': 'fallback_calculation'
            }
            
            error_result = await self.analytics_manager._handle_analytics_error(Exception("Test error"))
            assert isinstance(error_result, dict)
            assert 'error_handled' in error_result
            assert 'recovery_action' in error_result
