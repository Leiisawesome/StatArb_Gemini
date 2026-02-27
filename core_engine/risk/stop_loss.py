"""
Centralized Stop-Loss Utilities (F6)
====================================

Shared stop-loss logic for strategies, risk manager, and execution.
Reduces fragmentation across enhanced_mean_reversion, order_manager,
position_manager, multi_exit_engine, and shadow components.

Design:
- Strategies compute stop_price via compute_stop_price() for consistency.
- CRM and execution use the same helpers for authorization and fills.
- Trailing-stop: broker supports (IBKR submit_trailing_stop_order);
  CRM does not yet enforce trailing stops — strategies implement ad-hoc.

Author: StatArb_Gemini Core Engine
"""

from typing import Optional, Literal
import logging

logger = logging.getLogger(__name__)

# Default stop-loss percentage (2%) — aligned with component_config.stop_loss_pct
DEFAULT_STOP_LOSS_PCT = 0.02


def compute_stop_price(
    arrival_price: float,
    side: Literal["buy", "sell"],
    stop_loss_pct: float = DEFAULT_STOP_LOSS_PCT,
) -> float:
    """
    Compute stop price from arrival price and stop-loss percentage.

    For long (buy): stop = arrival * (1 - stop_loss_pct)
    For short (sell): stop = arrival * (1 + stop_loss_pct)

    Args:
        arrival_price: Price at entry
        side: 'buy' (long) or 'sell' (short)
        stop_loss_pct: Stop-loss as fraction (e.g. 0.02 = 2%)

    Returns:
        Stop price (trigger level)
    """
    if arrival_price <= 0:
        return arrival_price
    pct = abs(stop_loss_pct)
    if side.lower() == "buy":
        return arrival_price * (1.0 - pct)
    return arrival_price * (1.0 + pct)


def check_stop_loss_triggered(
    current_price: float,
    stop_price: float,
    side: Literal["buy", "sell"],
) -> bool:
    """
    Check if stop-loss has been triggered.

    Long: triggered when current_price <= stop_price
    Short: triggered when current_price >= stop_price

    Args:
        current_price: Current market price
        stop_price: Stop level from compute_stop_price
        side: 'buy' (long) or 'sell' (short)

    Returns:
        True if stop-loss should fire
    """
    if side.lower() == "buy":
        return current_price <= stop_price
    return current_price >= stop_price


def compute_pnl_pct(
    current_price: float,
    entry_price: float,
    side: Literal["buy", "sell"],
) -> float:
    """
    Compute unrealized P&L percentage for a position.

    Long: (current - entry) / entry
    Short: (entry - current) / entry

    Args:
        current_price: Current market price
        entry_price: Entry/cost basis
        side: 'buy' (long) or 'sell' (short)

    Returns:
        P&L as decimal (e.g. -0.02 = -2%)
    """
    if entry_price <= 0:
        return 0.0
    if side.lower() == "buy":
        return (current_price - entry_price) / entry_price
    return (entry_price - current_price) / entry_price
