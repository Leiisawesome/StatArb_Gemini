"""
Professional Order Management and Position Tracking System
Handles order lifecycle, position tracking, and execution monitoring.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"

class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"

@dataclass
class Order:
    """Order representation."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    limit_price: Optional[float] = None
    time_in_force: str = "DAY"
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    parent_strategy: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Position:
    """Position representation."""
    symbol: str
    quantity: float
    avg_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    market_value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)

class OrderManager:
    """
    Professional order management system with position tracking.
    """
    
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.available_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.risk_limits = {
            'max_position_size': 0.1,  # 10% of capital per position
            'max_leverage': 2.0,       # 2x leverage
            'max_drawdown': 0.15,      # 15% max drawdown
            'position_limit': 20       # Max 20 positions
        }
        
    def submit_order(self, order: Order) -> str:
        """
        Submit an order for execution.
        
        Args:
            order: Order to submit
            
        Returns:
            Order ID
        """
        # Validate order
        if not self._validate_order(order):
            order.status = OrderStatus.REJECTED
            logger.error(f"Order validation failed for {order.symbol}")
            return order.order_id
        
        # Check risk limits
        if not self._check_risk_limits(order):
            order.status = OrderStatus.REJECTED
            logger.error(f"Risk limit exceeded for {order.symbol}")
            return order.order_id
        
        # Reserve capital
        required_capital = self._calculate_required_capital(order)
        if required_capital > self.available_capital:
            order.status = OrderStatus.REJECTED
            logger.error(f"Insufficient capital for {order.symbol}")
            return order.order_id
        
        # Submit order
        order.status = OrderStatus.SUBMITTED
        self.orders[order.order_id] = order
        self.available_capital -= required_capital
        
        logger.info(f"Order submitted: {order.order_id} for {order.symbol}")
        return order.order_id
    
    def update_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update order status and details.
        
        Args:
            order_id: Order ID to update
            updates: Updates to apply
            
        Returns:
            Success status
        """
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        
        # Update order fields
        for key, value in updates.items():
            if hasattr(order, key):
                setattr(order, key, value)
        
        # Handle fills
        if 'filled_quantity' in updates:
            self._handle_fill(order, updates['filled_quantity'], updates.get('fill_price', order.price))
        
        # Handle order completion
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            self._complete_order(order)
        
        logger.info(f"Order updated: {order_id} - {order.status.value}")
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Success status
        """
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        order.status = OrderStatus.CANCELLED
        
        # Return reserved capital
        self._return_reserved_capital(order)
        
        logger.info(f"Order cancelled: {order_id}")
        return True
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for a symbol."""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all current positions."""
        return self.positions.copy()
    
    def update_position_prices(self, price_updates: Dict[str, float]):
        """
        Update position prices and calculate P&L.
        
        Args:
            price_updates: Dictionary of symbol -> price updates
        """
        for symbol, price in price_updates.items():
            if symbol in self.positions:
                position = self.positions[symbol]
                old_value = position.market_value
                position.market_value = position.quantity * price
                position.unrealized_pnl = position.market_value - (position.quantity * position.avg_price)
                position.total_pnl = position.realized_pnl + position.unrealized_pnl
                position.last_update = datetime.now()
                
                # Log significant P&L changes
                pnl_change = position.market_value - old_value
                if abs(pnl_change) > 1000:  # $1k threshold
                    logger.info(f"Position P&L update: {symbol} = ${pnl_change:.2f}")
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary.
        
        Returns:
            Portfolio summary statistics
        """
        total_market_value = sum(pos.market_value for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        
        # Calculate portfolio metrics
        portfolio_return = (total_market_value + total_realized_pnl - self.initial_capital) / self.initial_capital
        leverage = total_market_value / (self.initial_capital + total_realized_pnl)
        
        # Calculate drawdown
        peak_value = max([float(pos.market_value + pos.realized_pnl) for pos in self.positions.values()] + [self.initial_capital])
        current_value = self.initial_capital + total_realized_pnl + total_unrealized_pnl
        drawdown = (peak_value - current_value) / peak_value if peak_value > 0 else 0
        
        return {
            'total_market_value': total_market_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': total_realized_pnl,
            'total_pnl': total_unrealized_pnl + total_realized_pnl,
            'portfolio_return': portfolio_return,
            'leverage': leverage,
            'drawdown': drawdown,
            'available_capital': self.available_capital,
            'position_count': len(self.positions),
            'active_orders': len([o for o in self.orders.values() if o.status not in [OrderStatus.FILLED, OrderStatus.CANCELLED]])
        }
    
    def _validate_order(self, order: Order) -> bool:
        """Validate order parameters."""
        if order.quantity <= 0:
            logger.error(f"Invalid quantity: {order.quantity}")
            return False
        
        if order.order_type == OrderType.LIMIT and order.price is None:
            logger.error("Limit order requires price")
            return False
        
        if order.order_type == OrderType.STOP and order.stop_price is None:
            logger.error("Stop order requires stop price")
            return False
        
        return True
    
    def _check_risk_limits(self, order: Order) -> bool:
        """Check risk limits for order."""
        # Position size limit
        current_position = self.positions.get(order.symbol, Position(order.symbol, 0, 0))
        new_quantity = current_position.quantity + (order.quantity if order.side == OrderSide.BUY else -order.quantity)
        
        if abs(new_quantity) * (order.price or 100) > self.initial_capital * self.risk_limits['max_position_size']:
            logger.warning(f"Position size limit exceeded for {order.symbol}")
            return False
        
        # Leverage limit
        total_exposure = sum(abs(pos.quantity) * (pos.avg_price or 100) for pos in self.positions.values())
        new_exposure = total_exposure + order.quantity * (order.price or 100)
        
        if new_exposure > (self.initial_capital + sum(pos.realized_pnl for pos in self.positions.values())) * self.risk_limits['max_leverage']:
            logger.warning(f"Leverage limit exceeded")
            return False
        
        return True
    
    def _calculate_required_capital(self, order: Order) -> float:
        """Calculate required capital for order."""
        price = order.price or 100  # Default price for estimation
        return order.quantity * price
    
    def _handle_fill(self, order: Order, filled_qty: float, fill_price: float):
        """Handle order fill."""
        if filled_qty <= 0:
            return
        
        # Update order
        order.filled_quantity += filled_qty
        total_cost = order.avg_fill_price * (order.filled_quantity - filled_qty) + fill_price * filled_qty
        order.avg_fill_price = total_cost / order.filled_quantity
        
        # Update position
        self._update_position(order.symbol, order.side, filled_qty, fill_price)
        
        # Update order status
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIAL_FILL
        
        # Record trade
        self._record_trade(order, filled_qty, fill_price)
    
    def _update_position(self, symbol: str, side: OrderSide, quantity: float, price: float):
        """Update position after fill."""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol, 0, 0)
        
        position = self.positions[symbol]
        
        if side == OrderSide.BUY:
            # Buying - increase position
            total_cost = position.quantity * position.avg_price + quantity * price
            position.quantity += quantity
            position.avg_price = total_cost / position.quantity if position.quantity > 0 else 0
        else:
            # Selling - decrease position
            if position.quantity > 0:
                # Calculate realized P&L
                realized_pnl = (price - position.avg_price) * min(quantity, position.quantity)
                position.realized_pnl += realized_pnl
            
            position.quantity -= quantity
            if position.quantity <= 0:
                position.quantity = 0
                position.avg_price = 0
        
        position.market_value = position.quantity * price
        position.unrealized_pnl = position.market_value - (position.quantity * position.avg_price)
        position.total_pnl = position.realized_pnl + position.unrealized_pnl
        position.last_update = datetime.now()
    
    def _record_trade(self, order: Order, quantity: float, price: float):
        """Record trade in history."""
        trade = {
            'timestamp': datetime.now(),
            'order_id': order.order_id,
            'symbol': order.symbol,
            'side': order.side.value,
            'quantity': quantity,
            'price': price,
            'notional': quantity * price,
            'commission': order.commission * (quantity / order.quantity) if order.quantity > 0 else 0,
            'strategy': order.parent_strategy
        }
        self.trade_history.append(trade)
    
    def _complete_order(self, order: Order):
        """Complete order processing."""
        # Return unused reserved capital
        self._return_reserved_capital(order)
        
        # Move to history
        self.order_history.append(order)
        del self.orders[order.order_id]
    
    def _return_reserved_capital(self, order: Order):
        """Return reserved capital for order."""
        if order.status == OrderStatus.SUBMITTED:
            unused_quantity = order.quantity - order.filled_quantity
            price = order.price or 100
            returned_capital = unused_quantity * price
            self.available_capital += returned_capital

class PositionManager:
    """
    Advanced position management with risk controls and optimization.
    """
    
    def __init__(self, order_manager: OrderManager):
        self.order_manager = order_manager
        self.position_limits = {}
        self.correlation_matrix = pd.DataFrame()
        self.volatility_estimates = {}
        
    def set_position_limit(self, symbol: str, max_notional: float):
        """Set position limit for symbol."""
        self.position_limits[symbol] = max_notional
    
    def update_correlation_matrix(self, returns_data: pd.DataFrame):
        """Update correlation matrix for position sizing."""
        self.correlation_matrix = returns_data.corr()
    
    def update_volatility_estimates(self, volatility_estimates: Dict[str, float]):
        """Update volatility estimates for risk calculation."""
        self.volatility_estimates.update(volatility_estimates)
    
    def calculate_optimal_position_size(self, 
                                      symbol: str, 
                                      signal_strength: float,
                                      current_price: float,
                                      target_volatility: float = 0.15) -> float:
        """
        Calculate optimal position size based on risk metrics.
        
        Args:
            symbol: Trading symbol
            signal_strength: Signal strength (-1 to 1)
            current_price: Current market price
            target_volatility: Target portfolio volatility
            
        Returns:
            Optimal position size
        """
        # Get current volatility
        volatility = self.volatility_estimates.get(symbol, 0.20)
        
        # Calculate base position size
        base_size = abs(signal_strength) * self.order_manager.initial_capital * target_volatility / volatility
        
        # Apply position limits
        if symbol in self.position_limits:
            max_size = self.position_limits[symbol] / current_price
            base_size = min(base_size, max_size)
        
        # Apply correlation adjustment
        correlation_penalty = self._calculate_correlation_penalty(symbol)
        adjusted_size = base_size * correlation_penalty
        
        return adjusted_size
    
    def _calculate_correlation_penalty(self, symbol: str) -> float:
        """Calculate correlation penalty for position sizing."""
        if symbol not in self.correlation_matrix.index:
            return 1.0
        
        # Calculate average correlation with existing positions
        existing_positions = [s for s in self.order_manager.positions.keys() if s != symbol]
        if not existing_positions:
            return 1.0
        
        correlations = []
        for pos_symbol in existing_positions:
            if pos_symbol in self.correlation_matrix.columns:
                corr = abs(self.correlation_matrix.loc[symbol, pos_symbol])
                correlations.append(corr)
        
        if not correlations:
            return 1.0
        
        avg_correlation = np.mean(correlations)
        # Reduce position size for highly correlated positions
        penalty = 1.0 - avg_correlation * 0.5
        return max(penalty, 0.1)  # Minimum 10% position size
    
    def rebalance_portfolio(self, target_weights: Dict[str, float], 
                           current_prices: Dict[str, float]) -> List[Order]:
        """
        Generate rebalancing orders to achieve target weights.
        
        Args:
            target_weights: Target portfolio weights
            current_prices: Current market prices
            
        Returns:
            List of rebalancing orders
        """
        orders = []
        current_positions = self.order_manager.get_all_positions()
        total_value = sum(pos.market_value for pos in current_positions.values())
        
        for symbol, target_weight in target_weights.items():
            target_value = total_value * target_weight
            current_value = current_positions.get(symbol, Position(symbol, 0, 0)).market_value
            
            if abs(target_value - current_value) > 1000:  # $1k minimum rebalance
                target_quantity = target_value / current_prices[symbol]
                current_quantity = current_positions.get(symbol, Position(symbol, 0, 0)).quantity
                
                quantity_diff = target_quantity - current_quantity
                
                if abs(quantity_diff) > 0:
                    side = OrderSide.BUY if quantity_diff > 0 else OrderSide.SELL
                    order = Order(
                        order_id=str(uuid.uuid4()),
                        symbol=symbol,
                        side=side,
                        order_type=OrderType.MARKET,
                        quantity=abs(quantity_diff),
                        parent_strategy="rebalancing"
                    )
                    orders.append(order)
        
        return orders 