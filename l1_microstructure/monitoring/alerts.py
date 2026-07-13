"""Operational alert publication with bounded history and deduplication."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from threading import Lock, RLock
from time import time_ns
from typing import Any

from .interfaces import AlertCategory, AlertSeverity, OperationalAlert


class OperationalAlertManager:
    def __init__(
        self,
        sink: Any | None = None,
        *,
        deduplication_window_ns: int = 60_000_000_000,
        max_history: int = 500,
        clock: Callable[[], int] = time_ns,
    ) -> None:
        if deduplication_window_ns < 0:
            raise ValueError("alert deduplication window cannot be negative")
        if max_history <= 0:
            raise ValueError("alert history size must be positive")
        self.sink = sink
        self.deduplication_window_ns = deduplication_window_ns
        self._clock = clock
        self._alerts: deque[OperationalAlert] = deque(maxlen=max_history)
        self._delivery_failures: deque[dict[str, Any]] = deque(maxlen=max_history)
        self._delivery_failure_count = 0
        self._last_emitted_ns: dict[str, int] = {}
        self._lock = RLock()
        self._delivery_lock = Lock()

    def emit(
        self,
        severity: AlertSeverity,
        category: AlertCategory,
        code: str,
        message: str,
        *,
        symbol: str | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp_ns: int | None = None,
    ) -> OperationalAlert | None:
        if not code.strip() or not message.strip():
            raise ValueError("operational alerts require a code and message")
        alert = OperationalAlert(
            timestamp_ns=self._clock() if timestamp_ns is None else int(timestamp_ns),
            severity=severity,
            category=category,
            code=code.strip(),
            message=message.strip(),
            symbol=symbol,
            metadata=dict(metadata or {}),
        )
        with self._lock:
            previous = self._last_emitted_ns.get(alert.deduplication_key)
            if previous is not None and alert.timestamp_ns - previous < self.deduplication_window_ns:
                return None
            self._last_emitted_ns[alert.deduplication_key] = alert.timestamp_ns
            self._alerts.append(alert)
        try:
            with self._delivery_lock:
                self._deliver(alert)
        except Exception as exc:
            self._record_delivery_failure(alert, exc)
        return alert

    def recent(self, limit: int = 100) -> list[OperationalAlert]:
        bounded = min(max(int(limit), 1), self._alerts.maxlen or 500)
        with self._lock:
            return list(self._alerts)[-bounded:]

    def recent_dicts(self, limit: int = 100) -> list[dict[str, Any]]:
        return [alert.to_dict() for alert in self.recent(limit)]

    def delivery_diagnostics(self, limit: int = 20) -> dict[str, Any]:
        bounded = min(max(int(limit), 1), self._delivery_failures.maxlen or 500)
        with self._lock:
            return {
                "failure_count": self._delivery_failure_count,
                "recent_failures": list(self._delivery_failures)[-bounded:],
            }

    def _deliver(self, alert: OperationalAlert) -> None:
        publish_alert = getattr(self.sink, "publish_alert", None)
        if callable(publish_alert):
            publish_alert(alert)
            return
        critical = getattr(self.sink, "critical", None)
        if callable(critical) and alert.severity is AlertSeverity.CRITICAL:
            critical(alert.code.replace("_", " ").title(), alert.message)

    def _record_delivery_failure(self, alert: OperationalAlert, error: Exception) -> None:
        failure = {
            "timestamp_ns": self._clock(),
            "alert_timestamp_ns": alert.timestamp_ns,
            "alert_key": alert.deduplication_key,
            "sink_type": type(self.sink).__name__,
            "error_type": type(error).__name__,
            "error": str(error),
        }
        with self._lock:
            self._delivery_failure_count += 1
            self._delivery_failures.append(failure)
