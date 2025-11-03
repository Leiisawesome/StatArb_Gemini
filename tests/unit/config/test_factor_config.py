"""
Unit tests for FactorConfig class.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

from dataclasses import asdict

from core_engine.config.strategies import FactorConfig, StrategyType


class TestFactorConfig:
    """Test suite for FactorConfig class."""

    def test_initialization(self):
        """Test FactorConfig initialization with defaults."""
        config = FactorConfig()
        assert config.name == "strategy"  # Inherited from BaseStrategyConfig
        assert config.strategy_type == StrategyType.FACTOR
        assert config.factors == ['momentum', 'value', 'quality', 'size']
        assert config.factor_weights == {
            'momentum': 0.3, 'value': 0.3, 'quality': 0.2, 'size': 0.2
        }
        assert config.rebalance_frequency == 20
        assert config.factor_lookback == 60  # Updated from 252 to 60 (merged from local config)
        assert config.min_factor_score == 0.5

    def test_custom_initialization(self):
        """Test FactorConfig initialization with custom values."""
        custom_factors = ['momentum', 'value', 'quality']
        custom_weights = {'momentum': 0.4, 'value': 0.4, 'quality': 0.2}
        
        config = FactorConfig(
            factors=custom_factors,
            factor_weights=custom_weights,
            rebalance_frequency=10,
            factor_lookback=180,
            min_factor_score=0.6
        )
        
        assert config.factors == custom_factors
        assert config.factor_weights == custom_weights
        assert config.rebalance_frequency == 10
        assert config.factor_lookback == 180
        assert config.min_factor_score == 0.6

    def test_inheritance_from_base(self):
        """Test that FactorConfig inherits from BaseStrategyConfig."""
        config = FactorConfig()
        
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
        """Test that FactorConfig uses composition pattern for sub-configs."""
        config = FactorConfig()
        
        # Test that sub-configs are properly initialized
        assert config.position_limits is not None
        assert config.risk_limits is not None
        assert config.timing is not None
        
        # Test that sub-configs have expected properties
        assert hasattr(config.position_limits, 'max_position_size')
        assert hasattr(config.risk_limits, 'max_daily_var')
        assert hasattr(config.timing, 'health_check_interval')

    def test_serialization(self):
        """Test that FactorConfig can be serialized to dict."""
        config = FactorConfig()
        config_dict = asdict(config)
        
        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'strategy_type' in config_dict
        assert 'factors' in config_dict
        assert 'factor_weights' in config_dict
        assert 'rebalance_frequency' in config_dict
        assert 'factor_lookback' in config_dict
        assert 'min_factor_score' in config_dict

    def test_strategy_specific_parameters(self):
        """Test strategy-specific parameters are correctly set."""
        config = FactorConfig()
        
        # Test factor-specific parameters
        assert config.factors == ['momentum', 'value', 'quality', 'size']
        assert config.factor_weights == {
            'momentum': 0.3, 'value': 0.3, 'quality': 0.2, 'size': 0.2
        }
        assert config.rebalance_frequency == 20
        assert config.factor_lookback == 60  # Updated from 252 to 60 (merged from local config)
        assert config.min_factor_score == 0.5

    def test_parameter_validation(self):
        """Test parameter validation (if implemented)."""
        config = FactorConfig()
        
        # Test that all parameters are within expected ranges
        assert config.rebalance_frequency > 0
        assert config.factor_lookback > 0
        assert 0 <= config.min_factor_score <= 1
        
        # Test factor weights sum to approximately 1.0
        total_weight = sum(config.factor_weights.values())
        assert abs(total_weight - 1.0) < 0.001

    def test_custom_name_and_id(self):
        """Test custom name and strategy_id."""
        config = FactorConfig(
            name="custom_factor",
            strategy_id="factor_001"
        )
        
        assert config.name == "custom_factor"
        assert config.strategy_id == "factor_001"
        assert config.strategy_type == StrategyType.FACTOR

    def test_multi_timeframe_configuration(self):
        """Test multi-timeframe configuration."""
        config = FactorConfig(
            enable_multi_timeframe=True,
            primary_timeframe="1h",
            secondary_timeframes=["4h", "1D"]
        )
        
        assert config.enable_multi_timeframe is True
        assert config.primary_timeframe == "1h"
        assert config.secondary_timeframes == ["4h", "1D"]

    def test_symbol_configuration(self):
        """Test symbol configuration."""
        custom_symbols = ["AAPL", "GOOGL", "MSFT", "AMZN"]
        config = FactorConfig(symbols=custom_symbols)
        
        assert config.symbols == custom_symbols
        assert len(config.symbols) == 4
        assert "AAPL" in config.symbols
        assert "GOOGL" in config.symbols
        assert "MSFT" in config.symbols
        assert "AMZN" in config.symbols

    def test_factor_weights_consistency(self):
        """Test that factor weights are consistent with factors."""
        config = FactorConfig()
        
        # All factors should have weights
        for factor in config.factors:
            assert factor in config.factor_weights
        
        # All weights should correspond to factors
        for factor in config.factor_weights:
            assert factor in config.factors

    def test_custom_factor_weights(self):
        """Test custom factor weights."""
        custom_factors = ['momentum', 'value']
        custom_weights = {'momentum': 0.6, 'value': 0.4}
        
        config = FactorConfig(
            factors=custom_factors,
            factor_weights=custom_weights
        )
        
        assert config.factors == custom_factors
        assert config.factor_weights == custom_weights
        
        # Weights should sum to 1.0
        total_weight = sum(config.factor_weights.values())
        assert abs(total_weight - 1.0) < 0.001
