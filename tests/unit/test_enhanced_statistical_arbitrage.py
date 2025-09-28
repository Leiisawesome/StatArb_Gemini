"""
Unit Tests for Enhanced Statistical Arbitrage Strategy
====================================================

Tests for the EnhancedStatisticalArbitrageStrategy, focusing on:
- ISystemComponent interface compliance
- Cointegration analysis and spread trading
- Signal generation and position management
- Risk management and performance tracking
- Strategy-specific functionality

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import the strategy under test
from core_engine.trading.strategies.implementations.statistical_arbitrage.enhanced_statistical_arbitrage import (
    EnhancedStatisticalArbitrageStrategy,
    StatisticalArbitrageConfig,
    SpreadMetrics,
    SpreadState
)

from core_engine.trading.strategies.strategy_engine import (
    StrategySignal,
    SignalType,
    StrategyType,
    StrategyState
)


@pytest.fixture
def stat_arb_config():
    """Configuration for statistical arbitrage strategy"""
    return StatisticalArbitrageConfig(
        strategy_id="test_stat_arb_001",
        strategy_name="Test Statistical Arbitrage",
        strategy_type=StrategyType.STATISTICAL_ARBITRAGE,
        
        # StatArb specific config
        cointegration_lookback=100,
        min_cointegration_pvalue=0.05,
        min_correlation=0.7,
        entry_zscore_threshold=2.0,
        exit_zscore_threshold=0.5,
        stop_loss_zscore=3.5,
        max_spread_positions=3,
        position_size_method="risk_parity",
        base_position_size=0.02,
        max_holding_period=20,
        
        # Model settings
        kalman_filter_enabled=True,
        ou_process_modeling=True,
        error_correction_model=True,
        enable_monitoring=True,
        
        # Asset universe
        asset_universe=['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    )


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    np.random.seed(42)  # For reproducible tests
    
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    
    # Create correlated price series for cointegration testing
    base_trend = np.cumsum(np.random.normal(0.001, 0.02, len(dates)))
    
    data = {}
    for i, symbol in enumerate(['AAPL', 'MSFT', 'GOOGL', 'AMZN']):
        # Add some correlation between assets
        correlation_factor = 0.8 if i < 2 else 0.3  # AAPL-MSFT more correlated
        noise = np.random.normal(0, 0.01, len(dates))
        
        price_series = 100 + base_trend * correlation_factor + np.cumsum(noise)
        
        # Ensure positive prices
        price_series = np.maximum(price_series, 50)
        
        data[symbol] = pd.DataFrame({
            'open': price_series * (1 + np.random.normal(0, 0.001, len(dates))),
            'high': price_series * (1 + np.abs(np.random.normal(0, 0.005, len(dates)))),
            'low': price_series * (1 - np.abs(np.random.normal(0, 0.005, len(dates)))),
            'close': price_series,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        }, index=dates)
    
    return data


@pytest.fixture
def mock_risk_manager():
    """Mock risk manager for testing"""
    risk_manager = Mock()
    risk_manager.process_signal = AsyncMock(return_value=True)
    return risk_manager


@pytest.fixture
def stat_arb_strategy(stat_arb_config, mock_risk_manager):
    """Enhanced Statistical Arbitrage strategy instance for testing"""
    strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
    strategy.set_risk_manager(mock_risk_manager)
    return strategy


class TestEnhancedStatArbInterface:
    """Test ISystemComponent interface compliance"""
    
    def test_initialization(self, stat_arb_config):
        """Test strategy initialization"""
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        
        assert strategy.config == stat_arb_config
        assert strategy.strategy_id == "test_stat_arb_001"
        assert strategy.strategy_type == StrategyType.STATISTICAL_ARBITRAGE
        assert not strategy.is_initialized
        assert not strategy.is_operational
        assert len(strategy.cointegrated_pairs) == 0
        assert len(strategy.active_spreads) == 0
        assert len(strategy.config.asset_universe) == 4
    
    @pytest.mark.asyncio
    async def test_initialize_method(self, stat_arb_strategy):
        """Test initialize method"""
        result = await stat_arb_strategy.initialize()
        
        assert result is True
        assert stat_arb_strategy.is_initialized
        assert stat_arb_strategy.state == StrategyState.INACTIVE
        assert stat_arb_strategy.last_error is None
    
    @pytest.mark.asyncio
    async def test_start_method(self, stat_arb_strategy):
        """Test start method"""
        # Initialize first
        await stat_arb_strategy.initialize()
        
        result = await stat_arb_strategy.start()
        
        assert result is True
        assert stat_arb_strategy.is_operational
        assert stat_arb_strategy.state == StrategyState.ACTIVE
    
    @pytest.mark.asyncio
    async def test_health_check(self, stat_arb_strategy):
        """Test health check method"""
        await stat_arb_strategy.initialize()
        await stat_arb_strategy.start()
        
        health = await stat_arb_strategy.health_check()
        
        assert isinstance(health, dict)
        assert 'healthy' in health
        assert 'strategy_healthy' in health
        assert 'cointegrated_pairs' in health
        assert 'active_spreads' in health
        assert 'model_health' in health
        assert health['component_type'] == 'Strategy'
    
    def test_get_status(self, stat_arb_strategy):
        """Test get_status method"""
        status = stat_arb_strategy.get_status()
        
        assert isinstance(status, dict)
        assert 'component_type' in status
        assert 'strategy_id' in status
        assert 'config_summary' in status
        assert status['component_type'] == 'Strategy'
        assert status['strategy_id'] == 'test_stat_arb_001'


class TestConfigurationValidation:
    """Test configuration validation"""
    
    @pytest.mark.asyncio
    async def test_valid_configuration(self, stat_arb_strategy):
        """Test with valid configuration"""
        result = await stat_arb_strategy.initialize()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_invalid_zscore_thresholds(self, stat_arb_config):
        """Test with invalid Z-score thresholds"""
        # Entry threshold <= exit threshold
        stat_arb_config.entry_zscore_threshold = 1.0
        stat_arb_config.exit_zscore_threshold = 2.0
        
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        result = await strategy.initialize()
        
        assert result is False
        assert strategy.last_error is not None
    
    @pytest.mark.asyncio
    async def test_invalid_position_size(self, stat_arb_config):
        """Test with invalid position size"""
        stat_arb_config.base_position_size = 0.15  # Too large (> 10%)
        
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        result = await strategy.initialize()
        
        assert result is False
        assert strategy.last_error is not None
    
    @pytest.mark.asyncio
    async def test_insufficient_asset_universe(self, stat_arb_config):
        """Test with insufficient asset universe"""
        stat_arb_config.asset_universe = ['AAPL']  # Only one asset
        
        strategy = EnhancedStatisticalArbitrageStrategy(stat_arb_config)
        result = await strategy.initialize()
        
        assert result is False


class TestCointegrationAnalysis:
    """Test cointegration analysis functionality"""
    
    @pytest.mark.asyncio
    async def test_cointegration_test(self, stat_arb_strategy, sample_market_data):
        """Test cointegration testing between assets"""
        await stat_arb_strategy.initialize()
        await stat_arb_strategy.start()
        
        # Update market data
        stat_arb_strategy._update_market_data_cache(sample_market_data)
        
        # Test cointegration between AAPL and MSFT
        result = await stat_arb_strategy._test_cointegration('AAPL', 'MSFT')
        
        assert isinstance(result, dict)
        assert 'is_cointegrated' in result
        assert 'p_value' in result
        assert 'correlation' in result
        assert 'hedge_ratio' in result
        
        if result['is_cointegrated']:
            assert result['p_value'] < 0.05
            assert abs(result['correlation']) > 0.7
    
    @pytest.mark.asyncio
    async def test_cointegration_analysis_update(self, stat_arb_strategy, sample_market_data):
        """Test cointegration analysis update"""
        await stat_arb_strategy.initialize()
        await stat_arb_strategy.start()
        
        # Update market data
        stat_arb_strategy._update_market_data_cache(sample_market_data)
        
        # Run cointegration analysis
        await stat_arb_strategy._update_cointegration_analysis()
        
        # Should find some cointegrated pairs (given our correlated data)
        assert isinstance(stat_arb_strategy.cointegrated_pairs, dict)
        
        # Check that pairs are properly formatted
        for pair, data in stat_arb_strategy.cointegrated_pairs.items():
            assert isinstance(pair, tuple)
            assert len(pair) == 2
            assert 'hedge_ratio' in data
            assert 'correlation' in data
            assert 'p_value' in data


class TestSignalGeneration:
    """Test signal generation functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_signals_basic(self, stat_arb_strategy, sample_market_data):
        """Test basic signal generation"""
        await stat_arb_strategy.initialize()
        await stat_arb_strategy.start()
        
        signals = await stat_arb_strategy.generate_signals(sample_market_data)
        
        assert isinstance(signals, list)
        # Signals may or may not be generated depending on market conditions
        
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.strategy_id == stat_arb_strategy.strategy_id
            assert signal.symbol in stat_arb_strategy.config.asset_universe
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL]
            assert 0 <= signal.confidence <= 1
            assert signal.quantity > 0
    
    @pytest.mark.asyncio
    async def test_entry_signal_generation(self, stat_arb_strategy, sample_market_data):
        """Test entry signal generation"""
        await stat_arb_strategy.initialize()
        await stat_arb_strategy.start()
        
        # Update market data and cointegration
        stat_arb_strategy._update_market_data_cache(sample_market_data)
        await stat_arb_strategy._update_cointegration_analysis()
        
        # Generate entry signals
        entry_signals = await stat_arb_strategy._generate_entry_signals()
        
        assert isinstance(entry_signals, list)
        
        # Check signal properties
        for signal in entry_signals:
            assert 'spread_id' in signal.metadata
            assert 'pair' in signal.metadata
            assert 'hedge_ratio' in signal.metadata
            assert 'zscore' in signal.metadata
            assert 'spread_direction' in signal.metadata
            assert 'asset_role' in signal.metadata
    
    @pytest.mark.asyncio
    async def test_exit_signal_generation(self, stat_arb_strategy):
        """Test exit signal generation"""
        await stat_arb_strategy.initialize()
        await stat_arb_strategy.start()
        
        # Add a mock active spread
        spread_metrics = SpreadMetrics(
            spread_id="AAPL_MSFT",
            asset1="AAPL",
            asset2="MSFT",
            hedge_ratio=1.2,
            entry_zscore=2.5,
            current_zscore=0.3  # Below exit threshold
        )
        stat_arb_strategy.active_spreads["AAPL_MSFT"] = spread_metrics
        
        # Mock cointegrated pair
        stat_arb_strategy.cointegrated_pairs[("AAPL", "MSFT")] = {
            'hedge_ratio': 1.2,
            'spread_mean': 0.0,
            'spread_std': 1.0
        }
        
        # Mock price data for spread calculation
        stat_arb_strategy.price_data = {
            'AAPL': pd.DataFrame({'close': [150.0]}),
            'MSFT': pd.DataFrame({'close': [180.0]})
        }
        
        # Generate exit signals
        exit_signals = await stat_arb_strategy._generate_exit_signals()
        
        assert isinstance(exit_signals, list)
        
        # Should generate exit signals due to mean reversion
        if exit_signals:
            for signal in exit_signals:
                assert 'spread_id' in signal.metadata
                assert 'exit_reason' in signal.metadata
                assert 'action' in signal.metadata
                assert signal.metadata['action'] == 'exit'


