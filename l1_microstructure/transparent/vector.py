"""Training-only robust state vectors and probabilistic transition evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable

import numpy as np

from l1_microstructure.features import ObservedState

from .contracts import TRANSPARENT_ENGINE_VERSION


STATE_VECTOR_FEATURES: tuple[str, ...] = (
    "spread_norm",
    "quote_pressure",
    "trade_pressure",
    "flicker_intensity",
    "realized_volatility",
)


@dataclass(frozen=True, slots=True)
class StateVectorModel:
    symbol: str
    feature_names: tuple[str, ...]
    center: tuple[float, ...]
    scale: tuple[float, ...]
    covariance: tuple[tuple[float, ...], ...]
    precision: tuple[tuple[float, ...], ...]
    probability_score_knots: tuple[float, ...]
    probability_knots: tuple[float, ...]
    transition_probability_threshold: float
    train_start_ns: int
    train_end_ns: int
    sample_count: int
    engine_version: str = TRANSPARENT_ENGINE_VERSION
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        dimension = len(self.feature_names)
        if self.engine_version != TRANSPARENT_ENGINE_VERSION:
            raise ValueError("state-vector model requires engine version v2")
        if self.feature_names != STATE_VECTOR_FEATURES:
            raise ValueError("state-vector feature order does not match the v2 contract")
        if len(self.center) != dimension or len(self.scale) != dimension:
            raise ValueError("state-vector center and scale dimensions do not match")
        if any(value <= 0.0 or not np.isfinite(value) for value in self.scale):
            raise ValueError("state-vector scales must be positive and finite")
        for name, matrix in (("covariance", self.covariance), ("precision", self.precision)):
            if len(matrix) != dimension or any(len(row) != dimension for row in matrix):
                raise ValueError(f"state-vector {name} matrix has the wrong shape")
            if not np.all(np.isfinite(np.asarray(matrix, dtype=float))):
                raise ValueError(f"state-vector {name} matrix must be finite")
        if not self.probability_score_knots or len(self.probability_score_knots) != len(self.probability_knots):
            raise ValueError("transition probability calibration knots are incomplete")
        if any(left > right for left, right in zip(self.probability_score_knots, self.probability_score_knots[1:])):
            raise ValueError("transition score knots must be sorted")
        if any(left > right for left, right in zip(self.probability_knots, self.probability_knots[1:])):
            raise ValueError("transition probability knots must be monotone")
        if any(not 0.0 <= value <= 1.0 for value in self.probability_knots):
            raise ValueError("transition probability knots must be in [0, 1]")
        if not 0.0 < self.transition_probability_threshold < 1.0:
            raise ValueError("transition probability threshold must be in (0, 1)")
        if self.sample_count < 3 or self.train_start_ns > self.train_end_ns:
            raise ValueError("state-vector training metadata is invalid")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> StateVectorModel:
        return cls(
            symbol=str(payload["symbol"]),
            feature_names=tuple(str(value) for value in payload["feature_names"]),
            center=tuple(float(value) for value in payload["center"]),
            scale=tuple(float(value) for value in payload["scale"]),
            covariance=tuple(tuple(float(value) for value in row) for row in payload["covariance"]),
            precision=tuple(tuple(float(value) for value in row) for row in payload["precision"]),
            probability_score_knots=tuple(float(value) for value in payload["probability_score_knots"]),
            probability_knots=tuple(float(value) for value in payload["probability_knots"]),
            transition_probability_threshold=float(payload["transition_probability_threshold"]),
            train_start_ns=int(payload["train_start_ns"]),
            train_end_ns=int(payload["train_end_ns"]),
            sample_count=int(payload["sample_count"]),
            engine_version=str(payload.get("engine_version", "")),
            metadata=dict(payload.get("metadata", {})),
        )

    def transform(self, state: ObservedState) -> np.ndarray:
        if state.symbol != self.symbol:
            raise ValueError(f"state-vector model for {self.symbol} cannot transform {state.symbol}")
        return (state.vector - np.asarray(self.center, dtype=float)) / np.asarray(self.scale, dtype=float)

    def probability_for_score(self, score: float) -> float:
        return float(
            np.interp(
                max(float(score), 0.0),
                np.asarray(self.probability_score_knots, dtype=float),
                np.asarray(self.probability_knots, dtype=float),
                left=self.probability_knots[0],
                right=self.probability_knots[-1],
            )
        )


@dataclass(frozen=True, slots=True)
class TransitionEvidence:
    timestamp_ns: int
    score: float
    probability: float
    probability_threshold: float
    is_transition: bool
    feature_contributions: dict[str, float]
    standardized_vector: tuple[float, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class RobustStateVectorTrainer:
    def __init__(
        self,
        *,
        covariance_shrinkage: float = 0.20,
        regularization: float = 1e-6,
        calibration_bins: int = 20,
        transition_probability_threshold: float = 0.50,
    ) -> None:
        if not 0.0 <= covariance_shrinkage <= 1.0:
            raise ValueError("covariance shrinkage must be in [0, 1]")
        if regularization <= 0.0 or calibration_bins <= 1:
            raise ValueError("vector regularization and calibration bins must be positive")
        if not 0.0 < transition_probability_threshold < 1.0:
            raise ValueError("transition probability threshold must be in (0, 1)")
        self.covariance_shrinkage = covariance_shrinkage
        self.regularization = regularization
        self.calibration_bins = calibration_bins
        self.transition_probability_threshold = transition_probability_threshold

    def fit(
        self,
        states: Iterable[ObservedState],
        transition_targets: Iterable[bool | None],
        *,
        train_start_ns: int,
        train_end_ns: int,
    ) -> StateVectorModel:
        observations = tuple(states)
        raw_targets = tuple(transition_targets)
        targets = np.asarray(
            [np.nan if value is None else float(bool(value)) for value in raw_targets],
            dtype=float,
        )
        if len(observations) < 3:
            raise ValueError("robust vector training requires at least three states")
        if len(targets) != len(observations) - 1:
            raise ValueError("transition targets must align with consecutive state increments")
        resolved_target_mask = np.isfinite(targets)
        if int(np.sum(resolved_target_mask)) < 3:
            raise ValueError("robust vector training requires at least three resolved transition targets")
        symbols = {state.symbol for state in observations}
        if len(symbols) != 1:
            raise ValueError("robust vector training requires exactly one symbol")
        outside = [
            state.timestamp_ns
            for state in observations
            if state.timestamp_ns < train_start_ns or state.timestamp_ns > train_end_ns
        ]
        if outside:
            raise ValueError("state-vector training data crosses the declared training boundary")

        raw = np.vstack([state.vector for state in observations])
        center = np.median(raw, axis=0)
        median_absolute_deviation = np.median(np.abs(raw - center), axis=0) * 1.4826
        standard_deviation = np.std(raw, axis=0)
        scale = np.where(median_absolute_deviation > self.regularization, median_absolute_deviation, standard_deviation)
        scale = np.where(scale > self.regularization, scale, 1.0)
        standardized = (raw - center) / scale
        increments = np.diff(standardized, axis=0)
        empirical = np.atleast_2d(np.cov(increments, rowvar=False, ddof=1))
        if empirical.shape != (len(STATE_VECTOR_FEATURES), len(STATE_VECTOR_FEATURES)):
            empirical = np.diag(np.var(increments, axis=0, ddof=1))
        diagonal = np.diag(np.diag(empirical))
        covariance = (1.0 - self.covariance_shrinkage) * empirical + self.covariance_shrinkage * diagonal
        covariance += np.eye(covariance.shape[0]) * self.regularization
        precision = np.linalg.pinv(covariance)
        scores = np.einsum("ij,jk,ik->i", increments, precision, increments)
        score_knots, probability_knots = self._calibrate_probabilities(
            scores[resolved_target_mask],
            targets[resolved_target_mask],
        )
        return StateVectorModel(
            symbol=next(iter(symbols)),
            feature_names=STATE_VECTOR_FEATURES,
            center=tuple(float(value) for value in center),
            scale=tuple(float(value) for value in scale),
            covariance=tuple(tuple(float(value) for value in row) for row in covariance),
            precision=tuple(tuple(float(value) for value in row) for row in precision),
            probability_score_knots=score_knots,
            probability_knots=probability_knots,
            transition_probability_threshold=self.transition_probability_threshold,
            train_start_ns=int(train_start_ns),
            train_end_ns=int(train_end_ns),
            sample_count=len(observations),
            metadata={
                "trainer": "robust_state_vector_trainer",
                "covariance_shrinkage": self.covariance_shrinkage,
                "regularization": self.regularization,
                "calibration_bins": min(self.calibration_bins, int(np.sum(resolved_target_mask))),
                "resolved_target_count": int(np.sum(resolved_target_mask)),
                "censored_target_count": int(np.sum(~resolved_target_mask)),
            },
        )

    def _calibrate_probabilities(
        self,
        scores: np.ndarray,
        targets: np.ndarray,
    ) -> tuple[tuple[float, ...], tuple[float, ...]]:
        order = np.argsort(scores, kind="stable")
        ordered_scores = scores[order]
        ordered_targets = targets[order]
        groups = np.array_split(np.arange(len(scores)), min(self.calibration_bins, len(scores)))
        score_knots: list[float] = []
        probabilities: list[float] = []
        weights: list[float] = []
        for group in groups:
            if group.size == 0:
                continue
            score_knots.append(float(np.mean(ordered_scores[group])))
            # Jeffreys-like weak smoothing keeps small split-local calibration
            # bins usable without allowing exact zero/one probabilities.
            probabilities.append(float((np.sum(ordered_targets[group]) + 0.25) / (len(group) + 0.5)))
            weights.append(float(len(group)))
        monotone = _pool_adjacent_violators(probabilities, weights)
        return tuple(score_knots), tuple(monotone)


class RobustStateVectorRuntime:
    def __init__(self, model: StateVectorModel):
        self.model = model
        self.previous_vector: np.ndarray | None = None

    def reset(self) -> None:
        self.previous_vector = None

    def update(self, state: ObservedState) -> TransitionEvidence:
        current = self.model.transform(state)
        if self.previous_vector is None:
            self.previous_vector = current
            return TransitionEvidence(
                timestamp_ns=state.timestamp_ns,
                score=0.0,
                probability=0.0,
                probability_threshold=self.model.transition_probability_threshold,
                is_transition=False,
                feature_contributions={name: 0.0 for name in self.model.feature_names},
                standardized_vector=tuple(float(value) for value in current),
            )

        delta = current - self.previous_vector
        precision = np.asarray(self.model.precision, dtype=float)
        contributions = delta * (precision @ delta)
        score = max(float(np.sum(contributions)), 0.0)
        probability = self.model.probability_for_score(score)
        self.previous_vector = current
        return TransitionEvidence(
            timestamp_ns=state.timestamp_ns,
            score=score,
            probability=probability,
            probability_threshold=self.model.transition_probability_threshold,
            is_transition=probability >= self.model.transition_probability_threshold,
            feature_contributions={
                name: float(value) for name, value in zip(self.model.feature_names, contributions)
            },
            standardized_vector=tuple(float(value) for value in current),
        )


def _pool_adjacent_violators(values: list[float], weights: list[float]) -> list[float]:
    blocks: list[tuple[float, float, int]] = []
    for value, weight in zip(values, weights):
        blocks.append((float(value), float(weight), 1))
        while len(blocks) >= 2 and blocks[-2][0] > blocks[-1][0]:
            right_value, right_weight, right_size = blocks.pop()
            left_value, left_weight, left_size = blocks.pop()
            combined_weight = left_weight + right_weight
            combined_value = (left_value * left_weight + right_value * right_weight) / combined_weight
            blocks.append((combined_value, combined_weight, left_size + right_size))
    return [value for value, _, size in blocks for _ in range(size)]
