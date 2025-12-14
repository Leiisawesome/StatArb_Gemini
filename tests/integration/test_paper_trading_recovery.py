"""
Recovery Tests - Crash and Restore
==================================

Tests from plan Section 9.3:
- Simulate crash after fill generated, before checkpoint
- Restore → verify no double-applied fills

Additional tests:
- Test checkpoint atomicity
- Test recovery from various failure points
- Test idempotency after recovery

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 6)
"""

import pytest
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

class TestCrashRecovery:
    """Test crash and recovery scenarios."""

    @pytest.fixture
    def temp_checkpoint_dir(self):
        """Create temporary checkpoint directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def state_manager(self, temp_checkpoint_dir):
        """Create state manager with temp directory."""
        from core_engine.system.paper_state_manager import PaperSessionStateManager

        return PaperSessionStateManager(
            session_id="test-session-001",
            checkpoint_dir=temp_checkpoint_dir,
            checkpoint_interval_bars=100,
        )

    def test_checkpoint_created_successfully(self, state_manager):
        """Test that checkpoints are created."""
        # Create a checkpoint
        checkpoint_id = state_manager.create_checkpoint('test')

        assert checkpoint_id is not None
        assert checkpoint_id.startswith('test-session-001')

        # Verify checkpoint file exists
        checkpoints = state_manager.list_checkpoints()
        assert len(checkpoints) == 1

    def test_restore_from_checkpoint(self, state_manager):
        """Test restoring state from checkpoint."""
        # Set some state
        state_manager.update_event_tracking('event-123', 500)
        state_manager.set_replay_position(
            'AAPL',
            datetime.now(timezone.utc),
            1000
        )

        # Create checkpoint
        checkpoint_id = state_manager.create_checkpoint('test')

        # Create new state manager (simulate restart)
        from core_engine.system.paper_state_manager import PaperSessionStateManager

        new_manager = PaperSessionStateManager(
            session_id="test-session-001",
            checkpoint_dir=state_manager._checkpoint_dir,
        )

        # Restore
        success = new_manager.restore_checkpoint(checkpoint_id)
        assert success

        # Verify state restored
        info = new_manager.get_last_event_info()
        assert info['last_event_id'] == 'event-123'
        assert info['last_event_sequence'] == 500

    def test_no_duplicate_fills_after_recovery(self, temp_checkpoint_dir):
        """
        Test that fills are not duplicated after recovery.

        Simulates:
        1. Process fill
        2. Crash before checkpoint
        3. Restore
        4. Replay fill event
        5. Verify fill not applied twice
        """
        from core_engine.system.idempotency import IdempotencyTracker
        from core_engine.system.paper_state_manager import PaperSessionStateManager

        # Setup
        tracker = IdempotencyTracker()
        manager = PaperSessionStateManager(
            session_id="test-recovery",
            checkpoint_dir=temp_checkpoint_dir,
        )
        manager.register_component('idempotency', tracker)

        # Process a fill
        fill_id = "order-001:001"
        tracker.mark_processed('fill', fill_id)

        # Create checkpoint (simulating successful checkpoint after fill)
        manager.create_checkpoint('before_crash')

        # Simulate crash and restart
        new_tracker = IdempotencyTracker()
        new_manager = PaperSessionStateManager(
            session_id="test-recovery",
            checkpoint_dir=temp_checkpoint_dir,
        )
        new_manager.register_component('idempotency', new_tracker)

        # Restore
        new_manager.restore_checkpoint()

        # Try to process same fill again (replay scenario)
        is_duplicate = new_tracker.is_processed('fill', fill_id)

        # Should be detected as duplicate
        assert is_duplicate, "Fill should be detected as duplicate after recovery"

    def test_crash_between_fill_and_checkpoint(self, temp_checkpoint_dir):
        """
        Test recovery when crash occurs between fill and checkpoint.

        The fill should be replayable without duplication issues.
        """
        from core_engine.system.idempotency import IdempotencyTracker
        from core_engine.system.paper_state_manager import PaperSessionStateManager

        # Setup - initial state
        tracker = IdempotencyTracker()
        manager = PaperSessionStateManager(
            session_id="test-crash",
            checkpoint_dir=temp_checkpoint_dir,
        )
        manager.register_component('idempotency', tracker)

        # Create initial checkpoint
        manager.create_checkpoint('initial')

        # Process some fills
        tracker.mark_processed('fill', 'fill-001')
        tracker.mark_processed('fill', 'fill-002')

        # CRASH HERE - no checkpoint after fills 001 and 002

        # Simulate restart with new instances
        new_tracker = IdempotencyTracker()
        new_manager = PaperSessionStateManager(
            session_id="test-crash",
            checkpoint_dir=temp_checkpoint_dir,
        )
        new_manager.register_component('idempotency', new_tracker)

        # Restore from 'initial' checkpoint (before fills)
        new_manager.restore_checkpoint()

        # Replay fills - they should NOT be detected as duplicates
        # because we restored to before they were processed
        assert not new_tracker.is_processed('fill', 'fill-001')
        assert not new_tracker.is_processed('fill', 'fill-002')

        # Now process them again
        new_tracker.mark_processed('fill', 'fill-001')
        new_tracker.mark_processed('fill', 'fill-002')

        # Create checkpoint after successful replay
        new_manager.create_checkpoint('after_replay')

        # Now they should be tracked
        assert new_tracker.is_processed('fill', 'fill-001')
        assert new_tracker.is_processed('fill', 'fill-002')

class TestCheckpointAtomicity:
    """Test checkpoint atomicity guarantees."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_checkpoint_atomic_write(self, temp_dir):
        """
        Test that checkpoints are written atomically.

        Partial writes should not corrupt checkpoint.
        """
        from core_engine.system.paper_state_manager import PaperSessionStateManager

        manager = PaperSessionStateManager(
            session_id="atomic-test",
            checkpoint_dir=temp_dir,
        )

        # Set substantial state
        for i in range(10):
            manager.set_replay_position(
                f'SYMBOL_{i}',
                datetime.now(timezone.utc),
                i * 100
            )

        # Create checkpoint
        checkpoint_id = manager.create_checkpoint('test')

        # Verify checkpoint file is valid JSON
        checkpoint_path = Path(temp_dir) / f"{checkpoint_id.replace(':', '_')}.json"

        with open(checkpoint_path, 'r') as f:
            data = json.load(f)

        assert 'metadata' in data
        assert 'replay_positions' in data
        assert len(data['replay_positions']) == 10

    def test_no_temp_files_left(self, temp_dir):
        """
        Test that no temporary files are left after checkpoint.
        """
        from core_engine.system.paper_state_manager import PaperSessionStateManager

        manager = PaperSessionStateManager(
            session_id="temp-test",
            checkpoint_dir=temp_dir,
        )

        # Create multiple checkpoints
        for i in range(3):
            manager.create_checkpoint(f'test_{i}')

        # Check no .tmp files exist
        temp_files = list(Path(temp_dir).glob('*.tmp'))
        assert len(temp_files) == 0, f"Temp files remaining: {temp_files}"

