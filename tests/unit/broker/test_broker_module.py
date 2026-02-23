import pytest
from datetime import datetime

from core_engine.broker.broker_adapter import BrokerAdapter
from core_engine.broker.broker_manager import BrokerManager
from core_engine.system.interfaces import RegimeContext
from core_engine.type_definitions.broker_types import (
    AccountInfo,
    Order,
    OrderSide,
    OrderType,
    Position,
)


class DummyAdapter:
    def __init__(self, name: str, equity: float = 1000.0):
        self.name = name
        self.equity = equity
        self.connected = False
        self.regime = None

    async def connect(self):
        self.connected = True
        return True

    async def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    async def check_connection_health(self):
        return {"connected": self.connected}

    async def get_latest_quote(self, symbol):
        return {"bid_price": 99.0, "ask_price": 101.0, "timestamp": datetime.now()}

    def is_market_open(self):
        return True

    async def submit_market_order(self, symbol, quantity, side):
        return Order(symbol=symbol, side=side, quantity=quantity, order_type=OrderType.MARKET)

    async def submit_limit_order(self, symbol, quantity, side, limit_price):
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
        if self.name == "A":
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
        return [
            Position(
                symbol="AAPL",
                quantity=-3,
                avg_entry_price=100.0,
                market_value=-300.0,
                unrealized_pl=0.0,
                unrealized_plpc=0.0,
                current_price=100.0,
                side="short",
                cost_basis=-300.0,
            )
        ]

    async def get_position(self, symbol):
        return None

    async def get_account_info(self):
        return AccountInfo(
            account_id=f"ACC-{self.name}",
            cash=self.equity,
            buying_power=self.equity * 2,
            portfolio_value=self.equity,
            equity=self.equity,
        )

    def broker_name(self):
        return f"Dummy-{self.name}"


def test_manager_initialization():
    manager = BrokerManager([])
    assert manager.adapters == []


@pytest.mark.asyncio
async def test_submit_order_to_all_returns_orders():
    manager = BrokerManager([
        BrokerAdapter(DummyAdapter("A")),
        BrokerAdapter(DummyAdapter("B")),
    ])

    orders = await manager.submit_order_to_all("MSFT", 5, OrderSide.BUY, OrderType.MARKET)

    assert len(orders) == 2
    assert all(order.symbol == "MSFT" for order in orders)


@pytest.mark.asyncio
async def test_get_total_equity_aggregates_adapters():
    manager = BrokerManager([
        BrokerAdapter(DummyAdapter("A", equity=1500.0)),
        BrokerAdapter(DummyAdapter("B", equity=2500.0)),
    ])

    total_equity = await manager.get_total_equity()

    assert total_equity == 4000.0


@pytest.mark.asyncio
async def test_cancel_all_global_success():
    manager = BrokerManager([
        BrokerAdapter(DummyAdapter("A")),
        BrokerAdapter(DummyAdapter("B")),
    ])

    assert await manager.cancel_all_global() is True


@pytest.mark.asyncio
async def test_aggregated_positions_sum_quantities():
    manager = BrokerManager([
        BrokerAdapter(DummyAdapter("A")),
        BrokerAdapter(DummyAdapter("B")),
    ])

    aggregated = await manager.get_aggregated_positions()

    assert aggregated["AAPL"] == 7


@pytest.mark.asyncio
async def test_update_regime_propagates_to_all_adapters():
    adapter_a = BrokerAdapter(DummyAdapter("A"))
    adapter_b = BrokerAdapter(DummyAdapter("B"))
    manager = BrokerManager([adapter_a, adapter_b])

    context = RegimeContext(
        primary_regime="trend",
        volatility_regime="normal",
        regime_confidence=0.9,
        regime_start_time=datetime.now(),
        regime_duration_minutes=10.0,
    )

    await manager.update_regime(context)

    assert adapter_a._regime_context is context
    assert adapter_b._regime_context is context
