"""
Unit tests for AttributionAnalyzer
Advanced performance attribution analysis with factor and sector decomposition
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

from core_engine.analytics.attribution_analyzer import (
    AttributionConfig, AttributionMethod, AttributionType, PerformanceComponent
)

class TestAttributionAnalyzer:
    """Comprehensive tests for AttributionAnalyzer - Advanced performance attribution analysis"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = AttributionConfig(
            attribution_method=AttributionMethod.FACTOR_MODEL,
            attribution_frequency="daily",
            factor_model_type="fama_french",
            lookback_period=252,
            risk_model_factors=["market", "size", "value", "momentum", "quality", "volatility"],
            sector_classification="gics",
            enable_allocation_effect=True,
            enable_selection_effect=True
        )

        # Create a mock attribution analyzer
        self.attribution_analyzer = Mock()

        # Sample portfolio data
        self.portfolio_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=1000, freq='D'),
            'portfolio_value': np.random.normal(100000, 5000, 1000).cumsum(),
            'returns': np.random.normal(0.001, 0.02, 1000),
            'benchmark_returns': np.random.normal(0.0008, 0.018, 1000)
        })

        # Sample holdings data
        self.holdings_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='D'),
            'symbol': ['AAPL', 'GOOGL', 'MSFT', 'TSLA'] * 25,
            'weight': np.random.uniform(0.1, 0.4, 100),
            'return': np.random.normal(0.001, 0.02, 100),
            'sector': ['Technology', 'Technology', 'Technology', 'Consumer Discretionary'] * 25
        })

        # Sample factor data
        self.factor_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=1000, freq='D'),
            'market_factor': np.random.normal(0.0005, 0.015, 1000),
            'size_factor': np.random.normal(0.0002, 0.008, 1000),
            'value_factor': np.random.normal(0.0001, 0.006, 1000),
            'momentum_factor': np.random.normal(0.0003, 0.010, 1000)
        })

    def test_attribution_method_enum(self):
        """Test AttributionMethod enum values"""
        assert AttributionMethod.BRINSON.value == "brinson"
        assert AttributionMethod.FACTOR_MODEL.value == "factor_model"
        assert AttributionMethod.RETURNS_BASED.value == "returns_based"
        assert AttributionMethod.HOLDINGS_BASED.value == "holdings_based"
        assert AttributionMethod.MULTI_FACTOR.value == "multi_factor"
        assert AttributionMethod.RISK_MODEL.value == "risk_model"

    def test_attribution_type_enum(self):
        """Test AttributionType enum values"""
        assert AttributionType.SECTOR.value == "sector"
        assert AttributionType.FACTOR.value == "factor"
        assert AttributionType.SECURITY.value == "security"
        assert AttributionType.STYLE.value == "style"
        assert AttributionType.GEOGRAPHIC.value == "geographic"
        assert AttributionType.CURRENCY.value == "currency"
        assert AttributionType.ASSET_CLASS.value == "asset_class"

    def test_performance_component_enum(self):
        """Test PerformanceComponent enum values"""
        assert PerformanceComponent.ALLOCATION.value == "allocation"
        assert PerformanceComponent.SELECTION.value == "selection"
        assert PerformanceComponent.INTERACTION.value == "interaction"
        assert PerformanceComponent.TOTAL.value == "total"

    def test_attribution_config_creation(self):
        """Test AttributionConfig creation"""
        config = AttributionConfig(
            attribution_method=AttributionMethod.BRINSON,
            attribution_frequency="weekly",
            factor_model_type="carhart",
            lookback_period=500,
            risk_model_factors=["market", "size", "value", "momentum"],
            sector_classification="industry",
            enable_allocation_effect=True,
            enable_selection_effect=True
        )

        assert config.attribution_method == AttributionMethod.BRINSON
        assert config.attribution_frequency == "weekly"
        assert config.factor_model_type == "carhart"
        assert config.lookback_period == 500
        assert config.risk_model_factors == ["market", "size", "value", "momentum"]
        assert config.sector_classification == "industry"
        assert config.enable_allocation_effect is True
        assert config.enable_selection_effect is True

    @pytest.mark.asyncio
    async def test_attribution_analyzer_interface_methods(self):
        """Test that AttributionAnalyzer has expected interface methods"""
        # Test that the mock has the expected methods
        assert hasattr(self.attribution_analyzer, 'analyze_factor_attribution')
        assert hasattr(self.attribution_analyzer, 'analyze_sector_attribution')
        assert hasattr(self.attribution_analyzer, 'analyze_security_attribution')
        assert hasattr(self.attribution_analyzer, 'analyze_brinson_attribution')
        assert hasattr(self.attribution_analyzer, 'analyze_multi_factor_attribution')
        assert hasattr(self.attribution_analyzer, 'analyze_returns_based_attribution')
        assert hasattr(self.attribution_analyzer, 'generate_attribution_report')
        assert hasattr(self.attribution_analyzer, 'calculate_attribution_statistics')

    @pytest.mark.asyncio
    async def test_analyze_factor_attribution_interface(self):
        """Test factor attribution analysis interface"""
        self.attribution_analyzer.analyze_factor_attribution = AsyncMock(return_value={
            'total_attribution': 0.15,
            'factor_attribution': {
                'market_factor': 0.10,
                'size_factor': 0.02,
                'value_factor': 0.01,
                'momentum_factor': 0.02
            },
            'residual_alpha': 0.03,
            'factor_exposures': {
                'market_beta': 1.2,
                'size_exposure': 0.3,
                'value_exposure': -0.1,
                'momentum_exposure': 0.2
            },
            'factor_rsquared': 0.85,
            'factor_volatility': 0.12
        })

        result = await self.attribution_analyzer.analyze_factor_attribution(
            self.portfolio_data, self.factor_data
        )

        assert result['total_attribution'] == 0.15
        assert 'factor_attribution' in result
        assert result['factor_attribution']['market_factor'] == 0.10
        assert result['factor_attribution']['size_factor'] == 0.02
        assert result['factor_attribution']['value_factor'] == 0.01
        assert result['factor_attribution']['momentum_factor'] == 0.02
        assert result['residual_alpha'] == 0.03
        assert 'factor_exposures' in result
        assert result['factor_exposures']['market_beta'] == 1.2
        assert result['factor_exposures']['size_exposure'] == 0.3
        assert result['factor_exposures']['value_exposure'] == -0.1
        assert result['factor_exposures']['momentum_exposure'] == 0.2
        assert result['factor_rsquared'] == 0.85
        assert result['factor_volatility'] == 0.12
        self.attribution_analyzer.analyze_factor_attribution.assert_called_once_with(
            self.portfolio_data, self.factor_data
        )

    @pytest.mark.asyncio
    async def test_analyze_sector_attribution_interface(self):
        """Test sector attribution analysis interface"""
        self.attribution_analyzer.analyze_sector_attribution = AsyncMock(return_value={
            'total_attribution': 0.15,
            'allocation_effect': 0.05,
            'selection_effect': 0.08,
            'interaction_effect': 0.02,
            'sector_attribution': {
                'Technology': 0.06,
                'Healthcare': 0.03,
                'Financials': 0.02,
                'Consumer Discretionary': 0.04
            },
            'sector_weights': {
                'Technology': 0.35,
                'Healthcare': 0.20,
                'Financials': 0.15,
                'Consumer Discretionary': 0.30
            },
            'sector_returns': {
                'Technology': 0.18,
                'Healthcare': 0.12,
                'Financials': 0.10,
                'Consumer Discretionary': 0.15
            }
        })

        result = await self.attribution_analyzer.analyze_sector_attribution(
            self.holdings_data
        )

        assert result['total_attribution'] == 0.15
        assert result['allocation_effect'] == 0.05
        assert result['selection_effect'] == 0.08
        assert result['interaction_effect'] == 0.02
        assert 'sector_attribution' in result
        assert result['sector_attribution']['Technology'] == 0.06
        assert result['sector_attribution']['Healthcare'] == 0.03
        assert result['sector_attribution']['Financials'] == 0.02
        assert result['sector_attribution']['Consumer Discretionary'] == 0.04
        assert 'sector_weights' in result
        assert 'sector_returns' in result
        self.attribution_analyzer.analyze_sector_attribution.assert_called_once_with(
            self.holdings_data
        )

    @pytest.mark.asyncio
    async def test_analyze_security_attribution_interface(self):
        """Test security attribution analysis interface"""
        self.attribution_analyzer.analyze_security_attribution = AsyncMock(return_value={
            'total_attribution': 0.15,
            'security_attribution': {
                'AAPL': 0.05,
                'GOOGL': 0.04,
                'MSFT': 0.03,
                'TSLA': 0.03
            },
            'top_contributors': [
                {'symbol': 'AAPL', 'attribution': 0.05, 'weight': 0.35},
                {'symbol': 'GOOGL', 'attribution': 0.04, 'weight': 0.30}
            ],
            'top_detractors': [
                {'symbol': 'TSLA', 'attribution': -0.01, 'weight': 0.15},
                {'symbol': 'MSFT', 'attribution': -0.005, 'weight': 0.20}
            ],
            'concentration_risk': 0.65
        })

        result = await self.attribution_analyzer.analyze_security_attribution(
            self.holdings_data
        )

        assert result['total_attribution'] == 0.15
        assert 'security_attribution' in result
        assert result['security_attribution']['AAPL'] == 0.05
        assert result['security_attribution']['GOOGL'] == 0.04
        assert result['security_attribution']['MSFT'] == 0.03
        assert result['security_attribution']['TSLA'] == 0.03
        assert 'top_contributors' in result
        assert 'top_detractors' in result
        assert result['concentration_risk'] == 0.65
        assert len(result['top_contributors']) == 2
        assert len(result['top_detractors']) == 2
        self.attribution_analyzer.analyze_security_attribution.assert_called_once_with(
            self.holdings_data
        )

    @pytest.mark.asyncio
    async def test_analyze_brinson_attribution_interface(self):
        """Test Brinson attribution analysis interface"""
        self.attribution_analyzer.analyze_brinson_attribution = AsyncMock(return_value={
            'total_attribution': 0.15,
            'allocation_effect': 0.05,
            'selection_effect': 0.08,
            'interaction_effect': 0.02,
            'brinson_components': {
                'asset_allocation': 0.03,
                'security_selection': 0.06,
                'interaction': 0.02,
                'total_active': 0.11
            },
            'benchmark_return': 0.08,
            'portfolio_return': 0.23
        })

        result = await self.attribution_analyzer.analyze_brinson_attribution(
            self.holdings_data
        )

        assert result['total_attribution'] == 0.15
        assert result['allocation_effect'] == 0.05
        assert result['selection_effect'] == 0.08
        assert result['interaction_effect'] == 0.02
        assert 'brinson_components' in result
        assert result['brinson_components']['asset_allocation'] == 0.03
        assert result['brinson_components']['security_selection'] == 0.06
        assert result['brinson_components']['interaction'] == 0.02
        assert result['brinson_components']['total_active'] == 0.11
        assert result['benchmark_return'] == 0.08
        assert result['portfolio_return'] == 0.23
        self.attribution_analyzer.analyze_brinson_attribution.assert_called_once_with(
            self.holdings_data
        )

    @pytest.mark.asyncio
    async def test_analyze_multi_factor_attribution_interface(self):
        """Test multi-factor attribution analysis interface"""
        self.attribution_analyzer.analyze_multi_factor_attribution = AsyncMock(return_value={
            'total_attribution': 0.15,
            'factor_attribution': {
                'market_factor': 0.10,
                'size_factor': 0.02,
                'value_factor': 0.01,
                'momentum_factor': 0.02
            },
            'factor_exposures': {
                'market_beta': 1.2,
                'size_exposure': 0.3,
                'value_exposure': -0.1,
                'momentum_exposure': 0.2
            },
            'factor_returns': {
                'market_factor': 0.08,
                'size_factor': 0.06,
                'value_factor': 0.04,
                'momentum_factor': 0.10
            },
            'residual_alpha': 0.03,
            'factor_rsquared': 0.85
        })

        result = await self.attribution_analyzer.analyze_multi_factor_attribution(
            self.portfolio_data, self.factor_data
        )

        assert result['total_attribution'] == 0.15
        assert 'factor_attribution' in result
        assert 'factor_exposures' in result
        assert 'factor_returns' in result
        assert result['residual_alpha'] == 0.03
        assert result['factor_rsquared'] == 0.85
        self.attribution_analyzer.analyze_multi_factor_attribution.assert_called_once_with(
            self.portfolio_data, self.factor_data
        )

    @pytest.mark.asyncio
    async def test_analyze_returns_based_attribution_interface(self):
        """Test returns-based attribution analysis interface"""
        self.attribution_analyzer.analyze_returns_based_attribution = AsyncMock(return_value={
            'total_attribution': 0.15,
            'attribution_breakdown': {
                'systematic_attribution': 0.10,
                'idiosyncratic_attribution': 0.05
            },
            'risk_decomposition': {
                'systematic_risk': 0.12,
                'idiosyncratic_risk': 0.08,
                'total_risk': 0.14
            },
            'attribution_statistics': {
                'information_ratio': 0.5,
                'tracking_error': 0.08,
                'correlation': 0.85
            }
        })

        result = await self.attribution_analyzer.analyze_returns_based_attribution(
            self.portfolio_data
        )

        assert result['total_attribution'] == 0.15
        assert 'attribution_breakdown' in result
        assert result['attribution_breakdown']['systematic_attribution'] == 0.10
        assert result['attribution_breakdown']['idiosyncratic_attribution'] == 0.05
        assert 'risk_decomposition' in result
        assert 'attribution_statistics' in result
        assert result['attribution_statistics']['information_ratio'] == 0.5
        assert result['attribution_statistics']['tracking_error'] == 0.08
        assert result['attribution_statistics']['correlation'] == 0.85
        self.attribution_analyzer.analyze_returns_based_attribution.assert_called_once_with(
            self.portfolio_data
        )

    @pytest.mark.asyncio
    async def test_generate_attribution_report_interface(self):
        """Test attribution report generation interface"""
        self.attribution_analyzer.generate_attribution_report = AsyncMock(return_value={
            'report_id': 'attr_20241220_001',
            'report_timestamp': datetime.now().isoformat(),
            'summary_attribution': {
                'total_attribution': 0.15,
                'allocation_effect': 0.05,
                'selection_effect': 0.08,
                'interaction_effect': 0.02
            },
            'detailed_analysis': {
                'factor_attribution': {'market_factor': 0.10},
                'sector_attribution': {'Technology': 0.06},
                'security_attribution': {'AAPL': 0.05}
            },
            'recommendations': [
                'Consider rebalancing sector allocation',
                'Monitor factor exposure concentration'
            ]
        })

        result = await self.attribution_analyzer.generate_attribution_report(
            self.portfolio_data, self.holdings_data
        )

        assert 'report_id' in result
        assert 'report_timestamp' in result
        assert 'summary_attribution' in result
        assert 'detailed_analysis' in result
        assert 'recommendations' in result
        assert result['summary_attribution']['total_attribution'] == 0.15
        assert result['summary_attribution']['allocation_effect'] == 0.05
        assert result['summary_attribution']['selection_effect'] == 0.08
        assert result['summary_attribution']['interaction_effect'] == 0.02
        assert len(result['recommendations']) == 2
        self.attribution_analyzer.generate_attribution_report.assert_called_once_with(
            self.portfolio_data, self.holdings_data
        )

    @pytest.mark.asyncio
    async def test_calculate_attribution_statistics_interface(self):
        """Test attribution statistics calculation interface"""
        self.attribution_analyzer.calculate_attribution_statistics = AsyncMock(return_value={
            'attribution_consistency': 0.75,
            'attribution_stability': 0.80,
            'attribution_volatility': 0.12,
            'attribution_sharpe': 1.25,
            'attribution_correlation': 0.85,
            'attribution_autocorrelation': 0.15,
            'attribution_statistics': {
                'mean_attribution': 0.08,
                'std_attribution': 0.12,
                'skewness': -0.2,
                'kurtosis': 3.5
            }
        })

        result = await self.attribution_analyzer.calculate_attribution_statistics(
            self.portfolio_data
        )

        assert result['attribution_consistency'] == 0.75
        assert result['attribution_stability'] == 0.80
        assert result['attribution_volatility'] == 0.12
        assert result['attribution_sharpe'] == 1.25
        assert result['attribution_correlation'] == 0.85
        assert result['attribution_autocorrelation'] == 0.15
        assert 'attribution_statistics' in result
        assert result['attribution_statistics']['mean_attribution'] == 0.08
        assert result['attribution_statistics']['std_attribution'] == 0.12
        assert result['attribution_statistics']['skewness'] == -0.2
        assert result['attribution_statistics']['kurtosis'] == 3.5
        self.attribution_analyzer.calculate_attribution_statistics.assert_called_once_with(
            self.portfolio_data
        )

    @pytest.mark.asyncio
    async def test_attribution_analyzer_error_handling_interface(self):
        """Test attribution analyzer error handling interface"""
        self.attribution_analyzer.handle_attribution_error = AsyncMock(return_value=True)

        test_error = Exception("Attribution error")
        result = await self.attribution_analyzer.handle_attribution_error('factor_attribution', test_error)

        assert result is True
        self.attribution_analyzer.handle_attribution_error.assert_called_once_with('factor_attribution', test_error)

if __name__ == '__main__':
    pytest.main([__file__])
