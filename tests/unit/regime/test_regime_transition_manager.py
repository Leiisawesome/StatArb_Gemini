"""
Comprehensive Test Suite for Regime Transition Manager

Tests the complete regime transition management functionality including:
- Transition prediction models
- Rebalancing recommendations
- Transition monitoring
- Risk adjustments during transitions
- Portfolio rebalancing triggers
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Import regime transition components
from core_engine.regime.regime_transition_manager import (
    RegimeTransitionManager,
    TransitionPredictor,
    RebalancingManager,
    TransitionMonitor,
    TransitionPrediction,
    RebalancingRecommendation,
    TransitionMonitoring,
    TransitionPhase,
    TransitionType,
    RebalancingTrigger,
    SignalStrength
)

# Import regime types and indicators
from core_engine.regime.regime_detector import RegimeType
from core_engine.regime.regime_indicators import RegimeIndicator, IndicatorType
from core_engine.config.component_config import RegimeConfig


class TestTransitionPrediction:
    """Test transition prediction functionality"""
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing"""
        return RegimeConfig(
            prediction_horizon_days=[1, 3, 7, 14, 30],
            min_training_samples=50,
            volatility_percentile_threshold=0.75,
            momentum_threshold=0.1
        )
    
    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical market data"""
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        np.random.seed(42)
        
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(200) * 0.02),
            'volume': np.random.randint(1000, 10000, 200),
            'high': 100 + np.cumsum(np.random.randn(200) * 0.02) + np.random.uniform(0, 2, 200),
            'low': 100 + np.cumsum(np.random.randn(200) * 0.02) - np.random.uniform(0, 2, 200)
        }, index=dates)
        
        return data
    
    @pytest.fixture
    def sample_regime_history(self):
        """Sample regime history"""
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        regimes = [RegimeType.BULL_MARKET] * 50 + [RegimeType.BEAR_MARKET] * 30 + [RegimeType.SIDEWAYS] * 120
        return pd.Series(regimes, index=dates)
    
    @pytest.fixture
    def sample_indicators_history(self):
        """Sample indicators history"""
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        indicators = []
        
        for i, date in enumerate(dates):
            indicator = RegimeIndicator(
                name=f"test_indicator_{i}",
                current_value=np.random.randn(),
                signal_strength=SignalStrength.MODERATE,
                indicator_type=IndicatorType.VOLATILITY_REGIME,
                calculation_timestamp=date
            )
            indicators.append({'volatility': indicator, 'momentum': indicator})
        
        return indicators
    
    def test_transition_predictor_initialization(self, sample_config):
        """Test transition predictor initialization"""
        predictor = TransitionPredictor(sample_config)
        
        assert predictor.config == sample_config
        assert not predictor.is_trained
        assert predictor.models == {}
        assert predictor.scalers == {}
        assert predictor.feature_names == []
    
    def test_train_prediction_models_success(self, sample_config, sample_historical_data, 
                                           sample_regime_history, sample_indicators_history):
        """Test successful model training"""
        predictor = TransitionPredictor(sample_config)
        
        # Mock the internal methods to avoid complex ML training
        with patch.object(predictor, '_prepare_training_data') as mock_prepare, \
             patch.object(predictor, '_create_transition_labels') as mock_labels, \
             patch.object(predictor, '_train_horizon_models') as mock_train:
            
            # Setup mocks
            mock_prepare.return_value = (pd.DataFrame(np.random.randn(100, 10)), 
                                       pd.Series(np.random.randint(0, 2, 100)))
            mock_labels.return_value = pd.Series(np.random.randint(0, 2, 100))
            mock_train.return_value = {'random_forest': {'accuracy': 0.85}}
            
            # Test training
            result = predictor.train_prediction_models(
                sample_historical_data, sample_regime_history, sample_indicators_history
            )
            
            assert predictor.is_trained
            assert isinstance(result, dict)
            assert len(result) > 0
    
    def test_train_prediction_models_insufficient_data(self, sample_config, sample_historical_data):
        """Test training with insufficient data"""
        predictor = TransitionPredictor(sample_config)
        
        with patch.object(predictor, '_prepare_training_data') as mock_prepare:
            mock_prepare.return_value = (pd.DataFrame(), pd.Series())
            
            result = predictor.train_prediction_models(
                sample_historical_data, pd.Series(), []
            )
            
            assert not predictor.is_trained
            assert result == {}
    
    def test_predict_transition_not_trained(self, sample_config):
        """Test prediction when models not trained"""
        predictor = TransitionPredictor(sample_config)
        
        result = predictor.predict_transition(
            pd.DataFrame(), {}, RegimeType.BULL_MARKET
        )
        
        assert isinstance(result, TransitionPrediction)
        assert result.current_regime == RegimeType.BULL_MARKET
        assert result.predicted_regime == RegimeType.UNKNOWN
    
    def test_predict_transition_success(self, sample_config):
        """Test successful transition prediction"""
        predictor = TransitionPredictor(sample_config)
        predictor.is_trained = True
        
        # Mock internal methods
        with patch.object(predictor, '_extract_prediction_features') as mock_extract, \
             patch.object(predictor, '_get_horizon_prediction') as mock_pred, \
             patch.object(predictor, '_combine_predictions') as mock_combine, \
             patch.object(predictor, '_estimate_transition_timing') as mock_timing, \
             patch.object(predictor, '_assess_transition_characteristics') as mock_characteristics, \
             patch.object(predictor, '_calculate_risk_implications') as mock_risk:
            
            # Setup mocks
            mock_extract.return_value = pd.DataFrame(np.random.randn(1, 10))
            mock_pred.return_value = (RegimeType.BEAR_MARKET, 0.8)
            mock_combine.return_value = {
                'regime': RegimeType.BEAR_MARKET,
                'probability': 0.75,
                'confidence': 0.8,
                'model': 'random_forest'
            }
            mock_timing.return_value = TransitionPrediction()
            mock_characteristics.return_value = TransitionPrediction()
            mock_risk.return_value = TransitionPrediction()
            
            result = predictor.predict_transition(
                pd.DataFrame(), {}, RegimeType.BULL_MARKET
            )
            
            assert isinstance(result, TransitionPrediction)
            assert result.current_regime == RegimeType.BULL_MARKET


class TestRebalancingManager:
    """Test rebalancing management functionality"""
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing"""
        return RegimeConfig(
            volatility_percentile_threshold=0.75,
            momentum_threshold=0.1,
            min_training_samples=50
        )
    
    def test_rebalancing_manager_initialization(self, sample_config):
        """Test rebalancing manager initialization"""
        manager = RebalancingManager(sample_config)
        
        assert manager.config == sample_config
        assert manager.active_recommendations == []
        assert manager.rebalancing_history == []
    
    def test_generate_rebalancing_recommendation(self, sample_config):
        """Test rebalancing recommendation generation"""
        manager = RebalancingManager(sample_config)
        
        # Mock transition prediction with low risk to avoid RISK_THRESHOLD_EXCEEDED trigger
        transition_pred = TransitionPrediction(
            current_regime=RegimeType.BULL_MARKET,
            predicted_regime=RegimeType.BEAR_MARKET,
            transition_probability=0.9,  # > 0.8 to get VERY_STRONG urgency
            prediction_confidence=0.85,
            risk_increase_factor=0.5  # Low risk to avoid risk threshold trigger
        )
        
        # Mock portfolio state
        portfolio_state = {
            'AAPL': 0.3,
            'TSLA': 0.2,
            'CASH': 0.5
        }
        
        with patch.object(manager, '_calculate_optimal_weights') as mock_weights, \
             patch.object(manager, '_calculate_transaction_costs') as mock_costs:
            
            # Setup mocks
            mock_weights.return_value = {'AAPL': 0.2, 'TSLA': 0.1, 'CASH': 0.7}
            mock_costs.return_value = 100.0
            
            result = manager.generate_rebalancing_recommendation(
                transition_pred, portfolio_state
            )
            
            assert isinstance(result, RebalancingRecommendation)
            assert result.trigger == RebalancingTrigger.REGIME_CHANGE_CONFIRMED
            assert result.urgency == SignalStrength.VERY_STRONG
    
    def test_validate_rebalancing_recommendation(self, sample_config):
        """Test rebalancing recommendation validation"""
        manager = RebalancingManager(sample_config)
        
        recommendation = RebalancingRecommendation(
            trigger=RebalancingTrigger.REGIME_CHANGE_CONFIRMED,
            urgency=SignalStrength.STRONG,
            recommended_adjustments={'AAPL': -0.1, 'CASH': 0.1},
            recommendation_confidence=0.8
        )
        
        portfolio_state = {'AAPL': 0.3, 'CASH': 0.7}
        
        with patch.object(manager, '_check_position_limits') as mock_limits, \
             patch.object(manager, '_check_risk_limits') as mock_risk:
            
            mock_limits.return_value = True
            mock_risk.return_value = True
            
            result = manager.validate_rebalancing_recommendation(recommendation, portfolio_state)
            
            assert result is True
    
    def test_implement_rebalancing_recommendation(self, sample_config):
        """Test rebalancing recommendation implementation"""
        manager = RebalancingManager(sample_config)
        
        recommendation = RebalancingRecommendation(
            trigger=RebalancingTrigger.REGIME_CHANGE_CONFIRMED,
            urgency=SignalStrength.STRONG,
            recommended_adjustments={'AAPL': -0.1, 'CASH': 0.1},
            implementation_horizon=1
        )
        
        with patch.object(manager, '_execute_rebalancing') as mock_execute:
            mock_execute.return_value = {'success': True, 'cost': 50.0}
            
            result = manager.implement_rebalancing_recommendation(recommendation)
            
            assert result['success'] is True
            assert 'cost' in result


