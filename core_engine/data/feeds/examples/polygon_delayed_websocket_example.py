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
    1. Polygon.io Stock Starter subscription (includes delayed websockets!)
    2. API key set as environment variable: POLYGON_API_KEY
    3. Install websockets: pip install websockets

Usage:
    export POLYGON_API_KEY="your_api_key_here"
    python polygon_delayed_websocket_example.py

Author: StatArb_Gemini Core Engine
"""

import asyncio
import json
import logging
import os
import ssl
import sys
from datetime import datetime

import websockets

# Disable proxy usage for websockets
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

# Create SSL context that doesn't verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

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
    Example using the 15-minute delayed WebSocket feed with raw websockets
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
    logger.info("This provides 15-minute delayed data from live markets...")
    
    # Check market status
    try:
        import requests
        market_url = f"https://api.polygon.io/v1/marketstatus/now?apiKey={api_key}"
        market_response = requests.get(market_url, timeout=5)
        if market_response.status_code == 200:
            market_data = market_response.json()
            market_status = market_data.get('market', 'unknown')
            logger.info(f"📊 Market Status: {market_status.upper()}")
            if market_status == 'closed':
                logger.warning("⚠️  Market is closed - delayed feed may not stream data until market opens")
            else:
                logger.info("✅ Market is open - expecting live delayed data")
        else:
            logger.warning("⚠️  Could not check market status")
    except Exception as e:
        logger.warning(f"⚠️  Market status check failed: {e}")

    # Message counter
    message_count = {"bars": 0, "trades": 0, "total": 0}

    uri = "wss://delayed.massive.com/stocks"

    try:
        async with websockets.connect(uri, proxy=None, ssl=ssl_context) as websocket:
            logger.info("✅ Connected to delayed websocket")

            # Send authentication
            auth_msg = {"action": "auth", "params": api_key}
            await websocket.send(json.dumps(auth_msg))
            logger.info("✅ Sent authentication")

            # Wait for auth response - check next few messages
            auth_success = False
            for i in range(3):  # Check next 3 messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    logger.info(f"Message {i+1}: {data}")

                    if isinstance(data, list):
                        for msg in data:
                            if msg.get('status') == 'auth_success':
                                auth_success = True
                                logger.info("✅ Authentication successful")
                                break
                    elif isinstance(data, dict) and data.get('status') == 'auth_success':
                        auth_success = True
                        logger.info("✅ Authentication successful")
                        break
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for message {i+1}")
                    break

            if not auth_success:
                logger.error("❌ Authentication failed - no auth_success message received")
                return

            # Subscribe to data streams
            subscribe_msg = {"action": "subscribe", "params": "A.TSLA,A.AAPL,A.NVDA,AM.TSLA,AM.AAPL,AM.NVDA,T.TSLA,T.AAPL,T.NVDA"}
            await websocket.send(json.dumps(subscribe_msg))
            logger.info("✅ Subscribed to data streams")
            logger.info("Note: Data is 15 minutes delayed from real-time")

            # Listen for data
            logger.info("Waiting for delayed market data...")

            timeout = 60  # Increased timeout for testing
            max_messages = 20  # Increased limit for better analysis
            try:
                while message_count["total"] < max_messages:
                    response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    data = json.loads(response)

                    if isinstance(data, list):
                        for msg in data:
                            message_count["total"] += 1

                            # Extract timestamp based on message type
                            timestamp = None
                            if msg.get('ev') in ['A', 'AM']:  # Aggregates use 's' (start timestamp)
                                timestamp = msg.get('s')
                            elif msg.get('ev') == 'T':  # Trades use 't' (trade timestamp)
                                timestamp = msg.get('t')
                            
                            if timestamp:
                                try:
                                    timestamp_dt = datetime.fromtimestamp(timestamp / 1000.0)
                                    logger.info(f"🕒 TIMESTAMP: {timestamp_dt}")
                                except Exception as e:
                                    logger.warning(f"🕒 TIMESTAMP: Failed to convert {timestamp}: {e}")
                            else:
                                logger.warning(f"🕒 TIMESTAMP: No timestamp found in {msg.get('ev')} message")

                            if msg.get('ev') == 'A':  # Second aggregate
                                message_count["bars"] += 1
                                logger.info(f"📊 BAR [{msg.get('sym')}] ${msg.get('c'):.2f} Vol:{msg.get('v')} | Full msg: {msg}")
                            elif msg.get('ev') == 'AM':  # Minute aggregate
                                message_count["bars"] += 1
                                logger.info(f"📊 MIN BAR [{msg.get('sym')}] ${msg.get('c'):.2f} Vol:{msg.get('v')} | Full msg: {msg}")
                            elif msg.get('ev') == 'T':  # Trade
                                message_count["trades"] += 1
                                logger.info(f"💰 TRADE [{msg.get('sym')}] ${msg.get('p'):.2f} Size:{msg.get('s')} | Full msg: {msg}")
                            else:
                                # Handle status messages specially
                                if msg.get('ev') == 'status':
                                    status = msg.get('status', 'unknown')
                                    message = msg.get('message', '')
                                    if status == 'error':
                                        logger.warning(f"❌ Status Error: {message}")
                                    elif status == 'success':
                                        logger.info(f"✅ Status Success: {message}")
                                    else:
                                        logger.debug(f"📨 Status: {status} - {message}")
                                else:
                                    logger.info(f"📨 Other message: {msg}")
                    else:
                        logger.info(f"📨 Single message: {data}")

                    # Reset timeout after receiving first data
                    timeout = 10

            except asyncio.TimeoutError:
                logger.info("Timeout reached, disconnecting...")

        # Summary
        logger.info("\n📈 Session Summary:")
        logger.info(f"  Bars received: {message_count['bars']}")
        logger.info(f"  Trades received: {message_count['trades']}")
        logger.info(f"  Total messages: {message_count['total']}")

        if message_count["total"] == 0:
            logger.warning("⚠️ No data received. This could mean:")
            logger.warning("  - Market is closed (no trading activity)")
            logger.warning("  - No trading activity in the symbols")
            logger.warning("  - Network connectivity issues")
            logger.warning("  - API key permissions")
            logger.info("💡 Try running during market hours (9:30 AM - 4:00 PM ET)")
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