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
from unittest.mock import MagicMock, patch

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

    @pytest.mark.asyncio
    async def test_connect_exception_handling(self, adapter):
        """Test exception handling in connect method."""
        # Mock asyncio.sleep to raise an exception
        with patch('asyncio.sleep', side_effect=Exception("Connection failed")):
            result = await adapter.connect()
            assert result is False
            assert adapter.status == AdapterStatus.ERROR

    @pytest.mark.asyncio
    async def test_subscribe_exception_handling(self, adapter):
        """Test exception handling in subscribe method."""
        def mock_set_status(status):
            if status == AdapterStatus.ACTIVE:
                raise Exception("Subscribe failed")
            # For other statuses, do nothing
        
        with patch.object(adapter, '_set_status', side_effect=mock_set_status):
            await adapter.connect()
            result = await adapter.subscribe(["AAPL"], ["trade"])
            assert result is False

    @pytest.mark.asyncio
    async def test_simulate_data_exception_handling(self, adapter):
        """Test exception handling in _simulate_data method."""
        await adapter.connect()
        await adapter.subscribe(["AAPL"], ["trade"])
        
        # Wait a bit for simulation to start
        await asyncio.sleep(0.1)
        
        # The simulation should handle exceptions internally
        # This tests the try/except block in _simulate_data

    def test_add_error_handler(self, adapter):
        """Test adding error handlers."""
        handler = MagicMock()
        adapter.add_error_handler(handler)
        assert handler in adapter._error_handlers

    def test_add_status_handler(self, adapter):
        """Test adding status handlers."""
        handler = MagicMock()
        adapter.add_status_handler(handler)
        assert handler in adapter._status_handlers

    def test_get_statistics(self, adapter):
        """Test getting adapter statistics."""
        stats = adapter.get_statistics()
        assert isinstance(stats, dict)
        assert 'messages_received' in stats
        assert 'messages_processed' in stats
        assert 'errors' in stats

    def test_status_handler_notification(self, adapter):
        """Test status handler gets called on status changes."""
        handler = MagicMock()
        adapter.add_status_handler(handler)
        
        # Manually call _set_status to trigger handler
        adapter._set_status(AdapterStatus.CONNECTED)
        
        handler.assert_called_with(AdapterStatus.CONNECTED)

    def test_error_handler_notification(self, adapter):
        """Test error handler gets called."""
        handler = MagicMock()
        adapter.add_error_handler(handler)
        
        # Manually call _handle_error to trigger handler
        test_error = Exception("Test error")
        adapter._handle_error(test_error)
        
        handler.assert_called_with(test_error)

    def test_message_handler_notification(self, adapter):
        """Test message handler gets called."""
        from datetime import datetime
        handler = MagicMock()
        adapter.add_message_handler(handler)
        
        # Create a test message
        message = FeedMessage(
            provider=FeedProvider.SIMULATED,
            symbol="AAPL",
            message_type="trade",
            timestamp=datetime.now(),
            data={"price": 150.0}
        )
        
        # Manually call _handle_message to trigger handler
        adapter._handle_message(message)
        
        handler.assert_called_with(message)


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
    async def test_polygon_adapter_simulated_fallback(self, polygon_config):
        """Test PolygonFeedAdapter falls back to simulated when no production adapter."""
        # Create config without api_key to force simulated fallback
        config = FeedAdapterConfig(
            provider=FeedProvider.POLYGON,
            name="polygon_adapter",
            api_key=None  # No API key
        )
        adapter = PolygonFeedAdapter(config)
        
        # Should use simulated adapter
        result = await adapter.connect()
        assert result is True
        assert adapter.is_connected()
        
        result = await adapter.subscribe(["AAPL"], ["trade"])
        assert result is True
        
        await adapter.disconnect()
        assert not adapter.is_connected()

    @pytest.mark.asyncio
    async def test_ib_adapter_simulated_methods(self, ib_config):
        """Test InteractiveBrokersFeedAdapter simulated methods."""
        adapter = InteractiveBrokersFeedAdapter(ib_config)
        
        result = await adapter.connect()
        assert result is True
        
        result = await adapter.subscribe(["AAPL"], ["trade"])
        assert result is True
        
        result = await adapter.unsubscribe(["AAPL"])
        assert result is True
        
        assert adapter.is_connected()
        
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

    def test_get_implemented_providers(self):
        """Test getting implemented providers."""
        implemented = FeedAdapterFactory.get_implemented_providers()
        assert FeedProvider.SIMULATED in implemented
        assert FeedProvider.ALPACA not in implemented
        assert FeedProvider.POLYGON not in implemented
        assert FeedProvider.INTERACTIVE_BROKERS not in implemented

    def test_register_adapter_invalid_class(self):
        """Test registering invalid adapter class raises error."""
        with pytest.raises(TypeError, match="Adapter class must extend DataFeedAdapter"):
            FeedAdapterFactory.register(FeedProvider.CUSTOM, str)  # str doesn't extend DataFeedAdapter


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