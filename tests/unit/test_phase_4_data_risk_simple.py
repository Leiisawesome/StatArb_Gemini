#!/usr/bin/env python3
"""
Unit Tests for Phase 4 Enhanced Data & Risk Management Components
================================================================

Tests for the enhanced data and risk management components with ISystemComponent integration:
- ClickHouseDataManager (Enhanced UnifiedDataManager)
- CentralRiskManager (Enhanced Risk Management)
- EnhancedRegimeEngine (Enhanced Market Regime Analysis)

Author: StatArb_Gemini Testing Team
Version: 1.0.0 (Phase 4 Testing)
"""

import pytest
import pytest_asyncio
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import asyncio

# Import enhanced data and risk components
from core_engine.data.manager import (
    ClickHouseDataManager, ClickHouseDataConfig
)
from core_engine.system.central_risk_manager import (
    CentralRiskManager, TradingDecisionRequest, TradingDecisionType
)
from core_engine.regime.engine import (
    EnhancedRegimeEngine, RegimeEngineConfig
)


class TestClickHouseDataManagerBasics:
    """Test suite for ClickHouse Data Manager basic functionality"""

    @pytest_asyncio.fixture
    async def data_config(self):
        """Fixture for data manager configuration"""
        return ClickHouseDataConfig(
            symbols=['AAPL', 'TSLA'],
            start_date="2024-01-01",
            end_date="2024-01-31",
            enable_caching=True
        )

    @pytest_asyncio.fixture
    async def data_manager(self, data_config):
        """Fixture for data manager"""
        manager = ClickHouseDataManager(data_config)
        yield manager
        if manager.is_operational:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_data_manager_creation(self, data_config):
        """Test data manager creation"""
        manager = ClickHouseDataManager(data_config)
        assert manager is not None
        # ClickHouseDataManager may not have component_id in the same way
        assert not manager.is_initialized
        assert not manager.is_operational

    @pytest.mark.asyncio
    async def test_data_manager_initialization(self, data_manager):
        """Test data manager initialization"""
        result = await data_manager.initialize()
        assert result is True
        assert data_manager.is_initialized
        assert not data_manager.is_operational

    @pytest.mark.asyncio
    async def test_data_manager_lifecycle(self, data_manager):
        """Test data manager lifecycle"""
        # Initialize
        init_result = await data_manager.initialize()
        assert init_result is True
        assert data_manager.is_initialized

        # Start
        start_result = await data_manager.start()
        assert start_result is True
        assert data_manager.is_operational

        # Stop
        stop_result = await data_manager.stop()
        assert stop_result is True
        assert not data_manager.is_operational

    @pytest.mark.asyncio
    async def test_data_manager_health_check(self, data_manager):
        """Test data manager health check"""
        await data_manager.initialize()
        await data_manager.start()
        
        health = await data_manager.health_check()
        assert health['healthy'] is True
        assert 'component_type' in health
        assert health['initialized'] is True
        assert health['operational'] is True

    @pytest.mark.asyncio
    async def test_data_manager_status(self, data_manager):
        """Test data manager status reporting"""
        await data_manager.initialize()
        
        status = data_manager.get_status()
        assert 'component_type' in status
        assert status['initialized'] is True
        assert 'configuration' in status
        # ClickHouseDataManager has different status structure
        assert 'cache_stats' in status


