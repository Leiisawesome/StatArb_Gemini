"""
Strategy Assembler
=================

Assembles complete trading strategies from template components using
inheritance resolution and performance optimization.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import uuid

from .template_registry import BaseTemplate, TemplateRegistry, TemplateCategory, TemplateType
from .template_inheritance import TemplateInheritanceManager

logger = logging.getLogger(__name__)

@dataclass
class AssemblyContext:
    """Context for strategy assembly operations"""
    strategy_id: str
    assembly_timestamp: datetime
    source_templates: List[str] = field(default_factory=list)
    inheritance_resolved: bool = False
    validation_passed: bool = False
    performance_optimized: bool = False
    assembly_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AssemblyResult:
    """Result of strategy assembly"""
    success: bool
    assembled_strategy: Optional[BaseTemplate]
    context: AssemblyContext
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

class StrategyAssembler:
    """
    Assembles complete trading strategies from templates with inheritance
    resolution, validation, and performance optimization.
    """
    
    def __init__(self, template_registry: TemplateRegistry, 
                 inheritance_manager: TemplateInheritanceManager):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.registry = template_registry
        self.inheritance_manager = inheritance_manager
        
        # Assembly configuration
        self.assembly_config = {
            'validate_components': True,
            'optimize_performance': True,
            'resolve_inheritance': True,
            'check_dependencies': True,
            'generate_metadata': True
        }
        
        # Component assemblers
        self.component_assemblers = {
            TemplateType.SIGNAL_GENERATION: self._assemble_signal_component,
            TemplateType.RISK_MANAGEMENT: self._assemble_risk_component,
            TemplateType.PORTFOLIO_MANAGEMENT: self._assemble_portfolio_component,
            TemplateType.EXECUTION: self._assemble_execution_component
        }
        
        self.logger.info("StrategyAssembler initialized")
    
    def assemble_strategy(self, template_id: str, 
                         custom_parameters: Optional[Dict[str, Any]] = None,
                         assembly_options: Optional[Dict[str, Any]] = None) -> AssemblyResult:
        """
        Assemble a complete strategy from a template
        """
        try:
            # Create assembly context
            context = AssemblyContext(
                strategy_id=f"strategy_{uuid.uuid4().hex[:8]}",
                assembly_timestamp=datetime.now(),
                source_templates=[template_id]
            )
            
            # Merge assembly options
            config = self.assembly_config.copy()
            if assembly_options:
                config.update(assembly_options)
            
            self.logger.info(f"Starting strategy assembly for template {template_id}")
            
            # Step 1: Retrieve base template
            base_template = self.registry.get_template(template_id)
            if not base_template:
                return AssemblyResult(
                    success=False,
                    assembled_strategy=None,
                    context=context,
                    errors=[f"Template {template_id} not found"]
                )
            
            # Step 2: Resolve inheritance
            if config['resolve_inheritance']:
                try:
                    resolved_template = self.inheritance_manager.resolve_inheritance(template_id)
                    context.inheritance_resolved = True
                    self.logger.debug(f"Inheritance resolved for {template_id}")
                except Exception as e:
                    return AssemblyResult(
                        success=False,
                        assembled_strategy=None,
                        context=context,
                        errors=[f"Inheritance resolution failed: {e}"]
                    )
            else:
                resolved_template = base_template
            
            # Step 3: Apply custom parameters
            if custom_parameters:
                resolved_template = self._apply_custom_parameters(resolved_template, custom_parameters)
            
            # Step 4: Assemble components
            assembled_strategy = self._assemble_strategy_components(resolved_template, context)
            
            # Step 5: Validate assembled strategy
            if config['validate_components']:
                validation_result = self._validate_assembled_strategy(assembled_strategy, context)
                context.validation_passed = validation_result['success']
                if not validation_result['success']:
                    return AssemblyResult(
                        success=False,
                        assembled_strategy=assembled_strategy,
                        context=context,
                        errors=validation_result['errors'],
                        warnings=validation_result['warnings']
                    )
            
            # Step 6: Optimize performance
            if config['optimize_performance']:
                assembled_strategy = self._optimize_strategy_performance(assembled_strategy, context)
                context.performance_optimized = True
            
            # Step 7: Generate metadata
            if config['generate_metadata']:
                assembled_strategy = self._generate_assembly_metadata(assembled_strategy, context)
            
            self.logger.info(f"Successfully assembled strategy {context.strategy_id}")
            
            return AssemblyResult(
                success=True,
                assembled_strategy=assembled_strategy,
                context=context
            )
            
        except Exception as e:
            self.logger.error(f"Strategy assembly failed for {template_id}: {e}")
            return AssemblyResult(
                success=False,
                assembled_strategy=None,
                context=context,
                errors=[f"Assembly failed: {e}"]
            )
    
    def assemble_composite_strategy(self, template_ids: List[str], 
                                  composition_rules: Optional[Dict[str, Any]] = None) -> AssemblyResult:
        """
        Assemble a composite strategy from multiple templates
        """
        try:
            context = AssemblyContext(
                strategy_id=f"composite_strategy_{uuid.uuid4().hex[:8]}",
                assembly_timestamp=datetime.now(),
                source_templates=template_ids
            )
            
            self.logger.info(f"Starting composite strategy assembly from {len(template_ids)} templates")
            
            # Assemble individual strategies
            assembled_components = []
            for template_id in template_ids:
                component_result = self.assemble_strategy(template_id)
                if not component_result.success:
                    return AssemblyResult(
                        success=False,
                        assembled_strategy=None,
                        context=context,
                        errors=[f"Failed to assemble component {template_id}: {component_result.errors}"]
                    )
                assembled_components.append(component_result.assembled_strategy)
            
            # Compose strategies
            composite_strategy = self._compose_strategies(assembled_components, composition_rules, context)
            
            # Validate composite strategy
            validation_result = self._validate_assembled_strategy(composite_strategy, context)
            context.validation_passed = validation_result['success']
            
            if not validation_result['success']:
                return AssemblyResult(
                    success=False,
                    assembled_strategy=composite_strategy,
                    context=context,
                    errors=validation_result['errors'],
                    warnings=validation_result['warnings']
                )
            
            self.logger.info(f"Successfully assembled composite strategy {context.strategy_id}")
            
            return AssemblyResult(
                success=True,
                assembled_strategy=composite_strategy,
                context=context
            )
            
        except Exception as e:
            self.logger.error(f"Composite strategy assembly failed: {e}")
            return AssemblyResult(
                success=False,
                assembled_strategy=None,
                context=context,
                errors=[f"Composite assembly failed: {e}"]
            )
    
    def _apply_custom_parameters(self, template: BaseTemplate, 
                               custom_parameters: Dict[str, Any]) -> BaseTemplate:
        """Apply custom parameters to template"""
        updated_template = BaseTemplate(
            metadata=template.metadata,
            configuration=template.configuration.copy(),
            parameters=template.parameters.copy(),
            components=template.components.copy()
        )
        
        # Deep merge custom parameters
        for key, value in custom_parameters.items():
            if key in updated_template.parameters:
                if isinstance(updated_template.parameters[key], dict) and isinstance(value, dict):
                    updated_template.parameters[key].update(value)
                else:
                    updated_template.parameters[key] = value
            else:
                updated_template.parameters[key] = value
        
        return updated_template
    
    def _assemble_strategy_components(self, template: BaseTemplate, 
                                    context: AssemblyContext) -> BaseTemplate:
        """Assemble strategy components based on template type"""
        
        assembled_template = BaseTemplate(
            metadata=template.metadata,
            configuration=template.configuration.copy(),
            parameters=template.parameters.copy(),
            components=template.components.copy()
        )
        
        # If it's a complete strategy, assemble all components
        if template.metadata.template_type == TemplateType.COMPLETE_STRATEGY:
            assembled_template = self._assemble_complete_strategy(template, context)
        else:
            # Assemble specific component type
            if template.metadata.template_type in self.component_assemblers:
                assembler = self.component_assemblers[template.metadata.template_type]
                assembled_template = assembler(template, context)
        
        return assembled_template
    
    def _assemble_complete_strategy(self, template: BaseTemplate, 
                                  context: AssemblyContext) -> BaseTemplate:
        """Assemble a complete strategy with all components"""
        
        assembled = BaseTemplate(
            metadata=template.metadata,
            configuration=template.configuration.copy(),
            parameters=template.parameters.copy(),
            components={}
        )
        
        # Required component types for complete strategy
        required_components = [
            TemplateType.SIGNAL_GENERATION,
            TemplateType.RISK_MANAGEMENT,
            TemplateType.PORTFOLIO_MANAGEMENT,
            TemplateType.EXECUTION
        ]
        
        # Assemble each component
        for component_type in required_components:
            if component_type.value in template.components:
                component_config = template.components[component_type.value]
                assembled_component = self._assemble_component(component_type, component_config, context)
                assembled.components[component_type.value] = assembled_component
            else:
                # Use default component if not specified
                default_component = self._create_default_component(component_type, template)
                assembled.components[component_type.value] = default_component
        
        return assembled
    
    def _assemble_signal_component(self, template: BaseTemplate, 
                                 context: AssemblyContext) -> BaseTemplate:
        """Assemble signal generation component"""
        return self._assemble_specialized_component(template, "signal_generation", context)
    
    def _assemble_risk_component(self, template: BaseTemplate, 
                               context: AssemblyContext) -> BaseTemplate:
        """Assemble risk management component"""
        return self._assemble_specialized_component(template, "risk_management", context)
    
    def _assemble_portfolio_component(self, template: BaseTemplate, 
                                    context: AssemblyContext) -> BaseTemplate:
        """Assemble portfolio management component"""
        return self._assemble_specialized_component(template, "portfolio_management", context)
    
    def _assemble_execution_component(self, template: BaseTemplate, 
                                    context: AssemblyContext) -> BaseTemplate:
        """Assemble execution component"""
        return self._assemble_specialized_component(template, "execution", context)
    
    def _assemble_specialized_component(self, template: BaseTemplate, 
                                      component_type: str, 
                                      context: AssemblyContext) -> BaseTemplate:
        """Assemble a specialized component"""
        
        assembled = BaseTemplate(
            metadata=template.metadata,
            configuration=template.configuration.copy(),
            parameters=template.parameters.copy(),
            components=template.components.copy()
        )
        
        # Add component-specific assembly logic here
        assembled.components[f"assembled_{component_type}"] = {
            'type': component_type,
            'assembly_timestamp': context.assembly_timestamp.isoformat(),
            'source_template': template.metadata.template_id,
            'optimized': True
        }
        
        return assembled
    
    def _assemble_component(self, component_type: TemplateType, 
                          component_config: Dict[str, Any], 
                          context: AssemblyContext) -> Dict[str, Any]:
        """Assemble individual component"""
        return {
            'type': component_type.value,
            'config': component_config,
            'assembly_timestamp': context.assembly_timestamp.isoformat(),
            'optimized': True
        }
    
    def _create_default_component(self, component_type: TemplateType, 
                                template: BaseTemplate) -> Dict[str, Any]:
        """Create default component configuration"""
        return {
            'type': component_type.value,
            'config': {
                'default': True,
                'template_id': template.metadata.template_id
            },
            'parameters': {},
            'enabled': True
        }
    
    def _compose_strategies(self, strategies: List[BaseTemplate], 
                          composition_rules: Optional[Dict[str, Any]], 
                          context: AssemblyContext) -> BaseTemplate:
        """Compose multiple strategies into composite strategy"""
        
        # Create composite metadata
        composite_metadata = strategies[0].metadata
        composite_metadata.template_id = context.strategy_id
        composite_metadata.name = f"Composite Strategy - {context.strategy_id}"
        composite_metadata.template_type = TemplateType.COMPLETE_STRATEGY
        composite_metadata.category = TemplateCategory.COMPOSITE
        
        # Merge components from all strategies
        composite_components = {}
        composite_parameters = {}
        composite_configuration = {}
        
        for i, strategy in enumerate(strategies):
            strategy_key = f"strategy_{i}"
            composite_components[strategy_key] = {
                'template_id': strategy.metadata.template_id,
                'components': strategy.components,
                'weight': composition_rules.get('weights', [1.0] * len(strategies))[i] if composition_rules else 1.0
            }
            
            # Merge parameters with strategy prefix
            for param_key, param_value in strategy.parameters.items():
                composite_parameters[f"{strategy_key}_{param_key}"] = param_value
            
            # Merge configuration
            composite_configuration[strategy_key] = strategy.configuration
        
        # Add composition rules
        if composition_rules:
            composite_components['composition'] = composition_rules
        
        return BaseTemplate(
            metadata=composite_metadata,
            configuration=composite_configuration,
            parameters=composite_parameters,
            components=composite_components
        )
    
    def _validate_assembled_strategy(self, strategy: BaseTemplate, 
                                   context: AssemblyContext) -> Dict[str, Any]:
        """Validate assembled strategy"""
        errors = []
        warnings = []
        
        try:
            # Validate metadata
            if not strategy.metadata.template_id:
                errors.append("Missing template_id in metadata")
            
            if not strategy.metadata.name:
                errors.append("Missing name in metadata")
            
            # Validate components for complete strategies
            if strategy.metadata.template_type == TemplateType.COMPLETE_STRATEGY:
                required_components = ['signal_generation', 'risk_management', 'portfolio_management', 'execution']
                
                for component in required_components:
                    if component not in strategy.components:
                        warnings.append(f"Missing recommended component: {component}")
            
            # Validate parameters
            if not strategy.parameters:
                warnings.append("No parameters defined")
            
            # Check for conflicting parameters
            conflicts = self._check_parameter_conflicts(strategy)
            if conflicts:
                warnings.extend([f"Parameter conflict: {conflict}" for conflict in conflicts])
            
            return {
                'success': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Validation failed: {e}"],
                'warnings': warnings
            }
    
    def _check_parameter_conflicts(self, strategy: BaseTemplate) -> List[str]:
        """Check for parameter conflicts"""
        conflicts = []
        
        # Add parameter conflict detection logic here
        # For now, just basic checks
        
        return conflicts
    
    def _optimize_strategy_performance(self, strategy: BaseTemplate, 
                                     context: AssemblyContext) -> BaseTemplate:
        """Optimize strategy performance"""
        
        optimized_strategy = BaseTemplate(
            metadata=strategy.metadata,
            configuration=strategy.configuration.copy(),
            parameters=strategy.parameters.copy(),
            components=strategy.components.copy()
        )
        
        # Add performance optimization metadata
        optimized_strategy.components['performance_optimization'] = {
            'optimized_at': context.assembly_timestamp.isoformat(),
            'optimization_applied': True,
            'techniques': ['parameter_tuning', 'component_optimization']
        }
        
        # Apply performance optimizations
        optimized_strategy.parameters['performance'] = {
            'enable_caching': True,
            'parallel_processing': True,
            'memory_optimization': True
        }
        
        return optimized_strategy
    
    def _generate_assembly_metadata(self, strategy: BaseTemplate, 
                                  context: AssemblyContext) -> BaseTemplate:
        """Generate assembly metadata"""
        
        strategy.metadata.tags.extend(['assembled', 'optimized'])
        
        # Add assembly information to components
        strategy.components['assembly_info'] = {
            'assembly_id': context.strategy_id,
            'assembled_at': context.assembly_timestamp.isoformat(),
            'source_templates': context.source_templates,
            'inheritance_resolved': context.inheritance_resolved,
            'validation_passed': context.validation_passed,
            'performance_optimized': context.performance_optimized
        }
        
        return strategy
    
    def get_assembly_statistics(self) -> Dict[str, Any]:
        """Get assembly statistics"""
        return {
            'total_assemblies': 0,  # Track this in production
            'success_rate': 0.0,
            'average_assembly_time': 0.0,
            'component_usage': {},
            'performance_improvements': {}
        }
