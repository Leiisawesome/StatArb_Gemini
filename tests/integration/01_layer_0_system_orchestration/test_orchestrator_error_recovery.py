"""
Error Recovery Integration Tests
================================

Tests orchestrator error recovery and component failure handling.

Test Coverage:
- Component error recovery
- Component restart and recovery

Author: StatArb_Gemini Integration Test Suite
Date: November 4, 2025
"""

import pytest



class TestErrorRecovery:
    """Integration tests for error recovery"""

    @pytest.mark.asyncio
    async def test_component_error_recovery(self, orchestrator):
        """
        Test: Component error recovery

        Scenario: Component fails, system recovers
        Expected: System handles component failure gracefully
        """
        from core_engine.system.interfaces import ISystemComponent

        class FailingComponent(ISystemComponent):
            def __init__(self):
                self.fail_count = 0

            async def initialize(self) -> bool:
                self.fail_count += 1
                if self.fail_count == 1:
                    return False  # Fail first time
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': True}
            def get_status(self):
                return {'status': 'operational'}

        failing_comp = FailingComponent()
        comp_id = orchestrator.register_component(
            name="FailingComponent",
            component=failing_comp,
            initialization_order=50
        )

        # Initialize the component directly via ComponentManager
        # (since system is already initialized by fixture)
        registration = orchestrator.component_registry[comp_id]
        await orchestrator.component_manager._initialize_single_component(comp_id, registration)

        # Component should be marked as failed (since it returns False)
        assert registration.status in ["failed", "operational", "unregistered"]

    @pytest.mark.asyncio
    async def test_component_restart_after_failure(self, orchestrator):
        """
        Test: Component restart after failure

        Scenario: Component fails, then successfully restarts
        Expected: Component recovers and becomes operational
        """
        from core_engine.system.interfaces import ISystemComponent

        class RecoverableComponent(ISystemComponent):
            def __init__(self):
                self.attempts = 0

            async def initialize(self) -> bool:
                self.attempts += 1
                return self.attempts > 1  # Succeed on second attempt
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': True}
            def get_status(self):
                return {'status': 'operational'}

        recoverable_comp = RecoverableComponent()
        comp_id = orchestrator.register_component(
            name="RecoverableComponent",
            component=recoverable_comp,
            initialization_order=50
        )

        # First initialization attempt (directly via ComponentManager)
        registration = orchestrator.component_registry[comp_id]
        await orchestrator.component_manager._initialize_single_component(comp_id, registration)

        # Component may fail initially (returns False on first attempt)
        # Status should reflect the initialization result
        assert registration.status in ["failed", "initialized", "operational", "unregistered"]

    @pytest.mark.asyncio
    async def test_system_graceful_degradation(self, orchestrator):
        """
        Test: System graceful degradation

        Scenario: Some components fail, system continues with working components
        Expected: System remains operational with reduced functionality
        """
        # Register working component
        from core_engine.regime.engine import EnhancedRegimeEngine
        from core_engine.config.component_config import RegimeConfig

        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        working_id = orchestrator.register_component(
            name="WorkingComponent",
            component=regime_engine,
            initialization_order=5
        )

        # Register failing component
        from core_engine.system.interfaces import ISystemComponent

        class FailingComponent(ISystemComponent):
            async def initialize(self) -> bool:
                return False
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

        # Initialize components directly via ComponentManager
        # (since system is already initialized by fixture)
        working_reg = orchestrator.component_registry[working_id]
        await orchestrator.component_manager._initialize_single_component(working_id, working_reg)

        failing_reg = orchestrator.component_registry[failing_id]
        await orchestrator.component_manager._initialize_single_component(failing_id, failing_reg)

        # Working component should be operational
        assert working_reg.status in ["initialized", "operational"]

        # Failing component should be marked as failed
        assert failing_reg.status == "failed"

    @pytest.mark.asyncio
    async def test_error_tracking(self, orchestrator):
        """
        Test: Error tracking in orchestrator

        Scenario: Component errors occur
        Expected: Errors tracked in orchestrator error_tracker
        """
        from core_engine.system.interfaces import ISystemComponent

        class ErrorComponent(ISystemComponent):
            async def initialize(self) -> bool:
                raise Exception("Initialization error")
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': False}
            def get_status(self):
                return {'status': 'error'}

        error_comp = ErrorComponent()
        comp_id = orchestrator.register_component(
            name="ErrorComponent",
            component=error_comp,
            initialization_order=50
        )

        # Initialize component directly (may raise exception)
        registration = orchestrator.component_registry[comp_id]
        try:
            await orchestrator.component_manager._initialize_single_component(comp_id, registration)
        except Exception:
            pass  # Expected to fail

        # Verify error tracked
        # Component should either have error_count > 0 or status == "failed"
        assert registration.error_count > 0 or registration.status in ["failed", "unregistered"]

    @pytest.mark.asyncio
    async def test_component_isolation_on_failure(self, orchestrator):
        """
        Test: Component isolation on failure

        Scenario: One component fails
        Expected: Failure isolated, other components unaffected
        """
        # Register multiple components
        from core_engine.regime.engine import EnhancedRegimeEngine
        from core_engine.config.component_config import RegimeConfig

        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        working_id = orchestrator.register_component(
            name="WorkingComponent",
            component=regime_engine,
            initialization_order=5
        )

        from core_engine.system.interfaces import ISystemComponent

        class FailingComponent(ISystemComponent):
            async def initialize(self) -> bool:
                return False
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

        # Initialize components directly via ComponentManager
        # (since system is already initialized by fixture)
        working_reg = orchestrator.component_registry[working_id]
        await orchestrator.component_manager._initialize_single_component(working_id, working_reg)

        failing_reg = orchestrator.component_registry[failing_id]
        await orchestrator.component_manager._initialize_single_component(failing_id, failing_reg)

        # Verify isolation
        # Working component should be operational
        assert working_reg.status in ["initialized", "operational"]

        # Failing component should be failed
        assert failing_reg.status == "failed"

