from __future__ import annotations

from collections import deque
from dataclasses import replace

import numpy as np

from l1_microstructure.artifacts.runtime import RuntimeArtifactBundle
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import DecisionEngine, PosteriorEstimate, TradeAction, TradeIntent
from l1_microstructure.events import QuoteEvent, TradeEvent, TradeSide
from l1_microstructure.execution import ExecutionSimulator
from l1_microstructure.features import FeatureEngine, FlickerState, PressureState, SpreadState, VolatilityState
from l1_microstructure.pipeline import L1MicrostructureStateMachine
from l1_microstructure.regime import MicrostructureRegime, RegimeInferencer
from l1_microstructure.risk import OpenPosition
from l1_microstructure.transitions import EdgeKey, TransitionKernel


def _quote(ts: int, bid: float, ask: float, bid_size: int = 100, ask_size: int = 100) -> QuoteEvent:
    return QuoteEvent(
        symbol="AAPL",
        timestamp_ns=ts,
        bid_price=bid,
        ask_price=ask,
        bid_size=bid_size,
        ask_size=ask_size,
    )


def _trade(ts: int, price: float, size: int, side: TradeSide) -> TradeEvent:
    return TradeEvent(symbol="AAPL", timestamp_ns=ts, price=price, size=size, side=side)


def test_feature_engine_projects_observable_state() -> None:
    engine = FeatureEngine()
    state = engine.update(_quote(1_000_000_000, 100.00, 100.02, 200, 100))

    assert state is not None
    assert state.book.microprice > state.book.midpoint
    assert state.label.count("|") == 4


def test_transition_kernel_regularizes_probabilities() -> None:
    kernel = TransitionKernel()
    edge = EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY)
    kernel.observe_transition(edge, 1_000)
    kernel.attach_drift(edge, 2.5)
    diagnostic = kernel.diagnostic(edge)

    assert diagnostic.transition_probability > 0.0
    assert diagnostic.observation_count == 1
    assert diagnostic.alpha_score >= 0.0


def test_regime_inferencer_filters_marginal_one_step_flips() -> None:
    from l1_microstructure.calibration.interfaces import RegimeCalibrationArtifact

    observed_state = FeatureEngine().update(_quote(1_000_000_000, 100.00, 100.01, 200, 200))

    assert observed_state is not None

    base_state = replace(
        observed_state,
        spread_norm=0.75,
        quote_pressure=0.0,
        trade_pressure=0.0,
        flicker_intensity=max(observed_state.flicker_intensity * 0.8, 1e-6),
        realized_volatility=observed_state.realized_volatility,
        spread_state=SpreadState.TIGHT,
        quote_state=PressureState.NEUTRAL,
        trade_state=PressureState.NEUTRAL,
        flicker_state=FlickerState.STABLE,
        volatility_state=VolatilityState.QUIET,
    )

    inferencer = RegimeInferencer(
        regime_calibration=RegimeCalibrationArtifact(
            symbol="AAPL",
            regime_priors={
                "calm_liquidity": 0.94,
                "execution_flow": 0.03,
                "liquidity_shock": 0.02,
                "competitive_liquidity": 0.01,
            },
            holding_time_seconds={
                "calm_liquidity": 30.0,
                "execution_flow": 2.0,
                "liquidity_shock": 1.0,
                "competitive_liquidity": 2.0,
            },
            metadata={},
        )
    )
    first_posterior = inferencer.update(base_state)

    mixed_state = replace(
        base_state,
        timestamp_ns=base_state.timestamp_ns + 1_000_000_000,
        spread_norm=1.05,
        quote_pressure=0.65,
        trade_pressure=0.70,
        flicker_intensity=base_state.flicker_intensity * 1.1,
        spread_state=SpreadState.NORMAL,
        quote_state=PressureState.BUY_HEAVY,
        trade_state=PressureState.BUY_HEAVY,
        flicker_state=FlickerState.COMPETITIVE,
        volatility_state=VolatilityState.QUIET,
    )

    slow_context = inferencer._slow_context()
    emission = inferencer._emission_probabilities(
        {
            MicrostructureRegime.CALM_LIQUIDITY: inferencer._calm_score(mixed_state, slow_context),
            MicrostructureRegime.EXECUTION_FLOW: inferencer._execution_flow_score(mixed_state, slow_context),
            MicrostructureRegime.LIQUIDITY_SHOCK: inferencer._liquidity_shock_score(mixed_state, slow_context),
            MicrostructureRegime.COMPETITIVE_LIQUIDITY: inferencer._competitive_score(mixed_state, slow_context),
        }
    )
    filtered = inferencer.update(mixed_state)

    assert first_posterior.dominant_regime == MicrostructureRegime.CALM_LIQUIDITY
    assert emission[MicrostructureRegime.EXECUTION_FLOW] > emission[MicrostructureRegime.CALM_LIQUIDITY]
    assert filtered.probabilities[MicrostructureRegime.CALM_LIQUIDITY] > emission[MicrostructureRegime.CALM_LIQUIDITY]
    assert filtered.probabilities[MicrostructureRegime.EXECUTION_FLOW] < emission[MicrostructureRegime.EXECUTION_FLOW]


