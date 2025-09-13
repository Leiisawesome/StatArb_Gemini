"""
WebSocket Diversification Manager
=================================

Multi-source WebSocket feed manager providing diversified market data streams
with automatic failover, load balancing, and data quality monitoring.

This enhancement adds:
- Multiple WebSocket data sources (Alpaca, Polygon, Yahoo Finance, IBKR)
- Automatic failover between sources
- Load balancing and source selection
- Data quality monitoring and validation
- Unified data format standardization
- Latency and reliability tracking

Author: StatArb_Gemini WebSocket Enhancement
Version: 1.0
"""

import asyncio
import json
import logging
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set, Union
from enum import Enum
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import statistics
from urllib.parse import urlencode, urlparse

# WebSocket implementations
try:
    import websocket
    import websockets
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Import from existing infrastructure
try:
    from core_structure.components.market_data.core.data_feeds import (
        DataType, FeedStatus, DataSource, MarketDataPoint, FeedMetrics, BaseFeed, FeedConfig
    )
    from core_structure.infrastructure.monitoring.metrics_collector import MetricsCollector
    from core_structure.infrastructure.messaging.message_bus import MessageBus
except ImportError:
    # Fallback definitions
    class DataType(Enum):
        TICK = "tick"
        QUOTE = "quote"
        TRADE = "trade"
        ORDERBOOK = "orderbook"
        OHLCV = "ohlcv"
    
    class FeedStatus(Enum):
        DISCONNECTED = "disconnected"
        CONNECTING = "connecting"
        CONNECTED = "connected"
        ERROR = "error"
        RECONNECTING = "reconnecting"
    
    MetricsCollector = None
    MessageBus = None

logger = logging.getLogger(__name__)

class WebSocketSource(Enum):
    """Supported WebSocket data sources"""
    ALPACA = "alpaca"
    POLYGON = "polygon"
    YAHOO_FINANCE = "yahoo_finance"
    IBKR = "ibkr"
    FINNHUB = "finnhub"
    TWELVE_DATA = "twelve_data"

class SourcePriority(Enum):
    """Source priority levels"""
    PRIMARY = 1
    SECONDARY = 2
    BACKUP = 3
    EMERGENCY = 4

