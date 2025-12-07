#!/usr/bin/env python3
"""
Polygon.io Real-Time WebSocket Feed Adapter
============================================

Production-ready implementation for Polygon.io Stock Starter subscription.
Supports real-time aggregated bars (second/minute) and trades via WebSocket.

Features:
    - WebSocket connection to wss://socket.polygon.io/stocks
    - Automatic authentication and reconnection
    - Support for aggregated bars (A.* for second, AM.* for minute)
    - Trade stream support (T.*)
    - Real-time OHLCV bar construction
    - Latency monitoring and quality metrics
    - Circuit breaker pattern for fault tolerance

Subscription Tiers:
    Stock Starter: Second/Minute aggregates, Trades, Previous day bars
    Stock Developer: + Real-time quotes (NBBO)
    Stock Advanced: + Full Level 2 order book

Usage:
    from core_engine.data.feeds.polygon_realtime import (
        PolygonRealtimeFeedAdapter,
        PolygonFeedConfig,
    )

    config = PolygonFeedConfig(
        api_key="your_polygon_api_key",
        symbols=["AAPL", "TSLA", "NVDA"],
        subscription_tier="starter",  # starter, developer, or advanced
    )

    adapter = PolygonRealtimeFeedAdapter(config)
    await adapter.connect()
    await adapter.subscribe(["AAPL", "TSLA"], ["second_agg", "minute_agg", "trade"])

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

try:
    import websockets
    from websockets.exceptions import (
        ConnectionClosedError,
        ConnectionClosedOK,
    )
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None

# Alternative: aiohttp for WebSocket (better proxy handling)
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

from .adapters import (
    AdapterStatus,
    DataFeedAdapter,
    FeedAdapterConfig,
    FeedMessage,
    FeedProvider,
)

logger = logging.getLogger(__name__)


# ============================================================================
# POLYGON-SPECIFIC ENUMS AND CONFIGURATION
# ============================================================================

class PolygonSubscriptionTier(Enum):
    """Polygon.io subscription tiers"""
    STARTER = "starter"      # Second/Minute aggregates, Trades
    DEVELOPER = "developer"  # + Real-time NBBO quotes
    ADVANCED = "advanced"    # + Level 2 order book


class PolygonMessageType(Enum):
    """Polygon.io WebSocket message types"""
    # Connection/Auth
    STATUS = "status"
    AUTH = "auth"

    # Market Data - Stock Starter tier
    TRADE = "T"              # Real-time trades
    SECOND_AGG = "A"         # Per-second aggregates
    MINUTE_AGG = "AM"        # Per-minute aggregates

    # Market Data - Developer+ tier
    QUOTE = "Q"              # Real-time NBBO quotes

    # Market Data - Advanced tier
    LEVEL2 = "L2"            # Level 2 order book

    # Control
    SUBSCRIPTION = "subscription"


class PolygonCluster(Enum):
    """Polygon.io WebSocket clusters"""
    STOCKS = "stocks"
    STOCKS_DELAYED = "delayed.polygon.io/stocks"  # 15-min delayed data
    OPTIONS = "options"
    FOREX = "forex"
    CRYPTO = "crypto"


@dataclass
class PolygonFeedConfig:
    """
    Polygon.io feed configuration

    Stock Starter subscription includes:
        - Second aggregates (A.*)
        - Minute aggregates (AM.*)
        - Trades (T.*)
        - Previous day aggregates
    """
    # Required
    api_key: str

    # Symbols to subscribe (e.g., ["AAPL", "TSLA"])
    symbols: List[str] = field(default_factory=list)

    # Subscription tier (affects available data types)
    subscription_tier: PolygonSubscriptionTier = PolygonSubscriptionTier.STARTER

    # Cluster (stocks, options, forex, crypto)
    cluster: PolygonCluster = PolygonCluster.STOCKS

    # Data types to subscribe (depends on tier)
    # Stock Starter: ["second_agg", "minute_agg", "trade"]
    # Developer+: adds "quote"
    # Advanced: adds "level2"
    data_types: List[str] = field(default_factory=lambda: ["second_agg", "minute_agg", "trade"])

    # Connection settings
    connect_timeout_seconds: float = 30.0
    reconnect_delay_seconds: float = 5.0
    max_reconnect_attempts: int = 10
    heartbeat_interval_seconds: float = 30.0

    # Rate limiting (Polygon limits vary by subscription)
    max_subscriptions: int = 1000  # Starter default

    # Performance
    buffer_size: int = 10000
    enable_compression: bool = True

    # Name for identification
    name: str = "polygon-realtime"

    def __post_init__(self):
        """Validate configuration based on subscription tier"""
        if not self.api_key:
            raise ValueError("Polygon API key is required")

        # Validate data types for subscription tier
        tier_data_types = {
            PolygonSubscriptionTier.STARTER: {"second_agg", "minute_agg", "trade"},
            PolygonSubscriptionTier.DEVELOPER: {"second_agg", "minute_agg", "trade", "quote"},
            PolygonSubscriptionTier.ADVANCED: {"second_agg", "minute_agg", "trade", "quote", "level2"},
        }

        allowed = tier_data_types.get(self.subscription_tier, set())
        invalid = set(self.data_types) - allowed

        if invalid:
            raise ValueError(
                f"Data types {invalid} not available with {self.subscription_tier.value} tier. "
                f"Available: {allowed}"
            )

    @property
    def ws_url(self) -> str:
        """Get WebSocket URL for the cluster"""
        if self.cluster == PolygonCluster.STOCKS_DELAYED:
            return "wss://delayed.polygon.io/stocks"
        return f"wss://socket.polygon.io/{self.cluster.value}"


@dataclass
class PolygonAggregateBar:
    """Polygon.io aggregated bar data"""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float
    timestamp_start: datetime
    timestamp_end: datetime
    num_trades: int
    bar_type: str  # "second" or "minute"

    # Additional fields
    average_trade_size: Optional[float] = None
    otc: bool = False  # OTC market indicator


@dataclass
class PolygonTrade:
    """Polygon.io trade data"""
    symbol: str
    price: float
    size: int
    timestamp: datetime
    conditions: List[int] = field(default_factory=list)
    exchange: int = 0
    tape: int = 0
    sequence_number: Optional[int] = None


@dataclass
class PolygonQuote:
    """Polygon.io quote data (Developer+ tier)"""
    symbol: str
    bid_price: float
    bid_size: int
    ask_price: float
    ask_size: int
    timestamp: datetime
    bid_exchange: int = 0
    ask_exchange: int = 0
    conditions: List[int] = field(default_factory=list)


# ============================================================================
# POLYGON REAL-TIME FEED ADAPTER
# ============================================================================

class PolygonRealtimeFeedAdapter(DataFeedAdapter):
    """
    Production-ready Polygon.io WebSocket feed adapter.

    Implements real-time streaming for Stock Starter subscription:
        - Per-second aggregates (A.SYMBOL)
        - Per-minute aggregates (AM.SYMBOL)
        - Real-time trades (T.SYMBOL)

    Features:
        - Automatic authentication
        - Graceful reconnection with exponential backoff
        - Message parsing and normalization
        - Latency tracking
        - Circuit breaker for fault tolerance
    """

    IS_IMPLEMENTED = True
    PROVIDER = FeedProvider.POLYGON
    SUPPORTED_DATA_TYPES = ['trade', 'second_agg', 'minute_agg', 'quote']

    # Polygon message type to subscription prefix mapping
    MESSAGE_PREFIXES = {
        'trade': 'T',
        'second_agg': 'A',
        'minute_agg': 'AM',
        'quote': 'Q',
    }

    def __init__(self, config: PolygonFeedConfig):
        """Initialize Polygon.io real-time adapter"""

        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets package required for Polygon real-time feed. "
                "Install with: pip install websockets"
            )

        # Convert to base FeedAdapterConfig for parent
        base_config = FeedAdapterConfig(
            provider=FeedProvider.POLYGON,
            name=config.name,
            api_key=config.api_key,
            ws_url=config.ws_url,
            connect_timeout_seconds=config.connect_timeout_seconds,
            reconnect_delay_seconds=config.reconnect_delay_seconds,
            max_reconnect_attempts=config.max_reconnect_attempts,
            max_subscriptions=config.max_subscriptions,
            buffer_size=config.buffer_size,
            enable_compression=config.enable_compression,
        )

        super().__init__(base_config)

        self.polygon_config = config

        # WebSocket connection (websockets library)
        self._ws = None
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # aiohttp WebSocket (alternative, better proxy handling)
        self._use_aiohttp = False
        self._aiohttp_session = None
        self._aiohttp_ws = None

        # Subscription tracking
        self._active_subscriptions: Dict[str, Set[str]] = {
            'trade': set(),
            'second_agg': set(),
            'minute_agg': set(),
            'quote': set(),
        }

        # Reconnection state
        self._reconnect_count = 0
        self._should_reconnect = True

        # Latest bar cache for aggregation
        self._latest_bars: Dict[str, PolygonAggregateBar] = {}

        # Performance tracking
        self._message_count = 0
        self._last_message_time: Optional[datetime] = None

        self.logger.info(
            f"PolygonRealtimeFeedAdapter initialized for {config.subscription_tier.value} tier"
        )

    async def connect(self) -> bool:
        """Connect to Polygon.io WebSocket and authenticate"""
        import os
        import ssl

        try:
            self._set_status(AdapterStatus.CONNECTING)
            self._should_reconnect = True

            self.logger.info(f"Connecting to {self.polygon_config.ws_url}...")

            # Try aiohttp first (better proxy bypass), then fall back to websockets
            if AIOHTTP_AVAILABLE:
                try:
                    return await self._connect_with_aiohttp()
                except Exception as e:
                    self.logger.warning(f"aiohttp connection failed: {e}, trying websockets...")

            if not WEBSOCKETS_AVAILABLE:
                raise ImportError("Neither aiohttp nor websockets available")

            # Clear any proxy environment variables to avoid SOCKS proxy issues
            proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                         'ALL_PROXY', 'all_proxy', 'socks_proxy', 'SOCKS_PROXY']
            saved_proxy = {k: os.environ.pop(k, None) for k in proxy_vars}

            # Create SSL context for secure connection
            ssl_context = ssl.create_default_context()

            try:
                # Connect with timeout - explicitly no proxy
                self._ws = await asyncio.wait_for(
                    websockets.connect(
                        self.polygon_config.ws_url,
                        ping_interval=self.polygon_config.heartbeat_interval_seconds,
                        ping_timeout=10,
                        close_timeout=5,
                        ssl=ssl_context,
                    ),
                    timeout=self.polygon_config.connect_timeout_seconds
                )
            finally:
                # Restore proxy environment variables
                for k, v in saved_proxy.items():
                    if v is not None:
                        os.environ[k] = v

            self._set_status(AdapterStatus.CONNECTED)
            self._stats['connection_time'] = datetime.now()

            # Authenticate
            if not await self._authenticate():
                await self._ws.close()
                self._set_status(AdapterStatus.ERROR)
                return False

            self._set_status(AdapterStatus.AUTHENTICATED)

            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())

            # Start heartbeat monitoring
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

            self._reconnect_count = 0
            self.logger.info("Successfully connected and authenticated to Polygon.io")

            return True

        except asyncio.TimeoutError:
            self.logger.error("Connection timeout")
            self._handle_error(TimeoutError("Connection timeout"))
            self._set_status(AdapterStatus.ERROR)
            return False

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self._handle_error(e)
            self._set_status(AdapterStatus.ERROR)
            return False

    async def _connect_with_aiohttp(self) -> bool:
        """Connect using aiohttp (better proxy bypass)"""
        import ssl
        import certifi

        # Create SSL context with proper certificate handling
        # Use certifi's certificate bundle if available
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            # Fall back to default context without certificate verification for dev
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            self.logger.warning("SSL certificate verification disabled - not recommended for production")

        # Create connector that explicitly ignores system proxy
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        # Create session with trust_env=False to ignore system proxy settings
        self._aiohttp_session = aiohttp.ClientSession(
            connector=connector,
            trust_env=False,  # Critical: ignore system proxy settings
            timeout=aiohttp.ClientTimeout(total=self.polygon_config.connect_timeout_seconds)
        )

        try:
            # Connect to WebSocket
            self._aiohttp_ws = await self._aiohttp_session.ws_connect(
                self.polygon_config.ws_url,
                heartbeat=self.polygon_config.heartbeat_interval_seconds,
            )
        except Exception as e:
            # Cleanup on failure
            await self._aiohttp_session.close()
            self._aiohttp_session = None
            raise

        self._set_status(AdapterStatus.CONNECTED)
        self._stats['connection_time'] = datetime.now()
        self._use_aiohttp = True

        # Authenticate
        if not await self._authenticate_aiohttp():
            await self._aiohttp_ws.close()
            await self._aiohttp_session.close()
            self._set_status(AdapterStatus.ERROR)
            return False

        self._set_status(AdapterStatus.AUTHENTICATED)

        # Start receive loop
        self._receive_task = asyncio.create_task(self._receive_loop_aiohttp())

        self._reconnect_count = 0
        self.logger.info("Successfully connected via aiohttp to Polygon.io")

        return True

    async def _authenticate_aiohttp(self) -> bool:
        """Authenticate using aiohttp WebSocket"""
        try:
            self._set_status(AdapterStatus.AUTHENTICATING)

            # Wait for connection confirmation
            msg = await asyncio.wait_for(self._aiohttp_ws.receive(), timeout=10)
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if not isinstance(data, list):
                    data = [data]

                for m in data:
                    if m.get('ev') == 'status' and m.get('status') == 'connected':
                        self.logger.debug("Connection confirmed, sending auth...")
                        break

            # Send authentication
            auth_message = {"action": "auth", "params": self.polygon_config.api_key}
            await self._aiohttp_ws.send_str(json.dumps(auth_message))

            # Wait for auth confirmation
            msg = await asyncio.wait_for(self._aiohttp_ws.receive(), timeout=10)
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if not isinstance(data, list):
                    data = [data]

                for m in data:
                    if m.get('ev') == 'status':
                        if m.get('status') == 'auth_success':
                            self.logger.info("Authentication successful")
                            return True
                        elif m.get('status') == 'auth_failed':
                            self.logger.error(f"Auth failed: {m.get('message', 'Unknown')}")
                            return False

            return False

        except Exception as e:
            self.logger.error(f"aiohttp auth error: {e}")
            return False

    async def _receive_loop_aiohttp(self) -> None:
        """Receive loop for aiohttp WebSocket"""
        while self._should_reconnect:
            try:
                msg = await self._aiohttp_ws.receive()

                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._process_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.info("WebSocket closed")
                    if self._should_reconnect:
                        await self._attempt_reconnect()
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {self._aiohttp_ws.exception()}")
                    if self._should_reconnect:
                        await self._attempt_reconnect()
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"aiohttp receive error: {e}")
                self._handle_error(e)
                if self._should_reconnect:
                    await asyncio.sleep(1)

    async def _authenticate(self) -> bool:
        """Authenticate with Polygon.io using API key"""
        try:
            self._set_status(AdapterStatus.AUTHENTICATING)

            # Wait for connection confirmation
            message = await asyncio.wait_for(self._ws.recv(), timeout=10)
            data = json.loads(message)

            if not isinstance(data, list):
                data = [data]

            for msg in data:
                if msg.get('ev') == 'status' and msg.get('status') == 'connected':
                    self.logger.debug("Connection confirmed, sending auth...")
                    break
            else:
                self.logger.warning(f"Unexpected connection message: {data}")

            # Send authentication
            auth_message = {"action": "auth", "params": self.polygon_config.api_key}
            await self._ws.send(json.dumps(auth_message))

            # Wait for auth confirmation
            message = await asyncio.wait_for(self._ws.recv(), timeout=10)
            data = json.loads(message)

            if not isinstance(data, list):
                data = [data]

            for msg in data:
                if msg.get('ev') == 'status':
                    if msg.get('status') == 'auth_success':
                        self.logger.info("Authentication successful")
                        return True
                    elif msg.get('status') == 'auth_failed':
                        self.logger.error(f"Authentication failed: {msg.get('message', 'Unknown error')}")
                        return False

            self.logger.error(f"Unexpected auth response: {data}")
            return False

        except asyncio.TimeoutError:
            self.logger.error("Authentication timeout")
            return False
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Polygon.io WebSocket"""
        self._should_reconnect = False

        # Cancel tasks
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket (handle both implementations)
        if self._use_aiohttp:
            if self._aiohttp_ws:
                try:
                    await self._aiohttp_ws.close()
                except Exception as e:
                    self.logger.warning(f"Error closing aiohttp WebSocket: {e}")
            if self._aiohttp_session:
                try:
                    await self._aiohttp_session.close()
                except Exception as e:
                    self.logger.warning(f"Error closing aiohttp session: {e}")
            self._aiohttp_ws = None
            self._aiohttp_session = None
        else:
            if self._ws:
                try:
                    await self._ws.close()
                except Exception as e:
                    self.logger.warning(f"Error closing WebSocket: {e}")
            self._ws = None

        self._set_status(AdapterStatus.DISCONNECTED)
        self.logger.info("Disconnected from Polygon.io")

    async def subscribe(self, symbols: List[str], data_types: List[str]) -> bool:
        """
        Subscribe to market data for specified symbols.

        Args:
            symbols: List of stock symbols (e.g., ["AAPL", "TSLA"])
            data_types: Data types to subscribe:
                - "trade" (T.SYMBOL) - Real-time trades
                - "second_agg" (A.SYMBOL) - Per-second aggregates
                - "minute_agg" (AM.SYMBOL) - Per-minute aggregates
                - "quote" (Q.SYMBOL) - NBBO quotes (Developer+ tier)

        Returns:
            bool: True if subscription successful
        """
        if not self.is_connected():
            self.logger.error("Cannot subscribe - not connected")
            return False

        try:
            self._set_status(AdapterStatus.SUBSCRIBING)

            # Build subscription channels
            channels = []
            for data_type in data_types:
                prefix = self.MESSAGE_PREFIXES.get(data_type)
                if not prefix:
                    self.logger.warning(f"Unknown data type: {data_type}")
                    continue

                # Check tier compatibility
                if data_type == 'quote' and self.polygon_config.subscription_tier == PolygonSubscriptionTier.STARTER:
                    self.logger.warning(
                        "Quotes (Q.*) require Developer+ tier. Skipping."
                    )
                    continue

                for symbol in symbols:
                    channel = f"{prefix}.{symbol.upper()}"
                    channels.append(channel)
                    self._active_subscriptions[data_type].add(symbol.upper())
                    self._subscriptions.add(symbol.upper())

            if not channels:
                self.logger.warning("No valid channels to subscribe")
                return False

            # Send subscription message
            sub_message = {
                "action": "subscribe",
                "params": ",".join(channels)
            }
            await self._send_message(json.dumps(sub_message))

            self._set_status(AdapterStatus.ACTIVE)
            self.logger.info(f"Subscribed to {len(channels)} channels: {channels[:5]}...")

            return True

        except Exception as e:
            self.logger.error(f"Subscription failed: {e}")
            self._handle_error(e)
            return False

    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from market data for specified symbols"""
        if not self.is_connected():
            return True  # Already not receiving

        try:
            # Build unsubscription channels
            channels = []
            for data_type, prefix in self.MESSAGE_PREFIXES.items():
                for symbol in symbols:
                    symbol_upper = symbol.upper()
                    if symbol_upper in self._active_subscriptions[data_type]:
                        channel = f"{prefix}.{symbol_upper}"
                        channels.append(channel)
                        self._active_subscriptions[data_type].discard(symbol_upper)
                        self._subscriptions.discard(symbol_upper)

            if channels:
                unsub_message = {
                    "action": "unsubscribe",
                    "params": ",".join(channels)
                }
                await self._send_message(json.dumps(unsub_message))

                self.logger.info(f"Unsubscribed from {len(channels)} channels")

            return True

        except Exception as e:
            self.logger.error(f"Unsubscription failed: {e}")
            return False

    async def _send_message(self, message: str) -> None:
        """Send message via active WebSocket connection"""
        if self._use_aiohttp and self._aiohttp_ws:
            await self._aiohttp_ws.send_str(message)
        elif self._ws:
            await self._ws.send(message)
        else:
            raise ConnectionError("No active WebSocket connection")

    def is_connected(self) -> bool:
        """Check if WebSocket is connected and authenticated"""
        if self._use_aiohttp:
            return (
                self._aiohttp_ws is not None and
                not self._aiohttp_ws.closed and
                self.status in [AdapterStatus.AUTHENTICATED, AdapterStatus.ACTIVE]
            )
        return (
            self._ws is not None and
            self._ws.open and
            self.status in [AdapterStatus.AUTHENTICATED, AdapterStatus.ACTIVE]
        )

    async def _receive_loop(self) -> None:
        """Main loop to receive and process messages"""
        while self._should_reconnect:
            try:
                if not self._ws or not self._ws.open:
                    break

                message = await self._ws.recv()
                await self._process_message(message)

            except ConnectionClosedOK:
                self.logger.info("WebSocket closed normally")
                break

            except ConnectionClosedError as e:
                self.logger.warning(f"WebSocket closed with error: {e}")
                if self._should_reconnect:
                    await self._attempt_reconnect()
                break

            except asyncio.CancelledError:
                break

            except Exception as e:
                self.logger.error(f"Receive error: {e}")
                self._handle_error(e)
                if self._should_reconnect:
                    await asyncio.sleep(1)

    async def _process_message(self, raw_message: str) -> None:
        """Process incoming WebSocket message"""
        try:
            data = json.loads(raw_message)

            # Handle array of messages
            if not isinstance(data, list):
                data = [data]

            for msg in data:
                event_type = msg.get('ev', msg.get('type', ''))

                # Status messages
                if event_type == 'status':
                    self._handle_status_message(msg)
                    continue

                # Market data messages
                if event_type == 'T':  # Trade
                    await self._handle_trade(msg)
                elif event_type == 'A':  # Second aggregate
                    await self._handle_aggregate(msg, 'second')
                elif event_type == 'AM':  # Minute aggregate
                    await self._handle_aggregate(msg, 'minute')
                elif event_type == 'Q':  # Quote
                    await self._handle_quote(msg)
                else:
                    self.logger.debug(f"Unknown message type: {event_type}")

            self._message_count += 1
            self._last_message_time = datetime.now()

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
        except Exception as e:
            self.logger.error(f"Message processing error: {e}")
            self._handle_error(e)

    def _handle_status_message(self, msg: Dict[str, Any]) -> None:
        """Handle Polygon status messages"""
        status = msg.get('status', '')
        message_text = msg.get('message', '')

        if status == 'connected':
            self.logger.info(f"Polygon status: {message_text}")
        elif status == 'success':
            self.logger.debug(f"Subscription success: {message_text}")
        elif status == 'error':
            self.logger.error(f"Polygon error: {message_text}")
        else:
            self.logger.debug(f"Status message: {msg}")

    async def _handle_trade(self, msg: Dict[str, Any]) -> None:
        """Handle real-time trade message"""
        try:
            trade = PolygonTrade(
                symbol=msg.get('sym', msg.get('T', '')),
                price=float(msg.get('p', 0)),
                size=int(msg.get('s', 0)),
                timestamp=datetime.fromtimestamp(
                    msg.get('t', 0) / 1e9,  # Polygon uses nanoseconds
                    tz=timezone.utc
                ),
                conditions=msg.get('c', []),
                exchange=msg.get('x', 0),
                tape=msg.get('z', 0),
                sequence_number=msg.get('i'),
            )

            # Create standardized feed message
            feed_message = FeedMessage(
                provider=FeedProvider.POLYGON,
                symbol=trade.symbol,
                message_type='trade',
                timestamp=trade.timestamp,
                data={
                    'price': trade.price,
                    'size': trade.size,
                    'conditions': trade.conditions,
                    'exchange': trade.exchange,
                    'tape': trade.tape,
                },
                sequence_number=trade.sequence_number,
                latency_ms=self._calculate_latency(trade.timestamp),
                raw_data=json.dumps(msg).encode('utf-8'),
            )

            self._handle_message(feed_message)

        except Exception as e:
            self.logger.error(f"Trade parsing error: {e}")

    async def _handle_aggregate(self, msg: Dict[str, Any], bar_type: str) -> None:
        """Handle aggregate bar message (second or minute)"""
        try:
            # Parse Polygon aggregate format
            bar = PolygonAggregateBar(
                symbol=msg.get('sym', msg.get('T', '')),
                open=float(msg.get('o', 0)),
                high=float(msg.get('h', 0)),
                low=float(msg.get('l', 0)),
                close=float(msg.get('c', 0)),
                volume=float(msg.get('v', 0)),
                vwap=float(msg.get('vw', 0)) if msg.get('vw') else 0,
                timestamp_start=datetime.fromtimestamp(
                    msg.get('s', 0) / 1000,  # Start time in ms
                    tz=timezone.utc
                ),
                timestamp_end=datetime.fromtimestamp(
                    msg.get('e', 0) / 1000,  # End time in ms
                    tz=timezone.utc
                ),
                num_trades=int(msg.get('n', 0)) if msg.get('n') else 0,
                bar_type=bar_type,
                average_trade_size=float(msg.get('av', 0)) if msg.get('av') else None,
                otc=msg.get('otc', False),
            )

            # Cache latest bar
            cache_key = f"{bar.symbol}_{bar_type}"
            self._latest_bars[cache_key] = bar

            # Create standardized feed message
            message_type = 'second_agg' if bar_type == 'second' else 'minute_agg'

            feed_message = FeedMessage(
                provider=FeedProvider.POLYGON,
                symbol=bar.symbol,
                message_type=message_type,
                timestamp=bar.timestamp_end,
                data={
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume,
                    'vwap': bar.vwap,
                    'num_trades': bar.num_trades,
                    'bar_type': bar_type,
                    'timestamp_start': bar.timestamp_start.isoformat(),
                    'timestamp_end': bar.timestamp_end.isoformat(),
                    'otc': bar.otc,
                },
                latency_ms=self._calculate_latency(bar.timestamp_end),
                raw_data=json.dumps(msg).encode('utf-8'),
            )

            self._handle_message(feed_message)

        except Exception as e:
            self.logger.error(f"Aggregate parsing error: {e}")

    async def _handle_quote(self, msg: Dict[str, Any]) -> None:
        """Handle real-time quote message (Developer+ tier)"""
        try:
            quote = PolygonQuote(
                symbol=msg.get('sym', msg.get('T', '')),
                bid_price=float(msg.get('bp', msg.get('p', 0))),
                bid_size=int(msg.get('bs', msg.get('s', 0))),
                ask_price=float(msg.get('ap', msg.get('P', 0))),
                ask_size=int(msg.get('as', msg.get('S', 0))),
                timestamp=datetime.fromtimestamp(
                    msg.get('t', 0) / 1e9,  # Nanoseconds
                    tz=timezone.utc
                ),
                bid_exchange=msg.get('bx', 0),
                ask_exchange=msg.get('ax', 0),
                conditions=msg.get('c', []),
            )

            # Create standardized feed message
            feed_message = FeedMessage(
                provider=FeedProvider.POLYGON,
                symbol=quote.symbol,
                message_type='quote',
                timestamp=quote.timestamp,
                data={
                    'bid': quote.bid_price,
                    'bid_size': quote.bid_size,
                    'ask': quote.ask_price,
                    'ask_size': quote.ask_size,
                    'bid_exchange': quote.bid_exchange,
                    'ask_exchange': quote.ask_exchange,
                    'conditions': quote.conditions,
                },
                latency_ms=self._calculate_latency(quote.timestamp),
                raw_data=json.dumps(msg).encode('utf-8'),
            )

            self._handle_message(feed_message)

        except Exception as e:
            self.logger.error(f"Quote parsing error: {e}")

    def _calculate_latency(self, data_timestamp: datetime) -> float:
        """Calculate message latency in milliseconds"""
        now = datetime.now(timezone.utc)
        if data_timestamp.tzinfo is None:
            data_timestamp = data_timestamp.replace(tzinfo=timezone.utc)

        latency_seconds = (now - data_timestamp).total_seconds()
        return max(0, latency_seconds * 1000)  # Convert to ms

    async def _heartbeat_monitor(self) -> None:
        """Monitor connection health via heartbeat"""
        last_message_check = self._message_count

        while self._should_reconnect:
            try:
                await asyncio.sleep(self.polygon_config.heartbeat_interval_seconds)

                if not self.is_connected():
                    break

                # Check if we're receiving messages (only if subscribed)
                if self._subscriptions:
                    if self._message_count == last_message_check:
                        self.logger.warning("No messages received in heartbeat interval")
                    last_message_check = self._message_count

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat monitor error: {e}")

    async def _attempt_reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff"""
        if not self._should_reconnect:
            return

        self._set_status(AdapterStatus.RECONNECTING)
        self._stats['reconnects'] += 1
        self._reconnect_count += 1

        if self._reconnect_count > self.polygon_config.max_reconnect_attempts:
            self.logger.error("Max reconnection attempts exceeded")
            self._set_status(AdapterStatus.ERROR)
            return

        # Exponential backoff
        delay = min(
            self.polygon_config.reconnect_delay_seconds * (2 ** (self._reconnect_count - 1)),
            60  # Max 60 seconds
        )

        self.logger.info(f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_count})")
        await asyncio.sleep(delay)

        # Reconnect
        if await self.connect():
            # Resubscribe to all active subscriptions
            all_symbols = set()
            for symbols in self._active_subscriptions.values():
                all_symbols.update(symbols)

            if all_symbols:
                data_types = [dt for dt, syms in self._active_subscriptions.items() if syms]
                await self.subscribe(list(all_symbols), data_types)

    def get_latest_bar(self, symbol: str, bar_type: str = 'minute') -> Optional[PolygonAggregateBar]:
        """Get the latest cached aggregate bar for a symbol"""
        cache_key = f"{symbol.upper()}_{bar_type}"
        return self._latest_bars.get(cache_key)

    def get_statistics(self) -> Dict[str, Any]:
        """Get adapter statistics including Polygon-specific metrics"""
        stats = super().get_statistics()

        # Add Polygon-specific stats
        stats.update({
            'polygon_message_count': self._message_count,
            'last_message_time': self._last_message_time.isoformat() if self._last_message_time else None,
            'reconnect_count': self._reconnect_count,
            'active_subscriptions': {
                k: len(v) for k, v in self._active_subscriptions.items()
            },
            'subscription_tier': self.polygon_config.subscription_tier.value,
            'cached_bars': len(self._latest_bars),
        })

        return stats


