"""
Category Test Validator
======================

Validates template behavior and compliance within each category
(BASE, SPECIFIC, COMPOSITE) with category-specific rules and requirements.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum

from strategy_templates.base import (
    TemplateRegistry, BaseTemplate, TemplateCategory, TemplateType, TemplateStatus
)

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation severity levels"""
    STRICT = "strict"
    STANDARD = "standard"
    PERMISSIVE = "permissive"

class CategoryRequirement(Enum):
    """Category-specific requirements"""
    PARAMETER_COUNT = "parameter_count"
    COMPONENT_COUNT = "component_count"
    INHERITANCE_DEPTH = "inheritance_depth"
    PERFORMANCE_THRESHOLD = "performance_threshold"
    COMPLEXITY_SCORE = "complexity_score"
    VALIDATION_RULES = "validation_rules"

@dataclass
class CategoryTestConfig:
    """Configuration for category testing"""
    # Validation settings
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    enable_performance_validation: bool = True
    enable_complexity_analysis: bool = True
    enable_compliance_checking: bool = True
    
    # Category-specific thresholds
    base_category_limits: Dict[str, Any] = field(default_factory=lambda: {
        'max_parameters': 10,
        'max_components': 5,
        'max_inheritance_depth': 0,
        'min_performance_score': 0.6,
        'max_complexity_score': 50
    })
    
    specific_category_limits: Dict[str, Any] = field(default_factory=lambda: {
        'max_parameters': 20,
        'max_components': 8,
        'max_inheritance_depth': 3,
        'min_performance_score': 0.7,
        'max_complexity_score': 100
    })
    
    composite_category_limits: Dict[str, Any] = field(default_factory=lambda: {
        'max_parameters': 50,
        'max_components': 15,
        'max_inheritance_depth': 5,
        'min_performance_score': 0.8,
        'max_complexity_score': 200
    })
    
    # Required components by category
    required_components: Dict[TemplateCategory, List[str]] = field(default_factory=lambda: {
        TemplateCategory.BASE: ['signal_generator'],
        TemplateCategory.SPECIFIC: ['signal_generator', 'risk_manager'],
        TemplateCategory.COMPOSITE: ['signal_generator', 'risk_manager', 'execution_engine', 'portfolio_manager']
    })

