"""
Integration Test Fixtures

Comprehensive fixtures for integration testing including:
- System initialization helpers
- Component coordination fixtures
- Realistic market data generators
- Multi-component test environments

Author: StatArb_Gemini Test Infrastructure
Date: October 8, 2025
Version: 1.0.0
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import asyncio

# Import core components
from core_engine.risk.manager import CentralRiskManager
from core_engine.trading.strategy_manager import StrategyManager
from core_engine.trading.execution_engine import UnifiedExecutionEngine
from core_engine.system.orchestrator import HierarchicalSystemOrchestrator

# Import configuration
from core_engine.config.component_config import (
    RiskManagementConfig,
    StrategyConfig,
    ExecutionConfig,
    SystemOrchestrationConfig,
)

# Import type definitions
from core_engine.type_definitions.enums import (
    OrderStatus,
)


# ==============================================================================
# SYSTEM INITIALIZATION FIXTURES
# ==============================================================================

@pytest_asyncio.fixture
async def integrated_system():
    """
    Create fully integrated trading system with all components wired together.
    
    This is the main fixture for end-to-end integration testing.
    Returns all components properly initialized and connected.
    """
    # Initialize orchestrator
    orchestrator_config = SystemOrchestrationConfig(
        enable_hierarchical_control=True,
        emergency_override_enabled=True,
        health_check_interval=1.0,
        component_timeout=5.0,
    )
    orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)
    await orchestrator.initialize()
    
    # Initialize risk manager
    risk_config = RiskManagementConfig(
        max_position_size=10000.0,
        max_portfolio_exposure=50000.0,
        max_daily_loss=5000.0,
        max_drawdown=0.10,
        position_concentration_limit=0.30,
        enable_emergency_controls=True,
    )
    risk_manager = CentralRiskManager(risk_config)
    await risk_manager.initialize()
    
    # Initialize strategy manager
    strategy_config = StrategyConfig(
        enabled=True,
        max_strategies=10,
        strategy_timeout=5.0,
    )
    strategy_manager = StrategyManager(strategy_config)
    await strategy_manager.initialize()
    
    # Initialize execution engine
    execution_config = ExecutionConfig(
        max_order_size=10000.0,
        max_slippage=0.0020,  # 20 bps
        execution_timeout=30.0,
        enable_dark_pool_routing=True,
        dark_pool_threshold=0.30,
    )
    execution_engine = UnifiedExecutionEngine(execution_config)
    await execution_engine.initialize()
    
    # Register components with orchestrator
    await orchestrator.register_component(
        "risk_manager",
        risk_manager,
        layer="governance",
        authority_level="elevated"
    )
    await orchestrator.register_component(
        "strategy_manager",
        strategy_manager,
        layer="execution",
        authority_level="automatic"
    )
    await orchestrator.register_component(
        "execution_engine",
        execution_engine,
        layer="execution",
        authority_level="automatic"
    )
    
    # Return all components
    system = {
        'orchestrator': orchestrator,
        'risk_manager': risk_manager,
        'strategy_manager': strategy_manager,
        'execution_engine': execution_engine,
    }
    
    yield system
    
    # Cleanup
    await orchestrator.shutdown()
    await risk_manager.shutdown()
    await strategy_manager.shutdown()
    await execution_engine.shutdown()


@pytest_asyncio.fixture
async def risk_controlled_execution():
    """
    Create risk manager + execution engine integration.
    Tests risk authorization controlling execution flow.
    """
    # Risk manager
    risk_config = RiskManagementConfig(
        max_position_size=10000.0,
        max_portfolio_exposure=50000.0,
        enable_emergency_controls=True,
    )
    risk_manager = CentralRiskManager(risk_config)
    await risk_manager.initialize()
    
    # Execution engine
    execution_config = ExecutionConfig(
        max_order_size=10000.0,
        execution_timeout=30.0,
    )
    execution_engine = UnifiedExecutionEngine(execution_config)
    await execution_engine.initialize()
    
    # Wire together: execution engine should respect risk authorizations
    components = {
        'risk_manager': risk_manager,
        'execution_engine': execution_engine,
    }
    
    yield components
    
    await risk_manager.shutdown()
    await execution_engine.shutdown()


@pytest_asyncio.fixture
async def strategy_risk_pipeline():
    """
    Create strategy manager + risk manager integration.
    Tests signal generation → risk authorization flow.
    """
    # Strategy manager
    strategy_config = StrategyConfig(
        enabled=True,
        max_strategies=5,
    )
    strategy_manager = StrategyManager(strategy_config)
    await strategy_manager.initialize()
    
    # Risk manager
    risk_config = RiskManagementConfig(
        max_position_size=10000.0,
        max_portfolio_exposure=50000.0,
    )
    risk_manager = CentralRiskManager(risk_config)
    await risk_manager.initialize()
    
    components = {
        'strategy_manager': strategy_manager,
        'risk_manager': risk_manager,
    }
    
    yield components
    
    await strategy_manager.shutdown()
    await risk_manager.shutdown()


# ==============================================================================
# MARKET DATA GENERATORS
# ==============================================================================

@pytest.fixture
def market_data_generator():
    """
    Generate realistic market data for integration testing.
    
    Returns a callable that produces market data with specified characteristics.
    """
    def generate(
        symbols: List[str] = None,
        num_updates: int = 100,
        volatility: float = 0.01,
        trend: float = 0.0,
        start_price: float = 100.0,
    ) -> List[Dict[str, Any]]:
        """
        Generate synthetic market data.
        
        Args:
            symbols: List of ticker symbols
            num_updates: Number of price updates to generate
            volatility: Price volatility (std dev)
            trend: Drift/trend in price
            start_price: Starting price
            
        Returns:
            List of market data updates
        """
        if symbols is None:
            symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        import numpy as np
        updates = []
        
        for symbol in symbols:
            price = start_price
            timestamp = datetime.now()
            
            for i in range(num_updates):
                # Random walk with drift
                change = np.random.normal(trend, volatility)
                price = price * (1 + change)
                
                update = {
                    'symbol': symbol,
                    'price': round(price, 2),
                    'volume': int(np.random.uniform(1000, 10000)),
                    'timestamp': timestamp + timedelta(seconds=i),
                    'bid': round(price * 0.9995, 2),
                    'ask': round(price * 1.0005, 2),
                    'bid_size': int(np.random.uniform(100, 1000)),
                    'ask_size': int(np.random.uniform(100, 1000)),
                }
                updates.append(update)
        
        return updates
    
    return generate


@pytest.fixture
def market_crash_generator():
    """
    Generate flash crash market data for emergency testing.
    """
    def generate(
        symbols: List[str] = None,
        crash_magnitude: float = 0.10,  # 10% drop
        recovery_time: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Generate flash crash scenario.
        
        Args:
            symbols: List of ticker symbols
            crash_magnitude: Size of price drop (0-1)
            recovery_time: Updates until recovery
            
        Returns:
            List of market data with crash pattern
        """
        if symbols is None:
            symbols = ['AAPL', 'MSFT']
        
        updates = []
        start_price = 100.0
        timestamp = datetime.now()
        
        for symbol in symbols:
            price = start_price
            
            # Pre-crash normal trading
            for i in range(20):
                update = {
                    'symbol': symbol,
                    'price': round(price, 2),
                    'volume': 5000,
                    'timestamp': timestamp + timedelta(seconds=i),
                }
                updates.append(update)
            
            # Crash: rapid price decline
            for i in range(20, 30):
                crash_progress = (i - 20) / 10
                price = start_price * (1 - crash_magnitude * crash_progress)
                update = {
                    'symbol': symbol,
                    'price': round(price, 2),
                    'volume': 50000,  # High volume
                    'timestamp': timestamp + timedelta(seconds=i),
                }
                updates.append(update)
            
            # Recovery
            crash_price = start_price * (1 - crash_magnitude)
            for i in range(30, 30 + recovery_time):
                recovery_progress = (i - 30) / recovery_time
                price = crash_price + (start_price - crash_price) * recovery_progress
                update = {
                    'symbol': symbol,
                    'price': round(price, 2),
                    'volume': 10000,
                    'timestamp': timestamp + timedelta(seconds=i),
                }
                updates.append(update)
        
        return updates
    
    return generate


