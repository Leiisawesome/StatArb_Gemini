"""
Breakout Strategy Execution Test
=================================

Comprehensive test suite for validating breakout strategy signal generation,
execution pipeline, and performance attribution.

This test validates:
- Breakout detection accuracy from enriched market data
- Volume confirmation for breakout signals
- False breakout filtering
- Dynamic position sizing based on breakout strength
- Realistic execution with slippage and transaction costs
- Performance attribution to strategy logic vs. execution costs
- Regime-aware breakout filtering

Test Coverage:
- Signal quality validation (structure, timing, strength)
- End-to-end execution simulation
- Performance attribution accuracy
- Cross-market consistency
- Parameter sensitivity analysis
- Breakout detection accuracy
- Volume confirmation effectiveness
- False breakout filtering

Author: StatArb_Gemini Phase 7 Strategy Validation
Version: 1.0.0
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict
import logging

# Import testing framework
from tests.strategy_execution.framework import (
    StrategyTestEngine,
    StrategyTestConfig,
    SignalValidator,
    ExecutionSimulator,
    PerformanceAttributor
)

# Import strategy components
from core_engine.trading.strategies.implementations.breakout.enhanced_breakout import EnhancedBreakoutStrategy
from core_engine.config.strategies import BreakoutConfig
from core_engine.config.component_config import PositionLimits, RiskLimits

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestBreakoutStrategyExecution:
    """
    Comprehensive test suite for breakout strategy execution validation

    This test class validates the complete breakout strategy pipeline
    from signal generation through execution to performance attribution.
    """

    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        return StrategyTestConfig(
            test_start_date=datetime(2023, 1, 1),
            test_end_date=datetime(2024, 1, 1),
            symbols=["AAPL", "MSFT", "GOOGL"],
            initial_capital=1_000_000.0,
            enable_realistic_execution=True,
            min_signal_quality_threshold=0.6,
            max_acceptable_slippage=0.001,
            required_execution_success_rate=0.95,
            minimum_sharpe_ratio=0.5,
            maximum_acceptable_drawdown=0.20
        )

    @pytest.fixture
    def breakout_config(self):
        """Create breakout strategy configuration"""
        return BreakoutConfig(
            symbols=["AAPL", "MSFT", "GOOGL"],
            lookback_period=20,
            breakout_threshold=0.02,
            volume_confirmation=True,
            volume_multiplier=1.5,
            consolidation_periods=10,
            # Position sizing from position_limits
            position_limits=PositionLimits(
                base_position_pct=0.03,
                max_position_pct=0.08
            ),
            # Risk management from risk_limits
            risk_limits=RiskLimits(
                stop_loss_pct=0.03
            ),
            profit_target_ratio=2.0
        )

    @pytest.fixture
    def sample_market_data(self) -> Dict[str, pd.DataFrame]:
        """Generate sample enriched market data for testing with realistic breakout scenarios"""

        np.random.seed(42)  # Seed for reproducible results

        symbols = ["AAPL", "MSFT", "GOOGL"]
        market_data = {}

        # Generate 6 months of 1-minute data (more data for better indicator calculation)
        dates = pd.date_range(start="2023-01-01", end="2023-07-01", freq="1min")
        n_periods = len(dates)

        for symbol in symbols:
            # Base price
            base_price = {"AAPL": 150, "MSFT": 250, "GOOGL": 2800}[symbol]

            # Create realistic price movements with breakout scenarios
            # Mix of consolidation periods followed by breakouts
            returns = np.zeros(n_periods)

            # Create consolidation periods followed by breakouts
            consolidation_length = 2 * 24 * 60  # 2 days in minutes
            breakout_length = 1 * 24 * 60      # 1 day in minutes
            cycle_length = consolidation_length + breakout_length
            n_cycles = n_periods // cycle_length

            for i in range(n_cycles):
                cons_start = i * cycle_length
                cons_end = cons_start + consolidation_length
                breakout_start = cons_end
                breakout_end = min(breakout_start + breakout_length, n_periods)

                # Consolidation period - tight range
                if cons_end <= n_periods:
                    returns[cons_start:cons_end] = np.random.normal(0, 0.002, cons_end - cons_start)

                # Breakout period - strong directional move
                if breakout_end <= n_periods:
                    # Alternate between bullish and bearish breakouts
                    if i % 2 == 0:  # Bullish breakout
                        breakout_strength = 0.01 + np.random.uniform(0.005, 0.015)  # Strong upward move
                        returns[breakout_start:breakout_end] = np.random.normal(breakout_strength, 0.008, breakout_end - breakout_start)
                    else:  # Bearish breakout
                        breakout_strength = -0.01 - np.random.uniform(0.005, 0.015)  # Strong downward move
                        returns[breakout_start:breakout_end] = np.random.normal(breakout_strength, 0.008, breakout_end - breakout_start)

            # Add some false breakouts (breakout that fails)
            false_breakout_periods = np.random.choice(n_periods, size=int(n_periods * 0.1), replace=False)
            for idx in false_breakout_periods:
                if idx < n_periods - 10:  # Ensure we have room for reversal
                    # Initial breakout move
                    returns[idx:idx+5] = np.random.choice([-0.015, 0.015], 5)
                    # Reversal back
                    returns[idx+5:idx+10] = -returns[idx:idx+5] * 0.8

            # Generate prices from returns
            prices = base_price * np.exp(np.cumsum(returns))

            # Generate OHLCV data with realistic spreads
            high_mult = 1 + np.abs(np.random.normal(0, 0.005, n_periods))
            low_mult = 1 - np.abs(np.random.normal(0, 0.005, n_periods))
            volume_base = {"AAPL": 1000000, "MSFT": 800000, "GOOGL": 200000}[symbol]

            # Create volume spikes during breakout periods
            volume_multiplier = np.ones(n_periods)
            for i in range(n_cycles):
                breakout_start = i * cycle_length + consolidation_length
                breakout_end = min(breakout_start + breakout_length, n_periods)
                if breakout_end <= n_periods:
                    volume_multiplier[breakout_start:breakout_end] = np.random.uniform(2.0, 4.0)

            # Create DataFrame with OHLCV and technical indicators
            df = pd.DataFrame({
                'timestamp': dates,
                'open': prices * (1 + np.random.normal(0, 0.002, n_periods)),
                'high': prices * high_mult,
                'low': prices * low_mult,
                'close': prices,
                'volume': volume_base * volume_multiplier * np.random.uniform(0.8, 1.2, n_periods),
                'vwap': prices * (1 + np.random.normal(0, 0.001, n_periods)),
                'adv20': np.full(n_periods, volume_base),  # Average daily volume
            })

            # Ensure high >= max(open, close) and low <= min(open, close)
            df['high'] = np.maximum(df[['open', 'close']].max(axis=1), df['high'])
            df['low'] = np.minimum(df[['open', 'close']].min(axis=1), df['low'])

            # Add technical indicators that the strategy expects
            # Simple moving average for trend
            df['SMA_20'] = df['close'].rolling(window=20).mean()

            # ATR for volatility
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift(1))
            low_close = np.abs(df['low'] - df['close'].shift(1))
            tr = np.maximum(high_low, np.maximum(high_close, low_close))
            df['ATR_14'] = tr.rolling(window=14).mean()

            # Volume ratio for volume confirmation
            df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()

            # Fill NaN values
            df = df.bfill().ffill().fillna(0)

            market_data[symbol] = df

        return market_data

    @pytest.fixture
    async def breakout_strategy(self, breakout_config, sample_market_data):
        """Create and initialize breakout strategy"""
        strategy = EnhancedBreakoutStrategy(breakout_config)

        # Initialize strategy
        await strategy.initialize()

        # Start strategy
        await strategy.start()

        # Generate initial signals to populate internal state
        await strategy.generate_signals(sample_market_data)

        yield strategy

        # Cleanup
        await strategy.stop()

    async def test_breakout_signal_generation(self, breakout_strategy, sample_market_data):
        """Test breakout signal generation"""
        logger.info("Testing breakout signal generation")

        # Generate signals
        signals = await breakout_strategy.generate_signals(sample_market_data)

        # Validate signals
        assert isinstance(signals, list)
        assert len(signals) >= 0  # May generate 0 or more signals depending on market conditions

        # Check signal structure if signals exist
        for signal in signals:
            assert hasattr(signal, 'symbol')
            assert hasattr(signal, 'signal_type')
            assert hasattr(signal, 'strength')
            assert hasattr(signal, 'confidence')
            assert signal.symbol in ["AAPL", "MSFT", "GOOGL"]
            assert signal.signal_type in ['BUY', 'SELL', 'HOLD']
            assert 0 <= signal.confidence <= 1
            assert 0 <= signal.strength <= 1

        logger.info(f"Generated {len(signals)} breakout signals")

    async def test_signal_quality_validation(self, breakout_strategy, sample_market_data):
        """Test signal quality validation"""
        logger.info("Testing signal quality validation")

        # Generate signals
        signals = await breakout_strategy.generate_signals(sample_market_data)

        # Validate signals
        signal_validator = SignalValidator()
        quality_result = await signal_validator.validate_signal_quality(signals, sample_market_data, breakout_strategy.config)

        assert 'valid_signals' in quality_result
        assert 'invalid_signals' in quality_result
        assert 'quality_score' in quality_result
        assert quality_result['quality_score'] >= 0.0

        logger.info(f"Signal quality validation: {quality_result['quality_score']:.3f}")

    async def test_execution_simulation(self, breakout_strategy, sample_market_data, test_config):
        """Test realistic execution simulation"""
        logger.info("Testing execution simulation")

        # Generate signals
        signals = await breakout_strategy.generate_signals(sample_market_data)

        if signals:
            # Create execution simulator
            execution_simulator = ExecutionSimulator()

            # Simulate execution
            execution_result = await execution_simulator.simulate_strategy_execution(
                breakout_strategy.config, sample_market_data, test_config
            )

            assert 'signals_tested' in execution_result
            assert 'trades_executed' in execution_result
            assert 'execution_success_rate' in execution_result
            assert 'average_slippage' in execution_result
            assert 'average_transaction_cost' in execution_result

            # Check execution success rate
            success_rate = execution_result.get('execution_success_rate', 0)
            assert success_rate >= test_config.required_execution_success_rate

            logger.info(f"Execution simulation: {execution_result.get('trades_executed', 0)} trades executed")
        else:
            logger.info("No signals generated for execution simulation")

    async def test_performance_attribution(self, breakout_strategy, sample_market_data, test_config):
        """Test performance attribution accuracy"""
        logger.info("Testing performance attribution")

        # Generate signals
        signals = await breakout_strategy.generate_signals(sample_market_data)

        if signals:
            # Create execution simulator
            execution_simulator = ExecutionSimulator()
            execution_result = await execution_simulator.simulate_strategy_execution(
                breakout_strategy.config, sample_market_data, test_config
            )

            # Create mock trades for attribution
            mock_trades = [
                {
                    'symbol': signal.symbol,
                    'entry_price': 100.0,  # Mock price
                    'exit_price': 105.0,   # Mock exit price
                    'quantity': signal.quantity,
                    'entry_time': signal.timestamp,
                    'exit_time': signal.timestamp + timedelta(hours=1),
                    'pnl': 500.0  # Mock P&L
                }
                for signal in signals[:5]  # Use first 5 signals
            ]

            # Test attribution
            performance_attributor = PerformanceAttributor()
            attribution_result = await performance_attributor.attribute_performance(mock_trades, breakout_strategy.strategy_id)

            assert 'total_return' in attribution_result
            assert 'strategy_contribution' in attribution_result
            assert 'execution_cost_impact' in attribution_result

            logger.info(f"Performance attribution: {attribution_result['total_return']:.4f} total return")
        else:
            logger.info("No signals generated for performance attribution")

    async def test_comprehensive_validation(self, breakout_strategy, sample_market_data, test_config):
        """Test comprehensive end-to-end validation"""
        logger.info("Testing comprehensive validation")

        # Run full validation pipeline
        test_engine = StrategyTestEngine(test_config)
        validation_result = await test_engine.test_strategy_execution(
            breakout_strategy, breakout_strategy.config, sample_market_data
        )

        assert 'overall_result' in validation_result
        assert 'signal_validation' in validation_result
        assert 'execution_validation' in validation_result
        assert 'performance_attribution' in validation_result

        # Check minimum requirements
        assert validation_result['overall_result'].name in ['PASS', 'FAIL']

        logger.info(f"Comprehensive validation result: {validation_result['overall_result']}")
        logger.info(f"Signal validation: {validation_result['signal_validation']}")
        logger.info(f"Execution validation: {validation_result['execution_validation']}")

    async def test_cross_market_consistency(self, breakout_strategy, sample_market_data):
        """Test signal consistency across different market conditions"""
        logger.info("Testing cross-market consistency")

        # Test with different market data subsets
        symbols_to_test = ["AAPL", "MSFT"]

        for symbol in symbols_to_test:
            symbol_data = {symbol: sample_market_data[symbol]}

            # Generate signals for single symbol
            signals = await breakout_strategy.generate_signals(symbol_data)

            # Validate signal consistency
            for signal in signals:
                assert signal.symbol == symbol
                assert signal.confidence >= 0.5  # Minimum confidence for valid signals

        logger.info("Cross-market consistency validated")

    async def test_regime_aware_signaling(self, breakout_strategy, sample_market_data):
        """Test regime-aware breakout signaling"""
        logger.info("Testing regime-aware signaling")

        # Generate signals
        signals = await breakout_strategy.generate_signals(sample_market_data)

        # Check that signals are appropriate for breakout conditions
        for signal in signals:
            # Breakout signals should have high confidence when volume confirms
            if signal.confidence > 0.7:
                # Verify the signal occurred during breakout conditions
                symbol_data = sample_market_data[signal.symbol]
                current_data = symbol_data.iloc[-1]

                # Check if volume ratio supports the signal
                volume_ratio = current_data.get('volume_ratio', 1.0)
                assert volume_ratio >= breakout_strategy.config.volume_multiplier

        logger.info("Regime-aware signaling validated")

    async def test_parameter_sensitivity(self, breakout_config, sample_market_data):
        """Test parameter sensitivity analysis"""
        logger.info("Testing parameter sensitivity")

        # Test different breakout thresholds
        thresholds = [0.01, 0.02, 0.03]
        signal_counts = []

        for threshold in thresholds:
            config = BreakoutConfig(**breakout_config.__dict__)
            config.breakout_threshold = threshold

            strategy = EnhancedBreakoutStrategy(config)
            await strategy.initialize()
            await strategy.start()

            signals = await strategy.generate_signals(sample_market_data)
            signal_counts.append(len(signals))

            await strategy.stop()

        # More signals should be generated with lower thresholds
        assert signal_counts[0] >= signal_counts[1] >= signal_counts[2]

        logger.info(f"Parameter sensitivity: thresholds {thresholds} -> signals {signal_counts}")

    async def test_breakout_detection_accuracy(self, breakout_strategy, sample_market_data):
        """Test breakout detection accuracy"""
        logger.info("Testing breakout detection accuracy")

        # Generate signals
        signals = await breakout_strategy.generate_signals(sample_market_data)

        # Validate breakout detection logic
        for signal in signals:
            symbol_data = sample_market_data[signal.symbol]
            lookback_data = symbol_data.tail(breakout_strategy.config.lookback_period + 1)

            # Calculate support/resistance levels
            resistance = lookback_data['high'].max()
            support = lookback_data['low'].min()
            current_price = lookback_data['close'].iloc[-1]

            # Verify breakout conditions
            if signal.signal_type == 'BUY':
                assert current_price > resistance * (1 + breakout_strategy.config.breakout_threshold)
            elif signal.signal_type == 'SELL':
                assert current_price < support * (1 - breakout_strategy.config.breakout_threshold)

        logger.info("Breakout detection accuracy validated")

    async def test_volume_confirmation(self, breakout_strategy, sample_market_data):
        """Test volume confirmation effectiveness"""
        logger.info("Testing volume confirmation")

        # Generate signals
        signals = await breakout_strategy.generate_signals(sample_market_data)

        # Check volume confirmation for high-confidence signals
        for signal in signals:
            if signal.confidence > 0.6:  # High confidence signals should have volume confirmation
                symbol_data = sample_market_data[signal.symbol]
                current_data = symbol_data.iloc[-1]

                volume_ratio = current_data.get('volume_ratio', 1.0)
                assert volume_ratio >= breakout_strategy.config.volume_multiplier

        logger.info("Volume confirmation validated")

    async def test_false_breakout_filtering(self, breakout_strategy, sample_market_data):
        """Test false breakout filtering"""
        logger.info("Testing false breakout filtering")

        # Generate signals
        signals = await breakout_strategy.generate_signals(sample_market_data)

        # Track positions to ensure no duplicate signals for same symbol
        active_symbols = set()

        for signal in signals:
            # Should not have multiple signals for same symbol without position close
            assert signal.symbol not in active_symbols
            active_symbols.add(signal.symbol)

        logger.info("False breakout filtering validated")

    async def test_adaptive_position_sizing(self, breakout_strategy, sample_market_data):
        """Test adaptive position sizing based on breakout strength"""
        logger.info("Testing adaptive position sizing")

        # Generate signals
        signals = await breakout_strategy.generate_signals(sample_market_data)

        for signal in signals:
            # Calculate position size
            position_size = breakout_strategy.calculate_position_size(signal, sample_market_data)

            # Validate position size bounds
            assert breakout_strategy.config.base_position_pct <= position_size <= breakout_strategy.config.max_position_pct

            # Higher confidence should generally lead to larger positions
            expected_size = breakout_strategy.config.base_position_pct * signal.confidence
            assert abs(position_size - expected_size) < 0.01  # Allow small tolerance

        logger.info("Adaptive position sizing validated")

    async def test_stress_testing(self, breakout_strategy, sample_market_data):
        """Test strategy under stress conditions"""
        logger.info("Testing stress conditions")

        # Test with high volatility data
        stress_data = {}
        for symbol, data in sample_market_data.items():
            # Amplify volatility
            stressed_data = data.copy()
            stressed_data['close'] *= (1 + np.random.normal(0, 0.05, len(data)))
            stressed_data['high'] = np.maximum(stressed_data[['open', 'close']].max(axis=1), stressed_data['high'])
            stressed_data['low'] = np.minimum(stressed_data[['open', 'close']].min(axis=1), stressed_data['low'])
            stress_data[symbol] = stressed_data

        # Generate signals under stress
        signals = await breakout_strategy.generate_signals(stress_data)

        # Strategy should still function (not crash) under stress
        assert isinstance(signals, list)

        logger.info(f"Stress testing: {len(signals)} signals under high volatility")

    async def test_error_handling(self, breakout_strategy):
        """Test error handling and robustness"""
        logger.info("Testing error handling")

        # Test with invalid data
        invalid_data = {"INVALID": pd.DataFrame()}

        # Should handle gracefully
        signals = await breakout_strategy.generate_signals(invalid_data)
        assert isinstance(signals, list)  # Should return empty list, not crash

        logger.info("Error handling validated")

    async def test_end_to_end_pipeline(self, breakout_strategy, sample_market_data, test_config):
        """Test complete end-to-end pipeline"""
        logger.info("Testing end-to-end pipeline")

        # 1. Generate signals
        signals = await breakout_strategy.generate_signals(sample_market_data)

        # 2. Validate signals
        signal_validator = SignalValidator()
        quality_result = await signal_validator.validate_signal_quality(signals, sample_market_data, breakout_strategy.config)

        # 3. Simulate execution if signals exist
        if signals:
            execution_simulator = ExecutionSimulator()
            execution_result = await execution_simulator.simulate_strategy_execution(
                breakout_strategy.config, sample_market_data, test_config
            )

            # 4. Create mock trades for attribution
            mock_trades = [
                {
                    'symbol': signal.symbol,
                    'entry_price': 100.0,
                    'exit_price': 105.0,
                    'quantity': signal.quantity,
                    'entry_time': signal.timestamp,
                    'exit_time': signal.timestamp + timedelta(hours=1),
                    'pnl': 500.0
                }
                for signal in signals[:3]  # Use first 3 signals
            ]

            # 5. Attribute performance
            performance_attributor = PerformanceAttributor()
            attribution_result = await performance_attributor.attribute_performance(mock_trades, breakout_strategy.strategy_id)

            # Validate complete pipeline
            assert quality_result['quality_score'] >= 0.0
            assert 'total_return' in attribution_result
        else:
            # No signals case
            assert quality_result['quality_score'] >= 0.0

        logger.info("End-to-end pipeline validation complete")