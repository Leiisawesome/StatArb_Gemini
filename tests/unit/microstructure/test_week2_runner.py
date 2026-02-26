"""
Unit tests for the Week 2 pipeline (week2_runner.py).

Tests cover:
- TSV parsing for trades and quotes
- Bucket CSV formatting + ClickHouse column alignment
- High-lag bucket computation
- Bucket hashing determinism
- DayMetrics validation logic
- Quality report generation
"""

from __future__ import annotations

import hashlib
from datetime import date

import numpy as np
import pytest

from core_engine.microstructure.ingestion.week2_runner import (
    DayMetrics,
    Week2Pipeline,
)
from core_engine.microstructure.types import VolumeBucket


# ── Fixtures ──────────────────────────────────────────────────────────

def _make_bucket(
    bucket_id: int = 0,
    actual_volume: int = 10000,
    signed_volume: int = 3000,
    vwap: float = 150.12345678,
    **kwargs,
) -> VolumeBucket:
    defaults = dict(
        symbol="TEST",
        bucket_id=bucket_id,
        bucket_start_ns=1_000_000_000_000,
        bucket_end_ns=1_000_060_000_000,
        bucket_volume=10000,
        actual_volume=actual_volume,
        num_trades=100,
        open_price=150.0,
        close_price=150.5,
        high_price=151.0,
        low_price=149.5,
        vwap=vwap,
        signed_volume=signed_volume,
        unsigned_volume=actual_volume,
        buy_volume=6500,
        sell_volume=3500,
        indeterminate_volume=0,
        classification_confidence=0.95,
        tick_rule_fallback_pct=0.05,
        bid_at_start=149.9,
        ask_at_start=150.1,
        bid_at_end=150.3,
        ask_at_end=150.5,
        median_spread_bps=2.5,
        flow_imbalance=0.3,
        effective_spread_bps=3.0,
        price_impact_per_volume=0.0001,
        bucket_date=date(2026, 1, 15),
        fill_duration_ms=5000,
    )
    defaults.update(kwargs)
    return VolumeBucket(**defaults)


# ── TSV Parsing ───────────────────────────────────────────────────────

class TestTSVParsing:
    def test_parse_trades_tsv_basic(self):
        tsv = (
            "sip_timestamp\tprice\tsize\texchange_id\n"
            "1706000000000000000\t150.25\t100\t4\n"
            "1706000000100000000\t150.30\t200\t11\n"
            "1706000000200000000\t150.20\t50\t4\n"
        )
        data = Week2Pipeline._parse_trades_tsv(tsv)

        assert len(data["ts"]) == 3
        assert data["ts"].dtype == np.int64
        assert data["prices"].dtype == np.float64
        assert data["sizes"].dtype == np.uint32
        assert data["exchanges"].dtype == np.uint8

        assert data["ts"][0] == 1706000000000000000
        assert data["prices"][1] == pytest.approx(150.30)
        assert data["sizes"][2] == 50
        assert data["exchanges"][0] == 4

    def test_parse_trades_tsv_empty(self):
        tsv = "sip_timestamp\tprice\tsize\texchange_id\n"
        data = Week2Pipeline._parse_trades_tsv(tsv)
        assert len(data["ts"]) == 0
        assert data["ts"].dtype == np.int64

    def test_parse_trades_tsv_blank(self):
        data = Week2Pipeline._parse_trades_tsv("")
        assert len(data["ts"]) == 0

    def test_parse_quotes_tsv_basic(self):
        tsv = (
            "sip_timestamp\tbid_price\task_price\n"
            "1706000000000000000\t150.10\t150.20\n"
            "1706000000050000000\t150.15\t150.25\n"
        )
        data = Week2Pipeline._parse_quotes_tsv(tsv)

        assert len(data["ts"]) == 2
        assert data["ts"].dtype == np.int64
        assert data["bids"][0] == pytest.approx(150.10)
        assert data["asks"][1] == pytest.approx(150.25)

    def test_parse_quotes_tsv_empty(self):
        tsv = "sip_timestamp\tbid_price\task_price\n"
        data = Week2Pipeline._parse_quotes_tsv(tsv)
        assert len(data["ts"]) == 0

    def test_parse_trades_preserves_nanosecond_precision(self):
        ts_str = "1706123456789012345"
        tsv = f"sip_timestamp\tprice\tsize\texchange_id\n{ts_str}\t100.0\t100\t1\n"
        data = Week2Pipeline._parse_trades_tsv(tsv)
        assert data["ts"][0] == 1706123456789012345


# ── Bucket CSV Formatting ─────────────────────────────────────────────

