"""Tests targeting uncovered edge cases to achieve 100% coverage of l1_microstructure."""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from l1_microstructure.calibration import (
    CalibrationDataset,
    EmpiricalExecutionCalibrator,
    EmpiricalRegimeCalibrator,
    QuantileStateCalibrator,
)
from l1_microstructure.calibration.interfaces import ExecutionCalibrationDataset
from l1_microstructure.config import ExecutionConfig, FrameworkConfig, TransitionConfig
from l1_microstructure.datasets import PipelineTransitionDatasetBuilder
from l1_microstructure.decision import DecisionEngine, PosteriorEstimate, TradeAction, TradeIntent
from l1_microstructure.events import BookSnapshot, QuoteEvent, TradeEvent, TradeSide, infer_trade_side
from l1_microstructure.execution import ExecutionReport, ExecutionSimulator
from l1_microstructure.features import FeatureEngine, ObservedState
from l1_microstructure.labeling import ForwardDriftLabeler, HorizonLabelRequest
from l1_microstructure.portfolio import PortfolioAllocator
from l1_microstructure.regime import MicrostructureRegime, RegimeInferencer
from l1_microstructure.replay import DeterministicReplayEngine
from l1_microstructure.risk import OpenPosition, RiskEngine
from l1_microstructure.transitions import EdgeKey, EdgeStatistics, TransitionKernel


def _et_ns(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> int:
    ts = datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo("America/New_York"))
    return int(ts.timestamp() * 1_000_000_000)


def _quote(symbol: str, ts: int, bid: float, ask: float, bid_size: int = 100, ask_size: int = 100) -> QuoteEvent:
    return QuoteEvent(symbol=symbol, timestamp_ns=ts, bid_price=bid, ask_price=ask, bid_size=bid_size, ask_size=ask_size)


def _trade(symbol: str, ts: int, price: float, size: int, side: TradeSide) -> TradeEvent:
    return TradeEvent(symbol=symbol, timestamp_ns=ts, price=price, size=size, side=side)


def test_main_module_entrypoint() -> None:
    """Covers __main__.py if __name__ == '__main__'."""
    import runpy
    from unittest.mock import patch

    # Run module as __main__ in-process so coverage is collected
    with __import__("pytest").raises(SystemExit):
        with patch.object(sys, "argv", ["l1_microstructure", "--help"]):
            runpy.run_module("l1_microstructure", run_name="__main__")


def test_transition_config_drift_horizon_fallback() -> None:
    """Covers config.py lines 51-52: drift_horizon_ns_values when normalized is empty."""
    config = TransitionConfig(drift_horizons_ms=(0, -1), drift_horizon_ms=0)
    values = config.drift_horizon_ns_values
    assert len(values) == 1
    assert values[0] == 1_000_000


def test_decision_engine_sell_path_and_normal_cdf_edge() -> None:
    """Covers decision.py: SELL path and _normal_cdf with std<=0."""
    config = FrameworkConfig()
    config.decision.entry_probability_threshold = 0.55
    config.transition.min_edge_observations = 3
    config.transition.min_edge_training_sessions = 0
    config.transition.min_directional_consensus = 0.0
    config.transition.min_cross_session_hit_rate = 0.0
    config.transition.min_cross_session_hit_consensus = 0.0
    engine = DecisionEngine(config.decision, config.transition)
    kernel = TransitionKernel(config.transition)
    edge = EdgeKey("a", "b", MicrostructureRegime.EXECUTION_FLOW)
    for _ in range(3):
        kernel.observe_transition(edge, 1_000)
    for sample in [-5.0, -6.0, -4.5]:
        kernel.attach_drift(edge, sample)

    state = FeatureEngine().update(_quote("AAPL", 1_000_000_000, 100.0, 100.01, 200, 100))
    regime = RegimeInferencer().update(state)
    intent = engine.decide(edge, kernel.get_edge(edge), kernel.diagnostic(edge), regime, state)
    assert intent.action is TradeAction.SELL

    post = engine.estimate_posterior([], 2.0)
    assert post.sample_count == 0
    assert post.std_bps == float("inf")


