"""
Template Execution Coordinator
==============================

Coordinates execution of template-based strategies with intelligent routing,
load balancing, and category-aware optimization.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import uuid

from strategy_templates.base import TemplateRegistry, BaseTemplate, TemplateCategory
from strategy_layer.template_integration import TemplateStrategyManager
from .template_core_engine import TemplateEngineConfig

logger = logging.getLogger(__name__)

class ExecutionPriority(Enum):
    """Execution priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class ExecutionQueue(Enum):
    """Execution queue types"""
    REAL_TIME = "real_time"      # Immediate execution
    BATCH = "batch"              # Batch processing
    BACKGROUND = "background"    # Low priority background
    EMERGENCY = "emergency"      # Emergency bypass

@dataclass
class ExecutionRequest:
    """Template execution request"""
    request_id: str
    template_id: str
    market_data: Dict[str, Any]
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    queue_type: ExecutionQueue = ExecutionQueue.REAL_TIME
    execution_context: Optional[Dict[str, Any]] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    timeout_ms: int = 1000
    
    # Routing hints
    preferred_category: Optional[TemplateCategory] = None
    avoid_inheritance: bool = False
    force_single_execution: bool = False

@dataclass
class ExecutionSlot:
    """Execution slot for load balancing"""
    slot_id: str
    category: TemplateCategory
    is_busy: bool = False
    current_request: Optional[ExecutionRequest] = None
    
    # Performance tracking
    total_executions: int = 0
    successful_executions: int = 0
    avg_execution_time_ms: float = 0.0
    
    # Load balancing
    queue_length: int = 0
    last_execution_time: Optional[datetime] = None
    
    def calculate_load_score(self) -> float:
        """Calculate load score for slot selection"""
        base_score = 1.0
        
        # Busy penalty
        if self.is_busy:
            base_score *= 0.1
        
        # Queue length penalty
        queue_penalty = 1.0 / (1.0 + self.queue_length * 0.1)
        
        # Performance bonus
        success_rate = self.successful_executions / max(self.total_executions, 1)
        performance_bonus = success_rate
        
        # Recency bonus
        recency_bonus = 1.0
        if self.last_execution_time:
            time_since_last = (datetime.now() - self.last_execution_time).total_seconds()
            recency_bonus = min(1.2, 1.0 + time_since_last / 3600)  # Bonus for idle slots
        
        return base_score * queue_penalty * performance_bonus * recency_bonus

