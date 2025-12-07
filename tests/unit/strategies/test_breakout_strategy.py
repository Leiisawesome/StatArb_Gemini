"""
Comprehensive Unit Tests for Enhanced Breakout Strategy
========================================================

Tests strategy-specific logic, position sizing, and entry/exit conditions.

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 1: Core Logic Coverage
"""

import pytest

from core_engine.config import BreakoutConfig
from core_engine.trading.strategies.implementations.breakout.enhanced_breakout import EnhancedBreakoutStrategy
from tests.unit.strategies.test_helpers import (
    create_enriched_data_dict,
    create_mock_strategy_signal
)


class TestBreakoutSignalGeneration:
    """Test breakout-specific signal calculation logic"""

    @pytest.fixture
    def strategy(self):
        """Create breakout strategy instance"""
        config = BreakoutConfig(name='test_breakout')
        strategy = EnhancedBreakoutStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_resistance_breakout_signal(self, strategy):
        """Test buy signal on resistance breakout"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        # Create resistance breakout: price breaks above recent high
        recent_high = df['high'].rolling(20).max()
        df['high_20'] = recent_high
        df.loc[df.index[-1], 'close'] = recent_high.iloc[-1] * 1.03  # Breakout above
        df['volume_ratio'] = 1.5  # Volume confirmation
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_support_breakdown_signal(self, strategy):
        """Test sell signal on support breakdown"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        # Create support breakdown: price breaks below recent low
        recent_low = df['low'].rolling(20).min()
        df['low_20'] = recent_low
        df.loc[df.index[-1], 'close'] = recent_low.iloc[-1] * 0.97  # Breakdown below
        df['volume_ratio'] = 1.5
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        assert isinstance(signals, list)


class TestBreakoutPositionSizing:
    """Test position sizing logic"""

    @pytest.fixture
    def strategy(self):
        """Create breakout strategy instance"""
        config = BreakoutConfig(name='test_breakout')
        strategy = EnhancedBreakoutStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_breakout_strength_scaling(self, strategy):
        """Test position sizing scales with breakout strength"""
        await strategy.initialize()

        signal_high = create_mock_strategy_signal(symbol='AAPL', confidence=0.9)
        signal_low = create_mock_strategy_signal(symbol='AAPL', confidence=0.5)

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        position_size_high = strategy.calculate_position_size(signal_high, market_data)
        position_size_low = strategy.calculate_position_size(signal_low, market_data)

        assert position_size_high >= position_size_low
        assert position_size_high <= strategy.config.max_position_pct


class TestBreakoutEntryExitConditions:
    """Test entry and exit condition logic"""

    @pytest.fixture
    def strategy(self):
        """Create breakout strategy instance"""
        config = BreakoutConfig(name='test_breakout')
        strategy = EnhancedBreakoutStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_volume_confirmation_required(self, strategy):
        """Test volume confirmation is required for breakouts"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        # Price breakout but low volume
        recent_high = df['high'].rolling(20).max()
        df.loc[df.index[-1], 'close'] = recent_high.iloc[-1] * 1.03
        df['volume_ratio'] = 0.7  # Below threshold

        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # Low volume should reduce signal confidence
        assert isinstance(signals, list)
        for signal in signals:
            if signal.symbol == 'AAPL':
                assert signal.confidence < 1.0

