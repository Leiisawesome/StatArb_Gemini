from __future__ import annotations

from datetime import date, time

import pandas as pd

from core_engine.data.market_calendar import MarketCalendar
from core_engine.data.rth_filter import filter_bars_to_rth


def _mk_df(ts_list: list[str]) -> pd.DataFrame:
    # Timestamp strings are interpreted as America/New_York by filter when naive.
    return pd.DataFrame(
        {
            "timestamp": ts_list,
            "open": [1.0] * len(ts_list),
            "high": [1.0] * len(ts_list),
            "low": [1.0] * len(ts_list),
            "close": [1.0] * len(ts_list),
            "volume": [100.0] * len(ts_list),
        }
    )


def test_filter_bars_to_rth_us_equity_default_session() -> None:
    cal = MarketCalendar()
    df = _mk_df(
        [
            "2024-12-20 08:00:00",  # pre
            "2024-12-20 09:29:00",  # pre
            "2024-12-20 09:30:00",  # rth open
            "2024-12-20 12:00:00",  # rth
            "2024-12-20 15:59:00",  # rth
            "2024-12-20 16:00:00",  # post (excluded by < close)
            "2024-12-20 18:00:00",  # post
        ]
    )

    out = filter_bars_to_rth(df, symbol="TSLA", calendar=cal)
    assert list(pd.to_datetime(out["timestamp"]).dt.strftime("%H:%M:%S")) == [
        "09:30:00",
        "12:00:00",
        "15:59:00",
    ]


def test_filter_bars_to_rth_supports_early_close_override() -> None:
    cal = MarketCalendar()
    df = _mk_df(
        [
            "2024-11-29 12:59:00",  # rth
            "2024-11-29 13:00:00",  # early close boundary
            "2024-11-29 15:00:00",  # would be rth for normal day, should be excluded with early close
        ]
    )

    overrides = {date(2024, 11, 29): (time(9, 30), time(13, 0))}
    out = filter_bars_to_rth(df, symbol="TSLA", calendar=cal, overrides_by_date=overrides)
    assert list(pd.to_datetime(out["timestamp"]).dt.strftime("%H:%M:%S")) == ["12:59:00"]


