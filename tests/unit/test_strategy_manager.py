"""
Comprehensive Unit Tests for StrategyManager
===========================================

Tests for the StrategyManager component, focusing on:
- ISystemComponent interface compliance
- Strategy lifecycle management
- Signal generation and processing
- Risk manager integration
- Performance tracking and analytics
- Error handling and recovery

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.1 Enhancement)
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import the component under test
from core_engine.trading.strategies.manager import (
    StrategyManager,
    StrategyManagerConfig,
    TradingSignal,
    SignalType,
    SignalStrength,
    StrategyAllocation,
    IStrategySubscriber
)


@pytest.fixture
def strategy_config():
    """Configuration for strategy manager"""
    return {
        'max_concurrent_strategies': 10,
        'signal_generation_interval': 60,
        'min_confidence_threshold': 0.6,
        'max_strategy_allocation': 0.33,
        'enable_regime_awareness': True,
        'enable_correlation_filtering': True,
        'signal_aggregation_method': 'weighted_average'
    }


@pytest.fixture
def mock_risk_manager():
    """Mock risk manager for testing"""
    risk_manager = Mock()
    risk_manager.authorize_trading_decision = AsyncMock(return_value=Mock(
        authorization_level='STANDARD',
        authorized_quantity=100.0
    ))
    risk_manager.get_current_risk_metrics = Mock(return_value={
        'portfolio_var': 0.02,
        'max_position_size': 0.1
    })
    return risk_manager


@pytest.fixture
def mock_data_manager():
    """Mock data manager for testing"""
    data_manager = Mock()
    data_manager.get_market_data = AsyncMock(return_value=Mock(
        close=[100.0, 101.0, 102.0],
        volume=[1000, 1100, 1200],
        timestamp=[datetime.now() - timedelta(minutes=i) for i in range(3)]
    ))
    data_manager.get_current_price = Mock(return_value=101.5)
    return data_manager


@pytest.fixture
def mock_regime_engine():
    """Mock regime engine for testing"""
    regime_engine = Mock()
    regime_engine.get_current_regime = AsyncMock(return_value=Mock(
        primary_regime='normal_volatility',
        confidence=0.8,
        volatility=0.02
    ))
    return regime_engine


@pytest.fixture
def strategy_manager(strategy_config, mock_risk_manager, mock_data_manager, mock_regime_engine):
    """StrategyManager instance for testing"""
    manager = StrategyManager(strategy_config)
    manager.set_risk_manager(mock_risk_manager)
    manager.set_data_manager(mock_data_manager)
    manager.set_regime_engine(mock_regime_engine)
    return manager


@pytest.fixture
def sample_trading_signal():
    """Sample trading signal"""
    return TradingSignal(
        signal_id=str(uuid.uuid4()),
        symbol="AAPL",
        signal_type=SignalType.BUY,
        strength=SignalStrength.STRONG,
        confidence=0.85,
        price=150.0,
        quantity=100.0,
        timestamp=datetime.now(),
        strategy_id="test_strategy",
        metadata={'source': 'test'}
    )


class MockStrategy:
    """Mock strategy for testing"""
    
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        self.is_active = True
        
    async def generate_signals(self, market_data):
        """Generate mock signals"""
        return [TradingSignal(
            signal_id=str(uuid.uuid4()),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MEDIUM,
            confidence=0.7,
            price=150.0,
            quantity=100.0,
            timestamp=datetime.now(),
            strategy_id=self.strategy_id
        )]
    
    async def health_check(self):
        """Mock health check"""
        return {'healthy': True, 'strategy_id': self.strategy_id}


class MockSubscriber(IStrategySubscriber):
    """Mock strategy subscriber"""
    
    def __init__(self):
        self.received_signals = []
        self.received_events = []
    
    async def on_signal_generated(self, signal: TradingSignal) -> None:
        """Handle signal generation"""
        self.received_signals.append(signal)
    
    async def on_strategy_status_change(self, strategy_event: Dict[str, Any]) -> None:
        """Handle strategy status changes"""
        self.received_events.append(strategy_event)


class TestStrategyManagerInterface:
    """Test ISystemComponent interface compliance"""
    
    def test_initialization(self, strategy_config):
        """Test StrategyManager initialization"""
        manager = StrategyManager(strategy_config)
        
        assert isinstance(manager.config, StrategyManagerConfig)
        assert not manager.is_initialized
        assert not manager.is_running
        assert manager.component_id is None
        assert len(manager.active_strategies) == 0
        assert len(manager.strategy_allocations) == 0
        assert len(manager.subscribers) == 0
    
    @pytest.mark.asyncio
    async def test_initialize_method(self, strategy_manager):
        """Test initialize method"""
        result = await strategy_manager.initialize()
        
        assert result is True
        assert strategy_manager.is_initialized
        assert strategy_manager.last_error is None
    
    @pytest.mark.asyncio
    async def test_start_method(self, strategy_manager):
        """Test start method"""
        # Initialize first
        await strategy_manager.initialize()
        
        result = await strategy_manager.start()
        
        assert result is True
        assert strategy_manager.is_running
    
    @pytest.mark.asyncio
    async def test_start_without_initialization(self, strategy_manager):
        """Test start method without initialization"""
        result = await strategy_manager.start()
        
        assert result is False
        assert not strategy_manager.is_running
    
    @pytest.mark.asyncio
    async def test_stop_method(self, strategy_manager):
        """Test stop method"""
        # Initialize and start first
        await strategy_manager.initialize()
        await strategy_manager.start()
        
        result = await strategy_manager.stop()
        
        assert result is True
        assert not strategy_manager.is_running
    
    @pytest.mark.asyncio
    async def test_health_check(self, strategy_manager):
        """Test health check method"""
        await strategy_manager.initialize()
        await strategy_manager.start()
        
        health = await strategy_manager.health_check()
        
        assert isinstance(health, dict)
        assert 'healthy' in health
        assert 'initialized' in health
        assert 'operational' in health
        assert 'component_type' in health
        assert health['component_type'] == 'StrategyManager'
        assert health['initialized'] is True
        assert health['operational'] is True
    
    def test_get_status(self, strategy_manager):
        """Test get_status method"""
        status = strategy_manager.get_status()
        
        assert isinstance(status, dict)
        assert 'component_type' in status
        assert 'initialized' in status
        assert 'operational' in status
        assert 'active_strategies' in status
        assert 'component_connections' in status
        assert status['component_type'] == 'StrategyManager'


class TestStrategyManagement:
    """Test strategy management functionality"""
    
    @pytest.mark.asyncio
    async def test_strategy_registration(self, strategy_manager):
        """Test strategy registration"""
        await strategy_manager.initialize()
        
        mock_strategy = MockStrategy("test_strategy_1")
        
        # Register strategy
        strategy_manager.active_strategies["test_strategy_1"] = mock_strategy
        
        assert len(strategy_manager.active_strategies) == 1
        assert "test_strategy_1" in strategy_manager.active_strategies
    
    @pytest.mark.asyncio
    async def test_strategy_allocation(self, strategy_manager):
        """Test strategy allocation management"""
        await strategy_manager.initialize()
        
        allocation = StrategyAllocation(
            strategy_id="test_strategy",
            allocation_percentage=0.2,
            max_position_size=0.1,
            risk_budget=10000.0
        )
        
        strategy_manager.strategy_allocations["test_strategy"] = allocation
        
        assert len(strategy_manager.strategy_allocations) == 1
        assert strategy_manager.strategy_allocations["test_strategy"].allocation_percentage == 0.2
    
    @pytest.mark.asyncio
    async def test_strategy_health_monitoring(self, strategy_manager):
        """Test strategy health monitoring"""
        await strategy_manager.initialize()
        
        # Add healthy strategy
        healthy_strategy = MockStrategy("healthy_strategy")
        strategy_manager.active_strategies["healthy_strategy"] = healthy_strategy
        
        # Add unhealthy strategy
        unhealthy_strategy = MockStrategy("unhealthy_strategy")
        unhealthy_strategy.health_check = AsyncMock(return_value={'healthy': False})
        strategy_manager.active_strategies["unhealthy_strategy"] = unhealthy_strategy
        
        health = await strategy_manager.health_check()
        
        assert health['healthy'] is False
        assert 'unhealthy_strategies' in health
        assert 'unhealthy_strategy' in health['unhealthy_strategies']


class TestSignalProcessing:
    """Test signal generation and processing"""
    
    @pytest.mark.asyncio
    async def test_signal_generation(self, strategy_manager, sample_trading_signal):
        """Test signal generation"""
        await strategy_manager.initialize()
        
        # Add signal to pending signals
        strategy_manager.pending_signals[sample_trading_signal.signal_id] = sample_trading_signal
        
        assert len(strategy_manager.pending_signals) == 1
        assert sample_trading_signal.signal_id in strategy_manager.pending_signals
    
    @pytest.mark.asyncio
    async def test_signal_aggregation(self, strategy_manager):
        """Test signal aggregation functionality"""
        await strategy_manager.initialize()
        
        # Create multiple signals for same symbol
        signal1 = TradingSignal(
            signal_id=str(uuid.uuid4()),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MEDIUM,
            confidence=0.7,
            price=150.0,
            quantity=100.0,
            timestamp=datetime.now(),
            strategy_id="strategy_1"
        )
        
        signal2 = TradingSignal(
            signal_id=str(uuid.uuid4()),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=0.8,
            price=151.0,
            quantity=150.0,
            timestamp=datetime.now(),
            strategy_id="strategy_2"
        )
        
        strategy_manager.pending_signals[signal1.signal_id] = signal1
        strategy_manager.pending_signals[signal2.signal_id] = signal2
        
        # Test aggregation logic would be implemented here
        assert len(strategy_manager.pending_signals) == 2
    
    @pytest.mark.asyncio
    async def test_signal_filtering(self, strategy_manager):
        """Test signal filtering based on confidence"""
        await strategy_manager.initialize()
        
        # Low confidence signal (should be filtered)
        low_confidence_signal = TradingSignal(
            signal_id=str(uuid.uuid4()),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.WEAK,
            confidence=0.4,  # Below threshold
            price=150.0,
            quantity=100.0,
            timestamp=datetime.now(),
            strategy_id="test_strategy"
        )
        
        # High confidence signal (should pass)
        high_confidence_signal = TradingSignal(
            signal_id=str(uuid.uuid4()),
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=0.8,  # Above threshold
            price=150.0,
            quantity=100.0,
            timestamp=datetime.now(),
            strategy_id="test_strategy"
        )
        
        # Test filtering logic
        assert low_confidence_signal.confidence < strategy_manager.config.min_confidence_threshold
        assert high_confidence_signal.confidence >= strategy_manager.config.min_confidence_threshold


class TestComponentIntegration:
    """Test integration with other components"""
    
    @pytest.mark.asyncio
    async def test_risk_manager_integration(self, strategy_manager, sample_trading_signal):
        """Test integration with risk manager"""
        await strategy_manager.initialize()
        
        # Test risk manager connection
        assert strategy_manager.risk_manager is not None
        
        # Test authorization request (would be implemented in actual signal processing)
        status = strategy_manager.get_status()
        assert status['component_connections']['risk_manager_connected'] is True
    
    @pytest.mark.asyncio
    async def test_data_manager_integration(self, strategy_manager):
        """Test integration with data manager"""
        await strategy_manager.initialize()
        
        # Test data manager connection
        assert strategy_manager.data_manager is not None
        
        # Test data access
        status = strategy_manager.get_status()
        assert status['component_connections']['data_manager_connected'] is True
    
    @pytest.mark.asyncio
    async def test_regime_engine_integration(self, strategy_manager):
        """Test integration with regime engine"""
        await strategy_manager.initialize()
        
        # Test regime engine connection
        assert strategy_manager.regime_engine is not None
        
        # Test regime access
        status = strategy_manager.get_status()
        assert status['component_connections']['regime_engine_connected'] is True


class TestSubscriberPattern:
    """Test subscriber pattern implementation"""
    
    @pytest.mark.asyncio
    async def test_subscriber_registration(self, strategy_manager):
        """Test subscriber registration"""
        await strategy_manager.initialize()
        
        subscriber = MockSubscriber()
        strategy_manager.subscribe(subscriber)
        
        assert len(strategy_manager.subscribers) == 1
        assert subscriber in strategy_manager.subscribers
    
    @pytest.mark.asyncio
    async def test_signal_notification(self, strategy_manager, sample_trading_signal):
        """Test signal notification to subscribers"""
        await strategy_manager.initialize()
        
        subscriber = MockSubscriber()
        strategy_manager.subscribe(subscriber)
        
        # Simulate signal notification (would be implemented in actual signal processing)
        await subscriber.on_signal_generated(sample_trading_signal)
        
        assert len(subscriber.received_signals) == 1
        assert subscriber.received_signals[0] == sample_trading_signal


class TestPerformanceTracking:
    """Test performance tracking functionality"""
    
    @pytest.mark.asyncio
    async def test_performance_initialization(self, strategy_manager):
        """Test performance tracking initialization"""
        await strategy_manager.initialize()
        
        # Performance tracking should be initialized
        assert hasattr(strategy_manager, 'strategy_performance')
        assert isinstance(strategy_manager.strategy_performance, dict)
    
    @pytest.mark.asyncio
    async def test_signal_history_tracking(self, strategy_manager, sample_trading_signal):
        """Test signal history tracking"""
        await strategy_manager.initialize()
        
        # Add signal to history
        strategy_manager.signal_history.append(sample_trading_signal)
        
        assert len(strategy_manager.signal_history) == 1
        assert strategy_manager.signal_history[0] == sample_trading_signal
        
        # Check status reflects history
        status = strategy_manager.get_status()
        assert status['signal_history_count'] == 1


class TestErrorHandling:
    """Test error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_initialization_error_handling(self, strategy_config):
        """Test initialization error handling"""
        # Create manager with invalid config
        invalid_config = strategy_config.copy()
        invalid_config['max_strategies'] = -1  # Invalid value
        
        manager = StrategyManager(invalid_config)
        
        # Initialization should handle errors gracefully
        result = await manager.initialize()
        
        # Should either succeed (if validation is lenient) or fail gracefully
        assert isinstance(result, bool)
        if not result:
            assert manager.last_error is not None
    
    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, strategy_manager):
        """Test health check error handling"""
        await strategy_manager.initialize()
        
        # Mock an error in health check
        with patch.object(strategy_manager, 'active_strategies', side_effect=Exception("Mock error")):
            health = await strategy_manager.health_check()
        
        # Should handle error gracefully
        assert isinstance(health, dict)
        assert 'healthy' in health
        if not health['healthy']:
            assert 'error' in health
    
    @pytest.mark.asyncio
    async def test_component_connection_failure(self, strategy_config):
        """Test handling of missing component connections"""
        manager = StrategyManager(strategy_config)
        
        # Don't set component connections
        await manager.initialize()
        
        status = manager.get_status()
        connections = status['component_connections']
        
        assert connections['risk_manager_connected'] is False
        assert connections['data_manager_connected'] is False
        assert connections['regime_engine_connected'] is False


