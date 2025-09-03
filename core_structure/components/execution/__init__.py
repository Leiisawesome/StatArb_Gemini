"""
Enhanced Unified Execution Engine Module
======================================

Professional execution engine consolidating all execution functionality:
- Advanced execution algorithms (TWAP, VWAP, Implementation Shortfall)
- Smart order routing and venue selection
- Market impact modeling and prediction
- Transaction cost optimization
- Order management with real-time tracking
- Execution quality analytics
- Unified execution management system

This module transforms raw trading signals into optimal market executions
with institutional-grade performance and risk controls.
"""

from .enhanced_execution_engine import (
    EnhancedExecutionEngine,
    OrderManager,
    SmartOrderRouter,
    TransactionCostOptimizer,
    Order,
    OrderStatus,
    OrderType,
    OrderSide,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionStrategy,
    ExecutionMetrics
)

# Legacy exports for backward compatibility
from .execution_engine import ExecutionEngine
from .market_impact import MarketImpactModel, MarketConditions, SquareRootImpactModel
from .advanced_algorithms import (
    TWAPAlgorithm, VWAPAlgorithm, ImplementationShortfallAlgorithm,
    PairExecutionCoordinator, ExecutionAlgorithmFactory
)

__all__ = [
    # Enhanced unified execution engine
    'EnhancedExecutionEngine',
    'OrderManager',
    'SmartOrderRouter',
    'TransactionCostOptimizer',
    'Order',
    'OrderStatus',
    'OrderType',
    'OrderSide',
    'ExecutionRequest',
    'ExecutionResult',
    'ExecutionStatus',
    'ExecutionStrategy',
    'ExecutionMetrics',
    
    # Legacy components
    'ExecutionEngine',
    'MarketImpactModel',
    'SquareRootImpactModel',
    'MarketConditions',
    'TWAPAlgorithm',
    'VWAPAlgorithm', 
    'ImplementationShortfallAlgorithm',
    'PairExecutionCoordinator',
    'ExecutionAlgorithmFactory'
]

__version__ = "2.0.0" 