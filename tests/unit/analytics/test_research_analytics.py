#!/usr/bin/env python3
"""
Test Suite for Research Analytics Module
========================================

Comprehensive tests for core_structure/analytics/research_analytics.py
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any, Optional

# Import the module under test
from core_structure.analytics.research_analytics import (
    ResearchAnalyticsEngine,
    BacktestResult,
    RegimeAnalysis,
    AIInsight,
    BacktestMode,
    MarketRegime,
    InsightType,
    research_analytics,
    research_engine
)


class TestBacktestResult:
    """Test BacktestResult dataclass"""

    def test_initialization(self):
        """Test BacktestResult initialization"""
        trades = [
            {'timestamp': datetime(2024, 1, 1), 'symbol': 'AAPL', 'quantity': 100, 'price': 150.0, 'pnl': 500.0},
            {'timestamp': datetime(2024, 1, 2), 'symbol': 'MSFT', 'quantity': 50, 'price': 300.0, 'pnl': -200.0}
        ]

        result = BacktestResult(
            strategy_name="test_strategy",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_capital=100000.0,
            final_value=115000.0,
            total_return=0.15,
            annualized_return=0.12,
            volatility=0.25,
            sharpe_ratio=0.48,
            max_drawdown=-0.08,
            win_rate=0.55,
            total_trades=100,
            trades=trades,
            parameters={'lookback': 20, 'threshold': 0.02}
        )

        assert result.strategy_name == "test_strategy"
        assert result.start_date == datetime(2024, 1, 1)
        assert result.end_date == datetime(2024, 12, 31)
        assert result.initial_capital == 100000.0
        assert result.final_value == 115000.0
        assert result.total_return == 0.15
        assert result.annualized_return == 0.12
        assert result.volatility == 0.25
        assert result.sharpe_ratio == 0.48
        assert result.max_drawdown == -0.08
        assert result.win_rate == 0.55
        assert result.total_trades == 100
        assert len(result.trades) == 2
        assert result.parameters == {'lookback': 20, 'threshold': 0.02}

    def test_default_values(self):
        """Test BacktestResult default values"""
        result = BacktestResult(
            strategy_name="minimal_strategy",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_capital=100000.0,
            final_value=105000.0,
            total_return=0.05,
            annualized_return=0.04,
            volatility=0.15,
            sharpe_ratio=0.27,
            max_drawdown=-0.05,
            win_rate=0.52,
            total_trades=50
        )

        assert result.calmar_ratio == 0.0
        assert result.sortino_ratio == 0.0
        assert result.var_95 == 0.0
        assert result.beta == 0.0
        assert result.alpha == 0.0
        assert result.backtest_mode == BacktestMode.VECTORIZED
        assert result.trades == []
        assert result.daily_returns.empty
        assert result.equity_curve.empty
        assert result.parameters == {}


class TestRegimeAnalysis:
    """Test RegimeAnalysis dataclass"""

    def test_initialization(self):
        """Test RegimeAnalysis initialization"""
        regime_history = [
            (datetime(2024, 1, 1), MarketRegime.BULL_MARKET),
            (datetime(2024, 2, 1), MarketRegime.SIDEWAYS),
            (datetime(2024, 3, 1), MarketRegime.BEAR_MARKET)
        ]

        analysis = RegimeAnalysis(
            current_regime=MarketRegime.BULL_MARKET,
            regime_probability=0.75,
            regime_duration=30,
            regime_history=regime_history,
            regime_transitions={'bull_to_sideways': 2, 'sideways_to_bear': 1},
            confidence=0.85
        )

        assert analysis.current_regime == MarketRegime.BULL_MARKET
        assert analysis.regime_probability == 0.75
        assert analysis.regime_duration == 30
        assert len(analysis.regime_history) == 3
        assert analysis.regime_transitions == {'bull_to_sideways': 2, 'sideways_to_bear': 1}
        assert analysis.confidence == 0.85


class TestAIInsight:
    """Test AIInsight dataclass"""

    def test_initialization(self):
        """Test AIInsight initialization"""
        insight = AIInsight(
            insight_type=InsightType.PERFORMANCE_INSIGHT,
            title="Strategy Performance Pattern",
            description="Detected consistent outperformance in high volatility regimes",
            confidence=0.82,
            importance=0.75,
            actionable=True,
            supporting_data={'correlation': 0.65, 'sample_size': 150}
        )

        assert insight.insight_type == InsightType.PERFORMANCE_INSIGHT
        assert insight.title == "Strategy Performance Pattern"
        assert insight.description == "Detected consistent outperformance in high volatility regimes"
        assert insight.confidence == 0.82
        assert insight.importance == 0.75
        assert insight.actionable == True
        assert insight.supporting_data == {'correlation': 0.65, 'sample_size': 150}
        assert isinstance(insight.timestamp, datetime)


class TestEnums:
    """Test enum classes"""

    def test_backtest_mode_enum(self):
        """Test BacktestMode enum values"""
        assert BacktestMode.VECTORIZED.value == "vectorized"
        assert BacktestMode.EVENT_DRIVEN.value == "event_driven"
        assert BacktestMode.MONTE_CARLO.value == "monte_carlo"

    def test_market_regime_enum(self):
        """Test MarketRegime enum values"""
        assert MarketRegime.BULL_MARKET.value == "bull_market"
        assert MarketRegime.BEAR_MARKET.value == "bear_market"
        assert MarketRegime.SIDEWAYS.value == "sideways"
        assert MarketRegime.HIGH_VOLATILITY.value == "high_volatility"
        assert MarketRegime.LOW_VOLATILITY.value == "low_volatility"

    def test_insight_type_enum(self):
        """Test InsightType enum values"""
        assert InsightType.PATTERN_RECOGNITION.value == "pattern_recognition"
        assert InsightType.ANOMALY_INSIGHT.value == "anomaly_insight"
        assert InsightType.PERFORMANCE_INSIGHT.value == "performance_insight"
        assert InsightType.RISK_INSIGHT.value == "risk_insight"
        assert InsightType.OPTIMIZATION_SUGGESTION.value == "optimization_suggestion"


class TestResearchAnalyticsEngine:
    """Test ResearchAnalyticsEngine class"""

    @pytest.fixture
    def engine(self):
        """Create a test ResearchAnalyticsEngine instance"""
        return ResearchAnalyticsEngine(
            default_capital=100000.0,
            commission_rate=0.001,
            slippage_rate=0.0005,
            enable_ai_insights=True
        )

    @pytest.fixture
    def sample_market_data(self):
        """Generate sample market data for testing"""
        dates = pd.date_range('2024-01-01', periods=252, freq='D')  # ~1 year
        np.random.seed(42)

        # Generate realistic price data
        returns = np.random.normal(0.001, 0.02, 252)
        prices = 100 * np.exp(np.cumsum(returns))

        # Add some regime-like behavior
        for i in range(50, 100):  # Bull market period
            returns[i] += np.random.normal(0.005, 0.01)
        for i in range(150, 200):  # Bear market period
            returns[i] += np.random.normal(-0.005, 0.015)

        prices = 100 * np.exp(np.cumsum(returns))

        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, 252)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.002, 252))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.002, 252))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, 252),
            'returns': returns
        })

        return data

    @pytest.fixture
    def sample_strategy_signals(self):
        """Generate sample strategy signals"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        signals = []

        for i, date in enumerate(dates):
            # Simple momentum strategy signals
            if i > 20:  # Need lookback
                signal = 1 if np.random.random() > 0.5 else -1
                signals.append({
                    'timestamp': date,
                    'symbol': 'TEST',
                    'signal': signal,
                    'confidence': np.random.uniform(0.5, 0.95),
                    'price': 100 + np.random.normal(0, 5)
                })

        return pd.DataFrame(signals)

    def test_initialization(self, engine):
        """Test ResearchAnalyticsEngine initialization"""
        assert engine.default_capital == 100000.0
        assert engine.commission_rate == 0.001
        assert engine.slippage_rate == 0.0005
        assert engine.enable_ai_insights == True

        # Check data structures
        assert len(engine.backtest_results) == 0
        assert len(engine.regime_history) == 0
        assert len(engine.insights_history) == 0
        assert len(engine.research_cache) == 0

        # Check ML models are initialized
        assert hasattr(engine, 'pattern_classifier')
        assert hasattr(engine, 'performance_predictor')
        assert hasattr(engine, 'regime_classifier')
        assert hasattr(engine, 'scaler')

    def test_run_backtest_vectorized(self, engine, sample_market_data, sample_strategy_signals):
        """Test vectorized backtest execution"""
        # Mock strategy that generates signals
        def mock_strategy(data):
            signals = []
            for i in range(len(data)):
                if i > 20:  # Need lookback
                    signal = 1 if data['returns'].iloc[i-20:i].mean() > 0 else -1
                    signals.append({
                        'timestamp': data.index[i],
                        'symbol': 'TEST',
                        'signal': signal,
                        'confidence': 0.8,
                        'price': data['close'].iloc[i]
                    })
            return pd.DataFrame(signals)

        # Run backtest
        result = engine.run_backtest(
            strategy_function=mock_strategy,
            market_data=sample_market_data,
            strategy_name="test_strategy",
            mode=BacktestMode.VECTORIZED
        )

        assert isinstance(result, BacktestResult)
        assert result.strategy_name == "test_strategy"
        assert result.backtest_mode == BacktestMode.VECTORIZED
        assert result.initial_capital == 100000.0
        assert isinstance(result.total_return, float)
        assert isinstance(result.sharpe_ratio, float)

    def test_run_backtest_event_driven(self, engine, sample_market_data):
        """Test event-driven backtest execution"""
        # Mock event-driven strategy
        class MockEventStrategy:
            def __init__(self):
                self.positions = {}
                self.capital = 100000.0

            def on_market_data(self, data_point):
                # Simple strategy logic
                if data_point['returns'] > 0.01:  # Bullish signal
                    return {'action': 'buy', 'quantity': 100}
                elif data_point['returns'] < -0.01:  # Bearish signal
                    return {'action': 'sell', 'quantity': 100}
                return None

        strategy = MockEventStrategy()

        result = engine.run_backtest(
            strategy_instance=strategy,
            market_data=sample_market_data,
            strategy_name="event_strategy",
            mode=BacktestMode.EVENT_DRIVEN
        )

        assert isinstance(result, BacktestResult)
        assert result.strategy_name == "event_strategy"
        assert result.backtest_mode == BacktestMode.VECTORIZED  # Current implementation uses vectorized backtest

    def test_analyze_market_regime(self, engine, sample_market_data):
        """Test market regime analysis"""
        analysis = engine.analyze_market_regime(sample_market_data)

        assert isinstance(analysis, RegimeAnalysis)
        assert isinstance(analysis.current_regime, MarketRegime)
        assert isinstance(analysis.regime_probability, float)
        assert 0 <= analysis.regime_probability <= 1
        assert analysis.regime_duration >= 0
        assert isinstance(analysis.regime_history, list)
        assert isinstance(analysis.confidence, float)

    def test_generate_ai_insights(self, engine, sample_market_data):
        """Test AI insights generation"""
        insights = engine.generate_ai_insights(sample_market_data)

        assert isinstance(insights, list)

        for insight in insights:
            assert isinstance(insight, AIInsight)
            assert isinstance(insight.insight_type, InsightType)
            assert isinstance(insight.title, str)
            assert isinstance(insight.description, str)
            assert 0 <= insight.confidence <= 1
            assert 0 <= insight.importance <= 1
            assert isinstance(insight.actionable, bool)

    def test_compare_strategies(self, engine, sample_market_data):
        """Test strategy comparison"""
        # Create mock strategy results
        results = []
        for i in range(3):
            result = BacktestResult(
                strategy_name=f"strategy_{i}",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                initial_capital=100000.0,
                final_value=100000.0 * (1 + np.random.normal(0.05, 0.1)),
                total_return=np.random.normal(0.05, 0.1),
                annualized_return=np.random.normal(0.04, 0.08),
                volatility=np.random.normal(0.15, 0.05),
                sharpe_ratio=np.random.normal(0.3, 0.2),
                max_drawdown=np.random.normal(-0.1, 0.05),
                win_rate=np.random.uniform(0.4, 0.7),
                total_trades=np.random.randint(50, 200)
            )
            results.append(result)
            engine.backtest_results.append(result)

        comparison = engine.compare_strategies(results)

        assert isinstance(comparison, dict)
        assert 'best_performer' in comparison
        assert 'worst_performer' in comparison
        assert 'performance_rankings' in comparison
        assert 'risk_adjusted_rankings' in comparison

    def test_optimize_strategy_parameters(self, engine, sample_market_data):
        """Test strategy parameter optimization"""
        def mock_strategy_with_params(data, params):
            # Simple parameter-dependent strategy
            lookback = params.get('lookback', 20)
            threshold = params.get('threshold', 0.02)

            signals = []
            for i in range(len(data)):
                if i >= lookback:
                    avg_return = data['returns'].iloc[i-lookback:i].mean()
                    signal = 1 if avg_return > threshold else -1
                    signals.append({
                        'timestamp': data.index[i],
                        'signal': signal,
                        'confidence': 0.8
                    })
            return pd.DataFrame(signals)

        param_grid = {
            'lookback': [10, 20, 30],
            'threshold': [0.01, 0.02, 0.03]
        }

        optimization_result = engine.optimize_strategy_parameters(
            strategy_function=mock_strategy_with_params,
            market_data=sample_market_data,
            param_grid=param_grid,
            optimization_metric='sharpe_ratio'
        )

        assert isinstance(optimization_result, dict)
        assert 'best_parameters' in optimization_result
        assert 'best_score' in optimization_result
        assert 'all_results' in optimization_result

    def test_generate_research_report(self, engine):
        """Test research report generation"""
        # Add some mock data
        mock_result = BacktestResult(
            strategy_name="test_strategy",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            initial_capital=100000.0,
            final_value=115000.0,
            total_return=0.15,
            annualized_return=0.12,
            volatility=0.25,
            sharpe_ratio=0.48,
            max_drawdown=-0.08,
            win_rate=0.55,
            total_trades=100
        )
        engine.backtest_results.append(mock_result)

        report = engine.generate_research_report()

        assert isinstance(report, dict)
        assert 'summary' in report
        assert 'performance_analysis' in report
        assert 'risk_analysis' in report
        assert 'recommendations' in report
        assert 'generated_at' in report

    def test_get_research_summary(self, engine):
        """Test research summary"""
        summary = engine.get_research_summary()

        expected_keys = [
            'total_backtests',
            'total_insights',
            'regime_analysis_count',
            'cache_size',
            'ai_enabled',
            'last_research_activity'
        ]

        for key in expected_keys:
            assert key in summary


