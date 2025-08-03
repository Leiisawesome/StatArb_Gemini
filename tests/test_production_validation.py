"""
Production Validation Test Suite

Comprehensive tests for the production validation framework including:
- SystemValidator initialization and configuration
- Module integration validation
- AI infrastructure validation
- Analytics integration validation
- System orchestrator validation
- Signal generation validation
- Full validation workflow testing

Author: Pro Quant Desk Trader
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Mock all problematic imports at the module level
with patch.dict('sys.modules', {
    'core_structure.benchmarks.backtesting.engine': Mock(),
    'core_structure.analytics.performance_analytics': Mock(),
    'core_structure.infrastructure.config.base_config': Mock(),
    'core_structure.market_data.data_manager': Mock(),
    'core_structure.risk_management.risk_manager': Mock(),
    'core_structure.portfolio_management.portfolio_manager': Mock(),
    'core_structure.ai_infrastructure.llm_integration.llm_client': Mock(),
    'core_structure.ai_infrastructure.knowledge.knowledge_base': Mock(),
    'core_structure.ai_infrastructure.vector_store.vector_database': Mock(),
    'core_structure.analytics.execution_analytics': Mock(),
    'core_structure.optimization.optimization_analytics': Mock(),
    'core_structure.infrastructure.system_orchestrator': Mock(),
    'core_structure.signal_generation.ai_signal_enhancer': Mock(),
}):
    # Now import the validation components
    from core_structure.production_validation.system_validator import (
        SystemValidator, ValidationConfig, ValidationResults
    )
    from core_structure.production_validation.system_validator import (
        OptimizationStatus, OptimizationType, ConvergenceType
    )

logger = logging.getLogger(__name__)


class TestValidationConfiguration:
    """Test validation configuration and settings."""
    
    def test_validation_config_defaults(self):
        """Test ValidationConfig default values."""
        config = ValidationConfig()
        
        # Test tolerance thresholds
        assert config.performance_tolerance == 0.05
        assert config.risk_tolerance == 0.02
        assert config.cost_tolerance == 0.01
        assert config.correlation_threshold == 0.8
        
        # Test validation parameters
        assert config.test_duration_minutes == 60
        assert config.min_trades_required == 5
        assert config.max_drawdown_tolerance == 0.02
        
        # Test scoring weights
        assert config.performance_weight == 0.4
        assert config.cost_weight == 0.3
        assert config.risk_weight == 0.3
        
        # Test reporting settings
        assert config.min_passing_score == 70.0
        assert config.warning_score == 85.0
        assert config.save_detailed_results is True
        
        # Test real-time monitoring
        assert config.enable_continuous_monitoring is True
        assert config.monitoring_frequency_seconds == 300
        assert config.alert_threshold_score == 60.0
    
    def test_validation_config_custom_values(self):
        """Test ValidationConfig with custom values."""
        config = ValidationConfig(
            performance_tolerance=0.1,
            risk_tolerance=0.05,
            cost_tolerance=0.02,
            test_duration_minutes=120,
            min_passing_score=80.0,
            enable_continuous_monitoring=False
        )
        
        assert config.performance_tolerance == 0.1
        assert config.risk_tolerance == 0.05
        assert config.cost_tolerance == 0.02
        assert config.test_duration_minutes == 120
        assert config.min_passing_score == 80.0
        assert config.enable_continuous_monitoring is False


class TestValidationResults:
    """Test ValidationResults functionality."""
    
    def test_validation_results_creation(self):
        """Test ValidationResults creation and basic functionality."""
        timestamp = datetime.now()
        production_results = {'test': 'data'}
        backtest_results = {'test': 'data'}
        
        results = ValidationResults(
            timestamp=timestamp,
            validation_score=85.5,
            status='PASSED',
            production_results=production_results,
            backtest_results=backtest_results
        )
        
        assert results.timestamp == timestamp
        assert results.validation_score == 85.5
        assert results.status == 'PASSED'
        assert results.production_results == production_results
        assert results.backtest_results == backtest_results
    
    def test_validation_results_to_dict(self):
        """Test ValidationResults to_dict method."""
        timestamp = datetime.now()
        results = ValidationResults(
            timestamp=timestamp,
            validation_score=90.0,
            status='PASSED',
            production_results={'prod': 'data'},
            backtest_results={'backtest': 'data'}
        )
        
        results_dict = results.to_dict()
        
        assert isinstance(results_dict, dict)
        assert 'timestamp' in results_dict
        assert 'validation_score' in results_dict
        assert 'status' in results_dict
        assert 'production_results' in results_dict
        assert 'backtest_results' in results_dict
        assert results_dict['validation_score'] == 90.0
        assert results_dict['status'] == 'PASSED'


class TestOptimizationEnums:
    """Test optimization enums."""
    
    def test_optimization_status_enum(self):
        """Test OptimizationStatus enum values."""
        assert OptimizationStatus.PENDING == "pending"
        assert OptimizationStatus.RUNNING == "running"
        assert OptimizationStatus.CONVERGED == "converged"
        assert OptimizationStatus.FAILED == "failed"
        assert OptimizationStatus.TIMEOUT == "timeout"
        assert OptimizationStatus.CANCELLED == "cancelled"
    
    def test_optimization_type_enum(self):
        """Test OptimizationType enum values."""
        assert OptimizationType.PORTFOLIO_OPTIMIZATION == "portfolio_optimization"
        assert OptimizationType.PARAMETER_OPTIMIZATION == "parameter_optimization"
        assert OptimizationType.ALGORITHM_OPTIMIZATION == "algorithm_optimization"
        assert OptimizationType.RISK_OPTIMIZATION == "risk_optimization"
        assert OptimizationType.COST_OPTIMIZATION == "cost_optimization"
        assert OptimizationType.PERFORMANCE_OPTIMIZATION == "performance_optimization"
    
    def test_convergence_type_enum(self):
        """Test ConvergenceType enum values."""
        assert ConvergenceType.GRADIENT_BASED == "gradient_based"
        assert ConvergenceType.POPULATION_BASED == "population_based"
        assert ConvergenceType.BAYESIAN == "bayesian"
        assert ConvergenceType.GRID_SEARCH == "grid_search"
        assert ConvergenceType.RANDOM_SEARCH == "random_search"
        assert ConvergenceType.HYBRID == "hybrid"


class TestSystemValidatorInitialization:
    """Test SystemValidator initialization and configuration."""
    
    @patch('core_structure.production_validation.system_validator.BacktestEngine')
    @patch('core_structure.production_validation.system_validator.PerformanceAnalytics')
    @patch('core_structure.production_validation.system_validator.MarketDataManager')
    @patch('core_structure.production_validation.system_validator.ExecutionAnalytics')
    @patch('core_structure.production_validation.system_validator.OptimizationAnalytics')
    @patch('core_structure.production_validation.system_validator.SystemOrchestrator')
    @patch('core_structure.production_validation.system_validator.LLMClient')
    @patch('core_structure.production_validation.system_validator.KnowledgeBase')
    @patch('core_structure.production_validation.system_validator.VectorDatabase')
    @patch('core_structure.production_validation.system_validator.AISignalEnhancer')
    def test_default_initialization(self, mock_enhancer, mock_vdb, mock_kb, mock_llm, 
                                   mock_orchestrator, mock_opt_analytics, mock_exec_analytics,
                                   mock_data_manager, mock_perf_analytics, mock_backtest):
        """Test SystemValidator initialization with default config."""
        validator = SystemValidator()
        
        assert validator is not None
        assert validator.config is not None
        assert isinstance(validator.config, ValidationConfig)
        assert validator.config.performance_tolerance == 0.05
        assert validator.config.risk_tolerance == 0.02
        assert validator.config.cost_tolerance == 0.01
    
    @patch('core_structure.production_validation.system_validator.BacktestEngine')
    @patch('core_structure.production_validation.system_validator.PerformanceAnalytics')
    @patch('core_structure.production_validation.system_validator.MarketDataManager')
    @patch('core_structure.production_validation.system_validator.ExecutionAnalytics')
    @patch('core_structure.production_validation.system_validator.OptimizationAnalytics')
    @patch('core_structure.production_validation.system_validator.SystemOrchestrator')
    @patch('core_structure.production_validation.system_validator.LLMClient')
    @patch('core_structure.production_validation.system_validator.KnowledgeBase')
    @patch('core_structure.production_validation.system_validator.VectorDatabase')
    @patch('core_structure.production_validation.system_validator.AISignalEnhancer')
    def test_custom_config_initialization(self, mock_enhancer, mock_vdb, mock_kb, mock_llm, 
                                         mock_orchestrator, mock_opt_analytics, mock_exec_analytics,
                                         mock_data_manager, mock_perf_analytics, mock_backtest):
        """Test SystemValidator initialization with custom config."""
        custom_config = ValidationConfig(
            performance_tolerance=0.1,
            risk_tolerance=0.05,
            cost_tolerance=0.02,
            test_duration_minutes=120
        )
        
        validator = SystemValidator(custom_config)
        
        assert validator.config.performance_tolerance == 0.1
        assert validator.config.risk_tolerance == 0.05
        assert validator.config.cost_tolerance == 0.02
        assert validator.config.test_duration_minutes == 120
    
    @patch('core_structure.production_validation.system_validator.BacktestEngine')
    @patch('core_structure.production_validation.system_validator.PerformanceAnalytics')
    @patch('core_structure.production_validation.system_validator.MarketDataManager')
    @patch('core_structure.production_validation.system_validator.ExecutionAnalytics')
    @patch('core_structure.production_validation.system_validator.OptimizationAnalytics')
    @patch('core_structure.production_validation.system_validator.SystemOrchestrator')
    @patch('core_structure.production_validation.system_validator.LLMClient')
    @patch('core_structure.production_validation.system_validator.KnowledgeBase')
    @patch('core_structure.production_validation.system_validator.VectorDatabase')
    @patch('core_structure.production_validation.system_validator.AISignalEnhancer')
    def test_component_initialization(self, mock_enhancer, mock_vdb, mock_kb, mock_llm, 
                                     mock_orchestrator, mock_opt_analytics, mock_exec_analytics,
                                     mock_data_manager, mock_perf_analytics, mock_backtest):
        """Test that all components are properly initialized."""
        validator = SystemValidator()
        
        # Check core components
        assert hasattr(validator, 'production_interface')
        assert hasattr(validator, 'backtest_engine')
        assert hasattr(validator, 'performance_analytics')
        assert hasattr(validator, 'data_manager')
        
        # Check new modules
        assert hasattr(validator, 'execution_analytics')
        assert hasattr(validator, 'optimization_analytics')
        assert hasattr(validator, 'system_orchestrator')
        
        # Check AI infrastructure components
        assert hasattr(validator, 'llm_client')
        assert hasattr(validator, 'knowledge_base')
        assert hasattr(validator, 'vector_database')
        assert hasattr(validator, 'ai_signal_enhancer')
        
        # Check state tracking
        assert hasattr(validator, 'validation_history')
        assert hasattr(validator, 'continuous_monitoring')
        assert isinstance(validator.validation_history, list)
        assert validator.continuous_monitoring is False


class TestModuleIntegrationValidation:
    """Test module integration validation functionality."""
    
    @pytest.fixture
    async def validator(self):
        """Create SystemValidator instance for testing."""
        with patch('core_structure.production_validation.system_validator.BacktestEngine'), \
             patch('core_structure.production_validation.system_validator.PerformanceAnalytics'), \
             patch('core_structure.production_validation.system_validator.MarketDataManager'), \
             patch('core_structure.production_validation.system_validator.ExecutionAnalytics'), \
             patch('core_structure.production_validation.system_validator.OptimizationAnalytics'), \
             patch('core_structure.production_validation.system_validator.SystemOrchestrator'), \
             patch('core_structure.production_validation.system_validator.LLMClient'), \
             patch('core_structure.production_validation.system_validator.KnowledgeBase'), \
             patch('core_structure.production_validation.system_validator.VectorDatabase'), \
             patch('core_structure.production_validation.system_validator.AISignalEnhancer'):
            return SystemValidator()
    
    @pytest.mark.asyncio
    async def test_validate_module_integration(self, validator):
        """Test the main module integration validation method."""
        results = await validator.validate_module_integration()
        
        assert results is not None
        assert 'timestamp' in results
        assert 'integration_tests' in results
        assert 'overall_status' in results
        
        # Check that all integration test categories are present
        integration_tests = results['integration_tests']
        assert 'ai_infrastructure' in integration_tests
        assert 'analytics' in integration_tests
        assert 'orchestrator' in integration_tests
        assert 'signal_generation' in integration_tests
    
    @pytest.mark.asyncio
    async def test_ai_infrastructure_integration(self, validator):
        """Test AI infrastructure integration validation."""
        results = await validator._validate_ai_infrastructure_integration()
        
        assert results is not None
        assert 'status' in results
        assert 'components' in results
        
        # Check that all AI components are tested
        components = results['components']
        assert 'llm_client' in components
        assert 'knowledge_base' in components
        assert 'vector_database' in components
        assert 'ai_signal_enhancer' in components
    
    @pytest.mark.asyncio
    async def test_analytics_integration(self, validator):
        """Test analytics integration validation."""
        results = await validator._validate_analytics_integration()
        
        assert results is not None
        assert 'status' in results
        assert 'components' in results
        
        # Check that all analytics components are tested
        components = results['components']
        assert 'execution_analytics' in components
        assert 'optimization_analytics' in components
        assert 'performance_analytics' in components
    
    @pytest.mark.asyncio
    async def test_orchestrator_integration(self, validator):
        """Test system orchestrator integration validation."""
        results = await validator._validate_orchestrator_integration()
        
        assert results is not None
        assert 'status' in results
        assert 'orchestrator_status' in results
        assert 'module_registration' in results
        assert 'communication_tests' in results
    
    @pytest.mark.asyncio
    async def test_signal_generation_integration(self, validator):
        """Test signal generation integration validation."""
        results = await validator._validate_signal_generation_integration()
        
        assert results is not None
        assert 'status' in results
        assert 'signal_enhancer_status' in results
        assert 'enhancement_tests' in results


class TestComponentTesting:
    """Test individual component testing methods."""
    
    @pytest.fixture
    async def validator(self):
        """Create SystemValidator instance for testing."""
        with patch('core_structure.production_validation.system_validator.BacktestEngine'), \
             patch('core_structure.production_validation.system_validator.PerformanceAnalytics'), \
             patch('core_structure.production_validation.system_validator.MarketDataManager'), \
             patch('core_structure.production_validation.system_validator.ExecutionAnalytics'), \
             patch('core_structure.production_validation.system_validator.OptimizationAnalytics'), \
             patch('core_structure.production_validation.system_validator.SystemOrchestrator'), \
             patch('core_structure.production_validation.system_validator.LLMClient'), \
             patch('core_structure.production_validation.system_validator.KnowledgeBase'), \
             patch('core_structure.production_validation.system_validator.VectorDatabase'), \
             patch('core_structure.production_validation.system_validator.AISignalEnhancer'):
            return SystemValidator()
    
    @pytest.mark.asyncio
    async def test_llm_client_testing(self, validator):
        """Test LLM client testing method."""
        result = await validator._test_llm_client()
        
        assert result is not None
        assert 'status' in result
        assert 'test_time' in result
        assert result['status'] in ['OK', 'UNAVAILABLE', 'ERROR']
    
    @pytest.mark.asyncio
    async def test_knowledge_base_testing(self, validator):
        """Test knowledge base testing method."""
        result = await validator._test_knowledge_base()
        
        assert result is not None
        assert 'status' in result
        assert 'test_time' in result
        assert result['status'] in ['OK', 'UNAVAILABLE', 'ERROR']
    
    @pytest.mark.asyncio
    async def test_vector_database_testing(self, validator):
        """Test vector database testing method."""
        result = await validator._test_vector_database()
        
        assert result is not None
        assert 'status' in result
        assert 'test_time' in result
        assert result['status'] in ['OK', 'UNAVAILABLE', 'ERROR']
    
    @pytest.mark.asyncio
    async def test_ai_signal_enhancer_testing(self, validator):
        """Test AI signal enhancer testing method."""
        result = await validator._test_ai_signal_enhancer()
        
        assert result is not None
        assert 'status' in result
        assert 'test_time' in result
        assert result['status'] in ['OK', 'ERROR']
    
    @pytest.mark.asyncio
    async def test_execution_analytics_testing(self, validator):
        """Test execution analytics testing method."""
        result = await validator._test_execution_analytics()
        
        assert result is not None
        assert 'status' in result
        assert 'test_time' in result
        assert result['status'] in ['OK', 'ERROR']
    
    @pytest.mark.asyncio
    async def test_optimization_analytics_testing(self, validator):
        """Test optimization analytics testing method."""
        result = await validator._test_optimization_analytics()
        
        assert result is not None
        assert 'status' in result
        assert 'test_time' in result
        assert result['status'] in ['OK', 'ERROR']
    
    @pytest.mark.asyncio
    async def test_performance_analytics_testing(self, validator):
        """Test performance analytics testing method."""
        result = await validator._test_performance_analytics()
        
        assert result is not None
        assert 'status' in result
        assert 'test_time' in result
        assert result['status'] in ['OK', 'ERROR']
    
    @pytest.mark.asyncio
    async def test_system_orchestrator_testing(self, validator):
        """Test system orchestrator testing method."""
        result = await validator._test_system_orchestrator()
        
        assert result is not None
        assert 'status' in result
        assert 'test_time' in result
        assert result['status'] in ['OK', 'ERROR']


class TestValidationFrameworkStructure:
    """Test the structure and organization of the validation framework."""
    
    def test_validation_config_structure(self):
        """Test that ValidationConfig has all required fields."""
        config = ValidationConfig()
        
        # Check that all expected fields exist
        expected_fields = [
            'performance_tolerance', 'risk_tolerance', 'cost_tolerance', 'correlation_threshold',
            'test_duration_minutes', 'min_trades_required', 'max_drawdown_tolerance',
            'performance_weight', 'cost_weight', 'risk_weight',
            'min_passing_score', 'warning_score', 'save_detailed_results',
            'enable_continuous_monitoring', 'monitoring_frequency_seconds', 'alert_threshold_score'
        ]
        
        for field in expected_fields:
            assert hasattr(config, field), f"ValidationConfig missing field: {field}"
    
    def test_validation_results_structure(self):
        """Test that ValidationResults has all required fields."""
        timestamp = datetime.now()
        results = ValidationResults(
            timestamp=timestamp,
            validation_score=85.0,
            status='PASSED',
            production_results={},
            backtest_results={}
        )
        
        # Check that all expected fields exist
        expected_fields = [
            'timestamp', 'validation_score', 'status',
            'production_results', 'backtest_results',
            'performance_comparison', 'cost_comparison', 'risk_comparison',
            'recommendations', 'issues', 'warnings',
            'correlation_analysis', 'degradation_metrics'
        ]
        
        for field in expected_fields:
            assert hasattr(results, field), f"ValidationResults missing field: {field}"


class TestValidationDataTypes:
    """Test validation data types and serialization."""
    
    def test_validation_config_serialization(self):
        """Test that ValidationConfig can be serialized."""
        config = ValidationConfig()
        
        # Test that config can be converted to dict-like structure
        config_dict = {
            'performance_tolerance': config.performance_tolerance,
            'risk_tolerance': config.risk_tolerance,
            'cost_tolerance': config.cost_tolerance,
            'test_duration_minutes': config.test_duration_minutes,
            'min_passing_score': config.min_passing_score
        }
        
        assert isinstance(config_dict, dict)
        assert config_dict['performance_tolerance'] == 0.05
        assert config_dict['risk_tolerance'] == 0.02
    
    def test_validation_results_serialization(self):
        """Test that ValidationResults can be serialized."""
        timestamp = datetime.now()
        results = ValidationResults(
            timestamp=timestamp,
            validation_score=90.0,
            status='PASSED',
            production_results={'test': 'data'},
            backtest_results={'test': 'data'}
        )
        
        # Test to_dict method
        results_dict = results.to_dict()
        
        assert isinstance(results_dict, dict)
        assert 'timestamp' in results_dict
        assert 'validation_score' in results_dict
        assert 'status' in results_dict
        
        # Test that timestamp is properly serialized
        assert isinstance(results_dict['timestamp'], str)
        
        # Test that validation score is properly serialized
        assert isinstance(results_dict['validation_score'], float)
        assert results_dict['validation_score'] == 90.0


class TestValidationLogic:
    """Test validation logic and calculations."""
    
    def test_validation_score_calculation_logic(self):
        """Test the logic for validation score calculations."""
        # Test that validation scores are properly bounded
        timestamp = datetime.now()
        
        # Test with perfect score
        perfect_results = ValidationResults(
            timestamp=timestamp,
            validation_score=100.0,
            status='PASSED',
            production_results={},
            backtest_results={}
        )
        assert perfect_results.validation_score == 100.0
        assert perfect_results.status == 'PASSED'
        
        # Test with failing score
        failing_results = ValidationResults(
            timestamp=timestamp,
            validation_score=50.0,
            status='FAILED',
            production_results={},
            backtest_results={}
        )
        assert failing_results.validation_score == 50.0
        assert failing_results.status == 'FAILED'
    
    def test_validation_status_logic(self):
        """Test validation status logic."""
        timestamp = datetime.now()
        
        # Test PASSED status
        passed_results = ValidationResults(
            timestamp=timestamp,
            validation_score=85.0,
            status='PASSED',
            production_results={},
            backtest_results={}
        )
        assert passed_results.status == 'PASSED'
        
        # Test WARNING status
        warning_results = ValidationResults(
            timestamp=timestamp,
            validation_score=75.0,
            status='WARNING',
            production_results={},
            backtest_results={}
        )
        assert warning_results.status == 'WARNING'
        
        # Test FAILED status
        failed_results = ValidationResults(
            timestamp=timestamp,
            validation_score=60.0,
            status='FAILED',
            production_results={},
            backtest_results={}
        )
        assert failed_results.status == 'FAILED'


class TestErrorHandling:
    """Test error handling in validation framework."""
    
    @pytest.fixture
    async def validator(self):
        """Create SystemValidator instance for testing."""
        with patch('core_structure.production_validation.system_validator.BacktestEngine'), \
             patch('core_structure.production_validation.system_validator.PerformanceAnalytics'), \
             patch('core_structure.production_validation.system_validator.MarketDataManager'), \
             patch('core_structure.production_validation.system_validator.ExecutionAnalytics'), \
             patch('core_structure.production_validation.system_validator.OptimizationAnalytics'), \
             patch('core_structure.production_validation.system_validator.SystemOrchestrator'), \
             patch('core_structure.production_validation.system_validator.LLMClient'), \
             patch('core_structure.production_validation.system_validator.KnowledgeBase'), \
             patch('core_structure.production_validation.system_validator.VectorDatabase'), \
             patch('core_structure.production_validation.system_validator.AISignalEnhancer'):
            return SystemValidator()
    
    @pytest.mark.asyncio
    async def test_module_integration_error_handling(self, validator):
        """Test error handling in module integration validation."""
        # Mock a component to raise an exception
        with patch.object(validator, '_validate_ai_infrastructure_integration', side_effect=Exception("Test error")):
            results = await validator.validate_module_integration()
            
            assert results is not None
            assert results['overall_status'] == 'ERROR'
            assert 'error' in results
    
    @pytest.mark.asyncio
    async def test_component_testing_error_handling(self, validator):
        """Test error handling in component testing."""
        # Mock a component to raise an exception
        with patch.object(validator.llm_client, 'is_available', side_effect=Exception("Test error")):
            result = await validator._test_llm_client()
            
            assert result is not None
            assert result['status'] == 'ERROR'
            assert 'error' in result


class TestIntegrationWorkflow:
    """Test complete integration workflow."""
    
    @pytest.fixture
    async def validator(self):
        """Create SystemValidator instance for testing."""
        with patch('core_structure.production_validation.system_validator.BacktestEngine'), \
             patch('core_structure.production_validation.system_validator.PerformanceAnalytics'), \
             patch('core_structure.production_validation.system_validator.MarketDataManager'), \
             patch('core_structure.production_validation.system_validator.ExecutionAnalytics'), \
             patch('core_structure.production_validation.system_validator.OptimizationAnalytics'), \
             patch('core_structure.production_validation.system_validator.SystemOrchestrator'), \
             patch('core_structure.production_validation.system_validator.LLMClient'), \
             patch('core_structure.production_validation.system_validator.KnowledgeBase'), \
             patch('core_structure.production_validation.system_validator.VectorDatabase'), \
             patch('core_structure.production_validation.system_validator.AISignalEnhancer'):
            return SystemValidator()
    
    @pytest.mark.asyncio
    async def test_complete_validation_workflow(self, validator):
        """Test complete validation workflow from start to finish."""
        # Run module integration validation
        integration_results = await validator.validate_module_integration()
        
        assert integration_results is not None
        assert 'overall_status' in integration_results
        assert 'integration_tests' in integration_results
        
        # Check that all test categories are present
        test_categories = integration_results['integration_tests']
        assert len(test_categories) >= 4  # Should have at least 4 categories
        
        # Verify that results are properly structured
        for category_name, category_results in test_categories.items():
            assert 'status' in category_results
            assert category_results['status'] in ['PASSED', 'FAILED', 'ERROR']
    
    @pytest.mark.asyncio
    async def test_validation_with_mock_components(self, validator):
        """Test validation with mocked components."""
        # Mock all components to return successful status
        with patch.object(validator, '_test_llm_client', return_value={'status': 'OK', 'test_time': datetime.now().isoformat()}):
            with patch.object(validator, '_test_knowledge_base', return_value={'status': 'OK', 'test_time': datetime.now().isoformat()}):
                with patch.object(validator, '_test_vector_database', return_value={'status': 'OK', 'test_time': datetime.now().isoformat()}):
                    with patch.object(validator, '_test_ai_signal_enhancer', return_value={'status': 'OK', 'test_time': datetime.now().isoformat()}):
                        results = await validator._validate_ai_infrastructure_integration()
                        
                        assert results is not None
                        assert results['status'] == 'PASSED'


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 