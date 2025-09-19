"""
Workflow Manager for Core Engine Orchestration
Handles workflow control, state transitions, and process coordination
"""
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
import queue

class WorkflowState(Enum):
    """Workflow execution states"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"

class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

@dataclass
class WorkflowStep:
    """Individual workflow step definition"""
    name: str
    function: Callable
    dependencies: List[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[timedelta] = None
    retry_count: int = 3
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowResult:
    """Result of workflow execution"""
    success: bool
    step_name: str
    result: Any = None
    error: Optional[Exception] = None
    execution_time: Optional[timedelta] = None
    timestamp: datetime = field(default_factory=datetime.now)

class WorkflowManager:
    """
    Manages workflow execution, dependencies, and state transitions
    """
    
    def __init__(self, max_workers: int = 4):
        self.logger = logging.getLogger(__name__)
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Workflow state
        self.state = WorkflowState.INITIALIZED
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        self.active_workflows: Dict[str, Any] = {}
        self.workflow_results: Dict[str, List[WorkflowResult]] = {}
        
        # Threading and synchronization
        self.state_lock = threading.Lock()
        self.result_queue = queue.Queue()
        self._shutdown_event = threading.Event()
        
        # Monitoring
        self.execution_metrics: Dict[str, Dict[str, Any]] = {}
        
    def register_workflow(self, workflow_name: str, steps: List[WorkflowStep]) -> bool:
        """Register a new workflow with validation"""
        try:
            # Validate workflow steps
            if not self._validate_workflow_steps(steps):
                self.logger.error(f"Invalid workflow steps for {workflow_name}")
                return False
            
            # Check for circular dependencies
            if self._has_circular_dependencies(steps):
                self.logger.error(f"Circular dependencies detected in workflow {workflow_name}")
                return False
            
            # Register workflow
            self.workflows[workflow_name] = sorted(steps, key=lambda x: x.priority.value)
            self.workflow_results[workflow_name] = []
            self.execution_metrics[workflow_name] = {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'average_execution_time': timedelta(0),
                'last_execution': None
            }
            
            self.logger.info(f"Registered workflow '{workflow_name}' with {len(steps)} steps")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering workflow {workflow_name}: {e}")
            return False
    
    async def execute_workflow(self, workflow_name: str, context: Dict[str, Any] = None) -> bool:
        """Execute a registered workflow"""
        if workflow_name not in self.workflows:
            self.logger.error(f"Workflow '{workflow_name}' not found")
            return False
        
        with self.state_lock:
            if self.state not in [WorkflowState.INITIALIZED, WorkflowState.RUNNING]:
                self.logger.warning(f"Cannot execute workflow in state {self.state}")
                return False
            
            self.state = WorkflowState.RUNNING
            self.active_workflows[workflow_name] = {
                'start_time': datetime.now(),
                'context': context or {},
                'completed_steps': [],
                'failed_steps': []
            }
        
        try:
            return await self._execute_workflow_steps(workflow_name)
            
        except Exception as e:
            self.logger.error(f"Error executing workflow {workflow_name}: {e}")
            with self.state_lock:
                self.state = WorkflowState.ERROR
            return False
        finally:
            # Update metrics
            self._update_workflow_metrics(workflow_name)
    
    async def _execute_workflow_steps(self, workflow_name: str) -> bool:
        """Execute workflow steps with dependency resolution"""
        steps = self.workflows[workflow_name]
        completed_steps = set()
        failed_steps = set()
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(steps)
        
        # Execute steps in topological order
        while len(completed_steps) < len(steps) and not failed_steps:
            # Find ready steps (all dependencies completed)
            ready_steps = []
            for step in steps:
                if (step.name not in completed_steps and 
                    step.name not in failed_steps and
                    step.enabled and
                    all(dep in completed_steps for dep in step.dependencies)):
                    ready_steps.append(step)
            
            if not ready_steps:
                if failed_steps:
                    self.logger.error(f"Workflow {workflow_name} has failed steps: {failed_steps}")
                else:
                    self.logger.error(f"Workflow {workflow_name} has unresolvable dependencies")
                return False
            
            # Execute ready steps
            tasks = []
            for step in ready_steps:
                task = asyncio.create_task(self._execute_step(workflow_name, step))
                tasks.append((step, task))
            
            # Wait for step completion
            for step, task in tasks:
                try:
                    result = await task
                    if result.success:
                        completed_steps.add(step.name)
                        self.active_workflows[workflow_name]['completed_steps'].append(step.name)
                    else:
                        failed_steps.add(step.name)
                        self.active_workflows[workflow_name]['failed_steps'].append(step.name)
                    
                    self.workflow_results[workflow_name].append(result)
                    
                except Exception as e:
                    self.logger.error(f"Error executing step {step.name}: {e}")
                    failed_steps.add(step.name)
        
        success = len(completed_steps) == len([s for s in steps if s.enabled])
        
        with self.state_lock:
            self.state = WorkflowState.COMPLETED if success else WorkflowState.ERROR
        
        return success
    
    async def _execute_step(self, workflow_name: str, step: WorkflowStep) -> WorkflowResult:
        """Execute individual workflow step"""
        start_time = datetime.now()
        
        for attempt in range(step.retry_count + 1):
            try:
                self.logger.debug(f"Executing step {step.name} (attempt {attempt + 1})")
                
                # Get execution context
                context = self.active_workflows[workflow_name]['context']
                
                # Execute step function
                if asyncio.iscoroutinefunction(step.function):
                    result = await step.function(context)
                else:
                    # Run in executor for sync functions
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(self.executor, step.function, context)
                
                execution_time = datetime.now() - start_time
                
                return WorkflowResult(
                    success=True,
                    step_name=step.name,
                    result=result,
                    execution_time=execution_time
                )
                
            except Exception as e:
                self.logger.warning(f"Step {step.name} failed on attempt {attempt + 1}: {e}")
                if attempt == step.retry_count:
                    execution_time = datetime.now() - start_time
                    return WorkflowResult(
                        success=False,
                        step_name=step.name,
                        error=e,
                        execution_time=execution_time
                    )
                
                # Wait before retry
                await asyncio.sleep(min(2 ** attempt, 10))  # Exponential backoff
    
    def _validate_workflow_steps(self, steps: List[WorkflowStep]) -> bool:
        """Validate workflow step definitions"""
        if not steps:
            return False
        
        step_names = [step.name for step in steps]
        if len(step_names) != len(set(step_names)):
            self.logger.error("Duplicate step names found")
            return False
        
        # Validate dependencies exist
        for step in steps:
            for dep in step.dependencies:
                if dep not in step_names:
                    self.logger.error(f"Step {step.name} has invalid dependency: {dep}")
                    return False
        
        return True
    
    def _has_circular_dependencies(self, steps: List[WorkflowStep]) -> bool:
        """Check for circular dependencies using DFS"""
        graph = {step.name: step.dependencies for step in steps}
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step in steps:
            if step.name not in visited:
                if has_cycle(step.name):
                    return True
        
        return False
    
    def _build_dependency_graph(self, steps: List[WorkflowStep]) -> Dict[str, List[str]]:
        """Build dependency graph for execution planning"""
        return {step.name: step.dependencies for step in steps}
    
    def _update_workflow_metrics(self, workflow_name: str):
        """Update execution metrics for workflow"""
        if workflow_name not in self.active_workflows:
            return
        
        workflow_info = self.active_workflows[workflow_name]
        metrics = self.execution_metrics[workflow_name]
        
        # Update counters
        metrics['total_executions'] += 1
        
        if self.state == WorkflowState.COMPLETED:
            metrics['successful_executions'] += 1
        else:
            metrics['failed_executions'] += 1
        
        # Update timing
        execution_time = datetime.now() - workflow_info['start_time']
        current_avg = metrics['average_execution_time']
        total_execs = metrics['total_executions']
        
        metrics['average_execution_time'] = (
            (current_avg * (total_execs - 1) + execution_time) / total_execs
        )
        metrics['last_execution'] = datetime.now()
    
    def pause_workflow(self, workflow_name: str) -> bool:
        """Pause active workflow"""
        with self.state_lock:
            if self.state == WorkflowState.RUNNING:
                self.state = WorkflowState.PAUSED
                self.logger.info(f"Paused workflow {workflow_name}")
                return True
            return False
    
    def resume_workflow(self, workflow_name: str) -> bool:
        """Resume paused workflow"""
        with self.state_lock:
            if self.state == WorkflowState.PAUSED:
                self.state = WorkflowState.RUNNING
                self.logger.info(f"Resumed workflow {workflow_name}")
                return True
            return False
    
    def stop_workflow(self, workflow_name: str) -> bool:
        """Stop active workflow"""
        with self.state_lock:
            if self.state in [WorkflowState.RUNNING, WorkflowState.PAUSED]:
                self.state = WorkflowState.STOPPED
                self.logger.info(f"Stopped workflow {workflow_name}")
                return True
            return False
    
    def get_workflow_status(self, workflow_name: str) -> Dict[str, Any]:
        """Get current workflow status"""
        if workflow_name not in self.workflows:
            return {'error': 'Workflow not found'}
        
        status = {
            'name': workflow_name,
            'state': self.state.value,
            'registered_steps': len(self.workflows[workflow_name]),
            'metrics': self.execution_metrics.get(workflow_name, {}),
            'active': workflow_name in self.active_workflows
        }
        
        if workflow_name in self.active_workflows:
            active_info = self.active_workflows[workflow_name]
            status.update({
                'start_time': active_info['start_time'],
                'completed_steps': active_info['completed_steps'],
                'failed_steps': active_info['failed_steps'],
                'context_keys': list(active_info['context'].keys())
            })
        
        return status
    
    def cleanup(self):
        """Cleanup resources"""
        self._shutdown_event.set()
        self.executor.shutdown(wait=True)
        self.logger.info("Workflow manager cleaned up")