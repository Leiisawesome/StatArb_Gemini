"""
DeterministicEventDispatcher - Ordered Event Processing
========================================================

Single-threaded deterministic event dispatcher with:
- Priority queue ordered by (market_timestamp, sequence_number)
- Bounded queues with explicit backpressure policy
- Reproducible event ordering across runs

Backpressure Policy (from plan Section 2.2):
- Bar: Never drop; slow ingestion if behind
- Quote/Trade: Conflate (keep latest per symbol)

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 1)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import (
    Any, Callable, Dict, List, Optional
)
import heapq
import threading
import logging
from collections import defaultdict

from .time_source import TimeSource

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Types of events processed by the dispatcher."""
    BAR = auto()          # OHLCV bar - never drop
    QUOTE = auto()        # BBO quote - conflate per symbol
    TRADE = auto()        # Trade tick - conflate per symbol
    SIGNAL = auto()       # Trading signal
    ORDER = auto()        # Order lifecycle event
    FILL = auto()         # Fill/execution event
    REGIME = auto()       # Regime change event
    SYSTEM = auto()       # System event (circuit breaker, etc.)

class BackpressurePolicy(Enum):
    """How to handle queue overflow."""
    BLOCK = auto()        # Block producer until space available
    DROP_OLDEST = auto()  # Drop oldest events (FIFO overflow)
    CONFLATE = auto()     # Keep only latest per key (symbol)

@dataclass(order=True)
class PrioritizedEvent:
    """
    Event wrapper for priority queue ordering.

    Ordered by (market_timestamp, priority, sequence_number) for determinism.
    Priority is used to guarantee causal ordering within the same market timestamp
    (e.g., process FILLs before BARs so position state is updated before generating new signals).
    """
    market_timestamp: datetime = field(compare=True)
    priority: int = field(compare=True)
    sequence_number: int = field(compare=True)
    event_type: EventType = field(compare=False)
    symbol: Optional[str] = field(compare=False, default=None)
    payload: Any = field(compare=False, default=None)
    event_id: Optional[str] = field(compare=False, default=None)

    def __post_init__(self):
        # Ensure timezone-aware timestamp
        if self.market_timestamp.tzinfo is None:
            self.market_timestamp = self.market_timestamp.replace(tzinfo=timezone.utc)

EventHandler = Callable[[PrioritizedEvent], None]

