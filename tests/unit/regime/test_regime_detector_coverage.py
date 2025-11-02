"""
Additional Test Coverage for Regime Detector

Tests critical missing coverage areas:
- _prepare_features (lines 909-955)
- _calculate_rsi (lines 957-972)
- _combine_detections (lines 974-1047)
- _create_transition (lines 1049-1088)
- get_regime_history / get_transition_history (lines 1090-1118)
- get_regime_statistics (lines 1120-1163)
- Statistics calculation methods (lines 1165-1266)
- ISystemComponent methods (lines 1271-1332)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from core_engine.regime.regime_detector import (
    RegimeDetector,
    RegimeDetection,
    RegimeTransition,
    RegimeType,
    DetectionMethod,
    RegimeDetectionConfig
)


class TestPrepareFeatures:
    """Test _prepare_features method"""
    
    @pytest.fixture
    def detector(self):
        """Create RegimeDetector instance"""
        config = RegimeDetectionConfig()
        return RegimeDetector(config)
    
    @pytest.fixture
    def sample_market_data_with_all_columns(self):
        """Market data with all columns (close, volume)"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        returns = pd.Series(np.random.randn(100) * 0.02, index=dates)
        
        market_data = pd.DataFrame({
            'timestamp': dates,
            'close': 100 + np.cumsum(returns),
            'volume': np.random.uniform(1000000, 5000000, 100)
        }, index=dates)
        
        return market_data, returns
    
    @pytest.fixture
    def sample_market_data_minimal(self):
        """Market data with only price column"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        returns = pd.Series(np.random.randn(100) * 0.02, index=dates)
        
        market_data = pd.DataFrame({
            'timestamp': dates,
            'price': 100 + np.cumsum(returns)
        }, index=dates)
        
        return market_data, returns
    
    def test_prepare_features_with_all_columns(self, detector, sample_market_data_with_all_columns):
        """Test feature preparation with all columns (close, volume)"""
        market_data, returns = sample_market_data_with_all_columns
        
        features = detector._prepare_features(market_data, returns)
        
        assert isinstance(features, pd.DataFrame)
        assert len(features) > 0
        
        # Check return-based features
        assert 'returns' in features.columns
        assert 'returns_ma5' in features.columns
        assert 'returns_ma20' in features.columns
        assert 'returns_std20' in features.columns
        
        # Check volatility features
        assert 'volatility' in features.columns
        assert 'volatility_ma' in features.columns
        assert 'volatility_ratio' in features.columns
        
        # Check price features (should exist when 'close' is present)
        assert 'price_ma20' in features.columns
        assert 'price_ma50' in features.columns
        assert 'price_ratio' in features.columns
        
        # Check volume features (should exist when 'volume' is present)
        assert 'volume_ma' in features.columns
        assert 'volume_ratio' in features.columns
        
        # Check technical indicators
        assert 'rsi' in features.columns
        assert 'momentum' in features.columns
        
        # Check higher-order moments
        assert 'skewness' in features.columns
        assert 'kurtosis' in features.columns
    
    def test_prepare_features_without_volume(self, detector, sample_market_data_minimal):
        """Test feature preparation without volume column"""
        market_data, returns = sample_market_data_minimal
        
        # Add 'close' column but not 'volume'
        market_data['close'] = market_data['price']
        
        features = detector._prepare_features(market_data, returns)
        
        assert isinstance(features, pd.DataFrame)
        assert len(features) > 0
        
        # Volume features should not exist
        assert 'volume_ma' not in features.columns
        assert 'volume_ratio' not in features.columns
        
        # But price features should exist
        assert 'price_ma20' in features.columns
    
    def test_prepare_features_short_data(self, detector):
        """Test feature preparation with insufficient data for trend features"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        np.random.seed(42)
        returns = pd.Series(np.random.randn(30) * 0.02, index=dates)
        
        market_data = pd.DataFrame({
            'timestamp': dates,
            'close': 100 + np.cumsum(returns)
        }, index=dates)
        
        features = detector._prepare_features(market_data, returns)
        
        assert isinstance(features, pd.DataFrame)
        # Trend features may not exist if data is too short (<50)
        # But other features should still exist
        assert 'returns' in features.columns or len(features) == 0
    
    def test_prepare_features_error_handling(self, detector):
        """Test feature preparation error handling"""
        # Invalid data that will cause errors
        invalid_data = pd.DataFrame({'invalid': [1, 2, 3]})
        invalid_returns = pd.Series([1, 2, 3])
        
        features = detector._prepare_features(invalid_data, invalid_returns)
        
        # Should return empty DataFrame on error
        assert isinstance(features, pd.DataFrame)


