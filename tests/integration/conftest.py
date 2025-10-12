"""
Integration Test Fixtures
==========================

Shared fixtures for integration testing providing:
- Real component instances (not mocked)
- Async event loop management
- Integrated system setup
- Sample data generators
- Test utilities

Author: StatArb_Gemini Integration Testing
Phase: 8 - Integration Testing
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ========================================
# Event Loop Fixtures
# ========================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for entire test session
    
    Scope: session - one loop for all tests
    This prevents event loop conflicts in async tests
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def event_loop_for_test():
    """
    Create fresh event loop for a single test
    
    Use when test needs isolated event loop
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ========================================
# Core Component Fixtures
# ========================================

@pytest.fixture
async def risk_manager():
    """
    Real CentralRiskManager instance (standalone)
    
    Provides:
    - Risk authorization
    - Limit enforcement
    - Trading governance
    
    NOTE: This is a standalone instance. If you need an orchestrator
    with registered risk manager, use the 'orchestrator' fixture which
    creates both and registers them properly.
    """
    from core_engine.system.central_risk_manager import CentralRiskManager
    
    config = {
        'max_position_size': 0.1,
        'max_daily_var': 0.05,
        'max_total_risk': 0.20
    }
    
    rm = CentralRiskManager(config)
    await rm.initialize()
    
    yield rm
    
    # Cleanup
    try:
        await rm.stop()
    except Exception as e:
        logging.warning(f"Risk manager cleanup error: {e}")


@pytest.fixture
async def orchestrator(risk_manager):
    """
    Real HierarchicalOrchestrator instance with registered CentralRiskManager
    
    Provides:
    - Component registration
    - Lifecycle management
    - Authority framework
    - Properly integrated risk manager
    
    IMPORTANT: This fixture depends on risk_manager fixture to ensure
    proper registration before initialization.
    """
    from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
    
    orch = HierarchicalSystemOrchestrator()
    
    # CRITICAL: Register the risk manager BEFORE initializing
    orch.register_central_risk_manager(risk_manager)
    logging.info("✅ CentralRiskManager registered with orchestrator")
    
    # Now initialize with registered risk manager
    await orch.initialize()
    
    yield orch
    
    # Cleanup
    try:
        await orch.stop()
    except Exception as e:
        logging.warning(f"Orchestrator cleanup error: {e}")


@pytest.fixture
async def data_manager():
    """
    Mock DataManager instance for testing
    
    Provides:
    - Data storage methods
    - Data retrieval methods
    - Simple in-memory storage
    """
    
    class MockDataManager:
        def __init__(self):
            self.data_store = {}
            self.is_initialized = False
            self.is_operational = False
            
        async def initialize(self):
            self.is_initialized = True
            return True
            
        async def start(self):
            self.is_operational = True
            return True
            
        async def stop(self):
            self.is_operational = False
            return True
            
        async def store_market_data(self, symbol: str, data: pd.DataFrame):
            """Store market data in memory"""
            self.data_store[symbol] = data
            return True
            
        async def get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
            """Retrieve stored market data"""
            return self.data_store.get(symbol)
            
        def get_status(self) -> Dict[str, Any]:
            return {
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'symbols_stored': len(self.data_store)
            }
    
    dm = MockDataManager()
    await dm.initialize()
    
    yield dm
    
    # Cleanup
    try:
        await dm.stop()
    except Exception as e:
        logging.warning(f"Data manager cleanup error: {e}")


@pytest.fixture
async def regime_engine():
    """
    Real EnhancedRegimeEngine instance
    
    Provides:
    - Market regime detection
    - Regime change alerts
    - Strategy suitability
    """
    from core_engine.regime.engine import EnhancedRegimeEngine
    
    config = {
        'lookback_window': 60,
        'volatility_window': 20,
        'trend_threshold': 0.02,
        'update_frequency': 300  # seconds (5 minutes)
    }
    
    re = EnhancedRegimeEngine(config)
    await re.initialize()
    
    yield re
    
    # Cleanup
    try:
        await re.stop()
    except Exception as e:
        logging.warning(f"Regime engine cleanup error: {e}")


