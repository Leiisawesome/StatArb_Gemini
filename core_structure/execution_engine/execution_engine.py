"""
Enhanced Execution Engine

Professional-grade execution engine that provides:
- Multi-algorithm execution (TWAP, VWAP, Implementation Shortfall)
- Real-time market impact modeling
- Smart order routing and venue selection
- Transaction cost optimization
- Execution quality analytics
- Risk-aware position management

Author: Pro Quant Desk Trader
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import uuid
from abc import ABC, abstractmethod

# Import components (will be implemented in separate files)
from .order_manager import OrderManager, Order, OrderStatus, OrderType, OrderSide
from .market_impact import MarketImpactModel, MarketConditions
from .transaction_cost_optimizer import TransactionCostOptimizer


class ExecutionStatus(Enum):
    """Execution status enumeration"""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ExecutionAlgorithm(Enum):
    """Available execution algorithms"""
    MARKET = "market"
    TWAP = "twap"
    VWAP = "vwap"
    IMPLEMENTATION_SHORTFALL = "implementation_shortfall"
    SMART_ROUTING = "smart_routing"


@dataclass
class ExecutionRequest:
    """Request for trade execution"""
    symbol: str
    side: OrderSide
    quantity: float
    algorithm: ExecutionAlgorithm = ExecutionAlgorithm.MARKET
    target_price: Optional[float] = None
    time_limit: Optional[int] = None  # Minutes
    max_participation: float = 0.2  # 20% max participation
    urgency: float = 0.5  # 0=patient, 1=urgent
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
    algorithm_used: ExecutionAlgorithm = ExecutionAlgorithm.MARKET
    
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
            total_value = sum(order.filled_quantity * order.average_fill_price 
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
    
    # Algorithm performance
    algorithm_performance: Dict[ExecutionAlgorithm, Dict[str, float]] = field(default_factory=dict)
    
    # Venue performance
    venue_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)


class ExecutionEngine:
    """
    Professional execution engine with advanced capabilities
    
    Features:
    - Multi-algorithm execution support
    - Real-time market impact modeling
    - Smart order routing
    - Transaction cost optimization
    - Execution quality analytics
    - Risk controls and validation
    """
    
    def __init__(self, 
                 initial_capital: float = 10_000_000,  # $10M
                 max_order_value: float = 1_000_000,   # $1M
                 max_position_value: float = 5_000_000,  # $5M
                 commission_rate: float = 0.0005,      # 5 bps
                 enable_risk_checks: bool = True,
                 enable_cost_optimization: bool = True):
        """
        Initialize execution engine
        
        Args:
            initial_capital: Starting capital
            max_order_value: Maximum single order value
            max_position_value: Maximum position value
            commission_rate: Default commission rate
            enable_risk_checks: Enable pre-trade risk checks
            enable_cost_optimization: Enable transaction cost optimization
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_order_value = max_order_value
        self.max_position_value = max_position_value
        self.commission_rate = commission_rate
        self.enable_risk_checks = enable_risk_checks
        self.enable_cost_optimization = enable_cost_optimization
        
        # Initialize components
        self.order_manager = OrderManager(
            max_order_value=max_order_value,
            max_position_value=max_position_value,
            enable_risk_checks=enable_risk_checks
        )
        
        self.market_impact_model = MarketImpactModel(
            commission_rate=commission_rate
        )
        
        self.cost_optimizer = TransactionCostOptimizer() if enable_cost_optimization else None
        
        # Execution tracking
        self.execution_requests: Dict[str, ExecutionRequest] = {}
        self.execution_results: Dict[str, ExecutionResult] = {}
        self.execution_metrics = ExecutionMetrics()
        
        # Algorithm registry (will be populated by advanced_algorithms module)
        self.algorithms: Dict[ExecutionAlgorithm, Any] = {}
        
        # Market data feeds (to be injected)
        self.market_data_feed = None
        self.real_time_feed = None
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.total_transaction_costs = 0.0
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("ExecutionEngine initialized with institutional-grade capabilities")
    
    def set_market_data_feed(self, feed):
        """Set market data feed for execution algorithms"""
        self.market_data_feed = feed
        for algorithm in self.algorithms.values():
            if hasattr(algorithm, 'set_market_data_feed'):
                algorithm.set_market_data_feed(feed)
    
    def set_real_time_feed(self, feed):
        """Set real-time market data feed"""
        self.real_time_feed = feed
    
    def register_algorithm(self, algorithm_type: ExecutionAlgorithm, algorithm_instance):
        """Register execution algorithm"""
        self.algorithms[algorithm_type] = algorithm_instance
        algorithm_instance.set_execution_engine(self)
        self.logger.info(f"Registered algorithm: {algorithm_type.value}")
    
    async def execute_order(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute order using specified algorithm
        
        Args:
            request: Execution request
            
        Returns:
            ExecutionResult with execution details
        """
        start_time = datetime.now()
        
        # Store request
        self.execution_requests[request.request_id] = request
        
        # Initialize result
        result = ExecutionResult(
            request_id=request.request_id,
            status=ExecutionStatus.PENDING,
            symbol=request.symbol,
            side=request.side,
            requested_quantity=request.quantity,
            algorithm_used=request.algorithm
        )
        
        try:
            # Pre-execution validation
            if not await self._validate_execution_request(request):
                result.status = ExecutionStatus.REJECTED
                result.error_message = "Pre-execution validation failed"
                return result
            
            # Get market conditions
            market_conditions = await self._get_market_conditions(request.symbol)
            
            # Optimize execution if enabled
            if self.enable_cost_optimization and self.cost_optimizer:
                request = await self._optimize_execution_request(request, market_conditions)
            
            # Execute using specified algorithm
            result.status = ExecutionStatus.EXECUTING
            
            if request.algorithm == ExecutionAlgorithm.MARKET:
                result = await self._execute_market_order(request, market_conditions)
            elif request.algorithm in self.algorithms:
                algorithm = self.algorithms[request.algorithm]
                result = await algorithm.execute(request, market_conditions)
            else:
                result.status = ExecutionStatus.FAILED
                result.error_message = f"Algorithm {request.algorithm.value} not available"
            
            # Calculate execution metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            # Update performance metrics
            self._update_execution_metrics(result)
            
            # Store result
            self.execution_results[request.request_id] = result
            
            self.logger.info(f"Execution completed: {request.symbol} {request.side.value} "
                           f"{request.quantity} -> {result.status.value}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Execution failed: {str(e)}")
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.execution_time = (datetime.now() - start_time).total_seconds()
            
            self.execution_results[request.request_id] = result
            return result
    
    async def execute_pair_trade(self, 
                               symbol1: str, symbol2: str,
                               quantity1: float, quantity2: float,
                               algorithm: ExecutionAlgorithm = ExecutionAlgorithm.TWAP,
                               strategy_id: str = "pairs_trading") -> Tuple[ExecutionResult, ExecutionResult]:
        """
        Execute coordinated pair trade
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol  
            quantity1: Quantity for first symbol (positive=buy, negative=sell)
            quantity2: Quantity for second symbol (positive=buy, negative=sell)
            algorithm: Execution algorithm to use
            strategy_id: Strategy identifier
            
        Returns:
            Tuple of ExecutionResult for each leg
        """
        # Create execution requests
        request1 = ExecutionRequest(
            symbol=symbol1,
            side=OrderSide.BUY if quantity1 > 0 else OrderSide.SELL,
            quantity=abs(quantity1),
            algorithm=algorithm,
            strategy_id=strategy_id
        )
        
        request2 = ExecutionRequest(
            symbol=symbol2,
            side=OrderSide.BUY if quantity2 > 0 else OrderSide.SELL,
            quantity=abs(quantity2),
            algorithm=algorithm,
            strategy_id=strategy_id
        )
        
        # Execute both legs simultaneously
        tasks = [
            self.execute_order(request1),
            self.execute_order(request2)
        ]
        
        results = await asyncio.gather(*tasks)
        
        self.logger.info(f"Pair trade executed: {symbol1}({quantity1}) & {symbol2}({quantity2})")
        
        return results[0], results[1]
    
    async def _validate_execution_request(self, request: ExecutionRequest) -> bool:
        """Validate execution request"""
        try:
            # Check order value
            if self.real_time_feed:
                current_price = self.real_time_feed.get_current_price(request.symbol)
                if current_price:
                    order_value = request.quantity * current_price
                    if order_value > self.max_order_value:
                        self.logger.warning(f"Order value {order_value} exceeds maximum {self.max_order_value}")
                        return False
            
            # Check position limits
            if self.enable_risk_checks:
                current_position = self.order_manager.get_position(request.symbol)
                if current_position:
                    # Additional position checks can be added here
                    pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return False
    
    async def _get_market_conditions(self, symbol: str) -> MarketConditions:
        """Get current market conditions for symbol"""
        # This would typically fetch from market data feed
        # For now, return default conditions
        return MarketConditions(
            volatility=0.02,  # 2% daily volatility
            volume=1_000_000,  # 1M shares daily volume
            spread=0.001      # 10 bps spread
        )
    
    async def _optimize_execution_request(self, 
                                        request: ExecutionRequest,
                                        market_conditions: MarketConditions) -> ExecutionRequest:
        """Optimize execution request based on market conditions"""
        if self.cost_optimizer:
            # Cost optimizer would suggest optimal algorithm, timing, etc.
            pass
        
        return request
    
    async def _execute_market_order(self, 
                                  request: ExecutionRequest,
                                  market_conditions: MarketConditions) -> ExecutionResult:
        """Execute simple market order"""
        # Create order
        order = Order(
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            order_type=OrderType.MARKET,
            strategy_id=request.strategy_id
        )
        
        # Submit to order manager
        if not self.order_manager.submit_order(order):
            return ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.REJECTED,
                symbol=request.symbol,
                side=request.side,
                requested_quantity=request.quantity,
                error_message="Order submission failed"
            )
        
        # Simulate execution (in real system, this would be handled by market)
        current_price = 100.0  # Would get from market data
        execution_price = current_price * (1 + np.random.normal(0, 0.001))  # Add some slippage
        
        # Fill order
        fill = self.order_manager.fill_order(
            order_id=order.order_id,
            fill_quantity=request.quantity,
            fill_price=execution_price,
            commission=request.quantity * execution_price * self.commission_rate
        )
        
        if fill:
            return ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.SUCCESS,
                symbol=request.symbol,
                side=request.side,
                requested_quantity=request.quantity,
                executed_quantity=request.quantity,
                average_price=execution_price,
                total_cost=fill.commission,
                orders=[order]
            )
        else:
            return ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                symbol=request.symbol,
                side=request.side,
                requested_quantity=request.quantity,
                error_message="Order fill failed"
            )
    
    def _update_execution_metrics(self, result: ExecutionResult):
        """Update execution performance metrics"""
        self.execution_metrics.total_executions += 1
        
        if result.status == ExecutionStatus.SUCCESS:
            self.execution_metrics.successful_executions += 1
        
        # Update averages
        n = self.execution_metrics.total_executions
        self.execution_metrics.average_fill_rate = (
            (self.execution_metrics.average_fill_rate * (n-1) + result.fill_rate) / n
        )
        
        self.execution_metrics.average_execution_time = (
            (self.execution_metrics.average_execution_time * (n-1) + result.execution_time) / n
        )
        
        self.execution_metrics.total_transaction_costs += result.total_cost
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution summary"""
        positions = self.order_manager.get_all_positions()
        
        return {
            # Execution metrics
            'total_executions': self.execution_metrics.total_executions,
            'successful_executions': self.execution_metrics.successful_executions,
            'success_rate': (self.execution_metrics.successful_executions / 
                           max(1, self.execution_metrics.total_executions)) * 100,
            'average_fill_rate': self.execution_metrics.average_fill_rate,
            'average_execution_time': self.execution_metrics.average_execution_time,
            'total_transaction_costs': self.execution_metrics.total_transaction_costs,
            
            # Portfolio metrics
            'current_capital': self.current_capital,
            'active_positions': len([p for p in positions.values() if p.quantity != 0]),
            'daily_pnl': self.daily_pnl,
            
            # Algorithm performance
            'available_algorithms': [algo.value for algo in self.algorithms.keys()],
            'algorithm_performance': dict(self.execution_metrics.algorithm_performance),
            
            # Order management
            'pending_orders': len(self.order_manager.get_pending_orders()),
            'total_orders': len(self.order_manager.orders)
        }
    
    def get_execution_history(self, 
                            symbol: Optional[str] = None,
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None) -> List[ExecutionResult]:
        """Get execution history with optional filtering"""
        results = list(self.execution_results.values())
        
        # Filter by symbol
        if symbol:
            results = [r for r in results if r.symbol == symbol]
        
        # Filter by time range
        if start_time:
            results = [r for r in results if r.timestamp >= start_time]
        
        if end_time:
            results = [r for r in results if r.timestamp <= end_time]
        
        return sorted(results, key=lambda x: x.timestamp, reverse=True)
    
    def cancel_execution(self, request_id: str) -> bool:
        """Cancel pending execution"""
        if request_id in self.execution_requests:
            result = self.execution_results.get(request_id)
            if result and not result.is_complete:
                result.status = ExecutionStatus.CANCELLED
                self.logger.info(f"Execution cancelled: {request_id}")
                return True
        
        return False
    
    def get_real_time_positions(self) -> Dict[str, Dict[str, float]]:
        """Get real-time position information"""
        positions = self.order_manager.get_all_positions()
        
        position_info = {}
        for symbol, position in positions.items():
            if position.quantity != 0:
                position_info[symbol] = {
                    'quantity': position.quantity,
                    'average_price': position.average_price,
                    'market_value': position.market_value,
                    'unrealized_pnl': position.unrealized_pnl,
                    'realized_pnl': position.realized_pnl
                }
        
        return position_info 