class TestCalculateRSI:
    """Test _calculate_rsi method"""
    
    @pytest.fixture
    def detector(self):
        """Create RegimeDetector instance"""
        config = RegimeDetectionConfig()
        return RegimeDetector(config)
    
    def test_calculate_rsi_normal_data(self, detector):
        """Test RSI calculation with normal data"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        np.random.seed(42)
        returns = pd.Series(np.random.randn(50) * 0.02, index=dates)
        
        rsi = detector._calculate_rsi(returns)
        
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(returns)
        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        if len(valid_rsi) > 0:
            assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()
    
    def test_calculate_rsi_custom_period(self, detector):
        """Test RSI calculation with custom period"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        np.random.seed(42)
        returns = pd.Series(np.random.randn(50) * 0.02, index=dates)
        
        rsi = detector._calculate_rsi(returns, period=10)
        
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(returns)
    
    def test_calculate_rsi_error_handling(self, detector):
        """Test RSI calculation error handling"""
        # Empty series
        empty_returns = pd.Series([], dtype=float)
        rsi = detector._calculate_rsi(empty_returns)
        assert isinstance(rsi, pd.Series)
        
        # Single value
        single_returns = pd.Series([0.01])
        rsi = detector._calculate_rsi(single_returns)
        assert isinstance(rsi, pd.Series)


class TestCombineDetections:
    """Test _combine_detections method"""
    
    @pytest.fixture
    def detector(self):
        """Create RegimeDetector instance"""
        config = RegimeDetectionConfig()
        return RegimeDetector(config)
    
    @pytest.fixture
    def sample_detections(self):
        """Create sample detection results"""
        timestamp = datetime.now()
        
        detection1 = RegimeDetection(
            timestamp=timestamp,
            regime_type=RegimeType.BULL_MARKET,
            confidence=0.8,
            method=DetectionMethod.MARKOV_SWITCHING,
            avg_return=0.02,
            volatility=0.15,
            features={'rsi': 65.0, 'momentum': 0.05},
            model_output={'probabilities': [0.8, 0.15, 0.05]}
        )
        
        detection2 = RegimeDetection(
            timestamp=timestamp,
            regime_type=RegimeType.BULL_MARKET,
            confidence=0.75,
            method=DetectionMethod.VOLATILITY_BASED,
            avg_return=0.018,
            volatility=0.14,
            features={'rsi': 68.0, 'momentum': 0.04},
            model_output={'volatility_regime': 'normal'}
        )
        
        detection3 = RegimeDetection(
            timestamp=timestamp,
            regime_type=RegimeType.HIGH_VOLATILITY,
            confidence=0.6,
            method=DetectionMethod.THRESHOLD_BASED,
            avg_return=0.01,
            volatility=0.25,
            features={'rsi': 55.0},
            model_output={'threshold_breach': True}
        )
        
        return [detection1, detection2, detection3]
    
    def test_combine_detections_single(self, detector, sample_detections):
        """Test combining single detection"""
        timestamp = datetime.now()
        combined = detector._combine_detections([sample_detections[0]], timestamp)
        
        assert isinstance(combined, RegimeDetection)
        assert combined.regime_type == RegimeType.BULL_MARKET
        assert combined.confidence == 0.8
    
    def test_combine_detections_multiple_same_regime(self, detector, sample_detections):
        """Test combining multiple detections with same regime"""
        timestamp = datetime.now()
        # Use first two which both have BULL_MARKET
        combined = detector._combine_detections(sample_detections[:2], timestamp)
        
        assert isinstance(combined, RegimeDetection)
        assert combined.regime_type == RegimeType.BULL_MARKET
        assert combined.method == DetectionMethod.MACHINE_LEARNING  # Indicates ensemble
        assert 'ensemble_votes' in combined.model_output
        assert 'individual_detections' in combined.model_output
        assert combined.model_output['individual_detections'] == 2
    
    def test_combine_detections_multiple_different_regimes(self, detector, sample_detections):
        """Test combining multiple detections with different regimes"""
        timestamp = datetime.now()
        combined = detector._combine_detections(sample_detections, timestamp)
        
        assert isinstance(combined, RegimeDetection)
        # Should select regime with highest weighted vote (BULL_MARKET: 0.8+0.75 vs HIGH_VOLATILITY: 0.6)
        assert combined.regime_type == RegimeType.BULL_MARKET
        assert combined.method == DetectionMethod.MACHINE_LEARNING
        
        # Check ensemble information
        assert 'ensemble_votes' in combined.model_output
        assert 'agreement_score' in combined.model_output
        assert combined.model_output['individual_detections'] == 3
    
    def test_combine_detections_feature_aggregation(self, detector, sample_detections):
        """Test that features are properly aggregated"""
        timestamp = datetime.now()
        combined = detector._combine_detections(sample_detections[:2], timestamp)
        
        # Features should be weighted averages
        assert 'rsi' in combined.features
        assert 'momentum' in combined.features
    
    def test_combine_detections_error_handling(self, detector):
        """Test error handling in combine_detections"""
        timestamp = datetime.now()
        
        # Empty detections list
        empty_combined = detector._combine_detections([], timestamp)
        assert isinstance(empty_combined, RegimeDetection)
        
        # Invalid detection (should fallback to first)
        invalid_detection = RegimeDetection(timestamp=timestamp)
        combined = detector._combine_detections([invalid_detection], timestamp)
        assert isinstance(combined, RegimeDetection)


