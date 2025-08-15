"""
Template Core Engine (Minimal Implementation)
============================================

Minimal implementation of the template-compatible core engine
to avoid circular import issues.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from strategy_templates.base import TemplateRegistry, BaseTemplate, TemplateCategory
from .template_config import TemplateEngineConfig, ExecutionMode

logger = logging.getLogger(__name__)

@dataclass
class TemplateExecutionResult:
    """Result of template execution"""
    template_id: str
    success: bool
    execution_time_ms: float
    execution_latency_ms: float = 0.0
    
    # Execution outputs
    signals: Dict[str, float] = field(default_factory=dict)
    positions: Dict[str, float] = field(default_factory=dict)
    
    # Performance metrics
    category_performance_score: float = 0.0
    inheritance_impact: Dict[str, float] = field(default_factory=dict)
    
    # Error tracking
    errors: List[str] = field(default_factory=list)

class TemplateCoreEngine:
    """
    Minimal template-compatible core engine implementation
    """
    
    def __init__(self, config: TemplateEngineConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = config.template_registry
        
        # Engine state
        self.is_initialized = False
        self.active_executions = {}
        self.execution_history = []
        
        # Component managers (will be set during initialization)
        self.component_manager = None
        self.execution_coordinator = None
        self.performance_integrator = None
        
        self.logger.info("Template Core Engine created with minimal implementation")
    
    async def initialize(self):
        """Initialize the core engine"""
        
        self.logger.info("Initializing Template Core Engine")
        
        # Initialize component managers with delayed import to avoid circular dependencies
        try:
            from .template_component_manager import TemplateComponentManager
            from core_structure.unified_core_engine import UnifiedCoreEngine
            
            # Create a minimal unified core engine for compatibility
            from core_structure.unified_core_engine import CoreEngineConfig, TradingMode
            base_config = CoreEngineConfig(
                trading_mode=TradingMode.SIMULATION,
                enable_logging=True
            )
            base_core_engine = UnifiedCoreEngine(base_config)
            
            self.component_manager = TemplateComponentManager(self.template_registry, base_core_engine)
            await self.component_manager.initialize()
            self.logger.info("Component manager initialized")
        except (ImportError, Exception) as e:
            self.logger.warning(f"Component manager not available: {e}")
        
        try:
            from .template_execution_coordinator import TemplateExecutionCoordinator
            self.execution_coordinator = TemplateExecutionCoordinator(self.template_registry)
            await self.execution_coordinator.initialize()
            self.logger.info("Execution coordinator initialized")
        except (ImportError, Exception) as e:
            self.logger.warning(f"Execution coordinator not available: {e}")
        
        try:
            from .template_performance_integrator import TemplatePerformanceIntegrator
            from strategy_layer.template_integration import TemplatePerformanceTracker
            
            performance_tracker = TemplatePerformanceTracker(self.template_registry)
            self.performance_integrator = TemplatePerformanceIntegrator(performance_tracker, self.config)
            await self.performance_integrator.initialize()
            self.logger.info("Performance integrator initialized")
        except (ImportError, Exception) as e:
            self.logger.warning(f"Performance integrator not available: {e}")
        
        self.is_initialized = True
        self.logger.info("Template Core Engine initialization completed")
    
    async def execute_template(self, template_id: str, market_data: Dict[str, Any]) -> TemplateExecutionResult:
        """Execute a single template"""
        
        if not self.is_initialized:
            await self.initialize()
        
        start_time = datetime.now()
        
        try:
            # Get template from registry
            template = self.template_registry.get_template(template_id)
            if not template:
                return TemplateExecutionResult(
                    template_id=template_id,
                    success=False,
                    execution_time_ms=0.0,
                    errors=[f"Template '{template_id}' not found"]
                )
            
            # Create minimal execution result
            result = TemplateExecutionResult(
                template_id=template_id,
                success=True,
                execution_time_ms=0.0
            )
            
            # Generate mock signals (simplified implementation)
            symbols = market_data.get('symbols', ['AAPL', 'GOOGL', 'MSFT'])
            prices = market_data.get('prices', {})
            
            for symbol in symbols:
                if symbol in prices:
                    # Simple momentum signal based on price
                    price = prices[symbol]
                    signal = (price - 100.0) / 100.0  # Normalized signal
                    result.signals[symbol] = max(-1.0, min(1.0, signal))
                    
                    # Simple position sizing
                    position_size = template.parameters.get('position_size', 0.05)
                    result.positions[symbol] = result.signals[symbol] * position_size
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            result.execution_time_ms = execution_time
            result.execution_latency_ms = execution_time * 0.1  # Simplified latency
            
            # Category performance score (simplified)
            signal_strength = sum(abs(s) for s in result.signals.values())
            result.category_performance_score = min(1.0, signal_strength / len(result.signals)) if result.signals else 0.0
            
            # Apply category weights
            category_weight = self.config.category_performance_weights.get(template.metadata.category, 1.0)
            result.category_performance_score *= category_weight
            
            # Store in execution history
            self.execution_history.append(result)
            
            # Update performance integrator if available
            if self.performance_integrator:
                try:
                    await self.performance_integrator.update_template_performance(result)
                except Exception as e:
                    self.logger.warning(f"Performance integrator update failed: {e}")
            
            self.logger.info(f"Template {template_id} executed successfully in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            error_result = TemplateExecutionResult(
                template_id=template_id,
                success=False,
                execution_time_ms=execution_time,
                errors=[str(e)]
            )
            
            self.logger.error(f"Template execution failed: {e}")
            return error_result
    
    async def execute_category(self, category: TemplateCategory, market_data: Dict[str, Any]) -> List[TemplateExecutionResult]:
        """Execute all templates in a category"""
        
        if not self.is_initialized:
            await self.initialize()
        
        # Get templates in category from the registry's templates dictionary
        all_templates = list(self.template_registry.templates.keys())
        category_templates = []
        
        for template_id in all_templates:
            template = self.template_registry.get_template(template_id)
            if template and template.metadata.category == category:
                category_templates.append(template_id)
        
        if not category_templates:
            self.logger.warning(f"No templates found in category {category.value}")
            return []
        
        # Execute all templates in category
        results = []
        for template_id in category_templates:
            result = await self.execute_template(template_id, market_data)
            results.append(result)
        
        self.logger.info(f"Category {category.value} execution completed: {len(results)} templates")
        return results
    
    async def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        
        if not self.execution_history:
            return {'total_executions': 0}
        
        successful_executions = sum(1 for result in self.execution_history if result.success)
        total_executions = len(self.execution_history)
        
        avg_execution_time = sum(result.execution_time_ms for result in self.execution_history) / total_executions
        avg_performance_score = sum(result.category_performance_score for result in self.execution_history) / total_executions
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': successful_executions / total_executions,
            'avg_execution_time_ms': avg_execution_time,
            'avg_performance_score': avg_performance_score,
            'last_execution': self.execution_history[-1].template_id if self.execution_history else None
        }
    
    async def shutdown(self):
        """Shutdown the core engine"""
        
        self.logger.info("Shutting down Template Core Engine")
        
        # Shutdown component managers
        if self.component_manager:
            try:
                await self.component_manager.shutdown()
            except Exception as e:
                self.logger.warning(f"Component manager shutdown error: {e}")
        
        if self.execution_coordinator:
            try:
                await self.execution_coordinator.shutdown()
            except Exception as e:
                self.logger.warning(f"Execution coordinator shutdown error: {e}")
        
        if self.performance_integrator:
            try:
                await self.performance_integrator.shutdown()
            except Exception as e:
                self.logger.warning(f"Performance integrator shutdown error: {e}")
        
        # Clear state
        self.active_executions.clear()
        self.execution_history.clear()
        self.is_initialized = False
        
        self.logger.info("Template Core Engine shutdown completed")
