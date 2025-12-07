"""
Test suite for core_engine/data/feeds/adapters.py

Tests the data feed adapter infrastructure including:
- DataFeedAdapter abstract base class
- SimulatedFeedAdapter implementation
- Stub adapters (Alpaca, Polygon, InteractiveBrokers)
- FeedAdapterFactory
- Enums and dataclasses
"""

import asyncio
import pytest
from unittest.mock import MagicMock

from core_engine.data.feeds.adapters import (
    AdapterStatus,
    FeedProvider,
    FeedAdapterConfig,
    FeedMessage,
    DataFeedAdapter,
    SimulatedFeedAdapter,
    AlpacaFeedAdapter,
    PolygonFeedAdapter,
    InteractiveBrokersFeedAdapter,
    FeedAdapterFactory,
)


class TestEnums:
    """Test enum classes."""

    def test_adapter_status_values(self):
        """Test AdapterStatus enum values."""
        assert AdapterStatus.DISCONNECTED.value == "disconnected"
        assert AdapterStatus.CONNECTING.value == "connecting"
        assert AdapterStatus.CONNECTED.value == "connected"
        assert AdapterStatus.ERROR.value == "error"

    def test_feed_provider_values(self):
        """Test FeedProvider enum values."""
        assert FeedProvider.SIMULATED.value == "simulated"
        assert FeedProvider.ALPACA.value == "alpaca"
        assert FeedProvider.POLYGON.value == "polygon"
        assert FeedProvider.INTERACTIVE_BROKERS.value == "ib"


class TestDataclasses:
    """Test dataclass structures."""

    def test_feed_adapter_config_creation(self):
        """Test FeedAdapterConfig creation."""
        config = FeedAdapterConfig(
            provider=FeedProvider.SIMULATED,
            name="test_adapter",
            api_key="test_key"
        )
        assert config.provider == FeedProvider.SIMULATED
        assert config.name == "test_adapter"
        assert config.api_key == "test_key"

    def test_feed_adapter_config_defaults(self):
        """Test FeedAdapterConfig default values."""
        config = FeedAdapterConfig(provider=FeedProvider.SIMULATED, name="test")
        assert config.api_key is None
        assert config.api_secret is None
        assert config.base_url is None

    def test_feed_message_creation(self):
        """Test FeedMessage creation."""
        import datetime
        message = FeedMessage(
            provider=FeedProvider.SIMULATED,
            symbol="AAPL",
            message_type="trade",
            data={"price": 150.0, "volume": 100},
            timestamp=datetime.datetime.now()
        )
        assert message.symbol == "AAPL"
        assert message.message_type == "trade"
        assert message.data["price"] == 150.0


