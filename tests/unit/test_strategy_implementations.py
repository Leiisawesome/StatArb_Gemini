#!/usr/bin/env python3
"""
Trading Strategies Test Suite
=============================

Comprehensive test suite for all trading strategy implementations.
Tests cover strategy logic, signal generation, risk management, and performance.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, MagicMock
import asyncio
import warnings

from core_engine.trading.strategies.strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition,
    StrategyMetrics, StrategyState, StrategyType, SignalType, RiskLevel
)
from core_engine.trading.strategies.implementations.momentum.advanced_momentum import (
    AdvancedMomentumStrategy, MomentumConfig, MomentumType
)
from core_engine.trading.strategies.implementations.mean_reversion.advanced_mean_reversion import (
    AdvancedMeanReversionStrategy, MeanReversionConfig
)
from core_engine.trading.strategies.implementations.statistical_arbitrage.advanced_statistical_arbitrage import (
    AdvancedStatisticalArbitrageStrategy, StatisticalArbitrageConfig
)
from core_engine.trading.strategies.implementations.pairs_trading.advanced_pairs_trading import (
    AdvancedPairsTradingStrategy, PairsTradingConfig
)
from core_engine.trading.strategies.implementations.trend_following.advanced_trend_following import (
    AdvancedTrendFollowingStrategy, TrendFollowingConfig
)
from core_engine.trading.strategies.implementations.breakout.advanced_breakout import (
    AdvancedBreakoutStrategy, BreakoutConfig
)
from core_engine.trading.strategies.implementations.factor.advanced_factor import (
    AdvancedFactorStrategy, FactorConfig
)
from core_engine.trading.strategies.implementations.multi_asset.advanced_multi_asset import (
    AdvancedMultiAssetStrategy, MultiAssetConfig
)
from core_engine.trading.strategies.implementations.volatility.advanced_volatility import (
    AdvancedVolatilityStrategy, VolatilityStrategyConfig
)
from core_engine.trading.strategies.implementations.arbitrage.advanced_arbitrage import (
    AdvancedArbitrageStrategy, ArbitrageStrategyConfig
)

from core_engine.trading.strategies.strategy_manager import StrategyManager
from core_engine.trading.strategies.strategy_validator import StrategyValidator
from core_engine.trading.strategies.strategy_optimizer import StrategyOptimizer
from core_engine.trading.strategies.strategy_registry import StrategyRegistry


class TestBaseStrategy:
    """Test base strategy framework"""

    def test_strategy_config_initialization(self):
        """Test StrategyConfig initialization"""
        config = StrategyConfig(
            strategy_id="test_strategy",
            strategy_name="Test Strategy",
            strategy_type=StrategyType.MOMENTUM,
            required_symbols=["AAPL", "MSFT"],
            max_positions=5,
            risk_per_trade=0.02
        )

        assert config.strategy_id == "test_strategy"
        assert config.strategy_name == "Test Strategy"
        assert config.strategy_type == StrategyType.MOMENTUM
        assert config.required_symbols == ["AAPL", "MSFT"]
        assert config.max_positions == 5
        assert config.risk_per_trade == 0.02

    def test_strategy_signal_creation(self):
        """Test StrategySignal creation and properties"""
        signal = StrategySignal(
            signal_id="test_signal_001",
            strategy_id="test_strategy",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            confidence=0.85,
            strength=0.75,
            target_quantity=100.0,
            signal_price=150.0,
            stop_loss=140.0,
            take_profit=170.0
        )

        assert signal.signal_id == "test_signal_001"
        assert signal.strategy_id == "test_strategy"
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.confidence == 0.85
        assert signal.strength == 0.75
        assert signal.target_quantity == 100.0
        assert signal.signal_price == 150.0
        assert signal.stop_loss == 140.0
        assert signal.take_profit == 170.0

    def test_strategy_metrics_initialization(self):
        """Test StrategyMetrics initialization"""
        metrics = StrategyMetrics(
            total_signals=100,
            executed_signals=85,
            successful_signals=70,
            total_return=0.15,
            sharpe_ratio=1.8
        )

        assert metrics.total_signals == 100
        assert metrics.executed_signals == 85
        assert metrics.successful_signals == 70
        assert metrics.total_return == 0.15
        assert metrics.sharpe_ratio == 1.8
        assert metrics.signal_success_rate == 0.0  # Calculated property

    def test_base_strategy_initialization(self):
        """Test BaseStrategy initialization"""
        config = StrategyConfig(
            strategy_id="test_base",
            strategy_name="Test Base Strategy",
            required_symbols=["AAPL"]
        )

        # Mock the abstract methods for testing
        with patch.object(BaseStrategy, 'initialize', return_value=True):
            with patch.object(BaseStrategy, 'generate_signals', return_value=[]):
                with patch.object(BaseStrategy, 'update_positions'):
                    strategy = BaseStrategy(config)

                    assert strategy.config == config
                    assert strategy.strategy_id == "test_base"
                    assert strategy.state == StrategyState.INACTIVE
                    assert len(strategy._positions) == 0
                    assert len(strategy._signals) == 0

    def test_base_strategy_start_stop(self):
        """Test strategy start/stop lifecycle"""
        config = StrategyConfig(strategy_id="test_lifecycle")

        with patch.object(BaseStrategy, 'initialize', return_value=True):
            with patch.object(BaseStrategy, 'generate_signals', return_value=[]):
                with patch.object(BaseStrategy, 'update_positions'):
                    strategy = BaseStrategy(config)

                    # Test start
                    assert strategy.start()
                    assert strategy.state == StrategyState.ACTIVE
                    assert strategy._start_time is not None

                    # Test stop
                    strategy.stop()
                    assert strategy.state == StrategyState.STOPPED

    def test_base_strategy_error_handling(self):
        """Test strategy error handling"""
        config = StrategyConfig(strategy_id="test_error")

        with patch.object(BaseStrategy, 'initialize', side_effect=Exception("Init failed")):
            with patch.object(BaseStrategy, 'generate_signals', return_value=[]):
                with patch.object(BaseStrategy, 'update_positions'):
                    strategy = BaseStrategy(config)

                    # Start should fail
                    assert not strategy.start()
                    assert strategy.state == StrategyState.ERROR


class TestMomentumStrategy:
    """Test Advanced Momentum Strategy"""

    @pytest.fixture
    def sample_data(self):
        """Create sample market data for testing"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        # Generate realistic price data with trend
        base_price = 100
        trend = np.linspace(0, 20, 100)  # Upward trend
        noise = np.random.normal(0, 2, 100)
        prices = base_price + trend + noise

        # Generate volume data
        volume = np.random.uniform(1000000, 5000000, 100)

        df = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': volume,
            'returns': np.log(prices[1:] / prices[:-1]).tolist() + [0]
        }, index=dates)

        return {'AAPL': df}

    def test_momentum_config(self):
        """Test MomentumConfig initialization"""
        config = MomentumConfig(
            strategy_id="momentum_test",
            strategy_name="Test Momentum Strategy",
            lookback_periods=[1, 3, 6, 12],
            short_lookback=20,
            momentum_types=[MomentumType.TIME_SERIES, MomentumType.CROSS_SECTIONAL],
            min_momentum_score=0.02,
            max_position_size=0.10
        )

        assert config.strategy_id == "momentum_test"
        assert config.strategy_name == "Test Momentum Strategy"
        assert config.lookback_periods == [1, 3, 6, 12]
        assert config.short_lookback == 20
        assert MomentumType.TIME_SERIES in config.momentum_types
        assert config.min_momentum_score == 0.02
        assert config.max_position_size == 0.10

    def test_momentum_strategy_initialization(self, sample_data):
        """Test momentum strategy initialization"""
        config = StrategyConfig(
            strategy_id="momentum_test",
            strategy_name="Test Momentum Strategy",
            strategy_type=StrategyType.MOMENTUM,
            required_symbols=["AAPL"],
            strategy_parameters={
                'lookback_period': 20,
                'momentum_type': 'time_series',
                'volatility_adjusted': True
            }
        )

        strategy = AdvancedMomentumStrategy(config)
        assert strategy.config.strategy_id == "momentum_test"
        assert strategy.config.strategy_type == StrategyType.MOMENTUM

    def test_momentum_signal_generation(self, sample_data):
        """Test momentum signal generation"""
        config = StrategyConfig(
            strategy_id="momentum_signal_test",
            required_symbols=["AAPL"],
            strategy_parameters={
                'lookback_period': 20,
                'momentum_type': 'time_series',
                'min_momentum_threshold': 0.01
            }
        )

        strategy = AdvancedMomentumStrategy(config)

        # Initialize strategy
        assert strategy.initialize()

        # Generate signals
        signals = strategy.generate_signals(sample_data)

        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.symbol == "AAPL"
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
            assert 0.0 <= signal.confidence <= 1.0
            assert signal.strategy_id == "momentum_signal_test"

    def test_momentum_risk_management(self, sample_data):
        """Test momentum strategy risk management"""
        config = StrategyConfig(
            strategy_id="momentum_risk_test",
            required_symbols=["AAPL"],
            max_positions=3,
            risk_per_trade=0.02,
            strategy_parameters={
                'lookback_period': 20,
                'max_position_size': 0.1
            }
        )

        strategy = AdvancedMomentumStrategy(config)
        strategy.initialize()

        # Test position sizing
        signals = strategy.generate_signals(sample_data)

        for signal in signals:
            if signal.signal_type != SignalType.HOLD:
                # Check position size limits
                assert signal.target_quantity >= 0
                # Risk management should limit position sizes
                assert signal.confidence >= 0.5  # Minimum confidence threshold

    def test_momentum_performance_tracking(self, sample_data):
        """Test momentum strategy performance tracking"""
        config = StrategyConfig(
            strategy_id="momentum_perf_test",
            required_symbols=["AAPL"]
        )

        strategy = AdvancedMomentumStrategy(config)
        strategy.initialize()

        # Generate signals multiple times
        for _ in range(3):
            signals = strategy.generate_signals(sample_data)
            strategy._metrics.total_signals += len(signals)

        # Check metrics are updated
        assert strategy._metrics.total_signals > 0
        assert isinstance(strategy._metrics, StrategyMetrics)


