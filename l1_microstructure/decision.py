"""Bayesian decision logic for microstructure transition edges."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import erf, sqrt

import numpy as np

from .config import DecisionConfig, TransitionConfig
from .features import ObservedState
from .regime import RegimePosterior
from .transitions import EdgeKey, EdgeStatistics, TransitionDiagnostic


class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    EXIT = "exit"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class PosteriorEstimate:
    mean_bps: float
    std_bps: float
    probability_up: float
    probability_down: float
    threshold_bps: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class TradeIntent:
    action: TradeAction
    edge: EdgeKey
    posterior: PosteriorEstimate
    expected_holding_time_ns: int
    reason: str
    observation_confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class ExitHazardEstimate:
    total_hazard: float
    dominant_hazard: float
    dominant_cause: str
    components: dict[str, float]
    reason: str


class DecisionEngine:
    def __init__(
        self,
        decision_config: DecisionConfig | None = None,
        transition_config: TransitionConfig | None = None,
    ):
        self.config = decision_config or DecisionConfig()
        self.transition_config = transition_config or TransitionConfig()

    def estimate_posterior(self, samples: list[float], threshold_bps: float) -> PosteriorEstimate:
        if not samples:
            return PosteriorEstimate(0.0, float("inf"), 0.5, 0.5, threshold_bps, 0)

        data = np.array(samples, dtype=float)
        sample_count = data.size
        sample_mean = float(np.mean(data))
        centered = data - sample_mean
        sample_ss = float(np.sum(centered * centered))

        mu0 = self.config.posterior_prior_mean_bps
        kappa0 = self.config.posterior_prior_strength
        alpha0 = self.config.posterior_prior_alpha
        beta0 = self.config.posterior_prior_beta

        kappa_n = kappa0 + sample_count
        mu_n = (kappa0 * mu0 + sample_count * sample_mean) / kappa_n
        alpha_n = alpha0 + sample_count / 2.0
        beta_n = beta0 + 0.5 * sample_ss + (
            kappa0 * sample_count * (sample_mean - mu0) ** 2
        ) / (2.0 * kappa_n)

        mean_std = sqrt(max(beta_n / (alpha_n * kappa_n), 1e-9))
        probability_up = self._normal_tail_probability(mu_n, mean_std, threshold_bps)
        probability_down = self._normal_cdf(mu_n, mean_std, -threshold_bps)
        return PosteriorEstimate(
            mean_bps=float(mu_n),
            std_bps=float(mean_std),
            probability_up=float(probability_up),
            probability_down=float(probability_down),
            threshold_bps=threshold_bps,
            sample_count=int(sample_count),
        )

    def decide(
        self,
        edge: EdgeKey,
        edge_stats: EdgeStatistics,
        diagnostic: TransitionDiagnostic,
        regime: RegimePosterior,
        state: ObservedState,
    ) -> TradeIntent:
        threshold_bps = self.config.transaction_cost_bps + self.config.risk_premium_bps * max(
            state.realized_volatility * 10_000.0,
            0.1,
        )
        posterior = self.estimate_posterior(edge_stats.posterior_samples_bps, threshold_bps)
        observation_confidence = self._observation_confidence(posterior, regime)

        if edge_stats.count < self.transition_config.min_edge_observations:
            return TradeIntent(
                TradeAction.HOLD,
                edge,
                posterior,
                regime.expected_holding_time_ns,
                "insufficient observations",
                observation_confidence=observation_confidence,
            )
        if edge_stats.training_session_count < self.transition_config.min_edge_training_sessions:
            return TradeIntent(
                TradeAction.HOLD,
                edge,
                posterior,
                regime.expected_holding_time_ns,
                "insufficient session support",
                observation_confidence=observation_confidence,
            )
        if edge_stats.directional_consensus < self.transition_config.min_directional_consensus:
            return TradeIntent(
                TradeAction.HOLD,
                edge,
                posterior,
                regime.expected_holding_time_ns,
                "unstable session direction",
                observation_confidence=observation_confidence,
            )
        if edge_stats.cross_session_hit_rate < self.transition_config.min_cross_session_hit_rate:
            return TradeIntent(
                TradeAction.HOLD,
                edge,
                posterior,
                regime.expected_holding_time_ns,
                "weak cross-session hit rate",
                observation_confidence=observation_confidence,
            )
        if edge_stats.cross_session_hit_consensus < self.transition_config.min_cross_session_hit_consensus:
            return TradeIntent(
                TradeAction.HOLD,
                edge,
                posterior,
                regime.expected_holding_time_ns,
                "unstable cross-session hit rate",
                observation_confidence=observation_confidence,
            )
        if diagnostic.alpha_score < self.config.min_alpha_score:
            return TradeIntent(
                TradeAction.HOLD,
                edge,
                posterior,
                regime.expected_holding_time_ns,
                "low alpha concentration",
                observation_confidence=observation_confidence,
            )
        if observation_confidence < self.config.min_observation_confidence:
            return TradeIntent(
                TradeAction.HOLD,
                edge,
                posterior,
                regime.expected_holding_time_ns,
                "observation confidence below threshold",
                observation_confidence=observation_confidence,
            )

        if posterior.probability_up > self.config.entry_probability_threshold and diagnostic.shrunk_drift_bps > 0.0:
            return TradeIntent(
                TradeAction.BUY,
                edge,
                posterior,
                regime.expected_holding_time_ns,
                "posterior drift exceeds costs",
                observation_confidence=observation_confidence,
            )
        if posterior.probability_down > self.config.entry_probability_threshold and diagnostic.shrunk_drift_bps < 0.0:
            return TradeIntent(
                TradeAction.SELL,
                edge,
                posterior,
                regime.expected_holding_time_ns,
                "negative posterior drift exceeds costs",
                observation_confidence=observation_confidence,
            )
        return TradeIntent(
            TradeAction.HOLD,
            edge,
            posterior,
            regime.expected_holding_time_ns,
            "posterior below threshold",
            observation_confidence=observation_confidence,
        )

    def exit_hazard_diagnostics(
        self,
        entry_side: TradeAction,
        state: ObservedState,
        regime: RegimePosterior,
    ) -> ExitHazardEstimate:
        direction = 1.0 if entry_side == TradeAction.BUY else -1.0
        force_decay = min(max(max(0.0, 0.20 - direction * state.trade_pressure), 0.0), 1.0)
        spread_widen = min(max(max(state.spread_norm - 1.0, 0.0) * 0.20, 0.0), 1.0)
        regime_stress = regime.probabilities.get(regime.dominant_regime, 0.0)
        liquidity_shock = 0.0
        if regime.dominant_regime.value == "liquidity_shock":
            liquidity_shock = min(max(0.30 * regime_stress, 0.0), 1.0)

        components = {
            "order_flow_reversal": float(force_decay),
            "spread_deterioration": float(spread_widen),
            "liquidity_shock": float(liquidity_shock),
        }
        survival_probability = 1.0
        for hazard in components.values():
            survival_probability *= 1.0 - min(max(hazard, 0.0), 1.0)
        total_hazard = float(min(max(1.0 - survival_probability, 0.0), 1.0))
        dominant_cause, dominant_hazard = max(components.items(), key=lambda item: item[1])
        reason_map = {
            "order_flow_reversal": "order-flow reversal invalidation",
            "spread_deterioration": "spread deterioration invalidation",
            "liquidity_shock": "liquidity shock invalidation",
        }
        return ExitHazardEstimate(
            total_hazard=total_hazard,
            dominant_hazard=float(dominant_hazard),
            dominant_cause=dominant_cause,
            components=components,
            reason=reason_map.get(dominant_cause, "hazard-based invalidation"),
        )

    def exit_hazard(self, entry_side: TradeAction, state: ObservedState, regime: RegimePosterior) -> float:
        return self.exit_hazard_diagnostics(entry_side, state, regime).total_hazard

    @staticmethod
    def _normal_cdf(mean: float, std: float, threshold: float) -> float:
        if std <= 0:
            return 1.0 if mean <= threshold else 0.0
        z = (threshold - mean) / (std * sqrt(2.0))
        return 0.5 * (1.0 + erf(z))

    def _normal_tail_probability(self, mean: float, std: float, threshold: float) -> float:
        return 1.0 - self._normal_cdf(mean, std, threshold)

    def _observation_confidence(self, posterior: PosteriorEstimate, regime: RegimePosterior) -> float:
        regime_confidence = min(max(regime.confidence, 0.0), 1.0)
        directional_confidence = min(
            max(2.0 * (max(posterior.probability_up, posterior.probability_down) - 0.5), 0.0),
            1.0,
        )
        threshold_bps = max(posterior.threshold_bps, 1e-6)
        if posterior.std_bps == float("inf"):
            dispersion_confidence = 0.0
        else:
            dispersion_confidence = threshold_bps / (threshold_bps + max(posterior.std_bps, 0.0))
        observation_target = max(float(self.transition_config.min_edge_observations), 1.0)
        sample_confidence = 1.0 - np.exp(-float(posterior.sample_count) / observation_target)
        confidence = (
            0.35 * regime_confidence
            + 0.30 * directional_confidence
            + 0.20 * dispersion_confidence
            + 0.15 * sample_confidence
        )
        return float(min(max(confidence, 0.0), 1.0))
