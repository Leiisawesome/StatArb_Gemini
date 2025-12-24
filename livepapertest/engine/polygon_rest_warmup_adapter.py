"""
PolygonRestWarmupAdapter
========================

Provides `get_warmup_data(symbol, bars=...)` for `core_engine.paper.engine.PaperTradingEngine.warmup()`
using Polygon REST minute aggregates (Stock Starter compatible).

Key behavior
------------
- Fetches enough recent history to cover `bars` (best-effort; depends on market hours)
- Returns a DataFrame with a **timestamp column** (not index) so BufferManager warmup preserves time
- Returns rows in ascending timestamp order
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Optional

import pandas as pd

from core_engine.data.feeds.polygon_rest import PolygonRestService, create_polygon_rest_service


@dataclass(frozen=True)
class PolygonWarmupConfig:
    api_key: Optional[str] = None  # default: POLYGON_API_KEY env var
    timeframe: str = "1min"
    warmup_days_max: int = 10
    warmup_days_min: int = 1
    # Rough heuristic: 390 RTH minutes/day; we pad to handle holidays/outages
    rth_minutes_per_day: int = 390
    extra_days_padding: int = 2


class PolygonRestWarmupAdapter:
    """
    Minimal adapter for PaperTradingEngine.warmup() compatibility.
    """

    def __init__(self, config: Optional[PolygonWarmupConfig] = None):
        self.config = config or PolygonWarmupConfig()
        self._svc: Optional[PolygonRestService] = None
        self._last_ts_by_symbol: dict[str, datetime] = {}

    async def initialize(self) -> None:
        if self._svc is None:
            self._svc = await create_polygon_rest_service(api_key=self.config.api_key)

    async def close(self) -> None:
        if self._svc is not None:
            await self._svc.close()
            self._svc = None

    async def get_warmup_data(self, symbol: str, bars: int) -> pd.DataFrame:
        """
        Fetch warmup bars as a DataFrame with a timestamp column.

        PaperTradingEngine calls this method if present.
        """
        sym = (symbol or "").upper()
        bars = int(bars)
        if bars <= 0:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        if self._svc is None:
            await self.initialize()
        assert self._svc is not None

        end = datetime.now(timezone.utc)
        est_days = ceil(bars / max(1, self.config.rth_minutes_per_day)) + self.config.extra_days_padding
        days = min(self.config.warmup_days_max, max(self.config.warmup_days_min, est_days))
        start = end - timedelta(days=days)

        df = await self._svc.get_bars(sym, timeframe=self.config.timeframe, start=start, end=end)
        if df is None or df.empty:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        # Ensure ascending and materialize timestamp as a column (BufferManager warmup resets index).
        df = df.sort_index()
        df = df.tail(bars).copy()
        df = df.reset_index().rename(columns={"index": "timestamp"})

        # Guarantee required columns exist
        for col in ("timestamp", "open", "high", "low", "close", "volume"):
            if col not in df.columns:
                df[col] = pd.NA

        # Track last warmup timestamp for WS cutoff (handoff)
        try:
            if len(df) > 0 and "timestamp" in df.columns:
                last_ts = df["timestamp"].iloc[-1]
                if isinstance(last_ts, datetime):
                    if last_ts.tzinfo is None:
                        last_ts = last_ts.replace(tzinfo=timezone.utc)
                    self._last_ts_by_symbol[sym] = last_ts
        except Exception:
            pass

        return df

    def last_warmup_timestamp(self, symbol: str) -> Optional[datetime]:
        """Last timestamp returned by warmup for the given symbol (if any)."""
        sym = (symbol or "").upper()
        return self._last_ts_by_symbol.get(sym)


