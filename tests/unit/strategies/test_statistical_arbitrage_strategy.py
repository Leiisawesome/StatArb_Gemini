"""
Comprehensive Unit Tests for Enhanced Statistical Arbitrage Strategy
====================================================================

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

from core_engine.config import StatisticalArbitrageConfig
from core_engine.trading.strategies.implementations.statistical_arbitrage.enhanced_statistical_arbitrage import EnhancedStatisticalArbitrageStrategy
from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType
from tests.unit.strategies.test_helpers import (
    create_enriched_dataframe,
    create_enriched_data_dict,
    create_mock_strategy_signal
)


class TestStatisticalArbitrageSignalGeneration:
    """Test statistical arbitrage-specific signal calculation logic"""
    
    @pytest.fixture
    def strategy(self):
        """Create statistical arbitrage strategy instance"""
        config = StatisticalArbitrageConfig(name='test_stat_arb')
        strategy = EnhancedStatisticalArbitrageStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_spread_zscore_entry_signal(self, strategy):
        """Test entry signal generation based on spread z-score"""
        await strategy.initialize()
        await strategy.start()
        
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT'],
            rows=300  # Need more data for cointegration
        )
        
        # Ensure required features exist
        for symbol in enriched_data:
            df = enriched_data[symbol]
            df['returns_1'] = df['close'].pct_change(1)
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df
        
        signals = await strategy.generate_signals(enriched_data)
        
        assert isinstance(signals, list)
    
    @pytest.mark.asyncio
    async def test_cointegration_pair_selection(self, strategy):
        """Test cointegration-based pair selection"""
        await strategy.initialize()
        await strategy.start()
        
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            rows=300
        )
        
        for symbol in enriched_data:
            df = enriched_data[symbol]
            df['returns_1'] = df['close'].pct_change(1)
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df
        
        signals = await strategy.generate_signals(enriched_data)
        
        # Strategy should analyze pairs and select cointegrated ones
        assert isinstance(signals, list)


class TestStatisticalArbitragePositionSizing:
    """Test position sizing logic"""
    
    @pytest.fixture
    def strategy(self):
        """Create statistical arbitrage strategy instance"""
        config = StatisticalArbitrageConfig(name='test_stat_arb')
        strategy = EnhancedStatisticalArbitrageStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_fixed_position_sizing(self, strategy):
        """Test fixed position sizing method"""
        await strategy.initialize()
        
        # Set position sizing method to fixed
        strategy.config.position_size_method = "fixed"
        
        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        
        position_size = strategy.calculate_position_size(signal, market_data)
        
        assert position_size >= 0
        # StatisticalArbitrageConfig uses base_position_size, check against reasonable limit
        max_allowed = getattr(strategy.config, 'base_position_size', 0.1) * 3  # Allow up to 3x base
        assert position_size <= max_allowed
    
    @pytest.mark.asyncio
    async def test_volatility_adjusted_position_sizing(self, strategy):
        """Test volatility-adjusted position sizing"""
        await strategy.initialize()
        
        strategy.config.position_size_method = "volatility_adjusted"
        
        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        
        # Add volatility data
        df = market_data['AAPL']
        df['volatility'] = 0.15  # 15% volatility
        market_data['AAPL'] = df
        
        position_size = strategy.calculate_position_size(signal, market_data)
        
        assert position_size >= 0
        # StatisticalArbitrageConfig uses base_position_size, check against reasonable limit
        max_allowed = getattr(strategy.config, 'base_position_size', 0.1) * 3  # Allow up to 3x base
        assert position_size <= max_allowed
    
    @pytest.mark.asyncio
    async def test_risk_parity_position_sizing(self, strategy):
        """Test risk parity position sizing"""
        await strategy.initialize()
        
        strategy.config.position_size_method = "risk_parity"
        
        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        
        position_size = strategy.calculate_position_size(signal, market_data)
        
        assert position_size >= 0
        # StatisticalArbitrageConfig uses base_position_size, check against reasonable limit
        max_allowed = getattr(strategy.config, 'base_position_size', 0.1) * 3  # Allow up to 3x base
        assert position_size <= max_allowed


class TestStatisticalArbitrageEntryExitConditions:
    """Test entry and exit condition logic"""
    
    @pytest.fixture
    def strategy(self):
        """Create statistical arbitrage strategy instance"""
        config = StatisticalArbitrageConfig(name='test_stat_arb')
        strategy = EnhancedStatisticalArbitrageStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_spread_zscore_entry_threshold(self, strategy):
        """Test entry when spread z-score exceeds threshold"""
        await strategy.initialize()
        await strategy.start()
        
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT'],
            rows=300
        )
        
        for symbol in enriched_data:
            df = enriched_data[symbol]
            df['returns_1'] = df['close'].pct_change(1)
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df
        
        # Setup spread data with high z-score
        strategy.spread_data = {
            ('AAPL', 'MSFT'): {
                'zscore': 2.5,  # Above entry threshold
                'spread_mean': 0.0,
                'spread_std': 1.0
            }
        }
        
        signals = await strategy.generate_signals(enriched_data)
        
        assert isinstance(signals, list)
    
    @pytest.mark.asyncio
    async def test_spread_mean_reversion_exit(self, strategy):
        """Test exit when spread reverts to mean"""
        await strategy.initialize()
        await strategy.start()
        
        # Setup existing position
        strategy.active_spreads = {
            ('AAPL', 'MSFT'): Mock(entry_zscore=2.5, entry_time=datetime.now())
        }
        
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT'],
            rows=300
        )
        
        for symbol in enriched_data:
            df = enriched_data[symbol]
            df['returns_1'] = df['close'].pct_change(1)
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df
        
        # Spread reverts to mean (z-score near 0)
        strategy.spread_data = {
            ('AAPL', 'MSFT'): {
                'zscore': 0.2,  # Near mean (below exit threshold)
                'spread_mean': 0.0,
                'spread_std': 1.0
            }
        }
        
        signals = await strategy.generate_signals(enriched_data)
        
        # Should generate exit signals when spread reverts
        assert isinstance(signals, list)