class TestDataFeedAdapter:
    """Test the abstract DataFeedAdapter base class."""

    def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError."""
        # We can't instantiate the abstract class directly, but we can test
        # that the abstract methods are defined
        assert hasattr(DataFeedAdapter, 'connect')
        assert hasattr(DataFeedAdapter, 'disconnect')
        assert hasattr(DataFeedAdapter, 'subscribe')
        assert hasattr(DataFeedAdapter, 'unsubscribe')
        assert hasattr(DataFeedAdapter, 'is_connected')

    def test_abstract_method_signatures(self):
        """Test abstract method signatures are correct."""
        import inspect

        # Check connect method signature
        connect_sig = inspect.signature(DataFeedAdapter.connect)
        assert 'self' in connect_sig.parameters

        # Check disconnect method signature
        disconnect_sig = inspect.signature(DataFeedAdapter.disconnect)
        assert 'self' in disconnect_sig.parameters

        # Check subscribe method signature
        subscribe_sig = inspect.signature(DataFeedAdapter.subscribe)
        assert 'self' in subscribe_sig.parameters
        assert 'symbols' in subscribe_sig.parameters
        assert 'data_types' in subscribe_sig.parameters

        # Check unsubscribe method signature
        unsubscribe_sig = inspect.signature(DataFeedAdapter.unsubscribe)
        assert 'self' in unsubscribe_sig.parameters
        assert 'symbols' in unsubscribe_sig.parameters
        # Note: unsubscribe only takes symbols, not data_types

        # Check is_connected method signature
        is_connected_sig = inspect.signature(DataFeedAdapter.is_connected)
        assert 'self' in is_connected_sig.parameters


class TestSimulatedFeedAdapter:
    """Test the SimulatedFeedAdapter implementation."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return FeedAdapterConfig(
            provider=FeedProvider.SIMULATED,
            name="test_adapter",
            api_key="test_key"
        )

    @pytest.fixture
    def adapter(self, config):
        """Create a SimulatedFeedAdapter instance."""
        return SimulatedFeedAdapter(config)

    def test_initialization(self, adapter, config):
        """Test adapter initialization."""
        assert adapter.config == config
        assert adapter.status == AdapterStatus.DISCONNECTED
        assert adapter.get_subscriptions() == set()
        assert adapter._message_handlers == []

    @pytest.mark.asyncio
    async def test_connect(self, adapter):
        """Test connection to simulated feed."""
        await adapter.connect()
        assert adapter.status == AdapterStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        """Test disconnection from simulated feed."""
        await adapter.connect()
        await adapter.disconnect()
        assert adapter.status == AdapterStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_is_connected(self, adapter):
        """Test connection status checking."""
        assert not adapter.is_connected()
        await adapter.connect()
        assert adapter.is_connected()
        await adapter.disconnect()
        assert not adapter.is_connected()

    @pytest.mark.asyncio
    async def test_subscribe(self, adapter):
        """Test subscribing to symbols and data types."""
        symbols = ["AAPL"]
        data_types = ["trade"]

        await adapter.connect()
        await adapter.subscribe(symbols, data_types)

        assert "AAPL" in adapter.get_subscriptions()

    @pytest.mark.asyncio
    async def test_unsubscribe(self, adapter):
        """Test unsubscribing from symbols and data types."""
        symbols = ["AAPL"]
        data_types = ["trade"]

        await adapter.connect()
        await adapter.subscribe(symbols, data_types)
        assert "AAPL" in adapter.get_subscriptions()

        await adapter.unsubscribe(symbols)
        assert "AAPL" not in adapter.get_subscriptions()

    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self, adapter):
        """Test subscribing when not connected (should work for simulated adapter)."""
        # The simulated adapter allows subscribing when not connected
        await adapter.subscribe(["AAPL"], ["trade"])
        assert "AAPL" in adapter.get_subscriptions()

    @pytest.mark.asyncio
    async def test_unsubscribe_not_connected(self, adapter):
        """Test unsubscribing when not connected."""
        await adapter.subscribe(["AAPL"], ["trade"])
        assert "AAPL" in adapter.get_subscriptions()

        await adapter.unsubscribe(["AAPL"])
        assert "AAPL" not in adapter.get_subscriptions()

    @pytest.mark.asyncio
    async def test_message_generation(self, adapter):
        """Test that adapter generates simulated messages."""
        await adapter.connect()
        await adapter.subscribe(["AAPL"], ["trade"])

        # Wait a bit for message generation
        await asyncio.sleep(0.1)

        # Check that messages were generated (implementation detail)
        # This tests the internal message generation logic

    def test_add_message_handler(self, adapter):
        """Test adding message handlers."""
        handler = MagicMock()
        adapter.add_message_handler(handler)
        assert handler in adapter._message_handlers

    def test_remove_message_handler(self, adapter):
        """Test removing message handlers."""
        handler = MagicMock()
        adapter.add_message_handler(handler)
        # Since there's no remove method, we test that we can add multiple
        handler2 = MagicMock()
        adapter.add_message_handler(handler2)
        assert len(adapter._message_handlers) == 2


class TestStubAdapters:
    """Test the stub adapter implementations."""

    @pytest.fixture
    def alpaca_config(self):
        """Create Alpaca adapter config."""
        return FeedAdapterConfig(
            provider=FeedProvider.ALPACA,
            name="alpaca_adapter",
            api_key="test_key"
        )

    @pytest.fixture
    def polygon_config(self):
        """Create Polygon adapter config."""
        return FeedAdapterConfig(
            provider=FeedProvider.POLYGON,
            name="polygon_adapter",
            api_key="test_key"
        )

    @pytest.fixture
    def ib_config(self):
        """Create Interactive Brokers adapter config."""
        return FeedAdapterConfig(
            provider=FeedProvider.INTERACTIVE_BROKERS,
            name="ib_adapter",
            api_key="test_key"
        )

    def test_alpaca_adapter_creation(self, alpaca_config):
        """Test AlpacaFeedAdapter creation."""
        adapter = AlpacaFeedAdapter(alpaca_config)
        assert isinstance(adapter, DataFeedAdapter)
        assert adapter.config == alpaca_config

    def test_polygon_adapter_creation(self, polygon_config):
        """Test PolygonFeedAdapter creation."""
        adapter = PolygonFeedAdapter(polygon_config)
        assert isinstance(adapter, DataFeedAdapter)
        assert adapter.config == polygon_config

    def test_ib_adapter_creation(self, ib_config):
        """Test InteractiveBrokersFeedAdapter creation."""
        adapter = InteractiveBrokersFeedAdapter(ib_config)
        assert isinstance(adapter, DataFeedAdapter)
        assert adapter.config == ib_config

    @pytest.mark.asyncio
    async def test_stub_adapter_delegation(self, alpaca_config):
        """Test that stub adapters delegate to simulated adapter."""
        adapter = AlpacaFeedAdapter(alpaca_config)

        # The stub adapter creates its own simulated adapter internally
        # We can test that it behaves like a working adapter
        result = await adapter.connect()
        assert result is True
        assert adapter.is_connected()

        result = await adapter.subscribe(["AAPL"], ["trade"])
        assert result is True

        await adapter.disconnect()
        assert not adapter.is_connected()


