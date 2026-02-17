#!/usr/bin/env python3
"""
Polygon/Massive REST API Historical Data Example
================================================

Demonstrates how to use the Polygon/Massive REST API to fetch historical
market data with Stocks plan access.

This example shows how to get 1-minute bars for TSLA on 2024-12-20.

Prerequisites:
    1. Polygon Stocks Starter subscription (or higher)
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


def log_section(title: str) -> None:
    """Log a top-level section header."""
    border = "=" * 76
    logger.info("\n%s", border)
    logger.info("%s", title)
    logger.info("%s", border)


def log_subsection(title: str) -> None:
    """Log a subsection header."""
    logger.info("\n%s", f"--- {title} ---")


def log_kv(items):
    """Log aligned key-value rows for readability."""
    if not items:
        return
    width = max(len(str(k)) for k, _ in items)
    lines = [f"  {str(k):<{width}} : {v}" for k, v in items]
    logger.info("\n%s", "\n".join(lines))


def log_df_preview(title: str, df, rows: int = 10) -> None:
    """Log a compact DataFrame preview block."""
    log_subsection(title)
    if df.empty:
        logger.info("  (empty)")
        return
    logger.info("\n%s", df.head(rows).to_string())


def parse_event_timestamp(raw_timestamp):
    """Parse timestamps in seconds/ms/us/ns to UTC datetime."""
    try:
        timestamp_value = float(raw_timestamp)
    except (TypeError, ValueError):
        return None

    abs_value = abs(timestamp_value)
    if abs_value >= 1e17:  # nanoseconds
        seconds = timestamp_value / 1e9
    elif abs_value >= 1e14:  # microseconds
        seconds = timestamp_value / 1e6
    elif abs_value >= 1e11:  # milliseconds
        seconds = timestamp_value / 1e3
    else:  # seconds
        seconds = timestamp_value

    return datetime.fromtimestamp(seconds, tz=timezone.utc)

# ============================================================================
# EXAMPLE 1: Basic Historical Data Retrieval
# ============================================================================

async def basic_historical_example():
    """
    Basic example: Get 1-minute bars for TSLA on 2024-12-20
    """
    log_section("EXAMPLE 1: Basic Historical 1-Minute Bars")

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
    log_section("EXAMPLE 2: Multi-Day Historical Data")

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
    log_section("EXAMPLE 3: Multi-Symbol Comparison")

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
    log_section("EXAMPLE 4: Previous Day Data")

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
    log_section("EXAMPLE 5: Second Aggregates Historical Data")

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

        logger.info("Retrieved %s second bars for %s", len(df), symbol)

        if not df.empty:
            log_df_preview("First 10 second bars", df, rows=10)

            log_subsection("Last 10 second bars")
            logger.info("\n%s", df.tail(10).to_string())

            gaps = df.index.to_series().diff().dt.total_seconds() > 1
            gap_count = gaps.sum()

            log_subsection(f"Summary Statistics ({symbol})")
            log_kv([
                ("Time Range", f"{df.index.min()} to {df.index.max()}"),
                ("Total Seconds", len(df)),
                ("Avg Volume / Sec", f"{df['volume'].mean():.1f}"),
                ("Max Volume / Sec", f"{df['volume'].max():,.0f}"),
                ("Price Range", f"${df['low'].min():.2f} - ${df['high'].max():.2f}"),
                ("Data Gaps (>1 sec)", gap_count),
            ])

            # Quote + Last Trade snapshot for readability/completeness
            quote_map = await service.get_last_quote_multi([symbol])
            quote = quote_map.get(symbol, {})

            trade_url = f"{service.config.base_url}/v2/last/trade/{symbol.upper()}"
            trade_data = await service._request(trade_url)
            trade = trade_data.get('results', {}) if trade_data.get('status') == 'OK' else {}

            trade_ts = parse_event_timestamp(trade.get('t')) if trade else None

            log_subsection(f"Latest Quote + Last Trade Snapshot ({symbol})")
            log_kv([
                ("Snapshot Scope", "Current market snapshot (not limited to historical range above)"),
                ("Bid", f"${quote.get('bid', 0):.4f}" if quote else "n/a"),
                ("Ask", f"${quote.get('ask', 0):.4f}" if quote else "n/a"),
                ("Bid Size", quote.get('bid_size', "n/a") if quote else "n/a"),
                ("Ask Size", quote.get('ask_size', "n/a") if quote else "n/a"),
                ("Last Trade Price", f"${float(trade.get('p', 0)):.4f}" if trade else "n/a"),
                ("Last Trade Size", trade.get('s', "n/a") if trade else "n/a"),
                ("Last Trade Time", trade_ts.isoformat() if trade_ts else "n/a"),
            ])

        await service.close()

    except Exception as e:
        logger.error(f"Second aggregates example failed: {e}")


async def second_trade_quote_snapshots_example():
    """
    Build 1-second historical snapshots that include both trades and quotes.
    """
    log_section("EXAMPLE 6: Historical Trade + Quote Snapshot Per Second")

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY environment variable not set!")
        return

    try:
        service = await create_polygon_rest_service(api_key=api_key)

        symbol = "TSLA"
        start_time = datetime(2024, 12, 20, 9, 30, tzinfo=timezone.utc)
        end_time = datetime(2024, 12, 20, 10, 30, tzinfo=timezone.utc)

        logger.info(
            "Building 1-second trade+quote snapshots for %s from %s to %s...",
            symbol,
            start_time,
            end_time,
        )

        snapshot_df = await service.get_trade_quote_snapshots_1s(
            symbol=symbol,
            start=start_time,
            end=end_time,
            forward_fill_quotes=True,
            forward_fill_trades=False,
            max_pages=50,
        )

        logger.info("Built %s second snapshots for %s", len(snapshot_df), symbol)

        if not snapshot_df.empty:
            log_df_preview("First 10 trade+quote snapshots", snapshot_df, rows=10)

            log_subsection("Last 10 trade+quote snapshots")
            logger.info("\n%s", snapshot_df.tail(10).to_string())

            trade_count_series = snapshot_df.get('trade_count')
            quote_count_series = snapshot_df.get('quote_count')

            trade_count_series = trade_count_series.fillna(0).astype(int) if trade_count_series is not None else None
            quote_count_series = quote_count_series.fillna(0).astype(int) if quote_count_series is not None else None

            seconds_with_trade = int((trade_count_series > 0).sum()) if trade_count_series is not None else 0
            seconds_with_quote = int((quote_count_series > 0).sum()) if quote_count_series is not None else 0

            avg_spread = snapshot_df['spread'].dropna().mean() if 'spread' in snapshot_df.columns else None

            log_subsection(f"Snapshot Coverage ({symbol})")
            log_kv([
                ("Time Range", f"{snapshot_df.index.min()} to {snapshot_df.index.max()}"),
                ("Total Seconds", len(snapshot_df)),
                ("Seconds With Trade", seconds_with_trade),
                ("Seconds With Quote", seconds_with_quote),
                ("Trade Coverage", f"{(seconds_with_trade / len(snapshot_df) * 100):.2f}%"),
                ("Quote Coverage", f"{(seconds_with_quote / len(snapshot_df) * 100):.2f}%"),
                ("Avg Spread", f"{avg_spread:.4f}" if avg_spread is not None else "n/a"),
            ])

        await service.close()

    except Exception as e:
        logger.error(f"Trade+quote snapshot example failed: {e}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """
    Run all examples
    """
    log_section("POLYGON/MASSIVE REST API HISTORICAL DATA EXAMPLES")

    examples = [
        ("Basic Historical 1-Min Bars", basic_historical_example),
        ("Multi-Day Data", multi_day_example),
        ("Multi-Symbol Comparison", multi_symbol_example),
        ("Previous Day Data", previous_day_example),
        ("Second Aggregates", second_aggregates_example),
        ("Second Trade+Quote Snapshots", second_trade_quote_snapshots_example),
    ]

    # Run only the trade+quote snapshot example for demo (uncomment to run all)
    example_name, example_func = examples[5]
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