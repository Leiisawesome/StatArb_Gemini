"""
Template-Compatible Core Engine
===============================

Advanced core engine that seamlessly integrates with the hybrid template system,
providing template-aware processing with inheritance support and category-based optimization.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json
from collections import defaultdict

from strategy_templates.base import TemplateRegistry, BaseTemplate, TemplateCategory
from strategy_layer.template_integration import TemplateStrategyManager, TemplatePerformanceTracker
from core_structure.unified_core_engine import UnifiedCoreEngine, CoreEngineConfig, EngineStatus, TradingMode
from .template_config import TemplateEngineConfig, ExecutionMode

logger = logging.getLogger(__name__)

# Use configuration classes from template_config module
# TemplateEngineConfig and ExecutionMode are imported above

@dataclass
class TemplateExecutionResult:
    """Result from template execution"""
    template_id: str
    template_category: TemplateCategory
    execution_time_ms: float
    
    # Execution results
    signals: Dict[str, float] = field(default_factory=dict)
    positions: Dict[str, float] = field(default_factory=dict)
    orders: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics
    execution_latency_ms: float = 0.0
    processing_efficiency: float = 1.0
    resource_utilization: Dict[str, float] = field(default_factory=dict)
    
    # Template-specific metrics
    inheritance_impact: Dict[str, float] = field(default_factory=dict)
    category_performance_score: float = 0.0
    
    # Status
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class TemplateCoreEngine:
    """
    Advanced core engine with template-aware capabilities, inheritance processing,
    and category-based optimization for maximum performance and flexibility.
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 strategy_manager: TemplateStrategyManager,
                 performance_tracker: TemplatePerformanceTracker,
                 base_core_engine: Optional[UnifiedCoreEngine] = None,
                 config: Optional[TemplateEngineConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.strategy_manager = strategy_manager
        self.performance_tracker = performance_tracker
        self.config = config or TemplateEngineConfig()
        
        # Initialize base core engine or create new one
        if base_core_engine:
            self.base_engine = base_core_engine
        else:
            base_config = CoreEngineConfig()
            self.base_engine = UnifiedCoreEngine(base_config)
        
        # Initialize template-specific components with lazy loading
        self.component_manager = None
        self.execution_coordinator = None
        self.performance_integrator = None
        
        # Template execution state
        self.active_templates: Dict[str, str] = {}  # template_id -> instance_id
        self.template_performance: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.category_statistics: Dict[TemplateCategory, Dict[str, float]] = defaultdict(dict)
        
        # Execution metrics
        self.execution_history: List[TemplateExecutionResult] = []
        self.category_load_balancer: Dict[TemplateCategory, List[str]] = defaultdict(list)
        
        self.logger.info("TemplateCoreEngine initialized")
    
    async def initialize(self) -> bool:
        """Initialize the template-compatible core engine"""
        try:
            self.logger.info("Initializing template-compatible core engine")
            
            # Base engine is already initialized in constructor
            # await self.base_engine.initialize()  # Not needed
            self.logger.info("Base engine ready")
            
            # Initialize template components with lazy imports
            try:
                from .template_component_manager import TemplateComponentManager
                self.component_manager = TemplateComponentManager(self.template_registry, self.base_engine)
                await self.component_manager.initialize()
                self.logger.info("Component manager initialized")
            except ImportError as e:
                self.logger.warning(f"Component manager not available: {e}")
            
            try:
                from .template_execution_coordinator import TemplateExecutionCoordinator
                self.execution_coordinator = TemplateExecutionCoordinator(
                    self.template_registry, self.strategy_manager, self.config
                )
                await self.execution_coordinator.initialize()
                self.logger.info("Execution coordinator initialized")
            except ImportError as e:
                self.logger.warning(f"Execution coordinator not available: {e}")
            
            try:
                from .template_performance_integrator import TemplatePerformanceIntegrator
                self.performance_integrator = TemplatePerformanceIntegrator(
                    self.performance_tracker, self.config
                )
                await self.performance_integrator.initialize()
                self.logger.info("Performance integrator initialized")
            except ImportError as e:
                self.logger.warning(f"Performance integrator not available: {e}")
            
            # Setup category-based optimizations
            await self._setup_category_optimizations()
            
            # Load and prepare active templates
            await self._prepare_active_templates()
            
            self.logger.info("Template core engine initialization completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Template core engine initialization failed: {e}")
            return False
    
    async def execute_template_strategy(self, template_id: str,
                                      market_data: Dict[str, Any],
                                      execution_context: Optional[Dict[str, Any]] = None) -> TemplateExecutionResult:
        """
        Execute strategy based on template with full template-aware processing
        """
        try:
            start_time = datetime.now()
            
            # Get template and validate
            template = self.template_registry.get_template(template_id)
            if not template:
                return TemplateExecutionResult(
                    template_id=template_id,
                    template_category=TemplateCategory.BASE,
                    execution_time_ms=0.0,
                    success=False,
                    errors=[f"Template {template_id} not found"]
                )
            
            self.logger.debug(f"Executing template strategy: {template_id}")
            
            # Execute based on configured mode
            if self.config.template_execution_mode == ExecutionMode.SINGLE_TEMPLATE:
                result = await self._execute_single_template(template, market_data, execution_context)
            
            elif self.config.template_execution_mode == ExecutionMode.INHERITANCE_CHAIN:
                result = await self._execute_inheritance_chain(template, market_data, execution_context)
            
            elif self.config.template_execution_mode == ExecutionMode.CATEGORY_BATCH:
                result = await self._execute_category_batch(template, market_data, execution_context)
            
            elif self.config.template_execution_mode == ExecutionMode.ADAPTIVE_ROUTING:
                result = await self._execute_adaptive_routing(template, market_data, execution_context)
            
            else:
                result = await self._execute_single_template(template, market_data, execution_context)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            result.execution_time_ms = execution_time
            
            # Update performance tracking
            await self._update_template_performance(result)
            
            # Store execution history
            self.execution_history.append(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Template strategy execution failed: {e}")
            return TemplateExecutionResult(
                template_id=template_id,
                template_category=TemplateCategory.BASE,
                execution_time_ms=0.0,
                success=False,
                errors=[str(e)]
            )
    
    async def _execute_single_template(self, template: BaseTemplate,
                                     market_data: Dict[str, Any],
                                     execution_context: Optional[Dict[str, Any]]) -> TemplateExecutionResult:
        """Execute a single template strategy"""
        
        template_id = template.metadata.template_id
        
        # Get or create strategy instance
        if template_id not in self.active_templates:
            instance_id = self.strategy_manager.create_strategy_instance(template_id)
            self.active_templates[template_id] = instance_id
        else:
            instance_id = self.active_templates[template_id]
        
        # Execute strategy
        execution_result = self.strategy_manager.execute_strategy_instance(instance_id, market_data)
        
        # Apply category-specific optimizations
        optimized_result = await self._apply_category_optimizations(
            template, execution_result, execution_context
        )
        
        # Create template execution result
        result = TemplateExecutionResult(
            template_id=template_id,
            template_category=template.metadata.category,
            execution_time_ms=0.0,  # Will be set by caller
            signals=optimized_result.signals,
            positions=optimized_result.positions,
            orders=getattr(optimized_result, 'orders', []),
            execution_latency_ms=getattr(optimized_result, 'execution_time_ms', 0.0),
            success=not bool(optimized_result.errors),
            errors=optimized_result.errors,
            warnings=getattr(optimized_result, 'warnings', [])
        )
        
        # Calculate category performance score
        result.category_performance_score = await self._calculate_category_performance_score(
            template, result
        )
        
        return result
    
    async def _execute_inheritance_chain(self, template: BaseTemplate,
                                       market_data: Dict[str, Any],
                                       execution_context: Optional[Dict[str, Any]]) -> TemplateExecutionResult:
        """Execute template with inheritance chain processing"""
        
        # Get inheritance chain
        inheritance_chain = await self._get_inheritance_chain(template)
        
        # Execute each template in chain
        chain_results = []
        inheritance_weights = []
        
        for i, chain_template in enumerate(inheritance_chain):
            # Calculate inheritance weight (decay for deeper parents)
            weight = self.config.inheritance_weight_decay ** i
            inheritance_weights.append(weight)
            
            # Execute template
            result = await self._execute_single_template(chain_template, market_data, execution_context)
            chain_results.append(result)
        
        # Combine results using inheritance weights
        combined_result = await self._combine_inheritance_results(
            chain_results, inheritance_weights, template
        )
        
        # Add inheritance impact analysis
        combined_result.inheritance_impact = await self._analyze_inheritance_impact(
            chain_results, inheritance_weights
        )
        
        return combined_result
    
    async def _execute_category_batch(self, template: BaseTemplate,
                                    market_data: Dict[str, Any],
                                    execution_context: Optional[Dict[str, Any]]) -> TemplateExecutionResult:
        """Execute all templates in the same category"""
        
        category = template.metadata.category
        category_templates = self.template_registry.search_templates(category=category)
        
        # Execute templates in parallel
        batch_tasks = []
        for cat_template in category_templates[:self.config.max_parallel_templates]:
            task = self._execute_single_template(cat_template, market_data, execution_context)
            batch_tasks.append(task)
        
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Filter successful results
        successful_results = [r for r in batch_results if isinstance(r, TemplateExecutionResult) and r.success]
        
        if not successful_results:
            return TemplateExecutionResult(
                template_id=template.metadata.template_id,
                template_category=category,
                execution_time_ms=0.0,
                success=False,
                errors=["No successful executions in category batch"]
            )
        
        # Combine category results
        combined_result = await self._combine_category_results(successful_results, template)
        
        return combined_result
    
    async def _execute_adaptive_routing(self, template: BaseTemplate,
                                      market_data: Dict[str, Any],
                                      execution_context: Optional[Dict[str, Any]]) -> TemplateExecutionResult:
        """Execute with adaptive routing based on performance"""
        
        # Get performance-based execution strategy
        execution_strategy = await self._determine_adaptive_strategy(template)
        
        if execution_strategy == "inheritance":
            return await self._execute_inheritance_chain(template, market_data, execution_context)
        elif execution_strategy == "category_batch":
            return await self._execute_category_batch(template, market_data, execution_context)
        else:
            return await self._execute_single_template(template, market_data, execution_context)
    
    async def _apply_category_optimizations(self, template: BaseTemplate,
                                          execution_result: Any,
                                          execution_context: Optional[Dict[str, Any]]) -> Any:
        """Apply category-specific optimizations"""
        
        category = template.metadata.category
        optimized_result = execution_result
        
        # Apply category-specific risk limits
        if hasattr(optimized_result, 'positions'):
            risk_limits = self.config.category_risk_limits.get(category, {})
            max_position = risk_limits.get('max_position', 0.1)
            
            # Scale positions if they exceed category limits
            for symbol, position in optimized_result.positions.items():
                if abs(position) > max_position:
                    scale_factor = max_position / abs(position)
                    optimized_result.positions[symbol] *= scale_factor
        
        # Apply category-specific signal processing
        if hasattr(optimized_result, 'signals'):
            category_weight = self.config.category_performance_weights.get(category, 1.0)
            
            # Enhance signals based on category performance weight
            for symbol, signal in optimized_result.signals.items():
                optimized_result.signals[symbol] *= category_weight
        
        return optimized_result
    
    async def _get_inheritance_chain(self, template: BaseTemplate) -> List[BaseTemplate]:
        """Get ordered inheritance chain for template"""
        
        chain = [template]
        current_template = template
        depth = 0
        
        while (current_template.metadata.parent_templates and 
               depth < self.config.inheritance_depth_limit):
            
            # Get first parent (could be enhanced to handle multiple parents)
            parent_id = current_template.metadata.parent_templates[0]
            parent_template = self.template_registry.get_template(parent_id)
            
            if parent_template and parent_template not in chain:
                chain.append(parent_template)
                current_template = parent_template
                depth += 1
            else:
                break
        
        return chain
    
    async def _combine_inheritance_results(self, chain_results: List[TemplateExecutionResult],
                                         weights: List[float],
                                         primary_template: BaseTemplate) -> TemplateExecutionResult:
        """Combine results from inheritance chain"""
        
        if not chain_results:
            return TemplateExecutionResult(
                template_id=primary_template.metadata.template_id,
                template_category=primary_template.metadata.category,
                execution_time_ms=0.0,
                success=False,
                errors=["No chain results to combine"]
            )
        
        # Use primary result as base
        combined_result = chain_results[0]
        
        if len(chain_results) > 1:
            # Weighted combination of signals
            combined_signals = {}
            combined_positions = {}
            
            # Process all symbols across chain results
            all_symbols = set()
            for result in chain_results:
                all_symbols.update(result.signals.keys())
                all_symbols.update(result.positions.keys())
            
            for symbol in all_symbols:
                # Combine signals with weights
                weighted_signal = 0.0
                total_weight = 0.0
                
                for result, weight in zip(chain_results, weights):
                    if symbol in result.signals:
                        weighted_signal += result.signals[symbol] * weight
                        total_weight += weight
                
                if total_weight > 0:
                    combined_signals[symbol] = weighted_signal / total_weight
                
                # Combine positions with weights
                weighted_position = 0.0
                total_weight = 0.0
                
                for result, weight in zip(chain_results, weights):
                    if symbol in result.positions:
                        weighted_position += result.positions[symbol] * weight
                        total_weight += weight
                
                if total_weight > 0:
                    combined_positions[symbol] = weighted_position / total_weight
            
            combined_result.signals = combined_signals
            combined_result.positions = combined_positions
        
        return combined_result
    
    async def _combine_category_results(self, category_results: List[TemplateExecutionResult],
                                      primary_template: BaseTemplate) -> TemplateExecutionResult:
        """Combine results from category batch execution"""
        
        if not category_results:
            return TemplateExecutionResult(
                template_id=primary_template.metadata.template_id,
                template_category=primary_template.metadata.category,
                execution_time_ms=0.0,
                success=False,
                errors=["No category results to combine"]
            )
        
        # Use consensus-based combination
        combined_signals = {}
        combined_positions = {}
        
        # Get all symbols
        all_symbols = set()
        for result in category_results:
            all_symbols.update(result.signals.keys())
            all_symbols.update(result.positions.keys())
        
        for symbol in all_symbols:
            # Consensus signal (median)
            symbol_signals = [r.signals.get(symbol, 0.0) for r in category_results if symbol in r.signals]
            if symbol_signals:
                combined_signals[symbol] = np.median(symbol_signals)
            
            # Consensus position (median)
            symbol_positions = [r.positions.get(symbol, 0.0) for r in category_results if symbol in r.positions]
            if symbol_positions:
                combined_positions[symbol] = np.median(symbol_positions)
        
        # Create combined result
        combined_result = TemplateExecutionResult(
            template_id=primary_template.metadata.template_id,
            template_category=primary_template.metadata.category,
            execution_time_ms=sum(r.execution_time_ms for r in category_results) / len(category_results),
            signals=combined_signals,
            positions=combined_positions,
            success=True
        )
        
        return combined_result
    
    async def _analyze_inheritance_impact(self, chain_results: List[TemplateExecutionResult],
                                        weights: List[float]) -> Dict[str, float]:
        """Analyze the impact of inheritance on performance"""
        
        impact_analysis = {}
        
        if len(chain_results) > 1:
            primary_result = chain_results[0]
            
            for i, (result, weight) in enumerate(zip(chain_results[1:], weights[1:]), 1):
                # Compare signals strength
                primary_signal_strength = sum(abs(s) for s in primary_result.signals.values())
                parent_signal_strength = sum(abs(s) for s in result.signals.values())
                
                if primary_signal_strength > 0:
                    signal_impact = (parent_signal_strength / primary_signal_strength) * weight
                    impact_analysis[f"parent_{i}_signal_impact"] = signal_impact
                
                # Compare position sizing
                primary_position_size = sum(abs(p) for p in primary_result.positions.values())
                parent_position_size = sum(abs(p) for p in result.positions.values())
                
                if primary_position_size > 0:
                    position_impact = (parent_position_size / primary_position_size) * weight
                    impact_analysis[f"parent_{i}_position_impact"] = position_impact
        
        return impact_analysis
    
    async def _calculate_category_performance_score(self, template: BaseTemplate,
                                                  result: TemplateExecutionResult) -> float:
        """Calculate category-based performance score"""
        
        category = template.metadata.category
        base_score = 1.0
        
        # Apply category performance weight
        category_weight = self.config.category_performance_weights.get(category, 1.0)
        
        # Calculate signal quality score
        signal_strength = sum(abs(s) for s in result.signals.values())
        signal_score = min(signal_strength / 5.0, 1.0)  # Normalized to [0, 1]
        
        # Calculate execution efficiency score
        efficiency_score = result.processing_efficiency
        
        # Calculate latency score (lower is better)
        max_latency = self.config.template_execution_timeout_ms
        latency_score = max(0.0, 1.0 - (result.execution_latency_ms / max_latency))
        
        # Combine scores
        performance_score = (base_score * category_weight * 
                           (signal_score * 0.4 + efficiency_score * 0.3 + latency_score * 0.3))
        
        return performance_score
    
    async def _determine_adaptive_strategy(self, template: BaseTemplate) -> str:
        """Determine optimal execution strategy based on performance"""
        
        template_id = template.metadata.template_id
        
        # Get historical performance
        if template_id in self.template_performance:
            perf = self.template_performance[template_id]
            avg_latency = perf.get('avg_latency_ms', 100.0)
            success_rate = perf.get('success_rate', 1.0)
            
            # If high latency, try inheritance chain
            if avg_latency > self.config.template_execution_timeout_ms * 0.8:
                return "inheritance"
            
            # If low success rate, try category batch
            if success_rate < 0.8:
                return "category_batch"
        
        # Default to single template
        return "single"
    
    async def _setup_category_optimizations(self):
        """Setup category-based optimizations"""
        
        # Initialize category load balancers
        for category in TemplateCategory:
            templates = self.template_registry.search_templates(category=category)
            self.category_load_balancer[category] = [t.metadata.template_id for t in templates]
        
        # Initialize category statistics
        for category in TemplateCategory:
            self.category_statistics[category] = {
                'avg_execution_time_ms': 0.0,
                'success_rate': 1.0,
                'template_count': len(self.category_load_balancer[category])
            }
    
    async def _prepare_active_templates(self):
        """Prepare and pre-load active templates"""
        
        # Get high-priority templates for pre-loading
        high_priority_templates = []
        
        for category in [TemplateCategory.COMPOSITE, TemplateCategory.SPECIFIC]:
            category_templates = self.template_registry.search_templates(category=category)
            high_priority_templates.extend(category_templates[:2])  # Top 2 from each
        
        # Pre-create strategy instances for high-priority templates
        for template in high_priority_templates:
            try:
                instance_id = self.strategy_manager.create_strategy_instance(
                    template.metadata.template_id
                )
                self.active_templates[template.metadata.template_id] = instance_id
                self.logger.debug(f"Pre-loaded template: {template.metadata.template_id}")
            except Exception as e:
                self.logger.warning(f"Failed to pre-load template {template.metadata.template_id}: {e}")
    
    async def _update_template_performance(self, result: TemplateExecutionResult):
        """Update template performance tracking"""
        
        template_id = result.template_id
        
        # Update template-specific performance
        if template_id not in self.template_performance:
            self.template_performance[template_id] = {
                'total_executions': 0,
                'successful_executions': 0,
                'total_latency_ms': 0.0,
                'avg_latency_ms': 0.0,
                'success_rate': 1.0
            }
        
        perf = self.template_performance[template_id]
        perf['total_executions'] += 1
        
        if result.success:
            perf['successful_executions'] += 1
            perf['total_latency_ms'] += result.execution_latency_ms
        
        perf['avg_latency_ms'] = perf['total_latency_ms'] / max(perf['successful_executions'], 1)
        perf['success_rate'] = perf['successful_executions'] / perf['total_executions']
        
        # Update category statistics
        category = result.template_category
        cat_stats = self.category_statistics[category]
        
        # Update category averages (simple moving average)
        alpha = 0.1  # Smoothing factor
        cat_stats['avg_execution_time_ms'] = (
            (1 - alpha) * cat_stats['avg_execution_time_ms'] + 
            alpha * result.execution_time_ms
        )
        
        # Update performance integrator
        await self.performance_integrator.update_template_performance(result)
    
    async def get_engine_status(self) -> Dict[str, Any]:
        """Get comprehensive engine status"""
        
        base_status = await self.base_engine.get_system_status()
        
        template_status = {
            'template_engine_status': 'active',
            'active_templates': len(self.active_templates),
            'execution_history_count': len(self.execution_history),
            'category_statistics': dict(self.category_statistics),
            'template_performance': dict(self.template_performance),
            'execution_modes': {
                'current_mode': self.config.template_execution_mode.value,
                'inheritance_enabled': self.config.enable_inheritance_processing,
                'category_optimization_enabled': self.config.enable_category_optimization
            }
        }
        
        return {**base_status, **template_status}
    
    async def shutdown(self):
        """Shutdown template core engine"""
        
        self.logger.info("Shutting down template core engine")
        
        # Stop all active template instances
        for template_id, instance_id in self.active_templates.items():
            try:
                self.strategy_manager.stop_strategy_instance(instance_id)
            except Exception as e:
                self.logger.warning(f"Failed to stop template instance {template_id}: {e}")
        
        # Shutdown components safely
        if self.performance_integrator:
            await self.performance_integrator.shutdown()
        if self.execution_coordinator:
            await self.execution_coordinator.shutdown()
        if self.component_manager:
            await self.component_manager.shutdown()
        
        # Shutdown base engine (if it has a shutdown method)
        if self.base_engine and hasattr(self.base_engine, 'shutdown') and callable(getattr(self.base_engine, 'shutdown')):
            shutdown_method = getattr(self.base_engine, 'shutdown')
            # Check if it's an async method
            import inspect
            if inspect.iscoroutinefunction(shutdown_method):
                await shutdown_method()
            else:
                shutdown_method()
        else:
            # Base engine doesn't need shutdown or has no shutdown method
            self.logger.info("Base engine does not require explicit shutdown or has no shutdown method.")
        
        self.logger.info("Template core engine shutdown completed")
