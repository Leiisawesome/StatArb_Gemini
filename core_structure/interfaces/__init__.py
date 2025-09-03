"""
Interfaces Module - Strategy and Component Interfaces
====================================================

This module contains all interface definitions and contracts for the UnifiedTradingEngine.
Defines the contracts that strategies and components must implement.

Components:
- strategy_interfaces.py: Strategy interface definitions and base classes

Author: Professional Trading System Architecture
Version: PRODUCTION (Reorganized)
"""

# Strategy Interfaces
from .strategy_interfaces import (
    StrategyInterface, 
    BaseStrategy, 
    StrategyContext, 
    StrategyMetrics,
    StrategyFactory,
    StrategyType,
    StrategyError,
    StrategyConfig
)

__all__ = [
    'StrategyInterface',
    'BaseStrategy',
    'StrategyContext', 
    'StrategyMetrics',
    'StrategyFactory',
    'StrategyType',
    'StrategyError',
    'StrategyConfig'
]
