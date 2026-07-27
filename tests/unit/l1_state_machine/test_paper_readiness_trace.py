"""Critical paper-path characterization tests for readiness audit.

These drive the shipped paper runners and artifact selector — not reimplemented
stubs — and document operator-facing gates on the paper-trade path.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from l1_microstructure.artifacts import ArtifactBundleSelector, ArtifactMetadata
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.decision import DecisionEngine, TradeAction
from l1_microstructure.ingest import HistoricalBatchRequest, LiveSubscriptionRequest
from l1_microstructure.live.paper import SimulatorPaperTradingRunner
from l1_microstructure.live.source import SourceBackedPaperRunner
from l1_microstructure.live.interfaces import RunnerConfig
from l1_microstructure.pipeline import FrameworkUpdate, L1MicrostructureStateMachine
from l1_microstructure.risk import RiskEngine
from l1_microstructure.validation import RollingValidationHarness
from l1_microstructure.workflow import ArtifactDrivenResearchWorkflow
from tests.unit.l1_state_machine.support import FixtureMarketDataSource as InMemoryMassiveDataSource


def _et_ns(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> int:
    timestamp = datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo("America/New_York"))
    return int(timestamp.timestamp() * 1_000_000_000)


def _permissive_workflow(tmp_path, config: FrameworkConfig) -> ArtifactDrivenResearchWorkflow:
    """Match post-merge unit suite: tiny fixtures cannot satisfy production validation thresholds."""
    return ArtifactDrivenResearchWorkflow(
        tmp_path,
        framework_config=config,
        validation_harness=RollingValidationHarness(
            minimum_fill_rate=0.0,
            maximum_cancel_rate=1.0,
            maximum_drift_tracking_error_bps=float("inf"),
            minimum_directional_test_rows=0,
            bootstrap_sample_count=0,
            minimum_bootstrap_hit_rate_lower_bound=0.0,
            minimum_bootstrap_decay_ratio_lower_bound=0.0,
        ),
    )


def _make_source() -> InMemoryMassiveDataSource:
    # Same fixture shape as test_bundle_selection_and_source_runner.
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


def _workflow_bundle(tmp_path):
    source = _make_source()
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    workflow = _permissive_workflow(tmp_path, config)
    result = workflow.run(symbol="AAPL", events=events)
    return source, config, workflow, result


def test_simulator_paper_runner_uses_shared_state_machine_core() -> None:
    """Paper runner must invoke L1MicrostructureStateMachine, not a parallel mock path."""
    source = _make_source()
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    runner = SimulatorPaperTradingRunner(events=events, framework_config=config)
    runner.start(RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=100))

    assert runner.updates
    assert all(isinstance(update, FrameworkUpdate) for update in runner.updates)
    # FrameworkUpdate fields are only produced by pipeline.on_event orchestration
    assert any(update.state is not None for update in runner.updates)
    assert any(update.regime is not None for update in runner.updates)


def test_paper_path_decision_and_risk_are_shipped_classes() -> None:
    machine = L1MicrostructureStateMachine()
    assert isinstance(machine.decision_engine, DecisionEngine)
    assert isinstance(machine.risk_engine, RiskEngine)
    assert TradeAction.HOLD.value == "hold"


def test_source_backed_paper_historical_loads_workflow_artifacts(tmp_path) -> None:
    source, config, workflow, result = _workflow_bundle(tmp_path)
    runner = SourceBackedPaperRunner(
        source=source,
        framework_config=config,
        bundle_selector=ArtifactBundleSelector(workflow.store),
        require_validation_passed=True,
    )
    paper = runner.run_historical(
        HistoricalBatchRequest(symbols=("AAPL",), trade_date=date(2024, 3, 11)),
        RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=config.execution.latency_ms),
    )
    assert paper.updates
    assert paper.runtime_artifacts.transition_model is not None
    assert paper.runtime_artifacts.metadata["run_id"] == result.run_id
    assert paper.runtime_artifacts.metadata.get("validation_passed") is True


def test_require_validation_flag_is_opt_in_default_false() -> None:
    """CLI/default SourceBackedPaperRunner does not enforce validation unless requested."""
    runner = SourceBackedPaperRunner(source=_make_source())
    assert runner.require_validation_passed is False


def test_explicit_run_id_bypasses_require_validation_passed_gate(tmp_path) -> None:
    """Documented gap: with --run-id, require_validation_passed does not re-check validation.

    SourceBackedPaperRunner._run_events always calls resolve_by_run_id when run_id is set,
    never resolve_passing_by_run_id. A failing manifest can still be loaded.
    """
    source, config, workflow, result = _workflow_bundle(tmp_path)
    store = workflow.store
    selector = ArtifactBundleSelector(store)

    # Mark the committed run as validation-failed in the stored manifest payload.
    # list_run_manifests gates on payload["metadata"]["validation_passed"].
    manifest_meta = next(
        meta
        for meta in store.list_metadata("run_manifest")
        if store.load(meta.artifact_id).get("run_id") == result.run_id
    )
    payload = store.load(manifest_meta.artifact_id)
    payload_metadata = dict(payload.get("metadata", {}))
    payload_metadata["validation_passed"] = False
    payload["metadata"] = payload_metadata
    store.save(
        ArtifactMetadata(
            artifact_id=manifest_meta.artifact_id,
            artifact_type=manifest_meta.artifact_type,
            version=manifest_meta.version,
            created_at=manifest_meta.created_at,
            tags=manifest_meta.tags,
            metadata={**manifest_meta.metadata, "run_id": result.run_id, "symbol": "AAPL"},
        ),
        payload,
    )

    # Latest-passing path must refuse.
    with pytest.raises(ValueError, match="validation-passing"):
        SourceBackedPaperRunner(
            source=source,
            framework_config=config,
            bundle_selector=selector,
            require_validation_passed=True,
        ).run_historical(
            HistoricalBatchRequest(symbols=("AAPL",), trade_date=date(2024, 3, 11)),
            RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=config.execution.latency_ms),
        )

    # Explicit run_id still loads the failing run despite require_validation_passed=True.
    paper = SourceBackedPaperRunner(
        source=source,
        framework_config=config,
        bundle_selector=selector,
        require_validation_passed=True,
    ).run_historical(
        HistoricalBatchRequest(symbols=("AAPL",), trade_date=date(2024, 3, 11)),
        RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=config.execution.latency_ms),
        run_id=result.run_id,
    )
    assert paper.runtime_artifacts.metadata["run_id"] == result.run_id
    assert paper.runtime_artifacts.metadata.get("validation_passed") is False
