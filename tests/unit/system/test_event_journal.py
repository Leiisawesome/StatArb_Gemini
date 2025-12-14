"""
Tests for EventJournal
======================

Tests cover:
- Event creation and serialization
- Journal initialization and file operations
- All logging methods (bar, quote, signal, etc.)
- Thread safety
- Compression support
- Replay functionality
- Statistics and monitoring
- Sequence number management

Author: StatArb_Gemini Test Suite
"""

import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core_engine.system.event_journal import (
    EventJournal,
    JournalEvent,
    EventCategory,
)

class TestJournalEvent:
    """Tests for JournalEvent dataclass."""

    def test_initialization(self):
        """Test event initialization."""
        timestamp = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        event = JournalEvent(
            event_id="test-00000001",
            sequence=1,
            timestamp=timestamp,
            category=EventCategory.MARKET_DATA,
            event_type="bar",
            symbol="AAPL",
            data={"close": 150.0},
            metadata={"source": "test"}
        )

        assert event.event_id == "test-00000001"
        assert event.sequence == 1
        assert event.timestamp == timestamp
        assert event.category == EventCategory.MARKET_DATA
        assert event.event_type == "bar"
        assert event.symbol == "AAPL"
        assert event.data == {"close": 150.0}
        assert event.metadata == {"source": "test"}

    def test_to_dict(self):
        """Test serialization to dictionary."""
        timestamp = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        event = JournalEvent(
            event_id="test-00000001",
            sequence=1,
            timestamp=timestamp,
            category=EventCategory.MARKET_DATA,
            event_type="bar",
            symbol="AAPL",
            data={"close": 150.0},
        )

        data = event.to_dict()

        expected = {
            'event_id': 'test-00000001',
            'sequence': 1,
            'timestamp': '2024-01-15T09:30:00+00:00',
            'category': 'MARKET_DATA',
            'event_type': 'bar',
            'symbol': 'AAPL',
            'data': {'close': 150.0},
            'metadata': {},
        }

        assert data == expected

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            'event_id': 'test-00000001',
            'sequence': 1,
            'timestamp': '2024-01-15T09:30:00+00:00',
            'category': 'MARKET_DATA',
            'event_type': 'bar',
            'symbol': 'AAPL',
            'data': {'close': 150.0},
            'metadata': {'source': 'test'},
        }

        event = JournalEvent.from_dict(data)

        assert event.event_id == "test-00000001"
        assert event.sequence == 1
        assert event.timestamp == datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        assert event.category == EventCategory.MARKET_DATA
        assert event.event_type == "bar"
        assert event.symbol == "AAPL"
        assert event.data == {"close": 150.0}
        assert event.metadata == {"source": "test"}

    def test_round_trip_serialization(self):
        """Test that to_dict/from_dict is reversible."""
        original = JournalEvent(
            event_id="test-00000001",
            sequence=1,
            timestamp=datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc),
            category=EventCategory.SIGNAL,
            event_type="signal_generated",
            symbol="AAPL",
            data={"action": "BUY", "confidence": 0.8},
            metadata={"model_version": "1.0"}
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = JournalEvent.from_dict(data)

        assert restored == original

