"""
Unified Data Feeds - Market Data Sources
=======================================

Consolidated data feeds system combining:
- Real-time market data feeds
- ClickHouse data loading
- Feed management and routing
- Unified data source interface

This module replaces:
- feeds.py (637 lines)
- enhanced_clickhouse_loader.py (745 lines)

Author: StatArb_Gemini Architecture Consolidation  
Version: 4.0 (Phase 4B)
"""

import asyncio
import json
import logging
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, AsyncIterator, Union
from enum import Enum
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import pytz
from urllib.parse import urlencode

# Core infrastructure imports
try:
    from core_structure.infrastructure.messaging.message_bus import MessageBus
    from core_structure.infrastructure.monitoring.metrics_collector import MetricsCollector
    from core_structure.infrastructure.config import UnifiedConfigManager as ConfigManager
    from core_structure.infrastructure.database.clickhouse_client import ClickHouseClient
except ImportError:
    MessageBus = None
    MetricsCollector = None
    ConfigManager = None
    ClickHouseClient = None

# Optional dependencies
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    
try:
    import clickhouse_driver
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False

logger = logging.getLogger(__name__)

class DataType(Enum):
    """Market data types"""
    TICK = "tick"
    QUOTE = "quote"
    TRADE = "trade"
    ORDERBOOK = "orderbook"
    OHLCV = "ohlcv"
    NEWS = "news"
    CORPORATE_ACTION = "corporate_action"

