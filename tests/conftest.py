"""
Pytest Configuration and Shared Fixtures
========================================

Centralized pytest configuration with shared fixtures for all tests.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
import numpy as np

# Import core system components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_structure.config import TradingConfig, ConfigManager
from core_structure.engines import TradingEngine, SignalProcessor, ExecutionProcessor
from core_structure.strategies import StrategyManager, MomentumStrategy, MeanReversionStrategy, PairsTradingStrategy
from core_structure.system import UnifiedTradingSystem
# Import from the new optimization.py file (not the legacy optimization/ directory)
import importlib.util
import os

# Load optimization.py directly
optimization_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core_structure', 'optimization.py')
if os.path.exists(optimization_file):
    spec = importlib.util.spec_from_file_location('optimization_module', optimization_file)
    optimization_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(optimization_module)
    OptimizationManager = optimization_module.OptimizationManager
    OptimizationLevel = optimization_module.OptimizationLevel
else:
    OptimizationManager = None
    OptimizationLevel = None

# ================================================================================
# PYTEST CONFIGURATION
# ================================================================================

def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests for full workflows")
    config.addinivalue_line("markers", "performance: Performance and load tests")
    config.addinivalue_line("markers", "slow: Tests that take longer than 5 seconds")
    config.addinivalue_line("markers", "requires_data: Tests that require market data")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ================================================================================
# CONFIGURATION FIXTURES
# ================================================================================

@pytest.fixture
def test_config():
    """Create a test trading configuration"""
    return TradingConfig(
        environment="testing",  # Use valid enum value
        trading_mode="backtest",
        log_level="DEBUG",
        clickhouse_host="localhost",
        clickhouse_port=9000,
        clickhouse_database="test_trading",
        initial_capital=100000.0,
        max_position_size=1000.0,  # Use valid value
        max_daily_loss=2000.0  # Use max_daily_loss instead of risk_limit
    )

@pytest.fixture
def config_manager():
    """Create a test configuration manager"""
    manager = ConfigManager()  # No file path for testing
    # Set the config directly for testing
    manager._config = TradingConfig(
        environment="testing",
        trading_mode="backtest",
        initial_capital=100000.0
    )
    return manager

# ================================================================================
# ENGINE FIXTURES
# ================================================================================

@pytest.fixture
def trading_engine(test_config):
    """Create a test trading engine"""
    return TradingEngine(test_config)

@pytest.fixture
def signal_processor(test_config):
    """Create a test signal processor"""
    return SignalProcessor(test_config)

@pytest.fixture
def execution_processor(test_config):
    """Create a test execution processor"""
    return ExecutionProcessor(test_config)

# ================================================================================
# STRATEGY FIXTURES
# ================================================================================

@pytest.fixture
def strategy_manager(test_config):
    """Create a test strategy manager"""
    return StrategyManager(test_config)

@pytest.fixture
def momentum_strategy():
    """Create a test momentum strategy"""
    config = {'lookback_period': 20, 'momentum_threshold': 0.02}
    return MomentumStrategy("test_momentum", config)

@pytest.fixture
def mean_reversion_strategy():
    """Create a test mean reversion strategy"""
    config = {'lookback_period': 20, 'z_score_threshold': 2.0}
    return MeanReversionStrategy("test_mean_reversion", config)

@pytest.fixture
def pairs_trading_strategy():
    """Create a test pairs trading strategy"""
    config = {'pairs': [('AAPL', 'MSFT')], 'lookback_period': 60}
    return PairsTradingStrategy("test_pairs", config)

# ================================================================================
# SYSTEM FIXTURES
# ================================================================================

@pytest.fixture
def unified_trading_system(test_config):
    """Create a test unified trading system"""
    return UnifiedTradingSystem(test_config)

@pytest.fixture
def optimization_manager():
    """Create a test optimization manager"""
    if OptimizationManager and OptimizationLevel:
        return OptimizationManager(OptimizationLevel.BASIC)
    else:
        # Return mock optimization manager
        class MockOptimizationManager:
            def optimize_system(self):
                return {'status': 'mock_optimization'}
        return MockOptimizationManager()

# ================================================================================
# DATA FIXTURES
# ================================================================================

@pytest.fixture
def sample_market_data():
    """Generate sample market data for testing"""
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='1min')
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    
    data = {}
    for symbol in symbols:
        # Generate realistic price data
        np.random.seed(42)  # For reproducible tests
        returns = np.random.normal(0, 0.02, len(dates))
        prices = 100 * np.exp(np.cumsum(returns))
        
        data[symbol] = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.002, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.002, len(dates)))),
            'close': prices,
            'volume': np.random.randint(1000, 10000, len(dates))
        })
    
    return data

@pytest.fixture
def sample_signals():
    """Generate sample trading signals for testing"""
    from core_structure.engines import TradingSignal, SignalType, SignalStrength
    
    signals = []
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    signal_types = [SignalType.LONG, SignalType.SHORT]
    strengths = [SignalStrength.WEAK, SignalStrength.MODERATE, SignalStrength.STRONG]
    
    for i in range(10):
        signal = TradingSignal(
            symbol=np.random.choice(symbols),
            signal_type=np.random.choice(signal_types),
            strength=np.random.choice(strengths),
            confidence=np.random.uniform(0.5, 0.95),
            timestamp=datetime.now() - timedelta(minutes=i),
            metadata={'test_signal': True, 'signal_id': i}
        )
        signals.append(signal)
    
    return signals

# ================================================================================
# TEMPORARY DIRECTORY FIXTURES
# ================================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_data_dir(temp_dir):
    """Create a test data directory with sample files"""
    data_dir = temp_dir / "test_data"
    data_dir.mkdir()
    
    # Create sample configuration file
    config_file = data_dir / "test_config.yml"
    config_content = """
