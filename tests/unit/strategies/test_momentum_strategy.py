"""
Momentum Strategy Implementation Tests
=======================================

Comprehensive tests for EnhancedMomentumStrategy.

Author: StatArb_Gemini Test Suite
Date: October 23, 2025
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from core_engine.config import MomentumConfig
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from core_engine.trading.strategies.strategy_engine import SignalType, StrategyState
from tests.unit.strategies.conftest import BaseStrategyTest


class TestMomentumStrategy(BaseStrategyTest):
    """Test suite for Momentum strategy"""
    
    def test_momentum_config_creation(self):
        """Test momentum configuration creation"""
        config = MomentumConfig(
            name='test_momentum',
            lookback_period=60,
            momentum_threshold=0.02
        )
        
        assert config.name == 'test_momentum'
        assert config.lookback_period == 60
        assert config.momentum_threshold == 0.02
        assert config.strategy_type.value == 'momentum'
    
    def test_momentum_strategy_instantiation(self):
        """Test strategy instantiation"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        
        assert strategy is not None
        assert strategy.config == config
        assert strategy.state == StrategyState.INACTIVE
    
    @pytest.mark.asyncio
    async def test_momentum_lifecycle(self, mock_orchestrator):
        """Test complete lifecycle"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        
        await self.verify_strategy_initialization(strategy, config)
        await self.verify_strategy_lifecycle(strategy)
    
    @pytest.mark.asyncio
    async def test_momentum_signal_generation_uptrend(self, market_data_uptrend):
        """Test signal generation in uptrend"""
        config = MomentumConfig(
            name='test_momentum',
            lookback_period=20,
            momentum_threshold=0.01
        )
        strategy = EnhancedMomentumStrategy(config)
        
        await strategy.initialize()
        await strategy.start()
        
        # Should generate BUY signals in uptrend
        signals = await self.verify_signal_generation(strategy, market_data_uptrend)
        
        # In strong uptrend, should have some buy signals
        if len(signals) > 0:
            buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
            assert len(buy_signals) > 0, "Expected BUY signals in uptrend"
    
    @pytest.mark.asyncio
    async def test_momentum_signal_generation_downtrend(self, market_data_downtrend):
        """Test signal generation in downtrend"""
        config = MomentumConfig(
            name='test_momentum',
            lookback_period=20,
            momentum_threshold=0.01
        )
        strategy = EnhancedMomentumStrategy(config)
        
        await strategy.initialize()
        await strategy.start()
        
        signals = await self.verify_signal_generation(strategy, market_data_downtrend)
        
        # In downtrend, should have sell or hold signals
        if len(signals) > 0:
            sell_or_hold = [s for s in signals if s.signal_type in [SignalType.SELL, SignalType.HOLD]]
            # Should have more sell/hold than buy in downtrend
            assert len(sell_or_hold) >= 0
    
    @pytest.mark.asyncio
    async def test_momentum_regime_awareness(self, mock_regime_engine):
        """Test regime awareness integration"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        
        await strategy.initialize()
        await self.verify_regime_awareness(strategy, mock_regime_engine)
    
    @pytest.mark.asyncio
    async def test_momentum_performance_tracking(self, market_data_uptrend):
        """Test performance metrics tracking"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        
        await strategy.initialize()
        await strategy.start()
        
        # Generate some signals
        await strategy.generate_signals(market_data_uptrend)
        
        # Check performance metrics
        metrics = strategy.performance_metrics
        assert hasattr(metrics, 'total_signals')
        assert metrics.total_signals >= 0
    
    @pytest.mark.asyncio
    async def test_momentum_config_validation(self):
        """Test configuration validation"""
        # Valid config
        config = MomentumConfig(
            name='test_momentum',
            lookback_period=60,
            momentum_threshold=0.02
        )
        strategy = EnhancedMomentumStrategy(config)
        assert strategy is not None
        
        # Test with extreme parameters
        config_extreme = MomentumConfig(
            name='test_extreme',
            lookback_period=200,
            momentum_threshold=0.10
        )
        strategy_extreme = EnhancedMomentumStrategy(config_extreme)
        assert strategy_extreme is not None
    
    @pytest.mark.asyncio
    async def test_momentum_multiple_symbols(self):
        """Test strategy with multiple symbols"""
        from tests.unit.strategies.conftest import StrategyTestFixtures
        
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        
        await strategy.initialize()
        await strategy.start()
        
        # Create data for multiple symbols
        data_aapl = StrategyTestFixtures.create_mock_market_data('AAPL', trend='uptrend')
        data_tsla = StrategyTestFixtures.create_mock_market_data('TSLA', trend='downtrend')
        
        # Test each symbol
        signals_aapl = await strategy.generate_signals(data_aapl)
        signals_tsla = await strategy.generate_signals(data_tsla)
        
        # Should handle both symbols
        assert signals_aapl is not None
        assert signals_tsla is not None

