from __future__ import annotations

import pandas as pd

from l1_microstructure.validation import RegimeSplitSpec, RollingValidationHarness


def test_rolling_validation_harness_passes_on_stable_split() -> None:
    dataset = pd.DataFrame(
        [
            {"timestamp": "2024-01-02T14:30:00Z", "from_state": "s1", "to_state": "s2", "regime": "execution_flow", "realized_drift_bps": 1.2},
            {"timestamp": "2024-01-02T14:31:00Z", "from_state": "s1", "to_state": "s2", "regime": "execution_flow", "realized_drift_bps": 1.5},
            {"timestamp": "2024-01-02T14:32:00Z", "from_state": "s2", "to_state": "s3", "regime": "calm_liquidity", "realized_drift_bps": 0.8},
            {"timestamp": "2024-01-03T14:30:00Z", "from_state": "s1", "to_state": "s2", "regime": "execution_flow", "realized_drift_bps": 1.0},
            {"timestamp": "2024-01-03T14:31:00Z", "from_state": "s2", "to_state": "s3", "regime": "calm_liquidity", "realized_drift_bps": 0.7},
        ]
    )
    execution_frame = pd.DataFrame(
        [
            {
                "timestamp": "2024-01-03T14:30:00Z",
                "fill_rate": 0.75,
                "cancel_rate": 0.10,
                "expected_drift_bps": 1.1,
                "realized_drift_bps": 1.0,
                "kill_switch_active": False,
            },
            {
                "timestamp": "2024-01-03T14:31:00Z",
                "fill_rate": 0.80,
                "cancel_rate": 0.05,
                "expected_drift_bps": 0.8,
                "realized_drift_bps": 0.7,
                "kill_switch_active": False,
            },
        ]
    )
    harness = RollingValidationHarness(
        minimum_test_rows=2,
        minimum_regime_coverage=1.0,
        minimum_hit_rate=0.5,
        minimum_directional_test_rows=2,
        minimum_decay_ratio=0.5,
        minimum_fill_rate=0.5,
        maximum_cancel_rate=0.5,
        maximum_drift_tracking_error_bps=0.5,
        bootstrap_sample_count=128,
        minimum_bootstrap_hit_rate_lower_bound=0.5,
        minimum_bootstrap_decay_ratio_lower_bound=0.5,
    )
    report = harness.run(
        dataset,
        [
            RegimeSplitSpec(
                train_start="2024-01-02T14:29:00Z",
                train_end="2024-01-02T14:59:00Z",
                test_start="2024-01-03T14:29:00Z",
                test_end="2024-01-03T14:59:00Z",
                label="split-1",
            )
        ],
        execution_frame=execution_frame,
    )

    assert report.passed is True
    assert report.summary["mean_test_hit_rate"] >= 0.5
    assert report.summary["mean_unseen_edge_rate"] == 0.0
    assert report.summary["mean_test_fill_rate"] >= 0.5
    assert report.summary["mean_bootstrap_hit_rate_lower_bound"] >= 0.5


def test_rolling_validation_harness_flags_regime_and_edge_failures() -> None:
    dataset = pd.DataFrame(
        [
            {"timestamp": "2024-01-02T14:30:00Z", "from_state": "s1", "to_state": "s2", "regime": "execution_flow", "realized_drift_bps": 1.2},
            {"timestamp": "2024-01-02T14:31:00Z", "from_state": "s1", "to_state": "s2", "regime": "execution_flow", "realized_drift_bps": 1.1},
            {"timestamp": "2024-01-03T14:30:00Z", "from_state": "s9", "to_state": "s10", "regime": "liquidity_shock", "realized_drift_bps": -0.2},
        ]
    )
    execution_frame = pd.DataFrame(
        [
            {
                "timestamp": "2024-01-03T14:30:00Z",
                "fill_rate": 0.10,
                "cancel_rate": 0.90,
                "expected_drift_bps": 1.5,
                "realized_drift_bps": -0.2,
                "kill_switch_active": True,
            }
        ]
    )
    harness = RollingValidationHarness(
        minimum_test_rows=1,
        minimum_regime_coverage=0.5,
        minimum_hit_rate=0.5,
        minimum_decay_ratio=0.5,
        minimum_fill_rate=0.5,
        maximum_cancel_rate=0.5,
        maximum_drift_tracking_error_bps=1.0,
        bootstrap_sample_count=128,
        minimum_bootstrap_hit_rate_lower_bound=0.5,
        minimum_bootstrap_decay_ratio_lower_bound=0.5,
    )
    report = harness.run(
        dataset,
        [
            RegimeSplitSpec(
                train_start="2024-01-02T14:29:00Z",
                train_end="2024-01-02T14:59:00Z",
                test_start="2024-01-03T14:29:00Z",
                test_end="2024-01-03T14:59:00Z",
                label="split-1",
            )
        ],
        execution_frame=execution_frame,
    )

    assert report.passed is False
    assert any("regime coverage" in failure for failure in report.failures)
    assert any("trained-edge overlap" in failure for failure in report.failures)
    assert any("fill rate" in failure for failure in report.failures)
    assert any("cancel rate" in failure for failure in report.failures)
    assert any("tracking error" in failure for failure in report.failures)
    assert any("kill switch" in failure for failure in report.failures)
    assert any("bootstrap hit-rate" in failure for failure in report.failures)


