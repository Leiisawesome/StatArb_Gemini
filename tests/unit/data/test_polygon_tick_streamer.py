"""Unit tests for Polygon historical tick streamer."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from core_engine.data.feeds.adapters import AdapterStatus
from core_engine.data.replay.polygon_tick_streamer import (
    PolygonHistoricalTickStreamer,
    PolygonTickStreamerConfig,
)


@pytest.fixture
def tick_streamer_config() -> PolygonTickStreamerConfig:
    start = datetime(2025, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end = start + timedelta(seconds=2)
    return PolygonTickStreamerConfig(
        symbols=["AAPL"],
        start_time=start,
        end_time=end,
        api_key="test_api_key_12345",
        playback_speed=float("inf"),
    )


def test_tick_streamer_config_validation_empty_symbols(tick_streamer_config):
    with pytest.raises(ValueError, match="symbols"):
        PolygonTickStreamerConfig(
            symbols=[],
            start_time=tick_streamer_config.start_time,
            end_time=tick_streamer_config.end_time,
            api_key="test",
        )


def test_tick_streamer_config_validation_time_window(tick_streamer_config):
    with pytest.raises(ValueError, match="start_time"):
        PolygonTickStreamerConfig(
            symbols=["AAPL"],
            start_time=tick_streamer_config.end_time,
            end_time=tick_streamer_config.start_time,
            api_key="test",
        )


@pytest.mark.asyncio
async def test_streamer_emits_second_by_second_messages(tick_streamer_config):
    ts_1 = tick_streamer_config.start_time
    ts_2 = tick_streamer_config.start_time + timedelta(seconds=1)

    snapshot_df = pd.DataFrame(
        {
            "trade_price": [100.1, 100.2],
            "trade_size": [10, None],
            "trade_exchange": [1, None],
            "trade_count": [1, 0],
            "quote_bid": [100.0, 100.1],
            "quote_ask": [100.2, 100.3],
            "quote_bid_size": [50, 55],
            "quote_ask_size": [60, 65],
            "quote_count": [1, 1],
            "spread": [0.2, 0.2],
        },
        index=[ts_1, ts_2],
    )

    mock_rest_service = Mock()
    mock_rest_service.get_trade_quote_snapshots_1s = AsyncMock(return_value=snapshot_df)
    mock_rest_service.close = AsyncMock()

    with patch(
        "core_engine.data.replay.polygon_tick_streamer.create_polygon_rest_service",
        new=AsyncMock(return_value=mock_rest_service),
    ):
        streamer = PolygonHistoricalTickStreamer(tick_streamer_config)
        captured_messages = []
        streamer.add_message_handler(captured_messages.append)

        assert await streamer.connect()
        assert streamer.status == AdapterStatus.CONNECTED

        subscribed = await streamer.subscribe(["AAPL"], ["trade", "quote", "second_agg"])
        assert subscribed

        completed = await streamer.wait_until_complete(timeout=1.0)
        assert completed

        mock_rest_service.get_trade_quote_snapshots_1s.assert_awaited_once()
        rest_call_kwargs = mock_rest_service.get_trade_quote_snapshots_1s.await_args.kwargs
        assert rest_call_kwargs["full_fidelity"] is False

        assert len(captured_messages) == 5
        assert [msg.message_type for msg in captured_messages] == [
            "trade",
            "quote",
            "second_agg",
            "quote",
            "second_agg",
        ]
        assert captured_messages[0].symbol == "AAPL"
        assert captured_messages[0].timestamp == ts_1
        assert captured_messages[2].timestamp == ts_1 + timedelta(seconds=1)
        assert captured_messages[-1].timestamp == ts_2 + timedelta(seconds=1)
        assert captured_messages[0].data["conditions"] == []
        assert captured_messages[1].data["conditions"] == []
        assert captured_messages[2].data["bar_type"] == "second"
        assert "trade_count" not in captured_messages[0].data
        assert "spread" not in captured_messages[1].data

        await streamer.disconnect()
        mock_rest_service.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_streamer_enriched_mode_includes_replay_fields(tick_streamer_config):
    ts_1 = tick_streamer_config.start_time
    snapshot_df = pd.DataFrame(
        {
            "trade_price": [100.1],
            "trade_size": [10],
            "trade_exchange": [1],
            "trade_count": [3],
            "quote_bid": [100.0],
            "quote_ask": [100.2],
            "quote_bid_size": [50],
            "quote_ask_size": [60],
            "quote_count": [7],
            "spread": [0.2],
        },
        index=[ts_1],
    )

    mock_rest_service = Mock()
    mock_rest_service.get_trade_quote_snapshots_1s = AsyncMock(return_value=snapshot_df)
    mock_rest_service.close = AsyncMock()

    with patch(
        "core_engine.data.replay.polygon_tick_streamer.create_polygon_rest_service",
        new=AsyncMock(return_value=mock_rest_service),
    ):
        config = PolygonTickStreamerConfig(
            symbols=tick_streamer_config.symbols,
            start_time=tick_streamer_config.start_time,
            end_time=tick_streamer_config.end_time,
            api_key=tick_streamer_config.api_key,
            playback_speed=float("inf"),
            strict_live_parity=False,
        )
        streamer = PolygonHistoricalTickStreamer(config)
        captured_messages = []
        streamer.add_message_handler(captured_messages.append)

        assert await streamer.connect()
        assert await streamer.subscribe(["AAPL"], ["trade", "quote", "second_agg"])
        assert await streamer.wait_until_complete(timeout=1.0)

        trade_msg = next(msg for msg in captured_messages if msg.message_type == "trade")
        quote_msg = next(msg for msg in captured_messages if msg.message_type == "quote")

        assert trade_msg.data["trade_count"] == 3
        assert quote_msg.data["spread"] == pytest.approx(0.2)
        assert quote_msg.data["quote_count"] == 7
        assert quote_msg.data["is_stale"] is False

        await streamer.disconnect()


@pytest.mark.asyncio
async def test_streamer_full_fidelity_maps_microstructure_fields(tick_streamer_config):
    ts_1 = tick_streamer_config.start_time
    snapshot_df = pd.DataFrame(
        {
            "trade_price": [100.1],
            "trade_size": [10],
            "trade_exchange": [11],
            "trade_count": [3],
            "trade_conditions": [[12, 37]],
            "trade_tape": [2],
            "trade_sequence_number": [4242],
            "quote_bid": [100.0],
            "quote_ask": [100.2],
            "quote_bid_size": [50],
            "quote_ask_size": [60],
            "quote_bid_exchange": [8],
            "quote_ask_exchange": [9],
            "quote_conditions": [[1]],
            "quote_count": [7],
            "quote_age_ms": [150.0],
            "spread": [0.2],
        },
        index=[ts_1],
    )

    mock_rest_service = Mock()
    mock_rest_service.get_trade_quote_snapshots_1s = AsyncMock(return_value=snapshot_df)
    mock_rest_service.close = AsyncMock()

    with patch(
        "core_engine.data.replay.polygon_tick_streamer.create_polygon_rest_service",
        new=AsyncMock(return_value=mock_rest_service),
    ):
        config = PolygonTickStreamerConfig(
            symbols=tick_streamer_config.symbols,
            start_time=tick_streamer_config.start_time,
            end_time=tick_streamer_config.end_time,
            api_key=tick_streamer_config.api_key,
            playback_speed=float("inf"),
            strict_live_parity=False,
            full_fidelity=True,
        )
        streamer = PolygonHistoricalTickStreamer(config)
        captured_messages = []
        streamer.add_message_handler(captured_messages.append)

        assert await streamer.connect()
        assert await streamer.subscribe(["AAPL"], ["trade", "quote", "second_agg"])
        assert await streamer.wait_until_complete(timeout=1.0)

        mock_rest_service.get_trade_quote_snapshots_1s.assert_awaited_once()
        rest_call_kwargs = mock_rest_service.get_trade_quote_snapshots_1s.await_args.kwargs
        assert rest_call_kwargs["full_fidelity"] is True

        trade_msg = next(msg for msg in captured_messages if msg.message_type == "trade")
        quote_msg = next(msg for msg in captured_messages if msg.message_type == "quote")

        assert trade_msg.data["conditions"] == [12, 37]
        assert trade_msg.data["tape"] == 2
        assert trade_msg.sequence_number == 4242

        assert quote_msg.data["bid_exchange"] == 8
        assert quote_msg.data["ask_exchange"] == 9
        assert quote_msg.data["conditions"] == [1]
        assert quote_msg.data["quote_age_ms"] == pytest.approx(150.0)

        await streamer.disconnect()


@pytest.mark.asyncio
async def test_subscribe_fails_when_symbol_outside_config_scope(tick_streamer_config):
    mock_rest_service = Mock()
    mock_rest_service.get_trade_quote_snapshots_1s = AsyncMock(return_value=pd.DataFrame())
    mock_rest_service.close = AsyncMock()

    with patch(
        "core_engine.data.replay.polygon_tick_streamer.create_polygon_rest_service",
        new=AsyncMock(return_value=mock_rest_service),
    ):
        streamer = PolygonHistoricalTickStreamer(tick_streamer_config)
        assert await streamer.connect()

        subscribed = await streamer.subscribe(["MSFT"], ["quote"])
        assert not subscribed

        await streamer.disconnect()


@pytest.mark.asyncio
async def test_streamer_handles_nan_values_without_nan_payloads(tick_streamer_config):
    ts_1 = tick_streamer_config.start_time
    ts_2 = tick_streamer_config.start_time + timedelta(seconds=1)

    snapshot_df = pd.DataFrame(
        {
            "trade_price": [100.1, float("nan")],
            "trade_size": [float("nan"), float("nan")],
            "trade_exchange": [float("nan"), float("nan")],
            "trade_count": [1, float("nan")],
            "quote_bid": [100.0, 100.2],
            "quote_ask": [100.3, 100.5],
            "quote_bid_size": [float("nan"), 11],
            "quote_ask_size": [12, float("nan")],
            "quote_count": [float("nan"), 2],
            "spread": [float("nan"), float("nan")],
        },
        index=[ts_1, ts_2],
    )

    mock_rest_service = Mock()
    mock_rest_service.get_trade_quote_snapshots_1s = AsyncMock(return_value=snapshot_df)
    mock_rest_service.close = AsyncMock()

    with patch(
        "core_engine.data.replay.polygon_tick_streamer.create_polygon_rest_service",
        new=AsyncMock(return_value=mock_rest_service),
    ):
        config = PolygonTickStreamerConfig(
            symbols=tick_streamer_config.symbols,
            start_time=tick_streamer_config.start_time,
            end_time=tick_streamer_config.end_time,
            api_key=tick_streamer_config.api_key,
            playback_speed=float("inf"),
            strict_live_parity=False,
        )
        streamer = PolygonHistoricalTickStreamer(config)
        captured_messages = []
        streamer.add_message_handler(captured_messages.append)

        assert await streamer.connect()
        assert await streamer.subscribe(["AAPL"], ["trade", "quote", "second_agg"])
        assert await streamer.wait_until_complete(timeout=1.0)

        assert captured_messages
        for message in captured_messages:
            for value in message.data.values():
                if isinstance(value, (list, dict, tuple, set)):
                    continue
                assert not pd.isna(value), f"Found NaN in message payload: {message.message_type} {message.data}"

        await streamer.disconnect()
