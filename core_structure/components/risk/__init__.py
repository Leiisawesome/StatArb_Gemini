"""
Core Risk Management System
==========================

Professional risk management system with:
- Position-level risk monitoring and limits
- Portfolio-level risk metrics and VaR calculation
- Dynamic stop-loss and take-profit management
- Position sizing with Kelly criterion and volatility targeting
- Real-time risk monitoring and alerting

This module consolidates all risk management functionality from:
- [REMOVED] Old backtesting framework components (superseded by strategy_layer)
"""

# Import unified risk manager as the primary risk manager
from .unified_risk_manager import (
    UnifiedRiskManager as RiskManager,
    RiskLimits,
    PositionRiskProfile as PositionRisk,
    UnifiedRiskMetrics as PortfolioRisk,
    RiskLevel,
    RiskAction,
    RiskAlert,
    TradingMode
)

# Note: Old risk_manager.py has been removed - all functionality moved to unified_risk_manager.py

__all__ = [
    'RiskManager',           # UnifiedRiskManager (primary)
    'RiskLimits',           # Unified risk limits
    'PositionRisk',         # PositionRiskProfile
    'PortfolioRisk',        # UnifiedRiskMetrics
    'RiskLevel',            # Risk level enum
    'RiskAction',           # Risk action enum
    'RiskAlert',            # Risk alert dataclass
    'TradingMode',          # Trading mode enum
] 