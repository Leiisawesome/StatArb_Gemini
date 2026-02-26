"""
Tests for the Lee-Ready trade sign classifier.

Covers:
1. Quote rule: trades above/below midpoint
2. Tick rule: trades at midpoint with price history
3. Edge cases: no quotes, no trades, crossed quotes, stale quotes
4. Chunked classification with carry-forward
5. Quality metrics computation
6. Spread BPS computation
7. Spot-check with realistic trade/quote scenarios
"""

import numpy as np
import pytest
from datetime import date

from core_engine.microstructure.classification.lee_ready import (
    LeeReadyClassifier,
    ClassificationQuality,
    QUOTE_LAG_THRESHOLD_NS,
    _METHOD_QUOTE,
    _METHOD_TICK,
    _METHOD_INDETERMINATE,
)


@pytest.fixture
def classifier():
    return LeeReadyClassifier()


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def ns(ms: float) -> np.int64:
    """Convert milliseconds to nanoseconds."""
    return np.int64(int(ms * 1_000_000))


def make_quotes(entries):
    """Build quote arrays from list of (ms, bid, ask) tuples."""
    ts = np.array([ns(e[0]) for e in entries], dtype=np.int64)
    bids = np.array([e[1] for e in entries], dtype=np.float64)
    asks = np.array([e[2] for e in entries], dtype=np.float64)
    return ts, bids, asks


def make_trades(entries):
    """Build trade arrays from list of (ms, price, size) tuples."""
    ts = np.array([ns(e[0]) for e in entries], dtype=np.int64)
    prices = np.array([e[1] for e in entries], dtype=np.float64)
    sizes = np.array([e[2] for e in entries], dtype=np.uint32)
    exchanges = np.zeros(len(entries), dtype=np.uint8)
    return ts, prices, sizes, exchanges


# ═══════════════════════════════════════════════════════════════════════
# 1. Quote Rule Tests
# ═══════════════════════════════════════════════════════════════════════

class TestQuoteRule:
    """Trades clearly above or below midpoint → quote rule classification."""

    def test_buy_above_midpoint(self, classifier):
        """Trade at 100.10 with midpoint 100.00 → BUY."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([(2.0, 100.08, 100)])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert signs[0] == 1     # BUY
        assert methods[0] == _METHOD_QUOTE
        assert abs(mids[0] - 100.00) < 1e-6

    def test_sell_below_midpoint(self, classifier):
        """Trade at 99.92 with midpoint 100.00 → SELL."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([(2.0, 99.92, 100)])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert signs[0] == -1    # SELL
        assert methods[0] == _METHOD_QUOTE

    def test_multiple_trades_mixed(self, classifier):
        """Multiple trades at different prices relative to midpoint."""
        q_ts, q_bids, q_asks = make_quotes([
            (1.0, 99.90, 100.10),
        ])
        t_ts, t_prices, t_sizes, t_exch = make_trades([
            (2.0, 100.08, 100),   # above mid → BUY
            (3.0, 99.92, 200),    # below mid → SELL
            (4.0, 100.05, 150),   # above mid → BUY
            (5.0, 99.95, 50),     # below mid → SELL
        ])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        np.testing.assert_array_equal(signs, [1, -1, 1, -1])
        np.testing.assert_array_equal(methods, [_METHOD_QUOTE] * 4)

    def test_quote_updates_during_trades(self, classifier):
        """Quote changes between trades — each trade uses most recent."""
        q_ts, q_bids, q_asks = make_quotes([
            (1.0, 99.90, 100.10),    # mid = 100.00
            (3.5, 100.10, 100.30),   # mid = 100.20
        ])
        t_ts, t_prices, t_sizes, t_exch = make_trades([
            (2.0, 100.05, 100),  # quote1 mid=100.00 → above → BUY
            (4.0, 100.15, 100),  # quote2 mid=100.20 → below → SELL
        ])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert signs[0] == 1   # above 100.00
        assert signs[1] == -1  # below 100.20
        assert abs(mids[0] - 100.00) < 1e-6
        assert abs(mids[1] - 100.20) < 1e-6


# ═══════════════════════════════════════════════════════════════════════
# 2. Tick Rule Tests
# ═══════════════════════════════════════════════════════════════════════

