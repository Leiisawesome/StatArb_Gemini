"""
Batch Processor
==============

High-performance batch processing implementation for efficient processing
of large volumes of market data, signals, and trading operations.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Iterator, TypeVar, Generic
from datetime import datetime, timedelta
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class BatchConfig:
    """Configuration for batch processing"""
    batch_size: int = 1000
    max_batch_wait_ms: int = 100
    enable_parallel_batches: bool = True
    max_concurrent_batches: int = 4
    enable_batch_compression: bool = True
    enable_batch_caching: bool = True
    memory_threshold_mb: int = 500
    enable_adaptive_batching: bool = True

@dataclass
class BatchResult:
    """Result of batch processing operation"""
    total_items_processed: int
    total_batches: int
    average_batch_size: float
    total_processing_time_ms: float
    average_batch_time_ms: float
    throughput_items_per_second: float
    memory_usage_mb: float
    optimization_techniques: List[str] = field(default_factory=list)

class BatchBuffer(Generic[T]):
    """Thread-safe batch buffer for collecting items"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
    
    def add(self, item: T) -> bool:
        """Add item to buffer"""
        with self._condition:
            if len(self._buffer) < self.max_size:
                self._buffer.append(item)
                self._condition.notify()
                return True
            return False
    
    def get_batch(self, batch_size: int, timeout: float = 0.1) -> List[T]:
        """Get a batch of items from buffer"""
        with self._condition:
            # Wait for items or timeout
            end_time = time.time() + timeout
            while len(self._buffer) < batch_size and time.time() < end_time:
                remaining_time = end_time - time.time()
                if remaining_time > 0:
                    self._condition.wait(remaining_time)
                else:
                    break
            
            # Extract available items
            batch = []
            while self._buffer and len(batch) < batch_size:
                batch.append(self._buffer.popleft())
            
            return batch
    
    def size(self) -> int:
        """Get current buffer size"""
        with self._lock:
            return len(self._buffer)
    
    def clear(self):
        """Clear the buffer"""
        with self._lock:
            self._buffer.clear()

