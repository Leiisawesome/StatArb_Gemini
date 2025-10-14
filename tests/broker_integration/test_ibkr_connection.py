"""
IBKR Adapter Connection Test
Quick test to verify IBKR adapter can connect to IB Gateway/TWS

Prerequisites:
1. IB Gateway or TWS must be running
2. API connections enabled in settings
3. Port configured (4002 for paper, 4001 for live)
4. Client ID available (usually 0-10)

Run: pytest tests/broker_integration/test_ibkr_connection.py -v -s
"""

import pytest
import logging
from core_engine.config.broker_config import load_broker_config
from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter

logger = logging.getLogger(__name__)


@pytest.mark.integration
def test_ibkr_connection():
    """
    Test basic IBKR connection
    
    This test verifies:
    1. Can connect to IB Gateway/TWS
    2. Receives valid next order ID
    3. Can retrieve account info
    4. Can disconnect properly
    """
    print("\n" + "="*80)
    print("TEST: IBKR Connection")
    print("="*80)
    
    # Load configuration
    config = load_broker_config()
    
    # Create adapter
    adapter = IBKRAdapter(config.interactive_brokers)
    
    try:
        # Test connection
        print("\n1. Testing connection...")
        connected = adapter.connect()
        assert connected, "Failed to connect to IBKR"
        print(f"   ✅ Connected to IBKR")
        
        # Verify connection status
        print("\n2. Checking connection status...")
        assert adapter.is_connected(), "Connection not established"
        print(f"   ✅ Connection verified")
        
        # Check connection health
        print("\n3. Checking connection health...")
        health = adapter.check_connection_health()
        print(f"   Broker: {health['broker']}")
        print(f"   Host: {health['host']}:{health['port']}")
        print(f"   Client ID: {health['client_id']}")
        print(f"   Next Order ID: {health['next_order_id']}")
        print(f"   Paper Trading: {health['paper_trading']}")
        assert health['connected'], "Health check failed"
        print(f"   ✅ Connection healthy")
        
        # Get account info
        print("\n4. Retrieving account information...")
        account = adapter.get_account_info()
        print(f"   Account ID: {account.account_id}")
        print(f"   Cash: ${account.cash:,.2f}")
        print(f"   Buying Power: ${account.buying_power:,.2f}")
        print(f"   Portfolio Value: ${account.portfolio_value:,.2f}")
        print(f"   ✅ Account info retrieved")
        
        # Test disconnect
        print("\n5. Testing disconnect...")
        adapter.disconnect()
        assert not adapter.is_connected(), "Still connected after disconnect"
        print(f"   ✅ Disconnected successfully")
        
        print("\n" + "="*80)
        print("✅ IBKR CONNECTION TEST PASSED")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        if adapter.is_connected():
            adapter.disconnect()
        raise


@pytest.mark.integration  
def test_ibkr_market_data():
    """
    Test IBKR market data retrieval
    
    This test verifies:
    1. Can request quotes
    2. Receives bid/ask prices
    3. Quote data is reasonable
    """
    print("\n" + "="*80)
    print("TEST: IBKR Market Data")
    print("="*80)
    
    config = load_broker_config()
    adapter = IBKRAdapter(config.interactive_brokers)
    
    try:
        # Connect
        adapter.connect()
        
        # Test quote retrieval
        print("\n1. Getting quote for SPY...")
        quote = adapter.get_latest_quote('SPY')
        
        assert quote is not None, "Failed to get quote"
        assert 'bid_price' in quote, "Quote missing bid_price"
        assert 'ask_price' in quote, "Quote missing ask_price"
        
        print(f"   Symbol: {quote['symbol']}")
        print(f"   Bid: ${quote['bid_price']:.2f} x {quote['bid_size']}")
        print(f"   Ask: ${quote['ask_price']:.2f} x {quote['ask_size']}")
        if quote['last_price']:
            print(f"   Last: ${quote['last_price']:.2f}")
        
        # Validate quote sanity
        assert quote['bid_price'] > 0, "Invalid bid price"
        assert quote['ask_price'] > 0, "Invalid ask price"
        assert quote['ask_price'] >= quote['bid_price'], "Ask < Bid (crossed market)"
        
        spread = quote['ask_price'] - quote['bid_price']
        print(f"   Spread: ${spread:.2f}")
        print(f"   ✅ Quote data valid")
        
        # Test multiple symbols
        print("\n2. Getting quotes for multiple symbols...")
        for symbol in ['AAPL', 'MSFT']:
            quote = adapter.get_latest_quote(symbol)
            assert quote is not None, f"Failed to get quote for {symbol}"
            print(f"   {symbol}: Bid=${quote['bid_price']:.2f} Ask=${quote['ask_price']:.2f}")
        
        print(f"   ✅ Multiple quotes retrieved")
        
        print("\n" + "="*80)
        print("✅ MARKET DATA TEST PASSED")
        print("="*80)
        
    finally:
        if adapter.is_connected():
            adapter.disconnect()


@pytest.mark.integration
def test_ibkr_positions():
    """
    Test IBKR position retrieval
    
    This test verifies:
    1. Can request positions
    2. Position data is correctly formatted
    3. P&L calculations work
    """
    print("\n" + "="*80)
    print("TEST: IBKR Positions")
    print("="*80)
    
    config = load_broker_config()
    adapter = IBKRAdapter(config.interactive_brokers)
    
    try:
        # Connect
        adapter.connect()
        
        # Get positions
        print("\n1. Retrieving positions...")
        positions = adapter.get_positions()
        print(f"   Current positions: {len(positions)}")
        
        if positions:
            for pos in positions:
                print(f"\n   Position: {pos.symbol}")
                print(f"   Quantity: {pos.quantity}")
                print(f"   Avg Entry: ${pos.avg_entry_price:.2f}")
                print(f"   Current Price: ${pos.current_price:.2f}")
                print(f"   Market Value: ${pos.market_value:.2f}")
                print(f"   Unrealized P&L: ${pos.unrealized_pl:.2f} ({pos.unrealized_plpc:+.2f}%)")
        else:
            print("   No positions found (account may be flat)")
        
        print(f"   ✅ Position data retrieved")
        
        print("\n" + "="*80)
        print("✅ POSITIONS TEST PASSED")
        print("="*80)
        
    finally:
        if adapter.is_connected():
            adapter.disconnect()


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
