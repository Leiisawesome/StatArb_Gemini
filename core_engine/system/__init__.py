"""
System Components - Core Engine
================================

Central system components including orchestration and governance.

Main Components:
- CentralRiskManager: Single point of authority for all trading decisions (Rule 4)
- HierarchicalSystemOrchestrator: System-wide orchestration and lifecycle management
- UnifiedExecutionEngine: Institutional-grade order execution
- SystemIntegrationManager: Multi-phase initialization and health monitoring

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

from .central_risk_manager import (
    CentralRiskManager,
    TradingDecisionRequest,
    TradingAuthorization,
    TradingDecisionType,
    AuthorizationLevel
)

from .hierarchical_orchestrator import (
    HierarchicalSystemOrchestrator,
    ComponentLayer,
    AuthorityLevel
)

from .unified_execution_engine import (
    UnifiedExecutionEngine,
    ExecutionRequest,
    ExecutionResult,
    ExecutionAuthorization,
    ExecutionAlgorithm,
    ExecutionUrgency,
    ExecutionStatus
)

from .interfaces import (
    ISystemComponent,
    IRegimeAware,
    RegimeContext
)

__all__ = [
    # Central Risk Manager (Rule 4)
    'CentralRiskManager',
    'TradingDecisionRequest',
    'TradingAuthorization',
    'TradingDecisionType',
    'AuthorityLevel',
    
    # System Orchestration
    'HierarchicalSystemOrchestrator',
    'ComponentLayer',
    'AuthorityLevel',
    
    # Execution Engine
    'UnifiedExecutionEngine',
    'ExecutionRequest',
    'ExecutionResult',
    'ExecutionAuthorization',
    'ExecutionAlgorithm',
    'ExecutionUrgency',
    'ExecutionStatus',
    
    # Interfaces
    'ISystemComponent',
    'IRegimeAware',
    'RegimeContext',
]

