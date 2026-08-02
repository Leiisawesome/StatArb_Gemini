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
    cross_session_hit_rates: list[float] = field(default_factory=list)
    cross_session_hit_rate: float = 1.0
    cross_session_hit_consensus: float = 1.0
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
        # Prefer O(1) Welford stats when decisions use raw drift samples; session means
        # remain a short list and use pure-Python moments (avoid NumPy on every edge).
        if self.session_drift_means_bps:
            samples = self.session_drift_means_bps
            count = len(samples)
            if count < 2:
                return 0.0
            mean = sum(samples) / count
            variance = sum((value - mean) ** 2 for value in samples) / (count - 1)
            std = sqrt(max(variance, 0.0))
            return abs(mean) / max(std, 1e-6)
        if self._d_count < 2:
            return 0.0
        std = self.drift_std_bps
        return abs(self._d_mean) / std if std > 0 else 0.0

    @property
    def training_session_count(self) -> int:
        return len(self.session_drift_means_bps)

    @property
    def posterior_samples_bps(self) -> list[float]:
        return self.session_drift_means_bps or self.drift_samples_bps

    @property
    def decision_drift_mean_bps(self) -> float:
        if self.session_drift_means_bps:
            samples = self.session_drift_means_bps
            return sum(samples) / len(samples) if samples else 0.0
        return self.drift_mean_bps


@dataclass(frozen=True, slots=True)
class TransitionDiagnostic:
    edge: EdgeKey
    transition_probability: float
    entropy: float
    signal_to_noise: float
    alpha_score: float
    shrunk_drift_bps: float
    observation_count: int


@dataclass(frozen=True, slots=True)
class SoftEdgeComponent:
    """One regime-conditioned edge contributing to a soft mixture."""

    regime: MicrostructureRegime
    weight: float
    edge: EdgeKey
    stats: EdgeStatistics
    diagnostic: TransitionDiagnostic


