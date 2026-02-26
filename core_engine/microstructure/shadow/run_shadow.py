"""Step 9: Shadow Trading Runner — live integration entry point.

Wires together:
  Polygon WebSocket (trades + quotes)
    → LiquidityShadowEngine.on_trade() / on_quote()
    → OrderManager  ← IBKRAdapter.submit_limit_order / cancel_order
    → MechanismMonitor → ShadowLogger → ClickHouse

Lifecycle:
  1. Load config from YAML (env-var substitution for secrets)
  2. Pre-flight checks (ClickHouse, NTP, IBKR connectivity)
  3. Connect Polygon WebSocket + IBKR
  4. Run until market close, then run_daily_close()
  5. Graceful shutdown on SIGINT/SIGTERM

Spec: v1.8-SHADOW-SHOCK
Build Plan: v3-FINAL, Step 9
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

load_dotenv()

from core_engine.microstructure.shadow.constants import (
    SHADOW_CONSTANTS_VERSION,
    SYMBOLS,
)
from core_engine.microstructure.shadow.engine import LiquidityShadowEngine
from core_engine.microstructure.shadow.types import ShadowConfig

logger = logging.getLogger("shadow_runner")
ET = ZoneInfo("America/New_York")

_NON_REGULAR_CONDITIONS = frozenset({2, 7, 10, 15, 16, 21, 22, 29, 33, 38})


# =====================================================================
# Config loading
# =====================================================================

def _env_substitute(value: str) -> str:
    """Replace ${VAR} and ${VAR:-default} patterns with env vars."""
    def _repl(m):
        var = m.group(1)
        default = m.group(3)
        return os.environ.get(var, default if default is not None else "")
    return re.sub(r"\$\{(\w+)(:-(.*?))?\}", _repl, value)


def load_config(path: str) -> ShadowConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)

    polygon_key = _env_substitute(raw["polygon"]["api_key"])
    if not polygon_key:
        polygon_key = os.environ.get("POLYGON_API_KEY", "")

    ibkr_host = _env_substitute(raw["ibkr"].get("host", "127.0.0.1"))

    return ShadowConfig(
        polygon_api_key=polygon_key,
        ibkr_host=ibkr_host,
        ibkr_port=raw["ibkr"].get("port", 4002),
        ibkr_client_id=raw["ibkr"].get("client_id", 10),
        clickhouse_url=raw["clickhouse"].get("url", "http://localhost:8123"),
        clickhouse_db=raw["clickhouse"].get("db", "shadow_trading"),
        portfolio_value=raw["portfolio"].get("value", 200_000.0),
        state_log_path=raw["paths"].get("state_log", "data/shadow_state.json"),
        baselines_path=raw["paths"].get("baselines", "results/shadow_backtest/baselines.json"),
    )


# =====================================================================
# Polygon WebSocket bridge
# =====================================================================

class PolygonBridge:
    """Connects Polygon WebSocket feed to LiquidityShadowEngine."""

    def __init__(self, engine: LiquidityShadowEngine, api_key: str):
        self._engine = engine
        self._api_key = api_key
        self._adapter = None
        self._trade_count = 0
        self._quote_count = 0

    async def connect(self) -> bool:
        from core_engine.data.feeds.polygon_realtime import (
            PolygonFeedConfig,
            PolygonRealtimeFeedAdapter,
            PolygonSubscriptionTier,
        )

        config = PolygonFeedConfig(
            api_key=self._api_key,
            symbols=list(SYMBOLS),
            subscription_tier=PolygonSubscriptionTier.ADVANCED,
            data_types=["trade", "quote"],
        )
        self._adapter = PolygonRealtimeFeedAdapter(config)
        self._adapter.add_message_handler(self._on_message)

        ok = await self._adapter.connect()
        if not ok:
            logger.error("Polygon WebSocket connection failed")
            return False

        ok = await self._adapter.subscribe(list(SYMBOLS), ["trade", "quote"])
        if not ok:
            logger.error("Polygon subscription failed")
            return False

        logger.info("Polygon WebSocket connected, subscribed to %s", SYMBOLS)
        return True

    def _on_message(self, msg) -> None:
        """Route FeedMessage to engine.on_trade() or engine.on_quote()."""
        if msg.symbol not in SYMBOLS:
            return

        if msg.message_type == "trade":
            data = msg.data
            conditions = data.get("conditions", [])
            if conditions and _NON_REGULAR_CONDITIONS.intersection(conditions):
                return

            ts_ns = int(msg.timestamp.timestamp() * 1_000_000_000)
            price = data.get("price", 0.0)
            size = data.get("size", 0)
            if price > 0 and size > 0:
                self._engine.on_trade(msg.symbol, ts_ns, price, size)
                self._trade_count += 1

        elif msg.message_type == "quote":
            data = msg.data
            ts_ns = int(msg.timestamp.timestamp() * 1_000_000_000)
            bid = data.get("bid", data.get("bid_price", 0.0))
            ask = data.get("ask", data.get("ask_price", 0.0))
            bid_sz = data.get("bid_size", 0)
            ask_sz = data.get("ask_size", 0)
            if bid > 0 and ask > bid:
                self._engine.on_quote(msg.symbol, ts_ns, bid, ask, bid_sz, ask_sz)
                self._quote_count += 1

    async def disconnect(self) -> None:
        if self._adapter:
            await self._adapter.disconnect()
            logger.info(
                "Polygon disconnected (trades=%d, quotes=%d)",
                self._trade_count, self._quote_count,
            )

    @property
    def stats(self):
        return {"trades": self._trade_count, "quotes": self._quote_count}


# =====================================================================
# IBKR bridge
# =====================================================================

class IBKRBridge:
    """Connects IBKRAdapter to the shadow OrderManager."""

    def __init__(self, engine: LiquidityShadowEngine, host: str, port: int, client_id: int):
        self._engine = engine
        self._host = host
        self._port = port
        self._client_id = client_id
        self._adapter = None
        self._connected = False

    async def connect(self) -> bool:
        try:
            from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter
            from core_engine.config.broker_config import InteractiveBrokersConfig
        except ImportError:
            logger.warning("IBKRAdapter not available — running in simulation-only mode")
            return False

        try:
            ibkr_config = InteractiveBrokersConfig(
                host=self._host,
                port=self._port,
                client_id=self._client_id,
                paper_trading=True,
            )
            self._adapter = IBKRAdapter(ibkr_config)
            connected = await self._adapter.connect(
                host=self._host,
                port=self._port,
                client_id=self._client_id,
            )
            if not connected:
                logger.error("IBKR connection failed (host=%s, port=%d)", self._host, self._port)
                return False

            self._connected = True
            logger.info("IBKR connected (host=%s, port=%d, paper mode)", self._host, self._port)
            return True

        except Exception as e:
            logger.error("IBKR connection error: %s", e)
            return False

    def broker_submit(
        self, symbol: str, side: str, size: int, limit_price: float, order_id: str,
    ) -> None:
        """Called by OrderManager.place_order() to submit to IBKR."""
        if not self._connected or not self._adapter:
            logger.debug("IBKR not connected — order %s logged but not submitted", order_id)
            return

        async def _submit():
            try:
                from core_engine.type_definitions.broker import OrderSide
                ibkr_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
                await self._adapter.submit_limit_order(
                    symbol=symbol,
                    quantity=float(size),
                    side=ibkr_side,
                    limit_price=limit_price,
                )
                logger.info("IBKR order submitted: %s %s %d @ %.4f", symbol, side, size, limit_price)
            except Exception as e:
                logger.error("IBKR submit failed for %s: %s", order_id, e)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_submit())
        except RuntimeError:
            logger.warning("No event loop for IBKR submit — order %s not sent", order_id)

    def broker_cancel(self, order_id: str) -> None:
        """Called by OrderManager crash recovery to cancel stale orders."""
        if not self._connected or not self._adapter:
            return

        async def _cancel():
            try:
                await self._adapter.cancel_order(order_id)
                logger.info("IBKR cancel requested: %s", order_id)
            except Exception as e:
                logger.error("IBKR cancel failed for %s: %s", order_id, e)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_cancel())
        except RuntimeError:
            pass

    async def disconnect(self) -> None:
        if self._adapter and self._connected:
            try:
                await self._adapter.cancel_all_orders()
                logger.info("IBKR: cancelled all open orders")
            except Exception as e:
                logger.warning("IBKR cancel-all failed: %s", e)
            try:
                await self._adapter.disconnect()
            except Exception:
                pass
            self._connected = False
            logger.info("IBKR disconnected")


# =====================================================================
# Market hours scheduler
# =====================================================================

class MarketScheduler:
    """Schedules engine start, daily close, and shutdown around market hours."""

    def __init__(self, start: str = "09:45", close: str = "15:45", shutdown: str = "16:00"):
        h, m = start.split(":")
        self._start_h, self._start_m = int(h), int(m)
        h, m = close.split(":")
        self._close_h, self._close_m = int(h), int(m)
        h, m = shutdown.split(":")
        self._shutdown_h, self._shutdown_m = int(h), int(m)

    def _now_et(self) -> datetime:
        return datetime.now(ET)

    def _today_at(self, h: int, m: int) -> datetime:
        return self._now_et().replace(hour=h, minute=m, second=0, microsecond=0)

    @property
    def market_open(self) -> datetime:
        return self._today_at(self._start_h, self._start_m)

    @property
    def market_close(self) -> datetime:
        return self._today_at(self._close_h, self._close_m)

    @property
    def shutdown_time(self) -> datetime:
        return self._today_at(self._shutdown_h, self._shutdown_m)

    def seconds_until_open(self) -> float:
        return max(0.0, (self.market_open - self._now_et()).total_seconds())

    def seconds_until_close(self) -> float:
        return max(0.0, (self.market_close - self._now_et()).total_seconds())

    def is_market_open(self) -> bool:
        now = self._now_et()
        return self.market_open <= now <= self.market_close

    def is_past_shutdown(self) -> bool:
        return self._now_et() >= self.shutdown_time


# =====================================================================
# Main runner
# =====================================================================

class ShadowRunner:
    """Top-level orchestrator for a single trading day."""

    def __init__(self, config: ShadowConfig):
        self._config = config
        self._engine = LiquidityShadowEngine(config)
        self._polygon = PolygonBridge(self._engine, config.polygon_api_key)
        self._ibkr = IBKRBridge(
            self._engine, config.ibkr_host, config.ibkr_port, config.ibkr_client_id,
        )
        self._scheduler = MarketScheduler()
        self._shutdown_event = asyncio.Event()

    async def run(self) -> None:
        logger.info(
            "Shadow Runner starting — spec %s, symbols=%s",
            SHADOW_CONSTANTS_VERSION, list(SYMBOLS),
        )

        # Wire IBKR callbacks into OrderManager
        self._engine._order_manager._broker_submit = self._ibkr.broker_submit
        self._engine._order_manager._broker_cancel = self._ibkr.broker_cancel

        # Pre-flight
        ok = await self._engine.initialize()
        if not ok:
            logger.error("Pre-flight checks FAILED — aborting")
            return

        # Connect data sources
        polygon_ok = await self._polygon.connect()
        if not polygon_ok:
            logger.error("Polygon connection FAILED — aborting")
            return

        ibkr_ok = await self._ibkr.connect()
        if not ibkr_ok:
            logger.warning(
                "IBKR not connected — running in OBSERVATION mode "
                "(events detected + logged, no orders submitted)"
            )

        # Wait for market open
        wait_s = self._scheduler.seconds_until_open()
        if wait_s > 0:
            logger.info("Waiting %.0f seconds for market open at %s ET", wait_s, self._scheduler.market_open.strftime("%H:%M"))
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=wait_s)
                if self._shutdown_event.is_set():
                    logger.info("Shutdown requested before market open")
                    await self._cleanup()
                    return
            except asyncio.TimeoutError:
                pass

        # Start engine
        await self._engine.start()
        logger.info("Engine started — processing live data")

        # Run until market close or shutdown signal
        try:
            await self._run_session()
        except Exception as e:
            logger.exception("Unhandled error in session: %s", e)
        finally:
            await self._cleanup()

    async def _run_session(self) -> None:
        """Main session loop: heartbeat every 30s, daily close at scheduled time."""
        heartbeat_interval = 30
        last_heartbeat = time.time()

        while not self._shutdown_event.is_set():
            now = time.time()

            if self._scheduler.is_past_shutdown():
                logger.info("Past shutdown time — stopping")
                break

            if now - last_heartbeat >= heartbeat_interval:
                stats = self._polygon.stats
                logger.info(
                    "Heartbeat: trades=%d quotes=%d engine=%s paused=%s",
                    stats["trades"], stats["quotes"],
                    "running" if self._engine.is_running else "stopped",
                    self._engine.is_paused,
                )
                last_heartbeat = now

            close_secs = self._scheduler.seconds_until_close()
            if close_secs <= 0 and self._engine.is_running:
                logger.info("Market close — running daily close procedures")
                await self._engine.run_daily_close()
                logger.info("Daily close complete")
                break

            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=min(heartbeat_interval, max(1, close_secs)),
                )
                if self._shutdown_event.is_set():
                    logger.info("Shutdown signal received during session")
                    break
            except asyncio.TimeoutError:
                pass

    async def _cleanup(self) -> None:
        logger.info("Cleanup: stopping engine and disconnecting")
        await self._engine.stop()
        await self._polygon.disconnect()
        await self._ibkr.disconnect()
        logger.info("Cleanup complete")

    def request_shutdown(self) -> None:
        self._shutdown_event.set()


# =====================================================================
# Entry point
# =====================================================================

def _setup_logging() -> None:
    fmt = (
        f"%(asctime)s [{SHADOW_CONSTANTS_VERSION}] "
        "%(levelname)s %(name)s: %(message)s"
    )
    log_dir = Path("results/shadow_daily")
    log_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(ET).strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(log_dir / f"shadow_{today}.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(fmt))

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)


async def async_main(config_path: str) -> None:
    config = load_config(config_path)
    runner = ShadowRunner(config)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, runner.request_shutdown)

    await runner.run()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Shadow Trading Runner — Step 9")
    parser.add_argument(
        "--config", default="configs/shadow_config.yaml",
        help="Path to shadow config YAML",
    )
    parser.add_argument(
        "--preflight-only", action="store_true",
        help="Run pre-flight checks only, then exit",
    )
    args = parser.parse_args()

    _setup_logging()
    logger.info("=" * 60)
    logger.info("SHADOW TRADING RUNNER — %s", SHADOW_CONSTANTS_VERSION)
    logger.info("Config: %s", args.config)
    logger.info("=" * 60)

    if args.preflight_only:
        async def _preflight():
            config = load_config(args.config)
            engine = LiquidityShadowEngine(config)
            ok = await engine.initialize()
            await engine.stop()
            if ok:
                logger.info("PRE-FLIGHT: ALL PASSED")
            else:
                logger.error("PRE-FLIGHT: FAILED")
                sys.exit(1)
        asyncio.run(_preflight())
    else:
        asyncio.run(async_main(args.config))


if __name__ == "__main__":
    main()