class TestCreateTransition:
    """Test _create_transition method"""
    
    @pytest.fixture
    def detector(self):
        """Create RegimeDetector instance"""
        config = RegimeDetectionConfig()
        return RegimeDetector(config)
    
    @pytest.fixture
    def sample_detections(self):
        """Create sample detections for transition"""
        timestamp = datetime.now()
        
        from_detection = RegimeDetection(
            timestamp=timestamp - timedelta(days=1),
            regime_type=RegimeType.BULL_MARKET,
            confidence=0.7,
            volatility=0.15
        )
        
        to_detection = RegimeDetection(
            timestamp=timestamp,
            regime_type=RegimeType.HIGH_VOLATILITY,
            confidence=0.9,
            volatility=0.30
        )
        
        return from_detection, to_detection
    
    def test_create_transition_normal(self, detector, sample_detections):
        """Test creating normal transition"""
        from_detection, to_detection = sample_detections
        
        transition = detector._create_transition(from_detection, to_detection)
        
        assert isinstance(transition, RegimeTransition)
        assert transition.from_regime == RegimeType.BULL_MARKET
        assert transition.to_regime == RegimeType.HIGH_VOLATILITY
        assert transition.transition_volatility == abs(0.30 - 0.15)
    
    def test_create_transition_fast_speed(self, detector):
        """Test transition with fast speed (large confidence change)"""
        timestamp = datetime.now()
        
        from_detection = RegimeDetection(
            timestamp=timestamp - timedelta(days=1),
            regime_type=RegimeType.BULL_MARKET,
            confidence=0.5,
            volatility=0.15
        )
        
        to_detection = RegimeDetection(
            timestamp=timestamp,
            regime_type=RegimeType.CRISIS,
            confidence=0.9,  # Large change (>0.3)
            volatility=0.50
        )
        
        transition = detector._create_transition(from_detection, to_detection)
        
        assert transition.transition_speed == "fast"
        # Crisis regime should have high market stress
        assert transition.market_stress > 0.5
    
    def test_create_transition_slow_speed(self, detector):
        """Test transition with slow speed (small confidence change)"""
        timestamp = datetime.now()
        
        from_detection = RegimeDetection(
            timestamp=timestamp - timedelta(days=1),
            regime_type=RegimeType.BULL_MARKET,
            confidence=0.75,
            volatility=0.15
        )
        
        to_detection = RegimeDetection(
            timestamp=timestamp,
            regime_type=RegimeType.BULL_MARKET,  # Same regime
            confidence=0.78,  # Small change (<0.1)
            volatility=0.16
        )
        
        transition = detector._create_transition(from_detection, to_detection)
        
        assert transition.transition_speed == "slow"
    
    def test_create_transition_error_handling(self, detector):
        """Test transition creation error handling"""
        timestamp = datetime.now()
        
        from_detection = RegimeDetection(timestamp=timestamp, regime_type=RegimeType.BULL_MARKET)
        to_detection = RegimeDetection(timestamp=timestamp, regime_type=RegimeType.BEAR_MARKET)
        
        transition = detector._create_transition(from_detection, to_detection)
        
        assert isinstance(transition, RegimeTransition)


