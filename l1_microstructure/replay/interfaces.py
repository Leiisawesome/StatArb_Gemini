"""Replay protocols for historical event-time reconstruction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from l1_microstructure.events import MarketEvent


@dataclass(frozen=True, slots=True)
class ReplayCheckpoint:
    stream_id: str
    event_index: int
    event_timestamp_ns: int


@dataclass(frozen=True, slots=True)
class ReplayCursor:
    stream_id: str
    speed_multiplier: float
    current_index: int = 0
    current_timestamp_ns: int = 0


class ReplayController(Protocol):
    def replay(self, events: Iterable[MarketEvent], speed_multiplier: float = 1.0) -> Iterable[MarketEvent]:
        """Yield events under deterministic replay control."""

    def checkpoint(self) -> ReplayCheckpoint:
        """Capture a deterministic replay checkpoint."""

    def restore(self, checkpoint: ReplayCheckpoint) -> ReplayCursor:
        """Restore replay state from a checkpoint."""