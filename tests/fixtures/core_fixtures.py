"""
Core Component Fixtures - Institutional Testing Standards
=========================================================

Fixtures for core system components following hedge fund testing best practices.
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.config.component_config import RiskConfig  # Updated: use centralized config
from core_engine.system.unified_execution_engine import UnifiedExecutionEngine
from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
from core_engine.trading.strategies.manager import StrategyManager
from core_engine.analytics.metrics_calculator import EnhancedMetricsCalculator


# ========================================
# RISK MANAGER FIXTURES
# ========================================

@pytest.fixture
def risk_manager_config() -> Dict[str, Any]:
    """Standard risk manager configuration for testing"""
    return {
        'max_position_size': 0.10,
        'max_daily_var': 0.05,
        'max_total_risk': 0.20,
        'position_concentration_limit': 0.15,
        'strategy_allocation_limit': 0.33,
        'min_signal_confidence': 0.6,
        'high_confidence_threshold': 0.8,
        'auto_approval_threshold': 0.01,
        'elevated_review_threshold': 0.05,
        'emergency_threshold': 0.10,
        'real_time_monitoring': False,  # Disable monitoring in tests
    }


@pytest.fixture
async def risk_manager_fixture(risk_manager_config):
    """Initialized CentralRiskManager fixture"""
    manager = CentralRiskManager(risk_manager_config)
    await manager.initialize()
    yield manager
    # Cleanup
    try:
        await manager.stop()
    except:
        pass


@pytest.fixture
def mock_risk_manager():
    """Mock CentralRiskManager for isolated testing"""
    mock = Mock(spec=CentralRiskManager)
    mock.config = Mock(spec=RiskConfig)  # Updated: use centralized RiskConfig
    mock.config.min_signal_confidence = 0.6
    mock.config.max_position_size = 0.10
    mock.is_initialized = True
    mock.is_operational = True
    mock.emergency_mode = False

    # Mock methods
    mock.authorize_trading_decision = AsyncMock(return_value=Mock(
        authorization_level='automatic',
        authorized_quantity=100.0,
        is_valid=True
    ))
    mock.validate_position_limits = Mock(return_value=(True, []))
    mock.calculate_risk_metrics = Mock(return_value={
        'total_exposure': 0.5,
        'var_utilization': 0.3,
        'concentration_risk': 0.2
    })

    return mock


# ========================================
# STRATEGY MANAGER FIXTURES
# ========================================

@pytest.fixture
def strategy_manager_config() -> Dict[str, Any]:
    """Standard strategy manager configuration"""
    return {
        'max_concurrent_strategies': 5,
        'signal_generation_interval': 60,
        'min_confidence_threshold': 0.6,
        'max_strategy_allocation': 0.33,
        'enable_regime_awareness': True,
        'enable_correlation_filtering': True,
        'signal_aggregation_method': 'weighted_average',
        'enable_enhanced_strategies': True,
        'auto_discover_strategies': False,  # Disable in tests
        'strategy_registry_path': '/tmp/test_strategy_registry.json'
    }


@pytest.fixture
async def strategy_manager_fixture(strategy_manager_config):
    """Initialized StrategyManager fixture"""
    manager = StrategyManager(strategy_manager_config)
    await manager.initialize()
    yield manager
    # Cleanup
    try:
        await manager.stop()
    except:
        pass


@pytest.fixture
def mock_strategy_manager():
    """Mock StrategyManager for isolated testing"""
    mock = Mock(spec=StrategyManager)
    mock.is_initialized = True
    mock.is_running = True
    mock.active_strategies = {}

    # Mock methods
    mock.generate_signals = AsyncMock(return_value=[])
    mock.add_strategy = AsyncMock(return_value=True)
    mock.remove_strategy = AsyncMock(return_value=True)
    mock.get_strategy_performance = Mock(return_value={
        'total_return': 0.05,
        'sharpe_ratio': 1.2,
        'win_rate': 0.6
    })

    return mock


# ========================================
# EXECUTION ENGINE FIXTURES
# ========================================

@pytest.fixture
def execution_engine_config() -> Dict[str, Any]:
    """Standard execution engine configuration"""
    return {
        'default_algorithm': 'adaptive',
        'max_execution_time': 3600,
        'enable_smart_routing': True,
        'max_slippage': 0.001,
        'commission_rate': 0.0005,
        'enable_monitoring': False  # Disable in tests
    }


@pytest.fixture
async def execution_engine_fixture(execution_engine_config):
    """Initialized UnifiedExecutionEngine fixture"""
    engine = UnifiedExecutionEngine(execution_engine_config)
    await engine.initialize()
    yield engine
    # Cleanup
    try:
        await engine.stop()
    except:
        pass


@pytest.fixture
def mock_execution_engine():
    """Mock UnifiedExecutionEngine for isolated testing"""
    mock = Mock(spec=UnifiedExecutionEngine)
    mock.is_initialized = True

    # Mock methods
    mock.execute_order = AsyncMock(return_value=Mock(
        status='filled',
        filled_quantity=100.0,
        avg_fill_price=100.0,
        total_cost=10000.0
    ))
    mock.cancel_order = AsyncMock(return_value=True)
    mock.get_execution_status = Mock(return_value='filled')

    return mock


# ========================================
# ORCHESTRATOR FIXTURES
# ========================================

@pytest.fixture
def orchestrator_config() -> Dict[str, Any]:
    """Standard orchestrator configuration"""
    return {
        'health_check_interval': 5,
        'max_concurrent_operations': 10,
        'enable_monitoring': False,  # Disable in tests
        'component_startup_timeout': 30
    }


@pytest.fixture
async def orchestrator_fixture(orchestrator_config):
    """Initialized HierarchicalSystemOrchestrator fixture"""
    orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)
    await orchestrator.initialize_system()
    yield orchestrator
    # Cleanup
    try:
        await orchestrator.shutdown_system()
    except:
        pass


@pytest.fixture
def mock_orchestrator():
    """Mock HierarchicalSystemOrchestrator for isolated testing"""
    mock = Mock(spec=HierarchicalSystemOrchestrator)
    mock.system_status = 'operational'
    mock.component_registry = {}

    # Mock methods
    mock.register_component = Mock(return_value='test_component_id')
    mock.initialize_system = AsyncMock(return_value=True)
    mock.shutdown_system = AsyncMock(return_value=True)
    mock.get_system_health = Mock(return_value={
        'healthy': True,
        'component_count': 5,
        'operational_components': 5
    })

    return mock


# ========================================
# ANALYTICS FIXTURES
# ========================================

@pytest.fixture
def metrics_calculator_config() -> Dict[str, Any]:
    """Standard metrics calculator configuration"""
    return {
        'risk_free_rate': 0.02,
        'trading_days_per_year': 252,
        'confidence_levels': [0.90, 0.95, 0.99],
        'enable_higher_moments': True,
        'enable_tail_analysis': True
    }


@pytest.fixture
async def metrics_calculator_fixture(metrics_calculator_config):
    """Initialized EnhancedMetricsCalculator fixture"""
    calculator = EnhancedMetricsCalculator(metrics_calculator_config)
    await calculator.initialize()
    yield calculator
    # Cleanup
    try:
        await calculator.stop()
    except:
        pass


@pytest.fixture
def mock_metrics_calculator():
    """Mock metrics calculator for isolated testing"""
    mock = Mock(spec=EnhancedMetricsCalculator)

    # Mock methods
    mock.calculate_return_metrics = Mock(return_value={
        'total_return': 0.15,
        'annualized_return': 0.12,
        'sharpe_ratio': 1.5
    })
    mock.calculate_risk_metrics = Mock(return_value={
        'volatility': 0.15,
        'var_95': -0.02,
        'max_drawdown': -0.10
    })

    return mock


# ========================================
# COMPONENT INTEGRATION FIXTURES
# ========================================

@pytest.fixture
async def integrated_system_fixture(
    risk_manager_fixture,
    strategy_manager_fixture,
    execution_engine_fixture
):
    """Fixture with integrated core components"""
    # Link components
    strategy_manager_fixture.risk_manager = risk_manager_fixture
    risk_manager_fixture.strategy_manager = strategy_manager_fixture
    risk_manager_fixture.unified_execution_engine = execution_engine_fixture

    yield {
        'risk_manager': risk_manager_fixture,
        'strategy_manager': strategy_manager_fixture,
        'execution_engine': execution_engine_fixture
    }


# ========================================
# ASYNC HELPERS
# ========================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
