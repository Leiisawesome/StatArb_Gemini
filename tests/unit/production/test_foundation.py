from __future__ import annotations

from datetime import datetime, timezone
import json
import pickle

import pytest

from l1_microstructure.events import QuoteEvent
from l1_microstructure.live import RoutedExecutionService
from l1_microstructure.artifacts import LocalArtifactStore
from l1_microstructure.production.config import ModelQualityPolicy, OperatingMode, ProductionConfig
from l1_microstructure.production.ledger import OperationalLedger
from l1_microstructure.production.lifecycle import LifecycleState, RuntimeLifecycle
from l1_microstructure.production.runtime import ProductionRuntime


def _config(tmp_path, **overrides) -> ProductionConfig:
    values = {
        "symbols": ("aapl", "msft"),
        "artifact_root": tmp_path / "artifacts",
        "promoted_run_ids": {"AAPL": "aapl-v1", "MSFT": "msft-v1"},
        "database_path": tmp_path / "runtime.sqlite3",
        "event_stale_after_seconds": 60.0,
        "warmup_seconds": 0.0,
    }
    values.update(overrides)
    return ProductionConfig(**values)


def test_production_config_normalizes_symbols_and_requires_live_acknowledgement(tmp_path) -> None:
    config = _config(tmp_path)
    assert config.symbols == ("AAPL", "MSFT")

    with pytest.raises(ValueError, match="live capital risk acknowledgement"):
        _config(tmp_path, mode=OperatingMode.LIVE)


def test_production_config_rejects_missing_promoted_model(tmp_path) -> None:
    with pytest.raises(ValueError, match="missing promoted run ids"):
        _config(tmp_path, promoted_run_ids={"AAPL": "aapl-v1"})


def test_operational_ledger_persists_intents_events_and_state(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "runtime.sqlite3")
    client_order_id = ledger.record_order_intent({"symbol": "AAPL"}, "client-1")
    ledger.update_order(client_order_id, "accepted", external_order_id="42")
    ledger.append_event("order", "accepted", {"client_order_id": client_order_id})
    ledger.set_state("kill_switch", True)
    ledger.close()

    reopened = OperationalLedger(tmp_path / "runtime.sqlite3")
    assert reopened.open_orders()[0]["external_order_id"] == "42"
    assert reopened.get_state("kill_switch") is True
    assert reopened.recent_events()[0]["event_type"] == "accepted"
    reopened.close()


def test_legacy_artifact_migration_requires_explicit_trust(tmp_path) -> None:
    artifact_dir = tmp_path / "legacy"
    artifact_dir.mkdir()
    (artifact_dir / "metadata.json").write_text(
        json.dumps(
            {
                "artifact_id": "legacy",
                "artifact_type": "transition_model",
                "version": "v1",
                "created_at": "2026-01-01T00:00:00+00:00",
                "payload_format": "pickle",
            }
        ),
        encoding="utf-8",
    )
    (artifact_dir / "payload.pkl").write_bytes(pickle.dumps({"model_id": "legacy"}))
    store = LocalArtifactStore(tmp_path)

    with pytest.raises(ValueError, match="trusted=True"):
        store.migrate_legacy_pickle("legacy")

    store.migrate_legacy_pickle("legacy", trusted=True)
    assert store.load("legacy") == {"model_id": "legacy"}


def test_lifecycle_rejects_unsafe_transition() -> None:
    lifecycle = RuntimeLifecycle()
    with pytest.raises(ValueError, match="invalid lifecycle transition"):
        lifecycle.transition(LifecycleState.RUNNING, "skip reconciliation")


class _Source:
    def load_historical(self, request):
        return []

    def subscribe_live(self, request):
        return []


class _Router:
    def __init__(self, positions=None):
        self.requests = []
        self.positions = positions or {}

    def health_check(self):
        return {"connected": True, "status": "healthy", "net_liquidation": 100_000.0}

    def reconciliation_snapshot(self):
        return {**self.health_check(), "positions": self.positions, "open_order_ids": []}

    def open_order_ids(self):
        return []

    def cancel(self, order_id):
        return True

    def submit(self, request):
        self.requests.append(request)
        raise AssertionError("test runtime should not submit an order")

    def poll(self, symbols):
        return []

    def stop(self):
        return None


