"""
Unit tests for TrendFollowingConfig class.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

from dataclasses import asdict

from core_engine.config.strategies import TrendFollowingConfig, StrategyType


class TestTrendFollowingConfig:
    """Test suite for TrendFollowingConfig class."""

    def test_initialization(self):
        """Test TrendFollowingConfig initialization with defaults."""
        config = TrendFollowingConfig()
        assert config.name == "strategy"  # Inherited from BaseStrategyConfig
        assert config.strategy_type == StrategyType.TREND_FOLLOWING
        assert config.fast_ma_period == 50
        assert config.slow_ma_period == 200
        assert config.adx_period == 14
        assert config.adx_threshold == 25.0
        assert config.atr_period == 14
        assert config.atr_multiplier == 2.0

    def test_custom_initialization(self):
        """Test TrendFollowingConfig initialization with custom values."""
        config = TrendFollowingConfig(
            fast_ma_period=30,
            slow_ma_period=150,
            adx_period=21,
            adx_threshold=30.0,
            atr_period=21,
            atr_multiplier=2.5
        )
        
        assert config.fast_ma_period == 30
        assert config.slow_ma_period == 150
        assert config.adx_period == 21
        assert config.adx_threshold == 30.0
        assert config.atr_period == 21
        assert config.atr_multiplier == 2.5

    def test_inheritance_from_base(self):
        """Test that TrendFollowingConfig inherits from BaseStrategyConfig."""
        config = TrendFollowingConfig()
        
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
        """Test that TrendFollowingConfig uses composition pattern for sub-configs."""
        config = TrendFollowingConfig()
        
        # Test that sub-configs are properly initialized
        assert config.position_limits is not None
        assert config.risk_limits is not None
        assert config.timing is not None
        
        # Test that sub-configs have expected properties
        assert hasattr(config.position_limits, 'max_position_size')
        assert hasattr(config.risk_limits, 'max_daily_var')
        assert hasattr(config.timing, 'health_check_interval')

    def test_serialization(self):
        """Test that TrendFollowingConfig can be serialized to dict."""
        config = TrendFollowingConfig()
        config_dict = asdict(config)
        
        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'strategy_type' in config_dict
        assert 'fast_ma_period' in config_dict
        assert 'slow_ma_period' in config_dict
        assert 'adx_period' in config_dict
        assert 'adx_threshold' in config_dict
        assert 'atr_period' in config_dict
        assert 'atr_multiplier' in config_dict

    def test_strategy_specific_parameters(self):
        """Test strategy-specific parameters are correctly set."""
        config = TrendFollowingConfig()
        
        # Test trend following-specific parameters
        assert config.fast_ma_period == 50
        assert config.slow_ma_period == 200
        assert config.adx_period == 14
        assert config.adx_threshold == 25.0
        assert config.atr_period == 14
        assert config.atr_multiplier == 2.0

    def test_parameter_validation(self):
        """Test parameter validation (if implemented)."""
        config = TrendFollowingConfig()
        
        # Test that all parameters are within expected ranges
        assert config.fast_ma_period > 0
        assert config.slow_ma_period > 0
        assert config.fast_ma_period < config.slow_ma_period  # Fast should be less than slow
        assert config.adx_period > 0
        assert config.adx_threshold > 0
        assert config.atr_period > 0
        assert config.atr_multiplier > 0

    def test_custom_name_and_id(self):
        """Test custom name and strategy_id."""
        config = TrendFollowingConfig(
            name="custom_trend_following",
            strategy_id="trend_following_001"
        )
        
        assert config.name == "custom_trend_following"
        assert config.strategy_id == "trend_following_001"
        assert config.strategy_type == StrategyType.TREND_FOLLOWING

    def test_multi_timeframe_configuration(self):
        """Test multi-timeframe configuration."""
        config = TrendFollowingConfig(
            enable_multi_timeframe=True,
            primary_timeframe="1h",
            secondary_timeframes=["4h", "1D"]
        )
        
        assert config.enable_multi_timeframe is True
        assert config.primary_timeframe == "1h"
        assert config.secondary_timeframes == ["4h", "1D"]

    def test_symbol_configuration(self):
        """Test symbol configuration."""
        custom_symbols = ["SPY", "QQQ", "IWM", "EFA"]
        config = TrendFollowingConfig(symbols=custom_symbols)
        
        assert config.symbols == custom_symbols
        assert len(config.symbols) == 4
        assert "SPY" in config.symbols
        assert "QQQ" in config.symbols
        assert "IWM" in config.symbols
        assert "EFA" in config.symbols

    def test_ma_period_relationship(self):
        """Test that fast MA period is less than slow MA period."""
        config = TrendFollowingConfig()
        
        # Fast MA should be less than slow MA
        assert config.fast_ma_period < config.slow_ma_period
        
        # Test with custom values
        custom_config = TrendFollowingConfig(
            fast_ma_period=20,
            slow_ma_period=50
        )
        assert custom_config.fast_ma_period < custom_config.slow_ma_period

    def test_trend_strength_parameters(self):
        """Test trend strength detection parameters."""
        config = TrendFollowingConfig(
            adx_period=21,
            adx_threshold=30.0
        )
        
        assert config.adx_period == 21
        assert config.adx_threshold == 30.0
        
        # ADX threshold should be reasonable for trend detection
        assert 20 <= config.adx_threshold <= 50

    def test_volatility_parameters(self):
        """Test volatility-based parameters."""
        config = TrendFollowingConfig(
            atr_period=21,
            atr_multiplier=2.5
        )
        
        assert config.atr_period == 21
        assert config.atr_multiplier == 2.5
        
        # ATR multiplier should be reasonable for stop losses
        assert 1.0 <= config.atr_multiplier <= 5.0

    def test_parameter_combinations(self):
        """Test various parameter combinations."""
        # Conservative trend following
        conservative_config = TrendFollowingConfig(
            fast_ma_period=100,
            slow_ma_period=300,
            adx_threshold=35.0,
            atr_multiplier=3.0
        )
        
        assert conservative_config.fast_ma_period == 100
        assert conservative_config.slow_ma_period == 300
        assert conservative_config.adx_threshold == 35.0
        assert conservative_config.atr_multiplier == 3.0
        
        # Aggressive trend following
        aggressive_config = TrendFollowingConfig(
            fast_ma_period=20,
            slow_ma_period=50,
            adx_threshold=20.0,
            atr_multiplier=1.5
        )
        
        assert aggressive_config.fast_ma_period == 20
        assert aggressive_config.slow_ma_period == 50
        assert aggressive_config.adx_threshold == 20.0
        assert aggressive_config.atr_multiplier == 1.5
