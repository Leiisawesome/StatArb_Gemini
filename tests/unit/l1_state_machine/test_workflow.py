from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.ingest import LiveSubscriptionRequest
from l1_microstructure.validation import RegimeSplitSpec
from l1_microstructure.workflow import ArtifactDrivenResearchWorkflow
from tests.unit.l1_state_machine.support import FixtureMarketDataSource as InMemoryMassiveDataSource


def _et_ns(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> int:
    timestamp = datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo("America/New_York"))
    return int(timestamp.timestamp() * 1_000_000_000)


def test_artifact_driven_research_workflow_runs_end_to_end(tmp_path, monkeypatch) -> None:
    source = InMemoryMassiveDataSource(
        [
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 0),
                "bp": 100.0,
                "ap": 100.02,
                "bs": 100,
                "as": 100,
            },
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 1),
                "bp": 100.01,
                "ap": 100.02,
                "bs": 450,
                "as": 40,
            },
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 2), "p": 100.02, "s": 400, "side": "buy"},
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 4),
                "bp": 100.04,
                "ap": 100.08,
                "bs": 40,
                "as": 300,
            },
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 5), "p": 100.05, "s": 300, "side": "buy"},
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 7),
                "bp": 100.07,
                "ap": 100.09,
                "bs": 420,
                "as": 60,
            },
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 8), "p": 100.08, "s": 350, "side": "buy"},
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 10),
                "bp": 100.10,
                "ap": 100.14,
                "bs": 30,
                "as": 260,
            },
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    build_calls = 0
    original_build_panels = workflow._build_panels

    def counted_build_panels(*, symbol, events):
        nonlocal build_calls
        build_calls += 1
        return original_build_panels(symbol=symbol, events=events)

    monkeypatch.setattr(workflow, "_build_panels", counted_build_panels)

    result = workflow.run(symbol="AAPL", events=events)

    assert result.symbol == "AAPL"
    assert result.state_panel_rows > 0
    assert result.transition_panel_rows > 0
    assert result.validation_report.summary["mean_test_rows"] >= 1.0
    assert result.replay_summary["update_count"] > 0.0
    # One full-run build plus one isolated build for the default validation split.
    assert build_calls == 2

    artifact_ids = result.artifact_ids
    for artifact_id in (
        artifact_ids.state_calibration_id,
        artifact_ids.regime_calibration_id,
        artifact_ids.execution_calibration_id,
        artifact_ids.transition_model_id,
        artifact_ids.validation_report_id,
        artifact_ids.monitored_replay_id,
        artifact_ids.run_manifest_id,
    ):
        assert (tmp_path / artifact_id).exists()


def test_artifact_driven_research_workflow_supports_multi_split_oos_validation(tmp_path) -> None:
    source = InMemoryMassiveDataSource(
        [
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 0),
                "bp": 100.0,
                "ap": 100.02,
                "bs": 100,
                "as": 100,
            },
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 1),
                "bp": 100.01,
                "ap": 100.02,
                "bs": 450,
                "as": 40,
            },
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 2), "p": 100.02, "s": 400, "side": "buy"},
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 4),
                "bp": 100.04,
                "ap": 100.08,
                "bs": 40,
                "as": 300,
            },
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 5), "p": 100.05, "s": 300, "side": "buy"},
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 7),
                "bp": 100.07,
                "ap": 100.09,
                "bs": 420,
                "as": 60,
            },
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 8), "p": 100.08, "s": 350, "side": "buy"},
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 10),
                "bp": 100.10,
                "ap": 100.14,
                "bs": 30,
                "as": 260,
            },
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)

    result = workflow.run(
        symbol="AAPL",
        events=events,
        splits=[
            RegimeSplitSpec(
                train_start="2024-03-11T13:30:00+00:00",
                train_end="2024-03-11T13:30:04+00:00",
                test_start="2024-03-11T13:30:05+00:00",
                test_end="2024-03-11T13:30:07+00:00",
                label="split-1",
            ),
            RegimeSplitSpec(
                train_start="2024-03-11T13:30:00+00:00",
                train_end="2024-03-11T13:30:05+00:00",
                test_start="2024-03-11T13:30:07+00:00",
                test_end="2024-03-11T13:30:10+00:00",
                label="split-2",
            ),
        ],
    )

    manifest = workflow.store.load(result.artifact_ids.run_manifest_id)

    assert result.validation_report.metadata["split_count"] == 2
    assert manifest["metadata"]["validation_mode"] == "rolling-oos-retrain"
    assert manifest["metadata"]["validation_split_count"] == 2


