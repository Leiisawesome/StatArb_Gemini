"""
ExecutionBridge: Production ↔ Backtesting Execution Integration

This module provides a bridge between production execution systems and backtesting
execution requirements. It ensures execution consistency between production and
backtesting environments.

Key Features:
- Production-to-backtesting execution bridging
- Market impact modeling for realistic backtesting
- Transaction cost optimization
- Order management integration
- Execution strategy consistency
- Performance monitoring and validation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import json
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

# Core system imports
try:
    from ..infrastructure.config_manager import ConfigManager
    from ..infrastructure.message_bus import MessageBus
    from ..infrastructure.metrics_collector import MetricsCollector
except ImportError:
    ConfigManager = None
    MessageBus = None
    MetricsCollector = None

# Execution system imports
try:
    from .order_manager import OrderManager
    from .smart_order_router import SmartOrderRouter
    from .transaction_cost_optimizer import TransactionCostOptimizer
    from .market_impact_modeler import MarketImpactModeler
except ImportError:
    OrderManager = None
    SmartOrderRouter = None
    TransactionCostOptimizer = None
    MarketImpactModeler = None

logger = logging.getLogger(__name__)

class ExecutionMode(Enum):
    """Execution modes for different environments"""
    PRODUCTION = "production"
    BACKTESTING = "backtesting"
    SIMULATION = "simulation"
    PAPER_TRADING = "paper_trading"

class OrderType(Enum):
    """Order types supported by the bridge"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TWAP = "twap"
    VWAP = "vwap"
    ICEBERG = "iceberg"

@dataclass
class ExecutionBridgeConfig:
    """Configuration for ExecutionBridge"""
    
    # Execution mode
    execution_mode: ExecutionMode = ExecutionMode.BACKTESTING
    
    # Market impact modeling
    enable_market_impact: bool = True
    market_impact_model: str = "linear"
    impact_sensitivity: float = 0.1
    
    # Transaction costs
    enable_transaction_costs: bool = True
    commission_rate: float = 0.001  # 0.1%
    slippage_model: str = "proportional"
    slippage_rate: float = 0.0005  # 0.05%
    
    # Order management
    enable_smart_routing: bool = True
    enable_twap_vwap: bool = True
    max_order_size: float = 1000000  # $1M
    
    # Performance settings
    max_concurrent_orders: int = 10
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    
    # Validation settings
    validate_orders: bool = True
    min_order_size: float = 100  # $100
    max_position_size: float = 0.1  # 10% of portfolio
    
    # Logging settings
    log_executions: bool = True
    log_performance: bool = True

@dataclass
class ExecutionOrder:
    """Order structure for execution bridge"""
    
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: int
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"
    strategy: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ExecutionResult:
    """Result from execution bridge"""
    
    order_id: str
    symbol: str
    side: str
    quantity: int
    filled_quantity: int
    price: float
    execution_price: float
    commission: float
    slippage: float
    market_impact: float
    total_cost: float
    timestamp: datetime
    status: str  # 'filled', 'partial', 'cancelled', 'rejected'
    execution_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

