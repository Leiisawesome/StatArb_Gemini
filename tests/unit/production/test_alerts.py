from __future__ import annotations

import subprocess

from l1_microstructure.monitoring import AlertCategory, AlertSeverity, OperationalAlertManager
from l1_microstructure.production.alerts import LedgerAlertStore, LocalAlertSink
from l1_microstructure.production.ledger import OperationalLedger


class _RecordingSink:
    def __init__(self) -> None:
        self.alerts = []

    def publish_alert(self, alert) -> None:
        self.alerts.append(alert)


class _FailingSink:
    def publish_alert(self, _alert) -> None:
        raise RuntimeError("notification service unavailable")


class _FailingStore:
    def append_alert(self, _alert) -> None:
        raise OSError("ledger unavailable")

    def append_delivery_failure(self, _failure) -> None:
        raise OSError("ledger unavailable")

    def load_recent_alerts(self, _limit):
        return []

    def load_delivery_diagnostics(self, _limit):
        return {"failure_count": 0, "recent_failures": []}


def test_local_notification_timeout_is_captured_as_delivery_failure(monkeypatch) -> None:
    def time_out(*_args, **_kwargs) -> None:
        raise subprocess.TimeoutExpired(cmd="osascript", timeout=5)

    monkeypatch.setattr("l1_microstructure.production.alerts.sys.platform", "darwin")
    monkeypatch.setattr("l1_microstructure.production.alerts.subprocess.run", time_out)
    manager = OperationalAlertManager(LocalAlertSink(), clock=lambda: 2_000)

    alert = manager.emit(
        AlertSeverity.CRITICAL,
        AlertCategory.BROKER_CONNECTIVITY,
        "broker_disconnected",
        "broker disconnected",
        timestamp_ns=1_000,
    )

    assert alert is not None
    assert manager.recent() == [alert]
    diagnostics = manager.delivery_diagnostics()
    assert diagnostics["failure_count"] == 1
    assert diagnostics["recent_failures"][0]["error_type"] == "TimeoutExpired"
    assert diagnostics["recent_failures"][0]["sink_type"] == "LocalAlertSink"


def test_alert_store_failure_does_not_prevent_history_or_delivery() -> None:
    sink = _RecordingSink()
    manager = OperationalAlertManager(sink, store=_FailingStore(), clock=lambda: 2_000)

    alert = manager.emit(
        AlertSeverity.ERROR,
        AlertCategory.RUNTIME,
        "audit_unavailable",
        "alert persistence unavailable",
        timestamp_ns=1_000,
    )

    assert alert is not None
    assert manager.recent() == [alert]
    assert sink.alerts == [alert]
    assert manager.persistence_diagnostics() == {
        "failure_count": 1,
        "recent_failures": [
            {
                "timestamp_ns": 2_000,
                "operation": "append_alert",
                "alert_key": "runtime:audit_unavailable:*",
                "store_type": "_FailingStore",
                "error_type": "OSError",
                "error": "ledger unavailable",
            }
        ],
    }


def test_alert_history_deduplication_and_delivery_failures_survive_restart(tmp_path) -> None:
    path = tmp_path / "runtime.sqlite3"
    ledger = OperationalLedger(path)
    manager = OperationalAlertManager(
        _FailingSink(),
        store=LedgerAlertStore(ledger),
        deduplication_window_ns=100,
        clock=lambda: 2_000,
    )
    first = manager.emit(
        AlertSeverity.CRITICAL,
        AlertCategory.BROKER_CONNECTIVITY,
        "broker_disconnected",
        "broker disconnected",
        symbol="AAPL",
        timestamp_ns=1_000,
    )
    assert first is not None
    ledger.close()

    reopened = OperationalLedger(path)
    sink = _RecordingSink()
    restored = OperationalAlertManager(
        sink,
        store=LedgerAlertStore(reopened),
        deduplication_window_ns=100,
        clock=lambda: 3_000,
    )

    assert restored.recent() == [first]
    assert sink.alerts == []
    assert restored.delivery_diagnostics()["failure_count"] == 1
    assert restored.delivery_diagnostics()["recent_failures"][0]["error_type"] == "RuntimeError"
    duplicate = restored.emit(
        AlertSeverity.CRITICAL,
        AlertCategory.BROKER_CONNECTIVITY,
        "broker_disconnected",
        "duplicate after restart",
        symbol="AAPL",
        timestamp_ns=1_050,
    )
    assert duplicate is None
    assert reopened.event_count(category="alert", event_type="operational_alert") == 1
    assert sink.alerts == []
    reopened.close()


def test_restored_alert_history_is_bounded_and_ordered(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "runtime.sqlite3")
    store = LedgerAlertStore(ledger)
    writer = OperationalAlertManager(_RecordingSink(), store=store, deduplication_window_ns=0)
    for timestamp_ns in (1, 2, 3):
        writer.emit(
            AlertSeverity.WARNING,
            AlertCategory.MARKET_DATA,
            f"market_data_{timestamp_ns}",
            f"market data alert {timestamp_ns}",
            timestamp_ns=timestamp_ns,
        )

    restored = OperationalAlertManager(_RecordingSink(), store=store, max_history=2)

    assert [alert.timestamp_ns for alert in restored.recent()] == [2, 3]
    ledger.close()


def test_malformed_persisted_alert_is_skipped_without_redelivery(tmp_path) -> None:
    ledger = OperationalLedger(tmp_path / "runtime.sqlite3")
    ledger.append_event(
        "alert",
        "operational_alert",
        {"timestamp_ns": "invalid", "severity": "critical", "category": "runtime"},
    )
    sink = _RecordingSink()

    manager = OperationalAlertManager(sink, store=LedgerAlertStore(ledger))

    assert manager.recent() == []
    assert sink.alerts == []
    assert manager.persistence_diagnostics()["failure_count"] == 0
    ledger.close()
