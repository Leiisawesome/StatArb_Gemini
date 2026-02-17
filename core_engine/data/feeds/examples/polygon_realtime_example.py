#!/usr/bin/env python3
"""
Polygon/Massive Real-Time Feed Example
======================================

Demonstrates how to use the Polygon/Massive real-time feed integration
with the StatArb_Gemini data brick.

Prerequisites:
    1. Polygon Stock Advanced subscription (for real-time stocks streams)
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
from collections import defaultdict

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from core_engine.data import (
    # Simple service interface
    PolygonDataService,
    PolygonServiceConfig,
    create_polygon_service,
    create_polygon_rest_service,

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

# ============================================================================
# EXAMPLE 1: Simple Usage with PolygonDataService
# ============================================================================

async def simple_service_example():
    """
    Simple example using the high-level PolygonDataService.

    This is the recommended way to integrate Polygon/Massive data
    into your trading strategies.
    """
    log_section("EXAMPLE 1: Simple PolygonDataService Usage")

    # Get API key from environment
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY environment variable not set!")
        logger.info("Set it with: export POLYGON_API_KEY='your_key_here'")
        return

    # Define symbols to track
    symbols = ["AAPL", "TSLA", "NVDA", "GOOGL", "MSFT"]

    # Create service using convenience function
    log_subsection("Config")
    logger.info("Creating service for symbols: %s", symbols)

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

        log_subsection("Latest Bars")
        for symbol in symbols:
            df = service.get_latest_bars(symbol, timeframe='minute', limit=5)
            if not df.empty:
                logger.info("\n[%s]\n%s", symbol, df.to_string())
            else:
                logger.info("[%s] No bars received yet", symbol)

        # Get latest prices
        prices = service.get_all_latest_prices()
        log_subsection("Latest Prices")
        logger.info("%s", prices)

        # Get health status
        health = await service.health_check()
        log_subsection("Service Health")
        log_kv([
            ("healthy", health.get('healthy')),
            ("initialized", health.get('initialized')),
            ("operational", health.get('operational')),
            ("adapter_connected", health.get('adapter_connected')),
            ("messages_received", health.get('messages_received')),
            ("bars_processed", health.get('bars_processed')),
            ("trades_processed", health.get('trades_processed')),
            ("symbols_subscribed", health.get('symbols_subscribed')),
        ])

        # Get data for pipeline (Rule 2 format)
        df_pipeline = service.get_ohlcv_for_pipeline("AAPL", timeframe='minute')
        log_subsection("Pipeline Preview (AAPL)")
        logger.info("\n%s", df_pipeline.head().to_string())

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
    log_section("EXAMPLE 2: Real-Time Bar Callbacks")

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
        subscription_tier=PolygonSubscriptionTier.ADVANCED,
        data_types=["second_agg", "minute_agg", "quote"],
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
    log_section("EXAMPLE 3: Low-Level Adapter Usage")

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY not set")
        return

    # Create configuration
    config = PolygonFeedConfig(
        api_key=api_key,
        symbols=["META", "AMZN"],
        subscription_tier=PolygonSubscriptionTier.ADVANCED,
        data_types=["second_agg", "minute_agg", "trade", "quote"],
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
        logger.info("Connecting to Polygon/Massive websocket...")
        if await adapter.connect():
            logger.info("✅ Connected!")

            # Subscribe
            await adapter.subscribe(["META", "AMZN"], ["second_agg", "trade", "quote"])

            # Listen for messages
            logger.info("Listening for 5 seconds...")
            await asyncio.sleep(5)

            # Get statistics
            stats = adapter.get_statistics()
            log_subsection("Adapter Statistics")
            log_kv([
                ("messages_received", stats.get('messages_received')),
                ("messages_processed", stats.get('messages_processed')),
                ("errors", stats.get('errors')),
                ("reconnects", stats.get('reconnects')),
                ("connection_time", stats.get('connection_time')),
            ])

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
# EXAMPLE 4: Advanced Subscription Capability Showcase
# ============================================================================

async def advanced_subscription_capability_showcase():
    """
    Showcase what the Advanced subscription adds on top of baseline streams.

    Flow:
      1) STARTER tier client attempts quote subscription (expected local skip)
      2) ADVANCED tier client subscribes to trade/second_agg baseline
      3) ADVANCED tier client dynamically adds quote stream
      4) Prints capability table with counts and quote spread metrics
    """
    log_section("EXAMPLE 4: Advanced Subscription Capability Showcase")

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        logger.error("POLYGON_API_KEY not set")
        return

    symbols = ["SPY", "QQQ"]
    baseline_types = ["trade", "second_agg"]

    async def wait_for_stream_activity(
        label: str,
        total_counter,
        target_events: int = 1,
        base_seconds: int = 6,
        extension_seconds: int = 6,
        max_extra_seconds: int = 24,
    ) -> int:
        """Wait for stream messages, extending the window if the stream is idle."""
        await asyncio.sleep(base_seconds)

        elapsed = base_seconds
        while total_counter() < target_events and elapsed < base_seconds + max_extra_seconds:
            logger.info(
                "No stream events yet for %s; extending listen by %ss...",
                label,
                extension_seconds,
            )
            await asyncio.sleep(extension_seconds)
            elapsed += extension_seconds

        return elapsed

    starter_adapter = PolygonRealtimeFeedAdapter(
        PolygonFeedConfig(
            api_key=api_key,
            symbols=symbols,
            subscription_tier=PolygonSubscriptionTier.STARTER,
            data_types=baseline_types,
        )
    )

    starter_counts = defaultdict(int)

    def starter_handler(message):
        starter_counts[message.message_type] += 1

    starter_adapter.add_message_handler(starter_handler)

    starter_quote_ok = False
    try:
        if await starter_adapter.connect():
            await starter_adapter.subscribe(symbols, baseline_types)
            starter_quote_ok = await starter_adapter.subscribe(symbols, ["quote"])
            starter_wait_seconds = await wait_for_stream_activity(
                label="Starter baseline",
                total_counter=lambda: sum(starter_counts.values()),
            )

            starter_stats = starter_adapter.get_statistics()
            log_subsection("Tier Proof: Starter Client")
            log_kv([
                ("symbols", symbols),
                ("baseline_data_types", baseline_types),
                ("listen_seconds", starter_wait_seconds),
                ("quote_subscribe_result", starter_quote_ok),
                ("active_subscriptions", starter_stats.get("active_subscriptions", {})),
                ("messages_received", starter_stats.get("messages_received")),
                ("trade_count", starter_counts.get("trade", 0)),
                ("second_agg_count", starter_counts.get("second_agg", 0)),
                ("quote_count", starter_counts.get("quote", 0)),
            ])
    finally:
        await starter_adapter.disconnect()

    advanced_adapter = PolygonRealtimeFeedAdapter(
        PolygonFeedConfig(
            api_key=api_key,
            symbols=symbols,
            subscription_tier=PolygonSubscriptionTier.ADVANCED,
            data_types=baseline_types,
        )
    )

    advanced_counts = defaultdict(int)
    advanced_latencies = defaultdict(list)
    quote_spreads = []
    top_of_book_changes = 0
    last_top_of_book = {}

    def advanced_handler(message):
        nonlocal top_of_book_changes

        msg_type = message.message_type
        advanced_counts[msg_type] += 1

        if message.latency_ms is not None:
            advanced_latencies[msg_type].append(message.latency_ms)

        if msg_type != "quote":
            return

        bid = message.data.get("bid")
        ask = message.data.get("ask")
        if isinstance(bid, (int, float)) and isinstance(ask, (int, float)) and ask >= bid > 0:
            quote_spreads.append(ask - bid)

        top_of_book = (bid, ask, message.data.get("bid_size"), message.data.get("ask_size"))
        previous = last_top_of_book.get(message.symbol)
        if previous and previous != top_of_book:
            top_of_book_changes += 1
        last_top_of_book[message.symbol] = top_of_book

    advanced_adapter.add_message_handler(advanced_handler)

    advanced_quote_ok = False
    try:
        if not await advanced_adapter.connect():
            logger.error("Advanced showcase failed: unable to connect")
            return

        await advanced_adapter.subscribe(symbols, baseline_types)
        logger.info("Listening to baseline streams with adaptive window...")
        baseline_wait_seconds = await wait_for_stream_activity(
            label="Advanced baseline",
            total_counter=lambda: advanced_counts.get("trade", 0) + advanced_counts.get("second_agg", 0),
        )

        advanced_quote_ok = await advanced_adapter.subscribe(symbols, ["quote"])
        logger.info("Listening to baseline + quote streams with adaptive window...")
        quote_wait_seconds = await wait_for_stream_activity(
            label="Advanced quotes",
            total_counter=lambda: advanced_counts.get("quote", 0),
            base_seconds=8,
            extension_seconds=8,
            max_extra_seconds=32,
        )

        advanced_stats = advanced_adapter.get_statistics()

        trade_lat = advanced_latencies.get("trade", [])
        second_lat = advanced_latencies.get("second_agg", [])
        quote_lat = advanced_latencies.get("quote", [])

        avg_trade_latency = round(sum(trade_lat) / len(trade_lat), 2) if trade_lat else None
        avg_second_latency = round(sum(second_lat) / len(second_lat), 2) if second_lat else None
        avg_quote_latency = round(sum(quote_lat) / len(quote_lat), 2) if quote_lat else None

        avg_spread = round(sum(quote_spreads) / len(quote_spreads), 4) if quote_spreads else None
        min_spread = round(min(quote_spreads), 4) if quote_spreads else None
        max_spread = round(max(quote_spreads), 4) if quote_spreads else None

        log_subsection("Advanced Capability Summary")
        log_kv([
            ("symbols", symbols),
            ("baseline_listen_seconds", baseline_wait_seconds),
            ("quote_listen_seconds", quote_wait_seconds),
            ("quote_subscribe_result", advanced_quote_ok),
            ("active_subscriptions", advanced_stats.get("active_subscriptions", {})),
            ("messages_received", advanced_stats.get("messages_received")),
            ("trade_count", advanced_counts.get("trade", 0)),
            ("second_agg_count", advanced_counts.get("second_agg", 0)),
            ("quote_count", advanced_counts.get("quote", 0)),
            ("avg_trade_latency_ms", avg_trade_latency),
            ("avg_second_agg_latency_ms", avg_second_latency),
            ("avg_quote_latency_ms", avg_quote_latency),
            ("avg_quote_spread", avg_spread),
            ("min_quote_spread", min_spread),
            ("max_quote_spread", max_spread),
            ("top_of_book_changes", top_of_book_changes),
        ])

        log_subsection("Capability Table")
        logger.info(
            "\n"
            "  %-12s | %-17s | %-8s | %-8s\n"
            "  %s\n"
            "  %-12s | %-17s | %-8d | %-8s\n"
            "  %-12s | %-17s | %-8d | %-8s\n"
            "  %-12s | %-17s | %-8d | %-8s",
            "stream_type", "requires_advanced", "count", "sample",
            "-" * 58,
            "trade", "No", advanced_counts.get("trade", 0), "price/size",
            "second_agg", "No", advanced_counts.get("second_agg", 0), "OHLCV",
            "quote", "Yes", advanced_counts.get("quote", 0), "bid/ask",
        )

        if advanced_counts.get("quote", 0) == 0:
            log_subsection("Idle Stream Fallback (REST Snapshot)")
            rest_service = await create_polygon_rest_service(api_key=api_key)
            try:
                quote_map = await rest_service.get_last_quote_multi(symbols)
            finally:
                await rest_service.close()

            if quote_map:
                for symbol in symbols:
                    quote = quote_map.get(symbol, {})
                    if quote:
                        bid = quote.get("bid")
                        ask = quote.get("ask")
                        spread = (ask - bid) if isinstance(ask, (int, float)) and isinstance(bid, (int, float)) else None
                        log_kv([
                            ("symbol", symbol),
                            ("bid", bid),
                            ("ask", ask),
                            ("bid_size", quote.get("bid_size")),
                            ("ask_size", quote.get("ask_size")),
                            ("spread", round(spread, 4) if isinstance(spread, (int, float)) else None),
                        ])
            else:
                logger.warning("No REST snapshot quotes returned either. Market may be inactive or endpoint restricted.")

        if not starter_quote_ok and advanced_quote_ok and advanced_counts.get("quote", 0) > 0:
            logger.info("✅ Advanced capability verified: quote stream is active only in Advanced showcase stage.")
        elif not starter_quote_ok and advanced_quote_ok and advanced_counts.get("quote", 0) == 0:
            logger.info(
                "ℹ️ Advanced quote subscription succeeded, but no live quote events arrived in the listen window. "
                "REST snapshot fallback provided current NBBO quotes."
            )
        else:
            logger.warning("⚠️ Quote capability did not verify cleanly. Check subscription tier/API permissions.")

    except Exception as e:
        logger.error(f"Advanced showcase error: {e}")
    finally:
        await advanced_adapter.disconnect()

# ============================================================================
# EXAMPLE 5: Integration with Pipeline (Rule 2)
# ============================================================================

async def pipeline_integration_example():
    """
    Example showing how Polygon data integrates with the processing pipeline.

    This follows Rule 2: Unified Data Flow Pipeline
    Phase 1: Data Ingestion → provides DataFrame for Phase 2 (Indicators)
    """
    log_section("EXAMPLE 5: Pipeline Integration (Rule 2)")

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

        log_subsection("Sample OHLCV DataFrame (Phase 1 output)")
        logger.info("\n%s", sample_data.to_string())
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

        log_subsection("Phase 1 Output (Pipeline-Ready OHLCV)")
        log_kv([
            ("Columns", list(df.columns)),
            ("Shape", df.shape),
        ])
        logger.info("\n%s", df.tail(10).to_string())

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
    log_section("POLYGON/MASSIVE REAL-TIME FEED EXAMPLES")

    examples = [
        ("Simple Service", simple_service_example),
        ("Bar Callbacks", callback_example),
        ("Low-Level Adapter", low_level_adapter_example),
        ("Advanced Capability Showcase", advanced_subscription_capability_showcase),
        ("Pipeline Integration", pipeline_integration_example),
    ]

    # Run advanced capability showcase by default (uncomment loop below to run all)
    example_name, example_func = examples[3]
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

