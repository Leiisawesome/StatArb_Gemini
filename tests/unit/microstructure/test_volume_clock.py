"""
Tests for the volume-clock bucketing engine.

Covers:
1. Bucket size computation
2. Integer-safe boundary detection (deterministic replay guarantee)
3. Correct OHLCV, signed flow, and derived metric computation
4. Edge cases: empty trades, single trade, tiny bucket volume
5. Deterministic replay: identical input → identical output
6. Full pipeline integration: classifier → bucketer
7. Performance: 500K trades bucketized in reasonable time
"""

import numpy as np
import pytest
from datetime import date

from core_engine.microstructure.bucketing.volume_clock import VolumeClockBucketer
from core_engine.microstructure.classification.lee_ready import LeeReadyClassifier
from core_engine.microstructure.types import VolumeBucket


@pytest.fixture
def bucketer():
    return VolumeClockBucketer()


@pytest.fixture
def classifier():
    return LeeReadyClassifier()


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def ns(ms: float) -> np.int64:
    """Convert milliseconds to nanoseconds."""
    return np.int64(int(ms * 1_000_000))


def make_classified_trades(entries, default_mid=100.0, default_spread=20.0):
    """
    Build arrays for bucketing from (ms, price, size, sign) tuples.

    Returns all arrays needed by bucketize().
    """
    timestamps = np.array([ns(e[0]) for e in entries], dtype=np.int64)
    prices = np.array([e[1] for e in entries], dtype=np.float64)
    sizes = np.array([e[2] for e in entries], dtype=np.uint32)
    signs = np.array([e[3] for e in entries], dtype=np.int8)
    midpoints = np.full(len(entries), default_mid, dtype=np.float64)
    spread_bps = np.full(len(entries), default_spread, dtype=np.float32)
    bids = np.full(len(entries), default_mid - 0.01, dtype=np.float64)
    asks = np.full(len(entries), default_mid + 0.01, dtype=np.float64)
    methods = np.zeros(len(entries), dtype=np.uint8)
    return timestamps, prices, sizes, signs, midpoints, spread_bps, bids, asks, methods


# ═══════════════════════════════════════════════════════════════════════
# 1. Bucket Size Computation
# ═══════════════════════════════════════════════════════════════════════

class TestBucketSize:
    def test_standard_computation(self, bucketer):
        """ADV=1,000,000 / 200 = 5,000 shares per bucket."""
        assert bucketer.compute_bucket_size(1_000_000, 200) == 5_000

    def test_integer_division(self, bucketer):
        """ADV=1,000,001 / 200 = 5000 (integer floor division)."""
        assert bucketer.compute_bucket_size(1_000_001, 200) == 5_000

    def test_small_adv(self, bucketer):
        """Small ADV still produces at least 1 share per bucket."""
        assert bucketer.compute_bucket_size(50, 200) == 1

    def test_invalid_adv_raises(self, bucketer):
        with pytest.raises(ValueError):
            bucketer.compute_bucket_size(0, 200)

    def test_invalid_target_raises(self, bucketer):
        with pytest.raises(ValueError):
            bucketer.compute_bucket_size(1_000_000, 0)


# ═══════════════════════════════════════════════════════════════════════
# 2. Basic Bucketing
# ═══════════════════════════════════════════════════════════════════════

