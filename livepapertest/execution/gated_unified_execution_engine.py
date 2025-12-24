"""
GatedUnifiedExecutionEngine
===========================

Wraps `core_engine.system.unified_execution_engine.UnifiedExecutionEngine` to apply
the livepapertest kill switch / two-key order gate without modifying core engine code.

This is intentionally thin: it intercepts `execute_with_mode_routing` and either:
- delegates to the underlying engine, or
- returns a blocked result (best-effort shape compatible with callers)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core_engine.system.event_journal import EventJournal

from .execution_gate import ExecutionGate


@dataclass(frozen=True)
class BlockedExecutionResult:
    """
    Minimal result object compatible with `PaperTradingEngine` checks.

    The engine checks:
      - getattr(result, 'status', None) and string endswith('filled')
    So we ensure `status` is a string that cannot be mistaken for FILLED.
    """

    status: str = "BLOCKED"
    fill_quantity: float = 0.0
    fill_price: float = 0.0
    commission_cost: float = 0.0
    reason: str = ""


class GatedUnifiedExecutionEngine:
    def __init__(
        self,
        inner: Any,
        gate: ExecutionGate,
        journal: Optional[EventJournal] = None,
    ):
        self._inner = inner
        self._gate = gate
        self._journal = journal

    # Proxy config methods used by wiring code
    def set_live_broker(self, broker: Any) -> None:
        return self._inner.set_live_broker(broker)

    def set_execution_mode(self, mode: str) -> None:
        return self._inner.set_execution_mode(mode)

    def set_paper_broker(self, broker: Any) -> None:
        # Allowed; for completeness
        return self._inner.set_paper_broker(broker)

    async def execute_with_mode_routing(self, request: Any) -> Any:
        """
        Gate orders before delegating to real execution.
        """
        symbol = None
        try:
            symbol = getattr(getattr(request, "authorization", None), "symbol", None)
        except Exception:
            symbol = None

        reason = self._gate.should_block(symbol=str(symbol) if symbol else None)
        if reason is not None:
            payload = self._gate.block_payload(reason=reason, symbol=str(symbol) if symbol else None)
            if self._journal is not None:
                try:
                    self._journal.log_system("kill_switch_block", payload)
                except Exception:
                    pass
            return BlockedExecutionResult(reason=reason)

        return await self._inner.execute_with_mode_routing(request)


