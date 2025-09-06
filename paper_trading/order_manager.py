#!/usr/bin/env python3
"""
Advanced Order Management System
================================

Professional order management with advanced order types:
- Stop-loss orders (fixed and percentage-based)
- Take-profit orders (fixed and percentage-based)
- Trailing stops (dynamic stop-loss that follows price)
- Time-based exits (close positions after specified duration)
- Bracket orders (combined stop-loss and take-profit)

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Advanced order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"
    TIME_EXIT = "TIME_EXIT"
    BRACKET = "BRACKET"

class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

class OrderSide(Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class AdvancedOrder:
    """Advanced order with risk management features"""
    order_id: str
    symbol: str
    quantity: float
    order_type: OrderType
    side: OrderSide
    
    # Price parameters
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Advanced parameters
    trailing_amount: Optional[float] = None  # For trailing stops
    trailing_percent: Optional[float] = None  # Percentage-based trailing
    time_in_force: str = "DAY"
    expire_time: Optional[datetime] = None
    
    # Parent order (for bracket orders)
    parent_order_id: Optional[str] = None
    child_orders: List[str] = field(default_factory=list)
    
    # Execution tracking
    status: OrderStatus = OrderStatus.PENDING
    created_time: datetime = field(default_factory=datetime.now)
    filled_time: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    
    # Risk management
    strategy_id: str = ""
    position_id: str = ""
    
    # Trailing stop tracking
    highest_price: Optional[float] = None  # For trailing stops
    lowest_price: Optional[float] = None   # For trailing stops (short positions)

@dataclass
class Position:
    """Enhanced position with order management"""
    position_id: str
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    strategy_id: str
    side: str  # "LONG" or "SHORT"
    
    # Risk management orders
    stop_loss_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None
    trailing_stop_order_id: Optional[str] = None
    time_exit_order_id: Optional[str] = None
    
    # P&L tracking
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Risk parameters
    max_loss_pct: Optional[float] = None
    target_profit_pct: Optional[float] = None
    max_hold_time: Optional[timedelta] = None

class AdvancedOrderManager:
    """
    Advanced Order Management System
    
    Features:
    - Multiple order types with sophisticated logic
    - Automatic risk management order placement
    - Real-time order monitoring and execution
    - Position-based order management
    - Performance tracking and analytics
    """
    
    def __init__(self):
        # Order storage
        self.orders: Dict[str, AdvancedOrder] = {}
        self.positions: Dict[str, Position] = {}
        
        # Order execution tracking
        self.execution_history: List[Dict] = []
        self.order_counter = 0
        
        # Risk management settings
        self.default_stop_loss_pct = 0.02  # 2% stop loss
        self.default_take_profit_pct = 0.04  # 4% take profit
        self.default_trailing_pct = 0.015   # 1.5% trailing stop
        self.default_max_hold_hours = 24    # 24 hour max hold
        
        # Performance tracking
        self.total_orders = 0
        self.filled_orders = 0
        self.cancelled_orders = 0
        self.stop_loss_triggers = 0
        self.take_profit_triggers = 0
        self.trailing_stop_triggers = 0
        
        logger.info("🎯 Advanced Order Manager initialized")
    
    def create_market_order(self, symbol: str, quantity: float, side: OrderSide, 
                           strategy_id: str = "", **kwargs) -> str:
        """Create a market order"""
        
        order_id = self._generate_order_id()
        
        order = AdvancedOrder(
            order_id=order_id,
            symbol=symbol,
            quantity=quantity,
            order_type=OrderType.MARKET,
            side=side,
            strategy_id=strategy_id,
            **kwargs
        )
        
        self.orders[order_id] = order
        self.total_orders += 1
        
        logger.info(f"📋 Market order created: {order_id} - {side.value} {quantity} {symbol}")
        return order_id
    
    def create_bracket_order(self, symbol: str, quantity: float, side: OrderSide,
                           entry_price: float, stop_loss_price: float, 
                           take_profit_price: float, strategy_id: str = "") -> Tuple[str, str, str]:
        """Create a bracket order (entry + stop loss + take profit)"""
        
        # Create parent entry order
        parent_id = self.create_limit_order(symbol, quantity, side, entry_price, strategy_id)
        
        # Create child orders
        stop_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
        
        stop_loss_id = self._create_child_order(
            parent_id, symbol, quantity, OrderType.STOP_LOSS, 
            stop_side, stop_price=stop_loss_price, strategy_id=strategy_id
        )
        
        take_profit_id = self._create_child_order(
            parent_id, symbol, quantity, OrderType.TAKE_PROFIT,
            stop_side, limit_price=take_profit_price, strategy_id=strategy_id
        )
        
        # Link orders
        self.orders[parent_id].child_orders = [stop_loss_id, take_profit_id]
        
        logger.info(f"📋 Bracket order created: Entry={parent_id}, SL={stop_loss_id}, TP={take_profit_id}")
        return parent_id, stop_loss_id, take_profit_id
    
    def create_limit_order(self, symbol: str, quantity: float, side: OrderSide,
                          limit_price: float, strategy_id: str = "", **kwargs) -> str:
        """Create a limit order"""
        
        order_id = self._generate_order_id()
        
        order = AdvancedOrder(
            order_id=order_id,
            symbol=symbol,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            side=side,
            limit_price=limit_price,
            strategy_id=strategy_id,
            **kwargs
        )
        
        self.orders[order_id] = order
        self.total_orders += 1
        
        logger.info(f"📋 Limit order created: {order_id} - {side.value} {quantity} {symbol} @ ${limit_price:.2f}")
        return order_id
    
    def create_stop_loss_order(self, position_id: str, stop_price: Optional[float] = None,
                              stop_pct: Optional[float] = None) -> str:
        """Create a stop-loss order for existing position"""
        
        position = self.positions.get(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        # Calculate stop price
        if stop_price is None:
            if stop_pct is None:
                stop_pct = self.default_stop_loss_pct
            
            if position.side == "LONG":
                stop_price = position.entry_price * (1 - stop_pct)
            else:
                stop_price = position.entry_price * (1 + stop_pct)
        
        # Create stop loss order
        side = OrderSide.SELL if position.side == "LONG" else OrderSide.BUY
        order_id = self._generate_order_id()
        
        order = AdvancedOrder(
            order_id=order_id,
            symbol=position.symbol,
            quantity=abs(position.quantity),
            order_type=OrderType.STOP_LOSS,
            side=side,
            stop_price=stop_price,
            strategy_id=position.strategy_id,
            position_id=position_id
        )
        
        self.orders[order_id] = order
        position.stop_loss_order_id = order_id
        
        logger.info(f"🛡️  Stop-loss created: {order_id} - {position.symbol} @ ${stop_price:.2f}")
        return order_id
    
    def create_take_profit_order(self, position_id: str, target_price: Optional[float] = None,
                                target_pct: Optional[float] = None) -> str:
        """Create a take-profit order for existing position"""
        
        position = self.positions.get(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        # Calculate target price
        if target_price is None:
            if target_pct is None:
                target_pct = self.default_take_profit_pct
            
            if position.side == "LONG":
                target_price = position.entry_price * (1 + target_pct)
            else:
                target_price = position.entry_price * (1 - target_pct)
        
        # Create take profit order
        side = OrderSide.SELL if position.side == "LONG" else OrderSide.BUY
        order_id = self._generate_order_id()
        
        order = AdvancedOrder(
            order_id=order_id,
            symbol=position.symbol,
            quantity=abs(position.quantity),
            order_type=OrderType.TAKE_PROFIT,
            side=side,
            limit_price=target_price,
            strategy_id=position.strategy_id,
            position_id=position_id
        )
        
        self.orders[order_id] = order
        position.take_profit_order_id = order_id
        
        logger.info(f"🎯 Take-profit created: {order_id} - {position.symbol} @ ${target_price:.2f}")
        return order_id
    
    def create_trailing_stop_order(self, position_id: str, trailing_pct: Optional[float] = None,
                                  trailing_amount: Optional[float] = None) -> str:
        """Create a trailing stop order for existing position"""
        
        position = self.positions.get(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        if trailing_pct is None and trailing_amount is None:
            trailing_pct = self.default_trailing_pct
        
        # Create trailing stop order
        side = OrderSide.SELL if position.side == "LONG" else OrderSide.BUY
        order_id = self._generate_order_id()
        
        order = AdvancedOrder(
            order_id=order_id,
            symbol=position.symbol,
            quantity=abs(position.quantity),
            order_type=OrderType.TRAILING_STOP,
            side=side,
            trailing_pct=trailing_pct,
            trailing_amount=trailing_amount,
            strategy_id=position.strategy_id,
            position_id=position_id,
            highest_price=position.entry_price if position.side == "LONG" else None,
            lowest_price=position.entry_price if position.side == "SHORT" else None
        )
        
        self.orders[order_id] = order
        position.trailing_stop_order_id = order_id
        
        trail_desc = f"{trailing_pct:.1%}" if trailing_pct else f"${trailing_amount:.2f}"
        logger.info(f"📈 Trailing stop created: {order_id} - {position.symbol} trail: {trail_desc}")
        return order_id
    
    def create_time_exit_order(self, position_id: str, exit_time: datetime) -> str:
        """Create a time-based exit order"""
        
        position = self.positions.get(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        # Create time exit order
        side = OrderSide.SELL if position.side == "LONG" else OrderSide.BUY
        order_id = self._generate_order_id()
        
        order = AdvancedOrder(
            order_id=order_id,
            symbol=position.symbol,
            quantity=abs(position.quantity),
            order_type=OrderType.TIME_EXIT,
            side=side,
            expire_time=exit_time,
            strategy_id=position.strategy_id,
            position_id=position_id
        )
        
        self.orders[order_id] = order
        position.time_exit_order_id = order_id
        
        logger.info(f"⏰ Time exit created: {order_id} - {position.symbol} @ {exit_time}")
        return order_id
    
    def open_position_with_risk_management(self, symbol: str, quantity: float, 
                                         entry_price: float, strategy_id: str,
                                         side: str = "LONG",
                                         stop_loss_pct: Optional[float] = None,
                                         take_profit_pct: Optional[float] = None,
                                         use_trailing_stop: bool = False,
                                         max_hold_hours: Optional[int] = None) -> str:
        """Open position with automatic risk management orders"""
        
        # Create position
        position_id = f"pos_{strategy_id}_{symbol}_{datetime.now().strftime('%H%M%S')}"
        
        position = Position(
            position_id=position_id,
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=datetime.now(),
            strategy_id=strategy_id,
            side=side,
            max_loss_pct=stop_loss_pct,
            target_profit_pct=take_profit_pct,
            max_hold_time=timedelta(hours=max_hold_hours) if max_hold_hours else None
        )
        
        self.positions[position_id] = position
        
        # Create risk management orders
        risk_orders = []
        
        # Stop loss
        if stop_loss_pct:
            try:
                sl_order_id = self.create_stop_loss_order(position_id, stop_pct=stop_loss_pct)
                risk_orders.append(f"SL: {sl_order_id}")
            except Exception as e:
                logger.error(f"❌ Failed to create stop loss: {e}")
        
        # Take profit or trailing stop
        if use_trailing_stop:
            try:
                ts_order_id = self.create_trailing_stop_order(position_id)
                risk_orders.append(f"TS: {ts_order_id}")
            except Exception as e:
                logger.error(f"❌ Failed to create trailing stop: {e}")
        elif take_profit_pct:
            try:
                tp_order_id = self.create_take_profit_order(position_id, target_pct=take_profit_pct)
                risk_orders.append(f"TP: {tp_order_id}")
            except Exception as e:
                logger.error(f"❌ Failed to create take profit: {e}")
        
        # Time exit
        if max_hold_hours:
            try:
                exit_time = datetime.now() + timedelta(hours=max_hold_hours)
                te_order_id = self.create_time_exit_order(position_id, exit_time)
                risk_orders.append(f"TE: {te_order_id}")
            except Exception as e:
                logger.error(f"❌ Failed to create time exit: {e}")
        
        logger.info(f"📊 Position opened: {position_id} - {side} {quantity} {symbol} @ ${entry_price:.2f}")
        if risk_orders:
            logger.info(f"   Risk orders: {', '.join(risk_orders)}")
        
        return position_id
    
    async def update_market_data(self, symbol: str, current_price: float, 
                               bid: float, ask: float, volume: int = 0):
        """Update market data and check for order triggers"""
        
        # Update position P&L
        await self._update_position_pnl(symbol, current_price)
        
        # Check for order triggers
        await self._check_order_triggers(symbol, current_price, bid, ask)
    
    async def _update_position_pnl(self, symbol: str, current_price: float):
        """Update unrealized P&L for positions"""
        
        for position in self.positions.values():
            if position.symbol == symbol:
                if position.side == "LONG":
                    position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
                else:
                    position.unrealized_pnl = (position.entry_price - current_price) * position.quantity
    
    async def _check_order_triggers(self, symbol: str, current_price: float, 
                                  bid: float, ask: float):
        """Check if any orders should be triggered"""
        
        triggered_orders = []
        
        for order in self.orders.values():
            if order.symbol != symbol or order.status != OrderStatus.ACTIVE:
                continue
            
            should_trigger = False
            execution_price = current_price
            
            # Check different order types
            if order.order_type == OrderType.STOP_LOSS:
                if order.side == OrderSide.SELL and current_price <= order.stop_price:
                    should_trigger = True
                    execution_price = bid  # Market sell gets bid price
                elif order.side == OrderSide.BUY and current_price >= order.stop_price:
                    should_trigger = True
                    execution_price = ask  # Market buy gets ask price
            
            elif order.order_type == OrderType.TAKE_PROFIT:
                if order.side == OrderSide.SELL and current_price >= order.limit_price:
                    should_trigger = True
                    execution_price = order.limit_price  # Limit order gets limit price
                elif order.side == OrderSide.BUY and current_price <= order.limit_price:
                    should_trigger = True
                    execution_price = order.limit_price
            
            elif order.order_type == OrderType.TRAILING_STOP:
                should_trigger = await self._check_trailing_stop(order, current_price)
                if should_trigger:
                    execution_price = bid if order.side == OrderSide.SELL else ask
            
            elif order.order_type == OrderType.TIME_EXIT:
                if order.expire_time and datetime.now() >= order.expire_time:
                    should_trigger = True
                    execution_price = bid if order.side == OrderSide.SELL else ask
            
            elif order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and current_price <= order.limit_price:
                    should_trigger = True
                    execution_price = order.limit_price
                elif order.side == OrderSide.SELL and current_price >= order.limit_price:
                    should_trigger = True
                    execution_price = order.limit_price
            
            if should_trigger:
                triggered_orders.append((order, execution_price))
        
        # Execute triggered orders
        for order, execution_price in triggered_orders:
            await self._execute_order(order, execution_price)
    
    async def _check_trailing_stop(self, order: AdvancedOrder, current_price: float) -> bool:
        """Check if trailing stop should be triggered"""
        
        if order.order_type != OrderType.TRAILING_STOP:
            return False
        
        position = self.positions.get(order.position_id)
        if not position:
            return False
        
        # Update highest/lowest price
        if position.side == "LONG":
            if order.highest_price is None or current_price > order.highest_price:
                order.highest_price = current_price
            
            # Calculate trailing stop price
            if order.trailing_pct:
                stop_price = order.highest_price * (1 - order.trailing_pct)
            else:
                stop_price = order.highest_price - order.trailing_amount
            
            # Trigger if price drops below trailing stop
            return current_price <= stop_price
        
        else:  # SHORT position
            if order.lowest_price is None or current_price < order.lowest_price:
                order.lowest_price = current_price
            
            # Calculate trailing stop price
            if order.trailing_pct:
                stop_price = order.lowest_price * (1 + order.trailing_pct)
            else:
                stop_price = order.lowest_price + order.trailing_amount
            
            # Trigger if price rises above trailing stop
            return current_price >= stop_price
    
    async def _execute_order(self, order: AdvancedOrder, execution_price: float):
        """Execute a triggered order"""
        
        try:
            # Update order status
            order.status = OrderStatus.FILLED
            order.filled_time = datetime.now()
            order.filled_price = execution_price
            order.filled_quantity = order.quantity
            
            # Track execution
            self.filled_orders += 1
            
            # Log execution with order type
            order_type_desc = {
                OrderType.STOP_LOSS: "🛡️  STOP LOSS",
                OrderType.TAKE_PROFIT: "🎯 TAKE PROFIT", 
                OrderType.TRAILING_STOP: "📈 TRAILING STOP",
                OrderType.TIME_EXIT: "⏰ TIME EXIT",
                OrderType.LIMIT: "📋 LIMIT",
                OrderType.MARKET: "📋 MARKET"
            }.get(order.order_type, "📋 ORDER")
            
            logger.info(f"{order_type_desc} EXECUTED: {order.order_id} - "
                       f"{order.side.value} {order.quantity} {order.symbol} @ ${execution_price:.2f}")
            
            # Update position if this closes it
            if order.position_id:
                await self._close_position(order.position_id, execution_price, order.order_type)
            
            # Cancel related orders for bracket/OCO orders
            await self._cancel_related_orders(order)
            
            # Record execution
            self.execution_history.append({
                'timestamp': datetime.now(),
                'order_id': order.order_id,
                'symbol': order.symbol,
                'side': order.side.value,
                'quantity': order.quantity,
                'price': execution_price,
                'order_type': order.order_type.value,
                'strategy_id': order.strategy_id
            })
            
            # Update trigger counters
            if order.order_type == OrderType.STOP_LOSS:
                self.stop_loss_triggers += 1
            elif order.order_type == OrderType.TAKE_PROFIT:
                self.take_profit_triggers += 1
            elif order.order_type == OrderType.TRAILING_STOP:
                self.trailing_stop_triggers += 1
            
        except Exception as e:
            logger.error(f"❌ Error executing order {order.order_id}: {e}")
            order.status = OrderStatus.CANCELLED
    
    async def _close_position(self, position_id: str, exit_price: float, exit_reason: OrderType):
        """Close a position and calculate realized P&L"""
        
        position = self.positions.get(position_id)
        if not position:
            return
        
        # Calculate realized P&L
        if position.side == "LONG":
            realized_pnl = (exit_price - position.entry_price) * position.quantity
        else:
            realized_pnl = (position.entry_price - exit_price) * position.quantity
        
        position.realized_pnl = realized_pnl
        
        # Log position closure
        hold_time = datetime.now() - position.entry_time
        return_pct = realized_pnl / (position.entry_price * position.quantity) * 100
        
        exit_reason_desc = {
            OrderType.STOP_LOSS: "Stop Loss",
            OrderType.TAKE_PROFIT: "Take Profit",
            OrderType.TRAILING_STOP: "Trailing Stop", 
            OrderType.TIME_EXIT: "Time Exit",
            OrderType.MARKET: "Manual Exit"
        }.get(exit_reason, "Exit")
        
        logger.info(f"📊 Position closed: {position_id} - {exit_reason_desc}")
        logger.info(f"   Entry: ${position.entry_price:.2f} → Exit: ${exit_price:.2f}")
        logger.info(f"   P&L: ${realized_pnl:.2f} ({return_pct:+.2f}%) | Hold: {hold_time}")
        
        # Cancel any remaining risk management orders
        await self._cancel_position_orders(position_id)
    
    async def _cancel_related_orders(self, executed_order: AdvancedOrder):
        """Cancel related orders (for bracket orders)"""
        
        if executed_order.position_id:
            position = self.positions.get(executed_order.position_id)
            if position:
                # Cancel other risk management orders for this position
                orders_to_cancel = []
                
                if position.stop_loss_order_id and position.stop_loss_order_id != executed_order.order_id:
                    orders_to_cancel.append(position.stop_loss_order_id)
                
                if position.take_profit_order_id and position.take_profit_order_id != executed_order.order_id:
                    orders_to_cancel.append(position.take_profit_order_id)
                
                if position.trailing_stop_order_id and position.trailing_stop_order_id != executed_order.order_id:
                    orders_to_cancel.append(position.trailing_stop_order_id)
                
                if position.time_exit_order_id and position.time_exit_order_id != executed_order.order_id:
                    orders_to_cancel.append(position.time_exit_order_id)
                
                for order_id in orders_to_cancel:
                    await self.cancel_order(order_id)
    
    async def _cancel_position_orders(self, position_id: str):
        """Cancel all orders for a position"""
        
        position = self.positions.get(position_id)
        if not position:
            return
        
        orders_to_cancel = [
            position.stop_loss_order_id,
            position.take_profit_order_id,
            position.trailing_stop_order_id,
            position.time_exit_order_id
        ]
        
        for order_id in orders_to_cancel:
            if order_id:
                await self.cancel_order(order_id)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        
        order = self.orders.get(order_id)
        if not order:
            return False
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            return False
        
        order.status = OrderStatus.CANCELLED
        self.cancelled_orders += 1
        
        logger.info(f"❌ Order cancelled: {order_id}")
        return True
    
    def activate_orders(self):
        """Activate all pending orders"""
        
        activated_count = 0
        for order in self.orders.values():
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.ACTIVE
                activated_count += 1
        
        if activated_count > 0:
            logger.info(f"✅ Activated {activated_count} orders")
    
    def _create_child_order(self, parent_id: str, symbol: str, quantity: float,
                           order_type: OrderType, side: OrderSide, 
                           strategy_id: str = "", **kwargs) -> str:
        """Create a child order for bracket orders"""
        
        order_id = self._generate_order_id()
        
        order = AdvancedOrder(
            order_id=order_id,
            symbol=symbol,
            quantity=quantity,
            order_type=order_type,
            side=side,
            parent_order_id=parent_id,
            strategy_id=strategy_id,
            **kwargs
        )
        
        self.orders[order_id] = order
        return order_id
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        self.order_counter += 1
        return f"ord_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.order_counter:04d}"
    
    def get_active_orders(self, symbol: Optional[str] = None, 
                         strategy_id: Optional[str] = None) -> List[AdvancedOrder]:
        """Get active orders with optional filtering"""
        
        orders = [order for order in self.orders.values() 
                 if order.status == OrderStatus.ACTIVE]
        
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        
        if strategy_id:
            orders = [order for order in orders if order.strategy_id == strategy_id]
        
        return orders
    
    def get_positions(self, symbol: Optional[str] = None,
                     strategy_id: Optional[str] = None) -> List[Position]:
        """Get positions with optional filtering"""
        
        positions = list(self.positions.values())
        
        if symbol:
            positions = [pos for pos in positions if pos.symbol == symbol]
        
        if strategy_id:
            positions = [pos for pos in positions if pos.strategy_id == strategy_id]
        
        return positions
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get order management performance summary"""
        
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        return {
            "order_statistics": {
                "total_orders": self.total_orders,
                "filled_orders": self.filled_orders,
                "cancelled_orders": self.cancelled_orders,
                "fill_rate": self.filled_orders / max(self.total_orders, 1)
            },
            "risk_management": {
                "stop_loss_triggers": self.stop_loss_triggers,
                "take_profit_triggers": self.take_profit_triggers,
                "trailing_stop_triggers": self.trailing_stop_triggers
            },
            "position_summary": {
                "active_positions": len(self.positions),
                "total_realized_pnl": total_realized_pnl,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_pnl": total_realized_pnl + total_unrealized_pnl
            },
            "recent_executions": self.execution_history[-10:]  # Last 10 executions
        }
