"""
Data Engine - Market Data Handler
Advanced market data processing with real-time feeds, historical data, and multi-source aggregation
"""

import logging
import threading
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
from abc import ABC, abstractmethod

# Import ISystemComponent for orchestrator integration (Rule 1)
try:
    from ...system.interfaces import ISystemComponent
except ImportError:
    # Fallback for testing
    from abc import abstractmethod as abs_abstractmethod
    class ISystemComponent(ABC):
        @abs_abstractmethod
        async def initialize(self) -> bool: pass
        @abs_abstractmethod
        async def start(self) -> bool: pass
        @abs_abstractmethod
        async def stop(self) -> bool: pass
        @abs_abstractmethod
        async def health_check(self) -> Dict[str, Any]: pass
        @abs_abstractmethod
        def get_status(self) -> Dict[str, Any]: pass

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Market data source types"""
    EXCHANGE = "exchange"
    VENDOR = "vendor"
    BROKER = "broker"
    INTERNAL = "internal"
    ALTERNATIVE = "alternative"
    SYNTHETIC = "synthetic"


class DataType(Enum):
    """Market data types"""
    QUOTE = "quote"
    TRADE = "trade"
    DEPTH = "depth"
    OHLCV = "ohlcv"
    STATISTICS = "statistics"
    NEWS = "news"
    FUNDAMENTAL = "fundamental"
    TECHNICAL = "technical"


class DataQuality(Enum):
    """Data quality levels"""
    REAL_TIME = "real_time"
    DELAYED = "delayed"
    SNAPSHOT = "snapshot"
    HISTORICAL = "historical"
    ESTIMATED = "estimated"
    DERIVED = "derived"


@dataclass
class MarketDataPoint:
    """Individual market data point"""
    symbol: str
    data_type: DataType
    source: DataSource
    quality: DataQuality
    
    # Price data
    price: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    
    # Volume data
    volume: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    
    # OHLCV data
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    
    # Depth data
    bids: Optional[List[Tuple[float, float]]] = None
    asks: Optional[List[Tuple[float, float]]] = None
    
    # Metadata
    exchange: Optional[str] = None
    sequence_number: Optional[int] = None
    latency_ms: Optional[float] = None
    
    timestamp: datetime = field(default_factory=datetime.now)
    received_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DataSubscription:
    """Data subscription configuration"""
    subscription_id: str
    symbols: List[str]
    data_types: List[DataType]
    sources: List[DataSource]
    
    # Subscription parameters
    frequency_ms: int
    depth_levels: int
    include_trades: bool
    include_quotes: bool
    
    # Quality requirements
    max_latency_ms: float
    min_quality: DataQuality
    
    # Callbacks
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    
    # State
    is_active: bool = False
    last_update: Optional[datetime] = None
    received_count: int = 0
    error_count: int = 0


@dataclass
class DataFeed:
    """Data feed configuration and state"""
    feed_id: str
    name: str
    source: DataSource
    provider: str
    
    # Connection details
    endpoint_url: str
    api_key: Optional[str]
    connection_type: str  # websocket, rest, fix, etc.
    
    # Feed characteristics
    supported_symbols: List[str]
    supported_data_types: List[DataType]
    typical_latency_ms: float
    update_frequency_ms: int
    
    # Quality metrics
    reliability_score: float
    accuracy_score: float
    completeness_score: float
    
    # State
    is_connected: bool = False
    connection_time: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    messages_received: int = 0
    errors_count: int = 0
    
    # Performance tracking
    average_latency_ms: float = 0.0
    peak_latency_ms: float = 0.0
    message_rate_per_second: float = 0.0


class DataFeedAdapter(ABC):
    """Abstract base class for data feed adapters"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to data feed"""
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from data feed"""
    
    @abstractmethod
    async def subscribe(self, symbols: List[str], data_types: List[DataType]) -> bool:
        """Subscribe to data"""
    
    @abstractmethod
    async def unsubscribe(self, symbols: List[str], data_types: List[DataType]) -> bool:
        """Unsubscribe from data"""
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check connection status"""


