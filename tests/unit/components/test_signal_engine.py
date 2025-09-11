#!/usr/bin/env python3
"""
Test Suite for Signal Engine
============================

Comprehensive test coverage for the unified signal engine including:
- Signal generation and validation
- Feature processing and transformation
- Risk-aware signal filtering
- Performance monitoring and metrics
- Multi-timeframe signal processing
- Edge cases and error handling

Author: Test Coverage Implementation - Phase 3
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Optional, Union, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Import signal engine classes
from core_structure.components.signal_generation.core.signal_engine import (
    UnifiedSignalEngine,
    SignalType,
    SignalStrength,
    SignalConfig
)

# Mock external dependencies
try:
    import ta
    import sklearn
    TA_AVAILABLE = True
    SKLEARN_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    SKLEARN_AVAILABLE = False
    ta = None
    sklearn = None


class TestSignalType:
    """Test cases for SignalType enum"""

    def test_signal_type_values(self):
        """Test signal type enum values"""
        assert SignalType.LONG.value == 1
        assert SignalType.SHORT.value == -1
        assert SignalType.NEUTRAL.value == 0
        assert SignalType.EXIT.value == 99

    def test_signal_type_names(self):
        """Test signal type enum names"""
        assert SignalType.LONG.name == "LONG"
        assert SignalType.SHORT.name == "SHORT"
        assert SignalType.NEUTRAL.name == "NEUTRAL"
        assert SignalType.EXIT.name == "EXIT"


class TestSignalStrength:
    """Test cases for SignalStrength enum"""

    def test_signal_strength_values(self):
        """Test signal strength enum values"""
        assert SignalStrength.VERY_WEAK.value == 1
        assert SignalStrength.WEAK.value == 2
        assert SignalStrength.MODERATE.value == 3
        assert SignalStrength.STRONG.value == 4
        assert SignalStrength.VERY_STRONG.value == 5

    def test_signal_strength_ordering(self):
        """Test signal strength ordering"""
        assert SignalStrength.VERY_WEAK < SignalStrength.WEAK
        assert SignalStrength.WEAK < SignalStrength.MODERATE
        assert SignalStrength.MODERATE < SignalStrength.STRONG
        assert SignalStrength.STRONG < SignalStrength.VERY_STRONG


class TestSignalConfig:
    """Test cases for SignalConfig dataclass"""

    def test_default_configuration(self):
        """Test default signal configuration"""
        config = SignalConfig()

        assert config.min_confidence_threshold == 0.35
        assert config.max_position_size == 0.15
        assert config.lookback_period == 60
        assert config.enable_ml_features == True
        assert config.enable_risk_filtering == True
        assert config.signal_decay_factor == 0.95

    def test_custom_configuration(self):
        """Test custom signal configuration"""
        config = SignalConfig(
            min_confidence_threshold=0.5,
            max_position_size=0.2,
            lookback_period=100,
            enable_ml_features=False,
            enable_risk_filtering=False,
            signal_decay_factor=0.9
        )

        assert config.min_confidence_threshold == 0.5
        assert config.max_position_size == 0.2
        assert config.lookback_period == 100
        assert config.enable_ml_features == False
        assert config.enable_risk_filtering == False
        assert config.signal_decay_factor == 0.9


class TestSignalEngine:
    """Test cases for SignalEngine class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = SignalConfig(
            min_confidence_threshold=0.01,  # Lower threshold for testing
            min_data_points=5,             # Lower data points requirement for testing
            enable_risk_filtering=False,    # Disable risk filtering for testing
            enable_adaptive_thresholds=False, # Disable adaptive thresholds for testing
            enable_kalman_filtering=False,  # Disable Kalman filtering for testing
            enable_caching=False,           # Disable caching for testing
            enable_ml_enhancement=False,    # Disable ML enhancement for testing
            enable_regime_detection=False,  # Disable regime detection for testing
            enable_feature_engineering=False, # Disable feature engineering for testing
            enable_validation=False,        # Disable validation for testing
            parallel_processing=False,      # Disable parallel processing for testing
            enable_parameter_optimization=False, # Disable parameter optimization for testing
            feature_selection=False,       # Disable feature selection for testing
            outlier_detection=False        # Disable outlier detection for testing
        )
        self.signal_engine = UnifiedSignalEngine(self.config)

        # Mock external dependencies
        if not TA_AVAILABLE:
            self.signal_engine.ta = Mock()
        if not SKLEARN_AVAILABLE:
            self.signal_engine.scaler = Mock()
            self.signal_engine.ml_model = Mock()

    def test_initialization(self):
        """Test signal engine initialization"""
        assert self.signal_engine.config == self.config
        assert isinstance(self.signal_engine.signal_history, dict)
        assert len(self.signal_engine.signal_history) == 0
        assert self.signal_engine.signal_count == 0

    def test_generate_base_signals(self):
        """Test base signal generation"""
        # Create sample market data
        data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105],
            'high': [101, 102, 103, 104, 105, 106],
            'low': [99, 100, 101, 102, 103, 104],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500]
        })

        signals = self.signal_engine.generate_base_signals("AAPL", data)

        assert isinstance(signals, dict)
        assert "momentum" in signals
        assert "mean_reversion" in signals
        assert "trend" in signals

    def test_calculate_momentum_signal(self):
        """Test momentum signal calculation"""
        prices = pd.Series([100, 101, 102, 103, 104, 105])

        momentum_signal = self.signal_engine.calculate_momentum_signal(prices)

        assert isinstance(momentum_signal, float)
        assert -1 <= momentum_signal <= 1

    def test_calculate_mean_reversion_signal(self):
        """Test mean reversion signal calculation"""
        prices = pd.Series([100, 105, 95, 102, 98, 101])

        mr_signal = self.signal_engine.calculate_mean_reversion_signal(prices)

        assert isinstance(mr_signal, float)
        assert -1 <= mr_signal <= 1

    def test_calculate_trend_signal(self):
        """Test trend signal calculation"""
        prices = pd.Series([100, 101, 102, 103, 104, 105])

        trend_signal = self.signal_engine.calculate_trend_signal(prices)

        assert isinstance(trend_signal, float)
        assert -1 <= trend_signal <= 1

    def test_combine_signals(self):
        """Test signal combination"""
        signals = {
            "momentum": 0.8,
            "mean_reversion": -0.3,
            "trend": 0.6
        }

        combined_signal = self.signal_engine.combine_signals(signals)

        assert isinstance(combined_signal, float)
        assert -1 <= combined_signal <= 1

    def test_apply_risk_filters(self):
        """Test risk filter application"""
        signal = 0.8
        confidence = 0.9

        # Mock risk metrics
        risk_metrics = {
            "volatility": 0.02,
            "max_drawdown": 0.05,
            "sharpe_ratio": 1.5
        }

        filtered_signal = self.signal_engine.apply_risk_filters(
            signal, confidence, risk_metrics
        )

        assert isinstance(filtered_signal, float)
        assert -1 <= filtered_signal <= 1

    def test_calculate_signal_confidence(self):
        """Test signal confidence calculation"""
        signals = {
            "momentum": 0.8,
            "mean_reversion": -0.3,
            "trend": 0.6
        }

        confidence = self.signal_engine.calculate_signal_confidence(signals)

        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1

    def test_validate_signal(self):
        """Test signal validation"""
        # Valid signal
        valid_signal = {
            "symbol": "AAPL",
            "signal_type": SignalType.LONG,
            "strength": SignalStrength.STRONG,
            "confidence": 0.8,
            "timestamp": datetime.now()
        }

        is_valid = self.signal_engine.validate_signal(valid_signal)
        assert is_valid is True

        # Invalid signal - low confidence
        invalid_signal = {
            "symbol": "AAPL",
            "signal_type": SignalType.LONG,
            "strength": SignalStrength.WEAK,
            "confidence": 0.005,  # Below threshold
            "timestamp": datetime.now()
        }

        is_valid = self.signal_engine.validate_signal(invalid_signal)
        assert is_valid is False

    def test_generate_signal(self):
        """Test complete signal generation"""
        # Create sample market data with stronger trend
        data = pd.DataFrame({
            'close': [100, 102, 104, 106, 108, 110, 112, 114, 116, 118],  # Strong uptrend
            'high': [101, 103, 105, 107, 109, 111, 113, 115, 117, 119],
            'low': [99, 101, 103, 105, 107, 109, 111, 113, 115, 117],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        })
        
        signal = self.signal_engine.generate_signal("AAPL", data)

        assert isinstance(signal, dict)
        assert "symbol" in signal
        assert "signal_type" in signal
        assert "strength" in signal
        assert "confidence" in signal
        assert "timestamp" in signal
        assert signal["symbol"] == "AAPL"

    def test_process_market_data(self):
        """Test market data processing"""
        # Create sample market data
        data = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100,
            'high': np.random.randn(100).cumsum() + 102,
            'low': np.random.randn(100).cumsum() + 98,
            'volume': np.random.randint(1000, 2000, 100)
        })

        processed_data = self.signal_engine.process_market_data("AAPL", data)

        assert isinstance(processed_data, pd.DataFrame)
        assert len(processed_data) == len(data)

    def test_update_signal_history(self):
        """Test signal history updates"""
        signal = {
            "symbol": "AAPL",
            "signal_type": SignalType.LONG,
            "strength": SignalStrength.STRONG,
            "confidence": 0.8,
            "timestamp": datetime.now()
        }

        self.signal_engine.update_signal_history(signal)

        assert "AAPL" in self.signal_engine.signal_history
        assert len(self.signal_engine.signal_history["AAPL"]) == 1
        assert self.signal_engine.signal_history["AAPL"][0] == signal

    def test_get_signal_history(self):
        """Test signal history retrieval"""
        # Add some signals
        signals = [
            {
                "symbol": "AAPL",
                "signal_type": SignalType.LONG,
                "strength": SignalStrength.STRONG,
                "confidence": 0.8,
                "timestamp": datetime.now()
            },
            {
                "symbol": "AAPL",
                "signal_type": SignalType.SHORT,
                "strength": SignalStrength.MODERATE,
                "confidence": 0.6,
                "timestamp": datetime.now()
            }
        ]

        for signal in signals:
            self.signal_engine.update_signal_history(signal)

        history = self.signal_engine.get_signal_history("AAPL")

        assert len(history) == 2
        assert history == signals

    def test_calculate_signal_metrics(self):
        """Test signal performance metrics calculation"""
        # Add historical signals with known outcomes
        signals = [
            {
                "symbol": "AAPL",
                "signal_type": SignalType.LONG,
                "strength": SignalStrength.STRONG,
                "confidence": 0.8,
                "timestamp": datetime.now() - timedelta(days=5),
                "outcome": 0.02  # 2% return
            },
            {
                "symbol": "AAPL",
                "signal_type": SignalType.SHORT,
                "strength": SignalStrength.MODERATE,
                "confidence": 0.6,
                "timestamp": datetime.now() - timedelta(days=3),
                "outcome": -0.01  # -1% return
            }
        ]

        for signal in signals:
            self.signal_engine.update_signal_history(signal)

        metrics = self.signal_engine.calculate_signal_metrics("AAPL")

        assert isinstance(metrics, dict)
        assert "total_signals" in metrics
        assert "win_rate" in metrics
        assert "avg_return" in metrics
        assert metrics["total_signals"] == 2
        assert metrics["win_rate"] == 0.5  # 1 win out of 2

    def test_apply_signal_decay(self):
        """Test signal decay application"""
        signal = 0.8
        age_hours = 24  # 1 day old

        decayed_signal = self.signal_engine.apply_signal_decay(signal, age_hours)

        assert isinstance(decayed_signal, float)
        assert decayed_signal < signal  # Should be decayed
        assert decayed_signal > 0

    def test_generate_multi_timeframe_signals(self):
        """Test multi-timeframe signal generation"""
        # Create data for different timeframes
        data_1h = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100,
            'high': np.random.randn(100).cumsum() + 102,
            'low': np.random.randn(100).cumsum() + 98,
            'volume': np.random.randint(1000, 2000, 100)
        })

        data_4h = pd.DataFrame({
            'close': np.random.randn(25).cumsum() + 100,
            'high': np.random.randn(25).cumsum() + 102,
            'low': np.random.randn(25).cumsum() + 98,
            'volume': np.random.randint(1000, 2000, 25)
        })

        multi_data = {
            "1h": data_1h,
            "4h": data_4h
        }

        signals = self.signal_engine.generate_multi_timeframe_signals("AAPL", multi_data)

        assert isinstance(signals, dict)
        assert "combined_signal" in signals
        assert "timeframe_signals" in signals

    def test_risk_adjusted_position_size(self):
        """Test risk-adjusted position sizing"""
        signal_strength = 0.8
        confidence = 0.9
        volatility = 0.02
        portfolio_value = 100000.0

        position_size = self.signal_engine.calculate_risk_adjusted_position_size(
            signal_strength, confidence, volatility, portfolio_value
        )

        assert isinstance(position_size, float)
        assert 0 <= position_size <= portfolio_value * self.config.max_position_size

    def test_signal_correlation_filter(self):
        """Test signal correlation filtering"""
        signals = {
            "AAPL": 0.8,
            "GOOGL": 0.6,
            "MSFT": 0.7
        }

        # Mock correlation matrix
        correlation_matrix = pd.DataFrame({
            'AAPL': [1.0, 0.8, 0.6],
            'GOOGL': [0.8, 1.0, 0.7],
            'MSFT': [0.6, 0.7, 1.0]
        }, index=['AAPL', 'GOOGL', 'MSFT'])

        filtered_signals = self.signal_engine.apply_correlation_filter(
            signals, correlation_matrix
        )

        assert isinstance(filtered_signals, dict)
        assert len(filtered_signals) == len(signals)


