"""
Academic Strategy Validator - Production Suitability Assessment
================================================================

Validates academic strategies for production deployment, ensuring they meet
industry standards for risk management, execution, and performance.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import numpy as np

from .academic_strategy_registry import AcademicTemplate, ResearchField


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Categories of validation checks"""
    TEMPLATE_STRUCTURE = "template_structure"
    ACADEMIC_METADATA = "academic_metadata"
    STATISTICAL_SIGNIFICANCE = "statistical_significance"
    PRODUCTION_CONSTRAINTS = "production_constraints"
    RISK_MANAGEMENT = "risk_management"
    EXECUTION_VIABILITY = "execution_viability"
    PERFORMANCE_RELIABILITY = "performance_reliability"
    ROBUSTNESS = "robustness"


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation result for academic strategy"""
    is_valid: bool = False
    overall_score: float = 0.0
    issues: List[ValidationIssue] = field(default_factory=list)
    category_scores: Dict[ValidationCategory, float] = field(default_factory=dict)
    
    # Detailed results
    production_readiness_score: float = 0.0
    academic_quality_score: float = 0.0
    risk_assessment_score: float = 0.0
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    required_modifications: List[str] = field(default_factory=list)
    
    def add_issue(self, category: ValidationCategory, severity: ValidationSeverity, 
                  message: str, details: Optional[Dict[str, Any]] = None, suggestion: Optional[str] = None):
        """Add validation issue"""
        self.issues.append(ValidationIssue(category, severity, message, details, suggestion))
    
    def add_error(self, message: str, category: ValidationCategory = ValidationCategory.TEMPLATE_STRUCTURE):
        """Add error issue"""
        self.add_issue(category, ValidationSeverity.ERROR, message)
    
    def add_warning(self, message: str, category: ValidationCategory = ValidationCategory.PRODUCTION_CONSTRAINTS):
        """Add warning issue"""
        self.add_issue(category, ValidationSeverity.WARNING, message)
    
    def add_info(self, message: str, category: ValidationCategory = ValidationCategory.TEMPLATE_STRUCTURE):
        """Add info issue"""
        self.add_issue(category, ValidationSeverity.INFO, message)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues by severity level"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_issues_by_category(self, category: ValidationCategory) -> List[ValidationIssue]:
        """Get issues by category"""
        return [issue for issue in self.issues if issue.category == category]
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues"""
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.issues)
    
    def has_errors(self) -> bool:
        """Check if there are errors"""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)