def test_regime_slow_context_uses_incremental_window_sums() -> None:
    engine = FeatureEngine()
    inferencer = RegimeInferencer()
    states = []
    for index in range(4):
        state = engine.update(_quote((index + 1) * 1_000_000_000, 100.0 + index * 0.01, 100.02 + index * 0.01))
        assert state is not None
        states.append(state)
        posterior = inferencer.update(state)

    expected_volatility = sum(state.realized_volatility for state in states) / len(states)
    assert np.isclose(posterior.slow_context.slow_volatility, expected_volatility)
    inferencer.rebuild_context_sums()
    assert inferencer._slow_context() == posterior.slow_context


def test_transition_kernel_mahalanobis_uses_prior_history_only() -> None:
    kernel = TransitionKernel()
    prior_history = [
        np.array([1.0, 0.0]),
        np.array([0.0, 1.0]),
        np.array([1.0, 1.0]),
        np.array([2.0, 1.0]),
        np.array([1.0, 2.0]),
    ]
    kernel.increment_history.extend(prior_history)
    previous = np.array([0.0, 0.0])
    current = np.array([2.0, 2.0])

    covariance = np.cov(np.vstack(prior_history), rowvar=False)
    covariance = np.atleast_2d(covariance) + np.eye(2) * 1e-6
    expected_distance = float(current.T @ np.linalg.pinv(covariance) @ current)

    observed_distance = kernel.mahalanobis_distance(previous, current)

    assert observed_distance == expected_distance
    assert np.array_equal(kernel.increment_history[-1], current)


def test_decision_engine_requires_probability_net_of_costs() -> None:
    config = FrameworkConfig()
    config.transition.min_edge_observations = 3
    decision_engine = DecisionEngine(config.decision, config.transition)
    kernel = TransitionKernel(config.transition)
    edge = EdgeKey("a", "b", MicrostructureRegime.EXECUTION_FLOW)
    for _ in range(3):
        kernel.observe_transition(edge, 1_000)
    for sample in [5.0, 6.0, 4.5, 5.5]:
        kernel.attach_drift(edge, sample)

    state = FeatureEngine().update(_quote(1_000_000_000, 100.0, 100.01, 200, 100))
    regime = L1MicrostructureStateMachine(config).regime_inferencer.update(state)
    intent = decision_engine.decide(edge, kernel.get_edge(edge), kernel.diagnostic(edge), regime, state)

    assert intent.action is TradeAction.BUY


