"""
High-Performance Execution Engine
=================================

Ultra-fast execution engine designed for batch order processing
with 1,000+ orders/second and <3ms latency per execution.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import threading
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order execution status"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

@dataclass
class ExecutionEngineConfig:
    """Configuration for high-performance execution engine"""
    # Performance targets
    target_orders_per_second: int = 1000
    target_latency_ms: float = 3.0
    max_workers: int = 10
    
    # Execution settings
    enable_batch_execution: bool = True
    enable_parallel_execution: bool = True
    batch_size: int = 100
    max_batch_wait_ms: int = 50
    
    # Market impact management
    enable_market_impact_calculation: bool = True
    default_commission_rate: float = 0.0005
    default_slippage_bps: float = 5.0

@dataclass
class ExecutionResult:
    """Result of execution operation"""
    orders_processed: int
    orders_filled: int
    orders_rejected: int
    processing_time_ms: float
    orders_per_second: float
    total_value_executed: float
    average_fill_price: float
    optimization_techniques_used: List[str] = field(default_factory=list)

class BatchOrderProcessor:
    """Batch order processing engine"""
    
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="OrderExec")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_orders_batch(self, orders: List[Dict[str, Any]], 
                           market_data: Dict[str, float]) -> List[Dict[str, Any]]:
        """Process orders in batches for optimal performance"""
        if not orders:
            return []
        
        # Group orders by symbol for efficient processing
        orders_by_symbol = self._group_orders_by_symbol(orders)
        
        # Process each symbol group in parallel
        futures = []
        for symbol, symbol_orders in orders_by_symbol.items():
            symbol_price = market_data.get(symbol, 100.0)  # Default price
            future = self.executor.submit(self._process_symbol_orders, symbol, symbol_orders, symbol_price)
            futures.append(future)
        
        # Collect all results
        all_results = []
        for future in as_completed(futures, timeout=2.0):  # 2s timeout
            try:
                symbol_results = future.result()
                all_results.extend(symbol_results)
            except Exception as e:
                self.logger.warning(f"Symbol order processing failed: {e}")
        
        return all_results
    
    def _group_orders_by_symbol(self, orders: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group orders by symbol for batch processing"""
        groups = {}
        for order in orders:
            symbol = order.get('symbol', 'UNKNOWN')
            if symbol not in groups:
                groups[symbol] = []
            groups[symbol].append(order)
        return groups
    
    def _process_symbol_orders(self, symbol: str, orders: List[Dict[str, Any]], 
                             current_price: float) -> List[Dict[str, Any]]:
        """Process all orders for a single symbol"""
        results = []
        
        # Sort orders by priority (market orders first, then by price)
        sorted_orders = self._sort_orders_by_priority(orders)
        
        for order in sorted_orders:
            try:
                result = self._execute_single_order(order, current_price)
                results.append(result)
                
                # Update price based on market impact
                current_price = self._calculate_price_impact(current_price, order, result)
                
            except Exception as e:
                self.logger.error(f"Order execution failed for {symbol}: {e}")
                results.append(self._create_rejected_order(order, str(e)))
        
        return results
    
    def _sort_orders_by_priority(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort orders by execution priority"""
        def priority_key(order):
            order_type = order.get('type', OrderType.MARKET.value)
            timestamp = order.get('timestamp', datetime.now()).timestamp()
            
            # Market orders have highest priority, then by timestamp
            if order_type == OrderType.MARKET.value:
                return (0, timestamp)
            else:
                return (1, timestamp)
        
        return sorted(orders, key=priority_key)
    
    def _execute_single_order(self, order: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Execute a single order"""
        order_id = order.get('order_id', str(uuid.uuid4()))
        symbol = order.get('symbol', 'UNKNOWN')
        quantity = order.get('quantity', 0)
        order_type = order.get('type', OrderType.MARKET.value)
        limit_price = order.get('price', current_price)
        
        # Determine execution price
        if order_type == OrderType.MARKET.value:
            execution_price = current_price
            fill_status = OrderStatus.FILLED.value
        elif order_type == OrderType.LIMIT.value:
            if (quantity > 0 and current_price <= limit_price) or \
               (quantity < 0 and current_price >= limit_price):
                execution_price = limit_price
                fill_status = OrderStatus.FILLED.value
            else:
                execution_price = 0.0
                fill_status = OrderStatus.PENDING.value
        else:
            # Stop orders, etc.
            execution_price = current_price
            fill_status = OrderStatus.FILLED.value
        
        # Calculate execution details
        if fill_status == OrderStatus.FILLED.value:
            commission = abs(quantity * execution_price * 0.0005)  # 5 bps commission
            slippage = abs(quantity * execution_price * 0.0005)     # 5 bps slippage
            total_cost = abs(quantity * execution_price) + commission + slippage
        else:
            commission = 0.0
            slippage = 0.0
            total_cost = 0.0
        
        return {
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity if fill_status == OrderStatus.FILLED.value else 0,
            'execution_price': execution_price,
            'status': fill_status,
            'commission': commission,
            'slippage': slippage,
            'total_cost': total_cost,
            'execution_time': datetime.now(),
            'original_order': order
        }
    
    def _calculate_price_impact(self, current_price: float, order: Dict[str, Any], 
                              result: Dict[str, Any]) -> float:
        """Calculate price impact from order execution"""
        if result['status'] != OrderStatus.FILLED.value:
            return current_price
        
        quantity = abs(order.get('quantity', 0))
        
        # Simple linear price impact model
        impact_bps = min(quantity / 10000 * 5, 20)  # Max 20 bps impact
        impact_factor = 1 + (impact_bps / 10000)
        
        # Buy orders increase price, sell orders decrease price
        if order.get('quantity', 0) > 0:
            return current_price * impact_factor
        else:
            return current_price / impact_factor
    
    def _create_rejected_order(self, order: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Create rejected order result"""
        return {
            'order_id': order.get('order_id', str(uuid.uuid4())),
            'symbol': order.get('symbol', 'UNKNOWN'),
            'quantity': 0,
            'execution_price': 0.0,
            'status': OrderStatus.REJECTED.value,
            'commission': 0.0,
            'slippage': 0.0,
            'total_cost': 0.0,
            'execution_time': datetime.now(),
            'rejection_reason': reason,
            'original_order': order
        }
    
    def __del__(self):
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

class VectorizedPnLCalculator:
    """Vectorized P&L and performance calculations"""
    
    @staticmethod
    def calculate_batch_pnl(executions: List[Dict[str, Any]], 
                           current_prices: Dict[str, float]) -> Dict[str, float]:
        """Calculate P&L for batch of executions using vectorized operations"""
        if not executions:
            return {}
        
        # Group executions by symbol
        symbol_executions = {}
        for execution in executions:
            symbol = execution.get('symbol', 'UNKNOWN')
            if symbol not in symbol_executions:
                symbol_executions[symbol] = []
            symbol_executions[symbol].append(execution)
        
        # Calculate P&L for each symbol
        symbol_pnl = {}
        for symbol, symbol_execs in symbol_executions.items():
            if symbol in current_prices:
                pnl = VectorizedPnLCalculator._calculate_symbol_pnl(symbol_execs, current_prices[symbol])
                symbol_pnl[symbol] = pnl
        
        return symbol_pnl
    
    @staticmethod
    def _calculate_symbol_pnl(executions: List[Dict[str, Any]], current_price: float) -> float:
        """Calculate P&L for a single symbol using vectorized operations"""
        # Extract quantities and prices
        quantities = np.array([exec.get('quantity', 0) for exec in executions])
        prices = np.array([exec.get('execution_price', 0) for exec in executions])
        
        # Calculate position and average price
        total_quantity = np.sum(quantities)
        if total_quantity != 0:
            avg_price = np.sum(quantities * prices) / total_quantity
            unrealized_pnl = total_quantity * (current_price - avg_price)
        else:
            unrealized_pnl = 0.0
        
        return unrealized_pnl

class HighPerformanceExecutionEngine:
    """
    Ultra-fast execution engine designed to achieve 1,000+ orders/second
    with sub-3ms latency using batch processing and parallel execution.
    """
    
    def __init__(self, config: Optional[ExecutionEngineConfig] = None):
        self.config = config or ExecutionEngineConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # High-performance components
        if self.config.enable_batch_execution:
            self.batch_processor = BatchOrderProcessor(self.config.max_workers)
        
        self.pnl_calculator = VectorizedPnLCalculator()
        
        # Execution tracking
        self.execution_history: List[Dict[str, Any]] = []
        self.pending_orders: List[Dict[str, Any]] = []
        self.execution_lock = threading.RLock()
        
        # Performance tracking
        self.execution_times: List[float] = []
        self.order_counts: List[int] = []
        self.total_orders_processed = 0
        self.total_value_executed = 0.0
        
        self.logger.info(f"HighPerformanceExecutionEngine initialized - Target: {self.config.target_orders_per_second} orders/sec")
    
    def execute_orders(self, orders: List[Dict[str, Any]], 
                      market_data: Dict[str, float]) -> ExecutionResult:
        """
        Execute orders with high-throughput batch processing
        """
        start_time = time.perf_counter()
        optimization_techniques = []
        
        try:
            if not orders:
                return self._create_empty_result(start_time)
            
            # Validate orders first
            valid_orders = self._validate_orders(orders)
            if not valid_orders:
                return self._create_empty_result(start_time)
            
            # Choose execution strategy
            if len(valid_orders) > 1 and self.config.enable_batch_execution:
                # Batch execution for multiple orders
                execution_results = self.batch_processor.process_orders_batch(valid_orders, market_data)
                optimization_techniques.append("batch_execution")
                
                if self.config.enable_parallel_execution:
                    optimization_techniques.append("parallel_execution")
            else:
                # Sequential execution
                execution_results = []
                for order in valid_orders:
                    result = self._execute_single_order_direct(order, market_data)
                    execution_results.append(result)
                optimization_techniques.append("sequential_execution")
            
            # Calculate P&L if enabled
            if self.config.enable_market_impact_calculation:
                self._update_pnl_calculations(execution_results, market_data)
                optimization_techniques.append("vectorized_pnl")
            
            # Store execution history
            with self.execution_lock:
                self.execution_history.extend(execution_results)
                if len(self.execution_history) > 10000:  # Keep last 10k executions
                    self.execution_history = self.execution_history[-10000:]
            
            return self._create_result(start_time, execution_results, optimization_techniques)
            
        except Exception as e:
            self.logger.error(f"High-performance order execution failed: {e}")
            return self._create_error_result(start_time, len(orders))
    
    def _validate_orders(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate orders before execution"""
        valid_orders = []
        
        for order in orders:
            # Basic validation
            if (order.get('symbol') and 
                order.get('quantity') is not None and 
                order.get('quantity') != 0):
                
                # Add order ID if missing
                if 'order_id' not in order:
                    order['order_id'] = str(uuid.uuid4())
                
                # Add timestamp if missing
                if 'timestamp' not in order:
                    order['timestamp'] = datetime.now()
                
                valid_orders.append(order)
            else:
                self.logger.warning(f"Invalid order rejected: {order}")
        
        return valid_orders
    
    def _execute_single_order_direct(self, order: Dict[str, Any], 
                                   market_data: Dict[str, float]) -> Dict[str, Any]:
        """Direct single order execution"""
        symbol = order.get('symbol', 'UNKNOWN')
        current_price = market_data.get(symbol, 100.0)
        
        try:
            return self.batch_processor._execute_single_order(order, current_price)
        except Exception as e:
            return self.batch_processor._create_rejected_order(order, str(e))
    
    def _update_pnl_calculations(self, execution_results: List[Dict[str, Any]], 
                               market_data: Dict[str, float]) -> None:
        """Update P&L calculations using vectorized operations"""
        try:
            filled_executions = [result for result in execution_results 
                               if result['status'] == OrderStatus.FILLED.value]
            
            if filled_executions:
                symbol_pnl = self.pnl_calculator.calculate_batch_pnl(filled_executions, market_data)
                
                # Store P&L information
                for result in execution_results:
                    symbol = result.get('symbol', 'UNKNOWN')
                    if symbol in symbol_pnl:
                        result['unrealized_pnl'] = symbol_pnl[symbol]
                
        except Exception as e:
            self.logger.warning(f"P&L calculation failed: {e}")
    
    def _create_result(self, start_time: float, execution_results: List[Dict[str, Any]], 
                      optimization_techniques: List[str]) -> ExecutionResult:
        """Create execution result with performance metrics"""
        processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
        orders_processed = len(execution_results)
        
        # Count filled and rejected orders
        filled_orders = sum(1 for result in execution_results 
                          if result['status'] == OrderStatus.FILLED.value)
        rejected_orders = sum(1 for result in execution_results 
                            if result['status'] == OrderStatus.REJECTED.value)
        
        # Calculate total value and average price
        total_value = sum(abs(result.get('quantity', 0) * result.get('execution_price', 0))
                         for result in execution_results 
                         if result['status'] == OrderStatus.FILLED.value)
        
        filled_results = [result for result in execution_results 
                         if result['status'] == OrderStatus.FILLED.value and result.get('execution_price', 0) > 0]
        
        if filled_results:
            total_quantity = sum(abs(result.get('quantity', 0)) for result in filled_results)
            weighted_price_sum = sum(abs(result.get('quantity', 0)) * result.get('execution_price', 0) 
                                   for result in filled_results)
            avg_fill_price = weighted_price_sum / total_quantity if total_quantity > 0 else 0.0
        else:
            avg_fill_price = 0.0
        
        # Update performance tracking
        self.execution_times.append(processing_time)
        self.order_counts.append(orders_processed)
        self.total_orders_processed += orders_processed
        self.total_value_executed += total_value
        
        # Keep only recent measurements
        if len(self.execution_times) > 1000:
            self.execution_times = self.execution_times[-1000:]
            self.order_counts = self.order_counts[-1000:]
        
        # Calculate orders per second
        orders_per_second = (orders_processed / (processing_time / 1000)) if processing_time > 0 else 0
        
        return ExecutionResult(
            orders_processed=orders_processed,
            orders_filled=filled_orders,
            orders_rejected=rejected_orders,
            processing_time_ms=processing_time,
            orders_per_second=orders_per_second,
            total_value_executed=total_value,
            average_fill_price=avg_fill_price,
            optimization_techniques_used=optimization_techniques
        )
    
    def _create_empty_result(self, start_time: float) -> ExecutionResult:
        """Create empty result for no orders"""
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return ExecutionResult(
            orders_processed=0,
            orders_filled=0,
            orders_rejected=0,
            processing_time_ms=processing_time,
            orders_per_second=0.0,
            total_value_executed=0.0,
            average_fill_price=0.0,
            optimization_techniques_used=["no_orders"]
        )
    
    def _create_error_result(self, start_time: float, order_count: int) -> ExecutionResult:
        """Create error result for failed execution"""
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return ExecutionResult(
            orders_processed=order_count,
            orders_filled=0,
            orders_rejected=order_count,
            processing_time_ms=processing_time,
            orders_per_second=0.0,
            total_value_executed=0.0,
            average_fill_price=0.0,
            optimization_techniques_used=["error_fallback"]
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        if not self.execution_times:
            return {}
        
        avg_processing_time = np.mean(self.execution_times)
        avg_orders_per_batch = np.mean(self.order_counts)
        avg_orders_per_second = avg_orders_per_batch / (avg_processing_time / 1000) if avg_processing_time > 0 else 0
        
        return {
            'average_processing_time_ms': avg_processing_time,
            'average_orders_per_batch': avg_orders_per_batch,
            'average_orders_per_second': avg_orders_per_second,
            'total_orders_processed': self.total_orders_processed,
            'total_value_executed': self.total_value_executed,
            'target_orders_per_second': self.config.target_orders_per_second,
            'target_latency_ms': self.config.target_latency_ms,
            'throughput_target_achieved': avg_orders_per_second >= self.config.target_orders_per_second,
            'latency_target_achieved': avg_processing_time <= self.config.target_latency_ms
        }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        with self.execution_lock:
            recent_executions = self.execution_history[-1000:] if self.execution_history else []
            
            if not recent_executions:
                return {'total_executions': 0}
            
            filled_count = sum(1 for ex in recent_executions if ex['status'] == OrderStatus.FILLED.value)
            rejected_count = sum(1 for ex in recent_executions if ex['status'] == OrderStatus.REJECTED.value)
            
            return {
                'total_executions': len(recent_executions),
                'filled_orders': filled_count,
                'rejected_orders': rejected_count,
                'fill_rate': (filled_count / len(recent_executions)) * 100 if recent_executions else 0,
                'total_value_executed': self.total_value_executed
            }
