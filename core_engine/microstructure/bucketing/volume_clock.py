"""
Volume-clock bucket engine.

Aggregates classified trades into fixed-volume buckets (ADV / 200).
Uses integer arithmetic (np.uint64) for cumulative volume accumulation
to guarantee deterministic replay. No floating-point accumulation anywhere
in the bucket boundary logic.

Vectorized with np.cumsum + np.searchsorted: 1M trades in < 10 seconds.

Blueprint: v1.6-FINAL Section 1.6
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional, Tuple

import numpy as np

from core_engine.microstructure.types import VolumeBucket

logger = logging.getLogger(__name__)

# Method encoding from classifier (must stay in sync)
_METHOD_TICK: np.uint8 = np.uint8(1)


class VolumeClockBucketer:
    """Constructs volume-clock buckets from classified trades.

    All volume accumulation uses integer arithmetic (UInt64).
    Float conversion happens ONLY after bucket indices are fixed.
    """

    def compute_bucket_size(self, adv_shares: int, target_buckets: int = 200) -> int:
        """Compute bucket volume = ADV / target_buckets (integer division, minimum 1)."""
        if adv_shares <= 0 or target_buckets <= 0:
            raise ValueError(f"Invalid ADV ({adv_shares}) or target ({target_buckets})")
        return max(1, adv_shares // target_buckets)

    def bucketize(
        self,
        symbol: str,
        trading_date: date,
        trade_timestamps: np.ndarray,
        trade_prices: np.ndarray,
        trade_sizes: np.ndarray,
        trade_signs: np.ndarray,
        trade_midpoints: np.ndarray,
        trade_spread_bps: np.ndarray,
        quote_bid_at_trade: np.ndarray,
        quote_ask_at_trade: np.ndarray,
        bucket_volume: int,
        trade_methods: Optional[np.ndarray] = None,
    ) -> List[VolumeBucket]:
        """
        Aggregate classified trades into volume-clock buckets.

        Uses np.cumsum on integer volumes and np.searchsorted to find
        bucket boundaries. No floating-point accumulation.

        Args:
            trade_methods: UInt8 array of classification methods (0=quote, 1=tick, 2=indet).
                           If None, tick_rule_fallback_pct will be 0.

        Returns list of VolumeBucket objects, one per completed bucket.
        """
        n_trades = len(trade_timestamps)
        if n_trades == 0:
            return []

        if bucket_volume <= 0:
            raise ValueError(f"bucket_volume must be positive, got {bucket_volume}")

        # ── Step 1: Integer-safe bucket boundary computation ─────────
        bucket_vol_u64 = np.uint64(bucket_volume)
        trade_sizes_u64 = trade_sizes.astype(np.uint64)
        cumulative_volume = np.cumsum(trade_sizes_u64)
        total_volume = cumulative_volume[-1]

        if total_volume == 0:
            return []

        # Bucket boundaries: bucket_vol, 2*bucket_vol, 3*bucket_vol, ...
        # up to total_volume. Each boundary marks where a bucket is "full".
        bucket_boundaries = np.arange(
            bucket_vol_u64,
            total_volume + bucket_vol_u64,
            bucket_vol_u64,
            dtype=np.uint64,
        )

        # searchsorted: for each boundary, find the first trade index
        # where cumulative volume >= boundary. This trade completes the bucket.
        bucket_end_indices = np.searchsorted(cumulative_volume, bucket_boundaries)

        # Clip to valid range — the last boundary may exceed total volume
        bucket_end_indices = np.clip(bucket_end_indices, 0, n_trades - 1)

        # Remove duplicate end indices (can happen when last boundary overshoots)
        # and the final bucket that captures remaining trades
        unique_mask = np.concatenate([
            [True],
            np.diff(bucket_end_indices) > 0
        ])
        bucket_end_indices = bucket_end_indices[unique_mask]

        # ── Step 2: Build bucket start/end index pairs ───────────────
        # Bucket i spans [start_idx, end_idx] inclusive
        bucket_start_indices = np.concatenate([
            [0],
            bucket_end_indices[:-1] + 1
        ])

        # Ensure we don't miss trailing trades
        if len(bucket_end_indices) > 0 and bucket_end_indices[-1] < n_trades - 1:
            bucket_start_indices = np.append(
                bucket_start_indices, bucket_end_indices[-1] + 1
            )
            bucket_end_indices = np.append(bucket_end_indices, n_trades - 1)

        n_buckets = len(bucket_start_indices)
        if n_buckets == 0:
            return []

        # ── Step 3: Compute metrics per bucket (vectorized where possible) ──
        # Pre-compute signed volume components
        signed_sizes = trade_signs.astype(np.int64) * trade_sizes.astype(np.int64)

        buckets: List[VolumeBucket] = []

        for i in range(n_buckets):
            s = int(bucket_start_indices[i])
            e = int(bucket_end_indices[i]) + 1  # exclusive end for slicing

            if s >= e:
                continue

            bucket = self._compute_single_bucket(
                symbol=symbol,
                trading_date=trading_date,
                bucket_id=i,
                target_bucket_volume=bucket_volume,
                timestamps=trade_timestamps[s:e],
                prices=trade_prices[s:e],
                sizes=trade_sizes[s:e],
                signs=trade_signs[s:e],
                signed_sizes=signed_sizes[s:e],
                midpoints=trade_midpoints[s:e],
                spread_bps=trade_spread_bps[s:e],
                bids=quote_bid_at_trade[s:e],
                asks=quote_ask_at_trade[s:e],
                methods=trade_methods[s:e] if trade_methods is not None else None,
            )

            if bucket is not None:
                buckets.append(bucket)

        logger.info(
            "Bucketed %s %s: %d trades → %d buckets (target vol=%d, "
            "actual range %d–%d)",
            symbol, trading_date, n_trades, len(buckets), bucket_volume,
            min(b.actual_volume for b in buckets) if buckets else 0,
            max(b.actual_volume for b in buckets) if buckets else 0,
        )

        return buckets

    def _compute_single_bucket(
        self,
        symbol: str,
        trading_date: date,
        bucket_id: int,
        target_bucket_volume: int,
        timestamps: np.ndarray,
        prices: np.ndarray,
        sizes: np.ndarray,
        signs: np.ndarray,
        signed_sizes: np.ndarray,
        midpoints: np.ndarray,
        spread_bps: np.ndarray,
        bids: np.ndarray,
        asks: np.ndarray,
        methods: Optional[np.ndarray],
    ) -> Optional[VolumeBucket]:
        """Compute all metrics for a single bucket from its constituent trades."""
        n = len(prices)
        if n == 0:
            return None

        sizes_int = sizes.astype(np.uint64)
        actual_volume = int(np.sum(sizes_int))
        if actual_volume == 0:
            return None

        # ── OHLCV ────────────────────────────────────────────────────
        open_price = float(prices[0])
        close_price = float(prices[-1])
        high_price = float(np.max(prices))
        low_price = float(np.min(prices))

        # VWAP: sum(price * size) / sum(size) — float conversion after bucket fixed
        dollar_volume = np.sum(prices * sizes.astype(np.float64))
        vwap = float(dollar_volume / actual_volume)

        # ── Signed flow ──────────────────────────────────────────────
        buy_mask = signs > 0
        sell_mask = signs < 0
        indet_mask = signs == 0

        buy_volume = int(np.sum(sizes_int[buy_mask]))
        sell_volume = int(np.sum(sizes_int[sell_mask]))
        indeterminate_volume = int(np.sum(sizes_int[indet_mask]))
        unsigned_volume = actual_volume
        signed_volume = int(np.sum(signed_sizes))

        # ── Flow imbalance ───────────────────────────────────────────
        flow_imbalance = float(signed_volume) / unsigned_volume if unsigned_volume > 0 else 0.0

        # ── Classification quality ───────────────────────────────────
        classified_volume = buy_volume + sell_volume
        classification_confidence = (
            classified_volume / unsigned_volume if unsigned_volume > 0 else 0.0
        )

        if methods is not None:
            tick_count = int(np.sum(methods == _METHOD_TICK))
            tick_rule_fallback_pct = tick_count / n if n > 0 else 0.0
        else:
            tick_rule_fallback_pct = 0.0

        # ── Quote context ────────────────────────────────────────────
        bid_at_start = float(bids[0]) if np.isfinite(bids[0]) else 0.0
        ask_at_start = float(asks[0]) if np.isfinite(asks[0]) else 0.0
        bid_at_end = float(bids[-1]) if np.isfinite(bids[-1]) else 0.0
        ask_at_end = float(asks[-1]) if np.isfinite(asks[-1]) else 0.0

        valid_spreads = spread_bps[np.isfinite(spread_bps)]
        median_spread = float(np.median(valid_spreads)) if len(valid_spreads) > 0 else 0.0

        # ── Effective spread (blueprint formula) ─────────────────────
        # effective_spread_bps = median(2 × |trade_price - midpoint| / midpoint × 10000)
        valid_mid = np.isfinite(midpoints) & (midpoints > 0)
        if np.any(valid_mid):
            half_spreads = (
                2.0 * np.abs(prices[valid_mid] - midpoints[valid_mid])
                / midpoints[valid_mid] * 10_000
            )
            effective_spread_bps = float(np.median(half_spreads))
        else:
            effective_spread_bps = median_spread  # fallback to quoted spread

        # ── Price impact per volume ──────────────────────────────────
        # price_impact_per_volume = (midpoint_end - midpoint_start) / signed_volume
        valid_mid_indices = np.where(valid_mid)[0]
        if len(valid_mid_indices) >= 2 and signed_volume != 0:
            mid_start = midpoints[valid_mid_indices[0]]
            mid_end = midpoints[valid_mid_indices[-1]]
            price_impact_per_volume = float(
                (mid_end - mid_start) / signed_volume
            )
        else:
            price_impact_per_volume = 0.0

        # ── Timing metadata ──────────────────────────────────────────
        bucket_start_ns = int(timestamps[0])
        bucket_end_ns = int(timestamps[-1])
        fill_duration_ms = int((bucket_end_ns - bucket_start_ns) / 1_000_000)

        return VolumeBucket(
            symbol=symbol,
            bucket_id=bucket_id,
            bucket_start_ns=bucket_start_ns,
            bucket_end_ns=bucket_end_ns,
            bucket_volume=target_bucket_volume,
            actual_volume=actual_volume,
            num_trades=n,
            open_price=open_price,
            close_price=close_price,
            high_price=high_price,
            low_price=low_price,
            vwap=vwap,
            signed_volume=signed_volume,
            unsigned_volume=unsigned_volume,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            indeterminate_volume=indeterminate_volume,
            classification_confidence=classification_confidence,
            tick_rule_fallback_pct=tick_rule_fallback_pct,
            bid_at_start=bid_at_start,
            ask_at_start=ask_at_start,
            bid_at_end=bid_at_end,
            ask_at_end=ask_at_end,
            median_spread_bps=median_spread,
            flow_imbalance=flow_imbalance,
            effective_spread_bps=effective_spread_bps,
            price_impact_per_volume=price_impact_per_volume,
            bucket_date=trading_date,
            fill_duration_ms=fill_duration_ms,
        )
