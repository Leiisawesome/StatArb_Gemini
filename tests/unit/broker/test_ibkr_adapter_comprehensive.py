"""
Focused unit tests for IBKRAdapter against current async interface.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter
from core_engine.type_definitions.broker_types import OrderSide, OrderType, OrderStatus


@pytest.fixture
def mock_config():
    config = Mock()
    config.host = "127.0.0.1"
    config.port = 7497
    config.client_id = 1
    config.paper_trading = True
    return config


@pytest.fixture
def adapter(mock_config):
    with patch("core_engine.broker.adapters.ibkr_adapter.IBKRWrapper") as wrapper_cls, patch(
        "core_engine.broker.adapters.ibkr_adapter.IBKRClient"
    ) as client_cls:
        wrapper = Mock()
        wrapper.connection_ready = Mock()
        wrapper.connection_ready.is_set.return_value = True
        wrapper.next_order_id = 1000
        wrapper.connected = True
        wrapper.errors = []
        wrapper.orders = {}
        wrapper.positions = {}
        wrapper.account_values = {}

        client = Mock()
        client.isConnected.return_value = True

        wrapper_cls.return_value = wrapper
        client_cls.return_value = client

        instance = IBKRAdapter(mock_config)
        yield instance


@pytest.mark.asyncio
async def test_connect_success(adapter):
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await adapter.connect()

    assert result is True
    assert adapter._connected is True
    adapter.client.connect.assert_called_once_with("127.0.0.1", 7497, 1)
    adapter.client.reqMarketDataType.assert_called_once_with(3)
    adapter.client.reqAccountSummary.assert_called_once()
    adapter.client.reqPositions.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect(adapter):
    adapter._connected = True
    await adapter.disconnect()
    assert adapter._connected is False
    adapter.client.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_check_connection_health(adapter):
    adapter._connected = True
    health = await adapter.check_connection_health()

    assert health["status"] == "healthy"
    assert health["connected"] is True
    assert health["next_order_id"] == 1000


@pytest.mark.asyncio
async def test_submit_market_order(adapter):
    adapter._connected = True
    adapter.wrapper.next_order_id = 1000

    with patch.object(adapter, "_create_stock_contract", return_value=Mock()):
        order = await adapter.submit_market_order("TSLA", 100, OrderSide.BUY)

    assert order.symbol == "TSLA"
    assert order.order_type == OrderType.MARKET
    assert order.status == OrderStatus.SUBMITTED
    assert order.order_id == "1000"
    adapter.client.placeOrder.assert_called_once()


@pytest.mark.asyncio
async def test_submit_limit_order(adapter):
    adapter._connected = True
    adapter.wrapper.next_order_id = 2000

    with patch.object(adapter, "_create_stock_contract", return_value=Mock()):
        order = await adapter.submit_limit_order("AAPL", 50, OrderSide.SELL, 195.5)

    assert order.symbol == "AAPL"
    assert order.order_type == OrderType.LIMIT
    assert order.price == 195.5
    assert order.order_id == "2000"


@pytest.mark.asyncio
async def test_cancel_order(adapter):
    result = await adapter.cancel_order("1234")

    assert result is True
    adapter.client.cancelOrder.assert_called_once_with(1234)


@pytest.mark.asyncio
async def test_cancel_all_orders_uses_global_cancel(adapter):
    result = await adapter.cancel_all_orders()

    assert result is True
    adapter.client.reqGlobalCancel.assert_called_once()


@pytest.mark.asyncio
async def test_get_order_returns_none_for_missing(adapter):
    adapter.wrapper.orders = {}
    with patch("asyncio.sleep", new_callable=AsyncMock):
        order = await adapter.get_order("999")

    assert order is None
    adapter.client.reqOpenOrders.assert_called_once()
