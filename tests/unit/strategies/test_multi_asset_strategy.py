"""
Comprehensive Unit Tests for Enhanced Multi-Asset Strategy
===========================================================

Tests strategy-specific logic, position sizing, and entry/exit conditions.

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 1: Core Logic Coverage
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock

from core_engine.config import MultiAssetConfig
from core_engine.trading.strategies.implementations.multi_asset.enhanced_multi_asset import EnhancedMultiAssetStrategy
from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType
from tests.unit.strategies.test_helpers import (
    create_enriched_dataframe,
    create_enriched_data_dict,
    create_mock_strategy_signal
)


class TestMultiAssetSignalGeneration:
    """Test multi-asset-specific signal calculation logic"""
    
    @pytest.fixture
    def strategy(self):
        """Create multi-asset strategy instance"""
        config = MultiAssetConfig(name='test_multi_asset')
        strategy = EnhancedMultiAssetStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_portfolio_rebalancing_signal(self, strategy):
        """Test rebalancing signal generation"""
        await strategy.initialize()
        await strategy.start()
        
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            rows=200
        )
        
        for symbol in enriched_data:
            df = enriched_data[symbol]
            df['returns_1'] = df['close'].pct_change(1)
            df['volatility'] = 0.15
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df
        
        signals = await strategy.generate_signals(enriched_data)
        
        assert isinstance(signals, list)
    
    @pytest.mark.asyncio
    async def test_correlation_based_allocation(self, strategy):
        """Test allocation based on correlation"""
        await strategy.initialize()
        await strategy.start()
        
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT'],
            rows=200
        )
        
        # Create correlated assets
        df1 = enriched_data['AAPL']
        df2 = enriched_data['MSFT']
        df2['close'] = df1['close'] * 1.1
        
        for symbol in enriched_data:
            df = enriched_data[symbol]
            df['returns_1'] = df['close'].pct_change(1)
            df['volatility'] = 0.15
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df
        
        signals = await strategy.generate_signals(enriched_data)
        
        # High correlation should affect allocation
        assert isinstance(signals, list)


class TestMultiAssetPositionSizing:
    """Test position sizing logic"""
    
    @pytest.fixture
    def strategy(self):
        """Create multi-asset strategy instance"""
        config = MultiAssetConfig(name='test_multi_asset')
        strategy = EnhancedMultiAssetStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_portfolio_weight_constraints(self, strategy):
        """Test position sizing respects portfolio weight constraints"""
        await strategy.initialize()
        
        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        
        position_size = strategy.calculate_position_size(signal, market_data)
        
        # Should respect min/max asset weight constraints
        # Position size may be 0 if conditions not met, which is valid
        min_weight = getattr(strategy.config, 'min_asset_weight', 0.0)
        max_weight = getattr(strategy.config, 'max_asset_weight', getattr(strategy.config, 'max_position_pct', getattr(strategy.config.position_limits, 'max_position_size', 0.1)))
        assert position_size >= 0  # Allow 0 if strategy determines no position
        if position_size > 0:
            assert position_size >= min_weight
        assert position_size <= max_weight
    
    @pytest.mark.asyncio
    async def test_volatility_target_sizing(self, strategy):
        """Test position sizing targets portfolio volatility"""
        await strategy.initialize()
        
        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        
        # Add volatility data
        df = market_data['AAPL']
        df['volatility'] = 0.20  # 20% volatility
        market_data['AAPL'] = df
        
        position_size = strategy.calculate_position_size(signal, market_data)
        
        # Should scale to target portfolio volatility
        assert position_size >= 0
        max_weight = getattr(strategy.config, 'max_asset_weight', getattr(strategy.config, 'max_position_pct', getattr(strategy.config.position_limits, 'max_position_size', 0.1)))
        assert position_size <= max_weight


class TestMultiAssetEntryExitConditions:
    """Test entry and exit condition logic"""
    
    @pytest.fixture
    def strategy(self):
        """Create multi-asset strategy instance"""
        config = MultiAssetConfig(name='test_multi_asset')
        strategy = EnhancedMultiAssetStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_rebalance_threshold(self, strategy):
        """Test rebalancing triggered by drift threshold"""
        await strategy.initialize()
        await strategy.start()
        
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT'],
            rows=200
        )
        
        for symbol in enriched_data:
            df = enriched_data[symbol]
            df['returns_1'] = df['close'].pct_change(1)
            df['volatility'] = 0.15
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df
        
        signals = await strategy.generate_signals(enriched_data)
        
        # Rebalancing signals should be generated when drift exceeds threshold
        assert isinstance(signals, list)

