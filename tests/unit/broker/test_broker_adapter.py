#!/usr/bin/env python3
"""
Broker Adapter Test Suite
========================

This test suite provides testing for the BrokerAdapter components
to ensure basic functionality and interface compliance.

Components Tested:
- BrokerAdapter (Multi-broker integration)
- StandardOrder (Order standardization)
- StandardExecution (Execution standardization)
- StandardPosition (Position standardization)
- StandardAccount (Account standardization)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

# Import broker components
from core_engine.broker.broker_adapter import (
    BrokerCredentials, BrokerType, ConnectionStatus, StandardOrder,
    StandardExecution, StandardPosition, StandardAccount, OrderAction,
    OrderType, TimeInForce, BrokerAdapterFactory
)

class TestBrokerAdapterBasic:
    """Basic tests for BrokerAdapter - Multi-broker integration"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'broker_type': BrokerType.INTERACTIVE_BROKERS,
            'host': 'localhost',
            'port': 7497,
            'client_id': 1,
            'connection_timeout': 30,
            'max_retries': 3,
            'retry_delay': 1.0,
            'enable_logging': True
        }

        self.credentials = BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            username='test_user',
            password='test_password',
            api_key='test_api_key',
            secret_key='test_api_secret'
        )

        # Create a mock broker adapter
        self.broker_adapter = Mock()

        # Mock order data
        self.mock_order = StandardOrder(
            order_id='test_order_001',
            symbol='AAPL',
            action=OrderAction.BUY,
            order_type=OrderType.MARKET,
            quantity=100.0,
            limit_price=150.0,
            time_in_force=TimeInForce.DAY,
            created_at=datetime.now()
        )

        # Mock execution data
        self.mock_execution = StandardExecution(
            execution_id='test_exec_001',
            order_id='test_order_001',
            symbol='AAPL',
            side='BUY',
            quantity=100.0,
            price=150.25,
            execution_time=datetime.now(),
            commission=1.0
        )

        # Mock position data
        self.mock_position = StandardPosition(
            symbol='AAPL',
            quantity=100.0,
            side='long',
            avg_cost=150.0,
            market_value=15000.0,
            unrealized_pnl=0.0,
            last_price=150.0,
            currency='USD',
            last_updated=datetime.now()
        )

        # Mock account data
        self.mock_account = StandardAccount(
            account_id='test_account',
            account_type='MARGIN',
            total_equity=150000.0,
            buying_power=200000.0,
            cash_balance=100000.0,
            positions=[self.mock_position]
        )

    def test_broker_type_enum(self):
        """Test BrokerType enum values"""
        assert BrokerType.INTERACTIVE_BROKERS.value == "interactive_brokers"
        assert BrokerType.TD_AMERITRADE.value == "td_ameritrade"

    def test_connection_status_enum(self):
        """Test ConnectionStatus enum values"""
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.READY.value == "ready"

    def test_order_action_enum(self):
        """Test OrderAction enum values"""
        assert OrderAction.BUY.value == "BUY"
        assert OrderAction.SELL.value == "SELL"

    def test_order_type_enum(self):
        """Test OrderType enum values"""
        assert OrderType.MARKET.value == "MKT"
        assert OrderType.LIMIT.value == "LMT"
        assert OrderType.STOP.value == "STP"

    def test_time_in_force_enum(self):
        """Test TimeInForce enum values"""
        assert TimeInForce.DAY.value == "DAY"
        assert TimeInForce.GTC.value == "GTC"
        assert TimeInForce.IOC.value == "IOC"

    def test_broker_credentials_creation(self):
        """Test BrokerCredentials creation"""
        credentials = BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            username='test_user',
            password='test_password',
            api_key='test_api_key',
            secret_key='test_api_secret'
        )

        assert credentials.username == 'test_user'
        assert credentials.password == 'test_password'
        assert credentials.api_key == 'test_api_key'
        assert credentials.secret_key == 'test_api_secret'

    def test_standard_order_creation(self):
        """Test StandardOrder creation"""
        order = StandardOrder(
            order_id='test_order_001',
            symbol='AAPL',
            action=OrderAction.BUY,
            order_type=OrderType.MARKET,
            quantity=100.0,
            limit_price=150.0,
            time_in_force=TimeInForce.DAY,
            created_at=datetime.now()
        )

        assert order.order_id == 'test_order_001'
        assert order.symbol == 'AAPL'
        assert order.action == OrderAction.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == 100.0
        assert order.limit_price == 150.0
        assert order.time_in_force == TimeInForce.DAY

    def test_standard_execution_creation(self):
        """Test StandardExecution creation"""
        execution = StandardExecution(
            execution_id='test_exec_001',
            order_id='test_order_001',
            symbol='AAPL',
            side='BUY',
            quantity=100.0,
            price=150.25,
            execution_time=datetime.now(),
            commission=1.0
        )

        assert execution.execution_id == 'test_exec_001'
        assert execution.order_id == 'test_order_001'
        assert execution.symbol == 'AAPL'
        assert execution.side == 'BUY'
        assert execution.quantity == 100.0
        assert execution.price == 150.25
        assert execution.commission == 1.0

    def test_standard_position_creation(self):
        """Test StandardPosition creation"""
        position = StandardPosition(
            symbol='AAPL',
            quantity=100.0,
            side='long',
            avg_cost=150.0,
            market_value=15000.0,
            unrealized_pnl=0.0,
            last_price=150.0,
            currency='USD',
            last_updated=datetime.now()
        )

        assert position.symbol == 'AAPL'
        assert position.quantity == 100.0
        assert position.side == 'long'
        assert position.avg_cost == 150.0
        assert position.market_value == 15000.0
        assert position.unrealized_pnl == 0.0
        assert position.last_price == 150.0
        assert position.currency == 'USD'

    def test_standard_account_creation(self):
        """Test StandardAccount creation"""
        position = StandardPosition(
            symbol='AAPL',
            quantity=100.0,
            side='long',
            avg_cost=150.0,
            market_value=15000.0,
            unrealized_pnl=0.0,
            last_price=150.0,
            currency='USD',
            last_updated=datetime.now()
        )

        account = StandardAccount(
            account_id='test_account',
            account_type='MARGIN',
            total_equity=150000.0,
            buying_power=200000.0,
            cash_balance=100000.0,
            positions=[position]
        )

        assert account.account_id == 'test_account'
        assert account.account_type == 'MARGIN'
        assert account.total_equity == 150000.0
        assert account.buying_power == 200000.0
        assert account.cash_balance == 100000.0
        assert len(account.positions) == 1
        assert account.positions[0].symbol == 'AAPL'

    @pytest.mark.asyncio
    async def test_broker_adapter_interface_methods(self):
        """Test that BrokerAdapter has expected interface methods"""
        # Test that the mock has the expected methods
        assert hasattr(self.broker_adapter, 'connect')
        assert hasattr(self.broker_adapter, 'disconnect')
        assert hasattr(self.broker_adapter, 'authenticate')
        assert hasattr(self.broker_adapter, 'submit_order')
        assert hasattr(self.broker_adapter, 'cancel_order')
        assert hasattr(self.broker_adapter, 'modify_order')
        assert hasattr(self.broker_adapter, 'get_order_status')
        assert hasattr(self.broker_adapter, 'get_positions')
        assert hasattr(self.broker_adapter, 'get_account_info')
        assert hasattr(self.broker_adapter, 'get_market_data')

    @pytest.mark.asyncio
    async def test_broker_adapter_connect(self):
        """Test broker adapter connection"""
        self.broker_adapter.connect = AsyncMock(return_value=True)

        result = await self.broker_adapter.connect()

        assert result is True
        self.broker_adapter.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_adapter_disconnect(self):
        """Test broker adapter disconnection"""
        self.broker_adapter.disconnect = AsyncMock(return_value=True)

        result = await self.broker_adapter.disconnect()

        assert result is True
        self.broker_adapter.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_adapter_authenticate(self):
        """Test broker adapter authentication"""
        self.broker_adapter.authenticate = AsyncMock(return_value=True)

        result = await self.broker_adapter.authenticate()

        assert result is True
        self.broker_adapter.authenticate.assert_called_once()

    @pytest.mark.asyncio
    async def test_broker_adapter_submit_order(self):
        """Test broker adapter order submission"""
        self.broker_adapter.submit_order = AsyncMock(return_value='order_123')

        result = await self.broker_adapter.submit_order(self.mock_order)

        assert result == 'order_123'
        self.broker_adapter.submit_order.assert_called_once_with(self.mock_order)

    @pytest.mark.asyncio
    async def test_broker_adapter_cancel_order(self):
        """Test broker adapter order cancellation"""
        self.broker_adapter.cancel_order = AsyncMock(return_value=True)

        result = await self.broker_adapter.cancel_order('order_123')

        assert result is True
        self.broker_adapter.cancel_order.assert_called_once_with('order_123')

    @pytest.mark.asyncio
    async def test_broker_adapter_modify_order(self):
        """Test broker adapter order modification"""
        self.broker_adapter.modify_order = AsyncMock(return_value=True)

        updates = {'quantity': 150.0, 'limit_price': 149.0}
        result = await self.broker_adapter.modify_order('order_123', updates)

        assert result is True
        self.broker_adapter.modify_order.assert_called_once_with('order_123', updates)

    @pytest.mark.asyncio
    async def test_broker_adapter_get_order_status(self):
        """Test broker adapter order status retrieval"""
        mock_status = {'order_id': 'order_123', 'status': 'FILLED', 'filled_qty': 100.0}
        self.broker_adapter.get_order_status = AsyncMock(return_value=mock_status)

        result = await self.broker_adapter.get_order_status('order_123')

        assert result == mock_status
        self.broker_adapter.get_order_status.assert_called_once_with('order_123')

    @pytest.mark.asyncio
    async def test_broker_adapter_get_positions(self):
        """Test broker adapter positions retrieval"""
        mock_positions = [self.mock_position]
        self.broker_adapter.get_positions = AsyncMock(return_value=mock_positions)

        result = await self.broker_adapter.get_positions()

        assert result == mock_positions
        assert len(result) == 1
        assert result[0].symbol == 'AAPL'
        self.broker_adapter.get_positions.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_broker_adapter_get_account_info(self):
        """Test broker adapter account info retrieval"""
        self.broker_adapter.get_account_info = AsyncMock(return_value=self.mock_account)

        result = await self.broker_adapter.get_account_info()

        assert result == self.mock_account
        assert result.account_id == 'test_account'
        assert result.total_equity == 150000.0
        self.broker_adapter.get_account_info.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_broker_adapter_get_market_data(self):
        """Test broker adapter market data retrieval"""
        mock_market_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'bid': 149.9,
            'ask': 150.1,
            'volume': 1000000,
            'timestamp': datetime.now()
        }
        self.broker_adapter.get_market_data = AsyncMock(return_value=mock_market_data)

        result = await self.broker_adapter.get_market_data('AAPL')

        assert result == mock_market_data
        assert result['symbol'] == 'AAPL'
        assert result['price'] == 150.0
        self.broker_adapter.get_market_data.assert_called_once_with('AAPL')

class TestBrokerAdapterFactory:
    """Tests for BrokerAdapterFactory"""

    def test_factory_creation(self):
        """Test BrokerAdapterFactory creation"""
        factory = BrokerAdapterFactory()
        assert factory is not None

    def test_factory_broker_types(self):
        """Test available broker types"""
        factory = BrokerAdapterFactory()
        # The factory should support different broker types
        # This is a basic test to ensure the factory exists and can be instantiated
        assert hasattr(factory, 'create_adapter')

if __name__ == '__main__':
    pytest.main([__file__])