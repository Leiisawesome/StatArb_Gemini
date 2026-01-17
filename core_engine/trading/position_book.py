"""
PositionBook - Single Source of Truth for Position State
=========================================================

The PositionBook is the authoritative source for all position data in the trading system.
It implements the CQRS pattern where:
- READ: Any component can query position state
- WRITE: Only execution fills modify position state (via on_fill)

Design Principles:
- Thread-safe for concurrent access
- Event-driven updates with subscriber notifications
- Immutable position snapshots for reads
- Complete audit trail via fill history
- Supports both backtest and live trading

Architecture:
                     ┌─────────────────────────────┐
                     │      POSITION BOOK          │
                     │  (Single Source of Truth)   │
                     └─────────────┬───────────────┘
                                   │
       ┌───────────────────────────┼───────────────────────────┐
       │ READ                      │ READ                      │ WRITE
       ▼                           ▼                           ▼
┌─────────────┐           ┌─────────────┐            ┌─────────────┐
│ RISK ENGINE │           │  ANALYTICS  │            │  EXECUTION  │
│  (query)    │           │  (query)    │            │ (on_fill)   │
└─────────────┘           └─────────────┘            └─────────────┘

Author: StatArb_Gemini
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Union
import threading
import copy
import logging
import uuid

logger = logging.getLogger(__name__)

# =============================================================================
# ENUMS
# =============================================================================

class PositionSide(Enum):
    """Position direction"""
    FLAT = "flat"
    LONG = "long"
    SHORT = "short"

class PositionStatus(Enum):
    """Position lifecycle status"""
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"

class PositionEventType(Enum):
    """Types of position events"""
    OPENED = "opened"
    UPDATED = "updated"
    CLOSED = "closed"
    PRICE_UPDATED = "price_updated"

class FillSide(Enum):
    """Fill/order side"""
    BUY = "buy"
    SELL = "sell"

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Fill:
    """
    Execution fill record.

    Represents a single trade execution from the broker/exchange.
    """
    fill_id: str
    symbol: str
    side: FillSide
    quantity: Decimal
    price: Decimal
    timestamp: datetime

    # Costs
    commission: Decimal = Decimal('0')
    slippage: Decimal = Decimal('0')

    # Attribution
    order_id: str = ""
    strategy_id: str = ""

    # Metadata
    venue: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def notional_value(self) -> Decimal:
        """Gross notional value of the fill"""
        return self.quantity * self.price

    @property
    def total_cost(self) -> Decimal:
        """Total cost including commission and slippage"""
        return self.commission + self.slippage

    @classmethod
    def create(
        cls,
        symbol: str,
        side: Union[str, FillSide],
        quantity: Union[float, Decimal],
        price: Union[float, Decimal],
        commission: Union[float, Decimal] = 0,
        slippage: Union[float, Decimal] = 0,
        strategy_id: str = "",
        order_id: str = "",
        timestamp: Optional[datetime] = None,
        **kwargs
    ) -> 'Fill':
        """Factory method to create a Fill with proper type conversion"""
        if isinstance(side, str):
            side = FillSide(side.lower())

        return cls(
            fill_id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            quantity=Decimal(str(quantity)),
            price=Decimal(str(price)),
            timestamp=timestamp or datetime.now(timezone.utc),
            commission=Decimal(str(commission)),
            slippage=Decimal(str(slippage)),
            order_id=order_id,
            strategy_id=strategy_id,
            **kwargs
        )

@dataclass
class BookPosition:
    """
    Complete position record in PositionBook.

    This is the authoritative representation of a position, containing
    all data needed for risk, analytics, and P&L calculations.
    """
    symbol: str
    quantity: Decimal
    side: PositionSide

    # Cost basis tracking
    avg_entry_price: Decimal
    total_cost_basis: Decimal

    # P&L tracking
    realized_pnl: Decimal
    unrealized_pnl: Decimal

    # Market data (MTM)
    current_price: Decimal
    market_value: Decimal

    # Lifecycle
    opened_at: datetime
    last_fill_at: datetime
    status: PositionStatus

    # Attribution
    strategy_id: str

    # Fill history for this position
    fills: List[Fill] = field(default_factory=list)

    @property
    def is_long(self) -> bool:
        return self.side == PositionSide.LONG

    @property
    def is_short(self) -> bool:
        return self.side == PositionSide.SHORT

    @property
    def is_flat(self) -> bool:
        return self.quantity == Decimal('0') or self.side == PositionSide.FLAT

    @property
    def total_pnl(self) -> Decimal:
        """Total P&L (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def pnl_percent(self) -> Decimal:
        """P&L as percentage of cost basis"""
        if self.total_cost_basis == Decimal('0'):
            return Decimal('0')
        return (self.total_pnl / abs(self.total_cost_basis)) * Decimal('100')

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'quantity': float(self.quantity),
            'side': self.side.value,
            'avg_entry_price': float(self.avg_entry_price),
            'total_cost_basis': float(self.total_cost_basis),
            'realized_pnl': float(self.realized_pnl),
            'unrealized_pnl': float(self.unrealized_pnl),
            'current_price': float(self.current_price),
            'market_value': float(self.market_value),
            'opened_at': self.opened_at.isoformat(),
            'last_fill_at': self.last_fill_at.isoformat(),
            'status': self.status.value,
            'strategy_id': self.strategy_id,
            'total_pnl': float(self.total_pnl),
            'pnl_percent': float(self.pnl_percent),
            'fill_count': len(self.fills)
        }

