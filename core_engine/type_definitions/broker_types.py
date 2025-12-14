"""
Extended broker type definitions for Phase 9 real broker integration
Adds Position, AccountInfo, TimeInForce types
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Import existing types from orders module
from .orders import Order, OrderType, OrderSide, OrderStatus

class TimeInForce(Enum):
    """Time-in-force enumeration"""
    DAY = "day"  # Day order
    GTC = "gtc"  # Good-til-cancelled
    IOC = "ioc"  # Immediate-or-cancel
    FOK = "fok"  # Fill-or-kill
    GTD = "gtd"  # Good-til-date

@dataclass
class Position:
    """Position information from broker"""
    symbol: str
    quantity: float
    avg_entry_price: float
    market_value: float
    unrealized_pl: float
    unrealized_plpc: float  # Unrealized P&L percentage
    current_price: float
    side: str  # "long" or "short"
    cost_basis: float

    # Optional fields
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AccountInfo:
    """Account information from broker"""
    account_id: str
    cash: float
    buying_power: float
    portfolio_value: float
    equity: float
    currency: str = "USD"

    # Trading restrictions
    is_pattern_day_trader: bool = False
    day_trade_count: int = 0

    # Account status
    status: str = "active"

    # Optional fields
    margin_multiplier: Optional[float] = None
    maintenance_margin: Optional[float] = None
    initial_margin: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

# Export all types
__all__ = [
    'Order',
    'OrderType',
    'OrderSide',
    'OrderStatus',
    'TimeInForce',
    'Position',
    'AccountInfo'
]
