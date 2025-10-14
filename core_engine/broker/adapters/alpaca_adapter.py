"""
Alpaca Broker Adapter
Real broker integration for Alpaca Markets using alpaca-py SDK
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

# Alpaca SDK imports
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    GetOrdersRequest
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    OrderType,
    OrderStatus as AlpacaOrderStatus
)
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from core_engine.config.broker_config import AlpacaConfig
from core_engine.type_definitions.broker_types import (
    TimeInForce as SystemTimeInForce,
    Position,
    AccountInfo
)
from core_engine.type_definitions.orders import Order as SystemOrder

logger = logging.getLogger(__name__)


class AlpacaAdapter:
    """
    Alpaca Markets broker adapter for real trading integration
    
    Features:
    - REST API for trading operations (market & limit orders)
    - Account and position management
    - Order status tracking
    - Paper trading support
    - Comprehensive error handling
    """
    
    def __init__(self, config: AlpacaConfig):
        """
        Initialize Alpaca adapter
        
        Args:
            config: AlpacaConfig with API credentials and settings
        """
        self.config = config
        self._connected = False
        self._trading_client: Optional[TradingClient] = None
        self._data_client: Optional[StockHistoricalDataClient] = None
        self._stream_client: Optional[StockDataStream] = None
        
        logger.info(f"Initialized Alpaca adapter (paper_trading={config.paper_trading})")
    
    def connect(self) -> bool:
        """
        Connect to Alpaca API
        
        Returns:
            True if connection successful
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Create trading client
            self._trading_client = TradingClient(
                api_key=self.config.api_key,
                secret_key=self.config.secret_key,
                paper=self.config.paper_trading,
                url_override=self.config.base_url if self.config.base_url else None
            )
            
            # Create data client
            self._data_client = StockHistoricalDataClient(
                api_key=self.config.api_key,
                secret_key=self.config.secret_key
            )
            
            # Test connection by getting account
            account = self._trading_client.get_account()
            
            self._connected = True
            
            logger.info(f"✅ Connected to Alpaca (account: {account.account_number})")
            logger.info(f"   Status: {account.status}, Cash: ${float(account.cash):,.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            self._connected = False
            raise ConnectionError(f"Alpaca connection failed: {e}")
    
    def disconnect(self) -> bool:
        """
        Disconnect from Alpaca API
        
        Returns:
            True if disconnection successful
        """
        try:
            # Close any open streams
            if self._stream_client:
                # Stream client cleanup if needed
                pass
            
            self._trading_client = None
            self._data_client = None
            self._stream_client = None
            self._connected = False
            
            logger.info("✅ Disconnected from Alpaca")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Alpaca: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to Alpaca"""
        return self._connected and self._trading_client is not None
    
    def get_account_info(self) -> AccountInfo:
        """
        Get account information
        
        Returns:
            AccountInfo with account details
        
        Raises:
            RuntimeError: If not connected or request fails
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        try:
            account = self._trading_client.get_account()
            
            # Convert to system AccountInfo
            account_info = AccountInfo(
                account_id=account.account_number,
                cash=float(account.cash),
                buying_power=float(account.buying_power),
                portfolio_value=float(account.portfolio_value),
                equity=float(account.equity),
                currency="USD",
                is_pattern_day_trader=account.pattern_day_trader,
                day_trade_count=account.daytrade_count if hasattr(account, 'daytrade_count') else 0,
                status=account.status
            )
            
            logger.debug(f"Account info: cash=${account_info.cash:,.2f}, " 
                        f"equity=${account_info.equity:,.2f}")
            
            return account_info
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise RuntimeError(f"Get account info failed: {e}")
    
    def get_positions(self) -> List[Position]:
        """
        Get all open positions
        
        Returns:
            List of Position objects
        
        Raises:
            RuntimeError: If not connected or request fails
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        try:
            alpaca_positions = self._trading_client.get_all_positions()
            
            positions = []
            for pos in alpaca_positions:
                position = Position(
                    symbol=pos.symbol,
                    quantity=float(pos.qty),
                    avg_entry_price=float(pos.avg_entry_price),
                    market_value=float(pos.market_value),
                    unrealized_pl=float(pos.unrealized_pl),
                    unrealized_plpc=float(pos.unrealized_plpc),
                    current_price=float(pos.current_price),
                    side="long" if float(pos.qty) > 0 else "short",
                    cost_basis=float(pos.cost_basis)
                )
                positions.append(position)
            
            logger.debug(f"Retrieved {len(positions)} positions")
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise RuntimeError(f"Get positions failed: {e}")
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for specific symbol
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Position if exists, None otherwise
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        try:
            pos = self._trading_client.get_open_position(symbol)
            
            position = Position(
                symbol=pos.symbol,
                quantity=float(pos.qty),
                avg_entry_price=float(pos.avg_entry_price),
                market_value=float(pos.market_value),
                unrealized_pl=float(pos.unrealized_pl),
                unrealized_plpc=float(pos.unrealized_plpc),
                current_price=float(pos.current_price),
                side="long" if float(pos.qty) > 0 else "short",
                cost_basis=float(pos.cost_basis)
            )
            
            return position
            
        except Exception as e:
            # Position not found is not an error
            if "position does not exist" in str(e).lower():
                return None
            logger.error(f"Failed to get position for {symbol}: {e}")
            raise RuntimeError(f"Get position failed: {e}")
    
    def submit_market_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        time_in_force: str = "day"
    ) -> SystemOrder:
        """
        Submit market order
        
        Args:
            symbol: Stock symbol
            qty: Quantity (positive integer)
            side: "buy" or "sell"
            time_in_force: "day", "gtc", "ioc", "fok"
        
        Returns:
            Order object with order details
        
        Raises:
            ValueError: If parameters invalid
            RuntimeError: If order submission fails
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        # Validate parameters
        if qty <= 0:
            raise ValueError(f"Quantity must be positive: {qty}")
        
        if side.lower() not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {side}")
        
        try:
            # Convert to Alpaca enums
            alpaca_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            alpaca_tif = self._convert_tif_to_alpaca(time_in_force)
            
            # Create market order request
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=alpaca_side,
                time_in_force=alpaca_tif
            )
            
            # Submit order
            alpaca_order = self._trading_client.submit_order(order_request)
            
            # Convert to system Order
            order = self._convert_alpaca_order(alpaca_order)
            
            logger.info(f"✅ Market order submitted: {side.upper()} {qty} {symbol} "
                       f"(order_id={order.order_id})")
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to submit market order: {e}")
            raise RuntimeError(f"Market order submission failed: {e}")
    
    def submit_limit_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        limit_price: float,
        time_in_force: str = "day"
    ) -> SystemOrder:
        """
        Submit limit order
        
        Args:
            symbol: Stock symbol
            qty: Quantity (positive integer)
            side: "buy" or "sell"
            limit_price: Limit price
            time_in_force: "day", "gtc", "ioc", "fok"
        
        Returns:
            Order object with order details
        
        Raises:
            ValueError: If parameters invalid
            RuntimeError: If order submission fails
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        # Validate parameters
        if qty <= 0:
            raise ValueError(f"Quantity must be positive: {qty}")
        
        if side.lower() not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {side}")
        
        if limit_price <= 0:
            raise ValueError(f"Limit price must be positive: {limit_price}")
        
        try:
            # Convert to Alpaca enums
            alpaca_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            alpaca_tif = self._convert_tif_to_alpaca(time_in_force)
            
            # Create limit order request
            order_request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=alpaca_side,
                time_in_force=alpaca_tif,
                limit_price=limit_price
            )
            
            # Submit order
            alpaca_order = self._trading_client.submit_order(order_request)
            
            # Convert to system Order
            order = self._convert_alpaca_order(alpaca_order)
            
            logger.info(f"✅ Limit order submitted: {side.upper()} {qty} {symbol} "
                       f"@ ${limit_price} (order_id={order.order_id})")
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to submit limit order: {e}")
            raise RuntimeError(f"Limit order submission failed: {e}")
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if cancellation successful
        
        Raises:
            RuntimeError: If cancellation fails
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        try:
            self._trading_client.cancel_order_by_id(order_id)
            logger.info(f"✅ Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise RuntimeError(f"Order cancellation failed: {e}")
    
    def get_order(self, order_id: str) -> SystemOrder:
        """
        Get order by ID
        
        Args:
            order_id: Order ID
        
        Returns:
            Order object
        
        Raises:
            RuntimeError: If request fails
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        try:
            alpaca_order = self._trading_client.get_order_by_id(order_id)
            return self._convert_alpaca_order(alpaca_order)
            
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            raise RuntimeError(f"Get order failed: {e}")
    
    def get_orders(self, status: Optional[str] = None) -> List[SystemOrder]:
        """
        Get orders (optionally filtered by status)
        
        Args:
            status: Filter by status ("open", "closed", "all")
        
        Returns:
            List of Order objects
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        try:
            # Create request with status filter
            request = GetOrdersRequest(
                status=status if status else "all"
            )
            
            alpaca_orders = self._trading_client.get_orders(filter=request)
            
            orders = [self._convert_alpaca_order(order) for order in alpaca_orders]
            
            logger.debug(f"Retrieved {len(orders)} orders (status={status})")
            
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            raise RuntimeError(f"Get orders failed: {e}")
    
    # Helper methods
    
    def _convert_tif_to_alpaca(self, tif: str) -> TimeInForce:
        """Convert time-in-force string to Alpaca enum"""
        tif_map = {
            "day": TimeInForce.DAY,
            "gtc": TimeInForce.GTC,
            "ioc": TimeInForce.IOC,
            "fok": TimeInForce.FOK
        }
        
        tif_lower = tif.lower()
        if tif_lower not in tif_map:
            raise ValueError(f"Invalid time_in_force: {tif}")
        
        return tif_map[tif_lower]
    
    def _convert_alpaca_order(self, alpaca_order) -> SystemOrder:
        """Convert Alpaca order to system Order"""
        from core_engine.type_definitions.orders import OrderSide, OrderType, OrderStatus
        
        # Convert side
        side = OrderSide.BUY if alpaca_order.side.value.lower() == "buy" else OrderSide.SELL
        
        # Convert order type
        order_type_map = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP,
            "stop_limit": OrderType.STOP_LIMIT
        }
        order_type = order_type_map.get(alpaca_order.order_type.value.lower(), OrderType.MARKET)
        
        # Convert status
        status_str = self._convert_alpaca_status(alpaca_order.status)
        status_map = {
            "pending": OrderStatus.PENDING,
            "submitted": OrderStatus.SUBMITTED,
            "accepted": OrderStatus.SUBMITTED,
            "partially_filled": OrderStatus.PARTIAL_FILLED,
            "filled": OrderStatus.FILLED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
        }
        status = status_map.get(status_str, OrderStatus.PENDING)
        
        # Create order with metadata for additional fields
        order = SystemOrder(
            symbol=alpaca_order.symbol,
            side=side,
            quantity=float(alpaca_order.qty),
            order_type=order_type,
            price=float(alpaca_order.limit_price) if alpaca_order.limit_price else None,
            stop_price=float(alpaca_order.stop_price) if alpaca_order.stop_price else None,
            order_id=alpaca_order.id,
            status=status,
            filled_quantity=float(alpaca_order.filled_qty) if alpaca_order.filled_qty else 0,
            average_price=float(alpaca_order.filled_avg_price) if alpaca_order.filled_avg_price else None,
            metadata={
                "time_in_force": alpaca_order.time_in_force.value,
                "created_at": alpaca_order.created_at,
                "updated_at": alpaca_order.updated_at,
                "submitted_at": alpaca_order.submitted_at,
                "filled_at": alpaca_order.filled_at
            }
        )
        
        return order
    
    def _convert_alpaca_status(self, status: AlpacaOrderStatus) -> str:
        """Convert Alpaca order status to system status"""
        status_map = {
            AlpacaOrderStatus.NEW: "pending",
            AlpacaOrderStatus.PENDING_NEW: "pending",
            AlpacaOrderStatus.ACCEPTED: "accepted",
            AlpacaOrderStatus.PARTIALLY_FILLED: "partially_filled",
            AlpacaOrderStatus.FILLED: "filled",
            AlpacaOrderStatus.DONE_FOR_DAY: "done_for_day",
            AlpacaOrderStatus.CANCELED: "cancelled",
            AlpacaOrderStatus.EXPIRED: "expired",
            AlpacaOrderStatus.REPLACED: "replaced",
            AlpacaOrderStatus.PENDING_CANCEL: "pending_cancel",
            AlpacaOrderStatus.PENDING_REPLACE: "pending_replace",
            AlpacaOrderStatus.REJECTED: "rejected",
            AlpacaOrderStatus.SUSPENDED: "suspended",
            AlpacaOrderStatus.CALCULATED: "calculated"
        }
        
        return status_map.get(status, "unknown")
    
    # ========================================================================
    # ENHANCED FEATURES - Market Data & Status
    # ========================================================================
    
    def is_market_open(self) -> bool:
        """
        Check if market is currently open
        
        Returns:
            True if market is open for trading
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        try:
            clock = self._trading_client.get_clock()
            return clock.is_open
            
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
            return False
    
    def get_market_clock(self) -> Dict[str, Any]:
        """
        Get market clock information
        
        Returns:
            Dictionary with market timing information
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        try:
            clock = self._trading_client.get_clock()
            
            return {
                'timestamp': clock.timestamp,
                'is_open': clock.is_open,
                'next_open': clock.next_open,
                'next_close': clock.next_close
            }
            
        except Exception as e:
            logger.error(f"Failed to get market clock: {e}")
            raise RuntimeError(f"Get market clock failed: {e}")
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest quote for a symbol
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary with latest quote data
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self._data_client.get_stock_latest_quote(request)
            
            if symbol in quotes:
                quote = quotes[symbol]
                return {
                    'symbol': symbol,
                    'bid_price': float(quote.bid_price),
                    'bid_size': int(quote.bid_size),
                    'ask_price': float(quote.ask_price),
                    'ask_size': int(quote.ask_size),
                    'timestamp': quote.timestamp
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest quote for {symbol}: {e}")
            return None
    
    def get_asset_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get asset information
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary with asset details
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        try:
            asset = self._trading_client.get_asset(symbol)
            
            return {
                'symbol': asset.symbol,
                'name': asset.name if hasattr(asset, 'name') else asset.symbol,
                'exchange': asset.exchange,
                'asset_class': asset.asset_class,
                'tradable': asset.tradable,
                'marginable': asset.marginable,
                'shortable': asset.shortable,
                'fractionable': asset.fractionable if hasattr(asset, 'fractionable') else False
            }
            
        except Exception as e:
            logger.error(f"Failed to get asset info for {symbol}: {e}")
            return None
    
    def get_historical_bars(
        self,
        symbol: str,
        timeframe: str = "1Min",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical OHLCV bar data for a symbol.
        
        This is essential for:
        - Backtesting strategies
        - Calculating technical indicators
        - Analyzing historical patterns
        - Strategy validation
        
        Args:
            symbol: Stock symbol (e.g., "SPY", "AAPL")
            timeframe: Bar timeframe. Supported values:
                - "1Min", "5Min", "15Min", "30Min" - Minute bars
                - "1Hour", "2Hour", "4Hour" - Hour bars
                - "1Day" - Daily bars
            start: Start datetime (default: 7 days ago for intraday, 1 year for daily)
            end: End datetime (default: now)
            limit: Maximum number of bars to return (max 10,000)
        
        Returns:
            List of bar dictionaries, each containing:
            - timestamp: Bar start time (datetime)
            - open: Opening price (float)
            - high: Highest price (float)
            - low: Lowest price (float)
            - close: Closing price (float)
            - volume: Total volume (int)
            - vwap: Volume-weighted average price (float)
            - trade_count: Number of trades (int, if available)
        
        Example:
            # Get last 100 1-minute bars
            bars = adapter.get_historical_bars("SPY", "1Min", limit=100)
            
            # Get specific date range
            start = datetime(2025, 10, 1)
            end = datetime(2025, 10, 13)
            bars = adapter.get_historical_bars("AAPL", "1Day", start=start, end=end)
            
            # Calculate returns
            if len(bars) >= 2:
                returns = (bars[-1]['close'] - bars[0]['open']) / bars[0]['open']
                print(f"Return: {returns * 100:.2f}%")
        
        Note:
            - Alpaca provides free historical data for all US equities
            - Intraday data available for ~1 year back
            - Daily data available for ~5+ years back
            - Rate limit: ~200 requests/minute
        """
        if not self.is_connected():
            logger.error("Not connected to broker")
            return []
        
        try:
            # Map timeframe string to Alpaca TimeFrame object
            timeframe_map = {
                # Minute bars
                "1Min": TimeFrame(1, TimeFrameUnit.Minute),
                "5Min": TimeFrame(5, TimeFrameUnit.Minute),
                "15Min": TimeFrame(15, TimeFrameUnit.Minute),
                "30Min": TimeFrame(30, TimeFrameUnit.Minute),
                
                # Hour bars
                "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
                "2Hour": TimeFrame(2, TimeFrameUnit.Hour),
                "4Hour": TimeFrame(4, TimeFrameUnit.Hour),
                
                # Daily bars
                "1Day": TimeFrame(1, TimeFrameUnit.Day),
            }
            
            if timeframe not in timeframe_map:
                logger.error(f"Invalid timeframe: {timeframe}. Supported: {list(timeframe_map.keys())}")
                return []
            
            tf = timeframe_map[timeframe]
            
            # Set default date ranges based on timeframe
            if start is None:
                if "Day" in timeframe:
                    # Daily data: default to 1 year back
                    start = datetime.now() - timedelta(days=365)
                else:
                    # Intraday data: default to 7 days back
                    start = datetime.now() - timedelta(days=7)
            
            if end is None:
                end = datetime.now()
            
            # Validate date range
            if start >= end:
                logger.error(f"Invalid date range: start ({start}) >= end ({end})")
                return []
            
            # Build request
            request_params = {
                'symbol_or_symbols': symbol,
                'timeframe': tf,
                'start': start,
                'end': end
            }
            
            if limit is not None:
                request_params['limit'] = min(limit, 10000)  # Alpaca max is 10,000
            
            request = StockBarsRequest(**request_params)
            
            # Fetch bars from Alpaca
            logger.info(f"Fetching {timeframe} bars for {symbol} from {start} to {end}")
            bars_response = self._data_client.get_stock_bars(request)
            
            # Check if symbol exists in response
            if symbol not in bars_response:
                logger.warning(f"No bar data returned for {symbol}")
                return []
            
            # Convert to list of dictionaries
            bars = []
            for bar in bars_response[symbol]:
                bar_dict = {
                    'timestamp': bar.timestamp,
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': int(bar.volume),
                    'vwap': float(bar.vwap) if bar.vwap else None,
                    'trade_count': int(bar.trade_count) if hasattr(bar, 'trade_count') else None
                }
                bars.append(bar_dict)
            
            logger.info(f"✅ Retrieved {len(bars)} {timeframe} bars for {symbol}")
            
            # Log sample data for debugging
            if bars:
                logger.debug(f"First bar: {bars[0]['timestamp']} OHLC: {bars[0]['open']:.2f}/{bars[0]['high']:.2f}/{bars[0]['low']:.2f}/{bars[0]['close']:.2f}")
                logger.debug(f"Last bar: {bars[-1]['timestamp']} OHLC: {bars[-1]['open']:.2f}/{bars[-1]['high']:.2f}/{bars[-1]['low']:.2f}/{bars[-1]['close']:.2f}")
            
            return bars
            
        except Exception as e:
            logger.error(f"Failed to get historical bars for {symbol}: {e}")
            logger.exception("Full traceback:")
            return []
    
    # ========================================================================
    # ENHANCED FEATURES - Advanced Order Types
    # ========================================================================
    
    def submit_stop_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        stop_price: float,
        time_in_force: str = "day"
    ) -> SystemOrder:
        """
        Submit stop order
        
        Args:
            symbol: Stock symbol
            qty: Quantity (positive integer)
            side: "buy" or "sell"
            stop_price: Stop trigger price
            time_in_force: "day", "gtc", "ioc", "fok"
        
        Returns:
            Order object with order details
        
        Raises:
            ValueError: If parameters invalid
            RuntimeError: If order submission fails
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        # Validate parameters
        if qty <= 0:
            raise ValueError(f"Quantity must be positive: {qty}")
        
        if side.lower() not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {side}")
        
        if stop_price <= 0:
            raise ValueError(f"Stop price must be positive: {stop_price}")
        
        try:
            from alpaca.trading.requests import StopOrderRequest
            
            # Convert to Alpaca enums
            alpaca_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            alpaca_tif = self._convert_tif_to_alpaca(time_in_force)
            
            # Create stop order request
            order_request = StopOrderRequest(
                symbol=symbol,
                qty=qty,
                side=alpaca_side,
                time_in_force=alpaca_tif,
                stop_price=stop_price
            )
            
            # Submit order
            alpaca_order = self._trading_client.submit_order(order_request)
            
            # Convert to system Order
            order = self._convert_alpaca_order(alpaca_order)
            
            logger.info(f"✅ Stop order submitted: {side.upper()} {qty} {symbol} "
                       f"@ stop ${stop_price} (order_id={order.order_id})")
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to submit stop order: {e}")
            raise RuntimeError(f"Stop order submission failed: {e}")
    
    def submit_stop_limit_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        stop_price: float,
        limit_price: float,
        time_in_force: str = "day"
    ) -> SystemOrder:
        """
        Submit stop-limit order
        
        Args:
            symbol: Stock symbol
            qty: Quantity (positive integer)
            side: "buy" or "sell"
            stop_price: Stop trigger price
            limit_price: Limit price after trigger
            time_in_force: "day", "gtc", "ioc", "fok"
        
        Returns:
            Order object with order details
        
        Raises:
            ValueError: If parameters invalid
            RuntimeError: If order submission fails
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        
        # Validate parameters
        if qty <= 0:
            raise ValueError(f"Quantity must be positive: {qty}")
        
        if side.lower() not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {side}")
        
        if stop_price <= 0:
            raise ValueError(f"Stop price must be positive: {stop_price}")
        
        if limit_price <= 0:
            raise ValueError(f"Limit price must be positive: {limit_price}")
        
        try:
            from alpaca.trading.requests import StopLimitOrderRequest
            
            # Convert to Alpaca enums
            alpaca_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            alpaca_tif = self._convert_tif_to_alpaca(time_in_force)
            
            # Create stop-limit order request
            order_request = StopLimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=alpaca_side,
                time_in_force=alpaca_tif,
                stop_price=stop_price,
                limit_price=limit_price
            )
            
            # Submit order
            alpaca_order = self._trading_client.submit_order(order_request)
            
            # Convert to system Order
            order = self._convert_alpaca_order(alpaca_order)
            
            logger.info(f"✅ Stop-limit order submitted: {side.upper()} {qty} {symbol} "
                       f"@ stop ${stop_price}, limit ${limit_price} (order_id={order.order_id})")
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to submit stop-limit order: {e}")
            raise RuntimeError(f"Stop-limit order submission failed: {e}")
    
    # ========================================================================
    # ENHANCED FEATURES - Order Validation & Risk Checks
    # ========================================================================
    
    def validate_order_params(
        self,
        symbol: str,
        qty: int,
        price: Optional[float] = None,
        side: str = "buy"
    ) -> tuple[bool, str]:
        """
        Validate order parameters before submission
        
        Args:
            symbol: Stock symbol
            qty: Quantity
            price: Order price (if applicable)
            side: "buy" or "sell"
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check connection
            if not self.is_connected():
                return False, "Not connected to broker"
            
            # Validate quantity
            if qty <= 0:
                return False, f"Invalid quantity: {qty}"
            
            # Validate side
            if side.lower() not in ["buy", "sell"]:
                return False, f"Invalid side: {side}"
            
            # Validate price if provided
            if price is not None and price <= 0:
                return False, f"Invalid price: {price}"
            
            # Check if asset exists and is tradable
            asset_info = self.get_asset_info(symbol)
            if not asset_info:
                return False, f"Asset not found: {symbol}"
            
            if not asset_info.get('tradable', False):
                return False, f"Asset not tradable: {symbol}"
            
            # Check buying power for buy orders
            if side.lower() == "buy":
                account = self.get_account_info()
                estimated_cost = qty * (price if price else 0)
                
                if estimated_cost > 0 and estimated_cost > account.buying_power:
                    return False, f"Insufficient buying power: ${account.buying_power:,.2f} < ${estimated_cost:,.2f}"
            
            return True, "Valid"
            
        except Exception as e:
            logger.error(f"Order validation failed: {e}")
            return False, f"Validation error: {str(e)}"
    
    def check_buying_power(self, required_amount: float) -> bool:
        """
        Check if account has sufficient buying power
        
        Args:
            required_amount: Required buying power
        
        Returns:
            True if sufficient buying power available
        """
        try:
            account = self.get_account_info()
            return account.buying_power >= required_amount
            
        except Exception as e:
            logger.error(f"Failed to check buying power: {e}")
            return False
    
    # ========================================================================
    # ENHANCED FEATURES - Connection Health & Monitoring
    # ========================================================================
    
    def check_connection_health(self) -> Dict[str, Any]:
        """
        Check connection health and get status
        
        Returns:
            Dictionary with health status information
        """
        health = {
            'connected': self._connected,
            'trading_client_active': self._trading_client is not None,
            'data_client_active': self._data_client is not None,
            'timestamp': datetime.now(),
            'errors': []
        }
        
        if not self.is_connected():
            health['errors'].append("Not connected")
            health['status'] = 'ERROR'
            return health
        
        # Test trading client
        try:
            self._trading_client.get_account()
            health['trading_client_healthy'] = True
        except Exception as e:
            health['trading_client_healthy'] = False
            health['errors'].append(f"Trading client error: {str(e)}")
        
        # Test data client
        try:
            # Simple asset lookup as health check
            self._trading_client.get_asset('SPY')
            health['data_client_healthy'] = True
        except Exception as e:
            health['data_client_healthy'] = False
            health['errors'].append(f"Data client error: {str(e)}")
        
        # Determine overall status
        if health['trading_client_healthy'] and health['data_client_healthy']:
            health['status'] = 'HEALTHY'
        elif health['trading_client_healthy']:
            health['status'] = 'DEGRADED'
        else:
            health['status'] = 'ERROR'
        
        return health
    
    def get_account(self):
        """Get raw Alpaca account object (for compatibility)"""
        if not self.is_connected():
            raise RuntimeError("Not connected to Alpaca")
        return self._trading_client.get_account()


if __name__ == "__main__":
    # Test module
    print("✅ Alpaca adapter module loaded")
    print("Usage: adapter = AlpacaAdapter(config)")
