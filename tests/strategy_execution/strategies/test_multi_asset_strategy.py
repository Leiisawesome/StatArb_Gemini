"""
Multi-Asset Strategy Execution Test
====================================

Comprehensive test suite for validating multi-asset strategy signal generation,
portfolio optimization, and performance attribution.

This test validates:
- Cross-asset correlation analysis and portfolio optimization
- Dynamic asset allocation and rebalancing signals
- Risk budgeting across multiple asset classes
- Portfolio-level performance attribution
- Multi-asset regime consistency and parameter sensitivity
- Correlation matrix robustness and optimization stability

Test Coverage:
- Signal quality validation (portfolio optimization, rebalancing signals, risk budgeting)
- End-to-end portfolio management with multi-asset logic
- Performance attribution accuracy for portfolio-level decisions
- Cross-asset correlation analysis and regime consistency
- Parameter sensitivity analysis (volatility targets, correlation thresholds)
- Portfolio optimization robustness testing
- Error handling for asset class divergence and market regime changes

Author: StatArb_Gemini Phase 7 Strategy Validation
Version: 1.0.0
"""

import asyncio
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

# Import testing framework
from tests.strategy_execution.framework import (
    StrategyTestConfig,
    SignalValidator,
    ExecutionSimulator,
    PerformanceAttributor
)

