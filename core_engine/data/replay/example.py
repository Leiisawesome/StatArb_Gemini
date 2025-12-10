#!/usr/bin/env python3
"""
Historical Data Replay Example
==============================

Demonstrates how to use the HistoricalDataReplayEngine to test live trading
components with historical data streams. Shows integration with signal
processing and event-driven architecture.

This example simulates a simple mean-reversion strategy that would normally
run on live market data, but uses historical data replay instead.

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from core_engine.data.replay.adapter import HistoricalReplayFeedAdapter, ReplayFeedConfig
from core_engine.data.replay.engine import ReplaySpeed
from core_engine.data.feeds.adapters import FeedMessage, FeedProvider
from core_engine.config import DataConfig
import yaml

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExampleSignalProcessor:
    """
    Example signal processor that demonstrates live trading component testing

    This simulates a mean-reversion strategy that generates signals based on
    price deviations from a moving average.
    """

    def __init__(self):
        self.prices: Dict[str, list] = {}
        self.signals_generated = 0
        self.messages_processed = 0

    async def on_market_data(self, message: FeedMessage) -> None:
        """
        Handle incoming market data messages

        This simulates what a real signal processor would do with live data.
        """
        self.messages_processed += 1

        symbol = message.symbol
        data = message.data

        # Extract price data
        close_price = data.get('close', 0)
        if close_price <= 0:
            return

        # Maintain price history (last 20 periods for moving average)
        if symbol not in self.prices:
            self.prices[symbol] = []

        self.prices[symbol].append(close_price)

        # Keep only last 20 prices
        if len(self.prices[symbol]) > 20:
            self.prices[symbol] = self.prices[symbol][-20:]

        # Generate signal if we have enough data
        if len(self.prices[symbol]) >= 20:
            signal = self._generate_signal(symbol, close_price)
            if signal:
                self.signals_generated += 1
                logger.info(f"📊 Signal generated for {symbol}: {signal}")

    def _generate_signal(self, symbol: str, current_price: float) -> Optional[str]:
        """
        Generate trading signal based on mean reversion logic

        Returns:
            Signal string or None
        """
        prices = self.prices[symbol]

        # Calculate simple moving average
        sma = sum(prices) / len(prices)

        # Calculate z-score (standardized deviation from mean)
        std_dev = (sum((p - sma) ** 2 for p in prices) / len(prices)) ** 0.5
        if std_dev == 0:
            return None

        z_score = (current_price - sma) / std_dev

        # Generate signals based on z-score thresholds
        if z_score < -2.0:  # Price significantly below mean
            return "BUY"    # Mean reversion: expect price to rise
        elif z_score > 2.0:  # Price significantly above mean
            return "SELL"   # Mean reversion: expect price to fall

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'messages_processed': self.messages_processed,
            'signals_generated': self.signals_generated,
            'symbols_tracked': len(self.prices),
            'signal_ratio': self.signals_generated / max(self.messages_processed, 1)
        }


async def main(config_file: Optional[str] = None):
    """
    Main example function demonstrating historical data replay for testing

    Args:
        config_file: Optional path to YAML config file
    """
    logger.info("🚀 Starting Historical Data Replay Example")

    # Load configuration
    if config_file:
        # Load from YAML config file
        logger.info(f"Loading configuration from {config_file}")
        with open(config_file, 'r') as f:
            yaml_config = yaml.safe_load(f)

        # Create DataConfig from YAML
        data_config = DataConfig()
        if 'data' in yaml_config:
            data_section = yaml_config['data']
            # Update DataConfig fields from YAML
            for key, value in data_section.items():
                if hasattr(data_config, key):
                    setattr(data_config, key, value)
                elif key == 'replay' and hasattr(data_config.replay, '__dict__'):
                    # Update replay sub-config
                    for replay_key, replay_value in value.items():
                        if hasattr(data_config.replay, replay_key):
                            setattr(data_config.replay, replay_key, replay_value)
    else:
        # Use default configuration
        data_config = DataConfig()
        data_config.mode = "replay"

    # Extract replay configuration
    symbols = data_config.symbols
    start_date = data_config.start_date or "2024-12-20"
    end_date = data_config.end_date or start_date
    replay_speed = ReplaySpeed[data_config.replay.speed]

    logger.info(f"Replay configuration: symbols={symbols}, dates={start_date} to {end_date}, speed={replay_speed.name}")

    # Create signal processor
    signal_processor = ExampleSignalProcessor()

    # Create replay feed adapter
    config = ReplayFeedConfig(
        provider=FeedProvider.SIMULATED,
        replay_symbols=symbols,
        replay_start_date=start_date,
        replay_end_date=end_date,
        replay_speed=replay_speed
    )

    adapter = HistoricalReplayFeedAdapter(config)

    # Connect to replay feed
    logger.info("Connecting to historical replay feed...")
    connected = await adapter.connect()
    if not connected:
        logger.error("Failed to connect to replay feed")
        return

    # Subscribe to market data
    logger.info(f"Subscribing to {len(symbols)} symbol...")
    subscribed = await adapter.subscribe(symbols, ['bar'])
    if not subscribed:
        logger.error("Failed to subscribe to symbols")
        return

    # Add message handler
    adapter.add_message_handler(signal_processor.on_market_data)

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    async def shutdown():
        """Graceful shutdown"""
        logger.info("Shutting down...")
        await adapter.stop_replay()
        await adapter.disconnect()

        # Print final statistics
        stats = signal_processor.get_statistics()
        replay_stats = adapter.get_replay_statistics()

        logger.info("📈 Final Statistics:")
        logger.info(f"  Messages processed: {stats['messages_processed']}")
        logger.info(f"  Signals generated: {stats['signals_generated']}")
        logger.info(f"  Signal ratio: {stats['signal_ratio']:.3%}")
        logger.info(f"  Symbols tracked: {stats['symbols_tracked']}")
        logger.info(f"  Replay progress: {replay_stats.get('progress_percentage', 0):.1f}%")
        logger.info(f"  Replay speed: {replay_stats.get('speed_multiplier', 1.0)}x")

        sys.exit(0)

    # Start replay
    logger.info(f"Starting replay at {replay_speed.name} speed...")
    started = await adapter.start_replay()
    if not started:
        logger.error("Failed to start replay")
        return

    # Monitor progress
    try:
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds

            stats = adapter.get_replay_statistics()
            progress = stats.get('progress_percentage', 0)
            current_time = stats.get('current_timestamp')

            logger.info(f"Progress: {progress:.1f}% | Current time: {current_time} | Signals: {signal_processor.signals_generated}")

            # Check if replay is complete
            if progress >= 100.0:
                logger.info("Replay completed!")
                break

    except KeyboardInterrupt:
        logger.info("Interrupted by user")

    # Shutdown
    await shutdown()


async def run_speed_test():
    """
    Speed test demonstrating different replay speeds
    """
    logger.info("🧪 Running Speed Test")

    # Load configuration from config system
    data_config = DataConfig()
    data_config.mode = "replay"

    symbols = data_config.symbols[:1]  # Use first symbol for speed test
    start_date = data_config.start_date or "2024-12-20"
    end_date = data_config.end_date or start_date

    speeds = [ReplaySpeed.REALTIME, ReplaySpeed.FAST_2X, ReplaySpeed.FAST_10X, ReplaySpeed.INSTANT]

    for speed in speeds:
        logger.info(f"Testing {speed.name} speed...")

        # Create adapter
        config = ReplayFeedConfig(
            replay_symbols=symbols,
            replay_start_date=start_date,
            replay_end_date=end_date,
            replay_speed=speed
        )

        adapter = HistoricalReplayFeedAdapter(config)

        # Connect and run quick test
        await adapter.connect()
        await adapter.subscribe(symbols, ['bar'])

        # Simple message counter
        message_count = 0
        async def count_messages(message: FeedMessage):
            nonlocal message_count
            message_count += 1

        adapter.add_message_handler(count_messages)

        # Start timing
        start_time = asyncio.get_event_loop().time()
        await adapter.start_replay()

        # Wait for completion or timeout
        timeout = 30.0 if speed != ReplaySpeed.INSTANT else 5.0
        try:
            await asyncio.wait_for(asyncio.sleep(1000), timeout=timeout)  # Long wait, but with timeout
        except asyncio.TimeoutError:
            pass  # Expected for slower speeds

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        await adapter.stop_replay()
        await adapter.disconnect()

        logger.info(f"  {speed.name}: {message_count} messages in {duration:.2f}s")


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--speed-test":
        asyncio.run(run_speed_test())
    elif len(sys.argv) > 1 and sys.argv[1].startswith("--config="):
        config_file = sys.argv[1].split("--config=", 1)[1]
        asyncio.run(main(config_file))
    else:
        asyncio.run(main())