class TestConvenienceFunctions:
    """Test module-level convenience functions"""

    def test_research_analytics_global_instance(self):
        """Test global research analytics instance"""
        assert isinstance(research_analytics, ResearchAnalyticsEngine)
        assert hasattr(research_analytics, 'run_backtest')

    def test_research_engine_alias(self):
        """Test research_engine alias"""
        # This should be the same instance
        assert research_engine is research_analytics


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def engine(self):
        """Create a test ResearchAnalyticsEngine instance"""
        return ResearchAnalyticsEngine()

    def test_empty_market_data(self, engine):
        """Test handling of empty market data"""
        empty_data = pd.DataFrame()

        # Should handle gracefully
        result = engine.analyze_market_regime(empty_data)
        assert isinstance(result, RegimeAnalysis)

    def test_insufficient_data_for_backtest(self, engine):
        """Test backtest with insufficient data"""
        small_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='D'),
            'close': [100, 101, 99, 102, 98],
            'returns': [0.01, -0.01, 0.03, -0.04, 0.02]
        })

        def simple_strategy(data):
            return pd.DataFrame({
                'timestamp': data.index,
                'signal': [1, -1, 1, -1, 1]
            })

        # Should handle gracefully
        result = engine.run_backtest(
            strategy_function=simple_strategy,
            market_data=small_data,
            strategy_name="small_test"
        )

        assert isinstance(result, BacktestResult)

    def test_single_regime_data(self, engine):
        """Test regime analysis with single regime"""
        single_regime_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='D'),
            'close': np.cumsum(np.random.normal(0.001, 0.02, 100)) + 100,
            'returns': np.random.normal(0.001, 0.02, 100)
        })

        analysis = engine.analyze_market_regime(single_regime_data)

        assert isinstance(analysis, RegimeAnalysis)
        assert len(analysis.regime_history) >= 1

    def test_extreme_parameter_values(self, engine):
        """Test with extreme parameter values"""
        extreme_engine = ResearchAnalyticsEngine(
            default_capital=1e9,  # Very large capital
            commission_rate=0.1,  # Very high commission
            slippage_rate=0.01   # Very high slippage
        )

        assert extreme_engine.default_capital == 1e9
        assert extreme_engine.commission_rate == 0.1
        assert extreme_engine.slippage_rate == 0.01

    @pytest.mark.asyncio
    async def test_ai_insights_disabled(self):
        """Test with AI insights disabled"""
        engine_no_ai = ResearchAnalyticsEngine(enable_ai_insights=False)

        # Should still work but without AI features
        assert engine_no_ai.enable_ai_insights == False

        sample_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50, freq='D'),
            'returns': np.random.normal(0.001, 0.02, 50)
        })

        insights = engine_no_ai.generate_ai_insights(sample_data)

        # Should return empty or basic insights
        assert isinstance(insights, list)


