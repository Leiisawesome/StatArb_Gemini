from __future__ import annotations

from datetime import datetime, timezone
import json
import pickle
from types import SimpleNamespace

import pytest

from l1_microstructure.events import QuoteEvent
from l1_microstructure.ingest.interfaces import LiveSubscriptionRequest
from l1_microstructure.live import RouteAcknowledgement, RoutedExecutionService
from l1_microstructure.monitoring import AlertCategory, AlertSeverity
from l1_microstructure.artifacts import LocalArtifactStore
from l1_microstructure.production.config import (
    InfrastructureRetryPolicies,
    ModelQualityPolicy,
    OperatingMode,
    ProductionConfig,
)
from l1_microstructure.production.ledger import OperationalLedger
from l1_microstructure.production.lifecycle import LifecycleState, RuntimeLifecycle
from l1_microstructure.production.runtime import ProductionRuntime
from l1_microstructure.retry import RetryPolicy


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


def test_production_config_loads_partial_operation_specific_retry_policy(tmp_path) -> None:
    path = tmp_path / "production.json"
    path.write_text(
        json.dumps(
            {
                "symbols": ["AAPL"],
                "artifact_root": str(tmp_path / "artifacts"),
                "promoted_run_ids": {"AAPL": "aapl-v1"},
                "database_path": str(tmp_path / "runtime.sqlite3"),
                "retry": {"market_data": {"max_attempts": 7}},
            }
        ),
        encoding="utf-8",
    )

    config = ProductionConfig.from_json(path)

    assert config.retry.market_data.max_attempts == 7
    assert config.retry.market_data.initial_delay_seconds == 1.0
    assert config.retry.broker_connection.initial_delay_seconds == 0.5
    assert config.public_dict()["retry"]["market_data"]["max_attempts"] == 7


def _retry_policies(*, max_attempts: int = 3) -> InfrastructureRetryPolicies:
    return InfrastructureRetryPolicies(
        market_data=RetryPolicy(
            max_attempts=max_attempts,
            initial_delay_seconds=1.0,
            maximum_delay_seconds=2.0,
        )
    )


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
    assert reopened.recent_events(category="order", event_type="accepted")[0]["payload"] == {
        "client_order_id": "client-1"
    }
    assert reopened.event_count(category="order", event_type="accepted") == 1
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


class _TransientMarketDataSource(_Source):
    def __init__(self, failures: list[Exception]) -> None:
        self.failures = list(failures)
        self.calls = 0
        self.runtime = None

    def subscribe_live(self, request):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        self.runtime._shutdown = True
        return []


class _Alerts:
    def __init__(self):
        self.messages = []

    def critical(self, title, message):
        self.messages.append((title, message))


class _FailingAlerts:
    def critical(self, _title, _message):
        raise RuntimeError("notification service unavailable")


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


def test_production_runtime_reports_healthy_liveness_and_readiness(tmp_path) -> None:
    runtime = _Runtime(_config(tmp_path), source=_Source(), router=_Router())
    runtime.start()
    timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
    for symbol in runtime.config.symbols:
        runtime.process_event(QuoteEvent(symbol, timestamp_ns, 100.0, 100.01, 100, 100))

    health = runtime.health_report(timestamp_ns=timestamp_ns)
    readiness = runtime.readiness_report(timestamp_ns=timestamp_ns)

    assert health.status.value == "healthy"
    assert health.alive is True
    assert readiness.status.value == "healthy"
    assert readiness.ready is True
    assert all(check.passed for check in readiness.checks)
    runtime.stop()


