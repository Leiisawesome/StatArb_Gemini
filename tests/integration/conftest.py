"""
Integration Test Fixtures
=========================

Comprehensive fixtures for integration testing with REAL components (not mocks).
All fixtures provide actual component instances for true integration testing.

Author: StatArb_Gemini Integration Test Suite
Date: November 4, 2025
Version: 1.0.0
"""

import pytest
import pytest_asyncio
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Prevent importing problematic modules from main conftest
sys.modules['tests.performance'] = None
sys.modules['tests.performance.benchmarks'] = None
sys.modules['tests.performance.benchmarks.latency_testing'] = None

# Core engine imports
from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
from core_engine.system.orchestrator_components import ComponentLayer, AuthorityLevel
from core_engine.system.central_risk_manager import CentralRiskManager, TradingDecisionRequest, TradingDecisionType
from core_engine.data.manager import ClickHouseDataManager
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.trading.strategies.manager import StrategyManager
from core_engine.system.unified_execution_engine import UnifiedExecutionEngine
from core_engine.trading.engine import EnhancedTradingEngine
from core_engine.processing.pipeline_orchestrator import ProcessingPipelineOrchestrator
from core_engine.analytics.manager_enhanced import EnhancedAnalyticsManager

# Configuration imports
from core_engine.config.component_config import (
    RiskConfig, DataConfig, RegimeConfig, ExecutionConfig
)
# StrategyConfig is in StrategyManagerConfig
from core_engine.trading.strategies.manager import StrategyManagerConfig

logger = logging.getLogger(__name__)

# ==============================================================================
# EVENT LOOP FIXTURE
# ==============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ==============================================================================
# SYSTEM ORCHESTRATOR FIXTURES
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def orchestrator():
    """
    Create REAL HierarchicalSystemOrchestrator for integration tests.
    
    This is a REAL component, not a mock.
    """
    orchestrator = HierarchicalSystemOrchestrator()
    await orchestrator.initialize()
    yield orchestrator
    await orchestrator.shutdown()

@pytest_asyncio.fixture(scope="function")
async def initialized_orchestrator():
    """
    Create initialized orchestrator with system started.
    """
    orchestrator = HierarchicalSystemOrchestrator()
    await orchestrator.initialize()
    await orchestrator.start()
    yield orchestrator
    await orchestrator.stop()
    await orchestrator.shutdown()

# ==============================================================================
# REGIME ENGINE FIXTURES (Regime-First Principle)
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def regime_engine():
    """
    Create REAL EnhancedRegimeEngine for integration tests.
    
    This is the FOUNDATION component (initializes FIRST per Rule 2).
    """
    config = RegimeConfig()
    engine = EnhancedRegimeEngine(config)
    await engine.initialize()
    await engine.start()
    yield engine
    await engine.stop()

# ==============================================================================
# RISK MANAGER FIXTURES
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def risk_manager():
    """
    Create REAL CentralRiskManager for integration tests.
    
    This is the GOVERNANCE layer component (Layer 1).
    """
    config = RiskConfig()
    manager = CentralRiskManager(config)
    await manager.initialize()
    yield manager
    await manager.stop()

@pytest_asyncio.fixture(scope="function")
async def risk_manager_with_orchestrator(orchestrator, risk_manager):
    """
    Create risk manager registered with orchestrator.
    """
    orchestrator.register_central_risk_manager(risk_manager)
    yield {'orchestrator': orchestrator, 'risk_manager': risk_manager}

# ==============================================================================
# DATA MANAGER FIXTURES
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def data_manager():
    """
    Create REAL ClickHouseDataManager for integration tests.
    
    Note: In tests, this may use mock data or test database.
    """
    config = DataConfig()
    manager = ClickHouseDataManager(config)
    await manager.initialize()
    yield manager
    await manager.stop()

@pytest_asyncio.fixture(scope="function")
async def data_manager_with_regime(data_manager, regime_engine):
    """
    Create data manager with regime engine injected (Regime-First).
    """
    data_manager.set_regime_engine(regime_engine)
    yield {'data_manager': data_manager, 'regime_engine': regime_engine}

# ==============================================================================
# PIPELINE FIXTURES
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def pipeline_orchestrator():
    """
    Create REAL ProcessingPipelineOrchestrator for integration tests.
    """
    from core_engine.config.component_config import (
        IndicatorConfig, FeatureConfig, SignalConfig
    )
    
    config = {
        'data_config': DataConfig(),
        'indicator_config': IndicatorConfig(),
        'feature_config': FeatureConfig(),
        'signal_config': SignalConfig()
    }
    
    pipeline = ProcessingPipelineOrchestrator(**config)
    await pipeline.initialize()
    yield pipeline
    await pipeline.stop()

