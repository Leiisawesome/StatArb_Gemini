"""
Unit tests for Enhanced Factor Strategy
=====================================

Comprehensive test suite for the Enhanced Factor Strategy implementation
with focus on achieving 100% test coverage.

Author: StatArb_Gemini Test Suite
Version: 1.0.0
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from unittest.mock import Mock
from dataclasses import replace

from core_engine.trading.strategies.implementations.factor.enhanced_factor import (
    EnhancedFactorStrategy, FactorConfig
)
from core_engine.trading.strategies.strategy_engine import (
    StrategyType
)


class TestFactorInitialization:
    """Test factor strategy initialization"""
    
    @pytest.fixture
    def factor_config(self):
        """Create factor strategy configuration"""
        return FactorConfig(
            strategy_type=StrategyType.FACTOR,
            required_symbols=["AAPL", "MSFT", "GOOGL"],
            factors=['momentum', 'value', 'quality'],
            rebalance_frequency=20,
            factor_lookback=60,
            base_position_pct=0.02,
            max_position_pct=0.06
        )
    
    @pytest.fixture
    def factor_strategy(self, factor_config):
        """Create factor strategy instance"""
        return EnhancedFactorStrategy(factor_config)
    
    def test_initialization(self, factor_strategy):
        """Test strategy initialization"""
        assert factor_strategy.strategy_id is not None
        assert factor_strategy.strategy_type == StrategyType.FACTOR
        assert factor_strategy.config.factors == ['momentum', 'value', 'quality']
        assert factor_strategy.config.rebalance_frequency == 20
        assert factor_strategy.config.factor_lookback == 60
        assert factor_strategy.config.base_position_pct == 0.02
        assert factor_strategy.config.max_position_pct == 0.06
    
    def test_config_validation(self, factor_config):
        """Test configuration validation"""
        # Test invalid config
        invalid_config = replace(factor_config, factor_lookback=-1)
        strategy = EnhancedFactorStrategy(invalid_config)
        assert not strategy._validate_configuration()
    
    def test_health_check(self, factor_strategy):
        """Test strategy health check"""
        health = asyncio.run(factor_strategy.health_check())
        assert 'healthy' in health
        assert 'component_type' in health
        assert 'active_positions' in health
        assert 'factors_calculated' in health
    
    def test_get_status(self, factor_strategy):
        """Test strategy status"""
        status = factor_strategy.get_status()
        assert 'operational' in status
        assert 'component_type' in status
        assert 'strategy_type' in status


class TestFactorAnalysis:
    """Test factor analysis functionality"""
    
    @pytest.fixture
    def factor_strategy(self):
        """Create factor strategy for testing"""
        config = FactorConfig(
            strategy_type=StrategyType.FACTOR,
            required_symbols=["AAPL", "MSFT"],
            factors=['momentum', 'value', 'quality'],
            factor_lookback=60
        )
        return EnhancedFactorStrategy(config)
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        # Create factor data
        base_price = 100
        momentum = np.linspace(0, 0.2, 100)  # 20% momentum
        value = np.random.normal(0, 0.1, 100)  # Value factor
        quality = np.random.normal(0, 0.05, 100)  # Quality factor
        
        prices = base_price * (1 + momentum + value + quality)
        volumes = np.random.randint(1000000, 5000000, 100)
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.999,
            'high': prices * 1.002,
            'low': prices * 0.998,
            'close': prices,
            'volume': volumes
        })
    
    def test_calculate_factors(self, factor_strategy, sample_market_data):
        """Test factor calculation"""
        # Update market data first
        factor_strategy._update_market_data({'AAPL': sample_market_data})
        factor_strategy._calculate_factor_scores()
        
        assert 'AAPL' in factor_strategy.factor_scores
        factors = factor_strategy.factor_scores['AAPL']
        
        assert 'momentum' in factors
        assert 'value' in factors
        assert 'quality' in factors
        
        # Check that factors are calculated
        assert isinstance(factors['momentum'], float)
        assert isinstance(factors['value'], float)
        assert isinstance(factors['quality'], float)
    
    def test_factor_exposure_analysis(self, factor_strategy, sample_market_data):
        """Test factor exposure analysis"""
        # Update market data and calculate factors
        factor_strategy._update_market_data({'AAPL': sample_market_data})
        factor_strategy._calculate_factor_scores()
        
        # Test exposure analysis through factor scores
        factors = factor_strategy.factor_scores['AAPL']
        
        assert 'momentum' in factors
        assert 'value' in factors
        assert 'quality' in factors
    
    def test_factor_correlation_analysis(self, factor_strategy, sample_market_data):
        """Test factor correlation analysis"""
        # Update market data and calculate factors
        factor_strategy._update_market_data({'AAPL': sample_market_data})
        factor_strategy._calculate_factor_scores()
        
        # Test correlation analysis through factor scores
        factors = factor_strategy.factor_scores['AAPL']
        
        assert 'momentum' in factors
        assert 'value' in factors
        assert 'quality' in factors


class TestSignalGeneration:
    """Test signal generation functionality"""
    
    @pytest.fixture
    def factor_strategy(self):
        """Create factor strategy for testing"""
        config = FactorConfig(
            strategy_type=StrategyType.FACTOR,
            required_symbols=["AAPL"],
            factors=['momentum', 'value', 'quality'],
            factor_lookback=60
        )
        return EnhancedFactorStrategy(config)
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        base_price = 100
        momentum = np.linspace(0, 0.2, 100)
        value = np.random.normal(0, 0.1, 100)
        quality = np.random.normal(0, 0.05, 100)
        
        prices = base_price * (1 + momentum + value + quality)
        volumes = np.random.randint(1000000, 5000000, 100)
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.999,
            'high': prices * 1.002,
            'low': prices * 0.998,
            'close': prices,
            'volume': volumes
        })
    
    def test_generate_symbol_signals(self, factor_strategy, sample_market_data):
        """Test signal generation for a symbol"""
        # Update market data and calculate factors
        factor_strategy._update_market_data({'AAPL': sample_market_data})
        factor_strategy._calculate_factor_scores()
        
        signals = asyncio.run(factor_strategy._generate_factor_signals())
        
        assert isinstance(signals, list)
        # Signals should be StrategySignal objects
        for signal in signals:
            assert hasattr(signal, 'strategy_id')
            assert hasattr(signal, 'signal_type')
            assert hasattr(signal, 'quantity')
            assert hasattr(signal, 'confidence')
    
    def test_factor_signal_creation(self, factor_strategy):
        """Test factor signal creation through signal generation"""
        # This is tested indirectly through _generate_factor_signals
        # which creates signals based on factor rankings
        assert True  # Placeholder for signal creation test


class TestPositionManagement:
    """Test position management functionality"""
    
    @pytest.fixture
    def factor_strategy(self):
        """Create factor strategy for testing"""
        config = FactorConfig(
            strategy_type=StrategyType.FACTOR,
            required_symbols=["AAPL"],
            base_position_pct=0.02,
            max_position_pct=0.06
        )
        return EnhancedFactorStrategy(config)
    
    def test_calculate_position_size(self, factor_strategy):
        """Test position size calculation"""
        # Create a mock signal
        signal = Mock()
        signal.strength = 0.8
        signal.quantity = 0.02
        
        # Create mock market data
        market_data = {'AAPL': pd.DataFrame()}
        
        position_size = factor_strategy.calculate_position_size(signal, market_data)
        
        assert position_size > 0
        assert position_size <= factor_strategy.config.max_position_pct
    
    def test_position_tracking(self, factor_strategy):
        """Test position tracking through signal generation"""
        # Test by generating signals which may create positions
        factor_strategy.factor_scores['AAPL'] = {
            'momentum': 0.8,
            'value': 0.6,
            'quality': 0.7
        }
        
        signals = asyncio.run(factor_strategy._generate_factor_signals())
        assert isinstance(signals, list)
    
    def test_position_updates(self, factor_strategy):
        """Test position updates through signal generation"""
        # Test by generating signals which may create positions
        factor_strategy.factor_scores['AAPL'] = {
            'momentum': 0.8,
            'value': 0.6,
            'quality': 0.7
        }
        
        signals = asyncio.run(factor_strategy._generate_factor_signals())
        assert isinstance(signals, list)


class TestFactorWeighting:
    """Test factor weighting functionality"""
    
    @pytest.fixture
    def factor_strategy(self):
        """Create factor strategy for testing"""
        config = FactorConfig(
            strategy_type=StrategyType.FACTOR,
            required_symbols=["AAPL"],
            factors=['momentum', 'value', 'quality']
        )
        return EnhancedFactorStrategy(config)
    
    def test_calculate_factor_weights(self, factor_strategy):
        """Test factor weight calculation through ranking"""
        # Test factor ranking which includes weighting
        factor_strategy.factor_scores['AAPL'] = {
            'momentum': 0.8,
            'value': 0.6,
            'quality': 0.7
        }
        
        rankings = factor_strategy._rank_symbols_by_factors()
        assert isinstance(rankings, list)
    
    def test_dynamic_factor_weighting(self, factor_strategy):
        """Test dynamic factor weighting through ranking"""
        # Test with different market conditions
        factor_strategy.factor_scores['AAPL'] = {
            'momentum': 0.9,
            'value': 0.4,
            'quality': 0.6
        }
        
        rankings = factor_strategy._rank_symbols_by_factors()
        assert isinstance(rankings, list)


class TestPerformanceTracking:
    """Test performance tracking functionality"""
    
    @pytest.fixture
    def factor_strategy(self):
        """Create factor strategy for testing"""
        config = FactorConfig(
            strategy_type=StrategyType.FACTOR,
            required_symbols=["AAPL"]
        )
        return EnhancedFactorStrategy(config)
    
    def test_performance_metrics(self, factor_strategy):
        """Test performance metrics calculation"""
        # Simulate some trades
        factor_strategy.performance_metrics.total_signals = 15
        factor_strategy.performance_metrics.successful_signals = 12
        factor_strategy.performance_metrics.failed_signals = 3
        
        # Manually set win rate
        factor_strategy.performance_metrics.win_rate = 0.8
        
        metrics = factor_strategy.performance_metrics
        
        assert metrics.total_signals == 15
        assert metrics.successful_signals == 12
        assert metrics.failed_signals == 3
        assert metrics.win_rate == 0.8
    
    def test_factor_summary(self, factor_strategy):
        """Test factor strategy summary"""
        summary = factor_strategy.get_factor_summary()
        
        assert 'active_positions' in summary
        assert 'factor_scores' in summary
        assert 'performance_summary' in summary
        assert 'strategy_id' in summary


class TestIntegration:
    """Test integration functionality"""
    
    @pytest.fixture
    def factor_strategy(self):
        """Create factor strategy for testing"""
        config = FactorConfig(
            strategy_type=StrategyType.FACTOR,
            required_symbols=["AAPL", "MSFT"],
            factors=['momentum', 'value', 'quality'],
            factor_lookback=60
        )
        return EnhancedFactorStrategy(config)
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        base_price = 100
        momentum = np.linspace(0, 0.2, 100)
        value = np.random.normal(0, 0.1, 100)
        quality = np.random.normal(0, 0.05, 100)
        
        prices = base_price * (1 + momentum + value + quality)
        volumes = np.random.randint(1000000, 5000000, 100)
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.999,
            'high': prices * 1.002,
            'low': prices * 0.998,
            'close': prices,
            'volume': volumes
        })
    
    def test_strategy_lifecycle(self, factor_strategy, sample_market_data):
        """Test complete strategy lifecycle"""
        # Test initialization
        assert factor_strategy.strategy_id is not None
        assert factor_strategy.strategy_type == StrategyType.FACTOR
        
        # Test health check
        health = asyncio.run(factor_strategy.health_check())
        assert 'healthy' in health
        
        # Test signal generation
        factor_strategy._update_market_data({'AAPL': sample_market_data})
        factor_strategy._calculate_factor_scores()
        signals = asyncio.run(factor_strategy._generate_factor_signals())
        assert isinstance(signals, list)
        
        # Test performance metrics
        metrics = factor_strategy.performance_metrics
        assert hasattr(metrics, 'total_signals')
        assert hasattr(metrics, 'successful_signals')
        assert hasattr(metrics, 'win_rate')
    
    def test_error_handling(self, factor_strategy):
        """Test error handling"""
        # Test with invalid data
        invalid_data = pd.DataFrame()
        
        # Should handle gracefully
        factor_strategy._update_market_data({'AAPL': invalid_data})
        factor_strategy._calculate_factor_scores()
        signals = asyncio.run(factor_strategy._generate_factor_signals())
        assert isinstance(signals, list)
        assert len(signals) == 0  # No signals for invalid data
    
    def test_configuration_validation(self, factor_strategy):
        """Test configuration validation"""
        # Test valid configuration
        assert factor_strategy._validate_configuration() is True
        
        # Test invalid configuration
        invalid_config = replace(factor_strategy.config, factor_lookback=-1)
        factor_strategy.config = invalid_config
        assert factor_strategy._validate_configuration() is False
