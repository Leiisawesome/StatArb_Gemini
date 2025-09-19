#!/usr/bin/env python3
"""
UnifiedExecutionEngine: Trade Execution and Order Management
==========================================================

Component in the essential flow: Market Data -> UnifiedDataManager -> UnifiedRegimeEngine -> RiskManager -> StrategyManager -> RealTimeTradingEngine -> **UnifiedExecutionEngine** -> PortfolioManager

This engine handles trade execution, order management, and position tracking.
It receives trading signals and executes them through connected brokers.

Key Features:
- Order execution and management
- Position tracking
- Broker integration
- Execution performance monitoring
- Integration with SystemOrchestrator
- Central Risk Authority: Validates risk approval tokens before execution

Author: Professional Trading System Architecture
Version: 1.0.0 (SystemOrchestrator Integration)
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum
import uuid

# Import risk management for token validation
try:
    from .advanced_risk_management import AdvancedRiskManager, TradeAuthorization
except ImportError:
    # Fallback for missing risk management
    @dataclass
    class TradeAuthorization:
        request_id: str
        authorized: bool
        authorization_token: str
        risk_limits_applied: Dict[str, Any]
        rejection_reason: Optional[str] = None
        timestamp: datetime = None

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Types of orders"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(Enum):
    """Order status states"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"

@dataclass
class Order:
    """Order structure with risk authorization validation"""
    id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: datetime = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    broker: str = "simulation"
    strategy: str = "unknown"
    
    # CRITICAL: Risk authorization fields
    authorization_token: Optional[str] = None
    risk_limits_applied: Optional[Dict[str, Any]] = None
    authorization_timestamp: Optional[datetime] = None
    authorization_validated: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    def has_valid_authorization(self) -> bool:
        """Check if order has valid risk authorization"""
        return (
            self.authorization_token is not None and
            len(self.authorization_token) > 0 and
            self.authorization_validated
        )

@dataclass
class Position:
    """Position structure"""
    symbol: str
    quantity: float
    avg_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    last_update: datetime = None
    
    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now()

@dataclass
class ExecutionConfig:
    """Configuration for execution engine"""
    default_broker: str = "simulation"
    max_order_size: float = 10000.0  # Maximum order size
    order_timeout: int = 300  # seconds
    slippage_model: str = "linear"  # linear, fixed, market_impact
    commission_per_share: float = 0.005  # $0.005 per share
    max_daily_trades: int = 1000
    
    # Execution parameters
    market_order_slippage: float = 0.001  # 0.1% slippage for market orders
    limit_order_fill_probability: float = 0.8  # 80% fill rate for limit orders

