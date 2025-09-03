"""
Async/Await Optimization - Phase 2 Batch 3
==========================================

Comprehensive async/await patterns for maximum concurrency and performance.
Eliminates blocking operations and enables true parallel processing.

Features:
- Advanced async patterns for trading operations
- Concurrent execution with proper resource management
- Async context managers and utilities
- Performance monitoring for async operations
- Deadlock prevention and timeout management

Author: Professional Trading System Architecture
Version: 2.0 (Async Optimized)
"""

import asyncio
import time
import logging
import functools
from typing import Dict, Any, Optional, List, Callable, Awaitable, Union, TypeVar, Generic, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
import threading
import weakref
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')

# ================================================================================
# ASYNC PERFORMANCE MONITORING
# ================================================================================

@dataclass
class AsyncOperationMetrics:
    """Metrics for async operation performance"""
    operation_name: str
    total_calls: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    concurrent_calls: int = 0
    max_concurrent: int = 0
    timeout_count: int = 0
    error_count: int = 0
    last_call_time: Optional[datetime] = None
    
    def update(self, execution_time_ms: float, concurrent_count: int = 0, 
               timeout: bool = False, error: bool = False):
        """Update metrics with new execution data"""
        self.total_calls += 1
        self.total_time_ms += execution_time_ms
        self.min_time_ms = min(self.min_time_ms, execution_time_ms)
        self.max_time_ms = max(self.max_time_ms, execution_time_ms)
        self.max_concurrent = max(self.max_concurrent, concurrent_count)
        self.last_call_time = datetime.now()
        
        if timeout:
            self.timeout_count += 1
        if error:
            self.error_count += 1
    
    def get_average_time_ms(self) -> float:
        """Get average execution time"""
        return self.total_time_ms / self.total_calls if self.total_calls > 0 else 0.0
    
    def get_success_rate(self) -> float:
        """Get operation success rate"""
        if self.total_calls == 0:
            return 0.0
        return (self.total_calls - self.error_count - self.timeout_count) / self.total_calls

class AsyncPerformanceMonitor:
    """Monitor performance of async operations"""
    
    def __init__(self):
        self.metrics: Dict[str, AsyncOperationMetrics] = {}
        self.active_operations: Dict[str, int] = {}  # Track concurrent operations
        self.lock = threading.RLock()
        
    def start_operation(self, operation_name: str) -> str:
        """Start tracking an async operation"""
        operation_id = f"{operation_name}_{int(time.time() * 1000000)}"
        
        with self.lock:
            if operation_name not in self.metrics:
                self.metrics[operation_name] = AsyncOperationMetrics(operation_name)
            
            self.active_operations[operation_id] = time.perf_counter()
            
            # Update concurrent count
            concurrent_count = sum(1 for op_id in self.active_operations.keys() 
                                 if op_id.startswith(operation_name))
            self.metrics[operation_name].concurrent_calls = concurrent_count
        
        return operation_id
    
    def end_operation(self, operation_id: str, timeout: bool = False, error: bool = False):
        """End tracking an async operation"""
        if operation_id not in self.active_operations:
            return
        
        start_time = self.active_operations.pop(operation_id)
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Extract operation name from ID
        operation_name = operation_id.rsplit('_', 1)[0]
        
        with self.lock:
            if operation_name in self.metrics:
                concurrent_count = sum(1 for op_id in self.active_operations.keys() 
                                     if op_id.startswith(operation_name))
                self.metrics[operation_name].update(
                    execution_time_ms, concurrent_count, timeout, error
                )
    
    def get_metrics(self, operation_name: str) -> Optional[AsyncOperationMetrics]:
        """Get metrics for specific operation"""
        with self.lock:
            return self.metrics.get(operation_name)
    
    def get_all_metrics(self) -> Dict[str, AsyncOperationMetrics]:
        """Get all async operation metrics"""
        with self.lock:
            return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self.lock:
            self.metrics.clear()
            self.active_operations.clear()

