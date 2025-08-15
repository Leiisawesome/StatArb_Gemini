"""
Template Strategy Manager
========================

Manages the lifecycle of template-based strategies including creation,
execution, monitoring, and performance tracking.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import uuid
import threading
from collections import defaultdict

from strategy_layer.base import StrategyDefinition, StrategyResult, StrategyExecutionResult
from strategy_templates.base import TemplateRegistry, BaseTemplate
from .template_strategy_adapter import TemplateStrategyAdapter, TemplateAdaptationResult

logger = logging.getLogger(__name__)

@dataclass
class StrategyInstance:
    """Running strategy instance"""
    instance_id: str
    template_id: str
    strategy_object: StrategyDefinition
    created_at: datetime
    last_executed: Optional[datetime] = None
    status: str = "active"  # active, paused, stopped, error
    execution_count: int = 0
    total_runtime_ms: float = 0.0
    last_result: Optional[StrategyResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TemplateStrategyStats:
    """Statistics for template-based strategies"""
    total_instances: int = 0
    active_instances: int = 0
    total_executions: int = 0
    average_execution_time_ms: float = 0.0
    success_rate: float = 0.0
    templates_used: Set[str] = field(default_factory=set)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

class TemplateStrategyManager:
    """
    Manages template-based strategy instances with lifecycle management,
    execution coordination, and performance monitoring.
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 template_adapter: TemplateStrategyAdapter):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.template_adapter = template_adapter
        
        # Strategy instance management
        self.strategy_instances: Dict[str, StrategyInstance] = {}
        self.template_to_instances: Dict[str, List[str]] = defaultdict(list)
        
        # Execution coordination
        self.execution_queue: List[str] = []
        self.execution_lock = threading.RLock()
        
        # Performance tracking
        self.execution_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}
        
        # Configuration
        self.max_concurrent_strategies = 50
        self.execution_timeout_seconds = 30
        self.enable_performance_tracking = True
        
        self.logger.info("TemplateStrategyManager initialized")
    
    def create_strategy_instance(self, template_id: str, 
                               instance_name: Optional[str] = None,
                               custom_parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new strategy instance from a template
        
        Returns:
            instance_id: Unique identifier for the created instance
        """
        try:
            # Generate unique instance ID
            instance_id = instance_name or f"strategy_{uuid.uuid4().hex[:8]}"
            
            self.logger.info(f"Creating strategy instance {instance_id} from template {template_id}")
            
            # Adapt template to strategy
            adaptation_result = self.template_adapter.adapt_template_to_strategy(
                template_id, custom_parameters
            )
            
            if not adaptation_result.success:
                raise ValueError(f"Template adaptation failed: {adaptation_result.errors}")
            
            # Create strategy instance
            strategy_instance = StrategyInstance(
                instance_id=instance_id,
                template_id=template_id,
                strategy_object=adaptation_result.strategy_object,
                created_at=datetime.now(),
                metadata={
                    'custom_parameters': custom_parameters or {},
                    'adaptation_metadata': adaptation_result.metadata,
                    'template_category': adaptation_result.strategy_object.get_template_metadata().category.value,
                    'inheritance_chain': adaptation_result.strategy_object.get_inheritance_chain()
                }
            )
            
            # Register instance
            self.strategy_instances[instance_id] = strategy_instance
            self.template_to_instances[template_id].append(instance_id)
            
            self.logger.info(f"Strategy instance {instance_id} created successfully")
            return instance_id
            
        except Exception as e:
            self.logger.error(f"Failed to create strategy instance from template {template_id}: {e}")
            raise
    
    def execute_strategy_instance(self, instance_id: str, 
                                market_data: Dict[str, Any]) -> StrategyResult:
        """
        Execute a strategy instance with market data
        """
        try:
            if instance_id not in self.strategy_instances:
                raise ValueError(f"Strategy instance {instance_id} not found")
            
            instance = self.strategy_instances[instance_id]
            
            if instance.status != "active":
                raise ValueError(f"Strategy instance {instance_id} is not active (status: {instance.status})")
            
            execution_start = datetime.now()
            
            self.logger.debug(f"Executing strategy instance {instance_id}")
            
            # Execute strategy
            strategy_result = self._execute_strategy_with_monitoring(instance, market_data)
            
            # Update instance metadata
            execution_time = datetime.now()
            execution_duration = (execution_time - execution_start).total_seconds() * 1000
            
            instance.last_executed = execution_time
            instance.execution_count += 1
            instance.total_runtime_ms += execution_duration
            instance.last_result = strategy_result
            
            # Track performance
            if self.enable_performance_tracking:
                self._record_execution_metrics(instance_id, execution_duration, strategy_result)
            
            self.logger.debug(f"Strategy instance {instance_id} executed in {execution_duration:.1f}ms")
            
            return strategy_result
            
        except Exception as e:
            self.logger.error(f"Strategy execution failed for instance {instance_id}: {e}")
            
            # Update instance status
            if instance_id in self.strategy_instances:
                self.strategy_instances[instance_id].status = "error"
            
            # Return error result
            return StrategyResult(
                strategy_id=instance_id,
                execution_time=datetime.now(),
                errors=[f"Execution failed: {e}"]
            )
    
    def execute_multiple_instances(self, instance_ids: List[str], 
                                 market_data: Dict[str, Any]) -> Dict[str, StrategyResult]:
        """
        Execute multiple strategy instances with the same market data
        """
        results = {}
        
        for instance_id in instance_ids:
            try:
                results[instance_id] = self.execute_strategy_instance(instance_id, market_data)
            except Exception as e:
                self.logger.error(f"Failed to execute instance {instance_id}: {e}")
                results[instance_id] = StrategyResult(
                    strategy_id=instance_id,
                    execution_time=datetime.now(),
                    errors=[f"Execution failed: {e}"]
                )
        
        return results
    
    def pause_strategy_instance(self, instance_id: str):
        """Pause a strategy instance"""
        if instance_id in self.strategy_instances:
            self.strategy_instances[instance_id].status = "paused"
            self.logger.info(f"Strategy instance {instance_id} paused")
        else:
            raise ValueError(f"Strategy instance {instance_id} not found")
    
    def resume_strategy_instance(self, instance_id: str):
        """Resume a paused strategy instance"""
        if instance_id in self.strategy_instances:
            instance = self.strategy_instances[instance_id]
            if instance.status == "paused":
                instance.status = "active"
                self.logger.info(f"Strategy instance {instance_id} resumed")
            else:
                raise ValueError(f"Strategy instance {instance_id} is not paused")
        else:
            raise ValueError(f"Strategy instance {instance_id} not found")
    
    def stop_strategy_instance(self, instance_id: str):
        """Stop and remove a strategy instance"""
        if instance_id in self.strategy_instances:
            instance = self.strategy_instances[instance_id]
            instance.status = "stopped"
            
            # Remove from template mapping
            template_id = instance.template_id
            if template_id in self.template_to_instances:
                self.template_to_instances[template_id].remove(instance_id)
            
            # Remove instance
            del self.strategy_instances[instance_id]
            
            self.logger.info(f"Strategy instance {instance_id} stopped and removed")
        else:
            raise ValueError(f"Strategy instance {instance_id} not found")
    
    def get_strategy_instance(self, instance_id: str) -> Optional[StrategyInstance]:
        """Get strategy instance by ID"""
        return self.strategy_instances.get(instance_id)
    
    def list_strategy_instances(self, template_id: Optional[str] = None, 
                              status: Optional[str] = None) -> List[StrategyInstance]:
        """List strategy instances with optional filtering"""
        instances = list(self.strategy_instances.values())
        
        if template_id:
            instances = [inst for inst in instances if inst.template_id == template_id]
        
        if status:
            instances = [inst for inst in instances if inst.status == status]
        
        return instances
    
    def get_template_strategy_stats(self) -> TemplateStrategyStats:
        """Get comprehensive statistics about template-based strategies"""
        
        total_instances = len(self.strategy_instances)
        active_instances = len([inst for inst in self.strategy_instances.values() if inst.status == "active"])
        total_executions = sum(inst.execution_count for inst in self.strategy_instances.values())
        
        # Calculate average execution time
        total_runtime = sum(inst.total_runtime_ms for inst in self.strategy_instances.values())
        avg_execution_time = total_runtime / max(total_executions, 1)
        
        # Calculate success rate
        successful_executions = 0
        for inst in self.strategy_instances.values():
            if inst.last_result and not inst.last_result.errors:
                successful_executions += inst.execution_count
        
        success_rate = successful_executions / max(total_executions, 1)
        
        # Get templates used
        templates_used = set(inst.template_id for inst in self.strategy_instances.values())
        
        return TemplateStrategyStats(
            total_instances=total_instances,
            active_instances=active_instances,
            total_executions=total_executions,
            average_execution_time_ms=avg_execution_time,
            success_rate=success_rate,
            templates_used=templates_used,
            performance_metrics=self.performance_metrics
        )
    
    def bulk_create_from_templates(self, template_ids: List[str],
                                 instances_per_template: int = 1) -> Dict[str, List[str]]:
        """Create multiple strategy instances from multiple templates"""
        created_instances = {}
        
        for template_id in template_ids:
            instances = []
            for i in range(instances_per_template):
                try:
                    instance_name = f"{template_id}_instance_{i+1}"
                    instance_id = self.create_strategy_instance(template_id, instance_name)
                    instances.append(instance_id)
                except Exception as e:
                    self.logger.error(f"Failed to create instance {i+1} for template {template_id}: {e}")
            
            created_instances[template_id] = instances
        
        return created_instances
    
    def update_strategy_parameters(self, instance_id: str, 
                                 parameters: Dict[str, Any]) -> bool:
        """Update parameters for a strategy instance"""
        try:
            if instance_id not in self.strategy_instances:
                raise ValueError(f"Strategy instance {instance_id} not found")
            
            instance = self.strategy_instances[instance_id]
            
            # Update strategy configuration parameters
            for key, value in parameters.items():
                instance.strategy_object.config.parameters[key] = value
            
            # Update metadata
            instance.metadata['last_parameter_update'] = datetime.now().isoformat()
            instance.metadata['updated_parameters'] = list(parameters.keys())
            
            self.logger.info(f"Updated parameters for strategy instance {instance_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update parameters for instance {instance_id}: {e}")
            return False
    
    def _execute_strategy_with_monitoring(self, instance: StrategyInstance, 
                                        market_data: Dict[str, Any]) -> StrategyResult:
        """Execute strategy with comprehensive monitoring"""
        
        strategy = instance.strategy_object
        execution_start = datetime.now()
        
        try:
            # Generate signals
            signals = strategy.generate_signals(market_data)
            
            # Calculate position sizes
            positions = strategy.calculate_position_sizes(signals, market_data)
            
            # Validate risk
            risk_valid = strategy.validate_risk(positions, market_data)
            
            # Create strategy result
            result = StrategyResult(
                strategy_id=instance.instance_id,
                execution_time=execution_start,
                signals=signals,
                positions=positions if risk_valid else {},
                performance_metrics={
                    'signal_count': len(signals),
                    'position_count': len(positions),
                    'risk_validation_passed': risk_valid,
                    'execution_time_ms': (datetime.now() - execution_start).total_seconds() * 1000
                }
            )
            
            if not risk_valid:
                result.warnings.append("Risk validation failed - positions cleared")
            
            return result
            
        except Exception as e:
            return StrategyResult(
                strategy_id=instance.instance_id,
                execution_time=execution_start,
                errors=[f"Strategy execution error: {e}"]
            )
    
    def _record_execution_metrics(self, instance_id: str, execution_time_ms: float, 
                                result: StrategyResult):
        """Record execution metrics for performance tracking"""
        
        execution_record = {
            'instance_id': instance_id,
            'execution_time_ms': execution_time_ms,
            'timestamp': datetime.now().isoformat(),
            'signal_count': len(result.signals),
            'position_count': len(result.positions),
            'success': len(result.errors) == 0,
            'template_id': self.strategy_instances[instance_id].template_id
        }
        
        self.execution_history.append(execution_record)
        
        # Maintain rolling window of last 1000 executions
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
    
    def cleanup_stopped_instances(self):
        """Clean up stopped strategy instances"""
        stopped_instances = [
            instance_id for instance_id, instance in self.strategy_instances.items()
            if instance.status == "stopped"
        ]
        
        for instance_id in stopped_instances:
            if instance_id in self.strategy_instances:
                del self.strategy_instances[instance_id]
        
        self.logger.info(f"Cleaned up {len(stopped_instances)} stopped instances")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all strategy instances"""
        
        stats = self.get_template_strategy_stats()
        
        # Calculate performance metrics from execution history
        recent_executions = self.execution_history[-100:] if self.execution_history else []
        
        if recent_executions:
            avg_execution_time = sum(ex['execution_time_ms'] for ex in recent_executions) / len(recent_executions)
            success_rate = sum(1 for ex in recent_executions if ex['success']) / len(recent_executions)
            avg_signals = sum(ex['signal_count'] for ex in recent_executions) / len(recent_executions)
        else:
            avg_execution_time = 0
            success_rate = 0
            avg_signals = 0
        
        return {
            'total_instances': stats.total_instances,
            'active_instances': stats.active_instances,
            'total_executions': stats.total_executions,
            'recent_avg_execution_time_ms': avg_execution_time,
            'recent_success_rate': success_rate,
            'recent_avg_signals_per_execution': avg_signals,
            'templates_in_use': len(stats.templates_used),
            'execution_history_size': len(self.execution_history)
        }
