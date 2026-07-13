"""Production daemon entrypoint."""

from __future__ import annotations

import argparse
import json
from threading import Thread
from typing import Sequence, cast

import uvicorn

from l1_microstructure.ingest import MassiveWebSocketConfig, MassiveWebSocketDataSource
from l1_microstructure.live import IBKRBrokerOrderRouter

from .api import create_app
from .config import ProductionConfig
from .preflight import (
    PreflightCheck,
    PreflightStatus,
    ProductionPreflight,
    ProductionPreflightReport,
)
from .runtime import ProductionRuntime
from .secrets import get_secret


PREFLIGHT_SUCCESS_EXIT_CODE = 0
PREFLIGHT_FAILURE_EXIT_CODE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the supervised StatArb trading daemon")
    parser.add_argument("--config", required=True, help="production JSON configuration")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="print a redacted JSON preflight report without constructing runtime infrastructure",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = ProductionConfig.from_json(args.config)
    except Exception as exc:
        if not args.preflight:
            raise
        report = _configuration_failure_report(exc)
        print(json.dumps(report.to_dict(), sort_keys=True))
        return PREFLIGHT_FAILURE_EXIT_CODE

    report, secrets = _run_preflight(config)
    if args.preflight:
        print(json.dumps(report.to_dict(), sort_keys=True))
        return PREFLIGHT_SUCCESS_EXIT_CODE if report.passed else PREFLIGHT_FAILURE_EXIT_CODE

    report.raise_for_failure()
    massive_key = cast(str, secrets["MASSIVE_API_KEY"])
    api_token = cast(str, secrets["TRADING_CONSOLE_TOKEN"])
    source = MassiveWebSocketDataSource(MassiveWebSocketConfig(api_key=massive_key))
    router = IBKRBrokerOrderRouter.from_env(
        str(config.broker_env_file) if config.broker_env_file else None,
        prefer_limit_orders=True,
        require_paper=config.mode.value == "paper",
        connection_retry_policy=config.retry.broker_connection,
        read_retry_policy=config.retry.broker_read,
    )
    runtime = ProductionRuntime(config, source=source, router=router)
    runtime_thread = Thread(target=runtime.run, name="production-runtime", daemon=True)
    runtime_thread.start()
    app = create_app(runtime, api_token)
    try:
        uvicorn.run(app, host=config.api_host, port=config.api_port, log_level="info")
    finally:
        runtime.stop()
        runtime_thread.join(timeout=10)
    return 0


def _run_preflight(config: ProductionConfig) -> tuple[ProductionPreflightReport, dict[str, str | None]]:
    values: dict[str, str | None] = {}
    errors: dict[str, Exception] = {}

    def lookup(name: str) -> str | None:
        if name in errors:
            raise errors[name]
        if name not in values:
            try:
                values[name] = get_secret(name)
            except Exception as exc:
                errors[name] = exc
                raise
        return values[name]

    return ProductionPreflight(config, secret_lookup=lookup).run(), values


def _configuration_failure_report(error: Exception) -> ProductionPreflightReport:
    return ProductionPreflightReport(
        checks=(
            PreflightCheck(
                code="runtime.configuration",
                status=PreflightStatus.FAILED,
                message="production configuration could not be loaded",
                metadata={"error_type": type(error).__name__},
            ),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
