"""
Unit tests for Enhanced Arbitrage Strategy
==========================================

Comprehensive test suite for the EnhancedArbitrageStrategy with ISystemComponent integration.
Tests cover initialization, arbitrage detection, signal generation, position management,
and performance tracking.

Author: StatArb_Gemini Test Suite
Version: 1.0.0
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

# Import the strategy and related classes
from core_engine.trading.strategies.implementations.arbitrage.enhanced_arbitrage import (
    EnhancedArbitrageStrategy, ArbitrageConfig, ArbitrageType
)
from core_engine.trading.strategies.strategy_engine import (
    StrategySignal, StrategyPosition, SignalType, StrategyType
)


@pytest.fixture
def arbitrage_config():
    """Enhanced Arbitrage Strategy configuration for testing"""
    return ArbitrageConfig(
        strategy_name="test_arbitrage",
        strategy_type=StrategyType.ARBITRAGE,
        required_symbols=["AAPL", "MSFT", "GOOGL", "AMZN"],
        warmup_period=60,
        min_price_discrepancy=0.001,
        max_execution_time=5.0,
        confidence_threshold=0.8,
        max_position_pct=0.05,
        transaction_cost_threshold=0.0005,
        arbitrage_pairs=[("AAPL", "MSFT"), ("GOOGL", "AMZN")],
        opportunity_timeout=10.0,
        price_update_frequency=1.0
    )


@pytest.fixture
def mock_orchestrator():
    """Mock system orchestrator"""
    orchestrator = Mock()
    orchestrator.register_component = Mock(return_value="test_component_id")
    orchestrator.request_system_authorization = AsyncMock(return_value=True)
    return orchestrator


@pytest.fixture
def mock_risk_manager():
    """Mock risk manager"""
    risk_manager = Mock()
    risk_manager.authorize_trading_decision = AsyncMock(return_value=Mock(
        authorization_level="AUTOMATIC",
        authorized_quantity=100.0,
        risk_budget_allocation=5000.0
    ))
    return risk_manager


@pytest.fixture
def arbitrage_strategy(arbitrage_config, mock_orchestrator, mock_risk_manager):
    """Enhanced Arbitrage Strategy instance for testing"""
    strategy = EnhancedArbitrageStrategy(arbitrage_config)
    strategy.orchestrator = mock_orchestrator
    strategy.risk_manager = mock_risk_manager
    return strategy


@pytest.fixture
def sample_market_data():
    """Sample market data for testing - arbitrage opportunities"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    np.random.seed(42)  # For reproducible tests
    
    # Create correlated but slightly diverging prices for arbitrage opportunities
    base_prices = {
        'AAPL': 150.0,
        'MSFT': 300.0,
        'GOOGL': 2800.0,
        'AMZN': 140.0
    }
    
    market_data = {}
    for symbol, base_price in base_prices.items():
        # Create correlated price movements with small divergences
        trend = np.sin(np.linspace(0, 4*np.pi, 100)) * 2
        noise = np.random.normal(0, 0.5, 100)
        prices = base_price + trend + noise
        
        market_data[symbol] = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.random.uniform(0, 1, 100),
            'low': prices - np.random.uniform(0, 1, 100),
            'close': prices,
            'volume': np.random.uniform(1000, 10000, 100)
        }).set_index('timestamp')
    
    return market_data


class TestArbitrageInitialization:
    """Test arbitrage strategy initialization"""
    
    def test_initialization(self, arbitrage_strategy):
        """Test strategy initialization"""
        assert arbitrage_strategy.strategy_id is not None
        assert arbitrage_strategy.strategy_type == StrategyType.ARBITRAGE
        assert arbitrage_strategy.config.min_price_discrepancy == 0.001
        assert arbitrage_strategy.config.max_execution_time == 5.0
        assert len(arbitrage_strategy.config.arbitrage_pairs) == 2
    
    def test_config_validation(self, arbitrage_config):
        """Test configuration validation"""
        # Test valid config
        assert arbitrage_config.min_price_discrepancy > 0
        assert arbitrage_config.max_execution_time > 0
        assert arbitrage_config.confidence_threshold > 0
        
        # Test invalid config
        invalid_config = ArbitrageConfig(
            strategy_name="invalid",
            strategy_type=StrategyType.ARBITRAGE,
            required_symbols=[],
            min_price_discrepancy=-0.001  # Invalid negative value
        )
        strategy = EnhancedArbitrageStrategy(invalid_config)
        assert not strategy._validate_strategy_config()
    
    def test_component_registration(self, arbitrage_strategy, mock_orchestrator):
        """Test component registration with orchestrator"""
        arbitrage_strategy.register_with_orchestrator(mock_orchestrator)
        mock_orchestrator.register_component.assert_called_once()