def test_execution_simulator_cancels_when_state_misaligned() -> None:
    config = FrameworkConfig()
    simulator = ExecutionSimulator(config.execution)
    feature_engine = FeatureEngine()
    expected = feature_engine.update(_quote(1_000_000_000, 100.0, 100.01, 300, 100))
    realized = feature_engine.update(_quote(2_000_000_000, 99.8, 100.4, 50, 400))
    machine = L1MicrostructureStateMachine(config)
    regime = machine.regime_inferencer.update(expected)

    edge = EdgeKey("x", "y", MicrostructureRegime.LIQUIDITY_SHOCK)
    intent = machine.decision_engine.decide(edge, machine.transition_kernel.get_edge(edge), machine.transition_kernel.diagnostic(edge), regime, expected)
    request = simulator.build_request(intent, expected, 100)
    report = simulator.execute(request, realized)

    assert report.status == "cancelled"


def test_execution_alignment_is_scale_aware_for_positive_state_features() -> None:
    config = FrameworkConfig()
    simulator = ExecutionSimulator(config.execution)
    expected = FeatureEngine().update(_quote(1_000_000_000, 100.0, 100.01, 300, 100))

    assert expected is not None

    realized = replace(
        expected,
        spread_norm=expected.spread_norm * 4.5,
        flicker_intensity=expected.flicker_intensity * 1.15,
    )

    alignment_probability = simulator.state_alignment_probability(expected, realized)

    assert alignment_probability > config.execution.alignment_probability_threshold


def test_execution_simulator_preserves_hazard_exit_fill_reason() -> None:
    config = FrameworkConfig()
    config.execution.base_fill_probability = 1.0
    simulator = ExecutionSimulator(config.execution)
    state = FeatureEngine().update(_quote(1_000_000_000, 100.0, 100.0, 300, 300))

    assert state is not None

    request = simulator.build_request(
        TradeIntent(
            action=TradeAction.SELL,
            edge=EdgeKey(state.label, state.label, MicrostructureRegime.CALM_LIQUIDITY),
            posterior=PosteriorEstimate(
                mean_bps=0.0,
                std_bps=float("inf"),
                probability_up=0.5,
                probability_down=0.5,
                threshold_bps=0.0,
                sample_count=0,
            ),
            expected_holding_time_ns=0,
            reason="hazard-based invalidation",
        ),
        state,
        quantity=100,
    )
    report = simulator.execute(request, state)

    assert report.status == "filled"
    assert report.reason == "hazard-based invalidation"


def test_state_machine_exit_uses_cause_specific_reason() -> None:
    config = FrameworkConfig()
    config.decision.exit_hazard_threshold = 0.15
    config.execution.base_fill_probability = 1.0
    machine = L1MicrostructureStateMachine(config)
    state = FeatureEngine().update(_quote(1_000_000_000, 100.0, 100.01, 300, 300))

    assert state is not None

    machine.open_positions["AAPL"] = OpenPosition(
        symbol="AAPL",
        side=TradeAction.BUY,
        quantity=100,
        entry_price=100.01,
        entry_timestamp_ns=state.timestamp_ns,
    )

    adverse_state = replace(state, trade_pressure=-0.8, spread_norm=1.0)
    regime = RegimeInferencer().update(adverse_state)

    assert regime is not None

    reports = machine._manage_open_positions(adverse_state, regime)

    assert len(reports) == 1
    assert reports[0].status == "filled"
    assert reports[0].reason == "order-flow reversal invalidation"


