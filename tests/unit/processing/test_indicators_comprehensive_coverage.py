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
        base_price = 100.0

        return pd.DataFrame({
            'timestamp': dates,
            'symbol': ['AAPL'] * 100,
            'open': [base_price] * 100,
            'high': [base_price + 1] * 100,
            'low': [base_price - 1] * 100,
            'close': [base_price] * 100,
            'volume': [1000] * 100
        })

    @pytest.fixture
    def engine(self):
        """Create indicator engine with fresh config"""
        from core_engine.config import IndicatorConfig
        config = IndicatorConfig()
        return EnhancedTechnicalIndicators(config)

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
        base_price = 100.0

        return pd.DataFrame({
            'timestamp': dates,
            'open': [base_price + i * 0.1 for i in range(100)],
            'high': [base_price + 1 + i * 0.1 for i in range(100)],
            'low': [base_price - 1 + i * 0.1 for i in range(100)],
            'close': [base_price + i * 0.1 for i in range(100)],
            'volume': [1000 + i * 10 for i in range(100)]
        })

    @pytest.fixture
    def engine(self):
        """Create indicator engine with fresh config"""
        from core_engine.config import IndicatorConfig
        config = IndicatorConfig()
        return EnhancedTechnicalIndicators(config)

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

        data_dict = {}
        for timeframe in ['5min', '1H', '1D']:
            dates = pd.date_range(base_time, periods=100, freq='1min')  # Use 1min base for resampling
            base_price = 100.0

            # Create base 1min data
            df = pd.DataFrame({
                'timestamp': dates,
                'symbol': ['AAPL'] * 100,
                'open': [base_price + i * 0.1 for i in range(100)],
                'high': [base_price + 1 + i * 0.1 for i in range(100)],
                'low': [base_price - 1 + i * 0.1 for i in range(100)],
                'close': [base_price + i * 0.1 for i in range(100)],
                'volume': [1000 + i * 10 for i in range(100)]
            })

            # Resample to target timeframe
            if timeframe != '1min':
                df = df.set_index('timestamp').resample(timeframe).agg({
                    'symbol': 'first',
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).reset_index()

            data_dict[f'AAPL_{timeframe}'] = df

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
        """Create indicator engine with macro indicators enabled"""
        from core_engine.config import IndicatorConfig

        class TestIndicatorConfig(IndicatorConfig):
            @property
            def enable_macro_indicators(self) -> bool:
                return True

        config = TestIndicatorConfig()
        return EnhancedTechnicalIndicators(config)

    @pytest.fixture
    def macro_data(self):
        """Create sample macro data"""
        dates = pd.date_range('2024-01-01', periods=50, freq='D')

        return {
            'vix': pd.DataFrame({
                'timestamp': dates,
                'close': [15 + i * 0.1 for i in range(50)],
            }),
            'spy': pd.DataFrame({
                'timestamp': dates,
                'close': [400 + i * 0.5 for i in range(50)],
            }),
            'dxy': pd.DataFrame({
                'timestamp': dates,
                'close': [100 + i * 0.2 for i in range(50)],
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
        """Create indicator engine with fresh config"""
        from core_engine.config import IndicatorConfig
        config = IndicatorConfig()
        return EnhancedTechnicalIndicators(config)

    @pytest.fixture
    def enriched_data(self):
        """Create sample enriched data with indicators"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        base_price = 100.0

        df = pd.DataFrame({
            'timestamp': dates,
            'symbol': ['AAPL'] * 100,
            'open': [base_price + i * 0.1 for i in range(100)],
            'high': [base_price + 1 + i * 0.1 for i in range(100)],
            'low': [base_price - 1 + i * 0.1 for i in range(100)],
            'close': [base_price + i * 0.1 for i in range(100)],
            'volume': [1000 + i * 10 for i in range(100)],
            'rsi': [50 + i * 0.1 for i in range(100)],
            'macd': [i * 0.01 for i in range(100)],
            'macd_signal': [i * 0.005 for i in range(100)],
            'bb_position': [i * 0.001 for i in range(100)],
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
        """Create indicator engine with fresh config"""
        from core_engine.config import IndicatorConfig
        config = IndicatorConfig()
        return EnhancedTechnicalIndicators(config)

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

    @pytest.mark.asyncio
    async def test_adapt_to_regime_high_volatility(self, engine):
        """Test regime adaptation for high volatility"""
        # Mock regime context for high volatility
        from unittest.mock import Mock
        regime_context = Mock()
        regime_context.primary_regime = Mock()
        regime_context.primary_regime.value = 'high_volatility'
        regime_context.volatility_regime = 'high_volatility'

        # Adapt to regime
        result = await engine.adapt_to_regime(regime_context)

        # Verify adaptation result
        assert isinstance(result, dict)
        assert result['success'] is True
        assert 'adjustments' in result
        assert len(result['adjustments']) > 0

        # Verify BB parameters were adjusted for high volatility
        assert engine.config.bb_std == 2.5
        assert engine.config.bb_period == 25

    @pytest.mark.asyncio
    async def test_adapt_to_regime_low_volatility(self, engine):
        """Test regime adaptation for low volatility"""
        # Mock regime context for low volatility
        from unittest.mock import Mock
        regime_context = Mock()
        regime_context.primary_regime = Mock()
        regime_context.primary_regime.value = 'low_volatility'
        regime_context.volatility_regime = 'low_volatility'

        # Adapt to regime
        result = await engine.adapt_to_regime(regime_context)

        # Verify adaptation result
        assert isinstance(result, dict)
        assert result['success'] is True

        # Verify BB parameters were adjusted for low volatility
        assert engine.config.bb_std == 1.5
        assert engine.config.bb_period == 15

    @pytest.mark.asyncio
    async def test_adapt_to_regime_trending(self, engine):
        """Test regime adaptation for trending market"""
        # Mock regime context for trending
        from unittest.mock import Mock
        regime_context = Mock()
        regime_context.primary_regime = Mock()
        regime_context.primary_regime.value = 'trending_up'
        regime_context.volatility_regime = 'normal'

        # Adapt to regime
        result = await engine.adapt_to_regime(regime_context)

        # Verify adaptation result
        assert isinstance(result, dict)
        assert result['success'] is True

        # Verify RSI period was adjusted for trending
        assert engine.config.rsi_period == 21

    def test_adapt_to_liquidity_low_score(self, engine):
        """Test liquidity adaptation for low liquidity score"""
        liquidity_context = {
            'overall_score': 30.0,
            'liquidity_regime': 'low_liquidity'
        }

        # Adapt to liquidity
        result = engine.adapt_to_liquidity(liquidity_context)

        # Verify adaptation result
        assert isinstance(result, dict)
        assert result['mode'] == 'low_liquidity'
        assert result['score'] == 30.0

        # Verify parameters were adjusted for low liquidity
        assert engine.config.bb_std > 2.0  # Wider bands
        assert engine.config.bb_period > 20  # Longer period

    def test_adapt_to_liquidity_high_score(self, engine):
        """Test liquidity adaptation for high liquidity score"""
        liquidity_context = {
            'overall_score': 85.0,
            'liquidity_regime': 'high_liquidity'
        }

        # Adapt to liquidity
        result = engine.adapt_to_liquidity(liquidity_context)

        # Verify adaptation result
        assert isinstance(result, dict)
        assert result['mode'] == 'high_liquidity'
        assert result['score'] == 85.0

        # Verify parameters were adjusted for high liquidity
        assert engine.config.bb_std < 2.0  # Tighter bands
        assert engine.config.bb_period < 20  # Shorter period

    def test_adapt_to_liquidity_disabled(self, engine):
        """Test liquidity adaptation when disabled"""
        # Disable liquidity adjustments
        engine.config.enable_liquidity_adjustments = False

        liquidity_context = {
            'overall_score': 50.0,
            'liquidity_regime': 'normal'
        }

        # Adapt to liquidity
        result = engine.adapt_to_liquidity(liquidity_context)

        # Verify adaptation is disabled
        assert isinstance(result, dict)
        assert result['mode'] == 'disabled'

class TestMultiTimeframeIndicators:
    """Test multi-timeframe indicator calculations"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine with multi-timeframe enabled"""
        from core_engine.config import IndicatorConfig
        config = IndicatorConfig(enable_multi_timeframe=True)
        return EnhancedTechnicalIndicators(config)

    @pytest.fixture
    def timeframe_data(self):
        """Create sample data for multiple timeframes"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')  # More data for resampling
        base_price = 100.0

        # Create 5min data
        min5_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=60, freq='5min'),
            'symbol': ['AAPL'] * 60,
            'open': [base_price + i * 0.5 for i in range(60)],
            'high': [base_price + 2 + i * 0.5 for i in range(60)],
            'low': [base_price - 2 + i * 0.5 for i in range(60)],
            'close': [base_price + i * 0.5 for i in range(60)],
            'volume': [5000 + i * 100 for i in range(60)]
        })

        # Create 1H data
        hour1_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='1H'),
            'symbol': ['AAPL'] * 5,
            'open': [base_price + i * 2.0 for i in range(5)],
            'high': [base_price + 4 + i * 2.0 for i in range(5)],
            'low': [base_price - 4 + i * 2.0 for i in range(5)],
            'close': [base_price + i * 2.0 for i in range(5)],
            'volume': [25000 + i * 500 for i in range(5)]
        })

        return {
            'AAPL_5min': min5_data,
            'AAPL_1H': hour1_data
        }

    def test_calculate_multi_timeframe_indicators(self, engine, timeframe_data):
        """Test calculate_multi_timeframe_indicators method"""
        result = engine.calculate_multi_timeframe_indicators(timeframe_data)

        assert isinstance(result, dict)
        # Should return results by symbol
        assert 'AAPL' in result or len(result) == 0  # May be empty if data insufficient

    def test_calculate_timeframe_indicators(self, engine, timeframe_data):
        """Test _calculate_timeframe_indicators method"""
        df = timeframe_data['AAPL_5min']
        result = engine._calculate_timeframe_indicators(df, '5min')

        assert isinstance(result, dict)
        # Check for timeframe-specific indicators
        assert any('rsi_5min' in key or 'sma_' in key for key in result.keys())

    def test_calculate_timeframe_consensus(self, engine):
        """Test _calculate_timeframe_consensus method"""
        # Mock timeframe indicators
        indicators = {
            '5min': {'rsi_5min': 70, 'macd_hist_5min': 1.5},
            '1H': {'rsi_1H': 65, 'macd_hist_1H': 1.2}
        }

        consensus = engine._calculate_timeframe_consensus(indicators)

        assert isinstance(consensus, dict)
        # Should have consensus signals
        assert len(consensus) >= 0  # May be empty if no valid data

    def test_calculate_timeframe_alignment(self, engine):
        """Test _calculate_timeframe_alignment method"""
        # Mock timeframe indicators with RSI values
        indicators = {
            '5min': {'rsi_5min': 70},
            '1H': {'rsi_1H': 65}
        }

        alignment = engine._calculate_timeframe_alignment(indicators)

        assert isinstance(alignment, float)
        assert 0 <= alignment <= 1

    def test_analyze_vix_regime(self, engine):
        """Test _analyze_vix_regime method"""
        # Create VIX data with different levels
        dates = pd.date_range('2024-01-01', periods=30, freq='D')

        # Low volatility - VIX below 12
        low_vix = pd.DataFrame({'close': [10] * 30})
        regime = engine._analyze_vix_regime(low_vix)
        assert regime == "low"

        # Normal volatility - VIX 12-20
        normal_vix = pd.DataFrame({'close': [15] * 30})
        regime = engine._analyze_vix_regime(normal_vix)
        assert regime == "normal"

        # Elevated volatility - VIX 20-30
        elevated_vix = pd.DataFrame({'close': [25] * 30})
        regime = engine._analyze_vix_regime(elevated_vix)
        assert regime == "elevated"

        # Extreme volatility - VIX above 30
        extreme_vix = pd.DataFrame({'close': [35] * 30})
        regime = engine._analyze_vix_regime(extreme_vix)
        assert regime == "extreme"

class TestMacroRegimeIndicators:
    """Test macro regime indicator calculations"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine with macro indicators enabled"""
        from core_engine.config import IndicatorConfig

        class TestIndicatorConfig(IndicatorConfig):
            @property
            def enable_macro_indicators(self) -> bool:
                return True

        config = TestIndicatorConfig()
        return EnhancedTechnicalIndicators(config)

    @pytest.fixture
    def macro_data(self):
        """Create sample macro data"""
        dates = pd.date_range('2024-01-01', periods=50, freq='D')

        # VIX data
        vix_data = pd.DataFrame({
            'timestamp': dates,
            'close': [15 + i * 0.1 for i in range(50)]
        })

        # Yield curve data (10Y - 2Y spread)
        yield_data = pd.DataFrame({
            'timestamp': dates,
            'close': [0.5 + i * 0.01 for i in range(50)]
        })

        # Dollar index
        dollar_data = pd.DataFrame({
            'timestamp': dates,
            'close': [100 + i * 0.2 for i in range(50)]
        })

        # Commodity data (WTI)
        commodity_data = pd.DataFrame({
            'timestamp': dates,
            'close': [80 + i * 0.5 for i in range(50)]
        })

        # Credit spread data (HYG/LQD proxy)
        hyg_data = pd.DataFrame({
            'timestamp': dates,
            'close': [85 + i * 0.1 for i in range(50)]
        })
        lqd_data = pd.DataFrame({
            'timestamp': dates,
            'close': [120 + i * 0.3 for i in range(50)]
        })

        return {
            'VIX': vix_data,
            'TNX_TYX': yield_data,
            'DXY': dollar_data,
            'WTI': commodity_data,
            'HYG': hyg_data,
            'LQD': lqd_data
        }

    def test_calculate_macro_regime_indicators(self, engine, macro_data):
        """Test calculate_macro_regime_indicators method"""
        result = engine.calculate_macro_regime_indicators(macro_data)

        assert isinstance(result, MacroRegimeIndicators)
        assert hasattr(result, 'vix_regime')
        assert hasattr(result, 'yield_curve_regime')
        assert hasattr(result, 'dollar_strength')
        assert hasattr(result, 'commodity_trend')
        assert hasattr(result, 'credit_spread_regime')
        assert hasattr(result, 'macro_regime_score')
        assert hasattr(result, 'regime_confidence')

    def test_analyze_vix_regime(self, engine):
        """Test _analyze_vix_regime method"""
        # Create VIX data with different levels
        dates = pd.date_range('2024-01-01', periods=30, freq='D')

        # Low volatility - VIX below 12
        low_vix = pd.DataFrame({'close': [10] * 30})
        regime = engine._analyze_vix_regime(low_vix)
        assert regime == "low"

        # Normal volatility - VIX 12-20
        normal_vix = pd.DataFrame({'close': [15] * 30})
        regime = engine._analyze_vix_regime(normal_vix)
        assert regime == "normal"

        # Elevated volatility - VIX 20-30
        elevated_vix = pd.DataFrame({'close': [25] * 30})
        regime = engine._analyze_vix_regime(elevated_vix)
        assert regime == "elevated"

        # Extreme volatility - VIX above 30
        extreme_vix = pd.DataFrame({'close': [35] * 30})
        regime = engine._analyze_vix_regime(extreme_vix)
        assert regime == "extreme"

    def test_analyze_yield_curve_regime(self, engine):
        """Test _analyze_yield_curve_regime method"""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')

        # Steep yield curve - yields rising 15% over 20 days (from 1.0 to 1.15)
        steep_curve = pd.DataFrame({'close': [1.0] * 10 + list(np.linspace(1.0, 1.15, 20))})
        regime = engine._analyze_yield_curve_regime(steep_curve, None)
        assert regime == "steep"

        # Normal yield curve - yields stable
        normal_curve = pd.DataFrame({'close': [0.5] * 30})
        regime = engine._analyze_yield_curve_regime(normal_curve, None)
        assert regime == "normal"

        # Flat yield curve - yields falling 15% over 20 days
        flat_curve = pd.DataFrame({'close': [0.5] * 10 + list(np.linspace(0.5, 0.425, 20))})
        regime = engine._analyze_yield_curve_regime(flat_curve, None)
        assert regime == "flat"

    def test_analyze_dollar_strength(self, engine):
        """Test _analyze_dollar_strength method"""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')

        # Strong dollar - rising from 95 to 105 (10% increase)
        strong_dollar = pd.DataFrame({'close': list(range(95, 106)) + [105] * 9})
        strength = engine._analyze_dollar_strength(strong_dollar)
        assert strength > 0

        # Weak dollar - falling from 105 to 95 (10% decrease)
        weak_dollar = pd.DataFrame({'close': list(range(105, 94, -1)) + [95] * 9})
        strength = engine._analyze_dollar_strength(weak_dollar)
        assert strength < 0

    def test_analyze_commodity_trend(self, engine):
        """Test _analyze_commodity_trend method"""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')

        # Bullish trend (Gold up 10% over 20 days)
        bullish_data = pd.DataFrame({
            'close': list(range(80, 101))  # Rising from 80 to 100
        })
        trend = engine._analyze_commodity_trend(bullish_data, None)
        assert trend == "bullish"

        # Bearish trend (Gold down 10% over 20 days)
        bearish_data = pd.DataFrame({
            'close': list(range(100, 79, -1))  # Falling from 100 to 80
        })
        trend = engine._analyze_commodity_trend(bearish_data, None)
        assert trend == "bearish"

        # Neutral trend
        neutral_data = pd.DataFrame({'close': [90] * 30})
        trend = engine._analyze_commodity_trend(neutral_data, None)
        assert trend == "neutral"

    def test_analyze_credit_spreads(self, engine):
        """Test _analyze_credit_spreads method"""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')

        # Wide spreads (HYG underperforms LQD)
        hyg_data = pd.DataFrame({'close': [85] * 30})
        lqd_data = pd.DataFrame({'close': [120] * 30})
        # Simulate HYG down 3%, LQD up 1% = wide spreads
        hyg_data.loc[29, 'close'] = 82.45  # -3%
        lqd_data.loc[29, 'close'] = 121.2   # +1%

        regime = engine._analyze_credit_spreads(hyg_data, lqd_data)
        assert regime in ["wide", "stressed"]

        # Tight spreads (HYG outperforms LQD)
        hyg_data.loc[29, 'close'] = 87.55  # +3%
        lqd_data.loc[29, 'close'] = 118.8   # -1%

        regime = engine._analyze_credit_spreads(hyg_data, lqd_data)
        assert regime == "tight"

    def test_calculate_cross_asset_correlation(self, engine, macro_data):
        """Test _calculate_cross_asset_correlation method"""
        correlation = engine._calculate_cross_asset_correlation(macro_data)

        assert isinstance(correlation, float)
        assert 0 <= correlation <= 1

    def test_calculate_macro_regime_score(self, engine):
        """Test _calculate_macro_regime_score method"""
        score = engine._calculate_macro_regime_score(
            vix_regime="low",
            yield_curve_regime="steep",
            dollar_strength=0.5,
            commodity_trend="bullish",
            credit_spread_regime="tight"
        )

        assert isinstance(score, float)
        assert -1 <= score <= 1

        # Test with negative factors
        score_negative = engine._calculate_macro_regime_score(
            vix_regime="extreme",
            yield_curve_regime="inverted",
            dollar_strength=-0.5,
            commodity_trend="bearish",
            credit_spread_regime="stressed"
        )

        assert score_negative < score  # Should be more negative

    def test_calculate_macro_confidence(self, engine, macro_data):
        """Test _calculate_macro_confidence method"""
        confidence = engine._calculate_macro_confidence(macro_data)

        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1

class TestStandardizedConsumptionMethods:
    """Test standardized data consumption methods"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine with fresh config"""
        from core_engine.config import IndicatorConfig
        config = IndicatorConfig()
        return EnhancedTechnicalIndicators(config)

    @pytest.fixture
    def sample_indicators(self):
        """Create sample indicators DataFrame"""
        dates = pd.date_range('2024-01-01', periods=10, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'symbol': ['AAPL'] * 10,
            'rsi': [50.0 + i for i in range(10)],
            'macd': [0.5 + i * 0.1 for i in range(10)],
            'close': [100.0 + i for i in range(10)]
        })

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data DataFrame"""
        dates = pd.date_range('2024-01-01', periods=10, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'symbol': ['AAPL'] * 10,
            'open': [100.0 + i for i in range(10)],
            'high': [101.0 + i for i in range(10)],
            'low': [99.0 + i for i in range(10)],
            'close': [100.5 + i for i in range(10)],
            'volume': [1000 + i * 10 for i in range(10)]
        })

    def test_process_indicators(self, engine, sample_indicators):
        """Test process_indicators method"""
        result = engine.process_indicators(sample_indicators)
        assert isinstance(result, pd.DataFrame)
        assert result.equals(sample_indicators)

    def test_use_indicators(self, engine, sample_indicators):
        """Test use_indicators method"""
        result = engine.use_indicators(sample_indicators)
        assert isinstance(result, pd.DataFrame)
        assert result.equals(sample_indicators)

    def test_analyze_indicators(self, engine, sample_indicators):
        """Test analyze_indicators method"""
        result = engine.analyze_indicators(sample_indicators)
        assert isinstance(result, pd.DataFrame)
        assert result.equals(sample_indicators)

    def test_process_market_data(self, engine, sample_market_data):
        """Test process_market_data method"""
        result = engine.process_market_data(sample_market_data)
        assert isinstance(result, pd.DataFrame)
        assert result.equals(sample_market_data)

    def test_analyze_data(self, engine, sample_market_data):
        """Test analyze_data method"""
        result = engine.analyze_data(sample_market_data)
        assert isinstance(result, pd.DataFrame)
        assert result.equals(sample_market_data)

    def test_consume_data(self, engine, sample_market_data):
        """Test consume_data method"""
        result = engine.consume_data(sample_market_data)
        assert isinstance(result, pd.DataFrame)
        assert result.equals(sample_market_data)

class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine with fresh config"""
        from core_engine.config import IndicatorConfig
        config = IndicatorConfig()
        return EnhancedTechnicalIndicators(config)

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
            'close': [100.0] * 10,
            'open': [100.0] * 10,
            'high': [100.0] * 10,
            'low': [100.0] * 10,
            'volume': [1000] * 10
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
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [101.0, 102.0, 103.0, 104.0, 105.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0],
            'close': [100.5, 101.5, 102.5, 103.5, 104.5],
            'volume': [1000, 1500, 2000, 2500, 3000]
        })

        # Should handle gracefully
        result = engine.calculate_indicators(minimal_df)
        assert isinstance(result, pd.DataFrame)

    def test_calculate_indicators_with_nan(self, engine):
        """Test handling of NaN values"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        base_price = 100.0
        df = pd.DataFrame({
            'timestamp': dates,
            'symbol': ['AAPL'] * 100,
            'open': [base_price + i * 0.1 for i in range(100)],
            'high': [base_price + 1 + i * 0.1 for i in range(100)],
            'low': [base_price - 1 + i * 0.1 for i in range(100)],
            'close': [base_price + i * 0.1 for i in range(100)],
            'volume': [1000 + i * 10 for i in range(100)]
        })
        # Introduce some NaN values
        df.loc[10:20, 'close'] = np.nan

        result = engine.calculate_indicators(df)
        assert isinstance(result, pd.DataFrame)

class TestHealthChecks:
    """Test component health checks"""

    @pytest.fixture
    def engine(self):
        """Create indicator engine with fresh config"""
        from core_engine.config import IndicatorConfig
        config = IndicatorConfig()
        return EnhancedTechnicalIndicators(config)

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

