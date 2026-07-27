from __future__ import annotations

import pytest
import numpy as np

from l1_microstructure.events import BookSnapshot
from l1_microstructure.features import (
    FlickerState,
    ObservedState,
    PressureState,
    SpreadState,
    VolatilityState,
)
from l1_microstructure.transparent import (
    RobustStateVectorTrainer,
    SemiMarkovRegimeModel,
    SemiMarkovRegimeRuntime,
    SemiMarkovRegimeTrainer,
)


def _state(index: int, group: int) -> ObservedState:
    templates = (
        (0.5, 0.0, 0.0, 2.0, 0.0002),
        (1.0, 0.8, 0.9, 4.0, 0.0008),
        (3.0, -0.5, -0.7, 8.0, 0.0040),
        (0.4, 0.2, -0.2, 10.0, 0.0005),
    )
    spread, quote, trade, flicker, volatility = templates[group]
    jitter = (index % 3 - 1) * 0.01
    timestamp_ns = 1_000_000_000 + index * 1_000_000_000
    return ObservedState(
        symbol="AAPL",
        timestamp_ns=timestamp_ns,
        book=BookSnapshot("AAPL", timestamp_ns, 100.0, 100.01, 100, 100),
        spread_norm=spread + jitter,
        quote_pressure=quote + jitter,
        trade_pressure=trade - jitter,
        flicker_intensity=flicker + jitter,
        realized_volatility=volatility + jitter * 1e-4,
        spread_state=SpreadState.NORMAL,
        quote_state=PressureState.NEUTRAL,
        trade_state=PressureState.NEUTRAL,
        flicker_state=FlickerState.COMPETITIVE,
        volatility_state=VolatilityState.NORMAL,
    )


def _models():
    states = [_state(index, index // 10) for index in range(40)]
    vector = RobustStateVectorTrainer(calibration_bins=5).fit(
        states,
        [False] * 9 + [True] + [False] * 9 + [True] + [False] * 9 + [True] + [False] * 9,
        train_start_ns=states[0].timestamp_ns,
        train_end_ns=states[-1].timestamp_ns,
    )
    regime = SemiMarkovRegimeTrainer().fit(
        states,
        vector,
        train_start_ns=states[0].timestamp_ns,
        train_end_ns=states[-1].timestamp_ns,
    )
    return states, vector, regime


def test_semi_markov_model_is_fitted_semantically_anchored_and_round_trips() -> None:
    _, _, model = _models()
    restored = SemiMarkovRegimeModel.from_dict(model.to_dict())

    assert restored.to_dict() == model.to_dict()
    shock_index = model.regime_order.index("liquidity_shock")
    calm_index = model.regime_order.index("calm_liquidity")
    assert model.emission_means[shock_index][0] > model.emission_means[calm_index][0]
    assert model.emission_means[shock_index][4] > model.emission_means[calm_index][4]
    assert all(duration > 0 for duration in model.expected_duration_ns)


def test_semi_markov_runtime_exposes_prior_emission_and_duration_evidence() -> None:
    states, vector, model = _models()
    runtime = SemiMarkovRegimeRuntime(model, vector)

    posterior = runtime.update(states[0])
    later = runtime.update(_state(41, 2))

    assert sum(posterior.probabilities.values()) == pytest.approx(1.0)
    assert sum(later.predicted_probabilities.values()) == pytest.approx(1.0)
    assert set(later.emission_log_likelihoods) == set(model.regime_order)
    assert set(later.duration_stay_probabilities) == set(model.regime_order)
    assert later.dominant_regime == "liquidity_shock"


def test_semi_markov_trainer_rejects_state_outside_training_boundary() -> None:
    states, vector, _ = _models()
    with pytest.raises(ValueError, match="boundary"):
        SemiMarkovRegimeTrainer().fit(
            states,
            vector,
            train_start_ns=states[1].timestamp_ns,
            train_end_ns=states[-1].timestamp_ns,
        )


def test_semi_markov_duration_shape_is_fitted_from_variable_regime_runs() -> None:
    assignments = np.asarray([0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1], dtype=int)
    states = tuple(_state(index, min(int(group), 3)) for index, group in enumerate(assignments))
    trainer = SemiMarkovRegimeTrainer(duration_shape=2.0)

    means, shapes = trainer._fit_duration_models(states, assignments)

    assert means[0] > 0
    assert 0.5 <= shapes[0] <= 10.0
    assert shapes[0] != 2.0
