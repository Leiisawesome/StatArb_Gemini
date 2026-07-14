from __future__ import annotations

from dataclasses import replace

import pytest

from l1_microstructure.training import TransitionTrainingSample
from l1_microstructure.transparent import (
    HierarchicalTransitionModel,
    HierarchicalTransitionRuntime,
    HierarchicalTransitionTrainer,
)


def _sample(
    index: int,
    *,
    to_state: str,
    drift: float,
    horizon_ns: int = 3_000_000_000,
) -> TransitionTrainingSample:
    timestamp_ns = 1_000_000_000 + index * 1_000_000
    return TransitionTrainingSample(
        symbol="AAPL",
        from_state="normal",
        to_state=to_state,
        regime="execution_flow",
        horizon_ns=horizon_ns,
        holding_time_ns=1_000_000,
        realized_drift_bps=drift,
        metadata={"timestamp_ns": timestamp_ns, "end_timestamp_ns": timestamp_ns + 500_000},
    )


def _model(max_edges: int = 10) -> HierarchicalTransitionModel:
    samples = [
        *[_sample(index, to_state="up", drift=3.0 + index * 0.01) for index in range(30)],
        *[_sample(100 + index, to_state="rare", drift=-2.0) for index in range(2)],
        *[
            _sample(200 + index, to_state="up", drift=4.0, horizon_ns=15_000_000_000)
            for index in range(5)
        ],
    ]
    return HierarchicalTransitionTrainer(
        prior_strength=5.0,
        online_decay=0.99,
        max_exact_edges_per_horizon=max_edges,
    ).fit(
        samples,
        train_start_ns=1_000_000_000,
        train_end_ns=2_000_000_000,
    )


def test_hierarchical_transition_model_round_trips_without_raw_samples() -> None:
    model = _model()
    restored = HierarchicalTransitionModel.from_dict(model.to_dict())

    assert restored.to_dict() == model.to_dict()
    assert set(restored.horizons_ns) == {3_000_000_000, 15_000_000_000}
    assert "drift_samples_bps" not in str(restored.to_dict())


def test_sparse_edge_backs_off_and_reports_hierarchical_support() -> None:
    runtime = HierarchicalTransitionRuntime(_model())
    exact = runtime.posterior(
        from_state="normal",
        to_state="up",
        regime="execution_flow",
        horizon_ns=3_000_000_000,
        threshold_bps=1.0,
    )
    unseen = runtime.posterior(
        from_state="normal",
        to_state="unseen",
        regime="execution_flow",
        horizon_ns=3_000_000_000,
        threshold_bps=1.0,
    )

    assert exact.exact_edge_seen is True
    assert exact.probability_up > 0.5
    assert exact.support["exact_edge"] > 0.0
    assert unseen.exact_edge_seen is False
    assert unseen.support["from_state"] > 0.0
    assert sum(unseen.support.values()) == pytest.approx(1.0)


def test_exact_edge_memory_is_bounded_and_unseen_updates_only_parents() -> None:
    model = _model(max_edges=1)
    horizon = str(3_000_000_000)
    runtime = HierarchicalTransitionRuntime(model)
    exact_before = len(model.statistics[horizon]["edge"])
    parent_before = model.statistics[horizon]["global"]["*"].effective_count

    runtime.observe(
        from_state="normal",
        to_state="never-retained",
        regime="execution_flow",
        horizon_ns=3_000_000_000,
        drift_bps=8.0,
        holding_time_ns=10,
    )

    assert len(model.statistics[horizon]["edge"]) == exact_before == 1
    assert model.statistics[horizon]["global"]["*"].effective_count > parent_before


def test_hierarchical_trainer_rejects_outcome_after_training_boundary() -> None:
    sample = _sample(0, to_state="up", drift=2.0)
    sample = replace(
        sample,
        metadata={"timestamp_ns": 1_000_000_000, "end_timestamp_ns": 3_000_000_000},
    )
    with pytest.raises(ValueError, match="resolves after"):
        HierarchicalTransitionTrainer().fit(
            [sample],
            train_start_ns=1_000_000_000,
            train_end_ns=2_000_000_000,
        )


def test_hierarchical_posterior_retains_predictive_uncertainty_for_repeated_outcomes() -> None:
    samples = [_sample(index, to_state="up", drift=3.0) for index in range(8)]
    model = HierarchicalTransitionTrainer(variance_floor_bps2=0.25).fit(
        samples,
        train_start_ns=1_000_000_000,
        train_end_ns=2_000_000_000,
    )

    posterior = HierarchicalTransitionRuntime(model).posterior(
        from_state="normal",
        to_state="up",
        regime="execution_flow",
        horizon_ns=3_000_000_000,
        threshold_bps=1.0,
    )

    assert posterior.std_bps >= 0.5
    assert posterior.probability_up < 1.0
