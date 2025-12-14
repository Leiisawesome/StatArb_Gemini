"""
Regime-Aware Tests for Enhanced Pairs Trading Strategy
=======================================================

Tests strategy adaptation to different market regimes (Priority 2).

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 2: Regime-Aware Testing
"""

import pytest
from core_engine.config import PairsConfig
from core_engine.trading.strategies.implementations.pairs_trading.enhanced_pairs_trading import EnhancedPairsTradingStrategy
from tests.unit.strategies.test_regime_aware_helpers import (
    create_mock_regime_engine,
    create_regime_context_mock,
    get_regime_config
)

class TestPairsTradingRegimeAwareness:
    """Test pairs trading strategy regime awareness"""

    @pytest.fixture
    def strategy(self):
        """Create pairs trading strategy instance"""
        config = PairsConfig(name='test_pairs')
        strategy = EnhancedPairsTradingStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_set_regime_engine(self, strategy):
        """Test regime engine injection"""
        await strategy.initialize()

        regime_engine = create_mock_regime_engine('normal_volatility', 'normal', 'sideways')
        strategy.set_regime_engine(regime_engine)

        assert strategy.regime_engine == regime_engine
        assert strategy.validate_regime_dependency() is True

    @pytest.mark.asyncio
    async def test_sideways_regime_favorable(self, strategy):
        """Test that sideways regime is favorable for pairs trading"""
        await strategy.initialize()

        # Sideways regime (favorable for mean reversion strategies like pairs)
        regime_context = create_regime_context_mock('normal_volatility', 'normal', 'sideways')
        await strategy.on_regime_change(regime_context)

        assert strategy._current_regime_context.trend_regime == 'sideways'

    @pytest.mark.asyncio
    async def test_regime_adaptation(self, strategy):
        """Test regime adaptation"""
        await strategy.initialize()

        regime_config = get_regime_config('sideways')
        regime_context = create_regime_context_mock(**regime_config)

        adaptation_result = await strategy.adapt_to_regime(regime_context)

        assert adaptation_result['adapted'] is True

