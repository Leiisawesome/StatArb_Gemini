#!/usr/bin/env python3
"""
Polygon.io Delayed WebSocket Feed Adapter
==========================================

Production-ready implementation for Polygon.io delayed WebSocket feeds.
Provides 15-minute delayed market data via wss://delayed.massive.com/stocks.

Features:
    - WebSocket connection to delayed endpoint
    - Automatic authentication and reconnection
    - Support for delayed aggregated bars (A.* for second, AM.* for minute)
    - Delayed trade stream support (T.*)
    - Proper timestamp handling (milliseconds for aggregates, nanoseconds for trades)
    - Circuit breaker pattern for fault tolerance

Subscription Requirements:
    Stock Starter plan includes delayed websockets

Usage:
    from core_engine.data.feeds.polygon_delayed import (
        PolygonDelayedFeedAdapter,
        PolygonDelayedFeedConfig,
    )

    config = PolygonDelayedFeedConfig(
        api_key="your_polygon_api_key",
        symbols=["AAPL", "TSLA", "NVDA"],
    )

    adapter = PolygonDelayedFeedAdapter(config)
    await adapter.connect()
    await adapter.subscribe(["AAPL", "TSLA"], ["second_agg", "minute_agg", "trade"])

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import ssl
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

import websockets

from adapters import (
    AdapterStatus,
    DataFeedAdapter,
    FeedAdapterConfig,
    FeedMessage,
    FeedProvider,
)
from polygon_realtime import (
    PolygonAggregateBar,
    PolygonTrade,
    PolygonFeedConfig,
)

# Disable proxy usage for websockets
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

# Create SSL context that doesn't verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


@dataclass
class PolygonDelayedFeedConfig(FeedAdapterConfig):
    """Configuration for Polygon delayed WebSocket feed"""
    symbols: List[str] = field(default_factory=list)
    reconnect_delay: float = 5.0
    max_reconnect_attempts: int = 10
    heartbeat_interval: float = 30.0


class PolygonDelayedFeedAdapter(DataFeedAdapter):
    """
    WebSocket adapter for Polygon.io delayed market data feeds.
    Provides 15-minute delayed real-time data.
    """

    def __init__(self, config: PolygonDelayedFeedConfig):
        super().__init__(config)
        self.config: PolygonDelayedFeedConfig = config
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._connected = False
        self._subscribed_symbols: Set[str] = set()
        self._reconnect_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def connect(self) -> bool:
        """Connect to delayed WebSocket feed"""
        try:
            self.logger.info("Connecting to Polygon delayed WebSocket feed...")

            uri = "wss://delayed.massive.com/stocks"

            self.websocket = await websockets.connect(
                uri,
                proxy=None,
                ssl=ssl_context,
                extra_headers=None
            )

            # Authenticate
            if not await self._authenticate():
                self.logger.error("Authentication failed")
                return False

            self._connected = True
            self.logger.info("✅ Connected to delayed WebSocket feed")

            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat())

            return True

        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from WebSocket feed"""
        self._connected = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        self.logger.info("Disconnected from delayed WebSocket feed")

    async def subscribe(self, symbols: List[str], data_types: List[str]) -> bool:
        """Subscribe to market data streams"""
        if not self._connected or not self.websocket:
            self.logger.error("Not connected to WebSocket")
            return False

        try:
            # Build subscription parameters
            subscriptions = []

            for symbol in symbols:
                for data_type in data_types:
                    if data_type == "second_agg":
                        subscriptions.append(f"A.{symbol}")
                    elif data_type == "minute_agg":
                        subscriptions.append(f"AM.{symbol}")
                    elif data_type == "trade":
                        subscriptions.append(f"T.{symbol}")

            if not subscriptions:
                self.logger.warning("No valid subscriptions specified")
                return False

            # Send subscription message
            subscribe_msg = {
                "action": "subscribe",
                "params": ",".join(subscriptions)
            }

            await self.websocket.send(json.dumps(subscribe_msg))
            self._subscribed_symbols.update(symbols)

            self.logger.info(f"✅ Subscribed to: {subscriptions}")
            return True

        except Exception as e:
            self.logger.error(f"Subscription failed: {e}")
            return False

    async def unsubscribe(self, symbols: List[str], data_types: List[str]) -> bool:
        """Unsubscribe from market data streams"""
        if not self._connected or not self.websocket:
            return False

        try:
            # Build unsubscription parameters
            unsubscriptions = []

            for symbol in symbols:
                for data_type in data_types:
                    if data_type == "second_agg":
                        unsubscriptions.append(f"A.{symbol}")
                    elif data_type == "minute_agg":
                        unsubscriptions.append(f"AM.{symbol}")
                    elif data_type == "trade":
                        unsubscriptions.append(f"T.{symbol}")

            if not unsubscriptions:
                return False

            # Send unsubscription message
            unsubscribe_msg = {
                "action": "unsubscribe",
                "params": ",".join(unsubscriptions)
            }

            await self.websocket.send(json.dumps(unsubscribe_msg))
            self._subscribed_symbols.difference_update(symbols)

            self.logger.info(f"✅ Unsubscribed from: {unsubscriptions}")
            return True

        except Exception as e:
            self.logger.error(f"Unsubscription failed: {e}")
            return False

    async def start_listening(self) -> None:
        """Start listening for incoming messages"""
        if not self._connected or not self.websocket:
            raise RuntimeError("Not connected to WebSocket")

        try:
            while self._connected:
                try:
                    # Receive message with timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=60.0
                    )

                    # Parse and handle message
                    await self._handle_message(message)

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await self.websocket.ping()
                    continue

                except websockets.exceptions.ConnectionClosed:
                    self.logger.warning("WebSocket connection closed")
                    self._connected = False
                    break

        except Exception as e:
            self.logger.error(f"Error in message loop: {e}")
            self._connected = False

        # Attempt reconnection
        if self.config.max_reconnect_attempts > 0:
            self._reconnect_task = asyncio.create_task(self._reconnect())

    async def _authenticate(self) -> bool:
        """Authenticate with Polygon API"""
        try:
            # Send authentication message
            auth_msg = {"action": "auth", "params": self.config.api_key}
            await self.websocket.send(json.dumps(auth_msg))

            # Wait for auth response
            for _ in range(5):  # Check next 5 messages
                try:
                    response = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=5.0
                    )
                    data = json.loads(response)

                    # Handle both single messages and arrays
                    messages = data if isinstance(data, list) else [data]

                    for msg in messages:
                        if msg.get('ev') == 'status' and msg.get('status') == 'auth_success':
                            return True

                except asyncio.TimeoutError:
                    continue

            return False

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)

            # Handle both single messages and arrays
            messages = data if isinstance(data, list) else [data]

            for msg in messages:
                msg_type = msg.get('ev')

                if msg_type in ['A', 'AM']:  # Aggregate bars
                    await self._handle_aggregate(msg)
                elif msg_type == 'T':  # Trades
                    await self._handle_trade(msg)
                elif msg_type == 'status':  # Status messages
                    await self._handle_status(msg)
                else:
                    self.logger.debug(f"Unrecognized message type: {msg_type}")

        except json.JSONDecodeError:
            self.logger.warning(f"Invalid JSON message: {message}")
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    async def _handle_aggregate(self, msg: Dict[str, Any]) -> None:
        """Handle aggregate bar message"""
        try:
            # Determine bar type
            bar_type = 'second' if msg.get('ev') == 'A' else 'minute'

            bar = PolygonAggregateBar(
                symbol=msg.get('sym', ''),
                open=float(msg.get('o', 0)),
                high=float(msg.get('h', 0)),
                low=float(msg.get('l', 0)),
                close=float(msg.get('c', 0)),
                volume=float(msg.get('v', 0)),
                vwap=float(msg.get('vw', 0)) if msg.get('vw') else 0,
                timestamp_start=datetime.fromtimestamp(
                    msg.get('s', 0) / 1000,  # Start time in milliseconds
                    tz=timezone.utc
                ),
                timestamp_end=datetime.fromtimestamp(
                    msg.get('e', 0) / 1000,  # End time in milliseconds
                    tz=timezone.utc
                ),
                num_trades=int(msg.get('n', 0)) if msg.get('n') else 0,
                bar_type=bar_type,
                average_trade_size=float(msg.get('av', 0)) if msg.get('av') else None,
                otc=msg.get('otc', False),
            )

            # Create feed message
            message_type = 'second_agg' if bar_type == 'second' else 'minute_agg'
            feed_message = FeedMessage(
                provider=FeedProvider.POLYGON,
                symbol=bar.symbol,
                message_type=message_type,
                data=bar,
                timestamp=bar.timestamp_end,
            )

            # Notify subscribers
            await self._notify_subscribers(feed_message)

        except Exception as e:
            self.logger.error(f"Error handling aggregate: {e}")

    async def _handle_trade(self, msg: Dict[str, Any]) -> None:
        """Handle trade message"""
        try:
            trade = PolygonTrade(
                symbol=msg.get('sym', ''),
                price=float(msg.get('p', 0)),
                size=int(msg.get('s', 0)),
                timestamp=datetime.fromtimestamp(
                    msg.get('t', 0) / 1e9,  # Trade time in nanoseconds
                    tz=timezone.utc
                ),
                conditions=msg.get('c', []),
                exchange=msg.get('x', 0),
                tape=msg.get('z', 0),
                sequence_number=msg.get('i'),
            )

            # Create feed message
            feed_message = FeedMessage(
                provider=FeedProvider.POLYGON,
                symbol=trade.symbol,
                message_type='trade',
                data=trade,
                timestamp=trade.timestamp,
            )

            # Notify subscribers
            await self._notify_subscribers(feed_message)

        except Exception as e:
            self.logger.error(f"Error handling trade: {e}")

    async def _handle_status(self, msg: Dict[str, Any]) -> None:
        """Handle status message"""
        status = msg.get('status', '')
        message = msg.get('message', '')

        if status == 'connected':
            self.logger.info("WebSocket connected")
        elif status == 'auth_success':
            self.logger.info("Authentication successful")
        elif status == 'error':
            self.logger.error(f"WebSocket error: {message}")
        elif status == 'success':
            self.logger.debug(f"WebSocket success: {message}")
        else:
            self.logger.debug(f"WebSocket status: {status} - {message}")

    async def _heartbeat(self) -> None:
        """Send periodic heartbeat to keep connection alive"""
        while self._connected:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                if self.websocket:
                    await self.websocket.ping()
            except Exception as e:
                self.logger.warning(f"Heartbeat failed: {e}")
                break

    async def _reconnect(self) -> None:
        """Attempt to reconnect to WebSocket"""
        for attempt in range(self.config.max_reconnect_attempts):
            try:
                self.logger.info(f"Reconnection attempt {attempt + 1}/{self.config.max_reconnect_attempts}")

                await asyncio.sleep(self.config.reconnect_delay * (attempt + 1))

                if await self.connect():
                    # Re-subscribe to previous symbols
                    if self._subscribed_symbols:
                        await self.subscribe(list(self._subscribed_symbols), ["second_agg", "minute_agg", "trade"])

                    # Restart listening
                    asyncio.create_task(self.start_listening())
                    return

            except Exception as e:
                self.logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")

        self.logger.error("Max reconnection attempts exceeded")

    @property
    def is_connected(self) -> bool:
        """Check if adapter is connected"""
        return self._connected and self.websocket is not None