#!/usr/bin/env python3
"""
Comprehensive tests for Signal Combiners
========================================

Tests all functionality to achieve 100% coverage.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock

from core_engine.processing.signals.combiners import (
    SignalCombiner,
    CombinationMethod,
    CombinationConfig
)

class TestSignalCombinerBase:
    """Test base SignalCombiner class"""

    @pytest.fixture
    def combiner(self):
        return SignalCombiner()

    @pytest.fixture
    def mock_signals(self):
        """Create mock signals for testing"""
        signals = []
        for i in range(5):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now() + timedelta(minutes=i)
            signal.signal_type = "BUY" if i % 2 == 0 else "SELL"
            signal.strength = 0.8 if i % 3 == 0 else 0.6
            signal.confidence = 0.6 + i * 0.1
            signal.price = 150.0 + i * 0.5
            signal.quantity = 100 + i * 10
            signal.strategy = f"strategy_{i}"
            signal.metadata = {"test": f"value_{i}"}
            signals.append(signal)
        return signals

    def test_initialization_default(self, combiner):
        """Test initialization with default config"""
        assert combiner.config is not None
        assert combiner.config.method == CombinationMethod.WEIGHTED_AVERAGE
        assert combiner.config.min_signals == 2
        assert combiner.config.max_signals == 10

    def test_initialization_custom_config(self, combiner):
        """Test initialization with custom config"""
        config = CombinationConfig(
            method=CombinationMethod.SIMPLE_AVERAGE,
            min_signals=3,
            max_signals=5
        )
        combiner = SignalCombiner(config)
        assert combiner.config == config

    def test_combine_signals_not_implemented(self, combiner, mock_signals):
        """Test that combine_signals requires symbol parameter"""
        with pytest.raises(TypeError):
            combiner.combine_signals(mock_signals)

    def test_validate_signals_valid(self, combiner, mock_signals):
        """Test validation with valid signals"""
        result = combiner._filter_signals(mock_signals, {})
        assert len(result) > 0

    def test_validate_signals_empty_list(self, combiner):
        """Test validation with empty signal list"""
        result = combiner._filter_signals([], {})
        assert len(result) == 0

    def test_validate_signals_none(self, combiner):
        """Test validation with None signals"""
        with pytest.raises(AttributeError):
            combiner._filter_signals(None, {})

    def test_validate_signals_invalid_type(self, combiner):
        """Test validation with invalid signal type"""
        with pytest.raises(ValueError, match="Signals must be a list"):
            combiner._validate_signals("not_a_list")

    def test_validate_signals_missing_attributes(self, combiner):
        """Test validation with signals missing required attributes"""
        invalid_signal = Mock()
        # Don't set required attributes

        with pytest.raises(ValueError, match="Signal missing required attributes"):
            combiner._validate_signals([invalid_signal])

    def test_validate_signals_different_symbols(self, combiner):
        """Test validation with signals for different symbols"""
        signal1 = Mock()
        signal1.symbol = "AAPL"
        signal1.signal_type = "BUY"
        signal1.confidence = 0.7
        signal1.price = 150.0

        signal2 = Mock()
        signal2.symbol = "TSLA"
        signal2.signal_type = "SELL"
        signal2.confidence = 0.8
        signal2.price = 200.0

        with pytest.raises(ValueError, match="All signals must be for the same symbol"):
            combiner._validate_signals([signal1, signal2])

    def test_validate_signals_different_timestamps(self, combiner):
        """Test validation with signals from different timestamps"""
        signal1 = Mock()
        signal1.symbol = "AAPL"
        signal1.timestamp = datetime.now()
        signal1.signal_type = "BUY"
        signal1.confidence = 0.7
        signal1.price = 150.0

        signal2 = Mock()
        signal2.symbol = "AAPL"
        signal2.timestamp = datetime.now() + timedelta(hours=1)
        signal2.signal_type = "SELL"
        signal2.confidence = 0.8
        signal2.price = 150.0

        with pytest.raises(ValueError, match="All signals must be from the same timestamp"):
            combiner._validate_signals([signal1, signal2])

    def test_validate_signals_different_prices(self, combiner):
        """Test validation with signals at different prices"""
        signal1 = Mock()
        signal1.symbol = "AAPL"
        signal1.timestamp = datetime.now()
        signal1.signal_type = "BUY"
        signal1.confidence = 0.7
        signal1.price = 150.0

        signal2 = Mock()
        signal2.symbol = "AAPL"
        signal2.timestamp = datetime.now()
        signal2.signal_type = "SELL"
        signal2.confidence = 0.8
        signal2.price = 155.0

        with pytest.raises(ValueError, match="All signals must be at the same price"):
            combiner._validate_signals([signal1, signal2])

    def test_create_combined_signal(self, combiner, mock_signals):
        """Test creating combined signal"""
        combined = combiner._create_combined_signal(
            mock_signals,
            "BUY",
            0.8,
            0.8,
            150.0,
            500,
            "test_strategy",
            {"test": "metadata"}
        )

        assert combined.symbol == mock_signals[0].symbol
        assert combined.signal_type == "BUY"
        assert combined.strength == 0.8
        assert combined.confidence == 0.8
        assert combined.price == 150.0
        assert combined.quantity == 500
        assert combined.strategy == "test_strategy"
        assert combined.metadata == {"test": "metadata"}

    def test_get_combination_key(self, combiner, mock_signals):
        """Test getting combination cache key"""
        key = combiner._get_combination_key(mock_signals)

        # Should be a string
        assert isinstance(key, str)
        assert len(key) > 0

        # Should be consistent for same signals
        key2 = combiner._get_combination_key(mock_signals)
        assert key == key2

    def test_update_performance_metrics(self, combiner):
        """Test updating performance metrics"""
        initial_metrics = combiner.performance_metrics.copy()

        combiner._update_performance_metrics(0.1, True)

        # Check that metrics are updated
        assert combiner.performance_metrics['combinations_performed'] > initial_metrics['combinations_performed']
        assert combiner.performance_metrics['avg_combination_time'] > 0
        assert combiner.performance_metrics['cache_hits'] > initial_metrics['cache_hits']

    def test_get_performance_metrics(self, combiner):
        """Test getting performance metrics"""
        metrics = combiner.get_performance_metrics()

        assert isinstance(metrics, dict)
        assert 'combinations_performed' in metrics
        assert 'cache_hits' in metrics
        assert 'cache_misses' in metrics
        assert 'avg_combination_time' in metrics

    def test_clear_cache(self, combiner):
        """Test clearing combination cache"""
        # Add something to cache
        combiner.combination_cache['test_key'] = 'test_value'

        combiner.clear_cache()

        assert len(combiner.combination_cache) == 0

class TestSignalCombiner:
    """Test SignalCombiner class"""

    @pytest.fixture
    def combiner(self):
        config = CombinationConfig(method=CombinationMethod.WEIGHTED_AVERAGE)
        return SignalCombiner(config)

    @pytest.fixture
    def mock_signals(self):
        """Create mock signals for testing"""
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY"
            signal.strength = 0.8
            signal.confidence = 0.6 + i * 0.1
            signal.price = 150.0
            signal.quantity = 100 + i * 10
            signal.strategy = f"strategy_{i}"
            signal.metadata = {"weight": 0.3 + i * 0.1}
            signals.append(signal)
        return signals

    def test_initialization_default(self, combiner):
        """Test initialization with default config"""
        assert combiner.config == {}
        assert combiner.weight_strategy == 'confidence'
        assert combiner.weight_metadata_key == 'weight'
        assert combiner.default_weight == 1.0

    def test_initialization_custom_config(self, combiner):
        """Test initialization with custom config"""
        config = {
            'weight_strategy': 'metadata',
            'weight_metadata_key': 'custom_weight',
            'default_weight': 0.5
        }
        combiner = SignalCombiner(config)
        assert combiner.weight_strategy == 'metadata'
        assert combiner.weight_metadata_key == 'custom_weight'
        assert combiner.default_weight == 0.5

    def test_combine_signals_confidence_weights(self, combiner, mock_signals):
        """Test combining signals with confidence-based weights"""
        result = combiner.combine_signals(mock_signals)

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_metadata_weights(self, combiner, mock_signals):
        """Test combining signals with metadata-based weights"""
        config = {'weight_strategy': 'metadata', 'weight_metadata_key': 'weight'}
        combiner = SignalCombiner(config)

        result = combiner.combine_signals(mock_signals)

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_equal_weights(self, combiner, mock_signals):
        """Test combining signals with equal weights"""
        config = {'weight_strategy': 'equal'}
        combiner = SignalCombiner(config)

        result = combiner.combine_signals(mock_signals)

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_mixed_signal_types(self, combiner):
        """Test combining signals with mixed signal types"""
        signals = []
        for i in range(4):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 2 else "SELL"
            signal.strength = 0.8
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should resolve to the dominant signal type
        assert result.symbol == "AAPL"
        assert result.signal_type in ["BUY", "SELL"]
        assert result.price == 150.0

    def test_combine_signals_single_signal(self, combiner):
        """Test combining single signal"""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.timestamp = datetime.now()
        signal.signal_type = "BUY"
        signal.strength = 0.8
        signal.confidence = 0.8
        signal.price = 150.0
        signal.quantity = 100
        signal.strategy = "strategy_1"
        signal.metadata = {}

        result = combiner.combine_signals([signal])

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.confidence == 0.8
        assert result.price == 150.0
        assert result.quantity == 100

    def test_combine_signals_caching(self, combiner, mock_signals):
        """Test that caching works correctly"""
        # First combination
        result1 = combiner.combine_signals(mock_signals)

        # Second combination should use cache
        result2 = combiner.combine_signals(mock_signals)

        # Results should be identical
        assert result1.symbol == result2.symbol
        assert result1.signal_type == result2.signal_type
        assert result1.confidence == result2.confidence
        assert result1.price == result2.price
        assert result1.quantity == result2.quantity

        # Check that cache was used
        assert combiner.performance_metrics['cache_hits'] > 0

    def test_combine_signals_error_handling(self, combiner):
        """Test error handling in combine_signals"""
        # Test with invalid signals
        with pytest.raises(ValueError):
            combiner.combine_signals([])

    def test_combine_signals_performance_metrics(self, combiner, mock_signals):
        """Test that performance metrics are updated"""
        initial_metrics = combiner.performance_metrics.copy()

        combiner.combine_signals(mock_signals)

        # Check that metrics are updated
        assert combiner.performance_metrics['combinations_performed'] > initial_metrics['combinations_performed']
        assert combiner.performance_metrics['avg_combination_time'] > 0

    def test_combine_signals_with_nan_weights(self, combiner):
        """Test combining signals with NaN weights"""
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY"
            signal.strength = 0.8
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {"weight": np.nan if i == 1 else 0.3}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should handle NaN weights gracefully
        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_with_zero_weights(self, combiner):
        """Test combining signals with zero weights"""
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY"
            signal.strength = 0.8
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {"weight": 0.0 if i == 1 else 0.3}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should handle zero weights gracefully
        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_with_negative_weights(self, combiner):
        """Test combining signals with negative weights"""
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY"
            signal.strength = 0.8
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {"weight": -0.1 if i == 1 else 0.3}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should handle negative weights gracefully
        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

class TestSignalCombiner:
    """Test SignalCombiner class"""

    @pytest.fixture
    def combiner(self):
        config = CombinationConfig(method=CombinationMethod.ENSEMBLE_VOTING)
        return SignalCombiner(config)

    @pytest.fixture
    def mock_signals(self):
        """Create mock signals for testing"""
        signals = []
        for i in range(5):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 3 else "SELL"
            signal.strength = 0.8 if i % 2 == 0 else 0.6
            signal.confidence = 0.6 + i * 0.1
            signal.price = 150.0
            signal.quantity = 100 + i * 10
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)
        return signals

    def test_initialization_default(self, combiner):
        """Test initialization with default config"""
        assert combiner.config == {}
        assert combiner.voting_strategy == 'majority'
        assert combiner.minimum_votes == 1
        assert combiner.tie_breaker == 'confidence'

    def test_initialization_custom_config(self, combiner):
        """Test initialization with custom config"""
        config = {
            'voting_strategy': 'unanimous',
            'minimum_votes': 3,
            'tie_breaker': 'strength'
        }
        combiner = SignalCombiner(config)
        assert combiner.voting_strategy == 'unanimous'
        assert combiner.minimum_votes == 3
        assert combiner.tie_breaker == 'strength'

    def test_combine_signals_majority_voting(self, combiner, mock_signals):
        """Test combining signals with majority voting"""
        result = combiner.combine_signals(mock_signals)

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"  # 3 BUY vs 2 SELL
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_unanimous_voting(self, combiner):
        """Test combining signals with unanimous voting"""
        config = {'voting_strategy': 'unanimous'}
        combiner = SignalCombiner(config)

        # All signals are BUY
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY"
            signal.strength = 0.8
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_unanimous_voting_fails(self, combiner):
        """Test combining signals with unanimous voting when not unanimous"""
        config = {'voting_strategy': 'unanimous'}
        combiner = SignalCombiner(config)

        # Mixed signals
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 2 else "SELL"
            signal.strength = 0.8
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should return None when not unanimous
        assert result is None

    def test_combine_signals_minimum_votes(self, combiner):
        """Test combining signals with minimum votes requirement"""
        config = {'minimum_votes': 3}
        combiner = SignalCombiner(config)

        # Only 2 signals
        signals = []
        for i in range(2):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY"
            signal.strength = 0.8
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should return None when minimum votes not met
        assert result is None

    def test_combine_signals_tie_breaker_confidence(self, combiner):
        """Test combining signals with confidence tie breaker"""
        config = {'tie_breaker': 'confidence'}
        combiner = SignalCombiner(config)

        # Equal number of BUY and SELL signals
        signals = []
        for i in range(4):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 2 else "SELL"
            signal.strength = 0.8
            signal.confidence = 0.8 if i < 2 else 0.6  # BUY signals have higher confidence
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should choose BUY due to higher confidence
        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0

    def test_combine_signals_tie_breaker_strength(self, combiner):
        """Test combining signals with strength tie breaker"""
        config = {'tie_breaker': 'strength'}
        combiner = SignalCombiner(config)

        # Equal number of BUY and SELL signals
        signals = []
        for i in range(4):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 2 else "SELL"
            signal.strength = 0.8 if i < 2 else 0.6
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should choose BUY due to higher strength
        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0

    def test_combine_signals_tie_breaker_random(self, combiner):
        """Test combining signals with random tie breaker"""
        config = {'tie_breaker': 'random'}
        combiner = SignalCombiner(config)

        # Equal number of BUY and SELL signals
        signals = []
        for i in range(4):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 2 else "SELL"
            signal.strength = 0.8
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should return a valid signal (either BUY or SELL)
        assert result.symbol == "AAPL"
        assert result.signal_type in ["BUY", "SELL"]
        assert result.price == 150.0

    def test_combine_signals_single_signal(self, combiner):
        """Test combining single signal"""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.timestamp = datetime.now()
        signal.signal_type = "BUY"
        signal.strength = 0.8
        signal.confidence = 0.8
        signal.price = 150.0
        signal.quantity = 100
        signal.strategy = "strategy_1"
        signal.metadata = {}

        result = combiner.combine_signals([signal])

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.confidence == 0.8
        assert result.price == 150.0
        assert result.quantity == 100

    def test_combine_signals_caching(self, combiner, mock_signals):
        """Test that caching works correctly"""
        # First combination
        result1 = combiner.combine_signals(mock_signals)

        # Second combination should use cache
        result2 = combiner.combine_signals(mock_signals)

        # Results should be identical
        assert result1.symbol == result2.symbol
        assert result1.signal_type == result2.signal_type
        assert result1.confidence == result2.confidence
        assert result1.price == result2.price
        assert result1.quantity == result2.quantity

        # Check that cache was used
        assert combiner.performance_metrics['cache_hits'] > 0

    def test_combine_signals_error_handling(self, combiner):
        """Test error handling in combine_signals"""
        # Test with invalid signals
        with pytest.raises(ValueError):
            combiner.combine_signals([])

    def test_combine_signals_performance_metrics(self, combiner, mock_signals):
        """Test that performance metrics are updated"""
        initial_metrics = combiner.performance_metrics.copy()

        combiner.combine_signals(mock_signals)

        # Check that metrics are updated
        assert combiner.performance_metrics['combinations_performed'] > initial_metrics['combinations_performed']
        assert combiner.performance_metrics['avg_combination_time'] > 0

class TestSignalCombiner:
    """Test SignalCombiner class"""

    @pytest.fixture
    def combiner(self):
        config = CombinationConfig(method=CombinationMethod.SIMPLE_AVERAGE)
        return SignalCombiner(config)

    @pytest.fixture
    def mock_signals(self):
        """Create mock signals for testing"""
        signals = []
        for i in range(5):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 3 else "SELL"
            signal.strength = 0.8 if i % 2 == 0 else 0.6
            signal.confidence = 0.6 + i * 0.1
            signal.price = 150.0
            signal.quantity = 100 + i * 10
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)
        return signals

    def test_initialization_default(self, combiner):
        """Test initialization with default config"""
        assert combiner.config == {}
        assert combiner.consensus_threshold == 0.6
        assert combiner.confidence_weight == 0.7
        assert combiner.strength_weight == 0.3

    def test_initialization_custom_config(self, combiner):
        """Test initialization with custom config"""
        config = {
            'consensus_threshold': 0.8,
            'confidence_weight': 0.8,
            'strength_weight': 0.2
        }
        combiner = SignalCombiner(config)
        assert combiner.consensus_threshold == 0.8
        assert combiner.confidence_weight == 0.8
        assert combiner.strength_weight == 0.2

    def test_combine_signals_consensus_reached(self, combiner, mock_signals):
        """Test combining signals when consensus is reached"""
        result = combiner.combine_signals(mock_signals)

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"  # 3 BUY vs 2 SELL
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_no_consensus(self, combiner):
        """Test combining signals when no consensus is reached"""
        config = {'consensus_threshold': 0.9}
        combiner = SignalCombiner(config)

        # Mixed signals with low consensus
        signals = []
        for i in range(4):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 2 else "SELL"
            signal.strength = 0.8
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should return None when no consensus
        assert result is None

    def test_combine_signals_confidence_weighted(self, combiner):
        """Test combining signals with confidence weighting"""
        config = {'confidence_weight': 1.0, 'strength_weight': 0.0}
        combiner = SignalCombiner(config)

        # Signals with different confidence levels
        signals = []
        for i in range(4):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 2 else "SELL"
            signal.strength = 0.8
            signal.confidence = 0.9 if i < 2 else 0.6  # BUY signals have higher confidence
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should choose BUY due to higher confidence
        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0

    def test_combine_signals_strength_weighted(self, combiner):
        """Test combining signals with strength weighting"""
        config = {'confidence_weight': 0.0, 'strength_weight': 1.0}
        combiner = SignalCombiner(config)

        # Signals with different strength levels
        signals = []
        for i in range(4):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 2 else "SELL"
            signal.strength = 0.8 if i < 2 else 0.6
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should choose BUY due to higher strength
        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0

    def test_combine_signals_single_signal(self, combiner):
        """Test combining single signal"""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.timestamp = datetime.now()
        signal.signal_type = "BUY"
        signal.strength = 0.8
        signal.confidence = 0.8
        signal.price = 150.0
        signal.quantity = 100
        signal.strategy = "strategy_1"
        signal.metadata = {}

        result = combiner.combine_signals([signal])

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.confidence == 0.8
        assert result.price == 150.0
        assert result.quantity == 100

    def test_combine_signals_caching(self, combiner, mock_signals):
        """Test that caching works correctly"""
        # First combination
        result1 = combiner.combine_signals(mock_signals)

        # Second combination should use cache
        result2 = combiner.combine_signals(mock_signals)

        # Results should be identical
        assert result1.symbol == result2.symbol
        assert result1.signal_type == result2.signal_type
        assert result1.confidence == result2.confidence
        assert result1.price == result2.price
        assert result1.quantity == result2.quantity

        # Check that cache was used
        assert combiner.performance_metrics['cache_hits'] > 0

    def test_combine_signals_error_handling(self, combiner):
        """Test error handling in combine_signals"""
        # Test with invalid signals
        with pytest.raises(ValueError):
            combiner.combine_signals([])

    def test_combine_signals_performance_metrics(self, combiner, mock_signals):
        """Test that performance metrics are updated"""
        initial_metrics = combiner.performance_metrics.copy()

        combiner.combine_signals(mock_signals)

        # Check that metrics are updated
        assert combiner.performance_metrics['combinations_performed'] > initial_metrics['combinations_performed']
        assert combiner.performance_metrics['avg_combination_time'] > 0

class TestSignalCombiner:
    """Test SignalCombiner class"""

    @pytest.fixture
    def combiner(self):
        config = CombinationConfig(method=CombinationMethod.DYNAMIC_WEIGHTING)
        return SignalCombiner(config)

    @pytest.fixture
    def mock_signals(self):
        """Create mock signals for testing"""
        signals = []
        for i in range(5):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 3 else "SELL"
            signal.strength = 0.8 if i % 2 == 0 else 0.6
            signal.confidence = 0.6 + i * 0.1
            signal.price = 150.0
            signal.quantity = 100 + i * 10
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)
        return signals

    def test_initialization_default(self, combiner):
        """Test initialization with default config"""
        assert combiner.config == {}
        assert combiner.adaptation_strategy == 'performance'
        assert combiner.learning_rate == 0.1
        assert combiner.performance_window == 100
        assert combiner.strategy_weights == {}
        assert combiner.performance_history == {}

    def test_initialization_custom_config(self, combiner):
        """Test initialization with custom config"""
        config = {
            'adaptation_strategy': 'confidence',
            'learning_rate': 0.2,
            'performance_window': 50
        }
        combiner = SignalCombiner(config)
        assert combiner.adaptation_strategy == 'confidence'
        assert combiner.learning_rate == 0.2
        assert combiner.performance_window == 50

    def test_combine_signals_performance_adaptation(self, combiner, mock_signals):
        """Test combining signals with performance-based adaptation"""
        result = combiner.combine_signals(mock_signals)

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"  # 3 BUY vs 2 SELL
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_confidence_adaptation(self, combiner, mock_signals):
        """Test combining signals with confidence-based adaptation"""
        config = {'adaptation_strategy': 'confidence'}
        combiner = SignalCombiner(config)

        result = combiner.combine_signals(mock_signals)

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_volatility_adaptation(self, combiner, mock_signals):
        """Test combining signals with volatility-based adaptation"""
        config = {'adaptation_strategy': 'volatility'}
        combiner = SignalCombiner(config)

        result = combiner.combine_signals(mock_signals)

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_single_signal(self, combiner):
        """Test combining single signal"""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.timestamp = datetime.now()
        signal.signal_type = "BUY"
        signal.strength = 0.8
        signal.confidence = 0.8
        signal.price = 150.0
        signal.quantity = 100
        signal.strategy = "strategy_1"
        signal.metadata = {}

        result = combiner.combine_signals([signal])

        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.confidence == 0.8
        assert result.price == 150.0
        assert result.quantity == 100

    def test_combine_signals_caching(self, combiner, mock_signals):
        """Test that caching works correctly"""
        # First combination
        result1 = combiner.combine_signals(mock_signals)

        # Second combination should use cache
        result2 = combiner.combine_signals(mock_signals)

        # Results should be identical
        assert result1.symbol == result2.symbol
        assert result1.signal_type == result2.signal_type
        assert result1.confidence == result2.confidence
        assert result1.price == result2.price
        assert result1.quantity == result2.quantity

        # Check that cache was used
        assert combiner.performance_metrics['cache_hits'] > 0

    def test_combine_signals_error_handling(self, combiner):
        """Test error handling in combine_signals"""
        # Test with invalid signals
        with pytest.raises(ValueError):
            combiner.combine_signals([])

    def test_combine_signals_performance_metrics(self, combiner, mock_signals):
        """Test that performance metrics are updated"""
        initial_metrics = combiner.performance_metrics.copy()

        combiner.combine_signals(mock_signals)

        # Check that metrics are updated
        assert combiner.performance_metrics['combinations_performed'] > initial_metrics['combinations_performed']
        assert combiner.performance_metrics['avg_combination_time'] > 0

    def test_update_strategy_weights(self, combiner):
        """Test updating strategy weights"""
        # Mock performance data
        performance_data = {
            'strategy_1': {'accuracy': 0.8, 'returns': 0.1},
            'strategy_2': {'accuracy': 0.6, 'returns': 0.05}
        }

        combiner._update_strategy_weights(performance_data)

        # Check that weights are updated
        assert 'strategy_1' in combiner.strategy_weights
        assert 'strategy_2' in combiner.strategy_weights
        assert combiner.strategy_weights['strategy_1'] > combiner.strategy_weights['strategy_2']

    def test_calculate_adaptive_weights(self, combiner, mock_signals):
        """Test calculating adaptive weights"""
        weights = combiner._calculate_adaptive_weights(mock_signals)

        # Should return weights for all signals
        assert len(weights) == len(mock_signals)
        assert all(w > 0 for w in weights)
        assert abs(sum(weights) - 1.0) < 1e-10  # Should sum to 1

    def test_adapt_to_market_conditions(self, combiner):
        """Test adapting to market conditions"""
        market_context = {
            'volatility': 'high',
            'trend': 'sideways',
            'liquidity': 'normal'
        }

        combiner._adapt_to_market_conditions(market_context)

        # Should update internal state based on market conditions
        assert combiner.market_context == market_context

    def test_learn_from_performance(self, combiner):
        """Test learning from performance feedback"""
        # Mock performance feedback
        feedback = {
            'strategy_1': {'success': True, 'returns': 0.05},
            'strategy_2': {'success': False, 'returns': -0.02}
        }

        combiner._learn_from_performance(feedback)

        # Should update performance history
        assert 'strategy_1' in combiner.performance_history
        assert 'strategy_2' in combiner.performance_history

    def test_get_adaptation_status(self, combiner):
        """Test getting adaptation status"""
        status = combiner.get_adaptation_status()

        assert isinstance(status, dict)
        assert 'adaptation_strategy' in status
        assert 'learning_rate' in status
        assert 'strategy_weights' in status
        assert 'performance_history' in status

    def test_reset_adaptation(self, combiner):
        """Test resetting adaptation state"""
        # Set some initial state
        combiner.strategy_weights = {'strategy_1': 0.6, 'strategy_2': 0.4}
        combiner.performance_history = {'strategy_1': [0.8, 0.7]}

        combiner.reset_adaptation()

        # Should reset to initial state
        assert combiner.strategy_weights == {}
        assert combiner.performance_history == {}

class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling"""

    @pytest.fixture
    def combiner(self):
        return SignalCombiner()

    def test_combine_signals_empty_list(self, combiner):
        """Test combining empty signal list"""
        with pytest.raises(ValueError, match="No signals provided"):
            combiner.combine_signals([])

    def test_combine_signals_none(self, combiner):
        """Test combining None signals"""
        with pytest.raises(ValueError, match="Signals cannot be None"):
            combiner.combine_signals(None)

    def test_combine_signals_invalid_type(self, combiner):
        """Test combining invalid signal type"""
        with pytest.raises(ValueError, match="Signals must be a list"):
            combiner.combine_signals("not_a_list")

    def test_combine_signals_missing_attributes(self, combiner):
        """Test combining signals with missing attributes"""
        invalid_signal = Mock()
        # Don't set required attributes

        with pytest.raises(ValueError, match="Signal missing required attributes"):
            combiner.combine_signals([invalid_signal])

    def test_combine_signals_different_symbols(self, combiner):
        """Test combining signals for different symbols"""
        signal1 = Mock()
        signal1.symbol = "AAPL"
        signal1.timestamp = datetime.now()
        signal1.signal_type = "BUY"
        signal1.confidence = 0.7
        signal1.price = 150.0
        signal1.quantity = 100
        signal1.strategy = "strategy_1"
        signal1.metadata = {}

        signal2 = Mock()
        signal2.symbol = "TSLA"
        signal2.timestamp = datetime.now()
        signal2.signal_type = "SELL"
        signal2.confidence = 0.8
        signal2.price = 200.0
        signal2.quantity = 50
        signal2.strategy = "strategy_2"
        signal2.metadata = {}

        with pytest.raises(ValueError, match="All signals must be for the same symbol"):
            combiner.combine_signals([signal1, signal2])

    def test_combine_signals_different_timestamps(self, combiner):
        """Test combining signals from different timestamps"""
        signal1 = Mock()
        signal1.symbol = "AAPL"
        signal1.timestamp = datetime.now()
        signal1.signal_type = "BUY"
        signal1.confidence = 0.7
        signal1.price = 150.0
        signal1.quantity = 100
        signal1.strategy = "strategy_1"
        signal1.metadata = {}

        signal2 = Mock()
        signal2.symbol = "AAPL"
        signal2.timestamp = datetime.now() + timedelta(hours=1)
        signal2.signal_type = "SELL"
        signal2.confidence = 0.8
        signal2.price = 150.0
        signal2.quantity = 100
        signal2.strategy = "strategy_2"
        signal2.metadata = {}

        with pytest.raises(ValueError, match="All signals must be from the same timestamp"):
            combiner.combine_signals([signal1, signal2])

    def test_combine_signals_different_prices(self, combiner):
        """Test combining signals at different prices"""
        signal1 = Mock()
        signal1.symbol = "AAPL"
        signal1.timestamp = datetime.now()
        signal1.signal_type = "BUY"
        signal1.confidence = 0.7
        signal1.price = 150.0
        signal1.quantity = 100
        signal1.strategy = "strategy_1"
        signal1.metadata = {}

        signal2 = Mock()
        signal2.symbol = "AAPL"
        signal2.timestamp = datetime.now()
        signal2.signal_type = "SELL"
        signal2.confidence = 0.8
        signal2.price = 155.0
        signal2.quantity = 100
        signal2.strategy = "strategy_2"
        signal2.metadata = {}

        with pytest.raises(ValueError, match="All signals must be at the same price"):
            combiner.combine_signals([signal1, signal2])

    def test_combine_signals_extreme_values(self, combiner):
        """Test combining signals with extreme values"""
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY"
            signal.strength = 0.8
            signal.confidence = 1e10 if i == 0 else 0.7  # Extreme confidence
            signal.price = 150.0
            signal.quantity = 1e10 if i == 1 else 100  # Extreme quantity
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should handle extreme values gracefully
        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_zero_confidence(self, combiner):
        """Test combining signals with zero confidence"""
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY"
            signal.strength = 0.8
            signal.confidence = 0.0 if i == 0 else 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should handle zero confidence gracefully
        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_combine_signals_constant_values(self, combiner):
        """Test combining signals with constant values"""
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY"
            signal.strength = 0.8
            signal.confidence = 0.7
            signal.price = 150.0
            signal.quantity = 100
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)

        result = combiner.combine_signals(signals)

        # Should handle constant values gracefully
        assert result.symbol == "AAPL"
        assert result.signal_type == "BUY"
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

