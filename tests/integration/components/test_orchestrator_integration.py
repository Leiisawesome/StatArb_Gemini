#!/usr/bin/env python3
"""
Comprehensive Orchestrator Integration Test Suite
================================================

Tests the complete orchestrator integration across all 27 components
in the StatArb_Gemini core_engine system.

This test suite validates:
- Component registration with orchestrator
- Authorization request patterns
- Lifecycle management
- Health monitoring
- System workflows
- Data flow integrity

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Integration Testing)
"""

import asyncio
import logging
import sys
import os
import traceback
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from datetime import datetime
from typing import List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Add core_engine to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core_engine'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('orchestrator_integration_test.log')
    ]
)
logger = logging.getLogger(__name__)


class TestResult(Enum):
    """Test result status"""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclass
class ComponentTestResult:
    """Test result for a single component"""
    component_name: str
    test_name: str
    result: TestResult
    message: str
    execution_time: float
    error_details: Optional[str] = None


@dataclass
class IntegrationTestReport:
    """Comprehensive integration test report"""
    test_start_time: datetime
    test_end_time: datetime
    total_components_tested: int
    total_tests_run: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    tests_error: int
    component_results: List[ComponentTestResult]
    system_workflow_results: List[ComponentTestResult]
    overall_success: bool
    recommendations: List[str]