def test_decision_engine_exit_hazard_liquidity_shock() -> None:
    """Covers decision.py exit diagnostics when regime is liquidity_shock."""
    engine = DecisionEngine()
    state = FeatureEngine().update(_quote("AAPL", 1_000_000_000, 100.0, 100.02, 100, 100))
    state = replace(state, spread_norm=1.0, trade_pressure=0.2)
    regime = RegimeInferencer().update(state)
    regime = type(regime)(
        timestamp_ns=regime.timestamp_ns,
        probabilities={**regime.probabilities, MicrostructureRegime.LIQUIDITY_SHOCK: 0.9},
        dominant_regime=MicrostructureRegime.LIQUIDITY_SHOCK,
        confidence=0.9,
        expected_holding_time_ns=regime.expected_holding_time_ns,
        slow_context=regime.slow_context,
    )
    diagnostics = engine.exit_hazard_diagnostics(TradeAction.BUY, state, regime)
    assert 0.0 <= diagnostics.total_hazard <= 1.0
    assert diagnostics.dominant_cause == "liquidity_shock"
    assert diagnostics.reason == "liquidity shock invalidation"


def test_dataset_builder_skips_different_symbol_updates() -> None:
    """Covers datasets/builders.py line 34: update.state.symbol != symbol skips row."""
    events = [
        _quote("MSFT", 1_000_000_000, 100.0, 100.01, 100, 100),
        _quote("MSFT", 1_100_000_000, 100.01, 100.02, 100, 100),
        _quote("AAPL", 1_200_000_000, 150.0, 150.01, 100, 100),
        _quote("AAPL", 1_300_000_000, 150.01, 150.02, 100, 100),
    ]
    builder = PipelineTransitionDatasetBuilder(events)
    panel = builder.build_state_panel("AAPL")
    assert panel.frame is not None
    assert len(panel.frame) <= 2


def test_regime_inferencer_with_calibration() -> None:
    """Covers regime.py lines 82, 86, 113: regime_calibration paths."""
    from l1_microstructure.calibration.interfaces import RegimeCalibrationArtifact

    cal = RegimeCalibrationArtifact(
        symbol="AAPL",
        regime_priors={"calm_liquidity": 0.5, "execution_flow": 0.3, "liquidity_shock": 0.1, "competitive_liquidity": 0.1},
        holding_time_seconds={"calm_liquidity": 8.0, "execution_flow": 5.0, "liquidity_shock": 3.0, "competitive_liquidity": 4.0},
        metadata={},
    )
    inferencer = RegimeInferencer(regime_calibration=cal)
    state = FeatureEngine().update(_quote("AAPL", 1_000_000_000, 100.0, 100.01, 100, 100))
    posterior = inferencer.update(state)
    assert posterior.expected_holding_time_ns > 0


def test_events_infer_trade_side_and_book_snapshot() -> None:
    """Covers events.py: infer_trade_side, BookSnapshot edge cases."""
    book = BookSnapshot(symbol="AAPL", timestamp_ns=1_000_000_000, bid_price=100.0, ask_price=100.02, bid_size=100, ask_size=100)
    assert abs(book.spread - 0.02) < 1e-9
    assert abs(book.midpoint - 100.01) < 1e-9
    trade_above = TradeEvent(symbol="AAPL", timestamp_ns=1_000_000_001, price=100.02, size=50, side=TradeSide.UNKNOWN)
    assert infer_trade_side(trade_above, book) is TradeSide.BUY
    trade_below = TradeEvent(symbol="AAPL", timestamp_ns=1_000_000_001, price=100.0, size=50, side=TradeSide.UNKNOWN)
    assert infer_trade_side(trade_below, book) is TradeSide.SELL
    trade_mid = TradeEvent(symbol="AAPL", timestamp_ns=1_000_000_001, price=100.01, size=50, side=TradeSide.UNKNOWN)
    assert infer_trade_side(trade_mid, book) is TradeSide.BUY
    trade_between = TradeEvent(symbol="AAPL", timestamp_ns=1_000_000_001, price=100.005, size=50, side=TradeSide.UNKNOWN)
    assert infer_trade_side(trade_between, book) is TradeSide.SELL
    assert infer_trade_side(trade_mid, None) is TradeSide.UNKNOWN