# Global async performance monitor
async_monitor = AsyncPerformanceMonitor()

# ================================================================================
# ASYNC DECORATORS AND UTILITIES
# ================================================================================

def async_timed(operation_name: str = None, timeout: float = None):
    """
    Decorator for timing and monitoring async operations.
    
    Args:
        operation_name: Name for monitoring (defaults to function name)
        timeout: Timeout in seconds for the operation
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            operation_id = async_monitor.start_operation(op_name)
            
            timeout_occurred = False
            error_occurred = False
            
            try:
                if timeout:
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                else:
                    result = await func(*args, **kwargs)
                return result
                
            except asyncio.TimeoutError:
                timeout_occurred = True
                logger.warning(f"Async operation {op_name} timed out after {timeout}s")
                raise
            except Exception as e:
                error_occurred = True
                logger.error(f"Async operation {op_name} failed: {e}")
                raise
            finally:
                async_monitor.end_operation(operation_id, timeout_occurred, error_occurred)
        
        return wrapper
    return decorator

def async_retry(max_retries: int = 3, delay: float = 0.1, backoff: float = 2.0):
    """
    Decorator for retrying async operations with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"Async operation {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    
                    logger.debug(f"Async operation {func.__name__} attempt {attempt + 1} failed, retrying in {current_delay}s: {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            # Should never reach here, but for type safety
            raise RuntimeError("Unexpected end of retry loop")
        
        return wrapper
    return decorator

# ================================================================================
# CONCURRENT EXECUTION PATTERNS
# ================================================================================

class ConcurrencyLimiter:
    """Limit concurrent async operations to prevent resource exhaustion"""
    
    def __init__(self, max_concurrent: int):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self.active_count = 0
        
    async def __aenter__(self):
        await self.semaphore.acquire()
        self.active_count += 1
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.semaphore.release()
        self.active_count -= 1
    
    def get_active_count(self) -> int:
        """Get current number of active operations"""
        return self.active_count

class AsyncBatchProcessor:
    """Process items in async batches with concurrency control"""
    
    def __init__(self, batch_size: int = 50, max_concurrent: int = 10):
        self.batch_size = batch_size
        self.limiter = ConcurrencyLimiter(max_concurrent)
        
    @async_timed("batch_process")
    async def process_batch(self, items: List[T], 
                          processor: Callable[[T], Awaitable[Any]]) -> List[Any]:
        """Process items in concurrent batches"""
        if not items:
            return []
        
        # Split into batches
        batches = [items[i:i + self.batch_size] 
                  for i in range(0, len(items), self.batch_size)]
        
        # Process batches concurrently
        batch_tasks = []
        for batch in batches:
            task = asyncio.create_task(self._process_single_batch(batch, processor))
            batch_tasks.append(task)
        
        # Wait for all batches to complete
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Flatten results and handle exceptions
        results = []
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"Batch processing failed: {batch_result}")
                continue
            
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)
        
        return results
    
    async def _process_single_batch(self, batch: List[T], 
                                  processor: Callable[[T], Awaitable[Any]]) -> List[Any]:
        """Process a single batch with concurrency limiting"""
        async with self.limiter:
            tasks = [asyncio.create_task(processor(item)) for item in batch]
            return await asyncio.gather(*tasks, return_exceptions=True)

# ================================================================================
# ASYNC CONTEXT MANAGERS
# ================================================================================

@asynccontextmanager
async def async_timeout_context(timeout_seconds: float, operation_name: str = "operation"):
    """Async context manager with timeout"""
    start_time = time.perf_counter()
    
    try:
        async with asyncio.timeout(timeout_seconds):
            yield
    except asyncio.TimeoutError:
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.warning(f"Async {operation_name} timed out after {elapsed:.2f}ms (limit: {timeout_seconds * 1000:.2f}ms)")
        raise
    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.error(f"Async {operation_name} failed after {elapsed:.2f}ms: {e}")
        raise

