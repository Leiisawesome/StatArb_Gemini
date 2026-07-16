from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.ingest import HistoricalBatchRequest, MassiveRESTConfig, MassiveRESTDataSource
from l1_microstructure.ingest.massive import _resolve_massive_api_key
from l1_microstructure.production.secrets import get_secret
from l1_microstructure.workflow import ArtifactDrivenResearchWorkflow


_EASTERN = ZoneInfo("America/New_York")


def _et_ns(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> int:
    timestamp = datetime(year, month, day, hour, minute, second, tzinfo=_EASTERN)
    return int(timestamp.timestamp() * 1_000_000_000)


pytestmark = [pytest.mark.integration, pytest.mark.external, pytest.mark.requires_data]


def test_massive_rest_source_can_drive_bounded_workflow(tmp_path) -> None:
    api_key = _resolve_massive_api_key(None) or get_secret("MASSIVE_API_KEY")
    if not api_key:
        pytest.skip("MASSIVE_API_KEY is not configured")

    source = MassiveRESTDataSource(MassiveRESTConfig(api_key=api_key))
    request = HistoricalBatchRequest(
        symbols=("AAPL",),
        trade_date=date(2024, 3, 11),
        include_quotes=True,
        include_trades=True,
        start_ns=_et_ns(2024, 3, 11, 9, 30, 0),
        end_ns=_et_ns(2024, 3, 11, 9, 30, 5),
    )
    events = list(source.load_historical(request))

    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    result = workflow.run(symbol="AAPL", events=events)

    assert events
    assert result.symbol == "AAPL"
    assert result.state_panel_rows > 0
    assert result.transition_panel_rows > 0
    assert result.replay_summary["update_count"] > 0.0
    assert (tmp_path / result.artifact_ids.run_manifest_id).exists()
