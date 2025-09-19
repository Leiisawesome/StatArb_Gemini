"""
Trading Engine - Order Manager
Comprehensive order management with lifecycle tracking, validation, and execution coordination
"""

import logging
import threading
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"
    IMPLEMENTATION_SHORTFALL = "implementation_shortfall"


class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status"""
    PENDING_NEW = "pending_new"
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    PENDING_CANCEL = "pending_cancel"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    PENDING_REPLACE = "pending_replace"
    REPLACED = "replaced"


class TimeInForce(Enum):
    """Time in force"""
    DAY = "day"
    GTC = "gtc"  # Good Till Canceled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill
    GTD = "gtd"  # Good Till Date


class OrderPriority(Enum):
    """Order priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class OrderExecution:
    """Order execution record"""
    execution_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime
    venue: str = ""
    commission: float = 0.0
    fees: float = 0.0
    liquidity_flag: str = ""  # "A" for aggressive, "P" for passive
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    """Comprehensive order representation"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    status: OrderStatus = OrderStatus.PENDING_NEW
    priority: OrderPriority = OrderPriority.NORMAL
    
    # Timestamps
    created_time: datetime = field(default_factory=datetime.now)
    submitted_time: Optional[datetime] = None
    last_update_time: datetime = field(default_factory=datetime.now)
    expiry_time: Optional[datetime] = None
    
    # Execution tracking
    filled_quantity: float = 0.0
    remaining_quantity: Optional[float] = None
    average_fill_price: Optional[float] = None
    executions: List[OrderExecution] = field(default_factory=list)
    
    # Order attributes
    parent_order_id: Optional[str] = None
    strategy_id: Optional[str] = None
    account_id: Optional[str] = None
    trader_id: Optional[str] = None
    
    # Risk and compliance
    risk_checked: bool = False
    compliance_checked: bool = False
    rejection_reason: Optional[str] = None
    
    # Advanced order parameters
    iceberg_visible_quantity: Optional[float] = None
    trailing_amount: Optional[float] = None
    trailing_percent: Optional[float] = None
    
    # Execution algorithm parameters
    algo_params: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
    
    @property
    def is_complete(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        """Check if order is still active"""
        return self.status in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def fill_ratio(self) -> float:
        """Get fill ratio (0.0 to 1.0)"""
        return self.filled_quantity / self.quantity if self.quantity > 0 else 0.0


@dataclass
class OrderValidationResult:
    """Order validation result"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrderManager:
    """
    Comprehensive order management system
    
    Handles order lifecycle, validation, execution tracking, and risk management
    with support for complex order types and execution algorithms.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize order manager"""
        self.config = config or {}
        self._lock = threading.Lock()
        self._orders = {}  # order_id -> Order
        self._order_history = deque(maxlen=10000)
        self._execution_history = deque(maxlen=10000)
        
        # Order tracking by various criteria
        self._orders_by_symbol = defaultdict(list)
        self._orders_by_strategy = defaultdict(list)
        self._orders_by_status = defaultdict(list)
        
        # Event handlers
        self._order_event_handlers = []
        self._execution_event_handlers = []
        
        # Configuration
        self.max_order_age_hours = self.config.get('max_order_age_hours', 24)
        self.auto_expire_orders = self.config.get('auto_expire_orders', True)
        self.enable_order_validation = self.config.get('enable_order_validation', True)
        
        # Risk limits
        self.max_order_value = self.config.get('max_order_value', 1000000)
        self.max_quantity_per_order = self.config.get('max_quantity_per_order', 10000)
        self.blocked_symbols = set(self.config.get('blocked_symbols', []))
        
        # Performance tracking
        self._order_metrics = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_canceled': 0,
            'orders_rejected': 0,
            'total_execution_value': 0.0,
            'average_fill_time': 0.0
        }
        
        logger.info("OrderManager initialized")
    
    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        **kwargs
    ) -> Order:
        """
        Create a new order
        
        Args:
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            quantity: Order quantity
            order_type: Order type
            price: Limit price (for limit orders)
            **kwargs: Additional order parameters
            
        Returns:
            Created order
        """
        try:
            # Generate unique order ID
            order_id = self._generate_order_id()
            
            # Create order object
            order = Order(
                order_id=order_id,
                symbol=symbol.upper(),
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                **kwargs
            )
            
            # Validate order if enabled
            if self.enable_order_validation:
                validation_result = await self._validate_order(order)
                if not validation_result.is_valid:
                    order.status = OrderStatus.REJECTED
                    order.rejection_reason = "; ".join(validation_result.errors)
                    logger.warning(f"Order rejected: {order.rejection_reason}")
                    return order
            
            # Store order
            with self._lock:
                self._orders[order_id] = order
                self._orders_by_symbol[order.symbol].append(order_id)
                if order.strategy_id:
                    self._orders_by_strategy[order.strategy_id].append(order_id)
                self._orders_by_status[order.status].append(order_id)
                
                # Update metrics
                self._order_metrics['orders_created'] += 1
            
            # Set order to NEW status
            await self._update_order_status(order, OrderStatus.NEW)
            
            # Trigger order event
            await self._trigger_order_event('order_created', order)
            
            logger.info(f"Created order {order_id}: {side.value} {quantity} {symbol} @ {price}")
            
            return order
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise
    
    async def _validate_order(self, order: Order) -> OrderValidationResult:
        """Validate order before submission"""
        
        errors = []
        warnings = []
        
        # Basic validation
        if order.quantity <= 0:
            errors.append("Order quantity must be positive")
        
        if order.quantity > self.max_quantity_per_order:
            errors.append(f"Order quantity exceeds maximum: {self.max_quantity_per_order}")
        
        if order.symbol in self.blocked_symbols:
            errors.append(f"Symbol {order.symbol} is blocked")
        
        # Price validation for limit orders
        if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if order.price is None or order.price <= 0:
                errors.append("Limit orders require a positive price")
        
        # Stop price validation
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT, OrderType.TRAILING_STOP]:
            if order.stop_price is None or order.stop_price <= 0:
                errors.append("Stop orders require a positive stop price")
        
        # Order value check
        if order.price:
            order_value = order.quantity * order.price
            if order_value > self.max_order_value:
                errors.append(f"Order value exceeds maximum: {self.max_order_value}")
        
        # Time in force validation
        if order.time_in_force == TimeInForce.GTD and order.expiry_time is None:
            errors.append("GTD orders require an expiry time")
        
        # Algorithm parameter validation
        if order.order_type in [OrderType.TWAP, OrderType.VWAP, OrderType.IMPLEMENTATION_SHORTFALL]:
            if not order.algo_params:
                warnings.append(f"Algorithm order {order.order_type.value} has no parameters")
        
        return OrderValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def submit_order(self, order_id: str) -> bool:
        """Submit order for execution"""
        
        order = self.get_order(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False
        
        if order.status != OrderStatus.NEW:
            logger.warning(f"Cannot submit order in status: {order.status}")
            return False
        
        try:
            # Mark order as submitted
            order.submitted_time = datetime.now()
            await self._update_order_status(order, OrderStatus.NEW)
            
            # Trigger submission event
            await self._trigger_order_event('order_submitted', order)
            
            logger.info(f"Submitted order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting order {order_id}: {e}")
            return False
    
    async def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """Cancel an active order"""
        
        order = self.get_order(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False
        
        if not order.is_active:
            logger.warning(f"Cannot cancel order in status: {order.status}")
            return False
        
        try:
            # Update status to pending cancel
            await self._update_order_status(order, OrderStatus.PENDING_CANCEL)
            
            # Simulate cancel processing (in real implementation, would send to broker)
            await asyncio.sleep(0.1)
            
            # Mark as canceled
            await self._update_order_status(order, OrderStatus.CANCELED)
            
            if reason:
                order.notes += f" Canceled: {reason}"
            
            # Update metrics
            with self._lock:
                self._order_metrics['orders_canceled'] += 1
            
            # Trigger cancel event
            await self._trigger_order_event('order_canceled', order)
            
            logger.info(f"Canceled order {order_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return False
    
    async def replace_order(
        self,
        order_id: str,
        new_quantity: Optional[float] = None,
        new_price: Optional[float] = None
    ) -> Optional[str]:
        """Replace an existing order with modified parameters"""
        
        original_order = self.get_order(order_id)
        if not original_order:
            logger.error(f"Order not found: {order_id}")
            return None
        
        if not original_order.is_active:
            logger.warning(f"Cannot replace order in status: {original_order.status}")
            return None
        
        try:
            # Mark original order as pending replace
            await self._update_order_status(original_order, OrderStatus.PENDING_REPLACE)
            
            # Create new order with modified parameters
            new_order = Order(
                order_id=self._generate_order_id(),
                symbol=original_order.symbol,
                side=original_order.side,
                order_type=original_order.order_type,
                quantity=new_quantity or original_order.quantity,
                price=new_price or original_order.price,
                stop_price=original_order.stop_price,
                time_in_force=original_order.time_in_force,
                priority=original_order.priority,
                parent_order_id=original_order.order_id,
                strategy_id=original_order.strategy_id,
                account_id=original_order.account_id,
                trader_id=original_order.trader_id,
                algo_params=original_order.algo_params.copy(),
                tags=original_order.tags.copy(),
                metadata=original_order.metadata.copy()
            )
            
            # Validate new order
            if self.enable_order_validation:
                validation_result = await self._validate_order(new_order)
                if not validation_result.is_valid:
                    new_order.status = OrderStatus.REJECTED
                    new_order.rejection_reason = "; ".join(validation_result.errors)
                    logger.warning(f"Replacement order rejected: {new_order.rejection_reason}")
                    return None
            
            # Store new order
            with self._lock:
                self._orders[new_order.order_id] = new_order
                self._orders_by_symbol[new_order.symbol].append(new_order.order_id)
                if new_order.strategy_id:
                    self._orders_by_strategy[new_order.strategy_id].append(new_order.order_id)
                self._orders_by_status[new_order.status].append(new_order.order_id)
            
            # Mark original as replaced
            await self._update_order_status(original_order, OrderStatus.REPLACED)
            
            # Mark new order as active
            await self._update_order_status(new_order, OrderStatus.NEW)
            
            # Trigger events
            await self._trigger_order_event('order_replaced', original_order)
            await self._trigger_order_event('order_created', new_order)
            
            logger.info(f"Replaced order {order_id} with {new_order.order_id}")
            return new_order.order_id
            
        except Exception as e:
            logger.error(f"Error replacing order {order_id}: {e}")
            return None
    
    async def add_execution(
        self,
        order_id: str,
        quantity: float,
        price: float,
        venue: str = "",
        commission: float = 0.0,
        fees: float = 0.0,
        **kwargs
    ) -> Optional[str]:
        """Add execution to an order"""
        
        order = self.get_order(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return None
        
        try:
            # Create execution record
            execution = OrderExecution(
                execution_id=str(uuid.uuid4()),
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=quantity,
                price=price,
                timestamp=datetime.now(),
                venue=venue,
                commission=commission,
                fees=fees,
                **kwargs
            )
            
            # Update order execution tracking
            order.executions.append(execution)
            order.filled_quantity += quantity
            order.remaining_quantity = order.quantity - order.filled_quantity
            
            # Calculate average fill price
            total_value = sum(exec.quantity * exec.price for exec in order.executions)
            order.average_fill_price = total_value / order.filled_quantity
            
            # Update order status
            if order.remaining_quantity <= 0:
                await self._update_order_status(order, OrderStatus.FILLED)
                
                # Update metrics
                with self._lock:
                    self._order_metrics['orders_filled'] += 1
                    self._order_metrics['total_execution_value'] += quantity * price
                    
                    # Calculate average fill time
                    if order.submitted_time:
                        fill_time = (datetime.now() - order.submitted_time).total_seconds()
                        current_avg = self._order_metrics['average_fill_time']
                        filled_count = self._order_metrics['orders_filled']
                        self._order_metrics['average_fill_time'] = (
                            (current_avg * (filled_count - 1) + fill_time) / filled_count
                        )
            else:
                await self._update_order_status(order, OrderStatus.PARTIALLY_FILLED)
            
            # Store execution in history
            with self._lock:
                self._execution_history.append(execution)
            
            # Trigger execution event
            await self._trigger_execution_event('execution_received', execution, order)
            
            logger.info(f"Added execution: {quantity} @ {price} for order {order_id}")
            return execution.execution_id
            
        except Exception as e:
            logger.error(f"Error adding execution for order {order_id}: {e}")
            return None
    
    async def _update_order_status(self, order: Order, new_status: OrderStatus) -> None:
        """Update order status and maintain indices"""
        
        old_status = order.status
        
        with self._lock:
            # Remove from old status list
            if order.order_id in self._orders_by_status[old_status]:
                self._orders_by_status[old_status].remove(order.order_id)
            
            # Add to new status list
            self._orders_by_status[new_status].append(order.order_id)
        
        # Update order
        order.status = new_status
        order.last_update_time = datetime.now()
        
        # Add to history if terminal status
        if new_status in [OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.EXPIRED]:
            with self._lock:
                self._order_history.append(order)
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        return f"ORD_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8].upper()}"
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        with self._lock:
            return self._orders.get(order_id)
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get all orders for a symbol"""
        with self._lock:
            order_ids = self._orders_by_symbol.get(symbol.upper(), [])
            return [self._orders[oid] for oid in order_ids if oid in self._orders]
    
    def get_orders_by_strategy(self, strategy_id: str) -> List[Order]:
        """Get all orders for a strategy"""
        with self._lock:
            order_ids = self._orders_by_strategy.get(strategy_id, [])
            return [self._orders[oid] for oid in order_ids if oid in self._orders]
    
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """Get all orders with specific status"""
        with self._lock:
            order_ids = self._orders_by_status.get(status, [])
            return [self._orders[oid] for oid in order_ids if oid in self._orders]
    
    def get_active_orders(self) -> List[Order]:
        """Get all active orders"""
        active_orders = []
        active_orders.extend(self.get_orders_by_status(OrderStatus.NEW))
        active_orders.extend(self.get_orders_by_status(OrderStatus.PARTIALLY_FILLED))
        return active_orders
    
    def get_order_metrics(self) -> Dict[str, Any]:
        """Get order management metrics"""
        with self._lock:
            metrics = self._order_metrics.copy()
        
        # Add current counts
        metrics.update({
            'total_orders': len(self._orders),
            'active_orders': len(self.get_active_orders()),
            'orders_by_status': {
                status.value: len(self.get_orders_by_status(status))
                for status in OrderStatus
            }
        })
        
        return metrics
    
    def add_order_event_handler(self, handler: Callable[[str, Order], None]) -> None:
        """Add order event handler"""
        self._order_event_handlers.append(handler)
    
    def add_execution_event_handler(self, handler: Callable[[str, OrderExecution, Order], None]) -> None:
        """Add execution event handler"""
        self._execution_event_handlers.append(handler)
    
    async def _trigger_order_event(self, event_type: str, order: Order) -> None:
        """Trigger order event to all handlers"""
        for handler in self._order_event_handlers:
            try:
                await handler(event_type, order)
            except Exception as e:
                logger.error(f"Error in order event handler: {e}")
    
    async def _trigger_execution_event(self, event_type: str, execution: OrderExecution, order: Order) -> None:
        """Trigger execution event to all handlers"""
        for handler in self._execution_event_handlers:
            try:
                await handler(event_type, execution, order)
            except Exception as e:
                logger.error(f"Error in execution event handler: {e}")
    
    async def cleanup_expired_orders(self) -> int:
        """Clean up expired orders"""
        expired_count = 0
        current_time = datetime.now()
        
        for order in list(self._orders.values()):
            # Check expiry time
            if order.expiry_time and current_time >= order.expiry_time:
                if order.is_active:
                    await self._update_order_status(order, OrderStatus.EXPIRED)
                    expired_count += 1
            
            # Check maximum age
            elif self.auto_expire_orders:
                age_hours = (current_time - order.created_time).total_seconds() / 3600
                if age_hours >= self.max_order_age_hours and order.is_active:
                    await self._update_order_status(order, OrderStatus.EXPIRED)
                    expired_count += 1
        
        if expired_count > 0:
            logger.info(f"Expired {expired_count} orders")
        
        return expired_count
    
    async def cleanup(self) -> None:
        """Cleanup order manager resources"""
        # Cancel all active orders
        active_orders = self.get_active_orders()
        for order in active_orders:
            await self.cancel_order(order.order_id, "System shutdown")
        
        logger.info("OrderManager cleanup completed")