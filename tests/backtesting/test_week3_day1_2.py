#!/usr/bin/env python3
"""
Week 3 Day 1-2: Signal Generation Building Blocks Tests
"""

import unittest
import numpy as np
from datetime import datetime

from core_structure.strategy_layer.blocks import (
    SignalGenerator,
    SignalResult,
    SignalMetrics,
    MomentumSignalGenerator,
    PairTradingSignalGenerator,
    MeanReversionSignalGenerator
)
from core_structure.strategy_layer.config import SignalConfig
from core_structure.strategy_layer.exceptions import SignalError, ValidationError


class TestSignalGeneratorBase(unittest.TestCase):
    """Test base signal generator functionality."""
    
    def setUp(self):
        self.config = SignalConfig(
            type="test",
            indicators={"test_period": 10},
            signal_combination={"weights": {"test": 1.0}}
        )
        
        class MockSignalGenerator(SignalGenerator):
            def generate_signal(self, data):
                return SignalResult(
                    signal_value=0.5,
                    signal_type="test",
                    confidence=0.8,
                    timestamp=datetime.now()
                )
            
            def get_required_data_fields(self):
                return ["test_data"]
            
            def _validate_specific_config(self):
                pass
        
        self.signal_generator = MockSignalGenerator(self.config)
    
    def test_signal_generator_initialization(self):
        """Test signal generator initialization."""
        self.assertIsNotNone(self.signal_generator)
        self.assertEqual(self.signal_generator.name, "MockSignalGenerator")
    
    def test_process_signal_success(self):
        """Test successful signal processing."""
        data = {"test_data": [1, 2, 3]}
        result = self.signal_generator.process_signal(data)
        
        self.assertIsInstance(result, SignalResult)
        self.assertEqual(result.signal_value, 0.5)
        self.assertEqual(result.signal_type, "test")


class TestMomentumSignalGenerator(unittest.TestCase):
    """Test MomentumSignalGenerator class."""
    
    def setUp(self):
        self.config = SignalConfig(
            type="momentum",
            indicators={
                "rsi_period": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "momentum_period": 10
            },
            signal_combination={
                "weights": {"rsi": 0.3, "macd": 0.4, "momentum": 0.3}
            }
        )
        
        self.signal_generator = MomentumSignalGenerator(self.config)
        np.random.seed(42)
        self.prices = 100 + np.cumsum(np.random.randn(100) * 0.1)
    
    def test_momentum_signal_generation(self):
        """Test momentum signal generation."""
        data = {"prices": self.prices}
        result = self.signal_generator.generate_signal(data)
        
        self.assertIsInstance(result, SignalResult)
        self.assertEqual(result.signal_type, "momentum")
        self.assertTrue(-1 <= result.signal_value <= 1)
        self.assertTrue(0 <= result.confidence <= 1)


class TestPairTradingSignalGenerator(unittest.TestCase):
    """Test PairTradingSignalGenerator class."""
    
    def setUp(self):
        self.config = SignalConfig(
            type="pair_trading",
            indicators={
                "correlation_threshold": 0.7,
                "zscore_threshold": 2.0,
                "lookback_period": 60
            },
            signal_combination={
                "weights": {"correlation": 0.2, "cointegration": 0.3, "zscore": 0.5}
            }
        )
        
        self.signal_generator = PairTradingSignalGenerator(self.config)
        np.random.seed(42)
        self.asset1_prices = 100 + np.cumsum(np.random.randn(100) * 0.1)
        self.asset2_prices = 50 + np.cumsum(np.random.randn(100) * 0.1)
    
    def test_pair_trading_signal_generation(self):
        """Test pair trading signal generation."""
        data = {
            "asset1_prices": self.asset1_prices,
            "asset2_prices": self.asset2_prices
        }
        result = self.signal_generator.generate_signal(data)
        
        self.assertIsInstance(result, SignalResult)
        self.assertEqual(result.signal_type, "pair_trading")
        self.assertTrue(-1 <= result.signal_value <= 1)
        self.assertTrue(0 <= result.confidence <= 1)


class TestMeanReversionSignalGenerator(unittest.TestCase):
    """Test MeanReversionSignalGenerator class."""
    
    def setUp(self):
        self.config = SignalConfig(
            type="mean_reversion",
            indicators={
                "lookback_period": 60,
                "zscore_threshold": 2.0,
                "adf_pvalue": 0.05
            },
            signal_combination={
                "weights": {"zscore": 0.4, "stationarity": 0.3, "half_life": 0.3}
            }
        )
        
        self.signal_generator = MeanReversionSignalGenerator(self.config)
        np.random.seed(42)
        self.prices = 100 + np.cumsum(np.random.randn(100) * 0.1)
    
    def test_mean_reversion_signal_generation(self):
        """Test mean reversion signal generation."""
        data = {"prices": self.prices}
        result = self.signal_generator.generate_signal(data)
        
        self.assertIsInstance(result, SignalResult)
        self.assertEqual(result.signal_type, "mean_reversion")
        self.assertTrue(-1 <= result.signal_value <= 1)
        self.assertTrue(0 <= result.confidence <= 1)


if __name__ == "__main__":
    unittest.main() 