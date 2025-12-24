"""
ExecutionGate
=============

Implements the two-key safety model for live paper trading:

- Config flag: enable_orders (default false)
- CLI flag: --enable-orders must be present
- Env override: LIVEPAPER_KILL_SWITCH=1 forces NO-ORDER mode

This gate is applied by wrapping `UnifiedExecutionEngine.execute_with_mode_routing`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional, Dict


@dataclass(frozen=True)
class ExecutionGateConfig:
    enable_orders_config: bool = False
    enable_orders_cli: bool = False
    kill_switch_env_var: str = "LIVEPAPER_KILL_SWITCH"
    # Optional data-age based guard: if provided and returns True -> block
    should_block_orders: Optional[Callable[[str], bool]] = None


class ExecutionGate:
    def __init__(self, cfg: ExecutionGateConfig):
        self._cfg = cfg

    def is_kill_switch_active(self) -> bool:
        v = os.getenv(self._cfg.kill_switch_env_var, "").strip().lower()
        return v in ("1", "true", "yes", "on")

    def orders_enabled(self) -> bool:
        if self.is_kill_switch_active():
            return False
        return bool(self._cfg.enable_orders_config and self._cfg.enable_orders_cli)

    def should_block(self, symbol: Optional[str] = None) -> Optional[str]:
        """
        Returns a string reason if blocked, else None.
        """
        if self.is_kill_switch_active():
            return "kill_switch_env"
        if not self._cfg.enable_orders_config:
            return "enable_orders_config_false"
        if not self._cfg.enable_orders_cli:
            return "enable_orders_cli_missing"
        if symbol and self._cfg.should_block_orders is not None:
            try:
                if bool(self._cfg.should_block_orders(symbol)):
                    return "data_stale_block"
            except Exception:
                # If guard fails, be safe and block
                return "data_stale_guard_error"
        return None

    def block_payload(self, reason: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        return {
            "blocked": True,
            "reason": reason,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "kill_switch_env_var": self._cfg.kill_switch_env_var,
        }


