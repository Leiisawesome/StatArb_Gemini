"""
Regime-Aware Tests for Enhanced Volatility Strategy
====================================================

Tests strategy adaptation to different market regimes (Priority 2).

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 2: Regime-Aware Testing
"""

import pytest
from core_engine.config import VolatilityConfig
from core_engine.trading.strategies.implementations.volatility.enhanced_volatility import EnhancedVolatilityStrategy
from tests.unit.strategies.test_regime_aware_helpers import (
    create_mock_regime_engine,
    create_regime_context_mock,
    get_regime_config
)


class TestVolatilityRegimeAwareness:
    """Test volatility strategy regime awareness"""

    @pytest.fixture
    def strategy(self):
        """Create volatility strategy instance"""
        config = VolatilityConfig(name='test_volatility')
        strategy = EnhancedVolatilityStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_set_regime_engine(self, strategy):
        """Test regime engine injection"""
        await strategy.initialize()

        regime_engine = create_mock_regime_engine('high_volatility', 'high', 'choppy')
        strategy.set_regime_engine(regime_engine)

        assert strategy.regime_engine == regime_engine
        assert strategy.validate_regime_dependency() is True

    @pytest.mark.asyncio
    async def test_volatility_regime_detection(self, strategy):
        """Test volatility regime detection affects strategy behavior"""
        await strategy.initialize()

        # High volatility regime
        regime_context = create_regime_context_mock('high_volatility', 'high', 'choppy')
        await strategy.on_regime_change(regime_context)

        assert strategy._current_regime_context.volatility_regime == 'high'

    @pytest.mark.asyncio
    async def test_volatility_expansion_detection(self, strategy):
        """Test volatility expansion from low to high"""
        await strategy.initialize()

        # Low volatility regime
        low_vol_regime = create_regime_context_mock('low_volatility', 'low', 'trending')
        await strategy.on_regime_change(low_vol_regime)

        # Transition to high volatility
        high_vol_regime = create_regime_context_mock('high_volatility', 'high', 'choppy')
        await strategy.on_regime_change(high_vol_regime)

        assert strategy._current_regime_context.volatility_regime == 'high'

    @pytest.mark.asyncio
    async def test_regime_adaptation(self, strategy):
        """Test regime adaptation"""
        await strategy.initialize()

        regime_config = get_regime_config('high_volatility')
        regime_context = create_regime_context_mock(**regime_config)

        adaptation_result = await strategy.adapt_to_regime(regime_context)

        assert adaptation_result['adapted'] is True

