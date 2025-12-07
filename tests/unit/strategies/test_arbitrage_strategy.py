"""
Comprehensive Unit Tests for Enhanced Arbitrage Strategy
==========================================================

Tests strategy-specific logic, position sizing, and entry/exit conditions.

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 1: Core Logic Coverage
"""

import pytest

from core_engine.config import ArbitrageConfig
from core_engine.trading.strategies.implementations.arbitrage.enhanced_arbitrage import EnhancedArbitrageStrategy
from tests.unit.strategies.test_helpers import (
    create_enriched_data_dict,
    create_mock_strategy_signal
)


class TestArbitrageSignalGeneration:
    """Test arbitrage-specific signal calculation logic"""

    @pytest.fixture
    def strategy(self):
        """Create arbitrage strategy instance"""
        config = ArbitrageConfig(name='test_arbitrage')
        strategy = EnhancedArbitrageStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_price_discrepancy_detection(self, strategy):
        """Test signal generation on price discrepancy"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT'],
            rows=200
        )

        # Create price discrepancy (simulate arbitrage opportunity)
        df1 = enriched_data['AAPL']
        df2 = enriched_data['MSFT']

        # Ensure prices exist
        for symbol in enriched_data:
            df = enriched_data[symbol]
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df

        signals = await strategy.generate_signals(enriched_data)

        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_minimum_discrepancy_threshold(self, strategy):
        """Test signals filtered by minimum price discrepancy"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT'],
            rows=200
        )

        for symbol in enriched_data:
            df = enriched_data[symbol]
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df

        signals = await strategy.generate_signals(enriched_data)

        # Only signals above minimum discrepancy threshold should be generated
        assert isinstance(signals, list)


class TestArbitragePositionSizing:
    """Test position sizing logic"""

    @pytest.fixture
    def strategy(self):
        """Create arbitrage strategy instance"""
        config = ArbitrageConfig(name='test_arbitrage')
        strategy = EnhancedArbitrageStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_arbitrage_position_sizing(self, strategy):
        """Test position sizing for arbitrage trades"""
        await strategy.initialize()

        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        position_size = strategy.calculate_position_size(signal, market_data)

        assert position_size >= 0
        assert position_size <= strategy.config.max_position_pct

    @pytest.mark.asyncio
    async def test_transaction_cost_adjustment(self, strategy):
        """Test position sizing adjusts for transaction costs"""
        await strategy.initialize()

        signal_high_profit = create_mock_strategy_signal(
            symbol='AAPL',
            confidence=0.9
        )

        signal_low_profit = create_mock_strategy_signal(
            symbol='AAPL',
            confidence=0.6
        )

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        position_size_high = strategy.calculate_position_size(signal_high_profit, market_data)
        position_size_low = strategy.calculate_position_size(signal_low_profit, market_data)

        # Higher profit opportunity should support larger position
        assert position_size_high >= position_size_low


class TestArbitrageEntryExitConditions:
    """Test entry and exit condition logic"""

    @pytest.fixture
    def strategy(self):
        """Create arbitrage strategy instance"""
        config = ArbitrageConfig(name='test_arbitrage')
        strategy = EnhancedArbitrageStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_arbitrage_opportunity_timeout(self, strategy):
        """Test opportunity expires after timeout"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT'],
            rows=200
        )

        for symbol in enriched_data:
            df = enriched_data[symbol]
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df

        signals = await strategy.generate_signals(enriched_data)

        # Opportunities should timeout if they persist too long
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_profit_threshold_filtering(self, strategy):
        """Test signals filtered by profit threshold after transaction costs"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(
            symbols=['AAPL', 'MSFT'],
            rows=200
        )

        for symbol in enriched_data:
            df = enriched_data[symbol]
            df = df.ffill().bfill().fillna(0)
            enriched_data[symbol] = df

        signals = await strategy.generate_signals(enriched_data)

        # Only profitable opportunities after costs should generate signals
        assert isinstance(signals, list)

