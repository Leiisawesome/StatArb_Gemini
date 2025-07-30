#!/usr/bin/env python3
"""
Order Management System
Phase 2: Core System Integration - Batch 2
"""

import logging
import uuid
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import pandas as pd

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderSide(Enum):
    """Order sides"""
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class Order:
    """Order object"""
    
    def __init__(self, symbol: str, side: OrderSide, quantity: int, 
                 order_type: OrderType = OrderType.MARKET, 
                 limit_price: float = None, stop_price: float = None):
        self.order_id = str(uuid.uuid4())
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.order_type = order_type
        self.limit_price = limit_price
        self.stop_price = stop_price
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0
        self.avg_fill_price = 0.0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.fills = []
        
        logger.info(f"Created order {self.order_id}: {side.value} {quantity} {symbol} @ {order_type.value}")

class OrderManager:
    """Order management system"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.available_capital = initial_capital
        self.orders = {}
        self.order_history = []
        self.execution_callbacks = []
        self.risk_callbacks = []
        
        # Order tracking
        self.pending_orders = []
        self.filled_orders = []
        self.cancelled_orders = []
        
        logger.info(f"Initialized OrderManager with ${initial_capital:,.2f} capital")
    
    def add_execution_callback(self, callback: Callable):
        """Add callback for order execution events"""
        self.execution_callbacks.append(callback)
        logger.info(f"Added execution callback: {callback.__name__}")
    
    def add_risk_callback(self, callback: Callable):
        """Add callback for risk management events"""
        self.risk_callbacks.append(callback)
        logger.info(f"Added risk callback: {callback.__name__}")
    
    def create_order(self, symbol: str, side: OrderSide, quantity: int,
                    order_type: OrderType = OrderType.MARKET,
                    limit_price: float = None, stop_price: float = None) -> Order:
        """Create a new order"""
        
        # Validate order parameters
        if quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}")
        
        if order_type == OrderType.LIMIT and limit_price is None:
            raise ValueError("Limit price required for LIMIT orders")
        
        if order_type == OrderType.STOP and stop_price is None:
            raise ValueError("Stop price required for STOP orders")
        
        # Create order
        order = Order(symbol, side, quantity, order_type, limit_price, stop_price)
        
        # Store order
        self.orders[order.order_id] = order
        self.pending_orders.append(order)
        
        logger.info(f"Created order {order.order_id}: {side.value} {quantity} {symbol}")
        return order
    
    def submit_order(self, order_id: str) -> bool:
        """Submit an order for execution"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        if order.status != OrderStatus.PENDING:
            logger.warning(f"Order {order_id} is not pending (status: {order.status})")
            return False
        
        # Update status
        order.status = OrderStatus.SUBMITTED
        order.updated_at = datetime.now()
        
        logger.info(f"Submitted order {order_id}: {order.side.value} {order.quantity} {order.symbol}")
        
        # Notify callbacks
        for callback in self.execution_callbacks:
            try:
                callback(order, "SUBMITTED")
            except Exception as e:
                logger.error(f"Execution callback error: {e}")
        
        return True
    
    def execute_order(self, order_id: str, fill_price: float, fill_quantity: int = None) -> bool:
        """Execute an order (simulate fill)"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        if order.status not in [OrderStatus.SUBMITTED, OrderStatus.PARTIAL]:
            logger.warning(f"Order {order_id} is not submitted (status: {order.status})")
            return False
        
        # Determine fill quantity
        if fill_quantity is None:
            fill_quantity = order.quantity - order.filled_quantity
        
        # Validate fill
        remaining_quantity = order.quantity - order.filled_quantity
        if fill_quantity > remaining_quantity:
            fill_quantity = remaining_quantity
        
        if fill_quantity <= 0:
            logger.warning(f"No remaining quantity to fill for order {order_id}")
            return False
        
        # Record fill
        fill = {
            'timestamp': datetime.now(),
            'price': fill_price,
            'quantity': fill_quantity
        }
        order.fills.append(fill)
        
        # Update order
        order.filled_quantity += fill_quantity
        order.avg_fill_price = ((order.avg_fill_price * (order.filled_quantity - fill_quantity)) + 
                               (fill_price * fill_quantity)) / order.filled_quantity
        order.updated_at = datetime.now()
        
        # Update status
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
            self.filled_orders.append(order)
            if order in self.pending_orders:
                self.pending_orders.remove(order)
        else:
            order.status = OrderStatus.PARTIAL
        
        # Update capital
        fill_value = fill_price * fill_quantity
        if order.side == OrderSide.BUY:
            self.available_capital -= fill_value
        else:
            self.available_capital += fill_value
        
        logger.info(f"Executed order {order_id}: {fill_quantity} @ ${fill_price:.2f} "
                   f"(Total: {order.filled_quantity}/{order.quantity})")
        
        # Notify callbacks
        for callback in self.execution_callbacks:
            try:
                callback(order, "FILLED", fill)
            except Exception as e:
                logger.error(f"Execution callback error: {e}")
        
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL]:
            logger.warning(f"Order {order_id} cannot be cancelled (status: {order.status})")
            return False
        
        # Update status
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        
        # Move to cancelled list
        self.cancelled_orders.append(order)
        if order in self.pending_orders:
            self.pending_orders.remove(order)
        
        logger.info(f"Cancelled order {order_id}")
        
        # Notify callbacks
        for callback in self.execution_callbacks:
            try:
                callback(order, "CANCELLED")
            except Exception as e:
                logger.error(f"Execution callback error: {e}")
        
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders"""
        return self.pending_orders.copy()
    
    def get_filled_orders(self) -> List[Order]:
        """Get all filled orders"""
        return self.filled_orders.copy()
    
    def get_order_summary(self) -> Dict:
        """Get order management summary"""
        total_orders = len(self.orders)
        pending_orders = len(self.pending_orders)
        filled_orders = len(self.filled_orders)
        cancelled_orders = len(self.cancelled_orders)
        
        total_fill_value = sum(
            order.avg_fill_price * order.filled_quantity 
            for order in self.filled_orders
        )
        
        return {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'filled_orders': filled_orders,
            'cancelled_orders': cancelled_orders,
            'available_capital': self.available_capital,
            'total_fill_value': total_fill_value,
            'execution_callbacks': len(self.execution_callbacks),
            'risk_callbacks': len(self.risk_callbacks)
        } 