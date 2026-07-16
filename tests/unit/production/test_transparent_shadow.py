from __future__ import annotations

from types import SimpleNamespace

import pytest

from l1_microstructure.decision import TradeAction
from l1_microstructure.events import QuoteEvent
from l1_microstructure.production import OperationalLedger, ProductionConfig, ProductionRuntime
from l1_microstructure.production.preflight import PreflightStatus, ProductionPreflight
from l1_microstructure.live.broker_models import IBKRConnectionConfig


class _Source:
    def load_historical(self, _request):
        return []

    def subscribe_live(self, _request):
        return []


class _Router:
    def submit(self, _request):
        raise AssertionError("shadow test must not route")

    def poll(self, _symbols):
        return []

    def stop(self):
        return None

    def cancel(self, _order_id):
        return True

    def open_order_ids(self):
        return []

    def health_check(self):
        return {"connected": True, "net_liquidation": 100_000.0}

    def reconciliation_snapshot(self):
        return {**self.health_check(), "positions": {}, "open_order_ids": []}

    def snapshot_recovery_state(self):
        return None

    def validate_recovery_state(self, state, _symbols=None):
        if state is not None:
            raise TypeError("shadow test router does not support recovery state")

    def restore_recovery_state(self, state):
        self.validate_recovery_state(state)

    def recovery_reconciliations(self):
        return []


class _Candidate:
    def __init__(self, *, fails: bool = False) -> None:
        self.fails = fails

    def on_event(self, _event):
        if self.fails:
            raise RuntimeError("isolated candidate failure")
        return SimpleNamespace(action=TradeAction.BUY)


def _config(tmp_path, **overrides) -> ProductionConfig:
    values = {
        "symbols": ("AAPL",),
        "artifact_root": tmp_path / "artifacts",
        "promoted_run_ids": {"AAPL": "v1"},
        "database_path": tmp_path / "ledger.sqlite3",
        "broker_env_file": None,
        "warmup_seconds": 0.0,
    }
    values.update(overrides)
    return ProductionConfig(**values)


def test_production_config_requires_complete_transparent_shadow_universe(tmp_path) -> None:
    with pytest.raises(ValueError, match="missing transparent shadow"):
        ProductionConfig(
            symbols=("AAPL", "MSFT"),
            artifact_root=tmp_path,
            promoted_run_ids={"AAPL": "v1", "MSFT": "v1"},
            transparent_shadow_run_ids={"AAPL": "v2"},
        )


def test_runtime_records_bounded_failure_isolated_transparent_shadow_summary(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "ledger.sqlite3")
    runtime = ProductionRuntime(
        _config(tmp_path, transparent_shadow_run_ids={"AAPL": "v2"}),
        source=_Source(),
        router=_Router(),
        ledger=ledger,
    )
    runtime.transparent_shadow_engines = {"AAPL": _Candidate()}
    runtime._campaign_fingerprint = "frozen"
    event = QuoteEvent("AAPL", 1, 100.0, 100.01, 100, 100)
    runtime._process_transparent_shadow(event, None)
    runtime.transparent_shadow_engines = {"AAPL": _Candidate(fails=True)}
    runtime._process_transparent_shadow(event, None)
    runtime._record_transparent_shadow_summary(timestamp="2026-07-14T16:00:00+00:00")

    payload = ledger.recent_events(
        category="model", event_type="transparent_shadow_summary"
    )[0]["payload"]
    assert payload["candidate_update_count"] == 1
    assert payload["candidate_error_count"] == 1
    assert payload["routing_engine_version"] == "v1"
    assert payload["campaign_fingerprint"] == "frozen"
    assert len(runtime._shadow_candidate_latencies) <= 4096
    ledger.close()


def test_preflight_requires_validation_approved_transparent_shadow_bundle(tmp_path, monkeypatch) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    config = _config(
        tmp_path,
        artifact_root=artifact_root,
        transparent_shadow_run_ids={"AAPL": "v2"},
    )
    resolved: list[tuple[str, str, bool]] = []

    def resolve(_selector, *, symbol, run_id, passing_only):
        resolved.append((symbol, run_id, passing_only))
        return object()

    monkeypatch.setattr(
        "l1_microstructure.production.preflight.TransparentArtifactSelector.resolve",
        resolve,
    )
    report = ProductionPreflight(
        config,
        secret_lookup=lambda _name: "configured",
        artifact_validator=lambda _symbol, _run_id: None,
        broker_config_loader=lambda _path: IBKRConnectionConfig(paper_trading=True),
    ).run()

    check = next(item for item in report.checks if item.code == "artifact.transparent_shadow.aapl")
    assert check.status is PreflightStatus.PASSED
    assert resolved == [("AAPL", "v2", True)]
