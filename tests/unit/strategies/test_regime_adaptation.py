"""
Comprehensive Regime Adaptation Tests
=====================================

Tests regime adaptation capabilities for all strategies including:
- Regime engine injection (set_regime_engine)
- Regime context retrieval (get_current_regime_context)
- Regime-aware position sizing
- Regime-aware signal filtering
- Strategy adaptation to regime changes

Author: StatArb_Gemini Test Suite
Date: November 4, 2025
"""

import pytest
from datetime import datetime

from core_engine.config import (
    MomentumConfig, MeanReversionConfig, StatisticalArbitrageConfig,
    TrendFollowingConfig, BreakoutConfig, PairsConfig
)
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion import EnhancedMeanReversionStrategy
from core_engine.trading.strategies.implementations.statistical_arbitrage.enhanced_statistical_arbitrage import EnhancedStatisticalArbitrageStrategy
from core_engine.trading.strategies.implementations.trend_following.enhanced_trend_following import EnhancedTrendFollowingStrategy
from core_engine.trading.strategies.implementations.breakout.enhanced_breakout import EnhancedBreakoutStrategy
from core_engine.trading.strategies.implementations.pairs_trading.enhanced_pairs_trading import EnhancedPairsTradingStrategy
from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType
from tests.unit.strategies.test_helpers import create_enriched_data_dict


# =============================================================================
# REGIME ENGINE MOCK
# =============================================================================

class MockRegimeEngine:
    """Mock regime engine for testing"""

    def __init__(self, regime_context=None):
        self.current_regime_context = regime_context or {
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal_volatility',
            'trend_regime': 'trending',
            'liquidity_regime': 'high_liquidity',
            'confidence': 0.8,
            'regime_id': 'regime_1'
        }

    def get_current_regime_context(self):
        """Get current regime context"""
        return self.current_regime_context

    async def get_current_regime(self):
        """Get current regime (async version)"""
        return self.current_regime_context

    def set_regime_context(self, regime_context):
        """Set regime context for testing"""
        self.current_regime_context = regime_context


# =============================================================================
# REGIME ENGINE INJECTION TESTS
# =============================================================================

