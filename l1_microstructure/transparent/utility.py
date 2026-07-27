"""Explained execution- and risk-adjusted expected-utility decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import exp
from typing import Iterable

import numpy as np

from l1_microstructure.calibration.interfaces import ExecutionCalibrationArtifact
from l1_microstructure.decision import TradeAction
from l1_microstructure.features import ObservedState

from .contracts import TRANSPARENT_ENGINE_VERSION
from .edges import HierarchicalDriftPosterior


@dataclass(frozen=True, slots=True)
class UtilityCalibrationSample:
    timestamp_ns: int
    horizon_ns: int
    filled: bool
    alignment_probability: float
    spread_bps: float
    slippage_bps: float
    symbol: str | None = None

    def __post_init__(self) -> None:
        if self.timestamp_ns < 0 or self.horizon_ns <= 0:
            raise ValueError("utility calibration sample identity is invalid")
        if not 0.0 <= self.alignment_probability <= 1.0:
            raise ValueError("utility alignment probability must be in [0, 1]")
        if self.spread_bps < 0.0 or self.slippage_bps < 0.0:
            raise ValueError("utility execution costs cannot be negative")
        if self.symbol is not None and not self.symbol:
            raise ValueError("utility calibration symbol cannot be empty")


@dataclass(frozen=True, slots=True)
class UtilityModel:
    symbol: str
    fill_intercept: float
    fill_alignment_weight: float
    fill_spread_penalty: float
    slippage_bps_by_horizon: dict[str, float]
    fill_multiplier_by_regime: dict[str, float]
    slippage_multiplier_by_regime: dict[str, float]
    fixed_cost_bps: float
    uncertainty_penalty_multiplier: float
    risk_penalty_bps: float
    minimum_expected_utility_bps: float
    train_start_ns: int
    train_end_ns: int
    sample_count: int
    engine_version: str = TRANSPARENT_ENGINE_VERSION
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.engine_version != TRANSPARENT_ENGINE_VERSION:
            raise ValueError("utility model requires engine version v2")
        if not self.symbol:
            raise ValueError("utility model symbol cannot be empty")
        if self.fill_alignment_weight < 0.0 or self.fill_spread_penalty < 0.0:
            raise ValueError("utility fill coefficients have invalid signs")
        if any(value < 0.0 for value in self.slippage_bps_by_horizon.values()):
            raise ValueError("utility slippage estimates cannot be negative")
        if any(value < 0.0 for value in self.fill_multiplier_by_regime.values()) or any(
            value < 0.0 for value in self.slippage_multiplier_by_regime.values()
        ):
            raise ValueError("utility regime execution multipliers cannot be negative")
        if self.fixed_cost_bps < 0.0 or self.uncertainty_penalty_multiplier < 0.0 or self.risk_penalty_bps < 0.0:
            raise ValueError("utility penalties cannot be negative")
        if self.sample_count <= 0 or self.train_start_ns > self.train_end_ns:
            raise ValueError("utility training metadata is invalid")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> UtilityModel:
        return cls(
            symbol=str(payload["symbol"]),
            fill_intercept=float(payload["fill_intercept"]),
            fill_alignment_weight=float(payload["fill_alignment_weight"]),
            fill_spread_penalty=float(payload["fill_spread_penalty"]),
            slippage_bps_by_horizon={
                str(key): float(value) for key, value in dict(payload["slippage_bps_by_horizon"]).items()
            },
            fill_multiplier_by_regime={
                str(key): float(value)
                for key, value in dict(payload.get("fill_multiplier_by_regime", {})).items()
            },
            slippage_multiplier_by_regime={
                str(key): float(value)
                for key, value in dict(payload.get("slippage_multiplier_by_regime", {})).items()
            },
            fixed_cost_bps=float(payload["fixed_cost_bps"]),
            uncertainty_penalty_multiplier=float(payload["uncertainty_penalty_multiplier"]),
            risk_penalty_bps=float(payload["risk_penalty_bps"]),
            minimum_expected_utility_bps=float(payload["minimum_expected_utility_bps"]),
            train_start_ns=int(payload["train_start_ns"]),
            train_end_ns=int(payload["train_end_ns"]),
            sample_count=int(payload["sample_count"]),
            engine_version=str(payload.get("engine_version", "")),
            metadata=dict(payload.get("metadata", {})),
        )

    @classmethod
    def from_execution_calibration(
        cls,
        calibration: ExecutionCalibrationArtifact,
        horizons_ns: Iterable[int],
        *,
        train_start_ns: int,
        train_end_ns: int,
        fixed_cost_bps: float,
    ) -> UtilityModel:
        horizons = tuple(sorted({int(value) for value in horizons_ns if int(value) > 0}))
        if not horizons:
            raise ValueError("utility conversion requires positive horizons")
        if fixed_cost_bps < 0.0:
            raise ValueError("utility conversion fixed cost cannot be negative")
        sample_count = max(
            int(calibration.metadata.get("transition_row_count", calibration.metadata.get("row_count", 1))),
            1,
        )
        return cls(
            symbol=calibration.symbol,
            fill_intercept=float(calibration.fill_probability_intercept),
            fill_alignment_weight=float(max(calibration.alignment_weight, 0.0)),
            fill_spread_penalty=float(max(calibration.spread_penalty, 0.0)),
            slippage_bps_by_horizon={
                str(horizon): float(max(calibration.slippage_intercept_bps, 0.0)) for horizon in horizons
            },
            fill_multiplier_by_regime={
                str(key): float(max(value, 0.0))
                for key, value in calibration.regime_fill_multipliers.items()
            },
            slippage_multiplier_by_regime={
                str(key): float(max(value, 0.0))
                for key, value in calibration.regime_slippage_multipliers.items()
            },
            fixed_cost_bps=float(fixed_cost_bps),
            uncertainty_penalty_multiplier=1.0,
            risk_penalty_bps=2.0,
            minimum_expected_utility_bps=0.0,
            train_start_ns=int(train_start_ns),
            train_end_ns=int(train_end_ns),
            sample_count=sample_count,
            metadata={
                "trainer": "execution_calibration_adapter",
                "source_method": calibration.metadata.get("method", "unknown"),
            },
        )


class UtilityModelTrainer:
    def __init__(
        self,
        *,
        fixed_cost_bps: float = 1.2,
        uncertainty_penalty_multiplier: float = 1.0,
        risk_penalty_bps: float = 2.0,
        minimum_expected_utility_bps: float = 0.0,
        learning_rate: float = 0.05,
        iterations: int = 500,
    ) -> None:
        if min(
            fixed_cost_bps,
            uncertainty_penalty_multiplier,
            risk_penalty_bps,
            minimum_expected_utility_bps,
        ) < 0.0:
            raise ValueError("utility trainer penalties cannot be negative")
        if learning_rate <= 0.0 or iterations <= 0:
            raise ValueError("utility trainer optimizer configuration is invalid")
        self.fixed_cost_bps = fixed_cost_bps
        self.uncertainty_penalty_multiplier = uncertainty_penalty_multiplier
        self.risk_penalty_bps = risk_penalty_bps
        self.minimum_expected_utility_bps = minimum_expected_utility_bps
        self.learning_rate = learning_rate
        self.iterations = iterations

    def fit(
        self,
        samples: Iterable[UtilityCalibrationSample],
        *,
        symbol: str,
        train_start_ns: int,
        train_end_ns: int,
    ) -> UtilityModel:
        values = tuple(samples)
        if not values:
            raise ValueError("utility model training requires execution samples")
        if not symbol or any(sample.symbol not in {None, symbol} for sample in values):
            raise ValueError("utility training samples do not match the model symbol")
        if any(not train_start_ns <= sample.timestamp_ns <= train_end_ns for sample in values):
            raise ValueError("utility training data crosses the declared training boundary")
        features = np.asarray(
            [[1.0, sample.alignment_probability, -sample.spread_bps] for sample in values],
            dtype=float,
        )
        targets = np.asarray([float(sample.filled) for sample in values], dtype=float)
        coefficients = np.zeros(3, dtype=float)
        for _ in range(self.iterations):
            scores = np.clip(features @ coefficients, -30.0, 30.0)
            probabilities = 1.0 / (1.0 + np.exp(-scores))
            gradient = features.T @ (probabilities - targets) / len(values)
            coefficients -= self.learning_rate * gradient
        coefficients[1] = max(coefficients[1], 0.0)
        coefficients[2] = max(coefficients[2], 0.0)

        slippage: dict[str, list[float]] = {}
        for sample in values:
            slippage.setdefault(str(sample.horizon_ns), []).append(sample.slippage_bps)
        return UtilityModel(
            symbol=symbol,
            fill_intercept=float(coefficients[0]),
            fill_alignment_weight=float(coefficients[1]),
            fill_spread_penalty=float(coefficients[2]),
            slippage_bps_by_horizon={key: float(np.mean(items)) for key, items in slippage.items()},
            fill_multiplier_by_regime={},
            slippage_multiplier_by_regime={},
            fixed_cost_bps=self.fixed_cost_bps,
            uncertainty_penalty_multiplier=self.uncertainty_penalty_multiplier,
            risk_penalty_bps=self.risk_penalty_bps,
            minimum_expected_utility_bps=self.minimum_expected_utility_bps,
            train_start_ns=int(train_start_ns),
            train_end_ns=int(train_end_ns),
            sample_count=len(values),
            metadata={
                "trainer": "transparent_utility_model_trainer",
                "fill_model": "logistic_alignment_spread",
                "optimizer_iterations": self.iterations,
            },
        )


@dataclass(frozen=True, slots=True)
class UtilityAlternative:
    action: TradeAction
    horizon_ns: int
    expected_drift_bps: float
    expected_cost_bps: float
    fill_probability: float
    transition_probability: float
    uncertainty_penalty_bps: float
    risk_penalty_bps: float
    expected_utility_bps: float

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["action"] = self.action.value
        return payload


@dataclass(frozen=True, slots=True)
class UtilityDecision:
    action: TradeAction
    horizon_ns: int
    expected_utility_bps: float
    reason: str
    alternatives: tuple[UtilityAlternative, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action.value,
            "horizon_ns": self.horizon_ns,
            "expected_utility_bps": self.expected_utility_bps,
            "reason": self.reason,
            "alternatives": [alternative.to_dict() for alternative in self.alternatives],
        }


class ExpectedUtilityDecisionEngine:
    def __init__(self, model: UtilityModel):
        self.model = model

    def decide(
        self,
        posteriors: Iterable[HierarchicalDriftPosterior],
        state: ObservedState,
        *,
        alignment_probability: float,
        transition_probability: float,
        current_risk_fraction: float,
        regime: str | None = None,
    ) -> UtilityDecision:
        spread_bps = state.book.spread / max(state.book.midpoint, 1e-9) * 10_000.0
        return self.decide_for_spread(
            posteriors,
            spread_bps=spread_bps,
            alignment_probability=alignment_probability,
            transition_probability=transition_probability,
            current_risk_fraction=current_risk_fraction,
            regime=regime,
        )

    def decide_for_spread(
        self,
        posteriors: Iterable[HierarchicalDriftPosterior],
        *,
        spread_bps: float,
        alignment_probability: float,
        transition_probability: float,
        current_risk_fraction: float,
        regime: str | None = None,
    ) -> UtilityDecision:
        """Choose an action from sufficient, serializable execution inputs."""
        if not 0.0 <= alignment_probability <= 1.0 or not 0.0 <= transition_probability <= 1.0:
            raise ValueError("utility decision probabilities must be in [0, 1]")
        if spread_bps < 0.0 or current_risk_fraction < 0.0:
            raise ValueError("utility decision spread and risk fraction cannot be negative")
        estimates = tuple(posteriors)
        if not estimates:
            raise ValueError("utility decision requires at least one horizon posterior")
        regime_fill_multiplier = self.model.fill_multiplier_by_regime.get(regime or "", 1.0)
        regime_slippage_multiplier = self.model.slippage_multiplier_by_regime.get(regime or "", 1.0)
        fill_probability = min(
            self._fill_probability(alignment_probability, spread_bps)
            * regime_fill_multiplier,
            1.0,
        )
        alternatives: list[UtilityAlternative] = []
        for posterior in estimates:
            slippage = self.model.slippage_bps_by_horizon.get(
                str(posterior.horizon_ns),
                max(self.model.slippage_bps_by_horizon.values(), default=0.0),
            )
            slippage *= regime_slippage_multiplier
            cost = self.model.fixed_cost_bps + slippage
            uncertainty = self.model.uncertainty_penalty_multiplier * posterior.std_bps
            risk_penalty = self.model.risk_penalty_bps * current_risk_fraction
            for action, direction in ((TradeAction.BUY, 1.0), (TradeAction.SELL, -1.0)):
                directional_drift = direction * posterior.mean_bps
                utility = fill_probability * (directional_drift - cost) - uncertainty - risk_penalty
                alternatives.append(
                    UtilityAlternative(
                        action=action,
                        horizon_ns=posterior.horizon_ns,
                        expected_drift_bps=float(directional_drift),
                        expected_cost_bps=float(cost),
                        fill_probability=float(fill_probability),
                        transition_probability=float(transition_probability),
                        uncertainty_penalty_bps=float(uncertainty),
                        risk_penalty_bps=float(risk_penalty),
                        expected_utility_bps=float(utility),
                    )
                )
        ordered = tuple(sorted(alternatives, key=lambda item: (-item.expected_utility_bps, item.horizon_ns, item.action.value)))
        best = ordered[0]
        if best.expected_utility_bps <= self.model.minimum_expected_utility_bps:
            return UtilityDecision(
                TradeAction.HOLD,
                best.horizon_ns,
                0.0,
                "no action has positive cost- and risk-adjusted utility",
                ordered,
            )
        return UtilityDecision(
            best.action,
            best.horizon_ns,
            best.expected_utility_bps,
            "selected maximum positive expected utility",
            ordered,
        )

    def _fill_probability(self, alignment_probability: float, spread_bps: float) -> float:
        score = (
            self.model.fill_intercept
            + self.model.fill_alignment_weight * alignment_probability
            - self.model.fill_spread_penalty * spread_bps
        )
        return float(1.0 / (1.0 + exp(-min(max(score, -30.0), 30.0))))
