"""
Base Broker Interface

Abstract base classes for broker integration that provide unified interfaces
for order management, market data, and portfolio management across different brokers.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple
import uuid

# Use canonical types to eliminate duplicates
from ..infrastructure import OrderType, OrderSide, OrderStatus, Order

logger = logging.getLogger(__name__)


@dataclass
class BrokerConfig:
    """Base configuration for broker connections"""
    broker_name: str
    account_id: str
    paper_trading: bool = True
    enable_logging: bool = True
    connection_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Connection parameters
    host: str = "localhost"
    port: int = 0
    client_id: int = 1
    
    # Security
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    passphrase: Optional[str] = None
    
    # Rate limiting
    max_requests_per_second: int = 100
    max_orders_per_second: int = 10
    
    # Risk management
    max_position_size: float = 0.1  # 10% of portfolio
    max_daily_loss: float = 0.02    # 2% daily loss limit
    max_order_value: float = 1000000  # $1M max order value


@dataclass
class OrderResult:
    """Result of order placement"""
    order_id: str
    status: OrderStatus
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = ""
    error_code: Optional[str] = None


@dataclass
class Position:
    """Broker-specific position information
    
    Note: This is a specialized position class for broker integration.
    For canonical position representation, see infrastructure/types/strategy_types.py
    """
    symbol: str
    quantity: float
    average_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AccountSummary:
    """Account summary information"""
    account_id: str
    total_value: float
    available_cash: float
    buying_power: float
    margin_balance: float
    net_liquidation: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MarketData:
    """Market data representation"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Additional fields
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None


@dataclass
class PortfolioSummary:
    """Portfolio summary information"""
    account_id: str
    total_value: float
    positions_value: float
    cash_balance: float
    unrealized_pnl: float
    realized_pnl: float
    day_pnl: float
    margin_used: float
    buying_power: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    portfolio_beta: float
    portfolio_delta: float
    portfolio_gamma: float
    portfolio_theta: float
    portfolio_vega: float
    var_1day: float  # Value at Risk 1-day
    var_5day: float  # Value at Risk 5-day
    sharpe_ratio: float
    max_drawdown: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TradeExecution:
    """Trade execution details"""
    execution_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Additional execution details
    exchange: Optional[str] = None
    client_id: Optional[str] = None
    account_id: Optional[str] = None


class BaseBroker(ABC):
    """Abstract base class for broker integration"""
    
    def __init__(self, config: BrokerConfig):
        self.config = config
        self.connected = False
        self.connection_time = None
        self.last_heartbeat = None
        
        # Initialize logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Rate limiting
        self.request_count = 0
        self.last_request_time = datetime.now()
        
        # Order tracking
        self.active_orders: Dict[str, Order] = {}
        self.order_history: List[OrderResult] = []
        
        self.logger.info(f"Initialized {config.broker_name} broker integration")
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to broker"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from broker"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to broker"""
        pass
    
    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult:
        """Place order through broker"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel existing order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get current order status"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> Dict[str, Position]:
        """Get current positions"""
        pass
    
    @abstractmethod
    async def get_account_summary(self) -> AccountSummary:
        """Get account summary"""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> MarketData:
        """Get real-time market data"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, 
                                start_date: datetime, 
                                end_date: datetime) -> List[MarketData]:
        """Get historical market data"""
        pass
    
    # Portfolio Management Abstract Methods
    @abstractmethod
    async def get_portfolio_summary(self) -> PortfolioSummary:
        """Get comprehensive portfolio summary"""
        pass
    
    @abstractmethod
    async def get_risk_metrics(self) -> RiskMetrics:
        """Calculate and return portfolio risk metrics"""
        pass
    
    @abstractmethod
    async def get_executions(self, start_date: Optional[datetime] = None) -> List[TradeExecution]:
        """Get trade executions history"""
        pass
    
    @abstractmethod
    async def calculate_pnl(self, symbol: Optional[str] = None) -> Dict[str, float]:
        """Calculate P&L for portfolio or specific symbol"""
        pass
    
    @abstractmethod
    async def get_position_details(self, symbol: str) -> Position:
        """Get detailed position information for a symbol"""
        pass
    
    def _validate_rate_limit(self) -> bool:
        """Validate rate limiting"""
        now = datetime.now()
        if (now - self.last_request_time).total_seconds() >= 1:
            self.request_count = 0
            self.last_request_time = now
        
        if self.request_count >= self.config.max_requests_per_second:
            return False
        
        self.request_count += 1
        return True
    
    def _validate_order(self, order: Order) -> bool:
        """Validate order parameters"""
        # Check order value limit
        if order.price and order.quantity * order.price > self.config.max_order_value:
            self.logger.warning(f"Order value {order.quantity * order.price} exceeds limit {self.config.max_order_value}")
            return False
        
        return True
    
    async def _handle_connection_error(self, error: Exception) -> None:
        """Handle connection errors"""
        self.logger.error(f"Connection error: {error}")
        self.connected = False
        self.connection_time = None
        
        # Implement retry logic
        for attempt in range(self.config.retry_attempts):
            try:
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                if await self.connect():
                    self.logger.info("Reconnected successfully")
                    return
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
        
        self.logger.error("Failed to reconnect after all attempts")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status information"""
        return {
            'connected': self.connected,
            'connection_time': self.connection_time,
            'last_heartbeat': self.last_heartbeat,
            'active_orders': len(self.active_orders),
            'request_count': self.request_count
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'total_orders': len(self.order_history),
            'successful_orders': len([o for o in self.order_history if o.status == OrderStatus.FILLED]),
            'failed_orders': len([o for o in self.order_history if o.status == OrderStatus.REJECTED]),
            'average_commission': sum(o.commission for o in self.order_history) / len(self.order_history) if self.order_history else 0,
            'uptime': (datetime.now() - self.connection_time).total_seconds() if self.connection_time else 0
        }