@dataclass
class MarketDataRequest:
    """Market data request"""
    symbols: List[str]
    fields: List[str]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketDataResponse:
    """Market data response"""
    success: bool
    data: Any
    error_message: Optional[str] = None


class SimulatedDataFeed(DataFeedAdapter):
    """Simulated data feed for testing"""
    
    def __init__(self, feed_config: DataFeed):
        self.config = feed_config
        self._connected = False
        self._subscriptions = set()
        self._simulation_task = None
        self._data_callback = None
    
    async def connect(self) -> bool:
        """Connect to simulated feed"""
        self._connected = True
        self.config.is_connected = True
        self.config.connection_time = datetime.now()
        
        # Start simulation
        self._simulation_task = asyncio.create_task(self._simulate_data())
        
        logger.info(f"Connected to simulated feed: {self.config.name}")
        return True
    
    async def disconnect(self) -> None:
        """Disconnect from simulated feed"""
        self._connected = False
        self.config.is_connected = False
        
        if self._simulation_task:
            self._simulation_task.cancel()
        
        logger.info(f"Disconnected from simulated feed: {self.config.name}")
    
    async def subscribe(self, symbols: List[str], data_types: List[DataType]) -> bool:
        """Subscribe to simulated data"""
        for symbol in symbols:
            for data_type in data_types:
                self._subscriptions.add((symbol, data_type))
        
        logger.info(f"Subscribed to {len(symbols)} symbols, {len(data_types)} data types")
        return True
    
    async def unsubscribe(self, symbols: List[str], data_types: List[DataType]) -> bool:
        """Unsubscribe from simulated data"""
        for symbol in symbols:
            for data_type in data_types:
                self._subscriptions.discard((symbol, data_type))
        
        return True
    
    def is_connected(self) -> bool:
        """Check connection status"""
        return self._connected
    
    def set_data_callback(self, callback: Callable) -> None:
        """Set data callback"""
        self._data_callback = callback
    
    async def _simulate_data(self) -> None:
        """Simulate market data"""
        while self._connected:
            try:
                await asyncio.sleep(0.1)  # 100ms updates
                
                # Generate data for subscribed symbols
                for symbol, data_type in self._subscriptions:
                    data_point = self._generate_market_data(symbol, data_type)
                    
                    if self._data_callback:
                        await self._data_callback(data_point)
                    
                    self.config.messages_received += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in data simulation: {e}")
                self.config.errors_count += 1
                await asyncio.sleep(1)
    
    def _generate_market_data(self, symbol: str, data_type: DataType) -> MarketDataPoint:
        """Generate simulated market data"""
        
        # Base price simulation
        base_price = 100.0
        price_change = np.random.normal(0, 0.01)
        current_price = base_price * (1 + price_change)
        
        # Generate spread
        spread_bps = np.random.uniform(2, 10)
        spread = current_price * spread_bps / 10000
        
        bid_price = current_price - spread / 2
        ask_price = current_price + spread / 2
        
        # Generate sizes
        bid_size = np.random.uniform(100, 5000)
        ask_size = np.random.uniform(100, 5000)
        volume = np.random.uniform(1, 1000)
        
        if data_type == DataType.QUOTE:
            return MarketDataPoint(
                symbol=symbol,
                data_type=data_type,
                source=self.config.source,
                quality=DataQuality.REAL_TIME,
                price=current_price,
                bid_price=bid_price,
                ask_price=ask_price,
                bid_size=bid_size,
                ask_size=ask_size,
                exchange=self.config.provider,
                latency_ms=np.random.uniform(1, 5)
            )
        
        elif data_type == DataType.TRADE:
            return MarketDataPoint(
                symbol=symbol,
                data_type=data_type,
                source=self.config.source,
                quality=DataQuality.REAL_TIME,
                price=current_price,
                volume=volume,
                exchange=self.config.provider,
                latency_ms=np.random.uniform(1, 3)
            )
        
        elif data_type == DataType.DEPTH:
            # Generate order book
            bids = []
            asks = []
            
            for i in range(5):
                bid_level = bid_price - i * 0.01
                ask_level = ask_price + i * 0.01
                bid_qty = np.random.uniform(100, 2000)
                ask_qty = np.random.uniform(100, 2000)
                
                bids.append((bid_level, bid_qty))
                asks.append((ask_level, ask_qty))
            
            return MarketDataPoint(
                symbol=symbol,
                data_type=data_type,
                source=self.config.source,
                quality=DataQuality.REAL_TIME,
                bid_price=bid_price,
                ask_price=ask_price,
                bids=bids,
                asks=asks,
                exchange=self.config.provider,
                latency_ms=np.random.uniform(2, 8)
            )
        
        else:
            # Default to quote
            return MarketDataPoint(
                symbol=symbol,
                data_type=DataType.QUOTE,
                source=self.config.source,
                quality=DataQuality.REAL_TIME,
                price=current_price,
                bid_price=bid_price,
                ask_price=ask_price,
                exchange=self.config.provider
            )


