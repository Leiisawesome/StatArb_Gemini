"""
Unit tests for Streaming Signal Manager.

Tests the StreamingSignalManager class for signal lifecycle management.
"""

import pytest
import threading
from datetime import datetime, timezone
from unittest.mock import Mock

from core_engine.processing.signals.streaming_manager import (
    StreamingSignalManager,
    BarPolicy,
    BarPolicyPhase,
    EnhancedTradingSignal,
    SignalValidationResult,
)

class TestStreamingSignalManager:
    """Test StreamingSignalManager class."""

    @pytest.fixture
    def signal_manager(self):
        """Create test signal manager instance."""
        return StreamingSignalManager(
            bar_policy=BarPolicy(),
            default_stop_loss_pct=0.02,
            max_stop_loss_pct=0.10,
            session_id="test_session"
        )

    @pytest.fixture
    def valid_signal(self):
        """Create a valid trading signal."""
        return EnhancedTradingSignal(
            symbol="AAPL",
            side="buy",
            requested_quantity=100.0,
            signal_strength=0.8,
            strategy_id="test_strategy",
            signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            arrival_price=150.0,
            stop_loss_pct=0.05,
        )

    def test_initialization(self):
        """Test signal manager initialization."""
        manager = StreamingSignalManager(
            bar_policy=BarPolicy(compute_on="bar_close", signal_on="bar_close", act_on="next_bar_open"),
            default_stop_loss_pct=0.03,
            max_stop_loss_pct=0.15,
            session_id="test_session"
        )

        assert manager._bar_policy.compute_on == "bar_close"
        assert manager._default_stop_pct == 0.03
        assert manager._max_stop_pct == 0.15
        assert manager._session_id == "test_session"
        assert manager._current_phase == BarPolicyPhase.AWAITING_BAR
        assert manager._current_bar_timestamp is None
        assert len(manager._pending_signals) == 0
        assert len(manager._handlers) == 0
        assert manager._signal_sequence == 0

        expected_stats = {
            'signals_generated': 0,
            'signals_validated': 0,
            'signals_rejected': 0,
            'signals_with_warnings': 0,
            'defaults_applied': 0,
        }
        assert manager._stats == expected_stats

    def test_initialization_defaults(self):
        """Test signal manager initialization with defaults."""
        manager = StreamingSignalManager()

        assert manager._bar_policy.compute_on == "bar_close"
        assert manager._default_stop_pct == 0.02
        assert manager._max_stop_pct == 0.10
        assert manager._session_id == "paper"

    def test_register_handler(self, signal_manager):
        """Test registering signal handlers."""
        handler1 = Mock()
        handler2 = Mock()

        signal_manager.register_handler(handler1)
        signal_manager.register_handler(handler2)

        assert handler1 in signal_manager._handlers
        assert handler2 in signal_manager._handlers

    def test_register_validation_handler(self, signal_manager):
        """Test registering validation handlers."""
        handler = Mock()

        signal_manager.register_validation_handler(handler)

        assert handler in signal_manager._validation_handlers

    def test_validate_signal_valid(self, signal_manager, valid_signal):
        """Test validation of a valid signal."""
        result = signal_manager.validate_signal(valid_signal)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.applied_defaults) == 0

        # Check stats updated
        assert signal_manager._stats['signals_validated'] == 1
        assert signal_manager._stats['signals_rejected'] == 0
        assert signal_manager._stats['signals_with_warnings'] == 0

    def test_validate_signal_missing_required_fields(self, signal_manager):
        """Test validation with missing required fields."""
        invalid_signal = EnhancedTradingSignal(
            symbol="",  # Missing symbol
            side="invalid",  # Invalid side
            requested_quantity=-100.0,  # Invalid quantity
            signal_strength=1.5,  # Invalid strength
            strategy_id="",  # Missing strategy_id
            signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            arrival_price=-10.0,  # Invalid price
        )

        result = signal_manager.validate_signal(invalid_signal)

        assert result.is_valid is False
        assert len(result.errors) >= 5  # Multiple errors
        assert "Missing required field: symbol" in result.errors
        assert "Invalid side: invalid, must be 'buy' or 'sell'" in result.errors
        assert "Invalid quantity: -100.0, must be positive" in result.errors
        assert "Missing required field: strategy_id" in result.errors
        assert "Invalid arrival_price: -10.0" in result.errors

        # Check stats
        assert signal_manager._stats['signals_validated'] == 1
        assert signal_manager._stats['signals_rejected'] == 1

    def test_validate_signal_apply_defaults(self, signal_manager):
        """Test validation with default stop application."""
        signal_no_stop = EnhancedTradingSignal(
            symbol="AAPL",
            side="buy",
            requested_quantity=100.0,
            signal_strength=0.8,
            strategy_id="test_strategy",
            signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            arrival_price=150.0,
            # No stop specified
        )

        result = signal_manager.validate_signal(signal_no_stop, apply_defaults=True)

        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "applied default stop_loss_pct" in result.warnings[0]
        assert result.applied_defaults['stop_loss_pct'] == 0.02
        assert signal_no_stop.stop_loss_pct == 0.02

        # Check stats
        assert signal_manager._stats['defaults_applied'] == 1

    def test_validate_signal_no_defaults(self, signal_manager):
        """Test validation without applying defaults."""
        signal_no_stop = EnhancedTradingSignal(
            symbol="AAPL",
            side="buy",
            requested_quantity=100.0,
            signal_strength=0.8,
            strategy_id="test_strategy",
            signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            arrival_price=150.0,
        )

        result = signal_manager.validate_signal(signal_no_stop, apply_defaults=False)

        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "No stop specification provided" in result.warnings[0]
        assert signal_no_stop.stop_loss_pct is None

    def test_validate_signal_stop_price_validation(self, signal_manager):
        """Test stop price validation for buy/sell sides."""
        # Invalid buy signal (stop above arrival)
        buy_signal = EnhancedTradingSignal(
            symbol="AAPL",
            side="buy",
            requested_quantity=100.0,
            signal_strength=0.8,
            strategy_id="test_strategy",
            signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            arrival_price=150.0,
            stop_price=160.0,  # Above arrival for buy
        )

        result = signal_manager.validate_signal(buy_signal)
        assert result.is_valid is False
        assert "Stop price 160.0 is above arrival 150.0 for BUY" in result.errors

        # Invalid sell signal (stop below arrival)
        sell_signal = EnhancedTradingSignal(
            symbol="AAPL",
            side="sell",
            requested_quantity=100.0,
            signal_strength=0.8,
            strategy_id="test_strategy",
            signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            arrival_price=150.0,
            stop_price=140.0,  # Below arrival for sell
        )

        result = signal_manager.validate_signal(sell_signal)
        assert result.is_valid is False
        assert "Stop price 140.0 is below arrival 150.0 for SELL" in result.errors

    def test_validate_signal_wide_stop_warning(self, signal_manager):
        """Test warning for unusually wide stops."""
        signal = EnhancedTradingSignal(
            symbol="AAPL",
            side="buy",
            requested_quantity=100.0,
            signal_strength=0.8,
            strategy_id="test_strategy",
            signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            arrival_price=150.0,
            stop_loss_pct=0.15,  # Above max_stop_pct (0.10)
        )

        result = signal_manager.validate_signal(signal)

        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "Unusually wide stop: 15.0% > 10.0%" in result.warnings[0]

    def test_resolve_stop_with_stop_price(self, signal_manager, valid_signal):
        """Test stop resolution with explicit stop price."""
        valid_signal.stop_price = 145.0
        valid_signal.stop_loss_pct = 0.05  # Should be ignored

        stop_price = signal_manager.resolve_stop(valid_signal)

        assert stop_price == 145.0

    def test_resolve_stop_with_stop_pct_buy(self, signal_manager, valid_signal):
        """Test stop resolution with stop percentage for buy."""
        valid_signal.stop_price = None
        valid_signal.stop_loss_pct = 0.05
        valid_signal.arrival_price = 150.0
        valid_signal.side = "buy"

        stop_price = signal_manager.resolve_stop(valid_signal)

        assert stop_price == 142.5  # 150 * (1 - 0.05)

    def test_resolve_stop_with_stop_pct_sell(self, signal_manager, valid_signal):
        """Test stop resolution with stop percentage for sell."""
        valid_signal.stop_price = None
        valid_signal.stop_loss_pct = 0.05
        valid_signal.arrival_price = 150.0
        valid_signal.side = "sell"

        stop_price = signal_manager.resolve_stop(valid_signal)

        assert stop_price == 157.5  # 150 * (1 + 0.05)

    def test_resolve_stop_default_stop(self, signal_manager, valid_signal):
        """Test stop resolution with default stop."""
        valid_signal.stop_price = None
        valid_signal.stop_loss_pct = None
        valid_signal.arrival_price = 150.0
        valid_signal.side = "buy"

        stop_price = signal_manager.resolve_stop(valid_signal)

        assert stop_price == 147.0  # 150 * (1 - 0.02)

    def test_on_bar_close(self, signal_manager):
        """Test bar close event handling."""
        timestamp = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)

        signal_manager.on_bar_close(timestamp)

        assert signal_manager._current_phase == BarPolicyPhase.COMPUTING
        assert signal_manager._current_bar_timestamp == timestamp

    def test_on_computation_complete(self, signal_manager):
        """Test computation complete event handling."""
        signal_manager.on_computation_complete()

        assert signal_manager._current_phase == BarPolicyPhase.GENERATING_SIGNALS

    def test_submit_signal_valid(self, signal_manager, valid_signal):
        """Test submitting a valid signal."""
        # Set up bar context
        bar_timestamp = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        signal_manager.on_bar_close(bar_timestamp)

        signal_id = signal_manager.submit_signal(valid_signal)

        assert signal_id is not None
        assert "test_strategy:AAPL:2023-01-01T10:00:00:0001" in signal_id
        assert valid_signal.signal_id == signal_id
        assert valid_signal.bar_timestamp == bar_timestamp

        # Check signal queued
        assert len(signal_manager._pending_signals) == 1
        assert signal_manager._pending_signals[0] == valid_signal

        # Check stats
        assert signal_manager._stats['signals_generated'] == 1

    def test_submit_signal_invalid(self, signal_manager):
        """Test submitting an invalid signal."""
        invalid_signal = EnhancedTradingSignal(
            symbol="",  # Invalid
            side="buy",
            requested_quantity=100.0,
            signal_strength=0.8,
            strategy_id="test_strategy",
            signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            arrival_price=150.0,
        )

        signal_id = signal_manager.submit_signal(invalid_signal)

        assert signal_id is None
        assert len(signal_manager._pending_signals) == 0
        assert signal_manager._stats['signals_generated'] == 0

    def test_submit_signal_no_validation(self, signal_manager):
        """Test submitting signal without validation."""
        invalid_signal = EnhancedTradingSignal(
            symbol="",  # Would be invalid
            side="buy",
            requested_quantity=100.0,
            signal_strength=0.8,
            strategy_id="test_strategy",
            signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            arrival_price=150.0,
        )

        signal_id = signal_manager.submit_signal(invalid_signal, validate=False)

        assert signal_id is not None
        assert len(signal_manager._pending_signals) == 1

    def test_on_bar_open_with_pending_signals(self, signal_manager, valid_signal):
        """Test bar open event with pending signals."""
        # Submit a signal
        signal_manager.submit_signal(valid_signal, validate=False)

        # Register a handler
        handler = Mock()
        signal_manager.register_handler(handler)

        # Trigger bar open
        signals = signal_manager.on_bar_open()

        assert len(signals) == 1
        assert signals[0] == valid_signal
        assert len(signal_manager._pending_signals) == 0
        assert signal_manager._current_phase == BarPolicyPhase.AWAITING_BAR

        # Check handler was called
        handler.assert_called_once_with(valid_signal)

    def test_on_bar_open_no_pending_signals(self, signal_manager):
        """Test bar open event with no pending signals."""
        signals = signal_manager.on_bar_open()

        assert len(signals) == 0
        assert signal_manager._current_phase == BarPolicyPhase.AWAITING_BAR

    def test_get_pending_signals(self, signal_manager, valid_signal):
        """Test getting pending signals without clearing."""
        signal_manager.submit_signal(valid_signal, validate=False)

        pending = signal_manager.get_pending_signals()

        assert len(pending) == 1
        assert pending[0] == valid_signal
        assert len(signal_manager._pending_signals) == 1  # Still pending

    def test_clear_pending_signals(self, signal_manager, valid_signal):
        """Test clearing pending signals."""
        signal_manager.submit_signal(valid_signal, validate=False)
        signal_manager.submit_signal(valid_signal, validate=False)

        count = signal_manager.clear_pending_signals()

        assert count == 2
        assert len(signal_manager._pending_signals) == 0

    def test_get_current_phase(self, signal_manager):
        """Test getting current phase."""
        assert signal_manager.get_current_phase() == BarPolicyPhase.AWAITING_BAR

        signal_manager.on_bar_close(datetime.now(timezone.utc))
        assert signal_manager.get_current_phase() == BarPolicyPhase.COMPUTING

    def test_get_bar_policy(self, signal_manager):
        """Test getting bar policy."""
        policy = signal_manager.get_bar_policy()

        assert isinstance(policy, BarPolicy)
        assert policy.compute_on == "bar_close"

    def test_get_stats(self, signal_manager):
        """Test getting statistics."""
        stats = signal_manager.get_stats()

        assert isinstance(stats, dict)
        assert 'signals_generated' in stats
        assert 'signals_validated' in stats

    def test_reset_stats(self, signal_manager):
        """Test resetting statistics."""
        # Modify stats
        signal_manager._stats['signals_generated'] = 10
        signal_manager._stats['signals_validated'] = 5

        signal_manager.reset_stats()

        assert signal_manager._stats['signals_generated'] == 0
        assert signal_manager._stats['signals_validated'] == 0

    def test_get_sequence_counter(self, signal_manager, valid_signal):
        """Test getting sequence counter."""
        initial = signal_manager.get_sequence_counter()
        assert initial == 0

        signal_manager.submit_signal(valid_signal, validate=False)

        current = signal_manager.get_sequence_counter()
        assert current == 1

    def test_restore_sequence_counter(self, signal_manager):
        """Test restoring sequence counter."""
        signal_manager.restore_sequence_counter(42)

        assert signal_manager._signal_sequence == 42

        # Next signal should use 43
        valid_signal = EnhancedTradingSignal(
            symbol="AAPL",
            side="buy",
            requested_quantity=100.0,
            signal_strength=0.8,
            strategy_id="test_strategy",
            signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
            arrival_price=150.0,
        )

        signal_manager.submit_signal(valid_signal, validate=False)
        assert "0043" in valid_signal.signal_id

    def test_thread_safety(self, signal_manager):
        """Test thread safety of signal operations."""
        results = []
        errors = []

        def worker(thread_id):
            try:
                for i in range(10):
                    signal = EnhancedTradingSignal(
                        symbol=f"SYMBOL_{thread_id}",
                        side="buy",
                        requested_quantity=100.0,
                        signal_strength=0.8,
                        strategy_id=f"strategy_{thread_id}",
                        signal_timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
                        arrival_price=150.0,
                    )

                    signal_id = signal_manager.submit_signal(signal, validate=False)
                    results.append(signal_id)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Check results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 50  # 5 threads * 10 signals each

        # Check all signal IDs are unique
        assert len(set(results)) == 50

        # Check sequence counter
        assert signal_manager.get_sequence_counter() == 50

    def test_validation_handler_called(self, signal_manager, valid_signal):
        """Test that validation handlers are called."""
        handler = Mock()
        signal_manager.register_validation_handler(handler)

        signal_manager.validate_signal(valid_signal)

        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert isinstance(call_args, SignalValidationResult)
        assert call_args.is_valid is True

    def test_signal_handler_error_handling(self, signal_manager, valid_signal):
        """Test error handling in signal handlers."""
        # Register a handler that raises an exception
        def failing_handler(signal):
            raise Exception("Handler error")

        signal_manager.register_handler(failing_handler)
        signal_manager.submit_signal(valid_signal, validate=False)

        # Should not raise exception, just log error
        signals = signal_manager.on_bar_open()

        assert len(signals) == 1

    def test_validation_handler_error_handling(self, signal_manager, valid_signal):
        """Test error handling in validation handlers."""
        def failing_handler(result):
            raise Exception("Validation handler error")

        signal_manager.register_validation_handler(failing_handler)

        # Should not raise exception, just log error
        result = signal_manager.validate_signal(valid_signal)

        assert result.is_valid is True