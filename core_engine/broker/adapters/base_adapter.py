"""
Base Broker Adapter Interface
Abstract base class that all broker adapters must implement for consistency
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from core_engine.type_definitions.broker_types import (
    Order, OrderSide, OrderType, Position, AccountInfo
)


class BaseBrokerAdapter(ABC):
    """
    Abstract base class for all broker adapters
    
    This ensures consistent interface across different brokers (Alpaca, IBKR, etc.)
    and allows for seamless broker switching and failover.
    """
    
    # ==================== Connection Management ====================
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to broker
        
        Returns:
            bool: True if connection successful, False otherwise
        """
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnect from broker and clean up resources
        """
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if currently connected to broker
        
        Returns:
            bool: True if connected, False otherwise
        """
    
    @abstractmethod
    def check_connection_health(self) -> Dict[str, Any]:
        """
        Check connection health and return status
        
        Returns:
            dict: Health status with keys like 'connected', 'latency', 'last_heartbeat'
        """
    
    # ==================== Market Data ====================
    
    @abstractmethod
    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest quote for a symbol
        
        Args:
            symbol: Stock symbol (e.g., 'SPY')
        
        Returns:
            dict: Quote data with keys:
                - bid_price: Current bid price
                - ask_price: Current ask price
                - bid_size: Bid size
                - ask_size: Ask size
                - last_price: Last trade price (optional)
                - timestamp: Quote timestamp
        """
    
    @abstractmethod
    def is_market_open(self) -> bool:
        """
        Check if market is currently open
        
        Returns:
            bool: True if market is open, False otherwise
        """
    
    # ==================== Order Management ====================
    
    @abstractmethod
    def submit_market_order(
        self, 
        symbol: str, 
        quantity: float, 
        side: OrderSide
    ) -> Order:
        """
        Submit a market order
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: OrderSide.BUY or OrderSide.SELL
        
        Returns:
            Order: Order object with order details and ID
        """
    
    @abstractmethod
    def submit_limit_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        limit_price: float
    ) -> Order:
        """
        Submit a limit order
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: OrderSide.BUY or OrderSide.SELL
            limit_price: Limit price for the order
        
        Returns:
            Order: Order object with order details and ID
        """
    
    @abstractmethod
    def submit_stop_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        stop_price: float
    ) -> Order:
        """
        Submit a stop order
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: OrderSide.BUY or OrderSide.SELL
            stop_price: Stop price that triggers the order
        
        Returns:
            Order: Order object with order details and ID
        """
    
    @abstractmethod
    def submit_stop_limit_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        stop_price: float,
        limit_price: float
    ) -> Order:
        """
        Submit a stop-limit order
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: OrderSide.BUY or OrderSide.SELL
            stop_price: Stop price that triggers the order
            limit_price: Limit price once triggered
        
        Returns:
            Order: Order object with order details and ID
        """
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            bool: True if cancellation successful, False otherwise
        """
    
    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order details
        
        Args:
            order_id: Order ID to retrieve
        
        Returns:
            Order: Order object if found, None otherwise
        """
    
    @abstractmethod
    def get_orders(self, status: str = "open") -> List[Order]:
        """
        Get orders with specified status
        
        Args:
            status: Order status filter ('open', 'closed', 'all')
        
        Returns:
            list[Order]: List of orders matching the status
        """
    
    # ==================== Position Management ====================
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """
        Get all current positions
        
        Returns:
            list[Position]: List of all positions
        """
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for a specific symbol
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Position: Position object if exists, None otherwise
        """
    
    @abstractmethod
    def close_position(self, symbol: str) -> Order:
        """
        Close a position (market order to close)
        
        Args:
            symbol: Stock symbol to close
        
        Returns:
            Order: Order object for the closing order
        """
    
    @abstractmethod
    def close_all_positions(self) -> List[Order]:
        """
        Close all positions
        
        Returns:
            list[Order]: List of closing orders
        """
    
    # ==================== Account Management ====================
    
    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """
        Get account information
        
        Returns:
            AccountInfo: Account details including balance, buying power, etc.
        """
    
    # ==================== Validation & Safety ====================
    
    @abstractmethod
    def validate_order_params(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate order parameters before submission
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: Order side
            order_type: Order type
            limit_price: Limit price (if applicable)
            stop_price: Stop price (if applicable)
        
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
    
    # ==================== Broker-Specific Info ====================
    
    @property
    @abstractmethod
    def broker_name(self) -> str:
        """
        Return broker name (e.g., 'Alpaca', 'Interactive Brokers')
        """
    
    @property
    @abstractmethod
    def supports_fractional_shares(self) -> bool:
        """
        Does this broker support fractional shares?
        """
    
    @property
    @abstractmethod
    def supports_crypto(self) -> bool:
        """
        Does this broker support cryptocurrency trading?
        """
    
    @property
    @abstractmethod
    def min_order_size(self) -> float:
        """
        Minimum order size for this broker
        """
    
    # ==================== Optional Advanced Features ====================
    
    def get_historical_bars(
        self,
        symbol: str,
        timeframe: str = "1Min",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical OHLCV bar data (optional, not all brokers support)
        
        Args:
            symbol: Stock symbol
            timeframe: Bar timeframe (e.g., '1Min', '1Hour', '1Day')
            start: Start datetime
            end: End datetime
            limit: Maximum number of bars
        
        Returns:
            list[dict]: List of OHLCV bars
        """
        raise NotImplementedError(f"{self.broker_name} does not support historical data")
    
    def subscribe_to_quotes(self, symbols: List[str], callback) -> bool:
        """
        Subscribe to real-time quote updates (optional)
        
        Args:
            symbols: List of symbols to subscribe to
            callback: Function to call with quote updates
        
        Returns:
            bool: True if subscription successful
        """
        raise NotImplementedError(f"{self.broker_name} does not support quote subscriptions")
    
    def unsubscribe_from_quotes(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from quote updates (optional)
        
        Args:
            symbols: List of symbols to unsubscribe from
        
        Returns:
            bool: True if unsubscription successful
        """
        raise NotImplementedError(f"{self.broker_name} does not support quote subscriptions")