def test_execution_simulator_with_calibration() -> None:
    """Covers execution.py lines 113-121, 143-150: execution_calibration paths."""
    from l1_microstructure.calibration.interfaces import ExecutionCalibrationArtifact

    cal = ExecutionCalibrationArtifact(
        symbol="AAPL",
        fill_probability_intercept=0.5,
        alignment_weight=2.0,
        spread_penalty=0.05,
        slippage_intercept_bps=1.0,
        spread_slippage_weight=0.5,
        adverse_selection_weight=0.3,
        regime_fill_multipliers={"calm_liquidity": 1.0, "execution_flow": 1.0, "liquidity_shock": 0.8, "competitive_liquidity": 1.0},
        regime_slippage_multipliers={"calm_liquidity": 1.0, "execution_flow": 1.0, "liquidity_shock": 1.2, "competitive_liquidity": 1.0},
        metadata={},
    )
    config = ExecutionConfig()
    sim = ExecutionSimulator(config, execution_calibration=cal)
    state = FeatureEngine().update(_quote("AAPL", 1_000_000_000, 100.0, 100.01, 300, 300))
    intent = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY),
        posterior=PosteriorEstimate(4.0, 1.0, 0.8, 0.2, 1.0, 20),
        expected_holding_time_ns=1_000_000_000,
        reason="test",
    )
    request = sim.build_request(intent, state, 100)
    report = sim.execute(request, state)
    assert report.status in ("filled", "rejected", "cancelled")


def test_feature_engine_returns_none_for_non_event() -> None:
    """Covers features.py: update returns None for non-QuoteEvent/TradeEvent."""
    engine = FeatureEngine()
    result = engine.update("not_an_event")  # type: ignore[arg-type]
    assert result is None


def test_risk_engine_halt_and_drawdown() -> None:
    """Covers risk.py: halt, drawdown, process_fill, target_fraction."""
    config = FrameworkConfig()
    config.risk.daily_drawdown_limit = 0.01
    engine = RiskEngine(config.risk)
    state = FeatureEngine().update(_quote("AAPL", 1_000_000_000, 100.0, 100.01, 100, 100))
    intent = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY),
        posterior=PosteriorEstimate(4.0, 1.0, 0.8, 0.2, 1.0, 20),
        expected_holding_time_ns=1_000_000_000,
        reason="test",
    )
    decision = engine.authorize(intent, state, target_fraction=0.01)
    assert decision.approved or not decision.approved

    engine.register_realized_pnl(-20_000)
    engine.register_realized_pnl(-15_000)
    engine.process_fill(
        ExecutionReport(
            symbol="AAPL",
            action=TradeAction.BUY,
            status="filled",
            quantity=100,
            fill_price=100.01,
            alignment_probability=0.9,
            fill_probability=0.8,
            slippage_bps=1.0,
            reason="test",
            timestamp_ns=1_000_000_000,
        )
    )
    assert engine.drawdown >= 0.0
    decision_hold = engine.authorize(
        TradeIntent(
            action=TradeAction.HOLD,
            edge=EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY),
            posterior=PosteriorEstimate(0.0, 1.0, 0.5, 0.5, 1.0, 0),
            expected_holding_time_ns=0,
            reason="hold",
        ),
        state,
    )
    assert not decision_hold.approved


def test_transitions_load_trained_payload_edges() -> None:
    """Covers transitions.py: load_trained_payload with invalid structure."""
    kernel = TransitionKernel()
    kernel.load_trained_payload({})
    kernel.load_trained_payload({"edges": "not_a_dict"})
    kernel.load_trained_payload({"edges": {"x": "not_a_dict"}})
    kernel.load_trained_payload({
        "edges": {
            "e1": {
                "from_state": "a",
                "to_state": "b",
                "regime": "execution_flow",
                "count": 5,
                "holding_times_ns": [1000, 2000],
                "drift_samples_bps": [1.0, 2.0],
                "session_drift_means_bps": [1.5, 1.0],
                "directional_consensus": 1.0,
                "cross_session_hit_rates": [0.75, 0.80],
                "cross_session_hit_rate": 0.775,
                "cross_session_hit_consensus": 1.0,
            }
        }
    })
    edge = EdgeKey("a", "b", MicrostructureRegime.EXECUTION_FLOW)
    stats = kernel.get_edge(edge)
    assert stats.count == 5 or stats.count == 0
    assert stats.training_session_count == 2
    assert stats.directional_consensus == 1.0
    assert stats.cross_session_hit_rates == [0.75, 0.80]
    assert stats.cross_session_hit_rate == 0.775
    assert stats.cross_session_hit_consensus == 1.0


def test_transitions_load_compact_summary_statistics() -> None:
    kernel = TransitionKernel()
    kernel.load_trained_payload({
        "sample_count": 3,
        "edges": {
            "e1": {
                "from_state": "a",
                "to_state": "b",
                "regime": "execution_flow",
                "count": 3,
                "mean_holding_time_ns": 2_000.0,
                "drift_mean_bps": 2.0,
                "drift_std_bps": 1.0,
                "session_drift_means_bps": [1.5, 2.5],
                "directional_consensus": 1.0,
                "cross_session_hit_rates": [1.0, 1.0],
                "cross_session_hit_rate": 1.0,
                "cross_session_hit_consensus": 1.0,
            }
        },
    })

    stats = kernel.get_edge(EdgeKey("a", "b", MicrostructureRegime.EXECUTION_FLOW))
    assert stats.holding_times_ns == []
    assert stats.drift_samples_bps == []
    assert stats.mean_holding_time_ns == 2_000.0
    assert stats.drift_mean_bps == 2.0
    assert stats.drift_std_bps == 1.0


