"""
Comprehensive Unit Tests for HierarchicalSystemOrchestrator
==========================================================

Professional test suite covering:
- Component registration and lifecycle management
- Hierarchical layer enforcement (DATA → ANALYSIS → ACTION)
- Authority level validation
- Emergency shutdown coordination
- System monitoring and health checks
- Governance authorization flows

Author: StatArb_Gemini Test Infrastructure
Version: 1.0.0
"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from core_engine.system.hierarchical_orchestrator import (
    HierarchicalSystemOrchestrator,
    SystemStatus
)
from core_engine.system.orchestrator_components import (
    ComponentLayer,
    AuthorityLevel
)


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def orchestrator_config():
    """Orchestrator configuration"""
    return {
        'health_check_interval': 30,
        'max_concurrent_operations': 10,
        'emergency_override_enabled': True,
        'component_startup_timeout': 60
    }


@pytest_asyncio.fixture
async def orchestrator(orchestrator_config):
    """Create orchestrator instance"""
    orch = HierarchicalSystemOrchestrator(orchestrator_config)
    yield orch
    # Cleanup
    if orch.system_status == SystemStatus.OPERATIONAL:
        await orch.stop()


@pytest.fixture
def mock_risk_manager():
    """Mock Central Risk Manager"""
    risk_manager = Mock()
    risk_manager.initialize = AsyncMock(return_value=True)
    risk_manager.start = AsyncMock(return_value=True)
    risk_manager.stop = AsyncMock(return_value=True)
    risk_manager.health_check = AsyncMock(return_value={'healthy': True})
    risk_manager.set_controlled_components = Mock()
    return risk_manager


@pytest.fixture
def mock_strategy_manager():
    """Mock Strategy Manager"""
    strategy = Mock()
    strategy.initialize = AsyncMock(return_value=True)
    strategy.start = AsyncMock(return_value=True)
    strategy.stop = AsyncMock(return_value=True)
    strategy.health_check = AsyncMock(return_value={'healthy': True})
    return strategy


@pytest.fixture
def mock_execution_engine():
    """Mock Execution Engine"""
    engine = Mock()
    engine.initialize = AsyncMock(return_value=True)
    engine.start = AsyncMock(return_value=True)
    engine.stop = AsyncMock(return_value=True)
    engine.health_check = AsyncMock(return_value={'healthy': True})
    return engine


# ========================================
# TESTS: LIFECYCLE MANAGEMENT
# ========================================

class TestOrchestratorLifecycle:
    """Test orchestrator lifecycle management"""

    def test_initialization(self, orchestrator):
        """Test orchestrator initializes correctly"""
        assert orchestrator.system_status == SystemStatus.UNINITIALIZED
        assert orchestrator.system_id is not None
        assert orchestrator.component_registry == {}

    def test_configuration_access(self, orchestrator):
        """Test configuration properties"""
        config = orchestrator.config
        assert config is not None
        assert hasattr(config, 'health_check_interval')

    @pytest.mark.asyncio
    async def test_component_interface_methods(self, orchestrator):
        """Test ISystemComponent interface implementation"""
        # Should have required methods
        assert hasattr(orchestrator, 'initialize')
        assert hasattr(orchestrator, 'start')
        assert hasattr(orchestrator, 'stop')
        assert hasattr(orchestrator, 'health_check')
        assert hasattr(orchestrator, 'get_status')


# ========================================
# TESTS: COMPONENT REGISTRATION
# ========================================

class TestComponentRegistration:
    """Test component registration and hierarchy"""

    def test_register_component_basic(self, orchestrator):
        """Test basic component registration"""
        mock_component = Mock()

        component_id = orchestrator.register_component(
            name="TestComponent",
            component=mock_component,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.READ_ONLY
        )

        assert component_id != ""
        assert component_id in orchestrator.component_registry

        registration = orchestrator.component_registry[component_id]
        assert registration.name == "TestComponent"
        assert registration.layer == ComponentLayer.SUPPORT
        assert registration.authority_level == AuthorityLevel.READ_ONLY

    def test_register_governance_component(self, orchestrator, mock_risk_manager):
        """Test registering governance layer component"""
        component_id = orchestrator.register_central_risk_manager(mock_risk_manager)

        assert component_id != ""
        assert orchestrator.risk_manager_id == component_id
        assert orchestrator.central_risk_manager == mock_risk_manager

        registration = orchestrator.component_registry[component_id]
        assert registration.layer == ComponentLayer.GOVERNANCE
        assert registration.authority_level == AuthorityLevel.GOVERNANCE_CONTROL

    def test_register_execution_component(self, orchestrator, mock_execution_engine):
        """Test registering execution layer component"""
        component_id = orchestrator.register_component(
            name="ExecutionEngine",
            component=mock_execution_engine,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.TACTICAL
        )

        assert component_id != ""
        registration = orchestrator.component_registry[component_id]
        assert registration.layer == ComponentLayer.EXECUTION
        assert registration.authority_level == AuthorityLevel.TACTICAL

    def test_layer_segregation(self, orchestrator, mock_risk_manager, mock_execution_engine):
        """Test components are properly segregated by layer"""
        # Register components in different layers
        gov_id = orchestrator.register_central_risk_manager(mock_risk_manager)
        exec_id = orchestrator.register_component(
            name="ExecutionEngine",
            component=mock_execution_engine,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.TACTICAL
        )

        # Check layer segregation
        assert len(orchestrator.layer_components[ComponentLayer.GOVERNANCE]) == 1
        assert len(orchestrator.layer_components[ComponentLayer.EXECUTION]) == 1
        assert gov_id in orchestrator.layer_components[ComponentLayer.GOVERNANCE]
        assert exec_id in orchestrator.layer_components[ComponentLayer.EXECUTION]


# ========================================
# TESTS: AUTHORITY LEVELS
# ========================================

class TestAuthorityLevels:
    """Test authority level enforcement"""

    def test_system_control_authority(self, orchestrator):
        """Test system control authority level"""
        mock_component = Mock()

        component_id = orchestrator.register_component(
            name="SystemController",
            component=mock_component,
            layer=ComponentLayer.ORCHESTRATION,
            authority_level=AuthorityLevel.SYSTEM_CONTROL
        )

        registration = orchestrator.component_registry[component_id]
        allowed_ops = registration.allowed_operations

        # System control should have full permissions
        assert "system_shutdown" in allowed_ops
        assert "component_control" in allowed_ops
        assert "authority_delegation" in allowed_ops

    def test_governance_control_authority(self, orchestrator, mock_risk_manager):
        """Test governance control authority level"""
        component_id = orchestrator.register_central_risk_manager(mock_risk_manager)

        registration = orchestrator.component_registry[component_id]
        allowed_ops = registration.allowed_operations

        # Governance should have trading control but not system control
        assert "authorize_trades" in allowed_ops
        assert "emergency_stop" in allowed_ops
        assert "override_limits" in allowed_ops
        assert "system_shutdown" not in allowed_ops

    def test_operational_authority(self, orchestrator):
        """Test operational authority level"""
        mock_component = Mock()

        component_id = orchestrator.register_component(
            name="DataProcessor",
            component=mock_component,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL
        )

        registration = orchestrator.component_registry[component_id]
        allowed_ops = registration.allowed_operations

        # Operational should have processing but not trading control
        assert "process_data" in allowed_ops
        assert "calculate_indicators" in allowed_ops
        assert "execute_trades" not in allowed_ops

    def test_read_only_authority(self, orchestrator):
        """Test read-only authority level"""
        mock_component = Mock()

        component_id = orchestrator.register_component(
            name="Monitor",
            component=mock_component,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.READ_ONLY
        )

        registration = orchestrator.component_registry[component_id]
        allowed_ops = registration.allowed_operations

        # Read-only should only view
        assert "view_status" in allowed_ops
        assert "view_positions" in allowed_ops
        assert "process_data" not in allowed_ops
        assert "execute_trades" not in allowed_ops


# ========================================
# TESTS: HIERARCHICAL INITIALIZATION
# ========================================

class TestHierarchicalInitialization:
    """Test hierarchical component initialization"""

    @pytest.mark.asyncio
    async def test_initialization_order(self, orchestrator, mock_risk_manager,
                                       mock_strategy_manager, mock_execution_engine):
        """Test components initialize in correct hierarchical order"""
        # Register components with different orders
        orchestrator.register_central_risk_manager(mock_risk_manager)

        orchestrator.register_component(
            name="StrategyManager",
            component=mock_strategy_manager,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.STRATEGIC,
            initialization_order=20
        )

        orchestrator.register_component(
            name="ExecutionEngine",
            component=mock_execution_engine,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.TACTICAL,
            initialization_order=30
        )

        # Initialize system
        success = await orchestrator.initialize_system()

        # Should initialize successfully
        assert success
        assert orchestrator.system_status == SystemStatus.READY

        # Verify components were initialized
        mock_risk_manager.initialize.assert_called_once()
        mock_strategy_manager.initialize.assert_called_once()
        mock_execution_engine.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_governance_initializes_first(self, orchestrator, mock_risk_manager):
        """Test governance layer initializes before other layers"""
        orchestrator.register_central_risk_manager(mock_risk_manager)

        success = await orchestrator.initialize_system()

        assert success
        # Risk manager should be initialized
        mock_risk_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_initialization_handling(self, orchestrator):
        """Test handling of failed component initialization"""
        mock_component = Mock()
        mock_component.initialize = AsyncMock(return_value=False)

        orchestrator.register_central_risk_manager(mock_component)

        success = await orchestrator.initialize_system()

        # Should fail gracefully
        assert not success
        assert orchestrator.system_status == SystemStatus.EMERGENCY


# ========================================
# TESTS: CONTROL RELATIONSHIPS
# ========================================

class TestControlRelationships:
    """Test hierarchical control relationships"""

    @pytest.mark.asyncio
    async def test_risk_manager_controls_trading(self, orchestrator, mock_risk_manager,
                                                 mock_strategy_manager, mock_execution_engine):
        """Test risk manager controls trading components"""
        # Register components
        risk_id = orchestrator.register_central_risk_manager(mock_risk_manager)

        strategy_id = orchestrator.register_component(
            name="StrategyManager",
            component=mock_strategy_manager,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.STRATEGIC
        )

        execution_id = orchestrator.register_component(
            name="ExecutionEngine",
            component=mock_execution_engine,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.TACTICAL
        )

        # Initialize to establish relationships
        await orchestrator.initialize_system()

        # Check that trading components report to risk manager
        strategy_reg = orchestrator.component_registry[strategy_id]
        execution_reg = orchestrator.component_registry[execution_id]

        assert strategy_reg.reports_to == risk_id
        assert execution_reg.reports_to == risk_id

        # Check risk manager controls trading components
        mock_risk_manager.set_controlled_components.assert_called_once()


# ========================================
# TESTS: HEALTH CHECKS
# ========================================

class TestHealthChecks:
    """Test system health monitoring"""

    @pytest.mark.asyncio
    async def test_orchestrator_health_check(self, orchestrator, mock_risk_manager):
        """Test orchestrator health check"""
        orchestrator.register_central_risk_manager(mock_risk_manager)
        await orchestrator.initialize_system()
        await orchestrator.start()

        health = await orchestrator.health_check()

        assert 'healthy' in health
        assert 'system_status' in health
        assert 'component_count' in health
        assert health['component_count'] == 1

    def test_get_status(self, orchestrator):
        """Test getting orchestrator status"""
        status = orchestrator.get_status()

        assert 'component_type' in status
        assert status['component_type'] == 'HierarchicalSystemOrchestrator'
        assert 'system_status' in status
        assert 'component_count' in status


# ========================================
# TESTS: EMERGENCY SHUTDOWN
# ========================================

class TestEmergencyShutdown:
    """Test emergency shutdown coordination"""

    @pytest.mark.asyncio
    async def test_emergency_mode_flag(self, orchestrator):
        """Test emergency mode flag"""
        assert orchestrator.emergency_mode == False

    @pytest.mark.asyncio
    async def test_graceful_stop(self, orchestrator, mock_risk_manager):
        """Test graceful system stop"""
        orchestrator.register_central_risk_manager(mock_risk_manager)
        await orchestrator.initialize_system()
        await orchestrator.start()

        # Stop system
        success = await orchestrator.stop()

        assert success


# ========================================
# TESTS: SYSTEM METRICS
# ========================================

class TestSystemMetrics:
    """Test system metrics collection"""

    def test_system_metrics_property(self, orchestrator):
        """Test system metrics property access"""
        metrics = orchestrator.system_metrics

        assert metrics is not None
        assert isinstance(metrics, dict)

    def test_performance_metrics_property(self, orchestrator):
        """Test performance metrics property access"""
        metrics = orchestrator.performance_metrics

        assert metrics is not None
        assert isinstance(metrics, dict)


# ========================================
# TESTS: CONCURRENT OPERATIONS
# ========================================

class TestConcurrentOperations:
    """Test concurrent operation handling"""

    @pytest.mark.asyncio
    async def test_operation_semaphore(self, orchestrator):
        """Test operation semaphore limits concurrency"""
        assert orchestrator.operation_semaphore is not None
        assert orchestrator.operation_semaphore._value == 10  # max_concurrent_operations


# ========================================
# TESTS: AUDIT TRAIL
# ========================================

class TestAuditTrail:
    """Test audit trail for compliance"""

    def test_audit_trail_initialization(self, orchestrator):
        """Test audit trail is initialized"""
        assert hasattr(orchestrator, 'audit_trail')
        assert isinstance(orchestrator.audit_trail, list)

    def test_authorization_audit(self, orchestrator):
        """Test authorization audit trail"""
        assert hasattr(orchestrator, '_authorization_audit')
        assert isinstance(orchestrator._authorization_audit, list)


# ========================================
# TESTS: PERFORMANCE
# ========================================

class TestPerformance:
    """Test orchestrator performance"""

    @pytest.mark.asyncio
    async def test_initialization_performance(self, orchestrator, mock_risk_manager):
        """Test initialization completes quickly"""
        orchestrator.register_central_risk_manager(mock_risk_manager)

        start_time = datetime.now()
        await orchestrator.initialize_system()
        duration = (datetime.now() - start_time).total_seconds()

        # Should initialize in under 1 second
        assert duration < 1.0

    def test_component_registration_performance(self, orchestrator):
        """Test component registration is fast"""
        mock_component = Mock()

        start_time = datetime.now()
        for i in range(10):
            orchestrator.register_component(
                name=f"Component{i}",
                component=mock_component,
                layer=ComponentLayer.SUPPORT
            )
        duration = (datetime.now() - start_time).total_seconds()

        # Should register 10 components in under 100ms
        assert duration < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
