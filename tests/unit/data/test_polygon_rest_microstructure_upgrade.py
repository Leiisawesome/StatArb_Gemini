import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pandas as pd
import pytest

from core_engine.data.feeds.polygon_rest import PolygonRestService


@pytest.mark.asyncio
async def test_get_historical_trades_full_fidelity_preserves_microstructure_fields():
    service = PolygonRestService(api_key="test_key")
    service._rest_client = Mock()

    service._rest_client.list_trades.return_value = iter(
        [
            {
                "price": 100.25,
                "size": 10,
                "exchange": 11,
                "conditions": [12, 37],
                "tape": 1,
                "timestamp": 1735723800000000000,
                "sip_timestamp": 1735723800000000000,
                "participant_timestamp": 1735723799999000000,
                "trf_timestamp": 1735723800000000000,
                "id": "trade-abc",
                "sequence_number": 4242,
                "trf_id": 77,
                "correction": 0,
            }
        ]
    )

    start = datetime(2025, 1, 1, 14, 30, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, 14, 31, tzinfo=timezone.utc)

    df = await service.get_historical_trades(
        symbol="AAPL",
        start=start,
        end=end,
        full_fidelity=True,
    )

    assert not df.empty
    assert "event_id" in df.columns
    assert "sequence_number" in df.columns
    assert "sip_timestamp_raw" in df.columns
    assert "participant_timestamp_raw" in df.columns
    assert "trf_timestamp_raw" in df.columns
    assert "trf_id" in df.columns
    assert "correction" in df.columns
    assert df.iloc[0]["event_id"] == "trade-abc"
    assert int(df.iloc[0]["sequence_number"]) == 4242
    assert df.iloc[0]["conditions"] == [12, 37]


@pytest.mark.asyncio
async def test_get_historical_quotes_warns_when_cap_truncates(caplog):
    service = PolygonRestService(api_key="test_key")
    service._rest_client = Mock()

    service._rest_client.list_quotes.return_value = iter(
        [
            {
                "bid_price": 100.0,
                "ask_price": 100.1,
                "bid_size": 1,
                "ask_size": 2,
                "bid_exchange": 11,
                "ask_exchange": 12,
                "timestamp": 1735723800000000000,
            },
            {
                "bid_price": 100.01,
                "ask_price": 100.11,
                "bid_size": 3,
                "ask_size": 4,
                "bid_exchange": 11,
                "ask_exchange": 12,
                "timestamp": 1735723801000000000,
            },
        ]
    )

    start = datetime(2025, 1, 1, 14, 30, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, 14, 31, tzinfo=timezone.utc)

    with caplog.at_level(logging.WARNING, logger="PolygonRestService"):
        df = await service.get_historical_quotes(
            symbol="AAPL",
            start=start,
            end=end,
            limit=1,
            max_pages=1,
        )

    assert len(df) == 1
    assert "truncated at cap=1" in caplog.text


@pytest.mark.asyncio
async def test_trade_quote_snapshots_full_fidelity_adds_quote_age_ms_and_micro_columns():
    service = PolygonRestService(api_key="test_key")

    base_ts = datetime(2025, 1, 1, 14, 30, 0, tzinfo=timezone.utc)

    trades_df = pd.DataFrame(
        {
            "price": [100.0],
            "size": [5.0],
            "exchange": [11],
            "conditions": [[12]],
            "tape": [1],
            "sequence_number": [99],
        },
        index=pd.DatetimeIndex([base_ts]),
    )
    trades_df.index.name = "timestamp"

    quotes_df = pd.DataFrame(
        {
            "bid": [99.9],
            "ask": [100.1],
            "bid_size": [20.0],
            "ask_size": [25.0],
            "bid_exchange": [11],
            "ask_exchange": [12],
            "conditions": [[1]],
            "sequence_number": [501],
        },
        index=pd.DatetimeIndex([base_ts]),
    )
    quotes_df.index.name = "timestamp"

    service.get_historical_trades = AsyncMock(return_value=trades_df)
    service.get_historical_quotes = AsyncMock(return_value=quotes_df)

    snapshot = await service.get_trade_quote_snapshots_1s(
        symbol="AAPL",
        start=base_ts,
        end=base_ts.replace(second=2),
        forward_fill_quotes=True,
        forward_fill_trades=False,
        full_fidelity=True,
    )

    assert "quote_age_ms" in snapshot.columns
    assert "trade_sequence_number" in snapshot.columns
    assert "quote_sequence_number" in snapshot.columns

    assert snapshot.iloc[0]["quote_age_ms"] == 0.0
    assert snapshot.iloc[1]["quote_age_ms"] == 1000.0
    assert snapshot.iloc[2]["quote_age_ms"] == 2000.0