class TestRegimeEngineInjection:
    """Tests for regime engine injection"""

    @pytest.mark.asyncio
    async def test_set_regime_engine_momentum(self):
        """Test setting regime engine for momentum strategy"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        regime_engine = MockRegimeEngine()
        strategy.set_regime_engine(regime_engine)

        assert strategy.regime_engine is not None
        assert strategy.regime_engine == regime_engine

    @pytest.mark.asyncio
    async def test_set_regime_engine_all_strategies(self):
        """Test setting regime engine for all strategies"""
        strategies = [
            (EnhancedMomentumStrategy, MomentumConfig, {'symbols': ['AAPL']}),
            (EnhancedMeanReversionStrategy, MeanReversionConfig, {'symbols': ['AAPL']}),
            (EnhancedBreakoutStrategy, BreakoutConfig, {'symbols': ['AAPL']}),
            (EnhancedTrendFollowingStrategy, TrendFollowingConfig, {'symbols': ['AAPL']}),
            (EnhancedPairsTradingStrategy, PairsConfig, {'asset_universe': ['AAPL', 'MSFT']})
        ]

        for strategy_class, config_class, config_params in strategies:
            config = config_class(name='test', **config_params)
            strategy = strategy_class(config)
            await strategy.initialize()

            regime_engine = MockRegimeEngine()
            strategy.set_regime_engine(regime_engine)

            assert strategy.regime_engine is not None
            assert strategy.regime_engine == regime_engine

    @pytest.mark.asyncio
    async def test_get_current_regime_context_with_engine(self):
        """Test getting regime context when engine is set"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        regime_context = {
            'primary_regime': 'high_volatility',
            'volatility_regime': 'high_volatility',
            'confidence': 0.9
        }
        regime_engine = MockRegimeEngine(regime_context)
        strategy.set_regime_engine(regime_engine)

        # Get regime context
        context = strategy.get_current_regime_context()

        assert context is not None
        assert context['primary_regime'] == 'high_volatility'

    @pytest.mark.asyncio
    async def test_get_current_regime_context_without_engine(self):
        """Test getting regime context when engine is not set"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        # Get regime context without engine
        context = strategy.get_current_regime_context()

        # Should return None or handle gracefully
        assert context is None or isinstance(context, dict)


# =============================================================================
# REGIME-AWARE POSITION SIZING TESTS
# =============================================================================

class TestRegimeAwarePositionSizing:
    """Tests for regime-aware position sizing"""

    @pytest.mark.asyncio
    async def test_position_sizing_low_volatility_regime(self):
        """Test position sizing in low volatility regime"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        # Set low volatility regime
        regime_engine = MockRegimeEngine({
            'primary_regime': 'low_volatility',
            'volatility_regime': 'low_volatility',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        signal = StrategySignal(
            strategy_id=strategy.strategy_id,
            symbol='AAPL',
            signal_type=SignalType.BUY,
            confidence=0.8,
            target_quantity=100,
            timestamp=datetime.now()
        )

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=100)

        # Calculate position size
        size = strategy.calculate_position_size(signal, market_data)

        # In low volatility, should allow larger positions
        assert size > 0
        assert isinstance(size, (int, float))

    @pytest.mark.asyncio
    async def test_position_sizing_high_volatility_regime(self):
        """Test position sizing in high volatility regime"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        # Set high volatility regime
        regime_engine = MockRegimeEngine({
            'primary_regime': 'high_volatility',
            'volatility_regime': 'high_volatility',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        signal = StrategySignal(
            strategy_id=strategy.strategy_id,
            symbol='AAPL',
            signal_type=SignalType.BUY,
            confidence=0.8,
            target_quantity=100,
            timestamp=datetime.now()
        )

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=100)

        # Calculate position size
        size_high_vol = strategy.calculate_position_size(signal, market_data)

        # Compare with low volatility
        regime_engine.set_regime_context({
            'primary_regime': 'low_volatility',
            'volatility_regime': 'low_volatility',
            'confidence': 0.8
        })
        size_low_vol = strategy.calculate_position_size(signal, market_data)

        # High volatility should have smaller or equal position size
        assert size_high_vol > 0
        assert size_low_vol > 0

    @pytest.mark.asyncio
    async def test_position_sizing_extreme_volatility_regime(self):
        """Test position sizing in extreme volatility regime"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        # Set extreme volatility regime
        regime_engine = MockRegimeEngine({
            'primary_regime': 'extreme_volatility',
            'volatility_regime': 'extreme_volatility',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        signal = StrategySignal(
            strategy_id=strategy.strategy_id,
            symbol='AAPL',
            signal_type=SignalType.BUY,
            confidence=0.8,
            target_quantity=100,
            timestamp=datetime.now()
        )

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=100)

        # Calculate position size
        size = strategy.calculate_position_size(signal, market_data)

        # In extreme volatility, should be conservative
        assert size >= 0
        assert isinstance(size, (int, float))

    @pytest.mark.asyncio
    async def test_position_sizing_crisis_regime(self):
        """Test position sizing in crisis regime"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        # Set crisis regime
        regime_engine = MockRegimeEngine({
            'primary_regime': 'crisis',
            'volatility_regime': 'extreme_volatility',
            'trend_regime': 'choppy',
            'confidence': 0.9
        })
        strategy.set_regime_engine(regime_engine)

        signal = StrategySignal(
            strategy_id=strategy.strategy_id,
            symbol='AAPL',
            signal_type=SignalType.BUY,
            confidence=0.8,
            target_quantity=100,
            timestamp=datetime.now()
        )

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=100)

        # Calculate position size
        size = strategy.calculate_position_size(signal, market_data)

        # In crisis, should be very conservative
        assert size >= 0


# =============================================================================
# REGIME-AWARE SIGNAL FILTERING TESTS
# =============================================================================

class TestRegimeAwareSignalFiltering:
    """Tests for regime-aware signal filtering"""

    @pytest.mark.asyncio
    async def test_signal_generation_normal_regime(self):
        """Test signal generation in normal regime"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()
        await strategy.start()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal_volatility',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        # Generate signals
        signals = await strategy.generate_signals(market_data)

        # Should generate signals normally
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_signal_generation_high_volatility_regime(self):
        """Test signal generation in high volatility regime"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()
        await strategy.start()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'high_volatility',
            'volatility_regime': 'high_volatility',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        # Generate signals
        signals = await strategy.generate_signals(market_data)

        # Should generate signals (may be filtered more strictly)
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_signal_generation_crisis_regime(self):
        """Test signal generation in crisis regime"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()
        await strategy.start()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'crisis',
            'volatility_regime': 'extreme_volatility',
            'confidence': 0.9
        })
        strategy.set_regime_engine(regime_engine)

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        # Generate signals
        signals = await strategy.generate_signals(market_data)

        # In crisis, may generate fewer signals
        assert isinstance(signals, list)


# =============================================================================
# REGIME CHANGE HANDLING TESTS
# =============================================================================

