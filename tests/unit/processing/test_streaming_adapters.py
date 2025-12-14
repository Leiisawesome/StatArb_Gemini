"""
Unit tests for Streaming Adapters.

Tests the StreamingIndicatorAdapter and StreamingFeatureAdapter classes.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock

from core_engine.processing.streaming.adapters import (
    StreamingIndicatorAdapter,
    StreamingFeatureAdapter,
)

class TestStreamingIndicatorAdapter:
    """Test StreamingIndicatorAdapter class."""

    @pytest.fixture
    def mock_indicator_engine(self):
        """Create mock indicator engine."""
        engine = Mock()
        engine.calculate_indicators.return_value = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=5, freq='1min'),
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400],
            'sma_20': [100.5, 101.5, 102.5, 103.5, 104.5],
            'rsi_14': [50.0, 52.0, 48.0, 55.0, 45.0],
            'macd': [0.5, 0.7, 0.3, 0.8, 0.2],
        })
        engine.get_supported_indicators.return_value = ['sma_20', 'rsi_14', 'macd']
        return engine

    @pytest.fixture
    def adapter(self, mock_indicator_engine):
        """Create test adapter instance."""
        return StreamingIndicatorAdapter(mock_indicator_engine)

    def test_initialization(self, mock_indicator_engine):
        """Test adapter initialization."""
        adapter = StreamingIndicatorAdapter(mock_indicator_engine)

        assert adapter._engine == mock_indicator_engine
        assert adapter._indicator_groups is None
        assert adapter._indicator_columns is None
        assert adapter._stats == {
            'compute_calls': 0,
            'avg_compute_ms': 0.0,
        }

    def test_initialization_with_groups(self, mock_indicator_engine):
        """Test adapter initialization with indicator groups."""
        groups = ['trend', 'momentum']
        adapter = StreamingIndicatorAdapter(mock_indicator_engine, groups)

        assert adapter._indicator_groups == groups

    def test_compute_indicators_success(self, adapter, mock_indicator_engine):
        """Test successful indicator computation."""
        buffer = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=5, freq='1min'),
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400],
        })

        result = adapter.compute_indicators(buffer)

        # Should call engine's calculate_indicators
        mock_indicator_engine.calculate_indicators.assert_called_once()

        # Should return dict with last row indicator values
        expected = {
            'sma_20': 104.5,
            'rsi_14': 45.0,
            'macd': 0.2,
        }
        assert result == expected

        # Should update stats
        assert adapter._stats['compute_calls'] == 1
        assert adapter._stats['avg_compute_ms'] > 0

    def test_compute_indicators_empty_buffer(self, adapter, mock_indicator_engine):
        """Test computation with empty buffer."""
        result = adapter.compute_indicators(pd.DataFrame())

        assert result == {}
        mock_indicator_engine.calculate_indicators.assert_not_called()

    def test_compute_indicators_none_buffer(self, adapter, mock_indicator_engine):
        """Test computation with None buffer."""
        result = adapter.compute_indicators(None)

        assert result == {}
        mock_indicator_engine.calculate_indicators.assert_not_called()

    def test_compute_indicators_engine_returns_none(self, adapter, mock_indicator_engine):
        """Test computation when engine returns None."""
        mock_indicator_engine.calculate_indicators.return_value = None

        buffer = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=5, freq='1min'),
            'close': [102, 103, 104, 105, 106],
        })

        result = adapter.compute_indicators(buffer)

        assert result == {}

    def test_compute_indicators_engine_returns_empty(self, adapter, mock_indicator_engine):
        """Test computation when engine returns empty DataFrame."""
        mock_indicator_engine.calculate_indicators.return_value = pd.DataFrame()

        buffer = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=5, freq='1min'),
            'close': [102, 103, 104, 105, 106],
        })

        result = adapter.compute_indicators(buffer)

        assert result == {}

    def test_compute_indicators_with_nan_values(self, adapter, mock_indicator_engine):
        """Test computation filters out NaN and infinite values."""
        mock_indicator_engine.calculate_indicators.return_value = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=3, freq='1min'),
            'close': [102, 103, 104],
            'sma_20': [100.5, np.nan, np.inf],
            'rsi_14': [50.0, 52.0, 48.0],
        })

        buffer = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=3, freq='1min'),
            'close': [102, 103, 104],
        })

        result = adapter.compute_indicators(buffer)

        # Should only include finite values
        expected = {
            'rsi_14': 48.0,
        }
        assert result == expected

    def test_compute_indicators_engine_error(self, adapter, mock_indicator_engine):
        """Test computation when engine raises exception."""
        mock_indicator_engine.calculate_indicators.side_effect = Exception("Engine error")

        buffer = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=5, freq='1min'),
            'close': [102, 103, 104, 105, 106],
        })

        result = adapter.compute_indicators(buffer)

        assert result == {}
        # Stats are not updated on error in compute_indicators
        assert adapter._stats['compute_calls'] == 0

    def test_compute_indicators_batch_success(self, adapter, mock_indicator_engine):
        """Test batch indicator computation."""
        buffer = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=5, freq='1min'),
            'close': [102, 103, 104, 105, 106],
        })

        result = adapter.compute_indicators_batch(buffer, last_n=2)

        mock_indicator_engine.calculate_indicators.assert_called_once()
        assert len(result) == 2
        assert result.iloc[-1]['close'] == 106

    def test_compute_indicators_batch_empty_buffer(self, adapter, mock_indicator_engine):
        """Test batch computation with empty buffer."""
        result = adapter.compute_indicators_batch(pd.DataFrame())

        assert result.empty
        mock_indicator_engine.calculate_indicators.assert_not_called()

    def test_compute_indicators_batch_engine_error(self, adapter, mock_indicator_engine):
        """Test batch computation when engine raises exception."""
        mock_indicator_engine.calculate_indicators.side_effect = Exception("Engine error")

        buffer = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=5, freq='1min'),
            'close': [102, 103, 104, 105, 106],
        })

        result = adapter.compute_indicators_batch(buffer)

        assert result.empty

    def test_get_supported_indicators(self, adapter, mock_indicator_engine):
        """Test getting supported indicators."""
        result = adapter.get_supported_indicators()

        assert result == ['sma_20', 'rsi_14', 'macd']
        mock_indicator_engine.get_supported_indicators.assert_called_once()

    def test_get_stats(self, adapter):
        """Test getting adapter statistics."""
        # Initially empty
        stats = adapter.get_stats()
        assert stats == {
            'compute_calls': 0,
            'avg_compute_ms': 0.0,
        }

        # After some calls
        adapter._stats['compute_calls'] = 5
        adapter._stats['avg_compute_ms'] = 10.5

        stats = adapter.get_stats()
        assert stats == {
            'compute_calls': 5,
            'avg_compute_ms': 10.5,
        }

class TestStreamingFeatureAdapter:
    """Test StreamingFeatureAdapter class."""

    @pytest.fixture
    def mock_feature_engineer(self):
        """Create mock feature engineer."""
        engineer = Mock()
        engineer.load_scalers.return_value = None
        engineer.transform_single.return_value = {
            'feature_1': 1.5,
            'feature_2': -0.8,
            'feature_3': 2.1,
        }
        engineer.get_feature_names.return_value = ['feature_1', 'feature_2', 'feature_3']
        return engineer

    @pytest.fixture
    def adapter(self, mock_feature_engineer):
        """Create test adapter instance."""
        return StreamingFeatureAdapter(mock_feature_engineer)

    def test_initialization(self, mock_feature_engineer):
        """Test adapter initialization."""
        adapter = StreamingFeatureAdapter(mock_feature_engineer)

        assert adapter._engineer == mock_feature_engineer
        assert adapter._scalers_loaded is False
        assert adapter._stats == {
            'transform_calls': 0,
            'avg_transform_ms': 0.0,
            'transform_errors': 0,
        }

    def test_load_scalers_success(self, adapter, mock_feature_engineer):
        """Test successful scaler loading."""
        result = adapter.load_scalers('/path/to/scalers.pkl')

        assert result is True
        assert adapter._scalers_loaded is True
        mock_feature_engineer.load_scalers.assert_called_once_with('/path/to/scalers.pkl')

    def test_load_scalers_failure(self, adapter, mock_feature_engineer):
        """Test scaler loading failure."""
        mock_feature_engineer.load_scalers.side_effect = Exception("Load error")

        result = adapter.load_scalers('/path/to/scalers.pkl')

        assert result is False
        assert adapter._scalers_loaded is False

    def test_transform_single_success(self, adapter, mock_feature_engineer):
        """Test successful single row transformation."""
        adapter._scalers_loaded = True

        row = {'indicator_1': 1.0, 'indicator_2': 2.0}
        result = adapter.transform_single(row)

        expected = {
            'feature_1': 1.5,
            'feature_2': -0.8,
            'feature_3': 2.1,
        }
        assert result == expected

        mock_feature_engineer.transform_single.assert_called_once_with(row)

        # Should update stats
        assert adapter._stats['transform_calls'] == 1
        assert adapter._stats['avg_transform_ms'] > 0

    def test_transform_single_scalers_not_loaded(self, adapter):
        """Test transformation when scalers not loaded."""
        row = {'indicator_1': 1.0, 'indicator_2': 2.0}

        with pytest.raises(RuntimeError, match="Scalers not loaded"):
            adapter.transform_single(row)

    def test_transform_single_engine_error(self, adapter, mock_feature_engineer):
        """Test transformation when engine raises exception."""
        adapter._scalers_loaded = True
        mock_feature_engineer.transform_single.side_effect = Exception("Transform error")

        row = {'indicator_1': 1.0, 'indicator_2': 2.0}
        result = adapter.transform_single(row)

        assert result == {}
        assert adapter._stats['transform_calls'] == 0  # Not incremented on error
        assert adapter._stats['transform_errors'] == 1  # But errors are counted

    def test_transform_single_unsafe_success(self, adapter, mock_feature_engineer):
        """Test unsafe transformation success."""
        row = {'indicator_1': 1.0, 'indicator_2': 2.0}
        result = adapter.transform_single_unsafe(row)

        expected = {
            'feature_1': 1.5,
            'feature_2': -0.8,
            'feature_3': 2.1,
        }
        assert result == expected

    def test_transform_single_unsafe_error(self, adapter, mock_feature_engineer):
        """Test unsafe transformation error."""
        mock_feature_engineer.transform_single.side_effect = Exception("Transform error")

        row = {'indicator_1': 1.0, 'indicator_2': 2.0}
        result = adapter.transform_single_unsafe(row)

        assert result == {}

    def test_are_scalers_loaded(self, adapter):
        """Test checking if scalers are loaded."""
        assert adapter.are_scalers_loaded() is False

        adapter._scalers_loaded = True
        assert adapter.are_scalers_loaded() is True

    def test_get_feature_names(self, adapter, mock_feature_engineer):
        """Test getting feature names."""
        result = adapter.get_feature_names()

        assert result == ['feature_1', 'feature_2', 'feature_3']
        mock_feature_engineer.get_feature_names.assert_called_once()

    def test_get_feature_names_no_method(self, adapter, mock_feature_engineer):
        """Test getting feature names when method doesn't exist."""
        del mock_feature_engineer.get_feature_names  # Remove the method

        result = adapter.get_feature_names()

        assert result == []

    def test_get_stats(self, adapter):
        """Test getting adapter statistics."""
        # Initially empty
        stats = adapter.get_stats()
        assert stats == {
            'transform_calls': 0,
            'avg_transform_ms': 0.0,
            'transform_errors': 0,
        }

        # After some calls
        adapter._stats['transform_calls'] = 10
        adapter._stats['avg_transform_ms'] = 5.5
        adapter._stats['transform_errors'] = 2

        stats = adapter.get_stats()
        assert stats == {
            'transform_calls': 10,
            'avg_transform_ms': 5.5,
            'transform_errors': 2,
        }