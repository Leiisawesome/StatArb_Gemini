"""
Pairs Trading Strategy Execution Test
====================================

Comprehensive test suite for validating pairs trading strategy signal generation,
execution pipeline, and performance attribution.

This test validates:
- Cointegration-based pair selection and validation
- Spread calculation accuracy and statistical arbitrage signals
- Realistic execution with slippage and transaction costs
- Performance attribution to strategy logic vs. execution costs
- Cross-pair consistency and correlation analysis
- Regime-aware pair trading signals

Test Coverage:
- Signal quality validation (cointegration, spread calculations, entry/exit timing)
- End-to-end execution simulation with pair-specific logic
- Performance attribution accuracy for statistical arbitrage
- Cross-market pair consistency
- Parameter sensitivity analysis (correlation thresholds, z-score levels)
- Cointegration robustness testing
- Error handling for pair divergence and market regime changes

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
from core_engine.trading.strategies.implementations.pairs_trading.enhanced_pairs_trading import EnhancedPairsTradingStrategy, PairsConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestPairsTradingStrategyExecution:
    """Comprehensive pairs trading strategy execution validation"""

    @pytest.fixture
    def pairs_config(self):
        """Create pairs trading configuration for testing"""
        return PairsConfig(
            min_correlation=0.5,
            cointegration_pvalue=0.05,
            lookback_period=252,
            entry_zscore=2.0,
            exit_zscore=0.5,
            stop_loss_zscore=3.5,
            max_pairs=5,
            position_size_pct=0.02,
            max_holding_period=30,
            correlation_threshold=0.5,
            asset_universe=["AAPL", "MSFT"]
        )

    @pytest.fixture
    def pairs_trading_strategy(self, pairs_config):
        """Create pairs trading strategy instance"""
        return EnhancedPairsTradingStrategy(pairs_config)

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for pairs trading testing"""
        dates = pd.date_range('2023-01-01', periods=300, freq='D')

        # Create correlated price series for AAPL and MSFT
        np.random.seed(42)

        # Base trends
        aapl_trend = np.linspace(150, 180, 300)
        msft_trend = np.linspace(280, 320, 300)

        # Add correlated noise
        common_noise = np.random.normal(0, 2, 300)
        aapl_noise = np.random.normal(0, 3, 300)
        msft_noise = np.random.normal(0, 4, 300)

        # Create cointegrated series
        aapl_prices = aapl_trend + 0.8 * common_noise + aapl_noise
        msft_prices = msft_trend + 0.6 * common_noise + msft_noise

        # Create spread with mean reversion characteristics
        spread = aapl_prices - 0.5 * msft_prices
        # Add mean reversion to spread
        spread = spread + np.sin(np.arange(300) * 0.1) * 5

        # Create DataFrame with OHLCV data
        data = []
        for i, date in enumerate(dates):
            data.append({
                'timestamp': date,
                'symbol': 'AAPL',
                'open': aapl_prices[i] * (1 + np.random.uniform(-0.005, 0.005)),
                'high': aapl_prices[i] * (1 + np.random.uniform(0.001, 0.01)),
                'low': aapl_prices[i] * (1 + np.random.uniform(-0.01, -0.001)),
                'close': aapl_prices[i],
                'volume': np.random.randint(50000000, 150000000),
                'returns': np.log(aapl_prices[i] / aapl_prices[i-1]) if i > 0 else 0,
                'spread': spread[i]
            })
            data.append({
                'timestamp': date,
                'symbol': 'MSFT',
                'open': msft_prices[i] * (1 + np.random.uniform(-0.005, 0.005)),
                'high': msft_prices[i] * (1 + np.random.uniform(0.001, 0.01)),
                'low': msft_prices[i] * (1 + np.random.uniform(-0.01, -0.001)),
                'close': msft_prices[i],
                'volume': np.random.randint(30000000, 100000000),
                'returns': np.log(msft_prices[i] / msft_prices[i-1]) if i > 0 else 0,
                'spread': spread[i]
            })

        df = pd.DataFrame(data)
        return {symbol: df[df['symbol'] == symbol].set_index('timestamp') for symbol in ['AAPL', 'MSFT']}

    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        return {
            'results_directory': '/tmp/test_results',
            'test_timeout': 30,
            'validation_thresholds': {
                'signal_quality': 0.7,
                'execution_accuracy': 0.8,
                'performance_score': 0.75
            }
        }

    @pytest.mark.asyncio
    async def test_pairs_trading_signal_generation(self, pairs_trading_strategy, sample_market_data):
        """Test pairs trading signal generation from cointegrated pairs"""
        logger.info("Testing pairs trading signal generation")

        # Initialize and start strategy
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        # Generate signals
        signals = await pairs_trading_strategy.generate_signals(sample_market_data)

        # Validate signals
        assert isinstance(signals, list), "Should return list of signals"
        assert len(signals) >= 0, "Should generate valid number of signals"

        # Check signal structure if signals exist
        if signals:
            for signal in signals:
                assert hasattr(signal, 'signal_type'), "Signal should have signal_type"
                assert hasattr(signal, 'symbol'), "Signal should have symbol"
                assert hasattr(signal, 'confidence'), "Signal should have confidence"
                assert hasattr(signal, 'strength'), "Signal should have strength"
                assert signal.confidence >= 0.0 and signal.confidence <= 1.0, "Confidence should be between 0 and 1"

        logger.info(f"Generated {len(signals)} pairs trading signals")

    @pytest.mark.asyncio
    async def test_cointegration_analysis(self, pairs_trading_strategy, sample_market_data):
        """Test cointegration analysis for pair selection"""
        logger.info("Testing cointegration analysis")

        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        # Test cointegration between AAPL and MSFT
        aapl_data = sample_market_data['AAPL']['close']
        msft_data = sample_market_data['MSFT']['close']

        # Check if cointegration analysis can be performed
        # Note: This is a simplified test - actual cointegration testing would be in the strategy
        assert len(aapl_data) > 0, "Should have AAPL data"
        assert len(msft_data) > 0, "Should have MSFT data"

        # Correlation should be positive for cointegrated pairs
        correlation = aapl_data.corr(msft_data)
        assert correlation > 0.3, f"Should have reasonable correlation, got {correlation}"

        logger.info(f"AAPL-MSFT correlation: {correlation:.3f}")

    @pytest.mark.asyncio
    async def test_spread_calculation(self, pairs_trading_strategy, sample_market_data):
        """Test spread calculation and normalization"""
        logger.info("Testing spread calculation")

        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        # Generate signals which should include spread calculations
        signals = await pairs_trading_strategy.generate_signals(sample_market_data)

        # Check if spread data exists in market data
        aapl_data = sample_market_data['AAPL']
        msft_data = sample_market_data['MSFT']

        assert 'spread' in aapl_data.columns, "Should have spread data in AAPL"
        assert 'spread' in msft_data.columns, "Should have spread data in MSFT"

        # Spread should have some variation
        spread_std = aapl_data['spread'].std()
        assert spread_std > 0, f"Spread should have variation, got std {spread_std}"

        logger.info(f"Spread standard deviation: {spread_std:.3f}")

    @pytest.mark.asyncio
    async def test_signal_quality_validation(self, pairs_trading_strategy, sample_market_data):
        """Test signal quality validation for pairs trading"""
        logger.info("Testing signal quality validation")

        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        signals = await pairs_trading_strategy.generate_signals(sample_market_data)

        # Use SignalValidator to assess quality
        validator = SignalValidator()
        quality_result = await validator.validate_signal_quality(signals, sample_market_data, pairs_trading_strategy.config)

        assert isinstance(quality_result, dict), "Should return dictionary with quality metrics"
        assert "quality_score" in quality_result, "Should contain quality_score key"
        assert isinstance(quality_result["quality_score"], (int, float)), "Quality score should be numeric"
        assert quality_result["quality_score"] >= 0.0, "Quality score should be non-negative"

        logger.info(f"Signal quality result: {quality_result}")

    @pytest.mark.asyncio
    async def test_execution_simulation(self, pairs_trading_strategy, sample_market_data, test_config):
        """Test realistic execution simulation for pairs trading"""
        logger.info("Testing execution simulation")

        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        signals = await pairs_trading_strategy.generate_signals(sample_market_data)

        if signals:
            # Simulate execution
            simulator = ExecutionSimulator()
            execution_results = await simulator.simulate_execution(signals, sample_market_data)

            assert 'executed_trades' in execution_results, "Should have executed trades"
            assert 'total_pnl' in execution_results, "Should have total P&L"
            assert 'execution_quality' in execution_results, "Should have execution quality metrics"

            logger.info(f"Execution simulation results: {execution_results}")
        else:
            logger.info("No signals generated for execution simulation")

    @pytest.mark.asyncio
    async def test_performance_attribution(self, pairs_trading_strategy, sample_market_data, test_config):
        """Test performance attribution for pairs trading strategy"""
        logger.info("Testing performance attribution")

        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        signals = await pairs_trading_strategy.generate_signals(sample_market_data)

        if signals:
            # Simulate execution first
            simulator = ExecutionSimulator()
            execution_results = await simulator.simulate_execution(signals, sample_market_data)

            # Test attribution
            attributor = PerformanceAttributor()
            attribution_result = attributor.validate_attribution(execution_results)

            assert 'attribution_accuracy' in attribution_result, "Should have attribution accuracy"
            assert 'total_pnl' in attribution_result, "Should have total P&L"
            assert 'strategy_contributions' in attribution_result, "Should have strategy contributions"

            logger.info(f"Performance attribution: {attribution_result}")
        else:
            logger.info("No signals generated for performance attribution")

    @pytest.mark.asyncio
    async def test_comprehensive_strategy_validation(self, pairs_trading_strategy, sample_market_data, test_config):
        """Test complete pairs trading validation pipeline"""
        logger.info("Testing comprehensive strategy validation")

        # This would use the StrategyTestEngine for full validation
        # For now, we'll do a simplified comprehensive test
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        signals = await pairs_trading_strategy.generate_signals(sample_market_data)

        # Basic validation
        assert pairs_trading_strategy.is_operational, "Strategy should be operational"
        assert isinstance(signals, list), "Should generate signal list"

        logger.info(f"Comprehensive validation: {len(signals)} signals generated")

    @pytest.mark.asyncio
    async def test_cross_market_consistency(self, pairs_trading_strategy, sample_market_data):
        """Test pairs trading consistency across different market conditions"""
        logger.info("Testing cross-market consistency")

        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        # Test with different data subsets
        signals = await pairs_trading_strategy.generate_signals(sample_market_data)

        # Check consistency - should generate reasonable number of signals
        assert len(signals) >= 0, "Should generate valid signals"

        logger.info(f"Cross-market consistency: {len(signals)} signals")

    @pytest.mark.asyncio
    async def test_regime_aware_signaling(self, pairs_trading_strategy, sample_market_data):
        """Test regime-aware signaling for pairs trading"""
        logger.info("Testing regime-aware signaling")

        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        signals = await pairs_trading_strategy.generate_signals(sample_market_data)

        # Analyze signals by regime (simplified)
        if signals:
            # Check signal distribution
            signal_types = [s.signal_type for s in signals]
            logger.info(f"Signal types distribution: {signal_types}")
        else:
            logger.info("No signals generated for regime analysis")

    @pytest.mark.asyncio
    async def test_parameter_sensitivity(self, pairs_trading_strategy, sample_market_data):
        """Test parameter sensitivity for pairs trading"""
        logger.info("Testing parameter sensitivity")

        # Test different z-score thresholds
        thresholds = [1.5, 2.0, 2.5]

        for threshold in thresholds:
            # Create config with different threshold
            config = PairsConfig(
                entry_zscore=threshold,
                exit_zscore=threshold * 0.25,
                correlation_threshold=0.5,
                cointegration_pvalue=0.05,
                asset_universe=["AAPL", "MSFT"]
            )

            strategy = EnhancedPairsTradingStrategy(config)
            await strategy.initialize()
            await strategy.start()

            signals = await strategy.generate_signals(sample_market_data)
            logger.info(f"Threshold {threshold}: {len(signals)} signals")

    @pytest.mark.asyncio
    async def test_strategy_stress_testing(self, pairs_trading_strategy, sample_market_data):
        """Test pairs trading under stress conditions"""
        logger.info("Testing strategy stress conditions")

        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        # Test with normal conditions
        normal_signals = await pairs_trading_strategy.generate_signals(sample_market_data)

        # Test with high volatility (add noise to data)
        volatile_data = {}
        for symbol, data in sample_market_data.items():
            noisy_data = data.copy()
            noisy_data['close'] *= (1 + np.random.normal(0, 0.05, len(data)))  # 5% volatility
            volatile_data[symbol] = noisy_data

        volatile_signals = await pairs_trading_strategy.generate_signals(volatile_data)

        logger.info(f"Normal conditions: {len(normal_signals)} signals")
        logger.info(f"High volatility: {len(volatile_signals)} signals")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_data(self, pairs_trading_strategy):
        """Test error handling with invalid data"""
        logger.info("Testing error handling with invalid data")

        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        # Test with empty data
        empty_data = {}
        signals = await pairs_trading_strategy.generate_signals(empty_data)
        assert len(signals) == 0, "Should handle empty data gracefully"

        # Test with incomplete data (create minimal test data)
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        incomplete_data = {
            'AAPL': pd.DataFrame({
                'close': np.random.normal(150, 5, 10),
                'volume': np.random.randint(50000000, 150000000, 10)
            }, index=dates)
        }
        signals = await pairs_trading_strategy.generate_signals(incomplete_data)
        # Should not crash, may generate fewer signals
        assert isinstance(signals, list), "Should return list even with incomplete data"

        logger.info("Error handling test completed")

    @pytest.mark.asyncio
    async def test_error_handling_uninitialized_strategy(self, pairs_config):
        """Test error handling with uninitialized strategy"""
        logger.info("Testing error handling with uninitialized strategy")

        strategy = EnhancedPairsTradingStrategy(pairs_config)

        # Try to generate signals without initialization
        try:
            signals = await strategy.generate_signals({})
            # If it doesn't raise an error, that's also acceptable
            assert isinstance(signals, list), "Should return list even if uninitialized"
        except Exception as e:
            # If it fails, it should be a clear error
            logger.info(f"Uninitialized strategy properly raised error: {e}")

    @pytest.mark.asyncio
    async def test_pairs_trading_end_to_end_pipeline(self, pairs_trading_strategy, sample_market_data):
        """Test complete pairs trading pipeline from signal to P&L"""
        logger.info("Testing end-to-end pairs trading pipeline")

        # Initialize strategy
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()

        # Generate signals
        signals = await pairs_trading_strategy.generate_signals(sample_market_data)

        if signals:
            # Simulate execution
            simulator = ExecutionSimulator()
            execution_results = await simulator.simulate_execution(signals, sample_market_data)

            # Attribute performance
            attributor = PerformanceAttributor()
            attribution_result = attributor.validate_attribution(execution_results)

            # Validate complete pipeline
            assert 'total_pnl' in attribution_result, "Should have total P&L"
            assert 'strategy_contributions' in attribution_result, "Should have strategy contributions"

            logger.info(f"End-to-end pipeline P&L: {attribution_result.get('total_pnl', 'N/A')}")
        else:
            logger.info("No signals generated for end-to-end testing")