class TestMeanReversionStrategy:
    """Test Advanced Mean Reversion Strategy"""

    @pytest.fixture
    def oscillating_data(self):
        """Create oscillating price data for mean reversion testing"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(123)

        # Generate mean-reverting price data
        base_price = 100
        # Create oscillating pattern around mean
        t = np.arange(100)
        oscillation = 5 * np.sin(2 * np.pi * t / 20)  # 20-day cycle
        noise = np.random.normal(0, 1, 100)
        prices = base_price + oscillation + noise

        df = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.uniform(1000000, 5000000, 100),
            'returns': np.log(prices[1:] / prices[:-1]).tolist() + [0]
        }, index=dates)

        return {'MSFT': df}

    def test_mean_reversion_config(self):
        """Test MeanReversionConfig initialization"""
        config = MeanReversionConfig(
            lookback_window=30,
            entry_threshold=2.0,
            exit_threshold=0.5,
            max_holding_period=10
        )

        assert config.lookback_window == 30
        assert config.entry_threshold == 2.0
        assert config.exit_threshold == 0.5
        assert config.max_holding_period == 10

    def test_mean_reversion_signal_generation(self, oscillating_data):
        """Test mean reversion signal generation"""
        config = StrategyConfig(
            strategy_id="mr_signal_test",
            required_symbols=["MSFT"],
            strategy_parameters={
                'lookback_window': 20,
                'entry_threshold': 1.5,
                'exit_threshold': 0.3
            }
        )

        strategy = AdvancedMeanReversionStrategy(config)
        strategy.initialize()

        signals = strategy.generate_signals(oscillating_data)

        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.symbol == "MSFT"
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]

    def test_mean_reversion_extreme_deviations(self, oscillating_data):
        """Test mean reversion with extreme price deviations"""
        # Modify data to create extreme deviations
        test_data = oscillating_data.copy()
        test_data['MSFT'].iloc[-5:] *= 1.1  # Create upward spike

        config = StrategyConfig(
            strategy_id="mr_extreme_test",
            required_symbols=["MSFT"],
            strategy_parameters={
                'lookback_window': 20,
                'entry_threshold': 1.0
            }
        )

        strategy = AdvancedMeanReversionStrategy(config)
        strategy.initialize()

        signals = strategy.generate_signals(test_data)

        # Should generate sell signals for overbought conditions
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        assert len(sell_signals) > 0


class TestStatisticalArbitrageStrategy:
    """Test Advanced Statistical Arbitrage Strategy"""

    @pytest.fixture
    def pairs_data(self):
        """Create correlated pairs data for statistical arbitrage"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(456)

        # Create correlated price series
        base_price = 100
        common_trend = np.cumsum(np.random.normal(0, 0.5, 100))
        noise1 = np.random.normal(0, 1, 100)
        noise2 = np.random.normal(0, 1, 100)

        prices1 = base_price + common_trend + noise1
        prices2 = base_price + common_trend * 0.8 + noise2  # Correlated but with spread

        df1 = pd.DataFrame({
            'close': prices1,
            'volume': np.random.uniform(1000000, 5000000, 100)
        }, index=dates)

        df2 = pd.DataFrame({
            'close': prices2,
            'volume': np.random.uniform(1000000, 5000000, 100)
        }, index=dates)

        return {'KO': df1, 'PEP': df2}  # Coca-Cola and Pepsi as correlated pair

    def test_statistical_arbitrage_config(self):
        """Test StatisticalArbitrageConfig initialization"""
        config = StatisticalArbitrageConfig(
            pairs=[('KO', 'PEP')],
            lookback_period=60,
            entry_zscore=2.0,
            exit_zscore=0.5,
            max_holding_period=20
        )

        assert ('KO', 'PEP') in config.pairs
        assert config.lookback_period == 60
        assert config.entry_zscore == 2.0
        assert config.exit_zscore == 0.5

    def test_statistical_arbitrage_signal_generation(self, pairs_data):
        """Test statistical arbitrage signal generation"""
        config = StrategyConfig(
            strategy_id="stat_arb_test",
            required_symbols=["KO", "PEP"],
            strategy_parameters={
                'pairs': [('KO', 'PEP')],
                'lookback_period': 30,
                'entry_zscore': 1.5,
                'exit_zscore': 0.5
            }
        )

        strategy = AdvancedStatisticalArbitrageStrategy(config)
        strategy.initialize()

        signals = strategy.generate_signals(pairs_data)

        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.symbol in ["KO", "PEP"]

    def test_statistical_arbitrage_spread_calculation(self, pairs_data):
        """Test spread calculation and z-score computation"""
        config = StrategyConfig(
            strategy_id="spread_test",
            required_symbols=["KO", "PEP"],
            strategy_parameters={
                'pairs': [('KO', 'PEP')],
                'lookback_period': 20
            }
        )

        strategy = AdvancedStatisticalArbitrageStrategy(config)
        strategy.initialize()

        # Test spread calculation
        spread_data = strategy._calculate_spread(pairs_data['KO']['close'], pairs_data['PEP']['close'])
        assert len(spread_data) > 0

        # Test z-score calculation
        zscore_data = strategy._calculate_zscore(spread_data)
        assert len(zscore_data) > 0
        assert not np.isnan(zscore_data.iloc[-1])  # Latest z-score should be valid


