"""
Data Engine - Feed Manager
Advanced data feed orchestration with real-time streaming, subscription management, and fault tolerance
"""

import logging
import threading
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
import json
import warnings

# Import centralized configuration (Rule 1, Section 7)
try:
    from core_engine.config import DataConfig as CentralizedDataConfig, FeedManagementConfig
except ImportError:
    CentralizedDataConfig = None
    FeedManagementConfig = None

try:
    import websocket
except ImportError:
    websocket = None
import requests
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class FeedType(Enum):
    """Data feed types"""
    MARKET_DATA = "market_data"
    NEWS = "news"
    SENTIMENT = "sentiment"
    FUNDAMENTAL = "fundamental"
    ALTERNATIVE = "alternative"
    REFERENCE = "reference"
    ANALYTICS = "analytics"


class FeedStatus(Enum):
    """Feed connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    SUBSCRIBING = "subscribing"
    ACTIVE = "active"
    ERROR = "error"
    RECONNECTING = "reconnecting"
    SUSPENDED = "suspended"


class DataFormat(Enum):
    """Data format types"""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    BINARY = "binary"
    PROTOBUF = "protobuf"
    AVRO = "avro"
    PARQUET = "parquet"


class SubscriptionType(Enum):
    """Subscription types"""
    REAL_TIME = "real_time"
    DELAYED = "delayed"
    SNAPSHOT = "snapshot"
    HISTORICAL = "historical"
    ON_DEMAND = "on_demand"


@dataclass
class FeedConfiguration:
    """
    Feed configuration for individual data feeds
    
    NOTE: This is a per-feed configuration (not system-wide).
    For system-wide feed management config, use:
        from core_engine.config import FeedManagementConfig
    
    This class configures a specific feed connection/subscription.
    """
    feed_id: str
    feed_type: FeedType
    name: str
    description: str
    
    # Connection details
    url: str
    protocol: str  # websocket, http, tcp, udp
    port: Optional[int] = None
    
    # Authentication
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    auth_method: str = "api_key"  # api_key, oauth, basic, bearer
    
    # Data format
    data_format: DataFormat = DataFormat.JSON
    compression: Optional[str] = None  # gzip, zlib, lz4
    
    # Subscription settings
    subscription_type: SubscriptionType = SubscriptionType.REAL_TIME
    symbols: List[str] = field(default_factory=list)
    fields: List[str] = field(default_factory=list)
    
    # Connection parameters
    connect_timeout: float = 30.0
    read_timeout: float = 10.0
    heartbeat_interval: float = 30.0
    reconnect_interval: float = 5.0
    max_reconnect_attempts: int = 10
    
    # Rate limiting
    max_requests_per_second: Optional[float] = None
    max_concurrent_requests: int = 10
    
    # Buffer settings
    buffer_size: int = 10000
    max_message_size: int = 1024 * 1024  # 1MB
    
    # Quality settings
    enable_data_validation: bool = True
    enable_sequence_check: bool = True
    enable_timestamp_validation: bool = True
    
    # Performance settings
    enable_compression: bool = False
    enable_caching: bool = True
    cache_ttl_seconds: float = 60.0
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedMessage:
    """Feed message container"""
    feed_id: str
    message_id: str
    timestamp: datetime
    sequence_number: Optional[int]
    
    # Message content
    message_type: str
    symbol: Optional[str]
    data: Dict[str, Any]
    raw_data: Optional[bytes] = None
    
    # Quality metadata
    latency_ms: Optional[float] = None
    processing_time_ms: Optional[float] = None
    validation_status: str = "pending"
    
    # Source metadata
    source_timestamp: Optional[datetime] = None
    received_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FeedStatistics:
    """Feed performance statistics"""
    feed_id: str
    
    # Connection statistics
    connection_uptime_seconds: float = 0.0
    total_connections: int = 0
    failed_connections: int = 0
    reconnections: int = 0
    
    # Message statistics
    total_messages: int = 0
    valid_messages: int = 0
    invalid_messages: int = 0
    duplicate_messages: int = 0
    out_of_sequence_messages: int = 0
    
    # Performance metrics
    average_latency_ms: float = 0.0
    average_processing_time_ms: float = 0.0
    message_rate_per_second: float = 0.0
    bytes_received: int = 0
    bytes_processed: int = 0
    
    # Error statistics
    connection_errors: int = 0
    authentication_errors: int = 0
    subscription_errors: int = 0
    parsing_errors: int = 0
    validation_errors: int = 0
    
    # Timestamps
    first_message_time: Optional[datetime] = None
    last_message_time: Optional[datetime] = None
    last_update_time: datetime = field(default_factory=datetime.now)


class DataFeed(ABC):
    """Abstract data feed interface"""
    
    def __init__(self, config: FeedConfiguration):
        self.config = config
        self.status = FeedStatus.DISCONNECTED
        self.statistics = FeedStatistics(feed_id=config.feed_id)
        
        # Message handling
        self._message_handlers = []
        self._error_handlers = []
        self._status_handlers = []
        
        # Threading
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # Buffering
        self._message_buffer = deque(maxlen=config.buffer_size)
        
        # Sequence tracking
        self._last_sequence_number = None
        self._expected_sequence_number = None
        
        logger.info(f"DataFeed {config.feed_id} initialized")
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to data feed"""
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from data feed"""
    
    @abstractmethod
    async def subscribe(self, symbols: List[str], fields: List[str] = None) -> bool:
        """Subscribe to data"""
    
    @abstractmethod
    async def unsubscribe(self, symbols: List[str] = None) -> bool:
        """Unsubscribe from data"""
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if feed is connected"""
    
    def add_message_handler(self, handler: Callable[[FeedMessage], None]) -> None:
        """Add message handler"""
        with self._lock:
            self._message_handlers.append(handler)
    
    def add_error_handler(self, handler: Callable[[str, Exception], None]) -> None:
        """Add error handler"""
        with self._lock:
            self._error_handlers.append(handler)
    
    def add_status_handler(self, handler: Callable[[FeedStatus], None]) -> None:
        """Add status change handler"""
        with self._lock:
            self._status_handlers.append(handler)
    
    def _set_status(self, status: FeedStatus) -> None:
        """Set feed status"""
        if self.status != status:
            old_status = self.status
            self.status = status
            
            logger.info(f"Feed {self.config.feed_id} status: {old_status.value} -> {status.value}")
            
            # Notify handlers
            for handler in self._status_handlers:
                try:
                    handler(status)
                except Exception as e:
                    logger.error(f"Error in status handler: {e}")
    
    def _handle_message(self, message: FeedMessage) -> None:
        """Handle incoming message"""
        
        # Add to buffer
        with self._lock:
            self._message_buffer.append(message)
        
        # Update statistics
        self._update_message_statistics(message)
        
        # Notify handlers
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
    
    def _handle_error(self, error_msg: str, exception: Exception) -> None:
        """Handle error"""
        
        logger.error(f"Feed {self.config.feed_id} error: {error_msg} - {exception}")
        
        # Update statistics
        self.statistics.connection_errors += 1
        
        # Notify handlers
        for handler in self._error_handlers:
            try:
                handler(error_msg, exception)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")
    
    def _update_message_statistics(self, message: FeedMessage) -> None:
        """Update message statistics"""
        
        with self._lock:
            stats = self.statistics
            
            # Message counts
            stats.total_messages += 1
            
            # Timing
            if message.latency_ms:
                current_avg = stats.average_latency_ms
                total_msgs = stats.total_messages
                stats.average_latency_ms = (
                    (current_avg * (total_msgs - 1) + message.latency_ms) / total_msgs
                )
            
            # First/last message times
            if not stats.first_message_time:
                stats.first_message_time = message.timestamp
            stats.last_message_time = message.timestamp
            
            # Message rate calculation
            if stats.first_message_time and stats.last_message_time:
                time_diff = (stats.last_message_time - stats.first_message_time).total_seconds()
                if time_diff > 0:
                    stats.message_rate_per_second = stats.total_messages / time_diff
            
            stats.last_update_time = datetime.now()
    
    def get_recent_messages(self, count: int = 100) -> List[FeedMessage]:
        """Get recent messages from buffer"""
        with self._lock:
            return list(self._message_buffer)[-count:]
    
    def get_statistics(self) -> FeedStatistics:
        """Get feed statistics"""
        with self._lock:
            return self.statistics