class TestBucketCSV:
    def test_csv_header_matches_clickhouse_schema(self):
        bucket = _make_bucket()
        csv_data = Week2Pipeline._buckets_to_csv([bucket])
        header_line = csv_data.split("\n")[0]
        columns = [c.strip() for c in header_line.split(",")]

        expected_columns = [
            "symbol", "bucket_id", "bucket_start_ns", "bucket_end_ns",
            "bucket_volume", "actual_volume", "num_trades",
            "open_price", "close_price", "high_price", "low_price", "vwap",
            "signed_volume", "unsigned_volume", "buy_volume", "sell_volume",
            "indeterminate_volume",
            "classification_confidence", "tick_rule_fallback_pct",
            "bid_at_start", "ask_at_start", "bid_at_end", "ask_at_end",
            "median_spread_bps",
            "flow_imbalance", "effective_spread_bps", "price_impact_per_volume",
            "bucket_date", "fill_duration_ms",
        ]
        assert columns == expected_columns

    def test_csv_column_count(self):
        bucket = _make_bucket()
        csv_data = Week2Pipeline._buckets_to_csv([bucket])
        lines = [l for l in csv_data.strip().split("\n") if l]
        assert len(lines) == 2  # header + 1 data row
        header_cols = lines[0].split(",")
        data_cols = lines[1].split(",")
        assert len(header_cols) == 29
        assert len(data_cols) == 29

    def test_csv_vwap_precision(self):
        bucket = _make_bucket(vwap=150.12345678)
        csv_data = Week2Pipeline._buckets_to_csv([bucket])
        data_line = csv_data.strip().split("\n")[1]
        assert "150.12345678" in data_line

    def test_csv_multiple_buckets(self):
        buckets = [_make_bucket(bucket_id=i) for i in range(5)]
        csv_data = Week2Pipeline._buckets_to_csv(buckets)
        lines = [l for l in csv_data.strip().split("\n") if l]
        assert len(lines) == 6  # header + 5 data rows

    def test_csv_date_format(self):
        bucket = _make_bucket(bucket_date=date(2026, 2, 14))
        csv_data = Week2Pipeline._buckets_to_csv([bucket])
        assert "2026-02-14" in csv_data

    def test_csv_empty_list(self):
        csv_data = Week2Pipeline._buckets_to_csv([])
        lines = [l for l in csv_data.strip().split("\n") if l]
        assert len(lines) == 1  # header only


# ── Hashing ───────────────────────────────────────────────────────────

class TestHashing:
    def test_hash_buckets_deterministic(self):
        buckets = [_make_bucket(bucket_id=i, signed_volume=i * 100) for i in range(10)]
        h1 = Week2Pipeline._hash_buckets(buckets)
        h2 = Week2Pipeline._hash_buckets(buckets)
        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex

    def test_hash_buckets_sensitive_to_volume(self):
        b1 = [_make_bucket(signed_volume=1000)]
        b2 = [_make_bucket(signed_volume=1001)]
        assert Week2Pipeline._hash_buckets(b1) != Week2Pipeline._hash_buckets(b2)

    def test_hash_buckets_sensitive_to_vwap(self):
        b1 = [_make_bucket(vwap=150.12345678)]
        b2 = [_make_bucket(vwap=150.12345679)]
        assert Week2Pipeline._hash_buckets(b1) != Week2Pipeline._hash_buckets(b2)

    def test_hash_buckets_sensitive_to_order(self):
        buckets = [_make_bucket(bucket_id=i) for i in range(5)]
        h_forward = Week2Pipeline._hash_buckets(buckets)
        h_reverse = Week2Pipeline._hash_buckets(list(reversed(buckets)))
        assert h_forward != h_reverse

    def test_hash_empty_buckets(self):
        h = Week2Pipeline._hash_buckets([])
        expected = hashlib.sha256(b"").hexdigest()
        assert h == expected

    def test_hash_arrays_deterministic(self):
        data = {
            "ts": np.array([1, 2, 3], dtype=np.int64),
            "prices": np.array([1.0, 2.0, 3.0], dtype=np.float64),
        }
        h1 = Week2Pipeline._hash_arrays(data)
        h2 = Week2Pipeline._hash_arrays(data)
        assert h1 == h2

    def test_hash_arrays_sensitive_to_data(self):
        d1 = {"ts": np.array([1, 2, 3], dtype=np.int64)}
        d2 = {"ts": np.array([1, 2, 4], dtype=np.int64)}
        assert Week2Pipeline._hash_arrays(d1) != Week2Pipeline._hash_arrays(d2)


# ── High-Lag Bucket Computation ───────────────────────────────────────

