"""
Trading Strategies Module

This module provides professional trading strategies and risk management:
- Risk management and position controls
- Stop-loss and take-profit logic
- Drawdown controls and circuit breakers
- Position sizing and portfolio risk
"""

from .risk_management import RiskManager, RiskLimits, RiskMetrics, DrawdownControl

__all__ = [
    'RiskManager',
    'RiskLimits', 
    'RiskMetrics',
    'DrawdownControl'
] 