class TestSignalEngineIntegration:
    """Integration tests for signal engine"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = SignalConfig(
            min_confidence_threshold=0.01,  # Lower threshold for testing
            enable_feature_engineering=False,  # Disable feature engineering for testing
            enable_ml_enhancement=False,  # Disable ML enhancement for testing
            enable_regime_detection=False,  # Disable regime detection for testing
            enable_adaptive_thresholds=False,  # Disable adaptive thresholds for testing
            enable_kalman_filtering=False,  # Disable Kalman filtering for testing
            enable_caching=False,  # Disable caching for testing
            enable_risk_filtering=False,  # Disable risk filtering for testing
            parallel_processing=False,  # Disable parallel processing for testing
            enable_parameter_optimization=False,  # Disable parameter optimization for testing
            feature_selection=False,  # Disable feature selection for testing
            outlier_detection=False  # Disable outlier detection for testing
        )
        self.signal_engine = UnifiedSignalEngine(self.config)

    def test_end_to_end_signal_generation(self):
        """Test end-to-end signal generation workflow"""
        # Create realistic market data
        np.random.seed(42)
        n_periods = 200

        # Generate price data with some trend and noise
        trend = np.linspace(100, 110, n_periods)
        noise = np.random.normal(0, 2, n_periods)
        close_prices = trend + noise

        # Generate OHLCV data
        high_prices = close_prices + np.abs(np.random.normal(0, 1, n_periods))
        low_prices = close_prices - np.abs(np.random.normal(0, 1, n_periods))
        volume = np.random.randint(100000, 500000, n_periods)

        data = pd.DataFrame({
            'close': close_prices,
            'high': high_prices,
            'low': low_prices,
            'volume': volume
        })

        # Generate signal
        signal = self.signal_engine.generate_signal("AAPL", data)

        # Validate signal structure
        required_fields = ["symbol", "signal_type", "strength", "confidence", "timestamp"]
        for field in required_fields:
            assert field in signal

        assert signal["symbol"] == "AAPL"
        assert signal["signal_type"] in ["LONG", "SHORT", "NEUTRAL"]
        assert signal["strength"] in ["VERY_WEAK", "WEAK", "MODERATE", "STRONG", "VERY_STRONG"]
        assert 0 <= signal["confidence"] <= 1

    def test_signal_consistency_over_time(self):
        """Test signal consistency over multiple data points"""
        np.random.seed(42)

        signals = []
        for i in range(10):
            # Generate slightly different data each time
            data = pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 100 + i,
                'high': np.random.randn(100).cumsum() + 102 + i,
                'low': np.random.randn(100).cumsum() + 98 + i,
                'volume': np.random.randint(1000, 2000, 100)
            })

            signal = self.signal_engine.generate_signal("AAPL", data)
            signals.append(signal)

        # Check that signals are reasonably consistent (not completely random)
        confidences = [s["confidence"] for s in signals]
        confidence_std = np.std(confidences)

        # Confidence shouldn't vary too wildly
        assert confidence_std < 0.5

    def test_multi_symbol_signal_generation(self):
        """Test signal generation for multiple symbols"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]

        # Generate data for each symbol
        np.random.seed(42)
        signals = {}

        for symbol in symbols:
            data = pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 100,
                'high': np.random.randn(100).cumsum() + 102,
                'low': np.random.randn(100).cumsum() + 98,
                'volume': np.random.randint(1000, 2000, 100)
            })

            signal = self.signal_engine.generate_signal(symbol, data)
            signals[symbol] = signal

        # Validate all signals
        for symbol in symbols:
            assert symbol in signals
            signal = signals[symbol]
            assert signal["symbol"] == symbol
            assert 0 <= signal["confidence"] <= 1

    def test_signal_performance_under_stress(self):
        """Test signal generation under stress conditions"""
        # Test with very volatile data
        np.random.seed(42)
        volatile_data = pd.DataFrame({
            'close': np.random.randn(1000).cumsum() + 100,  # Very volatile
            'high': np.random.randn(1000).cumsum() + 110,
            'low': np.random.randn(1000).cumsum() + 90,
            'volume': np.random.randint(10000, 100000, 1000)  # High volume
        })

        signal = self.signal_engine.generate_signal("VOLATILE", volatile_data)

        # Should still generate valid signal
        assert signal["symbol"] == "VOLATILE"
        assert 0 <= signal["confidence"] <= 1

    def test_signal_adaptation_to_market_conditions(self):
        """Test signal adaptation to different market conditions"""
        # Test trending market
        trending_data = pd.DataFrame({
            'close': np.linspace(100, 120, 100),  # Strong uptrend
            'high': np.linspace(101, 121, 100),
            'low': np.linspace(99, 119, 100),
            'volume': np.linspace(1000, 2000, 100)
        })

        trending_signal = self.signal_engine.generate_signal("TRENDING", trending_data)

        # Test ranging market
        ranging_data = pd.DataFrame({
            'close': np.sin(np.linspace(0, 4*np.pi, 100)) * 5 + 100,  # Sideways
            'high': np.sin(np.linspace(0, 4*np.pi, 100)) * 5 + 102,
            'low': np.sin(np.linspace(0, 4*np.pi, 100)) * 5 + 98,
            'volume': np.full(100, 1000)
        })

        ranging_signal = self.signal_engine.generate_signal("RANGING", ranging_data)

        # Both should generate valid signals
        assert trending_signal["confidence"] > 0
        assert ranging_signal["confidence"] > 0