class BatchProcessor:
    """
    High-performance batch processor that efficiently processes large volumes
    of market data, signals, and trading operations in optimized batches.
    """
    
    def __init__(self, config: Optional[BatchConfig] = None):
        self.config = config or BatchConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Processing statistics
        self.stats = {
            'total_items_processed': 0,
            'total_batches': 0,
            'total_processing_time': 0.0,
            'last_processing_time': 0.0
        }
        
        # Batch buffers for different data types
        self.buffers: Dict[str, BatchBuffer] = {}
        
        # Thread pool for parallel batch processing
        if self.config.enable_parallel_batches:
            self.executor = ThreadPoolExecutor(
                max_workers=self.config.max_concurrent_batches,
                thread_name_prefix="BatchProcessor"
            )
        else:
            self.executor = None
        
        # Adaptive batching parameters
        self.adaptive_batch_size = self.config.batch_size
        self.recent_processing_times = deque(maxlen=10)
        
        self.logger.info(f"BatchProcessor initialized with batch_size={self.config.batch_size}")
    
    def optimize_core_engine_batching(self, core_engine) -> BatchResult:
        """
        Optimize batch processing across all core engine components
        """
        self.logger.info("Starting core engine batch processing optimization")
        
        start_time = time.perf_counter()
        optimization_techniques = []
        
        # 1. Optimize signal generation batching
        if hasattr(core_engine, 'signal_generator'):
            self._optimize_signal_generation_batching(core_engine.signal_generator)
            optimization_techniques.append("signal_generation_batching")
        
        # 2. Optimize execution engine batching
        if hasattr(core_engine, 'execution_engine'):
            self._optimize_execution_batching(core_engine.execution_engine)
            optimization_techniques.append("execution_batching")
        
        # 3. Optimize risk management batching
        if hasattr(core_engine, 'risk_manager'):
            self._optimize_risk_management_batching(core_engine.risk_manager)
            optimization_techniques.append("risk_management_batching")
        
        # 4. Optimize data manager batching
        if hasattr(core_engine, 'data_manager'):
            self._optimize_data_manager_batching(core_engine.data_manager)
            optimization_techniques.append("data_manager_batching")
        
        # 5. Optimize portfolio manager batching
        if hasattr(core_engine, 'portfolio_manager'):
            self._optimize_portfolio_batching(core_engine.portfolio_manager)
            optimization_techniques.append("portfolio_batching")
        
        total_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
        
        # Calculate results
        total_batches = self.stats['total_batches']
        avg_batch_size = (self.stats['total_items_processed'] / total_batches) if total_batches > 0 else 0
        avg_batch_time = (self.stats['total_processing_time'] / total_batches) if total_batches > 0 else 0
        throughput = (self.stats['total_items_processed'] / (total_time / 1000)) if total_time > 0 else 0
        
        result = BatchResult(
            total_items_processed=self.stats['total_items_processed'],
            total_batches=total_batches,
            average_batch_size=avg_batch_size,
            total_processing_time_ms=total_time,
            average_batch_time_ms=avg_batch_time * 1000,  # Convert to ms
            throughput_items_per_second=throughput,
            memory_usage_mb=self._get_memory_usage(),
            optimization_techniques=optimization_techniques
        )
        
        self.logger.info(f"Batch processing optimization completed: {throughput:.0f} items/sec")
        
        return result
    
    def _optimize_signal_generation_batching(self, signal_generator):
        """Optimize signal generation for batch processing"""
        self.logger.info("Optimizing signal generation batching")
        
        # Create buffer for signal data
        if 'signals' not in self.buffers:
            self.buffers['signals'] = BatchBuffer(max_size=10000)
        
        # Replace individual signal processing with batch processing
        if hasattr(signal_generator, 'process_market_data'):
            original_process = signal_generator.process_market_data
            
            def batch_process_market_data(market_data_list):
                if len(market_data_list) > self.config.batch_size:
                    # Process in batches
                    results = []
                    batches = self._create_batches(market_data_list, self.adaptive_batch_size)
                    
                    if self.executor:
                        # Parallel batch processing
                        futures = []
                        for batch in batches:
                            future = self.executor.submit(self._process_signal_batch, batch, original_process)
                            futures.append(future)
                        
                        # Collect results
                        for future in as_completed(futures):
                            try:
                                batch_results = future.result()
                                results.extend(batch_results)
                            except Exception as e:
                                self.logger.warning(f"Signal batch processing failed: {e}")
                    else:
                        # Sequential batch processing
                        for batch in batches:
                            batch_results = self._process_signal_batch(batch, original_process)
                            results.extend(batch_results)
                    
                    return results
                else:
                    return [original_process(data) for data in market_data_list]
            
            signal_generator.batch_process_market_data = batch_process_market_data
    
    def _optimize_execution_batching(self, execution_engine):
        """Optimize execution engine for batch order processing"""
        self.logger.info("Optimizing execution batching")
        
        # Create buffer for orders
        if 'orders' not in self.buffers:
            self.buffers['orders'] = BatchBuffer(max_size=5000)
        
        # Implement batch order execution
        if hasattr(execution_engine, 'execute_order'):
            original_execute = execution_engine.execute_order
            
            def batch_execute_orders(orders):
                if len(orders) > 1:
                    # Group orders by symbol for efficient execution
                    orders_by_symbol = {}
                    for order in orders:
                        symbol = getattr(order, 'symbol', 'unknown')
                        if symbol not in orders_by_symbol:
                            orders_by_symbol[symbol] = []
                        orders_by_symbol[symbol].append(order)
                    
                    # Execute orders by symbol in batches
                    results = []
                    for symbol, symbol_orders in orders_by_symbol.items():
                        batch_results = self._execute_symbol_batch(symbol_orders, original_execute)
                        results.extend(batch_results)
                    
                    return results
                else:
                    return [original_execute(order) for order in orders]
            
            execution_engine.batch_execute_orders = batch_execute_orders
    
    def _optimize_risk_management_batching(self, risk_manager):
        """Optimize risk management for batch validation"""
        self.logger.info("Optimizing risk management batching")
        
        # Create buffer for risk checks
        if 'risk_checks' not in self.buffers:
            self.buffers['risk_checks'] = BatchBuffer(max_size=5000)
        
        # Implement batch risk validation
        if hasattr(risk_manager, 'validate_trade'):
            original_validate = risk_manager.validate_trade
            
            def batch_validate_trades(trades):
                if len(trades) > self.config.batch_size:
                    # Process risk checks in batches
                    batches = self._create_batches(trades, self.adaptive_batch_size)
                    results = []
                    
                    for batch in batches:
                        batch_results = self._validate_risk_batch(batch, original_validate)
                        results.extend(batch_results)
                    
                    return results
                else:
                    return [original_validate(trade) for trade in trades]
            
            risk_manager.batch_validate_trades = batch_validate_trades
    
    def _optimize_data_manager_batching(self, data_manager):
        """Optimize data manager for batch data processing"""
        self.logger.info("Optimizing data manager batching")
        
        # Create buffer for market data
        if 'market_data' not in self.buffers:
            self.buffers['market_data'] = BatchBuffer(max_size=20000)
        
        # Implement batch data loading
        if hasattr(data_manager, 'load_data'):
            original_load = data_manager.load_data
            
            def batch_load_data(symbols):
                if len(symbols) > 1:
                    # Load data for multiple symbols efficiently
                    if self.config.enable_parallel_batches and self.executor:
                        # Parallel data loading
                        symbol_batches = self._create_batches(symbols, max(1, len(symbols) // self.config.max_concurrent_batches))
                        
                        futures = []
                        for batch in symbol_batches:
                            future = self.executor.submit(self._load_data_batch, batch, original_load)
                            futures.append(future)
                        
                        # Collect results
                        results = {}
                        for future in as_completed(futures):
                            try:
                                batch_results = future.result()
                                results.update(batch_results)
                            except Exception as e:
                                self.logger.warning(f"Data loading batch failed: {e}")
                        
                        return results
                    else:
                        # Sequential batch loading
                        return self._load_data_batch(symbols, original_load)
                else:
                    return {symbols[0]: original_load(symbols[0])} if symbols else {}
            
            data_manager.batch_load_data = batch_load_data
    
    def _optimize_portfolio_batching(self, portfolio_manager):
        """Optimize portfolio manager for batch updates"""
        self.logger.info("Optimizing portfolio batching")
        
        # Create buffer for portfolio updates
        if 'portfolio_updates' not in self.buffers:
            self.buffers['portfolio_updates'] = BatchBuffer(max_size=5000)
        
        # Implement batch portfolio updates
        if hasattr(portfolio_manager, 'update_position'):
            original_update = portfolio_manager.update_position
            
            def batch_update_positions(position_updates):
                if len(position_updates) > 1:
                    # Group updates by symbol to minimize locking
                    updates_by_symbol = {}
                    for update in position_updates:
                        symbol = update.get('symbol', 'unknown')
                        if symbol not in updates_by_symbol:
                            updates_by_symbol[symbol] = []
                        updates_by_symbol[symbol].append(update)
                    
                    # Apply updates by symbol
                    results = []
                    for symbol, symbol_updates in updates_by_symbol.items():
                        batch_result = self._update_positions_batch(symbol_updates, original_update)
                        results.append(batch_result)
                    
                    return results
                else:
                    return [original_update(update) for update in position_updates]
            
            portfolio_manager.batch_update_positions = batch_update_positions
    
    def _create_batches(self, items: List[T], batch_size: int) -> List[List[T]]:
        """Create batches from a list of items"""
        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batches.append(batch)
        return batches
    
    def _process_signal_batch(self, batch: List, original_process: Callable) -> List:
        """Process a batch of signals"""
        start_time = time.perf_counter()
        
        try:
            # Process batch
            results = []
            for item in batch:
                result = original_process(item)
                results.append(result)
            
            # Update statistics
            processing_time = time.perf_counter() - start_time
            self._update_stats(len(batch), processing_time)
            
            return results
        
        except Exception as e:
            self.logger.error(f"Signal batch processing failed: {e}")
            return []
    
    def _execute_symbol_batch(self, orders: List, original_execute: Callable) -> List:
        """Execute a batch of orders for the same symbol"""
        start_time = time.perf_counter()
        
        try:
            # Execute orders for symbol
            results = []
            for order in orders:
                result = original_execute(order)
                results.append(result)
            
            # Update statistics
            processing_time = time.perf_counter() - start_time
            self._update_stats(len(orders), processing_time)
            
            return results
        
        except Exception as e:
            self.logger.error(f"Order batch execution failed: {e}")
            return []
    
    def _validate_risk_batch(self, trades: List, original_validate: Callable) -> List:
        """Validate a batch of trades for risk"""
        start_time = time.perf_counter()
        
        try:
            # Validate trades
            results = []
            for trade in trades:
                result = original_validate(trade)
                results.append(result)
            
            # Update statistics
            processing_time = time.perf_counter() - start_time
            self._update_stats(len(trades), processing_time)
            
            return results
        
        except Exception as e:
            self.logger.error(f"Risk batch validation failed: {e}")
            return [False] * len(trades)
    
    def _load_data_batch(self, symbols: List[str], original_load: Callable) -> Dict:
        """Load data for a batch of symbols"""
        start_time = time.perf_counter()
        
        try:
            # Load data for symbols
            results = {}
            for symbol in symbols:
                data = original_load(symbol)
                results[symbol] = data
            
            # Update statistics
            processing_time = time.perf_counter() - start_time
            self._update_stats(len(symbols), processing_time)
            
            return results
        
        except Exception as e:
            self.logger.error(f"Data batch loading failed: {e}")
            return {}
    
    def _update_positions_batch(self, updates: List[Dict], original_update: Callable) -> bool:
        """Update positions in batch"""
        start_time = time.perf_counter()
        
        try:
            # Apply position updates
            for update in updates:
                original_update(update)
            
            # Update statistics
            processing_time = time.perf_counter() - start_time
            self._update_stats(len(updates), processing_time)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Position batch update failed: {e}")
            return False
    
    def _update_stats(self, items_processed: int, processing_time: float):
        """Update processing statistics"""
        self.stats['total_items_processed'] += items_processed
        self.stats['total_batches'] += 1
        self.stats['total_processing_time'] += processing_time
        self.stats['last_processing_time'] = processing_time
        
        # Update adaptive batching
        if self.config.enable_adaptive_batching:
            self.recent_processing_times.append(processing_time)
            self._adjust_batch_size()
    
    def _adjust_batch_size(self):
        """Adjust batch size based on recent performance"""
        if len(self.recent_processing_times) >= 5:
            avg_time = sum(self.recent_processing_times) / len(self.recent_processing_times)
            
            # Target processing time: 10ms per batch
            target_time = 0.01
            
            if avg_time > target_time * 1.5:
                # Reduce batch size if processing is too slow
                self.adaptive_batch_size = max(100, int(self.adaptive_batch_size * 0.8))
            elif avg_time < target_time * 0.5:
                # Increase batch size if processing is too fast
                self.adaptive_batch_size = min(10000, int(self.adaptive_batch_size * 1.2))
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0
    
    def get_buffer_status(self) -> Dict[str, int]:
        """Get status of all buffers"""
        return {name: buffer.size() for name, buffer in self.buffers.items()}
    
    def clear_all_buffers(self):
        """Clear all batch buffers"""
        for buffer in self.buffers.values():
            buffer.clear()
        self.logger.info("All batch buffers cleared")
    
    def __del__(self):
        """Cleanup resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
