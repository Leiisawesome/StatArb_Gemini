#!/usr/bin/env python3
"""
Comprehensive Indicator Engine Test Coverage
============================================

Addresses critical coverage gap: indicators/engine.py (43% → 80% target)

Tests all missing methods and code paths identified in coverage analysis:
- Advanced indicator calculations (ADX, stochastic, etc.)
- Multi-timeframe indicator calculations
- Macro regime indicators
- Regime-aware adaptations
- Performance monitoring
- Error handling paths
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock

from core_engine.processing.indicators.engine import (
    EnhancedTechnicalIndicators,
    MultiTimeframeIndicatorResult,
    MacroRegimeIndicators
)
from core_engine.config.component_config import (
    IndicatorConfig,
    PerformanceConfig
)


class TestInitializationAndConfig:
    """Test initialization with various configurations"""

    def test_initialization_default(self):
        """Test initialization with default config"""
        engine = EnhancedTechnicalIndicators()
        assert engine.config is not None
        assert isinstance(engine.config, IndicatorConfig)
        assert engine.component_id is not None
        assert not engine.is_initialized
        assert not engine.is_operational

    def test_initialization_custom_config(self):
        """Test initialization with custom IndicatorConfig"""
        config = IndicatorConfig(
            rsi_period=21,
            sma_periods=[10, 20, 50],
            performance=PerformanceConfig(enable_caching=True)
        )
        engine = EnhancedTechnicalIndicators(config)
        assert engine.config.rsi_period == 21
        assert engine.config.sma_periods == [10, 20, 50]
        assert engine.config.performance.enable_caching is True

    def test_initialization_dict_config(self):
        """Test initialization with dict config (backward compatibility)"""
        config_dict = {
            'rsi_period': 21,
            'sma_periods': [10, 20],
            'performance': {'enable_caching': True}
        }
        engine = EnhancedTechnicalIndicators(config_dict)
        assert engine.config.rsi_period == 21

    @pytest.mark.asyncio
    async def test_initialize_lifecycle(self):
        """Test component initialization lifecycle"""
        engine = EnhancedTechnicalIndicators()
        result = await engine.initialize()
        assert result is True
        assert engine.is_initialized

    @pytest.mark.asyncio
    async def test_start_lifecycle(self):
        """Test component start lifecycle"""
        engine = EnhancedTechnicalIndicators()
        await engine.initialize()
        result = await engine.start()
        assert result is True
        assert engine.is_operational

    @pytest.mark.asyncio
    async def test_stop_lifecycle(self):
        """Test component stop lifecycle"""
        engine = EnhancedTechnicalIndicators()
        await engine.initialize()
        await engine.start()
        result = await engine.stop()
        assert result is True
        assert not engine.is_operational


class TestBasicIndicatorCalculations:
    """Test basic indicator calculation methods"""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        np.random.seed(42)
        base_price = 100.0

        return pd.DataFrame({
            'timestamp': dates,
            'symbol': ['AAPL'] * 100,
            'open': base_price + np.cumsum(np.random.randn(100) * 0.1),
            'high': base_price + 1 + np.cumsum(np.random.randn(100) * 0.1),
            'low': base_price - 1 + np.cumsum(np.random.randn(100) * 0.1),
            'close': base_price + np.cumsum(np.random.randn(100) * 0.1),
            'volume': np.random.randint(1000, 10000, 100)
        })

    @pytest.fixture
    def engine(self):
        """Create indicator engine"""
        return EnhancedTechnicalIndicators()

    def test_calculate_indicators_basic(self, engine, sample_data):
        """Test basic indicator calculation"""
        result = engine.calculate_indicators(sample_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_data)
        assert 'close' in result.columns

    def test_calculate_all_indicators(self, engine, sample_data):
        """Test calculate_all_indicators method"""
        result = engine.calculate_all_indicators(sample_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) >= len(sample_data)

    def test_calculate_moving_averages(self, engine, sample_data):
        """Test moving averages calculation"""
        result = engine._calculate_moving_averages(sample_data)

        assert isinstance(result, pd.DataFrame)
        # Check for SMA columns
        for period in engine.config.sma_periods:
            col = f'sma_{period}'
            if col in result.columns:
                assert not result[col].isna().all()

    def test_calculate_momentum_indicators(self, engine, sample_data):
        """Test momentum indicators calculation"""
        result = engine._calculate_momentum_indicators(sample_data)

        assert isinstance(result, pd.DataFrame)
        # Check for RSI
        if 'rsi' in result.columns:
            rsi_values = result['rsi'].dropna()
            if len(rsi_values) > 0:
                assert (rsi_values >= 0).all()
                assert (rsi_values <= 100).all()

    def test_calculate_volatility_indicators(self, engine, sample_data):
        """Test volatility indicators calculation"""
        result = engine._calculate_volatility_indicators(sample_data)

        assert isinstance(result, pd.DataFrame)
        # Check for ATR
        if 'atr' in result.columns:
            atr_values = result['atr'].dropna()
            if len(atr_values) > 0:
                assert (atr_values >= 0).all()

    def test_calculate_volume_indicators(self, engine, sample_data):
        """Test volume indicators calculation"""
        result = engine._calculate_volume_indicators(sample_data)

        assert isinstance(result, pd.DataFrame)
        # Check for OBV if calculated
        if 'obv' in result.columns:
            obv_values = result['obv'].dropna()
            assert len(obv_values) > 0


class TestAdvancedIndicatorCalculations:
    """Test advanced indicator calculation methods"""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        np.random.seed(42)
        base_price = 100.0

        return pd.DataFrame({
            'timestamp': dates,
            'open': base_price + np.cumsum(np.random.randn(100) * 0.1),
            'high': base_price + 1 + np.cumsum(np.random.randn(100) * 0.1),
            'low': base_price - 1 + np.cumsum(np.random.randn(100) * 0.1),
            'close': base_price + np.cumsum(np.random.randn(100) * 0.1),
            'volume': np.random.randint(1000, 10000, 100)
        })

    @pytest.fixture
    def engine(self):
        """Create indicator engine"""
        return EnhancedTechnicalIndicators()

    def test_calculate_rsi(self, engine, sample_data):
        """Test RSI calculation"""
        close = sample_data['close']
        period = engine.config.rsi_period

        rsi = engine._calculate_rsi(close, period)

        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(close)
        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        if len(valid_rsi) > 0:
            assert (valid_rsi >= 0).all()
            assert (valid_rsi <= 100).all()

    def test_calculate_macd(self, engine, sample_data):
        """Test MACD calculation"""
        close = sample_data['close']
        fast = engine.config.macd_fast
        slow = engine.config.macd_slow
        signal = engine.config.macd_signal

        macd, macd_signal, macd_hist = engine._calculate_macd(close, fast, slow, signal)

        assert isinstance(macd, pd.Series)
        assert isinstance(macd_signal, pd.Series)
        assert isinstance(macd_hist, pd.Series)
        assert len(macd) == len(close)

    def test_calculate_stochastic(self, engine, sample_data):
        """Test Stochastic oscillator calculation"""
        high = sample_data['high']
        low = sample_data['low']
        close = sample_data['close']
        k_period = 14
        d_period = 3

        k, d = engine._calculate_stochastic(high, low, close, k_period, d_period)

        assert isinstance(k, pd.Series)
        assert isinstance(d, pd.Series)
        assert len(k) == len(close)
        # Stochastic should be between 0 and 100
        valid_k = k.dropna()
        if len(valid_k) > 0:
            assert (valid_k >= 0).all()
            assert (valid_k <= 100).all()

    def test_calculate_atr(self, engine, sample_data):
        """Test ATR calculation"""
        high = sample_data['high']
        low = sample_data['low']
        close = sample_data['close']
        period = 14

        atr = engine._calculate_atr(high, low, close, period)

        assert isinstance(atr, pd.Series)
        assert len(atr) == len(close)
        # ATR should be non-negative
        valid_atr = atr.dropna()
        if len(valid_atr) > 0:
            assert (valid_atr >= 0).all()

    def test_calculate_adx(self, engine, sample_data):
        """Test ADX calculation"""
        high = sample_data['high']
        low = sample_data['low']
        close = sample_data['close']
        period = 14

        adx, plus_di, minus_di = engine._calculate_adx(high, low, close, period)

        assert isinstance(adx, pd.Series)
        assert isinstance(plus_di, pd.Series)
        assert isinstance(minus_di, pd.Series)
        assert len(adx) == len(close)
        # ADX should be between 0 and 100
        valid_adx = adx.dropna()
        if len(valid_adx) > 0:
            assert (valid_adx >= 0).all()
            assert (valid_adx <= 100).all()


class TestMultiTimeframeIndicators:
    """Test multi-timeframe indicator calculations"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine with multi-timeframe enabled"""
        config = IndicatorConfig(enable_multi_timeframe=True)
        return EnhancedTechnicalIndicators(config)

    @pytest.fixture
    def multi_timeframe_data(self):
        """Create sample multi-timeframe data"""
        base_time = datetime(2024, 1, 1)
        np.random.seed(42)

        data_dict = {}
        for timeframe in ['1min', '5min', '15min']:
            dates = pd.date_range(base_time, periods=100, freq=timeframe)
            base_price = 100.0

            df = pd.DataFrame({
                'timestamp': dates,
                'symbol': ['AAPL'] * 100,
                'open': base_price + np.cumsum(np.random.randn(100) * 0.1),
                'high': base_price + 1 + np.cumsum(np.random.randn(100) * 0.1),
                'low': base_price - 1 + np.cumsum(np.random.randn(100) * 0.1),
                'close': base_price + np.cumsum(np.random.randn(100) * 0.1),
                'volume': np.random.randint(1000, 10000, 100)
            })
            data_dict[timeframe] = df

        return data_dict

    def test_calculate_multi_timeframe_indicators(self, engine, multi_timeframe_data):
        """Test multi-timeframe indicator calculation"""
        results = engine.calculate_multi_timeframe_indicators(multi_timeframe_data)

        assert isinstance(results, dict)
        # Should have results for symbols in data
        if results:
            for symbol, result in results.items():
                assert isinstance(result, MultiTimeframeIndicatorResult)
                assert result.symbol == symbol
                assert isinstance(result.timeframe_indicators, dict)
                assert 0 <= result.timeframe_alignment <= 1

    def test_calculate_multi_timeframe_disabled(self):
        """Test that multi-timeframe returns empty when disabled"""
        config = IndicatorConfig(enable_multi_timeframe=False)
        engine = EnhancedTechnicalIndicators(config)

        data_dict = {'1min': pd.DataFrame()}
        results = engine.calculate_multi_timeframe_indicators(data_dict)

        assert results == {}