class TestTransitionMonitor:
    """Test transition monitoring functionality"""
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing"""
        return RegimeConfig(
            prediction_horizon_days=[1, 3, 7],
            min_training_samples=50,
            volatility_percentile_threshold=0.75
        )
    
    def test_transition_monitor_initialization(self, sample_config):
        """Test transition monitor initialization"""
        monitor = TransitionMonitor(sample_config)
        
        assert monitor.config == sample_config
        assert monitor.active_transitions == {}
        assert monitor.monitoring_history == []
    
    def test_start_transition_monitoring(self, sample_config):
        """Test starting transition monitoring"""
        monitor = TransitionMonitor(sample_config)
        
        transition_id = "test_transition_1"
        transition_pred = TransitionPrediction(
            current_regime=RegimeType.BULL_MARKET,
            predicted_regime=RegimeType.BEAR_MARKET,
            transition_probability=0.8
        )
        
        result = monitor.start_transition_monitoring(transition_id, transition_pred)
        
        assert isinstance(result, TransitionMonitoring)
        assert transition_id in monitor.active_transitions
        assert isinstance(monitor.active_transitions[transition_id], TransitionMonitoring)
    
    def test_update_transition_monitoring(self, sample_config):
        """Test updating transition monitoring"""
        monitor = TransitionMonitor(sample_config)
        
        # Start monitoring
        transition_id = "test_transition_1"
        transition_pred = TransitionPrediction(
            current_regime=RegimeType.BULL_MARKET,
            predicted_regime=RegimeType.BEAR_MARKET
        )
        monitor.start_transition_monitoring(transition_id, transition_pred)
        
        # Update monitoring
        current_regime = RegimeType.BEAR_MARKET
        portfolio_performance = 0.05
        risk_metrics = {'volatility': 0.2, 'var_95': 0.03}
        
        result = monitor.update_transition_monitoring(
            transition_id, current_regime, portfolio_performance, risk_metrics
        )
        
        assert result is True
        monitoring = monitor.active_transitions[transition_id]
        assert monitoring.portfolio_performance == portfolio_performance
        assert monitoring.realized_volatility == risk_metrics['volatility']
    
    def test_complete_transition_monitoring(self, sample_config):
        """Test completing transition monitoring"""
        monitor = TransitionMonitor(sample_config)
        
        # Start and update monitoring
        transition_id = "test_transition_1"
        transition_pred = TransitionPrediction(
            current_regime=RegimeType.BULL_MARKET,
            predicted_regime=RegimeType.BEAR_MARKET
        )
        monitor.start_transition_monitoring(transition_id, transition_pred)
        monitor.update_transition_monitoring(transition_id, RegimeType.BEAR_MARKET, 0.05, {})
        
        # Complete monitoring
        final_regime = RegimeType.BEAR_MARKET
        
        result = monitor.complete_transition_monitoring(transition_id, final_regime)
        
        assert isinstance(result, TransitionMonitoring)
        assert transition_id not in monitor.active_transitions
        assert len(monitor.monitoring_history) == 1


class TestRegimeTransitionManager:
    """Test main regime transition manager integration"""
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing"""
        return RegimeConfig(
            prediction_horizon_days=[1, 3, 7, 14, 30],
            min_training_samples=50,
            volatility_percentile_threshold=0.75,
            momentum_threshold=0.1
        )
    
    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        return pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100) * 0.02),
            'volume': np.random.randint(1000, 10000, 100),
            'high': 100 + np.cumsum(np.random.randn(100) * 0.02) + np.random.uniform(0, 2, 100),
            'low': 100 + np.cumsum(np.random.randn(100) * 0.02) - np.random.uniform(0, 2, 100)
        }, index=dates)
    
    def test_regime_transition_manager_initialization(self, sample_config):
        """Test regime transition manager initialization"""
        manager = RegimeTransitionManager(sample_config)
        
        assert manager.config == sample_config
        assert isinstance(manager.predictor, TransitionPredictor)
        assert isinstance(manager.rebalancing_manager, RebalancingManager)
        assert isinstance(manager.monitor, TransitionMonitor)
        assert manager.is_operational is False
    
    def test_initialize_success(self, sample_config):
        """Test successful initialization"""
        manager = RegimeTransitionManager(sample_config)
        
        result = manager.initialize()
        
        assert result is True
        assert manager.is_initialized is True
    
    def test_start_success(self, sample_config):
        """Test successful start"""
        manager = RegimeTransitionManager(sample_config)
        manager.initialize()
        
        result = manager.start()
        
        assert result is True
        assert manager.is_operational is True
    
    def test_stop_success(self, sample_config):
        """Test successful stop"""
        manager = RegimeTransitionManager(sample_config)
        manager.initialize()
        manager.start()
        
        result = manager.stop()
        
        assert result is True
        assert manager.is_operational is False
    
    def test_analyze_transition_opportunity(self, sample_config, sample_market_data):
        """Test transition opportunity analysis"""
        manager = RegimeTransitionManager(sample_config)
        manager.initialize()
        manager.start()
        
        # Mock regime detection
        current_regime = RegimeType.BULL_MARKET
        indicators = {
            'volatility': RegimeIndicator(
                name='volatility',
                current_value=0.15,
                signal_strength=SignalStrength.STRONG,
                indicator_type=IndicatorType.VOLATILITY_REGIME
            )
        }
        
        with patch.object(manager.predictor, 'predict_transition') as mock_predict:
            mock_predict.return_value = TransitionPrediction(
                current_regime=current_regime,
                predicted_regime=RegimeType.BEAR_MARKET,
                transition_probability=0.8,
                prediction_confidence=0.85
            )
            
            result = manager.analyze_transition_opportunity(
                sample_market_data, indicators, current_regime, {}
            )
            
            assert isinstance(result, dict)
            assert 'transition_prediction' in result
            assert result['transition_prediction'].current_regime == current_regime
            assert result['transition_prediction'].predicted_regime == RegimeType.BEAR_MARKET
    
    def test_generate_rebalancing_recommendations(self, sample_config):
        """Test rebalancing recommendation generation"""
        manager = RegimeTransitionManager(sample_config)
        manager.initialize()
        manager.start()
        
        transition_pred = TransitionPrediction(
            current_regime=RegimeType.BULL_MARKET,
            predicted_regime=RegimeType.BEAR_MARKET,
            transition_probability=0.8
        )
        
        portfolio_state = {'AAPL': 0.3, 'CASH': 0.7}
        
        with patch.object(manager.rebalancing_manager, 'generate_rebalancing_recommendation') as mock_generate:
            mock_generate.return_value = RebalancingRecommendation(
                trigger=RebalancingTrigger.REGIME_CHANGE_CONFIRMED,
                urgency=SignalStrength.STRONG
            )
            
            result = manager.generate_rebalancing_recommendations(transition_pred, portfolio_state)
            
            assert isinstance(result, list)
            assert len(result) > 0
            assert isinstance(result[0], RebalancingRecommendation)
    
    def test_monitor_active_transitions(self, sample_config):
        """Test monitoring active transitions"""
        manager = RegimeTransitionManager(sample_config)
        manager.initialize()
        manager.start()
        
        # Start a transition monitoring
        transition_id = "test_transition_1"
        transition_pred = TransitionPrediction(
            current_regime=RegimeType.BULL_MARKET,
            predicted_regime=RegimeType.BEAR_MARKET
        )
        
        with patch.object(manager.monitor, 'start_transition_monitoring') as mock_start:
            mock_start.return_value = True
            
            manager.start_transition_monitoring(transition_id, transition_pred)
            
            # Monitor active transitions
            current_regime = RegimeType.BEAR_MARKET
            portfolio_performance = 0.05
            risk_metrics = {'volatility': 0.2}
            
            with patch.object(manager.monitor, 'update_transition_monitoring') as mock_update:
                mock_update.return_value = True
                
                result = manager.monitor_active_transitions(
                    current_regime, portfolio_performance, risk_metrics
                )
                
                assert result is True
    
    def test_get_transition_analytics(self, sample_config):
        """Test transition analytics retrieval"""
        manager = RegimeTransitionManager(sample_config)
        manager.initialize()
        manager.start()
        
        # Add some mock monitoring history
        manager.monitor.monitoring_history = [
            TransitionMonitoring(
                current_phase=TransitionPhase.TRANSITION_COMPLETION,
                prediction_accuracy=0.85,
                timing_accuracy=0.80
            )
        ]
        
        result = manager.get_transition_analytics()
        
        assert isinstance(result, dict)
        assert 'total_transitions' in result
        assert 'average_accuracy' in result
        assert 'success_rate' in result
    
    def test_health_check(self, sample_config):
        """Test health check functionality"""
        manager = RegimeTransitionManager(sample_config)
        manager.initialize()
        manager.start()
        
        result = manager.health_check()
        
        assert isinstance(result, dict)
        assert 'healthy' in result
        assert 'operational' in result
        assert 'initialized' in result
        assert result['operational'] is True
        assert result['initialized'] is True