class WebSocketFeed(DataFeed):
    """WebSocket data feed implementation"""
    
    def __init__(self, config: FeedConfiguration):
        super().__init__(config)
        self._ws = None
        self._ws_thread = None
        
    async def connect(self) -> bool:
        """Connect to WebSocket feed"""
        try:
            self._set_status(FeedStatus.CONNECTING)
            
            # Create WebSocket connection
            self._ws = websocket.WebSocketApp(
                self.config.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start WebSocket in separate thread
            self._ws_thread = threading.Thread(target=self._ws.run_forever)
            self._ws_thread.start()
            
            # Wait for connection
            for _ in range(int(self.config.connect_timeout)):
                if self.status in [FeedStatus.CONNECTED, FeedStatus.AUTHENTICATED]:
                    return True
                await asyncio.sleep(1)
            
            return False
            
        except Exception as e:
            self._handle_error("Connection failed", e)
            self._set_status(FeedStatus.ERROR)
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from WebSocket feed"""
        try:
            if self._ws:
                self._ws.close()
            
            if self._ws_thread and self._ws_thread.is_alive():
                self._ws_thread.join(timeout=5)
            
            self._set_status(FeedStatus.DISCONNECTED)
            return True
            
        except Exception as e:
            self._handle_error("Disconnection failed", e)
            return False
    
    async def subscribe(self, symbols: List[str], fields: List[str] = None) -> bool:
        """Subscribe to symbols"""
        try:
            if not await self.is_connected():
                return False
            
            # Build subscription message
            subscription_msg = {
                "action": "subscribe",
                "symbols": symbols,
                "fields": fields or self.config.fields
            }
            
            # Send subscription
            self._ws.send(json.dumps(subscription_msg))
            
            self._set_status(FeedStatus.SUBSCRIBING)
            return True
            
        except Exception as e:
            self._handle_error("Subscription failed", e)
            return False
    
    async def unsubscribe(self, symbols: List[str] = None) -> bool:
        """Unsubscribe from symbols"""
        try:
            if not await self.is_connected():
                return False
            
            # Build unsubscription message
            unsubscription_msg = {
                "action": "unsubscribe",
                "symbols": symbols or []
            }
            
            # Send unsubscription
            self._ws.send(json.dumps(unsubscription_msg))
            return True
            
        except Exception as e:
            self._handle_error("Unsubscription failed", e)
            return False
    
    async def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.status in [FeedStatus.CONNECTED, FeedStatus.AUTHENTICATED, FeedStatus.ACTIVE]
    
    def _on_open(self, ws):
        """WebSocket open handler"""
        self._set_status(FeedStatus.CONNECTED)
        self.statistics.total_connections += 1
        
        # Send authentication if required
        if self.config.api_key:
            auth_msg = {
                "action": "auth",
                "api_key": self.config.api_key
            }
            ws.send(json.dumps(auth_msg))
    
    def _on_message(self, ws, message):
        """WebSocket message handler"""
        try:
            # Parse message
            data = json.loads(message)
            
            # Create feed message
            feed_message = FeedMessage(
                feed_id=self.config.feed_id,
                message_id=data.get('id', str(time.time())),
                timestamp=datetime.now(),
                sequence_number=data.get('sequence'),
                message_type=data.get('type', 'data'),
                symbol=data.get('symbol'),
                data=data,
                raw_data=message.encode('utf-8')
            )
            
            # Handle special message types
            if feed_message.message_type == "auth_success":
                self._set_status(FeedStatus.AUTHENTICATED)
            elif feed_message.message_type == "subscription_success":
                self._set_status(FeedStatus.ACTIVE)
            else:
                # Regular data message
                self._handle_message(feed_message)
            
        except Exception as e:
            self._handle_error("Message parsing failed", e)
    
    def _on_error(self, ws, error):
        """WebSocket error handler"""
        self._handle_error("WebSocket error", error)
        self._set_status(FeedStatus.ERROR)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket close handler"""
        self._set_status(FeedStatus.DISCONNECTED)


class HTTPFeed(DataFeed):
    """HTTP polling data feed implementation"""
    
    def __init__(self, config: FeedConfiguration):
        super().__init__(config)
        self._session = None
        self._polling_task = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        
    async def connect(self) -> bool:
        """Connect to HTTP feed"""
        try:
            self._set_status(FeedStatus.CONNECTING)
            
            # Create HTTP session
            self._session = requests.Session()
            
            # Set authentication
            if self.config.api_key:
                self._session.headers.update({'Authorization': f'Bearer {self.config.api_key}'})
            
            # Test connection
            response = self._session.get(self.config.url, timeout=self.config.connect_timeout)
            
            if response.status_code == 200:
                self._set_status(FeedStatus.CONNECTED)
                return True
            else:
                self._handle_error(f"HTTP connection failed: {response.status_code}", 
                                 Exception(response.text))
                return False
                
        except Exception as e:
            self._handle_error("HTTP connection failed", e)
            self._set_status(FeedStatus.ERROR)
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from HTTP feed"""
        try:
            if self._polling_task:
                self._polling_task.cancel()
            
            if self._session:
                self._session.close()
            
            self._set_status(FeedStatus.DISCONNECTED)
            return True
            
        except Exception as e:
            self._handle_error("HTTP disconnection failed", e)
            return False
    
    async def subscribe(self, symbols: List[str], fields: List[str] = None) -> bool:
        """Start polling for data"""
        try:
            if not await self.is_connected():
                return False
            
            # Start polling task
            self._polling_task = asyncio.create_task(self._poll_data(symbols, fields))
            self._set_status(FeedStatus.ACTIVE)
            return True
            
        except Exception as e:
            self._handle_error("HTTP subscription failed", e)
            return False
    
    async def unsubscribe(self, symbols: List[str] = None) -> bool:
        """Stop polling"""
        try:
            if self._polling_task:
                self._polling_task.cancel()
            
            return True
            
        except Exception as e:
            self._handle_error("HTTP unsubscription failed", e)
            return False
    
    async def is_connected(self) -> bool:
        """Check if HTTP session is active"""
        return self.status in [FeedStatus.CONNECTED, FeedStatus.ACTIVE]
    
    async def _poll_data(self, symbols: List[str], fields: List[str]) -> None:
        """Poll data from HTTP endpoint"""
        
        while not self._stop_event.is_set():
            try:
                # Build request parameters
                params = {
                    'symbols': ','.join(symbols),
                    'fields': ','.join(fields or self.config.fields)
                }
                
                # Make request
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    self._executor,
                    lambda: self._session.get(self.config.url, params=params, 
                                            timeout=self.config.read_timeout)
                )
                
                if response.status_code == 200:
                    # Process response
                    data = response.json()
                    
                    # Create feed message
                    feed_message = FeedMessage(
                        feed_id=self.config.feed_id,
                        message_id=str(time.time()),
                        timestamp=datetime.now(),
                        sequence_number=None,
                        message_type='data',
                        symbol=None,
                        data=data,
                        raw_data=response.content
                    )
                    
                    self._handle_message(feed_message)
                else:
                    self._handle_error(f"HTTP polling error: {response.status_code}",
                                     Exception(response.text))
                
                # Wait before next poll
                await asyncio.sleep(1.0)  # 1 second polling interval
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._handle_error("HTTP polling failed", e)
                await asyncio.sleep(5.0)  # Wait before retry


class FeedManager:
    """
    Advanced data feed manager
    
    Orchestrates multiple data feeds with subscription management,
    fault tolerance, and performance monitoring.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize feed manager"""
        self.config = config or {}
        
        # Feed management
        self._feeds = {}
        self._feed_configs = {}
        self._subscriptions = defaultdict(set)  # symbol -> set of feed_ids
        
        # Threading
        self._lock = threading.Lock()
        
        # Message routing
        self._message_handlers = {}  # feed_id -> list of handlers
        self._global_message_handlers = []
        
        # Error handling
        self._error_handlers = {}
        self._global_error_handlers = []
        
        # Performance monitoring
        self._performance_monitor = None
        self._monitoring_interval = self.config.get('monitoring_interval', 60)
        
        # Feed factory
        self._feed_types = {
            'websocket': WebSocketFeed,
            'http': HTTPFeed
        }
        
        # Background tasks
        self._monitoring_task = None
        self._health_check_task = None
        
        logger.info("FeedManager initialized")
    
    def register_feed(self, config: FeedConfiguration) -> bool:
        """Register a data feed"""
        try:
            with self._lock:
                self._feed_configs[config.feed_id] = config
            
            logger.info(f"Registered feed: {config.feed_id} ({config.feed_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register feed {config.feed_id}: {e}")
            return False
    
    def unregister_feed(self, feed_id: str) -> bool:
        """Unregister a data feed"""
        try:
            # Disconnect if connected
            if feed_id in self._feeds:
                asyncio.create_task(self.disconnect_feed(feed_id))
            
            with self._lock:
                self._feed_configs.pop(feed_id, None)
                self._message_handlers.pop(feed_id, None)
                self._error_handlers.pop(feed_id, None)
            
            logger.info(f"Unregistered feed: {feed_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister feed {feed_id}: {e}")
            return False
    
    async def connect_feed(self, feed_id: str) -> bool:
        """Connect to a data feed"""
        try:
            config = self._feed_configs.get(feed_id)
            if not config:
                logger.error(f"Feed {feed_id} not registered")
                return False
            
            # Create feed instance
            feed_class = self._feed_types.get(config.protocol)
            if not feed_class:
                logger.error(f"Unsupported protocol: {config.protocol}")
                return False
            
            feed = feed_class(config)
            
            # Add message and error handlers
            feed.add_message_handler(self._route_message)
            feed.add_error_handler(self._route_error)
            
            # Connect
            if await feed.connect():
                with self._lock:
                    self._feeds[feed_id] = feed
                
                logger.info(f"Connected to feed: {feed_id}")
                return True
            else:
                logger.error(f"Failed to connect to feed: {feed_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to feed {feed_id}: {e}")
            return False
    
    async def disconnect_feed(self, feed_id: str) -> bool:
        """Disconnect from a data feed"""
        try:
            feed = self._feeds.get(feed_id)
            if not feed:
                return True
            
            # Disconnect
            await feed.disconnect()
            
            with self._lock:
                self._feeds.pop(feed_id, None)
            
            logger.info(f"Disconnected from feed: {feed_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from feed {feed_id}: {e}")
            return False
    
    async def subscribe_symbol(
        self,
        symbol: str,
        feed_ids: Optional[List[str]] = None,
        fields: List[str] = None
    ) -> bool:
        """Subscribe to a symbol across feeds"""
        try:
            target_feeds = feed_ids or list(self._feeds.keys())
            success_count = 0
            
            for feed_id in target_feeds:
                feed = self._feeds.get(feed_id)
                if feed and await feed.is_connected():
                    if await feed.subscribe([symbol], fields):
                        with self._lock:
                            self._subscriptions[symbol].add(feed_id)
                        success_count += 1
            
            logger.info(f"Subscribed to {symbol} on {success_count}/{len(target_feeds)} feeds")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error subscribing to symbol {symbol}: {e}")
            return False
    
    async def unsubscribe_symbol(
        self,
        symbol: str,
        feed_ids: Optional[List[str]] = None
    ) -> bool:
        """Unsubscribe from a symbol"""
        try:
            target_feeds = feed_ids or list(self._subscriptions.get(symbol, []))
            success_count = 0
            
            for feed_id in target_feeds:
                feed = self._feeds.get(feed_id)
                if feed:
                    if await feed.unsubscribe([symbol]):
                        with self._lock:
                            self._subscriptions[symbol].discard(feed_id)
                        success_count += 1
            
            # Clean up empty subscriptions
            if not self._subscriptions[symbol]:
                with self._lock:
                    del self._subscriptions[symbol]
            
            logger.info(f"Unsubscribed from {symbol} on {success_count} feeds")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error unsubscribing from symbol {symbol}: {e}")
            return False
    
    def add_message_handler(
        self,
        handler: Callable[[FeedMessage], None],
        feed_id: Optional[str] = None
    ) -> None:
        """Add message handler"""
        
        if feed_id:
            # Feed-specific handler
            with self._lock:
                if feed_id not in self._message_handlers:
                    self._message_handlers[feed_id] = []
                self._message_handlers[feed_id].append(handler)
        else:
            # Global handler
            with self._lock:
                self._global_message_handlers.append(handler)
    
    def add_error_handler(
        self,
        handler: Callable[[str, str, Exception], None],  # feed_id, error_msg, exception
        feed_id: Optional[str] = None
    ) -> None:
        """Add error handler"""
        
        if feed_id:
            # Feed-specific handler
            with self._lock:
                if feed_id not in self._error_handlers:
                    self._error_handlers[feed_id] = []
                self._error_handlers[feed_id].append(handler)
        else:
            # Global handler
            with self._lock:
                self._global_error_handlers.append(handler)
    
    def _route_message(self, message: FeedMessage) -> None:
        """Route message to appropriate handlers"""
        
        # Feed-specific handlers
        handlers = self._message_handlers.get(message.feed_id, [])
        for handler in handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in feed-specific message handler: {e}")
        
        # Global handlers
        for handler in self._global_message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Error in global message handler: {e}")
    
    def _route_error(self, error_msg: str, exception: Exception) -> None:
        """Route error to appropriate handlers"""
        
        # Determine feed_id from context if possible
        feed_id = getattr(exception, 'feed_id', 'unknown')
        
        # Feed-specific handlers
        handlers = self._error_handlers.get(feed_id, [])
        for handler in handlers:
            try:
                handler(feed_id, error_msg, exception)
            except Exception as e:
                logger.error(f"Error in feed-specific error handler: {e}")
        
        # Global handlers
        for handler in self._global_error_handlers:
            try:
                handler(feed_id, error_msg, exception)
            except Exception as e:
                logger.error(f"Error in global error handler: {e}")
    
    async def start_monitoring(self) -> None:
        """Start performance monitoring"""
        
        self._monitoring_task = asyncio.create_task(self._performance_monitoring())
        self._health_check_task = asyncio.create_task(self._health_check())
        
        logger.info("Started feed monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
        
        if self._health_check_task:
            self._health_check_task.cancel()
        
        logger.info("Stopped feed monitoring")
    
    async def _performance_monitoring(self) -> None:
        """Monitor feed performance"""
        
        while True:
            try:
                await asyncio.sleep(self._monitoring_interval)
                
                # Collect statistics from all feeds
                total_messages = 0
                total_errors = 0
                active_feeds = 0
                
                for feed_id, feed in self._feeds.items():
                    stats = feed.get_statistics()
                    total_messages += stats.total_messages
                    total_errors += stats.connection_errors + stats.parsing_errors
                    
                    if feed.status == FeedStatus.ACTIVE:
                        active_feeds += 1
                    
                    logger.debug(f"Feed {feed_id}: {stats.total_messages} messages, "
                               f"{stats.message_rate_per_second:.1f} msg/s, "
                               f"{stats.average_latency_ms:.2f}ms latency")
                
                logger.info(f"Feed monitoring: {active_feeds} active feeds, "
                           f"{total_messages} total messages, {total_errors} errors")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(self._monitoring_interval)
    
    async def _health_check(self) -> None:
        """Perform health checks and auto-recovery"""
        
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                for feed_id, feed in list(self._feeds.items()):
                    if feed.status == FeedStatus.ERROR:
                        logger.warning(f"Feed {feed_id} in error state, attempting reconnection")
                        
                        # Attempt reconnection
                        await self.disconnect_feed(feed_id)
                        await asyncio.sleep(5)
                        await self.connect_feed(feed_id)
                    
                    elif feed.status == FeedStatus.DISCONNECTED:
                        logger.warning(f"Feed {feed_id} disconnected, attempting reconnection")
                        await self.connect_feed(feed_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                await asyncio.sleep(30)
    
    def get_feed_status(self, feed_id: Optional[str] = None) -> Dict[str, Any]:
        """Get feed status information"""
        
        if feed_id:
            feed = self._feeds.get(feed_id)
            if feed:
                return {
                    'feed_id': feed_id,
                    'status': feed.status.value,
                    'statistics': feed.get_statistics()
                }
            else:
                return {'feed_id': feed_id, 'status': 'not_found'}
        else:
            # Get status for all feeds
            status_info = {}
            for fid, feed in self._feeds.items():
                status_info[fid] = {
                    'status': feed.status.value,
                    'statistics': feed.get_statistics()
                }
            return status_info
    
    def get_subscriptions(self) -> Dict[str, List[str]]:
        """Get current subscriptions"""
        
        with self._lock:
            return {symbol: list(feed_ids) for symbol, feed_ids in self._subscriptions.items()}
    
    def get_registered_feeds(self) -> List[str]:
        """Get list of registered feed IDs"""
        
        with self._lock:
            return list(self._feed_configs.keys())
    
    def get_active_feeds(self) -> List[str]:
        """Get list of active feed IDs"""
        
        return [feed_id for feed_id, feed in self._feeds.items() 
                if feed.status == FeedStatus.ACTIVE]
    
    async def cleanup(self) -> None:
        """Cleanup feed manager resources"""
        
        # Stop monitoring
        await self.stop_monitoring()
        
        # Disconnect all feeds
        for feed_id in list(self._feeds.keys()):
            await self.disconnect_feed(feed_id)
        
        logger.info("FeedManager cleanup completed")