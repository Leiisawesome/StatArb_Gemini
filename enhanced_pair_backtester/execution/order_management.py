"""
Order Management System

Professional order management for pairs trading with:
- Order tracking and lifecycle management
- Risk checks and validation
- Execution quality monitoring
- Portfolio position tracking
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid


class OrderType(Enum):
    """Order types supported by the execution engine"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status lifecycle"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    """Order side (buy/sell)"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """
    Comprehensive order representation
    """
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Order identification
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_order_id: Optional[str] = None
    
    # Timing
    created_time: datetime = field(default_factory=datetime.now)
    submitted_time: Optional[datetime] = None
    filled_time: Optional[datetime] = None
    
    # Status and execution
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    
    # Risk and metadata
    account_id: str = "default"
    strategy_id: str = "pairs_trading"
    notes: str = ""
    
    @property
    def remaining_quantity(self) -> float:
        """Remaining quantity to be filled"""
        return self.quantity - self.filled_quantity
    
    @property
    def is_complete(self) -> bool:
        """Check if order is completely filled"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]
    
    @property
    def fill_percentage(self) -> float:
        """Percentage of order filled"""
        if self.quantity == 0:
            return 0.0
        return (self.filled_quantity / self.quantity) * 100
    
    def to_dict(self) -> Dict:
        """Convert order to dictionary for logging/storage"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'order_type': self.order_type.value,
            'price': self.price,
            'stop_price': self.stop_price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_fill_price': self.average_fill_price,
            'created_time': self.created_time.isoformat(),
            'submitted_time': self.submitted_time.isoformat() if self.submitted_time else None,
            'filled_time': self.filled_time.isoformat() if self.filled_time else None,
            'account_id': self.account_id,
            'strategy_id': self.strategy_id,
            'notes': self.notes
        }


@dataclass
class Fill:
    """Trade fill/execution record"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    fill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    commission: float = 0.0
    
    @property
    def notional_value(self) -> float:
        """Notional value of the fill"""
        return self.quantity * self.price


@dataclass
class Position:
    """Current position in a symbol"""
    symbol: str
    quantity: float = 0.0
    average_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    @property
    def notional_value(self) -> float:
        """Notional value of position"""
        return self.quantity * self.average_price