@pytest.fixture
async def indicator_engine():
    """
    Real EnhancedTechnicalIndicators instance
    
    Provides:
    - Technical indicator calculations
    - Multi-timeframe analysis
    - Vectorized operations
    """
    from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
    
    config = {
        'enable_caching': True,
        'cache_size': 1000,
        'supported_indicators': ['sma', 'ema', 'rsi', 'macd', 'bbands']
    }
    
    ie = EnhancedTechnicalIndicators(config)
    await ie.initialize()
    
    yield ie
    
    # Cleanup
    try:
        await ie.stop()
    except Exception as e:
        logging.warning(f"Indicator engine cleanup error: {e}")


@pytest.fixture
async def strategy_manager():
    """
    Real StrategyManager instance
    
    Provides:
    - Strategy registration
    - Signal generation
    - Multi-strategy coordination
    """
    from core_engine.trading.strategies.manager import StrategyManager
    
    config = {
        'max_concurrent_strategies': 3,
        'enable_enhanced_strategies': False,
        'auto_discover_strategies': False
    }
    
    sm = StrategyManager(config)
    await sm.initialize()
    
    yield sm
    
    # Cleanup
    try:
        await sm.stop()
    except Exception as e:
        logging.warning(f"Strategy manager cleanup error: {e}")


@pytest.fixture
async def execution_engine():
    """
    Real UnifiedExecutionEngine instance
    
    Provides:
    - Order execution
    - Fill monitoring
    - Execution algorithms
    """
    from core_engine.system.unified_execution_engine import UnifiedExecutionEngine
    
    config = {
        'default_algorithm': 'market',
        'enable_smart_routing': True,
        'max_order_size': 10000,
        'mock_broker': True  # Use mock broker for testing
    }
    
    ee = UnifiedExecutionEngine(config)
    await ee.initialize()
    
    yield ee
    
    # Cleanup
    try:
        await ee.stop()
    except Exception as e:
        logging.warning(f"Execution engine cleanup error: {e}")


# ========================================
# Integrated System Fixtures
# ========================================

@pytest.fixture
async def basic_integrated_system(orchestrator, risk_manager):
    """
    Basic integrated system with orchestrator + risk manager
    
    Use for: Testing core authorization workflows
    """
    # Register risk manager with orchestrator
    orchestrator.register_central_risk_manager(risk_manager)
    
    await orchestrator.initialize_system()
    
    yield {
        'orchestrator': orchestrator,
        'risk_manager': risk_manager
    }
    
    # Cleanup handled by individual fixtures


@pytest.fixture
async def data_processing_system(orchestrator, risk_manager, data_manager, 
                                  regime_engine, indicator_engine):
    """
    System with data processing components
    
    Use for: Testing data pipeline integration
    """
    from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel
    
    # Register components
    orchestrator.register_central_risk_manager(risk_manager)
    
    orchestrator.register_component(
        name="DataManager",
        component=data_manager,
        layer=ComponentLayer.SUPPORT,
        authority_level=AuthorityLevel.OPERATIONAL
    )
    
    orchestrator.register_component(
        name="RegimeEngine",
        component=regime_engine,
        layer=ComponentLayer.SUPPORT,
        authority_level=AuthorityLevel.STRATEGIC
    )
    
    orchestrator.register_component(
        name="IndicatorEngine",
        component=indicator_engine,
        layer=ComponentLayer.SUPPORT,
        authority_level=AuthorityLevel.OPERATIONAL
    )
    
    await orchestrator.initialize_system()
    
    yield {
        'orchestrator': orchestrator,
        'risk_manager': risk_manager,
        'data_manager': data_manager,
        'regime_engine': regime_engine,
        'indicator_engine': indicator_engine
    }


