"""
Async Broker Manager
Coordinates multiple broker adapters and handles order management with asyncio safety.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any

from core_engine.type_definitions.broker_types import (
    Order, OrderSide, OrderType
)
from core_engine.broker.broker_adapter import BrokerAdapter
from core_engine.system.interfaces import RegimeContext

logger = logging.getLogger(__name__)

class BrokerManager:
    """
    Manages one or more BrokerAdapters with Async safety
    """

    def __init__(self, adapters: List[BrokerAdapter]):
        self.adapters = adapters
        self._lock = asyncio.Lock()  # Unified async lock
        self._active_orders: Dict[str, Order] = {}
        self._current_regime: Optional[RegimeContext] = None

    async def update_regime(self, context: RegimeContext):
        """Propagate regime changes to all adapters"""
        async with self._lock:
            self._current_regime = context
            for adapter in self.adapters:
                adapter.update_regime_context(context)
            logger.info(f"Regime updated in BrokerManager: {context.primary_regime}")

    async def submit_order_to_all(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET
    ) -> List[Order]:
        """Submit order to all configured brokers (e.g., for dual-broker execution)"""
        if not self.adapters:
            return []

        tasks = [
            adapter.submit_order(symbol, quantity, side, order_type)
            for adapter in self.adapters
        ]
        orders = await asyncio.gather(*tasks, return_exceptions=True)

        valid_orders: List[Order] = []
        for order in orders:
            if isinstance(order, Exception):
                logger.error(f"Order submission failed: {order}")
            else:
                valid_orders.append(order)

        async with self._lock:
            for order in valid_orders:
                self._active_orders[order.order_id] = order

        return valid_orders

    async def get_total_equity(self) -> float:
        """Aggregated equity across all brokers"""
        if not self.adapters:
            return 0.0

        tasks = [adapter.get_account_info() for adapter in self.adapters]
        accounts = await asyncio.gather(*tasks)
        return sum(acc.equity for acc in accounts)

    async def cancel_all_global(self) -> bool:
        """Emergency kill switch for all brokers"""
        if not self.adapters:
            return True

        tasks = [adapter.cancel_all_orders() for adapter in self.adapters]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Global cancel failed on adapter: {result}")
        return all(result is True for result in results)

    async def get_aggregated_positions(self) -> Dict[str, float]:
        """Aggregate positions across all accounts"""
        if not self.adapters:
            return {}

        aggregated = {}
        tasks = [adapter.get_positions() for adapter in self.adapters]
        all_pos_lists = await asyncio.gather(*tasks)
        
        for pos_list in all_pos_lists:
            for pos in pos_list:
                aggregated[pos.symbol] = aggregated.get(pos.symbol, 0.0) + pos.quantity
        
        return aggregated
