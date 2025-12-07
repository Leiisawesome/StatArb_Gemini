#!/usr/bin/env python3
"""
Unit Tests for Enhanced Regime Engine
=====================================

Tests for the EnhancedRegimeEngine (Enhanced Market Regime Analysis)
with ISystemComponent integration.

Author: StatArb_Gemini Testing Team
Version: 1.0.0
"""

import pytest
import pytest_asyncio

# Import enhanced regime components
from core_engine.regime.engine import (
    EnhancedRegimeEngine
)


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
