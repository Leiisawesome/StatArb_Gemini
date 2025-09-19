"""
Canonical Type Definitions - Redirected to Messaging System
===========================================================

Phase 5D Infrastructure Consolidation - Types Module
All type definitions have been consolidated into the messaging system.

This module now serves as a redirect to maintain backward compatibility.
"""

from enum import Enum

# Define MarketDataType that components expect
class MarketDataType(Enum):
    """Market data type enumeration for component compatibility"""
    TICK = "tick"
    BAR = "bar"
    QUOTE = "quote"
    TRADE = "trade"

# Import all types from the consolidated messaging system
from core_structure.infrastructure.messaging.messaging_system import (
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
    # Market Data Types
    'MarketDataType',
    
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
