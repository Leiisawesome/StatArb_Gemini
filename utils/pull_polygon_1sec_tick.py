#!/usr/bin/env python3
"""
Pull 1-Second Tick (Trade + Quote) Data from Polygon REST API
=============================================================

Fetches historical 1-second trade and quote snapshots for a symbol
via polygon_rest.py and saves to CSV. RTH (Regular Trading Hours) only:
09:30–16:00 Eastern.

Prerequisites:
    - POLYGON_API_KEY environment variable
    - massive package: pip install massive

Usage:
    python utils/pull_polygon_1sec_tick.py
    python utils/pull_polygon_1sec_tick.py --symbol TSLA --date 2024-12-20
    python utils/pull_polygon_1sec_tick.py --symbol TSLA --date 2024-12-20 --output data/tsla_1sec.csv

Author: StatArb_Gemini
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# Add project root for imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from core_engine.data.feeds.polygon_rest import create_polygon_rest_service


ET = ZoneInfo("America/New_York")
UTC = timezone.utc


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pull 1-second trade+quote tick data from Polygon REST and save to CSV",
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
        help="Output CSV path (default: utils/output/<symbol>_1sec_<date>.csv)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=100,
        help="Max pagination pages for trades/quotes (default: 100)",
    )
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("ERROR: POLYGON_API_KEY environment variable not set.", file=sys.stderr)
        return 1

    # Parse date
    try:
        year, month, day = map(int, args.date.split("-"))
        base_date = datetime(year, month, day, tzinfo=ET)
    except ValueError:
        print(f"ERROR: Invalid date format '{args.date}'. Use YYYY-MM-DD.", file=sys.stderr)
        return 1

    # RTH only: 09:30–16:00 ET; Polygon API expects UTC
    start_et = base_date.replace(hour=9, minute=30, second=0)
    end_et = base_date.replace(hour=16, minute=0, second=0)
    start = start_et.astimezone(UTC)
    end = end_et.astimezone(UTC)

    # Output path
    if args.output:
        out_path = Path(args.output)
    else:
        out_dir = _SCRIPT_DIR / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{args.symbol}_1sec_{args.date}.csv"

    print(f"Fetching RTH (09:30–16:00 ET) 1-sec trade+quote snapshots: {args.symbol} on {args.date}")
    print(f"  Range: {start} to {end} UTC")
    print(f"  Output: {out_path}")

    try:
        service = await create_polygon_rest_service(api_key=api_key)

        df = await service.get_trade_quote_snapshots_1s(
            symbol=args.symbol,
            start=start,
            end=end,
            forward_fill_quotes=True,
            forward_fill_trades=False,
            max_pages=args.max_pages,
        )

        await service.close()

        if df.empty:
            print("WARNING: No data returned.", file=sys.stderr)
            return 0

        # Convert timestamps to U.S. Eastern before saving
        if df.index.tz is not None:
            df = df.copy()
            df.index = df.index.tz_convert(ET)
        df.to_csv(out_path)
        print(f"Saved {len(df)} rows to {out_path}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
