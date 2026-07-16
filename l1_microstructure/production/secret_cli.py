"""Interactive Keychain secret management."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import getpass
import json
from secrets import token_urlsafe
from typing import Sequence
from zoneinfo import ZoneInfo

from l1_microstructure.ingest import HistoricalBatchRequest, MassiveRESTConfig, MassiveRESTDataSource

from .secrets import get_secret, set_secret


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage StatArb Gemini secrets in the system keyring")
    parser.add_argument("name", choices=("MASSIVE_API_KEY", "TRADING_CONSOLE_TOKEN"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report whether the secret exists")
    mode.add_argument(
        "--generate",
        action="store_true",
        help="generate and store a random local console token without displaying it",
    )
    mode.add_argument(
        "--validate",
        action="store_true",
        help="verify the stored Massive credential with a bounded read-only request",
    )
    args = parser.parse_args(argv)
    if args.check:
        print("configured" if get_secret(args.name, allow_environment=False) else "missing")
        return 0
    if args.generate:
        if args.name != "TRADING_CONSOLE_TOKEN":
            parser.error("--generate is only valid for TRADING_CONSOLE_TOKEN")
        set_secret(args.name, token_urlsafe(32))
        print("generated and stored TRADING_CONSOLE_TOKEN in the system keyring")
        return 0
    if args.validate:
        if args.name != "MASSIVE_API_KEY":
            parser.error("--validate is only valid for MASSIVE_API_KEY")
        value = get_secret(args.name)
        if not value:
            print("MASSIVE_API_KEY validation failed: no credential is configured")
            return 2
        try:
            _validate_massive_api_key(value)
        except Exception as exc:
            print(f"MASSIVE_API_KEY validation failed: {_massive_failure_code(exc)}")
            return 2
        print("MASSIVE_API_KEY validation passed with a bounded read-only market-data request")
        return 0
    value = getpass.getpass(f"{args.name}: ")
    set_secret(args.name, value)
    print(f"stored {args.name} in the system keyring")
    return 0


def _validate_massive_api_key(api_key: str) -> None:
    eastern = ZoneInfo("America/New_York")

    def timestamp_ns(hour: int, minute: int, second: int) -> int:
        value = datetime(2024, 3, 11, hour, minute, second, tzinfo=eastern)
        return int(value.timestamp() * 1_000_000_000)

    events = list(
        MassiveRESTDataSource(MassiveRESTConfig(api_key=api_key)).load_historical(
            HistoricalBatchRequest(
                symbols=("AAPL",),
                trade_date=date(2024, 3, 11),
                include_quotes=True,
                include_trades=False,
                start_ns=timestamp_ns(9, 30, 0),
                end_ns=timestamp_ns(9, 30, 5),
            )
        )
    )
    if not events:
        raise RuntimeError("bounded Massive validation returned no events")


def _massive_failure_code(exc: Exception) -> str:
    try:
        from massive.exceptions import AuthError, BadResponse
    except ImportError:
        AuthError = BadResponse = ()  # type: ignore[assignment,misc]
    if isinstance(exc, AuthError):
        return "credential_missing_or_invalid"
    if isinstance(exc, BadResponse):
        try:
            payload = json.loads(str(exc))
        except (TypeError, ValueError):
            payload = {}
        diagnostic = " ".join(
            str(payload.get(key, "")) for key in ("status", "error", "message")
        ).lower()
        if any(marker in diagnostic for marker in ("api key", "authentication", "invalid key")):
            return "credential_rejected"
        if any(
            marker in diagnostic
            for marker in ("not authorized", "not_authorized", "entitl", "subscription", "upgrade")
        ):
            return "data_entitlement_missing"
        return "vendor_request_rejected"
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return "network_or_timeout_failure"
    return f"request_failed_{type(exc).__name__}"


if __name__ == "__main__":
    raise SystemExit(main())