class MarketDataHandler(ISystemComponent):
    """
    Advanced market data handler with multi-source aggregation
    
    Manages real-time and historical market data from multiple sources
    with quality monitoring, latency tracking, and intelligent routing.
    
    Implements ISystemComponent for orchestrator integration (Rule 1).
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize market data handler"""
        self.config = config or {}
        self._lock = threading.Lock()
        
        # ISystemComponent state (Rule 1)
        self.is_initialized = False
        self.is_operational = False
        self.component_id: Optional[str] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Data feeds and adapters
        self._data_feeds = {}
        self._feed_adapters = {}
        self._active_subscriptions = {}
        
        # Data storage
        self._real_time_data = defaultdict(lambda: defaultdict(deque))
        self._latest_data = {}
        self._historical_data = defaultdict(lambda: defaultdict(list))
        
        # Quality monitoring
        self._quality_metrics = defaultdict(dict)
        self._latency_tracking = defaultdict(deque)
        self._error_tracking = defaultdict(int)
        
        # Performance tracking
        self._performance_stats = {
            'total_messages_received': 0,
            'average_latency_ms': 0.0,
            'peak_latency_ms': 0.0,
            'messages_per_second': 0.0,
            'active_subscriptions': 0,
            'connected_feeds': 0,
            'data_quality_score': 0.0
        }
        
        # Configuration
        self.max_real_time_buffer = self.config.get('max_real_time_buffer', 1000)
        self.quality_threshold = self.config.get('quality_threshold', 0.95)
        self.latency_threshold_ms = self.config.get('latency_threshold_ms', 10.0)
        
        # Note: Background tasks will be started in initialize() method (ISystemComponent lifecycle)
        self.logger.info("✅ MarketDataHandler created (call initialize() and start() for full activation)")
    
    async def _initialize_default_feeds(self) -> None:
        """Initialize default data feeds"""
        
        # Primary exchange feed
        exchange_feed = DataFeed(
            feed_id="NYSE_REAL_TIME",
            name="NYSE Real-Time Feed",
            source=DataSource.EXCHANGE,
            provider="NYSE",
            endpoint_url="wss://api.nyse.com/v1/data",
            connection_type="websocket",
            supported_symbols=["*"],
            supported_data_types=[DataType.QUOTE, DataType.TRADE, DataType.DEPTH],
            typical_latency_ms=2.5,
            update_frequency_ms=100,
            reliability_score=0.99,
            accuracy_score=0.995,
            completeness_score=0.98
        )
        
        # Vendor feed
        vendor_feed = DataFeed(
            feed_id="BLOOMBERG_FEED",
            name="Bloomberg Market Data",
            source=DataSource.VENDOR,
            provider="Bloomberg",
            endpoint_url="tcp://api.bloomberg.com:8194",
            connection_type="tcp",
            supported_symbols=["*"],
            supported_data_types=[DataType.QUOTE, DataType.TRADE, DataType.OHLCV, DataType.STATISTICS],
            typical_latency_ms=5.0,
            update_frequency_ms=500,
            reliability_score=0.98,
            accuracy_score=0.99,
            completeness_score=0.99
        )
        
        # Alternative data feed
        alt_feed = DataFeed(
            feed_id="QUANDL_FUNDAMENTAL",
            name="Quandl Fundamental Data",
            source=DataSource.ALTERNATIVE,
            provider="Quandl",
            endpoint_url="https://api.quandl.com/v3",
            connection_type="rest",
            supported_symbols=["*"],
            supported_data_types=[DataType.FUNDAMENTAL, DataType.STATISTICS],
            typical_latency_ms=100.0,
            update_frequency_ms=60000,
            reliability_score=0.95,
            accuracy_score=0.97,
            completeness_score=0.92
        )
        
        # Register feeds
        await self.register_data_feed(exchange_feed)
        await self.register_data_feed(vendor_feed)
        await self.register_data_feed(alt_feed)
    
    async def register_data_feed(self, feed_config: DataFeed) -> None:
        """Register a new data feed"""
        
        with self._lock:
            self._data_feeds[feed_config.feed_id] = feed_config
        
        # Create appropriate adapter
        if feed_config.provider in ["NYSE", "NASDAQ"]:
            adapter = SimulatedDataFeed(feed_config)
        else:
            adapter = SimulatedDataFeed(feed_config)  # Use simulation for all feeds in this example
        
        # Set data callback
        adapter.set_data_callback(self._handle_market_data)
        
        self._feed_adapters[feed_config.feed_id] = adapter
        
        logger.info(f"Registered data feed: {feed_config.name}")
    
    async def connect_feed(self, feed_id: str) -> bool:
        """Connect to a specific data feed"""
        
        adapter = self._feed_adapters.get(feed_id)
        if not adapter:
            raise ValueError(f"Data feed {feed_id} not found")
        
        try:
            success = await adapter.connect()
            
            if success:
                with self._lock:
                    self._performance_stats['connected_feeds'] += 1
                
                logger.info(f"Connected to feed: {feed_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error connecting to feed {feed_id}: {e}")
            return False
    
    async def disconnect_feed(self, feed_id: str) -> None:
        """Disconnect from a specific data feed"""
        
        adapter = self._feed_adapters.get(feed_id)
        if adapter:
            await adapter.disconnect()
            
            with self._lock:
                if self._data_feeds[feed_id].is_connected:
                    self._performance_stats['connected_feeds'] -= 1
            
            logger.info(f"Disconnected from feed: {feed_id}")
    
    async def subscribe_to_data(
        self,
        symbols: List[str],
        data_types: List[DataType],
        callback: Optional[Callable] = None,
        sources: Optional[List[DataSource]] = None,
        quality_requirements: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Subscribe to market data
        
        Args:
            symbols: List of symbols to subscribe to
            data_types: List of data types to receive
            callback: Optional callback for data updates
            sources: Preferred data sources
            quality_requirements: Quality requirements
            
        Returns:
            Subscription ID
        """
        
        subscription_id = f"sub_{int(time.time() * 1000)}"
        
        # Create subscription
        subscription = DataSubscription(
            subscription_id=subscription_id,
            symbols=symbols,
            data_types=data_types,
            sources=sources or [DataSource.EXCHANGE, DataSource.VENDOR],
            frequency_ms=100,
            depth_levels=5,
            include_trades=DataType.TRADE in data_types,
            include_quotes=DataType.QUOTE in data_types,
            max_latency_ms=quality_requirements.get('max_latency_ms', 10.0) if quality_requirements else 10.0,
            min_quality=DataQuality(quality_requirements.get('min_quality', 'real_time')) if quality_requirements else DataQuality.REAL_TIME,
            callback=callback
        )
        
        # Store subscription
        with self._lock:
            self._active_subscriptions[subscription_id] = subscription
            self._performance_stats['active_subscriptions'] += 1
        
        # Subscribe to relevant feeds
        await self._route_subscription(subscription)
        
        subscription.is_active = True
        subscription.last_update = datetime.now()
        
        logger.info(f"Created subscription {subscription_id} for {len(symbols)} symbols")
        
        return subscription_id
    
    async def _route_subscription(self, subscription: DataSubscription) -> None:
        """Route subscription to appropriate data feeds"""
        
        # Find best feeds for this subscription
        suitable_feeds = []
        
        for feed_id, feed_config in self._data_feeds.items():
            # Check if feed supports required data types
            if not all(dt in feed_config.supported_data_types for dt in subscription.data_types):
                continue
            
            # Check if feed supports required sources
            if subscription.sources and feed_config.source not in subscription.sources:
                continue
            
            # Check quality requirements
            if feed_config.typical_latency_ms > subscription.max_latency_ms:
                continue
            
            suitable_feeds.append((feed_id, feed_config))
        
        # Sort by quality score
        suitable_feeds.sort(key=lambda x: x[1].reliability_score, reverse=True)
        
        # Subscribe to top feeds
        for feed_id, feed_config in suitable_feeds[:3]:  # Use top 3 feeds
            adapter = self._feed_adapters.get(feed_id)
            if adapter and adapter.is_connected():
                try:
                    await adapter.subscribe(subscription.symbols, subscription.data_types)
                    logger.debug(f"Subscribed to feed {feed_id} for subscription {subscription.subscription_id}")
                except Exception as e:
                    logger.warning(f"Failed to subscribe to feed {feed_id}: {e}")
    
    async def _handle_market_data(self, data_point: MarketDataPoint) -> None:
        """Handle incoming market data point"""
        
        try:
            # Update latency tracking
            latency = data_point.latency_ms or 0
            with self._lock:
                self._latency_tracking[data_point.source].append(latency)
                if len(self._latency_tracking[data_point.source]) > 1000:
                    self._latency_tracking[data_point.source].popleft()
                
                # Update performance stats
                self._performance_stats['total_messages_received'] += 1
                
                # Update average latency
                total_latencies = []
                for source_latencies in self._latency_tracking.values():
                    total_latencies.extend(source_latencies)
                
                if total_latencies:
                    self._performance_stats['average_latency_ms'] = np.mean(total_latencies)
                    self._performance_stats['peak_latency_ms'] = max(self._performance_stats['peak_latency_ms'], latency)
            
            # Store real-time data
            key = f"{data_point.symbol}_{data_point.data_type.value}"
            
            with self._lock:
                # Add to real-time buffer
                rt_buffer = self._real_time_data[data_point.symbol][data_point.data_type]
                rt_buffer.append(data_point)
                if len(rt_buffer) > self.max_real_time_buffer:
                    rt_buffer.popleft()
                
                # Update latest data
                self._latest_data[key] = data_point
            
            # Quality assessment
            await self._assess_data_quality(data_point)
            
            # Route to subscriptions
            await self._route_to_subscriptions(data_point)
            
        except Exception as e:
            logger.error(f"Error handling market data: {e}")
            with self._lock:
                self._error_tracking[data_point.source] += 1
    
    async def _assess_data_quality(self, data_point: MarketDataPoint) -> None:
        """Assess data quality for incoming data"""
        
        quality_score = 1.0
        
        # Latency check
        if data_point.latency_ms and data_point.latency_ms > self.latency_threshold_ms:
            quality_score *= 0.8
        
        # Staleness check
        age_seconds = (datetime.now() - data_point.timestamp).total_seconds()
        if age_seconds > 1.0:  # Data older than 1 second
            quality_score *= max(0.5, 1.0 - age_seconds / 10.0)
        
        # Price reasonableness check
        if data_point.price and data_point.price <= 0:
            quality_score = 0.0
        
        # Spread reasonableness check
        if data_point.bid_price and data_point.ask_price:
            if data_point.bid_price >= data_point.ask_price:
                quality_score *= 0.3
            
            spread_pct = ((data_point.ask_price - data_point.bid_price) / 
                         data_point.bid_price) * 100
            if spread_pct > 5.0:  # Spread > 5%
                quality_score *= 0.7
        
        # Store quality metrics
        symbol_source_key = f"{data_point.symbol}_{data_point.source.value}"
        with self._lock:
            if symbol_source_key not in self._quality_metrics:
                self._quality_metrics[symbol_source_key] = {
                    'scores': deque(maxlen=100),
                    'average_score': 0.0,
                    'total_points': 0
                }
            
            metrics = self._quality_metrics[symbol_source_key]
            metrics['scores'].append(quality_score)
            metrics['total_points'] += 1
            metrics['average_score'] = np.mean(metrics['scores'])
    
    async def _route_to_subscriptions(self, data_point: MarketDataPoint) -> None:
        """Route data point to relevant subscriptions"""
        
        relevant_subscriptions = []
        
        with self._lock:
            for subscription in self._active_subscriptions.values():
                if (data_point.symbol in subscription.symbols and
                    data_point.data_type in subscription.data_types and
                    subscription.is_active):
                    relevant_subscriptions.append(subscription)
        
        # Call subscription callbacks
        for subscription in relevant_subscriptions:
            if subscription.callback:
                try:
                    await subscription.callback(data_point)
                    subscription.received_count += 1
                    subscription.last_update = datetime.now()
                except Exception as e:
                    logger.warning(f"Subscription callback error: {e}")
                    subscription.error_count += 1
                    
                    if subscription.error_callback:
                        try:
                            await subscription.error_callback(e)
                        except:
                            pass
    
    async def get_latest_data(
        self,
        symbol: str,
        data_type: DataType,
        source: Optional[DataSource] = None
    ) -> Optional[MarketDataPoint]:
        """Get latest data point for symbol and type"""
        
        key = f"{symbol}_{data_type.value}"
        
        with self._lock:
            data_point = self._latest_data.get(key)
        
        if data_point and source and data_point.source != source:
            return None
        
        return data_point
    
    async def get_historical_data(
        self,
        symbol: str,
        data_type: DataType,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        source: Optional[DataSource] = None
    ) -> List[MarketDataPoint]:
        """Get historical data for symbol and type"""
        
        end_time = end_time or datetime.now()
        historical_data = []
        
        with self._lock:
            # Get from real-time buffer
            rt_buffer = self._real_time_data[symbol][data_type]
            for data_point in rt_buffer:
                if (start_time <= data_point.timestamp <= end_time and
                    (not source or data_point.source == source)):
                    historical_data.append(data_point)
            
            # Get from historical storage
            hist_data = self._historical_data[symbol][data_type]
            for data_point in hist_data:
                if (start_time <= data_point.timestamp <= end_time and
                    (not source or data_point.source == source)):
                    historical_data.append(data_point)
        
        # Sort by timestamp
        historical_data.sort(key=lambda x: x.timestamp)
        
        return historical_data
    
    async def get_order_book(
        self,
        symbol: str,
        depth: int = 5,
        source: Optional[DataSource] = None
    ) -> Optional[Dict[str, Any]]:
        """Get current order book for symbol"""
        
        depth_data = await self.get_latest_data(symbol, DataType.DEPTH, source)
        
        if not depth_data or not depth_data.bids or not depth_data.asks:
            return None
        
        return {
            'symbol': symbol,
            'bids': depth_data.bids[:depth],
            'asks': depth_data.asks[:depth],
            'timestamp': depth_data.timestamp,
            'source': depth_data.source.value
        }
    
    def get_data_quality_report(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get data quality report"""
        
        with self._lock:
            if symbol:
                # Symbol-specific report
                symbol_metrics = {}
                for key, metrics in self._quality_metrics.items():
                    if key.startswith(f"{symbol}_"):
                        source = key.split('_', 1)[1]
                        symbol_metrics[source] = {
                            'average_score': metrics['average_score'],
                            'total_points': metrics['total_points'],
                            'recent_scores': list(metrics['scores'])[-10:]
                        }
                
                return {
                    'symbol': symbol,
                    'sources': symbol_metrics,
                    'overall_score': np.mean([m['average_score'] for m in symbol_metrics.values()]) if symbol_metrics else 0.0
                }
            else:
                # Overall report
                all_scores = []
                source_scores = defaultdict(list)
                
                for key, metrics in self._quality_metrics.items():
                    source = key.split('_', 1)[1]
                    all_scores.append(metrics['average_score'])
                    source_scores[source].append(metrics['average_score'])
                
                return {
                    'overall_quality_score': np.mean(all_scores) if all_scores else 0.0,
                    'source_quality': {
                        source: np.mean(scores) for source, scores in source_scores.items()
                    },
                    'total_data_points': sum(m['total_points'] for m in self._quality_metrics.values()),
                    'performance_stats': self._performance_stats.copy()
                }
    
    def get_subscription_status(self, subscription_id: Optional[str] = None) -> Dict[str, Any]:
        """Get subscription status"""
        
        with self._lock:
            if subscription_id:
                subscription = self._active_subscriptions.get(subscription_id)
                if subscription:
                    return {
                        'subscription_id': subscription.subscription_id,
                        'symbols': subscription.symbols,
                        'data_types': [dt.value for dt in subscription.data_types],
                        'is_active': subscription.is_active,
                        'received_count': subscription.received_count,
                        'error_count': subscription.error_count,
                        'last_update': subscription.last_update.isoformat() if subscription.last_update else None
                    }
                else:
                    return {'error': 'Subscription not found'}
            else:
                return {
                    'total_subscriptions': len(self._active_subscriptions),
                    'active_subscriptions': sum(1 for s in self._active_subscriptions.values() if s.is_active),
                    'subscriptions': [
                        {
                            'subscription_id': sub.subscription_id,
                            'symbols_count': len(sub.symbols),
                            'data_types_count': len(sub.data_types),
                            'is_active': sub.is_active,
                            'received_count': sub.received_count,
                            'error_count': sub.error_count
                        }
                        for sub in self._active_subscriptions.values()
                    ]
                }
    
    async def _start_monitoring(self) -> None:
        """Start monitoring background tasks"""
        asyncio.create_task(self._monitor_performance())
        asyncio.create_task(self._monitor_feed_health())
        asyncio.create_task(self._cleanup_old_data())
        
        logger.info("Started market data monitoring")
    
    async def _monitor_performance(self) -> None:
        """Monitor performance metrics"""
        while True:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                with self._lock:
                    # Calculate messages per second
                    current_time = time.time()
                    if hasattr(self, '_last_perf_check'):
                        time_diff = current_time - self._last_perf_check
                        msg_diff = self._performance_stats['total_messages_received'] - getattr(self, '_last_msg_count', 0)
                        self._performance_stats['messages_per_second'] = msg_diff / time_diff if time_diff > 0 else 0
                    
                    self._last_perf_check = current_time
                    self._last_msg_count = self._performance_stats['total_messages_received']
                    
                    # Calculate data quality score
                    all_scores = [m['average_score'] for m in self._quality_metrics.values()]
                    self._performance_stats['data_quality_score'] = np.mean(all_scores) if all_scores else 0.0
                
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_feed_health(self) -> None:
        """Monitor data feed health"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                for feed_id, feed_config in self._data_feeds.items():
                    if feed_config.is_connected:
                        # Check heartbeat
                        if feed_config.last_heartbeat:
                            time_since_heartbeat = datetime.now() - feed_config.last_heartbeat
                            if time_since_heartbeat > timedelta(seconds=60):
                                logger.warning(f"Feed {feed_id} heartbeat timeout")
                        
                        # Check error rate
                        if feed_config.errors_count > 10:
                            logger.warning(f"High error count for feed {feed_id}: {feed_config.errors_count}")
                
            except Exception as e:
                logger.error(f"Error in feed health monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _cleanup_old_data(self) -> None:
        """Cleanup old data to manage memory"""
        while True:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                with self._lock:
                    # Cleanup historical data
                    for symbol_data in self._historical_data.values():
                        for data_type_list in symbol_data.values():
                            data_type_list[:] = [
                                dp for dp in data_type_list
                                if dp.timestamp >= cutoff_time
                            ]
                
                logger.info("Completed data cleanup")
                
            except Exception as e:
                logger.error(f"Error in data cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from data"""
        
        with self._lock:
            subscription = self._active_subscriptions.pop(subscription_id, None)
            
            if subscription:
                subscription.is_active = False
                self._performance_stats['active_subscriptions'] -= 1
                
                logger.info(f"Unsubscribed: {subscription_id}")
                return True
            
            return False
    
    async def cleanup(self) -> None:
        """Cleanup market data handler resources"""
        
        # Disconnect all feeds
        for feed_id in list(self._feed_adapters.keys()):
            await self.disconnect_feed(feed_id)
        
        # Clear all subscriptions
        with self._lock:
            self._active_subscriptions.clear()
        
        self.logger.info("MarketDataHandler cleanup completed")
    
    # ========================================================================
    # ISystemComponent Lifecycle Methods (Rule 1)
    # ========================================================================
    
    async def initialize(self) -> bool:
        """Initialize market data handler"""
        try:
            self.logger.info("Initializing MarketDataHandler...")
            
            # Initialize default feeds
            await self._initialize_default_feeds()
            
            # Initialize performance monitoring
            await self._start_monitoring()
            
            self.is_initialized = True
            self.logger.info("✅ MarketDataHandler initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ MarketDataHandler initialization failed: {e}")
            return False
    
    async def start(self) -> bool:
        """Start market data handler operations"""
        try:
            if not self.is_initialized:
                self.logger.error("Cannot start - not initialized. Call initialize() first.")
                return False
            
            self.is_operational = True
            self.logger.info("✅ MarketDataHandler started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ MarketDataHandler start failed: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop market data handler operations"""
        try:
            self.logger.info("Stopping MarketDataHandler...")
            
            # Cleanup all resources
            await self.cleanup()
            
            self.is_operational = False
            self.logger.info("✅ MarketDataHandler stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ MarketDataHandler stop failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on market data handler"""
        
        # Calculate health metrics
        with self._lock:
            total_feeds = len(self._feed_adapters)
            total_subs = len(self._active_subscriptions)
            active_subs = sum(1 for s in self._active_subscriptions.values() if s.is_active)
            
            quality_score = self._performance_stats.get('data_quality_score', 0.0)
            msg_rate = self._performance_stats.get('messages_per_second', 0.0)
            total_messages = self._performance_stats.get('total_messages_received', 0)
        
        # Determine health (healthy if no data processed yet OR quality is good)
        is_healthy = (
            self.is_operational and
            self.is_initialized and
            (total_messages == 0 or quality_score >= 0.7) and  # Good quality data OR no data yet
            (total_subs == 0 or active_subs / total_subs >= 0.5)  # At least 50% subs active OR no subs
        )
        
        return {
            'healthy': is_healthy,
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_id': self.component_id,
            'component_type': 'MarketDataHandler',
            'total_feeds': total_feeds,
            'total_subscriptions': total_subs,
            'active_subscriptions': active_subs,
            'data_quality_score': quality_score,
            'messages_per_second': msg_rate
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of market data handler"""
        with self._lock:
            return {
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'component_id': self.component_id,
                'component_type': 'MarketDataHandler',
                'total_feeds': len(self._feed_adapters),
                'total_subscriptions': len(self._active_subscriptions),
                'performance_stats': dict(self._performance_stats)
            }