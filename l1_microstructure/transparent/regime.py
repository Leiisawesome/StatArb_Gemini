"""Fitted, semantically anchored semi-Markov microstructure regimes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from itertools import permutations
from math import exp, gamma, pi
from typing import Iterable

import numpy as np

from l1_microstructure.features import ObservedState
from l1_microstructure.regime import MicrostructureRegime

from .contracts import TRANSPARENT_ENGINE_VERSION
from .vector import STATE_VECTOR_FEATURES, StateVectorModel


REGIME_ORDER: tuple[str, ...] = tuple(regime.value for regime in MicrostructureRegime)


@dataclass(frozen=True, slots=True)
class SemiMarkovRegimeModel:
    symbol: str
    feature_names: tuple[str, ...]
    regime_order: tuple[str, ...]
    emission_means: tuple[tuple[float, ...], ...]
    emission_variances: tuple[tuple[float, ...], ...]
    initial_probabilities: tuple[float, ...]
    transition_matrix: tuple[tuple[float, ...], ...]
    expected_duration_ns: tuple[int, ...]
    duration_shapes: tuple[float, ...]
    train_start_ns: int
    train_end_ns: int
    sample_count: int
    engine_version: str = TRANSPARENT_ENGINE_VERSION
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        state_count = len(self.regime_order)
        dimension = len(self.feature_names)
        if self.engine_version != TRANSPARENT_ENGINE_VERSION:
            raise ValueError("semi-Markov regime model requires engine version v2")
        if self.feature_names != STATE_VECTOR_FEATURES or self.regime_order != REGIME_ORDER:
            raise ValueError("semi-Markov regime model ordering violates the v2 contract")
        for matrix in (self.emission_means, self.emission_variances):
            if len(matrix) != state_count or any(len(row) != dimension for row in matrix):
                raise ValueError("semi-Markov emission matrix has the wrong shape")
        if any(value <= 0.0 for row in self.emission_variances for value in row):
            raise ValueError("semi-Markov emission variances must be positive")
        if len(self.initial_probabilities) != state_count or not np.isclose(sum(self.initial_probabilities), 1.0):
            raise ValueError("semi-Markov initial probabilities are invalid")
        if len(self.transition_matrix) != state_count or any(len(row) != state_count for row in self.transition_matrix):
            raise ValueError("semi-Markov transition matrix has the wrong shape")
        if any(not np.isclose(sum(row), 1.0) for row in self.transition_matrix):
            raise ValueError("semi-Markov transition rows must sum to one")
        if len(self.expected_duration_ns) != state_count or any(value <= 0 for value in self.expected_duration_ns):
            raise ValueError("semi-Markov durations must be positive")
        if len(self.duration_shapes) != state_count or any(value <= 0.0 for value in self.duration_shapes):
            raise ValueError("semi-Markov duration shapes must be positive")
        if self.sample_count < state_count or self.train_start_ns > self.train_end_ns:
            raise ValueError("semi-Markov training metadata is invalid")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> SemiMarkovRegimeModel:
        return cls(
            symbol=str(payload["symbol"]),
            feature_names=tuple(str(value) for value in payload["feature_names"]),
            regime_order=tuple(str(value) for value in payload["regime_order"]),
            emission_means=tuple(tuple(float(value) for value in row) for row in payload["emission_means"]),
            emission_variances=tuple(
                tuple(float(value) for value in row) for row in payload["emission_variances"]
            ),
            initial_probabilities=tuple(float(value) for value in payload["initial_probabilities"]),
            transition_matrix=tuple(tuple(float(value) for value in row) for row in payload["transition_matrix"]),
            expected_duration_ns=tuple(int(value) for value in payload["expected_duration_ns"]),
            duration_shapes=tuple(float(value) for value in payload["duration_shapes"]),
            train_start_ns=int(payload["train_start_ns"]),
            train_end_ns=int(payload["train_end_ns"]),
            sample_count=int(payload["sample_count"]),
            engine_version=str(payload.get("engine_version", "")),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class SemiMarkovRegimePosterior:
    timestamp_ns: int
    probabilities: dict[str, float]
    predicted_probabilities: dict[str, float]
    emission_log_likelihoods: dict[str, float]
    duration_stay_probabilities: dict[str, float]
    dominant_regime: str
    confidence: float
    expected_holding_time_ns: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class SemiMarkovRegimeTrainer:
    def __init__(
        self,
        *,
        max_iterations: int = 50,
        variance_floor: float = 1e-4,
        dirichlet_alpha: float = 0.25,
        duration_shape: float = 2.0,
    ) -> None:
        if max_iterations <= 0 or variance_floor <= 0.0 or dirichlet_alpha <= 0.0 or duration_shape <= 0.0:
            raise ValueError("semi-Markov trainer configuration is invalid")
        self.max_iterations = max_iterations
        self.variance_floor = variance_floor
        self.dirichlet_alpha = dirichlet_alpha
        self.duration_shape = duration_shape

    def fit(
        self,
        states: Iterable[ObservedState],
        vector_model: StateVectorModel,
        *,
        train_start_ns: int,
        train_end_ns: int,
    ) -> SemiMarkovRegimeModel:
        observations = tuple(states)
        if len(observations) < len(REGIME_ORDER) * 2:
            raise ValueError("semi-Markov fitting requires at least two samples per regime")
        if any(state.symbol != vector_model.symbol for state in observations):
            raise ValueError("semi-Markov states do not match the state-vector model symbol")
        if any(not train_start_ns <= state.timestamp_ns <= train_end_ns for state in observations):
            raise ValueError("semi-Markov training data crosses the declared training boundary")
        vectors = np.vstack([vector_model.transform(state) for state in observations])
        centroids, assignments = self._fit_clusters(vectors)
        cluster_to_regime = self._semantic_mapping(centroids)
        regime_assignments = np.asarray([cluster_to_regime[int(cluster)] for cluster in assignments], dtype=int)

        means: list[np.ndarray] = []
        variances: list[np.ndarray] = []
        global_variance = np.maximum(np.var(vectors, axis=0), self.variance_floor)
        for regime_index in range(len(REGIME_ORDER)):
            members = vectors[regime_assignments == regime_index]
            if len(members) == 0:
                means.append(np.zeros(vectors.shape[1], dtype=float))
                variances.append(global_variance)
            else:
                means.append(np.mean(members, axis=0))
                variances.append(np.maximum(np.var(members, axis=0), self.variance_floor))

        transition_counts = np.full(
            (len(REGIME_ORDER), len(REGIME_ORDER)),
            self.dirichlet_alpha,
            dtype=float,
        )
        for previous, current in zip(regime_assignments[:-1], regime_assignments[1:]):
            transition_counts[previous, current] += 1.0
        transition_matrix = transition_counts / transition_counts.sum(axis=1, keepdims=True)
        initial_counts = np.full(len(REGIME_ORDER), self.dirichlet_alpha, dtype=float)
        initial_counts[regime_assignments[0]] += 1.0
        initial_probabilities = initial_counts / initial_counts.sum()
        durations, duration_shapes = self._fit_duration_models(observations, regime_assignments)
        return SemiMarkovRegimeModel(
            symbol=vector_model.symbol,
            feature_names=STATE_VECTOR_FEATURES,
            regime_order=REGIME_ORDER,
            emission_means=tuple(tuple(float(value) for value in row) for row in means),
            emission_variances=tuple(tuple(float(value) for value in row) for row in variances),
            initial_probabilities=tuple(float(value) for value in initial_probabilities),
            transition_matrix=tuple(tuple(float(value) for value in row) for row in transition_matrix),
            expected_duration_ns=tuple(int(value) for value in durations),
            duration_shapes=tuple(float(value) for value in duration_shapes),
            train_start_ns=int(train_start_ns),
            train_end_ns=int(train_end_ns),
            sample_count=len(observations),
            metadata={
                "trainer": "semantically_anchored_semi_markov_trainer",
                "fit_method": "deterministic_kmeans_diagonal_emissions",
                "duration_fit_method": "weibull_moment_shape",
                "semantic_mapping": {
                    str(cluster): REGIME_ORDER[regime] for cluster, regime in sorted(cluster_to_regime.items())
                },
            },
        )

    def _fit_clusters(self, vectors: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        cluster_count = len(REGIME_ORDER)
        selected = [int(np.argmin(np.linalg.norm(vectors, axis=1)))]
        while len(selected) < cluster_count:
            distances = np.min(
                np.stack([np.sum((vectors - vectors[index]) ** 2, axis=1) for index in selected]),
                axis=0,
            )
            distances[selected] = -1.0
            selected.append(int(np.argmax(distances)))
        centroids = vectors[selected].copy()
        assignments = np.zeros(len(vectors), dtype=int)
        for _ in range(self.max_iterations):
            distances = np.stack([np.sum((vectors - centroid) ** 2, axis=1) for centroid in centroids], axis=1)
            updated_assignments = np.argmin(distances, axis=1)
            if np.array_equal(assignments, updated_assignments):
                assignments = updated_assignments
                break
            assignments = updated_assignments
            for index in range(cluster_count):
                members = vectors[assignments == index]
                if len(members):
                    centroids[index] = np.mean(members, axis=0)
        return centroids, assignments

    @staticmethod
    def _semantic_mapping(centroids: np.ndarray) -> dict[int, int]:
        spread, quote, trade, flicker, volatility = range(len(STATE_VECTOR_FEATURES))
        semantic_scores = np.column_stack(
            (
                -centroids[:, spread] - np.abs(centroids[:, quote]) - np.abs(centroids[:, trade])
                - centroids[:, volatility],
                np.abs(centroids[:, quote]) + np.abs(centroids[:, trade]),
                centroids[:, spread] + centroids[:, volatility],
                centroids[:, flicker] - centroids[:, spread] - centroids[:, volatility],
            )
        )
        best_permutation: tuple[int, ...] | None = None
        best_score = float("-inf")
        for cluster_for_regime in permutations(range(len(REGIME_ORDER))):
            score = sum(semantic_scores[cluster, regime] for regime, cluster in enumerate(cluster_for_regime))
            if score > best_score:
                best_score = float(score)
                best_permutation = cluster_for_regime
        assert best_permutation is not None
        return {cluster: regime for regime, cluster in enumerate(best_permutation)}

    def _fit_duration_models(
        self,
        states: tuple[ObservedState, ...],
        assignments: np.ndarray,
    ) -> tuple[list[int], list[float]]:
        deltas = [
            max(current.timestamp_ns - previous.timestamp_ns, 1)
            for previous, current in zip(states[:-1], states[1:])
        ]
        default_delta = int(np.median(deltas)) if deltas else 1
        runs: dict[int, list[int]] = {index: [] for index in range(len(REGIME_ORDER))}
        run_start = 0
        for index in range(1, len(assignments) + 1):
            if index < len(assignments) and assignments[index] == assignments[run_start]:
                continue
            last_timestamp = states[index - 1].timestamp_ns
            duration = max(last_timestamp - states[run_start].timestamp_ns + default_delta, 1)
            runs[int(assignments[run_start])].append(duration)
            run_start = index
        means: list[int] = []
        shapes: list[float] = []
        for index in range(len(REGIME_ORDER)):
            values = np.asarray(runs[index], dtype=float)
            if values.size == 0:
                means.append(default_delta)
                shapes.append(self.duration_shape)
                continue
            mean = float(np.mean(values))
            means.append(max(int(mean), 1))
            if values.size < 2 or mean <= 0.0:
                shapes.append(self.duration_shape)
                continue
            coefficient_of_variation = float(np.std(values, ddof=1) / mean)
            if coefficient_of_variation <= 1e-6:
                fitted_shape = 10.0
            else:
                fitted_shape = coefficient_of_variation ** -1.086
            shapes.append(float(min(max(fitted_shape, 0.5), 10.0)))
        return means, shapes


class SemiMarkovRegimeRuntime:
    def __init__(self, model: SemiMarkovRegimeModel, vector_model: StateVectorModel):
        if model.symbol != vector_model.symbol or model.feature_names != vector_model.feature_names:
            raise ValueError("semi-Markov and state-vector artifacts are incompatible")
        self.model = model
        self.vector_model = vector_model
        self.previous_probabilities: np.ndarray | None = None
        self.previous_timestamp_ns: int | None = None
        self.dominant_index: int | None = None
        self.regime_started_at_ns: int | None = None

    def reset(self) -> None:
        self.previous_probabilities = None
        self.previous_timestamp_ns = None
        self.dominant_index = None
        self.regime_started_at_ns = None

    def update(self, state: ObservedState) -> SemiMarkovRegimePosterior:
        vector = self.vector_model.transform(state)
        likelihood_logs = self._emission_log_likelihoods(vector)
        predicted, stays = self._predict(state.timestamp_ns)
        shifted = likelihood_logs - np.max(likelihood_logs)
        emission = np.exp(shifted)
        filtered = np.maximum(predicted * emission, 1e-12)
        filtered /= np.sum(filtered)
        dominant = int(np.argmax(filtered))
        if self.dominant_index != dominant:
            self.regime_started_at_ns = state.timestamp_ns
        self.dominant_index = dominant
        self.previous_timestamp_ns = state.timestamp_ns
        self.previous_probabilities = filtered
        return SemiMarkovRegimePosterior(
            timestamp_ns=state.timestamp_ns,
            probabilities={regime: float(filtered[index]) for index, regime in enumerate(self.model.regime_order)},
            predicted_probabilities={
                regime: float(predicted[index]) for index, regime in enumerate(self.model.regime_order)
            },
            emission_log_likelihoods={
                regime: float(likelihood_logs[index]) for index, regime in enumerate(self.model.regime_order)
            },
            duration_stay_probabilities={
                regime: float(stays[index]) for index, regime in enumerate(self.model.regime_order)
            },
            dominant_regime=self.model.regime_order[dominant],
            confidence=float(filtered[dominant]),
            expected_holding_time_ns=int(self.model.expected_duration_ns[dominant]),
        )

    def _emission_log_likelihoods(self, vector: np.ndarray) -> np.ndarray:
        means = np.asarray(self.model.emission_means, dtype=float)
        variances = np.asarray(self.model.emission_variances, dtype=float)
        return -0.5 * np.sum(np.log(2.0 * pi * variances) + ((vector - means) ** 2) / variances, axis=1)

    def _predict(self, timestamp_ns: int) -> tuple[np.ndarray, np.ndarray]:
        if self.previous_probabilities is None or self.previous_timestamp_ns is None:
            return np.asarray(self.model.initial_probabilities, dtype=float), np.ones(len(REGIME_ORDER), dtype=float)
        dt_ns = max(timestamp_ns - self.previous_timestamp_ns, 0)
        dwell_ns = (
            0
            if self.regime_started_at_ns is None
            else max(self.previous_timestamp_ns - self.regime_started_at_ns, 0)
        )
        matrix = np.zeros((len(REGIME_ORDER), len(REGIME_ORDER)), dtype=float)
        stays = np.zeros(len(REGIME_ORDER), dtype=float)
        base = np.asarray(self.model.transition_matrix, dtype=float)
        for index in range(len(REGIME_ORDER)):
            current_dwell = dwell_ns if index == self.dominant_index else 0
            stays[index] = _conditional_weibull_survival(
                current_dwell,
                dt_ns,
                self.model.expected_duration_ns[index],
                self.model.duration_shapes[index],
            )
            off_diagonal = base[index].copy()
            off_diagonal[index] = 0.0
            total = float(np.sum(off_diagonal))
            if total <= 0.0:
                off_diagonal = np.ones(len(REGIME_ORDER), dtype=float)
                off_diagonal[index] = 0.0
                total = float(np.sum(off_diagonal))
            matrix[index] = (1.0 - stays[index]) * off_diagonal / total
            matrix[index, index] = stays[index]
        predicted = self.previous_probabilities @ matrix
        predicted = np.maximum(predicted, 1e-12)
        predicted /= np.sum(predicted)
        return predicted, stays


def _conditional_weibull_survival(dwell_ns: int, dt_ns: int, mean_ns: int, shape: float) -> float:
    if dt_ns <= 0:
        return 1.0
    scale = max(float(mean_ns) / gamma(1.0 + 1.0 / shape), 1.0)
    start = (max(float(dwell_ns), 0.0) / scale) ** shape
    end = ((max(float(dwell_ns), 0.0) + float(dt_ns)) / scale) ** shape
    return float(min(max(exp(-(end - start)), 1e-9), 1.0))
