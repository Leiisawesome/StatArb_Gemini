"""Terminal operations console for the localhost trading daemon."""

from __future__ import annotations

import argparse
import json
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from .secrets import get_secret


class ConfirmationScreen(ModalScreen[str | None]):
    def __init__(self, expected: str):
        super().__init__()
        self.expected = expected

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"Type {self.expected!r} to confirm")
            yield Input(id="confirmation")
            with Horizontal():
                yield Button("Confirm", id="confirm", variant="error")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        value = self.query_one("#confirmation", Input).value
        if value != self.expected:
            self.notify("Confirmation text does not match", severity="error")
            return
        self.dismiss(value)


class TradingConsole(App[None]):
    CSS = """
    #status { height: 5; padding: 1 2; }
    #controls { height: 3; }
    Button { margin: 0 1; }
    DataTable { height: 1fr; }
    """

    def __init__(self, base_url: str, token: str):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.last_status: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Connecting to trading daemon...", id="status")
        with Horizontal(id="controls"):
            yield Button("Pause", id="pause")
            yield Button("Resume", id="resume")
            yield Button("HALT", id="halt", variant="error")
            yield Button("Flatten", id="flatten", variant="warning")
        yield Label("Positions")
        yield DataTable(id="positions")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#positions", DataTable)
        table.add_columns("Symbol", "Side", "Quantity", "Entry")
        self.set_interval(1.0, self.refresh_status)
        self.refresh_status()

    def refresh_status(self) -> None:
        try:
            status = self._request("GET", "/health")
        except (HTTPError, URLError, ValueError) as exc:
            self.query_one("#status", Static).update(f"Daemon unavailable: {exc}")
            return
        self.last_status = status
        broker = status.get("broker", {})
        self.query_one("#status", Static).update(
            f"State: {status['lifecycle'].upper()}   Mode: {status['mode'].upper()}\n"
            f"Broker: {broker.get('status', 'unknown')}   Kill switch: {status['kill_switch']}   "
            f"Open orders: {len(status.get('open_orders', []))}"
        )
        table = self.query_one("#positions", DataTable)
        table.clear()
        for symbol, position in sorted(status.get("positions", {}).items()):
            side = position.get("side", "")
            if isinstance(side, dict):
                side = side.get("value", "")
            table.add_row(symbol, str(side), str(position.get("quantity", "")), str(position.get("entry_price", "")))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        command = event.button.id
        confirmations = {"halt": "HALT", "flatten": "FLATTEN"}
        if command in confirmations:
            self.push_screen(
                ConfirmationScreen(confirmations[command]),
                lambda confirmation: self._send_control(command, confirmation),
            )
            return
        self._send_control(command, None)

    def _send_control(self, command: str, confirmation: str | None) -> None:
        if confirmation is None and command in {"halt", "flatten"}:
            return
        payload = {"reason": "terminal console", "confirmation": confirmation}
        try:
            self._request("POST", f"/control/{command}", payload)
        except (HTTPError, URLError, ValueError) as exc:
            self.notify(str(exc), severity="error")
        self.refresh_status()

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        with urlopen(request, timeout=2) as response:
            return json.loads(response.read())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open the StatArb terminal trading console")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args(argv)
    token = get_secret("TRADING_CONSOLE_TOKEN")
    if not token:
        raise RuntimeError("TRADING_CONSOLE_TOKEN is missing from Keychain")
    TradingConsole(args.url, token).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
