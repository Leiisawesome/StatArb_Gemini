from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.ingest import InMemoryPolygonDataSource, LiveSubscriptionRequest
from l1_microstructure.workflow import ArtifactDrivenResearchWorkflow


def _et_ns(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> int:
    timestamp = datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo("America/New_York"))
    return int(timestamp.timestamp() * 1_000_000_000)


def test_artifact_driven_research_workflow_runs_end_to_end(tmp_path) -> None:
    source = InMemoryPolygonDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 1), "bp": 100.01, "ap": 100.02, "bs": 450, "as": 40},
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 2), "p": 100.02, "s": 400, "side": "buy"},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 4), "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 5), "p": 100.05, "s": 300, "side": "buy"},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 7), "bp": 100.07, "ap": 100.09, "bs": 420, "as": 60},
            {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 8), "p": 100.08, "s": 350, "side": "buy"},
            {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 10), "bp": 100.10, "ap": 100.14, "bs": 30, "as": 260},
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)

    result = workflow.run(symbol="AAPL", events=events)

    assert result.symbol == "AAPL"
    assert result.state_panel_rows > 0
    assert result.transition_panel_rows > 0
    assert result.validation_report.summary["mean_test_rows"] >= 1.0
    assert result.replay_summary["update_count"] > 0.0

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