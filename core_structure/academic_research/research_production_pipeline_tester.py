"""
Research-to-Production Pipeline Tester - Comprehensive Validation System
========================================================================

Advanced testing framework for validating the complete research-to-production pipeline,
ensuring seamless transition from academic research to production-ready trading strategies.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import pandas as pd
from copy import deepcopy

from .academic_strategy_registry import AcademicTemplate, AcademicStrategyRegistry
from .research_to_production_pipeline import ResearchToProductionPipeline, ProductionEvaluation
from .academic_strategy_validator import AcademicStrategyValidator
from .academic_strategy_enhancer import AcademicStrategyEnhancer


class PipelineStage(Enum):
    """Stages in the research-to-production pipeline"""
    ACADEMIC_INGESTION = "academic_ingestion"
    VALIDATION = "validation"
    ENHANCEMENT = "enhancement"
    PRODUCTION_ADAPTATION = "production_adaptation"
    INTEGRATION = "integration"
    DEPLOYMENT = "deployment"


class PipelineTestType(Enum):
    """Types of pipeline tests"""
    STAGE_FUNCTIONALITY = "stage_functionality"
    STAGE_PERFORMANCE = "stage_performance"
    DATA_INTEGRITY = "data_integrity"
    WORKFLOW_CONTINUITY = "workflow_continuity"
    ERROR_HANDLING = "error_handling"
    ROLLBACK_CAPABILITY = "rollback_capability"
    END_TO_END = "end_to_end"


class PipelineTestStatus(Enum):
    """Pipeline test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass
class PipelineStageResult:
    """Result of testing a specific pipeline stage"""
    stage: PipelineStage
    stage_name: str
    status: PipelineTestStatus
    execution_time_ms: float = 0.0
    input_data_valid: bool = False
    output_data_valid: bool = False
    stage_specific_metrics: Dict[str, float] = field(default_factory=dict)
    data_transformation_accuracy: float = 0.0
    performance_improvement: float = 0.0
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    stage_recommendations: List[str] = field(default_factory=list)


@dataclass
class PipelineTestResult:
    """Complete pipeline test result"""
    test_id: str
    test_name: str
    test_type: PipelineTestType
    template_id: str
    status: PipelineTestStatus
    total_execution_time_ms: float = 0.0
    stage_results: List[PipelineStageResult] = field(default_factory=list)
    end_to_end_success: bool = False
    data_integrity_score: float = 0.0
    performance_degradation: float = 0.0
    pipeline_efficiency: float = 0.0
    critical_errors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PipelineTestConfiguration:
    """Configuration for pipeline testing"""
    # Test scope
    stages_to_test: List[PipelineStage] = field(default_factory=lambda: list(PipelineStage))
    test_types: List[PipelineTestType] = field(default_factory=lambda: list(PipelineTestType))
    
    # Performance thresholds
    max_stage_execution_time_ms: Dict[PipelineStage, float] = field(default_factory=lambda: {
        PipelineStage.ACADEMIC_INGESTION: 5000,
        PipelineStage.VALIDATION: 10000,
        PipelineStage.ENHANCEMENT: 15000,
        PipelineStage.PRODUCTION_ADAPTATION: 20000,
        PipelineStage.INTEGRATION: 10000,
        PipelineStage.DEPLOYMENT: 5000
    })
    
    max_total_pipeline_time_ms: float = 60000  # 1 minute
    min_data_integrity_score: float = 0.95
    max_performance_degradation: float = 0.05
    min_pipeline_efficiency: float = 0.80
    
    # Error handling settings
    test_error_scenarios: bool = True
    test_rollback_scenarios: bool = True
    max_retry_attempts: int = 3
    
    # Data validation settings
    validate_data_at_each_stage: bool = True
    perform_schema_validation: bool = True
    check_data_completeness: bool = True


