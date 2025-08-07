"""
Enhanced Real-Time Market Data Feeds System
Institutional-grade data feeds with AI-ready streaming capabilities
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, AsyncIterator
from enum import Enum
import requests
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue, Empty

from ..infrastructure.messaging.message_bus import MessageBus
from ..infrastructure.monitoring.metrics_collector import MetricsCollector
from ..infrastructure.config import UnifiedConfigManager as ConfigManager

# Optional websocket dependency
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


class DataType(Enum):
    """Market data types"""
    TICK = "tick"
    QUOTE = "quote"
    TRADE = "trade"
    ORDERBOOK = "orderbook"
    NEWS = "news"
    CORPORATE_ACTION = "corporate_action"


class FeedStatus(Enum):
    """Feed connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class MarketTick:
    """Standardized market tick data"""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    data_type: DataType = DataType.TICK
    exchange: Optional[str] = None
    conditions: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for messaging"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['data_type'] = self.data_type.value
        return data


@dataclass
class FeedMetrics:
    """Feed performance metrics"""
    feed_name: str
    messages_received: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    latency_ms: float = 0.0
    connection_uptime: float = 0.0
    last_message_time: Optional[datetime] = None
    data_quality_score: float = 1.0


class BaseFeed(ABC):
    """Abstract base class for market data feeds"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.status = FeedStatus.DISCONNECTED
        self.logger = logging.getLogger(f"feeds.{name}")
        self.message_bus = MessageBus()
        self.metrics = MetricsCollector()
        self.callbacks: List[Callable[[MarketTick], None]] = []
        self.metrics_data = FeedMetrics(feed_name=name)
        self._stop_event = threading.Event()
        self._connection_thread: Optional[threading.Thread] = None
        self._connection_start_time: float = 0.0
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the data feed"""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the data feed"""
        pass
        
    @abstractmethod
    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to symbols"""
        pass
        
    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from symbols"""
        pass
    
    def add_callback(self, callback: Callable[[MarketTick], None]) -> None:
        """Add data callback"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[MarketTick], None]) -> None:
        """Remove data callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _process_tick(self, tick: MarketTick) -> None:
        """Process incoming tick data"""
        try:
            start_time = time.time()
            
            # Update metrics
            self.metrics_data.messages_received += 1
            self.metrics_data.last_message_time = datetime.now()
            
            # Data quality checks
            if self._validate_tick(tick):
                self.metrics_data.messages_processed += 1
                
                # Send to callbacks
                for callback in self.callbacks:
                    try:
                        callback(tick)
                    except Exception as e:
                        self.logger.error(f"Callback error: {e}")
                
                # Publish to message bus
                self.message_bus.publish(
                    message_type=f"market_data.{tick.symbol}",
                    payload=tick.to_dict()
                )
                
                # Publish to AI data stream
                self.message_bus.publish(
                    message_type="ai.market_data_stream",
                    payload={
                        "type": "market_tick",
                        "data": tick.to_dict(),
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
            else:
                self.metrics_data.messages_failed += 1
                self.metrics_data.data_quality_score *= 0.999  # Decay quality score
            
            # Update latency metrics
            processing_time = (time.time() - start_time) * 1000
            self.metrics_data.latency_ms = (
                self.metrics_data.latency_ms * 0.9 + processing_time * 0.1
            )
            
            # Report metrics
            self.metrics.record_latency(
                f"feed.{self.name}.processing_latency_ms",
                processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Error processing tick: {e}")
            self.metrics_data.messages_failed += 1
    
    def _validate_tick(self, tick: MarketTick) -> bool:
        """Validate tick data quality"""
        try:
            # Basic validation
            if not tick.symbol or tick.price <= 0:
                return False
            
            # Timestamp validation (not too old or in future)
            now = datetime.now()
            if abs((tick.timestamp - now).total_seconds()) > 300:  # 5 minutes
                return False
            
            # Price sanity checks
            if tick.bid and tick.ask and tick.bid >= tick.ask:
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_metrics(self) -> FeedMetrics:
        """Get feed metrics"""
        if self._connection_thread and self._connection_start_time:
            uptime = time.time() - self._connection_start_time
            self.metrics_data.connection_uptime = uptime
        
        return self.metrics_data


class PolygonFeed(BaseFeed):
    """Polygon.io real-time feed"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("polygon", config)
        self.api_key = config.get("api_key")
        self.ws_url = "wss://socket.polygon.io/stocks"
        self.ws: Optional[Any] = None  # websocket.WebSocketApp
        self.subscribed_symbols = set()
        
    async def connect(self) -> bool:
        """Connect to Polygon WebSocket"""
        try:
            if not WEBSOCKET_AVAILABLE:
                self.logger.error("WebSocket library not available. Install websocket-client.")
                return False
                
            self.status = FeedStatus.CONNECTING
            self.logger.info("Connecting to Polygon feed...")
            
            # Create WebSocket connection in separate thread
            self._connection_thread = threading.Thread(
                target=self._run_websocket,
                daemon=True
            )
            self._connection_start_time = time.time()
            self._connection_thread.start()
            
            # Wait for connection
            await asyncio.sleep(2)
            
            if self.status == FeedStatus.CONNECTED:
                self.logger.info("Connected to Polygon feed")
                return True
            else:
                self.logger.error("Failed to connect to Polygon feed")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.status = FeedStatus.ERROR
            return False
    
    def _run_websocket(self):
        """Run WebSocket in separate thread"""
        try:
            if not WEBSOCKET_AVAILABLE:
                return
                
            def on_open(ws):
                self.logger.info("Polygon WebSocket opened")
                # Authenticate
                auth_msg = {"action": "auth", "params": self.api_key}
                ws.send(json.dumps(auth_msg))
                self.status = FeedStatus.CONNECTED
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if isinstance(data, list):
                        for item in data:
                            self._process_polygon_message(item)
                    else:
                        self._process_polygon_message(data)
                except Exception as e:
                    self.logger.error(f"Message processing error: {e}")
            
            def on_error(ws, error):
                self.logger.error(f"Polygon WebSocket error: {error}")
                self.status = FeedStatus.ERROR
            
            def on_close(ws, close_status_code, close_msg):
                self.logger.info("Polygon WebSocket closed")
                self.status = FeedStatus.DISCONNECTED
            
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            self.ws.run_forever()
            
        except Exception as e:
            self.logger.error(f"WebSocket thread error: {e}")
            self.status = FeedStatus.ERROR
    
    def _process_polygon_message(self, message: Dict[str, Any]):
        """Process Polygon message format"""
        try:
            if message.get("ev") == "T":  # Trade
                tick = MarketTick(
                    symbol=message.get("sym", ""),
                    timestamp=datetime.fromtimestamp(message.get("t", 0) / 1000),
                    price=float(message.get("p", 0)),
                    volume=int(message.get("s", 0)),
                    data_type=DataType.TRADE,
                    exchange=message.get("x")
                )
                self._process_tick(tick)
                
            elif message.get("ev") == "Q":  # Quote
                tick = MarketTick(
                    symbol=message.get("sym", ""),
                    timestamp=datetime.fromtimestamp(message.get("t", 0) / 1000),
                    price=(float(message.get("bp", 0)) + float(message.get("ap", 0))) / 2,
                    volume=0,
                    bid=float(message.get("bp", 0)),
                    ask=float(message.get("ap", 0)),
                    bid_size=int(message.get("bs", 0)),
                    ask_size=int(message.get("as", 0)),
                    data_type=DataType.QUOTE,
                    exchange=message.get("x")
                )
                self._process_tick(tick)
                
        except Exception as e:
            self.logger.error(f"Error processing Polygon message: {e}")
    
    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to symbols"""
        try:
            if self.status != FeedStatus.CONNECTED or not self.ws:
                return False
            
            for symbol in symbols:
                if symbol not in self.subscribed_symbols:
                    # Subscribe to trades and quotes
                    trade_msg = {"action": "subscribe", "params": f"T.{symbol}"}
                    quote_msg = {"action": "subscribe", "params": f"Q.{symbol}"}
                    
                    self.ws.send(json.dumps(trade_msg))
                    self.ws.send(json.dumps(quote_msg))
                    
                    self.subscribed_symbols.add(symbol)
                    self.logger.info(f"Subscribed to {symbol}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Subscription error: {e}")
            return False
    
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from symbols"""
        try:
            if self.status != FeedStatus.CONNECTED or not self.ws:
                return False
            
            for symbol in symbols:
                if symbol in self.subscribed_symbols:
                    # Unsubscribe from trades and quotes
                    trade_msg = {"action": "unsubscribe", "params": f"T.{symbol}"}
                    quote_msg = {"action": "unsubscribe", "params": f"Q.{symbol}"}
                    
                    self.ws.send(json.dumps(trade_msg))
                    self.ws.send(json.dumps(quote_msg))
                    
                    self.subscribed_symbols.remove(symbol)
                    self.logger.info(f"Unsubscribed from {symbol}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Unsubscription error: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Polygon feed"""
        try:
            self._stop_event.set()
            if self.ws:
                self.ws.close()
            self.status = FeedStatus.DISCONNECTED
            self.logger.info("Disconnected from Polygon feed")
            
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")


class AlphaVantageFeed(BaseFeed):
    """Alpha Vantage real-time feed (REST-based polling)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("alphavantage", config)
        self.api_key = config.get("api_key")
        self.base_url = "https://www.alphavantage.co/query"
        self.poll_interval = config.get("poll_interval", 5)  # seconds
        self.subscribed_symbols = set()
        self._polling_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> bool:
        """Connect to Alpha Vantage (start polling)"""
        try:
            self.status = FeedStatus.CONNECTING
            self.logger.info("Starting Alpha Vantage polling...")
            
            # Test API connection
            test_url = f"{self.base_url}?function=GLOBAL_QUOTE&symbol=AAPL&apikey={self.api_key}"
            response = requests.get(test_url, timeout=10)
            
            if response.status_code == 200:
                self.status = FeedStatus.CONNECTED
                self.logger.info("Connected to Alpha Vantage")
                return True
            else:
                self.logger.error(f"Alpha Vantage connection failed: {response.status_code}")
                self.status = FeedStatus.ERROR
                return False
                
        except Exception as e:
            self.logger.error(f"Alpha Vantage connection error: {e}")
            self.status = FeedStatus.ERROR
            return False
    
    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to symbols (start polling)"""
        try:
            for symbol in symbols:
                self.subscribed_symbols.add(symbol)
                self.logger.info(f"Added {symbol} to polling list")
            
            # Start polling task if not running
            if not self._polling_task or self._polling_task.done():
                self._polling_task = asyncio.create_task(self._poll_data())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Alpha Vantage subscription error: {e}")
            return False
    
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from symbols"""
        try:
            for symbol in symbols:
                self.subscribed_symbols.discard(symbol)
                self.logger.info(f"Removed {symbol} from polling list")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Alpha Vantage unsubscription error: {e}")
            return False
    
    async def _poll_data(self):
        """Poll data for subscribed symbols"""
        while not self._stop_event.is_set() and self.subscribed_symbols:
            try:
                for symbol in list(self.subscribed_symbols):
                    await self._fetch_quote(symbol)
                    
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                self.logger.error(f"Polling error: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def _fetch_quote(self, symbol: str):
        """Fetch quote for symbol"""
        try:
            url = f"{self.base_url}?function=GLOBAL_QUOTE&symbol={symbol}&apikey={self.api_key}"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, timeout=10)
            )
            
            if response.status_code == 200:
                data = response.json()
                quote_data = data.get("Global Quote", {})
                
                if quote_data:
                    tick = MarketTick(
                        symbol=symbol,
                        timestamp=datetime.now(),
                        price=float(quote_data.get("05. price", 0)),
                        volume=int(float(quote_data.get("06. volume", 0))),
                        data_type=DataType.QUOTE
                    )
                    self._process_tick(tick)
                    
        except Exception as e:
            self.logger.error(f"Error fetching quote for {symbol}: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from Alpha Vantage (stop polling)"""
        try:
            self._stop_event.set()
            if self._polling_task:
                self._polling_task.cancel()
            self.status = FeedStatus.DISCONNECTED
            self.logger.info("Disconnected from Alpha Vantage")
            
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")


class FeedManager:
    """Manages multiple market data feeds"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger("feeds.manager")
        self.feeds: Dict[str, BaseFeed] = {}
        self.message_bus = MessageBus()
        self.metrics = MetricsCollector()
        self._setup_feeds()
    
    def _setup_feeds(self):
        """Setup configured feeds"""
        feed_configs = self.config.get("market_data.feeds", {})
        
        for feed_name, feed_config in feed_configs.items():
            if not feed_config.get("enabled", False):
                continue
                
            try:
                if feed_name == "polygon":
                    feed = PolygonFeed(feed_config)
                elif feed_name == "alphavantage":
                    feed = AlphaVantageFeed(feed_config)
                else:
                    self.logger.warning(f"Unknown feed type: {feed_name}")
                    continue
                
                self.feeds[feed_name] = feed
                self.logger.info(f"Configured feed: {feed_name}")
                
            except Exception as e:
                self.logger.error(f"Error setting up feed {feed_name}: {e}")
    
    async def start_all_feeds(self) -> bool:
        """Start all configured feeds"""
        success = True
        
        for name, feed in self.feeds.items():
            try:
                if await feed.connect():
                    self.logger.info(f"Started feed: {name}")
                else:
                    self.logger.error(f"Failed to start feed: {name}")
                    success = False
                    
            except Exception as e:
                self.logger.error(f"Error starting feed {name}: {e}")
                success = False
        
        return success
    
    async def stop_all_feeds(self) -> None:
        """Stop all feeds"""
        for name, feed in self.feeds.items():
            try:
                await feed.disconnect()
                self.logger.info(f"Stopped feed: {name}")
                
            except Exception as e:
                self.logger.error(f"Error stopping feed {name}: {e}")
    
    async def subscribe_symbols(self, symbols: List[str]) -> bool:
        """Subscribe to symbols across all feeds"""
        success = True
        
        for name, feed in self.feeds.items():
            try:
                if feed.status == FeedStatus.CONNECTED:
                    if not await feed.subscribe(symbols):
                        success = False
                        
            except Exception as e:
                self.logger.error(f"Error subscribing to {symbols} on {name}: {e}")
                success = False
        
        return success
    
    def add_data_callback(self, callback: Callable[[MarketTick], None]) -> None:
        """Add data callback to all feeds"""
        for feed in self.feeds.values():
            feed.add_callback(callback)
    
    def get_feed_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all feeds"""
        status = {}
        
        for name, feed in self.feeds.items():
            metrics = feed.get_metrics()
            status[name] = {
                "status": feed.status.value,
                "metrics": asdict(metrics),
                "subscribed_symbols": getattr(feed, 'subscribed_symbols', set())
            }
        
        return status
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all feeds"""
        health = {}
        
        for name, feed in self.feeds.items():
            try:
                # Basic health check
                last_msg_time = feed.get_metrics().last_message_time
                is_healthy = (
                    feed.status == FeedStatus.CONNECTED and
                    last_msg_time is not None and
                    (datetime.now() - last_msg_time).total_seconds() < 60
                )
                health[name] = is_healthy
                
            except Exception as e:
                self.logger.error(f"Health check error for {name}: {e}")
                health[name] = False
        
        return health 