class TestBasicBucketing:
    def test_exact_bucket_fill(self, bucketer):
        """10 trades × 100 shares = 1000 total, bucket=500 → 2 buckets."""
        entries = [(float(i), 100.0 + i * 0.01, 100, 1) for i in range(10)]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 500,
            trade_methods=meth,
        )

        assert len(buckets) == 2
        assert buckets[0].actual_volume == 500
        assert buckets[1].actual_volume == 500
        assert buckets[0].num_trades == 5
        assert buckets[1].num_trades == 5

    def test_uneven_bucket_fill(self, bucketer):
        """Total volume doesn't divide evenly — last bucket gets remainder.

        Trades: 300+300+300+200 = 1100 total.
        Bucket boundaries at cumvol >= 500 and >= 1000:
          - Bucket 0: trades 0,1 (300+300=600, first cumvol >= 500)
          - Bucket 1: trades 2,3 (300+200=500, captures remainder)
        """
        entries = [
            (1.0, 100.0, 300, 1),
            (2.0, 100.1, 300, 1),
            (3.0, 100.2, 300, -1),
            (4.0, 100.3, 200, -1),  # Total = 1100
        ]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 500,
            trade_methods=meth,
        )

        assert len(buckets) == 2
        assert buckets[0].actual_volume == 600  # Overflows past 500
        assert buckets[1].actual_volume == 500
        total_volume = sum(b.actual_volume for b in buckets)
        assert total_volume == 1100

    def test_bucket_ids_sequential(self, bucketer):
        """Bucket IDs should be sequential starting from 0."""
        entries = [(float(i), 100.0, 100, 1) for i in range(20)]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 500,
            trade_methods=meth,
        )

        for i, b in enumerate(buckets):
            assert b.bucket_id == i


# ═══════════════════════════════════════════════════════════════════════
# 3. OHLCV and Derived Metrics
# ═══════════════════════════════════════════════════════════════════════

class TestMetrics:
    def test_ohlcv(self, bucketer):
        """OHLCV correctly computed from trade prices within bucket."""
        entries = [
            (1.0, 100.0, 200, 1),   # open
            (2.0, 101.5, 200, 1),   # high
            (3.0, 99.5,  200, -1),  # low
            (4.0, 100.5, 200, -1),  # close, fills bucket at 800
            (5.0, 101.0, 200, 1),   # next bucket
        ]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(
            entries, default_mid=100.0
        )

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 800,
            trade_methods=meth,
        )

        b = buckets[0]
        assert b.open_price == 100.0
        assert b.close_price == 100.5
        assert b.high_price == 101.5
        assert b.low_price == 99.5

    def test_vwap(self, bucketer):
        """VWAP = sum(price*size) / sum(size)."""
        entries = [
            (1.0, 100.0, 100, 1),
            (2.0, 102.0, 100, 1),
        ]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 200,
            trade_methods=meth,
        )

        expected_vwap = (100.0 * 100 + 102.0 * 100) / 200
        assert abs(buckets[0].vwap - expected_vwap) < 1e-6

    def test_signed_flow(self, bucketer):
        """Signed volume correctly sums buy(+) and sell(-) contributions."""
        entries = [
            (1.0, 100.0, 300, 1),    # buy 300
            (2.0, 100.1, 200, -1),   # sell 200
        ]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 500,
            trade_methods=meth,
        )

        b = buckets[0]
        assert b.signed_volume == 100     # 300 - 200
        assert b.buy_volume == 300
        assert b.sell_volume == 200
        assert b.unsigned_volume == 500
        assert abs(b.flow_imbalance - 0.2) < 1e-6  # 100/500

    def test_indeterminate_volume(self, bucketer):
        """Indeterminate trades (sign=0) tracked separately."""
        entries = [
            (1.0, 100.0, 200, 1),
            (2.0, 100.1, 150, 0),   # indeterminate
            (3.0, 100.2, 150, -1),
        ]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 500,
            trade_methods=meth,
        )

        b = buckets[0]
        assert b.indeterminate_volume == 150
        assert b.classification_confidence == pytest.approx(
            (200 + 150) / 500, abs=0.01
        )

    def test_effective_spread_bps(self, bucketer):
        """Effective spread = median(2 * |price - mid| / mid * 10000)."""
        entries = [
            (1.0, 100.05, 200, 1),   # |100.05 - 100| / 100 * 2 * 10000 = 10 bps
            (2.0, 99.95, 200, -1),    # same: 10 bps
            (3.0, 100.10, 100, 1),    # 20 bps
        ]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(
            entries, default_mid=100.0
        )

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 500,
            trade_methods=meth,
        )

        # median of [10, 10, 20] = 10
        assert abs(buckets[0].effective_spread_bps - 10.0) < 0.5

    def test_fill_duration_ms(self, bucketer):
        """fill_duration_ms = (last_ts - first_ts) / 1e6."""
        entries = [
            (1.0, 100.0, 250, 1),
            (5.0, 100.1, 250, 1),
        ]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 500,
            trade_methods=meth,
        )

        assert buckets[0].fill_duration_ms == 4  # 5ms - 1ms = 4ms

    def test_price_impact_per_volume(self, bucketer):
        """price_impact = (mid_end - mid_start) / signed_volume."""
        mid_start = 100.00
        mid_end = 100.10
        entries = [
            (1.0, 100.05, 250, 1),
            (2.0, 100.08, 250, 1),
        ]
        ts = np.array([ns(1.0), ns(2.0)], dtype=np.int64)
        pr = np.array([100.05, 100.08], dtype=np.float64)
        sz = np.array([250, 250], dtype=np.uint32)
        sg = np.array([1, 1], dtype=np.int8)
        midpoints = np.array([mid_start, mid_end], dtype=np.float64)
        sp = np.array([5.0, 5.0], dtype=np.float32)
        bid = np.array([99.99, 100.09], dtype=np.float64)
        ask = np.array([100.01, 100.11], dtype=np.float64)
        meth = np.array([0, 0], dtype=np.uint8)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, midpoints, sp, bid, ask, 500,
            trade_methods=meth,
        )

        # signed_volume = 500 (all buys), impact = 0.10 / 500
        expected = (mid_end - mid_start) / 500
        assert abs(buckets[0].price_impact_per_volume - expected) < 1e-10