class TestPositionSizing:
    """Test position sizing methods"""
    
    def test_fixed_position_sizing(self, stat_arb_strategy):
        """Test fixed position sizing"""
        signal = StrategySignal(
            strategy_id=stat_arb_strategy.strategy_id,
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.8,
            confidence=0.9,
            quantity=100.0,
            timestamp=datetime.now()
        )
        
        size = stat_arb_strategy._calculate_fixed_position_size(signal)
        
        assert size == stat_arb_strategy.config.base_position_size
    
    def test_volatility_adjusted_sizing(self, stat_arb_strategy, sample_market_data):
        """Test volatility-adjusted position sizing"""
        # Set up returns data
        stat_arb_strategy._update_market_data_cache(sample_market_data)
        
        signal = StrategySignal(
            strategy_id=stat_arb_strategy.strategy_id,
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.8,
            confidence=0.9,
            quantity=100.0,
            timestamp=datetime.now()
        )
        
        size = stat_arb_strategy._calculate_volatility_adjusted_size(signal, sample_market_data)
        
        assert isinstance(size, float)
        assert size > 0
        assert size <= stat_arb_strategy.max_position_size
    
    def test_risk_parity_sizing(self, stat_arb_strategy, sample_market_data):
        """Test risk parity position sizing"""
        # Set up returns data
        stat_arb_strategy._update_market_data_cache(sample_market_data)
        
        signal = StrategySignal(
            strategy_id=stat_arb_strategy.strategy_id,
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.8,
            confidence=0.9,
            quantity=100.0,
            timestamp=datetime.now()
        )
        
        size = stat_arb_strategy._calculate_risk_parity_size(signal, sample_market_data)
        
        assert isinstance(size, float)
        assert size > 0
        assert size <= stat_arb_strategy.max_position_size


