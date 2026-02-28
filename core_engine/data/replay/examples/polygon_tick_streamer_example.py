#!/usr/bin/env python3
"""
Polygon Historical Tick Streamer Example
=======================================

Simple, fully-functional wiring example for the backtest-only
PolygonHistoricalTickStreamer.

What it does:
    1) Pulls historical 1-second trade/quote snapshots for a symbol
    2) Replays them as FeedMessage events (trade, quote, bar)
    3) Prints compact stream output and final message counts

Prerequisites:
    - POLYGON_API_KEY environment variable
    - massive client dependency installed

Usage:
    python core_engine/data/replay/examples/polygon_tick_streamer_example.py

    python core_engine/data/replay/examples/polygon_tick_streamer_example.py \
      --symbol AAPL \
      --start 2025-01-02T14:30:00+00:00 \
      --end 2025-01-02T14:35:00+00:00 \
      --speed 20
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from collections import Counter
from datetime import datetime, timezone

from dotenv import load_dotenv

# Add project root to path for direct script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from core_engine.data.feeds.adapters import FeedMessage
from core_engine.data.replay.polygon_tick_streamer import (
    PolygonTickStreamerConfig,
    create_polygon_tick_streamer,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-35s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("polygon_tick_streamer_example")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Polygon historical tick streamer example")
    parser.add_argument("--symbol", default="AAPL", help="Symbol to stream")
    parser.add_argument(
        "--start",
        default="2025-01-02T14:30:00+00:00",
        help="UTC ISO timestamp start (inclusive)",
    )
    parser.add_argument(
        "--end",
        default="2025-01-02T14:32:00+00:00",
        help="UTC ISO timestamp end (exclusive)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=float("inf"),
        help="Playback speed: 1=realtime, 10=10x, inf=instant",
    )
    parser.add_argument(
        "--max-print",
        type=int,
        default=40,
        help="Maximum number of emitted messages to print",
    )
    parser.add_argument(
        "--strict-live-parity",
        action="store_true",
        default=True,
        help="Emit only websocket-live payload fields (default: enabled)",
    )
    parser.add_argument(
        "--allow-enriched-replay",
        action="store_true",
        help="Include additional replay-only convenience fields",
    )
    parser.add_argument(
        "--full-fidelity",
        action="store_true",
        help="Request and propagate richer historical microstructure fields",
    )
    return parser.parse_args()


def _parse_iso_utc(raw: str) -> datetime:
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_message_line(message: FeedMessage) -> str:
    ts = message.timestamp.isoformat()
    symbol = message.symbol or "?"
    message_type = message.message_type
    data = message.data

    if message_type == "trade":
        return (
            f"[{ts}] {symbol:<6} trade  "
            f"price={data.get('price')} size={data.get('size')}"
        )
    if message_type == "quote":
        return (
            f"[{ts}] {symbol:<6} quote  "
            f"bid={data.get('bid')} ask={data.get('ask')} spread={data.get('spread')}"
        )
    if message_type == "bar":
        return (
            f"[{ts}] {symbol:<6} bar    "
            f"close={data.get('close')} vol={data.get('volume')}"
        )
    if message_type == "second_agg":
        return (
            f"[{ts}] {symbol:<6} second_agg "
            f"close={data.get('close')} vol={data.get('volume')} trades={data.get('num_trades')}"
        )
    if message_type == "minute_agg":
        return (
            f"[{ts}] {symbol:<6} minute_agg "
            f"close={data.get('close')} vol={data.get('volume')} trades={data.get('num_trades')}"
        )
    return f"[{ts}] {symbol:<6} {message_type:<6} {data}"


async def run_example() -> None:
    args = _parse_args()
    api_key = os.getenv("POLYGON_API_KEY", "")
    if not api_key:
        raise RuntimeError("POLYGON_API_KEY is not set")

    start = _parse_iso_utc(args.start)
    end = _parse_iso_utc(args.end)

    config = PolygonTickStreamerConfig(
        symbols=[args.symbol.upper()],
        start_time=start,
        end_time=end,
        api_key=api_key,
        playback_speed=args.speed,
        emit_trade=True,
        emit_quote=True,
        emit_second_agg=True,
        emit_minute_agg=False,
        strict_live_parity=not args.allow_enriched_replay,
        full_fidelity=args.full_fidelity,
    )

    counters = Counter()
    printed = 0

    async def on_message(message: FeedMessage) -> None:
        nonlocal printed
        counters[message.message_type] += 1
        if printed < args.max_print:
            logger.info(_format_message_line(message))
            printed += 1

    logger.info("Starting historical tick stream")
    logger.info(
        "symbol=%s start=%s end=%s speed=%s strict_live_parity=%s full_fidelity=%s",
        config.symbols[0],
        start.isoformat(),
        end.isoformat(),
        args.speed,
        config.strict_live_parity,
        config.full_fidelity,
    )

    streamer = await create_polygon_tick_streamer(config)
    streamer.add_message_handler(on_message)

    try:
        subscribed = await streamer.subscribe(config.symbols, ["trade", "quote", "second_agg"])
        if not subscribed:
            raise RuntimeError("subscribe() returned False")

        completed = await streamer.wait_until_complete(timeout=120.0)
        if not completed:
            raise TimeoutError("Timed out waiting for stream completion")

        logger.info("Stream completed")
        logger.info(
            "Counts: trade=%d quote=%d second_agg=%d minute_agg=%d total=%d",
            counters.get("trade", 0),
            counters.get("quote", 0),
            counters.get("second_agg", 0),
            counters.get("minute_agg", 0),
            sum(counters.values()),
        )
    finally:
        await streamer.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run_example())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as exc:
        logger.error("Example failed: %s", exc)
        raise
