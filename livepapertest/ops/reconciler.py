"""
IBKR reconciliation loops (External SSOT -> Internal SSOT convergence checks).

External SSOT: IBKR positions/cash
Internal SSOT: core_engine PositionBook
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from core_engine.system.event_journal import EventJournal
from core_engine.trading.position_book import IPositionBook

from livepapertest.broker.ibkr_paper_facade import LivePaperBrokerFacade


@dataclass
class TradingPauseFlag:
    """Simple pause flag to block order submission without stopping the engine."""
    paused: bool = False
    reason: str = ""


def _book_positions_to_qty(book: IPositionBook) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for sym, pos in (book.get_all_positions() or {}).items():
        try:
            out[str(sym).upper()] = float(getattr(pos, "quantity", 0.0) or 0.0)
        except Exception:
            continue
    return out


@dataclass
class IBKRReconciler:
    facade: LivePaperBrokerFacade
    position_book: IPositionBook
    journal: Optional[EventJournal] = None
    pause_on_mismatch: bool = True
    qty_tolerance: float = 1e-6
    cash_tolerance: float = 1.0  # dollars
    pause_flag: Optional[TradingPauseFlag] = None

    async def reconcile_positions_once(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Returns (ok, details)
        """
        # Refresh snapshots (blocking) off-loop
        acct = await asyncio.to_thread(self.facade.refresh_account_info)
        await asyncio.to_thread(self.facade.refresh_positions)

        ib_pos = self.facade.get_all_positions()
        ib_qty = {sym: float(p.quantity) for sym, p in ib_pos.items()}
        book_qty = _book_positions_to_qty(self.position_book)

        symbols = set(ib_qty.keys()) | set(book_qty.keys())
        mismatches = []
        for sym in sorted(symbols):
            a = float(book_qty.get(sym, 0.0) or 0.0)
            b = float(ib_qty.get(sym, 0.0) or 0.0)
            if abs(a - b) > self.qty_tolerance:
                mismatches.append({"symbol": sym, "position_book_qty": a, "ibkr_qty": b})

        cash_book = float(self.position_book.get_cash_balance())
        cash_ib = float(getattr(acct, "cash", 0.0) or 0.0)
        cash_diff = cash_book - cash_ib
        cash_mismatch = abs(cash_diff) > self.cash_tolerance

        ok = (len(mismatches) == 0) and (not cash_mismatch)
        details = {
            "ok": ok,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mismatches": mismatches,
            "cash": {"position_book": cash_book, "ibkr": cash_ib, "diff": cash_diff},
        }
        return ok, details

    async def run_positions_loop(self, interval_sec: float) -> None:
        while True:
            try:
                ok, details = await self.reconcile_positions_once()
                if not ok:
                    if self.journal is not None:
                        try:
                            self.journal.log_system("reconcile_mismatch", details)
                        except Exception:
                            pass
                    if self.pause_on_mismatch and self.pause_flag is not None:
                        self.pause_flag.paused = True
                        self.pause_flag.reason = "reconcile_mismatch"
                await asyncio.sleep(max(1.0, float(interval_sec)))
            except asyncio.CancelledError:
                return
            except Exception as e:
                if self.journal is not None:
                    try:
                        self.journal.log_system("reconcile_error", {"error": str(e)})
                    except Exception:
                        pass
                await asyncio.sleep(max(1.0, float(interval_sec)))


