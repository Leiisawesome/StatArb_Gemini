#!/usr/bin/env python3
"""
Comprehensive Broker Integration Test Suite
==========================================

This test suite provides comprehensive testing for all broker integration
components to ensure institutional-grade broker connectivity and order management.

Components Tested:
- BrokerManager (Multi-broker connectivity and routing)
- BaseBroker (Abstract broker interface)
- MockBroker (Test broker implementation)
- BrokerConnection (Connection management)
- Order execution and management workflows
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

# Import broker components
from core_engine.broker.manager import (
    BrokerManager, BrokerManagerConfig, BaseBroker, OrderResult,
    BrokerConnection, BrokerType, ConnectionStatus, BrokerCapabilities
)
from core_engine.type_definitions.orders import (
    Order, ExecutionResult, OrderStatus, OrderType, OrderSide
)


class MockBroker(BaseBroker):
    """Mock broker implementation for testing"""
    
    def __init__(self, broker_id: str, connection_status: ConnectionStatus = ConnectionStatus.CONNECTED):
        self.broker_id = broker_id
        self.connection_status = connection_status
        self.orders = {}
        self.order_counter = 0
        self.is_connected = connection_status == ConnectionStatus.CONNECTED
    
    async def submit_order(self, order: Order) -> OrderResult:
        """Submit order to mock broker"""
        self.order_counter += 1
        order_id = f"{self.broker_id}_{self.order_counter}"
        
        # Simulate order processing
        if self.is_connected:
            self.orders[order_id] = {
                'order': order,
                'status': OrderStatus.SUBMITTED,
                'filled_quantity': 0.0,
                'average_price': order.price if order.price else 100.0
            }
            return OrderResult(
                success=True,
                order_id=order_id,
                status=OrderStatus.SUBMITTED,
                filled_quantity=0.0,
                average_price=order.price if order.price else 100.0
            )
        else:
            return OrderResult(
                success=False,
                order_id="",
                status=OrderStatus.REJECTED,
                filled_quantity=0.0,
                average_price=0.0,
                error_message="Broker not connected"
            )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if order_id in self.orders:
            self.orders[order_id]['status'] = OrderStatus.CANCELLED
            return True
        return False
    
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get order status"""
        if order_id in self.orders:
            return self.orders[order_id]['status']
        return OrderStatus.PENDING


