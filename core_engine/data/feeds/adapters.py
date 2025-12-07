#!/usr/bin/env python3
"""
Data Feed Adapters - Production-Ready Feed Implementations

This module provides the adapter infrastructure for connecting to various
data feed providers. Adapters abstract the connection and data handling
details for each provider.

Architecture:
    DataFeedAdapter (ABC) - Base interface for all feed adapters
    ├── SimulatedFeedAdapter - For testing and backtesting
    ├── WebSocketFeedAdapter - Generic WebSocket-based feeds
    ├── RESTFeedAdapter - Generic REST API-based feeds
    └── Provider-specific adapters (to be implemented):
        ├── AlpacaFeedAdapter
        ├── PolygonFeedAdapter
        ├── InteractiveBrokersFeedAdapter
        └── etc.

Usage:
    adapter = FeedAdapterFactory.create('alpaca', config)
    await adapter.connect()
    await adapter.subscribe(['AAPL', 'GOOGL'], [DataType.QUOTE, DataType.TRADE])

Configuration:
    All adapters receive configuration through a standardized FeedConfig dataclass.
    Provider-specific settings go in the `provider_config` dict.

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
import warnings

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONFIGURATION
# ============================================================================

class AdapterStatus(Enum):
    """Adapter connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    SUBSCRIBING = "subscribing"
    ACTIVE = "active"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    CLOSED = "closed"


class FeedProvider(Enum):
    """Supported feed providers

    Note: Not all providers are fully implemented. Check IS_IMPLEMENTED
    flag in the adapter class before use.
    """
    SIMULATED = "simulated"      # ✅ Implemented - for testing
    ALPACA = "alpaca"            # ⚠️  Stub - needs API key
    POLYGON = "polygon"          # ⚠️  Stub - needs API key
    INTERACTIVE_BROKERS = "ib"   # ⚠️  Stub - needs IB Gateway
    BINANCE = "binance"          # ⚠️  Stub - for crypto
    COINBASE = "coinbase"        # ⚠️  Stub - for crypto
    CUSTOM = "custom"            # For custom implementations


