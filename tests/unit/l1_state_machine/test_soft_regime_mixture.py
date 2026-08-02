"""Soft regime mixture over edges (decision-time readout)."""

from __future__ import annotations

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import DecisionEngine, MixtureComponent, TradeAction
from l1_microstructure.events import QuoteEvent
from l1_microstructure.features import FeatureEngine
from l1_microstructure.pipeline import L1MicrostructureStateMachine
from l1_microstructure.regime import MicrostructureRegime, RegimePosterior, SlowContext
from l1_microstructure.transitions import EdgeKey, TransitionKernel


def _quote(ts: int, bid: float = 100.0, ask: float = 100.01) -> QuoteEvent:
    return QuoteEvent(
        symbol="AAPL",
        timestamp_ns=ts,
        bid_price=bid,
        ask_price=ask,
        bid_size=200,
        ask_size=100,
    )


def _regime_posterior(
    probabilities: dict[MicrostructureRegime, float],
) -> RegimePosterior:
    dominant = max(probabilities, key=probabilities.get)
    return RegimePosterior(
        timestamp_ns=1,
        probabilities=probabilities,
        dominant_regime=dominant,
        confidence=probabilities[dominant],
        expected_holding_time_ns=1_000_000_000,
        slow_context=SlowContext(0.0, 0.0, 0.0, 0.0),
    )


def _seed_edge(
    kernel: TransitionKernel,
    edge: EdgeKey,
    *,
    count: int,
    drifts: list[float],
    sessions: list[float] | None = None,
) -> None:
    for _ in range(count):
        kernel.observe_transition(edge, 1_000_000)
    for sample in drifts:
        kernel.attach_drift(edge, sample)
    stats = kernel.get_edge(edge)
    if sessions is not None:
        stats.session_drift_means_bps = list(sessions)
        stats.directional_consensus = 1.0
        stats.cross_session_hit_rate = 1.0
        stats.cross_session_hit_consensus = 1.0


def test_soft_edge_view_mixes_effective_counts_and_drift() -> None:
    kernel = TransitionKernel()
    edge_calm = EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY)
    edge_flow = EdgeKey("a", "b", MicrostructureRegime.EXECUTION_FLOW)
    _seed_edge(kernel, edge_calm, count=100, drifts=[10.0] * 4, sessions=[10.0, 10.0, 10.0, 10.0])
    _seed_edge(kernel, edge_flow, count=100, drifts=[-10.0] * 4, sessions=[-10.0, -10.0, -10.0, -10.0])

    view = kernel.soft_edge_view(
        "a",
        "b",
        {
            MicrostructureRegime.CALM_LIQUIDITY: 0.6,
            MicrostructureRegime.EXECUTION_FLOW: 0.4,
            MicrostructureRegime.LIQUIDITY_SHOCK: 0.0,
            MicrostructureRegime.COMPETITIVE_LIQUIDITY: 0.0,
        },
        primary_regime=MicrostructureRegime.CALM_LIQUIDITY,
        min_weight=0.05,
    )

    assert view.primary_edge == edge_calm
    assert abs(view.effective_count - 100.0) < 1e-9
    # Soft mixture equals weighted component diagnostics (including adversarial age).
    expected_shrunk = (
        0.6 * kernel.diagnostic(edge_calm).shrunk_drift_bps
        + 0.4 * kernel.diagnostic(edge_flow).shrunk_drift_bps
    )
    assert abs(view.shrunk_drift_bps - expected_shrunk) < 1e-9
    assert abs(view.regime_weights[MicrostructureRegime.CALM_LIQUIDITY] - 0.6) < 1e-9
    assert abs(view.regime_weights[MicrostructureRegime.EXECUTION_FLOW] - 0.4) < 1e-9
    assert MicrostructureRegime.LIQUIDITY_SHOCK not in view.regime_weights


def test_soft_edge_view_drops_tiny_mass_and_renormalizes() -> None:
    kernel = TransitionKernel()
    edge = EdgeKey("x", "y", MicrostructureRegime.CALM_LIQUIDITY)
    _seed_edge(kernel, edge, count=10, drifts=[1.0])

    view = kernel.soft_edge_view(
        "x",
        "y",
        {
            MicrostructureRegime.CALM_LIQUIDITY: 0.90,
            MicrostructureRegime.EXECUTION_FLOW: 0.04,
            MicrostructureRegime.LIQUIDITY_SHOCK: 0.03,
            MicrostructureRegime.COMPETITIVE_LIQUIDITY: 0.03,
        },
        min_weight=0.05,
    )

    assert list(view.regime_weights) == [MicrostructureRegime.CALM_LIQUIDITY]
    assert abs(view.regime_weights[MicrostructureRegime.CALM_LIQUIDITY] - 1.0) < 1e-9


def test_mixture_posterior_is_weight_average_of_component_means() -> None:
    config = FrameworkConfig()
    engine = DecisionEngine(config.decision, config.transition)
    samples_hi = [8.0, 8.0, 8.0, 8.0]
    samples_lo = [0.0, 0.0, 0.0, 0.0]
    posterior = engine.estimate_mixture_posterior(
        [
            MixtureComponent(0.75, samples_hi),
            MixtureComponent(0.25, samples_lo),
        ],
        threshold_bps=1.0,
    )
    # Mixture of NI-Gamma posteriors (prior pulls sample means toward 0).
    expected = (
        0.75 * engine.estimate_posterior(samples_hi, 1.0).mean_bps
        + 0.25 * engine.estimate_posterior(samples_lo, 1.0).mean_bps
    )
    assert abs(posterior.mean_bps - expected) < 1e-9
    assert posterior.sample_count == 4