class TestSpreadCalculations:
    """Test spread calculation methods"""
    
    def test_spread_zscore_calculation(self, stat_arb_strategy):
        """Test spread Z-score calculation"""
        # Set up mock data
        pair = ("AAPL", "MSFT")
        coint_data = {
            'hedge_ratio': 1.2,
            'spread_mean': 0.0,
            'spread_std': 5.0
        }
        
        stat_arb_strategy.price_data = {
            'AAPL': pd.DataFrame({'close': [150.0]}),
            'MSFT': pd.DataFrame({'close': [180.0]})
        }
        
        spread, zscore = stat_arb_strategy._calculate_current_spread_zscore(pair, coint_data)
        
        assert isinstance(spread, float)
        assert isinstance(zscore, float)
        
        # Verify calculation: spread = 180 - 1.2 * 150 = 0
        expected_spread = 180.0 - 1.2 * 150.0
        assert abs(spread - expected_spread) < 0.001
        
        # Verify Z-score: (0 - 0) / 5 = 0
        expected_zscore = (expected_spread - 0.0) / 5.0
        assert abs(zscore - expected_zscore) < 0.001
    
    def test_spread_zscore_with_invalid_data(self, stat_arb_strategy):
        """Test spread Z-score calculation with invalid data"""
        pair = ("INVALID1", "INVALID2")
        coint_data = {'hedge_ratio': 1.0, 'spread_mean': 0.0, 'spread_std': 1.0}
        
        spread, zscore = stat_arb_strategy._calculate_current_spread_zscore(pair, coint_data)
        
        assert spread is None
        assert zscore is None


