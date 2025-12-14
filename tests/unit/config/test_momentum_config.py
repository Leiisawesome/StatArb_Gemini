"""
Unit tests for MomentumConfig class.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

from dataclasses import asdict

from core_engine.config.strategies import MomentumConfig, StrategyType

class TestMomentumConfig:
    """Test suite for MomentumConfig class."""

    def test_initialization(self):
        """Test MomentumConfig initialization with defaults."""
        config = MomentumConfig()
        assert config.name == "strategy"  # Inherited from BaseStrategyConfig
        assert config.strategy_type == StrategyType.MOMENTUM
        assert config.lookback_period == 60
        assert config.short_period == 10
        assert config.medium_period == 20
        assert config.long_period == 50
        assert config.momentum_threshold == 0.02
        assert config.rsi_period == 14
        assert config.rsi_overbought == 70.0
        assert config.rsi_oversold == 30.0
        assert config.adx_period == 14
        assert config.adx_threshold == 25.0
        assert config.volume_ma_period == 20
        assert config.volume_threshold == 1.2

    def test_custom_initialization(self):
        """Test MomentumConfig initialization with custom values."""
        config = MomentumConfig(
            lookback_period=90,
            momentum_threshold=0.03,
            rsi_period=21,
            rsi_overbought=75.0,
            rsi_oversold=25.0,
            adx_period=21,
            adx_threshold=30.0,
            volume_ma_period=30,
            volume_threshold=1.5
        )
        assert config.lookback_period == 90
        assert config.momentum_threshold == 0.03
        assert config.rsi_period == 21
        assert config.rsi_overbought == 75.0
        assert config.rsi_oversold == 25.0
        assert config.adx_period == 21
        assert config.adx_threshold == 30.0
        assert config.volume_ma_period == 30
        assert config.volume_threshold == 1.5

    def test_inheritance_from_base(self):
        """Test that MomentumConfig inherits from BaseStrategyConfig."""
        config = MomentumConfig()

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
        """Test that MomentumConfig uses composition pattern for sub-configs."""
        config = MomentumConfig()

        # Test that sub-configs are properly initialized
        assert config.position_limits is not None
        assert config.risk_limits is not None
        assert config.timing is not None

        # Test that sub-configs have expected properties
        assert hasattr(config.position_limits, 'max_position_size')
        assert hasattr(config.risk_limits, 'max_daily_var')
        assert hasattr(config.timing, 'health_check_interval')

    def test_serialization(self):
        """Test that MomentumConfig can be serialized to dict."""
        config = MomentumConfig()
        config_dict = asdict(config)

        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'strategy_type' in config_dict
        assert 'lookback_period' in config_dict
        assert 'momentum_threshold' in config_dict
        assert 'rsi_period' in config_dict
        assert 'adx_period' in config_dict
        assert 'volume_threshold' in config_dict

    def test_strategy_specific_parameters(self):
        """Test strategy-specific parameters are correctly set."""
        config = MomentumConfig()

        # Test momentum-specific parameters
        assert config.lookback_period == 60
        assert config.short_period == 10
        assert config.medium_period == 20
        assert config.long_period == 50
        assert config.momentum_threshold == 0.02

        # Test technical indicator parameters
        assert config.rsi_period == 14
        assert config.rsi_overbought == 70.0
        assert config.rsi_oversold == 30.0
        assert config.adx_period == 14
        assert config.adx_threshold == 25.0

        # Test volume parameters
        assert config.volume_ma_period == 20
        assert config.volume_threshold == 1.2

    def test_parameter_validation(self):
        """Test parameter validation (if implemented)."""
        config = MomentumConfig()

        # Test that all parameters are within expected ranges
        assert config.lookback_period > 0
        assert config.short_period > 0
        assert config.medium_period > 0
        assert config.long_period > 0
        assert 0 < config.momentum_threshold < 1
        assert config.rsi_period > 0
        assert 0 < config.rsi_overbought < 100
        assert 0 < config.rsi_oversold < 100
        assert config.adx_period > 0
        assert config.adx_threshold > 0
        assert config.volume_ma_period > 0
        assert config.volume_threshold > 0

    def test_custom_name_and_id(self):
        """Test custom name and strategy_id."""
        config = MomentumConfig(
            name="custom_momentum",
            strategy_id="momentum_001"
        )

        assert config.name == "custom_momentum"
        assert config.strategy_id == "momentum_001"
        assert config.strategy_type == StrategyType.MOMENTUM

    def test_multi_timeframe_configuration(self):
        """Test multi-timeframe configuration."""
        config = MomentumConfig(
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
        config = MomentumConfig(symbols=custom_symbols)

        assert config.symbols == custom_symbols
        assert len(config.symbols) == 3
        assert "AAPL" in config.symbols
        assert "GOOGL" in config.symbols
        assert "MSFT" in config.symbols
