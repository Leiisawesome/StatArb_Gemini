#!/usr/bin/env python3
"""
Polygon.io REST API Historical Data Example
============================================

Demonstrates how to use the Polygon.io REST API to fetch historical
market data with the Stock Starter subscription plan.

This example shows how to get 1-minute bars for TSLA on 2024-12-20.

Prerequisites:
    1. Polygon.io Stock Starter subscription
    2. API key set as environment variable: POLYGON_API_KEY

Usage:
    export POLYGON_API_KEY="your_api_key_here"
    python polygon_rest_historical_example.py

Author: StatArb_Gemini Core Engine
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

from core_engine.data.feeds.polygon_rest import (
    create_polygon_rest_service,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('polygon_rest_example')

# ============================================================================
# EXAMPLE 1: Basic Historical Data Retrieval
# ============================================================================

async def basic_historical_example():
    """
    Basic example: Get 1-minute bars for TSLA on 2024-12-20
    """
    logger.info("=" * 60)
    logger.info("EXAMPLE 1: Basic Historical 1-Minute Bars")
    logger.info("=" * 60)

    # Get API key
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY environment variable not set!")
        return

    try:
        # Create and initialize service
        logger.info("Creating Polygon REST service...")
        service = await create_polygon_rest_service(api_key=api_key)
        logger.info("✅ Service initialized successfully!")

        # Define the date we want (2024-12-20)
        target_date = datetime(2024, 12, 20, tzinfo=timezone.utc)
        symbol = "TSLA"

        logger.info(f"Fetching 1-minute bars for {symbol} on {target_date.date()}...")

        # Method 1: Using start/end dates
        df = await service.get_bars(
            symbol=symbol,
            timeframe="1min",
            start=target_date,
            end=target_date.replace(hour=23, minute=59, second=59),  # End of day
        )

        logger.info(f"Retrieved {len(df)} bars for {symbol}")
        logger.info(f"Data range: {df.index.min()} to {df.index.max()}")

        if not df.empty:
            logger.info("\nFirst 5 bars:")
            logger.info(df.head().to_string())

            logger.info("\nLast 5 bars:")
            logger.info(df.tail().to_string())

            # Basic statistics
            logger.info(f"\nDaily Statistics for {symbol} on {target_date.date()}:")
            logger.info(f"  Opening Price: ${df['open'].iloc[0]:.2f}")
            logger.info(f"  Closing Price: ${df['close'].iloc[-1]:.2f}")
            logger.info(f"  High: ${df['high'].max():.2f}")
            logger.info(f"  Low: ${df['low'].min():.2f}")
            logger.info(f"  Total Volume: {df['volume'].sum():,.0f}")
            logger.info(f"  Average Volume per bar: {df['volume'].mean():,.0f}")

        # Clean up
        await service.close()
        logger.info("✅ Service closed")

    except Exception as e:
        logger.error(f"Example failed: {e}")

# ============================================================================
# EXAMPLE 2: Multiple Days Historical Data
# ============================================================================

async def multi_day_example():
    """
    Get multiple days of 1-minute data for TSLA
    """
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 2: Multi-Day Historical Data")
    logger.info("=" * 60)

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY environment variable not set!")
        return

    try:
        service = await create_polygon_rest_service(api_key=api_key)

        symbol = "TSLA"
        days = 5  # Get last 5 trading days

        logger.info(f"Fetching {days} days of 1-minute bars for {symbol}...")

        df = await service.get_bars(
            symbol=symbol,
            timeframe="1min",
            days=days
        )

        logger.info(f"Retrieved {len(df)} bars across {df.index.date.nunique()} days")

        # Group by date and show daily summaries
        daily_summary = df.groupby(df.index.date).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        logger.info(f"\nDaily Summary for {symbol} (last {days} days):")
        logger.info(daily_summary.to_string())

        await service.close()

    except Exception as e:
        logger.error(f"Multi-day example failed: {e}")

# ============================================================================
# EXAMPLE 3: Multiple Symbols Comparison
# ============================================================================

async def multi_symbol_example():
    """
    Compare 1-minute data for multiple symbols on the same day
    """
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 3: Multi-Symbol Comparison")
    logger.info("=" * 60)

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY environment variable not set!")
        return

    try:
        service = await create_polygon_rest_service(api_key=api_key)

        symbols = ["TSLA", "AAPL", "NVDA"]
        target_date = datetime(2024, 12, 20, tzinfo=timezone.utc)

        logger.info(f"Fetching 1-minute bars for {symbols} on {target_date.date()}...")

        # Get data for all symbols
        results = await service.get_bars_multi(
            symbols=symbols,
            timeframe="1min",
            days=1  # This will get data around our target date
        )

        # Compare closing prices at the same time
        logger.info(f"\nClosing Prices Comparison at {target_date.date()}:")

        for symbol, df in results.items():
            if not df.empty:
                # Filter to our target date
                day_data = df[df.index.date == target_date.date()]
                if not day_data.empty:
                    close_price = day_data['close'].iloc[-1]
                    volume = day_data['volume'].sum()
                    logger.info(f"  {symbol}: ${close_price:.2f} (Volume: {volume:,.0f})")
                else:
                    logger.info(f"  {symbol}: No data for target date")
            else:
                logger.info(f"  {symbol}: No data available")

        await service.close()

    except Exception as e:
        logger.error(f"Multi-symbol example failed: {e}")

# ============================================================================
# EXAMPLE 4: Previous Day Data
# ============================================================================

async def previous_day_example():
    """
    Get previous day aggregate data (useful for getting latest prices)
    """
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 4: Previous Day Data")
    logger.info("=" * 60)

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY environment variable not set!")
        return

    try:
        service = await create_polygon_rest_service(api_key=api_key)

        symbol = "TSLA"

        logger.info(f"Getting previous day data for {symbol}...")

        prev_day = await service.get_previous_day(symbol)

        if prev_day:
            logger.info("Previous Day Data:")
            logger.info(f"  Date: {prev_day.timestamp.date()}")
            logger.info(f"  Open: ${prev_day.open:.2f}")
            logger.info(f"  High: ${prev_day.high:.2f}")
            logger.info(f"  Low: ${prev_day.low:.2f}")
            logger.info(f"  Close: ${prev_day.close:.2f}")
            logger.info(f"  Volume: {prev_day.volume:,.0f}")
            if prev_day.vwap:
                logger.info(f"  VWAP: ${prev_day.vwap:.2f}")
            if prev_day.num_trades:
                logger.info(f"  Number of Trades: {prev_day.num_trades:,.0f}")
        else:
            logger.info(f"No previous day data available for {symbol}")

        await service.close()

    except Exception as e:
        logger.error(f"Previous day example failed: {e}")

async def second_aggregates_example():
    """
    Get historical second aggregated data for TSLA
    """
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 5: Second Aggregates Historical Data")
    logger.info("=" * 60)

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY environment variable not set!")
        return

    try:
        service = await create_polygon_rest_service(api_key=api_key)

        symbol = "TSLA"
        # Get just 1 hour of second data to avoid rate limits
        start_time = datetime(2024, 12, 20, 9, 30, tzinfo=timezone.utc)  # 9:30 AM
        end_time = datetime(2024, 12, 20, 10, 30, tzinfo=timezone.utc)   # 10:30 AM

        logger.info(f"Fetching second aggregates for {symbol} from {start_time} to {end_time}...")

        df = await service.get_bars(
            symbol=symbol,
            timeframe="1s",  # Second aggregates
            start=start_time,
            end=end_time,
        )

        logger.info(f"Retrieved {len(df)} second bars for {symbol}")

        if not df.empty:
            logger.info("\nFirst 10 second bars:")
            logger.info(df.head(10).to_string())

            logger.info("\nLast 10 second bars:")
            logger.info(df.tail(10).to_string())

            # Statistics
            logger.info(f"\nSecond Data Statistics for {symbol}:")
            logger.info(f"  Time Range: {df.index.min()} to {df.index.max()}")
            logger.info(f"  Total Seconds: {len(df)}")
            logger.info(f"  Average Volume per Second: {df['volume'].mean():.1f}")
            logger.info(f"  Max Volume in a Second: {df['volume'].max():,.0f}")
            logger.info(f"  Price Range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")

            # Check data quality
            gaps = df.index.to_series().diff().dt.total_seconds() > 1
            gap_count = gaps.sum()
            logger.info(f"  Data Gaps (>1 second): {gap_count}")

        await service.close()

    except Exception as e:
        logger.error(f"Second aggregates example failed: {e}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """
    Run all examples
    """
    logger.info("🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷")
    logger.info("POLYGON.IO REST API HISTORICAL DATA EXAMPLES")
    logger.info("🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷🔷")
    logger.info("")

    examples = [
        ("Basic Historical 1-Min Bars", basic_historical_example),
        ("Multi-Day Data", multi_day_example),
        ("Multi-Symbol Comparison", multi_symbol_example),
        ("Previous Day Data", previous_day_example),
        ("Second Aggregates", second_aggregates_example),
    ]

    # Run only the second aggregates example for demo (uncomment to run all)
    example_name, example_func = examples[4]  # Second aggregates example
    logger.info(f"🚀 Running: {example_name}\n")

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
    #     await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())