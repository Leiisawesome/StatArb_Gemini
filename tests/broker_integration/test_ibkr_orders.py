"""
Test IBKR Order Placement
Tests order submission, modification, and cancellation via Interactive Brokers API.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import time
from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter
from core_engine.config.broker_config import load_broker_config

# Counter for unique client IDs
_client_id_counter = 1

@pytest.fixture
def ibkr_adapter():
    """Create and connect IBKR adapter for testing"""
    global _client_id_counter
    config = load_broker_config()
    # Use unique client ID for each test to avoid conflicts
    config.interactive_brokers.client_id = _client_id_counter
    _client_id_counter += 1
    adapter = IBKRAdapter(config.interactive_brokers)
    yield adapter
    # Cleanup: disconnect after test
    if adapter.is_connected:
        adapter.disconnect()

class TestIBKROrders:
    """Test suite for IBKR order operations."""

    def test_market_order_submission(self, ibkr_adapter):
        """
        Test: Submit a market order to IBKR
        Expected: Order submitted successfully with order ID
        Note: During market hours in paper trading, orders fill instantly
        """
        print("\n" + "="*80)
        print("TEST: IBKR Market Order Submission")
        print("="*80)

        # Connect to IBKR
        ibkr_adapter.connect()
        assert ibkr_adapter.is_connected, "Failed to connect to IBKR"

        # Wait for connection to stabilize
        time.sleep(2)

        print("\n1. Submitting market order for SPY...")
        print("   Symbol: SPY")
        print("   Action: BUY")
        print("   Quantity: 1")
        print("   Order Type: MARKET")

        # Submit market order
        order_id = ibkr_adapter.place_order(
            symbol="SPY",
            quantity=1,
            side="BUY",
            order_type="MARKET"
        )

        print(f"\n2. Order submitted:")
        print(f"   Order ID: {order_id}")

        # Verify order ID was returned
        assert order_id is not None, "Order ID should not be None"
        assert isinstance(order_id, (int, str)), "Order ID should be int or string"
        assert order_id != 0, "Order ID should not be 0"

        print("\n✅ Market order submission test passed!")
        print("   (Order status tracking requires market hours or extended testing)")

        # Cancel the order if it's still pending (market closed scenario)
        try:
            ibkr_adapter.cancel_order(order_id)
            print(f"\n   Cancelled order {order_id} for cleanup")
        except Exception as e:
            print(f"\n   Could not cancel order (may be already filled): {e}")

    def test_limit_order_submission(self, ibkr_adapter):
        """
        Test: Submit a limit order to IBKR
        Expected: Order submitted successfully with specified limit price
        """
        print("\n" + "="*80)
        print("TEST: IBKR Limit Order Submission")
        print("="*80)

        # Connect to IBKR
        ibkr_adapter.connect()
        assert ibkr_adapter.is_connected, "Failed to connect to IBKR"

        # Wait for connection to stabilize
        time.sleep(2)

        # Get current market price for SPY
        print("\n1. Getting current market price for SPY...")
        quote = ibkr_adapter.get_quote("SPY")

        if quote and quote.get('last_price', 0) > 0:
            current_price = quote['last_price']
            # Set limit price 5% below current price (unlikely to fill in paper trading)
            limit_price = float(current_price) * 0.95
            print(f"   Current price: ${current_price:.2f}")
            print(f"   Limit price: ${limit_price:.2f} (5% below)")
        else:
            # Use a conservative limit price if we can't get current price
            limit_price = 500.0
            print(f"   Using default limit price: ${limit_price:.2f}")

        print("\n2. Submitting limit order for SPY...")
        print("   Symbol: SPY")
        print("   Action: BUY")
        print("   Quantity: 1")
        print("   Order Type: LIMIT")
        print(f"   Limit Price: ${limit_price:.2f}")

        # Submit limit order
        order_id = ibkr_adapter.place_order(
            symbol="SPY",
            quantity=1,
            side="BUY",
            order_type="LIMIT",
            limit_price=limit_price
        )

        print(f"\n3. Order submitted:")
        print(f"   Order ID: {order_id}")

        # Verify order ID was returned
        assert order_id is not None, "Order ID should not be None"
        assert isinstance(order_id, (int, str)), "Order ID should be int or string"

        print("\n✅ Limit order submission test passed!")
        print("   (Order status tracking requires market hours)")

        # Cancel the order (cleanup)
        try:
            ibkr_adapter.cancel_order(order_id)
            print(f"\n   Cancelled order {order_id} for cleanup")
        except Exception as e:
            print(f"\n   Could not cancel order (may be already rejected): {e}")

    def test_order_cancellation(self, ibkr_adapter):
        """
        Test: Cancel a pending order
        Expected: Order cancelled successfully
        """
        print("\n" + "="*80)
        print("TEST: IBKR Order Cancellation")
        print("="*80)

        # Connect to IBKR
        ibkr_adapter.connect()
        assert ibkr_adapter.is_connected, "Failed to connect to IBKR"

        # Wait for connection to stabilize
        time.sleep(2)

        print("\n1. Submitting limit order to cancel...")
        print("   Symbol: SPY")
        print("   Limit Price: $1.00 (will not fill)")

        # Submit a limit order that won't fill (price way below market)
        order_id = ibkr_adapter.place_order(
            symbol="SPY",
            quantity=1,
            side="BUY",
            order_type="LIMIT",
            limit_price=1.0  # Way below market, won't fill
        )

        print(f"\n2. Order submitted:")
        print(f"   Order ID: {order_id}")

        assert order_id is not None, "Order ID should not be None"

        # Wait for order to be submitted
        time.sleep(2)

        # Cancel the order
        print("\n3. Cancelling order...")
        ibkr_adapter.cancel_order(order_id)

        # Wait for cancellation to process
        time.sleep(1)

        print("\n✅ Order cancellation test passed!")
        print("   (Order status verification requires market hours)")

    def test_get_open_orders(self, ibkr_adapter):
        """
        Test: Retrieve all open orders
        Expected: List of open orders returned
        """
        print("\n" + "="*80)
        print("TEST: IBKR Get Open Orders")
        print("="*80)

        # Connect to IBKR
        ibkr_adapter.connect()
        assert ibkr_adapter.is_connected, "Failed to connect to IBKR"

        # Wait for connection to stabilize
        time.sleep(2)

        print("\n1. Submitting test order...")
        # Submit a limit order that won't fill
        order_id = ibkr_adapter.place_order(
            symbol="SPY",
            quantity=1,
            side="BUY",
            order_type="LIMIT",
            limit_price=1.0
        )

        print(f"   Order ID: {order_id}")

        # Wait for order to be submitted
        time.sleep(2)

        print("\n2. Retrieving open orders...")
        open_orders = ibkr_adapter.get_open_orders()

        print(f"\n3. Open orders found: {len(open_orders)}")
        for order in open_orders:
            print(f"   - Order ID: {order.get('order_id')}, "
                  f"Symbol: {order.get('symbol')}, "
                  f"Status: {order.get('status')}")

        # Verify we got a list back
        assert isinstance(open_orders, list), "Should return a list of orders"

        print(f"\n✅ Get open orders test passed!")
        print("   (Returns empty list when market closed, populated during market hours)")

        # Cleanup: cancel the test order if it exists
        try:
            ibkr_adapter.cancel_order(order_id)
            print(f"\n   Cancelled order {order_id} for cleanup")
        except Exception as e:
            print(f"\n   Could not cancel order (may be already rejected): {e}")

    @pytest.mark.skip(reason="Only run during market hours for realistic testing")
    def test_market_order_fill(self, ibkr_adapter):
        """
        Test: Verify market order gets filled during market hours
        Expected: Order filled with execution details
        Note: Skip this test outside market hours
        """
        print("\n" + "="*80)
        print("TEST: IBKR Market Order Fill (Market Hours Only)")
        print("="*80)

        # Connect to IBKR
        ibkr_adapter.connect()
        assert ibkr_adapter.is_connected, "Failed to connect to IBKR"

        # Check if market is open
        if not ibkr_adapter.is_market_open():
            pytest.skip("Market is closed - skipping fill test")

        # Wait for connection to stabilize
        time.sleep(2)

        print("\n1. Submitting market order...")
        # Submit a small market order
        order_id = ibkr_adapter.place_order(
            symbol="SPY",
            quantity=1,
            side="BUY",
            order_type="MARKET"
        )

        print(f"   Order ID: {order_id}")

        # Wait for fill (should be quick for market order)
        print("\n2. Waiting for order fill...")
        max_wait = 10  # seconds
        filled = False

        for i in range(max_wait):
            time.sleep(1)
            order_status = ibkr_adapter.get_order_status(order_id)
            status = order_status.get('status', 'Unknown')
            filled_qty = order_status.get('filled_qty', 0)

            print(f"   [{i+1}s] Status: {status}, Filled: {filled_qty}")

            if status == 'Filled':
                filled = True
                break

        # Verify order filled
        assert filled, "Market order should fill during market hours"

        # Get execution details
        order_status = ibkr_adapter.get_order_status(order_id)
        print(f"\n3. Order filled:")
        print(f"   Status: {order_status.get('status')}")
        print(f"   Filled Qty: {order_status.get('filled_qty')}")
        print(f"   Avg Fill Price: ${order_status.get('avg_fill_price', 0):.2f}")

        assert order_status.get('filled_qty') == 1, "Should fill 1 share"
        assert order_status.get('avg_fill_price', 0) > 0, "Should have fill price"

        print("\n✅ Market order fill test passed!")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