def test_execution_simulator_penalizes_large_orders_against_thin_touch_depth() -> None:
    config = FrameworkConfig()
    config.execution.queue_penalty_weight = 1.0
    config.execution.queue_reference_size = 100.0
    simulator = ExecutionSimulator(config.execution)
    expected_state = FeatureEngine().update(_quote(1_000_000_000, 100.0, 100.01, 300, 300))
    deep_state = FeatureEngine().update(_quote(1_000_000_000, 100.0, 100.01, 300, 600))
    thin_state = FeatureEngine().update(_quote(1_000_000_000, 100.0, 100.01, 300, 50))

    assert expected_state is not None
    assert deep_state is not None
    assert thin_state is not None

    request = simulator.build_request(
        TradeIntent(
            action=TradeAction.BUY,
            edge=EdgeKey("tight|neutral|neutral|stable|quiet", "wide|buy_heavy|buy_heavy|chaotic|stressed", MicrostructureRegime.EXECUTION_FLOW),
            posterior=PosteriorEstimate(
                mean_bps=4.0,
                std_bps=1.0,
                probability_up=0.8,
                probability_down=0.2,
                threshold_bps=1.0,
                sample_count=20,
            ),
            expected_holding_time_ns=1_000_000_000,
            reason="unit-test",
        ),
        expected_state,
        quantity=250,
    )

    deep_report = simulator.execute(request, deep_state)
    thin_report = simulator.execute(request, thin_state)

    assert thin_report.fill_probability < deep_report.fill_probability


def test_execution_simulator_fill_decision_is_probability_driven_and_reproducible() -> None:
    config = FrameworkConfig()
    simulator = ExecutionSimulator(config.execution)
    state = FeatureEngine().update(_quote(1_000_000_000, 100.0, 100.01, 300, 300))

    assert state is not None

    request = simulator.build_request(
        TradeIntent(
            action=TradeAction.BUY,
            edge=EdgeKey(state.label, state.label, MicrostructureRegime.CALM_LIQUIDITY),
            posterior=PosteriorEstimate(
                mean_bps=2.0,
                std_bps=1.0,
                probability_up=0.6,
                probability_down=0.4,
                threshold_bps=1.0,
                sample_count=10,
            ),
            expected_holding_time_ns=1_000_000_000,
            reason="unit-test",
        ),
        state,
        quantity=100,
    )

    first_report = simulator.execute(request, state)
    second_report = simulator.execute(request, state)

    assert 0.0 < first_report.fill_probability < 1.0
    assert first_report.status == second_report.status
    assert first_report.fill_price == second_report.fill_price


def test_execution_simulator_reduces_aggressiveness_under_low_observation_confidence() -> None:
    config = FrameworkConfig()
    config.execution.base_fill_probability = 1.0
    simulator = ExecutionSimulator(config.execution)
    state = FeatureEngine().update(_quote(1_000_000_000, 100.0, 100.01, 300, 300))

    assert state is not None

    high_confidence = simulator.build_request(
        TradeIntent(
            action=TradeAction.BUY,
            edge=EdgeKey(state.label, state.label, MicrostructureRegime.CALM_LIQUIDITY),
            posterior=PosteriorEstimate(2.0, 1.0, 0.6, 0.4, 1.0, 10),
            expected_holding_time_ns=1_000_000_000,
            reason="unit-test",
            observation_confidence=1.0,
        ),
        state,
        quantity=100,
    )
    low_confidence = simulator.build_request(
        TradeIntent(
            action=TradeAction.BUY,
            edge=EdgeKey(state.label, state.label, MicrostructureRegime.CALM_LIQUIDITY),
            posterior=PosteriorEstimate(2.0, 1.0, 0.6, 0.4, 1.0, 10),
            expected_holding_time_ns=1_000_000_000,
            reason="unit-test",
            observation_confidence=0.10,
        ),
        state,
        quantity=100,
    )

    high_report = simulator.execute(high_confidence, state)
    low_report = simulator.execute(low_confidence, state)

    assert low_report.fill_probability < high_report.fill_probability
    assert low_report.slippage_bps < high_report.slippage_bps


