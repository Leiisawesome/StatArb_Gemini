"""Regime inference on separated time scales for the L1 state machine."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from math import exp
from typing import Deque

import numpy as np

from .calibration.interfaces import RegimeCalibrationArtifact
from .config import FeatureConfig, RegimeConfig
from .features import FlickerState, ObservedState, SpreadState, VolatilityState


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
        self.previous_probabilities: dict[MicrostructureRegime, float] | None = None
        self.previous_timestamp_ns: int | None = None
        # Precompute transition-matrix constants — these only depend on calibration (set once)
        self._cached_base_prior = np.array(
            [self._base_prior(r) for r in self.REGIME_ORDER], dtype=float
        )
        self._cached_holding_times_ns = np.array(
            [self._expected_holding_time_ns(r) for r in self.REGIME_ORDER], dtype=np.int64
        )
        n = len(self.REGIME_ORDER)
        self._off_diagonal_masks = np.ones((n, n), dtype=float) - np.eye(n, dtype=float)

    def update(self, state: ObservedState) -> RegimePosterior:
        self.state_window.append(state)
        self._prune(state.timestamp_ns)
        slow_context = self._slow_context()

        scores = {
            MicrostructureRegime.CALM_LIQUIDITY: self._calm_score(state, slow_context),
            MicrostructureRegime.EXECUTION_FLOW: self._execution_flow_score(state, slow_context),
            MicrostructureRegime.LIQUIDITY_SHOCK: self._liquidity_shock_score(state, slow_context),
            MicrostructureRegime.COMPETITIVE_LIQUIDITY: self._competitive_score(state, slow_context),
        }
        emission = self._emission_probabilities(scores)
        predicted = self._predicted_probabilities(state.timestamp_ns)
        probabilities = self._filtered_probabilities(predicted, emission)
        dominant_regime = max(probabilities, key=probabilities.get)
        confidence = probabilities[dominant_regime]
        expected_holding_time_ns = self._expected_holding_time_ns(dominant_regime)
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
            self.state_window.popleft()

    def _slow_context(self) -> SlowContext:
        if not self.state_window:
            return SlowContext(0.0, 0.0, 0.0, 0.0)
        n = len(self.state_window)
        sv = ss = st = si = 0.0
        wide = SpreadState.WIDE
        for state in self.state_window:
            sv += state.realized_volatility
            ss += 1.0 if state.spread_state is wide else 0.0
            st += abs(state.trade_pressure)
            si += abs(state.quote_pressure)
        return SlowContext(
            slow_volatility=sv / n,
            spread_persistence=ss / n,
            trade_intensity=st / n,
            imbalance_persistence=si / n,
        )

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
        values = np.array([scores[regime] for regime in self.REGIME_ORDER], dtype=float)
        shifted = values - np.max(values)
        probabilities = np.exp(shifted)
        probabilities /= np.sum(probabilities)
        return {
            regime: float(max(probability, self.config.posterior_floor))
            for regime, probability in zip(self.REGIME_ORDER, probabilities)
        }

    def _predicted_probabilities(self, timestamp_ns: int) -> dict[MicrostructureRegime, float]:
        if self.previous_probabilities is None or self.previous_timestamp_ns is None:
            return self._initial_probabilities()

        dt_ns = max(int(timestamp_ns - self.previous_timestamp_ns), 0)
        if dt_ns <= 0:
            return dict(self.previous_probabilities)

        transition = self._transition_matrix(dt_ns)
        previous = np.array([self.previous_probabilities.get(regime, self.config.posterior_floor) for regime in self.REGIME_ORDER], dtype=float)
        predicted = previous @ transition
        predicted = np.maximum(predicted, self.config.posterior_floor)
        predicted /= np.sum(predicted)
        return {
            regime: float(probability)
            for regime, probability in zip(self.REGIME_ORDER, predicted)
        }

    def _filtered_probabilities(
        self,
        predicted: dict[MicrostructureRegime, float],
        emission: dict[MicrostructureRegime, float],
    ) -> dict[MicrostructureRegime, float]:
        unnormalized = np.array(
            [
                max(predicted.get(regime, self.config.posterior_floor), self.config.posterior_floor)
                * max(emission.get(regime, self.config.posterior_floor), self.config.posterior_floor)
                for regime in self.REGIME_ORDER
            ],
            dtype=float,
        )
        total = float(np.sum(unnormalized))
        if total <= 0:
            return self._initial_probabilities()
        filtered = np.maximum(unnormalized / total, self.config.posterior_floor)
        filtered /= np.sum(filtered)
        return {
            regime: float(probability)
            for regime, probability in zip(self.REGIME_ORDER, filtered)
        }

    def _transition_matrix(self, dt_ns: int) -> np.ndarray:
        base_prior = self._cached_base_prior
        n = len(self.REGIME_ORDER)
        matrix = np.zeros((n, n), dtype=float)
        for row_index in range(n):
            holding_time_ns = max(int(self._cached_holding_times_ns[row_index]), 1)
            stay_probability = exp(-dt_ns / holding_time_ns)
            stay_probability = min(max(stay_probability, self.config.posterior_floor), 1.0)
            leave_mass = max(1.0 - stay_probability, 0.0)

            off_diagonal = base_prior * self._off_diagonal_masks[row_index]
            off_diagonal_total = float(np.sum(off_diagonal))
            if off_diagonal_total <= 0:
                off_diagonal = self._off_diagonal_masks[row_index] / max(n - 1, 1)
                off_diagonal_total = float(np.sum(off_diagonal))

            matrix[row_index, :] = leave_mass * (off_diagonal / off_diagonal_total)
            matrix[row_index, row_index] = stay_probability
        return matrix

    def _initial_probabilities(self) -> dict[MicrostructureRegime, float]:
        priors = np.array([self._base_prior(regime) for regime in self.REGIME_ORDER], dtype=float)
        priors = np.maximum(priors, self.config.posterior_floor)
        priors /= np.sum(priors)
        return {
            regime: float(probability)
            for regime, probability in zip(self.REGIME_ORDER, priors)
        }

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