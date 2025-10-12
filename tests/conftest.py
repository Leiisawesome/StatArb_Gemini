"""
Pytest Configuration and Fixtures for StatArb_Gemini Core Engine Testing
Comprehensive test configuration with async support and system initialization
"""

import pytest
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, AsyncGenerator
from unittest.mock import Mock, AsyncMock

# Core engine imports
from core_engine.system.integration_manager import SystemIntegrationManager
from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
from core_engine.data.manager import ClickHouseDataManager
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.system.central_risk_manager import CentralRiskManager

# Performance testing imports
from tests.performance.benchmarks.latency_testing import LatencyProfiler
from tests.performance.profiling.memory_profiling import MemoryProfiler
from tests.performance.benchmarks.throughput_benchmarking import ThroughputBenchmarker
from tests.performance.tests.test_performance_suite import PerformanceTestSuite

# Import centralized fixtures
# Note: Only import fixtures that don't have dependency issues
pytest_plugins = [
    'tests.fixtures.core_fixtures',
    'tests.fixtures.data_fixtures',
    # 'tests.fixtures.integration_fixtures',  # Has import dependencies
    # 'tests.fixtures.strategy_fixtures',  # Has import dependencies
]

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_system() -> AsyncGenerator[SystemIntegrationManager, None]:
    """Initialize test system for all tests"""
    logger.info("🔧 Initializing test system...")
    
    try:
        system = SystemIntegrationManager()
        await system.initialize()
        
        logger.info("✅ Test system initialized successfully")
        yield system
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize test system: {e}")
        raise
    finally:
        try:
            await system.shutdown()
            logger.info("🧹 Test system shutdown completed")
        except Exception as e:
            logger.error(f"❌ Test system shutdown failed: {e}")

@pytest.fixture(scope="session")
async def test_orchestrator() -> AsyncGenerator[HierarchicalSystemOrchestrator, None]:
    """Initialize test orchestrator for all tests"""
    logger.info("🎭 Initializing test orchestrator...")
    
    try:
        orchestrator = HierarchicalSystemOrchestrator()
        await orchestrator.initialize()
        
        logger.info("✅ Test orchestrator initialized successfully")
        yield orchestrator
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize test orchestrator: {e}")
        raise
    finally:
        try:
            await orchestrator.shutdown()
            logger.info("🧹 Test orchestrator shutdown completed")
        except Exception as e:
            logger.error(f"❌ Test orchestrator shutdown failed: {e}")

@pytest.fixture(scope="function")
async def mock_data_manager() -> Mock:
    """Mock data manager for testing"""
    mock_manager = Mock(spec=ClickHouseDataManager)
    mock_manager.get_market_data = AsyncMock(return_value={
        'timestamp': datetime.now(),
        'symbol': 'TEST',
        'price': 100.0,
        'volume': 1000
    })
    mock_manager.load_market_data = AsyncMock(return_value=[])
    return mock_manager

@pytest.fixture(scope="function")
async def mock_regime_engine() -> Mock:
    """Mock regime engine for testing"""
    mock_engine = Mock(spec=EnhancedRegimeEngine)
    mock_engine.get_current_regime = AsyncMock(return_value={
        'primary_regime': 'normal_volatility',
        'confidence': 0.8,
        'volatility': 0.15
    })
    mock_engine.on_market_data = AsyncMock()
    return mock_engine

@pytest.fixture(scope="function")
async def mock_risk_manager() -> Mock:
    """Mock risk manager for testing"""
    mock_risk = Mock(spec=CentralRiskManager)
    mock_risk.authorize_trading_decision = AsyncMock(return_value={
        'authorization_level': 'AUTOMATIC',
        'authorized_quantity': 100,
        'risk_score': 0.3
    })
    mock_risk.get_risk_status = AsyncMock(return_value={
        'emergency_mode': False,
        'risk_level': 'NORMAL'
    })
    return mock_risk