class TestTransitionPredictionDataClasses:
    """Test transition prediction data classes"""
    
    def test_transition_prediction_creation(self):
        """Test TransitionPrediction creation"""
        prediction = TransitionPrediction(
            current_regime=RegimeType.BULL_MARKET,
            predicted_regime=RegimeType.BEAR_MARKET,
            transition_probability=0.8,
            prediction_confidence=0.85,
            transition_type=TransitionType.GRADUAL,
            transition_phase=TransitionPhase.EARLY_WARNING
        )
        
        assert prediction.current_regime == RegimeType.BULL_MARKET
        assert prediction.predicted_regime == RegimeType.BEAR_MARKET
        assert prediction.transition_probability == 0.8
        assert prediction.prediction_confidence == 0.85
        assert prediction.transition_type == TransitionType.GRADUAL
        assert prediction.transition_phase == TransitionPhase.EARLY_WARNING
    
    def test_rebalancing_recommendation_creation(self):
        """Test RebalancingRecommendation creation"""
        recommendation = RebalancingRecommendation(
            trigger=RebalancingTrigger.REGIME_CHANGE_CONFIRMED,
            urgency=SignalStrength.STRONG,
            recommended_adjustments={'AAPL': -0.1, 'CASH': 0.1},
            implementation_horizon=1,
            recommendation_confidence=0.8
        )
        
        assert recommendation.trigger == RebalancingTrigger.REGIME_CHANGE_CONFIRMED
        assert recommendation.urgency == SignalStrength.STRONG
        assert recommendation.recommended_adjustments['AAPL'] == -0.1
        assert recommendation.implementation_horizon == 1
        assert recommendation.recommendation_confidence == 0.8
    
    def test_transition_monitoring_creation(self):
        """Test TransitionMonitoring creation"""
        monitoring = TransitionMonitoring(
            current_phase=TransitionPhase.ACTIVE_TRANSITION,
            transition_progress=0.5,
            portfolio_performance=0.05,
            realized_volatility=0.2
        )
        
        assert monitoring.current_phase == TransitionPhase.ACTIVE_TRANSITION
        assert monitoring.transition_progress == 0.5
        assert monitoring.portfolio_performance == 0.05
        assert monitoring.realized_volatility == 0.2


