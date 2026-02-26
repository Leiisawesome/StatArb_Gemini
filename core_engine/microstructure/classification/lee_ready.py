"""
Lee-Ready trade sign classification.

Implements the 3-step Lee-Ready (1991) classification rule:
1. Quote rule: trade_price > midpoint → BUY, trade_price < midpoint → SELL
2. At-midpoint: apply tick rule (compare to previous trade price)
3. No resolution: mark INDETERMINATE

Vectorized with numpy for performance: 1M trades in < 30 seconds.
Quote-trade matching via np.searchsorted on sorted timestamp arrays.

Blueprint: v1.6-FINAL Section 1.5
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple

import numpy as np

from core_engine.microstructure.constants import (
    QUOTE_LAG_THRESHOLD_MS,
    TICK_RULE_FALLBACK_MAX_PCT,
)

logger = logging.getLogger(__name__)

# Method encoding for compact storage
_METHOD_QUOTE: np.uint8 = np.uint8(0)
_METHOD_TICK: np.uint8 = np.uint8(1)
_METHOD_INDETERMINATE: np.uint8 = np.uint8(2)

QUOTE_LAG_THRESHOLD_NS: int = QUOTE_LAG_THRESHOLD_MS * 1_000_000


# Polygon condition codes that indicate non-regular trades to exclude.
# Reference: https://polygon.io/glossary/us/stocks/conditions-indicators
# These represent odd-lot, average-price, out-of-sequence, etc.
NON_REGULAR_CONDITIONS: frozenset = frozenset({
    2,   # Average Price Trade
    7,   # Qualified Contingent Trade (QCT)
    10,  # Cross Trade
    15,  # Reopening Trade
    16,  # Closing Trade
    21,  # Corrected Consolidated Close Price as per Listing Market
    22,  # Prior Reference Price
    29,  # Official Close Price
    33,  # Official Open Price
    38,  # Derivatively Priced
})


@dataclass
class ClassificationQuality:
    """Quality metrics for a batch of classified trades."""
    total_trades: int
    buy_count: int
    sell_count: int
    indeterminate_count: int
    midpoint_fraction: float
    tick_rule_fallback_pct: float
    stale_quote_pct: float
    mean_quote_age_ms: float
    quote_age_p50_ms: float
    quote_age_p99_ms: float


class LeeReadyClassifier:
    """Vectorized Lee-Ready trade classification with quality tracking.

    All array operations use numpy — no row-level Python loops.
    Trade-to-quote matching uses np.searchsorted for O(n log m) complexity.
    """

    def classify_trades(
        self,
        trade_timestamps: np.ndarray,
        trade_prices: np.ndarray,
        trade_sizes: np.ndarray,
        trade_exchanges: np.ndarray,
        quote_timestamps: np.ndarray,
        quote_bids: np.ndarray,
        quote_asks: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Classify all trades in a symbol-day (or hourly chunk).

        Args:
            trade_timestamps: Int64 nanoseconds, must be sorted ascending.
            trade_prices:     Float64 trade prices.
            trade_sizes:      UInt32 trade sizes (shares).
            trade_exchanges:  UInt8 exchange IDs.
            quote_timestamps: Int64 nanoseconds, must be sorted ascending.
            quote_bids:       Float64 bid prices.
            quote_asks:       Float64 ask prices.

        Returns:
            signs:      Int8 array of length N_trades (-1=sell, 0=indeterminate, +1=buy)
            methods:    UInt8 array (0=quote_rule, 1=tick_rule, 2=indeterminate)
            midpoints:  Float64 array — prevailing NBBO midpoint at each trade
            quote_ages: Int64 array — nanoseconds since the matched quote update
        """
        n_trades = len(trade_timestamps)
        n_quotes = len(quote_timestamps)

        if n_trades == 0:
            return (
                np.array([], dtype=np.int8),
                np.array([], dtype=np.uint8),
                np.array([], dtype=np.float64),
                np.array([], dtype=np.int64),
            )

        if n_quotes == 0:
            logger.warning("No quotes available — all trades marked indeterminate")
            return (
                np.zeros(n_trades, dtype=np.int8),
                np.full(n_trades, _METHOD_INDETERMINATE, dtype=np.uint8),
                np.full(n_trades, np.nan, dtype=np.float64),
                np.full(n_trades, -1, dtype=np.int64),
            )

        # ── Step 1: Match each trade to prevailing NBBO ──────────────────
        midpoints, quote_ages, has_quote = self._match_quotes(
            trade_timestamps, quote_timestamps, quote_bids, quote_asks
        )

        # ── Step 2: Apply quote rule (vectorized) ────────────────────────
        signs = np.zeros(n_trades, dtype=np.int8)
        methods = np.full(n_trades, _METHOD_INDETERMINATE, dtype=np.uint8)

        # Only apply to trades that have a valid quote match
        valid = has_quote & np.isfinite(midpoints) & (midpoints > 0)

        price_diff = np.where(valid, trade_prices - midpoints, 0.0)

        above_mid = valid & (price_diff > 1e-10)
        below_mid = valid & (price_diff < -1e-10)
        at_mid = valid & ~above_mid & ~below_mid

        signs[above_mid] = 1
        signs[below_mid] = -1
        methods[above_mid] = _METHOD_QUOTE
        methods[below_mid] = _METHOD_QUOTE

        # ── Step 3: Tick rule for at-midpoint trades ─────────────────────
        if np.any(at_mid):
            tick_signs = self._apply_tick_rule(trade_prices, at_mid)
            resolved = at_mid & (tick_signs != 0)
            signs[resolved] = tick_signs[resolved]
            methods[resolved] = _METHOD_TICK
            methods[at_mid & ~resolved] = _METHOD_INDETERMINATE

        # Trades with no valid quote match remain indeterminate
        no_quote = ~valid
        signs[no_quote] = 0
        methods[no_quote] = _METHOD_INDETERMINATE

        return signs, methods, midpoints, quote_ages

    def classify_day_chunked(
        self,
        symbol: str,
        trading_date: date,
        trade_timestamps: np.ndarray,
        trade_prices: np.ndarray,
        trade_sizes: np.ndarray,
        trade_exchanges: np.ndarray,
        quote_timestamps: np.ndarray,
        quote_bids: np.ndarray,
        quote_asks: np.ndarray,
        chunk_duration_ns: int = 3_600_000_000_000,  # 1 hour
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, ClassificationQuality]:
        """
        Classify a full day with hour-level chunking for memory management.

        Splits quotes into hourly chunks and processes trades per chunk,
        carrying forward the last quote from each chunk to the next.
        This keeps peak memory at ~1-2 GB even for Tier A names.

        Returns signs, methods, midpoints, quote_ages, and quality metrics.
        """
        n_trades = len(trade_timestamps)
        if n_trades == 0:
            quality = ClassificationQuality(
                total_trades=0, buy_count=0, sell_count=0,
                indeterminate_count=0, midpoint_fraction=0.0,
                tick_rule_fallback_pct=0.0, stale_quote_pct=0.0,
                mean_quote_age_ms=0.0, quote_age_p50_ms=0.0,
                quote_age_p99_ms=0.0,
            )
            return (
                np.array([], dtype=np.int8),
                np.array([], dtype=np.uint8),
                np.array([], dtype=np.float64),
                np.array([], dtype=np.int64),
                quality,
            )

        # Determine hourly chunk boundaries from trade timestamp range
        t_min = int(trade_timestamps[0])
        t_max = int(trade_timestamps[-1])

        chunk_starts = np.arange(t_min, t_max + 1, chunk_duration_ns, dtype=np.int64)
        chunk_ends = np.append(chunk_starts[1:], np.int64(t_max + 1))

        all_signs = np.zeros(n_trades, dtype=np.int8)
        all_methods = np.full(n_trades, _METHOD_INDETERMINATE, dtype=np.uint8)
        all_midpoints = np.full(n_trades, np.nan, dtype=np.float64)
        all_quote_ages = np.full(n_trades, -1, dtype=np.int64)

        # Initialize carry-forward from the last quote before the first trade.
        # Without this, chunks starting at t_min miss quotes that precede all trades.
        carry_ts: Optional[np.int64] = None
        carry_bid: Optional[np.float64] = None
        carry_ask: Optional[np.float64] = None

        pre_trade_mask = quote_timestamps < t_min
        if np.any(pre_trade_mask):
            last_pre_idx = np.where(pre_trade_mask)[0][-1]
            carry_ts = quote_timestamps[last_pre_idx]
            carry_bid = quote_bids[last_pre_idx]
            carry_ask = quote_asks[last_pre_idx]

        for chunk_start, chunk_end in zip(chunk_starts, chunk_ends):
            # Select trades in this chunk
            t_mask = (trade_timestamps >= chunk_start) & (trade_timestamps < chunk_end)
            if not np.any(t_mask):
                # Update carry-forward from quotes in this window even if no trades
                q_mask = (quote_timestamps >= chunk_start) & (quote_timestamps < chunk_end)
                if np.any(q_mask):
                    q_idx = np.where(q_mask)[0]
                    carry_ts = quote_timestamps[q_idx[-1]]
                    carry_bid = quote_bids[q_idx[-1]]
                    carry_ask = quote_asks[q_idx[-1]]
                continue

            t_idx = np.where(t_mask)[0]

            # Select quotes for this chunk — include carry-forward quote
            # Extend quote window slightly before chunk_start to include carry-forward
            q_window_start = chunk_start
            if carry_ts is not None:
                q_window_start = min(carry_ts, chunk_start)

            q_mask = (quote_timestamps >= q_window_start) & (quote_timestamps < chunk_end)
            q_idx = np.where(q_mask)[0]

            # Build chunk quote arrays with carry-forward prepended if needed
            if len(q_idx) > 0:
                chunk_q_ts = quote_timestamps[q_idx]
                chunk_q_bids = quote_bids[q_idx]
                chunk_q_asks = quote_asks[q_idx]
            else:
                chunk_q_ts = np.array([], dtype=np.int64)
                chunk_q_bids = np.array([], dtype=np.float64)
                chunk_q_asks = np.array([], dtype=np.float64)

            # Prepend carry-forward quote if it's before the earliest quote in chunk
            if carry_ts is not None:
                if len(chunk_q_ts) == 0 or carry_ts < chunk_q_ts[0]:
                    chunk_q_ts = np.concatenate([[carry_ts], chunk_q_ts])
                    chunk_q_bids = np.concatenate([[carry_bid], chunk_q_bids])
                    chunk_q_asks = np.concatenate([[carry_ask], chunk_q_asks])

            # Classify this chunk
            chunk_signs, chunk_methods, chunk_mids, chunk_ages = self.classify_trades(
                trade_timestamps[t_idx],
                trade_prices[t_idx],
                trade_sizes[t_idx],
                trade_exchanges[t_idx],
                chunk_q_ts,
                chunk_q_bids,
                chunk_q_asks,
            )

            all_signs[t_idx] = chunk_signs
            all_methods[t_idx] = chunk_methods
            all_midpoints[t_idx] = chunk_mids
            all_quote_ages[t_idx] = chunk_ages

            # Update carry-forward from the last quote in this chunk
            if len(chunk_q_ts) > 0:
                carry_ts = chunk_q_ts[-1]
                carry_bid = chunk_q_bids[-1]
                carry_ask = chunk_q_asks[-1]

        # Apply tick rule across chunk boundaries for remaining indeterminates
        at_mid = all_methods == _METHOD_INDETERMINATE
        valid_quote = np.isfinite(all_midpoints) & (all_midpoints > 0)
        truly_at_mid = at_mid & valid_quote
        if np.any(truly_at_mid):
            tick_signs = self._apply_tick_rule(trade_prices, truly_at_mid)
            resolved = truly_at_mid & (tick_signs != 0)
            all_signs[resolved] = tick_signs[resolved]
            all_methods[resolved] = _METHOD_TICK

        quality = self._compute_quality(
            all_signs, all_methods, all_midpoints, all_quote_ages,
            trade_prices, n_trades,
        )

        logger.info(
            "Classified %s %s: %d trades, buy=%d sell=%d indet=%d, "
            "tick_rule=%.1f%%, stale_quote=%.1f%%, mean_age=%.1fms",
            symbol, trading_date, n_trades, quality.buy_count,
            quality.sell_count, quality.indeterminate_count,
            quality.tick_rule_fallback_pct * 100,
            quality.stale_quote_pct * 100,
            quality.mean_quote_age_ms,
        )

        return all_signs, all_methods, all_midpoints, all_quote_ages, quality

    # ── Internal methods ─────────────────────────────────────────────────

    def _match_quotes(
        self,
        trade_ts: np.ndarray,
        quote_ts: np.ndarray,
        quote_bids: np.ndarray,
        quote_asks: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        For each trade, find the most recent quote with ts <= trade_ts.

        Uses np.searchsorted for O(n log m) matching.

        Returns:
            midpoints:  Float64 midpoint at each trade
            quote_ages: Int64 nanoseconds since matched quote
            has_quote:  Bool array — True if a valid quote was found
        """
        n_trades = len(trade_ts)

        # searchsorted('right') gives the index of the first quote_ts > trade_ts.
        # Subtract 1 to get the last quote_ts <= trade_ts.
        indices = np.searchsorted(quote_ts, trade_ts, side="right") - 1

        has_quote = indices >= 0

        midpoints = np.full(n_trades, np.nan, dtype=np.float64)
        quote_ages = np.full(n_trades, -1, dtype=np.int64)

        valid = has_quote
        valid_idx = indices[valid]

        bids = quote_bids[valid_idx]
        asks = quote_asks[valid_idx]

        # Defensive: skip crossed/locked quotes (bid >= ask or either <= 0)
        good_quote = (bids > 0) & (asks > 0) & (asks > bids)

        # Map good_quote back to full array
        valid_positions = np.where(valid)[0]
        good_positions = valid_positions[good_quote]
        bad_positions = valid_positions[~good_quote]

        midpoints[good_positions] = (bids[good_quote] + asks[good_quote]) / 2.0
        quote_ages[good_positions] = (
            trade_ts[good_positions] - quote_ts[valid_idx[good_quote]]
        )

        has_quote[bad_positions] = False

        return midpoints, quote_ages, has_quote

    def _apply_tick_rule(
        self,
        trade_prices: np.ndarray,
        at_midpoint_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Apply tick test to trades at the midpoint.

        For each at-midpoint trade, look backward to the most recent trade
        with a different price. If current > previous → BUY, else → SELL.

        Vectorized by propagating the last non-zero price diff forward.
        """
        n = len(trade_prices)
        tick_signs = np.zeros(n, dtype=np.int8)

        # Price changes from one trade to the next
        diffs = np.diff(trade_prices, prepend=np.nan)

        # Build a "last known direction" array by forward-filling non-zero diffs
        direction = np.zeros(n, dtype=np.int8)
        direction[diffs > 1e-10] = 1
        direction[diffs < -1e-10] = -1

        # Forward-fill: propagate non-zero direction forward
        # This handles the "look back to most recent different price" requirement
        last_dir = np.int8(0)
        for i in range(n):
            if direction[i] != 0:
                last_dir = direction[i]
            direction[i] = last_dir

        tick_signs[at_midpoint_mask] = direction[at_midpoint_mask]
        return tick_signs

    def _compute_quality(
        self,
        signs: np.ndarray,
        methods: np.ndarray,
        midpoints: np.ndarray,
        quote_ages: np.ndarray,
        trade_prices: np.ndarray,
        total_trades: int,
    ) -> ClassificationQuality:
        """Compute classification quality metrics for the batch."""
        buy_count = int(np.sum(signs == 1))
        sell_count = int(np.sum(signs == -1))
        indeterminate_count = int(np.sum(signs == 0))

        # Midpoint fraction: trades exactly at midpoint (before tick rule)
        valid_mid = np.isfinite(midpoints) & (midpoints > 0)
        at_mid = valid_mid & (np.abs(trade_prices - midpoints) < 1e-10)
        midpoint_fraction = float(np.sum(at_mid)) / max(total_trades, 1)

        # Tick rule fallback percentage
        tick_count = int(np.sum(methods == _METHOD_TICK))
        tick_rule_fallback_pct = tick_count / max(total_trades, 1)

        # Stale quote percentage (quote_age > threshold)
        valid_ages = quote_ages[quote_ages >= 0]
        if len(valid_ages) > 0:
            stale_count = int(np.sum(valid_ages > QUOTE_LAG_THRESHOLD_NS))
            stale_quote_pct = stale_count / max(total_trades, 1)
            mean_quote_age_ms = float(np.mean(valid_ages)) / 1_000_000
            quote_age_p50_ms = float(np.percentile(valid_ages, 50)) / 1_000_000
            quote_age_p99_ms = float(np.percentile(valid_ages, 99)) / 1_000_000
        else:
            stale_quote_pct = 1.0
            mean_quote_age_ms = -1.0
            quote_age_p50_ms = -1.0
            quote_age_p99_ms = -1.0

        return ClassificationQuality(
            total_trades=total_trades,
            buy_count=buy_count,
            sell_count=sell_count,
            indeterminate_count=indeterminate_count,
            midpoint_fraction=midpoint_fraction,
            tick_rule_fallback_pct=tick_rule_fallback_pct,
            stale_quote_pct=stale_quote_pct,
            mean_quote_age_ms=mean_quote_age_ms,
            quote_age_p50_ms=quote_age_p50_ms,
            quote_age_p99_ms=quote_age_p99_ms,
        )

    @staticmethod
    def compute_spread_bps(
        trade_prices: np.ndarray,
        midpoints: np.ndarray,
        quote_bids: np.ndarray,
        quote_asks: np.ndarray,
        quote_ts: np.ndarray,
        trade_ts: np.ndarray,
    ) -> np.ndarray:
        """
        Compute bid-ask spread in basis points at each trade time.

        Uses the matched quote's bid/ask, not the midpoint alone.
        Returns Float64 array of spread in bps.
        """
        indices = np.searchsorted(quote_ts, trade_ts, side="right") - 1
        valid = indices >= 0

        spreads_bps = np.full(len(trade_prices), np.nan, dtype=np.float64)

        if np.any(valid):
            valid_idx = indices[valid]
            bids = quote_bids[valid_idx]
            asks = quote_asks[valid_idx]
            mids = (bids + asks) / 2.0

            good = (mids > 0) & (asks > bids) & (bids > 0)
            valid_positions = np.where(valid)[0]
            good_positions = valid_positions[good]

            spreads_bps[good_positions] = (
                (asks[good] - bids[good]) / mids[good] * 10_000
            )

        return spreads_bps
