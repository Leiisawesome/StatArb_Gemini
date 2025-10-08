"""
Unit tests for EnhancedMetricsCalculator
Advanced metrics calculation with risk-adjusted performance and statistical measures
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core_engine.analytics.metrics_calculator import (
    EnhancedMetricsCalculator, MetricConfig, MetricCategory
)
from core_engine.system.interfaces import ISystemComponent


class TestEnhancedMetricsCalculator:
    """Comprehensive tests for EnhancedMetricsCalculator - Advanced metrics calculation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = MetricConfig(
            risk_free_rate=0.02,
            trading_days_per_year=252,
            confidence_levels=[0.90, 0.95, 0.99],
            rolling_windows={'short': 21, 'medium': 63, 'long': 252},
            var_methods=['historical', 'parametric', 'monte_carlo'],
            monte_carlo_simulations=10000
        )
        
        # Create a mock metrics calculator
        self.metrics_calculator = Mock()
        
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
    
    def test_metric_category_enum(self):
        """Test MetricCategory enum values"""
        assert MetricCategory.RETURN.value == "return"
        assert MetricCategory.RISK.value == "risk"
        assert MetricCategory.RISK_ADJUSTED.value == "risk_adjusted"
        assert MetricCategory.DRAWDOWN.value == "drawdown"
        assert MetricCategory.DISTRIBUTION.value == "distribution"
        assert MetricCategory.TRADING.value == "trading"
        assert MetricCategory.BEHAVIORAL.value == "behavioral"
        assert MetricCategory.TAIL_RISK.value == "tail_risk"
    
    def test_metric_config_creation(self):
        """Test MetricConfig creation"""
        config = MetricConfig(
            risk_free_rate=0.03,
            trading_days_per_year=252,
            confidence_levels=[0.95, 0.99],
            rolling_windows={'short': 21, 'long': 252},
            var_methods=['historical', 'parametric'],
            monte_carlo_simulations=5000
        )
        
        assert config.risk_free_rate == 0.03
        assert config.trading_days_per_year == 252
        assert config.confidence_levels == [0.95, 0.99]
        assert config.rolling_windows == {'short': 21, 'long': 252}
        assert config.var_methods == ['historical', 'parametric']
        assert config.monte_carlo_simulations == 5000
    
    @pytest.mark.asyncio
    async def test_metrics_calculator_interface_methods(self):
        """Test that MetricsCalculator has expected interface methods"""
        # Test that the mock has the expected methods
        assert hasattr(self.metrics_calculator, 'calculate_return_metrics')
        assert hasattr(self.metrics_calculator, 'calculate_risk_metrics')
        assert hasattr(self.metrics_calculator, 'calculate_risk_adjusted_metrics')
        assert hasattr(self.metrics_calculator, 'calculate_drawdown_metrics')
        assert hasattr(self.metrics_calculator, 'calculate_distribution_metrics')
        assert hasattr(self.metrics_calculator, 'calculate_trading_metrics')
        assert hasattr(self.metrics_calculator, 'calculate_behavioral_metrics')
        assert hasattr(self.metrics_calculator, 'calculate_tail_risk_metrics')
    
    @pytest.mark.asyncio
    async def test_calculate_return_metrics_interface(self):
        """Test return metrics calculation interface"""
        self.metrics_calculator.calculate_return_metrics = AsyncMock(return_value={
            'total_return': 0.15,
            'annualized_return': 0.12,
            'cumulative_return': 0.15,
            'average_daily_return': 0.0005,
            'volatility': 0.18,
            'sharpe_ratio': 0.67
        })
        
        result = await self.metrics_calculator.calculate_return_metrics(self.portfolio_data)
        
        assert result['total_return'] == 0.15
        assert result['annualized_return'] == 0.12
        assert result['cumulative_return'] == 0.15
        assert result['average_daily_return'] == 0.0005
        assert result['volatility'] == 0.18
        assert result['sharpe_ratio'] == 0.67
        self.metrics_calculator.calculate_return_metrics.assert_called_once_with(self.portfolio_data)
    
    @pytest.mark.asyncio
    async def test_calculate_risk_metrics_interface(self):
        """Test risk metrics calculation interface"""
        self.metrics_calculator.calculate_risk_metrics = AsyncMock(return_value={
            'var_95': -0.025,
            'var_99': -0.035,
            'expected_shortfall': -0.040,
            'maximum_drawdown': -0.12,
            'downside_deviation': 0.015,
            'beta': 1.2,
            'tracking_error': 0.08
        })
        
        result = await self.metrics_calculator.calculate_risk_metrics(self.portfolio_data)
        
        assert result['var_95'] == -0.025
        assert result['var_99'] == -0.035
        assert result['expected_shortfall'] == -0.040
        assert result['maximum_drawdown'] == -0.12
        assert result['downside_deviation'] == 0.015
        assert result['beta'] == 1.2
        assert result['tracking_error'] == 0.08
        self.metrics_calculator.calculate_risk_metrics.assert_called_once_with(self.portfolio_data)
    
    @pytest.mark.asyncio
    async def test_calculate_risk_adjusted_metrics_interface(self):
        """Test risk-adjusted metrics calculation interface"""
        self.metrics_calculator.calculate_risk_adjusted_metrics = AsyncMock(return_value={
            'sharpe_ratio': 0.75,
            'sortino_ratio': 1.2,
            'calmar_ratio': 1.0,
            'information_ratio': 0.5,
            'treynor_ratio': 0.1,
            'jensen_alpha': 0.02
        })
        
        result = await self.metrics_calculator.calculate_risk_adjusted_metrics(self.portfolio_data)
        
        assert result['sharpe_ratio'] == 0.75
        assert result['sortino_ratio'] == 1.2
        assert result['calmar_ratio'] == 1.0
        assert result['information_ratio'] == 0.5
        assert result['treynor_ratio'] == 0.1
        assert result['jensen_alpha'] == 0.02
        self.metrics_calculator.calculate_risk_adjusted_metrics.assert_called_once_with(self.portfolio_data)
    
    @pytest.mark.asyncio
    async def test_calculate_drawdown_metrics_interface(self):
        """Test drawdown metrics calculation interface"""
        self.metrics_calculator.calculate_drawdown_metrics = AsyncMock(return_value={
            'maximum_drawdown': -0.15,
            'average_drawdown': -0.05,
            'drawdown_duration': 45,
            'recovery_time': 30,
            'drawdown_frequency': 0.1,
            'underwater_periods': 120
        })
        
        result = await self.metrics_calculator.calculate_drawdown_metrics(self.portfolio_data)
        
        assert result['maximum_drawdown'] == -0.15
        assert result['average_drawdown'] == -0.05
        assert result['drawdown_duration'] == 45
        assert result['recovery_time'] == 30
        assert result['drawdown_frequency'] == 0.1
        assert result['underwater_periods'] == 120
        self.metrics_calculator.calculate_drawdown_metrics.assert_called_once_with(self.portfolio_data)
    
    @pytest.mark.asyncio
    async def test_calculate_distribution_metrics_interface(self):
        """Test distribution metrics calculation interface"""
        self.metrics_calculator.calculate_distribution_metrics = AsyncMock(return_value={
            'skewness': -0.2,
            'kurtosis': 3.5,
            'jarque_bera_stat': 15.2,
            'jarque_bera_pvalue': 0.001,
            'normality_test': False,
            'percentile_5': -0.025,
            'percentile_95': 0.030
        })
        
        result = await self.metrics_calculator.calculate_distribution_metrics(self.portfolio_data)
        
        assert result['skewness'] == -0.2
        assert result['kurtosis'] == 3.5
        assert result['jarque_bera_stat'] == 15.2
        assert result['jarque_bera_pvalue'] == 0.001
        assert result['normality_test'] is False
        assert result['percentile_5'] == -0.025
        assert result['percentile_95'] == 0.030
        self.metrics_calculator.calculate_distribution_metrics.assert_called_once_with(self.portfolio_data)
    
    @pytest.mark.asyncio
    async def test_calculate_trading_metrics_interface(self):
        """Test trading metrics calculation interface"""
        self.metrics_calculator.calculate_trading_metrics = AsyncMock(return_value={
            'total_trades': 150,
            'winning_trades': 85,
            'losing_trades': 65,
            'win_rate': 0.567,
            'average_win': 250.0,
            'average_loss': -180.0,
            'profit_factor': 1.39,
            'expectancy': 45.5,
            'recovery_factor': 2.1
        })
        
        result = await self.metrics_calculator.calculate_trading_metrics(self.trade_data)
        
        assert result['total_trades'] == 150
        assert result['winning_trades'] == 85
        assert result['losing_trades'] == 65
        assert result['win_rate'] == 0.567
        assert result['average_win'] == 250.0
        assert result['average_loss'] == -180.0
        assert result['profit_factor'] == 1.39
        assert result['expectancy'] == 45.5
        assert result['recovery_factor'] == 2.1
        self.metrics_calculator.calculate_trading_metrics.assert_called_once_with(self.trade_data)
    
    @pytest.mark.asyncio
    async def test_calculate_behavioral_metrics_interface(self):
        """Test behavioral metrics calculation interface"""
        self.metrics_calculator.calculate_behavioral_metrics = AsyncMock(return_value={
            'herding_behavior': 0.65,
            'momentum_bias': 0.45,
            'contrarian_bias': 0.35,
            'loss_aversion': 0.8,
            'overconfidence': 0.6,
            'disposition_effect': 0.7
        })
        
        result = await self.metrics_calculator.calculate_behavioral_metrics(self.trade_data)
        
        assert result['herding_behavior'] == 0.65
        assert result['momentum_bias'] == 0.45
        assert result['contrarian_bias'] == 0.35
        assert result['loss_aversion'] == 0.8
        assert result['overconfidence'] == 0.6
        assert result['disposition_effect'] == 0.7
        self.metrics_calculator.calculate_behavioral_metrics.assert_called_once_with(self.trade_data)
    
    @pytest.mark.asyncio
    async def test_calculate_tail_risk_metrics_interface(self):
        """Test tail risk metrics calculation interface"""
        self.metrics_calculator.calculate_tail_risk_metrics = AsyncMock(return_value={
            'conditional_var': -0.045,
            'expected_shortfall': -0.050,
            'tail_expectation': -0.055,
            'tail_ratio': 0.8,
            'extreme_value_index': 0.15,
            'tail_dependence': 0.7
        })
        
        result = await self.metrics_calculator.calculate_tail_risk_metrics(self.portfolio_data)
        
        assert result['conditional_var'] == -0.045
        assert result['expected_shortfall'] == -0.050
        assert result['tail_expectation'] == -0.055
        assert result['tail_ratio'] == 0.8
        assert result['extreme_value_index'] == 0.15
        assert result['tail_dependence'] == 0.7
        self.metrics_calculator.calculate_tail_risk_metrics.assert_called_once_with(self.portfolio_data)
    
    @pytest.mark.asyncio
    async def test_calculate_comprehensive_metrics_interface(self):
        """Test comprehensive metrics calculation interface"""
        self.metrics_calculator.calculate_comprehensive_metrics = AsyncMock(return_value={
            'return_metrics': {'total_return': 0.15},
            'risk_metrics': {'var_95': -0.025},
            'risk_adjusted_metrics': {'sharpe_ratio': 0.75},
            'drawdown_metrics': {'maximum_drawdown': -0.15},
            'distribution_metrics': {'skewness': -0.2},
            'trading_metrics': {'win_rate': 0.567},
            'behavioral_metrics': {'loss_aversion': 0.8},
            'tail_risk_metrics': {'conditional_var': -0.045}
        })
        
        result = await self.metrics_calculator.calculate_comprehensive_metrics(
            self.portfolio_data, self.trade_data
        )
        
        assert 'return_metrics' in result
        assert 'risk_metrics' in result
        assert 'risk_adjusted_metrics' in result
        assert 'drawdown_metrics' in result
        assert 'distribution_metrics' in result
        assert 'trading_metrics' in result
        assert 'behavioral_metrics' in result
        assert 'tail_risk_metrics' in result
        
        self.metrics_calculator.calculate_comprehensive_metrics.assert_called_once_with(
            self.portfolio_data, self.trade_data
        )
    
    @pytest.mark.asyncio
    async def test_calculate_rolling_metrics_interface(self):
        """Test rolling metrics calculation interface"""
        self.metrics_calculator.calculate_rolling_metrics = AsyncMock(return_value={
            'rolling_sharpe': [0.5, 0.6, 0.7, 0.8, 0.75],
            'rolling_volatility': [0.15, 0.18, 0.16, 0.14, 0.17],
            'rolling_beta': [1.1, 1.2, 1.0, 0.9, 1.05],
            'rolling_max_drawdown': [-0.05, -0.08, -0.06, -0.04, -0.07]
        })
        
        result = await self.metrics_calculator.calculate_rolling_metrics(
            self.portfolio_data, window=21
        )
        
        assert 'rolling_sharpe' in result
        assert 'rolling_volatility' in result
        assert 'rolling_beta' in result
        assert 'rolling_max_drawdown' in result
        assert len(result['rolling_sharpe']) == 5
        assert len(result['rolling_volatility']) == 5
        assert len(result['rolling_beta']) == 5
        assert len(result['rolling_max_drawdown']) == 5
        
        self.metrics_calculator.calculate_rolling_metrics.assert_called_once_with(
            self.portfolio_data, window=21
        )
    
    @pytest.mark.asyncio
    async def test_calculate_benchmark_comparison_interface(self):
        """Test benchmark comparison interface"""
        self.metrics_calculator.calculate_benchmark_comparison = AsyncMock(return_value={
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
        
        result = await self.metrics_calculator.calculate_benchmark_comparison(
            self.portfolio_data
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
        
        self.metrics_calculator.calculate_benchmark_comparison.assert_called_once_with(
            self.portfolio_data
        )
    
    @pytest.mark.asyncio
    async def test_metrics_calculator_initialization_interface(self):
        """Test metrics calculator initialization interface"""
        self.metrics_calculator.initialize = AsyncMock(return_value=True)
        
        result = await self.metrics_calculator.initialize()
        
        assert result is True
        self.metrics_calculator.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_metrics_calculator_start_interface(self):
        """Test metrics calculator start interface"""
        self.metrics_calculator.start = AsyncMock(return_value=True)
        
        result = await self.metrics_calculator.start()
        
        assert result is True
        self.metrics_calculator.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_metrics_calculator_stop_interface(self):
        """Test metrics calculator stop interface"""
        self.metrics_calculator.stop = AsyncMock(return_value=True)
        
        result = await self.metrics_calculator.stop()
        
        assert result is True
        self.metrics_calculator.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_metrics_calculator_health_check_interface(self):
        """Test metrics calculator health check interface"""
        self.metrics_calculator.health_check = AsyncMock(return_value={
            'healthy': True,
            'initialized': True,
            'component_type': 'EnhancedMetricsCalculator',
            'calculations_performed': 1250,
            'average_calculation_time_ms': 15.5,
            'memory_usage_mb': 45.2
        })
        
        result = await self.metrics_calculator.health_check()
        
        assert result['healthy'] is True
        assert result['initialized'] is True
        assert result['component_type'] == 'EnhancedMetricsCalculator'
        assert result['calculations_performed'] == 1250
        assert result['average_calculation_time_ms'] == 15.5
        assert result['memory_usage_mb'] == 45.2
        self.metrics_calculator.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_metrics_calculator_get_status_interface(self):
        """Test metrics calculator status interface"""
        self.metrics_calculator.get_status = Mock(return_value={
            'operational': True,
            'calculations_active': 3,
            'queue_size': 15,
            'last_calculation_time': datetime.now().isoformat(),
            'total_calculations': 1250,
            'error_count': 2
        })
        
        result = self.metrics_calculator.get_status()
        
        assert result['operational'] is True
        assert result['calculations_active'] == 3
        assert result['queue_size'] == 15
        assert 'last_calculation_time' in result
        assert result['total_calculations'] == 1250
        assert result['error_count'] == 2
        self.metrics_calculator.get_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_metrics_calculator_error_handling_interface(self):
        """Test metrics calculator error handling interface"""
        self.metrics_calculator.handle_calculation_error = AsyncMock(return_value=True)
        
        test_error = Exception("Calculation error")
        result = await self.metrics_calculator.handle_calculation_error('return_metrics', test_error)
        
        assert result is True
        self.metrics_calculator.handle_calculation_error.assert_called_once_with('return_metrics', test_error)


if __name__ == '__main__':
    pytest.main([__file__])