class TestPairsTradingStrategy:
    """Test Advanced Pairs Trading Strategy"""

    @pytest.fixture
    def pairs_trading_data(self):
        """Create pairs trading data with divergence"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(789)

        # Create cointegrated pair with temporary divergence
        base_price = 50
        common_trend = np.cumsum(np.random.normal(0, 0.3, 100))

        # Asset 1
        prices1 = base_price + common_trend + np.random.normal(0, 0.5, 100)

        # Asset 2 (cointegrated with Asset 1)
        prices2 = base_price + common_trend * 0.9 + np.random.normal(0, 0.5, 100)

        # Create divergence in the middle
        divergence_start = 40
        divergence_end = 60
        prices1[divergence_start:divergence_end] += np.linspace(0, 5, divergence_end - divergence_start)
        prices2[divergence_start:divergence_end] -= np.linspace(0, 3, divergence_end - divergence_start)

        df1 = pd.DataFrame({'close': prices1, 'volume': np.random.uniform(500000, 2000000, 100)}, index=dates)
        df2 = pd.DataFrame({'close': prices2, 'volume': np.random.uniform(500000, 2000000, 100)}, index=dates)

        return {'ASSET1': df1, 'ASSET2': df2}

    def test_pairs_trading_config(self):
        """Test PairsTradingConfig initialization"""
        config = PairsTradingConfig(
            pair=('ASSET1', 'ASSET2'),
            lookback_period=50,
            entry_threshold=2.5,
            exit_threshold=0.8,
            max_holding_period=15
        )

        assert config.pair == ('ASSET1', 'ASSET2')
        assert config.lookback_period == 50
        assert config.entry_threshold == 2.5

    def test_pairs_trading_cointegration_test(self, pairs_trading_data):
        """Test cointegration testing in pairs trading"""
        config = StrategyConfig(
            strategy_id="pairs_test",
            required_symbols=["ASSET1", "ASSET2"],
            strategy_parameters={
                'pair': ('ASSET1', 'ASSET2'),
                'lookback_period': 30
            }
        )

        strategy = AdvancedPairsTradingStrategy(config)
        strategy.initialize()

        # Test cointegration
        is_cointegrated, p_value = strategy._test_cointegration(
            pairs_trading_data['ASSET1']['close'],
            pairs_trading_data['ASSET2']['close']
        )

        assert isinstance(is_cointegrated, bool)
        assert isinstance(p_value, float)
        assert 0 <= p_value <= 1

    def test_pairs_trading_signal_generation(self, pairs_trading_data):
        """Test pairs trading signal generation"""
        config = StrategyConfig(
            strategy_id="pairs_signal_test",
            required_symbols=["ASSET1", "ASSET2"],
            strategy_parameters={
                'pair': ('ASSET1', 'ASSET2'),
                'lookback_period': 30,
                'entry_threshold': 1.5
            }
        )

        strategy = AdvancedPairsTradingStrategy(config)
        strategy.initialize()

        signals = strategy.generate_signals(pairs_trading_data)

        assert isinstance(signals, list)
        # Should generate signals for both assets in the pair
        asset1_signals = [s for s in signals if s.symbol == "ASSET1"]
        asset2_signals = [s for s in signals if s.symbol == "ASSET2"]

        # In a proper pairs trade, we should have signals for both assets
        # (long one, short the other, or close both)
        assert len(asset1_signals) > 0 or len(asset2_signals) > 0


class TestTrendFollowingStrategy:
    """Test Advanced Trend Following Strategy"""

    @pytest.fixture
    def trending_data(self):
        """Create trending price data"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(101)

        # Create strong upward trend with noise
        base_price = 50
        trend = np.linspace(0, 30, 100)  # Strong upward trend
        noise = np.random.normal(0, 1, 100)
        prices = base_price + trend + noise

        df = pd.DataFrame({
            'close': prices,
            'volume': np.random.uniform(1000000, 5000000, 100)
        }, index=dates)

        return {'TSLA': df}

    def test_trend_following_config(self):
        """Test TrendFollowingConfig initialization"""
        config = TrendFollowingConfig(
            fast_period=10,
            slow_period=30,
            trend_strength_threshold=0.7,
            confirmation_periods=3
        )

        assert config.fast_period == 10
        assert config.slow_period == 30
        assert config.trend_strength_threshold == 0.7

    def test_trend_following_signal_generation(self, trending_data):
        """Test trend following signal generation"""
        config = StrategyConfig(
            strategy_id="trend_test",
            required_symbols=["TSLA"],
            strategy_parameters={
                'fast_period': 10,
                'slow_period': 30,
                'trend_strength_threshold': 0.6
            }
        )

        strategy = AdvancedTrendFollowingStrategy(config)
        strategy.initialize()

        signals = strategy.generate_signals(trending_data)

        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.symbol == "TSLA"

    def test_trend_detection(self, trending_data):
        """Test trend detection logic"""
        config = StrategyConfig(
            strategy_id="trend_detect_test",
            required_symbols=["TSLA"],
            strategy_parameters={
                'fast_period': 10,
                'slow_period': 30
            }
        )

        strategy = AdvancedTrendFollowingStrategy(config)
        strategy.initialize()

        # Test trend strength calculation
        trend_strength = strategy._calculate_trend_strength(trending_data['TSLA']['close'])
        assert isinstance(trend_strength, float)
        assert 0 <= trend_strength <= 1

        # Test moving average crossover
        fast_ma, slow_ma = strategy._calculate_moving_averages(trending_data['TSLA']['close'])
        assert len(fast_ma) > 0
        assert len(slow_ma) > 0


