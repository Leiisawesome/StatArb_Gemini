#!/usr/bin/env python3
"""
Historical Data Replay Engine
=============================

Streams historical market data from ClickHouse to simulate real-time data feeds.
Enables testing of live trading components without connecting to live market feeds.

Features:
    - Historical data streaming with configurable speed
    - Market hours simulation (9:30 AM - 4:00 PM ET)
    - Event-driven data distribution
    - Integration with existing FeedMessage architecture
    - Speed controls (1x, 2x, 10x, etc.) and pause/resume
    - Timestamp preservation and timezone handling

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from enum import Enum
import pandas as pd

from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.data.feeds.adapters import FeedMessage, FeedProvider
from core_engine.type_definitions.data import MarketData
from .config import ReplayConfig, ReplaySpeed

logger = logging.getLogger(__name__)


class ReplayStatus(Enum):
    """Replay engine status"""
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ReplayStatistics:
    """Statistics for replay session"""
    total_records: int = 0
    records_processed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_timestamp: Optional[datetime] = None
    speed_multiplier: float = 1.0
    market_hours_simulated: bool = True


class HistoricalDataReplayEngine:
    """
    Engine for replaying historical market data as real-time streams.

    Streams data from ClickHouse with proper timing to simulate live market feeds,
    enabling testing of live trading components without market risk.
    """

    def __init__(self, config: ReplayConfig):
        self.config = config
        self.status = ReplayStatus.STOPPED
        self.stats = ReplayStatistics()

        # Data source
        self.data_manager: Optional[ClickHouseDataManager] = None

        # Event handling
        self.message_handlers: List[Callable[[FeedMessage], None]] = []
        self.status_handlers: List[Callable[[ReplayStatus], None]] = []

        # Control
        self._running = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused

        # Data buffer
        self._data_buffer: Dict[str, pd.DataFrame] = {}
        self._buffer_lock = asyncio.Lock()

        # Timing control
        self._last_replay_time: Optional[datetime] = None
        self._speed_multiplier = config.speed.value

        logger.info(f"✅ HistoricalDataReplayEngine initialized for {len(config.symbols)} symbols")

    async def initialize(self) -> bool:
        """
        Initialize the replay engine

        Initializes the ClickHouse data manager and pre-loads the initial data buffer.
        Must be called before start_replay().

        Returns:
            bool: True if initialization successful, False otherwise

        Raises:
            RuntimeError: If ClickHouse initialization fails
        """
        try:
            self.status = ReplayStatus.INITIALIZING
            logger.info("Initializing Historical Data Replay Engine...")

            # Validate engine not already initialized
            if self.data_manager is not None:
                logger.warning("Engine already initialized")
                return True

            # Initialize ClickHouse data manager
            ch_config = ClickHouseDataConfig(
                symbols=self.config.symbols,
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                interval=self.config.interval
            )

            self.data_manager = ClickHouseDataManager(ch_config)
            success = await self.data_manager.initialize()

            if not success:
                self.status = ReplayStatus.ERROR
                raise RuntimeError("Failed to initialize ClickHouse data manager")

            # Pre-load initial data buffer
            await self._preload_data_buffer()

            # Validate data was loaded
            if self.stats.total_records == 0:
                logger.warning("No data loaded - check symbols and date range")

            # Update statistics
            self.stats.market_hours_simulated = self.config.simulate_market_hours
            self.stats.speed_multiplier = self._speed_multiplier

            self.status = ReplayStatus.STOPPED
            logger.info("✅ Historical Data Replay Engine initialized successfully")
            return True

        except Exception as e:
            self.status = ReplayStatus.ERROR
            logger.error(f"❌ Failed to initialize replay engine: {e}", exc_info=True)
            return False

    async def start_replay(self) -> bool:
        """
        Start the data replay

        Begins streaming historical data through registered message handlers.
        Must be called after initialize().

        Returns:
            bool: True if replay started successfully, False otherwise

        Raises:
            RuntimeError: If engine not initialized or already running
        """
        if self.status == ReplayStatus.RUNNING:
            logger.warning("Replay already running")
            return True

        if not self.data_manager:
            logger.error("Engine not initialized - call initialize() first")
            return False

        if self.stats.total_records == 0:
            logger.warning("No data available for replay - check configuration")
            return False

        try:
            self.status = ReplayStatus.RUNNING
            self._running = True
            self.stats.start_time = datetime.now()
            self.stats.records_processed = 0  # Reset progress

            # Notify status handlers
            await self._notify_status_handlers()

            # Start replay task
            asyncio.create_task(self._replay_loop())

            logger.info(f"🚀 Started data replay at {self._speed_multiplier}x speed")
            logger.info(f"   Total records to process: {self.stats.total_records}")
            return True

        except Exception as e:
            self.status = ReplayStatus.ERROR
            logger.error(f"❌ Failed to start replay: {e}", exc_info=True)
            return False

    async def stop_replay(self) -> None:
        """Stop the data replay"""
        self._running = False
        self.status = ReplayStatus.STOPPED
        self.stats.end_time = datetime.now()

        await self._notify_status_handlers()
        logger.info("🛑 Data replay stopped")

    async def pause_replay(self) -> None:
        """Pause the data replay"""
        if self.status == ReplayStatus.RUNNING:
            self._pause_event.clear()
            self.status = ReplayStatus.PAUSED
            await self._notify_status_handlers()
            logger.info("⏸️ Data replay paused")

    async def resume_replay(self) -> None:
        """Resume the data replay"""
        if self.status == ReplayStatus.PAUSED:
            self._pause_event.set()
            self.status = ReplayStatus.RUNNING
            await self._notify_status_handlers()
            logger.info("▶️ Data replay resumed")

    def set_speed(self, speed: ReplaySpeed) -> None:
        """Set replay speed"""
        self._speed_multiplier = speed.value
        self.stats.speed_multiplier = speed.value
        logger.info(f"⚡ Replay speed set to {speed.name} ({speed.value}x)")

    def add_message_handler(self, handler: Callable[[FeedMessage], None]) -> None:
        """Add a message handler for incoming data"""
        self.message_handlers.append(handler)

    def add_status_handler(self, handler: Callable[[ReplayStatus], None]) -> None:
        """Add a status change handler"""
        self.status_handlers.append(handler)

    def get_statistics(self) -> ReplayStatistics:
        """Get current replay statistics"""
        return self.stats

    async def _preload_data_buffer(self) -> None:
        """Pre-load initial data into buffer"""
        logger.info("Pre-loading data buffer...")

        for symbol in self.config.symbols:
            try:
                # Load initial batch of data
                data = self.data_manager.load_market_data(
                    symbols=[symbol],
                    interval=self.config.interval
                )

                if not data.empty:
                    async with self._buffer_lock:
                        self._data_buffer[symbol] = data
                        self.stats.total_records += len(data)

                    logger.debug(f"Loaded {len(data)} records for {symbol}")

            except Exception as e:
                logger.warning(f"Failed to load data for {symbol}: {e}")

        logger.info(f"✅ Pre-loaded {self.stats.total_records} total records")

    async def _replay_loop(self) -> None:
        """
        Main replay loop
        
        Iterates through all timestamps and processes data at the configured speed.
        Handles pause/resume and graceful shutdown.
        """
        try:
            # Get all timestamps across all symbols
            all_timestamps = await self._get_all_timestamps()
            if not all_timestamps:
                logger.warning("No data available for replay")
                self.status = ReplayStatus.COMPLETED
                await self._notify_status_handlers()
                return

            # Sort timestamps
            all_timestamps.sort()

            logger.info(f"Starting replay of {len(all_timestamps)} timestamps")

            for idx, timestamp in enumerate(all_timestamps):
                if not self._running:
                    logger.info("Replay stopped by user")
                    break

                # Wait for pause/resume
                await self._pause_event.wait()

                # Process data for this timestamp
                await self._process_timestamp(timestamp)

                # Calculate delay based on speed
                await self._apply_timing_delay(timestamp)

                # Log progress periodically
                if (idx + 1) % 100 == 0:
                    progress = (idx + 1) / len(all_timestamps) * 100
                    logger.debug(f"Replay progress: {progress:.1f}% ({idx + 1}/{len(all_timestamps)} timestamps)")

            if self._running:
                self.status = ReplayStatus.COMPLETED
                logger.info("✅ Replay completed successfully")
            else:
                self.status = ReplayStatus.STOPPED
                logger.info("🛑 Replay stopped before completion")
                
            self.stats.end_time = datetime.now()

        except Exception as e:
            self.status = ReplayStatus.ERROR
            logger.error(f"❌ Error in replay loop: {e}", exc_info=True)

        finally:
            await self._notify_status_handlers()
            logger.info(f"Replay session ended: {self.stats.records_processed} records processed")

    async def _get_all_timestamps(self) -> List[datetime]:
        """Get all unique timestamps across all symbols"""
        all_timestamps = set()

        async with self._buffer_lock:
            for symbol_data in self._data_buffer.values():
                if 'timestamp' in symbol_data.columns:
                    timestamps = symbol_data['timestamp'].dropna().unique()
                    all_timestamps.update(timestamps)

        return sorted(list(all_timestamps))

    async def _process_timestamp(self, timestamp: datetime) -> None:
        """Process all data for a given timestamp"""
        # Find data for this timestamp across all symbols
        messages = []

        async with self._buffer_lock:
            for symbol, data in self._data_buffer.items():
                # Filter data for this timestamp
                timestamp_data = data[data['timestamp'] == timestamp]
                if not timestamp_data.empty:
                    # Convert to FeedMessage format
                    for _, row in timestamp_data.iterrows():
                        message = self._convert_to_feed_message(symbol, row, timestamp)
                        messages.append(message)

        # Send messages to handlers
        for message in messages:
            await self._send_message(message)

        self.stats.records_processed += len(messages)
        self.stats.current_timestamp = timestamp

    def _convert_to_feed_message(self, symbol: str, row: pd.Series, timestamp: datetime) -> FeedMessage:
        """Convert DataFrame row to FeedMessage"""
        # Create market data dict
        data = {
            'symbol': symbol,
            'timestamp': timestamp,
            'open': float(row.get('open', 0)),
            'high': float(row.get('high', 0)),
            'low': float(row.get('low', 0)),
            'close': float(row.get('close', 0)),
            'volume': int(row.get('volume', 0)),
            'vwap': float(row.get('vwap', row.get('close', 0))),
        }

        # Add additional fields if available
        if 'transactions' in row:
            data['transactions'] = int(row.get('transactions', 0))

        return FeedMessage(
            provider=FeedProvider.SIMULATED,
            symbol=symbol,
            message_type='bar',
            timestamp=timestamp,
            data=data
        )

    async def _send_message(self, message: FeedMessage) -> None:
        """Send message to all registered handlers"""
        for handler in self.message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.warning(f"Message handler error: {e}")

    async def _apply_timing_delay(self, timestamp: datetime) -> None:
        """Apply timing delay based on replay speed"""
        if self._speed_multiplier == float('inf'):
            # Instant replay - no delay
            return

        if self._last_replay_time is None:
            self._last_replay_time = datetime.now()
            return

        # Calculate real time difference
        if self.config.simulate_market_hours:
            # Only simulate during market hours
            if not self._is_market_hours(timestamp):
                return

        # Calculate time difference between data points
        # For 1min data, difference should be 60 seconds
        interval_seconds = self._get_interval_seconds()

        # Apply speed multiplier
        delay_seconds = interval_seconds / self._speed_multiplier

        # Cap minimum delay to prevent overwhelming the system
        delay_seconds = max(delay_seconds, 0.001)  # Minimum 1ms delay

        await asyncio.sleep(delay_seconds)
        self._last_replay_time = datetime.now()

    def _is_market_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is during market hours"""
        if not self.config.simulate_market_hours:
            return True

        # Convert to time
        ts_time = timestamp.time()

        # Check if within market hours (9:30 AM - 4:00 PM ET)
        return self.config.start_time <= ts_time <= self.config.end_time

    def _get_interval_seconds(self) -> float:
        """Get interval in seconds"""
        interval_map = {
            '1min': 60,
            '5min': 300,
            '15min': 900,
            '30min': 1800,
            '1h': 3600,
            '4h': 14400,
            '1D': 86400,
        }
        return interval_map.get(self.config.interval, 60)

    async def _notify_status_handlers(self) -> None:
        """Notify all status handlers"""
        for handler in self.status_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(self.status)
                else:
                    handler(self.status)
            except Exception as e:
                logger.warning(f"Status handler error: {e}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def create_replay_engine(
    symbols: List[str],
    start_date: str,
    end_date: str,
    speed: ReplaySpeed = ReplaySpeed.REALTIME
) -> HistoricalDataReplayEngine:
    """
    Convenience function to create and initialize a replay engine

    Args:
        symbols: List of symbols to replay
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        speed: Replay speed

    Returns:
        Initialized replay engine
    """
    config = ReplayConfig(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        speed=speed
    )

    engine = HistoricalDataReplayEngine(config)
    success = await engine.initialize()

    if not success:
        raise RuntimeError("Failed to initialize replay engine")

    return engine