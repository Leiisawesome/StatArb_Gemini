"""
Unified Messaging and Type System for StatArb Trading System
===========================================================

Phase 5D Infrastructure Consolidation - Messaging & Types Module
Consolidates messaging and type functionality into a unified system.

Consolidated from:
- message_bus.py (257 lines) - Event-driven message bus system
- order_types.py (164 lines) - Canonical order type definitions
- market_types.py (94 lines) - Market regime and data types
- strategy_types.py (47 lines) - Strategy configuration types
- monitoring_types.py (30 lines) - Monitoring and alert types

This module provides comprehensive messaging and type capabilities including:
- Event-driven message bus with pub/sub messaging
- Canonical type definitions eliminating duplicates
- Message routing and persistence
- Type safety across the entire system
"""

import asyncio
import json
import logging
import threading
import uuid
from typing import Dict, List, Any, Callable, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from queue import Queue, Empty
import time

logger = logging.getLogger(__name__)

# =============================================================================
# Core Type Definitions
# =============================================================================

# Order Types (from order_types.py)
class OrderType(Enum):
    """Standard order types - canonical definition"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"
    HIDDEN = "hidden"

class OrderSide(Enum):
    """Order side (buy/sell) - canonical definition"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Order execution status - canonical definition"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class TimeInForce(Enum):
    """Time in force - canonical definition"""
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill

class ExecutionStrategy(Enum):
    """Execution strategies - canonical definition"""
    MARKET = "market"
    LIMIT = "limit"
    TWAP = "twap"  # Time-Weighted Average Price
    VWAP = "vwap"  # Volume-Weighted Average Price
    ICEBERG = "iceberg"  # Iceberg orders
    POV = "pov"  # Percentage of Volume

# Market Types (from market_types.py)
class MarketRegime(Enum):
    """Canonical market regime types - consolidates all implementations"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    MEAN_REVERTING = "mean_reverting"
    MOMENTUM = "momentum"
    UNKNOWN = "unknown"

class RegimeType(Enum):
    """Regime classification types"""
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"

class RegimeConfidence(Enum):
    """Confidence levels for regime detection"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# Strategy Types (from strategy_types.py)
class StrategyType(Enum):
    """Strategy types"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    ARBITRAGE = "arbitrage"
    CUSTOM = "custom"

# Monitoring Types (from monitoring_types.py)
class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class MessageType(Enum):
    """Message types for the message bus"""
    MARKET_DATA = "market_data"
    ORDER_EVENT = "order_event"
    SIGNAL = "signal"
    ALERT = "alert"
    STRATEGY_UPDATE = "strategy_update"
    PERFORMANCE_UPDATE = "performance_update"
    SYSTEM_STATUS = "system_status"
    AI_COMMUNICATION = "ai_communication"
    CONFIG_CHANGE = "config_change"
    REGIME_CHANGE = "regime_change"

# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Fill:
    """Order fill information - canonical definition"""
    fill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: float = 0.0
    price: float = 0.0
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    venue: str = "default"
    execution_id: str = ""
    
    @property
    def notional_value(self) -> float:
        """Notional value of fill"""
        return self.quantity * self.price
    
    @property
    def net_value(self) -> float:
        """Net value after commission"""
        return self.notional_value - self.commission

@dataclass
class Order:
    """Canonical order representation - consolidates all implementations"""
    # Basic order details
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    
    # Pricing
    price: Optional[float] = None
    limit_price: Optional[float] = None  # Alias for price
    stop_price: Optional[float] = None
    
    # Order management
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    time_in_force: TimeInForce = TimeInForce.DAY
    
    # Execution tracking
    execution_strategy: ExecutionStrategy = ExecutionStrategy.MARKET
    filled_quantity: float = 0.0
    remaining_quantity: Optional[float] = None
    average_fill_price: Optional[float] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Metadata
    strategy_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Fills
    fills: List[Fill] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize calculated fields"""
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
        if self.limit_price is None and self.price is not None:
            self.limit_price = self.price
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        """Check if order is active (can be filled)"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.ACKNOWLEDGED, OrderStatus.PARTIALLY_FILLED]
    
    def add_fill(self, fill: Fill) -> None:
        """Add a fill to this order"""
        self.fills.append(fill)
        self.filled_quantity += fill.quantity
        self.remaining_quantity = self.quantity - self.filled_quantity
        
        # Update average fill price
        if self.fills:
            total_value = sum(f.quantity * f.price for f in self.fills)
            total_quantity = sum(f.quantity for f in self.fills)
            self.average_fill_price = total_value / total_quantity if total_quantity > 0 else 0
        
        # Update status
        if self.remaining_quantity <= 0:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        self.updated_at = datetime.now()

@dataclass
class Position:
    """Trading position"""
    symbol: str
    quantity: float
    average_price: float
    market_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def market_value(self) -> float:
        """Current market value of position"""
        return self.quantity * self.market_price
    
    @property
    def unrealized_pnl(self) -> float:
        """Unrealized P&L"""
        return (self.market_price - self.average_price) * self.quantity
    
    @property
    def is_long(self) -> bool:
        """Check if position is long"""
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        """Check if position is short"""
        return self.quantity < 0

@dataclass
class RegimeInfo:
    """Market regime information"""
    regime: MarketRegime
    confidence: RegimeConfidence
    strength: float
    timestamp: datetime
    duration: timedelta
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StrategyConfig:
    """Strategy configuration"""
    name: str
    strategy_type: StrategyType
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    risk_limits: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

@dataclass
class PerformanceMetric:
    """Performance metric data"""
    name: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    alert_level: Optional[AlertLevel] = None

@dataclass
class Message:
    """Base message class for all events"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.SYSTEM_STATUS
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        return cls(**data)

