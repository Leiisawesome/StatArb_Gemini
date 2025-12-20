"""
PaperBrokerAdapter - Simulated Broker for Paper Trading
=======================================================

Implements BaseBrokerAdapter interface with realistic simulation:
- Configurable latency (50-200ms)
- Partial fills based on ADV participation
- Spread cost (half spread applied)
- Market impact (sqrt participation model)
- Slippage (random within bounds)
- Commissions (per-share or per-trade)
- Rejects (insufficient cash, halted, no liquidity)

Order Lifecycle (from plan Section 6.1):
PENDING_NEW → NEW → [PARTIALLY_FILLED] → FILLED | CANCELLED | REJECTED

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 4)
"""

import asyncio
import logging
import random
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
import threading

from .base_adapter import BaseBrokerAdapter
from ...type_definitions.broker_types import Order, OrderSide, OrderType, OrderStatus, Position, AccountInfo

logger = logging.getLogger(__name__)

class PaperOrderStatus(Enum):
    """Order status in paper trading."""
    PENDING_NEW = auto()
    NEW = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()

@dataclass
class PaperFill:
    """A fill event from paper trading."""
    fill_id: str
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    commission: float
    timestamp: datetime
    is_partial: bool = False

@dataclass
class PaperOrder:
    """Internal order representation for paper trading."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    # State
    status: PaperOrderStatus = PaperOrderStatus.PENDING_NEW
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None

    # Fills
    fills: List[PaperFill] = field(default_factory=list)

    # Rejection info
    rejection_reason: str = ""

    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity

@dataclass
class PaperPosition:
    """Position in paper trading."""
    symbol: str
    quantity: float
    avg_entry_price: float
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

class PaperBrokerAdapter(BaseBrokerAdapter):
    """
    Simulated broker for paper trading with realistic behaviors.

    Features:
    - Realistic fill simulation with slippage/impact
    - Partial fills based on ADV
    - Commission and fee calculation
    - Order rejection simulation
    - Latency simulation

    Thread-safe for concurrent order submission.
    """

    def __init__(
        self,
        initial_cash: float = 100_000.0,
        commission_per_share: float = 0.005,
        min_commission: float = 1.0,
        latency_ms_min: float = 50.0,
        latency_ms_max: float = 200.0,
        fill_probability: float = 0.95,
        partial_fill_probability: float = 0.10,
        slippage_bps_max: float = 5.0,
        impact_coefficient: float = 10.0,
        adv_table: Optional[Dict[str, float]] = None,
        spread_table: Optional[Dict[str, float]] = None,
        seed: Optional[int] = None,
        use_historical_execution_simulator: bool = False,
        historical_execution_simulator_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize paper broker.

        Args:
            initial_cash: Starting cash balance
            commission_per_share: Commission per share
            min_commission: Minimum commission per order
            latency_ms_min: Minimum simulated latency
            latency_ms_max: Maximum simulated latency
            fill_probability: Probability of market order fill
            partial_fill_probability: Probability of partial fill
            slippage_bps_max: Maximum random slippage in bps
            impact_coefficient: Market impact coefficient
            adv_table: Symbol -> ADV in shares
            spread_table: Symbol -> spread in bps
        """
        self._initial_cash = initial_cash
        self._cash = initial_cash
        self._commission_per_share = commission_per_share
        self._min_commission = min_commission
        self._latency_min = latency_ms_min
        self._latency_max = latency_ms_max
        self._fill_prob = fill_probability
        self._partial_prob = partial_fill_probability
        self._slippage_max = slippage_bps_max
        self._impact_coef = impact_coefficient
        self._adv_table = adv_table or {}
        self._spread_table = spread_table or {}
        self._seed = seed
        # Always use an instance RNG for determinism; never use module-level random.
        self._rng = random.Random(seed) if seed is not None else random.Random()

        # Optional: reuse backtest's deterministic execution cost model for parity
        self._use_historical_execution_simulator = bool(use_historical_execution_simulator)
        self._historical_execution_simulator_config = historical_execution_simulator_config or {}
        self._historical_execution_simulator = None

        # State
        self._connected = False
        self._orders: Dict[str, PaperOrder] = {}
        self._positions: Dict[str, PaperPosition] = {}
        self._prices: Dict[str, float] = {}  # Current prices
        self._latest_market_data: Dict[str, Dict[str, Any]] = {}
        self._next_order_context: Optional[Dict[str, Any]] = None

        # Halted symbols
        self._halted_symbols: set = set()

        # Fill sequence counter
        self._fill_seq = 0

        # Callbacks
        self._fill_callback: Optional[Callable[[PaperFill], None]] = None
        self._order_callback: Optional[Callable[[PaperOrder], None]] = None

        # Time source (optional; needed for replay-mode monotonic market timestamps)
        self._time_source: Optional[Any] = None

        # Thread safety
        self._lock = threading.Lock()

        # Stats
        self._stats = {
            'orders_submitted': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'orders_cancelled': 0,
            'partial_fills': 0,
            'total_commission': 0.0,
        }

    # ==================== Connection Management ====================

    def connect(self) -> bool:
        """Connect to paper broker (always succeeds)."""
        self._connected = True
        logger.info("📝 Paper broker connected")
        return True

    def disconnect(self) -> None:
        """Disconnect from paper broker."""
        self._connected = False
        logger.info("📝 Paper broker disconnected")

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    def check_connection_health(self) -> Dict[str, Any]:
        """Check connection health."""
        return {
            'connected': self._connected,
            'latency': (self._latency_min + self._latency_max) / 2,
            'last_heartbeat': self._now(),
            'type': 'paper',
        }

    def set_time_source(self, time_source: Any) -> None:
        """
        Set a TimeSource (ReplayTimeSource in papertest) so timestamps use market time, not wall time.

        This prevents dispatcher market time from jumping to wall-clock time on fills, which would
        break replay monotonicity (cannot move market time backwards).
        """
        self._time_source = time_source

    def _now(self) -> datetime:
        """
        Return a timestamp appropriate for this broker.

        In replay/papertest: prefer market_now() so fill events are ordered with replay bars.
        Fallback: wall-clock UTC.
        """
        try:
            ts = self._time_source.market_now() if self._time_source is not None else None
            if ts is not None:
                return ts
        except Exception:
            pass
        return datetime.now(timezone.utc)

    # ==================== Market Data ====================

    def set_price(self, symbol: str, price: float) -> None:
        """Set current price for a symbol (called by replay engine)."""
        with self._lock:
            self._prices[symbol] = price

    def set_market_data(self, symbol: str, bar: Dict[str, Any], market_timestamp: Any) -> None:
        """
        Store the most recent bar snapshot for execution simulation.
        This lets paper mode reuse backtest's HistoricalExecutionSimulator with identical OHLCV inputs.
        """
        try:
            self._latest_market_data[symbol] = {
                "timestamp": market_timestamp,
                "open": bar.get("open") or bar.get("open_price"),
                "high": bar.get("high"),
                "low": bar.get("low"),
                "close": bar.get("close") or bar.get("close_price"),
                "volume": bar.get("volume", 0),
                "volatility": bar.get("volatility", 0.02),
            }
        except Exception:
            # Best-effort; never break trading loop on telemetry
            pass

    def set_next_order_context(self, context: Dict[str, Any]) -> None:
        """
        Set one-shot context for the *next* submitted order.
        Used by paper execution routing to pass signal-time decision_price so we can
        match backtest's HistoricalExecutionSimulator semantics.
        """
        try:
            self._next_order_context = dict(context or {})
        except Exception:
            self._next_order_context = None

    def set_prices(self, prices: Dict[str, float]) -> None:
        """Set multiple prices at once."""
        with self._lock:
            self._prices.update(prices)

    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest quote (simulated from price + spread)."""
        with self._lock:
            if symbol not in self._prices:
                return None

            price = self._prices[symbol]
            spread_bps = self._spread_table.get(symbol, 5.0)
            half_spread = price * spread_bps / 10000 / 2

            return {
                'bid_price': price - half_spread,
                'ask_price': price + half_spread,
                'bid_size': 100,
                'ask_size': 100,
                'last_price': price,
                'timestamp': self._now(),
            }

    def is_market_open(self) -> bool:
        """Check if market is open (always True for paper)."""
        return True

    # ==================== Order Management ====================

    def _next_fill_id(self, order_id: str) -> str:
        """Generate next fill ID."""
        self._fill_seq += 1
        return f"{order_id}:{self._fill_seq:03d}"

    def _simulate_latency(self) -> float:
        """Get simulated latency in seconds."""
        latency_ms = self._rng.uniform(self._latency_min, self._latency_max)
        return latency_ms / 1000.0

    def _calculate_fill_price(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType,
        limit_price: Optional[float] = None,
    ) -> float:
        """Calculate realistic fill price with slippage and impact."""
        base_price = self._prices.get(symbol, 100.0)

        # Get spread
        spread_bps = self._spread_table.get(symbol, 5.0)
        half_spread = spread_bps / 2

        # Calculate impact
        adv = self._adv_table.get(symbol, 1_000_000)
        participation = quantity / adv if adv > 0 else 0
        impact_bps = math.sqrt(participation) * self._impact_coef

        # Random slippage
        slippage_bps = self._rng.uniform(0, self._slippage_max)

        # Total cost
        total_bps = half_spread + impact_bps + slippage_bps

        if side == OrderSide.BUY:
            fill_price = base_price * (1 + total_bps / 10000)
        else:
            fill_price = base_price * (1 - total_bps / 10000)

        # Apply limit price constraint
        if order_type == OrderType.LIMIT and limit_price:
            if side == OrderSide.BUY:
                fill_price = min(fill_price, limit_price)
            else:
                fill_price = max(fill_price, limit_price)

        return round(fill_price, 4)

    def _get_historical_execution_simulator(self):
        if self._historical_execution_simulator is not None:
            return self._historical_execution_simulator
        try:
            # Lazy import to avoid hard dependency during normal operation
            from backtest.engine.historical_execution_simulator import HistoricalExecutionSimulator
            cfg = {
                'fill_model': 'realistic',
                'base_spread_bps': 5.0,
                'base_slippage_bps': 2.0,
                'commission_per_share': float(self._commission_per_share),
                'enable_random_slippage': False,  # deterministic
                'impact_linear_coeff': 0.1,
                'impact_sqrt_coeff': 0.5,
                'disable_rejections': True,
            }
            cfg.update(self._historical_execution_simulator_config or {})
            self._historical_execution_simulator = HistoricalExecutionSimulator(cfg)
            return self._historical_execution_simulator
        except Exception:
            self._historical_execution_simulator = None
            return None

    def _calculate_commission(self, quantity: float) -> float:
        """Calculate commission for a fill."""
        commission = quantity * self._commission_per_share
        return max(commission, self._min_commission)

    def _check_rejection(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
    ) -> Optional[str]:
        """Check if order should be rejected."""
        # Check halted
        if symbol in self._halted_symbols:
            return f"Symbol {symbol} is halted"

        # Check cash for buys
        if side == OrderSide.BUY:
            required = quantity * price
            if required > self._cash:
                return f"Insufficient cash: need ${required:.2f}, have ${self._cash:.2f}"

        # Check position for sells
        if side == OrderSide.SELL:
            position = self._positions.get(symbol)
            if position is None or position.quantity < quantity:
                available = position.quantity if position else 0
                return f"Insufficient position: need {quantity}, have {available}"

        # Random rejection (simulate broker issues)
        if self._rng.random() > self._fill_prob:
            return "Order rejected by venue"

        return None

    async def _execute_order_async(self, order: PaperOrder) -> None:
        """Execute order asynchronously with simulated latency."""
        # Simulate latency
        await asyncio.sleep(self._simulate_latency())

        with self._lock:
            # Transition to NEW
            order.status = PaperOrderStatus.NEW
            order.submitted_at = self._now()
            # Capture a deterministic decision price + bar snapshot at submission time.
            # This avoids races where the engine updates broker price to bar-close before the async fill runs.
            try:
                dp_override = getattr(order, "_decision_price_override", None)
                if dp_override is not None:
                    setattr(order, "_paper_decision_price", float(dp_override))
                else:
                    setattr(order, "_paper_decision_price", float(self._prices.get(order.symbol, 100.0)))
                setattr(order, "_paper_market_data", dict(self._latest_market_data.get(order.symbol, {}) or {}))
            except Exception:
                pass

            if self._order_callback:
                self._order_callback(order)

        # Another latency for fill
        await asyncio.sleep(self._simulate_latency())

        with self._lock:
            # Check if cancelled
            if order.status == PaperOrderStatus.CANCELLED:
                return

            # Get fill price
            fill_price = None
            if self._use_historical_execution_simulator:
                sim = self._get_historical_execution_simulator()
                if sim is not None:
                    base_price = float(getattr(order, "_paper_decision_price", self._prices.get(order.symbol, 100.0)))
                    md0 = getattr(order, "_paper_market_data", None) or self._latest_market_data.get(order.symbol, {}) or {}
                    market_data = {
                        'timestamp': md0.get('timestamp', self._now()),
                        'open': md0.get('open', base_price),
                        'high': md0.get('high', base_price),
                        'low': md0.get('low', base_price),
                        # Match backtest: 'close' should be the decision price (bar-open execution)
                        'close': base_price,
                        'volume': md0.get('volume', 0),
                        'volatility': md0.get('volatility', 0.02),
                    }
                    # Pull optional context (regime/liquidity) from order context if provided
                    ctx = getattr(order, "_paper_context", None) if hasattr(order, "_paper_context") else None
                    regime_ctx = None
                    liquidity_score = None
                    try:
                        if isinstance(ctx, dict):
                            regime_ctx = ctx.get("regime_context")
                            liquidity_score = ctx.get("liquidity_score")
                    except Exception:
                        regime_ctx = None
                        liquidity_score = None
                    res = sim.simulate_fill_with_rejection(
                        symbol=order.symbol,
                        side=order.side.value.lower(),
                        quantity=float(order.remaining_quantity),
                        decision_price=base_price,
                        market_data=market_data,
                        authorization_id=getattr(order, "order_id", ""),
                        strategy_id="PAPER_SIM",
                        regime_context=regime_ctx if isinstance(regime_ctx, dict) else None,
                        liquidity_score=float(liquidity_score) if liquidity_score is not None else None,
                        max_retries=0,
                    )
                    sf = res.get('fill')
                    if sf is not None:
                        fill_price = float(getattr(sf, "fill_price", base_price))

            if fill_price is None:
                fill_price = self._calculate_fill_price(
                    order.symbol,
                    order.side,
                    order.quantity,
                    order.order_type,
                    order.limit_price,
                )

            # Determine fill quantity (partial fill simulation)
            if self._use_historical_execution_simulator:
                fill_qty = order.remaining_quantity
                is_partial = False
            elif self._rng.random() < self._partial_prob:
                fill_qty = self._rng.uniform(0.5, 0.9) * order.remaining_quantity
                fill_qty = round(fill_qty)
                is_partial = True
                self._stats['partial_fills'] += 1
            else:
                fill_qty = order.remaining_quantity
                is_partial = False

            # Create fill
            commission = self._calculate_commission(fill_qty)

            fill = PaperFill(
                fill_id=self._next_fill_id(order.order_id),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=fill_qty,
                price=fill_price,
                commission=commission,
                timestamp=self._now(),
                is_partial=is_partial,
            )

            # Update order
            order.fills.append(fill)
            order.filled_quantity += fill_qty

            # Update average fill price
            total_value = order.avg_fill_price * (order.filled_quantity - fill_qty) + fill_price * fill_qty
            order.avg_fill_price = total_value / order.filled_quantity

            if order.remaining_quantity <= 0:
                order.status = PaperOrderStatus.FILLED
                order.filled_at = self._now()
                self._stats['orders_filled'] += 1
            else:
                order.status = PaperOrderStatus.PARTIALLY_FILLED

            # Update position
            self._update_position(order.symbol, order.side, fill_qty, fill_price)

            # Update cash
            if order.side == OrderSide.BUY:
                self._cash -= fill_qty * fill_price + commission
            else:
                self._cash += fill_qty * fill_price - commission

            self._stats['total_commission'] += commission

            # Callbacks
            if self._fill_callback:
                self._fill_callback(fill)
            if self._order_callback:
                self._order_callback(order)

    def _update_position(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
    ) -> None:
        """Update position from fill."""
        if symbol not in self._positions:
            self._positions[symbol] = PaperPosition(
                symbol=symbol,
                quantity=0.0,
                avg_entry_price=0.0,
            )

        pos = self._positions[symbol]

        if side == OrderSide.BUY:
            # Add to position
            total_value = pos.quantity * pos.avg_entry_price + quantity * price
            pos.quantity += quantity
            if pos.quantity > 0:
                pos.avg_entry_price = total_value / pos.quantity
        else:
            # Reduce position
            pos.quantity -= quantity
            if pos.quantity <= 0:
                pos.realized_pnl += pos.unrealized_pnl
                pos.quantity = 0
                pos.avg_entry_price = 0

    def submit_market_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
    ) -> Order:
        """Submit a market order."""
        return self._submit_order(symbol, quantity, side, OrderType.MARKET)

    def submit_limit_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        limit_price: float,
    ) -> Order:
        """Submit a limit order."""
        return self._submit_order(symbol, quantity, side, OrderType.LIMIT, limit_price)

    def submit_stop_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        stop_price: float,
    ) -> Order:
        """Submit a stop order."""
        return self._submit_order(symbol, quantity, side, OrderType.STOP, stop_price=stop_price)

    def submit_stop_limit_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        stop_price: float,
        limit_price: float,
    ) -> Order:
        """Submit a stop-limit order."""
        return self._submit_order(
            symbol, quantity, side, OrderType.STOP_LIMIT,
            limit_price=limit_price, stop_price=stop_price
        )

    def _submit_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Order:
        """Internal order submission."""
        with self._lock:
            order_id = str(uuid.uuid4())
            ctx = self._next_order_context or {}
            self._next_order_context = None

            paper_order = PaperOrder(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                limit_price=limit_price,
                stop_price=stop_price,
            )
            # Attach context (best-effort)
            try:
                dp = ctx.get("decision_price", None)
                if dp is not None:
                    setattr(paper_order, "_decision_price_override", float(dp))
                setattr(paper_order, "_paper_context", dict(ctx))
            except Exception:
                pass

            # Check for immediate rejection
            est_price = limit_price or self._prices.get(symbol, 100.0)
            rejection = self._check_rejection(symbol, side, quantity, est_price)

            if rejection:
                paper_order.status = PaperOrderStatus.REJECTED
                paper_order.rejection_reason = rejection
                self._orders[order_id] = paper_order
                self._stats['orders_rejected'] += 1
                logger.warning(f"Order rejected: {rejection}")
            else:
                self._orders[order_id] = paper_order
                self._stats['orders_submitted'] += 1

                # Execute asynchronously
                asyncio.create_task(self._execute_order_async(paper_order))

            # Convert to Order type
            return Order(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=limit_price,
                stop_price=stop_price,
                status=OrderStatus(paper_order.status.name.lower()) if paper_order.status.name.lower() in [s.value for s in OrderStatus] else OrderStatus.PENDING,
                filled_quantity=0,
                average_price=0.0,
            )

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        with self._lock:
            if order_id not in self._orders:
                return False

            order = self._orders[order_id]

            if order.status in (PaperOrderStatus.FILLED, PaperOrderStatus.CANCELLED, PaperOrderStatus.REJECTED):
                return False

            order.status = PaperOrderStatus.CANCELLED
            self._stats['orders_cancelled'] += 1

            if self._order_callback:
                self._order_callback(order)

            return True

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[float] = None,
        limit_price: Optional[float] = None,
    ) -> bool:
        """Modify an existing order."""
        with self._lock:
            if order_id not in self._orders:
                return False

            order = self._orders[order_id]

            if order.status not in (PaperOrderStatus.NEW, PaperOrderStatus.PARTIALLY_FILLED):
                return False

            if quantity is not None:
                order.quantity = quantity
            if limit_price is not None:
                order.limit_price = limit_price

            return True

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        with self._lock:
            if order_id not in self._orders:
                return None

            paper_order = self._orders[order_id]

            return Order(
                order_id=paper_order.order_id,
                symbol=paper_order.symbol,
                side=paper_order.side,
                order_type=paper_order.order_type,
                quantity=paper_order.quantity,
                price=paper_order.limit_price,
                stop_price=paper_order.stop_price,
                status=self._map_paper_status_to_order_status(paper_order.status),
                filled_quantity=paper_order.filled_quantity,
                average_price=paper_order.avg_fill_price,
            )

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders."""
        with self._lock:
            open_statuses = {PaperOrderStatus.PENDING_NEW, PaperOrderStatus.NEW, PaperOrderStatus.PARTIALLY_FILLED}

            orders = [
                o for o in self._orders.values()
                if o.status in open_statuses
            ]

            if symbol:
                orders = [o for o in orders if o.symbol == symbol]

            return [
                Order(
                    order_id=o.order_id,
                    symbol=o.symbol,
                    side=o.side,
                    order_type=o.order_type,
                    quantity=o.quantity,
                    price=o.limit_price,
                    stop_price=o.stop_price,
                    status=self._map_paper_status_to_order_status(o.status),
                    filled_quantity=o.filled_quantity,
                    average_price=o.avg_fill_price,
                )
                for o in orders
            ]

    def _map_paper_status_to_order_status(self, paper_status: PaperOrderStatus) -> OrderStatus:
        """Map PaperOrderStatus to OrderStatus."""
        status_map = {
            PaperOrderStatus.PENDING_NEW: OrderStatus.PENDING,
            PaperOrderStatus.NEW: OrderStatus.SUBMITTED,
            PaperOrderStatus.PARTIALLY_FILLED: OrderStatus.PARTIAL_FILLED,
            PaperOrderStatus.FILLED: OrderStatus.FILLED,
            PaperOrderStatus.CANCELLED: OrderStatus.CANCELLED,
            PaperOrderStatus.REJECTED: OrderStatus.REJECTED,
        }
        return status_map.get(paper_status, OrderStatus.PENDING)

    # ==================== Position Management ====================

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol."""
        with self._lock:
            if symbol not in self._positions:
                return None

            pos = self._positions[symbol]
            current_price = self._prices.get(symbol, pos.avg_entry_price)

            cost_basis = pos.quantity * pos.avg_entry_price
            unrealized_pl = (current_price - pos.avg_entry_price) * pos.quantity
            unrealized_plpc = (unrealized_pl / cost_basis * 100) if cost_basis > 0 else 0.0
            return Position(
                symbol=symbol,
                quantity=pos.quantity,
                avg_entry_price=pos.avg_entry_price,
                current_price=current_price,
                market_value=pos.quantity * current_price,
                unrealized_pl=unrealized_pl,
                unrealized_plpc=unrealized_plpc,
                side="long" if pos.quantity > 0 else "short",
                cost_basis=cost_basis,
            )

    def get_all_positions(self) -> List[Position]:
        """Get all positions."""
        with self._lock:
            positions = []
            for symbol, pos in self._positions.items():
                if pos.quantity > 0:
                    current_price = self._prices.get(symbol, pos.avg_entry_price)
                    cost_basis = pos.quantity * pos.avg_entry_price
                    unrealized_pl = (current_price - pos.avg_entry_price) * pos.quantity
                    unrealized_plpc = (unrealized_pl / cost_basis * 100) if cost_basis > 0 else 0.0
                    positions.append(Position(
                        symbol=symbol,
                        quantity=pos.quantity,
                        avg_entry_price=pos.avg_entry_price,
                        current_price=current_price,
                        market_value=pos.quantity * current_price,
                        unrealized_pl=unrealized_pl,
                        unrealized_plpc=unrealized_plpc,
                        side="long" if pos.quantity > 0 else "short",
                        cost_basis=cost_basis,
                    ))
            return positions

    # ==================== Account Management ====================

    def get_account_info(self) -> AccountInfo:
        """Get account information."""
        with self._lock:
            # Calculate total equity
            position_value = sum(
                pos.quantity * self._prices.get(pos.symbol, pos.avg_entry_price)
                for pos in self._positions.values()
            )
            total_equity = self._cash + position_value

            return AccountInfo(
                account_id="paper-account",
                cash=self._cash,
                buying_power=self._cash,
                portfolio_value=total_equity,
                equity=total_equity,
            )

    def get_buying_power(self) -> float:
        """Get available buying power."""
        return self._cash

    # ==================== Paper-Specific Methods ====================

    def halt_symbol(self, symbol: str) -> None:
        """Halt a symbol from trading."""
        with self._lock:
            self._halted_symbols.add(symbol)

    def resume_symbol(self, symbol: str) -> None:
        """Resume a halted symbol."""
        with self._lock:
            self._halted_symbols.discard(symbol)

    def set_fill_callback(self, callback: Callable[[PaperFill], None]) -> None:
        """Set callback for fill events."""
        self._fill_callback = callback

    def set_order_callback(self, callback: Callable[[PaperOrder], None]) -> None:
        """Set callback for order status updates."""
        self._order_callback = callback

    def reset(self) -> None:
        """Reset paper broker to initial state."""
        with self._lock:
            self._cash = self._initial_cash
            self._orders.clear()
            self._positions.clear()
            self._prices.clear()
            self._halted_symbols.clear()
            self._fill_seq = 0
            for key in self._stats:
                self._stats[key] = 0
            logger.info("📝 Paper broker reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get paper broker statistics."""
        with self._lock:
            return {
                **self._stats,
                'cash': self._cash,
                'position_count': len([p for p in self._positions.values() if p.quantity > 0]),
                'open_orders': len(self.get_open_orders()),
            }

    # ==================== Abstract Method Implementations ====================

    @property
    def broker_name(self) -> str:
        """Return broker name."""
        return "PaperBroker"

    @property
    def supports_fractional_shares(self) -> bool:
        """Does this broker support fractional shares?"""
        return True

    @property
    def supports_crypto(self) -> bool:
        """Does this broker support cryptocurrency trading?"""
        return False

    @property
    def min_order_size(self) -> float:
        """Minimum order size for this broker."""
        return 1.0

    def get_orders(self, status: str = "open") -> List[Order]:
        """Get orders with specified status."""
        with self._lock:
            if status == "open":
                return self.get_open_orders()
            elif status == "closed":
                closed_statuses = {PaperOrderStatus.FILLED, PaperOrderStatus.CANCELLED, PaperOrderStatus.REJECTED}
                orders = [o for o in self._orders.values() if o.status in closed_statuses]
            else:  # all
                orders = list(self._orders.values())

            return [
                Order(
                    order_id=o.order_id,
                    symbol=o.symbol,
                    side=o.side,
                    order_type=o.order_type,
                    quantity=o.quantity,
                    price=o.limit_price,
                    stop_price=o.stop_price,
                    status=self._map_paper_status_to_order_status(o.status),
                    filled_quantity=o.filled_quantity,
                    average_price=o.avg_fill_price,
                )
                for o in orders
            ]

    def get_positions(self) -> List[Position]:
        """Get all current positions."""
        return self.get_all_positions()

    def close_position(self, symbol: str) -> Order:
        """Close a position (market order to close)."""
        with self._lock:
            if symbol not in self._positions:
                raise ValueError(f"No position found for {symbol}")

            pos = self._positions[symbol]
            if pos.quantity <= 0:
                raise ValueError(f"No position to close for {symbol}")

            return self.submit_market_order(symbol, pos.quantity, OrderSide.SELL)

    def close_all_positions(self) -> List[Order]:
        """Close all positions."""
        orders = []
        with self._lock:
            symbols_to_close = [
                symbol for symbol, pos in self._positions.items()
                if pos.quantity > 0
            ]

        for symbol in symbols_to_close:
            try:
                order = self.close_position(symbol)
                orders.append(order)
            except Exception as e:
                logger.error(f"Failed to close position for {symbol}: {e}")

        return orders

    def validate_order_params(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> tuple:
        """Validate order parameters before submission."""
        # Check quantity
        if quantity <= 0:
            return (False, "Quantity must be positive")

        if quantity < self.min_order_size:
            return (False, f"Quantity below minimum order size of {self.min_order_size}")

        # Check limit price for limit orders
        if order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
            if limit_price is None or limit_price <= 0:
                return (False, "Limit price required and must be positive")

        # Check stop price for stop orders
        if order_type in (OrderType.STOP, OrderType.STOP_LIMIT):
            if stop_price is None or stop_price <= 0:
                return (False, "Stop price required and must be positive")

        # Check cash for buys
        if side == OrderSide.BUY:
            est_price = limit_price or self._prices.get(symbol, 100.0)
            required = quantity * est_price
            if required > self._cash:
                return (False, f"Insufficient cash: need ${required:.2f}, have ${self._cash:.2f}")

        # Check position for sells
        if side == OrderSide.SELL:
            with self._lock:
                position = self._positions.get(symbol)
                if position is None or position.quantity < quantity:
                    available = position.quantity if position else 0
                    return (False, f"Insufficient position: need {quantity}, have {available}")

        # Check halted symbol
        if symbol in self._halted_symbols:
            return (False, f"Symbol {symbol} is halted")

        return (True, None)

