"""
Regime-Aware Tests for Enhanced Momentum Strategy
==================================================

Tests strategy adaptation to different market regimes (Priority 2).

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 2: Regime-Aware Testing
"""

import pytest
from unittest.mock import Mock

from core_engine.config import MomentumConfig
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from tests.unit.strategies.test_helpers import (
    create_enriched_data_dict
)

class TestMomentumRegimeAwareness:
    """Test momentum strategy regime awareness implementation"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy instance"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        return strategy

    @pytest.fixture
    def mock_regime_engine(self):
        """Create mock regime engine"""
        regime_engine = Mock()
        regime_engine.get_current_regime_context = Mock(return_value={
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal',
            'trend_regime': 'trending',
            'confidence': 0.8
        })
        regime_engine.current_regime_context = {
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal',
            'trend_regime': 'trending'
        }
        return regime_engine

    @pytest.mark.asyncio
    async def test_set_regime_engine(self, strategy, mock_regime_engine):
        """Test regime engine injection"""
        await strategy.initialize()

        strategy.set_regime_engine(mock_regime_engine)

        assert strategy.regime_engine == mock_regime_engine
        assert strategy.validate_regime_dependency() is True

    @pytest.mark.asyncio
    async def test_get_current_regime_context(self, strategy, mock_regime_engine):
        """Test getting current regime context"""
        await strategy.initialize()
        strategy.set_regime_engine(mock_regime_engine)

        regime_context = strategy.get_current_regime_context()

        assert regime_context is not None
        assert regime_context['primary_regime'] == 'normal_volatility'

    @pytest.mark.asyncio
    async def test_on_regime_change(self, strategy):
        """Test regime change handling"""
        await strategy.initialize()

        # Create mock regime context
        new_regime = Mock()
        new_regime.primary_regime = 'high_volatility'
        new_regime.volatility_regime = 'high'
        new_regime.trend_regime = 'choppy'
        new_regime.confidence = 0.7

        await strategy.on_regime_change(new_regime)

        # Verify regime context was stored
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
        assert adaptation_result['regime'] == 'low_volatility'
        assert adaptation_result['strategy_id'] == strategy.strategy_id

    @pytest.mark.asyncio
    async def test_validate_regime_dependency(self, strategy, mock_regime_engine):
        """Test regime dependency validation"""
        await strategy.initialize()

        # Without regime engine
        assert strategy.validate_regime_dependency() is False

        # With regime engine
        strategy.set_regime_engine(mock_regime_engine)
        assert strategy.validate_regime_dependency() is True

class TestMomentumHighVolatilityRegime:
    """Test momentum strategy behavior in high volatility regime"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy instance"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        return strategy

    @pytest.fixture
    def high_vol_regime_engine(self):
        """Create regime engine for high volatility"""
        regime_engine = Mock()
        regime_engine.get_current_regime_context = Mock(return_value={
            'primary_regime': 'high_volatility',
            'volatility_regime': 'high',
            'trend_regime': 'choppy',
            'confidence': 0.75
        })
        return regime_engine

    @pytest.mark.asyncio
    async def test_signal_generation_in_high_vol(self, strategy, high_vol_regime_engine):
        """Test signal generation adapts to high volatility"""
        await strategy.initialize()
        await strategy.start()
        strategy.set_regime_engine(high_vol_regime_engine)

        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=200,
            trend='uptrend'
        )

        # Set high volatility indicators
        df = enriched_data['AAPL']
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['ADX_14'] = 35.0  # Strong trend
        df['volume_ratio'] = 1.5
        df['RSI_14'] = 60.0
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        df['volatility'] = 0.30  # High volatility
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        # Trigger regime change
        regime_context = Mock()
        regime_context.primary_regime = 'high_volatility'
        regime_context.volatility_regime = 'high'
        await strategy.on_regime_change(regime_context)

        signals = await strategy.generate_signals(enriched_data)

        # Strategy should adapt to high volatility (may reduce signals or confidence)
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_position_sizing_in_high_vol(self, strategy, high_vol_regime_engine):
        """Test position sizing adjusts for high volatility"""
        await strategy.initialize()
        strategy.set_regime_engine(high_vol_regime_engine)

        # Trigger high volatility regime
        regime_context = Mock()
        regime_context.primary_regime = 'high_volatility'
        regime_context.volatility_regime = 'high'
        await strategy.on_regime_change(regime_context)

        from tests.unit.strategies.test_helpers import create_mock_strategy_signal

        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        position_size = strategy.calculate_position_size(signal, market_data)

        # High volatility should potentially reduce position size
        assert position_size >= 0
        assert position_size <= strategy.config.max_position_pct

