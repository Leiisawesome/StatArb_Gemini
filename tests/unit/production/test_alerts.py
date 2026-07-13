from __future__ import annotations

import subprocess

from l1_microstructure.monitoring import AlertCategory, AlertSeverity, OperationalAlertManager
from l1_microstructure.production.alerts import LocalAlertSink


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
