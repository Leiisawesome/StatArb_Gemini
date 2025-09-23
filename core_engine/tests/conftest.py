"""
Testing Framework - Core Engine
==============================

Automated testing framework with pytest integration for core_engine components.
Provides fixtures, utilities, and test patterns for comprehensive testing.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Generator, AsyncGenerator
from unittest.mock import Mock, MagicMock

from ..config.unified_config import UnifiedConfig, init_config
from ..utils.dependency_injection import DependencyInjectionContainer, reset_container
from ..utils.logging import LogConfig, init_logging
from ..utils.health import HealthMonitor

# Test configuration
@pytest.fixture(scope="session")
def test_config_dir(tmp_path_factory) -> Path:
    """Create a temporary directory for test configuration"""
    return tmp_path_factory.mktemp("core_engine_test_config")

@pytest.fixture(scope="session")
def test_log_dir(tmp_path_factory) -> Path:
    """Create a temporary directory for test logs"""
    return tmp_path_factory.mktemp("core_engine_test_logs")

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory) -> Path:
    """Create a temporary directory for test data"""
    return tmp_path_factory.mktemp("core_engine_test_data")

@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for individual tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def async_fixture():
    """Base async fixture for async tests"""
    yield

# Configuration fixtures
@pytest.fixture(scope="session")
def test_config(test_config_dir: Path) -> UnifiedConfig:
    """Initialize test configuration"""
    # Create test config file
    config_file = test_config_dir / "config.yaml"
    config_data = {
        "system": {
            "environment": "test",
            "debug": True
        },
        "risk": {
            "max_position_size": 0.1,
            "max_daily_var": 0.05
        },
        "data": {
            "cache_enabled": False,
            "validate_data": False
        },
        "logging": {
            "level": "DEBUG",
            "console_output": False
        }
    }

    import yaml
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    # Initialize config
    config = init_config(str(test_config_dir))
    return config

# Dependency injection fixtures
@pytest.fixture(scope="function")
def di_container() -> Generator[DependencyInjectionContainer, None, None]:
    """Create a fresh dependency injection container for each test"""
    reset_container()
    from ..utils.dependency_injection import get_container
    container = get_container()
    yield container
    reset_container()

# Logging fixtures
@pytest.fixture(scope="function")
def test_logger(test_log_dir: Path):
    """Initialize test logging"""
    log_config = LogConfig(
        level="DEBUG",
        format="structured",
        file_path=test_log_dir / "test.log",
        console_output=False
    )
    logger = init_logging(log_config)
    return logger

# Mock fixtures for external dependencies
@pytest.fixture(scope="function")
def mock_data_provider():
    """Mock data provider for testing"""
    mock = Mock()
    mock.get_historical_data.return_value = create_mock_market_data()
    mock.get_current_price.return_value = 100.0
    mock.get_multiple_prices.return_value = {"AAPL": 150.0, "GOOGL": 2500.0}
    return mock

@pytest.fixture(scope="function")
def mock_broker():
    """Mock broker for testing"""
    mock = Mock()
    mock.connect.return_value = True
    mock.connected = True
    mock.submit_order.return_value = True
    mock.get_account_info.return_value = {
        "cash": 100000.0,
        "total_value": 100000.0,
        "buying_power": 100000.0
    }
    mock.get_positions.return_value = {}
    return mock

@pytest.fixture(scope="function")
def mock_risk_manager():
    """Mock risk manager for testing"""
    mock = Mock()
    mock.check_trade_risk.return_value = Mock(
        approved=True,
        risk_level="low",
        reasons=[],
        warnings=[]
    )
    return mock

# Test data creation utilities
def create_mock_market_data(symbol: str = "AAPL", days: int = 100):
    """Create mock market data for testing"""
    import pandas as pd
    import numpy as np

    dates = pd.date_range(start="2023-01-01", periods=days, freq="D")
    np.random.seed(42)  # For reproducible tests

    # Generate realistic price data
    returns = np.random.normal(0.001, 0.02, days)
    prices = 100 * np.exp(np.cumsum(returns))

    # Create OHLCV data
    high_mult = 1 + np.random.uniform(0, 0.05, days)
    low_mult = 1 - np.random.uniform(0, 0.05, days)
    volume = np.random.uniform(1000000, 10000000, days)

    data = pd.DataFrame({
        'Open': prices * (1 + np.random.normal(0, 0.01, days)),
        'High': prices * high_mult,
        'Low': prices * low_mult,
        'Close': prices,
        'Volume': volume
    }, index=dates)

    # Ensure OHLC consistency
    data['High'] = data[['Open', 'Close', 'High']].max(axis=1)
    data['Low'] = data[['Open', 'Close', 'Low']].min(axis=1)

    return data

def create_mock_trading_signal(symbol: str = "AAPL", signal_type: str = "BUY"):
    """Create mock trading signal for testing"""
    from ..type_definitions import TradingSignal
    import uuid
    from datetime import datetime

    return TradingSignal(
        strategy_id=str(uuid.uuid4()),
        symbol=symbol,
        signal_type=signal_type,
        strength=0.8,
        price=100.0,
        quantity=100,
        timestamp=datetime.now(),
        metadata={"test": True}
    )

def create_mock_order(symbol: str = "AAPL", side: str = "buy", quantity: float = 100):
    """Create mock order for testing"""
    from ..type_definitions import Order, OrderType, OrderSide
    import uuid

    return Order(
        symbol=symbol,
        side=OrderSide(side.lower()),
        quantity=quantity,
        order_type=OrderType.MARKET,
        order_id=str(uuid.uuid4())
    )

# Test assertion utilities
def assert_health_check_result(result, expected_status: str, component: str):
    """Assert health check result properties"""
    from ..utils.health import HealthStatus
    assert result.component == component
    assert result.status == HealthStatus(expected_status)
    assert result.message is not None
    assert result.timestamp is not None
    assert result.response_time_ms >= 0

def assert_trading_signal(signal, symbol: str, signal_type: str):
    """Assert trading signal properties"""
    assert signal.symbol == symbol
    assert signal.signal_type == signal_type
    assert 0 <= signal.strength <= 1
    assert signal.timestamp is not None

def assert_portfolio_state(portfolio, expected_cash: float, expected_positions: Dict[str, float]):
    """Assert portfolio state"""
    assert abs(portfolio.cash - expected_cash) < 0.01
    for symbol, expected_qty in expected_positions.items():
        actual_qty = portfolio.positions.get(symbol, 0)
        assert abs(actual_qty - expected_qty) < 0.01

# Async test utilities
async def async_assert_eventually(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Assert that a condition becomes true within a timeout"""
    import time
    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition_func():
            return
        await asyncio.sleep(interval)

    raise AssertionError(f"Condition not met within {timeout} seconds")

