"""
Unit tests for StrategyCorrelationAnalyzer

Tests cross-strategy correlation monitoring, diversification scoring,
and rebalancing recommendations.
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

import sys
sys.path.insert(0, '/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

from core_engine.trading.strategies.correlation_analyzer import (
    StrategyCorrelationAnalyzer,
    CorrelationLevel,
    StrategyPairCorrelation,
    DiversificationReport
)


@pytest.fixture
def mock_strategy_manager():
    """Mock StrategyManager"""
    return Mock()


@pytest.fixture
def correlation_analyzer(mock_strategy_manager):
    """Create StrategyCorrelationAnalyzer instance"""
    config = {
        'correlation_window_days': 30,
        'min_data_points': 20,
        'analysis_frequency_hours': 24
    }
    return StrategyCorrelationAnalyzer(mock_strategy_manager, config)


class TestStrategyCorrelationAnalyzer:
    """Test suite for StrategyCorrelationAnalyzer"""
    
    def test_initialization(self, correlation_analyzer):
        """Test analyzer initializes correctly"""
        assert correlation_analyzer is not None
        assert correlation_analyzer.independent_threshold == 0.3
        assert correlation_analyzer.moderate_threshold == 0.7
        assert correlation_analyzer.high_threshold == 0.9
        assert correlation_analyzer.correlation_window_days == 30
        assert correlation_analyzer.total_analyses == 0
    
    def test_record_strategy_return(self, correlation_analyzer):
        """Test recording strategy returns"""
        timestamp = datetime.now()
        
        correlation_analyzer.record_strategy_return('momentum_1', 0.015, timestamp)
        
        assert 'momentum_1' in correlation_analyzer.returns_history
        assert len(correlation_analyzer.returns_history['momentum_1']) == 1
        
        ts, ret = correlation_analyzer.returns_history['momentum_1'][0]
        assert ts == timestamp
        assert ret == 0.015
    
    def test_record_multiple_returns(self, correlation_analyzer):
        """Test recording multiple returns for same strategy"""
        for i in range(5):
            correlation_analyzer.record_strategy_return('momentum_1', 0.01 * i)
        
        assert len(correlation_analyzer.returns_history['momentum_1']) == 5
    
    def test_determine_correlation_level(self, correlation_analyzer):
        """Test correlation level determination"""
        assert correlation_analyzer._determine_correlation_level(0.2) == CorrelationLevel.INDEPENDENT
        assert correlation_analyzer._determine_correlation_level(0.5) == CorrelationLevel.MODERATE
        assert correlation_analyzer._determine_correlation_level(0.8) == CorrelationLevel.HIGH
        assert correlation_analyzer._determine_correlation_level(0.95) == CorrelationLevel.EXTREME
        
        # Test negative correlations
        assert correlation_analyzer._determine_correlation_level(-0.2) == CorrelationLevel.INDEPENDENT
        assert correlation_analyzer._determine_correlation_level(-0.8) == CorrelationLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_analyze_insufficient_strategies(self, correlation_analyzer):
        """Test analysis with insufficient strategies (<2)"""
        # Only one strategy
        correlation_analyzer.record_strategy_return('momentum_1', 0.01)
        
        report = await correlation_analyzer.analyze_strategy_correlations()
        
        assert report.strategy_count == 1
        assert report.diversification_score == 100  # Perfect with <2 strategies
        assert len(report.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_insufficient_data(self, correlation_analyzer):
        """Test analysis with insufficient data points"""
        # Two strategies but not enough data
        for i in range(5):  # Less than min_data_points (20)
            correlation_analyzer.record_strategy_return('momentum_1', 0.01 * i)
            correlation_analyzer.record_strategy_return('mean_reversion_1', -0.01 * i)
        
        report = await correlation_analyzer.analyze_strategy_correlations()
        
        assert len(report.recommendations) > 0
        assert 'Insufficient data' in report.recommendations[0] or report.strategy_count < 2
    
    @pytest.mark.asyncio
    async def test_analyze_independent_strategies(self, correlation_analyzer):
        """Test analysis with independent strategies (low correlation)"""
        # Generate independent returns
        np.random.seed(42)
        for i in range(30):
            correlation_analyzer.record_strategy_return(
                'momentum_1',
                np.random.normal(0.01, 0.02),
                datetime.now() - timedelta(days=30-i)
            )
            correlation_analyzer.record_strategy_return(
                'mean_reversion_1',
                np.random.normal(0.01, 0.02),
                datetime.now() - timedelta(days=30-i)
            )
        
        report = await correlation_analyzer.analyze_strategy_correlations()
        
        assert report.strategy_count == 2
        # Should have good diversification (independent strategies)
        assert report.diversification_score > 60
        assert len(report.high_correlations) == 0  # No high correlations
    
    @pytest.mark.asyncio
    async def test_analyze_highly_correlated_strategies(self, correlation_analyzer):
        """Test analysis with highly correlated strategies"""
        # Generate highly correlated returns
        np.random.seed(42)
        base_returns = [np.random.normal(0.01, 0.02) for _ in range(30)]
        
        for i, ret in enumerate(base_returns):
            correlation_analyzer.record_strategy_return(
                'momentum_1',
                ret,
                datetime.now() - timedelta(days=30-i)
            )
            # Second strategy has same returns + small noise
            correlation_analyzer.record_strategy_return(
                'momentum_2',
                ret + np.random.normal(0, 0.001),
                datetime.now() - timedelta(days=30-i)
            )
        
        report = await correlation_analyzer.analyze_strategy_correlations()
        
        assert report.strategy_count == 2
        # Should have poor diversification (highly correlated)
        assert report.diversification_score < 40
        # Should detect high correlation
        assert len(report.high_correlations) == 1
        
        high_corr = report.high_correlations[0]
        assert high_corr.level in [CorrelationLevel.HIGH, CorrelationLevel.EXTREME]
        assert high_corr.correlation > 0.7
    
    @pytest.mark.asyncio
    async def test_analyze_three_strategies_mixed(self, correlation_analyzer):
        """Test analysis with three strategies (mixed correlations)"""
        np.random.seed(42)
        
        # Strategy 1 & 2: Highly correlated
        base_returns = [np.random.normal(0.01, 0.02) for _ in range(30)]
        
        for i, ret in enumerate(base_returns):
            ts = datetime.now() - timedelta(days=30-i)
            
            # Strategy 1 & 2 highly correlated
            correlation_analyzer.record_strategy_return('momentum_1', ret, ts)
            correlation_analyzer.record_strategy_return('momentum_2', ret + np.random.normal(0, 0.001), ts)
            
            # Strategy 3 independent
            correlation_analyzer.record_strategy_return(
                'mean_reversion_1',
                np.random.normal(0.01, 0.02),
                ts
            )
        
        report = await correlation_analyzer.analyze_strategy_correlations()
        
        assert report.strategy_count == 3
        # Should have one high correlation pair (momentum_1 & momentum_2)
        assert len(report.high_correlations) >= 1
    
    def test_calculate_diversification_score(self, correlation_analyzer):
        """Test diversification score calculation"""
        # Perfect negative correlation (-1, -1, -1) → score = 100
        corr_matrix_neg = np.array([
            [1.0, -1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [-1.0, -1.0, 1.0]
        ])
        score_neg = correlation_analyzer._calculate_diversification_score(corr_matrix_neg)
        assert score_neg == 100
        
        # Perfect positive correlation (1, 1, 1) → score = 0
        corr_matrix_pos = np.array([
            [1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0]
        ])
        score_pos = correlation_analyzer._calculate_diversification_score(corr_matrix_pos)
        assert score_pos == 0
        
        # Zero correlation (0, 0, 0) → score = 100
        corr_matrix_zero = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ])
        score_zero = correlation_analyzer._calculate_diversification_score(corr_matrix_zero)
        assert score_zero == 100
    
    def test_generate_recommendations_good_diversification(self, correlation_analyzer):
        """Test recommendations with good diversification"""
        high_correlations = []  # No high correlations
        strategies = ['momentum_1', 'mean_reversion_1', 'stat_arb_1']
        
        recommendations = correlation_analyzer._generate_recommendations(high_correlations, strategies)
        
        assert len(recommendations) > 0
        assert '✅' in recommendations[0]  # Good diversification message
    
    def test_generate_recommendations_high_correlations(self, correlation_analyzer):
        """Test recommendations with high correlations"""
        high_correlations = [
            StrategyPairCorrelation(
                strategy_a='momentum_1',
                strategy_b='momentum_2',
                correlation=0.85,
                level=CorrelationLevel.HIGH,
                data_points=30
            ),
            StrategyPairCorrelation(
                strategy_a='momentum_1',
                strategy_b='momentum_3',
                correlation=0.82,
                level=CorrelationLevel.HIGH,
                data_points=30
            )
        ]
        strategies = ['momentum_1', 'momentum_2', 'momentum_3']
        
        recommendations = correlation_analyzer._generate_recommendations(high_correlations, strategies)
        
        assert len(recommendations) > 0
        # Should recommend action on momentum_1 (involved in multiple high correlations)
        assert any('momentum_1' in rec for rec in recommendations)
    
    def test_generate_recommendations_extreme_correlation(self, correlation_analyzer):
        """Test recommendations with extreme correlation"""
        high_correlations = [
            StrategyPairCorrelation(
                strategy_a='momentum_1',
                strategy_b='momentum_2',
                correlation=0.95,
                level=CorrelationLevel.EXTREME,
                data_points=30
            )
        ]
        strategies = ['momentum_1', 'momentum_2']
        
        recommendations = correlation_analyzer._generate_recommendations(high_correlations, strategies)
        
        assert len(recommendations) > 0
        # Should have critical/extreme recommendation
        assert any('EXTREME' in rec or 'disabling' in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_check_correlation_alerts_first_time(self, correlation_analyzer):
        """Test alert checking when never analyzed before"""
        should_analyze = await correlation_analyzer.check_correlation_alerts()
        
        assert should_analyze is True
    
    @pytest.mark.asyncio
    async def test_check_correlation_alerts_too_soon(self, correlation_analyzer):
        """Test alert checking when analyzed recently"""
        correlation_analyzer.last_analysis_time = datetime.now()
        
        should_analyze = await correlation_analyzer.check_correlation_alerts()
        
        assert should_analyze is False
    
    @pytest.mark.asyncio
    async def test_check_correlation_alerts_time_passed(self, correlation_analyzer):
        """Test alert checking when enough time has passed"""
        correlation_analyzer.last_analysis_time = datetime.now() - timedelta(hours=25)
        correlation_analyzer.analysis_frequency_hours = 24
        
        should_analyze = await correlation_analyzer.check_correlation_alerts()
        
        assert should_analyze is True
    
    def test_get_statistics(self, correlation_analyzer):
        """Test getting correlation statistics"""
        stats = correlation_analyzer.get_correlation_statistics()
        
        assert 'total_analyses' in stats
        assert 'high_correlation_alerts' in stats
        assert 'strategies_tracked' in stats
    
    @pytest.mark.asyncio
    async def test_generate_report(self, correlation_analyzer):
        """Test generating correlation report"""
        # Add some returns
        for i in range(25):
            correlation_analyzer.record_strategy_return('momentum_1', 0.01 * i)
            correlation_analyzer.record_strategy_return('mean_reversion_1', -0.01 * i)
        
        # Run analysis
        await correlation_analyzer.analyze_strategy_correlations()
        
        # Generate report
        report_str = correlation_analyzer.generate_correlation_report()
        
        assert 'STRATEGY CORRELATION REPORT' in report_str
        assert 'Total Analyses:' in report_str
        assert 'CURRENT DIVERSIFICATION:' in report_str
    
    @pytest.mark.asyncio
    async def test_correlation_history_tracking(self, correlation_analyzer):
        """Test correlation reports are stored in history"""
        # Add data
        for i in range(25):
            correlation_analyzer.record_strategy_return('momentum_1', 0.01 * i)
            correlation_analyzer.record_strategy_return('mean_reversion_1', -0.01 * i)
        
        initial_count = len(correlation_analyzer.correlation_history)
        
        await correlation_analyzer.analyze_strategy_correlations()
        
        assert len(correlation_analyzer.correlation_history) == initial_count + 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

