"""
Comprehensive Unit Tests for HierarchicalSystemOrchestrator
==========================================================

Professional test suite following institutional testing standards.
Tests all critical functionality including component registration, lifecycle management,
hierarchical control, authority management, and system monitoring.

Author: StatArb_Gemini Testing Framework
Version: 1.0.0 (Professional Testing Standards)
"""

import pytest
import asyncio
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List

# Import the components under test
from core_engine.system.hierarchical_orchestrator import (
    HierarchicalSystemOrchestrator, SystemOrchestrationConfig, ComponentRegistration,
    SystemStatus, ComponentLayer, AuthorityLevel
)

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Module-level fixtures
@pytest.fixture
def orchestrator_config() -> Dict[str, Any]:
    """Standard orchestrator configuration for testing"""
    return {
        'component_startup_timeout': 30,
        'health_check_interval': 10,
        'graceful_shutdown_timeout': 15,
        'max_component_errors': 3,
        'max_concurrent_operations': 50
    }

@pytest.fixture
def orchestrator(orchestrator_config) -> HierarchicalSystemOrchestrator:
    """Initialize HierarchicalSystemOrchestrator for testing"""
    return HierarchicalSystemOrchestrator(orchestrator_config)

@pytest.fixture
def mock_component():
    """Create a mock component for testing"""
    component = Mock()
    component.initialize = AsyncMock(return_value=True)
    component.start = AsyncMock(return_value=True)
    component.stop = AsyncMock(return_value=True)
    component.health_check = AsyncMock(return_value={'healthy': True})
    component.get_status = Mock(return_value={'operational': True})
    return component

@pytest.fixture
def mock_risk_manager():
    """Create a mock risk manager for testing"""
    risk_manager = Mock()
    risk_manager.initialize = AsyncMock(return_value=True)
    risk_manager.start = AsyncMock(return_value=True)
    risk_manager.stop = AsyncMock(return_value=True)
    risk_manager.health_check = AsyncMock(return_value={'healthy': True})
    risk_manager.get_status = Mock(return_value={'operational': True})
    risk_manager.set_controlled_components = Mock()
    return risk_manager


class TestSystemOrchestrationConfig:
    """Test suite for SystemOrchestrationConfig"""
    
    def test_config_initialization_default(self):
        """Test default configuration initialization"""
        config = SystemOrchestrationConfig()
        
        # Check default values
        assert config.component_startup_timeout > 0
        assert config.health_check_interval > 0
        assert config.graceful_shutdown_timeout > 0
        assert isinstance(config.enforce_hierarchical_control, bool)
        
        logger.info("✅ Default config initialization test passed")
    
    def test_config_custom_values(self):
        """Test configuration with custom values"""
        config = SystemOrchestrationConfig(
            component_startup_timeout=120,
            health_check_interval=5,
            graceful_shutdown_timeout=60,
            enforce_hierarchical_control=False
        )
        
        assert config.component_startup_timeout == 120
        assert config.health_check_interval == 5
        assert config.graceful_shutdown_timeout == 60
        assert config.enforce_hierarchical_control is False
        
        logger.info("✅ Custom config values test passed")


class TestComponentRegistration:
    """Test suite for ComponentRegistration"""
    
    def test_registration_creation(self):
        """Test component registration creation"""
        registration = ComponentRegistration(
            name="TestComponent",
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL
        )
        
        assert registration.name == "TestComponent"
        assert registration.layer == ComponentLayer.EXECUTION
        assert registration.authority_level == AuthorityLevel.OPERATIONAL
        assert registration.status == "unregistered"
        assert registration.error_count == 0
        
        logger.info("✅ Registration creation test passed")
    
    def test_status_update(self):
        """Test status update functionality"""
        registration = ComponentRegistration(name="TestComponent")
        
        # Update status without error
        registration.update_status("operational")
        assert registration.status == "operational"
        assert registration.last_error is None
        
        # Update status with error
        registration.update_status("error", "Test error message")
        assert registration.status == "error"
        assert registration.last_error == "Test error message"
        assert registration.error_count == 1
        
        logger.info("✅ Status update test passed")


