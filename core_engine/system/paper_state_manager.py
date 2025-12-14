"""
PaperSessionStateManager - Atomic Checkpoints for Paper Trading
===============================================================

Manages checkpointing and recovery for paper trading sessions.

Saved State (from plan Section 7.2):
- Replay position (symbol, timestamp, row_index)
- PositionBook snapshot
- Buffer states (per-symbol DataFrames)
- Regime engine state
- OMS state (pending orders)
- Risk budget state
- last_event_id processed

Checkpoint Triggers:
- Every N bars (configurable, e.g., 1000)
- On manual pause
- On graceful shutdown
- On circuit breaker halt

Atomicity: Save state + last_event_id together; restore resumes exactly-once.

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 5)
"""

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading

logger = logging.getLogger(__name__)

@dataclass
class ReplayPosition:
    """Position in the replay data stream."""
    symbol: str
    timestamp: datetime
    row_index: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'row_index': self.row_index,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReplayPosition':
        return cls(
            symbol=data['symbol'],
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else None,
            row_index=data['row_index'],
        )

@dataclass
class CheckpointMetadata:
    """Metadata for a checkpoint."""
    checkpoint_id: str
    session_id: str
    created_at: datetime
    trigger: str  # 'periodic', 'manual', 'shutdown', 'circuit_breaker'
    last_event_id: str
    last_event_sequence: int
    bars_processed: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'checkpoint_id': self.checkpoint_id,
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'trigger': self.trigger,
            'last_event_id': self.last_event_id,
            'last_event_sequence': self.last_event_sequence,
            'bars_processed': self.bars_processed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointMetadata':
        return cls(
            checkpoint_id=data['checkpoint_id'],
            session_id=data['session_id'],
            created_at=datetime.fromisoformat(data['created_at']),
            trigger=data['trigger'],
            last_event_id=data['last_event_id'],
            last_event_sequence=data['last_event_sequence'],
            bars_processed=data['bars_processed'],
        )

