#!/usr/bin/env python3
"""
Test Suite for Regime Analytics Module
======================================

Comprehensive tests for core_structure/analytics/regime_analytics.py
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Tuple

# Import the module under test
from core_structure.analytics.regime_analytics import (
    RegimeAnalyticsEngine,
    RegimePerformanceMetrics,
    RegimeTransitionAnalysis,
    StrategyEffectivenessAnalysis,
    RegimeAnalyticsResult,
    RegimeAnalyticsType,
    regime_analytics
)


class TestRegimePerformanceMetrics:
    """Test RegimePerformanceMetrics dataclass"""

    def test_initialization(self):
        """Test RegimePerformanceMetrics initialization"""
        metrics = RegimePerformanceMetrics(
            regime_name="bull_market",
            total_duration_minutes=1440,  # 1 day
            total_return=0.15,
            annualized_return=0.12,
            volatility=0.25,
            sharpe_ratio=0.48,
            max_drawdown=-0.08,
            win_rate=0.55,
            profit_factor=1.8,
            total_trades=50,
            winning_trades=28,
            losing_trades=22,
            avg_trade_return=0.003
        )

        assert metrics.regime_name == "bull_market"
        assert metrics.total_duration_minutes == 1440
        assert metrics.total_return == 0.15
        assert metrics.annualized_return == 0.12
        assert metrics.volatility == 0.25
        assert metrics.sharpe_ratio == 0.48
        assert metrics.max_drawdown == -0.08
        assert metrics.win_rate == 0.55
        assert metrics.profit_factor == 1.8
        assert metrics.total_trades == 50
        assert metrics.winning_trades == 28
        assert metrics.losing_trades == 22
        assert metrics.avg_trade_return == 0.003

    def test_default_values(self):
        """Test default values"""
        metrics = RegimePerformanceMetrics(regime_name="test_regime")

        assert metrics.regime_name == "test_regime"
        assert metrics.total_duration_minutes == 0
        assert metrics.total_return == 0.0
        assert metrics.annualized_return == 0.0
        assert metrics.volatility == 0.0
        assert metrics.sharpe_ratio == 0.0
        assert metrics.max_drawdown == 0.0
        assert metrics.win_rate == 0.0
        assert metrics.profit_factor == 0.0
        assert metrics.total_trades == 0
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 0
        assert metrics.avg_trade_return == 0.0
        assert metrics.var_95 == 0.0
        assert metrics.expected_shortfall == 0.0
        assert metrics.calmar_ratio == 0.0
        assert metrics.strategy_returns == {}
        assert metrics.strategy_allocations == {}


class TestRegimeTransitionAnalysis:
    """Test RegimeTransitionAnalysis dataclass"""

    def test_initialization(self):
        """Test RegimeTransitionAnalysis initialization"""
        analysis = RegimeTransitionAnalysis(
            from_regime="bull_market",
            to_regime="sideways",
            transition_count=5,
            avg_transition_duration=120.0,  # 2 hours
            transition_performance=0.02,
            transition_volatility=0.15,
            predictability_score=0.75
        )

        assert analysis.from_regime == "bull_market"
        assert analysis.to_regime == "sideways"
        assert analysis.transition_count == 5
        assert analysis.avg_transition_duration == 120.0
        assert analysis.transition_performance == 0.02
        assert analysis.transition_volatility == 0.15
        assert analysis.predictability_score == 0.75
        assert analysis.common_triggers == []
        assert analysis.market_conditions == {}


class TestStrategyEffectivenessAnalysis:
    """Test StrategyEffectivenessAnalysis dataclass"""

    def test_initialization(self):
        """Test StrategyEffectivenessAnalysis initialization"""
        analysis = StrategyEffectivenessAnalysis(
            strategy_name="momentum_strategy",
            optimal_regimes=["bull_market", "high_volatility"],
            suboptimal_regimes=["sideways"],
            consistency_score=0.85,
            adaptability_score=0.72,
            regime_sensitivity=0.35
        )

        assert analysis.strategy_name == "momentum_strategy"
        assert analysis.optimal_regimes == ["bull_market", "high_volatility"]
        assert analysis.suboptimal_regimes == ["sideways"]
        assert analysis.consistency_score == 0.85
        assert analysis.adaptability_score == 0.72
        assert analysis.regime_sensitivity == 0.35
        assert analysis.regime_performance == {}


class TestRegimeAnalyticsResult:
    """Test RegimeAnalyticsResult dataclass"""

    def test_initialization(self):
        """Test RegimeAnalyticsResult initialization"""
        result = RegimeAnalyticsResult(
            analysis_type=RegimeAnalyticsType.PERFORMANCE_ATTRIBUTION,
            timestamp=datetime.now(),
            time_period=(datetime(2024, 1, 1), datetime(2024, 12, 31)),
            total_return=0.25,
            best_regime="bull_market",
            worst_regime="bear_market",
            predicted_next_regime="sideways",
            regime_confidence=0.82,
            expected_regime_duration=720,  # 12 hours
            data_quality_score=0.95,
            analysis_confidence=0.88
        )

        assert result.analysis_type == RegimeAnalyticsType.PERFORMANCE_ATTRIBUTION
        assert isinstance(result.timestamp, datetime)
        assert result.time_period == (datetime(2024, 1, 1), datetime(2024, 12, 31))
        assert result.total_return == 0.25
        assert result.best_regime == "bull_market"
        assert result.worst_regime == "bear_market"
        assert result.predicted_next_regime == "sideways"
        assert result.regime_confidence == 0.82
        assert result.expected_regime_duration == 720
        assert result.data_quality_score == 0.95
        assert result.analysis_confidence == 0.88
        assert result.regime_performance == {}
        assert result.transition_analysis == []
        assert result.strategy_effectiveness == {}
        assert result.regime_attribution == {}
        assert result.recommendations == []


class TestRegimeAnalyticsType:
    """Test RegimeAnalyticsType enum"""

    def test_enum_values(self):
        """Test RegimeAnalyticsType enum values"""
        assert RegimeAnalyticsType.PERFORMANCE_ATTRIBUTION.value == "performance_attribution"
        assert RegimeAnalyticsType.REGIME_TRANSITION.value == "regime_transition"
        assert RegimeAnalyticsType.STRATEGY_EFFECTIVENESS.value == "strategy_effectiveness"
        assert RegimeAnalyticsType.RISK_ATTRIBUTION.value == "risk_attribution"
        assert RegimeAnalyticsType.CORRELATION_ANALYSIS.value == "correlation_analysis"
        assert RegimeAnalyticsType.PREDICTIVE_ANALYTICS.value == "predictive_analytics"


class TestRegimeAnalyticsEngine:
    """Test RegimeAnalyticsEngine class"""

    @pytest.fixture
    def engine(self):
        """Create a test RegimeAnalyticsEngine instance"""
        return RegimeAnalyticsEngine(
            lookback_days=30,
            min_regime_duration=5
        )

    @pytest.fixture
    def sample_regime_data(self):
        """Generate sample regime data"""
        dates = pd.date_range('2024-01-01', periods=1000, freq='1min')
        np.random.seed(42)

        # Generate regime sequence
        regimes = []
        current_regime = "bull_market"
        regime_start = 0

        for i in range(1000):
            # Change regime every ~200 minutes (with some randomness)
            if i > 0 and i % np.random.randint(150, 250) == 0:
                old_regime = current_regime
                # Cycle through regimes
                regime_options = ["bull_market", "bear_market", "sideways", "high_volatility"]
                current_regime = np.random.choice(regime_options)
                if current_regime != old_regime:
                    regime_start = i

            regimes.append(current_regime)

        return pd.DataFrame({
            'timestamp': dates,
            'regime': regimes,
            'regime_start': [i == regime_start for i in range(1000)]
        })

    @pytest.fixture
    def sample_performance_data(self):
        """Generate sample performance data"""
        dates = pd.date_range('2024-01-01', periods=1000, freq='1min')
        np.random.seed(43)

        # Generate returns that vary by regime
        returns = []
        for i in range(1000):
            base_return = 0.001  # Base return

            # Add regime-specific effects (simplified)
            if i % 4 == 0:  # bull_market
                base_return += np.random.normal(0.002, 0.01)
            elif i % 4 == 1:  # bear_market
                base_return += np.random.normal(-0.002, 0.015)
            elif i % 4 == 2:  # sideways
                base_return += np.random.normal(0.0, 0.005)
            else:  # high_volatility
                base_return += np.random.normal(0.001, 0.03)

            returns.append(base_return)

        return pd.DataFrame({
            'timestamp': dates,
            'returns': returns,
            'strategy_a_returns': np.array(returns) * np.random.uniform(0.8, 1.2, 1000),
            'strategy_b_returns': np.array(returns) * np.random.uniform(0.9, 1.1, 1000)
        })

    def test_initialization(self, engine):
        """Test RegimeAnalyticsEngine initialization"""
        assert engine.lookback_days == 30
        assert engine.min_regime_duration == 5

        # Check data structures
        assert len(engine.regime_history) == 0
        assert len(engine.performance_history) == 0
        assert len(engine.transition_history) == 0

        # Check analytics cache
        assert len(engine.analytics_cache) == 0
        assert engine.cache_ttl == timedelta(minutes=5)

        # Check tracking dictionaries
        assert len(engine.regime_performance_tracker) == 0
        assert len(engine.strategy_performance_tracker) == 0

    def test_integrate_phase_systems(self, engine):
        """Test integration with phase systems"""
        # Mock phase systems
        mock_regime_system = Mock()
        mock_portfolio_manager = Mock()
        mock_orchestrator = Mock()

        engine.integrate_phase_systems(
            regime_system=mock_regime_system,
            portfolio_manager=mock_portfolio_manager,
            orchestrator=mock_orchestrator
        )

        assert engine.regime_system == mock_regime_system
        assert engine.portfolio_manager == mock_portfolio_manager
        assert engine.orchestrator == mock_orchestrator

    @pytest.mark.asyncio
    async def test_analyze_regime_performance(self, engine, sample_regime_data, sample_performance_data):
        """Test regime performance analysis"""
        # Mock the data collection methods
        with patch.object(engine, '_collect_regime_data', return_value=sample_regime_data), \
             patch.object(engine, '_collect_performance_data', return_value=sample_performance_data), \
             patch.object(engine, '_calculate_regime_performance') as mock_calc_performance, \
             patch.object(engine, '_analyze_regime_transitions') as mock_analyze_transitions, \
             patch.object(engine, '_analyze_strategy_effectiveness') as mock_analyze_strategy, \
             patch.object(engine, '_predict_next_regime') as mock_predict, \
             patch.object(engine, '_generate_recommendations') as mock_recommend, \
             patch.object(engine, '_calculate_data_quality') as mock_data_quality:

            # Setup mocks
            mock_calc_performance.return_value = {
                'bull_market': RegimePerformanceMetrics(
                    regime_name='bull_market',
                    total_return=0.15,
                    annualized_return=0.12
                )
            }
            mock_analyze_transitions.return_value = []
            mock_analyze_strategy.return_value = {}
            mock_predict.return_value = ('sideways', 0.8, 300)
            mock_recommend.return_value = ['Diversify strategies']
            mock_data_quality.return_value = 0.9

            time_period = (datetime(2024, 1, 1), datetime(2024, 1, 2))
            result = await engine.analyze_regime_performance(time_period)

            assert isinstance(result, RegimeAnalyticsResult)
            assert result.analysis_type == RegimeAnalyticsType.PERFORMANCE_ATTRIBUTION
            assert result.time_period == time_period
            assert result.total_return == 0.15  # Sum of regime returns
            assert result.best_regime == 'bull_market'
            assert result.worst_regime == 'bull_market'  # Only one regime
            assert result.predicted_next_regime == 'sideways'
            assert result.regime_confidence == 0.8
            assert result.expected_regime_duration == 300

    def test_collect_regime_data(self, engine, sample_regime_data):
        """Test regime data collection"""
        # Add sample data to history
        for _, row in sample_regime_data.iterrows():
            engine.regime_history.append({
                'timestamp': row['timestamp'],
                'regime': row['regime']
            })

        # Test data collection for a time period
        time_period = (datetime(2024, 1, 1), datetime(2024, 1, 2))
        collected_data = engine._collect_regime_data(time_period)

        assert isinstance(collected_data, pd.DataFrame)
        assert len(collected_data) > 0

    def test_collect_performance_data(self, engine, sample_performance_data):
        """Test performance data collection"""
        # Add sample data to history
        for _, row in sample_performance_data.iterrows():
            engine.performance_history.append({
                'timestamp': row['timestamp'],
                'returns': row['returns'],
                'strategy_returns': {
                    'strategy_a': row['strategy_a_returns'],
                    'strategy_b': row['strategy_b_returns']
                }
            })

        # Test data collection for a time period
        time_period = (datetime(2024, 1, 1), datetime(2024, 1, 2))
        collected_data = engine._collect_performance_data(time_period)

        assert isinstance(collected_data, pd.DataFrame)
        assert len(collected_data) > 0

    def test_calculate_regime_performance(self, engine, sample_regime_data, sample_performance_data):
        """Test regime performance calculation"""
        regime_performance = engine._calculate_regime_performance(
            sample_regime_data,
            sample_performance_data
        )

        assert isinstance(regime_performance, dict)

        # Should have performance metrics for each unique regime
        unique_regimes = sample_regime_data['regime'].unique()
        for regime in unique_regimes:
            if regime in regime_performance:
                assert isinstance(regime_performance[regime], RegimePerformanceMetrics)
                assert regime_performance[regime].regime_name == regime

    def test_analyze_regime_transitions(self, engine, sample_regime_data):
        """Test regime transition analysis"""
        transitions = engine._analyze_regime_transitions(sample_regime_data)

        assert isinstance(transitions, list)

        for transition in transitions:
            assert isinstance(transition, RegimeTransitionAnalysis)
            assert transition.from_regime != transition.to_regime
            assert transition.transition_count > 0

    def test_analyze_strategy_effectiveness(self, engine, sample_regime_data, sample_performance_data):
        """Test strategy effectiveness analysis"""
        strategy_effectiveness = engine._analyze_strategy_effectiveness(
            sample_regime_data,
            sample_performance_data
        )

        assert isinstance(strategy_effectiveness, dict)

        # Should analyze effectiveness for each strategy
        if len(sample_performance_data.columns) > 2:  # Has strategy columns
            for strategy_col in sample_performance_data.columns:
                if strategy_col.endswith('_returns'):
                    strategy_name = strategy_col.replace('_returns', '')
                    if strategy_name in strategy_effectiveness:
                        assert isinstance(strategy_effectiveness[strategy_name], StrategyEffectivenessAnalysis)

    def test_predict_next_regime(self, engine, sample_regime_data):
        """Test next regime prediction"""
        predicted_regime, confidence, duration = engine._predict_next_regime(sample_regime_data)

        assert isinstance(predicted_regime, str)
        assert isinstance(confidence, float)
        assert isinstance(duration, int)
        assert 0 <= confidence <= 1
        assert duration > 0

    def test_generate_recommendations(self, engine):
        """Test recommendation generation"""
        # Create sample regime performance data
        regime_performance = {
            'bull_market': RegimePerformanceMetrics(
                regime_name='bull_market',
                total_return=0.15,
                annualized_return=0.12
            ),
            'sideways': RegimePerformanceMetrics(
                regime_name='sideways',
                total_return=0.02,
                annualized_return=0.015
            )
        }

        strategy_effectiveness = {
            'momentum': StrategyEffectivenessAnalysis(
                strategy_name='momentum',
                optimal_regimes=['bull_market'],
                suboptimal_regimes=['sideways']
            )
        }

        recommendations = engine._generate_recommendations(regime_performance, strategy_effectiveness)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        for rec in recommendations:
            assert isinstance(rec, str)

    def test_calculate_data_quality(self, engine, sample_regime_data, sample_performance_data):
        """Test data quality calculation"""
        quality_score = engine._calculate_data_quality(sample_regime_data, sample_performance_data)

        assert isinstance(quality_score, float)
        assert 0 <= quality_score <= 1


class TestConvenienceFunctions:
    """Test module-level convenience functions"""

    def test_regime_analytics_global_instance(self):
        """Test global regime analytics instance"""
        assert isinstance(regime_analytics, RegimeAnalyticsEngine)
        assert hasattr(regime_analytics, 'analyze_regime_performance')


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def engine(self):
        """Create a test RegimeAnalyticsEngine instance"""
        return RegimeAnalyticsEngine()

    def test_empty_regime_data(self, engine):
        """Test handling of empty regime data"""
        empty_data = pd.DataFrame()

        # Should handle gracefully
        result = engine._calculate_regime_performance(empty_data, pd.DataFrame())
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_single_regime(self, engine):
        """Test analysis with single regime"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        single_regime_data = pd.DataFrame({
            'timestamp': dates,
            'regime': ['bull_market'] * 100
        })

        transitions = engine._analyze_regime_transitions(single_regime_data)

        # Should have no transitions
        assert len(transitions) == 0

    def test_insufficient_data(self, engine):
        """Test with insufficient data"""
        dates = pd.date_range('2024-01-01', periods=5, freq='1min')
        small_data = pd.DataFrame({
            'timestamp': dates,
            'regime': ['bull_market'] * 5,
            'returns': [0.001] * 5
        })

        # Should handle gracefully
        performance = engine._calculate_regime_performance(small_data, small_data)
        assert isinstance(performance, dict)

    @pytest.mark.asyncio
    async def test_invalid_time_period(self, engine):
        """Test invalid time period"""
        # End before start
        invalid_period = (datetime(2024, 1, 2), datetime(2024, 1, 1))

        # Should handle gracefully or raise appropriate error
        with pytest.raises((ValueError, Exception)):
            await engine.analyze_regime_performance(invalid_period)