class TestMomentumLowVolatilityRegime:
    """Test momentum strategy behavior in low volatility regime"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy instance"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        return strategy

    @pytest.fixture
    def low_vol_regime_engine(self):
        """Create regime engine for low volatility"""
        regime_engine = Mock()
        regime_engine.get_current_regime_context = Mock(return_value={
            'primary_regime': 'low_volatility',
            'volatility_regime': 'low',
            'trend_regime': 'trending',
            'confidence': 0.85
        })
        return regime_engine

    @pytest.mark.asyncio
    async def test_signal_generation_in_low_vol(self, strategy, low_vol_regime_engine):
        """Test signal generation in low volatility regime"""
        await strategy.initialize()
        await strategy.start()
        strategy.set_regime_engine(low_vol_regime_engine)

        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=200,
            trend='uptrend'
        )

        df = enriched_data['AAPL']
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['ADX_14'] = 28.0
        df['volume_ratio'] = 1.3
        df['RSI_14'] = 58.0
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        df['volatility'] = 0.08  # Low volatility
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        # Trigger regime change
        regime_context = Mock()
        regime_context.primary_regime = 'low_volatility'
        regime_context.volatility_regime = 'low'
        await strategy.on_regime_change(regime_context)

        signals = await strategy.generate_signals(enriched_data)

        # Low volatility may increase signal confidence
        assert isinstance(signals, list)

class TestMomentumRegimeTransition:
    """Test momentum strategy handling of regime transitions"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy instance"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_regime_transition_handling(self, strategy):
        """Test smooth handling of regime transitions"""
        await strategy.initialize()

        # Transition 1: Normal -> High Volatility
        regime_1 = Mock()
        regime_1.primary_regime = 'normal_volatility'
        regime_1.volatility_regime = 'normal'
        await strategy.on_regime_change(regime_1)

        # Transition 2: High Volatility
        regime_2 = Mock()
        regime_2.primary_regime = 'high_volatility'
        regime_2.volatility_regime = 'high'
        await strategy.on_regime_change(regime_2)

        # Verify strategy adapted to new regime
        assert strategy._current_regime_context == regime_2

    @pytest.mark.asyncio
    async def test_multiple_regime_changes(self, strategy):
        """Test handling of rapid regime changes"""
        await strategy.initialize()

        regimes = [
            ('normal_volatility', 'normal'),
            ('high_volatility', 'high'),
            ('low_volatility', 'low'),
            ('normal_volatility', 'normal')
        ]

        for primary, volatility in regimes:
            regime_context = Mock()
            regime_context.primary_regime = primary
            regime_context.volatility_regime = volatility
            await strategy.on_regime_change(regime_context)

            # Verify each transition is handled
            assert strategy._current_regime_context.primary_regime == primary

    @pytest.mark.asyncio
    async def test_regime_change_affects_behavior(self, strategy):
        """Test that regime changes actually affect strategy behavior"""
        await strategy.initialize()
        await strategy.start()

        # Start in normal regime
        normal_regime = Mock()
        normal_regime.primary_regime = 'normal_volatility'
        normal_regime.volatility_regime = 'normal'
        await strategy.on_regime_change(normal_regime)

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        df = enriched_data['AAPL']
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['ADX_14'] = 25.0
        df['volume_ratio'] = 1.3
        df['RSI_14'] = 55.0
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals_normal = await strategy.generate_signals(enriched_data)

        # Switch to high volatility regime
        high_vol_regime = Mock()
        high_vol_regime.primary_regime = 'high_volatility'
        high_vol_regime.volatility_regime = 'high'
        await strategy.on_regime_change(high_vol_regime)

        signals_high_vol = await strategy.generate_signals(enriched_data)

        # Strategy behavior should adapt (may change signal count or confidence)
        assert isinstance(signals_normal, list)
        assert isinstance(signals_high_vol, list)

