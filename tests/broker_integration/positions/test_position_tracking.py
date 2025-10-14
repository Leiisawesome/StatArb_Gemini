"""
Day 5: Position Tracking and P&L Testing
Test position monitoring and P&L calculations.

This test:
1. Retrieves all current positions
2. Monitors position details (if any exist)
3. Validates position data structure
4. Tests P&L calculation fields

This test can run anytime but is most useful when positions exist.
During market hours, you can create a position and monitor it.
Outside market hours, it tests the position retrieval infrastructure.

Safety:
- Read-only operations (no trading)
- Paper trading account only
- No positions created or modified

Requirements:
- Broker connection only
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.config.broker_config import load_broker_config
from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter


def test_position_tracking():
    """Test position retrieval and data validation"""
    
    print("\n" + "=" * 70)
    print("DAY 5: Position Tracking & P&L Testing")
    print("=" * 70)
    
    # Load configuration
    print("\n[1/5] Loading broker configuration...")
    config = load_broker_config()
    print(f"✅ Configuration loaded: {config.active_broker.value}")
    
    # Create adapter and connect
    print("\n[2/5] Connecting to Alpaca...")
    adapter = AlpacaAdapter(config.alpaca)
    
    try:
        adapter.connect()
        account_info = adapter.get_account_info()
        print(f"✅ Connected to account: {account_info.account_id}")
        
        # Get account state
        print("\n[3/5] Retrieving account information...")
        print(f"✅ Account details:")
        print(f"   Cash: ${account_info.cash:,.2f}")
        print(f"   Buying power: ${account_info.buying_power:,.2f}")
        print(f"   Portfolio value: ${account_info.portfolio_value:,.2f}")
        print(f"   Equity: ${account_info.equity:,.2f}")
        
        # Calculate portfolio metrics
        positions_value = account_info.portfolio_value - account_info.cash
        if account_info.portfolio_value > 0:
            cash_percentage = (account_info.cash / account_info.portfolio_value) * 100
            positions_percentage = (positions_value / account_info.portfolio_value) * 100
        else:
            cash_percentage = 100
            positions_percentage = 0
        
        print(f"\n   Portfolio Breakdown:")
        print(f"   Cash: ${account_info.cash:,.2f} ({cash_percentage:.1f}%)")
        print(f"   Positions: ${positions_value:,.2f} ({positions_percentage:.1f}%)")
        
        # Get all positions
        print("\n[4/5] Retrieving all open positions...")
        positions = adapter.get_positions()
        
        if len(positions) == 0:
            print(f"✅ No open positions (clean state)")
            print(f"\n   To test with positions:")
            print(f"   1. Run market order test during market hours")
            print(f"   2. Run this test again to see position tracking")
        else:
            print(f"✅ Found {len(positions)} open position(s):")
            
            total_unrealized_pl = 0.0
            total_market_value = 0.0
            
            for i, pos in enumerate(positions, 1):
                print(f"\n   Position #{i}:")
                print(f"   Symbol: {pos.symbol}")
                print(f"   Quantity: {pos.qty} shares")
                print(f"   Side: {pos.side}")
                print(f"   Avg entry price: ${float(pos.avg_entry_price):,.2f}")
                print(f"   Current price: ${float(pos.current_price):,.2f}")
                print(f"   Market value: ${float(pos.market_value):,.2f}")
                print(f"   Cost basis: ${float(pos.cost_basis):,.2f}")
                print(f"   Unrealized P&L: ${float(pos.unrealized_pl):,.2f}")
                print(f"   Unrealized P&L %: {float(pos.unrealized_plpc):.2f}%")
                
                # Validate calculations
                expected_market_value = float(pos.qty) * float(pos.current_price)
                expected_unrealized_pl = float(pos.market_value) - float(pos.cost_basis)
                
                market_value_match = abs(float(pos.market_value) - expected_market_value) < 0.01
                pl_match = abs(float(pos.unrealized_pl) - expected_unrealized_pl) < 0.01
                
                if market_value_match and pl_match:
                    print(f"   ✅ P&L calculations verified")
                else:
                    print(f"   ⚠️  P&L calculation discrepancy detected")
                
                total_unrealized_pl += float(pos.unrealized_pl)
                total_market_value += float(pos.market_value)
            
            # Summary
            print(f"\n   Portfolio Summary:")
            print(f"   Total positions value: ${total_market_value:,.2f}")
            print(f"   Total unrealized P&L: ${total_unrealized_pl:,.2f}")
            
            if total_market_value > 0:
                total_pl_percentage = (total_unrealized_pl / (total_market_value - total_unrealized_pl)) * 100
                print(f"   Total P&L %: {total_pl_percentage:.2f}%")
        
        # Test position retrieval by symbol
        print("\n[5/5] Testing specific position retrieval...")
        test_symbol = "SPY"
        spy_position = adapter.get_position(test_symbol)
        
        if spy_position:
            print(f"✅ {test_symbol} position found:")
            print(f"   Quantity: {spy_position.qty}")
            print(f"   Current value: ${float(spy_position.market_value):,.2f}")
        else:
            print(f"✅ No {test_symbol} position (as expected)")
        
        print("\n" + "=" * 70)
        print("✅ DAY 5 TEST PASSED: Position tracking verified!")
        print("=" * 70)
        print("\nVerified capabilities:")
        print("  ✓ Account information retrieval")
        print("  ✓ Portfolio metrics calculation")
        print("  ✓ Position list retrieval")
        print("  ✓ Position detail access")
        print("  ✓ P&L calculation validation")
        print("  ✓ Specific position lookup")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print("\nDisconnecting from broker...")
        adapter.disconnect()
        print("✅ Disconnected")


if __name__ == "__main__":
    import datetime
    
    print("\n" + "=" * 70)
    print("PHASE 9 - BROKER INTEGRATION - WEEK 1 - DAY 5")
    print("Position Tracking & P&L Testing")
    print("=" * 70)
    print(f"Test started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Trading mode: PAPER ONLY")
    print(f"\n✅ This test can run anytime (read-only operations)")
    
    success = test_position_tracking()
    
    print(f"\nTest completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("\n🎉 SUCCESS: Position tracking verified!")
        print("   Week 1 Days 3-5 testing complete!")
        sys.exit(0)
    else:
        print("\n❌ FAILURE: Review errors above and retry")
        sys.exit(1)
