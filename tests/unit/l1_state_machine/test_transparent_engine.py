from __future__ import annotations

from itertools import count

import pytest

from l1_microstructure.artifacts import RuntimeArtifactBundle
from l1_microstructure.events import BookSnapshot, QuoteEvent
from l1_microstructure.features import (
    FlickerState,
    ObservedState,
    PressureState,
    SpreadState,
    VolatilityState,
)
from l1_microstructure.training import TransitionTrainingSample
from l1_microstructure.transparent import (
    ComparativeShadowRunner,
    HierarchicalTransitionTrainer,
    RobustStateVectorTrainer,
    SemiMarkovRegimeTrainer,
    TransparentEngineArtifacts,
    TransparentStatisticalEngine,
    UtilityCalibrationSample,
    UtilityModelTrainer,
)


HORIZONS = (30, 150, 600)


def _state(index: int, group: int) -> ObservedState:
    templates = (
        (0.5, 0.0, 0.0, 2.0, 0.0002),
        (1.0, 0.8, 0.9, 4.0, 0.0008),
        (3.0, -0.5, -0.7, 8.0, 0.0040),
        (0.4, 0.2, -0.2, 10.0, 0.0005),
    )
    spread, quote, trade, flicker, volatility = templates[group]
    timestamp_ns = 1_000 + index * 100
    return ObservedState(
        symbol="AAPL",
        timestamp_ns=timestamp_ns,
        book=BookSnapshot("AAPL", timestamp_ns, 100.0 + index * 0.001, 100.01 + index * 0.001, 100, 100),
        spread_norm=spread + index * 0.001,
        quote_pressure=quote,
        trade_pressure=trade,
        flicker_intensity=flicker,
        realized_volatility=volatility,
        spread_state=SpreadState.NORMAL,
        quote_state=PressureState.NEUTRAL,
        trade_state=PressureState.NEUTRAL,
        flicker_state=FlickerState.COMPETITIVE,
        volatility_state=VolatilityState.NORMAL,
    )