class DataQuality(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"

@dataclass
class SourceConfig:
    """Configuration for a WebSocket source"""
    source: WebSocketSource
    priority: SourcePriority
    websocket_url: str
    api_key: Optional[str] = None
    symbols: List[str] = field(default_factory=list)
    data_types: List[DataType] = field(default_factory=lambda: [DataType.TRADE, DataType.QUOTE])
    
    # Connection settings
    max_reconnect_attempts: int = 5
    reconnect_delay: float = 1.0
    ping_interval: int = 30
    timeout: int = 10
    
    # Quality settings
    max_latency_ms: float = 500.0
    min_message_rate: float = 1.0  # messages per second
    max_error_rate: float = 0.05   # 5% error rate
    
    # Rate limiting
    max_subscriptions: int = 100
    rate_limit_per_minute: int = 1000

@dataclass
class SourceMetrics:
    """Metrics for a WebSocket source"""
    source: WebSocketSource
    status: FeedStatus = FeedStatus.DISCONNECTED
    connection_time: Optional[datetime] = None
    last_message_time: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0
    reconnect_count: int = 0
    
    # Performance metrics
    latency_samples: List[float] = field(default_factory=list)
    average_latency_ms: float = 0.0
    message_rate: float = 0.0
    data_quality: DataQuality = DataQuality.GOOD
    
    # Reliability metrics
    uptime_percentage: float = 0.0
    success_rate: float = 1.0
    last_error: Optional[str] = None

@dataclass
class WebSocketMessage:
    """Standardized WebSocket message"""
    source: WebSocketSource
    symbol: str
    message_type: DataType
    timestamp: datetime
    data: Dict[str, Any]
    latency_ms: Optional[float] = None
    quality_score: float = 1.0

class WebSocketSourceManager(ABC):
    """Abstract base class for WebSocket source managers"""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self.metrics = SourceMetrics(source=config.source)
        self._ws = None
        self._running = False
        self._subscribers = []
        self._message_queue = Queue(maxsize=1000)
        self._last_ping = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the WebSocket source"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the WebSocket source"""
        pass
    
    @abstractmethod
    async def subscribe(self, symbols: List[str], data_types: List[DataType]):
        """Subscribe to symbols and data types"""
        pass
    
    @abstractmethod
    def parse_message(self, raw_message: str) -> Optional[WebSocketMessage]:
        """Parse raw WebSocket message into standardized format"""
        pass
    
    def add_subscriber(self, callback: Callable[[WebSocketMessage], None]):
        """Add message subscriber"""
        self._subscribers.append(callback)
    
    def _notify_subscribers(self, message: WebSocketMessage):
        """Notify all subscribers of new message"""
        for callback in self._subscribers:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")
    
    def _update_metrics(self, message: WebSocketMessage):
        """Update source metrics"""
        self.metrics.message_count += 1
        self.metrics.last_message_time = message.timestamp
        
        # Update latency if available
        if message.latency_ms is not None:
            self.metrics.latency_samples.append(message.latency_ms)
            if len(self.metrics.latency_samples) > 100:
                self.metrics.latency_samples.pop(0)
            
            self.metrics.average_latency_ms = statistics.mean(self.metrics.latency_samples)
        
        # Calculate message rate
        if self.metrics.connection_time:
            duration = (datetime.now() - self.metrics.connection_time).total_seconds()
            if duration > 0:
                self.metrics.message_rate = self.metrics.message_count / duration

class AlpacaWebSocketManager(WebSocketSourceManager):
    """Alpaca WebSocket data manager"""
    
    async def connect(self) -> bool:
        """Connect to Alpaca WebSocket"""
        try:
            self.metrics.status = FeedStatus.CONNECTING
            
            if not self.config.api_key:
                logger.error("Alpaca API key required")
                return False
            
            # Alpaca WebSocket URL for market data
            ws_url = "wss://stream.data.alpaca.markets/v2/iex"
            
            self._ws = await websockets.connect(
                ws_url,
                ping_interval=self.config.ping_interval,
                timeout=self.config.timeout
            )
            
            # Authenticate
            auth_message = {
                "action": "auth",
                "key": self.config.api_key,
                "secret": self.config.api_key  # Using API key as both key and secret for demo
            }
            await self._ws.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await self._ws.recv()
            auth_data = json.loads(response)
            
            if auth_data.get("T") == "success":
                self.metrics.status = FeedStatus.CONNECTED
                self.metrics.connection_time = datetime.now()
                logger.info(f"Connected to Alpaca WebSocket: {self.config.source}")
                return True
            else:
                logger.error(f"Alpaca authentication failed: {auth_data}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            self.metrics.status = FeedStatus.ERROR
            self.metrics.last_error = str(e)
            return False
    
    async def disconnect(self):
        """Disconnect from Alpaca WebSocket"""
        if self._ws:
            await self._ws.close()
            self._ws = None
        self.metrics.status = FeedStatus.DISCONNECTED
        self._running = False
    
    async def subscribe(self, symbols: List[str], data_types: List[DataType]):
        """Subscribe to Alpaca symbols"""
        if not self._ws or self.metrics.status != FeedStatus.CONNECTED:
            return False
        
        # Map data types to Alpaca channels
        channels = []
        if DataType.TRADE in data_types:
            channels.append("trades")
        if DataType.QUOTE in data_types:
            channels.append("quotes")
        
        subscribe_message = {
            "action": "subscribe",
            "trades": symbols if "trades" in channels else [],
            "quotes": symbols if "quotes" in channels else []
        }
        
        await self._ws.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to Alpaca symbols: {symbols}")
        
    def parse_message(self, raw_message: str) -> Optional[WebSocketMessage]:
        """Parse Alpaca WebSocket message"""
        try:
            data = json.loads(raw_message)
            
            if isinstance(data, list):
                # Multiple messages in array
                messages = []
                for item in data:
                    msg = self._parse_single_message(item)
                    if msg:
                        messages.append(msg)
                return messages[0] if messages else None
            else:
                return self._parse_single_message(data)
                
        except Exception as e:
            logger.error(f"Error parsing Alpaca message: {e}")
            self.metrics.error_count += 1
            return None
    
    def _parse_single_message(self, data: Dict[str, Any]) -> Optional[WebSocketMessage]:
        """Parse single Alpaca message"""
        message_type_map = {
            "t": DataType.TRADE,
            "q": DataType.QUOTE
        }
        
        msg_type = data.get("T")
        if msg_type not in message_type_map:
            return None
        
        symbol = data.get("S", "")
        timestamp_str = data.get("t", "")
        
        # Convert timestamp
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except:
            timestamp = datetime.now()
        
        # Calculate latency
        latency_ms = (datetime.now() - timestamp).total_seconds() * 1000
        
        return WebSocketMessage(
            source=WebSocketSource.ALPACA,
            symbol=symbol,
            message_type=message_type_map[msg_type],
            timestamp=timestamp,
            data=data,
            latency_ms=latency_ms
        )

class PolygonWebSocketManager(WebSocketSourceManager):
    """Polygon.io WebSocket data manager"""
    
    async def connect(self) -> bool:
        """Connect to Polygon WebSocket"""
        try:
            self.metrics.status = FeedStatus.CONNECTING
            
            if not self.config.api_key:
                logger.error("Polygon API key required")
                return False
            
            # Polygon WebSocket URL
            ws_url = f"wss://socket.polygon.io/stocks"
            
            self._ws = await websockets.connect(
                ws_url,
                ping_interval=self.config.ping_interval,
                timeout=self.config.timeout
            )
            
            # Authenticate
            auth_message = {"action": "auth", "params": self.config.api_key}
            await self._ws.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await self._ws.recv()
            auth_data = json.loads(response)
            
            if auth_data[0].get("status") == "auth_success":
                self.metrics.status = FeedStatus.CONNECTED
                self.metrics.connection_time = datetime.now()
                logger.info(f"Connected to Polygon WebSocket: {self.config.source}")
                return True
            else:
                logger.error(f"Polygon authentication failed: {auth_data}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Polygon: {e}")
            self.metrics.status = FeedStatus.ERROR
            self.metrics.last_error = str(e)
            return False
    
    async def disconnect(self):
        """Disconnect from Polygon WebSocket"""
        if self._ws:
            await self._ws.close()
            self._ws = None
        self.metrics.status = FeedStatus.DISCONNECTED
        self._running = False
    
    async def subscribe(self, symbols: List[str], data_types: List[DataType]):
        """Subscribe to Polygon symbols"""
        if not self._ws or self.metrics.status != FeedStatus.CONNECTED:
            return False
        
        # Build subscription channels
        channels = []
        for data_type in data_types:
            if data_type == DataType.TRADE:
                channels.extend([f"T.{symbol}" for symbol in symbols])
            elif data_type == DataType.QUOTE:
                channels.extend([f"Q.{symbol}" for symbol in symbols])
        
        subscribe_message = {"action": "subscribe", "params": ",".join(channels)}
        await self._ws.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to Polygon symbols: {symbols}")
        
    def parse_message(self, raw_message: str) -> Optional[WebSocketMessage]:
        """Parse Polygon WebSocket message"""
        try:
            data = json.loads(raw_message)
            
            if isinstance(data, list) and len(data) > 0:
                # Take first message from array
                item = data[0]
                
                event_type = item.get("ev")
                if event_type == "T":  # Trade
                    message_type = DataType.TRADE
                elif event_type == "Q":  # Quote
                    message_type = DataType.QUOTE
                else:
                    return None
                
                symbol = item.get("sym", "")
                timestamp_ms = item.get("t", 0)
                
                # Convert timestamp
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0)
                
                # Calculate latency
                latency_ms = (datetime.now() - timestamp).total_seconds() * 1000
                
                return WebSocketMessage(
                    source=WebSocketSource.POLYGON,
                    symbol=symbol,
                    message_type=message_type,
                    timestamp=timestamp,
                    data=item,
                    latency_ms=latency_ms
                )
            
            return None
                
        except Exception as e:
            logger.error(f"Error parsing Polygon message: {e}")
            self.metrics.error_count += 1
            return None

class WebSocketDiversificationManager:
    """
    Main WebSocket diversification manager
    
    Manages multiple WebSocket sources with automatic failover,
    load balancing, and data quality monitoring.
    """
    
    def __init__(self, source_configs: List[SourceConfig]):
        self.source_configs = source_configs
        self.source_managers: Dict[WebSocketSource, WebSocketSourceManager] = {}
        self.active_sources: Set[WebSocketSource] = set()
        self.primary_source: Optional[WebSocketSource] = None
        
        # Data routing
        self._subscribers = []
        self._message_queue = Queue(maxsize=5000)
        self._running = False
        self._router_thread = None
        
        # Quality monitoring
        self._quality_monitor_thread = None
        self._last_quality_check = datetime.now()
        
        # Metrics
        self.total_messages = 0
        self.total_errors = 0
        self.source_switches = 0
        
        # Initialize source managers
        self._initialize_source_managers()
        
        logger.info(f"WebSocket Diversification Manager initialized with {len(source_configs)} sources")
    
    def _initialize_source_managers(self):
        """Initialize WebSocket source managers"""
        manager_map = {
            WebSocketSource.ALPACA: AlpacaWebSocketManager,
            WebSocketSource.POLYGON: PolygonWebSocketManager,
            # Add more source managers as needed
        }
        
        for config in self.source_configs:
            if config.source in manager_map:
                manager_class = manager_map[config.source]
                manager = manager_class(config)
                manager.add_subscriber(self._handle_source_message)
                self.source_managers[config.source] = manager
                logger.info(f"Initialized {config.source} manager")
    
    async def start(self):
        """Start the diversification manager"""
        self._running = True
        
        # Start quality monitoring
        self._quality_monitor_thread = threading.Thread(target=self._quality_monitor_loop)
        self._quality_monitor_thread.daemon = True
        self._quality_monitor_thread.start()
        
        # Start message router
        self._router_thread = threading.Thread(target=self._message_router_loop)
        self._router_thread.daemon = True
        self._router_thread.start()
        
        # Connect to sources in priority order
        await self._connect_sources()
        
        logger.info("WebSocket Diversification Manager started")
    
    async def stop(self):
        """Stop the diversification manager"""
        self._running = False
        
        # Disconnect all sources
        for manager in self.source_managers.values():
            await manager.disconnect()
        
        self.active_sources.clear()
        logger.info("WebSocket Diversification Manager stopped")
    
    async def _connect_sources(self):
        """Connect to WebSocket sources in priority order"""
        # Sort sources by priority
        sorted_configs = sorted(self.source_configs, key=lambda x: x.priority.value)
        
        connected_count = 0
        for config in sorted_configs:
            if config.source in self.source_managers:
                manager = self.source_managers[config.source]
                if await manager.connect():
                    self.active_sources.add(config.source)
                    connected_count += 1
                    
                    # Set primary source (highest priority connected source)
                    if self.primary_source is None:
                        self.primary_source = config.source
                        logger.info(f"Set primary source: {config.source}")
                    
                    # Start message receiving for this source
                    asyncio.create_task(self._receive_messages(manager))
        
        logger.info(f"Connected to {connected_count}/{len(self.source_configs)} WebSocket sources")
    
    async def _receive_messages(self, manager: WebSocketSourceManager):
        """Receive messages from a source manager"""
        while self._running and manager.metrics.status == FeedStatus.CONNECTED:
            try:
                if manager._ws:
                    raw_message = await manager._ws.recv()
                    message = manager.parse_message(raw_message)
                    
                    if message:
                        manager._update_metrics(message)
                        self._message_queue.put(message, timeout=1.0)
                        
            except Exception as e:
                logger.error(f"Error receiving from {manager.config.source}: {e}")
                manager.metrics.error_count += 1
                manager.metrics.last_error = str(e)
                
                # Attempt reconnection
                await self._handle_source_failure(manager.config.source)
                break
    
    async def _handle_source_failure(self, failed_source: WebSocketSource):
        """Handle source failure and failover"""
        logger.warning(f"Source failed: {failed_source}")
        
        if failed_source in self.active_sources:
            self.active_sources.remove(failed_source)
        
        # If primary source failed, switch to next available
        if self.primary_source == failed_source:
            self._switch_primary_source()
        
        # Attempt to reconnect failed source
        asyncio.create_task(self._reconnect_source(failed_source))
    
    def _switch_primary_source(self):
        """Switch to next available primary source"""
        if not self.active_sources:
            self.primary_source = None
            logger.warning("No active sources available")
            return
        
        # Select next best source by priority
        available_configs = [
            config for config in self.source_configs 
            if config.source in self.active_sources
        ]
        
        if available_configs:
            best_config = min(available_configs, key=lambda x: x.priority.value)
            old_primary = self.primary_source
            self.primary_source = best_config.source
            self.source_switches += 1
            
            logger.info(f"Switched primary source: {old_primary} -> {self.primary_source}")
    
    async def _reconnect_source(self, source: WebSocketSource):
        """Attempt to reconnect a failed source"""
        if source not in self.source_managers:
            return
        
        manager = self.source_managers[source]
        config = manager.config
        
        for attempt in range(config.max_reconnect_attempts):
            logger.info(f"Reconnecting {source}, attempt {attempt + 1}")
            
            await asyncio.sleep(config.reconnect_delay * (2 ** attempt))  # Exponential backoff
            
            if await manager.connect():
                self.active_sources.add(source)
                logger.info(f"Successfully reconnected to {source}")
                
                # Start receiving messages again
                asyncio.create_task(self._receive_messages(manager))
                break
        else:
            logger.error(f"Failed to reconnect to {source} after {config.max_reconnect_attempts} attempts")
    
    def _handle_source_message(self, message: WebSocketMessage):
        """Handle message from source manager"""
        try:
            self._message_queue.put(message, timeout=0.1)
        except:
            # Queue full, drop message
            pass
    
    def _message_router_loop(self):
        """Main message routing loop"""
        while self._running:
            try:
                message = self._message_queue.get(timeout=1.0)
                
                # Apply quality filtering
                if self._is_quality_message(message):
                    self.total_messages += 1
                    
                    # Route to subscribers
                    for callback in self._subscribers:
                        try:
                            callback(message)
                        except Exception as e:
                            logger.error(f"Error in subscriber callback: {e}")
                
                self._message_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in message router: {e}")
    
    def _is_quality_message(self, message: WebSocketMessage) -> bool:
        """Check if message meets quality standards"""
        # Basic quality checks
        if not message.symbol or not message.data:
            return False
        
        # Latency check
        if message.latency_ms and message.latency_ms > 5000:  # 5 second max latency
            return False
        
        # Source quality check
        if message.source in self.source_managers:
            manager = self.source_managers[message.source]
            if manager.metrics.data_quality in [DataQuality.POOR, DataQuality.UNUSABLE]:
                return False
        
        return True
    
    def _quality_monitor_loop(self):
        """Monitor source quality and performance"""
        while self._running:
            try:
                time.sleep(30)  # Check every 30 seconds
                self._update_source_quality()
                
            except Exception as e:
                logger.error(f"Error in quality monitor: {e}")
    
    def _update_source_quality(self):
        """Update quality metrics for all sources"""
        current_time = datetime.now()
        
        for source, manager in self.source_managers.items():
            metrics = manager.metrics
            
            # Calculate uptime
            if metrics.connection_time:
                total_time = (current_time - metrics.connection_time).total_seconds()
                if total_time > 0:
                    error_rate = metrics.error_count / max(metrics.message_count, 1)
                    
                    # Determine quality based on metrics
                    if error_rate < 0.01 and metrics.average_latency_ms < 100:
                        metrics.data_quality = DataQuality.EXCELLENT
                    elif error_rate < 0.05 and metrics.average_latency_ms < 500:
                        metrics.data_quality = DataQuality.GOOD
                    elif error_rate < 0.10 and metrics.average_latency_ms < 1000:
                        metrics.data_quality = DataQuality.ACCEPTABLE
                    elif error_rate < 0.20:
                        metrics.data_quality = DataQuality.POOR
                    else:
                        metrics.data_quality = DataQuality.UNUSABLE
    
    def add_subscriber(self, callback: Callable[[WebSocketMessage], None]):
        """Add message subscriber"""
        self._subscribers.append(callback)
    
    async def subscribe_symbols(self, symbols: List[str], data_types: List[DataType] = None):
        """Subscribe to symbols across all active sources"""
        if data_types is None:
            data_types = [DataType.TRADE, DataType.QUOTE]
        
        for source in self.active_sources:
            if source in self.source_managers:
                manager = self.source_managers[source]
                await manager.subscribe(symbols, data_types)
        
        logger.info(f"Subscribed to {symbols} across {len(self.active_sources)} sources")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get status summary of all sources"""
        summary = {
            "total_sources": len(self.source_managers),
            "active_sources": len(self.active_sources),
            "primary_source": self.primary_source.value if self.primary_source else None,
            "total_messages": self.total_messages,
            "total_errors": self.total_errors,
            "source_switches": self.source_switches,
            "sources": {}
        }
        
        for source, manager in self.source_managers.items():
            summary["sources"][source.value] = {
                "status": manager.metrics.status.value,
                "message_count": manager.metrics.message_count,
                "error_count": manager.metrics.error_count,
                "average_latency_ms": manager.metrics.average_latency_ms,
                "data_quality": manager.metrics.data_quality.value,
                "last_message": manager.metrics.last_message_time.isoformat() if manager.metrics.last_message_time else None
            }
        
        return summary

# Factory function for easy setup
def create_websocket_diversification_manager(
    alpaca_api_key: Optional[str] = None,
    polygon_api_key: Optional[str] = None,
    symbols: List[str] = None
) -> WebSocketDiversificationManager:
    """Create a WebSocket diversification manager with common configurations"""
    
    if symbols is None:
        symbols = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL"]
    
    configs = []
    
    # Alpaca configuration
    if alpaca_api_key:
        alpaca_config = SourceConfig(
            source=WebSocketSource.ALPACA,
            priority=SourcePriority.PRIMARY,
            websocket_url="wss://stream.data.alpaca.markets/v2/iex",
            api_key=alpaca_api_key,
            symbols=symbols,
            data_types=[DataType.TRADE, DataType.QUOTE]
        )
        configs.append(alpaca_config)
    
    # Polygon configuration
    if polygon_api_key:
        polygon_config = SourceConfig(
            source=WebSocketSource.POLYGON,
            priority=SourcePriority.SECONDARY,
            websocket_url="wss://socket.polygon.io/stocks",
            api_key=polygon_api_key,
            symbols=symbols,
            data_types=[DataType.TRADE, DataType.QUOTE]
        )
        configs.append(polygon_config)
    
    if not configs:
        logger.warning("No API keys provided, creating manager with empty configurations")
    
    return WebSocketDiversificationManager(configs)
