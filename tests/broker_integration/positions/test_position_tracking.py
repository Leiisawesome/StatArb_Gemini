import pytest

from core_engine.type_definitions.broker_types import Position
from core_engine.type_definitions.orders import OrderSide


class FakePositionAdapter:
    def __init__(self):
        self.positions = {}

    async def connect(self):
        return True

    async def disconnect(self):
        return None

    async def submit_market_order(self, symbol: str, quantity: float, side: OrderSide):
        signed = quantity if side == OrderSide.BUY else -quantity
        self.positions[symbol] = self.positions.get(symbol, 0.0) + signed
        if self.positions[symbol] == 0:
            del self.positions[symbol]

    async def get_positions(self):
        result = []
        for symbol, quantity in self.positions.items():
            result.append(
                Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_entry_price=100.0,
                    market_value=quantity * 100.0,
                    unrealized_pl=0.0,
                    unrealized_plpc=0.0,
                    current_price=100.0,
                    side="long" if quantity >= 0 else "short",
                    cost_basis=quantity * 100.0,
                )
            )
        return result


@pytest.mark.asyncio
async def test_position_tracking():
    adapter = FakePositionAdapter()
    await adapter.connect()

    await adapter.submit_market_order("SPY", 2, OrderSide.BUY)
    positions = await adapter.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "SPY"
    assert positions[0].quantity == 2

    await adapter.submit_market_order("SPY", 1, OrderSide.SELL)
    positions = await adapter.get_positions()
    assert len(positions) == 1
    assert positions[0].quantity == 1

    await adapter.submit_market_order("SPY", 1, OrderSide.SELL)
    positions = await adapter.get_positions()
    assert positions == []

    await adapter.disconnect()
