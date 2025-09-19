"""
Interfaces Module - Strategy and Component Interfaces
====================================================

This module contains all interface definitions and contracts for the UnifiedTradingEngine.
Defines the contracts that strategies and components must implement.

This is the foundational layer that ensures clean separation between strategy
contracts and implementations. All strategy classes in the unified system
extend from the base classes defined here.

Components:
- strategy_interfaces.py: Strategy interface definitions and base classes
- regime_interfaces.py: Regime detection interfaces (to avoid circular imports)

Integration:
- Used by core_structure/strategies/ for unified strategy system
- Provides StrategyInterface, BaseStrategy, StrategyFactory
- Enables consistent strategy behavior across the system

Author: Professional Trading System Architecture
Version: 3.0.0 (Updated for Consolidated Architecture)
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

# Regime Interfaces (to avoid circular imports)
from .regime_interfaces import (
    RegimeType,
    RegimeMetrics, 
    RegimeState,
    RegimeTransition,
    IRegimeSubscriber
)

__all__ = [
    'StrategyInterface',
    'BaseStrategy',
    'StrategyContext', 
    'StrategyMetrics',
    'StrategyFactory',
    'StrategyType',
    'StrategyError',
    'StrategyConfig',
    'RegimeType',
    'RegimeMetrics',
    'RegimeState', 
    'RegimeTransition',
    'IRegimeSubscriber'
]
