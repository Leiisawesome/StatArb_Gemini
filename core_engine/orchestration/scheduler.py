"""
Task Scheduler for Core Engine Orchestration
Handles task scheduling, timing, and execution coordination
"""
from typing import Dict, List, Any, Optional, Callable, Union, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
import heapq
import time
# from croniter import croniter  # Optional dependency - implement basic CRON parsing if needed

class ScheduleType(Enum):
    """Types of scheduling"""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    EVENT_DRIVEN = "event_driven"
    MARKET_HOURS = "market_hours"

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"

@dataclass
class ScheduledTask:
    """Scheduled task definition"""
    id: str
    name: str
    function: Callable
    schedule_type: ScheduleType
    next_run: datetime
    schedule_config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    max_retries: int = 3
    timeout: Optional[timedelta] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1 = highest, 10 = lowest
    
    def __lt__(self, other):
        """For heapq ordering"""
        return self.next_run < other.next_run

@dataclass
class TaskExecution:
    """Task execution record"""
    task_id: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    retry_count: int = 0

class MarketHours:
    """Market hours configuration"""
    
    def __init__(self):
        # Standard US market hours (Eastern Time)
        self.market_open = (9, 30)  # 9:30 AM
        self.market_close = (16, 0)  # 4:00 PM
        self.market_days = [0, 1, 2, 3, 4]  # Monday-Friday
        self.holidays = set()  # Market holidays
        
    def is_market_open(self, dt: datetime = None) -> bool:
        """Check if market is currently open"""
        if dt is None:
            dt = datetime.now(timezone.utc)
        
        # Convert to Eastern Time
        # Note: This is simplified - real implementation would use proper timezone handling
        
        # Check if it's a weekday
        if dt.weekday() not in self.market_days:
            return False
        
        # Check if it's a holiday
        if dt.date() in self.holidays:
            return False
        
        # Check time
        current_time = (dt.hour, dt.minute)
        return self.market_open <= current_time < self.market_close
    
    def next_market_open(self, dt: datetime = None) -> datetime:
        """Get next market open time"""
        if dt is None:
            dt = datetime.now(timezone.utc)
        
        # Simplified implementation
        next_open = dt.replace(hour=self.market_open[0], minute=self.market_open[1], second=0, microsecond=0)
        
        # If market already opened today, move to next trading day
        if dt.time() >= dt.replace(hour=self.market_open[0], minute=self.market_open[1]).time():
            next_open += timedelta(days=1)
        
        # Skip weekends
        while next_open.weekday() not in self.market_days:
            next_open += timedelta(days=1)
        
        return next_open

