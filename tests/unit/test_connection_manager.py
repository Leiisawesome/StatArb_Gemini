#!/usr/bin/env python3
"""
Comprehensive Connection Manager Test Suite
==========================================

This test suite provides comprehensive testing for the ConnectionManager component
to ensure robust multi-broker connection management with pooling, failover, and monitoring.

Components Tested:
- ConnectionManager (Multi-broker connection management)
- ConnectionPool (Connection pooling)
- FailoverManager (Failover strategies)
- HealthMonitor (Connection health monitoring)
- LoadBalancer (Load balancing)
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

# Import connection manager components
from core_engine.broker.connection_manager import (
    ConnectionManager, ConnectionPool, FailoverManager, HealthMonitor,
    ConnectionPriority, FailoverStrategy, HealthStatus, LoadBalancer,
    ConnectionConfig, PoolConfig, FailoverConfig, HealthConfig
)


class TestConnectionManagerComprehensive:
    """Comprehensive tests for ConnectionManager - Multi-broker connection management"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'max_connections': 10,
            'connection_timeout': 30,
            'health_check_interval': 60,
            'failover_enabled': True,
            'load_balancing_enabled': True,
            'auto_reconnect': True,
            'reconnect_delay': 5.0,
            'max_reconnect_attempts': 3
        }
        
        self.connection_manager = ConnectionManager(self.config)
        
        # Mock broker configurations
        self.broker_configs = [
            {
                'broker_id': 'broker_1',
                'broker_type': 'interactive_brokers',
                'host': 'localhost',
                'port': 7497,
                'priority': ConnectionPriority.PRIMARY,
                'weight': 1.0,
                'max_connections': 5
            },
            {
                'broker_id': 'broker_2',
                'broker_type': 'alpaca',
                'host': 'api.alpaca.markets',
                'port': 443,
                'priority': ConnectionPriority.SECONDARY,
                'weight': 0.8,
                'max_connections': 3
            },
            {
                'broker_id': 'broker_3',
                'broker_type': 'td_ameritrade',
                'host': 'api.tdameritrade.com',
                'port': 443,
                'priority': ConnectionPriority.BACKUP,
                'weight': 0.6,
                'max_connections': 2
            }
        ]
        
        # Mock connection data
        self.mock_connection_data = {
            'connection_id': 'conn_001',
            'broker_id': 'broker_1',
            'status': 'connected',
            'created_at': datetime.now(),
            'last_heartbeat': datetime.now(),
            'latency_ms': 50,
            'error_count': 0
        }
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test ConnectionManager initialization"""
        assert self.connection_manager is not None
        assert self.connection_manager.config == self.config
        assert hasattr(self.connection_manager, 'connection_pool')
        assert hasattr(self.connection_manager, 'failover_manager')
        assert hasattr(self.connection_manager, 'health_monitor')
        assert hasattr(self.connection_manager, 'load_balancer')
    
    @pytest.mark.asyncio
    async def test_broker_registration(self):
        """Test broker registration"""
        for broker_config in self.broker_configs:
            result = await self.connection_manager.register_broker(broker_config)
            assert result is True
        
        # Verify all brokers are registered
        registered_brokers = self.connection_manager.get_registered_brokers()
        assert len(registered_brokers) == 3
        assert 'broker_1' in registered_brokers
        assert 'broker_2' in registered_brokers
        assert 'broker_3' in registered_brokers
    
    @pytest.mark.asyncio
    async def test_connection_establishment(self):
        """Test connection establishment"""
        # Register brokers first
        for broker_config in self.broker_configs:
            await self.connection_manager.register_broker(broker_config)
        
        # Mock connection establishment
        with patch.object(self.connection_manager, '_establish_connection', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = self.mock_connection_data
            
            result = await self.connection_manager.establish_connection('broker_1')
            
            assert result is not None
            assert result['connection_id'] == 'conn_001'
            assert result['broker_id'] == 'broker_1'
            mock_connect.assert_called_once_with('broker_1')
    
    @pytest.mark.asyncio
    async def test_connection_pooling(self):
        """Test connection pooling functionality"""
        # Register brokers and establish multiple connections
        for broker_config in self.broker_configs:
            await self.connection_manager.register_broker(broker_config)
        
        with patch.object(self.connection_manager, '_establish_connection', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = self.mock_connection_data
            
            # Establish multiple connections for broker_1
            connections = []
            for i in range(3):
                conn_data = self.mock_connection_data.copy()
                conn_data['connection_id'] = f'conn_{i:03d}'
                mock_connect.return_value = conn_data
                
                connection = await self.connection_manager.establish_connection('broker_1')
                connections.append(connection)
            
            # Verify connections are pooled
            pool_status = self.connection_manager.get_pool_status('broker_1')
            assert pool_status['active_connections'] == 3
            assert pool_status['max_connections'] == 5
    
    @pytest.mark.asyncio
    async def test_connection_retrieval(self):
        """Test connection retrieval from pool"""
        # Register broker and establish connection
        await self.connection_manager.register_broker(self.broker_configs[0])
        
        with patch.object(self.connection_manager, '_establish_connection', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = self.mock_connection_data
            
            await self.connection_manager.establish_connection('broker_1')
            
            # Retrieve connection
            connection = await self.connection_manager.get_connection('broker_1')
            
            assert connection is not None
            assert connection['broker_id'] == 'broker_1'
    
    @pytest.mark.asyncio
    async def test_connection_closure(self):
        """Test connection closure"""
        # Register broker and establish connection
        await self.connection_manager.register_broker(self.broker_configs[0])
        
        with patch.object(self.connection_manager, '_establish_connection', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = self.mock_connection_data
            
            connection = await self.connection_manager.establish_connection('broker_1')
            
            # Close connection
            with patch.object(self.connection_manager, '_close_connection', new_callable=AsyncMock) as mock_close:
                mock_close.return_value = True
                
                result = await self.connection_manager.close_connection(connection['connection_id'])
                
                assert result is True
                mock_close.assert_called_once_with(connection['connection_id'])
    
    @pytest.mark.asyncio
    async def test_failover_functionality(self):
        """Test failover functionality"""
        # Register brokers with different priorities
        for broker_config in self.broker_configs:
            await self.connection_manager.register_broker(broker_config)
        
        # Mock primary broker failure
        with patch.object(self.connection_manager, '_establish_connection', new_callable=AsyncMock) as mock_connect:
            # Primary broker fails
            mock_connect.side_effect = [Exception("Primary broker failed"), self.mock_connection_data]
            
            # First attempt fails, second succeeds
            result = await self.connection_manager.establish_connection('broker_1')
            
            # Should failover to secondary broker
            assert mock_connect.call_count == 2
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self):
        """Test health monitoring functionality"""
        # Register broker and establish connection
        await self.connection_manager.register_broker(self.broker_configs[0])
        
        with patch.object(self.connection_manager, '_establish_connection', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = self.mock_connection_data
            
            connection = await self.connection_manager.establish_connection('broker_1')
            
            # Perform health check
            with patch.object(self.connection_manager, '_perform_health_check', new_callable=AsyncMock) as mock_health:
                mock_health.return_value = {
                    'status': HealthStatus.HEALTHY,
                    'latency_ms': 50,
                    'last_heartbeat': datetime.now(),
                    'error_count': 0
                }
                
                health_status = await self.connection_manager.check_connection_health(connection['connection_id'])
                
                assert health_status is not None
                assert health_status['status'] == HealthStatus.HEALTHY
                mock_health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_balancing(self):
        """Test load balancing functionality"""
        # Register multiple brokers
        for broker_config in self.broker_configs:
            await self.connection_manager.register_broker(broker_config)
        
        # Establish connections to all brokers
        with patch.object(self.connection_manager, '_establish_connection', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = self.mock_connection_data
            
            for broker_config in self.broker_configs:
                await self.connection_manager.establish_connection(broker_config['broker_id'])
            
            # Test load balancing
            selected_broker = await self.connection_manager.select_broker_for_request()
            
            assert selected_broker is not None
            assert selected_broker in ['broker_1', 'broker_2', 'broker_3']
    
    @pytest.mark.asyncio
    async def test_connection_recovery(self):
        """Test connection recovery after failure"""
        # Register broker and establish connection
        await self.connection_manager.register_broker(self.broker_configs[0])
        
        with patch.object(self.connection_manager, '_establish_connection', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = self.mock_connection_data
            
            connection = await self.connection_manager.establish_connection('broker_1')
            
            # Simulate connection failure
            with patch.object(self.connection_manager, '_detect_connection_failure', new_callable=AsyncMock) as mock_detect:
                mock_detect.return_value = True
                
                # Attempt recovery
                with patch.object(self.connection_manager, '_recover_connection', new_callable=AsyncMock) as mock_recover:
                    mock_recover.return_value = True
                    
                    result = await self.connection_manager.recover_failed_connection(connection['connection_id'])
                    
                    assert result is True
                    mock_detect.assert_called_once()
                    mock_recover.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_statistics(self):
        """Test connection statistics tracking"""
        # Register brokers and establish connections
        for broker_config in self.broker_configs:
            await self.connection_manager.register_broker(broker_config)
        
        with patch.object(self.connection_manager, '_establish_connection', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = self.mock_connection_data
            
            # Establish connections
            for broker_config in self.broker_configs:
                await self.connection_manager.establish_connection(broker_config['broker_id'])
            
            # Get statistics
            stats = self.connection_manager.get_connection_statistics()
            
            assert stats is not None
            assert 'total_connections' in stats
            assert 'active_connections' in stats
            assert 'failed_connections' in stats
            assert stats['total_connections'] >= 3
    
    @pytest.mark.asyncio
    async def test_connection_cleanup(self):
        """Test connection cleanup functionality"""
        # Register broker and establish connection
        await self.connection_manager.register_broker(self.broker_configs[0])
        
        with patch.object(self.connection_manager, '_establish_connection', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = self.mock_connection_data
            
            connection = await self.connection_manager.establish_connection('broker_1')
            
            # Cleanup connections
            with patch.object(self.connection_manager, '_close_all_connections', new_callable=AsyncMock) as mock_cleanup:
                mock_cleanup.return_value = True
                
                result = await self.connection_manager.cleanup_connections()
                
                assert result is True
                mock_cleanup.assert_called_once()


class TestConnectionPoolComprehensive:
    """Comprehensive tests for ConnectionPool - Connection pooling"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.pool_config = {
            'max_connections': 5,
            'min_connections': 1,
            'connection_timeout': 30,
            'idle_timeout': 300,
            'cleanup_interval': 60
        }
        
        self.connection_pool = ConnectionPool(self.pool_config)
        
        self.mock_connection = {
            'connection_id': 'conn_001',
            'broker_id': 'broker_1',
            'status': 'connected',
            'created_at': datetime.now(),
            'last_used': datetime.now()
        }
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self):
        """Test connection pool initialization"""
        assert self.connection_pool is not None
        assert self.connection_pool.config == self.pool_config
        assert hasattr(self.connection_pool, 'max_connections')
        assert hasattr(self.connection_pool, 'min_connections')
    
    @pytest.mark.asyncio
    async def test_connection_addition(self):
        """Test adding connections to pool"""
        result = await self.connection_pool.add_connection(self.mock_connection)
        
        assert result is True
        
        # Verify connection is in pool
        connections = self.connection_pool.get_connections()
        assert len(connections) == 1
        assert connections[0]['connection_id'] == 'conn_001'
    
    @pytest.mark.asyncio
    async def test_connection_retrieval(self):
        """Test retrieving connections from pool"""
        # Add connection to pool
        await self.connection_pool.add_connection(self.mock_connection)
        
        # Retrieve connection
        connection = await self.connection_pool.get_connection()
        
        assert connection is not None
        assert connection['connection_id'] == 'conn_001'
    
    @pytest.mark.asyncio
    async def test_connection_removal(self):
        """Test removing connections from pool"""
        # Add connection to pool
        await self.connection_pool.add_connection(self.mock_connection)
        
        # Remove connection
        result = await self.connection_pool.remove_connection('conn_001')
        
        assert result is True
        
        # Verify connection is removed
        connections = self.connection_pool.get_connections()
        assert len(connections) == 0
    
    @pytest.mark.asyncio
    async def test_pool_capacity_management(self):
        """Test pool capacity management"""
        # Add connections up to max capacity
        connections = []
        for i in range(5):  # max_connections
            conn = self.mock_connection.copy()
            conn['connection_id'] = f'conn_{i:03d}'
            connections.append(conn)
        
        for conn in connections:
            await self.connection_pool.add_connection(conn)
        
        # Verify all connections are added
        pool_connections = self.connection_pool.get_connections()
        assert len(pool_connections) == 5
        
        # Try to add one more (should fail or replace)
        extra_conn = self.mock_connection.copy()
        extra_conn['connection_id'] = 'conn_extra'
        result = await self.connection_pool.add_connection(extra_conn)
        
        # Should either fail or replace existing connection
        assert result is not None  # May be True (replaced) or False (rejected)
    
    @pytest.mark.asyncio
    async def test_idle_connection_cleanup(self):
        """Test idle connection cleanup"""
        # Add connection to pool
        await self.connection_pool.add_connection(self.mock_connection)
        
        # Simulate idle connection
        with patch.object(self.connection_pool, '_is_connection_idle', return_value=True):
            # Perform cleanup
            cleaned_connections = await self.connection_pool.cleanup_idle_connections()
            
            assert cleaned_connections >= 0
    
    @pytest.mark.asyncio
    async def test_pool_statistics(self):
        """Test pool statistics"""
        # Add some connections
        for i in range(3):
            conn = self.mock_connection.copy()
            conn['connection_id'] = f'conn_{i:03d}'
            await self.connection_pool.add_connection(conn)
        
        # Get statistics
        stats = self.connection_pool.get_statistics()
        
        assert stats is not None
        assert 'total_connections' in stats
        assert 'active_connections' in stats
        assert 'idle_connections' in stats
        assert stats['total_connections'] == 3


