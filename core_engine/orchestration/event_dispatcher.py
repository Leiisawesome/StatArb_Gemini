"""
Event Dispatcher for Core Engine Orchestration
Handles event-driven communication between components
"""
from typing import Dict, List, Any, Optional, Callable, Union, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import threading
import logging
import queue
import json
import uuid
from concurrent.futures import ThreadPoolExecutor

class EventPriority(Enum):
    """Event priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

class EventType(Enum):
    """Core event types"""
    SYSTEM_STATE_CHANGE = "system_state_change"
    COMPONENT_STATE_CHANGE = "component_state_change"
    MARKET_DATA_UPDATE = "market_data_update"
    ORDER_EVENT = "order_event"
    POSITION_UPDATE = "position_update"
    RISK_ALERT = "risk_alert"
    PERFORMANCE_UPDATE = "performance_update"
    ERROR_EVENT = "error_event"
    WARNING_EVENT = "warning_event"
    CUSTOM_EVENT = "custom_event"

@dataclass
class Event:
    """Core event class"""
    event_id: str
    event_type: EventType
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    target: Optional[str] = None  # Specific target component
    ttl: Optional[datetime] = None  # Time to live
    correlation_id: Optional[str] = None  # For event correlation
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'priority': self.priority.value,
            'target': self.target,
            'ttl': self.ttl.isoformat() if self.ttl else None,
            'correlation_id': self.correlation_id,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(
            event_id=data['event_id'],
            event_type=EventType(data['event_type']),
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data['data'],
            priority=EventPriority(data['priority']),
            target=data.get('target'),
            ttl=datetime.fromisoformat(data['ttl']) if data.get('ttl') else None,
            correlation_id=data.get('correlation_id'),
            metadata=data.get('metadata', {})
        )

@dataclass
class EventHandler:
    """Event handler registration"""
    handler_id: str
    event_types: Set[EventType]
    callback: Callable[[Event], Any]
    component: str
    async_handler: bool = False
    filter_func: Optional[Callable[[Event], bool]] = None
    priority: int = 5  # Handler priority (1 = highest)

class EventBus:
    """
    Central event bus for component communication
    """
    
    def __init__(self, max_workers: int = 4):
        self.logger = logging.getLogger(__name__)
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Event handling
        self.handlers: Dict[str, EventHandler] = {}
        self.event_types_to_handlers: Dict[EventType, List[str]] = {}
        self.event_queue = queue.PriorityQueue()
        self.event_history: List[Event] = []
        
        # Threading
        self.processing_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        # Event filtering and routing
        self.global_filters: List[Callable[[Event], bool]] = []
        self.routing_rules: Dict[str, Callable[[Event], str]] = {}
        
        # Metrics and monitoring
        self.event_metrics = {
            'total_events': 0,
            'events_by_type': {},
            'events_by_source': {},
            'handler_executions': {},
            'failed_handlers': {},
            'average_processing_time': 0.0
        }
        
        # Locks
        self.handlers_lock = threading.RLock()
        self.metrics_lock = threading.Lock()
        
        # Initialize event type mappings
        for event_type in EventType:
            self.event_types_to_handlers[event_type] = []
    
    def register_handler(self, handler: EventHandler) -> bool:
        """Register an event handler"""
        try:
            with self.handlers_lock:
                if handler.handler_id in self.handlers:
                    self.logger.warning(f"Handler {handler.handler_id} already registered")
                    return False
                
                self.handlers[handler.handler_id] = handler
                
                # Update event type mappings
                for event_type in handler.event_types:
                    if event_type not in self.event_types_to_handlers:
                        self.event_types_to_handlers[event_type] = []
                    
                    self.event_types_to_handlers[event_type].append(handler.handler_id)
                    
                    # Sort by priority
                    self.event_types_to_handlers[event_type].sort(
                        key=lambda h_id: self.handlers[h_id].priority
                    )
                
                self.logger.info(f"Registered handler {handler.handler_id} for events: {[et.value for et in handler.event_types]}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error registering handler {handler.handler_id}: {e}")
            return False
    
    def unregister_handler(self, handler_id: str) -> bool:
        """Unregister an event handler"""
        try:
            with self.handlers_lock:
                if handler_id not in self.handlers:
                    return False
                
                handler = self.handlers.pop(handler_id)
                
                # Remove from event type mappings
                for event_type in handler.event_types:
                    if event_type in self.event_types_to_handlers:
                        if handler_id in self.event_types_to_handlers[event_type]:
                            self.event_types_to_handlers[event_type].remove(handler_id)
                
                self.logger.info(f"Unregistered handler {handler_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error unregistering handler {handler_id}: {e}")
            return False
    
    def publish_event(self, event: Event) -> bool:
        """Publish an event to the bus"""
        try:
            # Check TTL
            if event.ttl and datetime.now(timezone.utc) > event.ttl:
                self.logger.debug(f"Event {event.event_id} expired, not publishing")
                return False
            
            # Apply global filters
            for filter_func in self.global_filters:
                if not filter_func(event):
                    self.logger.debug(f"Event {event.event_id} filtered out by global filter")
                    return False
            
            # Add to queue with priority
            priority_value = event.priority.value
            self.event_queue.put((priority_value, event.timestamp, event))
            
            # Update metrics
            with self.metrics_lock:
                self.event_metrics['total_events'] += 1
                
                event_type_key = event.event_type.value
                if event_type_key not in self.event_metrics['events_by_type']:
                    self.event_metrics['events_by_type'][event_type_key] = 0
                self.event_metrics['events_by_type'][event_type_key] += 1
                
                if event.source not in self.event_metrics['events_by_source']:
                    self.event_metrics['events_by_source'][event.source] = 0
                self.event_metrics['events_by_source'][event.source] += 1
            
            self.logger.debug(f"Published event {event.event_id} of type {event.event_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing event {event.event_id}: {e}")
            return False
    
    def create_event(self, event_type: EventType, source: str, data: Dict[str, Any], 
                    priority: EventPriority = EventPriority.NORMAL, target: str = None,
                    correlation_id: str = None) -> Event:
        """Create a new event"""
        return Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            source=source,
            timestamp=datetime.now(timezone.utc),
            data=data,
            priority=priority,
            target=target,
            correlation_id=correlation_id
        )
    
    def start_processing(self) -> bool:
        """Start event processing"""
        if self.is_running:
            self.logger.warning("Event bus is already running")
            return False
        
        try:
            self.is_running = True
            self.shutdown_event.clear()
            self.processing_thread = threading.Thread(target=self._process_events, daemon=True)
            self.processing_thread.start()
            
            self.logger.info("Event bus started")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting event bus: {e}")
            self.is_running = False
            return False
    
    def stop_processing(self) -> bool:
        """Stop event processing"""
        if not self.is_running:
            return True
        
        try:
            self.is_running = False
            self.shutdown_event.set()
            
            if self.processing_thread:
                self.processing_thread.join(timeout=5)
            
            self.logger.info("Event bus stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping event bus: {e}")
            return False
    
    def _process_events(self):
        """Main event processing loop"""
        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Get event from queue (with timeout)
                try:
                    priority, timestamp, event = self.event_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Process event
                self._handle_event(event)
                
                # Add to history
                self.event_history.append(event)
                
                # Limit history size
                if len(self.event_history) > 1000:
                    self.event_history = self.event_history[-500:]
                
                self.event_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in event processing loop: {e}")
    
    def _handle_event(self, event: Event):
        """Handle individual event"""
        start_time = datetime.now()
        
        try:
            # Get handlers for this event type
            handler_ids = self.event_types_to_handlers.get(event.event_type, [])
            
            # Filter handlers by target if specified
            if event.target:
                handler_ids = [
                    h_id for h_id in handler_ids 
                    if self.handlers[h_id].component == event.target
                ]
            
            if not handler_ids:
                self.logger.debug(f"No handlers for event {event.event_id} of type {event.event_type.value}")
                return
            
            # Execute handlers
            for handler_id in handler_ids:
                try:
                    handler = self.handlers[handler_id]
                    
                    # Apply handler-specific filter
                    if handler.filter_func and not handler.filter_func(event):
                        continue
                    
                    # Execute handler
                    if handler.async_handler:
                        # Submit to thread pool for async execution
                        self.executor.submit(self._execute_handler, handler, event)
                    else:
                        self._execute_handler(handler, event)
                    
                    # Update metrics
                    with self.metrics_lock:
                        if handler_id not in self.event_metrics['handler_executions']:
                            self.event_metrics['handler_executions'][handler_id] = 0
                        self.event_metrics['handler_executions'][handler_id] += 1
                
                except Exception as e:
                    self.logger.error(f"Error executing handler {handler_id} for event {event.event_id}: {e}")
                    
                    with self.metrics_lock:
                        if handler_id not in self.event_metrics['failed_handlers']:
                            self.event_metrics['failed_handlers'][handler_id] = 0
                        self.event_metrics['failed_handlers'][handler_id] += 1
            
            # Update processing time metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            with self.metrics_lock:
                current_avg = self.event_metrics['average_processing_time']
                total_events = self.event_metrics['total_events']
                self.event_metrics['average_processing_time'] = (
                    (current_avg * (total_events - 1) + processing_time) / total_events
                )
        
        except Exception as e:
            self.logger.error(f"Error handling event {event.event_id}: {e}")
    
    def _execute_handler(self, handler: EventHandler, event: Event):
        """Execute individual handler"""
        try:
            self.logger.debug(f"Executing handler {handler.handler_id} for event {event.event_id}")
            
            # Call handler
            result = handler.callback(event)
            
            # Handle async results if needed
            if asyncio.iscoroutine(result):
                # If we get a coroutine, we need to run it
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(result)
                finally:
                    loop.close()
            
        except Exception as e:
            self.logger.error(f"Error in handler {handler.handler_id}: {e}")
            raise
    
    def add_global_filter(self, filter_func: Callable[[Event], bool]):
        """Add global event filter"""
        self.global_filters.append(filter_func)
    
    def remove_global_filter(self, filter_func: Callable[[Event], bool]):
        """Remove global event filter"""
        if filter_func in self.global_filters:
            self.global_filters.remove(filter_func)
    
    def get_event_metrics(self) -> Dict[str, Any]:
        """Get event processing metrics"""
        with self.metrics_lock:
            return self.event_metrics.copy()
    
    def get_recent_events(self, event_type: EventType = None, count: int = 10) -> List[Event]:
        """Get recent events, optionally filtered by type"""
        if event_type:
            filtered_events = [e for e in self.event_history if e.event_type == event_type]
            return filtered_events[-count:]
        else:
            return self.event_history[-count:]
    
    def get_handler_info(self) -> Dict[str, Any]:
        """Get information about registered handlers"""
        with self.handlers_lock:
            handler_info = {}
            for handler_id, handler in self.handlers.items():
                handler_info[handler_id] = {
                    'component': handler.component,
                    'event_types': [et.value for et in handler.event_types],
                    'async_handler': handler.async_handler,
                    'priority': handler.priority
                }
            return handler_info
    
    def cleanup(self):
        """Cleanup event bus resources"""
        self.stop_processing()
        self.executor.shutdown(wait=True)
        self.logger.info("Event bus cleaned up")

class EventDispatcher:
    """
    High-level event dispatcher that manages the event bus
    """
    
    def __init__(self, max_workers: int = 4):
        self.logger = logging.getLogger(__name__)
        self.event_bus = EventBus(max_workers=max_workers)
        
        # Start processing
        self.event_bus.start_processing()
    
    def register_component_handlers(self, component_name: str, handlers: List[Dict[str, Any]]) -> bool:
        """Register multiple handlers for a component"""
        try:
            for handler_config in handlers:
                handler = EventHandler(
                    handler_id=f"{component_name}_{handler_config['name']}",
                    event_types=set(EventType(et) for et in handler_config['event_types']),
                    callback=handler_config['callback'],
                    component=component_name,
                    async_handler=handler_config.get('async_handler', False),
                    filter_func=handler_config.get('filter_func'),
                    priority=handler_config.get('priority', 5)
                )
                
                if not self.event_bus.register_handler(handler):
                    return False
            
            self.logger.info(f"Registered {len(handlers)} handlers for component {component_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering handlers for component {component_name}: {e}")
            return False
    
    def publish(self, event_type: EventType, source: str, data: Dict[str, Any], 
               priority: EventPriority = EventPriority.NORMAL, target: str = None) -> bool:
        """Publish an event"""
        event = self.event_bus.create_event(event_type, source, data, priority, target)
        return self.event_bus.publish_event(event)
    
    def get_status(self) -> Dict[str, Any]:
        """Get dispatcher status"""
        return {
            'is_running': self.event_bus.is_running,
            'queue_size': self.event_bus.event_queue.qsize(),
            'handler_count': len(self.event_bus.handlers),
            'metrics': self.event_bus.get_event_metrics(),
            'handlers': self.event_bus.get_handler_info()
        }
    
    def cleanup(self):
        """Cleanup dispatcher"""
        self.event_bus.cleanup()
        self.logger.info("Event dispatcher cleaned up")