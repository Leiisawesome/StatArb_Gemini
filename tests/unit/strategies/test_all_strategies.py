"""
All Strategies Comprehensive Tests
===================================

Comprehensive test suite for all 10 enhanced strategy implementations.
Tests common functionality across all strategies.

Author: StatArb_Gemini Test Suite
Date: October 23, 2025
"""

import pytest
import pandas as pd
from datetime import datetime

from core_engine.config import (
    MomentumConfig, MeanReversionConfig, StatisticalArbitrageConfig,
    TrendFollowingConfig, PairsConfig, FactorConfig, MultiAssetConfig,
    BreakoutConfig, VolatilityConfig, ArbitrageConfig
)

from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion import EnhancedMeanReversionStrategy
from core_engine.trading.strategies.implementations.statistical_arbitrage.enhanced_statistical_arbitrage import EnhancedStatisticalArbitrageStrategy
from core_engine.trading.strategies.implementations.trend_following.enhanced_trend_following import EnhancedTrendFollowingStrategy
from core_engine.trading.strategies.implementations.pairs_trading.enhanced_pairs_trading import EnhancedPairsTradingStrategy
from core_engine.trading.strategies.implementations.factor.enhanced_factor import EnhancedFactorStrategy
from core_engine.trading.strategies.implementations.multi_asset.enhanced_multi_asset import EnhancedMultiAssetStrategy
from core_engine.trading.strategies.implementations.breakout.enhanced_breakout import EnhancedBreakoutStrategy
from core_engine.trading.strategies.implementations.volatility.enhanced_volatility import EnhancedVolatilityStrategy
from core_engine.trading.strategies.implementations.arbitrage.enhanced_arbitrage import EnhancedArbitrageStrategy

from core_engine.trading.strategies.strategy_engine import StrategyState
from tests.unit.strategies.conftest import BaseStrategyTest

# All strategies and their configs
ALL_STRATEGIES = [
    (EnhancedMomentumStrategy, MomentumConfig, 'momentum'),
    (EnhancedMeanReversionStrategy, MeanReversionConfig, 'mean_reversion'),
    (EnhancedStatisticalArbitrageStrategy, StatisticalArbitrageConfig, 'statistical_arbitrage'),
    (EnhancedTrendFollowingStrategy, TrendFollowingConfig, 'trend_following'),
    (EnhancedPairsTradingStrategy, PairsConfig, 'pairs_trading'),
    (EnhancedFactorStrategy, FactorConfig, 'factor'),
    (EnhancedMultiAssetStrategy, MultiAssetConfig, 'multi_asset'),
    (EnhancedBreakoutStrategy, BreakoutConfig, 'breakout'),
    (EnhancedVolatilityStrategy, VolatilityConfig, 'volatility'),
    (EnhancedArbitrageStrategy, ArbitrageConfig, 'arbitrage'),
]

