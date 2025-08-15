"""
Template Component Manager
=========================

Manages template-compatible core components with inheritance support
and category-based component selection and optimization.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Type
from datetime import datetime
from enum import Enum
from collections import defaultdict

from strategy_templates.base import TemplateRegistry, BaseTemplate, TemplateCategory
from core_structure.unified_core_engine import UnifiedCoreEngine
from core_structure.signal_generation.signal_generator import SignalGenerator
from core_structure.risk.risk_manager import RiskManager
from core_structure.execution_engine.execution_engine import ExecutionEngine
from core_structure.portfolio.portfolio_manager import PortfolioManager
from core_structure.market_data.data_manager import DataManager

logger = logging.getLogger(__name__)

class ComponentType(Enum):
    """Core component types"""
    SIGNAL_GENERATOR = "signal_generator"
    RISK_MANAGER = "risk_manager"
    EXECUTION_ENGINE = "execution_engine"
    PORTFOLIO_MANAGER = "portfolio_manager"
    DATA_MANAGER = "data_manager"

@dataclass
class ComponentConfig:
    """Configuration for template-compatible components"""
    component_type: ComponentType
    template_category: TemplateCategory
    inheritance_support: bool = True
    
    # Performance settings
    max_processing_time_ms: int = 100
    enable_caching: bool = True
    cache_ttl_seconds: int = 60
    
    # Category-specific settings
    category_optimization_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ComponentInstance:
    """Instance of a template-compatible component"""
    component_id: str
    component_type: ComponentType
    template_category: TemplateCategory
    instance: Any
    config: ComponentConfig
    
    # Performance tracking
    execution_count: int = 0
    total_execution_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0
    success_rate: float = 1.0
    
    # Template associations
    associated_templates: List[str] = field(default_factory=list)
    
    def update_performance(self, execution_time_ms: float, success: bool):
        """Update component performance metrics"""
        self.execution_count += 1
        
        if success:
            self.total_execution_time_ms += execution_time_ms
            self.avg_execution_time_ms = self.total_execution_time_ms / self.execution_count
        
        # Update success rate with exponential smoothing
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)

class TemplateComponentManager:
    """
    Manages template-compatible versions of core components with
    inheritance support and category-based optimization.
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 base_core_engine: UnifiedCoreEngine):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.base_core_engine = base_core_engine
        
        # Component management
        self.component_instances: Dict[str, ComponentInstance] = {}
        self.category_components: Dict[TemplateCategory, Dict[ComponentType, List[str]]] = defaultdict(lambda: defaultdict(list))
        self.component_cache: Dict[str, Any] = {}
        
        # Component factories for each category
        self.component_factories = self._initialize_component_factories()
        
        # Performance tracking
        self.component_performance: Dict[ComponentType, Dict[str, float]] = defaultdict(dict)
        
        self.logger.info("TemplateComponentManager initialized")
    
    def _initialize_component_factories(self) -> Dict[TemplateCategory, Dict[ComponentType, Type]]:
        """Initialize component factories for each category"""
        
        return {
            TemplateCategory.BASE: {
                ComponentType.SIGNAL_GENERATOR: BaseSignalGenerator,
                ComponentType.RISK_MANAGER: BaseRiskManager,
                ComponentType.EXECUTION_ENGINE: BaseExecutionEngine,
                ComponentType.PORTFOLIO_MANAGER: BasePortfolioManager,
                ComponentType.DATA_MANAGER: BaseDataManager
            },
            TemplateCategory.SPECIFIC: {
                ComponentType.SIGNAL_GENERATOR: SpecificSignalGenerator,
                ComponentType.RISK_MANAGER: SpecificRiskManager,
                ComponentType.EXECUTION_ENGINE: SpecificExecutionEngine,
                ComponentType.PORTFOLIO_MANAGER: SpecificPortfolioManager,
                ComponentType.DATA_MANAGER: SpecificDataManager
            },
            TemplateCategory.COMPOSITE: {
                ComponentType.SIGNAL_GENERATOR: CompositeSignalGenerator,
                ComponentType.RISK_MANAGER: CompositeRiskManager,
                ComponentType.EXECUTION_ENGINE: CompositeExecutionEngine,
                ComponentType.PORTFOLIO_MANAGER: CompositePortfolioManager,
                ComponentType.DATA_MANAGER: CompositeDataManager
            }
        }
    
    async def initialize(self):
        """Initialize template component manager"""
        
        self.logger.info("Initializing template component manager")
        
        # Create default components for each category
        for category in TemplateCategory:
            await self._create_category_components(category)
        
        # Setup component caching
        await self._setup_component_caching()
        
        self.logger.info("Template component manager initialization completed")
    
    async def get_component_for_template(self, template: BaseTemplate,
                                       component_type: ComponentType) -> Optional[ComponentInstance]:
        """Get appropriate component instance for template"""
        
        try:
            # Determine component selection strategy
            component_id = await self._select_optimal_component(template, component_type)
            
            if component_id and component_id in self.component_instances:
                return self.component_instances[component_id]
            
            # Create new component instance if needed
            return await self._create_component_for_template(template, component_type)
            
        except Exception as e:
            self.logger.error(f"Failed to get component for template {template.metadata.template_id}: {e}")
            return None
    
    async def _select_optimal_component(self, template: BaseTemplate,
                                       component_type: ComponentType) -> Optional[str]:
        """Select optimal component based on template and performance"""
        
        category = template.metadata.category
        
        # Get available components for category and type
        available_components = self.category_components[category][component_type]
        
        if not available_components:
            return None
        
        # Performance-based selection
        best_component_id = None
        best_score = float('-inf')
        
        for component_id in available_components:
            if component_id in self.component_instances:
                instance = self.component_instances[component_id]
                
                # Calculate selection score
                score = await self._calculate_component_score(instance, template)
                
                if score > best_score:
                    best_score = score
                    best_component_id = component_id
        
        return best_component_id
    
    async def _calculate_component_score(self, component: ComponentInstance,
                                        template: BaseTemplate) -> float:
        """Calculate component selection score for template"""
        
        base_score = 1.0
        
        # Performance score (based on success rate and execution time)
        performance_score = component.success_rate * (1.0 / max(component.avg_execution_time_ms, 1.0))
        
        # Category compatibility score
        if component.template_category == template.metadata.category:
            category_score = 1.0
        elif component.template_category == TemplateCategory.BASE:
            category_score = 0.8  # Base components work with all categories
        else:
            category_score = 0.5  # Cross-category compatibility
        
        # Template association score
        association_score = 1.0
        if template.metadata.template_id in component.associated_templates:
            association_score = 1.2  # Bonus for previously used with this template
        
        return base_score * performance_score * category_score * association_score
    
    async def _create_component_for_template(self, template: BaseTemplate,
                                           component_type: ComponentType) -> Optional[ComponentInstance]:
        """Create new component instance for template"""
        
        try:
            category = template.metadata.category
            
            # Get component factory
            factory = self.component_factories.get(category, {}).get(component_type)
            if not factory:
                # Fallback to base category
                factory = self.component_factories[TemplateCategory.BASE][component_type]
            
            # Create component configuration
            config = ComponentConfig(
                component_type=component_type,
                template_category=category,
                category_optimization_params=await self._get_category_optimization_params(
                    category, component_type
                )
            )
            
            # Create component instance
            component_instance = factory(template, config, self.base_core_engine)
            await component_instance.initialize()
            
            # Create component wrapper
            component_id = f"{category.value}_{component_type.value}_{template.metadata.template_id}"
            wrapper = ComponentInstance(
                component_id=component_id,
                component_type=component_type,
                template_category=category,
                instance=component_instance,
                config=config,
                associated_templates=[template.metadata.template_id]
            )
            
            # Register component
            self.component_instances[component_id] = wrapper
            self.category_components[category][component_type].append(component_id)
            
            self.logger.debug(f"Created component {component_id} for template {template.metadata.template_id}")
            return wrapper
            
        except Exception as e:
            self.logger.error(f"Failed to create component for template: {e}")
            return None
    
    async def _create_category_components(self, category: TemplateCategory):
        """Create default components for category"""
        
        for component_type in ComponentType:
            try:
                # Create generic component for category
                factory = self.component_factories[category][component_type]
                config = ComponentConfig(
                    component_type=component_type,
                    template_category=category
                )
                
                # Create with placeholder template
                placeholder_template = await self._create_placeholder_template(category)
                component_instance = factory(placeholder_template, config, self.base_core_engine)
                await component_instance.initialize()
                
                # Create wrapper
                component_id = f"{category.value}_{component_type.value}_default"
                wrapper = ComponentInstance(
                    component_id=component_id,
                    component_type=component_type,
                    template_category=category,
                    instance=component_instance,
                    config=config
                )
                
                # Register
                self.component_instances[component_id] = wrapper
                self.category_components[category][component_type].append(component_id)
                
            except Exception as e:
                self.logger.warning(f"Failed to create default {component_type.value} for {category.value}: {e}")
    
    async def _get_category_optimization_params(self, category: TemplateCategory,
                                              component_type: ComponentType) -> Dict[str, Any]:
        """Get category-specific optimization parameters"""
        
        base_params = {
            "enable_fast_mode": False,
            "cache_size": 100,
            "timeout_ms": 100
        }
        
        if category == TemplateCategory.BASE:
            return {
                **base_params,
                "enable_fast_mode": True,
                "cache_size": 50,
                "timeout_ms": 50
            }
        elif category == TemplateCategory.SPECIFIC:
            return {
                **base_params,
                "cache_size": 200,
                "timeout_ms": 150,
                "enable_specialization": True
            }
        elif category == TemplateCategory.COMPOSITE:
            return {
                **base_params,
                "cache_size": 500,
                "timeout_ms": 200,
                "enable_ensemble_mode": True,
                "parallel_processing": True
            }
        
        return base_params
    
    async def _setup_component_caching(self):
        """Setup component result caching"""
        
        # Initialize cache for each component type
        for component_type in ComponentType:
            self.component_cache[component_type.value] = {}
    
    async def _create_placeholder_template(self, category: TemplateCategory) -> BaseTemplate:
        """Create placeholder template for component initialization"""
        
        from strategy_templates.base import TemplateMetadata, TemplateType, TemplateStatus
        
        metadata = TemplateMetadata(
            template_id=f"placeholder_{category.value}",
            name=f"Placeholder {category.value}",
            version="1.0.0",
            category=category,
            template_type=TemplateType.COMPLETE_STRATEGY,
            status=TemplateStatus.DRAFT,
            description=f"Placeholder template for {category.value}",
            author="System",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        return BaseTemplate(
            metadata=metadata,
            parameters={},
            components={}
        )
    
    async def update_component_performance(self, component_id: str,
                                         execution_time_ms: float, success: bool):
        """Update component performance metrics"""
        
        if component_id in self.component_instances:
            self.component_instances[component_id].update_performance(execution_time_ms, success)
    
    async def get_component_statistics(self) -> Dict[str, Any]:
        """Get component performance statistics"""
        
        stats = {
            'total_components': len(self.component_instances),
            'category_distribution': {},
            'component_type_distribution': {},
            'performance_summary': {}
        }
        
        # Category distribution
        for category in TemplateCategory:
            count = sum(len(components) for components in self.category_components[category].values())
            stats['category_distribution'][category.value] = count
        
        # Component type distribution
        for component_type in ComponentType:
            count = sum(1 for comp in self.component_instances.values() 
                       if comp.component_type == component_type)
            stats['component_type_distribution'][component_type.value] = count
        
        # Performance summary
        for component_type in ComponentType:
            type_components = [comp for comp in self.component_instances.values() 
                             if comp.component_type == component_type]
            
            if type_components:
                avg_execution_time = np.mean([comp.avg_execution_time_ms for comp in type_components])
                avg_success_rate = np.mean([comp.success_rate for comp in type_components])
                
                stats['performance_summary'][component_type.value] = {
                    'avg_execution_time_ms': avg_execution_time,
                    'avg_success_rate': avg_success_rate
                }
        
        return stats
    
    async def shutdown(self):
        """Shutdown component manager"""
        
        self.logger.info("Shutting down template component manager")
        
        # Shutdown all component instances
        for component_id, component in self.component_instances.items():
            try:
                if hasattr(component.instance, 'shutdown'):
                    await component.instance.shutdown()
            except Exception as e:
                self.logger.warning(f"Failed to shutdown component {component_id}: {e}")
        
        self.component_instances.clear()
        self.category_components.clear()
        self.component_cache.clear()


# Template-compatible component implementations
class BaseSignalGenerator:
    """Base template-compatible signal generator"""
    
    def __init__(self, template: BaseTemplate, config: ComponentConfig, core_engine: UnifiedCoreEngine):
        self.template = template
        self.config = config
        self.core_engine = core_engine
        self.base_signal_generator = core_engine.signal_generator
    
    async def initialize(self):
        """Initialize component"""
        pass
    
    async def generate_signals(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate signals based on template configuration"""
        # Use base signal generator with template parameters
        return await self.base_signal_generator.generate_signals(market_data)

class SpecificSignalGenerator(BaseSignalGenerator):
    """Specific template-compatible signal generator with enhanced features"""
    
    async def generate_signals(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate enhanced signals for specific templates"""
        base_signals = await super().generate_signals(market_data)
        
        # Apply template-specific enhancements
        enhanced_signals = {}
        for symbol, signal in base_signals.items():
            # Apply category-specific scaling
            enhanced_signals[symbol] = signal * 1.2  # 20% boost for specific category
        
        return enhanced_signals

class CompositeSignalGenerator(BaseSignalGenerator):
    """Composite template-compatible signal generator with ensemble capabilities"""
    
    async def generate_signals(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate ensemble signals for composite templates"""
        base_signals = await super().generate_signals(market_data)
        
        # Apply ensemble logic
        ensemble_signals = {}
        for symbol, signal in base_signals.items():
            # Apply composite-specific processing
            ensemble_signals[symbol] = signal * 1.5  # 50% boost for composite category
        
        return ensemble_signals

# Similar implementations for other component types
class BaseRiskManager:
    def __init__(self, template: BaseTemplate, config: ComponentConfig, core_engine: UnifiedCoreEngine):
        self.template = template
        self.config = config
        self.core_engine = core_engine
    
    async def initialize(self):
        pass

class SpecificRiskManager(BaseRiskManager):
    pass

class CompositeRiskManager(BaseRiskManager):
    pass

class BaseExecutionEngine:
    def __init__(self, template: BaseTemplate, config: ComponentConfig, core_engine: UnifiedCoreEngine):
        self.template = template
        self.config = config
        self.core_engine = core_engine
    
    async def initialize(self):
        pass

class SpecificExecutionEngine(BaseExecutionEngine):
    pass

class CompositeExecutionEngine(BaseExecutionEngine):
    pass

class BasePortfolioManager:
    def __init__(self, template: BaseTemplate, config: ComponentConfig, core_engine: UnifiedCoreEngine):
        self.template = template
        self.config = config
        self.core_engine = core_engine
    
    async def initialize(self):
        pass

class SpecificPortfolioManager(BasePortfolioManager):
    pass

class CompositePortfolioManager(BasePortfolioManager):
    pass

class BaseDataManager:
    def __init__(self, template: BaseTemplate, config: ComponentConfig, core_engine: UnifiedCoreEngine):
        self.template = template
        self.config = config
        self.core_engine = core_engine
    
    async def initialize(self):
        pass

class SpecificDataManager(BaseDataManager):
    pass

class CompositeDataManager(BaseDataManager):
    pass
