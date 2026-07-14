from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from l1_microstructure.events import BookSnapshot
from l1_microstructure.features import (
    FlickerState,
    ObservedState,
    PressureState,
    SpreadState,
    VolatilityState,
)
from l1_microstructure.transparent import RobustStateVectorRuntime, RobustStateVectorTrainer, StateVectorModel


def _state(index: int, *, symbol: str = "AAPL", shock: bool = False) -> ObservedState:
    scale = 8.0 if shock else 1.0
    return ObservedState(
        symbol=symbol,
        timestamp_ns=1_000_000_000 + index * 1_000_000,
        book=BookSnapshot(symbol, 1_000_000_000 + index * 1_000_000, 100.0, 100.01, 100, 100),
        spread_norm=1.0 + 0.05 * index * scale,
        quote_pressure=(-0.2 + 0.04 * index) * scale,
        trade_pressure=(-0.1 + 0.02 * index) * scale,
        flicker_intensity=4.0 + 0.1 * index * scale,
        realized_volatility=0.001 + 0.00001 * index * scale,
        spread_state=SpreadState.NORMAL,
        quote_state=PressureState.NEUTRAL,
        trade_state=PressureState.NEUTRAL,
        flicker_state=FlickerState.COMPETITIVE,
        volatility_state=VolatilityState.NORMAL,
    )


def _fit_model() -> StateVectorModel:
    states = [_state(index, shock=index >= 9) for index in range(12)]
    targets = [False] * 8 + [True] * 3
    return RobustStateVectorTrainer(calibration_bins=4, transition_probability_threshold=0.60).fit(
        states,
        targets,
        train_start_ns=states[0].timestamp_ns,
        train_end_ns=states[-1].timestamp_ns,
    )


def test_robust_vector_model_round_trips_and_rejects_boundary_leakage() -> None:
    model = _fit_model()
    restored = StateVectorModel.from_dict(model.to_dict())

    assert restored == model
    assert np.allclose(restored.transform(_state(3)), model.transform(_state(3)))

    states = [_state(index) for index in range(4)]
    with pytest.raises(ValueError, match="boundary"):
        RobustStateVectorTrainer().fit(
            states,
            [False, False, True],
            train_start_ns=states[1].timestamp_ns,
            train_end_ns=states[-1].timestamp_ns,
        )


def test_robust_vector_runtime_has_no_euclidean_cold_start_and_explains_score() -> None:
    model = _fit_model()
    runtime = RobustStateVectorRuntime(model)

    first = runtime.update(_state(7))
    second = runtime.update(_state(8))
    shock = runtime.update(_state(11, shock=True))

    assert first.score == 0.0
    assert first.probability == 0.0
    assert first.is_transition is False
    assert second.probability <= shock.probability
    assert sum(shock.feature_contributions.values()) == pytest.approx(shock.score)
    assert set(shock.feature_contributions) == set(model.feature_names)


def test_transition_probability_calibration_is_monotone() -> None:
    model = _fit_model()
    probabilities = [model.probability_for_score(value) for value in np.linspace(0.0, 100.0, 100)]

    assert all(left <= right for left, right in zip(probabilities, probabilities[1:]))
    assert probabilities[-1] >= probabilities[0]


def test_state_vector_model_rejects_mixed_engine_version() -> None:
    model = _fit_model()
    with pytest.raises(ValueError, match="v2"):
        replace(model, engine_version="v1")


def test_vector_calibration_excludes_unresolved_targets_instead_of_marking_them_negative() -> None:
    states = [_state(index) for index in range(8)]

    model = RobustStateVectorTrainer(
        calibration_bins=4,
        transition_probability_threshold=0.25,
    ).fit(
        states,
        (True, False, True, False, None, None, None),
        train_start_ns=states[0].timestamp_ns,
        train_end_ns=states[-1].timestamp_ns,
    )

    assert model.metadata["resolved_target_count"] == 4
    assert model.metadata["censored_target_count"] == 3
