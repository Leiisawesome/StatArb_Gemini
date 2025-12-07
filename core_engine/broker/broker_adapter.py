"""
Broker Engine - Broker Adapter
Multi-broker integration with standardized API abstraction
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict
from abc import ABC, abstractmethod
import uuid
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class BrokerType(Enum):
    """Supported broker types"""
    INTERACTIVE_BROKERS = "interactive_brokers"
    TD_AMERITRADE = "td_ameritrade"
    E_TRADE = "e_trade"
    CHARLES_SCHWAB = "charles_schwab"
    FIDELITY = "fidelity"
    BLOOMBERG = "bloomberg"
    REFINITIV = "refinitiv"
    PRIME_BROKERAGE = "prime_brokerage"
    CRYPTO_EXCHANGE = "crypto_exchange"


class ConnectionStatus(Enum):
    """Connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    READY = "ready"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class OrderAction(Enum):
    """Order actions"""
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"


class OrderType(Enum):
    """Order types"""
    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP_LMT"
    TRAIL = "TRAIL"
    TRAIL_LIMIT = "TRAIL_LIMIT"
    ICEBERG = "ICEBERG"
    HIDDEN = "HIDDEN"


class TimeInForce(Enum):
    """Time in force"""
    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    GTC = "GTC"  # Good Till Cancel
    GTD = "GTD"  # Good Till Date


@dataclass
class BrokerCredentials:
    """Broker authentication credentials"""
    broker_type: BrokerType

    # API credentials
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    access_token: Optional[str] = None

    # Connection details
    host: Optional[str] = None
    port: Optional[int] = None
    client_id: Optional[str] = None

    # Account information
    account_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    # Additional parameters
    paper_trading: bool = False
    sandbox_mode: bool = False
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StandardOrder:
    """Standardized order representation"""
    order_id: str
    symbol: str
    action: OrderAction
    quantity: float
    order_type: OrderType

    # Price parameters
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    # Time and execution
    time_in_force: TimeInForce = TimeInForce.DAY

    # Advanced parameters
    display_size: Optional[float] = None
    min_quantity: Optional[float] = None

    # Routing
    exchange: Optional[str] = None

    # Metadata
    client_order_id: Optional[str] = None
    parent_order_id: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None


@dataclass
class StandardExecution:
    """Standardized execution representation"""
    execution_id: str
    order_id: str
    symbol: str
    side: str

    # Execution details
    quantity: float
    price: float

    # Timing
    execution_time: datetime

    # Optional fields with defaults
    commission: float = 0.0

    # Market data
    bid: Optional[float] = None
    ask: Optional[float] = None

    # Venue information
    exchange: Optional[str] = None
    liquidity_flag: Optional[str] = None

    # Broker specific
    broker_execution_id: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StandardPosition:
    """Standardized position representation"""
    symbol: str
    quantity: float
    avg_cost: float
    market_value: float
    unrealized_pnl: float

    # Additional details
    last_price: Optional[float] = None
    currency: str = "USD"

    # Timestamps
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class StandardAccount:
    """Standardized account information"""
    account_id: str
    account_type: str

    # Balances
    total_equity: float
    buying_power: float
    cash_balance: float

    # Positions
    positions: List[StandardPosition] = field(default_factory=list)

    # Metadata
    currency: str = "USD"
    last_updated: datetime = field(default_factory=datetime.now)


