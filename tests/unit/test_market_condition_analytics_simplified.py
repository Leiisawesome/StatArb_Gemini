"""
Simplified Unit Tests for Market Condition Analytics System
==========================================================

Focused unit tests for the MarketConditionAnalyticsEngine that test
the main functionality without getting into implementation details
of tightly coupled components.
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

# Import the MarketCondition Analytics components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core_structure.analytics.market_condition_analytics import (
    MarketConditionAnalyticsEngine,
    MarketCondition,
    MarketConditionState,
    StrategySelection,
    PerformanceFeedback,
    InstrumentRanking
)

from core_structure.strategies import StrategyType


# ================================================================================
# FIXTURES
# ================================================================================

@pytest.fixture
def sample_market_data():
    """Generate sample OHLCV market data"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    n_periods = len(dates)
    
    # Generate realistic price data
    base_price = 100.0
    returns = np.random.normal(0.0001, 0.02, n_periods)
    prices = base_price * np.exp(np.cumsum(returns))
    
    return pd.DataFrame({
        'timestamp': dates,
        'symbol': 'SPY',
        'open': prices * (1 + np.random.normal(0, 0.001, n_periods)),
        'high': prices * (1 + np.random.uniform(0, 0.01, n_periods)),
        'low': prices * (1 - np.random.uniform(0, 0.01, n_periods)),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, n_periods)
    })


@pytest.fixture
def sample_macro_data():
    """Generate sample macroeconomic data"""
    return {
        'fed_funds_rate': 5.25,
        'cpi_yoy': 3.2,
        'gdp_growth_qoq': 2.1,
        'unemployment': 3.8,
        'vix': 18.5
    }


@pytest.fixture
def sample_sentiment_data():
    """Generate sample sentiment data"""
    return {
        'news_sentiment_score': 0.2,
        'social_media_sentiment': 0.1,
        'analyst_sentiment': 0.3,
        'put_call_ratio': 0.8,
        'fear_greed_index': 45
    }


@pytest.fixture
def mock_database_manager():
    """Mock database manager"""
    mock_db = Mock()
    mock_db.execute_query = AsyncMock(return_value=[])
    mock_db.insert_data = AsyncMock(return_value=True)
    mock_db.execute = AsyncMock(return_value=None)
    mock_db.get_connection = Mock()
    return mock_db


@pytest.fixture
def mock_message_bus():
    """Mock message bus"""
    mock_bus = Mock()
    mock_bus.publish = AsyncMock()
    mock_bus.subscribe = Mock()
    mock_bus.start = AsyncMock()
    mock_bus.stop = AsyncMock()
    return mock_bus


@pytest.fixture
def mock_metrics_collector():
    """Mock metrics collector"""
    mock_metrics = Mock()
    mock_metrics.record_metric = Mock()
    mock_metrics.start = AsyncMock()
    mock_metrics.stop = AsyncMock()
    return mock_metrics


# ================================================================================
# MAIN ENGINE TESTS
# ================================================================================

