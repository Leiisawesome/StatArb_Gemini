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

__all__ = [
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
    'OrderStatus'
]
