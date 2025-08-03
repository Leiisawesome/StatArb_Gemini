"""
Test suite for SignalBridge: Core System ↔ Backtesting Framework Integration

This module provides comprehensive tests for the SignalBridge class, including:
- Basic functionality testing
- Performance testing
- Integration testing
- Error handling testing
- Cache testing
- Fallback mechanism testing
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import time
import logging

# Add the core_structure to the path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core_structure'))

from signal_generation.signal_bridge import (
    SignalBridge, 
    SignalBridgeConfig, 
    SignalBridgeResult,
    create_signal_bridge,
    generate_signals_for_backtesting
)


class TestSignalBridgeConfig:
    """Test SignalBridgeConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = SignalBridgeConfig()
        
        assert config.use_core_signal_generator is True
        assert config.use_ai_enhancement is True
        assert config.use_regime_detection is True
        assert config.max_concurrent_signals == 10
        assert config.timeout_seconds == 5.0
        assert config.cache_size == 1000
        assert config.enable_fallback is True
        assert config.validate_signals is True
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = SignalBridgeConfig(
            use_core_signal_generator=False,
            use_ai_enhancement=False,
            max_concurrent_signals=5,
            cache_size=500
        )
        
        assert config.use_core_signal_generator is False
        assert config.use_ai_enhancement is False
        assert config.max_concurrent_signals == 5
        assert config.cache_size == 500


class TestSignalBridgeResult:
    """Test SignalBridgeResult dataclass"""
    
    def test_signal_bridge_result_creation(self):
        """Test SignalBridgeResult creation"""
        timestamp = datetime.now()
        result = SignalBridgeResult(
            symbol="AAPL",
            signal_value=0.75,
            confidence=0.8,
            timestamp=timestamp,
            source="core",
            processing_time_ms=150.0
        )
        
        assert result.symbol == "AAPL"
        assert result.signal_value == 0.75
        assert result.confidence == 0.8
        assert result.timestamp == timestamp
        assert result.source == "core"
        assert result.processing_time_ms == 150.0
        assert result.error_message is None
    
    def test_signal_bridge_result_with_metadata(self):
        """Test SignalBridgeResult with metadata"""
        result = SignalBridgeResult(
            symbol="SPY",
            signal_value=-0.5,
            confidence=0.6,
            timestamp=datetime.now(),
            source="fallback",
            metadata={"ma_short": 100.0, "ma_long": 98.0}
        )
        
        assert result.metadata["ma_short"] == 100.0
        assert result.metadata["ma_long"] == 98.0


class TestSignalBridgeInitialization:
    """Test SignalBridge initialization"""
    
    @patch('signal_generation.signal_bridge.SignalGenerator')
    @patch('signal_generation.signal_bridge.EnhancedSignalGenerator')
    @patch('signal_generation.signal_bridge.AISignalEnhancer')
    @patch('signal_generation.signal_bridge.RegimeDetector')
    @patch('signal_generation.signal_bridge.FeatureEngine')
    def test_signal_bridge_init_default(self, mock_feature_engine, mock_regime_detector, 
                                       mock_ai_enhancer, mock_enhanced_generator, mock_generator):
        """Test SignalBridge initialization with default config"""
        bridge = SignalBridge()
        
        assert bridge.config.use_core_signal_generator is True
        assert bridge.config.use_ai_enhancement is True
        assert bridge.config.use_regime_detection is True
        assert len(bridge._signal_cache) == 0
        assert bridge._performance_stats['total_signals'] == 0
    
    @patch('signal_generation.signal_bridge.SignalGenerator')
    @patch('signal_generation.signal_bridge.EnhancedSignalGenerator')
    @patch('signal_generation.signal_bridge.AISignalEnhancer')
    @patch('signal_generation.signal_bridge.RegimeDetector')
    @patch('signal_generation.signal_bridge.FeatureEngine')
    def test_signal_bridge_init_custom_config(self, mock_feature_engine, mock_regime_detector,
                                             mock_ai_enhancer, mock_enhanced_generator, mock_generator):
        """Test SignalBridge initialization with custom config"""
        config = SignalBridgeConfig(
            use_core_signal_generator=False,
            use_ai_enhancement=False,
            max_concurrent_signals=5
        )
        
        bridge = SignalBridge(config)
        
        assert bridge.config.use_core_signal_generator is False
        assert bridge.config.use_ai_enhancement is False
        assert bridge.config.max_concurrent_signals == 5
    
    @patch('signal_generation.signal_bridge.SignalGenerator')
    def test_signal_bridge_init_error(self, mock_generator):
        """Test SignalBridge initialization error handling"""
        mock_generator.side_effect = Exception("Initialization error")
        
        with pytest.raises(Exception):
            SignalBridge()


