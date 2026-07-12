"""Standalone broker-side data models used by routed-live adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class BrokerOrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class BrokerOrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class BrokerOrderStatus(str, Enum):
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass(slots=True)
class BrokerOrder:
    symbol: str
    side: BrokerOrderSide
    quantity: float
    order_type: BrokerOrderType
    price: float | None = None
    status: BrokerOrderStatus = BrokerOrderStatus.SUBMITTED
    filled_quantity: float = 0.0
    average_price: float | None = None
    timestamp: datetime | None = None
    order_id: str = field(default_factory=lambda: uuid4().hex)
    client_order_id: str | None = None


@dataclass(frozen=True, slots=True)
class IBKRConnectionConfig:
    host: str = "127.0.0.1"
    port: int = 4002
    client_id: int = 1
    account_id: str | None = None
    paper_trading: bool = True
    outside_regular_trading_hours: bool = False
