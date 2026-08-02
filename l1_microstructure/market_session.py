"""Shared U.S. equity-session identity helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


_NEW_YORK = ZoneInfo("America/New_York")


def market_session_date(timestamp_ns: int) -> str:
    """Return the New York market date for a nanosecond UTC timestamp."""
    timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000.0, tz=timezone.utc)
    return timestamp.astimezone(_NEW_YORK).date().isoformat()


def same_market_session(first_timestamp_ns: int, second_timestamp_ns: int) -> bool:
    return market_session_date(first_timestamp_ns) == market_session_date(second_timestamp_ns)
