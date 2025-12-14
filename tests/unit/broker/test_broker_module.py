"""
Unit tests for broker module components.
Tests broker adapter, connection manager, and related components.
"""

import pytest
from unittest.mock import patch, AsyncMock

from core_engine.broker.broker_adapter import (
    BrokerAdapter,
    BrokerCredentials,
    BrokerType,
    ConnectionStatus,
    StandardOrder,
    StandardPosition,
    StandardAccount,
    OrderAction,
    OrderType,
    TimeInForce
)

from core_engine.broker.broker_manager import (
    BrokerManager,
    BrokerConfig
)

class TestBrokerAdapter:
    """Test suite for BrokerAdapter class."""

    @pytest.fixture
    def broker_credentials(self):
        """Create test broker credentials."""
        return BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            api_key="test_api_key",
            secret_key="test_secret_key",
            host="api.testbroker.com",
            account_id="test_account"
        )

    @pytest.fixture
    def broker_adapter(self, broker_credentials):
        """Create test broker adapter."""
        return BrokerAdapter(
            credentials=broker_credentials
        )

    def test_initialization(self, broker_adapter, broker_credentials):
        """Test broker adapter initialization."""
        assert broker_adapter.broker_type == BrokerType.INTERACTIVE_BROKERS
        assert broker_adapter.credentials == broker_credentials
        assert broker_adapter.connection_status == ConnectionStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_connect_success(self, broker_adapter):
        """Test successful connection."""
        with patch.object(broker_adapter._adapter, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            with patch.object(broker_adapter._adapter, 'authenticate', new_callable=AsyncMock) as mock_auth:
                mock_auth.return_value = True
                broker_adapter._adapter.connection_status = ConnectionStatus.CONNECTED

                result = await broker_adapter.connect()

                assert result is True
                mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, broker_adapter):
        """Test connection failure."""
        with patch.object(broker_adapter._adapter, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = False

            result = await broker_adapter.connect()

            assert result is False
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, broker_adapter):
        """Test disconnection."""
        broker_adapter.connection_status = ConnectionStatus.CONNECTED

        with patch.object(broker_adapter._adapter, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
            mock_disconnect.return_value = True

            result = await broker_adapter.disconnect()

            assert result is True
            mock_disconnect.assert_called_once()

    def test_create_standard_order(self, broker_adapter):
        """Test creating a standard order."""
        order = StandardOrder(
            order_id="test_order_123",
            symbol="AAPL",
            quantity=100,
            action=OrderAction.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY
        )

        assert isinstance(order, StandardOrder)
        assert order.symbol == "AAPL"
        assert order.quantity == 100
        assert order.action == OrderAction.BUY
        assert order.order_type == OrderType.MARKET
        assert order.time_in_force == TimeInForce.DAY

    @pytest.mark.asyncio
    async def test_submit_order_connected(self, broker_adapter):
        """Test order submission when connected."""
        broker_adapter.connection_status = ConnectionStatus.READY

        order = StandardOrder(
            order_id="test_order_123",
            symbol="AAPL",
            quantity=100,
            action=OrderAction.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY
        )

        with patch.object(broker_adapter._adapter, 'submit_order', new_callable=AsyncMock) as mock_submit:
            mock_submit.return_value = "broker_order_123"

            result = await broker_adapter.submit_order(order)

            assert result == "broker_order_123"
            mock_submit.assert_called_once_with(order)

    @pytest.mark.asyncio
    async def test_submit_order_disconnected(self, broker_adapter):
        """Test order submission when disconnected."""
        broker_adapter.connection_status = ConnectionStatus.DISCONNECTED

        order = StandardOrder(
            order_id="test_order_124",
            symbol="AAPL",
            quantity=100,
            action=OrderAction.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY
        )

        with pytest.raises(RuntimeError):
            await broker_adapter.submit_order(order)

    @pytest.mark.asyncio
    async def test_get_positions(self, broker_adapter):
        """Test getting positions."""
        broker_adapter.connection_status = ConnectionStatus.READY

        expected_positions = [
            StandardPosition(
                symbol="AAPL",
                quantity=100,
                avg_cost=150.0,
                market_value=15500.0,
                unrealized_pnl=500.0,
                last_price=155.0
            )
        ]

        with patch.object(broker_adapter._adapter, 'get_positions', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = expected_positions

            positions = await broker_adapter.get_positions()

            assert positions == expected_positions
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_account_info(self, broker_adapter):
        """Test getting account information."""
        broker_adapter.connection_status = ConnectionStatus.READY

        expected_account = StandardAccount(
            account_id="test_account",
            account_type="margin",
            total_equity=150000.0,
            buying_power=200000.0,
            cash_balance=100000.0
        )

        with patch.object(broker_adapter._adapter, 'get_account_info', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = expected_account

            account = await broker_adapter.get_account_info()

            assert account == expected_account
            mock_get.assert_called_once()

class TestBrokerManager:
    """Test suite for BrokerManager class."""

    @pytest.fixture
    def broker_manager(self):
        """Create test broker manager."""
        return BrokerManager(BrokerConfig())

    def test_initialization(self, broker_manager):
        """Test broker manager initialization."""
        assert len(broker_manager._broker_adapters) == 0
        assert broker_manager.is_initialized is False
        assert broker_manager.is_operational is False

    @pytest.mark.asyncio
    async def test_add_broker(self, broker_manager):
        """Test adding a broker."""
        credentials = BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            api_key="test_key",
            secret_key="test_secret",
            host="test.host.com",
            account_id="test_account"
        )

        broker_id = await broker_manager.add_broker(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            credentials=credentials
        )

        assert broker_id in broker_manager._broker_adapters
        assert isinstance(broker_manager._broker_adapters[broker_id], BrokerAdapter)

    @pytest.mark.asyncio
    async def test_remove_broker(self, broker_manager):
        """Test removing a broker."""
        credentials = BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            api_key="test_key",
            secret_key="test_secret",
            host="test.host.com",
            account_id="test_account"
        )

        broker_id = await broker_manager.add_broker(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            credentials=credentials
        )

        assert broker_id in broker_manager._broker_adapters

        result = await broker_manager.remove_broker(broker_id)
        assert result is True
        assert broker_id not in broker_manager._broker_adapters

    def test_get_broker(self, broker_manager):
        """Test getting a broker."""
        # Test with non-existent broker
        adapter = broker_manager.get_broker("non_existent")
        assert adapter is None

    def test_list_brokers(self, broker_manager):
        """Test listing brokers."""
        brokers = broker_manager.list_brokers()
        assert isinstance(brokers, list)
        assert len(brokers) == 0

    def test_get_broker_count(self, broker_manager):
        """Test getting broker count."""
        count = broker_manager.get_broker_count()
        assert count == 0