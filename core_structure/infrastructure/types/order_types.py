"""
Canonical Order Type Definitions
===============================

Single source of truth for all order-related types.
Consolidates 5+ duplicate implementations across the codebase.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
import uuid

class OrderType(Enum):
    """Standard order types - canonical definition"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"
    HIDDEN = "hidden"

class OrderSide(Enum):
    """Order side (buy/sell) - canonical definition"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Order execution status - canonical definition"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class TimeInForce(Enum):
    """Time in force - canonical definition"""
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill

class ExecutionStrategy(Enum):
    """Execution strategies - canonical definition"""
    MARKET = "market"
    LIMIT = "limit"
    TWAP = "twap"  # Time-Weighted Average Price
    VWAP = "vwap"  # Volume-Weighted Average Price
    ICEBERG = "iceberg"  # Iceberg orders
    POV = "pov"  # Percentage of Volume

@dataclass
class Fill:
    """Order fill information - canonical definition"""
    fill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: float = 0.0
    price: float = 0.0
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    venue: str = "default"
    execution_id: str = ""
    
    @property
    def notional_value(self) -> float:
        """Notional value of fill"""
        return self.quantity * self.price
    
    @property
    def net_value(self) -> float:
        """Net value after commission"""
        return self.notional_value - self.commission

@dataclass
class Order:
    """Canonical order representation - consolidates all implementations"""
    # Basic order details
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    
    # Pricing
    price: Optional[float] = None
    limit_price: Optional[float] = None  # Alias for price
    stop_price: Optional[float] = None
    
    # Order management
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    time_in_force: TimeInForce = TimeInForce.DAY
    
    # Execution tracking
    filled_quantity: float = 0.0
    avg_fill_price: Optional[float] = None
    fills: List[Fill] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    timestamp: Optional[datetime] = None  # Alias for created_at
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    venue: str = "default"
    execution_id: Optional[str] = None
    commission: float = 0.0
    
    def __post_init__(self):
        """Initialize order with aliases"""
        if self.timestamp is None:
            self.timestamp = self.created_at
        if self.limit_price is not None and self.price is None:
            self.price = self.limit_price
        elif self.price is not None and self.limit_price is None:
            self.limit_price = self.price
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_open(self) -> bool:
        """Check if order is still open"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def remaining_quantity(self) -> float:
        """Remaining quantity to be filled"""
        return max(0, self.quantity - self.filled_quantity)
    
    @property
    def notional_value(self) -> float:
        """Total notional value of order"""
        price = self.price or self.avg_fill_price or 0
        return self.quantity * price
    
    def add_fill(self, fill: Fill):
        """Add a fill to the order"""
        self.fills.append(fill)
        self.filled_quantity += fill.quantity
        self.commission += fill.commission
        
        # Update average fill price
        total_value = sum(f.quantity * f.price for f in self.fills)
        total_quantity = sum(f.quantity for f in self.fills)
        if total_quantity > 0:
            self.avg_fill_price = total_value / total_quantity
        
        # Update status
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        self.updated_at = datetime.now()
