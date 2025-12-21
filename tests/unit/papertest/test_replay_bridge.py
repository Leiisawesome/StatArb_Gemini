"""
Unit tests for papertest.engine.replay_bridge
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

from core_engine.data.feeds.adapters import FeedMessage
from core_engine.system.event_dispatcher import EventType

from papertest.engine.replay_bridge import ReplayToDispatcherBridge, BridgeStats


class TestBridgeStats:
    def test_initialization(self):
        """Test BridgeStats initialization"""
        stats = BridgeStats()
        assert stats.bars_enqueued == 0
        assert stats.quotes_enqueued == 0
        assert stats.trades_enqueued == 0
        assert stats.dropped == 0


class TestReplayToDispatcherBridge:
    def test_initialization(self):
        """Test bridge initialization"""
        dispatcher = Mock()
        id_generator = Mock()

        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator
        )

        assert bridge._dispatcher == dispatcher
        assert bridge._ids == id_generator
        assert bridge._timeout is None
        assert bridge._start_at_timestamp is None
        assert bridge._skipped_before_start == 0
        assert bridge._stop_after_bars is None
        assert bridge._stop_at_timestamp is None
        assert bridge._stop_callback is None
        assert bridge._stop_requested is False

    def test_initialization_with_options(self):
        """Test bridge initialization with all options"""
        dispatcher = Mock()
        id_generator = Mock()
        stop_callback = Mock()
        start_ts = datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc)

        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator,
            enqueue_timeout=1.0,
            start_at_timestamp=start_ts,
            stop_after_bars=100,
            stop_at_timestamp=start_ts,
            stop_callback=stop_callback
        )

        assert bridge._timeout == 1.0
        assert bridge._start_at_timestamp == start_ts
        assert bridge._stop_after_bars == 100
        assert bridge._stop_at_timestamp == start_ts
        assert bridge._stop_callback == stop_callback

    def test_stats_property(self):
        """Test stats property returns correct dict"""
        dispatcher = Mock()
        id_generator = Mock()

        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator
        )

        # Manually set some stats
        bridge._stats.bars_enqueued = 10
        bridge._stats.quotes_enqueued = 5
        bridge._stats.trades_enqueued = 3
        bridge._stats.dropped = 2
        bridge._skipped_before_start = 7

        stats = bridge.stats
        expected = {
            "bars_enqueued": 10,
            "quotes_enqueued": 5,
            "trades_enqueued": 3,
            "dropped": 2,
            "skipped_before_start": 7
        }
        assert stats == expected

    def test_map_type_bar(self):
        """Test mapping bar message type"""
        result = ReplayToDispatcherBridge._map_type("bar")
        assert result == EventType.BAR

    def test_map_type_quote(self):
        """Test mapping quote message type"""
        result = ReplayToDispatcherBridge._map_type("quote")
        assert result == EventType.QUOTE

    def test_map_type_trade(self):
        """Test mapping trade message type"""
        result = ReplayToDispatcherBridge._map_type("trade")
        assert result == EventType.TRADE

    def test_map_type_unknown(self):
        """Test mapping unknown message type"""
        result = ReplayToDispatcherBridge._map_type("unknown")
        assert result is None

    def test_map_type_case_insensitive(self):
        """Test mapping is case insensitive"""
        result = ReplayToDispatcherBridge._map_type("BAR")
        assert result == EventType.BAR

    def test_normalize_payload(self):
        """Test payload normalization"""
        msg = FeedMessage(
            message_type="bar",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
            data={"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000}
        )

        result = ReplayToDispatcherBridge._normalize_payload(msg)

        expected = {
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 1000,
            "symbol": "AAPL",
            "timestamp": datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc)
        }
        assert result == expected

    def test_on_feed_message_bar(self):
        """Test handling bar message"""
        dispatcher = Mock()
        id_generator = Mock()
        id_generator.generate_event_id.return_value = "test_event_id"

        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator
        )

        msg = FeedMessage(
            message_type="bar",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
            data={"close": 100.0}
        )

        dispatcher.enqueue.return_value = True

        bridge.on_feed_message(msg)

        # Check that enqueue was called
        dispatcher.enqueue.assert_called_once()
        call_args = dispatcher.enqueue.call_args
        assert call_args[1]["event_type"] == EventType.BAR
        assert call_args[1]["symbol"] == "AAPL"
        assert call_args[1]["event_id"] == "test_event_id"

        # Check stats
        assert bridge._stats.bars_enqueued == 1

    def test_on_feed_message_quote(self):
        """Test handling quote message"""
        dispatcher = Mock()
        id_generator = Mock()
        id_generator.generate_event_id.return_value = "test_event_id"

        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator
        )

        msg = FeedMessage(
            message_type="quote",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
            data={"bid": 99.9, "ask": 100.1}
        )

        dispatcher.enqueue.return_value = True

        bridge.on_feed_message(msg)

        dispatcher.enqueue.assert_called_once()
        assert bridge._stats.quotes_enqueued == 1

    def test_on_feed_message_trade(self):
        """Test handling trade message"""
        dispatcher = Mock()
        id_generator = Mock()
        id_generator.generate_event_id.return_value = "test_event_id"

        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator
        )

        msg = FeedMessage(
            message_type="trade",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
            data={"price": 100.0, "size": 100}
        )

        dispatcher.enqueue.return_value = True

        bridge.on_feed_message(msg)

        dispatcher.enqueue.assert_called_once()
        assert bridge._stats.trades_enqueued == 1

    def test_on_feed_message_unknown_type(self):
        """Test handling unknown message type"""
        dispatcher = Mock()
        id_generator = Mock()

        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator
        )

        msg = FeedMessage(
            message_type="unknown",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
            data={}
        )

        bridge.on_feed_message(msg)

        # Should not call enqueue for unknown types
        dispatcher.enqueue.assert_not_called()
        assert bridge._stats.dropped == 0  # Not counted as dropped

    def test_on_feed_message_enqueue_fails(self):
        """Test handling enqueue failure"""
        dispatcher = Mock()
        id_generator = Mock()
        id_generator.generate_event_id.return_value = "test_event_id"

        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator
        )

        msg = FeedMessage(
            message_type="bar",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
            data={"close": 100.0}
        )

        dispatcher.enqueue.return_value = False

        bridge.on_feed_message(msg)

        dispatcher.enqueue.assert_called_once()
        assert bridge._stats.dropped == 1

    def test_on_feed_message_skip_before_start(self):
        """Test skipping messages before start timestamp"""
        dispatcher = Mock()
        id_generator = Mock()

        start_ts = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator,
            start_at_timestamp=start_ts
        )

        # Message before start time
        msg = FeedMessage(
            message_type="bar",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
            data={"close": 100.0}
        )

        bridge.on_feed_message(msg)

        # Should not enqueue
        dispatcher.enqueue.assert_not_called()
        assert bridge._skipped_before_start == 1

    def test_on_feed_message_process_at_start(self):
        """Test processing messages at start timestamp"""
        dispatcher = Mock()
        id_generator = Mock()
        id_generator.generate_event_id.return_value = "test_event_id"

        start_ts = datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc)
        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator,
            start_at_timestamp=start_ts
        )

        msg = FeedMessage(
            message_type="bar",
            symbol="AAPL",
            timestamp=start_ts,
            data={"close": 100.0}
        )

        dispatcher.enqueue.return_value = True

        bridge.on_feed_message(msg)

        dispatcher.enqueue.assert_called_once()
        assert bridge._skipped_before_start == 0

    def test_maybe_stop_after_bars(self):
        """Test stopping after specified number of bars"""
        dispatcher = Mock()
        id_generator = Mock()
        id_generator.generate_event_id.return_value = "test_event_id"
        stop_callback = Mock()

        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator,
            stop_after_bars=2,
            stop_callback=stop_callback
        )

        msg = FeedMessage(
            message_type="bar",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
            data={"close": 100.0}
        )

        dispatcher.enqueue.return_value = True

        # First bar
        bridge.on_feed_message(msg)
        assert not bridge._stop_requested
        stop_callback.assert_not_called()

        # Second bar - should trigger stop
        bridge.on_feed_message(msg)
        assert bridge._stop_requested
        stop_callback.assert_called_once()

        # Third bar - should not call again
        bridge.on_feed_message(msg)
        assert stop_callback.call_count == 1

    def test_maybe_stop_at_timestamp(self):
        """Test stopping at specified timestamp"""
        dispatcher = Mock()
        id_generator = Mock()
        id_generator.generate_event_id.return_value = "test_event_id"
        stop_callback = Mock()

        stop_ts = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator,
            stop_at_timestamp=stop_ts,
            stop_callback=stop_callback
        )

        # Bar before stop time
        msg1 = FeedMessage(
            message_type="bar",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
            data={"close": 100.0}
        )

        dispatcher.enqueue.return_value = True
        bridge.on_feed_message(msg1)
        assert not bridge._stop_requested

        # Bar at stop time
        msg2 = FeedMessage(
            message_type="bar",
            symbol="AAPL",
            timestamp=stop_ts,
            data={"close": 100.0}
        )

        bridge.on_feed_message(msg2)
        assert bridge._stop_requested
        stop_callback.assert_called_once()

    def test_timestamp_normalization(self):
        """Test that timestamps without timezone are normalized"""
        dispatcher = Mock()
        id_generator = Mock()
        id_generator.generate_event_id.return_value = "test_event_id"

        bridge = ReplayToDispatcherBridge(
            dispatcher=dispatcher,
            id_generator=id_generator
        )

        # Message with naive timestamp
        msg = FeedMessage(
            message_type="bar",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30),  # No timezone
            data={"close": 100.0}
        )

        dispatcher.enqueue.return_value = True

        bridge.on_feed_message(msg)

        # Should have been normalized to UTC
        call_args = dispatcher.enqueue.call_args
        market_ts = call_args[1]["market_timestamp"]
        assert market_ts.tzinfo == timezone.utc