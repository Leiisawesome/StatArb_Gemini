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
- backtesting_framework/risk/risk_manager.py
- backtesting_framework/risk/stop_loss_manager.py
- backtesting_framework/portfolio/position_sizing.py
"""

from .risk_manager import (
    RiskManager,
    RiskLimits,
    PositionRisk,
    PortfolioRisk,
    RiskOrder,
    PositionSize,
    RiskLevel,
    OrderType
)

__all__ = [
    'RiskManager',
    'RiskLimits', 
    'PositionRisk',
    'PortfolioRisk',
    'RiskOrder',
    'PositionSize',
    'RiskLevel',
    'OrderType'
] 