def test_soft_decision_mixes_opposing_regime_edges() -> None:
    config = FrameworkConfig()
    config.transition.min_edge_observations = 10
    config.transition.min_edge_training_sessions = 2
    config.transition.min_directional_consensus = 0.0
    config.transition.min_cross_session_hit_rate = 0.0
    config.transition.min_cross_session_hit_consensus = 0.0
    config.decision.min_alpha_score = 0.0
    config.decision.min_observation_confidence = 0.0
    config.decision.transaction_cost_bps = 0.0
    config.decision.risk_premium_bps = 0.0
    config.decision.entry_probability_threshold = 0.55
    config.decision.soft_regime_mixture = True

    kernel = TransitionKernel(config.transition)
    edge_calm = EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY)
    edge_flow = EdgeKey("a", "b", MicrostructureRegime.EXECUTION_FLOW)
    # Only flow has strong positive history; calm is empty / weak.
    _seed_edge(
        kernel,
        edge_flow,
        count=40,
        drifts=[6.0, 6.5, 5.5, 6.0],
        sessions=[6.0, 6.0, 6.0, 6.0],
    )
    _seed_edge(
        kernel,
        edge_calm,
        count=40,
        drifts=[0.1, -0.1, 0.0, 0.05],
        sessions=[0.0, 0.0, 0.0, 0.0],
    )

    state = FeatureEngine().update(_quote(1_000_000_000))
    assert state is not None
    # Dominant is calm, but soft mass on flow should pull the mixture bullish.
    regime = _regime_posterior(
        {
            MicrostructureRegime.CALM_LIQUIDITY: 0.55,
            MicrostructureRegime.EXECUTION_FLOW: 0.45,
            MicrostructureRegime.LIQUIDITY_SHOCK: 0.0,
            MicrostructureRegime.COMPETITIVE_LIQUIDITY: 0.0,
        }
    )
    soft_view = kernel.soft_edge_view(
        "a",
        "b",
        regime.probabilities,
        primary_regime=regime.dominant_regime,
        min_weight=config.decision.soft_regime_min_weight,
    )
    engine = DecisionEngine(config.decision, config.transition)

    hard_intent = engine.decide(
        edge_calm,
        kernel.get_edge(edge_calm),
        kernel.diagnostic(edge_calm),
        regime,
        state,
    )
    soft_intent = engine.decide(
        edge_calm,
        kernel.get_edge(edge_calm),
        soft_view.diagnostic,
        regime,
        state,
        soft_view=soft_view,
    )

    # Hard MAP edge (calm) has near-zero drift → HOLD; soft mixture leans BUY.
    assert hard_intent.action is TradeAction.HOLD
    assert soft_intent.action is TradeAction.BUY
    assert "soft-regime" in soft_intent.reason
    assert soft_intent.edge == edge_calm  # primary identity remains MAP


def test_soft_mixture_is_opt_in_by_default() -> None:
    config = FrameworkConfig()
    assert config.decision.soft_regime_mixture is False
    machine = L1MicrostructureStateMachine(config)
    first = machine.on_event(_quote(1_000_000_000, 100.0, 100.02))
    second = machine.on_event(_quote(2_000_000_000, 100.05, 100.08))
    assert first is not None
    assert second is not None


def test_soft_decision_fails_closed_on_unsupported_regime_mass() -> None:
    """Mixture mass on empty edges must not trade."""
    config = FrameworkConfig()
    config.transition.min_edge_observations = 10
    config.transition.min_edge_training_sessions = 0
    config.transition.min_directional_consensus = 0.0
    config.transition.min_cross_session_hit_rate = 0.0
    config.transition.min_cross_session_hit_consensus = 0.0
    config.decision.min_alpha_score = 0.0
    config.decision.min_observation_confidence = 0.0
    config.decision.soft_regime_min_supported_weight = 0.50
    config.decision.soft_regime_min_weight = 0.05

    kernel = TransitionKernel(config.transition)
    # Only flow has data; calm (dominant mass) is empty.
    edge_flow = EdgeKey("a", "b", MicrostructureRegime.EXECUTION_FLOW)
    _seed_edge(
        kernel,
        edge_flow,
        count=40,
        drifts=[6.0, 6.0, 6.0, 6.0],
        sessions=[6.0, 6.0, 6.0, 6.0],
    )

    state = FeatureEngine().update(_quote(1_000_000_000))
    assert state is not None
    regime = _regime_posterior(
        {
            MicrostructureRegime.CALM_LIQUIDITY: 0.60,
            MicrostructureRegime.EXECUTION_FLOW: 0.40,
            MicrostructureRegime.LIQUIDITY_SHOCK: 0.0,
            MicrostructureRegime.COMPETITIVE_LIQUIDITY: 0.0,
        }
    )
    soft_view = kernel.soft_edge_view(
        "a",
        "b",
        regime.probabilities,
        primary_regime=regime.dominant_regime,
        min_weight=config.decision.soft_regime_min_weight,
    )
    assert soft_view.supported_weight == 0.40  # only flow has observations
    assert soft_view.supported_weight < config.decision.soft_regime_min_supported_weight

    engine = DecisionEngine(config.decision, config.transition)
    intent = engine.decide(
        EdgeKey("a", "b", regime.dominant_regime),
        kernel.get_edge(EdgeKey("a", "b", regime.dominant_regime)),
        soft_view.diagnostic,
        regime,
        state,
        soft_view=soft_view,
    )
    assert intent.action is TradeAction.HOLD
    assert intent.reason == "insufficient supported regime mass"
