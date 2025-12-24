import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from livepapertest.engine.polygon_rest_warmup_adapter import PolygonRestWarmupAdapter, PolygonWarmupConfig

@pytest.fixture
def mock_polygon_svc():
    svc = AsyncMock()
    # Create dummy data
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=10, freq="1min")
    df = pd.DataFrame({
        "open": [100.0] * 10,
        "high": [101.0] * 10,
        "low": [99.0] * 10,
        "close": [100.5] * 10,
        "volume": [1000] * 10
    }, index=dates)
    svc.get_bars.return_value = df
    return svc

@pytest.mark.asyncio
async def test_polygon_warmup_get_data(mock_polygon_svc):
    adapter = PolygonRestWarmupAdapter()
    adapter._svc = mock_polygon_svc
    
    df = await adapter.get_warmup_data("AAPL", bars=5)
    
    assert len(df) == 5
    assert "timestamp" in df.columns
    assert df["timestamp"].iloc[-1] > df["timestamp"].iloc[0]
    assert adapter._last_ts_by_symbol["AAPL"] == df["timestamp"].iloc[-1]
    assert adapter.last_warmup_timestamp("AAPL") == df["timestamp"].iloc[-1]

@pytest.mark.asyncio
async def test_polygon_warmup_missing_columns(mock_polygon_svc):
    # Return DF with missing columns
    mock_polygon_svc.get_bars.return_value = pd.DataFrame({
        "open": [100.0]
    }, index=[datetime.now(timezone.utc)])
    
    adapter = PolygonRestWarmupAdapter()
    adapter._svc = mock_polygon_svc
    
    df = await adapter.get_warmup_data("AAPL", bars=1)
    assert "high" in df.columns
    assert pd.isna(df["high"].iloc[0])
    mock_polygon_svc.get_bars.return_value = pd.DataFrame()
    adapter = PolygonRestWarmupAdapter()
    adapter._svc = mock_polygon_svc
    
    df = await adapter.get_warmup_data("AAPL", bars=5)
    assert df.empty
    assert "timestamp" in df.columns

@pytest.mark.asyncio
async def test_polygon_warmup_zero_bars():
    adapter = PolygonRestWarmupAdapter()
    df = await adapter.get_warmup_data("AAPL", bars=0)
    assert df.empty
    assert "timestamp" in df.columns

@pytest.mark.asyncio
async def test_polygon_warmup_initialization():
    with patch("livepapertest.engine.polygon_rest_warmup_adapter.create_polygon_rest_service", new_callable=AsyncMock) as mock_create:
        mock_svc = AsyncMock()
        mock_create.return_value = mock_svc
        
        adapter = PolygonRestWarmupAdapter()
        await adapter.initialize()
        
        assert adapter._svc == mock_svc
        mock_create.assert_called_once()
        
        await adapter.close()
        assert adapter._svc is None
        mock_svc.close.assert_called_once()
