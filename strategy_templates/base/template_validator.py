"""
Template Validator
=================

Comprehensive validation system for strategy templates ensuring
correctness, consistency, and performance compliance.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
from enum import Enum
import re

from .template_registry import BaseTemplate, TemplateType, TemplateCategory, TemplateStatus

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation strictness levels"""
    BASIC = "basic"           # Basic structure validation
    STANDARD = "standard"     # Standard business rules
    STRICT = "strict"         # Strict compliance validation
    ENTERPRISE = "enterprise" # Enterprise-grade validation

class ValidationSeverity(Enum):
    """Validation issue severity"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationIssue:
    """Individual validation issue"""
    severity: ValidationSeverity
    category: str
    message: str
    field_path: str
    suggested_fix: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Result of template validation"""
    template_id: str
    validation_timestamp: datetime
    validation_level: ValidationLevel
    overall_score: float  # 0.0 to 100.0
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues by severity level"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues"""
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.issues)
    
    def has_errors(self) -> bool:
        """Check if there are errors"""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

class TemplateValidator:
    """
    Comprehensive template validation system with configurable rules,
    business logic validation, and performance compliance checking.
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.validation_level = validation_level
        
        # Validation rules registry
        self.validation_rules = {
            ValidationLevel.BASIC: self._get_basic_rules(),
            ValidationLevel.STANDARD: self._get_standard_rules(),
            ValidationLevel.STRICT: self._get_strict_rules(),
            ValidationLevel.ENTERPRISE: self._get_enterprise_rules()
        }
        
        # Custom validators
        self.custom_validators = {}
        
        # Validation weights for scoring
        self.severity_weights = {
            ValidationSeverity.CRITICAL: 50.0,
            ValidationSeverity.ERROR: 25.0,
            ValidationSeverity.WARNING: 10.0,
            ValidationSeverity.INFO: 5.0
        }
        
        self.logger.info(f"TemplateValidator initialized with {validation_level.value} level")
    
    def validate_template(self, template: BaseTemplate, 
                         custom_rules: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate a template according to configured rules
        """
        try:
            result = ValidationResult(
                template_id=template.metadata.template_id,
                validation_timestamp=datetime.now(),
                validation_level=self.validation_level,
                overall_score=0.0,
                passed=False
            )
            
            self.logger.info(f"Starting validation for template {template.metadata.template_id}")
            
            # Get applicable rules
            rules = self.validation_rules[self.validation_level].copy()
            if custom_rules:
                rules.extend(custom_rules)
            
            # Run validation rules
            for rule_name in rules:
                if hasattr(self, f"_validate_{rule_name}"):
                    validator = getattr(self, f"_validate_{rule_name}")
                    issues = validator(template)
                    result.issues.extend(issues)
                elif rule_name in self.custom_validators:
                    issues = self.custom_validators[rule_name](template)
                    result.issues.extend(issues)
                else:
                    self.logger.warning(f"Validation rule '{rule_name}' not found")
            
            # Calculate score and pass/fail
            result.overall_score = self._calculate_validation_score(result.issues)
            result.passed = self._determine_pass_status(result)
            
            # Add metadata
            result.metadata = {
                'rules_applied': rules,
                'total_issues': len(result.issues),
                'critical_issues': len(result.get_issues_by_severity(ValidationSeverity.CRITICAL)),
                'error_issues': len(result.get_issues_by_severity(ValidationSeverity.ERROR)),
                'warning_issues': len(result.get_issues_by_severity(ValidationSeverity.WARNING)),
                'info_issues': len(result.get_issues_by_severity(ValidationSeverity.INFO))
            }
            
            self.logger.info(f"Validation completed for {template.metadata.template_id}: "
                           f"Score {result.overall_score:.1f}, Passed: {result.passed}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Validation failed for {template.metadata.template_id}: {e}")
            return ValidationResult(
                template_id=template.metadata.template_id,
                validation_timestamp=datetime.now(),
                validation_level=self.validation_level,
                overall_score=0.0,
                passed=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="validation_error",
                    message=f"Validation process failed: {e}",
                    field_path="validation",
                    suggested_fix="Check template structure and validation configuration"
                )]
            )
    
    def register_custom_validator(self, name: str, validator: Callable[[BaseTemplate], List[ValidationIssue]]):
        """Register custom validation function"""
        self.custom_validators[name] = validator
        self.logger.info(f"Registered custom validator: {name}")
    
    def _get_basic_rules(self) -> List[str]:
        """Get basic validation rules"""
        return [
            "metadata_structure",
            "required_fields",
            "data_types"
        ]
    
    def _get_standard_rules(self) -> List[str]:
        """Get standard validation rules"""
        basic_rules = self._get_basic_rules()
        return basic_rules + [
            "parameter_validation",
            "component_validation",
            "configuration_validation",
            "naming_conventions",
            "dependency_validation"
        ]
    
    def _get_strict_rules(self) -> List[str]:
        """Get strict validation rules"""
        standard_rules = self._get_standard_rules()
        return standard_rules + [
            "business_logic_validation",
            "performance_validation",
            "security_validation",
            "version_compatibility"
        ]
    
    def _get_enterprise_rules(self) -> List[str]:
        """Get enterprise validation rules"""
        strict_rules = self._get_strict_rules()
        return strict_rules + [
            "compliance_validation",
            "audit_trail_validation",
            "documentation_validation",
            "testing_validation",
            "deployment_validation"
        ]
    
    def _validate_metadata_structure(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate metadata structure"""
        issues = []
        
        if not template.metadata:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="metadata",
                message="Template metadata is missing",
                field_path="metadata",
                suggested_fix="Add complete metadata section"
            ))
            return issues
        
        # Check metadata fields
        required_metadata_fields = [
            'template_id', 'name', 'version', 'category', 
            'template_type', 'status', 'description', 'author'
        ]
        
        for field in required_metadata_fields:
            if not hasattr(template.metadata, field) or getattr(template.metadata, field) is None:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="metadata",
                    message=f"Required metadata field '{field}' is missing",
                    field_path=f"metadata.{field}",
                    suggested_fix=f"Add {field} to template metadata"
                ))
        
        return issues
    
    def _validate_required_fields(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate required template fields"""
        issues = []
        
        # Check top-level required fields
        if not template.configuration:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="structure",
                message="Configuration section is empty",
                field_path="configuration",
                suggested_fix="Add configuration parameters"
            ))
        
        if not template.parameters:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="structure", 
                message="Parameters section is empty",
                field_path="parameters",
                suggested_fix="Add strategy parameters"
            ))
        
        if not template.components:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="structure",
                message="Components section is empty",
                field_path="components",
                suggested_fix="Add strategy components if applicable"
            ))
        
        return issues
    
    def _validate_data_types(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate data types"""
        issues = []
        
        # Validate metadata types
        if template.metadata:
            if not isinstance(template.metadata.template_id, str):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="data_types",
                    message="template_id must be a string",
                    field_path="metadata.template_id",
                    suggested_fix="Ensure template_id is a string"
                ))
            
            if not isinstance(template.metadata.tags, list):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="data_types",
                    message="tags must be a list",
                    field_path="metadata.tags",
                    suggested_fix="Convert tags to list format"
                ))
        
        # Validate configuration types
        if template.configuration and not isinstance(template.configuration, dict):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="data_types",
                message="configuration must be a dictionary",
                field_path="configuration",
                suggested_fix="Ensure configuration is a dictionary"
            ))
        
        # Validate parameters types
        if template.parameters and not isinstance(template.parameters, dict):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="data_types",
                message="parameters must be a dictionary",
                field_path="parameters",
                suggested_fix="Ensure parameters is a dictionary"
            ))
        
        return issues
    
    def _validate_parameter_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate parameter definitions and values"""
        issues = []
        
        if not template.parameters:
            return issues
        
        for param_name, param_value in template.parameters.items():
            # Check parameter naming
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', param_name):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="parameters",
                    message=f"Parameter name '{param_name}' doesn't follow naming convention",
                    field_path=f"parameters.{param_name}",
                    suggested_fix="Use alphanumeric characters and underscores only"
                ))
            
            # Check for reasonable numeric ranges
            if isinstance(param_value, (int, float)):
                if abs(param_value) > 1e10:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="parameters",
                        message=f"Parameter '{param_name}' has very large value: {param_value}",
                        field_path=f"parameters.{param_name}",
                        suggested_fix="Verify parameter value is correct"
                    ))
        
        return issues
    
    def _validate_component_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate component definitions"""
        issues = []
        
        if not template.components:
            return issues
        
        # Validate component structure
        for comp_name, comp_config in template.components.items():
            if not isinstance(comp_config, dict):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="components",
                    message=f"Component '{comp_name}' must be a dictionary",
                    field_path=f"components.{comp_name}",
                    suggested_fix="Ensure component is defined as a dictionary"
                ))
                continue
            
            # Check for required component fields
            if 'type' not in comp_config:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="components",
                    message=f"Component '{comp_name}' missing type field",
                    field_path=f"components.{comp_name}.type",
                    suggested_fix="Add type field to component definition"
                ))
        
        return issues
    
    def _validate_configuration_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate configuration settings"""
        issues = []
        
        if not template.configuration:
            return issues
        
        # Check for common configuration issues
        if 'enabled' in template.configuration:
            if not isinstance(template.configuration['enabled'], bool):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="configuration",
                    message="'enabled' should be a boolean value",
                    field_path="configuration.enabled",
                    suggested_fix="Set enabled to true or false"
                ))
        
        return issues
    
    def _validate_naming_conventions(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate naming conventions"""
        issues = []
        
        # Validate template ID naming
        if template.metadata and template.metadata.template_id:
            template_id = template.metadata.template_id
            if not re.match(r'^[a-z][a-z0-9_]*$', template_id):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="naming",
                    message="template_id should use lowercase letters, numbers, and underscores",
                    field_path="metadata.template_id",
                    suggested_fix="Use lowercase naming convention"
                ))
        
        return issues
    
    def _validate_dependency_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate dependencies"""
        issues = []
        
        if template.metadata and template.metadata.dependencies:
            for dep in template.metadata.dependencies:
                if not isinstance(dep, str):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="dependencies",
                        message=f"Dependency must be a string: {dep}",
                        field_path="metadata.dependencies",
                        suggested_fix="Ensure all dependencies are strings"
                    ))
        
        return issues
    
    def _validate_business_logic_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate business logic constraints"""
        issues = []
        
        # Add business-specific validation logic here
        # For example, risk limits, position sizing rules, etc.
        
        return issues
    
    def _validate_performance_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate performance requirements"""
        issues = []
        
        # Check for performance-related parameters
        if template.parameters:
            if 'max_positions' in template.parameters:
                max_pos = template.parameters['max_positions']
                if isinstance(max_pos, int) and max_pos > 1000:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="performance",
                        message=f"max_positions ({max_pos}) may impact performance",
                        field_path="parameters.max_positions",
                        suggested_fix="Consider reducing max_positions for better performance"
                    ))
        
        return issues
    
    def _validate_security_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate security requirements"""
        issues = []
        
        # Add security validation logic here
        # For example, check for hardcoded credentials, unsafe parameters, etc.
        
        return issues
    
    def _validate_version_compatibility(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate version compatibility"""
        issues = []
        
        # Add version compatibility checks here
        
        return issues
    
    def _validate_compliance_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate regulatory compliance"""
        issues = []
        
        # Add compliance validation logic here
        
        return issues
    
    def _validate_audit_trail_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate audit trail requirements"""
        issues = []
        
        # Check for audit-related metadata
        if not template.metadata.created_at:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="audit",
                message="Missing creation timestamp",
                field_path="metadata.created_at",
                suggested_fix="Add creation timestamp for audit trail"
            ))
        
        return issues
    
    def _validate_documentation_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate documentation requirements"""
        issues = []
        
        if template.metadata:
            if not template.metadata.description or len(template.metadata.description) < 10:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="documentation",
                    message="Description is too short or missing",
                    field_path="metadata.description",
                    suggested_fix="Add detailed description (at least 10 characters)"
                ))
        
        return issues
    
    def _validate_testing_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate testing requirements"""
        issues = []
        
        # Add testing validation logic here
        
        return issues
    
    def _validate_deployment_validation(self, template: BaseTemplate) -> List[ValidationIssue]:
        """Validate deployment readiness"""
        issues = []
        
        # Check deployment status
        if template.metadata and template.metadata.status == TemplateStatus.PRODUCTION:
            if not template.metadata.validation_results:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="deployment",
                    message="Production template missing validation results",
                    field_path="metadata.validation_results",
                    suggested_fix="Run validation before marking as production"
                ))
        
        return issues
    
    def _calculate_validation_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate overall validation score"""
        if not issues:
            return 100.0
        
        total_deduction = 0.0
        for issue in issues:
            total_deduction += self.severity_weights[issue.severity]
        
        # Score is 100 minus deductions, minimum 0
        score = max(0.0, 100.0 - total_deduction)
        return score
    
    def _determine_pass_status(self, result: ValidationResult) -> bool:
        """Determine if validation passes"""
        # Fail if critical issues
        if result.has_critical_issues():
            return False
        
        # Fail if score too low
        min_scores = {
            ValidationLevel.BASIC: 50.0,
            ValidationLevel.STANDARD: 70.0,
            ValidationLevel.STRICT: 80.0,
            ValidationLevel.ENTERPRISE: 90.0
        }
        
        return result.overall_score >= min_scores[self.validation_level]
    
    def generate_validation_report(self, result: ValidationResult) -> str:
        """Generate human-readable validation report"""
        report = []
        report.append(f"Validation Report for Template: {result.template_id}")
        report.append(f"Validation Level: {result.validation_level.value}")
        report.append(f"Validation Date: {result.validation_timestamp.isoformat()}")
        report.append(f"Overall Score: {result.overall_score:.1f}/100")
        report.append(f"Status: {'PASSED' if result.passed else 'FAILED'}")
        report.append("")
        
        if result.issues:
            report.append("Issues Found:")
            report.append("-" * 40)
            
            for severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR, 
                           ValidationSeverity.WARNING, ValidationSeverity.INFO]:
                severity_issues = result.get_issues_by_severity(severity)
                if severity_issues:
                    report.append(f"\n{severity.value.upper()} ({len(severity_issues)}):")
                    for issue in severity_issues:
                        report.append(f"  • {issue.message}")
                        if issue.suggested_fix:
                            report.append(f"    → Suggested fix: {issue.suggested_fix}")
        else:
            report.append("No issues found!")
        
        return "\n".join(report)
