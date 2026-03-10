"""Protocols for runtime monitoring and diagnostics emission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    timestamp_ns: int
    state_label: str
    dominant_regime: str
    entropy: float
    alpha_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class MonitoringSink(Protocol):
    def publish(self, snapshot: RuntimeSnapshot) -> None:
        """Emit runtime diagnostics for dashboards, logs, or alerts."""