#!/usr/bin/env python3
"""
Polygon/Massive Delayed Feed Example (Unified Cluster Routing)
===============================================================

Demonstrates delayed market data streaming via the unified realtime adapter
using PolygonCluster.STOCKS_DELAYED.

Delayed feed provides 15-minute delayed data including:
- Second aggregates (A.*)
- Minute aggregates (AM.*)
- Trades (T.*)

Prerequisites:
    1. Polygon Stock Starter (or higher) subscription
    2. API key set as environment variable: POLYGON_API_KEY

Usage:
    export POLYGON_API_KEY="your_api_key_here"
    python polygon_delayed_websocket_example.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from core_engine.data import (
    PolygonCluster,
    PolygonFeedConfig,
    PolygonRealtimeFeedAdapter,
    PolygonSubscriptionTier,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('polygon_delayed_example')


def log_section(title: str) -> None:
    border = "=" * 76
    logger.info("\n%s", border)
    logger.info("%s", title)
    logger.info("%s", border)


def log_subsection(title: str) -> None:
    logger.info("\n%s", f"--- {title} ---")


def log_kv(items):
    if not items:
        return
    width = max(len(str(k)) for k, _ in items)
    lines = [f"  {str(k):<{width}} : {v}" for k, v in items]
    logger.info("\n%s", "\n".join(lines))


async def delayed_websocket_example():
    """Run delayed feed example through unified realtime adapter."""
    log_section("POLYGON/MASSIVE DELAYED FEED (UNIFIED ADAPTER)")

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY environment variable not set!")
        logger.info("Set it with: export POLYGON_API_KEY='your_api_key_here'")
        return

    symbols = ["TSLA", "AAPL", "NVDA"]
    message_count = {"second_agg": 0, "minute_agg": 0, "trade": 0, "total": 0}

    config = PolygonFeedConfig(
        api_key=api_key,
        symbols=symbols,
        cluster=PolygonCluster.STOCKS_DELAYED,
        subscription_tier=PolygonSubscriptionTier.STARTER,
        data_types=["second_agg", "minute_agg", "trade"],
    )

    adapter = PolygonRealtimeFeedAdapter(config)

    def on_message(message):
        message_count["total"] += 1
        msg_type = message.message_type
        if msg_type in message_count:
            message_count[msg_type] += 1

        if msg_type in ["second_agg", "minute_agg", "trade"]:
            event_time = message.timestamp.astimezone(timezone.utc)
            logger.info(
                "📩 %-10s | %-5s | %s",
                msg_type,
                message.symbol,
                event_time.isoformat(),
            )

    adapter.add_message_handler(on_message)

    try:
        log_subsection("Config")
        log_kv([
            ("symbols", symbols),
            ("cluster", config.cluster.value),
            ("data_types", config.data_types),
            ("subscription_tier", config.subscription_tier.value),
        ])

        if not await adapter.connect():
            logger.error("❌ Connection failed")
            return

        subscribed = await adapter.subscribe(symbols, config.data_types)
        if not subscribed:
            logger.error("❌ Subscription failed")
            await adapter.disconnect()
            return

        log_subsection("Streaming")
        logger.info("Listening for delayed events (45 seconds)...")
        await asyncio.sleep(45)

        stats = adapter.get_statistics()

        log_subsection("Session Summary")
        log_kv([
            ("second_agg", message_count["second_agg"]),
            ("minute_agg", message_count["minute_agg"]),
            ("trade", message_count["trade"]),
            ("total", message_count["total"]),
            ("messages_received", stats.get("messages_received")),
            ("messages_processed", stats.get("messages_processed")),
            ("errors", stats.get("errors")),
            ("active_subscriptions", stats.get("active_subscriptions")),
            ("last_message_time", stats.get("last_message_time")),
        ])

        if message_count["total"] == 0:
            logger.warning("⚠️ No delayed events received in the listen window.")
            logger.info("This can happen outside active market activity windows.")

    except Exception as e:
        logger.error(f"Delayed feed example failed: {e}")
    finally:
        await adapter.disconnect()


async def main():
    """Run delayed feed example."""
    try:
        await delayed_websocket_example()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")


if __name__ == "__main__":
    asyncio.run(main())