def test_state_machine_sizes_incrementally_against_portfolio_target_weight() -> None:
    config = FrameworkConfig()
    config.risk.max_position_fraction = 0.50
    config.portfolio.max_weight = 0.10
    machine = L1MicrostructureStateMachine(config)
    state = FeatureEngine().update(_quote(1_000_000_000, 100.0, 100.01, 300, 300))

    assert state is not None

    intent = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey("tight|neutral|neutral|stable|quiet", "wide|buy_heavy|buy_heavy|chaotic|stressed", MicrostructureRegime.EXECUTION_FLOW),
        posterior=PosteriorEstimate(
            mean_bps=4.0,
            std_bps=1.0,
            probability_up=0.8,
            probability_down=0.2,
            threshold_bps=1.0,
            sample_count=20,
        ),
        expected_holding_time_ns=1_000_000_000,
        reason="unit-test",
    )

    machine.signal_expectations["MSFT"] = 2.4
    first_decision = machine._authorize_intent(intent, state)

    assert first_decision.approved
    assert first_decision.quantity == 999

    machine.open_positions["AAPL"] = OpenPosition(
        symbol="AAPL",
        side=TradeAction.BUY,
        quantity=900,
        entry_price=100.01,
        entry_timestamp_ns=state.timestamp_ns,
    )
    second_decision = machine._authorize_intent(intent, state)

    assert second_decision.approved
    assert second_decision.quantity == 99


def test_portfolio_target_fraction_uses_realized_covariance_proxy() -> None:
    config = FrameworkConfig()
    config.portfolio.max_weight = 1.0
    machine = L1MicrostructureStateMachine(config)

    machine.signal_expectations = {"AAPL": 1.0, "MSFT": 1.0}
    machine.return_history["AAPL"] = deque([0.04, -0.04, 0.04, -0.04], maxlen=config.transition.covariance_history)
    machine.return_history["MSFT"] = deque([0.01, -0.01, 0.01, -0.01], maxlen=config.transition.covariance_history)
    machine.realized_volatility_by_symbol = {"AAPL": 0.04, "MSFT": 0.01}

    aapl_target = machine._portfolio_target_fraction("AAPL")
    msft_target = machine._portfolio_target_fraction("MSFT")

    assert aapl_target is not None
    assert msft_target is not None
    assert aapl_target < msft_target


def test_portfolio_target_fraction_applies_runtime_sector_caps() -> None:
    config = FrameworkConfig()
    config.portfolio.max_weight = 1.0
    config.portfolio.sector_cap = 0.25
    machine = L1MicrostructureStateMachine(
        config,
        runtime_artifacts=RuntimeArtifactBundle(metadata={"sector_map": {"AAPL": "tech", "MSFT": "tech"}}),
    )

    machine.signal_expectations = {"AAPL": 1.0, "MSFT": 1.0}
    machine.return_history["AAPL"] = deque([0.02, -0.01, 0.02, -0.01], maxlen=config.transition.covariance_history)
    machine.return_history["MSFT"] = deque([0.02, -0.01, 0.02, -0.01], maxlen=config.transition.covariance_history)
    machine.realized_volatility_by_symbol = {"AAPL": 0.02, "MSFT": 0.02}

    aapl_target = machine._portfolio_target_fraction("AAPL")
    msft_target = machine._portfolio_target_fraction("MSFT")

    assert aapl_target is not None
    assert msft_target is not None
    assert aapl_target <= config.portfolio.sector_cap
    assert msft_target <= config.portfolio.sector_cap


def test_pipeline_resolves_forward_drift_outcomes() -> None:
    config = FrameworkConfig()
    config.transition.min_edge_observations = 999
    config.transition.drift_horizon_ms = 1
    config.execution.latency_ms = 0
    machine = L1MicrostructureStateMachine(config)

    events = [
        _quote(1_000_000_000, 100.00, 100.02, 100, 100),
        _quote(1_100_000_000, 100.01, 100.02, 300, 80),
        _trade(1_150_000_000, 100.02, 200, TradeSide.BUY),
        _quote(1_300_000_000, 100.03, 100.04, 320, 70),
    ]

    updates = machine.run_replay(events)

    assert any(update.transition_edge is not None for update in updates)
    assert any(update.resolved_outcomes for update in updates)
    summary = machine.summarize_transition_edges()
    assert not summary.empty
    assert "drift_mean_bps" in summary.columns
