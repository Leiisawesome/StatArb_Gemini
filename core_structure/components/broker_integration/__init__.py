"""
Broker Integration Module

Professional-grade broker integration for quantitative trading systems.
Supports multiple brokers with unified interfaces for order management,
market data, and portfolio management.

Supported Brokers:
- Interactive Brokers (IBKR) - Primary broker
- Additional brokers can be added as needed

Author: Pro Quant Desk Trader
"""

from .base_broker import (
    BaseBroker, 
    BrokerConfig, 
    Order, 
    OrderResult, 
    Position, 
    AccountSummary, 
    MarketData,
    PortfolioSummary,
    RiskMetrics,
    TradeExecution,
    OrderType,
    OrderSide,
    OrderStatus
)
from .ibkr_config import IBKRConfig, IBKRSetupHelper
from .ibkr import IBKRClient
from .advanced_order_management import (
    AdvancedOrderManager,
    ExecutionParameters,
    ExecutionResult,
    ExecutionAlgorithm,
    OrderPriority,
    MarketCondition,
    MarketImpactModel,
    create_advanced_order_manager
)
from .multi_broker_manager import (
    MultiBrokerManager,
    BrokerType,
    RoutingStrategy,
    BrokerStatus,
    BrokerMetrics,
    RoutingDecision,
    create_multi_broker_manager
)

__all__ = [
    # Core broker components
    'IBKRConfig',
    'IBKRSetupHelper',
    'IBKRClient',
    'BaseBroker',
    'BrokerConfig',
    'Order',
    'OrderResult',
    'Position',
    'AccountSummary',
    'MarketData',
    'PortfolioSummary',
    'RiskMetrics',
    'TradeExecution',
    'OrderType',
    'OrderSide',
    'OrderStatus',
    
    # Advanced order management
    'AdvancedOrderManager',
    'ExecutionParameters',
    'ExecutionResult',
    'ExecutionAlgorithm',
    'OrderPriority',
    'MarketCondition',
    'MarketImpactModel',
    'create_advanced_order_manager',
    
    # Multi-broker management
    'MultiBrokerManager',
    'BrokerType',
    'RoutingStrategy',
    'BrokerStatus',
    'BrokerMetrics',
    'RoutingDecision',
    'create_multi_broker_manager'
]
