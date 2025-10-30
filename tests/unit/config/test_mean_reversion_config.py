"""
Unit tests for MeanReversionConfig class.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

import pytest
from dataclasses import asdict

from core_engine.config.strategies import MeanReversionConfig, StrategyType


class TestMeanReversionConfig:
    """Test suite for MeanReversionConfig class."""

    def test_initialization(self):
        """Test MeanReversionConfig initialization with defaults."""
        config = MeanReversionConfig()
        assert config.strategy_type == StrategyType.MEAN_REVERSION
        assert config.lookback_period == 20
        assert config.zscore_entry_threshold == 2.0
        assert config.zscore_exit_threshold == 0.5
        assert config.bollinger_period == 20
        assert config.bollinger_std == 2.0
        assert config.rsi_period == 14
        assert config.rsi_oversold == 30
        assert config.rsi_overbought == 70

    def test_custom_initialization(self):
        """Test MeanReversionConfig initialization with custom values."""
        config = MeanReversionConfig(
            lookback_period=30,
            zscore_entry_threshold=2.5,
            zscore_exit_threshold=0.3,
            bollinger_period=25,
            bollinger_std=2.5,
            rsi_period=21,
            rsi_oversold=25,
            rsi_overbought=75
        )
        assert config.lookback_period == 30
        assert config.zscore_entry_threshold == 2.5
        assert config.zscore_exit_threshold == 0.3
        assert config.bollinger_period == 25
        assert config.bollinger_std == 2.5
        assert config.rsi_period == 21
        assert config.rsi_oversold == 25
        assert config.rsi_overbought == 75

    def test_inheritance_from_base(self):
        """Test that MeanReversionConfig inherits from BaseStrategyConfig."""
        config = MeanReversionConfig()
        
        # Test inherited properties
        assert hasattr(config, 'name')
        assert hasattr(config, 'strategy_type')
        assert hasattr(config, 'position_limits')
        assert hasattr(config, 'risk_limits')
        assert hasattr(config, 'timing')
        assert hasattr(config, 'symbols')
        assert hasattr(config, 'profit_target_ratio')
        assert hasattr(config, 'execution_timeout')
        
        # Test inherited default values
        assert config.symbols == ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        assert config.profit_target_ratio == 2.0
        assert config.execution_timeout == 30.0

    def test_composition_pattern(self):
        """Test that MeanReversionConfig uses composition pattern for sub-configs."""
        config = MeanReversionConfig()
        
        # Test that sub-configs are properly initialized
        assert config.position_limits is not None
        assert config.risk_limits is not None
        assert config.timing is not None
        
        # Test that sub-configs have expected properties
        assert hasattr(config.position_limits, 'max_position_size')
        assert hasattr(config.risk_limits, 'max_daily_var')
        assert hasattr(config.timing, 'health_check_interval')

    def test_serialization(self):
        """Test that MeanReversionConfig can be serialized to dict."""
        config = MeanReversionConfig()
        config_dict = asdict(config)
        
        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'strategy_type' in config_dict
        assert 'lookback_period' in config_dict
        assert 'zscore_entry_threshold' in config_dict
        assert 'zscore_exit_threshold' in config_dict
        assert 'bollinger_period' in config_dict
        assert 'bollinger_std' in config_dict
        assert 'rsi_period' in config_dict

    def test_strategy_specific_parameters(self):
        """Test strategy-specific parameters are correctly set."""
        config = MeanReversionConfig()
        
        # Test mean reversion-specific parameters
        assert config.lookback_period == 20
        assert config.zscore_entry_threshold == 2.0
        assert config.zscore_exit_threshold == 0.5
        
        # Test Bollinger Bands parameters
        assert config.bollinger_period == 20
        assert config.bollinger_std == 2.0
        
        # Test RSI parameters
        assert config.rsi_period == 14
        assert config.rsi_oversold == 30
        assert config.rsi_overbought == 70

    def test_parameter_validation(self):
        """Test parameter validation (if implemented)."""
        config = MeanReversionConfig()
        
        # Test that all parameters are within expected ranges
        assert config.lookback_period > 0
        assert config.zscore_entry_threshold > 0
        assert config.zscore_exit_threshold > 0
        assert config.bollinger_period > 0
        assert config.bollinger_std > 0
        assert config.rsi_period > 0
        assert 0 < config.rsi_oversold < 100
        assert 0 < config.rsi_overbought < 100

    def test_custom_name_and_id(self):
        """Test custom name and strategy_id."""
        config = MeanReversionConfig(
            name="custom_mean_reversion",
            strategy_id="mean_reversion_001"
        )
        
        assert config.name == "custom_mean_reversion"
        assert config.strategy_id == "mean_reversion_001"
        assert config.strategy_type == StrategyType.MEAN_REVERSION

    def test_multi_timeframe_configuration(self):
        """Test multi-timeframe configuration."""
        config = MeanReversionConfig(
            enable_multi_timeframe=True,
            primary_timeframe="5min",
            secondary_timeframes=["15min", "1h"]
        )
        
        assert config.enable_multi_timeframe is True
        assert config.primary_timeframe == "5min"
        assert config.secondary_timeframes == ["15min", "1h"]

    def test_symbol_configuration(self):
        """Test symbol configuration."""
        custom_symbols = ["AAPL", "GOOGL", "MSFT"]
        config = MeanReversionConfig(symbols=custom_symbols)
        
        assert config.symbols == custom_symbols
        assert len(config.symbols) == 3
        assert "AAPL" in config.symbols
        assert "GOOGL" in config.symbols
        assert "MSFT" in config.symbols

    def test_zscore_thresholds_relationship(self):
        """Test that zscore thresholds have proper relationship."""
        config = MeanReversionConfig()
        
        # Entry threshold should be higher than exit threshold
        assert config.zscore_entry_threshold > config.zscore_exit_threshold
        
        # Both should be positive
        assert config.zscore_entry_threshold > 0
        assert config.zscore_exit_threshold > 0

    def test_rsi_thresholds_relationship(self):
        """Test that RSI thresholds have proper relationship."""
        config = MeanReversionConfig()
        
        # Overbought should be higher than oversold
        assert config.rsi_overbought > config.rsi_oversold
        
        # Both should be within valid RSI range (0-100)
        assert 0 <= config.rsi_oversold <= 100
        assert 0 <= config.rsi_overbought <= 100

    def test_bollinger_bands_parameters(self):
        """Test Bollinger Bands specific parameters."""
        config = MeanReversionConfig()
        
        # Period should be positive
        assert config.bollinger_period > 0
        
        # Standard deviation should be positive
        assert config.bollinger_std > 0
        
        # Common values are 1, 2, 2.5
        assert config.bollinger_std in [1.0, 2.0, 2.5, 3.0] or config.bollinger_std > 0