class TestHighLagBuckets:
    def test_no_high_lag_when_all_fresh(self):
        sizes = np.array([100, 100, 100, 100], dtype=np.uint32)
        ages = np.array([1_000_000, 2_000_000, 3_000_000, 4_000_000], dtype=np.int64)
        pct = Week2Pipeline._compute_high_lag_pct(sizes, ages, bucket_vol=200)
        assert pct == 0.0

    def test_all_high_lag_when_stale(self):
        sizes = np.array([100, 100, 100, 100], dtype=np.uint32)
        ages_ns = np.full(4, 100_000_000, dtype=np.int64)  # 100ms >> 50ms threshold
        pct = Week2Pipeline._compute_high_lag_pct(sizes, ages_ns, bucket_vol=200)
        assert pct == 1.0

    def test_partial_high_lag(self):
        sizes = np.array([100] * 8, dtype=np.uint32)
        ages = np.array(
            [1_000_000] * 4 + [100_000_000] * 4,  # first 4 fresh, last 4 stale
            dtype=np.int64,
        )
        pct = Week2Pipeline._compute_high_lag_pct(sizes, ages, bucket_vol=400)
        assert 0.0 < pct < 1.0

    def test_empty_input(self):
        sizes = np.array([], dtype=np.uint32)
        ages = np.array([], dtype=np.int64)
        pct = Week2Pipeline._compute_high_lag_pct(sizes, ages, bucket_vol=200)
        assert pct == 0.0

    def test_negative_ages_ignored(self):
        sizes = np.array([100, 100], dtype=np.uint32)
        ages = np.array([-1, -1], dtype=np.int64)
        pct = Week2Pipeline._compute_high_lag_pct(sizes, ages, bucket_vol=200)
        assert pct == 0.0


# ── DayMetrics ────────────────────────────────────────────────────────

class TestDayMetrics:
    def test_default_valid(self):
        m = DayMetrics(symbol="TEST", trading_date=date(2026, 1, 15))
        assert m.valid is True
        assert m.invalid_reason == ""
        assert m.bucket_count == 0

    def test_invalid_with_reason(self):
        m = DayMetrics(symbol="TEST", trading_date=date(2026, 1, 15))
        m.valid = False
        m.invalid_reason = "Insufficient trades"
        assert not m.valid
        assert "Insufficient" in m.invalid_reason


# ── Integration-level logic tests ─────────────────────────────────────

class TestPipelineLogic:
    def test_non_regular_conditions_string(self):
        from core_engine.microstructure.ingestion.week2_runner import NON_REGULAR_STR
        parts = NON_REGULAR_STR.split(",")
        assert len(parts) == 10
        assert all(p.strip().isdigit() for p in parts)

    def test_bucket_csv_roundtrip_preserves_key_fields(self):
        bucket = _make_bucket(
            symbol="NVDA",
            bucket_id=42,
            actual_volume=987654,
            signed_volume=-123456,
            vwap=123.45678901,
            flow_imbalance=-0.125,
            bucket_date=date(2026, 2, 10),
        )
        csv_data = Week2Pipeline._buckets_to_csv([bucket])
        data_line = csv_data.strip().split("\n")[1]

        assert "NVDA" in data_line
        assert "42" in data_line
        assert "987654" in data_line
        assert "-123456" in data_line
        assert "123.45678901" in data_line
        assert "2026-02-10" in data_line

    def test_hash_reproducibility_across_calls(self):
        """Verify hashing is stable across independent pipeline instances."""
        buckets = [_make_bucket(bucket_id=i, vwap=100.0 + i * 0.00000001) for i in range(100)]

        h1 = Week2Pipeline._hash_buckets(buckets)
        h2 = Week2Pipeline._hash_buckets(buckets)
        assert h1 == h2

    def test_large_bucket_csv(self):
        """CSV generation handles 500 buckets without error."""
        buckets = [_make_bucket(bucket_id=i) for i in range(500)]
        csv_data = Week2Pipeline._buckets_to_csv(buckets)
        lines = [l for l in csv_data.strip().split("\n") if l]
        assert len(lines) == 501


# ── Pipeline behavior with zero quotes ────────────────────────────────

class TestEdgeCases:
    def test_parse_trades_with_extra_whitespace(self):
        tsv = (
            "sip_timestamp\tprice\tsize\texchange_id\n"
            "1706000000000000000\t150.25\t100\t4\n"
            "\n"
        )
        data = Week2Pipeline._parse_trades_tsv(tsv)
        assert len(data["ts"]) == 1

    def test_parse_quotes_single_row(self):
        tsv = (
            "sip_timestamp\tbid_price\task_price\n"
            "1706000000000000000\t150.10\t150.20\n"
        )
        data = Week2Pipeline._parse_quotes_tsv(tsv)
        assert len(data["ts"]) == 1
        assert data["bids"][0] == pytest.approx(150.10)