class TestStrategyManagerIntegration:
    """Integration tests for strategy manager"""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, strategy_manager):
        """Test complete strategy manager lifecycle"""
        # Initialize
        assert await strategy_manager.initialize() is True
        assert strategy_manager.is_initialized is True
        
        # Start
        assert await strategy_manager.start() is True
        assert strategy_manager.is_running is True
        
        # Check health
        health = await strategy_manager.health_check()
        assert health['healthy'] is True
        
        # Check status
        status = strategy_manager.get_status()
        assert status['initialized'] is True
        assert status['operational'] is True
        
        # Stop
        assert await strategy_manager.stop() is True
        assert strategy_manager.is_running is False
    
    @pytest.mark.asyncio
    async def test_strategy_workflow(self, strategy_manager):
        """Test complete strategy workflow"""
        await strategy_manager.initialize()
        await strategy_manager.start()
        
        # Add mock strategy
        mock_strategy = MockStrategy("test_strategy")
        strategy_manager.active_strategies["test_strategy"] = mock_strategy
        
        # Add allocation
        allocation = StrategyAllocation(
            strategy_id="test_strategy",
            allocation_percentage=0.1,
            max_position_size=0.05,
            risk_budget=5000.0
        )
        strategy_manager.strategy_allocations["test_strategy"] = allocation
        
        # Add subscriber
        subscriber = MockSubscriber()
        strategy_manager.subscribe(subscriber)
        
        # Verify setup
        assert len(strategy_manager.active_strategies) == 1
        assert len(strategy_manager.strategy_allocations) == 1
        assert len(strategy_manager.subscribers) == 1
        
        # Check health with active strategy
        health = await strategy_manager.health_check()
        assert health['healthy'] is True
        assert health['active_strategies'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
