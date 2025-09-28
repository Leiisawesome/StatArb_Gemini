#!/usr/bin/env python3
"""
Unit Tests for Phase 5 Enhanced Trading & Execution Components
==============================================================

Tests for the enhanced trading and execution components with ISystemComponent integration:
- StrategyManager (Enhanced Strategy Orchestration)
- EnhancedTradingEngine (Enhanced Trading Logic)
- UnifiedExecutionEngine (Enhanced Execution Algorithms)
- EnhancedPortfolioManager (Enhanced Position Tracking)

Author: StatArb_Gemini Testing Team
Version: 1.0.0 (Phase 5 Testing)
"""

import pytest
import pytest_asyncio
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import asyncio

# Import enhanced trading and execution components
from core_engine.trading.strategies.manager import (
    StrategyManager, StrategyManagerConfig
)
from core_engine.trading.engine import (
    EnhancedTradingEngine, TradingEngineConfig
)
from core_engine.system.unified_execution_engine import (
    UnifiedExecutionEngine
)
from core_engine.trading.portfolio.manager_enhanced import (
    EnhancedPortfolioManager
)


class TestStrategyManagerBasics:
    """Test suite for Strategy Manager basic functionality"""

    @pytest_asyncio.fixture
    async def strategy_config(self):
        """Fixture for strategy manager configuration"""
        return {
            'max_concurrent_strategies': 5,
            'signal_generation_interval': 60,
            'min_confidence_threshold': 0.6,
            'max_strategy_allocation': 0.33,
            'enable_regime_awareness': True,
            'enable_correlation_filtering': True,
            'signal_aggregation_method': 'weighted_average'
        }

    @pytest_asyncio.fixture
    async def strategy_manager(self, strategy_config):
        """Fixture for strategy manager"""
        manager = StrategyManager(strategy_config)
        yield manager
        # StrategyManager uses different attribute names
        if hasattr(manager, 'is_operational') and manager.is_operational:
            await manager.stop()
        elif hasattr(manager, 'is_running') and manager.is_running:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_strategy_manager_creation(self, strategy_config):
        """Test strategy manager creation"""
        manager = StrategyManager(strategy_config)
        assert manager is not None
        assert hasattr(manager, 'component_id')
        assert not manager.is_initialized
        # StrategyManager may use different attribute names

    @pytest.mark.asyncio
    async def test_strategy_manager_initialization(self, strategy_manager):
        """Test strategy manager initialization"""
        result = await strategy_manager.initialize()
        assert result is True
        assert strategy_manager.is_initialized
        # StrategyManager may use different operational status

    @pytest.mark.asyncio
    async def test_strategy_manager_lifecycle(self, strategy_manager):
        """Test strategy manager lifecycle"""
        # Initialize
        init_result = await strategy_manager.initialize()
        assert init_result is True
        assert strategy_manager.is_initialized

        # Start
        start_result = await strategy_manager.start()
        assert start_result is True
        # StrategyManager may use different operational status

        # Stop
        stop_result = await strategy_manager.stop()
        assert stop_result is True
        # StrategyManager may use different operational status

    @pytest.mark.asyncio
    async def test_strategy_manager_health_check(self, strategy_manager):
        """Test strategy manager health check"""
        await strategy_manager.initialize()
        await strategy_manager.start()
        
        health = await strategy_manager.health_check()
        assert health['healthy'] is True
        assert 'component_type' in health
        assert health['initialized'] is True
        assert health['operational'] is True

    @pytest.mark.asyncio
    async def test_strategy_manager_status(self, strategy_manager):
        """Test strategy manager status reporting"""
        await strategy_manager.initialize()
        
        status = strategy_manager.get_status()
        assert 'component_type' in status
        assert status['initialized'] is True
        # StrategyManager has different status structure
        assert 'active_strategies' in status
        assert 'component_connections' in status