class TestTransitionEnums:
    """Test transition-related enums"""
    
    def test_transition_phase_enum(self):
        """Test TransitionPhase enum values"""
        assert TransitionPhase.STABLE.value == "stable"
        assert TransitionPhase.EARLY_WARNING.value == "early_warning"
        assert TransitionPhase.TRANSITION_BEGINNING.value == "transition_beginning"
        assert TransitionPhase.ACTIVE_TRANSITION.value == "active_transition"
        assert TransitionPhase.TRANSITION_COMPLETION.value == "transition_completion"
        assert TransitionPhase.CONSOLIDATION.value == "consolidation"
    
    def test_transition_type_enum(self):
        """Test TransitionType enum values"""
        assert TransitionType.GRADUAL.value == "gradual"
        assert TransitionType.SUDDEN.value == "sudden"
        assert TransitionType.OSCILLATING.value == "oscillating"
        assert TransitionType.FAILED.value == "failed"
        assert TransitionType.PARTIAL.value == "partial"
    
    def test_rebalancing_trigger_enum(self):
        """Test RebalancingTrigger enum values"""
        assert RebalancingTrigger.REGIME_CHANGE_CONFIRMED.value == "regime_change_confirmed"
        assert RebalancingTrigger.TRANSITION_PROBABILITY_HIGH.value == "transition_probability_high"
        assert RebalancingTrigger.RISK_THRESHOLD_EXCEEDED.value == "risk_threshold_exceeded"
        assert RebalancingTrigger.VOLATILITY_SPIKE.value == "volatility_spike"
        assert RebalancingTrigger.CORRELATION_BREAKDOWN.value == "correlation_breakdown"
        assert RebalancingTrigger.STRESS_INDICATOR_ALERT.value == "stress_indicator_alert"
        assert RebalancingTrigger.TIME_BASED.value == "time_based"
        assert RebalancingTrigger.PERFORMANCE_DEVIATION.value == "performance_deviation"


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_transition_predictor_error_handling(self):
        """Test transition predictor error handling"""
        predictor = TransitionPredictor(None)
        
        # Test with invalid data
        result = predictor.predict_transition(
            pd.DataFrame(), {}, RegimeType.BULL_MARKET
        )
        
        assert isinstance(result, TransitionPrediction)
        assert result.current_regime == RegimeType.BULL_MARKET
    
    def test_rebalancing_manager_error_handling(self):
        """Test rebalancing manager error handling"""
        manager = RebalancingManager(None)
        
        # Test with invalid recommendation
        recommendation = RebalancingRecommendation()
        portfolio_state = {}
        
        result = manager.validate_rebalancing_recommendation(recommendation, portfolio_state)
        
        # Should handle gracefully
        assert isinstance(result, bool)
    
    def test_transition_monitor_error_handling(self):
        """Test transition monitor error handling"""
        monitor = TransitionMonitor(None)
        
        # Test with invalid transition ID
        result = monitor.update_transition_monitoring(
            "invalid_id", RegimeType.BULL_MARKET, 0.0, {}
        )
        
        assert result is False
    
    def test_regime_transition_manager_error_handling(self):
        """Test regime transition manager error handling"""
        manager = RegimeTransitionManager(None)
        
        # Test operations before initialization
        result = manager.start()
        assert result is False
        
        result = manager.stop()
        assert result is True  # stop() always returns True


