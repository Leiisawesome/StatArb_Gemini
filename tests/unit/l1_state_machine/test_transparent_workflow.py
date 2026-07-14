from __future__ import annotations

from dataclasses import replace

import pytest

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.events import QuoteEvent
from l1_microstructure.transparent import (
    PromotionThresholds,
    RobustStateVectorTrainer,
    TransparentArtifactDrivenWorkflow,
    TransparentArtifactSelector,
    TransparentModelTrainer,
    build_common_opportunity_samples,
)
from l1_microstructure.validation import RegimeSplitSpec


def _events(count: int = 180) -> list[QuoteEvent]:
    events = []
    start = 1_700_000_000_000_000_000
    for index in range(count):
        phase = (index // 12) % 4
        midpoint = 100.0 + phase * 0.03 + (index % 5) * 0.002
        spread = (0.01, 0.02, 0.05, 0.015)[phase]
        events.append(
            QuoteEvent(
                symbol="AAPL",
                timestamp_ns=start + index * 1_000_000,
                bid_price=midpoint - spread / 2.0,
                ask_price=midpoint + spread / 2.0,
                bid_size=100 + (index % 7) * 20 + phase * 30,
                ask_size=260 - (index % 6) * 20 + (3 - phase) * 10,
                sequence_number=index,
            )
        )
    return events


def _iso(timestamp_ns: int) -> str:
    import pandas as pd

    return pd.Timestamp(timestamp_ns, unit="ns", tz="UTC").isoformat()


def test_v2_workflow_resets_each_window_and_publishes_fail_closed_bundle(tmp_path) -> None:
    events = _events()
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.05
    config.transition.drift_horizon_ms = 1
    config.transition.drift_horizons_ms = (1, 2, 3)
    trainer = TransparentModelTrainer(
        vector_trainer=RobustStateVectorTrainer(
            calibration_bins=8,
            transition_probability_threshold=0.01,
        )
    )
    splits = [
        RegimeSplitSpec(
            _iso(events[0].timestamp_ns),
            _iso(events[79].timestamp_ns),
            _iso(events[80].timestamp_ns),
            _iso(events[119].timestamp_ns),
            "early",
        ),
        RegimeSplitSpec(
            _iso(events[20].timestamp_ns),
            _iso(events[119].timestamp_ns),
            _iso(events[120].timestamp_ns),
            _iso(events[159].timestamp_ns),
            "late",
        ),
    ]
    workflow = TransparentArtifactDrivenWorkflow(
        tmp_path,
        framework_config=config,
        model_trainer=trainer,
        promotion_thresholds=PromotionThresholds(
            minimum_brier_improvement_fraction=0.0,
            maximum_log_loss_ratio=10.0,
            maximum_calibration_error_ratio=10.0,
            minimum_net_drift_ratio=0.0,
            maximum_latency_ratio=100.0,
            maximum_memory_ratio=100.0,
            minimum_candidate_samples=2,
        ),
    )

    result = workflow.run(symbol="AAPL", events=events, splits=splits, run_id="workflow-v2")

    assert result.split_count == 2
    assert result.artifacts.metadata["train_start_ns"] == events[0].timestamp_ns
    assert result.artifacts.metadata["train_end_ns"] == events[-1].timestamp_ns
    assert result.validation_report.split_sample_counts.keys() == {"early", "late"}
    manifests = TransparentArtifactSelector(workflow.store).list_manifests("AAPL")
    assert [manifest.run_id for manifest in manifests] == ["workflow-v2"]
    if result.validation_report.passed:
        assert TransparentArtifactSelector(workflow.store).resolve(
            symbol="AAPL", run_id="workflow-v2"
        ).symbol == "AAPL"
    else:
        with pytest.raises(ValueError, match="validation-approved"):
            TransparentArtifactSelector(workflow.store).resolve(symbol="AAPL", run_id="workflow-v2")


def test_v2_workflow_rejects_overlapping_train_and_test(tmp_path) -> None:
    events = _events(40)
    split = RegimeSplitSpec(
        _iso(events[0].timestamp_ns),
        _iso(events[20].timestamp_ns),
        _iso(events[20].timestamp_ns),
        _iso(events[-1].timestamp_ns),
        "overlap",
    )

    with pytest.raises(ValueError, match="overlaps"):
        TransparentArtifactDrivenWorkflow(tmp_path).run(
            symbol="AAPL", events=events, splits=[split], run_id="bad"
        )


def test_common_oos_opportunities_include_baseline_only_detections(tmp_path) -> None:
    events = _events()
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.05
    config.transition.drift_horizon_ms = 1
    config.transition.drift_horizons_ms = (1, 2, 3)
    workflow = TransparentArtifactDrivenWorkflow(
        tmp_path,
        framework_config=config,
        model_trainer=TransparentModelTrainer(
            vector_trainer=RobustStateVectorTrainer(
                calibration_bins=8,
                transition_probability_threshold=0.01,
            )
        ),
    )
    fitted = workflow._fit_window(
        symbol="AAPL",
        events=events[:100],
        train_start_ns=events[0].timestamp_ns,
        train_end_ns=events[99].timestamp_ns,
    )
    test_states = workflow._states(events[100:150], fitted.candidate.state_calibration)
    suppressed_candidate = replace(
        fitted.candidate.state_vector_model,
        transition_probability_threshold=0.999999,
    )

    samples = build_common_opportunity_samples(
        test_states,
        candidate_vector_model=suppressed_candidate,
        candidate_regime_model=fitted.candidate.semi_markov_regime_model,
        baseline_regime_calibration=fitted.baseline.regime_calibration,
        baseline_transition_payload=fitted.baseline_transition_payload,
        config=config,
    )

    assert samples
    assert any(
        sample.metadata["baseline_detected"] and not sample.metadata["candidate_detected"]
        for sample in samples
    )
    assert all(
        sample.metadata["baseline_detected"] or sample.metadata["candidate_detected"]
        for sample in samples
    )