class AcademicStrategyValidator:
    """
    Comprehensive validator for academic strategies to assess production suitability
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Production constraints
        self.production_constraints = {
            'max_position_size': 0.25,
            'max_daily_loss': 0.05,
            'commission_rate': 0.001,
            'min_liquidity': 1000000,
            'max_slippage': 0.002,
            'min_sharpe_ratio': 0.5,
            'max_drawdown': 0.20,
            'min_trade_frequency': 1,  # trades per month
            'max_trade_frequency': 1000,  # trades per month
            'min_holding_period': 1,  # days
            'max_leverage': 3.0
        }
        
        # Statistical significance thresholds
        self.significance_thresholds = {
            'min_t_statistic': 2.0,
            'max_p_value': 0.05,
            'min_observations': 100,
            'min_out_of_sample_period': 0.2,  # 20% of total sample
            'required_robustness_checks': ['bootstrap', 'monte_carlo']
        }
        
        # Academic quality requirements
        self.academic_requirements = {
            'required_metadata_fields': [
                'authors', 'institution', 'publication', 'abstract', 'key_contributions'
            ],
            'required_validation_fields': [
                'performance_metrics', 'statistical_significance'
            ],
            'min_abstract_length': 100,
            'min_contributions': 1
        }
        
        self.logger.info("Academic Strategy Validator initialized")
    
    def validate_academic_strategy(self, academic_template: AcademicTemplate, 
                                 custom_constraints: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Comprehensive validation of academic strategy for production deployment
        """
        try:
            self.logger.info(f"Validating academic strategy: {academic_template.template_id}")
            
            result = ValidationResult()
            
            # Apply custom constraints if provided
            constraints = self.production_constraints.copy()
            if custom_constraints:
                constraints.update(custom_constraints)
            
            # 1. Template Structure Validation
            structure_score = self._validate_template_structure(academic_template, result)
            result.category_scores[ValidationCategory.TEMPLATE_STRUCTURE] = structure_score
            
            # 2. Academic Metadata Validation
            metadata_score = self._validate_academic_metadata(academic_template, result)
            result.category_scores[ValidationCategory.ACADEMIC_METADATA] = metadata_score
            
            # 3. Statistical Significance Validation
            significance_score = self._validate_statistical_significance(academic_template, result)
            result.category_scores[ValidationCategory.STATISTICAL_SIGNIFICANCE] = significance_score
            
            # 4. Production Constraints Validation
            constraints_score = self._validate_production_constraints(academic_template, result, constraints)
            result.category_scores[ValidationCategory.PRODUCTION_CONSTRAINTS] = constraints_score
            
            # 5. Risk Management Validation
            risk_score = self._validate_risk_management(academic_template, result)
            result.category_scores[ValidationCategory.RISK_MANAGEMENT] = risk_score
            
            # 6. Execution Viability Validation
            execution_score = self._validate_execution_viability(academic_template, result)
            result.category_scores[ValidationCategory.EXECUTION_VIABILITY] = execution_score
            
            # 7. Performance Reliability Validation
            performance_score = self._validate_performance_reliability(academic_template, result)
            result.category_scores[ValidationCategory.PERFORMANCE_RELIABILITY] = performance_score
            
            # 8. Robustness Validation
            robustness_score = self._validate_robustness(academic_template, result)
            result.category_scores[ValidationCategory.ROBUSTNESS] = robustness_score
            
            # Calculate overall scores
            result.academic_quality_score = np.mean([metadata_score, significance_score, robustness_score])
            result.production_readiness_score = np.mean([constraints_score, risk_score, execution_score])
            result.risk_assessment_score = np.mean([risk_score, performance_score])
            
            # Calculate overall validation score
            all_scores = list(result.category_scores.values())
            result.overall_score = np.mean(all_scores) if all_scores else 0.0
            
            # Determine if strategy is valid
            result.is_valid = (
                not result.has_critical_issues() and 
                not result.has_errors() and
                result.overall_score >= 0.6
            )
            
            # Generate recommendations
            self._generate_recommendations(result)
            
            self.logger.info(f"Validation completed. Overall score: {result.overall_score:.2f}, Valid: {result.is_valid}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            result = ValidationResult()
            result.add_issue(
                ValidationCategory.TEMPLATE_STRUCTURE,
                ValidationSeverity.CRITICAL,
                f"Validation process failed: {str(e)}"
            )
            return result
    
    def _validate_template_structure(self, template: AcademicTemplate, result: ValidationResult) -> float:
        """Validate basic template structure"""
        score = 1.0
        
        # Check if base template exists
        if not template.base_template:
            result.add_error("Missing base template", ValidationCategory.TEMPLATE_STRUCTURE)
            score -= 0.5
        
        # Check required template fields
        required_fields = ['template_id', 'template_name', 'template_type', 'base_parameters']
        for field in required_fields:
            if field not in template.base_template:
                result.add_error(f"Missing required field: {field}", ValidationCategory.TEMPLATE_STRUCTURE)
                score -= 0.1
        
        # Check base parameters structure
        base_params = template.base_template.get('base_parameters', {})
        if not isinstance(base_params, dict):
            result.add_error("Invalid base_parameters structure", ValidationCategory.TEMPLATE_STRUCTURE)
            score -= 0.2
        
        return max(0.0, score)
    
    def _validate_academic_metadata(self, template: AcademicTemplate, result: ValidationResult) -> float:
        """Validate academic metadata completeness and quality"""
        score = 1.0
        metadata = template.academic_metadata
        
        # Check required fields
        for field in self.academic_requirements['required_metadata_fields']:
            if not hasattr(metadata, field) or not getattr(metadata, field):
                result.add_error(f"Missing required metadata field: {field}", ValidationCategory.ACADEMIC_METADATA)
                score -= 0.15
        
        # Check abstract length
        if len(metadata.abstract) < self.academic_requirements['min_abstract_length']:
            result.add_warning(
                f"Abstract too short ({len(metadata.abstract)} chars, minimum {self.academic_requirements['min_abstract_length']})",
                ValidationCategory.ACADEMIC_METADATA
            )
            score -= 0.1
        
        # Check key contributions
        if len(metadata.key_contributions) < self.academic_requirements['min_contributions']:
            result.add_warning("Insufficient key contributions listed", ValidationCategory.ACADEMIC_METADATA)
            score -= 0.1
        
        # Check DOI or ArXiv ID for credibility
        if not metadata.doi and not metadata.arxiv_id:
            result.add_info("No DOI or ArXiv ID provided", ValidationCategory.ACADEMIC_METADATA)
            score -= 0.05
        
        return max(0.0, score)
    
    def _validate_statistical_significance(self, template: AcademicTemplate, result: ValidationResult) -> float:
        """Validate statistical significance of results"""
        score = 1.0
        validation = template.academic_validation
        
        # Check t-statistics
        t_stats = validation.t_statistics
        if t_stats:
            for metric, t_stat in t_stats.items():
                if abs(t_stat) < self.significance_thresholds['min_t_statistic']:
                    result.add_warning(
                        f"Low t-statistic for {metric}: {t_stat:.2f}",
                        ValidationCategory.STATISTICAL_SIGNIFICANCE
                    )
                    score -= 0.1
        else:
            result.add_warning("No t-statistics provided", ValidationCategory.STATISTICAL_SIGNIFICANCE)
            score -= 0.2
        
        # Check p-values
        p_values = validation.p_values
        if p_values:
            for metric, p_val in p_values.items():
                if p_val > self.significance_thresholds['max_p_value']:
                    result.add_warning(
                        f"High p-value for {metric}: {p_val:.3f}",
                        ValidationCategory.STATISTICAL_SIGNIFICANCE
                    )
                    score -= 0.1
        else:
            result.add_warning("No p-values provided", ValidationCategory.STATISTICAL_SIGNIFICANCE)
            score -= 0.2
        
        # Check out-of-sample validation
        if not validation.out_of_sample_period:
            result.add_error("No out-of-sample period specified", ValidationCategory.STATISTICAL_SIGNIFICANCE)
            score -= 0.3
        
        return max(0.0, score)
    
    def _validate_production_constraints(self, template: AcademicTemplate, result: ValidationResult, 
                                       constraints: Dict[str, Any]) -> float:
        """Validate against production constraints"""
        score = 1.0
        base_params = template.base_template.get('base_parameters', {})
        
        # Check position sizing
        risk_mgmt = base_params.get('risk_management', {})
        if risk_mgmt:
            position_sizing = risk_mgmt.get('position_sizing', {})
            max_position = position_sizing.get('max_position_size', 1.0)
            
            if max_position > constraints['max_position_size']:
                result.add_warning(
                    f"Position size {max_position:.2%} exceeds limit {constraints['max_position_size']:.2%}",
                    ValidationCategory.PRODUCTION_CONSTRAINTS
                )
                score -= 0.2
        
        # Check performance constraints
        performance = template.academic_validation.performance_metrics
        if performance:
            sharpe_ratio = performance.get('sharpe_ratio', 0)
            if sharpe_ratio < constraints['min_sharpe_ratio']:
                result.add_warning(
                    f"Sharpe ratio {sharpe_ratio:.2f} below minimum {constraints['min_sharpe_ratio']:.2f}",
                    ValidationCategory.PRODUCTION_CONSTRAINTS
                )
                score -= 0.2
            
            max_drawdown = performance.get('max_drawdown', 1.0)
            if max_drawdown > constraints['max_drawdown']:
                result.add_warning(
                    f"Max drawdown {max_drawdown:.2%} exceeds limit {constraints['max_drawdown']:.2%}",
                    ValidationCategory.PRODUCTION_CONSTRAINTS
                )
                score -= 0.2
        
        return max(0.0, score)
    
    def _validate_risk_management(self, template: AcademicTemplate, result: ValidationResult) -> float:
        """Validate risk management components"""
        score = 1.0
        base_params = template.base_template.get('base_parameters', {})
        
        # Check if risk management exists
        if 'risk_management' not in base_params:
            result.add_error("No risk management parameters specified", ValidationCategory.RISK_MANAGEMENT)
            score -= 0.5
        else:
            risk_mgmt = base_params['risk_management']
            
            # Check stop-loss mechanisms
            if 'stop_loss' not in risk_mgmt and 'max_loss' not in risk_mgmt:
                result.add_warning("No stop-loss mechanism specified", ValidationCategory.RISK_MANAGEMENT)
                score -= 0.2
            
            # Check position sizing rules
            if 'position_sizing' not in risk_mgmt:
                result.add_warning("No position sizing rules specified", ValidationCategory.RISK_MANAGEMENT)
                score -= 0.2
        
        return max(0.0, score)
    
    def _validate_execution_viability(self, template: AcademicTemplate, result: ValidationResult) -> float:
        """Validate execution viability in production"""
        score = 1.0
        base_params = template.base_template.get('base_parameters', {})
        
        # Check execution parameters
        if 'execution' not in base_params:
            result.add_warning("No execution parameters specified", ValidationCategory.EXECUTION_VIABILITY)
            score -= 0.3
        
        # Check for transaction cost considerations
        execution_params = base_params.get('execution', {})
        if 'commission_rate' not in execution_params and 'transaction_costs' not in execution_params:
            result.add_warning("No transaction cost considerations", ValidationCategory.EXECUTION_VIABILITY)
            score -= 0.2
        
        return max(0.0, score)
    
    def _validate_performance_reliability(self, template: AcademicTemplate, result: ValidationResult) -> float:
        """Validate performance reliability and consistency"""
        score = 1.0
        validation = template.academic_validation
        
        # Check if performance metrics exist
        if not validation.performance_metrics:
            result.add_error("No performance metrics provided", ValidationCategory.PERFORMANCE_RELIABILITY)
            score -= 0.5
        
        # Check for risk metrics
        if not validation.risk_metrics:
            result.add_warning("No risk metrics provided", ValidationCategory.PERFORMANCE_RELIABILITY)
            score -= 0.2
        
        return max(0.0, score)
    
    def _validate_robustness(self, template: AcademicTemplate, result: ValidationResult) -> float:
        """Validate robustness of results"""
        score = 1.0
        validation = template.academic_validation
        
        # Check robustness checks
        required_checks = self.significance_thresholds['required_robustness_checks']
        performed_checks = validation.robustness_checks
        
        for check in required_checks:
            if check not in performed_checks:
                result.add_warning(f"Missing robustness check: {check}", ValidationCategory.ROBUSTNESS)
                score -= 0.2
        
        # Check bootstrap results
        if not validation.bootstrap_results:
            result.add_info("No bootstrap results provided", ValidationCategory.ROBUSTNESS)
            score -= 0.1
        
        # Check sensitivity analysis
        if not validation.sensitivity_analysis:
            result.add_info("No sensitivity analysis provided", ValidationCategory.ROBUSTNESS)
            score -= 0.1
        
        return max(0.0, score)
    
    def _generate_recommendations(self, result: ValidationResult):
        """Generate recommendations based on validation results"""
        # Performance recommendations
        if result.category_scores.get(ValidationCategory.STATISTICAL_SIGNIFICANCE, 1.0) < 0.7:
            result.recommendations.append("Improve statistical significance with larger sample size or better methodology")
        
        if result.category_scores.get(ValidationCategory.PRODUCTION_CONSTRAINTS, 1.0) < 0.7:
            result.recommendations.append("Adjust strategy parameters to meet production constraints")
        
        if result.category_scores.get(ValidationCategory.RISK_MANAGEMENT, 1.0) < 0.7:
            result.recommendations.append("Enhance risk management framework with stop-losses and position sizing")
        
        if result.category_scores.get(ValidationCategory.ROBUSTNESS, 1.0) < 0.7:
            result.recommendations.append("Conduct additional robustness checks including bootstrap and sensitivity analysis")
        
        # Required modifications for critical issues
        critical_issues = result.get_issues_by_severity(ValidationSeverity.CRITICAL)
        for issue in critical_issues:
            result.required_modifications.append(f"Critical: {issue.message}")
        
        error_issues = result.get_issues_by_severity(ValidationSeverity.ERROR)
        for issue in error_issues:
            result.required_modifications.append(f"Required: {issue.message}")
    
    def get_validation_summary(self, result: ValidationResult) -> Dict[str, Any]:
        """Get comprehensive validation summary"""
        return {
            'overall_assessment': {
                'is_valid': result.is_valid,
                'overall_score': result.overall_score,
                'production_readiness_score': result.production_readiness_score,
                'academic_quality_score': result.academic_quality_score,
                'risk_assessment_score': result.risk_assessment_score
            },
            'category_scores': {cat.value: score for cat, score in result.category_scores.items()},
            'issues_summary': {
                'critical': len(result.get_issues_by_severity(ValidationSeverity.CRITICAL)),
                'errors': len(result.get_issues_by_severity(ValidationSeverity.ERROR)),
                'warnings': len(result.get_issues_by_severity(ValidationSeverity.WARNING)),
                'info': len(result.get_issues_by_severity(ValidationSeverity.INFO))
            },
            'recommendations': result.recommendations,
            'required_modifications': result.required_modifications,
            'detailed_issues': [
                {
                    'category': issue.category.value,
                    'severity': issue.severity.value,
                    'message': issue.message,
                    'details': issue.details,
                    'suggestion': issue.suggestion
                }
                for issue in result.issues
            ]
        }
