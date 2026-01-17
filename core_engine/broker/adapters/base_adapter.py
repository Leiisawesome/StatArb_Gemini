"""
Base Broker Adapter Interface (Async)
Abstract base class that all broker adapters must implement for consistency
"""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from core_engine.type_definitions.broker_types import (
    Order, OrderSide, OrderType, Position, AccountInfo
)

class BaseBrokerAdapter(ABC):
    """
    Abstract base class for all broker adapters (Async)

    This ensures consistent interface across different brokers (Alpaca, IBKR, etc.)
    and allows for seamless broker switching and failover.
    """

    # ==================== Connection Management ====================

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to broker (Async)

        Returns:
            bool: True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from broker and clean up resources (Async)
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if currently connected to broker (Sync)

        Returns:
            bool: True if connected, False otherwise
        """
        pass

    @abstractmethod
    async def check_connection_health(self) -> Dict[str, Any]:
        """
        Check connection health and return status (Async)

        Returns:
            dict: Health status with keys like 'connected', 'latency', 'last_heartbeat'
        """
        pass

    # ==================== Market Data ====================

    @abstractmethod
    async def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest quote for a symbol (Async)

        Args:
            symbol: Stock symbol (e.g., 'SPY')

        Returns:
            dict: Quote data
        """
        pass

    @abstractmethod
    def is_market_open(self) -> bool:
        """
        Check if market is currently open (Sync/Fast)

        Returns:
            bool: True if market is open, False otherwise
        """
        pass

    # ==================== Order Management ====================

    @abstractmethod
    async def submit_market_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide
    ) -> Order:
        """
        Submit a market order (Async)

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: Order side (BUY/SELL)

        Returns:
            Order: Standardized Order object
        """
        pass

    @abstractmethod
    async def submit_limit_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        limit_price: float
    ) -> Order:
        """
        Submit a limit order (Async)

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: Order side
            limit_price: Fixed price target

        Returns:
            Order: Standardized Order object
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order (Async)

        Args:
            order_id: Broker's order ID

        Returns:
            bool: True if successfully cancelled
        """
        pass

    @abstractmethod
    async def cancel_all_orders(self) -> bool:
        """
        Cancel all open orders (Async)

        Returns:
            bool: True if all attempts succeeded
        """
        pass

    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order details by ID (Async)

        Args:
            order_id: Broker's order ID

        Returns:
            Optional[Order]: Standardized Order object or None
        """
        pass

    @abstractmethod
    async def get_orders(self, status: str = "open") -> List[Order]:
        """
        Get all orders with specific status (Async)

        Args:
            status: 'open', 'closed', 'all'

        Returns:
            List[Order]: List of standardized Order objects
        """
        pass

    # ==================== Account & Positions ====================

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get list of current positions (Async)

        Returns:
            List[Position]: List of standardized Position objects
        """
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for a specific symbol (Async)

        Args:
            symbol: Stock symbol

        Returns:
            Optional[Position]: Standardized Position object or None
        """
        pass

    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """
        Get account equity, buying power, etc. (Async)

        Returns:
            AccountInfo: Standardized AccountInfo object
        """
        pass

    # ==================== Utility ====================

    @abstractmethod
    def broker_name(self) -> str:
        """
        Return the name of the broker (Sync)

        Returns:
            str: e.g., 'Interactive Brokers', 'Alpaca'
        """
        pass