class DeterministicEventDispatcher:
    """
    Single-threaded deterministic event dispatcher.

    Guarantees:
    - Events processed in strict (timestamp, sequence) order
    - No concurrent handler execution (single-threaded processing)
    - Reproducible runs given same input sequence
    - Bounded memory with configurable backpressure

    Thread Safety:
    - enqueue() is thread-safe (multiple producers)
    - process_next() / process_all() must be called from single thread
    """

    def __init__(
        self,
        time_source: TimeSource,
        max_queue_size: int = 10000,
        bar_queue_size: int = 1000,
        conflate_quotes: bool = True
    ):
        """
        Initialize the dispatcher.

        Args:
            time_source: TimeSource for market/wall time
            max_queue_size: Maximum events in main queue
            bar_queue_size: Maximum bars in bar queue (never dropped)
            conflate_quotes: Whether to conflate quotes per symbol
        """
        self._time_source = time_source
        self._max_queue_size = max_queue_size
        self._bar_queue_size = bar_queue_size
        self._conflate_quotes = conflate_quotes

        # Main priority queue: list of PrioritizedEvent, heapified
        self._queue: List[PrioritizedEvent] = []

        # Conflation buffers for quotes/trades (symbol -> latest event)
        self._quote_buffer: Dict[str, PrioritizedEvent] = {}
        self._trade_buffer: Dict[str, PrioritizedEvent] = {}

        # Sequence counter for deterministic ordering of same-timestamp events
        self._sequence_counter: int = 0
        self._sequence_lock = threading.Lock()

        # Queue lock for thread-safe enqueue
        self._queue_lock = threading.Lock()

        # Event handlers by type
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)

        # Backpressure condition (for blocking producers)
        self._space_available = threading.Condition(self._queue_lock)

        # Stats
        self._events_processed: int = 0
        self._events_dropped: int = 0
        self._events_conflated: int = 0

        # Running flag
        self._running: bool = False

    def _next_sequence(self) -> int:
        """Get next sequence number (thread-safe)."""
        with self._sequence_lock:
            self._sequence_counter += 1
            return self._sequence_counter

    def _event_priority(self, event_type: EventType) -> int:
        """
        Priority within the same market_timestamp.

        Lower number means processed earlier.
        This is critical for deterministic causality: fills should be applied before bar-driven signal generation.
        """
        # Most urgent first: fills -> orders -> signals -> bars -> quotes/trades -> rest
        if event_type == EventType.FILL:
            return 0
        if event_type == EventType.ORDER:
            return 1
        if event_type == EventType.SIGNAL:
            return 2
        if event_type == EventType.BAR:
            return 3
        if event_type in (EventType.QUOTE, EventType.TRADE):
            return 4
        return 5

    def register_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Register a handler for an event type.

        Handlers are called in registration order.

        Args:
            event_type: Type of events to handle
            handler: Callback function
        """
        self._handlers[event_type].append(handler)

    def unregister_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """Remove a handler for an event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def enqueue(
        self,
        event_type: EventType,
        payload: Any,
        market_timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None,
        event_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Enqueue an event for processing.

        Thread-safe. May block if queue is full (for BAR events).

        Args:
            event_type: Type of event
            payload: Event data
            market_timestamp: Event timestamp (uses current market time if None)
            symbol: Symbol for conflation (required for QUOTE/TRADE)
            event_id: Unique event ID for idempotency
            timeout: Max seconds to wait if blocking (None = forever)

        Returns:
            True if event was enqueued, False if dropped/timeout
        """
        timestamp = market_timestamp or self._time_source.market_now()
        seq = self._next_sequence()
        pri = self._event_priority(event_type)

        event = PrioritizedEvent(
            market_timestamp=timestamp,
            priority=pri,
            sequence_number=seq,
            event_type=event_type,
            symbol=symbol,
            payload=payload,
            event_id=event_id
        )

        with self._space_available:
            # Handle backpressure based on event type
            if event_type == EventType.BAR:
                # Bars: block until space available (never drop)
                while len(self._queue) >= self._bar_queue_size:
                    if not self._space_available.wait(timeout):
                        logger.warning("Timeout waiting to enqueue bar event")
                        return False
                heapq.heappush(self._queue, event)
                return True

            elif event_type in (EventType.QUOTE, EventType.TRADE) and self._conflate_quotes:
                # Quotes/Trades: conflate per symbol
                if symbol is None:
                    logger.warning(f"Quote/Trade event without symbol, dropping")
                    self._events_dropped += 1
                    return False

                buffer = self._quote_buffer if event_type == EventType.QUOTE else self._trade_buffer
                if symbol in buffer:
                    self._events_conflated += 1
                buffer[symbol] = event
                return True

            else:
                # Other events: drop oldest if full
                if len(self._queue) >= self._max_queue_size:
                    # Pop oldest (smallest) to make room
                    heapq.heappop(self._queue)
                    self._events_dropped += 1
                    logger.debug(f"Dropped oldest event due to queue overflow")

                heapq.heappush(self._queue, event)
                return True

    def _flush_conflation_buffers(self) -> None:
        """Move conflated events into main queue."""
        # Note: Caller must hold _queue_lock
        for event in self._quote_buffer.values():
            heapq.heappush(self._queue, event)
        for event in self._trade_buffer.values():
            heapq.heappush(self._queue, event)
        self._quote_buffer.clear()
        self._trade_buffer.clear()

    def process_next(self) -> Optional[PrioritizedEvent]:
        """
        Process the next event in queue.

        Must be called from single processing thread.

        Returns:
            The processed event, or None if queue is empty
        """
        event: Optional[PrioritizedEvent] = None

        with self._queue_lock:
            # First flush any conflated events
            if self._quote_buffer or self._trade_buffer:
                self._flush_conflation_buffers()

            if not self._queue:
                return None

            event = heapq.heappop(self._queue)
            self._space_available.notify_all()

        if event:
            # Advance market time
            self._time_source.advance_market_time(event.market_timestamp)

            # Dispatch to handlers
            for handler in self._handlers.get(event.event_type, []):
                try:
                    handler(event)
                except Exception as e:
                    logger.error(
                        f"Handler error for {event.event_type}: {e}",
                        exc_info=True
                    )

            self._events_processed += 1

        return event

    def peek_next(self) -> Optional[PrioritizedEvent]:
        """
        Peek at the next event without removing it.

        Intended for single-threaded consumer usage (same as process_next()).
        """
        with self._queue_lock:
            # First flush any conflated events
            if self._quote_buffer or self._trade_buffer:
                self._flush_conflation_buffers()
            if not self._queue:
                return None
            return self._queue[0]

    def process_all(self, max_events: Optional[int] = None) -> int:
        """
        Process all queued events.

        Args:
            max_events: Maximum events to process (None = all)

        Returns:
            Number of events processed
        """
        count = 0
        while True:
            if max_events and count >= max_events:
                break

            event = self.process_next()
            if event is None:
                break
            count += 1

        return count

    def queue_size(self) -> int:
        """Get current queue size."""
        with self._queue_lock:
            return len(self._queue) + len(self._quote_buffer) + len(self._trade_buffer)

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        with self._queue_lock:
            return (
                len(self._queue) == 0
                and len(self._quote_buffer) == 0
                and len(self._trade_buffer) == 0
            )

    def get_stats(self) -> Dict[str, int]:
        """Get dispatcher statistics."""
        return {
            'events_processed': self._events_processed,
            'events_dropped': self._events_dropped,
            'events_conflated': self._events_conflated,
            'queue_size': self.queue_size(),
            'sequence_counter': self._sequence_counter
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._events_processed = 0
        self._events_dropped = 0
        self._events_conflated = 0

    def clear(self) -> None:
        """Clear all queued events."""
        with self._queue_lock:
            self._queue.clear()
            self._quote_buffer.clear()
            self._trade_buffer.clear()
            self._space_available.notify_all()

    def get_sequence_counter(self) -> int:
        """Get current sequence counter (for checkpointing)."""
        with self._sequence_lock:
            return self._sequence_counter

    def restore_sequence_counter(self, value: int) -> None:
        """Restore sequence counter (from checkpoint)."""
        with self._sequence_lock:
            self._sequence_counter = value

