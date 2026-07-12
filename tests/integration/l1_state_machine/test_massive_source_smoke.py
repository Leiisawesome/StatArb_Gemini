from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from l1_microstructure.ingest import HistoricalBatchRequest, MassiveRESTDataSource
from l1_microstructure.ingest.massive import _resolve_massive_api_key


_EASTERN = ZoneInfo("America/New_York")


def _et_ns(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> int:
    timestamp = datetime(year, month, day, hour, minute, second, tzinfo=_EASTERN)
    return int(timestamp.timestamp() * 1_000_000_000)


pytestmark = [pytest.mark.integration, pytest.mark.external, pytest.mark.requires_data]


def test_massive_api_key_is_available_for_source_backed_smoke() -> None:
    api_key = _resolve_massive_api_key(None)
    if not api_key:
        pytest.skip("MASSIVE_API_KEY is not configured")

    assert api_key


def test_massive_rest_source_can_load_bounded_historical_window() -> None:
    api_key = _resolve_massive_api_key(None)
    if not api_key:
        pytest.skip("MASSIVE_API_KEY is not configured")

    source = MassiveRESTDataSource()
    request = HistoricalBatchRequest(
        symbols=("AAPL",),
        trade_date=date(2024, 3, 11),
        include_quotes=True,
        include_trades=True,
        start_ns=_et_ns(2024, 3, 11, 9, 30, 0),
        end_ns=_et_ns(2024, 3, 11, 9, 31, 0),
    )

    events = list(source.load_historical(request))

    assert events
    assert all(event.symbol == "AAPL" for event in events)
    assert any(type(event).__name__ == "QuoteEvent" for event in events)
