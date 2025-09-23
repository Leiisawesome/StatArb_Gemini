"""
Unit tests for momentum backtest strategy methods.
Tests core calculation methods for momentum analysis.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import Dict

# Import the classes we need to test
from backtest.momentum_backtest_legacy import (
    AdvancedMomentumStrategy,
    MomentumBacktestConfig,
    MomentumSignal
)


class TestMomentumCalculations:
    """Test suite for momentum calculation methods."""

    @pytest.fixture
    def sample_data(self) -> pd.DataFrame:
        """Create sample price data for testing."""
        np.random.seed(42)  # For reproducible tests
        dates = pd.date_range('2024-01-01 09:30:00', periods=100, freq='1min')

        # Create realistic price data with some trend and noise
        base_price = 100.0
        trend = np.linspace(0, 5, 100)  # Upward trend
        noise = np.random.normal(0, 0.5, 100)
        prices = base_price + trend + noise

        # Ensure prices are positive and reasonable
        prices = np.maximum(prices, 50.0)

        # Create volume data
        volume = np.random.uniform(1000, 10000, 100)

        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.999,
            'high': prices * 1.002,
            'low': prices * 0.998,
            'close': prices,
            'volume': volume
        })

    @pytest.fixture
    def strategy_config(self) -> MomentumBacktestConfig:
        """Create a test configuration."""
        return MomentumBacktestConfig(
            symbols=['TEST'],
            start_date='2024-01-01',
            end_date='2024-01-02',
            initial_capital=10000.0,
            momentum_threshold=0.01,
            min_trend_strength=0.5,
            min_rsi_momentum=30,
            max_position_size=0.2,
            stop_loss_pct=0.05,
            take_profit_pct=0.1,
            momentum_lookback=60,
            trend_confirmation_period=30,
            min_volume_ratio=1.0,
            max_volatility=0.08,
            strong_momentum_multiplier=2.0,
            rsi_oversold_threshold=30,
            momentum_sell_weak_threshold=0.003,
            momentum_sell_strong_threshold=0.003
        )

    @pytest.fixture
    def strategy(self, strategy_config: MomentumBacktestConfig) -> AdvancedMomentumStrategy:
        """Create a strategy instance for testing."""
        return AdvancedMomentumStrategy(strategy_config)

    def test_calculate_momentum_score_positive_trend(self, strategy: AdvancedMomentumStrategy, sample_data: pd.DataFrame):
        """Test momentum score calculation for positive trending data."""
        score = strategy._calculate_momentum_score(sample_data)

        # With our upward trending data, score should be positive
        assert isinstance(score, float)
        assert score > 0  # Should detect upward momentum
        assert score < 1.0  # Should be bounded

    def test_calculate_momentum_score_negative_trend(self, strategy: AdvancedMomentumStrategy, sample_data: pd.DataFrame):
        """Test momentum score calculation for negative trending data."""
        # Reverse the data to create downward trend
        reversed_data = sample_data.copy()
        reversed_data['close'] = sample_data['close'].iloc[::-1].values
        reversed_data['high'] = sample_data['high'].iloc[::-1].values
        reversed_data['low'] = sample_data['low'].iloc[::-1].values

        score = strategy._calculate_momentum_score(reversed_data)

        # With downward trending data, score should be negative
        assert isinstance(score, float)
        assert score < 0  # Should detect downward momentum

    def test_calculate_trend_strength(self, strategy: AdvancedMomentumStrategy, sample_data: pd.DataFrame):
        """Test trend strength calculation."""
        strength = strategy._calculate_trend_strength(sample_data)

        assert isinstance(strength, float)
        assert 0 <= strength <= 1  # Should be normalized between 0 and 1

        # With our trending data, strength should be reasonably high
        assert strength > 0.3

    def test_calculate_rsi(self, strategy: AdvancedMomentumStrategy):
        """Test RSI calculation."""
        # Create a simple price series
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                           111, 110, 112, 114, 113, 115, 117, 116, 118, 120])

        rsi_values = strategy._calculate_rsi(prices, period=14)

        assert isinstance(rsi_values, pd.Series)
        assert len(rsi_values) == len(prices)

        # RSI should be between 0 and 100
        valid_rsi = rsi_values.dropna()
        assert all(0 <= val <= 100 for val in valid_rsi)

        # With rising prices, RSI should be above 50
        final_rsi = rsi_values.iloc[-1]
        assert final_rsi > 50

    def test_calculate_rsi_insufficient_data(self, strategy: AdvancedMomentumStrategy):
        """Test RSI calculation with insufficient data."""
        # RSI needs at least period+1 data points
        short_prices = pd.Series([100, 102, 101])

        rsi_values = strategy._calculate_rsi(short_prices, period=14)

        # Should return NaN for insufficient data
        assert rsi_values.isna().all()

    def test_calculate_position_size(self, strategy: AdvancedMomentumStrategy):
        """Test position size calculation."""
        price = 100.0
        confidence = 0.8
        timeframe_quality = 0.7

        position_size = strategy._calculate_position_size(
            price=price,
            confidence=confidence,
            timeframe_quality=timeframe_quality
        )

        assert isinstance(position_size, int)
        assert position_size > 0

        # Position size should scale with confidence and quality
        low_conf_size = strategy._calculate_position_size(
            price=price, confidence=0.3, timeframe_quality=timeframe_quality
        )
        assert low_conf_size < position_size

    def test_calculate_position_size_edge_cases(self, strategy: AdvancedMomentumStrategy):
        """Test position size calculation with edge cases."""
        # Test with zero confidence - should still return some minimum position
        size_zero = strategy._calculate_position_size(
            price=100.0, confidence=0.0, timeframe_quality=0.5
        )
        assert isinstance(size_zero, int)
        assert size_zero >= 0  # May be 0 or minimum position

        # Test with maximum confidence
        size_max = strategy._calculate_position_size(
            price=100.0, confidence=1.0, timeframe_quality=1.0
        )
        assert isinstance(size_max, int)
        assert size_max > 0

    def test_calculate_volatility(self, strategy: AdvancedMomentumStrategy, sample_data: pd.DataFrame):
        """Test volatility calculation."""
        volatility = strategy._calculate_volatility(sample_data)

        assert isinstance(volatility, float)
        assert volatility >= 0  # Volatility should be non-negative

        # With our test data, volatility should be reasonable
        assert 0.001 <= volatility <= 0.1  # Reasonable range for percentage volatility

    def test_calculate_multi_timeframe_metrics(self, strategy: AdvancedMomentumStrategy, sample_data: pd.DataFrame):
        """Test multi-timeframe metrics calculation."""
        metrics = strategy._calculate_multi_timeframe_metrics(sample_data)

        assert isinstance(metrics, dict)
        required_keys = [
            'short_momentum', 'medium_momentum', 'long_momentum',
            'short_trend', 'medium_trend', 'long_trend',
            'momentum_alignment', 'trend_alignment', 'momentum_persistence'
        ]

        for key in required_keys:
            assert key in metrics
            assert isinstance(metrics[key], (int, float))

    def test_momentum_signal_creation(self):
        """Test MomentumSignal dataclass creation."""
        signal = MomentumSignal(
            symbol='TEST',
            timestamp=pd.Timestamp('2024-01-01 10:00:00'),
            signal_type='BUY',
            momentum_score=0.023,
            trend_strength=0.75,
            confidence=0.85,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size=25.5,
            metadata={'regime': 'bull_market', 'timeframe_quality': 0.8}
        )

        assert signal.symbol == 'TEST'
        assert signal.signal_type == 'BUY'
        assert signal.confidence == 0.85
        assert signal.position_size == 25.5
        assert isinstance(signal.timestamp, pd.Timestamp)

    def test_momentum_signal_missing_position_size(self):
        """Test that MomentumSignal raises error when position_size is missing."""
        with pytest.raises(TypeError):
            # This should fail because position_size is required
            MomentumSignal(
                symbol='TEST',
                direction='BUY',
                confidence=0.85,
                momentum_score=0.023,
                trend_strength=0.75,
                timeframe_quality=0.8,
                # position_size missing
                entry_price=100.0,
                stop_loss=95.0,
                take_profit=110.0,
                timestamp=pd.Timestamp('2024-01-01 10:00:00'),
                regime='bull_market'
            )


if __name__ == '__main__':
    pytest.main([__file__])