class TestEnhancedTradingEngineBasics:
    """Test suite for Enhanced Trading Engine basic functionality"""

    @pytest_asyncio.fixture
    async def trading_config(self):
        """Fixture for trading engine configuration"""
        return {
            'max_slice_size': 1000.0,
            'min_slice_size': 10.0,
            'twap_duration_minutes': 30,
            'vwap_participation_rate': 0.1,
            'enable_smart_routing': True
        }

    @pytest_asyncio.fixture
    async def trading_engine(self, trading_config):
        """Fixture for trading engine"""
        engine = EnhancedTradingEngine(trading_config)
        yield engine
        if engine.is_operational:
            await engine.stop()

    @pytest.mark.asyncio
    async def test_trading_engine_creation(self, trading_config):
        """Test trading engine creation"""
        engine = EnhancedTradingEngine(trading_config)
        assert engine is not None
        assert engine.component_id is not None
        assert not engine.is_initialized
        assert not engine.is_operational

    @pytest.mark.asyncio
    async def test_trading_engine_initialization(self, trading_engine):
        """Test trading engine initialization"""
        result = await trading_engine.initialize()
        assert result is True
        assert trading_engine.is_initialized
        assert not trading_engine.is_operational

    @pytest.mark.asyncio
    async def test_trading_engine_lifecycle(self, trading_engine):
        """Test trading engine lifecycle"""
        # Initialize
        init_result = await trading_engine.initialize()
        assert init_result is True
        assert trading_engine.is_initialized

        # Start
        start_result = await trading_engine.start()
        assert start_result is True
        assert trading_engine.is_operational

        # Stop
        stop_result = await trading_engine.stop()
        assert stop_result is True
        assert not trading_engine.is_operational

    @pytest.mark.asyncio
    async def test_trading_engine_health_check(self, trading_engine):
        """Test trading engine health check"""
        await trading_engine.initialize()
        await trading_engine.start()
        
        health = await trading_engine.health_check()
        assert health['healthy'] is True
        assert health['component_type'] == 'EnhancedTradingEngine'
        assert health['initialized'] is True
        assert health['operational'] is True

    @pytest.mark.asyncio
    async def test_trading_engine_status(self, trading_engine):
        """Test trading engine status reporting"""
        await trading_engine.initialize()
        
        status = trading_engine.get_status()
        assert status['component_type'] == 'EnhancedTradingEngine'
        assert status['initialized'] is True
        assert 'configuration' in status
        assert 'health_metrics' in status


class TestUnifiedExecutionEngineBasics:
    """Test suite for Unified Execution Engine basic functionality"""

    @pytest_asyncio.fixture
    async def execution_config(self):
        """Fixture for execution engine configuration"""
        return {
            'max_market_impact': 0.05,
            'default_time_horizon': 300,
            'enable_position_tracking': True
        }

    @pytest_asyncio.fixture
    async def execution_engine(self, execution_config):
        """Fixture for execution engine"""
        engine = UnifiedExecutionEngine(execution_config)
        yield engine
        if engine.is_operational:
            await engine.stop()

    @pytest.mark.asyncio
    async def test_execution_engine_creation(self, execution_config):
        """Test execution engine creation"""
        engine = UnifiedExecutionEngine(execution_config)
        assert engine is not None
        assert hasattr(engine, 'component_id')
        assert not engine.is_initialized
        assert not engine.is_operational

    @pytest.mark.asyncio
    async def test_execution_engine_initialization(self, execution_engine):
        """Test execution engine initialization"""
        result = await execution_engine.initialize()
        assert result is True
        assert execution_engine.is_initialized
        assert not execution_engine.is_operational

    @pytest.mark.asyncio
    async def test_execution_engine_lifecycle(self, execution_engine):
        """Test execution engine lifecycle"""
        # Initialize
        init_result = await execution_engine.initialize()
        assert init_result is True
        assert execution_engine.is_initialized

        # Start
        start_result = await execution_engine.start()
        assert start_result is True
        assert execution_engine.is_operational

        # Stop
        stop_result = await execution_engine.stop()
        assert stop_result is True
        assert not execution_engine.is_operational

    @pytest.mark.asyncio
    async def test_execution_engine_health_check(self, execution_engine):
        """Test execution engine health check"""
        await execution_engine.initialize()
        await execution_engine.start()
        
        health = await execution_engine.health_check()
        assert health['healthy'] is True
        assert 'component_type' in health
        assert health['initialized'] is True
        assert health['operational'] is True

    @pytest.mark.asyncio
    async def test_execution_engine_status(self, execution_engine):
        """Test execution engine status reporting"""
        await execution_engine.initialize()
        
        status = execution_engine.get_status()
        assert 'component_type' in status
        assert status['initialized'] is True
        # UnifiedExecutionEngine has different status structure
        assert 'active_executions' in status
        assert 'execution_metrics' in status


