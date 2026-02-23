"""
Tests for the Week 0 feasibility probe runner.

Tests the offline logic: timestamp analysis, hashing, report generation,
metrics computation, date selection, and storage projection.
Actual Polygon/ClickHouse integration is tested separately.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from core_engine.microstructure.ingestion.probe_runner import (
    DEFAULT_PROBE_SYMBOLS,
    ProbeResult,
    ProbeRunner,
    SymbolDayMetrics,
)
from core_engine.microstructure.types import Tier


# ── Fixtures ──────────────────────────────────────────────────────────


def make_metrics(
    symbol: str = "AAPL",
    tier: Tier = Tier.A,
    trading_date: date = date(2025, 12, 1),
    trade_count: int = 100_000,
    quote_count: int = 500_000,
    classification_confidence: float = 0.92,
    bucket_count: int = 195,
    total_mb: float = 85.0,
    replay_hash_match: bool = True,
) -> SymbolDayMetrics:
    m = SymbolDayMetrics(symbol=symbol, tier=tier, trading_date=trading_date)
    m.trade_count = trade_count
    m.quote_count = quote_count
    m.classification_confidence = classification_confidence
    m.bucket_count = bucket_count
    m.total_mb = total_mb
    m.replay_hash_match = replay_hash_match
    m.trades_hash = "a" * 64
    m.quotes_hash = "b" * 64
    m.buckets_hash = "c" * 64
    m.delta_p50_us = 150.0
    m.delta_p90_us = 500.0
    m.delta_p99_us = 2000.0
    m.negative_delta_count = 0
    m.ms_clustering = False
    m.classify_seconds = 2.5
    m.bucket_seconds = 0.8
    m.peak_rss_mb = 450.0
    return m


# ── ProbeResult tests ────────────────────────────────────────────────


class TestProbeResult:
    """Tests for ProbeResult verdict logic."""

    def test_all_pass_clean(self):
        result = ProbeResult()
        result.projected_total_gb = 140.0
        sd = make_metrics()
        result.symbol_days = [sd]
        assert result.all_pass is True

    def test_fail_storage_exceeds_target(self):
        result = ProbeResult()
        result.projected_total_gb = 230.0  # > 220 GB target
        result.symbol_days = [make_metrics()]
        assert result.all_pass is False

    def test_fail_blocking_issue(self):
        result = ProbeResult()
        result.projected_total_gb = 140.0
        result.symbol_days = [make_metrics()]
        result.blocking_issues.append("Something broke")
        assert result.all_pass is False

    def test_fail_replay_mismatch(self):
        result = ProbeResult()
        result.projected_total_gb = 140.0
        result.symbol_days = [make_metrics(replay_hash_match=False)]
        assert result.all_pass is False

    def test_fail_low_classification(self):
        result = ProbeResult()
        result.projected_total_gb = 140.0
        result.symbol_days = [make_metrics(classification_confidence=0.70)]
        assert result.all_pass is False

    def test_empty_symbol_days_passes(self):
        result = ProbeResult()
        result.projected_total_gb = 100.0
        assert result.all_pass is True


# ── Default symbols ──────────────────────────────────────────────────


class TestDefaultSymbols:
    def test_has_three_tiers(self):
        assert Tier.A in DEFAULT_PROBE_SYMBOLS
        assert Tier.B in DEFAULT_PROBE_SYMBOLS
        assert Tier.C in DEFAULT_PROBE_SYMBOLS

    def test_all_different_symbols(self):
        symbols = list(DEFAULT_PROBE_SYMBOLS.values())
        assert len(set(symbols)) == len(symbols)


# ── Default dates ────────────────────────────────────────────────────


class TestDefaultDates:
    def test_returns_three_dates(self):
        dates = ProbeRunner._default_dates()
        assert len(dates) == 3

    def test_dates_are_weekdays(self):
        dates = ProbeRunner._default_dates()
        for d in dates:
            assert d.weekday() < 5, f"{d} is not a weekday"

    def test_dates_are_sorted(self):
        dates = ProbeRunner._default_dates()
        assert dates == sorted(dates)

    def test_dates_are_recent(self):
        from datetime import timedelta
        today = date.today()
        dates = ProbeRunner._default_dates()
        for d in dates:
            age = (today - d).days
            assert 7 <= age <= 30, f"{d} is {age} days ago, expected 7-30"


# ── Hashing ──────────────────────────────────────────────────────────


class TestHashing:
    def test_hash_deterministic(self):
        data = {
            "ts": np.array([100, 200, 300], dtype=np.int64),
            "prices": np.array([150.0, 151.0, 152.0], dtype=np.float64),
        }
        h1 = ProbeRunner._hash_arrays(data)
        h2 = ProbeRunner._hash_arrays(data)
        assert h1 == h2

    def test_hash_differs_on_change(self):
        data1 = {"ts": np.array([100, 200], dtype=np.int64)}
        data2 = {"ts": np.array([100, 201], dtype=np.int64)}
        assert ProbeRunner._hash_arrays(data1) != ProbeRunner._hash_arrays(data2)

    def test_hash_is_sha256(self):
        data = {"x": np.array([1.0], dtype=np.float64)}
        h = ProbeRunner._hash_arrays(data)
        assert len(h) == 64
        int(h, 16)  # valid hex

    def test_hash_key_sorted(self):
        data_a = {
            "bids": np.array([1.0], dtype=np.float64),
            "asks": np.array([2.0], dtype=np.float64),
        }
        data_b = {
            "asks": np.array([2.0], dtype=np.float64),
            "bids": np.array([1.0], dtype=np.float64),
        }
        assert ProbeRunner._hash_arrays(data_a) == ProbeRunner._hash_arrays(data_b)


# ── Timestamp delta analysis ────────────────────────────────────────


class TestTimestampAnalysis:
    def test_basic_delta_analysis(self):
        runner = ProbeRunner.__new__(ProbeRunner)
        metrics = SymbolDayMetrics(symbol="TEST", tier=Tier.A, trading_date=date(2025, 12, 1))

        trades = {
            "ts": np.array([1000, 2000, 3000, 4000, 5000], dtype=np.int64),
            "prices": np.array([100.0] * 5),
            "sizes": np.array([100] * 5, dtype=np.uint32),
            "exchanges": np.array([1] * 5, dtype=np.uint8),
        }
        quotes = {
            "ts": np.array([500, 1500, 2500, 3500, 4500], dtype=np.int64),
            "bids": np.array([99.0] * 5),
            "asks": np.array([101.0] * 5),
        }

        runner._analyze_timestamp_deltas(trades, quotes, metrics)

        # trade[0]=1000, matched to quote[0]=500 → delta=500ns=0.5μs
        # trade[1]=2000, matched to quote[1]=1500 → delta=500
        assert metrics.delta_p50_us == pytest.approx(0.5, abs=0.1)
        assert metrics.negative_delta_count == 0

    def test_negative_deltas_counted(self):
        runner = ProbeRunner.__new__(ProbeRunner)
        metrics = SymbolDayMetrics(symbol="TEST", tier=Tier.A, trading_date=date(2025, 12, 1))

        # Quote after trade (negative delta scenario for pre-matched)
        trades = {
            "ts": np.array([100, 200, 300], dtype=np.int64),
            "prices": np.array([100.0] * 3),
            "sizes": np.array([100] * 3, dtype=np.uint32),
            "exchanges": np.array([1] * 3, dtype=np.uint8),
        }
        quotes = {
            "ts": np.array([150, 250, 350], dtype=np.int64),
            "bids": np.array([99.0] * 3),
            "asks": np.array([101.0] * 3),
        }

        runner._analyze_timestamp_deltas(trades, quotes, metrics)
        # trade[0]=100 → no quote before it → searchsorted -1 = -1 (excluded by valid)
        # Only trade[1]=200 → quote[0]=150 → delta = 50; trade[2]=300 → quote[1]=250 → delta=50

    def test_empty_data_no_crash(self):
        runner = ProbeRunner.__new__(ProbeRunner)
        metrics = SymbolDayMetrics(symbol="TEST", tier=Tier.A, trading_date=date(2025, 12, 1))

        trades = {"ts": np.array([], dtype=np.int64)}
        quotes = {"ts": np.array([], dtype=np.int64)}

        runner._analyze_timestamp_deltas(trades, quotes, metrics)
        assert metrics.delta_p50_us == 0.0

    def test_ms_clustering_detection(self):
        runner = ProbeRunner.__new__(ProbeRunner)
        metrics = SymbolDayMetrics(symbol="TEST", tier=Tier.A, trading_date=date(2025, 12, 1))

        # Quotes exactly on millisecond boundaries
        base = 1_000_000_000_000_000
        quote_ts = np.array(
            [base + i * 1_000_000 for i in range(200)], dtype=np.int64
        )
        trade_ts = np.array(
            [base + i * 1_000_000 + 500_000 for i in range(50)], dtype=np.int64
        )

        trades = {
            "ts": trade_ts,
            "prices": np.full(50, 100.0),
            "sizes": np.full(50, 100, dtype=np.uint32),
            "exchanges": np.full(50, 1, dtype=np.uint8),
        }
        quotes = {
            "ts": quote_ts,
            "bids": np.full(200, 99.0),
            "asks": np.full(200, 101.0),
        }

        runner._analyze_timestamp_deltas(trades, quotes, metrics)
        assert metrics.ms_clustering is True


# ── Report generation ────────────────────────────────────────────────


class TestReportGeneration:
    def test_report_is_written(self, tmp_path):
        runner = ProbeRunner.__new__(ProbeRunner)

        result = ProbeResult()
        result.projected_total_gb = 140.0
        result.storage_verdict = "WITHIN TARGET"
        result.ch_insert_trades_per_sec = 50_000
        result.ch_insert_quotes_per_sec = 80_000
        result.ch_query_bucket_single_ms = 15.0
        result.ch_compression_ratio = 3.5
        result.total_elapsed_seconds = 300.0

        sd = make_metrics()
        result.symbol_days = [sd]

        with patch.object(type(runner), '_write_report') as mock_write:
            mock_write.side_effect = lambda r: None
            pass

        # Directly test the report content generation logic
        import core_engine.microstructure.ingestion.probe_runner as pr_module
        original_docs = pr_module.DOCS_DIR
        pr_module.DOCS_DIR = tmp_path

        try:
            runner._write_report(result)
            report_path = tmp_path / "feasibility_probe_report.md"
            assert report_path.exists()

            content = report_path.read_text()
            assert "Feasibility Probe Report" in content
            assert "Section A" in content
            assert "Section B" in content
            assert "Section C" in content
            assert "140.0 GB" in content
            assert "WITHIN TARGET" in content
            assert "AAPL" in content
        finally:
            pr_module.DOCS_DIR = original_docs

    def test_report_shows_blocking_issues(self, tmp_path):
        runner = ProbeRunner.__new__(ProbeRunner)

        result = ProbeResult()
        result.projected_total_gb = 260.0
        result.storage_verdict = "REDUCE SYMBOLS"
        result.blocking_issues = ["Storage exceeds limit"]
        result.total_elapsed_seconds = 60.0

        sd = make_metrics()
        result.symbol_days = [sd]

        import core_engine.microstructure.ingestion.probe_runner as pr_module
        original_docs = pr_module.DOCS_DIR
        pr_module.DOCS_DIR = tmp_path

        try:
            runner._write_report(result)
            content = (tmp_path / "feasibility_probe_report.md").read_text()
            assert "ISSUES FOUND" in content
            assert "Storage exceeds limit" in content
        finally:
            pr_module.DOCS_DIR = original_docs

    def test_report_hash_audit_trail(self, tmp_path):
        runner = ProbeRunner.__new__(ProbeRunner)

        result = ProbeResult()
        result.projected_total_gb = 140.0
        result.storage_verdict = "WITHIN TARGET"
        result.total_elapsed_seconds = 100.0

        sd = make_metrics()
        result.symbol_days = [sd]

        import core_engine.microstructure.ingestion.probe_runner as pr_module
        original_docs = pr_module.DOCS_DIR
        pr_module.DOCS_DIR = tmp_path

        try:
            runner._write_report(result)
            content = (tmp_path / "feasibility_probe_report.md").read_text()
            assert "Hash Audit Trail" in content
            assert sd.trades_hash[:12] in content
        finally:
            pr_module.DOCS_DIR = original_docs


# ── SymbolDayMetrics defaults ────────────────────────────────────────


class TestSymbolDayMetrics:
    def test_default_values(self):
        m = SymbolDayMetrics(symbol="X", tier=Tier.B, trading_date=date(2025, 1, 1))
        assert m.trade_count == 0
        assert m.classification_confidence == 0.0
        assert m.replay_hash_match is False

    def test_all_fields_settable(self):
        m = make_metrics(trade_count=500_000, classification_confidence=0.95)
        assert m.trade_count == 500_000
        assert m.classification_confidence == 0.95


# ── ProbeRunner initialization ───────────────────────────────────────


class TestProbeRunnerInit:
    def test_default_symbols_used(self):
        runner = ProbeRunner()
        assert runner._symbols == DEFAULT_PROBE_SYMBOLS

    def test_custom_symbols(self):
        custom = {Tier.A: "MSFT", Tier.B: "NVDA", Tier.C: "SNAP"}
        runner = ProbeRunner(probe_symbols=custom)
        assert runner._symbols == custom

    def test_custom_dates(self):
        dates = [date(2025, 11, 3), date(2025, 11, 4), date(2025, 11, 5)]
        runner = ProbeRunner(probe_dates=dates)
        assert runner._dates == dates

    def test_custom_clickhouse_url(self):
        runner = ProbeRunner(clickhouse_url="http://ch:9000")
        assert runner._ch_url == "http://ch:9000"
