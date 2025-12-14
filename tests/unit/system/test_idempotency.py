"""
Tests for idempotency.py - Exactly-once processing guarantees.

This module provides comprehensive test coverage for the IdGenerator and IdempotencyTracker
implementations, ensuring deterministic ID generation and duplicate processing prevention.
"""

from datetime import datetime, timezone
from unittest.mock import patch
from threading import Thread

from core_engine.system.idempotency import (
    IdGenerator,
    IdempotencyTracker,
    generate_session_id,
)

def process_event(event_id):
    """Mock event processing function."""
    # In real code, this would do actual processing

class TestIdGenerator:
    """Tests for IdGenerator class."""

    def test_initialization(self):
        """Test IdGenerator initialization."""
        gen = IdGenerator("test_component", "test_session")

        assert gen.component == "test_component"
        assert gen.session_id == "test_session"
        assert gen._seq == 0

    def test_generate_signal_id(self):
        """Test signal ID generation."""
        gen = IdGenerator("test_component", "session_123")

        market_ts = datetime(2024, 1, 15, 9, 30, 45, tzinfo=timezone.utc)
        signal_id = gen.generate_signal_id("session_123", "AAPL", market_ts)

        # Format: f"{strategy_id}:{symbol}:{market_ts_iso}:{seq}"
        expected = "session_123:AAPL:2024-01-15T09:30:45:0001"
        assert signal_id == expected

    def test_generate_signal_id_sequence(self):
        """Test that signal IDs increment sequence numbers."""
        gen = IdGenerator("test_component", "session_123")

        market_ts = datetime(2024, 1, 15, 9, 30, 45, tzinfo=timezone.utc)

        id1 = gen.generate_signal_id("session_123", "AAPL", market_ts)
        id2 = gen.generate_signal_id("session_123", "AAPL", market_ts)
        id3 = gen.generate_signal_id("session_123", "MSFT", market_ts)

        assert "0001" in id1
        assert "0002" in id2
        assert "0003" in id3

    def test_generate_authorization_id(self):
        """Test authorization ID generation."""
        gen = IdGenerator("test_component", "session_123")

        auth_id = gen.generate_authorization_id("signal_001", "GATE_PASSED")

        # Format: f"auth:{signal_id}:{gate_passed}"
        expected = "auth:signal_001:GATE_PASSED"
        assert auth_id == expected

    def test_generate_order_id(self):
        """Test order ID generation."""
        gen = IdGenerator("test_component", "session_123")

        order_id1 = gen.generate_order_id()
        order_id2 = gen.generate_order_id()

        # Format: f"{session_id}:{seq:08d}"
        assert order_id1 == "session_123:00000001"
        assert order_id2 == "session_123:00000002"

    def test_generate_fill_id(self):
        """Test fill ID generation."""
        gen = IdGenerator("test_component", "session_123")

        order_id = "session_123:00000001"
        fill_id1 = gen.generate_fill_id(order_id, 1)
        fill_id2 = gen.generate_fill_id(order_id, 2)

        # Format: f"{order_id}:{fill_seq:03d}"
        assert fill_id1 == "session_123:00000001:001"
        assert fill_id2 == "session_123:00000001:002"

    def test_thread_safety_sequence(self):
        """Test thread safety of sequence number generation."""
        gen = IdGenerator("test_component", "session_123")

        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(100):
                    seq = gen.next_seq()
                    results.append((worker_id, seq))
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

        # Should have collected 500 sequence numbers
        assert len(results) == 500

        # All sequence numbers should be unique
        all_seqs = [seq for worker_id, seq in results]
        assert len(set(all_seqs)) == 500

        # Should be consecutive (no gaps)
        sorted_seqs = sorted(all_seqs)
        assert sorted_seqs[0] == 1
        assert sorted_seqs[-1] == 500

    def test_different_generators_independent(self):
        """Test that different IdGenerator instances are independent."""
        gen1 = IdGenerator("component1", "session_1")
        gen2 = IdGenerator("component2", "session_2")

        id1 = gen1.generate_signal_id("session_1", "AAPL", datetime.now(timezone.utc))
        id2 = gen2.generate_signal_id("session_2", "AAPL", datetime.now(timezone.utc))

        assert id1 != id2
        assert "session_1" in id1
        assert "session_2" in id2

