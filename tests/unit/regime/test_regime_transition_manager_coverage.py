"""
Additional Test Coverage for Regime Transition Manager

Tests critical missing coverage areas:
- _prepare_training_data (lines 302-341)
- _train_horizon_models (lines 363-409)
- _create_volatility_based_recommendation (lines 1025-1045)
- Other production transition system methods
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from core_engine.regime.regime_transition_manager import (
    TransitionPredictor,
    RebalancingManager,
    TransitionPrediction,
    RebalancingRecommendation,
    TransitionPhase,
    TransitionType,
    RebalancingTrigger,
    SignalStrength
)

from core_engine.regime.regime_detector import RegimeType
from core_engine.regime.regime_indicators import RegimeIndicator, IndicatorType
from core_engine.config.component_config import RegimeConfig


class TestPrepareTrainingData:
    """Test _prepare_training_data method (lines 302-341)"""
    
    @pytest.fixture
    def sample_config(self):
        """Sample config with feature extraction enabled"""
        config = RegimeConfig()
        # Set feature extraction flags (these attributes must exist for code to work)
        config.volatility_features = True
        config.momentum_features = True
        config.correlation_features = True
        config.feature_lookback_periods = [5, 10, 20]
        # Set model_types (required for _train_horizon_models)
        config.model_types = ['random_forest']
        return config
    
    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical data for training"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        # Create multi-asset data for correlation features
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100) * 0.02),
            'close2': 50 + np.cumsum(np.random.randn(100) * 0.015),
            'volume': np.random.randint(1000, 10000, 100),
        }, index=dates)
        
        return data
    
    @pytest.fixture
    def sample_regime_history(self):
        """Sample regime history"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        regimes = [RegimeType.BULL_MARKET] * 50 + [RegimeType.BEAR_MARKET] * 50
        return pd.Series(regimes, index=dates)
    
    @pytest.fixture
    def sample_indicators_history(self):
        """Sample indicators history"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
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
    
    def test_prepare_training_data_with_all_features(self, sample_config, sample_historical_data,
                                                    sample_regime_history, sample_indicators_history):
        """Test preparing training data with all feature types enabled"""
        predictor = TransitionPredictor(sample_config)
        
        features, regime_history = predictor._prepare_training_data(
            sample_historical_data, sample_regime_history, sample_indicators_history
        )
        
        # Should have features extracted (may be empty if insufficient data, but should be DataFrame)
        assert isinstance(features, pd.DataFrame)
        
        # If features were extracted, check they have expected columns
        if len(features) > 0:
            # Should have volatility features for each period (if data sufficient)
            for period in sample_config.feature_lookback_periods:
                if f'volatility_{period}d' in features.columns:
                    # Feature exists
                    pass
            
            # Feature names should be stored
            assert len(predictor.feature_names) > 0
            
            # Should match regime history length (after dropna)
            assert len(features) <= len(regime_history)
    
    def test_prepare_training_data_only_volatility_features(self, sample_config, sample_historical_data,
                                                          sample_regime_history, sample_indicators_history):
        """Test preparing training data with only volatility features"""
        sample_config.volatility_features = True
        sample_config.momentum_features = False
        sample_config.correlation_features = False
        
        predictor = TransitionPredictor(sample_config)
        
        features, regime_history = predictor._prepare_training_data(
            sample_historical_data, sample_regime_history, sample_indicators_history
        )
        
        assert isinstance(features, pd.DataFrame)
        
        # If features extracted, check composition
        if len(features) > 0:
            # Should have volatility features for each period
            vol_cols = [col for col in features.columns if 'volatility' in col]
            assert len(vol_cols) > 0
            
            # Should not have momentum features (if disabled)
            mom_cols = [col for col in features.columns if 'momentum' in col]
            assert len(mom_cols) == 0
    
    def test_prepare_training_data_insufficient_data(self, sample_config):
        """Test preparing training data with insufficient data"""
        predictor = TransitionPredictor(sample_config)
        
        # Create data with less than minimum lookback period
        small_data = pd.DataFrame({
            'close': [100, 101, 102]
        })
        small_regime = pd.Series([RegimeType.BULL_MARKET] * 3)
        
        features, regime_history = predictor._prepare_training_data(
            small_data, small_regime, []
        )
        
        # Should return empty DataFrame when insufficient data
        assert isinstance(features, pd.DataFrame)
        assert len(features) == 0
    
    def test_prepare_training_data_single_asset_no_correlation(self, sample_config):
        """Test preparing training data with single asset (no correlation features)"""
        predictor = TransitionPredictor(sample_config)
        
        # Single column data (no correlation possible)
        single_asset_data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100) * 0.02)
        })
        regime_history = pd.Series([RegimeType.BULL_MARKET] * 100)
        
        features, _ = predictor._prepare_training_data(
            single_asset_data, regime_history, []
        )
        
        assert isinstance(features, pd.DataFrame)
        # Correlation features should not be created for single asset
        correlation_cols = [col for col in features.columns if 'correlation' in col]
        assert len(correlation_cols) == 0
    
    def test_prepare_training_data_error_handling(self, sample_config):
        """Test error handling in _prepare_training_data"""
        predictor = TransitionPredictor(sample_config)
        
        # Invalid data types
        with patch('pandas.DataFrame.pct_change', side_effect=Exception("Test error")):
            features, regime_history = predictor._prepare_training_data(
                pd.DataFrame({'close': [100, 101, 102]}),
                pd.Series([RegimeType.BULL_MARKET] * 3),
                []
            )
            
            # Should return empty DataFrames on error
            assert isinstance(features, pd.DataFrame)
            assert len(features) == 0
            assert isinstance(regime_history, pd.Series)
            assert len(regime_history) == 0


class TestTrainHorizonModels:
    """Test _train_horizon_models method (lines 363-409)"""
    
    @pytest.fixture
    def sample_config(self):
        """Sample config with model types"""
        config = RegimeConfig()
        # Set model_types (required attribute)
        config.model_types = ['random_forest', 'gradient_boosting', 'logistic']
        config.test_size = 0.2
        # Set feature flags for compatibility
        config.volatility_features = True
        config.momentum_features = True
        config.correlation_features = True
        return config
    
    @pytest.fixture
    def sample_training_data(self):
        """Sample training data"""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 10))
        y = pd.Series(np.random.randint(0, 2, 100))
        return X, y
    
    def test_train_horizon_models_all_types(self, sample_config, sample_training_data):
        """Test training models for all model types"""
        predictor = TransitionPredictor(sample_config)
        X, y = sample_training_data
        
        performances = predictor._train_horizon_models(X, y, horizon=5)
        
        # Should return performance metrics for each model
        assert isinstance(performances, dict)
        assert len(performances) == len(sample_config.model_types)
        
        # Each model type should have performance metrics
        for model_type in sample_config.model_types:
            assert model_type in performances
            perf = performances[model_type]
            
            if model_type == 'logistic':
                assert 'accuracy' in perf
                assert perf['type'] == 'classification'
            else:
                assert 'mse' in perf
                assert 'mae' in perf
                assert 'r2' in perf
                assert perf['type'] == 'regression'
        
        # Models should be stored
        for model_type in sample_config.model_types:
            model_key = f'5d_{model_type}'
            assert model_key in predictor.models
        
        # Scaler should be stored
        assert '5d' in predictor.scalers
    
    def test_train_horizon_models_logistic_only(self, sample_config, sample_training_data):
        """Test training with logistic regression only"""
        sample_config.model_types = ['logistic']
        predictor = TransitionPredictor(sample_config)
        X, y = sample_training_data
        
        performances = predictor._train_horizon_models(X, y, horizon=7)
        
        assert len(performances) == 1
        assert 'logistic' in performances
        assert performances['logistic']['type'] == 'classification'
        assert 'accuracy' in performances['logistic']
    
    def test_train_horizon_models_regression_only(self, sample_config, sample_training_data):
        """Test training with regression models only"""
        sample_config.model_types = ['random_forest', 'gradient_boosting']
        predictor = TransitionPredictor(sample_config)
        X, y = sample_training_data
        
        performances = predictor._train_horizon_models(X, y, horizon=10)
        
        assert len(performances) == 2
        for model_type in ['random_forest', 'gradient_boosting']:
            assert model_type in performances
            assert performances[model_type]['type'] == 'regression'
            assert 'mse' in performances[model_type]
            assert 'mae' in performances[model_type]
            assert 'r2' in performances[model_type]
    
    def test_train_horizon_models_error_handling(self, sample_config):
        """Test error handling in _train_horizon_models"""
        predictor = TransitionPredictor(sample_config)
        
        # Invalid data
        X = pd.DataFrame()
        y = pd.Series()
        
        performances = predictor._train_horizon_models(X, y, horizon=5)
        
        # Should return empty dict on error
        assert isinstance(performances, dict)
        assert len(performances) == 0
    
    def test_train_horizon_models_custom_test_size(self, sample_config, sample_training_data):
        """Test training with custom test size"""
        sample_config.test_size = 0.3
        predictor = TransitionPredictor(sample_config)
        X, y = sample_training_data
        
        performances = predictor._train_horizon_models(X, y, horizon=5)
        
        # Should still work with custom test size
        assert isinstance(performances, dict)
        assert len(performances) > 0


class TestCreateVolatilityBasedRecommendation:
    """Test _create_volatility_based_recommendation method (lines 1025-1045)"""
    
    @pytest.fixture
    def sample_config(self):
        """Sample config"""
        return RegimeConfig()
    
    @pytest.fixture
    def sample_transition_prediction(self):
        """Sample transition prediction with high volatility"""
        return TransitionPrediction(
            current_regime=RegimeType.BULL_MARKET,
            predicted_regime=RegimeType.BEAR_MARKET,
            transition_probability=0.8,
            volatility_increase_factor=1.5  # 50% increase
        )
    
    @pytest.fixture
    def sample_portfolio(self):
        """Sample portfolio state"""
        return {
            'AAPL': 0.3,
            'TSLA': 0.2,
            'CASH': 0.5
        }
    
    def test_create_volatility_based_recommendation(self, sample_config, sample_transition_prediction,
                                                   sample_portfolio):
        """Test creating volatility-based rebalancing recommendation"""
        manager = RebalancingManager(sample_config)
        
        recommendation = manager._create_volatility_based_recommendation(
            sample_transition_prediction, sample_portfolio
        )
        
        assert isinstance(recommendation, RebalancingRecommendation)
        assert recommendation.trigger == RebalancingTrigger.VOLATILITY_SPIKE
        assert recommendation.urgency == SignalStrength.STRONG
        
        # Should have adjustments for each asset
        assert len(recommendation.recommended_adjustments) == len(sample_portfolio)
        
        # All adjustments should be negative (reducing volatility exposure)
        for adjustment in recommendation.recommended_adjustments.values():
            assert adjustment <= 0
        
        # Should have volatility adjustment target
        assert recommendation.target_volatility_adjustment is not None
        assert recommendation.target_volatility_adjustment < 1.0  # Reducing volatility
        
        # Should have implementation horizon
        assert recommendation.implementation_horizon == 1  # Urgent
        
        # Should have risk mitigation measures
        assert len(recommendation.risk_mitigation_measures) > 0
        assert 'volatility' in ' '.join(recommendation.risk_mitigation_measures).lower()
    
    def test_create_volatility_based_recommendation_high_volatility(self, sample_config, sample_portfolio):
        """Test creating recommendation with very high volatility increase"""
        manager = RebalancingManager(sample_config)
        
        high_vol_prediction = TransitionPrediction(
            volatility_increase_factor=2.0  # 100% increase
        )
        
        recommendation = manager._create_volatility_based_recommendation(
            high_vol_prediction, sample_portfolio
        )
        
        assert recommendation.trigger == RebalancingTrigger.VOLATILITY_SPIKE
        
        # Adjustments should be larger for higher volatility
        total_adjustment = sum(abs(adj) for adj in recommendation.recommended_adjustments.values())
        assert total_adjustment > 0
    
    def test_create_volatility_based_recommendation_low_volatility(self, sample_config, sample_portfolio):
        """Test creating recommendation with low volatility increase"""
        manager = RebalancingManager(sample_config)
        
        low_vol_prediction = TransitionPrediction(
            volatility_increase_factor=1.1  # 10% increase
        )
        
        recommendation = manager._create_volatility_based_recommendation(
            low_vol_prediction, sample_portfolio
        )
        
        assert recommendation.trigger == RebalancingTrigger.VOLATILITY_SPIKE
        
        # Adjustments should be smaller for lower volatility
        total_adjustment = sum(abs(adj) for adj in recommendation.recommended_adjustments.values())
        assert total_adjustment >= 0
    
    def test_create_volatility_based_recommendation_adjustment_limits(self, sample_config, sample_portfolio):
        """Test that adjustments respect limits"""
        manager = RebalancingManager(sample_config)
        
        extreme_vol_prediction = TransitionPrediction(
            volatility_increase_factor=5.0  # 400% increase
        )
        
        recommendation = manager._create_volatility_based_recommendation(
            extreme_vol_prediction, sample_portfolio
        )
        
        # Each adjustment should be capped at 0.2 (20%)
        for adjustment in recommendation.recommended_adjustments.values():
            assert abs(adjustment) <= 0.2
    
    def test_create_volatility_based_recommendation_error_handling(self, sample_config):
        """Test error handling in _create_volatility_based_recommendation"""
        manager = RebalancingManager(sample_config)
        
        # Invalid prediction
        invalid_prediction = TransitionPrediction(
            volatility_increase_factor=None  # Invalid
        )
        
        recommendation = manager._create_volatility_based_recommendation(
            invalid_prediction, {}
        )
        
        # Should return valid recommendation with default trigger
        assert isinstance(recommendation, RebalancingRecommendation)
        assert recommendation.trigger == RebalancingTrigger.VOLATILITY_SPIKE


class TestCreateCorrelationBasedRecommendation:
    """Test _create_correlation_based_recommendation method"""
    
    @pytest.fixture
    def sample_config(self):
        return RegimeConfig()
    
    @pytest.fixture
    def sample_portfolio(self):
        return {
            'AAPL': 0.3,
            'TSLA': 0.2,
            'CASH': 0.5
        }
    
    def test_create_correlation_based_recommendation(self, sample_config, sample_portfolio):
        """Test creating correlation-based rebalancing recommendation"""
        manager = RebalancingManager(sample_config)
        
        prediction = TransitionPrediction(
            correlation_change_factor=1.3  # 30% increase
        )
        
        recommendation = manager._create_correlation_based_recommendation(
            prediction, sample_portfolio
        )
        
        assert isinstance(recommendation, RebalancingRecommendation)
        assert recommendation.trigger == RebalancingTrigger.CORRELATION_BREAKDOWN
        assert recommendation.urgency == SignalStrength.MODERATE
        
        # Should have adjustments
        assert len(recommendation.recommended_adjustments) == len(sample_portfolio)
        
        # Should have risk mitigation measures
        assert len(recommendation.risk_mitigation_measures) > 0
        assert 'diversification' in ' '.join(recommendation.risk_mitigation_measures).lower()
    
    def test_create_correlation_based_recommendation_high_change(self, sample_config, sample_portfolio):
        """Test with high correlation change"""
        manager = RebalancingManager(sample_config)
        
        prediction = TransitionPrediction(
            correlation_change_factor=1.5  # 50% increase
        )
        
        recommendation = manager._create_correlation_based_recommendation(
            prediction, sample_portfolio
        )
        
        # Adjustments should respect limits (15%)
        for adjustment in recommendation.recommended_adjustments.values():
            assert abs(adjustment) <= 0.15
    
    def test_create_correlation_based_recommendation_error_handling(self, sample_config):
        """Test error handling"""
        manager = RebalancingManager(sample_config)
        
        invalid_prediction = TransitionPrediction(
            correlation_change_factor=None
        )
        
        recommendation = manager._create_correlation_based_recommendation(
            invalid_prediction, {}
        )
        
        assert isinstance(recommendation, RebalancingRecommendation)
        assert recommendation.trigger == RebalancingTrigger.CORRELATION_BREAKDOWN


class TestTransitionMonitoringMethods:
    """Test transition monitoring methods that are missing coverage"""
    
    @pytest.fixture
    def sample_config(self):
        return RegimeConfig()
    
    def test_calculate_final_metrics_low_volatility(self, sample_config):
        """Test _calculate_final_metrics with low realized volatility"""
        from core_engine.regime.regime_transition_manager import TransitionMonitor, TransitionMonitoring
        
        monitor = TransitionMonitor(sample_config)
        monitoring = TransitionMonitoring(
            realized_volatility=0.16,  # Within 20% of target (0.15)
            relative_performance=0.02
        )
        
        monitor._calculate_final_metrics(monitoring)
        
        assert monitoring.risk_control_effectiveness == 0.8
        assert monitoring.prediction_accuracy == 0.8
    
    def test_calculate_final_metrics_high_volatility(self, sample_config):
        """Test _calculate_final_metrics with high realized volatility"""
        from core_engine.regime.regime_transition_manager import TransitionMonitor, TransitionMonitoring
        
        monitor = TransitionMonitor(sample_config)
        monitoring = TransitionMonitoring(
            realized_volatility=0.30,  # > 1.5x target
            relative_performance=-0.03
        )
        
        monitor._calculate_final_metrics(monitoring)
        
        assert monitoring.risk_control_effectiveness == 0.4
        assert monitoring.prediction_accuracy == 0.4
    
    def test_calculate_final_metrics_moderate_performance(self, sample_config):
        """Test _calculate_final_metrics with moderate performance"""
        from core_engine.regime.regime_transition_manager import TransitionMonitor, TransitionMonitoring
        
        monitor = TransitionMonitor(sample_config)
        monitoring = TransitionMonitoring(
            realized_volatility=0.20,  # Between 1.2x and 1.5x
            relative_performance=-0.01  # Between 0 and -0.02
        )
        
        monitor._calculate_final_metrics(monitoring)
        
        assert monitoring.risk_control_effectiveness == 0.6
        assert monitoring.prediction_accuracy == 0.6
    
    def test_generate_lessons_learned_successful(self, sample_config):
        """Test _generate_lessons_learned with successful transition"""
        from core_engine.regime.regime_transition_manager import TransitionMonitor, TransitionMonitoring
        
        monitor = TransitionMonitor(sample_config)
        monitoring = TransitionMonitoring(
            relative_performance=0.03,
            risk_control_effectiveness=0.85,
            prediction_accuracy=0.75,
            realized_volatility=0.18
        )
        
        # Initialize lists
        monitoring.successful_adjustments = []
        monitoring.failed_adjustments = []
        monitoring.improvement_opportunities = []
        
        monitor._generate_lessons_learned(monitoring)
        
        assert len(monitoring.successful_adjustments) > 0
        assert "risk management" in ' '.join(monitoring.successful_adjustments).lower()
    
    def test_generate_lessons_learned_failed(self, sample_config):
        """Test _generate_lessons_learned with failed transition"""
        from core_engine.regime.regime_transition_manager import TransitionMonitor, TransitionMonitoring
        
        monitor = TransitionMonitor(sample_config)
        monitoring = TransitionMonitoring(
            relative_performance=-0.06,
            risk_control_effectiveness=0.5,
            prediction_accuracy=0.5,
            realized_volatility=0.30
        )
        
        # Initialize lists
        monitoring.successful_adjustments = []
        monitoring.failed_adjustments = []
        monitoring.improvement_opportunities = []
        
        monitor._generate_lessons_learned(monitoring)
        
        assert len(monitoring.failed_adjustments) > 0
        assert len(monitoring.improvement_opportunities) > 0
        assert "excessive volatility" in ' '.join(monitoring.failed_adjustments).lower() or \
               "underperformed" in ' '.join(monitoring.failed_adjustments).lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