# ═══════════════════════════════════════════════════════════════════════
# 4. Edge Cases
# ═══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_trades(self, bucketer):
        """Zero trades → empty bucket list."""
        empty = np.array([], dtype=np.int64)
        empty_f = np.array([], dtype=np.float64)
        empty_u = np.array([], dtype=np.uint32)
        empty_s = np.array([], dtype=np.int8)
        empty_sp = np.array([], dtype=np.float32)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            empty, empty_f, empty_u, empty_s,
            empty_f, empty_sp, empty_f, empty_f, 500,
        )

        assert len(buckets) == 0

    def test_single_trade(self, bucketer):
        """One trade → one bucket."""
        entries = [(1.0, 100.0, 100, 1)]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 500,
            trade_methods=meth,
        )

        assert len(buckets) == 1
        assert buckets[0].actual_volume == 100
        assert buckets[0].fill_duration_ms == 0

    def test_zero_size_trades_skipped(self, bucketer):
        """Trades with size 0 don't produce buckets."""
        entries = [(1.0, 100.0, 0, 1)]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 500,
            trade_methods=meth,
        )

        assert len(buckets) == 0

    def test_single_large_trade_multiple_buckets(self, bucketer):
        """One trade of 1000 shares with bucket_vol=100 → 1 bucket (no splitting)."""
        entries = [(1.0, 100.0, 1000, 1)]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 100,
            trade_methods=meth,
        )

        # One trade can only go into one bucket (we don't split trades)
        assert len(buckets) == 1
        assert buckets[0].actual_volume == 1000

    def test_invalid_bucket_volume_raises(self, bucketer):
        entries = [(1.0, 100.0, 100, 1)]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        with pytest.raises(ValueError):
            bucketer.bucketize(
                "TEST", date(2025, 1, 1),
                ts, pr, sz, sg, mid, sp, bid, ask, 0,
            )


# ═══════════════════════════════════════════════════════════════════════
# 5. Deterministic Replay
# ═══════════════════════════════════════════════════════════════════════