class TestArbitrageInterface:
    """Test ISystemComponent interface methods"""
    
    @pytest.mark.asyncio
    async def test_initialize_method(self, arbitrage_strategy):
        """Test strategy initialization"""
        result = await arbitrage_strategy.initialize()
        assert result is True
        assert arbitrage_strategy.is_initialized
    
    @pytest.mark.asyncio
    async def test_start_method(self, arbitrage_strategy):
        """Test strategy start"""
        await arbitrage_strategy.initialize()
        result = await arbitrage_strategy.start()
        assert result is True
        assert arbitrage_strategy.is_operational
    
    @pytest.mark.asyncio
    async def test_start_without_initialization(self, arbitrage_strategy):
        """Test start without initialization fails"""
        result = await arbitrage_strategy.start()
        assert result is False
        assert not arbitrage_strategy.is_operational
    
    @pytest.mark.asyncio
    async def test_stop_method(self, arbitrage_strategy):
        """Test strategy stop"""
        await arbitrage_strategy.initialize()
        await arbitrage_strategy.start()
        await arbitrage_strategy.stop()
        assert not arbitrage_strategy.is_operational
    
    @pytest.mark.asyncio
    async def test_health_check(self, arbitrage_strategy):
        """Test health check"""
        await arbitrage_strategy.initialize()
        health = await arbitrage_strategy.health_check()
        
        assert health['initialized'] is True
        assert health['operational'] is False  # Not started yet
        assert health['component_type'] == 'Strategy'
        assert 'active_opportunities' in health
    
    def test_get_status(self, arbitrage_strategy):
        """Test get status"""
        status = arbitrage_strategy.get_status()
        
        assert status['component_id'] is None
        assert status['component_type'] == 'Strategy'
        assert status['initialized'] is False
        assert status['operational'] is False


