"""
Broker Engine - Message Processor
Advanced message processing, routing, and transformation for broker communications
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
import time
from collections import defaultdict, deque
import uuid
import warnings
import json
import zlib

from .protocol_handler import (
    ProtocolMessage, MessageType, MessageDirection, ProtocolType,
    ProtocolHandler, ProtocolConfig
)

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ProcessingPriority(Enum):
    """Message processing priority"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class MessageStatus(Enum):
    """Message processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    REJECTED = "rejected"
    RETRY = "retry"
    ARCHIVED = "archived"


class TransformationType(Enum):
    """Message transformation types"""
    NONE = "none"
    FORMAT_CONVERSION = "format_conversion"
    FIELD_MAPPING = "field_mapping"
    ENRICHMENT = "enrichment"
    VALIDATION = "validation"
    ENCRYPTION = "encryption"
    COMPRESSION = "compression"
    AGGREGATION = "aggregation"
    FILTERING = "filtering"


@dataclass
class ProcessingConfig:
    """Message processing configuration"""
    # Queue settings
    max_queue_size: int = 10000
    batch_size: int = 100
    batch_timeout: float = 1.0
    
    # Worker settings
    worker_count: int = 4
    max_concurrent_messages: int = 1000
    
    # Retry settings
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    
    # Performance settings
    enable_metrics: bool = True
    metrics_window: int = 1000
    enable_compression: bool = False
    compression_threshold: int = 1024
    
    # Storage settings
    persist_messages: bool = False
    archive_processed: bool = False
    archive_retention_days: int = 30
    
    # Dead letter queue
    enable_dlq: bool = True
    dlq_max_size: int = 1000
    
    # Rate limiting
    enable_rate_limiting: bool = False
    messages_per_second: int = 1000
    burst_capacity: int = 5000


@dataclass
class MessageEnvelope:
    """Message envelope for processing"""
    envelope_id: str
    message: ProtocolMessage
    priority: ProcessingPriority
    
    # Processing metadata
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    # Routing information
    source: Optional[str] = None
    destination: Optional[str] = None
    route: List[str] = field(default_factory=list)
    
    # Processing context
    context: Dict[str, Any] = field(default_factory=dict)
    transformations: List[TransformationType] = field(default_factory=list)
    
    # Timing
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    
    # Error handling
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ProcessingRule:
    """Message processing rule"""
    rule_id: str
    name: str
    condition: Callable[[ProtocolMessage], bool]
    action: Callable[[MessageEnvelope], MessageEnvelope]
    
    # Rule metadata
    priority: int = 0
    enabled: bool = True
    description: Optional[str] = None
    
    # Statistics
    matches: int = 0
    executions: int = 0
    errors: int = 0
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    last_executed: Optional[datetime] = None


@dataclass
class MessageRoute:
    """Message routing configuration"""
    route_id: str
    name: str
    
    # Routing criteria
    source_filter: Optional[Callable[[ProtocolMessage], bool]] = None
    message_type_filter: Optional[List[MessageType]] = None
    protocol_filter: Optional[List[ProtocolType]] = None
    
    # Route destinations
    destinations: List[str] = field(default_factory=list)
    
    # Route behavior
    broadcast: bool = False  # Send to all destinations vs first available
    failover: bool = True    # Try next destination on failure
    
    # Route statistics
    messages_routed: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0


class MessageTransformer:
    """Message transformation engine"""
    
    def __init__(self):
        self._transformers: Dict[TransformationType, Callable] = {}
        self._field_mappings: Dict[str, Dict[str, str]] = {}
        
        # Register default transformers
        self._register_default_transformers()
        
        logger.info("Message transformer initialized")
    
    def _register_default_transformers(self) -> None:
        """Register default transformation functions"""
        
        self._transformers[TransformationType.FORMAT_CONVERSION] = self._format_conversion
        self._transformers[TransformationType.FIELD_MAPPING] = self._field_mapping
        self._transformers[TransformationType.ENRICHMENT] = self._enrichment
        self._transformers[TransformationType.VALIDATION] = self._validation
        self._transformers[TransformationType.ENCRYPTION] = self._encryption
        self._transformers[TransformationType.COMPRESSION] = self._compression
        self._transformers[TransformationType.AGGREGATION] = self._aggregation
        self._transformers[TransformationType.FILTERING] = self._filtering
    
    def transform(self, envelope: MessageEnvelope, 
                 transformation: TransformationType) -> MessageEnvelope:
        """Apply transformation to message envelope"""
        
        try:
            transformer = self._transformers.get(transformation)
            
            if not transformer:
                envelope.warnings.append(f"Unknown transformation: {transformation.value}")
                return envelope
            
            # Apply transformation
            transformed_envelope = transformer(envelope)
            
            # Record transformation
            if transformation not in transformed_envelope.transformations:
                transformed_envelope.transformations.append(transformation)
            
            logger.debug(f"Applied transformation {transformation.value} to message {envelope.envelope_id}")
            
            return transformed_envelope
            
        except Exception as e:
            error_msg = f"Transformation {transformation.value} failed: {e}"
            envelope.errors.append(error_msg)
            logger.error(error_msg)
            return envelope
    
    def _format_conversion(self, envelope: MessageEnvelope) -> MessageEnvelope:
        """Convert message format"""
        
        message = envelope.message
        
        # Example: Convert between JSON and XML
        if message.protocol_type == ProtocolType.REST:
            # Already in JSON format
            pass
        elif message.protocol_type == ProtocolType.FIX:
            # Convert FIX to structured format
            structured_data = {}
            for key, value in message.parsed_data.items():
                if key.isdigit():
                    field_name = self._get_fix_field_name(key)
                    structured_data[field_name] = value
                else:
                    structured_data[key] = value
            
            message.parsed_data = structured_data
        
        return envelope
    
    def _field_mapping(self, envelope: MessageEnvelope) -> MessageEnvelope:
        """Map fields between different formats"""
        
        message = envelope.message
        protocol_key = f"{message.protocol_type.value}_{message.message_type.value}"
        
        if protocol_key in self._field_mappings:
            mapping = self._field_mappings[protocol_key]
            
            mapped_data = {}
            for source_field, target_field in mapping.items():
                if source_field in message.parsed_data:
                    mapped_data[target_field] = message.parsed_data[source_field]
            
            # Merge with existing data
            message.parsed_data.update(mapped_data)
        
        return envelope
    
    def _enrichment(self, envelope: MessageEnvelope) -> MessageEnvelope:
        """Enrich message with additional data"""
        
        message = envelope.message
        
        # Add timestamps
        if 'processing_timestamp' not in message.parsed_data:
            message.parsed_data['processing_timestamp'] = datetime.now().isoformat()
        
        # Add message metadata
        message.parsed_data['_envelope_id'] = envelope.envelope_id
        message.parsed_data['_priority'] = envelope.priority.value
        
        # Add context data
        if envelope.context:
            message.parsed_data['_context'] = envelope.context
        
        return envelope
    
    def _validation(self, envelope: MessageEnvelope) -> MessageEnvelope:
        """Validate message content"""
        
        message = envelope.message
        errors = []
        
        # Basic validation
        if not message.parsed_data:
            errors.append("Message has no data")
        
        # Message type specific validation
        if message.message_type == MessageType.NEW_ORDER:
            required_fields = ['symbol', 'quantity', 'side', 'order_type']
            for field in required_fields:
                if field not in message.parsed_data:
                    errors.append(f"Missing required field: {field}")
        
        elif message.message_type == MessageType.EXECUTION_REPORT:
            required_fields = ['order_id', 'symbol', 'quantity', 'price']
            for field in required_fields:
                if field not in message.parsed_data:
                    errors.append(f"Missing required field: {field}")
        
        # Update message validation status
        if errors:
            message.is_valid = False
            message.validation_errors.extend(errors)
            envelope.errors.extend(errors)
        
        return envelope
    
    def _encryption(self, envelope: MessageEnvelope) -> MessageEnvelope:
        """Encrypt sensitive message data"""
        
        message = envelope.message
        
        # Identify sensitive fields
        sensitive_fields = ['password', 'api_key', 'secret', 'token']
        
        for field in sensitive_fields:
            if field in message.parsed_data:
                # Simple encryption (in practice, use proper encryption)
                value = str(message.parsed_data[field])
                encrypted_value = f"***{len(value)}***"
                message.parsed_data[field] = encrypted_value
        
        return envelope
    
    def _compression(self, envelope: MessageEnvelope) -> MessageEnvelope:
        """Compress message data if beneficial"""
        
        message = envelope.message
        
        # Compress if message is large
        data_size = len(str(message.parsed_data))
        
        if data_size > 1024:  # Compress if > 1KB
            try:
                compressed_data = zlib.compress(
                    json.dumps(message.parsed_data).encode('utf-8')
                )
                
                if len(compressed_data) < data_size * 0.8:  # Only if 20% compression
                    message.parsed_data = {
                        '_compressed': True,
                        '_original_size': data_size,
                        '_compressed_data': compressed_data.hex()
                    }
                    
                    logger.debug(f"Compressed message {envelope.envelope_id}: {data_size} -> {len(compressed_data)}")
                
            except Exception as e:
                envelope.warnings.append(f"Compression failed: {e}")
        
        return envelope
    
    def _aggregation(self, envelope: MessageEnvelope) -> MessageEnvelope:
        """Aggregate related messages"""
        
        # This would typically accumulate messages and create aggregated views
        # For now, just add aggregation metadata
        
        message = envelope.message
        message.parsed_data['_aggregated'] = False
        message.parsed_data['_aggregation_candidate'] = True
        
        return envelope
    
    def _filtering(self, envelope: MessageEnvelope) -> MessageEnvelope:
        """Filter message content"""
        
        message = envelope.message
        
        # Remove internal fields from outbound messages
        if message.direction == MessageDirection.OUTBOUND:
            filtered_data = {}
            for key, value in message.parsed_data.items():
                if not key.startswith('_internal_'):
                    filtered_data[key] = value
            
            message.parsed_data = filtered_data
        
        return envelope
    
    def _get_fix_field_name(self, tag: str) -> str:
        """Get FIX field name from tag"""
        
        fix_tags = {
            '1': 'Account',
            '6': 'AvgPx',
            '8': 'BeginString',
            '9': 'BodyLength',
            '10': 'CheckSum',
            '11': 'ClOrdID',
            '14': 'CumQty',
            '17': 'ExecID',
            '20': 'ExecTransType',
            '31': 'LastPx',
            '32': 'LastQty',
            '34': 'MsgSeqNum',
            '35': 'MsgType',
            '37': 'OrderID',
            '38': 'OrderQty',
            '39': 'OrdStatus',
            '40': 'OrdType',
            '44': 'Price',
            '49': 'SenderCompID',
            '52': 'SendingTime',
            '54': 'Side',
            '55': 'Symbol',
            '56': 'TargetCompID',
            '59': 'TimeInForce',
            '60': 'TransactTime',
            '150': 'ExecType',
            '151': 'LeavesQty'
        }
        
        return fix_tags.get(tag, f'Field_{tag}')
    
    def register_transformer(self, transformation: TransformationType,
                            transformer: Callable[[MessageEnvelope], MessageEnvelope]) -> None:
        """Register custom transformer"""
        self._transformers[transformation] = transformer
        logger.info(f"Registered custom transformer: {transformation.value}")
    
    def add_field_mapping(self, protocol_type: ProtocolType, 
                         message_type: MessageType,
                         mapping: Dict[str, str]) -> None:
        """Add field mapping for protocol/message type"""
        key = f"{protocol_type.value}_{message_type.value}"
        self._field_mappings[key] = mapping
        logger.info(f"Added field mapping for {key}")


class MessageRouter:
    """Message routing engine"""
    
    def __init__(self):
        self._routes: Dict[str, MessageRoute] = {}
        self._default_route: Optional[str] = None
        
        logger.info("Message router initialized")
    
    def add_route(self, route: MessageRoute) -> None:
        """Add message route"""
        self._routes[route.route_id] = route
        logger.info(f"Added message route: {route.name}")
    
    def remove_route(self, route_id: str) -> bool:
        """Remove message route"""
        if route_id in self._routes:
            del self._routes[route_id]
            logger.info(f"Removed message route: {route_id}")
            return True
        return False
    
    def set_default_route(self, route_id: str) -> None:
        """Set default route"""
        if route_id in self._routes:
            self._default_route = route_id
            logger.info(f"Set default route: {route_id}")
    
    def route_message(self, envelope: MessageEnvelope) -> List[str]:
        """Route message to destinations"""
        
        message = envelope.message
        destinations = []
        
        try:
            # Find matching routes
            matching_routes = []
            
            for route in self._routes.values():
                if self._matches_route(message, route):
                    matching_routes.append(route)
            
            # If no matching routes, use default
            if not matching_routes and self._default_route:
                default_route = self._routes.get(self._default_route)
                if default_route:
                    matching_routes.append(default_route)
            
            # Collect destinations from matching routes
            for route in matching_routes:
                route.messages_routed += 1
                
                if route.broadcast:
                    destinations.extend(route.destinations)
                else:
                    # Take first available destination
                    if route.destinations:
                        destinations.append(route.destinations[0])
            
            # Remove duplicates while preserving order
            unique_destinations = []
            for dest in destinations:
                if dest not in unique_destinations:
                    unique_destinations.append(dest)
            
            # Update envelope routing info
            envelope.route = unique_destinations
            
            logger.debug(f"Routed message {envelope.envelope_id} to {len(unique_destinations)} destinations")
            
            return unique_destinations
            
        except Exception as e:
            error_msg = f"Message routing failed: {e}"
            envelope.errors.append(error_msg)
            logger.error(error_msg)
            return []
    
    def _matches_route(self, message: ProtocolMessage, route: MessageRoute) -> bool:
        """Check if message matches route criteria"""
        
        try:
            # Check source filter
            if route.source_filter and not route.source_filter(message):
                return False
            
            # Check message type filter
            if route.message_type_filter and message.message_type not in route.message_type_filter:
                return False
            
            # Check protocol filter
            if route.protocol_filter and message.protocol_type not in route.protocol_filter:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking route match: {e}")
            return False
    
    def get_route_statistics(self) -> Dict[str, Any]:
        """Get routing statistics"""
        
        stats = {}
        
        for route_id, route in self._routes.items():
            stats[route_id] = {
                'name': route.name,
                'messages_routed': route.messages_routed,
                'successful_deliveries': route.successful_deliveries,
                'failed_deliveries': route.failed_deliveries,
                'success_rate': (route.successful_deliveries / max(route.messages_routed, 1)) * 100,
                'destinations': len(route.destinations),
                'broadcast': route.broadcast,
                'failover': route.failover
            }
        
        return stats


class MessageProcessor:
    """
    Advanced Message Processor
    
    Processes broker messages with transformation, routing,
    validation, and advanced processing capabilities.
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """Initialize message processor"""
        
        self.config = config or ProcessingConfig()
        
        # Processing queues
        self._inbound_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.max_queue_size)
        self._outbound_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.max_queue_size)
        self._priority_queues: Dict[ProcessingPriority, asyncio.Queue] = {
            priority: asyncio.Queue(maxsize=self.config.max_queue_size // 5)
            for priority in ProcessingPriority
        }
        
        # Dead letter queue
        self._dlq: deque = deque(maxlen=self.config.dlq_max_size)
        
        # Processing components
        self._transformer = MessageTransformer()
        self._router = MessageRouter()
        
        # Processing rules
        self._rules: Dict[str, ProcessingRule] = {}
        
        # Worker management
        self._workers: List[asyncio.Task] = []
        self._worker_semaphore = asyncio.Semaphore(self.config.max_concurrent_messages)
        self._stop_workers = False
        
        # Message tracking
        self._pending_messages: Dict[str, MessageEnvelope] = {}
        self._processed_messages: Dict[str, MessageEnvelope] = {}
        
        # Metrics
        self._metrics = {
            'messages_received': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'messages_rejected': 0,
            'processing_times': deque(maxlen=self.config.metrics_window),
            'transformation_times': deque(maxlen=self.config.metrics_window),
            'routing_times': deque(maxlen=self.config.metrics_window)
        }
        
        # Event handlers
        self._event_handlers = defaultdict(list)
        
        # Rate limiting
        self._rate_limiter = None
        if self.config.enable_rate_limiting:
            self._rate_limiter = asyncio.Semaphore(self.config.messages_per_second)
        
        logger.info("Message processor initialized")
    
    async def start(self) -> None:
        """Start message processor"""
        
        try:
            # Start worker tasks
            for i in range(self.config.worker_count):
                worker = asyncio.create_task(self._worker_loop(f"worker_{i}"))
                self._workers.append(worker)
            
            # Start batch processor
            batch_processor = asyncio.create_task(self._batch_processor())
            self._workers.append(batch_processor)
            
            # Start metrics collector
            if self.config.enable_metrics:
                metrics_collector = asyncio.create_task(self._metrics_collector())
                self._workers.append(metrics_collector)
            
            logger.info(f"Message processor started with {self.config.worker_count} workers")
            
        except Exception as e:
            logger.error(f"Failed to start message processor: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop message processor"""
        
        try:
            # Signal workers to stop
            self._stop_workers = True
            
            # Cancel worker tasks
            for worker in self._workers:
                worker.cancel()
            
            # Wait for workers to complete
            if self._workers:
                await asyncio.gather(*self._workers, return_exceptions=True)
            
            self._workers.clear()
            
            logger.info("Message processor stopped")
            
        except Exception as e:
            logger.error(f"Error stopping message processor: {e}")
    
    async def process_message(self, message: ProtocolMessage,
                             priority: ProcessingPriority = ProcessingPriority.NORMAL,
                             context: Optional[Dict[str, Any]] = None) -> str:
        """Submit message for processing"""
        
        try:
            # Rate limiting
            if self._rate_limiter:
                await self._rate_limiter.acquire()
            
            # Create message envelope
            envelope = MessageEnvelope(
                envelope_id=str(uuid.uuid4()),
                message=message,
                priority=priority,
                context=context or {}
            )
            
            # Add to appropriate queue
            if priority == ProcessingPriority.CRITICAL:
                await self._priority_queues[priority].put(envelope)
            else:
                await self._inbound_queue.put(envelope)
            
            # Track message
            self._pending_messages[envelope.envelope_id] = envelope
            self._metrics['messages_received'] += 1
            
            logger.debug(f"Queued message {envelope.envelope_id} for processing")
            
            self._trigger_event('message_queued', {
                'envelope_id': envelope.envelope_id,
                'message_type': message.message_type.value,
                'priority': priority.value
            })
            
            return envelope.envelope_id
            
        except Exception as e:
            logger.error(f"Failed to queue message for processing: {e}")
            raise
    
    async def get_message_status(self, envelope_id: str) -> Optional[MessageStatus]:
        """Get message processing status"""
        
        # Check pending messages
        if envelope_id in self._pending_messages:
            return self._pending_messages[envelope_id].status
        
        # Check processed messages
        if envelope_id in self._processed_messages:
            return self._processed_messages[envelope_id].status
        
        return None
    
    async def get_message_result(self, envelope_id: str) -> Optional[MessageEnvelope]:
        """Get message processing result"""
        
        if envelope_id in self._processed_messages:
            return self._processed_messages[envelope_id]
        
        return None
    
    def add_processing_rule(self, rule: ProcessingRule) -> None:
        """Add message processing rule"""
        self._rules[rule.rule_id] = rule
        logger.info(f"Added processing rule: {rule.name}")
    
    def remove_processing_rule(self, rule_id: str) -> bool:
        """Remove processing rule"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f"Removed processing rule: {rule_id}")
            return True
        return False
    
    def add_route(self, route: MessageRoute) -> None:
        """Add message route"""
        self._router.add_route(route)
    
    def add_transformer(self, transformation: TransformationType,
                       transformer: Callable[[MessageEnvelope], MessageEnvelope]) -> None:
        """Add custom transformer"""
        self._transformer.register_transformer(transformation, transformer)
    
    async def _worker_loop(self, worker_id: str) -> None:
        """Worker loop for processing messages"""
        
        logger.info(f"Worker {worker_id} started")
        
        while not self._stop_workers:
            try:
                # Get message from queue (priority first)
                envelope = await self._get_next_message()
                
                if envelope:
                    async with self._worker_semaphore:
                        await self._process_envelope(envelope)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker {worker_id}: {e}")
                await asyncio.sleep(1)  # Brief pause on error
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _get_next_message(self) -> Optional[MessageEnvelope]:
        """Get next message to process (priority-based)"""
        
        # Check critical priority first
        try:
            return await asyncio.wait_for(
                self._priority_queues[ProcessingPriority.CRITICAL].get(),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            pass
        
        # Check high priority
        try:
            return await asyncio.wait_for(
                self._priority_queues[ProcessingPriority.HIGH].get(),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            pass
        
        # Check normal queue
        try:
            return await asyncio.wait_for(
                self._inbound_queue.get(),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            pass
        
        # Check lower priorities
        for priority in [ProcessingPriority.NORMAL, ProcessingPriority.LOW, ProcessingPriority.BACKGROUND]:
            try:
                return await asyncio.wait_for(
                    self._priority_queues[priority].get(),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                continue
        
        return None
    
    async def _process_envelope(self, envelope: MessageEnvelope) -> None:
        """Process message envelope"""
        
        start_time = time.time()
        
        try:
            envelope.status = MessageStatus.PROCESSING
            envelope.processing_started_at = datetime.now()
            envelope.updated_at = datetime.now()
            
            # Apply processing rules
            await self._apply_rules(envelope)
            
            # Transform message
            await self._transform_message(envelope)
            
            # Route message
            await self._route_message(envelope)
            
            # Mark as processed
            envelope.status = MessageStatus.PROCESSED
            envelope.processing_completed_at = datetime.now()
            
            # Move to processed messages
            self._move_to_processed(envelope)
            
            # Update metrics
            processing_time = time.time() - start_time
            self._metrics['messages_processed'] += 1
            self._metrics['processing_times'].append(processing_time)
            
            logger.debug(f"Processed message {envelope.envelope_id} in {processing_time:.3f}s")
            
            self._trigger_event('message_processed', {
                'envelope_id': envelope.envelope_id,
                'processing_time': processing_time,
                'transformations': [t.value for t in envelope.transformations],
                'destinations': envelope.route
            })
            
        except Exception as e:
            await self._handle_processing_error(envelope, e, start_time)
    
    async def _apply_rules(self, envelope: MessageEnvelope) -> None:
        """Apply processing rules to message"""
        
        message = envelope.message
        
        # Sort rules by priority
        sorted_rules = sorted(
            [rule for rule in self._rules.values() if rule.enabled],
            key=lambda r: r.priority,
            reverse=True
        )
        
        for rule in sorted_rules:
            try:
                # Check if rule condition matches
                if rule.condition(message):
                    rule.matches += 1
                    
                    # Apply rule action
                    envelope = rule.action(envelope)
                    rule.executions += 1
                    rule.last_executed = datetime.now()
                    
                    logger.debug(f"Applied rule {rule.name} to message {envelope.envelope_id}")
                
            except Exception as e:
                rule.errors += 1
                error_msg = f"Rule {rule.name} failed: {e}"
                envelope.errors.append(error_msg)
                logger.error(error_msg)
    
    async def _transform_message(self, envelope: MessageEnvelope) -> None:
        """Transform message based on configuration"""
        
        start_time = time.time()
        
        try:
            # Apply default transformations
            default_transformations = [
                TransformationType.VALIDATION,
                TransformationType.ENRICHMENT,
                TransformationType.FORMAT_CONVERSION
            ]
            
            for transformation in default_transformations:
                envelope = self._transformer.transform(envelope, transformation)
            
            # Apply custom transformations from context
            custom_transformations = envelope.context.get('transformations', [])
            for transformation_name in custom_transformations:
                try:
                    transformation = TransformationType(transformation_name)
                    envelope = self._transformer.transform(envelope, transformation)
                except ValueError:
                    envelope.warnings.append(f"Unknown transformation: {transformation_name}")
            
            # Update metrics
            transformation_time = time.time() - start_time
            self._metrics['transformation_times'].append(transformation_time)
            
        except Exception as e:
            error_msg = f"Message transformation failed: {e}"
            envelope.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _route_message(self, envelope: MessageEnvelope) -> None:
        """Route message to destinations"""
        
        start_time = time.time()
        
        try:
            destinations = self._router.route_message(envelope)
            
            if not destinations:
                envelope.warnings.append("No routing destinations found")
            
            # Update metrics
            routing_time = time.time() - start_time
            self._metrics['routing_times'].append(routing_time)
            
        except Exception as e:
            error_msg = f"Message routing failed: {e}"
            envelope.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _handle_processing_error(self, envelope: MessageEnvelope, 
                                     error: Exception, start_time: float) -> None:
        """Handle processing error"""
        
        error_msg = f"Processing failed: {error}"
        envelope.errors.append(error_msg)
        
        # Check if retry is possible
        if envelope.retry_count < self.config.max_retry_attempts:
            envelope.retry_count += 1
            envelope.status = MessageStatus.RETRY
            
            # Calculate retry delay
            delay = self.config.retry_delay * (self.config.retry_backoff ** (envelope.retry_count - 1))
            
            logger.warning(f"Retrying message {envelope.envelope_id} in {delay}s (attempt {envelope.retry_count})")
            
            # Re-queue after delay
            asyncio.create_task(self._retry_message(envelope, delay))
            
        else:
            # Max retries exceeded
            envelope.status = MessageStatus.FAILED
            
            # Move to dead letter queue
            if self.config.enable_dlq:
                self._dlq.append(envelope)
            
            # Move to processed (failed) messages
            self._move_to_processed(envelope)
            
            self._metrics['messages_failed'] += 1
            
            logger.error(f"Message {envelope.envelope_id} failed after {envelope.retry_count} retries")
            
            self._trigger_event('message_failed', {
                'envelope_id': envelope.envelope_id,
                'error': error_msg,
                'retry_count': envelope.retry_count
            })
        
        # Update processing time
        processing_time = time.time() - start_time
        self._metrics['processing_times'].append(processing_time)
    
    async def _retry_message(self, envelope: MessageEnvelope, delay: float) -> None:
        """Retry message after delay"""
        
        await asyncio.sleep(delay)
        
        # Reset processing state
        envelope.status = MessageStatus.PENDING
        envelope.processing_started_at = None
        envelope.processing_completed_at = None
        
        # Re-queue message
        await self._inbound_queue.put(envelope)
    
    def _move_to_processed(self, envelope: MessageEnvelope) -> None:
        """Move envelope from pending to processed"""
        
        if envelope.envelope_id in self._pending_messages:
            del self._pending_messages[envelope.envelope_id]
        
        self._processed_messages[envelope.envelope_id] = envelope
        
        # Cleanup old processed messages
        if len(self._processed_messages) > self.config.max_queue_size:
            # Remove oldest 10%
            oldest_keys = list(self._processed_messages.keys())[:len(self._processed_messages) // 10]
            for key in oldest_keys:
                del self._processed_messages[key]
    
    async def _batch_processor(self) -> None:
        """Batch processor for aggregating related messages"""
        
        batch: List[MessageEnvelope] = []
        last_batch_time = time.time()
        
        while not self._stop_workers:
            try:
                # Check if batch should be processed
                current_time = time.time()
                should_process_batch = (
                    len(batch) >= self.config.batch_size or
                    (batch and current_time - last_batch_time > self.config.batch_timeout)
                )
                
                if should_process_batch:
                    await self._process_batch(batch)
                    batch.clear()
                    last_batch_time = current_time
                
                await asyncio.sleep(0.1)  # Small delay
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
    
    async def _process_batch(self, batch: List[MessageEnvelope]) -> None:
        """Process batch of messages"""
        
        if not batch:
            return
        
        logger.debug(f"Processing batch of {len(batch)} messages")
        
        # Example: Aggregate market data updates
        market_data_messages = [
            env for env in batch 
            if env.message.message_type == MessageType.MARKET_DATA_INCREMENTAL
        ]
        
        if len(market_data_messages) > 1:
            # Aggregate market data
            await self._aggregate_market_data(market_data_messages)
    
    async def _aggregate_market_data(self, messages: List[MessageEnvelope]) -> None:
        """Aggregate market data messages"""
        
        # Group by symbol
        symbol_groups = defaultdict(list)
        for envelope in messages:
            symbol = envelope.message.parsed_data.get('symbol')
            if symbol:
                symbol_groups[symbol].append(envelope)
        
        # Create aggregated messages
        for symbol, envelopes in symbol_groups.items():
            if len(envelopes) > 1:
                # Create aggregated message
                latest_envelope = max(envelopes, key=lambda e: e.message.created_at)
                
                aggregated_data = {
                    'symbol': symbol,
                    'aggregated': True,
                    'message_count': len(envelopes),
                    'latest_data': latest_envelope.message.parsed_data
                }
                
                # Mark as aggregated
                latest_envelope.message.parsed_data = aggregated_data
                latest_envelope.transformations.append(TransformationType.AGGREGATION)
                
                logger.debug(f"Aggregated {len(envelopes)} messages for {symbol}")
    
    async def _metrics_collector(self) -> None:
        """Collect and report metrics"""
        
        while not self._stop_workers:
            try:
                await asyncio.sleep(60)  # Collect metrics every minute
                
                # Calculate metrics
                metrics = self.get_metrics()
                
                self._trigger_event('metrics_collected', metrics)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collector: {e}")
    
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
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics"""
        
        # Calculate averages
        avg_processing_time = (
            sum(self._metrics['processing_times']) / len(self._metrics['processing_times'])
            if self._metrics['processing_times'] else 0
        )
        
        avg_transformation_time = (
            sum(self._metrics['transformation_times']) / len(self._metrics['transformation_times'])
            if self._metrics['transformation_times'] else 0
        )
        
        avg_routing_time = (
            sum(self._metrics['routing_times']) / len(self._metrics['routing_times'])
            if self._metrics['routing_times'] else 0
        )
        
        # Queue sizes
        queue_sizes = {
            'inbound': self._inbound_queue.qsize(),
            'outbound': self._outbound_queue.qsize(),
            'dlq': len(self._dlq)
        }
        
        for priority in ProcessingPriority:
            queue_sizes[f'priority_{priority.value}'] = self._priority_queues[priority].qsize()
        
        return {
            'messages_received': self._metrics['messages_received'],
            'messages_processed': self._metrics['messages_processed'],
            'messages_failed': self._metrics['messages_failed'],
            'messages_rejected': self._metrics['messages_rejected'],
            'pending_messages': len(self._pending_messages),
            'processed_messages': len(self._processed_messages),
            'queue_sizes': queue_sizes,
            'avg_processing_time': avg_processing_time,
            'avg_transformation_time': avg_transformation_time,
            'avg_routing_time': avg_routing_time,
            'worker_count': len(self._workers),
            'rules_count': len(self._rules),
            'routes_count': len(self._router._routes),
            'success_rate': (
                self._metrics['messages_processed'] / 
                max(self._metrics['messages_received'], 1) * 100
            )
        }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status information"""
        
        return {
            'inbound_queue': {
                'size': self._inbound_queue.qsize(),
                'max_size': self.config.max_queue_size
            },
            'outbound_queue': {
                'size': self._outbound_queue.qsize(),
                'max_size': self.config.max_queue_size
            },
            'priority_queues': {
                priority.value: {
                    'size': queue.qsize(),
                    'max_size': self.config.max_queue_size // 5
                }
                for priority, queue in self._priority_queues.items()
            },
            'dead_letter_queue': {
                'size': len(self._dlq),
                'max_size': self.config.dlq_max_size
            }
        }
    
    def get_processing_rules(self) -> Dict[str, Any]:
        """Get processing rules information"""
        
        rules_info = {}
        
        for rule_id, rule in self._rules.items():
            rules_info[rule_id] = {
                'name': rule.name,
                'enabled': rule.enabled,
                'priority': rule.priority,
                'matches': rule.matches,
                'executions': rule.executions,
                'errors': rule.errors,
                'success_rate': (rule.executions / max(rule.matches, 1)) * 100,
                'last_executed': rule.last_executed
            }
        
        return rules_info