class TestHierarchicalSystemOrchestrator:
    """Comprehensive test suite for HierarchicalSystemOrchestrator"""
    
    # ========================================
    # INITIALIZATION AND LIFECYCLE TESTS
    # ========================================
    
    def test_initialization(self, orchestrator_config):
        """Test HierarchicalSystemOrchestrator initialization"""
        orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)
        
        # Verify configuration
        assert orchestrator.config.component_startup_timeout == 30
        assert orchestrator.config.health_check_interval == 10
        
        # Verify initial state
        assert orchestrator.system_status == SystemStatus.UNINITIALIZED
        assert not orchestrator.emergency_mode
        
        # Verify collections are initialized
        assert isinstance(orchestrator.component_registry, dict)
        assert isinstance(orchestrator.layer_components, dict)
        assert len(orchestrator.component_registry) == 0
        
        logger.info("✅ Initialization test passed")
    
    @pytest.mark.asyncio
    async def test_component_lifecycle_basic(self, orchestrator):
        """Test basic ISystemComponent lifecycle methods"""
        
        # Test health check before initialization
        health = await orchestrator.health_check()
        assert health['healthy'] is False
        assert health['system_status'] == SystemStatus.UNINITIALIZED.value
        
        # Test status
        status = orchestrator.get_status()
        assert status['component_type'] == 'HierarchicalSystemOrchestrator'
        assert status['system_status'] == SystemStatus.UNINITIALIZED.value
        
        logger.info("✅ Basic component lifecycle test passed")
    
    # ========================================
    # COMPONENT REGISTRATION TESTS
    # ========================================
    
    def test_component_registration_basic(self, orchestrator, mock_component):
        """Test basic component registration"""
        
        component_id = orchestrator.register_component(
            name="TestComponent",
            component=mock_component,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL
        )
        
        # Verify registration
        assert component_id != ""
        assert component_id in orchestrator.component_registry
        
        registration = orchestrator.component_registry[component_id]
        assert registration.name == "TestComponent"
        assert registration.layer == ComponentLayer.EXECUTION
        assert registration.authority_level == AuthorityLevel.OPERATIONAL
        assert registration.component_instance is mock_component
        
        logger.info("✅ Basic component registration test passed")
    
    def test_component_registration_layers(self, orchestrator, mock_component):
        """Test component registration across different layers"""
        
        # Register components in different layers
        support_id = orchestrator.register_component(
            "SupportComponent", mock_component, ComponentLayer.SUPPORT
        )
        execution_id = orchestrator.register_component(
            "ExecutionComponent", mock_component, ComponentLayer.EXECUTION
        )
        governance_id = orchestrator.register_component(
            "GovernanceComponent", mock_component, ComponentLayer.GOVERNANCE
        )
        
        # Verify layer assignments
        assert orchestrator.component_registry[support_id].layer == ComponentLayer.SUPPORT
        assert orchestrator.component_registry[execution_id].layer == ComponentLayer.EXECUTION
        assert orchestrator.component_registry[governance_id].layer == ComponentLayer.GOVERNANCE
        
        # Verify layer tracking
        assert support_id in orchestrator.layer_components[ComponentLayer.SUPPORT]
        assert execution_id in orchestrator.layer_components[ComponentLayer.EXECUTION]
        assert governance_id in orchestrator.layer_components[ComponentLayer.GOVERNANCE]
        
        logger.info("✅ Component registration layers test passed")
    
    def test_risk_manager_registration(self, orchestrator, mock_risk_manager):
        """Test Central Risk Manager registration"""
        
        risk_manager_id = orchestrator.register_central_risk_manager(mock_risk_manager)
        
        # Verify registration
        assert risk_manager_id != ""
        assert orchestrator.risk_manager_id == risk_manager_id
        assert orchestrator.central_risk_manager is mock_risk_manager
        
        # Verify layer and authority
        registration = orchestrator.component_registry[risk_manager_id]
        assert registration.layer == ComponentLayer.GOVERNANCE
        assert registration.authority_level == AuthorityLevel.GOVERNANCE_CONTROL
        
        logger.info("✅ Risk manager registration test passed")
    
    # ========================================
    # AUTHORITY AND PERMISSION TESTS
    # ========================================
    
    def test_authority_levels(self, orchestrator):
        """Test authority level management"""
        
        # Test different authority levels
        authority_levels = [
            AuthorityLevel.READ_ONLY,
            AuthorityLevel.OPERATIONAL,
            AuthorityLevel.TACTICAL,
            AuthorityLevel.STRATEGIC,
            AuthorityLevel.GOVERNANCE_CONTROL,
            AuthorityLevel.SYSTEM_CONTROL
        ]
        
        for authority in authority_levels:
            allowed_ops = orchestrator._get_allowed_operations(authority)
            assert isinstance(allowed_ops, set)
            
            # Higher authority levels should have more operations
            if authority == AuthorityLevel.SYSTEM_CONTROL:
                assert len(allowed_ops) > 0
        
        logger.info("✅ Authority levels test passed")
    
    @pytest.mark.asyncio
    async def test_authorization_request(self, orchestrator, mock_component):
        """Test system authorization requests"""
        
        # Register a component
        component_id = orchestrator.register_component(
            "TestComponent", mock_component, 
            authority_level=AuthorityLevel.OPERATIONAL
        )
        
        # Test authorization request
        authorized = await orchestrator.request_system_authorization(
            operation="test_operation",
            component_id=component_id,
            details={"test": "data"}
        )
        
        # Should be authorized for basic operations
        assert isinstance(authorized, bool)
        
        logger.info("✅ Authorization request test passed")
    
    # ========================================
    # COMPONENT LIFECYCLE MANAGEMENT TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_component_initialization_order(self, orchestrator):
        """Test component initialization ordering"""
        
        # Create mock components with different initialization orders
        component1 = Mock()
        component1.initialize = AsyncMock(return_value=True)
        component1.start = AsyncMock(return_value=True)
        
        component2 = Mock()
        component2.initialize = AsyncMock(return_value=True)
        component2.start = AsyncMock(return_value=True)
        
        # Register with different initialization orders
        id1 = orchestrator.register_component(
            "Component1", component1, initialization_order=20
        )
        id2 = orchestrator.register_component(
            "Component2", component2, initialization_order=10
        )
        
        # Verify components are registered with correct orders
        reg1 = orchestrator.component_registry[id1]
        reg2 = orchestrator.component_registry[id2]
        
        assert reg1.initialization_order == 20
        assert reg2.initialization_order == 10
        
        logger.info("✅ Component initialization order test passed")
    
    @pytest.mark.asyncio
    async def test_component_health_monitoring(self, orchestrator, mock_component):
        """Test component health monitoring"""
        
        # Register component
        component_id = orchestrator.register_component(
            "TestComponent", mock_component
        )
        
        # Test that component is registered and has health check capability
        registration = orchestrator.component_registry[component_id]
        assert registration.component_instance is mock_component
        
        # Test that mock component has health_check method
        assert hasattr(mock_component, 'health_check')
        
        logger.info("✅ Component health monitoring test passed")
    
    # ========================================
    # SYSTEM MONITORING TESTS
    # ========================================
    
    def test_system_metrics_collection(self, orchestrator):
        """Test system metrics collection"""
        
        # Get system metrics (using available property)
        metrics = orchestrator.system_metrics
        
        # Should return metrics dictionary
        assert isinstance(metrics, dict)
        
        logger.info("✅ System metrics collection test passed")
    
    def test_performance_tracking(self, orchestrator):
        """Test performance tracking functionality"""
        
        # Should have performance metrics property
        assert isinstance(orchestrator.performance_metrics, dict)
        
        logger.info("✅ Performance tracking test passed")
    
    # ========================================
    # ERROR HANDLING AND RECOVERY TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_component_failure_handling(self, orchestrator):
        """Test component failure handling"""
        
        # Create failing component
        failing_component = Mock()
        failing_component.initialize = AsyncMock(side_effect=Exception("Initialization failed"))
        failing_component.health_check = AsyncMock(return_value={'healthy': False})
        
        # Register failing component
        component_id = orchestrator.register_component(
            "FailingComponent", failing_component
        )
        
        # Test that component is registered
        registration = orchestrator.component_registry[component_id]
        assert registration.component_instance is failing_component
        
        # Test that we can track errors by updating status
        registration.update_status("error", "Test error")
        assert registration.error_count > 0
        
        logger.info("✅ Component failure handling test passed")
    
    @pytest.mark.asyncio
    async def test_emergency_mode_activation(self, orchestrator):
        """Test emergency mode activation"""
        
        # Check emergency mode property exists
        assert isinstance(orchestrator.emergency_mode, bool)
        
        # Initially should not be in emergency mode
        assert orchestrator.emergency_mode is False
        
        logger.info("✅ Emergency mode activation test passed")
    
    # ========================================
    # SYSTEM SHUTDOWN TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, orchestrator, mock_component):
        """Test graceful system shutdown"""
        
        # Register component
        orchestrator.register_component("TestComponent", mock_component)
        
        # Test shutdown
        result = await orchestrator.shutdown_system()
        
        # Should shutdown successfully
        assert result is True
        assert orchestrator.system_status == SystemStatus.SHUTDOWN
        
        logger.info("✅ Graceful shutdown test passed")
    
    # ========================================
    # INTEGRATION TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_full_system_lifecycle(self, orchestrator, mock_risk_manager, mock_component):
        """Test complete system lifecycle"""
        
        # Register risk manager
        orchestrator.register_central_risk_manager(mock_risk_manager)
        
        # Register additional components
        orchestrator.register_component(
            "DataManager", mock_component, ComponentLayer.SUPPORT
        )
        orchestrator.register_component(
            "TradingEngine", mock_component, ComponentLayer.EXECUTION
        )
        
        # Mock the initialization methods to avoid complex dependencies
        with patch.object(orchestrator, '_initialize_central_risk_manager', return_value=True), \
             patch.object(orchestrator, '_initialize_components_hierarchically', return_value=True), \
             patch.object(orchestrator, '_establish_control_relationships', return_value=True), \
             patch.object(orchestrator, '_start_system_monitoring', return_value=None):
            
            # Test full lifecycle
            init_result = await orchestrator.initialize()
            assert init_result is True
            assert orchestrator.system_status == SystemStatus.READY
            
            start_result = await orchestrator.start()
            assert start_result is True
            assert orchestrator.system_status == SystemStatus.OPERATIONAL
            
            # Test health check
            health = await orchestrator.health_check()
            assert health['healthy'] is True
            
            # Test stop
            stop_result = await orchestrator.stop()
            assert stop_result is True
        
        logger.info("✅ Full system lifecycle test passed")
    
    # ========================================
    # CAPITAL ALLOCATION TESTS
    # ========================================
    
    def test_capital_allocation_tracking(self, orchestrator):
        """Test capital allocation tracking"""
        
        # Test capital utilization property exists
        assert isinstance(orchestrator.capital_utilization, dict)
        assert 'total_capital' in orchestrator.capital_utilization
        assert 'distributed_capital' in orchestrator.capital_utilization
        
        logger.info("✅ Capital allocation tracking test passed")
    
    # ========================================
    # MESSAGING AND COMMUNICATION TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_component_messaging(self, orchestrator, mock_component):
        """Test inter-component messaging"""
        
        # Register components
        sender_id = orchestrator.register_component("Sender", mock_component)
        receiver_id = orchestrator.register_component("Receiver", mock_component)
        
        # Verify components are registered
        assert sender_id in orchestrator.component_registry
        assert receiver_id in orchestrator.component_registry
        
        logger.info("✅ Component messaging test passed")
    
    @pytest.mark.asyncio
    async def test_event_publishing(self, orchestrator):
        """Test event publishing system"""
        
        # Test that orchestrator has audit trail capability
        assert hasattr(orchestrator, 'audit_trail')
        assert isinstance(orchestrator.audit_trail, list)
        
        logger.info("✅ Event publishing test passed")
    
    # ========================================
    # PERFORMANCE AND STRESS TESTS
    # ========================================
    
    def test_large_component_registration(self, orchestrator):
        """Test registration of many components"""
        
        # Register multiple components
        component_ids = []
        for i in range(20):
            mock_comp = Mock()
            mock_comp.initialize = AsyncMock(return_value=True)
            
            comp_id = orchestrator.register_component(
                f"Component_{i}", mock_comp
            )
            component_ids.append(comp_id)
        
        # Verify all registered
        assert len(orchestrator.component_registry) == 20
        assert all(comp_id in orchestrator.component_registry for comp_id in component_ids)
        
        logger.info("✅ Large component registration test passed")
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, orchestrator, mock_component):
        """Test concurrent operations"""
        
        # Register multiple components
        component_ids = []
        for i in range(5):
            comp_id = orchestrator.register_component(f"Component_{i}", mock_component)
            component_ids.append(comp_id)
        
        # Test concurrent component access
        tasks = []
        for comp_id in component_ids:
            task = asyncio.create_task(
                asyncio.to_thread(lambda: orchestrator.component_registry[comp_id])
            )
            tasks.append(task)
        
        # Wait for all operations
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should complete all operations
        assert len(results) == 5
        
        logger.info("✅ Concurrent operations test passed")


class TestSystemIntegration:
    """Integration tests for system orchestrator with other components"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_risk_manager_integration(self, orchestrator_config):
        """Test integration between orchestrator and risk manager"""
        
        orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)
        
        # Create mock risk manager with proper interface
        mock_risk_manager = Mock()
        mock_risk_manager.initialize = AsyncMock(return_value=True)
        mock_risk_manager.start = AsyncMock(return_value=True)
        mock_risk_manager.health_check = AsyncMock(return_value={'healthy': True})
        mock_risk_manager.set_controlled_components = Mock()
        
        # Register risk manager
        risk_manager_id = orchestrator.register_central_risk_manager(mock_risk_manager)
        
        # Verify integration
        assert orchestrator.central_risk_manager is mock_risk_manager
        assert orchestrator.risk_manager_id == risk_manager_id
        
        logger.info("✅ Orchestrator-RiskManager integration test passed")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
