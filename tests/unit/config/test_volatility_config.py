"""
Unit tests for VolatilityConfig class.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

import pytest
from dataclasses import asdict

from core_engine.config.strategies import VolatilityConfig, StrategyType


class TestVolatilityConfig:
    """Test suite for VolatilityConfig class."""

    def test_initialization(self):
        """Test VolatilityConfig initialization with defaults."""
        config = VolatilityConfig()
        assert config.name == "strategy"  # Inherited from BaseStrategyConfig
        assert config.strategy_type == StrategyType.VOLATILITY
        assert config.volatility_lookback == 20
        assert config.volatility_threshold == 0.02
        assert config.regime_detection is True
        assert config.base_position_pct == 0.025
        assert config.max_position_pct == 0.07
        assert config.volatility_scaling is True
        assert config.vol_target == 0.15

    def test_custom_initialization(self):
        """Test VolatilityConfig initialization with custom values."""
        config = VolatilityConfig(
            volatility_lookback=30,
            volatility_threshold=0.03,
            regime_detection=False,
            base_position_pct=0.02,
            max_position_pct=0.05,
            volatility_scaling=False,
            vol_target=0.12
        )
        
        assert config.volatility_lookback == 30
        assert config.volatility_threshold == 0.03
        assert config.regime_detection is False
        assert config.base_position_pct == 0.02
        assert config.max_position_pct == 0.05
        assert config.volatility_scaling is False
        assert config.vol_target == 0.12

    def test_inheritance_from_base(self):
        """Test that VolatilityConfig inherits from BaseStrategyConfig."""
        config = VolatilityConfig()
        
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
        """Test that VolatilityConfig uses composition pattern for sub-configs."""
        config = VolatilityConfig()
        
        # Test that sub-configs are properly initialized
        assert config.position_limits is not None
        assert config.risk_limits is not None
        assert config.timing is not None
        
        # Test that sub-configs have expected properties
        assert hasattr(config.position_limits, 'max_position_size')
        assert hasattr(config.risk_limits, 'max_daily_var')
        assert hasattr(config.timing, 'health_check_interval')

    def test_serialization(self):
        """Test that VolatilityConfig can be serialized to dict."""
        config = VolatilityConfig()
        config_dict = asdict(config)
        
        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'strategy_type' in config_dict
        assert 'volatility_lookback' in config_dict
        assert 'volatility_threshold' in config_dict
        assert 'regime_detection' in config_dict
        assert 'base_position_pct' in config_dict
        assert 'max_position_pct' in config_dict
        assert 'volatility_scaling' in config_dict
        assert 'vol_target' in config_dict

    def test_strategy_specific_parameters(self):
        """Test strategy-specific parameters are correctly set."""
        config = VolatilityConfig()
        
        # Test volatility-specific parameters
        assert config.volatility_lookback == 20
        assert config.volatility_threshold == 0.02
        assert config.regime_detection is True
        assert config.base_position_pct == 0.025
        assert config.max_position_pct == 0.07
        assert config.volatility_scaling is True
        assert config.vol_target == 0.15

    def test_parameter_validation(self):
        """Test parameter validation (if implemented)."""
        config = VolatilityConfig()
        
        # Test that all parameters are within expected ranges
        assert config.volatility_lookback > 0
        assert config.volatility_threshold > 0
        assert 0 < config.base_position_pct < 1
        assert 0 < config.max_position_pct < 1
        assert config.base_position_pct < config.max_position_pct
        assert 0 < config.vol_target < 1

    def test_custom_name_and_id(self):
        """Test custom name and strategy_id."""
        config = VolatilityConfig(
            name="custom_volatility",
            strategy_id="volatility_001"
        )
        
        assert config.name == "custom_volatility"
        assert config.strategy_id == "volatility_001"
        assert config.strategy_type == StrategyType.VOLATILITY

    def test_multi_timeframe_configuration(self):
        """Test multi-timeframe configuration."""
        config = VolatilityConfig(
            enable_multi_timeframe=True,
            primary_timeframe="5min",
            secondary_timeframes=["15min", "1h"]
        )
        
        assert config.enable_multi_timeframe is True
        assert config.primary_timeframe == "5min"
        assert config.secondary_timeframes == ["15min", "1h"]

    def test_symbol_configuration(self):
        """Test symbol configuration."""
        custom_symbols = ["VIX", "VXX", "UVXY", "SVXY"]
        config = VolatilityConfig(symbols=custom_symbols)
        
        assert config.symbols == custom_symbols
        assert len(config.symbols) == 4
        assert "VIX" in config.symbols
        assert "VXX" in config.symbols
        assert "UVXY" in config.symbols
        assert "SVXY" in config.symbols

    def test_position_sizing_relationship(self):
        """Test that base position is less than max position."""
        config = VolatilityConfig()
        
        # Base position should be less than max position
        assert config.base_position_pct < config.max_position_pct
        
        # Test with custom values
        custom_config = VolatilityConfig(
            base_position_pct=0.01,
            max_position_pct=0.05
        )
        assert custom_config.base_position_pct < custom_config.max_position_pct

    def test_volatility_threshold_range(self):
        """Test volatility threshold is within reasonable range."""
        config = VolatilityConfig()
        
        # Volatility threshold should be reasonable (0.5% to 10%)
        assert 0.005 <= config.volatility_threshold <= 0.10
        
        # Test with custom values
        low_vol_config = VolatilityConfig(volatility_threshold=0.01)
        high_vol_config = VolatilityConfig(volatility_threshold=0.05)
        
        assert 0.005 <= low_vol_config.volatility_threshold <= 0.10
        assert 0.005 <= high_vol_config.volatility_threshold <= 0.10

    def test_volatility_target_range(self):
        """Test volatility target is within reasonable range."""
        config = VolatilityConfig()
        
        # Volatility target should be reasonable (5% to 50%)
        assert 0.05 <= config.vol_target <= 0.50
        
        # Test with custom values
        conservative_config = VolatilityConfig(vol_target=0.08)
        aggressive_config = VolatilityConfig(vol_target=0.25)
        
        assert 0.05 <= conservative_config.vol_target <= 0.50
        assert 0.05 <= aggressive_config.vol_target <= 0.50

    def test_regime_detection_settings(self):
        """Test regime detection settings."""
        # With regime detection
        config_with_regime = VolatilityConfig(regime_detection=True)
        assert config_with_regime.regime_detection is True
        
        # Without regime detection
        config_without_regime = VolatilityConfig(regime_detection=False)
        assert config_without_regime.regime_detection is False

    def test_volatility_scaling_settings(self):
        """Test volatility scaling settings."""
        # With volatility scaling
        config_with_scaling = VolatilityConfig(volatility_scaling=True)
        assert config_with_scaling.volatility_scaling is True
        
        # Without volatility scaling
        config_without_scaling = VolatilityConfig(volatility_scaling=False)
        assert config_without_scaling.volatility_scaling is False

    def test_parameter_combinations(self):
        """Test various parameter combinations."""
        # Conservative volatility strategy
        conservative_config = VolatilityConfig(
            volatility_threshold=0.03,
            base_position_pct=0.015,
            max_position_pct=0.04,
            vol_target=0.10,
            regime_detection=True,
            volatility_scaling=True
        )
        
        assert conservative_config.volatility_threshold == 0.03
        assert conservative_config.base_position_pct == 0.015
        assert conservative_config.max_position_pct == 0.04
        assert conservative_config.vol_target == 0.10
        assert conservative_config.regime_detection is True
        assert conservative_config.volatility_scaling is True
        
        # Aggressive volatility strategy
        aggressive_config = VolatilityConfig(
            volatility_threshold=0.015,
            base_position_pct=0.04,
            max_position_pct=0.10,
            vol_target=0.20,
            regime_detection=False,
            volatility_scaling=False
        )
        
        assert aggressive_config.volatility_threshold == 0.015
        assert aggressive_config.base_position_pct == 0.04
        assert aggressive_config.max_position_pct == 0.10
        assert aggressive_config.vol_target == 0.20
        assert aggressive_config.regime_detection is False
        assert aggressive_config.volatility_scaling is False

    def test_boolean_settings(self):
        """Test boolean settings behavior."""
        config_true_regime = VolatilityConfig(regime_detection=True)
        config_false_regime = VolatilityConfig(regime_detection=False)
        config_true_scaling = VolatilityConfig(volatility_scaling=True)
        config_false_scaling = VolatilityConfig(volatility_scaling=False)
        
        assert config_true_regime.regime_detection is True
        assert config_false_regime.regime_detection is False
        assert config_true_scaling.volatility_scaling is True
        assert config_false_scaling.volatility_scaling is False
        
        # Test that boolean values are preserved
        assert isinstance(config_true_regime.regime_detection, bool)
        assert isinstance(config_false_regime.regime_detection, bool)
        assert isinstance(config_true_scaling.volatility_scaling, bool)
        assert isinstance(config_false_scaling.volatility_scaling, bool)

    def test_volatility_lookback_variations(self):
        """Test different volatility lookback period settings."""
        # Short-term volatility
        short_config = VolatilityConfig(volatility_lookback=10)
        assert short_config.volatility_lookback == 10
        
        # Medium-term volatility
        medium_config = VolatilityConfig(volatility_lookback=30)
        assert medium_config.volatility_lookback == 30
        
        # Long-term volatility (default)
        long_config = VolatilityConfig()
        assert long_config.volatility_lookback == 20
