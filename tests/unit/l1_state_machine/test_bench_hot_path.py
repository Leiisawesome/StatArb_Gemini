"""Hot-path bench harness drives shipped engine entry points."""

from __future__ import annotations

from l1_microstructure.bench_hot_path import (
    bench_build_panels,
    bench_on_event,
    make_synthetic_events,
    run_suite,
)
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import DecisionEngine
from l1_microstructure.pipeline import L1MicrostructureStateMachine
from l1_microstructure.regime import MicrostructureRegime
from l1_microstructure.transitions import EdgeKey, EdgeStatistics, TransitionKernel


def test_synthetic_fixture_is_deterministic() -> None:
    first = make_synthetic_events(count=100)
    second = make_synthetic_events(count=100)
    assert len(first) == 100
    assert [type(event).__name__ for event in first] == [type(event).__name__ for event in second]
    assert [event.timestamp_ns for event in first] == [event.timestamp_ns for event in second]


def test_on_event_bench_drives_shipped_state_machine() -> None:
    events = make_synthetic_events(count=500)
    result = bench_on_event(events, measure_per_event=False)
    assert result.name == "on_event"
    assert result.event_count == 500
    assert result.updates > 0
    assert result.wall_seconds > 0.0
    assert result.events_per_second > 0.0


def test_build_panels_bench_drives_shipped_dataset_builder() -> None:
    events = make_synthetic_events(count=400)
    result = bench_build_panels(events)
    assert result.name == "build_panels_single_pass"
    assert result.event_count == 400
    assert result.updates > 0
    assert result.wall_seconds > 0.0


def test_run_suite_returns_both_hot_paths() -> None:
    payload = run_suite(event_count=300)
    assert payload["event_count"] == 300
    assert payload["on_event"]["updates"] > 0
    assert payload["build_panels_single_pass"]["wall_seconds"] > 0.0


def test_edge_snr_matches_welford_for_raw_drift_samples() -> None:
    stats = EdgeStatistics()
    for value in (1.0, 2.0, 3.0, 4.0, 5.0):
        stats.record_drift(value)
    # Pure-Python SNR must agree with sample mean/std of the drift series.
    mean = sum(stats.drift_samples_bps) / len(stats.drift_samples_bps)
    var = sum((value - mean) ** 2 for value in stats.drift_samples_bps) / (len(stats.drift_samples_bps) - 1)
    expected = abs(mean) / (var**0.5)
    assert abs(stats.signal_to_noise - expected) < 1e-12
    assert abs(stats.decision_drift_mean_bps - mean) < 1e-12


def test_posterior_pure_python_matches_prior_path_shape() -> None:
    config = FrameworkConfig()
    engine = DecisionEngine(config.decision, config.transition)
    samples = [1.5, 2.0, 1.0, 2.5, 1.8]
    posterior = engine.estimate_posterior(samples, threshold_bps=1.0)
    assert posterior.sample_count == 5
    assert posterior.mean_bps > 0.0
    assert posterior.std_bps > 0.0
    assert 0.0 <= posterior.probability_up <= 1.0


def test_cached_observed_state_vector_stable_across_reads() -> None:
    machine = L1MicrostructureStateMachine(FrameworkConfig())
    events = make_synthetic_events(count=20)
    last = None
    for event in events:
        update = machine.on_event(event)
        if update is not None:
            last = update.state
    assert last is not None
    first = last.vector
    second = last.vector
    assert first is second  # cached array identity
    assert last.label == last.label
