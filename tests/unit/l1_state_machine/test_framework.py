from __future__ import annotations

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import DecisionEngine, PosteriorEstimate, TradeAction, TradeIntent
from l1_microstructure.events import QuoteEvent, TradeEvent, TradeSide
from l1_microstructure.execution import ExecutionSimulator
from l1_microstructure.features import FeatureEngine
from l1_microstructure.pipeline import L1MicrostructureStateMachine
from l1_microstructure.regime import MicrostructureRegime
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

    assert deep_report.status == "filled"
    assert thin_report.status == "filled"
    assert thin_report.fill_probability < deep_report.fill_probability


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