@asynccontextmanager
async def async_resource_manager(acquire_func: Callable[[], Awaitable[T]], 
                               release_func: Callable[[T], Awaitable[None]]):
    """Generic async resource manager"""
    resource = None
    try:
        resource = await acquire_func()
        yield resource
    finally:
        if resource is not None:
            try:
                await release_func(resource)
            except Exception as e:
                logger.error(f"Failed to release async resource: {e}")

# ================================================================================
# TRADING-SPECIFIC ASYNC PATTERNS
# ================================================================================

class AsyncTradingOperations:
    """Async patterns optimized for trading operations"""
    
    def __init__(self, max_concurrent_signals: int = 20, 
                 max_concurrent_executions: int = 10):
        self.signal_limiter = ConcurrencyLimiter(max_concurrent_signals)
        self.execution_limiter = ConcurrencyLimiter(max_concurrent_executions)
        self.batch_processor = AsyncBatchProcessor(batch_size=25, max_concurrent=5)
    
    @async_timed("parallel_signal_generation", timeout=5.0)
    @async_retry(max_retries=2, delay=0.05)
    async def generate_signals_parallel(self, strategies: List[Any], 
                                      market_data: Any) -> List[Any]:
        """Generate signals from multiple strategies in parallel"""
        async def generate_single_strategy_signals(strategy):
            async with self.signal_limiter:
                # Simulate strategy signal generation
                context = self._create_strategy_context(market_data)
                return await strategy.generate_signals(context)
        
        # Process strategies concurrently
        signal_tasks = [
            asyncio.create_task(generate_single_strategy_signals(strategy))
            for strategy in strategies
        ]
        
        # Wait for all strategies to complete
        strategy_results = await asyncio.gather(*signal_tasks, return_exceptions=True)
        
        # Flatten and filter results
        all_signals = []
        for result in strategy_results:
            if isinstance(result, Exception):
                logger.warning(f"Strategy signal generation failed: {result}")
                continue
            
            if isinstance(result, list):
                all_signals.extend(result)
        
        return all_signals
    
    @async_timed("parallel_order_execution", timeout=10.0)
    async def execute_orders_parallel(self, signals: List[Any], 
                                    execution_engine: Any) -> List[Any]:
        """Execute orders from signals in parallel with proper throttling"""
        async def execute_single_order(signal):
            async with self.execution_limiter:
                # Convert signal to execution request
                execution_request = self._signal_to_execution_request(signal)
                return await execution_engine.execute_order(execution_request)
        
        # Use batch processor for controlled concurrency
        return await self.batch_processor.process_batch(signals, execute_single_order)
    
    @async_timed("parallel_portfolio_updates")
    async def update_portfolio_parallel(self, execution_results: List[Any], 
                                      portfolio_manager: Any) -> Any:
        """Update portfolio with execution results in parallel"""
        # Group updates by symbol for batch processing
        symbol_updates = {}
        for result in execution_results:
            if hasattr(result, 'symbol'):
                symbol = result.symbol
                if symbol not in symbol_updates:
                    symbol_updates[symbol] = []
                symbol_updates[symbol].append(result)
        
        # Process symbol updates concurrently
        async def update_symbol_positions(symbol_results):
            symbol, results = symbol_results
            return await portfolio_manager.update_positions_batch(symbol, results)
        
        update_tasks = [
            asyncio.create_task(update_symbol_positions(item))
            for item in symbol_updates.items()
        ]
        
        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)
        
        return await portfolio_manager.get_portfolio_metrics()
    
    def _create_strategy_context(self, market_data: Any) -> Any:
        """Create strategy context (placeholder)"""
        # This would be implemented based on actual strategy context requirements
        return market_data
    
    def _signal_to_execution_request(self, signal: Any) -> Any:
        """Convert signal to execution request (placeholder)"""
        # This would be implemented based on actual signal and execution request types
        return signal

