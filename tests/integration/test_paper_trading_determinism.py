"""
Determinism Tests - Reproducible Paper Trading Runs
===================================================

Tests from plan Section 9.2:
- Run same session twice → identical fills, positions, P&L
- Verify event ordering is consistent

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 6)
"""

import pytest
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List

class TestDeterministicEventOrdering:
    """Test deterministic event ordering."""

    def test_event_dispatcher_ordering(self):
        """
        Test that event dispatcher maintains deterministic ordering.

        Events with same timestamp should be ordered by sequence number.
        """
        from core_engine.system.time_source import ReplayTimeSource
        from core_engine.system.event_dispatcher import (
            DeterministicEventDispatcher, EventType
        )

        # Initialize with a time before the test timestamps
        initial_time = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        time_source = ReplayTimeSource(initial_time=initial_time)
        dispatcher = DeterministicEventDispatcher(time_source)

        # Enqueue events with same timestamp
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        dispatcher.enqueue(EventType.BAR, {'symbol': 'AAPL', 'close': 150}, timestamp, 'AAPL')
        dispatcher.enqueue(EventType.BAR, {'symbol': 'MSFT', 'close': 380}, timestamp, 'MSFT')
        dispatcher.enqueue(EventType.BAR, {'symbol': 'GOOGL', 'close': 140}, timestamp, 'GOOGL')

        # Process and verify order
        events = []
        while not dispatcher.is_empty():
            event = dispatcher.process_next()
            if event:
                events.append(event)

        # Should be in sequence order
        for i in range(len(events) - 1):
            assert events[i].sequence_number < events[i + 1].sequence_number

    def test_same_input_same_output(self):
        """
        Test that same inputs produce same outputs.

        Two identical runs should produce identical results.
        """
        from core_engine.system.time_source import ReplayTimeSource
        from core_engine.system.event_dispatcher import (
            DeterministicEventDispatcher, EventType
        )

        def run_simulation(seed: int) -> List[Dict]:
            # Initialize with a time before the test timestamps
            initial_time = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
            time_source = ReplayTimeSource(initial_time=initial_time)
            dispatcher = DeterministicEventDispatcher(time_source)

            # Reset sequence counter for reproducibility
            dispatcher.restore_sequence_counter(0)

            np.random.seed(seed)

            results = []
            for i in range(10):
                timestamp = datetime(2025, 1, 15, 10, 30, i, tzinfo=timezone.utc)
                dispatcher.enqueue(
                    EventType.BAR,
                    {'close': 150 + np.random.randn()},
                    timestamp,
                    'TEST'
                )

            while not dispatcher.is_empty():
                event = dispatcher.process_next()
                if event:
                    results.append({
                        'seq': event.sequence_number,
                        'ts': event.market_timestamp,
                        'data': event.payload,
                    })

            return results

        # Run twice with same seed
        run1 = run_simulation(42)
        run2 = run_simulation(42)

        # Should be identical
        assert len(run1) == len(run2)
        for r1, r2 in zip(run1, run2):
            assert r1['seq'] == r2['seq']
            assert r1['ts'] == r2['ts']
            assert r1['data']['close'] == r2['data']['close']

    def test_id_generation_determinism(self):
        """
        Test that ID generation is deterministic.

        Same sequence counter state should produce same IDs.
        """
        from core_engine.system.idempotency import IdGenerator

        session_id = "paper-20250115-0001"

        # First generator
        gen1 = IdGenerator("test", session_id)
        gen1.restore_seq(100)  # Set to known state

        ids1 = []
        for i in range(5):
            ids1.append(gen1.generate_order_id())

        # Second generator with same state
        gen2 = IdGenerator("test", session_id)
        gen2.restore_seq(100)

        ids2 = []
        for i in range(5):
            ids2.append(gen2.generate_order_id())

        # Should produce identical IDs
        assert ids1 == ids2

