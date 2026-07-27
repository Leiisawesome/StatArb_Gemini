from __future__ import annotations

from dataclasses import asdict

import pytest

from l1_microstructure.artifacts import ArtifactMetadata, LocalArtifactStore
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.transparent import (
    RobustStateVectorTrainer,
    EngineEvaluation,
    PromotionThresholds,
    TransparentArtifactBundleLoader,
    TransparentArtifactPublisher,
    TransparentArtifactSelector,
    TransparentPromotionGate,
    TransparentModelTrainer,
)

from .test_transparent_training import _calibrations, _state


def _trained_artifacts():
    states = [_state(index) for index in range(40)]
    state_calibration, execution_calibration = _calibrations()
    config = FrameworkConfig()
    config.transition.drift_horizon_ms = 1
    config.transition.drift_horizons_ms = (1, 2, 3)
    artifacts = TransparentModelTrainer(
        vector_trainer=RobustStateVectorTrainer(
            calibration_bins=5,
            transition_probability_threshold=0.15,
        )
    ).fit(
        states,
        state_calibration=state_calibration,
        execution_calibration=execution_calibration,
        train_start_ns=states[0].timestamp_ns,
        train_end_ns=states[-1].timestamp_ns,
        config=config,
    )
    return artifacts


def _validation_report(passed: bool) -> dict[str, object]:
    baseline = EngineEvaluation(2, 0.25, 0.69, 0.10, 0.5, 0.0, -1.0, 100.0, 1_000)
    candidate = EngineEvaluation(2, 0.10, 0.30, 0.05, 1.0, 1.0, 2.0, 100.0, 1_000)
    thresholds = PromotionThresholds(
        minimum_brier_improvement_fraction=0.0,
        maximum_log_loss_ratio=1.0,
        maximum_calibration_error_ratio=1.0,
        minimum_edge_coverage_gain=0.0,
        minimum_net_drift_ratio=0.0,
        maximum_latency_ratio=1.0,
        maximum_memory_ratio=1.0,
        minimum_candidate_samples=2,
    )
    promotion = TransparentPromotionGate(thresholds).evaluate(baseline, candidate)
    return {
        "passed": passed,
        "baseline": baseline.to_dict(),
        "candidate": candidate.to_dict(),
        "promotion": promotion.to_dict(),
        "split_sample_counts": {"one": 1, "two": 1},
        "failures": [] if passed else ["test"],
        "thresholds": asdict(thresholds),
        "opportunity_definition": "union_of_v1_v2_detected_transitions",
    }


def test_v2_artifact_bundle_round_trip_is_validation_bound(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path)
    manifest = TransparentArtifactPublisher(store).publish(
        run_id="run-1",
        trade_date="2026-07-14",
        artifacts=_trained_artifacts(),
        validation_report=_validation_report(True),
        created_at="2026-07-14T00:00:00+00:00",
    )

    loaded = TransparentArtifactBundleLoader(store).load(manifest)
    selected = TransparentArtifactSelector(store).resolve(symbol="AAPL", run_id="run-1")

    assert loaded.symbol == selected.symbol == "AAPL"
    assert loaded.engine_version == "v2"
    assert set(loaded.artifact_ids) == {
        "state_calibration",
        "execution_calibration",
        "state_vector_model",
        "semi_markov_regime_model",
        "hierarchical_transition_model",
        "utility_model",
    }


def test_v2_selector_rejects_model_changed_after_validation(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path)
    manifest = TransparentArtifactPublisher(store).publish(
        run_id="run-2",
        trade_date="2026-07-14",
        artifacts=_trained_artifacts(),
        validation_report=_validation_report(True),
    )
    artifact_id = manifest.artifact_ids["utility_model"]
    metadata = store.load_metadata(artifact_id)
    payload = store.load(artifact_id)
    payload["fixed_cost_bps"] = float(payload["fixed_cost_bps"]) + 1.0
    store.save(metadata, payload)

    assert TransparentArtifactSelector(store).list_manifests("AAPL", passing_only=True) == []
    with pytest.raises(ValueError, match="validation-approved"):
        TransparentArtifactSelector(store).resolve(symbol="AAPL", run_id="run-2")


def test_v2_loader_rejects_mixed_artifact_version_and_duplicate_run(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path)
    publisher = TransparentArtifactPublisher(store)
    artifacts = _trained_artifacts()
    manifest = publisher.publish(
        run_id="run-3",
        trade_date="2026-07-14",
        artifacts=artifacts,
        validation_report=_validation_report(False),
    )
    artifact_id = manifest.artifact_ids["state_vector_model"]
    metadata = store.load_metadata(artifact_id)
    store.save(
        ArtifactMetadata(
            artifact_id=metadata.artifact_id,
            artifact_type=metadata.artifact_type,
            version="v1",
            created_at=metadata.created_at,
            metadata=metadata.metadata,
        ),
        store.load(artifact_id),
    )

    with pytest.raises(ValueError, match="mixed"):
        TransparentArtifactBundleLoader(store).load(manifest)
    with pytest.raises(ValueError, match="immutable"):
        publisher.publish(
            run_id="run-3",
            trade_date="2026-07-14",
            artifacts=artifacts,
            validation_report=_validation_report(True),
        )


def test_v2_publisher_rejects_unsubstantiated_validation_flag(tmp_path) -> None:
    with pytest.raises(ValueError, match="incomplete"):
        TransparentArtifactPublisher(LocalArtifactStore(tmp_path)).publish(
            run_id="forged",
            trade_date="2026-07-14",
            artifacts=_trained_artifacts(),
            validation_report={"passed": True},
        )