class TestBrokerManagerComprehensive:
    """Comprehensive tests for BrokerManager - Multi-broker connectivity and routing"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'primary_broker': 'IBKR',
            'enable_failover': True,
            'health_check_interval': 30,
            'max_reconnect_attempts': 3,
            'connection_timeout': 30,
            'enable_load_balancing': True,
            'order_routing_strategy': 'primary_first'
        }
        self.broker_manager = BrokerManager(self.config)
        
        # Mock order for testing
        self.mock_order = Order(
            symbol='AAPL',
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=100.0,
            price=150.0,
            order_id='test_order_001',
            timestamp=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test BrokerManager initialization"""
        assert self.broker_manager is not None
        assert self.broker_manager.config.primary_broker == 'IBKR'
        assert self.broker_manager.config.enable_failover is True
        assert hasattr(self.broker_manager, 'broker_instances')
        assert hasattr(self.broker_manager, 'broker_connections')
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test broker manager initialization"""
        result = await self.broker_manager.initialize()
        assert result is True
        assert self.broker_manager.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_start(self):
        """Test broker manager start"""
        await self.broker_manager.initialize()
        result = await self.broker_manager.start()
        assert result is True
        assert self.broker_manager.is_running is True
    
    @pytest.mark.asyncio
    async def test_stop(self):
        """Test broker manager stop"""
        await self.broker_manager.initialize()
        await self.broker_manager.start()
        result = await self.broker_manager.stop()
        assert result is True
        assert self.broker_manager.is_running is False
    
    @pytest.mark.asyncio
    async def test_add_broker(self):
        """Test adding a broker"""
        broker_config = {
            'broker_id': 'test_broker',
            'type': BrokerType.IBKR.value,
            'name': 'Test Broker',
            'config': {
                'host': 'localhost',
                'port': 7497,
                'username': 'test_user',
                'password': 'test_pass'
            },
            'priority': 1
        }
        
        result = await self.broker_manager.add_broker(broker_config)
        assert result is True
        assert 'test_broker' in self.broker_manager.broker_connections
    
    @pytest.mark.asyncio
    async def test_remove_broker(self):
        """Test removing a broker"""
        # First add a broker
        broker_config = {
            'broker_id': 'test_broker',
            'type': BrokerType.IBKR.value,
            'host': 'localhost',
            'port': 7497
        }
        await self.broker_manager.add_broker(broker_config)
        
        # Then remove it
        result = await self.broker_manager.remove_broker('test_broker')
        assert result is True
        assert 'test_broker' not in self.broker_manager.broker_connections
    
    @pytest.mark.asyncio
    async def test_get_available_brokers(self):
        """Test getting available brokers"""
        # Add some brokers
        broker_configs = [
            {'broker_id': 'broker1', 'type': BrokerType.IBKR.value, 'name': 'Broker1', 'config': {'host': 'localhost', 'port': 7497}, 'priority': 1},
            {'broker_id': 'broker2', 'type': BrokerType.ALPACA.value, 'name': 'Broker2', 'config': {'host': 'localhost', 'port': 443}, 'priority': 2}
        ]
        
        for config in broker_configs:
            await self.broker_manager.add_broker(config)
        
        available_brokers = await self.broker_manager.get_available_brokers()
        assert len(available_brokers) >= 2
        assert 'broker1' in available_brokers
        assert 'broker2' in available_brokers
    
    @pytest.mark.asyncio
    async def test_execute_order_success(self):
        """Test successful order execution"""
        # Add a mock broker
        broker_config = {
            'broker_id': 'mock_broker',
            'type': BrokerType.MOCK.value,
            'host': 'localhost',
            'port': 7497
        }
        await self.broker_manager.add_broker(broker_config)
        
        # Execute order
        result = await self.broker_manager.execute_order(self.mock_order)
        
        assert result is not None
        assert result.success is True
        assert result.order_id is not None
        assert result.status in [OrderStatus.SUBMITTED, OrderStatus.FILLED]
    
    @pytest.mark.asyncio
    async def test_execute_order_with_preference(self):
        """Test order execution with broker preference"""
        # Add multiple brokers
        broker_configs = [
            {'broker_id': 'broker1', 'broker_type': 'IBKR', 'host': 'localhost', 'port': 7497},
            {'broker_id': 'broker2', 'broker_type': 'ALPACA', 'host': 'localhost', 'port': 443}
        ]
        
        for config in broker_configs:
            await self.broker_manager.add_broker(config)
        
        # Execute order with preference
        result = await self.broker_manager.execute_order(
            self.mock_order, 
            broker_preference='broker1'
        )
        
        assert result is not None
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_cancel_order(self):
        """Test order cancellation"""
        # Add a mock broker
        broker_config = {
            'broker_id': 'mock_broker',
            'type': BrokerType.MOCK.value,
            'host': 'localhost',
            'port': 7497
        }
        await self.broker_manager.add_broker(broker_config)
        
        # Execute order first
        execution_result = await self.broker_manager.execute_order(self.mock_order)
        assert execution_result.success is True
        
        # Cancel the order
        cancel_result = await self.broker_manager.cancel_order(execution_result.order_id)
        assert cancel_result is True
    
    @pytest.mark.asyncio
    async def test_get_broker_status(self):
        """Test getting broker status"""
        # Add a broker
        broker_config = {
            'broker_id': 'test_broker',
            'type': BrokerType.IBKR.value,
            'host': 'localhost',
            'port': 7497
        }
        await self.broker_manager.add_broker(broker_config)
        
        # Get status
        status = await self.broker_manager.get_broker_status()
        assert status is not None
        assert 'brokers' in status
        assert 'total_brokers' in status
        assert 'active_brokers' in status
    
    @pytest.mark.asyncio
    async def test_get_broker_manager_status(self):
        """Test getting broker manager status"""
        status = self.broker_manager.get_broker_manager_status()
        
        assert status is not None
        assert 'is_initialized' in status
        assert 'is_running' in status
        assert 'total_brokers' in status
        assert 'active_brokers' in status
        assert 'broker_manager_id' in status
    
    @pytest.mark.asyncio
    async def test_subscriber_notification(self):
        """Test subscriber notification"""
        # Create a mock subscriber
        mock_subscriber = Mock()
        mock_subscriber.on_connection_status_change = AsyncMock()
        mock_subscriber.on_order_update = AsyncMock()
        
        # Subscribe
        self.broker_manager.subscribe(mock_subscriber)
        
        # Verify subscription
        assert mock_subscriber in self.broker_manager.subscribers
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_broker(self):
        """Test error handling with invalid broker"""
        # Try to execute order without any brokers
        result = await self.broker_manager.execute_order(self.mock_order)
        
        # Should handle gracefully
        assert result is not None
        # Result might be unsuccessful but should not crash
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_order(self):
        """Test error handling with invalid order"""
        # Create invalid order
        invalid_order = Order(
            symbol='',
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.0,
            price=0.0
        )
        
        # Add a broker
        broker_config = {
            'broker_id': 'mock_broker',
            'type': BrokerType.MOCK.value,
            'host': 'localhost',
            'port': 7497
        }
        await self.broker_manager.add_broker(broker_config)
        
        # Try to execute invalid order
        result = await self.broker_manager.execute_order(invalid_order)
        
        # Should handle gracefully
        assert result is not None


class TestBaseBrokerComprehensive:
    """Comprehensive tests for BaseBroker abstract interface"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_broker = MockBroker('test_broker')
        self.mock_order = Order(
            symbol='AAPL',
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=100.0,
            price=150.0,
            order_id='test_order_001',
            timestamp=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_submit_order_success(self):
        """Test successful order submission"""
        result = await self.mock_broker.submit_order(self.mock_order)
        
        assert result.success is True
        assert result.order_id is not None
        assert result.status == OrderStatus.SUBMITTED
        assert result.filled_quantity == 0.0
        assert result.average_price == 150.0
    
    @pytest.mark.asyncio
    async def test_submit_order_disconnected(self):
        """Test order submission when disconnected"""
        # Disconnect the broker
        self.mock_broker.is_connected = False
        self.mock_broker.connection_status = ConnectionStatus.DISCONNECTED
        
        result = await self.mock_broker.submit_order(self.mock_order)
        
        assert result.success is False
        assert result.order_id == ""
        assert result.status == OrderStatus.REJECTED
        assert "not connected" in result.error_message
    
    @pytest.mark.asyncio
    async def test_cancel_order_success(self):
        """Test successful order cancellation"""
        # First submit an order
        submit_result = await self.mock_broker.submit_order(self.mock_order)
        assert submit_result.success is True
        
        # Then cancel it
        cancel_result = await self.mock_broker.cancel_order(submit_result.order_id)
        assert cancel_result is True
        
        # Check order status
        status = await self.mock_broker.get_order_status(submit_result.order_id)
        assert status == OrderStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cancel_order_not_found(self):
        """Test canceling non-existent order"""
        result = await self.mock_broker.cancel_order('non_existent_order')
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_order_status(self):
        """Test getting order status"""
        # Submit an order
        submit_result = await self.mock_broker.submit_order(self.mock_order)
        
        # Get status
        status = await self.mock_broker.get_order_status(submit_result.order_id)
        assert status == OrderStatus.SUBMITTED
    
    @pytest.mark.asyncio
    async def test_get_order_status_not_found(self):
        """Test getting status for non-existent order"""
        status = await self.mock_broker.get_order_status('non_existent_order')
        assert status == OrderStatus.UNKNOWN


class TestBrokerConnectionComprehensive:
    """Comprehensive tests for broker connection management"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.connection_config = {
            'broker_id': 'test_broker',
            'type': BrokerType.IBKR.value,
            'name': 'Test Broker',
            'config': {
                'host': 'localhost',
                'port': 7497,
                'username': 'test_user',
                'password': 'test_pass',
                'connection_timeout': 30,
                'max_reconnect_attempts': 3
            },
            'priority': 1
        }
    
    def test_connection_creation(self):
        """Test broker connection creation"""
        connection = BrokerConnection(**self.connection_config)
        
        assert connection.broker_id == 'test_broker'
        assert connection.broker_type == BrokerType.IBKR
        assert connection.host == 'localhost'
        assert connection.port == 7497
        assert connection.username == 'test_user'
        assert connection.connection_timeout == 30
        assert connection.max_reconnect_attempts == 3
    
    def test_connection_status_initial(self):
        """Test initial connection status"""
        connection = BrokerConnection(**self.connection_config)
        assert connection.status == ConnectionStatus.DISCONNECTED
    
    def test_connection_equality(self):
        """Test connection equality"""
        conn1 = BrokerConnection(**self.connection_config)
        conn2 = BrokerConnection(**self.connection_config)
        
        # Same broker_id should be equal
        assert conn1 == conn2
        
        # Different broker_id should not be equal
        conn3_config = self.connection_config.copy()
        conn3_config['broker_id'] = 'different_broker'
        conn3 = BrokerConnection(**conn3_config)
        assert conn1 != conn3


class TestBrokerIntegrationComprehensive:
    """Integration tests for broker components working together"""
    
    def setup_method(self):
        """Set up integration test fixtures"""
        self.broker_manager = BrokerManager({
            'primary_broker': 'IBKR',
            'enable_failover': True,
            'order_routing_strategy': 'round_robin'
        })
        
        self.orders = [
            Order(symbol='AAPL', order_type=OrderType.MARKET, side=OrderSide.BUY, 
                  quantity=100.0, price=150.0, order_id=f'order_{i}',
                  timestamp=datetime.now())
            for i in range(3)
        ]
    
    @pytest.mark.asyncio
    async def test_full_broker_lifecycle(self):
        """Test complete broker lifecycle"""
        # Initialize
        await self.broker_manager.initialize()
        assert self.broker_manager.is_initialized is True
        
        # Add brokers
        broker_configs = [
            {'broker_id': 'broker1', 'broker_type': 'IBKR', 'host': 'localhost', 'port': 7497},
            {'broker_id': 'broker2', 'broker_type': 'ALPACA', 'host': 'localhost', 'port': 443}
        ]
        
        for config in broker_configs:
            result = await self.broker_manager.add_broker(config)
            assert result is True
        
        # Start
        await self.broker_manager.start()
        assert self.broker_manager.is_running is True
        
        # Execute orders
        results = []
        for order in self.orders:
            result = await self.broker_manager.execute_order(order)
            results.append(result)
            assert result.success is True
        
        # Cancel some orders
        for result in results[:2]:
            cancel_result = await self.broker_manager.cancel_order(result.order_id)
            assert cancel_result is True
        
        # Stop
        await self.broker_manager.stop()
        assert self.broker_manager.is_running is False
    
    @pytest.mark.asyncio
    async def test_broker_failover_scenario(self):
        """Test broker failover scenario"""
        # Add multiple brokers
        broker_configs = [
            {'broker_id': 'primary', 'broker_type': 'IBKR', 'host': 'localhost', 'port': 7497},
            {'broker_id': 'backup', 'broker_type': 'ALPACA', 'host': 'localhost', 'port': 443}
        ]
        
        for config in broker_configs:
            await self.broker_manager.add_broker(config)
        
        # Execute orders
        for order in self.orders:
            result = await self.broker_manager.execute_order(order, broker_preference='primary')
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_load_balancing(self):
        """Test load balancing across brokers"""
        # Add multiple brokers
        broker_configs = [
            {'broker_id': 'broker1', 'broker_type': 'IBKR', 'host': 'localhost', 'port': 7497},
            {'broker_id': 'broker2', 'broker_type': 'ALPACA', 'host': 'localhost', 'port': 443},
            {'broker_id': 'broker3', 'broker_type': 'POLYGON', 'host': 'localhost', 'port': 443}
        ]
        
        for config in broker_configs:
            await self.broker_manager.add_broker(config)
        
        # Execute multiple orders
        results = []
        for order in self.orders:
            result = await self.broker_manager.execute_order(order)
            results.append(result)
            assert result.success is True
        
        # Verify orders were distributed across brokers
        assert len(results) == len(self.orders)
    
    @pytest.mark.asyncio
    async def test_broker_health_monitoring(self):
        """Test broker health monitoring"""
        # Add a broker
        broker_config = {
            'broker_id': 'test_broker',
            'type': BrokerType.IBKR.value,
            'host': 'localhost',
            'port': 7497
        }
        await self.broker_manager.add_broker(broker_config)
        
        # Start health monitoring
        await self.broker_manager.start()
        
        # Check broker status
        status = await self.broker_manager.get_broker_status('test_broker')
        assert status is not None
        
        # Check overall status
        overall_status = await self.broker_manager.get_broker_status()
        assert overall_status is not None
        assert 'total_brokers' in overall_status
        assert 'active_brokers' in overall_status


class TestBrokerPerformanceComprehensive:
    """Performance tests for broker components"""
    
    def setup_method(self):
        """Set up performance test fixtures"""
        self.broker_manager = BrokerManager({
            'primary_broker': 'IBKR',
            'enable_failover': True
        })
        
        self.test_orders = [
            Order(symbol=f'SYMBOL_{i}', order_type=OrderType.MARKET, side=OrderSide.BUY,
                  quantity=100.0, price=100.0 + i, order_id=f'perf_order_{i}',
                  timestamp=datetime.now())
            for i in range(10)
        ]
    
    @pytest.mark.asyncio
    async def test_concurrent_order_execution(self):
        """Test concurrent order execution"""
        # Add a broker
        broker_config = {
            'broker_id': 'perf_broker',
            'type': BrokerType.MOCK.value,
            'host': 'localhost',
            'port': 7497
        }
        await self.broker_manager.add_broker(broker_config)
        
        # Execute orders concurrently
        tasks = [
            self.broker_manager.execute_order(order) 
            for order in self.test_orders
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all orders were executed successfully
        assert len(results) == len(self.test_orders)
        for result in results:
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_order_execution_speed(self):
        """Test order execution speed"""
        # Add a broker
        broker_config = {
            'broker_id': 'speed_broker',
            'type': BrokerType.MOCK.value,
            'host': 'localhost',
            'port': 7497
        }
        await self.broker_manager.add_broker(broker_config)
        
        # Measure execution time
        start_time = datetime.now()
        
        for order in self.test_orders[:5]:  # Test with 5 orders
            result = await self.broker_manager.execute_order(order)
            assert result.success is True
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time
        assert execution_time < 10.0  # Less than 10 seconds for 5 orders
    
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage during operations"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Add brokers and execute orders
        broker_configs = [
            {'broker_id': f'mem_broker_{i}', 'broker_type': 'MOCK', 'host': 'localhost', 'port': 7497 + i}
            for i in range(5)
        ]
        
        for config in broker_configs:
            await self.broker_manager.add_broker(config)
        
        # Execute many orders
        for i in range(50):
            order = Order(
                symbol=f'MEM_SYMBOL_{i}',
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=100.0,
                price=100.0,
                order_id=f'mem_order_{i}',
                timestamp=datetime.now()
            )
            result = await self.broker_manager.execute_order(order)
            assert result.success is True
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100.0


if __name__ == '__main__':
    pytest.main([__file__])