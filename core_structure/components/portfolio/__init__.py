"""
Core Portfolio Management System
===============================

Professional portfolio management system with:
- Unified portfolio management across all trading modes
- Position tracking and management
- P&L tracking and analytics
- Portfolio performance metrics
- Real-time portfolio monitoring
- Strategy-level performance attribution

This module consolidates all portfolio management functionality and
provides consistent portfolio tracking across backtesting and live trading.
"""

from .portfolio_manager import (
    PortfolioManager,
    Position,
    PnLTracker,
    PortfolioMetrics,
    PositionMetrics
)

from .unified_portfolio_bridge import (
    UnifiedPortfolioBridge,
    UnifiedPosition,
    PortfolioState,
    TradingMode as PortfolioTradingMode,
    create_unified_portfolio
)

__all__ = [
    # Core portfolio management
    'PortfolioManager',
    'Position',
    'PnLTracker',
    'PortfolioMetrics',
    'PositionMetrics',
    
    # Unified portfolio bridge (primary)
    'UnifiedPortfolioBridge',
    'UnifiedPosition',
    'PortfolioState',
    'PortfolioTradingMode',
    'create_unified_portfolio'
] 