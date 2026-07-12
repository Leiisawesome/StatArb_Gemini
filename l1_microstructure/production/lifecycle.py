"""Fail-closed production runtime lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import RLock


class LifecycleState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    WARMING = "warming"
    RECONCILING = "reconciling"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    FLATTENING = "flattening"
    HALTED = "halted"
    ERROR = "error"


_ALLOWED_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.STOPPED: {LifecycleState.STARTING},
    LifecycleState.STARTING: {LifecycleState.WARMING, LifecycleState.RECONCILING, LifecycleState.STOPPED, LifecycleState.HALTED, LifecycleState.ERROR},
    LifecycleState.WARMING: {LifecycleState.RECONCILING, LifecycleState.READY, LifecycleState.FLATTENING, LifecycleState.STOPPED, LifecycleState.HALTED, LifecycleState.ERROR},
    LifecycleState.RECONCILING: {LifecycleState.WARMING, LifecycleState.READY, LifecycleState.STOPPED, LifecycleState.HALTED, LifecycleState.ERROR},
    LifecycleState.READY: {LifecycleState.RUNNING, LifecycleState.STOPPED, LifecycleState.HALTED},
    LifecycleState.RUNNING: {LifecycleState.PAUSED, LifecycleState.FLATTENING, LifecycleState.HALTED, LifecycleState.ERROR},
    LifecycleState.PAUSED: {LifecycleState.RUNNING, LifecycleState.FLATTENING, LifecycleState.HALTED, LifecycleState.STOPPED},
    LifecycleState.FLATTENING: {LifecycleState.HALTED, LifecycleState.STOPPED, LifecycleState.ERROR},
    LifecycleState.HALTED: {LifecycleState.RECONCILING, LifecycleState.STOPPED},
    LifecycleState.ERROR: {LifecycleState.RECONCILING, LifecycleState.STOPPED},
}


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    previous: LifecycleState
    current: LifecycleState
    reason: str
    timestamp: str


class RuntimeLifecycle:
    def __init__(self, initial: LifecycleState = LifecycleState.STOPPED):
        self._state = initial
        self._lock = RLock()

    @property
    def state(self) -> LifecycleState:
        with self._lock:
            return self._state

    def transition(self, target: LifecycleState, reason: str) -> LifecycleTransition:
        with self._lock:
            if target not in _ALLOWED_TRANSITIONS[self._state]:
                raise ValueError(f"invalid lifecycle transition {self._state.value} -> {target.value}")
            previous = self._state
            self._state = target
        return LifecycleTransition(previous, target, reason, datetime.now(timezone.utc).isoformat())

    @property
    def permits_entries(self) -> bool:
        return self.state is LifecycleState.RUNNING
