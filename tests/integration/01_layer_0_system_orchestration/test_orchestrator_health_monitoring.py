"""
Health Monitoring Integration Tests
===================================

Tests orchestrator health monitoring capabilities.

Test Coverage:
- Component health monitoring
- Component health degradation handling
- Health check integration

Author: StatArb_Gemini Integration Test Suite
Date: November 4, 2025
"""

import pytest

from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.config.component_config import RegimeConfig

class TestHealthMonitoring:
    """Integration tests for health monitoring"""

    @pytest.mark.asyncio
    async def test_component_health_monitoring(self, orchestrator):
        """
        Test: Component health monitoring

        Scenario: Perform health checks on all registered components
        Expected: Health checks execute for all components
        """
        # Register component
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)

        orchestrator.register_component(
            name="EnhancedRegimeEngine",
            component=regime_engine,
            initialization_order=5
        )

        # Initialize and start
        await orchestrator.initialize_system()
        await orchestrator.start()

        # Perform health checks
        await orchestrator.component_manager.health_check_components()

        # Verify health checks executed
        status = orchestrator.component_manager.get_component_status()
        assert status['total_components'] > 0

    @pytest.mark.asyncio
    async def test_component_health_degradation_handling(self, orchestrator):
        """
        Test: Component health degradation handling

        Scenario: Component health check fails
        Expected: Component status updated to unhealthy
        """
        from core_engine.system.interfaces import ISystemComponent

        class UnhealthyComponent(ISystemComponent):
            async def initialize(self) -> bool:
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                return {'healthy': False, 'reason': 'Test failure'}
            def get_status(self):
                return {'status': 'unhealthy'}

        unhealthy_comp = UnhealthyComponent()
        comp_id = orchestrator.register_component(
            name="UnhealthyComponent",
            component=unhealthy_comp,
            initialization_order=50
        )

        await orchestrator.initialize_system()
        await orchestrator.start()

        # Perform health check
        await orchestrator.component_manager.health_check_components()

        # Verify component marked as unhealthy
        registration = orchestrator.component_registry[comp_id]
        assert registration.status in ["unhealthy", "error"]

    @pytest.mark.asyncio
    async def test_health_check_integration(self, orchestrator):
        """
        Test: Health check integration with orchestrator

        Scenario: Get system health through orchestrator
        Expected: Health includes all component statuses
        """
        # Register multiple components
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        orchestrator.register_component("RegimeEngine", regime_engine, initialization_order=5)

        await orchestrator.initialize_system()
        await orchestrator.start()

        # Get health
        health = await orchestrator.health_check()

        # Verify health structure
        assert 'healthy' in health
        assert 'component_count' in health
        assert 'operational_components' in health
        assert health['component_count'] > 0

    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, orchestrator):
        """
        Test: Health check error handling

        Scenario: Component health check raises exception
        Expected: Error handled gracefully, component status updated
        """
        from core_engine.system.interfaces import ISystemComponent

        class ErrorComponent(ISystemComponent):
            async def initialize(self) -> bool:
                return True
            async def start(self) -> bool:
                return True
            async def stop(self) -> bool:
                return True
            async def health_check(self):
                raise Exception("Health check error")
            def get_status(self):
                return {'status': 'error'}

        error_comp = ErrorComponent()
        comp_id = orchestrator.register_component(
            name="ErrorComponent",
            component=error_comp,
            initialization_order=50
        )

        await orchestrator.initialize_system()
        await orchestrator.start()

        # Perform health check (should handle error)
        await orchestrator.component_manager.health_check_components()

        # Verify error recorded
        registration = orchestrator.component_registry[comp_id]
        assert registration.status in ["error", "unhealthy"]
        assert registration.error_count > 0

    @pytest.mark.asyncio
    async def test_health_monitoring_multiple_components(self, orchestrator):
        """
        Test: Health monitoring for multiple components

        Scenario: Monitor health of multiple registered components
        Expected: All components health checked
        """
        # Register multiple components
        regime_config = RegimeConfig()
        regime_engine = EnhancedRegimeEngine(regime_config)
        orchestrator.register_component("RegimeEngine", regime_engine, initialization_order=5)

        from core_engine.data.manager import ClickHouseDataManager
        from core_engine.config.component_config import DataConfig

        data_config = DataConfig()
        data_manager = ClickHouseDataManager(data_config)
        orchestrator.register_component("DataManager", data_manager, initialization_order=10)

        await orchestrator.initialize_system()
        await orchestrator.start()

        # Perform health checks
        await orchestrator.component_manager.health_check_components()

        # Verify all components checked
        status = orchestrator.component_manager.get_component_status()
        assert status['total_components'] >= 2