class TestBreakoutStrategy:
    """Test Advanced Breakout Strategy"""

    @pytest.fixture
    def consolidation_data(self):
        """Create price data with consolidation followed by breakout"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(202)

        prices = np.zeros(100)

        # Phase 1: Consolidation (first 60 periods)
        consolidation_level = 100
        prices[:60] = consolidation_level + np.random.normal(0, 1, 60)

        # Phase 2: Breakout (last 40 periods)
        breakout_start = prices[59]
        breakout_trend = np.linspace(0, 15, 41)
        prices[60:] = breakout_start + breakout_trend[1:] + np.random.normal(0, 1.5, 40)

        df = pd.DataFrame({
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.uniform(500000, 2000000, 100)
        }, index=dates)

        return {'NVDA': df}

    def test_breakout_config(self):
        """Test BreakoutConfig initialization"""
        config = BreakoutConfig(
            lookback_period=20,
            breakout_threshold=2.5,
            volume_confirmation=True,
            min_breakout_volume=1.5
        )

        assert config.lookback_period == 20
        assert config.breakout_threshold == 2.5
        assert config.volume_confirmation == True

    def test_breakout_signal_generation(self, consolidation_data):
        """Test breakout signal generation"""
        config = StrategyConfig(
            strategy_id="breakout_test",
            required_symbols=["NVDA"],
            strategy_parameters={
                'lookback_period': 20,
                'breakout_threshold': 2.0,
                'volume_confirmation': True
            }
        )

        strategy = AdvancedBreakoutStrategy(config)
        strategy.initialize()

        signals = strategy.generate_signals(consolidation_data)

        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.symbol == "NVDA"

    def test_breakout_detection(self, consolidation_data):
        """Test breakout detection logic"""
        config = StrategyConfig(
            strategy_id="breakout_detect_test",
            required_symbols=["NVDA"],
            strategy_parameters={
                'lookback_period': 20,
                'breakout_threshold': 2.0
            }
        )

        strategy = AdvancedBreakoutStrategy(config)
        strategy.initialize()

        # Test resistance level calculation
        resistance = strategy._calculate_resistance_level(
            consolidation_data['NVDA']['high'],
            consolidation_data['NVDA']['low']
        )
        assert isinstance(resistance, float)

        # Test breakout confirmation
        is_breakout = strategy._confirm_breakout(
            consolidation_data['NVDA']['close'].iloc[-1],
            resistance,
            consolidation_data['NVDA']['volume'].iloc[-1]
        )
        assert isinstance(is_breakout, bool)


class TestFactorStrategy:
    """Test Advanced Factor Strategy"""

    @pytest.fixture
    def multi_asset_data(self):
        """Create multi-asset data for factor analysis"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(303)

        assets = {}
        for i, symbol in enumerate(['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']):
            # Create asset with different factor exposures
            base_price = 100 + i * 20
            market_factor = np.cumsum(np.random.normal(0, 0.5, 100))
            size_factor = np.cumsum(np.random.normal(0, 0.3, 100)) * (1 if i < 3 else -1)  # Size effect
            value_factor = np.cumsum(np.random.normal(0, 0.2, 100)) * (-1 if i % 2 == 0 else 1)  # Value effect

            prices = base_price + market_factor + size_factor + value_factor + np.random.normal(0, 1, 100)

            df = pd.DataFrame({
                'close': prices,
                'volume': np.random.uniform(1000000, 5000000, 100),
                'market_cap': base_price * 1000000,  # Mock market cap
                'pe_ratio': 15 + np.random.normal(0, 2),  # Mock P/E ratio
                'book_to_market': 0.5 + np.random.normal(0, 0.1)  # Mock B/M ratio
            }, index=dates)

            assets[symbol] = df

        return assets

    def test_factor_config(self):
        """Test FactorConfig initialization"""
        config = FactorConfig(
            factors=['momentum', 'value', 'quality', 'size'],
            lookback_period=60,
            min_factor_score=0.3,
            max_factor_weight=0.4
        )

        assert 'momentum' in config.factors
        assert config.lookback_period == 60
        assert config.min_factor_score == 0.3

    def test_factor_signal_generation(self, multi_asset_data):
        """Test factor-based signal generation"""
        config = StrategyConfig(
            strategy_id="factor_test",
            required_symbols=list(multi_asset_data.keys()),
            strategy_parameters={
                'factors': ['momentum', 'value'],
                'lookback_period': 30,
                'min_factor_score': 0.2
            }
        )

        strategy = AdvancedFactorStrategy(config)
        strategy.initialize()

        signals = strategy.generate_signals(multi_asset_data)

        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.symbol in multi_asset_data.keys()

    def test_factor_scoring(self, multi_asset_data):
        """Test factor scoring logic"""
        config = StrategyConfig(
            strategy_id="factor_score_test",
            required_symbols=list(multi_asset_data.keys()),
            strategy_parameters={
                'factors': ['momentum'],
                'lookback_period': 20
            }
        )

        strategy = AdvancedFactorStrategy(config)
        strategy.initialize()

        # Test momentum factor scoring
        momentum_scores = strategy._calculate_momentum_scores(multi_asset_data)
        assert isinstance(momentum_scores, dict)
        assert len(momentum_scores) == len(multi_asset_data)

        for symbol, score in momentum_scores.items():
            assert isinstance(score, float)
            assert -1 <= score <= 1  # Normalized score


