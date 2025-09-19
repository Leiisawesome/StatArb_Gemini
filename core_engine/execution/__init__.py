"""
Execution Engine Package
Advanced execution capabilities with institutional-grade algorithms and risk controls
"""

from .execution_engine import (
    ExecutionEngine,
    ExecutionConfig,
    ExecutionRequest,
    ExecutionSlice,
    ExecutionResult,
    ExecutionAlgorithm,
    ExecutionStatus as EngineExecutionStatus
)

from .order_executor import (
    OrderExecutor,
    OrderExecutionConfig,
    OrderRequest,
    OrderType,
    TimeInForce,
    OrderStatus,
    ExecutionQuality,
    Fill,
    OrderState
)

from .trade_executor import (
    TradeExecutor,
    TradeExecutionRequest,
    TradeExecutionAlgorithm,
    TradeStatus,
    RiskLevel,
    TradeSlice,
    MarketDataSnapshot
)

from .fill_processor import (
    FillProcessor,
    TradeExecution,
    FillStatus,
    ReconciliationStatus,
    PositionUpdate,
    FillValidationRule
)

from .execution_validator import (
    ExecutionValidator,
    ExecutionContext,
    ValidationRule,
    ValidationResult,
    ValidationSeverity,
    ValidationCategory,
    ValidationAction
)

from .execution_manager import (
    ExecutionManager,
    ExecutionConfiguration,
    UnifiedExecutionRequest,
    ExecutionStatus,
    ExecutionPriority,
    ExecutionMode
)

__all__ = [
    # Execution Engine
    'ExecutionEngine',
    'ExecutionConfig',
    'ExecutionRequest',
    'ExecutionSlice',
    'ExecutionResult',
    'ExecutionAlgorithm',
    'EngineExecutionStatus',
    
    # Order Executor
    'OrderExecutor',
    'OrderExecutionConfig',
    'OrderRequest',
    'OrderType',
    'TimeInForce',
    'OrderStatus',
    'ExecutionQuality',
    'Fill',
    'OrderState',
    
    # Trade Executor
    'TradeExecutor',
    'TradeExecutionRequest',
    'TradeExecutionAlgorithm',
    'TradeStatus',
    'RiskLevel',
    'TradeSlice',
    'MarketDataSnapshot',
    
    # Fill Processor
    'FillProcessor',
    'TradeExecution',
    'FillStatus',
    'ReconciliationStatus',
    'PositionUpdate',
    'FillValidationRule',
    
    # Execution Validator
    'ExecutionValidator',
    'ExecutionContext',
    'ValidationRule',
    'ValidationResult',
    'ValidationSeverity',
    'ValidationCategory',
    'ValidationAction',
    
    # Execution Manager (Unified Interface)
    'ExecutionManager',
    'ExecutionConfiguration',
    'UnifiedExecutionRequest',
    'ExecutionStatus',
    'ExecutionPriority',
    'ExecutionMode'
]

# Version information
__version__ = "1.0.0"
__author__ = "StatArb Execution Team"
__description__ = "Advanced execution engine with institutional-grade algorithms and risk controls"