@pytest.fixture
async def full_trading_system(orchestrator, risk_manager, data_manager, 
                               regime_engine, indicator_engine, 
                               strategy_manager, execution_engine):
    """
    Complete trading system with all components
    
    Use for: End-to-end workflow testing
    """
    from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel
    
    # Register risk manager (Layer 2 - Governance)
    orchestrator.register_central_risk_manager(risk_manager)
    
    # Register data layer (Layer 3)
    orchestrator.register_component(
        name="DataManager",
        component=data_manager,
        layer=ComponentLayer.SUPPORT,
        authority_level=AuthorityLevel.OPERATIONAL
    )
    
    # Register processing layer (Layer 4)
    orchestrator.register_component(
        name="RegimeEngine",
        component=regime_engine,
        layer=ComponentLayer.SUPPORT,
        authority_level=AuthorityLevel.STRATEGIC
    )
    
    orchestrator.register_component(
        name="IndicatorEngine",
        component=indicator_engine,
        layer=ComponentLayer.SUPPORT,
        authority_level=AuthorityLevel.OPERATIONAL
    )
    
    # Register strategy layer (Layer 5)
    orchestrator.register_component(
        name="StrategyManager",
        component=strategy_manager,
        layer=ComponentLayer.EXECUTION,
        authority_level=AuthorityLevel.STRATEGIC
    )
    
    # Register execution layer (Layer 7)
    orchestrator.register_component(
        name="ExecutionEngine",
        component=execution_engine,
        layer=ComponentLayer.EXECUTION,
        authority_level=AuthorityLevel.TACTICAL
    )
    
    # Set component dependencies
    risk_manager.set_controlled_components(
        strategy_manager=strategy_manager,
        regime_engine=regime_engine
    )
    
    strategy_manager.risk_manager = risk_manager
    strategy_manager.data_manager = data_manager
    
    execution_engine.risk_manager = risk_manager
    
    # Initialize system
    await orchestrator.initialize_system()
    
    yield {
        'orchestrator': orchestrator,
        'risk_manager': risk_manager,
        'data_manager': data_manager,
        'regime_engine': regime_engine,
        'indicator_engine': indicator_engine,
        'strategy_manager': strategy_manager,
        'execution_engine': execution_engine
    }
    
    # Shutdown handled by orchestrator
    try:
        await orchestrator.shutdown_system()
    except Exception as e:
        logging.warning(f"System shutdown error: {e}")


# ========================================
# Data Fixtures
# ========================================

@pytest.fixture
def sample_market_data():
    """
    Generate sample OHLCV market data
    
    Returns: DataFrame with 100 rows of realistic market data
    """
    dates = pd.date_range('2024-01-01 09:30', periods=100, freq='1min')
    
    # Generate realistic price movements
    base_price = 150.0
    returns = np.random.randn(100) * 0.001  # 0.1% volatility
    prices = base_price * (1 + returns).cumprod()
    
    return pd.DataFrame({
        'timestamp': dates,
        'symbol': 'AAPL',
        'open': prices + np.random.randn(100) * 0.1,
        'high': prices + np.abs(np.random.randn(100)) * 0.2,
        'low': prices - np.abs(np.random.randn(100)) * 0.2,
        'close': prices,
        'volume': np.random.randint(900000, 1100000, 100)
    })


@pytest.fixture
def multi_symbol_market_data():
    """
    Generate market data for multiple symbols
    
    Returns: Dict[symbol -> DataFrame]
    """
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    data = {}
    
    dates = pd.date_range('2024-01-01 09:30', periods=100, freq='1min')
    
    for symbol in symbols:
        base_price = np.random.uniform(100, 300)
        returns = np.random.randn(100) * 0.001
        prices = base_price * (1 + returns).cumprod()
        
        data[symbol] = pd.DataFrame({
            'timestamp': dates,
            'symbol': symbol,
            'open': prices + np.random.randn(100) * 0.1,
            'high': prices + np.abs(np.random.randn(100)) * 0.2,
            'low': prices - np.abs(np.random.randn(100)) * 0.2,
            'close': prices,
            'volume': np.random.randint(900000, 1100000, 100)
        })
    
    return data


@pytest.fixture
def sample_trading_signal():
    """
    Generate sample trading signal
    
    Returns: Dict with signal details
    """
    return {
        'symbol': 'AAPL',
        'action': 'BUY',
        'size': 100,
        'strategy_id': 'momentum_strategy',
        'confidence': 0.75,
        'timestamp': datetime.now(),
        'metadata': {
            'indicator': 'SMA_crossover',
            'timeframe': '5min'
        }
    }