def test_production_readiness_reports_partial_multi_symbol_warmup(tmp_path) -> None:
    runtime = _Runtime(_config(tmp_path, warmup_seconds=1.0), source=_Source(), router=_Router())
    runtime.start()
    timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
    runtime.process_event(QuoteEvent("AAPL", timestamp_ns, 100.0, 100.01, 100, 100))
    runtime.process_event(QuoteEvent("AAPL", timestamp_ns + 2_000_000_000, 100.0, 100.01, 100, 100))

    report = runtime.readiness_report(timestamp_ns=timestamp_ns + 2_000_000_000)
    checks = {check.code: check for check in report.checks}

    assert report.ready is False
    assert report.status.value == "not_ready"
    assert checks["runtime.lifecycle_running"].passed is False
    assert checks["market_data.fresh"].details["missing_symbols"] == ["MSFT"]
    assert checks["market_data.warmup_complete"].details["incomplete_symbols"] == ["MSFT"]
    runtime.stop()


def test_production_readiness_detects_stale_data_and_kill_switch(tmp_path) -> None:
    runtime = _Runtime(_config(tmp_path, event_stale_after_seconds=1.0), source=_Source(), router=_Router())
    runtime.start()
    timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
    for symbol in runtime.config.symbols:
        runtime.process_event(QuoteEvent(symbol, timestamp_ns, 100.0, 100.01, 100, 100))
    runtime.ledger.set_state("kill_switch", True)

    report = runtime.readiness_report(timestamp_ns=timestamp_ns + 2_000_000_000)
    checks = {check.code: check for check in report.checks}

    assert report.ready is False
    assert checks["safety.kill_switch_clear"].passed is False
    assert checks["market_data.fresh"].details["stale_symbols"] == ["AAPL", "MSFT"]
    runtime.stop()


def test_market_data_subscription_retries_and_records_recovery(tmp_path) -> None:
    waits: list[float] = []
    source = _TransientMarketDataSource([TimeoutError("one"), ConnectionError("two")])
    runtime = _Runtime(
        _config(tmp_path, retry=_retry_policies()),
        source=source,
        router=_Router(),
        wait=waits.append,
        retry_random_source=lambda: 0.5,
    )
    source.runtime = runtime
    runtime.start()

    result = runtime._run_market_data_cycle(LiveSubscriptionRequest(symbols=runtime.config.symbols))

    assert result.succeeded is True
    assert result.attempts == 3
    assert source.calls == 3
    assert waits == [1.0, 2.0]
    assert runtime.recent_alerts()[0]["code"] == "market_data_retry_recovered"
    retry_events = [
        event for event in runtime.ledger.recent_events() if event["event_type"] == "market_data_subscription"
    ]
    assert retry_events[0]["payload"]["attempts"] == 3
    runtime.stop()


def test_market_data_retry_exhaustion_halts_with_attempt_metadata(tmp_path) -> None:
    waits: list[float] = []
    source = _TransientMarketDataSource([TimeoutError("one"), TimeoutError("two"), TimeoutError("three")])
    runtime = _Runtime(
        _config(tmp_path, retry=_retry_policies()),
        source=source,
        router=_Router(),
        wait=waits.append,
        retry_random_source=lambda: 0.5,
    )
    source.runtime = runtime
    runtime.start()

    result = runtime._run_market_data_cycle(LiveSubscriptionRequest(symbols=runtime.config.symbols))

    assert result.succeeded is False
    assert result.attempts == 3
    assert waits == [1.0, 2.0]
    assert runtime.lifecycle.state is LifecycleState.HALTED
    alert = runtime.recent_alerts()[0]
    assert alert["code"] == "market_data_retry_exhausted"
    assert alert["metadata"]["attempts"] == 3
    runtime.stop()


def test_market_data_permission_failure_is_not_retried(tmp_path) -> None:
    waits: list[float] = []
    source = _TransientMarketDataSource([PermissionError("invalid API entitlement")])
    runtime = _Runtime(
        _config(tmp_path, retry=_retry_policies()),
        source=source,
        router=_Router(),
        wait=waits.append,
    )
    source.runtime = runtime
    runtime.start()

    result = runtime._run_market_data_cycle(LiveSubscriptionRequest(symbols=runtime.config.symbols))

    assert result.succeeded is False
    assert result.attempts == 1
    assert source.calls == 1
    assert waits == []
    assert result.final_failure is not None
    assert result.final_failure.retryable is False
    runtime.stop()


