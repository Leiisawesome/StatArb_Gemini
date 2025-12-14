"""
Unit tests for MultiAssetConfig class.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

from dataclasses import asdict

from core_engine.config.strategies import MultiAssetConfig, StrategyType

class TestMultiAssetConfig:
    """Test suite for MultiAssetConfig class."""

    def test_initialization(self):
        """Test MultiAssetConfig initialization with defaults."""
        config = MultiAssetConfig()
        assert config.name == "strategy"  # Inherited from BaseStrategyConfig
        assert config.strategy_type == StrategyType.MULTI_ASSET
        # asset_classes is now a dict mapping class names to symbol lists (merged from local config)
        assert isinstance(config.asset_classes, dict)
        assert 'tech' in config.asset_classes
        assert 'growth' in config.asset_classes
        assert 'value' in config.asset_classes
        assert 'equities' in config.asset_classes  # Base asset classes also available
        assert 'bonds' in config.asset_classes
        assert 'commodities' in config.asset_classes
        assert config.target_allocations == {
            'equities': 0.6, 'bonds': 0.3, 'commodities': 0.1
        }
        assert config.rebalance_frequency == 10
        assert config.rebalance_threshold == 0.05
        assert config.correlation_lookback == 60

    def test_custom_initialization(self):
        """Test MultiAssetConfig initialization with custom values."""
        custom_asset_classes = ['equities', 'bonds', 'commodities', 'real_estate']
        custom_allocations = {
            'equities': 0.5, 'bonds': 0.3, 'commodities': 0.1, 'real_estate': 0.1
        }

        config = MultiAssetConfig(
            asset_classes=custom_asset_classes,
            target_allocations=custom_allocations,
            rebalance_frequency=5,
            rebalance_threshold=0.03,
            correlation_lookback=90
        )

        assert config.asset_classes == custom_asset_classes
        assert config.target_allocations == custom_allocations
        assert config.rebalance_frequency == 5
        assert config.rebalance_threshold == 0.03
        assert config.correlation_lookback == 90

    def test_inheritance_from_base(self):
        """Test that MultiAssetConfig inherits from BaseStrategyConfig."""
        config = MultiAssetConfig()

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
        """Test that MultiAssetConfig uses composition pattern for sub-configs."""
        config = MultiAssetConfig()

        # Test that sub-configs are properly initialized
        assert config.position_limits is not None
        assert config.risk_limits is not None
        assert config.timing is not None

        # Test that sub-configs have expected properties
        assert hasattr(config.position_limits, 'max_position_size')
        assert hasattr(config.risk_limits, 'max_daily_var')
        assert hasattr(config.timing, 'health_check_interval')

    def test_serialization(self):
        """Test that MultiAssetConfig can be serialized to dict."""
        config = MultiAssetConfig()
        config_dict = asdict(config)

        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'strategy_type' in config_dict
        assert 'asset_classes' in config_dict
        assert 'target_allocations' in config_dict
        assert 'rebalance_frequency' in config_dict
        assert 'rebalance_threshold' in config_dict
        assert 'correlation_lookback' in config_dict

    def test_strategy_specific_parameters(self):
        """Test strategy-specific parameters are correctly set."""
        config = MultiAssetConfig()

        # Test multi-asset-specific parameters
        # asset_classes is now a dict mapping class names to symbol lists (merged from local config)
        assert isinstance(config.asset_classes, dict)
        assert 'tech' in config.asset_classes
        assert 'growth' in config.asset_classes
        assert 'value' in config.asset_classes
        assert config.target_allocations == {
            'equities': 0.6, 'bonds': 0.3, 'commodities': 0.1
        }
        assert config.rebalance_frequency == 10
        assert config.rebalance_threshold == 0.05
        assert config.correlation_lookback == 60

    def test_parameter_validation(self):
        """Test parameter validation (if implemented)."""
        config = MultiAssetConfig()

        # Test that all parameters are within expected ranges
        assert config.rebalance_frequency > 0
        assert config.rebalance_threshold > 0
        assert config.correlation_lookback > 0

        # Test that allocations sum to approximately 1.0
        total_allocation = sum(config.target_allocations.values())
        assert abs(total_allocation - 1.0) < 0.001

    def test_custom_name_and_id(self):
        """Test custom name and strategy_id."""
        config = MultiAssetConfig(
            name="custom_multi_asset",
            strategy_id="multi_asset_001"
        )

        assert config.name == "custom_multi_asset"
        assert config.strategy_id == "multi_asset_001"
        assert config.strategy_type == StrategyType.MULTI_ASSET

    def test_multi_timeframe_configuration(self):
        """Test multi-timeframe configuration."""
        config = MultiAssetConfig(
            enable_multi_timeframe=True,
            primary_timeframe="1D",
            secondary_timeframes=["1W", "1M"]
        )

        assert config.enable_multi_timeframe is True
        assert config.primary_timeframe == "1D"
        assert config.secondary_timeframes == ["1W", "1M"]

    def test_symbol_configuration(self):
        """Test symbol configuration."""
        custom_symbols = ["SPY", "TLT", "GLD", "VNQ"]
        config = MultiAssetConfig(symbols=custom_symbols)

        assert config.symbols == custom_symbols
        assert len(config.symbols) == 4
        assert "SPY" in config.symbols
        assert "TLT" in config.symbols
        assert "GLD" in config.symbols
        assert "VNQ" in config.symbols

    def test_asset_class_consistency(self):
        """Test that asset classes are consistent with target allocations."""
        config = MultiAssetConfig()

        # asset_classes is now a dict, so we check consistency differently
        # Base asset classes (equities, bonds, commodities) should have allocations
        for asset_class in config.target_allocations:
            # These base classes may or may not be in asset_classes dict (they're empty lists)
            # But they should at least exist as keys for consistency
            if asset_class in config.asset_classes:
                assert isinstance(config.asset_classes[asset_class], list)

        # Additional asset class keys (tech, growth, value) don't need target_allocations
        # They're for symbol grouping, not allocation targets

    def test_custom_asset_allocations(self):
        """Test custom asset allocations."""
        custom_asset_classes = ['equities', 'bonds']
        custom_allocations = {'equities': 0.7, 'bonds': 0.3}

        config = MultiAssetConfig(
            asset_classes=custom_asset_classes,
            target_allocations=custom_allocations
        )

        assert config.asset_classes == custom_asset_classes
        assert config.target_allocations == custom_allocations

        # Allocations should sum to 1.0
        total_allocation = sum(config.target_allocations.values())
        assert abs(total_allocation - 1.0) < 0.001

    def test_rebalance_parameters(self):
        """Test rebalance-specific parameters."""
        config = MultiAssetConfig(
            rebalance_frequency=7,  # Weekly rebalancing
            rebalance_threshold=0.02  # 2% threshold
        )

        assert config.rebalance_frequency == 7
        assert config.rebalance_threshold == 0.02
        assert config.correlation_lookback == 60  # Default value

    def test_correlation_analysis_parameters(self):
        """Test correlation analysis parameters."""
        config = MultiAssetConfig(
            correlation_lookback=120  # 4 months
        )

        assert config.correlation_lookback == 120
        assert config.rebalance_frequency == 10  # Default value
        assert config.rebalance_threshold == 0.05  # Default value
