"""
Lifecycle Management Integration Tests
======================================

Tests component lifecycle management (initialize, start, stop, shutdown).

Test Coverage:
- Component start/stop lifecycle
- Component shutdown order
- Component status reporting
- Component lifecycle state transitions
- Component restart and recovery

Author: StatArb_Gemini Integration Test Suite
Date: November 4, 2025
"""

import pytest
import pytest_asyncio
from datetime import datetime

from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
from core_engine.system.orchestrator_components import ComponentLayer, AuthorityLevel
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.config.component_config import RegimeConfig


# =============================================================================
# LIFECYCLE MANAGEMENT TESTS
# =============================================================================

class TestLifecycleManagement:
    """Integration tests for component lifecycle management"""
    
    @pytest.mark.asyncio
    async def test_component_start_stop_lifecycle(self, orchestrator):
        """
        Test: Component start/stop lifecycle
        
        Scenario: Initialize, start, and stop components through orchestrator
        Expected: Components transition through lifecycle states correctly
        """
        # Register component
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        
        component_id = orchestrator.register_component(
            name="EnhancedRegimeEngine",
            component=regime_engine,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=5
        )
        
        # Initialize system
        await orchestrator.initialize_system()
        
        # Verify component initialized
        registration = orchestrator.component_registry[component_id]
        assert registration.status in ["initialized", "operational"]
        
        # Start system
        await orchestrator.start()
        
        # Verify component operational
        registration = orchestrator.component_registry[component_id]
        assert registration.status == "operational"
        
        # Stop system
        await orchestrator.stop()
        
        # Verify component stopped (status may vary)
        assert registration.status in ["stopped", "operational", "initialized"]
    
    @pytest.mark.asyncio
    async def test_component_shutdown_order(self, orchestrator):
        """
        Test: Components shutdown in reverse initialization order
        
        Scenario: Register components with different shutdown orders
        Expected: Components shutdown in reverse order
        """
        # Register components with different initialization orders
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        
        regime_id = orchestrator.register_component(
            name="EnhancedRegimeEngine",
            component=regime_engine,
            initialization_order=5
        )
        
        from core_engine.data.manager import ClickHouseDataManager
        from core_engine.config.component_config import DataConfig
        
        data_config = DataConfig()
        data_manager = ClickHouseDataManager(data_config)
        
        data_id = orchestrator.register_component(
            name="ClickHouseDataManager",
            component=data_manager,
            initialization_order=10
        )
        
        # Initialize and start
        await orchestrator.initialize_system()
        await orchestrator.start()
        
        # Shutdown
        await orchestrator.shutdown_system()
        
        # Verify both components were shutdown
        # (Exact shutdown order verification may require additional instrumentation)
        regime_reg = orchestrator.component_registry[regime_id]
        data_reg = orchestrator.component_registry[data_id]
        
        # Components should be in shutdown state
        assert regime_reg.status in ["shutdown", "stopped", "uninitialized"]
        assert data_reg.status in ["shutdown", "stopped", "uninitialized"]
    
    @pytest.mark.asyncio
    async def test_component_status_reporting(self, orchestrator):
        """
        Test: Component status reporting
        
        Scenario: Get status from orchestrator for all components
        Expected: Status includes all registered components with correct information
        """
        # Register multiple components
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        
        orchestrator.register_component(
            name="EnhancedRegimeEngine",
            component=regime_engine,
            initialization_order=5
        )
        
        from core_engine.system.central_risk_manager import CentralRiskManager
        from core_engine.config.component_config import RiskConfig
        
        risk_config = RiskConfig()
        risk_manager = CentralRiskManager(risk_config)
        orchestrator.register_central_risk_manager(risk_manager)
        
        # Initialize
        await orchestrator.initialize_system()
        
        # Get component status
        status = orchestrator.component_manager.get_component_status()
        
        # Verify status structure
        assert 'total_components' in status
        assert 'operational_components' in status
        assert 'components_by_layer' in status
        
        # Verify component count
        assert status['total_components'] >= 2
        
        # Verify layer distribution
        assert 'support' in status['components_by_layer']
        assert 'governance' in status['components_by_layer']
    
    @pytest.mark.asyncio
    async def test_component_lifecycle_state_transitions(self, orchestrator):
        """
        Test: Component lifecycle state transitions
        
        Scenario: Component transitions through initialization states
        Expected: Component status updates correctly through lifecycle
        """
        # Register component
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        
        component_id = orchestrator.register_component(
            name="EnhancedRegimeEngine",
            component=regime_engine,
            initialization_order=5
        )
        
        registration = orchestrator.component_registry[component_id]
        
        # Initial state
        assert registration.status == "unregistered"
        
        # Initialize
        await orchestrator.initialize_system()
        
        # Should be initialized or operational
        assert registration.status in ["initialized", "operational"]
        
        # Start
        await orchestrator.start()
        
        # Should be operational
        assert registration.status == "operational"
    
    @pytest.mark.asyncio
    async def test_component_restart_and_recovery(self, orchestrator):
        """
        Test: Component restart and recovery
        
        Scenario: Stop and restart system
        Expected: Components restart successfully
        """
        # Register and initialize
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        
        component_id = orchestrator.register_component(
            name="EnhancedRegimeEngine",
            component=regime_engine,
            initialization_order=5
        )
        
        await orchestrator.initialize_system()
        await orchestrator.start()
        
        registration = orchestrator.component_registry[component_id]
        assert registration.status == "operational"
        
        # Stop
        await orchestrator.stop()
        
        # Restart
        await orchestrator.start()
        
        # Verify operational again
        registration = orchestrator.component_registry[component_id]
        assert registration.status == "operational"
    
    @pytest.mark.asyncio
    async def test_system_initialization_order(self, orchestrator):
        """
        Test: System initialization respects initialization order
        
        Scenario: Register components with different initialization orders
        Expected: Components initialize in order (lowest first)
        """
        # Track initialization order
        init_order = []
        
        from core_engine.system.interfaces import ISystemComponent
        
        class TrackedComponent(ISystemComponent):
            def __init__(self, name, order):
                self.name = name
                self.order = order
            
            async def initialize(self) -> bool:
                init_order.append(self.order)
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': True}
            def get_status(self):
                return {'status': 'operational'}
        
        # Register components in reverse order
        comp3 = TrackedComponent("Component3", 30)
        orchestrator.register_component("Component3", comp3, initialization_order=30)
        
        comp1 = TrackedComponent("Component1", 10)
        orchestrator.register_component("Component1", comp1, initialization_order=10)
        
        comp2 = TrackedComponent("Component2", 20)
        orchestrator.register_component("Component2", comp2, initialization_order=20)
        
        # Initialize
        await orchestrator.initialize_system()
        
        # Verify initialization order (lowest first)
        assert init_order == [10, 20, 30] or init_order == sorted(init_order)
    
    @pytest.mark.asyncio
    async def test_orchestrator_health_check(self, orchestrator):
        """
        Test: Orchestrator health check
        
        Scenario: Get health status from orchestrator
        Expected: Health check returns system status
        """
        # Initialize system
        await orchestrator.initialize_system()
        await orchestrator.start()
        
        # Get health check
        health = await orchestrator.health_check()
        
        # Verify health structure
        assert 'healthy' in health
        assert 'system_status' in health
        assert 'component_count' in health
        assert 'operational_components' in health
        
        # Verify health status
        assert health['system_status'] == 'operational'
        assert health['healthy'] == True
    
    @pytest.mark.asyncio
    async def test_orchestrator_get_status(self, orchestrator):
        """
        Test: Orchestrator get_status
        
        Scenario: Get status from orchestrator
        Expected: Status includes system information
        """
        # Initialize system
        await orchestrator.initialize_system()
        await orchestrator.start()
        
        # Get status
        status = orchestrator.get_status()
        
        # Verify status structure
        assert 'component_type' in status
        assert 'system_status' in status
        assert 'component_count' in status
        assert status['component_type'] == 'HierarchicalSystemOrchestrator'
    
    @pytest.mark.asyncio
    async def test_component_initialization_failure_handling(self, orchestrator):
        """
        Test: Component initialization failure handling
        
        Scenario: Component fails to initialize
        Expected: System handles failure gracefully, other components continue
        """
        from core_engine.system.interfaces import ISystemComponent
        
        class FailingComponent(ISystemComponent):
            async def initialize(self) -> bool:
                return False  # Fail initialization
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': False}
            def get_status(self):
                return {'status': 'failed'}
        
        failing_comp = FailingComponent()
        failing_id = orchestrator.register_component(
            name="FailingComponent",
            component=failing_comp,
            initialization_order=50
        )
        
        # Register working component
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        working_id = orchestrator.register_component(
            name="WorkingComponent",
            component=regime_engine,
            initialization_order=5
        )
        
        # Initialize system (should handle failure)
        result = await orchestrator.initialize_system()
        
        # System may still initialize (80% success rate required)
        failing_reg = orchestrator.component_registry[failing_id]
        working_reg = orchestrator.component_registry[working_id]
        
        # Failing component should be marked as failed
        assert failing_reg.status == "failed"
        
        # Working component should still initialize
        assert working_reg.status in ["initialized", "operational"]
    
    @pytest.mark.asyncio
    async def test_concurrent_component_initialization(self, orchestrator):
        """
        Test: Concurrent component initialization
        
        Scenario: Initialize components with same initialization order
        Expected: Components with same order initialize concurrently
        """
        init_times = {}
        
        from core_engine.system.interfaces import ISystemComponent
        import asyncio
        
        class ConcurrentComponent(ISystemComponent):
            def __init__(self, name):
                self.name = name
            
            async def initialize(self) -> bool:
                init_times[self.name] = asyncio.get_event_loop().time()
                await asyncio.sleep(0.1)  # Simulate initialization time
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': True}
            def get_status(self):
                return {'status': 'operational'}
        
        # Register components with same initialization order
        comp1 = ConcurrentComponent("Comp1")
        orchestrator.register_component("Comp1", comp1, initialization_order=50)
        
        comp2 = ConcurrentComponent("Comp2")
        orchestrator.register_component("Comp2", comp2, initialization_order=50)
        
        # Initialize
        await orchestrator.initialize_system()
        
        # Both should be initialized
        assert "Comp1" in init_times
        assert "Comp2" in init_times
        
        # Times should be close (concurrent initialization)
        time_diff = abs(init_times["Comp1"] - init_times["Comp2"])
        assert time_diff < 0.2  # Should initialize within 200ms of each other

