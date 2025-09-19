"""
Broker Engine - Broker Manager
Unified broker management with multi-broker coordination and orchestration
"""

import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
import time
from collections import defaultdict, deque
import uuid
import warnings
from abc import ABC, abstractmethod
import json

from .broker_adapter import (
    BrokerAdapter, BrokerCredentials, BrokerType, ConnectionStatus,
    StandardOrder, StandardExecution, StandardPosition, StandardAccount,
    OrderAction, OrderType, TimeInForce
)
from .connection_manager import ConnectionManager, ConnectionConfig, ConnectionPriority
from .protocol_handler import ProtocolHandler, ProtocolConfig, ProtocolType, MessageType
from .message_processor import MessageProcessor, ProcessingConfig, ProcessingPriority
from .session_manager import SessionManager, SessionConfig, SessionType, AuthenticationRequest

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class BrokerStatus(Enum):
    """Broker status"""
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ONLINE = "online"
    DEGRADED = "degraded"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ExecutionVenue(Enum):
    """Execution venues"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DARK_POOL = "dark_pool"
    ECN = "ecn"
    SMART_ROUTING = "smart_routing"


@dataclass
class BrokerConfig:
    """Broker manager configuration"""
    # Connection settings
    connection_config: ConnectionConfig = field(default_factory=ConnectionConfig)
    session_config: SessionConfig = field(default_factory=SessionConfig)
    processing_config: ProcessingConfig = field(default_factory=ProcessingConfig)
    
    # Execution settings
    default_venue: ExecutionVenue = ExecutionVenue.SMART_ROUTING
    enable_smart_routing: bool = True
    enable_order_aggregation: bool = True
    
    # Risk settings
    enable_pre_trade_risk: bool = True
    enable_real_time_risk: bool = True
    position_limit_check: bool = True
    
    # Monitoring
    enable_performance_monitoring: bool = True
    enable_latency_monitoring: bool = True
    metrics_collection_interval: float = 60.0
    
    # Failover
    enable_automatic_failover: bool = True
    failover_threshold: float = 0.1  # 10% error rate
    recovery_check_interval: float = 300.0  # 5 minutes


@dataclass
class BrokerInfo:
    """Broker information"""
    broker_id: str
    broker_type: BrokerType
    name: str
    status: BrokerStatus
    
    # Connection details
    connection_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Capabilities
    supported_order_types: List[OrderType] = field(default_factory=list)
    supported_venues: List[ExecutionVenue] = field(default_factory=list)
    max_order_size: Optional[float] = None
    
    # Performance metrics
    avg_latency: float = 0.0
    success_rate: float = 0.0
    uptime: float = 0.0
    
    # Timestamps
    connected_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    # Custom attributes
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderRequest:
    """Unified order request"""
    request_id: str
    symbol: str
    action: OrderAction
    quantity: float
    order_type: OrderType
    
    # Price parameters
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Execution preferences
    venue: Optional[ExecutionVenue] = None
    broker_preference: Optional[BrokerType] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    
    # Advanced parameters
    display_size: Optional[float] = None
    min_quantity: Optional[float] = None
    
    # Risk parameters
    max_position: Optional[float] = None
    risk_tolerance: str = "normal"
    
    # Metadata
    strategy_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    client_order_id: Optional[str] = None
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    requested_at: Optional[datetime] = None


@dataclass
class ExecutionReport:
    """Unified execution report"""
    execution_id: str
    order_request_id: str
    broker_id: str
    
    # Execution details
    symbol: str
    side: str
    quantity: float
    price: float
    
    # Timing
    execution_time: datetime
    
    # Fees and costs
    commission: float = 0.0
    fees: float = 0.0
    
    # Market data
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    
    # Venue information
    venue: Optional[str] = None
    liquidity_flag: Optional[str] = None
    
    # Performance metrics
    latency: Optional[float] = None
    slippage: Optional[float] = None
    
    # Metadata
    broker_execution_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class BrokerSelector:
    """Intelligent broker selection engine"""
    
    def __init__(self, config: BrokerConfig):
        self.config = config
        self._broker_scores: Dict[str, float] = {}
        self._venue_mappings: Dict[ExecutionVenue, List[str]] = defaultdict(list)
        
        logger.info("Broker selector initialized")
    
    def select_broker(self, order_request: OrderRequest, 
                     available_brokers: List[BrokerInfo]) -> Optional[BrokerInfo]:
        """Select best broker for order execution"""
        
        try:
            if not available_brokers:
                return None
            
            # Filter brokers based on requirements
            eligible_brokers = self._filter_eligible_brokers(order_request, available_brokers)
            
            if not eligible_brokers:
                logger.warning(f"No eligible brokers found for order {order_request.request_id}")
                return None
            
            # Score brokers
            scored_brokers = []
            for broker in eligible_brokers:
                score = self._calculate_broker_score(order_request, broker)
                scored_brokers.append((broker, score))
            
            # Sort by score (highest first)
            scored_brokers.sort(key=lambda x: x[1], reverse=True)
            
            selected_broker = scored_brokers[0][0]
            
            logger.debug(f"Selected broker {selected_broker.broker_id} for order {order_request.request_id}")
            
            return selected_broker
            
        except Exception as e:
            logger.error(f"Broker selection failed: {e}")
            return None
    
    def _filter_eligible_brokers(self, order_request: OrderRequest, 
                                brokers: List[BrokerInfo]) -> List[BrokerInfo]:
        """Filter brokers based on eligibility criteria"""
        
        eligible = []
        
        for broker in brokers:
            # Check status
            if broker.status != BrokerStatus.ONLINE:
                continue
            
            # Check broker preference
            if order_request.broker_preference and broker.broker_type != order_request.broker_preference:
                continue
            
            # Check order type support
            if order_request.order_type not in broker.supported_order_types:
                continue
            
            # Check order size limits
            if broker.max_order_size and order_request.quantity > broker.max_order_size:
                continue
            
            # Check venue support
            if order_request.venue and order_request.venue not in broker.supported_venues:
                continue
            
            eligible.append(broker)
        
        return eligible
    
    def _calculate_broker_score(self, order_request: OrderRequest, 
                               broker: BrokerInfo) -> float:
        """Calculate broker suitability score"""
        
        score = 0.0
        
        # Performance metrics (40% weight)
        score += broker.success_rate * 0.2
        score += broker.uptime * 0.1
        score += (1.0 - min(broker.avg_latency / 1000.0, 1.0)) * 0.1  # Latency penalty
        
        # Venue preference (20% weight)
        if order_request.venue and order_request.venue in broker.supported_venues:
            score += 0.2
        
        # Order type optimization (15% weight)
        if order_request.order_type in broker.supported_order_types:
            score += 0.15
        
        # Broker type preference (10% weight)
        if order_request.broker_preference and broker.broker_type == order_request.broker_preference:
            score += 0.1
        
        # Recent activity bonus (10% weight)
        if broker.last_activity:
            time_since_activity = (datetime.now() - broker.last_activity).total_seconds()
            activity_score = max(0, 1.0 - time_since_activity / 3600.0)  # Decay over 1 hour
            score += activity_score * 0.1
        
        # Size efficiency (5% weight)
        if broker.max_order_size:
            size_ratio = order_request.quantity / broker.max_order_size
            size_score = 1.0 - abs(0.5 - size_ratio)  # Optimal at 50% of capacity
            score += size_score * 0.05
        
        return min(score, 1.0)  # Cap at 1.0
    
    def add_venue_mapping(self, venue: ExecutionVenue, broker_id: str) -> None:
        """Add venue to broker mapping"""
        self._venue_mappings[venue].append(broker_id)
    
    def update_broker_score(self, broker_id: str, score: float) -> None:
        """Update broker performance score"""
        self._broker_scores[broker_id] = score


class OrderRouter:
    """Advanced order routing engine"""
    
    def __init__(self, config: BrokerConfig):
        self.config = config
        self._routing_rules: List[Callable] = []
        
        # Smart routing statistics
        self._routing_stats = {
            'total_orders': 0,
            'successful_routes': 0,
            'failed_routes': 0,
            'venue_distribution': defaultdict(int)
        }
        
        logger.info("Order router initialized")
    
    async def route_order(self, order_request: OrderRequest, 
                         available_brokers: List[BrokerInfo]) -> List[Tuple[BrokerInfo, OrderRequest]]:
        """Route order to optimal execution destinations"""
        
        try:
            self._routing_stats['total_orders'] += 1
            
            # Apply routing rules
            routing_decisions = []
            
            if self.config.enable_smart_routing:
                routing_decisions = await self._smart_route(order_request, available_brokers)
            else:
                # Simple routing to best broker
                selector = BrokerSelector(self.config)
                best_broker = selector.select_broker(order_request, available_brokers)
                
                if best_broker:
                    routing_decisions.append((best_broker, order_request))
            
            if routing_decisions:
                self._routing_stats['successful_routes'] += 1
                
                # Update venue statistics
                for broker, _ in routing_decisions:
                    venue = order_request.venue or ExecutionVenue.SMART_ROUTING
                    self._routing_stats['venue_distribution'][venue.value] += 1
            else:
                self._routing_stats['failed_routes'] += 1
            
            return routing_decisions
            
        except Exception as e:
            logger.error(f"Order routing failed: {e}")
            self._routing_stats['failed_routes'] += 1
            return []
    
    async def _smart_route(self, order_request: OrderRequest, 
                          available_brokers: List[BrokerInfo]) -> List[Tuple[BrokerInfo, OrderRequest]]:
        """Intelligent order routing with splitting and optimization"""
        
        routing_decisions = []
        
        # Large order handling
        if order_request.quantity > 10000:  # Example threshold
            # Split large orders
            split_orders = await self._split_large_order(order_request)
            
            for split_order in split_orders:
                selector = BrokerSelector(self.config)
                broker = selector.select_broker(split_order, available_brokers)
                if broker:
                    routing_decisions.append((broker, split_order))
        
        else:
            # Standard routing
            selector = BrokerSelector(self.config)
            broker = selector.select_broker(order_request, available_brokers)
            if broker:
                routing_decisions.append((broker, order_request))
        
        return routing_decisions
    
    async def _split_large_order(self, order_request: OrderRequest) -> List[OrderRequest]:
        """Split large order into smaller chunks"""
        
        split_orders = []
        chunk_size = 5000  # Example chunk size
        remaining_quantity = order_request.quantity
        
        while remaining_quantity > 0:
            current_chunk = min(chunk_size, remaining_quantity)
            
            # Create split order
            split_order = OrderRequest(
                request_id=f"{order_request.request_id}_split_{len(split_orders)}",
                symbol=order_request.symbol,
                action=order_request.action,
                quantity=current_chunk,
                order_type=order_request.order_type,
                limit_price=order_request.limit_price,
                stop_price=order_request.stop_price,
                venue=order_request.venue,
                broker_preference=order_request.broker_preference,
                time_in_force=order_request.time_in_force,
                strategy_id=order_request.strategy_id,
                portfolio_id=order_request.portfolio_id,
                context=order_request.context.copy()
            )
            
            split_orders.append(split_order)
            remaining_quantity -= current_chunk
        
        logger.info(f"Split order {order_request.request_id} into {len(split_orders)} chunks")
        
        return split_orders
    
    def add_routing_rule(self, rule: Callable[[OrderRequest, List[BrokerInfo]], List[Tuple[BrokerInfo, OrderRequest]]]) -> None:
        """Add custom routing rule"""
        self._routing_rules.append(rule)
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing statistics"""
        
        success_rate = (
            self._routing_stats['successful_routes'] / 
            max(self._routing_stats['total_orders'], 1) * 100
        )
        
        return {
            'total_orders': self._routing_stats['total_orders'],
            'successful_routes': self._routing_stats['successful_routes'],
            'failed_routes': self._routing_stats['failed_routes'],
            'success_rate': success_rate,
            'venue_distribution': dict(self._routing_stats['venue_distribution'])
        }


