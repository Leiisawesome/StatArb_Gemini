#!/usr/bin/env python3
"""
Live Paper Trading Runner
========================

Wires:
PolygonDataService (delayed) -> PolygonToDispatcherBridge -> DeterministicEventDispatcher
-> PaperTradingEngine -> UnifiedExecutionEngine(LIVE) -> IBKRAdapter (paper)

Safe-by-default:
- Config `enable_orders: false` by default
- CLI `--enable-orders` required to actually submit orders
- Env `LIVEPAPER_KILL_SWITCH=1` hard-disables orders
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

from core_engine.paper.engine import PaperTradingEngine, PaperTradingConfig
from core_engine.system.time_source import TimeSourceFactory
from core_engine.system.event_dispatcher import DeterministicEventDispatcher
from core_engine.system.event_journal import EventJournal
from core_engine.system.paper_state_manager import PaperSessionStateManager
from core_engine.system.paper_watchdog import PaperTradingWatchdog
from core_engine.system.idempotency import IdGenerator, IdempotencyTracker
from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.system.session_gate import TradingSessionGate
from core_engine.system.risk_budget import RiskBudgetState
from core_engine.system.order_management_system import OrderManagementSystem
from core_engine.system.unified_execution_engine import UnifiedExecutionEngine

from core_engine.data.validation.streaming_validator import StreamingDataValidator
from core_engine.processing.streaming.buffer_manager import StreamingBufferManager
from core_engine.processing.streaming.adapters import StreamingIndicatorAdapter, StreamingFeatureAdapter
from core_engine.processing.signals.streaming_manager import StreamingSignalManager, BarPolicy
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import EnhancedFeatureEngineer
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.trading.strategies.manager import StrategyManager
from core_engine.trading.position_book import PositionBook, Fill

from core_engine.config.broker_config import InteractiveBrokersConfig
from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter

from core_engine.data.feeds.polygon_integration import PolygonDataService, PolygonServiceConfig

from livepapertest.utils.config_loader import load_yaml
from livepapertest.engine.polygon_live_bridge import PolygonToDispatcherBridge
from livepapertest.engine.polygon_rest_warmup_adapter import PolygonRestWarmupAdapter, PolygonWarmupConfig
from livepapertest.broker.ibkr_paper_facade import LivePaperBrokerFacade
from livepapertest.execution.execution_gate import ExecutionGate, ExecutionGateConfig
from livepapertest.execution.gated_unified_execution_engine import GatedUnifiedExecutionEngine
from livepapertest.execution.risk_manager_position_callback import RiskManagerPositionCallback
from livepapertest.ops.reconciler import IBKRReconciler, TradingPauseFlag
from livepapertest.ops.health import HealthReporter

logger = logging.getLogger(__name__)


def _default_config_path() -> str:
    return str(Path(__file__).parent / "configs" / "live_paper.yaml")


def _get_cfg(root: Dict[str, Any]) -> Dict[str, Any]:
    if "livepapertest" not in root or not isinstance(root["livepapertest"], dict):
        raise ValueError("Config must contain top-level key: livepapertest")
    return root["livepapertest"]


def _bootstrap_position_book_from_ibkr(account_cash: float, positions: List[Any]) -> PositionBook:
    """
    Bootstrap internal PositionBook from IBKR snapshot.

    We choose initial_cash such that after replaying synthetic fills at avg_cost,
    the resulting cash matches IBKR cash:
      cash_after = initial_cash - long_cost + short_proceeds = ib_cash
      => initial_cash = ib_cash + long_cost - short_proceeds
    """
    long_cost = 0.0
    short_proceeds = 0.0
    for p in positions or []:
        try:
            qty = float(getattr(p, "quantity", 0.0) or 0.0)
            px = float(getattr(p, "avg_entry_price", 0.0) or 0.0)
            if qty > 0:
                long_cost += qty * px
            elif qty < 0:
                short_proceeds += abs(qty) * px
        except Exception:
            continue

    initial_cash = float(account_cash) + float(long_cost) - float(short_proceeds)
    book = PositionBook(initial_cash=Decimal(str(initial_cash)))

    now = datetime.now(timezone.utc)
    for p in positions or []:
        sym = str(getattr(p, "symbol", "") or "").upper()
        qty = float(getattr(p, "quantity", 0.0) or 0.0)
        px = float(getattr(p, "avg_entry_price", 0.0) or 0.0)
        if not sym or qty == 0 or px <= 0:
            continue
        side = "buy" if qty > 0 else "sell"
        fill = Fill.create(symbol=sym, side=side, quantity=abs(qty), price=px, commission=0.0, timestamp=now, order_id="bootstrap")
        book.on_fill(fill)

    return book


async def _connect_ibkr(cfg: Dict[str, Any]) -> IBKRAdapter:
    ib = cfg["ibkr"]
    ib_cfg = InteractiveBrokersConfig(
        host=str(ib["host"]),
        port=int(ib["port"]),
        client_id=int(ib["client_id"]),
        account_id=ib.get("account_id"),
        paper_trading=bool(ib.get("paper_trading", True)),
    )
    adapter = IBKRAdapter(ib_cfg)
    ok = await asyncio.to_thread(adapter.connect)
    if not ok:
        raise RuntimeError("Failed to connect to IBKR")
    return adapter


async def _create_polygon_service(cfg: Dict[str, Any]) -> PolygonDataService:
    p = cfg["polygon"]
    api_key = os.getenv("POLYGON_API_KEY", "")
    ps_cfg = PolygonServiceConfig(
        api_key=api_key,
        symbols=[str(s).upper() for s in p["symbols"]],
        data_types=list(p.get("data_types", ["minute_agg", "trade"])),
        use_delayed=bool(p.get("use_delayed", True)),
        name="livepapertest-polygon",
    )
    svc = PolygonDataService(config=ps_cfg)
    if not await svc.initialize():
        raise RuntimeError("Failed to initialize PolygonDataService")
    return svc


async def main_async(args: argparse.Namespace) -> None:
    root = load_yaml(args.config)
    cfg = _get_cfg(root)

    # Basic logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Load universe from artifact if provided
    if args.universe_file:
        logger.info(f"Loading universe from {args.universe_file}")
        try:
            with open(args.universe_file, 'r') as f:
                artifact = json.load(f)
                # Schema: { "symbols": { "SYM": {...} }, "regime": ... }
                if "symbols" in artifact and isinstance(artifact["symbols"], dict):
                    loaded_symbols = list(artifact["symbols"].keys())
                    # Override config symbols
                    cfg["polygon"]["symbols"] = loaded_symbols
                    logger.info(f"Overridden symbols from artifact: {len(loaded_symbols)} found")
                    
                    if "regime" in artifact:
                        regime_info = artifact["regime"]
                        regime_label = regime_info.get("primary") if isinstance(regime_info, dict) else regime_info
                        logger.info(f"Artifact Regime: {regime_label}")
                else:
                    logger.warning("Artifact missing 'symbols' dictionary, using config default.")
        except Exception as e:
            logger.error(f"Failed to load universe file: {e}")
            raise

    symbols = [str(s).upper() for s in cfg["polygon"]["symbols"]]
    if not symbols:
        raise ValueError("polygon.symbols must be non-empty")

    logger.info("Starting livepapertest runner")
    logger.info(f"Symbols: {symbols}")

    # Build engine config
    sess = cfg.get("session", {})
    buffers_cfg = cfg.get("buffers", {})
    dispatcher_cfg = cfg.get("dispatcher", {})
    risk_cfg = cfg.get("risk", {})
    exec_cfg = cfg.get("execution", {})
    strategies_cfg = cfg.get("strategies", [])

    paper_cfg = PaperTradingConfig(
        session_id="",  # allow engine to generate
        buffer_size=int(buffers_cfg.get("size", 500)),
        warmup_required=int(buffers_cfg.get("warmup_required", 200)),
        checkpoint_interval_bars=int(sess.get("checkpoint_interval_bars", 1000)),
        checkpoint_dir=str(sess.get("checkpoint_dir", "livepapertest/results/checkpoints")),
        journal_dir=str(sess.get("journal_dir", "livepapertest/results/journals")),
        daily_risk_budget_pct=float(risk_cfg.get("daily_risk_budget_pct", 0.01)),
        per_trade_risk_pct=float(risk_cfg.get("per_trade_risk_pct", 0.005)),
        initial_cash=float(exec_cfg.get("initial_cash", 100_000.0)),
        commission_per_share=float(exec_cfg.get("commission_per_share", 0.005)),
        stall_threshold_seconds=float(sess.get("stall_threshold_seconds", 60.0)),
        enable_eod_liquidation=False,
        eod_close_time=str(exec_cfg.get("eod_close_time", "15:55")),
    )

    engine = PaperTradingEngine(paper_cfg)

    # Deterministic IDs
    session_prefix = str(sess.get("id_prefix", "lp"))
    id_gen = IdGenerator("livepapertest", f"{session_prefix}:{engine._session_id}")
    id_tracker = IdempotencyTracker(max_history=200_000)

    # Time + dispatcher
    time_source = TimeSourceFactory.create_live()
    dispatcher = DeterministicEventDispatcher(
        time_source=time_source,
        max_queue_size=int(dispatcher_cfg.get("max_queue_size", 20000)),
        bar_queue_size=int(dispatcher_cfg.get("bar_queue_size", 5000)),
        conflate_quotes=bool(dispatcher_cfg.get("conflate_quotes", True)),
    )

    # Core processing components
    validator = StreamingDataValidator()
    buffer_manager = StreamingBufferManager(
        buffer_size=int(buffers_cfg.get("size", 500)),
        warmup_required=int(buffers_cfg.get("warmup_required", 200)),
    )
    indicator_adapter = StreamingIndicatorAdapter(EnhancedTechnicalIndicators())
    feature_adapter = StreamingFeatureAdapter(EnhancedFeatureEngineer())
    signal_manager = StreamingSignalManager(bar_policy=BarPolicy(), session_id=engine._session_id)
    regime_engine = EnhancedRegimeEngine({})
    strategy_manager = StrategyManager(config={}, data_config=None)
    session_gate = TradingSessionGate()
    risk_budget = RiskBudgetState(
        daily_risk_budget_pct=float(risk_cfg.get("daily_risk_budget_pct", 0.01)),
        per_trade_risk_pct=float(risk_cfg.get("per_trade_risk_pct", 0.005)),
    )
    oms = OrderManagementSystem({})

    risk_manager = CentralRiskManager(
        {
            "allow_shorts": bool(risk_cfg.get("allow_shorts", False)),
            "min_signal_confidence": float(risk_cfg.get("min_signal_confidence", 0.60)),
            "max_position_size": float(risk_cfg.get("max_position_size", 0.10)),
            "max_position_pct": float(risk_cfg.get("max_position_pct", 0.05)),
            "max_positions": int(risk_cfg.get("max_positions", 5)),
            "position_concentration_limit": float(risk_cfg.get("position_concentration_limit", 0.15)),
            "initial_capital": float(exec_cfg.get("initial_cash", 100_000.0)),
        }
    )
    risk_manager.set_session_gate(session_gate)
    risk_manager.set_risk_budget(risk_budget)
    risk_manager.set_oms(oms)

    strategy_manager.set_regime_engine(regime_engine)
    strategy_manager.set_risk_manager(risk_manager)

    # Ops: journal/state/watchdog
    journal = EventJournal(
        session_id=engine._session_id,
        output_dir=str(paper_cfg.journal_dir),
        compress=bool(sess.get("journal_compress", False)),
    )
    state_mgr = PaperSessionStateManager(
        session_id=engine._session_id,
        checkpoint_dir=paper_cfg.checkpoint_dir,
        checkpoint_interval_bars=paper_cfg.checkpoint_interval_bars,
    )
    watchdog = PaperTradingWatchdog(stall_threshold_seconds=paper_cfg.stall_threshold_seconds)

    # Connect IBKR + bootstrap PositionBook from IB snapshot
    ibkr = await _connect_ibkr(cfg)
    acct = await asyncio.to_thread(ibkr.get_account_info)
    positions = await asyncio.to_thread(ibkr.get_positions)
    position_book = _bootstrap_position_book_from_ibkr(acct.cash, positions)
    risk_manager.set_position_book(position_book)

    # Broker facade used by the engine for pricing + snapshots (no order submission here)
    facade = LivePaperBrokerFacade(ibkr=ibkr, position_book=position_book)
    # Prime caches
    await asyncio.to_thread(facade.refresh_account_info)
    await asyncio.to_thread(facade.refresh_positions)

    # Execution engine (LIVE), with gating + journaling
    uee = UnifiedExecutionEngine(
        {
            "test_mode": False,
            "enable_position_tracking": True,
            "ibkr_fill_timeout_seconds": float(exec_cfg.get("ibkr_fill_timeout_seconds", 30.0)),
            "ibkr_poll_interval_seconds": float(exec_cfg.get("ibkr_poll_interval_seconds", 0.25)),
        }
    )
    uee.set_live_broker(ibkr)
    uee.set_execution_mode("LIVE")
    # Use UEE position callback to update PositionBook via RiskManager and journal fills
    uee.set_position_callbacks(risk_manager_callback=RiskManagerPositionCallback(risk_manager=risk_manager, journal=journal))

    enable_orders_config = bool(exec_cfg.get("enable_orders", False))
    enable_orders_cli = bool(args.enable_orders) and (not bool(args.dry_run))
    max_price_age = float(exec_cfg.get("max_price_age_seconds_block_orders", 3600.0))
    pause_flag = TradingPauseFlag(paused=False, reason="")
    gate = ExecutionGate(
        ExecutionGateConfig(
            enable_orders_config=enable_orders_config,
            enable_orders_cli=enable_orders_cli,
            should_block_orders=lambda sym: pause_flag.paused or ((facade.get_price_age_seconds(sym) or 1e9) > max_price_age),
        )
    )
    gated_uee = GatedUnifiedExecutionEngine(inner=uee, gate=gate, journal=journal)

    # Wire into engine
    engine.setup_time_source(time_source)
    engine.setup_dispatcher(dispatcher)
    engine.setup_data_validator(validator)
    engine.setup_buffer_manager(buffer_manager)
    engine.setup_indicator_adapter(indicator_adapter)
    engine.setup_feature_adapter(feature_adapter)
    engine.setup_signal_manager(signal_manager)
    engine.setup_regime_engine(regime_engine)
    engine.setup_session_gate(session_gate)
    engine.setup_risk_manager(risk_manager)
    engine.setup_risk_budget(risk_budget)
    engine.setup_paper_broker(facade)
    engine.setup_execution_engine(gated_uee)
    engine.setup_event_journal(journal)
    engine.setup_state_manager(state_mgr)
    engine.setup_idempotency_tracker(id_tracker)
    engine.setup_watchdog(watchdog)
    engine.setup_position_book(position_book)
    engine.setup_oms(oms)
    engine.setup_strategy_manager(strategy_manager)

    # Warmup: REST adapter implements get_warmup_data so engine.warmup works
    warm_cfg = cfg["polygon"].get("warmup", {})
    warmup_adapter = PolygonRestWarmupAdapter(
        PolygonWarmupConfig(
            timeframe=str(warm_cfg.get("timeframe", "1min")),
            warmup_days_max=int(warm_cfg.get("warmup_days_max", 10)),
        )
    )
    engine.setup_replay_adapter(warmup_adapter)

    # Load strategies
    for s in strategies_cfg or []:
        try:
            await strategy_manager.add_strategy(dict(s))
        except Exception as e:
            logger.error(f"Failed to add strategy {s.get('name')}: {e}")

    # Polygon service + bridge
    polygon = await _create_polygon_service(cfg)
    bridge = PolygonToDispatcherBridge(dispatcher=dispatcher, id_generator=id_gen)
    polygon.add_bar_callback(bridge.on_bar)
    polygon.add_trade_callback(bridge.on_trade)

    # Initialize engine
    if not await engine.initialize():
        raise RuntimeError("PaperTradingEngine initialization failed")

    # Warmup buffers and set WS cutoff per symbol
    ok = await engine.warmup(symbols)
    if not ok:
        raise RuntimeError("Warmup failed")
    for sym in symbols:
        last_ts = warmup_adapter.last_warmup_timestamp(sym)
        if last_ts is not None:
            bridge.set_min_source_timestamp(last_ts, symbol=sym)

    # Start Polygon WS
    if not await polygon.start():
        raise RuntimeError("Failed to start PolygonDataService")

    logger.info(f"Orders enabled (two-key): {gate.orders_enabled()} (config={enable_orders_config}, cli={enable_orders_cli})")
    if gate.is_kill_switch_active():
        logger.warning("LIVEPAPER_KILL_SWITCH is active: orders are blocked")

    # Reconciliation loop (External SSOT -> Internal SSOT convergence checks)
    rec_cfg = cfg.get("reconcile", {})
    reconciler = IBKRReconciler(
        facade=facade,
        position_book=position_book,
        journal=journal,
        pause_on_mismatch=bool(rec_cfg.get("pause_on_mismatch", True)),
        pause_flag=pause_flag,
    )
    reconcile_task = asyncio.create_task(reconciler.run_positions_loop(float(rec_cfg.get("positions_interval_sec", 15.0))))

    # Periodic health logging (1/min by default)
    ops_cfg = cfg.get("ops", {})
    reporter = HealthReporter(
        engine=engine,
        symbols=symbols,
        facade=facade,
        position_book=position_book,
        bridge=bridge,
        journal=journal,
        polygon_service=polygon,
        ibkr_adapter=ibkr,
    )
    health_task = asyncio.create_task(reporter.run(float(ops_cfg.get("health_log_interval_sec", 60.0))))

    # Run engine (until cancelled)
    try:
        await engine.run()
    finally:
        try:
            reconcile_task.cancel()
        except Exception:
            pass
        try:
            health_task.cancel()
        except Exception:
            pass
        try:
            await polygon.stop()
        except Exception:
            pass
        try:
            await warmup_adapter.close()
        except Exception:
            pass
        try:
            await asyncio.to_thread(ibkr.disconnect)
        except Exception:
            pass


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run live paper trading (Polygon delayed -> IBKR paper).")
    p.add_argument("--config", type=str, default=_default_config_path(), help="Path to YAML config")
    p.add_argument("--universe-file", type=str, help="Path to universe JSON artifact from picker")
    p.add_argument("--enable-orders", action="store_true", help="Second key: allow real order submission")
    p.add_argument("--dry-run", action="store_true", help="Force no-order mode (signals/risk still run)")
    return p


def main() -> None:
    load_dotenv()
    args = build_arg_parser().parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()


