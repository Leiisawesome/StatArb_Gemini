"""
RiskManagerPositionCallback
===========================

UnifiedExecutionEngine can update positions via a registered `risk_manager_callback`.
In livepapertest, we wrap the CentralRiskManager update to also emit fill records
to the EventJournal (without double-applying positions).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.system.event_journal import EventJournal


@dataclass
class RiskManagerPositionCallback:
    risk_manager: CentralRiskManager
    journal: Optional[EventJournal] = None

    async def update_position(self, symbol: str, side: str, quantity: float, price: float) -> None:
        # Delegate to RiskManager (which delegates to PositionBook when configured)
        await self.risk_manager.update_position(symbol=symbol, side=side, quantity=quantity, price=price)

        # Best-effort fill journaling (OMS order_id not available at this layer)
        if self.journal is not None:
            try:
                ts = datetime.now(timezone.utc)
                fill_id = f"livefill:{symbol}:{side}:{ts.timestamp()}"
                self.journal.log_fill(
                    symbol=symbol,
                    order_id="",
                    fill_id=fill_id,
                    quantity=quantity,
                    price=price,
                    commission=0.0,
                    side=side,
                    fill_timestamp=ts,
                )
            except Exception:
                pass


