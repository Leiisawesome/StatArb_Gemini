"""Bounded hierarchical Bayesian drift statistics for transparent transitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import erf, sqrt
from typing import Iterable

from l1_microstructure.training.interfaces import TransitionTrainingSample

from .contracts import TRANSPARENT_ENGINE_VERSION


@dataclass(slots=True)
class SufficientStatistics:
    effective_count: float = 0.0
    mean: float = 0.0
    m2: float = 0.0
    holding_count: float = 0.0
    holding_mean_ns: float = 0.0

    def update(self, drift_bps: float, holding_time_ns: int, *, decay: float = 1.0) -> None:
        if not 0.0 < decay <= 1.0:
            raise ValueError("sufficient-statistic decay must be in (0, 1]")
        if decay < 1.0:
            self.effective_count *= decay
            self.m2 *= decay
            self.holding_count *= decay
        self.effective_count += 1.0
        delta = float(drift_bps) - self.mean
        self.mean += delta / self.effective_count
        self.m2 += delta * (float(drift_bps) - self.mean)
        self.holding_count += 1.0
        self.holding_mean_ns += (float(holding_time_ns) - self.holding_mean_ns) / self.holding_count

    @property
    def variance(self) -> float:
        return self.m2 / max(self.effective_count - 1.0, 1.0)

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> SufficientStatistics:
        return cls(
            effective_count=float(payload.get("effective_count", 0.0)),
            mean=float(payload.get("mean", 0.0)),
            m2=float(payload.get("m2", 0.0)),
            holding_count=float(payload.get("holding_count", 0.0)),
            holding_mean_ns=float(payload.get("holding_mean_ns", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class HierarchicalTransitionModel:
    symbol: str
    horizons_ns: tuple[int, ...]
    statistics: dict[str, dict[str, dict[str, SufficientStatistics]]]
    exact_edge_keys: dict[str, tuple[str, ...]]
    prior_strength: float
    variance_floor_bps2: float
    online_decay: float
    max_exact_edges_per_horizon: int
    train_start_ns: int
    train_end_ns: int
    sample_count: int
    engine_version: str = TRANSPARENT_ENGINE_VERSION
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.engine_version != TRANSPARENT_ENGINE_VERSION:
            raise ValueError("hierarchical transition model requires engine version v2")
        if not self.horizons_ns or any(value <= 0 for value in self.horizons_ns):
            raise ValueError("hierarchical transition horizons must be positive")
        if (
            self.prior_strength <= 0.0
            or self.variance_floor_bps2 <= 0.0
            or not 0.0 < self.online_decay <= 1.0
        ):
            raise ValueError("hierarchical transition shrinkage configuration is invalid")
        if self.max_exact_edges_per_horizon <= 0 or self.sample_count <= 0:
            raise ValueError("hierarchical transition bounds are invalid")
        if self.train_start_ns > self.train_end_ns:
            raise ValueError("hierarchical transition training interval is invalid")
        expected = {str(value) for value in self.horizons_ns}
        if set(self.statistics) != expected or set(self.exact_edge_keys) != expected:
            raise ValueError("hierarchical transition horizon payload is incomplete")
        for horizon in expected:
            levels = self.statistics[horizon]
            if set(levels) != {"global", "regime", "from_state", "edge"}:
                raise ValueError("hierarchical transition levels are incomplete")
            if len(self.exact_edge_keys[horizon]) > self.max_exact_edges_per_horizon:
                raise ValueError("hierarchical transition exact-edge bound is exceeded")

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "horizons_ns": list(self.horizons_ns),
            "statistics": {
                horizon: {
                    level: {key: stats.to_dict() for key, stats in records.items()}
                    for level, records in levels.items()
                }
                for horizon, levels in self.statistics.items()
            },
            "exact_edge_keys": {horizon: list(keys) for horizon, keys in self.exact_edge_keys.items()},
            "prior_strength": self.prior_strength,
            "variance_floor_bps2": self.variance_floor_bps2,
            "online_decay": self.online_decay,
            "max_exact_edges_per_horizon": self.max_exact_edges_per_horizon,
            "train_start_ns": self.train_start_ns,
            "train_end_ns": self.train_end_ns,
            "sample_count": self.sample_count,
            "engine_version": self.engine_version,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> HierarchicalTransitionModel:
        raw_statistics = dict(payload["statistics"])
        return cls(
            symbol=str(payload["symbol"]),
            horizons_ns=tuple(int(value) for value in payload["horizons_ns"]),
            statistics={
                str(horizon): {
                    str(level): {
                        str(key): SufficientStatistics.from_dict(dict(stats))
                        for key, stats in dict(records).items()
                    }
                    for level, records in dict(levels).items()
                }
                for horizon, levels in raw_statistics.items()
            },
            exact_edge_keys={
                str(horizon): tuple(str(key) for key in keys)
                for horizon, keys in dict(payload["exact_edge_keys"]).items()
            },
            prior_strength=float(payload["prior_strength"]),
            variance_floor_bps2=float(payload.get("variance_floor_bps2", 0.25)),
            online_decay=float(payload["online_decay"]),
            max_exact_edges_per_horizon=int(payload["max_exact_edges_per_horizon"]),
            train_start_ns=int(payload["train_start_ns"]),
            train_end_ns=int(payload["train_end_ns"]),
            sample_count=int(payload["sample_count"]),
            engine_version=str(payload.get("engine_version", "")),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class HierarchicalDriftPosterior:
    horizon_ns: int
    mean_bps: float
    std_bps: float
    probability_up: float
    probability_down: float
    threshold_bps: float
    expected_holding_time_ns: int
    exact_edge_seen: bool
    exact_observation_count: float
    support: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class HierarchicalTransitionTrainer:
    def __init__(
        self,
        *,
        prior_strength: float = 20.0,
        variance_floor_bps2: float = 0.25,
        online_decay: float = 0.999,
        max_exact_edges_per_horizon: int = 2_048,
    ) -> None:
        if prior_strength <= 0.0 or variance_floor_bps2 <= 0.0 or not 0.0 < online_decay <= 1.0:
            raise ValueError("hierarchical trainer shrinkage configuration is invalid")
        if max_exact_edges_per_horizon <= 0:
            raise ValueError("hierarchical trainer exact-edge bound must be positive")
        self.prior_strength = prior_strength
        self.variance_floor_bps2 = variance_floor_bps2
        self.online_decay = online_decay
        self.max_exact_edges_per_horizon = max_exact_edges_per_horizon

    def fit(
        self,
        samples: Iterable[TransitionTrainingSample],
        *,
        train_start_ns: int,
        train_end_ns: int,
    ) -> HierarchicalTransitionModel:
        values = tuple(samples)
        if not values:
            raise ValueError("hierarchical transition training requires samples")
        symbols = {sample.symbol for sample in values}
        if len(symbols) != 1:
            raise ValueError("hierarchical transition training requires exactly one symbol")
        for sample in values:
            timestamp_ns = sample.metadata.get("timestamp_ns")
            end_timestamp_ns = sample.metadata.get("end_timestamp_ns", timestamp_ns)
            if timestamp_ns is not None and not train_start_ns <= int(timestamp_ns) <= train_end_ns:
                raise ValueError("hierarchical transition sample crosses the training boundary")
            if end_timestamp_ns is not None and int(end_timestamp_ns) > train_end_ns:
                raise ValueError("hierarchical transition outcome resolves after the training boundary")

        horizons = tuple(sorted({int(sample.horizon_ns) for sample in values if int(sample.horizon_ns) > 0}))
        if not horizons:
            raise ValueError("hierarchical transition samples require positive horizons")
        statistics: dict[str, dict[str, dict[str, SufficientStatistics]]] = {}
        exact_keys: dict[str, tuple[str, ...]] = {}
        for horizon_ns in horizons:
            horizon_samples = [sample for sample in values if int(sample.horizon_ns) == horizon_ns]
            exact_counts: dict[str, int] = {}
            for sample in horizon_samples:
                key = _edge_key(sample.regime, sample.from_state, sample.to_state)
                exact_counts[key] = exact_counts.get(key, 0) + 1
            retained = {
                key
                for key, _ in sorted(exact_counts.items(), key=lambda item: (-item[1], item[0]))[
                    : self.max_exact_edges_per_horizon
                ]
            }
            levels = {level: {} for level in ("global", "regime", "from_state", "edge")}
            for sample in horizon_samples:
                keys = (
                    ("global", "*"),
                    ("regime", sample.regime),
                    ("from_state", _from_state_key(sample.regime, sample.from_state)),
                )
                exact = _edge_key(sample.regime, sample.from_state, sample.to_state)
                for level, key in keys:
                    levels[level].setdefault(key, SufficientStatistics()).update(
                        sample.realized_drift_bps,
                        sample.holding_time_ns,
                    )
                if exact in retained:
                    levels["edge"].setdefault(exact, SufficientStatistics()).update(
                        sample.realized_drift_bps,
                        sample.holding_time_ns,
                    )
            statistics[str(horizon_ns)] = levels
            exact_keys[str(horizon_ns)] = tuple(sorted(retained))
        return HierarchicalTransitionModel(
            symbol=next(iter(symbols)),
            horizons_ns=horizons,
            statistics=statistics,
            exact_edge_keys=exact_keys,
            prior_strength=self.prior_strength,
            variance_floor_bps2=self.variance_floor_bps2,
            online_decay=self.online_decay,
            max_exact_edges_per_horizon=self.max_exact_edges_per_horizon,
            train_start_ns=int(train_start_ns),
            train_end_ns=int(train_end_ns),
            sample_count=len(values),
            metadata={
                "trainer": "hierarchical_transition_trainer",
                "bounded_sufficient_statistics": True,
            },
        )


class HierarchicalTransitionRuntime:
    def __init__(self, model: HierarchicalTransitionModel):
        self.model = model

    def posterior(
        self,
        *,
        from_state: str,
        to_state: str,
        regime: str,
        horizon_ns: int,
        threshold_bps: float,
    ) -> HierarchicalDriftPosterior:
        levels = self._levels(horizon_ns)
        hierarchy = (
            ("global", "*"),
            ("regime", regime),
            ("from_state", _from_state_key(regime, from_state)),
            ("edge", _edge_key(regime, from_state, to_state)),
        )
        available = [(level, levels[level].get(key)) for level, key in hierarchy]
        available = [(level, stats) for level, stats in available if stats is not None and stats.effective_count > 0]
        if not available:
            raise ValueError("hierarchical transition model contains no usable statistics")

        first_level, first = available[0]
        mean = first.mean
        variance = _predictive_variance(first, self.model.variance_floor_bps2)
        holding_time = first.holding_mean_ns
        support = {"global": 0.0, "regime": 0.0, "from_state": 0.0, "exact_edge": 0.0}
        support[_support_name(first_level)] = 1.0
        for level, stats in available[1:]:
            weight = stats.effective_count / (stats.effective_count + self.model.prior_strength)
            prior_mean = mean
            child_variance = _predictive_variance(stats, self.model.variance_floor_bps2)
            mean = weight * stats.mean + (1.0 - weight) * prior_mean
            # Parent and child samples are nested, not independent. Blend
            # predictive distributions with the law of total variance instead
            # of repeatedly shrinking the same observations as independent data.
            variance = weight * (child_variance + (stats.mean - mean) ** 2) + (
                1.0 - weight
            ) * (variance + (prior_mean - mean) ** 2)
            holding_time = weight * stats.holding_mean_ns + (1.0 - weight) * holding_time
            support = {key: value * (1.0 - weight) for key, value in support.items()}
            support[_support_name(level)] += weight

        std = sqrt(max(variance, 1e-9))
        probability_up = 1.0 - _normal_cdf(mean, std, threshold_bps)
        probability_down = _normal_cdf(mean, std, -threshold_bps)
        exact = levels["edge"].get(_edge_key(regime, from_state, to_state))
        return HierarchicalDriftPosterior(
            horizon_ns=int(horizon_ns),
            mean_bps=float(mean),
            std_bps=float(std),
            probability_up=float(probability_up),
            probability_down=float(probability_down),
            threshold_bps=float(threshold_bps),
            expected_holding_time_ns=int(max(holding_time, 0.0)),
            exact_edge_seen=exact is not None,
            exact_observation_count=0.0 if exact is None else float(exact.effective_count),
            support={key: float(value) for key, value in support.items()},
        )

    def observe(
        self,
        *,
        from_state: str,
        to_state: str,
        regime: str,
        horizon_ns: int,
        drift_bps: float,
        holding_time_ns: int,
    ) -> None:
        levels = self._levels(horizon_ns)
        for level, key in (
            ("global", "*"),
            ("regime", regime),
            ("from_state", _from_state_key(regime, from_state)),
        ):
            levels[level].setdefault(key, SufficientStatistics()).update(
                drift_bps,
                holding_time_ns,
                decay=self.model.online_decay,
            )
        exact_key = _edge_key(regime, from_state, to_state)
        if exact_key in set(self.model.exact_edge_keys[str(int(horizon_ns))]):
            levels["edge"].setdefault(exact_key, SufficientStatistics()).update(
                drift_bps,
                holding_time_ns,
                decay=self.model.online_decay,
            )

    def _levels(self, horizon_ns: int) -> dict[str, dict[str, SufficientStatistics]]:
        key = str(int(horizon_ns))
        if key not in self.model.statistics:
            raise ValueError(f"unsupported hierarchical transition horizon: {horizon_ns}")
        return self.model.statistics[key]


def _normal_cdf(mean: float, std: float, threshold: float) -> float:
    z = (threshold - mean) / max(std, 1e-9)
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def _predictive_variance(stats: SufficientStatistics, floor_bps2: float) -> float:
    observation_variance = max(stats.variance, floor_bps2)
    return observation_variance * (1.0 + 1.0 / max(stats.effective_count, 1.0))


def _from_state_key(regime: str, from_state: str) -> str:
    return f"{regime}::{from_state}"


def _edge_key(regime: str, from_state: str, to_state: str) -> str:
    return f"{regime}::{from_state}::{to_state}"


def _support_name(level: str) -> str:
    return "exact_edge" if level == "edge" else level
