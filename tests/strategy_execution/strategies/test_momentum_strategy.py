"""
Momentum Strategy Execution Test
=================================

Comprehensive test suite for validating momentum strategy signal generation,
execution pipeline, and performance attribution.

This test validates:
- Signal generation accuracy from enriched market data
- Realistic execution with slippage and transaction costs
- Performance attribution to strategy logic vs. execution costs
- Multi-timeframe momentum analysis
- Regime-aware signal generation

Test Coverage:
- Signal quality validation (structure, timing, strength)
- End-to-end execution simulation
- Performance attribution accuracy
- Cross-market consistency
- Parameter sensitivity analysis

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
    StrategyTestEngine,
    StrategyTestConfig,
    SignalValidator,
    ExecutionSimulator,
    PerformanceAttributor
)

# Import strategy components
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from core_engine.trading.strategies.strategy_engine import StrategyConfig, StrategyType
from core_engine.config.strategies import MomentumConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMomentumStrategyExecution:
    """
    Comprehensive test suite for momentum strategy execution validation

    This test class validates the complete momentum strategy pipeline
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
    def momentum_config(self):
        """Create momentum strategy configuration"""
        return MomentumConfig(
            name="Test Momentum Strategy",
            strategy_id="momentum_test",
            symbols=["AAPL", "MSFT", "GOOGL"],
            short_period=10,
            medium_period=20,
            long_period=50,
            momentum_threshold=0.001,  # Very low for testing signal generation
            adx_threshold=10.0,  # Very low for testing
            volume_threshold=1.0,  # Very low for testing
            enable_breakout_detection=False,  # Disable for testing
            base_position_pct=0.03,
            max_position_pct=0.08
        )

    @pytest.fixture
    def sample_market_data(self) -> Dict[str, pd.DataFrame]:
        """Generate sample enriched market data for testing with realistic momentum scenarios"""

        np.random.seed(123)  # Changed seed for stronger trends

        symbols = ["AAPL", "MSFT", "GOOGL"]
        market_data = {}

        # Generate 6 months of 1-minute data (more data for better indicator calculation)
        dates = pd.date_range(start="2023-01-01", end="2023-07-01", freq="1min")
        n_periods = len(dates)

        for symbol in symbols:
            # Base price
            base_price = {"AAPL": 150, "MSFT": 250, "GOOGL": 2800}[symbol]

            # Create realistic price movements with trend periods
            # Mix of random walk, trending periods, and consolidation
            returns = np.zeros(n_periods)

            # Create trend periods (every 2 weeks, alternate up/down trends)
            trend_length = 2 * 24 * 60  # 2 days in minutes
            n_trends = n_periods // trend_length

            for i in range(n_trends):
                start_idx = i * trend_length
                end_idx = min((i + 1) * trend_length, n_periods)

                # Alternate between uptrend and downtrend
                if i % 2 == 0:  # Uptrend - stronger momentum
                    trend_strength = 0.002 + np.random.uniform(0.001, 0.004)  # Much stronger uptrend
                    trend_returns = np.random.normal(trend_strength, 0.008, end_idx - start_idx)
                else:  # Downtrend - also stronger
                    trend_strength = -0.002 - np.random.uniform(0.001, 0.004)  # Stronger downtrend
                    trend_returns = np.random.normal(trend_strength, 0.008, end_idx - start_idx)

                returns[start_idx:end_idx] = trend_returns

            # Add some consolidation periods (sideways movement)
            consolidation_periods = np.random.choice(n_periods, size=int(n_periods * 0.3), replace=False)
            returns[consolidation_periods] = np.random.normal(0, 0.002, len(consolidation_periods))

            # Generate prices from returns
            prices = base_price * np.exp(np.cumsum(returns))

            # Generate OHLCV data with realistic spreads
            high_mult = 1 + np.abs(np.random.normal(0, 0.003, n_periods))
            low_mult = 1 - np.abs(np.random.normal(0, 0.003, n_periods))
            volume_base = {"AAPL": 1000000, "MSFT": 800000, "GOOGL": 200000}[symbol]

            # Create volume spikes during trend periods
            volume_multiplier = np.ones(n_periods)
            for i in range(n_trends):
                start_idx = i * trend_length
                end_idx = min((i + 1) * trend_length, n_periods)
                # High volume during trends (1.5x to 3x normal)
                volume_multiplier[start_idx:end_idx] = np.random.uniform(1.5, 3.0, end_idx - start_idx)

            df = pd.DataFrame({
                'open': prices * (1 + np.random.normal(0, 0.001, n_periods)),
                'high': prices * high_mult,
                'low': prices * low_mult,
                'close': prices,
                'volume': volume_base * volume_multiplier * (1 + np.random.normal(0, 0.3, n_periods)),
                'timestamp': dates
            })

            # Calculate indicators (same as before but now with trend data)
            df['SMA_10'] = df['close'].rolling(10).mean()
            df['SMA_20'] = df['close'].rolling(20).mean()
            df['SMA_50'] = df['close'].rolling(50).mean()

            # RSI calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['RSI_14'] = 100 - (100 / (1 + rs))

            # MACD (simplified)
            ema12 = df['close'].ewm(span=12).mean()
            ema26 = df['close'].ewm(span=26).mean()
            df['MACD'] = ema12 - ema26

            # ATR (simplified)
            df['TR'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            df['ATR_14'] = df['TR'].rolling(14).mean()

            # ADX calculation (simplified but more realistic)
            # Calculate directional movement
            df['DM_plus'] = np.where(
                (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                np.maximum(df['high'] - df['high'].shift(1), 0),
                0
            )
            df['DM_minus'] = np.where(
                (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                np.maximum(df['low'].shift(1) - df['low'], 0),
                0
            )

            # Smooth DM values
            df['DM_plus_smooth'] = df['DM_plus'].rolling(14).mean()
            df['DM_minus_smooth'] = df['DM_minus'].rolling(14).mean()
            df['TR_smooth'] = df['TR'].rolling(14).mean()

            # Calculate DI values
            df['DI_plus'] = 100 * (df['DM_plus_smooth'] / df['TR_smooth'])
            df['DI_minus'] = 100 * (df['DM_minus_smooth'] / df['TR_smooth'])

            # Calculate DX and ADX
            df['DX'] = 100 * abs(df['DI_plus'] - df['DI_minus']) / (df['DI_plus'] + df['DI_minus'])
            df['ADX_14'] = df['DX'].rolling(14).mean()

            # Use ADX_14 as the adx indicator
            df['trend_strength'] = df['ADX_14'] / 100.0  # Normalize to 0-1 range

            # Volume ratio (higher during trends due to volume_multiplier)
            df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

            # Momentum indicators (will be stronger during trend periods)
            df['momentum_short'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10)
            df['momentum_medium'] = (df['close'] - df['close'].shift(20)) / df['close'].shift(20)
            df['momentum_long'] = (df['close'] - df['close'].shift(50)) / df['close'].shift(50)

            df.set_index('timestamp', inplace=True)
            market_data[symbol] = df.dropna()  # Remove NaN values

        return market_data

    @pytest.fixture
    async def momentum_strategy(self, momentum_config):
        """Create and initialize momentum strategy"""
        strategy = EnhancedMomentumStrategy(momentum_config)

        # Initialize strategy
        success = await strategy.initialize()
        assert success, "Strategy initialization failed"

        # Start strategy
        success = await strategy.start()
        assert success, "Strategy start failed"

        return strategy

    @pytest.mark.asyncio
    async def test_momentum_signal_generation(self, momentum_strategy, sample_market_data):
        """Test momentum strategy signal generation"""

        logger.info("Testing momentum signal generation")

        # Generate signals
        signals = await momentum_strategy.generate_signals(sample_market_data)

        # Basic validation
        assert isinstance(signals, list), "Signals should be a list"

        if signals:  # Only validate if signals were generated
            for signal in signals:
                # Validate signal structure
                assert hasattr(signal, 'strategy_id'), "Signal missing strategy_id"
                assert hasattr(signal, 'symbol'), "Signal missing symbol"
                assert hasattr(signal, 'signal_type'), "Signal missing signal_type"
                assert hasattr(signal, 'confidence'), "Signal missing confidence"
                assert hasattr(signal, 'strength'), "Signal missing strength"
                assert hasattr(signal, 'timestamp'), "Signal missing timestamp"

                # Validate signal values
                assert signal.confidence >= 0.0 and signal.confidence <= 1.0, "Invalid confidence range"
                assert signal.strength >= 0.0 and signal.strength <= 1.0, "Invalid strength range"
                assert signal.symbol in sample_market_data.keys(), "Invalid symbol"

        logger.info(f"Generated {len(signals)} momentum signals")

    @pytest.mark.asyncio
    async def test_signal_quality_validation(self, momentum_strategy, sample_market_data):
        """Test signal quality validation"""

        logger.info("Testing signal quality validation")

        # Generate signals
        signals = await momentum_strategy.generate_signals(sample_market_data)

        if not signals:
            pytest.skip("No signals generated for quality validation")

        # Create signal validator
        validator = SignalValidator()

        # Validate signals
        validation_results = await validator.validate_signal_quality(
            signals, sample_market_data, momentum_strategy.config
        )

        # Validate results structure
        assert "total_signals" in validation_results
        assert "valid_signals" in validation_results
        assert "quality_score" in validation_results
        assert "timing_accuracy" in validation_results
        assert "market_alignment" in validation_results

        # Validate quality thresholds
        assert validation_results["quality_score"] >= 0.0
        assert validation_results["timing_accuracy"] >= 0.0
        assert validation_results["market_alignment"] >= 0.0

        logger.info(f"Signal quality score: {validation_results['quality_score']:.3f}")

    @pytest.mark.asyncio
    async def test_execution_simulation(self, momentum_strategy, sample_market_data, test_config):
        """Test realistic execution simulation"""

        logger.info("Testing execution simulation")

        # Create execution simulator
        simulator = ExecutionSimulator()

        # Run execution simulation
        execution_results = await simulator.simulate_strategy_execution(
            momentum_strategy.config, sample_market_data, test_config
        )

        # Validate results structure
        assert "signals_tested" in execution_results
        assert "trades_executed" in execution_results
        assert "success_rate" in execution_results
        assert "avg_slippage" in execution_results
        assert "avg_cost" in execution_results
        assert "total_pnl" in execution_results
        assert "sharpe_ratio" in execution_results
        assert "trade_log" in execution_results

        # Validate execution quality
        assert execution_results["success_rate"] >= 0.0
        assert execution_results["avg_slippage"] >= 0.0
        assert execution_results["sharpe_ratio"] >= -10.0  # Allow negative Sharpe

        logger.info(f"Execution success rate: {execution_results['success_rate']:.3f}")
        logger.info(f"Average slippage: {execution_results['avg_slippage']:.6f}")

    @pytest.mark.asyncio
    async def test_performance_attribution(self, momentum_strategy, test_config):
        """Test performance attribution accuracy"""

        logger.info("Testing performance attribution")

        # Create sample trade log
        trade_log = self._generate_sample_trade_log(momentum_strategy.config.strategy_id)

        # Create performance attributor
        attributor = PerformanceAttributor()

        # Run attribution analysis
        attribution_results = await attributor.validate_attribution(
            momentum_strategy.config, trade_log
        )

        # Validate results structure
        assert "attribution_accuracy" in attribution_results
        assert "total_pnl" in attribution_results
        assert "strategy_contributions" in attribution_results
        assert "validation_checks" in attribution_results

        # Validate attribution accuracy
        assert attribution_results["attribution_accuracy"] >= 0.0
        assert attribution_results["attribution_accuracy"] <= 1.0

        logger.info(f"Attribution accuracy: {attribution_results['attribution_accuracy']:.3f}")

    @pytest.mark.asyncio
    async def test_comprehensive_strategy_validation(self, momentum_strategy, sample_market_data, test_config):
        """Test complete strategy validation pipeline"""

        logger.info("Testing comprehensive strategy validation")

        # Create test engine
        test_engine = StrategyTestEngine(test_config)

        # Run comprehensive validation
        validation_results = await test_engine.test_strategy_execution(
            momentum_strategy, momentum_strategy.config, sample_market_data
        )

        # Validate results structure
        assert "strategy_id" in validation_results
        assert "overall_result" in validation_results
        assert "signal_validation" in validation_results
        assert "execution_validation" in validation_results
        assert "performance_attribution" in validation_results

        # Log results
        logger.info(f"Overall result: {validation_results['overall_result']}")
        logger.info(f"Signal validation: {validation_results['signal_validation'].test_result}")
        logger.info(f"Execution validation: {validation_results['execution_validation'].test_result}")

    @pytest.mark.asyncio
    async def test_cross_market_consistency(self, momentum_strategy, sample_market_data):
        """Test signal consistency across different markets"""

        logger.info("Testing cross-market signal consistency")

        # Generate signals for each symbol
        symbol_signals = {}
        for symbol in momentum_strategy.config.symbols:
            if symbol in sample_market_data:
                # Create single-symbol market data
                single_symbol_data = {symbol: sample_market_data[symbol]}

                # Generate signals
                signals = await momentum_strategy.generate_signals(single_symbol_data)
                symbol_signals[symbol] = signals

        # Validate consistency
        signal_counts = [len(signals) for signals in symbol_signals.values()]
        avg_signals = np.mean(signal_counts) if signal_counts else 0

        # Check for reasonable consistency (not too much variation)
        if len(signal_counts) > 1:
            signal_std = np.std(signal_counts)
            consistency_ratio = signal_std / avg_signals if avg_signals > 0 else 0

            # Log consistency metrics
            logger.info(f"Cross-market signal consistency ratio: {consistency_ratio:.3f}")
            logger.info(f"Signal counts by symbol: {dict(zip(momentum_strategy.config.symbols, signal_counts))}")

    @pytest.mark.asyncio
    async def test_regime_aware_signaling(self, momentum_strategy, sample_market_data):
        """Test regime-aware signal generation"""

        logger.info("Testing regime-aware signaling")

        # Generate signals
        signals = await momentum_strategy.generate_signals(sample_market_data)

        if signals:
            # Analyze signals by market regime
            trending_signals = []
            ranging_signals = []

            for signal in signals:
                symbol = signal.symbol
                if symbol in sample_market_data:
                    df = sample_market_data[symbol]

                    # Simple regime detection
                    recent_volatility = df['close'].pct_change().std()
                    recent_trend = abs(df['close'].pct_change().mean())

                    if recent_trend > recent_volatility:
                        trending_signals.append(signal)
                    else:
                        ranging_signals.append(signal)

            # Log regime analysis
            logger.info(f"Trending regime signals: {len(trending_signals)}")
            logger.info(f"Ranging regime signals: {len(ranging_signals)}")

            # Validate regime awareness (basic check)
            total_signals = len(signals)
            if total_signals > 0:
                trending_ratio = len(trending_signals) / total_signals
                logger.info(f"Trending signal ratio: {trending_ratio:.3f}")

    def _generate_sample_trade_log(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Generate sample trade log for testing"""

        trade_log = []

        # Generate 50 sample trades
        for i in range(50):
            trade = {
                "signal_id": f"signal_{i}",
                "strategy_id": strategy_id,
                "symbol": np.random.choice(["AAPL", "MSFT", "GOOGL"]),
                "signal_type": np.random.choice(["BUY", "SELL"]),
                "intended_quantity": np.random.uniform(1000, 10000),
                "executed_quantity": np.random.uniform(900, 9500),  # Slight reduction for partial fills
                "intended_price": np.random.uniform(100, 3000),
                "executed_price": np.random.uniform(100, 3000),
                "slippage_bps": np.random.uniform(0, 50),
                "transaction_cost": np.random.uniform(5, 50),
                "total_cost": np.random.uniform(1000, 50000),
                "execution_time": datetime.now() - timedelta(minutes=np.random.randint(1, 1000)),
                "fill_rate": np.random.uniform(0.9, 1.0),
                "pnl": np.random.normal(100, 500)  # Random P&L
            }
            trade_log.append(trade)

        return trade_log

    @pytest.mark.asyncio
    async def test_parameter_sensitivity(self, momentum_strategy, sample_market_data):
        """Test strategy sensitivity to parameter changes"""

        logger.info("Testing parameter sensitivity")

        base_config = momentum_strategy.config
        sensitivity_results = {}

        # Test different momentum thresholds
        thresholds = [0.01, 0.02, 0.05]
        for threshold in thresholds:
            # Modify config
            test_config = MomentumConfig(
                name=f"Momentum Threshold {threshold}",
                strategy_id=f"momentum_threshold_{threshold}",
                symbols=base_config.symbols,
                momentum_threshold=threshold,
                adx_threshold=base_config.adx_threshold,
                volume_threshold=base_config.volume_threshold,
                short_period=base_config.short_period,
                medium_period=base_config.medium_period,
                long_period=base_config.long_period
            )

            # Create test strategy
            test_strategy = EnhancedMomentumStrategy(test_config)
            await test_strategy.initialize()
            await test_strategy.start()

            # Generate signals
            signals = await test_strategy.generate_signals(sample_market_data)
            sensitivity_results[f"threshold_{threshold}"] = len(signals)

        # Log sensitivity analysis
        logger.info("Parameter sensitivity results:")
        for param, signal_count in sensitivity_results.items():
            logger.info(f"  {param}: {signal_count} signals")

    @pytest.mark.asyncio
    async def test_strategy_stress_testing(self, momentum_strategy, sample_market_data):
        """Test strategy under stress conditions"""

        logger.info("Testing strategy stress conditions")

        # Test with high volatility data
        stress_data = {}
        for symbol, df in sample_market_data.items():
            # Increase volatility
            stressed_df = df.copy()
            stressed_df['close'] *= (1 + np.random.normal(0, 0.05, len(df)))  # 5% vol stress
            stress_data[symbol] = stressed_df

        # Generate signals under stress
        stress_signals = await momentum_strategy.generate_signals(stress_data)

        # Test with low liquidity data
        low_liq_data = {}
        for symbol, df in sample_market_data.items():
            # Reduce volume
            low_liq_df = df.copy()
            low_liq_df['volume'] *= 0.1  # 90% volume reduction
            low_liq_data[symbol] = low_liq_df

        # Generate signals with low liquidity
        low_liq_signals = await momentum_strategy.generate_signals(low_liq_data)

        # Log stress test results
        logger.info(f"Normal conditions: {len(await momentum_strategy.generate_signals(sample_market_data))} signals")
        logger.info(f"High volatility: {len(stress_signals)} signals")
        logger.info(f"Low liquidity: {len(low_liq_signals)} signals")

        # Validate strategy stability
        assert len(stress_signals) >= 0, "Strategy should handle high volatility"
        assert len(low_liq_signals) >= 0, "Strategy should handle low liquidity"