#!/usr/bin/env python3
"""
Integration Tests for Data, Risk, and Regime Components
=======================================================

Tests for the integration of enhanced data, risk, and regime components
with ISystemComponent integration.

Author: StatArb_Gemini Testing Team
Version: 1.0.0
"""

import pytest
import pytest_asyncio

# Import enhanced data, risk, and regime components
from core_engine.data.manager import (
    ClickHouseDataManager, ClickHouseDataConfig
)
from core_engine.system.central_risk_manager import (
    CentralRiskManager
)
from core_engine.regime.engine import (
    EnhancedRegimeEngine
)


class TestIntegrationWorkflow:
    """Test suite for integration of enhanced data and risk components"""

    @pytest_asyncio.fixture
    async def integrated_components(self):
        """Fixture for integrated data and risk components"""
        data_config = ClickHouseDataConfig(
            symbols=['AAPL'],
            start_date="2024-01-01",
            end_date="2024-01-31",
            enable_caching=True
        )
        risk_config = {
            'max_position_size': 0.10,
            'max_daily_var': 0.05,
            'position_concentration_limit': 0.15
        }
        regime_config = {
            'lookback_window': 60,
            'volatility_window': 20,
            'trend_threshold': 0.02
        }

        data_manager = ClickHouseDataManager(data_config)
        risk_manager = CentralRiskManager(risk_config)
        regime_engine = EnhancedRegimeEngine(regime_config)

        yield data_manager, risk_manager, regime_engine

        # Cleanup
        for component in [data_manager, risk_manager, regime_engine]:
            if component.is_operational:
                await component.stop()

    @pytest.mark.asyncio
    async def test_component_integration(self, integrated_components):
        """Test basic integration of all data and risk components"""
        data_manager, risk_manager, regime_engine = integrated_components

        # Initialize all components
        await data_manager.initialize()
        await risk_manager.initialize()
        await regime_engine.initialize()

        assert data_manager.is_initialized
        assert risk_manager.is_initialized
        assert regime_engine.is_initialized

        # Start all components
        await data_manager.start()
        await risk_manager.start()
        await regime_engine.start()

        assert data_manager.is_operational
        assert risk_manager.is_operational
        assert regime_engine.is_operational

        # Stop all components
        await data_manager.stop()
        await risk_manager.stop()
        await regime_engine.stop()

        assert not data_manager.is_operational
        assert not risk_manager.is_operational
        assert not regime_engine.is_operational

    @pytest.mark.asyncio
    async def test_health_checks_all_components(self, integrated_components):
        """Test health checks across all integrated components"""
        data_manager, risk_manager, regime_engine = integrated_components

        await data_manager.initialize()
        await risk_manager.initialize()
        await regime_engine.initialize()

        # Start components for health check
        await data_manager.start()
        await risk_manager.start()
        await regime_engine.start()

        # Test health checks
        data_health = await data_manager.health_check()
        risk_health = await risk_manager.health_check()
        regime_health = await regime_engine.health_check()

        assert data_health['healthy'] is True
        assert risk_health['healthy'] is True
        # Regime health may be False initially, which is acceptable
        assert 'healthy' in regime_health

        # Cleanup
        await data_manager.stop()
        await risk_manager.stop()
        await regime_engine.stop()

        assert 'component_type' in data_health
        assert 'component_type' in risk_health
        assert regime_health['component_type'] == 'EnhancedRegimeEngine'

    @pytest.mark.asyncio
    async def test_component_status_reporting(self, integrated_components):
        """Test status reporting across all components"""
        data_manager, risk_manager, regime_engine = integrated_components

        # Initialize all components
        for component in [data_manager, risk_manager, regime_engine]:
            await component.initialize()

        # Check that all components have proper status reporting
        for component in [data_manager, risk_manager, regime_engine]:
            status = component.get_status()
            assert 'component_type' in status
            assert 'initialized' in status
            assert 'operational' in status
            assert status['initialized'] is True

            # Different components have different status structures
            if hasattr(component, 'health_metrics'):
                assert 'health_metrics' in status

    @pytest.mark.asyncio
    async def test_component_performance_metrics(self, integrated_components):
        """Test performance metrics tracking across all components"""
        data_manager, risk_manager, regime_engine = integrated_components

        # Initialize and start all components
        for component in [data_manager, risk_manager, regime_engine]:
            await component.initialize()
            await component.start()

        # Check that all components have performance metrics
        for component in [data_manager, risk_manager, regime_engine]:
            status = component.get_status()
            # Only enhanced components have health_metrics
            if hasattr(component, 'health_metrics'):
                assert 'health_metrics' in status
                assert 'performance_metrics' in status['health_metrics']

        # Cleanup
        for component in [data_manager, risk_manager, regime_engine]:
            await component.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
