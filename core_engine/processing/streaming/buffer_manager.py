"""
StreamingBufferManager - Per-Symbol Rolling DataFrames
=======================================================

Maintains rolling window DataFrames per symbol for batch indicator reuse.

Design (from plan Section 3.1):
- buffers: Dict[symbol, DataFrame] - Rolling window per symbol
- buffer_size: int - e.g., 500 bars
- warmup_required: int - e.g., 200 bars
- Methods: update(), get_buffer(), is_warmed_up(), load_warmup_data()

Warmup: Load 1-2 RTH sessions before trading starts.

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 2)
"""

from typing import Any, Dict, List, Optional, Set
import logging
import threading
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class StreamingBufferManager:
    """
    Manages per-symbol rolling DataFrames for streaming indicator computation.

    Thread-safe: buffers can be updated and read from different threads.

    Usage:
        manager = StreamingBufferManager(buffer_size=500, warmup_required=200)
        manager.load_warmup_data('AAPL', historical_df)

        # On each new bar:
        manager.update('AAPL', bar_dict)
        if manager.is_warmed_up('AAPL'):
            buffer = manager.get_buffer('AAPL')
            # compute indicators on buffer
    """

    # Standard OHLCV columns (+ symbol). Indicator engine expects `symbol` for groupby paths.
    OHLCV_COLUMNS = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']

    def __init__(
        self,
        buffer_size: int = 500,
        warmup_required: int = 200,
        column_mapping: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize buffer manager.

        Args:
            buffer_size: Maximum bars to keep per symbol
            warmup_required: Minimum bars before buffer is "warmed up"
            column_mapping: Optional mapping from input column names to standard names
        """
        self._buffer_size = buffer_size
        self._warmup_required = warmup_required
        self._column_mapping = column_mapping or {}

        # Per-symbol buffers: symbol -> DataFrame
        # Stored as fixed-size ring buffers to avoid per-bar pd.concat allocations.
        # Each symbol has:
        # - DataFrame of length buffer_size (preallocated)
        # - write index (next insertion point)
        # - count (number of valid rows, <= buffer_size)
        self._buffers: Dict[str, pd.DataFrame] = {}
        self._write_idx: Dict[str, int] = {}
        self._count: Dict[str, int] = {}

        # Track warmup status to avoid repeated checks
        self._warmed_up: Set[str] = set()

        # Thread lock for buffer access
        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            'total_updates': 0,
            'symbols_tracked': 0,
            'symbols_warmed_up': 0,
        }

    def _normalize_bar(self, bar: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize bar dict to standard column names.

        Handles common naming conventions:
        - open_price -> open
        - high_price -> high
        - close_price -> close
        - low_price -> low
        - vol -> volume
        """
        normalized = {}

        # Standard mappings
        default_mapping = {
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close',
            'vol': 'volume',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume',
            'bar_timestamp': 'timestamp',
            'time': 'timestamp',
        }

        # Merge with custom mapping (custom takes precedence)
        mapping = {**default_mapping, **self._column_mapping}

        for key, value in bar.items():
            normalized_key = mapping.get(key, key)
            normalized[normalized_key] = value

        return normalized

    def _create_empty_buffer(self) -> pd.DataFrame:
        """Create a fixed-size ring buffer DataFrame with standard columns."""
        n = int(self._buffer_size)
        # Timestamp can be tz-aware; keep as object to avoid dtype churn.
        # IMPORTANT: Use np.full(..., None) instead of np.empty(...) to avoid uninitialized garbage
        # (which can include ints) leading to sort/type errors downstream.
        return pd.DataFrame(
            {
                "timestamp": np.full(n, None, dtype=object),
                "symbol": np.full(n, None, dtype=object),
                "open": np.full(n, np.nan, dtype="float64"),
                "high": np.full(n, np.nan, dtype="float64"),
                "low": np.full(n, np.nan, dtype="float64"),
                "close": np.full(n, np.nan, dtype="float64"),
                "volume": np.full(n, np.nan, dtype="float64"),
            }
        )

    @staticmethod
    def _coerce_timestamp(value: Any) -> Any:
        """
        Coerce incoming timestamps to a consistent datetime-like object.

        We prefer pandas.Timestamp (tz-aware if input has tz) to avoid mixed-type
        comparisons inside indicator engines (e.g. DataFrame.sort_values on timestamp).
        """
        tz_name = "America/New_York"
        if value is None:
            return pd.NaT
        if isinstance(value, pd.Timestamp):
            ts = value
            if ts.tz is None:
                try:
                    ts = ts.tz_localize(tz_name, ambiguous="infer", nonexistent="shift_forward")
                except Exception:
                    ts = ts.tz_localize(tz_name)
            else:
                try:
                    ts = ts.tz_convert(tz_name)
                except Exception:
                    pass
            return ts
        if isinstance(value, datetime):
            ts = pd.Timestamp(value)
            if ts.tz is None:
                try:
                    ts = ts.tz_localize(tz_name, ambiguous="infer", nonexistent="shift_forward")
                except Exception:
                    ts = ts.tz_localize(tz_name)
            else:
                ts = ts.tz_convert(tz_name)
            return ts
        if isinstance(value, np.datetime64):
            # Treat naive np.datetime64 as UTC and convert to NY (common from .values on tz-aware series).
            try:
                ts = pd.Timestamp(value, tz="UTC").tz_convert(tz_name)
            except Exception:
                ts = pd.Timestamp(value)
                if ts.tz is None:
                    ts = ts.tz_localize(tz_name)
            return ts
        if isinstance(value, (int, np.integer)):
            # Treat integer timestamps as nanoseconds since epoch UTC (ClickHouse window_start style).
            try:
                return pd.to_datetime(int(value), unit="ns", utc=True).tz_convert(tz_name)
            except Exception:
                return pd.NaT
        if isinstance(value, str):
            ts = pd.to_datetime(value, errors="coerce")
            if isinstance(ts, pd.Timestamp):
                if ts.tz is None:
                    try:
                        ts = ts.tz_localize(tz_name, ambiguous="infer", nonexistent="shift_forward")
                    except Exception:
                        ts = ts.tz_localize(tz_name)
                else:
                    try:
                        ts = ts.tz_convert(tz_name)
                    except Exception:
                        pass
            return ts
        # Best-effort fallback
        try:
            ts = pd.Timestamp(value)
            if ts.tz is None:
                ts = ts.tz_localize(tz_name)
            else:
                ts = ts.tz_convert(tz_name)
            return ts
        except Exception:
            return pd.NaT

    def _ensure_symbol(self, symbol: str) -> None:
        """Initialize ring buffer state for a symbol if missing."""
        if symbol in self._buffers:
            return
        self._buffers[symbol] = self._create_empty_buffer()
        self._write_idx[symbol] = 0
        self._count[symbol] = 0
        self._stats["symbols_tracked"] += 1

    def _append_row(self, symbol: str, row: Dict[str, Any]) -> None:
        """Append a normalized row into the symbol ring buffer (O(1))."""
        buf = self._buffers[symbol]
        i = self._write_idx[symbol]

        # Write into preallocated columns (fast, avoids concat/alloc).
        # Missing fields become NaN/None.
        buf.at[i, "timestamp"] = self._coerce_timestamp(row.get("timestamp"))
        buf.at[i, "symbol"] = row.get("symbol", symbol)
        buf.at[i, "open"] = row.get("open", np.nan)
        buf.at[i, "high"] = row.get("high", np.nan)
        buf.at[i, "low"] = row.get("low", np.nan)
        buf.at[i, "close"] = row.get("close", np.nan)
        buf.at[i, "volume"] = row.get("volume", np.nan)

        self._write_idx[symbol] = (i + 1) % self._buffer_size
        self._count[symbol] = min(self._count[symbol] + 1, self._buffer_size)

    def _ordered_view(self, symbol: str) -> pd.DataFrame:
        """
        Return an ordered (oldest->newest) view DataFrame of valid rows for a symbol.

        Note: This may allocate when the ring has wrapped (count==buffer_size).
        That allocation replaces the per-bar pd.concat overhead we removed in update().
        """
        buf = self._buffers[symbol]
        n = self._count.get(symbol, 0)
        if n <= 0:
            return pd.DataFrame(columns=self.OHLCV_COLUMNS)

        if n < self._buffer_size:
            # Not wrapped yet: valid rows are [0:n)
            return buf.iloc[:n].reset_index(drop=True)

        # Wrapped: oldest is at write_idx (next write location).
        w = self._write_idx.get(symbol, 0)
        if w == 0:
            return buf.reset_index(drop=True)

        a = buf.iloc[w:]
        b = buf.iloc[:w]
        return pd.concat([a, b], ignore_index=True)

    def update(self, symbol: str, bar: Dict[str, Any]) -> None:
        """
        Append a new bar to the symbol's buffer.

        Args:
            symbol: Symbol to update
            bar: Bar data dictionary with OHLCV fields
        """
        normalized = self._normalize_bar(bar)

        with self._lock:
            self._ensure_symbol(symbol)
            self._append_row(symbol, normalized)

            # Check warmup status
            if symbol not in self._warmed_up:
                if self._count.get(symbol, 0) >= self._warmup_required:
                    self._warmed_up.add(symbol)
                    self._stats['symbols_warmed_up'] += 1
                    logger.info(f"Buffer warmed up for {symbol} ({self._count.get(symbol, 0)} bars)")

            self._stats['total_updates'] += 1

    def get_buffer(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get the buffer DataFrame for a symbol.

        Returns a copy to prevent external modification.

        Args:
            symbol: Symbol to get buffer for

        Returns:
            DataFrame copy or None if symbol not tracked
        """
        with self._lock:
            if symbol not in self._buffers:
                return None
            return self._ordered_view(symbol).copy()

    def get_buffer_view(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get a view of the buffer (no copy).

        WARNING: Do not modify the returned DataFrame.
        Use only for read-only operations where performance matters.

        Args:
            symbol: Symbol to get buffer for

        Returns:
            DataFrame view or None if symbol not tracked
        """
        with self._lock:
            if symbol not in self._buffers:
                return None
            return self._ordered_view(symbol)

    def is_warmed_up(self, symbol: str) -> bool:
        """
        Check if a symbol's buffer has enough data for indicator computation.

        Args:
            symbol: Symbol to check

        Returns:
            True if buffer has >= warmup_required bars
        """
        with self._lock:
            return symbol in self._warmed_up

    def get_buffer_length(self, symbol: str) -> int:
        """Get current buffer length for a symbol."""
        with self._lock:
            return int(self._count.get(symbol, 0))

    def load_warmup_data(
        self,
        symbol: str,
        historical_df: pd.DataFrame,
        normalize_columns: bool = True,
    ) -> None:
        """
        Pre-load historical data for warmup.

        Args:
            symbol: Symbol to load data for
            historical_df: Historical OHLCV DataFrame
            normalize_columns: If True, rename columns to standard names
        """
        with self._lock:
            df = historical_df.copy()

            # Normalize column names if needed
            if normalize_columns:
                rename_map = {}
                for col in df.columns:
                    normalized = self._normalize_bar({col: None})
                    for new_col in normalized:
                        if new_col != col:
                            rename_map[col] = new_col
                            break
                if rename_map:
                    df = df.rename(columns=rename_map)

            # Keep only buffer_size most recent bars
            df = df.tail(self._buffer_size).reset_index(drop=True)
            self._ensure_symbol(symbol)

            # Fill ring buffer sequentially (not wrapped)
            buf = self._buffers[symbol]
            # Reset columns without polluting object columns with float NaNs.
            buf["timestamp"] = np.full(self._buffer_size, None, dtype=object)
            buf["symbol"] = np.full(self._buffer_size, None, dtype=object)
            for col in ("open", "high", "low", "close", "volume"):
                buf[col] = np.nan

            n = len(df)
            if n > 0:
                # Copy columns that exist
                for col in self.OHLCV_COLUMNS:
                    if col in df.columns:
                        if col == "timestamp":
                            s = pd.to_datetime(df[col], errors="coerce")
                            # Preserve tz-awareness; .values can drop tz and create naive np.datetime64.
                            # Store as object Timestamps in America/New_York.
                            try:
                                if getattr(s.dtype, "tz", None) is None:
                                    s = s.dt.tz_localize("America/New_York", ambiguous="infer", nonexistent="shift_forward")
                                else:
                                    s = s.dt.tz_convert("America/New_York")
                            except Exception:
                                pass
                            buf.loc[: n - 1, col] = s.astype(object).values
                        else:
                            buf.loc[: n - 1, col] = df[col].values
                if "symbol" not in df.columns:
                    buf.loc[: n - 1, "symbol"] = symbol

            self._count[symbol] = n
            # Next write is 0 if full, else n
            self._write_idx[symbol] = 0 if n >= self._buffer_size else n

            # Check warmup status
            if len(df) >= self._warmup_required:
                if symbol not in self._warmed_up:
                    self._warmed_up.add(symbol)
                    self._stats['symbols_warmed_up'] += 1
                logger.info(f"Warmup data loaded for {symbol} ({len(df)} bars)")
            else:
                logger.warning(
                    f"Warmup data for {symbol} has only {len(df)} bars, "
                    f"need {self._warmup_required} for warmup"
                )

    def clear_symbol(self, symbol: str) -> None:
        """Clear buffer for a specific symbol."""
        with self._lock:
            if symbol in self._buffers:
                del self._buffers[symbol]
                self._stats['symbols_tracked'] -= 1
            if symbol in self._warmed_up:
                self._warmed_up.remove(symbol)
                self._stats['symbols_warmed_up'] -= 1

    def clear_all(self) -> None:
        """Clear all buffers."""
        with self._lock:
            self._buffers.clear()
            self._warmed_up.clear()
            self._stats['symbols_tracked'] = 0
            self._stats['symbols_warmed_up'] = 0

    def get_tracked_symbols(self) -> List[str]:
        """Get list of all tracked symbols."""
        with self._lock:
            return list(self._buffers.keys())

    def get_warmed_up_symbols(self) -> List[str]:
        """Get list of symbols that are warmed up."""
        with self._lock:
            return list(self._warmed_up)

    def get_stats(self) -> Dict[str, Any]:
        """Get buffer manager statistics."""
        with self._lock:
            return {
                **self._stats,
                'buffer_size': self._buffer_size,
                'warmup_required': self._warmup_required,
            }

    def get_last_bar(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the most recent bar for a symbol."""
        with self._lock:
            if symbol not in self._buffers or len(self._buffers[symbol]) == 0:
                return None
            return self._buffers[symbol].iloc[-1].to_dict()

    def get_last_n_bars(self, symbol: str, n: int) -> Optional[pd.DataFrame]:
        """Get the last N bars for a symbol."""
        with self._lock:
            if symbol not in self._buffers:
                return None
            return self._buffers[symbol].tail(n).copy()

    def get_state_for_checkpoint(self) -> Dict[str, Any]:
        """
        Get buffer state for checkpointing.

        Returns serializable state for PaperSessionStateManager.
        """
        with self._lock:
            state = {
                'buffer_size': self._buffer_size,
                'warmup_required': self._warmup_required,
                'buffers': {},
            }

            for symbol in self._buffers.keys():
                # Persist only valid rows (oldest -> newest), not the full preallocated ring memory.
                valid_df = self._ordered_view(symbol)
                state['buffers'][symbol] = valid_df.to_dict(orient='records')

            return state

    def restore_from_checkpoint(self, state: Dict[str, Any]) -> None:
        """
        Restore buffer state from checkpoint.

        Args:
            state: State dict from get_state_for_checkpoint()
        """
        with self._lock:
            self._buffer_size = state.get('buffer_size', self._buffer_size)
            self._warmup_required = state.get('warmup_required', self._warmup_required)

            self._buffers.clear()
            self._write_idx.clear()
            self._count.clear()
            self._warmed_up.clear()

            for symbol, records in state.get('buffers', {}).items():
                df = pd.DataFrame(records)
                # Keep only most recent buffer_size rows and restore into ring layout.
                if len(df) > self._buffer_size:
                    df = df.tail(self._buffer_size).reset_index(drop=True)

                self._ensure_symbol(symbol)
                buf = self._buffers[symbol]

                # Reset buffer memory explicitly.
                buf["timestamp"] = np.full(self._buffer_size, None, dtype=object)
                buf["symbol"] = np.full(self._buffer_size, None, dtype=object)
                for col in ("open", "high", "low", "close", "volume"):
                    buf[col] = np.nan

                n = len(df)
                if n > 0:
                    for col in self.OHLCV_COLUMNS:
                        if col in df.columns:
                            if col == "timestamp":
                                s = pd.to_datetime(df[col], errors="coerce")
                                try:
                                    if getattr(s.dtype, "tz", None) is None:
                                        s = s.dt.tz_localize("America/New_York", ambiguous="infer", nonexistent="shift_forward")
                                    else:
                                        s = s.dt.tz_convert("America/New_York")
                                except Exception:
                                    pass
                                buf.loc[: n - 1, col] = s.astype(object).values
                            else:
                                buf.loc[: n - 1, col] = df[col].values

                    if "symbol" not in df.columns:
                        buf.loc[: n - 1, "symbol"] = symbol

                self._count[symbol] = n
                self._write_idx[symbol] = 0 if n >= self._buffer_size else n

                if n >= self._warmup_required:
                    self._warmed_up.add(symbol)

            self._stats['symbols_tracked'] = len(self._buffers)
            self._stats['symbols_warmed_up'] = len(self._warmed_up)

            logger.info(
                f"Restored buffer state: {len(self._buffers)} symbols, "
                f"{len(self._warmed_up)} warmed up"
            )

