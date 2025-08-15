"""
Template-Based Testing Framework
===============================

Advanced testing framework that uses the hybrid template system
for comprehensive, inheritance-aware test case generation and execution.

Author: Pro Quant Desk Trader
"""

from .template_test_framework import (
    TemplateTestFramework, TemplateTestConfig, TemplateTestResult,
    TestExecutionMode, TestSeverity, TemplateTestSuite
)

from .inheritance_test_manager import (
    InheritanceTestManager, InheritanceTestConfig, InheritanceTestResult,
    InheritanceTestType
)

from .category_test_validator import (
    CategoryTestValidator, CategoryTestConfig, ValidationLevel
)

from .template_test_generator import (
    TemplateTestGenerator, TestGenerationConfig, TestPattern
)

from .performance_test_analyzer import (
    PerformanceTestAnalyzer, PerformanceTestConfig, PerformanceMetric
)

__all__ = [
    'TemplateTestFramework',
    'TemplateTestConfig', 
    'TemplateTestResult',
    'TestExecutionMode',
    'TestSeverity',
    'TemplateTestSuite',
    'InheritanceTestManager',
    'InheritanceTestConfig',
    'InheritanceTestResult',
    'InheritanceTestType',
    'CategoryTestValidator',
    'CategoryTestConfig',
    'ValidationLevel',
    'TemplateTestGenerator',
    'TestGenerationConfig',
    'TestPattern',
    'PerformanceTestAnalyzer',
    'PerformanceTestConfig',
    'PerformanceMetric'
]