class TestMultiAssetStrategy:
    """Test Advanced Multi-Asset Strategy"""

    @pytest.fixture
    def multi_asset_portfolio_data(self):
        """Create multi-asset portfolio data"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(404)

        assets = ['SPY', 'BND', 'GLD', 'VNQ']  # Equity, Bonds, Gold, Real Estate
        asset_data = {}

        for asset in assets:
            base_price = {'SPY': 400, 'BND': 80, 'GLD': 180, 'VNQ': 90}[asset]
            returns = np.random.normal(0, 0.02, 100)  # 2% daily volatility
            prices = base_price * np.exp(np.cumsum(returns))

            df = pd.DataFrame({
                'close': prices,
                'volume': np.random.uniform(1000000, 10000000, 100)
            }, index=dates)

            asset_data[asset] = df

        return asset_data

    def test_multi_asset_config(self):
        """Test MultiAssetConfig initialization"""
        config = MultiAssetConfig(
            asset_classes=['equity', 'fixed_income', 'commodity', 'real_estate'],
            target_allocations={'equity': 0.5, 'fixed_income': 0.3, 'commodity': 0.1, 'real_estate': 0.1},
            rebalance_threshold=0.05,
            max_allocation_shift=0.1
        )

        assert 'equity' in config.asset_classes
        assert config.target_allocations['equity'] == 0.5
        assert config.rebalance_threshold == 0.05

    def test_multi_asset_allocation(self, multi_asset_portfolio_data):
        """Test multi-asset allocation logic"""
        config = StrategyConfig(
            strategy_id="multi_asset_test",
            required_symbols=list(multi_asset_portfolio_data.keys()),
            strategy_parameters={
                'asset_classes': ['equity', 'fixed_income', 'commodity', 'real_estate'],
                'target_allocations': {'equity': 0.4, 'fixed_income': 0.3, 'commodity': 0.15, 'real_estate': 0.15}
            }
        )

        strategy = AdvancedMultiAssetStrategy(config)
        strategy.initialize()

        # Test asset class mapping
        asset_classes = strategy._map_assets_to_classes(multi_asset_portfolio_data.keys())
        assert isinstance(asset_classes, dict)
        assert len(asset_classes) == len(multi_asset_portfolio_data)

    def test_multi_asset_rebalancing_signals(self, multi_asset_portfolio_data):
        """Test rebalancing signal generation"""
        config = StrategyConfig(
            strategy_id="rebalance_test",
            required_symbols=list(multi_asset_portfolio_data.keys()),
            strategy_parameters={
                'target_allocations': {'SPY': 0.4, 'BND': 0.3, 'GLD': 0.15, 'VNQ': 0.15},
                'rebalance_threshold': 0.03
            }
        )

        strategy = AdvancedMultiAssetStrategy(config)
        strategy.initialize()

        signals = strategy.generate_signals(multi_asset_portfolio_data)

        assert isinstance(signals, list)
        # Rebalancing signals should be generated when allocations drift


class TestVolatilityStrategy:
    """Test Advanced Volatility Strategy"""

    @pytest.fixture
    def volatile_data(self):
        """Create volatile price data"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(505)

        # Create periods of high and low volatility
        base_price = 100
        prices = [base_price]

        for i in range(1, 100):
            # Alternate between high and low volatility periods
            if i < 30 or (i > 60 and i < 80):  # Low volatility periods
                volatility = 0.005
            else:  # High volatility periods
                volatility = 0.02

            return_val = np.random.normal(0, volatility)
            new_price = prices[-1] * (1 + return_val)
            prices.append(new_price)

        df = pd.DataFrame({
            'close': prices,
            'high': np.array(prices) * 1.01,
            'low': np.array(prices) * 0.99,
            'volume': np.random.uniform(1000000, 5000000, 100)
        }, index=dates)

        return {'VXX': df}  # Volatility ETF

    def test_volatility_config(self):
        """Test VolatilityStrategyConfig initialization"""
        config = VolatilityStrategyConfig(
            volatility_lookback=20,
            target_volatility=0.15,
            rebalance_frequency=5,
            max_leverage=2.0
        )

        assert config.volatility_lookback == 20
        assert config.target_volatility == 0.15
        assert config.max_leverage == 2.0

    def test_volatility_signal_generation(self, volatile_data):
        """Test volatility-based signal generation"""
        config = StrategyConfig(
            strategy_id="volatility_test",
            required_symbols=["VXX"],
            strategy_parameters={
                'volatility_lookback': 20,
                'target_volatility': 0.15
            }
        )

        strategy = AdvancedVolatilityStrategy(config)
        strategy.initialize()

        signals = strategy.generate_signals(volatile_data)

        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.symbol == "VXX"

    def test_volatility_calculation(self, volatile_data):
        """Test volatility calculation methods"""
        config = StrategyConfig(
            strategy_id="vol_calc_test",
            required_symbols=["VXX"],
            strategy_parameters={
                'volatility_lookback': 20
            }
        )

        strategy = AdvancedVolatilityStrategy(config)
        strategy.initialize()

        # Test realized volatility calculation
        volatility = strategy._calculate_realized_volatility(volatile_data['VXX']['close'])
        assert isinstance(volatility, float)
        assert volatility >= 0

        # Test implied volatility (if available)
        implied_vol = strategy._calculate_implied_volatility(volatile_data['VXX'])
        assert isinstance(implied_vol, (float, type(None)))


