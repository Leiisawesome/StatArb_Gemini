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

# Unified execution engine (PRIMARY - use this for all execution needs)
from .unified_execution_engine import (
    UnifiedExecutionEngine, 
    ExecutionMode, 
    SlippageModel, 
    LatencySimulator,
    MarketConditions as UnifiedMarketConditions,
    create_execution_engine,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus
)

# Supporting components
from .market_impact import MarketImpactModel, MarketConditions, SquareRootImpactModel
from .advanced_algorithms import (
    TWAPAlgorithm, VWAPAlgorithm, ImplementationShortfallAlgorithm,
    PairExecutionCoordinator, ExecutionAlgorithmFactory
)

# Order management components (if needed separately)
try:
    from .order_manager import OrderManager, Order, OrderStatus, OrderType, OrderSide
    ORDER_MANAGER_AVAILABLE = True
except ImportError:
    ORDER_MANAGER_AVAILABLE = False

__all__ = [
    # Unified execution engine (PRIMARY - use this for all execution needs)
    'UnifiedExecutionEngine',
    'ExecutionMode',
    'SlippageModel',
    'LatencySimulator',
    'UnifiedMarketConditions',
    'create_execution_engine',
    'ExecutionRequest',
    'ExecutionResult',
    'ExecutionStatus',
    
    # Supporting components
    'MarketImpactModel',
    'SquareRootImpactModel',
    'MarketConditions',
    'TWAPAlgorithm',
    'VWAPAlgorithm', 
    'ImplementationShortfallAlgorithm',
    'PairExecutionCoordinator',
    'ExecutionAlgorithmFactory'
]

# Add order management components if available
if ORDER_MANAGER_AVAILABLE:
    __all__.extend([
        'OrderManager',
        'Order',
        'OrderStatus',
        'OrderType',
        'OrderSide'
    ])

__version__ = "2.0.0" 