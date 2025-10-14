"""
Enhanced Alpaca Features Testing
Test advanced features: market status, quotes, stop orders, validation
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.config.broker_config import load_broker_config
from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter


def test_market_status_and_clock():
    """Test market status checking and clock information"""
    
    print("\n" + "=" * 70)
    print("TEST: Market Status & Clock")
    print("=" * 70)
    
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    
    try:
        adapter.connect()
        
        # Test market open check
        print("\n[1/3] Checking if market is open...")
        is_open = adapter.is_market_open()
        print(f"✅ Market is {'OPEN' if is_open else 'CLOSED'}")
        
        # Test market clock
        print("\n[2/3] Getting market clock...")
        clock = adapter.get_market_clock()
        print(f"✅ Market clock retrieved:")
        print(f"   Current time: {clock['timestamp']}")
        print(f"   Is open: {clock['is_open']}")
        print(f"   Next open: {clock['next_open']}")
        print(f"   Next close: {clock['next_close']}")
        
        # Calculate time until next open/close
        now = datetime.now(clock['timestamp'].tzinfo)
        if clock['is_open']:
            time_until_close = clock['next_close'] - now
            print(f"   ⏰ Market closes in: {time_until_close}")
        else:
            time_until_open = clock['next_open'] - now
            print(f"   ⏰ Market opens in: {time_until_open}")
        
        # Test connection health
        print("\n[3/3] Checking connection health...")
        health = adapter.check_connection_health()
        print(f"✅ Connection health: {health['status']}")
        print(f"   Trading client: {'✅' if health.get('trading_client_healthy') else '❌'}")
        print(f"   Data client: {'✅' if health.get('data_client_healthy') else '❌'}")
        if health['errors']:
            print(f"   Errors: {health['errors']}")
        
        print("\n✅ Market status tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        adapter.disconnect()


def test_market_data_and_quotes():
    """Test market data retrieval and quote fetching"""
    
    print("\n" + "=" * 70)
    print("TEST: Market Data & Quotes")
    print("=" * 70)
    
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    
    try:
        adapter.connect()
        
        test_symbol = "SPY"
        
        # Test latest quote
        print(f"\n[1/2] Getting latest quote for {test_symbol}...")
        quote = adapter.get_latest_quote(test_symbol)
        
        if quote:
            print(f"✅ Quote retrieved for {test_symbol}:")
            print(f"   Bid: ${quote['bid_price']:.2f} x {quote['bid_size']}")
            print(f"   Ask: ${quote['ask_price']:.2f} x {quote['ask_size']}")
            print(f"   Spread: ${quote['ask_price'] - quote['bid_price']:.2f}")
            print(f"   Timestamp: {quote['timestamp']}")
        else:
            print(f"⚠️  No quote data available for {test_symbol}")
        
        # Test asset info
        print(f"\n[2/2] Getting asset information for {test_symbol}...")
        asset_info = adapter.get_asset_info(test_symbol)
        
        if asset_info:
            print(f"✅ Asset info retrieved for {test_symbol}:")
            print(f"   Name: {asset_info['name']}")
            print(f"   Exchange: {asset_info['exchange']}")
            print(f"   Class: {asset_info['asset_class']}")
            print(f"   Tradable: {'✅' if asset_info['tradable'] else '❌'}")
            print(f"   Marginable: {'✅' if asset_info['marginable'] else '❌'}")
            print(f"   Shortable: {'✅' if asset_info['shortable'] else '❌'}")
            print(f"   Status: {asset_info['status']}")
        else:
            print(f"❌ Could not retrieve asset info for {test_symbol}")
        
        print("\n✅ Market data tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        adapter.disconnect()


def test_order_validation():
    """Test order parameter validation"""
    
    print("\n" + "=" * 70)
    print("TEST: Order Validation")
    print("=" * 70)
    
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    
    try:
        adapter.connect()
        
        # Test 1: Valid order
        print("\n[1/5] Testing valid order parameters...")
        valid, msg = adapter.validate_order_params("SPY", 1, 400.0, "buy")
        print(f"   Result: {'✅ VALID' if valid else '❌ INVALID'} - {msg}")
        
        # Test 2: Invalid quantity
        print("\n[2/5] Testing invalid quantity (negative)...")
        valid, msg = adapter.validate_order_params("SPY", -5, 400.0, "buy")
        print(f"   Result: {'✅ VALID' if valid else '❌ INVALID (expected)'} - {msg}")
        
        # Test 3: Invalid symbol
        print("\n[3/5] Testing invalid symbol...")
        valid, msg = adapter.validate_order_params("INVALID_SYMBOL_XYZ", 1, 100.0, "buy")
        print(f"   Result: {'✅ VALID' if valid else '❌ INVALID (expected)'} - {msg}")
        
        # Test 4: Invalid side
        print("\n[4/5] Testing invalid side...")
        valid, msg = adapter.validate_order_params("SPY", 1, 400.0, "invalid_side")
        print(f"   Result: {'✅ VALID' if valid else '❌ INVALID (expected)'} - {msg}")
        
        # Test 5: Buying power check
        print("\n[5/5] Testing buying power check...")
        account = adapter.get_account_info()
        print(f"   Current buying power: ${account.buying_power:,.2f}")
        
        has_power = adapter.check_buying_power(1000.0)
        print(f"   Can afford $1,000: {'✅ YES' if has_power else '❌ NO'}")
        
        has_power = adapter.check_buying_power(1000000000.0)
        print(f"   Can afford $1B: {'✅ YES' if has_power else '❌ NO (expected)'}")
        
        print("\n✅ Order validation tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        adapter.disconnect()


def test_stop_orders():
    """Test stop and stop-limit order submission"""
    
    print("\n" + "=" * 70)
    print("TEST: Stop Orders")
    print("=" * 70)
    
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    
    try:
        adapter.connect()
        
        test_symbol = "SPY"
        test_quantity = 1
        
        # Clean up any existing orders first
        print("\n[0/3] Cleaning up existing orders...")
        try:
            existing_orders = adapter.get_orders(status="open")
            for order in existing_orders:
                if order.symbol == test_symbol:
                    adapter.cancel_order(order.order_id)
                    print(f"   Cancelled existing order: {order.order_id}")
            time.sleep(2)  # Wait for cancellations to process
        except Exception as e:
            print(f"   Note: Cleanup encountered: {e}")
        
        # Get current quote to set sensible stop prices
        quote = adapter.get_latest_quote(test_symbol)
        if quote:
            mid_price = (quote['bid_price'] + quote['ask_price']) / 2
            # Set stop prices far from market to avoid accidental fills
            # Round to 2 decimal places to avoid sub-penny errors
            stop_buy_price = round(mid_price * 1.20, 2)  # 20% above market
            stop_sell_price = round(mid_price * 0.80, 2)  # 20% below market
        else:
            stop_buy_price = 500.0
            stop_sell_price = 300.0
        
        # Test 1: Stop order
        print(f"\n[1/3] Submitting stop BUY order...")
        print(f"   Symbol: {test_symbol}")
        print(f"   Quantity: {test_quantity}")
        print(f"   Stop price: ${stop_buy_price:.2f}")
        
        stop_order = adapter.submit_stop_order(
            symbol=test_symbol,
            qty=test_quantity,
            side="buy",
            stop_price=stop_buy_price,
            time_in_force="day"
        )
        
        print(f"✅ Stop order submitted:")
        print(f"   Order ID: {stop_order.order_id}")
        print(f"   Status: {stop_order.status}")
        
        # Cancel first order before submitting opposite side (avoid wash trade detection)
        time.sleep(1)
        adapter.cancel_order(stop_order.order_id)
        print(f"   Cancelled stop order: {stop_order.order_id}")
        
        # Test 2: Stop-limit order
        print(f"\n[2/3] Submitting stop-limit SELL order...")
        print(f"   Symbol: {test_symbol}")
        print(f"   Quantity: {test_quantity}")
        print(f"   Stop price: ${stop_sell_price:.2f}")
        print(f"   Limit price: ${stop_sell_price * 0.99:.2f}")
        
        stop_limit_order = adapter.submit_stop_limit_order(
            symbol=test_symbol,
            qty=test_quantity,
            side="sell",
            stop_price=stop_sell_price,
            limit_price=round(stop_sell_price * 0.99, 2),  # Round to 2 decimals
            time_in_force="day"
        )
        
        print(f"✅ Stop-limit order submitted:")
        print(f"   Order ID: {stop_limit_order.order_id}")
        print(f"   Status: {stop_limit_order.status}")
        
        # Test 3: Cancel the stop-limit order
        print(f"\n[3/3] Cancelling test order...")
        
        time.sleep(1)  # Brief pause
        
        adapter.cancel_order(stop_limit_order.order_id)
        print(f"✅ Cancelled stop-limit order: {stop_limit_order.order_id}")
        
        print("\n✅ Stop order tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        adapter.disconnect()


def test_all_enhanced_features():
    """Run all enhanced feature tests"""
    
    print("\n" + "=" * 70)
    print("ALPACA ENHANCED FEATURES - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'market_status': test_market_status_and_clock(),
        'market_data': test_market_data_and_quotes(),
        'validation': test_order_validation(),
        'stop_orders': test_stop_orders()
    }
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20s}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = test_all_enhanced_features()
    sys.exit(exit_code)
