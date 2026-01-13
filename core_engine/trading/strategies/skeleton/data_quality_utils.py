"""
Skeleton data-quality utilities (Rule 7).

Centralizes generic checks (e.g., detecting stale forward-filled series) so alphas
don't carry pipeline/ETL policing logic.
"""

from __future__ import annotations

import pandas as pd


def is_ffill_stale(series: pd.Series, *, max_stale_bars: int = 10, logger=None) -> bool:
    """
    Check if forward-filled data is stale (too many consecutive identical values at the end).
    """
    if series.empty or len(series) < 2:
        return False

    try:
        last_value = series.iloc[-1]
        if pd.isna(last_value):
            return True

        consecutive_same = 1
        for i in range(len(series) - 2, max(-1, len(series) - max_stale_bars - 2), -1):
            if pd.isna(series.iloc[i]) or series.iloc[i] != last_value:
                break
            consecutive_same += 1

        is_stale = consecutive_same >= max_stale_bars
        if is_stale and logger is not None:
            logger.warning(f"Stale ffill detected: {consecutive_same} consecutive bars with value {last_value}")
        return is_stale
    except Exception as e:
        if logger is not None:
            logger.error(f"Error checking stale ffill: {e}")
        return False

