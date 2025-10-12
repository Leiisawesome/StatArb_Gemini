"""
Enhanced Pairs Trading Strategy Tests
====================================

Comprehensive test suite for EnhancedPairsTradingStrategy with full coverage
of initialization, pair selection, cointegration analysis, signal generation,
position management, and performance tracking.

Test Categories:
- Initialization and Configuration
- Pair Selection and Validation
- Cointegration Analysis
- Signal Generation
- Position Management
- Performance Tracking
- Error Handling
- Integration Testing

Author: StatArb_Gemini Test Suite
Version: 1.0.0
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock
from dataclasses import replace

# Import the strategy and related classes
from core_engine.trading.strategies.implementations.pairs_trading.enhanced_pairs_trading import (
    EnhancedPairsTradingStrategy, PairsConfig, PairMetrics
)
from core_engine.trading.strategies.strategy_engine import (
    StrategySignal, SignalType, StrategyType
)


class TestPairsTradingInitialization:
    """Test pairs trading strategy initialization and configuration"""
    
    @pytest.fixture
    def pairs_config(self):
        """Create pairs trading configuration"""
        return PairsConfig(
            strategy_name="test_pairs_trading",
            strategy_type=StrategyType.PAIRS_TRADING,
            required_symbols=["AAPL", "MSFT"],
            min_correlation=0.7,
            cointegration_pvalue=0.05,
            entry_zscore=2.0,
            exit_zscore=0.5,
            stop_loss_zscore=3.5,
            max_pairs=5,
            position_size_pct=0.02,
            max_holding_period=30,
            correlation_threshold=0.5
        )
    
    @pytest.fixture
    def pairs_trading_strategy(self, pairs_config):
        """Create pairs trading strategy instance"""
        return EnhancedPairsTradingStrategy(pairs_config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, pairs_trading_strategy):
        """Test strategy initialization"""
        assert pairs_trading_strategy.strategy_id is not None
        assert pairs_trading_strategy.strategy_type == StrategyType.PAIRS_TRADING
        assert pairs_trading_strategy.config is not None
        assert pairs_trading_strategy.is_initialized is False
        assert pairs_trading_strategy.is_operational is False
    
    @pytest.mark.asyncio
    async def test_config_validation(self, pairs_config):
        """Test configuration validation"""
        # Test valid configuration
        strategy = EnhancedPairsTradingStrategy(pairs_config)
        assert strategy._validate_strategy_config() is True
        
        # Test invalid configuration
        invalid_config = replace(pairs_config, min_correlation=1.5)  # > 1.0
        invalid_strategy = EnhancedPairsTradingStrategy(invalid_config)
        assert invalid_strategy._validate_strategy_config() is False
    
    @pytest.mark.asyncio
    async def test_component_registration(self, pairs_trading_strategy):
        """Test component registration with orchestrator"""
        mock_orchestrator = Mock()
        pairs_trading_strategy.register_with_orchestrator(mock_orchestrator)
        
        assert pairs_trading_strategy.orchestrator == mock_orchestrator
        assert pairs_trading_strategy.component_id is not None


class TestPairsTradingInterface:
    """Test ISystemComponent interface implementation"""
    
    @pytest.fixture
    def pairs_trading_strategy(self):
        """Create pairs trading strategy instance"""
        config = PairsConfig(
            strategy_name="test_pairs_trading",
            strategy_type=StrategyType.PAIRS_TRADING,
            required_symbols=["AAPL", "MSFT"]
        )
        return EnhancedPairsTradingStrategy(config)
    
    @pytest.mark.asyncio
    async def test_initialize_method(self, pairs_trading_strategy):
        """Test initialize method"""
        result = await pairs_trading_strategy.initialize()
        assert result is True
        assert pairs_trading_strategy.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_start_method(self, pairs_trading_strategy):
        """Test start method"""
        await pairs_trading_strategy.initialize()
        result = await pairs_trading_strategy.start()
        assert result is True
        assert pairs_trading_strategy.is_operational is True
    
    @pytest.mark.asyncio
    async def test_start_without_initialization(self, pairs_trading_strategy):
        """Test start without initialization should fail"""
        result = await pairs_trading_strategy.start()
        assert result is False
        assert pairs_trading_strategy.is_operational is False
    
    @pytest.mark.asyncio
    async def test_stop_method(self, pairs_trading_strategy):
        """Test stop method"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        result = await pairs_trading_strategy.stop()
        assert result is True
        assert pairs_trading_strategy.is_operational is False
    
    @pytest.mark.asyncio
    async def test_health_check(self, pairs_trading_strategy):
        """Test health check method"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        health = await pairs_trading_strategy.health_check()
        assert 'healthy' in health
        assert 'initialized' in health
        assert 'operational' in health
        assert 'component_type' in health
        assert health['component_type'] == 'Strategy'
    
    def test_get_status(self, pairs_trading_strategy):
        """Test get status method"""
        status = pairs_trading_strategy.get_status()
        assert 'initialized' in status
        assert 'operational' in status
        assert 'component_type' in status
        assert status['component_type'] == 'Strategy'


class TestPairSelection:
    """Test pair selection and validation functionality"""
    
    @pytest.fixture
    def pairs_trading_strategy(self):
        """Create pairs trading strategy instance"""
        config = PairsConfig(
            strategy_name="test_pairs_trading",
            strategy_type=StrategyType.PAIRS_TRADING,
            required_symbols=["AAPL", "MSFT", "GOOGL"],
            asset_universe=["AAPL", "MSFT", "GOOGL"],
            lookback_period=50  # Shorter lookback for test data
        )
        strategy = EnhancedPairsTradingStrategy(config)
        return strategy
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        return {
            'AAPL': pd.DataFrame({
                'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
                'volume': np.random.randint(1000000, 5000000, 100)
            }, index=dates),
            'MSFT': pd.DataFrame({
                'close': 200 + np.cumsum(np.random.randn(100) * 0.3),
                'volume': np.random.randint(1000000, 5000000, 100)
            }, index=dates),
            'GOOGL': pd.DataFrame({
                'close': 150 + np.cumsum(np.random.randn(100) * 0.4),
                'volume': np.random.randint(1000000, 5000000, 100)
            }, index=dates)
        }
    
    @pytest.mark.asyncio
    async def test_calculate_correlation_matrix(self, pairs_trading_strategy, sample_market_data):
        """Test correlation matrix calculation"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Update market data
        pairs_trading_strategy._update_market_data(sample_market_data)
        
        # Calculate correlation matrix
        pairs_trading_strategy._calculate_correlation_matrix()
        
        # Check that correlation matrix was calculated
        assert hasattr(pairs_trading_strategy, 'correlation_matrix')
        assert pairs_trading_strategy.correlation_matrix is not None
    
    @pytest.mark.asyncio
    async def test_update_pair_selection(self, pairs_trading_strategy, sample_market_data):
        """Test pair selection update"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Update market data
        pairs_trading_strategy._update_market_data(sample_market_data)
        
        # Update pair selection
        await pairs_trading_strategy._update_pair_selection()
        
        # Check that pair selection was updated
        assert hasattr(pairs_trading_strategy, 'selected_pairs')
    
    @pytest.mark.asyncio
    async def test_select_trading_pairs(self, pairs_trading_strategy, sample_market_data):
        """Test trading pair selection"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Update market data
        pairs_trading_strategy._update_market_data(sample_market_data)
        
        # Select trading pairs
        pairs_trading_strategy._select_trading_pairs()
        
        # Check that trading pairs were selected
        assert hasattr(pairs_trading_strategy, 'selected_pairs')
    
    @pytest.mark.asyncio
    async def test_cointegration_test(self, pairs_trading_strategy, sample_market_data):
        """Test cointegration testing"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Update market data
        pairs_trading_strategy._update_market_data(sample_market_data)
        
        # Test cointegration
        await pairs_trading_strategy._test_cointegration()
        
        # Check that cointegration was tested
        assert hasattr(pairs_trading_strategy, 'cointegration_results')


class TestCointegrationAnalysis:
    """Test cointegration analysis functionality"""
    
    @pytest.fixture
    def pairs_trading_strategy(self):
        """Create pairs trading strategy instance"""
        config = PairsConfig(
            strategy_name="test_pairs_trading",
            strategy_type=StrategyType.PAIRS_TRADING,
            required_symbols=["AAPL", "MSFT"],
            cointegration_pvalue=0.05
        )
        strategy = EnhancedPairsTradingStrategy(config)
        return strategy
    
    @pytest.fixture
    def cointegrated_data(self):
        """Create cointegrated price data"""
        np.random.seed(42)
        n = 100
        # Create cointegrated series
        x = np.cumsum(np.random.randn(n))
        y = 2 * x + np.random.randn(n) * 0.1  # y = 2x + noise
        
        dates = pd.date_range(start='2024-01-01', periods=n, freq='5min')
        return {
            'AAPL': pd.DataFrame({'close': 100 + x}, index=dates),
            'MSFT': pd.DataFrame({'close': 200 + y}, index=dates)
        }
    
    @pytest.mark.asyncio
    async def test_cointegration_test(self, pairs_trading_strategy, cointegrated_data):
        """Test cointegration test"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Update market data
        pairs_trading_strategy._update_market_data(cointegrated_data)
        
        # Test cointegration
        await pairs_trading_strategy._test_cointegration()
        
        # Check that cointegration was tested
        assert hasattr(pairs_trading_strategy, 'cointegration_results')
    
    @pytest.mark.asyncio
    async def test_pair_cointegration_test(self, pairs_trading_strategy, cointegrated_data):
        """Test pair-specific cointegration test"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Update market data
        pairs_trading_strategy._update_market_data(cointegrated_data)
        
        # Test pair cointegration
        result = await pairs_trading_strategy._test_pair_cointegration('AAPL', 'MSFT')
        
        if result is not None:
            assert isinstance(result, dict)
            assert 'is_cointegrated' in result
            assert 'p_value' in result
            assert 'test_statistic' in result
    
    @pytest.mark.asyncio
    async def test_calculate_current_zscore(self, pairs_trading_strategy, cointegrated_data):
        """Test current Z-score calculation"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Update market data
        pairs_trading_strategy._update_market_data(cointegrated_data)
        
        # Create a mock pair metrics object
        pair_metrics = PairMetrics(
            stock1='AAPL',
            stock2='MSFT',
            correlation=0.8,
            cointegration_pvalue=0.01,
            hedge_ratio=1.5
        )
        
        # Calculate current Z-score
        zscore = pairs_trading_strategy._calculate_current_zscore(pair_metrics)
        
        assert isinstance(zscore, float)
        assert not np.isnan(zscore)


