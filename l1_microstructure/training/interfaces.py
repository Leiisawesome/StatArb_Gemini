"""Training-side protocols for the transition kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol


@dataclass(frozen=True, slots=True)
class TransitionTrainingSample:
    symbol: str
    from_state: str
    to_state: str
    regime: str
    horizon_ns: int
    holding_time_ns: int
    realized_drift_bps: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TransitionModelArtifact:
    model_id: str
    created_at: str
    edge_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


class TransitionTrainer(Protocol):
    def fit(self, samples: Iterable[TransitionTrainingSample]) -> TransitionModelArtifact:
        """Fit a regularized transition kernel and drift posterior bundle."""