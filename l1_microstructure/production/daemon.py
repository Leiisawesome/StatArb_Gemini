"""Production daemon entrypoint."""

from __future__ import annotations

import argparse
from threading import Thread
from typing import Sequence

import uvicorn

from l1_microstructure.ingest import MassiveWebSocketConfig, MassiveWebSocketDataSource
from l1_microstructure.live import IBKRBrokerOrderRouter

from .api import create_app
from .config import ProductionConfig
from .runtime import ProductionRuntime
from .secrets import get_secret


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the supervised StatArb trading daemon")
    parser.add_argument("--config", required=True, help="production JSON configuration")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ProductionConfig.from_json(args.config)
    massive_key = get_secret("MASSIVE_API_KEY")
    api_token = get_secret("TRADING_CONSOLE_TOKEN")
    if not massive_key:
        raise RuntimeError("MASSIVE_API_KEY is missing from Keychain")
    if not api_token:
        raise RuntimeError("TRADING_CONSOLE_TOKEN is missing from Keychain")
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


if __name__ == "__main__":
    raise SystemExit(main())