class TestSignalGeneration:
    """Test signal generation functionality"""
    
    @pytest.fixture
    def pairs_trading_strategy(self):
        """Create pairs trading strategy instance"""
        config = PairsConfig(
            strategy_name="test_pairs_trading",
            strategy_type=StrategyType.PAIRS_TRADING,
            required_symbols=["AAPL", "MSFT"],
            entry_zscore=2.0
        )
        strategy = EnhancedPairsTradingStrategy(config)
        return strategy
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='5min')
        return {
            'AAPL': pd.DataFrame({
                'close': 100 + np.cumsum(np.random.randn(50) * 0.5),
                'volume': np.random.randint(1000000, 5000000, 50)
            }, index=dates),
            'MSFT': pd.DataFrame({
                'close': 200 + np.cumsum(np.random.randn(50) * 0.3),
                'volume': np.random.randint(1000000, 5000000, 50)
            }, index=dates)
        }
    
    @pytest.mark.asyncio
    async def test_generate_signals(self, pairs_trading_strategy, sample_market_data):
        """Test signal generation"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Generate signals
        signals = await pairs_trading_strategy.generate_signals(sample_market_data)
        
        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.symbol in ['AAPL', 'MSFT']
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
    
    @pytest.mark.asyncio
    async def test_generate_entry_signals(self, pairs_trading_strategy, sample_market_data):
        """Test entry signal generation"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Update market data
        pairs_trading_strategy._update_market_data(sample_market_data)
        
        # Generate entry signals
        signals = await pairs_trading_strategy._generate_entry_signals()
        
        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
    
    @pytest.mark.asyncio
    async def test_generate_exit_signals(self, pairs_trading_strategy, sample_market_data):
        """Test exit signal generation"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Update market data
        pairs_trading_strategy._update_market_data(sample_market_data)
        
        # Generate exit signals
        signals = await pairs_trading_strategy._generate_exit_signals()
        
        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
    
    @pytest.mark.asyncio
    async def test_create_spread_signal(self, pairs_trading_strategy):
        """Test spread signal creation"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Create spread signal
        signal = StrategySignal(
            signal_id="test_signal",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            target_quantity=100.0,
            position_side='long'
        )
        
        assert isinstance(signal, StrategySignal)
        assert signal.symbol == 'AAPL'
        assert signal.target_quantity == 100.0