class TestStrategySpecificMethods:
    """Test strategy-specific methods"""
    
    def test_get_spread_summary(self, stat_arb_strategy):
        """Test spread summary generation"""
        # Add some mock data
        stat_arb_strategy.cointegrated_pairs[("AAPL", "MSFT")] = {
            'correlation': 0.8,
            'hedge_ratio': 1.2
        }
        
        spread_metrics = SpreadMetrics(
            spread_id="AAPL_MSFT",
            asset1="AAPL",
            asset2="MSFT",
            hedge_ratio=1.2,
            current_zscore=1.5,
            entry_zscore=2.0
        )
        stat_arb_strategy.active_spreads["AAPL_MSFT"] = spread_metrics
        
        summary = stat_arb_strategy.get_spread_summary()
        
        assert isinstance(summary, dict)
        assert 'strategy_id' in summary
        assert 'strategy_type' in summary
        assert 'cointegrated_pairs' in summary
        assert 'active_spreads' in summary
        assert 'spread_details' in summary
        
        assert summary['cointegrated_pairs'] == 1
        assert summary['active_spreads'] == 1
        assert "AAPL_MSFT" in summary['spread_details']
    
    def test_strategy_config_summary(self, stat_arb_strategy):
        """Test strategy configuration summary"""
        config_summary = stat_arb_strategy._get_strategy_config_summary()
        
        assert isinstance(config_summary, dict)
        assert 'strategy_type' in config_summary
        assert 'asset_universe_size' in config_summary
        assert 'entry_zscore_threshold' in config_summary
        assert 'kalman_filter_enabled' in config_summary
        
        assert config_summary['strategy_type'] == 'Enhanced Statistical Arbitrage'
        assert config_summary['asset_universe_size'] == 4


