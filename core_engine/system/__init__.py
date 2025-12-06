"""
System Components - Core Engine
================================

Central system components including orchestration and governance.

Architecture Compliance (Tier-1 Rules - December 2025 Migration):
- Rule 1: System Architecture - Layer 0 (Orchestrator), Layer 1 (Governance)
- Rule 3: Risk & Compliance Governance - CentralRiskManager, ComplianceChecker
- Rule 5: Execution & Order Management - OMS, UnifiedExecutionEngine
- Rule 6: Operations & Recovery - Reconciliation, P&L, Settlement, Aging

Main Components:
- CentralRiskManager: Single point of authority for all trading decisions (Rule 3)
- HierarchicalSystemOrchestrator: System-wide orchestration and lifecycle management (Rule 1)
- UnifiedExecutionEngine: Institutional-grade order execution (Rule 5, Phase 13)
- OrderManagementSystem: Order lifecycle management (Rule 5, Phase 12)
- SettlementManager: T+1/T+2 settlement tracking (Rule 6, Section 4)

Operational Components (Rule 6):
- PositionReconciliationEngine: Broker position sync
- RealTimePnLTracker: Tick-level P&L monitoring
- PositionAgingMonitor: Holding period enforcement
- TradingCircuitBreakers: Emergency protection (Rule 3, Phase 9)

Author: StatArb_Gemini Core Engine
Version: 2.0.0 (Rules Migration December 2025)
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

# New components (Rule 5 & Rule 6)
from .order_management_system import (
    OrderManagementSystem,
    Order,
    OrderState,
    OrderType,
    TimeInForce
)

from .settlement_manager import (
    SettlementManager,
    SettlementRecord,
    SettlementStatus,
    SettlementType
)

# Operational components (Rule 6)
from .circuit_breakers import CircuitBreakerLevel
from .compliance_checker import PreTradeComplianceChecker

__all__ = [
    # Central Risk Manager (Rule 3)
    'CentralRiskManager',
    'TradingDecisionRequest',
    'TradingAuthorization',
    'TradingDecisionType',
    'AuthorizationLevel',
    
    # System Orchestration (Rule 1)
    'HierarchicalSystemOrchestrator',
    'ComponentLayer',
    'AuthorityLevel',
    
    # Execution Engine (Rule 5, Phase 13)
    'UnifiedExecutionEngine',
    'ExecutionRequest',
    'ExecutionResult',
    'ExecutionAuthorization',
    'ExecutionAlgorithm',
    'ExecutionUrgency',
    'ExecutionStatus',
    
    # Order Management System (Rule 5, Phase 12)
    'OrderManagementSystem',
    'Order',
    'OrderState',
    'OrderType',
    'TimeInForce',
    
    # Settlement Manager (Rule 6, Section 4)
    'SettlementManager',
    'SettlementRecord',
    'SettlementStatus',
    'SettlementType',
    
    # Compliance (Rule 3, Phase 7)
    'PreTradeComplianceChecker',
    'CircuitBreakerLevel',
    
    # Interfaces
    'ISystemComponent',
    'IRegimeAware',
    'RegimeContext',
]

