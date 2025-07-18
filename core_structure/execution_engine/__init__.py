"""
Execution Engine Module

Professional-grade execution engine providing:
- Advanced execution algorithms (TWAP, VWAP, Implementation Shortfall)
- Smart order routing and venue selection
- Market impact modeling and prediction
- Transaction cost optimization
- Order management with real-time tracking
- Execution quality analytics

This module transforms raw trading signals into optimal market executions
with institutional-grade performance and risk controls.
"""

from .execution_engine import ExecutionEngine, ExecutionResult, ExecutionStatus
from .order_manager import OrderManager, Order, OrderStatus, OrderType, OrderSide
from .market_impact import MarketImpactModel, MarketConditions, SquareRootImpactModel
from .transaction_cost_optimizer import TransactionCostOptimizer, BrokerType
from .advanced_algorithms import (
    TWAPAlgorithm, VWAPAlgorithm, ImplementationShortfallAlgorithm,
    PairExecutionCoordinator, ExecutionAlgorithmFactory
)
from .smart_order_router import SmartOrderRouter, VenueSelector, ExecutionVenue

__all__ = [
    # Core execution engine
    'ExecutionEngine',
    'ExecutionResult', 
    'ExecutionStatus',
    
    # Order management
    'OrderManager',
    'Order',
    'OrderStatus',
    'OrderType',
    'OrderSide',
    
    # Market impact and costs
    'MarketImpactModel',
    'SquareRootImpactModel',
    'MarketConditions',
    'TransactionCostOptimizer',
    'BrokerType',
    
    # Advanced algorithms
    'TWAPAlgorithm',
    'VWAPAlgorithm', 
    'ImplementationShortfallAlgorithm',
    'PairExecutionCoordinator',
    'ExecutionAlgorithmFactory',
    
    # Smart routing
    'SmartOrderRouter',
    'VenueSelector',
    'ExecutionVenue'
]

__version__ = "1.0.0" 