class PaperSessionStateManager:
    """
    Manages checkpointing and recovery for paper trading sessions.

    Features:
    - Atomic checkpoint writes (temp file + rename)
    - Component state aggregation
    - Incremental checkpoints
    - Recovery with exactly-once semantics

    Thread-safe for concurrent checkpoint triggers.
    """

    def __init__(
        self,
        session_id: str,
        checkpoint_dir: str = "checkpoints",
        checkpoint_interval_bars: int = 1000,
        max_checkpoints: int = 5,
    ):
        """
        Initialize paper session state manager.

        Args:
            session_id: Unique session identifier
            checkpoint_dir: Directory for checkpoint files
            checkpoint_interval_bars: Bars between automatic checkpoints
            max_checkpoints: Maximum checkpoints to retain
        """
        self._session_id = session_id
        self._checkpoint_dir = Path(checkpoint_dir)
        self._interval_bars = checkpoint_interval_bars
        self._max_checkpoints = max_checkpoints

        # Create checkpoint directory
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Component references for state gathering
        self._components: Dict[str, Any] = {}

        # Current state
        self._bars_processed = 0
        self._last_event_id = ""
        self._last_event_sequence = 0
        self._checkpoint_count = 0

        # Replay positions per symbol
        self._replay_positions: Dict[str, ReplayPosition] = {}

        # Thread safety
        self._lock = threading.Lock()

        # Stats
        self._stats = {
            'checkpoints_created': 0,
            'checkpoints_restored': 0,
            'bytes_written': 0,
        }

        logger.info(f"📸 PaperSessionStateManager initialized: {session_id}")

    def register_component(self, name: str, component: Any) -> None:
        """
        Register a component for state checkpointing.

        Component must have:
        - get_state_for_checkpoint() -> Dict[str, Any]
        - restore_from_checkpoint(state: Dict[str, Any])
        """
        self._components[name] = component
        logger.debug(f"Registered component for checkpointing: {name}")

    def set_replay_position(
        self,
        symbol: str,
        timestamp: datetime,
        row_index: int,
    ) -> None:
        """Update replay position for a symbol."""
        with self._lock:
            self._replay_positions[symbol] = ReplayPosition(
                symbol=symbol,
                timestamp=timestamp,
                row_index=row_index,
            )

    def update_event_tracking(
        self,
        event_id: str,
        sequence: int,
    ) -> None:
        """Update last processed event info."""
        with self._lock:
            self._last_event_id = event_id
            self._last_event_sequence = sequence

    def increment_bars(self, count: int = 1) -> bool:
        """
        Increment bar count and check if checkpoint needed.

        Returns:
            True if checkpoint should be triggered
        """
        with self._lock:
            self._bars_processed += count
            return self._bars_processed % self._interval_bars == 0

    def _next_checkpoint_id(self) -> str:
        """Generate next checkpoint ID."""
        self._checkpoint_count += 1
        return f"{self._session_id}:cp{self._checkpoint_count:04d}"

    def _checkpoint_path(self, checkpoint_id: str) -> Path:
        """Get file path for a checkpoint."""
        safe_id = checkpoint_id.replace(':', '_')
        return self._checkpoint_dir / f"{safe_id}.json"

    def create_checkpoint(
        self,
        trigger: str = 'periodic',
    ) -> Optional[str]:
        """
        Create a checkpoint of current state.

        Args:
            trigger: What triggered this checkpoint

        Returns:
            Checkpoint ID if successful, None otherwise
        """
        with self._lock:
            checkpoint_id = self._next_checkpoint_id()

            try:
                # Gather component states
                component_states = {}
                for name, component in self._components.items():
                    if hasattr(component, 'get_state_for_checkpoint'):
                        try:
                            component_states[name] = component.get_state_for_checkpoint()
                        except Exception as e:
                            logger.error(f"Error getting state from {name}: {e}")
                            component_states[name] = {'error': str(e)}

                # Build checkpoint data
                checkpoint_data = {
                    'metadata': CheckpointMetadata(
                        checkpoint_id=checkpoint_id,
                        session_id=self._session_id,
                        created_at=datetime.now(timezone.utc),
                        trigger=trigger,
                        last_event_id=self._last_event_id,
                        last_event_sequence=self._last_event_sequence,
                        bars_processed=self._bars_processed,
                    ).to_dict(),
                    'replay_positions': {
                        sym: pos.to_dict()
                        for sym, pos in self._replay_positions.items()
                    },
                    'components': component_states,
                }

                # Atomic write: write to temp, then rename
                checkpoint_path = self._checkpoint_path(checkpoint_id)
                temp_path = checkpoint_path.with_suffix('.tmp')

                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint_data, f, indent=2, default=str)

                # Atomic rename
                shutil.move(str(temp_path), str(checkpoint_path))

                self._stats['checkpoints_created'] += 1
                self._stats['bytes_written'] += checkpoint_path.stat().st_size

                logger.info(f"📸 Checkpoint created: {checkpoint_id} ({trigger})")

                # Cleanup old checkpoints
                self._cleanup_old_checkpoints()

                return checkpoint_id

            except Exception as e:
                logger.error(f"Checkpoint creation failed: {e}")
                return None

    def _cleanup_old_checkpoints(self) -> None:
        """Remove old checkpoints beyond max_checkpoints."""
        checkpoints = self.list_checkpoints()

        if len(checkpoints) > self._max_checkpoints:
            # Sort by creation time and remove oldest
            checkpoints.sort(key=lambda x: x.created_at)
            to_remove = checkpoints[:-self._max_checkpoints]

            for metadata in to_remove:
                try:
                    path = self._checkpoint_path(metadata.checkpoint_id)
                    if path.exists():
                        path.unlink()
                        logger.debug(f"Removed old checkpoint: {metadata.checkpoint_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove checkpoint: {e}")

    def list_checkpoints(self) -> List[CheckpointMetadata]:
        """List all available checkpoints for this session."""
        checkpoints = []

        for path in self._checkpoint_dir.glob(f"{self._session_id.replace(':', '_')}*.json"):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    checkpoints.append(CheckpointMetadata.from_dict(data['metadata']))
            except Exception as e:
                logger.warning(f"Failed to read checkpoint {path}: {e}")

        return checkpoints

    def get_latest_checkpoint(self) -> Optional[CheckpointMetadata]:
        """Get the most recent checkpoint."""
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return None

        checkpoints.sort(key=lambda x: x.created_at, reverse=True)
        return checkpoints[0]

    def restore_checkpoint(
        self,
        checkpoint_id: Optional[str] = None,
    ) -> bool:
        """
        Restore state from a checkpoint.

        Args:
            checkpoint_id: Specific checkpoint to restore (None = latest)

        Returns:
            True if restored successfully
        """
        with self._lock:
            try:
                # Find checkpoint
                if checkpoint_id:
                    checkpoint_path = self._checkpoint_path(checkpoint_id)
                else:
                    latest = self.get_latest_checkpoint()
                    if not latest:
                        logger.warning("No checkpoints available for restore")
                        return False
                    checkpoint_id = latest.checkpoint_id
                    checkpoint_path = self._checkpoint_path(checkpoint_id)

                if not checkpoint_path.exists():
                    logger.error(f"Checkpoint not found: {checkpoint_path}")
                    return False

                # Load checkpoint
                with open(checkpoint_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                metadata = CheckpointMetadata.from_dict(data['metadata'])

                # Restore replay positions
                self._replay_positions = {
                    sym: ReplayPosition.from_dict(pos_data)
                    for sym, pos_data in data.get('replay_positions', {}).items()
                }

                # Restore tracking state
                self._last_event_id = metadata.last_event_id
                self._last_event_sequence = metadata.last_event_sequence
                self._bars_processed = metadata.bars_processed

                # Restore component states
                component_states = data.get('components', {})
                for name, component in self._components.items():
                    if name in component_states and hasattr(component, 'restore_from_checkpoint'):
                        try:
                            component.restore_from_checkpoint(component_states[name])
                            logger.debug(f"Restored state for component: {name}")
                        except Exception as e:
                            logger.error(f"Error restoring {name}: {e}")

                self._stats['checkpoints_restored'] += 1

                logger.info(
                    f"📸 Checkpoint restored: {checkpoint_id} "
                    f"(bars: {metadata.bars_processed}, last_event: {metadata.last_event_id})"
                )

                return True

            except Exception as e:
                logger.error(f"Checkpoint restore failed: {e}")
                return False

    def get_last_event_info(self) -> Dict[str, Any]:
        """Get info about last processed event."""
        with self._lock:
            return {
                'last_event_id': self._last_event_id,
                'last_event_sequence': self._last_event_sequence,
                'bars_processed': self._bars_processed,
            }

    def get_replay_positions(self) -> Dict[str, ReplayPosition]:
        """Get all replay positions."""
        with self._lock:
            return dict(self._replay_positions)

    def get_stats(self) -> Dict[str, Any]:
        """Get state manager statistics."""
        return {
            **self._stats,
            'session_id': self._session_id,
            'bars_processed': self._bars_processed,
            'components_registered': len(self._components),
            'checkpoints_available': len(self.list_checkpoints()),
        }

    def on_shutdown(self) -> Optional[str]:
        """Create shutdown checkpoint."""
        return self.create_checkpoint(trigger='shutdown')

    def on_circuit_breaker(self) -> Optional[str]:
        """Create circuit breaker checkpoint."""
        return self.create_checkpoint(trigger='circuit_breaker')

    def on_pause(self) -> Optional[str]:
        """Create manual pause checkpoint."""
        return self.create_checkpoint(trigger='manual')