@dataclass
class PositionUpdate:
    """
    Result of a position update from a fill.

    Returned by on_fill() and published to subscribers.
    """
    update_id: str
    symbol: str
    event_type: PositionEventType
    timestamp: datetime

    # Fill that caused this update
    fill: Fill

    # Position state after update
    new_quantity: Decimal
    new_side: PositionSide
    new_avg_price: Decimal

    # P&L from this fill
    realized_pnl: Decimal

    # Cash impact
    cash_change: Decimal

    # Previous state (for audit)
    previous_quantity: Decimal
    previous_avg_price: Decimal

    # Full position snapshot
    position: Optional[BookPosition] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'update_id': self.update_id,
            'symbol': self.symbol,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'fill_id': self.fill.fill_id,
            'fill_side': self.fill.side.value,
            'fill_quantity': float(self.fill.quantity),
            'fill_price': float(self.fill.price),
            'new_quantity': float(self.new_quantity),
            'new_side': self.new_side.value,
            'new_avg_price': float(self.new_avg_price),
            'realized_pnl': float(self.realized_pnl),
            'cash_change': float(self.cash_change),
            'previous_quantity': float(self.previous_quantity),
            'previous_avg_price': float(self.previous_avg_price)
        }

@dataclass
class PortfolioSnapshot:
    """
    Point-in-time snapshot of entire portfolio state.

    Used for analytics, reporting, and checkpointing.
    """
    snapshot_id: str
    timestamp: datetime

    # Portfolio totals
    total_value: Decimal
    cash_balance: Decimal
    positions_value: Decimal

    # P&L
    total_realized_pnl: Decimal
    total_unrealized_pnl: Decimal

    # Positions (deep copy)
    positions: Dict[str, BookPosition]

    # Counts
    long_count: int
    short_count: int
    total_positions: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'snapshot_id': self.snapshot_id,
            'timestamp': self.timestamp.isoformat(),
            'total_value': float(self.total_value),
            'cash_balance': float(self.cash_balance),
            'positions_value': float(self.positions_value),
            'total_realized_pnl': float(self.total_realized_pnl),
            'total_unrealized_pnl': float(self.total_unrealized_pnl),
            'long_count': self.long_count,
            'short_count': self.short_count,
            'total_positions': self.total_positions,
            'positions': {k: v.to_dict() for k, v in self.positions.items()}
        }

# =============================================================================
# INTERFACE
# =============================================================================

