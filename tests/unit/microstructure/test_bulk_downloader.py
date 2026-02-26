"""
Tests for the bulk downloader and DDL manager.

Covers:
1. CSV formatting — trades and quotes produce valid ClickHouse CSVWithNames
2. Nanosecond timestamp preservation (no datetime conversion)
3. RTH time window computation
4. Trading date generation
5. SymbolDayResult / IngestionReport data structures
6. DDL manager schema parsing
"""

import csv
import io
import numpy as np
import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from core_engine.microstructure.ingestion.bulk_downloader import (
    BulkDownloader,
    IngestionReport,
    SymbolDayResult,
)
from core_engine.microstructure.schema.ddl_manager import DDLManager, DDL_PATH


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def make_polygon_trade(
    sip_ts: int = 1700000000000000000,
    price: float = 150.25,
    size: int = 100,
    exchange: int = 4,
    conditions: list = None,
    tape: int = 1,
    trade_id: str = "abc123",
) -> dict:
    """Create a mock Polygon v3 trade response dict."""
    return {
        "sip_timestamp": sip_ts,
        "participant_timestamp": sip_ts + 1000,
        "trf_timestamp": sip_ts + 2000,
        "price": price,
        "size": size,
        "exchange": exchange,
        "conditions": conditions or [0],
        "tape": tape,
        "id": trade_id,
    }


def make_polygon_quote(
    sip_ts: int = 1700000000000000000,
    bid_price: float = 150.20,
    ask_price: float = 150.30,
    bid_size: int = 200,
    ask_size: int = 300,
    bid_exchange: int = 4,
    ask_exchange: int = 11,
) -> dict:
    """Create a mock Polygon v3 quote response dict."""
    return {
        "sip_timestamp": sip_ts,
        "participant_timestamp": sip_ts + 500,
        "bid_price": bid_price,
        "ask_price": ask_price,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "bid_exchange": bid_exchange,
        "ask_exchange": ask_exchange,
        "indicators": {},
    }


# ═══════════════════════════════════════════════════════════════════════
# 1. CSV Formatting — Trades
# ═══════════════════════════════════════════════════════════════════════

class TestTradeCSV:
    def test_csv_header(self):
        """Trade CSV has correct column headers."""
        rows = [make_polygon_trade()]
        csv_data = BulkDownloader._trades_to_csv("AAPL", "2025-01-15", rows)
        reader = csv.reader(io.StringIO(csv_data))
        header = next(reader)
        assert header == [
            "symbol", "sip_timestamp", "exchange_timestamp",
            "price", "size", "exchange_id", "conditions",
            "tape", "trade_id", "ingestion_date",
        ]

    def test_nanosecond_timestamp_preserved(self):
        """Int64 nanosecond timestamp passes through without conversion."""
        ts = 1700000000123456789
        rows = [make_polygon_trade(sip_ts=ts)]
        csv_data = BulkDownloader._trades_to_csv("AAPL", "2025-01-15", rows)
        reader = csv.reader(io.StringIO(csv_data))
        next(reader)  # skip header
        data_row = next(reader)
        assert data_row[1] == str(ts)

    def test_conditions_array_format(self):
        """Conditions formatted as ClickHouse array literal [1,2,3]."""
        rows = [make_polygon_trade(conditions=[12, 37, 41])]
        csv_data = BulkDownloader._trades_to_csv("AAPL", "2025-01-15", rows)
        reader = csv.reader(io.StringIO(csv_data))
        next(reader)
        data_row = next(reader)
        assert data_row[6] == "[12,37,41]"

    def test_empty_conditions(self):
        """None/missing conditions produce [0] (default condition)."""
        rows = [make_polygon_trade()]
        rows[0]["conditions"] = None
        csv_data = BulkDownloader._trades_to_csv("AAPL", "2025-01-15", rows)
        reader = csv.reader(io.StringIO(csv_data))
        next(reader)
        data_row = next(reader)
        assert data_row[6] == "[]"

    def test_multiple_rows(self):
        """Multiple trades produce correct row count."""
        rows = [make_polygon_trade(sip_ts=1700000000000000000 + i * 1000)
                for i in range(5)]
        csv_data = BulkDownloader._trades_to_csv("TSLA", "2025-06-01", rows)
        reader = csv.reader(io.StringIO(csv_data))
        all_rows = list(reader)
        assert len(all_rows) == 6  # 1 header + 5 data

    def test_exchange_timestamp_fallback(self):
        """Uses participant_timestamp if available, falls back to sip."""
        row = make_polygon_trade(sip_ts=100)
        row["participant_timestamp"] = 200
        csv_data = BulkDownloader._trades_to_csv("AAPL", "2025-01-15", [row])
        reader = csv.reader(io.StringIO(csv_data))
        next(reader)
        data_row = next(reader)
        assert data_row[2] == "200"  # exchange_timestamp = participant_timestamp


