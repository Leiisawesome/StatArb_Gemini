from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from l1_microstructure.artifacts import ArtifactBundleSelector, ArtifactMetadata, LocalArtifactStore, RunQualityGate
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.execution import ExecutionReport
from l1_microstructure.ingest import HistoricalBatchRequest, LiveSubscriptionRequest
from l1_microstructure.live import RouteAcknowledgement, RoutedLiveTradingRunner, RunnerConfig, SourceBackedPaperRunner
from l1_microstructure.workflow import ArtifactDrivenResearchWorkflow
from tests.unit.l1_state_machine.support import FixtureMarketDataSource as InMemoryMassiveDataSource


def _et_ns(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> int:
    timestamp = datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo("America/New_York"))
    return int(timestamp.timestamp() * 1_000_000_000)


def _make_source() -> InMemoryMassiveDataSource:
    return InMemoryMassiveDataSource(
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


class AcceptedFillRouter:
    def __init__(self) -> None:
        self.pending_reports: list[ExecutionReport] = []

    def submit(self, request):
        self.pending_reports.append(
            ExecutionReport(
                symbol=request.symbol,
                action=request.action,
                status="filled",
                quantity=request.quantity,
                fill_price=request.expected_state.book.ask_price,
                alignment_probability=1.0,
                fill_probability=1.0,
                slippage_bps=0.0,
                reason="accepted fill router",
                timestamp_ns=request.executable_timestamp_ns,
            )
        )
        return RouteAcknowledgement(external_order_id="accepted-fill-1", status="accepted")

    def poll(self, symbols):
        ready = [report for report in self.pending_reports if report.symbol in symbols]
        self.pending_reports = [report for report in self.pending_reports if report.symbol not in symbols]
        return ready

    def stop(self) -> None:
        return None


def test_artifact_bundle_selector_resolves_latest_complete_run(tmp_path) -> None:
    source = _make_source()
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)

    first = workflow.run(symbol="AAPL", events=events)
    second = workflow.run(symbol="AAPL", events=events)

    selector = ArtifactBundleSelector(workflow.store)
    bundle = selector.resolve_latest_for_symbol("AAPL")
    date_bundle = selector.resolve_for_symbol_on_date(symbol="AAPL", trade_date="2024-03-11")
    passing_bundle = selector.resolve_latest_passing_for_symbol("AAPL")
    passing_date_bundle = selector.resolve_passing_for_symbol_on_date(symbol="AAPL", trade_date="2024-03-11")

    assert selector.available_run_ids("AAPL")
    assert selector.list_run_manifests("AAPL")
    assert selector.list_run_manifests("AAPL", passing_only=True)
    assert bundle.metadata["run_id"] == second.run_id
    assert bundle.artifact_ids["state_calibration"] == second.artifact_ids.state_calibration_id
    assert bundle.artifact_ids["execution_calibration"] == second.artifact_ids.execution_calibration_id
    assert bundle.artifact_ids["transition_model"] == second.artifact_ids.transition_model_id
    assert date_bundle.metadata["run_id"] == second.run_id
    assert passing_bundle.metadata["run_id"] == second.run_id
    assert passing_date_bundle.metadata["run_id"] == second.run_id
    assert second.run_id != first.run_id


def test_artifact_bundle_selector_ignores_uncommitted_loose_artifacts(tmp_path) -> None:
    store = LocalArtifactStore(tmp_path)
    for artifact_type in ArtifactBundleSelector.REQUIRED_TYPES:
        store.save(
            ArtifactMetadata(
                artifact_id=f"loose-{artifact_type}",
                artifact_type=artifact_type,
                version="v1",
                created_at="2026-01-01T00:00:00+00:00",
                metadata={"symbol": "AAPL", "run_id": "uncommitted"},
            ),
            {"uncommitted": True},
        )

    selector = ArtifactBundleSelector(store)
    with pytest.raises(ValueError, match="no complete artifact bundle"):
        selector.resolve_latest_for_symbol("AAPL")
    with pytest.raises(ValueError, match="no committed run manifest"):
        selector.resolve_by_run_id(symbol="AAPL", run_id="uncommitted")


def test_source_backed_runner_uses_historical_source_and_resolved_bundle(tmp_path) -> None:
    source = _make_source()
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    result = workflow.run(symbol="AAPL", events=events)

    selector = ArtifactBundleSelector(workflow.store)
    runner = SourceBackedPaperRunner(source=source, framework_config=config, bundle_selector=selector)
    historical_runner = runner.run_historical(
        HistoricalBatchRequest(symbols=("AAPL",), trade_date=date(2024, 3, 11)),
        RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=config.execution.latency_ms),
        run_id=result.run_id,
    )

    assert historical_runner.updates
    assert historical_runner.monitoring_frame().shape[0] > 0
    assert historical_runner.runtime_artifacts.metadata["run_id"] == result.run_id
    assert historical_runner.runtime_artifacts.metadata["symbol"] == "AAPL"