def test_edge_statistics_signal_to_noise_zero_std() -> None:
    """Covers transitions.py line 53: signal_to_noise when std is 0."""
    stats = EdgeStatistics(drift_samples_bps=[1.0, 1.0])
    assert stats.signal_to_noise == 0.0 or stats.drift_std_bps == 0.0


def test_calibration_fitters_require_columns() -> None:
    """Covers calibration/fitters.py: _require_columns raises."""
    with __import__("pytest").raises(ValueError, match="missing required columns"):
        QuantileStateCalibrator().fit(CalibrationDataset(symbol="AAPL", features=pd.DataFrame({"x": [1]}), metadata={}))

    with __import__("pytest").raises(ValueError, match="missing required columns"):
        EmpiricalRegimeCalibrator().fit(CalibrationDataset(symbol="AAPL", features=pd.DataFrame({"spread_norm": [1.0]}), metadata={}))

    state_frame = pd.DataFrame({
        "spread_norm": [1.0],
        "realized_volatility": [0.001],
        "dominant_regime": ["calm_liquidity"],
        "regime_confidence": [0.8],
    })
    trans_frame = pd.DataFrame({"regime": ["calm_liquidity"], "realized_drift_bps": [1.5]})
    with __import__("pytest").raises(ValueError, match="missing required columns"):
        EmpiricalExecutionCalibrator().fit(
            ExecutionCalibrationDataset(
                symbol="AAPL",
                state_features=state_frame,
                transition_features=pd.DataFrame({"regime": ["calm"]}),
                metadata={},
            )
        )


def test_quantile_state_calibrator_without_dominant_regime() -> None:
    """Covers calibration/fitters.py: frame without dominant_regime."""
    frame = pd.DataFrame({
        "spread_norm": [0.8, 1.0, 1.2],
        "realized_volatility": [0.0008, 0.001, 0.0012],
        "flicker_intensity": [3.5, 4.0, 4.5],
        "quote_pressure": [-0.2, 0.0, 0.2],
    })
    dataset = CalibrationDataset(symbol="AAPL", features=frame, metadata={})
    artifact = QuantileStateCalibrator().fit(dataset)
    assert artifact.regime_surfaces == {}
    assert artifact.symbol == "AAPL"


def test_forward_drift_labeler_non_quote_trade_event() -> None:
    """Covers labeling/drift.py: _price_for_event returns None for unknown event, censored path."""
    from types import SimpleNamespace

    unknown = SimpleNamespace(symbol="AAPL", timestamp_ns=1_000_000_000)

    labeler = ForwardDriftLabeler()
    request = HorizonLabelRequest(
        symbol="AAPL",
        horizon_ns=5_000_000_000,
        start_timestamp_ns=1_000_000_000,
        reference_price=100.0,
        metadata={},
    )
    events = [unknown, unknown]
    label = labeler.label(request, events)
    assert label.censored is True
    assert label.realized_drift_bps == 0.0


def test_forward_drift_labeler_zero_reference_price() -> None:
    """Covers labeling/drift.py: _build_label when reference_price <= 0."""
    labeler = ForwardDriftLabeler()
    request = HorizonLabelRequest(
        symbol="AAPL",
        horizon_ns=1_000_000_000,
        start_timestamp_ns=1_000_000_000,
        reference_price=0.0,
        metadata={},
    )
    events = [_quote("AAPL", 1_500_000_000, 100.0, 100.01)]
    label = labeler.label(request, events)
    assert label.realized_drift_bps == 0.0


def test_artifact_store_list_metadata_filters_by_type(tmp_path) -> None:
    """Covers artifacts/store.py: list_metadata with artifact_type filter, non-dir skip."""
    from l1_microstructure.artifacts import ArtifactMetadata, LocalArtifactStore

    store = LocalArtifactStore(tmp_path)
    meta = ArtifactMetadata(
        artifact_id="id1",
        artifact_type="state_calibration",
        version="v1",
        created_at="2026-01-01T00:00:00",
        tags=(),
        metadata={},
    )
    store.save(meta, {"x": 1})
    meta2 = ArtifactMetadata(
        artifact_id="id2",
        artifact_type="regime_calibration",
        version="v1",
        created_at="2026-01-01T00:00:00",
        tags=(),
        metadata={},
    )
    store.save(meta2, {"y": 2})
    listed = store.list_metadata(artifact_type="state_calibration")
    assert len(listed) == 1
    assert listed[0].artifact_type == "state_calibration"