@pytest.fixture(scope="function")
def test_market_data() -> Dict[str, Any]:
    """Test market data for performance testing"""
    return {
        'timestamp': datetime.now(),
        'symbol': 'NVDA',
        'open': 100.0,
        'high': 105.0,
        'low': 95.0,
        'close': 102.0,
        'volume': 1000000,
        'data_type': 'market_data'
    }

@pytest.fixture(scope="function")
def test_configuration() -> Dict[str, Any]:
    """Test configuration for performance testing"""
    return {
        'test_timeout': 300,
        'retry_attempts': 3,
        'parallel_tests': False,
        'performance_standards': {
            'latency_p99_ms': 10.0,
            'latency_p95_ms': 5.0,
            'memory_efficiency_score': 85.0,
            'throughput_ops_per_sec': 1000.0
        },
        'stress_test_standards': {
            'market_stress_success_rate': 0.95,
            'component_failure_recovery_rate': 0.99,
            'load_stress_performance_retention': 0.80
        }
    }

@pytest.fixture(scope="function")
def latency_profiler() -> LatencyProfiler:
    """Latency profiler for performance testing"""
    return LatencyProfiler(max_samples=10000)

@pytest.fixture(scope="function")
def memory_profiler() -> MemoryProfiler:
    """Memory profiler for performance testing"""
    return MemoryProfiler(snapshot_interval=0.5, max_snapshots=10000)

@pytest.fixture(scope="function")
def throughput_benchmarker() -> ThroughputBenchmarker:
    """Throughput benchmarker for performance testing"""
    return ThroughputBenchmarker(max_measurements=5000)

@pytest.fixture(scope="function")
def performance_test_suite() -> PerformanceTestSuite:
    """Performance test suite for comprehensive testing"""
    return PerformanceTestSuite()

@pytest.fixture(scope="function")
def test_components(test_system, test_orchestrator, mock_data_manager, mock_regime_engine, mock_risk_manager):
    """All test components for integration testing"""
    return {
        'system': test_system,
        'orchestrator': test_orchestrator,
        'data_manager': mock_data_manager,
        'regime_engine': mock_regime_engine,
        'risk_manager': mock_risk_manager
    }

@pytest.fixture(scope="function")
def performance_test_runner(test_configuration):
    """Performance test runner for comprehensive testing"""
    from tests.performance.runners.test_runner import PerformanceTestRunner
    return PerformanceTestRunner(test_configuration)

# Test data generators
@pytest.fixture(scope="function")
def generate_test_data():
    """Generator function for creating test data"""
    def _generate_data(count: int = 100) -> list:
        data = []
        for i in range(count):
            data.append({
                'timestamp': datetime.now(),
                'symbol': f'TEST{i % 10}',
                'price': 100.0 + (i % 50),
                'volume': 1000 + (i % 1000),
                'data_type': 'test_data'
            })
        return data
    return _generate_data

@pytest.fixture(scope="function")
def generate_market_scenarios():
    """Generator function for creating market scenarios"""
    def _generate_scenarios() -> list:
        scenarios = [
            {
                'name': 'bull_market',
                'volatility': 0.15,
                'trend': 0.05,
                'liquidity': 'high'
            },
            {
                'name': 'bear_market',
                'volatility': 0.25,
                'trend': -0.08,
                'liquidity': 'normal'
            },
            {
                'name': 'sideways_market',
                'volatility': 0.12,
                'trend': 0.0,
                'liquidity': 'normal'
            },
            {
                'name': 'volatile_market',
                'volatility': 0.35,
                'trend': 0.02,
                'liquidity': 'low'
            },
            {
                'name': 'crisis_market',
                'volatility': 0.50,
                'trend': -0.15,
                'liquidity': 'crisis'
            }
        ]
        return scenarios
    return _generate_scenarios

# Async test utilities
@pytest.fixture(scope="function")
async def async_test_environment():
    """Async test environment setup"""
    # Setup async environment
    yield
    # Cleanup async environment

