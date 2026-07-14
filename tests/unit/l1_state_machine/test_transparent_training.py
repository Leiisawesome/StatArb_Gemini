from __future__ import annotations

import pytest

from l1_microstructure.calibration import ExecutionCalibrationArtifact, StateCalibrationArtifact
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.events import BookSnapshot
from l1_microstructure.features import (
    FlickerState,
    ObservedState,
    PressureState,
    SpreadState,
    VolatilityState,
)
from l1_microstructure.transparent import RobustStateVectorTrainer, TransparentModelTrainer


def _state(index: int) -> ObservedState:
    group = index // 10
    timestamp_ns = 1_000_000_000 + index * 1_000_000
    spread_states = (SpreadState.TIGHT, SpreadState.NORMAL, SpreadState.WIDE, SpreadState.TIGHT)
    pressure_states = (
        PressureState.NEUTRAL,
        PressureState.BUY_HEAVY,
        PressureState.SELL_HEAVY,
        PressureState.NEUTRAL,
    )
    return ObservedState(
        symbol="AAPL",
        timestamp_ns=timestamp_ns,
        book=BookSnapshot("AAPL", timestamp_ns, 100.0 + index * 0.02, 100.01 + index * 0.02, 100, 100),
        spread_norm=(0.5, 1.0, 3.0, 0.4)[group] + index * 0.001,
        quote_pressure=(0.0, 0.8, -0.8, 0.2)[group],
        trade_pressure=(0.0, 0.9, -0.7, -0.2)[group],
        flicker_intensity=(2.0, 4.0, 8.0, 10.0)[group],
        realized_volatility=(0.0002, 0.0008, 0.004, 0.0005)[group],
        spread_state=spread_states[group],
        quote_state=pressure_states[group],
        trade_state=pressure_states[group],
        flicker_state=(
            FlickerState.STABLE,
            FlickerState.COMPETITIVE,
            FlickerState.CHAOTIC,
            FlickerState.CHAOTIC,
        )[group],
        volatility_state=(
            VolatilityState.QUIET,
            VolatilityState.NORMAL,
            VolatilityState.STRESSED,
            VolatilityState.NORMAL,
        )[group],
    )


def _calibrations():
    state = StateCalibrationArtifact(
        symbol="AAPL",
        spread_quantiles=(0.8, 2.0),
        volatility_quantiles=(0.0005, 0.002),
        flicker_baseline=4.0,
        quote_pressure_scale=1.0,
    )
    execution = ExecutionCalibrationArtifact(
        symbol="AAPL",
        fill_probability_intercept=1.0,
        alignment_weight=2.0,
        spread_penalty=0.05,
        slippage_intercept_bps=0.5,
        spread_slippage_weight=0.5,
        adverse_selection_weight=1.0,
        regime_fill_multipliers={},
        regime_slippage_multipliers={},
        metadata={"row_count": 40, "transition_row_count": 12, "method": "test"},
    )
    return state, execution


def test_transparent_model_trainer_builds_complete_split_local_bundle() -> None:
    states = [_state(index) for index in range(40)]
    state_calibration, execution_calibration = _calibrations()
    config = FrameworkConfig()
    config.transition.drift_horizon_ms = 1
    config.transition.drift_horizons_ms = (1, 2, 3)
    trainer = TransparentModelTrainer(
        vector_trainer=RobustStateVectorTrainer(
            calibration_bins=5,
            transition_probability_threshold=0.15,
        )
    )

    artifacts = trainer.fit(
        states,
        state_calibration=state_calibration,
        execution_calibration=execution_calibration,
        train_start_ns=states[0].timestamp_ns,
        train_end_ns=states[-1].timestamp_ns,
        config=config,
    )

    assert artifacts.symbol == "AAPL"
    assert artifacts.engine_version == "v2"
    assert artifacts.state_vector_model.train_end_ns == states[-1].timestamp_ns
    assert set(artifacts.hierarchical_transition_model.horizons_ns) == {1_000_000, 2_000_000, 3_000_000}
    assert artifacts.utility_model.metadata["trainer"] == "execution_calibration_adapter"
    assert artifacts.utility_model.fixed_cost_bps == config.decision.transaction_cost_bps
    assert artifacts.metadata["candidate_transition_sample_count"] > 0


def test_transparent_model_trainer_rejects_cross_boundary_state() -> None:
    states = [_state(index) for index in range(40)]
    state_calibration, execution_calibration = _calibrations()
    with pytest.raises(ValueError, match="boundary"):
        TransparentModelTrainer().fit(
            states,
            state_calibration=state_calibration,
            execution_calibration=execution_calibration,
            train_start_ns=states[1].timestamp_ns,
            train_end_ns=states[-1].timestamp_ns,
        )
