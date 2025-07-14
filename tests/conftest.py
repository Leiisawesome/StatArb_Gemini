"""
Global pytest configuration and fixtures
"""
import os
import sys
import pytest
import logging
from typing import Dict, Any
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@pytest.fixture(scope="session")
def test_config() -> Dict[Any, Any]:
    """Global test configuration"""
    return {
        "market_data": {
            "test_symbols": ["AAPL", "GOOGL", "MSFT"],
            "test_timeframe": "1d",
            "test_period": "1y"
        },
        "clickhouse": {
            "host": "localhost",
            "database": "test_statarb",
            "user": "default",
            "password": ""
        },
        "performance": {
            "latency_threshold_ms": 100,
            "memory_threshold_mb": 512
        }
    }

@pytest.fixture(scope="session")
def mock_market_data(test_config):
    """Generate mock market data for testing"""
    import pandas as pd
    import numpy as np
    
    symbols = test_config["market_data"]["test_symbols"]
    dates = pd.date_range(end=pd.Timestamp.now(), periods=252, freq='D')
    
    data = {}
    for symbol in symbols:
        price = 100 * (1 + np.random.randn(len(dates)).cumsum() * 0.02)
        data[symbol] = pd.DataFrame({
            'open': price * (1 + np.random.randn(len(dates)) * 0.001),
            'high': price * (1 + np.random.randn(len(dates)) * 0.002),
            'low': price * (1 - np.random.randn(len(dates)) * 0.002),
            'close': price,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        }, index=dates)
    
    return data

@pytest.fixture(scope="session")
def mock_signal_generator():
    """Mock signal generator for strategy testing"""
    class MockSignalGenerator:
        def __init__(self):
            self.signals = []
        
        def generate_signal(self, data):
            import numpy as np
            return np.random.choice(['LONG', 'SHORT', 'FLAT'])
        
        def update(self, data):
            pass
    
    return MockSignalGenerator()

@pytest.fixture(scope="function")
def mock_portfolio():
    """Mock portfolio for testing execution and risk management"""
    class MockPortfolio:
        def __init__(self):
            self.positions = {}
            self.cash = 1000000
        
        def add_position(self, symbol, quantity, price):
            self.positions[symbol] = {
                'quantity': quantity,
                'price': price
            }
        
        def get_position_value(self, symbol):
            if symbol not in self.positions:
                return 0
            return self.positions[symbol]['quantity'] * self.positions[symbol]['price']
    
    return MockPortfolio()

@pytest.fixture(scope="session")
def benchmark_metrics():
    """Performance benchmarking metrics"""
    return {
        'latency': [],
        'memory_usage': [],
        'cpu_usage': []
    }

def pytest_configure(config):
    """Custom pytest markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")

def pytest_collection_modifyitems(config, items):
    """Handle test markers and skip slow tests unless explicitly requested"""
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--integration", action="store_true", default=False, help="run integration tests"
    )
    parser.addoption(
        "--performance", action="store_true", default=False, help="run performance tests"
    ) 