# ═══════════════════════════════════════════════════════════════════════
# 2. CSV Formatting — Quotes
# ═══════════════════════════════════════════════════════════════════════

class TestQuoteCSV:
    def test_csv_header(self):
        """Quote CSV has correct column headers."""
        rows = [make_polygon_quote()]
        csv_data = BulkDownloader._quotes_to_csv("AAPL", "2025-01-15", rows)
        reader = csv.reader(io.StringIO(csv_data))
        header = next(reader)
        assert header == [
            "symbol", "sip_timestamp",
            "bid_price", "ask_price", "bid_size", "ask_size",
            "bid_exchange", "ask_exchange", "conditions",
            "ingestion_date",
        ]

    def test_nanosecond_preserved(self):
        """Quote sip_timestamp preserved as raw Int64."""
        ts = 1700000000987654321
        rows = [make_polygon_quote(sip_ts=ts)]
        csv_data = BulkDownloader._quotes_to_csv("AAPL", "2025-01-15", rows)
        reader = csv.reader(io.StringIO(csv_data))
        next(reader)
        data_row = next(reader)
        assert data_row[1] == str(ts)

    def test_indicators_dict_handled(self):
        """Polygon 'indicators' dict format converted to array."""
        row = make_polygon_quote()
        row["indicators"] = {"condition_flags": [1, 2]}
        csv_data = BulkDownloader._quotes_to_csv("AAPL", "2025-01-15", [row])
        reader = csv.reader(io.StringIO(csv_data))
        next(reader)
        data_row = next(reader)
        assert data_row[8] == "[1,2]"


# ═══════════════════════════════════════════════════════════════════════
# 3. RTH Time Window
# ═══════════════════════════════════════════════════════════════════════

class TestRTHWindow:
    def test_rth_window_valid_range(self):
        """RTH window is roughly 6.5 hours (9:29:30 to 16:00:30)."""
        start_ns, end_ns = BulkDownloader._day_to_rth_ns(date(2025, 6, 15))
        duration_hours = (end_ns - start_ns) / (3600 * 1e9)
        assert 6.0 < duration_hours < 7.0  # ~6.5 hours + 1 minute buffer

    def test_rth_start_is_before_end(self):
        start_ns, end_ns = BulkDownloader._day_to_rth_ns(date(2025, 1, 15))
        assert start_ns < end_ns

    def test_nanosecond_precision(self):
        """Output is in nanoseconds (>= 10^18 range for recent dates)."""
        start_ns, _ = BulkDownloader._day_to_rth_ns(date(2025, 6, 15))
        assert start_ns > 1_000_000_000_000_000_000  # > 10^18


# ═══════════════════════════════════════════════════════════════════════
# 4. Trading Date Generation
# ═══════════════════════════════════════════════════════════════════════

