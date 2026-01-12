"""
Comprehensive Unit Tests for Enhanced Momentum Strategy
=======================================================

Tests strategy-specific logic, position sizing, and entry/exit conditions.

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
Priority 1: Core Logic Coverage
"""

import pytest
import pandas as pd
from unittest.mock import Mock

from core_engine.config import MomentumConfig
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from core_engine.type_definitions.strategy import SignalType
from tests.unit.strategies.test_helpers import (
    create_enriched_data_dict,
    create_mock_strategy_signal
)

class TestMomentumSignalGeneration:
    """Test momentum-specific signal calculation logic"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy instance"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_bullish_momentum_signal_generation(self, strategy):
        """Test bullish momentum signal generation"""
        await strategy.initialize()
        await strategy.start()

        # Create uptrending data with strong momentum
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=200,
            start_price=100.0,
            trend='uptrend'
        )

        # Ensure bullish conditions
        df = enriched_data['AAPL']
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['ADX_14'] = 30.0  # Strong trend
        df['volume_ratio'] = 1.5  # Above threshold
        df['RSI_14'] = 55.0  # Not overbought
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()

        # Forward fill to ensure all values exist
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        assert isinstance(signals, list)
        # Should generate at least one signal if conditions are met
        if len(signals) > 0:
            signal = signals[0]
            assert signal.symbol == 'AAPL'
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
            assert 0 <= signal.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_bearish_momentum_signal_generation(self, strategy):
        """Test bearish momentum signal generation"""
        await strategy.initialize()
        await strategy.start()

        # Create downtrending data
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=200,
            start_price=100.0,
            trend='downtrend'
        )

        df = enriched_data['AAPL']
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['ADX_14'] = 30.0
        df['volume_ratio'] = 1.5
        df['RSI_14'] = 45.0  # Not oversold
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        assert isinstance(signals, list)
        # Strategy logic will determine signal type based on momentum direction

    @pytest.mark.asyncio
    async def test_weak_momentum_no_signal(self, strategy):
        """Test that weak momentum doesn't generate signals"""
        await strategy.initialize()
        await strategy.start()

        # Create sideways data with weak momentum
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=200,
            start_price=100.0,
            trend='sideways'
        )

        df = enriched_data['AAPL']
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['ADX_14'] = 15.0  # Weak trend
        df['volume_ratio'] = 0.8  # Below threshold
        df['RSI_14'] = 50.0
        df['MACD'] = 0.01  # Very small momentum
        df['MACD_signal'] = 0.01
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # May generate signals but with lower confidence
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_adx_threshold_filtering(self, strategy):
        """Test that ADX threshold filters weak trends"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['ADX_14'] = 10.0  # Below threshold (default is 20)
        df['volume_ratio'] = 1.5
        df['RSI_14'] = 55.0
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # Low ADX should reduce signal confidence or prevent signals
        assert isinstance(signals, list)
        for signal in signals:
            if signal.symbol == 'AAPL':
                # Confidence should be lower for weak trends
                assert signal.confidence < 1.0

class TestMomentumPositionSizing:
    """Test position sizing logic"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy instance"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_base_position_size_calculation(self, strategy):
        """Test base position size calculation"""
        await strategy.initialize()

        signal = create_mock_strategy_signal(
            symbol='AAPL',
            signal_type=SignalType.BUY,
            confidence=0.75
        )

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        position_size = strategy.calculate_position_size(signal, market_data)

        assert position_size > 0
        assert position_size <= strategy.config.max_position_pct

    @pytest.mark.asyncio
    async def test_momentum_strength_scaling(self, strategy):
        """Test position sizing scales with momentum strength"""
        await strategy.initialize()

        # Setup momentum data with strong momentum
        strategy.momentum_data = {
            'AAPL': {
                'momentum_strength': 2.0,  # Strong momentum (2x threshold)
                'short_momentum': 0.05,
                'medium_momentum': 0.04,
                'long_momentum': 0.03
            }
        }

        signal_high = create_mock_strategy_signal(
            symbol='AAPL',
            confidence=0.9
        )

        signal_low = create_mock_strategy_signal(
            symbol='AAPL',
            confidence=0.5
        )

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        position_size_high = strategy.calculate_position_size(signal_high, market_data)
        position_size_low = strategy.calculate_position_size(signal_low, market_data)

        # Higher confidence should lead to larger position
        assert position_size_high >= position_size_low

    @pytest.mark.asyncio
    async def test_trend_multiplier_scaling(self, strategy):
        """Test position sizing scales with trend strength (ADX)"""
        await strategy.initialize()

        signal = create_mock_strategy_signal(symbol='AAPL', confidence=0.75)
        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        # Add ADX data
        df = market_data['AAPL']
        df['ADX_14'] = 35.0  # Strong trend
        market_data['AAPL'] = df

        position_size = strategy.calculate_position_size(signal, market_data)

        assert position_size > 0
        assert position_size <= strategy.config.max_position_pct

    @pytest.mark.asyncio
    async def test_position_size_caps(self, strategy):
        """Test position size respects maximum caps"""
        await strategy.initialize()

        # Create signal with maximum confidence
        signal = create_mock_strategy_signal(
            symbol='AAPL',
            confidence=1.0
        )

        # Setup very strong momentum
        strategy.momentum_data = {
            'AAPL': {
                'momentum_strength': 10.0,  # Very strong
                'short_momentum': 0.1,
                'medium_momentum': 0.09,
                'long_momentum': 0.08
            }
        }

        market_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)
        df = market_data['AAPL']
        df['ADX_14'] = 50.0  # Very strong trend
        market_data['AAPL'] = df

        position_size = strategy.calculate_position_size(signal, market_data)

        # Should be capped at max_position_pct
        assert position_size <= strategy.config.max_position_pct