class TestIdempotencyRecovery:
    """Test idempotency after recovery."""

    def test_idempotency_tracker_persistence(self):
        """Test idempotency tracker state persists correctly."""
        from core_engine.system.idempotency import IdempotencyTracker

        tracker = IdempotencyTracker(max_history=1000)

        # Track many IDs
        for i in range(100):
            tracker.mark_processed('event', f'event-{i}')
            tracker.mark_processed('signal', f'signal-{i}')

        # Get state
        state = tracker.get_state_for_checkpoint()

        # Create new tracker and restore
        new_tracker = IdempotencyTracker()
        new_tracker.restore_from_checkpoint(state)

        # Verify IDs are tracked
        for i in range(100):
            assert new_tracker.is_processed('event', f'event-{i}')
            assert new_tracker.is_processed('signal', f'signal-{i}')

    def test_check_and_mark_atomic(self):
        """Test check_and_mark is atomic."""
        from core_engine.system.idempotency import IdempotencyTracker

        tracker = IdempotencyTracker()

        # First call should return False (not duplicate) and mark
        result1 = tracker.check_and_mark('event', 'test-event')
        assert result1 == False  # Not a duplicate, now marked

        # Second call should return True (duplicate)
        result2 = tracker.check_and_mark('event', 'test-event')
        assert result2 == True  # Is a duplicate

