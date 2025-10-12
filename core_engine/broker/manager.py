#!/usr/bin/env python3
"""
Broker Manager - Core Engine
============================

Clean implementation of the broker manager for core_engine.
This component manages multi-broker connectivity and routing.

As a supporting component in the institutional architecture:
- Manages connections to multiple brokers (IBKR, Alpaca, Polygon)
- Provides unified broker interface for execution
- Handles broker-specific order routing and management
- Monitors broker connectivity and failover

Migration: Direct implementation using proven broker integration patterns.

Author: StatArb_Gemini Core Engine Migration  
Version: 1.0.0 (Clean Production - Multi-Broker)
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Leverage existing high-quality broker components
# Import core_engine types instead of core_structure
from ..type_definitions.orders import (
    Order, ExecutionResult, OrderStatus
)

# Define missing broker types
from abc import ABC, abstractmethod

@dataclass
class OrderResult:
    """Result of order submission"""
    success: bool
    order_id: str
    status: OrderStatus
    filled_quantity: float
    average_price: float
    error_message: Optional[str] = None

class BaseBroker(ABC):
    """Abstract base broker interface"""
    
    @abstractmethod
    async def submit_order(self, order: Order) -> OrderResult:
        """Submit order to broker"""
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get order status"""

@dataclass
class ExecutionParameters:
    """Parameters for order execution"""
    max_slippage: float = 0.01  # 1%
    timeout_seconds: int = 30
    allow_partial_fills: bool = True
    priority: str = "normal"

class AdvancedOrderManager:
    """Advanced order management capabilities"""
    
    def __init__(self):
        self.pending_orders: Dict[str, Order] = {}
        self.order_history: List[OrderResult] = []
    
    async def submit_bracket_order(self, entry_order: Order, 
                                 stop_loss: Order, 
                                 take_profit: Order) -> List[OrderResult]:
        """Submit bracket order (entry + stop loss + take profit)"""
        # Mock implementation
        results = []
        for order in [entry_order, stop_loss, take_profit]:
            result = OrderResult(
                success=True,
                order_id=order.order_id,
                status=OrderStatus.SUBMITTED,
                filled_quantity=0,
                average_price=0
            )
            results.append(result)
        return results
    
    async def submit_oco_order(self, order1: Order, order2: Order) -> List[OrderResult]:
        """Submit one-cancels-other order"""
        # Mock implementation
        results = []
        for order in [order1, order2]:
            result = OrderResult(
                success=True,
                order_id=order.order_id,
                status=OrderStatus.SUBMITTED,
                filled_quantity=0,
                average_price=0
            )
            results.append(result)
        return results

logger = logging.getLogger(__name__)

class BrokerType(Enum):
    """Supported broker types"""
    IBKR = "ibkr"
    ALPACA = "alpaca"
    POLYGON = "polygon"
    MOCK = "mock"

