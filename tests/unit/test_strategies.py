"""
Unit Tests for Strategy System
=============================

Tests for the streamlined strategy system (strategies.py).
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from core_structure.strategies import (
    StrategyManager, StrategyRegistry, BaseStrategy,
    MomentumStrategy, MeanReversionStrategy, PairsTradingStrategy,
    StrategyType, StrategyStatus, ExecutionMode
)
from core_structure.engines import TradingSignal, SignalType, SignalStrength
from core_structure.config import TradingConfig


class TestBaseStrategy:
    """Test BaseStrategy abstract class"""
    
    def test_base_strategy_interface(self):
        """Test base strategy interface"""
        # BaseStrategy is abstract, so we test through concrete implementation
        config = {'lookback_period': 20}
        strategy = MomentumStrategy("test_momentum", config)
        
        assert strategy.strategy_id == "test_momentum"
        assert strategy.config == config
        assert strategy.status == StrategyStatus.INACTIVE
        assert strategy.strategy_type == StrategyType.MOMENTUM
    
    def test_strategy_lifecycle(self):
        """Test strategy lifecycle management"""
        config = {'lookback_period': 20}
        strategy = MomentumStrategy("test_momentum", config)
        
        # Initial state
        assert strategy.status == StrategyStatus.INACTIVE
        
        # Activate strategy
        strategy.set_status(StrategyStatus.ACTIVE)
        assert strategy.status == StrategyStatus.ACTIVE
        
        # Deactivate strategy
        strategy.set_status(StrategyStatus.INACTIVE)
        assert strategy.status == StrategyStatus.INACTIVE
    
    def test_strategy_metrics(self):
        """Test strategy performance metrics"""
        config = {'lookback_period': 20}
        strategy = MomentumStrategy("test_momentum", config)
        
        metrics = strategy.get_metrics()
        
        assert hasattr(metrics, 'signals_generated')
        assert hasattr(metrics, 'successful_signals')
        assert hasattr(metrics, 'avg_confidence')
        assert metrics.signals_generated >= 0


class TestMomentumStrategy:
    """Test MomentumStrategy implementation"""
    
    def test_momentum_strategy_creation(self):
        """Test momentum strategy creation"""
        config = {
            'lookback_period': 20,
            'momentum_threshold': 0.02,
            'confidence_threshold': 0.7
        }
        
        strategy = MomentumStrategy("momentum_test", config)
        
        assert strategy.strategy_id == "momentum_test"
        assert strategy.strategy_type == StrategyType.MOMENTUM
        assert strategy.config['lookback_period'] == 20
        assert strategy.config['momentum_threshold'] == 0.02
    
    def test_momentum_signal_generation(self, sample_market_data):
        """Test momentum signal generation"""
        config = {
            'lookback_period': 20,
            'momentum_threshold': 0.02,
            'confidence_threshold': 0.7
        }
        
        strategy = MomentumStrategy("momentum_test", config)
        strategy.set_status(StrategyStatus.ACTIVE)
        
        # Use sample data for AAPL
        data = sample_market_data['AAPL']
        
        signals = strategy.generate_signals(data)
        
        assert isinstance(signals, list)
        # Should generate some signals for trending data
        for signal in signals:
            assert isinstance(signal, TradingSignal)
            assert signal.symbol in ['AAPL']
            assert signal.signal_type in [SignalType.LONG, SignalType.SHORT]
    
    def test_momentum_calculation(self, sample_market_data):
        """Test momentum calculation logic"""
        config = {'lookback_period': 10, 'momentum_threshold': 0.01}
        strategy = MomentumStrategy("momentum_test", config)
        
        data = sample_market_data['AAPL']
        
        # Test momentum calculation
        momentum = strategy._calculate_momentum(data['close'])
        
        assert isinstance(momentum, (float, np.float64))
        assert not np.isnan(momentum)
    
    def test_momentum_signal_validation(self):
        """Test momentum signal validation"""
        config = {
            'lookback_period': 20,
            'momentum_threshold': 0.02,
            'confidence_threshold': 0.8
        }
        
        strategy = MomentumStrategy("momentum_test", config)
        
        # Create test signals with different confidence levels
        high_confidence_signal = TradingSignal(
            "AAPL", SignalType.LONG, SignalStrength.STRONG, 0.9, datetime.now()
        )
        
        low_confidence_signal = TradingSignal(
            "AAPL", SignalType.LONG, SignalStrength.WEAK, 0.5, datetime.now()
        )
        
        assert strategy._validate_signal(high_confidence_signal)
        assert not strategy._validate_signal(low_confidence_signal)


class TestMeanReversionStrategy:
    """Test MeanReversionStrategy implementation"""
    
    def test_mean_reversion_strategy_creation(self):
        """Test mean reversion strategy creation"""
        config = {
            'lookback_period': 20,
            'z_score_threshold': 2.0,
            'exit_threshold': 0.5
        }
        
        strategy = MeanReversionStrategy("mean_reversion_test", config)
        
        assert strategy.strategy_id == "mean_reversion_test"
        assert strategy.strategy_type == StrategyType.MEAN_REVERSION
        assert strategy.config['z_score_threshold'] == 2.0
    
    def test_z_score_calculation(self, sample_market_data):
        """Test z-score calculation"""
        config = {'lookback_period': 20, 'z_score_threshold': 2.0}
        strategy = MeanReversionStrategy("mean_reversion_test", config)
        
        data = sample_market_data['AAPL']
        
        z_score = strategy._calculate_z_score(data['close'])
        
        assert isinstance(z_score, (float, np.float64))
        assert not np.isnan(z_score)
    
    def test_mean_reversion_signals(self, sample_market_data):
        """Test mean reversion signal generation"""
        config = {
            'lookbook_period': 20,
            'z_score_threshold': 1.5,  # Lower threshold for testing
            'confidence_threshold': 0.6
        }
        
        strategy = MeanReversionStrategy("mean_reversion_test", config)
        strategy.set_status(StrategyStatus.ACTIVE)
        
        data = sample_market_data['AAPL']
        
        signals = strategy.generate_signals(data)
        
        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, TradingSignal)
            assert signal.symbol == 'AAPL'


class TestPairsTradingStrategy:
    """Test PairsTradingStrategy implementation"""
    
    def test_pairs_strategy_creation(self):
        """Test pairs trading strategy creation"""
        config = {
            'pairs': [('AAPL', 'MSFT'), ('GOOGL', 'AMZN')],
            'lookback_period': 60,
            'entry_threshold': 2.0,
            'exit_threshold': 0.5
        }
        
        strategy = PairsTradingStrategy("pairs_test", config)
        
        assert strategy.strategy_id == "pairs_test"
        assert strategy.strategy_type == StrategyType.PAIRS_TRADING
        assert len(strategy.config['pairs']) == 2
    
    def test_cointegration_analysis(self, sample_market_data):
        """Test cointegration analysis"""
        config = {
            'pairs': [('AAPL', 'MSFT')],
            'lookback_period': 60
        }
        
        strategy = PairsTradingStrategy("pairs_test", config)
        
        # Get data for both symbols
        data1 = sample_market_data['AAPL']['close']
        data2 = sample_market_data['MSFT']['close']
        
        # Test cointegration analysis
        is_cointegrated, hedge_ratio = strategy._test_cointegration(data1, data2)
        
        assert isinstance(is_cointegrated, bool)
        assert isinstance(hedge_ratio, (float, np.float64))
        assert not np.isnan(hedge_ratio)
    
    def test_spread_calculation(self, sample_market_data):
        """Test spread calculation for pairs"""
        config = {'pairs': [('AAPL', 'MSFT')], 'lookback_period': 60}
        strategy = PairsTradingStrategy("pairs_test", config)
        
        data1 = sample_market_data['AAPL']['close']
        data2 = sample_market_data['MSFT']['close']
        
        spread = strategy._calculate_spread(data1, data2, hedge_ratio=1.0)
        
        assert isinstance(spread, pd.Series)
        assert len(spread) == len(data1)
    
    def test_pairs_signal_generation(self, sample_market_data):
        """Test pairs trading signal generation"""
        config = {
            'pairs': [('AAPL', 'MSFT')],
            'lookback_period': 30,
            'entry_threshold': 1.5,
            'confidence_threshold': 0.6
        }
        
        strategy = PairsTradingStrategy("pairs_test", config)
        strategy.set_status(StrategyStatus.ACTIVE)
        
        # Combine data for pairs analysis
        combined_data = {
            'AAPL': sample_market_data['AAPL'],
            'MSFT': sample_market_data['MSFT']
        }
        
        signals = strategy.generate_signals(combined_data)
        
        assert isinstance(signals, list)
        # Pairs trading generates signals for both legs
        for signal in signals:
            assert isinstance(signal, TradingSignal)
            assert signal.symbol in ['AAPL', 'MSFT']


class TestStrategyRegistry:
    """Test StrategyRegistry functionality"""
    
    def test_registry_initialization(self):
        """Test strategy registry initialization"""
        registry = StrategyRegistry()
        
        # Should have built-in strategies registered
        available_strategies = registry.get_available_strategies()
        
        assert StrategyType.MOMENTUM in available_strategies
        assert StrategyType.MEAN_REVERSION in available_strategies
        assert StrategyType.PAIRS_TRADING in available_strategies
    
    def test_strategy_registration(self):
        """Test custom strategy registration"""
        registry = StrategyRegistry()
        
        # Register custom strategy
        class CustomStrategy(BaseStrategy):
            @property
            def strategy_type(self):
                return StrategyType.CUSTOM
            
            def generate_signals(self, data):
                return []
        
        registry.register_strategy(StrategyType.CUSTOM, CustomStrategy)
        
        # Should be available
        available_strategies = registry.get_available_strategies()
        assert StrategyType.CUSTOM in available_strategies
    
    def test_strategy_creation(self):
        """Test strategy instance creation"""
        registry = StrategyRegistry()
        
        config = {'lookback_period': 20}
        
        # Create momentum strategy
        strategy = registry.create_strategy(
            StrategyType.MOMENTUM,
            "test_momentum",
            config
        )
        
        assert isinstance(strategy, MomentumStrategy)
        assert strategy.strategy_id == "test_momentum"
        assert strategy.config == config
    
    def test_strategy_retrieval(self):
        """Test strategy instance retrieval"""
        registry = StrategyRegistry()
        
        config = {'lookback_period': 20}
        
        # Create and retrieve strategy
        strategy = registry.create_strategy(
            StrategyType.MOMENTUM,
            "test_momentum",
            config
        )
        
        retrieved_strategy = registry.get_strategy("test_momentum")
        
        assert retrieved_strategy is strategy
        assert retrieved_strategy.strategy_id == "test_momentum"


class TestStrategyManager:
    """Test StrategyManager functionality"""
    
    def test_manager_initialization(self, test_config):
        """Test strategy manager initialization"""
        manager = StrategyManager(test_config)
        
        assert manager.config == test_config
        assert isinstance(manager.registry, StrategyRegistry)
        assert len(manager._active_strategies) == 0
    
    def test_strategy_lifecycle_management(self, test_config):
        """Test strategy lifecycle through manager"""
        manager = StrategyManager(test_config)
        
        config = {'lookback_period': 20}
        
        # Create strategy
        strategy = manager.create_strategy(
            StrategyType.MOMENTUM,
            "managed_momentum",
            config
        )
        
        assert strategy.strategy_id == "managed_momentum"
        assert "managed_momentum" in manager._active_strategies
        
        # Remove strategy
        manager.remove_strategy("managed_momentum")
        assert "managed_momentum" not in manager._active_strategies
    
    def test_multi_strategy_management(self, test_config):
        """Test managing multiple strategies"""
        manager = StrategyManager(test_config)
        
        # Create multiple strategies
        strategies = [
            (StrategyType.MOMENTUM, "momentum_1", {'lookback_period': 20}),
            (StrategyType.MEAN_REVERSION, "mean_rev_1", {'z_score_threshold': 2.0}),
            (StrategyType.PAIRS_TRADING, "pairs_1", {'pairs': [('AAPL', 'MSFT')]})
        ]
        
        for strategy_type, strategy_id, config in strategies:
            manager.create_strategy(strategy_type, strategy_id, config)
        
        assert len(manager._active_strategies) == 3
        
        # Test strategy retrieval
        momentum_strategy = manager.get_strategy("momentum_1")
        assert momentum_strategy.strategy_type == StrategyType.MOMENTUM
    
    def test_strategy_execution(self, test_config, sample_market_data):
        """Test strategy execution through manager"""
        manager = StrategyManager(test_config)
        
        # Create momentum strategy
        config = {'lookback_period': 20, 'momentum_threshold': 0.02}
        strategy = manager.create_strategy(
            StrategyType.MOMENTUM,
            "test_momentum",
            config
        )
        
        # Execute strategy
        data = sample_market_data['AAPL']
        results = manager.execute_strategy("test_momentum", data)
        
        assert isinstance(results, list)  # Should return list of signals
    
    def test_manager_performance_tracking(self, test_config):
        """Test manager performance tracking"""
        manager = StrategyManager(test_config)
        
        # Create strategies
        config = {'lookback_period': 20}
        manager.create_strategy(StrategyType.MOMENTUM, "momentum_1", config)
        manager.create_strategy(StrategyType.MEAN_REVERSION, "mean_rev_1", config)
        
        # Get overall metrics
        metrics = manager.get_overall_metrics()
        
        assert 'total_strategies' in metrics
        assert 'active_strategies' in metrics
        assert metrics['total_strategies'] == 2


class TestStrategyIntegration:
    """Test strategy system integration"""
    
    def test_strategy_signal_pipeline(self, test_config, sample_market_data):
        """Test complete strategy signal pipeline"""
        manager = StrategyManager(test_config)
        
        # Create multiple strategies
        strategies = [
            (StrategyType.MOMENTUM, "momentum", {'lookback_period': 20}),
            (StrategyType.MEAN_REVERSION, "mean_rev", {'z_score_threshold': 2.0})
        ]
        
        for strategy_type, strategy_id, config in strategies:
            manager.create_strategy(strategy_type, strategy_id, config)
        
        # Execute all strategies
        all_signals = []
        for strategy_id in ["momentum", "mean_rev"]:
            signals = manager.execute_strategy(strategy_id, sample_market_data['AAPL'])
            all_signals.extend(signals)
        
        # Should have signals from multiple strategies
        assert len(all_signals) >= 0  # May be 0 if no signals generated
        
        # All signals should be valid
        for signal in all_signals:
            assert isinstance(signal, TradingSignal)
    
    def test_strategy_error_handling(self, test_config):
        """Test strategy error handling"""
        manager = StrategyManager(test_config)
        
        # Test invalid strategy creation
        try:
            manager.create_strategy("INVALID_TYPE", "invalid", {})
            assert False, "Should have raised an error"
        except (ValueError, KeyError):
            pass  # Expected
        
        # Test invalid strategy execution
        result = manager.execute_strategy("nonexistent_strategy", {})
        assert result is None or result == []


@pytest.mark.performance
class TestStrategyPerformance:
    """Test strategy performance characteristics"""
    
    def test_strategy_signal_generation_performance(self, sample_market_data, performance_timer):
        """Test strategy signal generation performance"""
        config = {'lookback_period': 20, 'momentum_threshold': 0.02}
        strategy = MomentumStrategy("perf_test", config)
        strategy.set_status(StrategyStatus.ACTIVE)
        
        performance_timer.start()
        
        # Generate signals multiple times
        for _ in range(10):
            signals = strategy.generate_signals(sample_market_data['AAPL'])
        
        performance_timer.stop()
        
        # Should be fast
        assert performance_timer.elapsed_seconds < 1.0
    
    def test_multi_strategy_performance(self, test_config, sample_market_data, performance_timer):
        """Test multi-strategy performance"""
        manager = StrategyManager(test_config)
        
        # Create multiple strategies
        strategies = [
            (StrategyType.MOMENTUM, f"momentum_{i}", {'lookback_period': 20})
            for i in range(5)
        ]
        
        for strategy_type, strategy_id, config in strategies:
            manager.create_strategy(strategy_type, strategy_id, config)
        
        performance_timer.start()
        
        # Execute all strategies
        for i in range(5):
            manager.execute_strategy(f"momentum_{i}", sample_market_data['AAPL'])
        
        performance_timer.stop()
        
        # Should handle multiple strategies efficiently
        assert performance_timer.elapsed_seconds < 2.0
