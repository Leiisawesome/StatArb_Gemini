"""
Academic Research Integration Module
====================================

Complete academic research integration system for converting academic strategies
into production-ready trading systems with proper validation and enhancement.

Phase 4 Week 26-27 Implementation:
- Academic Strategy Registry: Comprehensive academic template management
- Academic Strategy Validator: Production suitability assessment  
- Research-to-Production Pipeline: Complete conversion workflow
- Academic Strategy Enhancer: Production enhancement framework

Author: Pro Quant Desk Trader
"""

# Academic Strategy Registry
from .academic_strategy_registry import (
    AcademicStrategyRegistry, AcademicTemplate, AcademicMetadata, AcademicValidation,
    ResearchField, PublicationStatus
)

# Academic Strategy Validator
from .academic_strategy_validator import (
    AcademicStrategyValidator, ValidationResult, ValidationIssue,
    ValidationSeverity, ValidationCategory
)

# Research-to-Production Pipeline
from .research_to_production_pipeline import (
    ResearchToProductionPipeline, ProductionEvaluation, ProductionConstraints,
    ProductionEnhancement, ProductionConstraintApplicator
)

# Academic Strategy Enhancer
from .academic_strategy_enhancer import (
    AcademicStrategyEnhancer, EnhancementRecord, EnhancementSummary,
    EnhancementType
)

# Academic-Industry Collaboration (Week 28-29)
from .academic_industry_collaboration import (
    AcademicIndustryCollaboration, ResearchPartnership, StrategySubmission,
    PartnershipTerms, PartnershipType, PartnershipStatus, DataSharingLevel,
    SubmissionStatus
)

# Academic Strategy Repository (Week 28-29)
from .academic_strategy_repository import (
    AcademicStrategyRepository, SearchFilters, SearchResult, RepositoryStatistics,
    SortCriteria, PerformanceMetric
)

# Research-to-Production Testing (Week 30-31)
from .academic_strategy_testing_framework import (
    AcademicStrategyTestingFramework, TestResult, TestSuite, ProductionTestConfiguration,
    TestType, TestSeverity, TestStatus
)

from .research_production_pipeline_tester import (
    ResearchProductionPipelineTester, PipelineTestResult, PipelineStageResult,
    PipelineTestConfiguration, PipelineStage, PipelineTestType, PipelineTestStatus
)

from .academic_strategy_search_tester import (
    AcademicStrategySearchTester, SearchTestResult, SearchTestSuite,
    SearchTestConfiguration, SearchTestType, SearchTestStatus
)

__all__ = [
    # Academic Strategy Registry
    'AcademicStrategyRegistry',
    'AcademicTemplate', 
    'AcademicMetadata',
    'AcademicValidation',
    'ResearchField',
    'PublicationStatus',
    
    # Academic Strategy Validator
    'AcademicStrategyValidator',
    'ValidationResult',
    'ValidationIssue',
    'ValidationSeverity',
    'ValidationCategory',
    
    # Research-to-Production Pipeline
    'ResearchToProductionPipeline',
    'ProductionEvaluation',
    'ProductionConstraints',
    'ProductionEnhancement',
    'ProductionConstraintApplicator',
    
    # Academic Strategy Enhancer
    'AcademicStrategyEnhancer',
    'EnhancementRecord',
    'EnhancementSummary',
    'EnhancementType',
    
    # Academic-Industry Collaboration (Week 28-29)
    'AcademicIndustryCollaboration',
    'ResearchPartnership',
    'StrategySubmission',
    'PartnershipTerms',
    'PartnershipType',
    'PartnershipStatus', 
    'DataSharingLevel',
    'SubmissionStatus',
    
    # Academic Strategy Repository (Week 28-29)
    'AcademicStrategyRepository',
    'SearchFilters',
    'SearchResult',
    'RepositoryStatistics',
    'SortCriteria',
    'PerformanceMetric',
    
    # Research-to-Production Testing (Week 30-31)
    'AcademicStrategyTestingFramework',
    'TestResult',
    'TestSuite',
    'ProductionTestConfiguration',
    'TestType',
    'TestSeverity',
    'TestStatus',
    'ResearchProductionPipelineTester',
    'PipelineTestResult',
    'PipelineStageResult',
    'PipelineTestConfiguration',
    'PipelineStage',
    'PipelineTestType',
    'PipelineTestStatus',
    'AcademicStrategySearchTester',
    'SearchTestResult',
    'SearchTestSuite',
    'SearchTestConfiguration',
    'SearchTestType',
    'SearchTestStatus'
]
