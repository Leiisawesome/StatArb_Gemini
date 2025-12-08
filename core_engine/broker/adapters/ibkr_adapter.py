"""
Interactive Brokers Adapter
Production-ready broker integration using IB TWS API

This adapter connects to Interactive Brokers via TWS (Trader Workstation) or IB Gateway
and provides full trading functionality for algorithmic trading.
"""

import logging
import threading
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order as IBOrder
from ibapi.common import TickerId, OrderId

from core_engine.broker.adapters.base_adapter import BaseBrokerAdapter
from core_engine.type_definitions.broker_types import (
    Order, OrderSide, OrderType, OrderStatus, Position, AccountInfo
)

logger = logging.getLogger(__name__)


class IBKRWrapper(EWrapper):
    """
    Callback handler for IB API events

    This class receives all callbacks from the IB API and stores data
    for retrieval by the IBKRClient/IBKRAdapter.
    """

    def __init__(self):
        super().__init__()
        self.next_order_id = None
        self.positions = {}
        self.account_values = {}
        self.managed_accounts = []
        self.quotes = {}
        self.orders = {}
        self.errors = []
        self.connected = False

        # Historical data storage
        self.historical_data = {}  # req_id -> list of bars
        self.historical_data_completed = set()  # set of completed req_ids

        # Event for waiting on connection
        self.connection_ready = threading.Event()

    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        """Handle error messages"""
        # Some error codes are informational, not actual errors
        if errorCode in [2104, 2106, 2158]:  # Market data farm connection, HMDS connection
            logger.info(f"IB Info [{errorCode}]: {errorString}")
        elif errorCode in [2108, 2119]:  # Market data farm disconnection
            logger.warning(f"IB Warning [{errorCode}]: {errorString}")
        else:
            error_msg = f"IB Error [{errorCode}] reqId={reqId}: {errorString}"
            logger.error(error_msg)
            self.errors.append({
                'req_id': reqId,
                'code': errorCode,
                'message': errorString,
                'timestamp': datetime.now()
            })

    def nextValidId(self, orderId: OrderId):
        """Callback when connection is established and next valid order ID is received"""
        logger.info(f"Connected - Next valid order ID: {orderId}")
        self.next_order_id = orderId
        self.connected = True
        self.connection_ready.set()

    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Callback for position updates"""
        logger.debug(f"Position update: {contract.symbol} qty={position} avgCost={avgCost}")
        self.positions[contract.symbol] = {
            'symbol': contract.symbol,
            'position': position,
            'avg_cost': avgCost,
            'account': account,
            'contract': contract,
            'timestamp': datetime.now()
        }

    def positionEnd(self):
        """Callback when all positions have been received"""
        logger.debug("Position updates complete")

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Callback for account summary data"""
        logger.debug(f"Account summary: {tag}={value} {currency}")
        self.account_values[tag] = {
            'value': value,
            'currency': currency,
            'account': account
        }

    def accountSummaryEnd(self, reqId: int):
        """Callback when account summary is complete"""
        logger.debug("Account summary complete")

    def managedAccounts(self, accountsList: str):
        """Callback for managed accounts list"""
        logger.info(f"📊 Managed accounts: {accountsList}")
        self.managed_accounts = accountsList.split(',')

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        """Callback for account value updates"""
        self.account_values[key] = {
            'value': val,
            'currency': currency,
            'account': accountName
        }

    def updateAccountTime(self, timeStamp: str):
        """Callback for account time updates"""
        logger.debug(f"Account time: {timeStamp}")

    def tickPrice(self, reqId: TickerId, tickType: int, price: float, attrib):
        """Callback for price tick updates"""
        if reqId not in self.quotes:
            self.quotes[reqId] = {'timestamp': datetime.now()}

        # TickType: 1=BID, 2=ASK, 4=LAST, 6=HIGH, 7=LOW, 9=CLOSE
        if tickType == 1:
            self.quotes[reqId]['bid_price'] = price
        elif tickType == 2:
            self.quotes[reqId]['ask_price'] = price
        elif tickType == 4:
            self.quotes[reqId]['last_price'] = price
        elif tickType == 6:
            self.quotes[reqId]['high'] = price
        elif tickType == 7:
            self.quotes[reqId]['low'] = price
        elif tickType == 9:
            self.quotes[reqId]['close'] = price

    def tickSize(self, reqId: TickerId, tickType: int, size: int):
        """Callback for size tick updates"""
        if reqId not in self.quotes:
            self.quotes[reqId] = {'timestamp': datetime.now()}

        # TickType: 0=BID_SIZE, 3=ASK_SIZE, 5=LAST_SIZE, 8=VOLUME
        if tickType == 0:
            self.quotes[reqId]['bid_size'] = size
        elif tickType == 3:
            self.quotes[reqId]['ask_size'] = size
        elif tickType == 5:
            self.quotes[reqId]['last_size'] = size
        elif tickType == 8:
            self.quotes[reqId]['volume'] = size

    def orderStatus(self, orderId: OrderId, status: str, filled: float,
                   remaining: float, avgFillPrice: float, permId: int,
                   parentId: int, lastFillPrice: float, clientId: int,
                   whyHeld: str, mktCapPrice: float):
        """Callback for order status updates"""
        logger.info(f"Order {orderId} status: {status}, filled={filled}, remaining={remaining}")

        if orderId not in self.orders:
            self.orders[orderId] = {}

        self.orders[orderId].update({
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avg_fill_price': avgFillPrice,
            'last_fill_price': lastFillPrice,
            'timestamp': datetime.now()
        })

    def openOrder(self, orderId: OrderId, contract: Contract, order: IBOrder, orderState):
        """Callback for open order data"""
        logger.debug(f"Open order: {orderId} {order.action} {order.totalQuantity} {contract.symbol}")

        if orderId not in self.orders:
            self.orders[orderId] = {}

        self.orders[orderId].update({
            'order_id': orderId,
            'symbol': contract.symbol,
            'action': order.action,
            'quantity': order.totalQuantity,
            'order_type': order.orderType,
            'limit_price': order.lmtPrice if order.lmtPrice != 0 else None,
            'stop_price': order.auxPrice if order.auxPrice != 0 else None,
            'contract': contract,
            'order': order,
            'state': orderState
        })

    def contractDetails(self, reqId: int, contractDetails):
        """Callback for contract details"""
        logger.debug(f"Contract details received for reqId {reqId}")

    def historicalData(self, reqId: int, bar):
        """Callback for historical data bars"""
        logger.debug(f"Historical data bar received for reqId {reqId}: {bar.date}")

        if reqId not in self.historical_data:
            self.historical_data[reqId] = []

        self.historical_data[reqId].append(bar)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Callback when historical data request is complete"""
        logger.debug(f"Historical data complete for reqId {reqId}")
        self.historical_data_completed.add(reqId)

    def historicalDataUpdate(self, reqId: int, bar):
        """Callback for real-time historical data updates (not used)"""


class IBKRClient(EClient):
    """IB API client - handles communication with TWS/Gateway"""

    def __init__(self, wrapper):
        super().__init__(wrapper)


class IBKRAdapter(BaseBrokerAdapter):
    """
    Interactive Brokers adapter for live trading

    Features:
    - Real-time market data
    - Order management (market, limit, stop, stop-limit)
    - Position tracking
    - Account monitoring
    - Paper and live trading support
    - Multiple asset classes (stocks, futures, options, forex)

    Connection:
    - Connects to TWS (Trader Workstation) or IB Gateway
    - Paper trading: port 7497 (TWS) or 4002 (Gateway)
    - Live trading: port 7496 (TWS) or 4001 (Gateway)
    """

    def __init__(self, config):
        """
        Initialize IBKR adapter

        Args:
            config: InteractiveBrokersConfig object with connection settings
        """
        self.config = config
        self.wrapper = IBKRWrapper()
        self.client = IBKRClient(self.wrapper)
        self._connected = False
        self._thread = None
        self._next_req_id = 1
        self._req_id_lock = threading.Lock()

        logger.info(
            f"Initialized IBKR adapter "
            f"(host={config.host}, port={config.port}, "
            f"client_id={config.client_id}, paper_trading={config.paper_trading})"
        )

    def _get_next_req_id(self) -> int:
        """Thread-safe request ID generation"""
        with self._req_id_lock:
            req_id = self._next_req_id
            self._next_req_id += 1
            return req_id

    def _run_loop(self):
        """Run IB client message loop in background thread"""
        try:
            self.client.run()
        except Exception as e:
            logger.error(f"IB client loop error: {e}")
            self._connected = False

    # ==================== Connection Management ====================

    def connect(self) -> bool:
        """
        Connect to IB Gateway/TWS

        Returns:
            bool: True if connection successful
        """
        try:
            logger.info(
                f"Connecting to IBKR at {self.config.host}:{self.config.port} "
                f"(client_id={self.config.client_id})..."
            )

            # Connect to IB
            self.client.connect(
                self.config.host,
                self.config.port,
                self.config.client_id
            )

            # Start message processing thread
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

            # Wait for connection confirmation
            if not self.wrapper.connection_ready.wait(timeout=10):
                raise TimeoutError("Connection timeout - IB Gateway/TWS not responding")

            self._connected = True

            # Configure market data type
            # 1 = Real-time (requires subscription)
            # 2 = Frozen (last available)
            # 3 = Delayed (15-20 minutes, free)
            # 4 = Delayed frozen
            if self.config.paper_trading:
                # Check if user has market data subscription via env variable
                import os
                has_subscription = os.getenv('IB_HAS_MARKET_DATA_SUBSCRIPTION', 'false').lower() == 'true'

                if has_subscription:
                    self.client.reqMarketDataType(1)  # Real-time data
                    logger.info("📊 Enabled real-time market data (subscription active)")
                else:
                    self.client.reqMarketDataType(3)  # Delayed data
                    logger.info("📊 Enabled delayed market data (15-20 min delay)")
                    logger.warning("⚠️  For real-time quotes, subscribe to market data and set IB_HAS_MARKET_DATA_SUBSCRIPTION=true")

            # Request initial data
            self.client.reqAccountSummary(9001, "All", "$LEDGER")
            self.client.reqPositions()

            # Give time for initial data
            time.sleep(1)

            logger.info(
                f"✅ Connected to IBKR "
                f"(next_order_id={self.wrapper.next_order_id})"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from IB"""
        if self._connected:
            try:
                self.client.disconnect()
                self._connected = False
                self.wrapper.connected = False
                logger.info("✅ Disconnected from IBKR")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")

    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self.client.isConnected() and self.wrapper.connected

    def check_connection_health(self) -> Dict[str, Any]:
        """Check connection health"""
        connected = self.is_connected()
        return {
            'status': 'healthy' if connected else 'disconnected',
            'connected': connected,
            'broker': 'Interactive Brokers',
            'host': self.config.host,
            'port': self.config.port,
            'client_id': self.config.client_id,
            'paper_trading': self.config.paper_trading,
            'next_order_id': self.wrapper.next_order_id,
            'errors': len(self.wrapper.errors),
            'last_error': self.wrapper.errors[-1] if self.wrapper.errors else None,
            'timestamp': datetime.now()
        }

    def reconnect(self, max_attempts: int = 3, delay: float = 5.0) -> bool:
        """
        Attempt to reconnect to IBKR with retry logic.

        Args:
            max_attempts: Maximum number of reconnection attempts
            delay: Delay between attempts in seconds

        Returns:
            bool: True if reconnection successful
        """
        logger.info(f"🔄 Attempting to reconnect to IBKR (max {max_attempts} attempts)...")

        for attempt in range(max_attempts):
            try:
                # Disconnect first if still connected
                if self.is_connected():
                    self.disconnect()
                    time.sleep(1)

                # Clear any error state
                self.wrapper.errors.clear()
                self.wrapper.connection_ready.clear()

                # Attempt reconnection
                logger.info(f"Reconnection attempt {attempt + 1}/{max_attempts}")
                if self.connect():
                    logger.info("✅ Reconnection successful")
                    return True

            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")

            if attempt < max_attempts - 1:
                logger.info(f"⏳ Waiting {delay}s before next attempt...")
                time.sleep(delay)

        logger.error(f"❌ Failed to reconnect after {max_attempts} attempts")
        return False

    def handle_connection_error(self, error: Exception) -> bool:
        """
        Handle connection errors with appropriate recovery actions.

        Args:
            error: The connection error that occurred

        Returns:
            bool: True if error was handled successfully
        """
        error_msg = str(error).lower()

        # Categorize error types
        if any(keyword in error_msg for keyword in ['timeout', 'connection refused', 'connection reset']):
            logger.warning(f"🔌 Connection error detected: {error}")
            return self.reconnect(max_attempts=3, delay=3.0)

        elif any(keyword in error_msg for keyword in ['market data farm', 'subscription']):
            logger.warning(f"📊 Market data error: {error}")
            # Try to switch to delayed data
            try:
                self.client.reqMarketDataType(3)  # Delayed data
                logger.info("📊 Switched to delayed market data")
                return True
            except Exception as e:
                logger.error(f"Failed to switch market data type: {e}")
                return False

        elif 'next order id' in error_msg or 'duplicate order' in error_msg:
            logger.warning(f"📋 Order ID error: {error}")
            # Request fresh order ID
            try:
                self.client.reqIds(-1)
                time.sleep(1)
                logger.info("📋 Requested fresh order ID")
                return True
            except Exception as e:
                logger.error(f"Failed to request order ID: {e}")
                return False

        else:
            logger.error(f"❓ Unhandled connection error: {error}")
            return False

    def monitor_connection(self, interval: float = 30.0) -> None:
        """
        Monitor connection health and attempt recovery if needed.
        This method should be run in a separate thread.

        Args:
            interval: Monitoring interval in seconds
        """
        logger.info(f"👁️  Starting connection monitor (interval: {interval}s)")

        while self._connected:
            try:
                health = self.check_connection_health()

                if not health['connected']:
                    logger.warning("🔌 Connection lost, attempting recovery...")
                    if not self.reconnect(max_attempts=3, delay=5.0):
                        logger.error("❌ Connection recovery failed")
                        break

                # Check for recent errors
                if health['errors'] > 0:
                    last_error = health['last_error']
                    if last_error and self.handle_connection_error(Exception(last_error)):
                        logger.info("✅ Error handled successfully")
                        # Clear handled errors
                        self.wrapper.errors.clear()

                time.sleep(interval)

            except Exception as e:
                logger.error(f"Connection monitor error: {e}")
                time.sleep(interval)

        logger.info("👁️  Connection monitor stopped")

    # ==================== Contract Creation ====================

    def _create_stock_contract(self, symbol: str) -> Contract:
        """
        Create IB contract for US stocks

        Args:
            symbol: Stock ticker symbol

        Returns:
            Contract: IB contract object
        """
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.primaryExchange = "ISLAND"  # NASDAQ
        return contract

    # ==================== Market Data ====================

    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest quote for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            dict: Quote data or None if not available
        """
        try:
            contract = self._create_stock_contract(symbol)
            req_id = self._get_next_req_id()

            # Request market data
            self.client.reqMktData(req_id, contract, "", False, False, [])

            # Wait for quote data
            timeout = 5
            start_time = time.time()
            while req_id not in self.wrapper.quotes:
                if time.time() - start_time > timeout:
                    logger.warning(f"Quote timeout for {symbol}")
                    self.client.cancelMktData(req_id)
                    return None
                time.sleep(0.05)

            # Wait a bit more for complete quote
            time.sleep(0.2)

            # Cancel market data
            self.client.cancelMktData(req_id)

            quote_data = self.wrapper.quotes.get(req_id, {})

            return {
                'symbol': symbol,
                'bid_price': quote_data.get('bid_price', 0),
                'ask_price': quote_data.get('ask_price', 0),
                'last_price': quote_data.get('last_price', 0),
                'bid_size': quote_data.get('bid_size', 0),
                'ask_size': quote_data.get('ask_size', 0),
                'high': quote_data.get('high'),
                'low': quote_data.get('low'),
                'close': quote_data.get('close'),
                'volume': quote_data.get('volume'),
                'timestamp': quote_data.get('timestamp', datetime.now())
            }

        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Alias for get_latest_quote() - simpler method name for common use

        Args:
            symbol: Stock symbol

        Returns:
            dict: Quote data with bid, ask, last prices and sizes
                  Returns None if not available

        Example:
            >>> quote = adapter.get_quote("SPY")
            >>> if quote and quote['last_price'] > 0:
            >>>     print(f"SPY last price: ${quote['last_price']:.2f}")
        """
        return self.get_latest_quote(symbol)

    def is_market_open(self) -> bool:
        """
        Check if market is currently open

        Uses US Eastern Time for accurate market hours check.
        Market hours: Monday-Friday, 9:30 AM - 4:00 PM ET

        Note: This is a simplified check. For production, you'd want to
        check the actual market hours from IB or use a market calendar
        to handle holidays.

        Returns:
            bool: True if market is open
        """
        # Get current time in US Eastern Time
        et_tz = ZoneInfo("America/New_York")
        now_et = datetime.now(et_tz)

        # Check if it's a weekday (Monday=0, Sunday=6)
        if now_et.weekday() >= 5:  # Saturday or Sunday
            return False

        hour = now_et.hour
        minute = now_et.minute

        # Market hours: 9:30 AM - 4:00 PM ET
        market_open = (hour == 9 and minute >= 30) or (10 <= hour < 16)

        return market_open

    # ==================== Order Management ====================

    def _convert_order_status(self, ib_status: str) -> OrderStatus:
        """Convert IB order status to our OrderStatus enum"""
        status_map = {
            'PendingSubmit': OrderStatus.PENDING,
            'PendingCancel': OrderStatus.PENDING,
            'PreSubmitted': OrderStatus.SUBMITTED,
            'Submitted': OrderStatus.SUBMITTED,
            'Cancelled': OrderStatus.CANCELLED,
            'Filled': OrderStatus.FILLED,
            'Inactive': OrderStatus.REJECTED,
        }
        return status_map.get(ib_status, OrderStatus.PENDING)

    def submit_market_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide
    ) -> Order:
        """Submit market order"""
        try:
            # Validate parameters
            is_valid, error_msg = self.validate_order_params(
                symbol, quantity, side, OrderType.MARKET
            )
            if not is_valid:
                raise ValueError(f"Invalid order parameters: {error_msg}")

            # Create contract
            contract = self._create_stock_contract(symbol)

            # Create order
            ib_order = IBOrder()
            ib_order.action = "BUY" if side == OrderSide.BUY else "SELL"
            ib_order.orderType = "MKT"
            ib_order.totalQuantity = quantity
            ib_order.transmit = True
            ib_order.eTradeOnly = False  # Explicitly disable E*TRADE only
            ib_order.firmQuoteOnly = False  # Explicitly disable firm quote only
            ib_order.outsideRth = False  # Orders only during regular trading hours

            # Get order ID (must be connected to have valid next_order_id)
            if self.wrapper.next_order_id is None:
                raise RuntimeError("Not connected to IBKR - cannot get next order ID")
            order_id = self.wrapper.next_order_id
            self.wrapper.next_order_id += 1

            # Submit order
            self.client.placeOrder(order_id, contract, ib_order)

            # Create our Order object
            order = Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=OrderType.MARKET,
                order_id=str(order_id),
                status=OrderStatus.SUBMITTED,
                timestamp=datetime.now(),
                metadata={'broker': 'IBKR'}
            )

            logger.info(
                f"✅ Market order submitted: {side.value} {quantity} {symbol} "
                f"(order_id={order_id})"
            )

            return order

        except Exception as e:
            logger.error(f"Failed to submit market order: {e}")
            raise

    def submit_limit_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        limit_price: float
    ) -> Order:
        """Submit limit order"""
        try:
            # Validate parameters
            is_valid, error_msg = self.validate_order_params(
                symbol, quantity, side, OrderType.LIMIT, limit_price=limit_price
            )
            if not is_valid:
                raise ValueError(f"Invalid order parameters: {error_msg}")

            # Create contract
            contract = self._create_stock_contract(symbol)

            # Create order
            ib_order = IBOrder()
            ib_order.action = "BUY" if side == OrderSide.BUY else "SELL"
            ib_order.orderType = "LMT"
            ib_order.totalQuantity = quantity
            ib_order.lmtPrice = round(limit_price, 2)
            ib_order.transmit = True

            # Get order ID (must be connected to have valid next_order_id)
            if self.wrapper.next_order_id is None:
                raise RuntimeError("Not connected to IBKR - cannot get next order ID")
            order_id = self.wrapper.next_order_id
            self.wrapper.next_order_id += 1

            # Submit order
            self.client.placeOrder(order_id, contract, ib_order)

            # Create our Order object
            order = Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=OrderType.LIMIT,
                price=limit_price,
                order_id=str(order_id),
                status=OrderStatus.SUBMITTED,
                timestamp=datetime.now(),
                metadata={'broker': 'IBKR'}
            )

            logger.info(
                f"✅ Limit order submitted: {side.value} {quantity} {symbol} "
                f"@ ${limit_price:.2f} (order_id={order_id})"
            )

            return order

        except Exception as e:
            logger.error(f"Failed to submit limit order: {e}")
            raise

    def submit_stop_order(
        self,
        symbol: str,
        quantity: float = None,
        qty: float = None,
        side: OrderSide = None,
        stop_price: float = None,
        time_in_force: str = "day"
    ) -> Order:
        """
        Submit stop order (enhanced to accept qty parameter for compatibility)

        Args:
            symbol: Stock symbol
            quantity: Number of shares (preferred)
            qty: Number of shares (alias for quantity)
            side: OrderSide.BUY or OrderSide.SELL, or string "buy"/"sell"
            stop_price: Stop price that triggers the order
            time_in_force: Time in force ('day', 'gtc', etc.)

        Returns:
            Order: Order object with order details and ID
        """
        # Handle qty parameter for compatibility
        if qty is not None and quantity is None:
            quantity = qty

        if quantity is None:
            raise ValueError("Either 'quantity' or 'qty' parameter must be provided")

        # Handle string side parameter
        if isinstance(side, str):
            side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        # Call the original implementation
        return self._submit_stop_order_impl(symbol, quantity, side, stop_price)

    def _submit_stop_order_impl(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        stop_price: float
    ) -> Order:
        """Original submit_stop_order implementation"""
        try:
            # Validate parameters
            is_valid, error_msg = self.validate_order_params(
                symbol, quantity, side, OrderType.STOP, stop_price=stop_price
            )
            if not is_valid:
                raise ValueError(f"Invalid order parameters: {error_msg}")

            # Create contract
            contract = self._create_stock_contract(symbol)

            # Create order
            ib_order = IBOrder()
            ib_order.action = "BUY" if side == OrderSide.BUY else "SELL"
            ib_order.orderType = "STP"
            ib_order.totalQuantity = quantity
            ib_order.auxPrice = round(stop_price, 2)
            ib_order.transmit = True

            # Get order ID (must be connected to have valid next_order_id)
            if self.wrapper.next_order_id is None:
                raise RuntimeError("Not connected to IBKR - cannot get next order ID")
            order_id = self.wrapper.next_order_id
            self.wrapper.next_order_id += 1

            # Submit order
            self.client.placeOrder(order_id, contract, ib_order)

            # Create our Order object
            order = Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=OrderType.STOP,
                stop_price=stop_price,
                order_id=str(order_id),
                status=OrderStatus.SUBMITTED,
                timestamp=datetime.now(),
                metadata={'broker': 'IBKR'}
            )

            logger.info(
                f"✅ Stop order submitted: {side.value} {quantity} {symbol} "
                f"@ stop ${stop_price:.2f} (order_id={order_id})"
            )

            return order

        except Exception as e:
            logger.error(f"Failed to submit stop order: {e}")
            raise

    def submit_stop_limit_order(
        self,
        symbol: str,
        quantity: float = None,
        qty: float = None,
        side: OrderSide = None,
        stop_price: float = None,
        limit_price: float = None,
        time_in_force: str = "day"
    ) -> Order:
        """
        Submit stop-limit order (enhanced to accept qty parameter for compatibility)

        Args:
            symbol: Stock symbol
            quantity: Number of shares (preferred)
            qty: Number of shares (alias for quantity)
            side: OrderSide.BUY or OrderSide.SELL, or string "buy"/"sell"
            stop_price: Stop price that triggers the order
            limit_price: Limit price once triggered
            time_in_force: Time in force ('day', 'gtc', etc.)

        Returns:
            Order: Order object with order details and ID
        """
        # Handle qty parameter for compatibility
        if qty is not None and quantity is None:
            quantity = qty

        if quantity is None:
            raise ValueError("Either 'quantity' or 'qty' parameter must be provided")

        # Handle string side parameter
        if isinstance(side, str):
            side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        # Call the original implementation
        return self._submit_stop_limit_order_impl(symbol, quantity, side, stop_price, limit_price)

    def _submit_stop_limit_order_impl(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        stop_price: float,
        limit_price: float
    ) -> Order:
        """Original submit_stop_limit_order implementation"""
        try:
            # Validate parameters
            is_valid, error_msg = self.validate_order_params(
                symbol, quantity, side, OrderType.STOP_LIMIT,
                limit_price=limit_price, stop_price=stop_price
            )
            if not is_valid:
                raise ValueError(f"Invalid order parameters: {error_msg}")

            # Create contract
            contract = self._create_stock_contract(symbol)

            # Create order
            ib_order = IBOrder()
            ib_order.action = "BUY" if side == OrderSide.BUY else "SELL"
            ib_order.orderType = "STP LMT"
            ib_order.totalQuantity = quantity
            ib_order.lmtPrice = round(limit_price, 2)
            ib_order.auxPrice = round(stop_price, 2)
            ib_order.transmit = True

            # Get order ID (must be connected to have valid next_order_id)
            if self.wrapper.next_order_id is None:
                raise RuntimeError("Not connected to IBKR - cannot get next order ID")
            order_id = self.wrapper.next_order_id
            self.wrapper.next_order_id += 1

            # Submit order
            self.client.placeOrder(order_id, contract, ib_order)

            # Create our Order object
            order = Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=OrderType.STOP_LIMIT,
                price=limit_price,
                stop_price=stop_price,
                order_id=str(order_id),
                status=OrderStatus.SUBMITTED,
                timestamp=datetime.now(),
                metadata={'broker': 'IBKR'}
            )

            logger.info(
                f"✅ Stop-limit order submitted: {side.value} {quantity} {symbol} "
                f"@ stop ${stop_price:.2f}, limit ${limit_price:.2f} (order_id={order_id})"
            )

            return order

        except Exception as e:
            logger.error(f"Failed to submit stop-limit order: {e}")
            raise

    def submit_bracket_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        entry_price: Optional[float] = None,
        profit_target: Optional[float] = None,
        stop_loss: Optional[float] = None,
        transmit: bool = True
    ) -> tuple[Order, Order, Order]:
        """
        Submit a bracket order (parent + profit taker + stop loss).
        Bracket orders automatically manage risk and reward.

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            side: BUY or SELL
            entry_price: Entry price (None for market entry)
            profit_target: Profit target price
            stop_loss: Stop loss price
            transmit: Whether to transmit the bracket immediately

        Returns:
            Tuple of (parent_order, profit_taker_order, stop_loss_order)
        """
        try:
            # Validate parameters
            valid, error_msg = self.validate_order_params(
                symbol, quantity, side,
                OrderType.LIMIT if entry_price else OrderType.MARKET,
                entry_price, stop_loss
            )
            if not valid:
                raise ValueError(error_msg)

            if profit_target is None and stop_loss is None:
                raise ValueError("Either profit_target or stop_loss must be specified")

            # Create parent order
            if entry_price:
                parent_order = self.submit_limit_order(symbol, quantity, side, entry_price)
            else:
                parent_order = self.submit_market_order(symbol, quantity, side)

            parent_order_id = int(parent_order.order_id)

            # Create profit taker order (opposite side)
            profit_taker_order = None
            if profit_target:
                profit_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
                profit_taker_order = self.submit_limit_order(
                    symbol, quantity, profit_side, profit_target
                )
                profit_taker_id = int(profit_taker_order.order_id)

                # Set OCA group for profit taker
                self.client.reqOneCancelsAll(
                    reqId=profit_taker_id,
                    ocaType="OCA",
                    ocaGroup=f"bracket_{parent_order_id}"
                )

            # Create stop loss order
            stop_loss_order = None
            if stop_loss:
                stop_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
                stop_loss_order = self.submit_stop_order(
                    symbol, quantity, stop_side, stop_loss
                )
                stop_loss_id = int(stop_loss_order.order_id)

                # Set OCA group for stop loss
                self.client.reqOneCancelsAll(
                    reqId=stop_loss_id,
                    ocaType="OCA",
                    ocaGroup=f"bracket_{parent_order_id}"
                )

            # Set parent-child relationships
            if profit_taker_order:
                self.client.reqOneCancelsAll(
                    reqId=parent_order_id,
                    ocaType="OCA",
                    ocaGroup=f"bracket_{parent_order_id}"
                )

            logger.info(
                f"✅ Bracket order submitted: {side.value} {quantity} {symbol} "
                f"@ {entry_price or 'MKT'} (parent_id={parent_order_id})"
            )
            if profit_taker_order:
                logger.info(f"   Profit target: {profit_target} (order_id={profit_taker_id})")
            if stop_loss_order:
                logger.info(f"   Stop loss: {stop_loss} (order_id={stop_loss_id})")

            return parent_order, profit_taker_order, stop_loss_order

        except Exception as e:
            logger.error(f"Failed to submit bracket order: {e}")
            raise

    def submit_trailing_stop_order(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        trail_amount: float,
        trail_type: str = "AMOUNT"
    ) -> Order:
        """
        Submit a trailing stop order.

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            side: BUY or SELL
            trail_amount: Trail amount (absolute or percentage)
            trail_type: "AMOUNT" for absolute trailing, "PERCENT" for percentage

        Returns:
            Trailing stop order
        """
        try:
            # Validate parameters
            valid, error_msg = self.validate_order_params(
                symbol, quantity, side, OrderType.STOP, None, trail_amount
            )
            if not valid:
                raise ValueError(error_msg)

            # Create IB contract
            contract = self._create_contract(symbol)

            # Create trailing stop order
            order = self._create_base_order(quantity, side)
            order.orderType = "TRAIL"
            order.auxPrice = trail_amount  # Trail amount

            if trail_type == "PERCENT":
                order.trailStopPrice = trail_amount  # Percentage trail
            else:
                order.auxPrice = trail_amount  # Amount trail

            # Submit order
            order_id = self._get_next_order_id()
            self.client.placeOrder(order_id, contract, order)

            # Create order object
            trailing_order = Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=OrderType.STOP,
                stop_price=trail_amount,
                order_id=str(order_id),
                status=OrderStatus.SUBMITTED,
                timestamp=datetime.now(),
                metadata={'broker': 'IBKR', 'trail_type': trail_type}
            )

            logger.info(
                f"✅ Trailing stop order submitted: {side.value} {quantity} {symbol} "
                f"trail {trail_amount} ({trail_type}) (order_id={order_id})"
            )

            return trailing_order

        except Exception as e:
            logger.error(f"Failed to submit trailing stop order: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self.client.cancelOrder(int(order_id))
            logger.info(f"✅ Order cancellation requested: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order details"""
        try:
            # If order not in cache, request open orders to populate
            if int(order_id) not in self.wrapper.orders:
                self.client.reqOpenOrders()
                time.sleep(1)  # Wait for callbacks

            order_data = self.wrapper.orders.get(int(order_id))
            if not order_data:
                return None

            # Convert to our Order type
            order = Order(
                symbol=order_data.get('symbol', ''),
                side=OrderSide.BUY if order_data.get('action') == 'BUY' else OrderSide.SELL,
                quantity=order_data.get('quantity', 0),
                order_type=self._convert_order_type(order_data.get('order_type', 'MKT')),
                price=order_data.get('limit_price'),
                stop_price=order_data.get('stop_price'),
                order_id=order_id,
                status=self._convert_order_status(order_data.get('status', 'Unknown')),
                timestamp=order_data.get('timestamp', datetime.now()),
                average_price=order_data.get('avg_fill_price'),
                metadata={'broker': 'IBKR'}
            )

            return order

        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None

    def _convert_order_type(self, ib_type: str) -> OrderType:
        """Convert IB order type to our OrderType enum"""
        type_map = {
            'MKT': OrderType.MARKET,
            'LMT': OrderType.LIMIT,
            'STP': OrderType.STOP,
            'STP LMT': OrderType.STOP_LIMIT,
        }
        return type_map.get(ib_type, OrderType.MARKET)

    def get_orders(self, status: str = "open") -> List[Order]:
        """Get orders with specified status"""
        try:
            # Request open orders
            self.client.reqOpenOrders()
            time.sleep(0.5)  # Wait for response

            orders = []
            for order_id, order_data in self.wrapper.orders.items():
                order = self.get_order(str(order_id))
                if order:
                    # Filter by status if specified
                    if status == "open" and order.status in [
                        OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.ACCEPTED
                    ]:
                        orders.append(order)
                    elif status == "closed" and order.status in [
                        OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED
                    ]:
                        orders.append(order)
                    elif status == "all":
                        orders.append(order)

            return orders

        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []

    # ==================== Position Management ====================

    def get_positions(self) -> List[Position]:
        """Get all current positions"""
        try:
            # Request positions
            self.client.reqPositions()
            time.sleep(1)  # Wait for response

            positions = []
            for symbol, pos_data in self.wrapper.positions.items():
                qty = pos_data['position']
                if qty == 0:
                    continue

                avg_cost = pos_data['avg_cost']

                # Get current price
                quote = self.get_latest_quote(symbol)
                current_price = quote['last_price'] if quote and quote['last_price'] > 0 else avg_cost
                if current_price == 0:
                    current_price = quote['bid_price'] if quote else avg_cost

                market_value = qty * current_price
                cost_basis = qty * avg_cost
                unrealized_pl = market_value - cost_basis
                unrealized_plpc = (unrealized_pl / abs(cost_basis)) * 100 if cost_basis != 0 else 0

                position = Position(
                    symbol=symbol,
                    quantity=qty,
                    avg_entry_price=avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    cost_basis=cost_basis,
                    unrealized_pl=unrealized_pl,
                    unrealized_plpc=unrealized_plpc,
                    side="long" if qty > 0 else "short",
                    timestamp=pos_data['timestamp']
                )

                positions.append(position)

            return positions

        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None

    def close_position(self, symbol: str) -> Order:
        """Close a position"""
        position = self.get_position(symbol)
        if not position:
            raise ValueError(f"No position found for {symbol}")

        # Determine side to close
        side = OrderSide.SELL if position.quantity > 0 else OrderSide.BUY
        quantity = abs(position.quantity)

        return self.submit_market_order(symbol, quantity, side)

    def close_all_positions(self) -> List[Order]:
        """Close all positions"""
        positions = self.get_positions()
        orders = []

        for position in positions:
            try:
                order = self.close_position(position.symbol)
                orders.append(order)
            except Exception as e:
                logger.error(f"Failed to close position {position.symbol}: {e}")

        return orders

    # ==================== Account Management ====================

    def get_account_info(self) -> AccountInfo:
        """Get account information"""
        try:
            # Clear previous account values
            self.wrapper.account_values = {}

            # Request account updates (real-time account data)
            self.client.reqAccountUpdates(True, self.config.account_id or "")

            # Wait for response
            time.sleep(3.0)

            # Extract values
            values = self.wrapper.account_values
            logger.info(f"📊 Retrieved {len(values)} account value fields")

            cash = float(values.get('TotalCashValue', {}).get('value', 0))
            buying_power = float(values.get('BuyingPower', {}).get('value', cash))
            net_liquidation = float(values.get('NetLiquidation', {}).get('value', cash))
            equity = float(values.get('EquityWithLoanValue', {}).get('value', net_liquidation))

            account = AccountInfo(
                account_id=self.config.account_id or values.get('AccountCode', {}).get('account', 'UNKNOWN'),
                cash=cash,
                buying_power=buying_power,
                portfolio_value=net_liquidation,
                equity=equity,
                currency="USD",
                status="active",
                timestamp=datetime.now(),
                metadata={'broker': 'IBKR'}
            )

            return account

        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            logger.error(f"Account values at time of error: {self.wrapper.account_values}")
            raise

    # ==================== Validation & Safety ====================

    def validate_order_params(
        self,
        symbol: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> tuple[bool, Optional[str]]:
        """Validate order parameters"""
        # Basic validation
        if not symbol or not isinstance(symbol, str):
            return False, "Invalid symbol"

        if quantity <= 0:
            return False, f"Invalid quantity: {quantity}"

        if not isinstance(side, OrderSide):
            return False, f"Invalid side: {side}"

        if not isinstance(order_type, OrderType):
            return False, f"Invalid order type: {order_type}"

        # Price validation
        if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if limit_price is None or limit_price <= 0:
                return False, f"Invalid limit price: {limit_price}"

        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if stop_price is None or stop_price <= 0:
                return False, f"Invalid stop price: {stop_price}"

        # Stop-limit validation
        if order_type == OrderType.STOP_LIMIT:
            if side == OrderSide.BUY and stop_price > limit_price:
                return False, "Buy stop-limit: stop price must be <= limit price"
            if side == OrderSide.SELL and stop_price < limit_price:
                return False, "Sell stop-limit: stop price must be >= limit price"

        return True, None

    # ==================== Broker Properties ====================

    @property
    def broker_name(self) -> str:
        return "Interactive Brokers"

    @property
    def supports_fractional_shares(self) -> bool:
        return False  # IB doesn't support fractional shares for stocks

    @property
    def supports_crypto(self) -> bool:
        return True  # IB supports crypto trading

    @property
    def min_order_size(self) -> float:
        return 1.0  # Minimum 1 share

    # ==================== Convenience Methods for Testing ====================

    def place_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> str:
        """
        Convenience method to place an order with string parameters.
        Returns order ID as string.
        """
        # Convert string side to OrderSide enum
        order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

        # Submit order based on type
        if order_type.upper() == "MARKET":
            order = self.submit_market_order(symbol, quantity, order_side)
        elif order_type.upper() == "LIMIT":
            if limit_price is None:
                raise ValueError("limit_price required for LIMIT orders")
            order = self.submit_limit_order(symbol, quantity, order_side, limit_price)
        elif order_type.upper() == "STOP":
            if stop_price is None:
                raise ValueError("stop_price required for STOP orders")
            order = self.submit_stop_order(symbol, quantity, order_side, stop_price)
        elif order_type.upper() == "STOP_LIMIT":
            if limit_price is None or stop_price is None:
                raise ValueError("limit_price and stop_price required for STOP_LIMIT orders")
            order = self.submit_stop_limit_order(symbol, quantity, order_side, limit_price, stop_price)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        return order.order_id

    def get_order_status(self, order_id: str) -> dict:
        """
        Get order status as a dictionary.
        Returns dict with status, filled_qty, avg_fill_price, etc.
        """
        order = self.get_order(order_id)
        if not order:
            return {
                'order_id': order_id,
                'status': 'Unknown',
                'filled_qty': 0,
                'avg_fill_price': 0,
                'limit_price': 0,
                'stop_price': 0
            }

        return {
            'order_id': order.order_id,
            'symbol': order.symbol,
            'quantity': order.quantity,
            'side': order.side.value,
            'type': order.order_type.value,
            'status': order.status.value,
            'filled_qty': order.filled_quantity or 0,
            'avg_fill_price': order.average_price or 0,
            'limit_price': order.price or 0,
            'stop_price': order.stop_price or 0,
            'submitted_at': order.timestamp
        }

    def get_open_orders(self) -> List[dict]:
        """
        Get all open orders as a list of dictionaries.
        """
        orders = self.get_orders(status="open")
        return [
            {
                'order_id': order.order_id,
                'symbol': order.symbol,
                'quantity': order.quantity,
                'side': order.side.value,
                'type': order.order_type.value,
                'status': order.status.value,
                'limit_price': order.price or 0,
                'stop_price': order.stop_price or 0,
                'submitted_at': order.timestamp
            }
            for order in orders
        ]

    def get_market_clock(self) -> Dict[str, Any]:
        """
        Get market clock information

        Returns:
            Dict with market clock data including current time, open status, next open/close times
        """
        try:
            from datetime import datetime, time
            from zoneinfo import ZoneInfo

            # IBKR operates in Eastern Time
            eastern_tz = ZoneInfo("America/New_York")
            now = datetime.now(eastern_tz)

            # Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
            market_open = time(9, 30, tzinfo=eastern_tz)
            market_close = time(16, 0, tzinfo=eastern_tz)

            # Check if it's a weekday (0=Monday, 6=Sunday)
            is_weekday = now.weekday() < 5

            # Check if current time is within market hours
            is_open = (is_weekday and
                      market_open <= now.time() <= market_close)

            # Calculate next open/close times
            if is_open:
                # Market is open, next close is today
                next_close = datetime.combine(now.date(), market_close)
                # Next open is tomorrow if today is Friday, otherwise next weekday
                if now.weekday() == 4:  # Friday
                    days_to_add = 3  # Monday
                else:
                    days_to_add = 1
                next_open_date = now.date() + timedelta(days=days_to_add)
                next_open = datetime.combine(next_open_date, market_open)
            else:
                # Market is closed
                if now.time() < market_open and is_weekday:
                    # Before market open today
                    next_open = datetime.combine(now.date(), market_open)
                    next_close = datetime.combine(now.date(), market_close)
                else:
                    # After market close or weekend
                    if now.weekday() == 4:  # Friday after close
                        days_to_add = 3  # Monday
                    elif now.weekday() == 5:  # Saturday
                        days_to_add = 2  # Monday
                    elif now.weekday() == 6:  # Sunday
                        days_to_add = 1  # Monday
                    else:  # Monday-Thursday after close
                        days_to_add = 1

                    next_open_date = now.date() + timedelta(days=days_to_add)
                    next_open = datetime.combine(next_open_date, market_open)
                    next_close = datetime.combine(next_open_date, market_close)

            return {
                'timestamp': now,
                'is_open': is_open,
                'next_open': next_open,
                'next_close': next_close
            }

        except Exception as e:
            logger.error(f"Error getting market clock: {e}")
            # Return basic fallback data
            now = datetime.now(ZoneInfo("America/New_York"))
            return {
                'timestamp': now,
                'is_open': False,
                'next_open': None,
                'next_close': None
            }

    def get_asset_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get asset information for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Dict with asset information or None if not found
        """
        try:
            # For IBKR, we can get basic contract details
            # In a real implementation, this would query IBKR's contract details
            # For now, return basic stock info assuming it's valid

            return {
                'symbol': symbol,
                'name': f"{symbol} Corporation",  # Placeholder
                'exchange': 'SMART',  # IBKR's smart routing
                'asset_class': 'equity',
                'tradable': True,
                'marginable': True,
                'shortable': True,
                'status': 'active'
            }

        except Exception as e:
            logger.error(f"Error getting asset info for {symbol}: {e}")
            return None

    def check_buying_power(self, amount: float) -> bool:
        """
        Check if account has sufficient buying power

        Args:
            amount: Amount to check against buying power

        Returns:
            bool: True if account has enough buying power, False otherwise
        """
        try:
            account_info = self.get_account_info()
            if account_info and hasattr(account_info, 'buying_power'):
                return float(account_info.buying_power) >= amount
            else:
                # If we can't get buying power, assume insufficient
                logger.warning("Could not retrieve buying power from account info")
                return False

        except Exception as e:
            logger.error(f"Error checking buying power: {e}")
            return False

    def get_historical_bars(
        self,
        symbol: str,
        timeframe: str = "1Min",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical OHLCV bar data from Interactive Brokers

        Args:
            symbol: Stock symbol
            timeframe: Bar timeframe (e.g., '1Min', '5Min', '1Hour', '1Day')
            start: Start datetime
            end: End datetime (defaults to now if not provided)
            limit: Maximum number of bars (IBKR has limits, typically 2000 for intraday)

        Returns:
            list[dict]: List of OHLCV bars with keys: timestamp, open, high, low, close, volume
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to IBKR - cannot get historical data")

        try:
            # Set default end time to now if not provided
            if end is None:
                end = datetime.now(ZoneInfo("America/New_York"))

            # Set default start time if not provided
            if start is None:
                if timeframe == "1Day":
                    start = end - timedelta(days=365)  # 1 year of daily data
                elif timeframe in ["1Hour", "1H"]:
                    start = end - timedelta(days=30)  # 30 days of hourly data
                else:
                    start = end - timedelta(days=7)  # 7 days of intraday data

            # Convert timeframe to IBKR format
            try:
                ib_timeframe = self._convert_timeframe_to_ib(timeframe)
            except ValueError:
                # Return empty list for unsupported timeframes
                logger.warning(f"Unsupported timeframe: {timeframe}")
                return []

            # Calculate duration string for IBKR
            duration = self._calculate_duration_string(start, end, timeframe)

            # Create contract
            contract = self._create_stock_contract(symbol)

            # Generate unique request ID
            req_id = self._get_next_request_id()

            # Set up data collection
            self.wrapper.historical_data[req_id] = []

            # Request historical data
            # Convert end time to IBKR format: yyyymmdd hh:mm:ss timezone
            end_datetime_str = end.strftime("%Y%m%d %H:%M:%S") + " US/Eastern"

            self.client.reqHistoricalData(
                reqId=req_id,
                contract=contract,
                endDateTime=end_datetime_str,
                durationStr=duration,
                barSizeSetting=ib_timeframe,
                whatToShow="TRADES",
                useRTH=1,  # Regular trading hours only
                formatDate=1,
                keepUpToDate=False,
                chartOptions=[]  # Empty list for chart options
            )

            # Wait for data (with timeout)
            timeout = 30  # seconds
            start_time = time.time()

            while req_id not in self.wrapper.historical_data_completed:
                # Check for errors during the wait
                req_errors = [e for e in self.wrapper.errors if e['req_id'] == req_id]
                if req_errors:
                    error = req_errors[-1]  # Get the last error
                    if error['code'] == 200:  # No security definition found
                        logger.warning(f"Invalid symbol '{symbol}' - no security definition found")
                        return []
                    else:
                        raise RuntimeError(f"IBKR error for req_id={req_id}: {error['message']}")

                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Timeout waiting for historical data (req_id={req_id})")
                time.sleep(0.1)

            # Get the collected data
            bars = self.wrapper.historical_data.get(req_id, [])

            # Clean up
            if req_id in self.wrapper.historical_data:
                del self.wrapper.historical_data[req_id]
            if req_id in self.wrapper.historical_data_completed:
                self.wrapper.historical_data_completed.discard(req_id)

            # Convert to expected format
            formatted_bars = []
            for bar in bars:
                # Convert timestamp string to datetime if it's a string
                timestamp = bar.date
                if isinstance(timestamp, str):
                    # IBKR format is typically "YYYYMMDD" or "YYYYMMDD  HH:MM:SS"
                    if len(timestamp) == 8:  # Date only
                        timestamp = datetime.strptime(timestamp, "%Y%m%d")
                    else:  # Date and time
                        timestamp = datetime.strptime(timestamp, "%Y%m%d  %H:%M:%S")

                formatted_bars.append({
                    'timestamp': timestamp,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume
                })

            # Sort by timestamp (oldest first)
            formatted_bars.sort(key=lambda x: x['timestamp'])

            # Filter by date range if start/end specified
            if start or end:
                # Convert timezone-aware start/end to naive for comparison with IBKR timestamps
                start_naive = start.replace(tzinfo=None) if start and start.tzinfo else start
                end_naive = end.replace(tzinfo=None) if end and end.tzinfo else end

                filtered_bars = []
                for bar in formatted_bars:
                    bar_timestamp = bar['timestamp']
                    if start_naive and bar_timestamp < start_naive:
                        continue
                    if end_naive and bar_timestamp > end_naive:
                        continue
                    filtered_bars.append(bar)
                formatted_bars = filtered_bars

            # Apply limit if specified
            if limit and len(formatted_bars) > limit:
                formatted_bars = formatted_bars[-limit:]

            logger.info(f"✅ Retrieved {len(formatted_bars)} historical bars for {symbol} ({timeframe})")
            return formatted_bars

        except Exception as e:
            logger.error(f"Failed to get historical bars for {symbol}: {e}")
            raise

    def _convert_timeframe_to_ib(self, timeframe: str) -> str:
        """Convert timeframe string to IBKR bar size format"""
        timeframe_map = {
            '1Min': '1 min',
            '5Min': '5 mins',
            '15Min': '15 mins',
            '30Min': '30 mins',
            '1Hour': '1 hour',
            '1H': '1 hour',
            '4Hour': '4 hours',
            '1Day': '1 day',
            '1D': '1 day'
        }

        if timeframe not in timeframe_map:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {list(timeframe_map.keys())}")

        return timeframe_map[timeframe]

    def _calculate_duration_string(self, start: datetime, end: datetime, timeframe: str) -> str:
        """Calculate IBKR duration string based on date range and timeframe"""
        delta = end - start

        if timeframe == "1Day":
            days = delta.days
            if days <= 1:
                return "1 D"
            elif days <= 30:
                return f"{days} D"
            else:
                return f"{min(days, 365)} D"  # IBKR limit
        else:
            # For intraday data, IBKR supports up to 2000 bars
            # Convert to seconds for IBKR duration format
            total_seconds = delta.total_seconds()

            if timeframe == "1Min":
                max_seconds = min(2000 * 60, 86400)  # Max 2000 bars or 1 day
            elif timeframe == "5Min":
                max_seconds = min(2000 * 300, 86400)  # Max 2000 bars or 1 day
            elif timeframe == "15Min":
                max_seconds = min(2000 * 900, 86400)  # Max 2000 bars or 1 day
            elif timeframe == "30Min":
                max_seconds = min(2000 * 1800, 86400)  # Max 2000 bars or 1 day
            elif timeframe in ["1Hour", "1H"]:
                max_seconds = min(2000 * 3600, 86400 * 365)  # Max 2000 bars or 365 days
            elif timeframe == "4Hour":
                max_seconds = min(2000 * 14400, 86400 * 365)  # Max 2000 bars or 365 days
            else:
                max_seconds = 86400  # 1 day default

            actual_seconds = min(int(total_seconds), max_seconds)
            return f"{actual_seconds} S"  # S = seconds

    def _get_next_request_id(self) -> int:
        """Get next available request ID for historical data"""
        if not hasattr(self.wrapper, 'next_hist_req_id'):
            self.wrapper.next_hist_req_id = 10000  # Start at 10000 to avoid conflicts

        req_id = self.wrapper.next_hist_req_id
        self.wrapper.next_hist_req_id += 1
        return req_id
