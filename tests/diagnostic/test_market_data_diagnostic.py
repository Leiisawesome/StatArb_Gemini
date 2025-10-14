"""
Simple IBKR market data diagnostic test
Tests if we're receiving any tick callbacks at all
"""

from core_engine.config.broker_config import load_broker_config
from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter
import time

print("="*80)
print("IBKR Market Data Diagnostic Test")
print("="*80)

config = load_broker_config()
adapter = IBKRAdapter(config.interactive_brokers)

print("\n1. Connecting to IBKR...")
adapter.connect()
print("   ✅ Connected")

print(f"\n2. Market data mode: {1 if adapter.config.paper_trading else 'N/A'} (1=real-time)")
print(f"   Wrapper quotes dict: {len(adapter.wrapper.quotes)} entries")

print("\n3. Requesting market data for SPY...")
contract = adapter._create_stock_contract('SPY')
req_id = 999  # Use a specific ID for tracking

# Request market data
adapter.client.reqMktData(req_id, contract, "", False, False, [])
print(f"   Market data request sent (req_id={req_id})")

# Wait and monitor for callbacks
print("\n4. Waiting 10 seconds for callbacks...")
for i in range(10):
    time.sleep(1)
    if req_id in adapter.wrapper.quotes:
        print(f"   [{i+1}s] ✅ Got data: {adapter.wrapper.quotes[req_id]}")
    else:
        print(f"   [{i+1}s] Waiting...")

# Check final result
print("\n5. Final result:")
if req_id in adapter.wrapper.quotes:
    quote_data = adapter.wrapper.quotes[req_id]
    print(f"   ✅ Received callbacks!")
    print(f"   Data: {quote_data}")
    
    if 'bid_price' in quote_data and quote_data['bid_price'] > 0:
        print(f"   ✅ BID PRICE WORKING: ${quote_data['bid_price']}")
    else:
        print(f"   ⚠️  No bid_price in data")
        
    if 'ask_price' in quote_data and quote_data['ask_price'] > 0:
        print(f"   ✅ ASK PRICE WORKING: ${quote_data['ask_price']}")
    else:
        print(f"   ⚠️  No ask_price in data")
else:
    print(f"   ❌ No callbacks received")
    print(f"   This means IB isn't sending tick data")
    print(f"   Possible reasons:")
    print(f"      - Subscription not fully activated yet (wait 15-30 min)")
    print(f"      - Need to restart IB Gateway")
    print(f"      - Market data permissions issue")

# Cleanup
adapter.client.cancelMktData(req_id)
adapter.disconnect()

print("\n" + "="*80)
print("Diagnostic complete")
print("="*80)