class OrderManager:
    """
    Comprehensive order management system
    
    Handles order lifecycle, risk checks, and position tracking
    """
    
    def __init__(self, 
                 max_order_value: float = 1000000,  # $1M max order
                 max_position_value: float = 5000000,  # $5M max position
                 risk_check_enabled: bool = True):
        """
        Initialize order manager
        
        Args:
            max_order_value: Maximum order value for risk checks
            max_position_value: Maximum position value for risk checks
            risk_check_enabled: Whether to perform risk checks
        """
        self.max_order_value = max_order_value
        self.max_position_value = max_position_value
        self.risk_check_enabled = risk_check_enabled
        
        # Order and position tracking
        self.orders: Dict[str, Order] = {}
        self.fills: List[Fill] = []
        self.positions: Dict[str, Position] = {}
        
        # Performance tracking
        self.order_stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'cancelled_orders': 0,
            'rejected_orders': 0,
            'total_fill_value': 0.0,
            'total_commission': 0.0
        }
    
    def create_order(self, 
                    symbol: str,
                    side: OrderSide,
                    quantity: float,
                    order_type: OrderType,
                    price: Optional[float] = None,
                    stop_price: Optional[float] = None,
                    strategy_id: str = "pairs_trading") -> Order:
        """
        Create a new order
        
        Args:
            symbol: Trading symbol
            side: Buy or sell
            quantity: Order quantity
            order_type: Type of order
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            strategy_id: Strategy identifier
            
        Returns:
            Created Order object
        """
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            strategy_id=strategy_id
        )
        
        self.orders[order.order_id] = order
        self.order_stats['total_orders'] += 1
        
        return order
    
    def submit_order(self, order: Order) -> bool:
        """
        Submit order for execution (with risk checks)
        
        Args:
            order: Order to submit
            
        Returns:
            True if order was submitted successfully
        """
        # Risk checks
        if self.risk_check_enabled:
            if not self._validate_order(order):
                order.status = OrderStatus.REJECTED
                self.order_stats['rejected_orders'] += 1
                return False
        
        # Submit order
        order.status = OrderStatus.SUBMITTED
        order.submitted_time = datetime.now()
        
        return True
    
    def fill_order(self, 
                  order_id: str,
                  fill_quantity: float,
                  fill_price: float,
                  commission: float = 0.0) -> Optional[Fill]:
        """
        Fill an order (partially or completely)
        
        Args:
            order_id: Order ID to fill
            fill_quantity: Quantity being filled
            fill_price: Price of the fill
            commission: Commission charged
            
        Returns:
            Fill object if successful, None otherwise
        """
        if order_id not in self.orders:
            return None
        
        order = self.orders[order_id]
        
        # Validate fill
        if order.status not in [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]:
            return None
        
        if fill_quantity > order.remaining_quantity:
            fill_quantity = order.remaining_quantity
        
        # Create fill record
        fill = Fill(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=fill_quantity,
            price=fill_price,
            commission=commission
        )
        
        self.fills.append(fill)
        
        # Update order
        old_filled_qty = order.filled_quantity
        order.filled_quantity += fill_quantity
        
        # Update average fill price
        if old_filled_qty == 0:
            order.average_fill_price = fill_price
        else:
            total_value = (old_filled_qty * order.average_fill_price + 
                          fill_quantity * fill_price)
            order.average_fill_price = total_value / order.filled_quantity
        
        # Update order status
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
            order.filled_time = datetime.now()
            self.order_stats['filled_orders'] += 1
        else:
            order.status = OrderStatus.PARTIALLY_FILLED
        
        # Update position
        self._update_position(order.symbol, order.side, fill_quantity, fill_price)
        
        # Update statistics
        self.order_stats['total_fill_value'] += fill_quantity * fill_price
        self.order_stats['total_commission'] += commission
        
        return fill
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if order was cancelled successfully
        """
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            return False
        
        order.status = OrderStatus.CANCELLED
        self.order_stats['cancelled_orders'] += 1
        
        return True
    
    def get_position(self, symbol: str) -> Position:
        """
        Get current position for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position object
        """
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        
        return self.positions[symbol]
    
    def get_order_history(self, 
                         symbol: Optional[str] = None,
                         status: Optional[OrderStatus] = None) -> List[Order]:
        """
        Get order history with optional filtering
        
        Args:
            symbol: Filter by symbol
            status: Filter by status
            
        Returns:
            List of orders matching criteria
        """
        orders = list(self.orders.values())
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        return sorted(orders, key=lambda x: x.created_time, reverse=True)
    
    def get_fill_history(self, 
                        symbol: Optional[str] = None,
                        start_time: Optional[datetime] = None) -> List[Fill]:
        """
        Get fill history with optional filtering
        
        Args:
            symbol: Filter by symbol
            start_time: Filter by start time
            
        Returns:
            List of fills matching criteria
        """
        fills = self.fills
        
        if symbol:
            fills = [f for f in fills if f.symbol == symbol]
        
        if start_time:
            fills = [f for f in fills if f.timestamp >= start_time]
        
        return sorted(fills, key=lambda x: x.timestamp, reverse=True)
    
    def get_performance_summary(self) -> Dict:
        """
        Get performance summary statistics
        
        Returns:
            Dictionary with performance metrics
        """
        total_orders = self.order_stats['total_orders']
        
        fill_rate = (self.order_stats['filled_orders'] / total_orders * 100 
                    if total_orders > 0 else 0)
        
        cancel_rate = (self.order_stats['cancelled_orders'] / total_orders * 100 
                      if total_orders > 0 else 0)
        
        reject_rate = (self.order_stats['rejected_orders'] / total_orders * 100 
                      if total_orders > 0 else 0)
        
        return {
            'total_orders': total_orders,
            'filled_orders': self.order_stats['filled_orders'],
            'cancelled_orders': self.order_stats['cancelled_orders'],
            'rejected_orders': self.order_stats['rejected_orders'],
            'fill_rate_pct': fill_rate,
            'cancel_rate_pct': cancel_rate,
            'reject_rate_pct': reject_rate,
            'total_fill_value': self.order_stats['total_fill_value'],
            'total_commission': self.order_stats['total_commission'],
            'active_positions': len([p for p in self.positions.values() if p.quantity != 0])
        }
    
    def _validate_order(self, order: Order) -> bool:
        """
        Validate order against risk limits
        
        Args:
            order: Order to validate
            
        Returns:
            True if order passes validation
        """
        # Check order value
        if order.price and order.quantity:
            order_value = abs(order.quantity * order.price)
            if order_value > self.max_order_value:
                order.notes = f"Order value {order_value} exceeds limit {self.max_order_value}"
                return False
        
        # Check position limits
        position = self.get_position(order.symbol)
        new_quantity = position.quantity
        
        if order.side == OrderSide.BUY:
            new_quantity += order.quantity
        else:
            new_quantity -= order.quantity
        
        if order.price:
            new_position_value = abs(new_quantity * order.price)
            if new_position_value > self.max_position_value:
                order.notes = f"Position value {new_position_value} exceeds limit {self.max_position_value}"
                return False
        
        return True
    
    def _update_position(self, 
                        symbol: str,
                        side: OrderSide,
                        quantity: float,
                        price: float):
        """
        Update position after a fill
        
        Args:
            symbol: Trading symbol
            side: Order side
            quantity: Fill quantity
            price: Fill price
        """
        position = self.get_position(symbol)
        
        if side == OrderSide.BUY:
            # Adding to position
            if position.quantity >= 0:
                # Long position or flat
                total_cost = (position.quantity * position.average_price + 
                             quantity * price)
                position.quantity += quantity
                position.average_price = total_cost / position.quantity if position.quantity > 0 else 0
            else:
                # Short position - reducing short
                if quantity >= abs(position.quantity):
                    # Covering short and going long
                    remaining_qty = quantity - abs(position.quantity)
                    position.realized_pnl += abs(position.quantity) * (position.average_price - price)
                    position.quantity = remaining_qty
                    position.average_price = price if remaining_qty > 0 else 0
                else:
                    # Partially covering short
                    position.realized_pnl += quantity * (position.average_price - price)
                    position.quantity += quantity
        else:  # SELL
            # Reducing position
            if position.quantity > 0:
                # Long position - reducing long
                if quantity >= position.quantity:
                    # Selling entire position and going short
                    remaining_qty = quantity - position.quantity
                    position.realized_pnl += position.quantity * (price - position.average_price)
                    position.quantity = -remaining_qty
                    position.average_price = price if remaining_qty > 0 else 0
                else:
                    # Partially selling long
                    position.realized_pnl += quantity * (price - position.average_price)
                    position.quantity -= quantity
            else:
                # Short position or flat
                total_cost = (abs(position.quantity) * position.average_price + 
                             quantity * price)
                position.quantity -= quantity
                position.average_price = total_cost / abs(position.quantity) if position.quantity != 0 else 0 