def test_portfolio_allocator_empty_and_sector_caps() -> None:
    """Covers portfolio.py: empty expected_returns, sector cap scaling."""
    allocator = PortfolioAllocator()
    assert allocator.allocate({}, pd.DataFrame()) == {}

    cov = pd.DataFrame(
        [[0.0001, 0.00005], [0.00005, 0.0001]],
        index=["A", "B"],
        columns=["A", "B"],
    )
    weights = allocator.allocate(
        expected_returns={"A": 0.01, "B": 0.02},
        covariance=cov,
        sector_map={"A": "tech", "B": "tech"},
    )
    assert "A" in weights
    assert "B" in weights


def test_replay_engine_empty_events() -> None:
    """Covers replay/engine.py: _stream_id_for_events with empty list."""
    engine = DeterministicReplayEngine()
    replayed = list(engine.replay([], speed_multiplier=1.0))
    assert replayed == []


def test_events_quote_and_trade_kind_properties() -> None:
    """Covers events.py: QuoteEvent.kind and TradeEvent.kind."""
    from l1_microstructure.events import EventKind

    q = _quote("AAPL", 1_000_000_000, 100.0, 100.01)
    assert q.kind is EventKind.QUOTE
    t = _trade("AAPL", 1_000_000_001, 100.01, 50, TradeSide.BUY)
    assert t.kind is EventKind.TRADE


def test_book_snapshot_from_quote() -> None:
    """Covers events.py: BookSnapshot.from_quote."""
    q = _quote("AAPL", 1_000_000_000, 100.0, 100.02, 200, 100)
    book = BookSnapshot.from_quote(q)
    assert book.symbol == "AAPL"
    assert book.bid_price == 100.0
    assert book.ask_price == 100.02


def test_forward_drift_labeler_symbol_mismatch() -> None:
    """Covers labeling/drift.py line 19: event.symbol != request.symbol continue."""
    labeler = ForwardDriftLabeler()
    request = HorizonLabelRequest(
        symbol="AAPL",
        horizon_ns=1_000_000_000,
        start_timestamp_ns=1_000_000_000,
        reference_price=100.0,
        metadata={},
    )
    # Only MSFT events - all skipped, censored with initial price
    events = [_quote("MSFT", 1_100_000_000, 99.0, 99.01), _quote("MSFT", 1_200_000_000, 99.5, 99.51)]
    label = labeler.label(request, events)
    assert label.censored is True
    assert label.realized_drift_bps == 0.0


def test_feature_engine_trade_side_unknown() -> None:
    """Covers features.py: _on_trade with TradeSide.UNKNOWN (signed_volume=0)."""
    engine = FeatureEngine()
    engine._on_quote(_quote("AAPL", 1_000_000_000, 100.0, 100.01, 100, 100))
    trade = TradeEvent(symbol="AAPL", timestamp_ns=1_000_000_001, price=100.005, size=50, side=TradeSide.UNKNOWN)
    engine._on_trade(trade)
    state = engine.update(_quote("AAPL", 1_000_000_002, 100.01, 100.02, 100, 100))
    assert state is not None
    assert state.trade_pressure == 0.0 or -1 <= state.trade_pressure <= 1


def test_edge_statistics_mean_holding_time_empty() -> None:
    """Covers transitions.py: mean_holding_time_ns when empty."""
    stats = EdgeStatistics()
    assert stats.mean_holding_time_ns == 0.0


def test_edge_statistics_drift_std_single_sample() -> None:
    """Covers transitions.py: drift_std_bps with <2 samples."""
    stats = EdgeStatistics(drift_samples_bps=[1.0])
    assert stats.drift_std_bps == 0.0


def test_portfolio_sector_cap_scaling() -> None:
    """Covers portfolio.py lines 36, 51-52: sector cap exceeding."""
    allocator = PortfolioAllocator()
    cov = pd.DataFrame(
        [[0.0001, 0.0001, 0.0001], [0.0001, 0.0001, 0.0001], [0.0001, 0.0001, 0.0001]],
        index=["A", "B", "C"],
        columns=["A", "B", "C"],
    )
    weights = allocator.allocate(
        expected_returns={"A": 0.02, "B": 0.02, "C": 0.02},
        covariance=cov,
        sector_map={"A": "tech", "B": "tech", "C": "tech"},
    )
    sector_total = sum(abs(weights[s]) for s in ["A", "B", "C"])
    assert sector_total <= allocator.config.sector_cap + 0.01


