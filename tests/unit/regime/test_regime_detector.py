"""
Unit tests for regime component.
Tests regime detection, classification, analysis, and management.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import regime component classes



from core_engine.regime.regime_detector import (
    RegimeType,
    DetectionMethod,
    ConfidenceLevel,
    RegimeDetection,
    RegimeTransition,
    RegimeDetectionConfig,
    MarkovSwitchingDetector,
    GaussianMixtureDetector,
    VolatilityBasedDetector,
    ThresholdBasedDetector,
    RegimeDetector
)




class TestRegimeType:
    """Test RegimeType enum."""

    def test_regime_type_values(self):
        """Test RegimeType enum values."""
        assert RegimeType.BULL_MARKET.value == "bull_market"
        assert RegimeType.BEAR_MARKET.value == "bear_market"
        assert RegimeType.SIDEWAYS.value == "sideways"
        assert RegimeType.HIGH_VOLATILITY.value == "high_volatility"
        assert RegimeType.LOW_VOLATILITY.value == "low_volatility"


class TestDetectionMethod:
    """Test DetectionMethod enum."""

    def test_detection_method_values(self):
        """Test DetectionMethod enum values."""
        assert DetectionMethod.MARKOV_SWITCHING.value == "markov_switching"
        assert DetectionMethod.GAUSSIAN_MIXTURE.value == "gaussian_mixture"
        assert DetectionMethod.CLUSTERING.value == "clustering"
        assert DetectionMethod.THRESHOLD_BASED.value == "threshold_based"
        assert DetectionMethod.STATISTICAL_TESTS.value == "statistical_tests"


class TestConfidenceLevel:
    """Test ConfidenceLevel enum."""

    def test_confidence_level_values(self):
        """Test ConfidenceLevel enum values."""
        assert ConfidenceLevel.VERY_LOW.value == 0.50
        assert ConfidenceLevel.LOW.value == 0.65
        assert ConfidenceLevel.MEDIUM.value == 0.75
        assert ConfidenceLevel.HIGH.value == 0.85
        assert ConfidenceLevel.VERY_HIGH.value == 0.95


class TestRegimeDetectionConfig:
    """Test RegimeDetectionConfig dataclass."""

    def test_initialization_default(self):
        """Test RegimeDetectionConfig initialization with defaults."""
        config = RegimeDetectionConfig()

        assert config.methods == [DetectionMethod.MARKOV_SWITCHING, DetectionMethod.GAUSSIAN_MIXTURE, DetectionMethod.VOLATILITY_BASED]
        assert config.short_lookback == 20
        assert config.medium_lookback == 60
        assert config.long_lookback == 252
        assert config.volatility_window == 20
        assert config.volatility_threshold_high == 0.25
        assert config.volatility_threshold_low == 0.10
        assert config.bull_threshold == 0.15
        assert config.bear_threshold == -0.10
        assert config.min_regime_duration == 10
        assert config.confidence_threshold == 0.75
        assert config.n_regimes == 3
        assert config.switching_variance == True
        assert config.n_clusters == 3
        assert config.random_state == 42

    def test_initialization_custom(self):
        """Test RegimeDetectionConfig initialization with custom values."""
        config = RegimeDetectionConfig(
            methods=[DetectionMethod.MARKOV_SWITCHING, DetectionMethod.CLUSTERING],
            short_lookback=30,
            medium_lookback=90,
            long_lookback=365,
            volatility_window=30,
            volatility_threshold_high=0.30,
            volatility_threshold_low=0.15,
            bull_threshold=0.20,
            bear_threshold=-0.15,
            min_regime_duration=15,
            confidence_threshold=0.80,
            n_regimes=4,
            switching_variance=False,
            n_clusters=4,
            random_state=123
        )

        assert config.methods == [DetectionMethod.MARKOV_SWITCHING, DetectionMethod.CLUSTERING]
        assert config.short_lookback == 30
        assert config.medium_lookback == 90
        assert config.long_lookback == 365
        assert config.volatility_window == 30
        assert config.volatility_threshold_high == 0.30
        assert config.volatility_threshold_low == 0.15
        assert config.bull_threshold == 0.20
        assert config.bear_threshold == -0.15
        assert config.min_regime_duration == 15
        assert config.confidence_threshold == 0.80
        assert config.n_regimes == 4
        assert config.switching_variance == False
        assert config.n_clusters == 4
        assert config.random_state == 123


class TestRegimeDetection:
    """Test RegimeDetection dataclass."""

    def test_initialization(self):
        """Test RegimeDetection initialization."""
        timestamp = datetime.now()
        detection = RegimeDetection(
            timestamp=timestamp,
            regime_type=RegimeType.BULL_MARKET,
            confidence=0.85,
            method=DetectionMethod.THRESHOLD_BASED,
            regime_start=timestamp - timedelta(days=10),
            regime_duration=10,
            expected_duration=15,
            regime_probability=0.85,
            transition_probability=0.15,
            stability_score=0.9,
            avg_return=0.02,
            volatility=0.15,
            skewness=0.1,
            kurtosis=2.5,
            max_drawdown=0.05,
            features={"rsi": 65.0, "macd": 0.5},
            model_output={"probabilities": [0.85, 0.10, 0.05]}
        )

        assert detection.timestamp == timestamp
        assert detection.regime_type == RegimeType.BULL_MARKET
        assert detection.confidence == 0.85
        assert detection.method == DetectionMethod.THRESHOLD_BASED
        assert detection.regime_start == timestamp - timedelta(days=10)
        assert detection.regime_duration == 10
        assert detection.expected_duration == 15
        assert detection.regime_probability == 0.85
        assert detection.transition_probability == 0.15
        assert detection.stability_score == 0.9
        assert detection.avg_return == 0.02
        assert detection.volatility == 0.15
        assert detection.skewness == 0.1
        assert detection.kurtosis == 2.5
        assert detection.max_drawdown == 0.05
        assert detection.features == {"rsi": 65.0, "macd": 0.5}
        assert detection.model_output == {"probabilities": [0.85, 0.10, 0.05]}


class TestRegimeTransition:
    """Test RegimeTransition dataclass."""

    def test_initialization(self):
        """Test RegimeTransition initialization."""
        timestamp = datetime.now()
        transition = RegimeTransition(
            from_regime=RegimeType.SIDEWAYS,
            to_regime=RegimeType.BULL_MARKET,
            transition_date=timestamp,
            transition_probability=0.8,
            transition_speed="fast",
            transition_volatility=0.25,
            market_stress=0.7,
            leading_indicators={"rsi_divergence": 0.8, "volume_surge": 0.9},
            warning_signals=["high_volatility", "momentum_shift"],
            performance_impact=0.05,
            risk_impact=0.15
        )

        assert transition.from_regime == RegimeType.SIDEWAYS
        assert transition.to_regime == RegimeType.BULL_MARKET
        assert transition.transition_date == timestamp
        assert transition.transition_probability == 0.8
        assert transition.transition_speed == "fast"
        assert transition.transition_volatility == 0.25
        assert transition.market_stress == 0.7
        assert transition.leading_indicators == {"rsi_divergence": 0.8, "volume_surge": 0.9}
        assert transition.warning_signals == ["high_volatility", "momentum_shift"]
        assert transition.performance_impact == 0.05
        assert transition.risk_impact == 0.15


class TestMarkovSwitchingDetector:
    """Test MarkovSwitchingDetector class."""

    @pytest.fixture
    def detector_config(self):
        """Create detector configuration for testing."""
        return RegimeDetectionConfig()

    @pytest.fixture
    def sample_returns_data(self):
        """Create sample returns data for testing."""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=200, freq='D')

        # Generate regime-switching returns
        returns = np.zeros(200)

        # Regime 1: Low volatility (first 100 days)
        returns[:100] = np.random.normal(0.0005, 0.01, 100)

        # Regime 2: High volatility (last 100 days)
        returns[100:] = np.random.normal(0.001, 0.03, 100)

        data = pd.DataFrame({
            'timestamp': dates,
            'returns': returns
        })

        return data

    def test_initialization(self, detector_config):
        """Test MarkovSwitchingDetector initialization."""
        detector = MarkovSwitchingDetector(detector_config)

        assert hasattr(detector, 'fit')
        assert hasattr(detector, 'detect_regime')

    def test_detect_regime(self, sample_returns_data, detector_config):
        """Test regime detection using Markov switching."""
        detector = MarkovSwitchingDetector(detector_config)

        # First fit the model
        success = detector.fit(sample_returns_data['returns'])
        assert success

        # Then detect regime
        regime_detection = detector.detect_regime(sample_returns_data['returns'], datetime.now())

        assert isinstance(regime_detection, RegimeDetection)
        assert regime_detection.regime_type in RegimeType
        assert 0.0 <= regime_detection.confidence <= 1.0


class TestGaussianMixtureDetector:
    """Test GaussianMixtureDetector class."""

    @pytest.fixture
    def detector_config(self):
        """Create detector configuration for testing."""
        return RegimeDetectionConfig()

    @pytest.fixture
    def sample_multivariate_data(self):
        """Create sample multivariate data for testing."""
        np.random.seed(42)
        n_samples = 300

        # Generate data from two different regimes
        data = np.zeros((n_samples, 2))

        # Regime 1: Low volatility, positive correlation
        n_regime1 = 150
        returns1 = np.random.multivariate_normal([0.001, 0.0005], [[0.0001, 0.00005], [0.00005, 0.0001]], n_regime1)
        data[:n_regime1] = returns1

        # Regime 2: High volatility, negative correlation
        n_regime2 = 150
        returns2 = np.random.multivariate_normal([0.0005, 0.001], [[0.0004, -0.0001], [-0.0001, 0.0004]], n_regime2)
        data[n_regime1:] = returns2

        return pd.DataFrame(data, columns=['asset_a_returns', 'asset_b_returns'])

    def test_initialization(self, detector_config):
        """Test GaussianMixtureDetector initialization."""
        detector = GaussianMixtureDetector(detector_config)

        assert hasattr(detector, 'fit')
        assert hasattr(detector, 'detect_regime')

    def test_detect_regime(self, sample_multivariate_data, detector_config):
        """Test regime detection using GMM."""
        detector = GaussianMixtureDetector(detector_config)

        # First fit the model
        success = detector.fit(sample_multivariate_data)
        assert success

        # Then detect regime
        regime_detection = detector.detect_regime(sample_multivariate_data, datetime.now())

        assert isinstance(regime_detection, RegimeDetection)
        assert regime_detection.regime_type in RegimeType
        assert 0.0 <= regime_detection.confidence <= 1.0


class TestVolatilityBasedDetector:
    """Test VolatilityBasedDetector class."""

    @pytest.fixture
    def detector_config(self):
        """Create detector configuration for testing."""
        return RegimeDetectionConfig()

    @pytest.fixture
    def sample_volatility_data(self):
        """Create sample volatility data for testing."""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=200, freq='D')

        # Generate changing volatility
        volatility = np.zeros(200)

        # Low volatility period
        volatility[:100] = np.random.uniform(0.005, 0.015, 100)

        # High volatility period
        volatility[100:] = np.random.uniform(0.02, 0.05, 100)

        data = pd.DataFrame({
            'timestamp': dates,
            'volatility': volatility,
            'returns': np.random.randn(200) * 0.02
        })

        return data

    def test_initialization(self, detector_config):
        """Test VolatilityBasedDetector initialization."""
        detector = VolatilityBasedDetector(detector_config)

        assert hasattr(detector, 'detect_regime')

    def test_detect_regime(self, sample_volatility_data, detector_config):
        """Test volatility-based regime detection."""
        detector = VolatilityBasedDetector(detector_config)

        regime_detection = detector.detect_regime(sample_volatility_data['returns'], datetime.now())

        assert isinstance(regime_detection, RegimeDetection)
        assert regime_detection.regime_type in RegimeType
        assert 0.0 <= regime_detection.confidence <= 1.0


class TestThresholdBasedDetector:
    """Test ThresholdBasedDetector class."""

    @pytest.fixture
    def detector_config(self):
        """Create detector configuration for testing."""
        return RegimeDetectionConfig()

    @pytest.fixture
    def sample_threshold_data(self):
        """Create sample data for threshold-based detection."""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=200, freq='D')

        # Generate returns data
        returns = np.random.randn(200) * 0.02

        data = pd.DataFrame({
            'timestamp': dates,
            'returns': returns,
            'volatility': np.random.uniform(0.01, 0.04, 200)
        })

        return data

    def test_initialization(self, detector_config):
        """Test ThresholdBasedDetector initialization."""
        detector = ThresholdBasedDetector(detector_config)

        assert hasattr(detector, 'detect_regime')

    def test_detect_regime(self, sample_threshold_data, detector_config):
        """Test threshold-based regime detection."""
        detector = ThresholdBasedDetector(detector_config)

        regime_detection = detector.detect_regime(sample_threshold_data['returns'], datetime.now())

        assert isinstance(regime_detection, RegimeDetection)
        assert regime_detection.regime_type in RegimeType
        assert 0.0 <= regime_detection.confidence <= 1.0


class TestRegimeDetector:
    """Test RegimeDetector class."""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'timestamp': dates,
            'close': 100 + np.cumsum(np.random.randn(200) * 0.5),
            'returns': np.random.randn(200) * 0.02,
            'volatility': np.random.uniform(0.01, 0.04, 200)
        })

        return data

    @pytest.fixture
    def detector_config(self):
        """Create detector configuration for testing."""
        return RegimeDetectionConfig(
            methods=[DetectionMethod.THRESHOLD_BASED],
            short_lookback=20,
            confidence_threshold=0.7
        )

    def test_initialization(self, detector_config):
        """Test RegimeDetector initialization."""
        detector = RegimeDetector(detector_config)

        assert detector.config == detector_config
        assert hasattr(detector, 'detect_current_regime')

    def test_detect_regime(self, sample_market_data, detector_config):
        """Test regime detection."""
        detector = RegimeDetector(detector_config)

        detection = detector.detect_current_regime(sample_market_data)

        assert isinstance(detection, RegimeDetection)
        assert detection.regime_type in list(RegimeType)
        assert 0.0 <= detection.confidence <= 1.0

    def test_detect_transition(self, sample_market_data, detector_config):
        """Test regime transition detection."""
        detector = RegimeDetector(detector_config)
        
        # Run multiple detections to potentially create transitions
        detection1 = detector.detect_current_regime(sample_market_data.iloc[:100])
        detection2 = detector.detect_current_regime(sample_market_data.iloc[50:150])
        
        # Get transition history
        transitions = detector.get_transition_history()
        
        assert isinstance(transitions, list)
        if transitions:
            for transition in transitions:
                assert isinstance(transition, RegimeTransition)
                assert transition.from_regime in list(RegimeType)
                assert transition.to_regime in list(RegimeType)

    def test_empty_data_handling(self, detector_config):
        """Test handling of empty data."""
        empty_data = pd.DataFrame()

        detector = RegimeDetector(detector_config)

        result = detector.detect_current_regime(empty_data)
        assert result is None

    def test_insufficient_data_handling(self, detector_config):
        """Test handling of insufficient data."""
        insufficient_data = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=5),
            'close': [100, 101, 102, 103, 104]
        })

        detector = RegimeDetector(detector_config)

        # Should handle gracefully or return None for insufficient data
        result = detector.detect_current_regime(insufficient_data)
        assert result is None  # Expected for insufficient data