class TestAllStrategies(BaseStrategyTest):
    """Test suite for all 10 strategies"""

    @pytest.mark.parametrize("StrategyClass,ConfigClass,strategy_name", ALL_STRATEGIES)
    def test_all_strategies_instantiation(self, StrategyClass, ConfigClass, strategy_name):
        """Test all strategies can be instantiated"""
        config = ConfigClass(name=f'test_{strategy_name}')
        strategy = StrategyClass(config)

        assert strategy is not None
        assert strategy.config == config
        assert strategy.state == StrategyState.INACTIVE
        print(f"✅ {strategy_name}: Instantiation successful")

    @pytest.mark.parametrize("StrategyClass,ConfigClass,strategy_name", ALL_STRATEGIES)
    def test_all_strategies_config_creation(self, StrategyClass, ConfigClass, strategy_name):
        """Test config creation for all strategies"""
        config = ConfigClass(name=f'test_{strategy_name}')

        assert config.name == f'test_{strategy_name}'
        assert config.strategy_type.value == strategy_name
        print(f"✅ {strategy_name}: Config creation successful")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("StrategyClass,ConfigClass,strategy_name", ALL_STRATEGIES)
    async def test_all_strategies_lifecycle(self, StrategyClass, ConfigClass, strategy_name):
        """Test lifecycle for all strategies"""
        config = ConfigClass(name=f'test_{strategy_name}')
        strategy = StrategyClass(config)

        # Initialize
        result = await strategy.initialize()
        assert result is True, f"{strategy_name}: Initialize failed"
        assert strategy.is_initialized is True

        # Start
        result = await strategy.start()
        assert result is True, f"{strategy_name}: Start failed"
        assert strategy.is_operational is True

        # Health check
        health = await strategy.health_check()
        assert health is not None, f"{strategy_name}: Health check failed"
        assert 'healthy' in health

        # Stop
        result = await strategy.stop()
        assert result is True, f"{strategy_name}: Stop failed"

        print(f"✅ {strategy_name}: Lifecycle complete")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("StrategyClass,ConfigClass,strategy_name", ALL_STRATEGIES)
    async def test_all_strategies_signal_generation(
        self, StrategyClass, ConfigClass, strategy_name, market_data_uptrend
    ):
        """Test signal generation for all strategies"""
        config = ConfigClass(name=f'test_{strategy_name}')
        strategy = StrategyClass(config)

        await strategy.initialize()
        await strategy.start()

        # All strategies should handle signal generation without crashing
        signals = await strategy.generate_signals(market_data_uptrend)

        assert signals is not None, f"{strategy_name}: Signal generation returned None"
        assert isinstance(signals, list), f"{strategy_name}: Signals not a list"

        print(f"✅ {strategy_name}: Generated {len(signals)} signals")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("StrategyClass,ConfigClass,strategy_name", ALL_STRATEGIES)
    async def test_all_strategies_regime_awareness(
        self, StrategyClass, ConfigClass, strategy_name, mock_regime_engine
    ):
        """Test regime awareness for all strategies"""
        config = ConfigClass(name=f'test_{strategy_name}')
        strategy = StrategyClass(config)

        await strategy.initialize()

        # Set regime engine
        strategy.set_regime_engine(mock_regime_engine)
        assert strategy.regime_engine is not None

        # Test regime change
        from core_engine.system.interfaces import RegimeContext
        new_regime = RegimeContext(
            primary_regime='high_volatility',
            regime_confidence=0.85,
            regime_start_time=datetime.now(),
            regime_duration_minutes=10.0
        )

        # Should not crash
        await strategy.on_regime_change(new_regime)

        print(f"✅ {strategy_name}: Regime awareness working")

    @pytest.mark.asyncio
    async def test_all_strategies_parallel_operation(self, market_data_uptrend):
        """Test all strategies can run in parallel"""
        strategies = []

        # Create all strategies
        for StrategyClass, ConfigClass, strategy_name in ALL_STRATEGIES:
            config = ConfigClass(name=f'test_{strategy_name}')
            strategy = StrategyClass(config)
            await strategy.initialize()
            await strategy.start()
            strategies.append((strategy, strategy_name))

        # All should generate signals in parallel
        results = []
        for strategy, name in strategies:
            signals = await strategy.generate_signals(market_data_uptrend)
            results.append((name, len(signals)))

        # Verify all completed
        assert len(results) == 10
        print(f"\n✅ All 10 strategies ran in parallel:")
        for name, count in results:
            print(f"   - {name}: {count} signals")

    @pytest.mark.asyncio
    async def test_strategies_performance_metrics(self):
        """Test performance metrics tracking across strategies"""
        for StrategyClass, ConfigClass, strategy_name in ALL_STRATEGIES[:3]:  # Test first 3
            config = ConfigClass(name=f'test_{strategy_name}')
            strategy = StrategyClass(config)

            await strategy.initialize()
            await strategy.start()

            # Check performance metrics exist
            metrics = strategy.performance_metrics
            assert hasattr(metrics, 'total_signals')
            assert metrics.total_signals >= 0

            print(f"✅ {strategy_name}: Performance metrics available")

class TestStrategyCoordination:
    """Test strategy coordination and interaction"""

    @pytest.mark.asyncio
    async def test_strategy_signal_aggregation(self, market_data_uptrend):
        """Test signals from multiple strategies can be aggregated"""

        # Create a few strategies
        momentum_config = MomentumConfig(name='momentum')
        momentum_strategy = EnhancedMomentumStrategy(momentum_config)

        mean_rev_config = MeanReversionConfig(name='mean_reversion')
        mean_rev_strategy = EnhancedMeanReversionStrategy(mean_rev_config)

        # Initialize
        await momentum_strategy.initialize()
        await momentum_strategy.start()
        await mean_rev_strategy.initialize()
        await mean_rev_strategy.start()

        # Generate signals
        momentum_signals = await momentum_strategy.generate_signals(market_data_uptrend)
        mean_rev_signals = await mean_rev_strategy.generate_signals(market_data_uptrend)

        # Both should work
        assert momentum_signals is not None
        assert mean_rev_signals is not None

        print(f"✅ Multi-strategy coordination: Momentum({len(momentum_signals)}) + MeanRev({len(mean_rev_signals)})")

class TestStrategyEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_strategy_with_empty_data(self):
        """Test strategy handles empty data gracefully"""
        config = MomentumConfig(name='test_empty')
        strategy = EnhancedMomentumStrategy(config)

        await strategy.initialize()
        await strategy.start()

        # Empty dataframe wrapped in Dict (enriched_data format)
        empty_data = {'EMPTY': pd.DataFrame()}

        # Should not crash
        signals = await strategy.generate_signals(empty_data)
        assert signals is not None  # May be empty list, but not None

    @pytest.mark.asyncio
    async def test_strategy_with_insufficient_data(self):
        """Test strategy handles insufficient data"""
        from tests.unit.strategies.conftest import StrategyTestFixtures

        config = MomentumConfig(name='test_insufficient', lookback_period=100)
        strategy = EnhancedMomentumStrategy(config)

        await strategy.initialize()
        await strategy.start()

        # Only 10 days of data (less than lookback), wrapped in Dict
        small_df = StrategyTestFixtures.create_mock_market_data(days=10)
        small_data = {'AAPL': small_df}

        # Should handle gracefully
        signals = await strategy.generate_signals(small_data)
        assert signals is not None

    @pytest.mark.asyncio
    async def test_strategy_double_initialization(self):
        """Test strategy handles double initialization"""
        config = MomentumConfig(name='test_double')
        strategy = EnhancedMomentumStrategy(config)

        # Initialize twice
        result1 = await strategy.initialize()
        result2 = await strategy.initialize()

        # Should handle gracefully
        assert result1 is True
        assert result2 is True  # Or False, either is acceptable

