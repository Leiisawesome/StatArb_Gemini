"""
Pytest Configuration for StatArb Trading System Tests

This module provides centralized test configuration, fixtures,
and utilities for unit, integration, and performance tests.
"""

import pytest
import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from datetime import datetime
import logging

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test configuration
TEST_CONFIG = {
    'database': {
        'host': 'localhost',
        'port': 6379,
        'database': 15  # Use database 15 for testing
    },
    'cache': {
        'enabled': True,
        'ttl_seconds': 300
    },
    'market_data': {
        'mock_feeds': True,
        'simulation_mode': True
    },
    'execution': {
        'paper_trading': True,
        'mock_venues': True
    }
}


def pytest_configure(config):
    """Configure pytest markers and settings"""
    # Register custom markers
    config.addinivalue_line(
        "markers", 
        "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", 
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", 
        "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", 
        "slow: mark test as slow running test"
    )
    config.addinivalue_line(
        "markers", 
        "asyncio: mark test as async test"
    )
    config.addinivalue_line(
        "markers", 
        "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", 
        "redis: mark test as requiring Redis"
    )
    config.addinivalue_line(
        "markers", 
        "clickhouse: mark test as requiring ClickHouse"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers"""
    # Skip slow tests by default unless --runslow is given
    if config.getoption("--runslow"):
        return
    
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--runslow", 
        action="store_true", 
        default=False, 
        help="run slow tests"
    )
    parser.addoption(
        "--runintegration", 
        action="store_true", 
        default=False, 
        help="run integration tests"
    )
    parser.addoption(
        "--runperformance", 
        action="store_true", 
        default=False, 
        help="run performance tests"
    )


# Session-scoped fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration"""
    return TEST_CONFIG


@pytest.fixture(scope="session")
def temp_storage():
    """Create temporary storage directory for tests"""
    temp_dir = tempfile.mkdtemp(prefix="statarb_test_")
    temp_path = Path(temp_dir)
    
    # Create subdirectories
    (temp_path / "data").mkdir()
    (temp_path / "logs").mkdir()
    (temp_path / "models").mkdir()
    (temp_path / "config").mkdir()
    
    yield temp_path
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


# Function-scoped fixtures
@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    logger = Mock(spec=logging.Logger)
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture
def sample_market_data():
    """Generate sample market data for testing"""
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    data = []
    for symbol in symbols:
        base_price = np.random.uniform(100, 300)
        prices = base_price * np.exp(np.cumsum(np.random.normal(0, 0.02, 100)))
        
        for i, (date, price) in enumerate(zip(dates, prices)):
            data.append({
                'symbol': symbol,
                'date': date,
                'open': price * np.random.uniform(0.99, 1.01),
                'high': price * np.random.uniform(1.00, 1.03),
                'low': price * np.random.uniform(0.97, 1.00),
                'close': price,
                'volume': np.random.randint(1000000, 10000000),
                'timestamp': date
            })
    
    return pd.DataFrame(data)


# Database fixtures
@pytest.fixture
async def mock_redis_client():
    """Mock Redis client for testing"""
    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.setex.return_value = True
    mock_client.delete.return_value = 1
    mock_client.keys.return_value = []
    mock_client.flushdb.return_value = True
    
    # Pipeline support
    mock_pipeline = AsyncMock()
    mock_pipeline.execute.return_value = ["OK", "value", 1]
    mock_client.pipeline.return_value = mock_pipeline
    
    return mock_client


@pytest.fixture
async def mock_clickhouse_client():
    """Mock ClickHouse client for testing"""
    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    mock_client.execute.return_value = []
    mock_client.execute_iter.return_value = iter([])
    mock_client.insert_dataframe.return_value = True
    
    # Transaction support
    mock_client.begin_transaction = AsyncMock()
    mock_client.commit_transaction = AsyncMock()
    mock_client.rollback_transaction = AsyncMock()
    
    return mock_client


@pytest.fixture
async def mock_database_manager(mock_redis_client, mock_clickhouse_client):
    """Mock database manager for testing"""
    from unittest.mock import patch
    
    with patch('new_structure.infrastructure.database.database_manager.RedisClient', return_value=mock_redis_client), \
         patch('new_structure.infrastructure.database.database_manager.ClickHouseClient', return_value=mock_clickhouse_client):
        
        from new_structure.infrastructure.config.database_config import DatabaseConfig
        from new_structure.infrastructure.database.database_manager import DatabaseManager
        
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()
        
        yield db_manager
        
        await db_manager.close()


# Market data fixtures
@pytest.fixture
def mock_market_data_feeds():
    """Mock market data feeds for testing"""
    mock_feeds = AsyncMock()
    
    mock_feeds.connect.return_value = True
    mock_feeds.disconnect.return_value = True
    mock_feeds.subscribe.return_value = True
    mock_feeds.unsubscribe.return_value = True
    
    # Mock data responses
    mock_feeds.get_latest_price.return_value = {
        'symbol': 'AAPL',
        'price': 150.0,
        'volume': 1000000,
        'timestamp': datetime.now()
    }
    
    mock_feeds.get_historical_data.return_value = []
    mock_feeds.stream_real_time_data.return_value = []
    
    return mock_feeds


@pytest.fixture
def mock_signal_generator():
    """Mock signal generator for testing"""
    mock_generator = AsyncMock()
    
    mock_generator.generate_signals.return_value = [
        {
            'symbol': 'AAPL',
            'signal': 'BUY',
            'strength': 0.75,
            'timestamp': datetime.now(),
            'features': {'momentum': 0.05, 'mean_reversion': -0.02}
        }
    ]
    
    mock_generator.update_models.return_value = True
    mock_generator.get_feature_importance.return_value = {
        'momentum': 0.3,
        'mean_reversion': 0.25,
        'volatility': 0.2,
        'correlation': 0.15,
        'volume': 0.1
    }
    
    return mock_generator


# Portfolio and risk fixtures
@pytest.fixture
def mock_portfolio_manager():
    """Mock portfolio manager for testing"""
    mock_manager = AsyncMock()
    
    mock_manager.get_portfolio_state.return_value = {
        'positions': {
            'AAPL': {'quantity': 100, 'market_value': 15000, 'unrealized_pnl': 500},
            'MSFT': {'quantity': -50, 'market_value': -15000, 'unrealized_pnl': -200}
        },
        'cash': 70000,
        'total_value': 70300,
        'total_pnl': 300
    }
    
    mock_manager.update_positions.return_value = True
    mock_manager.calculate_performance.return_value = {
        'total_return': 0.015,
        'sharpe_ratio': 1.2,
        'max_drawdown': 0.05,
        'volatility': 0.12
    }
    
    return mock_manager


@pytest.fixture
def mock_risk_manager():
    """Mock risk manager for testing"""
    mock_manager = AsyncMock()
    
    mock_manager.assess_portfolio_risk.return_value = {
        'var_1d': 5000,
        'var_5d': 15000,
        'expected_shortfall': 7500,
        'beta': 0.8,
        'risk_score': 0.6,
        'approved': True
    }
    
    mock_manager.check_position_limits.return_value = {
        'position_limits_ok': True,
        'sector_limits_ok': True,
        'concentration_ok': True,
        'leverage_ok': True
    }
    
    mock_manager.calculate_position_size.return_value = {
        'recommended_size': 1000,
        'max_size': 1500,
        'risk_adjusted_size': 800
    }
    
    return mock_manager


# Execution fixtures
@pytest.fixture
def mock_execution_engine():
    """Mock execution engine for testing"""
    mock_engine = AsyncMock()
    
    mock_engine.place_order.return_value = {
        'order_id': 'ORD_12345',
        'status': 'ACCEPTED',
        'timestamp': datetime.now()
    }
    
    mock_engine.get_order_status.return_value = {
        'order_id': 'ORD_12345',
        'status': 'FILLED',
        'filled_quantity': 100,
        'avg_price': 149.95,
        'commission': 5.0
    }
    
    mock_engine.cancel_order.return_value = {
        'order_id': 'ORD_12345',
        'status': 'CANCELLED'
    }
    
    return mock_engine


# AI and ML fixtures
@pytest.fixture
def mock_model_registry():
    """Mock model registry for testing"""
    mock_registry = AsyncMock()
    
    mock_registry.register_model.return_value = "model_12345"
    mock_registry.get_model.return_value = {
        'model_id': 'model_12345',
        'model_name': 'test_model',
        'version': '1.0.0',
        'status': 'deployed'
    }
    
    mock_registry.list_models.return_value = []
    mock_registry.deploy_model.return_value = True
    mock_registry.retire_model.return_value = True
    
    return mock_registry


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    mock_client = AsyncMock()
    
    mock_client.generate_response.return_value = {
        'response': 'Test response from LLM',
        'confidence': 0.85,
        'tokens_used': 150
    }
    
    mock_client.embed_text.return_value = [0.1] * 1536  # OpenAI embedding dimension
    
    return mock_client


# Test utilities
class TestDataGenerator:
    """Utility class for generating test data"""
    
    @staticmethod
    def generate_orders(count: int = 10):
        """Generate test orders"""
        import random
        
        orders = []
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        for i in range(count):
            orders.append({
                'order_id': f'ORD_{i:06d}',
                'symbol': random.choice(symbols),
                'side': random.choice(['BUY', 'SELL']),
                'quantity': random.randint(10, 1000),
                'price': random.uniform(50, 300),
                'order_type': random.choice(['MARKET', 'LIMIT']),
                'timestamp': datetime.now()
            })
        
        return orders
    
    @staticmethod
    def generate_signals(count: int = 10):
        """Generate test signals"""
        import random
        
        signals = []
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        for i in range(count):
            signals.append({
                'signal_id': f'SIG_{i:06d}',
                'symbol': random.choice(symbols),
                'signal': random.choice(['BUY', 'SELL', 'HOLD']),
                'strength': random.uniform(0.1, 1.0),
                'confidence': random.uniform(0.5, 0.95),
                'timestamp': datetime.now()
            })
        
        return signals


@pytest.fixture
def test_data_generator():
    """Test data generator fixture"""
    return TestDataGenerator()


# Test result collection
def pytest_runtest_makereport(item, call):
    """Collect test results for reporting"""
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previousfailed = item


def pytest_runtest_setup(item):
    """Setup for incremental tests"""
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.xfail(f"previous test failed ({previousfailed.name})")


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_environment():
    """Automatically cleanup test environment after each test"""
    yield
    
    # Force garbage collection
    import gc
    gc.collect()
    
    # Clear any test-specific environment variables
    test_env_vars = [key for key in os.environ.keys() if key.startswith('TEST_')]
    for var in test_env_vars:
        os.environ.pop(var, None)