@dataclass(frozen=True, slots=True)
class SoftEdgeView:
    """
    Decision-time mixture of regime-conditioned edges for a fixed (from, to) pair.

    Training still keys edges by a hard regime label; this view only mixes the
    historical readout using the current regime posterior mass.

    Hard (MAP-only) decisions are the degenerate case: one component with weight 1.
    """

    from_state: str
    to_state: str
    primary_edge: EdgeKey
    components: tuple[SoftEdgeComponent, ...]
    effective_count: float
    effective_training_sessions: float
    directional_consensus: float
    cross_session_hit_rate: float
    cross_session_hit_consensus: float
    transition_probability: float
    entropy: float
    signal_to_noise: float
    alpha_score: float
    shrunk_drift_bps: float
    regime_weights: dict[MicrostructureRegime, float]
    # Posterior mass on components that have at least one observation.
    supported_weight: float = 1.0

    @property
    def diagnostic(self) -> TransitionDiagnostic:
        return TransitionDiagnostic(
            edge=self.primary_edge,
            transition_probability=self.transition_probability,
            entropy=self.entropy,
            signal_to_noise=self.signal_to_noise,
            alpha_score=self.alpha_score,
            shrunk_drift_bps=self.shrunk_drift_bps,
            observation_count=int(round(self.effective_count)),
        )

    @classmethod
    def from_hard(
        cls,
        edge: EdgeKey,
        stats: EdgeStatistics,
        diagnostic: TransitionDiagnostic,
    ) -> SoftEdgeView:
        """Degenerate single-component view used by the unified decision path."""
        component = SoftEdgeComponent(
            regime=edge.regime,
            weight=1.0,
            edge=edge,
            stats=stats,
            diagnostic=diagnostic,
        )
        return cls(
            from_state=edge.from_state,
            to_state=edge.to_state,
            primary_edge=edge,
            components=(component,),
            effective_count=float(stats.count),
            effective_training_sessions=float(stats.training_session_count),
            directional_consensus=float(stats.directional_consensus),
            cross_session_hit_rate=float(stats.cross_session_hit_rate),
            cross_session_hit_consensus=float(stats.cross_session_hit_consensus),
            transition_probability=float(diagnostic.transition_probability),
            entropy=float(diagnostic.entropy),
            signal_to_noise=float(diagnostic.signal_to_noise),
            alpha_score=float(diagnostic.alpha_score),
            shrunk_drift_bps=float(diagnostic.shrunk_drift_bps),
            regime_weights={edge.regime: 1.0},
            supported_weight=1.0 if stats.count > 0 else 0.0,
        )


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
        # Vectors are small (5-D); avoid copy when already float arrays.
        previous = previous_vector if isinstance(previous_vector, np.ndarray) else np.asarray(previous_vector, dtype=float)
        current = current_vector if isinstance(current_vector, np.ndarray) else np.asarray(current_vector, dtype=float)
        delta = current - previous
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

    def soft_edge_view(
        self,
        from_state: str,
        to_state: str,
        regime_probabilities: dict[MicrostructureRegime, float],
        *,
        primary_regime: MicrostructureRegime | None = None,
        min_weight: float = 0.05,
    ) -> SoftEdgeView:
        """
        Mix historical edge readouts across regimes for a fixed cell transition.

        ``primary_regime`` is the MAP / recording regime used for edge identity
        and logging. Components with posterior mass below ``min_weight`` are
        dropped, then surviving weights are renormalized.
        """
        if primary_regime is None:
            primary_regime = max(regime_probabilities, key=regime_probabilities.get)

        primary_edge = EdgeKey(from_state, to_state, primary_regime)
        raw_weights = {
            regime: float(max(weight, 0.0))
            for regime, weight in regime_probabilities.items()
            if float(weight) >= float(min_weight)
        }
        if not raw_weights:
            raw_weights = {primary_regime: 1.0}

        weight_total = sum(raw_weights.values())
        if weight_total <= 0.0:
            normalized = {primary_regime: 1.0}
        else:
            normalized = {regime: weight / weight_total for regime, weight in raw_weights.items()}

        components: list[SoftEdgeComponent] = []
        for regime, weight in normalized.items():
            edge = EdgeKey(from_state, to_state, regime)
            stats = self.get_edge(edge)
            diagnostic = self.diagnostic(edge)
            components.append(
                SoftEdgeComponent(
                    regime=regime,
                    weight=weight,
                    edge=edge,
                    stats=stats,
                    diagnostic=diagnostic,
                )
            )
        components_tuple = tuple(components)
        supported = tuple(component for component in components_tuple if component.stats.count > 0)
        supported_weight = float(sum(component.weight for component in supported))
        # Gate metrics only over components that have data; mixture posterior still
        # sees full components (empty ones contribute nothing to samples).
        gate_components = supported if supported else components_tuple
        gate_total = sum(component.weight for component in gate_components) or 1.0

        def _weighted(getter, pool: tuple[SoftEdgeComponent, ...] = gate_components) -> float:
            return float(
                sum((component.weight / gate_total) * getter(component) for component in pool)
            )

        return SoftEdgeView(
            from_state=from_state,
            to_state=to_state,
            primary_edge=primary_edge,
            components=components_tuple,
            effective_count=_weighted(lambda c: float(c.stats.count)),
            effective_training_sessions=_weighted(lambda c: float(c.stats.training_session_count)),
            directional_consensus=_weighted(lambda c: float(c.stats.directional_consensus)),
            cross_session_hit_rate=_weighted(lambda c: float(c.stats.cross_session_hit_rate)),
            cross_session_hit_consensus=_weighted(lambda c: float(c.stats.cross_session_hit_consensus)),
            transition_probability=_weighted(lambda c: float(c.diagnostic.transition_probability)),
            entropy=_weighted(lambda c: float(c.diagnostic.entropy)),
            signal_to_noise=_weighted(lambda c: float(c.diagnostic.signal_to_noise)),
            alpha_score=_weighted(lambda c: float(c.diagnostic.alpha_score)),
            shrunk_drift_bps=_weighted(lambda c: float(c.diagnostic.shrunk_drift_bps)),
            regime_weights=dict(normalized),
            supported_weight=supported_weight,
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
                cross_session_hit_rates=[
                    float(value) for value in edge_record.get("cross_session_hit_rates", [])
                ],
                cross_session_hit_rate=float(edge_record.get("cross_session_hit_rate", 0.0)),
                cross_session_hit_consensus=float(edge_record.get("cross_session_hit_consensus", 0.0)),
                # A batch artifact is fresh at its publication boundary. An
                # edge count is not a position in the global observation
                # stream; treating it as one can age every fitted edge by
                # millions of observations and underflow its drift to zero.
                last_observation_index=int(
                    edge_record.get("last_observation_index", self.observation_index)
                ),
            )
            if not stats.holding_times_ns and stats.count > 0:
                stats._ht_count = stats.count
                stats._ht_mean = float(edge_record.get("mean_holding_time_ns", 0.0))
            if not stats.drift_samples_bps and stats.count > 0:
                stats._d_count = stats.count
                stats._d_mean = float(edge_record.get("drift_mean_bps", 0.0))
                drift_std_bps = float(edge_record.get("drift_std_bps", 0.0))
                stats._d_M2 = drift_std_bps * drift_std_bps * max(stats.count - 1, 0)
            self.edge_stats[edge] = stats
            self.outgoing_counts[(edge.from_state, edge.regime)][edge.to_state] = stats.count
