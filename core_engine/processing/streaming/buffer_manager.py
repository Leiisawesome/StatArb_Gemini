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

    # Standard OHLCV columns
    OHLCV_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

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
        self._buffers: Dict[str, pd.DataFrame] = {}

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
        """Create an empty buffer DataFrame with standard columns."""
        return pd.DataFrame(columns=self.OHLCV_COLUMNS)

    def update(self, symbol: str, bar: Dict[str, Any]) -> None:
        """
        Append a new bar to the symbol's buffer.

        Args:
            symbol: Symbol to update
            bar: Bar data dictionary with OHLCV fields
        """
        normalized = self._normalize_bar(bar)

        with self._lock:
            if symbol not in self._buffers:
                self._buffers[symbol] = self._create_empty_buffer()
                self._stats['symbols_tracked'] += 1

            buffer = self._buffers[symbol]

            # Create new row
            new_row = pd.DataFrame([normalized])

            # Append and trim to buffer size
            # Handle empty buffer case to avoid FutureWarning
            if buffer.empty:
                self._buffers[symbol] = new_row
            else:
                self._buffers[symbol] = pd.concat(
                    [buffer, new_row],
                    ignore_index=True
                ).tail(self._buffer_size)

            # Check warmup status
            if symbol not in self._warmed_up:
                if len(self._buffers[symbol]) >= self._warmup_required:
                    self._warmed_up.add(symbol)
                    self._stats['symbols_warmed_up'] += 1
                    logger.info(f"Buffer warmed up for {symbol} ({len(self._buffers[symbol])} bars)")

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
            return self._buffers[symbol].copy()

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
            return self._buffers.get(symbol)

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
            if symbol not in self._buffers:
                return 0
            return len(self._buffers[symbol])

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

            self._buffers[symbol] = df

            if symbol not in self._warmed_up:
                self._stats['symbols_tracked'] += 1

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

            for symbol, df in self._buffers.items():
                # Convert DataFrame to list of dicts for JSON serialization
                state['buffers'][symbol] = df.to_dict(orient='records')

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
            self._warmed_up.clear()

            for symbol, records in state.get('buffers', {}).items():
                df = pd.DataFrame(records)
                self._buffers[symbol] = df

                if len(df) >= self._warmup_required:
                    self._warmed_up.add(symbol)

            self._stats['symbols_tracked'] = len(self._buffers)
            self._stats['symbols_warmed_up'] = len(self._warmed_up)

            logger.info(
                f"Restored buffer state: {len(self._buffers)} symbols, "
                f"{len(self._warmed_up)} warmed up"
            )

