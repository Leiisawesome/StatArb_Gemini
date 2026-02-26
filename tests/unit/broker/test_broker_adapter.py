import pytest
from datetime import datetime

from core_engine.broker.broker_adapter import BrokerAdapter
from core_engine.system.interfaces import RegimeContext
from core_engine.type_definitions.broker_types import (
    AccountInfo,
    Order,
    OrderSide,
    OrderType,
    Position,
)


class DummyAdapter:
    def __init__(self):
        self.connected = False
        self.last_call = None

    async def connect(self):
        self.connected = True
        return True

    async def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    async def check_connection_health(self):
        return {"connected": self.connected, "latency": 0.001}

    async def get_latest_quote(self, symbol):
        return {"bid_price": 99.0, "ask_price": 101.0, "timestamp": datetime.now()}

    def is_market_open(self):
        return True

    async def submit_market_order(self, symbol, quantity, side):
        self.last_call = ("market", symbol, quantity, side)
        return Order(symbol=symbol, side=side, quantity=quantity, order_type=OrderType.MARKET)

    async def submit_limit_order(self, symbol, quantity, side, limit_price):
        self.last_call = ("limit", symbol, quantity, side, limit_price)
        return Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            price=limit_price,
        )

    async def cancel_order(self, order_id):
        return True

    async def cancel_all_orders(self):
        return True

    async def get_order(self, order_id):
        return None

    async def get_orders(self, status="open"):
        return []

    async def get_positions(self):
        return [
            Position(
                symbol="AAPL",
                quantity=10,
                avg_entry_price=100.0,
                market_value=1000.0,
                unrealized_pl=0.0,
                unrealized_plpc=0.0,
                current_price=100.0,
                side="long",
                cost_basis=1000.0,
            )
        ]

    async def get_position(self, symbol):
        return None

    async def get_account_info(self):
        return AccountInfo(
            account_id="DUMMY",
            cash=1000.0,
            buying_power=2000.0,
            portfolio_value=1000.0,
            equity=1000.0,
        )

    def broker_name(self):
        return "Dummy"


@pytest.mark.asyncio
async def test_connect_disconnect_and_health():
    adapter = BrokerAdapter(DummyAdapter())

    assert await adapter.connect() is True
    assert adapter.is_connected() is True
    health = await adapter.check_health()
    assert health["connected"] is True

    await adapter.disconnect()
    assert adapter.is_connected() is False


@pytest.mark.asyncio
async def test_submit_market_order_routes_to_market():
    base = DummyAdapter()
    adapter = BrokerAdapter(base)

    order = await adapter.submit_order("AAPL", 5, OrderSide.BUY, OrderType.MARKET)

    assert order.order_type == OrderType.MARKET
    assert base.last_call[0] == "market"


@pytest.mark.asyncio
async def test_submit_limit_order_requires_price():
    adapter = BrokerAdapter(DummyAdapter())

    with pytest.raises(ValueError):
        await adapter.submit_order("AAPL", 5, OrderSide.BUY, OrderType.LIMIT)


@pytest.mark.asyncio
async def test_high_volatility_forces_market_to_limit():
    base = DummyAdapter()
    adapter = BrokerAdapter(base)

    adapter.update_regime_context(
        RegimeContext(
            primary_regime="trend",
            volatility_regime="high_volatility",
            regime_confidence=0.8,
            regime_start_time=datetime.now(),
            regime_duration_minutes=30.0,
        )
    )

    order = await adapter.submit_order("AAPL", 10, OrderSide.BUY, OrderType.MARKET)

    assert order.order_type == OrderType.LIMIT
    assert order.price == pytest.approx(102.01)
    assert base.last_call[0] == "limit"


@pytest.mark.asyncio
async def test_account_and_position_passthrough():
    adapter = BrokerAdapter(DummyAdapter())

    account = await adapter.get_account_info()
    positions = await adapter.get_positions()

    assert account.account_id == "DUMMY"
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"


def test_broker_name_passthrough():
    adapter = BrokerAdapter(DummyAdapter())
    assert adapter.broker_name() == "Dummy"
