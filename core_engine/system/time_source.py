"""
TimeSource - Dual Clock Implementation for Paper Trading
=========================================================

Provides a unified time abstraction with two clocks:
- Market time: Event time from replay/live feed (for signal logic)
- Wall time: Real system time (for operational controls like watchdogs, timeouts)

Usage Rules (from plan Section 2.1):
- Signal age, bar alignment, regime evaluation → market_now()
- Watchdog, IO timeouts, rate limiting, SLAs → wall_monotonic()

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 1)
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from time import monotonic
from typing import Optional
import threading

class TimeSource(ABC):
    """
    Abstract base class for time sources.

    Provides dual-clock semantics:
    - market_now(): Current event/replay timestamp
    - wall_now(): Real system time
    - wall_monotonic(): Monotonic clock for timeouts (never goes backwards)
    """

    @abstractmethod
    def market_now(self) -> datetime:
        """
        Get current market/event time.

        For replay: returns the timestamp of the current event being processed.
        For live: returns the timestamp from the feed.

        Returns:
            datetime: Current market time (timezone-aware, UTC)
        """

    @abstractmethod
    def wall_now(self) -> datetime:
        """
        Get current wall-clock (system) time.

        Always returns real system time regardless of mode.

        Returns:
            datetime: Current wall time (timezone-aware, UTC)
        """

    @abstractmethod
    def wall_monotonic(self) -> float:
        """
        Get monotonic time for duration measurements.

        Never goes backwards (immune to clock adjustments).
        Use for: timeouts, rate limiting, SLA tracking.

        Returns:
            float: Seconds since arbitrary epoch (use only for deltas)
        """

    @abstractmethod
    def advance_market_time(self, timestamp: datetime) -> None:
        """
        Advance market time to a new timestamp.

        Called by the event dispatcher when processing new events.

        Args:
            timestamp: New market timestamp (must be >= current)
        """

class LiveTimeSource(TimeSource):
    """
    Time source for live trading.

    Market time equals wall time (real-time feed).
    """

    def market_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def wall_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def wall_monotonic(self) -> float:
        return monotonic()

    def advance_market_time(self, timestamp: datetime) -> None:
        # In live mode, market time is driven by system clock, not events
        pass

class ReplayTimeSource(TimeSource):
    """
    Time source for replay/paper trading.

    Market time is controlled by the event dispatcher.
    Wall time remains real system time.

    Thread-safe: market time can be read from any thread.
    """

    def __init__(self, initial_time: Optional[datetime] = None):
        """
        Initialize replay time source.

        Args:
            initial_time: Starting market time. If None, uses current wall time.
        """
        self._market_time: datetime = initial_time or datetime.now(timezone.utc)
        self._lock = threading.Lock()

    def market_now(self) -> datetime:
        with self._lock:
            return self._market_time

    def wall_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def wall_monotonic(self) -> float:
        return monotonic()

    def advance_market_time(self, timestamp: datetime) -> None:
        """
        Advance market time to new timestamp.

        Args:
            timestamp: New market timestamp

        Raises:
            ValueError: If timestamp is before current market time
        """
        # Ensure timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        with self._lock:
            if timestamp < self._market_time:
                raise ValueError(
                    f"Cannot move market time backwards: "
                    f"{timestamp} < {self._market_time}"
                )
            self._market_time = timestamp

    def set_market_time(self, timestamp: datetime) -> None:
        """
        Set market time to an arbitrary value (for initialization/recovery).

        Unlike advance_market_time, allows setting to any time.
        Use only during initialization or recovery.

        Args:
            timestamp: New market timestamp
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        with self._lock:
            self._market_time = timestamp

    def get_lag_seconds(self) -> float:
        """
        Get the lag between market time and wall time.

        Useful for monitoring replay progress.

        Returns:
            float: Seconds that market time is behind wall time
                   (negative if market time is in the future)
        """
        with self._lock:
            delta = self.wall_now() - self._market_time
            return delta.total_seconds()

class TimeSourceFactory:
    """Factory for creating appropriate time sources."""

    @staticmethod
    def create_live() -> LiveTimeSource:
        """Create a live time source."""
        return LiveTimeSource()

    @staticmethod
    def create_replay(initial_time: Optional[datetime] = None) -> ReplayTimeSource:
        """
        Create a replay time source.

        Args:
            initial_time: Starting market time
        """
        return ReplayTimeSource(initial_time)

