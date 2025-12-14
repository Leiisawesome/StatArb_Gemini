"""
Unit tests for ArbitrageConfig class.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

from dataclasses import asdict

from core_engine.config.strategies import ArbitrageConfig, StrategyType

class TestArbitrageConfig:
    """Test suite for ArbitrageConfig class."""

    def test_initialization(self):
        """Test ArbitrageConfig initialization with defaults."""
        config = ArbitrageConfig()
        assert config.name == "strategy"  # Inherited from BaseStrategyConfig
        assert config.strategy_type == StrategyType.ARBITRAGE
        assert config.min_spread_bps == 5.0
        assert config.max_spread_bps == 50.0
        assert config.confidence_threshold == 0.8
        assert config.execution_speed == 'fast'
        assert config.max_execution_time == 5.0
        assert config.enable_multi_venue is True

    def test_custom_initialization(self):
        """Test ArbitrageConfig initialization with custom values."""
        config = ArbitrageConfig(
            min_spread_bps=10.0,
            max_spread_bps=100.0,
            confidence_threshold=0.9,
            execution_speed='normal',
            max_execution_time=10.0,
            enable_multi_venue=False
        )

        assert config.min_spread_bps == 10.0
        assert config.max_spread_bps == 100.0
        assert config.confidence_threshold == 0.9
        assert config.execution_speed == 'normal'
        assert config.max_execution_time == 10.0
        assert config.enable_multi_venue is False

    def test_inheritance_from_base(self):
        """Test that ArbitrageConfig inherits from BaseStrategyConfig."""
        config = ArbitrageConfig()

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
        """Test that ArbitrageConfig uses composition pattern for sub-configs."""
        config = ArbitrageConfig()

        # Test that sub-configs are properly initialized
        assert config.position_limits is not None
        assert config.risk_limits is not None
        assert config.timing is not None

        # Test that sub-configs have expected properties
        assert hasattr(config.position_limits, 'max_position_size')
        assert hasattr(config.risk_limits, 'max_daily_var')
        assert hasattr(config.timing, 'health_check_interval')

    def test_serialization(self):
        """Test that ArbitrageConfig can be serialized to dict."""
        config = ArbitrageConfig()
        config_dict = asdict(config)

        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'strategy_type' in config_dict
        assert 'min_spread_bps' in config_dict
        assert 'max_spread_bps' in config_dict
        assert 'confidence_threshold' in config_dict
        assert 'execution_speed' in config_dict
        assert 'max_execution_time' in config_dict
        assert 'enable_multi_venue' in config_dict

    def test_strategy_specific_parameters(self):
        """Test strategy-specific parameters are correctly set."""
        config = ArbitrageConfig()

        # Test arbitrage-specific parameters
        assert config.min_spread_bps == 5.0
        assert config.max_spread_bps == 50.0
        assert config.confidence_threshold == 0.8
        assert config.execution_speed == 'fast'
        assert config.max_execution_time == 5.0
        assert config.enable_multi_venue is True

    def test_parameter_validation(self):
        """Test parameter validation (if implemented)."""
        config = ArbitrageConfig()

        # Test that all parameters are within expected ranges
        assert config.min_spread_bps > 0
        assert config.max_spread_bps > 0
        assert config.min_spread_bps < config.max_spread_bps
        assert 0 < config.confidence_threshold <= 1
        assert config.max_execution_time > 0
        assert config.execution_speed in ['fast', 'normal']

    def test_custom_name_and_id(self):
        """Test custom name and strategy_id."""
        config = ArbitrageConfig(
            name="custom_arbitrage",
            strategy_id="arbitrage_001"
        )

        assert config.name == "custom_arbitrage"
        assert config.strategy_id == "arbitrage_001"
        assert config.strategy_type == StrategyType.ARBITRAGE

    def test_multi_timeframe_configuration(self):
        """Test multi-timeframe configuration."""
        config = ArbitrageConfig(
            enable_multi_timeframe=True,
            primary_timeframe="1min",
            secondary_timeframes=["5min", "15min"]
        )

        assert config.enable_multi_timeframe is True
        assert config.primary_timeframe == "1min"
        assert config.secondary_timeframes == ["5min", "15min"]

    def test_symbol_configuration(self):
        """Test symbol configuration."""
        custom_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"]
        config = ArbitrageConfig(symbols=custom_symbols)

        assert config.symbols == custom_symbols
        assert len(config.symbols) == 7
        assert "AAPL" in config.symbols
        assert "MSFT" in config.symbols
        assert "GOOGL" in config.symbols
        assert "AMZN" in config.symbols
        assert "TSLA" in config.symbols
        assert "META" in config.symbols
        assert "NVDA" in config.symbols

    def test_spread_threshold_relationship(self):
        """Test that min spread is less than max spread."""
        config = ArbitrageConfig()

        # Min spread should be less than max spread
        assert config.min_spread_bps < config.max_spread_bps

        # Test with custom values
        custom_config = ArbitrageConfig(
            min_spread_bps=15.0,
            max_spread_bps=75.0
        )
        assert custom_config.min_spread_bps < custom_config.max_spread_bps

    def test_confidence_threshold_range(self):
        """Test confidence threshold is within valid range."""
        config = ArbitrageConfig()

        # Confidence threshold should be between 0 and 1
        assert 0 < config.confidence_threshold <= 1

        # Test with custom values
        high_confidence_config = ArbitrageConfig(confidence_threshold=0.95)
        low_confidence_config = ArbitrageConfig(confidence_threshold=0.6)

        assert 0 < high_confidence_config.confidence_threshold <= 1
        assert 0 < low_confidence_config.confidence_threshold <= 1

    def test_execution_speed_options(self):
        """Test execution speed options."""
        # Fast execution
        fast_config = ArbitrageConfig(execution_speed='fast')
        assert fast_config.execution_speed == 'fast'

        # Normal execution
        normal_config = ArbitrageConfig(execution_speed='normal')
        assert normal_config.execution_speed == 'normal'

        # Default should be fast
        default_config = ArbitrageConfig()
        assert default_config.execution_speed == 'fast'

    def test_execution_time_limits(self):
        """Test execution time limits."""
        config = ArbitrageConfig()

        # Max execution time should be reasonable for arbitrage
        assert 0 < config.max_execution_time <= 60  # Max 1 minute

        # Test with custom values
        quick_config = ArbitrageConfig(max_execution_time=2.0)
        slow_config = ArbitrageConfig(max_execution_time=15.0)

        assert 0 < quick_config.max_execution_time <= 60
        assert 0 < slow_config.max_execution_time <= 60

    def test_multi_venue_settings(self):
        """Test multi-venue settings."""
        # With multi-venue
        multi_venue_config = ArbitrageConfig(enable_multi_venue=True)
        assert multi_venue_config.enable_multi_venue is True

        # Without multi-venue
        single_venue_config = ArbitrageConfig(enable_multi_venue=False)
        assert single_venue_config.enable_multi_venue is False

    def test_parameter_combinations(self):
        """Test various parameter combinations."""
        # High-frequency arbitrage
        hf_config = ArbitrageConfig(
            min_spread_bps=2.0,
            max_spread_bps=20.0,
            confidence_threshold=0.9,
            execution_speed='fast',
            max_execution_time=1.0,
            enable_multi_venue=True
        )

        assert hf_config.min_spread_bps == 2.0
        assert hf_config.max_spread_bps == 20.0
        assert hf_config.confidence_threshold == 0.9
        assert hf_config.execution_speed == 'fast'
        assert hf_config.max_execution_time == 1.0
        assert hf_config.enable_multi_venue is True

        # Conservative arbitrage
        conservative_config = ArbitrageConfig(
            min_spread_bps=10.0,
            max_spread_bps=100.0,
            confidence_threshold=0.95,
            execution_speed='normal',
            max_execution_time=10.0,
            enable_multi_venue=False
        )

        assert conservative_config.min_spread_bps == 10.0
        assert conservative_config.max_spread_bps == 100.0
        assert conservative_config.confidence_threshold == 0.95
        assert conservative_config.execution_speed == 'normal'
        assert conservative_config.max_execution_time == 10.0
        assert conservative_config.enable_multi_venue is False

    def test_boolean_settings(self):
        """Test boolean settings behavior."""
        config_true = ArbitrageConfig(enable_multi_venue=True)
        config_false = ArbitrageConfig(enable_multi_venue=False)

        assert config_true.enable_multi_venue is True
        assert config_false.enable_multi_venue is False

        # Test that boolean values are preserved
        assert isinstance(config_true.enable_multi_venue, bool)
        assert isinstance(config_false.enable_multi_venue, bool)

    def test_spread_threshold_variations(self):
        """Test different spread threshold settings."""
        # Tight spreads (high-frequency)
        tight_config = ArbitrageConfig(
            min_spread_bps=1.0,
            max_spread_bps=10.0
        )
        assert tight_config.min_spread_bps == 1.0
        assert tight_config.max_spread_bps == 10.0

        # Wide spreads (conservative)
        wide_config = ArbitrageConfig(
            min_spread_bps=20.0,
            max_spread_bps=200.0
        )
        assert wide_config.min_spread_bps == 20.0
        assert wide_config.max_spread_bps == 200.0

        # Default spreads
        default_config = ArbitrageConfig()
        assert default_config.min_spread_bps == 5.0
        assert default_config.max_spread_bps == 50.0
