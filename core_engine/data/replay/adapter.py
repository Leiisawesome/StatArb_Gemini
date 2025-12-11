#!/usr/bin/env python3
"""
Historical Data Replay Feed Adapter
===================================

Adapter that integrates the HistoricalDataReplayEngine with the core_engine
feed adapter architecture. Allows live trading components to be tested using
historical data streams.

Features:
    - Implements DataFeedAdapter interface
    - Converts replay messages to standardized FeedMessage format
    - Supports subscription management
    - Provides connection lifecycle management
    - Integrates with existing event-driven processing

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from .engine import HistoricalDataReplayEngine, ReplayStatus
from .config import ReplayConfig, ReplaySpeed
from core_engine.data.feeds.adapters import (
    DataFeedAdapter,
    FeedAdapterConfig,
    FeedMessage,
    FeedProvider,
    AdapterStatus
)

logger = logging.getLogger(__name__)


class HistoricalReplayFeedAdapter(DataFeedAdapter):
    """
    Feed adapter for historical data replay

    Implements the DataFeedAdapter interface to provide historical data
    streams that simulate real-time market feeds for testing purposes.
    
    Uses centralized ReplayConfig for all configuration settings.
    """

    # Adapter metadata
    IS_IMPLEMENTED = True
    PROVIDER = FeedProvider.SIMULATED
    SUPPORTED_DATA_TYPES = ['bar', 'quote', 'trade']

    def __init__(self, config: ReplayConfig):
        """
        Initialize the replay feed adapter
        
        Args:
            config: ReplayConfig instance with all replay settings
        """
        # Create minimal FeedAdapterConfig for base class
        base_config = FeedAdapterConfig(
            name=config.adapter_name,
            provider=FeedProvider.SIMULATED
        )
        
        # Initialize base adapter
        super().__init__(base_config)

        # Store replay configuration
        self.replay_config = config
        self.replay_engine: Optional[HistoricalDataReplayEngine] = None

        # Adapter state
        self._replay_task: Optional[asyncio.Task] = None

        logger.info(f"✅ HistoricalReplayFeedAdapter initialized for {len(config.symbols)} symbols")

    async def connect(self) -> bool:
        """
        Connect to the replay feed

        Initializes the replay engine and sets up message handlers.

        Returns:
            bool: True if connection successful, False otherwise

        Raises:
            RuntimeError: If replay engine initialization fails
        """
        try:
            # Check if already connected
            if self.status == AdapterStatus.CONNECTED:
                logger.warning("Already connected to replay feed")
                return True

            self.status = AdapterStatus.CONNECTING
            logger.info("Connecting to historical replay feed...")

            # Create and initialize replay engine
            self.replay_engine = HistoricalDataReplayEngine(self.replay_config)
            success = await self.replay_engine.initialize()

            if not success:
                self.status = AdapterStatus.ERROR
                raise RuntimeError("Failed to initialize replay engine")

            # Set up message handling
            self.replay_engine.add_message_handler(self._handle_replay_message)
            self.replay_engine.add_status_handler(self._handle_replay_status)

            # Update connection statistics
            self._stats['connection_time'] = datetime.now().isoformat()

            self.status = AdapterStatus.CONNECTED
            logger.info("✅ Connected to historical replay feed")
            return True

        except Exception as e:
            self.status = AdapterStatus.ERROR
            logger.error(f"❌ Failed to connect to replay feed: {e}", exc_info=True)
            return False

    async def disconnect(self) -> None:
        """
        Disconnect from the replay feed
        
        Stops the replay engine and cleans up resources. Safe to call multiple times.
        """
        try:
            # Check if already disconnected
            if self.status == AdapterStatus.DISCONNECTED:
                logger.debug("Already disconnected from replay feed")
                return

            logger.info("Disconnecting from replay feed...")

            # Stop replay engine
            if self.replay_engine:
                await self.replay_engine.stop_replay()

            # Cancel replay task if running
            if self._replay_task and not self._replay_task.done():
                self._replay_task.cancel()
                try:
                    await self._replay_task
                except asyncio.CancelledError:
                    logger.debug("Replay task cancelled successfully")

            # Clear subscriptions
            self._subscriptions.clear()

            self.status = AdapterStatus.DISCONNECTED
            logger.info("✅ Disconnected from historical replay feed")

        except Exception as e:
            self.status = AdapterStatus.ERROR
            logger.error(f"❌ Error during disconnect: {e}", exc_info=True)

    async def subscribe(self, symbols: List[str], data_types: List[str]) -> bool:
        """
        Subscribe to market data

        For replay adapter, this validates the subscription request.
        Actual data streaming is controlled by the replay engine.

        Args:
            symbols: List of symbols to subscribe to
            data_types: List of data types ('bar', 'quote', 'trade', etc.)

        Returns:
            bool: True if subscription successful
        """
        try:
            self.status = AdapterStatus.SUBSCRIBING

            # Validate requested symbols are available
            available_symbols = set(self.replay_config.symbols)
            requested_symbols = set(symbols)

            if not requested_symbols.issubset(available_symbols):
                missing = requested_symbols - available_symbols
                logger.warning(f"Requested symbols not available in replay data: {missing}")

            # Validate data types
            invalid_types = set(data_types) - set(self.SUPPORTED_DATA_TYPES)
            if invalid_types:
                logger.warning(f"Unsupported data types requested: {invalid_types}")

            # Update subscriptions
            self._subscriptions.update(symbols)

            self.status = AdapterStatus.ACTIVE
            logger.info(f"✅ Subscribed to {len(symbols)} symbols for data types: {data_types}")
            return True

        except Exception as e:
            self.status = AdapterStatus.ERROR
            logger.error(f"❌ Subscription failed: {e}")
            return False

    async def start_replay(self) -> bool:
        """
        Start the data replay

        Returns:
            bool: True if replay started successfully
        """
        if not self.replay_engine:
            logger.error("Replay engine not initialized")
            return False

        try:
            success = await self.replay_engine.start_replay()
            if success:
                self.status = AdapterStatus.ACTIVE
            return success
        except Exception as e:
            self.status = AdapterStatus.ERROR
            logger.error(f"❌ Failed to start replay: {e}")
            return False

    async def stop_replay(self) -> None:
        """Stop the data replay"""
        if self.replay_engine:
            await self.replay_engine.stop_replay()
            self.status = AdapterStatus.CONNECTED

    async def pause_replay(self) -> None:
        """Pause the data replay"""
        if self.replay_engine:
            await self.replay_engine.pause_replay()

    async def resume_replay(self) -> None:
        """Resume the data replay"""
        if self.replay_engine:
            await self.replay_engine.resume_replay()

    def set_replay_speed(self, speed: ReplaySpeed) -> None:
        """Set replay speed"""
        if self.replay_engine:
            self.replay_engine.set_speed(speed)

    def get_replay_statistics(self) -> Dict[str, Any]:
        """Get replay statistics"""
        if not self.replay_engine:
            return {}

        stats = self.replay_engine.get_statistics()
        return {
            'total_records': stats.total_records,
            'records_processed': stats.records_processed,
            'start_time': stats.start_time.isoformat() if stats.start_time else None,
            'end_time': stats.end_time.isoformat() if stats.end_time else None,
            'current_timestamp': stats.current_timestamp.isoformat() if stats.current_timestamp else None,
            'speed_multiplier': stats.speed_multiplier,
            'market_hours_simulated': stats.market_hours_simulated,
            'progress_percentage': (stats.records_processed / stats.total_records * 100) if stats.total_records > 0 else 0
        }

    def _handle_replay_message(self, message: FeedMessage) -> None:
        """
        Handle incoming replay messages

        Converts replay messages to adapter format and forwards to subscribers.
        """
        try:
            # Update statistics
            self._stats['messages_received'] += 1

            # Forward to message handlers
            for handler in self._message_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        # Schedule coroutine handler
                        asyncio.create_task(handler(message))
                    else:
                        handler(message)
                except Exception as e:
                    logger.warning(f"Message handler error: {e}")

            self._stats['messages_processed'] += 1

        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"Error handling replay message: {e}")

    def _handle_replay_status(self, status: ReplayStatus) -> None:
        """Handle replay engine status changes"""
        try:
            # Map replay status to adapter status
            status_mapping = {
                ReplayStatus.STOPPED: AdapterStatus.CONNECTED,
                ReplayStatus.INITIALIZING: AdapterStatus.CONNECTING,
                ReplayStatus.RUNNING: AdapterStatus.ACTIVE,
                ReplayStatus.PAUSED: AdapterStatus.CONNECTED,  # Paused but still connected
                ReplayStatus.COMPLETED: AdapterStatus.CONNECTED,
                ReplayStatus.ERROR: AdapterStatus.ERROR,
            }

            new_status = status_mapping.get(status, AdapterStatus.ERROR)
            if new_status != self.status:
                self.status = new_status

                # Notify status handlers
                for handler in self._status_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(new_status))
                        else:
                            handler(new_status)
                    except Exception as e:
                        logger.warning(f"Status handler error: {e}")

            logger.debug(f"Replay status changed to: {status.value}")

        except Exception as e:
            logger.error(f"Error handling replay status change: {e}")

    async def unsubscribe(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from market data.

        Args:
            symbols: List of symbols to unsubscribe from

        Returns:
            bool: True if unsubscription successful
        """
        try:
            # Remove symbols from subscriptions
            for symbol in symbols:
                self._subscriptions.discard(symbol)

            self.logger.info(f"✅ Unsubscribed from {len(symbols)} symbols")
            return True

        except Exception as e:
            self.logger.error(f"❌ Unsubscription failed: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if adapter is connected."""
        return self.status in [AdapterStatus.CONNECTED, AdapterStatus.ACTIVE]

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        # Base health check
        health_status = {
            'healthy': self.status == AdapterStatus.ACTIVE,
            'status': self.status.value,
            'subscriptions': len(self._subscriptions),
            'messages_received': self._stats['messages_received'],
            'messages_processed': self._stats['messages_processed'],
            'errors': self._stats['errors'],
            'last_message_time': self._stats['last_message_time'],
            'connection_time': self._stats['connection_time'],
        }

        # Add replay-specific health checks
        if self.replay_engine:
            replay_stats = self.get_replay_statistics()
            health_status.update({
                'replay_engine_initialized': True,
                'replay_total_records': replay_stats.get('total_records', 0),
                'replay_records_processed': replay_stats.get('records_processed', 0),
                'replay_progress_percentage': replay_stats.get('progress_percentage', 0),
                'replay_current_speed': replay_stats.get('speed_multiplier', 1.0),
            })
        else:
            health_status.update({
                'replay_engine_initialized': False,
                'replay_error': 'Replay engine not initialized'
            })

        return health_status


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def create_replay_adapter(
    symbols: List[str],
    start_date: str,
    end_date: str,
    speed: ReplaySpeed = ReplaySpeed.REALTIME
) -> HistoricalReplayFeedAdapter:
    """
    Convenience function to create and connect a replay feed adapter

    Args:
        symbols: List of symbols to replay
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        speed: Replay speed

    Returns:
        Connected replay feed adapter
    """
    config = ReplayConfig.create_for_symbols(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        speed=speed
    )

    adapter = HistoricalReplayFeedAdapter(config)
    success = await adapter.connect()

    if not success:
        raise RuntimeError("Failed to connect replay adapter")

    return adapter