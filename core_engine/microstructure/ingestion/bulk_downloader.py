"""
Bulk historical data downloader for Polygon.io trades and quotes.

Uses _fetch_paginated_v3() from the existing PolygonRestService to preserve
raw Int64 nanosecond timestamps. Does NOT use get_historical_trades() or
get_historical_quotes() because they convert to Python datetime, losing
nanosecond precision.

Inserts directly into ClickHouse via HTTP POST in batched CSV format.

Blueprint: v1.6-FINAL Section 1.3
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from core_engine.data.feeds.polygon_rest import PolygonRestService, PolygonRestConfig
from core_engine.microstructure.constants import (
    DATASET_STORAGE_KILL_GB,
    DATASET_STORAGE_TARGET_GB,
)

logger = logging.getLogger(__name__)

# Polygon v3 API fields we extract (preserving raw integer timestamps)
TRADE_FIELDS = [
    "sip_timestamp", "participant_timestamp", "trf_timestamp",
    "price", "size", "exchange", "conditions", "tape", "id",
]
QUOTE_FIELDS = [
    "sip_timestamp", "participant_timestamp",
    "bid_price", "ask_price", "bid_size", "ask_size",
    "bid_exchange", "ask_exchange", "conditions",
]


@dataclass
class SymbolDayResult:
    """Result of downloading a single symbol-day."""
    symbol: str
    trading_date: date
    trade_count: int = 0
    quote_count: int = 0
    trade_pages: int = 0
    quote_pages: int = 0
    elapsed_seconds: float = 0.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and self.trade_count > 0


@dataclass
class IngestionReport:
    """Summary of a bulk download run."""
    total_trades: int = 0
    total_quotes: int = 0
    symbol_days_completed: int = 0
    symbol_days_failed: int = 0
    failures: List[Tuple[str, date, str]] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    estimated_storage_gb: float = 0.0


class BulkDownloader:
    """Downloads historical trades and quotes from Polygon.io into ClickHouse.

    Key design decisions:
    - Uses _fetch_paginated_v3() directly to preserve raw Int64 nanosecond timestamps
    - Batches inserts into ClickHouse via HTTP POST (CSV format, 100K rows per batch)
    - Per-symbol sequential day processing (ensures timestamp ordering)
    - Cross-symbol parallelism via asyncio.Semaphore
    - Storage monitoring: checks total GB after each symbol, halts at kill-switch
    """

    def __init__(
        self,
        polygon_service: PolygonRestService,
        clickhouse_url: str = "http://localhost:8123",
        batch_insert_size: int = 100_000,
        max_concurrent_symbols: int = 5,
        max_pages_per_request: int = 200,
    ):
        self._polygon = polygon_service
        self._ch_url = clickhouse_url
        self._batch_size = batch_insert_size
        self._max_concurrent = max_concurrent_symbols
        self._max_pages = max_pages_per_request

    # ── Public API ───────────────────────────────────────────────────

    async def download_trades(self, symbol: str, trading_date: date) -> int:
        """Download all trades for a symbol-day. Returns row count inserted."""
        start_ns, end_ns = self._day_to_rth_ns(trading_date)
        endpoint = f"{self._polygon.config.base_url}/v3/trades/{symbol.upper()}"
        params = {
            "timestamp.gte": start_ns,
            "timestamp.lte": end_ns,
            "order": "asc",
            "sort": "timestamp",
            "limit": 50000,
        }

        rows = await self._polygon._fetch_paginated_v3(
            endpoint, params, max_pages=self._max_pages
        )
        if not rows:
            return 0

        rows = self._dedup_by_timestamp(rows, "sip_timestamp")
        return await self._insert_trades(symbol, trading_date, rows)

    async def download_quotes(self, symbol: str, trading_date: date) -> int:
        """Download all NBBO quotes for a symbol-day. Returns row count inserted."""
        start_ns, end_ns = self._day_to_rth_ns(trading_date)
        endpoint = f"{self._polygon.config.base_url}/v3/quotes/{symbol.upper()}"
        params = {
            "timestamp.gte": start_ns,
            "timestamp.lte": end_ns,
            "order": "asc",
            "sort": "timestamp",
            "limit": 50000,
        }

        rows = await self._polygon._fetch_paginated_v3(
            endpoint, params, max_pages=self._max_pages
        )
        if not rows:
            return 0

        rows = self._dedup_by_timestamp(rows, "sip_timestamp")
        return await self._insert_quotes(symbol, trading_date, rows)

    async def download_symbol_day(
        self, symbol: str, trading_date: date
    ) -> SymbolDayResult:
        """Download both trades and quotes for a single symbol-day."""
        t0 = time.monotonic()
        result = SymbolDayResult(symbol=symbol, trading_date=trading_date)

        try:
            result.trade_count = await self.download_trades(symbol, trading_date)
            result.quote_count = await self.download_quotes(symbol, trading_date)
        except Exception as e:
            result.error = str(e)
            logger.error("Failed %s %s: %s", symbol, trading_date, e)

        result.elapsed_seconds = time.monotonic() - t0
        logger.info(
            "Downloaded %s %s: %d trades, %d quotes in %.1fs%s",
            symbol, trading_date, result.trade_count, result.quote_count,
            result.elapsed_seconds,
            f" ERROR: {result.error}" if result.error else "",
        )
        return result

    async def download_symbol_range(
        self,
        symbol: str,
        trading_dates: List[date],
    ) -> List[SymbolDayResult]:
        """Download all data for a symbol over a list of trading dates (sequential)."""
        results = []
        for d in trading_dates:
            r = await self.download_symbol_day(symbol, d)
            results.append(r)
        return results

    async def download_all(
        self,
        symbols: List[str],
        trading_dates: List[date],
        storage_check_interval: int = 10,
    ) -> IngestionReport:
        """
        Download all symbols over all dates with controlled concurrency.

        Per-symbol: days processed sequentially (timestamp ordering).
        Cross-symbol: parallel up to max_concurrent_symbols.

        Monitors storage after every `storage_check_interval` symbol-days.
        Halts if storage exceeds kill-switch.
        """
        t0 = time.monotonic()
        report = IngestionReport()
        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def process_symbol(sym: str) -> List[SymbolDayResult]:
            async with semaphore:
                return await self.download_symbol_range(sym, trading_dates)

        tasks = [process_symbol(s) for s in symbols]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        for sym_results in all_results:
            if isinstance(sym_results, Exception):
                report.symbol_days_failed += 1
                report.failures.append(("unknown", date.min, str(sym_results)))
                continue

            for r in sym_results:
                if r.success:
                    report.total_trades += r.trade_count
                    report.total_quotes += r.quote_count
                    report.symbol_days_completed += 1
                else:
                    report.symbol_days_failed += 1
                    if r.error:
                        report.failures.append((r.symbol, r.trading_date, r.error))

        report.elapsed_seconds = time.monotonic() - t0

        # Final storage check
        try:
            report.estimated_storage_gb = await self._check_storage()
        except Exception:
            pass

        logger.info(
            "Bulk download complete: %d trades, %d quotes, "
            "%d symbol-days OK, %d failed, %.1f hours, ~%.1f GB",
            report.total_trades, report.total_quotes,
            report.symbol_days_completed, report.symbol_days_failed,
            report.elapsed_seconds / 3600,
            report.estimated_storage_gb,
        )

        return report

    # ── ClickHouse Insert ────────────────────────────────────────────

    async def _insert_trades(
        self, symbol: str, trading_date: date, raw_rows: List[Dict[str, Any]]
    ) -> int:
        """Parse and batch-insert trade rows into ClickHouse."""
        date_str = trading_date.isoformat()
        inserted = 0

        for batch_start in range(0, len(raw_rows), self._batch_size):
            batch = raw_rows[batch_start : batch_start + self._batch_size]
            csv_data = self._trades_to_csv(symbol, date_str, batch)
            await self._ch_insert(
                "polygon_data.microstructure_trades", csv_data
            )
            inserted += len(batch)

        return inserted

    async def _insert_quotes(
        self, symbol: str, trading_date: date, raw_rows: List[Dict[str, Any]]
    ) -> int:
        """Parse and batch-insert quote rows into ClickHouse."""
        date_str = trading_date.isoformat()
        inserted = 0

        for batch_start in range(0, len(raw_rows), self._batch_size):
            batch = raw_rows[batch_start : batch_start + self._batch_size]
            csv_data = self._quotes_to_csv(symbol, date_str, batch)
            await self._ch_insert(
                "polygon_data.microstructure_quotes", csv_data
            )
            inserted += len(batch)

        return inserted

    async def _ch_insert(self, table: str, csv_data: str) -> None:
        """Insert CSV data into ClickHouse via HTTP POST."""
        query = f"INSERT INTO {table} FORMAT CSVWithNames"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._ch_url,
                params={"query": query},
                data=csv_data.encode("utf-8"),
                headers={"Content-Type": "text/csv"},
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"ClickHouse insert failed ({resp.status}): {body[:500]}"
                    )

    async def _check_storage(self) -> float:
        """Check total polygon_data storage in GB, raise if over kill-switch."""
        query = (
            "SELECT sum(bytes_on_disk) / 1073741824 AS gb "
            "FROM system.parts "
            "WHERE database = 'polygon_data' AND active = 1 "
            "FORMAT TSVWithNames"
        )
        async with aiohttp.ClientSession() as session:
            async with session.post(self._ch_url, data=query) as resp:
                text = await resp.text()
                for line in text.strip().split("\n")[1:]:
                    gb = float(line.strip())
                    if gb > DATASET_STORAGE_KILL_GB:
                        raise RuntimeError(
                            f"Storage kill-switch triggered: {gb:.1f} GB > "
                            f"{DATASET_STORAGE_KILL_GB} GB limit"
                        )
                    return gb
        return 0.0

    @staticmethod
    def _dedup_by_timestamp(
        rows: List[Dict[str, Any]], ts_field: str
    ) -> List[Dict[str, Any]]:
        """Remove rows with duplicate timestamps, keeping first occurrence."""
        seen: set = set()
        deduped: List[Dict[str, Any]] = []
        for row in rows:
            ts = row.get(ts_field)
            if ts not in seen:
                seen.add(ts)
                deduped.append(row)
        if len(deduped) < len(rows):
            logger.warning(
                "Deduplication removed %d/%d rows (%.1f%%)",
                len(rows) - len(deduped), len(rows),
                (len(rows) - len(deduped)) / len(rows) * 100,
            )
        return deduped

    # ── CSV Formatting ───────────────────────────────────────────────

    @staticmethod
    def _trades_to_csv(
        symbol: str, date_str: str, rows: List[Dict[str, Any]]
    ) -> str:
        """Convert raw Polygon trade dicts to ClickHouse CSV format.

        Preserves raw Int64 nanosecond timestamps — no datetime conversion.
        """
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "symbol", "sip_timestamp", "exchange_timestamp",
            "price", "size", "exchange_id", "conditions",
            "tape", "trade_id", "ingestion_date",
        ])

        for row in rows:
            sip_ts = row.get("sip_timestamp", 0)
            exch_ts = (
                row.get("participant_timestamp")
                or row.get("trf_timestamp")
                or sip_ts
            )

            conditions = row.get("conditions", []) or []
            cond_str = "[" + ",".join(str(c) for c in conditions) + "]"

            writer.writerow([
                symbol,
                sip_ts,
                exch_ts,
                row.get("price", 0),
                int(row.get("size", 0)),
                int(row.get("exchange", 0)),
                cond_str,
                int(row.get("tape", 0)),
                str(row.get("id", "")),
                date_str,
            ])

        return buf.getvalue()

    @staticmethod
    def _quotes_to_csv(
        symbol: str, date_str: str, rows: List[Dict[str, Any]]
    ) -> str:
        """Convert raw Polygon quote dicts to ClickHouse CSV format."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "symbol", "sip_timestamp",
            "bid_price", "ask_price", "bid_size", "ask_size",
            "bid_exchange", "ask_exchange", "conditions",
            "ingestion_date",
        ])

        for row in rows:
            sip_ts = row.get("sip_timestamp", 0)
            conditions = row.get("conditions") or row.get("indicators", {})
            if isinstance(conditions, dict):
                cond_list = []
                for v in conditions.values():
                    if isinstance(v, list):
                        cond_list.extend(v)
                cond_str = "[" + ",".join(str(c) for c in cond_list) + "]"
            elif isinstance(conditions, list):
                cond_str = "[" + ",".join(str(c) for c in conditions) + "]"
            else:
                cond_str = "[]"

            writer.writerow([
                symbol,
                sip_ts,
                row.get("bid_price", 0),
                row.get("ask_price", 0),
                int(row.get("bid_size", 0)),
                int(row.get("ask_size", 0)),
                int(row.get("bid_exchange", 0)),
                int(row.get("ask_exchange", 0)),
                cond_str,
                date_str,
            ])

        return buf.getvalue()

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _day_to_rth_ns(trading_date: date) -> Tuple[int, int]:
        """Convert a trading date to RTH (9:30-16:00 ET) nanosecond range.

        Extends window slightly to 9:29:30 - 16:00:30 to capture trades
        right at boundaries.
        """
        # US Eastern timezone offset: handle DST
        import zoneinfo
        et = zoneinfo.ZoneInfo("America/New_York")

        dt_open = datetime(
            trading_date.year, trading_date.month, trading_date.day,
            9, 29, 30, tzinfo=et
        )
        dt_close = datetime(
            trading_date.year, trading_date.month, trading_date.day,
            16, 0, 30, tzinfo=et
        )

        start_ns = int(dt_open.timestamp() * 1_000_000_000)
        end_ns = int(dt_close.timestamp() * 1_000_000_000)

        return start_ns, end_ns

    @staticmethod
    def get_trading_dates(start: date, end: date) -> List[date]:
        """Generate list of US trading dates (weekdays, excluding major holidays)."""
        from datetime import timedelta

        MAJOR_HOLIDAYS = {
            # 2025 holidays
            date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17),
            date(2025, 4, 18), date(2025, 5, 26), date(2025, 6, 19),
            date(2025, 7, 4), date(2025, 9, 1), date(2025, 11, 27),
            date(2025, 12, 25),
            # 2026 holidays
            date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16),
            date(2026, 4, 3), date(2026, 5, 25), date(2026, 6, 19),
            date(2026, 7, 3), date(2026, 9, 7), date(2026, 11, 26),
            date(2026, 12, 25),
        }

        dates = []
        current = start
        while current <= end:
            if current.weekday() < 5 and current not in MAJOR_HOLIDAYS:
                dates.append(current)
            current += timedelta(days=1)

        return dates
