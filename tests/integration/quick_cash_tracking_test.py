#!/usr/bin/env python3
"""
Quick Cash Tracking Test
=========================

Tests enhanced cash tracking in CentralRiskManager per Week 2 Day 3.
"""

import asyncio
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core_engine.system.central_risk_manager import CentralRiskManager

async def main():
    """Test enhanced cash tracking"""
    
    print("\n" + "="*80)
    print("Cash Tracking Enhancement - Quick Test")
    print("="*80)
    
    # Initialize Risk Manager
    config = {
        'monitoring_frequency': 5,
        'max_position_size': 0.10,
        'max_daily_var': 0.05
    }
    
    risk_manager = CentralRiskManager(config)
    await risk_manager.initialize()
    
    print(f"\n✅ Risk Manager initialized")
    print(f"   Initial Portfolio: ${risk_manager.portfolio_value:,.2f}")
    print(f"   Initial Cash: ${risk_manager.available_cash:,.2f}")
    
    # Test 1: BUY trade (cash decreases)
    print("\n" + "-"*80)
    print("Test 1: BUY trade - Cash should decrease")
    print("-"*80)
    
    result = risk_manager.update_position(
        symbol='AAPL',
        side='buy',
        quantity=100,
        price=150.0
    )
    
    print(f"\n📊 Buy Result:")
    print(f"   Symbol: {result['symbol']}")
    print(f"   Position: {result['previous_position']} → {result['new_position']}")
    print(f"   Cash Change: ${result['cash_change']:,.2f}")
    print(f"   Available Cash: ${result['available_cash']:,.2f}")
    print(f"   Portfolio Value: ${result['portfolio_value']:,.2f}")
    
    assert result['success'], "Buy should succeed"
    assert result['new_position'] == 100, "Position should be 100"
    assert result['cash_change'] == -15000, "Cash should decrease by $15,000"
    assert result['available_cash'] == 985000, "Cash should be $985,000"
    
    print("   ✅ PASSED")
    
    # Test 2: SELL trade (cash increases)
    print("\n" + "-"*80)
    print("Test 2: SELL trade - Cash should increase")
    print("-"*80)
    
    result = risk_manager.update_position(
        symbol='AAPL',
        side='sell',
        quantity=50,
        price=155.0
    )
    
    print(f"\n📊 Sell Result:")
    print(f"   Position: {result['previous_position']} → {result['new_position']}")
    print(f"   Cash Change: ${result['cash_change']:,.2f}")
    print(f"   Available Cash: ${result['available_cash']:,.2f}")
    print(f"   Portfolio Value: ${result['portfolio_value']:,.2f}")
    
    assert result['success'], "Sell should succeed"
    assert result['new_position'] == 50, "Position should be 50"
    assert result['cash_change'] == +7750, "Cash should increase by $7,750"
    assert result['available_cash'] == 992750, "Cash should be $992,750"
    
    print("   ✅ PASSED")
    
    # Test 3: Multiple trades sequence
    print("\n" + "-"*80)
    print("Test 3: Multiple trades - Track cash through sequence")
    print("-"*80)
    
    initial_cash = risk_manager.available_cash
    print(f"\n   Starting Cash: ${initial_cash:,.2f}")
    
    # Buy TSLA
    result1 = risk_manager.update_position('TSLA', 'buy', 50, 200.0)
    print(f"   After TSLA buy: Cash=${result1['available_cash']:,.2f}")
    
    # Buy NVDA
    result2 = risk_manager.update_position('NVDA', 'buy', 75, 300.0)
    print(f"   After NVDA buy: Cash=${result2['available_cash']:,.2f}")
    
    # Sell AAPL (remaining 50)
    result3 = risk_manager.update_position('AAPL', 'sell', 50, 160.0)
    print(f"   After AAPL sell: Cash=${result3['available_cash']:,.2f}")
    
    # Calculate expected cash
    expected_cash = initial_cash - 10000 - 22500 + 8000  # TSLA buy, NVDA buy, AAPL sell
    actual_cash = result3['available_cash']
    
    print(f"\n   Expected Cash: ${expected_cash:,.2f}")
    print(f"   Actual Cash: ${actual_cash:,.2f}")
    print(f"   Difference: ${abs(expected_cash - actual_cash):,.2f}")
    
    assert abs(actual_cash - expected_cash) < 1.0, "Cash tracking should be accurate"
    print("   ✅ PASSED")
    
    # Test 4: Position history tracking
    print("\n" + "-"*80)
    print("Test 4: Position history - Verify complete audit trail")
    print("-"*80)
    
    history = risk_manager.position_history
    print(f"\n   Total Transactions: {len(history)}")
    
    for i, record in enumerate(history, 1):
        print(f"   {i}. {record['timestamp'].strftime('%H:%M:%S')} - "
              f"{record['symbol']} {record['side'].upper()} {record['quantity']} @ ${record['price']:.2f} | "
              f"Cash: ${record['previous_cash']:,.0f} → ${record['new_cash']:,.0f}")
    
    assert len(history) == 5, "Should have 5 transactions"
    print("   ✅ PASSED - Complete audit trail maintained")
    
    # Test 5: Portfolio value calculation
    print("\n" + "-"*80)
    print("Test 5: Portfolio value = Positions + Cash")
    print("-"*80)
    
    # Get current positions
    positions = risk_manager.get_all_positions()
    print(f"\n   Current Positions:")
    for symbol, qty in positions.items():
        if qty != 0:
            print(f"      {symbol}: {qty}")
    
    # Calculate position value (using $100/share default)
    position_value = sum(abs(qty) * 100 for qty in positions.values())
    expected_portfolio = position_value + risk_manager.available_cash
    actual_portfolio = risk_manager.portfolio_value
    
    print(f"\n   Position Value: ${position_value:,.2f}")
    print(f"   Available Cash: ${risk_manager.available_cash:,.2f}")
    print(f"   Portfolio Value: ${actual_portfolio:,.2f}")
    print(f"   Expected: ${expected_portfolio:,.2f}")
    
    assert abs(actual_portfolio - expected_portfolio) < 1.0, "Portfolio value should match"
    print("   ✅ PASSED")
    
    # Test 6: Cash constraints
    print("\n" + "-"*80)
    print("Test 6: Verify cash can be used for authorization checks")
    print("-"*80)
    
    available_cash = risk_manager.available_cash
    print(f"\n   Available Cash: ${available_cash:,.2f}")
    print(f"   Can buy 1000 shares @ $500: {available_cash >= 500000}")
    print(f"   Can buy 2000 shares @ $500: {available_cash >= 1000000}")
    
    assert available_cash > 0, "Should have cash available"
    assert available_cash < 1000000, "Cash should have decreased from initial"
    print("   ✅ PASSED - Cash available for authorization decisions")
    
    print("\n" + "="*80)
    print("✅ ALL CASH TRACKING TESTS PASSED")
    print("="*80)
    print("\n📋 Summary:")
    print("   - BUY trades decrease cash ✅")
    print("   - SELL trades increase cash ✅")
    print("   - Multi-trade cash tracking accurate ✅")
    print("   - Complete position history maintained ✅")
    print("   - Portfolio = Positions + Cash ✅")
    print("   - Cash available for authorization checks ✅")
    print("\n🎉 Cash Tracking Enhancement: COMPLETE")
    print(f"\n💰 Final State:")
    print(f"   Portfolio Value: ${risk_manager.portfolio_value:,.2f}")
    print(f"   Available Cash: ${risk_manager.available_cash:,.2f}")
    print(f"   Active Positions: {len([p for p in risk_manager.get_all_positions().values() if p != 0])}")
    
    return True

if __name__ == '__main__':
    asyncio.run(main())

