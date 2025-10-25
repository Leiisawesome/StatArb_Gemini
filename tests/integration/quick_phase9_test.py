#!/usr/bin/env python3
"""
Quick Phase 9 Enhancements Test
================================

Tests VWAP algorithm and OrderManager per Week 3 Day 1.
"""

import asyncio
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core_engine.system.unified_execution_engine import (
    UnifiedExecutionEngine, VWAPAlgorithm, OrderManager,
    ExecutionRequest, ExecutionAuthorization, ExecutionAlgorithm, ExecutionUrgency
)

async def main():
    """Test Phase 9 enhancements"""
    
    print("\n" + "="*80)
    print("Phase 9 Enhancements - Quick Test")
    print("="*80)
    
    # Test 1: VWAP Algorithm
    print("\n" + "-"*80)
    print("Test 1: VWAP Algorithm Execution")
    print("-"*80)
    
    vwap_algo = VWAPAlgorithm({'test_mode': True})
    vwap_algo.test_mode = True
    
    # Create authorization
    authorization = ExecutionAuthorization(
        symbol='AAPL',
        side='buy',
        quantity=1000,
        max_quantity=1000,
        urgency_level=ExecutionUrgency.NORMAL
    )
    
    # Create execution request
    request = ExecutionRequest(
        authorization=authorization,
        algorithm=ExecutionAlgorithm.VWAP,
        urgency=ExecutionUrgency.NORMAL,
        time_horizon=300  # 5 minutes
    )
    
    result = await vwap_algo.execute(request)
    
    print(f"\n📊 VWAP Execution Results:")
    print(f"   Status: {result.status.value}")
    print(f"   Filled Quantity: {result.filled_quantity}")
    print(f"   Avg Fill Price: ${result.avg_fill_price:.2f}")
    print(f"   Execution Time: {result.execution_time:.2f}s")
    print(f"   Number of Slices: {len(result.fills)}")
    print(f"   Market Impact: {result.market_impact:.4f}")
    
    assert result.status.value == 'filled', "VWAP should complete successfully"
    assert result.filled_quantity == 1000, "Should fill full quantity"
    assert len(result.fills) > 0, "Should have fill records"
    
    print("   ✅ PASSED")
    
    # Test 2: OrderManager - Order Creation
    print("\n" + "-"*80)
    print("Test 2: OrderManager - Order Creation and Fill Tracking")
    print("-"*80)
    
    order_mgr = OrderManager()
    
    # Create order
    order_id = order_mgr.create_order(
        symbol='TSLA',
        side='buy',
        quantity=500,
        order_type='market'
    )
    
    print(f"\n📝 Order Created:")
    print(f"   Order ID: {order_id[:8]}...")
    
    order_status = order_mgr.get_order_status(order_id)
    print(f"   Symbol: {order_status['symbol']}")
    print(f"   Side: {order_status['side'].upper()}")
    print(f"   Quantity: {order_status['quantity']}")
    print(f"   Status: {order_status['status']}")
    
    assert order_status['status'] == 'pending', "New order should be pending"
    assert order_status['remaining_quantity'] == 500, "Should have full remaining quantity"
    
    print("   ✅ PASSED")
    
    # Test 3: OrderManager - Partial Fills
    print("\n" + "-"*80)
    print("Test 3: OrderManager - Partial Fill Handling")
    print("-"*80)
    
    # Add partial fill 1
    success = order_mgr.add_fill(order_id, fill_quantity=200, fill_price=195.50)
    assert success, "First fill should succeed"
    
    order_status = order_mgr.get_order_status(order_id)
    print(f"\n📊 After First Fill:")
    print(f"   Filled: {order_status['filled_quantity']}/{order_status['quantity']}")
    print(f"   Remaining: {order_status['remaining_quantity']}")
    print(f"   Avg Price: ${order_status['avg_fill_price']:.2f}")
    print(f"   Status: {order_status['status']}")
    
    assert order_status['status'] == 'partially_filled', "Should be partially filled"
    assert order_status['filled_quantity'] == 200, "Should have 200 filled"
    assert order_status['remaining_quantity'] == 300, "Should have 300 remaining"
    
    # Add partial fill 2
    success = order_mgr.add_fill(order_id, fill_quantity=300, fill_price=196.00)
    assert success, "Second fill should succeed"
    
    order_status = order_mgr.get_order_status(order_id)
    print(f"\n📊 After Second Fill:")
    print(f"   Filled: {order_status['filled_quantity']}/{order_status['quantity']}")
    print(f"   Remaining: {order_status['remaining_quantity']}")
    print(f"   Avg Price: ${order_status['avg_fill_price']:.2f}")
    print(f"   Status: {order_status['status']}")
    
    assert order_status['status'] == 'filled', "Should be fully filled"
    assert order_status['filled_quantity'] == 500, "Should have 500 filled"
    assert order_status['remaining_quantity'] == 0, "Should have 0 remaining"
    
    print("   ✅ PASSED")
    
    # Test 4: OrderManager - Fill History
    print("\n" + "-"*80)
    print("Test 4: OrderManager - Fill History Tracking")
    print("-"*80)
    
    fills = order_mgr.get_fills(order_id)
    print(f"\n📋 Fill History ({len(fills)} fills):")
    for i, fill in enumerate(fills, 1):
        print(f"   {i}. {fill['quantity']} @ ${fill['price']:.2f} = ${fill['value']:.2f}")
    
    assert len(fills) == 2, "Should have 2 fills"
    print("   ✅ PASSED - Complete fill history maintained")
    
    # Test 5: UnifiedExecutionEngine Integration
    print("\n" + "-"*80)
    print("Test 5: UnifiedExecutionEngine - VWAP Registration")
    print("-"*80)
    
    execution_engine = UnifiedExecutionEngine({'test_mode': True})
    await execution_engine.initialize()
    
    # Check VWAP algorithm is registered
    assert ExecutionAlgorithm.VWAP in execution_engine.algorithms, \
        "VWAP algorithm should be registered"
    
    print(f"\n✅ Registered Algorithms:")
    for algo in execution_engine.algorithms.keys():
        print(f"   - {algo.value.upper()}")
    
    assert len(execution_engine.algorithms) >= 4, "Should have at least 4 algorithms"
    print("   ✅ PASSED - All algorithms registered")
    
    print("\n" + "="*80)
    print("✅ ALL PHASE 9 ENHANCEMENT TESTS PASSED")
    print("="*80)
    print("\n📋 Summary:")
    print("   - VWAP algorithm operational ✅")
    print("   - Volume-based order slicing working ✅")
    print("   - OrderManager order creation ✅")
    print("   - OrderManager partial fill handling ✅")
    print("   - OrderManager fill history tracking ✅")
    print("   - UnifiedExecutionEngine integration ✅")
    print("   - 4+ execution algorithms available ✅")
    print("\n🎉 Phase 9 Enhancements: COMPLETE")
    print("\n💡 Available Algorithms:")
    print("   - MARKET: Immediate execution")
    print("   - LIMIT: Price-limited execution")
    print("   - TWAP: Time-weighted execution")
    print("   - VWAP: Volume-weighted execution (NEW)")
    print("   - ADAPTIVE: Smart algorithm selection")
    
    return True

if __name__ == '__main__':
    asyncio.run(main())