# Performance testing utilities
def time_operation(func, *args, **kwargs) -> tuple:
    """Time an operation and return result with execution time"""
    import time
    start_time = time.time()
    result = func(*args, **kwargs)
    execution_time = time.time() - start_time
    return result, execution_time

async def time_async_operation(coro) -> tuple:
    """Time an async operation and return result with execution time"""
    import time
    start_time = time.time()
    result = await coro
    execution_time = time.time() - start_time
    return result, execution_time

# Test data validation
def validate_market_data(data):
    """Validate market data structure"""
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_columns:
        assert col in data.columns, f"Missing required column: {col}"

    # Validate OHLC consistency
    assert (data['High'] >= data['Low']).all(), "High must be >= Low"
    assert (data['Open'] >= data['Low']).all(), "Open must be >= Low"
    assert (data['Open'] <= data['High']).all(), "Open must be <= High"
    assert (data['Close'] >= data['Low']).all(), "Close must be >= Low"
    assert (data['Close'] <= data['High']).all(), "Close must be <= High"
    assert (data['Volume'] >= 0).all(), "Volume must be >= 0"

# Component lifecycle testing
class ComponentTestHarness:
    """Test harness for component lifecycle testing"""

    def __init__(self, component_class, config=None):
        self.component_class = component_class
        self.config = config or {}
        self.component = None

    async def setup(self):
        """Setup component for testing"""
        self.component = self.component_class(self.config)
        if hasattr(self.component, 'initialize'):
            await self.component.initialize()
        return self.component

    async def teardown(self):
        """Teardown component after testing"""
        if self.component and hasattr(self.component, 'shutdown'):
            await self.component.shutdown()
        self.component = None

    async def __aenter__(self):
        await self.setup()
        return self.component

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.teardown()

# Pytest configuration
def pytest_configure(config):
    """Configure pytest for core_engine tests"""
    # Add custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")

    # Set asyncio mode
    config.option.asyncio_mode = "auto"

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file paths"""
    for item in items:
        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark performance tests
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)

        # Mark slow tests
        if "slow" in item.keywords:
            item.add_marker(pytest.mark.slow)