class TestSignalBridgeCoreFunctionality:
    """Test SignalBridge core functionality"""
    
    @pytest.fixture
    def mock_bridge(self):
        """Create a mock SignalBridge for testing"""
        with patch('signal_generation.signal_bridge.SignalGenerator'), \
             patch('signal_generation.signal_bridge.EnhancedSignalGenerator'), \
             patch('signal_generation.signal_bridge.AISignalEnhancer'), \
             patch('signal_generation.signal_bridge.RegimeDetector'), \
             patch('signal_generation.signal_bridge.FeatureEngine'):
            
            bridge = SignalBridge()
            
            # Mock the core components
            bridge.signal_generator = Mock()
            bridge.ai_enhancer = Mock()
            bridge.regime_detector = Mock()
            bridge.feature_engine = Mock()
            
            return bridge
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        data = {
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(100, 200, 100),
            'low': np.random.uniform(100, 200, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000000, 5000000, 100)
        }
        return pd.DataFrame(data, index=dates)
    
    def test_generate_signals_sync_basic(self, mock_bridge, sample_market_data):
        """Test basic signal generation"""
        # Mock the signal generation
        mock_signal = Mock()
        mock_signal.signal_value = 0.75
        mock_signal.confidence = 0.8
        mock_bridge.signal_generator.generate_signal.return_value = mock_signal
        
        # Mock feature extraction
        mock_bridge.feature_engine.extract_features.return_value = {'feature1': 1.0}
        
        # Mock regime detection
        mock_regime = Mock()
        mock_regime.regime_type = 'trending'
        mock_bridge.regime_detector.detect_regime.return_value = mock_regime
        
        symbols = ["AAPL"]
        market_data = {"AAPL": sample_market_data}
        current_date = datetime.now()
        
        results = mock_bridge.generate_signals_sync(symbols, market_data, current_date)
        
        assert "AAPL" in results
        assert isinstance(results["AAPL"], SignalBridgeResult)
        assert results["AAPL"].signal_value == 0.9  # 0.75 * 1.2 for trending regime
        assert results["AAPL"].source == "core"
    
    def test_generate_signals_sync_multiple_symbols(self, mock_bridge, sample_market_data):
        """Test signal generation for multiple symbols"""
        # Mock signal generation
        mock_signal = Mock()
        mock_signal.signal_value = 0.5
        mock_signal.confidence = 0.7
        mock_bridge.signal_generator.generate_signal.return_value = mock_signal
        
        # Mock other components
        mock_bridge.feature_engine.extract_features.return_value = {}
        mock_regime = Mock()
        mock_regime.regime_type = 'mean_reverting'
        mock_bridge.regime_detector.detect_regime.return_value = mock_regime
        
        symbols = ["AAPL", "SPY", "MSFT"]
        market_data = {
            "AAPL": sample_market_data,
            "SPY": sample_market_data,
            "MSFT": sample_market_data
        }
        current_date = datetime.now()
        
        results = mock_bridge.generate_signals_sync(symbols, market_data, current_date)
        
        assert len(results) == 3
        for symbol in symbols:
            assert symbol in results
            assert results[symbol].signal_value == 0.4  # 0.5 * 0.8 for mean_reverting regime
    
    def test_generate_signals_sync_with_cache(self, mock_bridge, sample_market_data):
        """Test signal generation with caching"""
        # First call - generate signals
        mock_signal = Mock()
        mock_signal.signal_value = 0.6
        mock_signal.confidence = 0.8
        mock_bridge.signal_generator.generate_signal.return_value = mock_signal
        mock_bridge.feature_engine.extract_features.return_value = {}
        mock_regime = Mock()
        mock_regime.regime_type = 'unknown'
        mock_bridge.regime_detector.detect_regime.return_value = mock_regime
        
        symbols = ["AAPL"]
        market_data = {"AAPL": sample_market_data}
        current_date = datetime.now()
        
        # First call
        results1 = mock_bridge.generate_signals_sync(symbols, market_data, current_date)
        
        # Second call - should use cache
        results2 = mock_bridge.generate_signals_sync(symbols, market_data, current_date)
        
        assert results1["AAPL"].source == "core"
        assert results2["AAPL"].source == "cached"
        assert results1["AAPL"].signal_value == results2["AAPL"].signal_value


