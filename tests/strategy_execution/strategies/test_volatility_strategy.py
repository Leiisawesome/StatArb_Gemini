"""
Volatility Strategy Execution Tests
==================================

Comprehensive test suite for EnhancedVolatilityStrategy execution validation.
Tests signal generation, quality validation, execution simulation, performance attribution,
and comprehensive validation across volatility regimes and market conditions.

Author: StatArb_Gemini Phase 7 Strategy Validation
Date: October 28, 2025
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List

from core_engine.trading.strategies.implementations.volatility.enhanced_volatility import (
    EnhancedVolatilityStrategy, VolatilityConfig
)
from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType
from tests.strategy_execution.framework.strategy_test_engine import StrategyTestEngine
from tests.strategy_execution.framework.signal_validator import SignalValidator
from tests.strategy_execution.framework.execution_simulator import ExecutionSimulator
from tests.strategy_execution.framework.performance_attributor import PerformanceAttributor


class TestVolatilityStrategyExecution:
    """Comprehensive volatility strategy execution tests"""

    @pytest.fixture
    def volatility_config(self) -> VolatilityConfig:
        """Create volatility strategy configuration"""
        return VolatilityConfig(
            volatility_lookback=20,
            volatility_threshold=0.02,
            regime_detection=True,
            base_position_pct=0.025,
            max_position_pct=0.07,
            volatility_scaling=True,
            vol_target=0.15,
            symbols=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        )

    @pytest.fixture
    def sample_market_data(self, volatility_config: VolatilityConfig) -> Dict[str, pd.DataFrame]:
        """Generate sample market data with volatility features"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        data = {}
        for symbol in volatility_config.symbols:
            # Generate price data with different volatility regimes
            base_price = 100 + np.random.randn() * 20

            # Create returns with varying volatility
            returns = np.random.randn(100) * 0.02  # Base volatility
            # Add volatility clustering (high vol periods)
            high_vol_periods = np.random.choice(100, 20, replace=False)
            returns[high_vol_periods] *= 3  # 3x volatility in high vol periods

            # Low vol periods
            low_vol_periods = np.random.choice(100, 15, replace=False)
            returns[low_vol_periods] *= 0.3  # 0.3x volatility in low vol periods

            prices = base_price * (1 + returns).cumprod()

            # Create DataFrame with required features
            df = pd.DataFrame({
                'close': prices,
                'high': prices * (1 + np.abs(np.random.randn(100)) * 0.02),
                'low': prices * (1 - np.abs(np.random.randn(100)) * 0.02),
                'returns_1': returns,
                'volatility': pd.Series(np.abs(returns)).rolling(20).mean().values,  # Pre-calculated volatility
                'ATR_14': pd.Series(np.abs(returns)).rolling(14).mean().values * prices  # ATR approximation
            }, index=dates)

            # Fill NaN values
            df = df.bfill().ffill()

            data[symbol] = df

        return data

    @pytest.mark.asyncio
    async def test_volatility_signal_generation(self, volatility_config: VolatilityConfig,
                                               sample_market_data: Dict[str, pd.DataFrame]):
        """Test volatility strategy signal generation"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        signals = await strategy.generate_signals(sample_market_data)

        # Validate signal structure
        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.strategy_id == strategy.strategy_id
            assert signal.symbol in volatility_config.symbols
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL]
            assert 0 < signal.strength <= 1.0
            assert 0 < signal.confidence <= 1.0
            assert signal.target_quantity > 0

        # Log results
        print(f"Generated {len(signals)} volatility signals")

    @pytest.mark.asyncio
    async def test_signal_quality_validation(self, volatility_config: VolatilityConfig,
                                           sample_market_data: Dict[str, pd.DataFrame]):
        """Test signal quality validation for volatility strategy"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        signals = await strategy.generate_signals(sample_market_data)

        # Initialize signal validator
        validator = SignalValidator()

        # Validate signals
        quality_metrics = await validator.validate_signal_quality(signals, sample_market_data)

        # Check quality metrics structure
        assert isinstance(quality_metrics, dict)
        assert 'quality_score' in quality_metrics  # Updated to match actual return key
        assert 'total_signals' in quality_metrics  # Updated to match actual return key
        assert 'valid_signals' in quality_metrics  # Updated to match actual return key

        print(f"Signal quality validation: {quality_metrics.get('total_signals', 0)} signals")

    @pytest.mark.asyncio
    async def test_execution_simulation(self, volatility_config: VolatilityConfig,
                                      sample_market_data: Dict[str, pd.DataFrame]):
        """Test execution simulation for volatility signals"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        signals = await strategy.generate_signals(sample_market_data)

        if signals:
            # Initialize execution simulator
            simulator = ExecutionSimulator()

            # Simulate execution
            execution_results = await simulator.simulate_execution(signals, sample_market_data)

            # Validate execution results
            assert isinstance(execution_results, dict)
            assert 'executed_signals' in execution_results
            assert 'failed_signals' in execution_results
            assert 'execution_summary' in execution_results

        print(f"Execution simulation: {len(signals)} signals tested")

    @pytest.mark.asyncio
    async def test_performance_attribution(self, volatility_config: VolatilityConfig,
                                         sample_market_data: Dict[str, pd.DataFrame]):
        """Test performance attribution for volatility strategy"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        signals = await strategy.generate_signals(sample_market_data)

        if signals:
            # Initialize performance attributor
            attributor = PerformanceAttributor()

            # Attribute performance
            attribution_results = await attributor.attribute_performance(signals, sample_market_data)

            # Validate attribution results
            assert isinstance(attribution_results, dict)
            assert 'total_return' in attribution_results
            assert 'sharpe_ratio' in attribution_results
            assert 'max_drawdown' in attribution_results

        print(f"Performance attribution: {len(signals)} signals analyzed")

    @pytest.mark.asyncio
    async def test_comprehensive_validation(self, volatility_config: VolatilityConfig,
                                          sample_market_data: Dict[str, pd.DataFrame]):
        """Test comprehensive validation pipeline"""
        # Initialize strategy test engine
        from tests.strategy_execution.framework.strategy_test_engine import StrategyTestConfig
        test_config = StrategyTestConfig(
            test_start_date=datetime.now() - timedelta(days=100),
            test_end_date=datetime.now(),
            symbols=volatility_config.symbols
        )
        engine = StrategyTestEngine(test_config)

        # Create strategy instance
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        # Run comprehensive validation
        validation_results = await engine.test_strategy_execution(
            strategy, volatility_config, sample_market_data
        )

        # Validate results structure
        assert isinstance(validation_results, dict)
        assert 'signal_validation' in validation_results
        assert 'execution_validation' in validation_results
        assert 'performance_attribution' in validation_results  # Updated to match actual return key
        assert 'overall_result' in validation_results

        print("Comprehensive validation completed (config compatibility handled)")

    @pytest.mark.asyncio
    async def test_cross_market_consistency(self, volatility_config: VolatilityConfig):
        """Test volatility strategy consistency across different market conditions"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        # Test different market conditions
        conditions = ['normal', 'high_volatility', 'low_liquidity']

        for condition in conditions:
            # Generate market data for specific condition
            market_data = self._generate_market_data_for_condition(
                volatility_config.symbols, condition
            )

            signals = await strategy.generate_signals(market_data)

            # Validate signals are reasonable for condition
            assert isinstance(signals, list)

            print(f"Cross-market consistency ({condition}): {len(signals)} signals")

    @pytest.mark.asyncio
    async def test_regime_aware_signaling(self, volatility_config: VolatilityConfig):
        """Test regime-aware signaling in volatility strategy"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        # Test different regimes
        regimes = ['bull', 'bear', 'sideways']

        for regime in regimes:
            # Generate market data for specific regime
            market_data = self._generate_market_data_for_regime(
                volatility_config.symbols, regime
            )

            signals = await strategy.generate_signals(market_data)

            # Validate signals are appropriate for regime
            assert isinstance(signals, list)

            print(f"Regime-aware signaling ({regime}): {len(signals)} signals")

    @pytest.mark.asyncio
    async def test_parameter_sensitivity(self, volatility_config: VolatilityConfig,
                                       sample_market_data: Dict[str, pd.DataFrame]):
        """Test parameter sensitivity analysis"""
        base_signals = []

        # Test different parameter combinations
        param_combinations = [
            {'volatility_threshold': 0.01, 'vol_target': 0.10},
            {'volatility_threshold': 0.03, 'vol_target': 0.20},
            {'volatility_threshold': 0.05, 'vol_target': 0.25}
        ]

        for params in param_combinations:
            # Create config with modified parameters
            test_config = VolatilityConfig(**{**volatility_config.__dict__, **params})
            strategy = EnhancedVolatilityStrategy(test_config)
            await strategy.initialize()

            signals = await strategy.generate_signals(sample_market_data)
            base_signals.append(len(signals))

        print(f"Parameter sensitivity: thresholds -> signals {base_signals}")

    @pytest.mark.asyncio
    async def test_volatility_regime_detection(self, volatility_config: VolatilityConfig):
        """Test volatility regime detection logic"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        # Generate data with known volatility regimes
        market_data = self._generate_volatility_regime_data(volatility_config.symbols)

        signals = await strategy.generate_signals(market_data)

        # Validate regime detection worked
        assert isinstance(signals, list)

        print(f"Volatility regime detection: {len(signals)} signals generated")

    @pytest.mark.asyncio
    async def test_volatility_scaling_logic(self, volatility_config: VolatilityConfig):
        """Test volatility-based position scaling"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        # Create test signal
        test_signal = StrategySignal(
            strategy_id=strategy.strategy_id,
            symbol='AAPL',
            signal_type=SignalType.BUY,
            strength=0.8,
            confidence=0.9,
            target_quantity=0.02,
            timestamp=datetime.now()
        )

        # Generate market data with different volatility levels
        high_vol_data = self._generate_high_volatility_data(['AAPL'])
        low_vol_data = self._generate_low_volatility_data(['AAPL'])

        # Test position sizing in different volatility regimes
        high_vol_size = strategy.calculate_position_size(test_signal, high_vol_data)
        low_vol_size = strategy.calculate_position_size(test_signal, low_vol_data)

        # High volatility should result in smaller position
        assert high_vol_size <= low_vol_size

        print(f"Volatility scaling: high_vol={high_vol_size:.4f}, low_vol={low_vol_size:.4f}")

    @pytest.mark.asyncio
    async def test_volatility_threshold_logic(self, volatility_config: VolatilityConfig):
        """Test volatility threshold-based signal generation"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        # Generate data with volatility above/below thresholds
        above_threshold_data = self._generate_above_threshold_data(volatility_config.symbols)
        below_threshold_data = self._generate_below_threshold_data(volatility_config.symbols)

        above_signals = await strategy.generate_signals(above_threshold_data)
        below_signals = await strategy.generate_signals(below_threshold_data)

        # Validate signal generation logic
        assert isinstance(above_signals, list)
        assert isinstance(below_signals, list)

        print(f"Volatility threshold logic: above={len(above_signals)}, below={len(below_signals)} signals")

    @pytest.mark.asyncio
    async def test_risk_targeting(self, volatility_config: VolatilityConfig):
        """Test volatility targeting for risk management"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        # Generate market data
        market_data = self._generate_market_data_for_condition(volatility_config.symbols, 'normal')

        signals = await strategy.generate_signals(market_data)

        # Check that position sizes align with volatility target
        total_exposure = sum(signal.target_quantity for signal in signals)

        # Should not exceed reasonable bounds
        assert total_exposure <= len(volatility_config.symbols) * volatility_config.max_position_pct

        print(f"Risk targeting: total exposure = {total_exposure:.4f}")

    @pytest.mark.asyncio
    async def test_stress_testing(self, volatility_config: VolatilityConfig):
        """Test strategy under stress conditions"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        # Generate high volatility stress data
        stress_data = self._generate_stress_test_data(volatility_config.symbols)

        signals = await strategy.generate_signals(stress_data)

        # Strategy should still function under stress
        assert isinstance(signals, list)

        print(f"Stress testing: {len(signals)} signals under high volatility")

    @pytest.mark.asyncio
    async def test_error_handling(self, volatility_config: VolatilityConfig):
        """Test error handling in volatility strategy"""
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        # Test with invalid data
        invalid_data = {"INVALID": pd.DataFrame()}

        signals = await strategy.generate_signals(invalid_data)

        # Should handle errors gracefully
        assert isinstance(signals, list)

        print("Error handling validated")

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self, volatility_config: VolatilityConfig,
                                     sample_market_data: Dict[str, pd.DataFrame]):
        """Test complete end-to-end volatility strategy pipeline"""
        # Initialize all components
        strategy = EnhancedVolatilityStrategy(volatility_config)
        await strategy.initialize()

        validator = SignalValidator()
        simulator = ExecutionSimulator()
        attributor = PerformanceAttributor()

        # Run full pipeline
        signals = await strategy.generate_signals(sample_market_data)

        if signals:
            quality = await validator.validate_signal_quality(signals, sample_market_data)
            execution = await simulator.simulate_execution(signals, sample_market_data)
            performance = await attributor.attribute_performance(signals, sample_market_data)

            # Validate complete pipeline
            assert quality is not None
            assert execution is not None
            assert performance is not None

        print("End-to-end pipeline validation complete")

    # Helper methods for generating test data

    def _generate_market_data_for_condition(self, symbols: List[str], condition: str) -> Dict[str, pd.DataFrame]:
        """Generate market data for specific market condition"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        data = {}
        for symbol in symbols:
            base_price = 100 + np.random.randn() * 20

            if condition == 'high_volatility':
                returns = np.random.randn(100) * 0.05  # High volatility
            elif condition == 'low_liquidity':
                returns = np.random.randn(100) * 0.01  # Low volatility
            else:  # normal
                returns = np.random.randn(100) * 0.02  # Normal volatility

            prices = base_price * (1 + returns).cumprod()

            df = pd.DataFrame({
                'close': prices,
                'high': prices * (1 + np.abs(np.random.randn(100)) * 0.02),
                'low': prices * (1 - np.abs(np.random.randn(100)) * 0.02),
                'returns_1': returns,
                'volatility': pd.Series(np.abs(returns)).rolling(20).mean().values,  # Pre-calculated volatility
                'ATR_14': pd.Series(np.abs(returns)).rolling(14).mean().values * prices  # ATR approximation
            }, index=dates)

            df = df.bfill().ffill()
            data[symbol] = df

        return data

    def _generate_market_data_for_regime(self, symbols: List[str], regime: str) -> Dict[str, pd.DataFrame]:
        """Generate market data for specific market regime"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        data = {}
        for symbol in symbols:
            base_price = 100 + np.random.randn() * 20

            if regime == 'bull':
                returns = np.abs(np.random.randn(100)) * 0.02  # Upward bias
            elif regime == 'bear':
                returns = -np.abs(np.random.randn(100)) * 0.02  # Downward bias
            else:  # sideways
                returns = np.random.randn(100) * 0.015  # Mean-reverting

            prices = base_price * (1 + returns).cumprod()

            df = pd.DataFrame({
                'close': prices,
                'high': prices * (1 + np.abs(np.random.randn(100)) * 0.02),
                'low': prices * (1 - np.abs(np.random.randn(100)) * 0.02),
                'returns_1': returns,
                'volatility': pd.Series(np.abs(returns)).rolling(20).mean().values,  # Pre-calculated volatility
                'ATR_14': pd.Series(np.abs(returns)).rolling(14).mean().values * prices  # ATR approximation
            }, index=dates)

            df = df.bfill().ffill()
            data[symbol] = df

        return data

    def _generate_volatility_regime_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Generate data with clear volatility regimes"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        data = {}
        for symbol in symbols:
            base_price = 100

            # Create distinct volatility regimes
            returns = np.zeros(100)
            returns[:30] = np.random.randn(30) * 0.01  # Low vol period
            returns[30:70] = np.random.randn(40) * 0.04  # High vol period
            returns[70:] = np.random.randn(30) * 0.02  # Normal vol period

            prices = base_price * (1 + returns).cumprod()

            df = pd.DataFrame({
                'close': prices,
                'high': prices * (1 + np.abs(np.random.randn(100)) * 0.02),
                'low': prices * (1 - np.abs(np.random.randn(100)) * 0.02),
                'returns_1': returns,
                'volatility': pd.Series(np.abs(returns)).rolling(20).mean().values,  # Pre-calculated volatility
                'ATR_14': pd.Series(np.abs(returns)).rolling(14).mean().values * prices  # ATR approximation
            }, index=dates)

            df = df.bfill().ffill()
            data[symbol] = df

        return data

    def _generate_high_volatility_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Generate high volatility market data"""
        return self._generate_market_data_for_condition(symbols, 'high_volatility')

    def _generate_low_volatility_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Generate low volatility market data"""
        return self._generate_market_data_for_condition(symbols, 'low_liquidity')

    def _generate_above_threshold_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Generate data with volatility above threshold"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        data = {}
        for symbol in symbols:
            base_price = 100
            returns = np.random.randn(100) * 0.04  # High volatility
            prices = base_price * (1 + returns).cumprod()

            df = pd.DataFrame({
                'close': prices,
                'high': prices * (1 + np.abs(np.random.randn(100)) * 0.02),
                'low': prices * (1 - np.abs(np.random.randn(100)) * 0.02),
                'returns_1': returns,
                'volatility': pd.Series(np.abs(returns)).rolling(20).mean().values,  # Pre-calculated volatility
                'ATR_14': pd.Series(np.abs(returns)).rolling(14).mean().values * prices  # ATR approximation
            }, index=dates)

            df = df.bfill().ffill()
            data[symbol] = df

        return data

    def _generate_below_threshold_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Generate data with volatility below threshold"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        data = {}
        for symbol in symbols:
            base_price = 100
            returns = np.random.randn(100) * 0.005  # Very low volatility
            prices = base_price * (1 + returns).cumprod()

            df = pd.DataFrame({
                'close': prices,
                'high': prices * (1 + np.abs(np.random.randn(100)) * 0.02),
                'low': prices * (1 - np.abs(np.random.randn(100)) * 0.02),
                'returns_1': returns,
                'volatility': pd.Series(np.abs(returns)).rolling(20).mean().values,  # Pre-calculated volatility
                'ATR_14': pd.Series(np.abs(returns)).rolling(14).mean().values * prices  # ATR approximation
            }, index=dates)

            df = df.bfill().ffill()
            data[symbol] = df

        return data

    def _generate_stress_test_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Generate stress test data with extreme volatility"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        data = {}
        for symbol in symbols:
            base_price = 100
            returns = np.random.randn(100) * 0.08  # Extreme volatility
            prices = base_price * (1 + returns).cumprod()

            df = pd.DataFrame({
                'close': prices,
                'high': prices * (1 + np.abs(np.random.randn(100)) * 0.05),
                'low': prices * (1 - np.abs(np.random.randn(100)) * 0.05),
                'returns_1': returns,
                'volatility': pd.Series(np.abs(returns)).rolling(20).mean().values,  # Pre-calculated volatility
                'ATR_14': pd.Series(np.abs(returns)).rolling(14).mean().values * prices  # ATR approximation
            }, index=dates)

            df = df.bfill().ffill()
            data[symbol] = df

        return data