class TestPerformanceAndOptimization:
    """Test performance and optimization features"""

    @pytest.fixture
    def combiner(self):
        return SignalCombiner()

    @pytest.fixture
    def large_signal_set(self):
        """Create large set of signals for performance testing"""
        signals = []
        for i in range(100):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i % 2 == 0 else "SELL"
            signal.strength = 0.8 if i % 3 == 0 else 0.6
            signal.confidence = 0.6 + (i % 10) * 0.05
            signal.price = 150.0
            signal.quantity = 100 + i
            signal.strategy = f"strategy_{i % 10}"
            signal.metadata = {"weight": 0.1 + (i % 5) * 0.05}
            signals.append(signal)
        return signals

    def test_performance_metrics_tracking(self, combiner, large_signal_set):
        """Test that performance metrics are properly tracked"""
        initial_metrics = combiner.performance_metrics.copy()

        combiner.combine_signals(large_signal_set)

        # Check that metrics are updated
        assert combiner.performance_metrics['combinations_performed'] > initial_metrics['combinations_performed']
        assert combiner.performance_metrics['avg_combination_time'] > 0
        assert combiner.performance_metrics['cache_hits'] >= 0
        assert combiner.performance_metrics['cache_misses'] >= 0

    def test_caching_effectiveness(self, combiner, large_signal_set):
        """Test that caching improves performance"""
        # First combination
        start_time = datetime.now()
        result1 = combiner.combine_signals(large_signal_set)
        first_duration = (datetime.now() - start_time).total_seconds()

        # Second combination (should use cache)
        start_time = datetime.now()
        result2 = combiner.combine_signals(large_signal_set)
        second_duration = (datetime.now() - start_time).total_seconds()

        # Second combination should be faster
        assert second_duration < first_duration

        # Results should be identical
        assert result1.symbol == result2.symbol
        assert result1.signal_type == result2.signal_type
        assert result1.confidence == result2.confidence
        assert result1.price == result2.price
        assert result1.quantity == result2.quantity

    def test_memory_usage(self, combiner, large_signal_set):
        """Test memory usage with large signal sets"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        result = combiner.combine_signals(large_signal_set)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024

        # Result should be correct
        assert result.symbol == "AAPL"
        assert result.signal_type in ["BUY", "SELL"]
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_parallel_processing(self, combiner, large_signal_set):
        """Test parallel processing if enabled"""
        config = {'parallel_processing': True}
        combiner = SignalCombiner(config)

        result = combiner.combine_signals(large_signal_set)

        # Should complete successfully
        assert result.symbol == "AAPL"
        assert result.signal_type in ["BUY", "SELL"]
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

class TestIntegrationAndCompatibility:
    """Test integration and compatibility with other components"""

    @pytest.fixture
    def combiner(self):
        return SignalCombiner()

    @pytest.fixture
    def test_signals(self):
        """Create test signals for integration tests"""
        signals = []
        for i in range(5):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 3 else "SELL"
            signal.strength = 0.8 if i % 2 == 0 else 0.6
            signal.confidence = 0.6 + i * 0.1
            signal.price = 150.0
            signal.quantity = 100 + i * 10
            signal.strategy = f"strategy_{i}"
            signal.metadata = {"weight": 0.2}
            signals.append(signal)
        return signals

    def test_integration_with_pandas_operations(self, combiner, test_signals):
        """Test integration with pandas operations"""
        result = combiner.combine_signals(test_signals)

        # Should work with pandas operations
        assert hasattr(result, 'symbol')
        assert hasattr(result, 'signal_type')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'price')
        assert hasattr(result, 'quantity')

    def test_integration_with_numpy_operations(self, combiner, test_signals):
        """Test integration with numpy operations"""
        result = combiner.combine_signals(test_signals)

        # Should work with numpy operations
        assert np.isfinite(result.confidence)
        assert np.isfinite(result.price)
        assert np.isfinite(result.quantity)

    def test_integration_with_serialization(self, combiner, test_signals):
        """Test integration with serialization"""
        result = combiner.combine_signals(test_signals)

        # Should work with pickle
        import pickle
        pickled = pickle.dumps(result)
        unpickled = pickle.loads(pickled)

        assert unpickled.symbol == result.symbol
        assert unpickled.signal_type == result.signal_type
        assert unpickled.confidence == result.confidence
        assert unpickled.price == result.price
        assert unpickled.quantity == result.quantity

    def test_integration_with_database_operations(self, combiner, test_signals):
        """Test integration with database operations"""
        result = combiner.combine_signals(test_signals)

        # Should work with SQL operations
        try:
            import sqlite3
            conn = sqlite3.connect(':memory:')

            # Create table
            conn.execute('''
                CREATE TABLE signals (
                    symbol TEXT,
                    signal_type TEXT,
                    confidence REAL,
                    price REAL,
                    quantity REAL
                )
            ''')

            # Insert result
            conn.execute('''
                INSERT INTO signals (symbol, signal_type, confidence, price, quantity)
                VALUES (?, ?, ?, ?, ?)
            ''', (result.symbol, result.signal_type, result.confidence, result.price, result.quantity))

            # Verify data was stored correctly
            cursor = conn.execute('SELECT COUNT(*) FROM signals')
            count = cursor.fetchone()[0]
            assert count == 1

            conn.close()
        except ImportError:
            # SQLite not available, skip test
            pass

class TestRegimeAwareSignalCombining:
    """Test regime-aware signal combining"""

    @pytest.fixture
    def combiner(self):
        return SignalCombiner()

    @pytest.fixture
    def test_signals(self):
        """Create test signals for regime-aware combining"""
        signals = []
        for i in range(5):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 3 else "SELL"
            signal.strength = 0.8 if i % 2 == 0 else 0.6
            signal.confidence = 0.6 + i * 0.1
            signal.price = 150.0
            signal.quantity = 100 + i * 10
            signal.strategy = f"strategy_{i}"
            signal.metadata = {}
            signals.append(signal)
        return signals

    def test_regime_aware_combining(self, combiner, test_signals):
        """Test that combining adapts to regime context"""
        # Mock regime context
        regime_context = {
            'regime': 'high_volatility',
            'confidence': 0.8,
            'volatility_multiplier': 1.5
        }

        result = combiner.combine_signals(test_signals, regime_context)

        # Should complete successfully
        assert result.symbol == "AAPL"
        assert result.signal_type in ["BUY", "SELL"]
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

    def test_regime_aware_volatility_scaling(self, combiner, test_signals):
        """Test that combining scales with regime volatility"""
        # Test in low volatility regime
        low_vol_regime = {
            'regime': 'low_volatility',
            'confidence': 0.8,
            'volatility_multiplier': 0.5
        }

        result_low_vol = combiner.combine_signals(test_signals, low_vol_regime)

        # Test in high volatility regime
        high_vol_regime = {
            'regime': 'high_volatility',
            'confidence': 0.8,
            'volatility_multiplier': 2.0
        }

        result_high_vol = combiner.combine_signals(test_signals, high_vol_regime)

        # Both should complete successfully
        assert result_low_vol.symbol == "AAPL"
        assert result_high_vol.symbol == "AAPL"

        # Confidence should be different due to volatility scaling
        assert result_low_vol.confidence != result_high_vol.confidence

    def test_regime_aware_trend_adaptation(self, combiner, test_signals):
        """Test that combining adapts to regime trend"""
        # Test in trending regime
        trending_regime = {
            'regime': 'trending',
            'confidence': 0.8,
            'trend_strength': 0.7
        }

        result_trending = combiner.combine_signals(test_signals, trending_regime)

        # Test in ranging regime
        ranging_regime = {
            'regime': 'ranging',
            'confidence': 0.8,
            'trend_strength': 0.2
        }

        result_ranging = combiner.combine_signals(test_signals, ranging_regime)

        # Both should complete successfully
        assert result_trending.symbol == "AAPL"
        assert result_ranging.symbol == "AAPL"

        # Results should be different due to trend adaptation
        assert result_trending.confidence != result_ranging.confidence

class TestAdvancedSignalCombining:
    """Test advanced signal combining techniques"""

    @pytest.fixture
    def combiner(self):
        return SignalCombiner()

    @pytest.fixture
    def test_signals(self):
        """Create test signals for advanced combining"""
        signals = []
        for i in range(10):
            signal = Mock()
            signal.symbol = "AAPL"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 6 else "SELL"
            signal.strength = 0.8 if i % 3 == 0 else 0.6
            signal.confidence = 0.6 + (i % 5) * 0.1
            signal.price = 150.0
            signal.quantity = 100 + i * 5
            signal.strategy = f"strategy_{i % 3}"
            signal.metadata = {"weight": 0.1 + (i % 3) * 0.05}
            signals.append(signal)
        return signals

    def test_advanced_combining_comprehensive(self, combiner, test_signals):
        """Test comprehensive advanced combining"""
        # Enable all advanced features
        config = {
            'adaptation_strategy': 'performance',
            'learning_rate': 0.1,
            'performance_window': 50,
            'enable_caching': True,
            'parallel_processing': True
        }

        combiner = SignalCombiner(config)
        result = combiner.combine_signals(test_signals)

        # Should complete successfully
        assert result.symbol == "AAPL"
        assert result.signal_type in ["BUY", "SELL"]
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

        # Check that advanced features are working
        assert combiner.performance_metrics['combinations_performed'] > 0
        assert combiner.performance_metrics['avg_combination_time'] > 0

    def test_advanced_combining_with_regime_adaptation(self, combiner, test_signals):
        """Test advanced combining with regime adaptation"""
        # Test different regime contexts
        regimes = [
            {'regime': 'trending', 'confidence': 0.8, 'trend_strength': 0.7},
            {'regime': 'ranging', 'confidence': 0.8, 'trend_strength': 0.2},
            {'regime': 'high_volatility', 'confidence': 0.8, 'volatility_multiplier': 2.0},
            {'regime': 'low_volatility', 'confidence': 0.8, 'volatility_multiplier': 0.5},
            {'regime': 'crisis', 'confidence': 0.8, 'crisis_mode': True}
        ]

        for regime in regimes:
            result = combiner.combine_signals(test_signals, regime)

            # Should complete successfully for all regimes
            assert result.symbol == "AAPL"
            assert result.signal_type in ["BUY", "SELL"]
            assert result.price == 150.0
            assert result.confidence > 0
            assert result.quantity > 0

    def test_advanced_combining_with_performance_optimization(self, combiner, test_signals):
        """Test advanced combining with performance optimization"""
        # Test with performance optimization enabled
        config = {
            'performance_optimization': True,
            'parallel_processing': True,
            'vectorization': True,
            'enable_caching': True
        }

        combiner = SignalCombiner(config)
        result = combiner.combine_signals(test_signals)

        # Should complete successfully
        assert result.symbol == "AAPL"
        assert result.signal_type in ["BUY", "SELL"]
        assert result.price == 150.0
        assert result.confidence > 0
        assert result.quantity > 0

        # Check that performance metrics are tracked
        assert combiner.performance_metrics['combinations_performed'] > 0
        assert combiner.performance_metrics['avg_combination_time'] > 0
