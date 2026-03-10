"""Regime inference on separated time scales for the L1 state machine."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
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
        probabilities = self._softmax(scores)
        dominant_regime = max(probabilities, key=probabilities.get)
        confidence = probabilities[dominant_regime]
        expected_holding_time_ns = self._expected_holding_time_ns(dominant_regime)

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

        volatility = float(np.mean([state.realized_volatility for state in self.state_window]))
        spread_persistence = float(
            np.mean([1.0 if state.spread_state is SpreadState.WIDE else 0.0 for state in self.state_window])
        )
        trade_intensity = float(
            np.mean([abs(state.trade_pressure) for state in self.state_window])
        )
        imbalance_persistence = float(
            np.mean([abs(state.quote_pressure) for state in self.state_window])
        )
        return SlowContext(
            slow_volatility=volatility,
            spread_persistence=spread_persistence,
            trade_intensity=trade_intensity,
            imbalance_persistence=imbalance_persistence,
        )

    def _calm_score(self, state: ObservedState, slow_context: SlowContext) -> float:
        score = 2.0
        score -= 2.0 * slow_context.slow_volatility * 10_000.0
        score -= 1.5 * state.flicker_intensity / max(self.feature_config.flicker_baseline_intensity, 1.0)
        score -= 1.5 * max(state.spread_norm - 1.0, 0.0)
        if state.volatility_state is VolatilityState.QUIET:
            score += 1.0
        if state.flicker_state is FlickerState.STABLE:
            score += 0.5
        return score

    def _execution_flow_score(self, state: ObservedState, slow_context: SlowContext) -> float:
        score = 0.5
        score += 3.0 * abs(state.trade_pressure)
        score += 1.5 * abs(state.quote_pressure)
        score += 1.0 * slow_context.trade_intensity
        if state.spread_state is SpreadState.NORMAL:
            score += 0.5
        return score

    def _liquidity_shock_score(self, state: ObservedState, slow_context: SlowContext) -> float:
        score = -0.5
        score += 2.0 * slow_context.spread_persistence
        score += 3.0 * state.realized_volatility * 10_000.0
        score += 1.2 * (state.flicker_intensity / max(self.feature_config.flicker_baseline_intensity, 1.0))
        if state.spread_state is SpreadState.WIDE:
            score += 1.0
        if state.volatility_state is VolatilityState.STRESSED:
            score += 1.0
        return score

    def _competitive_score(self, state: ObservedState, slow_context: SlowContext) -> float:
        score = 0.0
        score += 1.5 * (state.flicker_intensity / max(self.feature_config.flicker_baseline_intensity, 1.0))
        score += 0.75 * (1.0 - min(slow_context.slow_volatility * 10_000.0, 1.0))
        if state.spread_state is SpreadState.TIGHT:
            score += 1.0
        if state.flicker_state is FlickerState.COMPETITIVE:
            score += 0.75
        return score

    def _softmax(self, scores: dict[MicrostructureRegime, float]) -> dict[MicrostructureRegime, float]:
        values = np.array(list(scores.values()), dtype=float)
        shifted = values - np.max(values)
        probabilities = np.exp(shifted)
        if self.regime_calibration is not None:
            priors = np.array(
                [
                    max(
                        float(self.regime_calibration.regime_priors.get(regime.value, self.config.posterior_floor)),
                        self.config.posterior_floor,
                    )
                    for regime in scores.keys()
                ],
                dtype=float,
            )
            probabilities *= priors
        probabilities /= np.sum(probabilities)
        return {
            regime: float(max(probability, self.config.posterior_floor))
            for regime, probability in zip(scores.keys(), probabilities)
        }

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