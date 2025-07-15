"""
Unit Tests for Infrastructure Components

This module provides comprehensive unit tests for all infrastructure
components including database, messaging, configuration, and caching.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import shutil

# Infrastructure imports (adjust paths as needed)
from new_structure.infrastructure.database.database_manager import DatabaseManager
from new_structure.infrastructure.database.redis_client import RedisClient
from new_structure.infrastructure.database.cache_strategy import CacheStrategy, CacheType
from new_structure.infrastructure.config.base_config import BaseConfig, SystemConfig
from new_structure.infrastructure.config.database_config import DatabaseConfig, ClickHouseConfig
from new_structure.infrastructure.config.trading_config import TradingConfig, StrategyConfig
from new_structure.infrastructure.config.risk_config import RiskConfig, PositionRiskConfig


class TestDatabaseManager:
    """Test database manager functionality"""
    
    @pytest.fixture
    def db_config(self):
        """Create test database configuration"""
        return DatabaseConfig()
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        return mock_client
    
    @pytest.fixture
    def mock_clickhouse_client(self):
        """Mock ClickHouse client"""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.execute.return_value = []
        return mock_client
    
    @pytest.fixture
    async def db_manager(self, db_config, mock_redis_client, mock_clickhouse_client):
        """Create database manager instance"""
        with patch('new_structure.infrastructure.database.database_manager.RedisClient', return_value=mock_redis_client), \
             patch('new_structure.infrastructure.database.database_manager.ClickHouseClient', return_value=mock_clickhouse_client):
            
            manager = DatabaseManager(db_config)
            await manager.initialize()
            yield manager
            await manager.close()
    
    @pytest.mark.asyncio
    async def test_initialization(self, db_manager):
        """Test database manager initialization"""
        assert db_manager.redis_client is not None
        assert db_manager.clickhouse_client is not None
        assert db_manager.cache_strategy is not None
        
        # Test health check
        health = await db_manager.health_check()
        assert health["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_cache_operations(self, db_manager):
        """Test cache operations"""
        # Test cache set/get
        test_data = {"test": "data", "value": 123}
        
        # Mock cache operations
        db_manager.cache_strategy.set = AsyncMock(return_value=True)
        db_manager.cache_strategy.get = AsyncMock(return_value=test_data)
        
        # Test set
        result = await db_manager.cache_set(
            CacheType.MARKET_DATA, "test_key", test_data
        )
        assert result is True
        
        # Test get
        cached_data = await db_manager.cache_get(
            CacheType.MARKET_DATA, "test_key"
        )
        assert cached_data == test_data
    
    @pytest.mark.asyncio
    async def test_database_queries(self, db_manager):
        """Test database query operations"""
        # Mock query results
        expected_result = [{"symbol": "AAPL", "price": 150.0}]
        db_manager.clickhouse_client.execute.return_value = expected_result
        
        # Test query execution
        result = await db_manager.execute_query(
            "SELECT symbol, price FROM market_data WHERE symbol = 'AAPL'"
        )
        assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_transaction_handling(self, db_manager):
        """Test transaction management"""
        # Mock transaction methods
        db_manager.clickhouse_client.begin_transaction = AsyncMock()
        db_manager.clickhouse_client.commit_transaction = AsyncMock()
        db_manager.clickhouse_client.rollback_transaction = AsyncMock()
        
        # Test successful transaction
        async with db_manager.transaction():
            await db_manager.execute_query("INSERT INTO test_table VALUES (1, 'test')")
        
        # Verify transaction methods called
        db_manager.clickhouse_client.begin_transaction.assert_called_once()
        db_manager.clickhouse_client.commit_transaction.assert_called_once()


class TestRedisClient:
    """Test Redis client functionality"""
    
    @pytest.fixture
    def redis_config(self):
        """Create test Redis configuration"""
        from new_structure.infrastructure.config.database_config import RedisConfig
        return RedisConfig(host="localhost", port=6379, database=1)
    
    @pytest.fixture
    def mock_redis_pool(self):
        """Mock Redis connection pool"""
        mock_pool = AsyncMock()
        mock_pool.get.return_value = "test_value"
        mock_pool.set.return_value = True
        mock_pool.delete.return_value = 1
        mock_pool.ping.return_value = True
        return mock_pool
    
    @pytest.mark.asyncio
    async def test_redis_operations(self, redis_config, mock_redis_pool):
        """Test basic Redis operations"""
        with patch('aioredis.from_url', return_value=mock_redis_pool):
            client = RedisClient(redis_config)
            await client.connect()
            
            # Test set
            result = await client.set("test_key", "test_value", ex=300)
            assert result is True
            
            # Test get
            value = await client.get("test_key")
            assert value == "test_value"
            
            # Test delete
            deleted = await client.delete("test_key")
            assert deleted == 1
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_redis_pipeline(self, redis_config, mock_redis_pool):
        """Test Redis pipeline operations"""
        mock_pipeline = AsyncMock()
        mock_pipeline.execute.return_value = ["OK", "test_value", 1]
        mock_redis_pool.pipeline.return_value = mock_pipeline
        
        with patch('aioredis.from_url', return_value=mock_redis_pool):
            client = RedisClient(redis_config)
            await client.connect()
            
            # Test pipeline execution
            results = await client.pipeline([
                ("set", "key1", "value1"),
                ("get", "key1"),
                ("delete", "key1")
            ])
            
            assert len(results) == 3
            await client.close()


class TestCacheStrategy:
    """Test cache strategy functionality"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for cache strategy"""
        mock_client = AsyncMock()
        mock_client.get.return_value = json.dumps({"test": "data"})
        mock_client.setex.return_value = True
        mock_client.delete.return_value = 1
        mock_client.keys.return_value = ["cache:test:key1", "cache:test:key2"]
        return mock_client
    
    @pytest.fixture
    def cache_strategy(self, mock_redis_client):
        """Create cache strategy instance"""
        return CacheStrategy(mock_redis_client)
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache_strategy):
        """Test cache key generation"""
        key = cache_strategy.get_cache_key(CacheType.MARKET_DATA, "AAPL")
        assert key.startswith("market_data:")
        assert "AAPL" in key
        
        # Test with timestamp
        timestamp = datetime.now()
        key_with_time = cache_strategy.get_cache_key(
            CacheType.MARKET_DATA, "AAPL", timestamp
        )
        assert timestamp.strftime("%Y%m%d") in key_with_time
    
    @pytest.mark.asyncio
    async def test_cache_operations(self, cache_strategy):
        """Test cache set/get operations"""
        test_data = {"symbol": "AAPL", "price": 150.0}
        
        # Test set
        result = await cache_strategy.set(
            CacheType.MARKET_DATA, "AAPL", test_data
        )
        assert result is True
        
        # Test get
        cached_data = await cache_strategy.get(
            CacheType.MARKET_DATA, "AAPL"
        )
        assert cached_data == {"test": "data"}  # Mocked response
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_strategy):
        """Test cache invalidation"""
        # Test pattern invalidation
        invalidated_count = await cache_strategy.invalidate_pattern(
            CacheType.MARKET_DATA, "AAPL*"
        )
        assert invalidated_count == 2  # Mocked response