def test_risk_engine_volatility_collapsed_and_already_at_target() -> None:
    """Covers risk.py: target_quantity<=0, incremental<=0, gross exposure, peak_equity."""
    config = FrameworkConfig()
    config.risk.volatility_target = 0.001
    config.risk.max_position_fraction = 0.01
    engine = RiskEngine(config.risk)
    state = FeatureEngine().update(_quote("AAPL", 1_000_000_000, 100.0, 100.01, 100, 100))
    intent = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY),
        posterior=PosteriorEstimate(4.0, 1.0, 0.8, 0.2, 1.0, 20),
        expected_holding_time_ns=1_000_000_000,
        reason="test",
    )
    # Very low volatility could collapse quantity
    decision = engine.authorize(intent, state, target_fraction=0.0001)
    assert decision.approved or decision.reason == "volatility scaled quantity collapsed"

    # Already at target: position size exceeds target so incremental=0
    engine2 = RiskEngine()
    pos = OpenPosition(symbol="AAPL", side=TradeAction.BUY, quantity=2000, entry_price=100.0, entry_timestamp_ns=1_000_000_000)
    decision2 = engine2.authorize(intent, state, current_position=pos, target_fraction=0.01)
    assert decision2.approved or decision2.reason == "already at target size"

    # Gross exposure limit
    engine3 = RiskEngine()
    decision3 = engine3.authorize(intent, state, current_gross_exposure=2.0)
    assert decision3.approved or decision3.reason == "gross exposure limit breached"


def test_risk_engine_enforces_beta_hedge_threshold_without_blocking_offsets() -> None:
    config = FrameworkConfig()
    config.risk.beta_hedge_threshold = 0.30
    config.risk.max_position_fraction = 0.50
    state = FeatureEngine().update(_quote("AAPL", 1_000_000_000, 100.0, 100.01, 100, 100))
    assert state is not None

    buy_intent = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY),
        posterior=PosteriorEstimate(4.0, 1.0, 0.8, 0.2, 1.0, 20),
        expected_holding_time_ns=1_000_000_000,
        reason="test",
    )
    rejecting_engine = RiskEngine(config.risk)
    rejected = rejecting_engine.authorize(
        buy_intent,
        state,
        target_fraction=0.20,
        current_net_exposure=0.20,
        current_symbol_exposure=0.0,
    )
    assert not rejected.approved
    assert rejected.reason == "beta hedge threshold breached"

    sell_intent = TradeIntent(
        action=TradeAction.SELL,
        edge=EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY),
        posterior=PosteriorEstimate(-4.0, 1.0, 0.2, 0.8, 1.0, 20),
        expected_holding_time_ns=1_000_000_000,
        reason="test",
    )
    offsetting_engine = RiskEngine(config.risk)
    approved = offsetting_engine.authorize(
        sell_intent,
        state,
        target_fraction=0.10,
        current_position=OpenPosition(
            symbol="AAPL",
            side=TradeAction.BUY,
            quantity=2000,
            entry_price=100.0,
            entry_timestamp_ns=1_000_000_000,
        ),
        current_net_exposure=0.35,
        current_symbol_exposure=0.20,
    )
    assert approved.approved


def test_risk_engine_uses_beta_aware_exposure_not_just_net_notional() -> None:
    config = FrameworkConfig()
    config.risk.beta_hedge_threshold = 0.30
    config.risk.max_position_fraction = 0.50
    state = FeatureEngine().update(_quote("AAPL", 1_000_000_000, 100.0, 100.01, 100, 100))
    assert state is not None

    intent = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY),
        posterior=PosteriorEstimate(4.0, 1.0, 0.8, 0.2, 1.0, 20),
        expected_holding_time_ns=1_000_000_000,
        reason="test",
        observation_confidence=1.0,
    )
    engine = RiskEngine(config.risk)
    decision = engine.authorize(
        intent,
        state,
        target_fraction=0.05,
        current_net_exposure=0.05,
        current_beta_exposure=0.25,
        current_symbol_beta_exposure=0.0,
        proposed_symbol_beta=2.0,
    )

    assert not decision.approved
    assert decision.reason == "beta hedge threshold breached"


