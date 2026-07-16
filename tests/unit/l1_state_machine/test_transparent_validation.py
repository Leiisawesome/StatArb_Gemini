from __future__ import annotations

from dataclasses import replace

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.training import TransitionTrainingSample
from l1_microstructure.transparent import (
    HierarchicalTransitionTrainer,
    PromotionThresholds,
    TransparentOOSValidator,
    UtilityModel,
    ValidationSplitEvidence,
)


def _sample(index: int, *, drift: float = 5.0) -> TransitionTrainingSample:
    timestamp = 1_000 + index * 10
    return TransitionTrainingSample(
        symbol="AAPL",
        from_state="a",
        to_state="b",
        regime="calm",
        horizon_ns=5,
        holding_time_ns=10,
        realized_drift_bps=drift,
        metadata={"timestamp_ns": timestamp, "end_timestamp_ns": timestamp + 5},
    )


def _clock():
    values = iter(range(0, 10_000, 10))
    return lambda: next(values)


def test_oos_validator_compares_identical_resolved_samples_and_passes_fixed_gate() -> None:
    model = HierarchicalTransitionTrainer(prior_strength=1.0).fit(
        [_sample(index) for index in range(8)],
        train_start_ns=1_000,
        train_end_ns=1_075,
    )
    splits = (
        ValidationSplitEvidence("one", 2_000, 2_100, tuple(_sample(100 + index) for index in range(3))),
        ValidationSplitEvidence("two", 3_000, 3_100, tuple(_sample(200 + index) for index in range(3))),
    )
    thresholds = PromotionThresholds(
        minimum_brier_improvement_fraction=0.01,
        maximum_log_loss_ratio=1.0,
        maximum_calibration_error_ratio=1.0,
        minimum_edge_coverage_gain=0.0,
        minimum_net_drift_ratio=0.0,
        maximum_latency_ratio=1.0,
        maximum_memory_ratio=1_000.0,
        minimum_candidate_samples=6,
    )
    baseline = {"horizon_models": {"5": {"edges": {}}}}

    report = TransparentOOSValidator(thresholds, clock=_clock()).evaluate(
        baseline_transition_payload=baseline,
        candidate_model=model,
        splits=splits,
        config=FrameworkConfig(),
    )

    assert report.passed
    assert report.baseline.sample_count == report.candidate.sample_count == 6
    assert report.candidate.brier_score < report.baseline.brier_score
    assert report.candidate.edge_coverage > report.baseline.edge_coverage


def test_oos_validator_fails_closed_on_insufficient_splits() -> None:
    model = HierarchicalTransitionTrainer(prior_strength=1.0).fit(
        [_sample(index) for index in range(8)],
        train_start_ns=1_000,
        train_end_ns=1_075,
    )
    split = ValidationSplitEvidence("only", 2_000, 2_100, tuple(_sample(100 + index) for index in range(3)))
    thresholds = PromotionThresholds(
        minimum_brier_improvement_fraction=0.0,
        maximum_calibration_error_ratio=2.0,
        maximum_memory_ratio=1_000.0,
        minimum_candidate_samples=3,
    )

    report = TransparentOOSValidator(thresholds, minimum_split_count=2, clock=_clock()).evaluate(
        baseline_transition_payload={"horizon_models": {"5": {"edges": {}}}},
        candidate_model=model,
        splits=(split,),
    )

    assert not report.passed
    assert "requires 2 splits" in report.failures[0]


def test_validation_split_rejects_label_resolved_after_test_boundary() -> None:
    sample = _sample(100)
    try:
        ValidationSplitEvidence("leaky", 2_000, 2_002, (sample,))
    except ValueError as exc:
        assert "crosses" in str(exc)
    else:
        raise AssertionError("expected held-out boundary rejection")


def test_oos_validator_uses_hierarchical_fallback_when_candidate_did_not_detect() -> None:
    model = HierarchicalTransitionTrainer(prior_strength=1.0).fit(
        [_sample(index) for index in range(8)],
        train_start_ns=1_000,
        train_end_ns=1_075,
    )
    sample = _sample(100)
    sample = replace(
        sample,
        metadata={
            **sample.metadata,
            "candidate_detected": False,
            "baseline_detected": True,
        },
    )
    report = TransparentOOSValidator(
        PromotionThresholds(
            minimum_brier_improvement_fraction=0.0,
            maximum_log_loss_ratio=1.0,
            maximum_calibration_error_ratio=1.0,
            minimum_edge_coverage_gain=0.0,
            minimum_net_drift_ratio=0.0,
            maximum_latency_ratio=10.0,
            maximum_memory_ratio=1_000.0,
            minimum_candidate_samples=1,
        ),
        minimum_split_count=1,
        clock=_clock(),
    ).evaluate(
        baseline_transition_payload={"horizon_models": {"5": {"edges": {}}}},
        candidate_model=model,
        splits=(ValidationSplitEvidence("one", 2_000, 2_100, (sample,)),),
    )

    assert report.candidate.edge_coverage == 1.0
    assert report.candidate.brier_score < report.baseline.brier_score


def test_oos_validator_makes_one_runtime_equivalent_utility_choice_across_horizons() -> None:
    short_horizon_training = [_sample(index) for index in range(8)]
    training = short_horizon_training + [
        replace(sample, horizon_ns=10) for sample in short_horizon_training
    ]
    model = HierarchicalTransitionTrainer(prior_strength=1.0).fit(
        training,
        train_start_ns=1_000,
        train_end_ns=1_100,
    )
    utility = UtilityModel(
        symbol="AAPL",
        fill_intercept=10.0,
        fill_alignment_weight=0.0,
        fill_spread_penalty=0.0,
        slippage_bps_by_horizon={"5": 0.0, "10": 0.0},
        fill_multiplier_by_regime={},
        slippage_multiplier_by_regime={},
        fixed_cost_bps=0.0,
        uncertainty_penalty_multiplier=0.0,
        risk_penalty_bps=0.0,
        minimum_expected_utility_bps=0.0,
        train_start_ns=1_000,
        train_end_ns=1_100,
        sample_count=8,
    )
    first = replace(
        _sample(100),
        metadata={
            **_sample(100).metadata,
            "opportunity_index": 100,
            "candidate_detected": True,
            "candidate_transition_probability": 0.9,
            "spread_bps": 1.0,
        },
    )
    second = replace(
        first,
        horizon_ns=10,
        metadata={**first.metadata, "end_timestamp_ns": 2_020},
    )

    report = TransparentOOSValidator(
        PromotionThresholds(minimum_candidate_samples=1),
        minimum_split_count=1,
        clock=_clock(),
    ).evaluate(
        baseline_transition_payload={"horizon_models": {}},
        candidate_model=model,
        candidate_utility_model=utility,
        splits=(ValidationSplitEvidence("one", 2_000, 2_100, (first, second)),),
    )

    assert report.candidate.decisive_count == 1
    assert report.candidate.decision_rate == 0.5