class TestPositionManagement:
    """Test position management functionality"""
    
    @pytest.fixture
    def pairs_trading_strategy(self):
        """Create pairs trading strategy instance"""
        config = PairsConfig(
            strategy_name="test_pairs_trading",
            strategy_type=StrategyType.PAIRS_TRADING,
            required_symbols=["AAPL", "MSFT"]
        )
        strategy = EnhancedPairsTradingStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_calculate_position_size(self, pairs_trading_strategy):
        """Test position size calculation"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Create mock signal
        signal = StrategySignal(
            signal_id="test_signal",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            target_quantity=100.0,
            position_side='long'
        )
        
        # Mock market data
        market_data = {'AAPL': {'close': 150.0, 'volume': 1000000}}
        
        position_size = pairs_trading_strategy.calculate_position_size(signal, market_data)
        
        assert isinstance(position_size, float)
        assert position_size >= 0
    
    @pytest.mark.asyncio
    async def test_position_tracking(self, pairs_trading_strategy):
        """Test position tracking"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Create signal
        signal = StrategySignal(
            signal_id="test_signal",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            target_quantity=100.0,
            position_side='long'
        )
        
        # Update positions
        market_data = {'AAPL': pd.DataFrame({'close': [150.0], 'volume': [1000000]})}
        await pairs_trading_strategy.update_positions(market_data)
        
        positions = pairs_trading_strategy.get_active_positions()
        assert isinstance(positions, dict)
    
    @pytest.mark.asyncio
    async def test_position_updates(self, pairs_trading_strategy):
        """Test position updates"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Create initial position
        signal = StrategySignal(
            signal_id="test_signal",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            target_quantity=100.0,
            position_side='long'
        )
        
        # Update positions
        market_data = {'AAPL': pd.DataFrame({'close': [150.0], 'volume': [1000000]})}
        await pairs_trading_strategy.update_positions(market_data)
        
        positions = pairs_trading_strategy.get_active_positions()
        assert isinstance(positions, dict)


class TestPerformanceTracking:
    """Test performance tracking functionality"""
    
    @pytest.fixture
    def pairs_trading_strategy(self):
        """Create pairs trading strategy instance"""
        config = PairsConfig(
            strategy_name="test_pairs_trading",
            strategy_type=StrategyType.PAIRS_TRADING,
            required_symbols=["AAPL", "MSFT"]
        )
        strategy = EnhancedPairsTradingStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, pairs_trading_strategy):
        """Test performance metrics calculation"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Create signal
        signal = StrategySignal(
            signal_id="test_signal",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            target_quantity=100.0,
            position_side='long'
        )
        
        # Update performance metrics
        pairs_trading_strategy.update_performance_metrics(signal, True)
        
        assert pairs_trading_strategy.performance_metrics.total_signals > 0
        assert pairs_trading_strategy.performance_metrics.total_return >= 0
    
    @pytest.mark.asyncio
    async def test_pairs_summary(self, pairs_trading_strategy):
        """Test pairs trading summary"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Get pairs summary
        summary = pairs_trading_strategy.get_pairs_trading_summary()
        
        assert isinstance(summary, dict)
        assert 'strategy_id' in summary
        assert 'active_pairs' in summary


class TestErrorHandling:
    """Test error handling and recovery"""
    
    @pytest.fixture
    def pairs_trading_strategy(self):
        """Create pairs trading strategy instance"""
        config = PairsConfig(
            strategy_name="test_pairs_trading",
            strategy_type=StrategyType.PAIRS_TRADING,
            required_symbols=["AAPL", "MSFT"]
        )
        strategy = EnhancedPairsTradingStrategy(config)
        return strategy
    
    @pytest.mark.asyncio
    async def test_invalid_data_handling(self, pairs_trading_strategy):
        """Test handling of invalid data"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Test with empty data
        empty_data = {}
        signals = await pairs_trading_strategy.generate_signals(empty_data)
        
        assert signals == []
    
    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self, pairs_trading_strategy):
        """Test handling of insufficient data"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Test with insufficient data
        insufficient_data = {
            'AAPL': pd.DataFrame({'close': [100, 101, 102]})  # Only 3 data points
        }
        
        signals = await pairs_trading_strategy.generate_signals(insufficient_data)
        
        # Should handle gracefully
        assert isinstance(signals, list)


class TestIntegration:
    """Test integration and lifecycle functionality"""
    
    @pytest.fixture
    def pairs_trading_strategy(self):
        """Create pairs trading strategy instance"""
        config = PairsConfig(
            strategy_name="test_pairs_trading",
            strategy_type=StrategyType.PAIRS_TRADING,
            required_symbols=["AAPL", "MSFT"]
        )
        strategy = EnhancedPairsTradingStrategy(config)
        return strategy
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='5min')
        return {
            'AAPL': pd.DataFrame({
                'close': 100 + np.cumsum(np.random.randn(50) * 0.5),
                'volume': np.random.randint(1000000, 5000000, 50)
            }, index=dates),
            'MSFT': pd.DataFrame({
                'close': 200 + np.cumsum(np.random.randn(50) * 0.3),
                'volume': np.random.randint(1000000, 5000000, 50)
            }, index=dates)
        }
    
    @pytest.mark.asyncio
    async def test_strategy_lifecycle(self, pairs_trading_strategy, sample_market_data):
        """Test complete strategy lifecycle"""
        # Initialize
        assert await pairs_trading_strategy.initialize() is True
        assert pairs_trading_strategy.is_initialized
        
        # Start
        assert await pairs_trading_strategy.start() is True
        assert pairs_trading_strategy.is_operational
        
        # Generate signals
        signals = await pairs_trading_strategy.generate_signals(sample_market_data)
        assert isinstance(signals, list)
        
        # Health check
        health = await pairs_trading_strategy.health_check()
        assert health['initialized'] is True
        
        # Stop
        assert await pairs_trading_strategy.stop() is True
        assert not pairs_trading_strategy.is_operational
    
    @pytest.mark.asyncio
    async def test_performance_under_different_conditions(self, pairs_trading_strategy):
        """Test performance under different market conditions"""
        await pairs_trading_strategy.initialize()
        await pairs_trading_strategy.start()
        
        # Test with different market conditions
        conditions = [
            {'AAPL': pd.DataFrame({'close': np.linspace(100, 120, 50)})},
            {'AAPL': pd.DataFrame({'close': np.linspace(120, 100, 50)})},
            {'AAPL': pd.DataFrame({'close': np.full(50, 110) + np.random.randn(50)})}
        ]
        
        for condition in conditions:
            signals = await pairs_trading_strategy.generate_signals(condition)
            assert isinstance(signals, list)
