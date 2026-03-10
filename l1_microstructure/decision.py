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
        posterior = self.estimate_posterior(edge_stats.drift_samples_bps, threshold_bps)

        if edge_stats.count < self.transition_config.min_edge_observations:
            return TradeIntent(TradeAction.HOLD, edge, posterior, regime.expected_holding_time_ns, "insufficient observations")
        if diagnostic.alpha_score < self.config.min_alpha_score:
            return TradeIntent(TradeAction.HOLD, edge, posterior, regime.expected_holding_time_ns, "low alpha concentration")

        if posterior.probability_up > self.config.entry_probability_threshold and diagnostic.shrunk_drift_bps > 0.0:
            return TradeIntent(TradeAction.BUY, edge, posterior, regime.expected_holding_time_ns, "posterior drift exceeds costs")
        if posterior.probability_down > self.config.entry_probability_threshold and diagnostic.shrunk_drift_bps < 0.0:
            return TradeIntent(TradeAction.SELL, edge, posterior, regime.expected_holding_time_ns, "negative posterior drift exceeds costs")
        return TradeIntent(TradeAction.HOLD, edge, posterior, regime.expected_holding_time_ns, "posterior below threshold")

    def exit_hazard(self, entry_side: TradeAction, state: ObservedState, regime: RegimePosterior) -> float:
        direction = 1.0 if entry_side is TradeAction.BUY else -1.0
        force_decay = max(0.0, 0.20 - direction * state.trade_pressure)
        spread_widen = max(state.spread_norm - 1.0, 0.0) * 0.20
        regime_stress = regime.probabilities.get(regime.dominant_regime, 0.0)
        hazard = force_decay + spread_widen
        if regime.dominant_regime.value == "liquidity_shock":
            hazard += 0.30 * regime_stress
        return float(min(max(hazard, 0.0), 1.0))

    @staticmethod
    def _normal_cdf(mean: float, std: float, threshold: float) -> float:
        if std <= 0:
            return 1.0 if mean <= threshold else 0.0
        z = (threshold - mean) / (std * sqrt(2.0))
        return 0.5 * (1.0 + erf(z))

    def _normal_tail_probability(self, mean: float, std: float, threshold: float) -> float:
        return 1.0 - self._normal_cdf(mean, std, threshold)