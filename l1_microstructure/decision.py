"""Bayesian decision logic for microstructure transition edges."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import erf, exp, isfinite, sqrt

from .calibration.interfaces import SwitchingDiffusionPrior
from .config import DecisionConfig, TransitionConfig
from .features import ObservedState
from .regime import MicrostructureRegime, RegimePosterior
from .transitions import EdgeKey, EdgeStatistics, SoftEdgeView, TransitionDiagnostic


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


@dataclass(frozen=True, slots=True)
class MixtureComponent:
    """One regime-weighted sample bag for mixture posteriors."""

    weight: float
    samples: list[float]
    regime: MicrostructureRegime | None = None


class DecisionEngine:
    def __init__(
        self,
        decision_config: DecisionConfig | None = None,
        transition_config: TransitionConfig | None = None,
        diffusion_prior: SwitchingDiffusionPrior | None = None,
    ):
        self.config = decision_config or DecisionConfig()
        self.transition_config = transition_config or TransitionConfig()
        self.diffusion_prior = diffusion_prior

    def estimate_posterior(
        self,
        samples: list[float],
        threshold_bps: float,
        *,
        regime: MicrostructureRegime | str | None = None,
        horizon_ns: int | None = None,
    ) -> PosteriorEstimate:
        if not samples:
            mu0, _, _, _ = self._prior_hyperparameters(regime, horizon_ns)
            return PosteriorEstimate(float(mu0), float("inf"), 0.5, 0.5, threshold_bps, 0)

        sample_count = len(samples)
        sample_mean = sum(samples) / sample_count
        sample_ss = 0.0
        for value in samples:
            delta = value - sample_mean
            sample_ss += delta * delta

        mu0, kappa0, alpha0, beta0 = self._prior_hyperparameters(regime, horizon_ns)
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

    def estimate_mixture_posterior(
        self,
        components: list[MixtureComponent],
        threshold_bps: float,
        *,
        horizon_ns: int | None = None,
    ) -> PosteriorEstimate:
        """Mixture of regime-conditioned NI-Gamma posteriors."""
        active: list[tuple[float, PosteriorEstimate]] = []
        for component in components:
            if component.weight <= 0.0 or not component.samples:
                continue
            active.append(
                (
                    float(component.weight),
                    self.estimate_posterior(
                        component.samples,
                        threshold_bps,
                        regime=component.regime,
                        horizon_ns=horizon_ns,
                    ),
                )
            )
        if not active:
            return self.estimate_posterior([], threshold_bps, horizon_ns=horizon_ns)

        weight_total = sum(weight for weight, _ in active)
        if weight_total <= 0.0:
            return self.estimate_posterior([], threshold_bps, horizon_ns=horizon_ns)

        mean_bps = 0.0
        second_moment = 0.0
        probability_up = 0.0
        probability_down = 0.0
        sample_count = 0.0
        for weight, posterior in active:
            w = weight / weight_total
            mean_bps += w * posterior.mean_bps
            variance = max(posterior.std_bps, 0.0) ** 2
            second_moment += w * (variance + posterior.mean_bps**2)
            probability_up += w * posterior.probability_up
            probability_down += w * posterior.probability_down
            sample_count += w * float(posterior.sample_count)

        mixture_variance = max(second_moment - mean_bps**2, 0.0)
        return PosteriorEstimate(
            mean_bps=float(mean_bps),
            std_bps=float(sqrt(mixture_variance)),
            probability_up=float(probability_up),
            probability_down=float(probability_down),
            threshold_bps=threshold_bps,
            sample_count=int(round(sample_count)),
        )

    def decide(
        self,
        edge: EdgeKey,
        edge_stats: EdgeStatistics,
        diagnostic: TransitionDiagnostic,
        regime: RegimePosterior,
        state: ObservedState,
        *,
        execution_cost_bps: float | None = None,
        soft_view: SoftEdgeView | None = None,
    ) -> TradeIntent:
        """
        Single decision path. Hard MAP edges are expressed as a one-component
        SoftEdgeView so gates and posterior construction stay identical.
        """
        view = soft_view or SoftEdgeView.from_hard(edge, edge_stats, diagnostic)
        return self._decide_from_view(
            view,
            regime,
            state,
            execution_cost_bps=execution_cost_bps,
            soft_mixture=soft_view is not None,
        )

    def _decide_from_view(
        self,
        view: SoftEdgeView,
        regime: RegimePosterior,
        state: ObservedState,
        *,
        execution_cost_bps: float | None,
        soft_mixture: bool,
    ) -> TradeIntent:
        if execution_cost_bps is not None and (
            not isfinite(execution_cost_bps) or execution_cost_bps < 0.0
        ):
            raise ValueError("execution cost must be finite and non-negative")
        transaction_cost_bps = (
            self.config.transaction_cost_bps
            if execution_cost_bps is None
            else float(execution_cost_bps)
        )
        threshold_bps = (
            transaction_cost_bps
            + self.config.risk_premium_bps
            * max(state.realized_volatility * 10_000.0, 0.1)
        )
        horizon_ns = self.transition_config.drift_horizon_ns
        if soft_mixture and len(view.components) > 1:
            posterior = self.estimate_mixture_posterior(
                [
                    MixtureComponent(
                        weight=component.weight,
                        samples=component.stats.posterior_samples_bps,
                        regime=component.regime,
                    )
                    for component in view.components
                ],
                threshold_bps,
                horizon_ns=horizon_ns,
            )
        else:
            component = view.components[0]
            posterior = self.estimate_posterior(
                component.stats.posterior_samples_bps,
                threshold_bps,
                regime=component.regime,
                horizon_ns=horizon_ns,
            )

        observation_confidence = self._observation_confidence(posterior, regime)
        edge = view.primary_edge
        holding_time_ns = regime.expected_holding_time_ns
        reason_prefix = "soft-regime " if soft_mixture and len(view.components) > 1 else ""

        if soft_mixture and view.supported_weight < self.config.soft_regime_min_supported_weight:
            return self._hold(
                edge,
                posterior,
                holding_time_ns,
                "insufficient supported regime mass",
                observation_confidence,
            )
        if view.effective_count < self.transition_config.min_edge_observations:
            return self._hold(
                edge, posterior, holding_time_ns, "insufficient observations", observation_confidence
            )
        if view.effective_training_sessions < self.transition_config.min_edge_training_sessions:
            return self._hold(
                edge, posterior, holding_time_ns, "insufficient session support", observation_confidence
            )
        if view.directional_consensus < self.transition_config.min_directional_consensus:
            return self._hold(
                edge, posterior, holding_time_ns, "unstable session direction", observation_confidence
            )
        if view.cross_session_hit_rate < self.transition_config.min_cross_session_hit_rate:
            return self._hold(
                edge, posterior, holding_time_ns, "weak cross-session hit rate", observation_confidence
            )
        if view.cross_session_hit_consensus < self.transition_config.min_cross_session_hit_consensus:
            return self._hold(
                edge,
                posterior,
                holding_time_ns,
                "unstable cross-session hit rate",
                observation_confidence,
            )
        if view.alpha_score < self.config.min_alpha_score:
            return self._hold(
                edge, posterior, holding_time_ns, "low alpha concentration", observation_confidence
            )
        if observation_confidence < self.config.min_observation_confidence:
            return self._hold(
                edge,
                posterior,
                holding_time_ns,
                "observation confidence below threshold",
                observation_confidence,
            )

        if (
            posterior.probability_up > self.config.entry_probability_threshold
            and view.shrunk_drift_bps > 0.0
        ):
            return TradeIntent(
                TradeAction.BUY,
                edge,
                posterior,
                holding_time_ns,
                f"{reason_prefix}posterior drift exceeds costs".strip(),
                observation_confidence=observation_confidence,
            )
        if (
            posterior.probability_down > self.config.entry_probability_threshold
            and view.shrunk_drift_bps < 0.0
        ):
            return TradeIntent(
                TradeAction.SELL,
                edge,
                posterior,
                holding_time_ns,
                f"{reason_prefix}negative posterior drift exceeds costs".strip(),
                observation_confidence=observation_confidence,
            )
        return self._hold(
            edge, posterior, holding_time_ns, "posterior below threshold", observation_confidence
        )

    @staticmethod
    def _hold(
        edge: EdgeKey,
        posterior: PosteriorEstimate,
        holding_time_ns: int,
        reason: str,
        observation_confidence: float,
    ) -> TradeIntent:
        return TradeIntent(
            TradeAction.HOLD,
            edge,
            posterior,
            holding_time_ns,
            reason,
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
        sample_confidence = 1.0 - exp(-float(posterior.sample_count) / observation_target)
        confidence = (
            0.35 * regime_confidence
            + 0.30 * directional_confidence
            + 0.20 * dispersion_confidence
            + 0.15 * sample_confidence
        )
        return float(min(max(confidence, 0.0), 1.0))

    def _prior_hyperparameters(
        self,
        regime: MicrostructureRegime | str | None,
        horizon_ns: int | None,
    ) -> tuple[float, float, float, float]:
        """Return (mu0, kappa0, alpha0, beta0) for the NI-Gamma edge posterior."""
        alpha0 = self.config.posterior_prior_alpha
        if self.diffusion_prior is None or not self.config.use_switching_diffusion_prior:
            return (
                self.config.posterior_prior_mean_bps,
                self.config.posterior_prior_strength,
                alpha0,
                self.config.posterior_prior_beta,
            )

        regime_key = self._regime_key(regime)
        resolved_horizon = (
            int(horizon_ns)
            if horizon_ns is not None
            else int(self.diffusion_prior.reference_horizon_ns)
        )
        mu0 = self.diffusion_prior.mean_bps(regime_key, resolved_horizon)
        variance = self.diffusion_prior.variance_bps2(regime_key, resolved_horizon)
        # Strength is frozen onto the fitted prior at calibration time.
        kappa0 = max(float(self.diffusion_prior.prior_strength), 1e-6)
        if alpha0 > 1.0:
            beta0 = max(variance * (alpha0 - 1.0), 1e-9)
        else:
            beta0 = max(variance, 1e-9)
        return float(mu0), float(kappa0), float(alpha0), float(beta0)

    @staticmethod
    def _regime_key(regime: MicrostructureRegime | str | None) -> str:
        if regime is None:
            return ""
        if isinstance(regime, MicrostructureRegime):
            return regime.value
        return str(regime)
