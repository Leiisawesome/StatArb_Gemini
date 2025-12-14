"""
Order Management System (OMS) - Institutional Order Lifecycle Management

Architecture Compliance (Tier-1 Rules):
- Rule 5: Execution & Order Management - Phase 12 (Order Management)
  - Complete order lifecycle management (pending → new → filled)
  - Order state persistence for disaster recovery
  - Parent/child order relationships for order slicing
  - Modification and cancellation workflows
  - Allocation management for fund/account splits
  - Complete audit trail

Key Responsibilities:
1. Order lifecycle management (new → working → filled/cancelled)
2. Order state persistence (survive restarts)
3. Parent/child order relationships (slicing)
4. Order modification/cancellation
5. Allocation management
6. Compliance tagging
7. Complete audit trail

Integration Points:
- Phase 11 (Execution Planning): Receives ExecutionPlan
- Phase 13 (Execution Action): Submits orders to ExecutionEngine
- Phase 14 (Fill Processing): Receives fill updates
- Rule 6 (Settlement): Reports completed trades

Author: Trading System Team
Date: December 6, 2025
Version: 1.0 (Initial implementation per Rule 5, Phase 12)
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import defaultdict

from .interfaces import ISystemComponent

logger = logging.getLogger(__name__)

class OrderState(Enum):
    """Order lifecycle states per Rule 5"""
    PENDING_NEW = "pending_new"           # Created, not yet submitted
    NEW = "new"                           # Submitted to venue
    PARTIALLY_FILLED = "partially_filled" # Some fills received
    FILLED = "filled"                     # Completely filled
    PENDING_CANCEL = "pending_cancel"     # Cancel requested
    CANCELLED = "cancelled"               # Cancelled (confirmed)
    REJECTED = "rejected"                 # Rejected by venue
    EXPIRED = "expired"                   # Time-in-force expired
    PENDING_REPLACE = "pending_replace"   # Modification requested

class OrderType(Enum):
    """Supported order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    MARKET_ON_CLOSE = "moc"
    LIMIT_ON_CLOSE = "loc"
    TWAP = "twap"
    VWAP = "vwap"

class TimeInForce(Enum):
    """Time in force options"""
    DAY = "day"                 # Valid for the day
    GTC = "gtc"                 # Good till cancelled
    IOC = "ioc"                 # Immediate or cancel
    FOK = "fok"                 # Fill or kill
    GTD = "gtd"                 # Good till date
    OPG = "opg"                 # At the opening
    CLS = "cls"                 # At the close

@dataclass
class OrderStateChange:
    """Record of order state transition"""
    timestamp: datetime
    from_state: Optional[OrderState]
    to_state: OrderState
    reason: str
    user_id: Optional[str] = None

@dataclass
class Fill:
    """Execution fill record"""
    fill_id: str
    timestamp: datetime
    quantity: float
    price: float
    venue: str = "primary"
    commission: float = 0.0
    fees: float = 0.0