class TestIntegrationScenarios:
    """Test complex integration scenarios"""
    
    @pytest.fixture
    def sample_config(self):
        """Sample configuration for integration testing"""
        return RegimeConfig(
            prediction_horizon_days=[1, 3, 7],
            min_training_samples=20,
            volatility_percentile_threshold=0.75,
            momentum_threshold=0.1
        )
    
    def test_full_transition_workflow(self, sample_config):
        """Test complete transition workflow"""
        manager = RegimeTransitionManager(sample_config)
        
        # Initialize and start
        assert manager.initialize() is True
        assert manager.start() is True
        
        # Mock market data and indicators
        market_data = pd.DataFrame({
            'close': [100, 101, 99, 102, 98],
            'volume': [1000, 1100, 900, 1200, 800]
        })
        
        indicators = {
            'volatility': RegimeIndicator(
                name='volatility',
                current_value=0.2,
                signal_strength=SignalStrength.STRONG,
                indicator_type=IndicatorType.VOLATILITY_REGIME
            )
        }
        
        # Mock prediction
        with patch.object(manager.predictor, 'predict_transition') as mock_predict:
            mock_predict.return_value = TransitionPrediction(
                current_regime=RegimeType.BULL_MARKET,
                predicted_regime=RegimeType.BEAR_MARKET,
                transition_probability=0.8
            )
            
            # Analyze transition opportunity
            prediction = manager.analyze_transition_opportunity(
                market_data, indicators, RegimeType.BULL_MARKET, {}
            )
            
            assert isinstance(prediction, dict)
            assert 'transition_prediction' in prediction
            
            # Generate rebalancing recommendations
            with patch.object(manager.rebalancing_manager, 'generate_rebalancing_recommendation') as mock_rebal:
                mock_rebal.return_value = RebalancingRecommendation(
                    trigger=RebalancingTrigger.REGIME_CHANGE_CONFIRMED
                )
                
                recommendations = manager.generate_rebalancing_recommendations(
                    prediction, {'AAPL': 0.5, 'CASH': 0.5}
                )
                
                assert isinstance(recommendations, list)
        
        # Stop
        assert manager.stop() is True
    
    def test_multiple_concurrent_transitions(self, sample_config):
        """Test handling multiple concurrent transitions"""
        manager = RegimeTransitionManager(sample_config)
        manager.initialize()
        manager.start()
        
        # Start multiple transitions
        transition_ids = ["trans_1", "trans_2", "trans_3"]
        
        for i, trans_id in enumerate(transition_ids):
            prediction = TransitionPrediction(
                current_regime=RegimeType.BULL_MARKET,
                predicted_regime=RegimeType.BEAR_MARKET if i % 2 == 0 else RegimeType.SIDEWAYS
            )
            
            with patch.object(manager.monitor, 'start_transition_monitoring') as mock_start:
                mock_start.return_value = True
                manager.start_transition_monitoring(trans_id, prediction)
        
        # Monitor all transitions
        with patch.object(manager.monitor, 'update_transition_monitoring') as mock_update:
            mock_update.return_value = True
            
            result = manager.monitor_active_transitions(
                RegimeType.BEAR_MARKET, 0.05, {'volatility': 0.2}
            )
            
            assert result is True
    
    def test_transition_analytics_aggregation(self, sample_config):
        """Test transition analytics aggregation"""
        manager = RegimeTransitionManager(sample_config)
        manager.initialize()
        manager.start()
        
        # Add mock monitoring history
        manager.monitor.monitoring_history = [
            TransitionMonitoring(
                prediction_accuracy=0.8,
                timing_accuracy=0.75,
                risk_control_effectiveness=0.85
            ),
            TransitionMonitoring(
                prediction_accuracy=0.9,
                timing_accuracy=0.80,
                risk_control_effectiveness=0.90
            )
        ]
        
        analytics = manager.get_transition_analytics()
        
        assert analytics['total_transitions'] == 2
        assert 'average_accuracy' in analytics
        assert 'success_rate' in analytics
        assert analytics['average_accuracy'] > 0.8