class TestHistoryMethods:
    """Test history retrieval methods"""
    
    @pytest.fixture
    def detector_with_history(self):
        """Create detector with populated history"""
        config = RegimeDetectionConfig()
        detector = RegimeDetector(config)
        
        # Add detection history
        base_date = datetime.now() - timedelta(days=60)
        for i in range(20):
            detection = RegimeDetection(
                timestamp=base_date + timedelta(days=i),
                regime_type=RegimeType.BULL_MARKET if i % 2 == 0 else RegimeType.BEAR_MARKET,
                confidence=0.7 + (i % 3) * 0.1
            )
            detector.detection_history.append(detection)
            
            # Add transitions when regime changes
            if i > 0 and detector.detection_history[i].regime_type != detector.detection_history[i-1].regime_type:
                transition = RegimeTransition(
                    from_regime=detector.detection_history[i-1].regime_type,
                    to_regime=detector.detection_history[i].regime_type,
                    transition_date=detection.timestamp
                )
                detector.regime_transitions.append(transition)
        
        return detector
    
    def test_get_regime_history_default(self, detector_with_history):
        """Test get_regime_history with default lookback"""
        history = detector_with_history.get_regime_history()
        
        assert isinstance(history, list)
        assert len(history) <= 20  # Should be filtered by 30 days
        for detection in history:
            assert isinstance(detection, RegimeDetection)
    
    def test_get_regime_history_custom_lookback(self, detector_with_history):
        """Test get_regime_history with custom lookback"""
        history = detector_with_history.get_regime_history(lookback_days=10)
        
        assert isinstance(history, list)
        # Should only include recent detections
        if len(history) > 0:
            cutoff = datetime.now() - timedelta(days=10)
            for detection in history:
                assert detection.timestamp >= cutoff
    
    def test_get_transition_history_default(self, detector_with_history):
        """Test get_transition_history with default lookback"""
        history = detector_with_history.get_transition_history()
        
        assert isinstance(history, list)
        for transition in history:
            assert isinstance(transition, RegimeTransition)
    
    def test_get_transition_history_custom_lookback(self, detector_with_history):
        """Test get_transition_history with custom lookback"""
        history = detector_with_history.get_transition_history(lookback_days=30)
        
        assert isinstance(history, list)
        if len(history) > 0:
            cutoff = datetime.now() - timedelta(days=30)
            for transition in history:
                assert transition.transition_date >= cutoff
    
    def test_get_regime_history_empty(self):
        """Test get_regime_history with no history"""
        config = RegimeDetectionConfig()
        detector = RegimeDetector(config)
        
        history = detector.get_regime_history()
        assert history == []
    
    def test_get_transition_history_empty(self):
        """Test get_transition_history with no transitions"""
        config = RegimeDetectionConfig()
        detector = RegimeDetector(config)
        
        history = detector.get_transition_history()
        assert history == []


