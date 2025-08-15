"""
Base Template Infrastructure
===========================

Core template system providing foundational patterns and inheritance mechanisms.
"""

from .template_registry import (
    TemplateRegistry, BaseTemplate, TemplateMetadata,
    TemplateCategory, TemplateType, TemplateStatus
)
from .template_inheritance import TemplateInheritanceManager, InheritanceRule
from .strategy_assembler import StrategyAssembler, AssemblyContext
from .template_validator import TemplateValidator, ValidationResult, ValidationLevel

__all__ = [
    'TemplateRegistry',
    'BaseTemplate',
    'TemplateMetadata',
    'TemplateCategory',
    'TemplateType', 
    'TemplateStatus',
    'TemplateInheritanceManager',
    'InheritanceRule',
    'StrategyAssembler',
    'AssemblyContext',
    'TemplateValidator',
    'ValidationResult',
    'ValidationLevel'
]
