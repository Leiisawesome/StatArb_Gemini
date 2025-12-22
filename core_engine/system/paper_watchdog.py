"""
PaperTradingWatchdog - Stall Detection and Recovery
===================================================

Monitors paper trading for stalls and triggers recovery.

Monitors (using wall/monotonic time, from plan Section 7.4):
- Time since last processed bar
- Processing rate (bars/second)
- Queue depth

Actions:
- Warning at 50% of max stall threshold
- Save checkpoint at 80%
- Trigger recovery at 100%

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 5)
"""

import asyncio
import logging
import threading
from dataclasses import dataclass
from enum import Enum, auto
from time import monotonic
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

class WatchdogAlertLevel(Enum):
    """Alert levels for watchdog conditions."""
    NORMAL = auto()    # All good
    WARNING = auto()   # 50% threshold
    CRITICAL = auto()  # 80% threshold
    STALLED = auto()   # 100% threshold

@dataclass
class WatchdogStatus:
    """Current watchdog status."""
    alert_level: WatchdogAlertLevel
    last_bar_time: Optional[float]  # Monotonic time
    time_since_last_bar: float
    stall_threshold: float
    processing_rate: float  # Bars per second
    queue_depth: int
    message: str

class PaperTradingWatchdog:
    """
    Monitors paper trading for stalls and triggers recovery.

    Uses wall/monotonic time (not market time) for operational monitoring.

    Features:
    - Stall detection based on wall-clock time
    - Processing rate monitoring
    - Queue depth tracking
    - Configurable thresholds and callbacks

    Thread-safe for concurrent updates.
    """

    def __init__(
        self,
        stall_threshold_seconds: float = 60.0,
        warning_pct: float = 0.50,
        critical_pct: float = 0.80,
        min_processing_rate: float = 0.1,  # Min bars/second before warning
        max_queue_depth: int = 1000,
        check_interval_seconds: float = 5.0,
    ):
        """
        Initialize watchdog.

        Args:
            stall_threshold_seconds: Max seconds without bar before stall
            warning_pct: Percentage of threshold for warning
            critical_pct: Percentage of threshold for critical
            min_processing_rate: Minimum bars/second before concern
            max_queue_depth: Max queue depth before concern
            check_interval_seconds: How often to run checks
        """
        self._stall_threshold = stall_threshold_seconds
        self._warning_pct = warning_pct
        self._critical_pct = critical_pct
        self._min_rate = min_processing_rate
        self._max_queue = max_queue_depth
        self._check_interval = check_interval_seconds

        # Timing tracking (monotonic time)
        self._last_bar_time: Optional[float] = None
        self._started_at: Optional[float] = None

        # Processing stats
        self._bars_processed = 0
        self._last_rate_check_time: Optional[float] = None
        self._last_rate_check_bars: int = 0
        self._current_rate: float = 0.0

        # Queue depth (set externally)
        self._queue_depth = 0

        # Current alert level
        self._alert_level = WatchdogAlertLevel.NORMAL

        # Callbacks
        self._on_warning: Optional[Callable[[], None]] = None
        self._on_critical: Optional[Callable[[], None]] = None
        self._on_stall: Optional[Callable[[], None]] = None

        # Running state
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Thread safety
        self._lock = threading.Lock()

        # Stats
        self._stats = {
            'warnings_issued': 0,
            'critical_alerts': 0,
            'stalls_detected': 0,
            'recoveries': 0,
        }

    def set_callbacks(
        self,
        on_warning: Optional[Callable[[], None]] = None,
        on_critical: Optional[Callable[[], None]] = None,
        on_stall: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Set callback functions for alert levels.

        Args:
            on_warning: Called when warning threshold reached
            on_critical: Called when critical threshold reached (should checkpoint)
            on_stall: Called when stall threshold reached (should trigger recovery)
        """
        self._on_warning = on_warning
        self._on_critical = on_critical
        self._on_stall = on_stall

    def start(self) -> None:
        """Start the watchdog."""
        with self._lock:
            self._running = True
            self._started_at = monotonic()
            self._last_bar_time = monotonic()
            self._last_rate_check_time = monotonic()

        logger.info("🐕 PaperTradingWatchdog started")

    def stop(self) -> None:
        """Stop the watchdog."""
        with self._lock:
            self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()

        logger.info("🐕 PaperTradingWatchdog stopped")

    def on_bar_processed(self) -> None:
        """Called when a bar is processed. Updates timing."""
        with self._lock:
            self._last_bar_time = monotonic()
            self._bars_processed += 1

            # Reset alert level on activity
            if self._alert_level != WatchdogAlertLevel.NORMAL:
                self._alert_level = WatchdogAlertLevel.NORMAL
                self._stats['recoveries'] += 1
                logger.info("🐕 Watchdog: Activity resumed, alert cleared")

    def on_heartbeat(self) -> None:
        """
        Called to indicate activity without incrementing bar count.
        Resets the stall timer.
        """
        with self._lock:
            self._last_bar_time = monotonic()

            # Reset alert level on activity
            if self._alert_level != WatchdogAlertLevel.NORMAL:
                self._alert_level = WatchdogAlertLevel.NORMAL
                self._stats['recoveries'] += 1
                logger.info("🐕 Watchdog: Activity resumed (heartbeat), alert cleared")

    def update_queue_depth(self, depth: int) -> None:
        """Update current queue depth."""
        with self._lock:
            self._queue_depth = depth

    def get_status(self) -> WatchdogStatus:
        """Get current watchdog status."""
        with self._lock:
            now = monotonic()

            if self._last_bar_time is None:
                time_since = 0.0
            else:
                time_since = now - self._last_bar_time

            # Calculate processing rate
            rate = self._calculate_rate()

            # Determine alert level
            if time_since >= self._stall_threshold:
                level = WatchdogAlertLevel.STALLED
                message = f"STALLED: No bar for {time_since:.1f}s (threshold: {self._stall_threshold:.1f}s)"
            elif time_since >= self._stall_threshold * self._critical_pct:
                level = WatchdogAlertLevel.CRITICAL
                message = f"CRITICAL: No bar for {time_since:.1f}s"
            elif time_since >= self._stall_threshold * self._warning_pct:
                level = WatchdogAlertLevel.WARNING
                message = f"WARNING: No bar for {time_since:.1f}s"
            else:
                level = WatchdogAlertLevel.NORMAL
                message = f"Normal: Last bar {time_since:.1f}s ago, rate {rate:.2f}/s"

            return WatchdogStatus(
                alert_level=level,
                last_bar_time=self._last_bar_time,
                time_since_last_bar=time_since,
                stall_threshold=self._stall_threshold,
                processing_rate=rate,
                queue_depth=self._queue_depth,
                message=message,
            )

    def _calculate_rate(self) -> float:
        """Calculate current processing rate."""
        now = monotonic()

        if self._last_rate_check_time is None:
            self._last_rate_check_time = now
            self._last_rate_check_bars = self._bars_processed
            return 0.0

        elapsed = now - self._last_rate_check_time
        if elapsed < 1.0:  # Don't recalculate too frequently
            return self._current_rate

        bars_delta = self._bars_processed - self._last_rate_check_bars
        self._current_rate = bars_delta / elapsed if elapsed > 0 else 0.0

        self._last_rate_check_time = now
        self._last_rate_check_bars = self._bars_processed

        return self._current_rate

    def check(self) -> WatchdogStatus:
        """
        Run a watchdog check and trigger callbacks if needed.

        Returns:
            Current WatchdogStatus
        """
        status = self.get_status()

        with self._lock:
            old_level = self._alert_level
            new_level = status.alert_level

            # Transition handling
            if new_level != old_level:
                self._alert_level = new_level

                if new_level == WatchdogAlertLevel.WARNING:
                    self._stats['warnings_issued'] += 1
                    logger.warning(f"🐕 {status.message}")
                    if self._on_warning:
                        try:
                            self._on_warning()
                        except Exception as e:
                            logger.error(f"Warning callback error: {e}")

                elif new_level == WatchdogAlertLevel.CRITICAL:
                    self._stats['critical_alerts'] += 1
                    logger.error(f"🐕 {status.message}")
                    if self._on_critical:
                        try:
                            self._on_critical()
                        except Exception as e:
                            logger.error(f"Critical callback error: {e}")

                elif new_level == WatchdogAlertLevel.STALLED:
                    self._stats['stalls_detected'] += 1
                    logger.critical(f"🐕 {status.message}")
                    if self._on_stall:
                        try:
                            self._on_stall()
                        except Exception as e:
                            logger.error(f"Stall callback error: {e}")

        return status

    async def run_monitor_loop(self) -> None:
        """
        Run the monitoring loop (async).

        Call this in an asyncio task for continuous monitoring.
        """
        logger.info(f"🐕 Watchdog monitor loop started (interval: {self._check_interval}s)")

        while self._running:
            try:
                self.check()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watchdog monitor error: {e}")
                await asyncio.sleep(self._check_interval)

        logger.info("🐕 Watchdog monitor loop stopped")

    def start_async_monitor(self) -> asyncio.Task:
        """
        Start the async monitor loop.

        Returns:
            The monitor task
        """
        self.start()
        self._monitor_task = asyncio.create_task(self.run_monitor_loop())
        return self._monitor_task

    def get_stats(self) -> Dict[str, Any]:
        """Get watchdog statistics."""
        status = self.get_status()
        return {
            **self._stats,
            'current_level': status.alert_level.name,
            'processing_rate': status.processing_rate,
            'queue_depth': status.queue_depth,
            'bars_processed': self._bars_processed,
            'running': self._running,
        }

    def reset(self) -> None:
        """Reset watchdog state."""
        with self._lock:
            self._last_bar_time = monotonic()
            self._bars_processed = 0
            self._last_rate_check_time = monotonic()
            self._last_rate_check_bars = 0
            self._current_rate = 0.0
            self._queue_depth = 0
            self._alert_level = WatchdogAlertLevel.NORMAL

