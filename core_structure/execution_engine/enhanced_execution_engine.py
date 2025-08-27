"""
Enhanced Unified Execution Management System
==========================================

Professional execution management system consolidating all execution functionality.
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import uuid

# Use canonical types to eliminate duplicates
from ..infrastructure import OrderType, OrderSide, OrderStatus, ExecutionStrategy, Order

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """Execution status enumeration"""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

@dataclass
class ExecutionRequest:
    """Request for trade execution"""
    symbol: str
    side: OrderSide
    quantity: float
    strategy: ExecutionStrategy = ExecutionStrategy.MARKET
    target_price: Optional[float] = None
    time_limit: Optional[int] = None  # Minutes
    max_participation: float = 0.2  # 20% max participation
    urgency: str = "NORMAL"  # HIGH, NORMAL, LOW
    strategy_id: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Auto-generated fields
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ExecutionResult:
    """Result of execution request"""
    request_id: str
    status: ExecutionStatus
    symbol: str
    side: OrderSide
    requested_quantity: float
    executed_quantity: float = 0.0
    remaining_quantity: float = 0.0
    average_price: float = 0.0
    total_cost: float = 0.0
    
    # Execution details
    orders: List[Order] = field(default_factory=list)
    execution_time: float = 0.0
    strategy_used: ExecutionStrategy = ExecutionStrategy.MARKET
    
    # Quality metrics
    implementation_shortfall: float = 0.0
    market_impact: float = 0.0
    timing_cost: float = 0.0
    
    # Error handling
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived fields"""
        self.remaining_quantity = self.requested_quantity - self.executed_quantity
        if self.orders:
            total_value = sum(order.filled_quantity * order.avg_fill_price 
                            for order in self.orders if order.filled_quantity > 0)
            total_quantity = sum(order.filled_quantity for order in self.orders)
            
            if total_quantity > 0:
                self.average_price = total_value / total_quantity
                self.executed_quantity = total_quantity
    
    @property
    def fill_rate(self) -> float:
        """Percentage of order filled"""
        if self.requested_quantity == 0:
            return 0.0
        return (self.executed_quantity / self.requested_quantity) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete"""
        return self.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, 
                              ExecutionStatus.REJECTED, ExecutionStatus.CANCELLED]

@dataclass
class ExecutionMetrics:
    """Comprehensive execution quality metrics"""
    total_executions: int = 0
    successful_executions: int = 0
    average_fill_rate: float = 0.0
    average_implementation_shortfall: float = 0.0
    average_market_impact: float = 0.0
    average_execution_time: float = 0.0
    total_transaction_costs: float = 0.0
    
    # Strategy performance
    strategy_performance: Dict[ExecutionStrategy, Dict[str, float]] = field(default_factory=dict)
    
    # Venue performance
    venue_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)

class OrderManager:
    """Enhanced order management system"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.available_capital = initial_capital
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self.execution_callbacks: List[Callable] = []
        self.risk_callbacks: List[Callable] = []
        
        # Order tracking
        self.pending_orders: List[Order] = []
        self.filled_orders: List[Order] = []
        self.cancelled_orders: List[Order] = []
        
        logger.info(f"Initialized OrderManager with ${initial_capital:,.2f} capital")
    
    def add_execution_callback(self, callback: Callable):
        """Add callback for order execution events"""
        self.execution_callbacks.append(callback)
        logger.info(f"Added execution callback: {callback.__name__}")
    
    def add_risk_callback(self, callback: Callable):
        """Add callback for risk management events"""
        self.risk_callbacks.append(callback)
        logger.info(f"Added risk callback: {callback.__name__}")
    
    def create_order(self, symbol: str, side: OrderSide, quantity: int,
                    order_type: OrderType = OrderType.MARKET,
                    limit_price: Optional[float] = None, stop_price: Optional[float] = None) -> Order:
        """Create a new order"""
        
        # Validate order parameters
        if quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}")
        
        if order_type == OrderType.LIMIT and limit_price is None:
            raise ValueError("Limit price required for LIMIT orders")
        
        if order_type == OrderType.STOP and stop_price is None:
            raise ValueError("Stop price required for STOP orders")
        
        # Create order
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price
        )
        
        # Store order
        self.orders[order.order_id] = order
        self.pending_orders.append(order)
        
        logger.info(f"Created order {order.order_id}: {side.value} {quantity} {symbol}")
        return order
    
    def submit_order(self, order_id: str) -> bool:
        """Submit order for execution"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        if order.status != OrderStatus.PENDING:
            logger.warning(f"Order {order_id} already submitted")
            return False
        
        # Update order status
        order.status = OrderStatus.SUBMITTED
        order.updated_at = datetime.now()
        
        # Notify callbacks
        for callback in self.execution_callbacks:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"Execution callback failed: {e}")
        
        logger.info(f"Submitted order {order_id}")
        return True
    
    def execute_order(self, order_id: str, fill_price: float, fill_quantity: int = None) -> bool:
        """Execute order with fill"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        if order.status not in [OrderStatus.SUBMITTED, OrderStatus.PARTIAL]:
            logger.warning(f"Order {order_id} not in executable state")
            return False
        
        # Use remaining quantity if not specified
        if fill_quantity is None:
            fill_quantity = order.quantity - order.filled_quantity
        
        if fill_quantity <= 0:
            logger.warning(f"Invalid fill quantity: {fill_quantity}")
            return False
        
        # Record fill
        fill = {
            'price': fill_price,
            'quantity': fill_quantity,
            'timestamp': datetime.now()
        }
        order.fills.append(fill)
        
        # Update order
        order.filled_quantity += fill_quantity
        order.avg_fill_price = ((order.avg_fill_price * (order.filled_quantity - fill_quantity)) + 
                               (fill_price * fill_quantity)) / order.filled_quantity
        order.updated_at = datetime.now()
        
        # Update status
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
            self.filled_orders.append(order)
            if order in self.pending_orders:
                self.pending_orders.remove(order)
        else:
            order.status = OrderStatus.PARTIAL
        
        # Update capital
        trade_value = fill_price * fill_quantity
        if order.side == OrderSide.BUY:
            self.available_capital -= trade_value
        else:
            self.available_capital += trade_value
        
        logger.info(f"Executed order {order_id}: {fill_quantity} @ {fill_price}")
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            logger.warning(f"Order {order_id} cannot be cancelled")
            return False
        
        # Update order status
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        
        # Move to cancelled orders
        self.cancelled_orders.append(order)
        if order in self.pending_orders:
            self.pending_orders.remove(order)
        
        logger.info(f"Cancelled order {order_id}")
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders"""
        return self.pending_orders.copy()
    
    def get_filled_orders(self) -> List[Order]:
        """Get all filled orders"""
        return self.filled_orders.copy()
    
    def get_order_summary(self) -> Dict[str, Any]:
        """Get order summary statistics"""
        total_orders = len(self.orders)
        pending_orders = len(self.pending_orders)
        filled_orders = len(self.filled_orders)
        cancelled_orders = len(self.cancelled_orders)
        
        total_volume = sum(order.filled_quantity for order in self.filled_orders)
        total_value = sum(order.filled_quantity * order.avg_fill_price for order in self.filled_orders)
        
        return {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'filled_orders': filled_orders,
            'cancelled_orders': cancelled_orders,
            'total_volume': total_volume,
            'total_value': total_value,
            'available_capital': self.available_capital
        }

class SmartOrderRouter:
    """Enhanced smart order routing system"""
    
    def __init__(self, order_manager: OrderManager):
        self.order_manager = order_manager
        self.execution_strategies: Dict[ExecutionStrategy, Dict[str, Any]] = {}
        self.market_data: Dict[str, Dict[str, Any]] = {}
        self.execution_analytics: Dict[str, Any] = {}
        
        # Execution parameters
        self.default_slippage = 0.001  # 0.1% default slippage
        self.max_order_size = 10000    # Maximum order size
        self.min_order_size = 100      # Minimum order size
        
        logger.info("Initialized SmartOrderRouter")
    
    def add_execution_strategy(self, strategy: ExecutionStrategy, config: Dict[str, Any]):
        """Add execution strategy configuration"""
        self.execution_strategies[strategy] = config
        logger.info(f"Added execution strategy: {strategy.value}")
    
    def update_market_data(self, symbol: str, data: Dict[str, Any]):
        """Update market data for routing decisions"""
        self.market_data[symbol] = data
        logger.debug(f"Updated market data for {symbol}")
    
    def route_order(self, symbol: str, side: OrderSide, quantity: int,
                   strategy: ExecutionStrategy = ExecutionStrategy.MARKET,
                   urgency: str = "NORMAL") -> Optional[Order]:
        """Route order using smart execution strategy"""
        
        # Validate order parameters
        if quantity > self.max_order_size:
            logger.warning(f"Order size {quantity} exceeds maximum {self.max_order_size}")
            quantity = self.max_order_size
        
        if quantity < self.min_order_size:
            logger.warning(f"Order size {quantity} below minimum {self.min_order_size}")
            quantity = self.min_order_size
        
        # Get market data
        market_data = self.market_data.get(symbol, {})
        
        # Apply execution strategy
        if strategy == ExecutionStrategy.MARKET:
            return self._execute_market_order(symbol, side, quantity, urgency)
        elif strategy == ExecutionStrategy.LIMIT:
            return self._execute_limit_order(symbol, side, quantity, market_data)
        elif strategy == ExecutionStrategy.TWAP:
            return self._execute_twap_order(symbol, side, quantity, market_data)
        elif strategy == ExecutionStrategy.VWAP:
            return self._execute_vwap_order(symbol, side, quantity, market_data)
        else:
            logger.warning(f"Unknown strategy {strategy}, falling back to MARKET")
            return self._execute_market_order(symbol, side, quantity, urgency)
    
    def _execute_market_order(self, symbol: str, side: OrderSide, quantity: int, 
                            urgency: str) -> Optional[Order]:
        """Execute market order with slippage adjustment"""
        
        # Get current market price
        market_price = self._get_market_price(symbol)
        if market_price is None:
            logger.error(f"No market price available for {symbol}")
            return None
        
        # Apply slippage based on urgency
        slippage_multiplier = {
            "HIGH": 2.0,
            "NORMAL": 1.0,
            "LOW": 0.5
        }.get(urgency, 1.0)
        
        slippage = self.default_slippage * slippage_multiplier
        
        # Calculate execution price
        if side == OrderSide.BUY:
            execution_price = market_price * (1 + slippage)
        else:
            execution_price = market_price * (1 - slippage)
        
        # Create and submit order
        order = self.order_manager.create_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET
        )
        
        self.order_manager.submit_order(order.order_id)
        
        # Execute immediately for market orders
        self.order_manager.execute_order(order.order_id, execution_price, quantity)
        
        logger.info(f"Executed market order: {side.value} {quantity} {symbol} @ {execution_price:.2f}")
        return order
    
    def _execute_limit_order(self, symbol: str, side: OrderSide, quantity: int,
                           market_data: Dict[str, Any]) -> Optional[Order]:
        """Execute limit order"""
        
        market_price = self._get_market_price(symbol)
        if market_price is None:
            logger.error(f"No market price available for {symbol}")
            return None
        
        # Calculate limit price based on side
        if side == OrderSide.BUY:
            limit_price = market_price * 0.99  # 1% below market
        else:
            limit_price = market_price * 1.01  # 1% above market
        
        # Create limit order
        order = self.order_manager.create_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=limit_price
        )
        
        self.order_manager.submit_order(order.order_id)
        
        logger.info(f"Created limit order: {side.value} {quantity} {symbol} @ {limit_price:.2f}")
        return order
    
    def _execute_twap_order(self, symbol: str, side: OrderSide, quantity: int,
                          market_data: Dict[str, Any]) -> Optional[Order]:
        """Execute TWAP order"""
        
        # TWAP implementation would split order over time
        # For now, create a single market order
        logger.info(f"TWAP order requested: {side.value} {quantity} {symbol}")
        return self._execute_market_order(symbol, side, quantity, "LOW")
    
    def _execute_vwap_order(self, symbol: str, side: OrderSide, quantity: int,
                          market_data: Dict[str, Any]) -> Optional[Order]:
        """Execute VWAP order"""
        
        # VWAP implementation would consider volume profile
        # For now, create a single market order
        logger.info(f"VWAP order requested: {side.value} {quantity} {symbol}")
        return self._execute_market_order(symbol, side, quantity, "LOW")
    
    def _get_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol"""
        market_data = self.market_data.get(symbol, {})
        return market_data.get('price', 100.0)  # Default price for testing
    
    def get_execution_analytics(self) -> Dict[str, Any]:
        """Get execution analytics"""
        return self.execution_analytics.copy()

