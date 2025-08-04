"""
Shared test fixtures for integration tests.

This module provides common fixtures and utilities used across all integration tests.
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
import tempfile
import os
import json

# Import core system components (using mock versions for now)
# These will be replaced with actual bridge components when they're implemented
class SignalBridge:
    def __init__(self, config):
        self.config = config
        self.mode = config.get('mode', 'backtesting')
    
    def clear_cache(self):
        pass

class SignalBridgeConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class ExecutionBridge:
    def __init__(self, config):
        self.config = config
        self.mode = config.get('mode', 'backtesting')
    
    def clear_cache(self):
        pass

class ExecutionBridgeConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class RiskBridge:
    def __init__(self, config):
        self.config = config
        self.mode = config.get('mode', 'backtesting')
    
    def clear_cache(self):
        pass

class RiskBridgeConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class DataBridge:
    def __init__(self, config):
        self.config = config
        self.mode = config.get('mode', 'backtesting')
    
    def clear_cache(self):
        pass

class DataBridgeConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class PortfolioBridge:
    def __init__(self, config):
        self.config = config
        self.mode = config.get('mode', 'backtesting')
    
    def clear_cache(self):
        pass

class PortfolioBridgeConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class ConfigBridge:
    def __init__(self, config):
        self.config = config
        self.mode = config.get('mode', 'backtesting')
    
    def clear_cache(self):
        pass

class ConfigBridgeConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class AnalyticsBridge:
    def __init__(self, config):
        self.config = config
        self.mode = config.get('mode', 'backtesting')
    
    def clear_cache(self):
        pass

class AnalyticsBridgeConfig:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestConfig:
    """Configuration for integration tests."""
    test_symbols: List[str] = None
    test_duration: timedelta = None
    test_scenarios: List[str] = None
    performance_targets: Dict[str, float] = None
    
    def __post_init__(self):
        if self.test_symbols is None:
            self.test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
        if self.test_duration is None:
            self.test_duration = timedelta(hours=1)
        if self.test_scenarios is None:
            self.test_scenarios = ['normal', 'high_volatility', 'trending', 'crisis']
        if self.performance_targets is None:
            self.performance_targets = {
                'signal_latency_ms': 100,
                'execution_latency_ms': 500,
                'data_latency_ms': 50,
                'throughput_signals_per_min': 1000,
                'memory_usage_mb': 2048,
                'cpu_usage_percent': 80
            }


@dataclass
class TestResult:
    """Result of a test execution."""
    test_name: str
    success: bool
    duration: float
    metrics: Dict[str, Any]
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class MockDataGenerator:
    """Generates realistic test data for integration tests."""
    
    def __init__(self):
        self.market_scenarios = self._load_market_scenarios()
    
    def _load_market_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined market scenarios."""
        return {
            'normal': {
                'volatility': 0.15,
                'trend': 0.0,
                'correlation': 0.3,
                'volume_multiplier': 1.0
            },
            'high_volatility': {
                'volatility': 0.35,
                'trend': 0.0,
                'correlation': 0.5,
                'volume_multiplier': 1.5
            },
            'trending': {
                'volatility': 0.20,
                'trend': 0.1,
                'correlation': 0.4,
                'volume_multiplier': 1.2
            },
            'crisis': {
                'volatility': 0.50,
                'trend': -0.2,
                'correlation': 0.8,
                'volume_multiplier': 2.0
            }
        }
    
    def generate_market_data(self, symbols: List[str], scenario: str = 'normal', 
                           duration: timedelta = timedelta(hours=1)) -> Dict[str, pd.DataFrame]:
        """Generate realistic market data for testing."""
        scenario_config = self.market_scenarios[scenario]
        
        data = {}
        base_price = 100.0
        
        for symbol in symbols:
            # Generate price data
            n_periods = int(duration.total_seconds() / 60)  # 1-minute intervals
            returns = np.random.normal(
                scenario_config['trend'] / 252,  # Daily trend
                scenario_config['volatility'] / np.sqrt(252),  # Daily volatility
                n_periods
            )
            
            prices = [base_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # Generate volume data
            volumes = np.random.lognormal(
                mean=10,
                sigma=0.5,
                size=n_periods
            ) * scenario_config['volume_multiplier']
            
            # Create DataFrame
            timestamps = pd.date_range(
                start=datetime.now() - duration,
                end=datetime.now(),
                periods=n_periods
            )
            
            df = pd.DataFrame({
                'timestamp': timestamps,
                'open': prices,
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': volumes
            })
            
            data[symbol] = df
        
        return data
    
    def generate_trading_signals(self, symbols: List[str], count: int = 10) -> List[Dict[str, Any]]:
        """Generate realistic trading signals for testing."""
        signals = []
        
        for i in range(count):
            signal = {
                'signal_id': f'signal_{i:04d}',
                'symbol': np.random.choice(symbols),
                'timestamp': datetime.now() - timedelta(minutes=np.random.randint(1, 60)),
                'signal_type': np.random.choice(['BUY', 'SELL']),
                'confidence': np.random.uniform(0.5, 1.0),
                'strength': np.random.uniform(0.1, 0.5),
                'source': 'test_signal_generator',
                'metadata': {
                    'test_signal': True,
                    'batch_id': f'batch_{i//5:03d}'
                }
            }
            signals.append(signal)
        
        return signals
    
    def generate_orders(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate orders based on signals."""
        orders = []
        
        for signal in signals:
            order = {
                'order_id': f'order_{signal["signal_id"]}',
                'symbol': signal['symbol'],
                'side': signal['signal_type'],
                'quantity': int(np.random.uniform(100, 1000)),
                'order_type': 'MARKET',
                'timestamp': signal['timestamp'],
                'signal_id': signal['signal_id'],
                'metadata': {
                    'test_order': True,
                    'signal_confidence': signal['confidence']
                }
            }
            orders.append(order)
        
        return orders


class MockServices:
    """Mock external services for integration testing."""
    
    def __init__(self):
        self.data_generator = MockDataGenerator()
        self.orders = {}
        self.executions = {}
        self.positions = {}
    
    async def get_market_data(self, symbols: List[str], scenario: str = 'normal') -> Dict[str, pd.DataFrame]:
        """Mock market data service."""
        await asyncio.sleep(0.001)  # Simulate async delay
        return self.data_generator.generate_market_data(symbols, scenario)
    
    async def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Mock order placement service."""
        await asyncio.sleep(0.001)  # Simulate async delay
        
        execution = {
            'execution_id': f'exec_{order["order_id"]}',
            'order_id': order['order_id'],
            'symbol': order['symbol'],
            'side': order['side'],
            'quantity': order['quantity'],
            'price': 100.0 + np.random.normal(0, 1),  # Mock execution price
            'timestamp': datetime.now(),
            'status': 'FILLED',
            'fill_rate': np.random.uniform(0.95, 1.0),
            'implementation_shortfall': np.random.uniform(0, 0.001)
        }
        
        self.executions[order['order_id']] = execution
        return execution
    
    async def get_portfolio_positions(self) -> Dict[str, Any]:
        """Mock portfolio service."""
        await asyncio.sleep(0.001)  # Simulate async delay
        
        return {
            'timestamp': datetime.now(),
            'total_value': 1000000.0,
            'cash': 500000.0,
            'positions': {
                'AAPL': {'quantity': 1000, 'avg_price': 150.0, 'current_value': 150000.0},
                'GOOGL': {'quantity': 500, 'avg_price': 2800.0, 'current_value': 1400000.0}
            },
            'pnl': 50000.0,
            'metadata': {'test_portfolio': True}
        }


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    """Provide test configuration."""
    return TestConfig()


@pytest.fixture(scope="session")
def mock_services() -> MockServices:
    """Provide mock services for testing."""
    return MockServices()


@pytest.fixture(scope="session")
def data_generator() -> MockDataGenerator:
    """Provide data generator for testing."""
    return MockDataGenerator()


@pytest.fixture(scope="session")
def temp_test_dir():
    """Provide temporary directory for test artifacts."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="function")
async def signal_bridge(test_config) -> SignalBridge:
    """Provide SignalBridge instance for testing."""
    config = SignalBridgeConfig(
        mode="backtesting",
        cache_enabled=True,
        cache_ttl=300,
        performance_tracking=True
    )
    bridge = SignalBridge(config)
    yield bridge
    # Cleanup
    if hasattr(bridge, 'clear_cache'):
        bridge.clear_cache()


@pytest.fixture(scope="function")
async def execution_bridge(test_config) -> ExecutionBridge:
    """Provide ExecutionBridge instance for testing."""
    config = ExecutionBridgeConfig(
        mode="backtesting",
        cache_enabled=True,
        cache_ttl=300,
        performance_tracking=True
    )
    bridge = ExecutionBridge(config)
    yield bridge
    # Cleanup
    if hasattr(bridge, 'clear_cache'):
        bridge.clear_cache()


@pytest.fixture(scope="function")
async def risk_bridge(test_config) -> RiskBridge:
    """Provide RiskBridge instance for testing."""
    config = RiskBridgeConfig(
        mode="backtesting",
        cache_enabled=True,
        cache_ttl=300,
        performance_tracking=True
    )
    bridge = RiskBridge(config)
    yield bridge
    # Cleanup
    if hasattr(bridge, 'clear_cache'):
        bridge.clear_cache()


@pytest.fixture(scope="function")
async def data_bridge(test_config) -> DataBridge:
    """Provide DataBridge instance for testing."""
    config = DataBridgeConfig(
        mode="backtesting",
        cache_enabled=True,
        cache_ttl=300,
        performance_tracking=True
    )
    bridge = DataBridge(config)
    yield bridge
    # Cleanup
    if hasattr(bridge, 'clear_cache'):
        bridge.clear_cache()


@pytest.fixture(scope="function")
async def portfolio_bridge(test_config) -> PortfolioBridge:
    """Provide PortfolioBridge instance for testing."""
    config = PortfolioBridgeConfig(
        mode="backtesting",
        cache_enabled=True,
        cache_ttl=300,
        performance_tracking=True
    )
    bridge = PortfolioBridge(config)
    yield bridge
    # Cleanup
    if hasattr(bridge, 'clear_cache'):
        bridge.clear_cache()


@pytest.fixture(scope="function")
async def config_bridge(test_config) -> ConfigBridge:
    """Provide ConfigBridge instance for testing."""
    config = ConfigBridgeConfig(
        mode="backtesting",
        cache_enabled=True,
        cache_ttl=300,
        performance_tracking=True
    )
    bridge = ConfigBridge(config)
    yield bridge
    # Cleanup
    if hasattr(bridge, 'clear_cache'):
        bridge.clear_cache()


@pytest.fixture(scope="function")
async def analytics_bridge(test_config) -> AnalyticsBridge:
    """Provide AnalyticsBridge instance for testing."""
    config = AnalyticsBridgeConfig(
        mode="backtesting",
        cache_enabled=True,
        cache_ttl=300,
        performance_tracking=True
    )
    bridge = AnalyticsBridge(config)
    yield bridge
    # Cleanup
    if hasattr(bridge, 'clear_cache'):
        bridge.clear_cache()


@pytest.fixture(scope="function")
def test_data(data_generator, test_config) -> Dict[str, Any]:
    """Provide test data for integration tests."""
    return {
        'market_data': data_generator.generate_market_data(
            test_config.test_symbols, 
            'normal', 
            test_config.test_duration
        ),
        'signals': data_generator.generate_trading_signals(
            test_config.test_symbols, 
            count=20
        ),
        'orders': data_generator.generate_orders(
            data_generator.generate_trading_signals(test_config.test_symbols, count=10)
        )
    }


def assert_performance_targets(metrics: Dict[str, float], targets: Dict[str, float], 
                             test_name: str = "Test"):
    """Assert that performance metrics meet targets."""
    failures = []
    
    for metric, target in targets.items():
        if metric in metrics:
            actual = metrics[metric]
            if actual > target:
                failures.append(f"{metric}: {actual} > {target}")
    
    if failures:
        pytest.fail(f"{test_name} performance targets not met: {', '.join(failures)}")


def log_test_metrics(test_name: str, metrics: Dict[str, Any], duration: float):
    """Log test metrics for analysis."""
    logger.info(f"Test: {test_name}")
    logger.info(f"Duration: {duration:.3f}s")
    logger.info(f"Metrics: {json.dumps(metrics, indent=2, default=str)}")
    logger.info("-" * 50) 