class _Machine:
    def __init__(self):
        self.events = []
        self.open_positions = {}
        self.previous_state = None

    def on_event(self, event):
        self.events.append(event)
        return None


class _Runtime(ProductionRuntime):
    def _load_machines(self) -> None:
        self.machines = {symbol: _Machine() for symbol in self.config.symbols}


class _Alerts:
    def __init__(self):
        self.messages = []

    def critical(self, title, message):
        self.messages.append((title, message))


def test_production_runtime_isolates_symbol_engines(tmp_path) -> None:
    runtime = _Runtime(_config(tmp_path), source=_Source(), router=_Router())
    assert isinstance(runtime.execution_service, RoutedExecutionService)
    runtime.start()
    timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
    runtime.process_event(QuoteEvent("AAPL", timestamp_ns, 100.0, 100.01, 100, 100))

    assert len(runtime.machines["AAPL"].events) == 1
    assert runtime.machines["MSFT"].events == []
    assert runtime.lifecycle.state is LifecycleState.RUNNING
    runtime.stop()


def test_production_runtime_halts_on_position_reconciliation_mismatch(tmp_path) -> None:
    alerts = _Alerts()
    router = _Router({"AAPL": {"quantity": 10, "average_cost": 100.0}})
    runtime = _Runtime(_config(tmp_path), source=_Source(), router=router, alert_sink=alerts)

    runtime.start()

    assert runtime.lifecycle.state is LifecycleState.HALTED
    assert "position reconciliation mismatch" in alerts.messages[0][1]
    runtime.stop()


def test_production_runtime_requires_each_symbol_to_finish_warmup(tmp_path) -> None:
    runtime = _Runtime(_config(tmp_path, warmup_seconds=1.0), source=_Source(), router=_Router())
    runtime.start()
    assert runtime.lifecycle.state is LifecycleState.WARMING
    timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
    for symbol in ("AAPL", "MSFT"):
        runtime.process_event(QuoteEvent(symbol, timestamp_ns, 100.0, 100.01, 100, 100))
        runtime.process_event(QuoteEvent(symbol, timestamp_ns + 2_000_000_000, 100.0, 100.01, 100, 100))

    assert runtime.lifecycle.state is LifecycleState.RUNNING
    runtime.stop()


def test_production_runtime_rejects_router_without_safety_capabilities(tmp_path) -> None:
    class IncompleteRouter:
        def submit(self, request):
            return None

        def poll(self, symbols):
            return []

        def stop(self):
            return None

    with pytest.raises(TypeError, match="missing required capabilities"):
        _Runtime(_config(tmp_path), source=_Source(), router=IncompleteRouter())


def test_production_config_validates_model_quality_policy(tmp_path) -> None:
    with pytest.raises(ValueError, match="minimum_fill_rate"):
        _config(tmp_path, model_quality=ModelQualityPolicy(minimum_fill_rate=1.1))


def test_production_promotion_requires_passing_quality_gate(tmp_path, monkeypatch) -> None:
    calls = []

    def resolve_passing(self, *, symbol, run_id, quality_gate):
        calls.append((symbol, run_id, quality_gate))
        return object()

    monkeypatch.setattr(
        "l1_microstructure.production.runtime.ArtifactBundleSelector.resolve_passing_by_run_id", resolve_passing
    )
    runtime = _Runtime(
        _config(tmp_path, model_quality=ModelQualityPolicy(minimum_fill_rate=0.5)),
        source=_Source(),
        router=_Router(),
    )

    runtime.promote_model("AAPL", "approved-run")

    assert calls[0][0:2] == ("AAPL", "approved-run")
    assert calls[0][2].minimum_fill_rate == 0.5
    assert runtime.promoted_run_ids["AAPL"] == "approved-run"