@dataclass
class MarketImpactResult:
    """Market impact calculation result"""
    
    symbol: str
    quantity: int
    side: str
    base_price: float
    impacted_price: float
    impact_amount: float
    impact_percentage: float
    model_used: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionCostResult:
    """Transaction cost calculation result"""
    
    symbol: str
    quantity: int
    price: float
    commission: float
    slippage: float
    total_cost: float
    cost_percentage: float
    model_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class ExecutionBridge:
    """Bridge between production and backtesting execution systems"""
    
    def __init__(self, config: Optional[ExecutionBridgeConfig] = None):
        """Initialize ExecutionBridge"""
        self.config = config or ExecutionBridgeConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Performance tracking
        self._performance_stats = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0,
            'total_commission': 0.0,
            'total_slippage': 0.0,
            'total_market_impact': 0.0
        }
        
        # Initialize components
        self._initialize_components()
        
        # Thread pool for concurrent execution
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_orders)
        
        self.logger.info(f"ExecutionBridge initialized in {self.config.execution_mode.value} mode")
    
    def _initialize_components(self):
        """Initialize execution components"""
        try:
            # Order management
            if OrderManager:
                self.order_manager = OrderManager()
                self.logger.info("OrderManager initialized")
            else:
                self.order_manager = None
                self.logger.warning("OrderManager not available")
            
            # Smart order routing
            if SmartOrderRouter and self.config.enable_smart_routing:
                self.smart_router = SmartOrderRouter()
                self.logger.info("SmartOrderRouter initialized")
            else:
                self.smart_router = None
            
            # Transaction cost optimization
            if TransactionCostOptimizer and self.config.enable_transaction_costs:
                self.cost_optimizer = TransactionCostOptimizer()
                self.logger.info("TransactionCostOptimizer initialized")
            else:
                self.cost_optimizer = None
            
            # Market impact modeling
            if MarketImpactModeler and self.config.enable_market_impact:
                self.impact_modeler = MarketImpactModeler()
                self.logger.info("MarketImpactModeler initialized")
            else:
                self.impact_modeler = None
            
        except Exception as e:
            self.logger.error(f"Error initializing execution components: {e}")
            raise
    
    def execute_order(
        self,
        order: ExecutionOrder,
        market_data: Optional[pd.DataFrame] = None,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute an order with market impact and transaction cost modeling"""
        start_time = time.time()
        
        try:
            # Validate order
            if self.config.validate_orders:
                self._validate_order(order, portfolio_state)
            
            # Calculate market impact
            market_impact = self._calculate_market_impact(order, market_data)
            
            # Calculate transaction costs
            transaction_costs = self._calculate_transaction_costs(order, market_impact)
            
            # Execute order based on mode
            if self.config.execution_mode == ExecutionMode.BACKTESTING:
                result = self._execute_backtesting_order(order, market_impact, transaction_costs)
            elif self.config.execution_mode == ExecutionMode.PRODUCTION:
                result = self._execute_production_order(order, market_impact, transaction_costs)
            else:
                result = self._execute_simulation_order(order, market_impact, transaction_costs)
            
            # Update performance stats
            self._update_performance_stats(result, time.time() - start_time)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing order: {e}")
            return self._create_error_result(order, str(e), time.time() - start_time)
    
    def execute_orders_batch(
        self,
        orders: List[ExecutionOrder],
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
        portfolio_state: Optional[Dict[str, Any]] = None
    ) -> List[ExecutionResult]:
        """Execute multiple orders concurrently"""
        results = []
        
        # Use thread pool for concurrent execution
        futures = []
        for order in orders:
            future = self._executor.submit(
                self.execute_order,
                order,
                market_data.get(order.symbol) if market_data else None,
                portfolio_state
            )
            futures.append(future)
        
        # Collect results
        for future in futures:
            try:
                result = future.result(timeout=self.config.timeout_seconds)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error in batch execution: {e}")
                # Create error result for failed orders
                results.append(self._create_error_result(
                    ExecutionOrder("UNKNOWN", "buy", 0, OrderType.MARKET),
                    str(e),
                    0.0
                ))
        
        return results
    
    def _validate_order(self, order: ExecutionOrder, portfolio_state: Optional[Dict[str, Any]] = None):
        """Validate order parameters"""
        if order.quantity <= 0:
            raise ValueError(f"Invalid quantity: {order.quantity}")
        
        if order.quantity * (order.price or 100) < self.config.min_order_size:
            raise ValueError(f"Order size below minimum: {order.quantity * (order.price or 100)}")
        
        if portfolio_state:
            portfolio_value = portfolio_state.get('total_value', 0)
            order_value = order.quantity * (order.price or 100)
            if order_value > portfolio_value * self.config.max_position_size:
                raise ValueError(f"Order size exceeds position limit: {order_value} > {portfolio_value * self.config.max_position_size}")
    
    def _calculate_market_impact(self, order: ExecutionOrder, market_data: Optional[pd.DataFrame] = None) -> MarketImpactResult:
        """Calculate market impact of the order"""
        if not self.impact_modeler or not self.config.enable_market_impact:
            return MarketImpactResult(
                symbol=order.symbol,
                quantity=order.quantity,
                side=order.side,
                base_price=order.price or 100.0,
                impacted_price=order.price or 100.0,
                impact_amount=0.0,
                impact_percentage=0.0,
                model_used="none",
                confidence=1.0
            )
        
        try:
            # Use market impact modeler if available
            base_price = order.price or 100.0
            
            # Simple linear market impact model
            # Impact increases with order size relative to typical volume
            typical_volume = 1000000  # Assume 1M shares typical volume
            volume_ratio = order.quantity / typical_volume
            impact_percentage = self.config.impact_sensitivity * volume_ratio
            
            # Cap impact at reasonable levels
            impact_percentage = min(impact_percentage, 0.05)  # Max 5% impact
            
            if order.side == 'buy':
                impacted_price = base_price * (1 + impact_percentage)
            else:
                impacted_price = base_price * (1 - impact_percentage)
            
            return MarketImpactResult(
                symbol=order.symbol,
                quantity=order.quantity,
                side=order.side,
                base_price=base_price,
                impacted_price=impacted_price,
                impact_amount=abs(impacted_price - base_price),
                impact_percentage=impact_percentage,
                model_used=self.config.market_impact_model,
                confidence=0.8
            )
        except Exception as e:
            self.logger.warning(f"Error calculating market impact: {e}")
            return MarketImpactResult(
                symbol=order.symbol,
                quantity=order.quantity,
                side=order.side,
                base_price=order.price or 100.0,
                impacted_price=order.price or 100.0,
                impact_amount=0.0,
                impact_percentage=0.0,
                model_used="fallback",
                confidence=0.5
            )
    
    def _calculate_transaction_costs(self, order: ExecutionOrder, market_impact: MarketImpactResult) -> TransactionCostResult:
        """Calculate transaction costs including commission and slippage"""
        if not self.config.enable_transaction_costs:
            return TransactionCostResult(
                symbol=order.symbol,
                quantity=order.quantity,
                price=market_impact.impacted_price,
                commission=0.0,
                slippage=0.0,
                total_cost=0.0,
                cost_percentage=0.0,
                model_used="none"
            )
        
        try:
            # Calculate commission
            order_value = order.quantity * market_impact.impacted_price
            commission = order_value * self.config.commission_rate
            
            # Calculate slippage
            if self.config.slippage_model == "proportional":
                slippage = order_value * self.config.slippage_rate
            else:
                slippage = 0.0
            
            total_cost = commission + slippage
            cost_percentage = total_cost / order_value if order_value > 0 else 0.0
            
            return TransactionCostResult(
                symbol=order.symbol,
                quantity=order.quantity,
                price=market_impact.impacted_price,
                commission=commission,
                slippage=slippage,
                total_cost=total_cost,
                cost_percentage=cost_percentage,
                model_used=self.config.slippage_model
            )
        except Exception as e:
            self.logger.warning(f"Error calculating transaction costs: {e}")
            return TransactionCostResult(
                symbol=order.symbol,
                quantity=order.quantity,
                price=market_impact.impacted_price,
                commission=0.0,
                slippage=0.0,
                total_cost=0.0,
                cost_percentage=0.0,
                model_used="fallback"
            )
    
    def _execute_backtesting_order(
        self,
        order: ExecutionOrder,
        market_impact: MarketImpactResult,
        transaction_costs: TransactionCostResult
    ) -> ExecutionResult:
        """Execute order in backtesting mode"""
        execution_price = market_impact.impacted_price
        filled_quantity = order.quantity  # Assume full fill in backtesting
        
        return ExecutionResult(
            order_id=f"BT_{int(time.time() * 1000)}",
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=filled_quantity,
            price=order.price or execution_price,
            execution_price=execution_price,
            commission=transaction_costs.commission,
            slippage=transaction_costs.slippage,
            market_impact=market_impact.impact_amount,
            total_cost=transaction_costs.total_cost,
            timestamp=datetime.now(),
            status="filled",
            execution_time_ms=0.0,
            metadata={
                'mode': 'backtesting',
                'market_impact_model': market_impact.model_used,
                'cost_model': transaction_costs.model_used
            }
        )
    
    def _execute_production_order(
        self,
        order: ExecutionOrder,
        market_impact: MarketImpactResult,
        transaction_costs: TransactionCostResult
    ) -> ExecutionResult:
        """Execute order in production mode"""
        # This would integrate with actual production execution systems
        # For now, simulate production execution
        execution_price = market_impact.impacted_price
        filled_quantity = order.quantity  # Assume full fill
        
        return ExecutionResult(
            order_id=f"PROD_{int(time.time() * 1000)}",
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=filled_quantity,
            price=order.price or execution_price,
            execution_price=execution_price,
            commission=transaction_costs.commission,
            slippage=transaction_costs.slippage,
            market_impact=market_impact.impact_amount,
            total_cost=transaction_costs.total_cost,
            timestamp=datetime.now(),
            status="filled",
            execution_time_ms=0.0,
            metadata={
                'mode': 'production',
                'market_impact_model': market_impact.model_used,
                'cost_model': transaction_costs.model_used
            }
        )
    
    def _execute_simulation_order(
        self,
        order: ExecutionOrder,
        market_impact: MarketImpactResult,
        transaction_costs: TransactionCostResult
    ) -> ExecutionResult:
        """Execute order in simulation mode"""
        execution_price = market_impact.impacted_price
        filled_quantity = order.quantity  # Assume full fill
        
        return ExecutionResult(
            order_id=f"SIM_{int(time.time() * 1000)}",
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=filled_quantity,
            price=order.price or execution_price,
            execution_price=execution_price,
            commission=transaction_costs.commission,
            slippage=transaction_costs.slippage,
            market_impact=market_impact.impact_amount,
            total_cost=transaction_costs.total_cost,
            timestamp=datetime.now(),
            status="filled",
            execution_time_ms=0.0,
            metadata={
                'mode': 'simulation',
                'market_impact_model': market_impact.model_used,
                'cost_model': transaction_costs.model_used
            }
        )
    
    def _create_error_result(self, order: ExecutionOrder, error_message: str, execution_time: float) -> ExecutionResult:
        """Create error result for failed orders"""
        return ExecutionResult(
            order_id=f"ERROR_{int(time.time() * 1000)}",
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=0,
            price=order.price or 0.0,
            execution_price=0.0,
            commission=0.0,
            slippage=0.0,
            market_impact=0.0,
            total_cost=0.0,
            timestamp=datetime.now(),
            status="rejected",
            execution_time_ms=execution_time * 1000,
            error_message=error_message
        )
    
    def _update_performance_stats(self, result: ExecutionResult, execution_time: float):
        """Update performance statistics"""
        self._performance_stats['total_orders'] += 1
        self._performance_stats['total_execution_time'] += execution_time
        
        if result.status == "filled":
            self._performance_stats['successful_orders'] += 1
            self._performance_stats['total_commission'] += result.commission
            self._performance_stats['total_slippage'] += result.slippage
            self._performance_stats['total_market_impact'] += result.market_impact
        else:
            self._performance_stats['failed_orders'] += 1
        
        # Update average execution time
        self._performance_stats['avg_execution_time'] = (
            self._performance_stats['total_execution_time'] / self._performance_stats['total_orders']
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self._performance_stats.copy()
    
    def reset_performance_stats(self):
        """Reset performance statistics"""
        self._performance_stats = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0,
            'total_commission': 0.0,
            'total_slippage': 0.0,
            'total_market_impact': 0.0
        }
    
    def shutdown(self):
        """Shutdown the execution bridge"""
        if self._executor:
            self._executor.shutdown(wait=True)
        self.logger.info("ExecutionBridge shutdown complete")

def create_execution_bridge(config: Optional[ExecutionBridgeConfig] = None) -> ExecutionBridge:
    """Create an ExecutionBridge instance"""
    return ExecutionBridge(config)

def execute_orders_for_backtesting(
    orders: List[ExecutionOrder],
    market_data: Optional[Dict[str, pd.DataFrame]] = None,
    portfolio_state: Optional[Dict[str, Any]] = None,
    bridge: Optional[ExecutionBridge] = None
) -> List[ExecutionResult]:
    """Convenience function for backtesting order execution"""
    if bridge is None:
        config = ExecutionBridgeConfig(execution_mode=ExecutionMode.BACKTESTING)
        bridge = ExecutionBridge(config)
    
    return bridge.execute_orders_batch(orders, market_data, portfolio_state) 