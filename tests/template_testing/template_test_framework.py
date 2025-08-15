"""
Template Test Framework
======================

Core framework for template-based testing with inheritance support
and category-aware test execution.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import traceback

from strategy_templates.base import (
    TemplateRegistry, BaseTemplate, TemplateCategory, TemplateType, TemplateStatus
)
from core_structure.template_integration.template_core_engine import TemplateCoreEngine
from core_structure.template_integration.template_config import TemplateEngineConfig, ExecutionMode

logger = logging.getLogger(__name__)

class TestExecutionMode(Enum):
    """Test execution modes"""
    SINGLE_TEMPLATE = "single_template"
    INHERITANCE_CHAIN = "inheritance_chain"
    CATEGORY_BATCH = "category_batch"
    CROSS_CATEGORY = "cross_category"
    STRESS_TEST = "stress_test"

class TestSeverity(Enum):
    """Test severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class TemplateTestConfig:
    """Configuration for template-based testing"""
    # Test execution settings
    execution_mode: TestExecutionMode = TestExecutionMode.SINGLE_TEMPLATE
    target_categories: List[TemplateCategory] = field(default_factory=lambda: list(TemplateCategory))
    target_templates: List[str] = field(default_factory=list)
    
    # Test parameters
    test_timeout_ms: int = 10000
    max_concurrent_tests: int = 5
    enable_performance_testing: bool = True
    enable_inheritance_testing: bool = True
    enable_validation_testing: bool = True
    
    # Test data configuration
    use_synthetic_data: bool = True
    synthetic_data_size: int = 1000
    market_data_symbols: List[str] = field(default_factory=lambda: ['AAPL', 'GOOGL', 'MSFT'])
    
    # Performance thresholds
    max_execution_time_ms: float = 1000.0
    min_success_rate: float = 0.95
    min_signal_quality: float = 0.7
    
    # Inheritance testing
    max_inheritance_depth: int = 5
    test_inheritance_conflicts: bool = True
    
    # Error handling
    continue_on_failure: bool = True
    generate_detailed_reports: bool = True

@dataclass
class TemplateTestResult:
    """Result of template test execution"""
    test_id: str
    template_id: str
    template_category: TemplateCategory
    test_type: str
    execution_mode: TestExecutionMode
    
    # Test outcome
    success: bool
    execution_time_ms: float
    start_time: datetime
    end_time: datetime
    
    # Test metrics
    signals_generated: int = 0
    positions_created: int = 0
    orders_placed: int = 0
    performance_score: float = 0.0
    
    # Inheritance metrics
    inheritance_depth: int = 0
    inheritance_conflicts: int = 0
    parent_templates: List[str] = field(default_factory=list)
    
    # Validation results
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    
    # Performance metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Detailed data
    test_data: Dict[str, Any] = field(default_factory=dict)