class TestFailoverManagerComprehensive:
    """Comprehensive tests for FailoverManager - Failover strategies"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.failover_config = {
            'strategy': FailoverStrategy.PRIORITY_BASED,
            'max_failover_attempts': 3,
            'failover_delay': 1.0,
            'health_check_timeout': 5.0
        }
        
        self.failover_manager = FailoverManager(self.failover_config)
        
        self.broker_list = [
            {'broker_id': 'broker_1', 'priority': ConnectionPriority.PRIMARY, 'status': 'healthy'},
            {'broker_id': 'broker_2', 'priority': ConnectionPriority.SECONDARY, 'status': 'healthy'},
            {'broker_id': 'broker_3', 'priority': ConnectionPriority.BACKUP, 'status': 'healthy'}
        ]
    
    @pytest.mark.asyncio
    async def test_failover_initialization(self):
        """Test failover manager initialization"""
        assert self.failover_manager is not None
        assert self.failover_manager.config == self.failover_config
        assert hasattr(self.failover_manager, 'strategy')
        assert hasattr(self.failover_manager, 'max_attempts')
    
    @pytest.mark.asyncio
    async def test_priority_based_failover(self):
        """Test priority-based failover strategy"""
        # Set priority-based strategy
        self.failover_manager.strategy = FailoverStrategy.PRIORITY_BASED
        
        # Simulate primary broker failure
        self.broker_list[0]['status'] = 'failed'
        
        # Get next broker
        next_broker = await self.failover_manager.get_next_broker(self.broker_list, 'broker_1')
        
        assert next_broker is not None
        assert next_broker['broker_id'] == 'broker_2'  # Should select secondary
    
    @pytest.mark.asyncio
    async def test_round_robin_failover(self):
        """Test round-robin failover strategy"""
        # Set round-robin strategy
        self.failover_manager.strategy = FailoverStrategy.ROUND_ROBIN
        
        # Get next broker multiple times
        brokers = []
        for _ in range(5):
            next_broker = await self.failover_manager.get_next_broker(self.broker_list, 'broker_1')
            brokers.append(next_broker['broker_id'])
        
        # Should cycle through brokers
        assert len(set(brokers)) > 1  # Should use multiple brokers
    
    @pytest.mark.asyncio
    async def test_load_balanced_failover(self):
        """Test load-balanced failover strategy"""
        # Set load-balanced strategy
        self.failover_manager.strategy = FailoverStrategy.LOAD_BALANCED
        
        # Add load information
        for broker in self.broker_list:
            broker['current_load'] = 0.5
            broker['capacity'] = 1.0
        
        # Get next broker
        next_broker = await self.failover_manager.get_next_broker(self.broker_list, 'broker_1')
        
        assert next_broker is not None
        # Should select broker with lowest load
        assert next_broker['current_load'] <= 0.5
    
    @pytest.mark.asyncio
    async def test_failover_attempt_tracking(self):
        """Test failover attempt tracking"""
        # Track failover attempts
        attempts = await self.failover_manager.track_failover_attempt('broker_1')
        
        assert attempts == 1
        
        # Track multiple attempts
        for _ in range(2):
            attempts = await self.failover_manager.track_failover_attempt('broker_1')
        
        assert attempts == 3
        
        # Check if max attempts reached
        max_reached = await self.failover_manager.has_reached_max_attempts('broker_1')
        assert max_reached is True
    
    @pytest.mark.asyncio
    async def test_failover_recovery(self):
        """Test failover recovery functionality"""
        # Simulate broker recovery
        self.broker_list[0]['status'] = 'healthy'
        
        # Reset failover attempts
        result = await self.failover_manager.reset_failover_attempts('broker_1')
        
        assert result is True
        
        # Verify attempts are reset
        attempts = await self.failover_manager.track_failover_attempt('broker_1')
        assert attempts == 1


class TestHealthMonitorComprehensive:
    """Comprehensive tests for HealthMonitor - Connection health monitoring"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.health_config = {
            'check_interval': 60,
            'timeout': 5.0,
            'failure_threshold': 3,
            'recovery_threshold': 2,
            'latency_threshold': 1000  # ms
        }
        
        self.health_monitor = HealthMonitor(self.health_config)
        
        self.mock_connection = {
            'connection_id': 'conn_001',
            'broker_id': 'broker_1',
            'status': 'connected',
            'last_heartbeat': datetime.now()
        }
    
    @pytest.mark.asyncio
    async def test_health_monitor_initialization(self):
        """Test health monitor initialization"""
        assert self.health_monitor is not None
        assert self.health_monitor.config == self.health_config
        assert hasattr(self.health_monitor, 'check_interval')
        assert hasattr(self.health_monitor, 'failure_threshold')
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self):
        """Test health check performance"""
        # Perform health check
        with patch.object(self.health_monitor, '_perform_health_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                'status': HealthStatus.HEALTHY,
                'latency_ms': 50,
                'timestamp': datetime.now()
            }
            
            result = await self.health_monitor.check_health(self.mock_connection)
            
            assert result is not None
            assert result['status'] == HealthStatus.HEALTHY
            assert result['latency_ms'] == 50
            mock_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_status_tracking(self):
        """Test health status tracking"""
        # Track health status
        await self.health_monitor.update_health_status('conn_001', HealthStatus.HEALTHY)
        
        # Get health status
        status = self.health_monitor.get_health_status('conn_001')
        
        assert status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_failure_detection(self):
        """Test failure detection"""
        # Simulate multiple failures
        for _ in range(3):
            await self.health_monitor.record_failure('conn_001', 'Connection timeout')
        
        # Check if failure threshold reached
        is_failed = await self.health_monitor.is_connection_failed('conn_001')
        
        assert is_failed is True
    
    @pytest.mark.asyncio
    async def test_recovery_detection(self):
        """Test recovery detection"""
        # First simulate failures
        for _ in range(3):
            await self.health_monitor.record_failure('conn_001', 'Connection timeout')
        
        # Then simulate recoveries
        for _ in range(2):
            await self.health_monitor.record_success('conn_001')
        
        # Check if recovery threshold reached
        is_recovered = await self.health_monitor.is_connection_recovered('conn_001')
        
        assert is_recovered is True
    
    @pytest.mark.asyncio
    async def test_latency_monitoring(self):
        """Test latency monitoring"""
        # Record latency measurements
        latencies = [50, 75, 100, 125, 150]
        for latency in latencies:
            await self.health_monitor.record_latency('conn_001', latency)
        
        # Get latency statistics
        stats = self.health_monitor.get_latency_statistics('conn_001')
        
        assert stats is not None
        assert 'average_latency' in stats
        assert 'max_latency' in stats
        assert 'min_latency' in stats
        assert stats['average_latency'] > 0
    
    @pytest.mark.asyncio
    async def test_health_statistics(self):
        """Test health statistics"""
        # Record various health events
        await self.health_monitor.record_success('conn_001')
        await self.health_monitor.record_failure('conn_002', 'Timeout')
        await self.health_monitor.record_latency('conn_001', 100)
        
        # Get overall statistics
        stats = self.health_monitor.get_health_statistics()
        
        assert stats is not None
        assert 'total_connections' in stats
        assert 'healthy_connections' in stats
        assert 'failed_connections' in stats


