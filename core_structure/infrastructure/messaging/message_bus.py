"""
Message bus system for event-driven communication between components
"""
from typing import Dict, List, Any, Callable, Optional
import logging
import json
import threading
from queue import Queue
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid

from ..monitoring import MetricsCollector
from ..config import UnifiedConfigManager as ConfigManager

logger = logging.getLogger(__name__)

@dataclass
class Message:
    """Base message class for all events"""
    id: str
    type: str
    payload: Dict[str, Any]
    timestamp: datetime
    source: str
    metadata: Dict[str, Any]

class MessageBus:
    """
    Event-driven message bus for component communication
    Supports:
    - Pub/sub messaging
    - Message persistence
    - Message routing
    - AI agent communication
    """
    
    def __init__(self):
        self.config = ConfigManager().get_messaging_config()
        self.metrics = MetricsCollector()
        
        # Subscribers for different message types
        self._subscribers: Dict[str, List[Callable]] = {}
        
        # Message queues for async processing
        self._queues: Dict[str, Queue] = {}
        
        # Message persistence (if enabled)
        self._message_history: List[Message] = []
        self._max_history = self.config.get('max_history_size', 1000)
        
        # Background processing
        self._processing_threads: Dict[str, threading.Thread] = {}
        self._should_stop = threading.Event()
        
        # AI agent communication channel
        self._ai_channel = self.config.get('ai_channel', 'ai_messages')
        self._setup_ai_channel()
    
    def _setup_ai_channel(self):
        """Setup dedicated channel for AI agent communication"""
        self._subscribers[self._ai_channel] = []
        self._queues[self._ai_channel] = Queue()
        
        # Start AI message processor
        self._processing_threads[self._ai_channel] = threading.Thread(
            target=self._process_messages,
            args=(self._ai_channel,),
            daemon=True
        )
        self._processing_threads[self._ai_channel].start()
    
    def subscribe(
        self,
        message_type: str,
        callback: Callable[[Message], None],
        queue_size: Optional[int] = None
    ) -> None:
        """
        Subscribe to messages of a specific type
        
        Args:
            message_type: Type of messages to subscribe to
            callback: Callback function to handle messages
            queue_size: Optional queue size for async processing
        """
        if message_type not in self._subscribers:
            self._subscribers[message_type] = []
            
            # Create message queue if async processing requested
            if queue_size is not None:
                self._queues[message_type] = Queue(maxsize=queue_size)
                
                # Start message processor thread
                self._processing_threads[message_type] = threading.Thread(
                    target=self._process_messages,
                    args=(message_type,),
                    daemon=True
                )
                self._processing_threads[message_type].start()
        
        self._subscribers[message_type].append(callback)
    
    def publish(
        self,
        message_type: str,
        payload: Dict[str, Any],
        source: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Publish a message
        
        Args:
            message_type: Type of message
            payload: Message payload
            source: Source of the message
            metadata: Optional message metadata
            
        Returns:
            Message ID
        """
        message = Message(
            id=str(uuid.uuid4()),
            type=message_type,
            payload=payload,
            timestamp=datetime.now(),
            source=source,
            metadata=metadata or {}
        )
        
        # Add to history if enabled
        if self.config.get('enable_history', False):
            self._add_to_history(message)
        
        # Metrics
        self.metrics.increment_counter(
            f"messages_published_{message_type}",
            tags={'source': source}
        )
        
        # Queue message if async processing enabled
        if message_type in self._queues:
            self._queues[message_type].put(message)
        else:
            # Synchronous delivery
            self._deliver_message(message)
        
        return message.id
    
    def publish_ai_message(
        self,
        payload: Dict[str, Any],
        source: str = "ai_agent",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Publish message to AI channel
        
        Args:
            payload: Message payload
            source: Source AI agent
            metadata: Optional message metadata
            
        Returns:
            Message ID
        """
        return self.publish(
            message_type=self._ai_channel,
            payload=payload,
            source=source,
            metadata=metadata
        )
    
    def _process_messages(self, message_type: str) -> None:
        """Background thread for processing messages"""
        queue = self._queues[message_type]
        
        while not self._should_stop.is_set():
            try:
                message = queue.get(timeout=1)
                self._deliver_message(message)
                queue.task_done()
            except:
                continue
    
    def _deliver_message(self, message: Message) -> None:
        """Deliver message to all subscribers"""
        if message.type not in self._subscribers:
            return
        
        start_time = datetime.now()
        
        for callback in self._subscribers[message.type]:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error in message callback: {str(e)}")
                self.metrics.increment_counter(
                    "message_delivery_errors",
                    tags={'type': message.type}
                )
        
        # Record delivery latency
        latency = (datetime.now() - start_time).total_seconds() * 1000
        self.metrics.record_latency(
            "message_delivery",
            latency,
            tags={'type': message.type}
        )
    
    def _add_to_history(self, message: Message) -> None:
        """Add message to history"""
        self._message_history.append(message)
        
        # Maintain history size
        while len(self._message_history) > self._max_history:
            self._message_history.pop(0)
    
    def get_message_history(
        self,
        message_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get message history with optional filtering
        
        Args:
            message_type: Optional message type filter
            source: Optional source filter
            limit: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        messages = self._message_history
        
        if message_type:
            messages = [m for m in messages if m.type == message_type]
        if source:
            messages = [m for m in messages if m.source == source]
        
        return [asdict(m) for m in messages[-limit:]]
    
    def shutdown(self) -> None:
        """Shutdown message bus"""
        self._should_stop.set()
        
        # Wait for processing threads to finish
        for thread in self._processing_threads.values():
            thread.join(timeout=1)
        
        # Clear queues
        for queue in self._queues.values():
            while not queue.empty():
                queue.get_nowait()
                queue.task_done() 