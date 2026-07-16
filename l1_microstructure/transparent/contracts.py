"""Version, measurement, and promotion contracts for the transparent engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

import numpy as np


BASELINE_ENGINE_VERSION = "v1"
TRANSPARENT_ENGINE_VERSION = "v2"


@dataclass(frozen=True, slots=True)
class EngineArtifactContract:
    """Fail-closed artifact membership rules for one engine generation."""

    engine_version: str
    required_artifact_types: tuple[str, ...]

    @classmethod
    def for_version(cls, engine_version: str) -> EngineArtifactContract:
        if engine_version == BASELINE_ENGINE_VERSION:
            return cls(
                engine_version=engine_version,
                required_artifact_types=(
                    "state_calibration",
                    "regime_calibration",
                    "execution_calibration",
                    "transition_model",
                ),
            )
        if engine_version == TRANSPARENT_ENGINE_VERSION:
            return cls(
                engine_version=engine_version,
                required_artifact_types=(
                    "state_calibration",
                    "execution_calibration",
                    "state_vector_model",
                    "semi_markov_regime_model",
                    "hierarchical_transition_model",
                    "utility_model",
                ),
            )
        raise ValueError(f"unsupported engine contract version: {engine_version}")

    def validate_manifest(
        self,
        artifact_ids: dict[str, str],
        artifact_versions: dict[str, str],
    ) -> None:
        missing = [kind for kind in self.required_artifact_types if not artifact_ids.get(kind)]
        if missing:
            raise ValueError(f"{self.engine_version} artifact bundle is incomplete: missing {missing}")
        mismatched = {
            kind: artifact_versions.get(kind)
            for kind in self.required_artifact_types
            if artifact_versions.get(kind) != self.engine_version
        }
        if mismatched:
            raise ValueError(
                f"{self.engine_version} artifact bundle contains mixed or missing versions: {mismatched}"
            )


@dataclass(frozen=True, slots=True)
class EnginePredictionRecord:
    """One held-out directional forecast and its operational measurements."""

    probability_up: float
    realized_drift_bps: float
    threshold_bps: float
    edge_seen: bool
    latency_ns: int
    resident_bytes: int = 0
    probability_down: float | None = None
    selected_direction: int | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability_up <= 1.0:
            raise ValueError("probability_up must be in [0, 1]")
        if self.probability_down is not None:
            if not 0.0 <= self.probability_down <= 1.0:
                raise ValueError("probability_down must be in [0, 1]")
            if self.probability_up + self.probability_down > 1.0 + 1e-12:
                raise ValueError("directional probabilities cannot sum above one")
        if self.threshold_bps < 0.0:
            raise ValueError("threshold_bps cannot be negative")
        if not np.isfinite(self.realized_drift_bps) or not np.isfinite(self.threshold_bps):
            raise ValueError("prediction drift and threshold must be finite")
        if self.latency_ns < 0 or self.resident_bytes < 0:
            raise ValueError("operational measurements cannot be negative")
        if self.selected_direction not in {None, -1, 0, 1}:
            raise ValueError("selected prediction direction must be -1, 0, 1, or omitted")

    @property
    def target_up(self) -> float:
        return float(self.realized_drift_bps > self.threshold_bps)

    @property
    def target_down(self) -> float:
        return float(self.realized_drift_bps < -self.threshold_bps)

    @property
    def target_neutral(self) -> float:
        return float(not self.target_up and not self.target_down)

    @property
    def resolved_probability_down(self) -> float:
        return 1.0 - self.probability_up if self.probability_down is None else self.probability_down

    @property
    def probability_neutral(self) -> float:
        return max(1.0 - self.probability_up - self.resolved_probability_down, 0.0)

    @property
    def forecast_direction(self) -> int:
        """Return the unique most-probable forecast class as a signed direction."""
        probabilities = (
            self.probability_up,
            self.resolved_probability_down,
            self.probability_neutral,
        )
        maximum = max(probabilities)
        if sum(abs(value - maximum) <= 1e-12 for value in probabilities) != 1:
            return 0
        selected = probabilities.index(maximum)
        return 1 if selected == 0 else -1 if selected == 1 else 0

    @property
    def direction(self) -> int:
        """Return the executable action when supplied, else the forecast direction."""
        return self.forecast_direction if self.selected_direction is None else self.selected_direction

    @property
    def signed_net_drift_bps(self) -> float:
        if self.direction > 0:
            return self.realized_drift_bps - self.threshold_bps
        if self.direction < 0:
            return -self.realized_drift_bps - self.threshold_bps
        return 0.0


@dataclass(frozen=True, slots=True)
class EngineEvaluation:
    sample_count: int
    brier_score: float
    log_loss: float
    calibration_error: float
    directional_hit_rate: float
    edge_coverage: float
    mean_signed_net_drift_bps: float
    p95_latency_ns: float
    peak_resident_bytes: int
    decisive_count: int = 0
    decision_rate: float = 0.0

    def __post_init__(self) -> None:
        if self.sample_count <= 0:
            raise ValueError("engine evaluation sample count must be positive")
        bounded = (
            self.brier_score,
            self.calibration_error,
            self.directional_hit_rate,
            self.edge_coverage,
        )
        if any(not np.isfinite(value) or not 0.0 <= value <= 1.0 for value in bounded):
            raise ValueError("engine evaluation bounded metrics must be finite and in [0, 1]")
        if (
            not np.isfinite(self.log_loss)
            or self.log_loss < 0.0
            or not np.isfinite(self.mean_signed_net_drift_bps)
            or not np.isfinite(self.p95_latency_ns)
            or self.p95_latency_ns < 0.0
            or self.peak_resident_bytes < 0
            or self.decisive_count < 0
            or self.decisive_count > self.sample_count
            or not 0.0 <= self.decision_rate <= 1.0
        ):
            raise ValueError("engine evaluation operational metrics are invalid")

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def evaluate_prediction_records(
    records: Iterable[EnginePredictionRecord],
    *,
    calibration_bins: int = 10,
) -> EngineEvaluation:
    values = tuple(records)
    if not values:
        raise ValueError("engine evaluation requires at least one prediction record")
    if calibration_bins <= 0:
        raise ValueError("calibration_bins must be positive")

    probabilities = np.asarray(
        [
            (record.probability_up, record.resolved_probability_down, record.probability_neutral)
            for record in values
        ],
        dtype=float,
    )
    targets = np.asarray(
        [(record.target_up, record.target_down, record.target_neutral) for record in values],
        dtype=float,
    )
    clipped = np.clip(probabilities, 1e-12, 1.0)
    brier = float(np.mean(np.sum((probabilities - targets) ** 2, axis=1) / 2.0))
    log_loss = float(-np.mean(np.sum(targets * np.log(clipped), axis=1)))
    forecast_directions = np.asarray([record.forecast_direction for record in values], dtype=int)
    selected = np.asarray(
        [0 if direction > 0 else 1 if direction < 0 else 2 for direction in forecast_directions],
        dtype=int,
    )
    actual = np.argmax(targets, axis=1)
    confidence = probabilities[np.arange(len(values)), selected]
    correct = selected == actual
    calibration_error = _expected_calibration_error(confidence, correct.astype(float), calibration_bins)
    forecast_decisive = forecast_directions != 0
    directional_correct = ((forecast_directions > 0) & (targets[:, 0] == 1.0)) | (
        (forecast_directions < 0) & (targets[:, 1] == 1.0)
    )
    hit_rate = (
        float(np.mean(directional_correct[forecast_decisive]))
        if np.any(forecast_decisive)
        else 0.0
    )
    action_directions = np.asarray([record.direction for record in values], dtype=int)
    decisive_count = int(np.count_nonzero(action_directions))
    return EngineEvaluation(
        sample_count=len(values),
        brier_score=brier,
        log_loss=log_loss,
        calibration_error=calibration_error,
        directional_hit_rate=hit_rate,
        edge_coverage=float(np.mean([record.edge_seen for record in values])),
        mean_signed_net_drift_bps=float(np.mean([record.signed_net_drift_bps for record in values])),
        p95_latency_ns=float(np.quantile([record.latency_ns for record in values], 0.95)),
        peak_resident_bytes=max(record.resident_bytes for record in values),
        decisive_count=decisive_count,
        decision_rate=float(decisive_count / len(values)),
    )


def _expected_calibration_error(probabilities: np.ndarray, targets: np.ndarray, bins: int) -> float:
    boundaries = np.linspace(0.0, 1.0, bins + 1)
    total = len(probabilities)
    error = 0.0
    for index in range(bins):
        upper_inclusive = index == bins - 1
        mask = (probabilities >= boundaries[index]) & (
            probabilities <= boundaries[index + 1]
            if upper_inclusive
            else probabilities < boundaries[index + 1]
        )
        if not np.any(mask):
            continue
        error += float(np.sum(mask) / total) * abs(float(np.mean(probabilities[mask]) - np.mean(targets[mask])))
    return float(error)


@dataclass(frozen=True, slots=True)
class PromotionThresholds:
    """Thresholds fixed before candidate results are inspected."""

    minimum_brier_improvement_fraction: float = 0.05
    maximum_log_loss_ratio: float = 1.0
    maximum_calibration_error_ratio: float = 0.95
    minimum_directional_hit_rate_ratio: float = 0.95
    minimum_edge_coverage_gain: float = 0.0
    minimum_net_drift_ratio: float = 0.95
    maximum_latency_ratio: float = 1.20
    maximum_memory_ratio: float = 1.20
    minimum_candidate_samples: int = 100

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_brier_improvement_fraction < 1.0:
            raise ValueError("minimum brier improvement must be in [0, 1)")
        for value in (
            self.maximum_log_loss_ratio,
            self.maximum_calibration_error_ratio,
            self.minimum_directional_hit_rate_ratio,
            self.minimum_net_drift_ratio,
            self.maximum_latency_ratio,
            self.maximum_memory_ratio,
        ):
            if value < 0.0:
                raise ValueError("promotion ratios cannot be negative")
        if self.minimum_candidate_samples <= 0:
            raise ValueError("minimum candidate samples must be positive")


@dataclass(frozen=True, slots=True)
class PromotionCheck:
    code: str
    passed: bool
    baseline: float
    candidate: float
    limit: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PromotionReport:
    checks: tuple[PromotionCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
        }


class TransparentPromotionGate:
    def __init__(self, thresholds: PromotionThresholds | None = None) -> None:
        self.thresholds = thresholds or PromotionThresholds()

    def evaluate(self, baseline: EngineEvaluation, candidate: EngineEvaluation) -> PromotionReport:
        threshold = self.thresholds
        brier_limit = baseline.brier_score * (1.0 - threshold.minimum_brier_improvement_fraction)
        log_loss_limit = baseline.log_loss * threshold.maximum_log_loss_ratio
        calibration_limit = baseline.calibration_error * threshold.maximum_calibration_error_ratio
        hit_rate_limit = baseline.directional_hit_rate * threshold.minimum_directional_hit_rate_ratio
        coverage_limit = baseline.edge_coverage + threshold.minimum_edge_coverage_gain
        net_drift_limit = _signed_ratio_limit(
            baseline.mean_signed_net_drift_bps,
            threshold.minimum_net_drift_ratio,
        )
        latency_limit = baseline.p95_latency_ns * threshold.maximum_latency_ratio
        memory_limit = baseline.peak_resident_bytes * threshold.maximum_memory_ratio
        checks = (
            PromotionCheck(
                "samples.minimum",
                candidate.sample_count >= threshold.minimum_candidate_samples,
                float(baseline.sample_count),
                float(candidate.sample_count),
                float(threshold.minimum_candidate_samples),
            ),
            PromotionCheck(
                "calibration.brier",
                candidate.brier_score <= brier_limit,
                baseline.brier_score,
                candidate.brier_score,
                brier_limit,
            ),
            PromotionCheck(
                "calibration.log_loss",
                candidate.log_loss <= log_loss_limit,
                baseline.log_loss,
                candidate.log_loss,
                log_loss_limit,
            ),
            PromotionCheck(
                "calibration.expected_error",
                candidate.calibration_error <= calibration_limit,
                baseline.calibration_error,
                candidate.calibration_error,
                calibration_limit,
            ),
            PromotionCheck(
                "directional.hit_rate",
                candidate.directional_hit_rate >= hit_rate_limit,
                baseline.directional_hit_rate,
                candidate.directional_hit_rate,
                hit_rate_limit,
            ),
            PromotionCheck(
                "coverage.edges",
                candidate.edge_coverage >= coverage_limit,
                baseline.edge_coverage,
                candidate.edge_coverage,
                coverage_limit,
            ),
            PromotionCheck(
                "economics.net_drift",
                candidate.mean_signed_net_drift_bps >= net_drift_limit,
                baseline.mean_signed_net_drift_bps,
                candidate.mean_signed_net_drift_bps,
                net_drift_limit,
            ),
            PromotionCheck(
                "performance.latency",
                candidate.p95_latency_ns <= latency_limit,
                baseline.p95_latency_ns,
                candidate.p95_latency_ns,
                latency_limit,
            ),
            PromotionCheck(
                "performance.memory",
                candidate.peak_resident_bytes <= memory_limit,
                float(baseline.peak_resident_bytes),
                float(candidate.peak_resident_bytes),
                memory_limit,
            ),
        )
        return PromotionReport(checks)


def _signed_ratio_limit(baseline: float, ratio: float) -> float:
    if baseline >= 0.0:
        return baseline * ratio
    return baseline / max(ratio, 1e-12)
