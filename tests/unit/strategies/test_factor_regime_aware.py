"""
Regime-Aware Tests for Enhanced Factor Strategy
================================================

Tests strategy adaptation to different market regimes (Priority 2).

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 2: Regime-Aware Testing
"""

import pytest
from core_engine.config import FactorConfig
from core_engine.trading.strategies.implementations.factor.enhanced_factor import EnhancedFactorStrategy
from tests.unit.strategies.test_regime_aware_helpers import (
    create_mock_regime_engine,
    create_regime_context_mock,
    get_regime_config
)

class TestFactorRegimeAwareness:
    """Test factor strategy regime awareness"""

    @pytest.fixture
    def strategy(self):
        """Create factor strategy instance"""
        config = FactorConfig(name='test_factor')
        strategy = EnhancedFactorStrategy(config)
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
    async def test_regime_affects_factor_weights(self, strategy):
        """Test that regime affects factor weighting"""
        await strategy.initialize()

        regime_context = create_regime_context_mock('high_volatility', 'high', 'choppy')
        await strategy.on_regime_change(regime_context)

        # Factor strategy may adjust factor weights based on regime
        assert strategy._current_regime_context.volatility_regime == 'high'

    @pytest.mark.asyncio
    async def test_regime_adaptation(self, strategy):
        """Test regime adaptation"""
        await strategy.initialize()

        regime_config = get_regime_config('normal_volatility')
        regime_context = create_regime_context_mock(**regime_config)

        adaptation_result = await strategy.adapt_to_regime(regime_context)

        assert adaptation_result['adapted'] is True