class TestIdempotencyTracker:
    """Tests for IdempotencyTracker class."""

    def test_initialization(self):
        """Test IdempotencyTracker initialization."""
        tracker = IdempotencyTracker(max_history=1000)

        assert tracker.max_history == 1000
        assert len(tracker.processed_event_ids) == 0
        assert len(tracker.processed_signal_ids) == 0
        assert len(tracker.processed_fill_ids) == 0
        assert len(tracker._lru) == 0

        stats = tracker.get_stats()
        assert stats['checks'] == 0
        assert stats['duplicates_found'] == 0
        assert stats['ids_tracked'] == 0
        assert stats['evictions'] == 0

    def test_is_processed_false_for_new(self):
        """Test is_processed returns False for new IDs."""
        tracker = IdempotencyTracker()

        assert not tracker.is_processed('event', 'event_1')
        assert not tracker.is_processed('signal', 'signal_1')
        assert not tracker.is_processed('fill', 'fill_1')

    def test_mark_processed_and_check(self):
        """Test marking IDs as processed and checking them."""
        tracker = IdempotencyTracker()

        # Mark as processed
        tracker.mark_processed('event', 'event_1')
        tracker.mark_processed('signal', 'signal_1')

        # Should now be processed
        assert tracker.is_processed('event', 'event_1')
        assert tracker.is_processed('signal', 'signal_1')

        # Different IDs should not be processed
        assert not tracker.is_processed('event', 'event_2')
        assert not tracker.is_processed('signal', 'signal_2')

    def test_check_and_mark_atomic(self):
        """Test check_and_mark atomic operation."""
        tracker = IdempotencyTracker()

        # First call should return False (new) and mark as processed
        assert not tracker.check_and_mark('event', 'event_1')

        # Second call should return True (duplicate)
        assert tracker.check_and_mark('event', 'event_1')

        # Should be marked as processed
        assert tracker.is_processed('event', 'event_1')

    def test_lru_eviction(self):
        """Test LRU eviction when max_history is reached."""
        tracker = IdempotencyTracker(max_history=3)

        # Add 3 IDs
        tracker.mark_processed('event', 'event_1')
        tracker.mark_processed('event', 'event_2')
        tracker.mark_processed('event', 'event_3')

        assert tracker.is_processed('event', 'event_1')
        assert tracker.is_processed('event', 'event_2')
        assert tracker.is_processed('event', 'event_3')
        assert len(tracker._lru) == 3

        # Add 4th ID - should evict oldest (event_1)
        tracker.mark_processed('event', 'event_4')

        assert not tracker.is_processed('event', 'event_1')  # Evicted
        assert tracker.is_processed('event', 'event_2')
        assert tracker.is_processed('event', 'event_3')
        assert tracker.is_processed('event', 'event_4')
        assert len(tracker._lru) == 3

        stats = tracker.get_stats()
        assert stats['evictions'] == 1

    def test_different_id_types_separate(self):
        """Test that different ID types are tracked separately."""
        tracker = IdempotencyTracker()

        # Same ID value but different types
        tracker.mark_processed('event', 'id_1')
        tracker.mark_processed('signal', 'id_1')

        assert tracker.is_processed('event', 'id_1')
        assert tracker.is_processed('signal', 'id_1')
        assert not tracker.is_processed('fill', 'id_1')

    def test_invalid_id_type(self):
        """Test handling of invalid ID types."""
        tracker = IdempotencyTracker()

        # Invalid type should use event_ids as fallback
        tracker.mark_processed('invalid', 'test_id')
        assert tracker.is_processed('invalid', 'test_id')

        # Should be in event_ids
        assert 'test_id' in tracker.processed_event_ids

    def test_clear(self):
        """Test clearing all tracked IDs."""
        tracker = IdempotencyTracker()

        tracker.mark_processed('event', 'event_1')
        tracker.mark_processed('signal', 'signal_1')
        tracker.mark_processed('fill', 'fill_1')

        assert tracker.is_processed('event', 'event_1')
        assert tracker.is_processed('signal', 'signal_1')
        assert tracker.is_processed('fill', 'fill_1')

        tracker.clear()

        assert not tracker.is_processed('event', 'event_1')
        assert not tracker.is_processed('signal', 'signal_1')
        assert not tracker.is_processed('fill', 'fill_1')

        assert len(tracker._lru) == 0

    def test_get_stats(self):
        """Test getting tracker statistics."""
        tracker = IdempotencyTracker()

        # Perform some operations
        tracker.is_processed('event', 'event_1')  # Check (not found)
        tracker.mark_processed('event', 'event_1')  # Mark
        tracker.is_processed('event', 'event_1')  # Check (found)
        tracker.check_and_mark('signal', 'signal_1')  # Check and mark (new)

        stats = tracker.get_stats()

        assert stats['checks'] == 3
        assert stats['duplicates_found'] == 1
        assert stats['ids_tracked'] == 2
        assert stats['event_ids_count'] == 1
        assert stats['signal_ids_count'] == 1
        assert stats['fill_ids_count'] == 0

    def test_checkpoint_state(self):
        """Test checkpoint save/restore functionality."""
        tracker = IdempotencyTracker(max_history=200)  # Enough for all 150 items

        # Add some IDs
        for i in range(50):
            tracker.mark_processed('event', f'event_{i}')
            tracker.mark_processed('signal', f'signal_{i}')
            tracker.mark_processed('fill', f'fill_{i}')

        # Get checkpoint state
        state = tracker.get_state_for_checkpoint()

        assert 'recent_event_ids' in state
        assert 'recent_signal_ids' in state
        assert 'recent_fill_ids' in state

        # Should have all IDs since max_history is large enough
        assert len(state['recent_event_ids']) == 50
        assert len(state['recent_signal_ids']) == 50
        assert len(state['recent_fill_ids']) == 50

        # Create new tracker and restore
        new_tracker = IdempotencyTracker()
        new_tracker.restore_from_checkpoint(state)

        # Should have restored all the IDs
        for i in range(50):
            assert new_tracker.is_processed('event', f'event_{i}')
            assert new_tracker.is_processed('signal', f'signal_{i}')
            assert new_tracker.is_processed('fill', f'fill_{i}')

    def test_thread_safety(self):
        """Test thread safety of IdempotencyTracker."""
        tracker = IdempotencyTracker(max_history=1000)

        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(100):
                    id_value = f"worker_{worker_id}_id_{i}"

                    # Try check_and_mark (should succeed first time)
                    is_duplicate = tracker.check_and_mark('event', id_value)
                    results.append((worker_id, i, id_value, is_duplicate))

                    # Second check should be duplicate
                    is_duplicate_again = tracker.check_and_mark('event', id_value)
                    assert is_duplicate_again  # Should be True

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

        # Should have 500 results (5 threads * 100 operations)
        assert len(results) == 500

        # All first operations should be False (not duplicates)
        first_ops = [r for r in results if r[1] == 0]
        assert len(first_ops) == 5
        for worker_id, i, id_value, is_duplicate in first_ops:
            assert not is_duplicate

        # All IDs should be unique across threads
        all_ids = [id_value for worker_id, i, id_value, is_duplicate in results]
        assert len(set(all_ids)) == 500

