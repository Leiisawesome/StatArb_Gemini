import pytest
from datetime import datetime

from core_engine.type_definitions.orders import Order, OrderSide, OrderType, OrderStatus


class FakeEnhancedIBKRAdapter:
    def __init__(self):
        self.connected = False

    async def connect(self):
        self.connected = True
        return True

    async def disconnect(self):
        self.connected = False

    def is_market_open(self):
        return True

    async def get_market_clock(self):
        return {"timestamp": datetime.now(), "is_open": True}

    async def get_latest_quote(self, symbol: str):
        return {"symbol": symbol, "bid_price": 100.0, "ask_price": 100.1, "last_price": 100.05}

    def validate_order_params(self, symbol, quantity, side, order_type, limit_price=None, stop_price=None):
        if not symbol:
            return False, "symbol required"
        if quantity <= 0:
            return False, "quantity must be > 0"
        if side not in {OrderSide.BUY, OrderSide.SELL}:
            return False, "invalid side"
        if order_type == OrderType.LIMIT and (limit_price is None or limit_price <= 0):
            return False, "invalid limit"
        if order_type == OrderType.STOP and (stop_price is None or stop_price <= 0):
            return False, "invalid stop"
        return True, ""

    async def submit_stop_order(self, symbol: str, quantity: float, side: OrderSide, stop_price: float):
        valid, msg = self.validate_order_params(symbol, quantity, side, OrderType.STOP, stop_price=stop_price)
        if not valid:
            raise ValueError(msg)
        return Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.STOP,
            stop_price=stop_price,
            status=OrderStatus.SUBMITTED,
        )


@pytest.mark.asyncio
async def test_market_status_and_clock():
    adapter = FakeEnhancedIBKRAdapter()
    assert await adapter.connect() is True

    assert adapter.is_market_open() is True
    clock = await adapter.get_market_clock()
    assert clock["is_open"] is True
    assert "timestamp" in clock

    await adapter.disconnect()


@pytest.mark.asyncio
async def test_market_data_and_quotes():
    adapter = FakeEnhancedIBKRAdapter()
    await adapter.connect()

    quote = await adapter.get_latest_quote("AAPL")
    assert quote["symbol"] == "AAPL"
    assert quote["ask_price"] >= quote["bid_price"]
    assert quote["last_price"] > 0

    await adapter.disconnect()


def test_order_validation():
    adapter = FakeEnhancedIBKRAdapter()

    ok, _ = adapter.validate_order_params("AAPL", 1, OrderSide.BUY, OrderType.MARKET)
    assert ok is True

    ok, _ = adapter.validate_order_params("", 1, OrderSide.BUY, OrderType.MARKET)
    assert ok is False

    ok, _ = adapter.validate_order_params("AAPL", 0, OrderSide.BUY, OrderType.MARKET)
    assert ok is False

    ok, _ = adapter.validate_order_params("AAPL", 1, OrderSide.BUY, OrderType.LIMIT, limit_price=0)
    assert ok is False


@pytest.mark.asyncio
async def test_stop_orders():
    adapter = FakeEnhancedIBKRAdapter()
    await adapter.connect()

    order = await adapter.submit_stop_order("SPY", 2, OrderSide.SELL, stop_price=95.0)
    assert order.order_type == OrderType.STOP
    assert order.stop_price == 95.0
    assert order.status == OrderStatus.SUBMITTED

    with pytest.raises(ValueError):
        await adapter.submit_stop_order("SPY", 2, OrderSide.SELL, stop_price=0)

    await adapter.disconnect()
