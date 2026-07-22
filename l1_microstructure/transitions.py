"""Transition kernel estimation for the L1 state machine."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from math import exp, log, sqrt
from typing import Deque

import numpy as np

from .config import TransitionConfig
from .regime import MicrostructureRegime


@dataclass(frozen=True, slots=True)
class EdgeKey:
    from_state: str
    to_state: str
    regime: MicrostructureRegime


@dataclass(slots=True)
class EdgeStatistics:
    count: int = 0
    holding_times_ns: list[int] = field(default_factory=list)
    drift_samples_bps: list[float] = field(default_factory=list)
    session_drift_means_bps: list[float] = field(default_factory=list)
    directional_consensus: float = 0.0
    last_observation_index: int = 0
    # Welford incremental stats — O(1) property access regardless of session length
    _ht_count: int = field(default=0, init=False, repr=False)
    _ht_mean: float = field(default=0.0, init=False, repr=False)
    _d_count: int = field(default=0, init=False, repr=False)
    _d_mean: float = field(default=0.0, init=False, repr=False)
    _d_M2: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        # Bootstrap incremental stats from any pre-populated lists (e.g. loaded payloads)
        for ht in self.holding_times_ns:
            self._welford_update_ht(ht)
        for d in self.drift_samples_bps:
            self._welford_update_d(d)

    def _welford_update_ht(self, value: int) -> None:
        self._ht_count += 1
        delta = value - self._ht_mean
        self._ht_mean += delta / self._ht_count

    def _welford_update_d(self, value: float) -> None:
        self._d_count += 1
        delta = value - self._d_mean
        self._d_mean += delta / self._d_count
        delta2 = value - self._d_mean
        self._d_M2 += delta * delta2

    def record_holding_time(self, ht_ns: int) -> None:
        """Append a holding-time sample and update incremental stats."""
        self.holding_times_ns.append(int(ht_ns))
        self._welford_update_ht(ht_ns)

    def record_drift(self, drift_bps: float) -> None:
        """Append a drift sample and update incremental stats."""
        self.drift_samples_bps.append(float(drift_bps))
        self._welford_update_d(drift_bps)

    @property
    def mean_holding_time_ns(self) -> float:
        return self._ht_mean if self._ht_count > 0 else 0.0

    @property
    def drift_mean_bps(self) -> float:
        return self._d_mean if self._d_count > 0 else 0.0

    @property
    def drift_std_bps(self) -> float:
        if self._d_count < 2:
            return 0.0
        return sqrt(self._d_M2 / (self._d_count - 1))

    @property
    def signal_to_noise(self) -> float:
        samples = self.posterior_samples_bps
        if len(samples) < 2:
            return 0.0
        mean = float(np.mean(samples))
        std = float(np.std(samples, ddof=1))
        if self.session_drift_means_bps:
            return abs(mean) / max(std, 1e-6)
        return abs(mean) / std if std > 0 else 0.0

    @property
    def training_session_count(self) -> int:
        return len(self.session_drift_means_bps)

    @property
    def posterior_samples_bps(self) -> list[float]:
        return self.session_drift_means_bps or self.drift_samples_bps

    @property
    def decision_drift_mean_bps(self) -> float:
        samples = self.posterior_samples_bps
        return float(np.mean(samples)) if samples else 0.0


@dataclass(frozen=True, slots=True)
class TransitionDiagnostic:
    edge: EdgeKey
    transition_probability: float
    entropy: float
    signal_to_noise: float
    alpha_score: float
    shrunk_drift_bps: float
    observation_count: int


class TransitionKernel:
    # Recompute the precision matrix every this many new increments.
    # The covariance changes slowly; daily re-pinv cost is negligible at this interval.
    _PRECISION_TTL: int = 50

    def __init__(self, config: TransitionConfig | None = None):
        self.config = config or TransitionConfig()
        self.edge_stats: dict[EdgeKey, EdgeStatistics] = {}
        self.outgoing_counts: dict[tuple[str, MicrostructureRegime], dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.increment_history: Deque[np.ndarray] = deque(maxlen=self.config.covariance_history)
        self.observation_index: int = 0
        self._precision_matrix: np.ndarray | None = None
        self._precision_stale_count: int = 0

    def mahalanobis_distance(self, previous_vector: np.ndarray, current_vector: np.ndarray) -> float:
        delta = np.asarray(current_vector, dtype=float) - np.asarray(previous_vector, dtype=float)
        if len(self.increment_history) < 5:
            self.increment_history.append(delta)
            return float(np.linalg.norm(delta))

        self._precision_stale_count += 1
        if self._precision_matrix is None or self._precision_stale_count >= self._PRECISION_TTL:
            history = np.vstack(self.increment_history)
            covariance = np.cov(history, rowvar=False)
            covariance = np.atleast_2d(covariance)
            covariance += np.eye(covariance.shape[0]) * 1e-6
            self._precision_matrix = np.linalg.pinv(covariance)
            self._precision_stale_count = 0

        distance = float(delta @ self._precision_matrix @ delta)
        self.increment_history.append(delta)
        return distance

    def is_transition(self, previous_vector: np.ndarray, current_vector: np.ndarray) -> bool:
        return self.mahalanobis_distance(previous_vector, current_vector) > self.config.mahalanobis_threshold

    def observe_transition(self, edge: EdgeKey, holding_time_ns: int) -> EdgeStatistics:
        self.observation_index += 1
        stats = self.edge_stats.setdefault(edge, EdgeStatistics())
        stats.count += 1
        stats.record_holding_time(holding_time_ns)
        stats.last_observation_index = self.observation_index
        self.outgoing_counts[(edge.from_state, edge.regime)][edge.to_state] += 1
        return stats

    def attach_drift(self, edge: EdgeKey, drift_bps: float) -> EdgeStatistics:
        stats = self.edge_stats.setdefault(edge, EdgeStatistics())
        stats.record_drift(drift_bps)
        stats.last_observation_index = self.observation_index
        return stats

    def get_edge(self, edge: EdgeKey) -> EdgeStatistics:
        return self.edge_stats.setdefault(edge, EdgeStatistics())

    def transition_probability(self, edge: EdgeKey) -> float:
        outgoing = self.outgoing_counts[(edge.from_state, edge.regime)]
        total = sum(outgoing.values())
        target_count = outgoing.get(edge.to_state, 0)
        num_targets = max(len(outgoing), 1)
        alpha = self.config.dirichlet_alpha
        return float((target_count + alpha) / (total + alpha * num_targets))

    def transition_entropy(self, from_state: str, regime: MicrostructureRegime) -> float:
        outgoing = self.outgoing_counts[(from_state, regime)]
        if not outgoing:
            return 0.0
        total = sum(outgoing.values())
        alpha = self.config.dirichlet_alpha
        num_targets = len(outgoing)
        entropy = 0.0
        for count in outgoing.values():
            probability = (count + alpha) / (total + alpha * num_targets)
            entropy -= probability * log(probability)
        return float(entropy)

    def shrunk_drift_mean(self, edge: EdgeKey) -> float:
        stats = self.get_edge(edge)
        if not stats.posterior_samples_bps:
            return 0.0
        age = max(self.observation_index - stats.last_observation_index, 0)
        return float(stats.decision_drift_mean_bps * exp(-self.config.adversarial_decay_gamma * age))

    def diagnostic(self, edge: EdgeKey) -> TransitionDiagnostic:
        stats = self.get_edge(edge)
        entropy = self.transition_entropy(edge.from_state, edge.regime)
        probability = self.transition_probability(edge)
        signal_to_noise = stats.signal_to_noise
        alpha_score = signal_to_noise / (1.0 + entropy)
        return TransitionDiagnostic(
            edge=edge,
            transition_probability=probability,
            entropy=entropy,
            signal_to_noise=signal_to_noise,
            alpha_score=alpha_score,
            shrunk_drift_bps=self.shrunk_drift_mean(edge),
            observation_count=stats.count,
        )

    def load_trained_payload(self, payload: dict[str, object]) -> None:
        self.edge_stats.clear()
        self.outgoing_counts.clear()
        self.increment_history.clear()
        self._precision_matrix = None
        self._precision_stale_count = 0
        self.observation_index = int(payload.get("sample_count", 0))

        edge_payloads = payload.get("edges", {})
        if not isinstance(edge_payloads, dict):
            return

        for edge_record in edge_payloads.values():
            if not isinstance(edge_record, dict):
                continue
            regime = MicrostructureRegime(str(edge_record["regime"]))
            edge = EdgeKey(
                from_state=str(edge_record["from_state"]),
                to_state=str(edge_record["to_state"]),
                regime=regime,
            )
            stats = EdgeStatistics(
                count=int(edge_record.get("count", 0)),
                holding_times_ns=[int(value) for value in edge_record.get("holding_times_ns", [])],
                drift_samples_bps=[float(value) for value in edge_record.get("drift_samples_bps", [])],
                session_drift_means_bps=[
                    float(value) for value in edge_record.get("session_drift_means_bps", [])
                ],
                directional_consensus=float(edge_record.get("directional_consensus", 0.0)),
                last_observation_index=int(edge_record.get("count", 0)),
            )
            self.edge_stats[edge] = stats
            self.outgoing_counts[(edge.from_state, edge.regime)][edge.to_state] = stats.count
