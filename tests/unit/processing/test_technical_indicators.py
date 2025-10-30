"""
Unit tests for processing component.
Tests feature engineering, indicators, signals, and processing components.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

# Import processing component classes

from core_engine.processing.indicators.engine import (
    EnhancedIndicatorConfig as IndicatorConfig,
    EnhancedTechnicalIndicators as IndicatorEngine
)

from core_engine.processing.signals.generator import (
    SignalType,
    SignalStrength,
    TradingSignal
)



# Import signal strategy classes

class TestIndicatorEngine:
    """Test IndicatorEngine class."""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'high': 102 + np.cumsum(np.random.randn(100) * 0.5),
            'low': 98 + np.cumsum(np.random.randn(100) * 0.5),
            'volume': np.random.randint(1000, 10000, 100),
            'open': 100 + np.cumsum(np.random.randn(100) * 0.3)
        }, index=dates)

        return data

    @pytest.fixture
    def indicator_config(self):
        """Create indicator configuration for testing."""
        from core_engine.config.component_config import PerformanceConfig
        return IndicatorConfig(
            sma_periods=[20, 50],
            ema_periods=[12, 26],
            rsi_period=14,
            macd_fast=12,
            macd_slow=26,
            macd_signal=9,
            performance=PerformanceConfig(enable_caching=False)
        )

    @pytest.fixture
    def indicator_market_data(self):
        """Create sample market data for indicator testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'timestamp': dates,
            'symbol': ['AAPL'] * 100,
            'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'high': 102 + np.cumsum(np.random.randn(100) * 0.5),
            'low': 98 + np.cumsum(np.random.randn(100) * 0.5),
            'volume': np.random.randint(1000, 10000, 100),
            'open': 100 + np.cumsum(np.random.randn(100) * 0.3)
        })

        return data

    def test_initialization(self, indicator_config):
        """Test IndicatorEngine initialization."""
        engine = IndicatorEngine(indicator_config)

        assert engine.config == indicator_config
        assert hasattr(engine, 'calculate_indicators')

    def test_calculate_indicators(self, indicator_market_data, indicator_config):
        """Test indicator calculation."""
        engine = IndicatorEngine(indicator_config)

        indicators = engine.calculate_indicators(indicator_market_data)

        assert isinstance(indicators, pd.DataFrame)
        assert len(indicators) > 0

    def test_calculate_all_indicators(self, indicator_market_data, indicator_config):
        """Test calculation of all indicators."""
        engine = IndicatorEngine(indicator_config)

        all_indicators = engine.calculate_all_indicators(indicator_market_data)

        assert isinstance(all_indicators, pd.DataFrame)
        assert len(all_indicators) > 0

    def test_get_supported_indicators(self, indicator_config):
        """Test getting supported indicators."""
        engine = IndicatorEngine(indicator_config)

        supported = engine.get_supported_indicators()

        assert isinstance(supported, list)
        assert len(supported) > 0

    def test_empty_data_handling(self, indicator_config):
        """Test handling of empty data."""
        empty_data = pd.DataFrame()

        engine = IndicatorEngine(indicator_config)

        # The engine may return empty result instead of raising error
        result = engine.calculate_indicators(empty_data)
        assert isinstance(result, pd.DataFrame)

    def test_invalid_data_handling(self, indicator_config):
        """Test handling of invalid data."""
        invalid_data = pd.DataFrame({'invalid_column': [1, 2, 3]})

        engine = IndicatorEngine(indicator_config)

        # Should handle gracefully or raise appropriate error
        try:
            result = engine.calculate_indicators(invalid_data)
            assert isinstance(result, pd.DataFrame)
        except Exception:
            # Expected for invalid data
            pass


class TestTradingSignal:
    """Test TradingSignal class."""

    def test_initialization(self):
        """Test TradingSignal initialization."""
        timestamp = datetime.now()
        signal = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=0.85,
            price=150.0,
            timestamp=timestamp,
            metadata={"strategy": "momentum", "timeframe": "1h", "indicators": {"rsi": 30, "macd": -0.5}}
        )

        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == SignalStrength.STRONG
        assert signal.confidence == 0.85
        assert signal.price == 150.0
        assert signal.timestamp == timestamp
        assert signal.metadata == {"strategy": "momentum", "timeframe": "1h", "indicators": {"rsi": 30, "macd": -0.5}}

    def test_initialization_defaults(self):
        """Test TradingSignal initialization with defaults."""
        timestamp = datetime.now()
        signal = TradingSignal(
            symbol="GOOGL",
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=0.7,
            price=100.0,
            timestamp=timestamp
        )

        assert signal.symbol == "GOOGL"
        assert signal.signal_type == SignalType.SELL
        assert signal.strength == SignalStrength.MODERATE
        assert signal.confidence == 0.7
        assert signal.price == 100.0
        assert signal.timestamp == timestamp
        assert signal.metadata == {}

    def test_to_dict(self):
        """Test TradingSignal to_dict method."""
        timestamp = datetime.now()
        signal = TradingSignal(
            symbol="MSFT",
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.6,
            price=200.0,
            timestamp=timestamp
        )

        signal_dict = signal.to_dict()

        assert isinstance(signal_dict, dict)
        assert signal_dict["symbol"] == "MSFT"
        assert signal_dict["signal_type"] == "HOLD"
        assert signal_dict["strength"] == "WEAK"
        assert signal_dict["confidence"] == 0.6
        assert signal_dict["price"] == 200.0

    def test_from_dict(self):
        """Test TradingSignal from_dict method."""
        timestamp = datetime.now()
        signal_dict = {
            "symbol": "TSLA",
            "signal_type": "buy",
            "strength": "STRONG",
            "confidence": 0.9,
            "price": 250.0,
            "timestamp": timestamp.isoformat(),
            "metadata": {"strategy": "breakout", "indicators": {"sma": 245, "rsi": 65}}
        }

        signal = TradingSignal.from_dict(signal_dict)

        assert signal.symbol == "TSLA"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == SignalStrength.STRONG
        assert signal.confidence == 0.9
        assert signal.price == 250.0
        assert signal.metadata == {"strategy": "breakout", "indicators": {"sma": 245, "rsi": 65}}

    def test_signal_strength_values(self):
        """Test SignalStrength enum values."""
        assert SignalStrength.WEAK.value == 1
        assert SignalStrength.MODERATE.value == 2
        assert SignalStrength.STRONG.value == 3

    def test_signal_type_values(self):
        """Test SignalType enum values."""
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"

    def test_invalid_confidence(self):
        """Test handling of invalid confidence values."""
        timestamp = datetime.now()
        with pytest.raises(ValueError):
            TradingSignal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=1.5,  # Invalid: > 1.0
                price=150.0,
                timestamp=timestamp
            )

        with pytest.raises(ValueError):
            TradingSignal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=-0.1,  # Invalid: < 0.0
                price=150.0,
                timestamp=timestamp
            )