# ================================================================================
# ASYNC UTILITIES AND HELPERS
# ================================================================================

class AsyncTaskManager:
    """Manage long-running async tasks with proper cleanup"""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, Any] = {}
        self.lock = asyncio.Lock()
    
    async def start_task(self, task_name: str, coro: Awaitable[T], 
                        timeout: Optional[float] = None) -> str:
        """Start a named async task"""
        async with self.lock:
            # Cancel existing task with same name if it exists
            if task_name in self.tasks and not self.tasks[task_name].done():
                self.tasks[task_name].cancel()
            
            # Create new task
            if timeout:
                coro = asyncio.wait_for(coro, timeout=timeout)
            
            task = asyncio.create_task(coro)
            self.tasks[task_name] = task
            
            # Set up completion callback
            task.add_done_callback(lambda t: self._task_completed(task_name, t))
            
            return task_name
    
    def _task_completed(self, task_name: str, task: asyncio.Task):
        """Handle task completion"""
        try:
            if not task.cancelled():
                self.task_results[task_name] = task.result()
        except Exception as e:
            logger.error(f"Task {task_name} failed: {e}")
            self.task_results[task_name] = e
    
    async def get_task_result(self, task_name: str, wait: bool = True) -> Any:
        """Get result of a named task"""
        async with self.lock:
            if task_name not in self.tasks:
                raise ValueError(f"Task {task_name} not found")
            
            task = self.tasks[task_name]
            
            if wait and not task.done():
                try:
                    return await task
                except Exception as e:
                    logger.error(f"Task {task_name} failed while waiting: {e}")
                    return e
            
            return self.task_results.get(task_name)
    
    async def cancel_task(self, task_name: str) -> bool:
        """Cancel a named task"""
        async with self.lock:
            if task_name in self.tasks:
                task = self.tasks[task_name]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    return True
            return False
    
    async def cancel_all_tasks(self):
        """Cancel all managed tasks"""
        async with self.lock:
            for task_name in list(self.tasks.keys()):
                await self.cancel_task(task_name)
    
    def get_task_status(self) -> Dict[str, str]:
        """Get status of all managed tasks"""
        status = {}
        for task_name, task in self.tasks.items():
            if task.done():
                if task.cancelled():
                    status[task_name] = "cancelled"
                elif task.exception():
                    status[task_name] = "failed"
                else:
                    status[task_name] = "completed"
            else:
                status[task_name] = "running"
        return status

class AsyncEventBus:
    """Async event bus for decoupled communication"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.lock = asyncio.Lock()
    
    async def subscribe(self, event_type: str, handler: Callable[[Any], Awaitable[None]]):
        """Subscribe to an event type"""
        async with self.lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(handler)
    
    async def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type"""
        async with self.lock:
            if event_type in self.subscribers:
                try:
                    self.subscribers[event_type].remove(handler)
                except ValueError:
                    pass
    
    @async_timed("event_publish")
    async def publish(self, event_type: str, event_data: Any):
        """Publish an event to all subscribers"""
        async with self.lock:
            handlers = self.subscribers.get(event_type, []).copy()
        
        if not handlers:
            return
        
        # Execute all handlers concurrently
        tasks = []
        for handler in handlers:
            try:
                task = asyncio.create_task(handler(event_data))
                tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to create task for event handler: {e}")
        
        if tasks:
            # Wait for all handlers to complete, but don't fail if some do
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any handler failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Event handler {i} failed for {event_type}: {result}")

# ================================================================================
# ASYNC PERFORMANCE UTILITIES
# ================================================================================