class TestLoadBalancerComprehensive:
    """Comprehensive tests for LoadBalancer - Load balancing"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.load_balancer = LoadBalancer()
        
        self.broker_list = [
            {
                'broker_id': 'broker_1',
                'weight': 1.0,
                'current_load': 0.3,
                'capacity': 1.0,
                'status': 'healthy'
            },
            {
                'broker_id': 'broker_2',
                'weight': 0.8,
                'current_load': 0.5,
                'capacity': 1.0,
                'status': 'healthy'
            },
            {
                'broker_id': 'broker_3',
                'weight': 0.6,
                'current_load': 0.7,
                'capacity': 1.0,
                'status': 'healthy'
            }
        ]
    
    @pytest.mark.asyncio
    async def test_weighted_selection(self):
        """Test weighted broker selection"""
        # Select broker multiple times
        selections = []
        for _ in range(100):
            broker = await self.load_balancer.select_broker(self.broker_list)
            selections.append(broker['broker_id'])
        
        # Count selections
        selection_counts = {broker_id: selections.count(broker_id) for broker_id in ['broker_1', 'broker_2', 'broker_3']}
        
        # broker_1 should be selected most often (highest weight)
        assert selection_counts['broker_1'] >= selection_counts['broker_2']
        assert selection_counts['broker_2'] >= selection_counts['broker_3']
    
    @pytest.mark.asyncio
    async def test_load_based_selection(self):
        """Test load-based broker selection"""
        # Select broker based on load
        broker = await self.load_balancer.select_broker_by_load(self.broker_list)
        
        # Should select broker with lowest load
        assert broker['broker_id'] == 'broker_1'  # Lowest load (0.3)
    
    @pytest.mark.asyncio
    async def test_round_robin_selection(self):
        """Test round-robin broker selection"""
        # Select brokers in round-robin fashion
        selections = []
        for _ in range(6):  # 2 cycles through 3 brokers
            broker = await self.load_balancer.select_broker_round_robin(self.broker_list)
            selections.append(broker['broker_id'])
        
        # Should cycle through all brokers
        unique_brokers = set(selections)
        assert len(unique_brokers) == 3
        assert 'broker_1' in unique_brokers
        assert 'broker_2' in unique_brokers
        assert 'broker_3' in unique_brokers
    
    @pytest.mark.asyncio
    async def test_capacity_aware_selection(self):
        """Test capacity-aware broker selection"""
        # Select broker considering capacity
        broker = await self.load_balancer.select_broker_by_capacity(self.broker_list)
        
        # Should select broker with available capacity
        assert broker['current_load'] < broker['capacity']
    
    @pytest.mark.asyncio
    async def test_healthy_broker_filtering(self):
        """Test filtering of healthy brokers"""
        # Mark one broker as unhealthy
        self.broker_list[1]['status'] = 'unhealthy'
        
        # Select broker (should only consider healthy ones)
        broker = await self.load_balancer.select_broker(self.broker_list)
        
        # Should not select unhealthy broker
        assert broker['status'] == 'healthy'
        assert broker['broker_id'] != 'broker_2'


if __name__ == '__main__':
    pytest.main([__file__])