class TestRecoveryWithComponents:
    """Test recovery with multiple components."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_buffer_manager_recovery(self, temp_dir):
        """Test buffer manager survives checkpoint/restore."""
        from core_engine.processing.streaming.buffer_manager import StreamingBufferManager
        from core_engine.system.paper_state_manager import PaperSessionStateManager

        # Setup
        buffer = StreamingBufferManager(buffer_size=100, warmup_required=10)
        manager = PaperSessionStateManager(
            session_id="buffer-test",
            checkpoint_dir=temp_dir,
        )
        manager.register_component('buffer', buffer)

        # Add data
        for i in range(20):
            buffer.update('TEST', {
                'timestamp': datetime(2025, 1, 15, 10, 0, i, tzinfo=timezone.utc),
                'open': 100 + i,
                'high': 101 + i,
                'low': 99 + i,
                'close': 100.5 + i,
                'volume': 1000,
            })

        # Checkpoint
        manager.create_checkpoint('test')

        # Create new instances
        new_buffer = StreamingBufferManager(buffer_size=100, warmup_required=10)
        new_manager = PaperSessionStateManager(
            session_id="buffer-test",
            checkpoint_dir=temp_dir,
        )
        new_manager.register_component('buffer', new_buffer)

        # Restore
        new_manager.restore_checkpoint()

        # Verify buffer restored
        assert new_buffer.is_warmed_up('TEST')
        assert new_buffer.get_buffer_length('TEST') == buffer.get_buffer_length('TEST')

    def test_risk_budget_recovery(self, temp_dir):
        """Test risk budget survives checkpoint/restore."""
        from core_engine.system.risk_budget import RiskBudgetState
        from core_engine.system.paper_state_manager import PaperSessionStateManager

        # Setup
        budget = RiskBudgetState(daily_risk_budget_pct=0.01)
        budget.update_portfolio_value(100_000)
        budget.add_position('AAPL', 'long', 100, 150.0, 145.0)

        manager = PaperSessionStateManager(
            session_id="risk-test",
            checkpoint_dir=temp_dir,
        )
        manager.register_component('risk_budget', budget)

        # Get state before checkpoint
        used_before = budget.get_used_risk_budget()

        # Checkpoint
        manager.create_checkpoint('test')

        # Create new instances
        new_budget = RiskBudgetState()
        new_manager = PaperSessionStateManager(
            session_id="risk-test",
            checkpoint_dir=temp_dir,
        )
        new_manager.register_component('risk_budget', new_budget)

        # Restore
        new_manager.restore_checkpoint()

        # Verify budget restored
        used_after = new_budget.get_used_risk_budget()
        assert used_after == used_before

class TestJournalRecovery:
    """Test event journal for recovery support."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_journal_readable_after_close(self, temp_dir):
        """Test journal can be read after close."""
        from core_engine.system.event_journal import EventJournal

        # Write events
        with EventJournal("test-session", temp_dir) as journal:
            journal.log_bar('AAPL', {'close': 150.0})
            journal.log_signal('AAPL', {'strength': 0.8})
            journal.log_fill('AAPL', 'order-1', 'fill-1', 100, 150.0)

        # Read events
        journal_path = Path(temp_dir) / "test-session.jsonl"
        events = EventJournal.read_journal(str(journal_path))

        assert len(events) == 3
        assert events[0].event_type == 'bar'
        assert events[1].event_type == 'signal_generated'
        assert events[2].event_type == 'fill'

    def test_journal_sequence_preserved(self, temp_dir):
        """Test journal preserves event sequence."""
        from core_engine.system.event_journal import EventJournal

        with EventJournal("seq-test", temp_dir) as journal:
            for i in range(10):
                journal.log_system(f'event_{i}', {'index': i})

        # Read and verify sequence
        journal_path = Path(temp_dir) / "seq-test.jsonl"
        events = EventJournal.read_journal(str(journal_path))

        for i, event in enumerate(events):
            assert event.sequence == i + 1
            assert event.data['index'] == i

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