class TransactionCostOptimizer:
    """Enhanced transaction cost optimization system"""
    
    def __init__(self):
        self.cost_models: Dict[str, Dict[str, float]] = {}
        self.optimization_history: List[Dict[str, Any]] = []
        
        # Default cost parameters
        self.default_commission = 0.005  # $5 per trade
        self.default_slippage = 0.001    # 0.1% slippage
        self.default_market_impact = 0.0001  # 0.01% per $10k
        
        logger.info("Initialized TransactionCostOptimizer")
    
    def calculate_transaction_costs(self, symbol: str, side: str, quantity: int, 
                                  price: float, order_type: str = "MARKET") -> Dict[str, float]:
        """Calculate total transaction costs"""
        
        # Commission costs
        commission_cost = self.default_commission
        
        # Slippage costs
        slippage_cost = price * quantity * self.default_slippage
        
        # Market impact costs
        trade_value = price * quantity
        market_impact_cost = trade_value * self.default_market_impact * (trade_value / 10000)
        
        # Total costs
        total_cost = commission_cost + slippage_cost + market_impact_cost
        total_cost_bps = (total_cost / trade_value) * 10000  # Basis points
        
        cost_breakdown = {
            'commission': commission_cost,
            'slippage': slippage_cost,
            'market_impact': market_impact_cost,
            'total_cost': total_cost,
            'total_cost_bps': total_cost_bps,
            'trade_value': trade_value
        }
        
        logger.debug(f"Transaction costs for {side} {quantity} {symbol}: ${total_cost:.2f} ({total_cost_bps:.1f} bps)")
        return cost_breakdown
    
    def optimize_order_size(self, symbol: str, side: str, total_quantity: int,
                          price: float, max_cost_bps: float = 10.0) -> Dict[str, Any]:
        """Optimize order size to minimize transaction costs"""
        
        # Test different order sizes
        order_sizes = [total_quantity]  # Start with single order
        
        # Split into smaller orders if beneficial
        if total_quantity > 1000:
            order_sizes.extend([total_quantity // 2, total_quantity // 4])
        
        best_config = None
        min_total_cost = float('inf')
        
        for order_size in order_sizes:
            if order_size <= 0:
                continue
            
            num_orders = (total_quantity + order_size - 1) // order_size  # Ceiling division
            actual_order_size = total_quantity // num_orders
            
            # Calculate costs for this configuration
            cost_per_order = self.calculate_transaction_costs(symbol, side, actual_order_size, price)
            total_cost = cost_per_order['total_cost'] * num_orders
            total_cost_bps = (total_cost / (price * total_quantity)) * 10000
            
            if total_cost_bps <= max_cost_bps and total_cost < min_total_cost:
                min_total_cost = total_cost
                best_config = {
                    'order_size': actual_order_size,
                    'num_orders': num_orders,
                    'total_cost': total_cost,
                    'total_cost_bps': total_cost_bps,
                    'cost_per_order': cost_per_order
                }
        
        if best_config:
            logger.info(f"Optimized order size: {best_config['num_orders']} orders of {best_config['order_size']} "
                       f"(cost: {best_config['total_cost_bps']:.1f} bps)")
        else:
            logger.warning(f"Could not optimize order size within {max_cost_bps} bps limit")
        
        return best_config or {
            'order_size': total_quantity,
            'num_orders': 1,
            'total_cost': self.calculate_transaction_costs(symbol, side, total_quantity, price)['total_cost'],
            'total_cost_bps': self.calculate_transaction_costs(symbol, side, total_quantity, price)['total_cost_bps'],
            'cost_per_order': self.calculate_transaction_costs(symbol, side, total_quantity, price)
        }
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost optimization summary"""
        if not self.optimization_history:
            return {'total_optimizations': 0, 'average_savings': 0.0}
        
        total_optimizations = len(self.optimization_history)
        total_savings = sum(opt.get('savings', 0) for opt in self.optimization_history)
        average_savings = total_savings / total_optimizations if total_optimizations > 0 else 0.0
        
        return {
            'total_optimizations': total_optimizations,
            'total_savings': total_savings,
            'average_savings': average_savings,
            'recent_optimizations': self.optimization_history[-10:]  # Last 10 optimizations
        }

class EnhancedExecutionEngine:
    """Enhanced unified execution management system"""
    
    def __init__(self, 
                 initial_capital: float = 10_000_000,  # $10M
                 max_order_value: float = 1_000_000,   # $1M
                 max_position_value: float = 5_000_000,  # $5M
                 commission_rate: float = 0.0005,      # 5 bps
                 enable_risk_checks: bool = True,
                 enable_cost_optimization: bool = True):
        
        # Initialize components
        self.order_manager = OrderManager(initial_capital=initial_capital)
        self.smart_router = SmartOrderRouter(self.order_manager)
        self.cost_optimizer = TransactionCostOptimizer()
        
        # Configuration
        self.max_order_value = max_order_value
        self.max_position_value = max_position_value
        self.commission_rate = commission_rate
        self.enable_risk_checks = enable_risk_checks
        self.enable_cost_optimization = enable_cost_optimization
        
        # Execution tracking
        self.execution_history: List[ExecutionResult] = []
        self.execution_metrics = ExecutionMetrics()
        
        # Market data feed
        self.market_data_feed = None
        self.real_time_feed = None
        
        logger.info(f"Initialized EnhancedExecutionEngine with ${initial_capital:,.2f} capital")
    
    def set_market_data_feed(self, feed):
        """Set market data feed"""
        self.market_data_feed = feed
        logger.info("Market data feed set")
    
    def set_real_time_feed(self, feed):
        """Set real-time data feed"""
        self.real_time_feed = feed
        logger.info("Real-time data feed set")
    
    async def execute_order(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute order using enhanced execution system"""
        
        start_time = datetime.now()
        
        try:
            # Validate request
            if not await self._validate_execution_request(request):
                return ExecutionResult(
                    request_id=request.request_id,
                    status=ExecutionStatus.REJECTED,
                    symbol=request.symbol,
                    side=request.side,
                    requested_quantity=request.quantity,
                    error_message="Request validation failed"
                )
            
            # Optimize execution if enabled
            if self.enable_cost_optimization:
                request = await self._optimize_execution_request(request)
            
            # Route order using smart router
            order = self.smart_router.route_order(
                symbol=request.symbol,
                side=request.side,
                quantity=int(request.quantity),
                strategy=request.strategy,
                urgency=request.urgency
            )
            
            if order is None:
                return ExecutionResult(
                    request_id=request.request_id,
                    status=ExecutionStatus.FAILED,
                    symbol=request.symbol,
                    side=request.side,
                    requested_quantity=request.quantity,
                    error_message="Order routing failed"
                )
            
            # Create execution result
            execution_time = (datetime.now() - start_time).total_seconds()
            result = ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.SUCCESS,
                symbol=request.symbol,
                side=request.side,
                requested_quantity=request.quantity,
                executed_quantity=order.filled_quantity,
                average_price=order.avg_fill_price,
                total_cost=self._calculate_total_cost(order),
                orders=[order],
                execution_time=execution_time,
                strategy_used=request.strategy
            )
            
            # Update metrics
            self._update_execution_metrics(result)
            self.execution_history.append(result)
            
            logger.info(f"Executed order {request.request_id}: {result.fill_rate:.1f}% filled")
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Execution failed for {request.request_id}: {e}")
            
            return ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                symbol=request.symbol,
                side=request.side,
                requested_quantity=request.quantity,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def execute_pair_trade(self, 
                               symbol1: str, symbol2: str,
                               quantity1: float, quantity2: float,
                               strategy: ExecutionStrategy = ExecutionStrategy.TWAP,
                               strategy_id: str = "pairs_trading") -> Tuple[ExecutionResult, ExecutionResult]:
        """Execute pair trade with coordinated execution"""
        
        logger.info(f"Executing pair trade: {symbol1} ({quantity1}) / {symbol2} ({quantity2})")
        
        # Create execution requests
        request1 = ExecutionRequest(
            symbol=symbol1,
            side=OrderSide.BUY if quantity1 > 0 else OrderSide.SELL,
            quantity=abs(quantity1),
            strategy=strategy,
            strategy_id=strategy_id
        )
        
        request2 = ExecutionRequest(
            symbol=symbol2,
            side=OrderSide.BUY if quantity2 > 0 else OrderSide.SELL,
            quantity=abs(quantity2),
            strategy=strategy,
            strategy_id=strategy_id
        )
        
        # Execute both orders
        result1 = await self.execute_order(request1)
        result2 = await self.execute_order(request2)
        
        return result1, result2
    
    async def _validate_execution_request(self, request: ExecutionRequest) -> bool:
        """Validate execution request"""
        
        # Check basic parameters
        if request.quantity <= 0:
            logger.error(f"Invalid quantity: {request.quantity}")
            return False
        
        if not request.symbol:
            logger.error("Symbol is required")
            return False
        
        # Check risk limits if enabled
        if self.enable_risk_checks:
            order_value = request.quantity * 100.0  # Approximate price
            if order_value > self.max_order_value:
                logger.error(f"Order value ${order_value:,.2f} exceeds limit ${self.max_order_value:,.2f}")
                return False
        
        return True
    
    async def _optimize_execution_request(self, request: ExecutionRequest) -> ExecutionRequest:
        """Optimize execution request for cost efficiency"""
        
        # Get current market price (approximate)
        market_price = 100.0  # This would come from market data feed
        
        # Optimize order size
        optimization = self.cost_optimizer.optimize_order_size(
            symbol=request.symbol,
            side=request.side.value,
            total_quantity=int(request.quantity),
            price=market_price
        )
        
        # Update request if optimization found better configuration
        if optimization['num_orders'] > 1:
            request.metadata['optimization'] = optimization
            logger.info(f"Optimized execution: {optimization['num_orders']} orders of {optimization['order_size']}")
        
        return request
    
    def _calculate_total_cost(self, order: Order) -> float:
        """Calculate total cost for order"""
        if order.filled_quantity == 0:
            return 0.0
        
        # Calculate transaction costs
        costs = self.cost_optimizer.calculate_transaction_costs(
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.filled_quantity,
            price=order.avg_fill_price,
            order_type=order.order_type.value
        )
        
        return costs['total_cost']
    
    def _update_execution_metrics(self, result: ExecutionResult):
        """Update execution metrics"""
        self.execution_metrics.total_executions += 1
        
        if result.status == ExecutionStatus.SUCCESS:
            self.execution_metrics.successful_executions += 1
        
        # Update averages
        if self.execution_metrics.total_executions > 0:
            self.execution_metrics.average_fill_rate = (
                (self.execution_metrics.average_fill_rate * (self.execution_metrics.total_executions - 1) + 
                 result.fill_rate) / self.execution_metrics.total_executions
            )
            
            self.execution_metrics.average_execution_time = (
                (self.execution_metrics.average_execution_time * (self.execution_metrics.total_executions - 1) + 
                 result.execution_time) / self.execution_metrics.total_executions
            )
        
        self.execution_metrics.total_transaction_costs += result.total_cost
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        return {
            'total_executions': self.execution_metrics.total_executions,
            'successful_executions': self.execution_metrics.successful_executions,
            'success_rate': (self.execution_metrics.successful_executions / 
                           self.execution_metrics.total_executions * 100) if self.execution_metrics.total_executions > 0 else 0,
            'average_fill_rate': self.execution_metrics.average_fill_rate,
            'average_execution_time': self.execution_metrics.average_execution_time,
            'total_transaction_costs': self.execution_metrics.total_transaction_costs,
            'order_summary': self.order_manager.get_order_summary()
        }
    
    def get_execution_history(self, 
                            symbol: Optional[str] = None,
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None) -> List[ExecutionResult]:
        """Get execution history with optional filtering"""
        
        history = self.execution_history.copy()
        
        if symbol:
            history = [r for r in history if r.symbol == symbol]
        
        if start_time:
            history = [r for r in history if r.timestamp >= start_time]
        
        if end_time:
            history = [r for r in history if r.timestamp <= end_time]
        
        return history
    
    def cancel_execution(self, request_id: str) -> bool:
        """Cancel execution request"""
        # Find and cancel associated orders
        for result in self.execution_history:
            if result.request_id == request_id and not result.is_complete:
                for order in result.orders:
                    if order.status not in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                        self.order_manager.cancel_order(order.order_id)
                return True
        
        return False
    
    def get_real_time_positions(self) -> Dict[str, Dict[str, float]]:
        """Get real-time position information"""
        # This would integrate with portfolio management system
        return {} 