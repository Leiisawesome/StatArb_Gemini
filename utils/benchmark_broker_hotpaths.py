import asyncio
import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter


def _build_mock_adapter() -> IBKRAdapter:
    config = SimpleNamespace(
        host="127.0.0.1",
        port=7497,
        client_id=999,
        paper_trading=True,
        account_id="DU_TEST",
    )
    adapter = IBKRAdapter(config)

    adapter.client.reqOpenOrders = Mock(side_effect=lambda: adapter.wrapper.open_orders_ready.set())
    adapter.client.reqPositions = Mock(side_effect=lambda: adapter.wrapper.positions_ready.set())

    now = datetime.now()
    adapter.wrapper.orders = {
        1001: {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10,
            "order_type": "LMT",
            "limit_price": 190.0,
            "stop_price": None,
            "status": "Submitted",
            "avg_fill_price": None,
            "timestamp": now,
        }
    }
    adapter.wrapper.positions = {
        "AAPL": {
            "symbol": "AAPL",
            "position": 10,
            "avg_cost": 188.0,
            "timestamp": now,
        }
    }

    async def fake_quote(symbol: str):
        return {
            "symbol": symbol,
            "bid_price": 189.9,
            "ask_price": 190.1,
            "last_price": 190.0,
            "timestamp": datetime.now(),
        }

    adapter.get_latest_quote = fake_quote
    return adapter


async def main() -> None:
    adapter = _build_mock_adapter()

    t0 = time.perf_counter()
    await adapter.get_orders(status="open")
    t1 = time.perf_counter()
    await adapter.get_orders(status="open")
    t2 = time.perf_counter()

    first_orders_ms = (t1 - t0) * 1000
    second_orders_ms = (t2 - t1) * 1000

    p0 = time.perf_counter()
    await adapter.get_positions()
    p1 = time.perf_counter()
    await adapter.get_positions()
    p2 = time.perf_counter()

    first_positions_ms = (p1 - p0) * 1000
    second_positions_ms = (p2 - p1) * 1000

    print("Broker hot-path benchmark (mocked IBKR)\n")
    print(f"get_orders first call : {first_orders_ms:8.2f} ms")
    print(f"get_orders second call: {second_orders_ms:8.2f} ms")
    if second_orders_ms > 0:
        print(f"orders speedup       : {first_orders_ms / second_orders_ms:8.2f}x")

    print()
    print(f"get_positions first call : {first_positions_ms:8.2f} ms")
    print(f"get_positions second call: {second_positions_ms:8.2f} ms")
    if second_positions_ms > 0:
        print(f"positions speedup       : {first_positions_ms / second_positions_ms:8.2f}x")


if __name__ == "__main__":
    asyncio.run(main())
