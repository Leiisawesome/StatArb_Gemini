"""Event-driven messaging system"""

"""
Unified Messaging and Type System
=================================

Phase 5D Infrastructure Consolidation - Messaging & Types Module
Consolidated messaging and type functionality into a unified system.

This module provides comprehensive messaging and type capabilities including:
- Event-driven message bus with pub/sub messaging
- Canonical type definitions eliminating duplicates
- Message routing and persistence
- Type safety across the entire system

Consolidated Components:
- messaging_system: Unified messaging and types (from message_bus + all types modules)

Legacy Support:
- Individual component imports maintained for backward compatibility
"""

# Phase 5D Consolidated System
from .messaging_system import (
    # Core Message Bus
    MessageBus,
    Message,
    MessageFactory,
    MessagingSystemFactory,
    
    # Type Enums
    OrderType,
    OrderSide, 
    OrderStatus,
    TimeInForce,
    ExecutionStrategy,
    MarketRegime,
    RegimeType,
    RegimeConfidence,
    StrategyType,
    AlertLevel,
    MessageType,
    
    # Data Classes
    Order,
    Fill,
    Position,
    RegimeInfo,
    StrategyConfig,
    PerformanceMetric
)

# Legacy backward compatibility imports
# Note: These now reference the consolidated modules
from .messaging_system import MessageBus, Message

__all__ = [
    # Core Message Bus
    'MessageBus',
    'Message',
    'MessageFactory',
    'MessagingSystemFactory',
    
    # Type Enums
    'OrderType',
    'OrderSide', 
    'OrderStatus',
    'TimeInForce',
    'ExecutionStrategy',
    'MarketRegime',
    'RegimeType',
    'RegimeConfidence',
    'StrategyType',
    'AlertLevel',
    'MessageType',
    
    # Data Classes
    'Order',
    'Fill',
    'Position',
    'RegimeInfo',
    'StrategyConfig',
    'PerformanceMetric'
] 