def test_validation_rebuilds_panels_from_only_the_training_window(tmp_path, monkeypatch) -> None:
    source = InMemoryMassiveDataSource(
        [
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 0),
                "bp": 100.0,
                "ap": 100.02,
                "bs": 100,
                "as": 100,
            },
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 2), "p": 100.01, "s": 100},
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 4),
                "bp": 100.01,
                "ap": 100.03,
                "bs": 300,
                "as": 50,
            },
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 5), "p": 100.03, "s": 100},
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 7),
                "bp": 100.04,
                "ap": 100.06,
                "bs": 50,
                "as": 300,
            },
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 8), "p": 101.0, "s": 100},
            {
                "ev": "Q",
                "sym": "AAPL",
                "t": _et_ns(2024, 3, 11, 9, 30, 10),
                "bp": 101.0,
                "ap": 101.02,
                "bs": 100,
                "as": 100,
            },
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    built_windows: list[list[int]] = []
    built_transition_drifts: list[list[float]] = []
    original_build_panels = workflow._build_panels

    def recorded_build_panels(*, symbol, events):
        built_windows.append([event.timestamp_ns for event in events])
        panels = original_build_panels(symbol=symbol, events=events)
        built_transition_drifts.append(panels[1].frame["realized_drift_bps"].tolist())
        return panels

    monkeypatch.setattr(workflow, "_build_panels", recorded_build_panels)

    workflow.run(
        symbol="AAPL",
        events=events,
        splits=[
            RegimeSplitSpec(
                train_start="2024-03-11T13:30:02+00:00",
                train_end="2024-03-11T13:30:07+00:00",
                test_start="2024-03-11T13:30:08+00:00",
                test_end="2024-03-11T13:30:10+00:00",
                label="isolated-window",
            )
        ],
    )

    assert built_windows[0] == [event.timestamp_ns for event in events]
    assert built_windows[1] == [_et_ns(2024, 3, 11, 9, 30, second) for second in (2, 4, 5, 7)]
    assert max(abs(drift) for drift in built_transition_drifts[1]) < 10.0


def test_multi_session_workflow_resets_state_and_uses_expanding_walk_forward_splits(tmp_path, monkeypatch) -> None:
    payloads = []
    for day, price_offset in ((11, 0.0), (12, 1.0), (13, 2.0)):
        payloads.extend(
            [
                {
                    "ev": "Q",
                    "sym": "AAPL",
                    "t": _et_ns(2024, 3, day, 9, 30, 0),
                    "bp": 100.0 + price_offset,
                    "ap": 100.02 + price_offset,
                    "bs": 100,
                    "as": 100,
                },
                {
                    "ev": "Q",
                    "sym": "AAPL",
                    "t": _et_ns(2024, 3, day, 9, 30, 1),
                    "bp": 100.01 + price_offset,
                    "ap": 100.03 + price_offset,
                    "bs": 400,
                    "as": 50,
                },
                {
                    "ev": "T",
                    "sym": "AAPL",
                    "t": _et_ns(2024, 3, day, 9, 30, 2),
                    "p": 100.03 + price_offset,
                    "s": 400,
                    "side": "buy",
                },
                {
                    "ev": "Q",
                    "sym": "AAPL",
                    "t": _et_ns(2024, 3, day, 9, 30, 4),
                    "bp": 100.04 + price_offset,
                    "ap": 100.08 + price_offset,
                    "bs": 40,
                    "as": 300,
                },
                {
                    "ev": "T",
                    "sym": "AAPL",
                    "t": _et_ns(2024, 3, day, 9, 30, 5),
                    "p": 100.05 + price_offset,
                    "s": 300,
                    "side": "sell",
                },
            ]
        )

    source = InMemoryMassiveDataSource(payloads)
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)

    combined_state, combined_transitions = workflow._build_panels(symbol="AAPL", events=events)
    per_session_rows = []
    for session_events in workflow._events_by_session(events).values():
        state_panel, transition_panel = workflow._build_panels(symbol="AAPL", events=session_events)
        per_session_rows.append((len(state_panel.frame), len(transition_panel.frame)))

    assert len(combined_state.frame) == sum(state_rows for state_rows, _ in per_session_rows)
    assert len(combined_transitions.frame) == sum(transition_rows for _, transition_rows in per_session_rows)
    assert combined_transitions.frame["session_date"].nunique() == 3

    build_calls = 0
    original_build_panels = workflow._build_panels

    def counted_build_panels(*, symbol, events):
        nonlocal build_calls
        build_calls += 1
        return original_build_panels(symbol=symbol, events=events)

    monkeypatch.setattr(workflow, "_build_panels", counted_build_panels)
    result = workflow.run(symbol="AAPL", events=events)
    manifest = workflow.store.load(result.artifact_ids.run_manifest_id)

    assert result.validation_report.metadata["split_count"] == 1
    assert set(result.validation_report.metadata["activation_diagnostics"]) == {
        "walk-forward-2024-03-13",
    }
    assert manifest["trade_date"] == "2024-03-13"
    assert manifest["training_session_dates"] == ["2024-03-11", "2024-03-12", "2024-03-13"]
    assert manifest["metadata"]["training_session_count"] == 3
    assert result.activation_summary["transition_count"] > 0
    assert build_calls == 1


def test_session_consensus_workflow_rejects_too_few_dates(tmp_path) -> None:
    payloads = []
    for day in (11, 12):
        payloads.extend(
            [
                {
                    "ev": "Q",
                    "sym": "AAPL",
                    "t": _et_ns(2024, 3, day, 9, 30, 0),
                    "bp": 100.0,
                    "ap": 100.02,
                    "bs": 100,
                    "as": 100,
                },
                {
                    "ev": "Q",
                    "sym": "AAPL",
                    "t": _et_ns(2024, 3, day, 9, 30, 1),
                    "bp": 100.01,
                    "ap": 100.03,
                    "bs": 300,
                    "as": 50,
                },
            ]
        )
    events = list(
        InMemoryMassiveDataSource(payloads).subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",)))
    )
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)

    with __import__("pytest").raises(ValueError, match="requires at least 3 completed trade dates"):
        workflow.run(symbol="AAPL", events=events)