class TemplateExecutionCoordinator:
    """
    Coordinates and optimizes template strategy execution with intelligent
    routing, load balancing, and category-aware processing.
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 strategy_manager: TemplateStrategyManager,
                 config: TemplateEngineConfig):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.strategy_manager = strategy_manager
        self.config = config
        
        # Execution management
        self.execution_queues: Dict[ExecutionQueue, deque] = {
            queue_type: deque() for queue_type in ExecutionQueue
        }
        self.execution_slots: Dict[str, ExecutionSlot] = {}
        self.active_executions: Dict[str, ExecutionRequest] = {}
        
        # Load balancing
        self.category_load_balancer: Dict[TemplateCategory, List[str]] = defaultdict(list)
        self.round_robin_counters: Dict[TemplateCategory, int] = defaultdict(int)
        
        # Performance tracking
        self.execution_statistics: Dict[str, Any] = defaultdict(float)
        self.category_performance: Dict[TemplateCategory, Dict[str, float]] = defaultdict(dict)
        
        # Queue processing
        self.queue_processors: Dict[ExecutionQueue, asyncio.Task] = {}
        self.shutdown_event = asyncio.Event()
        
        self.logger.info("TemplateExecutionCoordinator initialized")
    
    async def initialize(self):
        """Initialize execution coordinator"""
        
        self.logger.info("Initializing template execution coordinator")
        
        # Create execution slots for each category
        await self._create_execution_slots()
        
        # Start queue processors
        await self._start_queue_processors()
        
        # Initialize load balancing
        await self._initialize_load_balancing()
        
        self.logger.info("Template execution coordinator initialization completed")
    
    async def submit_execution_request(self, request: ExecutionRequest) -> str:
        """Submit template execution request"""
        
        try:
            # Validate request
            if not await self._validate_execution_request(request):
                raise ValueError(f"Invalid execution request: {request.request_id}")
            
            # Route to appropriate queue
            queue_type = await self._determine_optimal_queue(request)
            request.queue_type = queue_type
            
            # Add to queue
            self.execution_queues[queue_type].append(request)
            
            self.logger.debug(f"Execution request {request.request_id} queued in {queue_type.value}")
            return request.request_id
            
        except Exception as e:
            self.logger.error(f"Failed to submit execution request: {e}")
            raise
    
    async def execute_template_immediately(self, template_id: str,
                                         market_data: Dict[str, Any],
                                         execution_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute template immediately bypassing queues"""
        
        try:
            # Create emergency request
            request = ExecutionRequest(
                request_id=f"immediate_{uuid.uuid4().hex[:8]}",
                template_id=template_id,
                market_data=market_data,
                priority=ExecutionPriority.CRITICAL,
                queue_type=ExecutionQueue.EMERGENCY,
                execution_context=execution_context,
                timeout_ms=500  # Shorter timeout for immediate execution
            )
            
            # Execute directly
            result = await self._execute_request(request)
            return result
            
        except Exception as e:
            self.logger.error(f"Immediate execution failed for template {template_id}: {e}")
            raise
    
    async def _create_execution_slots(self):
        """Create execution slots for load balancing"""
        
        slots_per_category = max(1, self.config.max_parallel_templates // len(TemplateCategory))
        
        for category in TemplateCategory:
            category_slots = []
            
            for i in range(slots_per_category):
                slot_id = f"{category.value}_slot_{i}"
                slot = ExecutionSlot(
                    slot_id=slot_id,
                    category=category
                )
                
                self.execution_slots[slot_id] = slot
                category_slots.append(slot_id)
            
            self.category_load_balancer[category] = category_slots
    
    async def _start_queue_processors(self):
        """Start queue processing tasks"""
        
        for queue_type in ExecutionQueue:
            processor_task = asyncio.create_task(
                self._process_execution_queue(queue_type)
            )
            self.queue_processors[queue_type] = processor_task
    
    async def _process_execution_queue(self, queue_type: ExecutionQueue):
        """Process execution queue"""
        
        self.logger.debug(f"Started queue processor for {queue_type.value}")
        
        while not self.shutdown_event.is_set():
            try:
                # Check for requests in queue
                if self.execution_queues[queue_type]:
                    request = self.execution_queues[queue_type].popleft()
                    
                    # Check if request is still valid
                    if await self._is_request_valid(request):
                        # Find available execution slot
                        slot = await self._find_available_slot(request)
                        
                        if slot:
                            # Execute request
                            await self._execute_request_in_slot(request, slot)
                        else:
                            # Re-queue if no slot available
                            self.execution_queues[queue_type].appendleft(request)
                            await asyncio.sleep(0.01)  # Brief delay
                    else:
                        self.logger.warning(f"Dropping expired request: {request.request_id}")
                
                # Brief sleep to prevent busy waiting
                await asyncio.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error in queue processor {queue_type.value}: {e}")
                await asyncio.sleep(0.1)
    
    async def _execute_request_in_slot(self, request: ExecutionRequest, slot: ExecutionSlot):
        """Execute request in specific slot"""
        
        start_time = datetime.now()
        
        try:
            # Mark slot as busy
            slot.is_busy = True
            slot.current_request = request
            slot.queue_length = len(self.execution_queues[request.queue_type])
            
            # Add to active executions
            self.active_executions[request.request_id] = request
            
            # Execute request
            result = await self._execute_request(request)
            
            # Calculate execution time
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update slot performance
            slot.total_executions += 1
            if result.get('success', False):
                slot.successful_executions += 1
            
            # Update average execution time
            alpha = 0.1  # Smoothing factor
            slot.avg_execution_time_ms = (
                (1 - alpha) * slot.avg_execution_time_ms + 
                alpha * execution_time_ms
            )
            
            slot.last_execution_time = datetime.now()
            
            # Update statistics
            await self._update_execution_statistics(request, result, execution_time_ms)
            
        except Exception as e:
            self.logger.error(f"Execution failed in slot {slot.slot_id}: {e}")
            
        finally:
            # Release slot
            slot.is_busy = False
            slot.current_request = None
            
            # Remove from active executions
            if request.request_id in self.active_executions:
                del self.active_executions[request.request_id]
    
    async def _execute_request(self, request: ExecutionRequest) -> Dict[str, Any]:
        """Execute individual request"""
        
        try:
            # Get template
            template = self.template_registry.get_template(request.template_id)
            if not template:
                return {
                    'success': False,
                    'error': f"Template {request.template_id} not found",
                    'execution_time_ms': 0.0
                }
            
            # Create or get strategy instance
            instance_id = self.strategy_manager.create_strategy_instance(
                request.template_id,
                custom_parameters=request.execution_context.get('parameters', {}) if request.execution_context else {}
            )
            
            try:
                # Execute strategy
                execution_result = self.strategy_manager.execute_strategy_instance(
                    instance_id, request.market_data
                )
                
                # Convert to result format
                result = {
                    'success': not bool(execution_result.errors),
                    'signals': execution_result.signals,
                    'positions': execution_result.positions,
                    'errors': execution_result.errors,
                    'warnings': getattr(execution_result, 'warnings', []),
                    'execution_time_ms': getattr(execution_result, 'execution_time_ms', 0.0)
                }
                
                return result
                
            finally:
                # Clean up strategy instance (optional - could be cached)
                try:
                    self.strategy_manager.stop_strategy_instance(instance_id)
                except:
                    pass
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'execution_time_ms': 0.0
            }
    
    async def _find_available_slot(self, request: ExecutionRequest) -> Optional[ExecutionSlot]:
        """Find best available execution slot for request"""
        
        # Determine target category
        template = self.template_registry.get_template(request.template_id)
        target_category = template.metadata.category if template else TemplateCategory.BASE
        
        if request.preferred_category:
            target_category = request.preferred_category
        
        # Get candidate slots
        candidate_slots = self.category_load_balancer[target_category].copy()
        
        # Add cross-category slots if needed
        if not any(not self.execution_slots[slot_id].is_busy for slot_id in candidate_slots):
            # All category slots busy, consider other categories
            for category, slot_ids in self.category_load_balancer.items():
                if category != target_category:
                    candidate_slots.extend(slot_ids)
        
        # Find best slot
        best_slot = None
        best_score = float('-inf')
        
        for slot_id in candidate_slots:
            slot = self.execution_slots[slot_id]
            
            if not slot.is_busy:
                score = slot.calculate_load_score()
                
                # Priority bonus for matching category
                if slot.category == target_category:
                    score *= 1.5
                
                # Priority bonus based on request priority
                priority_multiplier = {
                    ExecutionPriority.LOW: 0.8,
                    ExecutionPriority.NORMAL: 1.0,
                    ExecutionPriority.HIGH: 1.2,
                    ExecutionPriority.CRITICAL: 1.5
                }
                score *= priority_multiplier[request.priority]
                
                if score > best_score:
                    best_score = score
                    best_slot = slot
        
        return best_slot
    
    async def _determine_optimal_queue(self, request: ExecutionRequest) -> ExecutionQueue:
        """Determine optimal queue for request"""
        
        # Emergency queue for critical requests
        if request.priority == ExecutionPriority.CRITICAL:
            return ExecutionQueue.EMERGENCY
        
        # Real-time queue for high priority
        if request.priority == ExecutionPriority.HIGH:
            return ExecutionQueue.REAL_TIME
        
        # Check if batch processing would be beneficial
        template = self.template_registry.get_template(request.template_id)
        if template and template.metadata.category == TemplateCategory.COMPOSITE:
            # Composite templates benefit from batch processing
            return ExecutionQueue.BATCH
        
        # Default to real-time
        return ExecutionQueue.REAL_TIME
    
    async def _validate_execution_request(self, request: ExecutionRequest) -> bool:
        """Validate execution request"""
        
        # Check template exists
        template = self.template_registry.get_template(request.template_id)
        if not template:
            return False
        
        # Check deadline
        if request.deadline and datetime.now() > request.deadline:
            return False
        
        # Check market data
        if not request.market_data:
            return False
        
        return True
    
    async def _is_request_valid(self, request: ExecutionRequest) -> bool:
        """Check if request is still valid"""
        
        # Check deadline
        if request.deadline and datetime.now() > request.deadline:
            return False
        
        # Check timeout
        elapsed = (datetime.now() - request.created_at).total_seconds() * 1000
        if elapsed > request.timeout_ms:
            return False
        
        return True
    
    async def _initialize_load_balancing(self):
        """Initialize load balancing system"""
        
        # Initialize round-robin counters
        for category in TemplateCategory:
            self.round_robin_counters[category] = 0
        
        # Initialize category performance tracking
        for category in TemplateCategory:
            self.category_performance[category] = {
                'avg_execution_time_ms': 0.0,
                'success_rate': 1.0,
                'throughput_per_second': 0.0
            }
    
    async def _update_execution_statistics(self, request: ExecutionRequest,
                                         result: Dict[str, Any], execution_time_ms: float):
        """Update execution statistics"""
        
        # Global statistics
        self.execution_statistics['total_executions'] += 1
        if result.get('success', False):
            self.execution_statistics['successful_executions'] += 1
        
        # Calculate success rate
        self.execution_statistics['success_rate'] = (
            self.execution_statistics['successful_executions'] / 
            self.execution_statistics['total_executions']
        )
        
        # Update average execution time
        alpha = 0.1
        current_avg = self.execution_statistics.get('avg_execution_time_ms', 0.0)
        self.execution_statistics['avg_execution_time_ms'] = (
            (1 - alpha) * current_avg + alpha * execution_time_ms
        )
        
        # Category-specific statistics
        template = self.template_registry.get_template(request.template_id)
        if template:
            category = template.metadata.category
            cat_perf = self.category_performance[category]
            
            # Update category averages
            current_cat_avg = cat_perf.get('avg_execution_time_ms', 0.0)
            cat_perf['avg_execution_time_ms'] = (
                (1 - alpha) * current_cat_avg + alpha * execution_time_ms
            )
            
            # Update category success rate
            cat_perf['total_executions'] = cat_perf.get('total_executions', 0) + 1
            if result.get('success', False):
                cat_perf['successful_executions'] = cat_perf.get('successful_executions', 0) + 1
            
            cat_perf['success_rate'] = (
                cat_perf['successful_executions'] / cat_perf['total_executions']
            )
    
    async def get_execution_statistics(self) -> Dict[str, Any]:
        """Get comprehensive execution statistics"""
        
        return {
            'global_statistics': dict(self.execution_statistics),
            'category_performance': {
                category.value: dict(perf) 
                for category, perf in self.category_performance.items()
            },
            'queue_lengths': {
                queue_type.value: len(queue) 
                for queue_type, queue in self.execution_queues.items()
            },
            'active_executions': len(self.active_executions),
            'slot_utilization': {
                slot_id: {
                    'is_busy': slot.is_busy,
                    'total_executions': slot.total_executions,
                    'success_rate': slot.successful_executions / max(slot.total_executions, 1),
                    'avg_execution_time_ms': slot.avg_execution_time_ms
                }
                for slot_id, slot in self.execution_slots.items()
            }
        }
    
    async def shutdown(self):
        """Shutdown execution coordinator"""
        
        self.logger.info("Shutting down template execution coordinator")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Cancel queue processors
        for queue_type, task in self.queue_processors.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Clear queues
        for queue in self.execution_queues.values():
            queue.clear()
        
        self.logger.info("Template execution coordinator shutdown completed")
