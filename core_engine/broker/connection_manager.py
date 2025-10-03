"""
Broker Engine - Connection Manager
Multi-broker connection management with pooling, failover, and monitoring
"""

import logging
import threading
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
import time
from collections import defaultdict, deque
import uuid
import warnings

from .broker_adapter import (
    BrokerAdapter, BrokerCredentials, BrokerType, ConnectionStatus,
    StandardOrder, StandardExecution, StandardPosition, StandardAccount
)

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ConnectionPriority(Enum):
    """Connection priority levels"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    BACKUP = "backup"
    EMERGENCY = "emergency"


class FailoverStrategy(Enum):
    """Failover strategies"""
    ROUND_ROBIN = "round_robin"
    PRIORITY_BASED = "priority_based"
    LOAD_BALANCED = "load_balanced"
    MANUAL = "manual"


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class ConnectionConfig:
    """Connection configuration"""
    # Connection parameters
    max_connections: int = 10
    connection_timeout: float = 30.0
    heartbeat_interval: float = 30.0
    
    # Retry settings
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    
    # Health check settings
    health_check_interval: float = 60.0
    health_timeout: float = 10.0
    
    # Failover settings
    failover_strategy: FailoverStrategy = FailoverStrategy.PRIORITY_BASED
    failover_threshold: float = 0.8  # 80% failure rate
    recovery_threshold: float = 0.2  # 20% failure rate
    
    # Pool settings
    min_pool_size: int = 1
    max_pool_size: int = 5
    idle_timeout: float = 300.0  # 5 minutes
    
    # Monitoring
    enable_monitoring: bool = True
    metric_window: int = 100  # Number of recent operations to track


@dataclass
class ConnectionInfo:
    """Connection information"""
    connection_id: str
    broker_adapter: BrokerAdapter
    priority: ConnectionPriority
    
    # Status
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    health_status: HealthStatus = HealthStatus.HEALTHY
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    connected_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    # Metrics
    successful_operations: int = 0
    failed_operations: int = 0
    total_operations: int = 0
    avg_response_time: float = 0.0
    
    # Pool info
    pool_id: Optional[str] = None
    is_pooled: bool = False
    
    # Metadata
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionPool:
    """Connection pool"""
    pool_id: str
    broker_type: BrokerType
    max_size: int
    min_size: int
    
    # Connections
    active_connections: List[ConnectionInfo] = field(default_factory=list)
    idle_connections: List[ConnectionInfo] = field(default_factory=list)
    
    # Pool stats
    total_created: int = 0
    total_destroyed: int = 0
    peak_active: int = 0
    
    # Settings
    idle_timeout: float = 300.0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: Optional[datetime] = None


class ConnectionMonitor:
    """Connection monitoring and health checks"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._connections: Dict[str, ConnectionInfo] = {}
        self._monitoring_task = None
        self._stop_monitoring = False
        
        # Metrics
        self._metrics_history = defaultdict(deque)
        self._alerts = []
        
        logger.info("Connection monitor initialized")
    
    def add_connection(self, connection: ConnectionInfo) -> None:
        """Add connection to monitoring"""
        self._connections[connection.connection_id] = connection
        logger.info(f"Added connection {connection.connection_id} to monitoring")
    
    def remove_connection(self, connection_id: str) -> None:
        """Remove connection from monitoring"""
        if connection_id in self._connections:
            del self._connections[connection_id]
            logger.info(f"Removed connection {connection_id} from monitoring")
    
    async def start_monitoring(self) -> None:
        """Start monitoring task"""
        if self._monitoring_task is None:
            self._stop_monitoring = False
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started connection monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring task"""
        self._stop_monitoring = True
        if self._monitoring_task:
            await self._monitoring_task
            self._monitoring_task = None
            logger.info("Stopped connection monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while not self._stop_monitoring:
            try:
                await self._perform_health_checks()
                await self._update_metrics()
                await self._check_alerts()
                
                await asyncio.sleep(self.config.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all connections"""
        for connection in self._connections.values():
            try:
                await self._health_check_connection(connection)
            except Exception as e:
                logger.error(f"Health check failed for {connection.connection_id}: {e}")
    
    async def _health_check_connection(self, connection: ConnectionInfo) -> None:
        """Perform health check on single connection"""
        try:
            start_time = time.time()
            
            # Perform health check
            if connection.broker_adapter.is_ready():
                health_check_result = await asyncio.wait_for(
                    connection.broker_adapter.health_check(),
                    timeout=self.config.health_timeout
                )
                
                response_time = time.time() - start_time
                
                if health_check_result:
                    connection.last_heartbeat = datetime.now()
                    connection.health_status = HealthStatus.HEALTHY
                    self._record_metric(connection.connection_id, 'health_check_time', response_time)
                else:
                    connection.health_status = HealthStatus.UNHEALTHY
                    self._record_alert(f"Health check failed for {connection.connection_id}")
            else:
                connection.health_status = HealthStatus.CRITICAL
                self._record_alert(f"Connection {connection.connection_id} not ready")
                
        except asyncio.TimeoutError:
            connection.health_status = HealthStatus.DEGRADED
            self._record_alert(f"Health check timeout for {connection.connection_id}")
        except Exception as e:
            connection.health_status = HealthStatus.CRITICAL
            self._record_alert(f"Health check error for {connection.connection_id}: {e}")
    
    async def _update_metrics(self) -> None:
        """Update connection metrics"""
        for connection in self._connections.values():
            # Calculate failure rate
            if connection.total_operations > 0:
                failure_rate = connection.failed_operations / connection.total_operations
                self._record_metric(connection.connection_id, 'failure_rate', failure_rate)
            
            # Update activity metrics
            if connection.last_activity:
                idle_time = (datetime.now() - connection.last_activity).total_seconds()
                self._record_metric(connection.connection_id, 'idle_time', idle_time)
    
    async def _check_alerts(self) -> None:
        """Check for alert conditions"""
        current_time = datetime.now()
        
        for connection in self._connections.values():
            # Check for stale connections
            if connection.last_heartbeat:
                time_since_heartbeat = (current_time - connection.last_heartbeat).total_seconds()
                if time_since_heartbeat > self.config.heartbeat_interval * 2:
                    self._record_alert(f"Stale connection detected: {connection.connection_id}")
            
            # Check failure rate
            if connection.total_operations >= 10:  # Minimum operations for meaningful rate
                failure_rate = connection.failed_operations / connection.total_operations
                if failure_rate > self.config.failover_threshold:
                    self._record_alert(f"High failure rate for {connection.connection_id}: {failure_rate:.2%}")
    
    def _record_metric(self, connection_id: str, metric_name: str, value: float) -> None:
        """Record metric value"""
        key = f"{connection_id}:{metric_name}"
        history = self._metrics_history[key]
        
        history.append({
            'timestamp': datetime.now(),
            'value': value
        })
        
        # Keep only recent history
        while len(history) > self.config.metric_window:
            history.popleft()
    
    def _record_alert(self, message: str) -> None:
        """Record alert"""
        alert = {
            'timestamp': datetime.now(),
            'message': message,
            'level': 'WARNING'
        }
        
        self._alerts.append(alert)
        
        # Keep only recent alerts
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-50:]  # Keep last 50
        
        logger.warning(f"Connection alert: {message}")
    
    def get_connection_health(self, connection_id: str) -> Dict[str, Any]:
        """Get health information for connection"""
        if connection_id not in self._connections:
            return {}
        
        connection = self._connections[connection_id]
        
        return {
            'connection_id': connection_id,
            'status': connection.status.value,
            'health_status': connection.health_status.value,
            'last_heartbeat': connection.last_heartbeat,
            'last_activity': connection.last_activity,
            'total_operations': connection.total_operations,
            'successful_operations': connection.successful_operations,
            'failed_operations': connection.failed_operations,
            'failure_rate': connection.failed_operations / max(connection.total_operations, 1),
            'avg_response_time': connection.avg_response_time
        }
    
    def get_metrics(self, connection_id: str, metric_name: str) -> List[Dict[str, Any]]:
        """Get metric history"""
        key = f"{connection_id}:{metric_name}"
        return list(self._metrics_history.get(key, []))
    
    def get_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        return self._alerts[-limit:] if self._alerts else []


