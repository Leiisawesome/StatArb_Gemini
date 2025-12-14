"""
TradingSessionGate - Trading Hours Control
==========================================

Prevents trading outside allowed windows:
- RTH (Regular Trading Hours) control
- Extended hours support
- Holiday calendar integration
- Symbol-specific market hours
- Opening/closing auction blackouts

Configuration (from plan Section 7.5):
```yaml
allowed_sessions:
  - type: RTH
    start: "09:30"
    end: "16:00"
    timezone: "America/New_York"
no_trade_windows:
  - "09:30:00-09:30:30"  # Opening auction
  - "15:59:30-16:00:00"  # Closing auction
holidays: [...calendar...]
```

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 3)
"""

from dataclasses import dataclass
from datetime import datetime, time, timezone as tz, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Set
import logging
import threading
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class SessionType(Enum):
    """Types of trading sessions."""
    RTH = auto()           # Regular Trading Hours (e.g., 9:30-16:00 ET)
    PRE_MARKET = auto()    # Pre-market (e.g., 4:00-9:30 ET)
    AFTER_HOURS = auto()   # After-hours (e.g., 16:00-20:00 ET)
    EXTENDED = auto()      # Extended hours (pre + after)
    CLOSED = auto()        # Market closed

class GateDecision(Enum):
    """Decision from the session gate."""
    ALLOW = auto()         # Trading allowed
    REJECT = auto()        # Trading not allowed
    WARN = auto()          # Allowed but with warning

@dataclass
class SessionWindow:
    """A trading session window."""
    session_type: SessionType
    start_time: time       # Local time in session timezone
    end_time: time
    timezone: str = "America/New_York"

    def contains_time(self, dt: datetime) -> bool:
        """Check if datetime falls within this window."""
        # Convert to session timezone
        tz_obj = ZoneInfo(self.timezone)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.utc)
        local_dt = dt.astimezone(tz_obj)
        local_time = local_dt.time()

        # Handle overnight sessions (end < start)
        if self.end_time < self.start_time:
            return local_time >= self.start_time or local_time <= self.end_time
        else:
            return self.start_time <= local_time <= self.end_time

@dataclass
class NoTradeWindow:
    """A window during which trading is blocked."""
    start_time: time
    end_time: time
    reason: str = ""

    def contains_time(self, local_time: time) -> bool:
        """Check if time falls within this no-trade window."""
        if self.end_time < self.start_time:
            # Overnight window
            return local_time >= self.start_time or local_time <= self.end_time
        else:
            return self.start_time <= local_time <= self.end_time

@dataclass
class GateCheckResult:
    """Result of a session gate check."""
    decision: GateDecision
    reason: str
    current_session: SessionType
    symbol: Optional[str] = None
    timestamp: Optional[datetime] = None

