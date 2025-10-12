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

from core_engine.broker.connection_manager import (
    ConnectionManager,
    ConnectionConfig
)

from core_engine.broker.protocol_handler import (
    ProtocolConfig,
    ProtocolType,
    MessageType,
    ProtocolMessage,
    MessageDirection,
    RESTProtocolHandler
)

from core_engine.broker.message_processor import (
    MessageProcessor,
    ProcessingConfig
)

from core_engine.broker.session_manager import (
    SessionManager,
    SessionConfig,
    SessionType
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


class TestConnectionManager:
    """Test suite for ConnectionManager class."""

    @pytest.fixture
    def connection_config(self):
        """Create test connection configuration."""
        return ConnectionConfig(
            max_connections=5,
            connection_timeout=30.0,
            max_retry_attempts=3,
            retry_delay=5.0
        )

    @pytest.fixture
    def connection_manager(self, connection_config):
        """Create test connection manager."""
        return ConnectionManager(connection_config)

    def test_initialization(self, connection_manager, connection_config):
        """Test connection manager initialization."""
        assert connection_manager.config == connection_config
        assert len(connection_manager._connections) == 0

    @pytest.mark.asyncio
    async def test_add_connection(self, connection_manager):
        """Test adding a connection."""
        from core_engine.broker.broker_adapter import BrokerCredentials
        
        credentials = BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            username="test_user",
            password="test_pass",
            api_key="test_key",
            secret_key="test_secret"
        )

        connection_id = await connection_manager.add_broker(credentials)

        assert connection_id in connection_manager._connections
        assert connection_manager._connections[connection_id].broker_adapter is not None

    @pytest.mark.asyncio
    async def test_remove_connection(self, connection_manager):
        """Test removing a connection."""
        from core_engine.broker.broker_adapter import BrokerCredentials
        
        credentials = BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            username="test_user",
            password="test_pass",
            api_key="test_key",
            secret_key="test_secret"
        )

        connection_id = await connection_manager.add_broker(credentials)
        assert connection_id in connection_manager._connections

        result = await connection_manager.remove_broker(connection_id)
        assert result is True
        assert connection_id not in connection_manager._connections

    @pytest.mark.asyncio
    async def test_get_connection(self, connection_manager):
        """Test getting a connection."""
        from core_engine.broker.broker_adapter import BrokerCredentials
        
        credentials = BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            username="test_user",
            password="test_pass",
            api_key="test_key",
            secret_key="test_secret"
        )

        connection_id = await connection_manager.add_broker(credentials)
        
        # Set the connection status to READY
        connection_manager._connections[connection_id].status = ConnectionStatus.READY
        
        retrieved_adapter = connection_manager.get_connection(BrokerType.INTERACTIVE_BROKERS)

        assert retrieved_adapter is not None

    def test_get_connection_not_found(self, connection_manager):
        """Test getting a non-existent connection."""
        retrieved_adapter = connection_manager.get_connection(BrokerType.INTERACTIVE_BROKERS)
        
        assert retrieved_adapter is None


class TestProtocolHandler:
    """Test suite for ProtocolHandler classes."""

    @pytest.fixture
    def protocol_config(self):
        """Create test protocol configuration."""
        return ProtocolConfig(
            protocol_type=ProtocolType.REST,
            url="https://api.testbroker.com",
            version="v1",
            connect_timeout=30.0,
            read_timeout=10.0,
            max_retries=3,
            retry_delay=1.0
        )

    @pytest.fixture
    def rest_protocol_handler(self, protocol_config):
        """Create test REST protocol handler."""
        return RESTProtocolHandler(protocol_config)

    def test_rest_initialization(self, rest_protocol_handler, protocol_config):
        """Test REST protocol handler initialization."""
        assert rest_protocol_handler.config == protocol_config
        assert rest_protocol_handler.protocol_type == ProtocolType.REST

    @pytest.mark.asyncio
    async def test_rest_send_message(self, rest_protocol_handler):
        """Test sending message via REST."""
        message = ProtocolMessage(
            message_id="test_id",
            message_type=MessageType.CUSTOM,
            direction=MessageDirection.OUTBOUND,
            protocol_type=ProtocolType.REST,
            raw_data=b'',
            parsed_data={"action": "get_positions", "account": "test"}
        )

        # Mock the session
        mock_session = AsyncMock()
        rest_protocol_handler._session = mock_session

        # Mock the request method with a context manager
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"positions": []}
        mock_response.read.return_value = b'{"positions": []}'
        
        # Create a proper context manager class
        class MockContextManager:
            async def __aenter__(self):
                return mock_response
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        # Replace the request method with a regular function that returns the context manager
        def mock_request(*args, **kwargs):
            return MockContextManager()
        
        mock_session.request = mock_request        # Mock the message handler trigger
        with patch.object(rest_protocol_handler, '_trigger_message_handlers') as mock_trigger:
            result = await rest_protocol_handler.send_message(message)

            assert result is True
            mock_trigger.assert_called_once()