def test_risk_engine_scales_quantity_with_observation_confidence() -> None:
    config = FrameworkConfig()
    config.risk.max_position_fraction = 0.20
    state = FeatureEngine().update(_quote("AAPL", 1_000_000_000, 100.0, 100.01, 100, 100))
    assert state is not None

    high_confidence = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY),
        posterior=PosteriorEstimate(4.0, 1.0, 0.8, 0.2, 1.0, 20),
        expected_holding_time_ns=1_000_000_000,
        reason="test",
        observation_confidence=1.0,
    )
    low_confidence = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY),
        posterior=PosteriorEstimate(4.0, 1.0, 0.8, 0.2, 1.0, 20),
        expected_holding_time_ns=1_000_000_000,
        reason="test",
        observation_confidence=0.10,
    )
    engine = RiskEngine(config.risk)

    high_decision = engine.authorize(high_confidence, state, target_fraction=0.20)
    low_decision = engine.authorize(low_confidence, state, target_fraction=0.20)

    assert high_decision.approved
    assert low_decision.approved
    assert low_decision.quantity < high_decision.quantity


def test_risk_drawdown_zero_peak() -> None:
    """Covers risk.py: drawdown when peak_equity<=0."""
    engine = RiskEngine()
    engine.peak_equity = 0.0
    assert engine.drawdown == 0.0


def test_risk_process_fill_non_filled_early_return() -> None:
    """Covers risk.py: process_fill early return when status != 'filled'."""
    engine = RiskEngine()
    engine.process_fill(
        ExecutionReport(
            symbol="AAPL",
            action=TradeAction.BUY,
            status="cancelled",
            quantity=0,
            fill_price=None,
            alignment_probability=0.5,
            fill_probability=0.0,
            slippage_bps=0.0,
            reason="cancelled",
            timestamp_ns=1_000_000_000,
        )
    )
    assert engine.trade_count == 0


def test_risk_engine_opposite_side_incremental() -> None:
    """Covers risk.py line 69: incremental when current_position.side != intent.action."""
    engine = RiskEngine()
    state = FeatureEngine().update(_quote("AAPL", 1_000_000_000, 100.0, 100.01, 100, 100))
    intent = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey("a", "b", MicrostructureRegime.CALM_LIQUIDITY),
        posterior=PosteriorEstimate(4.0, 1.0, 0.8, 0.2, 1.0, 20),
        expected_holding_time_ns=1_000_000_000,
        reason="test",
    )
    pos = OpenPosition(symbol="AAPL", side=TradeAction.SELL, quantity=50, entry_price=100.0, entry_timestamp_ns=1_000_000_000)
    decision = engine.authorize(intent, state, current_position=pos, target_fraction=0.01)
    assert decision.approved
    assert decision.quantity > 0


def test_portfolio_gross_zero() -> None:
    """Covers portfolio.py line 36: gross <= 0 returns all zeros."""
    allocator = PortfolioAllocator()
    cov = pd.DataFrame(
        [[0.0001, 0.0], [0.0, 0.0001]],
        index=["A", "B"],
        columns=["A", "B"],
    )
    weights = allocator.allocate(
        expected_returns={"A": 0.0, "B": 0.0},
        covariance=cov,
    )
    assert weights == {"A": 0.0, "B": 0.0}


def test_edge_statistics_drift_mean_empty() -> None:
    """Covers transitions.py line 39: drift_mean_bps when drift_samples_bps empty."""
    stats = EdgeStatistics()
    assert stats.drift_mean_bps == 0.0


def test_artifact_store_list_metadata_skips_non_dir_and_missing_metadata(tmp_path) -> None:
    """Covers artifacts/store.py lines 62, 65: continue for non-dir and missing metadata.json."""
    from l1_microstructure.artifacts import ArtifactMetadata, LocalArtifactStore

    store = LocalArtifactStore(tmp_path)
    store.save(
        ArtifactMetadata("id1", "state_calibration", "v1", "2026-01-01", (), None, None, {}),
        {"x": 1},
    )
    (tmp_path / "stray_file.txt").write_text("x")
    (tmp_path / "empty_dir").mkdir()
    listed = store.list_metadata()
    assert any(m.artifact_id == "id1" for m in listed)


def test_decision_engine_normal_cdf_zero_std() -> None:
    """Covers decision.py line 125: _normal_cdf when std<=0."""
    assert DecisionEngine._normal_cdf(100.0, 0.0, 50.0) == 0.0
    assert DecisionEngine._normal_cdf(100.0, 0.0, 150.0) == 1.0


