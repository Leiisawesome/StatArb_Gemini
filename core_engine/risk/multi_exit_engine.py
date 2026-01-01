"""
Multi-Exit Engine (ADS v3.1 Core)
================================

Implements the *core* multi-exit set for CentralRiskManager monitoring:
- Volatility stop (σ_eff-based, forward-looking via EWMA)
- Time stop
- Liquidity stop (best-effort, optional)

This module is intentionally simple and deterministic; it produces an exit decision
and reason code that RiskManager converts into a governed exit request.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    reason: str
    details: Dict[str, Any]


def decide_exit(
    *,
    now: datetime,
    opened_at: datetime,
    pnl_pct: float,
    stop_loss_pct: Optional[float] = None,
    max_holding_minutes: Optional[float] = None,
    liquidity_bad: bool = False,
    liquidity_details: Optional[Dict[str, Any]] = None,
) -> ExitDecision:
    """
    Evaluate core exit rules. Returns the first triggered rule in priority order:
    1) Vol stop (if provided)
    2) Time stop (if provided)
    3) Liquidity stop (if flagged)
    """
    # 1) Vol stop (pnl_pct is in percent, stop_loss_pct is positive percent distance)
    if stop_loss_pct is not None and stop_loss_pct > 0:
        if pnl_pct <= -abs(stop_loss_pct):
            return ExitDecision(
                should_exit=True,
                reason="VOL_STOP",
                details={"pnl_pct": float(pnl_pct), "stop_loss_pct": float(stop_loss_pct)},
            )

    # 2) Time stop
    if max_holding_minutes is not None and max_holding_minutes > 0:
        held_mins = (now - opened_at).total_seconds() / 60.0
        if held_mins >= float(max_holding_minutes):
            return ExitDecision(
                should_exit=True,
                reason="TIME_STOP",
                details={"held_minutes": float(held_mins), "max_holding_minutes": float(max_holding_minutes)},
            )

    # 3) Liquidity stop
    if liquidity_bad:
        return ExitDecision(
            should_exit=True,
            reason="LIQUIDITY_STOP",
            details=liquidity_details or {"liquidity_bad": True},
        )

    return ExitDecision(should_exit=False, reason="NONE", details={})