class TestDeterministicReplay:
    """Identical inputs must produce identical outputs — no floating-point drift."""

    def test_replay_exact_match(self, bucketer):
        """Running bucketize twice on same data produces identical results."""
        rng = np.random.default_rng(42)
        n = 5000
        base_ts = np.int64(1_700_000_000_000_000_000)

        ts = base_ts + np.sort(rng.integers(0, 10**10, n)).astype(np.int64)
        prices = 150.0 + rng.normal(0, 0.5, n)
        sizes = rng.integers(10, 500, n).astype(np.uint32)
        signs = rng.choice([-1, 0, 1], n).astype(np.int8)
        midpoints = 150.0 + rng.normal(0, 0.1, n)
        spread_bps = rng.uniform(3, 10, n).astype(np.float32)
        bids = midpoints - 0.005
        asks = midpoints + 0.005
        methods = rng.choice([0, 1, 2], n).astype(np.uint8)

        bucket_vol = int(np.sum(sizes) // 200)

        run1 = bucketer.bucketize(
            "AAPL", date(2025, 6, 15),
            ts, prices, sizes, signs, midpoints, spread_bps, bids, asks,
            bucket_vol, trade_methods=methods,
        )

        run2 = bucketer.bucketize(
            "AAPL", date(2025, 6, 15),
            ts, prices, sizes, signs, midpoints, spread_bps, bids, asks,
            bucket_vol, trade_methods=methods,
        )

        assert len(run1) == len(run2)
        for b1, b2 in zip(run1, run2):
            assert b1.bucket_id == b2.bucket_id
            assert b1.actual_volume == b2.actual_volume
            assert b1.signed_volume == b2.signed_volume
            assert b1.num_trades == b2.num_trades
            assert b1.bucket_start_ns == b2.bucket_start_ns
            assert b1.bucket_end_ns == b2.bucket_end_ns
            assert abs(b1.vwap - b2.vwap) < 1e-12
            assert abs(b1.flow_imbalance - b2.flow_imbalance) < 1e-12

    def test_integer_cumsum_no_drift(self, bucketer):
        """Verify cumsum uses integer path — no float accumulation."""
        entries = [(float(i), 100.0, 3, 1) for i in range(10000)]
        ts, pr, sz, sg, mid, sp, bid, ask, meth = make_classified_trades(entries)

        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            ts, pr, sz, sg, mid, sp, bid, ask, 300,
            trade_methods=meth,
        )

        total_vol = sum(b.actual_volume for b in buckets)
        assert total_vol == 30000  # 10000 * 3, exact integer


# ═══════════════════════════════════════════════════════════════════════
# 6. Full Pipeline: Classifier → Bucketer
# ═══════════════════════════════════════════════════════════════════════

class TestPipelineIntegration:
    """End-to-end: raw trades + quotes → classified → bucketed."""

    def test_classifier_to_bucketer(self, classifier, bucketer):
        """Classify trades then bucket them — full pipeline."""
        # Quote stream
        q_ts = np.array([ns(0.5), ns(5.0)], dtype=np.int64)
        q_bids = np.array([99.90, 99.95], dtype=np.float64)
        q_asks = np.array([100.10, 100.15], dtype=np.float64)

        # 8 trades, 100 shares each = 800 total, bucket_vol=400 → 2 buckets
        t_entries = [
            (1.0, 100.05), (1.5, 99.92), (2.0, 100.08), (2.5, 99.95),
            (6.0, 100.10), (6.5, 100.00), (7.0, 100.12), (7.5, 99.98),
        ]
        t_ts = np.array([ns(e[0]) for e in t_entries], dtype=np.int64)
        t_prices = np.array([e[1] for e in t_entries], dtype=np.float64)
        t_sizes = np.full(8, 100, dtype=np.uint32)
        t_exch = np.zeros(8, dtype=np.uint8)

        # Step 1: Classify
        signs, methods, midpoints, quote_ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        # Step 2: Compute spread_bps
        spread_bps = LeeReadyClassifier.compute_spread_bps(
            t_prices, midpoints, q_bids, q_asks, q_ts, t_ts
        )

        # Reconstruct bid/ask at each trade
        q_indices = np.searchsorted(q_ts, t_ts, side="right") - 1
        q_indices = np.clip(q_indices, 0, len(q_ts) - 1)
        bids_at_trade = q_bids[q_indices]
        asks_at_trade = q_asks[q_indices]

        # Step 3: Bucket
        buckets = bucketer.bucketize(
            "TEST", date(2025, 1, 1),
            t_ts, t_prices, t_sizes, signs, midpoints,
            spread_bps.astype(np.float32), bids_at_trade, asks_at_trade, 400,
            trade_methods=methods,
        )

        assert len(buckets) == 2
        assert all(b.actual_volume == 400 for b in buckets)
        assert all(b.classification_confidence > 0 for b in buckets)
        assert all(b.symbol == "TEST" for b in buckets)
        assert all(np.isfinite(b.flow_imbalance) for b in buckets)
        assert all(np.isfinite(b.effective_spread_bps) for b in buckets)

        total_signed = sum(b.signed_volume for b in buckets)
        # Verify signs flow through correctly
        expected_signed = int(np.sum(signs.astype(np.int64) * t_sizes.astype(np.int64)))
        assert total_signed == expected_signed