class TestArbitrageStrategy:
    """Test Advanced Arbitrage Strategy"""

    @pytest.fixture
    def arbitrage_data(self):
        """Create arbitrage opportunity data"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(606)

        # Create spot and futures prices with temporary mispricing
        spot_price = 100 + np.cumsum(np.random.normal(0, 0.5, 100))

        # Futures price usually tracks spot but with temporary arbitrage
        futures_price = spot_price.copy()

        # Create arbitrage opportunity (futures overpriced)
        arb_start = 50
        arb_end = 60
        futures_price[arb_start:arb_end] += np.linspace(0, 3, arb_end - arb_start)

        spot_df = pd.DataFrame({
            'close': spot_price,
            'volume': np.random.uniform(10000000, 50000000, 100)
        }, index=dates)

        futures_df = pd.DataFrame({
            'close': futures_price,
            'volume': np.random.uniform(1000000, 5000000, 100)
        }, index=dates)

        return {'SPOT': spot_df, 'FUTURES': futures_df}

    def test_arbitrage_config(self):
        """Test ArbitrageStrategyConfig initialization"""
        config = ArbitrageStrategyConfig(
            arbitrage_types=['cash_futures', 'statistical', ' triangular'],
            min_profit_threshold=0.005,
            max_holding_period=5,
            transaction_cost_estimate=0.001
        )

        assert 'cash_futures' in config.arbitrage_types
        assert config.min_profit_threshold == 0.005
        assert config.transaction_cost_estimate == 0.001

    def test_arbitrage_opportunity_detection(self, arbitrage_data):
        """Test arbitrage opportunity detection"""
        config = StrategyConfig(
            strategy_id="arbitrage_test",
            required_symbols=["SPOT", "FUTURES"],
            strategy_parameters={
                'arbitrage_types': ['cash_futures'],
                'min_profit_threshold': 0.003
            }
        )

        strategy = AdvancedArbitrageStrategy(config)
        strategy.initialize()

        signals = strategy.generate_signals(arbitrage_data)

        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.symbol in ["SPOT", "FUTURES"]

    def test_arbitrage_profit_calculation(self, arbitrage_data):
        """Test arbitrage profit calculation"""
        config = StrategyConfig(
            strategy_id="arb_profit_test",
            required_symbols=["SPOT", "FUTURES"],
            strategy_parameters={
                'arbitrage_types': ['cash_futures']
            }
        )

        strategy = AdvancedArbitrageStrategy(config)
        strategy.initialize()

        # Test profit calculation for cash-futures arbitrage
        profit = strategy._calculate_cash_futures_profit(
            arbitrage_data['SPOT']['close'].iloc[-1],
            arbitrage_data['FUTURES']['close'].iloc[-1],
            time_to_expiry=30  # 30 days
        )

        assert isinstance(profit, float)


class TestStrategyManager:
    """Test Strategy Manager functionality"""

    def test_strategy_manager_initialization(self):
        """Test StrategyManager initialization"""
        manager = StrategyManager()
        assert manager is not None
        assert len(manager._strategies) == 0

    def test_strategy_registration(self):
        """Test strategy registration"""
        manager = StrategyManager()

        config = StrategyConfig(
            strategy_id="test_strategy",
            strategy_name="Test Strategy",
            strategy_type=StrategyType.MOMENTUM
        )

        # Mock strategy class
        mock_strategy_class = Mock()
        mock_strategy_instance = Mock()
        mock_strategy_class.return_value = mock_strategy_instance
        mock_strategy_instance.config = config

        manager.register_strategy("test_strategy", mock_strategy_class)

        assert "test_strategy" in manager._strategy_classes

    def test_strategy_deployment(self):
        """Test strategy deployment"""
        manager = StrategyManager()

        config = StrategyConfig(
            strategy_id="deploy_test",
            strategy_name="Deploy Test Strategy"
        )

        # Mock strategy
        mock_strategy = Mock()
        mock_strategy.config = config
        mock_strategy.state = StrategyState.INACTIVE

        with patch.object(manager, '_create_strategy_instance', return_value=mock_strategy):
            with patch.object(manager, '_validate_strategy_config', return_value=True):
                success = manager.deploy_strategy("deploy_test", config)

                assert success
                assert "deploy_test" in manager._strategies

    def test_strategy_lifecycle_management(self):
        """Test strategy start/stop/status management"""
        manager = StrategyManager()

        config = StrategyConfig(strategy_id="lifecycle_test")

        mock_strategy = Mock()
        mock_strategy.config = config
        mock_strategy.state = StrategyState.INACTIVE
        mock_strategy.start.return_value = True
        mock_strategy.stop.return_value = None

        manager._strategies["lifecycle_test"] = mock_strategy

        # Test start
        success = manager.start_strategy("lifecycle_test")
        assert success
        mock_strategy.start.assert_called_once()

        # Test stop
        manager.stop_strategy("lifecycle_test")
        mock_strategy.stop.assert_called_once()

        # Test status
        status = manager.get_strategy_status("lifecycle_test")
        assert status is not None


class TestStrategyValidation:
    """Test Strategy Validation functionality"""

    def test_strategy_validator_initialization(self):
        """Test StrategyValidator initialization"""
        from core_engine.trading.strategies.strategy_validator import StrategyValidator

        validator = StrategyValidator()
        assert validator is not None

    def test_config_validation(self):
        """Test strategy configuration validation"""
        from core_engine.trading.strategies.strategy_validator import StrategyValidator

        validator = StrategyValidator()

        # Valid config
        valid_config = StrategyConfig(
            strategy_id="valid_test",
            strategy_name="Valid Test",
            required_symbols=["AAPL"],
            max_positions=5
        )

        is_valid, errors = validator.validate_config(valid_config)
        assert is_valid
        assert len(errors) == 0

        # Invalid config
        invalid_config = StrategyConfig(
            strategy_id="",  # Empty ID
            required_symbols=[]  # No symbols
        )

        is_valid, errors = validator.validate_config(invalid_config)
        assert not is_valid
        assert len(errors) > 0

    def test_risk_validation(self):
        """Test strategy risk validation"""
        from core_engine.trading.strategies.strategy_validator import StrategyValidator

        validator = StrategyValidator()

        config = StrategyConfig(
            strategy_id="risk_test",
            max_daily_loss=0.05,
            risk_per_trade=0.02
        )

        # Mock strategy with metrics
        mock_strategy = Mock()
        mock_strategy.config = config
        mock_strategy._metrics.total_return = -0.03  # Within limits

        is_valid, warnings = validator.validate_risk_limits(mock_strategy)
        assert is_valid  # Should pass risk validation


class TestStrategyOptimization:
    """Test Strategy Optimization functionality"""

    def test_strategy_optimizer_initialization(self):
        """Test StrategyOptimizer initialization"""
        from core_engine.trading.strategies.strategy_optimizer import StrategyOptimizer

        optimizer = StrategyOptimizer()
        assert optimizer is not None

    def test_parameter_optimization(self):
        """Test parameter optimization"""
        from core_engine.trading.strategies.strategy_optimizer import StrategyOptimizer

        optimizer = StrategyOptimizer()

        # Mock objective function
        def mock_objective(params):
            # Simple quadratic function: (x-2)^2 + (y-3)^2
            return (params[0] - 2)**2 + (params[1] - 3)**2

        bounds = [(0, 5), (0, 5)]
        result = optimizer.optimize_parameters(mock_objective, bounds, method='grid')

        assert result is not None
        assert 'best_params' in result
        assert 'best_score' in result

        # Optimal point should be close to (2, 3)
        best_params = result['best_params']
        assert abs(best_params[0] - 2) < 0.5
        assert abs(best_params[1] - 3) < 0.5


class TestStrategyRegistry:
    """Test Strategy Registry functionality"""

    def test_strategy_registry_initialization(self):
        """Test StrategyRegistry initialization"""
        from core_engine.trading.strategies.strategy_registry import StrategyRegistry

        registry = StrategyRegistry()
        assert registry is not None
        assert len(registry._strategies) == 0

    def test_strategy_registration(self):
        """Test strategy registration in registry"""
        from core_engine.trading.strategies.strategy_registry import StrategyRegistry

        registry = StrategyRegistry()

        metadata = {
            'name': 'Test Momentum Strategy',
            'type': StrategyType.MOMENTUM,
            'description': 'Test strategy for momentum trading',
            'author': 'Test Author',
            'version': '1.0.0'
        }

        registry.register_strategy('momentum_test', Mock, metadata)

        assert 'momentum_test' in registry._strategies
        assert registry._strategies['momentum_test']['name'] == 'Test Momentum Strategy'

    def test_strategy_discovery(self):
        """Test strategy discovery"""
        from core_engine.trading.strategies.strategy_registry import StrategyRegistry

        registry = StrategyRegistry()

        # Register strategies
        registry.register_strategy('momentum_v1', Mock, {'type': StrategyType.MOMENTUM})
        registry.register_strategy('mean_reversion_v1', Mock, {'type': StrategyType.MEAN_REVERSION})

        # Discover by type
        momentum_strategies = registry.discover_strategies(strategy_type=StrategyType.MOMENTUM)
        assert len(momentum_strategies) == 1
        assert 'momentum_v1' in momentum_strategies

        # Discover all
        all_strategies = registry.discover_strategies()
        assert len(all_strategies) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])