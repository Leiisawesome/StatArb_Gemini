from __future__ import annotations

from fastapi.testclient import TestClient

from l1_microstructure.production.api import create_app
from l1_microstructure.production.readiness import (
    OperationalCheck,
    RuntimeHealthReport,
    RuntimeReadinessReport,
)


class _Ledger:
    def recent_events(self, limit):
        return [{"id": 1, "limit": limit}]


class _Runtime:
    def __init__(self):
        self.ledger = _Ledger()
        self.halt_reason = None
        self.ready = False
        self.degraded = False

    def status(self):
        return {"lifecycle": "running"}

    def health_report(self):
        return RuntimeHealthReport.from_checks(
            123,
            (OperationalCheck("daemon.responding", True, "daemon is responding"),),
        )

    def readiness_report(self):
        checks = [OperationalCheck("runtime.ready", self.ready, "runtime readiness")]
        if self.degraded:
            checks.append(OperationalCheck("alerts.delivery", False, "notification failure", required=False))
        return RuntimeReadinessReport.from_checks(
            123,
            "running",
            tuple(checks),
        )

    def halt(self, reason):
        self.halt_reason = reason

    def recent_alerts(self, limit):
        return [{"code": "test_alert", "limit": limit}]


def test_control_api_requires_authentication_and_typed_confirmation() -> None:
    runtime = _Runtime()
    client = TestClient(create_app(runtime, "secret-token"))

    assert client.get("/health").status_code == 401
    headers = {"Authorization": "Bearer secret-token"}
    health = client.get("/health", headers=headers)
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert health.json()["alive"] is True
    assert client.get("/status", headers=headers).json() == {"lifecycle": "running"}
    assert client.post("/control/halt", headers=headers, json={"reason": "test"}).status_code == 400

    response = client.post(
        "/control/halt",
        headers=headers,
        json={"reason": "test", "confirmation": "HALT"},
    )
    assert response.status_code == 200
    assert runtime.halt_reason == "test"


def test_control_api_uses_stable_readiness_status_codes() -> None:
    runtime = _Runtime()
    client = TestClient(create_app(runtime, "secret-token"))
    headers = {"Authorization": "Bearer secret-token"}

    assert client.get("/ready").status_code == 401
    not_ready = client.get("/ready", headers=headers)
    assert not_ready.status_code == 503
    assert not_ready.json()["status"] == "not_ready"
    assert not_ready.json()["ready"] is False

    runtime.ready = True
    ready = client.get("/ready", headers=headers)
    assert ready.status_code == 200
    assert ready.json()["status"] == "healthy"
    assert ready.json()["ready"] is True

    runtime.degraded = True
    degraded = client.get("/ready", headers=headers)
    assert degraded.status_code == 200
    assert degraded.json()["status"] == "degraded"
    assert degraded.json()["ready"] is True


def test_control_api_exposes_authenticated_alert_history() -> None:
    client = TestClient(create_app(_Runtime(), "secret-token"))

    assert client.get("/alerts").status_code == 401
    response = client.get("/alerts?limit=999", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == 200
    assert response.json() == [{"code": "test_alert", "limit": 500}]
