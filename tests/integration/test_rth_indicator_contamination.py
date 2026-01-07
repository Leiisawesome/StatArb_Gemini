from __future__ import annotations

import numpy as np
import pandas as pd

from core_engine.data.market_calendar import MarketCalendar
from core_engine.data.rth_filter import filter_bars_to_rth


def test_rth_indicators_not_contaminated_by_premarket_when_filtered() -> None:
    """
    Regression test: if indicators are computed on a series that includes premarket bars,
    early RTH indicator values can be impacted by those premarket bars.

    The correct approach for RTH-only indicators is to:
    - filter bars to RTH
    - seed with prior-day RTH warmup bars
    - compute indicators on the continuous RTH-only series
    """
    cal = MarketCalendar()

    # Prior day RTH warmup bars (synthetic)
    prev_rth_ts = pd.date_range("2024-12-19 09:30:00", periods=60, freq="1min")
    prev_rth = pd.DataFrame(
        {
            "timestamp": prev_rth_ts,
            "close": 100.0 + np.linspace(0, 1.0, len(prev_rth_ts)),
        }
    )

    # Current day: premarket + RTH
    pre_ts = pd.date_range("2024-12-20 08:00:00", periods=90, freq="1min")  # 08:00–09:29
    rth_ts = pd.date_range("2024-12-20 09:30:00", periods=40, freq="1min")

    pre = pd.DataFrame({"timestamp": pre_ts, "close": 200.0 + np.linspace(0, 2.0, len(pre_ts))})
    rth = pd.DataFrame({"timestamp": rth_ts, "close": 150.0 + np.linspace(0, 1.0, len(rth_ts))})

    # Contaminated series: premarket immediately precedes RTH in the same day.
    contaminated = pd.concat([pre, rth], ignore_index=True)
    contaminated["sma_20"] = contaminated["close"].rolling(20).mean()

    # RTH-only series: filter both days to RTH and carry state across days (seed warmup).
    prev_rth_only = filter_bars_to_rth(prev_rth, symbol="TSLA", calendar=cal, timestamp_col="timestamp")
    rth_only = filter_bars_to_rth(pd.concat([pre, rth], ignore_index=True), symbol="TSLA", calendar=cal, timestamp_col="timestamp")
    clean = pd.concat([prev_rth_only, rth_only], ignore_index=True)
    clean["sma_20"] = clean["close"].rolling(20).mean()

    # Compare SMA at the first RTH bar (09:30). It should differ if premarket is present in the window.
    contaminated_0930 = contaminated.loc[contaminated["timestamp"] == pd.Timestamp("2024-12-20 09:30:00"), "sma_20"].iloc[0]
    clean_0930 = clean.loc[clean["timestamp"] == pd.Timestamp("2024-12-20 09:30:00"), "sma_20"].iloc[0]

    assert pd.notna(contaminated_0930)
    assert pd.notna(clean_0930)
    assert contaminated_0930 != clean_0930


