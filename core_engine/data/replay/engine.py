#!/usr/bin/env python3
"""
Historical Data Replay Engine
=============================

Streams historical market data from ClickHouse to simulate real-time data feeds.
Enables testing of live trading components without connecting to live market feeds.

Features:
    - Historical data streaming with configurable speed
    - Market hours simulation with extended hours support
    - Accurate timestamp-based timing (uses actual data gaps)
    - Event-driven data distribution
    - Integration with existing FeedMessage architecture
    - Speed controls (1x, 2x, 10x, etc.) and pause/resume
    - Timestamp preservation and timezone handling
    - Progress tracking with ETA

Author: StatArb_Gemini Core Engine
Version: 1.1.0
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
import pandas as pd

from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.data.feeds.adapters import FeedMessage, FeedProvider
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

class MarketSession(Enum):
    """Market trading session types"""
    PRE_MARKET = "pre_market"       # 4:00 AM - 9:30 AM ET
    REGULAR = "regular"              # 9:30 AM - 4:00 PM ET
    AFTER_HOURS = "after_hours"      # 4:00 PM - 8:00 PM ET
    CLOSED = "closed"                # 8:00 PM - 4:00 AM ET

@dataclass
class ReplayStatistics:
    """Statistics for replay session"""
    total_records: int = 0
    records_processed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_timestamp: Optional[datetime] = None
    first_data_timestamp: Optional[datetime] = None
    last_data_timestamp: Optional[datetime] = None
    speed_multiplier: float = 1.0
    market_hours_simulated: bool = True

    # Timing metrics
    elapsed_real_seconds: float = 0.0
    elapsed_simulated_seconds: float = 0.0
    estimated_remaining_seconds: float = 0.0

    @property
    def progress_percentage(self) -> float:
        """Calculate replay progress as a percentage"""
        if self.total_records == 0:
            return 0.0
        return (self.records_processed / self.total_records) * 100.0

    @property
    def records_per_second(self) -> float:
        """Calculate processing rate"""
        if self.elapsed_real_seconds == 0:
            return 0.0
        return self.records_processed / self.elapsed_real_seconds

class HistoricalDataReplayEngine:
    """
    Engine for replaying historical market data as real-time streams.

    Streams data from ClickHouse with proper timing to simulate live market feeds,
    enabling testing of live trading components without market risk.

    Key Features:
        - Uses actual timestamp gaps between data points for accurate timing
        - Supports pre-market, regular, and after-hours sessions
        - Provides progress tracking with ETA
        - Supports pause/resume and dynamic speed changes
    """

    # Extended market hours (pre-market to after-hours)
    PRE_MARKET_START = time(4, 0)    # 4:00 AM ET
    REGULAR_OPEN = time(9, 30)        # 9:30 AM ET
    REGULAR_CLOSE = time(16, 0)       # 4:00 PM ET
    AFTER_HOURS_END = time(20, 0)     # 8:00 PM ET

    def __init__(self, config: ReplayConfig):
        """
        Initialize the replay engine.

        Args:
            config: ReplayConfig with replay settings
        """
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
        self._replay_task: Optional[asyncio.Task] = None

        # Data buffer
        self._data_buffer: Dict[str, pd.DataFrame] = {}
        self._buffer_lock = asyncio.Lock()

        # Timing control - use actual data timestamps
        self._previous_data_timestamp: Optional[datetime] = None
        self._speed_multiplier = config.speed.value
        self._pause_start_time: Optional[datetime] = None
        self._total_pause_duration: float = 0.0

        logger.info(f"✅ HistoricalDataReplayEngine initialized for {len(config.symbols)} symbols")

    async def initialize(self) -> bool:
        """
        Initialize the replay engine.

        Initializes the ClickHouse data manager and pre-loads the initial data buffer.
        Must be called before start_replay().

        Returns:
            bool: True if initialization successful, False otherwise
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
        Start the data replay.

        Begins streaming historical data through registered message handlers.
        Must be called after initialize().

        Returns:
            bool: True if replay started successfully, False otherwise
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
            self._previous_data_timestamp = None  # Reset timing
            self._total_pause_duration = 0.0

            # Notify status handlers
            await self._notify_status_handlers()

            # Start replay task and track it
            self._replay_task = asyncio.create_task(self._replay_loop())

            logger.info(f"🚀 Started data replay at {self._speed_multiplier}x speed")
            logger.info(f"   Total records to process: {self.stats.total_records}")
            return True

        except Exception as e:
            self.status = ReplayStatus.ERROR
            logger.error(f"❌ Failed to start replay: {e}", exc_info=True)
            return False

    async def stop_replay(self) -> None:
        """Stop the data replay gracefully."""
        self.request_stop()
        self.stats.end_time = datetime.now()

        # Cancel replay task if running
        if self._replay_task and not self._replay_task.done():
            self._replay_task.cancel()
            try:
                await self._replay_task
            except asyncio.CancelledError:
                pass

        self.status = ReplayStatus.STOPPED
        self._update_elapsed_time()

        await self._notify_status_handlers()
        logger.info("🛑 Data replay stopped")

    def request_stop(self) -> None:
        """
        Synchronously request the replay loop to stop.
        Useful for INSTANT replay mode where the event loop may be blocked.
        """
        self._running = False
        logger.debug("Replay stop requested")

    async def pause_replay(self) -> None:
        """Pause the data replay."""
        if self.status == ReplayStatus.RUNNING:
            self._pause_event.clear()
            self._pause_start_time = datetime.now()
            self.status = ReplayStatus.PAUSED
            await self._notify_status_handlers()
            logger.info("⏸️ Data replay paused")

    async def resume_replay(self) -> None:
        """Resume the data replay."""
        if self.status == ReplayStatus.PAUSED:
            # Track pause duration
            if self._pause_start_time:
                pause_duration = (datetime.now() - self._pause_start_time).total_seconds()
                self._total_pause_duration += pause_duration
                self._pause_start_time = None

            self._pause_event.set()
            self.status = ReplayStatus.RUNNING
            await self._notify_status_handlers()
            logger.info("▶️ Data replay resumed")

    async def reset(self) -> None:
        """
        Reset the replay engine to initial state.

        Allows replaying from the beginning without re-initialization.
        """
        await self.stop_replay()

        # Reset statistics
        self.stats.records_processed = 0
        self.stats.start_time = None
        self.stats.end_time = None
        self.stats.current_timestamp = None
        self.stats.elapsed_real_seconds = 0.0
        self.stats.elapsed_simulated_seconds = 0.0
        self.stats.estimated_remaining_seconds = 0.0

        # Reset timing
        self._previous_data_timestamp = None
        self._total_pause_duration = 0.0

        self.status = ReplayStatus.STOPPED
        logger.info("🔄 Replay engine reset to initial state")

    def set_speed(self, speed: ReplaySpeed) -> None:
        """
        Set replay speed.

        Can be called during replay to dynamically change speed.

        Args:
            speed: New replay speed
        """
        old_speed = self._speed_multiplier
        self._speed_multiplier = speed.value
        self.stats.speed_multiplier = speed.value
        logger.info(f"⚡ Replay speed changed: {old_speed}x → {speed.value}x ({speed.name})")

    def add_message_handler(self, handler: Callable[[FeedMessage], None]) -> None:
        """Add a message handler for incoming data."""
        if handler not in self.message_handlers:
            self.message_handlers.append(handler)

    def remove_message_handler(self, handler: Callable[[FeedMessage], None]) -> bool:
        """
        Remove a message handler.

        Returns:
            bool: True if handler was removed, False if not found
        """
        try:
            self.message_handlers.remove(handler)
            return True
        except ValueError:
            return False

    def add_status_handler(self, handler: Callable[[ReplayStatus], None]) -> None:
        """Add a status change handler."""
        if handler not in self.status_handlers:
            self.status_handlers.append(handler)

    def remove_status_handler(self, handler: Callable[[ReplayStatus], None]) -> bool:
        """
        Remove a status handler.

        Returns:
            bool: True if handler was removed, False if not found
        """
        try:
            self.status_handlers.remove(handler)
            return True
        except ValueError:
            return False

    def get_statistics(self) -> ReplayStatistics:
        """Get current replay statistics with updated timing."""
        self._update_elapsed_time()
        return self.stats

    def get_market_session(self, timestamp: datetime) -> MarketSession:
        """
        Determine the market session for a given timestamp.

        Args:
            timestamp: Datetime to check

        Returns:
            MarketSession enum indicating the session type
        """
        ts_time = timestamp.time()

        if self.PRE_MARKET_START <= ts_time < self.REGULAR_OPEN:
            return MarketSession.PRE_MARKET
        elif self.REGULAR_OPEN <= ts_time < self.REGULAR_CLOSE:
            return MarketSession.REGULAR
        elif self.REGULAR_CLOSE <= ts_time < self.AFTER_HOURS_END:
            return MarketSession.AFTER_HOURS
        else:
            return MarketSession.CLOSED

    async def _preload_data_buffer(self) -> None:
        """Pre-load initial data into buffer."""
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

        # Calculate first and last data timestamps
        await self._calculate_timestamp_bounds()

        logger.info(f"✅ Pre-loaded {self.stats.total_records} total records")
        if self.stats.first_data_timestamp and self.stats.last_data_timestamp:
            logger.info(f"   Data range: {self.stats.first_data_timestamp} to {self.stats.last_data_timestamp}")

    async def _calculate_timestamp_bounds(self) -> None:
        """Calculate first and last timestamps in the data."""
        first_ts = None
        last_ts = None

        async with self._buffer_lock:
            for symbol_data in self._data_buffer.values():
                if 'timestamp' in symbol_data.columns and not symbol_data.empty:
                    timestamps = symbol_data['timestamp'].dropna()
                    if not timestamps.empty:
                        min_ts = timestamps.min()
                        max_ts = timestamps.max()

                        if first_ts is None or min_ts < first_ts:
                            first_ts = min_ts
                        if last_ts is None or max_ts > last_ts:
                            last_ts = max_ts

        # Convert numpy datetime64 to python datetime if needed
        if first_ts is not None:
            if hasattr(first_ts, 'to_pydatetime'):
                first_ts = first_ts.to_pydatetime()
            self.stats.first_data_timestamp = first_ts

        if last_ts is not None:
            if hasattr(last_ts, 'to_pydatetime'):
                last_ts = last_ts.to_pydatetime()
            self.stats.last_data_timestamp = last_ts

    async def _replay_loop(self) -> None:
        """
        Main replay loop.

        Iterates through all timestamps and processes data at the configured speed.
        Uses actual timestamp gaps for accurate timing simulation.
        """
        try:
            # Get all timestamps across all symbols
            all_timestamps = await self._get_all_timestamps()
            if not all_timestamps:
                logger.warning("No data available for replay")
                self.status = ReplayStatus.COMPLETED
                await self._notify_status_handlers()
                return

            total_timestamps = len(all_timestamps)
            logger.info(f"Starting replay of {total_timestamps} timestamps")

            # Calculate total simulated time span
            if len(all_timestamps) >= 2:
                total_simulated_span = (all_timestamps[-1] - all_timestamps[0]).total_seconds()
                logger.info(f"   Simulated time span: {total_simulated_span / 3600:.1f} hours")

            last_progress_log = 0

            for idx, timestamp in enumerate(all_timestamps):
                if not self._running:
                    logger.info("Replay stopped by user")
                    break

                # Wait for pause/resume
                await self._pause_event.wait()

                # Apply timing delay BEFORE processing (more accurate simulation)
                await self._apply_timing_delay(timestamp)

                # Process data for this timestamp
                await self._process_timestamp(timestamp)

                # Update elapsed simulated time
                if self._previous_data_timestamp is not None:
                    self.stats.elapsed_simulated_seconds += (
                        timestamp - self._previous_data_timestamp
                    ).total_seconds()
                self._previous_data_timestamp = timestamp

                # Log progress at 10% intervals
                progress = (idx + 1) / total_timestamps * 100
                if progress >= last_progress_log + 10:
                    last_progress_log = int(progress // 10) * 10
                    self._update_elapsed_time()
                    eta_str = self._format_eta()
                    logger.info(
                        f"📊 Progress: {progress:.0f}% "
                        f"({self.stats.records_processed}/{self.stats.total_records} records) "
                        f"| ETA: {eta_str}"
                    )

            if self._running:
                self.status = ReplayStatus.COMPLETED
                logger.info("✅ Replay completed successfully")
            else:
                self.status = ReplayStatus.STOPPED
                logger.info("🛑 Replay stopped before completion")

            self.stats.end_time = datetime.now()
            self._update_elapsed_time()

        except asyncio.CancelledError:
            logger.info("Replay task cancelled")
            raise

        except Exception as e:
            self.status = ReplayStatus.ERROR
            logger.error(f"❌ Error in replay loop: {e}", exc_info=True)

        finally:
            await self._notify_status_handlers()
            logger.info(
                f"Replay session ended: {self.stats.records_processed} records processed "
                f"in {self.stats.elapsed_real_seconds:.1f}s"
            )

    async def _get_all_timestamps(self) -> List[datetime]:
        """Get all unique timestamps across all symbols, sorted."""
        all_timestamps: Set[datetime] = set()

        async with self._buffer_lock:
            for symbol_data in self._data_buffer.values():
                if 'timestamp' in symbol_data.columns:
                    timestamps = symbol_data['timestamp'].dropna().unique()
                    for ts in timestamps:
                        # Convert numpy datetime64 to python datetime if needed
                        if hasattr(ts, 'to_pydatetime'):
                            ts = ts.to_pydatetime()
                        all_timestamps.add(ts)

        return sorted(list(all_timestamps))

    async def _process_timestamp(self, timestamp: datetime) -> None:
        """Process all data for a given timestamp."""
        messages: List[FeedMessage] = []

        async with self._buffer_lock:
            for symbol, data in self._data_buffer.items():
                # Filter data for this timestamp AND this symbol
                # The buffer might contain multiple symbols if the data manager returned a broad set
                timestamp_data = data[
                    (data['timestamp'] == timestamp) & 
                    (data['symbol'] == symbol)
                ]
                
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

    def _convert_to_feed_message(
        self,
        symbol: str,
        row: pd.Series,
        timestamp: datetime
    ) -> FeedMessage:
        """Convert DataFrame row to FeedMessage."""
        # Create market data dict with safe type conversion
        data = {
            'symbol': symbol,
            'timestamp': timestamp,
            'open': self._safe_float(row.get('open', 0)),
            'high': self._safe_float(row.get('high', 0)),
            'low': self._safe_float(row.get('low', 0)),
            'close': self._safe_float(row.get('close', 0)),
            'volume': self._safe_int(row.get('volume', 0)),
            'vwap': self._safe_float(row.get('vwap', row.get('close', 0))),
        }

        # Add additional fields if available
        if 'transactions' in row.index:
            data['transactions'] = self._safe_int(row.get('transactions', 0))

        return FeedMessage(
            provider=FeedProvider.SIMULATED,
            symbol=symbol,
            message_type='bar',
            timestamp=timestamp,
            data=data
        )

    @staticmethod
    def _safe_float(value: Any) -> float:
        """Safely convert value to float."""
        try:
            if pd.isna(value):
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _safe_int(value: Any) -> int:
        """Safely convert value to int."""
        try:
            if pd.isna(value):
                return 0
            return int(value)
        except (ValueError, TypeError):
            return 0

    async def _send_message(self, message: FeedMessage) -> None:
        """Send message to all registered handlers with error isolation."""
        for handler in self.message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.warning(f"Message handler error: {e}", exc_info=True)

    async def _apply_timing_delay(self, current_timestamp: datetime) -> None:
        """
        Apply timing delay based on actual timestamp gap and replay speed.

        Uses the actual time difference between consecutive data points
        instead of assuming a fixed interval, providing more accurate
        replay timing especially for irregular data (gaps, extended hours).
        """
        # Instant replay - no delay
        if self._speed_multiplier == float('inf') or self._speed_multiplier == 0:
            return

        # First timestamp - no delay
        if self._previous_data_timestamp is None:
            return

        # Calculate actual time gap between data points
        time_gap_seconds = (current_timestamp - self._previous_data_timestamp).total_seconds()

        # Skip if gap is negative or zero (shouldn't happen with sorted data)
        if time_gap_seconds <= 0:
            return

        # Check market session if simulating market hours
        if self.config.simulate_market_hours:
            current_session = self.get_market_session(current_timestamp)
            prev_session = self.get_market_session(self._previous_data_timestamp)

            # If transitioning from closed to open or vice versa,
            # use minimal delay instead of simulating overnight gap
            if current_session == MarketSession.CLOSED or prev_session == MarketSession.CLOSED:
                # Large gap (likely overnight) - use minimal delay
                if time_gap_seconds > 3600:  # More than 1 hour
                    time_gap_seconds = 1.0  # Use 1 second for session transitions

        # Apply speed multiplier
        delay_seconds = time_gap_seconds / self._speed_multiplier

        # Cap minimum delay to prevent overwhelming the system
        # Cap maximum delay to prevent extremely long waits
        delay_seconds = max(0.001, min(delay_seconds, 60.0))

        await asyncio.sleep(delay_seconds)

    def _update_elapsed_time(self) -> None:
        """Update elapsed real time in statistics."""
        if self.stats.start_time:
            total_elapsed = (datetime.now() - self.stats.start_time).total_seconds()
            self.stats.elapsed_real_seconds = total_elapsed - self._total_pause_duration

            # Estimate remaining time based on current rate
            if self.stats.records_processed > 0 and self.stats.total_records > 0:
                remaining_records = self.stats.total_records - self.stats.records_processed
                rate = self.stats.records_processed / max(self.stats.elapsed_real_seconds, 0.001)
                self.stats.estimated_remaining_seconds = remaining_records / max(rate, 0.001)

    def _format_eta(self) -> str:
        """Format estimated time remaining as a human-readable string."""
        eta_seconds = self.stats.estimated_remaining_seconds

        if eta_seconds <= 0:
            return "calculating..."
        elif eta_seconds < 60:
            return f"{eta_seconds:.0f}s"
        elif eta_seconds < 3600:
            return f"{eta_seconds / 60:.1f}m"
        else:
            return f"{eta_seconds / 3600:.1f}h"

    async def _notify_status_handlers(self) -> None:
        """Notify all status handlers with error isolation."""
        for handler in self.status_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(self.status)
                else:
                    handler(self.status)
            except Exception as e:
                logger.warning(f"Status handler error: {e}", exc_info=True)

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
    Convenience function to create and initialize a replay engine.

    Args:
        symbols: List of symbols to replay
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        speed: Replay speed

    Returns:
        Initialized replay engine

    Raises:
        RuntimeError: If initialization fails
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