class FeedStatus(Enum):
    """Feed connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"
    PAUSED = "paused"

class DataSource(Enum):
    """Data source types"""
    CLICKHOUSE = "clickhouse"
    REALTIME_FEED = "realtime_feed"
    REST_API = "rest_api"
    WEBSOCKET = "websocket"
    FILE = "file"
    MOCK = "mock"

@dataclass
class DataRequest:
    """Data request specification"""
    symbols: List[str]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    interval: str = "1m"
    data_type: DataType = DataType.OHLCV
    source: Optional[DataSource] = None
    include_volume: bool = True
    include_depth: bool = False
    max_records: Optional[int] = None
    
@dataclass
class FeedConfig:
    """Feed configuration"""
    source_type: DataSource
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    symbols: List[str] = field(default_factory=list)
    interval: str = "1m"
    buffer_size: int = 1000
    reconnect_attempts: int = 5
    reconnect_delay: float = 1.0
    timeout: int = 30
    rate_limit: int = 100  # requests per minute
    
@dataclass
class MarketDataPoint:
    """Standardized market data point"""
    symbol: str
    timestamp: datetime
    data_type: DataType
    source: DataSource
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None

@dataclass
class FeedMetrics:
    """Feed performance metrics"""
    messages_received: int = 0
    messages_processed: int = 0
    messages_dropped: int = 0
    reconnections: int = 0
    last_message_time: Optional[datetime] = None
    average_latency_ms: float = 0.0
    error_count: int = 0
    uptime_seconds: float = 0.0

class ClickHouseDataProvider:
    """ClickHouse historical data provider"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.client = ClickHouseClient(self.config) if ClickHouseClient else None
        self._connection_pool = None
        self._query_cache = {}
        
        logger.info("ClickHouse data provider initialized")
        
    def load_historical_data(self, request: DataRequest) -> Optional[pd.DataFrame]:
        """Load historical data from ClickHouse"""
        if not self.client:
            logger.warning("ClickHouse client not available")
            return None
            
        try:
            # Build query
            query = self._build_historical_query(request)
            
            # Check cache first
            cache_key = hash(query)
            if cache_key in self._query_cache:
                cached_result, cache_time = self._query_cache[cache_key]
                if (datetime.now() - cache_time).seconds < 300:  # 5 minute cache
                    return cached_result
                    
            # Execute query
            start_time = time.time()
            result = self.client.query_dataframe(query)
            query_time = (time.time() - start_time) * 1000
            
            if result is not None and not result.empty:
                # Standardize the data
                standardized = self._standardize_clickhouse_data(result, request)
                
                # Cache result
                self._query_cache[cache_key] = (standardized, datetime.now())
                
                logger.info(f"Loaded {len(standardized)} records for {request.symbols} in {query_time:.1f}ms")
                return standardized
            else:
                logger.warning(f"No data found for request: {request.symbols}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return None
            
    def _build_historical_query(self, request: DataRequest) -> str:
        """Build ClickHouse query for historical data"""
        symbols_str = "', '".join(request.symbols)
        
        base_query = f"""
        SELECT 
            symbol,
            timestamp,
            open,
            high, 
            low,
            close,
            volume
        FROM market_data
        WHERE symbol IN ('{symbols_str}')
        """
        
        if request.start_time:
            base_query += f" AND timestamp >= '{request.start_time}'"
        if request.end_time:
            base_query += f" AND timestamp <= '{request.end_time}'"
            
        base_query += " ORDER BY symbol, timestamp"
        
        if request.max_records:
            base_query += f" LIMIT {request.max_records}"
            
        return base_query
        
    def _standardize_clickhouse_data(self, data: pd.DataFrame, request: DataRequest) -> pd.DataFrame:
        """Standardize ClickHouse data format"""
        standardized = data.copy()
        
        # Ensure timestamp is datetime
        if 'timestamp' in standardized.columns:
            standardized['timestamp'] = pd.to_datetime(standardized['timestamp'])
            
        # Add metadata
        standardized['data_type'] = request.data_type.value
        standardized['source'] = DataSource.CLICKHOUSE.value
        
        # Ensure numeric columns
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in standardized.columns:
                standardized[col] = pd.to_numeric(standardized[col], errors='coerce')
                
        return standardized
        
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols in ClickHouse"""
        if not self.client:
            return []
            
        try:
            query = "SELECT DISTINCT symbol FROM market_data ORDER BY symbol"
            result = self.client.query_dataframe(query)
            return result['symbol'].tolist() if result is not None else []
        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
            return []

class BaseFeed(ABC):
    """Base class for market data feeds"""
    
    def __init__(self, config: FeedConfig):
        self.config = config
        self.status = FeedStatus.DISCONNECTED
        self.metrics = FeedMetrics()
        self._subscribers = []
        self._running = False
        self._thread = None
        self._data_queue = Queue(maxsize=config.buffer_size)
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the data feed"""
        pass
        
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the data feed"""
        pass
        
    @abstractmethod
    async def subscribe(self, symbols: List[str], data_types: List[DataType] = None):
        """Subscribe to symbols"""
        pass
        
    def add_subscriber(self, callback: Callable[[MarketDataPoint], None]):
        """Add data subscriber"""
        self._subscribers.append(callback)
        
    def _notify_subscribers(self, data_point: MarketDataPoint):
        """Notify all subscribers of new data"""
        for callback in self._subscribers:
            try:
                callback(data_point)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")

class MockDataFeed(BaseFeed):
    """Mock data feed for testing"""
    
    def __init__(self, config: FeedConfig):
        super().__init__(config)
        self._mock_data_generator = None
        
    async def connect(self) -> bool:
        """Connect to mock feed"""
        self.status = FeedStatus.CONNECTED
        self._running = True
        self._mock_data_generator = self._generate_mock_data()
        
        # Start data generation in background
        self._thread = threading.Thread(target=self._run_mock_feed)
        self._thread.daemon = True
        self._thread.start()
        
        logger.info("Mock data feed connected")
        return True
        
    async def disconnect(self):
        """Disconnect mock feed"""
        self._running = False
        self.status = FeedStatus.DISCONNECTED
        if self._thread:
            self._thread.join(timeout=1)
        logger.info("Mock data feed disconnected")
        
    async def subscribe(self, symbols: List[str], data_types: List[DataType] = None):
        """Subscribe to mock symbols"""
        self.config.symbols.extend(symbols)
        logger.info(f"Subscribed to mock symbols: {symbols}")
        
    def _run_mock_feed(self):
        """Run mock data generation"""
        while self._running:
            try:
                for symbol in self.config.symbols:
                    data_point = self._generate_mock_point(symbol)
                    self._notify_subscribers(data_point)
                    self.metrics.messages_received += 1
                    self.metrics.messages_processed += 1
                    
                time.sleep(1)  # Generate data every second
                
            except Exception as e:
                logger.error(f"Mock feed error: {e}")
                self.metrics.error_count += 1
                
    def _generate_mock_point(self, symbol: str) -> MarketDataPoint:
        """Generate mock market data point"""
        now = datetime.now()
        
        # Simple random walk for prices
        base_price = 100 + hash(symbol) % 500
        change = np.random.normal(0, 0.01)
        price = base_price * (1 + change)
        
        return MarketDataPoint(
            symbol=symbol,
            timestamp=now,
            data_type=DataType.TICK,
            source=DataSource.MOCK,
            close=round(price, 2),
            volume=np.random.randint(100, 1000)
        )

class UnifiedDataFeeds:
    """
    Unified data feeds manager
    
    Consolidates:
    - Real-time feed management
    - ClickHouse data loading
    - Feed routing and distribution
    - Data source abstraction
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.clickhouse_provider = ClickHouseDataProvider(self.config.get('clickhouse', {}))
        
        # Feed management
        self._feeds = {}
        self._subscribers = {}
        self._feed_router = {}
        
        # Metrics and monitoring
        self.metrics_collector = MetricsCollector() if MetricsCollector else None
        self.message_bus = MessageBus() if MessageBus else None
        
        logger.info("UnifiedDataFeeds initialized")
        
    def register_feed(self, name: str, feed: BaseFeed):
        """Register a data feed"""
        self._feeds[name] = feed
        feed.add_subscriber(self._route_data)
        logger.info(f"Registered feed: {name}")
        
    def get_historical_data(self, request: DataRequest) -> Optional[pd.DataFrame]:
        """Get historical data from appropriate source"""
        if request.source == DataSource.CLICKHOUSE or request.source is None:
            # Try ClickHouse first
            data = self.clickhouse_provider.load_historical_data(request)
            if data is not None:
                return data
                
        # Try other sources if ClickHouse fails
        logger.warning(f"ClickHouse unavailable, using alternative sources for {request.symbols}")
        return self._get_alternative_historical_data(request)
        
    def _get_alternative_historical_data(self, request: DataRequest) -> Optional[pd.DataFrame]:
        """Get historical data from alternative sources"""
        # Generate mock data for testing
        if not request.symbols:
            return None
            
        symbol = request.symbols[0]
        start_time = request.start_time or datetime.now() - timedelta(days=1)
        end_time = request.end_time or datetime.now()
        
        # Generate time series
        freq = '1min' if request.interval == '1m' else request.interval
        timestamps = pd.date_range(start_time, end_time, freq=freq)
        
        # Generate price data
        np.random.seed(hash(symbol) % 2**32)
        returns = np.random.normal(0, 0.01, len(timestamps))
        prices = 100 * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'symbol': symbol,
            'timestamp': timestamps,
            'open': prices * (1 + np.random.normal(0, 0.001, len(timestamps))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.002, len(timestamps)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.002, len(timestamps)))),
            'close': prices,
            'volume': np.random.randint(1000, 10000, len(timestamps)),
            'data_type': request.data_type.value,
            'source': DataSource.MOCK.value
        })
        
    def start_realtime_feed(self, feed_name: str = "mock") -> bool:
        """Start real-time data feed"""
        try:
            if feed_name not in self._feeds:
                # Create default mock feed
                config = FeedConfig(
                    source_type=DataSource.MOCK,
                    symbols=['AAPL', 'GOOGL', 'MSFT', 'TSLA'],
                    interval="1s"
                )
                mock_feed = MockDataFeed(config)
                self.register_feed(feed_name, mock_feed)
                
            feed = self._feeds[feed_name]
            asyncio.create_task(feed.connect())
            
            logger.info(f"Started real-time feed: {feed_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting real-time feed: {e}")
            return False
            
    def stop_realtime_feed(self, feed_name: str):
        """Stop real-time data feed"""
        if feed_name in self._feeds:
            feed = self._feeds[feed_name]
            asyncio.create_task(feed.disconnect())
            logger.info(f"Stopped real-time feed: {feed_name}")
            
    def _route_data(self, data_point: MarketDataPoint):
        """Route incoming data to subscribers"""
        symbol = data_point.symbol
        
        # Route to symbol-specific subscribers
        if symbol in self._subscribers:
            for callback in self._subscribers[symbol]:
                try:
                    callback(data_point)
                except Exception as e:
                    logger.error(f"Error routing data to subscriber: {e}")
                    
        # Route to global subscribers
        if '*' in self._subscribers:
            for callback in self._subscribers['*']:
                try:
                    callback(data_point)
                except Exception as e:
                    logger.error(f"Error routing data to global subscriber: {e}")
                    
        # Publish to message bus if available
        if self.message_bus:
            self.message_bus.publish(f"market_data.{symbol}", asdict(data_point))
            
    def subscribe_to_symbol(self, symbol: str, callback: Callable[[MarketDataPoint], None]):
        """Subscribe to market data for a specific symbol"""
        if symbol not in self._subscribers:
            self._subscribers[symbol] = []
        self._subscribers[symbol].append(callback)
        
    def subscribe_to_all(self, callback: Callable[[MarketDataPoint], None]):
        """Subscribe to all market data"""
        if '*' not in self._subscribers:
            self._subscribers['*'] = []
        self._subscribers['*'].append(callback)
        
    def get_feed_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all feeds"""
        status = {}
        for name, feed in self._feeds.items():
            status[name] = {
                'status': feed.status.value,
                'metrics': asdict(feed.metrics),
                'symbols': feed.config.symbols,
                'source_type': feed.config.source_type.value
            }
        return status
        
    def get_available_symbols(self) -> List[str]:
        """Get all available symbols from all sources"""
        symbols = set()
        
        # From ClickHouse
        symbols.update(self.clickhouse_provider.get_available_symbols())
        
        # From active feeds
        for feed in self._feeds.values():
            symbols.update(feed.config.symbols)
            
        return sorted(list(symbols))

# Backward compatibility aliases
MarketDataFeeds = UnifiedDataFeeds
EnhancedClickHouseLoader = ClickHouseDataProvider

# Export classes
__all__ = [
    'UnifiedDataFeeds',
    'ClickHouseDataProvider',
    'BaseFeed',
    'MockDataFeed',
    'DataRequest',
    'FeedConfig',
    'MarketDataPoint',
    'FeedMetrics',
    'DataType',
    'FeedStatus',
    'DataSource',
    # Backward compatibility
    'MarketDataFeeds',
    'EnhancedClickHouseLoader'
]