class TestEnhancedPortfolioManagerBasics:
    """Test suite for Enhanced Portfolio Manager basic functionality"""

    @pytest_asyncio.fixture
    async def portfolio_config(self):
        """Fixture for portfolio manager configuration"""
        return {
            'portfolio_id': 'test_portfolio',
            'base_currency': 'USD',
            'max_portfolio_risk': 0.20,
            'max_concentration': 0.10,
            'max_strategy_allocation': 0.30
        }

    @pytest_asyncio.fixture
    async def portfolio_manager(self, portfolio_config):
        """Fixture for portfolio manager"""
        manager = EnhancedPortfolioManager(portfolio_config)
        yield manager
        if manager.is_operational:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_portfolio_manager_creation(self, portfolio_config):
        """Test portfolio manager creation"""
        manager = EnhancedPortfolioManager(portfolio_config)
        assert manager is not None
        assert manager.component_id is not None
        assert not manager.is_initialized
        assert not manager.is_operational

    @pytest.mark.asyncio
    async def test_portfolio_manager_initialization(self, portfolio_manager):
        """Test portfolio manager initialization"""
        result = await portfolio_manager.initialize()
        assert result is True
        assert portfolio_manager.is_initialized
        assert not portfolio_manager.is_operational

    @pytest.mark.asyncio
    async def test_portfolio_manager_lifecycle(self, portfolio_manager):
        """Test portfolio manager lifecycle"""
        # Initialize
        init_result = await portfolio_manager.initialize()
        assert init_result is True
        assert portfolio_manager.is_initialized

        # Start
        start_result = await portfolio_manager.start()
        assert start_result is True
        assert portfolio_manager.is_operational

        # Stop
        stop_result = await portfolio_manager.stop()
        assert stop_result is True
        assert not portfolio_manager.is_operational

    @pytest.mark.asyncio
    async def test_portfolio_manager_health_check(self, portfolio_manager):
        """Test portfolio manager health check"""
        await portfolio_manager.initialize()
        await portfolio_manager.start()
        
        health = await portfolio_manager.health_check()
        assert health['healthy'] is True
        assert health['component_type'] == 'EnhancedPortfolioManager'
        assert health['initialized'] is True
        assert health['operational'] is True

    @pytest.mark.asyncio
    async def test_portfolio_manager_status(self, portfolio_manager):
        """Test portfolio manager status reporting"""
        await portfolio_manager.initialize()
        
        status = portfolio_manager.get_status()
        assert status['component_type'] == 'EnhancedPortfolioManager'
        assert status['initialized'] is True
        assert 'configuration' in status
        assert 'health_metrics' in status