class IPositionBook(ABC):
    """
    Abstract interface for PositionBook.

    Allows for different implementations (backtest vs live)
    while maintaining a consistent API.
    """

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[BookPosition]:
        """Get current position for symbol (returns copy)"""

    @abstractmethod
    def get_all_positions(self) -> Dict[str, BookPosition]:
        """Get all open positions (returns copies)"""

    @abstractmethod
    def get_position_quantity(self, symbol: str) -> Decimal:
        """Get position quantity (0 if no position)"""

    @abstractmethod
    def get_portfolio_value(self) -> Decimal:
        """Total portfolio value = cash + sum(position market values)"""

    @abstractmethod
    def get_net_exposure(self, symbol: Optional[str] = None) -> Decimal:
        """Net exposure (long - short) for symbol or portfolio"""

    @abstractmethod
    def get_cash_balance(self) -> Decimal:
        """Current available cash"""

    @abstractmethod
    def get_realized_pnl(self) -> Decimal:
        """Total realized P&L across all closed positions"""

    @abstractmethod
    def get_unrealized_pnl(self) -> Decimal:
        """Total unrealized P&L across all open positions"""

    @abstractmethod
    def get_snapshot(self) -> PortfolioSnapshot:
        """Get complete portfolio snapshot"""

    # =========================================================================
    # WRITE OPERATIONS
    # =========================================================================

    @abstractmethod
    def on_fill(self, fill: Fill) -> PositionUpdate:
        """
        Process execution fill - THE ONLY WAY to modify positions.

        Updates position, cash, and P&L. Publishes event to subscribers.
        """

    @abstractmethod
    def on_price_update(self, prices: Dict[str, Decimal]) -> None:
        """Update market prices for MTM and unrealized P&L"""

    # =========================================================================
    # EVENT SUBSCRIPTION
    # =========================================================================

    @abstractmethod
    def subscribe(self, handler: Callable[[PositionUpdate], None]) -> None:
        """Subscribe to position update events"""

    @abstractmethod
    def unsubscribe(self, handler: Callable[[PositionUpdate], None]) -> None:
        """Unsubscribe from position update events"""

# =============================================================================
# IMPLEMENTATION
# =============================================================================