class TradingSessionGate:
    """
    Controls trading based on market hours and session rules.

    Features:
    - RTH/extended hours session detection
    - Holiday calendar support
    - No-trade window enforcement (auctions, etc.)
    - Symbol-specific market hours
    - Halt detection integration

    Thread-safe for concurrent checks.
    """

    # Default US equity sessions
    DEFAULT_SESSIONS = [
        SessionWindow(SessionType.PRE_MARKET, time(4, 0), time(9, 29, 59)),
        SessionWindow(SessionType.RTH, time(9, 30), time(16, 0)),
        SessionWindow(SessionType.AFTER_HOURS, time(16, 0, 1), time(20, 0)),
    ]

    # Default no-trade windows
    DEFAULT_NO_TRADE = [
        NoTradeWindow(time(9, 30, 0), time(9, 30, 30), "Opening auction"),
        NoTradeWindow(time(15, 59, 30), time(16, 0, 0), "Closing auction"),
    ]

    # 2025 US market holidays (major ones)
    DEFAULT_HOLIDAYS_2025 = [
        datetime(2025, 1, 1),    # New Year's Day
        datetime(2025, 1, 20),   # MLK Day
        datetime(2025, 2, 17),   # Presidents Day
        datetime(2025, 4, 18),   # Good Friday
        datetime(2025, 5, 26),   # Memorial Day
        datetime(2025, 6, 19),   # Juneteenth
        datetime(2025, 7, 4),    # Independence Day
        datetime(2025, 9, 1),    # Labor Day
        datetime(2025, 11, 27),  # Thanksgiving
        datetime(2025, 12, 25),  # Christmas
    ]

    def __init__(
        self,
        allowed_sessions: Optional[List[SessionWindow]] = None,
        no_trade_windows: Optional[List[NoTradeWindow]] = None,
        holidays: Optional[List[datetime]] = None,
        primary_timezone: str = "America/New_York",
        allow_extended_hours: bool = False,
    ):
        """
        Initialize trading session gate.

        Args:
            allowed_sessions: List of allowed session windows
            no_trade_windows: List of no-trade windows (auctions, etc.)
            holidays: List of holiday dates (market closed)
            primary_timezone: Primary timezone for session checks
            allow_extended_hours: If True, allow pre/after-hours trading
        """
        self._sessions = allowed_sessions or self.DEFAULT_SESSIONS
        self._no_trade_windows = no_trade_windows or self.DEFAULT_NO_TRADE
        self._holidays = set(h.date() for h in (holidays or self.DEFAULT_HOLIDAYS_2025))
        self._timezone = primary_timezone
        self._allow_extended = allow_extended_hours

        # Halted symbols
        self._halted_symbols: Set[str] = set()

        # Symbol-specific session overrides
        self._symbol_sessions: Dict[str, List[SessionWindow]] = {}

        # Lock for thread safety
        self._lock = threading.Lock()

        # Statistics
        self._stats = {
            'checks_performed': 0,
            'allows': 0,
            'rejects': 0,
            'halt_rejects': 0,
            'holiday_rejects': 0,
            'session_rejects': 0,
            'no_trade_rejects': 0,
        }

    def check(
        self,
        timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> GateCheckResult:
        """
        Check if trading is allowed at the given time.

        Args:
            timestamp: Time to check (default: now)
            symbol: Optional symbol for symbol-specific checks

        Returns:
            GateCheckResult with decision and reason
        """
        if timestamp is None:
            timestamp = datetime.now(tz.utc)
        elif timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=tz.utc)

        with self._lock:
            self._stats['checks_performed'] += 1

            # Check for symbol halt
            if symbol and symbol in self._halted_symbols:
                self._stats['halt_rejects'] += 1
                return GateCheckResult(
                    decision=GateDecision.REJECT,
                    reason=f"Symbol {symbol} is halted",
                    current_session=SessionType.CLOSED,
                    symbol=symbol,
                    timestamp=timestamp,
                )

            # Check for holiday
            tz_obj = ZoneInfo(self._timezone)
            local_dt = timestamp.astimezone(tz_obj)

            if local_dt.date() in self._holidays:
                self._stats['holiday_rejects'] += 1
                return GateCheckResult(
                    decision=GateDecision.REJECT,
                    reason="Market closed for holiday",
                    current_session=SessionType.CLOSED,
                    symbol=symbol,
                    timestamp=timestamp,
                )

            # Check for weekend
            if local_dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
                self._stats['session_rejects'] += 1
                return GateCheckResult(
                    decision=GateDecision.REJECT,
                    reason="Market closed for weekend",
                    current_session=SessionType.CLOSED,
                    symbol=symbol,
                    timestamp=timestamp,
                )

            # Determine current session
            sessions = self._symbol_sessions.get(symbol, self._sessions) if symbol else self._sessions
            current_session = SessionType.CLOSED

            for session in sessions:
                if session.contains_time(timestamp):
                    current_session = session.session_type
                    break

            # Check if session is allowed
            allowed_types = {SessionType.RTH}
            if self._allow_extended:
                allowed_types.add(SessionType.PRE_MARKET)
                allowed_types.add(SessionType.AFTER_HOURS)
                allowed_types.add(SessionType.EXTENDED)

            if current_session not in allowed_types:
                self._stats['session_rejects'] += 1
                return GateCheckResult(
                    decision=GateDecision.REJECT,
                    reason=f"Outside allowed trading hours (current: {current_session.name})",
                    current_session=current_session,
                    symbol=symbol,
                    timestamp=timestamp,
                )

            # Check for no-trade windows
            local_time = local_dt.time()
            for no_trade in self._no_trade_windows:
                if no_trade.contains_time(local_time):
                    self._stats['no_trade_rejects'] += 1
                    return GateCheckResult(
                        decision=GateDecision.REJECT,
                        reason=f"No-trade window: {no_trade.reason}",
                        current_session=current_session,
                        symbol=symbol,
                        timestamp=timestamp,
                    )

            # All checks passed
            self._stats['allows'] += 1
            return GateCheckResult(
                decision=GateDecision.ALLOW,
                reason="Trading allowed",
                current_session=current_session,
                symbol=symbol,
                timestamp=timestamp,
            )

    def is_open(
        self,
        timestamp: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> bool:
        """Simple check if trading is allowed."""
        result = self.check(timestamp, symbol)
        return result.decision == GateDecision.ALLOW

    def get_current_session(self, timestamp: Optional[datetime] = None) -> SessionType:
        """Get the current session type."""
        result = self.check(timestamp)
        return result.current_session

    def halt_symbol(self, symbol: str, reason: str = "") -> None:
        """
        Halt trading for a symbol.

        Args:
            symbol: Symbol to halt
            reason: Reason for halt (LULD, news, etc.)
        """
        with self._lock:
            self._halted_symbols.add(symbol)
            logger.warning(f"Symbol {symbol} HALTED: {reason}")

    def resume_symbol(self, symbol: str) -> None:
        """Resume trading for a halted symbol."""
        with self._lock:
            if symbol in self._halted_symbols:
                self._halted_symbols.remove(symbol)
                logger.info(f"Symbol {symbol} RESUMED")

    def is_halted(self, symbol: str) -> bool:
        """Check if a symbol is halted."""
        with self._lock:
            return symbol in self._halted_symbols

    def get_halted_symbols(self) -> List[str]:
        """Get list of halted symbols."""
        with self._lock:
            return list(self._halted_symbols)

    def add_holiday(self, date: datetime) -> None:
        """Add a holiday date."""
        with self._lock:
            self._holidays.add(date.date())

    def remove_holiday(self, date: datetime) -> None:
        """Remove a holiday date."""
        with self._lock:
            self._holidays.discard(date.date())

    def set_symbol_sessions(
        self,
        symbol: str,
        sessions: List[SessionWindow]
    ) -> None:
        """Set symbol-specific session windows."""
        with self._lock:
            self._symbol_sessions[symbol] = sessions

    def add_no_trade_window(self, window: NoTradeWindow) -> None:
        """Add a no-trade window."""
        with self._lock:
            self._no_trade_windows.append(window)

    def set_allow_extended_hours(self, allow: bool) -> None:
        """Enable/disable extended hours trading."""
        self._allow_extended = allow

    def get_stats(self) -> Dict[str, int]:
        """Get gate statistics."""
        with self._lock:
            return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset statistics."""
        with self._lock:
            for key in self._stats:
                self._stats[key] = 0

    def get_next_open(self, timestamp: Optional[datetime] = None) -> Optional[datetime]:
        """
        Get the next market open time.

        Args:
            timestamp: Time to start looking from (default: now)

        Returns:
            Next market open datetime, or None if can't determine
        """
        if timestamp is None:
            timestamp = datetime.now(tz.utc)
        elif timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=tz.utc)

        tz_obj = ZoneInfo(self._timezone)
        local_dt = timestamp.astimezone(tz_obj)

        # Look for RTH session
        rth_session = None
        for session in self._sessions:
            if session.session_type == SessionType.RTH:
                rth_session = session
                break

        if rth_session is None:
            return None

        # Check if we're before today's open
        today_open = local_dt.replace(
            hour=rth_session.start_time.hour,
            minute=rth_session.start_time.minute,
            second=rth_session.start_time.second,
            microsecond=0
        )

        if local_dt < today_open:
            # Check if today is a trading day
            if local_dt.weekday() < 5 and local_dt.date() not in self._holidays:
                return today_open.astimezone(tz.utc)

        # Look for next trading day
        next_day = local_dt.date() + timedelta(days=1)
        for _ in range(10):  # Look up to 10 days ahead
            if next_day.weekday() < 5 and next_day not in self._holidays:
                next_open = datetime.combine(
                    next_day,
                    rth_session.start_time,
                    tzinfo=tz_obj
                )
                return next_open.astimezone(tz.utc)
            next_day += timedelta(days=1)

        return None

