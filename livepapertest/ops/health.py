"""
Health logging for livepapertest.

Emits a single periodic line suitable for tailing logs in production.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core_engine.paper.engine import PaperTradingEngine
from core_engine.trading.position_book import IPositionBook
from core_engine.system.event_journal import EventJournal

from livepapertest.broker.ibkr_paper_facade import LivePaperBrokerFacade
from livepapertest.engine.polygon_live_bridge import PolygonToDispatcherBridge


@dataclass
class HealthReporter:
    engine: PaperTradingEngine
    symbols: List[str]
    facade: LivePaperBrokerFacade
    position_book: IPositionBook
    bridge: PolygonToDispatcherBridge
    journal: Optional[EventJournal] = None
    polygon_service: Optional[Any] = None
    ibkr_adapter: Optional[Any] = None

    async def run(self, interval_sec: float) -> None:
        while True:
            try:
                self.emit()
                await asyncio.sleep(max(5.0, float(interval_sec)))
            except asyncio.CancelledError:
                return
            except Exception:
                await asyncio.sleep(max(5.0, float(interval_sec)))

    def emit(self) -> None:
        now = datetime.now(timezone.utc)
        eng = self.engine.get_stats()

        # Connectivity
        poly_ok = None
        try:
            if self.polygon_service is not None and hasattr(self.polygon_service, "is_operational"):
                poly_ok = bool(getattr(self.polygon_service, "is_operational"))
        except Exception:
            poly_ok = None
        ib_ok = None
        try:
            if self.ibkr_adapter is not None and hasattr(self.ibkr_adapter, "is_connected"):
                ib_ok = bool(self.ibkr_adapter.is_connected())
        except Exception:
            ib_ok = None

        # Per-symbol timestamps/ages
        sym_rows: List[Dict[str, Any]] = []
        for sym in self.symbols:
            last_bar = self.bridge.last_bar_timestamp(sym)
            last_bar_age = (now - last_bar).total_seconds() if last_bar else None
            px_age = self.facade.get_price_age_seconds(sym)
            q = self.facade.get_latest_quote(sym) or {}
            px = q.get("last_price")
            sym_rows.append(
                {
                    "symbol": sym,
                    "px": float(px) if px is not None else None,
                    "px_age_s": round(px_age, 1) if px_age is not None else None,
                    "bar_age_s": round(last_bar_age, 1) if last_bar_age is not None else None,
                }
            )

        # Exposure summary
        try:
            snap = self.position_book.get_snapshot()
            net = float(getattr(snap, "net_exposure", 0.0) or 0.0) if hasattr(snap, "net_exposure") else None
            cash = float(getattr(snap, "cash_balance", 0.0) or 0.0) if hasattr(snap, "cash_balance") else float(self.position_book.get_cash_balance())
            pos_n = len(getattr(snap, "positions", {}) or {}) if hasattr(snap, "positions") else len(self.position_book.get_all_positions() or {})
        except Exception:
            net = None
            cash = None
            pos_n = None

        payload = {
            "ts": now.isoformat(),
            "engine": {"state": eng.get("state"), "bars": eng.get("bars_processed"), "fills": eng.get("fills_received"), "orders": eng.get("orders_submitted")},
            "conn": {"polygon": poly_ok, "ibkr": ib_ok},
            "symbols": sym_rows,
            "portfolio": {"positions": pos_n, "cash": cash, "net_exposure": net},
        }

        # Log to journal for audit-friendly health stream (optional)
        if self.journal is not None:
            try:
                self.journal.log_system("health", payload)
            except Exception:
                pass

        # Also emit as a single log line via print (keeps deps minimal)
        # The system already uses logging extensively; this line is intentionally compact.
        print(f"[health] {payload}")