class TestErrorHandling:
    """Test error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_signal_generation_error_handling(self, stat_arb_strategy):
        """Test error handling in signal generation"""
        await stat_arb_strategy.initialize()
        await stat_arb_strategy.start()
        
        # Test with invalid market data
        invalid_data = {"INVALID": "not_a_dataframe"}
        
        signals = await stat_arb_strategy.generate_signals(invalid_data)
        
        # Should handle error gracefully and return empty list
        assert isinstance(signals, list)
        assert len(signals) == 0
        assert stat_arb_strategy.performance_metrics.error_count > 0
    
    @pytest.mark.asyncio
    async def test_cointegration_test_error_handling(self, stat_arb_strategy):
        """Test error handling in cointegration testing"""
        await stat_arb_strategy.initialize()
        await stat_arb_strategy.start()
        
        # Test with insufficient data
        result = await stat_arb_strategy._test_cointegration("NONEXISTENT1", "NONEXISTENT2")
        
        assert isinstance(result, dict)
        assert result['is_cointegrated'] is False
        assert 'reason' in result


class TestStrategyIntegration:
    """Integration tests for enhanced statistical arbitrage strategy"""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, stat_arb_strategy, sample_market_data):
        """Test complete strategy lifecycle"""
        # Initialize
        assert await stat_arb_strategy.initialize() is True
        assert stat_arb_strategy.is_initialized is True
        
        # Start
        assert await stat_arb_strategy.start() is True
        assert stat_arb_strategy.is_operational is True
        
        # Generate signals
        signals = await stat_arb_strategy.generate_signals(sample_market_data)
        assert isinstance(signals, list)
        
        # Update positions
        await stat_arb_strategy.update_positions(sample_market_data)
        
        # Check health
        health = await stat_arb_strategy.health_check()
        assert health['healthy'] is True
        
        # Get status
        status = stat_arb_strategy.get_status()
        assert status['initialized'] is True
        assert status['operational'] is True
        
        # Stop
        assert await stat_arb_strategy.stop() is True
        assert stat_arb_strategy.is_operational is False
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, stat_arb_strategy, sample_market_data):
        """Test concurrent strategy operations"""
        await stat_arb_strategy.initialize()
        await stat_arb_strategy.start()
        
        # Run multiple operations concurrently
        tasks = [
            stat_arb_strategy.generate_signals(sample_market_data),
            stat_arb_strategy.update_positions(sample_market_data),
            stat_arb_strategy.health_check()
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All operations should complete successfully
        assert len(results) == 3
        assert isinstance(results[0], list)  # signals
        assert results[1] is None  # update_positions returns None
        assert isinstance(results[2], dict)  # health check


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