class TestConfigurationClasses:
    """Test configuration classes"""
    
    def test_system_config_validation(self):
        """Test system configuration validation"""
        # Valid config
        config = SystemConfig(max_workers=4, memory_limit_gb=8)
        config.validate()  # Should not raise
        
        # Invalid config
        with pytest.raises(ValueError):
            invalid_config = SystemConfig(max_workers=-1)
            invalid_config.validate()
    
    def test_database_config_validation(self):
        """Test database configuration validation"""
        config = DatabaseConfig()
        config.validate()  # Should not raise
        
        # Test individual database configs
        clickhouse_config = ClickHouseConfig(host="localhost", port=9000)
        clickhouse_config.validate()
    
    def test_trading_config_validation(self):
        """Test trading configuration validation"""
        config = TradingConfig()
        config.validate()  # Should not raise
        
        # Test strategy config
        strategy_config = StrategyConfig(
            universe_size=100,
            min_correlation=0.7,
            max_correlation=0.95
        )
        strategy_config.validate()
    
    def test_risk_config_validation(self):
        """Test risk configuration validation"""
        config = RiskConfig()
        config.validate()  # Should not raise
        
        # Test position risk
        position_config = PositionRiskConfig(
            max_position_value=Decimal("1000000"),
            max_position_weight=0.05
        )
        position_config.validate()
    
    def test_config_serialization(self):
        """Test configuration serialization"""
        config = SystemConfig(system_name="TestSystem", max_workers=8)
        
        # Test to_dict
        config_dict = config.to_dict()
        assert config_dict["system_name"] == "TestSystem"
        assert config_dict["max_workers"] == 8
        
        # Test to_yaml
        yaml_str = config.to_yaml()
        assert "system_name: TestSystem" in yaml_str
        
        # Test to_json
        json_str = config.to_json()
        assert "TestSystem" in json_str
    
    def test_config_from_dict(self):
        """Test configuration creation from dictionary"""
        config_data = {
            "system_name": "TestSystem",
            "max_workers": 8,
            "environment": "testing"
        }
        
        config = SystemConfig.from_dict(config_data)
        assert config.system_name == "TestSystem"
        assert config.max_workers == 8
    
    def test_config_file_operations(self):
        """Test configuration file save/load"""
        config = SystemConfig(system_name="TestSystem", max_workers=8)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            
            # Save config
            config.save_to_file(config_path, "yaml")
            assert config_path.exists()
            
            # Load config
            loaded_config = SystemConfig.from_yaml_file(config_path)
            assert loaded_config.system_name == "TestSystem"
            assert loaded_config.max_workers == 8