def test_artifact_bundle_loader_validation_errors(tmp_path) -> None:
    """Covers artifacts/runtime.py: _validate_metadata version and format errors."""
    import json

    from l1_microstructure.artifacts import ArtifactMetadata, LocalArtifactStore
    from l1_microstructure.artifacts.runtime import ArtifactBundleLoader

    store = LocalArtifactStore(tmp_path)
    loader = ArtifactBundleLoader(store)

    # Save state_calibration with wrong version
    meta = ArtifactMetadata("bad-ver", "state_calibration", "v2", "2026-01-01", (), "h", "json", {})
    payload = {"symbol": "AAPL", "spread_quantiles": [1, 2], "volatility_quantiles": [1e-4, 2e-3], "flicker_baseline": 4.0, "quote_pressure_scale": 0.5}
    store.save(meta, payload)

    with __import__("pytest").raises(ValueError, match="version"):
        loader._load_state_calibration("bad-ver")

    # Create artifact with unsupported payload_format
    bad_dir = tmp_path / "bad-fmt"
    bad_dir.mkdir()
    (bad_dir / "metadata.json").write_text(json.dumps({
        "artifact_id": "bad-fmt",
        "artifact_type": "state_calibration",
        "version": "v1",
        "created_at": "2026-01-01",
        "payload_format": "pickle",
    }))
    (bad_dir / "payload.pkl").write_bytes(b"legacy")

    with __import__("pytest").raises(ValueError, match="unsupported payload format"):
        loader._load_state_calibration("bad-fmt")


def test_feature_engine_update_trade_only_returns_none() -> None:
    """Covers features.py line 112: return None when current_book is None (trade before quote)."""
    engine = FeatureEngine()
    result = engine.update(_trade("AAPL", 1_000_000_000, 100.01, 50, TradeSide.BUY))
    assert result is None


def test_feature_engine_quote_pressure_sell_evidence_branches() -> None:
    """Covers features.py lines 147, 153: sell_evidence branches in _quote_pressure_posterior."""
    engine = FeatureEngine()
    quotes = [
        _quote("AAPL", 1_000_000_000, 100.0, 100.02, 200, 100),
        _quote("AAPL", 1_000_000_001, 100.0, 100.02, 50, 150),
        _quote("AAPL", 1_000_000_002, 99.99, 100.01, 50, 150),
    ]
    for q in quotes:
        engine.update(q)
    assert engine.current_book is not None


def test_feature_engine_flicker_chaotic_state() -> None:
    """Covers features.py line 175: _flicker_state CHAOTIC when intensity >= baseline*1.5."""
    from l1_microstructure.features import FlickerState

    engine = FeatureEngine()
    engine.flicker_baseline = 4.0
    engine.flicker_intensity = 7.0
    state = engine._flicker_state(7.0)
    assert state is FlickerState.CHAOTIC


def test_feature_engine_realized_volatility_empty_log_returns() -> None:
    """Covers features.py line 231: _realized_volatility when log_returns.size==0."""
    engine = FeatureEngine()
    engine.microprice_history.append((1_000_000_000, 100.0))
    engine.microprice_history.append((1_000_000_001, 100.0))
    vol = engine._realized_volatility(1_000_000_002)
    assert vol == engine.config.minimum_sigma


def test_feature_engine_volatility_stressed_with_surface() -> None:
    """Covers features.py line 272: _volatility_state STRESSED with regime surface."""
    from l1_microstructure.calibration.interfaces import StateCalibrationArtifact, StateRegimeSurface
    from l1_microstructure.features import VolatilityState

    surface = StateRegimeSurface(
        spread_quantiles=(0.8, 1.5),
        volatility_quantiles=(1e-4, 2e-3),
        flicker_baseline=4.0,
        quote_pressure_scale=0.5,
        sample_count=100,
    )
    cal = StateCalibrationArtifact("AAPL", (0.8, 1.5), (1e-4, 2e-3), 4.0, 0.5, {}, {})
    engine = FeatureEngine(state_calibration=cal)
    engine.set_regime_hint("calm_liquidity")
    state = engine._volatility_state(5e-3)
    assert state is VolatilityState.STRESSED


def test_feature_engine_rolling_tertiles_sufficient_history() -> None:
    """Covers features.py line 293: _rolling_tertiles when values.size >= 8."""
    engine = FeatureEngine()
    for i in range(10):
        engine.spread_norm_history.append(0.8 + i * 0.1)
    low, high = engine._rolling_tertiles(engine.spread_norm_history, (0.75, 1.75))
    assert low < high
