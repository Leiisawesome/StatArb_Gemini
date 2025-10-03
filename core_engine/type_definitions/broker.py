"""
Core Engine Broker Types

Lightweight broker interfaces for standalone core_engine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from .orders import Order, OrderStatus, ExecutionResult


class BrokerType(Enum):
    """Broker type enumeration"""
    PAPER = "paper"  # Paper trading
    INTERACTIVE_BROKERS = "ib"
    ALPACA = "alpaca"
    TD_AMERITRADE = "td"
    CUSTOM = "custom"


@dataclass
class BrokerConfig:
    """Broker configuration"""
    broker_type: BrokerType
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    base_url: Optional[str] = None
    paper_trading: bool = True
    
    # Trading settings
    default_commission: float = 0.001  # 0.1%
    min_commission: float = 1.0  # Minimum $1
    max_commission: float = 100.0  # Maximum $100
    
    # Execution settings
    timeout_seconds: int = 30
    retry_attempts: int = 3
    partial_fills_allowed: bool = True


class BrokerInterface(ABC):
    """Abstract broker interface"""
    
    def __init__(self, config: BrokerConfig):
        self.config = config
        self.connected = False
        self.orders: Dict[str, Order] = {}
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to broker"""
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from broker"""
    
    @abstractmethod
    def submit_order(self, order: Order) -> bool:
        """Submit order to broker"""
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get order status"""
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
    
    @abstractmethod
    def get_positions(self) -> Dict[str, float]:
        """Get current positions"""


class PaperBroker(BrokerInterface):
    """Paper trading broker implementation"""
    
    def __init__(self, config: BrokerConfig):
        super().__init__(config)
        self.cash = 100000.0  # Starting cash
        self.positions: Dict[str, float] = {}
        self.order_callbacks: List[Callable[[ExecutionResult], None]] = []
        self.commission_paid = 0.0
    
    def connect(self) -> bool:
        """Connect to paper broker (always succeeds)"""
        self.connected = True
        return True
    
    def disconnect(self):
        """Disconnect from paper broker"""
        self.connected = False
    
    def submit_order(self, order: Order) -> bool:
        """Submit order to paper broker"""
        if not self.connected:
            return False
        
        # Store order
        self.orders[order.order_id] = order
        order.status = OrderStatus.SUBMITTED
        
        # Simulate immediate execution for market orders
        if order.order_type.value == "market":
            return self._execute_order(order)
        
        # For other order types, mark as pending
        order.status = OrderStatus.PENDING
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                order.status = OrderStatus.CANCELLED
                return True
        return False
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get order status"""
        if order_id in self.orders:
            return self.orders[order_id].status
        return None
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get paper account information"""
        total_position_value = sum(abs(qty * 100) for qty in self.positions.values())  # Assume $100 per share
        
        return {
            'cash': self.cash,
            'total_value': self.cash + total_position_value,
            'buying_power': self.cash,
            'positions': self.positions.copy(),
            'commission_paid': self.commission_paid,
            'broker_type': self.config.broker_type.value
        }
    
    def get_positions(self) -> Dict[str, float]:
        """Get current positions"""
        return self.positions.copy()
    
    def add_execution_callback(self, callback: Callable[[ExecutionResult], None]):
        """Add callback for order executions"""
        self.order_callbacks.append(callback)
    
    def _execute_order(self, order: Order) -> bool:
        """Execute order in paper trading"""
        try:
            # Calculate commission
            commission = max(
                self.config.min_commission,
                min(self.config.max_commission, 
                    abs(order.quantity * (order.price or 100)) * self.config.default_commission)
            )
            
            # Check if we have enough cash for buys
            if order.side.value == "buy":
                total_cost = order.quantity * (order.price or 100) + commission
                if self.cash < total_cost:
                    order.status = OrderStatus.REJECTED
                    return False
            
            # Execute trade
            execution_price = order.price or 100  # Default price for market orders
            
            # Update positions
            current_position = self.positions.get(order.symbol, 0.0)
            if order.side.value == "buy":
                self.positions[order.symbol] = current_position + order.quantity
                self.cash -= order.quantity * execution_price + commission
            else:  # sell
                self.positions[order.symbol] = current_position - order.quantity
                self.cash += order.quantity * execution_price - commission
            
            # Remove position if zero
            if abs(self.positions.get(order.symbol, 0)) < 1e-8:
                self.positions.pop(order.symbol, None)
            
            # Update order
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_price = execution_price
            order.commission = commission
            
            self.commission_paid += commission
            
            # Create execution result
            execution = ExecutionResult(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                commission=commission,
                success=True
            )
            
            # Notify callbacks
            for callback in self.order_callbacks:
                callback(execution)
            
            return True
            
        except Exception as e:
            order.status = OrderStatus.REJECTED
            return False
    
    def set_cash(self, cash: float):
        """Set available cash (for testing)"""
        self.cash = cash
    
    def set_position(self, symbol: str, quantity: float):
        """Set position (for testing)"""
        if abs(quantity) < 1e-8:
            self.positions.pop(symbol, None)
        else:
            self.positions[symbol] = quantity


class BrokerManager:
    """Broker manager for multiple broker connections"""
    
    def __init__(self):
        self.brokers: Dict[str, BrokerInterface] = {}
        self.default_broker: Optional[str] = None
    
    def add_broker(self, name: str, broker: BrokerInterface, set_as_default: bool = False):
        """Add broker connection"""
        self.brokers[name] = broker
        
        if set_as_default or self.default_broker is None:
            self.default_broker = name
    
    def get_broker(self, name: Optional[str] = None) -> Optional[BrokerInterface]:
        """Get broker by name or default"""
        if name is None:
            name = self.default_broker
        
        return self.brokers.get(name) if name else None
    
    def connect_all(self) -> Dict[str, bool]:
        """Connect all brokers"""
        results = {}
        for name, broker in self.brokers.items():
            results[name] = broker.connect()
        return results
    
    def disconnect_all(self):
        """Disconnect all brokers"""
        for broker in self.brokers.values():
            broker.disconnect()
    
    def submit_order(self, order: Order, broker_name: Optional[str] = None) -> bool:
        """Submit order through specific or default broker"""
        broker = self.get_broker(broker_name)
        if broker and broker.connected:
            return broker.submit_order(order)
        return False
    
    def get_all_positions(self) -> Dict[str, Dict[str, float]]:
        """Get positions from all brokers"""
        all_positions = {}
        for name, broker in self.brokers.items():
            if broker.connected:
                all_positions[name] = broker.get_positions()
        return all_positions
    
    def get_consolidated_positions(self) -> Dict[str, float]:
        """Get consolidated positions across all brokers"""
        consolidated = {}
        
        for broker in self.brokers.values():
            if broker.connected:
                positions = broker.get_positions()
                for symbol, quantity in positions.items():
                    consolidated[symbol] = consolidated.get(symbol, 0) + quantity
        
        # Remove zero positions
        return {k: v for k, v in consolidated.items() if abs(v) > 1e-8}