def test_source_backed_runner_can_require_validation_passing_bundle(tmp_path) -> None:
    source = _make_source()
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    result = workflow.run(symbol="AAPL", events=events)

    selector = ArtifactBundleSelector(workflow.store)
    runner = SourceBackedPaperRunner(
        source=source,
        framework_config=config,
        bundle_selector=selector,
        require_validation_passed=True,
    )
    historical_runner = runner.run_historical(
        HistoricalBatchRequest(symbols=("AAPL",), trade_date=date(2024, 3, 11)),
        RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=config.execution.latency_ms),
    )

    assert historical_runner.updates
    assert historical_runner.runtime_artifacts.metadata["run_id"] == result.run_id


def test_artifact_bundle_selector_can_gate_on_execution_quality(tmp_path) -> None:
    source = _make_source()
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    result = workflow.run(symbol="AAPL", events=events)

    selector = ArtifactBundleSelector(workflow.store)
    permissive = selector.resolve_latest_passing_for_symbol(
        "AAPL",
        quality_gate=RunQualityGate(maximum_drift_tracking_error_bps=3.5, maximum_unseen_edge_rate=0.3),
    )

    assert permissive.metadata["run_id"] == result.run_id
    approved = selector.resolve_passing_by_run_id(
        symbol="AAPL",
        run_id=result.run_id,
        quality_gate=RunQualityGate(maximum_drift_tracking_error_bps=3.5),
    )
    assert approved.metadata["run_id"] == result.run_id
    assert selector.list_run_manifests(
        "AAPL",
        passing_only=True,
        quality_gate=RunQualityGate(maximum_drift_tracking_error_bps=3.5),
    )

    with pytest.raises(ValueError):
        selector.resolve_latest_passing_for_symbol(
            "AAPL",
            quality_gate=RunQualityGate(minimum_fill_rate=0.1),
        )
    with pytest.raises(ValueError, match="not committed and validation-approved"):
        selector.resolve_passing_by_run_id(
            symbol="AAPL",
            run_id=result.run_id,
            quality_gate=RunQualityGate(minimum_fill_rate=0.1),
        )


def test_passing_bundle_requires_matching_approved_validation_report(tmp_path) -> None:
    source = _make_source()
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    result = workflow.run(symbol="AAPL", events=events)
    validation_id = result.artifact_ids.validation_report_id
    metadata = workflow.store.load_metadata(validation_id)
    payload = workflow.store.load(validation_id)
    payload["passed"] = False
    workflow.store.save(metadata, payload)

    selector = ArtifactBundleSelector(workflow.store)

    assert selector.list_run_manifests("AAPL", passing_only=True) == []
    with pytest.raises(ValueError, match="not committed and validation-approved"):
        selector.resolve_passing_by_run_id(symbol="AAPL", run_id=result.run_id)


def test_source_backed_runner_quality_gate_rejects_low_quality_bundle(tmp_path) -> None:
    source = _make_source()
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    workflow.run(symbol="AAPL", events=events)

    selector = ArtifactBundleSelector(workflow.store)
    runner = SourceBackedPaperRunner(
        source=source,
        framework_config=config,
        bundle_selector=selector,
        require_validation_passed=True,
        quality_gate=RunQualityGate(minimum_fill_rate=0.1),
    )

    with pytest.raises(ValueError):
        runner.run_historical(
            HistoricalBatchRequest(symbols=("AAPL",), trade_date=date(2024, 3, 11)),
            RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=config.execution.latency_ms),
        )


def test_routed_live_runner_can_resolve_latest_passing_bundle(tmp_path) -> None:
    source = _make_source()
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = ArtifactDrivenResearchWorkflow(tmp_path, framework_config=config)
    result = workflow.run(symbol="AAPL", events=events)

    runner = RoutedLiveTradingRunner(
        source=source,
        router=AcceptedFillRouter(),
        framework_config=config,
        bundle_selector=ArtifactBundleSelector(workflow.store),
        require_validation_passed=True,
    )
    routed_runner = runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=config.execution.latency_ms),
    )

    assert routed_runner.runtime_artifacts.metadata["run_id"] == result.run_id
    assert routed_runner.monitoring_frame().shape[0] > 0
