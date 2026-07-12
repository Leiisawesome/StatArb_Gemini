"""Local incident notifications for the macOS workstation deployment."""

from __future__ import annotations

import subprocess
import sys


class LocalAlertSink:
    def critical(self, title: str, message: str) -> None:
        safe_title = title.replace('"', "'")
        safe_message = message.replace('"', "'")
        if sys.platform == "darwin":
            script = f'display notification "{safe_message}" with title "{safe_title}" sound name "Basso"'
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
        else:
            sys.stderr.write(f"\aCRITICAL {title}: {message}\n")