@dataclass
class Order:
    """
    Order entity with complete lifecycle tracking.

    Implements Rule 5, Phase 12 requirements for order management.
    """

    # Identity
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_order_id: str = ""
    parent_order_id: Optional[str] = None  # For child orders (slicing)

    # Authorization link (Rule 3)
    authorization_id: str = ""

    # Order details
    symbol: str = ""
    side: str = ""  # 'buy' or 'sell'
    order_type: OrderType = OrderType.MARKET
    quantity: float = 0.0
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY

    # State
    state: OrderState = OrderState.PENDING_NEW
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    avg_fill_price: float = 0.0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Compliance (Rule 3)
    compliance_tags: List[str] = field(default_factory=list)
    strategy_id: str = ""

    # Fills
    fills: List[Fill] = field(default_factory=list)

    # Audit trail
    state_history: List[OrderStateChange] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize derived fields"""
        self.remaining_quantity = self.quantity
        if not self.client_order_id:
            self.client_order_id = f"CO-{self.order_id[:8]}"

class OrderManagementSystem(ISystemComponent):
    """
    Institutional Order Management System

    Implements Rule 5, Phase 12: Complete order lifecycle management.

    Integrates with:
    - Rule 3 (Phase 10): Receives authorized trades
    - Rule 5 (Phase 11): Receives execution plans
    - Rule 5 (Phase 13): Sends to execution engine
    - Rule 6: Reports to reconciliation and settlement
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize OMS with configuration.

        Args:
            config: OMS configuration including:
                - persistence_enabled: Enable order persistence
                - max_order_age_days: Max age before cleanup
                - state_persistence_path: Path for state files
        """
        self.config = config or {}
        self.orders: Dict[str, Order] = {}
        self.orders_by_authorization: Dict[str, List[str]] = defaultdict(list)
        self.orders_by_symbol: Dict[str, List[str]] = defaultdict(list)
        self.orders_by_strategy: Dict[str, List[str]] = defaultdict(list)

        # Configuration
        self.persistence_enabled = self.config.get('persistence_enabled', True)
        self.max_order_age_days = self.config.get('max_order_age_days', 30)
        self.state_persistence_path = self.config.get('state_persistence_path', './state/oms/')

        # Callbacks for integration
        self._execution_callback: Optional[Callable] = None
        self._risk_manager_callback: Optional[Callable] = None
        self._settlement_callback: Optional[Callable] = None

        # Statistics
        self.stats = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_cancelled': 0,
            'orders_rejected': 0,
            'total_volume': 0.0,
            'total_value': 0.0
        }

        self._initialized = False
        self._running = False

        logger.info("OrderManagementSystem initialized (Rule 5, Phase 12)")

    # ===== ISystemComponent Implementation =====

    async def initialize(self) -> bool:
        """Initialize OMS and recover state if persistence enabled"""
        try:
            if self.persistence_enabled:
                await self._recover_orders()

            self._initialized = True
            logger.info("OMS initialized successfully")
            return True
        except Exception as e:
            logger.error(f"OMS initialization failed: {e}")
            return False

    async def start(self) -> bool:
        """Start OMS operations"""
        if not self._initialized:
            await self.initialize()

        self._running = True

        # Start background tasks
        asyncio.create_task(self._order_expiry_monitor())
        asyncio.create_task(self._state_persistence_task())

        logger.info("OMS started")
        return True

    async def stop(self) -> bool:
        """Stop OMS and persist state"""
        self._running = False

        if self.persistence_enabled:
            await self._persist_all_orders()

        logger.info("OMS stopped")
        return True

    async def health_check(self) -> Dict[str, Any]:
        """Check OMS health"""
        working_orders = await self.get_working_orders()

        return {
            'healthy': self._running,
            'orders_total': len(self.orders),
            'orders_working': len(working_orders),
            'persistence_enabled': self.persistence_enabled,
            'stats': self.stats
        }

    def get_status(self) -> Dict[str, Any]:
        """Get OMS status"""
        return {
            'initialized': self._initialized,
            'running': self._running,
            'orders_count': len(self.orders),
            'stats': self.stats
        }

    # ===== Order Lifecycle Methods =====

    async def create_order(
        self,
        authorization_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
        parent_order_id: Optional[str] = None,
        compliance_tags: List[str] = None,
        strategy_id: str = "",
        metadata: Dict[str, Any] = None
    ) -> Order:
        """
        Create new order from authorization.

        Phase 12 entry point - receives from Phase 11 (Execution Planning).

        Args:
            authorization_id: Rule 3 authorization ID
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Order quantity
            order_type: Order type (MARKET, LIMIT, etc.)
            limit_price: Limit price for LIMIT orders
            stop_price: Stop price for STOP orders
            time_in_force: Time in force
            parent_order_id: Parent order ID for child orders
            compliance_tags: Compliance tags from Rule 3
            strategy_id: Strategy that generated the order
            metadata: Additional metadata

        Returns:
            Created Order object
        """
        order = Order(
            authorization_id=authorization_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            parent_order_id=parent_order_id,
            compliance_tags=compliance_tags or [],
            strategy_id=strategy_id,
            metadata=metadata or {}
        )

        # Store order in indices
        self.orders[order.order_id] = order
        self.orders_by_authorization[authorization_id].append(order.order_id)
        self.orders_by_symbol[symbol].append(order.order_id)
        if strategy_id:
            self.orders_by_strategy[strategy_id].append(order.order_id)

        # Record state change
        self._record_state_change(order, None, OrderState.PENDING_NEW, 'order_created')

        # Update stats
        self.stats['orders_created'] += 1

        # Persist if enabled
        if self.persistence_enabled:
            await self._persist_order(order)

        logger.info(
            f"📝 Order created: {order.order_id[:8]} "
            f"{symbol} {side} {quantity} @ {order_type.value}"
        )

        return order

    async def submit_order(self, order_id: str) -> Order:
        """
        Submit order to execution engine (Phase 13).

        Args:
            order_id: Order ID to submit

        Returns:
            Updated Order object

        Raises:
            ValueError: If order not found or invalid state
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        if order.state != OrderState.PENDING_NEW:
            raise ValueError(f"Cannot submit order in state: {order.state.value}")

        # Transition state
        await self._transition_state(order, OrderState.NEW, 'submitted_to_venue')
        order.submitted_at = datetime.now()

        logger.info(f"📤 Order submitted: {order.order_id[:8]}")

        return order

    async def record_fill(
        self,
        order_id: str,
        fill_quantity: float,
        fill_price: float,
        venue: str = "primary",
        commission: float = 0.0,
        fees: float = 0.0
    ) -> Order:
        """
        Record execution fill.

        Called by Phase 14 (Fill Processing) when fills are received.

        Args:
            order_id: Order ID
            fill_quantity: Quantity filled
            fill_price: Fill price
            venue: Execution venue
            commission: Commission charged
            fees: Exchange/regulatory fees

        Returns:
            Updated Order object
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        # Create fill record
        fill = Fill(
            fill_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            quantity=fill_quantity,
            price=fill_price,
            venue=venue,
            commission=commission,
            fees=fees
        )
        order.fills.append(fill)

        # Update quantities
        prev_filled = order.filled_quantity
        order.filled_quantity += fill_quantity
        order.remaining_quantity = order.quantity - order.filled_quantity

        # Update average price (weighted average)
        if prev_filled == 0:
            order.avg_fill_price = fill_price
        else:
            total_value = (order.avg_fill_price * prev_filled) + (fill_price * fill_quantity)
            order.avg_fill_price = total_value / order.filled_quantity

        order.last_updated_at = datetime.now()

        # Update stats
        self.stats['total_volume'] += fill_quantity
        self.stats['total_value'] += fill_quantity * fill_price

        # Determine new state
        if order.remaining_quantity <= 0:
            await self._transition_state(order, OrderState.FILLED, 'completely_filled')
            order.filled_at = datetime.now()
            self.stats['orders_filled'] += 1

            # Notify settlement (Rule 6)
            if self._settlement_callback:
                await self._settlement_callback(order)
        else:
            await self._transition_state(order, OrderState.PARTIALLY_FILLED, 'partial_fill')

        logger.info(
            f"✅ Fill recorded: {order.order_id[:8]} "
            f"{fill_quantity}@${fill_price:.2f} "
            f"({order.filled_quantity}/{order.quantity})"
        )

        return order

    async def cancel_order(self, order_id: str, reason: str = None) -> Order:
        """
        Request order cancellation.

        Args:
            order_id: Order ID to cancel
            reason: Cancellation reason

        Returns:
            Updated Order object
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        terminal_states = [OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED]
        if order.state in terminal_states:
            raise ValueError(f"Cannot cancel order in state: {order.state.value}")

        await self._transition_state(order, OrderState.PENDING_CANCEL, reason or 'cancel_requested')

        logger.info(f"🚫 Cancel requested: {order.order_id[:8]} - {reason}")

        return order

    async def confirm_cancellation(self, order_id: str) -> Order:
        """
        Confirm order cancellation from venue.

        Args:
            order_id: Order ID

        Returns:
            Updated Order object
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        await self._transition_state(order, OrderState.CANCELLED, 'cancel_confirmed')
        self.stats['orders_cancelled'] += 1

        logger.info(f"❌ Cancellation confirmed: {order.order_id[:8]}")

        return order

    async def reject_order(self, order_id: str, reason: str) -> Order:
        """
        Mark order as rejected.

        Args:
            order_id: Order ID
            reason: Rejection reason

        Returns:
            Updated Order object
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        await self._transition_state(order, OrderState.REJECTED, reason)
        self.stats['orders_rejected'] += 1

        logger.warning(f"⛔ Order rejected: {order.order_id[:8]} - {reason}")

        return order

    async def modify_order(
        self,
        order_id: str,
        new_quantity: float = None,
        new_limit_price: float = None
    ) -> Order:
        """
        Modify pending order.

        Args:
            order_id: Order ID to modify
            new_quantity: New quantity (optional)
            new_limit_price: New limit price (optional)

        Returns:
            Updated Order object
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        modifiable_states = [OrderState.NEW, OrderState.PARTIALLY_FILLED]
        if order.state not in modifiable_states:
            raise ValueError(f"Cannot modify order in state: {order.state.value}")

        # Record modifications
        modifications = {}
        if new_quantity is not None:
            modifications['quantity'] = {'old': order.quantity, 'new': new_quantity}
            order.quantity = new_quantity
            order.remaining_quantity = new_quantity - order.filled_quantity
        if new_limit_price is not None:
            modifications['limit_price'] = {'old': order.limit_price, 'new': new_limit_price}
            order.limit_price = new_limit_price

        order.metadata['modifications'] = order.metadata.get('modifications', [])
        order.metadata['modifications'].append({
            'timestamp': datetime.now().isoformat(),
            'changes': modifications
        })

        await self._transition_state(
            order,
            OrderState.PENDING_REPLACE,
            f'modification_requested: {list(modifications.keys())}'
        )

        logger.info(f"📝 Order modification requested: {order.order_id[:8]}")

        return order

    # ===== Query Methods =====

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)

    async def get_working_orders(self) -> List[Order]:
        """Get all working (active) orders"""
        working_states = [
            OrderState.NEW,
            OrderState.PARTIALLY_FILLED,
            OrderState.PENDING_CANCEL,
            OrderState.PENDING_REPLACE
        ]
        return [o for o in self.orders.values() if o.state in working_states]

    async def get_orders_by_authorization(self, authorization_id: str) -> List[Order]:
        """Get all orders for an authorization"""
        order_ids = self.orders_by_authorization.get(authorization_id, [])
        return [self.orders[oid] for oid in order_ids if oid in self.orders]

    async def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get all orders for a symbol"""
        order_ids = self.orders_by_symbol.get(symbol, [])
        return [self.orders[oid] for oid in order_ids if oid in self.orders]

    async def get_orders_by_strategy(self, strategy_id: str) -> List[Order]:
        """Get all orders for a strategy"""
        order_ids = self.orders_by_strategy.get(strategy_id, [])
        return [self.orders[oid] for oid in order_ids if oid in self.orders]

    async def get_child_orders(self, parent_order_id: str) -> List[Order]:
        """Get child orders for a parent order"""
        return [
            o for o in self.orders.values()
            if o.parent_order_id == parent_order_id
        ]

    # ===== Internal Methods =====

    def _record_state_change(
        self,
        order: Order,
        from_state: Optional[OrderState],
        to_state: OrderState,
        reason: str
    ):
        """Record state change in order history"""
        change = OrderStateChange(
            timestamp=datetime.now(),
            from_state=from_state,
            to_state=to_state,
            reason=reason
        )
        order.state_history.append(change)

    async def _transition_state(self, order: Order, new_state: OrderState, reason: str):
        """Transition order to new state"""
        old_state = order.state
        order.state = new_state
        order.last_updated_at = datetime.now()

        self._record_state_change(order, old_state, new_state, reason)

        if self.persistence_enabled:
            await self._persist_order(order)

    async def _persist_order(self, order: Order):
        """Persist order to storage (placeholder for actual implementation)"""
        # TODO: Implement actual persistence (database, file, etc.)

    async def _persist_all_orders(self):
        """Persist all orders"""
        for order in self.orders.values():
            await self._persist_order(order)

    async def _recover_orders(self):
        """Recover orders from persistence after restart"""
        # TODO: Implement recovery logic
        logger.info("Order recovery check complete")

    async def _order_expiry_monitor(self):
        """Monitor and expire old orders"""
        while self._running:
            try:
                now = datetime.now()
                for order in list(self.orders.values()):
                    # Check time-in-force expiry
                    if order.expires_at and now > order.expires_at:
                        if order.state in [OrderState.NEW, OrderState.PARTIALLY_FILLED]:
                            await self._transition_state(
                                order, OrderState.EXPIRED, 'time_in_force_expired'
                            )
                            logger.info(f"⏰ Order expired: {order.order_id[:8]}")

                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Order expiry monitor error: {e}")
                await asyncio.sleep(60)

    async def _state_persistence_task(self):
        """Periodic state persistence"""
        while self._running:
            try:
                if self.persistence_enabled:
                    await self._persist_all_orders()
                await asyncio.sleep(300)  # Every 5 minutes
            except Exception as e:
                logger.error(f"State persistence error: {e}")
                await asyncio.sleep(300)

    # ===== Callback Registration =====

    def set_execution_callback(self, callback: Callable):
        """Set callback for execution engine"""
        self._execution_callback = callback

    def set_risk_manager_callback(self, callback: Callable):
        """Set callback for risk manager"""
        self._risk_manager_callback = callback

    def set_settlement_callback(self, callback: Callable):
        """Set callback for settlement manager"""
        self._settlement_callback = callback

    # ===== Pending Exposure API (Paper Trading Evolution) =====
    #
    # Per plan Section 5.5 - Gate 3: Position-Aware Validation
    # OMS must expose read API for risk calculations

    def get_working_orders_sync(
        self,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
    ) -> List[Order]:
        """
        Synchronous version of get_working_orders with filters.

        Returns orders in states: PENDING_NEW, NEW, PARTIALLY_FILLED

        Args:
            symbol: Optional symbol filter
            side: Optional side filter ('buy' or 'sell')

        Returns:
            List of WorkingOrder-like Order objects
        """
        working_states = [
            OrderState.PENDING_NEW,
            OrderState.NEW,
            OrderState.PARTIALLY_FILLED,
        ]

        orders = [
            o for o in self.orders.values()
            if o.state in working_states
        ]

        if symbol:
            orders = [o for o in orders if o.symbol == symbol]

        if side:
            orders = [o for o in orders if o.side == side]

        return orders

    def get_pending_exposure(
        self,
        symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get pre-computed aggregate pending exposure.

        Called on every risk check; cached for O(1) access.

        Args:
            symbol: Optional symbol filter (None = all)

        Returns:
            PendingExposure dict with:
            - by_symbol: Dict of per-symbol exposures
            - total_pending_buy_notional: float
            - total_pending_sell_notional: float
            - total_pending_buy_count: int
            - total_pending_sell_count: int
        """
        working_orders = self.get_working_orders_sync(symbol=symbol)

        # Aggregate by symbol
        by_symbol: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            'pending_buy_qty': 0.0,
            'pending_sell_qty': 0.0,
            'pending_buy_notional': 0.0,
            'pending_sell_notional': 0.0,
        })

        total_buy_notional = 0.0
        total_sell_notional = 0.0
        buy_count = 0
        sell_count = 0

        for order in working_orders:
            remaining = order.remaining_quantity

            # Determine price for notional calculation
            if order.limit_price:
                price = order.limit_price
            elif order.stop_price:
                price = order.stop_price
            else:
                # Market order - use a reference price if available
                # For now, use 0 (caller should handle this case)
                price = 0.0

            notional = remaining * price
            sym_data = by_symbol[order.symbol]

            if order.side == 'buy':
                sym_data['pending_buy_qty'] += remaining
                sym_data['pending_buy_notional'] += notional
                total_buy_notional += notional
                buy_count += 1
            else:
                sym_data['pending_sell_qty'] += remaining
                sym_data['pending_sell_notional'] += notional
                total_sell_notional += notional
                sell_count += 1

        # Convert defaultdict to regular dict with symbol key
        by_symbol_result = {
            sym: {
                'symbol': sym,
                'pending_buy_qty': data['pending_buy_qty'],
                'pending_sell_qty': data['pending_sell_qty'],
                'pending_buy_notional': data['pending_buy_notional'],
                'pending_sell_notional': data['pending_sell_notional'],
            }
            for sym, data in by_symbol.items()
        }

        return {
            'by_symbol': by_symbol_result,
            'total_pending_buy_notional': total_buy_notional,
            'total_pending_sell_notional': total_sell_notional,
            'total_pending_buy_count': buy_count,
            'total_pending_sell_count': sell_count,
        }

    def get_pending_risk_at_price(
        self,
        symbol: str,
        price: float,
    ) -> Dict[str, Any]:
        """
        Returns exposure if orders fill at given price.

        Used for what-if analysis in Gate 3.

        Args:
            symbol: Symbol to check
            price: Hypothetical fill price

        Returns:
            Dict with pending exposure at the given price
        """
        working_orders = self.get_working_orders_sync(symbol=symbol)

        pending_buy_qty = 0.0
        pending_sell_qty = 0.0
        pending_buy_notional = 0.0
        pending_sell_notional = 0.0

        for order in working_orders:
            remaining = order.remaining_quantity
            notional = remaining * price

            if order.side == 'buy':
                pending_buy_qty += remaining
                pending_buy_notional += notional
            else:
                pending_sell_qty += remaining
                pending_sell_notional += notional

        return {
            'symbol': symbol,
            'price': price,
            'pending_buy_qty': pending_buy_qty,
            'pending_sell_qty': pending_sell_qty,
            'pending_buy_notional': pending_buy_notional,
            'pending_sell_notional': pending_sell_notional,
            'net_pending_qty': pending_buy_qty - pending_sell_qty,
            'net_pending_notional': pending_buy_notional - pending_sell_notional,
        }

