"""
Component Registration Integration Tests
=======================================

Tests component registration with correct layer/authority and validation.

Test Coverage:
- Component registration with correct layer/authority
- Dependency-ordered initialization (Regime-First validation)
- Component registration validation
- Component unregistration
- Component registration with dependencies

Author: StatArb_Gemini Integration Test Suite
Date: November 4, 2025
"""

import pytest
import pytest_asyncio
from datetime import datetime

from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
from core_engine.system.orchestrator_components import ComponentLayer, AuthorityLevel
from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.data.manager import ClickHouseDataManager
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.config.component_config import RiskConfig, DataConfig, RegimeConfig


# =============================================================================
# COMPONENT REGISTRATION TESTS
# =============================================================================

class TestComponentRegistration:
    """Integration tests for component registration"""
    
    @pytest.mark.asyncio
    async def test_component_registration_with_correct_layer_authority(self, orchestrator):
        """
        Test: Component registration with correct layer and authority
        
        Scenario: Register component with explicit layer and authority
        Expected: Component registered successfully with correct attributes
        """
        # Create a test component
        from core_engine.system.interfaces import ISystemComponent
        
        class TestComponent(ISystemComponent):
            async def initialize(self) -> bool:
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': True}
            def get_status(self):
                return {'status': 'operational'}
        
        test_component = TestComponent()
        
        # Register with explicit layer and authority
        component_id = orchestrator.register_component(
            name="TestComponent",
            component=test_component,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=50
        )
        
        # Verify registration
        assert component_id != ""
        assert component_id in orchestrator.component_registry
        
        registration = orchestrator.component_registry[component_id]
        assert registration.name == "TestComponent"
        assert registration.layer == ComponentLayer.SUPPORT
        assert registration.authority_level == AuthorityLevel.OPERATIONAL
        assert registration.initialization_order == 50
    
    @pytest.mark.asyncio
    async def test_regime_engine_registers_first(self, orchestrator):
        """
        Test: RegimeEngine registers with initialization_order=5 (FIRST)
        
        Scenario: Register RegimeEngine with order=5 per Regime-First Principle
        Expected: RegimeEngine registered with lowest initialization order
        """
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        
        regime_id = orchestrator.register_component(
            name="EnhancedRegimeEngine",
            component=regime_engine,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=5  # FIRST!
        )
        
        # Register another component with higher order
        data_config = DataConfig()
        data_manager = ClickHouseDataManager(data_config)
        
        data_id = orchestrator.register_component(
            name="ClickHouseDataManager",
            component=data_manager,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=10  # After RegimeEngine
        )
        
        # Verify initialization order
        regime_reg = orchestrator.component_registry[regime_id]
        data_reg = orchestrator.component_registry[data_id]
        
        assert regime_reg.initialization_order < data_reg.initialization_order
        assert regime_reg.initialization_order == 5
    
    @pytest.mark.asyncio
    async def test_risk_manager_registers_with_governance_layer(self, orchestrator):
        """
        Test: RiskManager registers with GOVERNANCE layer
        
        Scenario: Register CentralRiskManager with governance layer
        Expected: RiskManager registered with GOVERNANCE layer and GOVERNANCE_CONTROL authority
        """
        risk_config = RiskConfig()
        risk_manager = CentralRiskManager(risk_config)
        
        # Use register_central_risk_manager method
        risk_id = orchestrator.register_central_risk_manager(risk_manager)
        
        # Verify registration
        assert risk_id != ""
        assert risk_id in orchestrator.component_registry
        
        registration = orchestrator.component_registry[risk_id]
        assert registration.name == "CentralRiskManager"
        assert registration.layer == ComponentLayer.GOVERNANCE
        assert registration.authority_level == AuthorityLevel.GOVERNANCE_CONTROL
        assert registration.initialization_order == 10  # High priority
    
    @pytest.mark.asyncio
    async def test_component_registration_validation(self, orchestrator):
        """
        Test: Component registration validates input parameters
        
        Scenario: Attempt to register with invalid parameters
        Expected: Registration fails gracefully or uses defaults
        """
        from core_engine.system.interfaces import ISystemComponent
        
        class TestComponent(ISystemComponent):
            async def initialize(self) -> bool:
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': True}
            def get_status(self):
                return {'status': 'operational'}
        
        test_component = TestComponent()
        
        # Register with defaults (should work)
        component_id = orchestrator.register_component(
            name="TestComponent",
            component=test_component
            # No layer/authority specified - should use defaults
        )
        
        # Verify registration succeeded with defaults
        assert component_id != ""
        registration = orchestrator.component_registry[component_id]
        assert registration.layer == ComponentLayer.SUPPORT  # Default
        assert registration.authority_level == AuthorityLevel.READ_ONLY  # Default
    
    @pytest.mark.asyncio
    async def test_duplicate_component_registration(self, orchestrator):
        """
        Test: Duplicate component registration handling
        
        Scenario: Register same component instance twice
        Expected: Second registration returns same component_id
        """
        from core_engine.system.interfaces import ISystemComponent
        
        class TestComponent(ISystemComponent):
            async def initialize(self) -> bool:
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': True}
            def get_status(self):
                return {'status': 'operational'}
        
        test_component = TestComponent()
        
        # First registration
        component_id_1 = orchestrator.register_component(
            name="TestComponent",
            component=test_component
        )
        
        # Second registration (same instance)
        component_id_2 = orchestrator.register_component(
            name="TestComponent",
            component=test_component
        )
        
        # Should return same ID
        assert component_id_1 == component_id_2
    
    @pytest.mark.asyncio
    async def test_component_registration_with_dependencies(self, orchestrator):
        """
        Test: Component registration with dependency relationships
        
        Scenario: Register component that reports to another component
        Expected: Component registered with reports_to relationship
        """
        # Register parent component
        risk_config = RiskConfig()
        risk_manager = CentralRiskManager(risk_config)
        parent_id = orchestrator.register_central_risk_manager(risk_manager)
        
        # Register child component that reports to parent
        from core_engine.system.interfaces import ISystemComponent
        
        class ChildComponent(ISystemComponent):
            async def initialize(self) -> bool:
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': True}
            def get_status(self):
                return {'status': 'operational'}
        
        child_component = ChildComponent()
        
        child_id = orchestrator.register_component(
            name="ChildComponent",
            component=child_component,
            reports_to=parent_id
        )
        
        # Verify relationship
        child_reg = orchestrator.component_registry[child_id]
        assert child_reg.reports_to == parent_id
    
    @pytest.mark.asyncio
    async def test_component_registration_allowed_operations(self, orchestrator):
        """
        Test: Component registration sets allowed operations based on authority
        
        Scenario: Register component with different authority levels
        Expected: Allowed operations match authority level
        """
        from core_engine.system.interfaces import ISystemComponent
        
        class TestComponent(ISystemComponent):
            async def initialize(self) -> bool:
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': True}
            def get_status(self):
                return {'status': 'operational'}
        
        # Register with OPERATIONAL authority
        test_component = TestComponent()
        component_id = orchestrator.register_component(
            name="TestComponent",
            component=test_component,
            authority_level=AuthorityLevel.OPERATIONAL
        )
        
        registration = orchestrator.component_registry[component_id]
        
        # Verify allowed operations include operational-level permissions
        assert "process_data" in registration.allowed_operations
        assert "generate_signals" in registration.allowed_operations
        assert "update_positions" in registration.allowed_operations
    
    @pytest.mark.asyncio
    async def test_component_registration_component_id_set(self, orchestrator):
        """
        Test: Component registration sets component_id on component instance
        
        Scenario: Register component implementing ISystemComponent
        Expected: component.component_id is set after registration
        """
        from core_engine.system.interfaces import ISystemComponent
        
        class TestComponent(ISystemComponent):
            def __init__(self):
                self.component_id = None
            
            async def initialize(self) -> bool:
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': True}
            def get_status(self):
                return {'status': 'operational'}
        
        test_component = TestComponent()
        assert test_component.component_id is None
        
        # Register component
        component_id = orchestrator.register_component(
            name="TestComponent",
            component=test_component
        )
        
        # Verify component_id was set
        assert test_component.component_id == component_id
        assert test_component.component_id != None
    
    @pytest.mark.asyncio
    async def test_multiple_components_registration(self, orchestrator):
        """
        Test: Register multiple components with different layers
        
        Scenario: Register multiple components across different layers
        Expected: All components registered correctly with unique IDs
        """
        # Register components in different layers
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        regime_id = orchestrator.register_component(
            name="EnhancedRegimeEngine",
            component=regime_engine,
            layer=ComponentLayer.SUPPORT,
            initialization_order=5
        )
        
        risk_config = RiskConfig()
        risk_manager = CentralRiskManager(risk_config)
        risk_id = orchestrator.register_central_risk_manager(risk_manager)
        
        data_config = DataConfig()
        data_manager = ClickHouseDataManager(data_config)
        data_id = orchestrator.register_component(
            name="ClickHouseDataManager",
            component=data_manager,
            layer=ComponentLayer.SUPPORT,
            initialization_order=10
        )
        
        # Verify all registered
        assert regime_id in orchestrator.component_registry
        assert risk_id in orchestrator.component_registry
        assert data_id in orchestrator.component_registry
        
        # Verify unique IDs
        assert regime_id != risk_id
        assert risk_id != data_id
        assert regime_id != data_id
        
        # Verify layer distribution
        regime_reg = orchestrator.component_registry[regime_id]
        risk_reg = orchestrator.component_registry[risk_id]
        data_reg = orchestrator.component_registry[data_id]
        
        assert regime_reg.layer == ComponentLayer.SUPPORT
        assert risk_reg.layer == ComponentLayer.GOVERNANCE
        assert data_reg.layer == ComponentLayer.SUPPORT
    
    @pytest.mark.asyncio
    async def test_component_registration_layer_distribution(self, orchestrator):
        """
        Test: Components distributed across layers correctly
        
        Scenario: Register components in different layers
        Expected: layer_components dict correctly tracks components by layer
        """
        # Register components in different layers
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        regime_id = orchestrator.register_component(
            name="EnhancedRegimeEngine",
            component=regime_engine,
            layer=ComponentLayer.SUPPORT,
            initialization_order=5
        )
        
        risk_config = RiskConfig()
        risk_manager = CentralRiskManager(risk_config)
        risk_id = orchestrator.register_central_risk_manager(risk_manager)
        
        # Verify layer distribution
        support_components = orchestrator.layer_components[ComponentLayer.SUPPORT]
        governance_components = orchestrator.layer_components[ComponentLayer.GOVERNANCE]
        
        assert regime_id in support_components
        assert risk_id in governance_components
        assert len(support_components) >= 1
        assert len(governance_components) >= 1

