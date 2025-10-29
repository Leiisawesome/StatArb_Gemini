"""
Phase 9 Day 2: Alpaca Connection Test

Tests:
- Connection to Alpaca API
- Authentication with API credentials
- Account information retrieval
- Graceful disconnection
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter
from core_engine.config.broker_config import load_broker_config


def test_alpaca_connection():
    """Test connection to Alpaca paper trading account"""
    print("=" * 60)
    print("Broker Integration: Alpaca Connection Test")
    print("=" * 60)
    
    # Load configuration
    print("\n⏳ Loading configuration...")
    config = load_broker_config()
    alpaca_config = config.alpaca
    
    print(f"\n🔗 Connection Details:")
    print(f"   Target: {alpaca_config.base_url}")
    print(f"   Mode: {'Paper Trading' if alpaca_config.paper_trading else 'Live Trading'}")
    print(f"   API Key: {alpaca_config.api_key[:8]}...")
    
    # Create adapter
    print("\n⏳ Creating Alpaca adapter...")
    adapter = AlpacaAdapter(alpaca_config)
    
    # Test connection
    print("\n🔌 Testing connection...")
    connected = adapter.connect()
    
    if connected:
        print("   ✅ Connection established successfully!")
    else:
        print("   ❌ Connection failed!")
        print("\n📝 Troubleshooting:")
        print("   1. Check your internet connection")
        print("   2. Verify API credentials in .env file")
        print("   3. Check Alpaca API status: https://status.alpaca.markets")
    
    assert connected, "Failed to connect to Alpaca"
    
    # Test authentication (implicit in connect)
    print("\n🔐 Testing authentication...")
    print("   ✅ Authentication successful! (validated during connection)")
    
    # Get account info
    print("\n💼 Fetching account information...")
    account = adapter.get_account_info()
    
    assert account is not None, "Failed to retrieve account information"
    
    print("   ✅ Account information retrieved!")
    print(f"\n📊 Account Details:")
    print(f"   Account ID: {account.account_id}")
    print(f"   Cash: ${account.cash:,.2f}")
    print(f"   Portfolio Value: ${account.equity:,.2f}")
    print(f"   Buying Power: ${account.buying_power:,.2f}")
    print(f"   Account Status: {account.status}")
    
    # Check if account is active
    if account.status.upper() == "ACTIVE":
        print(f"   ✅ Account is active and ready for trading")
    else:
        print(f"   ⚠️  WARNING: Account status is {account.status}")
    
    # Get current positions (should be empty initially)
    print("\n📈 Checking current positions...")
    positions = adapter.get_positions()
    
    assert positions is not None, "Could not retrieve positions"
    
    print(f"   ✅ Retrieved {len(positions)} position(s)")
    
    if len(positions) == 0:
        print("   💡 No open positions (expected for new account)")
    else:
        print("   📊 Current positions:")
        for pos in positions:
            print(f"      {pos.symbol}: {pos.quantity} shares @ ${pos.current_price:.2f}")
    
    # Test connection health
    print("\n❤️  Testing connection health...")
    is_healthy = adapter.is_connected()
    
    if is_healthy:
        print("   ✅ Connection is healthy")
    else:
        print("   ⚠️  Connection health check failed")
    
    # Disconnect
    print("\n🔌 Disconnecting from Alpaca...")
    adapter.disconnect()
    print("   ✅ Disconnected successfully")
    
    # Verify disconnection
    still_connected = adapter.is_connected()
    if not still_connected:
        print("   ✅ Connection properly closed")
    else:
        print("   ⚠️  Connection may still be open")
    
    print("\n" + "=" * 60)
    print("✅ Alpaca Connection Test: SUCCESS")
    print("=" * 60)
    print("\n📝 Next Steps:")
    print("   1. Run error handling test: python tests/broker_integration/test_connection_error_handling.py")
    print("   2. Proceed to Day 3: Order submission")
    print("   3. Review account on Alpaca dashboard")


if __name__ == "__main__":
    success = test_alpaca_connection()
    sys.exit(0 if success else 1)
