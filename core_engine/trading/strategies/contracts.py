"""
Strategy Contracts (Rule 7)
===========================

Canonical, strategy-facing types for the Strategy Layer.

Per Rule 7, this module is the single place where strategy implementations and
the strategy skeleton agree on the shape of trade intent.

Notes:
- Enums `SignalType` and `StrategyType` are SSOT in `core_engine/type_definitions/strategy.py`.
- This module intentionally does NOT include execution, sizing authority, or position tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from core_engine.type_definitions.strategy import SignalType


class StrategyState(Enum):
    """Lifecycle state for EnhancedBaseStrategy instances."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    STOPPED = "stopped"


@dataclass
class StrategySignal:
    """
    Canonical trade-intent object emitted by strategies.

    This is intent only. Authorization/sizing/execution are handled elsewhere
    (CentralRiskManager + execution pipeline).
    """

    # Identity
    signal_id: str = ""
    strategy_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Intent
    symbol: str = ""
    signal_type: SignalType = SignalType.HOLD
    confidence: float = 0.0
    strength: float = 0.0

    # Optional sizing hint (RiskManager is final authority)
    quantity_type: str = "PERCENTAGE"  # "PERCENTAGE" or "ABSOLUTE"
    target_weight: Optional[float] = None  # 0.05 = 5% portfolio weight
    target_quantity: float = 0.0  # shares/contracts when ABSOLUTE

    # Backward-compat convenience (some code checks `.quantity`)
    quantity: Optional[float] = None

    # Optional fields (StrategyManager uses getattr, but having them here improves clarity)
    expected_return: float = 0.0
    risk_score: float = 0.0
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Diagnostics
    signal_source: str = ""
    signal_reason: str = ""
    additional_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.signal_id:
            self.signal_id = str(uuid.uuid4())

        # Backward compat: if `quantity` is provided and `target_quantity` is not, copy it.
        if (self.quantity is not None) and (self.target_quantity == 0.0):
            try:
                self.target_quantity = float(self.quantity)
            except Exception:
                # Keep default
                pass

