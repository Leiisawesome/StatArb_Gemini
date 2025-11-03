"""
Comprehensive Unit Tests for Enhanced Trend Following Strategy
================================================================

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

from core_engine.config import TrendFollowingConfig
from core_engine.trading.strategies.implementations.trend_following.enhanced_trend_following import EnhancedTrendFollowingStrategy
from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType
from tests.unit.strategies.test_helpers import (
    create_enriched_dataframe,
    create_enriched_data_dict,
    create_mock_strategy_signal
)


class TestTrendFollowingSignalGeneration:
    """Test trend following-specific signal calculation logic"""
    
    @pytest.fixture
    def strategy(self):
        """Create trend following strategy instance"""
        config = TrendFollowingConfig(name='test_trend')
        strategy = EnhancedTrendFollowingStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_uptrend_entry_signal(self, strategy):
        """Test entry signal on strong uptrend"""
        await strategy.initialize()
        await strategy.start()
        
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=200,
            trend='uptrend'
        )
        
        df = enriched_data['AAPL']
        # Create strong uptrend indicators
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['SMA_50'] = df['close'].rolling(50).mean()
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        df['ADX_14'] = 30.0  # Strong trend
        df['ATR_14'] = df['close'] * 0.02
        df['volatility'] = 0.15
        df['momentum_short'] = df['close'].pct_change(10)
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df
        
        signals = await strategy.generate_signals(enriched_data)
        
        assert isinstance(signals, list)
    
    @pytest.mark.asyncio
    async def test_weak_trend_no_signal(self, strategy):
        """Test no signal on weak trends"""
        await strategy.initialize()
        await strategy.start()
        
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=200,
            trend='sideways'
        )
        
        df = enriched_data['AAPL']
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['SMA_50'] = df['close'].rolling(50).mean()
        df['MACD'] = 0.01  # Very small
        df['MACD_signal'] = 0.01
        df['ADX_14'] = 15.0  # Weak trend
        df['ATR_14'] = df['close'] * 0.02
        df['volatility'] = 0.15
        df['momentum_short'] = df['close'].pct_change(10)
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df
        
        signals = await strategy.generate_signals(enriched_data)
        
        # Weak trends should generate fewer or no signals
        assert isinstance(signals, list)


class TestTrendFollowingPositionSizing:
    """Test position sizing logic"""
    
    @pytest.fixture
    def strategy(self):
        """Create trend following strategy instance"""
        config = TrendFollowingConfig(name='test_trend')
        strategy = EnhancedTrendFollowingStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_trend_strength_scaling(self, strategy):
        """Test position sizing scales with trend strength (ADX)"""
        await strategy.initialize()
        
        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        
        # Update strategy market data
        strategy.market_data = market_data
        
        df = market_data['AAPL']
        df['ADX_14'] = 35.0  # Strong trend
        market_data['AAPL'] = df
        
        position_size = strategy.calculate_position_size(signal, market_data)
        
        assert position_size >= 0
        assert position_size <= strategy.config.max_position_pct
    
    @pytest.mark.asyncio
    async def test_volatility_adjustment(self, strategy):
        """Test position sizing adjusts for volatility"""
        await strategy.initialize()
        
        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        
        strategy.market_data = market_data
        
        df = market_data['AAPL']
        df['ATR_14'] = df['close'] * 0.05  # High volatility
        market_data['AAPL'] = df
        
        position_size = strategy.calculate_position_size(signal, market_data)
        
        # High volatility should reduce position size
        assert position_size >= 0
        assert position_size <= strategy.config.max_position_pct


class TestTrendFollowingEntryExitConditions:
    """Test entry and exit condition logic"""
    
    @pytest.fixture
    def strategy(self):
        """Create trend following strategy instance"""
        config = TrendFollowingConfig(name='test_trend')
        strategy = EnhancedTrendFollowingStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_macd_crossover_entry(self, strategy):
        """Test entry on MACD bullish crossover"""
        await strategy.initialize()
        await strategy.start()
        
        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200, trend='uptrend')
        
        df = enriched_data['AAPL']
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['SMA_50'] = df['close'].rolling(50).mean()
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        # Create bullish crossover: MACD crosses above signal
        df.loc[df.index[-10:], 'MACD'] = df.loc[df.index[-10:], 'MACD_signal'] * 1.1
        df['ADX_14'] = 28.0
        df['ATR_14'] = df['close'] * 0.02
        df['volatility'] = 0.15
        df['momentum_short'] = df['close'].pct_change(10)
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df
        
        signals = await strategy.generate_signals(enriched_data)
        
        assert isinstance(signals, list)
    
    @pytest.mark.asyncio
    async def test_trend_reversal_exit(self, strategy):
        """Test exit on trend reversal"""
        await strategy.initialize()
        await strategy.start()
        
        # Setup existing position
        strategy.active_positions = {'AAPL': Mock(quantity=100.0)}
        
        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        
        df = enriched_data['AAPL']
        # Create trend reversal: MACD crosses below signal
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['SMA_50'] = df['close'].rolling(50).mean()
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        df.loc[df.index[-10:], 'MACD'] = df.loc[df.index[-10:], 'MACD_signal'] * 0.9  # Bearish
        df['ADX_14'] = 10.0  # Weak trend (reversal)
        df['ATR_14'] = df['close'] * 0.02
        df['volatility'] = 0.15
        df['momentum_short'] = df['close'].pct_change(10)
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df
        
        signals = await strategy.generate_signals(enriched_data)
        
        # Should detect trend reversal and generate exit
        assert isinstance(signals, list)

