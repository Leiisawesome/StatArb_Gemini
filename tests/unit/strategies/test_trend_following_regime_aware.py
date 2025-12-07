"""
Regime-Aware Tests for Enhanced Trend Following Strategy
=========================================================

Tests strategy adaptation to different market regimes (Priority 2).

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 2: Regime-Aware Testing
"""

import pytest
from core_engine.config import TrendFollowingConfig
from core_engine.trading.strategies.implementations.trend_following.enhanced_trend_following import EnhancedTrendFollowingStrategy
from tests.unit.strategies.test_regime_aware_helpers import (
    create_mock_regime_engine,
    create_regime_context_mock,
    get_regime_config
)


class TestTrendFollowingRegimeAwareness:
    """Test trend following strategy regime awareness"""

    @pytest.fixture
    def strategy(self):
        """Create trend following strategy instance"""
        config = TrendFollowingConfig(name='test_trend')
        strategy = EnhancedTrendFollowingStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_set_regime_engine(self, strategy):
        """Test regime engine injection"""
        await strategy.initialize()

        regime_engine = create_mock_regime_engine('normal_volatility', 'normal', 'trending')
        strategy.set_regime_engine(regime_engine)

        assert strategy.regime_engine == regime_engine
        assert strategy.validate_regime_dependency() is True

    @pytest.mark.asyncio
    async def test_trending_regime_enhances_signals(self, strategy):
        """Test that trending regime enhances trend following signals"""
        await strategy.initialize()

        # Trending regime (favorable for trend following)
        regime_context = create_regime_context_mock('normal_volatility', 'normal', 'trending')
        await strategy.on_regime_change(regime_context)

        assert strategy._current_regime_context.trend_regime == 'trending'

    @pytest.mark.asyncio
    async def test_choppy_regime_reduces_signals(self, strategy):
        """Test that choppy regime reduces trend following signals"""
        await strategy.initialize()

        # Choppy regime (unfavorable for trend following)
        regime_context = create_regime_context_mock('high_volatility', 'high', 'choppy')
        await strategy.on_regime_change(regime_context)

        assert strategy._current_regime_context.trend_regime == 'choppy'

    @pytest.mark.asyncio
    async def test_regime_adaptation(self, strategy):
        """Test regime adaptation"""
        await strategy.initialize()

        regime_config = get_regime_config('trending')
        regime_context = create_regime_context_mock(**regime_config)

        adaptation_result = await strategy.adapt_to_regime(regime_context)

        assert adaptation_result['adapted'] is True

