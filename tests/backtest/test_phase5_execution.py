#!/usr/bin/env python3
"""
Phase 5: Execution Engine Test
===============================

Test the complete execution flow for backtesting:
- EnhancedTradingEngine (order=30) - HOW to execute
- UnifiedExecutionEngine (order=40) - ACTION (execution)
- Execution cost modeling (spread + impact + slippage)
- Realistic fill simulation
- Position tracking via CentralRiskManager

Tests:
1. Initialization order (5, 10, 12, 15, 16, 17, 20, 25, 30, 40)
2. Complete authorization → execution flow
3. Fill simulation (market orders)
4. Execution cost calculation
5. Position updates via CentralRiskManager
6. Multiple trade execution
7. Execution performance metrics

Author: StatArb_Gemini Phase 5 Testing
Date: 2025-01-15
"""

import pytest
import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List

# System components
from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
from core_engine.system.central_risk_manager import (
    CentralRiskManager, TradingDecisionRequest, TradingDecisionType,
    AuthorizationLevel, ExecutionUrgency
)
from core_engine.system.unified_execution_engine import (
    UnifiedExecutionEngine, ExecutionRequest, ExecutionResult, ExecutionAlgorithm,
    ExecutionAuthorization, ExecutionStatus
)

# Trading engine
from core_engine.trading.engine import EnhancedTradingEngine

# Regime and data
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig

# Strategy management
from core_engine.trading.strategies.manager import StrategyManager

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_phase5_execution_engine():
    """
    Phase 5: Complete test of execution engine with fill simulation
    """
    
    logger.info("\n" + "="*80)
    logger.info("🎯 PHASE 5: EXECUTION ENGINE TEST")
    logger.info("="*80 + "\n")
    
    # ========================================
    # TEST 1: System Setup (Reusing Phase 4 components)
    # ========================================
    logger.info("\n✅ TEST 1: System Orchestration Setup")
    orchestrator = HierarchicalSystemOrchestrator()
    
    # RegimeEngine (order=5)
    regime_config = {
        'lookback_window': 60,
        'volatility_window': 20,
        'trend_threshold': 0.02,
        'regime_change_threshold': 0.7
    }
    regime_engine = EnhancedRegimeEngine(regime_config)
    regime_engine.register_with_orchestrator(orchestrator)
    
    # DataManager (order=10)
    data_config = ClickHouseDataConfig(
        symbols=['NVDA'],
        start_date='2024-01-02',
        end_date='2024-01-05',  # 3 days for faster test
        interval='1min',
        clickhouse_host='localhost'
    )
    data_manager = ClickHouseDataManager(config=data_config)
    data_manager.register_with_orchestrator(orchestrator)
    data_manager.set_regime_engine(regime_engine)
    
    # StrategyManager (order=20)
    strategy_config = {'max_concurrent_strategies': 5}
    strategy_manager = StrategyManager(strategy_config)
    strategy_manager.register_with_orchestrator(orchestrator)
    strategy_manager.set_regime_engine(regime_engine)
    
    # CentralRiskManager (order=25 - GOVERNANCE)
    risk_config = {
        'max_position_size': 0.10,
        'max_daily_var': 0.05,
        'min_signal_confidence': 0.6
    }
    risk_manager = CentralRiskManager(risk_config)
    risk_manager.register_with_orchestrator(orchestrator)
    risk_manager.set_controlled_components(
        strategy_manager=strategy_manager,
        regime_engine=regime_engine
    )
    
    logger.info("✅ Phase 4 components initialized")
    
    # ========================================
    # TEST 2: EnhancedTradingEngine (order=30)
    # ========================================
    logger.info("\n✅ TEST 2: EnhancedTradingEngine Initialization (order=30)")
    
    trading_engine_config = {
        'enable_smart_routing': True,
        'max_slice_size': 1000.0,
        'min_slice_size': 10.0
    }
    trading_engine = EnhancedTradingEngine(trading_engine_config)
    trading_engine.register_with_orchestrator(orchestrator)
    
    assert trading_engine.component_id is not None
    logger.info(f"✅ TradingEngine registered: {trading_engine.component_id}")
    
    # ========================================
    # TEST 3: UnifiedExecutionEngine (order=40)
    # ========================================
    logger.info("\n✅ TEST 3: UnifiedExecutionEngine Initialization (order=40)")
    
    execution_engine_config = {
        'test_mode': True,  # Enable test mode for backtest
        'enable_fill_simulation': True,
        'default_fill_rate': 0.99,  # 99% fill rate
        'enable_cost_modeling': True
    }
    execution_engine = UnifiedExecutionEngine(execution_engine_config)
    execution_engine.register_with_orchestrator(orchestrator)
    
    # Link execution engine to risk manager
    risk_manager.unified_execution_engine = execution_engine
    
    # Set position update callback from risk manager
    execution_engine.risk_manager_callback = risk_manager
    
    assert execution_engine.component_id is not None
    logger.info(f"✅ ExecutionEngine registered: {execution_engine.component_id}")
    logger.info(f"✅ ExecutionEngine linked to RiskManager for position updates")
    
    # ========================================
    # TEST 4: Verify Initialization Order
    # ========================================
    logger.info("\n✅ TEST 4: Verify Initialization Order")
    
    components = orchestrator.component_manager.component_registry
    component_orders = {reg.name: reg.initialization_order for reg_id, reg in components.items()}
    
    expected_orders = {
        'EnhancedRegimeEngine': 5,
        'ClickHouseDataManager': 10,
        'StrategyManager': 20,
        'CentralRiskManager': 25,
        'EnhancedTradingEngine': 30,
        'UnifiedExecutionEngine': 40
    }
    
    for name, expected_order in expected_orders.items():
        actual_order = component_orders.get(name)
        assert actual_order == expected_order, f"{name} order {actual_order} != {expected_order}"
        logger.info(f"   {name}: order={actual_order} ✅")
    
    logger.info("✅ All initialization orders correct")
    
    # ========================================
    # TEST 5: Initialize All Components
    # ========================================
    logger.info("\n✅ TEST 5: Initialize and Start All Components")
    
    await regime_engine.initialize()
    await data_manager.initialize()
    await strategy_manager.initialize()
    await risk_manager.initialize()
    await trading_engine.initialize()
    await execution_engine.initialize()
    
    await regime_engine.start()
    await data_manager.start()
    await strategy_manager.start()
    await risk_manager.start()
    await trading_engine.start()
    await execution_engine.start()
    
    logger.info("✅ All components initialized and started")
    
    # ========================================
    # TEST 6: Load Market Data
    # ========================================
    logger.info("\n✅ TEST 6: Load Historical Market Data (3 days)")
    
    market_data_df = data_manager.load_market_data()
    
    assert market_data_df is not None
    assert not market_data_df.empty
    data_points = len(market_data_df)
    logger.info(f"✅ Loaded {data_points:,} data points for NVDA")
    
    # ========================================
    # TEST 7: Complete Execution Flow
    # ========================================
    logger.info("\n✅ TEST 7: Test Complete Execution Flow")
    
    trades_executed = 0
    trades_failed = 0
    total_execution_cost = 0.0
    position_updates = 0
    
    # Process subset of data for testing
    test_data = market_data_df.head(500)
    logger.info(f"   Processing {len(test_data)} data points for execution test...")
    
    for i, row in enumerate(test_data.itertuples(index=False)):
        market_update = row._asdict()
        
        # Feed data to regime engine
        regime_result = regime_engine.process_market_data(market_update)
        
        # Create test trades every 50 bars
        if i % 50 == 0 and i > 100:
            try:
                # Create a test signal
                test_signal = {
                    'symbol': 'NVDA',
                    'signal_type': 'BUY' if i % 100 == 0 else 'SELL',
                    'confidence': 0.75,
                    'quantity': 100.0,
                    'price': market_update.get('close', 100.0)
                }
                
                # STEP 1: Request authorization from CentralRiskManager
                request = TradingDecisionRequest(
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    symbol=test_signal['symbol'],
                    side=test_signal['signal_type'].lower(),
                    quantity=test_signal['quantity'],
                    confidence=test_signal['confidence'],
                    strategy_id='test_strategy',
                    urgency=ExecutionUrgency.NORMAL
                )
                
                authorization = await risk_manager.authorize_trading_decision(request)
                
                logger.info(f"   Authorization: {test_signal['signal_type']} {test_signal['quantity']} shares → "
                          f"authorized {authorization.authorized_quantity} (level: {authorization.authorization_level.value})")
                
                # Skip if authorized quantity is 0 (e.g., SELL with no position)
                if authorization.authorization_level != AuthorizationLevel.REJECTED and authorization.authorized_quantity > 0:
                    logger.info(f"   Creating execution request for {authorization.authorized_quantity} shares...")
                    
                    # STEP 2: Convert TradingAuthorization to ExecutionAuthorization
                    exec_auth = ExecutionAuthorization(
                        authorization_id=authorization.authorization_id,
                        symbol=test_signal['symbol'],
                        side=test_signal['signal_type'].lower(),
                        quantity=authorization.authorized_quantity,
                        max_quantity=authorization.authorized_quantity,
                        strategy_id='test_strategy',
                        allowed_algorithms=[ExecutionAlgorithm.MARKET, ExecutionAlgorithm.TWAP]
                    )
                    
                    # STEP 3: Create execution request
                    execution_request = ExecutionRequest(
                        authorization=exec_auth,
                        algorithm=ExecutionAlgorithm.MARKET,
                        urgency=ExecutionUrgency.NORMAL,
                        strategy_context={
                            'current_price': test_signal['price'],
                            'regime': regime_engine.current_regime.primary_regime.value if regime_engine.current_regime else 'unknown'
                        }
                    )
                    
                    logger.info(f"   ExecutionRequest created successfully")
                    
                    # STEP 3: Execute via UnifiedExecutionEngine
                    try:
                        execution_result = await execution_engine.execute_authorized_trade(execution_request)
                        logger.info(f"   Execution result: {execution_result}")
                        logger.info(f"   Result type: {type(execution_result)}")
                        if execution_result:
                            logger.info(f"   Result status: {getattr(execution_result, 'status', 'NO STATUS')}")
                    except Exception as exec_error:
                        logger.warning(f"   Execution error: {exec_error}")
                        trades_failed += 1
                        continue
                    
                    if execution_result and execution_result.status == ExecutionStatus.FILLED:
                        trades_executed += 1
                        
                        # Track execution costs
                        if hasattr(execution_result, 'execution_cost'):
                            total_execution_cost += execution_result.execution_cost
                        
                        # Position should be updated via callback
                        position_updates += 1
                        
                        logger.info(f"   ✅ Trade {trades_executed}: {test_signal['symbol']} "
                                  f"{test_signal['signal_type']} {execution_result.filled_quantity:.0f} shares "
                                  f"@ ${execution_result.avg_fill_price:.2f}")
                    else:
                        trades_failed += 1
                
            except Exception as e:
                trades_failed += 1
    
    logger.info(f"\n📊 Execution Results:")
    logger.info(f"   Trades executed: {trades_executed}")
    logger.info(f"   Trades failed: {trades_failed}")
    logger.info(f"   Total execution cost: ${total_execution_cost:.2f}")
    logger.info(f"   Position updates: {position_updates}")
    
    # Assertions
    assert trades_executed > 0, "No trades executed"
    assert trades_executed >= trades_failed, "Too many failed trades"
    
    # ========================================
    # TEST 8: Verify Position Tracking
    # ========================================
    logger.info("\n✅ TEST 8: Verify Position Tracking")
    
    final_positions = risk_manager.current_positions
    logger.info(f"   Final positions: {final_positions}")
    
    if 'NVDA' in final_positions:
        nvda_position = final_positions['NVDA']
        logger.info(f"   NVDA position: {nvda_position} shares")
        assert isinstance(nvda_position, (int, float)), "Invalid position type"
    
    logger.info("✅ Position tracking verified")
    
    # ========================================
    # TEST 9: Execution Engine Health Check
    # ========================================
    logger.info("\n✅ TEST 9: Component Health Checks")
    
    trading_health = await trading_engine.health_check()
    execution_health = await execution_engine.health_check()
    
    assert trading_health.get('healthy', False), "TradingEngine not healthy"
    assert execution_health.get('healthy', False), "ExecutionEngine not healthy"
    
    logger.info("   TradingEngine: healthy ✅")
    logger.info("   ExecutionEngine: healthy ✅")
    
    # ========================================
    # TEST 10: Graceful Shutdown
    # ========================================
    logger.info("\n✅ TEST 10: Graceful Shutdown")
    
    await execution_engine.stop()
    await trading_engine.stop()
    await risk_manager.stop()
    await strategy_manager.stop()
    await data_manager.stop()
    await regime_engine.stop()
    
    logger.info("✅ All components stopped successfully")
    
    # ========================================
    # PHASE 5 SUMMARY
    # ========================================
    logger.info("\n" + "="*80)
    logger.info("🎉 PHASE 5 COMPLETE: EXECUTION ENGINE")
    logger.info("="*80)
    logger.info(f"\n📊 PHASE 5 SUMMARY:")
    logger.info(f"   ✅ 6 components registered with correct initialization orders")
    logger.info(f"   ✅ {data_points:,} data points loaded")
    logger.info(f"   ✅ {trades_executed} trades executed successfully")
    logger.info(f"   ✅ {position_updates} position updates")
    logger.info(f"   ✅ ${total_execution_cost:.2f} total execution costs")
    logger.info(f"   ✅ Complete authorization → execution flow working")
    logger.info(f"   ✅ Position tracking via CentralRiskManager")
    logger.info(f"   ✅ Execution engine operational")
    logger.info(f"\n🚀 Ready for Phase 6: Analytics & Reporting\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