# Test markers and configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "stress: mark test as stress test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "compliance: mark test as compliance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers"""
    for item in items:
        # Add performance marker to performance tests
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
        
        # Add stress marker to stress tests
        if "stress" in item.nodeid:
            item.add_marker(pytest.mark.stress)
        
        # Add integration marker to integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Add compliance marker to compliance tests
        if "compliance" in item.nodeid:
            item.add_marker(pytest.mark.compliance)
        
        # Add slow marker to tests that take > 5 seconds
        if hasattr(item, 'function') and hasattr(item.function, '__name__'):
            if 'slow' in item.function.__name__ or 'comprehensive' in item.function.__name__:
                item.add_marker(pytest.mark.slow)

# Test reporting configuration (optional - requires pytest-html plugin)
# Commented out because pytest-html is not installed
# try:
#     def pytest_html_report_title(report):
#         """Customize HTML report title"""
#         report.title = "StatArb_Gemini Core Engine Test Report"

#     def pytest_html_results_table_header(cells):
#         """Customize HTML report table header"""
#         from pytest_html import html
#         cells.pop()  # Remove the default 'Links' column
#         cells.insert(0, html.th('Test Name'))
#         cells.insert(1, html.th('Duration'))
#         cells.insert(2, html.th('Status'))

#     def pytest_html_results_table_row(report, cells):
#         """Customize HTML report table rows"""
#         from pytest_html import html
#         cells.pop()  # Remove the default 'Links' column
#         cells.insert(0, html.td(report.test_name))
#         cells.insert(1, html.td(f"{report.duration:.2f}s"))
#         cells.insert(2, html.td('PASS' if report.passed else 'FAIL'))
# except ImportError:
#     # pytest-html not installed, skip HTML report customization
#     pass

# Test session configuration
@pytest.fixture(scope="session", autouse=True)
def setup_test_session():
    """Setup test session with logging and configuration"""
    logger.info("🚀 Starting StatArb_Gemini Core Engine Test Session")
    yield
    logger.info("🏁 StatArb_Gemini Core Engine Test Session Completed")

# Performance test configuration
@pytest.fixture(scope="session")
def performance_test_config():
    """Configuration for performance tests"""
    return {
        'latency_standards': {
            'p99_max_ms': 10.0,
            'p95_max_ms': 5.0,
            'p999_max_ms': 20.0
        },
        'memory_standards': {
            'efficiency_min_score': 85.0,
            'max_leaks': 0,
            'max_growth_mb': 100.0
        },
        'throughput_standards': {
            'min_ops_per_sec': 1000.0,
            'success_rate_min': 0.95,
            'error_rate_max': 0.05
        }
    }

# Stress test configuration
@pytest.fixture(scope="session")
def stress_test_config():
    """Configuration for stress tests"""
    return {
        'market_stress_scenarios': [
            'bull_market', 'bear_market', 'sideways_market',
            'volatile_market', 'crisis_market'
        ],
        'component_failure_scenarios': [
            'graceful_failure', 'sudden_failure', 'partial_failure'
        ],
        'load_stress_levels': [1, 2, 5, 10, 20],  # Multipliers
        'recovery_time_max_seconds': 30
    }

# Compliance test configuration
@pytest.fixture(scope="session")
def compliance_test_config():
    """Configuration for compliance tests"""
    return {
        'regulatory_standards': [
            'SEC', 'FINRA', 'MIFID_II', 'CFTC', 'ESMA'
        ],
        'compliance_thresholds': {
            'position_concentration_max': 0.05,  # 5%
            'var_limit_max': 0.05,  # 5%
            'leverage_max': 10.0,
            'liquidity_min': 0.1  # 10%
        },
        'reporting_requirements': [
            'real_time_trade_reporting',
            'position_reporting',
            'risk_reporting',
            'compliance_reporting'
        ]
    }
