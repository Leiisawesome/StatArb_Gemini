"""Regime inference on separated time scales for the L1 state machine."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from math import exp
from typing import Deque

import numpy as np

from .calibration.interfaces import (
    RegimeCalibrationArtifact,
    RegimeDurationModel,
    RegimeEmissionModel,
)
from .config import FeatureConfig, RegimeConfig
from .features import FlickerState, ObservedState, SpreadState, VolatilityState
from .regime_transition import predict_regime_probabilities, stay_probability
from .stats.distributions import conditional_weibull_survival, diagonal_gaussian_log_likelihood

# Re-export for callers that historically imported survival from this module.
__all__ = [
    "MicrostructureRegime",
    "SlowContext",
    "RegimePosterior",
    "RegimeInferencer",
    "conditional_weibull_survival",
]


class MicrostructureRegime(str, Enum):
    CALM_LIQUIDITY = "calm_liquidity"
    EXECUTION_FLOW = "execution_flow"
    LIQUIDITY_SHOCK = "liquidity_shock"
    COMPETITIVE_LIQUIDITY = "competitive_liquidity"


@dataclass(frozen=True, slots=True)
class SlowContext:
    slow_volatility: float
    spread_persistence: float
    trade_intensity: float
    imbalance_persistence: float


@dataclass(frozen=True, slots=True)
class RegimePosterior:
    timestamp_ns: int
    probabilities: dict[MicrostructureRegime, float]
    dominant_regime: MicrostructureRegime
    confidence: float
    expected_holding_time_ns: int
    slow_context: SlowContext


class RegimeInferencer:
    REGIME_ORDER: tuple[MicrostructureRegime, ...] = (
        MicrostructureRegime.CALM_LIQUIDITY,
        MicrostructureRegime.EXECUTION_FLOW,
        MicrostructureRegime.LIQUIDITY_SHOCK,
        MicrostructureRegime.COMPETITIVE_LIQUIDITY,
    )

    def __init__(
        self,
        regime_config: RegimeConfig | None = None,
        feature_config: FeatureConfig | None = None,
        regime_calibration: RegimeCalibrationArtifact | None = None,
    ):
        self.config = regime_config or RegimeConfig()
        self.feature_config = feature_config or FeatureConfig()
        self.regime_calibration = regime_calibration
        self.state_window: Deque[ObservedState] = deque()
        self._slow_volatility_sum = 0.0
        self._wide_spread_count = 0
        self._trade_intensity_sum = 0.0
        self._imbalance_sum = 0.0
        self.previous_probabilities: dict[MicrostructureRegime, float] | None = None
        self.previous_timestamp_ns: int | None = None
        self.dominant_regime: MicrostructureRegime | None = None
        self.regime_started_at_ns: int | None = None
        # The state space is fixed at four regimes. Keep its transition constants
        # as scalar tuples so the per-event filter does not allocate tiny NumPy
        # arrays and matrices.
        self._cached_base_prior = tuple(self._base_prior(r) for r in self.REGIME_ORDER)
        self._cached_holding_times_ns = tuple(
            self._expected_holding_time_ns(r) for r in self.REGIME_ORDER
        )
        self._transition_leave_weights = tuple(
            self._leave_weights(row_index) for row_index in range(len(self.REGIME_ORDER))
        )
        self._emission_model = self._load_emission_model(regime_calibration)
        self._emission_feature_index = self._build_emission_feature_index(self._emission_model)
        self._duration_model = self._load_duration_model(regime_calibration)
        self._cached_duration_shapes = tuple(
            self._duration_shape(regime) for regime in self.REGIME_ORDER
        )
        self._use_hsmm = bool(
            self.config.use_hsmm_durations
            and self._duration_model is not None
            and self._duration_model.shapes
        )

    def update(self, state: ObservedState) -> RegimePosterior:
        self.state_window.append(state)
        self._add_to_context(state)
        self._prune(state.timestamp_ns)
        slow_context = self._slow_context()

        scores = {
            MicrostructureRegime.CALM_LIQUIDITY: self._calm_score(state, slow_context),
            MicrostructureRegime.EXECUTION_FLOW: self._execution_flow_score(state, slow_context),
            MicrostructureRegime.LIQUIDITY_SHOCK: self._liquidity_shock_score(state, slow_context),
            MicrostructureRegime.COMPETITIVE_LIQUIDITY: self._competitive_score(state, slow_context),
        }
        emission = self._resolve_emission_probabilities(state, scores)
        predicted = self._predicted_probabilities(state.timestamp_ns)
        probabilities = self._filtered_probabilities(predicted, emission)
        dominant_regime = max(probabilities, key=probabilities.get)
        confidence = probabilities[dominant_regime]
        expected_holding_time_ns = self._expected_holding_time_ns(dominant_regime)
        if self.dominant_regime != dominant_regime:
            self.dominant_regime = dominant_regime
            self.regime_started_at_ns = state.timestamp_ns
        self.previous_probabilities = probabilities
        self.previous_timestamp_ns = state.timestamp_ns

        return RegimePosterior(
            timestamp_ns=state.timestamp_ns,
            probabilities=probabilities,
            dominant_regime=dominant_regime,
            confidence=confidence,
            expected_holding_time_ns=expected_holding_time_ns,
            slow_context=slow_context,
        )

    def _prune(self, timestamp_ns: int) -> None:
        threshold_ns = timestamp_ns - int(self.feature_config.slow_context_window_seconds * 1_000_000_000)
        while self.state_window and self.state_window[0].timestamp_ns < threshold_ns:
            self._remove_from_context(self.state_window.popleft())

    def _slow_context(self) -> SlowContext:
        if not self.state_window:
            return SlowContext(0.0, 0.0, 0.0, 0.0)
        n = len(self.state_window)
        return SlowContext(
            slow_volatility=self._slow_volatility_sum / n,
            spread_persistence=self._wide_spread_count / n,
            trade_intensity=self._trade_intensity_sum / n,
            imbalance_persistence=self._imbalance_sum / n,
        )

    def rebuild_context_sums(self) -> None:
        self._slow_volatility_sum = 0.0
        self._wide_spread_count = 0
        self._trade_intensity_sum = 0.0
        self._imbalance_sum = 0.0
        for state in self.state_window:
            self._add_to_context(state)

    def _add_to_context(self, state: ObservedState) -> None:
        self._slow_volatility_sum += state.realized_volatility
        self._wide_spread_count += int(state.spread_state is SpreadState.WIDE)
        self._trade_intensity_sum += abs(state.trade_pressure)
        self._imbalance_sum += abs(state.quote_pressure)

    def _remove_from_context(self, state: ObservedState) -> None:
        self._slow_volatility_sum -= state.realized_volatility
        self._wide_spread_count -= int(state.spread_state is SpreadState.WIDE)
        self._trade_intensity_sum -= abs(state.trade_pressure)
        self._imbalance_sum -= abs(state.quote_pressure)

    def _calm_score(self, state: ObservedState, slow_context: SlowContext) -> float:
        score = 2.0
        score -= 2.0 * slow_context.slow_volatility * 10_000.0
        score -= 1.5 * state.flicker_intensity / max(self.feature_config.flicker_baseline_intensity, 1.0)
        score -= 1.5 * max(state.spread_norm - 1.0, 0.0)
        if state.volatility_state == VolatilityState.QUIET:
            score += 1.0
        if state.flicker_state == FlickerState.STABLE:
            score += 0.5
        return score

    def _execution_flow_score(self, state: ObservedState, slow_context: SlowContext) -> float:
        score = 0.5
        score += 3.0 * abs(state.trade_pressure)
        score += 1.5 * abs(state.quote_pressure)
        score += 1.0 * slow_context.trade_intensity
        if state.spread_state == SpreadState.NORMAL:
            score += 0.5
        return score

    def _liquidity_shock_score(self, state: ObservedState, slow_context: SlowContext) -> float:
        score = -0.5
        score += 2.0 * slow_context.spread_persistence
        score += 3.0 * state.realized_volatility * 10_000.0
        score += 1.2 * (state.flicker_intensity / max(self.feature_config.flicker_baseline_intensity, 1.0))
        if state.spread_state == SpreadState.WIDE:
            score += 1.0
        if state.volatility_state == VolatilityState.STRESSED:
            score += 1.0
        return score

    def _competitive_score(self, state: ObservedState, slow_context: SlowContext) -> float:
        score = 0.0
        score += 1.5 * (state.flicker_intensity / max(self.feature_config.flicker_baseline_intensity, 1.0))
        score += 0.75 * (1.0 - min(slow_context.slow_volatility * 10_000.0, 1.0))
        if state.spread_state == SpreadState.TIGHT:
            score += 1.0
        if state.flicker_state == FlickerState.COMPETITIVE:
            score += 0.75
        return score

    def _emission_probabilities(self, scores: dict[MicrostructureRegime, float]) -> dict[MicrostructureRegime, float]:
        values = tuple(scores[regime] for regime in self.REGIME_ORDER)
        maximum = max(values)
        weights = tuple(exp(value - maximum) for value in values)
        total = sum(weights)
        return {
            regime: max(weight / total, self.config.posterior_floor)
            for regime, weight in zip(self.REGIME_ORDER, weights)
        }

    def _resolve_emission_probabilities(
        self,
        state: ObservedState,
        scores: dict[MicrostructureRegime, float],
    ) -> dict[MicrostructureRegime, float]:
        heuristic = self._emission_probabilities(scores)
        if (
            self._emission_model is None
            or not self.config.use_fitted_emissions
            or not self._emission_feature_index
        ):
            return heuristic

        fitted = self._fitted_emission_probabilities(state)
        blend = min(max(float(self.config.emission_heuristic_blend), 0.0), 1.0)
        if blend <= 0.0:
            return fitted
        if blend >= 1.0:
            return heuristic

        mixed = {
            regime: (1.0 - blend) * fitted[regime] + blend * heuristic[regime]
            for regime in self.REGIME_ORDER
        }
        total = sum(mixed.values())
        if total <= 0.0:
            return heuristic
        return {regime: value / total for regime, value in mixed.items()}

    def _fitted_emission_probabilities(self, state: ObservedState) -> dict[MicrostructureRegime, float]:
        assert self._emission_model is not None
        features = self._emission_feature_vector(state)
        log_likelihoods = {
            regime: self._diagonal_gaussian_log_likelihood(
                features,
                self._emission_model.means.get(regime.value, ()),
                self._emission_model.stds.get(regime.value, ()),
            )
            for regime in self.REGIME_ORDER
        }
        maximum = max(log_likelihoods.values())
        weights = {
            regime: exp(log_likelihoods[regime] - maximum)
            for regime in self.REGIME_ORDER
        }
        total = sum(weights.values())
        floor = self.config.posterior_floor
        if total <= 0.0:
            return {regime: 1.0 / len(self.REGIME_ORDER) for regime in self.REGIME_ORDER}
        probabilities = {
            regime: max(weight / total, floor)
            for regime, weight in weights.items()
        }
        renorm = sum(probabilities.values())
        return {regime: value / renorm for regime, value in probabilities.items()}

    def _emission_feature_vector(self, state: ObservedState) -> tuple[float, ...]:
        accessors = {
            "spread_norm": lambda: float(state.spread_norm),
            "quote_pressure": lambda: float(state.quote_pressure),
            "trade_pressure": lambda: float(state.trade_pressure),
            "flicker_intensity": lambda: float(state.flicker_intensity),
            "realized_volatility": lambda: float(state.realized_volatility),
        }
        values: list[float] = []
        for name in self._emission_feature_index:
            getter = accessors.get(name)
            if getter is None:
                raise ValueError(
                    f"fitted emission model requests unsupported feature {name!r}; "
                    f"supported={sorted(accessors)}"
                )
            values.append(getter())
        return tuple(values)

    @staticmethod
    def _diagonal_gaussian_log_likelihood(
        observation: tuple[float, ...],
        mean: tuple[float, ...],
        std: tuple[float, ...],
    ) -> float:
        return diagonal_gaussian_log_likelihood(observation, mean, std)

    @staticmethod
    def _load_emission_model(
        regime_calibration: RegimeCalibrationArtifact | None,
    ) -> RegimeEmissionModel | None:
        if regime_calibration is None:
            return None
        model = regime_calibration.emission_model
        if model is None or not model.feature_names or not model.means or not model.stds:
            return None
        return model

    @staticmethod
    def _build_emission_feature_index(model: RegimeEmissionModel | None) -> tuple[str, ...]:
        if model is None:
            return ()
        return tuple(str(name) for name in model.feature_names)

    def _predicted_probabilities(self, timestamp_ns: int) -> dict[MicrostructureRegime, float]:
        if self.previous_probabilities is None or self.previous_timestamp_ns is None:
            return self._initial_probabilities()

        dt_ns = max(int(timestamp_ns - self.previous_timestamp_ns), 0)
        if dt_ns <= 0:
            return dict(self.previous_probabilities)

        floor = self.config.posterior_floor
        dwell_ns = 0
        if self.regime_started_at_ns is not None:
            dwell_ns = max(int(self.previous_timestamp_ns - self.regime_started_at_ns), 0)
        order = tuple(regime.value for regime in self.REGIME_ORDER)
        previous = {
            regime.value: self.previous_probabilities.get(regime, floor)
            for regime in self.REGIME_ORDER
        }
        leave_weights = {
            regime.value: self._transition_leave_weights[index]
            for index, regime in enumerate(self.REGIME_ORDER)
        }
        holding = {
            regime.value: self._cached_holding_times_ns[index]
            for index, regime in enumerate(self.REGIME_ORDER)
        }
        shapes = {
            regime.value: self._cached_duration_shapes[index]
            for index, regime in enumerate(self.REGIME_ORDER)
        }
        predicted = predict_regime_probabilities(
            previous,
            regime_order=order,
            dt_ns=dt_ns,
            holding_times_ns=holding,
            duration_shapes=shapes,
            leave_weights=leave_weights,
            dominant_regime=(
                self.dominant_regime.value if self.dominant_regime is not None else None
            ),
            dwell_ns=dwell_ns,
            use_hsmm=self._use_hsmm,
            floor=floor,
        )
        return {regime: predicted[regime.value] for regime in self.REGIME_ORDER}

    def _filtered_probabilities(
        self,
        predicted: dict[MicrostructureRegime, float],
        emission: dict[MicrostructureRegime, float],
    ) -> dict[MicrostructureRegime, float]:
        floor = self.config.posterior_floor
        unnormalized = tuple(
            max(predicted.get(regime, floor), floor)
            * max(emission.get(regime, floor), floor)
            for regime in self.REGIME_ORDER
        )
        total = sum(unnormalized)
        if total <= 0:
            return self._initial_probabilities()
        filtered = tuple(max(probability / total, floor) for probability in unnormalized)
        filtered_total = sum(filtered)
        return {
            regime: probability / filtered_total
            for regime, probability in zip(self.REGIME_ORDER, filtered)
        }

    def _transition_matrix(self, dt_ns: int) -> np.ndarray:
        rows: list[list[float]] = []
        floor = self.config.posterior_floor
        dwell_ns = 0
        if (
            self._use_hsmm
            and self.regime_started_at_ns is not None
            and self.previous_timestamp_ns is not None
        ):
            dwell_ns = max(int(self.previous_timestamp_ns - self.regime_started_at_ns), 0)
        for row_index, leave_weights in enumerate(self._transition_leave_weights):
            current_dwell = (
                dwell_ns if self.dominant_regime is self.REGIME_ORDER[row_index] else 0
            )
            stay = stay_probability(
                dwell_ns=current_dwell,
                dt_ns=dt_ns,
                mean_holding_ns=self._cached_holding_times_ns[row_index],
                duration_shape=self._cached_duration_shapes[row_index],
                use_hsmm=self._use_hsmm,
                floor=floor,
            )
            leave_mass = max(1.0 - stay, 0.0)
            row = [leave_mass * weight for weight in leave_weights]
            row[row_index] = stay
            rows.append(row)
        return np.asarray(rows, dtype=float)

    def _initial_probabilities(self) -> dict[MicrostructureRegime, float]:
        priors = tuple(max(prior, self.config.posterior_floor) for prior in self._cached_base_prior)
        total = sum(priors)
        return {
            regime: probability / total
            for regime, probability in zip(self.REGIME_ORDER, priors)
        }

    def _leave_weights(self, row_index: int) -> tuple[float, ...]:
        weights = tuple(
            0.0 if index == row_index else prior
            for index, prior in enumerate(self._cached_base_prior)
        )
        total = sum(weights)
        if total <= 0:
            denominator = max(len(self.REGIME_ORDER) - 1, 1)
            return tuple(0.0 if index == row_index else 1.0 / denominator for index in range(len(weights)))
        return tuple(weight / total for weight in weights)

    def _base_prior(self, regime: MicrostructureRegime) -> float:
        if self.regime_calibration is not None:
            return max(
                float(self.regime_calibration.regime_priors.get(regime.value, self.config.posterior_floor)),
                self.config.posterior_floor,
            )
        return 1.0 / len(self.REGIME_ORDER)

    def _expected_holding_time_ns(self, regime: MicrostructureRegime) -> int:
        if self.regime_calibration is not None:
            calibrated_seconds = self.regime_calibration.holding_time_seconds.get(regime.value)
            if calibrated_seconds is not None:
                return int(float(calibrated_seconds) * 1_000_000_000)
        seconds = {
            MicrostructureRegime.CALM_LIQUIDITY: self.config.calm_holding_time_seconds,
            MicrostructureRegime.EXECUTION_FLOW: self.config.execution_flow_holding_time_seconds,
            MicrostructureRegime.LIQUIDITY_SHOCK: self.config.liquidity_shock_holding_time_seconds,
            MicrostructureRegime.COMPETITIVE_LIQUIDITY: self.config.competitive_liquidity_holding_time_seconds,
        }[regime]
        return int(seconds * 1_000_000_000)

    def _duration_shape(self, regime: MicrostructureRegime) -> float:
        default = max(float(self.config.default_duration_shape), 1e-6)
        if self._duration_model is None:
            return default
        return max(float(self._duration_model.shapes.get(regime.value, default)), 1e-6)

    @staticmethod
    def _load_duration_model(
        regime_calibration: RegimeCalibrationArtifact | None,
    ) -> RegimeDurationModel | None:
        if regime_calibration is None:
            return None
        model = regime_calibration.duration_model
        if model is None or not model.shapes:
            return None
        return model