@dataclass
class CategoryValidationResult:
    """Result of category validation"""
    template_id: str
    category: TemplateCategory
    validation_level: ValidationLevel
    start_time: datetime
    end_time: datetime
    
    # Validation outcome
    is_compliant: bool
    compliance_score: float  # 0.0 to 1.0
    
    # Category metrics
    parameter_count: int = 0
    component_count: int = 0
    inheritance_depth: int = 0
    complexity_score: float = 0.0
    performance_score: float = 0.0
    
    # Compliance violations
    parameter_violations: List[str] = field(default_factory=list)
    component_violations: List[str] = field(default_factory=list)
    inheritance_violations: List[str] = field(default_factory=list)
    performance_violations: List[str] = field(default_factory=list)
    structural_violations: List[str] = field(default_factory=list)
    
    # Recommendations
    improvement_suggestions: List[str] = field(default_factory=list)
    optimization_opportunities: List[str] = field(default_factory=list)
    
    # Category-specific analysis
    category_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class CategoryTestValidator:
    """
    Validates templates against category-specific requirements and best practices
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 config: Optional[CategoryTestConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or CategoryTestConfig()
        
        # Validation state
        self.validation_results: List[CategoryValidationResult] = []
        self.category_statistics: Dict[TemplateCategory, Dict[str, Any]] = {}
        
        self.logger.info("CategoryTestValidator initialized")
    
    async def validate_template_category_compliance(self, template_id: str) -> CategoryValidationResult:
        """Validate a template's compliance with its category requirements"""
        
        start_time = datetime.now()
        
        template = self.template_registry.get_template(template_id)
        if not template:
            return CategoryValidationResult(
                template_id=template_id,
                category=TemplateCategory.BASE,
                validation_level=self.config.validation_level,
                start_time=start_time,
                end_time=datetime.now(),
                is_compliant=False,
                compliance_score=0.0,
                errors=[f"Template {template_id} not found"]
            )
        
        result = CategoryValidationResult(
            template_id=template_id,
            category=template.metadata.category,
            validation_level=self.config.validation_level,
            start_time=start_time,
            end_time=start_time,
            is_compliant=False,
            compliance_score=0.0
        )
        
        try:
            # Calculate basic metrics
            result.parameter_count = len(template.parameters)
            result.component_count = len(template.components)
            result.inheritance_depth = len(template.metadata.parent_templates)
            
            # Calculate complexity score
            result.complexity_score = await self._calculate_complexity_score(template)
            
            # Run category-specific validation
            await self._validate_category_requirements(result, template)
            
            # Check component requirements
            await self._validate_component_requirements(result, template)
            
            # Validate parameter structure
            await self._validate_parameter_structure(result, template)
            
            # Analyze inheritance compliance
            await self._validate_inheritance_compliance(result, template)
            
            # Calculate compliance score
            result.compliance_score = await self._calculate_compliance_score(result)
            result.is_compliant = result.compliance_score >= 0.8  # 80% compliance threshold
            
            # Generate recommendations
            await self._generate_recommendations(result, template)
            
            # Category-specific analysis
            await self._perform_category_analysis(result, template)
            
        except Exception as e:
            result.errors.append(f"Validation failed: {e}")
            result.is_compliant = False
            result.compliance_score = 0.0
        
        finally:
            result.end_time = datetime.now()
        
        self.validation_results.append(result)
        return result
    
    async def validate_category_batch(self, category: TemplateCategory) -> List[CategoryValidationResult]:
        """Validate all templates in a category"""
        
        self.logger.info(f"Validating all templates in category {category.value}")
        
        results = []
        
        # Get all templates in category
        for template_id in self.template_registry.templates.keys():
            template = self.template_registry.get_template(template_id)
            if template and template.metadata.category == category:
                result = await self.validate_template_category_compliance(template_id)
                results.append(result)
        
        # Update category statistics
        await self._update_category_statistics(category, results)
        
        self.logger.info(f"Category validation completed: {len(results)} templates in {category.value}")
        return results
    
    async def _validate_category_requirements(self, result: CategoryValidationResult, template: BaseTemplate):
        """Validate category-specific requirements"""
        
        category = template.metadata.category
        limits = self._get_category_limits(category)
        
        # Check parameter count
        if result.parameter_count > limits['max_parameters']:
            result.parameter_violations.append(
                f"Parameter count {result.parameter_count} exceeds limit {limits['max_parameters']} for {category.value}"
            )
        
        # Check component count
        if result.component_count > limits['max_components']:
            result.component_violations.append(
                f"Component count {result.component_count} exceeds limit {limits['max_components']} for {category.value}"
            )
        
        # Check inheritance depth
        if result.inheritance_depth > limits['max_inheritance_depth']:
            result.inheritance_violations.append(
                f"Inheritance depth {result.inheritance_depth} exceeds limit {limits['max_inheritance_depth']} for {category.value}"
            )
        
        # Check complexity score
        if result.complexity_score > limits['max_complexity_score']:
            result.structural_violations.append(
                f"Complexity score {result.complexity_score:.1f} exceeds limit {limits['max_complexity_score']} for {category.value}"
            )
    
    async def _validate_component_requirements(self, result: CategoryValidationResult, template: BaseTemplate):
        """Validate required components for category"""
        
        category = template.metadata.category
        required_components = self.config.required_components.get(category, [])
        
        for required_comp in required_components:
            if required_comp not in template.components:
                result.component_violations.append(
                    f"Required component '{required_comp}' missing for {category.value} category"
                )
        
        # Check component configuration quality
        for comp_name, comp_config in template.components.items():
            if not isinstance(comp_config, dict):
                result.component_violations.append(
                    f"Component '{comp_name}' has invalid configuration format"
                )
            elif 'type' not in comp_config:
                result.component_violations.append(
                    f"Component '{comp_name}' missing required 'type' field"
                )
    
    async def _validate_parameter_structure(self, result: CategoryValidationResult, template: BaseTemplate):
        """Validate parameter structure and types"""
        
        category = template.metadata.category
        
        # Category-specific parameter validation
        if category == TemplateCategory.BASE:
            await self._validate_base_parameters(result, template)
        elif category == TemplateCategory.SPECIFIC:
            await self._validate_specific_parameters(result, template)
        elif category == TemplateCategory.COMPOSITE:
            await self._validate_composite_parameters(result, template)
    
    async def _validate_base_parameters(self, result: CategoryValidationResult, template: BaseTemplate):
        """Validate BASE category parameters"""
        
        # BASE templates should have simple, fundamental parameters
        expected_params = ['lookback_period', 'signal_threshold']
        
        for param in expected_params:
            if param not in template.parameters:
                result.parameter_violations.append(
                    f"BASE template missing fundamental parameter: {param}"
                )
        
        # Check for overly complex parameters
        complex_params = ['ensemble_weights', 'factor_loadings', 'regime_parameters']
        for param in complex_params:
            if param in template.parameters:
                result.warnings.append(
                    f"BASE template has complex parameter '{param}' - consider SPECIFIC or COMPOSITE category"
                )
    
    async def _validate_specific_parameters(self, result: CategoryValidationResult, template: BaseTemplate):
        """Validate SPECIFIC category parameters"""
        
        # SPECIFIC templates should have specialized parameters
        if 'position_size' not in template.parameters:
            result.parameter_violations.append(
                "SPECIFIC template missing 'position_size' parameter"
            )
        
        # Check for inheritance from BASE
        if not template.metadata.parent_templates:
            result.warnings.append(
                "SPECIFIC template should typically inherit from BASE template"
            )
    
    async def _validate_composite_parameters(self, result: CategoryValidationResult, template: BaseTemplate):
        """Validate COMPOSITE category parameters"""
        
        # COMPOSITE templates should have comprehensive parameters
        expected_params = ['portfolio_weights', 'risk_limits', 'execution_params']
        
        for param in expected_params:
            if param not in template.parameters:
                result.parameter_violations.append(
                    f"COMPOSITE template missing advanced parameter: {param}"
                )
        
        # Should have inheritance chain
        if len(template.metadata.parent_templates) == 0:
            result.inheritance_violations.append(
                "COMPOSITE template should inherit from other templates"
            )
    
    async def _validate_inheritance_compliance(self, result: CategoryValidationResult, template: BaseTemplate):
        """Validate inheritance compliance for category"""
        
        category = template.metadata.category
        
        # Category-specific inheritance rules
        if category == TemplateCategory.BASE:
            if template.metadata.parent_templates:
                result.inheritance_violations.append(
                    "BASE templates should not inherit from other templates"
                )
        
        elif category == TemplateCategory.SPECIFIC:
            if len(template.metadata.parent_templates) > 1:
                result.warnings.append(
                    "SPECIFIC templates typically inherit from single BASE template"
                )
        
        elif category == TemplateCategory.COMPOSITE:
            if len(template.metadata.parent_templates) == 0:
                result.inheritance_violations.append(
                    "COMPOSITE templates should inherit from other templates"
                )
    
    async def _calculate_complexity_score(self, template: BaseTemplate) -> float:
        """Calculate template complexity score"""
        
        score = 0.0
        
        # Parameter complexity
        score += len(template.parameters) * 2
        
        # Component complexity
        score += len(template.components) * 5
        
        # Inheritance complexity
        score += len(template.metadata.parent_templates) * 10
        
        # Parameter value complexity (simplified)
        for param_value in template.parameters.values():
            if isinstance(param_value, (list, dict)):
                score += 5
            elif isinstance(param_value, str) and len(param_value) > 50:
                score += 2
        
        # Component configuration complexity
        for comp_config in template.components.values():
            if isinstance(comp_config, dict):
                score += len(comp_config) * 2
                if 'params' in comp_config:
                    score += 5
        
        return score
    
    async def _calculate_compliance_score(self, result: CategoryValidationResult) -> float:
        """Calculate overall compliance score"""
        
        total_violations = (
            len(result.parameter_violations) +
            len(result.component_violations) +
            len(result.inheritance_violations) +
            len(result.performance_violations) +
            len(result.structural_violations)
        )
        
        # Base score starts at 1.0
        base_score = 1.0
        
        # Deduct points for violations
        violation_penalty = total_violations * 0.1
        compliance_score = max(0.0, base_score - violation_penalty)
        
        # Bonus for exceeding minimum requirements
        category_limits = self._get_category_limits(result.category)
        
        if result.parameter_count >= 1:  # Has parameters
            compliance_score += 0.05
        
        if result.component_count >= len(self.config.required_components.get(result.category, [])):
            compliance_score += 0.1
        
        return min(1.0, compliance_score)
    
    async def _generate_recommendations(self, result: CategoryValidationResult, template: BaseTemplate):
        """Generate improvement recommendations"""
        
        # Parameter recommendations
        if result.parameter_violations:
            result.improvement_suggestions.append(
                f"Review parameter structure for {result.category.value} category compliance"
            )
        
        # Component recommendations
        if result.component_violations:
            result.improvement_suggestions.append(
                "Add missing required components or fix component configurations"
            )
        
        # Complexity recommendations
        if result.complexity_score > self._get_category_limits(result.category)['max_complexity_score']:
            result.improvement_suggestions.append(
                "Consider simplifying template or moving to higher category"
            )
        
        # Inheritance recommendations
        if result.inheritance_violations:
            if result.category == TemplateCategory.SPECIFIC and not template.metadata.parent_templates:
                result.improvement_suggestions.append(
                    "Consider inheriting from a BASE template"
                )
            elif result.category == TemplateCategory.COMPOSITE and len(template.metadata.parent_templates) < 2:
                result.improvement_suggestions.append(
                    "Consider inheriting from multiple templates for better composition"
                )
        
        # Optimization opportunities
        if result.parameter_count < 5 and result.category == TemplateCategory.COMPOSITE:
            result.optimization_opportunities.append(
                "COMPOSITE template could benefit from more sophisticated parameters"
            )
        
        if result.component_count == len(self.config.required_components.get(result.category, [])):
            result.optimization_opportunities.append(
                "Consider adding optional components for enhanced functionality"
            )
    
    async def _perform_category_analysis(self, result: CategoryValidationResult, template: BaseTemplate):
        """Perform detailed category-specific analysis"""
        
        analysis = {
            'category_fitness': self._assess_category_fitness(template),
            'suggested_category': self._suggest_optimal_category(template),
            'complexity_distribution': {
                'parameter_complexity': len(template.parameters) * 2,
                'component_complexity': len(template.components) * 5,
                'inheritance_complexity': len(template.metadata.parent_templates) * 10
            },
            'compliance_breakdown': {
                'parameter_compliance': len(result.parameter_violations) == 0,
                'component_compliance': len(result.component_violations) == 0,
                'inheritance_compliance': len(result.inheritance_violations) == 0,
                'structural_compliance': len(result.structural_violations) == 0
            }
        }
        
        result.category_analysis = analysis
    
    def _assess_category_fitness(self, template: BaseTemplate) -> float:
        """Assess how well template fits its declared category"""
        
        category = template.metadata.category
        limits = self._get_category_limits(category)
        
        fitness_score = 1.0
        
        # Check if template exceeds category limits
        if len(template.parameters) > limits['max_parameters']:
            fitness_score -= 0.2
        
        if len(template.components) > limits['max_components']:
            fitness_score -= 0.2
        
        if len(template.metadata.parent_templates) > limits['max_inheritance_depth']:
            fitness_score -= 0.2
        
        return max(0.0, fitness_score)
    
    def _suggest_optimal_category(self, template: BaseTemplate) -> TemplateCategory:
        """Suggest optimal category for template based on its characteristics"""
        
        param_count = len(template.parameters)
        comp_count = len(template.components)
        inheritance_count = len(template.metadata.parent_templates)
        
        # Simple heuristic for category suggestion
        if param_count <= 10 and comp_count <= 5 and inheritance_count == 0:
            return TemplateCategory.BASE
        elif param_count <= 20 and comp_count <= 8 and inheritance_count <= 3:
            return TemplateCategory.SPECIFIC
        else:
            return TemplateCategory.COMPOSITE
    
    def _get_category_limits(self, category: TemplateCategory) -> Dict[str, Any]:
        """Get limits for specific category"""
        
        if category == TemplateCategory.BASE:
            return self.config.base_category_limits
        elif category == TemplateCategory.SPECIFIC:
            return self.config.specific_category_limits
        else:  # COMPOSITE
            return self.config.composite_category_limits
    
    async def _update_category_statistics(self, category: TemplateCategory, results: List[CategoryValidationResult]):
        """Update category-level statistics"""
        
        if not results:
            return
        
        compliant_templates = [r for r in results if r.is_compliant]
        
        stats = {
            'total_templates': len(results),
            'compliant_templates': len(compliant_templates),
            'compliance_rate': len(compliant_templates) / len(results),
            'avg_compliance_score': sum(r.compliance_score for r in results) / len(results),
            'avg_complexity_score': sum(r.complexity_score for r in results) / len(results),
            'common_violations': self._analyze_common_violations(results),
            'improvement_areas': self._identify_improvement_areas(results)
        }
        
        self.category_statistics[category] = stats
    
    def _analyze_common_violations(self, results: List[CategoryValidationResult]) -> Dict[str, int]:
        """Analyze most common violations across results"""
        
        violation_counts = {}
        
        for result in results:
            all_violations = (
                result.parameter_violations +
                result.component_violations +
                result.inheritance_violations +
                result.structural_violations
            )
            
            for violation in all_violations:
                violation_counts[violation] = violation_counts.get(violation, 0) + 1
        
        return dict(sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:5])
    
    def _identify_improvement_areas(self, results: List[CategoryValidationResult]) -> List[str]:
        """Identify top improvement areas for category"""
        
        improvement_areas = []
        
        param_violations = sum(len(r.parameter_violations) for r in results)
        comp_violations = sum(len(r.component_violations) for r in results)
        inheritance_violations = sum(len(r.inheritance_violations) for r in results)
        
        violations = [
            (param_violations, "Parameter structure optimization"),
            (comp_violations, "Component configuration improvement"),
            (inheritance_violations, "Inheritance design enhancement")
        ]
        
        violations.sort(key=lambda x: x[0], reverse=True)
        
        for count, area in violations[:3]:
            if count > 0:
                improvement_areas.append(f"{area} ({count} violations)")
        
        return improvement_areas
    
    def get_category_validation_summary(self) -> Dict[str, Any]:
        """Get comprehensive category validation summary"""
        
        if not self.validation_results:
            return {'total_validations': 0, 'message': 'No category validations executed'}
        
        summary = {
            'total_validations': len(self.validation_results),
            'overall_compliance_rate': sum(r.compliance_score for r in self.validation_results) / len(self.validation_results),
            'category_breakdown': {},
            'top_violations': self._analyze_common_violations(self.validation_results),
            'compliance_distribution': {
                'fully_compliant': len([r for r in self.validation_results if r.compliance_score >= 0.95]),
                'mostly_compliant': len([r for r in self.validation_results if 0.8 <= r.compliance_score < 0.95]),
                'partially_compliant': len([r for r in self.validation_results if 0.5 <= r.compliance_score < 0.8]),
                'non_compliant': len([r for r in self.validation_results if r.compliance_score < 0.5])
            }
        }
        
        # Category-specific breakdown
        for category in TemplateCategory:
            category_results = [r for r in self.validation_results if r.category == category]
            if category_results:
                summary['category_breakdown'][category.value] = {
                    'total_templates': len(category_results),
                    'avg_compliance_score': sum(r.compliance_score for r in category_results) / len(category_results),
                    'compliance_rate': len([r for r in category_results if r.is_compliant]) / len(category_results)
                }
        
        return summary
