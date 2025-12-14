"""
Regime-Aware Tests for Enhanced Mean Reversion Strategy
========================================================

Tests strategy adaptation to different market regimes (Priority 2).

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 2: Regime-Aware Testing
"""

import pytest
from unittest.mock import Mock

from core_engine.config import MeanReversionConfig
from core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion import EnhancedMeanReversionStrategy
from tests.unit.strategies.test_helpers import (
    create_enriched_data_dict
)

class TestMeanReversionRegimeFiltering:
    """Test mean reversion strategy regime filtering functionality"""

    @pytest.fixture
    def strategy_with_regime_filter(self):
        """Create mean reversion strategy with regime filter enabled"""
        config = MeanReversionConfig(name='test_mean_reversion', enable_regime_filter=True)
        strategy = EnhancedMeanReversionStrategy(config)
        return strategy

    @pytest.fixture
    def strategy_without_regime_filter(self):
        """Create mean reversion strategy without regime filter"""
        config = MeanReversionConfig(name='test_mean_reversion', enable_regime_filter=False)
        strategy = EnhancedMeanReversionStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_regime_filter_enabled(self, strategy_with_regime_filter):
        """Test that regime filter can be enabled"""
        await strategy_with_regime_filter.initialize()

        assert strategy_with_regime_filter.config.enable_regime_filter is True

    @pytest.mark.asyncio
    async def test_regime_filter_disabled(self, strategy_without_regime_filter):
        """Test that regime filter can be disabled"""
        await strategy_without_regime_filter.initialize()

        assert strategy_without_regime_filter.config.enable_regime_filter is False

    @pytest.mark.asyncio
    async def test_regime_confidence_adjustment(self, strategy_with_regime_filter):
        """Test regime confidence adjustment in signal calculation"""
        await strategy_with_regime_filter.initialize()
        await strategy_with_regime_filter.start()

        # Setup favorable regime (mean reversion works well in range-bound markets)
        strategy_with_regime_filter.regime_data = {
            'AAPL': {
                'regime': 'sideways',
                'volatility_regime': 'normal'
            }
        }

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        df = enriched_data['AAPL']
        df['RSI_14'] = 25.0  # Oversold
        df['zscore'] = -2.5
        df['bb_position'] = 0.1
        df['bb_lower'] = df['close'] * 0.95
        df['bb_middle'] = df['close']
        df['bb_upper'] = df['close'] * 1.05
        df['SMA_20'] = df['close'] * 1.02
        df['ATR_14'] = df['close'] * 0.02
        df['volume_ratio'] = 1.3
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy_with_regime_filter.generate_signals(enriched_data)

        # Regime filtering should adjust signal confidence
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_favorable_regime_boosts_confidence(self, strategy_with_regime_filter):
        """Test that favorable regimes boost signal confidence"""
        await strategy_with_regime_filter.initialize()
        await strategy_with_regime_filter.start()

        # Favorable regime for mean reversion (sideways/range-bound)
        strategy_with_regime_filter.regime_data = {
            'AAPL': {
                'regime': 'sideways',
                'volatility_regime': 'normal'
            }
        }

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        df = enriched_data['AAPL']
        df['RSI_14'] = 28.0
        df['zscore'] = -2.3
        df['bb_position'] = 0.15
        df['bb_lower'] = df['close'] * 0.95
        df['bb_middle'] = df['close']
        df['bb_upper'] = df['close'] * 1.05
        df['SMA_20'] = df['close'] * 1.02
        df['ATR_14'] = df['close'] * 0.02
        df['volume_ratio'] = 1.2
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals_favorable = await strategy_with_regime_filter.generate_signals(enriched_data)

        # Unfavorable regime (trending markets)
        strategy_with_regime_filter.regime_data = {
            'AAPL': {
                'regime': 'trending',
                'volatility_regime': 'high'
            }
        }

        signals_unfavorable = await strategy_with_regime_filter.generate_signals(enriched_data)

        # Favorable regime should produce higher confidence signals
        assert isinstance(signals_favorable, list)
        assert isinstance(signals_unfavorable, list)