class TestArbitrageDetection:
    """Test arbitrage opportunity detection"""
    
    @pytest.mark.asyncio
    async def test_arbitrage_opportunity_detection(self, arbitrage_strategy, sample_market_data):
        """Test arbitrage opportunity detection"""
        await arbitrage_strategy.initialize()
        
        # Add market data
        arbitrage_strategy._update_market_data(sample_market_data)
        
        # Detect opportunities
        opportunities = arbitrage_strategy._detect_arbitrage_opportunities()
        
        assert isinstance(opportunities, dict)
        # Should detect opportunities for configured pairs
        for pair in arbitrage_strategy.config.arbitrage_pairs:
            pair_key = f"{pair[0]}-{pair[1]}"
            if pair_key in opportunities:
                opp = opportunities[pair_key]
                assert 'asset1' in opp
                assert 'asset2' in opp
                assert 'price_discrepancy' in opp
                assert 'confidence' in opp
    
    def test_pair_arbitrage_analysis(self, arbitrage_strategy, sample_market_data):
        """Test individual pair arbitrage analysis"""
        arbitrage_strategy._update_market_data(sample_market_data)
        
        # Test AAPL-MSFT pair
        analysis = arbitrage_strategy._analyze_pair_arbitrage('AAPL', 'MSFT')
        
        if analysis:  # If opportunity exists
            assert 'asset1' in analysis
            assert 'asset2' in analysis
            assert 'discrepancy' in analysis
            assert 'confidence' in analysis
            assert analysis['asset1'] == 'AAPL'
            assert analysis['asset2'] == 'MSFT'
    
    def test_historical_ratio_calculation(self, arbitrage_strategy, sample_market_data):
        """Test historical ratio calculation"""
        arbitrage_strategy._update_market_data(sample_market_data)
        
        ratio = arbitrage_strategy._get_historical_ratio('AAPL', 'MSFT')
        assert isinstance(ratio, float)
        assert ratio > 0
    
    def test_opportunity_validation(self, arbitrage_strategy):
        """Test opportunity validation"""
        # Valid opportunity
        valid_opportunity = {
            'asset1': 'AAPL',
            'asset2': 'MSFT',
            'discrepancy': 0.002,  # 0.2% discrepancy
            'confidence': 0.85,
            'timestamp': datetime.now()
        }
        assert arbitrage_strategy._validate_opportunity(valid_opportunity)
        
        # Invalid opportunity - low confidence
        invalid_opportunity = {
            'asset1': 'AAPL',
            'asset2': 'MSFT',
            'discrepancy': 0.002,
            'confidence': 0.3,  # Below confidence threshold (0.6)
            'timestamp': datetime.now()
        }
        assert not arbitrage_strategy._validate_opportunity(invalid_opportunity)
    
    def test_transaction_cost_estimation(self, arbitrage_strategy):
        """Test transaction cost estimation"""
        opportunity = {
            'asset1': 'AAPL',
            'asset2': 'MSFT',
            'price_discrepancy': 0.002,
            'confidence': 0.85,
            'volume': 1000
        }
        
        cost = arbitrage_strategy._estimate_transaction_cost(opportunity)
        assert isinstance(cost, float)
        assert cost >= 0


class TestSignalGeneration:
    """Test arbitrage signal generation"""
    
    @pytest.mark.asyncio
    async def test_generate_signals(self, arbitrage_strategy, sample_market_data):
        """Test signal generation"""
        await arbitrage_strategy.initialize()
        await arbitrage_strategy.start()
        
        # Generate signals
        signals = await arbitrage_strategy.generate_signals(sample_market_data)
        
        assert isinstance(signals, list)
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.signal_id is not None
            assert signal.target_quantity > 0
            assert signal.position_side in ['long', 'short']
    
    def test_create_arbitrage_signals(self, arbitrage_strategy):
        """Test arbitrage signal creation"""
        opportunity = {
            'asset1': 'AAPL',
            'asset2': 'MSFT',
            'current_ratio': 0.8,
            'historical_ratio': 0.75,
            'discrepancy': 0.002,
            'confidence': 0.85,
            'opportunity_type': ArbitrageType.PRICE_ARBITRAGE,
            'timestamp': datetime.now()
        }
        
        signals = arbitrage_strategy._create_arbitrage_signals(opportunity)
        
        assert isinstance(signals, list)
        assert len(signals) == 2  # Long and short signals
        
        for signal in signals:
            assert isinstance(signal, StrategySignal)
            assert signal.signal_id is not None
            assert signal.target_quantity > 0


class TestPositionManagement:
    """Test position management functionality"""
    
    @pytest.mark.asyncio
    async def test_position_tracking(self, arbitrage_strategy):
        """Test position tracking"""
        await arbitrage_strategy.initialize()
        
        # Test position entry tracking with proper signal structure
        signal = StrategySignal(
            signal_id="test_signal_1",
            target_quantity=100.0,
            position_side='long',
            signal_type=SignalType.BUY,
            entry_price=150.0
        )
        # Add quantity attribute that the implementation expects
        signal.quantity = signal.target_quantity
        # Add metadata that the implementation expects
        signal.metadata = {'entry_price': 150.0}
        
        # Test getting active positions (method exists)
        positions = arbitrage_strategy.get_active_positions()
        assert isinstance(positions, dict)
        
        # Initially no positions
        assert len(positions) == 0
    
    def test_position_size_calculation(self, arbitrage_strategy, sample_market_data):
        """Test position size calculation"""
        signal = StrategySignal(
            signal_id="test_signal_1",
            target_quantity=100.0,
            position_side='long',
            signal_type=SignalType.BUY,
            entry_price=150.0
        )
        # Add quantity attribute that the method expects
        signal.quantity = signal.target_quantity
        
        position_size = arbitrage_strategy.calculate_position_size(signal, sample_market_data)
        
        assert isinstance(position_size, float)
        assert position_size > 0
        assert position_size <= signal.target_quantity
    
    @pytest.mark.asyncio
    async def test_position_updates(self, arbitrage_strategy, sample_market_data):
        """Test position updates"""
        await arbitrage_strategy.initialize()
        
        # Update positions
        await arbitrage_strategy.update_positions(sample_market_data)
        
        # Check that positions were updated
        positions = arbitrage_strategy.get_active_positions()
        assert isinstance(positions, dict)