def test_production_runtime_halts_on_position_reconciliation_mismatch(tmp_path) -> None:
    alerts = _Alerts()
    router = _Router({"AAPL": {"quantity": 10, "average_cost": 100.0}})
    runtime = _Runtime(_config(tmp_path), source=_Source(), router=router, alert_sink=alerts)

    runtime.start()

    assert runtime.lifecycle.state is LifecycleState.HALTED
    assert "position reconciliation mismatch" in alerts.messages[0][1]
    assert runtime.recent_alerts()[0]["category"] == "reconciliation"
    assert runtime.recent_alerts()[0]["code"] == "reconciliation_failed"
    runtime.stop()


def test_production_runtime_surfaces_nonfatal_alert_delivery_failure(tmp_path) -> None:
    router = _Router({"AAPL": {"quantity": 10, "average_cost": 100.0}})
    runtime = _Runtime(_config(tmp_path), source=_Source(), router=router, alert_sink=_FailingAlerts())

    runtime.start()

    status = runtime.status()
    assert status["lifecycle"] == "halted"
    assert status["alerts"][0]["code"] == "reconciliation_failed"
    assert status["alert_delivery"]["failure_count"] == 1
    failure = status["alert_delivery"]["recent_failures"][0]
    assert failure["alert_key"] == "reconciliation:reconciliation_failed:*"
    assert failure["error_type"] == "RuntimeError"
    health = runtime.health_report()
    assert health.alive is True
    assert health.status.value == "degraded"
    assert {check.code: check for check in health.checks}["alerts.delivery"].passed is False
    runtime.stop()


def test_production_readiness_remains_eligible_but_degraded_after_notification_failure(tmp_path) -> None:
    runtime = _Runtime(_config(tmp_path), source=_Source(), router=_Router(), alert_sink=_FailingAlerts())
    runtime.start()
    timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
    for symbol in runtime.config.symbols:
        runtime.process_event(QuoteEvent(symbol, timestamp_ns, 100.0, 100.01, 100, 100))
    runtime.alerts.emit(
        AlertSeverity.CRITICAL,
        AlertCategory.RUNTIME,
        "notification_test",
        "notification test",
        timestamp_ns=timestamp_ns,
    )

    report = runtime.readiness_report(timestamp_ns=timestamp_ns)
    delivery = {check.code: check for check in report.checks}["alerts.delivery"]

    assert report.ready is True
    assert report.status.value == "degraded"
    assert delivery.required is False
    assert delivery.passed is False
    runtime.stop()


def test_production_runtime_categorizes_broker_disconnect(tmp_path) -> None:
    class DisconnectedRouter(_Router):
        def health_check(self):
            return {"connected": False, "status": "disconnected", "error": "gateway unavailable"}

    alerts = _Alerts()
    runtime = _Runtime(_config(tmp_path), source=_Source(), router=DisconnectedRouter(), alert_sink=alerts)

    runtime.start()

    alert = runtime.recent_alerts()[0]
    assert alert["category"] == "broker_connectivity"
    assert alert["code"] == "broker_disconnected"
    readiness = runtime.readiness_report()
    checks = {check.code: check for check in readiness.checks}
    assert readiness.ready is False
    assert checks["broker.connected"].passed is False
    assert checks["broker.reconciled"].passed is False
    runtime.stop()


def test_production_readiness_detects_post_start_reconciliation_mismatch(tmp_path) -> None:
    router = _Router()
    runtime = _Runtime(_config(tmp_path), source=_Source(), router=router)
    runtime.start()
    timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
    for symbol in runtime.config.symbols:
        runtime.process_event(QuoteEvent(symbol, timestamp_ns, 100.0, 100.01, 100, 100))
    router.positions = {"AAPL": {"quantity": 10, "average_cost": 100.0}}

    report = runtime.readiness_report(timestamp_ns=timestamp_ns)
    reconciliation = {check.code: check for check in report.checks}["broker.reconciled"]

    assert report.ready is False
    assert reconciliation.passed is False
    assert reconciliation.message == "position does not reconcile for AAPL"
    runtime.stop()