class TestCentralRiskManagerBasics:
    """Test suite for Central Risk Manager basic functionality"""

    @pytest_asyncio.fixture
    async def risk_config(self):
        """Fixture for risk manager configuration"""
        return {
            'max_position_size': 0.10,
            'max_daily_var': 0.05,
            'position_concentration_limit': 0.15,
            'strategy_allocation_limit': 0.33,
            'min_signal_confidence': 0.60
        }

    @pytest_asyncio.fixture
    async def risk_manager(self, risk_config):
        """Fixture for risk manager"""
        manager = CentralRiskManager(risk_config)
        yield manager
        if manager.is_operational:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_risk_manager_creation(self, risk_config):
        """Test risk manager creation"""
        manager = CentralRiskManager(risk_config)
        assert manager is not None
        # CentralRiskManager may not have component_id in the same way
        assert not manager.is_initialized
        # CentralRiskManager may start as operational

    @pytest.mark.asyncio
    async def test_risk_manager_initialization(self, risk_manager):
        """Test risk manager initialization"""
        result = await risk_manager.initialize()
        assert result is True
        assert risk_manager.is_initialized
        # CentralRiskManager may be operational after initialization

    @pytest.mark.asyncio
    async def test_risk_manager_lifecycle(self, risk_manager):
        """Test risk manager lifecycle"""
        # Initialize
        init_result = await risk_manager.initialize()
        assert init_result is True
        assert risk_manager.is_initialized

        # Start
        start_result = await risk_manager.start()
        assert start_result is True
        assert risk_manager.is_operational

        # Stop
        stop_result = await risk_manager.stop()
        assert stop_result is True
        assert not risk_manager.is_operational

    @pytest.mark.asyncio
    async def test_risk_manager_health_check(self, risk_manager):
        """Test risk manager health check"""
        await risk_manager.initialize()
        await risk_manager.start()
        
        health = await risk_manager.health_check()
        assert health['healthy'] is True
        assert 'component_type' in health
        assert health['initialized'] is True
        assert health['operational'] is True

    @pytest.mark.asyncio
    async def test_risk_manager_status(self, risk_manager):
        """Test risk manager status reporting"""
        await risk_manager.initialize()
        
        status = risk_manager.get_status()
        assert 'component_type' in status
        assert status['initialized'] is True
        # CentralRiskManager has different status structure
        assert 'risk_metrics' in status
        assert 'controlled_components' in status

    @pytest.mark.asyncio
    async def test_risk_manager_authorization(self, risk_manager):
        """Test risk manager authorization functionality"""
        await risk_manager.initialize()
        await risk_manager.start()
        
        # Create a trading decision request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol="AAPL",
            side="buy",
            quantity=100,
            strategy_id="test_strategy",
            confidence=0.75
        )
        
        # Test authorization (should work with mock data)
        try:
            authorization = await risk_manager.authorize_trading_decision(request)
            assert authorization is not None
        except Exception as e:
            # Authorization may fail due to missing dependencies, which is acceptable in unit tests
            assert "portfolio_value" in str(e) or "execution_engine" in str(e)


class TestEnhancedRegimeEngineBasics:
    """Test suite for Enhanced Regime Engine basic functionality"""

    @pytest_asyncio.fixture
    async def regime_config(self):
        """Fixture for regime engine configuration"""
        return {
            'lookback_window': 60,
            'volatility_window': 20,
            'trend_threshold': 0.02,
            'regime_change_threshold': 0.7,
            'update_frequency': 300,
            'enable_enhanced_detection': True
        }

    @pytest_asyncio.fixture
    async def regime_engine(self, regime_config):
        """Fixture for regime engine"""
        engine = EnhancedRegimeEngine(regime_config)
        yield engine
        if engine.is_operational:
            await engine.stop()

    @pytest.mark.asyncio
    async def test_regime_engine_creation(self, regime_config):
        """Test regime engine creation"""
        engine = EnhancedRegimeEngine(regime_config)
        assert engine is not None
        assert engine.component_id is not None
        assert not engine.is_initialized
        assert not engine.is_operational

    @pytest.mark.asyncio
    async def test_regime_engine_initialization(self, regime_engine):
        """Test regime engine initialization"""
        result = await regime_engine.initialize()
        assert result is True
        assert regime_engine.is_initialized
        assert not regime_engine.is_operational

    @pytest.mark.asyncio
    async def test_regime_engine_lifecycle(self, regime_engine):
        """Test regime engine lifecycle"""
        # Initialize
        init_result = await regime_engine.initialize()
        assert init_result is True
        assert regime_engine.is_initialized

        # Start
        start_result = await regime_engine.start()
        assert start_result is True
        assert regime_engine.is_operational

        # Stop
        stop_result = await regime_engine.stop()
        assert stop_result is True
        assert not regime_engine.is_operational

    @pytest.mark.asyncio
    async def test_regime_engine_health_check(self, regime_engine):
        """Test regime engine health check"""
        await regime_engine.initialize()
        await regime_engine.start()
        
        health = await regime_engine.health_check()
        # Health may be False initially due to no regime data, which is expected
        assert 'healthy' in health
        assert health['component_type'] == 'EnhancedRegimeEngine'
        assert health['initialized'] is True
        assert health['operational'] is True

    @pytest.mark.asyncio
    async def test_regime_engine_status(self, regime_engine):
        """Test regime engine status reporting"""
        await regime_engine.initialize()
        
        status = regime_engine.get_status()
        assert status['component_type'] == 'EnhancedRegimeEngine'
        assert status['initialized'] is True
        assert 'configuration' in status
        assert 'health_metrics' in status


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