class TestPerformanceTracking:
    """Test performance tracking functionality"""
    
    def test_performance_metrics(self, arbitrage_strategy):
        """Test performance metrics tracking"""
        # Check initial metrics
        metrics = arbitrage_strategy.performance_metrics
        assert metrics.total_signals == 0
        assert metrics.successful_signals == 0
        assert metrics.failed_signals == 0
        assert metrics.win_rate == 0.0
    
    def test_arbitrage_summary(self, arbitrage_strategy):
        """Test arbitrage summary generation"""
        summary = arbitrage_strategy.get_arbitrage_summary()
        
        assert isinstance(summary, dict)
        assert 'active_opportunities' in summary
        assert 'arbitrage_pairs' in summary
        assert 'executed_arbitrages' in summary


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_data_handling(self, arbitrage_strategy):
        """Test handling of invalid market data"""
        await arbitrage_strategy.initialize()
        
        # Test with empty market data
        empty_data = {}
        signals = await arbitrage_strategy.generate_signals(empty_data)
        assert signals == []
        
        # Test with invalid data structure
        invalid_data = {'AAPL': 'invalid_data'}
        signals = await arbitrage_strategy.generate_signals(invalid_data)
        assert signals == []
    
    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self, arbitrage_strategy):
        """Test handling of insufficient data"""
        await arbitrage_strategy.initialize()
        
        # Test with insufficient data points
        insufficient_data = {
            'AAPL': pd.DataFrame({
                'close': [150.0, 151.0]  # Only 2 data points
            })
        }
        
        signals = await arbitrage_strategy.generate_signals(insufficient_data)
        assert signals == []


class TestIntegration:
    """Test integration and complete workflow"""
    
    @pytest.mark.asyncio
    async def test_strategy_lifecycle(self, arbitrage_strategy, sample_market_data):
        """Test complete strategy lifecycle"""
        # Initialize
        assert await arbitrage_strategy.initialize() is True
        assert arbitrage_strategy.is_initialized
        
        # Start
        assert await arbitrage_strategy.start() is True
        assert arbitrage_strategy.is_operational
        
        # Add market data and generate signals
        arbitrage_strategy._update_market_data(sample_market_data)
        signals = await arbitrage_strategy.generate_signals(sample_market_data)
        
        # Health check
        health = await arbitrage_strategy.health_check()
        assert health['initialized'] is True
        assert health['operational'] is True
        
        # Stop
        await arbitrage_strategy.stop()
        assert not arbitrage_strategy.is_operational
    
    @pytest.mark.asyncio
    async def test_performance_under_different_conditions(self, arbitrage_strategy):
        """Test performance under different market conditions"""
        await arbitrage_strategy.initialize()
        await arbitrage_strategy.start()
        
        # Test with high volatility data
        high_vol_data = {
            'AAPL': pd.DataFrame({
                'close': np.random.normal(150, 10, 100)  # High volatility
            })
        }
        
        signals = await arbitrage_strategy.generate_signals(high_vol_data)
        assert isinstance(signals, list)
        
        # Test with low volatility data
        low_vol_data = {
            'AAPL': pd.DataFrame({
                'close': np.full(100, 150.0) + np.random.normal(0, 0.1, 100)  # Low volatility
            })
        }
        
        signals = await arbitrage_strategy.generate_signals(low_vol_data)
        assert isinstance(signals, list)