# =============================================================================
# Message Bus System
# =============================================================================

class MessageBus:
    """
    Event-driven message bus for component communication
    Supports:
    - Pub/sub messaging with type safety
    - Message persistence and replay
    - Message routing and filtering
    - AI agent communication
    - Async and sync message handling
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        
        # Subscribers for different message types
        self._subscribers: Dict[MessageType, List[Callable]] = {}
        self._async_subscribers: Dict[MessageType, List[Callable]] = {}
        
        # Message queues for async processing
        self._queues: Dict[str, Queue] = {}
        self._processing_threads: Dict[str, threading.Thread] = {}
        
        # Message persistence
        self._message_history: List[Message] = []
        self._max_history = self.config.get('max_history_size', 1000)
        self._persist_messages = self.config.get('persist_messages', True)
        
        # Metrics and monitoring
        self._message_count = 0
        self._error_count = 0
        self._last_activity = datetime.now()
        
        # Message filters
        self._filters: List[Callable[[Message], bool]] = []
        
        # Thread safety
        self._lock = threading.RLock()
        self._running = True
        
        logger.info("MessageBus initialized with pub/sub and persistence")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            'max_history_size': 1000,
            'persist_messages': True,
            'max_queue_size': 10000,
            'worker_threads': 2,
            'message_timeout': 30.0,
            'enable_metrics': True
        }
    
    def subscribe(self, message_type: MessageType, callback: Callable[[Message], None]) -> str:
        """Subscribe to messages of a specific type"""
        with self._lock:
            if message_type not in self._subscribers:
                self._subscribers[message_type] = []
            
            self._subscribers[message_type].append(callback)
            subscriber_id = f"{message_type.value}_{len(self._subscribers[message_type])}"
            
            logger.info(f"Subscribed to {message_type.value} messages: {subscriber_id}")
            return subscriber_id
    
    def subscribe_async(self, message_type: MessageType, callback: Callable[[Message], Any]) -> str:
        """Subscribe to messages with async callback"""
        with self._lock:
            if message_type not in self._async_subscribers:
                self._async_subscribers[message_type] = []
            
            self._async_subscribers[message_type].append(callback)
            subscriber_id = f"{message_type.value}_async_{len(self._async_subscribers[message_type])}"
            
            logger.info(f"Subscribed to {message_type.value} messages (async): {subscriber_id}")
            return subscriber_id
    
    def unsubscribe(self, message_type: MessageType, callback: Callable) -> bool:
        """Unsubscribe from messages"""
        with self._lock:
            # Try sync subscribers
            if message_type in self._subscribers:
                try:
                    self._subscribers[message_type].remove(callback)
                    return True
                except ValueError:
                    pass
            
            # Try async subscribers
            if message_type in self._async_subscribers:
                try:
                    self._async_subscribers[message_type].remove(callback)
                    return True
                except ValueError:
                    pass
            
            return False
    
    def publish(self, message: Message) -> bool:
        """Publish message to all subscribers"""
        try:
            with self._lock:
                # Apply filters
                if not self._apply_filters(message):
                    return False
                
                # Store in history if enabled
                if self._persist_messages:
                    self._message_history.append(message)
                    if len(self._message_history) > self._max_history:
                        self._message_history = self._message_history[-self._max_history:]
                
                # Update metrics
                self._message_count += 1
                self._last_activity = datetime.now()
                
                # Notify sync subscribers
                success_count = 0
                if message.type in self._subscribers:
                    for callback in self._subscribers[message.type]:
                        try:
                            callback(message)
                            success_count += 1
                        except Exception as e:
                            logger.error(f"Error in sync subscriber callback: {e}")
                            self._error_count += 1
                
                # Notify async subscribers
                if message.type in self._async_subscribers:
                    for callback in self._async_subscribers[message.type]:
                        try:
                            # Schedule async callback
                            threading.Thread(
                                target=self._run_async_callback,
                                args=(callback, message),
                                daemon=True
                            ).start()
                            success_count += 1
                        except Exception as e:
                            logger.error(f"Error scheduling async callback: {e}")
                            self._error_count += 1
                
                return success_count > 0
                
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            self._error_count += 1
            return False
    
    def _run_async_callback(self, callback: Callable, message: Message) -> None:
        """Run async callback in thread"""
        try:
            if asyncio.iscoroutinefunction(callback):
                # Run coroutine in new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(callback(message))
                finally:
                    loop.close()
            else:
                callback(message)
        except Exception as e:
            logger.error(f"Error in async callback: {e}")
            self._error_count += 1
    
    def publish_dict(self, message_type: MessageType, payload: Dict[str, Any], 
                     source: str = "system", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Publish message from dictionary payload"""
        message = Message(
            type=message_type,
            payload=payload,
            source=source,
            metadata=metadata or {}
        )
        return self.publish(message)
    
    def add_filter(self, filter_func: Callable[[Message], bool]) -> None:
        """Add message filter"""
        with self._lock:
            self._filters.append(filter_func)
    
    def _apply_filters(self, message: Message) -> bool:
        """Apply all filters to message"""
        for filter_func in self._filters:
            try:
                if not filter_func(message):
                    return False
            except Exception as e:
                logger.error(f"Error in message filter: {e}")
        return True
    
    def get_message_history(self, message_type: Optional[MessageType] = None, 
                           limit: Optional[int] = None) -> List[Message]:
        """Get message history with optional filtering"""
        with self._lock:
            messages = self._message_history
            
            if message_type:
                messages = [m for m in messages if m.type == message_type]
            
            if limit:
                messages = messages[-limit:]
            
            return messages.copy()
    
    def replay_messages(self, subscriber: Callable[[Message], None], 
                       message_type: Optional[MessageType] = None,
                       since: Optional[datetime] = None) -> int:
        """Replay historical messages to a subscriber"""
        messages = self.get_message_history(message_type)
        
        if since:
            messages = [m for m in messages if m.timestamp >= since]
        
        replayed = 0
        for message in messages:
            try:
                subscriber(message)
                replayed += 1
            except Exception as e:
                logger.error(f"Error replaying message {message.id}: {e}")
        
        return replayed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        with self._lock:
            subscriber_counts = {
                msg_type.value: len(callbacks) 
                for msg_type, callbacks in self._subscribers.items()
            }
            
            async_subscriber_counts = {
                msg_type.value: len(callbacks)
                for msg_type, callbacks in self._async_subscribers.items()
            }
            
            return {
                'total_messages': self._message_count,
                'error_count': self._error_count,
                'history_size': len(self._message_history),
                'subscribers': subscriber_counts,
                'async_subscribers': async_subscriber_counts,
                'last_activity': self._last_activity.isoformat(),
                'running': self._running
            }
    
    def clear_history(self) -> None:
        """Clear message history"""
        with self._lock:
            self._message_history.clear()
            logger.info("Message history cleared")
    
    def shutdown(self) -> None:
        """Shutdown message bus"""
        with self._lock:
            self._running = False
            
            # Stop processing threads
            for thread in self._processing_threads.values():
                if thread.is_alive():
                    thread.join(timeout=5)
            
            logger.info("MessageBus shutdown complete")

    # Compatibility shims for examples/tests that await these methods
    async def start(self) -> None:
        """Async start compatibility method - MessageBus starts automatically in __init__"""
        # MessageBus is ready to use immediately after initialization
        # This is a compatibility shim for examples/tests that call await message_bus.start()
        logger.debug("MessageBus.start() called (compatibility shim)")
        pass
    
    async def stop(self) -> None:
        """Async stop compatibility method - calls shutdown()"""
        # Delegate to existing shutdown method
        logger.debug("MessageBus.stop() called (compatibility shim)")
        self.shutdown()


