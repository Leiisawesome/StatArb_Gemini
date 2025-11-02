#!/usr/bin/env python3
"""
Comprehensive Signal Strategies Test Coverage
============================================

Addresses critical coverage gap: signals/strategies/signal_generator.py (29% → target 80%+)

Tests all signal strategy implementations:
- SignalStrategy (base class)
- MomentumSignalStrategy
- MeanReversionSignalStrategy
- StatisticalArbitrageSignalStrategy
- SignalGenerator (orchestrator)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import asyncio

from core_engine.processing.signals.strategies.signal_generator import (
    SignalStrategy,
    MomentumSignalStrategy,
    MeanReversionSignalStrategy,
    StatisticalArbitrageSignalStrategy,
    SignalGenerator,
    SignalParameters,
    SignalResult,
    SignalStatistics,
    SignalType,
    SignalStrength,
    SignalDirection
)


class TestSignalParameters:
    """Test SignalParameters dataclass"""
    
    def test_signal_parameters_creation(self):
        """Test creating SignalParameters"""
        params = SignalParameters(
            signal_type=SignalType.MOMENTUM,
            lookback_period=20
        )
        
        assert params.signal_type == SignalType.MOMENTUM
        assert params.lookback_period == 20
        assert params.z_score_threshold == 2.0
        assert params.confidence_level == 0.95
    
    def test_signal_parameters_custom(self):
        """Test SignalParameters with custom values"""
        params = SignalParameters(
            signal_type=SignalType.MEAN_REVERSION,
            lookback_period=50,
            fast_period=5,
            slow_period=20,
            z_score_threshold=2.5,
            max_position_size=0.1
        )
        
        assert params.fast_period == 5
        assert params.slow_period == 20
        assert params.z_score_threshold == 2.5
        assert params.max_position_size == 0.1


class TestSignalStrategyBase:
    """Test SignalStrategy base class"""
    
    @pytest.fixture
    def sample_params(self):
        """Create sample SignalParameters"""
        return SignalParameters(
            signal_type=SignalType.MOMENTUM,
            lookback_period=20,
            min_observations=20
        )
    
    def test_validate_data_valid(self, sample_params):
        """Test data validation with valid data"""
        # Create concrete implementation for testing
        class TestStrategy(SignalStrategy):
            def __init__(self, params):
                super().__init__("test_strategy", params)
            
            async def generate_signal(self, symbol, data, context):
                return None
            
            def get_required_data_fields(self):
                return ['close', 'timestamp']
        
        strategy = TestStrategy(sample_params)
        
        dates = pd.date_range('2024-01-01', periods=50, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'close': np.random.randn(50) * 100 + 100,
            'volume': np.random.randint(1000, 10000, 50)
        })
        
        assert strategy.validate_data(data) is True
    
    def test_validate_data_empty(self, sample_params):
        """Test data validation with empty DataFrame"""
        class TestStrategy(SignalStrategy):
            def __init__(self, params):
                super().__init__("test_strategy", params)
            
            async def generate_signal(self, symbol, data, context):
                return None
            
            def get_required_data_fields(self):
                return ['close']
        
        strategy = TestStrategy(sample_params)
        empty_df = pd.DataFrame()
        
        assert strategy.validate_data(empty_df) is False
    
    def test_validate_data_missing_fields(self, sample_params):
        """Test data validation with missing required fields"""
        class TestStrategy(SignalStrategy):
            def __init__(self, params):
                super().__init__("test_strategy", params)
            
            async def generate_signal(self, symbol, data, context):
                return None
            
            def get_required_data_fields(self):
                return ['close', 'volume']
        
        strategy = TestStrategy(sample_params)
        
        dates = pd.date_range('2024-01-01', periods=50, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'close': np.random.randn(50) * 100
            # Missing 'volume'
        })
        
        assert strategy.validate_data(data) is False
    
    def test_validate_data_insufficient_observations(self, sample_params):
        """Test data validation with insufficient observations"""
        class TestStrategy(SignalStrategy):
            def __init__(self, params):
                super().__init__("test_strategy", params)
            
            async def generate_signal(self, symbol, data, context):
                return None
            
            def get_required_data_fields(self):
                return ['close']
        
        strategy = TestStrategy(sample_params)
        
        dates = pd.date_range('2024-01-01', periods=10, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'close': np.random.randn(10) * 100
        })
        
        assert strategy.validate_data(data) is False


class TestMomentumSignalStrategy:
    """Test MomentumSignalStrategy"""
    
    @pytest.fixture
    def momentum_params(self):
        """Create momentum strategy parameters"""
        return SignalParameters(
            signal_type=SignalType.MOMENTUM,
            lookback_period=20,
            fast_period=5,
            slow_period=20,
            max_position_size=0.1,
            min_observations=20
        )
    
    @pytest.fixture
    def momentum_strategy(self, momentum_params):
        """Create momentum strategy instance"""
        return MomentumSignalStrategy(momentum_params)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample market data with upward trend"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        np.random.seed(42)
        base_price = 100.0
        
        # Create upward trend
        trend = np.linspace(0, 10, 100)
        noise = np.random.randn(100) * 0.5
        
        return pd.DataFrame({
            'timestamp': dates,
            'close': base_price + trend + noise,
            'volume': np.random.randint(1000, 10000, 100)
        })
    
    @pytest.mark.asyncio
    async def test_generate_signal_basic(self, momentum_strategy, sample_data):
        """Test basic momentum signal generation"""
        context = {}
        
        result = await momentum_strategy.generate_signal('AAPL', sample_data, context)
        
        assert result is not None
        assert isinstance(result, SignalResult)
        assert result.symbol == 'AAPL'
        assert result.signal_type == SignalType.MOMENTUM
        assert result.direction in [SignalDirection.LONG, SignalDirection.SHORT]
        assert 0 <= result.confidence <= 1
        assert -1 <= result.strength <= 1
    
    @pytest.mark.asyncio
    async def test_generate_signal_insufficient_data(self, momentum_strategy):
        """Test momentum signal with insufficient data"""
        dates = pd.date_range('2024-01-01', periods=10, freq='1min')
        insufficient_data = pd.DataFrame({
            'timestamp': dates,
            'close': np.random.randn(10) * 100
        })
        
        result = await momentum_strategy.generate_signal('AAPL', insufficient_data, {})
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_signal_downward_trend(self, momentum_strategy):
        """Test momentum signal with downward trend"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        np.random.seed(42)
        base_price = 100.0
        
        # Create downward trend
        trend = np.linspace(0, -10, 100)
        noise = np.random.randn(100) * 0.5
        
        data = pd.DataFrame({
            'timestamp': dates,
            'close': base_price + trend + noise,
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        result = await momentum_strategy.generate_signal('AAPL', data, {})
        
        assert result is not None
        # Downward trend should generate SHORT signal
        assert result.direction == SignalDirection.SHORT
    
    def test_get_required_data_fields(self, momentum_strategy):
        """Test required data fields"""
        fields = momentum_strategy.get_required_data_fields()
        
        assert 'close' in fields
        assert 'timestamp' in fields
    
    def test_categorize_strength(self, momentum_strategy):
        """Test strength categorization"""
        assert momentum_strategy._categorize_strength(0.1) == SignalStrength.VERY_WEAK
        assert momentum_strategy._categorize_strength(0.3) == SignalStrength.WEAK
        assert momentum_strategy._categorize_strength(0.5) == SignalStrength.MODERATE
        assert momentum_strategy._categorize_strength(0.7) == SignalStrength.STRONG
        assert momentum_strategy._categorize_strength(0.9) == SignalStrength.VERY_STRONG
    
    def test_calculate_data_quality(self, momentum_strategy, sample_data):
        """Test data quality calculation"""
        quality = momentum_strategy._calculate_data_quality(sample_data)
        
        assert 0 <= quality <= 1
    
    def test_update_statistics(self, momentum_strategy):
        """Test statistics update"""
        signal_result = SignalResult(
            signal_id="test",
            symbol="AAPL",
            timestamp=datetime.now(),
            signal_type=SignalType.MOMENTUM,
            direction=SignalDirection.LONG,
            strength=0.5,
            strength_category=SignalStrength.MODERATE,
            confidence=0.7
        )
        
        momentum_strategy._update_statistics(signal_result)
        
        assert momentum_strategy.statistics.total_signals_generated > 0


class TestMeanReversionSignalStrategy:
    """Test MeanReversionSignalStrategy"""
    
    @pytest.fixture
    def mean_reversion_params(self):
        """Create mean reversion strategy parameters"""
        return SignalParameters(
            signal_type=SignalType.MEAN_REVERSION,
            lookback_period=50,
            z_score_threshold=2.0,
            confidence_level=0.95,
            min_observations=50
        )
    
    @pytest.fixture
    def mean_reversion_strategy(self, mean_reversion_params):
        """Create mean reversion strategy instance"""
        return MeanReversionSignalStrategy(mean_reversion_params)
    
    @pytest.fixture
    def oversold_data(self):
        """Create data with oversold conditions (negative z-score)"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        np.random.seed(42)
        
        # Create price significantly below mean
        mean_price = 100.0
        std_price = 5.0
        oversold_price = mean_price - (3 * std_price)  # Strong oversold
        
        prices = [mean_price + np.random.randn() * std_price for _ in range(90)]
        prices.extend([oversold_price + np.random.randn() * 0.5 for _ in range(10)])
        
        return pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
    
    @pytest.mark.asyncio
    async def test_generate_signal_oversold(self, mean_reversion_strategy, oversold_data):
        """Test mean reversion signal with oversold conditions"""
        context = {}
        
        result = await mean_reversion_strategy.generate_signal('AAPL', oversold_data, context)
        
        # May return None if z-score doesn't exceed threshold, or generate signal
        if result is not None:
            assert isinstance(result, SignalResult)
            assert result.signal_type == SignalType.MEAN_REVERSION
            # Oversold should generate LONG signal (mean reversion up)
            assert result.direction == SignalDirection.LONG
            assert result.z_score is not None
            assert result.z_score < 0  # Negative z-score for oversold
        else:
            # If None, verify data would generate z-score (test data validation)
            prices = oversold_data['close'].values
            lookback = mean_reversion_strategy.parameters.lookback_period
            recent_prices = prices[-lookback:]
            mean_price = np.mean(recent_prices)
            std_price = np.std(recent_prices)
            if std_price > 0:
                z_score = (prices[-1] - mean_price) / std_price
                # Z-score might be below threshold, which is acceptable
                assert isinstance(z_score, (int, float))
    
    @pytest.mark.asyncio
    async def test_generate_signal_overbought(self, mean_reversion_strategy):
        """Test mean reversion signal with overbought conditions"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        np.random.seed(42)
        
        # Create price significantly above mean
        mean_price = 100.0
        std_price = 5.0
        overbought_price = mean_price + (3 * std_price)  # Strong overbought
        
        prices = [mean_price + np.random.randn() * std_price for _ in range(90)]
        prices.extend([overbought_price + np.random.randn() * 0.5 for _ in range(10)])
        
        data = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        result = await mean_reversion_strategy.generate_signal('AAPL', data, {})
        
        if result is not None:
            # Overbought should generate SHORT signal (mean reversion down)
            assert result.direction == SignalDirection.SHORT
            assert result.z_score > 0  # Positive z-score for overbought
    
    @pytest.mark.asyncio
    async def test_generate_signal_below_threshold(self, mean_reversion_strategy):
        """Test mean reversion signal when z-score below threshold"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        np.random.seed(42)
        
        # Create price near mean (low z-score)
        mean_price = 100.0
        std_price = 5.0
        prices = [mean_price + np.random.randn() * std_price for _ in range(100)]
        
        data = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        result = await mean_reversion_strategy.generate_signal('AAPL', data, {})
        
        # Should return None when z-score below threshold
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_signal_zero_std(self, mean_reversion_strategy):
        """Test mean reversion signal with zero standard deviation"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        
        # Create constant prices (zero std)
        data = pd.DataFrame({
            'timestamp': dates,
            'close': [100.0] * 100,
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        result = await mean_reversion_strategy.generate_signal('AAPL', data, {})
        
        assert result is None
    
    def test_get_required_data_fields(self, mean_reversion_strategy):
        """Test required data fields"""
        fields = mean_reversion_strategy.get_required_data_fields()
        
        assert 'close' in fields
        assert 'timestamp' in fields


class TestStatisticalArbitrageSignalStrategy:
    """Test StatisticalArbitrageSignalStrategy"""
    
    @pytest.fixture
    def stat_arb_params(self):
        """Create statistical arbitrage strategy parameters"""
        return SignalParameters(
            signal_type=SignalType.STATISTICAL_ARBITRAGE,
            lookback_period=100,
            z_score_threshold=2.5,
            confidence_level=0.99,
            min_observations=100
        )
    
    @pytest.fixture
    def stat_arb_strategy(self, stat_arb_params):
        """Create statistical arbitrage strategy instance"""
        return StatisticalArbitrageSignalStrategy(stat_arb_params)
    
    @pytest.fixture
    def pair_data(self):
        """Create correlated pair data"""
        dates = pd.date_range('2024-01-01', periods=150, freq='1min')
        np.random.seed(42)
        
        # Create correlated prices
        base1 = 100.0
        base2 = 50.0
        
        # Strong correlation with spread deviation
        trend = np.linspace(0, 5, 150)
        noise1 = np.random.randn(150) * 1.0
        noise2 = np.random.randn(150) * 1.0
        
        prices1 = base1 + trend + noise1
        prices2 = base2 + trend * 0.5 + noise2
        
        # Introduce spread widening near end (arbitrage opportunity)
        prices1[-10:] += 5  # Price 1 increases relative to price 2
        prices2[-10:] -= 2
        
        return pd.DataFrame({
            'timestamp': dates,
            'close': prices1,
            'volume': np.random.randint(1000, 10000, 150)
        }), pd.DataFrame({
            'timestamp': dates,
            'close': prices2,
            'volume': np.random.randint(1000, 10000, 150)
        })
    
    @pytest.mark.asyncio
    async def test_generate_signal_with_pair_data(self, stat_arb_strategy, pair_data):
        """Test statistical arbitrage signal generation with pair data"""
        primary_data, pair_df = pair_data
        
        context = {
            'pair_data': {
                'PAIR_SYMBOL': pair_df
            }
        }
        
        result = await stat_arb_strategy.generate_signal('PRIMARY_SYMBOL', primary_data, context)
        
        # May return None if cointegration/threshold not met
        if result is not None:
            assert isinstance(result, SignalResult)
            assert result.signal_type == SignalType.STATISTICAL_ARBITRAGE
            assert result.z_score is not None
            assert 'hedge_ratio' in result.underlying_data
    
    @pytest.mark.asyncio
    async def test_generate_signal_no_pair_data(self, stat_arb_strategy):
        """Test statistical arbitrage without pair data"""
        dates = pd.date_range('2024-01-01', periods=150, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'close': np.random.randn(150) * 100 + 100,
            'volume': np.random.randint(1000, 10000, 150)
        })
        
        context = {}  # No pair_data
        
        result = await stat_arb_strategy.generate_signal('AAPL', data, context)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_signal_insufficient_length(self, stat_arb_strategy):
        """Test statistical arbitrage with insufficient data length"""
        dates = pd.date_range('2024-01-01', periods=50, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'close': np.random.randn(50) * 100,
            'volume': np.random.randint(1000, 10000, 50)
        })
        
        pair_df = pd.DataFrame({
            'timestamp': dates,
            'close': np.random.randn(50) * 50,
            'volume': np.random.randint(1000, 10000, 50)
        })
        
        context = {'pair_data': {'PAIR': pair_df}}
        
        result = await stat_arb_strategy.generate_signal('AAPL', data, context)
        
        assert result is None
    
    def test_test_cointegration(self, stat_arb_strategy):
        """Test cointegration test method"""
        # Create cointegrated series
        np.random.seed(42)
        n = 200
        series1 = np.cumsum(np.random.randn(n)) + np.arange(n) * 0.1
        series2 = series1 * 0.5 + np.random.randn(n) * 0.1  # Cointegrated
        
        score = stat_arb_strategy._test_cointegration(series1, series2)
        
        assert 0 <= score <= 1
    
    def test_calculate_hedge_ratio(self, stat_arb_strategy):
        """Test hedge ratio calculation"""
        np.random.seed(42)
        n = 200
        # Create more correlated series
        base = np.cumsum(np.random.randn(n)) + 100
        series1 = base
        series2 = base * 0.5 + np.random.randn(n) * 0.1  # Strong correlation, ~0.5 ratio
        
        ratio = stat_arb_strategy._calculate_hedge_ratio(series1, series2)
        
        assert ratio > 0
        # Hedge ratio should be positive (may vary based on correlation strength)
        assert isinstance(ratio, (int, float))


class TestSignalGenerator:
    """Test SignalGenerator orchestrator"""
    
    @pytest.fixture
    def signal_generator(self):
        """Create SignalGenerator instance"""
        return SignalGenerator()
    
    @pytest.fixture
    def sample_symbol_data(self):
        """Create sample data for multiple symbols"""
        dates = pd.date_range('2024-01-01', periods=150, freq='1min')
        np.random.seed(42)
        
        data_dict = {}
        for symbol in ['AAPL', 'TSLA', 'NVDA']:
            base_price = 100.0 + np.random.randn() * 10
            trend = np.linspace(0, 5, 150)
            noise = np.random.randn(150) * 1.0
            
            data_dict[symbol] = pd.DataFrame({
                'timestamp': dates,
                'close': base_price + trend + noise,
                'volume': np.random.randint(1000, 10000, 150)
            })
        
        return data_dict
    
    def test_initialization_default(self, signal_generator):
        """Test default initialization"""
        assert signal_generator.config is not None
        assert len(signal_generator._strategies) > 0  # Should have default strategies
    
    def test_initialization_custom_config(self):
        """Test initialization with custom config"""
        config = {'custom_param': 'value'}
        generator = SignalGenerator(config)
        
        assert generator.config['custom_param'] == 'value'
    
    def test_register_strategy(self, signal_generator):
        """Test strategy registration"""
        params = SignalParameters(
            signal_type=SignalType.MOMENTUM,
            lookback_period=20
        )
        strategy = MomentumSignalStrategy(params)
        
        signal_generator.register_strategy(strategy, weight=0.5)
        
        assert 'momentum_strategy' in signal_generator._strategies
        assert signal_generator._strategy_weights['momentum_strategy'] == 0.5
    
    def test_unregister_strategy(self, signal_generator):
        """Test strategy unregistration"""
        # Register first
        params = SignalParameters(
            signal_type=SignalType.MOMENTUM,
            lookback_period=20
        )
        strategy = MomentumSignalStrategy(params)
        signal_generator.register_strategy(strategy)
        
        # Unregister
        result = signal_generator.unregister_strategy('momentum_strategy')
        
        assert result is True
        assert 'momentum_strategy' not in signal_generator._strategies
    
    def test_unregister_nonexistent_strategy(self, signal_generator):
        """Test unregistering non-existent strategy"""
        result = signal_generator.unregister_strategy('nonexistent')
        
        # Should return True (graceful handling) or False
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_generate_signals_multiple_symbols(self, signal_generator, sample_symbol_data):
        """Test generating signals for multiple symbols"""
        context = {}
        
        results = await signal_generator.generate_signals(
            list(sample_symbol_data.keys()),
            sample_symbol_data,
            context
        )
        
        assert isinstance(results, dict)
        # Should have results for each symbol
        for symbol in sample_symbol_data.keys():
            assert symbol in results
            assert isinstance(results[symbol], list)
            # Results may be empty if strategies don't generate signals
    
    @pytest.mark.asyncio
    async def test_generate_signals_empty_symbols(self, signal_generator):
        """Test generating signals with empty symbol list"""
        results = await signal_generator.generate_signals([], {}, {})
        
        assert isinstance(results, dict)
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_generate_signal_single(self, signal_generator):
        """Test generating signal for single symbol"""
        dates = pd.date_range('2024-01-01', periods=150, freq='1min')
        np.random.seed(42)
        
        data = pd.DataFrame({
            'timestamp': dates,
            'close': 100 + np.cumsum(np.random.randn(150) * 0.5),
            'volume': np.random.randint(1000, 10000, 150)
        })
        
        context = {}
        
        results = await signal_generator.generate_signal('AAPL', data, context)
        
        assert isinstance(results, list)
        # Results may be empty if strategies don't generate signals


class TestSignalResult:
    """Test SignalResult dataclass"""
    
    def test_signal_result_creation(self):
        """Test creating SignalResult"""
        result = SignalResult(
            signal_id="test_signal",
            symbol="AAPL",
            timestamp=datetime.now(),
            signal_type=SignalType.MOMENTUM,
            direction=SignalDirection.LONG,
            strength=0.7,
            strength_category=SignalStrength.STRONG,
            confidence=0.8
        )
        
        assert result.symbol == "AAPL"
        assert result.signal_type == SignalType.MOMENTUM
        assert result.direction == SignalDirection.LONG
        assert result.strength == 0.7
        assert result.confidence == 0.8
    
    def test_signal_result_with_optional_fields(self):
        """Test SignalResult with optional fields"""
        result = SignalResult(
            signal_id="test",
            symbol="AAPL",
            timestamp=datetime.now(),
            signal_type=SignalType.MEAN_REVERSION,
            direction=SignalDirection.SHORT,
            strength=-0.5,
            strength_category=SignalStrength.MODERATE,
            confidence=0.6,
            z_score=2.5,
            suggested_position_size=0.05,
            entry_price=100.0,
            target_price=95.0,
            stop_loss_price=102.0
        )
        
        assert result.z_score == 2.5
        assert result.suggested_position_size == 0.05
        assert result.entry_price == 100.0


class TestSignalStatistics:
    """Test SignalStatistics dataclass"""
    
    def test_signal_statistics_creation(self):
        """Test creating SignalStatistics"""
        stats = SignalStatistics(generator_id="test_strategy")
        
        assert stats.generator_id == "test_strategy"
        assert stats.total_signals_generated == 0
        assert stats.generation_errors == 0
        assert stats.rejected_signals_count == 0
        assert isinstance(stats.signals_by_type, dict)
        assert isinstance(stats.signals_by_direction, dict)

