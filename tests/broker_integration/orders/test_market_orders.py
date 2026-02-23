import pytest
from datetime import datetime

from core_engine.type_definitions.orders import Order, OrderType, OrderSide, OrderStatus
from core_engine.type_definitions.broker_types import Position


class FakeMarketOrderAdapter:
    def __init__(self):
        self.orders = {}
        self.positions = {}

    async def connect(self):
        return True

    async def disconnect(self):
        return None

    async def submit_market_order(self, symbol: str, quantity: float, side: OrderSide) -> Order:
        fill_price = 500.0
        signed_qty = quantity if side == OrderSide.BUY else -quantity

        position_qty = self.positions.get(symbol, 0.0) + signed_qty
        if position_qty == 0:
            self.positions.pop(symbol, None)
        else:
            self.positions[symbol] = position_qty

        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            filled_quantity=quantity,
            average_price=fill_price,
            timestamp=datetime.now(),
        )
        self.orders[order.order_id] = order
        return order

    async def get_order(self, order_id: str):
        return self.orders.get(order_id)

    async def get_positions(self):
        result = []
        for symbol, quantity in self.positions.items():
            result.append(
                Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_entry_price=500.0,
                    market_value=quantity * 500.0,
                    unrealized_pl=0.0,
                    unrealized_plpc=0.0,
                    current_price=500.0,
                    side="long" if quantity >= 0 else "short",
                    cost_basis=quantity * 500.0,
                )
            )
        return result


@pytest.mark.asyncio
async def test_market_order_buy_sell():
    adapter = FakeMarketOrderAdapter()
    await adapter.connect()

    buy_order = await adapter.submit_market_order("SPY", 1, OrderSide.BUY)
    assert buy_order.status == OrderStatus.FILLED
    assert buy_order.filled_quantity == 1

    positions_after_buy = await adapter.get_positions()
    assert any(p.symbol == "SPY" and p.quantity == 1 for p in positions_after_buy)

    sell_order = await adapter.submit_market_order("SPY", 1, OrderSide.SELL)
    assert sell_order.status == OrderStatus.FILLED

    positions_after_sell = await adapter.get_positions()
    assert all(p.symbol != "SPY" for p in positions_after_sell)

    await adapter.disconnect()