class TestMarketConditionAnalyticsEngine:
    """Test the main MarketConditionAnalyticsEngine"""
    
    def test_engine_initialization(self, mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test engine initialization"""
        engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        assert engine is not None
        assert engine.database_manager == mock_database_manager
        assert engine.message_bus == mock_message_bus
        assert engine.metrics_collector == mock_metrics_collector
        
        # Check that components are initialized
        assert hasattr(engine, 'regime_detector')
        assert hasattr(engine, 'strategy_selector')
        assert hasattr(engine, 'instrument_optimizer')
        assert hasattr(engine, 'performance_tracker')
        assert hasattr(engine, 'data_processor')
        
        # Check initial state
        assert engine.current_market_state is None
        assert engine.current_strategy_selection is None
    
    @pytest.mark.asyncio
    async def test_engine_start_stop(self, mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test engine start and stop"""
        # Make database_manager.execute async-compatible
        mock_database_manager.execute = AsyncMock(return_value=None)
        
        engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        # Test start
        await engine.start()
        assert hasattr(engine, 'running')
        assert engine.running == True
        
        # Test stop
        await engine.stop()
        assert engine.running == False
    
    @pytest.mark.asyncio
    async def test_analyze_current_market_condition(self, 
                                                   mock_database_manager, 
                                                   mock_message_bus, 
                                                   mock_metrics_collector,
                                                   sample_market_data,
                                                   sample_macro_data,
                                                   sample_sentiment_data):
        """Test current market condition analysis"""
        engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        await engine.start()
        
        try:
            market_state = await engine.analyze_current_market_condition(
                market_data=sample_market_data,
                macro_data=sample_macro_data,
                sentiment_data=sample_sentiment_data
            )
            
            assert isinstance(market_state, MarketConditionState)
            assert isinstance(market_state.primary_condition, MarketCondition)
            assert 0 <= market_state.confidence <= 1
            assert isinstance(market_state.timestamp, datetime)
            assert isinstance(market_state.features, dict)
            
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_get_strategy_recommendations(self,
                                              mock_database_manager,
                                              mock_message_bus,
                                              mock_metrics_collector):
        """Test strategy recommendations"""
        engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        await engine.start()
        
        try:
            market_state = MarketConditionState(
                timestamp=datetime.now(),
                primary_condition=MarketCondition.TRENDING_BULL,
                secondary_conditions=[],
                confidence=0.9,
                volatility_regime="normal",
                trend_strength=0.8,
                market_stress=0.2,
                liquidity_condition="normal",
                regime_duration=timedelta(hours=24),
                transition_probability={MarketCondition.TRENDING_BEAR: 0.1},
                features={},
                metadata={}
            )
            
            portfolio_context = {
                'total_value': 1000000,
                'current_allocations': {},
                'risk_budget_used': 0.5
            }
            
            recommendations = await engine.get_strategy_recommendations(
                market_state=market_state,
                portfolio_context=portfolio_context
            )
            
            assert isinstance(recommendations, StrategySelection)
            assert recommendations.regime == MarketCondition.TRENDING_BULL
            assert isinstance(recommendations.selected_strategies, dict)
            assert 0 <= recommendations.confidence <= 1
            assert isinstance(recommendations.instruments_per_strategy, dict)
            
            # Check that allocations sum to approximately 1
            total_allocation = sum(recommendations.selected_strategies.values())
            assert abs(total_allocation - 1.0) < 0.1  # Allow for some tolerance
            
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_update_performance_feedback(self,
                                             mock_database_manager,
                                             mock_message_bus,
                                             mock_metrics_collector):
        """Test performance feedback update"""
        engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        await engine.start()
        
        try:
            feedback = PerformanceFeedback(
                timestamp=datetime.now(),
                strategy=StrategyType.MOMENTUM,
                instrument='SPY',
                regime=MarketCondition.TRENDING_BULL,
                actual_return=0.02,
                predicted_return=0.015,
                prediction_error=0.005,
                risk_adjusted_return=0.1,
                execution_quality=0.95,
                regime_accuracy=0.9,
                metadata={}
            )
            
            await engine.update_performance_feedback(feedback)
            
            # Verify that feedback was processed (database execute should be called)
            mock_database_manager.execute.assert_called()
            
        finally:
            await engine.stop()
    
    def test_get_performance_metrics(self,
                                   mock_database_manager,
                                   mock_message_bus,
                                   mock_metrics_collector):
        """Test performance metrics retrieval"""
        engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        metrics = engine.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        # Should return some basic metrics even if empty
        assert len(metrics) >= 0
    
    def test_get_current_market_state(self,
                                    mock_database_manager,
                                    mock_message_bus,
                                    mock_metrics_collector):
        """Test current market state retrieval"""
        engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        # Test when no current state exists
        assert engine.get_current_market_state() is None
        
        # Set a current state
        test_state = MarketConditionState(
            timestamp=datetime.now(),
            primary_condition=MarketCondition.TRENDING_BULL,
            secondary_conditions=[],
            confidence=0.9,
            volatility_regime="normal",
            trend_strength=0.8,
            market_stress=0.2,
            liquidity_condition="normal",
            regime_duration=timedelta(hours=24),
            transition_probability={},
            features={},
            metadata={}
        )
        
        engine.current_market_state = test_state
        
        retrieved_state = engine.get_current_market_state()
        assert retrieved_state == test_state
    
    @pytest.mark.asyncio
    async def test_configuration_handling(self,
                                        mock_database_manager,
                                        mock_message_bus,
                                        mock_metrics_collector):
        """Test configuration handling"""
        
        # Test with custom config
        custom_config = {
            'analytics_window': 500,
            'regime_detection': {
                'min_confidence': 0.7,
                'lookback_periods': 252
            },
            'strategy_selection': {
                'max_strategies': 3,
                'min_allocation': 0.05
            }
        }
        
        engine = MarketConditionAnalyticsEngine(
            config=custom_config,
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        assert engine.config == custom_config
        
        # Test with default config
        engine_default = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        assert isinstance(engine_default.config, dict)
        assert len(engine_default.config) > 0


# ================================================================================
# DATA STRUCTURE TESTS
# ================================================================================

class TestDataStructures:
    """Test the data structures and enums"""
    
    def test_market_condition_enum(self):
        """Test MarketCondition enum"""
        assert MarketCondition.TRENDING_BULL.value == "trending_bull"
        assert MarketCondition.TRENDING_BEAR.value == "trending_bear"
        assert MarketCondition.HIGH_VOLATILITY.value == "high_volatility"
        assert MarketCondition.LOW_VOLATILITY.value == "low_volatility"
        assert MarketCondition.SIDEWAYS_RANGE.value == "sideways_range"
        
        # Test enum iteration
        conditions = list(MarketCondition)
        assert len(conditions) > 0
        assert all(isinstance(c, MarketCondition) for c in conditions)
    
    def test_market_condition_state_creation(self):
        """Test MarketConditionState creation"""
        state = MarketConditionState(
            timestamp=datetime.now(),
            primary_condition=MarketCondition.TRENDING_BULL,
            secondary_conditions=[MarketCondition.LOW_VOLATILITY],
            confidence=0.85,
            volatility_regime="low",
            trend_strength=0.7,
            market_stress=0.3,
            liquidity_condition="normal",
            regime_duration=timedelta(hours=6),
            transition_probability={MarketCondition.TRENDING_BEAR: 0.15},
            features={'momentum': 0.6, 'volatility': 0.2},
            metadata={'source': 'test'}
        )
        
        assert isinstance(state.timestamp, datetime)
        assert state.primary_condition == MarketCondition.TRENDING_BULL
        assert state.confidence == 0.85
        assert 'momentum' in state.features
        assert state.metadata['source'] == 'test'
    
    def test_strategy_selection_creation(self):
        """Test StrategySelection creation"""
        selection = StrategySelection(
            timestamp=datetime.now(),
            regime=MarketCondition.TRENDING_BULL,
            selected_strategies={
                StrategyType.MOMENTUM: 0.6,
                StrategyType.MEAN_REVERSION: 0.4
            },
            confidence=0.8,
            expected_performance={
                StrategyType.MOMENTUM: 0.12,
                StrategyType.MEAN_REVERSION: 0.08
            },
            risk_assessment={
                StrategyType.MOMENTUM: 0.15,
                StrategyType.MEAN_REVERSION: 0.10
            },
            instruments_per_strategy={
                StrategyType.MOMENTUM: ['SPY', 'QQQ'],
                StrategyType.MEAN_REVERSION: ['AAPL', 'MSFT']
            },
            reasoning={'regime_strength': 0.7}
        )
        
        assert selection.regime == MarketCondition.TRENDING_BULL
        assert len(selection.selected_strategies) == 2
        assert StrategyType.MOMENTUM in selection.selected_strategies
        assert sum(selection.selected_strategies.values()) == 1.0
    
    def test_performance_feedback_creation(self):
        """Test PerformanceFeedback creation"""
        feedback = PerformanceFeedback(
            timestamp=datetime.now(),
            strategy=StrategyType.MOMENTUM,
            instrument='SPY',
            regime=MarketCondition.TRENDING_BULL,
            actual_return=0.025,
            predicted_return=0.020,
            prediction_error=0.005,
            risk_adjusted_return=0.15,
            execution_quality=0.98,
            regime_accuracy=0.92,
            metadata={'slippage': 0.001}
        )
        
        assert feedback.strategy == StrategyType.MOMENTUM
        assert feedback.instrument == 'SPY'
        assert feedback.actual_return == 0.025
        assert feedback.prediction_error == 0.005
        assert feedback.metadata['slippage'] == 0.001


# ================================================================================
# MOCK INTEGRATION TESTS
# ================================================================================

class TestMockIntegration:
    """Test integration with mocked components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_mock(self,
                                          mock_database_manager,
                                          mock_message_bus,
                                          mock_metrics_collector,
                                          sample_market_data,
                                          sample_macro_data,
                                          sample_sentiment_data):
        """Test end-to-end workflow with mocked components"""
        engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        await engine.start()
        
        try:
            # Step 1: Analyze market condition
            market_state = await engine.analyze_current_market_condition(
                market_data=sample_market_data,
                macro_data=sample_macro_data,
                sentiment_data=sample_sentiment_data
            )
            
            assert isinstance(market_state, MarketConditionState)
            
            # Step 2: Get strategy recommendations
            recommendations = await engine.get_strategy_recommendations(
                market_state=market_state,
                portfolio_context={'total_value': 1000000}
            )
            
            assert isinstance(recommendations, StrategySelection)
            
            # Step 3: Update performance feedback
            feedback = PerformanceFeedback(
                timestamp=datetime.now(),
                strategy=StrategyType.MOMENTUM,
                instrument='SPY',
                regime=market_state.primary_condition,
                actual_return=0.02,
                predicted_return=0.015,
                prediction_error=0.005,
                risk_adjusted_return=0.1,
                execution_quality=0.95,
                regime_accuracy=0.9,
                metadata={}
            )
            
            await engine.update_performance_feedback(feedback)
            
            # Step 4: Get performance metrics
            metrics = engine.get_performance_metrics()
            assert isinstance(metrics, dict)
            
            # Verify mock interactions
            assert mock_database_manager.execute.called
            
        finally:
            await engine.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])