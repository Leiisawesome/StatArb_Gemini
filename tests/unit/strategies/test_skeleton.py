"""
Unit tests for core_engine/trading/strategies/skeleton/ utilities.

Tests cover all skeleton utility functions used by strategy implementations.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

# Import skeleton utilities
from core_engine.trading.strategies.skeleton import dataframe_utils
from core_engine.trading.strategies.skeleton import signal_type_utils
from core_engine.trading.strategies.skeleton import data_quality_utils
from core_engine.trading.strategies.skeleton import composite_feature_utils
from core_engine.trading.strategies.skeleton import enriched_data_utils
from core_engine.trading.strategies.skeleton import ads_regime_adapter
from core_engine.trading.strategies.skeleton import ads_sms_utils
from core_engine.trading.strategies.skeleton import bar_scanner

# Import required types
from core_engine.type_definitions.strategy import SignalType
from core_engine.alpha.ads_regime_vector import ADSRegimeVector


class TestDataframeUtils:
    """Test dataframe utility functions."""

    def test_safe_iloc_valid_index(self):
        """Test safe_iloc with valid indices."""
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        result = dataframe_utils.safe_iloc(df, 1)
        assert result is not None
        assert result['A'] == 2
        assert result['B'] == 5

    def test_safe_iloc_negative_index(self):
        """Test safe_iloc with negative indices."""
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        result = dataframe_utils.safe_iloc(df, -1)
        assert result is not None
        assert result['A'] == 3
        assert result['B'] == 6

    def test_safe_iloc_out_of_bounds(self):
        """Test safe_iloc with out-of-bounds indices."""
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        logger = Mock()
        result = dataframe_utils.safe_iloc(df, 10, logger=logger)
        assert result is None
        logger.warning.assert_called_once()

    def test_safe_iloc_empty_dataframe(self):
        """Test safe_iloc with empty DataFrame."""
        df = pd.DataFrame()
        result = dataframe_utils.safe_iloc(df, 0)
        assert result is None

    def test_extract_bar_timestamp_from_index(self):
        """Test timestamp extraction from DatetimeIndex."""
        dates = pd.date_range('2023-01-01', periods=3, freq='1H')
        df = pd.DataFrame({'close': [100, 101, 102]}, index=dates)
        ts = dataframe_utils.extract_bar_timestamp(df, 1)
        assert ts == dates[1].to_pydatetime()

    def test_extract_bar_timestamp_from_column(self):
        """Test timestamp extraction from timestamp column."""
        df = pd.DataFrame({
            'close': [100, 101, 102],
            'timestamp': ['2023-01-01T10:00:00', '2023-01-01T11:00:00', '2023-01-01T12:00:00']
        })
        ts = dataframe_utils.extract_bar_timestamp(df, 1)
        expected = datetime(2023, 1, 1, 11, 0, 0)
        assert ts == expected

    def test_extract_bar_timestamp_iso_format(self):
        """Test timestamp extraction with ISO format and Z suffix."""
        df = pd.DataFrame({
            'close': [100, 101, 102],
            'datetime': ['2023-01-01T10:00:00Z', '2023-01-01T11:00:00Z', '2023-01-01T12:00:00Z']
        })
        ts = dataframe_utils.extract_bar_timestamp(df, 1)
        expected = datetime(2023, 1, 1, 11, 0, 0)
        # Handle timezone-aware result
        if ts and ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)
        assert ts == expected

    def test_extract_bar_timestamp_fallback_to_index(self):
        """Test fallback to index when column extraction fails."""
        dates = pd.date_range('2023-01-01', periods=3, freq='1H')
        df = pd.DataFrame({
            'close': [100, 101, 102],
            'timestamp': [None, None, None]
        }, index=dates)
        ts = dataframe_utils.extract_bar_timestamp(df, 1)
        assert ts == dates[1].to_pydatetime()

    def test_extract_bar_timestamp_no_valid_source(self):
        """Test when no valid timestamp source is available."""
        df = pd.DataFrame({
            'close': [100, 101, 102],
            'timestamp': ['invalid', 'also_invalid', 'still_invalid']
        })
        # Set a non-datetime index
        df.index = ['a', 'b', 'c']
        ts = dataframe_utils.extract_bar_timestamp(df, 1)
        assert ts is None


class TestSignalTypeUtils:
    """Test signal type utility functions."""

    def test_is_long_signal(self):
        """Test identification of long signals."""
        assert signal_type_utils.is_long_signal(SignalType.LONG_ENTRY) is True
        assert signal_type_utils.is_long_signal(SignalType.BUY) is True
        assert signal_type_utils.is_long_signal(SignalType.SHORT_ENTRY) is False
        assert signal_type_utils.is_long_signal(SignalType.SELL) is False
        assert signal_type_utils.is_long_signal(SignalType.HOLD) is False

    def test_is_short_signal(self):
        """Test identification of short signals."""
        assert signal_type_utils.is_short_signal(SignalType.SHORT_ENTRY) is True
        assert signal_type_utils.is_short_signal(SignalType.SELL) is True
        assert signal_type_utils.is_short_signal(SignalType.LONG_ENTRY) is False
        assert signal_type_utils.is_short_signal(SignalType.BUY) is False
        assert signal_type_utils.is_short_signal(SignalType.HOLD) is False

    def test_side_from_signal_long(self):
        """Test side extraction for long signals."""
        assert signal_type_utils.side_from_signal(SignalType.LONG_ENTRY) == "BUY"
        assert signal_type_utils.side_from_signal(SignalType.BUY) == "BUY"

    def test_side_from_signal_short(self):
        """Test side extraction for short signals."""
        assert signal_type_utils.side_from_signal(SignalType.SHORT_ENTRY) == "SELL"
        assert signal_type_utils.side_from_signal(SignalType.SELL) == "SELL"

    def test_side_from_signal_unknown(self):
        """Test side extraction for unknown signals."""
        assert signal_type_utils.side_from_signal(SignalType.HOLD) == "UNKNOWN"


class TestDataQualityUtils:
    """Test data quality utility functions."""

    def test_is_ffill_stale_not_stale(self):
        """Test detection of non-stale forward-filled data."""
        series = pd.Series([1.0, 1.0, 1.0, 2.0, 3.0])
        assert data_quality_utils.is_ffill_stale(series) is False

    def test_is_ffill_stale_is_stale(self):
        """Test detection of stale forward-filled data."""
        series = pd.Series([1.0] * 15)  # 15 consecutive same values
        assert data_quality_utils.is_ffill_stale(series, max_stale_bars=10) is True

    def test_is_ffill_stale_with_nan(self):
        """Test detection with NaN values."""
        series = pd.Series([np.nan, np.nan, np.nan])
        assert data_quality_utils.is_ffill_stale(series) is True

    def test_is_ffill_stale_empty_series(self):
        """Test with empty series."""
        series = pd.Series([], dtype=float)
        assert data_quality_utils.is_ffill_stale(series) is False

    def test_is_ffill_stale_single_value(self):
        """Test with single value series."""
        series = pd.Series([1.0])
        assert data_quality_utils.is_ffill_stale(series) is False

    def test_is_ffill_stale_with_logger(self):
        """Test logging when stale data is detected."""
        series = pd.Series([1.0] * 15)
        logger = Mock()
        result = data_quality_utils.is_ffill_stale(series, max_stale_bars=10, logger=logger)
        assert result is True
        logger.warning.assert_called_once()


class TestCompositeFeatureUtils:
    """Test composite feature utility functions."""

    def test_normalize_composite_pct_signed_scale(self):
        """Test normalization of signed scale values."""
        assert composite_feature_utils.normalize_composite_pct(0.5) == 75.0
        assert composite_feature_utils.normalize_composite_pct(-1.0) == 0.0
        assert composite_feature_utils.normalize_composite_pct(1.0) == 100.0
        assert composite_feature_utils.normalize_composite_pct(0.0) == 50.0

    def test_normalize_composite_pct_percent_scale(self):
        """Test normalization of already percent-scale values."""
        assert composite_feature_utils.normalize_composite_pct(25.0) == 25.0
        assert composite_feature_utils.normalize_composite_pct(150.0) == 100.0
        assert composite_feature_utils.normalize_composite_pct(-50.0) == 0.0

    def test_normalize_composite_pct_invalid_input(self):
        """Test normalization with invalid input."""
        assert composite_feature_utils.normalize_composite_pct("invalid") == 0.0

    @pytest.mark.parametrize("short,medium,long,lookback", [
        (5, 10, 20, 30),
        (2, 5, 10, 15),
    ])
    def test_fallback_compute_composite_signals(self, short, medium, long, lookback):
        """Test fallback computation of composite signals."""
        # Create test data with increasing prices
        dates = pd.date_range('2023-01-01', periods=50, freq='1H')
        close_prices = np.linspace(100, 110, 50)  # Upward trend
        df = pd.DataFrame({'close': close_prices}, index=dates)

        params = composite_feature_utils.CompositeFallbackParams(
            short_period=short,
            medium_period=medium,
            long_period=long,
            lookback_period=lookback
        )

        z_score, pct = composite_feature_utils.fallback_compute_composite_signals(
            data=df, idx=40, params=params
        )

        assert z_score is not None
        assert pct is not None
        assert isinstance(z_score, float)
        assert isinstance(pct, float)
        assert 0.0 <= pct <= 100.0

    def test_fallback_compute_composite_signals_insufficient_history(self):
        """Test fallback with insufficient history."""
        df = pd.DataFrame({'close': [100, 101, 102]})
        params = composite_feature_utils.CompositeFallbackParams(5, 10, 20, 30)

        z_score, pct = composite_feature_utils.fallback_compute_composite_signals(
            data=df, idx=2, params=params
        )

        assert z_score is None
        assert pct is None

    def test_fallback_compute_composite_signals_no_close_column(self):
        """Test fallback without close column."""
        df = pd.DataFrame({'open': [100, 101, 102]})
        params = composite_feature_utils.CompositeFallbackParams(5, 10, 20, 30)

        z_score, pct = composite_feature_utils.fallback_compute_composite_signals(
            data=df, idx=10, params=params
        )

        assert z_score is None
        assert pct is None


class TestEnrichedDataUtils:
    """Test enriched data utility functions."""

    def test_resolve_first_present_column(self):
        """Test column resolution."""
        df = pd.DataFrame({'col_b': [1, 2], 'col_a': [3, 4]})
        candidates = ['col_a', 'col_b', 'col_c']

        result = enriched_data_utils.resolve_first_present_column(df, candidates)
        assert result == 'col_a'

    def test_resolve_first_present_column_none_found(self):
        """Test when no candidate columns are present."""
        df = pd.DataFrame({'col_x': [1, 2]})
        candidates = ['col_a', 'col_b']

        result = enriched_data_utils.resolve_first_present_column(df, candidates)
        assert result is None

    def test_resolve_expected_or_mapped_column_present(self):
        """Test resolution when expected column exists."""
        df = pd.DataFrame({'expected': [1, 2]})
        mapping = {'expected': 'mapped'}

        result = enriched_data_utils.resolve_expected_or_mapped_column(
            data=df, expected_name='expected', mapping=mapping
        )
        assert result == 'expected'

    def test_resolve_expected_or_mapped_column_mapped(self):
        """Test resolution using mapping."""
        df = pd.DataFrame({'mapped': [1, 2]})
        mapping = {'expected': 'mapped'}

        result = enriched_data_utils.resolve_expected_or_mapped_column(
            data=df, expected_name='expected', mapping=mapping
        )
        assert result == 'mapped'

    def test_resolve_expected_or_mapped_column_not_found(self):
        """Test resolution when neither expected nor mapped column exists."""
        df = pd.DataFrame({'other': [1, 2]})
        mapping = {'expected': 'mapped'}

        result = enriched_data_utils.resolve_expected_or_mapped_column(
            data=df, expected_name='expected', mapping=mapping
        )
        assert result == 'expected'

    def test_momentum_default_column_mapping(self):
        """Test default momentum column mapping."""
        mapping = enriched_data_utils.momentum_default_column_mapping()
        assert isinstance(mapping, dict)
        assert 'RSI_14' in mapping
        assert 'ADX_14' in mapping
        assert mapping['RSI_14'] == 'rsi'

    def test_extract_momentum_indicator_series_all_present(self):
        """Test extraction when all indicator columns are present."""
        df = pd.DataFrame({
            'adx': [25, 26, 27],
            'volume_ratio': [1.0, 1.1, 0.9],
            'trend_strength': [0.5, 0.6, 0.4]
        })

        bundle = enriched_data_utils.extract_momentum_indicator_series(
            data=df,
            adx_candidates=['adx'],
            volume_ratio_candidates=['volume_ratio'],
            trend_strength_candidates=['trend_strength']
        )

        assert len(bundle.adx) == 3
        assert len(bundle.volume_ratio) == 3
        assert len(bundle.trend_strength) == 3
        assert bundle.adx.iloc[0] == 25.0

    def test_extract_momentum_indicator_series_missing_columns(self):
        """Test extraction when some columns are missing."""
        df = pd.DataFrame({'other': [1, 2, 3]})

        bundle = enriched_data_utils.extract_momentum_indicator_series(
            data=df,
            adx_candidates=['adx'],
            volume_ratio_candidates=['volume_ratio'],
            trend_strength_candidates=['trend_strength'],
            default_adx=20.0,
            default_volume_ratio=1.5,
            default_trend_strength=0.0
        )

        assert (bundle.adx == 20.0).all()
        assert (bundle.volume_ratio == 1.5).all()
        assert (bundle.trend_strength == 0.0).all()

    def test_validate_required_indicator_columns_valid(self):
        """Test validation with all required indicators present."""
        enriched_data = {
            'AAPL': pd.DataFrame({
                'rsi': [50, 51, 52],
                'adx': [25, 26, 27]
            })
        }

        required_indicators = {
            'RSI': ['rsi'],
            'ADX': ['adx']
        }

        # Should not raise
        enriched_data_utils.validate_required_indicator_columns(
            enriched_data, required_indicators=required_indicators
        )

    def test_validate_required_indicator_columns_missing(self):
        """Test validation with missing indicators."""
        enriched_data = {
            'AAPL': pd.DataFrame({
                'rsi': [50, 51, 52]
                # Missing 'adx'
            })
        }

        required_indicators = {
            'RSI': ['rsi'],
            'ADX': ['adx']
        }

        with pytest.raises(ValueError, match="missing required indicators"):
            enriched_data_utils.validate_required_indicator_columns(
                enriched_data, required_indicators=required_indicators
            )

    def test_validate_required_indicator_columns_empty_dataframe(self):
        """Test validation with empty DataFrame."""
        enriched_data = {
            'AAPL': pd.DataFrame()
        }

        required_indicators = {
            'RSI': ['rsi']
        }

        with pytest.raises(ValueError, match="has empty DataFrame"):
            enriched_data_utils.validate_required_indicator_columns(
                enriched_data, required_indicators=required_indicators
            )


class TestADSRegimeAdapter:
    """Test ADS regime adapter functions."""

    def test_ads_regime_vector_cache_initialization(self):
        """Test cache initialization."""
        cache = ads_regime_adapter.ADSRegimeVectorCache()
        assert cache.prev == {}

    def test_get_vector_with_regime_context(self):
        """Test vector retrieval with regime context."""
        cache = ads_regime_adapter.ADSRegimeVectorCache()

        # Mock regime context
        regime_context = Mock()
        regime_context.regime_confidence = 0.8
        regime_context.volatility_regime = 'high_volatility'
        regime_context.trend_regime = 'strong_up'

        def get_context():
            return regime_context

        vector, diag = cache.get_vector(symbol='AAPL', get_regime_context=get_context)

        assert isinstance(vector, ADSRegimeVector)
        assert vector.volatility == 0.8  # high_volatility -> 0.8
        assert vector.trend == 1.0       # strong_up -> 1.0
        assert 'AAPL' in cache.prev

    def test_get_vector_without_regime_context(self):
        """Test vector retrieval without regime context."""
        cache = ads_regime_adapter.ADSRegimeVectorCache()

        def get_context():
            return None

        vector, diag = cache.get_vector(symbol='AAPL', get_regime_context=get_context)

        assert isinstance(vector, ADSRegimeVector)
        assert vector.volatility == 0.5  # default
        assert vector.trend == 0.0       # default
        assert 'used' in diag
        assert 'regime_context_missing' in diag['used']

    def test_get_vector_exception_in_context(self):
        """Test vector retrieval when get_regime_context raises exception."""
        cache = ads_regime_adapter.ADSRegimeVectorCache()

        def get_context():
            raise RuntimeError("Context error")

        vector, diag = cache.get_vector(symbol='AAPL', get_regime_context=get_context)

        assert isinstance(vector, ADSRegimeVector)
        assert 'regime_context_missing' in diag['used']


class TestADSSMSUtils:
    """Test ADS/SMS utility functions."""

    @pytest.mark.parametrize("volatility,expected_label", [
        (0.2, "low_vol"),
        (0.25, "low_vol"),
        (0.35, "normal"),
        (0.65, "normal"),
        (0.75, "high_vol"),
        (0.85, "high_vol"),
        (0.95, "crisis"),
        (1.0, "crisis"),
    ])
    def test_sms_regime_label_from_ads_vector(self, volatility, expected_label):
        """Test SMS label mapping from ADS vector."""
        vector = ADSRegimeVector(
            volatility=volatility,
            trend=0.0,
            liquidity=0.5,
            microstructure=0.5
        )

        label = ads_sms_utils.sms_regime_label_from_ads_vector(vector)
        assert label == expected_label


class TestBarScanner:
    """Test bar scanning utility functions."""

    @pytest.fixture
    def mock_emit_pending(self):
        """Mock emit_pending_at_index function."""
        return Mock(return_value=None)

    @pytest.fixture
    def mock_evaluate(self):
        """Mock evaluate_at_index function."""
        mock_func = AsyncMock(return_value="signal")
        return mock_func

    @pytest.mark.asyncio
    async def test_scan_bars_at_interval_basic(self, mock_emit_pending, mock_evaluate):
        """Test basic bar scanning."""
        result = await bar_scanner.scan_bars_at_interval(
            start_idx=0,
            end_idx=10,
            scan_interval=2,
            emit_pending_at_index=mock_emit_pending,
            evaluate_at_index=mock_evaluate
        )

        assert result.bars_evaluated == 5  # indices 0, 2, 4, 6, 8
        assert len(result.signals) == 5
        assert mock_emit_pending.call_count == 5
        assert mock_evaluate.call_count == 5

    @pytest.mark.asyncio
    async def test_scan_bars_at_interval_with_pending_signals(self, mock_evaluate):
        """Test scanning with pending signals."""
        pending_signals = ["pending_0", None, "pending_4", None, None]

        def emit_pending(idx):
            if idx < len(pending_signals):
                return pending_signals[idx]
            return None

        result = await bar_scanner.scan_bars_at_interval(
            start_idx=0,
            end_idx=5,
            scan_interval=1,
            emit_pending_at_index=emit_pending,
            evaluate_at_index=mock_evaluate
        )

        assert len(result.signals) == 7  # 2 pending + 5 evaluated
        assert "pending_0" in result.signals
        assert "pending_4" in result.signals

    @pytest.mark.asyncio
    async def test_scan_bars_at_interval_no_pending(self, mock_evaluate):
        """Test scanning without pending signal emission."""
        result = await bar_scanner.scan_bars_at_interval(
            start_idx=0,
            end_idx=6,
            scan_interval=2,
            emit_pending_at_index=None,
            evaluate_at_index=mock_evaluate
        )

        assert result.bars_evaluated == 3  # indices 0, 2, 4
        assert len(result.signals) == 3

    @pytest.mark.asyncio
    async def test_scan_bars_at_interval_empty_range(self, mock_emit_pending, mock_evaluate):
        """Test scanning with empty range."""
        result = await bar_scanner.scan_bars_at_interval(
            start_idx=5,
            end_idx=5,
            scan_interval=1,
            emit_pending_at_index=mock_emit_pending,
            evaluate_at_index=mock_evaluate
        )

        assert result.bars_evaluated == 0
        assert len(result.signals) == 0

    @pytest.mark.asyncio
    async def test_scan_bars_at_interval_invalid_interval(self, mock_emit_pending, mock_evaluate):
        """Test scanning with invalid interval."""
        with pytest.raises(ValueError, match="scan_interval must be > 0"):
            await bar_scanner.scan_bars_at_interval(
                start_idx=0,
                end_idx=10,
                scan_interval=0,
                emit_pending_at_index=mock_emit_pending,
                evaluate_at_index=mock_evaluate
            )

    @pytest.mark.asyncio
    async def test_scan_bars_at_interval_no_signals(self, mock_emit_pending):
        """Test scanning when evaluation returns no signals."""
        async def evaluate(idx):
            return None

        result = await bar_scanner.scan_bars_at_interval(
            start_idx=0,
            end_idx=4,
            scan_interval=1,
            emit_pending_at_index=mock_emit_pending,
            evaluate_at_index=evaluate
        )

        assert result.bars_evaluated == 4
        assert len(result.signals) == 0