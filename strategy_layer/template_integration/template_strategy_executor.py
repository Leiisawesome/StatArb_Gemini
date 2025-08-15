"""
Template Strategy Executor
==========================

High-performance executor for template-based strategies with batch processing,
parallel execution, and integration with the core engine.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from strategy_layer.base import StrategyResult, StrategyExecutionResult
from .template_strategy_manager import TemplateStrategyManager, StrategyInstance

logger = logging.getLogger(__name__)

@dataclass
class ExecutionBatch:
    """Batch of strategy executions"""
    batch_id: str
    instance_ids: List[str]
    market_data: Dict[str, Any]
    created_at: datetime
    priority: int = 1  # 1=normal, 2=high, 3=urgent
    callback: Optional[Callable[[Dict[str, StrategyResult]], None]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionStats:
    """Execution statistics"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time_ms: float = 0.0
    average_execution_time_ms: float = 0.0
    max_execution_time_ms: float = 0.0
    min_execution_time_ms: float = float('inf')
    batches_processed: int = 0
    last_execution_time: Optional[datetime] = None

class TemplateStrategyExecutor:
    """
    High-performance executor for template-based strategies with support for
    batch processing, parallel execution, and real-time monitoring.
    """
    
    def __init__(self, strategy_manager: TemplateStrategyManager):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.strategy_manager = strategy_manager
        
        # Execution configuration
        self.max_worker_threads = 10
        self.max_queue_size = 1000
        self.execution_timeout_seconds = 30
        self.batch_timeout_seconds = 60
        
        # Execution queue and workers
        self.execution_queue = queue.PriorityQueue(maxsize=self.max_queue_size)
        self.executor = ThreadPoolExecutor(max_workers=self.max_worker_threads)
        self.is_running = False
        self.worker_thread = None
        
        # Performance tracking
        self.execution_stats = ExecutionStats()
        self.execution_history: List[Dict[str, Any]] = []
        
        # Event handlers
        self.on_execution_complete: Optional[Callable[[str, StrategyResult], None]] = None
        self.on_batch_complete: Optional[Callable[[str, Dict[str, StrategyResult]], None]] = None
        self.on_execution_error: Optional[Callable[[str, Exception], None]] = None
        
        self.logger.info("TemplateStrategyExecutor initialized")
    
    def start(self):
        """Start the executor worker thread"""
        if self.is_running:
            self.logger.warning("Executor is already running")
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        self.logger.info("TemplateStrategyExecutor started")
    
    def stop(self, timeout: float = 10.0):
        """Stop the executor and wait for completion"""
        if not self.is_running:
            self.logger.warning("Executor is not running")
            return
        
        self.is_running = False
        
        # Wait for worker thread to finish
        if self.worker_thread:
            self.worker_thread.join(timeout=timeout)
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        self.logger.info("TemplateStrategyExecutor stopped")
    
    def execute_single(self, instance_id: str, market_data: Dict[str, Any],
                      priority: int = 1) -> str:
        """
        Queue a single strategy execution
        
        Returns:
            batch_id: Unique identifier for tracking execution
        """
        batch_id = f"single_{instance_id}_{int(time.time() * 1000)}"
        
        batch = ExecutionBatch(
            batch_id=batch_id,
            instance_ids=[instance_id],
            market_data=market_data,
            created_at=datetime.now(),
            priority=priority
        )
        
        try:
            self.execution_queue.put((priority, batch), timeout=1.0)
            self.logger.debug(f"Queued single execution for instance {instance_id}")
            return batch_id
        except queue.Full:
            self.logger.error("Execution queue is full")
            raise RuntimeError("Execution queue is full")
    
    def execute_batch(self, instance_ids: List[str], market_data: Dict[str, Any],
                     priority: int = 1, 
                     callback: Optional[Callable[[Dict[str, StrategyResult]], None]] = None) -> str:
        """
        Queue a batch of strategy executions
        
        Returns:
            batch_id: Unique identifier for tracking batch execution
        """
        batch_id = f"batch_{len(instance_ids)}_{int(time.time() * 1000)}"
        
        batch = ExecutionBatch(
            batch_id=batch_id,
            instance_ids=instance_ids,
            market_data=market_data,
            created_at=datetime.now(),
            priority=priority,
            callback=callback
        )
        
        try:
            self.execution_queue.put((priority, batch), timeout=1.0)
            self.logger.debug(f"Queued batch execution for {len(instance_ids)} instances")
            return batch_id
        except queue.Full:
            self.logger.error("Execution queue is full")
            raise RuntimeError("Execution queue is full")
    
    def execute_by_template(self, template_id: str, market_data: Dict[str, Any],
                           priority: int = 1) -> str:
        """
        Execute all strategy instances based on a specific template
        """
        instances = self.strategy_manager.list_strategy_instances(template_id=template_id, status="active")
        instance_ids = [inst.instance_id for inst in instances]
        
        if not instance_ids:
            self.logger.warning(f"No active instances found for template {template_id}")
            return ""
        
        return self.execute_batch(instance_ids, market_data, priority)
    
    def execute_all_active(self, market_data: Dict[str, Any], priority: int = 1) -> str:
        """
        Execute all active strategy instances
        """
        instances = self.strategy_manager.list_strategy_instances(status="active")
        instance_ids = [inst.instance_id for inst in instances]
        
        if not instance_ids:
            self.logger.warning("No active strategy instances found")
            return ""
        
        return self.execute_batch(instance_ids, market_data, priority)
    
    def execute_synchronous(self, instance_ids: List[str], 
                          market_data: Dict[str, Any]) -> Dict[str, StrategyResult]:
        """
        Execute strategies synchronously and return results immediately
        """
        try:
            execution_start = datetime.now()
            
            # Execute strategies in parallel using thread pool
            futures = {}
            for instance_id in instance_ids:
                future = self.executor.submit(
                    self.strategy_manager.execute_strategy_instance,
                    instance_id, market_data
                )
                futures[future] = instance_id
            
            # Collect results
            results = {}
            for future in as_completed(futures, timeout=self.execution_timeout_seconds):
                instance_id = futures[future]
                try:
                    result = future.result()
                    results[instance_id] = result
                except Exception as e:
                    self.logger.error(f"Execution failed for instance {instance_id}: {e}")
                    results[instance_id] = StrategyResult(
                        strategy_id=instance_id,
                        execution_time=datetime.now(),
                        errors=[f"Execution error: {e}"]
                    )
            
            # Update statistics
            execution_time = (datetime.now() - execution_start).total_seconds() * 1000
            self._update_execution_stats(len(instance_ids), execution_time, results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Synchronous execution failed: {e}")
            raise
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current execution queue status"""
        return {
            'queue_size': self.execution_queue.qsize(),
            'max_queue_size': self.max_queue_size,
            'is_running': self.is_running,
            'worker_threads': self.max_worker_threads,
            'queue_utilization': self.execution_queue.qsize() / self.max_queue_size
        }
    
    def get_execution_stats(self) -> ExecutionStats:
        """Get execution statistics"""
        return self.execution_stats
    
    def clear_queue(self):
        """Clear the execution queue"""
        try:
            while not self.execution_queue.empty():
                self.execution_queue.get_nowait()
            self.logger.info("Execution queue cleared")
        except queue.Empty:
            pass
    
    def _worker_loop(self):
        """Main worker loop for processing execution queue"""
        self.logger.info("Executor worker loop started")
        
        while self.is_running:
            try:
                # Get next batch from queue (with timeout)
                try:
                    priority, batch = self.execution_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process batch
                self._process_execution_batch(batch)
                
                # Mark task as done
                self.execution_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                time.sleep(0.1)  # Brief pause on error
        
        self.logger.info("Executor worker loop stopped")
    
    def _process_execution_batch(self, batch: ExecutionBatch):
        """Process a single execution batch"""
        try:
            batch_start = datetime.now()
            
            self.logger.debug(f"Processing batch {batch.batch_id} with {len(batch.instance_ids)} instances")
            
            # Execute all instances in the batch
            if len(batch.instance_ids) == 1:
                # Single execution
                instance_id = batch.instance_ids[0]
                result = self.strategy_manager.execute_strategy_instance(instance_id, batch.market_data)
                results = {instance_id: result}
                
                # Call single execution handler
                if self.on_execution_complete:
                    try:
                        self.on_execution_complete(instance_id, result)
                    except Exception as e:
                        self.logger.error(f"Error in execution complete handler: {e}")
                
            else:
                # Batch execution
                results = self.strategy_manager.execute_multiple_instances(
                    batch.instance_ids, batch.market_data
                )
            
            # Update statistics
            batch_time = (datetime.now() - batch_start).total_seconds() * 1000
            self._update_execution_stats(len(batch.instance_ids), batch_time, results)
            
            # Call batch completion handler
            if batch.callback:
                try:
                    batch.callback(results)
                except Exception as e:
                    self.logger.error(f"Error in batch callback: {e}")
            
            if self.on_batch_complete:
                try:
                    self.on_batch_complete(batch.batch_id, results)
                except Exception as e:
                    self.logger.error(f"Error in batch complete handler: {e}")
            
            self.logger.debug(f"Batch {batch.batch_id} completed in {batch_time:.1f}ms")
            
        except Exception as e:
            self.logger.error(f"Error processing batch {batch.batch_id}: {e}")
            
            # Call error handler
            if self.on_execution_error:
                try:
                    self.on_execution_error(batch.batch_id, e)
                except Exception as handler_error:
                    self.logger.error(f"Error in execution error handler: {handler_error}")
    
    def _update_execution_stats(self, instance_count: int, execution_time_ms: float,
                              results: Dict[str, StrategyResult]):
        """Update execution statistics"""
        
        # Count successes and failures
        successful = sum(1 for result in results.values() if not result.errors)
        failed = len(results) - successful
        
        # Update stats
        self.execution_stats.total_executions += instance_count
        self.execution_stats.successful_executions += successful
        self.execution_stats.failed_executions += failed
        self.execution_stats.batches_processed += 1
        self.execution_stats.last_execution_time = datetime.now()
        
        # Update timing statistics
        self.execution_stats.total_execution_time_ms += execution_time_ms
        self.execution_stats.average_execution_time_ms = (
            self.execution_stats.total_execution_time_ms / self.execution_stats.batches_processed
        )
        
        if execution_time_ms > self.execution_stats.max_execution_time_ms:
            self.execution_stats.max_execution_time_ms = execution_time_ms
        
        if execution_time_ms < self.execution_stats.min_execution_time_ms:
            self.execution_stats.min_execution_time_ms = execution_time_ms
        
        # Record execution history
        execution_record = {
            'timestamp': datetime.now().isoformat(),
            'instance_count': instance_count,
            'execution_time_ms': execution_time_ms,
            'successful_count': successful,
            'failed_count': failed,
            'batch_id': f"batch_{int(time.time() * 1000)}"
        }
        
        self.execution_history.append(execution_record)
        
        # Maintain rolling window
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        
        stats = self.execution_stats
        queue_status = self.get_queue_status()
        
        # Calculate success rate
        success_rate = 0.0
        if stats.total_executions > 0:
            success_rate = stats.successful_executions / stats.total_executions
        
        # Recent performance (last 100 executions)
        recent_executions = self.execution_history[-100:] if self.execution_history else []
        recent_avg_time = 0.0
        recent_success_rate = 0.0
        
        if recent_executions:
            recent_avg_time = sum(ex['execution_time_ms'] for ex in recent_executions) / len(recent_executions)
            recent_successful = sum(ex['successful_count'] for ex in recent_executions)
            recent_total = sum(ex['instance_count'] for ex in recent_executions)
            recent_success_rate = recent_successful / max(recent_total, 1)
        
        return {
            'total_executions': stats.total_executions,
            'successful_executions': stats.successful_executions,
            'failed_executions': stats.failed_executions,
            'success_rate': success_rate,
            'batches_processed': stats.batches_processed,
            'average_execution_time_ms': stats.average_execution_time_ms,
            'max_execution_time_ms': stats.max_execution_time_ms,
            'min_execution_time_ms': stats.min_execution_time_ms if stats.min_execution_time_ms != float('inf') else 0,
            'recent_avg_execution_time_ms': recent_avg_time,
            'recent_success_rate': recent_success_rate,
            'queue_size': queue_status['queue_size'],
            'queue_utilization': queue_status['queue_utilization'],
            'is_running': self.is_running,
            'last_execution_time': stats.last_execution_time.isoformat() if stats.last_execution_time else None
        }
    
    def set_event_handlers(self, 
                          on_execution_complete: Optional[Callable[[str, StrategyResult], None]] = None,
                          on_batch_complete: Optional[Callable[[str, Dict[str, StrategyResult]], None]] = None,
                          on_execution_error: Optional[Callable[[str, Exception], None]] = None):
        """Set event handlers for execution events"""
        
        if on_execution_complete:
            self.on_execution_complete = on_execution_complete
        
        if on_batch_complete:
            self.on_batch_complete = on_batch_complete
        
        if on_execution_error:
            self.on_execution_error = on_execution_error
        
        self.logger.info("Event handlers updated")
    
    def configure(self, max_worker_threads: Optional[int] = None,
                 max_queue_size: Optional[int] = None,
                 execution_timeout_seconds: Optional[float] = None):
        """Configure executor parameters"""
        
        if max_worker_threads:
            self.max_worker_threads = max_worker_threads
        
        if max_queue_size:
            self.max_queue_size = max_queue_size
        
        if execution_timeout_seconds:
            self.execution_timeout_seconds = execution_timeout_seconds
        
        self.logger.info(f"Executor configured: workers={self.max_worker_threads}, "
                        f"queue_size={self.max_queue_size}, timeout={self.execution_timeout_seconds}s")
