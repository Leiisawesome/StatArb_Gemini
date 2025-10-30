"""
Unit tests for StatisticalArbitrageConfig class.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

import pytest
from dataclasses import asdict

from core_engine.config.strategies import StatisticalArbitrageConfig, StrategyType


class TestStatisticalArbitrageConfig:
    """Test suite for StatisticalArbitrageConfig class."""

    def test_initialization(self):
        """Test StatisticalArbitrageConfig initialization with defaults."""
        config = StatisticalArbitrageConfig()
        assert config.strategy_type == StrategyType.STATISTICAL_ARBITRAGE
        assert config.cointegration_lookback == 252
        assert config.entry_zscore_threshold == 2.0
        assert config.exit_zscore_threshold == 0.5
        assert config.max_holding_period == 20
        assert config.min_correlation == 0.7

    def test_custom_initialization(self):
        """Test StatisticalArbitrageConfig initialization with custom values."""
        config = StatisticalArbitrageConfig(
            cointegration_lookback=500,
            entry_zscore_threshold=2.5,
            exit_zscore_threshold=0.3,
            max_holding_period=30,
            min_correlation=0.8
        )
        assert config.cointegration_lookback == 500
        assert config.entry_zscore_threshold == 2.5
        assert config.exit_zscore_threshold == 0.3
        assert config.max_holding_period == 30
        assert config.min_correlation == 0.8

    def test_inheritance_from_base(self):
        """Test that StatisticalArbitrageConfig inherits from BaseStrategyConfig."""
        config = StatisticalArbitrageConfig()
        
        # Test inherited properties
        assert hasattr(config, 'name')
        assert hasattr(config, 'strategy_type')
        assert hasattr(config, 'position_limits')
        assert hasattr(config, 'risk_limits')
        assert hasattr(config, 'timing')
        assert hasattr(config, 'symbols')
        assert hasattr(config, 'profit_target_ratio')
        assert hasattr(config, 'execution_timeout')

    def test_serialization(self):
        """Test that StatisticalArbitrageConfig can be serialized to dict."""
        config = StatisticalArbitrageConfig()
        config_dict = asdict(config)
        
        assert isinstance(config_dict, dict)
        assert 'name' in config_dict
        assert 'strategy_type' in config_dict
        assert 'cointegration_lookback' in config_dict
        assert 'entry_zscore_threshold' in config_dict
        assert 'exit_zscore_threshold' in config_dict
        assert 'min_correlation' in config_dict

    def test_strategy_specific_parameters(self):
        """Test strategy-specific parameters are correctly set."""
        config = StatisticalArbitrageConfig()
        
        # Test cointegration parameters
        assert config.cointegration_lookback == 252
        assert config.cointegration_threshold == 0.05
        
        # Test zscore parameters
        assert config.entry_zscore_threshold == 2.0
        assert config.exit_zscore_threshold == 0.5
        
        # Test correlation parameters
        assert config.min_correlation == 0.7
        
        # Test holding period
        assert config.max_holding_period == 20

    def test_parameter_validation(self):
        """Test parameter validation."""
        config = StatisticalArbitrageConfig()
        
        # Test that all parameters are within expected ranges
        assert config.cointegration_lookback > 0
        assert config.entry_zscore_threshold > 0
        assert config.exit_zscore_threshold > 0
        assert config.max_holding_period > 0
        assert 0 < config.min_correlation < 1

    def test_custom_name_and_id(self):
        """Test custom name and strategy_id."""
        config = StatisticalArbitrageConfig(
            name="custom_stat_arb",
            strategy_id="stat_arb_001"
        )
        
        assert config.name == "custom_stat_arb"
        assert config.strategy_id == "stat_arb_001"
        assert config.strategy_type == StrategyType.STATISTICAL_ARBITRAGE

    def test_zscore_thresholds_relationship(self):
        """Test that zscore thresholds have proper relationship."""
        config = StatisticalArbitrageConfig()
        
        # Entry threshold should be higher than exit threshold
        assert config.entry_zscore_threshold > config.exit_zscore_threshold
        
        # Both should be positive
        assert config.entry_zscore_threshold > 0
        assert config.exit_zscore_threshold > 0

    def test_correlation_parameters(self):
        """Test correlation-related parameters."""
        config = StatisticalArbitrageConfig()
        
        # Min correlation should be within valid range
        assert 0 < config.min_correlation < 1
        
        # Should be a reasonable threshold for pair selection
        assert config.min_correlation >= 0.5  # At least moderate correlation
