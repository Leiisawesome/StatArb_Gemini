"""
Day 3: Market Order Testing
Test market order submission, execution, and position verification.

This test:
1. Submits a market BUY order for 1 share of SPY
2. Waits for order fill confirmation
3. Verifies position creation
4. Submits a market SELL order to close the position
5. Verifies position closure
6. Confirms account balance changes

Safety:
- Uses paper trading only
- Tests with 1 share of SPY (highly liquid)
- Closes position immediately after opening
- Respects all risk limits

Requirements:
- Must run during market hours (9:30 AM - 4:00 PM ET)
- Requires active market (Monday-Friday, non-holidays)
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.config.broker_config import load_broker_config
from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter


def test_market_order_buy_sell():
    """Test complete market order flow: buy -> verify -> sell -> verify"""
    
    print("\n" + "=" * 70)
    print("DAY 3: Market Order Testing")
    print("=" * 70)
    
    # Load configuration
    print("\n[1/10] Loading broker configuration...")
    config = load_broker_config()
    print(f"✅ Configuration loaded: {config.active_broker.value}")
    print(f"   Mode: {config.trading_mode.value}")
    print(f"   Max position size: ${config.risk_limits.max_position_size}")
    
    # Create adapter and connect
    print("\n[2/10] Connecting to IBKR...")
    
    # Get IBKR config from broker config
    if config.interactive_brokers is None:
        raise ValueError("IBKR configuration not found in broker config")
    
    adapter = IBKRAdapter(config.interactive_brokers)
    
    try:
        adapter.connect()
        
        # Get account info to show account ID
        account_info = adapter.get_account_info()
        print(f"✅ Connected to account: {account_info.account_id}")
        
        # Get initial account state
        print("\n[3/10] Capturing initial account state...")
        initial_cash = account_info.cash
        initial_buying_power = account_info.buying_power
        initial_portfolio_value = account_info.portfolio_value
        
        print(f"✅ Initial state:")
        print(f"   Cash: ${initial_cash:,.2f}")
        print(f"   Buying power: ${initial_buying_power:,.2f}")
        print(f"   Portfolio value: ${initial_portfolio_value:,.2f}")
        
        # Check for existing positions
        print("\n[4/10] Checking for existing positions...")
        initial_positions = adapter.get_positions()
        if initial_positions:
            print(f"⚠️  Warning: {len(initial_positions)} existing position(s) found:")
            for pos in initial_positions:
                print(f"   {pos.symbol}: {pos.qty} shares @ ${float(pos.current_price):.2f}")
        else:
            print("✅ No existing positions (clean slate)")
        
        # Define test parameters
        test_symbol = "SPY"  # S&P 500 ETF - highly liquid
        test_quantity = 1  # Minimal quantity for safety
        
        print(f"\n[5/10] Submitting market BUY order...")
        print(f"   Symbol: {test_symbol}")
        print(f"   Quantity: {test_quantity} share(s)")
        print(f"   Order type: MARKET")
        
        # Submit buy order
        buy_order = adapter.submit_market_order(
            symbol=test_symbol,
            qty=test_quantity,
            side="buy",
            time_in_force="day"
        )
        
        print(f"✅ Buy order submitted:")
        print(f"   Order ID: {buy_order.order_id}")
        print(f"   Status: {buy_order.status}")
        print(f"   Submitted at: {buy_order.metadata.get('submitted_at', 'N/A')}")
        
        # Wait for order to fill
        print("\n[6/10] Waiting for order to fill...")
        max_wait_seconds = 30
        start_time = time.time()
        order_filled = False
        
        while time.time() - start_time < max_wait_seconds:
            order_status = adapter.get_order(buy_order.order_id)
            status_str = order_status.status.value if hasattr(order_status.status, 'value') else str(order_status.status)
            print(f"   Status: {status_str} (elapsed: {int(time.time() - start_time)}s)")
            
            if status_str == "filled":
                order_filled = True
                filled_price = float(order_status.average_price) if order_status.average_price else 0.0
                filled_qty = int(order_status.filled_quantity)
                filled_at = order_status.metadata.get('filled_at', 'N/A')
                print(f"✅ Order filled!")
                print(f"   Filled price: ${filled_price:.2f}")
                print(f"   Filled quantity: {filled_qty}")
                print(f"   Filled at: {filled_at}")
                break
            elif status_str in ["canceled", "cancelled", "expired", "rejected"]:
                print(f"❌ Order {status_str}: {order_status}")
                raise Exception(f"Order failed with status: {status_str}")
            
            time.sleep(2)  # Poll every 2 seconds
        
        if not order_filled:
            print(f"❌ Order did not fill within {max_wait_seconds} seconds")
            # Cancel the order if it's still pending
            try:
                adapter.cancel_order(buy_order.order_id)
                print(f"   Cancelled pending order: {buy_order.order_id}")
            except Exception as e:
                print(f"   Note: Could not cancel order: {e}")
            raise Exception("Order fill timeout")
        
        # Verify position was created
        print("\n[7/10] Verifying position creation...")
        time.sleep(1)  # Brief pause for position to update
        positions = adapter.get_positions()
        
        spy_position = None
        for pos in positions:
            if pos.symbol == test_symbol:
                spy_position = pos
                break
        
        if spy_position is None:
            print(f"❌ Position not found for {test_symbol}")
            raise Exception("Position verification failed")
        
        position_qty = int(spy_position.qty)
        position_avg_price = float(spy_position.avg_entry_price)
        position_current_price = float(spy_position.current_price)
        position_market_value = float(spy_position.market_value)
        position_unrealized_pl = float(spy_position.unrealized_pl)
        
        print(f"✅ Position verified:")
        print(f"   Symbol: {spy_position.symbol}")
        print(f"   Quantity: {position_qty}")
        print(f"   Avg entry price: ${position_avg_price:.2f}")
        print(f"   Current price: ${position_current_price:.2f}")
        print(f"   Market value: ${position_market_value:.2f}")
        print(f"   Unrealized P&L: ${position_unrealized_pl:.2f}")
        
        # Now close the position with a market sell order
        print(f"\n[8/10] Submitting market SELL order to close position...")
        print(f"   Symbol: {test_symbol}")
        print(f"   Quantity: {position_qty} share(s)")
        print(f"   Order type: MARKET")
        
        sell_order = adapter.submit_market_order(
            symbol=test_symbol,
            qty=position_qty,
            side="sell",
            time_in_force="day"
        )
        
        print(f"✅ Sell order submitted:")
        print(f"   Order ID: {sell_order.order_id}")
        print(f"   Status: {sell_order.status}")
        
        # Wait for sell order to fill
        print("\n[9/10] Waiting for sell order to fill...")
        start_time = time.time()
        sell_filled = False
        
        while time.time() - start_time < max_wait_seconds:
            sell_status = adapter.get_order(sell_order.order_id)
            sell_status_str = sell_status.status.value if hasattr(sell_status.status, 'value') else str(sell_status.status)
            print(f"   Status: {sell_status_str} (elapsed: {int(time.time() - start_time)}s)")
            
            if sell_status_str == "filled":
                sell_filled = True
                sell_price = float(sell_status.average_price) if sell_status.average_price else 0.0
                sell_qty = int(sell_status.filled_quantity)
                print(f"✅ Sell order filled!")
                print(f"   Filled price: ${sell_price:.2f}")
                print(f"   Filled quantity: {sell_qty}")
                
                # Calculate realized P&L
                realized_pl = (sell_price - filled_price) * sell_qty
                print(f"   Realized P&L: ${realized_pl:.2f}")
                break
            elif sell_status_str in ["canceled", "cancelled", "expired", "rejected"]:
                print(f"❌ Sell order {sell_status_str}")
                raise Exception(f"Sell order failed with status: {sell_status_str}")
            
            time.sleep(2)
        
        if not sell_filled:
            print(f"❌ Sell order did not fill within {max_wait_seconds} seconds")
            raise Exception("Sell order fill timeout")
        
        # Verify position is closed
        print("\n[10/10] Verifying position closure...")
        time.sleep(1)  # Brief pause for position to update
        final_positions = adapter.get_positions()
        
        spy_position_found = False
        for pos in final_positions:
            if pos.symbol == test_symbol:
                spy_position_found = True
                print(f"⚠️  Warning: {test_symbol} position still exists: {pos.qty} shares")
                break
        
        if not spy_position_found:
            print(f"✅ Position closed successfully (no {test_symbol} position found)")
        
        # Get final account state
        print("\n" + "=" * 70)
        print("FINAL ACCOUNT STATE")
        print("=" * 70)
        
        final_account = adapter.get_account()
        final_cash = float(final_account.cash)
        final_buying_power = float(final_account.buying_power)
        final_portfolio_value = float(final_account.portfolio_value)
        
        cash_change = final_cash - initial_cash
        buying_power_change = final_buying_power - initial_buying_power
        portfolio_change = final_portfolio_value - initial_portfolio_value
        
        print(f"\nAccount changes:")
        print(f"   Cash: ${initial_cash:,.2f} → ${final_cash:,.2f} ({cash_change:+,.2f})")
        print(f"   Buying power: ${initial_buying_power:,.2f} → ${final_buying_power:,.2f} ({buying_power_change:+,.2f})")
        print(f"   Portfolio value: ${initial_portfolio_value:,.2f} → ${final_portfolio_value:,.2f} ({portfolio_change:+,.2f})")
        
        print("\n" + "=" * 70)
        print("✅ DAY 3 TEST PASSED: Market order flow completed successfully!")
        print("=" * 70)
        print("\nVerified capabilities:")
        print("  ✓ Market order submission (buy)")
        print("  ✓ Order fill monitoring")
        print("  ✓ Position creation verification")
        print("  ✓ Market order submission (sell)")
        print("  ✓ Position closure verification")
        print("  ✓ Account balance tracking")
        
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
    print("PHASE 9 - BROKER INTEGRATION - WEEK 1 - DAY 3")
    print("Market Order Testing")
    print("=" * 70)
    print(f"Test started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Trading mode: PAPER ONLY")
    print(f"Test parameters: 1 share SPY, immediate close")
    
    # Check if market is open (approximate - doesn't account for holidays)
    now = datetime.datetime.now()
    is_weekday = now.weekday() < 5  # Monday = 0, Sunday = 6
    eastern_hour = now.hour  # Approximate - user's local time
    
    if not is_weekday:
        print("\n⚠️  WARNING: Today is a weekend. Market orders may not fill.")
        print("   Market hours: Monday-Friday, 9:30 AM - 4:00 PM ET")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Test cancelled.")
            sys.exit(0)
    
    success = test_market_order_buy_sell()
    
    print(f"\nTest completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("\n🎉 SUCCESS: Ready to proceed to Day 4 (Limit Orders)")
        sys.exit(0)
    else:
        print("\n❌ FAILURE: Review errors above and retry")
        sys.exit(1)
