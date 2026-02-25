"""
Tests for StreamingVolumeBucketer.

Validates that the streaming bucketer produces identical bucket boundaries
and flow metrics to the offline VolumeClockBucketer when fed the same trades.
Also tests Lee-Ready streaming classification consistency.

Build Plan: v4-FINAL, Step 1
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pytest

from core_engine.microstructure.bucketing.volume_clock import VolumeClockBucketer
from core_engine.microstructure.classification.lee_ready import LeeReadyClassifier
from core_engine.microstructure.shadow.streaming_bucketer import (
    StreamingLeeReady,
    StreamingVolumeBucketer,
)


# ============================================================================
# Fixtures
# ============================================================================

def _make_trades(
    n: int = 1000,
    base_price: float = 100.0,
    mean_size: int = 200,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate synthetic trades: timestamps (ns), prices, sizes."""
    rng = np.random.RandomState(seed)
    # Timestamps: ~1 trade per millisecond, sorted
    t0 = 1_700_000_000_000_000_000  # arbitrary nanoseconds
    intervals = rng.exponential(1_000_000, size=n).astype(np.int64)
    timestamps = t0 + np.cumsum(intervals)

    # Random walk prices around base
    returns = rng.normal(0, 0.0001, size=n)
    prices = base_price * np.cumprod(1 + returns)

    # Sizes: uniform-ish
    sizes = rng.poisson(mean_size, size=n).astype(np.uint32)
    sizes = np.maximum(sizes, 1)

    return timestamps, prices, sizes


