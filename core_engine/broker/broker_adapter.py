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
    ALPACA = "alpaca"
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


class InteractiveBrokersAdapter(BrokerAdapterInterface):
    """Interactive Brokers adapter implementation"""
    
    def __init__(self, credentials: BrokerCredentials):
        super().__init__(credentials)
        self._client = None
        self._request_id_counter = 1000
        self._orders = {}
        self._positions = {}
        
    async def connect(self) -> bool:
        """Connect to Interactive Brokers"""
        try:
            self.connection_status = ConnectionStatus.CONNECTING
            
            # Mock connection to IB Gateway/TWS
            await asyncio.sleep(1)  # Simulate connection time
            
            # In real implementation, would use ibapi library
            # from ibapi.client import EClient
            # from ibapi.wrapper import EWrapper
            # self._client = IBClient(self)
            # self._client.connect(host, port, client_id)
            
            self.connection_status = ConnectionStatus.CONNECTED
            logger.info("Connected to Interactive Brokers")
            
            return True
            
        except Exception as e:
            self.connection_status = ConnectionStatus.ERROR
            logger.error(f"Failed to connect to Interactive Brokers: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Interactive Brokers"""
        try:
            if self._client:
                # self._client.disconnect()
                pass
            
            self.connection_status = ConnectionStatus.DISCONNECTED
            logger.info("Disconnected from Interactive Brokers")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Interactive Brokers: {e}")
            return False
    
    async def authenticate(self) -> bool:
        """Authenticate with Interactive Brokers"""
        try:
            # IB uses connection-based authentication
            # Authentication happens during connection
            self.connection_status = ConnectionStatus.AUTHENTICATED
            
            # Get account info to verify
            await self.get_account_info()
            
            self.connection_status = ConnectionStatus.READY
            logger.info("Authenticated with Interactive Brokers")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed with Interactive Brokers: {e}")
            return False
    
    async def submit_order(self, order: StandardOrder) -> str:
        """Submit order to Interactive Brokers"""
        try:
            # Convert to IB order format
            self._convert_to_ib_order(order)
            
            # Generate IB contract
            self._create_ib_contract(order.symbol)
            
            # Submit order (mock implementation)
            request_id = self._get_next_request_id()
            
            # In real implementation:
            # self._client.placeOrder(request_id, ib_contract, ib_order)
            
            # Store order for tracking
            self._orders[order.order_id] = {
                'standard_order': order,
                'ib_order_id': request_id,
                'status': 'SUBMITTED',
                'submitted_at': datetime.now()
            }
            
            logger.info(f"Submitted order {order.order_id} to Interactive Brokers")
            return str(request_id)
            
        except Exception as e:
            logger.error(f"Failed to submit order to Interactive Brokers: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order in Interactive Brokers"""
        try:
            if order_id not in self._orders:
                logger.warning(f"Order {order_id} not found")
                return False
            
            self._orders[order_id]['ib_order_id']
            
            # In real implementation:
            # self._client.cancelOrder(ib_order_id)
            
            self._orders[order_id]['status'] = 'CANCELLED'
            logger.info(f"Cancelled order {order_id} in Interactive Brokers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def modify_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        """Modify order in Interactive Brokers"""
        try:
            if order_id not in self._orders:
                logger.warning(f"Order {order_id} not found")
                return False
            
            # Update order details
            order_data = self._orders[order_id]
            standard_order = order_data['standard_order']
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(standard_order, key):
                    setattr(standard_order, key, value)
            
            # Convert to IB order format
            self._convert_to_ib_order(standard_order)
            self._create_ib_contract(standard_order.symbol)
            order_data['ib_order_id']
            
            # In real implementation:
            # self._client.placeOrder(ib_order_id, ib_contract, ib_order)
            
            logger.info(f"Modified order {order_id} in Interactive Brokers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to modify order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status from Interactive Brokers"""
        try:
            if order_id not in self._orders:
                return None
            
            order_data = self._orders[order_id]
            
            # In real implementation, would query IB for current status
            # For now, return stored status
            return {
                'order_id': order_id,
                'status': order_data['status'],
                'submitted_at': order_data['submitted_at'],
                'ib_order_id': order_data['ib_order_id']
            }
            
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return None
    
    async def get_positions(self, account_id: Optional[str] = None) -> List[StandardPosition]:
        """Get positions from Interactive Brokers"""
        try:
            # In real implementation:
            # self._client.reqPositions()
            # Wait for position updates
            
            # Mock positions
            positions = [
                StandardPosition(
                    symbol="AAPL",
                    quantity=100,
                    avg_cost=150.00,
                    market_value=15000.00,
                    unrealized_pnl=500.00,
                    last_price=155.00
                ),
                StandardPosition(
                    symbol="MSFT",
                    quantity=-50,
                    avg_cost=300.00,
                    market_value=-14750.00,
                    unrealized_pnl=250.00,
                    last_price=295.00
                )
            ]
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions from Interactive Brokers: {e}")
            return []
    
    async def get_account_info(self, account_id: Optional[str] = None) -> StandardAccount:
        """Get account information from Interactive Brokers"""
        try:
            # In real implementation:
            # self._client.reqAccountSummary(reqId, "All", "TotalCashValue,StockMarketValue,BuyingPower")
            
            # Mock account info
            account = StandardAccount(
                account_id=account_id or self.credentials.account_id or "DU123456",
                account_type="MARGIN",
                total_equity=100000.00,
                buying_power=200000.00,
                cash_balance=50000.00,
                positions=await self.get_positions(account_id)
            )
            
            return account
            
        except Exception as e:
            logger.error(f"Failed to get account info from Interactive Brokers: {e}")
            raise
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data from Interactive Brokers"""
        try:
            # In real implementation:
            # self._client.reqMktData(reqId, contract, genericTickList, snapshot, regulatorySnapshot, mktDataOptions)
            
            # Mock market data
            market_data = {
                'symbol': symbol,
                'bid': 150.50,
                'ask': 150.55,
                'last': 150.52,
                'volume': 1000000,
                'timestamp': datetime.now()
            }
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return {}
    
    def _convert_to_ib_order(self, order: StandardOrder) -> Dict[str, Any]:
        """Convert standard order to IB order format"""
        
        # Map order types
        ib_order_type = {
            OrderType.MARKET: "MKT",
            OrderType.LIMIT: "LMT",
            OrderType.STOP: "STP",
            OrderType.STOP_LIMIT: "STP LMT"
        }.get(order.order_type, "LMT")
        
        # Map time in force
        ib_tif = {
            TimeInForce.DAY: "DAY",
            TimeInForce.IOC: "IOC",
            TimeInForce.FOK: "FOK",
            TimeInForce.GTC: "GTC"
        }.get(order.time_in_force, "DAY")
        
        ib_order = {
            'action': order.action.value,
            'totalQuantity': order.quantity,
            'orderType': ib_order_type,
            'tif': ib_tif
        }
        
        if order.limit_price:
            ib_order['lmtPrice'] = order.limit_price
        
        if order.stop_price:
            ib_order['auxPrice'] = order.stop_price
        
        if order.display_size:
            ib_order['displaySize'] = order.display_size
        
        return ib_order
    
    def _create_ib_contract(self, symbol: str) -> Dict[str, Any]:
        """Create IB contract for symbol"""
        
        return {
            'symbol': symbol,
            'secType': 'STK',
            'exchange': 'SMART',
            'currency': 'USD'
        }
    
    def _get_next_request_id(self) -> int:
        """Get next request ID"""
        self._request_id_counter += 1
        return self._request_id_counter


class AlpacaAdapter(BrokerAdapterInterface):
    """Alpaca adapter implementation"""
    
    def __init__(self, credentials: BrokerCredentials):
        super().__init__(credentials)
        self._session = None
        self._base_url = "https://paper-api.alpaca.markets" if credentials.paper_trading else "https://api.alpaca.markets"
        
    async def connect(self) -> bool:
        """Connect to Alpaca"""
        try:
            self.connection_status = ConnectionStatus.CONNECTING
            
            # Initialize HTTP session
            import aiohttp
            self._session = aiohttp.ClientSession()
            
            self.connection_status = ConnectionStatus.CONNECTED
            logger.info("Connected to Alpaca")
            return True
            
        except Exception as e:
            self.connection_status = ConnectionStatus.ERROR
            logger.error(f"Failed to connect to Alpaca: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Alpaca"""
        try:
            if self._session:
                await self._session.close()
            
            self.connection_status = ConnectionStatus.DISCONNECTED
            logger.info("Disconnected from Alpaca")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Alpaca: {e}")
            return False
    
    async def authenticate(self) -> bool:
        """Authenticate with Alpaca"""
        try:
            # Test authentication by getting account info
            headers = {
                'APCA-API-KEY-ID': self.credentials.api_key,
                'APCA-API-SECRET-KEY': self.credentials.secret_key
            }
            
            # Mock authentication check
            self.connection_status = ConnectionStatus.AUTHENTICATED
            
            # Verify by getting account
            await self.get_account_info()
            
            self.connection_status = ConnectionStatus.READY
            logger.info("Authenticated with Alpaca")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed with Alpaca: {e}")
            return False
    
    async def submit_order(self, order: StandardOrder) -> str:
        """Submit order to Alpaca"""
        try:
            # Convert to Alpaca order format
            self._convert_to_alpaca_order(order)
            
            # Mock submission
            order_response = {
                'id': str(uuid.uuid4()),
                'status': 'accepted',
                'created_at': datetime.now().isoformat()
            }
            
            logger.info(f"Submitted order {order.order_id} to Alpaca")
            return order_response['id']
            
        except Exception as e:
            logger.error(f"Failed to submit order to Alpaca: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order in Alpaca"""
        try:
            # Mock cancellation
            logger.info(f"Cancelled order {order_id} in Alpaca")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def modify_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        """Modify order in Alpaca"""
        try:
            # Alpaca supports limited order modifications
            # Mock modification
            logger.info(f"Modified order {order_id} in Alpaca")
            return True
            
        except Exception as e:
            logger.error(f"Failed to modify order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status from Alpaca"""
        try:
            # Mock order status
            return {
                'id': order_id,
                'status': 'filled',
                'filled_qty': '100',
                'filled_avg_price': '150.25'
            }
            
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return None
    
    async def get_positions(self, account_id: Optional[str] = None) -> List[StandardPosition]:
        """Get positions from Alpaca"""
        try:
            # Mock positions
            positions = [
                StandardPosition(
                    symbol="AAPL",
                    quantity=100,
                    avg_cost=150.00,
                    market_value=15000.00,
                    unrealized_pnl=500.00,
                    last_price=155.00
                )
            ]
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions from Alpaca: {e}")
            return []
    
    async def get_account_info(self, account_id: Optional[str] = None) -> StandardAccount:
        """Get account information from Alpaca"""
        try:
            # Mock account info
            account = StandardAccount(
                account_id=self.credentials.account_id or "ALPACA123",
                account_type="CASH",
                total_equity=100000.00,
                buying_power=100000.00,
                cash_balance=50000.00,
                positions=await self.get_positions(account_id)
            )
            
            return account
            
        except Exception as e:
            logger.error(f"Failed to get account info from Alpaca: {e}")
            raise
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data from Alpaca"""
        try:
            # Mock market data
            market_data = {
                'symbol': symbol,
                'bid': 150.50,
                'ask': 150.55,
                'last': 150.52,
                'volume': 1000000,
                'timestamp': datetime.now()
            }
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return {}
    
    def _convert_to_alpaca_order(self, order: StandardOrder) -> Dict[str, Any]:
        """Convert standard order to Alpaca order format"""
        
        alpaca_order = {
            'symbol': order.symbol,
            'qty': str(order.quantity),
            'side': order.action.value.lower(),
            'type': order.order_type.value.lower(),
            'time_in_force': order.time_in_force.value
        }
        
        if order.limit_price:
            alpaca_order['limit_price'] = str(order.limit_price)
        
        if order.stop_price:
            alpaca_order['stop_price'] = str(order.stop_price)
        
        return alpaca_order


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
    """Factory for creating broker adapters"""
    
    _adapters = {
        BrokerType.INTERACTIVE_BROKERS: InteractiveBrokersAdapter,
        BrokerType.ALPACA: AlpacaAdapter,
        BrokerType.TD_AMERITRADE: MockBrokerAdapter,  # Would implement TDAmeritrade
        BrokerType.E_TRADE: MockBrokerAdapter,        # Would implement ETrade
        BrokerType.CHARLES_SCHWAB: MockBrokerAdapter, # Would implement Schwab
        BrokerType.FIDELITY: MockBrokerAdapter,       # Would implement Fidelity
        BrokerType.BLOOMBERG: MockBrokerAdapter,      # Would implement Bloomberg
        BrokerType.REFINITIV: MockBrokerAdapter,      # Would implement Refinitiv
        BrokerType.PRIME_BROKERAGE: MockBrokerAdapter,# Would implement Prime
        BrokerType.CRYPTO_EXCHANGE: MockBrokerAdapter # Would implement Crypto
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