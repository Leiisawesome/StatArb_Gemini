"""
Template Inheritance Manager
===========================

Manages template inheritance, composition, and conflict resolution
in the hybrid template system.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Set
from enum import Enum
import copy

from .template_registry import BaseTemplate, TemplateRegistry

logger = logging.getLogger(__name__)

class InheritanceStrategy(Enum):
    """Strategies for resolving inheritance conflicts"""
    OVERRIDE = "override"         # Child overrides parent
    MERGE = "merge"              # Merge parent and child
    EXTEND = "extend"            # Child extends parent
    COMPOSITE = "composite"      # Combine as composite

class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    CHILD_WINS = "child_wins"
    PARENT_WINS = "parent_wins"
    MERGE_DEEP = "merge_deep"
    RAISE_ERROR = "raise_error"

@dataclass
class InheritanceRule:
    """Rule for inheritance behavior"""
    field_path: str                              # Path to field (e.g., "parameters.signal.lookback")
    strategy: InheritanceStrategy
    conflict_resolution: ConflictResolution
    merge_function: Optional[str] = None         # Custom merge function name
    validation_function: Optional[str] = None    # Custom validation function name
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InheritanceContext:
    """Context for inheritance operations"""
    template_id: str
    parent_chain: List[str] = field(default_factory=list)
    inheritance_rules: List[InheritanceRule] = field(default_factory=list)
    applied_rules: List[str] = field(default_factory=list)
    conflicts_resolved: List[Dict[str, Any]] = field(default_factory=list)

class TemplateInheritanceManager:
    """
    Manages template inheritance with support for multiple inheritance,
    composition patterns, and intelligent conflict resolution.
    """
    
    def __init__(self, template_registry: TemplateRegistry):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.registry = template_registry
        
        # Default inheritance rules
        self.default_rules = self._create_default_rules()
        
        # Custom merge functions
        self.merge_functions = {
            'parameters_merge': self._merge_parameters,
            'components_merge': self._merge_components,
            'configuration_merge': self._merge_configuration,
            'tags_merge': self._merge_tags,
            'dependencies_merge': self._merge_dependencies
        }
        
        # Validation functions
        self.validation_functions = {
            'validate_parameters': self._validate_parameters,
            'validate_components': self._validate_components,
            'validate_configuration': self._validate_configuration
        }
        
        self.logger.info("TemplateInheritanceManager initialized")
    
    def resolve_inheritance(self, template_id: str, 
                          custom_rules: Optional[List[InheritanceRule]] = None) -> BaseTemplate:
        """
        Resolve inheritance for a template, creating a fully resolved template
        """
        try:
            template = self.registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Create inheritance context
            context = InheritanceContext(
                template_id=template_id,
                inheritance_rules=custom_rules or self.default_rules.copy()
            )
            
            # Resolve inheritance chain
            resolved_template = self._resolve_template_inheritance(template, context)
            
            # Validate resolved template
            if not self._validate_resolved_template(resolved_template, context):
                raise ValueError(f"Resolved template {template_id} failed validation")
            
            self.logger.info(f"Successfully resolved inheritance for {template_id}")
            return resolved_template
            
        except Exception as e:
            self.logger.error(f"Failed to resolve inheritance for {template_id}: {e}")
            raise
    
    def _resolve_template_inheritance(self, template: BaseTemplate, 
                                    context: InheritanceContext) -> BaseTemplate:
        """Resolve inheritance for a single template"""
        
        # Check for circular inheritance
        if template.metadata.template_id in context.parent_chain:
            raise ValueError(f"Circular inheritance detected: {context.parent_chain}")
        
        context.parent_chain.append(template.metadata.template_id)
        
        # Start with current template as base
        resolved_template = copy.deepcopy(template)
        
        # Process parent templates
        for parent_id in template.metadata.parent_templates:
            parent_template = self.registry.get_template(parent_id)
            if not parent_template:
                self.logger.warning(f"Parent template {parent_id} not found")
                continue
            
            # Recursively resolve parent
            parent_context = copy.deepcopy(context)
            resolved_parent = self._resolve_template_inheritance(parent_template, parent_context)
            
            # Merge parent into resolved template
            resolved_template = self._merge_templates(resolved_parent, resolved_template, context)
        
        return resolved_template
    
    def _merge_templates(self, parent: BaseTemplate, child: BaseTemplate, 
                        context: InheritanceContext) -> BaseTemplate:
        """Merge parent template into child template"""
        
        merged = copy.deepcopy(child)
        
        # Merge metadata
        merged.metadata = self._merge_metadata(parent.metadata, child.metadata, context)
        
        # Merge configuration
        merged.configuration = self._apply_inheritance_rules(
            parent.configuration, child.configuration, "configuration", context
        )
        
        # Merge parameters
        merged.parameters = self._apply_inheritance_rules(
            parent.parameters, child.parameters, "parameters", context
        )
        
        # Merge components
        merged.components = self._apply_inheritance_rules(
            parent.components, child.components, "components", context
        )
        
        return merged
    
    def _apply_inheritance_rules(self, parent_data: Dict[str, Any], 
                               child_data: Dict[str, Any], 
                               field_type: str,
                               context: InheritanceContext) -> Dict[str, Any]:
        """Apply inheritance rules to merge data structures"""
        
        # Find applicable rules
        applicable_rules = [
            rule for rule in context.inheritance_rules
            if rule.field_path.startswith(field_type)
        ]
        
        if not applicable_rules:
            # Use default merge strategy
            return self._merge_deep(parent_data, child_data, ConflictResolution.CHILD_WINS)
        
        result = copy.deepcopy(child_data)
        
        # Apply specific rules
        for rule in applicable_rules:
            field_path_parts = rule.field_path.split('.')[1:]  # Remove field_type prefix
            
            if not field_path_parts:  # Rule applies to entire field
                result = self._apply_single_rule(parent_data, result, rule, context)
            else:
                # Apply rule to specific path
                result = self._apply_rule_to_path(parent_data, result, field_path_parts, rule, context)
        
        return result
    
    def _apply_single_rule(self, parent_data: Any, child_data: Any, 
                          rule: InheritanceRule, context: InheritanceContext) -> Any:
        """Apply inheritance rule to entire data structure"""
        
        if rule.strategy == InheritanceStrategy.OVERRIDE:
            return child_data if child_data is not None else parent_data
        
        elif rule.strategy == InheritanceStrategy.MERGE:
            if rule.merge_function and rule.merge_function in self.merge_functions:
                return self.merge_functions[rule.merge_function](parent_data, child_data)
            else:
                return self._merge_deep(parent_data, child_data, rule.conflict_resolution)
        
        elif rule.strategy == InheritanceStrategy.EXTEND:
            return self._extend_data(parent_data, child_data)
        
        elif rule.strategy == InheritanceStrategy.COMPOSITE:
            return self._create_composite(parent_data, child_data)
        
        return child_data
    
    def _apply_rule_to_path(self, parent_data: Dict[str, Any], child_data: Dict[str, Any],
                           path_parts: List[str], rule: InheritanceRule,
                           context: InheritanceContext) -> Dict[str, Any]:
        """Apply inheritance rule to specific path in data structure"""
        
        result = copy.deepcopy(child_data)
        
        # Navigate to the target path
        parent_value = self._get_nested_value(parent_data, path_parts)
        child_value = self._get_nested_value(child_data, path_parts)
        
        if parent_value is not None:
            merged_value = self._apply_single_rule(parent_value, child_value, rule, context)
            self._set_nested_value(result, path_parts, merged_value)
        
        return result
    
    def _merge_deep(self, parent: Any, child: Any, 
                   conflict_resolution: ConflictResolution) -> Any:
        """Deep merge two data structures"""
        
        if child is None:
            return parent
        if parent is None:
            return child
        
        if isinstance(parent, dict) and isinstance(child, dict):
            result = copy.deepcopy(parent)
            
            for key, child_value in child.items():
                if key in result:
                    if conflict_resolution == ConflictResolution.CHILD_WINS:
                        result[key] = child_value
                    elif conflict_resolution == ConflictResolution.PARENT_WINS:
                        pass  # Keep parent value
                    elif conflict_resolution == ConflictResolution.MERGE_DEEP:
                        result[key] = self._merge_deep(result[key], child_value, conflict_resolution)
                    else:  # RAISE_ERROR
                        raise ValueError(f"Conflict at key '{key}': parent={result[key]}, child={child_value}")
                else:
                    result[key] = child_value
            
            return result
        
        elif isinstance(parent, list) and isinstance(child, list):
            if conflict_resolution == ConflictResolution.CHILD_WINS:
                return child
            elif conflict_resolution == ConflictResolution.PARENT_WINS:
                return parent
            elif conflict_resolution == ConflictResolution.MERGE_DEEP:
                return parent + [item for item in child if item not in parent]
            else:
                raise ValueError(f"List conflict: parent={parent}, child={child}")
        
        else:
            # Scalar values
            if conflict_resolution == ConflictResolution.CHILD_WINS:
                return child
            elif conflict_resolution == ConflictResolution.PARENT_WINS:
                return parent
            else:
                raise ValueError(f"Value conflict: parent={parent}, child={child}")
    
    def _extend_data(self, parent: Any, child: Any) -> Any:
        """Extend parent data with child data"""
        if isinstance(parent, list) and isinstance(child, list):
            return parent + child
        elif isinstance(parent, dict) and isinstance(child, dict):
            result = copy.deepcopy(parent)
            result.update(child)
            return result
        else:
            return child if child is not None else parent
    
    def _create_composite(self, parent: Any, child: Any) -> Dict[str, Any]:
        """Create composite structure from parent and child"""
        return {
            'parent': parent,
            'child': child,
            'type': 'composite'
        }
    
    def _get_nested_value(self, data: Dict[str, Any], path_parts: List[str]) -> Any:
        """Get value from nested dictionary path"""
        current = data
        for part in path_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
    
    def _set_nested_value(self, data: Dict[str, Any], path_parts: List[str], value: Any):
        """Set value in nested dictionary path"""
        current = data
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path_parts[-1]] = value
    
    def _merge_metadata(self, parent_metadata, child_metadata, context: InheritanceContext):
        """Merge template metadata"""
        merged = copy.deepcopy(child_metadata)
        
        # Merge tags
        parent_tags = set(parent_metadata.tags)
        child_tags = set(child_metadata.tags)
        merged.tags = list(parent_tags.union(child_tags))
        
        # Merge dependencies
        parent_deps = set(parent_metadata.dependencies)
        child_deps = set(child_metadata.dependencies)
        merged.dependencies = list(parent_deps.union(child_deps))
        
        # Update parent templates list
        if parent_metadata.template_id not in merged.parent_templates:
            merged.parent_templates.append(parent_metadata.template_id)
        
        return merged
    
    def _create_default_rules(self) -> List[InheritanceRule]:
        """Create default inheritance rules"""
        return [
            # Parameters: merge with child winning conflicts
            InheritanceRule(
                field_path="parameters",
                strategy=InheritanceStrategy.MERGE,
                conflict_resolution=ConflictResolution.CHILD_WINS,
                merge_function="parameters_merge"
            ),
            
            # Components: merge with child winning conflicts
            InheritanceRule(
                field_path="components",
                strategy=InheritanceStrategy.MERGE,
                conflict_resolution=ConflictResolution.CHILD_WINS,
                merge_function="components_merge"
            ),
            
            # Configuration: child overrides parent
            InheritanceRule(
                field_path="configuration",
                strategy=InheritanceStrategy.OVERRIDE,
                conflict_resolution=ConflictResolution.CHILD_WINS,
                merge_function="configuration_merge"
            )
        ]
    
    def _merge_parameters(self, parent_params: Dict[str, Any], 
                         child_params: Dict[str, Any]) -> Dict[str, Any]:
        """Custom merge function for parameters"""
        return self._merge_deep(parent_params, child_params, ConflictResolution.CHILD_WINS)
    
    def _merge_components(self, parent_components: Dict[str, Any], 
                         child_components: Dict[str, Any]) -> Dict[str, Any]:
        """Custom merge function for components"""
        return self._merge_deep(parent_components, child_components, ConflictResolution.CHILD_WINS)
    
    def _merge_configuration(self, parent_config: Dict[str, Any], 
                           child_config: Dict[str, Any]) -> Dict[str, Any]:
        """Custom merge function for configuration"""
        return self._merge_deep(parent_config, child_config, ConflictResolution.CHILD_WINS)
    
    def _merge_tags(self, parent_tags: List[str], child_tags: List[str]) -> List[str]:
        """Custom merge function for tags"""
        return list(set(parent_tags + child_tags))
    
    def _merge_dependencies(self, parent_deps: List[str], child_deps: List[str]) -> List[str]:
        """Custom merge function for dependencies"""
        return list(set(parent_deps + child_deps))
    
    def _validate_resolved_template(self, template: BaseTemplate, 
                                  context: InheritanceContext) -> bool:
        """Validate resolved template"""
        try:
            # Run validation functions
            for rule in context.inheritance_rules:
                if rule.validation_function and rule.validation_function in self.validation_functions:
                    if not self.validation_functions[rule.validation_function](template):
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Template validation failed: {e}")
            return False
    
    def _validate_parameters(self, template: BaseTemplate) -> bool:
        """Validate template parameters"""
        # Add custom parameter validation logic
        return True
    
    def _validate_components(self, template: BaseTemplate) -> bool:
        """Validate template components"""
        # Add custom component validation logic
        return True
    
    def _validate_configuration(self, template: BaseTemplate) -> bool:
        """Validate template configuration"""
        # Add custom configuration validation logic
        return True
    
    def get_inheritance_chain(self, template_id: str) -> List[str]:
        """Get the complete inheritance chain for a template"""
        template = self.registry.get_template(template_id)
        if not template:
            return []
        
        chain = [template_id]
        for parent_id in template.metadata.parent_templates:
            parent_chain = self.get_inheritance_chain(parent_id)
            chain.extend(parent_chain)
        
        return chain
    
    def analyze_inheritance_conflicts(self, template_id: str) -> Dict[str, Any]:
        """Analyze potential inheritance conflicts"""
        conflicts = {
            'circular_dependencies': [],
            'parameter_conflicts': [],
            'component_conflicts': [],
            'dependency_conflicts': []
        }
        
        try:
            # Check for circular dependencies
            visited = set()
            self._check_circular_inheritance(template_id, visited, [])
            
            # Analyze parameter conflicts
            template = self.registry.get_template(template_id)
            if template:
                conflicts['parameter_conflicts'] = self._find_parameter_conflicts(template)
                conflicts['component_conflicts'] = self._find_component_conflicts(template)
        
        except Exception as e:
            self.logger.error(f"Failed to analyze inheritance conflicts: {e}")
        
        return conflicts
    
    def _check_circular_inheritance(self, template_id: str, visited: Set[str], path: List[str]):
        """Check for circular inheritance"""
        if template_id in visited:
            raise ValueError(f"Circular inheritance detected: {' -> '.join(path + [template_id])}")
        
        visited.add(template_id)
        path.append(template_id)
        
        template = self.registry.get_template(template_id)
        if template:
            for parent_id in template.metadata.parent_templates:
                self._check_circular_inheritance(parent_id, visited.copy(), path.copy())
    
    def _find_parameter_conflicts(self, template: BaseTemplate) -> List[Dict[str, Any]]:
        """Find parameter conflicts in inheritance chain"""
        conflicts = []
        
        for parent_id in template.metadata.parent_templates:
            parent = self.registry.get_template(parent_id)
            if parent:
                for param_key in template.parameters:
                    if param_key in parent.parameters:
                        if template.parameters[param_key] != parent.parameters[param_key]:
                            conflicts.append({
                                'parameter': param_key,
                                'parent_template': parent_id,
                                'parent_value': parent.parameters[param_key],
                                'child_value': template.parameters[param_key]
                            })
        
        return conflicts
    
    def _find_component_conflicts(self, template: BaseTemplate) -> List[Dict[str, Any]]:
        """Find component conflicts in inheritance chain"""
        conflicts = []
        
        for parent_id in template.metadata.parent_templates:
            parent = self.registry.get_template(parent_id)
            if parent:
                for comp_key in template.components:
                    if comp_key in parent.components:
                        if template.components[comp_key] != parent.components[comp_key]:
                            conflicts.append({
                                'component': comp_key,
                                'parent_template': parent_id,
                                'parent_value': parent.components[comp_key],
                                'child_value': template.components[comp_key]
                            })
        
        return conflicts
