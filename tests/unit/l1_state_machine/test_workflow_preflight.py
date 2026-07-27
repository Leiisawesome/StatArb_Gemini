from __future__ import annotations

import json
from contextlib import contextmanager

from l1_microstructure.cli import main
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.ingest import LiveSubscriptionRequest
from l1_microstructure.workflow import ArtifactDrivenResearchWorkflow
from tests.unit.l1_state_machine.support import FixtureMarketDataSource


def _payloads() -> list[dict[str, object]]:
    return [
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 450, "as": 40},
        {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
        {"ev": "T", "sym": "AAPL", "t": 1710163805000000000, "p": 100.05, "s": 300, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163807000000000, "bp": 100.07, "ap": 100.09, "bs": 420, "as": 60},
        {"ev": "T", "sym": "AAPL", "t": 1710163808000000000, "p": 100.08, "s": 350, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163810000000000, "bp": 100.10, "ap": 100.14, "bs": 30, "as": 260},
    ]


def _fixture_source() -> FixtureMarketDataSource:
    return FixtureMarketDataSource(_payloads())


@contextmanager
def _patched_cli_sources():
    from unittest.mock import patch

    with (
        patch("l1_microstructure.cli._historical_source", side_effect=lambda: _fixture_source()),
        patch("l1_microstructure.cli._live_source", side_effect=lambda: _fixture_source()),
    ):
        yield


def _workflow_config() -> FrameworkConfig:
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    return config


def test_fixture_market_data_source_supports_historical_loading() -> None:
    events = list(_fixture_source().subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    assert len(events) > 0
    assert all(event.symbol == "AAPL" for event in events)


def test_workflow_preflight_runs_end_to_end_from_fixture_source(tmp_path) -> None:
    events = list(_fixture_source().subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=_workflow_config())

    result = workflow.run(symbol="AAPL", events=events)

    assert result.symbol == "AAPL"
    assert result.state_panel_rows > 0
    assert result.transition_panel_rows > 0
    assert result.validation_report.summary["mean_test_rows"] >= 1.0
    assert result.replay_summary["update_count"] > 0.0


def test_cli_workflow_preflight_supports_manifest_listing_and_historical_replay(tmp_path, capsys) -> None:
    artifact_root = tmp_path / "artifacts"

    with _patched_cli_sources():
        workflow_exit = main(
            [
                "workflow",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
                "--allow-unexecuted-validation",
            ]
        )
        assert workflow_exit == 0
        workflow_payload = json.loads(capsys.readouterr().out.strip())

        list_runs_exit = main(
            [
                "list-runs",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
            ]
        )
        assert list_runs_exit == 0
        list_payload = json.loads(capsys.readouterr().out.strip())

        replay_exit = main(
            [
                "paper-historical",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--require-validation-passed",
                "--transition-threshold",
                "0.0",
            ]
        )
        assert replay_exit == 0
        replay_payload = json.loads(capsys.readouterr().out.strip())

    assert workflow_payload["symbol"] == "AAPL"
    assert list_payload["run_count"] >= 1
    assert list_payload["runs"][0]["run_id"] == workflow_payload["run_id"]
    assert replay_payload["update_count"] > 0
    assert replay_payload["monitoring_rows"] > 0


def test_cli_workflow_preflight_accepts_quality_gate_for_historical_replay(tmp_path, capsys) -> None:
    artifact_root = tmp_path / "artifacts"

    with _patched_cli_sources():
        workflow_exit = main(
            [
                "workflow",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
                "--allow-unexecuted-validation",
            ]
        )
        assert workflow_exit == 0
        _ = capsys.readouterr()

        replay_exit = main(
            [
                "paper-historical",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--require-validation-passed",
                "--max-drift-tracking-error-bps",
                "3.5",
                "--transition-threshold",
                "0.0",
            ]
        )
        assert replay_exit == 0
        replay_payload = json.loads(capsys.readouterr().out.strip())

    assert replay_payload["update_count"] > 0
    assert replay_payload["quality_metrics"]["mean_execution_drift_tracking_error_bps"] <= 3.5