class TestSignalBridgeFallback:
    """Test SignalBridge fallback mechanisms"""
    
    @pytest.fixture
    def mock_bridge_fallback(self):
        """Create a mock SignalBridge with fallback enabled"""
        with patch('signal_generation.signal_bridge.SignalGenerator'), \
             patch('signal_generation.signal_bridge.EnhancedSignalGenerator'), \
             patch('signal_generation.signal_bridge.AISignalEnhancer'), \
             patch('signal_generation.signal_bridge.RegimeDetector'), \
             patch('signal_generation.signal_bridge.FeatureEngine'):
            
            config = SignalBridgeConfig(enable_fallback=True)
            bridge = SignalBridge(config)
            
            return bridge
    
    def test_fallback_signal_generation(self, mock_bridge_fallback):
        """Test fallback signal generation"""
        # Create market data with clear trend
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        close_prices = np.linspace(100, 150, 50)  # Upward trend
        data = {
            'open': close_prices * 0.99,
            'high': close_prices * 1.02,
            'low': close_prices * 0.98,
            'close': close_prices,
            'volume': np.random.uniform(1000000, 5000000, 50)
        }
        market_data = pd.DataFrame(data, index=dates)
        
        symbols = ["AAPL"]
        current_date = datetime.now()
        
        results = mock_bridge_fallback._generate_fallback_signals(
            symbols, {"AAPL": market_data}, current_date
        )
        
        assert "AAPL" in results
        assert results["AAPL"].source == "fallback"
        assert results["AAPL"].signal_value > 0  # Should be positive for upward trend
        assert results["AAPL"].confidence > 0
    
    def test_fallback_signal_insufficient_data(self, mock_bridge_fallback):
        """Test fallback signal with insufficient data"""
        # Create insufficient market data
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        data = {
            'open': np.random.uniform(100, 200, 10),
            'high': np.random.uniform(100, 200, 10),
            'low': np.random.uniform(100, 200, 10),
            'close': np.random.uniform(100, 200, 10),
            'volume': np.random.uniform(1000000, 5000000, 10)
        }
        market_data = pd.DataFrame(data, index=dates)
        
        symbols = ["AAPL"]
        current_date = datetime.now()
        
        results = mock_bridge_fallback._generate_fallback_signals(
            symbols, {"AAPL": market_data}, current_date
        )
        
        assert "AAPL" in results
        assert results["AAPL"].source == "fallback"
        assert results["AAPL"].signal_value == 0.0
        assert results["AAPL"].error_message == "Insufficient market data"


