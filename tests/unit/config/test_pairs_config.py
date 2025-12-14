"""
Unit tests for PairsConfig class.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

from dataclasses import asdict

from core_engine.config.strategies import PairsConfig, StrategyType

class TestPairsConfig:
    """Test suite for PairsConfig class."""

    def test_initialization(self):
        """Test PairsConfig initialization with defaults."""
        config = PairsConfig()
        assert config.name == "strategy"  # Inherited from BaseStrategyConfig
        assert config.strategy_type == StrategyType.PAIRS_TRADING
        assert config.lookback_period == 252
        assert config.correlation_threshold == 0.5
        assert config.cointegration_threshold == 0.05
        assert config.entry_zscore_threshold == 2.0
        assert config.exit_zscore_threshold == 0.5
        assert config.max_pairs == 5
        assert config.pair_reselection_frequency == 20

    def test_custom_initialization(self):
        """Test PairsConfig initialization with custom values."""
        config = PairsConfig(
            lookback_period=180,
            correlation_threshold=0.6,
            cointegration_threshold=0.01,
            entry_zscore_threshold=2.5,
            exit_zscore_threshold=0.3,
            max_pairs=3,
            pair_reselection_frequency=10
        )

        assert config.lookback_period == 180
        assert config.correlation_threshold == 0.6
        assert config.cointegration_threshold == 0.01
        assert config.entry_zscore_threshold == 2.5
        assert config.exit_zscore_threshold == 0.3
        assert config.max_pairs == 3
        assert config.pair_reselection_frequency == 10

    def test_inheritance_from_base(self):
        """Test that PairsConfig inherits from BaseStrategyConfig."""
        config = PairsConfig()

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
        """Test that PairsConfig uses composition pattern for sub-configs."""
        config = PairsConfig()

        # Test that sub-configs are properly initialized
        assert config.position_limits is not None
        assert config.risk_limits is not None
        assert config.timing is not None

        # Test that sub-configs have expected properties
        assert hasattr(config.position_limits, 'max_position_size')
        assert hasattr(config.risk_limits, 'max_daily_var')
        assert hasattr(config.timing, 'health_check_interval')

    def test_serialization(self):
        """Test that PairsConfig can be serialized to dict."""
        config = PairsConfig()
        config_dict = asdict(config)

        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'strategy_type' in config_dict
        assert 'lookback_period' in config_dict
        assert 'correlation_threshold' in config_dict
        assert 'cointegration_threshold' in config_dict
        assert 'entry_zscore_threshold' in config_dict
        assert 'exit_zscore_threshold' in config_dict
        assert 'max_pairs' in config_dict
        assert 'pair_reselection_frequency' in config_dict

    def test_strategy_specific_parameters(self):
        """Test strategy-specific parameters are correctly set."""
        config = PairsConfig()

        # Test pairs trading-specific parameters
        assert config.lookback_period == 252
        assert config.correlation_threshold == 0.5
        assert config.cointegration_threshold == 0.05
        assert config.entry_zscore_threshold == 2.0
        assert config.exit_zscore_threshold == 0.5
        assert config.max_pairs == 5
        assert config.pair_reselection_frequency == 20

    def test_parameter_validation(self):
        """Test parameter validation (if implemented)."""
        config = PairsConfig()

        # Test that all parameters are within expected ranges
        assert config.lookback_period > 0
        assert 0 < config.correlation_threshold < 1
        assert 0 < config.cointegration_threshold < 1
        assert config.entry_zscore_threshold > 0
        assert config.exit_zscore_threshold > 0
        assert config.max_pairs > 0
        assert config.pair_reselection_frequency > 0

        # Entry threshold should be greater than exit threshold
        assert config.entry_zscore_threshold > config.exit_zscore_threshold

    def test_custom_name_and_id(self):
        """Test custom name and strategy_id."""
        config = PairsConfig(
            name="custom_pairs",
            strategy_id="pairs_001"
        )

        assert config.name == "custom_pairs"
        assert config.strategy_id == "pairs_001"
        assert config.strategy_type == StrategyType.PAIRS_TRADING

    def test_multi_timeframe_configuration(self):
        """Test multi-timeframe configuration."""
        config = PairsConfig(
            enable_multi_timeframe=True,
            primary_timeframe="1h",
            secondary_timeframes=["4h", "1D"]
        )

        assert config.enable_multi_timeframe is True
        assert config.primary_timeframe == "1h"
        assert config.secondary_timeframes == ["4h", "1D"]

    def test_symbol_configuration(self):
        """Test symbol configuration."""
        custom_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META"]
        config = PairsConfig(symbols=custom_symbols)

        assert config.symbols == custom_symbols
        assert len(config.symbols) == 6
        assert "AAPL" in config.symbols
        assert "MSFT" in config.symbols
        assert "GOOGL" in config.symbols
        assert "AMZN" in config.symbols
        assert "TSLA" in config.symbols
        assert "META" in config.symbols

    def test_zscore_threshold_relationship(self):
        """Test that entry zscore is greater than exit zscore."""
        config = PairsConfig()

        # Entry threshold should be greater than exit threshold
        assert config.entry_zscore_threshold > config.exit_zscore_threshold

        # Test with custom values
        custom_config = PairsConfig(
            entry_zscore_threshold=3.0,
            exit_zscore_threshold=0.5
        )
        assert custom_config.entry_zscore_threshold > custom_config.exit_zscore_threshold

    def test_correlation_threshold_range(self):
        """Test correlation threshold is within valid range."""
        config = PairsConfig()

        # Correlation threshold should be between 0 and 1
        assert 0 < config.correlation_threshold < 1

        # Test with custom values
        high_corr_config = PairsConfig(correlation_threshold=0.8)
        low_corr_config = PairsConfig(correlation_threshold=0.3)

        assert 0 < high_corr_config.correlation_threshold < 1
        assert 0 < low_corr_config.correlation_threshold < 1

    def test_cointegration_threshold_range(self):
        """Test cointegration threshold is within valid range."""
        config = PairsConfig()

        # Cointegration threshold should be between 0 and 1
        assert 0 < config.cointegration_threshold < 1

        # Test with custom values
        strict_config = PairsConfig(cointegration_threshold=0.01)
        lenient_config = PairsConfig(cointegration_threshold=0.1)

        assert 0 < strict_config.cointegration_threshold < 1
        assert 0 < lenient_config.cointegration_threshold < 1

    def test_pair_management_parameters(self):
        """Test pair management parameters."""
        config = PairsConfig(
            max_pairs=3,
            pair_reselection_frequency=15
        )

        assert config.max_pairs == 3
        assert config.pair_reselection_frequency == 15

        # Max pairs should be reasonable
        assert 1 <= config.max_pairs <= 20

    def test_parameter_combinations(self):
        """Test various parameter combinations."""
        # Conservative pairs strategy
        conservative_config = PairsConfig(
            correlation_threshold=0.7,
            cointegration_threshold=0.01,
            entry_zscore_threshold=2.5,
            exit_zscore_threshold=0.3,
            max_pairs=2
        )

        assert conservative_config.correlation_threshold == 0.7
        assert conservative_config.cointegration_threshold == 0.01
        assert conservative_config.entry_zscore_threshold == 2.5
        assert conservative_config.exit_zscore_threshold == 0.3
        assert conservative_config.max_pairs == 2

        # Aggressive pairs strategy
        aggressive_config = PairsConfig(
            correlation_threshold=0.4,
            cointegration_threshold=0.1,
            entry_zscore_threshold=1.5,
            exit_zscore_threshold=0.8,
            max_pairs=8
        )

        assert aggressive_config.correlation_threshold == 0.4
        assert aggressive_config.cointegration_threshold == 0.1
        assert aggressive_config.entry_zscore_threshold == 1.5
        assert aggressive_config.exit_zscore_threshold == 0.8
        assert aggressive_config.max_pairs == 8

    def test_lookback_period_variations(self):
        """Test different lookback period settings."""
        # Short-term pairs
        short_config = PairsConfig(lookback_period=60)
        assert short_config.lookback_period == 60

        # Medium-term pairs
        medium_config = PairsConfig(lookback_period=180)
        assert medium_config.lookback_period == 180

        # Long-term pairs (default)
        long_config = PairsConfig()
        assert long_config.lookback_period == 252
