"""
Trading Brick - Professional API
================================

Core trading components for institutional statistical arbitrage.

Author: StatArb_Gemini Architecture (Phase 4)
Date: October 23, 2025
Version: 2.0.0
"""

# Core Trading Engine
from .engine import EnhancedTradingEngine

# Strategy Management
from .strategies.manager import StrategyManager
from .strategies.base_strategy_enhanced import EnhancedBaseStrategy
from .strategies.strategy_registry import EnhancedStrategyRegistry
from .strategies.strategy_validator import EnhancedStrategyValidator
from .strategies.multi_strategy_coordinator import (
    MultiStrategySignalAggregator,
    SignalConflictResolver
)

# Portfolio Management
from .portfolio.manager_enhanced import EnhancedPortfolioManager
from .portfolio.cash_manager import CashManager

# Position Book (Single Source of Truth)
from .position_book import (
    PositionBook,
    IPositionBook,
    BookPosition,
    PositionUpdate,
    PortfolioSnapshot,
    Fill,
    FillSide,
    PositionSide,
    PositionStatus,
    PositionEventType,
)

# Execution
from .execution.execution_engine import ExecutionEngine

__all__ = [
    # Trading Engine
    'EnhancedTradingEngine',

    # Strategy Layer
    'StrategyManager',
    'EnhancedBaseStrategy',
    'EnhancedStrategyRegistry',
    'EnhancedStrategyValidator',
    'MultiStrategySignalAggregator',
    'SignalConflictResolver',

    # Portfolio Layer
    'EnhancedPortfolioManager',
    'CashManager',

    # Position Book (Single Source of Truth)
    'PositionBook',
    'IPositionBook',
    'BookPosition',
    'PositionUpdate',
    'PortfolioSnapshot',
    'Fill',
    'FillSide',
    'PositionSide',
    'PositionStatus',
    'PositionEventType',

    # Execution Layer
    'ExecutionEngine',
]

# Version info
__version__ = '2.0.0'
__author__ = 'StatArb_Gemini Architecture'

