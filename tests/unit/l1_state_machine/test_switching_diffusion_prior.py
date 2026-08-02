"""Switching-diffusion prior for post-edge mid drift (step 4)."""

from __future__ import annotations

from dataclasses import asdict, replace

import pandas as pd

from l1_microstructure.artifacts import ArtifactBundleLoader, ArtifactMetadata, LocalArtifactStore
from l1_microstructure.calibration import SwitchingDiffusionPriorCalibrator
from l1_microstructure.calibration.interfaces import (
    RegimeCalibrationArtifact,
    SwitchingDiffusionPrior,
)
from l1_microstructure.config import DecisionConfig, FrameworkConfig, TransitionConfig
from l1_microstructure.decision import DecisionEngine, MixtureComponent, TradeAction
from l1_microstructure.events import QuoteEvent
from l1_microstructure.features import FeatureEngine
from l1_microstructure.pipeline import L1MicrostructureStateMachine
from l1_microstructure.artifacts.runtime import RuntimeArtifactBundle
from l1_microstructure.regime import MicrostructureRegime, RegimePosterior, SlowContext
from l1_microstructure.transitions import EdgeKey, TransitionKernel


def _transition_panel() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    # Calm: near-zero drift
    for index in range(30):
        rows.append(
            {
                "regime": "calm_liquidity",
                "realized_drift_bps": 0.2 * ((index % 3) - 1),
                "horizon_ns": 3_000_000_000,
            }
        )
    # Execution flow: strong positive drift
    for index in range(30):
        rows.append(
            {
                "regime": "execution_flow",
                "realized_drift_bps": 6.0 + 0.3 * ((index % 3) - 1),
                "horizon_ns": 3_000_000_000,
            }
        )
    # Liquidity shock: negative drift
    for index in range(30):
        rows.append(
            {
                "regime": "liquidity_shock",
                "realized_drift_bps": -4.0 + 0.2 * ((index % 3) - 1),
                "horizon_ns": 3_000_000_000,
            }
        )
    # Competitive: mild positive
    for index in range(20):
        rows.append(
            {
                "regime": "competitive_liquidity",
                "realized_drift_bps": 1.0 + 0.1 * ((index % 2) - 0.5),
                "horizon_ns": 3_000_000_000,
            }
        )
    return pd.DataFrame(rows)


def test_switching_diffusion_calibrator_separates_regime_rates() -> None:
    prior = SwitchingDiffusionPriorCalibrator(
        reference_horizon_ns=3_000_000_000,
        min_regime_samples=8,
    ).fit(_transition_panel())

    assert prior.reference_horizon_ns == 3_000_000_000
    flow_mean = prior.mean_bps("execution_flow", 3_000_000_000)
    shock_mean = prior.mean_bps("liquidity_shock", 3_000_000_000)
    calm_mean = prior.mean_bps("calm_liquidity", 3_000_000_000)
    assert flow_mean > calm_mean
    assert shock_mean < calm_mean
    # Mean scales with horizon for Brownian-with-drift prior
    assert abs(prior.mean_bps("execution_flow", 6_000_000_000) - 2.0 * flow_mean) < 1e-9
    assert prior.variance_bps2("execution_flow", 6_000_000_000) > prior.variance_bps2(
        "execution_flow", 3_000_000_000
    )


def test_posterior_uses_diffusion_prior_mean_for_sparse_samples() -> None:
    prior = SwitchingDiffusionPriorCalibrator(reference_horizon_ns=3_000_000_000).fit(
        _transition_panel()
    )
    config = DecisionConfig(
        use_switching_diffusion_prior=True,
        posterior_prior_mean_bps=0.0,
        posterior_prior_strength=1.0,
        diffusion_prior_strength=8.0,
    )
    engine = DecisionEngine(config, TransitionConfig(), diffusion_prior=prior)
    # Sparse edge samples around zero under a strongly positive flow prior
    samples = [0.1, -0.1, 0.0, 0.05]
    with_prior = engine.estimate_posterior(
        samples,
        threshold_bps=1.0,
        regime=MicrostructureRegime.EXECUTION_FLOW,
        horizon_ns=3_000_000_000,
    )
    engine_off = DecisionEngine(
        replace(config, use_switching_diffusion_prior=False),
        TransitionConfig(),
        diffusion_prior=prior,
    )
    without = engine_off.estimate_posterior(
        samples,
        threshold_bps=1.0,
        regime=MicrostructureRegime.EXECUTION_FLOW,
        horizon_ns=3_000_000_000,
    )
    assert with_prior.mean_bps > without.mean_bps


def test_mixture_posterior_uses_per_regime_priors() -> None:
    prior = SwitchingDiffusionPriorCalibrator(reference_horizon_ns=3_000_000_000).fit(
        _transition_panel()
    )
    engine = DecisionEngine(
        DecisionConfig(use_switching_diffusion_prior=True, diffusion_prior_strength=6.0),
        TransitionConfig(),
        diffusion_prior=prior,
    )
    # Equal weights; flow samples slightly positive, shock slightly negative
    mixture = engine.estimate_mixture_posterior(
        [
            MixtureComponent(0.5, [0.5, 0.4, 0.6], MicrostructureRegime.EXECUTION_FLOW),
            MixtureComponent(0.5, [-0.5, -0.4, -0.6], MicrostructureRegime.LIQUIDITY_SHOCK),
        ],
        threshold_bps=0.5,
        horizon_ns=3_000_000_000,
    )
    # Flow prior pulls up, shock prior pulls down → mixture near zero-ish but defined
    assert abs(mixture.mean_bps) < 5.0
    assert mixture.sample_count == 3


