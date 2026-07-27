"""Failure-isolated comparative shadow execution for v1 and v2 engines."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter_ns
from typing import Callable, Iterable

import numpy as np

from l1_microstructure.artifacts.runtime import RuntimeArtifactBundle
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import TradeAction
from l1_microstructure.events import MarketEvent
from l1_microstructure.pipeline import L1MicrostructureStateMachine

from .engine import TransparentEngineArtifacts, TransparentStatisticalEngine


@dataclass(frozen=True, slots=True)
class ShadowComparison:
    timestamp_ns: int
    symbol: str
    baseline_state: str | None
    candidate_state: str | None
    baseline_regime: str | None
    candidate_regime: str | None
    baseline_action: str
    candidate_action: str
    state_disagreement: bool
    regime_disagreement: bool
    action_disagreement: bool
    baseline_latency_ns: int
    candidate_latency_ns: int
    candidate_error_type: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ShadowReport:
    comparisons: tuple[ShadowComparison, ...]
    comparison_count: int
    comparison_sampling_stride: int
    baseline_update_count: int
    candidate_update_count: int
    candidate_error_count: int
    state_disagreement_rate: float
    regime_disagreement_rate: float
    action_disagreement_rate: float
    baseline_p95_latency_ns: float
    candidate_p95_latency_ns: float

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "comparisons": [comparison.to_dict() for comparison in self.comparisons],
        }


class ComparativeShadowRunner:
    def __init__(
        self,
        *,
        baseline_artifacts: RuntimeArtifactBundle,
        candidate_artifacts: TransparentEngineArtifacts,
        config: FrameworkConfig | None = None,
        clock: Callable[[], int] = perf_counter_ns,
        max_comparisons: int = 10_000,
    ) -> None:
        if max_comparisons <= 0:
            raise ValueError("shadow comparison bound must be positive")
        self.config = config or FrameworkConfig()
        self.baseline = L1MicrostructureStateMachine(self.config, baseline_artifacts)
        self.candidate = TransparentStatisticalEngine(candidate_artifacts, self.config)
        self.clock = clock
        self.max_comparisons = max_comparisons

    def run(self, events: Iterable[MarketEvent]) -> ShadowReport:
        comparisons: list[ShadowComparison] = []
        baseline_count = 0
        candidate_count = 0
        candidate_errors = 0
        comparison_count = 0
        comparison_stride = 1
        state_disagreements = 0
        regime_disagreements = 0
        action_disagreements = 0
        for event in sorted(events, key=lambda item: (item.timestamp_ns, item.symbol)):
            baseline_started = self.clock()
            baseline_update = self.baseline.on_event(event)
            baseline_latency = max(self.clock() - baseline_started, 0)
            if baseline_update is not None:
                baseline_count += 1

            candidate_error_type: str | None = None
            candidate_started = self.clock()
            try:
                candidate_update = self.candidate.on_event(event)
            except Exception as exc:
                candidate_update = None
                candidate_error_type = type(exc).__name__
                candidate_errors += 1
            candidate_latency = max(self.clock() - candidate_started, 0)
            if candidate_update is not None:
                candidate_count += 1
            if baseline_update is None and candidate_update is None and candidate_error_type is None:
                continue

            baseline_state = None if baseline_update is None else baseline_update.state.label
            candidate_state = None if candidate_update is None else candidate_update.state.label
            baseline_regime = None if baseline_update is None else baseline_update.regime.dominant_regime.value
            candidate_regime = None if candidate_update is None else candidate_update.regime.dominant_regime
            baseline_action = (
                TradeAction.HOLD.value
                if baseline_update is None or baseline_update.intent is None
                else baseline_update.intent.action.value
            )
            candidate_action = TradeAction.HOLD.value if candidate_update is None else candidate_update.action.value
            comparison = ShadowComparison(
                timestamp_ns=event.timestamp_ns,
                symbol=event.symbol,
                baseline_state=baseline_state,
                candidate_state=candidate_state,
                baseline_regime=baseline_regime,
                candidate_regime=candidate_regime,
                baseline_action=baseline_action,
                candidate_action=candidate_action,
                state_disagreement=baseline_state != candidate_state,
                regime_disagreement=baseline_regime != candidate_regime,
                action_disagreement=baseline_action != candidate_action,
                baseline_latency_ns=baseline_latency,
                candidate_latency_ns=candidate_latency,
                candidate_error_type=candidate_error_type,
            )
            state_disagreements += int(comparison.state_disagreement)
            regime_disagreements += int(comparison.regime_disagreement)
            action_disagreements += int(comparison.action_disagreement)
            if comparison_count % comparison_stride == 0:
                comparisons.append(comparison)
                if len(comparisons) > self.max_comparisons:
                    comparisons = comparisons[::2]
                    comparison_stride *= 2
            comparison_count += 1
        return _shadow_report(
            comparisons,
            baseline_count,
            candidate_count,
            candidate_errors,
            comparison_count=comparison_count,
            comparison_stride=comparison_stride,
            state_disagreements=state_disagreements,
            regime_disagreements=regime_disagreements,
            action_disagreements=action_disagreements,
        )


def _shadow_report(
    comparisons: list[ShadowComparison],
    baseline_count: int,
    candidate_count: int,
    candidate_errors: int,
    *,
    comparison_count: int,
    comparison_stride: int,
    state_disagreements: int,
    regime_disagreements: int,
    action_disagreements: int,
) -> ShadowReport:
    count = max(comparison_count, 1)
    baseline_latencies = [comparison.baseline_latency_ns for comparison in comparisons]
    candidate_latencies = [comparison.candidate_latency_ns for comparison in comparisons]
    return ShadowReport(
        comparisons=tuple(comparisons),
        comparison_count=comparison_count,
        comparison_sampling_stride=comparison_stride,
        baseline_update_count=baseline_count,
        candidate_update_count=candidate_count,
        candidate_error_count=candidate_errors,
        state_disagreement_rate=state_disagreements / count,
        regime_disagreement_rate=regime_disagreements / count,
        action_disagreement_rate=action_disagreements / count,
        baseline_p95_latency_ns=float(np.quantile(baseline_latencies, 0.95)) if baseline_latencies else 0.0,
        candidate_p95_latency_ns=float(np.quantile(candidate_latencies, 0.95)) if candidate_latencies else 0.0,
    )
