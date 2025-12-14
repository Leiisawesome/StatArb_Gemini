#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Attribution Analyzer
===============================================

Tests factor-based, sector-based, and security-level attribution analysis.

Test Coverage:
- Factor model building and regression analysis
- Factor loading calculations and significance testing
- Sector attribution with allocation and selection effects
- Security-level contribution analysis
- Attribution result generation and validation
- Error handling and edge cases

Author: StatArb_Gemini Test Suite
Date: November 4, 2025
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from unittest.mock import patch

from core_engine.analytics.attribution_analyzer import (
    AttributionAnalyzer,
    AttributionConfig,
    AttributionMethod,
    AttributionType,
    AttributionResult,
    FactorModelAnalyzer,
    SectorAttributionAnalyzer
)

class TestFactorModelAnalyzer:
    """Test FactorModelAnalyzer functionality"""

    @pytest.fixture
    def config(self):
        """Create attribution config"""
        return AttributionConfig(
            attribution_method=AttributionMethod.FACTOR_MODEL,
            min_observations=30,
            risk_model_factors=["market", "size", "value"]
        )

    @pytest.fixture
    def analyzer(self, config):
        """Create factor model analyzer"""
        return FactorModelAnalyzer(config)

    @pytest.fixture
    def sample_returns(self):
        """Create sample portfolio returns"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        returns = pd.Series(
            np.random.normal(0.001, 0.02, 100),
            index=dates,
            name='portfolio'
        )
        return returns

    @pytest.fixture
    def sample_factor_returns(self):
        """Create sample factor returns"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        factors = pd.DataFrame({
            'market': np.random.normal(0.0008, 0.015, 100),
            'size': np.random.normal(0.0005, 0.012, 100),
            'value': np.random.normal(0.0003, 0.010, 100)
        }, index=dates)
        return factors

    def test_build_factor_model_basic(self, analyzer, sample_returns, sample_factor_returns):
        """Test basic factor model building"""
        model = analyzer.build_factor_model(sample_returns, sample_factor_returns)

        assert isinstance(model, dict)
        assert 'model' in model
        assert 'factor_loadings' in model
        assert 'factor_contributions' in model
        assert 'alpha' in model
        assert 'diagnostics' in model

    def test_build_factor_model_insufficient_data(self, analyzer):
        """Test factor model with insufficient data"""
        short_returns = pd.Series([0.01, 0.02, 0.03], name='portfolio')
        short_factors = pd.DataFrame({
            'market': [0.01, 0.02, 0.03],
            'size': [0.005, 0.01, 0.015]
        })

        model = analyzer.build_factor_model(short_returns, short_factors)

        # Should return empty dict for insufficient data
        assert model == {}

    def test_factor_loadings_calculation(self, analyzer, sample_returns, sample_factor_returns):
        """Test factor loading calculations"""
        model = analyzer.build_factor_model(sample_returns, sample_factor_returns)

        factor_loadings = model.get('factor_loadings', {})
        assert isinstance(factor_loadings, dict)
        assert 'market' in factor_loadings
        assert 'size' in factor_loadings
        assert 'value' in factor_loadings

        # All loadings should be numeric
        for loading in factor_loadings.values():
            assert isinstance(loading, (int, float))

    def test_factor_contributions_calculation(self, analyzer, sample_returns, sample_factor_returns):
        """Test factor contribution calculations"""
        model = analyzer.build_factor_model(sample_returns, sample_factor_returns)

        factor_contributions = model.get('factor_contributions', {})
        assert isinstance(factor_contributions, dict)

        # Contributions should be numeric
        for contribution in factor_contributions.values():
            assert isinstance(contribution, (int, float))

    def test_model_diagnostics(self, analyzer, sample_returns, sample_factor_returns):
        """Test model diagnostics calculation"""
        model = analyzer.build_factor_model(sample_returns, sample_factor_returns)

        diagnostics = model.get('diagnostics', {})
        assert isinstance(diagnostics, dict)

        expected_keys = ['r_squared', 'alpha', 'residual_volatility', 'observations']
        for key in expected_keys:
            assert key in diagnostics
            assert isinstance(diagnostics[key], (int, float))

    def test_calculate_factor_attribution(self, analyzer, sample_returns, sample_factor_returns):
        """Test factor attribution calculation"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 4, 10)

        result = analyzer.calculate_factor_attribution(
            sample_returns, sample_factor_returns, start_date, end_date
        )

        assert isinstance(result, AttributionResult)
        assert result.attribution_type == AttributionType.FACTOR
        assert result.attribution_method == AttributionMethod.FACTOR_MODEL

    def test_factor_significance_testing(self, analyzer, sample_returns, sample_factor_returns):
        """Test factor significance testing"""
        model = analyzer.build_factor_model(sample_returns, sample_factor_returns)

        diagnostics = model.get('diagnostics', {})
        factor_significance = diagnostics.get('factor_significance', {})

        assert isinstance(factor_significance, dict)
        # Should have significance for each factor
        assert len(factor_significance) > 0

class TestSectorAttributionAnalyzer:
    """Test SectorAttributionAnalyzer functionality"""

    @pytest.fixture
    def config(self):
        """Create attribution config"""
        return AttributionConfig()

    @pytest.fixture
    def analyzer(self, config):
        """Create sector attribution analyzer"""
        return SectorAttributionAnalyzer(config)

    @pytest.fixture
    def sample_weights(self):
        """Create sample portfolio weights"""
        return pd.Series({
            'AAPL': 0.3,
            'MSFT': 0.25,
            'GOOGL': 0.2,
            'AMZN': 0.15,
            'TSLA': 0.1
        })

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns"""
        return pd.Series({
            'AAPL': 0.02,
            'MSFT': 0.015,
            'GOOGL': 0.025,
            'AMZN': 0.01,
            'TSLA': 0.03
        })

    @pytest.fixture
    def benchmark_weights(self):
        """Create benchmark weights"""
        return pd.Series({
            'AAPL': 0.25,
            'MSFT': 0.2,
            'GOOGL': 0.18,
            'AMZN': 0.17,
            'TSLA': 0.2
        })

    @pytest.fixture
    def benchmark_returns(self):
        """Create benchmark returns"""
        return pd.Series({
            'AAPL': 0.018,
            'MSFT': 0.012,
            'GOOGL': 0.022,
            'AMZN': 0.008,
            'TSLA': 0.028
        })

    def test_calculate_sector_attribution(self, analyzer, sample_weights, sample_returns, benchmark_weights, benchmark_returns):
        """Test sector attribution calculation"""
        result = analyzer.calculate_sector_attribution(
            sample_weights, sample_returns, benchmark_weights, benchmark_returns
        )

        assert isinstance(result, AttributionResult)
        assert result.attribution_type == AttributionType.SECTOR

    def test_allocation_effect_calculation(self, analyzer, sample_weights, benchmark_weights, sample_returns, benchmark_returns):
        """Test allocation effect calculation"""
        # Create sector mappings
        sector_map = {
            'AAPL': 'Technology',
            'MSFT': 'Technology',
            'GOOGL': 'Technology',
            'AMZN': 'Consumer',
            'TSLA': 'Consumer'
        }

        allocation_effect = analyzer._calculate_allocation_effect(
            sample_weights, benchmark_weights, sample_returns, benchmark_returns, sector_map
        )

        assert isinstance(allocation_effect, dict)

    def test_selection_effect_calculation(self, analyzer, sample_weights, benchmark_weights, sample_returns, benchmark_returns):
        """Test selection effect calculation"""
        sector_map = {
            'AAPL': 'Technology',
            'MSFT': 'Technology',
            'GOOGL': 'Technology',
            'AMZN': 'Consumer',
            'TSLA': 'Consumer'
        }

        selection_effect = analyzer._calculate_selection_effect(
            sample_weights, benchmark_weights, sample_returns, benchmark_returns, sector_map
        )

        assert isinstance(selection_effect, dict)

