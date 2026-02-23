"""
Week 2 Pipeline: Classification + Bucketing + Data Quality Report + Replay Gate.

Processes all symbol-days from ClickHouse raw data:
  Load → Filter non-regular → Classify (Lee-Ready) → Bucket (Volume-Clock) →
  Insert buckets → SHA256 hash → Store diagnostics

Produces:
  - Volume buckets in polygon_data.microstructure_buckets
  - SHA256 hashes in polygon_data.microstructure_diagnostics
  - Data quality report in results/data_quality_report/

Blueprint: v1.6-FINAL, Week 2 specification
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import numpy as np
import yaml

from core_engine.microstructure.bucketing.volume_clock import VolumeClockBucketer
from core_engine.microstructure.classification.lee_ready import (
    LeeReadyClassifier,
    NON_REGULAR_CONDITIONS,
)
from core_engine.microstructure.constants import (
    CONSTANTS_VERSION,
    DATA_QUALITY_HIGH_LAG_BUCKET_MAX,
    DATA_QUALITY_MIN_QUOTE_MATCH_RATE,
    MAX_INVALID_DAY_PCT,
    MAX_STALE_QUOTE_PCT,
    MIN_TRADES_PER_DAY,
    QUOTE_LAG_THRESHOLD_MS,
    REPLAY_TEST_SYMBOL_DAYS,
    TARGET_BUCKETS_PER_DAY,
    TICK_RULE_FALLBACK_MAX_PCT,
)
from core_engine.microstructure.schema.ddl_manager import DDLManager
from core_engine.microstructure.types import VolumeBucket

logger = logging.getLogger(__name__)

NON_REGULAR_STR = ",".join(str(c) for c in sorted(NON_REGULAR_CONDITIONS))
QUOTE_LAG_THRESHOLD_NS = QUOTE_LAG_THRESHOLD_MS * 1_000_000

UNIVERSE_YAML = (
    Path(__file__).parents[2] / "config" / "catalog" / "microstructure" / "universe.yaml"
)
REPORT_DIR = Path(__file__).parents[3] / "results" / "data_quality_report"


@dataclass
class DayMetrics:
    """Quality metrics for one symbol-day of processing."""
    symbol: str
    trading_date: date
    total_trades: int = 0
    filtered_trades: int = 0
    non_regular_pct: float = 0.0
    quote_count: int = 0

    buy_count: int = 0
    sell_count: int = 0
    indeterminate_count: int = 0
    tick_rule_fallback_pct: float = 0.0
    stale_quote_pct: float = 0.0
    mean_quote_age_ms: float = 0.0
    quote_age_p50_ms: float = 0.0
    quote_age_p99_ms: float = 0.0
    classification_confidence: float = 0.0

    bucket_count: int = 0
    high_lag_bucket_pct: float = 0.0
    fill_duration_p10_ms: float = 0.0
    fill_duration_p50_ms: float = 0.0
    fill_duration_p90_ms: float = 0.0
    mean_bucket_confidence: float = 0.0

    trades_hash: str = ""
    quotes_hash: str = ""
    buckets_hash: str = ""

    classify_seconds: float = 0.0
    bucket_seconds: float = 0.0
    insert_seconds: float = 0.0

    valid: bool = True
    invalid_reason: str = ""


class Week2Pipeline:
    """Orchestrates Week 2: classify → bucket → quality report → replay gate."""

    def __init__(self, clickhouse_url: str = "http://localhost:8123"):
        self._ch_url = clickhouse_url
        self._classifier = LeeReadyClassifier()
        self._bucketer = VolumeClockBucketer()
        self._ddl_mgr = DDLManager(clickhouse_url)

        self._day_metrics: Dict[Tuple[str, date], DayMetrics] = {}
        self._symbols: List[str] = []
        self._tier_map: Dict[str, str] = {}
        self._adv_map: Dict[str, int] = {}

    def _load_universe_config(self) -> None:
        """Load symbols, tiers, and ADV from the frozen universe YAML."""
        with open(UNIVERSE_YAML) as f:
            config = yaml.safe_load(f)

        frozen = config["universe"]["frozen_classification"]["symbols"]
        for sym, info in frozen.items():
            self._symbols.append(sym)
            self._tier_map[sym] = info["tier"]
            self._adv_map[sym] = info["adv_shares"]

        self._symbols.sort()
        logger.info(
            "Loaded universe: %d symbols, tiers=%s",
            len(self._symbols),
            {s: self._tier_map[s] for s in self._symbols},
        )

    async def run(self, skip_existing: bool = True) -> bool:
        """
        Execute the full Week 2 pipeline.

        Returns True if all gates pass (replay + quality).
        """
        t0 = time.monotonic()
        self._load_universe_config()

        logger.info("=" * 60)
        logger.info("WEEK 2 PIPELINE — Classification + Bucketing")
        logger.info("Constants: %s", CONSTANTS_VERSION)
        logger.info("Symbols: %s", self._symbols)
        logger.info("=" * 60)

        await self._ddl_mgr.verify_schema()

        # Process each symbol sequentially
        for sym in self._symbols:
            await self._process_symbol(sym, skip_existing)

        elapsed = time.monotonic() - t0
        total_days = len(self._day_metrics)
        valid_days = sum(1 for m in self._day_metrics.values() if m.valid)
        total_buckets = sum(m.bucket_count for m in self._day_metrics.values())

        logger.info("=" * 60)
        logger.info(
            "CLASSIFICATION + BUCKETING COMPLETE: %d symbol-days processed "
            "(%d valid), %d buckets, %.1f hours",
            total_days, valid_days, total_buckets, elapsed / 3600,
        )

        # Replay gate
        replay_pass = await self._replay_gate()

        # Quality report
        report_pass = self._generate_quality_report()

        logger.info("=" * 60)
        logger.info("REPLAY GATE: %s", "PASS" if replay_pass else "FAIL")
        logger.info("QUALITY GATE: %s", "PASS" if report_pass else "ISSUES FLAGGED")
        logger.info("=" * 60)

        return replay_pass and report_pass

    async def _process_symbol(self, symbol: str, skip_existing: bool) -> None:
        """Process all days for one symbol."""
        dates = await self._get_symbol_dates(symbol)
        adv = self._adv_map[symbol]
        bucket_vol = self._bucketer.compute_bucket_size(adv, TARGET_BUCKETS_PER_DAY)
        tier = self._tier_map[symbol]

        logger.info(
            "─── %s (Tier %s) ── %d days, ADV=%d, bucket_vol=%d ───",
            symbol, tier, len(dates), adv, bucket_vol,
        )

        for i, trading_date in enumerate(dates):
            if skip_existing and await self._is_processed(symbol, trading_date):
                logger.debug("Skipping %s %s (already bucketed)", symbol, trading_date)
                continue

            metrics = DayMetrics(symbol=symbol, trading_date=trading_date)
            try:
                await self._process_symbol_day(
                    symbol, trading_date, bucket_vol, metrics
                )
            except Exception as e:
                logger.error("FAILED %s %s: %s", symbol, trading_date, e, exc_info=True)
                metrics.valid = False
                metrics.invalid_reason = str(e)[:200]

            self._day_metrics[(symbol, trading_date)] = metrics

            if (i + 1) % 10 == 0:
                logger.info(
                    "  %s progress: %d/%d days, latest: %d buckets",
                    symbol, i + 1, len(dates),
                    metrics.bucket_count,
                )

    async def _process_symbol_day(
        self, symbol: str, trading_date: date, bucket_vol: int, metrics: DayMetrics
    ) -> None:
        """Load → Filter → Classify → Bucket → Insert → Hash for one symbol-day."""
        date_str = trading_date.isoformat()

        # Load trades (filtered) and quotes
        trades, total_count = await self._load_trades(symbol, date_str)
        quotes = await self._load_quotes(symbol, date_str)

        metrics.total_trades = total_count
        metrics.filtered_trades = len(trades["ts"])
        metrics.non_regular_pct = (
            1.0 - metrics.filtered_trades / max(total_count, 1)
        )
        metrics.quote_count = len(quotes["ts"])

        if metrics.filtered_trades < MIN_TRADES_PER_DAY:
            metrics.valid = False
            metrics.invalid_reason = (
                f"Insufficient trades: {metrics.filtered_trades} < {MIN_TRADES_PER_DAY}"
            )
            logger.warning(
                "%s %s: only %d filtered trades, marking invalid",
                symbol, trading_date, metrics.filtered_trades,
            )
            return

        # Hash raw data
        metrics.trades_hash = self._hash_arrays(trades)
        metrics.quotes_hash = self._hash_arrays(quotes)

        # Classify
        t0 = time.monotonic()
        signs, methods, midpoints, quote_ages, quality = (
            self._classifier.classify_day_chunked(
                symbol, trading_date,
                trades["ts"], trades["prices"],
                trades["sizes"], trades["exchanges"],
                quotes["ts"], quotes["bids"], quotes["asks"],
            )
        )
        metrics.classify_seconds = time.monotonic() - t0
        metrics.buy_count = quality.buy_count
        metrics.sell_count = quality.sell_count
        metrics.indeterminate_count = quality.indeterminate_count
        metrics.tick_rule_fallback_pct = quality.tick_rule_fallback_pct
        metrics.stale_quote_pct = quality.stale_quote_pct
        metrics.mean_quote_age_ms = quality.mean_quote_age_ms
        metrics.quote_age_p50_ms = quality.quote_age_p50_ms
        metrics.quote_age_p99_ms = quality.quote_age_p99_ms
        classified = quality.buy_count + quality.sell_count
        metrics.classification_confidence = classified / max(quality.total_trades, 1)

        # Compute spread BPS and matched bid/ask for bucketer
        spread_bps = LeeReadyClassifier.compute_spread_bps(
            trades["prices"], midpoints,
            quotes["bids"], quotes["asks"],
            quotes["ts"], trades["ts"],
        ).astype(np.float32)

        q_indices = np.searchsorted(quotes["ts"], trades["ts"], side="right") - 1
        q_indices = np.clip(q_indices, 0, max(len(quotes["ts"]) - 1, 0))
        if len(quotes["bids"]) > 0:
            bids_at_trade = quotes["bids"][q_indices]
            asks_at_trade = quotes["asks"][q_indices]
        else:
            bids_at_trade = np.full(len(trades["ts"]), np.nan)
            asks_at_trade = np.full(len(trades["ts"]), np.nan)

        # Bucket
        t0 = time.monotonic()
        buckets = self._bucketer.bucketize(
            symbol, trading_date,
            trades["ts"], trades["prices"],
            trades["sizes"], signs, midpoints,
            spread_bps, bids_at_trade, asks_at_trade,
            bucket_vol, trade_methods=methods,
        )
        metrics.bucket_seconds = time.monotonic() - t0
        metrics.bucket_count = len(buckets)

        if buckets:
            durations = [b.fill_duration_ms for b in buckets]
            metrics.fill_duration_p10_ms = float(np.percentile(durations, 10))
            metrics.fill_duration_p50_ms = float(np.percentile(durations, 50))
            metrics.fill_duration_p90_ms = float(np.percentile(durations, 90))
            confidences = [b.classification_confidence for b in buckets]
            metrics.mean_bucket_confidence = float(np.mean(confidences))

            # High-lag bucket computation: partition quote_ages by bucket
            metrics.high_lag_bucket_pct = self._compute_high_lag_pct(
                trades["sizes"], quote_ages, bucket_vol
            )

        # Hash buckets
        metrics.buckets_hash = self._hash_buckets(buckets)

        # Insert buckets into ClickHouse
        if buckets:
            t0 = time.monotonic()
            await self._insert_buckets(buckets)
            metrics.insert_seconds = time.monotonic() - t0

        # Store hashes in diagnostics table
        await self._store_diagnostic(
            symbol, trading_date,
            {
                "trades_hash": metrics.trades_hash,
                "quotes_hash": metrics.quotes_hash,
                "buckets_hash": metrics.buckets_hash,
                "bucket_count": str(metrics.bucket_count),
                "classification_confidence": f"{metrics.classification_confidence:.4f}",
                "tick_rule_fallback_pct": f"{metrics.tick_rule_fallback_pct:.4f}",
            },
        )

    @staticmethod
    def _compute_high_lag_pct(
        trade_sizes: np.ndarray, quote_ages: np.ndarray, bucket_vol: int
    ) -> float:
        """Compute % of buckets where median quote_age exceeds threshold."""
        sizes_u64 = trade_sizes.astype(np.uint64)
        cum_vol = np.cumsum(sizes_u64)
        if len(cum_vol) == 0:
            return 0.0

        bucket_boundaries = np.arange(
            np.uint64(bucket_vol),
            cum_vol[-1] + np.uint64(bucket_vol),
            np.uint64(bucket_vol),
            dtype=np.uint64,
        )
        ends = np.searchsorted(cum_vol, bucket_boundaries)
        ends = np.clip(ends, 0, len(trade_sizes) - 1)
        unique_mask = np.concatenate([[True], np.diff(ends) > 0])
        ends = ends[unique_mask]

        starts = np.concatenate([[0], ends[:-1] + 1])
        n_buckets = len(starts)
        if n_buckets == 0:
            return 0.0

        high_lag_count = 0
        for s, e in zip(starts, ends):
            bucket_ages = quote_ages[s : e + 1]
            valid_ages = bucket_ages[bucket_ages >= 0]
            if len(valid_ages) > 0:
                median_age_ns = float(np.median(valid_ages))
                if median_age_ns > QUOTE_LAG_THRESHOLD_NS:
                    high_lag_count += 1

        return high_lag_count / n_buckets

    # ── Data loading ──────────────────────────────────────────────────

    async def _load_trades(
        self, symbol: str, date_str: str
    ) -> Tuple[Dict[str, np.ndarray], int]:
        """
        Load trades from ClickHouse, filtering non-regular conditions.

        Returns (data_dict, total_count_before_filter).
        """
        count_result = await self._ch_query(
            f"SELECT count() FROM polygon_data.microstructure_trades "
            f"WHERE symbol = '{symbol}' AND ingestion_date = '{date_str}' "
            f"FORMAT TSVWithNames"
        )
        total_count = 0
        for line in count_result.strip().split("\n")[1:]:
            total_count = int(line.strip())

        data_query = (
            f"SELECT sip_timestamp, price, size, exchange_id "
            f"FROM polygon_data.microstructure_trades "
            f"WHERE symbol = '{symbol}' AND ingestion_date = '{date_str}' "
            f"AND NOT hasAny(conditions, [{NON_REGULAR_STR}]) "
            f"ORDER BY sip_timestamp ASC "
            f"FORMAT TSVWithNames"
        )
        result = await self._ch_query(data_query, timeout=300)
        return self._parse_trades_tsv(result), total_count

    async def _load_quotes(
        self, symbol: str, date_str: str
    ) -> Dict[str, np.ndarray]:
        """Load quotes from ClickHouse into numpy arrays."""
        query = (
            f"SELECT sip_timestamp, bid_price, ask_price "
            f"FROM polygon_data.microstructure_quotes "
            f"WHERE symbol = '{symbol}' AND ingestion_date = '{date_str}' "
            f"ORDER BY sip_timestamp ASC "
            f"FORMAT TSVWithNames"
        )
        result = await self._ch_query(query, timeout=300)
        return self._parse_quotes_tsv(result)

    @staticmethod
    def _parse_trades_tsv(result: str) -> Dict[str, np.ndarray]:
        lines = result.strip().split("\n")
        if len(lines) <= 1:
            return {
                "ts": np.array([], dtype=np.int64),
                "prices": np.array([], dtype=np.float64),
                "sizes": np.array([], dtype=np.uint32),
                "exchanges": np.array([], dtype=np.uint8),
            }
        data_lines = lines[1:]
        ts, prices, sizes, exchanges = [], [], [], []
        for line in data_lines:
            parts = line.split("\t")
            if len(parts) >= 4:
                ts.append(int(parts[0]))
                prices.append(float(parts[1]))
                sizes.append(int(parts[2]))
                exchanges.append(int(parts[3]))
        return {
            "ts": np.array(ts, dtype=np.int64),
            "prices": np.array(prices, dtype=np.float64),
            "sizes": np.array(sizes, dtype=np.uint32),
            "exchanges": np.array(exchanges, dtype=np.uint8),
        }

    @staticmethod
    def _parse_quotes_tsv(result: str) -> Dict[str, np.ndarray]:
        lines = result.strip().split("\n")
        if len(lines) <= 1:
            return {
                "ts": np.array([], dtype=np.int64),
                "bids": np.array([], dtype=np.float64),
                "asks": np.array([], dtype=np.float64),
            }
        data_lines = lines[1:]
        ts, bids, asks = [], [], []
        for line in data_lines:
            parts = line.split("\t")
            if len(parts) >= 3:
                ts.append(int(parts[0]))
                bids.append(float(parts[1]))
                asks.append(float(parts[2]))
        return {
            "ts": np.array(ts, dtype=np.int64),
            "bids": np.array(bids, dtype=np.float64),
            "asks": np.array(asks, dtype=np.float64),
        }

    # ── ClickHouse operations ─────────────────────────────────────────

    async def _ch_query(self, query: str, timeout: int = 120) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._ch_url,
                data=query,
                headers={"Content-Type": "text/plain"},
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(
                        f"ClickHouse query failed ({resp.status}): {text[:500]}"
                    )
                return text

    async def _ch_insert(self, table: str, csv_data: str) -> None:
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

    async def _get_symbol_dates(self, symbol: str) -> List[date]:
        """Get all ingestion dates for a symbol, sorted ascending."""
        result = await self._ch_query(
            f"SELECT DISTINCT ingestion_date "
            f"FROM polygon_data.microstructure_trades "
            f"WHERE symbol = '{symbol}' "
            f"ORDER BY ingestion_date ASC "
            f"FORMAT TSVWithNames"
        )
        dates = []
        for line in result.strip().split("\n")[1:]:
            line = line.strip()
            if line:
                dates.append(date.fromisoformat(line))
        return dates

    async def _is_processed(self, symbol: str, trading_date: date) -> bool:
        """Check if buckets already exist for this symbol-day."""
        result = await self._ch_query(
            f"SELECT count() FROM polygon_data.microstructure_buckets "
            f"WHERE symbol = '{symbol}' AND bucket_date = '{trading_date.isoformat()}' "
            f"FORMAT TSVWithNames"
        )
        for line in result.strip().split("\n")[1:]:
            return int(line.strip()) > 0
        return False

    async def _insert_buckets(self, buckets: List[VolumeBucket]) -> None:
        """Insert volume buckets into ClickHouse."""
        csv_data = self._buckets_to_csv(buckets)
        await self._ch_insert("polygon_data.microstructure_buckets", csv_data)

    @staticmethod
    def _buckets_to_csv(buckets: List[VolumeBucket]) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
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
        ])
        for b in buckets:
            writer.writerow([
                b.symbol, b.bucket_id, b.bucket_start_ns, b.bucket_end_ns,
                b.bucket_volume, b.actual_volume, b.num_trades,
                b.open_price, b.close_price, b.high_price, b.low_price,
                f"{b.vwap:.8f}",
                b.signed_volume, b.unsigned_volume, b.buy_volume, b.sell_volume,
                b.indeterminate_volume,
                f"{b.classification_confidence:.6f}",
                f"{b.tick_rule_fallback_pct:.6f}",
                b.bid_at_start, b.ask_at_start, b.bid_at_end, b.ask_at_end,
                f"{b.median_spread_bps:.4f}",
                f"{b.flow_imbalance:.6f}",
                f"{b.effective_spread_bps:.4f}",
                f"{b.price_impact_per_volume:.10f}",
                b.bucket_date.isoformat(), b.fill_duration_ms,
            ])
        return buf.getvalue()

    async def _store_diagnostic(
        self, symbol: str, trading_date: date, metrics_dict: Dict[str, str]
    ) -> None:
        """Store per-symbol-day hashes and metrics in diagnostics table."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "run_id", "constants_version", "symbol", "metric_name",
            "metric_value", "metric_metadata", "computed_at", "run_date",
        ])
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        run_id = f"week2_{trading_date.isoformat()}"
        for name, value in metrics_dict.items():
            try:
                float_val = float(value)
            except ValueError:
                float_val = 0.0
            writer.writerow([
                run_id, CONSTANTS_VERSION, symbol, name,
                float_val,
                json.dumps({"raw": value, "date": trading_date.isoformat()}),
                now, trading_date.isoformat(),
            ])
        try:
            await self._ch_insert("polygon_data.microstructure_diagnostics", buf.getvalue())
        except Exception as e:
            logger.warning("Failed to store diagnostics for %s %s: %s", symbol, trading_date, e)

    # ── Hashing ───────────────────────────────────────────────────────

    @staticmethod
    def _hash_arrays(data: Dict[str, np.ndarray]) -> str:
        h = hashlib.sha256()
        for key in sorted(data.keys()):
            h.update(data[key].tobytes())
        return h.hexdigest()

    @staticmethod
    def _hash_buckets(buckets: List[VolumeBucket]) -> str:
        bucket_repr = "|".join(
            f"{b.bucket_id},{b.actual_volume},{b.signed_volume},{b.vwap:.8f}"
            for b in buckets
        )
        return hashlib.sha256(bucket_repr.encode()).hexdigest()

    # ── Replay gate ───────────────────────────────────────────────────

    async def _replay_gate(self) -> bool:
        """
        Re-run pipeline on N random symbol-days and compare bucket hashes.

        Blueprint: "If ANY difference → pipeline has non-determinism. Fix before Week 3."
        """
        valid_keys = [
            k for k, m in self._day_metrics.items()
            if m.valid and m.bucket_count > 0
        ]
        if not valid_keys:
            logger.error("No valid symbol-days for replay gate!")
            return False

        n = min(REPLAY_TEST_SYMBOL_DAYS, len(valid_keys))
        test_keys = random.sample(valid_keys, n)

        logger.info("=" * 60)
        logger.info("DETERMINISTIC REPLAY GATE — %d symbol-days", n)

        all_pass = True
        for symbol, trading_date in test_keys:
            original_hash = self._day_metrics[(symbol, trading_date)].buckets_hash
            replay_hash = await self._replay_single(symbol, trading_date)

            match = replay_hash == original_hash
            logger.info(
                "  %s %s: %s (orig=%s... replay=%s...)",
                symbol, trading_date,
                "PASS" if match else "FAIL",
                original_hash[:12], replay_hash[:12],
            )
            if not match:
                all_pass = False

        logger.info(
            "REPLAY GATE: %s (%d/%d passed)",
            "PASS" if all_pass else "FAIL", n if all_pass else 0, n,
        )
        return all_pass

    async def _replay_single(self, symbol: str, trading_date: date) -> str:
        """Re-run classification + bucketing for one symbol-day, return bucket hash."""
        date_str = trading_date.isoformat()
        trades, _ = await self._load_trades(symbol, date_str)
        quotes = await self._load_quotes(symbol, date_str)

        signs, methods, midpoints, quote_ages, _ = (
            self._classifier.classify_day_chunked(
                symbol, trading_date,
                trades["ts"], trades["prices"],
                trades["sizes"], trades["exchanges"],
                quotes["ts"], quotes["bids"], quotes["asks"],
            )
        )

        spread_bps = LeeReadyClassifier.compute_spread_bps(
            trades["prices"], midpoints,
            quotes["bids"], quotes["asks"],
            quotes["ts"], trades["ts"],
        ).astype(np.float32)

        q_idx = np.searchsorted(quotes["ts"], trades["ts"], side="right") - 1
        q_idx = np.clip(q_idx, 0, max(len(quotes["ts"]) - 1, 0))
        bids_at = quotes["bids"][q_idx] if len(quotes["bids"]) > 0 else np.full(len(trades["ts"]), np.nan)
        asks_at = quotes["asks"][q_idx] if len(quotes["asks"]) > 0 else np.full(len(trades["ts"]), np.nan)

        adv = self._adv_map[symbol]
        bucket_vol = self._bucketer.compute_bucket_size(adv, TARGET_BUCKETS_PER_DAY)

        buckets = self._bucketer.bucketize(
            symbol, trading_date,
            trades["ts"], trades["prices"],
            trades["sizes"], signs, midpoints,
            spread_bps, bids_at, asks_at,
            bucket_vol, trade_methods=methods,
        )
        return self._hash_buckets(buckets)

    # ── Quality report ────────────────────────────────────────────────

    def _generate_quality_report(self) -> bool:
        """
        Generate the Week 2 data quality report.

        Returns True if no structural quality issues found.
        """
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / "week2_data_quality_report.md"

        issues: List[str] = []

        # Per-symbol aggregation
        sym_agg: Dict[str, Dict[str, Any]] = {}
        for sym in self._symbols:
            sym_days = [
                m for (s, _), m in self._day_metrics.items() if s == sym
            ]
            if not sym_days:
                continue

            valid_days = [m for m in sym_days if m.valid]
            invalid_count = len(sym_days) - len(valid_days)
            invalid_pct = invalid_count / max(len(sym_days), 1)

            if invalid_pct > MAX_INVALID_DAY_PCT:
                issues.append(
                    f"{sym}: {invalid_pct:.1%} invalid days (>{MAX_INVALID_DAY_PCT:.0%})"
                )

            if not valid_days:
                sym_agg[sym] = {"total_days": len(sym_days), "valid_days": 0}
                continue

            quote_match_rates = [m.classification_confidence for m in valid_days]
            mean_quote_match = float(np.mean(quote_match_rates))
            if mean_quote_match < DATA_QUALITY_MIN_QUOTE_MATCH_RATE:
                issues.append(
                    f"{sym}: quote match rate {mean_quote_match:.1%} "
                    f"< {DATA_QUALITY_MIN_QUOTE_MATCH_RATE:.0%}"
                )

            tick_fallback = [m.tick_rule_fallback_pct for m in valid_days]
            mean_tick_fallback = float(np.mean(tick_fallback))
            if mean_tick_fallback > TICK_RULE_FALLBACK_MAX_PCT:
                issues.append(
                    f"{sym}: tick rule fallback {mean_tick_fallback:.1%} "
                    f"> {TICK_RULE_FALLBACK_MAX_PCT:.0%}"
                )

            stale_pcts = [m.stale_quote_pct for m in valid_days]
            mean_stale = float(np.mean(stale_pcts))
            if mean_stale > MAX_STALE_QUOTE_PCT:
                issues.append(
                    f"{sym}: stale quote % {mean_stale:.1%} > {MAX_STALE_QUOTE_PCT:.0%}"
                )

            high_lag_pcts = [m.high_lag_bucket_pct for m in valid_days]
            mean_high_lag = float(np.mean(high_lag_pcts))

            ages_ms = [m.mean_quote_age_ms for m in valid_days if m.mean_quote_age_ms > 0]
            median_age = float(np.median(ages_ms)) if ages_ms else 0.0

            bucket_counts = [m.bucket_count for m in valid_days]
            fill_p50s = [m.fill_duration_p50_ms for m in valid_days if m.fill_duration_p50_ms > 0]
            confidences = [m.mean_bucket_confidence for m in valid_days if m.mean_bucket_confidence > 0]

            non_regular_pcts = [m.non_regular_pct for m in valid_days]

            # Odd-lot days: days where >50% of total trades were filtered
            odd_lot_days = sum(1 for m in valid_days if m.non_regular_pct > 0.50)

            sym_agg[sym] = {
                "total_days": len(sym_days),
                "valid_days": len(valid_days),
                "invalid_count": invalid_count,
                "invalid_pct": invalid_pct,
                "tier": self._tier_map[sym],
                "mean_quote_match": mean_quote_match,
                "mean_tick_fallback": mean_tick_fallback,
                "mean_stale": mean_stale,
                "mean_high_lag": mean_high_lag,
                "median_quote_age_ms": median_age,
                "mean_bucket_count": float(np.mean(bucket_counts)),
                "total_buckets": sum(bucket_counts),
                "fill_p10": float(np.percentile(
                    [m.fill_duration_p10_ms for m in valid_days], 10
                )) if valid_days else 0,
                "fill_p50": float(np.median(fill_p50s)) if fill_p50s else 0,
                "fill_p90": float(np.percentile(
                    [m.fill_duration_p90_ms for m in valid_days], 90
                )) if valid_days else 0,
                "mean_confidence": float(np.mean(confidences)) if confidences else 0,
                "non_regular_pct": float(np.mean(non_regular_pcts)),
                "odd_lot_days": odd_lot_days,
                "classify_total_s": sum(m.classify_seconds for m in valid_days),
                "bucket_total_s": sum(m.bucket_seconds for m in valid_days),
            }

        # Write report
        lines = [
            "# Week 2 — Data Quality Report",
            "",
            f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Constants Version**: {CONSTANTS_VERSION}",
            f"**Total symbol-days**: {len(self._day_metrics)}",
            f"**Valid symbol-days**: {sum(1 for m in self._day_metrics.values() if m.valid)}",
            "",
            "---",
            "",
            "## Per-Symbol Summary",
            "",
            "| Symbol | Tier | Days | Valid | Quote Match | Tick Rule % | "
            "Stale % | High-Lag % | Med Age (ms) | Buckets/Day | Confidence |",
            "|--------|------|------|-------|-------------|-------------|"
            "---------|------------|--------------|-------------|------------|",
        ]

        for sym in self._symbols:
            agg = sym_agg.get(sym)
            if not agg or agg.get("valid_days", 0) == 0:
                lines.append(f"| {sym} | {self._tier_map.get(sym, '?')} | "
                             f"{agg['total_days'] if agg else 0} | 0 | — | — | — | — | — | — | — |")
                continue
            lines.append(
                f"| {sym} | {agg['tier']} | {agg['total_days']} | {agg['valid_days']} | "
                f"{agg['mean_quote_match']:.1%} | {agg['mean_tick_fallback']:.1%} | "
                f"{agg['mean_stale']:.1%} | {agg['mean_high_lag']:.1%} | "
                f"{agg['median_quote_age_ms']:.1f} | {agg['mean_bucket_count']:.0f} | "
                f"{agg['mean_confidence']:.1%} |"
            )

        lines.extend([
            "",
            "## Bucket Fill Time Distribution",
            "",
            "| Symbol | Tier | Fill P10 (ms) | Fill P50 (ms) | Fill P90 (ms) | "
            "Non-Regular % | Odd-Lot Days |",
            "|--------|------|---------------|---------------|---------------|"
            "---------------|--------------|",
        ])
        for sym in self._symbols:
            agg = sym_agg.get(sym)
            if not agg or agg.get("valid_days", 0) == 0:
                continue
            lines.append(
                f"| {sym} | {agg['tier']} | {agg['fill_p10']:.0f} | "
                f"{agg['fill_p50']:.0f} | {agg['fill_p90']:.0f} | "
                f"{agg['non_regular_pct']:.1%} | {agg['odd_lot_days']} |"
            )

        lines.extend([
            "",
            "## Performance",
            "",
            "| Symbol | Tier | Total Buckets | Classify (min) | Bucket (min) |",
            "|--------|------|---------------|----------------|--------------|",
        ])
        for sym in self._symbols:
            agg = sym_agg.get(sym)
            if not agg or agg.get("valid_days", 0) == 0:
                continue
            lines.append(
                f"| {sym} | {agg['tier']} | {agg['total_buckets']:,} | "
                f"{agg['classify_total_s'] / 60:.1f} | "
                f"{agg['bucket_total_s'] / 60:.1f} |"
            )

        # Tier comparison
        lines.extend(["", "## Cross-Tier Quality Comparison", ""])
        for tier in ["A", "B", "C"]:
            tier_syms = [s for s in self._symbols if self._tier_map.get(s) == tier]
            tier_aggs = [sym_agg[s] for s in tier_syms if s in sym_agg and sym_agg[s].get("valid_days", 0) > 0]
            if tier_aggs:
                avg_match = np.mean([a["mean_quote_match"] for a in tier_aggs])
                avg_stale = np.mean([a["mean_stale"] for a in tier_aggs])
                avg_conf = np.mean([a["mean_confidence"] for a in tier_aggs])
                lines.append(
                    f"- **Tier {tier}** ({len(tier_aggs)} symbols): "
                    f"Quote match={avg_match:.1%}, Stale={avg_stale:.1%}, "
                    f"Confidence={avg_conf:.1%}"
                )

        # Issues
        lines.extend(["", "---", "", "## Quality Issues", ""])
        if issues:
            for issue in issues:
                lines.append(f"- **WARNING**: {issue}")
        else:
            lines.append("**No structural quality issues detected.**")

        lines.extend([
            "",
            "---",
            "",
            f"**Gate**: Week 2 data quality report generated. "
            f"{'Proceed to Week 3.' if not issues else 'Review issues before proceeding.'}",
            "",
        ])

        report_path.write_text("\n".join(lines) + "\n")
        logger.info("Quality report written to %s", report_path)

        if issues:
            for issue in issues:
                logger.warning("QUALITY ISSUE: %s", issue)

        return len(issues) == 0


# ── Main entry point ──────────────────────────────────────────────────

async def run_week2(skip_existing: bool = True) -> bool:
    pipeline = Week2Pipeline()
    return await pipeline.run(skip_existing=skip_existing)


if __name__ == "__main__":
    import argparse

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Week 2: Classification + Bucketing")
    parser.add_argument(
        "--no-skip", action="store_true",
        help="Re-process symbol-days even if buckets already exist",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    )

    result = asyncio.run(run_week2(skip_existing=not args.no_skip))
    exit(0 if result else 1)