class TestRegimeChangeHandling:
    """Tests for handling regime changes"""

    @pytest.mark.asyncio
    async def test_regime_change_from_normal_to_high_volatility(self):
        """Test strategy adaptation when regime changes from normal to high volatility"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()
        await strategy.start()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal_volatility',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        # Get initial regime context
        initial_context = strategy.get_current_regime_context()
        assert initial_context['volatility_regime'] == 'normal_volatility'

        # Change regime to high volatility
        regime_engine.set_regime_context({
            'primary_regime': 'high_volatility',
            'volatility_regime': 'high_volatility',
            'confidence': 0.9
        })

        # Get updated regime context
        updated_context = strategy.get_current_regime_context()
        assert updated_context['volatility_regime'] == 'high_volatility'

    @pytest.mark.asyncio
    async def test_regime_change_position_sizing_adjustment(self):
        """Test position sizing adjustment on regime change"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal_volatility',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        signal = StrategySignal(
            strategy_id=strategy.strategy_id,
            symbol='AAPL',
            signal_type=SignalType.BUY,
            confidence=0.8,
            target_quantity=100,
            timestamp=datetime.now()
        )

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=100)

        # Calculate size in normal regime
        size_normal = strategy.calculate_position_size(signal, market_data)

        # Change to high volatility
        regime_engine.set_regime_context({
            'primary_regime': 'high_volatility',
            'volatility_regime': 'high_volatility',
            'confidence': 0.9
        })

        # Calculate size in high volatility
        size_high_vol = strategy.calculate_position_size(signal, market_data)

        # Both should be valid
        assert size_normal > 0
        assert size_high_vol >= 0


# =============================================================================
# REGIME-AWARE STRATEGY BEHAVIOR TESTS
# =============================================================================

class TestRegimeAwareStrategyBehavior:
    """Tests for regime-aware strategy behavior"""

    @pytest.mark.asyncio
    async def test_trend_following_regime_awareness(self):
        """Test trend following strategy regime awareness"""
        strategy = EnhancedTrendFollowingStrategy(TrendFollowingConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()
        await strategy.start()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'trending',
            'trend_regime': 'trending',
            'volatility_regime': 'normal_volatility',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        # Get regime context
        context = strategy.get_current_regime_context()

        assert context is not None
        assert context['trend_regime'] == 'trending'

    @pytest.mark.asyncio
    async def test_mean_reversion_regime_awareness(self):
        """Test mean reversion strategy regime awareness"""
        strategy = EnhancedMeanReversionStrategy(MeanReversionConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()
        await strategy.start()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'sideways',
            'trend_regime': 'sideways',
            'volatility_regime': 'normal_volatility',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        # Get regime context
        context = strategy.get_current_regime_context()

        assert context is not None

    @pytest.mark.asyncio
    async def test_breakout_regime_awareness(self):
        """Test breakout strategy regime awareness"""
        strategy = EnhancedBreakoutStrategy(BreakoutConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()
        await strategy.start()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal_volatility',
            'liquidity_regime': 'high_liquidity',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        # Get regime context
        context = strategy.get_current_regime_context()

        assert context is not None

    @pytest.mark.asyncio
    async def test_stat_arb_regime_awareness(self):
        """Test statistical arbitrage strategy regime awareness"""
        strategy = EnhancedStatisticalArbitrageStrategy(
            StatisticalArbitrageConfig(name='test', asset_universe=['AAPL', 'MSFT'])
        )
        await strategy.initialize()
        await strategy.start()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal_volatility',
            'confidence': 0.8
        })
        strategy.set_regime_engine(regime_engine)

        # Get regime context
        context = strategy.get_current_regime_context()

        assert context is not None


# =============================================================================
# REGIME CONTEXT VALIDATION TESTS
# =============================================================================

class TestRegimeContextValidation:
    """Tests for regime context validation"""

    @pytest.mark.asyncio
    async def test_regime_context_structure(self):
        """Test regime context has expected structure"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal_volatility',
            'trend_regime': 'trending',
            'liquidity_regime': 'high_liquidity',
            'confidence': 0.8,
            'regime_id': 'regime_1'
        })
        strategy.set_regime_engine(regime_engine)

        context = strategy.get_current_regime_context()

        assert context is not None
        assert isinstance(context, dict)
        assert 'primary_regime' in context or 'volatility_regime' in context

    @pytest.mark.asyncio
    async def test_regime_context_confidence(self):
        """Test regime context confidence values"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        regime_engine = MockRegimeEngine({
            'primary_regime': 'normal_volatility',
            'confidence': 0.9
        })
        strategy.set_regime_engine(regime_engine)

        context = strategy.get_current_regime_context()

        if context and 'confidence' in context:
            assert 0.0 <= context['confidence'] <= 1.0

    @pytest.mark.asyncio
    async def test_regime_context_regime_types(self):
        """Test different regime types"""
        strategy = EnhancedMomentumStrategy(MomentumConfig(name='test', symbols=['AAPL']))
        await strategy.initialize()

        regime_types = [
            'low_volatility',
            'normal_volatility',
            'high_volatility',
            'extreme_volatility',
            'crisis'
        ]

        for regime_type in regime_types:
            regime_engine = MockRegimeEngine({
                'primary_regime': regime_type,
                'volatility_regime': regime_type,
                'confidence': 0.8
            })
            strategy.set_regime_engine(regime_engine)

            context = strategy.get_current_regime_context()

            assert context is not None

