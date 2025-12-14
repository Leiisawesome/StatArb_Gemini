"""
StreamingSignalManager - Signal Lifecycle with BarPolicy Enforcement
====================================================================

Manages signal generation in streaming mode with:
- BarPolicy enforcement for compute/act timing parity
- Signal input contract validation (stop required)
- Signal ID generation for idempotency
- Signal queuing for next-bar execution

Design (from plan Section 3.4 & 5.1):
- compute_on: "bar_close" - Indicators/features computed at close
- signal_on: "bar_close" - Signal generated at close
- act_on: "next_bar_open" - Order submitted at next open
- fill_price: "next_bar_open" - For paper/backtest alignment

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 2)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
import logging
import threading
from collections import deque

logger = logging.getLogger(__name__)

class BarPolicyPhase(Enum):
    """Current phase in the bar lifecycle."""
    AWAITING_BAR = auto()        # Waiting for next bar close
    COMPUTING = auto()           # Computing indicators/features
    GENERATING_SIGNALS = auto()  # Signal generation in progress
    PENDING_EXECUTION = auto()   # Signals queued for next bar open
    EXECUTING = auto()           # Submitting orders at bar open

@dataclass
class BarPolicy:
    """
    Defines compute/act timing semantics for parity.

    This policy ensures backtest and paper trading produce
    identical results given the same data.
    """
    compute_on: str = "bar_close"      # When indicators computed
    signal_on: str = "bar_close"       # When signals generated
    act_on: str = "next_bar_open"      # When orders submitted
    fill_price: str = "next_bar_open"  # Price assumption for fills

@dataclass
class EnhancedTradingSignal:
    """
    Trading signal with full contract as specified in plan Section 5.1.

    Required fields (signal REJECTED if missing):
    - symbol, side, requested_quantity, signal_strength
    - strategy_id, signal_timestamp, arrival_price

    Stop specification (at least one required for risk budget):
    - stop_price OR stop_loss_pct

    Optional fields:
    - take_profit_price, take_profit_pct
    """
    # === REQUIRED FIELDS ===
    symbol: str
    side: str  # 'buy' | 'sell'
    requested_quantity: float
    signal_strength: float  # 0.0 - 1.0
    strategy_id: str
    signal_timestamp: datetime
    arrival_price: float

    # === STOP SPECIFICATION (at least one recommended) ===
    stop_price: Optional[float] = None
    stop_loss_pct: Optional[float] = None

    # === OPTIONAL FIELDS ===
    take_profit_price: Optional[float] = None
    take_profit_pct: Optional[float] = None

    # === METADATA ===
    signal_id: Optional[str] = None
    bar_timestamp: Optional[datetime] = None  # Bar that triggered signal
    features: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure timezone-aware timestamps
        if self.signal_timestamp and self.signal_timestamp.tzinfo is None:
            self.signal_timestamp = self.signal_timestamp.replace(tzinfo=timezone.utc)
        if self.bar_timestamp and self.bar_timestamp.tzinfo is None:
            self.bar_timestamp = self.bar_timestamp.replace(tzinfo=timezone.utc)

@dataclass
class SignalValidationResult:
    """Result of signal contract validation."""
    is_valid: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    applied_defaults: Dict[str, Any] = field(default_factory=dict)

# Type for signal handlers
SignalHandler = Callable[[EnhancedTradingSignal], None]

class StreamingSignalManager:
    """
    Manages signal lifecycle in streaming mode with BarPolicy enforcement.

    Responsibilities:
    - Validate signal contract (required fields, stop specification)
    - Generate deterministic signal IDs
    - Queue signals for next-bar execution
    - Enforce BarPolicy timing semantics
    - Emit events for signal lifecycle

    Thread-safe for concurrent signal generation.
    """

    def __init__(
        self,
        bar_policy: Optional[BarPolicy] = None,
        default_stop_loss_pct: float = 0.02,
        max_stop_loss_pct: float = 0.10,
        session_id: Optional[str] = None,
    ):
        """
        Initialize streaming signal manager.

        Args:
            bar_policy: BarPolicy for timing enforcement
            default_stop_loss_pct: Default stop if none provided (2%)
            max_stop_loss_pct: Warn if stop exceeds this (10%)
            session_id: Session ID for signal ID generation
        """
        self._bar_policy = bar_policy or BarPolicy()
        self._default_stop_pct = default_stop_loss_pct
        self._max_stop_pct = max_stop_loss_pct
        self._session_id = session_id or "paper"

        # Current phase in bar lifecycle
        self._current_phase = BarPolicyPhase.AWAITING_BAR
        self._current_bar_timestamp: Optional[datetime] = None

        # Pending signals for next-bar execution
        self._pending_signals: deque[EnhancedTradingSignal] = deque()

        # Signal handlers
        self._handlers: List[SignalHandler] = []
        self._validation_handlers: List[Callable[[SignalValidationResult], None]] = []

        # Sequence counter for deterministic signal IDs
        self._signal_sequence = 0
        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            'signals_generated': 0,
            'signals_validated': 0,
            'signals_rejected': 0,
            'signals_with_warnings': 0,
            'defaults_applied': 0,
        }

    def _next_signal_id(self, strategy_id: str, symbol: str, timestamp: datetime) -> str:
        """Generate deterministic signal ID."""
        with self._lock:
            self._signal_sequence += 1
            ts_str = timestamp.strftime('%Y-%m-%dT%H:%M:%S')
            return f"{strategy_id}:{symbol}:{ts_str}:{self._signal_sequence:04d}"

    def register_handler(self, handler: SignalHandler) -> None:
        """Register handler for validated signals."""
        self._handlers.append(handler)

    def register_validation_handler(
        self,
        handler: Callable[[SignalValidationResult], None]
    ) -> None:
        """Register handler for validation events (for monitoring)."""
        self._validation_handlers.append(handler)

    def validate_signal(
        self,
        signal: EnhancedTradingSignal,
        apply_defaults: bool = True,
    ) -> SignalValidationResult:
        """
        Validate signal against contract specification.

        Checks:
        - Required fields present
        - Side is valid
        - Quantities positive
        - Stop specification present (or apply default)
        - Stop price on correct side of arrival
        - Stop loss percentage reasonable

        Args:
            signal: Signal to validate
            apply_defaults: If True, apply default stop when missing

        Returns:
            SignalValidationResult with validation status
        """
        result = SignalValidationResult(is_valid=True)

        # === Required field checks ===
        if not signal.symbol:
            result.errors.append("Missing required field: symbol")
            result.is_valid = False

        if signal.side not in ('buy', 'sell'):
            result.errors.append(f"Invalid side: {signal.side}, must be 'buy' or 'sell'")
            result.is_valid = False

        if signal.requested_quantity <= 0:
            result.errors.append(f"Invalid quantity: {signal.requested_quantity}, must be positive")
            result.is_valid = False

        if not (0.0 <= signal.signal_strength <= 1.0):
            result.warnings.append(f"Signal strength {signal.signal_strength} outside [0, 1]")

        if not signal.strategy_id:
            result.errors.append("Missing required field: strategy_id")
            result.is_valid = False

        if signal.arrival_price <= 0:
            result.errors.append(f"Invalid arrival_price: {signal.arrival_price}")
            result.is_valid = False

        # === Stop specification checks ===
        has_stop = signal.stop_price is not None or signal.stop_loss_pct is not None

        if not has_stop:
            if apply_defaults:
                # Apply default stop loss
                signal.stop_loss_pct = self._default_stop_pct
                result.applied_defaults['stop_loss_pct'] = self._default_stop_pct
                result.warnings.append(
                    f"No stop specified, applied default stop_loss_pct={self._default_stop_pct:.1%}"
                )
                self._stats['defaults_applied'] += 1
            else:
                result.warnings.append("No stop specification provided")

        # Validate stop_price is on correct side
        if signal.stop_price is not None and signal.arrival_price > 0:
            if signal.side == 'buy':
                # For long, stop should be below arrival
                if signal.stop_price >= signal.arrival_price:
                    result.errors.append(
                        f"Stop price {signal.stop_price} is above arrival {signal.arrival_price} for BUY"
                    )
                    result.is_valid = False
            else:
                # For short, stop should be above arrival
                if signal.stop_price <= signal.arrival_price:
                    result.errors.append(
                        f"Stop price {signal.stop_price} is below arrival {signal.arrival_price} for SELL"
                    )
                    result.is_valid = False

        # Warn on unusually wide stop
        if signal.stop_loss_pct is not None and signal.stop_loss_pct > self._max_stop_pct:
            result.warnings.append(
                f"Unusually wide stop: {signal.stop_loss_pct:.1%} > {self._max_stop_pct:.1%}"
            )

        # Update stats
        self._stats['signals_validated'] += 1
        if not result.is_valid:
            self._stats['signals_rejected'] += 1
        elif result.warnings:
            self._stats['signals_with_warnings'] += 1

        # Emit validation event
        for handler in self._validation_handlers:
            try:
                handler(result)
            except Exception as e:
                logger.error(f"Validation handler error: {e}")

        return result

    def resolve_stop(self, signal: EnhancedTradingSignal) -> float:
        """
        Resolve effective stop price from signal.

        Priority: stop_price > stop_loss_pct > default

        Args:
            signal: Signal with stop specification

        Returns:
            Effective stop price
        """
        if signal.stop_price is not None:
            return signal.stop_price

        stop_pct = signal.stop_loss_pct or self._default_stop_pct

        if signal.side == 'buy':
            return signal.arrival_price * (1 - stop_pct)
        else:
            return signal.arrival_price * (1 + stop_pct)

    def on_bar_close(self, bar_timestamp: datetime) -> None:
        """
        Called when a bar closes. Transitions to computing phase.

        Args:
            bar_timestamp: Timestamp of the closed bar
        """
        with self._lock:
            self._current_phase = BarPolicyPhase.COMPUTING
            self._current_bar_timestamp = bar_timestamp

    def on_computation_complete(self) -> None:
        """Called when indicator/feature computation is complete."""
        with self._lock:
            self._current_phase = BarPolicyPhase.GENERATING_SIGNALS

    def submit_signal(
        self,
        signal: EnhancedTradingSignal,
        validate: bool = True,
    ) -> Optional[str]:
        """
        Submit a signal for processing.

        The signal is validated, assigned an ID, and queued for
        next-bar execution per BarPolicy.

        Args:
            signal: Trading signal to submit
            validate: If True, validate against contract

        Returns:
            Signal ID if accepted, None if rejected
        """
        with self._lock:
            # Validate if requested
            if validate:
                validation = self.validate_signal(signal)
                if not validation.is_valid:
                    logger.warning(
                        f"Signal rejected for {signal.symbol}: {validation.errors}"
                    )
                    return None

            # Generate signal ID
            signal.signal_id = self._next_signal_id(
                signal.strategy_id,
                signal.symbol,
                signal.signal_timestamp
            )

            # Set bar timestamp if not set
            if signal.bar_timestamp is None:
                signal.bar_timestamp = self._current_bar_timestamp

            # Queue for next-bar execution
            self._pending_signals.append(signal)
            self._stats['signals_generated'] += 1

            logger.debug(f"Signal queued: {signal.signal_id}")

            return signal.signal_id

    def on_bar_open(self) -> List[EnhancedTradingSignal]:
        """
        Called at bar open. Returns signals for execution.

        Per BarPolicy, signals generated at bar_close are
        executed at next_bar_open.

        Returns:
            List of signals ready for execution
        """
        with self._lock:
            self._current_phase = BarPolicyPhase.EXECUTING

            # Get all pending signals
            signals = list(self._pending_signals)
            self._pending_signals.clear()

            # Notify handlers
            for signal in signals:
                for handler in self._handlers:
                    try:
                        handler(signal)
                    except Exception as e:
                        logger.error(f"Signal handler error: {e}")

            # Transition back to awaiting
            self._current_phase = BarPolicyPhase.AWAITING_BAR

            return signals

    def get_pending_signals(self) -> List[EnhancedTradingSignal]:
        """Get list of pending signals (without clearing)."""
        with self._lock:
            return list(self._pending_signals)

    def clear_pending_signals(self) -> int:
        """Clear all pending signals. Returns count cleared."""
        with self._lock:
            count = len(self._pending_signals)
            self._pending_signals.clear()
            return count

    def get_current_phase(self) -> BarPolicyPhase:
        """Get current phase in bar lifecycle."""
        return self._current_phase

    def get_bar_policy(self) -> BarPolicy:
        """Get the configured BarPolicy."""
        return self._bar_policy

    def get_stats(self) -> Dict[str, int]:
        """Get signal manager statistics."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset statistics."""
        for key in self._stats:
            self._stats[key] = 0

    def get_sequence_counter(self) -> int:
        """Get current sequence counter (for checkpointing)."""
        with self._lock:
            return self._signal_sequence

    def restore_sequence_counter(self, value: int) -> None:
        """Restore sequence counter from checkpoint."""
        with self._lock:
            self._signal_sequence = value

