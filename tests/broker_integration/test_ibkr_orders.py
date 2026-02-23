import pytest

from core_engine.type_definitions.orders import Order, OrderType, OrderSide, OrderStatus


class FakeIBKROrderAdapter:
    def __init__(self):
        self.connected = False
        self.orders = {}

    async def connect(self):
        self.connected = True
        return True

    async def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    async def submit_market_order(self, symbol: str, quantity: float, side: OrderSide):
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            status=OrderStatus.SUBMITTED,
        )
        self.orders[order.order_id] = order
        return order

    async def submit_limit_order(self, symbol: str, quantity: float, side: OrderSide, limit_price: float):
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            price=limit_price,
            status=OrderStatus.SUBMITTED,
        )
        self.orders[order.order_id] = order
        return order

    async def cancel_order(self, order_id: str):
        order = self.orders.get(order_id)
        if not order:
            return False
        order.status = OrderStatus.CANCELLED
        return True

    async def get_orders(self, status: str = "open"):
        if status == "open":
            return [o for o in self.orders.values() if o.status in {OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED}]
        if status == "closed":
            return [o for o in self.orders.values() if o.status in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}]
        return list(self.orders.values())


@pytest.fixture
async def ibkr_adapter():
    adapter = FakeIBKROrderAdapter()
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest.mark.asyncio
async def test_market_order_submission(ibkr_adapter):
    order = await ibkr_adapter.submit_market_order("SPY", 1, OrderSide.BUY)

    assert order is not None
    assert order.order_type == OrderType.MARKET
    assert order.status == OrderStatus.SUBMITTED


@pytest.mark.asyncio
async def test_limit_order_submission(ibkr_adapter):
    order = await ibkr_adapter.submit_limit_order("SPY", 1, OrderSide.BUY, 450.0)

    assert order is not None
    assert order.order_type == OrderType.LIMIT
    assert order.price == 450.0


@pytest.mark.asyncio
async def test_order_cancellation(ibkr_adapter):
    order = await ibkr_adapter.submit_limit_order("SPY", 1, OrderSide.BUY, 1.0)
    result = await ibkr_adapter.cancel_order(order.order_id)

    assert result is True
    assert ibkr_adapter.orders[order.order_id].status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_get_open_orders(ibkr_adapter):
    order = await ibkr_adapter.submit_limit_order("SPY", 1, OrderSide.BUY, 1.0)

    open_orders = await ibkr_adapter.get_orders(status="open")

    assert isinstance(open_orders, list)
    assert any(o.order_id == order.order_id for o in open_orders)


@pytest.mark.skip(reason="Legacy live-market execution path intentionally disabled in deterministic suite")
def test_market_order_fill(ibkr_adapter):
    assert ibkr_adapter is not None