class TestEventJournal:
    """Tests for EventJournal."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for journal files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def journal(self, temp_dir):
        """Create a test journal."""
        return EventJournal(
            session_id="test-session-001",
            output_dir=str(temp_dir),
            compress=False,
            buffer_size=5,  # Small buffer for testing
        )

    def test_initialization(self, temp_dir):
        """Test journal initialization."""
        journal = EventJournal(
            session_id="test-session-001",
            output_dir=str(temp_dir),
            compress=True,
        )

        assert journal._session_id == "test-session-001"
        assert journal._output_dir == temp_dir
        assert journal._compress is True
        assert journal._sequence == 0
        assert journal._buffer == []
        assert journal._file is not None

        # Check file was created
        expected_path = temp_dir / "test-session-001.jsonl.gz"
        assert expected_path.exists()

        journal.close()

    def test_initialization_uncompressed(self, temp_dir):
        """Test journal initialization without compression."""
        journal = EventJournal(
            session_id="test-session-002",
            output_dir=str(temp_dir),
            compress=False,
        )

        expected_path = temp_dir / "test-session-002.jsonl"
        assert expected_path.exists()

        journal.close()

    def test_log_bar(self, journal):
        """Test logging market data bars."""
        bar_data = {
            "timestamp": "2024-01-15T09:30:00Z",
            "open": 149.0,
            "high": 151.0,
            "low": 148.5,
            "close": 150.0,
            "volume": 1000000
        }

        journal.log_bar("AAPL", bar_data)

        # Should be buffered
        assert len(journal._buffer) == 1

        event = journal._buffer[0]
        assert event.category == EventCategory.MARKET_DATA
        assert event.event_type == "bar"
        assert event.symbol == "AAPL"
        assert event.data == bar_data
        assert event.sequence == 1

    def test_log_quote(self, journal):
        """Test logging quotes."""
        quote_data = {
            "bid": 149.95,
            "ask": 150.05,
            "bid_size": 100,
            "ask_size": 200
        }

        journal.log_quote("AAPL", quote_data)

        assert len(journal._buffer) == 1
        event = journal._buffer[0]
        assert event.category == EventCategory.MARKET_DATA
        assert event.event_type == "quote"
        assert event.symbol == "AAPL"
        assert event.data == quote_data

    def test_log_features(self, journal):
        """Test logging computed features."""
        features = {
            "rsi": 65.5,
            "macd": 0.23,
            "bb_upper": 152.0,
            "bb_lower": 148.0
        }
        bar_timestamp = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        journal.log_features("AAPL", features, bar_timestamp)

        assert len(journal._buffer) == 1
        event = journal._buffer[0]
        assert event.category == EventCategory.DERIVED_STATE
        assert event.event_type == "features"
        assert event.symbol == "AAPL"
        assert event.data == features
        assert event.metadata["bar_timestamp"] == bar_timestamp.isoformat()

    def test_log_regime(self, journal):
        """Test logging regime detection."""
        journal.log_regime(
            regime="bull_trend",
            confidence=0.85,
            volatility_regime="low",
            details={"duration": 300}
        )

        assert len(journal._buffer) == 1
        event = journal._buffer[0]
        assert event.category == EventCategory.DERIVED_STATE
        assert event.event_type == "regime"
        assert event.data["regime"] == "bull_trend"
        assert event.data["confidence"] == 0.85
        assert event.data["volatility_regime"] == "low"
        assert event.data["duration"] == 300

    def test_log_signal(self, journal):
        """Test logging trading signals."""
        signal_data = {
            "action": "BUY",
            "quantity": 100,
            "confidence": 0.78,
            "reason": "RSI oversold"
        }

        journal.log_signal("AAPL", signal_data, signal_id="sig-001")

        assert len(journal._buffer) == 1
        event = journal._buffer[0]
        assert event.category == EventCategory.SIGNAL
        assert event.event_type == "signal_generated"
        assert event.symbol == "AAPL"
        assert event.data == signal_data
        assert event.event_id == "sig-001"

    def test_log_risk_decision(self, journal):
        """Test logging risk authorization decisions."""
        authorization = {
            "approved": True,
            "max_quantity": 100,
            "risk_checks": ["position_limit", "volatility"]
        }

        journal.log_risk_decision(
            symbol="AAPL",
            decision="approved",
            authorization=authorization,
            reasons=["All checks passed"]
        )

        assert len(journal._buffer) == 1
        event = journal._buffer[0]
        assert event.category == EventCategory.RISK_DECISION
        assert event.event_type == "authorization_approved"
        assert event.symbol == "AAPL"
        assert event.data["decision"] == "approved"
        assert event.data["authorization"] == authorization
        assert event.data["reasons"] == ["All checks passed"]

    def test_log_order(self, journal):
        """Test logging order lifecycle events."""
        order_data = {
            "quantity": 100,
            "price": 150.0,
            "order_type": "limit"
        }

        journal.log_order("AAPL", "order-001", "submit", order_data)

        assert len(journal._buffer) == 1
        event = journal._buffer[0]
        assert event.category == EventCategory.ORDER
        assert event.event_type == "order_submit"
        assert event.symbol == "AAPL"
        assert event.data["order_id"] == "order-001"
        assert event.data["quantity"] == 100

    def test_log_fill(self, journal):
        """Test logging execution fills."""
        journal.log_fill(
            symbol="AAPL",
            order_id="order-001",
            fill_id="fill-001",
            quantity=50,
            price=150.0,
            commission=0.5
        )

        assert len(journal._buffer) == 1
        event = journal._buffer[0]
        assert event.category == EventCategory.FILL
        assert event.event_type == "fill"
        assert event.symbol == "AAPL"
        assert event.event_id == "fill-001"
        assert event.data["order_id"] == "order-001"
        assert event.data["quantity"] == 50
        assert event.data["price"] == 150.0
        assert event.data["commission"] == 0.5

    def test_log_position(self, journal):
        """Test logging position updates."""
        position_data = {
            "quantity": 150,
            "avg_price": 149.5,
            "unrealized_pnl": 75.0
        }

        journal.log_position("AAPL", "update", position_data)

        assert len(journal._buffer) == 1
        event = journal._buffer[0]
        assert event.category == EventCategory.POSITION
        assert event.event_type == "position_update"
        assert event.symbol == "AAPL"
        assert event.data == position_data

    def test_log_system(self, journal):
        """Test logging system events."""
        system_data = {
            "component": "risk_manager",
            "status": "initialized"
        }

        journal.log_system("startup", system_data)

        assert len(journal._buffer) == 1
        event = journal._buffer[0]
        assert event.category == EventCategory.SYSTEM
        assert event.event_type == "startup"
        assert event.data == system_data

    def test_buffer_auto_flush(self, journal):
        """Test automatic buffer flushing when full."""
        # Log events up to buffer size
        for i in range(5):  # buffer_size = 5
            journal.log_bar("AAPL", {"close": 150.0 + i})

        # Buffer should be empty after auto-flush
        assert len(journal._buffer) == 0

        # Check stats
        stats = journal.get_stats()
        assert stats['flushes'] == 1

    def test_manual_flush(self, journal):
        """Test manual buffer flushing."""
        journal.log_bar("AAPL", {"close": 150.0})
        journal.log_bar("AAPL", {"close": 151.0})

        assert len(journal._buffer) == 2

        journal.flush()

        assert len(journal._buffer) == 0

        stats = journal.get_stats()
        assert stats['flushes'] == 1
        assert stats['events_logged'] == 2

    def test_close_flushes_buffer(self, journal):
        """Test that close() flushes any remaining buffer."""
        journal.log_bar("AAPL", {"close": 150.0})

        assert len(journal._buffer) == 1

        journal.close()

        assert len(journal._buffer) == 0
        assert journal._file is None

    def test_context_manager(self, temp_dir):
        """Test using journal as context manager."""
        with EventJournal("test-context", str(temp_dir)) as journal:
            journal.log_bar("AAPL", {"close": 150.0})
            assert len(journal._buffer) == 1

        # Should be closed and flushed
        assert journal._file is None

    def test_thread_safety(self, temp_dir):
        """Test thread-safe logging."""
        journal = EventJournal("test-thread", str(temp_dir), buffer_size=100)

        def log_events(thread_id: int):
            for i in range(10):
                journal.log_bar("AAPL", {"close": 150.0 + i, "thread": thread_id})

        threads = []
        for i in range(3):
            t = threading.Thread(target=log_events, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All events should be logged
        stats = journal.get_stats()
        assert stats['events_logged'] == 30

        journal.close()

    def test_sequence_numbering(self, journal):
        """Test that events get sequential sequence numbers."""
        journal.log_bar("AAPL", {"close": 150.0})
        journal.log_quote("AAPL", {"bid": 149.5})
        journal.log_signal("AAPL", {"action": "BUY"})

        journal.flush()  # Ensure all are written

        # Read back and check sequences
        events = EventJournal.read_journal(str(journal._file_path))

        assert len(events) == 3
        assert events[0].sequence == 1
        assert events[1].sequence == 2
        assert events[2].sequence == 3

    def test_read_journal_uncompressed(self, temp_dir):
        """Test reading uncompressed journal files."""
        # Create and populate journal
        journal = EventJournal("test-read", str(temp_dir), compress=False)
        journal.log_bar("AAPL", {"close": 150.0})
        journal.log_quote("AAPL", {"bid": 149.5})
        journal.close()

        # Read it back
        events = EventJournal.read_journal(str(journal._file_path))

        assert len(events) == 2
        assert events[0].event_type == "bar"
        assert events[0].symbol == "AAPL"
        assert events[1].event_type == "quote"

    def test_read_journal_compressed(self, temp_dir):
        """Test reading compressed journal files."""
        # Create and populate compressed journal
        journal = EventJournal("test-read-gz", str(temp_dir), compress=True)
        journal.log_bar("AAPL", {"close": 150.0})
        journal.log_system("test", {"data": "test"})
        journal.close()

        # Read it back
        events = EventJournal.read_journal(str(journal._file_path))

        assert len(events) == 2
        assert events[0].event_type == "bar"
        assert events[1].event_type == "test"

    def test_get_stats(self, journal):
        """Test statistics reporting."""
        journal.log_bar("AAPL", {"close": 150.0})
        journal.log_quote("AAPL", {"bid": 149.5})
        journal.flush()

        stats = journal.get_stats()

        assert stats['events_logged'] == 2
        assert stats['flushes'] == 1
        assert stats['session_id'] == "test-session-001"
        assert stats['sequence'] == 2
        assert stats['buffer_size'] == 0

    def test_get_restore_sequence(self, journal):
        """Test sequence number checkpointing."""
        journal.log_bar("AAPL", {"close": 150.0})
        journal.log_quote("AAPL", {"bid": 149.5})

        sequence = journal.get_sequence()
        assert sequence == 2

        # Create new journal and restore sequence
        new_journal = EventJournal("test-restore", str(journal._output_dir))
        new_journal.restore_sequence(sequence)

        assert new_journal._sequence == 2

        new_journal.close()

    def test_event_id_generation(self, journal):
        """Test automatic event ID generation."""
        journal.log_bar("AAPL", {"close": 150.0})

        event = journal._buffer[0]
        expected_id = f"test-session-001:{1:08d}"
        assert event.event_id == expected_id

    def test_custom_event_id(self, journal):
        """Test custom event ID usage."""
        journal.log_signal("AAPL", {"action": "BUY"}, signal_id="custom-sig-001")

        event = journal._buffer[0]
        assert event.event_id == "custom-sig-001"