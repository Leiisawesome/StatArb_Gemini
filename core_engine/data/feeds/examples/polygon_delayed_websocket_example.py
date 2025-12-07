#!/usr/bin/env python3
"""
Polygon.io Delayed WebSocket Feed Example
==========================================

Demonstrates how to use the Polygon.io delayed WebSocket feed
with the Stock Starter subscription plan.

The delayed feed provides 15-minute delayed data including:
- Second aggregates (A.*)
- Minute aggregates (AM.*)
- Trades (T.*)

Prerequisites:
    1. Polygon.io Stock Starter subscription
    2. API key set as environment variable: POLYGON_API_KEY
    3. Install websockets: pip install websockets

Usage:
    export POLYGON_API_KEY="your_api_key_here"
    python polygon_delayed_websocket_example.py

Author: StatArb_Gemini Core Engine
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..')))

from core_engine.data.feeds.polygon_realtime import (
    PolygonRealtimeFeedAdapter,
    PolygonFeedConfig,
    PolygonSubscriptionTier,
    PolygonCluster,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('polygon_delayed_example')


# ============================================================================
# DELAYED WEBSOCKET EXAMPLE
# ============================================================================

async def delayed_websocket_example():
    """
    Example using the 15-minute delayed WebSocket feed
    """
    logger.info("=" * 60)
    logger.info("POLYGON.IO DELAYED WEBSOCKET FEED EXAMPLE")
    logger.info("=" * 60)

    # Get API key
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY environment variable not set!")
        logger.info("Set it with: export POLYGON_API_KEY='your_api_key_here'")
        return

    # Define symbols to track
    symbols = ["TSLA", "AAPL", "NVDA"]

    logger.info(f"Testing delayed WebSocket feed for symbols: {symbols}")
    logger.info("This should provide 15-minute delayed data...")

    try:
        # Create config for DELAYED cluster
        config = PolygonFeedConfig(
            api_key=api_key,
            symbols=symbols,
            subscription_tier=PolygonSubscriptionTier.STARTER,
            cluster=PolygonCluster.STOCKS_DELAYED,  # Use delayed endpoint
            data_types=["second_agg", "minute_agg", "trade"],  # Available in Starter
            name="polygon-delayed-test",
        )

        logger.info(f"WebSocket URL: {config.ws_url}")
        logger.info(f"Subscription tier: {config.subscription_tier.value}")
        logger.info(f"Data types: {config.data_types}")

        # Create adapter
        adapter = PolygonRealtimeFeedAdapter(config)
        logger.info("✅ Adapter created")

        # Set up event handlers
        message_count = {"bars": 0, "trades": 0, "total": 0}

        def on_bar_received(bar_data):
            message_count["bars"] += 1
            message_count["total"] += 1
            symbol = bar_data.get("symbol", "UNKNOWN")
            price = bar_data.get("close", 0)
            volume = bar_data.get("volume", 0)
            timestamp = bar_data.get("timestamp", datetime.now())

            logger.info(f"📊 BAR [{symbol}] ${price:.2f} Vol:{volume} @ {timestamp}")

            # Stop after receiving some data
            if message_count["total"] >= 10:
                logger.info("Received 10 messages, stopping...")
                asyncio.create_task(adapter.disconnect())

        def on_trade_received(trade_data):
            message_count["trades"] += 1
            message_count["total"] += 1
            symbol = trade_data.get("symbol", "UNKNOWN")
            price = trade_data.get("price", 0)
            size = trade_data.get("size", 0)
            timestamp = trade_data.get("timestamp", datetime.now())

            logger.info(f"💰 TRADE [{symbol}] ${price:.2f} Size:{size} @ {timestamp}")

            # Stop after receiving some data
            if message_count["total"] >= 10:
                logger.info("Received 10 messages, stopping...")
                asyncio.create_task(adapter.disconnect())

        def on_status_changed(status):
            logger.info(f"🔄 Status changed: {status}")

        def on_error(error_msg):
            logger.error(f"❌ Error: {error_msg}")

        # Connect to event handlers
        adapter.on_bar = on_bar_received
        adapter.on_trade = on_trade_received
        adapter.on_status_change = on_status_changed
        adapter.on_error = on_error

        # Connect and subscribe
        logger.info("Connecting to delayed WebSocket feed...")
        await adapter.connect()

        logger.info("Subscribing to data streams...")
        await adapter.subscribe(symbols, ["second_agg", "minute_agg", "trade"])

        logger.info("✅ Connected and subscribed! Waiting for delayed data...")
        logger.info("Note: Data will be 15 minutes delayed from real-time")

        # Wait for data or timeout
        logger.info("Waiting for delayed data (30 seconds)...")
        await asyncio.sleep(30.0)  # Wait 30 seconds for data
        
        logger.info("Timeout reached, disconnecting...")
        await adapter.disconnect()

        # Summary
        logger.info("\n📈 Session Summary:")
        logger.info(f"  Bars received: {message_count['bars']}")
        logger.info(f"  Trades received: {message_count['trades']}")
        logger.info(f"  Total messages: {message_count['total']}")

        if message_count["total"] == 0:
            logger.warning("⚠️ No data received. This could mean:")
            logger.warning("  - Market is closed")
            logger.warning("  - No trading activity in the symbols")
            logger.warning("  - Network connectivity issues")
            logger.warning("  - API key permissions")
        else:
            logger.info("✅ Successfully received delayed market data!")

    except Exception as e:
        logger.error(f"Delayed WebSocket example failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """
    Run the delayed WebSocket example
    """
    logger.info("🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷")
    logger.info("POLYGON.IO DELAYED WEBSOCKET FEED TEST")
    logger.info("🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷")
    logger.info("")

    try:
        await delayed_websocket_example()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())