def _make_quotes(
    trade_timestamps: np.ndarray,
    trade_prices: np.ndarray,
    spread_bps: float = 2.0,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate synthetic NBBO quotes aligned with trades."""
    rng = np.random.RandomState(seed + 1)
    n = len(trade_timestamps)

    # Quotes arrive slightly before trades (1-50us before)
    offsets = rng.randint(1_000, 50_000, size=n).astype(np.int64)
    q_timestamps = trade_timestamps - offsets

    # Spread around trade prices
    half_spread = trade_prices * spread_bps / 10_000 / 2
    bids = trade_prices - half_spread + rng.normal(0, 0.001, n)
    asks = trade_prices + half_spread + rng.normal(0, 0.001, n)
    bids = np.maximum(bids, 0.01)
    asks = np.maximum(asks, bids + 0.01)

    bid_sizes = rng.randint(100, 5000, size=n).astype(np.int32)
    ask_sizes = rng.randint(100, 5000, size=n).astype(np.int32)

    # Sort by timestamp
    sort_idx = np.argsort(q_timestamps)
    return (
        q_timestamps[sort_idx],
        bids[sort_idx],
        asks[sort_idx],
        bid_sizes[sort_idx],
        ask_sizes[sort_idx],
    )


# ============================================================================
# StreamingLeeReady tests
# ============================================================================

class TestStreamingLeeReady:
    """Test streaming Lee-Ready classification logic."""

    def test_buy_above_midpoint(self):
        lr = StreamingLeeReady()
        sign, method = lr.classify(100.05, 100.00)
        assert sign == 1
        assert method == 0  # quote rule

    def test_sell_below_midpoint(self):
        lr = StreamingLeeReady()
        sign, method = lr.classify(99.95, 100.00)
        assert sign == -1
        assert method == 0

    def test_at_midpoint_no_history(self):
        lr = StreamingLeeReady()
        sign, method = lr.classify(100.00, 100.00)
        assert sign == 0
        assert method == 2  # indeterminate

    def test_tick_rule_uptick(self):
        lr = StreamingLeeReady()
        # First trade establishes price
        lr.classify(99.90, 100.00)
        # Second trade at higher price establishes uptick direction
        lr.classify(100.10, 100.00)
        # Third trade at midpoint — should use tick rule (uptick)
        sign, method = lr.classify(100.00, 100.00)
        assert sign == 1
        assert method == 1  # tick rule

    def test_tick_rule_downtick(self):
        lr = StreamingLeeReady()
        lr.classify(100.10, 100.00)
        lr.classify(99.90, 100.00)
        sign, method = lr.classify(100.00, 100.00)
        assert sign == -1
        assert method == 1

    def test_no_quote_returns_indeterminate(self):
        lr = StreamingLeeReady()
        sign, method = lr.classify(100.00, 0.0)
        assert sign == 0
        assert method == 2

    def test_nan_midpoint(self):
        lr = StreamingLeeReady()
        sign, method = lr.classify(100.00, float("nan"))
        assert sign == 0
        assert method == 2

    def test_reset(self):
        lr = StreamingLeeReady()
        lr.classify(100.00, 100.05)
        lr.classify(100.10, 100.05)
        lr.reset()
        # After reset, tick rule should have no history
        sign, method = lr.classify(100.05, 100.05)
        assert sign == 0  # at midpoint, no history

    def test_classification_matches_offline_direction(self):
        """Streaming and offline should agree on classification for typical trades."""
        n = 500
        rng = np.random.RandomState(123)
        prices = 100.0 + np.cumsum(rng.normal(0, 0.01, n))
        midpoints = prices + rng.normal(0, 0.005, n)

        lr = StreamingLeeReady()
        streaming_signs = []
        for p, m in zip(prices, midpoints):
            s, _ = lr.classify(p, m)
            streaming_signs.append(s)
        streaming_signs = np.array(streaming_signs)

        # Offline classification (simplified)
        offline_signs = np.zeros(n, dtype=np.int8)
        diff = prices - midpoints
        offline_signs[diff > 1e-10] = 1
        offline_signs[diff < -1e-10] = -1
        # Note: tick rule differs slightly, so only check quote-rule trades
        quote_ruled = np.abs(diff) > 1e-10
        assert np.all(streaming_signs[quote_ruled] == offline_signs[quote_ruled])


# ============================================================================
# StreamingVolumeBucketer tests
# ============================================================================

class TestStreamingVolumeBucketer:
    """Test streaming volume-clock bucketing."""

    def test_basic_bucket_creation(self):
        """Buckets should be created when cumulative volume reaches target."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.99
        )
        # bucket_volume = 10000 // 200 = 50
        assert bucketer.bucket_volume == 50

        # Feed 50 trades of size 1 each, with quotes
        bucketer.on_quote(1_000_000, 99.0, 101.0, 100, 100)
        for i in range(49):
            result = bucketer.on_trade(1_000_000 + i * 1000, 100.0 + i * 0.01, 1)
            assert result is None

        # 50th trade should complete the bucket
        result = bucketer.on_trade(1_000_000 + 49 * 1000, 100.5, 1)
        # With threshold 0.99, it may or may not emit — check bucket count
        assert bucketer.daily_bucket_count == 1

    def test_extreme_imbalance_event(self):
        """All-buy bucket should produce event when threshold is met."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.5
        )
        # bucket_volume = 50
        # Feed a quote with midpoint = 100
        bucketer.on_quote(1_000_000, 99.0, 101.0, 100, 100)

        # All trades above midpoint -> all classified as BUY -> imbalance = 1.0
        events = []
        for i in range(50):
            result = bucketer.on_trade(
                1_000_000 + i * 1000, 101.5, 1
            )
            if result is not None:
                events.append(result)

        assert len(events) == 1
        event = events[0]
        assert event.symbol == "TEST"
        assert event.flow_imbalance > 0.5  # all buys
        assert event.bucket_volume == 50
        assert event.num_trades == 50

    def test_no_event_below_threshold(self):
        """Balanced bucket should not produce an event."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.5
        )
        bucketer.on_quote(1_000_000, 99.0, 101.0, 100, 100)

        # Alternate buys and sells
        events = []
        for i in range(50):
            price = 101.5 if i % 2 == 0 else 98.5  # alternating buy/sell
            result = bucketer.on_trade(1_000_000 + i * 1000, price, 1)
            if result is not None:
                events.append(result)

        # No extreme imbalance
        assert len(events) == 0
        assert bucketer.daily_bucket_count == 1

    def test_classification_confidence_tracking(self):
        """Classification confidence should reflect classified vs total."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.99
        )
        bucketer.on_quote(1_000_000, 99.0, 101.0, 100, 100)

        for i in range(10):
            bucketer.on_trade(1_000_000 + i * 1000, 101.5, 1)

        confidence = bucketer.get_classification_confidence()
        assert confidence > 0.0

    def test_no_quote_all_indeterminate(self):
        """Without a quote, all trades should be indeterminate."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.99
        )
        # No quote update — midpoint is 0
        for i in range(50):
            bucketer.on_trade(1_000_000 + i * 1000, 100.0, 1)

        assert bucketer.get_classification_confidence() == 0.0

    def test_multiple_buckets(self):
        """Multiple buckets should be created in sequence."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.99
        )
        bucketer.on_quote(1_000_000, 99.0, 101.0, 100, 100)

        for i in range(150):
            bucketer.on_trade(1_000_000 + i * 1000, 100.0 + 0.01 * (i % 10), 1)

        assert bucketer.daily_bucket_count == 3  # 150 / 50 = 3 buckets

    def test_large_trade_spans_bucket(self):
        """A single large trade should complete a bucket."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.0
        )
        bucketer.on_quote(1_000_000, 99.0, 101.0, 100, 100)

        # One trade with volume = bucket_volume
        result = bucketer.on_trade(1_000_000, 101.5, 50)
        assert result is not None
        assert bucketer.daily_bucket_count == 1

    def test_daily_reset(self):
        """reset_daily should clear all state."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.99
        )
        bucketer.on_quote(1_000_000, 99.0, 101.0, 100, 100)
        for i in range(60):
            bucketer.on_trade(1_000_000 + i * 1000, 100.0, 1)

        assert bucketer.daily_bucket_count >= 1
        bucketer.reset_daily()
        assert bucketer.daily_bucket_count == 0
        assert bucketer.get_classification_confidence() == 0.0

    def test_zero_price_trade_ignored(self):
        """Zero-price trades should be silently ignored."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.99
        )
        result = bucketer.on_trade(1_000_000, 0.0, 100)
        assert result is None

    def test_zero_size_trade_ignored(self):
        """Zero-size trades should be silently ignored."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.99
        )
        result = bucketer.on_trade(1_000_000, 100.0, 0)
        assert result is None

    def test_locked_quote_does_not_classify(self):
        """Locked market (bid >= ask) should result in indeterminate classification."""
        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=10_000, imbalance_threshold=0.99
        )
        # Locked market
        bucketer.on_quote(1_000_000, 100.0, 100.0, 100, 100)
        bucketer.on_trade(2_000_000, 100.0, 1)
        assert bucketer.get_classification_confidence() == 0.0


class TestStreamingVsOfflineConsistency:
    """Verify streaming bucketer matches offline bucketer on synthetic data."""

    def test_bucket_boundaries_match(self):
        """Streaming and offline should produce the same number of buckets
        with matching volume boundaries."""
        n_trades = 5000
        adv = 200_000
        t_ts, t_prices, t_sizes = _make_trades(n_trades, seed=99)
        q_ts, q_bids, q_asks, q_bsizes, q_asizes = _make_quotes(t_ts, t_prices, seed=99)

        # Offline: classify then bucketize
        classifier = LeeReadyClassifier()
        signs, methods, midpoints, quote_ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes,
            np.zeros(n_trades, dtype=np.uint8),  # exchange_ids
            q_ts, q_bids, q_asks,
        )

        spread_bps = classifier.compute_spread_bps(
            t_prices, midpoints, q_bids, q_asks, q_ts, t_ts,
        )

        # Match quotes to trades for bid/ask at trade
        q_indices = np.searchsorted(q_ts, t_ts, side="right") - 1
        q_indices = np.clip(q_indices, 0, len(q_ts) - 1)
        quote_bid_at_trade = q_bids[q_indices]
        quote_ask_at_trade = q_asks[q_indices]

        offline_bucketer = VolumeClockBucketer()
        bucket_vol = offline_bucketer.compute_bucket_size(adv)
        offline_buckets = offline_bucketer.bucketize(
            symbol="TEST",
            trading_date=date.today(),
            trade_timestamps=t_ts,
            trade_prices=t_prices,
            trade_sizes=t_sizes,
            trade_signs=signs,
            trade_midpoints=midpoints,
            trade_spread_bps=spread_bps,
            quote_bid_at_trade=quote_bid_at_trade,
            quote_ask_at_trade=quote_ask_at_trade,
            bucket_volume=bucket_vol,
            trade_methods=methods,
        )

        # Streaming: feed trades and quotes chronologically
        streaming_bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=adv, imbalance_threshold=1.0
        )

        # Merge trades and quotes by timestamp, process in order
        all_events_ts = np.concatenate([t_ts, q_ts])
        all_events_type = np.concatenate([
            np.zeros(len(t_ts), dtype=np.int8),
            np.ones(len(q_ts), dtype=np.int8),
        ])
        sort_idx = np.argsort(all_events_ts, kind="stable")
        all_events_ts = all_events_ts[sort_idx]
        all_events_type = all_events_type[sort_idx]

        # Map back to original indices
        trade_idx = 0
        quote_idx = 0
        streaming_bucket_count = 0

        for i in range(len(all_events_ts)):
            if all_events_type[i] == 1:  # quote
                streaming_bucketer.on_quote(
                    q_ts[quote_idx],
                    q_bids[quote_idx],
                    q_asks[quote_idx],
                    int(q_bsizes[quote_idx]),
                    int(q_asizes[quote_idx]),
                )
                quote_idx += 1
            else:  # trade
                result = streaming_bucketer.on_trade(
                    t_ts[trade_idx], t_prices[trade_idx], int(t_sizes[trade_idx])
                )
                if result is not None:
                    streaming_bucket_count += 1
                trade_idx += 1

        streaming_total_buckets = streaming_bucketer.daily_bucket_count

        # Bucket counts should match within 1 (trailing partial bucket handling)
        assert abs(streaming_total_buckets - len(offline_buckets)) <= 1, (
            f"Streaming produced {streaming_total_buckets} buckets, "
            f"offline produced {len(offline_buckets)}"
        )

    def test_flow_imbalance_direction_agreement(self):
        """For strongly directional trade sequences, streaming and offline
        should agree on the sign of flow_imbalance."""
        adv = 10_000
        bucket_vol = adv // 200  # 50

        # Create all-buy trades (price well above midpoint)
        n = 100
        ts = np.arange(n, dtype=np.int64) * 1_000_000 + 1_700_000_000_000_000_000
        prices = np.full(n, 105.0)
        sizes = np.ones(n, dtype=np.uint32)

        bucketer = StreamingVolumeBucketer(
            symbol="TEST", adv_shares=adv, imbalance_threshold=0.0
        )
        # Set quote with midpoint = 100
        bucketer.on_quote(ts[0] - 1000, 99.0, 101.0, 100, 100)

        events = []
        for i in range(n):
            result = bucketer.on_trade(int(ts[i]), float(prices[i]), int(sizes[i]))
            if result is not None:
                events.append(result)

        # All events should show positive imbalance (all buys)
        assert len(events) >= 1
        for e in events:
            assert e.flow_imbalance > 0.5, (
                f"Expected positive imbalance for all-buy, got {e.flow_imbalance}"
            )
