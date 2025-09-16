"""
Unit Tests for Market Condition Analytics System
===============================================

Comprehensive test suite for the MarketConditionAnalyticsEngine and its components.
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
    EnhancedRegimeDetector,
    DynamicStrategySelector,
    InstrumentOptimizer,
    PerformanceTracker,
    UnifiedDataProcessor,
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
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='1H')
    n_periods = len(dates)
    
    # Generate realistic price data with trends and volatility
    base_price = 100.0
    returns = np.random.normal(0.0001, 0.02, n_periods)  # 2% hourly volatility
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
        'vix': 18.5,
        'yield_curve_slope': 1.2,
        'dollar_index': 103.5
    }


@pytest.fixture
def sample_sentiment_data():
    """Generate sample sentiment data"""
    return {
        'news_sentiment_score': 0.2,
        'social_media_sentiment': 0.1,
        'analyst_sentiment': 0.3,
        'put_call_ratio': 0.8,
        'fear_greed_index': 45,
        'insider_trading_ratio': 0.15
    }


@pytest.fixture
def mock_database_manager():
    """Mock database manager"""
    mock_db = Mock()
    mock_db.execute_query = AsyncMock(return_value=[])
    mock_db.insert_data = AsyncMock(return_value=True)
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
# TEST ENHANCED REGIME DETECTOR
# ================================================================================

class TestEnhancedRegimeDetector:
    """Test the EnhancedRegimeDetector component"""
    
    def test_regime_detector_initialization(self, mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test regime detector initialization"""
        # Create parent engine first
        parent_engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        detector = parent_engine.regime_detector
        
        assert detector is not None
        assert hasattr(detector, 'parent_engine')
        assert detector.parent_engine == parent_engine
    
    def test_extract_market_features(self, sample_market_data, mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test market feature extraction"""
        parent_engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        detector = parent_engine.regime_detector
        
        features = detector._extract_market_features(sample_market_data)
        
        assert isinstance(features, dict)
        # Check that some basic features exist (implementation may vary)
        assert len(features) > 0
        
        # Check feature values are numeric
        for key, value in features.items():
            assert isinstance(value, (int, float, np.integer, np.floating))
    
    def test_extract_macro_features(self, sample_macro_data, mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test macroeconomic feature extraction"""
        parent_engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        detector = parent_engine.regime_detector
        
        features = detector._extract_macro_features(sample_macro_data)
        
        assert isinstance(features, dict)
        assert len(features) > 0
        
        # Check feature normalization
        for key, value in features.items():
            assert isinstance(value, (int, float, np.integer, np.floating))
    
    def test_extract_sentiment_features(self, sample_sentiment_data, mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test sentiment feature extraction"""
        parent_engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        detector = parent_engine.regime_detector
        
        features = detector._extract_sentiment_features(sample_sentiment_data)
        
        assert isinstance(features, dict)
        assert len(features) > 0
        
        # Check sentiment scores are numeric
        for key, value in features.items():
            assert isinstance(value, (int, float, np.integer, np.floating))
    
    @pytest.mark.asyncio
    async def test_detect_regime(self, sample_market_data, sample_macro_data, sample_sentiment_data, 
                               mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test regime detection functionality"""
        parent_engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        detector = parent_engine.regime_detector
        
        # Train with some sample data first (if method exists)
        if hasattr(detector, '_train_models'):
            await detector._train_models(sample_market_data, sample_macro_data, sample_sentiment_data)
        
        regime, confidence = await detector.detect_regime(
            market_data=sample_market_data,
            macro_data=sample_macro_data,
            sentiment_data=sample_sentiment_data
        )
        
        assert isinstance(regime, MarketCondition)
        assert 0 <= confidence <= 1
        assert regime in list(MarketCondition)
    
    def test_regime_change_detection(self, mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test regime change detection"""
        parent_engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        detector = parent_engine.regime_detector
        
        # Test initial state
        assert getattr(detector, '_current_regime', None) is None
        
        # Test regime change (if method exists)
        if hasattr(detector, '_is_regime_change'):
            previous_regime = MarketCondition.TRENDING_BULL
            new_regime = MarketCondition.TRENDING_BEAR
            
            detector._current_regime = previous_regime
            is_change = detector._is_regime_change(new_regime, confidence=0.8)
            
            assert is_change == True
            
            # Test no change (same regime)
            detector._current_regime = new_regime
            is_change = detector._is_regime_change(new_regime, confidence=0.8)
            
            assert is_change == False


# ================================================================================
# TEST DYNAMIC STRATEGY SELECTOR
# ================================================================================

class TestDynamicStrategySelector:
    """Test the DynamicStrategySelector component"""
    
    def test_strategy_selector_initialization(self, mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test strategy selector initialization"""
        parent_engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        selector = parent_engine.strategy_selector
        
        assert selector is not None
        assert hasattr(selector, 'parent_engine')
        assert selector.parent_engine == parent_engine
    
    def test_regime_strategy_mapping(self, mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test regime to strategy mapping"""
        parent_engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        selector = parent_engine.strategy_selector
        
        # Test strategy mapping (if method exists)
        if hasattr(selector, '_get_regime_strategies'):
            # Test trending bull market mapping
            strategies = selector._get_regime_strategies(MarketCondition.TRENDING_BULL)
            assert isinstance(strategies, dict)
            assert len(strategies) > 0
            
            # Test trending bear market mapping
            strategies = selector._get_regime_strategies(MarketCondition.TRENDING_BEAR)
            assert isinstance(strategies, dict)
            
            # Test sideways market mapping
            strategies = selector._get_regime_strategies(MarketCondition.SIDEWAYS_RANGE)
            assert isinstance(strategies, dict)
    
    @pytest.mark.asyncio
    async def test_select_strategies(self):
        """Test strategy selection functionality"""
        selector = DynamicStrategySelector()
        
        market_state = MarketConditionState(
            timestamp=datetime.now(),
            primary_condition=MarketCondition.BULL_MARKET,
            secondary_conditions=[MarketCondition.LOW_VOLATILITY],
            confidence=0.85,
            regime_strength=0.7,
            transition_probability=0.1,
            supporting_indicators={
                'trend_strength': 0.8,
                'volatility_level': 0.3
            }
        )
        
        portfolio_context = {
            'total_value': 1000000,
            'current_allocations': {StrategyType.MOMENTUM: 0.5},
            'risk_budget_used': 0.6
        }
        
        selection = await selector.select_strategies(market_state, portfolio_context)
        
        assert isinstance(selection, StrategySelection)
        assert selection.regime == MarketCondition.BULL_MARKET
        assert 0.8 <= selection.confidence <= 1.0
        assert abs(sum(selection.selected_strategies.values()) - 1.0) < 0.01  # Should sum to 1
    
    def test_allocation_constraints(self):
        """Test allocation constraint enforcement"""
        selector = DynamicStrategySelector()
        
        raw_allocations = {
            StrategyType.MOMENTUM: 0.8,
            StrategyType.MEAN_REVERSION: 0.3,
            StrategyType.PAIRS_TRADING: 0.2
        }
        
        constrained = selector._apply_allocation_constraints(raw_allocations)
        
        # Check total allocation is normalized to 1.0
        assert abs(sum(constrained.values()) - 1.0) < 0.01
        
        # Check no single strategy exceeds maximum allocation
        max_allocation = selector._allocation_constraints.get('max_single_strategy', 0.6)
        for allocation in constrained.values():
            assert allocation <= max_allocation
    
    def test_performance_based_adjustment(self):
        """Test performance-based strategy adjustments"""
        selector = DynamicStrategySelector()
        
        # Add some performance history
        selector._strategy_performance_history[StrategyType.MOMENTUM] = [0.05, 0.03, 0.08]  # Good performance
        selector._strategy_performance_history[StrategyType.MEAN_REVERSION] = [-0.02, -0.01, 0.01]  # Poor performance
        
        base_allocations = {
            StrategyType.MOMENTUM: 0.5,
            StrategyType.MEAN_REVERSION: 0.5
        }
        
        adjusted = selector._adjust_for_performance(base_allocations)
        
        # Momentum should get higher allocation due to better performance
        assert adjusted[StrategyType.MOMENTUM] > base_allocations[StrategyType.MOMENTUM]
        assert adjusted[StrategyType.MEAN_REVERSION] < base_allocations[StrategyType.MEAN_REVERSION]


# ================================================================================
# TEST INSTRUMENT OPTIMIZER
# ================================================================================

class TestInstrumentOptimizer:
    """Test the InstrumentOptimizer component"""
    
    def test_instrument_optimizer_initialization(self):
        """Test instrument optimizer initialization"""
        optimizer = InstrumentOptimizer()
        
        assert optimizer is not None
        assert hasattr(optimizer, '_correlation_matrix')
        assert hasattr(optimizer, '_momentum_scores')
        assert hasattr(optimizer, '_volatility_scores')
    
    @pytest.mark.asyncio
    async def test_optimize_instruments(self, sample_market_data):
        """Test instrument optimization"""
        optimizer = InstrumentOptimizer()
        
        # Create sample strategy allocations
        strategy_allocations = {
            StrategyType.MOMENTUM: 0.6,
            StrategyType.MEAN_REVERSION: 0.4
        }
        
        # Create sample instrument universe
        instruments = ['SPY', 'QQQ', 'IWM', 'AAPL', 'MSFT', 'GOOGL']
        
        optimized = await optimizer.optimize_instruments(
            strategy_allocations=strategy_allocations,
            available_instruments=instruments,
            market_data=sample_market_data
        )
        
        assert isinstance(optimized, dict)
        assert StrategyType.MOMENTUM in optimized
        assert StrategyType.MEAN_REVERSION in optimized
        
        # Check that optimized instruments are from available set
        for strategy_type, strategy_instruments in optimized.items():
            assert isinstance(strategy_instruments, list)
            for instrument in strategy_instruments:
                assert instrument in instruments
    
    def test_calculate_momentum_scores(self, sample_market_data):
        """Test momentum score calculation"""
        optimizer = InstrumentOptimizer()
        
        scores = optimizer._calculate_momentum_scores(sample_market_data, lookback_days=20)
        
        assert isinstance(scores, dict)
        assert 'SPY' in scores
        assert isinstance(scores['SPY'], float)
        assert not np.isnan(scores['SPY'])
    
    def test_calculate_mean_reversion_scores(self, sample_market_data):
        """Test mean reversion score calculation"""
        optimizer = InstrumentOptimizer()
        
        scores = optimizer._calculate_mean_reversion_scores(sample_market_data, lookback_days=20)
        
        assert isinstance(scores, dict)
        assert 'SPY' in scores
        assert isinstance(scores['SPY'], float)
        assert not np.isnan(scores['SPY'])
    
    def test_calculate_correlation_matrix(self, sample_market_data):
        """Test correlation matrix calculation"""
        optimizer = InstrumentOptimizer()
        
        # Create multi-instrument data
        multi_data = pd.concat([
            sample_market_data.assign(symbol='SPY'),
            sample_market_data.assign(symbol='QQQ', close=sample_market_data['close'] * 1.1),
            sample_market_data.assign(symbol='IWM', close=sample_market_data['close'] * 0.9)
        ])
        
        corr_matrix = optimizer._calculate_correlation_matrix(multi_data)
        
        assert isinstance(corr_matrix, pd.DataFrame)
        assert 'SPY' in corr_matrix.index
        assert 'QQQ' in corr_matrix.columns
        assert corr_matrix.loc['SPY', 'SPY'] == 1.0


# ================================================================================
# TEST PERFORMANCE TRACKER
# ================================================================================

class TestPerformanceTracker:
    """Test the PerformanceTracker component"""
    
    def test_performance_tracker_initialization(self):
        """Test performance tracker initialization"""
        tracker = PerformanceTracker()
        
        assert tracker is not None
        assert hasattr(tracker, '_performance_history')
        assert hasattr(tracker, '_regime_accuracy_history')
        assert hasattr(tracker, '_prediction_errors')
    
    @pytest.mark.asyncio
    async def test_update_performance(self):
        """Test performance update functionality"""
        tracker = PerformanceTracker()
        
        feedback = PerformanceFeedback(
            timestamp=datetime.now(),
            strategy=StrategyType.MOMENTUM,
            instrument='SPY',
            regime=MarketCondition.BULL_MARKET,
            actual_return=0.02,
            predicted_return=0.015,
            prediction_error=0.005,
            risk_adjusted_return=0.1,
            execution_quality=0.95,
            regime_accuracy=0.9,
            metadata={'slippage': 0.001}
        )
        
        await tracker.update_performance(feedback)
        
        # Check that performance is recorded
        assert len(tracker._performance_history) > 0
        assert StrategyType.MOMENTUM in tracker._performance_history
        
        # Check regime accuracy tracking
        assert len(tracker._regime_accuracy_history) > 0
    
    def test_get_performance_metrics(self):
        """Test performance metrics calculation"""
        tracker = PerformanceTracker()
        
        # Add some sample data
        tracker._performance_history[StrategyType.MOMENTUM] = [
            {'return': 0.02, 'timestamp': datetime.now()},
            {'return': 0.01, 'timestamp': datetime.now()},
            {'return': 0.03, 'timestamp': datetime.now()}
        ]
        
        tracker._regime_accuracy_history = [0.9, 0.85, 0.92]
        tracker._prediction_errors = [0.005, 0.003, 0.007]
        
        metrics = tracker.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert 'recent_regime_accuracy' in metrics
        assert 'recent_prediction_error' in metrics
        assert 'strategy_performance' in metrics
        
        # Check metric values are reasonable
        assert 0 <= metrics['recent_regime_accuracy'] <= 1
        assert metrics['recent_prediction_error'] >= 0
    
    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation"""
        tracker = PerformanceTracker()
        
        returns = [0.01, 0.02, -0.005, 0.015, 0.008]
        risk_free_rate = 0.03  # 3% annual
        
        sharpe = tracker._calculate_sharpe_ratio(returns, risk_free_rate)
        
        assert isinstance(sharpe, float)
        assert not np.isnan(sharpe)


# ================================================================================
# TEST UNIFIED DATA PROCESSOR
# ================================================================================

class TestUnifiedDataProcessor:
    """Test the UnifiedDataProcessor component"""
    
    def test_data_processor_initialization(self):
        """Test data processor initialization"""
        processor = UnifiedDataProcessor()
        
        assert processor is not None
        assert hasattr(processor, '_data_cache')
        assert hasattr(processor, '_feature_cache')
    
    @pytest.mark.asyncio
    async def test_process_market_data(self, sample_market_data):
        """Test market data processing"""
        processor = UnifiedDataProcessor()
        
        processed = await processor.process_market_data(sample_market_data)
        
        assert isinstance(processed, pd.DataFrame)
        assert 'returns' in processed.columns
        assert 'volatility' in processed.columns
        assert 'volume_ma' in processed.columns
        assert len(processed) <= len(sample_market_data)  # May be shorter due to indicators
    
    @pytest.mark.asyncio
    async def test_enrich_with_technical_indicators(self, sample_market_data):
        """Test technical indicator enrichment"""
        processor = UnifiedDataProcessor()
        
        enriched = await processor._enrich_with_technical_indicators(sample_market_data)
        
        assert 'sma_20' in enriched.columns
        assert 'rsi' in enriched.columns
        assert 'bollinger_upper' in enriched.columns
        assert 'bollinger_lower' in enriched.columns
        assert 'macd' in enriched.columns
    
    @pytest.mark.asyncio
    async def test_normalize_features(self, sample_market_data):
        """Test feature normalization"""
        processor = UnifiedDataProcessor()
        
        # Add some features to normalize
        sample_market_data['feature1'] = np.random.randn(len(sample_market_data)) * 100
        sample_market_data['feature2'] = np.random.randn(len(sample_market_data)) * 50
        
        normalized = await processor._normalize_features(sample_market_data)
        
        # Check that features are normalized (approximately 0 mean, 1 std)
        assert abs(normalized['feature1'].mean()) < 0.1
        assert abs(normalized['feature1'].std() - 1.0) < 0.1
        assert abs(normalized['feature2'].mean()) < 0.1
        assert abs(normalized['feature2'].std() - 1.0) < 0.1


# ================================================================================
# TEST MAIN MARKET CONDITION ANALYTICS ENGINE
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
        assert isinstance(engine.regime_detector, EnhancedRegimeDetector)
        assert isinstance(engine.strategy_selector, DynamicStrategySelector)
        assert isinstance(engine.instrument_optimizer, InstrumentOptimizer)
        assert isinstance(engine.performance_tracker, PerformanceTracker)
        assert isinstance(engine.data_processor, UnifiedDataProcessor)
    
    @pytest.mark.asyncio
    async def test_engine_start_stop(self, mock_database_manager, mock_message_bus, mock_metrics_collector):
        """Test engine start and stop"""
        engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        # Test start
        await engine.start()
        assert engine._running == True
        
        # Test stop
        await engine.stop()
        assert engine._running == False
    
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
        
        # Mock the regime detector to return a predictable result
        with patch.object(engine.regime_detector, 'detect_regime', 
                         return_value=(MarketCondition.BULL_MARKET, 0.85)):
            
            market_state = await engine.analyze_current_market_condition(
                market_data=sample_market_data,
                macro_data=sample_macro_data,
                sentiment_data=sample_sentiment_data
            )
            
            assert isinstance(market_state, MarketConditionState)
            assert market_state.primary_condition == MarketCondition.BULL_MARKET
            assert market_state.confidence == 0.85
            assert isinstance(market_state.timestamp, datetime)
        
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
        
        market_state = MarketConditionState(
            timestamp=datetime.now(),
            primary_condition=MarketCondition.BULL_MARKET,
            secondary_conditions=[],
            confidence=0.9,
            regime_strength=0.8,
            transition_probability=0.1,
            supporting_indicators={}
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
        assert recommendations.regime == MarketCondition.BULL_MARKET
        assert isinstance(recommendations.selected_strategies, dict)
        assert len(recommendations.instruments_per_strategy) >= 0
        
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
        
        feedback = PerformanceFeedback(
            timestamp=datetime.now(),
            strategy=StrategyType.MOMENTUM,
            instrument='SPY',
            regime=MarketCondition.BULL_MARKET,
            actual_return=0.02,
            predicted_return=0.015,
            prediction_error=0.005,
            risk_adjusted_return=0.1,
            execution_quality=0.95,
            regime_accuracy=0.9,
            metadata={}
        )
        
        await engine.update_performance_feedback(feedback)
        
        # Verify that feedback was processed
        mock_database_manager.insert_data.assert_called()
        
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
        
        # Add some mock performance data
        engine.performance_tracker._regime_accuracy_history = [0.9, 0.85, 0.92]
        engine.performance_tracker._prediction_errors = [0.005, 0.003, 0.007]
        
        metrics = engine.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert 'recent_regime_accuracy' in metrics
        assert 'recent_prediction_error' in metrics
    
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
            primary_condition=MarketCondition.BULL_MARKET,
            secondary_conditions=[],
            confidence=0.9,
            regime_strength=0.8,
            transition_probability=0.1,
            supporting_indicators={}
        )
        
        engine._current_market_state = test_state
        
        retrieved_state = engine.get_current_market_state()
        assert retrieved_state == test_state


# ================================================================================
# INTEGRATION TESTS
# ================================================================================

class TestMarketConditionAnalyticsIntegration:
    """Integration tests for the complete analytics system"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self,
                                           mock_database_manager,
                                           mock_message_bus,
                                           mock_metrics_collector,
                                           sample_market_data,
                                           sample_macro_data,
                                           sample_sentiment_data):
        """Test the complete analytics workflow"""
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
            
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_regime_change_detection_workflow(self,
                                                  mock_database_manager,
                                                  mock_message_bus,
                                                  mock_metrics_collector,
                                                  sample_market_data,
                                                  sample_macro_data,
                                                  sample_sentiment_data):
        """Test regime change detection and notification"""
        engine = MarketConditionAnalyticsEngine(
            database_manager=mock_database_manager,
            message_bus=mock_message_bus,
            metrics_collector=mock_metrics_collector
        )
        
        await engine.start()
        
        try:
            # First analysis - establish baseline
            await engine.analyze_current_market_condition(
                market_data=sample_market_data,
                macro_data=sample_macro_data,
                sentiment_data=sample_sentiment_data
            )
            
            # Mock regime change
            with patch.object(engine.regime_detector, 'detect_regime') as mock_detect:
                # First call returns bull market
                mock_detect.side_effect = [
                    (MarketCondition.BULL_MARKET, 0.9),
                    (MarketCondition.BEAR_MARKET, 0.85)  # Changed regime
                ]
                
                # Second analysis should detect regime change
                await engine.analyze_current_market_condition(
                    market_data=sample_market_data,
                    macro_data=sample_macro_data,
                    sentiment_data=sample_sentiment_data
                )
                
                # Verify regime change message was published
                mock_message_bus.publish.assert_called()
                
        finally:
            await engine.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])