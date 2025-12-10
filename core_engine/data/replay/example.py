#!/usr/bin/env python3
"""
Simple TSLA Data Replay Example
===============================

Simple example that demonstrates replaying TSLA historical data and outputting the data stream.

Author: StatArb_Gemini Core Engine
"""

import asyncio
import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from core_engine.data.replay.adapter import HistoricalReplayFeedAdapter, ReplayFeedConfig
from core_engine.data.replay.engine import ReplaySpeed
from core_engine.data.feeds.adapters import FeedMessage, FeedProvider

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_market_data(message: FeedMessage) -> None:
    """
    Handle incoming market data - just print it out
    """
    data = message.data
    # Format timestamp properly
    timestamp_str = message.timestamp.strftime('%Y-%m-%d %H:%M:%S%z') if message.timestamp else 'N/A'
    print(f"{message.symbol} | {timestamp_str} | "
          f"O:{data.get('open', 'N/A'):>8} H:{data.get('high', 'N/A'):>8} "
          f"L:{data.get('low', 'N/A'):>8} C:{data.get('close', 'N/A'):>8} "
          f"V:{data.get('volume', 'N/A'):>8}")


async def main():
    """
    Simple main function that replays TSLA data and outputs the stream
    """
    logger.info("🚀 Starting Simple TSLA Data Replay")

    # Simple configuration for TSLA
    symbols = ["TSLA"]
    start_date = "2024-12-20"
    end_date = "2024-12-20"
    speed = ReplaySpeed.FAST_10X  # Fast replay for demo

    logger.info(f"Replaying TSLA data from {start_date} to {end_date} at {speed.name} speed")

    # Create replay feed adapter
    config = ReplayFeedConfig(
        provider=FeedProvider.SIMULATED,
        replay_symbols=symbols,
        replay_start_date=start_date,
        replay_end_date=end_date,
        replay_speed=speed
    )

    adapter = HistoricalReplayFeedAdapter(config)

    try:
        # Connect to replay feed
        logger.info("🔌 Connecting to replay feed...")
        connected = await adapter.connect()
        if not connected:
            logger.error("❌ Failed to connect to replay feed")
            return

        # Subscribe to market data
        logger.info("📡 Subscribing to TSLA...")
        subscribed = await adapter.subscribe(symbols, ['bar'])
        if not subscribed:
            logger.error("❌ Failed to subscribe to TSLA")
            return

        # Add message handler
        adapter.add_message_handler(on_market_data)

        # Start replay
        logger.info("▶️ Starting replay...")
        started = await adapter.start_replay()
        if not started:
            logger.error("❌ Failed to start replay")
            return

        # Wait for completion
        logger.info("⏳ Waiting for replay completion...")
        while True:
            await asyncio.sleep(1)

            stats = adapter.get_replay_statistics()
            progress = stats.get('progress_percentage', 0)

            if progress >= 100.0:
                logger.info("✅ Replay completed!")
                break

    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")

    finally:
        # Cleanup
        logger.info("🧹 Cleaning up...")
        await adapter.stop_replay()
        await adapter.disconnect()

    logger.info("🏁 Simple TSLA replay example completed")


if __name__ == "__main__":
    asyncio.run(main())