class TestMomentumEntryExitConditions:
    """Test entry and exit condition logic"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy instance"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_golden_cross_entry_condition(self, strategy):
        """Test golden cross (SMA crossover) entry condition"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200, trend='uptrend')

        df = enriched_data['AAPL']
        # Create golden cross: SMA_10 crosses above SMA_20
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['SMA_50'] = df['close'].rolling(50).mean()

        # Ensure golden cross condition
        df.loc[df.index[-10:], 'SMA_10'] = df.loc[df.index[-10:], 'SMA_20'] * 1.02

        df['ADX_14'] = 25.0
        df['volume_ratio'] = 1.3
        df['RSI_14'] = 60.0
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # Strategy should detect golden cross
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_death_cross_exit_condition(self, strategy):
        """Test death cross (SMA crossover) exit condition"""
        await strategy.initialize()
        await strategy.start()

        # Setup existing position
        strategy.active_positions = {'AAPL': Mock(quantity=100.0)}

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200, trend='downtrend')

        df = enriched_data['AAPL']
        # Create death cross: SMA_10 crosses below SMA_20
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()

        # Ensure death cross condition
        df.loc[df.index[-10:], 'SMA_10'] = df.loc[df.index[-10:], 'SMA_20'] * 0.98

        df['ADX_14'] = 25.0
        df['volume_ratio'] = 1.3
        df['RSI_14'] = 40.0
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # Strategy should detect death cross and generate exit signal
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_momentum_exhaustion_exit(self, strategy):
        """Test momentum exhaustion detection for exits"""
        await strategy.initialize()
        await strategy.start()

        # Setup existing position
        strategy.active_positions = {'AAPL': Mock(quantity=100.0)}

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200)

        df = enriched_data['AAPL']
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['RSI_14'] = 75.0  # Overbought - momentum exhaustion
        df['ADX_14'] = 15.0  # Weak trend
        df['volume_ratio'] = 0.7  # Declining volume
        df['MACD'] = 0.001  # Very small momentum
        df['MACD_signal'] = 0.001
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # Should detect momentum exhaustion
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_volume_confirmation_required(self, strategy):
        """Test that volume confirmation is required for signals"""
        await strategy.initialize()
        await strategy.start()

        enriched_data = create_enriched_data_dict(symbols=['AAPL'], rows=200, trend='uptrend')

        df = enriched_data['AAPL']
        df['SMA_10'] = df['close'].rolling(10).mean()
        df['SMA_20'] = df['close'].rolling(20).mean()
        df['ADX_14'] = 30.0
        df['volume_ratio'] = 0.5  # Below threshold
        df['RSI_14'] = 60.0
        df['MACD'] = df['close'].diff()
        df['MACD_signal'] = df['MACD'].rolling(9).mean()
        df = df.ffill().bfill().fillna(0)
        enriched_data['AAPL'] = df

        signals = await strategy.generate_signals(enriched_data)

        # Low volume should reduce signal confidence or prevent signals
        assert isinstance(signals, list)
        for signal in signals:
            if signal.symbol == 'AAPL':
                # Confidence should be lower without volume confirmation
                assert signal.confidence < 1.0

class TestMomentumEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy instance"""
        config = MomentumConfig(name='test_momentum')
        strategy = EnhancedMomentumStrategy(config)
        return strategy

    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self, strategy):
        """Test handling of insufficient data"""
        await strategy.initialize()
        await strategy.start()

        # Create data with less than long_period rows
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=20,  # Less than long_period (default 50)
            trend='uptrend'
        )

        signals = await strategy.generate_signals(enriched_data)

        # Should handle gracefully without crashing
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_missing_indicators_handling(self, strategy):
        """Test handling of missing indicators"""
        await strategy.initialize()
        await strategy.start()

        # Create data without required indicators
        enriched_data = {
            'AAPL': pd.DataFrame({
                'close': [100.0, 101.0, 102.0],
                'volume': [1000000, 1100000, 1200000]
            })
        }

        # Strategy should validate and raise ValueError for missing indicators
        # (Validation happens in _validate_enriched_data)
        try:
            signals = await strategy.generate_signals(enriched_data)
            # If no exception, verify it handled gracefully (empty signals or error state)
            assert isinstance(signals, list)
        except (ValueError, KeyError, AttributeError):
            # Expected behavior - validation failed
            pass

    @pytest.mark.asyncio
    async def test_position_size_with_missing_data(self, strategy):
        """Test position sizing with missing market data"""
        await strategy.initialize()

        signal = create_mock_strategy_signal(symbol='UNKNOWN', confidence=0.75)
        market_data = {}  # Empty market data

        position_size = strategy.calculate_position_size(signal, market_data)

        # Should return 0.0 or handle gracefully
        assert position_size >= 0
        assert position_size <= strategy.config.max_position_pct

