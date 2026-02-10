"""
Phase 0: Data Validation
=========================

Professionals don't trust data. Validate before computing anything.
"""

from typing import Any, Dict

import numpy as np
import pandas as pd

from .config import (
    EXPECTED_BARS_PER_DAY,
    MAX_MISSING_RATE,
    MIN_TRADING_DAYS,
    PRICE_ANOMALY_THRESHOLD,
    SESSION_GAP_SECONDS,
)


def validate_data(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """
    Validate data integrity for a single symbol.

    Must pass before any feature computation begins.

    Raises:
        AssertionError if hard gates fail.
    """
    report: Dict[str, Any] = {
        "symbol": symbol,
        "total_bars": len(df),
        "date_range": f"{df['timestamp'].min()} to {df['timestamp'].max()}",
        "trading_days": df["timestamp"].dt.date.nunique(),
        "missing_rate": _compute_missing_rate(df),
        "zero_volume_rate": float((df["volume"] == 0).mean()),
        "duplicate_timestamps": int(df["timestamp"].duplicated().sum()),
        "price_anomalies": _detect_price_anomalies(df),
    }

    # Hard gates
    assert (
        report["missing_rate"] < MAX_MISSING_RATE
    ), f"{symbol}: Missing rate {report['missing_rate']:.4f} > {MAX_MISSING_RATE}"
    assert (
        report["duplicate_timestamps"] == 0
    ), f"{symbol}: {report['duplicate_timestamps']} duplicate timestamps"
    assert (
        report["trading_days"] >= MIN_TRADING_DAYS
    ), f"{symbol}: Only {report['trading_days']} trading days (need >={MIN_TRADING_DAYS})"

    return report


def _compute_missing_rate(df: pd.DataFrame) -> float:
    """Fraction of expected 1-min bars that are missing within RTH sessions."""
    trading_days = df["timestamp"].dt.date.nunique()
    expected_total = trading_days * EXPECTED_BARS_PER_DAY
    return 1.0 - len(df) / max(expected_total, 1)


def _detect_price_anomalies(df: pd.DataFrame) -> int:
    """Count bars with excessive single-bar price changes (data errors or splits)."""
    returns = df["close"].pct_change().abs()
    return int((returns > PRICE_ANOMALY_THRESHOLD).sum())


def add_session_boundaries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mark session boundaries for feature computation.

    Features that measure path structure (PathEff, CounterFail) must NOT span
    overnight gaps. This function adds columns used by session-safe rolling.
    """
    df = df.sort_values("timestamp").copy()
    df["date"] = df["timestamp"].dt.date
    df["session_bar_num"] = df.groupby("date").cumcount()
    df["is_session_start"] = df["session_bar_num"] == 0

    # Time gap between consecutive bars
    df["time_gap_seconds"] = df["timestamp"].diff().dt.total_seconds()
    df["is_gap"] = df["time_gap_seconds"] > SESSION_GAP_SECONDS

    # Session ID: increments at each gap/session start
    df["session_id"] = (df["is_session_start"] | df["is_gap"]).cumsum()

    return df