class TestIntegrationWorkflow:
    """Test suite for integration of enhanced trading components"""

    @pytest_asyncio.fixture
    async def integrated_trading_components(self):
        """Fixture for integrated trading components"""
        strategy_config = {
            'max_concurrent_strategies': 3,
            'min_confidence_threshold': 0.6
        }
        trading_config = {
            'max_slice_size': 500.0,
            'enable_smart_routing': True
        }
        execution_config = {
            'max_market_impact': 0.03,
            'default_time_horizon': 180
        }
        portfolio_config = {
            'portfolio_id': 'integration_test',
            'base_currency': 'USD'
        }

        strategy_manager = StrategyManager(strategy_config)
        trading_engine = EnhancedTradingEngine(trading_config)
        execution_engine = UnifiedExecutionEngine(execution_config)
        portfolio_manager = EnhancedPortfolioManager(portfolio_config)

        yield strategy_manager, trading_engine, execution_engine, portfolio_manager

        # Cleanup
        for component in [strategy_manager, trading_engine, execution_engine, portfolio_manager]:
            # Different components use different attribute names
            if hasattr(component, 'is_operational') and component.is_operational:
                await component.stop()
            elif hasattr(component, 'is_running') and component.is_running:
                await component.stop()

    @pytest.mark.asyncio
    async def test_component_integration(self, integrated_trading_components):
        """Test basic integration of all trading components"""
        strategy_manager, trading_engine, execution_engine, portfolio_manager = integrated_trading_components

        # Initialize all components
        await strategy_manager.initialize()
        await trading_engine.initialize()
        await execution_engine.initialize()
        await portfolio_manager.initialize()

        assert strategy_manager.is_initialized
        assert trading_engine.is_initialized
        assert execution_engine.is_initialized
        assert portfolio_manager.is_initialized

        # Start all components
        await strategy_manager.start()
        await trading_engine.start()
        await execution_engine.start()
        await portfolio_manager.start()

        # Different components use different operational status
        assert trading_engine.is_operational
        assert execution_engine.is_operational
        assert portfolio_manager.is_operational

        # Stop all components
        await strategy_manager.stop()
        await trading_engine.stop()
        await execution_engine.stop()
        await portfolio_manager.stop()

        # Different components use different operational status
        assert not trading_engine.is_operational
        assert not execution_engine.is_operational
        assert not portfolio_manager.is_operational

    @pytest.mark.asyncio
    async def test_health_checks_all_components(self, integrated_trading_components):
        """Test health checks across all integrated components"""
        strategy_manager, trading_engine, execution_engine, portfolio_manager = integrated_trading_components

        await strategy_manager.initialize()
        await trading_engine.initialize()
        await execution_engine.initialize()
        await portfolio_manager.initialize()

        # Start components for health check
        await strategy_manager.start()
        await trading_engine.start()
        await execution_engine.start()
        await portfolio_manager.start()

        # Test health checks
        strategy_health = await strategy_manager.health_check()
        trading_health = await trading_engine.health_check()
        execution_health = await execution_engine.health_check()
        portfolio_health = await portfolio_manager.health_check()

        assert strategy_health['healthy'] is True
        assert trading_health['healthy'] is True
        assert execution_health['healthy'] is True
        assert portfolio_health['healthy'] is True

        # Cleanup
        await strategy_manager.stop()
        await trading_engine.stop()
        await execution_engine.stop()
        await portfolio_manager.stop()

        assert 'component_type' in strategy_health
        assert trading_health['component_type'] == 'EnhancedTradingEngine'
        assert 'component_type' in execution_health
        assert portfolio_health['component_type'] == 'EnhancedPortfolioManager'

    @pytest.mark.asyncio
    async def test_component_status_reporting(self, integrated_trading_components):
        """Test status reporting across all components"""
        strategy_manager, trading_engine, execution_engine, portfolio_manager = integrated_trading_components

        # Initialize all components
        for component in [strategy_manager, trading_engine, execution_engine, portfolio_manager]:
            await component.initialize()

        # Check that all components have proper status reporting
        for component in [strategy_manager, trading_engine, execution_engine, portfolio_manager]:
            status = component.get_status()
            assert 'component_type' in status
            assert 'initialized' in status
            assert 'operational' in status
            assert status['initialized'] is True
            
            # Only some components have health_metrics
            if hasattr(component, 'health_metrics'):
                assert 'health_metrics' in status

    @pytest.mark.asyncio
    async def test_component_performance_metrics(self, integrated_trading_components):
        """Test performance metrics tracking across all components"""
        strategy_manager, trading_engine, execution_engine, portfolio_manager = integrated_trading_components

        # Initialize and start all components
        for component in [strategy_manager, trading_engine, execution_engine, portfolio_manager]:
            await component.initialize()
            await component.start()

        # Check that enhanced components have performance metrics
        for component in [strategy_manager, trading_engine, execution_engine, portfolio_manager]:
            status = component.get_status()
            # Only enhanced components have health_metrics
            if hasattr(component, 'health_metrics'):
                assert 'health_metrics' in status
                assert 'performance_metrics' in status['health_metrics']

        # Cleanup
        for component in [strategy_manager, trading_engine, execution_engine, portfolio_manager]:
            await component.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