class TestTickRule:
    """Trades at the midpoint fall back to tick rule."""

    def test_uptick_at_midpoint(self, classifier):
        """Trade at midpoint after price increase → BUY (tick rule)."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([
            (2.0, 99.95, 100),   # below mid → SELL (establishes price)
            (3.0, 100.00, 100),  # at mid, price up from 99.95 → BUY (tick)
        ])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert signs[0] == -1               # SELL by quote rule
        assert signs[1] == 1                 # BUY by tick rule
        assert methods[1] == _METHOD_TICK

    def test_downtick_at_midpoint(self, classifier):
        """Trade at midpoint after price decrease → SELL (tick rule)."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([
            (2.0, 100.05, 100),  # above mid → BUY
            (3.0, 100.00, 100),  # at mid, price down from 100.05 → SELL (tick)
        ])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert signs[0] == 1
        assert signs[1] == -1
        assert methods[1] == _METHOD_TICK

    def test_zero_tick_at_midpoint(self, classifier):
        """Trade at midpoint with same price as previous → use last direction."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([
            (2.0, 99.95, 100),   # below mid → SELL (establishes down direction)
            (3.0, 100.00, 100),  # at mid, price up → BUY
            (4.0, 100.00, 100),  # at mid, same price → carry forward (BUY)
        ])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert signs[2] == 1  # carries forward the uptick direction


# ═══════════════════════════════════════════════════════════════════════
# 3. Edge Cases
# ═══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases: empty inputs, crossed quotes, no prior quotes."""

    def test_empty_trades(self, classifier):
        """Zero trades → empty outputs."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts = np.array([], dtype=np.int64)
        t_prices = np.array([], dtype=np.float64)
        t_sizes = np.array([], dtype=np.uint32)
        t_exch = np.array([], dtype=np.uint8)

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert len(signs) == 0
        assert len(methods) == 0

    def test_empty_quotes(self, classifier):
        """Zero quotes → all trades indeterminate."""
        q_ts = np.array([], dtype=np.int64)
        q_bids = np.array([], dtype=np.float64)
        q_asks = np.array([], dtype=np.float64)
        t_ts, t_prices, t_sizes, t_exch = make_trades([(2.0, 100.0, 100)])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert signs[0] == 0
        assert methods[0] == _METHOD_INDETERMINATE

    def test_trade_before_any_quote(self, classifier):
        """Trade timestamp before first quote → indeterminate."""
        q_ts, q_bids, q_asks = make_quotes([(10.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([(5.0, 100.0, 100)])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert signs[0] == 0
        assert methods[0] == _METHOD_INDETERMINATE

    def test_crossed_quote_ignored(self, classifier):
        """Crossed quote (bid >= ask) → trade treated as no valid quote."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 100.10, 99.90)])  # crossed
        t_ts, t_prices, t_sizes, t_exch = make_trades([(2.0, 100.0, 100)])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert signs[0] == 0
        assert methods[0] == _METHOD_INDETERMINATE

    def test_locked_quote_ignored(self, classifier):
        """Locked quote (bid == ask, zero spread) → treated as invalid."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 100.0, 100.0)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([(2.0, 100.0, 100)])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert signs[0] == 0


# ═══════════════════════════════════════════════════════════════════════
# 4. Quote Age and Staleness
# ═══════════════════════════════════════════════════════════════════════

class TestQuoteAge:
    """Verify quote_age_ns computation and staleness detection."""

    def test_quote_age_computed_correctly(self, classifier):
        """quote_age = trade_ts - matched_quote_ts."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([(3.0, 100.05, 100)])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        expected_age_ns = ns(3.0) - ns(1.0)  # 2ms in nanoseconds
        assert ages[0] == expected_age_ns

    def test_stale_quote_detection(self, classifier):
        """Quotes older than threshold are flagged in quality metrics."""
        stale_delay = 100.0  # 100ms — well above 50ms threshold
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([
            (1.0 + stale_delay, 100.05, 100),
        ])

        signs, methods, mids, ages, quality = classifier.classify_day_chunked(
            "TEST", date(2025, 1, 1),
            t_ts, t_prices, t_sizes, t_exch,
            q_ts, q_bids, q_asks,
        )

        assert quality.stale_quote_pct == 1.0
        assert quality.mean_quote_age_ms > 50.0


# ═══════════════════════════════════════════════════════════════════════
# 5. Chunked Classification
# ═══════════════════════════════════════════════════════════════════════