class ConnectionManager:
    """
    Multi-Broker Connection Manager
    
    Manages connections to multiple brokers with pooling,
    failover, health monitoring, and load balancing.
    """
    
    def __init__(self, config: Optional[ConnectionConfig] = None):
        """Initialize connection manager"""
        
        self.config = config or ConnectionConfig()
        
        # Connection tracking
        self._connections: Dict[str, ConnectionInfo] = {}
        self._pools: Dict[str, ConnectionPool] = {}
        self._broker_connections: Dict[BrokerType, List[str]] = defaultdict(list)
        
        # Connection selection
        self._round_robin_index: Dict[BrokerType, int] = defaultdict(int)
        
        # Monitoring
        self._monitor = ConnectionMonitor(self.config)
        self._monitoring_enabled = self.config.enable_monitoring
        
        # Async management
        self._background_tasks: Set[asyncio.Task] = set()
        
        # Event handlers
        self._event_handlers = defaultdict(list)
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        logger.info("Connection manager initialized")
    
    async def start(self) -> None:
        """Start connection manager"""
        try:
            if self._monitoring_enabled:
                await self._monitor.start_monitoring()
            
            # Start background tasks
            self._background_tasks.add(
                asyncio.create_task(self._pool_maintenance_loop())
            )
            
            logger.info("Connection manager started")
            
        except Exception as e:
            logger.error(f"Failed to start connection manager: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop connection manager"""
        try:
            # Stop monitoring
            if self._monitoring_enabled:
                await self._monitor.stop_monitoring()
            
            # Cancel background tasks
            for task in self._background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
            # Disconnect all connections
            await self.disconnect_all()
            
            logger.info("Connection manager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping connection manager: {e}")
    
    async def add_broker(self, credentials: BrokerCredentials, 
                        priority: ConnectionPriority = ConnectionPriority.PRIMARY,
                        pool_size: Optional[int] = None) -> str:
        """Add broker connection"""
        
        try:
            with self._lock:
                # Create broker adapter
                broker_adapter = BrokerAdapter(credentials)
                
                # Generate connection ID
                connection_id = f"{credentials.broker_type.value}_{uuid.uuid4().hex[:8]}"
                
                # Create connection info
                connection_info = ConnectionInfo(
                    connection_id=connection_id,
                    broker_adapter=broker_adapter,
                    priority=priority
                )
                
                # Store connection
                self._connections[connection_id] = connection_info
                self._broker_connections[credentials.broker_type].append(connection_id)
                
                # Add to monitoring
                if self._monitoring_enabled:
                    self._monitor.add_connection(connection_info)
                
                # Create pool if specified
                if pool_size and pool_size > 1:
                    await self._create_pool(credentials.broker_type, pool_size)
                
                logger.info(f"Added broker {credentials.broker_type.value} with connection {connection_id}")
                
                self._trigger_event('broker_added', {
                    'connection_id': connection_id,
                    'broker_type': credentials.broker_type.value,
                    'priority': priority.value
                })
                
                return connection_id
                
        except Exception as e:
            logger.error(f"Failed to add broker: {e}")
            raise
    
    async def remove_broker(self, connection_id: str) -> bool:
        """Remove broker connection"""
        
        try:
            with self._lock:
                if connection_id not in self._connections:
                    logger.warning(f"Connection {connection_id} not found")
                    return False
                
                connection = self._connections[connection_id]
                
                # Disconnect if connected
                if connection.status in [ConnectionStatus.CONNECTED, ConnectionStatus.READY]:
                    await connection.broker_adapter.disconnect()
                
                # Remove from pools
                if connection.pool_id:
                    await self._remove_from_pool(connection)
                
                # Remove from monitoring
                if self._monitoring_enabled:
                    self._monitor.remove_connection(connection_id)
                
                # Remove from tracking
                broker_type = connection.broker_adapter.broker_type
                if connection_id in self._broker_connections[broker_type]:
                    self._broker_connections[broker_type].remove(connection_id)
                
                del self._connections[connection_id]
                
                logger.info(f"Removed broker connection {connection_id}")
                
                self._trigger_event('broker_removed', {
                    'connection_id': connection_id,
                    'broker_type': broker_type.value
                })
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove broker {connection_id}: {e}")
            return False
    
    async def connect(self, connection_id: Optional[str] = None, 
                     broker_type: Optional[BrokerType] = None) -> bool:
        """Connect to broker(s)"""
        
        try:
            # Determine which connections to connect
            if connection_id:
                connections = [self._connections[connection_id]] if connection_id in self._connections else []
            elif broker_type:
                connection_ids = self._broker_connections[broker_type]
                connections = [self._connections[cid] for cid in connection_ids]
            else:
                connections = list(self._connections.values())
            
            if not connections:
                logger.warning("No connections to connect")
                return False
            
            # Connect all specified connections
            success_count = 0
            for connection in connections:
                try:
                    success = await self._connect_single(connection)
                    if success:
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to connect {connection.connection_id}: {e}")
            
            total_connections = len(connections)
            logger.info(f"Connected {success_count}/{total_connections} connections")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self, connection_id: Optional[str] = None,
                        broker_type: Optional[BrokerType] = None) -> bool:
        """Disconnect from broker(s)"""
        
        try:
            # Determine which connections to disconnect
            if connection_id:
                connections = [self._connections[connection_id]] if connection_id in self._connections else []
            elif broker_type:
                connection_ids = self._broker_connections[broker_type]
                connections = [self._connections[cid] for cid in connection_ids]
            else:
                connections = list(self._connections.values())
            
            # Disconnect all specified connections
            success_count = 0
            for connection in connections:
                try:
                    success = await connection.broker_adapter.disconnect()
                    if success:
                        connection.status = ConnectionStatus.DISCONNECTED
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to disconnect {connection.connection_id}: {e}")
            
            total_connections = len(connections)
            logger.info(f"Disconnected {success_count}/{total_connections} connections")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Disconnection failed: {e}")
            return False
    
    async def disconnect_all(self) -> None:
        """Disconnect all connections"""
        await self.disconnect()
    
    def get_connection(self, broker_type: BrokerType,
                      require_ready: bool = True) -> Optional[BrokerAdapter]:
        """Get available connection for broker type"""
        
        try:
            connection_ids = self._broker_connections[broker_type]
            
            if not connection_ids:
                logger.warning(f"No connections available for {broker_type.value}")
                return None
            
            # Filter connections based on requirements
            available_connections = []
            for connection_id in connection_ids:
                connection = self._connections[connection_id]
                
                if require_ready and connection.status != ConnectionStatus.READY:
                    continue
                
                available_connections.append(connection)
            
            if not available_connections:
                logger.warning(f"No ready connections available for {broker_type.value}")
                return None
            
            # Select connection based on strategy
            selected_connection = self._select_connection(broker_type, available_connections)
            
            if selected_connection:
                selected_connection.last_activity = datetime.now()
                return selected_connection.broker_adapter
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get connection for {broker_type.value}: {e}")
            return None
    
    def get_all_connections(self, broker_type: Optional[BrokerType] = None) -> List[BrokerAdapter]:
        """Get all connections, optionally filtered by broker type"""
        
        connections = []
        
        try:
            if broker_type:
                connection_ids = self._broker_connections[broker_type]
                for connection_id in connection_ids:
                    connection = self._connections[connection_id]
                    connections.append(connection.broker_adapter)
            else:
                for connection in self._connections.values():
                    connections.append(connection.broker_adapter)
            
            return connections
            
        except Exception as e:
            logger.error(f"Failed to get connections: {e}")
            return []
    
    def get_connection_status(self, connection_id: Optional[str] = None,
                            broker_type: Optional[BrokerType] = None) -> Dict[str, Any]:
        """Get connection status information"""
        
        try:
            if connection_id:
                if connection_id not in self._connections:
                    return {}
                
                connection = self._connections[connection_id]
                return self._get_connection_info(connection)
            
            elif broker_type:
                connection_ids = self._broker_connections[broker_type]
                status = {}
                for cid in connection_ids:
                    connection = self._connections[cid]
                    status[cid] = self._get_connection_info(connection)
                return status
            
            else:
                # Return all connections
                status = {}
                for connection in self._connections.values():
                    status[connection.connection_id] = self._get_connection_info(connection)
                return status
                
        except Exception as e:
            logger.error(f"Failed to get connection status: {e}")
            return {}
    
    async def failover(self, failed_connection_id: str) -> Optional[str]:
        """Perform failover to backup connection"""
        
        try:
            if failed_connection_id not in self._connections:
                logger.warning(f"Failed connection {failed_connection_id} not found")
                return None
            
            failed_connection = self._connections[failed_connection_id]
            broker_type = failed_connection.broker_adapter.broker_type
            
            # Mark failed connection as unhealthy
            failed_connection.status = ConnectionStatus.ERROR
            
            # Find backup connections
            backup_connections = []
            for connection_id in self._broker_connections[broker_type]:
                if connection_id != failed_connection_id:
                    connection = self._connections[connection_id]
                    if connection.priority in [ConnectionPriority.SECONDARY, ConnectionPriority.BACKUP]:
                        backup_connections.append(connection)
            
            if not backup_connections:
                logger.warning(f"No backup connections available for {broker_type.value}")
                return None
            
            # Sort by priority
            backup_connections.sort(key=lambda c: c.priority.value)
            
            # Try to connect to backup
            for backup_connection in backup_connections:
                try:
                    success = await self._connect_single(backup_connection)
                    if success:
                        logger.info(f"Failover successful to {backup_connection.connection_id}")
                        
                        self._trigger_event('failover_successful', {
                            'failed_connection': failed_connection_id,
                            'backup_connection': backup_connection.connection_id,
                            'broker_type': broker_type.value
                        })
                        
                        return backup_connection.connection_id
                        
                except Exception as e:
                    logger.error(f"Failover attempt failed for {backup_connection.connection_id}: {e}")
                    continue
            
            logger.error(f"All failover attempts failed for {broker_type.value}")
            return None
            
        except Exception as e:
            logger.error(f"Failover failed: {e}")
            return None
    
    async def _connect_single(self, connection: ConnectionInfo) -> bool:
        """Connect single connection with retry logic"""
        
        for attempt in range(self.config.max_retry_attempts):
            try:
                connection.status = ConnectionStatus.CONNECTING
                
                success = await asyncio.wait_for(
                    connection.broker_adapter.connect(),
                    timeout=self.config.connection_timeout
                )
                
                if success:
                    connection.status = connection.broker_adapter.connection_status
                    connection.connected_at = datetime.now()
                    connection.last_heartbeat = datetime.now()
                    
                    logger.info(f"Connected {connection.connection_id}")
                    
                    self._trigger_event('connection_established', {
                        'connection_id': connection.connection_id,
                        'broker_type': connection.broker_adapter.broker_type.value
                    })
                    
                    return True
                
            except asyncio.TimeoutError:
                logger.warning(f"Connection timeout for {connection.connection_id} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Connection failed for {connection.connection_id} (attempt {attempt + 1}): {e}")
            
            # Wait before retry
            if attempt < self.config.max_retry_attempts - 1:
                delay = self.config.retry_delay * (self.config.backoff_multiplier ** attempt)
                await asyncio.sleep(delay)
        
        connection.status = ConnectionStatus.ERROR
        
        self._trigger_event('connection_failed', {
            'connection_id': connection.connection_id,
            'broker_type': connection.broker_adapter.broker_type.value
        })
        
        return False
    
    def _select_connection(self, broker_type: BrokerType, 
                          connections: List[ConnectionInfo]) -> Optional[ConnectionInfo]:
        """Select connection based on strategy"""
        
        if not connections:
            return None
        
        if self.config.failover_strategy == FailoverStrategy.PRIORITY_BASED:
            # Sort by priority and select best
            connections.sort(key=lambda c: c.priority.value)
            return connections[0]
        
        elif self.config.failover_strategy == FailoverStrategy.ROUND_ROBIN:
            # Round robin selection
            index = self._round_robin_index[broker_type]
            selected = connections[index % len(connections)]
            self._round_robin_index[broker_type] = (index + 1) % len(connections)
            return selected
        
        elif self.config.failover_strategy == FailoverStrategy.LOAD_BALANCED:
            # Select connection with lowest load
            return min(connections, key=lambda c: c.total_operations)
        
        else:
            # Default to first available
            return connections[0]
    
    async def _create_pool(self, broker_type: BrokerType, max_size: int) -> str:
        """Create connection pool for broker type"""
        
        pool_id = f"{broker_type.value}_pool_{uuid.uuid4().hex[:8]}"
        
        pool = ConnectionPool(
            pool_id=pool_id,
            broker_type=broker_type,
            max_size=max_size,
            min_size=self.config.min_pool_size,
            idle_timeout=self.config.idle_timeout
        )
        
        self._pools[pool_id] = pool
        
        logger.info(f"Created connection pool {pool_id} for {broker_type.value}")
        
        return pool_id
    
    async def _remove_from_pool(self, connection: ConnectionInfo) -> None:
        """Remove connection from pool"""
        
        if not connection.pool_id:
            return
        
        pool = self._pools.get(connection.pool_id)
        if not pool:
            return
        
        # Remove from active connections
        if connection in pool.active_connections:
            pool.active_connections.remove(connection)
        
        # Remove from idle connections
        if connection in pool.idle_connections:
            pool.idle_connections.remove(connection)
        
        connection.pool_id = None
        connection.is_pooled = False
    
    async def _pool_maintenance_loop(self) -> None:
        """Background task for pool maintenance"""
        
        while True:
            try:
                await self._maintain_pools()
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Error in pool maintenance: {e}")
                await asyncio.sleep(10)
    
    async def _maintain_pools(self) -> None:
        """Maintain connection pools"""
        
        current_time = datetime.now()
        
        for pool in self._pools.values():
            # Remove idle connections that have timed out
            expired_connections = []
            for connection in pool.idle_connections:
                if connection.last_activity:
                    idle_time = (current_time - connection.last_activity).total_seconds()
                    if idle_time > pool.idle_timeout:
                        expired_connections.append(connection)
            
            for connection in expired_connections:
                await self._remove_from_pool(connection)
                await connection.broker_adapter.disconnect()
                logger.info(f"Removed expired connection {connection.connection_id} from pool")
    
    def _get_connection_info(self, connection: ConnectionInfo) -> Dict[str, Any]:
        """Get connection information dictionary"""
        
        return {
            'connection_id': connection.connection_id,
            'broker_type': connection.broker_adapter.broker_type.value,
            'priority': connection.priority.value,
            'status': connection.status.value,
            'health_status': connection.health_status.value,
            'created_at': connection.created_at,
            'connected_at': connection.connected_at,
            'last_heartbeat': connection.last_heartbeat,
            'last_activity': connection.last_activity,
            'successful_operations': connection.successful_operations,
            'failed_operations': connection.failed_operations,
            'total_operations': connection.total_operations,
            'failure_rate': connection.failed_operations / max(connection.total_operations, 1),
            'avg_response_time': connection.avg_response_time,
            'is_pooled': connection.is_pooled,
            'pool_id': connection.pool_id
        }
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add event handler"""
        self._event_handlers[event_type].append(handler)
    
    def _trigger_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger event handlers"""
        for handler in self._event_handlers[event_type]:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get connection manager statistics"""
        
        total_connections = len(self._connections)
        connected_count = sum(1 for c in self._connections.values() 
                            if c.status in [ConnectionStatus.CONNECTED, ConnectionStatus.READY])
        ready_count = sum(1 for c in self._connections.values() 
                         if c.status == ConnectionStatus.READY)
        
        # Broker type breakdown
        broker_stats = {}
        for broker_type, connection_ids in self._broker_connections.items():
            connections = [self._connections[cid] for cid in connection_ids]
            broker_stats[broker_type.value] = {
                'total': len(connections),
                'connected': sum(1 for c in connections 
                               if c.status in [ConnectionStatus.CONNECTED, ConnectionStatus.READY]),
                'ready': sum(1 for c in connections if c.status == ConnectionStatus.READY)
            }
        
        # Pool statistics
        pool_stats = {}
        for pool_id, pool in self._pools.items():
            pool_stats[pool_id] = {
                'active_connections': len(pool.active_connections),
                'idle_connections': len(pool.idle_connections),
                'total_created': pool.total_created,
                'total_destroyed': pool.total_destroyed,
                'peak_active': pool.peak_active
            }
        
        return {
            'total_connections': total_connections,
            'connected_connections': connected_count,
            'ready_connections': ready_count,
            'connection_rate': connected_count / max(total_connections, 1),
            'ready_rate': ready_count / max(total_connections, 1),
            'broker_statistics': broker_stats,
            'pool_statistics': pool_stats,
            'monitoring_enabled': self._monitoring_enabled
        }