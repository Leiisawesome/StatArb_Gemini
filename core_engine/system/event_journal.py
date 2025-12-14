"""
EventJournal - Append-Only Audit Trail
======================================

Append-only log for audit and deterministic replay.

Events Logged (from plan Section 7.1):
- Market data (normalized bars)
- Derived state (features, regime)
- Signals generated
- Risk decisions (approve/reject/resize + reasons)
- Orders (submit, fill, cancel, reject)
- Position updates

Format: JSON lines or Parquet, one file per session.

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 5)
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional
import gzip

logger = logging.getLogger(__name__)

class EventCategory(Enum):
    """Categories of journal events."""
    MARKET_DATA = auto()       # Bars, quotes, trades
    DERIVED_STATE = auto()     # Features, indicators, regime
    SIGNAL = auto()            # Trading signals
    RISK_DECISION = auto()     # Authorization decisions
    ORDER = auto()             # Order lifecycle
    FILL = auto()              # Execution fills
    POSITION = auto()          # Position updates
    SYSTEM = auto()            # System events (startup, shutdown, etc.)

@dataclass
class JournalEvent:
    """
    A single journal event entry.

    All events are timestamped and sequenced for deterministic replay.
    """
    event_id: str
    sequence: int
    timestamp: datetime
    category: EventCategory
    event_type: str
    symbol: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            'event_id': self.event_id,
            'sequence': self.sequence,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'category': self.category.name,
            'event_type': self.event_type,
            'symbol': self.symbol,
            'data': self.data,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JournalEvent':
        """Create from dictionary."""
        return cls(
            event_id=data['event_id'],
            sequence=data['sequence'],
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else None,
            category=EventCategory[data['category']],
            event_type=data['event_type'],
            symbol=data.get('symbol'),
            data=data.get('data', {}),
            metadata=data.get('metadata', {}),
        )

class EventJournal:
    """
    Append-only event journal for audit and replay.

    Features:
    - Append-only writes (immutable history)
    - Sequence-numbered events
    - JSON Lines format for streaming
    - Optional compression
    - Thread-safe

    Usage:
        journal = EventJournal(session_id="paper-20250115-0001")
        journal.log_bar('AAPL', bar_data)
        journal.log_signal('AAPL', signal_data)
        journal.log_risk_decision(auth_result)
        journal.close()
    """

    def __init__(
        self,
        session_id: str,
        output_dir: str = "journals",
        compress: bool = False,
        buffer_size: int = 100,
        auto_flush_interval: float = 5.0,
    ):
        """
        Initialize event journal.

        Args:
            session_id: Unique session identifier
            output_dir: Directory for journal files
            compress: If True, write gzip-compressed files
            buffer_size: Events to buffer before flush
            auto_flush_interval: Seconds between auto-flushes
        """
        self._session_id = session_id
        self._output_dir = Path(output_dir)
        self._compress = compress
        self._buffer_size = buffer_size
        self._auto_flush_interval = auto_flush_interval

        # Create output directory
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Determine file path
        ext = ".jsonl.gz" if compress else ".jsonl"
        self._file_path = self._output_dir / f"{session_id}{ext}"

        # Sequence counter
        self._sequence = 0

        # Event buffer
        self._buffer: List[JournalEvent] = []

        # File handle
        self._file = None
        self._open_file()

        # Thread safety
        self._lock = threading.Lock()

        # Stats
        self._stats = {
            'events_logged': 0,
            'flushes': 0,
            'bytes_written': 0,
        }

        # Auto-flush timer (disabled by default - call flush manually or use context manager)
        self._auto_flush_timer = None

        logger.info(f"📓 EventJournal created: {self._file_path}")

    def _open_file(self) -> None:
        """Open the journal file for appending."""
        if self._compress:
            self._file = gzip.open(self._file_path, 'at', encoding='utf-8')
        else:
            self._file = open(self._file_path, 'a', encoding='utf-8')

    def _next_sequence(self) -> int:
        """Get next sequence number."""
        self._sequence += 1
        return self._sequence

    def _create_event(
        self,
        category: EventCategory,
        event_type: str,
        symbol: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> JournalEvent:
        """Create a journal event."""
        return JournalEvent(
            event_id=event_id or f"{self._session_id}:{self._sequence + 1:08d}",
            sequence=self._next_sequence(),
            timestamp=datetime.now(timezone.utc),
            category=category,
            event_type=event_type,
            symbol=symbol,
            data=data or {},
            metadata=metadata or {},
        )

    def _append_event(self, event: JournalEvent) -> None:
        """Append event to buffer."""
        self._buffer.append(event)
        self._stats['events_logged'] += 1

        if len(self._buffer) >= self._buffer_size:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Flush buffered events to file."""
        if not self._buffer:
            return

        try:
            for event in self._buffer:
                line = json.dumps(event.to_dict(), default=str) + '\n'
                self._file.write(line)
                self._stats['bytes_written'] += len(line.encode('utf-8'))

            self._file.flush()
            self._buffer.clear()
            self._stats['flushes'] += 1

        except Exception as e:
            logger.error(f"Journal flush error: {e}")

    def flush(self) -> None:
        """Force flush of buffered events."""
        with self._lock:
            self._flush_buffer()

    def close(self) -> None:
        """Close the journal file."""
        with self._lock:
            self._flush_buffer()
            if self._file:
                self._file.close()
                self._file = None

        logger.info(
            f"📓 EventJournal closed: {self._stats['events_logged']} events, "
            f"{self._stats['bytes_written']} bytes"
        )

    def __enter__(self) -> 'EventJournal':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ==================== Event Logging Methods ====================

    def log_bar(
        self,
        symbol: str,
        bar: Dict[str, Any],
        event_id: Optional[str] = None,
    ) -> None:
        """Log a market data bar."""
        with self._lock:
            event = self._create_event(
                category=EventCategory.MARKET_DATA,
                event_type='bar',
                symbol=symbol,
                data=bar,
                event_id=event_id,
            )
            self._append_event(event)

    def log_quote(
        self,
        symbol: str,
        quote: Dict[str, Any],
    ) -> None:
        """Log a quote update."""
        with self._lock:
            event = self._create_event(
                category=EventCategory.MARKET_DATA,
                event_type='quote',
                symbol=symbol,
                data=quote,
            )
            self._append_event(event)

    def log_features(
        self,
        symbol: str,
        features: Dict[str, float],
        bar_timestamp: Optional[datetime] = None,
    ) -> None:
        """Log computed features."""
        with self._lock:
            event = self._create_event(
                category=EventCategory.DERIVED_STATE,
                event_type='features',
                symbol=symbol,
                data=features,
                metadata={'bar_timestamp': bar_timestamp.isoformat() if bar_timestamp else None},
            )
            self._append_event(event)

    def log_regime(
        self,
        regime: str,
        confidence: float,
        volatility_regime: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log regime detection."""
        with self._lock:
            event = self._create_event(
                category=EventCategory.DERIVED_STATE,
                event_type='regime',
                data={
                    'regime': regime,
                    'confidence': confidence,
                    'volatility_regime': volatility_regime,
                    **(details or {}),
                },
            )
            self._append_event(event)

    def log_signal(
        self,
        symbol: str,
        signal: Dict[str, Any],
        signal_id: Optional[str] = None,
    ) -> None:
        """Log a trading signal."""
        with self._lock:
            event = self._create_event(
                category=EventCategory.SIGNAL,
                event_type='signal_generated',
                symbol=symbol,
                data=signal,
                event_id=signal_id,
            )
            self._append_event(event)

    def log_risk_decision(
        self,
        symbol: str,
        decision: str,  # 'approved', 'rejected', 'resized'
        authorization: Dict[str, Any],
        reasons: Optional[List[str]] = None,
    ) -> None:
        """Log a risk authorization decision."""
        with self._lock:
            event = self._create_event(
                category=EventCategory.RISK_DECISION,
                event_type=f'authorization_{decision}',
                symbol=symbol,
                data={
                    'decision': decision,
                    'authorization': authorization,
                    'reasons': reasons or [],
                },
            )
            self._append_event(event)

    def log_order(
        self,
        symbol: str,
        order_id: str,
        action: str,  # 'submit', 'new', 'cancel', 'reject', 'expire'
        order: Dict[str, Any],
    ) -> None:
        """Log an order lifecycle event."""
        with self._lock:
            event = self._create_event(
                category=EventCategory.ORDER,
                event_type=f'order_{action}',
                symbol=symbol,
                data={'order_id': order_id, **order},
            )
            self._append_event(event)

    def log_fill(
        self,
        symbol: str,
        order_id: str,
        fill_id: str,
        quantity: float,
        price: float,
        commission: float = 0.0,
    ) -> None:
        """Log an execution fill."""
        with self._lock:
            event = self._create_event(
                category=EventCategory.FILL,
                event_type='fill',
                symbol=symbol,
                data={
                    'order_id': order_id,
                    'fill_id': fill_id,
                    'quantity': quantity,
                    'price': price,
                    'commission': commission,
                },
                event_id=fill_id,
            )
            self._append_event(event)

    def log_position(
        self,
        symbol: str,
        action: str,  # 'open', 'update', 'close'
        position: Dict[str, Any],
    ) -> None:
        """Log a position update."""
        with self._lock:
            event = self._create_event(
                category=EventCategory.POSITION,
                event_type=f'position_{action}',
                symbol=symbol,
                data=position,
            )
            self._append_event(event)

    def log_system(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a system event."""
        with self._lock:
            event = self._create_event(
                category=EventCategory.SYSTEM,
                event_type=event_type,
                data=data or {},
            )
            self._append_event(event)

    # ==================== Replay Support ====================

    @staticmethod
    def read_journal(file_path: str) -> List[JournalEvent]:
        """
        Read a journal file for replay.

        Args:
            file_path: Path to journal file

        Returns:
            List of JournalEvent in order
        """
        events = []

        path = Path(file_path)

        if path.suffix == '.gz' or str(path).endswith('.jsonl.gz'):
            opener = lambda p: gzip.open(p, 'rt', encoding='utf-8')
        else:
            opener = lambda p: open(p, 'r', encoding='utf-8')

        with opener(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    events.append(JournalEvent.from_dict(data))

        return events

    def get_stats(self) -> Dict[str, Any]:
        """Get journal statistics."""
        return {
            **self._stats,
            'session_id': self._session_id,
            'file_path': str(self._file_path),
            'sequence': self._sequence,
            'buffer_size': len(self._buffer),
        }

    def get_sequence(self) -> int:
        """Get current sequence number (for checkpointing)."""
        return self._sequence

    def restore_sequence(self, sequence: int) -> None:
        """Restore sequence number from checkpoint."""
        self._sequence = sequence

