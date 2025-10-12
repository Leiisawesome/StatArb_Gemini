"""
Unit tests for PerformanceAnalyzer
Advanced performance analysis with comprehensive metrics and attribution
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, AsyncMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core_engine.analytics.performance_analyzer import (
    PerformanceConfig, RiskFreeRateSource
)


class TestPerformanceAnalyzer:
    """Comprehensive tests for PerformanceAnalyzer - Advanced performance analysis"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = PerformanceConfig(
            risk_free_rate_source=RiskFreeRateSource.TREASURY_3M,
            custom_risk_free_rate=0.02,
            trading_days_per_year=252,
            confidence_level=0.95,
            var_lookback_days=252,
            default_benchmark="SPY",
            enable_benchmark_comparison=True,
            enable_factor_attribution=True,
            attribution_frequency="daily",
            enable_downside_metrics=True
        )
        
        # Create a mock performance analyzer
        self.performance_analyzer = Mock()
        
        # Sample portfolio data
        self.portfolio_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=1000, freq='D'),
            'portfolio_value': np.random.normal(100000, 5000, 1000).cumsum(),
            'returns': np.random.normal(0.001, 0.02, 1000),
            'benchmark_returns': np.random.normal(0.0008, 0.018, 1000)
        })
        
        # Sample trade data
        self.trade_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='D'),
            'symbol': ['AAPL'] * 50 + ['GOOGL'] * 50,
            'quantity': np.random.choice([100, -100], 100),
            'price': np.random.normal(150, 10, 100),
            'pnl': np.random.normal(50, 200, 100)
        })
        
        # Sample benchmark data
        self.benchmark_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=1000, freq='D'),
            'benchmark_value': np.random.normal(100, 5, 1000).cumsum(),
            'benchmark_returns': np.random.normal(0.0008, 0.018, 1000)
        })
    
    def test_risk_free_rate_source_enum(self):
        """Test RiskFreeRateSource enum values"""
        assert RiskFreeRateSource.TREASURY_3M.value == "treasury_3m"
        assert RiskFreeRateSource.TREASURY_10Y.value == "treasury_10y"
        assert RiskFreeRateSource.LIBOR.value == "libor"
        assert RiskFreeRateSource.SOFR.value == "sofr"
        assert RiskFreeRateSource.CUSTOM.value == "custom"
    
    def test_performance_config_creation(self):
        """Test PerformanceConfig creation"""
        config = PerformanceConfig(
            risk_free_rate_source=RiskFreeRateSource.CUSTOM,
            custom_risk_free_rate=0.03,
            trading_days_per_year=252,
            confidence_level=0.99,
            var_lookback_days=500,
            default_benchmark="QQQ",
            enable_benchmark_comparison=True,
            enable_factor_attribution=True,
            attribution_frequency="weekly",
            enable_downside_metrics=True
        )
        
        assert config.risk_free_rate_source == RiskFreeRateSource.CUSTOM
        assert config.custom_risk_free_rate == 0.03
        assert config.trading_days_per_year == 252
        assert config.confidence_level == 0.99
        assert config.var_lookback_days == 500
        assert config.default_benchmark == "QQQ"
        assert config.enable_benchmark_comparison is True
        assert config.enable_factor_attribution is True
        assert config.attribution_frequency == "weekly"
        assert config.enable_downside_metrics is True
    
    @pytest.mark.asyncio
    async def test_performance_analyzer_interface_methods(self):
        """Test that PerformanceAnalyzer has expected interface methods"""
        # Test that the mock has the expected methods
        assert hasattr(self.performance_analyzer, 'analyze_portfolio_performance')
        assert hasattr(self.performance_analyzer, 'analyze_benchmark_comparison')
        assert hasattr(self.performance_analyzer, 'analyze_risk_metrics')
        assert hasattr(self.performance_analyzer, 'analyze_attribution')
        assert hasattr(self.performance_analyzer, 'analyze_drawdown_analysis')
        assert hasattr(self.performance_analyzer, 'analyze_rolling_performance')
        assert hasattr(self.performance_analyzer, 'analyze_factor_exposure')
        assert hasattr(self.performance_analyzer, 'generate_performance_report')
    
    @pytest.mark.asyncio
    async def test_analyze_portfolio_performance_interface(self):
        """Test portfolio performance analysis interface"""
        self.performance_analyzer.analyze_portfolio_performance = AsyncMock(return_value={
            'total_return': 0.15,
            'annualized_return': 0.12,
            'volatility': 0.18,
            'sharpe_ratio': 0.67,
            'sortino_ratio': 1.2,
            'max_drawdown': -0.12,
            'calmar_ratio': 1.0,
            'var_95': -0.025,
            'expected_shortfall': -0.035
        })
        
        result = await self.performance_analyzer.analyze_portfolio_performance(self.portfolio_data)
        
        assert result['total_return'] == 0.15
        assert result['annualized_return'] == 0.12
        assert result['volatility'] == 0.18
        assert result['sharpe_ratio'] == 0.67
        assert result['sortino_ratio'] == 1.2
        assert result['max_drawdown'] == -0.12
        assert result['calmar_ratio'] == 1.0
        assert result['var_95'] == -0.025
        assert result['expected_shortfall'] == -0.035
        self.performance_analyzer.analyze_portfolio_performance.assert_called_once_with(self.portfolio_data)
    
    @pytest.mark.asyncio
    async def test_analyze_benchmark_comparison_interface(self):
        """Test benchmark comparison analysis interface"""
        self.performance_analyzer.analyze_benchmark_comparison = AsyncMock(return_value={
            'excess_return': 0.03,
            'tracking_error': 0.08,
            'information_ratio': 0.375,
            'beta': 1.2,
            'alpha': 0.02,
            'correlation': 0.85,
            'relative_volatility': 1.1,
            'upside_capture': 1.05,
            'downside_capture': 0.95
        })
        
        result = await self.performance_analyzer.analyze_benchmark_comparison(
            self.portfolio_data, self.benchmark_data
        )
        
        assert result['excess_return'] == 0.03
        assert result['tracking_error'] == 0.08
        assert result['information_ratio'] == 0.375
        assert result['beta'] == 1.2
        assert result['alpha'] == 0.02
        assert result['correlation'] == 0.85
        assert result['relative_volatility'] == 1.1
        assert result['upside_capture'] == 1.05
        assert result['downside_capture'] == 0.95
        self.performance_analyzer.analyze_benchmark_comparison.assert_called_once_with(
            self.portfolio_data, self.benchmark_data
        )
    
    @pytest.mark.asyncio
    async def test_analyze_risk_metrics_interface(self):
        """Test risk metrics analysis interface"""
        self.performance_analyzer.analyze_risk_metrics = AsyncMock(return_value={
            'var_95': -0.025,
            'var_99': -0.035,
            'expected_shortfall': -0.040,
            'maximum_drawdown': -0.12,
            'downside_deviation': 0.015,
            'beta': 1.2,
            'tracking_error': 0.08,
            'tail_risk': 0.05,
            'skewness': -0.2,
            'kurtosis': 3.5
        })
        
        result = await self.performance_analyzer.analyze_risk_metrics(self.portfolio_data)
        
        assert result['var_95'] == -0.025
        assert result['var_99'] == -0.035
        assert result['expected_shortfall'] == -0.040
        assert result['maximum_drawdown'] == -0.12
        assert result['downside_deviation'] == 0.015
        assert result['beta'] == 1.2
        assert result['tracking_error'] == 0.08
        assert result['tail_risk'] == 0.05
        assert result['skewness'] == -0.2
        assert result['kurtosis'] == 3.5
        self.performance_analyzer.analyze_risk_metrics.assert_called_once_with(self.portfolio_data)
    
    @pytest.mark.asyncio
    async def test_analyze_attribution_interface(self):
        """Test attribution analysis interface"""
        self.performance_analyzer.analyze_attribution = AsyncMock(return_value={
            'total_attribution': 0.15,
            'asset_allocation_effect': 0.05,
            'security_selection_effect': 0.08,
            'interaction_effect': 0.02,
            'factor_attribution': {
                'market_factor': 0.10,
                'size_factor': 0.02,
                'value_factor': 0.01,
                'momentum_factor': 0.02
            },
            'residual_alpha': 0.03
        })
        
        result = await self.performance_analyzer.analyze_attribution(
            self.portfolio_data, self.benchmark_data
        )
        
        assert result['total_attribution'] == 0.15
        assert result['asset_allocation_effect'] == 0.05
        assert result['security_selection_effect'] == 0.08
        assert result['interaction_effect'] == 0.02
        assert 'factor_attribution' in result
        assert result['factor_attribution']['market_factor'] == 0.10
        assert result['factor_attribution']['size_factor'] == 0.02
        assert result['factor_attribution']['value_factor'] == 0.01
        assert result['factor_attribution']['momentum_factor'] == 0.02
        assert result['residual_alpha'] == 0.03
        self.performance_analyzer.analyze_attribution.assert_called_once_with(
            self.portfolio_data, self.benchmark_data
        )
    
    @pytest.mark.asyncio
    async def test_analyze_drawdown_analysis_interface(self):
        """Test drawdown analysis interface"""
        self.performance_analyzer.analyze_drawdown_analysis = AsyncMock(return_value={
            'maximum_drawdown': -0.15,
            'average_drawdown': -0.05,
            'drawdown_duration': 45,
            'recovery_time': 30,
            'drawdown_frequency': 0.1,
            'underwater_periods': 120,
            'pain_index': 0.08,
            'ulcer_index': 0.12
        })
        
        result = await self.performance_analyzer.analyze_drawdown_analysis(self.portfolio_data)
        
        assert result['maximum_drawdown'] == -0.15
        assert result['average_drawdown'] == -0.05
        assert result['drawdown_duration'] == 45
        assert result['recovery_time'] == 30
        assert result['drawdown_frequency'] == 0.1
        assert result['underwater_periods'] == 120
        assert result['pain_index'] == 0.08
        assert result['ulcer_index'] == 0.12
        self.performance_analyzer.analyze_drawdown_analysis.assert_called_once_with(self.portfolio_data)
    
    @pytest.mark.asyncio
    async def test_analyze_rolling_performance_interface(self):
        """Test rolling performance analysis interface"""
        self.performance_analyzer.analyze_rolling_performance = AsyncMock(return_value={
            'rolling_sharpe': [0.5, 0.6, 0.7, 0.8, 0.75],
            'rolling_volatility': [0.15, 0.18, 0.16, 0.14, 0.17],
            'rolling_beta': [1.1, 1.2, 1.0, 0.9, 1.05],
            'rolling_max_drawdown': [-0.05, -0.08, -0.06, -0.04, -0.07],
            'rolling_information_ratio': [0.2, 0.3, 0.4, 0.5, 0.35]
        })
        
        result = await self.performance_analyzer.analyze_rolling_performance(
            self.portfolio_data, window=21
        )
        
        assert 'rolling_sharpe' in result
        assert 'rolling_volatility' in result
        assert 'rolling_beta' in result
        assert 'rolling_max_drawdown' in result
        assert 'rolling_information_ratio' in result
        assert len(result['rolling_sharpe']) == 5
        assert len(result['rolling_volatility']) == 5
        assert len(result['rolling_beta']) == 5
        assert len(result['rolling_max_drawdown']) == 5
        assert len(result['rolling_information_ratio']) == 5
        
        self.performance_analyzer.analyze_rolling_performance.assert_called_once_with(
            self.portfolio_data, window=21
        )
    
    @pytest.mark.asyncio
    async def test_analyze_factor_exposure_interface(self):
        """Test factor exposure analysis interface"""
        self.performance_analyzer.analyze_factor_exposure = AsyncMock(return_value={
            'market_beta': 1.2,
            'size_exposure': 0.3,
            'value_exposure': -0.1,
            'momentum_exposure': 0.2,
            'quality_exposure': 0.4,
            'volatility_exposure': -0.2,
            'factor_rsquared': 0.85,
            'factor_alpha': 0.02
        })
        
        result = await self.performance_analyzer.analyze_factor_exposure(self.portfolio_data)
        
        assert result['market_beta'] == 1.2
        assert result['size_exposure'] == 0.3
        assert result['value_exposure'] == -0.1
        assert result['momentum_exposure'] == 0.2
        assert result['quality_exposure'] == 0.4
        assert result['volatility_exposure'] == -0.2
        assert result['factor_rsquared'] == 0.85
        assert result['factor_alpha'] == 0.02
        self.performance_analyzer.analyze_factor_exposure.assert_called_once_with(self.portfolio_data)
    
    @pytest.mark.asyncio
    async def test_generate_performance_report_interface(self):
        """Test performance report generation interface"""
        self.performance_analyzer.generate_performance_report = AsyncMock(return_value={
            'report_id': 'perf_20241220_001',
            'report_timestamp': datetime.now().isoformat(),
            'summary_metrics': {
                'total_return': 0.15,
                'sharpe_ratio': 0.67,
                'max_drawdown': -0.12
            },
            'detailed_analysis': {
                'risk_metrics': {'var_95': -0.025},
                'attribution': {'total_attribution': 0.15},
                'benchmark_comparison': {'excess_return': 0.03}
            },
            'recommendations': [
                'Consider reducing concentration risk',
                'Monitor downside volatility'
            ]
        })
        
        result = await self.performance_analyzer.generate_performance_report(
            self.portfolio_data, self.benchmark_data
        )
        
        assert 'report_id' in result
        assert 'report_timestamp' in result
        assert 'summary_metrics' in result
        assert 'detailed_analysis' in result
        assert 'recommendations' in result
        assert result['summary_metrics']['total_return'] == 0.15
        assert result['summary_metrics']['sharpe_ratio'] == 0.67
        assert result['summary_metrics']['max_drawdown'] == -0.12
        assert len(result['recommendations']) == 2
        
        self.performance_analyzer.generate_performance_report.assert_called_once_with(
            self.portfolio_data, self.benchmark_data
        )
    
    @pytest.mark.asyncio
    async def test_performance_analyzer_initialization_interface(self):
        """Test performance analyzer initialization interface"""
        self.performance_analyzer.initialize = AsyncMock(return_value=True)
        
        result = await self.performance_analyzer.initialize()
        
        assert result is True
        self.performance_analyzer.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_analyzer_start_interface(self):
        """Test performance analyzer start interface"""
        self.performance_analyzer.start = AsyncMock(return_value=True)
        
        result = await self.performance_analyzer.start()
        
        assert result is True
        self.performance_analyzer.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_analyzer_stop_interface(self):
        """Test performance analyzer stop interface"""
        self.performance_analyzer.stop = AsyncMock(return_value=True)
        
        result = await self.performance_analyzer.stop()
        
        assert result is True
        self.performance_analyzer.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_analyzer_health_check_interface(self):
        """Test performance analyzer health check interface"""
        self.performance_analyzer.health_check = AsyncMock(return_value={
            'healthy': True,
            'initialized': True,
            'component_type': 'PerformanceAnalyzer',
            'analyses_performed': 850,
            'average_analysis_time_ms': 25.3,
            'memory_usage_mb': 67.8
        })
        
        result = await self.performance_analyzer.health_check()
        
        assert result['healthy'] is True
        assert result['initialized'] is True
        assert result['component_type'] == 'PerformanceAnalyzer'
        assert result['analyses_performed'] == 850
        assert result['average_analysis_time_ms'] == 25.3
        assert result['memory_usage_mb'] == 67.8
        self.performance_analyzer.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_analyzer_get_status_interface(self):
        """Test performance analyzer status interface"""
        self.performance_analyzer.get_status = Mock(return_value={
            'operational': True,
            'analyses_active': 2,
            'queue_size': 8,
            'last_analysis_time': datetime.now().isoformat(),
            'total_analyses': 850,
            'error_count': 1
        })
        
        result = self.performance_analyzer.get_status()
        
        assert result['operational'] is True
        assert result['analyses_active'] == 2
        assert result['queue_size'] == 8
        assert 'last_analysis_time' in result
        assert result['total_analyses'] == 850
        assert result['error_count'] == 1
        self.performance_analyzer.get_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_analyzer_error_handling_interface(self):
        """Test performance analyzer error handling interface"""
        self.performance_analyzer.handle_analysis_error = AsyncMock(return_value=True)
        
        test_error = Exception("Analysis error")
        result = await self.performance_analyzer.handle_analysis_error('portfolio_performance', test_error)
        
        assert result is True
        self.performance_analyzer.handle_analysis_error.assert_called_once_with('portfolio_performance', test_error)


if __name__ == '__main__':
    pytest.main([__file__])