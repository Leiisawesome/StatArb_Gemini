"""
Tests for DeterministicEventDispatcher
=======================================

Tests cover:
- Priority queue ordering and determinism
- Backpressure policies (block, drop, conflate)
- Handler registration and dispatch
- Thread safety
- Statistics and monitoring
- Sequence counter management

Author: StatArb_Gemini Test Suite
"""

import pytest
import threading
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from core_engine.system.event_dispatcher import (
    DeterministicEventDispatcher,
    PrioritizedEvent,
    EventType
)
from core_engine.system.time_source import TimeSource

class TestPrioritizedEvent:
    """Tests for PrioritizedEvent dataclass."""

    def test_initialization_with_timezone(self):
        """Test event initialization adds UTC timezone if missing."""
        naive_time = datetime(2024, 1, 15, 9, 30, 0)
        event = PrioritizedEvent(
            market_timestamp=naive_time,
            sequence_number=1,
            event_type=EventType.BAR,
            symbol="AAPL",
            payload={"close": 150.0}
        )

        assert event.market_timestamp.tzinfo == timezone.utc
        assert event.sequence_number == 1
        assert event.event_type == EventType.BAR
        assert event.symbol == "AAPL"
        assert event.payload == {"close": 150.0}

    def test_initialization_preserves_timezone(self):
        """Test event initialization preserves existing timezone."""
        utc_time = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        event = PrioritizedEvent(
            market_timestamp=utc_time,
            sequence_number=1,
            event_type=EventType.BAR
        )

        assert event.market_timestamp == utc_time
        assert event.market_timestamp.tzinfo == timezone.utc

    def test_ordering_by_timestamp_and_sequence(self):
        """Test events are ordered by timestamp then sequence."""
        time1 = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        time2 = datetime(2024, 1, 15, 9, 30, 1, tzinfo=timezone.utc)

        event1 = PrioritizedEvent(time1, 1, EventType.BAR)
        event2 = PrioritizedEvent(time1, 2, EventType.BAR)
        event3 = PrioritizedEvent(time2, 1, EventType.BAR)

        # Same timestamp, lower sequence first
        assert event1 < event2
        # Different timestamp takes precedence
        assert event1 < event3
        assert event2 < event3