# ==============================================================================
# STRATEGY MANAGER FIXTURES
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def strategy_manager():
    """
    Create REAL StrategyManager for integration tests.
    """
    config = {}  # StrategyManager accepts dict config
    manager = StrategyManager(config)
    await manager.initialize()
    yield manager
    await manager.stop()

@pytest_asyncio.fixture(scope="function")
async def strategy_manager_with_risk(strategy_manager, risk_manager):
    """
    Create strategy manager with risk manager integration.
    """
    strategy_manager.set_risk_manager(risk_manager)
    yield {'strategy_manager': strategy_manager, 'risk_manager': risk_manager}

# ==============================================================================
# EXECUTION ENGINE FIXTURES
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def execution_engine():
    """
    Create REAL UnifiedExecutionEngine for integration tests.
    """
    config = ExecutionConfig()
    engine = UnifiedExecutionEngine(config)
    await engine.initialize()
    yield engine
    await engine.stop()

@pytest_asyncio.fixture(scope="function")
async def execution_engine_with_risk(execution_engine, risk_manager):
    """
    Create execution engine with risk manager callback.
    """
    # Set risk manager callback for position updates
    execution_engine.set_risk_manager_callback(risk_manager)
    yield {'execution_engine': execution_engine, 'risk_manager': risk_manager}

# ==============================================================================
# TRADING ENGINE FIXTURES
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def trading_engine():
    """
    Create REAL EnhancedTradingEngine for integration tests.
    """
    config = ExecutionConfig()
    engine = EnhancedTradingEngine(config)
    await engine.initialize()
    yield engine
    await engine.stop()

# ==============================================================================
# ANALYTICS MANAGER FIXTURES
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def analytics_manager():
    """
    Create REAL EnhancedAnalyticsManager for integration tests.
    """
    from core_engine.config.component_config import AnalyticsConfig
    config = AnalyticsConfig()
    manager = EnhancedAnalyticsManager(config)
    await manager.initialize()
    yield manager
    await manager.stop()

# ==============================================================================
# COMPLETE SYSTEM FIXTURE
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def complete_system():
    """
    Create COMPLETE integrated system with all components.
    
    This fixture provides a fully integrated system for end-to-end testing.
    Components are initialized in correct order (Regime-First).
    """
    # STEP 1: Initialize RegimeEngine FIRST (order=5) - Rule 2
    regime_config = RegimeConfig()
    regime_engine = EnhancedRegimeEngine(regime_config)
    await regime_engine.initialize()
    await regime_engine.start()
    
    # STEP 2: Initialize Orchestrator
    orchestrator = HierarchicalSystemOrchestrator()
    await orchestrator.initialize()
    
    # STEP 3: Initialize RiskManager (order=25) - Governance
    risk_config = RiskConfig()
    risk_manager = CentralRiskManager(risk_config)
    await risk_manager.initialize()
    orchestrator.register_central_risk_manager(risk_manager)
    
    # STEP 4: Initialize DataManager (order=10) - with regime context
    data_config = DataConfig()
    data_manager = ClickHouseDataManager(data_config)
    data_manager.set_regime_engine(regime_engine)
    await data_manager.initialize()
    orchestrator.register_component(
        "ClickHouseDataManager", data_manager,
        ComponentLayer.SUPPORT, AuthorityLevel.OPERATIONAL,
        initialization_order=10
    )
    
    # STEP 5: Initialize Pipeline (order=15)
    from core_engine.config.component_config import (
        IndicatorConfig, FeatureConfig, SignalConfig
    )
    pipeline_config = {
        'data_config': data_config,
        'indicator_config': IndicatorConfig(),
        'feature_config': FeatureConfig(),
        'signal_config': SignalConfig()
    }
    pipeline = ProcessingPipelineOrchestrator(**pipeline_config)
    pipeline.set_regime_engine(regime_engine)
    await pipeline.initialize()
    orchestrator.register_component(
        "ProcessingPipelineOrchestrator", pipeline,
        ComponentLayer.SUPPORT, AuthorityLevel.OPERATIONAL,
        initialization_order=15
    )
    
    # STEP 6: Initialize StrategyManager (order=20)
    strategy_config = {}  # StrategyManager accepts dict config
    strategy_manager = StrategyManager(strategy_config)
    strategy_manager.set_risk_manager(risk_manager)
    strategy_manager.set_regime_engine(regime_engine)
    await strategy_manager.initialize()
    orchestrator.register_component(
        "StrategyManager", strategy_manager,
        ComponentLayer.EXECUTION, AuthorityLevel.OPERATIONAL,
        initialization_order=20
    )
    
    # STEP 7: Initialize TradingEngine (order=30)
    execution_config = ExecutionConfig()
    trading_engine = EnhancedTradingEngine(execution_config)
    trading_engine.set_risk_manager(risk_manager)
    await trading_engine.initialize()
    orchestrator.register_component(
        "EnhancedTradingEngine", trading_engine,
        ComponentLayer.EXECUTION, AuthorityLevel.OPERATIONAL,
        initialization_order=30
    )
    
    # STEP 8: Initialize ExecutionEngine (order=40)
    execution_engine = UnifiedExecutionEngine(execution_config)
    execution_engine.set_risk_manager_callback(risk_manager)
    await execution_engine.initialize()
    orchestrator.register_component(
        "UnifiedExecutionEngine", execution_engine,
        ComponentLayer.EXECUTION, AuthorityLevel.OPERATIONAL,
        initialization_order=40
    )
    
    # STEP 9: Initialize AnalyticsManager (order=35)
    from core_engine.config.component_config import AnalyticsConfig
    analytics_config = AnalyticsConfig()
    analytics_manager = EnhancedAnalyticsManager(analytics_config)
    await analytics_manager.initialize()
    orchestrator.register_component(
        "EnhancedAnalyticsManager", analytics_manager,
        ComponentLayer.EXECUTION, AuthorityLevel.OPERATIONAL,
        initialization_order=35
    )
    
    # Start system
    await orchestrator.start()
    
    system = {
        'orchestrator': orchestrator,
        'regime_engine': regime_engine,
        'risk_manager': risk_manager,
        'data_manager': data_manager,
        'pipeline': pipeline,
        'strategy_manager': strategy_manager,
        'trading_engine': trading_engine,
        'execution_engine': execution_engine,
        'analytics_manager': analytics_manager
    }
    
    yield system
    
    # Cleanup in reverse order
    await orchestrator.stop()
    await analytics_manager.stop()
    await execution_engine.stop()
    await trading_engine.stop()
    await strategy_manager.stop()
    await pipeline.stop()
    await data_manager.stop()
    await risk_manager.stop()
    await regime_engine.stop()
    await orchestrator.shutdown()