class BrokerAdapterInterface(ABC):
    """Abstract base class for broker adapters"""

    def __init__(self, credentials: BrokerCredentials):
        self.credentials = credentials
        self.connection_status = ConnectionStatus.DISCONNECTED
        self._event_callbacks = defaultdict(list)

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to broker"""

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from broker"""

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with broker"""

    @abstractmethod
    async def submit_order(self, order: StandardOrder) -> str:
        """Submit order to broker"""

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""

    @abstractmethod
    async def modify_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        """Modify existing order"""

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status"""

    @abstractmethod
    async def get_positions(self, account_id: Optional[str] = None) -> List[StandardPosition]:
        """Get account positions"""

    @abstractmethod
    async def get_account_info(self, account_id: Optional[str] = None) -> StandardAccount:
        """Get account information"""

    @abstractmethod
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for symbol"""

    def add_event_callback(self, event_type: str, callback: Callable) -> None:
        """Add event callback"""
        self._event_callbacks[event_type].append(callback)

    def _trigger_event(self, event_type: str, data: Any) -> None:
        """Trigger event callbacks"""
        for callback in self._event_callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")


# ============================================================================
# DEPRECATED ADAPTER CLASSES REMOVED
# ============================================================================
# The following deprecated classes have been removed from this file:
#
# 1. InteractiveBrokersAdapter (~330 LOC) - REMOVED
#    Use instead: core_engine.broker.adapters.ibkr_adapter.IBKRAdapter
#
# 2. AlpacaAdapter - REMOVED (Alpaca adapter has been removed from the codebase)
#    Previously: core_engine.broker.adapters.alpaca_adapter.AlpacaAdapter
#
# For production trading, import directly from the adapters module:
#   from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter
# ============================================================================


class MockBrokerAdapter(BrokerAdapterInterface):
    """Mock broker adapter for testing"""

    def __init__(self, credentials: BrokerCredentials):
        super().__init__(credentials)
        self._orders = {}
        self._positions = {}

    async def connect(self) -> bool:
        """Mock connect"""
        await asyncio.sleep(0.1)
        self.connection_status = ConnectionStatus.CONNECTED
        return True

    async def disconnect(self) -> bool:
        """Mock disconnect"""
        self.connection_status = ConnectionStatus.DISCONNECTED
        return True

    async def authenticate(self) -> bool:
        """Mock authenticate"""
        self.connection_status = ConnectionStatus.READY
        return True

    async def submit_order(self, order: StandardOrder) -> str:
        """Mock submit order"""
        broker_order_id = str(uuid.uuid4())
        self._orders[order.order_id] = {
            'broker_order_id': broker_order_id,
            'status': 'SUBMITTED',
            'order': order
        }
        return broker_order_id

    async def cancel_order(self, order_id: str) -> bool:
        """Mock cancel order"""
        if order_id in self._orders:
            self._orders[order_id]['status'] = 'CANCELLED'
            return True
        return False

    async def modify_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        """Mock modify order"""
        return order_id in self._orders

    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Mock get order status"""
        if order_id in self._orders:
            return self._orders[order_id]
        return None

    async def get_positions(self, account_id: Optional[str] = None) -> List[StandardPosition]:
        """Mock get positions"""
        return []

    async def get_account_info(self, account_id: Optional[str] = None) -> StandardAccount:
        """Mock get account info"""
        return StandardAccount(
            account_id="MOCK123",
            account_type="PAPER",
            total_equity=100000.00,
            buying_power=100000.00,
            cash_balance=100000.00
        )

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Mock get market data"""
        return {
            'symbol': symbol,
            'bid': 100.00,
            'ask': 100.05,
            'last': 100.02,
            'volume': 10000,
            'timestamp': datetime.now()
        }


class BrokerAdapterFactory:
    """
    Factory for creating broker adapters

    Note: For production trading, use the specific adapters directly:
    - core_engine.broker.adapters.ibkr_adapter.IBKRAdapter

    This factory uses MockBrokerAdapter for testing purposes.
    """

    _adapters = {
        BrokerType.INTERACTIVE_BROKERS: MockBrokerAdapter,  # Use IBKRAdapter for production
        BrokerType.TD_AMERITRADE: MockBrokerAdapter,
        BrokerType.E_TRADE: MockBrokerAdapter,
        BrokerType.CHARLES_SCHWAB: MockBrokerAdapter,
        BrokerType.FIDELITY: MockBrokerAdapter,
        BrokerType.BLOOMBERG: MockBrokerAdapter,
        BrokerType.REFINITIV: MockBrokerAdapter,
        BrokerType.PRIME_BROKERAGE: MockBrokerAdapter,
        BrokerType.CRYPTO_EXCHANGE: MockBrokerAdapter
    }

    @classmethod
    def create_adapter(cls, credentials: BrokerCredentials) -> BrokerAdapterInterface:
        """Create broker adapter based on broker type"""

        adapter_class = cls._adapters.get(credentials.broker_type)

        if not adapter_class:
            raise ValueError(f"Unsupported broker type: {credentials.broker_type}")

        return adapter_class(credentials)

    @classmethod
    def register_adapter(cls, broker_type: BrokerType, adapter_class: type) -> None:
        """Register custom broker adapter"""
        cls._adapters[broker_type] = adapter_class

    @classmethod
    def get_supported_brokers(cls) -> List[BrokerType]:
        """Get list of supported broker types"""
        return list(cls._adapters.keys())


class BrokerAdapter:
    """
    Multi-Broker Adapter

    Provides standardized interface for multiple brokers with
    automatic protocol translation and connection management.
    """

    def __init__(self, credentials: BrokerCredentials):
        """Initialize broker adapter"""

        self.credentials = credentials
        self.broker_type = credentials.broker_type

        # Create specific adapter
        self._adapter = BrokerAdapterFactory.create_adapter(credentials)

        # Connection tracking
        self.connection_status = ConnectionStatus.DISCONNECTED
        self.last_heartbeat = None

        # Performance metrics
        self._metrics = {
            'orders_submitted': 0,
            'orders_filled': 0,
            'orders_cancelled': 0,
            'connection_uptime': 0,
            'avg_response_time': 0,
            'error_count': 0
        }

        # Event handlers
        self._event_handlers = defaultdict(list)

        logger.info(f"Broker adapter initialized for {self.broker_type.value}")

    async def connect(self) -> bool:
        """Connect to broker"""
        try:
            start_time = time.time()

            success = await self._adapter.connect()

            if success:
                self.connection_status = self._adapter.connection_status
                self.last_heartbeat = datetime.now()

                # Authenticate if connected
                if self.connection_status == ConnectionStatus.CONNECTED:
                    auth_success = await self._adapter.authenticate()
                    if auth_success:
                        self.connection_status = self._adapter.connection_status
                    else:
                        await self._adapter.disconnect()
                        return False

                response_time = time.time() - start_time
                self._update_metrics('connection_time', response_time)

                logger.info(f"Successfully connected to {self.broker_type.value}")
                self._trigger_event('connected', {'broker': self.broker_type.value})

                return True

            return False

        except Exception as e:
            self._metrics['error_count'] += 1
            logger.error(f"Failed to connect to {self.broker_type.value}: {e}")
            self._trigger_event('connection_error', {'error': str(e)})
            return False

    async def disconnect(self) -> bool:
        """Disconnect from broker"""
        try:
            success = await self._adapter.disconnect()

            if success:
                self.connection_status = ConnectionStatus.DISCONNECTED
                logger.info(f"Disconnected from {self.broker_type.value}")
                self._trigger_event('disconnected', {'broker': self.broker_type.value})

            return success

        except Exception as e:
            logger.error(f"Error disconnecting from {self.broker_type.value}: {e}")
            return False

    async def submit_order(self, order: StandardOrder) -> str:
        """Submit order through broker"""
        try:
            start_time = time.time()

            if self.connection_status != ConnectionStatus.READY:
                raise RuntimeError("Broker not ready for trading")

            broker_order_id = await self._adapter.submit_order(order)

            response_time = time.time() - start_time
            self._update_metrics('order_response_time', response_time)
            self._metrics['orders_submitted'] += 1

            logger.info(f"Order {order.order_id} submitted to {self.broker_type.value}: {broker_order_id}")

            self._trigger_event('order_submitted', {
                'order_id': order.order_id,
                'broker_order_id': broker_order_id,
                'symbol': order.symbol
            })

            return broker_order_id

        except Exception as e:
            self._metrics['error_count'] += 1
            logger.error(f"Failed to submit order {order.order_id}: {e}")
            self._trigger_event('order_error', {'order_id': order.order_id, 'error': str(e)})
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order through broker"""
        try:
            if self.connection_status != ConnectionStatus.READY:
                raise RuntimeError("Broker not ready for trading")

            success = await self._adapter.cancel_order(order_id)

            if success:
                self._metrics['orders_cancelled'] += 1
                logger.info(f"Order {order_id} cancelled in {self.broker_type.value}")
                self._trigger_event('order_cancelled', {'order_id': order_id})

            return success

        except Exception as e:
            self._metrics['error_count'] += 1
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def modify_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        """Modify order through broker"""
        try:
            if self.connection_status != ConnectionStatus.READY:
                raise RuntimeError("Broker not ready for trading")

            success = await self._adapter.modify_order(order_id, updates)

            if success:
                logger.info(f"Order {order_id} modified in {self.broker_type.value}")
                self._trigger_event('order_modified', {'order_id': order_id, 'updates': updates})

            return success

        except Exception as e:
            self._metrics['error_count'] += 1
            logger.error(f"Failed to modify order {order_id}: {e}")
            return False

    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status from broker"""
        try:
            return await self._adapter.get_order_status(order_id)

        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return None

    async def get_positions(self, account_id: Optional[str] = None) -> List[StandardPosition]:
        """Get positions from broker"""
        try:
            return await self._adapter.get_positions(account_id)

        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    async def get_account_info(self, account_id: Optional[str] = None) -> Optional[StandardAccount]:
        """Get account information from broker"""
        try:
            return await self._adapter.get_account_info(account_id)

        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data from broker"""
        try:
            return await self._adapter.get_market_data(symbol)

        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return {}

    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add event handler"""
        self._event_handlers[event_type].append(handler)

    def _trigger_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger event handlers"""
        for handler in self._event_handlers[event_type]:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    def _update_metrics(self, metric: str, value: float) -> None:
        """Update performance metrics"""
        if metric == 'order_response_time':
            # Update rolling average
            current_avg = self._metrics.get('avg_response_time', 0)
            count = self._metrics.get('orders_submitted', 0)
            self._metrics['avg_response_time'] = (current_avg * count + value) / (count + 1)
        else:
            self._metrics[metric] = value

    def get_connection_status(self) -> ConnectionStatus:
        """Get current connection status"""
        return self.connection_status

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        metrics = self._metrics.copy()

        # Add connection uptime
        if self.last_heartbeat:
            uptime = (datetime.now() - self.last_heartbeat).total_seconds()
            metrics['connection_uptime'] = uptime

        return metrics

    def is_ready(self) -> bool:
        """Check if broker is ready for trading"""
        return self.connection_status == ConnectionStatus.READY

    def get_supported_features(self) -> Dict[str, bool]:
        """Get supported features for this broker"""

        # Feature matrix by broker type
        features = {
            BrokerType.INTERACTIVE_BROKERS: {
                'order_modification': True,
                'complex_orders': True,
                'real_time_data': True,
                'options_trading': True,
                'futures_trading': True,
                'forex_trading': True,
                'crypto_trading': False
            },
            BrokerType.ALPACA: {
                'order_modification': True,
                'complex_orders': False,
                'real_time_data': True,
                'options_trading': False,
                'futures_trading': False,
                'forex_trading': False,
                'crypto_trading': True
            }
        }

        return features.get(self.broker_type, {})

    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            # Try to get account info as health check
            account = await self.get_account_info()

            if account:
                self.last_heartbeat = datetime.now()
                return True

            return False

        except Exception as e:
            logger.error(f"Health check failed for {self.broker_type.value}: {e}")
            return False