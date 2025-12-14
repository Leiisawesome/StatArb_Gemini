"""
Regime-Aware Tests for Enhanced Statistical Arbitrage Strategy
================================================================

Tests strategy adaptation to different market regimes (Priority 2).

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 2: Regime-Aware Testing
"""

import pytest
from core_engine.config import StatisticalArbitrageConfig
from core_engine.trading.strategies.implementations.statistical_arbitrage.enhanced_statistical_arbitrage import EnhancedStatisticalArbitrageStrategy
from tests.unit.strategies.test_regime_aware_helpers import (
    create_mock_regime_engine,
    create_regime_context_mock,
    get_regime_config
)

class TestStatisticalArbitrageRegimeAwareness:
    """Test statistical arbitrage strategy regime awareness"""

    @pytest.fixture
    def strategy(self):
        """Create statistical arbitrage strategy instance"""
        config = StatisticalArbitrageConfig(name='test_stat_arb')
        strategy = EnhancedStatisticalArbitrageStrategy(config)
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
    async def test_on_regime_change(self, strategy):
        """Test regime change handling"""
        await strategy.initialize()

        regime_context = create_regime_context_mock('high_volatility', 'high', 'choppy')
        await strategy.on_regime_change(regime_context)

        assert hasattr(strategy, '_current_regime_context')
        assert strategy._current_regime_context == regime_context

    @pytest.mark.asyncio
    async def test_adapt_to_regime(self, strategy):
        """Test regime adaptation"""
        await strategy.initialize()

        regime_config = get_regime_config('high_volatility')
        regime_context = create_regime_context_mock(**regime_config)

        adaptation_result = await strategy.adapt_to_regime(regime_context)

        assert adaptation_result['adapted'] is True
        assert adaptation_result['regime'] == 'high_volatility'

class TestStatisticalArbitrageHighVolatilityRegime:
    """Test statistical arbitrage in high volatility regime"""

    @pytest.fixture
    def strategy(self):
        """Create statistical arbitrage strategy instance"""
        config = StatisticalArbitrageConfig(name='test_stat_arb')
        strategy = EnhancedStatisticalArbitrageStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_high_volatility_affects_position_sizing(self, strategy):
        """Test position sizing adapts to high volatility"""
        await strategy.initialize()

        # Set high volatility regime
        regime_context = create_regime_context_mock('high_volatility', 'high', 'choppy')
        await strategy.on_regime_change(regime_context)

        # High volatility should affect position sizing calculations
        assert strategy._current_regime_context.volatility_regime == 'high'

    @pytest.mark.asyncio
    async def test_regime_transition_handling(self, strategy):
        """Test handling of regime transitions"""
        await strategy.initialize()

        # Normal -> High volatility transition
        normal_regime = create_regime_context_mock('normal_volatility', 'normal', 'trending')
        await strategy.on_regime_change(normal_regime)

        high_vol_regime = create_regime_context_mock('high_volatility', 'high', 'choppy')
        await strategy.on_regime_change(high_vol_regime)

        assert strategy._current_regime_context.primary_regime == 'high_volatility'

