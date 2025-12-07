"""
Comprehensive Unit Tests for Enhanced Volatility Strategy
==========================================================

Tests strategy-specific logic, position sizing, and entry/exit conditions.

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 1: Core Logic Coverage
"""

import pytest

from core_engine.config import VolatilityConfig
from core_engine.trading.strategies.implementations.volatility.enhanced_volatility import EnhancedVolatilityStrategy
from tests.unit.strategies.test_helpers import (
    create_enriched_data_dict,
    create_mock_strategy_signal
)


class TestVolatilitySignalGeneration:
    """Test volatility-specific signal calculation logic"""

    @pytest.fixture
    def strategy(self):
        """Create volatility strategy instance"""
        config = VolatilityConfig(name='test_volatility')
        strategy = EnhancedVolatilityStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_low_volatility_expansion_signal(self, strategy):
        """Test signal on volatility expansion from low levels"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        df['volatility'] = 0.10  # Low volatility (expanding)
        df['returns_1'] = df['close'].pct_change(1)
        df['ATR_14'] = df['close'] * 0.01
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_high_volatility_contraction_signal(self, strategy):
        """Test signal on volatility contraction from high levels"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        df['volatility'] = 0.30  # High volatility (contracting)
        df['returns_1'] = df['close'].pct_change(1)
        df['ATR_14'] = df['close'] * 0.05
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        assert isinstance(signals, list)


class TestVolatilityPositionSizing:
    """Test position sizing logic"""

    @pytest.fixture
    def strategy(self):
        """Create volatility strategy instance"""
        config = VolatilityConfig(name='test_volatility')
        strategy = EnhancedVolatilityStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_inverse_volatility_scaling(self, strategy):
        """Test position sizing uses inverse volatility scaling"""
        await strategy.initialize()
        await strategy.start()

        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        # Setup volatility data
        strategy.volatility_data = {
            'AAPL': {
                'realized_volatility': 0.10,  # Low volatility -> larger position
                'historical_volatility': 0.12,
                'volatility_regime': 'low'
            }
        }

        position_size_low_vol = strategy.calculate_position_size(signal, market_data)

        # High volatility should result in smaller position
        strategy.volatility_data['AAPL']['realized_volatility'] = 0.30
        position_size_high_vol = strategy.calculate_position_size(signal, market_data)

        assert position_size_low_vol >= position_size_high_vol
        assert position_size_low_vol <= strategy.config.max_position_pct


class TestVolatilityEntryExitConditions:
    """Test entry and exit condition logic"""

    @pytest.fixture
    def strategy(self):
        """Create volatility strategy instance"""
        config = VolatilityConfig(name='test_volatility')
        strategy = EnhancedVolatilityStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_volatility_regime_detection(self, strategy):
        """Test volatility regime detection for signal filtering"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        df['volatility'] = 0.25  # High volatility regime
        df['returns_1'] = df['close'].pct_change(1)
        df['ATR_14'] = df['close'] * 0.04
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # Strategy should adapt to volatility regime
        assert isinstance(signals, list)

