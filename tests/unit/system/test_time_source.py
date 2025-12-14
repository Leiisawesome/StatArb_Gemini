"""
Tests for time_source.py - Dual-clock time management system.

This module provides comprehensive test coverage for the TimeSource implementations,
ensuring proper separation of market time (for signals) and wall time (for operations),
thread safety, and replay functionality.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from threading import Thread

from core_engine.system.time_source import (
    TimeSource,
    LiveTimeSource,
    ReplayTimeSource,
    TimeSourceFactory,
)

class TestTimeSource:
    """Base tests for TimeSource interface."""

    def test_abstract_methods(self):
        """Test that TimeSource defines required abstract methods."""
        # This should raise TypeError since TimeSource is abstract
        with pytest.raises(TypeError):
            TimeSource()

class TestLiveTimeSource:
    """Tests for LiveTimeSource implementation."""

    def test_initialization(self):
        """Test LiveTimeSource initialization."""
        ts = LiveTimeSource()

        # Should initialize with current time
        market_now = ts.market_now()
        wall_now = ts.wall_now()

        assert isinstance(market_now, datetime)
        assert isinstance(wall_now, datetime)
        assert market_now.tzinfo == timezone.utc
        assert wall_now.tzinfo == timezone.utc

        # Market and wall time should be very close (within 1 second)
        diff = abs((market_now - wall_now).total_seconds())
        assert diff < 1.0

    def test_market_now_consistency(self):
        """Test that market_now() returns consistent times."""
        ts = LiveTimeSource()

        t1 = ts.market_now()
        time.sleep(0.01)  # Small delay
        t2 = ts.market_now()

        assert t2 >= t1
        diff = (t2 - t1).total_seconds()
        assert 0.01 <= diff < 0.1  # Should advance by at least the sleep time

    def test_wall_now_advances(self):
        """Test that wall_now() advances with real time."""
        ts = LiveTimeSource()

        t1 = ts.wall_now()
        time.sleep(0.01)
        t2 = ts.wall_now()

        assert t2 > t1
        diff = (t2 - t1).total_seconds()
        assert diff >= 0.01

    def test_market_time_never_goes_backwards(self):
        """Test that market time is monotonically increasing."""
        ts = LiveTimeSource()

        times = []
        for _ in range(10):
            times.append(ts.market_now())
            time.sleep(0.001)

        # All times should be in ascending order
        for i in range(1, len(times)):
            assert times[i] >= times[i-1]

    @patch('core_engine.system.time_source.monotonic')
    def test_timeout_calculation(self, mock_monotonic):
        """Test timeout calculation using monotonic clock."""
        ts = LiveTimeSource()

        # Mock monotonic time starting at 1000
        mock_monotonic.return_value = 1000.0

        # Store start time
        start_time = ts.wall_monotonic()

        # Advance monotonic time by 5 seconds
        mock_monotonic.return_value = 1005.0

        # Should have advanced by 5 seconds
        assert (ts.wall_monotonic() - start_time) == 5.0

    def test_thread_safety(self):
        """Test thread safety of LiveTimeSource."""
        ts = LiveTimeSource()

        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(100):
                    market_time = ts.market_now()
                    wall_time = ts.wall_now()
                    results.append((worker_id, i, market_time, wall_time))
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Run multiple threads
        threads = []
        for i in range(5):
            t = Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0

        # Should have collected results from all threads
        assert len(results) == 500  # 5 threads * 100 iterations

        # All times should be reasonable
        for worker_id, iteration, market_time, wall_time in results:
            assert isinstance(market_time, datetime)
            assert isinstance(wall_time, datetime)
            assert market_time.tzinfo == timezone.utc
            assert wall_time.tzinfo == timezone.utc

    def test_advance_market_time_noop(self):
        """Test that advance_market_time is a no-op in live mode."""
        ts = LiveTimeSource()
        initial_market = ts.market_now()

        # Advance market time (should be no-op in live mode)
        future_time = initial_market + timedelta(hours=1)
        ts.advance_market_time(future_time)

        # Market time should remain unchanged (driven by system clock)
        current_market = ts.market_now()
        time_diff = abs((current_market - initial_market).total_seconds())
        assert time_diff < 0.1  # Should be very close to initial time

class TestReplayTimeSource:
    """Tests for ReplayTimeSource implementation."""

    def test_initialization(self):
        """Test ReplayTimeSource initialization."""
        start_time = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        ts = ReplayTimeSource(start_time)

        assert ts.market_now() == start_time
        assert ts.wall_now() != start_time  # Wall time should be current

    def test_market_time_advancement(self):
        """Test manual market time advancement."""
        start_time = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        ts = ReplayTimeSource(start_time)

        # Initial time
        assert ts.market_now() == start_time

        # Advance by 1 minute
        advance_time = start_time + timedelta(minutes=1)
        ts.advance_market_time(advance_time)

        assert ts.market_now() == advance_time

        # Advance by 30 seconds more
        next_time = advance_time + timedelta(seconds=30)
        ts.advance_market_time(next_time)
        assert ts.market_now() == next_time

    def test_wall_time_independence(self):
        """Test that wall time is independent of market time."""
        start_time = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        ts = ReplayTimeSource(start_time)

        wall_before = ts.wall_now()
        time.sleep(0.01)  # Real time passes
        wall_after = ts.wall_now()

        # Wall time should advance
        assert wall_after > wall_before

        # Market time should remain the same
        assert ts.market_now() == start_time

        # Advance market time
        new_market_time = start_time + timedelta(hours=1)
        ts.advance_market_time(new_market_time)

        # Market time should be advanced
        assert ts.market_now() == new_market_time

        # Wall time should still be advancing
        wall_final = ts.wall_now()
        assert wall_final > wall_after

    def test_zero_advance(self):
        """Test advancing to the same time."""
        start_time = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        ts = ReplayTimeSource(start_time)

        original = ts.market_now()
        ts.advance_market_time(original)  # Advance to same time

        assert ts.market_now() == original

    def test_negative_advance(self):
        """Test that advancing backwards raises an error."""
        start_time = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        ts = ReplayTimeSource(start_time)

        earlier_time = start_time - timedelta(minutes=5)
        with pytest.raises(ValueError, match="Cannot move market time backwards"):
            ts.advance_market_time(earlier_time)

    def test_timeout_calculation_replay(self):
        """Test timeout calculation in replay mode."""
        start_time = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        ts = ReplayTimeSource(start_time)

        # In replay mode, monotonic time still works for timeouts
        start_mono = ts.wall_monotonic()
        time.sleep(0.01)
        end_mono = ts.wall_monotonic()

        assert end_mono > start_mono

    def test_thread_safety_replay(self):
        """Test thread safety of ReplayTimeSource."""
        start_time = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        ts = ReplayTimeSource(start_time)

        results = []
        errors = []

        def worker(worker_id):
            try:
                # Each thread works in its own time range to avoid conflicts
                base_offset = worker_id * 1000  # Thread 0: 0-1000ms, Thread 1: 1000-2000ms, etc.
                for i in range(100):
                    offset_ms = base_offset + i
                    new_time = start_time + timedelta(milliseconds=offset_ms)
                    ts.advance_market_time(new_time)

                    market_time = ts.market_now()
                    wall_time = ts.wall_now()
                    results.append((worker_id, i, market_time, wall_time))
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Run multiple threads
        threads = []
        for i in range(3):
            t = Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have no errors (thread safety via locks)
        assert len(errors) == 0

        # Should have collected results
        assert len(results) == 300  # 3 threads * 100 iterations

    def test_set_market_time(self):
        """Test setting market time to arbitrary values."""
        start_time = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        ts = ReplayTimeSource(start_time)

        # Set to a different time
        new_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        ts.set_market_time(new_time)

        assert ts.market_now() == new_time

        # Test timezone handling (naive datetime should be converted to UTC)
        naive_time = datetime(2024, 1, 1, 11, 0, 0)  # No timezone
        ts.set_market_time(naive_time)

        expected_utc = naive_time.replace(tzinfo=timezone.utc)
        assert ts.market_now() == expected_utc

    def test_get_lag_seconds(self):
        """Test calculating lag between market time and wall time."""
        # Use a fixed market time
        market_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        ts = ReplayTimeSource(market_time)

        # Mock wall_now to return a consistent time for testing
        with patch.object(ts, 'wall_now', return_value=datetime(2024, 1, 1, 10, 5, 0, tzinfo=timezone.utc)):
            lag = ts.get_lag_seconds()
            assert lag == 300.0  # 5 minutes = 300 seconds

        # Test when market time is ahead of wall time (negative lag)
        with patch.object(ts, 'wall_now', return_value=datetime(2024, 1, 1, 9, 55, 0, tzinfo=timezone.utc)):
            lag = ts.get_lag_seconds()
            assert lag == -300.0  # -5 minutes = -300 seconds

class TestTimeSourceFactory:
    """Tests for TimeSourceFactory."""

    def test_create_live(self):
        """Test creating live time source."""
        ts = TimeSourceFactory.create_live()

        assert isinstance(ts, LiveTimeSource)

    def test_create_replay(self):
        """Test creating replay time source."""
        start_time = datetime(2024, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        ts = TimeSourceFactory.create_replay(start_time)

        assert isinstance(ts, ReplayTimeSource)
        assert ts.market_now() == start_time

    def test_create_replay_missing_start_time(self):
        """Test creating replay time source without start time."""
        # create_replay accepts None as initial_time
        ts = TimeSourceFactory.create_replay(None)

        assert isinstance(ts, ReplayTimeSource)
        # Should initialize to current time or None
        market_time = ts.market_now()
        assert isinstance(market_time, datetime)

class TestTimeSourceIntegration:
    """Integration tests for time source behavior."""

    def test_time_source_switching(self):
        """Test switching between live and replay modes."""
        # Start with live
        live_ts = TimeSourceFactory.create_live()
        live_time = live_ts.market_now()

        # Switch to replay at the same time
        replay_ts = TimeSourceFactory.create_replay(live_time)

        # Times should match initially
        assert replay_ts.market_now() == live_time

        # Advance replay time
        new_replay_time = live_time + timedelta(hours=1)
        replay_ts.advance_market_time(new_replay_time)

        # Live time should have advanced naturally
        live_time_later = live_ts.market_now()
        assert live_time_later > live_time

        # Replay time should be advanced
        replay_time = replay_ts.market_now()
        assert replay_time == new_replay_time

    def test_replay_for_testing(self):
        """Test using replay mode for deterministic testing."""
        # Create replay source at known time
        test_start = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        ts = ReplayTimeSource(test_start)

        # Simulate a sequence of time advancements
        times = []
        times.append(ts.market_now())

        # Market open to close simulation
        current_time = test_start
        for minutes in [30, 60, 120, 180, 240, 300, 360]:  # Every hour
            current_time = test_start + timedelta(minutes=minutes)
            ts.advance_market_time(current_time)
            times.append(ts.market_now())

        # Should have 8 time points (initial + 7 advancements)
        assert len(times) == 8

        # First time should be start time
        assert times[0] == test_start

        # Last time should be 6 hours later (360 minutes)
        expected_end = test_start + timedelta(minutes=360)
        assert times[-1] == expected_end

        # All times should be monotonically increasing
        for i in range(1, len(times)):
            assert times[i] > times[i-1]

    @pytest.mark.parametrize("duration", [0.1, 1.0, 5.0])
    def test_timeout_precision(self, duration):
        """Test timeout precision with different durations."""
        ts = LiveTimeSource()

        start = ts.wall_monotonic()
        time.sleep(duration + 0.01)

        elapsed = ts.wall_monotonic() - start
        assert elapsed >= duration