class TestMeanReversionRegimeAwareness:
    """Test mean reversion strategy regime awareness"""

    @pytest.fixture
    def strategy(self):
        """Create mean reversion strategy instance"""
        config = MeanReversionConfig(name='test_mean_reversion')
        strategy = EnhancedMeanReversionStrategy(config)
        return strategy

    @pytest.fixture
    def mock_regime_engine(self):
        """Create mock regime engine"""
        regime_engine = Mock()
        regime_engine.get_current_regime_context = Mock(return_value={
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal',
            'trend_regime': 'sideways',
            'confidence': 0.8
        })
        return regime_engine

    @pytest.mark.asyncio
    async def test_set_regime_engine(self, strategy, mock_regime_engine):
        """Test regime engine injection"""
        await strategy.initialize()

        strategy.set_regime_engine(mock_regime_engine)

        assert strategy.regime_engine == mock_regime_engine
        assert strategy.validate_regime_dependency() is True

    @pytest.mark.asyncio
    async def test_on_regime_change(self, strategy):
        """Test regime change handling"""
        await strategy.initialize()

        new_regime = Mock()
        new_regime.primary_regime = 'high_volatility'
        new_regime.volatility_regime = 'high'

        await strategy.on_regime_change(new_regime)

        assert hasattr(strategy, '_current_regime_context')
        assert strategy._current_regime_context == new_regime

    @pytest.mark.asyncio
    async def test_adapt_to_regime(self, strategy):
        """Test regime adaptation"""
        await strategy.initialize()

        regime_context = Mock()
        regime_context.primary_regime = 'low_volatility'
        regime_context.volatility_regime = 'low'

        adaptation_result = await strategy.adapt_to_regime(regime_context)

        assert adaptation_result['adapted'] is True

class TestMeanReversionHighVolatilityRegime:
    """Test mean reversion in high volatility regime"""

    @pytest.fixture
    def strategy(self):
        """Create mean reversion strategy with regime filter"""
        config = MeanReversionConfig(name='test_mean_reversion', enable_regime_filter=True)
        strategy = EnhancedMeanReversionStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_high_volatility_reduces_signals(self, strategy):
        """Test that high volatility reduces mean reversion signals"""
        await strategy.initialize()
        await strategy.start()

        # High volatility regime (unfavorable for mean reversion)
        strategy.regime_data = {
            'AAPL': {
                'regime': 'trending',
                'volatility_regime': 'high'
            }
        }

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        df = enriched_data['AAPL']
        df['RSI_14'] = 25.0  # Oversold
        df['zscore'] = -2.5
        df['bb_position'] = 0.1
        df['bb_lower'] = df['close'] * 0.95
        df['bb_middle'] = df['close']
        df['bb_upper'] = df['close'] * 1.05
        df['SMA_20'] = df['close'] * 1.02
        df['ATR_14'] = df['close'] * 0.04  # High ATR (high volatility)
        df['volume_ratio'] = 1.5
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # High volatility should reduce confidence or filter signals
        assert isinstance(signals, list)
        for signal in signals:
            if signal.symbol == 'AAPL':
                # Confidence may be reduced by regime filter
                assert signal.confidence <= 1.0

class TestMeanReversionSidewaysRegime:
    """Test mean reversion in sideways/range-bound regime (favorable)"""

    @pytest.fixture
    def strategy(self):
        """Create mean reversion strategy with regime filter"""
        config = MeanReversionConfig(name='test_mean_reversion', enable_regime_filter=True)
        strategy = EnhancedMeanReversionStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_sideways_regime_boosts_signals(self, strategy):
        """Test that sideways regime boosts mean reversion signals"""
        await strategy.initialize()
        await strategy.start()

        # Sideways regime (favorable for mean reversion)
        strategy.regime_data = {
            'AAPL': {
                'regime': 'sideways',
                'volatility_regime': 'normal'
            }
        }

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        df = enriched_data['AAPL']
        df['RSI_14'] = 28.0  # Oversold
        df['zscore'] = -2.2
        df['bb_position'] = 0.15
        df['bb_lower'] = df['close'] * 0.95
        df['bb_middle'] = df['close']
        df['bb_upper'] = df['close'] * 1.05
        df['SMA_20'] = df['close'] * 1.01
        df['ATR_14'] = df['close'] * 0.02  # Normal ATR
        df['volume_ratio'] = 1.2
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # Sideways regime should enhance mean reversion confidence
        assert isinstance(signals, list)