class TestGenerateSessionId:
    """Tests for generate_session_id function."""

    @patch('datetime.date')
    def test_generate_session_id(self, mock_date):
        """Test session ID generation."""
        mock_date.today.return_value = datetime(2024, 1, 15).date()

        session_id = generate_session_id("paper")

        # Format: "{prefix}-{date}-{seq:04d}"
        assert session_id.startswith("paper-20240115-")
        assert len(session_id) == len("paper-20240115-0001")

    def test_generate_session_id_different_prefixes(self):
        """Test session ID generation with different prefixes."""
        id1 = generate_session_id("paper")
        id2 = generate_session_id("live")

        assert id1.startswith("paper-")
        assert id2.startswith("live-")

    @patch('random.randint')
    def test_generate_session_id_sequence(self, mock_randint):
        """Test that session IDs can have different sequences."""
        mock_randint.return_value = 42

        session_id = generate_session_id("test")

        assert "0042" in session_id

class TestIdempotencyIntegration:
    """Integration tests for idempotency system."""

    def test_full_idempotency_workflow(self):
        """Test complete idempotency workflow from ID generation to tracking."""
        # Create components
        gen = IdGenerator("dispatcher", "test_session")
        tracker = IdempotencyTracker()

        market_ts = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        # Generate signal ID
        signal_id = gen.generate_signal_id("test_session", "AAPL", market_ts)
        assert signal_id == "test_session:AAPL:2024-01-15T09:30:00:0001"

        # Check it's not processed yet
        assert not tracker.is_processed('signal', signal_id)

        # Mark as processed
        tracker.mark_processed('signal', signal_id)

        # Now it should be processed
        assert tracker.is_processed('signal', signal_id)

        # Generate authorization ID
        auth_id = gen.generate_authorization_id(signal_id, "RISK_CHECK_PASSED")
        assert auth_id == f"auth:{signal_id}:RISK_CHECK_PASSED"

        # Generate order ID
        order_id = gen.generate_order_id()
        assert order_id == "test_session:00000002"

        # Generate fill IDs
        fill_id1 = gen.generate_fill_id(order_id, 1)
        fill_id2 = gen.generate_fill_id(order_id, 2)

        assert fill_id1 == f"{order_id}:001"
        assert fill_id2 == f"{order_id}:002"

        # Track fills
        tracker.mark_processed('fill', fill_id1)
        tracker.mark_processed('fill', fill_id2)

        assert tracker.is_processed('fill', fill_id1)
        assert tracker.is_processed('fill', fill_id2)

        # Check stats
        stats = tracker.get_stats()
        assert stats['ids_tracked'] == 3  # signal + 2 fills
        assert stats['signal_ids_count'] == 1
        assert stats['fill_ids_count'] == 2

    def test_idempotency_prevents_duplicate_processing(self):
        """Test that idempotency prevents duplicate event processing."""
        tracker = IdempotencyTracker()

        event_id = "event_123"

        # First processing
        is_duplicate = tracker.check_and_mark('event', event_id)
        assert not is_duplicate  # New event

        # Simulate processing
        process_event(event_id)

        # Attempt duplicate processing
        is_duplicate = tracker.check_and_mark('event', event_id)
        assert is_duplicate  # Should be blocked

        # Verify stats
        # Verify stats
        stats = tracker.get_stats()
        assert stats['duplicates_found'] == 1
        assert stats['checks'] == 2
