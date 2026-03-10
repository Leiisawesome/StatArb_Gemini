#!/usr/bin/env python3
"""
Pull Market Data from Local ClickHouse to CSV
=============================================

Uses core_engine.data ClickHouseDataManager to pull OHLCV data from the local
ClickHouse database (polygon_data.ticks) for a given symbol and date, RTH only
(09:30–16:00 Eastern), and save to CSV.

Prerequisites:
    - ClickHouse running locally (default localhost:8123)
    - polygon_data.ticks table populated with data

Usage:
    python utils/pull_clickhouse_to_csv.py
    python utils/pull_clickhouse_to_csv.py --symbol TSLA --date 2024-12-20 --output data/tsla_1min.csv

Author: StatArb_Gemini Utils
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add project root for imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from core_engine.data.manager import ClickHouseDataConfig, ClickHouseDataManager

ET = ZoneInfo("America/New_York")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pull OHLCV data from local ClickHouse (polygon_data.ticks) for RTH and save to CSV",
    )
    parser.add_argument(
        "--symbol",
        default="TSLA",
        help="Symbol to fetch (default: TSLA)",
    )
    parser.add_argument(
        "--date",
        default="2024-12-20",
        help="Date YYYY-MM-DD (default: 2024-12-20)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output CSV path (default: utils/output/<symbol>_1min_<date>.csv)",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="ClickHouse host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8123,
        help="ClickHouse port (default: 8123)",
    )
    parser.add_argument(
        "--database",
        default="polygon_data",
        help="ClickHouse database (default: polygon_data)",
    )
    parser.add_argument(
        "--interval",
        default="1min",
        choices=["1min", "5min", "15min", "1h"],
        help="Bar interval (default: 1min)",
    )
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()

    # Parse date and build RTH range (09:30–16:00 ET)
    try:
        year, month, day = map(int, args.date.split("-"))
        base_date = datetime(year, month, day, tzinfo=ET)
    except ValueError:
        print(f"ERROR: Invalid date format '{args.date}'. Use YYYY-MM-DD.", file=sys.stderr)
        return 1

    start_et = base_date.replace(hour=9, minute=30, second=0, microsecond=0)
    end_et = base_date.replace(hour=16, minute=0, second=0, microsecond=0)
    # Manager expects naive datetimes in ET for timestamp conversion
    start_naive = start_et.replace(tzinfo=None)
    end_naive = end_et.replace(tzinfo=None)

    # Output path
    if args.output:
        out_path = Path(args.output)
    else:
        out_dir = _SCRIPT_DIR / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{args.symbol}_1min_{args.date}.csv"

    print(f"Pulling RTH (09:30–16:00 ET) {args.interval} bars: {args.symbol} on {args.date}")
    print(f"  Database: {args.database}.ticks")
    print(f"  Output: {out_path}")

    # Configure and initialize ClickHouseDataManager
    config = ClickHouseDataConfig(
        symbols=[args.symbol],
        start_date=args.date,
        end_date=args.date,
        interval=args.interval,
        clickhouse_host=args.host,
        clickhouse_port=args.port,
        clickhouse_database=args.database,
    )
    manager = ClickHouseDataManager(config)

    try:
        if not await manager.initialize():
            print("ERROR: Failed to initialize ClickHouseDataManager.", file=sys.stderr)
            return 1

        df = await manager.load_market_data(
            symbols=[args.symbol],
            start_time=start_naive,
            end_time=end_naive,
            interval=args.interval,
        )
        await manager.stop()

        if df.empty:
            print("WARNING: No data returned from ClickHouse.", file=sys.stderr)
            return 0

        # Filter to requested symbol (manager may return multi-symbol)
        df = df[df["symbol"] == args.symbol].copy()

        df.to_csv(out_path, index=False)
        print(f"Saved {len(df)} rows to {out_path}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
