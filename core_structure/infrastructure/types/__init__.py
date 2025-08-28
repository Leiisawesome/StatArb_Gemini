"""
Canonical Type Definitions - Redirected to Messaging System
===========================================================

Phase 5D Infrastructure Consolidation - Types Module
All type definitions have been consolidated into the messaging system.

This module now serves as a redirect to maintain backward compatibility.
"""

# Import all types from the consolidated messaging system
from ..messaging.messaging_system import (
    # Order Types
    OrderType,
    OrderSide,
    OrderStatus,
    TimeInForce,
    ExecutionStrategy,
    Order,
    Fill,
    Position,
    
    # Market Types
    MarketRegime,
    RegimeType,
    RegimeConfidence,
    RegimeInfo,
    
    # Strategy Types
    StrategyType,
    StrategyConfig,
    
    # Monitoring Types
    AlertLevel,
    PerformanceMetric
)

__all__ = [
    # Order Types
    'OrderType',
    'OrderSide', 
    'OrderStatus',
    'TimeInForce',
    'ExecutionStrategy',
    'Order',
    'Fill',
    'Position',
    
    # Market Types
    'MarketRegime',
    'RegimeType',
    'RegimeConfidence', 
    'RegimeInfo',
    
    # Strategy Types
    'StrategyType',
    'StrategyConfig',
    
    # Monitoring Types
    'AlertLevel',
    'PerformanceMetric'
]
