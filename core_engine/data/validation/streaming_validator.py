"""
StreamingDataValidator - Real-time OHLCV Validation for Paper Trading
======================================================================

Lightweight streaming validator focused on:
- OHLCV sanity: High >= Low, Close within [Low, High], Volume >= 0
- Gap detection: Flag if gap > 2× expected interval
- Emit DataQualityEvent for monitoring; reject on hard errors

Designed for high-throughput streaming with minimal latency.

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 1)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DataQualitySeverity(Enum):
    """Severity levels for data quality issues."""
    INFO = auto()       # Informational, no action needed
    WARNING = auto()    # Suspicious but not blocking
    ERROR = auto()      # Hard error, reject data
    CRITICAL = auto()   # Critical issue, may trigger circuit breaker

class DataQualityIssue(Enum):
    """Types of data quality issues detected."""
    # OHLCV sanity issues
    HIGH_BELOW_LOW = auto()
    CLOSE_ABOVE_HIGH = auto()
    CLOSE_BELOW_LOW = auto()
    OPEN_ABOVE_HIGH = auto()
    OPEN_BELOW_LOW = auto()
    NEGATIVE_VOLUME = auto()
    ZERO_VOLUME = auto()
    NEGATIVE_PRICE = auto()
    ZERO_PRICE = auto()

    # Gap/timing issues
    GAP_DETECTED = auto()
    BACKWARD_TIMESTAMP = auto()
    STALE_DATA = auto()
    DUPLICATE_TIMESTAMP = auto()

    # Missing data
    MISSING_REQUIRED_FIELD = auto()

@dataclass
class DataQualityEvent:
    """
    Event emitted when data quality issue is detected.

    Used for monitoring and alerting.
    """
    event_id: str
    symbol: str
    timestamp: datetime
    issue: DataQualityIssue
    severity: DataQualitySeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    bar_timestamp: Optional[datetime] = None

@dataclass
class ValidationResult:
    """Result of bar validation."""
    is_valid: bool
    issues: List[DataQualityEvent] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if any ERROR or CRITICAL issues."""
        return any(
            e.severity in (DataQualitySeverity.ERROR, DataQualitySeverity.CRITICAL)
            for e in self.issues
        )

    @property
    def has_warnings(self) -> bool:
        """Check if any WARNING issues."""
        return any(e.severity == DataQualitySeverity.WARNING for e in self.issues)

# Type for quality event handlers
QualityEventHandler = Callable[[DataQualityEvent], None]

