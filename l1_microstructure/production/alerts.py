"""Local incident notifications for the macOS workstation deployment."""

from __future__ import annotations

import subprocess
import sys
from time import time_ns

from l1_microstructure.monitoring import AlertCategory, AlertSeverity, OperationalAlert

from .ledger import OperationalLedger


class LedgerAlertStore:
    def __init__(self, ledger: OperationalLedger) -> None:
        self.ledger = ledger

    def append_alert(self, alert: OperationalAlert) -> None:
        self.ledger.append_event("alert", "operational_alert", alert.to_dict())

    def append_delivery_failure(self, failure: dict) -> None:
        self.ledger.append_event("alert", "delivery_failure", failure)

    def load_recent_alerts(self, limit: int) -> list[OperationalAlert]:
        events = self.ledger.recent_events(limit, category="alert", event_type="operational_alert")
        alerts: list[OperationalAlert] = []
        for event in reversed(events):
            try:
                alerts.append(self._decode_alert(event["payload"]))
            except (KeyError, TypeError, ValueError):
                continue
        return alerts

    def load_delivery_diagnostics(self, limit: int) -> dict:
        events = self.ledger.recent_events(limit, category="alert", event_type="delivery_failure")
        failures = [dict(event["payload"]) for event in reversed(events) if isinstance(event["payload"], dict)]
        return {
            "failure_count": self.ledger.event_count(category="alert", event_type="delivery_failure"),
            "recent_failures": failures,
        }

    @staticmethod
    def _decode_alert(payload: dict) -> OperationalAlert:
        code = str(payload["code"]).strip()
        message = str(payload["message"]).strip()
        if not code or not message:
            raise ValueError("persisted alert requires a code and message")
        symbol = payload.get("symbol")
        return OperationalAlert(
            timestamp_ns=int(payload["timestamp_ns"]),
            severity=AlertSeverity(payload["severity"]),
            category=AlertCategory(payload["category"]),
            code=code,
            message=message,
            symbol=None if symbol is None else str(symbol),
            metadata=dict(payload.get("metadata", {})),
        )


class LocalAlertSink:
    def publish_alert(self, alert: OperationalAlert) -> None:
        title = f"{alert.severity.value.upper()} {alert.code.replace('_', ' ')}"
        self._notify(title, alert.message, critical=alert.severity is AlertSeverity.CRITICAL)

    def critical(self, title: str, message: str) -> None:
        self.publish_alert(
            OperationalAlert(
                timestamp_ns=time_ns(),
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.RUNTIME,
                code="runtime_halted",
                message=f"{title}: {message}",
            )
        )

    @staticmethod
    def _notify(title: str, message: str, *, critical: bool) -> None:
        safe_title = title.replace('"', "'")
        safe_message = message.replace('"', "'")
        if sys.platform == "darwin":
            sound = ' sound name "Basso"' if critical else ""
            script = f'display notification "{safe_message}" with title "{safe_title}"{sound}'
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
        else:
            bell = "\a" if critical else ""
            sys.stderr.write(f"{bell}{title}: {message}\n")
