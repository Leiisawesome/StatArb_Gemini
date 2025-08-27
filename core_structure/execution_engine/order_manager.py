"""
Order Management System

Professional order management with:
- Order lifecycle tracking
- Risk checks and validation
- Position management
- Fill processing
- Performance analytics

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import logging
from collections import defaultdict

# Use canonical types to eliminate duplicates
from ..infrastructure import OrderStatus, OrderType, OrderSide, TimeInForce, Fill, Order


@dataclass
class Position:
    """Execution engine position tracking
    
    Note: This is a specialized position class for order execution tracking
    with detailed long/short breakdown. For canonical position representation,
    see infrastructure/types/strategy_types.py
    """
    symbol: str
    quantity: float = 0.0
    average_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Position details
    long_quantity: float = 0.0
    short_quantity: float = 0.0
    total_cost: float = 0.0
    total_commission: float = 0.0
    
    # Tracking
    first_trade_time: Optional[datetime] = None
    last_trade_time: Optional[datetime] = None
    trade_count: int = 0
    
    def update_position(self, fill: Fill):
        """Update position with new fill"""
        if self.first_trade_time is None:
            self.first_trade_time = fill.timestamp
        
        self.last_trade_time = fill.timestamp
        self.trade_count += 1
        
        # Update quantities
        if fill.side == OrderSide.BUY:
            self.long_quantity += fill.quantity
            fill_value = fill.quantity * fill.price
        else:
            self.short_quantity += fill.quantity
            fill_value = -fill.quantity * fill.price
        
        # Calculate new average price
        old_value = self.quantity * self.average_price
        new_quantity = self.quantity + (fill.quantity if fill.side == OrderSide.BUY else -fill.quantity)
        
        if new_quantity != 0:
            self.average_price = (old_value + fill_value) / new_quantity
        else:
            self.average_price = 0.0
        
        self.quantity = new_quantity
        self.total_cost += abs(fill_value)
        self.total_commission += fill.commission
    
    @property
    def net_quantity(self) -> float:
        """Net position quantity"""
        return self.long_quantity - self.short_quantity
    
    @property
    def is_flat(self) -> bool:
        """Check if position is flat"""
        return abs(self.quantity) < 1e-8


class OrderManager:
    """
    Comprehensive order management system
    
    Features:
    - Order lifecycle management
    - Risk checks and validation
    - Position tracking
    - Fill processing
    - Performance analytics
    """
    
    def __init__(self, 
                 max_order_value: float = 1_000_000,
                 max_position_value: float = 5_000_000,
                 max_orders_per_symbol: int = 100,
                 enable_risk_checks: bool = True):
        """
        Initialize order manager
        
        Args:
            max_order_value: Maximum order value
            max_position_value: Maximum position value
            max_orders_per_symbol: Maximum orders per symbol
            enable_risk_checks: Enable risk checks
        """
        self.max_order_value = max_order_value
        self.max_position_value = max_position_value
        self.max_orders_per_symbol = max_orders_per_symbol
        self.enable_risk_checks = enable_risk_checks
        
        # Order tracking
        self.orders: Dict[str, Order] = {}
        self.orders_by_symbol: Dict[str, List[str]] = defaultdict(list)
        self.orders_by_strategy: Dict[str, List[str]] = defaultdict(list)
        
        # Position tracking
        self.positions: Dict[str, Position] = {}
        
        # Fill tracking
        self.fills: List[Fill] = []
        self.fills_by_symbol: Dict[str, List[Fill]] = defaultdict(list)
        
        # Performance metrics
        self.order_stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'cancelled_orders': 0,
            'rejected_orders': 0,
            'total_fill_value': 0.0,
            'total_commission': 0.0,
            'average_fill_time': 0.0
        }
        
        # Risk limits
        self.daily_order_count: Dict[str, int] = defaultdict(int)
        self.daily_volume: Dict[str, float] = defaultdict(float)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("OrderManager initialized with professional-grade capabilities")
    
    def submit_order(self, order: Order) -> bool:
        """
        Submit order with validation
        
        Args:
            order: Order to submit
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Pre-submission validation
            if not self._validate_order(order):
                order.status = OrderStatus.REJECTED
                order.notes = "Order validation failed"
                return False
            
            # Risk checks
            if self.enable_risk_checks and not self._check_risk_limits(order):
                order.status = OrderStatus.REJECTED
                order.notes = "Risk limit exceeded"
                return False
            
            # Store order
            self.orders[order.order_id] = order
            self.orders_by_symbol[order.symbol].append(order.order_id)
            self.orders_by_strategy[order.strategy_id].append(order.order_id)
            
            # Update status
            order.status = OrderStatus.SUBMITTED
            order.submitted_time = datetime.now()
            
            # Update statistics
            self.order_stats['total_orders'] += 1
            self.daily_order_count[order.symbol] += 1
            
            self.logger.info(f"Order submitted: {order.symbol} {order.side.value} {order.quantity}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Order submission failed: {str(e)}")
            order.status = OrderStatus.REJECTED
            order.notes = f"Submission error: {str(e)}"
            return False
    
    def fill_order(self, 
                  order_id: str,
                  fill_quantity: float,
                  fill_price: float,
                  commission: float = 0.0,
                  venue: str = "default") -> Optional[Fill]:
        """
        Process order fill
        
        Args:
            order_id: Order ID
            fill_quantity: Quantity filled
            fill_price: Fill price
            commission: Commission paid
            venue: Execution venue
            
        Returns:
            Fill object if successful, None otherwise
        """
        try:
            if order_id not in self.orders:
                self.logger.error(f"Order not found: {order_id}")
                return None
            
            order = self.orders[order_id]
            
            # Validate fill
            if fill_quantity <= 0:
                self.logger.error(f"Invalid fill quantity: {fill_quantity}")
                return None
            
            if fill_quantity > order.remaining_quantity:
                self.logger.error(f"Fill quantity exceeds remaining: {fill_quantity} > {order.remaining_quantity}")
                return None
            
            # Create fill
            fill = Fill(
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=fill_quantity,
                price=fill_price,
                commission=commission,
                venue=venue
            )
            
            # Add fill to order
            order.add_fill(fill)
            
            # Store fill
            self.fills.append(fill)
            self.fills_by_symbol[order.symbol].append(fill)
            
            # Update position
            self._update_position(fill)
            
            # Update statistics
            self.order_stats['total_fill_value'] += fill.notional_value
            self.order_stats['total_commission'] += commission
            self.daily_volume[order.symbol] += fill.notional_value
            
            if order.status == OrderStatus.FILLED:
                self.order_stats['filled_orders'] += 1
            
            self.logger.info(f"Order filled: {order.symbol} {fill_quantity}@{fill_price}")
            
            return fill
            
        except Exception as e:
            self.logger.error(f"Fill processing failed: {str(e)}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        try:
            if order_id not in self.orders:
                return False
            
            order = self.orders[order_id]
            
            if order.is_complete:
                self.logger.warning(f"Cannot cancel completed order: {order_id}")
                return False
            
            order.status = OrderStatus.CANCELLED
            order.last_update_time = datetime.now()
            
            self.order_stats['cancelled_orders'] += 1
            
            self.logger.info(f"Order cancelled: {order_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Order cancellation failed: {str(e)}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get orders by symbol"""
        order_ids = self.orders_by_symbol.get(symbol, [])
        return [self.orders[order_id] for order_id in order_ids if order_id in self.orders]
    
    def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get active orders"""
        orders = []
        
        if symbol:
            order_ids = self.orders_by_symbol.get(symbol, [])
            orders = [self.orders[order_id] for order_id in order_ids if order_id in self.orders]
        else:
            orders = list(self.orders.values())
        
        return [order for order in orders if order.is_active]
    
    def get_pending_orders(self) -> List[Order]:
        """Get pending orders"""
        return [order for order in self.orders.values() if order.status == OrderStatus.PENDING]
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all positions"""
        return dict(self.positions)
    
    def get_non_zero_positions(self) -> Dict[str, Position]:
        """Get non-zero positions"""
        return {symbol: pos for symbol, pos in self.positions.items() if not pos.is_flat}
    
    def get_fills_by_symbol(self, symbol: str) -> List[Fill]:
        """Get fills by symbol"""
        return self.fills_by_symbol.get(symbol, [])
    
    def get_recent_fills(self, hours: int = 24) -> List[Fill]:
        """Get recent fills"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [fill for fill in self.fills if fill.timestamp >= cutoff_time]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        active_orders = len(self.get_active_orders())
        non_zero_positions = len(self.get_non_zero_positions())
        
        # Calculate average fill time
        filled_orders = [order for order in self.orders.values() if order.status == OrderStatus.FILLED]
        avg_fill_time = 0.0
        if filled_orders:
            fill_times = []
            for order in filled_orders:
                if order.submitted_time and order.last_update_time:
                    fill_times.append((order.last_update_time - order.submitted_time).total_seconds())
            avg_fill_time = np.mean(fill_times) if fill_times else 0.0
        
        return {
            # Order statistics
            'total_orders': self.order_stats['total_orders'],
            'filled_orders': self.order_stats['filled_orders'],
            'cancelled_orders': self.order_stats['cancelled_orders'],
            'rejected_orders': self.order_stats['rejected_orders'],
            'active_orders': active_orders,
            'fill_rate': (self.order_stats['filled_orders'] / 
                         max(1, self.order_stats['total_orders'])) * 100,
            
            # Volume and value
            'total_fill_value': self.order_stats['total_fill_value'],
            'total_commission': self.order_stats['total_commission'],
            'average_fill_time': avg_fill_time,
            
            # Position statistics
            'total_positions': len(self.positions),
            'non_zero_positions': non_zero_positions,
            'total_unrealized_pnl': sum(pos.unrealized_pnl for pos in self.positions.values()),
            'total_realized_pnl': sum(pos.realized_pnl for pos in self.positions.values()),
            
            # Daily statistics
            'daily_order_counts': dict(self.daily_order_count),
            'daily_volumes': dict(self.daily_volume)
        }
    
    def _validate_order(self, order: Order) -> bool:
        """Validate order"""
        # Basic validation
        if order.quantity <= 0:
            self.logger.error(f"Invalid quantity: {order.quantity}")
            return False
        
        if not order.symbol:
            self.logger.error("Missing symbol")
            return False
        
        if order.order_type == OrderType.LIMIT and order.price is None:
            self.logger.error("Limit order missing price")
            return False
        
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and order.stop_price is None:
            self.logger.error("Stop order missing stop price")
            return False
        
        return True
    
    def _check_risk_limits(self, order: Order) -> bool:
        """Check risk limits"""
        # Order count limit
        if len(self.orders_by_symbol[order.symbol]) >= self.max_orders_per_symbol:
            self.logger.warning(f"Too many orders for {order.symbol}")
            return False
        
        # Order value limit (approximate)
        if order.price:
            order_value = order.quantity * order.price
            if order_value > self.max_order_value:
                self.logger.warning(f"Order value {order_value} exceeds limit {self.max_order_value}")
                return False
        
        # Position value limit
        current_position = self.positions.get(order.symbol)
        if current_position:
            new_quantity = current_position.quantity
            if order.side == OrderSide.BUY:
                new_quantity += order.quantity
            else:
                new_quantity -= order.quantity
            
            if order.price:
                position_value = abs(new_quantity * order.price)
                if position_value > self.max_position_value:
                    self.logger.warning(f"Position value {position_value} exceeds limit {self.max_position_value}")
                    return False
        
        return True
    
    def _update_position(self, fill: Fill):
        """Update position with fill"""
        if fill.symbol not in self.positions:
            self.positions[fill.symbol] = Position(symbol=fill.symbol)
        
        self.positions[fill.symbol].update_position(fill)
    
    def reset_daily_limits(self):
        """Reset daily limits (call at start of trading day)"""
        self.daily_order_count.clear()
        self.daily_volume.clear()
        self.logger.info("Daily limits reset") 