class PositionBook(IPositionBook):
    """
    Single Source of Truth for all position state.

    Thread-safe implementation with event publishing.

    Usage:
        book = PositionBook(initial_cash=Decimal('100000'))

        # Subscribe to updates
        book.subscribe(lambda update: print(f"Position updated: {update}"))

        # Process a fill
        fill = Fill.create(symbol='AAPL', side='buy', quantity=100, price=150.00)
        update = book.on_fill(fill)

        # Query positions
        aapl_pos = book.get_position('AAPL')
        portfolio_value = book.get_portfolio_value()
    """

    def __init__(
        self,
        initial_cash: Union[Decimal, float] = Decimal('100000'),
        book_id: str = "",
        default_commission_per_share: Union[Decimal, float] = Decimal('0.005'),
        default_slippage_bps: Union[Decimal, float] = Decimal('0.5')
    ):
        """
        Initialize PositionBook.

        Args:
            initial_cash: Starting cash balance
            book_id: Optional identifier for this book
            default_commission_per_share: Default commission per share for fills without explicit commission
            default_slippage_bps: Default slippage in basis points for fills without explicit slippage
        """
        self._book_id = book_id or str(uuid.uuid4())
        self._initial_capital = Decimal(str(initial_cash))
        self._cash_balance = Decimal(str(initial_cash))

        # Default costs for fills
        self._default_commission_per_share = Decimal(str(default_commission_per_share))
        self._default_slippage_bps = Decimal(str(default_slippage_bps))

        # Position storage
        self._positions: Dict[str, BookPosition] = {}

        # Cumulative P&L tracking (realized P&L persists after position closes)
        self._total_realized_pnl = Decimal('0')
        self._total_unrealized_pnl = Decimal('0')
        self._positions_value = Decimal('0')

        # History
        self._fill_history: List[Fill] = []
        self._update_history: List[PositionUpdate] = []
        self._snapshots: List[PortfolioSnapshot] = []

        # Thread safety
        self._lock = threading.RLock()

        # Event subscribers
        self._subscribers: List[Callable[[PositionUpdate], None]] = []

        logger.info(f"PositionBook initialized: id={self._book_id}, initial_cash=${initial_cash:,.2f}, "
                   f"commission=${self._default_commission_per_share}/share, slippage={self._default_slippage_bps}bps")

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def book_id(self) -> str:
        return self._book_id

    @property
    def initial_capital(self) -> Decimal:
        return self._initial_capital

    # =========================================================================
    # READ OPERATIONS (Thread-safe, return copies)
    # =========================================================================

    def get_position(self, symbol: str) -> Optional[BookPosition]:
        """Get current position for symbol (returns deep copy)"""
        with self._lock:
            pos = self._positions.get(symbol)
            return copy.deepcopy(pos) if pos else None

    def get_all_positions(self) -> Dict[str, BookPosition]:
        """Get all open positions (returns deep copies)"""
        with self._lock:
            return {
                k: copy.deepcopy(v)
                for k, v in self._positions.items()
                if v.quantity != Decimal('0')
            }

    def get_position_quantity(self, symbol: str) -> Decimal:
        """Get position quantity (0 if no position)"""
        with self._lock:
            pos = self._positions.get(symbol)
            return pos.quantity if pos else Decimal('0')

    def get_portfolio_value(self) -> Decimal:
        """
        Total portfolio value = cash + long_positions - short_positions
        
        CRITICAL: Short positions are LIABILITIES (owed shares), so their
        market value must be SUBTRACTED from portfolio value, not added.
        """
        with self._lock:
            return self._cash_balance + self._positions_value

    def get_net_exposure(self, symbol: Optional[str] = None) -> Decimal:
        """
        Net exposure (long - short) for symbol or portfolio.

        Args:
            symbol: If provided, return exposure for that symbol only.
                   If None, return total portfolio net exposure.
        """
        with self._lock:
            if symbol:
                pos = self._positions.get(symbol)
                if not pos:
                    return Decimal('0')
                # Long = positive, Short = negative
                return pos.market_value if pos.is_long else -pos.market_value

            # Total portfolio exposure
            total = Decimal('0')
            for pos in self._positions.values():
                if pos.is_long:
                    total += pos.market_value
                elif pos.is_short:
                    total -= pos.market_value
            return total

    def get_cash_balance(self) -> Decimal:
        """Current available cash"""
        with self._lock:
            return self._cash_balance

    def get_realized_pnl(self) -> Decimal:
        """Total realized P&L across all positions (current and closed)"""
        with self._lock:
            return self._total_realized_pnl

    def get_unrealized_pnl(self) -> Decimal:
        """Total unrealized P&L across all open positions"""
        with self._lock:
            return self._total_unrealized_pnl

    def get_total_pnl(self) -> Decimal:
        """Total P&L (realized + unrealized)"""
        with self._lock:
            return self._total_realized_pnl + self._total_unrealized_pnl

    def get_snapshot(self) -> PortfolioSnapshot:
        """Get complete portfolio snapshot"""
        with self._lock:
            # Optimized: Avoid deepcopy and use running totals
            positions_copy = {}
            long_count = 0
            short_count = 0
            
            for k, v in self._positions.items():
                if v.quantity == Decimal('0'):
                    continue
                    
                # Faster copy: shallow copy for the dataclass, 
                # but explicit shallow copy for the list of fills
                # to ensure the snapshot list doesn't grow if original does.
                pos_copy = copy.copy(v)
                pos_copy.fills = list(v.fills)
                positions_copy[k] = pos_copy
                
                if v.is_long:
                    long_count += 1
                elif v.is_short:
                    short_count += 1

            snapshot = PortfolioSnapshot(
                snapshot_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                total_value=self._cash_balance + self._positions_value,
                cash_balance=self._cash_balance,
                positions_value=self._positions_value,
                total_realized_pnl=self._total_realized_pnl,
                total_unrealized_pnl=self._total_unrealized_pnl,
                positions=positions_copy,
                long_count=long_count,
                short_count=short_count,
                total_positions=len(positions_copy)
            )

            self._snapshots.append(snapshot)
            return snapshot

    def get_fill_history(self) -> List[Fill]:
        """Get complete fill history (returns copies)"""
        with self._lock:
            return [copy.deepcopy(f) for f in self._fill_history]

    def get_update_history(self) -> List[PositionUpdate]:
        """Get position update history (returns copies)"""
        with self._lock:
            return [copy.deepcopy(u) for u in self._update_history]

    # =========================================================================
    # WRITE OPERATIONS
    # =========================================================================

    def on_fill(self, fill: Fill) -> PositionUpdate:
        """
        Process execution fill - THE ONLY WAY to modify positions.

        This method:
        1. Updates position quantity and average cost
        2. Updates cash balance (cost/proceeds + commissions)
        3. Calculates realized P&L (if reducing position)
        4. Records fill in history
        5. Publishes update event to subscribers

        Args:
            fill: The execution fill to process

        Returns:
            PositionUpdate with details of the position change
        """
        with self._lock:
            symbol = fill.symbol
            current = self._positions.get(symbol)

            # Subtract current position from totals before updating
            if current:
                self._total_unrealized_pnl -= current.unrealized_pnl
                if current.is_long:
                    self._positions_value -= current.market_value
                elif current.is_short:
                    self._positions_value += current.market_value

            # Track previous state
            prev_quantity = current.quantity if current else Decimal('0')
            prev_avg_price = current.avg_entry_price if current else Decimal('0')

            if current is None:
                # Opening new position
                position, realized_pnl = self._open_position(fill)
                event_type = PositionEventType.OPENED
                logger.info(f"📈 OPENED {fill.side.value.upper()} {symbol}: "
                           f"{fill.quantity} @ ${fill.price:.2f}")
            else:
                # Update existing position
                position, realized_pnl = self._update_position(current, fill)

                if position.quantity == Decimal('0'):
                    # Position fully closed
                    del self._positions[symbol]
                    event_type = PositionEventType.CLOSED
                    logger.info(f"📉 CLOSED {symbol}: realized P&L ${realized_pnl:,.2f}")
                else:
                    self._positions[symbol] = position
                    event_type = PositionEventType.UPDATED
                    logger.info(f"🔄 UPDATED {symbol}: {position.quantity} @ "
                               f"${position.avg_entry_price:.2f}")

            # Add new position to totals after updating
            if event_type != PositionEventType.CLOSED:
                self._total_unrealized_pnl += position.unrealized_pnl
                if position.is_long:
                    self._positions_value += position.market_value
                elif position.is_short:
                    self._positions_value -= position.market_value

            # Update cumulative realized P&L
            self._total_realized_pnl += realized_pnl

            # Calculate cash impact
            cash_change = self._calculate_cash_change(fill, realized_pnl)
            self._cash_balance += cash_change

            # Record fill
            self._fill_history.append(fill)

            # Create update record
            update = PositionUpdate(
                update_id=str(uuid.uuid4()),
                symbol=symbol,
                event_type=event_type,
                timestamp=fill.timestamp,
                fill=fill,
                new_quantity=position.quantity if event_type != PositionEventType.CLOSED else Decimal('0'),
                new_side=position.side if event_type != PositionEventType.CLOSED else PositionSide.FLAT,
                new_avg_price=position.avg_entry_price if event_type != PositionEventType.CLOSED else Decimal('0'),
                realized_pnl=realized_pnl,
                cash_change=cash_change,
                previous_quantity=prev_quantity,
                previous_avg_price=prev_avg_price,
                position=copy.deepcopy(position) if event_type != PositionEventType.CLOSED else None
            )

            self._update_history.append(update)

        # Publish event (outside lock to avoid deadlock)
        self._publish_event(update)

        return update

    def on_price_update(self, prices: Dict[str, Decimal]) -> None:
        """
        Update market prices for MTM and unrealized P&L.

        Args:
            prices: Dict of symbol -> current price
        """
        with self._lock:
            for symbol, price in prices.items():
                if symbol in self._positions:
                    pos = self._positions[symbol]
                    new_price = Decimal(str(price))
                    
                    # Calculate deltas to update running totals
                    price_delta = new_price - pos.current_price
                    if price_delta == 0:
                        continue
                        
                    # MTM value change: quantity * price_delta
                    # Long: price up -> market_value up, unrealized up
                    # Short: price up -> market_value down, unrealized down
                    value_delta = pos.quantity * price_delta
                    
                    if pos.is_long:
                        self._positions_value += value_delta
                        self._total_unrealized_pnl += value_delta
                    else:
                        # Short: quantity is positive in BookPosition, 
                        # but liability value increases with price
                        # value_delta here is (quantity * price_delta)
                        self._positions_value -= value_delta # Liability value increases, so subtracted from portfolio
                        self._total_unrealized_pnl -= value_delta # Short P&L is negative when price goes up

                    # Update position object
                    pos.current_price = new_price
                    pos.market_value = abs(pos.quantity) * pos.current_price
                    pos.unrealized_pnl = self._calculate_unrealized_pnl(pos)

    def set_cash_balance(self, amount: Union[Decimal, float]) -> None:
        """
        Set cash balance directly (use sparingly, mainly for initialization).

        Args:
            amount: New cash balance
        """
        with self._lock:
            self._cash_balance = Decimal(str(amount))
            logger.info(f"💰 Cash balance set to ${self._cash_balance:,.2f}")

    def reset(self) -> None:
        """Reset the position book to initial state"""
        with self._lock:
            self._positions.clear()
            self._cash_balance = self._initial_capital
            self._total_realized_pnl = Decimal('0')
            self._total_unrealized_pnl = Decimal('0')
            self._positions_value = Decimal('0')
            self._fill_history.clear()
            self._update_history.clear()
            self._snapshots.clear()
            logger.info(f"🔄 PositionBook reset: cash=${self._initial_capital:,.2f}")

    # =========================================================================
    # EVENT SUBSCRIPTION
    # =========================================================================

    def subscribe(self, handler: Callable[[PositionUpdate], None]) -> None:
        """Subscribe to position update events"""
        if handler not in self._subscribers:
            self._subscribers.append(handler)
            logger.debug(f"Subscriber added: {handler}")

    def unsubscribe(self, handler: Callable[[PositionUpdate], None]) -> None:
        """Unsubscribe from position update events"""
        if handler in self._subscribers:
            self._subscribers.remove(handler)
            logger.debug(f"Subscriber removed: {handler}")

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    def _open_position(self, fill: Fill) -> tuple[BookPosition, Decimal]:
        """Create a new position from a fill"""
        now = fill.timestamp

        # Determine side from fill
        side = PositionSide.LONG if fill.side == FillSide.BUY else PositionSide.SHORT

        position = BookPosition(
            symbol=fill.symbol,
            quantity=fill.quantity,
            side=side,
            avg_entry_price=fill.price,
            total_cost_basis=fill.quantity * fill.price,
            realized_pnl=Decimal('0'),
            unrealized_pnl=Decimal('0'),
            current_price=fill.price,
            market_value=fill.quantity * fill.price,
            opened_at=now,
            last_fill_at=now,
            status=PositionStatus.OPEN,
            strategy_id=fill.strategy_id,
            fills=[fill]
        )

        self._positions[fill.symbol] = position
        return position, Decimal('0')  # No realized P&L on open

    def _update_position(self, current: BookPosition, fill: Fill) -> tuple[BookPosition, Decimal]:
        """
        Update existing position with a new fill.

        Handles:
        - Adding to position (same direction)
        - Reducing position (opposite direction, partial)
        - Closing position (opposite direction, full)
        - Flipping position (opposite direction, more than current)
        """
        realized_pnl = Decimal('0')

        # Determine if adding or reducing
        is_adding = (
            (current.is_long and fill.side == FillSide.BUY) or
            (current.is_short and fill.side == FillSide.SELL)
        )

        if is_adding:
            # Adding to position - recalculate average price
            new_quantity = current.quantity + fill.quantity
            total_cost = (current.quantity * current.avg_entry_price) + (fill.quantity * fill.price)
            new_avg_price = total_cost / new_quantity

            current.quantity = new_quantity
            current.avg_entry_price = new_avg_price
            current.total_cost_basis = new_quantity * new_avg_price

        else:
            # Reducing or flipping position
            if fill.quantity < current.quantity:
                # Partial reduction
                realized_pnl = self._calculate_realized_pnl_for_reduction(
                    current, fill.quantity, fill.price
                )
                current.quantity -= fill.quantity
                current.total_cost_basis = current.quantity * current.avg_entry_price
                # Average price stays the same

            elif fill.quantity == current.quantity:
                # Full close
                realized_pnl = self._calculate_realized_pnl_for_reduction(
                    current, fill.quantity, fill.price
                )
                current.quantity = Decimal('0')
                current.side = PositionSide.FLAT
                current.status = PositionStatus.CLOSED
                current.total_cost_basis = Decimal('0')

            else:
                # Flip position
                # First, close existing position
                realized_pnl = self._calculate_realized_pnl_for_reduction(
                    current, current.quantity, fill.price
                )

                # Then open new position in opposite direction
                remaining_qty = fill.quantity - current.quantity
                current.quantity = remaining_qty
                current.side = PositionSide.LONG if fill.side == FillSide.BUY else PositionSide.SHORT
                current.avg_entry_price = fill.price
                current.total_cost_basis = remaining_qty * fill.price

        # Update common fields
        current.last_fill_at = fill.timestamp
        current.current_price = fill.price
        current.market_value = abs(current.quantity) * current.current_price
        current.realized_pnl += realized_pnl
        current.unrealized_pnl = self._calculate_unrealized_pnl(current)
        current.fills.append(fill)

        return current, realized_pnl

    def _calculate_realized_pnl_for_reduction(
        self,
        position: BookPosition,
        closed_quantity: Decimal,
        exit_price: Decimal
    ) -> Decimal:
        """Calculate realized P&L when reducing a position"""
        if position.is_long:
            # Long: profit when exit > entry
            pnl_per_share = exit_price - position.avg_entry_price
        else:
            # Short: profit when exit < entry
            pnl_per_share = position.avg_entry_price - exit_price

        return pnl_per_share * closed_quantity

    def _calculate_unrealized_pnl(self, position: BookPosition) -> Decimal:
        """Calculate unrealized P&L for a position"""
        if position.quantity == Decimal('0'):
            return Decimal('0')

        if position.is_long:
            return (position.current_price - position.avg_entry_price) * position.quantity
        else:
            return (position.avg_entry_price - position.current_price) * position.quantity

    def _calculate_cash_change(self, fill: Fill, realized_pnl: Decimal) -> Decimal:
        """
        Calculate cash change from a fill.

        BUY: cash decreases (cost + commission)
        SELL: cash increases (proceeds - commission)
        """
        notional = fill.quantity * fill.price
        total_costs = fill.commission + fill.slippage

        if fill.side == FillSide.BUY:
            # Pay for shares + costs
            return -(notional + total_costs)
        else:
            # Receive proceeds - costs
            return notional - total_costs

    def _publish_event(self, update: PositionUpdate) -> None:
        """Publish position update to all subscribers"""
        for handler in self._subscribers:
            try:
                handler(update)
            except Exception as e:
                logger.error(f"Error in position update handler: {e}")

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of position book state"""
        with self._lock:
            positions = list(self._positions.values())

            return {
                'book_id': self._book_id,
                'initial_capital': float(self._initial_capital),
                'cash_balance': float(self._cash_balance),
                'portfolio_value': float(self.get_portfolio_value()),
                'total_realized_pnl': float(self._total_realized_pnl),
                'total_unrealized_pnl': float(self.get_unrealized_pnl()),
                'total_pnl': float(self.get_total_pnl()),
                'position_count': len(positions),
                'long_count': sum(1 for p in positions if p.is_long),
                'short_count': sum(1 for p in positions if p.is_short),
                'fill_count': len(self._fill_history),
                'return_pct': float(
                    (self.get_portfolio_value() / self._initial_capital - 1) * 100
                ) if self._initial_capital > 0 else 0.0
            }

    def __repr__(self) -> str:
        summary = self.get_summary()
        return (
            f"PositionBook(id={summary['book_id'][:8]}..., "
            f"value=${summary['portfolio_value']:,.2f}, "
            f"positions={summary['position_count']}, "
            f"pnl=${summary['total_pnl']:,.2f})"
        )