@dataclass
class FeedAdapterConfig:
    """Configuration for feed adapters"""
    provider: FeedProvider
    name: str

    # Connection settings
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None
    ws_url: Optional[str] = None

    # Timeouts
    connect_timeout_seconds: float = 30.0
    read_timeout_seconds: float = 10.0
    reconnect_delay_seconds: float = 5.0
    max_reconnect_attempts: int = 5

    # Rate limiting
    max_requests_per_second: float = 10.0
    max_subscriptions: int = 1000

    # Data settings
    buffer_size: int = 10000
    enable_compression: bool = True

    # Provider-specific configuration
    provider_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration"""
        if self.provider not in [FeedProvider.SIMULATED, FeedProvider.CUSTOM]:
            if not self.api_key:
                warnings.warn(
                    f"API key not provided for {self.provider.value} adapter. "
                    "Connection will likely fail.",
                    UserWarning
                )


@dataclass
class FeedMessage:
    """Standardized feed message"""
    provider: FeedProvider
    symbol: str
    message_type: str  # 'quote', 'trade', 'bar', 'status', etc.
    timestamp: datetime
    data: Dict[str, Any]

    # Metadata
    sequence_number: Optional[int] = None
    latency_ms: Optional[float] = None
    raw_data: Optional[bytes] = None


# ============================================================================
# BASE ADAPTER INTERFACE
# ============================================================================

class DataFeedAdapter(ABC):
    """
    Abstract base class for all data feed adapters.

    Subclasses must implement the abstract methods to handle
    provider-specific connection and data handling logic.

    Class Attributes:
        IS_IMPLEMENTED (bool): Whether this adapter has real implementation
        PROVIDER (FeedProvider): The provider this adapter supports
        SUPPORTED_DATA_TYPES (List[str]): Data types this adapter can provide
    """

    # Subclasses should override these
    IS_IMPLEMENTED: bool = False
    PROVIDER: FeedProvider = FeedProvider.CUSTOM
    SUPPORTED_DATA_TYPES: List[str] = ['quote', 'trade']

    def __init__(self, config: FeedAdapterConfig):
        self.config = config
        self.status = AdapterStatus.DISCONNECTED
        self._subscriptions: Set[str] = set()
        self._message_handlers: List[Callable[[FeedMessage], None]] = []
        self._error_handlers: List[Callable[[Exception], None]] = []
        self._status_handlers: List[Callable[[AdapterStatus], None]] = []

        # Statistics
        self._stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'errors': 0,
            'reconnects': 0,
            'last_message_time': None,
            'connection_time': None,
        }

        self.logger = logging.getLogger(f"{self.__class__.__name__}[{config.name}]")

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the data feed.

        Returns:
            bool: True if connection successful, False otherwise
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the data feed."""

    @abstractmethod
    async def subscribe(self, symbols: List[str], data_types: List[str]) -> bool:
        """
        Subscribe to market data for specified symbols.

        Args:
            symbols: List of symbols to subscribe to
            data_types: List of data types ('quote', 'trade', 'bar', etc.)

        Returns:
            bool: True if subscription successful
        """

    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from market data.

        Args:
            symbols: List of symbols to unsubscribe from

        Returns:
            bool: True if unsubscription successful
        """

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if adapter is connected."""

    # ========================================================================
    # Common Methods (can be overridden if needed)
    # ========================================================================

    def add_message_handler(self, handler: Callable[[FeedMessage], None]) -> None:
        """Add a handler for incoming messages."""
        self._message_handlers.append(handler)

    def add_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Add a handler for errors."""
        self._error_handlers.append(handler)

    def add_status_handler(self, handler: Callable[[AdapterStatus], None]) -> None:
        """Add a handler for status changes."""
        self._status_handlers.append(handler)

    def get_subscriptions(self) -> Set[str]:
        """Get current subscriptions."""
        return self._subscriptions.copy()

    def get_statistics(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return self._stats.copy()

    def _set_status(self, status: AdapterStatus) -> None:
        """Update status and notify handlers."""
        old_status = self.status
        self.status = status

        if old_status != status:
            self.logger.info(f"Status: {old_status.value} -> {status.value}")
            for handler in self._status_handlers:
                try:
                    handler(status)
                except Exception as e:
                    self.logger.error(f"Error in status handler: {e}")

    def _handle_message(self, message: FeedMessage) -> None:
        """Process incoming message and notify handlers."""
        self._stats['messages_received'] += 1
        self._stats['last_message_time'] = datetime.now()

        for handler in self._message_handlers:
            try:
                handler(message)
                self._stats['messages_processed'] += 1
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")
                self._stats['errors'] += 1

    def _handle_error(self, error: Exception) -> None:
        """Process error and notify handlers."""
        self._stats['errors'] += 1
        self.logger.error(f"Adapter error: {error}")

        for handler in self._error_handlers:
            try:
                handler(error)
            except Exception as e:
                self.logger.error(f"Error in error handler: {e}")


# ============================================================================
# SIMULATED ADAPTER (FOR TESTING)
# ============================================================================

class SimulatedFeedAdapter(DataFeedAdapter):
    """
    Simulated data feed adapter for testing and backtesting.

    ✅ FULLY IMPLEMENTED - Safe for all environments

    Generates realistic market data with configurable patterns.
    Useful for:
        - Unit testing
        - Integration testing
        - Backtesting (with historical data injection)
        - Development without API keys
    """

    IS_IMPLEMENTED = True
    PROVIDER = FeedProvider.SIMULATED
    SUPPORTED_DATA_TYPES = ['quote', 'trade', 'bar']

    def __init__(self, config: FeedAdapterConfig):
        super().__init__(config)
        self._simulation_task: Optional[asyncio.Task] = None
        self._base_prices: Dict[str, float] = {}
        self._update_interval = config.provider_config.get('update_interval_ms', 100) / 1000.0

    async def connect(self) -> bool:
        """Connect to simulated feed."""
        try:
            self._set_status(AdapterStatus.CONNECTING)

            # Simulate connection delay
            await asyncio.sleep(0.1)

            self._set_status(AdapterStatus.CONNECTED)
            self._stats['connection_time'] = datetime.now()

            self.logger.info("Connected to simulated feed")
            return True

        except Exception as e:
            self._handle_error(e)
            self._set_status(AdapterStatus.ERROR)
            return False

    async def disconnect(self) -> None:
        """Disconnect from simulated feed."""
        if self._simulation_task and not self._simulation_task.done():
            self._simulation_task.cancel()
            try:
                await self._simulation_task
            except asyncio.CancelledError:
                pass

        self._set_status(AdapterStatus.DISCONNECTED)
        self.logger.info("Disconnected from simulated feed")

    async def subscribe(self, symbols: List[str], data_types: List[str]) -> bool:
        """Subscribe to simulated data."""
        try:
            for symbol in symbols:
                self._subscriptions.add(symbol)
                # Initialize base price for new symbols
                if symbol not in self._base_prices:
                    self._base_prices[symbol] = 100.0 + hash(symbol) % 900

            # Start simulation if not running
            if self._simulation_task is None or self._simulation_task.done():
                self._simulation_task = asyncio.create_task(self._simulate_data())

            self._set_status(AdapterStatus.ACTIVE)
            self.logger.info(f"Subscribed to {len(symbols)} symbols")
            return True

        except Exception as e:
            self._handle_error(e)
            return False

    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from simulated data."""
        for symbol in symbols:
            self._subscriptions.discard(symbol)

        # Stop simulation if no subscriptions
        if not self._subscriptions and self._simulation_task:
            self._simulation_task.cancel()

        self.logger.info(f"Unsubscribed from {len(symbols)} symbols")
        return True

    def is_connected(self) -> bool:
        """Check connection status."""
        return self.status in [AdapterStatus.CONNECTED, AdapterStatus.ACTIVE]

    async def _simulate_data(self) -> None:
        """Generate simulated market data."""
        import random

        while self._subscriptions:
            try:
                for symbol in list(self._subscriptions):
                    # Update base price with random walk
                    base_price = self._base_prices.get(symbol, 100.0)
                    change = random.gauss(0, 0.001) * base_price
                    base_price = max(1.0, base_price + change)
                    self._base_prices[symbol] = base_price

                    # Generate spread
                    spread = base_price * random.uniform(0.0001, 0.001)
                    bid = base_price - spread / 2
                    ask = base_price + spread / 2

                    # Create quote message
                    message = FeedMessage(
                        provider=FeedProvider.SIMULATED,
                        symbol=symbol,
                        message_type='quote',
                        timestamp=datetime.now(),
                        data={
                            'bid': round(bid, 2),
                            'ask': round(ask, 2),
                            'bid_size': random.randint(100, 5000),
                            'ask_size': random.randint(100, 5000),
                            'last': round(base_price, 2),
                            'volume': random.randint(1000, 100000),
                        },
                        latency_ms=random.uniform(0.1, 2.0)
                    )

                    self._handle_message(message)

                await asyncio.sleep(self._update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._handle_error(e)
                await asyncio.sleep(1.0)


# ============================================================================
# STUB ADAPTERS (FOR FUTURE IMPLEMENTATION)
# ============================================================================

class AlpacaFeedAdapter(DataFeedAdapter):
    """
    Alpaca Markets data feed adapter.

    ⚠️  STUB IMPLEMENTATION - Returns simulated data

    To implement fully, requires:
        1. Alpaca API key and secret
        2. alpaca-trade-api package
        3. WebSocket connection to Alpaca streams

    Documentation: https://alpaca.markets/docs/api-references/market-data-api/
    """

    IS_IMPLEMENTED = False
    PROVIDER = FeedProvider.ALPACA
    SUPPORTED_DATA_TYPES = ['quote', 'trade', 'bar']

    def __init__(self, config: FeedAdapterConfig):
        super().__init__(config)
        warnings.warn(
            "AlpacaFeedAdapter is a STUB. It returns simulated data. "
            "Implement connect/subscribe methods for production use.",
            UserWarning
        )
        self._simulated = SimulatedFeedAdapter(config)

    async def connect(self) -> bool:
        """Stub: Connect using simulated adapter."""
        self.logger.warning("STUB: Using simulated connection for Alpaca")
        return await self._simulated.connect()

    async def disconnect(self) -> None:
        """Stub: Disconnect simulated adapter."""
        await self._simulated.disconnect()

    async def subscribe(self, symbols: List[str], data_types: List[str]) -> bool:
        """Stub: Subscribe using simulated adapter."""
        self.logger.warning("STUB: Using simulated data for Alpaca subscription")
        return await self._simulated.subscribe(symbols, data_types)

    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Stub: Unsubscribe using simulated adapter."""
        return await self._simulated.unsubscribe(symbols)

    def is_connected(self) -> bool:
        """Check simulated connection."""
        return self._simulated.is_connected()


class PolygonFeedAdapter(DataFeedAdapter):
    """
    Polygon.io data feed adapter.

    ⚠️  BASIC STUB - For full production use, use PolygonRealtimeFeedAdapter.

    This adapter provides a fallback to simulated data when the production
    adapter is not configured. For real Polygon.io integration:

        from core_engine.data.feeds import (
            PolygonRealtimeFeedAdapter,
            PolygonFeedConfig,
        )

        config = PolygonFeedConfig(
            api_key="your_api_key",
            symbols=["AAPL", "TSLA"],
        )
        adapter = PolygonRealtimeFeedAdapter(config)

    Documentation: https://polygon.io/docs/stocks/getting-started
    """

    IS_IMPLEMENTED = False  # Mark as stub; production is PolygonRealtimeFeedAdapter
    PROVIDER = FeedProvider.POLYGON
    SUPPORTED_DATA_TYPES = ['quote', 'trade', 'bar', 'second_agg', 'minute_agg']

    def __init__(self, config: FeedAdapterConfig):
        super().__init__(config)

        # Check if we can use the production adapter
        self._use_production = False
        self._production_adapter = None

        if config.api_key:
            try:
                from .polygon_realtime import PolygonRealtimeFeedAdapter, PolygonFeedConfig

                polygon_config = PolygonFeedConfig(
                    api_key=config.api_key,
                    symbols=list(config.provider_config.get('symbols', [])),
                    name=config.name,
                    connect_timeout_seconds=config.connect_timeout_seconds,
                    reconnect_delay_seconds=config.reconnect_delay_seconds,
                    max_reconnect_attempts=config.max_reconnect_attempts,
                    max_subscriptions=config.max_subscriptions,
                    buffer_size=config.buffer_size,
                )
                self._production_adapter = PolygonRealtimeFeedAdapter(polygon_config)
                self._use_production = True
                self.logger.info("Using production PolygonRealtimeFeedAdapter")

            except ImportError as e:
                self.logger.warning(
                    f"Could not load production Polygon adapter: {e}. "
                    "Install websockets: pip install websockets"
                )

        if not self._use_production:
            warnings.warn(
                "PolygonFeedAdapter using simulated data. "
                "Provide api_key and install websockets for real data.",
                UserWarning
            )
            self._simulated = SimulatedFeedAdapter(config)

    async def connect(self) -> bool:
        if self._use_production and self._production_adapter:
            return await self._production_adapter.connect()
        self.logger.warning("STUB: Using simulated connection for Polygon")
        return await self._simulated.connect()

    async def disconnect(self) -> None:
        if self._use_production and self._production_adapter:
            await self._production_adapter.disconnect()
        else:
            await self._simulated.disconnect()

    async def subscribe(self, symbols: List[str], data_types: List[str]) -> bool:
        if self._use_production and self._production_adapter:
            return await self._production_adapter.subscribe(symbols, data_types)
        self.logger.warning("STUB: Using simulated data for Polygon subscription")
        return await self._simulated.subscribe(symbols, data_types)

    async def unsubscribe(self, symbols: List[str]) -> bool:
        if self._use_production and self._production_adapter:
            return await self._production_adapter.unsubscribe(symbols)
        return await self._simulated.unsubscribe(symbols)

    def is_connected(self) -> bool:
        if self._use_production and self._production_adapter:
            return self._production_adapter.is_connected()
        return self._simulated.is_connected()

    def add_message_handler(self, handler) -> None:
        """Route message handler to appropriate adapter"""
        if self._use_production and self._production_adapter:
            self._production_adapter.add_message_handler(handler)
        else:
            super().add_message_handler(handler)


class InteractiveBrokersFeedAdapter(DataFeedAdapter):
    """
    Interactive Brokers data feed adapter.

    ⚠️  STUB IMPLEMENTATION - Returns simulated data

    To implement fully, requires:
        1. IB Gateway or TWS running
        2. ib_insync or ibapi package
        3. Market data subscription

    Documentation: https://interactivebrokers.github.io/
    """

    IS_IMPLEMENTED = False
    PROVIDER = FeedProvider.INTERACTIVE_BROKERS
    SUPPORTED_DATA_TYPES = ['quote', 'trade', 'bar', 'depth']

    def __init__(self, config: FeedAdapterConfig):
        super().__init__(config)
        warnings.warn(
            "InteractiveBrokersFeedAdapter is a STUB. It returns simulated data. "
            "Implement connect/subscribe methods for production use.",
            UserWarning
        )
        self._simulated = SimulatedFeedAdapter(config)

    async def connect(self) -> bool:
        self.logger.warning("STUB: Using simulated connection for IB")
        return await self._simulated.connect()

    async def disconnect(self) -> None:
        await self._simulated.disconnect()

    async def subscribe(self, symbols: List[str], data_types: List[str]) -> bool:
        self.logger.warning("STUB: Using simulated data for IB subscription")
        return await self._simulated.subscribe(symbols, data_types)

    async def unsubscribe(self, symbols: List[str]) -> bool:
        return await self._simulated.unsubscribe(symbols)

    def is_connected(self) -> bool:
        return self._simulated.is_connected()


# ============================================================================
# ADAPTER FACTORY
# ============================================================================

class FeedAdapterFactory:
    """
    Factory for creating data feed adapters.

    Usage:
        config = FeedAdapterConfig(
            provider=FeedProvider.ALPACA,
            name="my-alpaca-feed",
            api_key="your-api-key"
        )
        adapter = FeedAdapterFactory.create(config)
    """

    _adapters: Dict[FeedProvider, type] = {
        FeedProvider.SIMULATED: SimulatedFeedAdapter,
        FeedProvider.ALPACA: AlpacaFeedAdapter,
        FeedProvider.POLYGON: PolygonFeedAdapter,
        FeedProvider.INTERACTIVE_BROKERS: InteractiveBrokersFeedAdapter,
    }

    @classmethod
    def create(cls, config: FeedAdapterConfig) -> DataFeedAdapter:
        """
        Create an adapter for the specified provider.

        Args:
            config: Adapter configuration

        Returns:
            DataFeedAdapter instance

        Raises:
            ValueError: If provider is not supported
        """
        adapter_class = cls._adapters.get(config.provider)

        if adapter_class is None:
            raise ValueError(
                f"Unsupported provider: {config.provider}. "
                f"Available: {list(cls._adapters.keys())}"
            )

        adapter = adapter_class(config)

        # Warn if using stub implementation
        if not adapter_class.IS_IMPLEMENTED:
            logger.warning(
                f"Provider {config.provider.value} adapter is a STUB. "
                "Data will be simulated."
            )

        return adapter

    @classmethod
    def register(cls, provider: FeedProvider, adapter_class: type) -> None:
        """
        Register a custom adapter class.

        Args:
            provider: Provider enum value
            adapter_class: Adapter class (must extend DataFeedAdapter)
        """
        if not issubclass(adapter_class, DataFeedAdapter):
            raise TypeError("Adapter class must extend DataFeedAdapter")

        cls._adapters[provider] = adapter_class
        logger.info(f"Registered adapter for provider: {provider.value}")

    @classmethod
    def get_available_providers(cls) -> List[FeedProvider]:
        """Get list of available providers."""
        return list(cls._adapters.keys())

    @classmethod
    def get_implemented_providers(cls) -> List[FeedProvider]:
        """Get list of fully implemented providers (not stubs)."""
        return [
            provider for provider, adapter_class in cls._adapters.items()
            if adapter_class.IS_IMPLEMENTED
        ]