def test_rolling_validation_harness_surfaces_bootstrap_decay_failure() -> None:
    dataset = pd.DataFrame(
        [
            {"timestamp": "2024-01-02T14:30:00Z", "from_state": "s1", "to_state": "s2", "regime": "execution_flow", "realized_drift_bps": 2.5},
            {"timestamp": "2024-01-02T14:31:00Z", "from_state": "s1", "to_state": "s2", "regime": "execution_flow", "realized_drift_bps": 2.0},
            {"timestamp": "2024-01-03T14:30:00Z", "from_state": "s1", "to_state": "s2", "regime": "execution_flow", "realized_drift_bps": 0.1},
            {"timestamp": "2024-01-03T14:31:00Z", "from_state": "s1", "to_state": "s2", "regime": "execution_flow", "realized_drift_bps": 0.2},
        ]
    )
    harness = RollingValidationHarness(
        minimum_test_rows=2,
        minimum_regime_coverage=1.0,
        minimum_hit_rate=0.5,
        minimum_decay_ratio=0.05,
        bootstrap_sample_count=128,
        minimum_bootstrap_hit_rate_lower_bound=0.5,
        minimum_bootstrap_decay_ratio_lower_bound=0.2,
    )
    report = harness.run(
        dataset,
        [
            RegimeSplitSpec(
                train_start="2024-01-02T14:29:00Z",
                train_end="2024-01-02T14:59:00Z",
                test_start="2024-01-03T14:29:00Z",
                test_end="2024-01-03T14:59:00Z",
                label="split-1",
            )
        ],
    )

    assert report.passed is False
    assert any("bootstrap decay-ratio" in failure for failure in report.failures)


def test_validation_hit_rate_scores_trained_direction_not_unconditional_drift_sign() -> None:
    train = [
        {
            "timestamp": "2024-01-02T14:30:00Z",
            "from_state": "s1",
            "to_state": "s2",
            "regime": "execution_flow",
            "realized_drift_bps": -1.0,
        },
        {
            "timestamp": "2024-01-02T14:31:00Z",
            "from_state": "s1",
            "to_state": "s2",
            "regime": "execution_flow",
            "realized_drift_bps": -2.0,
        },
    ]
    test = [
        {
            "timestamp": "2024-01-03T14:30:00Z",
            "from_state": "s1",
            "to_state": "s2",
            "regime": "execution_flow",
            "realized_drift_bps": -0.5,
        }
    ]
    harness = RollingValidationHarness(
        minimum_fill_rate=0.0,
        bootstrap_sample_count=0,
        minimum_bootstrap_hit_rate_lower_bound=0.0,
        minimum_bootstrap_decay_ratio_lower_bound=0.0,
    )

    report = harness.run(
        pd.DataFrame(train + test),
        [
            RegimeSplitSpec(
                train_start="2024-01-02T14:29:00Z",
                train_end="2024-01-02T14:59:00Z",
                test_start="2024-01-03T14:29:00Z",
                test_end="2024-01-03T14:59:00Z",
                label="directional",
            )
        ],
    )

    assert report.summary["mean_test_hit_rate"] == 1.0


def test_validation_scores_only_session_consensus_edges() -> None:
    dataset = pd.DataFrame(
        [
            {
                "timestamp": "2024-01-02T14:30:00Z",
                "session_date": "2024-01-02",
                "from_state": "stable",
                "to_state": "next",
                "regime": "execution_flow",
                "realized_drift_bps": 1.0,
            },
            {
                "timestamp": "2024-01-02T14:31:00Z",
                "session_date": "2024-01-02",
                "from_state": "unstable",
                "to_state": "next",
                "regime": "execution_flow",
                "realized_drift_bps": 5.0,
            },
            {
                "timestamp": "2024-01-03T14:30:00Z",
                "session_date": "2024-01-03",
                "from_state": "stable",
                "to_state": "next",
                "regime": "execution_flow",
                "realized_drift_bps": 2.0,
            },
            {
                "timestamp": "2024-01-03T14:31:00Z",
                "session_date": "2024-01-03",
                "from_state": "unstable",
                "to_state": "next",
                "regime": "execution_flow",
                "realized_drift_bps": -4.0,
            },
            {
                "timestamp": "2024-01-04T14:30:00Z",
                "session_date": "2024-01-04",
                "from_state": "stable",
                "to_state": "next",
                "regime": "execution_flow",
                "realized_drift_bps": 0.5,
            },
            {
                "timestamp": "2024-01-04T14:31:00Z",
                "session_date": "2024-01-04",
                "from_state": "unstable",
                "to_state": "next",
                "regime": "execution_flow",
                "realized_drift_bps": 0.5,
            },
        ]
    )
    harness = RollingValidationHarness(
        minimum_test_rows=2,
        minimum_directional_test_rows=1,
        minimum_decay_ratio=0.1,
        minimum_fill_rate=0.0,
        bootstrap_sample_count=0,
        minimum_bootstrap_hit_rate_lower_bound=0.0,
        minimum_bootstrap_decay_ratio_lower_bound=0.0,
    )

    report = harness.run(
        dataset,
        [
            RegimeSplitSpec(
                train_start="2024-01-02T14:29:00Z",
                train_end="2024-01-03T14:59:00Z",
                test_start="2024-01-04T14:29:00Z",
                test_end="2024-01-04T14:59:00Z",
                label="session-consensus",
            )
        ],
    )

    assert report.passed is True
    assert report.summary["mean_directional_test_rows"] == 1.0
    assert report.summary["mean_directional_coverage"] == 0.5
    assert report.summary["mean_test_hit_rate"] == 1.0