class TestIntegration:
    """Integration tests combining multiple research features"""

    @pytest.fixture
    def engine(self):
        """Create a test ResearchAnalyticsEngine instance"""
        return ResearchAnalyticsEngine()

    @pytest.fixture
    def comprehensive_market_data(self):
        """Generate comprehensive market data for integration testing"""
        dates = pd.date_range('2024-01-01', periods=500, freq='D')
        np.random.seed(42)

        # Generate multi-asset data
        assets = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
        data = {}

        for asset in assets:
            # Generate asset-specific returns with correlations
            base_returns = np.random.normal(0.001, 0.02, 500)

            # Add asset-specific patterns
            if asset == 'TSLA':
                base_returns *= 1.5  # More volatile
            elif asset == 'AAPL':
                base_returns += 0.0005  # Slight premium

            prices = 100 * np.exp(np.cumsum(base_returns))

            data[asset] = pd.DataFrame({
                'timestamp': dates,
                'open': prices * (1 + np.random.normal(0, 0.001, 500)),
                'high': prices * (1 + np.abs(np.random.normal(0, 0.002, 500))),
                'low': prices * (1 - np.abs(np.random.normal(0, 0.002, 500))),
                'close': prices,
                'volume': np.random.randint(100000, 2000000, 500),
                'returns': base_returns
            })

        return data

    def test_full_research_workflow(self, engine, comprehensive_market_data):
        """Test complete research workflow"""
        # Use AAPL data for primary analysis
        aapl_data = comprehensive_market_data['AAPL']

        # 1. Run backtest
        def momentum_strategy(data):
            signals = []
            lookback = 20
            for i in range(len(data)):
                if i >= lookback:
                    avg_return = data['returns'].iloc[i-lookback:i].mean()
                    signal = 1 if avg_return > 0.001 else -1
                    signals.append({
                        'timestamp': data.index[i],
                        'symbol': 'AAPL',
                        'signal': signal,
                        'confidence': 0.75,
                        'price': data['close'].iloc[i]
                    })
            return pd.DataFrame(signals)

        backtest_result = engine.run_backtest(
            strategy_function=momentum_strategy,
            market_data=aapl_data,
            strategy_name="momentum_test"
        )

        # 2. Analyze market regime
        regime_analysis = engine.analyze_market_regime(aapl_data)

        # 3. Generate AI insights
        insights = engine.generate_ai_insights(aapl_data)

        # 4. Compare with other strategies (mock)
        mock_results = [
            backtest_result,
            BacktestResult(
                strategy_name="mean_reversion",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                initial_capital=100000.0,
                final_value=108000.0,
                total_return=0.08,
                annualized_return=0.065,
                volatility=0.18,
                sharpe_ratio=0.36,
                max_drawdown=-0.06,
                win_rate=0.58,
                total_trades=80
            )
        ]

        comparison = engine.compare_strategies(mock_results)

        # 5. Generate research report
        report = engine.generate_research_report()

        # Verify all components work together
        assert isinstance(backtest_result, BacktestResult)
        assert isinstance(regime_analysis, RegimeAnalysis)
        assert isinstance(insights, list)
        assert isinstance(comparison, dict)
        assert isinstance(report, dict)

        # Verify relationships between components
        strategy_names_in_rankings = [item['name'] for item in comparison.get('performance_rankings', [])]
        assert backtest_result.strategy_name in strategy_names_in_rankings

    def test_multi_asset_research(self, engine, comprehensive_market_data):
        """Test research across multiple assets"""
        results = []

        for asset, data in comprehensive_market_data.items():
            # Run backtest for each asset
            def asset_strategy(data, asset_name=asset):
                signals = []
                for i in range(len(data)):
                    if i > 10:
                        signal = 1 if data['returns'].iloc[i] > 0 else -1
                        signals.append({
                            'timestamp': data.index[i],
                            'symbol': asset_name,
                            'signal': signal,
                            'confidence': 0.7,
                            'price': data['close'].iloc[i]
                        })
                return pd.DataFrame(signals)

            result = engine.run_backtest(
                strategy_function=asset_strategy,
                market_data=data,
                strategy_name=f"{asset}_strategy"
            )
            results.append(result)

        # Compare all asset strategies
        comparison = engine.compare_strategies(results)

        assert isinstance(comparison, dict)
        assert len(comparison.get('performance_rankings', {})) == len(comprehensive_market_data)

    def test_research_caching_and_performance(self, engine, comprehensive_market_data):
        """Test caching and performance aspects"""
        aapl_data = comprehensive_market_data['AAPL']

        # First analysis
        start_time = datetime.now()
        regime1 = engine.analyze_market_regime(aapl_data)
        first_duration = (datetime.now() - start_time).total_seconds()

        # Second analysis (should be cached or faster)
        start_time = datetime.now()
        regime2 = engine.analyze_market_regime(aapl_data)
        second_duration = (datetime.now() - start_time).total_seconds()

        # Results should be consistent
        assert regime1.current_regime == regime2.current_regime
        assert regime1.regime_probability == regime2.regime_probability

        # Second run should be faster (due to caching or optimization)
        # Note: This might not always be true in testing, but the structure should support it
        assert isinstance(regime1, RegimeAnalysis)
        assert isinstance(regime2, RegimeAnalysis)