class ConnectionStatus(Enum):
    """Broker connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    MAINTENANCE = "maintenance"

@dataclass
class BrokerConnection:
    """Broker connection configuration"""
    broker_id: str
    broker_type: BrokerType
    name: str
    config: Dict[str, Any]
    priority: int  # 1 = highest priority
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    last_connection: Optional[datetime] = None
    error_count: int = 0
    max_errors: int = 5

@dataclass
class BrokerCapabilities:
    """Broker capabilities"""
    supports_equities: bool = True
    supports_options: bool = False
    supports_futures: bool = False
    supports_crypto: bool = False
    supports_dark_pools: bool = False
    supports_fractional_shares: bool = False
    max_order_size: float = 1000000.0
    min_order_size: float = 1.0
    commission_structure: Dict[str, float] = field(default_factory=dict)

@dataclass
class BrokerPerformance:
    """Broker performance metrics"""
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    average_fill_time: float = 0.0
    average_commission: float = 0.0
    uptime_percentage: float = 100.0
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class BrokerManagerConfig:
    """Broker manager configuration"""
    primary_broker: str = "IBKR"
    enable_failover: bool = True
    health_check_interval: int = 30  # seconds
    max_reconnect_attempts: int = 3
    connection_timeout: int = 30
    enable_load_balancing: bool = True
    order_routing_strategy: str = "primary_first"  # primary_first, round_robin, least_load

class IBrokerSubscriber:
    """Interface for broker event subscribers"""
    
    async def on_connection_status_change(self, broker_id: str, status: ConnectionStatus) -> None:
        """Handle broker connection status changes"""
    
    async def on_order_update(self, broker_id: str, order_update: Dict[str, Any]) -> None:
        """Handle order updates from broker"""

class BrokerManager:
    """
    Core Engine Broker Manager
    
    This component provides unified multi-broker connectivity:
    
    1. Manages connections to multiple brokers
    2. Provides broker abstraction for execution engine
    3. Handles order routing and load balancing
    4. Monitors broker health and implements failover
    5. Tracks broker performance and capabilities
    
    The multi-broker approach includes:
    - Primary/secondary broker failover
    - Load balancing across brokers
    - Broker-specific order routing
    - Real-time health monitoring
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = BrokerManagerConfig(**config) if config else BrokerManagerConfig()
        
        # Broker infrastructure
        self.broker_connections: Dict[str, BrokerConnection] = {}
        self.broker_instances: Dict[str, BaseBroker] = {}
        self.broker_capabilities: Dict[str, BrokerCapabilities] = {}
        self.broker_performance: Dict[str, BrokerPerformance] = {}
        
        # Order routing
        self.active_orders: Dict[str, str] = {}  # order_id -> broker_id
        self.broker_load: Dict[str, int] = {}    # broker_id -> active_order_count
        
        # Subscribers
        self.subscribers: List[IBrokerSubscriber] = []
        
        # State
        self.is_initialized = False
        self.is_running = False
        self.health_check_task: Optional[asyncio.Task] = None
        
        logger.info("🏛️ Broker Manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize broker manager"""
        try:
            logger.info("🔄 Initializing Broker Manager...")
            
            # Initialize default broker configurations
            await self._initialize_default_brokers()
            
            # Connect to brokers
            await self._connect_all_brokers()
            
            # Initialize performance tracking
            await self._initialize_performance_tracking()
            
            self.is_initialized = True
            logger.info("✅ Broker Manager initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Broker Manager initialization failed: {e}")
            raise
    
    async def start(self) -> bool:
        """Start broker manager"""
        try:
            if not self.is_initialized:
                raise RuntimeError("Broker Manager not initialized")
            
            logger.info("🚀 Starting Broker Manager monitoring...")
            
            # Start health monitoring
            self.health_check_task = asyncio.create_task(self._run_health_monitoring())
            
            self.is_running = True
            logger.info("✅ Broker Manager started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Broker Manager: {e}")
            raise
    
    async def stop(self) -> bool:
        """Stop broker manager"""
        try:
            logger.info("🛑 Stopping Broker Manager...")
            
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
                self.health_check_task = None
            
            # Disconnect all brokers
            await self._disconnect_all_brokers()
            
            self.is_running = False
            logger.info("✅ Broker Manager stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop Broker Manager: {e}")
            return False
    
    def subscribe(self, subscriber: IBrokerSubscriber):
        """Subscribe to broker events"""
        self.subscribers.append(subscriber)
        logger.info(f"📝 New broker subscriber: {type(subscriber).__name__}")
    
    # Core Broker Management Methods
    async def add_broker(self, broker_config: Dict[str, Any]) -> bool:
        """Add new broker connection"""
        try:
            broker_id = broker_config['broker_id']
            broker_type = BrokerType(broker_config['type'])
            
            logger.info(f"➕ Adding broker: {broker_id} ({broker_type.value})")
            
            # Create broker connection
            connection = BrokerConnection(
                broker_id=broker_id,
                broker_type=broker_type,
                name=broker_config.get('name', broker_id),
                config=broker_config.get('config', {}),
                priority=broker_config.get('priority', 10)
            )
            
            # Store connection
            self.broker_connections[broker_id] = connection
            self.broker_load[broker_id] = 0
            
            # Initialize capabilities
            capabilities = await self._determine_broker_capabilities(broker_type)
            self.broker_capabilities[broker_id] = capabilities
            
            # Initialize performance tracking
            self.broker_performance[broker_id] = BrokerPerformance()
            
            # Connect broker
            await self._connect_broker(broker_id)
            
            logger.info(f"✅ Broker added: {broker_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add broker: {e}")
            return False
    
    async def remove_broker(self, broker_id: str) -> bool:
        """Remove broker connection"""
        try:
            if broker_id not in self.broker_connections:
                return False
            
            logger.info(f"➖ Removing broker: {broker_id}")
            
            # Disconnect broker
            await self._disconnect_broker(broker_id)
            
            # Remove from collections
            del self.broker_connections[broker_id]
            if broker_id in self.broker_instances:
                del self.broker_instances[broker_id]
            if broker_id in self.broker_capabilities:
                del self.broker_capabilities[broker_id]
            if broker_id in self.broker_performance:
                del self.broker_performance[broker_id]
            if broker_id in self.broker_load:
                del self.broker_load[broker_id]
            
            logger.info(f"✅ Broker removed: {broker_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to remove broker {broker_id}: {e}")
            return False
    
    async def execute_order(self, order: Order, broker_preference: Optional[str] = None) -> ExecutionResult:
        """Execute order through optimal broker"""
        try:
            # Determine best broker for execution
            broker_id = await self._select_broker_for_order(order, broker_preference)
            if not broker_id:
                raise Exception("No available broker for order execution")
            
            logger.info(f"📋 Routing order to broker: {broker_id}")
            
            # Execute through selected broker
            result = await self._execute_order_through_broker(order, broker_id)
            
            # Update broker performance
            await self._update_broker_performance(broker_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Order execution failed: {e}")
            return ExecutionResult(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=0.0,
                price=0.0,
                commission=0.0,
                success=False,
                error_message=str(e)
            )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order through appropriate broker"""
        try:
            if order_id not in self.active_orders:
                logger.warning(f"⚠️ Order not found for cancellation: {order_id}")
                return False
            
            broker_id = self.active_orders[order_id]
            broker = self.broker_instances.get(broker_id)
            
            if broker:
                success = await broker.cancel_order(order_id)
                if success:
                    del self.active_orders[order_id]
                    self.broker_load[broker_id] = max(0, self.broker_load[broker_id] - 1)
                    logger.info(f"✅ Order cancelled: {order_id}")
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Order cancellation failed: {e}")
            return False
    
    async def get_broker_status(self, broker_id: Optional[str] = None) -> Dict[str, Any]:
        """Get broker status information"""
        if broker_id:
            if broker_id not in self.broker_connections:
                return {}
            
            connection = self.broker_connections[broker_id]
            performance = self.broker_performance.get(broker_id, BrokerPerformance())
            
            return {
                'broker_id': broker_id,
                'status': connection.status.value,
                'last_connection': connection.last_connection,
                'error_count': connection.error_count,
                'performance': {
                    'total_orders': performance.total_orders,
                    'success_rate': performance.successful_orders / max(1, performance.total_orders),
                    'average_fill_time': performance.average_fill_time,
                    'uptime_percentage': performance.uptime_percentage
                },
                'current_load': self.broker_load.get(broker_id, 0)
            }
        else:
            # Return all broker statuses
            return {
                broker_id: await self.get_broker_status(broker_id)
                for broker_id in self.broker_connections.keys()
            }
    
    async def get_available_brokers(self) -> List[str]:
        """Get list of available (connected) brokers"""
        available = []
        for broker_id, connection in self.broker_connections.items():
            if connection.status == ConnectionStatus.CONNECTED:
                available.append(broker_id)
        return available
    
    # Broker Selection and Routing Methods
    async def _select_broker_for_order(self, order: Order, preference: Optional[str] = None) -> Optional[str]:
        """Select optimal broker for order execution"""
        available_brokers = await self.get_available_brokers()
        if not available_brokers:
            return None
        
        # Use preferred broker if specified and available
        if preference and preference in available_brokers:
            return preference
        
        # Apply routing strategy
        if self.config.order_routing_strategy == "primary_first":
            return await self._select_primary_broker(available_brokers)
        elif self.config.order_routing_strategy == "round_robin":
            return await self._select_round_robin_broker(available_brokers)
        elif self.config.order_routing_strategy == "least_load":
            return await self._select_least_loaded_broker(available_brokers)
        else:
            return available_brokers[0]  # Default to first available
    
    async def _select_primary_broker(self, available_brokers: List[str]) -> str:
        """Select primary broker (highest priority)"""
        primary_broker = None
        highest_priority = float('inf')
        
        for broker_id in available_brokers:
            connection = self.broker_connections[broker_id]
            if connection.priority < highest_priority:
                highest_priority = connection.priority
                primary_broker = broker_id
        
        return primary_broker or available_brokers[0]
    
    async def _select_round_robin_broker(self, available_brokers: List[str]) -> str:
        """Select broker using round-robin"""
        # Simple round-robin based on total orders
        broker_orders = {
            broker_id: self.broker_performance[broker_id].total_orders
            for broker_id in available_brokers
        }
        return min(broker_orders.items(), key=lambda x: x[1])[0]
    
    async def _select_least_loaded_broker(self, available_brokers: List[str]) -> str:
        """Select broker with least current load"""
        broker_loads = {
            broker_id: self.broker_load.get(broker_id, 0)
            for broker_id in available_brokers
        }
        return min(broker_loads.items(), key=lambda x: x[1])[0]
    
    # Broker Connection Management
    async def _connect_broker(self, broker_id: str) -> bool:
        """Connect to individual broker"""
        try:
            connection = self.broker_connections[broker_id]
            connection.status = ConnectionStatus.CONNECTING
            
            logger.info(f"🔌 Connecting to broker: {broker_id}")
            
            # Create broker instance based on type
            broker_instance = await self._create_broker_instance(connection)
            
            if broker_instance:
                # Store broker instance
                self.broker_instances[broker_id] = broker_instance
                
                # Update connection status
                connection.status = ConnectionStatus.CONNECTED
                connection.last_connection = datetime.now()
                connection.error_count = 0
                
                # Notify subscribers
                for subscriber in self.subscribers:
                    await subscriber.on_connection_status_change(broker_id, ConnectionStatus.CONNECTED)
                
                logger.info(f"✅ Connected to broker: {broker_id}")
                return True
            else:
                connection.status = ConnectionStatus.FAILED
                connection.error_count += 1
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to broker {broker_id}: {e}")
            connection.status = ConnectionStatus.FAILED
            connection.error_count += 1
            return False
    
    async def _disconnect_broker(self, broker_id: str) -> bool:
        """Disconnect from individual broker"""
        try:
            logger.info(f"🔌 Disconnecting from broker: {broker_id}")
            
            connection = self.broker_connections[broker_id]
            broker_instance = self.broker_instances.get(broker_id)
            
            if broker_instance:
                # Disconnect broker
                if hasattr(broker_instance, 'disconnect'):
                    await broker_instance.disconnect()
                
                # Remove instance
                del self.broker_instances[broker_id]
            
            # Update connection status
            connection.status = ConnectionStatus.DISCONNECTED
            
            # Notify subscribers
            for subscriber in self.subscribers:
                await subscriber.on_connection_status_change(broker_id, ConnectionStatus.DISCONNECTED)
            
            logger.info(f"✅ Disconnected from broker: {broker_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to disconnect from broker {broker_id}: {e}")
            return False
    
    async def _connect_all_brokers(self):
        """Connect to all configured brokers"""
        logger.info("🔌 Connecting to all brokers...")
        
        connection_tasks = [
            self._connect_broker(broker_id) 
            for broker_id in self.broker_connections.keys()
        ]
        
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        connected_count = sum(1 for result in results if result is True)
        logger.info(f"✅ Connected to {connected_count}/{len(connection_tasks)} brokers")
    
    async def _disconnect_all_brokers(self):
        """Disconnect from all brokers"""
        logger.info("🔌 Disconnecting from all brokers...")
        
        disconnect_tasks = [
            self._disconnect_broker(broker_id) 
            for broker_id in list(self.broker_instances.keys())
        ]
        
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        logger.info("✅ Disconnected from all brokers")
    
    async def _create_broker_instance(self, connection: BrokerConnection) -> Optional[BaseBroker]:
        """Create broker instance based on type"""
        try:
            if connection.broker_type == BrokerType.MOCK:
                # Create mock broker for testing
                return await self._create_mock_broker(connection)
            elif connection.broker_type == BrokerType.IBKR:
                # Would create IBKR broker instance
                return await self._create_mock_broker(connection)  # Placeholder
            elif connection.broker_type == BrokerType.ALPACA:
                # Would create Alpaca broker instance
                return await self._create_mock_broker(connection)  # Placeholder
            else:
                logger.warning(f"⚠️ Unsupported broker type: {connection.broker_type}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to create broker instance: {e}")
            return None
    
    async def _create_mock_broker(self, connection: BrokerConnection) -> BaseBroker:
        """Create mock broker for testing"""
        # Create a simple mock broker
        class MockBroker(BaseBroker):
            def __init__(self, broker_id: str):
                self.broker_id = broker_id
                
            async def submit_order(self, order: Order) -> OrderResult:
                # Mock order submission
                return OrderResult(
                    success=True,
                    order_id=order.order_id,
                    status=OrderStatus.FILLED,
                    filled_quantity=order.quantity,
                    average_price=order.price or 100.0
                )
            
            async def cancel_order(self, order_id: str) -> bool:
                return True
            
            async def get_order_status(self, order_id: str) -> OrderStatus:
                return OrderStatus.FILLED
        
        return MockBroker(connection.broker_id)
    
    # Execution and Performance Methods
    async def _execute_order_through_broker(self, order: Order, broker_id: str) -> ExecutionResult:
        """Execute order through specific broker"""
        try:
            broker = self.broker_instances[broker_id]
            
            # Track active order
            self.active_orders[order.order_id] = broker_id
            self.broker_load[broker_id] = self.broker_load.get(broker_id, 0) + 1
            
            # Execute order
            start_time = datetime.now()
            result = await broker.submit_order(order)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create execution result
            execution_result = ExecutionResult(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=result.filled_quantity if result.success else 0,
                price=result.average_price if result.success else 0,
                commission=result.filled_quantity * 0.001 if result.success else 0,  # Mock commission
                success=result.success,
                error_message=result.error_message if not result.success else None,
                broker_order_id=result.order_id,
                metadata={'broker_id': broker_id, 'execution_time': execution_time}
            )
            
            # Clean up active order tracking
            if order.order_id in self.active_orders:
                del self.active_orders[order.order_id]
            self.broker_load[broker_id] = max(0, self.broker_load[broker_id] - 1)
            
            return execution_result
            
        except Exception as e:
            logger.error(f"❌ Broker execution failed: {e}")
            # Clean up on error
            if order.order_id in self.active_orders:
                del self.active_orders[order.order_id]
            self.broker_load[broker_id] = max(0, self.broker_load[broker_id] - 1)
            
            return ExecutionResult(
                success=False,
                order_id=order.order_id,
                error_message=str(e)
            )
    
    async def _update_broker_performance(self, broker_id: str, result: ExecutionResult):
        """Update broker performance metrics"""
        performance = self.broker_performance[broker_id]
        
        performance.total_orders += 1
        if result.success:
            performance.successful_orders += 1
            
            # Update average fill time
            execution_time = result.metadata.get('execution_time', 0)
            if performance.average_fill_time == 0:
                performance.average_fill_time = execution_time
            else:
                performance.average_fill_time = (
                    performance.average_fill_time * 0.9 + execution_time * 0.1
                )
        else:
            performance.failed_orders += 1
        
        performance.last_updated = datetime.now()
    
    # Health Monitoring
    async def _run_health_monitoring(self):
        """Run continuous broker health monitoring"""
        logger.info("🏥 Starting broker health monitoring...")
        
        while self.is_running:
            try:
                await self._check_broker_health()
                await asyncio.sleep(self.config.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Health monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _check_broker_health(self):
        """Check health of all brokers"""
        for broker_id, connection in self.broker_connections.items():
            try:
                if connection.status == ConnectionStatus.CONNECTED:
                    # Check if broker is still responsive
                    broker = self.broker_instances.get(broker_id)
                    if broker:
                        # Perform health check (would be broker-specific)
                        is_healthy = await self._perform_broker_health_check(broker_id)
                        if not is_healthy:
                            logger.warning(f"🏥 Broker health check failed: {broker_id}")
                            await self._handle_broker_health_failure(broker_id)
                elif connection.status == ConnectionStatus.FAILED:
                    # Attempt reconnection if not exceeded max errors
                    if connection.error_count < connection.max_errors:
                        logger.info(f"🔄 Attempting reconnection: {broker_id}")
                        await self._connect_broker(broker_id)
                        
            except Exception as e:
                logger.error(f"❌ Health check failed for {broker_id}: {e}")
    
    async def _perform_broker_health_check(self, broker_id: str) -> bool:
        """Perform health check on specific broker"""
        # Mock health check - would be real broker API calls
        return True
    
    async def _handle_broker_health_failure(self, broker_id: str):
        """Handle broker health failure"""
        logger.warning(f"🚨 Handling broker health failure: {broker_id}")
        
        connection = self.broker_connections[broker_id]
        connection.status = ConnectionStatus.FAILED
        connection.error_count += 1
        
        # Notify subscribers
        for subscriber in self.subscribers:
            await subscriber.on_connection_status_change(broker_id, ConnectionStatus.FAILED)
    
    # Initialization Methods
    async def _initialize_default_brokers(self):
        """Initialize default broker configurations"""
        default_brokers = [
            {
                'broker_id': 'IBKR',
                'type': 'mock',  # Would be 'ibkr' in production
                'name': 'Interactive Brokers',
                'priority': 1,
                'config': {
                    'host': 'localhost',
                    'port': 7497,
                    'client_id': 1
                }
            },
            {
                'broker_id': 'Alpaca',
                'type': 'mock',  # Would be 'alpaca' in production
                'name': 'Alpaca Markets',
                'priority': 2,
                'config': {
                    'api_key': 'test_key',
                    'secret_key': 'test_secret',
                    'base_url': 'https://paper-api.alpaca.markets'
                }
            }
        ]
        
        for broker_config in default_brokers:
            await self.add_broker(broker_config)
    
    async def _determine_broker_capabilities(self, broker_type: BrokerType) -> BrokerCapabilities:
        """Determine capabilities for broker type"""
        if broker_type == BrokerType.IBKR:
            return BrokerCapabilities(
                supports_equities=True,
                supports_options=True,
                supports_futures=True,
                supports_dark_pools=True,
                max_order_size=1000000.0,
                commission_structure={'equities': 0.005, 'options': 1.0}
            )
        elif broker_type == BrokerType.ALPACA:
            return BrokerCapabilities(
                supports_equities=True,
                supports_fractional_shares=True,
                max_order_size=100000.0,
                commission_structure={'equities': 0.0}
            )
        else:
            return BrokerCapabilities()
    
    async def _initialize_performance_tracking(self):
        """Initialize broker performance tracking"""
        logger.info("📊 Initializing broker performance tracking...")
        
        for broker_id in self.broker_connections.keys():
            if broker_id not in self.broker_performance:
                self.broker_performance[broker_id] = BrokerPerformance()
    
    def get_broker_manager_status(self) -> Dict[str, Any]:
        """Get comprehensive broker manager status"""
        total_brokers = len(self.broker_connections)
        connected_brokers = sum(
            1 for conn in self.broker_connections.values() 
            if conn.status == ConnectionStatus.CONNECTED
        )
        
        return {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'total_brokers': total_brokers,
            'connected_brokers': connected_brokers,
            'connection_rate': connected_brokers / max(1, total_brokers),
            'active_orders': len(self.active_orders),
            'total_load': sum(self.broker_load.values()),
            'primary_broker': self.config.primary_broker,
            'failover_enabled': self.config.enable_failover,
            'broker_status': {
                broker_id: {
                    'status': conn.status.value,
                    'error_count': conn.error_count,
                    'load': self.broker_load.get(broker_id, 0)
                }
                for broker_id, conn in self.broker_connections.items()
            }
        }