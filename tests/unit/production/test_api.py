from __future__ import annotations

from fastapi.testclient import TestClient

from l1_microstructure.production.api import create_app


class _Ledger:
    def recent_events(self, limit):
        return [{"id": 1, "limit": limit}]


class _Runtime:
    def __init__(self):
        self.ledger = _Ledger()
        self.halt_reason = None

    def status(self):
        return {"lifecycle": "running"}

    def halt(self, reason):
        self.halt_reason = reason

    def recent_alerts(self, limit):
        return [{"code": "test_alert", "limit": limit}]


def test_control_api_requires_authentication_and_typed_confirmation() -> None:
    runtime = _Runtime()
    client = TestClient(create_app(runtime, "secret-token"))

    assert client.get("/health").status_code == 401
    headers = {"Authorization": "Bearer secret-token"}
    assert client.get("/health", headers=headers).json() == {"lifecycle": "running"}
    assert client.post("/control/halt", headers=headers, json={"reason": "test"}).status_code == 400

    response = client.post(
        "/control/halt",
        headers=headers,
        json={"reason": "test", "confirmation": "HALT"},
    )
    assert response.status_code == 200
    assert runtime.halt_reason == "test"


def test_control_api_exposes_authenticated_alert_history() -> None:
    client = TestClient(create_app(_Runtime(), "secret-token"))

    assert client.get("/alerts").status_code == 401
    response = client.get("/alerts?limit=999", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == 200
    assert response.json() == [{"code": "test_alert", "limit": 500}]