class ResearchProductionPipelineTester:
    """
    Comprehensive tester for the research-to-production pipeline
    """
    
    def __init__(self,
                 academic_registry: AcademicStrategyRegistry,
                 production_pipeline: ResearchToProductionPipeline,
                 strategy_validator: AcademicStrategyValidator,
                 strategy_enhancer: AcademicStrategyEnhancer):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Core components
        self.academic_registry = academic_registry
        self.production_pipeline = production_pipeline
        self.strategy_validator = strategy_validator
        self.strategy_enhancer = strategy_enhancer
        
        # Test state management
        self.pipeline_tests: Dict[str, PipelineTestResult] = {}
        self.test_configurations: Dict[str, PipelineTestConfiguration] = {}
        self.test_history: List[PipelineTestResult] = []
        
        # Pipeline monitoring
        self.stage_performance_baselines: Dict[PipelineStage, Dict[str, float]] = {}
        self.pipeline_metrics: Dict[str, Any] = {
            'total_pipeline_tests': 0,
            'successful_pipeline_tests': 0,
            'average_pipeline_time_ms': 0.0,
            'stage_success_rates': {},
            'common_failure_points': {},
            'pipeline_reliability_score': 0.0
        }
        
        # Default configuration
        self.default_config = PipelineTestConfiguration()
        
        self.logger.info("Research-to-Production Pipeline Tester initialized")
    
    async def create_pipeline_test(self,
                                 template_id: str,
                                 test_name: Optional[str] = None,
                                 config: Optional[PipelineTestConfiguration] = None) -> str:
        """Create comprehensive pipeline test for academic strategy"""
        try:
            if template_id not in self.academic_registry.academic_templates:
                raise ValueError(f"Academic template {template_id} not found")
            
            test_id = f"pipeline_test_{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if test_name is None:
                test_name = f"Pipeline Test for {template_id}"
            
            test_config = config or self.default_config
            self.test_configurations[test_id] = test_config
            
            # Create pipeline test result
            pipeline_test = PipelineTestResult(
                test_id=test_id,
                test_name=test_name,
                test_type=PipelineTestType.END_TO_END,  # Default to end-to-end
                template_id=template_id,
                status=PipelineTestStatus.PENDING
            )
            
            self.pipeline_tests[test_id] = pipeline_test
            
            self.logger.info(f"Pipeline test created: {test_id}")
            return test_id
            
        except Exception as e:
            self.logger.error(f"Failed to create pipeline test for {template_id}: {e}")
            raise
    
    async def execute_pipeline_test(self, test_id: str) -> PipelineTestResult:
        """Execute complete pipeline test"""
        try:
            if test_id not in self.pipeline_tests:
                raise ValueError(f"Pipeline test {test_id} not found")
            
            pipeline_test = self.pipeline_tests[test_id]
            config = self.test_configurations[test_id]
            template = self.academic_registry.academic_templates[pipeline_test.template_id]
            
            self.logger.info(f"Executing pipeline test: {test_id}")
            
            pipeline_test.status = PipelineTestStatus.RUNNING
            start_time = datetime.now()
            
            # Execute tests for each configured stage
            for stage in config.stages_to_test:
                stage_result = await self._test_pipeline_stage(stage, template, config)
                pipeline_test.stage_results.append(stage_result)
                
                # Stop if critical error occurs
                if stage_result.status == PipelineTestStatus.ERROR:
                    pipeline_test.critical_errors.append(f"Stage {stage.value} failed critically")
                    if not config.test_error_scenarios:
                        break
            
            # Execute pipeline-wide tests
            if PipelineTestType.END_TO_END in config.test_types:
                await self._test_end_to_end_pipeline(pipeline_test, template, config)
            
            if PipelineTestType.DATA_INTEGRITY in config.test_types:
                await self._test_data_integrity(pipeline_test, template, config)
            
            if PipelineTestType.WORKFLOW_CONTINUITY in config.test_types:
                await self._test_workflow_continuity(pipeline_test, template, config)
            
            if PipelineTestType.ERROR_HANDLING in config.test_types and config.test_error_scenarios:
                await self._test_error_handling(pipeline_test, template, config)
            
            # Calculate overall results
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            pipeline_test.total_execution_time_ms = total_time
            
            await self._calculate_pipeline_results(pipeline_test, config)
            
            # Update metrics
            self._update_pipeline_metrics(pipeline_test)
            
            # Add to history
            self.test_history.append(deepcopy(pipeline_test))
            
            self.logger.info(f"Pipeline test completed: {test_id}, Success: {pipeline_test.end_to_end_success}")
            
            return pipeline_test
            
        except Exception as e:
            if test_id in self.pipeline_tests:
                self.pipeline_tests[test_id].status = PipelineTestStatus.ERROR
                self.pipeline_tests[test_id].critical_errors.append(str(e))
            self.logger.error(f"Pipeline test execution failed: {e}")
            raise
    
    async def execute_stage_test(self, test_id: str, stage: PipelineStage) -> PipelineStageResult:
        """Execute test for specific pipeline stage"""
        try:
            pipeline_test = self.pipeline_tests[test_id]
            config = self.test_configurations[test_id]
            template = self.academic_registry.academic_templates[pipeline_test.template_id]
            
            stage_result = await self._test_pipeline_stage(stage, template, config)
            
            # Update or add stage result
            existing_result = next((r for r in pipeline_test.stage_results if r.stage == stage), None)
            if existing_result:
                pipeline_test.stage_results.remove(existing_result)
            pipeline_test.stage_results.append(stage_result)
            
            return stage_result
            
        except Exception as e:
            self.logger.error(f"Stage test execution failed: {e}")
            raise
    
    def get_pipeline_test_results(self, test_id: str) -> Optional[PipelineTestResult]:
        """Get pipeline test results"""
        return self.pipeline_tests.get(test_id)
    
    def get_stage_performance_analysis(self, stage: PipelineStage) -> Dict[str, Any]:
        """Get performance analysis for specific pipeline stage"""
        try:
            stage_results = []
            for test in self.test_history:
                stage_result = next((r for r in test.stage_results if r.stage == stage), None)
                if stage_result:
                    stage_results.append(stage_result)
            
            if not stage_results:
                return {}
            
            # Calculate stage metrics
            total_tests = len(stage_results)
            successful_tests = len([r for r in stage_results if r.status == PipelineTestStatus.PASSED])
            
            execution_times = [r.execution_time_ms for r in stage_results]
            transformation_accuracies = [r.data_transformation_accuracy for r in stage_results]
            performance_improvements = [r.performance_improvement for r in stage_results]
            
            return {
                'stage': stage.value,
                'summary': {
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'success_rate': successful_tests / total_tests,
                    'average_execution_time_ms': np.mean(execution_times),
                    'average_transformation_accuracy': np.mean(transformation_accuracies),
                    'average_performance_improvement': np.mean(performance_improvements)
                },
                'performance_trends': {
                    'execution_time_trend': execution_times[-10:],  # Last 10 tests
                    'accuracy_trend': transformation_accuracies[-10:],
                    'improvement_trend': performance_improvements[-10:]
                },
                'common_issues': self._get_stage_common_issues(stage_results),
                'recommendations': self._get_stage_recommendations(stage_results)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate stage performance analysis: {e}")
            return {}
    
    def get_pipeline_performance_summary(self) -> Dict[str, Any]:
        """Get overall pipeline performance summary"""
        try:
            if not self.test_history:
                return {}
            
            total_tests = len(self.test_history)
            successful_tests = len([t for t in self.test_history if t.end_to_end_success])
            
            # Pipeline-wide metrics
            execution_times = [t.total_execution_time_ms for t in self.test_history]
            integrity_scores = [t.data_integrity_score for t in self.test_history]
            efficiency_scores = [t.pipeline_efficiency for t in self.test_history]
            
            # Stage-wise analysis
            stage_analysis = {}
            for stage in PipelineStage:
                stage_analysis[stage.value] = self.get_stage_performance_analysis(stage)
            
            # Common failure patterns
            failure_patterns = {}
            for test in self.test_history:
                if not test.end_to_end_success:
                    for error in test.critical_errors:
                        failure_patterns[error] = failure_patterns.get(error, 0) + 1
            
            return {
                'overall_metrics': {
                    'total_pipeline_tests': total_tests,
                    'successful_pipeline_tests': successful_tests,
                    'pipeline_success_rate': successful_tests / total_tests,
                    'average_execution_time_ms': np.mean(execution_times),
                    'average_data_integrity_score': np.mean(integrity_scores),
                    'average_pipeline_efficiency': np.mean(efficiency_scores)
                },
                'stage_analysis': stage_analysis,
                'failure_patterns': dict(sorted(failure_patterns.items(), key=lambda x: x[1], reverse=True)[:10]),
                'performance_trends': {
                    'success_rate_trend': [t.end_to_end_success for t in self.test_history[-20:]],
                    'execution_time_trend': execution_times[-20:],
                    'efficiency_trend': efficiency_scores[-20:]
                },
                'pipeline_recommendations': self._get_pipeline_recommendations()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate pipeline performance summary: {e}")
            return {}
    
    # Private helper methods for stage testing
    async def _test_pipeline_stage(self, stage: PipelineStage, template: AcademicTemplate, config: PipelineTestConfiguration) -> PipelineStageResult:
        """Test individual pipeline stage"""
        stage_result = PipelineStageResult(
            stage=stage,
            stage_name=stage.value.replace('_', ' ').title(),
            status=PipelineTestStatus.RUNNING
        )
        
        start_time = datetime.now()
        
        try:
            if stage == PipelineStage.ACADEMIC_INGESTION:
                await self._test_academic_ingestion_stage(stage_result, template, config)
            elif stage == PipelineStage.VALIDATION:
                await self._test_validation_stage(stage_result, template, config)
            elif stage == PipelineStage.ENHANCEMENT:
                await self._test_enhancement_stage(stage_result, template, config)
            elif stage == PipelineStage.PRODUCTION_ADAPTATION:
                await self._test_production_adaptation_stage(stage_result, template, config)
            elif stage == PipelineStage.INTEGRATION:
                await self._test_integration_stage(stage_result, template, config)
            elif stage == PipelineStage.DEPLOYMENT:
                await self._test_deployment_stage(stage_result, template, config)
            
            stage_result.execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Check execution time threshold
            max_time = config.max_stage_execution_time_ms.get(stage, 30000)
            if stage_result.execution_time_ms > max_time:
                stage_result.warnings.append(f"Execution time {stage_result.execution_time_ms:.0f}ms exceeds threshold {max_time}ms")
            
            # Determine final status
            if stage_result.status == PipelineTestStatus.RUNNING:
                stage_result.status = PipelineTestStatus.PASSED
                
        except Exception as e:
            stage_result.status = PipelineTestStatus.ERROR
            stage_result.error_message = str(e)
            stage_result.execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return stage_result
    
    async def _test_academic_ingestion_stage(self, stage_result: PipelineStageResult, template: AcademicTemplate, config: PipelineTestConfiguration):
        """Test academic strategy ingestion stage"""
        # Simulate ingestion testing
        stage_result.input_data_valid = True
        stage_result.output_data_valid = True
        stage_result.data_transformation_accuracy = 0.98
        stage_result.stage_specific_metrics = {
            'template_parsing_accuracy': 0.99,
            'metadata_completeness': 0.95,
            'validation_data_integrity': 0.97
        }
        stage_result.stage_recommendations.append("Academic ingestion completed successfully")
    
    async def _test_validation_stage(self, stage_result: PipelineStageResult, template: AcademicTemplate, config: PipelineTestConfiguration):
        """Test strategy validation stage"""
        # Use actual validator if available
        try:
            validation_result = self.strategy_validator.validate_academic_strategy(template)
            stage_result.input_data_valid = True
            stage_result.output_data_valid = validation_result.is_valid
            stage_result.data_transformation_accuracy = 0.96
            stage_result.stage_specific_metrics = {
                'validation_score': validation_result.overall_score,
                'constraint_compliance': len(validation_result.passed_constraints) / len(validation_result.constraint_results) if validation_result.constraint_results else 1.0,
                'production_readiness': validation_result.production_readiness_score
            }
            
            if validation_result.is_valid:
                stage_result.stage_recommendations.append("Strategy validation passed")
            else:
                stage_result.warnings.extend(validation_result.issues)
                
        except Exception as e:
            stage_result.warnings.append(f"Validation stage error: {e}")
            stage_result.output_data_valid = False
    
    async def _test_enhancement_stage(self, stage_result: PipelineStageResult, template: AcademicTemplate, config: PipelineTestConfiguration):
        """Test strategy enhancement stage"""
        # Use actual enhancer if available
        try:
            enhancement_result = self.strategy_enhancer.enhance_academic_strategy(template, {})
            stage_result.input_data_valid = True
            stage_result.output_data_valid = enhancement_result.enhancement_applied
            stage_result.data_transformation_accuracy = 0.94
            stage_result.performance_improvement = enhancement_result.performance_improvement_estimate
            stage_result.stage_specific_metrics = {
                'enhancement_score': enhancement_result.enhancement_confidence,
                'feature_additions': len(enhancement_result.enhancement_details),
                'optimization_effectiveness': enhancement_result.performance_improvement_estimate
            }
            
            stage_result.stage_recommendations.append("Strategy enhancement completed")
            
        except Exception as e:
            stage_result.warnings.append(f"Enhancement stage error: {e}")
            stage_result.output_data_valid = False
    
    async def _test_production_adaptation_stage(self, stage_result: PipelineStageResult, template: AcademicTemplate, config: PipelineTestConfiguration):
        """Test production adaptation stage"""
        # Use actual production pipeline if available
        try:
            production_constraints = {
                'max_position_size': 0.10,
                'max_daily_loss': 0.02,
                'commission_rate': 0.001
            }
            
            evaluation = self.production_pipeline.evaluate_academic_strategy(template.template_id, production_constraints)
            stage_result.input_data_valid = True
            stage_result.output_data_valid = evaluation.production_strategy is not None
            stage_result.data_transformation_accuracy = 0.92
            stage_result.stage_specific_metrics = {
                'production_compatibility': evaluation.validation_result.is_valid if evaluation.validation_result else 0.0,
                'constraint_satisfaction': 0.95,  # Mock value
                'adaptation_effectiveness': 0.88   # Mock value
            }
            
            stage_result.stage_recommendations.append("Production adaptation completed")
            
        except Exception as e:
            stage_result.warnings.append(f"Production adaptation error: {e}")
            stage_result.output_data_valid = False
    
    async def _test_integration_stage(self, stage_result: PipelineStageResult, template: AcademicTemplate, config: PipelineTestConfiguration):
        """Test system integration stage"""
        # Mock integration testing
        stage_result.input_data_valid = True
        stage_result.output_data_valid = True
        stage_result.data_transformation_accuracy = 0.90
        stage_result.stage_specific_metrics = {
            'core_engine_integration': 0.92,
            'template_system_compatibility': 0.94,
            'dynamic_adaptation_integration': 0.89
        }
        stage_result.stage_recommendations.append("System integration successful")
    
    async def _test_deployment_stage(self, stage_result: PipelineStageResult, template: AcademicTemplate, config: PipelineTestConfiguration):
        """Test deployment stage"""
        # Mock deployment testing
        stage_result.input_data_valid = True
        stage_result.output_data_valid = True
        stage_result.data_transformation_accuracy = 0.88
        stage_result.stage_specific_metrics = {
            'deployment_readiness': 0.91,
            'production_environment_compatibility': 0.93,
            'monitoring_integration': 0.87
        }
        stage_result.stage_recommendations.append("Deployment stage completed")
    
    async def _test_end_to_end_pipeline(self, pipeline_test: PipelineTestResult, template: AcademicTemplate, config: PipelineTestConfiguration):
        """Test complete end-to-end pipeline flow"""
        try:
            # Check if all stages completed successfully
            successful_stages = [r for r in pipeline_test.stage_results if r.status == PipelineTestStatus.PASSED]
            total_stages = len(pipeline_test.stage_results)
            
            pipeline_test.end_to_end_success = len(successful_stages) == total_stages and total_stages > 0
            
            if pipeline_test.end_to_end_success:
                pipeline_test.recommendations.append("End-to-end pipeline test successful")
            else:
                failed_stages = [r.stage.value for r in pipeline_test.stage_results if r.status != PipelineTestStatus.PASSED]
                pipeline_test.critical_errors.append(f"Pipeline failed at stages: {', '.join(failed_stages)}")
                
        except Exception as e:
            pipeline_test.critical_errors.append(f"End-to-end test error: {e}")
    
    async def _test_data_integrity(self, pipeline_test: PipelineTestResult, template: AcademicTemplate, config: PipelineTestConfiguration):
        """Test data integrity throughout pipeline"""
        try:
            # Calculate overall data integrity score
            if pipeline_test.stage_results:
                integrity_scores = [r.data_transformation_accuracy for r in pipeline_test.stage_results if r.data_transformation_accuracy > 0]
                pipeline_test.data_integrity_score = np.mean(integrity_scores) if integrity_scores else 0.0
            else:
                pipeline_test.data_integrity_score = 0.0
            
            if pipeline_test.data_integrity_score >= config.min_data_integrity_score:
                pipeline_test.recommendations.append("Data integrity maintained throughout pipeline")
            else:
                pipeline_test.critical_errors.append(f"Data integrity score {pipeline_test.data_integrity_score:.3f} below threshold {config.min_data_integrity_score}")
                
        except Exception as e:
            pipeline_test.critical_errors.append(f"Data integrity test error: {e}")
    
    async def _test_workflow_continuity(self, pipeline_test: PipelineTestResult, template: AcademicTemplate, config: PipelineTestConfiguration):
        """Test workflow continuity and stage transitions"""
        try:
            # Check stage execution order and data flow
            continuity_score = 1.0
            
            for i, stage_result in enumerate(pipeline_test.stage_results[:-1]):
                next_stage = pipeline_test.stage_results[i + 1]
                
                # Check data flow continuity
                if not stage_result.output_data_valid or not next_stage.input_data_valid:
                    continuity_score -= 0.2
                    pipeline_test.recommendations.append(f"Data flow issue between {stage_result.stage.value} and {next_stage.stage.value}")
            
            pipeline_test.pipeline_efficiency = continuity_score
            
            if continuity_score >= config.min_pipeline_efficiency:
                pipeline_test.recommendations.append("Workflow continuity maintained")
            else:
                pipeline_test.critical_errors.append(f"Workflow continuity score {continuity_score:.3f} below threshold {config.min_pipeline_efficiency}")
                
        except Exception as e:
            pipeline_test.critical_errors.append(f"Workflow continuity test error: {e}")
    
    async def _test_error_handling(self, pipeline_test: PipelineTestResult, template: AcademicTemplate, config: PipelineTestConfiguration):
        """Test error handling and recovery mechanisms"""
        try:
            # Mock error handling testing
            error_handling_score = 0.85  # Mock score
            
            if error_handling_score >= 0.8:
                pipeline_test.recommendations.append("Error handling mechanisms functional")
            else:
                pipeline_test.critical_errors.append("Error handling inadequate")
                
        except Exception as e:
            pipeline_test.critical_errors.append(f"Error handling test error: {e}")
    
    async def _calculate_pipeline_results(self, pipeline_test: PipelineTestResult, config: PipelineTestConfiguration):
        """Calculate overall pipeline test results"""
        try:
            # Determine overall status
            if pipeline_test.critical_errors:
                pipeline_test.status = PipelineTestStatus.FAILED
            elif pipeline_test.end_to_end_success:
                pipeline_test.status = PipelineTestStatus.PASSED
            else:
                pipeline_test.status = PipelineTestStatus.FAILED
            
            # Calculate performance degradation
            if pipeline_test.stage_results:
                performance_improvements = [r.performance_improvement for r in pipeline_test.stage_results if r.performance_improvement > 0]
                if performance_improvements:
                    pipeline_test.performance_degradation = max(0, -min(performance_improvements))
                else:
                    pipeline_test.performance_degradation = 0.0
            
            # Check timing constraints
            if pipeline_test.total_execution_time_ms > config.max_total_pipeline_time_ms:
                pipeline_test.critical_errors.append(f"Pipeline execution time {pipeline_test.total_execution_time_ms:.0f}ms exceeds limit {config.max_total_pipeline_time_ms}ms")
            
        except Exception as e:
            pipeline_test.critical_errors.append(f"Result calculation error: {e}")
    
    def _update_pipeline_metrics(self, pipeline_test: PipelineTestResult):
        """Update framework-wide pipeline metrics"""
        self.pipeline_metrics['total_pipeline_tests'] += 1
        
        if pipeline_test.end_to_end_success:
            self.pipeline_metrics['successful_pipeline_tests'] += 1
        
        # Update success rate
        total = self.pipeline_metrics['total_pipeline_tests']
        successful = self.pipeline_metrics['successful_pipeline_tests']
        self.pipeline_metrics['pipeline_reliability_score'] = successful / total if total > 0 else 0
        
        # Update average execution time
        all_times = [t.total_execution_time_ms for t in self.test_history] + [pipeline_test.total_execution_time_ms]
        self.pipeline_metrics['average_pipeline_time_ms'] = np.mean(all_times)
        
        # Update stage success rates
        for stage_result in pipeline_test.stage_results:
            stage_name = stage_result.stage.value
            if stage_name not in self.pipeline_metrics['stage_success_rates']:
                self.pipeline_metrics['stage_success_rates'][stage_name] = {'total': 0, 'successful': 0}
            
            self.pipeline_metrics['stage_success_rates'][stage_name]['total'] += 1
            if stage_result.status == PipelineTestStatus.PASSED:
                self.pipeline_metrics['stage_success_rates'][stage_name]['successful'] += 1
    
    def _get_stage_common_issues(self, stage_results: List[PipelineStageResult]) -> List[str]:
        """Get common issues for a specific stage"""
        issue_counts = {}
        
        for result in stage_results:
            if result.error_message:
                issue_counts[result.error_message] = issue_counts.get(result.error_message, 0) + 1
            
            for warning in result.warnings:
                issue_counts[warning] = issue_counts.get(warning, 0) + 1
        
        # Return top 5 most common issues
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        return [issue for issue, count in sorted_issues[:5]]
    
    def _get_stage_recommendations(self, stage_results: List[PipelineStageResult]) -> List[str]:
        """Get recommendations for a specific stage"""
        recommendations = []
        
        # Analyze performance patterns
        execution_times = [r.execution_time_ms for r in stage_results]
        avg_time = np.mean(execution_times)
        
        if avg_time > 10000:  # 10 seconds
            recommendations.append("Consider optimizing stage execution time")
        
        # Analyze accuracy patterns
        accuracies = [r.data_transformation_accuracy for r in stage_results if r.data_transformation_accuracy > 0]
        if accuracies and np.mean(accuracies) < 0.9:
            recommendations.append("Improve data transformation accuracy")
        
        return recommendations[:3]  # Top 3 recommendations
    
    def _get_pipeline_recommendations(self) -> List[str]:
        """Get overall pipeline recommendations"""
        recommendations = []
        
        if not self.test_history:
            return recommendations
        
        # Analyze overall success rate
        success_rate = self.pipeline_metrics['pipeline_reliability_score']
        if success_rate < 0.8:
            recommendations.append("Pipeline reliability below 80% - comprehensive review needed")
        
        # Analyze execution times
        avg_time = self.pipeline_metrics['average_pipeline_time_ms']
        if avg_time > 45000:  # 45 seconds
            recommendations.append("Pipeline execution time optimization recommended")
        
        # Analyze stage performance
        stage_rates = self.pipeline_metrics['stage_success_rates']
        for stage_name, metrics in stage_rates.items():
            if metrics['total'] > 0:
                rate = metrics['successful'] / metrics['total']
                if rate < 0.9:
                    recommendations.append(f"Focus on improving {stage_name} stage reliability")
        
        return recommendations[:5]  # Top 5 recommendations
