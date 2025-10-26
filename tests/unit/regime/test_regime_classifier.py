"""
Unit tests for regime component.
Tests regime detection, classification, analysis, and management.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch

# Import regime component classes


from core_engine.regime.regime_classifier import (
    MLModel,
    FeatureType,
    FeatureImportance,
    ModelPerformance,
    RegimeClassification,
    FeatureEngineer,
    RegimeModelTrainer,
    RegimeClassifier
)

from core_engine.regime.regime_detector import (
    RegimeType
)




class TestMLModel:
    """Test MLModel enum."""

    def test_ml_model_values(self):
        """Test MLModel enum values."""
        assert MLModel.RANDOM_FOREST.value == "random_forest"
        assert MLModel.GRADIENT_BOOSTING.value == "gradient_boosting"
        assert MLModel.SVM.value == "svm"
        assert MLModel.NEURAL_NETWORK.value == "neural_network"


class TestFeatureType:
    """Test FeatureType enum."""

    def test_feature_type_values(self):
        """Test FeatureType enum values."""
        assert FeatureType.PRICE_BASED.value == "price_based"
        assert FeatureType.VOLATILITY_BASED.value == "volatility_based"
        assert FeatureType.MOMENTUM_BASED.value == "momentum_based"
        assert FeatureType.CORRELATION_BASED.value == "correlation_based"
        assert FeatureType.VOLUME_BASED.value == "volume_based"
        assert FeatureType.TECHNICAL_INDICATORS.value == "technical_indicators"
        assert FeatureType.MACRO_INDICATORS.value == "macro_indicators"
        assert FeatureType.SENTIMENT_INDICATORS.value == "sentiment_indicators"


class TestClassificationConfig:
    """Test ClassificationConfig dataclass."""

    def test_initialization_default(self):
        """Test ClassificationConfig initialization with defaults."""
        config = ClassificationConfig()

        assert config.primary_model == MLModel.ENSEMBLE
        assert config.models_to_test == [MLModel.RANDOM_FOREST, MLModel.GRADIENT_BOOSTING, MLModel.SVM, MLModel.LOGISTIC_REGRESSION]
        assert config.feature_types == [FeatureType.PRICE_BASED, FeatureType.VOLATILITY_BASED, FeatureType.MOMENTUM_BASED, FeatureType.CORRELATION_BASED]
        assert config.lookback_windows == [5, 10, 20, 60, 252]
        assert config.min_training_samples == 100
        assert config.test_size == 0.2
        assert config.validation_splits == 5
        assert config.max_features == 50
        assert config.feature_selection_method == "mutual_info"
        assert config.correlation_threshold == 0.95

    def test_initialization_custom(self):
        """Test ClassificationConfig initialization with custom values."""
        config = ClassificationConfig(
            primary_model=MLModel.GRADIENT_BOOSTING,
            models_to_test=[MLModel.RANDOM_FOREST, MLModel.SVM],
            feature_types=[FeatureType.PRICE_BASED, FeatureType.VOLATILITY_BASED],
            lookback_windows=[10, 20, 60],
            min_training_samples=200,
            test_size=0.3,
            validation_splits=3,
            max_features=25,
            feature_selection_method="f_classif",
            correlation_threshold=0.9
        )

        assert config.primary_model == MLModel.GRADIENT_BOOSTING
        assert config.models_to_test == [MLModel.RANDOM_FOREST, MLModel.SVM]
        assert config.feature_types == [FeatureType.PRICE_BASED, FeatureType.VOLATILITY_BASED]
        assert config.lookback_windows == [10, 20, 60]
        assert config.min_training_samples == 200
        assert config.test_size == 0.3
        assert config.validation_splits == 3
        assert config.max_features == 25
        assert config.feature_selection_method == "f_classif"
        assert config.correlation_threshold == 0.9


class TestFeatureImportance:
    """Test FeatureImportance dataclass."""

    def test_initialization(self):
        """Test FeatureImportance initialization."""
        importance = FeatureImportance(
            feature_name="rsi_14",
            importance_score=0.85,
            importance_rank=1,
            mean_value=50.0,
            std_value=10.0,
            correlation_with_target=0.65,
            regime_specific_importance={"bull": 0.8, "bear": 0.9}
        )

        assert importance.feature_name == "rsi_14"
        assert importance.importance_score == 0.85
        assert importance.importance_rank == 1
        assert importance.mean_value == 50.0
        assert importance.std_value == 10.0
        assert importance.correlation_with_target == 0.65
        assert importance.regime_specific_importance == {"bull": 0.8, "bear": 0.9}


class TestModelPerformance:
    """Test ModelPerformance dataclass."""

    def test_initialization(self):
        """Test ModelPerformance initialization."""
        performance = ModelPerformance(
            model_name="random_forest",
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            cv_accuracy_mean=0.83,
            cv_accuracy_std=0.02,
            regime_specific_metrics={"bull": {"accuracy": 0.87, "precision": 0.85}},
            confusion_matrix=np.array([[85, 15], [12, 88]]),
            feature_importances=[],
            training_samples=1000,
            training_time=45.2,
            last_trained=datetime(2024, 1, 1)
        )

        assert performance.model_name == "random_forest"
        assert performance.accuracy == 0.85
        assert performance.precision == 0.82
        assert performance.recall == 0.88
        assert performance.f1_score == 0.85
        assert performance.cv_accuracy_mean == 0.83
        assert performance.cv_accuracy_std == 0.02
        assert performance.regime_specific_metrics == {"bull": {"accuracy": 0.87, "precision": 0.85}}
        assert np.array_equal(performance.confusion_matrix, np.array([[85, 15], [12, 88]]))
        assert performance.training_samples == 1000
        assert performance.training_time == 45.2
        assert performance.last_trained == datetime(2024, 1, 1)


class TestRegimeClassification:
    """Test RegimeClassification dataclass."""

    def test_initialization(self):
        """Test RegimeClassification initialization."""
        timestamp = datetime.now()
        classification = RegimeClassification(
            timestamp=timestamp,
            predicted_regime=RegimeType.BULL_MARKET,
            prediction_confidence=0.85,
            regime_probabilities={RegimeType.BULL_MARKET: 0.85, RegimeType.SIDEWAYS: 0.15},
            top_3_regimes=[(RegimeType.BULL_MARKET, 0.85), (RegimeType.SIDEWAYS, 0.15)],
            feature_contributions={"rsi_14": 0.3, "macd": 0.25, "volume_ratio": 0.2},
            model_used=MLModel.RANDOM_FOREST,
            model_confidence=0.82,
            regime_stability=0.9,
            recent_regime_changes=2,
            prediction_horizon_days=5,
            prediction_decay=0.95
        )

        assert classification.timestamp == timestamp
        assert classification.predicted_regime == RegimeType.BULL_MARKET
        assert classification.prediction_confidence == 0.85
        assert classification.regime_probabilities == {RegimeType.BULL_MARKET: 0.85, RegimeType.SIDEWAYS: 0.15}
        assert classification.top_3_regimes == [(RegimeType.BULL_MARKET, 0.85), (RegimeType.SIDEWAYS, 0.15)]
        assert classification.feature_contributions == {"rsi_14": 0.3, "macd": 0.25, "volume_ratio": 0.2}
        assert classification.model_used == MLModel.RANDOM_FOREST
        assert classification.model_confidence == 0.82
        assert classification.regime_stability == 0.9
        assert classification.recent_regime_changes == 2
        assert classification.prediction_horizon_days == 5
        assert classification.prediction_decay == 0.95


class TestFeatureEngineer:
    """Test FeatureEngineer class."""

    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'high': 102 + np.cumsum(np.random.randn(100) * 0.5),
            'low': 98 + np.cumsum(np.random.randn(100) * 0.5),
            'volume': np.random.randint(1000, 10000, 100),
            'open': 100 + np.cumsum(np.random.randn(100) * 0.3)
        }, index=dates)

        return data

    @pytest.fixture
    def classifier_config(self):
        """Create classifier configuration for testing."""
        return ClassificationConfig(
            primary_model=MLModel.RANDOM_FOREST,
            max_features=20,
            lookback_windows=[5, 10, 20]  # Smaller windows for test data
        )

    def test_initialization(self, classifier_config):
        """Test FeatureEngineer initialization."""
        engineer = FeatureEngineer(classifier_config)

        assert engineer.config == classifier_config
        assert hasattr(engineer, 'engineer_features')

    def test_create_features(self, sample_price_data, classifier_config):
        """Test feature creation."""
        engineer = FeatureEngineer(classifier_config)

        features = engineer.engineer_features(sample_price_data)

        assert isinstance(features, pd.DataFrame)
        assert len(features) > 0
        assert len(features.columns) > len(sample_price_data.columns)


class TestRegimeModelTrainer:
    """Test RegimeModelTrainer class."""

    @pytest.fixture
    def sample_training_data(self):
        """Create sample training data for testing."""
        np.random.seed(42)
        n_samples = 1000

        # Generate features
        features = pd.DataFrame({
            'rsi_14': np.random.uniform(20, 80, n_samples),
            'macd': np.random.randn(n_samples) * 0.1,
            'volume_ratio': np.random.uniform(0.5, 1.5, n_samples),
            'volatility_20': np.random.uniform(0.1, 0.5, n_samples),
            'momentum_10': np.random.randn(n_samples) * 0.05
        })

        # Generate target regimes
        regimes = np.random.choice(list(RegimeType), n_samples)
        target = pd.Series(regimes)

        return features, target

    @pytest.fixture
    def trainer_config(self):
        """Create trainer configuration for testing."""
        return ClassificationConfig(
            primary_model=MLModel.RANDOM_FOREST,
            max_features=20,
            lookback_windows=[5, 10, 20]  # Smaller windows for test data
        )

    def test_initialization(self, trainer_config):
        """Test RegimeModelTrainer initialization."""
        trainer = RegimeModelTrainer(trainer_config)

        assert trainer.config == trainer_config
        assert hasattr(trainer, 'train_models')

    @patch('core_engine.regime.regime_classifier.RandomForestClassifier')
    def test_train_model(self, mock_rf, sample_training_data, trainer_config):
        """Test model training."""
        features, target = sample_training_data

        # Mock the classifier
        mock_model = Mock()
        mock_model.fit.return_value = None
        mock_model.score.return_value = 0.85
        mock_rf.return_value = mock_model

        trainer = RegimeModelTrainer(trainer_config)

        performances = trainer.train_models(features, target)

        assert isinstance(performances, dict)
        assert len(performances) > 0
        for model_name, performance in performances.items():
            assert isinstance(performance, ModelPerformance)

    def test_predict_regime(self, sample_training_data, trainer_config):
        """Test regime prediction."""
        features, target = sample_training_data

        trainer = RegimeModelTrainer(trainer_config)
        trainer.train_models(features, target)

        # Test prediction with a single sample
        single_sample = features.iloc[:1]
        prediction = trainer.predict_regime(single_sample)

        assert isinstance(prediction, RegimeClassification)


class TestRegimeClassifier:
    """Test RegimeClassifier class."""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'timestamp': dates,
            'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'high': 102 + np.cumsum(np.random.randn(100) * 0.5),
            'low': 98 + np.cumsum(np.random.randn(100) * 0.5),
            'volume': np.random.randint(1000, 10000, 100),
            'open': 100 + np.cumsum(np.random.randn(100) * 0.3)
        })

        return data

    @pytest.fixture
    def classifier_config(self):
        """Create classifier configuration for testing."""
        return ClassificationConfig(
            primary_model=MLModel.RANDOM_FOREST,
            max_features=20,
            lookback_windows=[5, 10, 20]  # Smaller windows for test data
        )

    def test_initialization(self, classifier_config):
        """Test RegimeClassifier initialization."""
        classifier = RegimeClassifier(classifier_config)

        assert classifier.config == classifier_config
        assert hasattr(classifier, 'classify_regime')

    @patch('core_engine.regime.regime_classifier.RegimeModelTrainer')
    @patch('core_engine.regime.regime_classifier.FeatureEngineer')
    def test_classify_regime(self, mock_feature_engineer, mock_trainer, sample_market_data, classifier_config):
        """Test regime classification."""
        # Mock feature engineer
        mock_engineer_instance = Mock()
        mock_features = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [0.1, 0.2, 0.3]})
        mock_engineer_instance.engineer_features.return_value = mock_features
        mock_feature_engineer.return_value = mock_engineer_instance

        # Mock trainer
        mock_trainer_instance = Mock()
        mock_classification = Mock(spec=RegimeClassification)
        mock_classification.predicted_regime = RegimeType.BULL_MARKET
        mock_classification.prediction_confidence = 0.85
        mock_trainer_instance.predict_regime.return_value = mock_classification
        mock_trainer.return_value = mock_trainer_instance

        classifier = RegimeClassifier(classifier_config)

        classification = classifier.classify_regime(sample_market_data)

        assert classification is not None
        assert classification.predicted_regime == RegimeType.BULL_MARKET
        assert classification.prediction_confidence == 0.85

    def test_empty_data_handling(self, classifier_config):
        """Test handling of empty data."""
        empty_data = pd.DataFrame()

        classifier = RegimeClassifier(classifier_config)

        result = classifier.classify_regime(empty_data)
        assert result is None

    def test_untrained_model_handling(self, sample_market_data, classifier_config):
        """Test handling when model is not trained."""
        classifier = RegimeClassifier(classifier_config)

        result = classifier.classify_regime(sample_market_data)
        assert result is None