@pytest.fixture
def sample_trading_decision_request():
    """
    Generate sample TradingDecisionRequest
    
    Returns: TradingDecisionRequest object
    """
    from core_engine.system.central_risk_manager import TradingDecisionRequest
    
    return TradingDecisionRequest(
        requesting_component='test_strategy',
        proposed_action='BUY',
        symbol='AAPL',
        size=100,
        price=150.0,
        justification='Momentum signal triggered',
        risk_assessment={
            'estimated_var': 0.02,
            'position_concentration': 0.05
        }
    )


# ========================================
# Utility Fixtures
# ========================================

@pytest.fixture
def test_timeout():
    """
    Standard timeout for integration tests
    
    Returns: Timeout in seconds
    """
    return 10.0  # 10 seconds for most integration tests


@pytest.fixture
def long_test_timeout():
    """
    Extended timeout for complex tests
    
    Returns: Timeout in seconds
    """
    return 30.0  # 30 seconds for complex workflows


@pytest.fixture
async def async_test_helper():
    """
    Helper utilities for async testing
    
    Provides:
    - Wait for condition
    - Timeout wrapper
    - Task management
    """
    class AsyncTestHelper:
        @staticmethod
        async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
            """Wait for condition to become True"""
            elapsed = 0.0
            while elapsed < timeout:
                if await condition_func():
                    return True
                await asyncio.sleep(interval)
                elapsed += interval
            return False
        
        @staticmethod
        async def run_with_timeout(coro, timeout=5.0):
            """Run coroutine with timeout"""
            try:
                return await asyncio.wait_for(coro, timeout=timeout)
            except asyncio.TimeoutError:
                logging.warning(f"Coroutine timed out after {timeout}s")
                raise
        
        @staticmethod
        def get_pending_tasks():
            """Get all pending tasks"""
            return [task for task in asyncio.all_tasks() 
                   if not task.done()]
        
        @staticmethod
        async def cancel_all_tasks():
            """Cancel all pending tasks"""
            tasks = AsyncTestHelper.get_pending_tasks()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    
    return AsyncTestHelper()


@pytest.fixture
def component_status_checker():
    """
    Utility to check component status
    
    Provides:
    - Check initialization status
    - Check operational status
    - Wait for status change
    """
    class ComponentStatusChecker:
        @staticmethod
        def is_initialized(component) -> bool:
            """Check if component is initialized"""
            return getattr(component, 'is_initialized', False)
        
        @staticmethod
        def is_operational(component) -> bool:
            """Check if component is operational"""
            return getattr(component, 'is_operational', False)
        
        @staticmethod
        async def wait_for_initialization(component, timeout=5.0):
            """Wait for component to initialize"""
            elapsed = 0.0
            while elapsed < timeout:
                if ComponentStatusChecker.is_initialized(component):
                    return True
                await asyncio.sleep(0.1)
                elapsed += 0.1
            return False
    
    return ComponentStatusChecker()


# ========================================
# Markers for Test Organization
# ========================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "integration: Integration test requiring multiple components"
    )
    config.addinivalue_line(
        "markers", "workflow: End-to-end workflow test"
    )
    config.addinivalue_line(
        "markers", "async_test: Test with async operations"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running test (> 5s)"
    )
    config.addinivalue_line(
        "markers", "system: Full system test"
    )


# ========================================
# Hooks for Test Monitoring
# ========================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to track test results
    
    Logs test failures with detailed information
    """
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        logging.error(f"❌ Test failed: {item.nodeid}")
        if hasattr(rep, 'longrepr'):
            logging.error(f"Error details: {rep.longrepr}")


@pytest.fixture(autouse=True)
def log_test_execution(request):
    """
    Automatically log test execution
    
    Logs test start and completion
    """
    test_name = request.node.nodeid
    logging.info(f"▶️  Starting test: {test_name}")
    
    yield
    
    logging.info(f"✅ Completed test: {test_name}")