class TestIntegration:
    """Integration tests combining multiple regime analytics features"""

    @pytest.fixture
    def engine(self):
        """Create a test RegimeAnalyticsEngine instance"""
        return RegimeAnalyticsEngine()

    @pytest.fixture
    def comprehensive_regime_data(self):
        """Generate comprehensive regime data for integration testing"""
        dates = pd.date_range('2024-01-01', periods=2000, freq='1min')
        np.random.seed(42)

        # Generate more complex regime sequence
        regimes = []
        current_regime = "bull_market"
        regime_changes = [0, 500, 1000, 1500]  # Change points

        for i in range(2000):
            if i in regime_changes:
                regime_options = ["bull_market", "bear_market", "sideways", "high_volatility"]
                current_regime = np.random.choice(regime_options)

            regimes.append(current_regime)

        return pd.DataFrame({
            'timestamp': dates,
            'regime': regimes
        })

    @pytest.fixture
    def comprehensive_performance_data(self):
        """Generate comprehensive performance data"""
        dates = pd.date_range('2024-01-01', periods=2000, freq='1min')
        np.random.seed(43)

        # Generate returns with regime-specific patterns
        returns = []
        strategy_a_returns = []
        strategy_b_returns = []

        for i in range(2000):
            # Base market return
            market_return = np.random.normal(0.001, 0.02)

            # Regime-specific adjustments
            if i < 500:  # bull_market
                market_return += np.random.normal(0.003, 0.01)
            elif i < 1000:  # bear_market
                market_return += np.random.normal(-0.003, 0.015)
            elif i < 1500:  # sideways
                market_return += np.random.normal(0.0, 0.005)
            else:  # high_volatility
                market_return += np.random.normal(0.001, 0.04)

            returns.append(market_return)

            # Strategy returns with different regime sensitivities
            strategy_a_returns.append(market_return * np.random.uniform(0.8, 1.3))
            strategy_b_returns.append(market_return * np.random.uniform(0.9, 1.1))

        return pd.DataFrame({
            'timestamp': dates,
            'returns': returns,
            'strategy_a_returns': strategy_a_returns,
            'strategy_b_returns': strategy_b_returns
        })

    @pytest.mark.asyncio
    async def test_full_regime_analytics_workflow(self, engine, comprehensive_regime_data, comprehensive_performance_data):
        """Test complete regime analytics workflow"""
        # Mock data collection methods to return our test data
        with patch.object(engine, '_collect_regime_data', return_value=comprehensive_regime_data), \
             patch.object(engine, '_collect_performance_data', return_value=comprehensive_performance_data):

            time_period = (datetime(2024, 1, 1), datetime(2024, 1, 2))

            # Run full analysis
            result = await engine.analyze_regime_performance(time_period)

            assert isinstance(result, RegimeAnalyticsResult)

            # Verify key components are present
            assert len(result.regime_performance) > 0
            assert len(result.transition_analysis) >= 0  # May be 0 if no transitions in period
            assert len(result.strategy_effectiveness) >= 0
            assert result.total_return != 0.0
            assert result.best_regime != ""
            assert result.predicted_next_regime != ""
            assert len(result.recommendations) > 0

            # Verify data quality and confidence scores
            assert 0 <= result.data_quality_score <= 1
            assert 0 <= result.analysis_confidence <= 1

    @pytest.mark.asyncio
    async def test_regime_analytics_caching(self, engine, comprehensive_regime_data, comprehensive_performance_data):
        """Test caching functionality in regime analytics"""
        with patch.object(engine, '_collect_regime_data', return_value=comprehensive_regime_data), \
             patch.object(engine, '_collect_performance_data', return_value=comprehensive_performance_data):

            time_period = (datetime(2024, 1, 1), datetime(2024, 1, 2))

            # First analysis
            result1 = await engine.analyze_regime_performance(time_period)

            # Second analysis (should use cache if within TTL)
            result2 = await engine.analyze_regime_performance(time_period)

            # Results should be identical (from cache)
            assert result1.total_return == result2.total_return
            assert result1.best_regime == result2.best_regime
            assert result1.predicted_next_regime == result2.predicted_next_regime

    @pytest.mark.asyncio
    async def test_multiple_regime_analysis_types(self, engine):
        """Test different types of regime analysis"""
        # Test that the engine can handle different analysis types
        # (This would be expanded based on actual implementation)

        time_period = (datetime(2024, 1, 1), datetime(2024, 1, 2))

        # Mock the analysis method
        with patch.object(engine, '_collect_regime_data'), \
             patch.object(engine, '_collect_performance_data'), \
             patch.object(engine, '_calculate_regime_performance', return_value={}), \
             patch.object(engine, '_analyze_regime_transitions', return_value=[]), \
             patch.object(engine, '_analyze_strategy_effectiveness', return_value={}), \
             patch.object(engine, '_predict_next_regime', return_value=('unknown', 0.5, 60)), \
             patch.object(engine, '_generate_recommendations', return_value=[]), \
             patch.object(engine, '_calculate_data_quality', return_value=0.8):

            result = await engine.analyze_regime_performance(time_period)

            assert isinstance(result, RegimeAnalyticsResult)
            assert result.analysis_type == RegimeAnalyticsType.PERFORMANCE_ATTRIBUTION