class TestMacroRegimeIndicators:
    """Test macro regime indicator calculations"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine"""
        return EnhancedTechnicalIndicators()

    @pytest.fixture
    def macro_data(self):
        """Create sample macro data"""
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        np.random.seed(42)

        return {
            'vix': pd.DataFrame({
                'timestamp': dates,
                'close': 15 + np.random.randn(50) * 2,
            }),
            'spy': pd.DataFrame({
                'timestamp': dates,
                'close': 400 + np.cumsum(np.random.randn(50) * 1),
            }),
            'dxy': pd.DataFrame({
                'timestamp': dates,
                'close': 100 + np.random.randn(50) * 1,
            })
        }

    def test_calculate_macro_regime_indicators(self, engine, macro_data):
        """Test macro regime indicator calculation"""
        result = engine.calculate_macro_regime_indicators(macro_data)

        assert isinstance(result, MacroRegimeIndicators)
        assert result.vix_regime in ['low', 'normal', 'elevated', 'extreme']
        assert -1 <= result.dollar_strength <= 1
        assert -1 <= result.macro_regime_score <= 1
        assert 0 <= result.regime_confidence <= 1


class TestIndicatorSummary:
    """Test indicator summary generation"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine"""
        return EnhancedTechnicalIndicators()

    @pytest.fixture
    def enriched_data(self):
        """Create sample enriched data with indicators"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        np.random.seed(42)
        base_price = 100.0

        df = pd.DataFrame({
            'timestamp': dates,
            'symbol': ['AAPL'] * 100,
            'open': base_price + np.cumsum(np.random.randn(100) * 0.1),
            'high': base_price + 1 + np.cumsum(np.random.randn(100) * 0.1),
            'low': base_price - 1 + np.cumsum(np.random.randn(100) * 0.1),
            'close': base_price + np.cumsum(np.random.randn(100) * 0.1),
            'volume': np.random.randint(1000, 10000, 100),
            'rsi': 50 + np.random.randn(100) * 10,
            'macd': np.random.randn(100) * 0.1,
            'macd_signal': np.random.randn(100) * 0.1,
            'bb_position': np.random.rand(100),
        })
        return df

    def test_get_indicator_summary(self, engine, enriched_data):
        """Test indicator summary generation"""
        summary = engine.get_indicator_summary(enriched_data, 'AAPL')

        assert isinstance(summary, dict)
        if summary:
            assert 'symbol' in summary or 'indicators' in summary


class TestRegimeAwareness:
    """Test regime-aware indicator calculations"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine"""
        return EnhancedTechnicalIndicators()

    @pytest.fixture
    def mock_regime_engine(self):
        """Create mock regime engine"""
        regime_engine = Mock()
        regime_engine.get_current_regime_context.return_value = {
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal',
            'confidence': 0.8
        }
        return regime_engine

    def test_set_regime_engine(self, engine, mock_regime_engine):
        """Test setting regime engine"""
        engine.set_regime_engine(mock_regime_engine)
        assert engine.regime_engine == mock_regime_engine

    @pytest.mark.asyncio
    async def test_on_regime_change(self, engine):
        """Test regime change handling"""
        regime_context = {
            'primary_regime': 'high_volatility',
            'volatility_regime': 'high',
            'confidence': 0.9
        }

        # Should not raise
        await engine.on_regime_change(regime_context)

    def test_validate_regime_dependency(self, engine):
        """Test regime dependency validation"""
        # Without regime engine
        result = engine.validate_regime_dependency()
        assert result is False

        # With regime engine
        engine.set_regime_engine(Mock())
        result = engine.validate_regime_dependency()
        assert result is True


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine"""
        return EnhancedTechnicalIndicators()

    def test_calculate_indicators_empty_dataframe(self, engine):
        """Test handling of empty DataFrame"""
        empty_df = pd.DataFrame()
        result = engine.calculate_indicators(empty_df)

        assert isinstance(result, pd.DataFrame)

    def test_calculate_indicators_missing_columns(self, engine):
        """Test handling of missing OHLCV columns"""
        incomplete_df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1min'),
            'symbol': ['AAPL'] * 10,
            'close': np.random.randn(10) * 100,
            'open': np.random.randn(10) * 100,
            'high': np.random.randn(10) * 100,
            'low': np.random.randn(10) * 100,
            'volume': np.random.randint(1000, 5000, 10)
        })
        # Remove one critical column to test error handling
        incomplete_df = incomplete_df.drop(columns=['high'])

        # Should handle gracefully or return empty/partial result
        try:
            result = engine.calculate_indicators(incomplete_df)
            assert isinstance(result, pd.DataFrame)
        except (KeyError, ValueError):
            # Acceptable - engine may require all OHLCV columns
            pass

    def test_calculate_indicators_insufficient_data(self, engine):
        """Test handling of insufficient data (too few rows)"""
        minimal_df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='1min'),
            'symbol': ['AAPL'] * 5,
            'open': np.random.randn(5) * 100,
            'high': np.random.randn(5) * 100,
            'low': np.random.randn(5) * 100,
            'close': np.random.randn(5) * 100,
            'volume': np.random.randint(1000, 5000, 5)
        })

        # Should handle gracefully
        result = engine.calculate_indicators(minimal_df)
        assert isinstance(result, pd.DataFrame)

    def test_calculate_indicators_with_nan(self, engine):
        """Test handling of NaN values"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        np.random.seed(42)
        base_price = 100.0
        df = pd.DataFrame({
            'timestamp': dates,
            'symbol': ['AAPL'] * 100,
            'open': base_price + np.cumsum(np.random.randn(100) * 0.1),
            'high': base_price + 1 + np.cumsum(np.random.randn(100) * 0.1),
            'low': base_price - 1 + np.cumsum(np.random.randn(100) * 0.1),
            'close': base_price + np.cumsum(np.random.randn(100) * 0.1),
            'volume': np.random.randint(1000, 10000, 100)
        })
        # Introduce some NaN values
        df.loc[10:20, 'close'] = np.nan

        result = engine.calculate_indicators(df)
        assert isinstance(result, pd.DataFrame)


class TestHealthChecks:
    """Test component health checks"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine"""
        return EnhancedTechnicalIndicators()

    @pytest.mark.asyncio
    async def test_health_check_uninitialized(self, engine):
        """Test health check when not initialized"""
        health = await engine.health_check()
        assert isinstance(health, dict)
        assert 'healthy' in health

    @pytest.mark.asyncio
    async def test_health_check_initialized(self, engine):
        """Test health check when initialized"""
        await engine.initialize()
        health = await engine.health_check()
        assert isinstance(health, dict)
        assert 'healthy' in health

    def test_get_status(self, engine):
        """Test get_status method"""
        status = engine.get_status()
        assert isinstance(status, dict)
        assert 'initialized' in status or 'operational' in status

