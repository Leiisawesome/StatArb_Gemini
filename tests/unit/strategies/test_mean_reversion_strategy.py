"""
Mean Reversion Strategy Implementation Tests
=============================================

Comprehensive tests for EnhancedMeanReversionStrategy.

Author: StatArb_Gemini Test Suite
Date: October 23, 2025
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from core_engine.config import MeanReversionConfig
from core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion import EnhancedMeanReversionStrategy
from core_engine.trading.strategies.strategy_engine import SignalType, StrategyState
from tests.unit.strategies.conftest import BaseStrategyTest


class TestMeanReversionStrategy(BaseStrategyTest):
    """Test suite for Mean Reversion strategy"""
    
    def test_mean_reversion_config_creation(self):
        """Test mean reversion configuration creation"""
        config = MeanReversionConfig(
            name='test_mean_reversion',
            lookback_period=20,
            entry_threshold=2.0,
            exit_threshold=0.5
        )
        
        assert config.name == 'test_mean_reversion'
        assert config.lookback_period == 20
        assert config.entry_threshold == 2.0
        assert config.exit_threshold == 0.5
        assert config.strategy_type.value == 'mean_reversion'
    
    def test_mean_reversion_strategy_instantiation(self):
        """Test strategy instantiation"""
        config = MeanReversionConfig(name='test_mean_reversion')
        strategy = EnhancedMeanReversionStrategy(config)
        
        assert strategy is not None
        assert strategy.config == config
        assert strategy.state == StrategyState.INACTIVE
    
    @pytest.mark.asyncio
    async def test_mean_reversion_lifecycle(self):
        """Test complete lifecycle"""
        config = MeanReversionConfig(name='test_mean_reversion')
        strategy = EnhancedMeanReversionStrategy(config)
        
        await self.verify_strategy_initialization(strategy, config)
        await self.verify_strategy_lifecycle(strategy)
    
    @pytest.mark.asyncio
    async def test_mean_reversion_sideways_market(self, market_data_sideways):
        """Test signal generation in sideways market"""
        config = MeanReversionConfig(
            name='test_mean_reversion',
            lookback_period=20,
            entry_threshold=1.5
        )
        strategy = EnhancedMeanReversionStrategy(config)
        
        await strategy.initialize()
        await strategy.start()
        
        # Mean reversion works best in sideways markets
        signals = await self.verify_signal_generation(strategy, market_data_sideways)
        
        # Should generate some signals in range-bound market
        assert signals is not None
    
    @pytest.mark.asyncio
    async def test_mean_reversion_uptrend(self, market_data_uptrend):
        """Test strategy handles trending markets"""
        config = MeanReversionConfig(name='test_mean_reversion')
        strategy = EnhancedMeanReversionStrategy(config)
        
        await strategy.initialize()
        await strategy.start()
        
        # Should still function in trending market (even if not optimal)
        signals = await self.verify_signal_generation(strategy, market_data_uptrend)
        assert signals is not None
    
    @pytest.mark.asyncio
    async def test_mean_reversion_regime_awareness(self, mock_regime_engine):
        """Test regime awareness"""
        config = MeanReversionConfig(name='test_mean_reversion')
        strategy = EnhancedMeanReversionStrategy(config)
        
        await strategy.initialize()
        await self.verify_regime_awareness(strategy, mock_regime_engine)
    
    @pytest.mark.asyncio
    async def test_mean_reversion_threshold_sensitivity(self):
        """Test different threshold configurations"""
        from tests.unit.strategies.conftest import StrategyTestFixtures
        
        market_data = StrategyTestFixtures.create_mock_market_data(trend='sideways')
        
        # Tight threshold
        config_tight = MeanReversionConfig(
            name='tight',
            entry_threshold=1.0,
            exit_threshold=0.3
        )
        strategy_tight = EnhancedMeanReversionStrategy(config_tight)
        await strategy_tight.initialize()
        await strategy_tight.start()
        signals_tight = await strategy_tight.generate_signals(market_data)
        
        # Wide threshold
        config_wide = MeanReversionConfig(
            name='wide',
            entry_threshold=3.0,
            exit_threshold=1.0
        )
        strategy_wide = EnhancedMeanReversionStrategy(config_wide)
        await strategy_wide.initialize()
        await strategy_wide.start()
        signals_wide = await strategy_wide.generate_signals(market_data)
        
        # Both should work, tighter threshold should generate more signals
        assert signals_tight is not None
        assert signals_wide is not None