class TestChunkedClassification:
    """Chunked processing with carry-forward produces same results as full-day."""

    def test_chunked_matches_full_day(self, classifier):
        """Chunked classification produces identical results to single-pass."""
        # Build a scenario spanning multiple "hours" (using small ns values for testing)
        q_entries = [
            (0.5, 99.90, 100.10),
            (5.0, 99.95, 100.15),  # New quote in "second hour"
        ]
        t_entries = [
            (1.0, 100.05, 100),   # First chunk
            (2.0, 99.92, 200),
            (6.0, 100.10, 150),   # Second chunk
            (7.0, 99.98, 50),
        ]

        q_ts, q_bids, q_asks = make_quotes(q_entries)
        t_ts, t_prices, t_sizes, t_exch = make_trades(t_entries)

        # Full-day classification
        signs_full, methods_full, mids_full, ages_full = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        # Chunked classification (small chunk to force splitting)
        signs_chunk, methods_chunk, mids_chunk, ages_chunk, _ = (
            classifier.classify_day_chunked(
                "TEST", date(2025, 1, 1),
                t_ts, t_prices, t_sizes, t_exch,
                q_ts, q_bids, q_asks,
                chunk_duration_ns=ns(4.0),  # Force split around 4ms
            )
        )

        np.testing.assert_array_equal(signs_full, signs_chunk)
        np.testing.assert_array_equal(mids_full, mids_chunk)

    def test_carry_forward_across_chunks(self, classifier):
        """Quote from chunk 1 is used for trade in chunk 2 when no new quote exists."""
        q_ts, q_bids, q_asks = make_quotes([
            (1.0, 99.90, 100.10),  # Only quote, in chunk 1
        ])
        t_ts, t_prices, t_sizes, t_exch = make_trades([
            (2.0, 100.05, 100),   # Chunk 1 — has quote
            (6.0, 99.95, 100),    # Chunk 2 — needs carry-forward
        ])

        signs, methods, mids, ages, quality = classifier.classify_day_chunked(
            "TEST", date(2025, 1, 1),
            t_ts, t_prices, t_sizes, t_exch,
            q_ts, q_bids, q_asks,
            chunk_duration_ns=ns(4.0),
        )

        # Both should be classified, not indeterminate
        assert signs[0] == 1    # above 100.00
        assert signs[1] == -1   # below 100.00
        assert np.isfinite(mids[1])


# ═══════════════════════════════════════════════════════════════════════
# 6. Quality Metrics
# ═══════════════════════════════════════════════════════════════════════

