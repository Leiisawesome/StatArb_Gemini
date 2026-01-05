"""
PapertestEngine
===============

Thin orchestration wrapper around core_engine.paper.PaperTradingEngine.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, List
import time as _time
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import json

from core_engine.data.replay.engine import ReplayStatus

from papertest.engine.component_factory import ComponentFactory, WiredPaperSystem
from papertest.engine.replay_bridge import ReplayToDispatcherBridge
from papertest.utils.config_loader import parse_debug_timestamps

logger = logging.getLogger(__name__)


@dataclass
class PapertestRunResult:
    engine_stats: Dict[str, Any]
    replay_stats: Dict[str, Any]
    bridge_stats: Dict[str, Any]
    execution_history: List[Dict[str, Any]]
    account_info: Dict[str, Any]


class PapertestEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.wired: Optional[WiredPaperSystem] = None
        self._bridge: Optional[ReplayToDispatcherBridge] = None
        self._run_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        self.wired = ComponentFactory(self.config).build()

        # Connect replay adapter
        ok = await self.wired.replay_adapter.connect()
        if not ok:
            raise RuntimeError("Replay adapter connect failed")

        # Subscribe (bars are the authoritative stream for this papertest suite)
        data_cfg = self.config["papertest"]["data"]
        await self.wired.replay_adapter.subscribe(list(data_cfg["symbols"]), ["bar", "quote", "trade"])

        # Bridge replay -> dispatcher
        debug_ts = parse_debug_timestamps(self.config)
        start_at_timestamp = debug_ts["start_at_timestamp"]
        stop_at_timestamp = debug_ts["stop_at_timestamp"]
        stop_after_bars = debug_ts["stop_after_bars"]

        # If we are intentionally skipping early replay data (debug window), we MUST warm up
        # right up to the first processed bar to avoid a large history gap that changes signals.
        if start_at_timestamp is not None and hasattr(self.wired.replay_adapter, "set_warmup_anchor_timestamp"):
            try:
                self.wired.replay_adapter.set_warmup_anchor_timestamp(start_at_timestamp)
            except Exception:
                pass

        def _request_stop() -> None:
            """
            Fast-stop for INSTANT replay.
            """
            if self.wired and self.wired.replay_adapter:
                self.wired.replay_adapter.request_stop()

        # Extract session gate for bridge filtering (consistency with backtest)
        session_gate = (self.wired.components or {}).get("session_gate")
        filter_market_hours = bool(data_cfg.get("simulate_market_hours", True))

        self._bridge = ReplayToDispatcherBridge(
            dispatcher=self.wired.dispatcher,
            id_generator=self.wired.id_generator,
            start_at_timestamp=start_at_timestamp,
            stop_after_bars=stop_after_bars,
            stop_at_timestamp=stop_at_timestamp,
            stop_callback=_request_stop,
            session_gate=session_gate,
            filter_market_hours=filter_market_hours,
        )
        self.wired.replay_adapter.add_message_handler(self._bridge.on_feed_message)

        # Initialize paper engine components
        ok = await self.wired.engine.initialize()
        if not ok:
            raise RuntimeError("PaperTradingEngine.initialize failed")

        # Configure StrategyManager (strategies + regime wiring)
        await self._configure_strategy_manager()

        # Warm up buffers before running
        await self.wired.engine.warmup(list(data_cfg["symbols"]))

    async def run(self) -> PapertestRunResult:
        if not self.wired or not self._bridge:
            raise RuntimeError("Call initialize() first")

        # Start replay
        ok = await self.wired.replay_adapter.start_replay()
        if not ok:
            raise RuntimeError("Replay start failed")

        # Run paper engine loop in background
        self._run_task = asyncio.create_task(self.wired.engine.run())

        # Wait until replay completes (or paper loop errors)
        await self._wait_for_replay_completion()

        # Give the paper engine a brief chance to drain queued events / finish in-flight risk work
        # (critical for deterministic signal↔risk parity in short debug windows)
        deadline = _time.time() + 2.0
        while _time.time() < deadline:
            try:
                bars_enq = getattr(self._bridge.stats, "bars_enqueued", None)
                bars_proc = (self.wired.engine.get_stats() or {}).get("bars_processed")
                if bars_enq is not None and bars_proc is not None and bars_proc >= bars_enq:
                    break
            except Exception:
                pass
            await asyncio.sleep(0.05)

        # Stop engine (request graceful shutdown)
        self.wired.engine.stop()

        # Prefer graceful completion; only cancel as last resort
        if self._run_task and not self._run_task.done():
            try:
                await asyncio.wait_for(self._run_task, timeout=2.0)
            except asyncio.TimeoutError:
                self._run_task.cancel()
                try:
                    await self._run_task
                except asyncio.CancelledError:
                    pass

        # Treat engine ERROR as a failed run
        try:
            state = self.wired.engine.get_state()
            if getattr(state, "name", "") == "ERROR":
                raise RuntimeError("PaperTradingEngine entered ERROR state during run")
        except Exception:
            # If state retrieval fails, still proceed with returning stats
            pass

        # Extract execution history for reporting (best-effort; avoids coupling callers to internal classes)
        execution_history: List[Dict[str, Any]] = []
        try:
            exec_engine = (self.wired.components or {}).get("execution_engine")
            if exec_engine is not None:
                for res in getattr(exec_engine, "execution_history", []) or []:
                    fills = getattr(res, "fills", None) or []
                    if fills:
                        for f in fills:
                            ts = f.get("timestamp")
                            if isinstance(ts, datetime):
                                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                            else:
                                ts_str = str(ts) if ts is not None else ""
                                ts_str = ts_str[:19] if ts_str else ""
                            execution_history.append(
                                {
                                    "timestamp": ts_str,
                                    "symbol": f.get("symbol"),
                                    "action": f.get("side") or f.get("action"),
                                    "quantity": f.get("quantity") or f.get("qty") or 0.0,
                                    "price": f.get("price") or f.get("fill_price") or 0.0,
                                    "signal_strength": f.get("signal_strength") or f.get("strength") or 0.0,
                                    "confidence": f.get("confidence") or 0.0,
                                }
                            )
                    else:
                        ts = getattr(res, "completed_at", None) or getattr(res, "started_at", None)
                        if isinstance(ts, datetime):
                            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            ts_str = str(ts)[:19] if ts is not None else ""
                        execution_history.append(
                            {
                                "timestamp": ts_str,
                                "symbol": None,
                                "action": None,
                                "quantity": float(getattr(res, "filled_quantity", 0.0) or 0.0),
                                "price": float(getattr(res, "avg_fill_price", 0.0) or 0.0),
                            }
                        )
        except Exception:
            execution_history = []

        # Extract broker account info for return calculations (best-effort)
        account_info: Dict[str, Any] = {}
        try:
            broker = (self.wired.components or {}).get("paper_broker")
            if broker is not None and hasattr(broker, "get_account_info"):
                acct = broker.get_account_info()
                account_info = {
                    "cash": float(getattr(acct, "cash", 0.0) or 0.0),
                    "equity": float(getattr(acct, "equity", 0.0) or 0.0),
                    "portfolio_value": float(getattr(acct, "portfolio_value", 0.0) or 0.0),
                }
        except Exception:
            account_info = {}

        # Fallback: UnifiedExecutionEngine may not retain fills in execution_history in some modes,
        # but the EventJournal is the source of truth for fills. If empty, derive trades from the journal.
        if not execution_history:
            try:
                journal_dir = str(((self.config.get("papertest") or {}).get("session") or {}).get("journal_dir", "papertest/results/journals"))
                session_id = str((self.wired.engine.get_stats() or {}).get("session_id") or "")
                if session_id:
                    execution_history = self._extract_execution_history_from_journal(
                        journal_dir=journal_dir,
                        session_id=session_id,
                    )
            except Exception:
                pass

        engine_stats = dict(self.wired.engine.get_stats() or {})
        engine_stats["execution_history"] = execution_history

        return PapertestRunResult(
            engine_stats=engine_stats,
            replay_stats=self.wired.replay_adapter.get_replay_statistics(),
            bridge_stats=self._bridge.stats,
            execution_history=execution_history,
            account_info=account_info,
        )

    def _extract_execution_history_from_journal(self, journal_dir: str, session_id: str) -> List[Dict[str, Any]]:
        """
        Parse EventJournal JSONL and return a backtest-like execution_history list.

        Uses:
        - FILL events for trades (timestamp, symbol, side, qty, price)
        - Best-effort "carry-forward" signal_strength from the most recent SIGNAL event for that symbol.
        """
        path = Path(journal_dir) / f"{session_id}.jsonl"
        if not path.exists():
            # Try gz variant if compression was enabled
            gz = Path(journal_dir) / f"{session_id}.jsonl.gz"
            path = gz if gz.exists() else path

        trades: List[Dict[str, Any]] = []
        last_strength_by_symbol: Dict[str, float] = {}
        last_confidence_by_symbol: Dict[str, float] = {}

        if not path.exists():
            return trades

        # Use EventJournal reader to support .gz transparently.
        try:
            from core_engine.system.event_journal import EventJournal as _EJ
            events = _EJ.read_journal(str(path))
        except Exception:
            # Fallback: line-by-line JSONL
            events = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        continue

        for ev in events:
            try:
                # EventJournal.read_journal returns JournalEvent objects; normalize to dict.
                if hasattr(ev, "to_dict"):
                    evd = ev.to_dict()  # type: ignore[attr-defined]
                else:
                    evd = ev if isinstance(ev, dict) else {}

                category = (evd.get("category") or "").upper()
                symbol = evd.get("symbol")
                data = evd.get("data") or {}

                if category == "SIGNAL" and evd.get("event_type") == "signal_generated":
                    if symbol:
                        try:
                            last_strength_by_symbol[symbol] = float(data.get("signal_strength") or 0.0)
                            last_confidence_by_symbol[symbol] = float(data.get("confidence") or 0.0)
                        except Exception:
                            last_strength_by_symbol[symbol] = 0.0
                            last_confidence_by_symbol[symbol] = 0.0
                if category == "FILL" and evd.get("event_type") == "fill":
                    side = data.get("side") or ""
                    qty = float(data.get("quantity") or 0.0)
                    px = float(data.get("price") or 0.0)
                    ft = data.get("fill_timestamp") or evd.get("timestamp") or ""
                    # Normalize timestamp to "YYYY-mm-dd HH:MM:SS"
                    ts = str(ft).replace("T", " ")
                    ts = ts[:19] if ts else "N/A"
                    trades.append(
                        {
                            "timestamp": ts,
                            "symbol": symbol,
                            "action": side,
                            "quantity": qty,
                            "price": px,
                            "signal_strength": float(last_strength_by_symbol.get(symbol or "", 0.0)),
                            "confidence": float(last_confidence_by_symbol.get(symbol or "", 0.0)),
                        }
                    )
            except Exception:
                continue

        return trades

    async def _wait_for_replay_completion(self) -> None:
        assert self.wired and self.wired.replay_adapter.replay_engine is not None
        engine = self.wired.replay_adapter.replay_engine

        while True:
            # Fail fast if paper engine errors out
            try:
                if getattr(self.wired.engine.get_state(), "name", "") == "ERROR":
                    await self.wired.replay_adapter.stop_replay()
                    return
            except Exception:
                pass

            st = engine.status
            if st in (ReplayStatus.COMPLETED, ReplayStatus.ERROR, ReplayStatus.STOPPED):
                return
            await asyncio.sleep(0.05)

    async def _configure_strategy_manager(self) -> None:
        assert self.wired is not None
        pt = self.config["papertest"]
        data_cfg = pt["data"]

        strategy_manager = self.wired.components.get("strategy_manager")
        regime_engine = self.wired.components.get("regime_engine")

        if not strategy_manager:
            return

        # Regime integration if supported
        if regime_engine and hasattr(strategy_manager, "set_regime_engine"):
            try:
                strategy_manager.set_regime_engine(regime_engine)
            except Exception:
                pass

        strategies = pt.get("strategies")
        if not strategies:
            # Minimal default: one momentum strategy over configured symbols
            strategies = [
                {
                    "name": "momentum_default",
                    "type": "momentum",
                    "symbols": list(data_cfg["symbols"]),
                    "active": True,
                    "allocation_pct": 0.10,
                }
            ]

        run_id = f"papertest_configure_strategy_{int(_time.time())}"

        # Add strategies
        if hasattr(strategy_manager, "add_strategy"):
            add_results = []
            for s in strategies:
                if "symbols" not in s:
                    s = dict(s)
                    s["symbols"] = list(data_cfg["symbols"])
                ok = await strategy_manager.add_strategy(s)
                add_results.append({"name": s.get("name"), "type": s.get("type"), "ok": bool(ok)})