# =============================================================================
# Specialized Message Factories
# =============================================================================

class MessageFactory:
    """Factory for creating specialized messages"""
    
    @staticmethod
    def create_order_event(order: Order, event_type: str, source: str = "order_manager") -> Message:
        """Create order event message"""
        return Message(
            type=MessageType.ORDER_EVENT,
            payload={
                'order_id': order.order_id,
                'symbol': order.symbol,
                'side': order.side.value,
                'event_type': event_type,
                'status': order.status.value,
                'order': asdict(order)
            },
            source=source,
            metadata={'event_type': event_type}
        )
    
    @staticmethod
    def create_signal_message(symbol: str, signal_type: str, strength: float, 
                             strategy: str, source: str = "signal_generator") -> Message:
        """Create trading signal message"""
        return Message(
            type=MessageType.SIGNAL,
            payload={
                'symbol': symbol,
                'signal_type': signal_type,
                'strength': strength,
                'strategy': strategy
            },
            source=source,
            metadata={'signal_type': signal_type, 'strategy': strategy}
        )
    
    @staticmethod
    def create_alert_message(level: AlertLevel, message_text: str, 
                           component: str, source: str = "monitoring") -> Message:
        """Create alert message"""
        return Message(
            type=MessageType.ALERT,
            payload={
                'level': level.value,
                'message': message_text,
                'component': component
            },
            source=source,
            metadata={'alert_level': level.value, 'component': component}
        )
    
    @staticmethod
    def create_regime_change_message(old_regime: MarketRegime, new_regime: MarketRegime,
                                   confidence: RegimeConfidence, source: str = "regime_detector") -> Message:
        """Create regime change message"""
        return Message(
            type=MessageType.REGIME_CHANGE,
            payload={
                'old_regime': old_regime.value,
                'new_regime': new_regime.value,
                'confidence': confidence.value
            },
            source=source,
            metadata={'regime_change': True}
        )
    
    @staticmethod
    def create_performance_update(metrics: Dict[str, float], strategy: str,
                                source: str = "performance_tracker") -> Message:
        """Create performance update message"""
        return Message(
            type=MessageType.PERFORMANCE_UPDATE,
            payload={
                'metrics': metrics,
                'strategy': strategy
            },
            source=source,
            metadata={'strategy': strategy}
        )


# =============================================================================
# Message Bus Factory
# =============================================================================

class MessagingSystemFactory:
    """Factory for creating messaging system components"""
    
    @staticmethod
    def create_production_message_bus() -> MessageBus:
        """Create message bus for production environment"""
        config = {
            'max_history_size': 10000,
            'persist_messages': True,
            'max_queue_size': 50000,
            'worker_threads': 4,
            'message_timeout': 60.0,
            'enable_metrics': True
        }
        return MessageBus(config)
    
    @staticmethod
    def create_development_message_bus() -> MessageBus:
        """Create message bus for development environment"""
        config = {
            'max_history_size': 1000,
            'persist_messages': False,
            'max_queue_size': 5000,
            'worker_threads': 1,
            'message_timeout': 10.0,
            'enable_metrics': False
        }
        return MessageBus(config)


# =============================================================================
# Module Exports
# =============================================================================

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
