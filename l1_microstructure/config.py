"""Configuration for the L1 microstructure state machine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class FeatureConfig:
    quote_persistence_updates: int = 5
    trade_window_seconds: float = 10.0
    micro_vol_window_seconds: float = 600.0
    slow_context_window_seconds: float = 1800.0
    minimum_sigma: float = 1e-4
    flicker_mean_reversion: float = 3.0
    flicker_baseline_intensity: float = 4.0
    flicker_jump: float = 1.0
    quantile_history: int = 256


@dataclass(slots=True)
class RegimeConfig:
    calm_holding_time_seconds: float = 12.0
    execution_flow_holding_time_seconds: float = 6.0
    liquidity_shock_holding_time_seconds: float = 2.0
    competitive_liquidity_holding_time_seconds: float = 4.0
    posterior_floor: float = 1e-6


@dataclass(slots=True)
class TransitionConfig:
    mahalanobis_threshold: float = 2.75
    covariance_history: int = 512
    dirichlet_alpha: float = 0.25
    drift_horizon_ms: int = 3000
    drift_horizons_ms: tuple[int, ...] = (3000, 15000, 60000)
    min_edge_observations: int = 200
    min_edge_training_sessions: int = 4
    min_directional_consensus: float = 0.60
    min_cross_session_hit_rate: float = 0.50
    min_cross_session_hit_consensus: float = 0.60
    min_sharpe_stability: float = 0.35
    adversarial_decay_gamma: float = 0.0025

    @property
    def drift_horizon_ns(self) -> int:
        return self.drift_horizon_ns_values[0]

    @property
    def drift_horizon_ns_values(self) -> tuple[int, ...]:
        candidates = (*self.drift_horizons_ms, self.drift_horizon_ms)
        normalized = tuple(sorted({int(value) for value in candidates if int(value) > 0}))
        if normalized:
            return tuple(int(value * 1_000_000) for value in normalized)
        fallback = max(int(self.drift_horizon_ms), 1)
        return (int(fallback * 1_000_000),)


@dataclass(slots=True)
class DecisionConfig:
    entry_probability_threshold: float = 0.62
    exit_hazard_threshold: float = 0.55
    risk_premium_bps: float = 1.5
    transaction_cost_bps: float = 1.2
    min_alpha_score: float = 0.15
    min_observation_confidence: float = 0.10
    posterior_prior_mean_bps: float = 0.0
    posterior_prior_strength: float = 1.0
    posterior_prior_alpha: float = 3.0
    posterior_prior_beta: float = 4.0


@dataclass(slots=True)
class ExecutionConfig:
    latency_ms: int = 100
    alignment_probability_threshold: float = 0.65
    base_fill_probability: float = 0.7
    adverse_selection_penalty: float = 0.4
    base_slippage_bps: float = 1.0
    max_slippage_bps: float = 12.0
    queue_penalty_weight: float = 0.0
    queue_reference_size: float = 100.0
    queue_penalty_exponent: float = 1.0
    queue_pressure_weight: float = 0.20
    queue_latency_weight: float = 0.10
    queue_survival_floor: float = 0.05
    confidence_aggressiveness_floor: float = 0.35

    @property
    def latency_ns(self) -> int:
        return int(self.latency_ms * 1_000_000)


@dataclass(slots=True)
class RiskConfig:
    starting_equity: float = 1_000_000.0
    daily_drawdown_limit: float = 0.03
    max_gross_exposure: float = 1.5
    volatility_target: float = 0.012
    max_position_fraction: float = 0.05
    beta_hedge_threshold: float = 0.30
    confidence_size_floor: float = 0.25


@dataclass(slots=True)
class PortfolioConfig:
    covariance_shrinkage: float = 0.20
    ridge: float = 1e-5
    max_weight: float = 0.10
    sector_cap: float = 0.25


@dataclass(slots=True)
class FrameworkConfig:
    feature: FeatureConfig = field(default_factory=FeatureConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    transition: TransitionConfig = field(default_factory=TransitionConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
