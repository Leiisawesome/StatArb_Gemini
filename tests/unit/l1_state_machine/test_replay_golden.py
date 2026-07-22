from __future__ import annotations

import json
from pathlib import Path

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.datasets import PipelineTransitionDatasetBuilder
from l1_microstructure.ingest import LiveSubscriptionRequest
from l1_microstructure.replay import DeterministicReplayEngine
from l1_microstructure.validation import RollingValidationHarness
from l1_microstructure.workflow import ArtifactDrivenResearchWorkflow
from tests.unit.l1_state_machine.support import FixtureMarketDataSource as InMemoryMassiveDataSource


_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "l1_state_machine"


def _load_fixture(name: str) -> object:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _config() -> FrameworkConfig:
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    return config


def _load_events():
    payloads = _load_fixture("golden_payloads.json")
    source = InMemoryMassiveDataSource(payloads)
    return list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))


def _round_transition_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rounded: list[dict[str, object]] = []
    for row in rows:
        rounded.append(
            {
                "timestamp_ns": int(row["timestamp_ns"]),
                "from_state": str(row["from_state"]),
                "to_state": str(row["to_state"]),
                "regime": str(row["regime"]),
                "horizon_ms": int(row["horizon_ms"]),
                "realized_drift_bps": round(float(row["realized_drift_bps"]), 6),
                "censored": bool(row["censored"]),
            }
        )
    return rounded


def _round_summary(summary: dict[str, float]) -> dict[str, float]:
    return {key: round(float(value), 6) for key, value in summary.items()}


def test_replay_ordering_matches_golden_fixture() -> None:
    expected = _load_fixture("golden_expected.json")
    events = _load_events()
    replayed = list(DeterministicReplayEngine().replay(events))

    assert [event.timestamp_ns for event in replayed] == expected["event_timestamps"]


def test_multi_horizon_dataset_matches_golden_fixture() -> None:
    expected = _load_fixture("golden_expected.json")
    builder = PipelineTransitionDatasetBuilder(_load_events(), config=_config())

    state_panel = builder.build_state_panel("AAPL")
    transition_panel = builder.build_transition_panel("AAPL")

    actual_rows = transition_panel.frame[
        ["timestamp_ns", "from_state", "to_state", "regime", "horizon_ms", "realized_drift_bps", "censored"]
    ].to_dict(orient="records")

    assert state_panel.frame["state_label"].tolist() == expected["state_labels"]
    assert _round_transition_rows(actual_rows) == expected["transition_rows"]


def test_artifact_driven_workflow_matches_golden_fixture(tmp_path) -> None:
    expected = _load_fixture("golden_expected.json")["workflow"]
    workflow = ArtifactDrivenResearchWorkflow(
        tmp_path,
        framework_config=_config(),
        validation_harness=RollingValidationHarness(
            minimum_fill_rate=0.0,
            maximum_cancel_rate=1.0,
            maximum_drift_tracking_error_bps=float("inf"),
            bootstrap_sample_count=0,
            minimum_bootstrap_hit_rate_lower_bound=0.0,
            minimum_bootstrap_decay_ratio_lower_bound=0.0,
        ),
    )

    result = workflow.run(symbol="AAPL", events=_load_events())
    manifest = workflow.store.load(result.artifact_ids.run_manifest_id)

    assert result.state_panel_rows == expected["state_panel_rows"]
    assert result.transition_panel_rows == expected["transition_panel_rows"]
    assert result.validation_report.passed is expected["validation_passed"]
    assert list(result.validation_report.failures) == expected["validation_failures"]
    assert _round_summary(result.validation_report.summary) == expected["validation_summary"]
    assert _round_summary(result.replay_summary) == expected["replay_summary"]
    assert manifest["metadata"]["runtime_transition_rows"] == expected["runtime_transition_rows"]
    assert manifest["metadata"]["available_horizons_ns"] == expected["available_horizons_ns"]