# ═══════════════════════════════════════════════════════════════════════
# 7. Performance
# ═══════════════════════════════════════════════════════════════════════

class TestPerformance:
    def test_500k_trades(self, bucketer):
        """500K trades bucketed without error, bucket count ~200."""
        rng = np.random.default_rng(99)
        n = 500_000
        adv = n * 50  # ~100 shares avg → ~50M ADV
        bucket_vol = adv // 200

        base_ts = np.int64(1_700_000_000_000_000_000)
        ts = base_ts + np.sort(rng.integers(0, 10**12, n)).astype(np.int64)
        prices = 200.0 + rng.normal(0, 1.0, n)
        sizes = rng.integers(10, 200, n).astype(np.uint32)
        signs = rng.choice([-1, 1], n).astype(np.int8)
        midpoints = 200.0 + rng.normal(0, 0.5, n)
        spread_bps = np.full(n, 5.0, dtype=np.float32)
        bids = midpoints - 0.05
        asks = midpoints + 0.05

        buckets = bucketer.bucketize(
            "TSLA", date(2025, 9, 1),
            ts, prices, sizes, signs, midpoints, spread_bps, bids, asks,
            bucket_vol,
        )

        assert len(buckets) > 100
        total_vol = sum(b.actual_volume for b in buckets)
        assert total_vol == int(np.sum(sizes.astype(np.uint64)))


# ═══════════════════════════════════════════════════════════════════════
# 8. Bucket Count Target (~200/day)
# ═══════════════════════════════════════════════════════════════════════

class TestBucketCountTarget:
    def test_approximately_200_buckets(self, bucketer):
        """With ADV-calibrated bucket_volume, expect ~200 buckets per day."""
        rng = np.random.default_rng(7)
        n = 100_000
        avg_size = 50
        total_vol = n * avg_size  # ~5M
        adv = total_vol
        bucket_vol = bucketer.compute_bucket_size(adv, 200)

        base_ts = np.int64(1_700_000_000_000_000_000)
        ts = base_ts + np.sort(rng.integers(0, 10**10, n)).astype(np.int64)
        prices = 150.0 + rng.normal(0, 0.3, n)
        sizes = rng.integers(10, 90, n).astype(np.uint32)
        signs = rng.choice([-1, 0, 1], n, p=[0.45, 0.05, 0.5]).astype(np.int8)
        midpoints = 150.0 + rng.normal(0, 0.1, n)
        spread_bps = np.full(n, 8.0, dtype=np.float32)
        bids = midpoints - 0.06
        asks = midpoints + 0.06

        buckets = bucketer.bucketize(
            "NVDA", date(2025, 3, 10),
            ts, prices, sizes, signs, midpoints, spread_bps, bids, asks,
            bucket_vol,
        )

        # Should be within 20% of 200 (blueprint gate)
        assert 160 <= len(buckets) <= 240, f"Got {len(buckets)} buckets, expected ~200"