class TestQualityMetrics:
    """Quality metrics: counts, fractions, percentiles."""

    def test_quality_counts(self, classifier):
        """Buy/sell/indeterminate counts are correct."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([
            (2.0, 100.05, 100),   # BUY
            (3.0, 99.92, 100),    # SELL
            (4.0, 100.08, 100),   # BUY
        ])

        _, _, _, _, quality = classifier.classify_day_chunked(
            "TEST", date(2025, 1, 1),
            t_ts, t_prices, t_sizes, t_exch,
            q_ts, q_bids, q_asks,
        )

        assert quality.total_trades == 3
        assert quality.buy_count == 2
        assert quality.sell_count == 1
        assert quality.indeterminate_count == 0

    def test_tick_rule_fallback_counted(self, classifier):
        """Tick rule usage is tracked in quality metrics."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([
            (2.0, 99.95, 100),   # SELL by quote
            (3.0, 100.00, 100),  # at mid → tick rule
            (4.0, 100.00, 100),  # at mid → tick rule
            (5.0, 100.05, 100),  # BUY by quote
        ])

        _, _, _, _, quality = classifier.classify_day_chunked(
            "TEST", date(2025, 1, 1),
            t_ts, t_prices, t_sizes, t_exch,
            q_ts, q_bids, q_asks,
        )

        assert quality.tick_rule_fallback_pct == pytest.approx(0.5, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════
# 7. Spread BPS Computation
# ═══════════════════════════════════════════════════════════════════════

class TestSpreadBPS:
    """Test the static spread computation helper."""

    def test_spread_bps_basic(self, classifier):
        """Spread = (ask - bid) / mid * 10000."""
        q_ts, q_bids, q_asks = make_quotes([(1.0, 99.90, 100.10)])
        t_ts, t_prices, t_sizes, t_exch = make_trades([(2.0, 100.0, 100)])

        spreads = LeeReadyClassifier.compute_spread_bps(
            t_prices, np.array([100.0]),
            q_bids, q_asks, q_ts, t_ts,
        )

        expected = (100.10 - 99.90) / 100.0 * 10000  # = 20 bps
        assert abs(spreads[0] - expected) < 0.01


# ═══════════════════════════════════════════════════════════════════════
# 8. Spot-Check: Realistic 10-Trade Scenario
# ═══════════════════════════════════════════════════════════════════════

class TestSpotCheck:
    """
    Manual spot-check with 10 trades against known correct classifications.
    This simulates a realistic AAPL-like trading scenario.
    """

    def test_10_trade_spot_check(self, classifier):
        """
        10 trades with known correct signs verified by hand.

        Quote stream:
          t=0.0ms  bid=174.50 ask=174.52  → mid=174.51
          t=3.0ms  bid=174.51 ask=174.53  → mid=174.52
          t=7.0ms  bid=174.49 ask=174.51  → mid=174.50

        Trade stream with expected classifications:
          t=1.0  p=174.52  → above 174.51 → BUY  (quote rule)
          t=1.5  p=174.50  → below 174.51 → SELL (quote rule)
          t=2.0  p=174.51  → at mid 174.51 → SELL (tick: 174.50 → 174.51 is uptick) → BUY
          t=2.5  p=174.51  → at mid → BUY (tick: same price, carry forward uptick)
          t=4.0  p=174.53  → above 174.52 → BUY  (quote rule, new quote)
          t=4.5  p=174.52  → at mid 174.52 → SELL (tick: 174.53→174.52 is downtick)
          t=5.0  p=174.51  → below 174.52 → SELL (quote rule)
          t=5.5  p=174.52  → at mid 174.52 → BUY  (tick: 174.51→174.52 is uptick)
          t=8.0  p=174.50  → at mid 174.50 → SELL (tick: 174.52→174.50 is downtick, new quote)
          t=8.5  p=174.51  → above 174.50 → BUY  (quote rule, above new mid)
        """
        q_ts, q_bids, q_asks = make_quotes([
            (0.0, 174.50, 174.52),
            (3.0, 174.51, 174.53),
            (7.0, 174.49, 174.51),
        ])

        t_ts, t_prices, t_sizes, t_exch = make_trades([
            (1.0, 174.52, 100),
            (1.5, 174.50, 200),
            (2.0, 174.51, 150),
            (2.5, 174.51, 100),
            (4.0, 174.53, 300),
            (4.5, 174.52, 100),
            (5.0, 174.51, 250),
            (5.5, 174.52, 100),
            (8.0, 174.50, 200),
            (8.5, 174.51, 150),
        ])

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        expected_signs = np.array([1, -1, 1, 1, 1, -1, -1, 1, -1, 1], dtype=np.int8)
        expected_methods_type = [
            _METHOD_QUOTE,          # 1: above mid
            _METHOD_QUOTE,          # 2: below mid
            _METHOD_TICK,           # 3: at mid, uptick
            _METHOD_TICK,           # 4: at mid, carry forward uptick
            _METHOD_QUOTE,          # 5: above mid
            _METHOD_TICK,           # 6: at mid, downtick
            _METHOD_QUOTE,          # 7: below mid
            _METHOD_TICK,           # 8: at mid, uptick
            _METHOD_TICK,           # 9: at mid, downtick
            _METHOD_QUOTE,          # 10: above mid
        ]

        np.testing.assert_array_equal(signs, expected_signs)
        np.testing.assert_array_equal(
            methods, np.array(expected_methods_type, dtype=np.uint8)
        )

        # Verify midpoints changed with quote updates
        assert abs(mids[0] - 174.51) < 1e-6  # first quote
        assert abs(mids[4] - 174.52) < 1e-6  # second quote
        assert abs(mids[8] - 174.50) < 1e-6  # third quote

        # Accuracy check: all 10 trades classified (no indeterminates)
        assert np.sum(signs == 0) == 0
        accuracy = np.sum(signs != 0) / len(signs)
        assert accuracy >= 0.85  # Blueprint requirement: > 85%


# ═══════════════════════════════════════════════════════════════════════
# 9. Performance Sanity Check
# ═══════════════════════════════════════════════════════════════════════

class TestPerformance:
    """Verify the classifier handles large arrays without crashing."""

    def test_100k_trades(self, classifier):
        """Classify 100K trades — should complete in reasonable time."""
        rng = np.random.default_rng(42)
        n_trades = 100_000
        n_quotes = 50_000

        base_ts = np.int64(1_000_000_000_000_000_000)  # ~2001 in ns
        q_ts = base_ts + np.sort(rng.integers(0, 10**12, n_quotes)).astype(np.int64)
        q_bids = 100.0 + rng.normal(0, 0.1, n_quotes)
        q_asks = q_bids + rng.uniform(0.01, 0.05, n_quotes)

        t_ts = base_ts + np.sort(rng.integers(0, 10**12, n_trades)).astype(np.int64)
        t_prices = 100.0 + rng.normal(0, 0.1, n_trades)
        t_sizes = rng.integers(1, 1000, n_trades).astype(np.uint32)
        t_exch = np.zeros(n_trades, dtype=np.uint8)

        signs, methods, mids, ages = classifier.classify_trades(
            t_ts, t_prices, t_sizes, t_exch, q_ts, q_bids, q_asks
        )

        assert len(signs) == n_trades
        # Most trades should be classified (not indeterminate)
        classified_pct = np.sum(signs != 0) / n_trades
        assert classified_pct > 0.80
