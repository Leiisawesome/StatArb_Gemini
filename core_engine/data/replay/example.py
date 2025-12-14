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

from core_engine.data.replay.adapter import HistoricalReplayFeedAdapter
from core_engine.data.replay.config import ReplayConfig, ReplaySpeed
from core_engine.data.feeds.adapters import FeedMessage

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def on_market_data(message: FeedMessage) -> None:
    """
    Handle incoming market data - format and print OHLCV data

    Args:
        message: FeedMessage containing market data
    """
    try:
        data = message.data
        # Format timestamp properly
        timestamp_str = message.timestamp.strftime('%Y-%m-%d %H:%M:%S%z') if message.timestamp else 'N/A'
        print(f"{message.symbol} | {timestamp_str} | "
              f"O:{data.get('open', 'N/A'):>8} H:{data.get('high', 'N/A'):>8} "
              f"L:{data.get('low', 'N/A'):>8} C:{data.get('close', 'N/A'):>8} "
              f"V:{data.get('volume', 'N/A'):>8}")
    except Exception as e:
        logger.error(f"Error handling market data: {e}")

async def main():
    """
    Simple main function that replays TSLA data and outputs the stream
    """
    logger.info("🚀 Starting Simple TSLA Data Replay")

    # Simple configuration using centralized ReplayConfig
    config = ReplayConfig.create_for_symbol(
        symbol="TSLA",
        start_date="2024-12-20",
        end_date="2024-12-20",
        speed=ReplaySpeed.FAST_100X
    )

    logger.info(f"Replaying {', '.join(config.symbols)} data from {config.start_date} to {config.end_date} at {config.speed.name} speed")

    # Create replay feed adapter with unified config
    adapter = HistoricalReplayFeedAdapter(config)

    try:
        # Connect to replay feed
        logger.info("🔌 Connecting to replay feed...")
        connected = await adapter.connect()
        if not connected:
            logger.error("❌ Failed to connect to replay feed")
            return

        # Subscribe to market data
        logger.info(f"📡 Subscribing to {', '.join(config.symbols)}...")
        subscribed = await adapter.subscribe(config.symbols, ['bar'])
        if not subscribed:
            logger.error(f"❌ Failed to subscribe to {', '.join(config.symbols)}")
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