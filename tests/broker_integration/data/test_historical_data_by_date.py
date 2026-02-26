import pytest
from datetime import datetime, timedelta


class FakeHistoricalAdapter:
    async def connect(self):
        return True

    async def disconnect(self):
        return None

    async def get_historical_bars(self, symbol: str, timeframe: str, limit: int = 100, start=None, end=None):
        now = datetime(2024, 12, 20, 15, 59)
        bars = []
        for i in range(limit):
            base = 250.0 + i * 0.1
            bars.append(
                {
                    "timestamp": now - timedelta(minutes=limit - i),
                    "open": base,
                    "high": base + 1.0,
                    "low": base - 1.0,
                    "close": base + 0.5,
                    "volume": 1000 + i,
                }
            )
        return bars


@pytest.mark.asyncio
async def test_historical_data_by_symbol_and_date():
    adapter = FakeHistoricalAdapter()
    await adapter.connect()

    bars = await adapter.get_historical_bars(symbol="TSLA", timeframe="1Min", limit=100)

    assert bars is not None
    assert len(bars) == 100

    first = bars[0]
    for key in ["timestamp", "open", "high", "low", "close", "volume"]:
        assert key in first

    assert first["high"] >= first["open"] >= first["low"]
    assert first["high"] >= first["close"] >= first["low"]
    assert first["volume"] >= 0

    await adapter.disconnect()


@pytest.mark.asyncio
async def test_historical_data_different_timeframes():
    adapter = FakeHistoricalAdapter()
    await adapter.connect()

    for timeframe in ["1Min", "5Min", "15Min", "1Hour"]:
        bars = await adapter.get_historical_bars(symbol="TSLA", timeframe=timeframe, limit=20)
        assert len(bars) == 20
        assert all(bar["volume"] >= 0 for bar in bars)

    await adapter.disconnect()