# ============================================================================
# AGGREGATED DATA MANAGER
# ============================================================================

class PolygonAggregatedDataManager:
    """
    Manages aggregated OHLCV data from Polygon.io real-time stream.

    Provides:
        - Rolling OHLCV bars from second/minute aggregates
        - Custom timeframe aggregation (5min, 15min, etc.)
        - Volume-weighted average price (VWAP) calculation
        - Integration with the processing pipeline
    """

    def __init__(self, adapter: PolygonRealtimeFeedAdapter):
        self.adapter = adapter
        self.logger = logging.getLogger(self.__class__.__name__)

        # Bar storage: symbol -> timeframe -> list of bars
        self._bars: Dict[str, Dict[str, List[PolygonAggregateBar]]] = {}

        # Custom aggregation periods (in seconds)
        self._aggregation_periods = {
            '1s': 1,
            '5s': 5,
            '10s': 10,
            '30s': 30,
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
        }

        # In-progress bars for custom aggregation
        self._building_bars: Dict[str, Dict[str, Dict[str, Any]]] = {}

        # Callbacks for bar completion
        self._bar_callbacks: List[Callable[[str, str, PolygonAggregateBar], None]] = []

    def add_bar_callback(self, callback: Callable[[str, str, PolygonAggregateBar], None]) -> None:
        """
        Add callback for bar completion.

        Callback signature: (symbol, timeframe, bar) -> None
        """
        self._bar_callbacks.append(callback)

    async def process_aggregate(self, message: FeedMessage) -> None:
        """Process incoming aggregate message"""
        if message.message_type not in ['second_agg', 'minute_agg']:
            return

        symbol = message.symbol
        data = message.data

        # Create bar from message
        bar = PolygonAggregateBar(
            symbol=symbol,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            volume=data['volume'],
            vwap=data.get('vwap', 0),
            timestamp_start=datetime.fromisoformat(data['timestamp_start']),
            timestamp_end=datetime.fromisoformat(data['timestamp_end']),
            num_trades=data.get('num_trades', 0),
            bar_type=data['bar_type'],
        )

        # Store bar
        if symbol not in self._bars:
            self._bars[symbol] = {'second': [], 'minute': []}

        self._bars[symbol][bar.bar_type].append(bar)

        # Limit storage (keep last 1000 bars per timeframe)
        if len(self._bars[symbol][bar.bar_type]) > 1000:
            self._bars[symbol][bar.bar_type] = self._bars[symbol][bar.bar_type][-1000:]

        # Build custom timeframe bars from minute aggregates
        if bar.bar_type == 'minute':
            await self._update_custom_bars(symbol, bar)

    async def _update_custom_bars(self, symbol: str, minute_bar: PolygonAggregateBar) -> None:
        """Update custom timeframe bars from minute aggregates"""
        if symbol not in self._building_bars:
            self._building_bars[symbol] = {}

        for timeframe, period_seconds in self._aggregation_periods.items():
            if period_seconds < 60:  # Skip sub-minute (handled by second aggs)
                continue

            period_minutes = period_seconds // 60

            if timeframe not in self._building_bars[symbol]:
                self._building_bars[symbol][timeframe] = {
                    'bars': [],
                    'start_time': None,
                }

            builder = self._building_bars[symbol][timeframe]

            # Check if we need to start a new bar
            bar_minute = minute_bar.timestamp_start.minute
            if builder['start_time'] is None or bar_minute % period_minutes == 0:
                # Complete previous bar if exists
                if builder['bars']:
                    completed_bar = self._complete_aggregated_bar(builder['bars'], timeframe)
                    if completed_bar:
                        self._notify_bar_completion(symbol, timeframe, completed_bar)

                # Start new bar
                builder['bars'] = [minute_bar]
                builder['start_time'] = minute_bar.timestamp_start
            else:
                builder['bars'].append(minute_bar)

    def _complete_aggregated_bar(
        self,
        minute_bars: List[PolygonAggregateBar],
        timeframe: str
    ) -> Optional[PolygonAggregateBar]:
        """Complete an aggregated bar from minute bars"""
        if not minute_bars:
            return None

        return PolygonAggregateBar(
            symbol=minute_bars[0].symbol,
            open=minute_bars[0].open,
            high=max(b.high for b in minute_bars),
            low=min(b.low for b in minute_bars),
            close=minute_bars[-1].close,
            volume=sum(b.volume for b in minute_bars),
            vwap=sum(b.vwap * b.volume for b in minute_bars) / sum(b.volume for b in minute_bars) if sum(b.volume for b in minute_bars) > 0 else 0,
            timestamp_start=minute_bars[0].timestamp_start,
            timestamp_end=minute_bars[-1].timestamp_end,
            num_trades=sum(b.num_trades for b in minute_bars),
            bar_type=timeframe,
        )

    def _notify_bar_completion(self, symbol: str, timeframe: str, bar: PolygonAggregateBar) -> None:
        """Notify callbacks of bar completion"""
        # Store the completed bar
        if symbol not in self._bars:
            self._bars[symbol] = {}
        if timeframe not in self._bars[symbol]:
            self._bars[symbol][timeframe] = []

        self._bars[symbol][timeframe].append(bar)

        # Limit storage (keep last 1000 bars per timeframe)
        if len(self._bars[symbol][timeframe]) > 1000:
            self._bars[symbol][timeframe] = self._bars[symbol][timeframe][-1000:]

        # Notify callbacks
        for callback in self._bar_callbacks:
            try:
                callback(symbol, timeframe, bar)
            except Exception as e:
                self.logger.error(f"Bar callback error: {e}")

    def get_bars(
        self,
        symbol: str,
        timeframe: str = 'minute',
        limit: int = 100
    ) -> List[PolygonAggregateBar]:
        """Get historical bars for a symbol"""
        if symbol not in self._bars:
            return []

        if timeframe not in self._bars[symbol]:
            return []

        # Return most recent bars first (reverse chronological order)
        return list(reversed(self._bars[symbol][timeframe][-limit:]))

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol"""
        bar = self.adapter.get_latest_bar(symbol, 'second')
        if bar:
            return bar.close

        bar = self.adapter.get_latest_bar(symbol, 'minute')
        if bar:
            return bar.close

        return None


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Configuration
    'PolygonFeedConfig',
    'PolygonSubscriptionTier',
    'PolygonCluster',

    # Data structures
    'PolygonAggregateBar',
    'PolygonTrade',
    'PolygonQuote',

    # Adapters
    'PolygonRealtimeFeedAdapter',
    'PolygonAggregatedDataManager',
]

