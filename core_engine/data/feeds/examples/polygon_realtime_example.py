#!/usr/bin/env python3
"""
Polygon.io Real-Time Feed Example
==================================

Demonstrates how to use the Polygon.io real-time feed integration
with the StatArb_Gemini data brick.

Prerequisites:
    1. Polygon.io Stock Starter subscription (or higher)
    2. API key set as environment variable: POLYGON_API_KEY
    3. Install websockets: pip install websockets

Usage:
    export POLYGON_API_KEY="your_api_key_here"
    python polygon_realtime_example.py

Author: StatArb_Gemini Core Engine
"""

import asyncio
import logging
import os
import sys

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..')))

from core_engine.data import (
    # Simple service interface
    PolygonDataService,
    PolygonServiceConfig,
    create_polygon_service,

    # Low-level adapter (for advanced usage)
    PolygonRealtimeFeedAdapter,
    PolygonFeedConfig,
    PolygonSubscriptionTier,
    PolygonAggregateBar,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('polygon_example')

# ============================================================================
# EXAMPLE 1: Simple Usage with PolygonDataService
# ============================================================================

async def simple_service_example():
    """
    Simple example using the high-level PolygonDataService.

    This is the recommended way to integrate Polygon.io data
    into your trading strategies.
    """
    logger.info("=" * 60)
    logger.info("EXAMPLE 1: Simple PolygonDataService Usage")
    logger.info("=" * 60)

    # Get API key from environment
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY environment variable not set!")
        logger.info("Set it with: export POLYGON_API_KEY='your_key_here'")
        return

    # Define symbols to track
    symbols = ["AAPL", "TSLA", "NVDA", "GOOGL", "MSFT"]

    # Create service using convenience function
    logger.info(f"Creating service for symbols: {symbols}")

    try:
        service = await create_polygon_service(
            api_key=api_key,
            symbols=symbols,
            auto_start=True,
        )

        logger.info("✅ Service started successfully!")

        # Wait for some data to accumulate
        logger.info("Waiting for real-time data...")
        await asyncio.sleep(5)

        # Get latest bars as DataFrame
        for symbol in symbols:
            df = service.get_latest_bars(symbol, timeframe='minute', limit=5)
            if not df.empty:
                logger.info(f"\n{symbol} Latest Minute Bars:\n{df.to_string()}")
            else:
                logger.info(f"{symbol}: No bars received yet")

        # Get latest prices
        prices = service.get_all_latest_prices()
        logger.info(f"\nLatest Prices: {prices}")

        # Get health status
        health = await service.health_check()
        logger.info(f"\nService Health: {health}")

        # Get data for pipeline (Rule 2 format)
        df_pipeline = service.get_ohlcv_for_pipeline("AAPL", timeframe='minute')
        logger.info(f"\nPipeline-ready AAPL data:\n{df_pipeline.head().to_string()}")

        # Stop service
        await service.stop()
        logger.info("✅ Service stopped")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise

# ============================================================================
# EXAMPLE 2: With Bar Callbacks for Real-Time Strategy Updates
# ============================================================================

async def callback_example():
    """
    Example showing how to register callbacks for real-time bar updates.

    This pattern is useful for strategies that need to react
    immediately when new bars arrive.
    """
    logger.info("=" * 60)
    logger.info("EXAMPLE 2: Real-Time Bar Callbacks")
    logger.info("=" * 60)

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY not set")
        return

    # Create custom bar handler
    def on_new_bar(symbol: str, timeframe: str, bar: PolygonAggregateBar):
        """Called whenever a new bar is received"""
        logger.info(
            f"📊 NEW BAR | {symbol} {timeframe} | "
            f"O:{bar.open:.2f} H:{bar.high:.2f} L:{bar.low:.2f} C:{bar.close:.2f} "
            f"V:{bar.volume:,.0f} | Trades:{bar.num_trades}"
        )

    # Create service
    config = PolygonServiceConfig(
        api_key=api_key,
        symbols=["SPY", "QQQ"],
        data_types=["second_agg", "minute_agg"],  # Get both for more frequent updates
    )

    service = PolygonDataService(config=config)

    # Register callback BEFORE starting
    service.add_bar_callback(on_new_bar)

    try:
        await service.initialize()
        await service.start()

        logger.info("Listening for real-time bars... (10 seconds)")
        await asyncio.sleep(10)

        await service.stop()

    except Exception as e:
        logger.error(f"Error: {e}")
        await service.stop()

# ============================================================================
# EXAMPLE 3: Low-Level Adapter Usage
# ============================================================================

async def low_level_adapter_example():
    """
    Example showing direct usage of PolygonRealtimeFeedAdapter.

    Use this when you need fine-grained control over the WebSocket
    connection and message handling.
    """
    logger.info("=" * 60)
    logger.info("EXAMPLE 3: Low-Level Adapter Usage")
    logger.info("=" * 60)

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY not set")
        return

    # Create configuration
    config = PolygonFeedConfig(
        api_key=api_key,
        symbols=["META", "AMZN"],
        subscription_tier=PolygonSubscriptionTier.STARTER,
        data_types=["second_agg", "minute_agg", "trade"],
        connect_timeout_seconds=30.0,
    )

    # Create adapter directly
    adapter = PolygonRealtimeFeedAdapter(config)

    # Add custom message handler
    def handle_message(message):
        logger.info(f"📩 {message.message_type} | {message.symbol} | {message.data}")

    adapter.add_message_handler(handle_message)

    try:
        # Connect
        logger.info("Connecting to Polygon.io...")
        if await adapter.connect():
            logger.info("✅ Connected!")

            # Subscribe
            await adapter.subscribe(["META", "AMZN"], ["second_agg", "trade"])

            # Listen for messages
            logger.info("Listening for 5 seconds...")
            await asyncio.sleep(5)

            # Get statistics
            stats = adapter.get_statistics()
            logger.info(f"Statistics: {stats}")

            # Unsubscribe and disconnect
            await adapter.unsubscribe(["META", "AMZN"])
            await adapter.disconnect()
            logger.info("✅ Disconnected")
        else:
            logger.error("❌ Connection failed")

    except Exception as e:
        logger.error(f"Error: {e}")
        await adapter.disconnect()

# ============================================================================
# EXAMPLE 4: Integration with Pipeline (Rule 2)
# ============================================================================

async def pipeline_integration_example():
    """
    Example showing how Polygon data integrates with the processing pipeline.

    This follows Rule 2: Unified Data Flow Pipeline
    Phase 1: Data Ingestion → provides DataFrame for Phase 2 (Indicators)
    """
    logger.info("=" * 60)
    logger.info("EXAMPLE 4: Pipeline Integration (Rule 2)")
    logger.info("=" * 60)

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.info("POLYGON_API_KEY not set - using sample data")

        # Create sample DataFrame to show expected format
        import pandas as pd
        import numpy as np

        dates = pd.date_range('2024-01-01 09:30', periods=10, freq='1min')
        sample_data = pd.DataFrame({
            'open': np.random.uniform(150, 151, 10),
            'high': np.random.uniform(151, 152, 10),
            'low': np.random.uniform(149, 150, 10),
            'close': np.random.uniform(150, 151, 10),
            'volume': np.random.randint(10000, 100000, 10),
        }, index=dates)

        logger.info("Sample OHLCV DataFrame (Phase 1 output):")
        logger.info(f"\n{sample_data.to_string()}")
        logger.info("\nThis DataFrame format is ready for Phase 2 (Indicators)")
        return

    # Real Polygon data
    service = await create_polygon_service(
        api_key=api_key,
        symbols=["AAPL"],
    )

    try:
        # Wait for data
        await asyncio.sleep(10)

        # Get pipeline-ready data
        df = service.get_ohlcv_for_pipeline("AAPL")

        logger.info("Phase 1 Output (Pipeline-Ready OHLCV):")
        logger.info(f"\nColumns: {list(df.columns)}")
        logger.info(f"Shape: {df.shape}")
        logger.info(f"\n{df.tail(10).to_string()}")

        logger.info("\n✅ This DataFrame is ready for EnhancedTechnicalIndicators (Phase 2)")

        await service.stop()

    except Exception as e:
        logger.error(f"Error: {e}")
        await service.stop()

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all examples"""
    logger.info("\n" + "🔷" * 30)
    logger.info("POLYGON.IO REAL-TIME FEED EXAMPLES")
    logger.info("🔷" * 30 + "\n")

    examples = [
        ("Simple Service", simple_service_example),
        ("Bar Callbacks", callback_example),
        ("Low-Level Adapter", low_level_adapter_example),
        ("Pipeline Integration", pipeline_integration_example),
    ]

    # Run only the first example for demo (uncomment to run all)
    example_name, example_func = examples[0]
    logger.info(f"\n🚀 Running: {example_name}\n")

    try:
        await example_func()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}")

    # Uncomment to run all examples:
    # for name, func in examples:
    #     logger.info(f"\n🚀 Running: {name}\n")
    #     try:
    #         await func()
    #     except Exception as e:
    #         logger.error(f"{name} failed: {e}")
    #     await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())