class TestAttributionAnalyzer:
    """Test AttributionAnalyzer functionality"""

    @pytest.fixture
    def config(self):
        """Create attribution config"""
        return AttributionConfig(
            attribution_method=AttributionMethod.FACTOR_MODEL,
            benchmark_symbol="SPY"
        )

    @pytest.fixture
    def analyzer(self, config):
        """Create attribution analyzer"""
        return AttributionAnalyzer(config)

    @pytest.fixture
    def sample_portfolio_returns(self):
        """Create sample portfolio returns series"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        returns = pd.Series(
            np.random.normal(0.001, 0.02, 50),
            index=dates,
            name='portfolio'
        )
        return returns

    @pytest.fixture
    def sample_factor_returns(self):
        """Create sample factor returns DataFrame"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        factors = pd.DataFrame({
            'market': np.random.normal(0.0008, 0.015, 50),
            'size': np.random.normal(0.0005, 0.012, 50),
            'value': np.random.normal(0.0003, 0.010, 50)
        }, index=dates)
        return factors

    def test_initialization(self, analyzer, config):
        """Test analyzer initialization"""
        assert analyzer.config == config
        assert analyzer.factor_analyzer is not None
        assert analyzer.sector_analyzer is not None

    @pytest.mark.asyncio
    async def test_analyze_attribution_factor_type(self, analyzer, sample_portfolio_returns, sample_factor_returns):
        """Test factor attribution analysis"""
        result = await analyzer.analyze_attribution(
            sample_portfolio_returns,
            factor_returns=sample_factor_returns,
            attribution_type=AttributionType.FACTOR
        )

        assert isinstance(result, AttributionResult)
        assert result.attribution_type == AttributionType.FACTOR

    @pytest.mark.asyncio
    async def test_analyze_attribution_sector_type(self, analyzer, sample_portfolio_returns):
        """Test sector attribution analysis"""
        # Mock the sector analyzer to avoid benchmark data requirements
        with patch.object(analyzer.sector_analyzer, 'calculate_sector_attribution') as mock_method:
            mock_result = AttributionResult(
                symbol="test",
                analysis_date=datetime.now(),
                attribution_method=AttributionMethod.BRINSON,
                attribution_type=AttributionType.SECTOR,
                analysis_period=(datetime.now(), datetime.now())
            )
            mock_method.return_value = mock_result

            result = await analyzer.analyze_attribution(
                sample_portfolio_returns,
                attribution_type=AttributionType.SECTOR
            )

            assert isinstance(result, AttributionResult)
            assert result.attribution_type == AttributionType.SECTOR

    @pytest.mark.asyncio
    async def test_analyze_attribution_security_type(self, analyzer, sample_portfolio_returns):
        """Test security attribution analysis"""
        weights = pd.Series([0.2, 0.2, 0.2, 0.2, 0.2], index=sample_portfolio_returns.index[:5])

        result = await analyzer.analyze_attribution(
            sample_portfolio_returns,
            portfolio_weights=weights,
            attribution_type=AttributionType.SECURITY
        )

        assert isinstance(result, AttributionResult)
        assert result.attribution_type == AttributionType.SECURITY

    @pytest.mark.asyncio
    async def test_analyze_attribution_date_filtering(self, analyzer, sample_portfolio_returns, sample_factor_returns):
        """Test attribution analysis with date filtering"""
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 2, 15)

        result = await analyzer.analyze_attribution(
            sample_portfolio_returns,
            factor_returns=sample_factor_returns,
            start_date=start_date,
            end_date=end_date
        )

        assert isinstance(result, AttributionResult)
        assert result.analysis_period[0] >= start_date
        assert result.analysis_period[1] <= end_date

    @pytest.mark.asyncio
    async def test_analyze_attribution_error_handling(self, analyzer):
        """Test error handling in attribution analysis"""
        empty_returns = pd.Series([], dtype=float)

        result = await analyzer.analyze_attribution(empty_returns)

        assert isinstance(result, AttributionResult)
        # Should return error result
        assert result.symbol == "error"

    @pytest.mark.asyncio
    async def test_get_default_factor_returns_error(self, analyzer):
        """Test that default factor returns raises error"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        with pytest.raises(Exception):  # PerformanceDataUnavailableError
            await analyzer._get_default_factor_returns(start_date, end_date)

    @pytest.mark.asyncio
    async def test_get_benchmark_returns_error(self, analyzer):
        """Test that benchmark returns raises error"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        with pytest.raises(Exception):  # BenchmarkDataUnavailableError
            await analyzer._get_benchmark_returns(start_date, end_date)

    def test_attribution_history_storage(self, analyzer):
        """Test attribution history storage"""
        assert len(analyzer._attribution_history) == 0

        # Manually add a result to test storage
        result = AttributionResult(
            symbol="test",
            analysis_date=datetime.now(),
            attribution_method=AttributionMethod.FACTOR_MODEL,
            attribution_type=AttributionType.FACTOR,
            analysis_period=(datetime.now(), datetime.now())
        )

        analyzer._attribution_history.append(result)
        assert len(analyzer._attribution_history) == 1

    @pytest.mark.asyncio
    async def test_generate_attribution_report(self, analyzer, sample_portfolio_returns, sample_factor_returns):
        """Test attribution report generation"""
        # Mock the generate method to avoid complex setup
        with patch.object(analyzer, 'analyze_attribution') as mock_analyze:
            mock_result = AttributionResult(
                symbol="test_portfolio",
                analysis_date=datetime.now(),
                attribution_method=AttributionMethod.FACTOR_MODEL,
                attribution_type=AttributionType.FACTOR,
                analysis_period=(datetime.now(), datetime.now())
            )
            mock_analyze.return_value = mock_result

            report = await analyzer.generate_attribution_report(
                sample_portfolio_returns,
                portfolio_name="test_portfolio",
                factor_returns=sample_factor_returns
            )

            assert report is not None
            # Report structure depends on implementation

    def test_thread_safety(self, analyzer):
        """Test thread safety of attribution analyzer"""
        # Test that lock exists and is accessible
        assert hasattr(analyzer, '_lock')
        assert analyzer._lock is not None

    @pytest.mark.asyncio
    async def test_multiple_attribution_types(self, analyzer, sample_portfolio_returns):
        """Test switching between different attribution types"""
        # Test factor attribution
        factor_result = await analyzer.analyze_attribution(
            sample_portfolio_returns,
            attribution_type=AttributionType.FACTOR
        )
        assert factor_result.attribution_type == AttributionType.FACTOR

        # Test security attribution
        security_result = await analyzer.analyze_attribution(
            sample_portfolio_returns,
            attribution_type=AttributionType.SECURITY
        )
        assert security_result.attribution_type == AttributionType.SECURITY

    def test_config_validation(self):
        """Test configuration validation"""
        # Valid config should work
        config = AttributionConfig()
        analyzer = AttributionAnalyzer(config)
        assert analyzer.config == config

        # None config should use defaults
        analyzer_default = AttributionAnalyzer(None)
        assert analyzer_default.config is not None