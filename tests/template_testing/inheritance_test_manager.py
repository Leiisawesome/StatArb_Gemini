"""
Inheritance Test Manager
=======================

Specialized testing for template inheritance chains, conflict resolution,
and cross-category inheritance validation.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from enum import Enum

from strategy_templates.base import (
    TemplateRegistry, BaseTemplate, TemplateCategory, 
    TemplateInheritanceManager, TemplateType
)
from .template_test_framework import TemplateTestResult, TestSeverity

logger = logging.getLogger(__name__)

class InheritanceTestType(Enum):
    """Types of inheritance tests"""
    CHAIN_VALIDATION = "chain_validation"
    CONFLICT_RESOLUTION = "conflict_resolution"
    DEPTH_ANALYSIS = "depth_analysis"
    CIRCULAR_DETECTION = "circular_detection"
    CATEGORY_CONSISTENCY = "category_consistency"
    PARAMETER_INHERITANCE = "parameter_inheritance"
    COMPONENT_INHERITANCE = "component_inheritance"

@dataclass
class InheritanceTestConfig:
    """Configuration for inheritance testing"""
    # Test scope
    test_types: List[InheritanceTestType] = field(default_factory=lambda: list(InheritanceTestType))
    max_inheritance_depth: int = 10
    enable_circular_detection: bool = True
    enable_conflict_analysis: bool = True
    
    # Validation settings
    strict_category_validation: bool = True
    allow_cross_category_inheritance: bool = False
    validate_parameter_types: bool = True
    
    # Performance settings
    inheritance_resolution_timeout_ms: int = 5000
    max_concurrent_inheritance_tests: int = 3

@dataclass
class InheritanceTestResult:
    """Result of inheritance testing"""
    test_id: str
    template_id: str
    test_type: InheritanceTestType
    start_time: datetime
    end_time: datetime
    
    # Test outcome
    success: bool
    execution_time_ms: float
    
    # Inheritance analysis
    inheritance_chain: List[str] = field(default_factory=list)
    inheritance_depth: int = 0
    circular_references: List[List[str]] = field(default_factory=list)
    
    # Conflict analysis
    parameter_conflicts: Dict[str, List[str]] = field(default_factory=dict)
    component_conflicts: Dict[str, List[str]] = field(default_factory=dict)
    resolution_strategy: Dict[str, str] = field(default_factory=dict)
    
    # Category validation
    category_violations: List[str] = field(default_factory=list)
    cross_category_inheritance: List[Tuple[str, TemplateCategory, TemplateCategory]] = field(default_factory=list)
    
    # Performance metrics
    resolution_time_ms: float = 0.0
    memory_usage_estimate: float = 0.0
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Detailed results
    detailed_analysis: Dict[str, Any] = field(default_factory=dict)

class InheritanceTestManager:
    """
    Manages comprehensive testing of template inheritance behavior
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 inheritance_manager: TemplateInheritanceManager,
                 config: Optional[InheritanceTestConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.inheritance_manager = inheritance_manager
        self.config = config or InheritanceTestConfig()
        
        # Test state
        self.test_results: List[InheritanceTestResult] = []
        self.inheritance_cache: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("InheritanceTestManager initialized")
    
    async def run_comprehensive_inheritance_test(self, template_id: str) -> List[InheritanceTestResult]:
        """Run comprehensive inheritance tests for a template"""
        
        self.logger.info(f"Running comprehensive inheritance tests for {template_id}")
        
        results = []
        
        # Run each configured test type
        for test_type in self.config.test_types:
            try:
                result = await self._run_inheritance_test(template_id, test_type)
                results.append(result)
                self.test_results.append(result)
            except Exception as e:
                self.logger.error(f"Inheritance test {test_type.value} failed for {template_id}: {e}")
        
        return results
    
    async def _run_inheritance_test(self, template_id: str, test_type: InheritanceTestType) -> InheritanceTestResult:
        """Run specific inheritance test"""
        
        start_time = datetime.now()
        test_id = f"{template_id}_{test_type.value}_{start_time.strftime('%H%M%S')}"
        
        result = InheritanceTestResult(
            test_id=test_id,
            template_id=template_id,
            test_type=test_type,
            start_time=start_time,
            end_time=start_time,
            success=False,
            execution_time_ms=0.0
        )
        
        try:
            if test_type == InheritanceTestType.CHAIN_VALIDATION:
                await self._test_inheritance_chain_validation(result)
            elif test_type == InheritanceTestType.CONFLICT_RESOLUTION:
                await self._test_conflict_resolution(result)
            elif test_type == InheritanceTestType.DEPTH_ANALYSIS:
                await self._test_inheritance_depth(result)
            elif test_type == InheritanceTestType.CIRCULAR_DETECTION:
                await self._test_circular_references(result)
            elif test_type == InheritanceTestType.CATEGORY_CONSISTENCY:
                await self._test_category_consistency(result)
            elif test_type == InheritanceTestType.PARAMETER_INHERITANCE:
                await self._test_parameter_inheritance(result)
            elif test_type == InheritanceTestType.COMPONENT_INHERITANCE:
                await self._test_component_inheritance(result)
            
            result.success = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"Test execution failed: {e}")
            result.success = False
        
        finally:
            result.end_time = datetime.now()
            result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    async def _test_inheritance_chain_validation(self, result: InheritanceTestResult):
        """Test inheritance chain validation"""
        
        template = self.template_registry.get_template(result.template_id)
        if not template:
            result.errors.append(f"Template {result.template_id} not found")
            return
        
        # Build inheritance chain
        chain = await self._build_inheritance_chain(result.template_id)
        result.inheritance_chain = chain
        result.inheritance_depth = len(chain) - 1  # Exclude the template itself
        
        # Validate each template in chain exists
        for parent_id in chain[1:]:  # Skip the template itself
            if not self.template_registry.get_template(parent_id):
                result.errors.append(f"Parent template {parent_id} not found in registry")
        
        # Check inheritance depth limits
        if result.inheritance_depth > self.config.max_inheritance_depth:
            result.warnings.append(
                f"Inheritance depth {result.inheritance_depth} exceeds limit {self.config.max_inheritance_depth}"
            )
        
        result.detailed_analysis['inheritance_chain_analysis'] = {
            'chain': chain,
            'depth': result.inheritance_depth,
            'valid_parents': len(chain) - 1 - len(result.errors)
        }
    
    async def _test_conflict_resolution(self, result: InheritanceTestResult):
        """Test inheritance conflict resolution"""
        
        template = self.template_registry.get_template(result.template_id)
        if not template:
            result.errors.append(f"Template {result.template_id} not found")
            return
        
        # Test parameter conflicts
        await self._analyze_parameter_conflicts(result, template)
        
        # Test component conflicts
        await self._analyze_component_conflicts(result, template)
        
        # Test inheritance resolution
        try:
            resolution_start = datetime.now()
            resolved_template = self.inheritance_manager.resolve_inheritance(result.template_id)
            resolution_time = (datetime.now() - resolution_start).total_seconds() * 1000
            result.resolution_time_ms = resolution_time
            
            if resolution_time > self.config.inheritance_resolution_timeout_ms:
                result.warnings.append(
                    f"Inheritance resolution took {resolution_time:.2f}ms, exceeds timeout {self.config.inheritance_resolution_timeout_ms}ms"
                )
            
            if resolved_template:
                result.detailed_analysis['resolved_template'] = {
                    'parameter_count': len(resolved_template.parameters),
                    'component_count': len(resolved_template.components),
                    'resolution_time_ms': resolution_time
                }
            else:
                result.errors.append("Inheritance resolution returned None")
                
        except Exception as e:
            result.errors.append(f"Inheritance resolution failed: {e}")
    
    async def _test_inheritance_depth(self, result: InheritanceTestResult):
        """Test inheritance depth analysis"""
        
        template = self.template_registry.get_template(result.template_id)
        if not template:
            result.errors.append(f"Template {result.template_id} not found")
            return
        
        # Calculate actual inheritance depth
        depth = await self._calculate_inheritance_depth(result.template_id)
        result.inheritance_depth = depth
        
        # Analyze depth impact on performance
        estimated_memory = depth * 1024  # Simplified estimation
        result.memory_usage_estimate = estimated_memory
        
        if depth > 5:
            result.warnings.append(f"Deep inheritance detected: {depth} levels")
        
        result.detailed_analysis['depth_analysis'] = {
            'calculated_depth': depth,
            'immediate_parents': len(template.metadata.parent_templates),
            'total_ancestors': depth,
            'memory_estimate_bytes': estimated_memory
        }
    
    async def _test_circular_references(self, result: InheritanceTestResult):
        """Test for circular inheritance references"""
        
        circular_refs = await self._detect_circular_references(result.template_id)
        result.circular_references = circular_refs
        
        if circular_refs:
            result.errors.append(f"Circular inheritance detected: {circular_refs}")
        
        result.detailed_analysis['circular_analysis'] = {
            'circular_references_found': len(circular_refs),
            'circular_paths': circular_refs
        }
    
    async def _test_category_consistency(self, result: InheritanceTestResult):
        """Test category consistency in inheritance chain"""
        
        template = self.template_registry.get_template(result.template_id)
        if not template:
            result.errors.append(f"Template {result.template_id} not found")
            return
        
        chain = await self._build_inheritance_chain(result.template_id)
        
        # Check category consistency
        for parent_id in chain[1:]:
            parent_template = self.template_registry.get_template(parent_id)
            if parent_template:
                # Check for cross-category inheritance
                if template.metadata.category != parent_template.metadata.category:
                    cross_cat = (parent_id, template.metadata.category, parent_template.metadata.category)
                    result.cross_category_inheritance.append(cross_cat)
                    
                    if not self.config.allow_cross_category_inheritance:
                        result.category_violations.append(
                            f"Cross-category inheritance: {template.metadata.category.value} inherits from {parent_template.metadata.category.value}"
                        )
        
        result.detailed_analysis['category_analysis'] = {
            'template_category': template.metadata.category.value,
            'cross_category_count': len(result.cross_category_inheritance),
            'violations': len(result.category_violations)
        }
    
    async def _test_parameter_inheritance(self, result: InheritanceTestResult):
        """Test parameter inheritance behavior"""
        
        template = self.template_registry.get_template(result.template_id)
        if not template:
            result.errors.append(f"Template {result.template_id} not found")
            return
        
        # Analyze parameter inheritance
        parameter_analysis = {}
        
        for param_name, param_value in template.parameters.items():
            # Check if parameter is inherited
            param_sources = []
            
            for parent_id in template.metadata.parent_templates:
                parent_template = self.template_registry.get_template(parent_id)
                if parent_template and param_name in parent_template.parameters:
                    param_sources.append({
                        'parent_id': parent_id,
                        'value': parent_template.parameters[param_name],
                        'matches_child': parent_template.parameters[param_name] == param_value
                    })
            
            parameter_analysis[param_name] = {
                'child_value': param_value,
                'inherited_from': param_sources,
                'is_overridden': any(not source['matches_child'] for source in param_sources)
            }
        
        result.detailed_analysis['parameter_inheritance'] = parameter_analysis
    
    async def _test_component_inheritance(self, result: InheritanceTestResult):
        """Test component inheritance behavior"""
        
        template = self.template_registry.get_template(result.template_id)
        if not template:
            result.errors.append(f"Template {result.template_id} not found")
            return
        
        # Analyze component inheritance
        component_analysis = {}
        
        for comp_name, comp_config in template.components.items():
            # Check if component is inherited
            comp_sources = []
            
            for parent_id in template.metadata.parent_templates:
                parent_template = self.template_registry.get_template(parent_id)
                if parent_template and comp_name in parent_template.components:
                    comp_sources.append({
                        'parent_id': parent_id,
                        'config': parent_template.components[comp_name],
                        'matches_child': parent_template.components[comp_name] == comp_config
                    })
            
            component_analysis[comp_name] = {
                'child_config': comp_config,
                'inherited_from': comp_sources,
                'is_overridden': any(not source['matches_child'] for source in comp_sources)
            }
        
        result.detailed_analysis['component_inheritance'] = component_analysis
    
    async def _analyze_parameter_conflicts(self, result: InheritanceTestResult, template: BaseTemplate):
        """Analyze parameter conflicts in inheritance"""
        
        for param_name in template.parameters:
            conflicts = []
            
            for parent_id in template.metadata.parent_templates:
                parent_template = self.template_registry.get_template(parent_id)
                if parent_template and param_name in parent_template.parameters:
                    if template.parameters[param_name] != parent_template.parameters[param_name]:
                        conflicts.append(f"Parent {parent_id}: {parent_template.parameters[param_name]} vs child: {template.parameters[param_name]}")
            
            if conflicts:
                result.parameter_conflicts[param_name] = conflicts
                result.resolution_strategy[param_name] = "child_wins"  # Default strategy
    
    async def _analyze_component_conflicts(self, result: InheritanceTestResult, template: BaseTemplate):
        """Analyze component conflicts in inheritance"""
        
        for comp_name in template.components:
            conflicts = []
            
            for parent_id in template.metadata.parent_templates:
                parent_template = self.template_registry.get_template(parent_id)
                if parent_template and comp_name in parent_template.components:
                    if template.components[comp_name] != parent_template.components[comp_name]:
                        conflicts.append(f"Parent {parent_id}: {parent_template.components[comp_name]} vs child: {template.components[comp_name]}")
            
            if conflicts:
                result.component_conflicts[comp_name] = conflicts
                result.resolution_strategy[comp_name] = "child_wins"  # Default strategy
    
    async def _build_inheritance_chain(self, template_id: str, visited: Optional[Set[str]] = None) -> List[str]:
        """Build complete inheritance chain for a template"""
        
        if visited is None:
            visited = set()
        
        if template_id in visited:
            return []  # Circular reference detected
        
        visited.add(template_id)
        chain = [template_id]
        
        template = self.template_registry.get_template(template_id)
        if template:
            for parent_id in template.metadata.parent_templates:
                parent_chain = await self._build_inheritance_chain(parent_id, visited.copy())
                chain.extend(parent_chain)
        
        return chain
    
    async def _calculate_inheritance_depth(self, template_id: str, visited: Optional[Set[str]] = None) -> int:
        """Calculate maximum inheritance depth"""
        
        if visited is None:
            visited = set()
        
        if template_id in visited:
            return 0  # Circular reference
        
        visited.add(template_id)
        
        template = self.template_registry.get_template(template_id)
        if not template or not template.metadata.parent_templates:
            return 0
        
        max_depth = 0
        for parent_id in template.metadata.parent_templates:
            parent_depth = await self._calculate_inheritance_depth(parent_id, visited.copy())
            max_depth = max(max_depth, parent_depth + 1)
        
        return max_depth
    
    async def _detect_circular_references(self, template_id: str, path: Optional[List[str]] = None) -> List[List[str]]:
        """Detect circular references in inheritance"""
        
        if path is None:
            path = []
        
        if template_id in path:
            # Circular reference found
            cycle_start = path.index(template_id)
            return [path[cycle_start:] + [template_id]]
        
        path.append(template_id)
        circular_refs = []
        
        template = self.template_registry.get_template(template_id)
        if template:
            for parent_id in template.metadata.parent_templates:
                parent_refs = await self._detect_circular_references(parent_id, path.copy())
                circular_refs.extend(parent_refs)
        
        return circular_refs
    
    def get_inheritance_test_summary(self) -> Dict[str, Any]:
        """Get comprehensive inheritance test summary"""
        
        if not self.test_results:
            return {'total_tests': 0, 'message': 'No inheritance tests executed'}
        
        successful_tests = [r for r in self.test_results if r.success]
        failed_tests = [r for r in self.test_results if not r.success]
        
        # Aggregate statistics
        total_conflicts = sum(len(r.parameter_conflicts) + len(r.component_conflicts) for r in self.test_results)
        total_circular_refs = sum(len(r.circular_references) for r in self.test_results)
        total_category_violations = sum(len(r.category_violations) for r in self.test_results)
        avg_inheritance_depth = sum(r.inheritance_depth for r in self.test_results) / len(self.test_results)
        
        return {
            'total_tests': len(self.test_results),
            'successful_tests': len(successful_tests),
            'failed_tests': len(failed_tests),
            'success_rate': len(successful_tests) / len(self.test_results),
            'avg_execution_time_ms': sum(r.execution_time_ms for r in self.test_results) / len(self.test_results),
            'inheritance_statistics': {
                'avg_inheritance_depth': avg_inheritance_depth,
                'max_inheritance_depth': max(r.inheritance_depth for r in self.test_results),
                'total_conflicts_detected': total_conflicts,
                'circular_references_found': total_circular_refs,
                'category_violations': total_category_violations,
                'avg_resolution_time_ms': sum(r.resolution_time_ms for r in self.test_results if r.resolution_time_ms > 0) / max(1, len([r for r in self.test_results if r.resolution_time_ms > 0]))
            },
            'test_type_distribution': {
                test_type.value: len([r for r in self.test_results if r.test_type == test_type])
                for test_type in InheritanceTestType
            }
        }