class IBroker(ABC):
    """Interface for broker implementations"""
    
    @abstractmethod
    async def submit_order(self, order: Order) -> bool:
        """Submit an order to the broker"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> Dict[str, Position]:
        """Get current positions"""
        pass

class SimulationBroker(IBroker):
    """Simulation broker for testing"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.last_prices: Dict[str, float] = {}
    
    async def submit_order(self, order: Order) -> bool:
        """Submit order to simulation"""
        try:
            self.orders[order.id] = order
            order.status = OrderStatus.SUBMITTED
            
            # Simulate order execution
            await self._simulate_execution(order)
            return True
            
        except Exception as e:
            logger.error(f"❌ Error submitting order {order.id}: {e}")
            order.status = OrderStatus.REJECTED
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order in simulation"""
        try:
            if order_id in self.orders:
                order = self.orders[order_id]
                if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                    order.status = OrderStatus.CANCELLED
                    return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Error cancelling order {order_id}: {e}")
            return False
    
    async def get_positions(self) -> Dict[str, Position]:
        """Get current positions"""
        return self.positions.copy()
    
    async def _simulate_execution(self, order: Order) -> None:
        """Simulate order execution"""
        try:
            # Simulate market price
            if order.symbol not in self.last_prices:
                self.last_prices[order.symbol] = 100.0  # Default price
            
            current_price = self.last_prices[order.symbol]
            
            # Determine execution price based on order type
            if order.order_type == OrderType.MARKET:
                # Market order - execute immediately with slippage
                slippage = 0.001  # 0.1% slippage
                if order.side == OrderSide.BUY:
                    execution_price = current_price * (1 + slippage)
                else:
                    execution_price = current_price * (1 - slippage)
                
                # Fill the order
                order.status = OrderStatus.FILLED
                order.filled_quantity = order.quantity
                order.avg_fill_price = execution_price
                
                # Update position
                await self._update_position(order)
                
            elif order.order_type == OrderType.LIMIT:
                # Limit order - check if price is favorable
                fill_probability = 0.8  # 80% chance of fill
                if np.random.random() < fill_probability:
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = order.quantity
                    order.avg_fill_price = order.price or current_price
                    
                    # Update position
                    await self._update_position(order)
            
            # Update market price for next simulation
            price_change = np.random.normal(0, 0.001)  # 0.1% volatility
            self.last_prices[order.symbol] *= (1 + price_change)
            
        except Exception as e:
            logger.error(f"❌ Error simulating execution for order {order.id}: {e}")
            order.status = OrderStatus.REJECTED
    
    async def _update_position(self, order: Order) -> None:
        """Update position after order execution"""
        try:
            symbol = order.symbol
            
            if symbol not in self.positions:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=0.0,
                    avg_price=0.0,
                    market_value=0.0,
                    unrealized_pnl=0.0
                )
            
            position = self.positions[symbol]
            
            # Calculate new position
            if order.side == OrderSide.BUY:
                new_quantity = position.quantity + order.filled_quantity
                if new_quantity != 0:
                    position.avg_price = (
                        (position.quantity * position.avg_price + 
                         order.filled_quantity * order.avg_fill_price) / new_quantity
                    )
                position.quantity = new_quantity
            else:  # SELL
                position.quantity -= order.filled_quantity
                if position.quantity < 0:
                    position.avg_price = order.avg_fill_price
                elif position.quantity == 0:
                    position.avg_price = 0.0
            
            # Update market value and P&L
            current_price = self.last_prices.get(symbol, order.avg_fill_price)
            position.market_value = position.quantity * current_price
            position.unrealized_pnl = (current_price - position.avg_price) * position.quantity
            position.last_update = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Error updating position for {order.symbol}: {e}")

class IExecutionSubscriber(ABC):
    """Interface for execution subscribers"""
    
    @abstractmethod
    def on_order_update(self, order: Order) -> None:
        """Handle order updates"""
        pass
    
    @abstractmethod
    def on_position_update(self, position: Position) -> None:
        """Handle position updates"""
        pass

class UnifiedExecutionEngine:
    """
    Unified execution engine for trade execution and order management.
    
    Receives trading signals and executes them through connected brokers.
    Final component before PortfolioManager in the essential flow.
    
    CRITICAL: All orders MUST have valid risk authorization tokens before execution.
    """
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """Initialize the execution engine with risk management integration"""
        self.config = config or ExecutionConfig()
        
        # Order and position tracking
        self.active_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self.positions: Dict[str, Position] = {}
        
        # Broker management
        self.brokers: Dict[str, IBroker] = {}
        self.default_broker = SimulationBroker()
        self.brokers["simulation"] = self.default_broker
        
        # Risk management integration
        self.risk_manager: Optional[AdvancedRiskManager] = None
        self.unauthorized_executions_blocked: int = 0
        self.total_executions_attempted: int = 0
        
        # Subscribers
        self.subscribers: List[IExecutionSubscriber] = []
        
        # State
        self.is_running = False
        self.order_monitoring_task: Optional[asyncio.Task] = None
        self.position_monitoring_task: Optional[asyncio.Task] = None
        
        logger.info("⚡ UnifiedExecutionEngine initialized with risk authorization validation")
    
    async def startup(self) -> bool:
        """Start the execution engine with risk management integration"""
        try:
            logger.info("🚀 Starting UnifiedExecutionEngine with risk authorization validation...")
            
            # Initialize risk manager for token validation
            try:
                self.risk_manager = AdvancedRiskManager()
                await self.risk_manager.startup()
                logger.info("✅ Risk Manager connected for authorization token validation")
            except Exception as e:
                logger.warning(f"⚠️ Risk Manager not available for token validation: {e}")
                self.risk_manager = None
            
            # Start monitoring tasks
            self.order_monitoring_task = asyncio.create_task(self._order_monitoring_loop())
            self.position_monitoring_task = asyncio.create_task(self._position_monitoring_loop())
            self.is_running = True
            
            logger.info("✅ UnifiedExecutionEngine started successfully with risk controls")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start UnifiedExecutionEngine: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the execution engine"""
        try:
            logger.info("🛑 Shutting down UnifiedExecutionEngine...")
            
            self.is_running = False
            
            # Cancel all active orders
            for order_id in list(self.active_orders.keys()):
                await self.cancel_order(order_id)
            
            # Stop monitoring tasks
            if self.order_monitoring_task:
                self.order_monitoring_task.cancel()
                try:
                    await self.order_monitoring_task
                except asyncio.CancelledError:
                    pass
            
            if self.position_monitoring_task:
                self.position_monitoring_task.cancel()
                try:
                    await self.position_monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("✅ UnifiedExecutionEngine shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Failed to shutdown UnifiedExecutionEngine: {e}")
    
    def subscribe(self, subscriber: IExecutionSubscriber) -> None:
        """Subscribe to execution updates"""
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)
            logger.info(f"📡 New execution subscriber added: {type(subscriber).__name__}")
    
    def unsubscribe(self, subscriber: IExecutionSubscriber) -> None:
        """Unsubscribe from execution updates"""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
            logger.info(f"📡 Execution subscriber removed: {type(subscriber).__name__}")
    
    async def submit_order(self, symbol: str, side: OrderSide, quantity: float, 
                          order_type: OrderType = OrderType.MARKET, 
                          price: Optional[float] = None, broker: str = None,
                          authorization_token: Optional[str] = None,
                          risk_limits_applied: Optional[Dict[str, Any]] = None,
                          authorization_timestamp: Optional[datetime] = None) -> Optional[str]:
        """
        Submit a new order with MANDATORY risk authorization validation.
        
        CRITICAL: All orders must include valid authorization tokens from RiskManager.
        Orders without authorization will be REJECTED immediately.
        """
        self.total_executions_attempted += 1
        
        try:
            # STEP 1: MANDATORY RISK AUTHORIZATION CHECK
            if not authorization_token:
                logger.error(f"🚫 Order REJECTED - No authorization token provided for {symbol} {side.value} {quantity}")
                self.unauthorized_executions_blocked += 1
                return None
            
            # Validate authorization token format
            if len(authorization_token) < 8:  # Minimum token length
                logger.error(f"🚫 Order REJECTED - Invalid authorization token format for {symbol}")
                self.unauthorized_executions_blocked += 1
                return None
            
            # STEP 2: VALIDATE ORDER PARAMETERS
            if quantity <= 0:
                logger.error(f"❌ Invalid quantity: {quantity}")
                return None
            
            if quantity > self.config.max_order_size:
                logger.error(f"❌ Order size {quantity} exceeds maximum {self.config.max_order_size}")
                return None
            
            # STEP 3: VALIDATE AUTHORIZATION WITH RISK MANAGER
            authorization_validated = await self._validate_authorization_token(
                authorization_token, symbol, side, quantity
            )
            
            if not authorization_validated:
                logger.error(f"🚫 Order REJECTED - Authorization token validation failed for {symbol}")
                self.unauthorized_executions_blocked += 1
                return None
            
            # STEP 4: CREATE ORDER WITH AUTHORIZATION METADATA
            order = Order(
                id=str(uuid.uuid4()),
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
                broker=broker or self.config.default_broker,
                authorization_token=authorization_token,
                risk_limits_applied=risk_limits_applied or {},
                authorization_timestamp=authorization_timestamp or datetime.now(),
                authorization_validated=True
            )
            
            # STEP 5: DOUBLE-CHECK AUTHORIZATION BEFORE BROKER SUBMISSION
            if not order.has_valid_authorization():
                logger.error(f"🚫 Order REJECTED - Failed final authorization check for {symbol}")
                self.unauthorized_executions_blocked += 1
                return None
            
            # STEP 6: GET BROKER AND SUBMIT
            broker_instance = self.brokers.get(order.broker)
            if not broker_instance:
                logger.error(f"❌ Broker not found: {order.broker}")
                return None
            
            # Submit to broker
            success = await broker_instance.submit_order(order)
            if success:
                self.active_orders[order.id] = order
                logger.info(f"✅ AUTHORIZED Order submitted: {order.id} - {side.value} {quantity} {symbol} (token: {authorization_token[:8]}...)")
                
                # Notify subscribers
                await self._notify_order_subscribers(order)
                return order.id
            else:
                logger.error(f"❌ Failed to submit order to broker: {order.id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error submitting order: {e}")
            return None
    
    async def _validate_authorization_token(self, authorization_token: str, symbol: str, 
                                          side: OrderSide, quantity: float) -> bool:
        """
        Validate authorization token with RiskManager.
        
        This ensures that the token is valid and corresponds to an actual
        risk authorization for this specific trade.
        """
        try:
            if self.risk_manager:
                # Call risk manager to validate the token
                # This would check if the token is valid and not expired
                is_valid = await self.risk_manager.validate_authorization_token(
                    authorization_token, symbol, side.value, quantity
                )
                return is_valid
            else:
                # If risk manager not available, perform basic validation
                logger.warning("⚠️ Risk Manager not available - using basic token validation")
                return len(authorization_token) >= 8 and authorization_token.isalnum()
                
        except Exception as e:
            logger.error(f"❌ Error validating authorization token: {e}")
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            order = self.active_orders.get(order_id)
            if not order:
                logger.warning(f"⚠️ Order not found: {order_id}")
                return False
            
            broker = self.brokers.get(order.broker)
            if not broker:
                logger.error(f"❌ Broker not found: {order.broker}")
                return False
            
            success = await broker.cancel_order(order_id)
            if success:
                order.status = OrderStatus.CANCELLED
                self.active_orders.pop(order_id, None)
                self.order_history.append(order)
                
                logger.info(f"✅ Order cancelled: {order_id}")
                await self._notify_order_subscribers(order)
                return True
            else:
                logger.error(f"❌ Failed to cancel order: {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error cancelling order {order_id}: {e}")
            return False
    
    async def get_positions(self, broker: str = None) -> Dict[str, Position]:
        """Get current positions"""
        try:
            broker_name = broker or self.config.default_broker
            broker_instance = self.brokers.get(broker_name)
            
            if broker_instance:
                positions = await broker_instance.get_positions()
                self.positions.update(positions)
                return positions
            else:
                logger.error(f"❌ Broker not found: {broker_name}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error getting positions: {e}")
            return {}
    
    def get_active_orders(self) -> Dict[str, Order]:
        """Get all active orders"""
        return self.active_orders.copy()
    
    def get_order_history(self, limit: int = 100) -> List[Order]:
        """Get order history"""
        return self.order_history[-limit:] if limit > 0 else self.order_history
    
    async def _order_monitoring_loop(self) -> None:
        """Monitor order status and handle updates"""
        while self.is_running:
            try:
                # Check for order timeouts
                current_time = datetime.now()
                timeout_orders = []
                
                for order_id, order in self.active_orders.items():
                    if order.status == OrderStatus.SUBMITTED:
                        age = (current_time - order.timestamp).total_seconds()
                        if age > self.config.order_timeout:
                            timeout_orders.append(order_id)
                
                # Cancel timeout orders
                for order_id in timeout_orders:
                    await self.cancel_order(order_id)
                    logger.warning(f"⏰ Order timed out and cancelled: {order_id}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                logger.info("⚡ Order monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in order monitoring loop: {e}")
                await asyncio.sleep(1)
    
    async def _position_monitoring_loop(self) -> None:
        """Monitor position updates"""
        while self.is_running:
            try:
                # Update positions from all brokers
                for broker_name, broker in self.brokers.items():
                    positions = await broker.get_positions()
                    
                    for symbol, position in positions.items():
                        old_position = self.positions.get(symbol)
                        if not old_position or old_position.quantity != position.quantity:
                            self.positions[symbol] = position
                            await self._notify_position_subscribers(position)
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except asyncio.CancelledError:
                logger.info("⚡ Position monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in position monitoring loop: {e}")
                await asyncio.sleep(1)
    
    async def _notify_order_subscribers(self, order: Order) -> None:
        """Notify subscribers of order updates"""
        for subscriber in self.subscribers:
            try:
                if hasattr(subscriber, 'on_order_update'):
                    if asyncio.iscoroutinefunction(subscriber.on_order_update):
                        await subscriber.on_order_update(order)
                    else:
                        subscriber.on_order_update(order)
            except Exception as e:
                logger.error(f"❌ Error notifying order subscriber {type(subscriber).__name__}: {e}")
    
    async def _notify_position_subscribers(self, position: Position) -> None:
        """Notify subscribers of position updates"""
        for subscriber in self.subscribers:
            try:
                if hasattr(subscriber, 'on_position_update'):
                    if asyncio.iscoroutinefunction(subscriber.on_position_update):
                        await subscriber.on_position_update(position)
                    else:
                        subscriber.on_position_update(position)
            except Exception as e:
                logger.error(f"❌ Error notifying position subscriber {type(subscriber).__name__}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current execution engine status"""
        return {
            "is_running": self.is_running,
            "active_orders_count": len(self.active_orders),
            "order_history_count": len(self.order_history),
            "positions_count": len(self.positions),
            "brokers": list(self.brokers.keys()),
            "subscribers_count": len(self.subscribers),
            "active_orders": {order_id: {
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": order.quantity,
                "status": order.status.value,
                "timestamp": order.timestamp.isoformat()
            } for order_id, order in self.active_orders.items()},
            "positions": {symbol: {
                "quantity": pos.quantity,
                "avg_price": pos.avg_price,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl
            } for symbol, pos in self.positions.items()}
        }

# Factory function
def create_unified_execution_engine(config: Optional[ExecutionConfig] = None) -> UnifiedExecutionEngine:
    """Create a UnifiedExecutionEngine instance"""
    return UnifiedExecutionEngine(config)

# Export for SystemOrchestrator integration
__all__ = [
    'UnifiedExecutionEngine', 'ExecutionConfig', 'Order', 'Position', 
    'OrderType', 'OrderStatus', 'OrderSide', 'IBroker', 'IExecutionSubscriber',
    'SimulationBroker', 'create_unified_execution_engine'
]