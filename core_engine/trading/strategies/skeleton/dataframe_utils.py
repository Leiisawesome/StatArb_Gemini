"""
Skeleton DataFrame utilities (Rule 7).

These helpers centralize strategy-agnostic pandas plumbing so strategy implementations
can focus on core alpha logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

import pandas as pd


def safe_iloc(df: pd.DataFrame, idx: int, *, logger=None) -> Optional[pd.Series]:
    """
    Safe DataFrame row access with bounds checking.

    - Supports negative indices
    - Returns None if out of bounds
    """
    # Convert negative index
    if idx < 0:
        idx = len(df) + idx

    # Bounds check
    if idx < 0 or idx >= len(df):
        if logger is not None:
            logger.warning(f"    Index {idx} out of bounds for DataFrame with {len(df)} rows")
        return None

    return df.iloc[idx]


def extract_bar_timestamp(
    data: pd.DataFrame,
    idx: int,
    *,
    column_candidates: Iterable[str] = ("timestamp", "Timestamp", "datetime", "date", "time"),
    logger=None,
) -> Optional[datetime]:
    """
    Best-effort timestamp extraction for a bar at `idx`.

    Priority:
    1) DataFrame index (DatetimeIndex or index values)
    2) Timestamp-like columns
    3) Last resort: coerce index value via pd.Timestamp

    Returns:
        datetime or None
    """
    signal_timestamp: Optional[datetime] = None

    # 1) Try index
    try:
        if isinstance(data.index, pd.DatetimeIndex):
            signal_timestamp = data.index[idx]
        elif hasattr(data.index, "iloc"):
            signal_timestamp = data.index.iloc[idx]
        else:
            signal_timestamp = data.index[idx]

        if isinstance(signal_timestamp, pd.Timestamp):
            signal_timestamp = signal_timestamp.to_pydatetime()
        elif not isinstance(signal_timestamp, datetime):
            if isinstance(signal_timestamp, str):
                try:
                    signal_timestamp = datetime.fromisoformat(signal_timestamp.replace("Z", "+00:00"))
                except Exception:
                    signal_timestamp = None
            else:
                signal_timestamp = None
    except Exception as e:
        if logger is not None:
            logger.debug(f"Could not extract timestamp from index: {e}")
        signal_timestamp = None

    # 2) Try columns
    if not signal_timestamp:
        try:
            for col in column_candidates:
                if col not in data.columns:
                    continue
                ts = data[col].iloc[idx]
                if isinstance(ts, pd.Timestamp):
                    signal_timestamp = ts.to_pydatetime()
                elif isinstance(ts, datetime):
                    signal_timestamp = ts
                elif isinstance(ts, str):
                    try:
                        signal_timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        signal_timestamp = None
                else:
                    try:
                        ts2 = pd.Timestamp(ts)
                        signal_timestamp = ts2.to_pydatetime()
                    except Exception:
                        signal_timestamp = None

                if signal_timestamp:
                    break
        except Exception:
            signal_timestamp = None

    # 3) Last resort: coerce index value
    if not signal_timestamp:
        try:
            ts2 = pd.Timestamp(data.index[idx])
            if not pd.isna(ts2):
                signal_timestamp = ts2.to_pydatetime()
        except Exception:
            signal_timestamp = None

    if signal_timestamp and isinstance(signal_timestamp, pd.Timestamp):
        return signal_timestamp.to_pydatetime()
    if isinstance(signal_timestamp, datetime):
        return signal_timestamp
    return None

