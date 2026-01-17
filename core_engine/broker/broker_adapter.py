"""
Unified Broker Adapter Facade (Async)
Provides a consistent async interface for multiple broker types.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from core_engine.type_definitions.broker_types import (
    Order, OrderSide, OrderType, Position, AccountInfo
)
from core_engine.broker.adapters.base_adapter import BaseBrokerAdapter
from core_engine.system.interfaces import RegimeContext

logger = logging.getLogger(__name__)

class BrokerAdapter:
    """
    Facade class that wraps specific broker implementations (Async)
    """

    def __init__(self, adapter: BaseBrokerAdapter):
        """
        Initialize with a concrete adapter (IBKR, Alpaca, Paper, etc.)
        """
        self.adapter = adapter
        self._regime_context: Optional[RegimeContext] = None

    def update_regime_context(self, context: RegimeContext):
        """Update the regime context for regime-adaptive logic"""
        self._regime_context = context

    # ==================== Connection ====================

    async def connect(self) -> bool:
        return await self.adapter.connect()

    async def disconnect(self) -> None:
        await self.adapter.disconnect()

    def is_connected(self) -> bool:
        return self.adapter.is_connected()

    async def check_health(self) -> Dict[str, Any]:
        return await self.adapter.check_connection_health()

    # ==================== Trading ====================

    async def submit_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None
    ) -> Order:
        """
        Unified order submission with regime-awareness logic
        """
        # Regime-aware logic: Override order types or add protections
        if self._regime_context and self._regime_context.volatility > 2.0:
            if order_type == OrderType.MARKET:
                logger.warning(f"⚠️ High volatility detected ({self._regime_context.volatility}). Forcing limit order for {symbol}")
                order_type = OrderType.LIMIT
                # If no limit price provided, use a wide buffer from last quote
                if limit_price is None:
                    quote = await self.adapter.get_latest_quote(symbol)
                    if quote:
                        if side == OrderSide.BUY:
                            limit_price = quote['ask_price'] * 1.01 # 1% buffer
                        else:
                            limit_price = quote['bid_price'] * 0.99 # 1% buffer

        if order_type == OrderType.MARKET:
            return await self.adapter.submit_market_order(symbol, quantity, side)
        elif order_type == OrderType.LIMIT:
            if limit_price is None:
                raise ValueError("limit_price must be provided for LIMIT orders")
            return await self.adapter.submit_limit_order(symbol, quantity, side, limit_price)
        else:
            raise NotImplementedError(f"Order type {order_type} not implemented in facade")

    async def cancel_order(self, order_id: str) -> bool:
        return await self.adapter.cancel_order(order_id)

    async def cancel_all_orders(self) -> bool:
        return await self.adapter.cancel_all_orders()

    # ==================== Data Retrieval ====================

    async def get_positions(self) -> List[Position]:
        return await self.adapter.get_positions()

    async def get_account_info(self) -> AccountInfo:
        return await self.adapter.get_account_info()

    async def get_order(self, order_id: str) -> Optional[Order]:
        return await self.adapter.get_order(order_id)

    def broker_name(self) -> str:
        return self.adapter.broker_name()