class TestMessageProcessor:
    """Test suite for MessageProcessor class."""

    @pytest.fixture
    def processing_config(self):
        """Create test processing configuration."""
        return ProcessingConfig(
            max_queue_size=1000,
            worker_count=4,
            max_concurrent_messages=100,
            batch_timeout=30.0
        )

    @pytest.fixture
    def message_processor(self, processing_config):
        """Create test message processor."""
        return MessageProcessor(processing_config)

    def test_initialization(self, message_processor, processing_config):
        """Test message processor initialization."""
        assert message_processor.config == processing_config
        assert message_processor._inbound_queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_process_message(self, message_processor):
        """Test processing a message."""
        message = ProtocolMessage(
            message_id="test_id",
            message_type=MessageType.ORDER_STATUS,
            direction=MessageDirection.OUTBOUND,
            protocol_type=ProtocolType.REST,
            raw_data=b'',
            parsed_data={
                "type": "order_update",
                "order_id": "123",
                "status": "filled",
                "price": 150.0
            }
        )

        envelope_id = await message_processor.process_message(message)

        assert isinstance(envelope_id, str)
        assert len(envelope_id) > 0
        assert envelope_id in message_processor._pending_messages


class TestSessionManager:
    """Test suite for SessionManager class."""

    @pytest.fixture
    def session_config(self):
        """Create test session configuration."""
        return SessionConfig(
            session_timeout=3600.0,
            max_sessions_per_user=10,
            heartbeat_interval=30.0,
            require_ssl=True
        )

    @pytest.fixture
    def session_manager(self, session_config):
        """Create test session manager."""
        return SessionManager(session_config)

    def test_initialization(self, session_manager, session_config):
        """Test session manager initialization."""
        assert session_manager.config == session_config
        assert len(session_manager._sessions) == 0
        assert session_manager._authenticator is not None

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Test creating a session."""
        credentials = BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            api_key="test_key",
            secret_key="test_secret",
            host="test.host.com",
            account_id="test_account"
        )
        
        session_id = await session_manager.create_session(
            user_id="test_user",
            session_type=SessionType.TRADING,
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            protocol_type=ProtocolType.REST,
            credentials=credentials
        )

        assert session_id in session_manager._sessions
        assert session_manager._sessions[session_id].session_type == SessionType.TRADING

    @pytest.mark.asyncio
    async def test_close_session(self, session_manager):
        """Test closing a session."""
        credentials = BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            api_key="test_key",
            secret_key="test_secret",
            host="test.host.com",
            account_id="test_account"
        )
        
        session_id = await session_manager.create_session(
            user_id="test_user",
            session_type=SessionType.TRADING,
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            protocol_type=ProtocolType.REST,
            credentials=credentials
        )
        assert session_id in session_manager._sessions

        await session_manager.close_session(session_id)
        assert session_id not in session_manager._sessions


class TestBrokerManager:
    """Test suite for BrokerManager class."""

    @pytest.fixture
    def broker_manager(self):
        """Create test broker manager."""
        return BrokerManager(BrokerConfig())

    def test_initialization(self, broker_manager):
        """Test broker manager initialization."""
        assert len(broker_manager._brokers) == 0
        assert len(broker_manager._broker_adapters) == 0
        assert broker_manager._message_processor is not None

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

        assert broker_id in broker_manager._brokers
        assert broker_id in broker_manager._broker_adapters
        assert broker_manager._broker_adapters[broker_id].broker_type == BrokerType.INTERACTIVE_BROKERS

    @pytest.mark.asyncio
    async def test_get_broker_status(self, broker_manager):
        """Test getting broker status."""
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
        
        status = broker_manager.get_broker_status(broker_id)
        assert isinstance(status, dict)
        assert status['broker_id'] == broker_id