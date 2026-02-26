import pytest
from datetime import datetime

from core_engine.type_definitions.orders import Order, OrderType, OrderSide, OrderStatus


class FakeLimitOrderAdapter:
    def __init__(self):
        self.orders = {}

    async def connect(self):
        return True

    async def disconnect(self):
        return None

    async def submit_limit_order(self, symbol: str, quantity: float, side: OrderSide, limit_price: float) -> Order:
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            price=limit_price,
            status=OrderStatus.SUBMITTED,
            timestamp=datetime.now(),
        )
        self.orders[order.order_id] = order
        return order

    async def get_order(self, order_id: str):
        return self.orders.get(order_id)

    async def get_orders(self, status: str = "open"):
        if status == "open":
            return [o for o in self.orders.values() if o.status in {OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED}]
        if status == "closed":
            return [o for o in self.orders.values() if o.status in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}]
        return list(self.orders.values())

    async def cancel_order(self, order_id: str):
        order = self.orders.get(order_id)
        if order is None:
            return False
        order.status = OrderStatus.CANCELLED
        return True


@pytest.mark.asyncio
async def test_limit_order_lifecycle():
    adapter = FakeLimitOrderAdapter()
    await adapter.connect()

    order = await adapter.submit_limit_order("SPY", 1, OrderSide.BUY, 100.0)
    assert order.order_type == OrderType.LIMIT
    assert order.status == OrderStatus.SUBMITTED

    fetched = await adapter.get_order(order.order_id)
    assert fetched is not None
    assert fetched.order_id == order.order_id

    open_orders = await adapter.get_orders(status="open")
    assert any(o.order_id == order.order_id for o in open_orders)

    assert await adapter.cancel_order(order.order_id) is True

    cancelled = await adapter.get_order(order.order_id)
    assert cancelled.status == OrderStatus.CANCELLED

    await adapter.disconnect()
