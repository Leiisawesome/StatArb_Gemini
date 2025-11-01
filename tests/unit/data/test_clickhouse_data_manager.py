#!/usr/bin/env python3
"""
Unit Tests for ClickHouse Data Manager
======================================

Tests for the ClickHouseDataManager (Enhanced UnifiedDataManager)
with ISystemComponent integration.

Author: StatArb_Gemini Testing Team
Version: 1.0.0
"""

import pytest
import pytest_asyncio
from unittest.mock import patch

# Import enhanced data components
from core_engine.data.manager import (
    ClickHouseDataManager, ClickHouseDataConfig
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
        """Fixture for data manager with mocked ClickHouse connection"""
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
            manager = ClickHouseDataManager(data_config)
            yield manager
            if manager.is_operational:
                await manager.stop()

    @pytest.mark.asyncio
    async def test_data_manager_creation(self, data_config):
        """Test data manager creation"""
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=True):
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
    async def test_data_manager_health_check_without_clickhouse(self, data_config):
        """Test data manager fails fast when ClickHouse unavailable"""
        from core_engine.exceptions import ClickHouseConnectionError
        
        # This should fail fast during initialization when ClickHouse is unavailable
        with patch.object(ClickHouseDataManager, '_test_connection', return_value=False):
            with pytest.raises(ClickHouseConnectionError):
                manager = ClickHouseDataManager(data_config)
                await manager.initialize()
    
    @pytest.mark.asyncio
    async def test_data_manager_health_check_with_clickhouse(self, data_manager):
        """Test data manager health check when ClickHouse is available"""
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