class TestSignalEngineEdgeCases:
    """Test edge cases for signal engine"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = SignalConfig(
            min_confidence_threshold=0.01,  # Lower threshold for testing
            enable_feature_engineering=False,  # Disable feature engineering for testing
            enable_ml_enhancement=False,  # Disable ML enhancement for testing
            enable_regime_detection=False,  # Disable regime detection for testing
            enable_adaptive_thresholds=False,  # Disable adaptive thresholds for testing
            enable_kalman_filtering=False,  # Disable Kalman filtering for testing
            enable_caching=False,  # Disable caching for testing
            enable_risk_filtering=False,  # Disable risk filtering for testing
            parallel_processing=False,  # Disable parallel processing for testing
            enable_parameter_optimization=False,  # Disable parameter optimization for testing
            feature_selection=False,  # Disable feature selection for testing
            outlier_detection=False  # Disable outlier detection for testing
        )
        self.signal_engine = UnifiedSignalEngine(self.config)

    def test_empty_data_handling(self):
        """Test handling of empty data"""
        empty_data = pd.DataFrame()

        signal = self.signal_engine.generate_signal("EMPTY", empty_data)

        # Should handle gracefully
        assert signal["symbol"] == "EMPTY"
        assert signal["signal_type"] == SignalType.NEUTRAL

    def test_single_data_point(self):
        """Test handling of single data point"""
        single_data = pd.DataFrame({
            'close': [100.0],
            'high': [101.0],
            'low': [99.0],
            'volume': [1000]
        })

        signal = self.signal_engine.generate_signal("SINGLE", single_data)

        # Should handle gracefully
        assert signal["symbol"] == "SINGLE"
        assert 0 <= signal["confidence"] <= 1

    def test_extreme_price_movements(self):
        """Test handling of extreme price movements"""
        # Test with very large price swings
        extreme_data = pd.DataFrame({
            'close': [100, 1000, 10, 500, 50],  # Extreme volatility
            'high': [110, 1100, 11, 550, 55],
            'low': [90, 900, 9, 450, 45],
            'volume': [1000, 10000, 100, 5000, 500]
        })

        signal = self.signal_engine.generate_signal("EXTREME", extreme_data)

        # Should handle without crashing
        assert signal["symbol"] == "EXTREME"
        assert 0 <= signal["confidence"] <= 1

    def test_zero_volume_handling(self):
        """Test handling of zero volume"""
        zero_volume_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'volume': [0, 0, 0, 0, 0]  # All zero volume
        })

        signal = self.signal_engine.generate_signal("ZERO_VOL", zero_volume_data)

        # Should handle gracefully
        assert signal["symbol"] == "ZERO_VOL"
        assert 0 <= signal["confidence"] <= 1

    def test_negative_price_handling(self):
        """Test handling of negative prices (edge case)"""
        negative_data = pd.DataFrame({
            'close': [100, -50, 25, -10, 75],  # Negative prices
            'high': [110, -40, 30, -5, 80],
            'low': [90, -60, 20, -15, 70],
            'volume': [1000, 500, 750, 250, 1250]
        })

        signal = self.signal_engine.generate_signal("NEGATIVE", negative_data)

        # Should handle without crashing
        assert signal["symbol"] == "NEGATIVE"
        assert 0 <= signal["confidence"] <= 1

    def test_missing_columns_handling(self):
        """Test handling of missing data columns"""
        # Missing volume column
        missing_volume_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103]
            # No volume column
        })

        signal = self.signal_engine.generate_signal("MISSING_VOL", missing_volume_data)

        # Should handle gracefully
        assert signal["symbol"] == "MISSING_VOL"
        assert 0 <= signal["confidence"] <= 1

    def test_nan_value_handling(self):
        """Test handling of NaN values in data"""
        nan_data = pd.DataFrame({
            'close': [100, np.nan, 102, 103, np.nan],
            'high': [101, 102, np.nan, 104, 105],
            'low': [99, np.nan, 101, 102, 103],
            'volume': [1000, 1100, np.nan, 1300, 1400]
        })

        signal = self.signal_engine.generate_signal("NAN_DATA", nan_data)

        # Should handle NaN values gracefully
        assert signal["symbol"] == "NAN_DATA"
        assert 0 <= signal["confidence"] <= 1

    def test_very_long_time_series(self):
        """Test handling of very long time series"""
        # Generate very long time series
        n_periods = 10000
        long_data = pd.DataFrame({
            'close': np.random.randn(n_periods).cumsum() + 100,
            'high': np.random.randn(n_periods).cumsum() + 102,
            'low': np.random.randn(n_periods).cumsum() + 98,
            'volume': np.random.randint(1000, 2000, n_periods)
        })

        signal = self.signal_engine.generate_signal("LONG_SERIES", long_data)

        # Should handle large datasets efficiently
        assert signal["symbol"] == "LONG_SERIES"
        assert 0 <= signal["confidence"] <= 1

    def test_concurrent_signal_generation(self):
        """Test concurrent signal generation"""
        import threading
        import time

        results = []

        def generate_signal_for_symbol(symbol):
            data = pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 100,
                'high': np.random.randn(100).cumsum() + 102,
                'low': np.random.randn(100).cumsum() + 98,
                'volume': np.random.randint(1000, 2000, 100)
            })

            signal = self.signal_engine.generate_signal(symbol, data)
            results.append(signal)

        # Generate signals for multiple symbols concurrently
        symbols = [f"CONCURRENT_{i}" for i in range(10)]
        threads = []

        for symbol in symbols:
            thread = threading.Thread(target=generate_signal_for_symbol, args=(symbol,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        assert len(results) == 10
        for result in results:
            assert 0 <= result["confidence"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
