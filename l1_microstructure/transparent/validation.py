"""Aligned, split-local out-of-sample validation for v1 versus v2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from bisect import bisect_left
from itertools import groupby
from time import perf_counter_ns
from typing import Callable, Iterable, Mapping
from sys import getsizeof

from l1_microstructure.calibration.interfaces import RegimeCalibrationArtifact
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import DecisionEngine, TradeAction
from l1_microstructure.features import ObservedState
from l1_microstructure.regime import RegimeInferencer
from l1_microstructure.training.interfaces import TransitionTrainingSample
from l1_microstructure.transitions import TransitionKernel

from .contracts import (
    EngineEvaluation,
    EnginePredictionRecord,
    PromotionReport,
    PromotionThresholds,
    TransparentPromotionGate,
    evaluate_prediction_records,
)
from .edges import HierarchicalTransitionModel, HierarchicalTransitionRuntime
from .regime import SemiMarkovRegimeModel, SemiMarkovRegimeRuntime
from .shadow import ShadowReport
from .utility import ExpectedUtilityDecisionEngine, UtilityModel
from .vector import RobustStateVectorRuntime, StateVectorModel


@dataclass(frozen=True, slots=True)
class ValidationSplitEvidence:
    label: str
    test_start_ns: int
    test_end_ns: int
    samples: tuple[TransitionTrainingSample, ...]

    def __post_init__(self) -> None:
        if self.test_start_ns > self.test_end_ns:
            raise ValueError("transparent validation split interval is invalid")
        if not self.samples:
            raise ValueError(f"transparent validation split {self.label} has no resolved samples")
        for sample in self.samples:
            start = int(sample.metadata.get("timestamp_ns", -1))
            end = int(sample.metadata.get("end_timestamp_ns", -1))
            if not self.test_start_ns <= start <= end <= self.test_end_ns:
                raise ValueError(
                    f"transparent validation sample in {self.label} crosses the held-out boundary"
                )


@dataclass(frozen=True, slots=True)
class TransparentOOSValidationReport:
    passed: bool
    baseline: EngineEvaluation
    candidate: EngineEvaluation
    promotion: PromotionReport
    split_sample_counts: dict[str, int]
    failures: tuple[str, ...]
    thresholds: PromotionThresholds
    shadow: dict[str, object] | None = None
    opportunity_definition: str = "union_of_v1_v2_detected_transitions"

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "baseline": self.baseline.to_dict(),
            "candidate": self.candidate.to_dict(),
            "promotion": self.promotion.to_dict(),
            "split_sample_counts": dict(self.split_sample_counts),
            "failures": list(self.failures),
            "thresholds": asdict(self.thresholds),
            "shadow": self.shadow,
            "opportunity_definition": self.opportunity_definition,
        }


class TransparentOOSValidator:
    """Compare both models on identical outcomes and fixed predeclared gates."""

    def __init__(
        self,
        thresholds: PromotionThresholds | None = None,
        *,
        minimum_split_count: int = 2,
        clock: Callable[[], int] = perf_counter_ns,
    ) -> None:
        if minimum_split_count <= 0:
            raise ValueError("minimum validation split count must be positive")
        self.thresholds = thresholds or PromotionThresholds()
        self.minimum_split_count = minimum_split_count
        self.clock = clock

    def evaluate(
        self,
        *,
        baseline_transition_payload: dict[str, object] | None = None,
        candidate_model: HierarchicalTransitionModel | None = None,
        candidate_utility_model: UtilityModel | None = None,
        models_by_split: Mapping[
            str,
            tuple[dict[str, object], HierarchicalTransitionModel]
            | tuple[dict[str, object], HierarchicalTransitionModel, UtilityModel],
        ] | None = None,
        splits: Iterable[ValidationSplitEvidence],
        config: FrameworkConfig | None = None,
        shadow_report: ShadowReport | None = None,
        shadow_reports: Iterable[ShadowReport] = (),
    ) -> TransparentOOSValidationReport:
        evidence = tuple(splits)
        if not evidence:
            raise ValueError("transparent validation requires held-out split evidence")
        framework_config = config or FrameworkConfig()
        baseline_records: list[EnginePredictionRecord] = []
        candidate_records: list[EnginePredictionRecord] = []
        for split in evidence:
            if models_by_split is not None:
                try:
                    split_models = models_by_split[split.label]
                except KeyError as exc:
                    raise ValueError(f"validation models are missing split {split.label}") from exc
                split_baseline, split_candidate = split_models[:2]
                split_utility = split_models[2] if len(split_models) == 3 else None
            else:
                if baseline_transition_payload is None or candidate_model is None:
                    raise ValueError("validation requires global models or models_by_split")
                split_baseline, split_candidate = baseline_transition_payload, candidate_model
                split_utility = candidate_utility_model
            candidate_runtime = HierarchicalTransitionRuntime(split_candidate)
            utility_engine = (
                None if split_utility is None else ExpectedUtilityDecisionEngine(split_utility)
            )
            baseline_bytes = _deep_size(split_baseline)
            candidate_bytes = _deep_size(
                {
                    "transition": split_candidate.to_dict(),
                    "utility": None if split_utility is None else split_utility.to_dict(),
                }
            )
            grouped_samples = groupby(split.samples, key=_opportunity_key)
            for _, opportunity in grouped_samples:
                candidate_items = []
                for sample in opportunity:
                    threshold = float(
                        sample.metadata.get(
                            "threshold_bps",
                            framework_config.decision.transaction_cost_bps,
                        )
                    )
                    started = self.clock()
                    baseline_up, baseline_down, baseline_seen = _baseline_probability(
                        split_baseline,
                        sample,
                        threshold,
                        framework_config,
                    )
                    baseline_latency = max(self.clock() - started, 0)
                    started = self.clock()
                    posterior = candidate_runtime.posterior(
                        from_state=sample.from_state,
                        to_state=sample.to_state,
                        regime=sample.regime,
                        horizon_ns=sample.horizon_ns,
                        threshold_bps=threshold,
                    )
                    candidate_latency = max(self.clock() - started, 0)
                    baseline_records.append(
                        EnginePredictionRecord(
                            probability_up=baseline_up,
                            probability_down=baseline_down,
                            realized_drift_bps=sample.realized_drift_bps,
                            threshold_bps=threshold,
                            edge_seen=baseline_seen,
                            latency_ns=baseline_latency,
                            resident_bytes=baseline_bytes,
                            selected_direction=(
                                0 if sample.metadata.get("baseline_detected") is False else None
                            ),
                        )
                    )
                    candidate_items.append((sample, posterior, threshold, candidate_latency))

                selected_action = None
                selected_horizon = None
                first_sample = candidate_items[0][0]
                candidate_detected = bool(first_sample.metadata.get("candidate_detected", True))
                if any(
                    bool(sample.metadata.get("candidate_detected", True)) != candidate_detected
                    for sample, _, _, _ in candidate_items
                ):
                    raise ValueError("candidate detection changed within one validation opportunity")
                if utility_engine is not None and candidate_detected:
                    started = self.clock()
                    decision = utility_engine.decide_for_spread(
                        (posterior for _, posterior, _, _ in candidate_items),
                        spread_bps=float(first_sample.metadata["spread_bps"]),
                        alignment_probability=1.0,
                        transition_probability=float(
                            first_sample.metadata.get("candidate_transition_probability", 1.0)
                        ),
                        current_risk_fraction=0.0,
                        regime=first_sample.regime,
                    )
                    decision_latency = max(self.clock() - started, 0)
                    selected_action = {
                        TradeAction.BUY: 1,
                        TradeAction.SELL: -1,
                        TradeAction.HOLD: 0,
                    }[decision.action]
                    selected_horizon = decision.horizon_ns
                else:
                    decision_latency = 0
                    if not candidate_detected:
                        selected_action = 0

                for sample, posterior, threshold, candidate_latency in candidate_items:
                    selected_direction = selected_action
                    if selected_action not in {None, 0} and sample.horizon_ns != selected_horizon:
                        selected_direction = 0
                    candidate_records.append(
                        EnginePredictionRecord(
                            probability_up=posterior.probability_up,
                            probability_down=posterior.probability_down,
                            realized_drift_bps=sample.realized_drift_bps,
                            threshold_bps=threshold,
                            edge_seen=posterior.exact_edge_seen,
                            latency_ns=candidate_latency
                            + (decision_latency if sample.horizon_ns == selected_horizon else 0),
                            resident_bytes=candidate_bytes,
                            selected_direction=selected_direction,
                        )
                    )
        baseline = evaluate_prediction_records(baseline_records)
        candidate = evaluate_prediction_records(candidate_records)
        promotion = TransparentPromotionGate(self.thresholds).evaluate(baseline, candidate)
        failures: list[str] = []
        if len(evidence) < self.minimum_split_count:
            failures.append(
                f"validation requires {self.minimum_split_count} splits; received {len(evidence)}"
            )
        all_shadow_reports = tuple(shadow_reports) + (() if shadow_report is None else (shadow_report,))
        shadow_error_count = sum(report.candidate_error_count for report in all_shadow_reports)
        if shadow_error_count:
            failures.append(f"shadow candidate errors: {shadow_error_count}")
        for index, report in enumerate(all_shadow_reports):
            latency_limit = report.baseline_p95_latency_ns * self.thresholds.maximum_latency_ratio
            if report.candidate_p95_latency_ns > latency_limit:
                failures.append(f"shadow.performance.latency[{index}]")
        failures.extend(check.code for check in promotion.checks if not check.passed)
        return TransparentOOSValidationReport(
            passed=not failures,
            baseline=baseline,
            candidate=candidate,
            promotion=promotion,
            split_sample_counts={split.label: len(split.samples) for split in evidence},
            failures=tuple(failures),
            thresholds=self.thresholds,
            shadow=None
            if not all_shadow_reports
            else {"reports": [report.to_dict() for report in all_shadow_reports]},
        )


def _baseline_probability(
    payload: dict[str, object],
    sample: TransitionTrainingSample,
    threshold_bps: float,
    config: FrameworkConfig,
) -> tuple[float, float, bool]:
    horizon_models = payload.get("horizon_models", {})
    horizon_payload = dict(horizon_models).get(str(int(sample.horizon_ns)), {})
    baseline_regime = str(sample.metadata.get("baseline_regime", sample.regime))
    edge_key = f"{sample.from_state}::{sample.to_state}::{baseline_regime}"
    edge = dict(horizon_payload).get("edges", {})
    edge_payload = dict(edge).get(edge_key)
    if not isinstance(edge_payload, dict):
        return 0.0, 0.0, False
    posterior = DecisionEngine(config.decision, config.transition).estimate_posterior(
        [float(value) for value in edge_payload.get("drift_samples_bps", ())],
        threshold_bps,
    )
    return posterior.probability_up, posterior.probability_down, True


def build_common_opportunity_samples(
    states: Iterable[ObservedState],
    *,
    candidate_vector_model: StateVectorModel,
    candidate_regime_model: SemiMarkovRegimeModel,
    baseline_regime_calibration: RegimeCalibrationArtifact,
    baseline_transition_payload: dict[str, object],
    config: FrameworkConfig | None = None,
) -> tuple[TransitionTrainingSample, ...]:
    """Resolve the union of v1/v2 detected transitions on one common state stream."""
    observations = tuple(states)
    if len(observations) < 2:
        raise ValueError("common-opportunity validation requires at least two states")
    framework_config = config or FrameworkConfig()
    if {state.symbol for state in observations} != {
        candidate_vector_model.symbol,
        candidate_regime_model.symbol,
        baseline_regime_calibration.symbol,
    }:
        raise ValueError("common-opportunity models and states must share one symbol")
    candidate_vector = RobustStateVectorRuntime(candidate_vector_model)
    candidate_regime = SemiMarkovRegimeRuntime(candidate_regime_model, candidate_vector_model)
    baseline_regime = RegimeInferencer(
        framework_config.regime,
        framework_config.feature,
        baseline_regime_calibration,
    )
    baseline_transition = TransitionKernel(framework_config.transition)
    baseline_transition.load_trained_payload(baseline_transition_payload)
    timestamps = tuple(state.timestamp_ns for state in observations)
    samples: list[TransitionTrainingSample] = []
    previous = observations[0]
    candidate_vector.update(previous)
    candidate_regime.update(previous)
    baseline_regime.update(previous)
    for index, state in enumerate(observations[1:], start=1):
        candidate_regime_posterior = candidate_regime.update(state)
        baseline_regime_posterior = baseline_regime.update(state)
        candidate_transition = candidate_vector.update(state)
        candidate_detected = candidate_transition.is_transition
        baseline_detected = baseline_transition.is_transition(previous.vector, state.vector)
        if candidate_detected or baseline_detected:
            threshold_bps = framework_config.decision.transaction_cost_bps + (
                framework_config.decision.risk_premium_bps
                * max(state.realized_volatility * 10_000.0, 0.1)
            )
            for horizon_ns in framework_config.transition.drift_horizon_ns_values:
                end_index = bisect_left(timestamps, state.timestamp_ns + horizon_ns, lo=index + 1)
                if end_index >= len(observations):
                    continue
                end_state = observations[end_index]
                samples.append(
                    TransitionTrainingSample(
                        symbol=state.symbol,
                        from_state=previous.label,
                        to_state=state.label,
                        regime=candidate_regime_posterior.dominant_regime,
                        horizon_ns=horizon_ns,
                        holding_time_ns=state.timestamp_ns - previous.timestamp_ns,
                        realized_drift_bps=(
                            (end_state.book.microprice - state.book.microprice)
                            / state.book.microprice
                            * 10_000.0
                        ),
                        metadata={
                            "timestamp_ns": state.timestamp_ns,
                            "end_timestamp_ns": end_state.timestamp_ns,
                            "threshold_bps": threshold_bps,
                            "candidate_detected": candidate_detected,
                            "candidate_transition_probability": candidate_transition.probability,
                            "baseline_detected": baseline_detected,
                            "baseline_regime": baseline_regime_posterior.dominant_regime.value,
                            "opportunity_index": index,
                            "spread_bps": (
                                state.book.spread
                                / max(state.book.midpoint, 1e-9)
                                * 10_000.0
                            ),
                        },
                    )
                )
        previous = state
    if not samples:
        raise ValueError("held-out window produced no common v1/v2 transition opportunities")
    return tuple(samples)


def _opportunity_key(sample: TransitionTrainingSample) -> tuple[object, ...]:
    metadata = sample.metadata
    return (
        metadata.get("opportunity_index", metadata.get("timestamp_ns")),
        metadata.get("timestamp_ns"),
        sample.from_state,
        sample.to_state,
        sample.regime,
        sample.holding_time_ns,
    )


def _deep_size(value: object, seen: set[int] | None = None) -> int:
    visited = set() if seen is None else seen
    identity = id(value)
    if identity in visited:
        return 0
    visited.add(identity)
    size = getsizeof(value)
    if isinstance(value, dict):
        size += sum(_deep_size(key, visited) + _deep_size(item, visited) for key, item in value.items())
    elif isinstance(value, (list, tuple, set, frozenset)):
        size += sum(_deep_size(item, visited) for item in value)
    return int(size)