class TestDeterministicEventDispatcher:
    """Tests for DeterministicEventDispatcher."""

    @pytest.fixture
    def time_source(self):
        """Create a mock time source."""
        mock_ts = Mock(spec=TimeSource)
        mock_ts.market_now.return_value = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        mock_ts.advance_market_time = Mock()
        return mock_ts

    @pytest.fixture
    def dispatcher(self, time_source):
        """Create a test dispatcher."""
        return DeterministicEventDispatcher(
            time_source=time_source,
            max_queue_size=10,
            bar_queue_size=5,
            conflate_quotes=True
        )

    def test_initialization(self, time_source):
        """Test dispatcher initialization."""
        dispatcher = DeterministicEventDispatcher(time_source)

        assert dispatcher._time_source == time_source
        assert dispatcher._max_queue_size == 10000
        assert dispatcher._bar_queue_size == 1000
        assert dispatcher._conflate_quotes is True
        assert dispatcher._sequence_counter == 0
        assert dispatcher._events_processed == 0
        assert dispatcher._events_dropped == 0
        assert dispatcher._events_conflated == 0
        assert dispatcher.is_empty()

    def test_register_handler(self, dispatcher):
        """Test handler registration."""
        handler = Mock()
        dispatcher.register_handler(EventType.BAR, handler)

        assert handler in dispatcher._handlers[EventType.BAR]
        assert len(dispatcher._handlers[EventType.BAR]) == 1

    def test_register_multiple_handlers(self, dispatcher):
        """Test multiple handlers for same event type."""
        handler1 = Mock()
        handler2 = Mock()

        dispatcher.register_handler(EventType.BAR, handler1)
        dispatcher.register_handler(EventType.BAR, handler2)

        assert len(dispatcher._handlers[EventType.BAR]) == 2
        assert handler1 in dispatcher._handlers[EventType.BAR]
        assert handler2 in dispatcher._handlers[EventType.BAR]

    def test_unregister_handler(self, dispatcher):
        """Test handler unregistration."""
        handler = Mock()
        dispatcher.register_handler(EventType.BAR, handler)

        assert handler in dispatcher._handlers[EventType.BAR]

        dispatcher.unregister_handler(EventType.BAR, handler)

        assert handler not in dispatcher._handlers[EventType.BAR]

    def test_enqueue_bar_event(self, dispatcher, time_source):
        """Test enqueuing bar events."""
        time_source.market_now.return_value = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        success = dispatcher.enqueue(
            EventType.BAR,
            {"close": 150.0},
            symbol="AAPL"
        )

        assert success is True
        assert dispatcher.queue_size() == 1

        # Check event was created correctly
        event = dispatcher._queue[0]
        assert event.event_type == EventType.BAR
        assert event.symbol == "AAPL"
        assert event.payload == {"close": 150.0}
        assert event.market_timestamp == datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        assert event.sequence_number == 1

    def test_enqueue_with_custom_timestamp(self, dispatcher):
        """Test enqueuing with custom timestamp."""
        custom_time = datetime(2024, 1, 15, 9, 31, 0, tzinfo=timezone.utc)

        success = dispatcher.enqueue(
            EventType.SIGNAL,
            {"action": "BUY"},
            market_timestamp=custom_time,
            symbol="AAPL"
        )

        assert success is True
        event = dispatcher._queue[0]
        assert event.market_timestamp == custom_time

    def test_process_next_empty_queue(self, dispatcher):
        """Test processing from empty queue."""
        event = dispatcher.process_next()
        assert event is None

    def test_process_next_with_event(self, dispatcher, time_source):
        """Test processing a single event."""
        # Setup handler
        handler = Mock()
        dispatcher.register_handler(EventType.BAR, handler)

        # Enqueue event
        dispatcher.enqueue(EventType.BAR, {"close": 150.0}, symbol="AAPL")

        # Process it
        event = dispatcher.process_next()

        assert event is not None
        assert event.event_type == EventType.BAR
        assert event.symbol == "AAPL"

        # Handler should have been called
        handler.assert_called_once_with(event)

        # Time source should have been advanced
        time_source.advance_market_time.assert_called_once_with(event.market_timestamp)

        # Stats updated
        stats = dispatcher.get_stats()
        assert stats['events_processed'] == 1

    def test_process_all(self, dispatcher):
        """Test processing all events."""
        handler = Mock()
        dispatcher.register_handler(EventType.BAR, handler)

        # Enqueue multiple events
        for i in range(3):
            dispatcher.enqueue(EventType.BAR, {"close": 150.0 + i}, symbol="AAPL")

        # Process all
        count = dispatcher.process_all()

        assert count == 3
        assert dispatcher.is_empty()
        assert handler.call_count == 3

    def test_process_all_with_limit(self, dispatcher):
        """Test processing with max_events limit."""
        handler = Mock()
        dispatcher.register_handler(EventType.BAR, handler)

        # Enqueue 5 events
        for i in range(5):
            dispatcher.enqueue(EventType.BAR, {"close": 150.0 + i}, symbol="AAPL")

        # Process only 2
        count = dispatcher.process_all(max_events=2)

        assert count == 2
        assert dispatcher.queue_size() == 3
        assert handler.call_count == 2

    def test_conflation_quotes(self, dispatcher):
        """Test quote conflation per symbol."""
        # Enqueue multiple quotes for same symbol
        dispatcher.enqueue(EventType.QUOTE, {"bid": 149.0}, symbol="AAPL")
        dispatcher.enqueue(EventType.QUOTE, {"bid": 149.5}, symbol="AAPL")  # Should conflate
        dispatcher.enqueue(EventType.QUOTE, {"bid": 150.0}, symbol="AAPL")  # Should conflate

        # Should only have 1 event in buffer
        assert dispatcher.queue_size() == 1

        # Register a handler to avoid issues
        handler = Mock()
        dispatcher.register_handler(EventType.QUOTE, handler)

        # Process it
        event = dispatcher.process_next()
        assert event is not None
        assert event.payload == {"bid": 150.0}  # Latest one

        stats = dispatcher.get_stats()
        assert stats['events_conflated'] == 2  # 2 older quotes conflated

    def test_conflation_different_symbols(self, dispatcher):
        """Test quote conflation maintains separate symbols."""
        dispatcher.enqueue(EventType.QUOTE, {"bid": 149.0}, symbol="AAPL")
        dispatcher.enqueue(EventType.QUOTE, {"bid": 249.0}, symbol="MSFT")

        assert dispatcher.queue_size() == 2

    def test_conflation_disabled(self, time_source):
        """Test disabling quote conflation."""
        dispatcher = DeterministicEventDispatcher(
            time_source=time_source,
            conflate_quotes=False
        )

        # Enqueue multiple quotes
        dispatcher.enqueue(EventType.QUOTE, {"bid": 149.0}, symbol="AAPL")
        dispatcher.enqueue(EventType.QUOTE, {"bid": 149.5}, symbol="AAPL")

        # Should have 2 separate events
        assert dispatcher.queue_size() == 2

    def test_bar_backpressure_blocking(self, dispatcher):
        """Test bar events block when queue is full."""
        # Fill bar queue
        for i in range(5):  # bar_queue_size = 5
            dispatcher.enqueue(EventType.BAR, {"close": 150.0}, symbol="AAPL")

        # This should succeed (at capacity)
        success = dispatcher.enqueue(EventType.BAR, {"close": 151.0}, symbol="AAPL")
        assert success is True
        assert dispatcher.queue_size() == 6

    def test_other_events_drop_oldest(self, dispatcher):
        """Test other events drop oldest when queue full."""
        # Fill queue
        for i in range(10):  # max_queue_size = 10
            dispatcher.enqueue(EventType.SIGNAL, {"action": "BUY"}, symbol="AAPL")

        # Add one more - should drop oldest
        dispatcher.enqueue(EventType.SIGNAL, {"action": "SELL"}, symbol="AAPL")

        assert dispatcher.queue_size() == 10

        stats = dispatcher.get_stats()
        assert stats['events_dropped'] == 1

    def test_quote_without_symbol_dropped(self, dispatcher):
        """Test quotes without symbol are dropped."""
        success = dispatcher.enqueue(EventType.QUOTE, {"bid": 149.0})  # No symbol

        assert success is False
        stats = dispatcher.get_stats()
        assert stats['events_dropped'] == 1

    def test_handler_error_handling(self, dispatcher, caplog):
        """Test handler exceptions are caught and logged."""
        handler = Mock(side_effect=ValueError("Handler failed"))
        dispatcher.register_handler(EventType.BAR, handler)

        dispatcher.enqueue(EventType.BAR, {"close": 150.0}, symbol="AAPL")
        event = dispatcher.process_next()

        assert event is not None
        handler.assert_called_once()

        # Error should be logged
        assert "Handler error" in caplog.text

    def test_thread_safety_enqueue(self, dispatcher):
        """Test thread-safe enqueuing."""
        results = []
        errors = []

        def enqueue_worker(event_id: int):
            try:
                for i in range(10):
                    success = dispatcher.enqueue(
                        EventType.SIGNAL,
                        {"id": f"{event_id}_{i}"},
                        symbol="AAPL"
                    )
                    results.append(success)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=enqueue_worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(results)  # All enqueues should succeed
        assert dispatcher.queue_size() == 30  # 3 threads * 10 events each

    def test_sequence_counter_thread_safety(self, dispatcher):
        """Test sequence counter thread safety."""
        sequences = []

        def get_sequences():
            for _ in range(10):
                seq = dispatcher._next_sequence()
                sequences.append(seq)

        threads = []
        for _ in range(3):
            t = threading.Thread(target=get_sequences)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have 30 unique sequences
        assert len(set(sequences)) == 30
        assert min(sequences) == 1
        assert max(sequences) == 30

    def test_get_stats(self, dispatcher):
        """Test statistics reporting."""
        # Add some activity
        dispatcher.enqueue(EventType.BAR, {}, symbol="AAPL")
        dispatcher._events_dropped = 2
        dispatcher._events_conflated = 3

        stats = dispatcher.get_stats()

        expected_keys = {
            'events_processed', 'events_dropped', 'events_conflated',
            'queue_size', 'sequence_counter'
        }
        assert set(stats.keys()) == expected_keys
        assert stats['events_dropped'] == 2
        assert stats['events_conflated'] == 3
        assert stats['sequence_counter'] == 1

    def test_reset_stats(self, dispatcher):
        """Test statistics reset."""
        dispatcher._events_processed = 10
        dispatcher._events_dropped = 5

        dispatcher.reset_stats()

        assert dispatcher._events_processed == 0
        assert dispatcher._events_dropped == 0

    def test_clear(self, dispatcher):
        """Test clearing all queues."""
        # Add events
        dispatcher.enqueue(EventType.BAR, {}, symbol="AAPL")
        dispatcher.enqueue(EventType.QUOTE, {"bid": 149.0}, symbol="AAPL")

        assert not dispatcher.is_empty()

        dispatcher.clear()

        assert dispatcher.is_empty()

    def test_get_restore_sequence_counter(self, dispatcher):
        """Test sequence counter checkpointing."""
        # Advance sequence
        dispatcher._next_sequence()
        dispatcher._next_sequence()

        counter = dispatcher.get_sequence_counter()
        assert counter == 2

        # Restore to different value
        dispatcher.restore_sequence_counter(100)

        assert dispatcher._next_sequence() == 101

    def test_priority_ordering(self, dispatcher):
        """Test events are processed in priority order."""
        base_time = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        # Enqueue events with different timestamps
        dispatcher.enqueue(
            EventType.BAR, {"id": 1},
            market_timestamp=base_time + timedelta(seconds=2)
        )
        dispatcher.enqueue(
            EventType.BAR, {"id": 2},
            market_timestamp=base_time + timedelta(seconds=1)
        )
        dispatcher.enqueue(
            EventType.BAR, {"id": 3},
            market_timestamp=base_time + timedelta(seconds=3)
        )

        # Process and check order
        processed = []
        while not dispatcher.is_empty():
            event = dispatcher.process_next()
            processed.append(event.payload["id"])

        # Should be processed in timestamp order: 2, 1, 3
        assert processed == [2, 1, 3]

    def test_same_timestamp_sequence_ordering(self, dispatcher):
        """Test events with same timestamp ordered by sequence."""
        timestamp = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        # Enqueue events at same timestamp
        dispatcher.enqueue(EventType.BAR, {"id": 1}, market_timestamp=timestamp)
        dispatcher.enqueue(EventType.BAR, {"id": 2}, market_timestamp=timestamp)
        dispatcher.enqueue(EventType.BAR, {"id": 3}, market_timestamp=timestamp)

        # Process and check sequence order
        processed = []
        while not dispatcher.is_empty():
            event = dispatcher.process_next()
            processed.append(event.payload["id"])

        # Should be in sequence order: 1, 2, 3
        assert processed == [1, 2, 3]