"""
Core Engine Order Types

Lightweight order types for standalone core_engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"

@dataclass
class Order:
    """Core order representation"""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None

    # Order tracking
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.now)

    # Execution tracking
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    commission: float = 0.0

    # Metadata
    strategy_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionResult:
    """Order execution result"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    timestamp: datetime = field(default_factory=datetime.now)
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Success/failure tracking
    success: bool = True
    error_message: Optional[str] = None

    # Broker details
    broker_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)