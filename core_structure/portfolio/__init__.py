"""
Core Portfolio Management System
===============================

Professional portfolio management system with:
- Position tracking and management
- P&L tracking and analytics
- Portfolio performance metrics
- Real-time portfolio monitoring

This module consolidates all portfolio management functionality from:
- backtesting_framework/portfolio/pnl_tracker.py
- backtesting_framework/portfolio/position_manager.py
"""

from .portfolio_manager import (
    PortfolioManager,
    Position,
    PnLTracker,
    PortfolioMetrics,
    PositionMetrics
)

__all__ = [
    'PortfolioManager',
    'Position',
    'PnLTracker',
    'PortfolioMetrics',
    'PositionMetrics'
] 