# ==============================================================================
# TEST DATA GENERATORS
# ==============================================================================

@pytest.fixture
def create_enriched_data():
    """
    Create enriched market data for strategy testing.
    
    Returns DataFrame with OHLCV + indicators + features.
    """
    def _create(symbols: List[str] = ['AAPL'], rows: int = 200) -> Dict[str, pd.DataFrame]:
        """Create enriched data for symbols"""
        enriched = {}
        
        for symbol in symbols:
            dates = pd.date_range(start='2024-01-01', periods=rows, freq='1min')
            np.random.seed(42)  # For reproducibility
            
            # Generate OHLCV data
            base_price = 100.0
            prices = []
            for i in range(rows):
                change = np.random.normal(0, 0.01)
                base_price *= (1 + change)
                prices.append(base_price)
            
            df = pd.DataFrame({
                'timestamp': dates,
                'open': prices,
                'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
                'close': prices,
                'volume': np.random.randint(1000, 10000, rows)
            })
            
            # Add indicators (simplified)
            df['SMA_10'] = df['close'].rolling(10).mean()
            df['SMA_20'] = df['close'].rolling(20).mean()
            df['RSI_14'] = 50.0  # Simplified RSI
            df['MACD'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
            df['ADX_14'] = 20.0  # Simplified ADX
            df['ATR_14'] = df['high'].rolling(14).max() - df['low'].rolling(14).min()
            
            # Add features
            df['returns_1'] = df['close'].pct_change(1)
            df['momentum_score'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10)
            df['volatility_ratio'] = df['returns_1'].rolling(20).std() / df['returns_1'].rolling(60).std()
            df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
            
            # Add signals
            df['signal_type'] = 'HOLD'
            df['signal_strength'] = 0
            df['confidence'] = 0.5
            
            enriched[symbol] = df
        
        return enriched
    
    return _create

@pytest.fixture
def create_trading_decision_request():
    """
    Create TradingDecisionRequest for risk authorization tests.
    """
    def _create(
        symbol: str = 'AAPL',
        side: str = 'buy',
        quantity: float = 100.0,
        confidence: float = 0.75,
        strategy_id: str = 'test_strategy'
    ) -> TradingDecisionRequest:
        return TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol=symbol,
            side=side,
            quantity=quantity,
            confidence=confidence,
            strategy_id=strategy_id,
            requesting_component='StrategyManager'
        )
    
    return _create

# ==============================================================================
# HELPER FIXTURES
# ==============================================================================

@pytest.fixture
def wait_for_condition():
    """
    Wait for async condition with timeout.
    """
    async def _wait(
        condition_fn,
        timeout: float = 5.0,
        interval: float = 0.1,
        error_msg: str = "Condition not met"
    ):
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            if await condition_fn() if asyncio.iscoroutinefunction(condition_fn) else condition_fn():
                return True
            await asyncio.sleep(interval)
        raise TimeoutError(error_msg)
    
    return _wait