def test_diffusion_prior_round_trips_on_regime_artifact(tmp_path) -> None:
    prior = SwitchingDiffusionPriorCalibrator(reference_horizon_ns=3_000_000_000).fit(
        _transition_panel()
    )
    artifact = RegimeCalibrationArtifact(
        symbol="AAPL",
        regime_priors={regime.value: 0.25 for regime in MicrostructureRegime},
        holding_time_seconds={
            "calm_liquidity": 12.0,
            "execution_flow": 6.0,
            "liquidity_shock": 2.0,
            "competitive_liquidity": 4.0,
        },
        diffusion_prior=prior,
    )
    store = LocalArtifactStore(tmp_path)
    store.save(
        ArtifactMetadata("regime-diff-1", "regime_calibration", "v1", "2026-03-09T00:00:00+00:00"),
        asdict(artifact),
    )
    loaded = ArtifactBundleLoader(store).load_runtime_bundle(regime_calibration_id="regime-diff-1")
    assert loaded.regime_calibration is not None
    assert loaded.regime_calibration.diffusion_prior is not None
    assert (
        loaded.regime_calibration.diffusion_prior.drift_rate_bps_per_sec["execution_flow"]
        == prior.drift_rate_bps_per_sec["execution_flow"]
    )


def test_pipeline_decision_engine_receives_diffusion_prior() -> None:
    prior = SwitchingDiffusionPriorCalibrator(reference_horizon_ns=3_000_000_000).fit(
        _transition_panel()
    )
    artifact = RegimeCalibrationArtifact(
        symbol="AAPL",
        regime_priors={regime.value: 0.25 for regime in MicrostructureRegime},
        holding_time_seconds={regime.value: 5.0 for regime in MicrostructureRegime},
        diffusion_prior=prior,
    )
    machine = L1MicrostructureStateMachine(
        FrameworkConfig(),
        runtime_artifacts=RuntimeArtifactBundle(regime_calibration=artifact),
    )
    assert machine.decision_engine.diffusion_prior is not None
    update = machine.on_event(
        QuoteEvent(
            symbol="AAPL",
            timestamp_ns=1_000_000_000,
            bid_price=100.0,
            ask_price=100.02,
            bid_size=100,
            ask_size=100,
        )
    )
    assert update is not None


def test_hard_decide_with_diffusion_prior_still_trades() -> None:
    prior = SwitchingDiffusionPrior(
        reference_horizon_ns=3_000_000_000,
        drift_rate_bps_per_sec={
            "calm_liquidity": 0.0,
            "execution_flow": 2.0,
            "liquidity_shock": -1.0,
            "competitive_liquidity": 0.2,
        },
        volatility_bps_per_sqrt_sec={
            "calm_liquidity": 1.0,
            "execution_flow": 1.5,
            "liquidity_shock": 2.0,
            "competitive_liquidity": 1.2,
        },
        prior_strength=2.0,
    )
    config = FrameworkConfig()
    config.transition.min_edge_observations = 3
    config.transition.min_edge_training_sessions = 0
    config.transition.min_directional_consensus = 0.0
    config.transition.min_cross_session_hit_rate = 0.0
    config.transition.min_cross_session_hit_consensus = 0.0
    config.decision.min_alpha_score = 0.0
    config.decision.min_observation_confidence = 0.0
    config.decision.transaction_cost_bps = 0.0
    config.decision.risk_premium_bps = 0.0
    config.decision.entry_probability_threshold = 0.55
    config.decision.use_switching_diffusion_prior = True

    engine = DecisionEngine(config.decision, config.transition, diffusion_prior=prior)
    kernel = TransitionKernel(config.transition)
    edge = EdgeKey("a", "b", MicrostructureRegime.EXECUTION_FLOW)
    for _ in range(4):
        kernel.observe_transition(edge, 1_000_000)
    for sample in (5.0, 6.0, 5.5, 6.5):
        kernel.attach_drift(edge, sample)

    state = FeatureEngine().update(
        QuoteEvent(symbol="AAPL", timestamp_ns=1_000_000_000, bid_price=100.0, ask_price=100.01, bid_size=200, ask_size=100)
    )
    assert state is not None
    regime = RegimePosterior(
        timestamp_ns=1,
        probabilities={regime: 0.25 for regime in MicrostructureRegime},
        dominant_regime=MicrostructureRegime.EXECUTION_FLOW,
        confidence=0.25,
        expected_holding_time_ns=1_000_000_000,
        slow_context=SlowContext(0.0, 0.0, 0.0, 0.0),
    )
    intent = engine.decide(edge, kernel.get_edge(edge), kernel.diagnostic(edge), regime, state)
    assert intent.action is TradeAction.BUY
