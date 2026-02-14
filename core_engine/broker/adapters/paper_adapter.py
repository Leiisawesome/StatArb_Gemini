"""
Paper Trading Adapter (Async)
Simulated broker for testing and paper trading.
"""

import asyncio
import logging
import uuid
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from core_engine.broker.adapters.base_adapter import BaseBrokerAdapter
from core_engine.type_definitions.broker_types import (
    Order, OrderSide, OrderType, OrderStatus, Position, AccountInfo
)

logger = logging.getLogger(__name__)

class PaperBrokerAdapter(BaseBrokerAdapter):
    """
    Simulated broker adapter with async support.
    Supports both simple probabilistic fills and institutional-grade historical simulation.
    """

    def __init__(
        self,
        initial_cash: float = 1_000_000.0,
        commission_per_share: float = 0.005,
        latency_ms_min: float = 50.0,
        latency_ms_max: float = 200.0,
        min_commission: float = 1.0,
        fill_probability: float = 0.95,
        partial_fill_probability: float = 0.10,
        slippage_bps_max: float = 5.0,
        impact_coefficient: float = 10.0,
        seed: Optional[int] = None,
        use_historical_execution_simulator: bool = False,
    ):
        self.equity = initial_cash
        self.cash = initial_cash
        self.commission_per_share = commission_per_share
        self.latency_ms_min = latency_ms_min
        self.latency_ms_max = latency_ms_max
        self.min_commission = min_commission
        self.fill_probability = fill_probability
        self.partial_fill_probability = partial_fill_probability
        self.slippage_bps_max = slippage_bps_max
        self.impact_coefficient = impact_coefficient
        self.use_historical_execution_simulator = use_historical_execution_simulator
        
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.current_prices: Dict[str, float] = {}
        self._connected = False
        self._time_source = None
        self._fill_callback = None
        self._next_order_context = {}

        if seed is not None:
            import random
            random.seed(seed)
            import numpy as np
            np.random.seed(seed)

    def set_time_source(self, time_source: Any) -> None:
        self._time_source = time_source

    def set_fill_callback(self, callback: Callable) -> None:
        self._fill_callback = callback

    def set_next_order_context(self, context: Dict[str, Any]) -> None:
        self._next_order_context = context

    async def connect(self) -> bool:
        await asyncio.sleep(0.05)  # Simulate network lag
        self._connected = True
        logger.info("✅ Paper Broker connected")
        return True

    async def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    async def check_connection_health(self) -> Dict[str, Any]:
        return {"connected": self._connected, "latency": 0.001}

    async def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        # In a real paper trader, this would hit a data provider
        # Here we just mock it for interface consistency
        return {
            "bid_price": 100.0,
            "ask_price": 100.05,
            "timestamp": datetime.now()
        }

    def is_market_open(self) -> bool:
        return True

    async def submit_market_order(self, symbol: str, quantity: float, side: OrderSide) -> Order:
        if not self._connected:
            raise RuntimeError("Broker not connected")

        # Simulate latency
        import random
        latency_sec = random.uniform(self.latency_ms_min, self.latency_ms_max) / 1000.0
        await asyncio.sleep(latency_sec)

        order_id = str(uuid.uuid4())
        
        # Check fill probability
        if random.random() > self.fill_probability:
            order = Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=OrderType.MARKET,
                order_id=order_id,
                status=OrderStatus.REJECTED,
                timestamp=self._get_now()
            )
            self.orders[order_id] = order
            return order

        # Simplified fill logic for now (could be enhanced with Realistic costs later)
        # In a real implementation with use_historical_execution_simulator=True, 
        # we would call self.simulator.simulate_fill here.
        
        fill_price = 100.0  # Last resort default
        if "decision_price" in self._next_order_context:
            fill_price = self._next_order_context["decision_price"]
        elif symbol in self.positions:
            fill_price = self.positions[symbol].average_price
        else:
            logger.warning(f"No price context for {symbol}, using default mock price $100.0")
        
        # Apply slippage
        slippage = random.uniform(0, self.slippage_bps_max) / 10000.0
        if side == OrderSide.BUY:
            fill_price *= (1 + slippage)
        else:
            fill_price *= (1 - slippage)

        commission = max(self.min_commission, quantity * self.commission_per_share)
        
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            order_id=order_id,
            status=OrderStatus.FILLED,
            timestamp=self._get_now(),
            average_price=fill_price,
            commission=commission
        )
        
        # Update positions and cash
        self._update_account(symbol, quantity, side, fill_price, commission)
            
        self.orders[order_id] = order
        
        # Trigger fill callback
        if self._fill_callback:
            # Wrap in try-except to avoid breaking the execution loop
            try:
                self._fill_callback(order)
            except Exception as e:
                logger.error(f"Error in paper broker fill callback: {e}")

        # Clear context
        self._next_order_context = {}
            
        return order

    def _get_now(self) -> datetime:
        if self._time_source:
            return self._time_source.market_now()
        return datetime.now()

    def _update_account(self, symbol, quantity, side, price, commission):
        q_change = quantity if side == OrderSide.BUY else -quantity
        cost = quantity * price
        
        if side == OrderSide.BUY:
            self.cash -= (cost + commission)
        else:
            self.cash += (cost - commission)

        if symbol in self.positions:
            old_q = self.positions[symbol].quantity
            old_px = self.positions[symbol].average_price
            new_q = old_q + q_change
            
            if new_q == 0:
                del self.positions[symbol]
            else:
                # Basic average price update for buys
                if side == OrderSide.BUY:
                    new_px = (old_q * old_px + cost) / new_q
                else:
                    new_px = old_px # Simplified
                self.positions[symbol] = Position(symbol=symbol, quantity=new_q, average_price=new_px)
        else:
            self.positions[symbol] = Position(symbol=symbol, quantity=q_change, average_price=price)
        
        # Update equity using best available prices
        self._recalculate_equity()

    def update_market_prices(self, prices: Dict[str, float]) -> None:
        """Update current market prices for accurate equity calculation."""
        self.current_prices.update(prices)
        self._recalculate_equity()

    def _recalculate_equity(self) -> None:
        """Recalculate equity using best available prices."""
        position_value = 0.0
        for symbol, pos in self.positions.items():
            price = self.current_prices.get(symbol, pos.average_price)
            position_value += pos.quantity * price
        self.equity = self.cash + position_value

    async def submit_limit_order(self, symbol: str, quantity: float, side: OrderSide, limit_price: float) -> Order:
        order_id = str(uuid.uuid4())
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=limit_price,
            order_id=order_id,
            status=OrderStatus.SUBMITTED,
            timestamp=datetime.now()
        )
        self.orders[order_id] = order
        return order

    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False

    async def cancel_all_orders(self) -> bool:
        for order in self.orders.values():
            if order.status in [OrderStatus.SUBMITTED, OrderStatus.OPEN]:
                order.status = OrderStatus.CANCELLED
        return True

    async def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)

    async def get_orders(self, status: str = "open") -> List[Order]:
        return list(self.orders.values())

    async def get_positions(self) -> List[Position]:
        return list(self.positions.values())

    async def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)

    async def get_account_info(self) -> AccountInfo:
        return AccountInfo(
            equity=self.equity,
            cash=self.cash,
            buying_power=self.cash * 2,
            timestamp=datetime.now()
        )

    def broker_name(self) -> str:
        return "PaperBroker"

