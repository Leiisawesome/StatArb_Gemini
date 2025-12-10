"""
Replay Engine Integration Test
==============================

Integration test for the HistoricalDataReplayEngine that demonstrates
calling the replay engine to output replayed data streams.

This test validates:
1. Replay engine initialization and configuration
2. Data streaming from ClickHouse via replay adapter
3. Message handling and data output
4. Proper cleanup and resource management

Author: StatArb_Gemini Integration Test Suite
Date: December 10, 2025
"""

import asyncio
import logging
import sys
from typing import List, Dict, Any
from datetime import datetime
import pytest

# Add project root to path
sys.path.insert(0, '/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

from core_engine.data.replay.adapter import HistoricalReplayFeedAdapter, ReplayFeedConfig
from core_engine.data.replay.engine import ReplaySpeed
from core_engine.data.feeds.adapters import FeedMessage, FeedProvider

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReplayDataCollector:
    """
    Test utility to collect and validate replayed data
    """

    def __init__(self):
        self.messages_received: List[FeedMessage] = []
        self.data_points: List[Dict[str, Any]] = []
        self.timestamps: List[datetime] = []
        self.symbols_seen: set = set()

    async def on_market_data(self, message: FeedMessage) -> None:
        """
        Handle incoming market data from replay engine
        """
        self.messages_received.append(message)

        # Extract data
        data = message.data
        self.data_points.append(data)
        self.timestamps.append(message.timestamp)
        self.symbols_seen.add(message.symbol)

        # Log first few messages for visibility
        if len(self.messages_received) <= 5:
            logger.info(f"📊 Received: {message.symbol} at {message.timestamp} - "
                       f"O: {data.get('open', 'N/A')} H: {data.get('high', 'N/A')} "
                       f"L: {data.get('low', 'N/A')} C: {data.get('close', 'N/A')} "
                       f"V: {data.get('volume', 'N/A')}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get collection statistics"""
        return {
            'messages_received': len(self.messages_received),
            'data_points': len(self.data_points),
            'unique_timestamps': len(set(self.timestamps)),
            'symbols_seen': list(self.symbols_seen),
            'time_range': {
                'start': min(self.timestamps) if self.timestamps else None,
                'end': max(self.timestamps) if self.timestamps else None
            }
        }


@pytest.mark.asyncio
async def test_replay_engine_basic_functionality():
    """
    Test basic replay engine functionality with data output

    This test demonstrates:
    1. Replay engine configuration and initialization
    2. Data streaming from historical data
    3. Message collection and validation
    4. Proper resource cleanup
    """
    logger.info("🚀 Starting Replay Engine Integration Test")

    # Test configuration
    symbols = ["TSLA"]
    start_date = "2024-12-20"
    end_date = "2024-12-20"
    replay_speed = ReplaySpeed.INSTANT  # Instant for fast testing

    # Create data collector
    collector = ReplayDataCollector()

    # Create replay feed adapter
    config = ReplayFeedConfig(
        provider=FeedProvider.SIMULATED,
        replay_symbols=symbols,
        replay_start_date=start_date,
        replay_end_date=end_date,
        replay_speed=replay_speed
    )

    adapter = HistoricalReplayFeedAdapter(config)

    try:
        # Connect to replay feed
        logger.info("🔌 Connecting to replay feed...")
        connected = await adapter.connect()
        assert connected, "Failed to connect to replay feed"

        # Subscribe to market data
        logger.info(f"📡 Subscribing to {len(symbols)} symbols...")
        subscribed = await adapter.subscribe(symbols, ['bar'])
        assert subscribed, "Failed to subscribe to symbols"

        # Add message handler
        adapter.add_message_handler(collector.on_market_data)

        # Start replay
        logger.info(f"▶️ Starting replay at {replay_speed.name} speed...")
        started = await adapter.start_replay()
        assert started, "Failed to start replay"

        # Wait for some messages to be collected (with timeout)
        logger.info("⏳ Waiting for message collection...")
        timeout = 10.0  # 10 second timeout for instant replay
        target_messages = 50  # Collect at least 50 messages

        try:
            # Monitor progress
            start_time = asyncio.get_event_loop().time()

            while len(collector.messages_received) < target_messages:
                await asyncio.sleep(0.5)  # Check every 0.5 seconds

                stats = adapter.get_replay_statistics()
                progress = stats.get('progress_percentage', 0)

                logger.info(f"📈 Progress: {progress:.1f}% | Messages: {len(collector.messages_received)}")

                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    logger.warning(f"⚠️ Timeout reached ({timeout}s), stopping replay")
                    break

        except KeyboardInterrupt:
            logger.info("🛑 Interrupted by user")

        # Validate results
        logger.info("🔍 Validating replay results...")

        stats = collector.get_statistics()
        logger.info(f"📊 Final Statistics:")
        logger.info(f"   Messages received: {stats['messages_received']}")
        logger.info(f"   Data points: {stats['data_points']}")
        logger.info(f"   Unique timestamps: {stats['unique_timestamps']}")
        logger.info(f"   Symbols seen: {stats['symbols_seen']}")
        if stats['time_range']['start'] and stats['time_range']['end']:
            logger.info(f"   Time range: {stats['time_range']['start']} → {stats['time_range']['end']}")

        # Assertions
        assert stats['messages_received'] > 0, "No messages received from replay"
        assert stats['data_points'] > 0, "No data points collected"
        assert len(stats['symbols_seen']) > 0, "No symbols detected"
        assert symbols[0] in stats['symbols_seen'], f"Expected symbol {symbols[0]} not found"

        # Validate data structure
        if collector.data_points:
            sample_data = collector.data_points[0]
            required_fields = ['open', 'high', 'low', 'close', 'volume']
            for field in required_fields:
                assert field in sample_data, f"Required field '{field}' missing from data"

        logger.info("✅ Replay engine integration test passed!")

    finally:
        # Cleanup
        logger.info("🧹 Cleaning up resources...")
        try:
            await adapter.stop_replay()
            await adapter.disconnect()
        except Exception as e:
            logger.warning(f"⚠️ Cleanup error: {e}")


@pytest.mark.asyncio
async def test_replay_engine_speed_configurations():
    """
    Test different replay speed configurations
    """
    logger.info("⚡ Testing replay speed configurations")

    symbols = ["TSLA"]
    speeds_to_test = [ReplaySpeed.FAST_2X, ReplaySpeed.FAST_10X, ReplaySpeed.FAST_50X]

    for speed in speeds_to_test:
        logger.info(f"Testing {speed.name} speed...")

        collector = ReplayDataCollector()

        config = ReplayFeedConfig(
            provider=FeedProvider.SIMULATED,
            replay_symbols=symbols,
            replay_start_date="2024-12-20",
            replay_end_date="2024-12-20",
            replay_speed=speed
        )

        adapter = HistoricalReplayFeedAdapter(config)

        try:
            # Quick connect and test
            await adapter.connect()
            await adapter.subscribe(symbols, ['bar'])
            adapter.add_message_handler(collector.on_market_data)

            # Start replay
            await adapter.start_replay()

            # Wait briefly to collect some data
            await asyncio.sleep(5)

            # Stop replay
            await adapter.stop_replay()

            stats = collector.get_statistics()
            logger.info(f"   {speed.name}: {stats['messages_received']} messages collected")

            # Validate we got some data
            assert stats['messages_received'] > 0, f"No data collected for {speed.name}"

        finally:
            await adapter.disconnect()


if __name__ == "__main__":
    # Run the tests
    logger.info("🧪 Running Replay Engine Integration Tests")

    async def run_tests():
        try:
            await test_replay_engine_basic_functionality()
            await test_replay_engine_speed_configurations()
            logger.info("🎉 All replay engine tests passed!")
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            raise

    asyncio.run(run_tests())