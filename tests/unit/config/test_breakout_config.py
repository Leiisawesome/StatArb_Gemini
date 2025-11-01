"""
Unit tests for BreakoutConfig class.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

from dataclasses import asdict

from core_engine.config.strategies import BreakoutConfig, StrategyType


class TestBreakoutConfig:
    """Test suite for BreakoutConfig class."""

    def test_initialization(self):
        """Test BreakoutConfig initialization with defaults."""
        config = BreakoutConfig()
        assert config.name == "strategy"  # Inherited from BaseStrategyConfig
        assert config.strategy_type == StrategyType.BREAKOUT
        assert config.lookback_period == 20
        assert config.breakout_threshold == 0.02
        assert config.volume_confirmation is True
        assert config.volume_multiplier == 1.5
        assert config.consolidation_periods == 10

    def test_custom_initialization(self):
        """Test BreakoutConfig initialization with custom values."""
        config = BreakoutConfig(
            lookback_period=30,
            breakout_threshold=0.03,
            volume_confirmation=False,
            volume_multiplier=2.0,
            consolidation_periods=15
        )
        
        assert config.lookback_period == 30
        assert config.breakout_threshold == 0.03
        assert config.volume_confirmation is False
        assert config.volume_multiplier == 2.0
        assert config.consolidation_periods == 15

    def test_inheritance_from_base(self):
        """Test that BreakoutConfig inherits from BaseStrategyConfig."""
        config = BreakoutConfig()
        
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
        """Test that BreakoutConfig uses composition pattern for sub-configs."""
        config = BreakoutConfig()
        
        # Test that sub-configs are properly initialized
        assert config.position_limits is not None
        assert config.risk_limits is not None
        assert config.timing is not None
        
        # Test that sub-configs have expected properties
        assert hasattr(config.position_limits, 'max_position_size')
        assert hasattr(config.risk_limits, 'max_daily_var')
        assert hasattr(config.timing, 'health_check_interval')

    def test_serialization(self):
        """Test that BreakoutConfig can be serialized to dict."""
        config = BreakoutConfig()
        config_dict = asdict(config)
        
        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'strategy_type' in config_dict
        assert 'lookback_period' in config_dict
        assert 'breakout_threshold' in config_dict
        assert 'volume_confirmation' in config_dict
        assert 'volume_multiplier' in config_dict
        assert 'consolidation_periods' in config_dict

    def test_strategy_specific_parameters(self):
        """Test strategy-specific parameters are correctly set."""
        config = BreakoutConfig()
        
        # Test breakout-specific parameters
        assert config.lookback_period == 20
        assert config.breakout_threshold == 0.02
        assert config.volume_confirmation is True
        assert config.volume_multiplier == 1.5
        assert config.consolidation_periods == 10

    def test_parameter_validation(self):
        """Test parameter validation (if implemented)."""
        config = BreakoutConfig()
        
        # Test that all parameters are within expected ranges
        assert config.lookback_period > 0
        assert config.breakout_threshold > 0
        assert config.volume_multiplier > 0
        assert config.consolidation_periods > 0
        
        # Breakout threshold should be reasonable (1-10%)
        assert 0.01 <= config.breakout_threshold <= 0.10

    def test_custom_name_and_id(self):
        """Test custom name and strategy_id."""
        config = BreakoutConfig(
            name="custom_breakout",
            strategy_id="breakout_001"
        )
        
        assert config.name == "custom_breakout"
        assert config.strategy_id == "breakout_001"
        assert config.strategy_type == StrategyType.BREAKOUT

    def test_multi_timeframe_configuration(self):
        """Test multi-timeframe configuration."""
        config = BreakoutConfig(
            enable_multi_timeframe=True,
            primary_timeframe="5min",
            secondary_timeframes=["15min", "1h"]
        )
        
        assert config.enable_multi_timeframe is True
        assert config.primary_timeframe == "5min"
        assert config.secondary_timeframes == ["15min", "1h"]

    def test_symbol_configuration(self):
        """Test symbol configuration."""
        custom_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
        config = BreakoutConfig(symbols=custom_symbols)
        
        assert config.symbols == custom_symbols
        assert len(config.symbols) == 5
        assert "AAPL" in config.symbols
        assert "GOOGL" in config.symbols
        assert "MSFT" in config.symbols
        assert "TSLA" in config.symbols
        assert "NVDA" in config.symbols

    def test_volume_confirmation_settings(self):
        """Test volume confirmation settings."""
        # With volume confirmation
        config_with_volume = BreakoutConfig(
            volume_confirmation=True,
            volume_multiplier=2.0
        )
        
        assert config_with_volume.volume_confirmation is True
        assert config_with_volume.volume_multiplier == 2.0
        
        # Without volume confirmation
        config_without_volume = BreakoutConfig(
            volume_confirmation=False,
            volume_multiplier=1.0
        )
        
        assert config_without_volume.volume_confirmation is False
        assert config_without_volume.volume_multiplier == 1.0

    def test_breakout_threshold_variations(self):
        """Test different breakout threshold settings."""
        # Conservative breakout
        conservative_config = BreakoutConfig(
            breakout_threshold=0.05  # 5%
        )
        assert conservative_config.breakout_threshold == 0.05
        
        # Aggressive breakout
        aggressive_config = BreakoutConfig(
            breakout_threshold=0.01  # 1%
        )
        assert aggressive_config.breakout_threshold == 0.01
        
        # Default breakout
        default_config = BreakoutConfig()
        assert default_config.breakout_threshold == 0.02  # 2%

    def test_consolidation_detection_parameters(self):
        """Test consolidation detection parameters."""
        config = BreakoutConfig(
            consolidation_periods=20,
            lookback_period=50
        )
        
        assert config.consolidation_periods == 20
        assert config.lookback_period == 50
        
        # Consolidation periods should be less than lookback period
        assert config.consolidation_periods < config.lookback_period

    def test_parameter_combinations(self):
        """Test various parameter combinations."""
        # High-frequency breakout strategy
        hf_config = BreakoutConfig(
            lookback_period=10,
            breakout_threshold=0.01,
            volume_confirmation=True,
            volume_multiplier=1.2,
            consolidation_periods=5
        )
        
        assert hf_config.lookback_period == 10
        assert hf_config.breakout_threshold == 0.01
        assert hf_config.volume_confirmation is True
        assert hf_config.volume_multiplier == 1.2
        assert hf_config.consolidation_periods == 5
        
        # Swing trading breakout strategy
        swing_config = BreakoutConfig(
            lookback_period=50,
            breakout_threshold=0.05,
            volume_confirmation=True,
            volume_multiplier=2.0,
            consolidation_periods=20
        )
        
        assert swing_config.lookback_period == 50
        assert swing_config.breakout_threshold == 0.05
        assert swing_config.volume_confirmation is True
        assert swing_config.volume_multiplier == 2.0
        assert swing_config.consolidation_periods == 20

    def test_boolean_volume_confirmation(self):
        """Test volume confirmation boolean behavior."""
        config_true = BreakoutConfig(volume_confirmation=True)
        config_false = BreakoutConfig(volume_confirmation=False)
        
        assert config_true.volume_confirmation is True
        assert config_false.volume_confirmation is False
        
        # Test that boolean values are preserved
        assert isinstance(config_true.volume_confirmation, bool)
        assert isinstance(config_false.volume_confirmation, bool)
