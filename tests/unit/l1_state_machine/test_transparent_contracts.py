from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from l1_microstructure.transparent import (
    EngineArtifactContract,
    EnginePredictionRecord,
    PromotionThresholds,
    TransparentPromotionGate,
    evaluate_prediction_records,
)


def _records(*, accurate: bool, count: int = 100, latency_ns: int = 1_000, memory: int = 10_000):
    values = []
    for index in range(count):
        up = index % 2 == 0
        probability = (0.99 if up else 0.01) if accurate else 0.55
        drift = 3.0 if up else -3.0
        values.append(
            EnginePredictionRecord(
                probability_up=probability,
                realized_drift_bps=drift,
                threshold_bps=1.0,
                edge_seen=index % 5 != 0,
                latency_ns=latency_ns,
                resident_bytes=memory,
            )
        )
    return values


def test_engine_artifact_contract_rejects_incomplete_and_mixed_v2_bundle() -> None:
    contract = EngineArtifactContract.for_version("v2")
    artifact_ids = {kind: f"artifact-{kind}" for kind in contract.required_artifact_types}

    contract.validate_manifest(artifact_ids, {kind: "v2" for kind in artifact_ids})

    with pytest.raises(ValueError, match="incomplete"):
        contract.validate_manifest({"state_calibration": "state"}, {"state_calibration": "v2"})
    versions = {kind: "v2" for kind in artifact_ids}
    versions["utility_model"] = "v1"
    with pytest.raises(ValueError, match="mixed"):
        contract.validate_manifest(artifact_ids, versions)


def test_prediction_evaluation_is_deterministic_and_calibrated() -> None:
    accurate = evaluate_prediction_records(_records(accurate=True))
    weak = evaluate_prediction_records(_records(accurate=False))

    assert accurate.sample_count == 100
    assert accurate.brier_score == pytest.approx(0.0001)
    assert accurate.log_loss < weak.log_loss
    assert accurate.calibration_error < weak.calibration_error
    assert accurate.directional_hit_rate == 1.0
    assert accurate.edge_coverage == 0.8
    assert accurate.mean_signed_net_drift_bps == 2.0


def test_v1_baseline_metrics_match_frozen_golden_snapshot() -> None:
    fixture = Path(__file__).parents[2] / "fixtures" / "transparent_v1_baseline.json"
    expected = json.loads(fixture.read_text(encoding="utf-8"))

    observed = evaluate_prediction_records(_records(accurate=False)).to_dict()

    assert observed == expected


def test_promotion_gate_requires_calibration_economics_and_bounded_cost() -> None:
    baseline = evaluate_prediction_records(_records(accurate=False, latency_ns=1_000, memory=10_000))
    candidate = evaluate_prediction_records(_records(accurate=True, latency_ns=1_100, memory=11_000))
    report = TransparentPromotionGate().evaluate(baseline, candidate)

    assert report.passed is True
    assert all(check.passed for check in report.checks)

    slow = replace(candidate, p95_latency_ns=2_000.0)
    failed = TransparentPromotionGate().evaluate(baseline, slow)
    assert failed.passed is False
    assert next(check for check in failed.checks if check.code == "performance.latency").passed is False


def test_promotion_thresholds_reject_post_hoc_invalid_values() -> None:
    with pytest.raises(ValueError, match="brier"):
        PromotionThresholds(minimum_brier_improvement_fraction=1.0)


def test_directional_evaluation_scores_neutral_outcomes_as_hold_not_sell() -> None:
    neutral = EnginePredictionRecord(
        probability_up=0.1,
        probability_down=0.1,
        realized_drift_bps=0.2,
        threshold_bps=1.0,
        edge_seen=True,
        latency_ns=10,
    )

    evaluation = evaluate_prediction_records((neutral,))

    assert neutral.direction == 0
    assert neutral.probability_neutral == pytest.approx(0.8)
    assert evaluation.mean_signed_net_drift_bps == 0.0
    assert evaluation.brier_score < 0.1

    with pytest.raises(ValueError, match="sum above"):
        replace(neutral, probability_up=0.8, probability_down=0.8)


def test_forecast_quality_is_independent_of_executable_hold_action() -> None:
    record = EnginePredictionRecord(
        probability_up=0.9,
        probability_down=0.05,
        realized_drift_bps=3.0,
        threshold_bps=1.0,
        edge_seen=True,
        latency_ns=10,
        selected_direction=0,
    )

    evaluation = evaluate_prediction_records((record,))

    assert record.forecast_direction == 1
    assert record.direction == 0
    assert evaluation.directional_hit_rate == 1.0
    assert evaluation.mean_signed_net_drift_bps == 0.0
    assert evaluation.decisive_count == 0
    assert evaluation.decision_rate == 0.0
