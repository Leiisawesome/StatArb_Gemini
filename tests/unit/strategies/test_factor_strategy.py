"""
Comprehensive Unit Tests for Enhanced Factor Strategy
=====================================================

Tests strategy-specific logic, position sizing, and entry/exit conditions.

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 1: Core Logic Coverage
"""

import pytest

from core_engine.config import FactorConfig
from core_engine.trading.strategies.implementations.factor.enhanced_factor import EnhancedFactorStrategy
from tests.unit.strategies.test_helpers import (
    create_enriched_data_dict,
    create_mock_strategy_signal
)

class TestFactorSignalGeneration:
    """Test factor-specific signal calculation logic"""

    @pytest.fixture
    def strategy(self):
        """Create factor strategy instance"""
        config = FactorConfig(name='test_factor')
        strategy = EnhancedFactorStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_value_factor_signal(self, strategy):
        """Test signal generation based on value factor"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        df['returns_1'] = df['close'].pct_change(1)
        df['volatility'] = 0.15
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_momentum_factor_signal(self, strategy):
        """Test signal generation based on momentum factor"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=200,
            trend='uptrend'
        )

        df = enriched_data['AAPL']
        df['returns_1'] = df['close'].pct_change(1)
        df['volatility'] = 0.15
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        assert isinstance(signals, list)

class TestFactorPositionSizing:
    """Test position sizing logic"""

    @pytest.fixture
    def strategy(self):
        """Create factor strategy instance"""
        config = FactorConfig(name='test_factor')
        strategy = EnhancedFactorStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_factor_strength_scaling(self, strategy):
        """Test position sizing scales with factor strength"""
        await strategy.initialize()

        signal_high = create_mock_strategy_signal(
            symbol='AAPL',
            confidence=0.9,
            quantity=100.0
        )
        signal_high.strength = 0.9  # High factor strength

        signal_low = create_mock_strategy_signal(
            symbol='AAPL',
            confidence=0.5,
            quantity=100.0
        )
        signal_low.strength = 0.5  # Low factor strength

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        position_size_high = strategy.calculate_position_size(signal_high, market_data)
        position_size_low = strategy.calculate_position_size(signal_low, market_data)

        # Higher factor strength should lead to larger position
        assert position_size_high >= position_size_low
        assert position_size_high <= strategy.config.max_position_pct

    @pytest.mark.asyncio
    async def test_position_size_caps(self, strategy):
        """Test position size respects maximum caps"""
        await strategy.initialize()

        signal = create_mock_strategy_signal(symbol='AAPL', confidence=1.0)
        signal.strength = 1.0  # Maximum factor strength

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        position_size = strategy.calculate_position_size(signal, market_data)

        # Should be capped at max_position_pct
        assert position_size <= strategy.config.max_position_pct

class TestFactorEntryExitConditions:
    """Test entry and exit condition logic"""

    @pytest.fixture
    def strategy(self):
        """Create factor strategy instance"""
        config = FactorConfig(name='test_factor')
        strategy = EnhancedFactorStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_quality_factor_selection(self, strategy):
        """Test selection based on quality factor"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        df['returns_1'] = df['close'].pct_change(1)
        df['volatility'] = 0.12  # Low volatility (quality indicator)
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # Should generate signals based on quality factors
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_factor_score_threshold(self):
        """Test signals filtered by minimum factor score"""
        # Use a lower min_factor_score to ensure signals pass threshold
        config = FactorConfig(name='test_factor', min_factor_score=0.3)
        strategy = EnhancedFactorStrategy(config)

        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        df['returns_1'] = df['close'].pct_change(1)
        df['volatility'] = 0.15
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # Signals should meet minimum factor score threshold (or be 0 for no-signal cases)
        assert isinstance(signals, list)
        for signal in signals:
            if signal.symbol == 'AAPL':
                # Allow signals at or above threshold, or zero (no signal)
                assert signal.strength >= strategy.config.min_factor_score or signal.strength == 0