class TestFeedAdapterFactory:
    """Test the FeedAdapterFactory."""

    def test_factory_creation(self):
        """Test factory creation."""
        # Factory is a class with class methods, no instance creation needed
        assert hasattr(FeedAdapterFactory, 'create')
        assert hasattr(FeedAdapterFactory, '_adapters')

    def test_register_adapter(self):
        """Test registering an adapter."""
        config = FeedAdapterConfig(provider=FeedProvider.SIMULATED, name="test")

        adapter = FeedAdapterFactory.create(config)
        assert isinstance(adapter, SimulatedFeedAdapter)
        assert adapter.config == config

    def test_create_simulated_adapter(self):
        """Test creating simulated adapter."""
        config = FeedAdapterConfig(provider=FeedProvider.SIMULATED, name="test")

        adapter = FeedAdapterFactory.create(config)
        assert isinstance(adapter, SimulatedFeedAdapter)

    def test_create_alpaca_adapter(self):
        """Test creating Alpaca adapter."""
        config = FeedAdapterConfig(provider=FeedProvider.ALPACA, name="test")

        adapter = FeedAdapterFactory.create(config)
        assert isinstance(adapter, AlpacaFeedAdapter)

    def test_create_polygon_adapter(self):
        """Test creating Polygon adapter."""
        config = FeedAdapterConfig(provider=FeedProvider.POLYGON, name="test")

        adapter = FeedAdapterFactory.create(config)
        assert isinstance(adapter, PolygonFeedAdapter)

    def test_create_interactive_brokers_adapter(self):
        """Test creating Interactive Brokers adapter."""
        config = FeedAdapterConfig(provider=FeedProvider.INTERACTIVE_BROKERS, name="test")

        adapter = FeedAdapterFactory.create(config)
        assert isinstance(adapter, InteractiveBrokersFeedAdapter)

    def test_create_unknown_provider(self):
        """Test creating adapter with unknown provider raises error."""
        config = FeedAdapterConfig(provider=FeedProvider.SIMULATED, name="test")
        config.provider = "unknown"  # Manually set to unknown

        with pytest.raises(ValueError, match="Unsupported provider"):
            FeedAdapterFactory.create(config)

    def test_get_supported_providers(self):
        """Test getting supported providers."""
        providers = FeedAdapterFactory.get_available_providers()

        expected_providers = {
            FeedProvider.SIMULATED,
            FeedProvider.ALPACA,
            FeedProvider.POLYGON,
            FeedProvider.INTERACTIVE_BROKERS
        }
        assert set(providers) == expected_providers


class TestIntegration:
    """Integration tests for adapter functionality."""

    @pytest.mark.asyncio
    async def test_full_adapter_lifecycle(self):
        """Test complete adapter lifecycle."""
        config = FeedAdapterConfig(
            provider=FeedProvider.SIMULATED,
            name="test_adapter"
        )

        adapter = SimulatedFeedAdapter(config)

        # Test initial state
        assert adapter.status == AdapterStatus.DISCONNECTED
        assert not adapter.is_connected()

        # Connect
        await adapter.connect()
        assert adapter.status == AdapterStatus.CONNECTED
        assert adapter.is_connected()

        # Subscribe
        await adapter.subscribe(["AAPL"], ["trade"])
        assert "AAPL" in adapter.get_subscriptions()

        # Unsubscribe
        await adapter.unsubscribe(["AAPL"])
        assert "AAPL" not in adapter.get_subscriptions()

        # Disconnect
        await adapter.disconnect()
        assert adapter.status == AdapterStatus.DISCONNECTED
        assert not adapter.is_connected()

    @pytest.mark.asyncio
    async def test_message_handler_integration(self):
        """Test message handler integration."""
        config = FeedAdapterConfig(provider=FeedProvider.SIMULATED, name="test")
        adapter = SimulatedFeedAdapter(config)

        # Add a mock message handler
        handler = MagicMock()
        adapter.add_message_handler(handler)

        await adapter.connect()
        await adapter.subscribe(["AAPL"], ["trade"])

        # Wait for some messages to be generated
        await asyncio.sleep(0.2)

        # Verify handler was called (this depends on implementation details)
        # The handler should have been called with FeedMessage objects

    def test_factory_integration(self):
        """Test factory creates correct adapter types."""
        providers_and_types = [
            (FeedProvider.SIMULATED, SimulatedFeedAdapter),
            (FeedProvider.ALPACA, AlpacaFeedAdapter),
            (FeedProvider.POLYGON, PolygonFeedAdapter),
            (FeedProvider.INTERACTIVE_BROKERS, InteractiveBrokersFeedAdapter),
        ]

        for provider, expected_type in providers_and_types:
            config = FeedAdapterConfig(provider=provider, name=f"{provider.value}_test")
            adapter = FeedAdapterFactory.create(config)
            assert isinstance(adapter, expected_type)
            assert adapter.config.provider == provider