def _artifacts() -> tuple[TransparentEngineArtifacts, list[ObservedState]]:
    states = [_state(index, index // 10) for index in range(40)]
    vector = RobustStateVectorTrainer(
        calibration_bins=5,
        transition_probability_threshold=0.15,
    ).fit(
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
    transition_samples = [
        TransitionTrainingSample(
            symbol="AAPL",
            from_state=states[index - 1].label,
            to_state=states[index].label,
            regime=regime.regime_order[index % len(regime.regime_order)],
            horizon_ns=horizon,
            holding_time_ns=100,
            realized_drift_bps=3.0,
            metadata={"timestamp_ns": states[index].timestamp_ns, "end_timestamp_ns": states[index].timestamp_ns},
        )
        for index in range(1, len(states))
        for horizon in HORIZONS
    ]
    transition = HierarchicalTransitionTrainer(prior_strength=5.0).fit(
        transition_samples,
        train_start_ns=states[0].timestamp_ns,
        train_end_ns=states[-1].timestamp_ns,
    )
    execution_samples = [
        UtilityCalibrationSample(
            timestamp_ns=states[index].timestamp_ns,
            horizon_ns=horizon,
            filled=index % 4 != 0,
            alignment_probability=0.9 if index % 4 != 0 else 0.2,
            spread_bps=1.0,
            slippage_bps=0.2,
        )
        for index in range(1, len(states))
        for horizon in HORIZONS
    ]
    utility = UtilityModelTrainer(
        fixed_cost_bps=0.2,
        uncertainty_penalty_multiplier=0.1,
    ).fit(
        execution_samples,
        symbol="AAPL",
        train_start_ns=states[0].timestamp_ns,
        train_end_ns=states[-1].timestamp_ns,
    )
    return TransparentEngineArtifacts(vector, regime, transition, utility), states


def test_transparent_engine_integrates_transition_horizons_and_online_outcomes() -> None:
    artifacts, states = _artifacts()
    engine = TransparentStatisticalEngine(artifacts)

    first = engine.on_state(states[0])
    transition = engine.on_state(states[20])
    resolved = engine.on_state(_state(40, 2))

    assert first.transition.is_transition is False
    assert transition.transition.is_transition is True
    assert {posterior.horizon_ns for posterior in transition.posteriors} == set(HORIZONS)
    assert transition.decision is not None
    assert transition.shadow_only is True
    assert resolved.resolved_outcomes
    assert all(outcome.horizon_ns in HORIZONS for outcome in resolved.resolved_outcomes)


def test_transparent_engine_ignores_late_events_before_mutating_features() -> None:
    artifacts, _ = _artifacts()
    engine = TransparentStatisticalEngine(artifacts)
    latest = QuoteEvent("AAPL", 2_000, 100.0, 100.01, 100, 100)
    late = QuoteEvent("AAPL", 1_900, 99.0, 99.01, 100, 100)

    first = engine.on_event(latest)
    assert first is not None
    original_book = engine.feature_engine.current_book

    assert engine.on_event(late) is None
    assert engine.previous_state is first.state
    assert engine.feature_engine.current_book is original_book
    assert engine.late_event_count == 1


def test_transparent_engine_outcome_recovery_validates_horizons() -> None:
    artifacts, states = _artifacts()
    engine = TransparentStatisticalEngine(artifacts)
    engine.on_state(states[0])
    engine.on_state(states[20])
    snapshot = engine.snapshot_outcomes()

    recovered = TransparentStatisticalEngine(artifacts)
    recovered.restore_outcomes(snapshot)
    assert recovered.snapshot_outcomes() == snapshot

    snapshot["horizons_ns"] = [999]
    with pytest.raises(ValueError, match="unsupported outcome horizon|do not match"):
        recovered.restore_outcomes(snapshot)


def test_comparative_shadow_runner_uses_isolated_engines_and_deterministic_clock(monkeypatch) -> None:
    artifacts, _ = _artifacts()
    ticks = count(start=0, step=100)
    runner = ComparativeShadowRunner(
        baseline_artifacts=RuntimeArtifactBundle(),
        candidate_artifacts=artifacts,
        clock=lambda: next(ticks),
    )
    events = [QuoteEvent("AAPL", 1_000 + index * 100, 100.0 + index * 0.01, 100.01 + index * 0.01, 100, 100) for index in range(12)]

    report = runner.run(events)

    assert report.baseline_update_count == len(events)
    assert report.candidate_update_count == len(events)
    assert report.candidate_error_count == 0
    assert report.comparison_count == len(events)
    assert report.comparison_sampling_stride == 1
    assert report.baseline_p95_latency_ns == 100
    assert report.candidate_p95_latency_ns == 100
    assert runner.baseline.feature_engine is not runner.candidate.feature_engine

    failing_runner = ComparativeShadowRunner(
        baseline_artifacts=RuntimeArtifactBundle(),
        candidate_artifacts=artifacts,
        clock=lambda: next(ticks),
    )
    monkeypatch.setattr(failing_runner.candidate, "on_event", lambda _event: (_ for _ in ()).throw(ValueError()))
    failed = failing_runner.run(events[:2])
    assert failed.baseline_update_count == 2
    assert failed.candidate_error_count == 2


def test_comparative_shadow_runner_bounds_serialized_comparisons() -> None:
    artifacts, _ = _artifacts()
    ticks = count(start=0, step=100)
    runner = ComparativeShadowRunner(
        baseline_artifacts=RuntimeArtifactBundle(),
        candidate_artifacts=artifacts,
        clock=lambda: next(ticks),
        max_comparisons=4,
    )
    events = [
        QuoteEvent(
            "AAPL",
            1_000 + index * 100,
            100.0 + index * 0.01,
            100.01 + index * 0.01,
            100,
            100,
        )
        for index in range(20)
    ]

    report = runner.run(events)

    assert report.comparison_count == len(events)
    assert len(report.comparisons) <= 4
    assert report.comparison_sampling_stride > 1
    assert len(report.to_dict()["comparisons"]) <= 4