class TemplateTestFramework:
    """
    Core template testing framework with inheritance and category support
    """
    
    def __init__(self, template_registry: TemplateRegistry, 
                 core_engine: TemplateCoreEngine,
                 config: Optional[TemplateTestConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.core_engine = core_engine
        self.config = config or TemplateTestConfig()
        
        # Test state
        self.test_results: List[TemplateTestResult] = []
        self.active_tests: Dict[str, TemplateTestResult] = {}
        self.test_statistics: Dict[str, Any] = {}
        
        # Test data
        self.synthetic_market_data = None
        
        self.logger.info("TemplateTestFramework initialized")
    
    async def initialize(self):
        """Initialize the test framework"""
        
        self.logger.info("Initializing template test framework")
        
        # Generate synthetic test data if needed
        if self.config.use_synthetic_data:
            await self._generate_synthetic_data()
        
        # Initialize test statistics
        self.test_statistics = {
            'total_tests': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'categories_tested': set(),
            'templates_tested': set(),
            'avg_execution_time_ms': 0.0,
            'last_test_time': None
        }
        
        self.logger.info("Template test framework initialized")
    
    async def run_template_test(self, template_id: str, test_type: str = "standard") -> TemplateTestResult:
        """Run a comprehensive test on a single template"""
        
        test_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()
        
        try:
            # Get template
            template = self.template_registry.get_template(template_id)
            if not template:
                return TemplateTestResult(
                    test_id=test_id,
                    template_id=template_id,
                    template_category=TemplateCategory.BASE,
                    test_type=test_type,
                    execution_mode=self.config.execution_mode,
                    success=False,
                    execution_time_ms=0.0,
                    start_time=start_time,
                    end_time=datetime.now(),
                    errors=[f"Template {template_id} not found"]
                )
            
            self.logger.debug(f"Running test {test_id} for template {template_id}")
            
            # Create test result
            result = TemplateTestResult(
                test_id=test_id,
                template_id=template_id,
                template_category=template.metadata.category,
                test_type=test_type,
                execution_mode=self.config.execution_mode,
                success=False,
                execution_time_ms=0.0,
                start_time=start_time,
                end_time=start_time,
                parent_templates=template.metadata.parent_templates
            )
            
            # Add to active tests
            self.active_tests[test_id] = result
            
            # Run template execution test
            execution_result = await self.core_engine.execute_template_strategy(
                template_id, 
                self.synthetic_market_data or self._get_default_market_data()
            )
            
            # Process results
            result.success = execution_result.success
            result.execution_time_ms = execution_result.execution_time_ms
            result.signals_generated = len(execution_result.signals)
            result.positions_created = len(execution_result.positions)
            result.orders_placed = len(execution_result.orders)
            result.performance_score = execution_result.category_performance_score
            result.inheritance_depth = len(execution_result.inheritance_impact)
            result.end_time = datetime.now()
            
            if not execution_result.success:
                result.errors.extend(execution_result.errors)
                result.warnings.extend(execution_result.warnings)
            
            # Run additional tests if enabled
            if self.config.enable_inheritance_testing:
                await self._test_inheritance_behavior(result, template)
            
            if self.config.enable_validation_testing:
                await self._test_template_validation(result, template)
            
            if self.config.enable_performance_testing:
                await self._test_performance_thresholds(result)
            
            # Store test data
            result.test_data = {
                'template_metadata': {
                    'template_id': template.metadata.template_id,
                    'name': template.metadata.name,
                    'category': template.metadata.category.value,
                    'version': template.metadata.version
                },
                'template_parameters': template.parameters,
                'template_components': template.components,
                'execution_results': {
                    'signals': execution_result.signals,
                    'positions': execution_result.positions,
                    'inheritance_impact': execution_result.inheritance_impact
                }
            }
            
            # Update statistics
            self._update_test_statistics(result)
            
            self.logger.info(f"Test {test_id} completed: {'SUCCESS' if result.success else 'FAILED'}")
            
            return result
            
        except Exception as e:
            error_time = datetime.now()
            error_result = TemplateTestResult(
                test_id=test_id,
                template_id=template_id,
                template_category=TemplateCategory.BASE,
                test_type=test_type,
                execution_mode=self.config.execution_mode,
                success=False,
                execution_time_ms=(error_time - start_time).total_seconds() * 1000,
                start_time=start_time,
                end_time=error_time,
                errors=[f"Test execution failed: {str(e)}"]
            )
            
            self.logger.error(f"Test {test_id} failed with exception: {e}")
            self.logger.debug(traceback.format_exc())
            
            return error_result
            
        finally:
            # Remove from active tests
            if test_id in self.active_tests:
                del self.active_tests[test_id]
    
    async def run_category_tests(self, category: TemplateCategory) -> List[TemplateTestResult]:
        """Run tests for all templates in a category"""
        
        self.logger.info(f"Running category tests for {category.value}")
        
        # Get templates in category
        category_templates = []
        for template_id in self.template_registry.templates.keys():
            template = self.template_registry.get_template(template_id)
            if template and template.metadata.category == category:
                category_templates.append(template_id)
        
        if not category_templates:
            self.logger.warning(f"No templates found in category {category.value}")
            return []
        
        # Run tests for all templates in category
        results = []
        for template_id in category_templates:
            result = await self.run_template_test(template_id, f"category_{category.value}")
            results.append(result)
        
        self.logger.info(f"Category tests completed: {len(results)} templates tested")
        return results
    
    async def run_inheritance_chain_tests(self, template_id: str) -> List[TemplateTestResult]:
        """Run tests for template and its inheritance chain"""
        
        self.logger.info(f"Running inheritance chain tests for {template_id}")
        
        template = self.template_registry.get_template(template_id)
        if not template:
            return []
        
        # Build inheritance chain
        inheritance_chain = [template_id]
        inheritance_chain.extend(template.metadata.parent_templates)
        
        # Run tests for each template in chain
        results = []
        for chain_template_id in inheritance_chain:
            if self.template_registry.get_template(chain_template_id):
                result = await self.run_template_test(chain_template_id, "inheritance_chain")
                results.append(result)
        
        self.logger.info(f"Inheritance chain tests completed: {len(results)} templates tested")
        return results
    
    async def _test_inheritance_behavior(self, result: TemplateTestResult, template: BaseTemplate):
        """Test template inheritance behavior"""
        
        try:
            # Test inheritance depth
            if len(template.metadata.parent_templates) > self.config.max_inheritance_depth:
                result.validation_warnings.append(
                    f"Inheritance depth {len(template.metadata.parent_templates)} exceeds limit {self.config.max_inheritance_depth}"
                )
            
            # Test for inheritance conflicts (simplified)
            if self.config.test_inheritance_conflicts and template.metadata.parent_templates:
                for parent_id in template.metadata.parent_templates:
                    parent_template = self.template_registry.get_template(parent_id)
                    if parent_template:
                        # Check for parameter conflicts
                        for param_name in template.parameters:
                            if param_name in parent_template.parameters:
                                if template.parameters[param_name] != parent_template.parameters[param_name]:
                                    result.inheritance_conflicts += 1
            
        except Exception as e:
            result.validation_errors.append(f"Inheritance test failed: {e}")
    
    async def _test_template_validation(self, result: TemplateTestResult, template: BaseTemplate):
        """Test template validation"""
        
        try:
            # Basic validation checks
            if not template.metadata.template_id:
                result.validation_errors.append("Template ID is missing")
            
            if not template.metadata.name:
                result.validation_errors.append("Template name is missing")
            
            if not template.parameters:
                result.validation_warnings.append("Template has no parameters")
            
            if not template.components:
                result.validation_errors.append("Template has no components")
            
            # Category-specific validation
            if template.metadata.category == TemplateCategory.COMPOSITE:
                if len(template.metadata.parent_templates) == 0:
                    result.validation_warnings.append("Composite template has no parent templates")
            
            # Update validation status
            result.validation_passed = len(result.validation_errors) == 0
            
        except Exception as e:
            result.validation_errors.append(f"Template validation failed: {e}")
            result.validation_passed = False
    
    async def _test_performance_thresholds(self, result: TemplateTestResult):
        """Test against performance thresholds"""
        
        try:
            # Check execution time
            if result.execution_time_ms > self.config.max_execution_time_ms:
                result.validation_warnings.append(
                    f"Execution time {result.execution_time_ms:.2f}ms exceeds threshold {self.config.max_execution_time_ms}ms"
                )
            
            # Check performance score
            if result.performance_score < self.config.min_signal_quality:
                result.validation_warnings.append(
                    f"Performance score {result.performance_score:.3f} below threshold {self.config.min_signal_quality}"
                )
            
            # Check signal generation
            if result.signals_generated == 0:
                result.validation_warnings.append("No signals generated")
            
        except Exception as e:
            result.validation_errors.append(f"Performance test failed: {e}")
    
    def _update_test_statistics(self, result: TemplateTestResult):
        """Update test statistics"""
        
        self.test_statistics['total_tests'] += 1
        self.test_statistics['last_test_time'] = result.end_time
        
        if result.success:
            self.test_statistics['successful_tests'] += 1
        else:
            self.test_statistics['failed_tests'] += 1
        
        self.test_statistics['categories_tested'].add(result.template_category.value)
        self.test_statistics['templates_tested'].add(result.template_id)
        
        # Update average execution time
        total_time = (self.test_statistics['avg_execution_time_ms'] * (self.test_statistics['total_tests'] - 1) + 
                     result.execution_time_ms)
        self.test_statistics['avg_execution_time_ms'] = total_time / self.test_statistics['total_tests']
        
        # Store result
        self.test_results.append(result)
    
    async def _generate_synthetic_data(self):
        """Generate synthetic market data for testing"""
        
        symbols = self.config.market_data_symbols
        
        self.synthetic_market_data = {
            'symbols': symbols,
            'prices': {symbol: 100.0 + i * 50.0 for i, symbol in enumerate(symbols)},
            'volumes': {symbol: 1000000 + i * 500000 for i, symbol in enumerate(symbols)},
            'market_data': {
                'volatility': {symbol: 0.2 + i * 0.05 for i, symbol in enumerate(symbols)},
                'beta': {symbol: 1.0 + i * 0.2 for i, symbol in enumerate(symbols)},
                'sector_correlation': 0.7,
                'market_regime': 'normal',
                'volatility_regime': 'normal'
            },
            'timestamp': datetime.now()
        }
        
        self.logger.debug(f"Generated synthetic data for {len(symbols)} symbols")
    
    def _get_default_market_data(self) -> Dict[str, Any]:
        """Get default market data if synthetic data is not available"""
        
        return {
            'symbols': ['AAPL', 'GOOGL'],
            'prices': {'AAPL': 150.0, 'GOOGL': 2800.0},
            'volumes': {'AAPL': 1000000, 'GOOGL': 500000},
            'timestamp': datetime.now()
        }
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get comprehensive test summary"""
        
        if not self.test_results:
            return {
                'total_tests': 0, 
                'successful_tests': 0,
                'failed_tests': 0,
                'success_rate': 0.0,
                'avg_execution_time_ms': 0.0,
                'categories_tested': 0,
                'templates_tested': 0,
                'inheritance_tests': 0,
                'validation_failures': 0,
                'performance_warnings': 0,
                'total_signals': 0,
                'total_positions': 0,
                'message': 'No tests executed'
            }
        
        successful_tests = [r for r in self.test_results if r.success]
        failed_tests = [r for r in self.test_results if not r.success]
        
        summary = {
            'total_tests': len(self.test_results),
            'successful_tests': len(successful_tests),
            'failed_tests': len(failed_tests),
            'success_rate': len(successful_tests) / len(self.test_results) if self.test_results else 0.0,
            'avg_execution_time_ms': sum(r.execution_time_ms for r in self.test_results) / len(self.test_results),
            'categories_tested': len(self.test_statistics['categories_tested']),
            'templates_tested': len(self.test_statistics['templates_tested']),
            'inheritance_tests': len([r for r in self.test_results if r.inheritance_depth > 0]),
            'validation_failures': len([r for r in self.test_results if not r.validation_passed]),
            'performance_warnings': sum(len(r.validation_warnings) for r in self.test_results),
            'total_signals': sum(r.signals_generated for r in self.test_results),
            'total_positions': sum(r.positions_created for r in self.test_results)
        }
        
        return summary

class TemplateTestSuite:
    """
    Comprehensive test suite for template-based testing
    """
    
    def __init__(self, template_registry: TemplateRegistry, core_engine: TemplateCoreEngine):
        self.template_registry = template_registry
        self.core_engine = core_engine
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Test components
        self.test_framework = None
        self.inheritance_manager = None
        self.category_validator = None
    
    async def initialize(self):
        """Initialize the test suite"""
        
        config = TemplateTestConfig(
            execution_mode=TestExecutionMode.SINGLE_TEMPLATE,
            enable_performance_testing=True,
            enable_inheritance_testing=True,
            enable_validation_testing=True
        )
        
        self.test_framework = TemplateTestFramework(
            self.template_registry, 
            self.core_engine, 
            config
        )
        await self.test_framework.initialize()
        
        self.logger.info("Template test suite initialized")
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive template tests"""
        
        if not self.test_framework:
            await self.initialize()
        
        # Test all templates
        all_results = []
        for template_id in self.template_registry.templates.keys():
            result = await self.test_framework.run_template_test(template_id)
            all_results.append(result)
        
        return self.test_framework.get_test_summary()