environment: test
trading_mode: backtest
log_level: DEBUG
initial_capital: 100000.0
max_position_size: 0.1
risk_limit: 0.02
"""
    config_file.write_text(config_content)
    
    return data_dir

# ================================================================================
# MOCK FIXTURES
# ================================================================================

@pytest.fixture
def mock_market_data_provider():
    """Mock market data provider for testing"""
    class MockMarketDataProvider:
        def __init__(self):
            self.data = {}
            
        def get_data(self, symbol: str, start_date: datetime, end_date: datetime):
            # Return mock data
            dates = pd.date_range(start=start_date, end=end_date, freq='1min')
            prices = 100 + np.random.randn(len(dates)).cumsum() * 0.1
            
            return pd.DataFrame({
                'timestamp': dates,
                'open': prices,
                'high': prices * 1.01,
                'low': prices * 0.99,
                'close': prices,
                'volume': np.random.randint(1000, 5000, len(dates))
            })
    
    return MockMarketDataProvider()

@pytest.fixture
def mock_broker():
    """Mock broker for testing execution"""
    class MockBroker:
        def __init__(self):
            self.orders = []
            self.positions = {}
            
        def submit_order(self, symbol: str, quantity: float, order_type: str):
            order_id = f"order_{len(self.orders)}"
            order = {
                'id': order_id,
                'symbol': symbol,
                'quantity': quantity,
                'type': order_type,
                'status': 'filled',
                'fill_price': 100.0  # Mock fill price
            }
            self.orders.append(order)
            return order_id
            
        def get_position(self, symbol: str):
            return self.positions.get(symbol, 0)
    
    return MockBroker()

# ================================================================================
# PERFORMANCE FIXTURES
# ================================================================================

@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing"""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = datetime.now()
            
        def stop(self):
            self.end_time = datetime.now()
            
        @property
        def elapsed_seconds(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds()
            return None
    
    return PerformanceTimer()

# ================================================================================
# CLEANUP FIXTURES
# ================================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test"""
    yield
    # Cleanup code here if needed
    # For example, clear caches, reset singletons, etc.
    pass
