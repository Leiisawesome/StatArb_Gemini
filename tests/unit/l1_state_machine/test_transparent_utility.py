from __future__ import annotations

from dataclasses import replace

import pytest

from l1_microstructure.decision import TradeAction
from l1_microstructure.events import BookSnapshot
from l1_microstructure.features import (
    FlickerState,
    ObservedState,
    PressureState,
    SpreadState,
    VolatilityState,
)
from l1_microstructure.transparent import (
    ExpectedUtilityDecisionEngine,
    HierarchicalDriftPosterior,
    UtilityCalibrationSample,
    UtilityModel,
    UtilityModelTrainer,
)


def _state() -> ObservedState:
    return ObservedState(
        symbol="AAPL",
        timestamp_ns=2_000,
        book=BookSnapshot("AAPL", 2_000, 100.00, 100.01, 100, 100),
        spread_norm=1.0,
        quote_pressure=0.0,
        trade_pressure=0.0,
        flicker_intensity=4.0,
        realized_volatility=0.001,
        spread_state=SpreadState.NORMAL,
        quote_state=PressureState.NEUTRAL,
        trade_state=PressureState.NEUTRAL,
        flicker_state=FlickerState.COMPETITIVE,
        volatility_state=VolatilityState.NORMAL,
    )


def _posterior(horizon: int, mean: float, std: float = 0.2) -> HierarchicalDriftPosterior:
    return HierarchicalDriftPosterior(
        horizon_ns=horizon,
        mean_bps=mean,
        std_bps=std,
        probability_up=0.9 if mean > 0 else 0.1,
        probability_down=0.1 if mean > 0 else 0.9,
        threshold_bps=1.0,
        expected_holding_time_ns=horizon,
        exact_edge_seen=True,
        exact_observation_count=100,
        support={"global": 0.1, "regime": 0.1, "from_state": 0.2, "exact_edge": 0.6},
    )


def _model() -> UtilityModel:
    samples = [
        UtilityCalibrationSample(
            timestamp_ns=1_000 + index,
            horizon_ns=3_000,
            filled=index % 4 != 0,
            alignment_probability=0.9 if index % 4 != 0 else 0.2,
            spread_bps=1.0,
            slippage_bps=0.3,
        )
        for index in range(40)
    ]
    return UtilityModelTrainer(
        fixed_cost_bps=0.2,
        uncertainty_penalty_multiplier=0.2,
        risk_penalty_bps=1.0,
    ).fit(samples, symbol="AAPL", train_start_ns=1_000, train_end_ns=2_000)


def test_utility_model_round_trips_and_fits_positive_alignment_weight() -> None:
    model = _model()
    restored = UtilityModel.from_dict(model.to_dict())

    assert restored == model
    assert model.fill_alignment_weight >= 0.0
    assert model.fill_spread_penalty >= 0.0


def test_expected_utility_selects_best_action_and_horizon_with_explanation() -> None:
    engine = ExpectedUtilityDecisionEngine(_model())
    decision = engine.decide(
        (_posterior(3_000, 2.0), _posterior(15_000, 4.0)),
        _state(),
        alignment_probability=0.95,
        transition_probability=0.95,
        current_risk_fraction=0.01,
    )

    assert decision.action is TradeAction.BUY
    assert decision.horizon_ns == 15_000
    assert decision.expected_utility_bps > 0.0
    assert {alternative.action for alternative in decision.alternatives} == {TradeAction.BUY, TradeAction.SELL}
    assert decision.to_dict()["reason"] == "selected maximum positive expected utility"


def test_expected_utility_holds_when_uncertainty_consumes_edge() -> None:
    engine = ExpectedUtilityDecisionEngine(_model())
    decision = engine.decide(
        (_posterior(3_000, 1.0, std=20.0),),
        _state(),
        alignment_probability=0.9,
        transition_probability=0.9,
        current_risk_fraction=0.5,
    )

    assert decision.action is TradeAction.HOLD
    assert decision.expected_utility_bps == 0.0


def test_utility_trainer_rejects_future_sample() -> None:
    sample = UtilityCalibrationSample(3_000, 3_000, True, 0.9, 1.0, 0.2)
    with pytest.raises(ValueError, match="boundary"):
        UtilityModelTrainer().fit(
            [sample],
            symbol="AAPL",
            train_start_ns=1_000,
            train_end_ns=2_000,
        )


def test_utility_model_rejects_mixed_engine_version() -> None:
    with pytest.raises(ValueError, match="v2"):
        replace(_model(), engine_version="v1")


def test_expected_utility_applies_regime_fill_and_slippage_calibration() -> None:
    model = replace(
        _model(),
        fill_multiplier_by_regime={"liquidity_shock": 0.25},
        slippage_multiplier_by_regime={"liquidity_shock": 3.0},
    )
    engine = ExpectedUtilityDecisionEngine(model)
    calm = engine.decide(
        (_posterior(3_000, 3.0),),
        _state(),
        alignment_probability=0.95,
        transition_probability=0.95,
        current_risk_fraction=0.0,
        regime="calm_liquidity",
    )
    shock = engine.decide(
        (_posterior(3_000, 3.0),),
        _state(),
        alignment_probability=0.95,
        transition_probability=0.95,
        current_risk_fraction=0.0,
        regime="liquidity_shock",
    )

    assert shock.alternatives[0].fill_probability < calm.alternatives[0].fill_probability
    assert shock.alternatives[0].expected_cost_bps > calm.alternatives[0].expected_cost_bps
    assert shock.expected_utility_bps <= calm.expected_utility_bps


def test_transition_confidence_does_not_distort_execution_fill_probability() -> None:
    engine = ExpectedUtilityDecisionEngine(_model())
    low_confidence = engine.decide(
        (_posterior(3_000, 3.0),),
        _state(),
        alignment_probability=0.95,
        transition_probability=0.05,
        current_risk_fraction=0.0,
    )
    high_confidence = engine.decide(
        (_posterior(3_000, 3.0),),
        _state(),
        alignment_probability=0.95,
        transition_probability=0.95,
        current_risk_fraction=0.0,
    )

    assert low_confidence.alternatives[0].fill_probability == pytest.approx(
        high_confidence.alternatives[0].fill_probability
    )
    assert low_confidence.alternatives[0].transition_probability == 0.05
    assert high_confidence.alternatives[0].transition_probability == 0.95


def test_spread_only_utility_entrypoint_matches_state_entrypoint() -> None:
    engine = ExpectedUtilityDecisionEngine(_model())
    state = _state()
    posteriors = (_posterior(3_000, 3.0), _posterior(15_000, 4.0))
    spread_bps = state.book.spread / state.book.midpoint * 10_000.0

    from_state = engine.decide(
        posteriors,
        state,
        alignment_probability=0.8,
        transition_probability=0.7,
        current_risk_fraction=0.01,
        regime="calm_liquidity",
    )
    from_spread = engine.decide_for_spread(
        posteriors,
        spread_bps=spread_bps,
        alignment_probability=0.8,
        transition_probability=0.7,
        current_risk_fraction=0.01,
        regime="calm_liquidity",
    )

    assert from_spread == from_state