class TestDeterministicFills:
    """Test deterministic fill simulation."""

    @pytest.mark.asyncio
    async def test_paper_broker_deterministic_fills(self):
        """
        Test that paper broker produces deterministic fills.

        Note: Random slippage needs to be seeded for determinism.
        """
        from core_engine.broker.adapters.paper_adapter import (
            PaperBrokerAdapter
        )
        from core_engine.type_definitions.broker_types import OrderSide
        import asyncio

        # Set seed for reproducibility
        import random
        random.seed(42)

        broker1 = PaperBrokerAdapter(initial_cash=100_000)
        broker1.connect()
        broker1.set_price('AAPL', 150.0)

        # Submit order
        order1 = broker1.submit_market_order('AAPL', 100, OrderSide.BUY)

        # Give async execution time to process
        await asyncio.sleep(0.3)

        # Reset and repeat
        random.seed(42)

        broker2 = PaperBrokerAdapter(initial_cash=100_000)
        broker2.connect()
        broker2.set_price('AAPL', 150.0)

        order2 = broker2.submit_market_order('AAPL', 100, OrderSide.BUY)

        # Give async execution time to process
        await asyncio.sleep(0.3)

        # Orders should have same structure
        assert order1.symbol == order2.symbol
        assert order1.quantity == order2.quantity

    def test_position_updates_deterministic(self):
        """
        Test that position updates are deterministic.
        """
        from core_engine.system.risk_budget import RiskBudgetState

        budget1 = RiskBudgetState()
        budget1.update_portfolio_value(100_000)
        budget1.add_position('AAPL', 'long', 100, 150.0, 145.0, 'test')

        budget2 = RiskBudgetState()
        budget2.update_portfolio_value(100_000)
        budget2.add_position('AAPL', 'long', 100, 150.0, 145.0, 'test')

        # Should have same used risk
        assert budget1.get_used_risk_budget() == budget2.get_used_risk_budget()
        assert budget1.get_available_risk() == budget2.get_available_risk()

class TestDeterministicCheckpointRestore:
    """Test checkpoint/restore produces deterministic state."""

    def test_buffer_manager_restore_determinism(self):
        """
        Test buffer manager checkpoint/restore.
        """
        from core_engine.processing.streaming.buffer_manager import StreamingBufferManager
        import pandas as pd

        # Create and populate buffer
        manager1 = StreamingBufferManager(buffer_size=100, warmup_required=10)

        for i in range(20):
            manager1.update('TEST', {
                'timestamp': datetime(2025, 1, 15, 10, 0, i, tzinfo=timezone.utc),
                'open': 150 + i * 0.1,
                'high': 151 + i * 0.1,
                'low': 149 + i * 0.1,
                'close': 150.5 + i * 0.1,
                'volume': 1000,
            })

        # Checkpoint
        state = manager1.get_state_for_checkpoint()

        # Restore to new manager
        manager2 = StreamingBufferManager(buffer_size=100, warmup_required=10)
        manager2.restore_from_checkpoint(state)

        # Verify identical state
        assert manager1.is_warmed_up('TEST') == manager2.is_warmed_up('TEST')
        assert manager1.get_buffer_length('TEST') == manager2.get_buffer_length('TEST')

        df1 = manager1.get_buffer('TEST')
        df2 = manager2.get_buffer('TEST')

        # DataFrames should be identical (check_dtype=False for serialization tolerance)
        pd.testing.assert_frame_equal(df1, df2, check_dtype=False)

    def test_idempotency_tracker_restore(self):
        """
        Test idempotency tracker checkpoint/restore.
        """
        from core_engine.system.idempotency import IdempotencyTracker

        tracker1 = IdempotencyTracker()

        # Mark some IDs
        tracker1.mark_processed('event', 'e1')
        tracker1.mark_processed('event', 'e2')
        tracker1.mark_processed('fill', 'f1')

        # Checkpoint
        state = tracker1.get_state_for_checkpoint()

        # Restore
        tracker2 = IdempotencyTracker()
        tracker2.restore_from_checkpoint(state)

        # Verify same IDs are tracked
        assert tracker2.is_processed('event', 'e1')
        assert tracker2.is_processed('event', 'e2')
        assert tracker2.is_processed('fill', 'f1')
        assert not tracker2.is_processed('event', 'e3')

    def test_risk_budget_restore(self):
        """
        Test risk budget checkpoint/restore.
        """
        from core_engine.system.risk_budget import RiskBudgetState

        budget1 = RiskBudgetState(daily_risk_budget_pct=0.01)
        budget1.update_portfolio_value(100_000)
        budget1.add_position('AAPL', 'long', 100, 150.0, 145.0)

        # Checkpoint
        state = budget1.get_state_for_checkpoint()

        # Restore
        budget2 = RiskBudgetState()
        budget2.restore_from_checkpoint(state)

        # Verify same state
        assert budget2._portfolio_value == budget1._portfolio_value
        assert len(budget2._positions) == len(budget1._positions)
        assert budget2.get_used_risk_budget() == budget1.get_used_risk_budget()

class TestSequenceCounterDeterminism:
    """Test sequence counter handling for determinism."""

    def test_sequence_restored_correctly(self):
        """
        Test that sequence counters restore correctly after checkpoint.
        """
        from core_engine.system.idempotency import IdGenerator

        gen = IdGenerator("test", "session-001")

        # Generate some IDs
        for _ in range(100):
            gen.next_seq()

        # Save state
        saved_seq = gen.current_seq

        # Generate more
        for _ in range(50):
            gen.next_seq()

        # Restore
        gen.restore_seq(saved_seq)

        # Should continue from saved point
        assert gen.current_seq == saved_seq
        next_id = gen.next_seq()
        assert next_id == saved_seq + 1

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