class TestSignalBridgePerformance:
    """Test SignalBridge performance characteristics"""
    
    @pytest.fixture
    def performance_bridge(self):
        """Create a SignalBridge for performance testing"""
        with patch('signal_generation.signal_bridge.SignalGenerator'), \
             patch('signal_generation.signal_bridge.EnhancedSignalGenerator'), \
             patch('signal_generation.signal_bridge.AISignalEnhancer'), \
             patch('signal_generation.signal_bridge.RegimeDetector'), \
             patch('signal_generation.signal_bridge.FeatureEngine'):
            
            bridge = SignalBridge()
            bridge.signal_generator = Mock()
            bridge.ai_enhancer = Mock()
            bridge.regime_detector = Mock()
            bridge.feature_engine = Mock()
            
            return bridge
    
    def test_performance_stats_tracking(self, performance_bridge):
        """Test performance statistics tracking"""
        # Mock signal generation
        mock_signal = Mock()
        mock_signal.signal_value = 0.5
        mock_signal.confidence = 0.7
        performance_bridge.signal_generator.generate_signal.return_value = mock_signal
        performance_bridge.feature_engine.extract_features.return_value = {}
        mock_regime = Mock()
        mock_regime.regime_type = 'unknown'
        performance_bridge.regime_detector.detect_regime.return_value = mock_regime
        
        # Generate signals
        symbols = ["AAPL", "SPY"]
        market_data = {
            "AAPL": pd.DataFrame({'close': np.random.uniform(100, 200, 50)}),
            "SPY": pd.DataFrame({'close': np.random.uniform(100, 200, 50)})
        }
        current_date = datetime.now()
        
        results = performance_bridge.generate_signals_sync(symbols, market_data, current_date)
        
        # Check performance stats
        stats = performance_bridge.get_performance_stats()
        
        assert stats['total_signals'] == 2
        assert stats['core_signals'] == 2
        assert stats['success_rate'] == 1.0
        assert stats['avg_processing_time'] > 0
    
    def test_concurrent_signal_generation(self, performance_bridge):
        """Test concurrent signal generation performance"""
        # Mock signal generation with delay
        def delayed_signal(*args, **kwargs):
            time.sleep(0.1)  # Simulate processing time
            mock_signal = Mock()
            mock_signal.signal_value = 0.5
            mock_signal.confidence = 0.7
            return mock_signal
        
        performance_bridge.signal_generator.generate_signal.side_effect = delayed_signal
        performance_bridge.feature_engine.extract_features.return_value = {}
        mock_regime = Mock()
        mock_regime.regime_type = 'unknown'
        performance_bridge.regime_detector.detect_regime.return_value = mock_regime
        
        # Generate signals for multiple symbols
        symbols = ["AAPL", "SPY", "MSFT", "GOOGL", "TSLA"]
        market_data = {
            symbol: pd.DataFrame({'close': np.random.uniform(100, 200, 50)})
            for symbol in symbols
        }
        current_date = datetime.now()
        
        start_time = time.time()
        results = performance_bridge.generate_signals_sync(symbols, market_data, current_date)
        end_time = time.time()
        
        # Should be faster than sequential processing (5 * 0.1 = 0.5 seconds)
        # Due to concurrent processing, should be around 0.1-0.2 seconds
        processing_time = end_time - start_time
        assert processing_time < 0.5
        assert len(results) == 5


class TestSignalBridgeIntegration:
    """Test SignalBridge integration with backtesting framework"""
    
    def test_generate_signals_for_backtesting_convenience(self):
        """Test the convenience function for backtesting integration"""
        with patch('signal_generation.signal_bridge.SignalBridge') as mock_bridge_class:
            mock_bridge = Mock()
            mock_bridge_class.return_value = mock_bridge
            
            # Mock signal generation
            mock_result = SignalBridgeResult(
                symbol="AAPL",
                signal_value=0.75,
                confidence=0.8,
                timestamp=datetime.now(),
                source="core"
            )
            mock_bridge.generate_signals_sync.return_value = {"AAPL": mock_result}
            
            symbols = ["AAPL"]
            market_data = {"AAPL": pd.DataFrame({'close': [100, 101, 102]})}
            current_date = datetime.now()
            
            # Test convenience function
            results = generate_signals_for_backtesting(symbols, market_data, current_date)
            
            assert "AAPL" in results
            assert results["AAPL"] == 0.75  # Should return float value
            assert isinstance(results["AAPL"], float)
    
    def test_create_signal_bridge_convenience(self):
        """Test the create_signal_bridge convenience function"""
        with patch('signal_generation.signal_bridge.SignalBridge') as mock_bridge_class:
            mock_bridge = Mock()
            mock_bridge_class.return_value = mock_bridge
            
            # Test with default config
            bridge = create_signal_bridge()
            assert bridge == mock_bridge
            
            # Test with custom config
            config = SignalBridgeConfig(use_ai_enhancement=False)
            bridge = create_signal_bridge(config)
            mock_bridge_class.assert_called_with(config)