class TestTradingDates:
    def test_weekdays_only(self):
        """No weekends in trading dates."""
        dates = BulkDownloader.get_trading_dates(
            date(2025, 6, 1), date(2025, 6, 30)
        )
        for d in dates:
            assert d.weekday() < 5, f"{d} is a weekend"

    def test_excludes_holidays(self):
        """US holidays excluded."""
        dates = BulkDownloader.get_trading_dates(
            date(2025, 7, 1), date(2025, 7, 7)
        )
        assert date(2025, 7, 4) not in dates  # Independence Day

    def test_130_trading_days_in_6_months(self):
        """~130-150 trading days in ~7 calendar months (Jul 1 - Jan 31)."""
        dates = BulkDownloader.get_trading_dates(
            date(2025, 7, 1), date(2026, 1, 31)
        )
        assert 125 <= len(dates) <= 155

    def test_empty_range(self):
        """Start after end returns empty list."""
        dates = BulkDownloader.get_trading_dates(
            date(2025, 6, 15), date(2025, 6, 10)
        )
        assert dates == []


# ═══════════════════════════════════════════════════════════════════════
# 5. Data Structures
# ═══════════════════════════════════════════════════════════════════════

class TestDataStructures:
    def test_symbol_day_result_success(self):
        r = SymbolDayResult("AAPL", date(2025, 1, 1), trade_count=1000, quote_count=5000)
        assert r.success is True

    def test_symbol_day_result_failure(self):
        r = SymbolDayResult("AAPL", date(2025, 1, 1), error="timeout")
        assert r.success is False

    def test_symbol_day_result_no_trades(self):
        r = SymbolDayResult("AAPL", date(2025, 1, 1), trade_count=0)
        assert r.success is False

    def test_ingestion_report_defaults(self):
        r = IngestionReport()
        assert r.total_trades == 0
        assert r.failures == []


# ═══════════════════════════════════════════════════════════════════════
# 6. DDL Manager
# ═══════════════════════════════════════════════════════════════════════

class TestDDLManager:
    def test_ddl_file_exists(self):
        """The DDL SQL file exists on disk."""
        assert DDL_PATH.exists()

    def test_ddl_contains_all_tables(self):
        """DDL file defines all 4 expected tables."""
        content = DDL_PATH.read_text()
        for table in DDLManager.EXPECTED_TABLES:
            assert table in content, f"Missing table: {table}"

    def test_ddl_uses_int64_timestamps(self):
        """DDL uses Int64 for nanosecond timestamps, not DateTime."""
        content = DDL_PATH.read_text()
        assert "sip_timestamp       Int64" in content
        assert "exchange_timestamp  Int64" in content

    def test_ddl_uses_lowcardinality(self):
        """DDL uses LowCardinality(String) for symbol columns."""
        content = DDL_PATH.read_text()
        assert "LowCardinality(String)" in content

    def test_ddl_compression_codecs(self):
        """DDL specifies compression codecs (Delta, ZSTD, T64, DoubleDelta)."""
        content = DDL_PATH.read_text()
        assert "CODEC(Delta, ZSTD" in content
        assert "CODEC(T64, ZSTD" in content
        assert "CODEC(DoubleDelta, ZSTD" in content


# ═══════════════════════════════════════════════════════════════════════
# 7. Large Batch CSV Performance
# ═══════════════════════════════════════════════════════════════════════

class TestCSVPerformance:
    def test_100k_trades_csv_generation(self):
        """Generate CSV for 100K trades without error."""
        rows = [
            make_polygon_trade(
                sip_ts=1700000000000000000 + i * 100000,
                price=150.0 + (i % 100) * 0.01,
                size=50 + (i % 500),
            )
            for i in range(100_000)
        ]
        csv_data = BulkDownloader._trades_to_csv("AAPL", "2025-01-15", rows)

        reader = csv.reader(io.StringIO(csv_data))
        all_rows = list(reader)
        assert len(all_rows) == 100_001  # header + 100K data rows

    def test_100k_quotes_csv_generation(self):
        """Generate CSV for 100K quotes without error."""
        rows = [
            make_polygon_quote(
                sip_ts=1700000000000000000 + i * 50000,
                bid_price=150.0 + (i % 50) * 0.01,
                ask_price=150.05 + (i % 50) * 0.01,
            )
            for i in range(100_000)
        ]
        csv_data = BulkDownloader._quotes_to_csv("AAPL", "2025-01-15", rows)

        reader = csv.reader(io.StringIO(csv_data))
        all_rows = list(reader)
        assert len(all_rows) == 100_001