class TaskScheduler:
    """
    Advanced task scheduler with market hours, dependencies, and retry logic
    """
    
    def __init__(self, max_workers: int = 8):
        self.logger = logging.getLogger(__name__)
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Task management
        self.tasks: Dict[str, ScheduledTask] = {}
        self.task_queue: List[ScheduledTask] = []  # Priority queue
        self.running_tasks: Dict[str, TaskExecution] = {}
        self.task_history: List[TaskExecution] = []
        self.task_dependencies: Dict[str, Set[str]] = {}
        
        # Market hours
        self.market_hours = MarketHours()
        
        # Scheduler state
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        
        # Locks for thread safety
        self.task_lock = threading.Lock()
        self.queue_lock = threading.Lock()
        
        # Metrics
        self.scheduler_metrics = {
            'total_tasks_scheduled': 0,
            'total_tasks_executed': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time': timedelta(0),
            'last_execution': None
        }
    
    def schedule_task(self, task: ScheduledTask) -> bool:
        """Schedule a new task"""
        try:
            with self.task_lock:
                # Validate task
                if not self._validate_task(task):
                    return False
                
                # Calculate next run time
                next_run = self._calculate_next_run(task)
                if next_run is None:
                    self.logger.error(f"Could not calculate next run for task {task.id}")
                    return False
                
                task.next_run = next_run
                
                # Store task
                self.tasks[task.id] = task
                
                # Add to queue
                with self.queue_lock:
                    heapq.heappush(self.task_queue, task)
                
                # Update dependencies
                self._update_dependencies(task)
                
                self.scheduler_metrics['total_tasks_scheduled'] += 1
                self.logger.info(f"Scheduled task {task.id} for {next_run}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error scheduling task {task.id}: {e}")
            return False
    
    def unschedule_task(self, task_id: str) -> bool:
        """Remove a scheduled task"""
        try:
            with self.task_lock:
                if task_id not in self.tasks:
                    return False
                
                # Remove from tasks
                task = self.tasks.pop(task_id)
                
                # Remove from queue (rebuild queue without this task)
                with self.queue_lock:
                    self.task_queue = [t for t in self.task_queue if t.id != task_id]
                    heapq.heapify(self.task_queue)
                
                # Remove dependencies
                if task_id in self.task_dependencies:
                    del self.task_dependencies[task_id]
                
                self.logger.info(f"Unscheduled task {task_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error unscheduling task {task_id}: {e}")
            return False
    
    def start_scheduler(self) -> bool:
        """Start the task scheduler"""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return False
        
        try:
            self.is_running = True
            self.shutdown_event.clear()
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            
            self.logger.info("Task scheduler started")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting scheduler: {e}")
            self.is_running = False
            return False
    
    def stop_scheduler(self) -> bool:
        """Stop the task scheduler"""
        if not self.is_running:
            return True
        
        try:
            self.is_running = False
            self.shutdown_event.set()
            
            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=5)
            
            # Cancel running tasks
            for execution in list(self.running_tasks.values()):
                execution.status = TaskStatus.CANCELLED
            
            self.logger.info("Task scheduler stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {e}")
            return False
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running and not self.shutdown_event.is_set():
            try:
                current_time = datetime.now(timezone.utc)
                
                # Check for tasks ready to run
                ready_tasks = []
                
                with self.queue_lock:
                    while self.task_queue and self.task_queue[0].next_run <= current_time:
                        task = heapq.heappop(self.task_queue)
                        if task.enabled and self._check_dependencies(task):
                            ready_tasks.append(task)
                
                # Execute ready tasks
                for task in ready_tasks:
                    self._execute_task_async(task)
                
                # Sleep until next check (1 second intervals)
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)  # Longer sleep on error
    
    def _execute_task_async(self, task: ScheduledTask):
        """Execute task asynchronously"""
        execution_id = f"{task.id}_{datetime.now().timestamp()}"
        execution = TaskExecution(
            task_id=task.id,
            execution_id=execution_id,
            start_time=datetime.now(timezone.utc),
            status=TaskStatus.RUNNING
        )
        
        self.running_tasks[execution_id] = execution
        
        # Submit to thread pool
        future = self.executor.submit(self._execute_task, task, execution)
        
        # Schedule next run
        self._schedule_next_run(task)
    
    def _execute_task(self, task: ScheduledTask, execution: TaskExecution):
        """Execute individual task"""
        try:
            self.logger.debug(f"Executing task {task.id}")
            
            # Execute task function
            if asyncio.iscoroutinefunction(task.function):
                # Handle async functions
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(task.function())
                finally:
                    loop.close()
            else:
                result = task.function()
            
            # Update execution record
            execution.end_time = datetime.now(timezone.utc)
            execution.status = TaskStatus.COMPLETED
            execution.result = result
            
            # Update metrics
            self._update_metrics(execution, True)
            
            self.logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            execution.end_time = datetime.now(timezone.utc)
            execution.status = TaskStatus.FAILED
            execution.error = e
            
            # Handle retries
            if execution.retry_count < task.max_retries:
                execution.retry_count += 1
                execution.status = TaskStatus.PENDING
                
                # Reschedule with delay
                retry_delay = timedelta(minutes=2 ** execution.retry_count)
                task.next_run = datetime.now(timezone.utc) + retry_delay
                
                with self.queue_lock:
                    heapq.heappush(self.task_queue, task)
                
                self.logger.warning(f"Task {task.id} failed, retrying in {retry_delay}")
            else:
                self.logger.error(f"Task {task.id} failed after {task.max_retries} retries: {e}")
                self._update_metrics(execution, False)
        
        finally:
            # Move to history and clean up
            self.task_history.append(execution)
            if execution.execution_id in self.running_tasks:
                del self.running_tasks[execution.execution_id]
            
            # Keep history limited
            if len(self.task_history) > 1000:
                self.task_history = self.task_history[-500:]
    
    def _calculate_next_run(self, task: ScheduledTask) -> Optional[datetime]:
        """Calculate next run time based on schedule type"""
        now = datetime.now(timezone.utc)
        
        if task.schedule_type == ScheduleType.ONCE:
            return task.schedule_config.get('run_time', now)
        
        elif task.schedule_type == ScheduleType.INTERVAL:
            interval = task.schedule_config.get('interval')
            if isinstance(interval, (int, float)):
                interval = timedelta(seconds=interval)
            elif isinstance(interval, dict):
                interval = timedelta(**interval)
            return now + interval
        
        elif task.schedule_type == ScheduleType.CRON:
            cron_expr = task.schedule_config.get('cron_expression')
            if cron_expr:
                # Basic CRON parsing - implement proper croniter if needed
                # For now, default to daily at specified hour
                try:
                    parts = cron_expr.split()
                    if len(parts) >= 2:
                        hour = int(parts[1]) if parts[1].isdigit() else 9
                        next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                        if next_run <= now:
                            next_run += timedelta(days=1)
                        return next_run
                except:
                    pass
                return now + timedelta(days=1)  # Default to daily
        
        elif task.schedule_type == ScheduleType.MARKET_HOURS:
            if self.market_hours.is_market_open(now):
                return now  # Run immediately if market is open
            else:
                return self.market_hours.next_market_open(now)
        
        elif task.schedule_type == ScheduleType.EVENT_DRIVEN:
            # Event-driven tasks are scheduled externally
            return task.schedule_config.get('next_run', now + timedelta(days=365))
        
        return None
    
    def _schedule_next_run(self, task: ScheduledTask):
        """Schedule next run for recurring tasks"""
        if task.schedule_type == ScheduleType.ONCE:
            return  # One-time tasks don't reschedule
        
        next_run = self._calculate_next_run(task)
        if next_run:
            task.next_run = next_run
            
            with self.queue_lock:
                heapq.heappush(self.task_queue, task)
    
    def _validate_task(self, task: ScheduledTask) -> bool:
        """Validate task configuration"""
        if not task.id or not task.name or not task.function:
            self.logger.error("Task missing required fields")
            return False
        
        if task.id in self.tasks:
            self.logger.error(f"Task with ID {task.id} already exists")
            return False
        
        # Validate schedule configuration
        if task.schedule_type == ScheduleType.CRON:
            cron_expr = task.schedule_config.get('cron_expression')
            if not cron_expr:
                self.logger.error("CRON tasks require cron_expression")
                return False
            try:
                # Basic CRON validation - check format
                parts = cron_expr.split()
                if len(parts) != 5:
                    raise ValueError("CRON expression must have 5 parts")
            except Exception:
                self.logger.error(f"Invalid CRON expression: {cron_expr}")
                return False
        
        elif task.schedule_type == ScheduleType.INTERVAL:
            if 'interval' not in task.schedule_config:
                self.logger.error("Interval tasks require interval configuration")
                return False
        
        return True
    
    def _check_dependencies(self, task: ScheduledTask) -> bool:
        """Check if task dependencies are satisfied"""
        if not task.dependencies:
            return True
        
        # Check if all dependencies have completed successfully recently
        for dep_task_id in task.dependencies:
            if not self._is_dependency_satisfied(dep_task_id):
                return False
        
        return True
    
    def _is_dependency_satisfied(self, task_id: str) -> bool:
        """Check if a dependency task has completed successfully"""
        # Look for recent successful execution
        recent_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for execution in reversed(self.task_history):
            if (execution.task_id == task_id and 
                execution.start_time >= recent_threshold and
                execution.status == TaskStatus.COMPLETED):
                return True
        
        return False
    
    def _update_dependencies(self, task: ScheduledTask):
        """Update dependency tracking"""
        if task.dependencies:
            self.task_dependencies[task.id] = set(task.dependencies)
    
    def _update_metrics(self, execution: TaskExecution, success: bool):
        """Update scheduler metrics"""
        self.scheduler_metrics['total_tasks_executed'] += 1
        
        if success:
            self.scheduler_metrics['successful_executions'] += 1
        else:
            self.scheduler_metrics['failed_executions'] += 1
        
        # Update average execution time
        if execution.end_time:
            exec_time = execution.end_time - execution.start_time
            current_avg = self.scheduler_metrics['average_execution_time']
            total_execs = self.scheduler_metrics['total_tasks_executed']
            
            self.scheduler_metrics['average_execution_time'] = (
                (current_avg * (total_execs - 1) + exec_time) / total_execs
            )
        
        self.scheduler_metrics['last_execution'] = datetime.now(timezone.utc)
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of specific task"""
        if task_id not in self.tasks:
            return {'error': 'Task not found'}
        
        task = self.tasks[task_id]
        
        # Get recent executions
        recent_executions = [
            {
                'execution_id': exec.execution_id,
                'start_time': exec.start_time,
                'end_time': exec.end_time,
                'status': exec.status.value,
                'retry_count': exec.retry_count
            }
            for exec in self.task_history
            if exec.task_id == task_id
        ][-10:]  # Last 10 executions
        
        return {
            'task_id': task.id,
            'name': task.name,
            'schedule_type': task.schedule_type.value,
            'next_run': task.next_run,
            'enabled': task.enabled,
            'dependencies': task.dependencies,
            'recent_executions': recent_executions
        }
    
    def get_scheduler_metrics(self) -> Dict[str, Any]:
        """Get scheduler performance metrics"""
        return self.scheduler_metrics.copy()
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_scheduler()
        self.executor.shutdown(wait=True)
        self.logger.info("Task scheduler cleaned up")