class TestSignalBridgeErrorHandling:
    """Test SignalBridge error handling"""
    
    @pytest.fixture
    def error_bridge(self):
        """Create a SignalBridge for error testing"""
        with patch('signal_generation.signal_bridge.SignalGenerator'), \
             patch('signal_generation.signal_bridge.EnhancedSignalGenerator'), \
             patch('signal_generation.signal_bridge.AISignalEnhancer'), \
             patch('signal_generation.signal_bridge.RegimeDetector'), \
             patch('signal_generation.signal_bridge.FeatureEngine'):
            
            config = SignalBridgeConfig(enable_fallback=True)
            bridge = SignalBridge(config)
            
            return bridge
    
    def test_signal_generation_error_with_fallback(self, error_bridge):
        """Test error handling with fallback enabled"""
        # Mock signal generation to raise exception
        error_bridge.signal_generator = Mock()
        error_bridge.signal_generator.generate_signal.side_effect = Exception("Signal generation error")
        
        symbols = ["AAPL"]
        market_data = {"AAPL": pd.DataFrame({'close': np.random.uniform(100, 200, 50)})}
        current_date = datetime.now()
        
        results = error_bridge.generate_signals_sync(symbols, market_data, current_date)
        
        assert "AAPL" in results
        assert results["AAPL"].source == "fallback"
        assert results["AAPL"].signal_value == 0.0  # Fallback should return 0
    
    def test_signal_generation_error_without_fallback(self, error_bridge):
        """Test error handling without fallback"""
        # Disable fallback
        error_bridge.config.enable_fallback = False
        
        # Mock signal generation to raise exception
        error_bridge.signal_generator = Mock()
        error_bridge.signal_generator.generate_signal.side_effect = Exception("Signal generation error")
        
        symbols = ["AAPL"]
        market_data = {"AAPL": pd.DataFrame({'close': np.random.uniform(100, 200, 50)})}
        current_date = datetime.now()
        
        with pytest.raises(Exception):
            error_bridge.generate_signals_sync(symbols, market_data, current_date)


class TestSignalBridgeValidation:
    """Test SignalBridge validation features"""
    
    @pytest.fixture
    def validation_bridge(self):
        """Create a SignalBridge for validation testing"""
        with patch('signal_generation.signal_bridge.SignalGenerator'), \
             patch('signal_generation.signal_bridge.EnhancedSignalGenerator'), \
             patch('signal_generation.signal_bridge.AISignalEnhancer'), \
             patch('signal_generation.signal_bridge.RegimeDetector'), \
             patch('signal_generation.signal_bridge.FeatureEngine'):
            
            config = SignalBridgeConfig(validate_signals=True)
            bridge = SignalBridge(config)
            
            return bridge
    
    def test_signal_validation_extreme_values(self, validation_bridge, caplog):
        """Test validation of extreme signal values"""
        # Create results with extreme values
        results = {
            "AAPL": SignalBridgeResult(
                symbol="AAPL",
                signal_value=3.0,  # Extreme value
                confidence=0.8,
                timestamp=datetime.now(),
                source="core"
            )
        }
        
        validation_bridge._validate_signals(results)
        
        # Check that warning was logged
        assert "Extreme signal value for AAPL: 3.0" in caplog.text
    
    def test_signal_validation_confidence_range(self, validation_bridge, caplog):
        """Test validation of confidence range"""
        # Create results with out-of-range confidence
        results = {
            "AAPL": SignalBridgeResult(
                symbol="AAPL",
                signal_value=0.5,
                confidence=1.5,  # Out of range
                timestamp=datetime.now(),
                source="core"
            )
        }
        
        validation_bridge._validate_signals(results)
        
        # Check that warning was logged
        assert "Signal confidence out of range for AAPL: 1.5" in caplog.text


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 