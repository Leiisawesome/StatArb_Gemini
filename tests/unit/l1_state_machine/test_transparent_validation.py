from __future__ import annotations

from dataclasses import replace

import pytest

from l1_microstructure.calibration.interfaces import ExecutionCalibrationArtifact
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.training import TransitionTrainingSample
from l1_microstructure.transparent import (
    HierarchicalTransitionRuntime,
    HierarchicalTransitionTrainer,
    PromotionThresholds,
    TransparentOOSValidator,
    UtilityModel,
    ValidationSplitEvidence,
)
from l1_microstructure.transparent.utility import ExpectedUtilityDecisionEngine
from l1_microstructure.decision import TradeAction


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
        minimum_candidate_decisions=1,
        minimum_candidate_decision_rate=0.0,
        minimum_decision_hit_rate=0.0,
        minimum_mean_decision_net_drift_bps=-10.0,
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
        slippage_bps_by_horizon={"5": 0.25, "10": 0.25},
        fill_multiplier_by_regime={},
        slippage_multiplier_by_regime={},
        fixed_cost_bps=0.75,
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
    assert report.candidate.mean_decision_net_drift_bps == 4.0


def _high_variance_training(*, mean_bps: float = 8.5, std_bps: float = 12.0, count: int = 80):
    """Train edges whose hierarchical predictive std is large relative to cost."""
    samples: list[TransitionTrainingSample] = []
    for index in range(count):
        # Alternate high/low around a strong mean so predictive std stays large.
        noise = std_bps if index % 2 == 0 else -std_bps
        samples.append(_sample(index, drift=mean_bps + noise))
    return samples


def _production_utility_from_execution_calibration(
    horizons_ns: tuple[int, ...] = (5,),
    *,
    fixed_cost_bps: float = 1.2,
) -> UtilityModel:
    """Build utility exactly as production training does (no zeroed penalties)."""
    calibration = ExecutionCalibrationArtifact(
        symbol="AAPL",
        fill_probability_intercept=2.0,
        alignment_weight=1.0,
        spread_penalty=0.05,
        slippage_intercept_bps=0.4,
        spread_slippage_weight=0.0,
        adverse_selection_weight=0.0,
        regime_fill_multipliers={"calm": 1.0},
        regime_slippage_multipliers={"calm": 1.0},
        metadata={"method": "unit_production_adapter", "row_count": 100, "transition_row_count": 100},
    )
    return UtilityModel.from_execution_calibration(
        calibration,
        horizons_ns,
        train_start_ns=1_000,
        train_end_ns=2_000,
        fixed_cost_bps=fixed_cost_bps,
    )


def _opportunity_samples(
    start_timestamp_ns: int,
    count: int,
    *,
    drift: float,
    session_date: str,
    step_ns: int = 10,
) -> tuple[TransitionTrainingSample, ...]:
    samples: list[TransitionTrainingSample] = []
    for offset in range(count):
        timestamp = start_timestamp_ns + offset * step_ns
        samples.append(
            TransitionTrainingSample(
                symbol="AAPL",
                from_state="a",
                to_state="b",
                regime="calm",
                horizon_ns=5,
                holding_time_ns=10,
                realized_drift_bps=drift,
                metadata={
                    "timestamp_ns": timestamp,
                    "end_timestamp_ns": timestamp + 5,
                    "opportunity_index": timestamp,
                    "candidate_detected": True,
                    "candidate_transition_probability": 0.95,
                    "spread_bps": 1.0,
                    "session_date": session_date,
                },
            )
        )
    return tuple(samples)


def _actionability_thresholds(**overrides: float | int) -> PromotionThresholds:
    base = dict(
        minimum_brier_improvement_fraction=0.0,
        maximum_log_loss_ratio=10.0,
        maximum_calibration_error_ratio=10.0,
        minimum_directional_hit_rate_ratio=0.0,
        minimum_edge_coverage_gain=-1.0,
        minimum_net_drift_ratio=0.0,
        maximum_latency_ratio=10.0,
        maximum_memory_ratio=1_000.0,
        minimum_candidate_samples=100,
        minimum_candidate_decisions=100,
        minimum_candidate_decision_rate=0.0001,
        minimum_decision_hit_rate=0.52,
        minimum_mean_decision_net_drift_bps=0.0,
    )
    base.update(overrides)
    return PromotionThresholds(**base)


