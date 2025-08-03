#!/usr/bin/env python3
"""
System Orchestrator
===================

This module provides system-wide orchestration capabilities for integrating
all modules in the core system. It manages module registration, inter-module
communication, health monitoring, and system coordination.

Author: Infrastructure Integration Team
Date: 2025-01-27
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class ModuleStatus(Enum):
    """Module status enumeration"""
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"

class MessageType(Enum):
    """Message type enumeration"""
    COMMAND = "command"
    EVENT = "event"
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    HEALTH_CHECK = "health_check"

@dataclass
class OrchestrationConfig:
    """Configuration for system orchestration"""
    
    # Module Management
    auto_register_modules: bool = True
    health_check_interval: float = 30.0  # seconds
    module_timeout: float = 60.0  # seconds
    
    # Messaging Configuration
    enable_messaging: bool = True
    message_timeout: float = 10.0  # seconds
    max_message_queue_size: int = 1000
    
    # Monitoring Configuration
    enable_monitoring: bool = True
    metrics_collection_interval: float = 60.0  # seconds
    performance_tracking: bool = True
    
    # Integration Configuration
    integration_points: List[str] = field(default_factory=lambda: [
        "signal_generation",
        "execution_engine", 
        "risk_management",
        "analytics",
        "ai_infrastructure",
        "market_data"
    ])
    
    # Error Handling
    retry_attempts: int = 3
    retry_delay: float = 5.0  # seconds
    graceful_shutdown: bool = True

@dataclass
class ModuleInfo:
    """Information about a registered module"""
    
    name: str
    module_type: str
    version: str
    status: ModuleStatus
    registration_time: datetime
    last_health_check: Optional[datetime] = None
    health_score: float = 1.0
    capabilities: List[str] = field(default_factory=list)
    integration_points: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics
    message_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    
    # Health metrics
    is_healthy: bool = True
    error_message: Optional[str] = None

@dataclass
class SystemMessage:
    """System message for inter-module communication"""
    
    message_id: str
    message_type: MessageType
    source_module: str
    payload: Dict[str, Any]
    target_module: Optional[str] = None
    topic: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 0
    ttl: Optional[float] = None  # Time to live in seconds

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    
    module_name: str
    is_healthy: bool
    health_score: float
    response_time: float
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)

class SystemOrchestrator:
    """System orchestrator for managing all modules and their interactions"""
    
    def __init__(self, config: Optional[OrchestrationConfig] = None):
        """Initialize the system orchestrator"""
        self.config = config or OrchestrationConfig()
        self.modules: Dict[str, ModuleInfo] = {}
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.health_checkers: Dict[str, Callable] = {}
        self.metrics_collectors: Dict[str, Callable] = {}
        
        # Internal state
        self._running = False
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._metrics_collector_task: Optional[asyncio.Task] = None
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.max_message_queue_size)
        
        # Threading
        self._lock = threading.RLock()
        self._message_processor_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self._performance_metrics: Dict[str, Any] = {
            "total_messages": 0,
            "total_errors": 0,
            "avg_response_time": 0.0,
            "start_time": datetime.now()
        }
        
        logger.info("SystemOrchestrator initialized")
    
    async def start(self):
        """Start the system orchestrator"""
        if self._running:
            logger.warning("SystemOrchestrator is already running")
            return
        
        logger.info("Starting SystemOrchestrator...")
        self._running = True
        
        # Start background tasks
        self._health_monitor_task = asyncio.create_task(self._start_health_monitoring())
        self._metrics_collector_task = asyncio.create_task(self._start_metrics_collection())
        self._message_processor_task = asyncio.create_task(self._process_messages())
        
        logger.info("SystemOrchestrator started successfully")
    
    async def stop(self):
        """Stop the system orchestrator"""
        if not self._running:
            logger.warning("SystemOrchestrator is not running")
            return
        
        logger.info("Stopping SystemOrchestrator...")
        self._running = False
        
        # Cancel background tasks
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
        if self._metrics_collector_task:
            self._metrics_collector_task.cancel()
        if self._message_processor_task:
            self._message_processor_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(
            self._health_monitor_task, 
            self._metrics_collector_task, 
            self._message_processor_task,
            return_exceptions=True
        )
        
        logger.info("SystemOrchestrator stopped")
    
    def register_module(
        self, 
        name: str, 
        module_type: str, 
        version: str,
        capabilities: Optional[List[str]] = None,
        integration_points: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        health_checker: Optional[Callable] = None,
        metrics_collector: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register a module with the orchestrator"""
        with self._lock:
            if name in self.modules:
                logger.warning(f"Module {name} is already registered")
                return False
            
            module_info = ModuleInfo(
                name=name,
                module_type=module_type,
                version=version,
                status=ModuleStatus.REGISTERED,
                registration_time=datetime.now(),
                capabilities=capabilities or [],
                integration_points=integration_points or [],
                dependencies=dependencies or [],
                metadata=metadata or {}
            )
            
            self.modules[name] = module_info
            
            # Register health checker and metrics collector
            if health_checker:
                self.health_checkers[name] = health_checker
            if metrics_collector:
                self.metrics_collectors[name] = metrics_collector
            
            # Initialize message handlers for this module
            self.message_handlers[name] = []
            
            logger.info(f"Module {name} ({module_type} v{version}) registered successfully")
            return True
    
    def unregister_module(self, name: str) -> bool:
        """Unregister a module from the orchestrator"""
        with self._lock:
            if name not in self.modules:
                logger.warning(f"Module {name} is not registered")
                return False
            
            # Clean up handlers
            if name in self.health_checkers:
                del self.health_checkers[name]
            if name in self.metrics_collectors:
                del self.metrics_collectors[name]
            if name in self.message_handlers:
                del self.message_handlers[name]
            
            # Remove module from modules dictionary
            del self.modules[name]
            
            logger.info(f"Module {name} unregistered successfully")
            return True
    
    async def send_message(
        self, 
        source_module: str, 
        target_module: str, 
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: int = 0,
        timeout: Optional[float] = None
    ) -> Optional[SystemMessage]:
        """Send a message to a specific module"""
        if not self._running:
            logger.error("SystemOrchestrator is not running")
            return None
        
        if target_module not in self.modules:
            logger.error(f"Target module {target_module} is not registered")
            return None
        
        message = SystemMessage(
            message_id=f"{source_module}_{target_module}_{int(time.time())}",
            message_type=message_type,
            source_module=source_module,
            target_module=target_module,
            payload=payload,
            priority=priority,
            ttl=timeout or self.config.message_timeout
        )
        
        try:
            await self._message_queue.put(message)
            logger.debug(f"Message sent from {source_module} to {target_module}")
            return message
        except asyncio.QueueFull:
            logger.error("Message queue is full")
            return None
    
    async def broadcast_message(
        self, 
        source_module: str, 
        message_type: MessageType,
        payload: Dict[str, Any],
        topic: Optional[str] = None,
        priority: int = 0
    ) -> List[SystemMessage]:
        """Broadcast a message to all modules"""
        if not self._running:
            logger.error("SystemOrchestrator is not running")
            return []
        
        messages = []
        for module_name in self.modules:
            if module_name != source_module and self.modules[module_name].status in [ModuleStatus.REGISTERED, ModuleStatus.RUNNING, ModuleStatus.HEALTHY]:
                message = SystemMessage(
                    message_id=f"{source_module}_broadcast_{int(time.time())}_{module_name}",
                    message_type=message_type,
                    source_module=source_module,
                    target_module=module_name,
                    topic=topic,
                    payload=payload,
                    priority=priority
                )
                
                try:
                    await self._message_queue.put(message)
                    messages.append(message)
                except asyncio.QueueFull:
                    logger.error("Message queue is full during broadcast")
                    break
        
        logger.debug(f"Broadcast message sent from {source_module} to {len(messages)} modules")
        return messages
    
    def add_message_handler(self, module_name: str, handler: Callable):
        """Add a message handler for a module"""
        if module_name not in self.message_handlers:
            self.message_handlers[module_name] = []
        
        self.message_handlers[module_name].append(handler)
        logger.debug(f"Message handler added for module {module_name}")
    
    async def _process_messages(self):
        """Process messages from the queue"""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(), 
                    timeout=1.0
                )
                
                # Update performance metrics
                self._performance_metrics["total_messages"] += 1
                
                # Process message
                await self._handle_message(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                self._performance_metrics["total_errors"] += 1
    
    async def _handle_message(self, message: SystemMessage):
        """Handle a single message"""
        if not message.target_module:
            return
        
        if message.target_module not in self.message_handlers:
            logger.warning(f"No message handlers for module {message.target_module}")
            return
        
        # Call all handlers for the target module
        for handler in self.message_handlers[message.target_module]:
            try:
                start_time = time.time()
                await handler(message)
                response_time = time.time() - start_time
                
                # Update module performance metrics
                if message.target_module in self.modules:
                    module = self.modules[message.target_module]
                    module.message_count += 1
                    module.avg_response_time = (
                        (module.avg_response_time * (module.message_count - 1) + response_time) / 
                        module.message_count
                    )
                
            except Exception as e:
                logger.error(f"Error in message handler for {message.target_module}: {e}")
                if message.target_module in self.modules:
                    self.modules[message.target_module].error_count += 1
                    self.modules[message.target_module].error_message = str(e)
                # Increment system error count
                self._performance_metrics["total_errors"] += 1
    
    async def _start_health_monitoring(self):
        """Start health monitoring for all modules"""
        while self._running:
            try:
                await self._check_all_modules_health()
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
    
    async def _check_all_modules_health(self):
        """Check health of all registered modules"""
        for module_name, health_checker in self.health_checkers.items():
            try:
                start_time = time.time()
                result = await health_checker()
                response_time = time.time() - start_time
                
                # Update module health
                if module_name in self.modules:
                    module = self.modules[module_name]
                    module.last_health_check = datetime.now()
                    module.is_healthy = result.get('is_healthy', True)
                    module.health_score = result.get('health_score', 1.0)
                    module.error_message = result.get('error_message')
                    
                    # Update status based on health
                    if module.is_healthy:
                        module.status = ModuleStatus.HEALTHY
                    else:
                        module.status = ModuleStatus.UNHEALTHY
                
            except Exception as e:
                logger.error(f"Health check failed for {module_name}: {e}")
                if module_name in self.modules:
                    module = self.modules[module_name]
                    module.is_healthy = False
                    module.health_score = 0.0
                    module.error_message = str(e)
                    module.status = ModuleStatus.ERROR
    
    async def _start_metrics_collection(self):
        """Start metrics collection for all modules"""
        while self._running:
            try:
                await self._collect_all_modules_metrics()
                await asyncio.sleep(self.config.metrics_collection_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
    
    async def _collect_all_modules_metrics(self):
        """Collect metrics from all modules"""
        for module_name, metrics_collector in self.metrics_collectors.items():
            try:
                metrics = await metrics_collector()
                
                # Update module metrics
                if module_name in self.modules:
                    module = self.modules[module_name]
                    module.metadata.update(metrics)
                
            except Exception as e:
                logger.error(f"Metrics collection failed for {module_name}: {e}")
    
    def get_module_status(self, module_name: str) -> Optional[ModuleInfo]:
        """Get status of a specific module"""
        return self.modules.get(module_name)
    
    def get_all_modules_status(self) -> Dict[str, ModuleInfo]:
        """Get status of all modules"""
        return self.modules.copy()
    
    def get_healthy_modules(self) -> List[str]:
        """Get list of healthy modules"""
        return [
            name for name, module in self.modules.items() 
            if module.is_healthy and module.status in [ModuleStatus.RUNNING, ModuleStatus.HEALTHY]
        ]
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health"""
        total_modules = len(self.modules)
        healthy_modules = len(self.get_healthy_modules())
        
        return {
            "total_modules": total_modules,
            "healthy_modules": healthy_modules,
            "health_percentage": (healthy_modules / total_modules * 100) if total_modules > 0 else 0,
            "system_status": "healthy" if healthy_modules == total_modules else "degraded" if healthy_modules > 0 else "unhealthy",
            "performance_metrics": self._performance_metrics.copy(),
            "uptime": (datetime.now() - self._performance_metrics["start_time"]).total_seconds()
        }
    
    def get_integration_points(self) -> Dict[str, List[str]]:
        """Get all integration points and their modules"""
        integration_points = {}
        for module_name, module in self.modules.items():
            if module.integration_points:
                for point in module.integration_points:
                    if point not in integration_points:
                        integration_points[point] = []
                    integration_points[point].append(module_name)
        return integration_points 