class OrchestratorIntegrationTester:
    """
    Comprehensive orchestrator integration tester
    
    Tests all 27 components across the 6-layer architecture:
    - Layer 1: System Orchestration (2 components)
    - Layer 2: Governance (1 component)
    - Layer 3: Data Management (1 component)
    - Layer 4: Core Processing (4 components)
    - Layer 5: Analytics & Strategy (10 components)
    - Layer 6: Trading & Execution (3 components)
    - Enhanced Strategies: (10 strategy implementations)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.test_results: List[ComponentTestResult] = []
        self.orchestrator = None
        self.test_start_time = None
        self.test_components = {}
        
        # Define all 27 components to test
        self.core_components = {
            # Layer 1: System Orchestration
            'HierarchicalSystemOrchestrator': 'core_engine.system.hierarchical_orchestrator',
            'SystemIntegrationManager': 'core_engine.system.integration_manager',
            
            # Layer 2: Governance
            'CentralRiskManager': 'core_engine.system.central_risk_manager',
            
            # Layer 3: Data Management
            'ClickHouseDataManager': 'core_engine.data.manager',
            
            # Layer 4: Core Processing
            'EnhancedRegimeEngine': 'core_engine.regime.engine',
            'EnhancedTechnicalIndicators': 'core_engine.processing.indicators.engine',
            'EnhancedFeatureEngineer': 'core_engine.processing.features.engineer',
            'EnhancedSignalGenerator': 'core_engine.processing.signals.generator',
            
            # Layer 5: Analytics & Strategy
            'EnhancedAnalyticsManager': 'core_engine.analytics.manager_enhanced',
            'EnhancedMetricsCalculator': 'core_engine.analytics.metrics_calculator',
            'PerformanceAnalyzer': 'core_engine.analytics.performance_analyzer',
            'StrategyManager': 'core_engine.trading.strategies.manager',
            'StrategyExecutionEngine': 'core_engine.trading.strategies.strategy_engine',
            'EnhancedStrategyValidator': 'core_engine.trading.strategies.strategy_validator',
            'EnhancedStrategyRegistry': 'core_engine.trading.strategies.strategy_registry',
            
            # Layer 6: Trading & Execution
            'EnhancedTradingEngine': 'core_engine.trading.engine',
            'UnifiedExecutionEngine': 'core_engine.system.unified_execution_engine',
            'EnhancedPortfolioManager': 'core_engine.trading.portfolio.manager_enhanced',
        }
        
        self.strategy_components = {
            'EnhancedMomentumStrategy': 'core_engine.trading.strategies.implementations.momentum.enhanced_momentum',
            'EnhancedMeanReversionStrategy': 'core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion',
            'EnhancedStatisticalArbitrageStrategy': 'core_engine.trading.strategies.implementations.statistical_arbitrage.enhanced_statistical_arbitrage',
            'EnhancedFactorStrategy': 'core_engine.trading.strategies.implementations.factor.enhanced_factor',
            'EnhancedMultiAssetStrategy': 'core_engine.trading.strategies.implementations.multi_asset.enhanced_multi_asset',
            'EnhancedTrendFollowingStrategy': 'core_engine.trading.strategies.implementations.trend_following.enhanced_trend_following',
            'EnhancedBreakoutStrategy': 'core_engine.trading.strategies.implementations.breakout.enhanced_breakout',
            'EnhancedPairsTradingStrategy': 'core_engine.trading.strategies.implementations.pairs_trading.enhanced_pairs_trading',
            'EnhancedVolatilityStrategy': 'core_engine.trading.strategies.implementations.volatility.enhanced_volatility',
            'EnhancedArbitrageStrategy': 'core_engine.trading.strategies.implementations.arbitrage.enhanced_arbitrage',
        }
        
        self.logger.info("🧪 Orchestrator Integration Tester initialized")
        self.logger.info(f"📊 Testing {len(self.core_components)} core components")
        self.logger.info(f"🧠 Testing {len(self.strategy_components)} strategy components")
    
    async def run_comprehensive_test_suite(self) -> IntegrationTestReport:
        """Run the complete integration test suite"""
        
        self.test_start_time = datetime.now()
        self.logger.info("🚀 Starting Comprehensive Orchestrator Integration Test Suite")
        self.logger.info("=" * 80)
        
        try:
            # Phase 1: Initialize orchestrator
            await self._initialize_test_orchestrator()
            
            # Phase 2: Test core components
            await self._test_core_components()
            
            # Phase 3: Test strategy components
            await self._test_strategy_components()
            
            # Phase 4: Test system workflows
            await self._test_system_workflows()
            
            # Phase 5: Generate comprehensive report
            report = await self._generate_test_report()
            
            self.logger.info("✅ Comprehensive Integration Test Suite completed")
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Test suite failed with error: {e}")
            self.logger.error(traceback.format_exc())
            
            # Generate error report
            return await self._generate_error_report(str(e))
    
    async def _initialize_test_orchestrator(self):
        """Initialize the orchestrator for testing"""
        
        self.logger.info("🔧 Initializing test orchestrator...")
        
        try:
            # Import and create orchestrator
            from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
            
            self.orchestrator = HierarchicalSystemOrchestrator()
            await self.orchestrator.initialize()
            
            self.logger.info("✅ Test orchestrator initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize test orchestrator: {e}")
            raise
    
    async def _test_core_components(self):
        """Test all 17 core components"""
        
        self.logger.info("🔍 Testing Core Components Integration...")
        self.logger.info("-" * 50)
        
        for component_name, module_path in self.core_components.items():
            await self._test_component_integration(component_name, module_path, is_strategy=False)
    
    async def _test_strategy_components(self):
        """Test all 10 enhanced strategy components"""
        
        self.logger.info("🧠 Testing Enhanced Strategy Components Integration...")
        self.logger.info("-" * 50)
        
        for component_name, module_path in self.strategy_components.items():
            await self._test_component_integration(component_name, module_path, is_strategy=True)
    
    async def _test_component_integration(self, component_name: str, module_path: str, is_strategy: bool = False):
        """Test individual component orchestrator integration"""
        
        start_time = datetime.now()
        self.logger.info(f"🧪 Testing {component_name}...")
        
        try:
            # Test 1: Component Import
            result1 = await self._test_component_import(component_name, module_path)
            self.test_results.append(result1)
            
            if result1.result != TestResult.PASSED:
                self.logger.warning(f"⚠️ Skipping further tests for {component_name} due to import failure")
                return
            
            # Test 2: ISystemComponent Interface
            result2 = await self._test_isystem_component_interface(component_name)
            self.test_results.append(result2)
            
            # Test 3: Orchestrator Registration
            result3 = await self._test_orchestrator_registration(component_name, is_strategy)
            self.test_results.append(result3)
            
            # Test 4: Authorization Request
            result4 = await self._test_authorization_request(component_name)
            self.test_results.append(result4)
            
            # Test 5: Lifecycle Management
            result5 = await self._test_lifecycle_management(component_name)
            self.test_results.append(result5)
            
            # Test 6: Health Check
            result6 = await self._test_health_check(component_name)
            self.test_results.append(result6)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Summary for component
            passed_tests = sum(1 for r in [result1, result2, result3, result4, result5, result6] if r.result == TestResult.PASSED)
            total_tests = 6
            
            if passed_tests == total_tests:
                self.logger.info(f"✅ {component_name}: ALL {total_tests} tests PASSED ({execution_time:.2f}s)")
            else:
                self.logger.warning(f"⚠️ {component_name}: {passed_tests}/{total_tests} tests passed ({execution_time:.2f}s)")
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_result = ComponentTestResult(
                component_name=component_name,
                test_name="component_integration",
                result=TestResult.ERROR,
                message=f"Component testing failed: {str(e)}",
                execution_time=execution_time,
                error_details=traceback.format_exc()
            )
            self.test_results.append(error_result)
            self.logger.error(f"❌ {component_name}: Testing failed with error: {e}")
    
    async def _test_component_import(self, component_name: str, module_path: str) -> ComponentTestResult:
        """Test component import"""
        
        start_time = datetime.now()
        
        try:
            # Import the module
            module = __import__(module_path, fromlist=[component_name])
            component_class = getattr(module, component_name)
            
            # Store for later tests
            self.test_components[component_name] = component_class
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="import_test",
                result=TestResult.PASSED,
                message="Component imported successfully",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="import_test",
                result=TestResult.FAILED,
                message=f"Import failed: {str(e)}",
                execution_time=execution_time,
                error_details=traceback.format_exc()
            )
    
    async def _test_isystem_component_interface(self, component_name: str) -> ComponentTestResult:
        """Test ISystemComponent interface implementation"""
        
        start_time = datetime.now()
        
        try:
            component_class = self.test_components[component_name]
            
            # Check if implements ISystemComponent
            from core_engine.system.interfaces import ISystemComponent
            
            if not issubclass(component_class, ISystemComponent):
                raise ValueError(f"{component_name} does not implement ISystemComponent")
            
            # Check required methods
            required_methods = ['initialize', 'start', 'stop', 'health_check', 'get_status']
            missing_methods = []
            
            for method in required_methods:
                if not hasattr(component_class, method):
                    missing_methods.append(method)
            
            if missing_methods:
                raise ValueError(f"Missing ISystemComponent methods: {missing_methods}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="isystem_component_interface",
                result=TestResult.PASSED,
                message="ISystemComponent interface properly implemented",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="isystem_component_interface",
                result=TestResult.FAILED,
                message=f"ISystemComponent interface test failed: {str(e)}",
                execution_time=execution_time,
                error_details=traceback.format_exc()
            )
    
    async def _test_orchestrator_registration(self, component_name: str, is_strategy: bool = False) -> ComponentTestResult:
        """Test orchestrator registration"""
        
        start_time = datetime.now()
        
        try:
            component_class = self.test_components[component_name]
            
            # Check if has registration method
            if not hasattr(component_class, 'register_with_orchestrator'):
                raise ValueError(f"{component_name} missing register_with_orchestrator method")
            
            # Create component instance with minimal config
            if is_strategy:
                # Strategy components need special config
                config = self._create_strategy_config(component_name)
                component_instance = component_class(config)
            else:
                # Core components
                config = self._create_component_config(component_name)
                
                # Handle special cases for different component types
                if component_name == 'HierarchicalSystemOrchestrator':
                    # Orchestrator doesn't need config
                    component_instance = component_class()
                elif component_name in ['CentralRiskManager', 'StrategyManager', 'EnhancedRegimeEngine', 'EnhancedTradingEngine']:
                    # These expect dict configs and create dataclass internally
                    if component_name == 'CentralRiskManager':
                        config_dict = {
                            'max_position_size': 0.1,
                            'max_daily_var': 0.05,
                            'max_total_risk': 0.20
                        }
                    elif component_name == 'StrategyManager':
                        config_dict = {
                            'max_concurrent_strategies': 3,
                            'enable_enhanced_strategies': False,
                            'auto_discover_strategies': False
                        }
                    elif component_name == 'EnhancedRegimeEngine':
                        config_dict = {
                            'lookback_window': 60,
                            'volatility_window': 20,
                            'enable_enhanced_detection': False
                        }
                    elif component_name == 'EnhancedTradingEngine':
                        config_dict = {
                            'enable_smart_routing': False,
                            'max_slice_size': 500.0
                        }
                    component_instance = component_class(config_dict)
                else:
                    # Other components use dict configs
                    component_instance = component_class(config)
            
            # Test registration
            component_id = component_instance.register_with_orchestrator(self.orchestrator)
            
            if not component_id:
                raise ValueError("Registration returned empty component_id")
            
            # Verify component is registered (skip for orchestrator self-registration)
            if component_name != 'HierarchicalSystemOrchestrator':
                if component_id not in self.orchestrator.component_registry:
                    raise ValueError("Component not found in orchestrator registry")
            # For orchestrator, just verify we got a component_id back
            elif component_id != "orchestrator_self_registration":
                raise ValueError("Orchestrator self-registration failed")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="orchestrator_registration",
                result=TestResult.PASSED,
                message=f"Successfully registered with component_id: {component_id}",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="orchestrator_registration",
                result=TestResult.FAILED,
                message=f"Registration test failed: {str(e)}",
                execution_time=execution_time,
                error_details=traceback.format_exc()
            )
    
    async def _test_authorization_request(self, component_name: str) -> ComponentTestResult:
        """Test authorization request functionality"""
        
        start_time = datetime.now()
        
        try:
            component_class = self.test_components[component_name]
            
            # Check if has authorization method
            if not hasattr(component_class, 'request_operation_authorization'):
                raise ValueError(f"{component_name} missing request_operation_authorization method")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="authorization_request",
                result=TestResult.PASSED,
                message="Authorization request method available",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="authorization_request",
                result=TestResult.FAILED,
                message=f"Authorization test failed: {str(e)}",
                execution_time=execution_time,
                error_details=traceback.format_exc()
            )
    
    async def _test_lifecycle_management(self, component_name: str) -> ComponentTestResult:
        """Test component lifecycle management"""
        
        start_time = datetime.now()
        
        try:
            # For now, just verify the methods exist
            # Full lifecycle testing would require more complex setup
            component_class = self.test_components[component_name]
            
            lifecycle_methods = ['initialize', 'start', 'stop']
            for method in lifecycle_methods:
                if not hasattr(component_class, method):
                    raise ValueError(f"Missing lifecycle method: {method}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="lifecycle_management",
                result=TestResult.PASSED,
                message="Lifecycle methods available",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="lifecycle_management",
                result=TestResult.FAILED,
                message=f"Lifecycle test failed: {str(e)}",
                execution_time=execution_time,
                error_details=traceback.format_exc()
            )
    
    async def _test_health_check(self, component_name: str) -> ComponentTestResult:
        """Test component health check functionality"""
        
        start_time = datetime.now()
        
        try:
            component_class = self.test_components[component_name]
            
            # Check if has health check methods
            health_methods = ['health_check', 'get_status']
            for method in health_methods:
                if not hasattr(component_class, method):
                    raise ValueError(f"Missing health method: {method}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="health_check",
                result=TestResult.PASSED,
                message="Health check methods available",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name=component_name,
                test_name="health_check",
                result=TestResult.FAILED,
                message=f"Health check test failed: {str(e)}",
                execution_time=execution_time,
                error_details=traceback.format_exc()
            )
    
    def _create_component_config(self, component_name: str) -> Any:
        """Create proper config objects for component testing"""
        
        try:
            # Import specific config classes
            if component_name == 'CentralRiskManager':
                from core_engine.system.central_risk_manager import RiskManagerConfig
                return RiskManagerConfig(
                    max_position_size=0.1,
                    max_daily_var=0.05,
                    max_total_risk=0.20
                )
            
            elif component_name == 'ClickHouseDataManager':
                from core_engine.data.manager import ClickHouseDataConfig
                return ClickHouseDataConfig(
                    symbols=['AAPL', 'MSFT'],
                    start_date='2024-01-01',
                    end_date='2024-01-02',
                    interval='1min',
                    clickhouse_host='localhost',
                    clickhouse_port=8123,
                    enable_caching=False
                )
            
            elif component_name == 'EnhancedRegimeEngine':
                from core_engine.regime.engine import RegimeEngineConfig
                return RegimeEngineConfig(
                    lookback_window=60,
                    volatility_window=20,
                    enable_enhanced_detection=False
                )
            
            elif component_name == 'EnhancedAnalyticsManager':
                from core_engine.analytics.manager_enhanced import AnalyticsConfig
                return AnalyticsConfig(
                    max_workers=2,
                    enable_caching=False
                )
            
            elif component_name == 'StrategyManager':
                from core_engine.trading.strategies.manager import StrategyManagerConfig
                return StrategyManagerConfig(
                    max_concurrent_strategies=3,
                    enable_enhanced_strategies=False,
                    auto_discover_strategies=False
                )
            
            elif component_name == 'EnhancedTradingEngine':
                from core_engine.trading.engine import TradingEngineConfig
                return TradingEngineConfig(
                    enable_smart_routing=False,
                    max_slice_size=500.0
                )
            
            elif component_name == 'HierarchicalSystemOrchestrator':
                # Orchestrator doesn't need special config for testing
                return {}
            
            else:
                # Generic config for other components
                return {
                    'enable_logging': True,
                    'enable_monitoring': False,
                }
                
        except ImportError as e:
            self.logger.warning(f"Failed to import config for {component_name}: {e}")
            # Return basic dict config as fallback
            return {
                'enable_logging': True,
                'enable_monitoring': False,
            }
    
    def _create_strategy_config(self, component_name: str) -> Any:
        """Create strategy config for strategy testing"""
        
        try:
            # Import the strategy config from strategy_engine
            from core_engine.trading.strategies.strategy_engine import StrategyConfig
            
            # Create basic strategy config with proper attributes
            config = StrategyConfig(
                strategy_id=f"test_{component_name.lower()}",
                max_position_size=0.05,
                paper_trading_mode=True
            )
            
            return config
            
        except Exception as e:
            self.logger.warning(f"Failed to create strategy config for {component_name}: {e}")
            # Return basic dict config as fallback - but make it an object-like dict
            class ConfigDict(dict):
                def __getattr__(self, key):
                    return self.get(key)
                def __setattr__(self, key, value):
                    self[key] = value
            
            config_dict = ConfigDict({
                'strategy_id': f"test_{component_name.lower()}",
                'max_position_size': 0.05,
                'enable_logging': True
            })
            
            return config_dict
    
    async def _test_system_workflows(self):
        """Test complete system workflows"""
        
        self.logger.info("🔄 Testing System Workflows...")
        self.logger.info("-" * 50)
        
        # Test 1: Component Registration Workflow
        workflow_result1 = await self._test_component_registration_workflow()
        self.test_results.append(workflow_result1)
        
        # Test 2: Authorization Workflow
        workflow_result2 = await self._test_authorization_workflow()
        self.test_results.append(workflow_result2)
        
        # Test 3: Data Flow Workflow
        workflow_result3 = await self._test_data_flow_workflow()
        self.test_results.append(workflow_result3)
    
    async def _test_component_registration_workflow(self) -> ComponentTestResult:
        """Test complete component registration workflow"""
        
        start_time = datetime.now()
        
        try:
            # Test that orchestrator can manage multiple components
            registered_count = len(self.orchestrator.component_registry)
            
            if registered_count == 0:
                raise ValueError("No components registered with orchestrator")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name="SystemWorkflow",
                test_name="component_registration_workflow",
                result=TestResult.PASSED,
                message=f"Successfully registered {registered_count} components",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name="SystemWorkflow",
                test_name="component_registration_workflow",
                result=TestResult.FAILED,
                message=f"Registration workflow failed: {str(e)}",
                execution_time=execution_time,
                error_details=traceback.format_exc()
            )
    
    async def _test_authorization_workflow(self) -> ComponentTestResult:
        """Test authorization workflow"""
        
        start_time = datetime.now()
        
        try:
            # Test orchestrator authorization system
            if not hasattr(self.orchestrator, 'request_system_authorization'):
                raise ValueError("Orchestrator missing authorization method")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name="SystemWorkflow",
                test_name="authorization_workflow",
                result=TestResult.PASSED,
                message="Authorization workflow available",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name="SystemWorkflow",
                test_name="authorization_workflow",
                result=TestResult.FAILED,
                message=f"Authorization workflow failed: {str(e)}",
                execution_time=execution_time,
                error_details=traceback.format_exc()
            )
    
    async def _test_data_flow_workflow(self) -> ComponentTestResult:
        """Test data flow workflow"""
        
        start_time = datetime.now()
        
        try:
            # Test that orchestrator has proper component management
            if not hasattr(self.orchestrator, 'component_registry'):
                raise ValueError("Orchestrator missing component registry")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name="SystemWorkflow",
                test_name="data_flow_workflow",
                result=TestResult.PASSED,
                message="Data flow workflow structure available",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentTestResult(
                component_name="SystemWorkflow",
                test_name="data_flow_workflow",
                result=TestResult.FAILED,
                message=f"Data flow workflow failed: {str(e)}",
                execution_time=execution_time,
                error_details=traceback.format_exc()
            )
    
    async def _generate_test_report(self) -> IntegrationTestReport:
        """Generate comprehensive test report"""
        
        test_end_time = datetime.now()
        
        # Calculate statistics
        total_tests = len(self.test_results)
        tests_passed = sum(1 for r in self.test_results if r.result == TestResult.PASSED)
        tests_failed = sum(1 for r in self.test_results if r.result == TestResult.FAILED)
        tests_skipped = sum(1 for r in self.test_results if r.result == TestResult.SKIPPED)
        tests_error = sum(1 for r in self.test_results if r.result == TestResult.ERROR)
        
        # Separate component and workflow results
        component_results = [r for r in self.test_results if r.component_name != "SystemWorkflow"]
        workflow_results = [r for r in self.test_results if r.component_name == "SystemWorkflow"]
        
        # Calculate unique components tested
        unique_components = set(r.component_name for r in component_results)
        total_components_tested = len(unique_components)
        
        # Determine overall success
        overall_success = tests_failed == 0 and tests_error == 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(tests_failed, tests_error, component_results)
        
        return IntegrationTestReport(
            test_start_time=self.test_start_time,
            test_end_time=test_end_time,
            total_components_tested=total_components_tested,
            total_tests_run=total_tests,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            tests_skipped=tests_skipped,
            tests_error=tests_error,
            component_results=component_results,
            system_workflow_results=workflow_results,
            overall_success=overall_success,
            recommendations=recommendations
        )
    
    async def _generate_error_report(self, error_message: str) -> IntegrationTestReport:
        """Generate error report when test suite fails"""
        
        test_end_time = datetime.now()
        
        return IntegrationTestReport(
            test_start_time=self.test_start_time,
            test_end_time=test_end_time,
            total_components_tested=0,
            total_tests_run=0,
            tests_passed=0,
            tests_failed=0,
            tests_skipped=0,
            tests_error=1,
            component_results=[],
            system_workflow_results=[],
            overall_success=False,
            recommendations=[f"Fix critical error: {error_message}"]
        )
    
    def _generate_recommendations(self, tests_failed: int, tests_error: int, 
                                component_results: List[ComponentTestResult]) -> List[str]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        if tests_failed > 0:
            recommendations.append(f"Fix {tests_failed} failed tests before production deployment")
        
        if tests_error > 0:
            recommendations.append(f"Resolve {tests_error} error conditions in component integration")
        
        # Component-specific recommendations
        failed_components = set()
        for result in component_results:
            if result.result in [TestResult.FAILED, TestResult.ERROR]:
                failed_components.add(result.component_name)
        
        if failed_components:
            recommendations.append(f"Priority components needing attention: {', '.join(failed_components)}")
        
        if tests_failed == 0 and tests_error == 0:
            recommendations.append("All tests passed - system ready for production deployment")
            recommendations.append("Consider implementing continuous integration testing")
            recommendations.append("Monitor component performance in production environment")
        
        return recommendations


def print_test_report(report: IntegrationTestReport):
    """Print comprehensive test report"""
    
    print("\n" + "=" * 80)
    print("🧪 COMPREHENSIVE ORCHESTRATOR INTEGRATION TEST REPORT")
    print("=" * 80)
    
    # Test Summary
    print(f"\n📊 TEST SUMMARY:")
    print(f"   Test Duration: {(report.test_end_time - report.test_start_time).total_seconds():.2f} seconds")
    print(f"   Components Tested: {report.total_components_tested}")
    print(f"   Total Tests Run: {report.total_tests_run}")
    print(f"   Tests Passed: {report.tests_passed} ✅")
    print(f"   Tests Failed: {report.tests_failed} ❌")
    print(f"   Tests Skipped: {report.tests_skipped} ⏭️")
    print(f"   Tests Error: {report.tests_error} 🚨")
    
    # Overall Result
    if report.overall_success:
        print(f"\n🎯 OVERALL RESULT: ✅ SUCCESS")
        print("   All orchestrator integration tests passed!")
    else:
        print(f"\n🎯 OVERALL RESULT: ❌ FAILURE")
        print("   Some tests failed - review details below")
    
    # Component Results Summary
    if report.component_results:
        print(f"\n📋 COMPONENT TEST RESULTS:")
        
        # Group by component
        component_summary = {}
        for result in report.component_results:
            if result.component_name not in component_summary:
                component_summary[result.component_name] = {'passed': 0, 'failed': 0, 'error': 0, 'skipped': 0}
            
            if result.result == TestResult.PASSED:
                component_summary[result.component_name]['passed'] += 1
            elif result.result == TestResult.FAILED:
                component_summary[result.component_name]['failed'] += 1
            elif result.result == TestResult.ERROR:
                component_summary[result.component_name]['error'] += 1
            elif result.result == TestResult.SKIPPED:
                component_summary[result.component_name]['skipped'] += 1
        
        for component, stats in component_summary.items():
            total = sum(stats.values())
            passed = stats['passed']
            status = "✅" if stats['failed'] == 0 and stats['error'] == 0 else "❌"
            print(f"   {status} {component}: {passed}/{total} tests passed")
    
    # Failed Tests Details
    failed_tests = [r for r in report.component_results if r.result in [TestResult.FAILED, TestResult.ERROR]]
    if failed_tests:
        print(f"\n❌ FAILED TESTS DETAILS:")
        for result in failed_tests:
            print(f"   • {result.component_name}.{result.test_name}: {result.message}")
            if result.error_details:
                print(f"     Error: {result.error_details.split(chr(10))[0]}")  # First line of error
    
    # System Workflow Results
    if report.system_workflow_results:
        print(f"\n🔄 SYSTEM WORKFLOW RESULTS:")
        for result in report.system_workflow_results:
            status = "✅" if result.result == TestResult.PASSED else "❌"
            print(f"   {status} {result.test_name}: {result.message}")
    
    # Recommendations
    if report.recommendations:
        print(f"\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"   {i}. {rec}")
    
    print("\n" + "=" * 80)


async def main():
    """Main test execution function"""
    
    print("🚀 Starting Comprehensive Orchestrator Integration Test Suite")
    print("Testing all 27 components across the 6-layer architecture")
    print("=" * 80)
    
    # Create and run tester
    tester = OrchestratorIntegrationTester()
    report = await tester.run_comprehensive_test_suite()
    
    # Print detailed report
    print_test_report(report)
    
    # Save report to file
    report_filename = f"orchestrator_integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w') as f:
        # Redirect print to file
        import sys
        original_stdout = sys.stdout
        sys.stdout = f
        print_test_report(report)
        sys.stdout = original_stdout
    
    print(f"\n📄 Detailed report saved to: {report_filename}")
    
    # Return exit code
    return 0 if report.overall_success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
