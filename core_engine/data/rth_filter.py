from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type, datetime, time as time_type
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd

from core_engine.data.market_calendar import AssetClass, MarketCalendar


@dataclass(frozen=True)
class SessionWindow:
    open_time: time_type
    close_time: time_type
    timezone: str


def _get_session_window(
    calendar: MarketCalendar,
    symbol: str,
    *,
    overrides_by_date: Optional[Dict[date_type, Tuple[time_type, time_type]]] = None,
    tz_name_override: Optional[str] = None,
) -> SessionWindow:
    asset_class = calendar.get_asset_class(symbol)
    session = calendar.sessions.get(asset_class) or calendar.sessions[AssetClass.US_EQUITY]
    tz_name = tz_name_override or session.timezone
    # Note: overrides are applied per-day inside the filter; here we return defaults.
    return SessionWindow(open_time=session.open_time, close_time=session.close_time, timezone=tz_name)


def filter_bars_to_rth(
    bars: pd.DataFrame,
    *,
    symbol: str,
    calendar: Optional[MarketCalendar] = None,
    timestamp_col: str = "timestamp",
    overrides_by_date: Optional[Dict[date_type, Tuple[time_type, time_type]]] = None,
) -> pd.DataFrame:
    """
    Filter bar series to Regular Trading Hours (RTH) based on MarketCalendar session times.

    - Uses the symbol's inferred AssetClass (via MarketCalendar.get_asset_class).
    - Compares timestamps in the session timezone.
    - `overrides_by_date` can be used to model early-close days (date -> (open, close)).

    This function is intentionally pure (doesn't mutate input).
    """
    if bars is None or len(bars) == 0:
        return bars

    cal = calendar or MarketCalendar()
    session = _get_session_window(cal, symbol, overrides_by_date=overrides_by_date)

    # Get timestamps from column or index
    if timestamp_col in bars.columns:
        ts = pd.to_datetime(bars[timestamp_col], errors="coerce")
    else:
        ts = pd.to_datetime(bars.index, errors="coerce")

    # Normalize timezone: treat naive timestamps as already in session timezone.
    if getattr(ts.dt, "tz", None) is None:
        try:
            ts = ts.dt.tz_localize(session.timezone, ambiguous="infer", nonexistent="shift_forward")
        except Exception:
            ts = ts.dt.tz_localize(session.timezone)
    else:
        ts = ts.dt.tz_convert(session.timezone)

    # Build masks. Default behavior: open <= ts < close.
    # Overrides apply on a per-date basis (supports early closes).
    t = ts.dt.time
    open_t = session.open_time
    close_t = session.close_time
    mask = (t >= open_t) & (t < close_t)

    # Filter out non-trading days (holidays/weekends)
    if cal:
        asset_class = cal.get_asset_class(symbol)
        unique_dates = ts.dt.date.unique()
        # Vectorized check for trading days
        trading_day_map = {
            d: cal.is_trading_day(datetime.combine(d, datetime.min.time()), asset_class) 
            for d in unique_dates
        }
        mask &= ts.dt.date.map(trading_day_map).astype(bool)

    if overrides_by_date:
        d = ts.dt.date
        # Apply overrides by replacing mask values for those dates.
        for od, (ot, ct) in overrides_by_date.items():
            day_mask = d == od
            if day_mask.any():
                mask = mask.where(~day_mask, (t >= ot) & (t < ct))

    return bars.loc[mask].copy()


def filter_bars_to_rth_multi(
    bars_by_symbol: Dict[str, pd.DataFrame],
    *,
    calendar: Optional[MarketCalendar] = None,
    timestamp_col: str = "timestamp",
    overrides_by_date: Optional[Dict[date_type, Tuple[time_type, time_type]]] = None,
) -> Dict[str, pd.DataFrame]:
    """Apply `filter_bars_to_rth` to each symbol DataFrame in a dict."""
    cal = calendar or MarketCalendar()
    out: Dict[str, pd.DataFrame] = {}
    for sym, df in (bars_by_symbol or {}).items():
        out[sym] = filter_bars_to_rth(
            df,
            symbol=sym,
            calendar=cal,
            timestamp_col=timestamp_col,
            overrides_by_date=overrides_by_date,
        )
    return out