def test_multi_session_oos_actionability_clears_promotion_floors() -> None:
    """Production utility defaults clear multi-session floors; full-std path HOLDs."""
    model = HierarchicalTransitionTrainer(prior_strength=1.0).fit(
        _high_variance_training(),
        train_start_ns=1_000,
        train_end_ns=1_800,
    )
    production_utility = _production_utility_from_execution_calibration()
    assert production_utility.uncertainty_penalty_multiplier == pytest.approx(0.25)
    assert production_utility.risk_penalty_bps == pytest.approx(1.0)

    # Probe: large predictive std makes full-std (legacy) HOLD and fractional ACT.
    posterior = HierarchicalTransitionRuntime(model).posterior(
        from_state="a",
        to_state="b",
        regime="calm",
        horizon_ns=5,
        threshold_bps=1.2,
    )
    assert posterior.std_bps > 5.0
    assert posterior.mean_bps > production_utility.fixed_cost_bps
    production_decision = ExpectedUtilityDecisionEngine(production_utility).decide_for_spread(
        (posterior,),
        spread_bps=1.0,
        alignment_probability=1.0,
        transition_probability=0.95,
        current_risk_fraction=0.0,
        regime="calm",
    )
    legacy_decision = ExpectedUtilityDecisionEngine(
        replace(
            production_utility,
            uncertainty_penalty_multiplier=1.0,
            risk_penalty_bps=2.0,
        )
    ).decide_for_spread(
        (posterior,),
        spread_bps=1.0,
        alignment_probability=1.0,
        transition_probability=0.95,
        current_risk_fraction=0.0,
        regime="calm",
    )
    assert production_decision.action is TradeAction.BUY
    assert legacy_decision.action is TradeAction.HOLD

    # Two complete held-out sessions; realized drift stays net-positive after cost.
    split_one = ValidationSplitEvidence(
        "expanding-2026-07-21",
        2_000,
        4_000,
        _opportunity_samples(2_000, 80, drift=5.0, session_date="2026-07-21"),
    )
    split_two = ValidationSplitEvidence(
        "expanding-2026-07-22",
        5_000,
        7_000,
        _opportunity_samples(5_000, 80, drift=5.0, session_date="2026-07-22"),
    )
    thresholds = _actionability_thresholds()

    report = TransparentOOSValidator(thresholds, minimum_split_count=2, clock=_clock()).evaluate(
        baseline_transition_payload={"horizon_models": {}},
        candidate_model=model,
        candidate_utility_model=production_utility,
        splits=(split_one, split_two),
    )

    assert report.candidate.decisive_count > 1
    assert report.candidate.decisive_count >= thresholds.minimum_candidate_decisions
    assert report.candidate.decision_rate >= thresholds.minimum_candidate_decision_rate
    assert report.candidate.mean_decision_net_drift_bps >= (
        thresholds.minimum_mean_decision_net_drift_bps
    )
    assert report.candidate.decision_hit_rate >= thresholds.minimum_decision_hit_rate
    assert "decisions.minimum" not in report.failures
    assert "decisions.rate" not in report.failures
    assert "economics.decision_net_drift" not in report.failures

    # Same multi-session OOS path with legacy full-std adapter defaults stays inert.
    legacy_report = TransparentOOSValidator(
        thresholds, minimum_split_count=2, clock=_clock()
    ).evaluate(
        baseline_transition_payload={"horizon_models": {}},
        candidate_model=model,
        candidate_utility_model=replace(
            production_utility,
            uncertainty_penalty_multiplier=1.0,
            risk_penalty_bps=2.0,
        ),
        splits=(split_one, split_two),
    )
    assert legacy_report.candidate.decisive_count == 0
    assert "decisions.minimum" in legacy_report.failures


def test_oos_actionability_gates_fail_closed_for_inert_and_lossy_candidates() -> None:
    model = HierarchicalTransitionTrainer(prior_strength=1.0).fit(
        _high_variance_training(count=60),
        train_start_ns=1_000,
        train_end_ns=1_600,
    )
    production_utility = _production_utility_from_execution_calibration()
    splits = (
        ValidationSplitEvidence(
            "expanding-day-a",
            2_000,
            4_000,
            _opportunity_samples(2_000, 60, drift=5.0, session_date="2026-07-21"),
        ),
        ValidationSplitEvidence(
            "expanding-day-b",
            5_000,
            7_000,
            _opportunity_samples(5_000, 60, drift=5.0, session_date="2026-07-22"),
        ),
    )
    thresholds = _actionability_thresholds(minimum_candidate_samples=10)

    # Legacy full-std production adapter path → chronic HOLD (pre-fix defaults).
    inert = TransparentOOSValidator(thresholds, minimum_split_count=2, clock=_clock()).evaluate(
        baseline_transition_payload={"horizon_models": {}},
        candidate_model=model,
        candidate_utility_model=replace(
            production_utility,
            uncertainty_penalty_multiplier=1.0,
            risk_penalty_bps=2.0,
        ),
        splits=splits,
    )
    assert not inert.passed
    assert "decisions.minimum" in inert.failures
    assert "decisions.rate" in inert.failures
    assert inert.candidate.decisive_count == 0

    # Production utility acts, but realized drift is negative after cost.
    lossy = TransparentOOSValidator(thresholds, minimum_split_count=2, clock=_clock()).evaluate(
        baseline_transition_payload={"horizon_models": {}},
        candidate_model=model,
        candidate_utility_model=production_utility,
        splits=(
            ValidationSplitEvidence(
                "expanding-day-a",
                2_000,
                4_000,
                _opportunity_samples(2_000, 60, drift=-3.0, session_date="2026-07-21"),
            ),
            ValidationSplitEvidence(
                "expanding-day-b",
                5_000,
                7_000,
                _opportunity_samples(5_000, 60, drift=-3.0, session_date="2026-07-22"),
            ),
        ),
    )
    assert not lossy.passed
    assert lossy.candidate.decisive_count >= thresholds.minimum_candidate_decisions
    assert lossy.candidate.mean_decision_net_drift_bps < (
        thresholds.minimum_mean_decision_net_drift_bps
    )
    assert "economics.decision_net_drift" in lossy.failures
