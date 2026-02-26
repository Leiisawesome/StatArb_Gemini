import pytest
from datetime import datetime, timedelta


class FakeHistoricalAdapter:
    async def connect(self):
        return True

    async def disconnect(self):
        return None

    async def get_historical_bars(self, symbol: str, timeframe: str, limit: int):
        now = datetime(2025, 1, 15, 16, 0)
        bars = []
        for idx in range(limit):
            base = 100.0 + idx
            bars.append(
                {
                    "timestamp": now - timedelta(minutes=limit - idx),
                    "open": base,
                    "high": base + 1.0,
                    "low": base - 1.0,
                    "close": base + 0.5,
                    "volume": 10_000 + idx,
                }
            )
        return bars


@pytest.mark.asyncio
async def test_get_1min_bars():
    adapter = FakeHistoricalAdapter()
    await adapter.connect()

    bars = await adapter.get_historical_bars("SPY", "1Min", 60)

    assert len(bars) == 60
    assert all(bar["high"] >= bar["open"] >= bar["low"] for bar in bars)
    assert all(bar["volume"] >= 0 for bar in bars)

    await adapter.disconnect()


@pytest.mark.asyncio
async def test_get_daily_bars():
    adapter = FakeHistoricalAdapter()
    await adapter.connect()

    bars = await adapter.get_historical_bars("AAPL", "1Day", 30)

    assert len(bars) == 30
    assert bars[0]["timestamp"] < bars[-1]["timestamp"]
    assert all(bar["close"] > 0 for bar in bars)

    await adapter.disconnect()