class BrokerManager:
    """
    Unified Broker Manager
    
    Orchestrates multi-broker operations with intelligent routing,
    session management, and comprehensive broker lifecycle management.
    """
    
    def __init__(self, config: Optional[BrokerConfig] = None):
        """Initialize broker manager"""
        
        self.config = config or BrokerConfig()
        
        # Core managers
        self._connection_manager = ConnectionManager(self.config.connection_config)
        self._session_manager = SessionManager(self.config.session_config)
        self._message_processor = MessageProcessor(self.config.processing_config)
        self._protocol_handler = ProtocolHandler()
        
        # Broker management
        self._brokers: Dict[str, BrokerInfo] = {}
        self._broker_adapters: Dict[str, BrokerAdapter] = {}
        
        # Order management
        self._order_selector = BrokerSelector(self.config)
        self._order_router = OrderRouter(self.config)
        
        # Order tracking
        self._pending_orders: Dict[str, OrderRequest] = {}
        self._order_executions: Dict[str, List[ExecutionReport]] = defaultdict(list)
        
        # Performance monitoring
        self._performance_metrics = {
            'total_orders': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_volume': 0.0,
            'avg_execution_time': 0.0,
            'avg_slippage': 0.0
        }
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._stop_background_tasks = False
        
        # Event handlers
        self._event_handlers = defaultdict(list)
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        logger.info("Broker manager initialized")
    
    async def start(self) -> None:
        """Start broker manager"""
        
        try:
            # Start core managers
            await self._connection_manager.start()
            await self._session_manager.start()
            await self._message_processor.start()
            
            # Start background tasks
            if self.config.enable_performance_monitoring:
                self._background_tasks.add(
                    asyncio.create_task(self._performance_monitor_loop())
                )
            
            if self.config.enable_automatic_failover:
                self._background_tasks.add(
                    asyncio.create_task(self._failover_monitor_loop())
                )
            
            logger.info("Broker manager started")
            
        except Exception as e:
            logger.error(f"Failed to start broker manager: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop broker manager"""
        
        try:
            # Signal background tasks to stop
            self._stop_background_tasks = True
            
            # Cancel background tasks
            for task in self._background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
            self._background_tasks.clear()
            
            # Stop core managers
            await self._message_processor.stop()
            await self._session_manager.stop()
            await self._connection_manager.stop()
            
            logger.info("Broker manager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping broker manager: {e}")
    
    async def add_broker(self, broker_type: BrokerType, credentials: BrokerCredentials,
                        name: Optional[str] = None, priority: ConnectionPriority = ConnectionPriority.PRIMARY,
                        capabilities: Optional[Dict[str, Any]] = None) -> str:
        """Add broker to manager"""
        
        try:
            with self._lock:
                # Generate broker ID
                broker_id = f"{broker_type.value}_{uuid.uuid4().hex[:8]}"
                
                # Add broker connection
                connection_id = await self._connection_manager.add_broker(
                    credentials, priority
                )
                
                # Create broker adapter
                broker_adapter = BrokerAdapter(credentials)
                self._broker_adapters[broker_id] = broker_adapter
                
                # Create broker info
                broker_info = BrokerInfo(
                    broker_id=broker_id,
                    broker_type=broker_type,
                    name=name or broker_type.value,
                    status=BrokerStatus.OFFLINE,
                    connection_id=connection_id,
                    supported_order_types=[
                        OrderType.MARKET, OrderType.LIMIT, OrderType.STOP, OrderType.STOP_LIMIT
                    ],
                    supported_venues=[
                        ExecutionVenue.PRIMARY, ExecutionVenue.SMART_ROUTING
                    ]
                )
                
                # Add capabilities
                if capabilities:
                    broker_info.attributes.update(capabilities)
                
                self._brokers[broker_id] = broker_info
                
                logger.info(f"Added broker {broker_id} ({broker_type.value})")
                
                self._trigger_event('broker_added', {
                    'broker_id': broker_id,
                    'broker_type': broker_type.value,
                    'name': broker_info.name
                })
                
                return broker_id
                
        except Exception as e:
            logger.error(f"Failed to add broker: {e}")
            raise
    
    async def remove_broker(self, broker_id: str) -> bool:
        """Remove broker from manager"""
        
        try:
            with self._lock:
                if broker_id not in self._brokers:
                    logger.warning(f"Broker {broker_id} not found")
                    return False
                
                broker_info = self._brokers[broker_id]
                
                # Disconnect broker
                if broker_info.connection_id:
                    await self._connection_manager.remove_broker(broker_info.connection_id)
                
                # Close sessions
                if broker_info.session_id:
                    await self._session_manager.close_session(broker_info.session_id)
                
                # Remove from tracking
                del self._brokers[broker_id]
                if broker_id in self._broker_adapters:
                    del self._broker_adapters[broker_id]
                
                logger.info(f"Removed broker {broker_id}")
                
                self._trigger_event('broker_removed', {
                    'broker_id': broker_id,
                    'broker_type': broker_info.broker_type.value
                })
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove broker {broker_id}: {e}")
            return False
    
    async def connect_broker(self, broker_id: str) -> bool:
        """Connect to specific broker"""
        
        try:
            with self._lock:
                if broker_id not in self._brokers:
                    logger.error(f"Broker {broker_id} not found")
                    return False
                
                broker_info = self._brokers[broker_id]
                broker_adapter = self._broker_adapters[broker_id]
                
                # Update status
                broker_info.status = BrokerStatus.CONNECTING
                
                # Connect broker
                success = await broker_adapter.connect()
                
                if success:
                    broker_info.status = BrokerStatus.ONLINE
                    broker_info.connected_at = datetime.now()
                    broker_info.last_activity = datetime.now()
                    
                    logger.info(f"Connected to broker {broker_id}")
                    
                    self._trigger_event('broker_connected', {
                        'broker_id': broker_id,
                        'broker_type': broker_info.broker_type.value
                    })
                else:
                    broker_info.status = BrokerStatus.ERROR
                    logger.error(f"Failed to connect to broker {broker_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to connect broker {broker_id}: {e}")
            return False
    
    async def disconnect_broker(self, broker_id: str) -> bool:
        """Disconnect from specific broker"""
        
        try:
            with self._lock:
                if broker_id not in self._brokers:
                    return True
                
                broker_info = self._brokers[broker_id]
                broker_adapter = self._broker_adapters[broker_id]
                
                # Disconnect broker
                success = await broker_adapter.disconnect()
                
                if success:
                    broker_info.status = BrokerStatus.OFFLINE
                    
                    logger.info(f"Disconnected from broker {broker_id}")
                    
                    self._trigger_event('broker_disconnected', {
                        'broker_id': broker_id,
                        'broker_type': broker_info.broker_type.value
                    })
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to disconnect broker {broker_id}: {e}")
            return False
    
    async def submit_order(self, order_request: OrderRequest) -> str:
        """Submit order for execution"""
        
        try:
            # Get available brokers
            available_brokers = [
                broker for broker in self._brokers.values()
                if broker.status == BrokerStatus.ONLINE
            ]
            
            if not available_brokers:
                raise RuntimeError("No online brokers available")
            
            # Route order
            routing_decisions = await self._order_router.route_order(order_request, available_brokers)
            
            if not routing_decisions:
                raise RuntimeError("No routing decisions made")
            
            # Execute orders
            execution_results = []
            
            for broker_info, routed_order in routing_decisions:
                try:
                    # Get broker adapter
                    broker_adapter = self._broker_adapters[broker_info.broker_id]
                    
                    # Convert to standard order
                    standard_order = self._convert_to_standard_order(routed_order)
                    
                    # Submit order
                    broker_order_id = await broker_adapter.submit_order(standard_order)
                    
                    # Track order
                    self._pending_orders[routed_order.request_id] = routed_order
                    
                    # Update metrics
                    self._performance_metrics['total_orders'] += 1
                    
                    execution_results.append({
                        'broker_id': broker_info.broker_id,
                        'order_id': routed_order.request_id,
                        'broker_order_id': broker_order_id
                    })
                    
                    logger.info(f"Submitted order {routed_order.request_id} to broker {broker_info.broker_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to submit order to broker {broker_info.broker_id}: {e}")
                    continue
            
            if not execution_results:
                raise RuntimeError("All order submissions failed")
            
            self._trigger_event('order_submitted', {
                'original_request_id': order_request.request_id,
                'execution_results': execution_results
            })
            
            return order_request.request_id
            
        except Exception as e:
            logger.error(f"Order submission failed: {e}")
            raise
    
    async def cancel_order(self, request_id: str) -> bool:
        """Cancel order"""
        
        try:
            if request_id not in self._pending_orders:
                logger.warning(f"Order {request_id} not found in pending orders")
                return False
            
            order_request = self._pending_orders[request_id]
            
            # Find and cancel with all relevant brokers
            success_count = 0
            
            for broker_id, broker_adapter in self._broker_adapters.items():
                try:
                    success = await broker_adapter.cancel_order(request_id)
                    if success:
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to cancel order {request_id} with broker {broker_id}: {e}")
            
            if success_count > 0:
                # Remove from pending orders
                del self._pending_orders[request_id]
                
                logger.info(f"Cancelled order {request_id}")
                
                self._trigger_event('order_cancelled', {
                    'request_id': request_id,
                    'brokers_cancelled': success_count
                })
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return False
    
    def get_broker_status(self, broker_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Get broker status information"""
        
        with self._lock:
            if broker_id:
                # Return specific broker status
                if broker_id not in self._brokers:
                    return {}
                
                broker_info = self._brokers[broker_id]
                return self._get_broker_status_dict(broker_info)
            
            else:
                # Return all broker statuses
                return [
                    self._get_broker_status_dict(broker_info)
                    for broker_info in self._brokers.values()
                ]
    
    def _get_broker_status_dict(self, broker_info: BrokerInfo) -> Dict[str, Any]:
        """Convert broker info to status dictionary"""
        
        return {
            'broker_id': broker_info.broker_id,
            'broker_type': broker_info.broker_type.value,
            'name': broker_info.name,
            'status': broker_info.status.value,
            'connection_id': broker_info.connection_id,
            'session_id': broker_info.session_id,
            'avg_latency': broker_info.avg_latency,
            'success_rate': broker_info.success_rate,
            'uptime': broker_info.uptime,
            'connected_at': broker_info.connected_at,
            'last_activity': broker_info.last_activity,
            'supported_order_types': [ot.value for ot in broker_info.supported_order_types],
            'supported_venues': [sv.value for sv in broker_info.supported_venues],
            'attributes': broker_info.attributes
        }
    
    def _convert_to_standard_order(self, order_request: OrderRequest) -> StandardOrder:
        """Convert order request to standard order"""
        
        return StandardOrder(
            order_id=order_request.request_id,
            symbol=order_request.symbol,
            action=order_request.action,
            quantity=order_request.quantity,
            order_type=order_request.order_type,
            limit_price=order_request.limit_price,
            stop_price=order_request.stop_price,
            time_in_force=order_request.time_in_force,
            display_size=order_request.display_size,
            min_quantity=order_request.min_quantity,
            client_order_id=order_request.client_order_id
        )
    
    async def _performance_monitor_loop(self) -> None:
        """Monitor broker performance"""
        
        while not self._stop_background_tasks:
            try:
                await self._update_broker_performance()
                await asyncio.sleep(self.config.metrics_collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitor loop: {e}")
                await asyncio.sleep(30)
    
    async def _update_broker_performance(self) -> None:
        """Update broker performance metrics"""
        
        current_time = datetime.now()
        
        for broker_id, broker_info in self._brokers.items():
            try:
                if broker_id not in self._broker_adapters:
                    continue
                
                broker_adapter = self._broker_adapters[broker_id]
                
                # Get broker metrics
                metrics = broker_adapter.get_metrics()
                
                # Update broker info
                broker_info.avg_latency = metrics.get('avg_response_time', 0) * 1000  # Convert to ms
                
                # Calculate success rate
                total_ops = metrics.get('orders_submitted', 0) + metrics.get('orders_cancelled', 0)
                successful_ops = metrics.get('orders_filled', 0) + metrics.get('orders_cancelled', 0)
                broker_info.success_rate = (successful_ops / max(total_ops, 1)) * 100
                
                # Calculate uptime
                if broker_info.connected_at:
                    uptime_seconds = (current_time - broker_info.connected_at).total_seconds()
                    broker_info.uptime = uptime_seconds / 3600.0  # Convert to hours
                
                # Update activity
                broker_info.last_activity = current_time
                
            except Exception as e:
                logger.error(f"Failed to update performance for broker {broker_id}: {e}")
    
    async def _failover_monitor_loop(self) -> None:
        """Monitor for failover conditions"""
        
        while not self._stop_background_tasks:
            try:
                await self._check_failover_conditions()
                await asyncio.sleep(self.config.recovery_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in failover monitor loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_failover_conditions(self) -> None:
        """Check for brokers requiring failover"""
        
        for broker_id, broker_info in self._brokers.items():
            try:
                # Check error rate
                if broker_info.success_rate < (1.0 - self.config.failover_threshold) * 100:
                    # Initiate failover
                    await self._initiate_failover(broker_id)
                
                # Check connectivity
                if broker_info.status == BrokerStatus.ERROR:
                    # Attempt recovery
                    await self._attempt_broker_recovery(broker_id)
                
            except Exception as e:
                logger.error(f"Error checking failover for broker {broker_id}: {e}")
    
    async def _initiate_failover(self, broker_id: str) -> None:
        """Initiate failover for problematic broker"""
        
        try:
            broker_info = self._brokers[broker_id]
            
            # Mark as degraded
            broker_info.status = BrokerStatus.DEGRADED
            
            logger.warning(f"Initiating failover for broker {broker_id}")
            
            # Trigger failover in connection manager
            if broker_info.connection_id:
                await self._connection_manager.failover(broker_info.connection_id)
            
            self._trigger_event('broker_failover', {
                'broker_id': broker_id,
                'reason': 'high_error_rate'
            })
            
        except Exception as e:
            logger.error(f"Failover initiation failed for broker {broker_id}: {e}")
    
    async def _attempt_broker_recovery(self, broker_id: str) -> None:
        """Attempt to recover failed broker"""
        
        try:
            logger.info(f"Attempting recovery for broker {broker_id}")
            
            # Try to reconnect
            success = await self.connect_broker(broker_id)
            
            if success:
                logger.info(f"Successfully recovered broker {broker_id}")
                
                self._trigger_event('broker_recovered', {
                    'broker_id': broker_id
                })
            else:
                logger.warning(f"Recovery failed for broker {broker_id}")
            
        except Exception as e:
            logger.error(f"Broker recovery failed for {broker_id}: {e}")
    
    def add_event_handler(self, event_type: str, 
                         handler: Callable[[Dict[str, Any]], None]) -> None:
        """Add event handler"""
        self._event_handlers[event_type].append(handler)
    
    def _trigger_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger event handlers"""
        for handler in self._event_handlers[event_type]:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get overall performance metrics"""
        
        return {
            'broker_metrics': self._performance_metrics.copy(),
            'routing_stats': self._order_router.get_routing_statistics(),
            'connection_stats': self._connection_manager.get_statistics(),
            'session_stats': self._session_manager.get_session_statistics(),
            'processing_stats': self._message_processor.get_metrics()
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        
        with self._lock:
            total_brokers = len(self._brokers)
            online_brokers = sum(1 for b in self._brokers.values() if b.status == BrokerStatus.ONLINE)
            degraded_brokers = sum(1 for b in self._brokers.values() if b.status == BrokerStatus.DEGRADED)
            
            health_score = (online_brokers / max(total_brokers, 1)) * 100
            
            return {
                'total_brokers': total_brokers,
                'online_brokers': online_brokers,
                'degraded_brokers': degraded_brokers,
                'offline_brokers': total_brokers - online_brokers - degraded_brokers,
                'health_score': health_score,
                'pending_orders': len(self._pending_orders),
                'system_status': 'healthy' if health_score >= 80 else 'degraded' if health_score >= 50 else 'critical'
            }