class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_database_cache_integration(self):
        """Test database and cache integration"""
        # Mock components
        mock_redis = AsyncMock()
        mock_clickhouse = AsyncMock()
        
        # Setup database manager
        with patch('new_structure.infrastructure.database.database_manager.RedisClient', return_value=mock_redis), \
             patch('new_structure.infrastructure.database.database_manager.ClickHouseClient', return_value=mock_clickhouse):
            
            db_config = DatabaseConfig()
            db_manager = DatabaseManager(db_config)
            await db_manager.initialize()
            
            # Test cache-through pattern
            mock_redis.get.return_value = None  # Cache miss
            mock_clickhouse.execute.return_value = [{"symbol": "AAPL", "price": 150.0}]
            mock_redis.setex.return_value = True  # Cache set
            
            # Simulate data retrieval with cache
            cache_key = "market_data:AAPL"
            cached_data = await db_manager.cache_get(CacheType.MARKET_DATA, "AAPL")
            
            if cached_data is None:
                # Cache miss - fetch from database
                data = await db_manager.execute_query(
                    "SELECT symbol, price FROM market_data WHERE symbol = 'AAPL'"
                )
                # Set in cache
                await db_manager.cache_set(CacheType.MARKET_DATA, "AAPL", data[0])
            
            await db_manager.close()
    
    def test_configuration_hierarchy(self):
        """Test configuration inheritance and composition"""
        # Test that complex configs validate their sub-components
        trading_config = TradingConfig()
        trading_config.validate()  # Should validate all sub-configs
        
        risk_config = RiskConfig()
        risk_config.validate()  # Should validate all sub-configs
        
        # Test configuration merging
        base_config = {"environment": "testing", "debug": True}
        
        system_config = SystemConfig.from_dict({
            **base_config,
            "max_workers": 4
        })
        
        assert system_config.debug is True
        assert system_config.max_workers == 4


# Pytest fixtures for test setup
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


# Test configuration
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