async def async_benchmark(coro: Awaitable[T], iterations: int = 1) -> Dict[str, Any]:
    """Benchmark an async operation"""
    times = []
    results = []
    errors = []
    
    for i in range(iterations):
        start_time = time.perf_counter()
        try:
            result = await coro
            results.append(result)
        except Exception as e:
            errors.append(e)
        finally:
            execution_time = (time.perf_counter() - start_time) * 1000
            times.append(execution_time)
    
    return {
        'iterations': iterations,
        'total_time_ms': sum(times),
        'average_time_ms': sum(times) / len(times) if times else 0,
        'min_time_ms': min(times) if times else 0,
        'max_time_ms': max(times) if times else 0,
        'success_rate': (iterations - len(errors)) / iterations if iterations > 0 else 0,
        'error_count': len(errors),
        'results': results,
        'errors': errors
    }

async def async_race_with_timeout(coros: List[Awaitable[T]], 
                                timeout: float) -> Tuple[T, int]:
    """Race multiple coroutines with timeout, return first result and its index"""
    if not coros:
        raise ValueError("No coroutines provided")
    
    # Create tasks for all coroutines
    tasks = [asyncio.create_task(coro) for coro in coros]
    
    try:
        # Wait for first completion or timeout
        done, pending = await asyncio.wait(
            tasks, 
            timeout=timeout, 
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
        
        if not done:
            raise asyncio.TimeoutError("All operations timed out")
        
        # Get the first completed task
        completed_task = next(iter(done))
        result = await completed_task
        
        # Find the index of the completed task
        completed_index = tasks.index(completed_task)
        
        return result, completed_index
        
    except Exception:
        # Cancel all tasks on error
        for task in tasks:
            if not task.done():
                task.cancel()
        raise

# ================================================================================
# GLOBAL ASYNC COMPONENTS
# ================================================================================

# Global instances for async management
async_task_manager = AsyncTaskManager()
async_event_bus = AsyncEventBus()
async_trading_ops = AsyncTradingOperations()

# ================================================================================
# ASYNC REPORTING AND MONITORING
# ================================================================================

def get_async_performance_report() -> str:
    """Generate comprehensive async performance report"""
    metrics = async_monitor.get_all_metrics()
    
    if not metrics:
        return "No async performance data available"
    
    report = []
    report.append("=" * 80)
    report.append("ASYNC PERFORMANCE REPORT")
    report.append("=" * 80)
    
    # Sort by total time (most expensive operations first)
    sorted_metrics = sorted(
        metrics.values(),
        key=lambda m: m.total_time_ms,
        reverse=True
    )
    
    for metric in sorted_metrics:
        success_rate = metric.get_success_rate()
        avg_time = metric.get_average_time_ms()
        
        report.append(f"⚡ {metric.operation_name}:")
        report.append(f"  • Total Calls: {metric.total_calls:,}")
        report.append(f"  • Avg Time: {avg_time:.2f}ms")
        report.append(f"  • Min/Max: {metric.min_time_ms:.2f}ms / {metric.max_time_ms:.2f}ms")
        report.append(f"  • Success Rate: {success_rate:.1%}")
        report.append(f"  • Max Concurrent: {metric.max_concurrent}")
        report.append(f"  • Timeouts: {metric.timeout_count}")
        report.append(f"  • Errors: {metric.error_count}")
        report.append("")
    
    # Task manager status
    task_status = async_task_manager.get_task_status()
    if task_status:
        report.append("ASYNC TASK STATUS")
        report.append("-" * 40)
        for task_name, status in task_status.items():
            status_emoji = {
                'running': '🏃',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '🚫'
            }.get(status, '❓')
            report.append(f"{status_emoji} {task_name}: {status}")
        report.append("")
    
    report.append("=" * 80)
    return "\n".join(report)

async def cleanup_async_resources():
    """Cleanup all async resources"""
    # Cancel all managed tasks
    await async_task_manager.cancel_all_tasks()
    
    # Reset performance monitoring
    async_monitor.reset_metrics()
    
    logger.info("Async optimization resources cleaned up")