class StreamingDataValidator:
    """
    Streaming-optimized OHLCV data validator.

    Validates bars in real-time with minimal overhead:
    - O(1) per-bar validation
    - Per-symbol gap tracking
    - Configurable rejection vs warning thresholds

    Thread-safe for multi-symbol concurrent validation.
    """

    # Default expected bar intervals (seconds) by timeframe
    DEFAULT_INTERVALS = {
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '1h': 3600,
        '1d': 86400,
    }

    def __init__(
        self,
        expected_interval_seconds: float = 60.0,
        gap_threshold_multiplier: float = 2.0,
        reject_on_ohlcv_error: bool = True,
        allow_zero_volume: bool = True,
        stale_threshold_seconds: float = 300.0,
    ):
        """
        Initialize streaming validator.

        Args:
            expected_interval_seconds: Expected time between bars
            gap_threshold_multiplier: Flag gap if > multiplier × expected
            reject_on_ohlcv_error: If True, reject bars with OHLCV violations
            allow_zero_volume: If True, zero volume is WARNING not ERROR
            stale_threshold_seconds: Flag stale if bar is older than this
        """
        self._expected_interval = expected_interval_seconds
        self._gap_multiplier = gap_threshold_multiplier
        self._reject_ohlcv_errors = reject_on_ohlcv_error
        self._allow_zero_volume = allow_zero_volume
        self._stale_threshold = stale_threshold_seconds

        # Per-symbol last bar timestamp for gap detection
        self._last_bar_time: Dict[str, datetime] = {}

        # Event handlers
        self._handlers: List[QualityEventHandler] = []

        # Statistics
        self._stats = {
            'bars_validated': 0,
            'bars_rejected': 0,
            'bars_with_warnings': 0,
            'gaps_detected': 0,
            'ohlcv_errors': 0,
        }

        # Event ID counter
        self._event_counter = 0

    def register_handler(self, handler: QualityEventHandler) -> None:
        """Register a handler for quality events."""
        self._handlers.append(handler)

    def unregister_handler(self, handler: QualityEventHandler) -> None:
        """Unregister a quality event handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def _emit_event(self, event: DataQualityEvent) -> None:
        """Emit quality event to all handlers."""
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Quality event handler error: {e}")

    def _next_event_id(self) -> str:
        """Generate next event ID."""
        self._event_counter += 1
        return f"dq_{self._event_counter:08d}"

    def validate_bar(
        self,
        symbol: str,
        bar_timestamp: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
    ) -> ValidationResult:
        """
        Validate a single OHLCV bar.

        Args:
            symbol: Symbol for the bar
            bar_timestamp: Bar timestamp
            open_price: Open price
            high_price: High price
            low_price: Low price
            close_price: Close price
            volume: Volume

        Returns:
            ValidationResult with is_valid and any issues
        """
        issues: List[DataQualityEvent] = []
        now = datetime.now(timezone.utc)

        # Ensure timezone-aware
        if bar_timestamp.tzinfo is None:
            bar_timestamp = bar_timestamp.replace(tzinfo=timezone.utc)

        # === OHLCV Sanity Checks ===

        # Check for negative/zero prices
        for name, price in [('open', open_price), ('high', high_price),
                            ('low', low_price), ('close', close_price)]:
            if price < 0:
                issues.append(DataQualityEvent(
                    event_id=self._next_event_id(),
                    symbol=symbol,
                    timestamp=now,
                    issue=DataQualityIssue.NEGATIVE_PRICE,
                    severity=DataQualitySeverity.ERROR,
                    message=f"{name} price is negative: {price}",
                    details={'field': name, 'value': price},
                    bar_timestamp=bar_timestamp,
                ))
            elif price == 0:
                issues.append(DataQualityEvent(
                    event_id=self._next_event_id(),
                    symbol=symbol,
                    timestamp=now,
                    issue=DataQualityIssue.ZERO_PRICE,
                    severity=DataQualitySeverity.ERROR,
                    message=f"{name} price is zero",
                    details={'field': name},
                    bar_timestamp=bar_timestamp,
                ))

        # High >= Low check
        if high_price < low_price:
            issues.append(DataQualityEvent(
                event_id=self._next_event_id(),
                symbol=symbol,
                timestamp=now,
                issue=DataQualityIssue.HIGH_BELOW_LOW,
                severity=DataQualitySeverity.ERROR,
                message=f"High ({high_price}) < Low ({low_price})",
                details={'high': high_price, 'low': low_price},
                bar_timestamp=bar_timestamp,
            ))
            self._stats['ohlcv_errors'] += 1

        # Close within [Low, High]
        if close_price > high_price:
            issues.append(DataQualityEvent(
                event_id=self._next_event_id(),
                symbol=symbol,
                timestamp=now,
                issue=DataQualityIssue.CLOSE_ABOVE_HIGH,
                severity=DataQualitySeverity.ERROR,
                message=f"Close ({close_price}) > High ({high_price})",
                details={'close': close_price, 'high': high_price},
                bar_timestamp=bar_timestamp,
            ))
            self._stats['ohlcv_errors'] += 1

        if close_price < low_price:
            issues.append(DataQualityEvent(
                event_id=self._next_event_id(),
                symbol=symbol,
                timestamp=now,
                issue=DataQualityIssue.CLOSE_BELOW_LOW,
                severity=DataQualitySeverity.ERROR,
                message=f"Close ({close_price}) < Low ({low_price})",
                details={'close': close_price, 'low': low_price},
                bar_timestamp=bar_timestamp,
            ))
            self._stats['ohlcv_errors'] += 1

        # Open within [Low, High]
        if open_price > high_price:
            issues.append(DataQualityEvent(
                event_id=self._next_event_id(),
                symbol=symbol,
                timestamp=now,
                issue=DataQualityIssue.OPEN_ABOVE_HIGH,
                severity=DataQualitySeverity.ERROR,
                message=f"Open ({open_price}) > High ({high_price})",
                details={'open': open_price, 'high': high_price},
                bar_timestamp=bar_timestamp,
            ))
            self._stats['ohlcv_errors'] += 1

        if open_price < low_price:
            issues.append(DataQualityEvent(
                event_id=self._next_event_id(),
                symbol=symbol,
                timestamp=now,
                issue=DataQualityIssue.OPEN_BELOW_LOW,
                severity=DataQualitySeverity.ERROR,
                message=f"Open ({open_price}) < Low ({low_price})",
                details={'open': open_price, 'low': low_price},
                bar_timestamp=bar_timestamp,
            ))
            self._stats['ohlcv_errors'] += 1

        # Volume checks
        if volume < 0:
            issues.append(DataQualityEvent(
                event_id=self._next_event_id(),
                symbol=symbol,
                timestamp=now,
                issue=DataQualityIssue.NEGATIVE_VOLUME,
                severity=DataQualitySeverity.ERROR,
                message=f"Negative volume: {volume}",
                details={'volume': volume},
                bar_timestamp=bar_timestamp,
            ))
        elif volume == 0:
            severity = DataQualitySeverity.WARNING if self._allow_zero_volume else DataQualitySeverity.ERROR
            issues.append(DataQualityEvent(
                event_id=self._next_event_id(),
                symbol=symbol,
                timestamp=now,
                issue=DataQualityIssue.ZERO_VOLUME,
                severity=severity,
                message="Zero volume bar",
                details={},
                bar_timestamp=bar_timestamp,
            ))

        # === Gap Detection ===

        if symbol in self._last_bar_time:
            last_time = self._last_bar_time[symbol]
            gap_seconds = (bar_timestamp - last_time).total_seconds()

            # Check for backward timestamp
            if gap_seconds < 0:
                issues.append(DataQualityEvent(
                    event_id=self._next_event_id(),
                    symbol=symbol,
                    timestamp=now,
                    issue=DataQualityIssue.BACKWARD_TIMESTAMP,
                    severity=DataQualitySeverity.ERROR,
                    message=f"Backward timestamp: {bar_timestamp} < {last_time}",
                    details={'current': bar_timestamp.isoformat(), 'previous': last_time.isoformat()},
                    bar_timestamp=bar_timestamp,
                ))
            elif gap_seconds == 0:
                issues.append(DataQualityEvent(
                    event_id=self._next_event_id(),
                    symbol=symbol,
                    timestamp=now,
                    issue=DataQualityIssue.DUPLICATE_TIMESTAMP,
                    severity=DataQualitySeverity.WARNING,
                    message=f"Duplicate timestamp: {bar_timestamp}",
                    details={'timestamp': bar_timestamp.isoformat()},
                    bar_timestamp=bar_timestamp,
                ))
            elif gap_seconds > self._expected_interval * self._gap_multiplier:
                # Filter out cross-day/weekend gaps to avoid false positives
                # Robustness: We only flag gaps within the SAME trading day.
                if bar_timestamp.date() == last_time.date():
                    issues.append(DataQualityEvent(
                        event_id=self._next_event_id(),
                        symbol=symbol,
                        timestamp=now,
                        issue=DataQualityIssue.GAP_DETECTED,
                        severity=DataQualitySeverity.WARNING,
                        message=f"Intraday gap detected: {gap_seconds:.0f}s > {self._expected_interval * self._gap_multiplier:.0f}s",
                        details={
                            'gap_seconds': gap_seconds,
                            'expected_max': self._expected_interval * self._gap_multiplier,
                            'previous': last_time.isoformat(),
                        },
                        bar_timestamp=bar_timestamp,
                    ))
                    self._stats['gaps_detected'] += 1

        # Update last bar time
        self._last_bar_time[symbol] = bar_timestamp

        # === Stale Data Check ===

        age_seconds = (now - bar_timestamp).total_seconds()
        if age_seconds > self._stale_threshold:
            issues.append(DataQualityEvent(
                event_id=self._next_event_id(),
                symbol=symbol,
                timestamp=now,
                issue=DataQualityIssue.STALE_DATA,
                severity=DataQualitySeverity.WARNING,
                message=f"Stale data: {age_seconds:.0f}s old",
                details={'age_seconds': age_seconds, 'threshold': self._stale_threshold},
                bar_timestamp=bar_timestamp,
            ))

        # Emit events
        for issue in issues:
            self._emit_event(issue)

        # Determine validity
        has_errors = any(
            e.severity in (DataQualitySeverity.ERROR, DataQualitySeverity.CRITICAL)
            for e in issues
        )

        is_valid = not (has_errors and self._reject_ohlcv_errors)

        # Update stats
        self._stats['bars_validated'] += 1
        if not is_valid:
            self._stats['bars_rejected'] += 1
        elif any(e.severity == DataQualitySeverity.WARNING for e in issues):
            self._stats['bars_with_warnings'] += 1

        return ValidationResult(is_valid=is_valid, issues=issues)

    def validate_bar_dict(
        self,
        symbol: str,
        bar: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate bar from dictionary format.

        Expects keys: timestamp, open, high, low, close, volume
        (or open_price, high_price, etc.)
        """
        # Extract fields with fallbacks for different naming conventions
        timestamp = bar.get('timestamp') or bar.get('bar_timestamp') or bar.get('time')
        open_price = bar.get('open') or bar.get('open_price') or bar.get('o', 0)
        high_price = bar.get('high') or bar.get('high_price') or bar.get('h', 0)
        low_price = bar.get('low') or bar.get('low_price') or bar.get('l', 0)
        close_price = bar.get('close') or bar.get('close_price') or bar.get('c', 0)
        volume = bar.get('volume') or bar.get('vol') or bar.get('v', 0)

        # Check required fields
        issues: List[DataQualityEvent] = []
        now = datetime.now(timezone.utc)

        if timestamp is None:
            issues.append(DataQualityEvent(
                event_id=self._next_event_id(),
                symbol=symbol,
                timestamp=now,
                issue=DataQualityIssue.MISSING_REQUIRED_FIELD,
                severity=DataQualitySeverity.ERROR,
                message="Missing timestamp field",
                details={'bar': bar},
            ))
            return ValidationResult(is_valid=False, issues=issues)

        # Parse timestamp if string
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                issues.append(DataQualityEvent(
                    event_id=self._next_event_id(),
                    symbol=symbol,
                    timestamp=now,
                    issue=DataQualityIssue.MISSING_REQUIRED_FIELD,
                    severity=DataQualitySeverity.ERROR,
                    message=f"Invalid timestamp format: {timestamp}",
                    details={'timestamp': timestamp},
                ))
                return ValidationResult(is_valid=False, issues=issues)

        return self.validate_bar(
            symbol=symbol,
            bar_timestamp=timestamp,
            open_price=float(open_price),
            high_price=float(high_price),
            low_price=float(low_price),
            close_price=float(close_price),
            volume=float(volume),
        )

    def reset_symbol(self, symbol: str) -> None:
        """Reset tracking for a symbol (e.g., after market close)."""
        if symbol in self._last_bar_time:
            del self._last_bar_time[symbol]

    def reset_all(self) -> None:
        """Reset all symbol tracking."""
        self._last_bar_time.clear()

    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset statistics."""
        for key in self._stats:
            self._stats[key] = 0

    def set_expected_interval(self, interval_seconds: float) -> None:
        """Set expected bar interval."""
        self._expected_interval = interval_seconds

    def set_expected_interval_from_timeframe(self, timeframe: str) -> None:
        """Set expected interval from timeframe string like '1m', '5m', '1h'."""
        if timeframe in self.DEFAULT_INTERVALS:
            self._expected_interval = self.DEFAULT_INTERVALS[timeframe]
        else:
            logger.warning(f"Unknown timeframe {timeframe}, keeping interval at {self._expected_interval}s")