@pytest.fixture
def high_frequency_data_generator():
    """
    Generate high-frequency market data for stress testing.
    """
    def generate(
        symbols: List[str] = None,
        updates_per_second: int = 100,
        duration_seconds: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Generate high-frequency tick data.
        
        Args:
            symbols: List of ticker symbols
            updates_per_second: Tick rate
            duration_seconds: Test duration
            
        Returns:
            List of rapid market updates
        """
        if symbols is None:
            symbols = ['AAPL']
        
        import numpy as np
        updates = []
        total_updates = updates_per_second * duration_seconds
        
        for symbol in symbols:
            price = 100.0
            base_time = datetime.now()
            
            for i in range(total_updates):
                # Micro price changes
                price += np.random.uniform(-0.01, 0.01)
                timestamp = base_time + timedelta(microseconds=i * (1000000 // updates_per_second))
                
                update = {
                    'symbol': symbol,
                    'price': round(price, 2),
                    'volume': 100,
                    'timestamp': timestamp,
                }
                updates.append(update)
        
        return updates
    
    return generate


# ==============================================================================
# SIGNAL GENERATORS
# ==============================================================================

@pytest.fixture
def trading_signal_generator():
    """
    Generate trading signals for integration testing.
    """
    def generate(
        signal_type: str = 'buy',
        confidence: float = 0.85,
        position_size: float = 1000.0,
        symbol: str = 'AAPL',
    ) -> Dict[str, Any]:
        """
        Generate trading signal.
        
        Args:
            signal_type: 'buy' or 'sell'
            confidence: Signal confidence (0-1)
            position_size: Suggested position size
            symbol: Ticker symbol
            
        Returns:
            Trading signal dictionary
        """
        return {
            'symbol': symbol,
            'signal_type': signal_type,
            'confidence': confidence,
            'position_size': position_size,
            'timestamp': datetime.now(),
            'strategy_id': 'momentum_01',
            'rationale': f"Strong {signal_type} signal based on momentum analysis",
        }
    
    return generate


# ==============================================================================
# MOCK BROKER FIXTURE
# ==============================================================================

@pytest_asyncio.fixture
async def mock_broker():
    """
    Create mock broker for integration testing.
    Simulates order execution without real broker connection.
    """
    class MockBroker:
        def __init__(self):
            self.orders = []
            self.fills = []
            self.connection_status = 'connected'
            
        async def submit_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate order submission."""
            self.orders.append(order)
            
            # Simulate fill
            fill = {
                'order_id': order.get('order_id'),
                'symbol': order.get('symbol'),
                'quantity': order.get('quantity'),
                'price': order.get('limit_price', 100.0),
                'status': OrderStatus.FILLED,
                'timestamp': datetime.now(),
            }
            self.fills.append(fill)
            
            return fill
        
        async def cancel_order(self, order_id: str) -> bool:
            """Simulate order cancellation."""
            for order in self.orders:
                if order.get('order_id') == order_id:
                    order['status'] = OrderStatus.CANCELLED
                    return True
            return False
        
        async def get_positions(self) -> List[Dict[str, Any]]:
            """Get current positions."""
            return []
        
        def disconnect(self):
            """Simulate broker disconnection."""
            self.connection_status = 'disconnected'
        
        def reconnect(self):
            """Simulate broker reconnection."""
            self.connection_status = 'connected'
    
    broker = MockBroker()
    yield broker


# ==============================================================================
# PERFORMANCE MONITORING FIXTURE
# ==============================================================================

@pytest.fixture
def performance_monitor():
    """
    Monitor performance metrics during integration tests.
    """
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {}
            self.start_times = {}
        
        def start(self, operation: str):
            """Start timing an operation."""
            self.start_times[operation] = time.time()
        
        def end(self, operation: str):
            """End timing and record duration."""
            if operation in self.start_times:
                duration = time.time() - self.start_times[operation]
                if operation not in self.metrics:
                    self.metrics[operation] = []
                self.metrics[operation].append(duration)
                del self.start_times[operation]
                return duration
            return None
        
        def get_average(self, operation: str) -> float:
            """Get average duration for operation."""
            if operation in self.metrics and self.metrics[operation]:
                return sum(self.metrics[operation]) / len(self.metrics[operation])
            return 0.0
        
        def get_max(self, operation: str) -> float:
            """Get max duration for operation."""
            if operation in self.metrics and self.metrics[operation]:
                return max(self.metrics[operation])
            return 0.0
        
        def reset(self):
            """Reset all metrics."""
            self.metrics = {}
            self.start_times = {}
    
    return PerformanceMonitor()


# ==============================================================================
# HELPER FIXTURES
# ==============================================================================

@pytest.fixture
def wait_for_condition():
    """
    Helper to wait for async conditions with timeout.
    """
    async def wait(
        condition_fn,
        timeout: float = 5.0,
        interval: float = 0.1,
        error_msg: str = "Condition not met"
    ):
        """
        Wait for condition to become true.
        
        Args:
            condition_fn: Callable that returns bool
            timeout: Maximum wait time
            interval: Check interval
            error_msg: Error message if timeout
        """
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            if condition_fn():
                return True
            await asyncio.sleep(interval)
        raise TimeoutError(error_msg)
    
    return wait
