"""
Week 1 Runner: Universe Freeze + Bulk Ingestion.

Sequence (from blueprint v1.6-FINAL):
  1. Scan ~35 candidates against liquidity guardrails
  2. Classify into tiers A/B/C (3A / 3B / 4C = 10 total)
  3. Freeze universe YAML
  4. Bulk download trades + quotes for 10 symbols × 130 trading days
  5. Monitor storage and progress

This script orchestrates the full Week 1 pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from core_engine.data.feeds.polygon_rest import PolygonRestConfig, PolygonRestService
from core_engine.microstructure.constants import (
    CONSTANTS_VERSION,
    DATASET_TARGET_SYMBOLS,
    DATASET_TRADING_DAYS,
    DATASET_STORAGE_TARGET_GB,
    DATASET_STORAGE_KILL_GB,
)
from core_engine.microstructure.ingestion.bulk_downloader import BulkDownloader
from core_engine.microstructure.ingestion.universe_scanner import UniverseScanner
from core_engine.microstructure.schema.ddl_manager import DDLManager
from core_engine.microstructure.types import Tier

logger = logging.getLogger(__name__)

# Candidate pool: ~35 symbols spanning multiple sectors and market caps.
# Intentionally broad to allow the guardrails to select the best 10.
CANDIDATE_SYMBOLS = [
    # Mega-cap tech (likely Tier A)
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOG", "META", "TSLA",
    # Large-cap tech/growth (likely Tier B)
    "AMD", "UBER", "SHOP", "PLTR", "CRWD", "NET", "SNOW",
    # Mid-cap / higher-spread (likely Tier C)
    "ROKU", "SNAP", "PINS", "HOOD", "SOFI", "LYFT", "DASH",
    "RBLX", "COIN", "U",
    # Financials (sector diversity)
    "JPM", "GS",
    # Healthcare (sector diversity)
    "PFE", "UNH",
    # Consumer (sector diversity)
    "WMT", "COST", "DIS", "ABNB",
    # Energy (sector diversity)
    "XOM", "CVX",
]


async def run_universe_scan(
    polygon: PolygonRestService,
    observation_end: Optional[date] = None,
) -> dict:
    """Step 1: Scan candidates and freeze universe."""
    scanner = UniverseScanner(polygon_service=polygon)

    obs_end = observation_end or (date.today() - timedelta(days=7))
    obs_start = obs_end - timedelta(days=30)  # ~20 trading days

    logger.info("=" * 60)
    logger.info("STEP 1: Universe scan — %d candidates", len(CANDIDATE_SYMBOLS))
    logger.info("Observation window: %s to %s", obs_start, obs_end)
    logger.info("=" * 60)

    classification = await scanner.scan_candidates(
        CANDIDATE_SYMBOLS, obs_start, obs_end
    )

    if len(classification.tier_assignments) < DATASET_TARGET_SYMBOLS:
        logger.warning(
            "Only %d symbols classified (target: %d). May need more candidates.",
            len(classification.tier_assignments), DATASET_TARGET_SYMBOLS,
        )

    # Freeze to YAML
    frozen_path = scanner.freeze_to_yaml(classification)
    logger.info("Universe frozen to %s", frozen_path)

    return {
        "classification": classification,
        "symbols": list(classification.tier_assignments.keys()),
        "frozen_path": str(frozen_path),
    }


async def run_bulk_download(
    polygon: PolygonRestService,
    symbols: List[str],
    clickhouse_url: str = "http://localhost:8123",
) -> dict:
    """Step 2: Download trades + quotes for all symbols × 130 days."""
    downloader = BulkDownloader(
        polygon_service=polygon,
        clickhouse_url=clickhouse_url,
        batch_insert_size=100_000,
        max_concurrent_symbols=3,
        max_pages_per_request=200,
    )

    # Compute 130 trading days
    end_date = date.today() - timedelta(days=7)
    start_date = end_date - timedelta(days=200)  # ~130 trading days in 200 cal days
    trading_dates = BulkDownloader.get_trading_dates(start_date, end_date)

    # Trim to exactly DATASET_TRADING_DAYS
    if len(trading_dates) > DATASET_TRADING_DAYS:
        trading_dates = trading_dates[-DATASET_TRADING_DAYS:]

    logger.info("=" * 60)
    logger.info("STEP 2: Bulk download")
    logger.info("Symbols: %s", symbols)
    logger.info("Trading days: %d (%s to %s)", len(trading_dates),
                trading_dates[0], trading_dates[-1])
    logger.info("Storage target: %d GB, kill-switch: %d GB",
                DATASET_STORAGE_TARGET_GB, DATASET_STORAGE_KILL_GB)
    logger.info("=" * 60)

    report = await downloader.download_all(
        symbols=symbols,
        trading_dates=trading_dates,
    )

    return {
        "report": report,
        "trading_dates": trading_dates,
    }


async def run_week1(
    scan_only: bool = False,
    download_only: bool = False,
    symbols_override: Optional[List[str]] = None,
    clickhouse_url: str = "http://localhost:8123",
) -> None:
    """Execute full Week 1 pipeline."""
    t0 = time.monotonic()

    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║  WEEK 1: Universe Freeze + Bulk Ingestion               ║")
    logger.info("║  Constants: %s                                  ║", CONSTANTS_VERSION)
    logger.info("╚" + "═" * 58 + "╝")

    # Ensure DDL is applied
    ddl = DDLManager(clickhouse_url)
    await ddl.apply_ddl()

    # Initialize Polygon
    polygon_config = PolygonRestConfig()
    polygon = PolygonRestService(config=polygon_config)
    await polygon.initialize()

    try:
        symbols = symbols_override

        if not download_only:
            scan_result = await run_universe_scan(polygon)
            symbols = scan_result["symbols"]

        if scan_only:
            logger.info("Scan-only mode. Universe frozen. Exiting.")
            return

        if not symbols:
            logger.error("No symbols to download. Aborting.")
            return

        dl_result = await run_bulk_download(
            polygon, symbols, clickhouse_url
        )
        report = dl_result["report"]

        elapsed_min = (time.monotonic() - t0) / 60
        logger.info("=" * 60)
        logger.info("WEEK 1 COMPLETE in %.1f minutes", elapsed_min)
        logger.info(
            "Downloaded: %d trades, %d quotes, %d symbol-days OK, %d failed",
            report.total_trades, report.total_quotes,
            report.symbol_days_completed, report.symbol_days_failed,
        )
        logger.info("Estimated storage: %.1f GB", report.estimated_storage_gb)
        if report.failures:
            logger.warning("Failures:")
            for sym, dt, err in report.failures[:10]:
                logger.warning("  %s %s: %s", sym, dt, err[:100])
        logger.info("=" * 60)

    finally:
        await polygon.close()


if __name__ == "__main__":
    import argparse

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Week 1: Universe + Bulk Download")
    parser.add_argument("--scan-only", action="store_true",
                        help="Only scan and freeze universe, don't download")
    parser.add_argument("--download-only", action="store_true",
                        help="Skip scan, use existing frozen universe")
    parser.add_argument("--symbols", nargs="+",
                        help="Override symbols (skip scan)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    )

    asyncio.run(run_week1(
        scan_only=args.scan_only,
        download_only=args.download_only,
        symbols_override=args.symbols,
    ))