class TestRegimeStatistics:
    """Test get_regime_statistics and calculation methods"""
    
    @pytest.fixture
    def detector_with_statistics(self):
        """Create detector with history for statistics"""
        config = RegimeDetectionConfig()
        detector = RegimeDetector(config)
        
        # Add diverse detection history
        base_date = datetime.now() - timedelta(days=100)
        regimes = [RegimeType.BULL_MARKET, RegimeType.BEAR_MARKET, RegimeType.HIGH_VOLATILITY]
        
        for i in range(50):
            detection = RegimeDetection(
                timestamp=base_date + timedelta(days=i),
                regime_type=regimes[i % len(regimes)],
                confidence=0.6 + (i % 5) * 0.05,
                avg_return=0.01 + (i % 3) * 0.005,
                volatility=0.15 + (i % 4) * 0.02
            )
            detector.detection_history.append(detection)
            
            # Add some transitions
            if i > 0 and detector.detection_history[i].regime_type != detector.detection_history[i-1].regime_type:
                transition = RegimeTransition(
                    from_regime=detector.detection_history[i-1].regime_type,
                    to_regime=detector.detection_history[i].regime_type,
                    transition_date=detection.timestamp
                )
                detector.regime_transitions.append(transition)
        
        detector.current_regime = detector.detection_history[-1]
        
        return detector
    
    def test_get_regime_statistics_comprehensive(self, detector_with_statistics):
        """Test comprehensive regime statistics"""
        stats = detector_with_statistics.get_regime_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_detections' in stats
        assert stats['total_detections'] == 50
        assert 'regime_distribution' in stats
        assert 'regime_durations' in stats
        assert 'transition_matrix' in stats
        assert 'regime_performance' in stats
        assert 'current_regime' in stats
        assert 'current_confidence' in stats
        assert 'total_transitions' in stats
    
    def test_get_regime_statistics_empty_history(self):
        """Test statistics with empty history"""
        config = RegimeDetectionConfig()
        detector = RegimeDetector(config)
        
        stats = detector.get_regime_statistics()
        assert stats == {}
    
    def test_calculate_regime_durations(self, detector_with_statistics):
        """Test regime duration calculation"""
        durations = detector_with_statistics._calculate_regime_durations()
        
        assert isinstance(durations, dict)
        # Should have durations for each regime type
        for regime_value in durations.values():
            assert isinstance(regime_value, (int, float))
            assert regime_value >= 0
    
    def test_calculate_transition_matrix(self, detector_with_statistics):
        """Test transition matrix calculation"""
        matrix = detector_with_statistics._calculate_transition_matrix()
        
        assert isinstance(matrix, dict)
        # Each from_regime should have probabilities to to_regimes
        for from_regime, to_regimes in matrix.items():
            assert isinstance(from_regime, str)
            assert isinstance(to_regimes, dict)
            # Probabilities should sum to approximately 1.0
            total_prob = sum(to_regimes.values())
            assert abs(total_prob - 1.0) < 0.01 or total_prob == 0
    
    def test_calculate_regime_performance(self, detector_with_statistics):
        """Test regime performance calculation"""
        performance = detector_with_statistics._calculate_regime_performance()
        
        assert isinstance(performance, dict)
        # Each regime should have performance stats
        for regime, stats in performance.items():
            assert isinstance(regime, str)
            assert isinstance(stats, dict)
            assert 'avg_return' in stats
            assert 'avg_volatility' in stats
            assert 'avg_confidence' in stats
            assert 'return_std' in stats
            assert 'count' in stats


class TestISystemComponentMethods:
    """Test ISystemComponent implementation methods"""
    
    @pytest.fixture
    def detector(self):
        """Create RegimeDetector instance"""
        config = RegimeDetectionConfig()
        return RegimeDetector(config)
    
    @pytest.mark.asyncio
    async def test_initialize(self, detector):
        """Test initialization"""
        result = await detector.initialize()
        
        assert result is True
        assert detector.is_initialized is True
        assert detector.initialization_time is not None
    
    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, detector):
        """Test initialization when already initialized"""
        await detector.initialize()
        result = await detector.initialize()
        
        assert result is True
        assert detector.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_start(self, detector):
        """Test start method"""
        await detector.initialize()
        result = await detector.start()
        
        assert result is True
        assert detector.is_operational is True
    
    @pytest.mark.asyncio
    async def test_start_without_initialization(self, detector):
        """Test start without initialization"""
        result = await detector.start()
        
        # Should fail if not initialized
        assert result is False or detector.is_operational is False
    
    @pytest.mark.asyncio
    async def test_stop(self, detector):
        """Test stop method"""
        await detector.initialize()
        await detector.start()
        
        result = await detector.stop()
        
        assert result is True
        assert detector.is_operational is False
    
    @pytest.mark.asyncio
    async def test_health_check(self, detector):
        """Test health check"""
        await detector.initialize()
        await detector.start()
        
        health = await detector.health_check()
        
        assert isinstance(health, dict)
        assert 'healthy' in health
        assert health['healthy'] is True
        assert 'initialized' in health
        assert 'operational' in health
        assert 'detection_count' in health
        assert 'uptime_seconds' in health
    
    @pytest.mark.asyncio
    async def test_health_check_not_operational(self, detector):
        """Test health check when not operational"""
        await detector.initialize()
        # Don't start
        
        health = await detector.health_check()
        
        assert health['healthy'] is False
        assert health['operational'] is False
    
    def test_get_status(self, detector):
        """Test get_status method"""
        status = detector.get_status()
        
        assert isinstance(status, dict)
        assert 'component_type' in status
        assert status['component_type'] == 'RegimeDetector'
        assert 'component_id' in status
        assert 'initialized' in status
        assert 'operational' in status
        assert 'detection_count' in status
        assert 'history_size' in status