def test_production_runtime_surfaces_broker_retry_exhaustion_metadata(tmp_path) -> None:
    class RetryExhaustedRouter(_Router):
        def reconciliation_snapshot(self):
            return {
                "connected": False,
                "status": "reconciliation_retry_exhausted",
                "error": "operation failed after 3 attempts",
                "retry": {
                    "reconciliation": {
                        "succeeded": False,
                        "attempts": 3,
                        "failures": [
                            {
                                "attempt": 3,
                                "timestamp_ns": 123,
                                "error_type": "TimeoutError",
                                "error": "account summary delayed",
                                "retryable": True,
                                "will_retry": False,
                                "delay_seconds": 0.0,
                            }
                        ],
                    }
                },
            }

    runtime = _Runtime(_config(tmp_path), source=_Source(), router=RetryExhaustedRouter())

    runtime.start()

    alert = runtime.recent_alerts()[0]
    assert alert["code"] == "broker_retry_exhausted"
    assert alert["metadata"]["retry"]["reconciliation"]["attempts"] == 3
    retry_event = next(event for event in runtime.ledger.recent_events() if event["category"] == "retry")
    assert retry_event["event_type"] == "broker_reconciliation"
    assert retry_event["payload"]["attempts"] == 3
    incident = next(event for event in runtime.ledger.recent_events() if event["event_type"] == "runtime_halted")
    assert incident["payload"]["alert"]["metadata"]["retry"]["reconciliation"]["attempts"] == 3
    runtime.stop()


def test_production_runtime_emits_typed_stale_data_alert(tmp_path) -> None:
    runtime = _Runtime(_config(tmp_path, event_stale_after_seconds=1.0), source=_Source(), router=_Router())
    runtime.start()

    runtime.process_event(QuoteEvent("AAPL", 1, 100.0, 100.01, 100, 100))

    assert runtime.lifecycle.state is LifecycleState.HALTED
    alert = runtime.recent_alerts()[0]
    assert alert["category"] == "market_data"
    assert alert["code"] == "stale_market_data"
    assert alert["symbol"] == "AAPL"
    runtime.stop()


def test_production_runtime_emits_typed_strategy_risk_halt(tmp_path) -> None:
    runtime = _Runtime(_config(tmp_path), source=_Source(), router=_Router())
    runtime.start()
    runtime.machines["AAPL"].risk_engine = SimpleNamespace(halted=True)
    timestamp_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)

    runtime.process_event(QuoteEvent("AAPL", timestamp_ns, 100.0, 100.01, 100, 100))

    assert runtime.lifecycle.state is LifecycleState.HALTED
    alert = runtime.recent_alerts()[0]
    assert alert["category"] == "risk"
    assert alert["code"] == "strategy_risk_halt"
    runtime.stop()


def test_production_runtime_emits_typed_order_rejection_alert(tmp_path) -> None:
    class RejectingRouter(_Router):
        def submit(self, request):
            self.requests.append(request)
            return RouteAcknowledgement(
                external_order_id="rejected-1",
                status="rejected",
                reason="broker risk check failed",
            )

    runtime = _Runtime(_config(tmp_path), source=_Source(), router=RejectingRouter())
    runtime.start()
    request = SimpleNamespace(
        symbol="AAPL",
        action=SimpleNamespace(value="buy"),
        quantity=1,
        decision_timestamp_ns=1,
        client_order_id="client-1",
    )

    runtime._route(request)

    assert runtime.lifecycle.state is LifecycleState.HALTED
    alert = runtime.recent_alerts()[0]
    assert alert["category"] == "order_routing"
    assert alert["code"] == "order_rejected"
    assert alert["symbol"] == "AAPL"
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
