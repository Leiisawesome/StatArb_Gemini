"""Local incident notifications for the macOS workstation deployment."""

from __future__ import annotations

import subprocess
import sys
from time import time_ns

from l1_microstructure.monitoring import AlertCategory, AlertSeverity, OperationalAlert


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