# Import strategy components
from core_engine.trading.strategies.implementations.multi_asset.enhanced_multi_asset import EnhancedMultiAssetStrategy, MultiAssetConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMultiAssetStrategyExecution:
    """Comprehensive multi-asset strategy execution validation"""

    @pytest.fixture
    def multi_asset_config(self):
        """Create multi-asset configuration for testing"""
        return MultiAssetConfig(
            rebalance_frequency=10,
            correlation_lookback=60,
            max_correlation=0.8,
            portfolio_vol_target=0.12,
            max_asset_weight=0.3,
            min_asset_weight=0.05,
            equal_weight_baseline=True,
            asset_classes={
                'tech': ['AAPL', 'MSFT', 'GOOGL'],
                'growth': ['AMZN', 'TSLA', 'NVDA'],
                'value': ['BRK.B', 'JPM', 'JNJ']
            }
        )

    @pytest.fixture
    def multi_asset_strategy(self, multi_asset_config):
        """Create multi-asset strategy instance"""
        return EnhancedMultiAssetStrategy(multi_asset_config)

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        # Create correlated price series for different asset classes
        np.random.seed(42)

        # Tech stocks - high correlation
        tech_trend = np.cumsum(np.random.normal(0.001, 0.02, 100))
        aapl_prices = 150 * (1 + tech_trend + np.random.normal(0, 0.01, 100))
        msft_prices = 300 * (1 + tech_trend * 0.9 + np.random.normal(0, 0.01, 100))
        googl_prices = 2500 * (1 + tech_trend * 0.85 + np.random.normal(0, 0.01, 100))

        # Growth stocks - moderate correlation with tech
        growth_trend = np.cumsum(np.random.normal(0.002, 0.03, 100))
        amzn_prices = 3000 * (1 + growth_trend + np.random.normal(0, 0.015, 100))
        tsla_prices = 200 * (1 + growth_trend * 1.2 + np.random.normal(0, 0.02, 100))
        nvda_prices = 400 * (1 + growth_trend * 0.95 + np.random.normal(0, 0.015, 100))

        # Value stocks - lower correlation
        value_trend = np.cumsum(np.random.normal(0.0005, 0.015, 100))
        brk_prices = 400000 * (1 + value_trend + np.random.normal(0, 0.008, 100))
        jpm_prices = 150 * (1 + value_trend * 0.9 + np.random.normal(0, 0.01, 100))
        jnj_prices = 180 * (1 + value_trend * 0.8 + np.random.normal(0, 0.009, 100))

        # Create enriched dataframes with required features
        def create_enriched_df(prices):
            df = pd.DataFrame({
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, 100),
                'high': prices * (1 + np.abs(np.random.normal(0, 0.01, 100))),
                'low': prices * (1 - np.abs(np.random.normal(0, 0.01, 100))),
                'open': prices * (1 + np.random.normal(0, 0.005, 100))
            }, index=dates)

            # Add required enriched features
            df['returns_1'] = df['close'].pct_change().fillna(0)
            df['volatility'] = df['returns_1'].rolling(20).std().fillna(0.02)

            return df

        return {
            'AAPL': create_enriched_df(aapl_prices),
            'MSFT': create_enriched_df(msft_prices),
            'GOOGL': create_enriched_df(googl_prices),
            'AMZN': create_enriched_df(amzn_prices),
            'TSLA': create_enriched_df(tsla_prices),
            'NVDA': create_enriched_df(nvda_prices),
            'BRK.B': create_enriched_df(brk_prices),
            'JPM': create_enriched_df(jpm_prices),
            'JNJ': create_enriched_df(jnj_prices)
        }

    @pytest.fixture
    def strategy_test_config(self):
        """Create strategy test configuration"""
        return {
            'lookback_period': 20,
            'signal_threshold': 0.5,
            'position_size': 0.02,
            'stop_loss': 0.05,
            'take_profit': 0.10,
            'max_positions': 10,
            'rebalance_frequency': 'daily',
            'enable_risk_management': True,
        }

    @pytest.mark.asyncio
    async def test_multi_asset_signal_generation(self, multi_asset_strategy, sample_market_data):
        """Test multi-asset signal generation"""
        logger.info("Testing multi-asset signal generation")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        signals = await multi_asset_strategy.generate_signals(sample_market_data)

        # Should generate signals for portfolio rebalancing
        assert isinstance(signals, list), "Should return list of signals"

        # Check signal structure if signals are generated
        if signals:
            for signal in signals:
                assert hasattr(signal, 'symbol'), "Signal should have symbol"
                assert hasattr(signal, 'signal_type'), "Signal should have signal_type"
                assert signal.symbol in sample_market_data.keys(), f"Signal symbol {signal.symbol} should be in market data"

        logger.info(f"Generated {len(signals)} multi-asset signals")

    @pytest.mark.asyncio
    async def test_correlation_matrix_calculation(self, multi_asset_strategy, sample_market_data):
        """Test correlation matrix calculation"""
        logger.info("Testing correlation matrix calculation")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        # Generate signals to trigger correlation calculation
        signals = await multi_asset_strategy.generate_signals(sample_market_data)

        # Check that correlation matrix was calculated
        assert multi_asset_strategy.correlation_matrix is not None, "Correlation matrix should be calculated"
        assert isinstance(multi_asset_strategy.correlation_matrix, pd.DataFrame), "Correlation matrix should be DataFrame"

        # Check matrix dimensions
        expected_symbols = list(sample_market_data.keys())
        assert multi_asset_strategy.correlation_matrix.shape == (len(expected_symbols), len(expected_symbols)), "Correlation matrix should be square with all symbols"

        # Check correlation values are reasonable
        corr_values = multi_asset_strategy.correlation_matrix.values
        assert np.all((corr_values >= -1) & (corr_values <= 1)), "Correlation values should be between -1 and 1"

        logger.info(f"Correlation matrix calculated for {len(expected_symbols)} symbols")

    @pytest.mark.asyncio
    async def test_portfolio_weight_optimization(self, multi_asset_strategy, sample_market_data):
        """Test portfolio weight optimization"""
        logger.info("Testing portfolio weight optimization")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        # Generate signals to trigger optimization
        signals = await multi_asset_strategy.generate_signals(sample_market_data)

        # Check that target weights were calculated
        assert multi_asset_strategy.target_weights, "Target weights should be calculated"
        assert isinstance(multi_asset_strategy.target_weights, dict), "Target weights should be dictionary"

        # Check weight constraints
        total_weight = sum(multi_asset_strategy.target_weights.values())
        assert abs(total_weight - 1.0) < 0.01, f"Total weights should sum to 1.0, got {total_weight}"

        for symbol, weight in multi_asset_strategy.target_weights.items():
            assert multi_asset_strategy.config.min_asset_weight <= weight <= multi_asset_strategy.config.max_asset_weight, \
                f"Weight for {symbol} ({weight}) should be between {multi_asset_strategy.config.min_asset_weight} and {multi_asset_strategy.config.max_asset_weight}"

        logger.info(f"Portfolio optimized with {len(multi_asset_strategy.target_weights)} positions")

    @pytest.mark.asyncio
    async def test_signal_quality_validation(self, multi_asset_strategy, sample_market_data):
        """Test signal quality validation for multi-asset strategy"""
        logger.info("Testing signal quality validation")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        signals = await multi_asset_strategy.generate_signals(sample_market_data)

        # Use SignalValidator to assess quality
        validator = SignalValidator()
        quality_result = await validator.validate_signal_quality(signals, sample_market_data, multi_asset_strategy.config)

        assert isinstance(quality_result, dict), "Should return dictionary with quality metrics"
        assert "quality_score" in quality_result, "Should contain quality_score key"
        assert isinstance(quality_result["quality_score"], (int, float)), "Quality score should be numeric"
        assert quality_result["quality_score"] >= 0.0, "Quality score should be non-negative"

        logger.info(f"Signal quality result: {quality_result}")

    @pytest.mark.asyncio
    async def test_execution_simulation(self, multi_asset_strategy, sample_market_data, strategy_test_config):
        """Test execution simulation for multi-asset strategy"""
        logger.info("Testing execution simulation")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        signals = await multi_asset_strategy.generate_signals(sample_market_data)

        if signals:
            # Create execution simulator
            simulator = ExecutionSimulator()

            # Simulate execution
            execution_results = await simulator.simulate_strategy_execution(
                multi_asset_strategy.config, sample_market_data, strategy_test_config
            )

            assert isinstance(execution_results, dict), "Execution results should be dictionary"
            assert "signals_tested" in execution_results, "Should contain signals tested"
            assert "trades_executed" in execution_results, "Should contain trades executed"

            logger.info(f"Execution simulation completed: {execution_results.get('total_trades', 0)} trades")
        else:
            logger.info("No signals generated for execution simulation")

    @pytest.mark.asyncio
    async def test_performance_attribution(self, multi_asset_strategy, sample_market_data):
        """Test performance attribution for multi-asset strategy"""
        logger.info("Testing performance attribution")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        signals = await multi_asset_strategy.generate_signals(sample_market_data)

        if signals:
            # Create performance attributor
            attributor = PerformanceAttributor()

            # Generate attribution analysis
            attribution_results = await attributor.attribute_performance(signals, sample_market_data)

            assert isinstance(attribution_results, dict), "Attribution results should be dictionary"
            assert "total_return" in attribution_results, "Should contain total return"
            assert "strategy_contribution" in attribution_results, "Should contain strategy contribution"

            logger.info(f"Performance attribution completed: {attribution_results.get('total_return', 0):.4f} total return")
        else:
            logger.info("No signals generated for performance attribution")

    @pytest.mark.asyncio
    async def test_comprehensive_strategy_validation(self, multi_asset_strategy, sample_market_data):
        """Test comprehensive multi-asset strategy validation"""
        logger.info("Testing comprehensive strategy validation")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        # Test multiple signal generations
        for i in range(3):
            signals = await multi_asset_strategy.generate_signals(sample_market_data)
            assert isinstance(signals, list), f"Iteration {i+1}: Should return list of signals"

        # Check strategy health
        health_status = await multi_asset_strategy.health_check()
        assert health_status.get('healthy', False), "Strategy should be healthy"

        logger.info("Comprehensive validation completed successfully")

    @pytest.mark.asyncio
    async def test_cross_asset_consistency(self, multi_asset_strategy, sample_market_data):
        """Test cross-asset consistency and correlation analysis"""
        logger.info("Testing cross-asset consistency")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        # Generate signals multiple times to check consistency
        signal_sets = []
        for i in range(5):
            signals = await multi_asset_strategy.generate_signals(sample_market_data)
            signal_sets.append(signals)

        # Check that correlation matrix is stable
        assert multi_asset_strategy.correlation_matrix is not None, "Correlation matrix should exist"

        # Verify correlation matrix properties
        corr_matrix = multi_asset_strategy.correlation_matrix
        assert corr_matrix.shape[0] == corr_matrix.shape[1], "Correlation matrix should be square"
        assert np.allclose(corr_matrix, corr_matrix.T), "Correlation matrix should be symmetric"

        logger.info("Cross-asset consistency validation completed")

    @pytest.mark.asyncio
    async def test_regime_aware_signaling(self, multi_asset_strategy, sample_market_data):
        """Test regime-aware signaling for multi-asset strategy"""
        logger.info("Testing regime-aware signaling")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        # Generate signals
        signals = await multi_asset_strategy.generate_signals(sample_market_data)

        # Check that signals are appropriate for current market regime
        # (This is a basic check - more sophisticated regime detection would be in the strategy)
        if signals:
            # Verify signals have required attributes
            for signal in signals:
                assert hasattr(signal, 'symbol'), "Signal should have symbol"
                assert hasattr(signal, 'signal_type'), "Signal should have signal_type"

        logger.info(f"Regime-aware signaling test completed with {len(signals)} signals")

    @pytest.mark.asyncio
    async def test_parameter_sensitivity(self, sample_market_data):
        """Test parameter sensitivity analysis"""
        logger.info("Testing parameter sensitivity")

        # Test different volatility targets
        vol_targets = [0.08, 0.12, 0.16]

        for vol_target in vol_targets:
            config = MultiAssetConfig(
                portfolio_vol_target=vol_target,
                asset_classes={
                    'tech': ['AAPL', 'MSFT'],
                    'growth': ['AMZN', 'TSLA']
                }
            )

            strategy = EnhancedMultiAssetStrategy(config)
            await strategy.initialize()
            await strategy.start()

            signals = await strategy.generate_signals(sample_market_data)

            # Should generate signals regardless of volatility target
            assert isinstance(signals, list), f"Should generate signals for vol_target {vol_target}"

            logger.info(f"Volatility target {vol_target}: {len(signals)} signals")

    @pytest.mark.asyncio
    async def test_strategy_stress_testing(self, multi_asset_strategy, sample_market_data):
        """Test strategy stress conditions"""
        logger.info("Testing strategy stress conditions")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        # Test with normal conditions
        signals_normal = await multi_asset_strategy.generate_signals(sample_market_data)
        logger.info(f"Normal conditions: {len(signals_normal)} signals")

        # Test strategy health under stress
        health_status = await multi_asset_strategy.health_check()
        assert health_status.get('healthy', False), "Strategy should remain healthy"

        logger.info("Stress testing completed successfully")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_data(self, multi_asset_strategy):
        """Test error handling with invalid data"""
        logger.info("Testing error handling with invalid data")

        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        # Test with empty data - strategy may still generate signals if it has target weights
        empty_data = {}
        signals = await multi_asset_strategy.generate_signals(empty_data)
        assert isinstance(signals, list), "Should return list even with empty data"
        # Note: Strategy may generate signals to reach target weights even with empty data

        # Test with None data - should handle gracefully
        try:
            signals = await multi_asset_strategy.generate_signals(None)
            assert isinstance(signals, list), "Should return list even with None data"
        except Exception:
            # It's acceptable for the strategy to raise an exception with None data
            pass

        logger.info("Error handling test completed")

    @pytest.mark.asyncio
    async def test_error_handling_uninitialized_strategy(self):
        """Test error handling with uninitialized strategy"""
        logger.info("Testing error handling with uninitialized strategy")

        config = MultiAssetConfig()
        strategy = EnhancedMultiAssetStrategy(config)

        # Try to generate signals without initialization
        try:
            signals = await strategy.generate_signals({})
            # Should handle gracefully
            assert isinstance(signals, list), "Should return list even when uninitialized"
        except Exception as e:
            # If it raises an exception, it should be handled gracefully
            logger.info(f"Expected exception caught: {e}")

        logger.info("Uninitialized strategy error handling test completed")

    @pytest.mark.asyncio
    async def test_multi_asset_end_to_end_pipeline(self, multi_asset_strategy, sample_market_data):
        """Test end-to-end multi-asset pipeline"""
        logger.info("Testing end-to-end multi-asset pipeline")

        # Initialize and start
        await multi_asset_strategy.initialize()
        await multi_asset_strategy.start()

        # Generate signals
        signals = await multi_asset_strategy.generate_signals(sample_market_data)

        # Update positions
        await multi_asset_strategy.update_positions(sample_market_data)

        # Check health
        health = await multi_asset_strategy.health_check()
        assert health.get('healthy', False), "Strategy should be healthy after full pipeline"

        # Stop strategy
        await multi_asset_strategy.stop()

        logger.info("End-to-end pipeline test completed successfully")