# Broker Integration Week 1: Days 3-5 - Order Management & Position Tracking

**Date**: October 13-15, 2025  
**Status**: 🚀 READY TO START  
**Focus**: Order submission, tracking, and position management

---

## 📋 Objectives

### Day 3: Market Orders
- [ ] Submit market buy orders
- [ ] Submit market sell orders
- [ ] Validate order execution
- [ ] Monitor order fills

### Day 4: Limit Orders & Order Management
- [ ] Submit limit orders
- [ ] Track order status changes
- [ ] Cancel pending orders
- [ ] Handle order rejections

### Day 5: Position Tracking & P&L
- [ ] Monitor open positions
- [ ] Calculate unrealized P&L
- [ ] Close positions
- [ ] Track portfolio value

---

## ✅ Prerequisites Complete

Before starting Days 3-5, ensure:
- ✅ Configuration test passing
- ✅ Connection test passing
- ✅ Error handling test passing
- ✅ Alpaca account connected ($100K paper money)
- ✅ All safety limits configured

---

## 🔧 Day 3 Tasks: Market Order Submission

### Overview
Market orders execute immediately at the current market price. This is the simplest order type and perfect for testing basic trading functionality.

### Test Objectives
1. Submit a small market BUY order
2. Wait for order to fill
3. Verify position was created
4. Submit a market SELL order to close
5. Verify position was closed

### Safety Limits
- ✅ Maximum position: $100 (100 shares @ ~$1)
- ✅ Test with low-priced stocks only
- ✅ Immediate close after buy
- ✅ Paper trading only

### Implementation Plan

**File**: `tests/broker_integration/orders/test_market_orders.py`

```python
"""
Broker Integration: Market Order Testing

Tests:
- Market buy order submission
- Order fill confirmation
- Market sell order submission
- Position verification
"""
import sys
from pathlib import Path
import time

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter
from core_engine.config.broker_config import load_broker_config


def test_market_orders():
    """Test market order submission and execution"""
    print("=" * 60)
    print("Broker Integration: Market Order Test")
    print("=" * 60)
    
    try:
        # Load configuration
        print("\n⏳ Loading configuration...")
        config = load_broker_config()
        
        # Create adapter
        print("⏳ Connecting to Alpaca...")
        adapter = AlpacaAdapter(config.alpaca)
        adapter.connect()
        
        # Get initial account state
        print("\n💼 Initial Account State:")
        account = adapter.get_account_info()
        print(f"   Cash: ${account.cash:,.2f}")
        print(f"   Buying Power: ${account.buying_power:,.2f}")
        
        # Define test symbol (use a cheap, liquid stock)
        test_symbol = "SPY"  # S&P 500 ETF - highly liquid
        test_qty = 1  # Single share for testing
        
        print(f"\n📈 Test Parameters:")
        print(f"   Symbol: {test_symbol}")
        print(f"   Quantity: {test_qty} share")
        print(f"   Order Type: Market")
        
        # Submit BUY order
        print(f"\n🛒 Submitting MARKET BUY order...")
        buy_order = adapter.submit_market_order(
            symbol=test_symbol,
            qty=test_qty,
            side="buy",
            time_in_force="day"
        )
        
        if buy_order:
            print(f"   ✅ Order submitted!")
            print(f"   Order ID: {buy_order.order_id}")
            print(f"   Symbol: {buy_order.symbol}")
            print(f"   Quantity: {buy_order.qty}")
            print(f"   Side: {buy_order.side}")
            print(f"   Status: {buy_order.status}")
        else:
            print("   ❌ Order submission failed!")
            return False
        
        # Wait for order to fill
        print("\n⏳ Waiting for order to fill...")
        max_wait = 30  # seconds
        wait_interval = 2  # seconds
        elapsed = 0
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            order_status = adapter.get_order(buy_order.order_id)
            print(f"   Status after {elapsed}s: {order_status.status}")
            
            if order_status.status in ["filled", "partially_filled"]:
                print(f"   ✅ Order filled!")
                if order_status.filled_price:
                    print(f"   Fill Price: ${order_status.filled_price:.2f}")
                break
            elif order_status.status in ["rejected", "canceled", "expired"]:
                print(f"   ❌ Order {order_status.status}!")
                return False
        
        # Verify position was created
        print("\n📊 Checking positions...")
        positions = adapter.get_positions()
        
        position_found = False
        for pos in positions:
            if pos.symbol == test_symbol:
                position_found = True
                print(f"   ✅ Position found!")
                print(f"   Symbol: {pos.symbol}")
                print(f"   Quantity: {pos.quantity}")
                print(f"   Entry Price: ${pos.entry_price:.2f}")
                print(f"   Current Price: ${pos.current_price:.2f}")
                print(f"   Unrealized P&L: ${pos.unrealized_pnl:.2f}")
                break
        
        if not position_found:
            print(f"   ⚠️  Position not found (may still be settling)")
        
        # Submit SELL order to close position
        print(f"\n🔻 Submitting MARKET SELL order to close position...")
        sell_order = adapter.submit_market_order(
            symbol=test_symbol,
            qty=test_qty,
            side="sell",
            time_in_force="day"
        )
        
        if sell_order:
            print(f"   ✅ Sell order submitted!")
            print(f"   Order ID: {sell_order.order_id}")
            print(f"   Status: {sell_order.status}")
        else:
            print("   ❌ Sell order submission failed!")
            return False
        
        # Wait for sell order to fill
        print("\n⏳ Waiting for sell order to fill...")
        elapsed = 0
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            order_status = adapter.get_order(sell_order.order_id)
            print(f"   Status after {elapsed}s: {order_status.status}")
            
            if order_status.status in ["filled", "partially_filled"]:
                print(f"   ✅ Sell order filled!")
                if order_status.filled_price:
                    print(f"   Fill Price: ${order_status.filled_price:.2f}")
                break
            elif order_status.status in ["rejected", "canceled", "expired"]:
                print(f"   ❌ Sell order {order_status.status}!")
                return False
        
        # Verify position was closed
        print("\n📊 Verifying position closed...")
        positions = adapter.get_positions()
        
        position_closed = True
        for pos in positions:
            if pos.symbol == test_symbol:
                position_closed = False
                print(f"   ⚠️  Position still open: {pos.quantity} shares")
                break
        
        if position_closed:
            print(f"   ✅ Position closed successfully!")
        
        # Get final account state
        print("\n💼 Final Account State:")
        account = adapter.get_account_info()
        print(f"   Cash: ${account.cash:,.2f}")
        print(f"   Buying Power: ${account.buying_power:,.2f}")
        
        # Disconnect
        adapter.disconnect()
        
        print("\n" + "=" * 60)
        print("✅ Market Order Test: SUCCESS")
        print("=" * 60)
        print("\n📝 Next Steps:")
        print("   1. Review order fills on Alpaca dashboard")
        print("   2. Proceed to Day 4: Limit orders")
        print("   3. Run: python tests/broker_integration/orders/test_limit_orders.py")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   {str(e)}")
        
        import traceback
        print("\n🔍 Full traceback:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_market_orders()
    sys.exit(0 if success else 1)
```

### Expected Output

```
============================================================
Broker Integration: Market Order Test
============================================================

💼 Initial Account State:
   Cash: $100,000.00
   Buying Power: $200,000.00

📈 Test Parameters:
   Symbol: SPY
   Quantity: 1 share
   Order Type: Market

🛒 Submitting MARKET BUY order...
   ✅ Order submitted!
   Order ID: xxx-xxx-xxx
   Symbol: SPY
   Quantity: 1
   Side: buy
   Status: new

⏳ Waiting for order to fill...
   Status after 2s: filled
   ✅ Order filled!
   Fill Price: $450.25

📊 Checking positions...
   ✅ Position found!
   Symbol: SPY
   Quantity: 1
   Entry Price: $450.25
   Current Price: $450.30
   Unrealized P&L: $0.05

🔻 Submitting MARKET SELL order to close position...
   ✅ Sell order submitted!

⏳ Waiting for sell order to fill...
   Status after 2s: filled
   ✅ Sell order filled!
   Fill Price: $450.30

📊 Verifying position closed...
   ✅ Position closed successfully!

💼 Final Account State:
   Cash: $100,000.05
   Buying Power: $200,000.05

============================================================
✅ Market Order Test: SUCCESS
============================================================
```

---

## 🔧 Day 4 Tasks: Limit Orders & Order Management

### Overview
Limit orders allow you to specify a maximum buy price or minimum sell price. They may not fill immediately, allowing testing of order management features.

### Test Objectives
1. Submit a limit BUY order (below market)
2. Track order status
3. Cancel the pending order
4. Submit a limit order (at market)
5. Wait for fill and verify

### Implementation Plan

**File**: `tests/broker_integration/orders/test_limit_orders.py`

```python
"""
Broker Integration: Limit Order Testing

Tests:
- Limit buy order submission
- Order status tracking
- Order cancellation
- Limit order execution
"""
```

### Key Features to Test
- Limit price validation
- Order pending status
- Order cancellation
- Fill at limit price or better
- Partial fills (if applicable)

---

## 🔧 Day 5 Tasks: Position Management

### Overview
Position tracking is critical for monitoring your portfolio's health, calculating P&L, and managing risk.

### Test Objectives
1. Open a position (market order)
2. Monitor position in real-time
3. Calculate unrealized P&L
4. Monitor portfolio value
5. Close position and lock in P&L

### Implementation Plan

**File**: `tests/broker_integration/positions/test_position_tracking.py`

```python
"""
Broker Integration: Position Tracking Test

Tests:
- Position monitoring
- Unrealized P&L calculation
- Portfolio value tracking
- Position closing
- Realized P&L verification
"""
```

### Key Metrics to Track
- Entry price vs. current price
- Unrealized P&L
- Realized P&L after close
- Position size
- Portfolio total value
- Buying power changes

---

## 📊 Test Directory Structure

Create organized test structure:

```
tests/broker_integration/
├── __init__.py
├── README.md
├── test_broker_config_loading.py
├── test_alpaca_connection.py
├── test_connection_error_handling.py
├── orders/
│   ├── __init__.py
│   ├── test_market_orders.py          # Day 3
│   ├── test_limit_orders.py           # Day 4
│   └── test_order_cancellation.py     # Day 4
└── positions/
    ├── __init__.py
    ├── test_position_tracking.py      # Day 5
    └── test_pnl_calculation.py        # Day 5
```

---

## 🔒 Safety Checklist

Before running order tests:

- [ ] Paper trading mode confirmed
- [ ] Position limits configured ($1,000 max)
- [ ] Daily trade limit set (10 trades max)
- [ ] Using liquid, low-priced stocks
- [ ] Test with small quantities (1-2 shares)
- [ ] Always close positions after testing
- [ ] Monitor Alpaca dashboard during tests

---

## 🆘 Troubleshooting

### "Order rejected"
**Possible causes**:
- Insufficient buying power
- Market closed (9:30 AM - 4:00 PM ET)
- Symbol not found
- Invalid order parameters

### "Order not filling"
**Solutions**:
- Use market orders for immediate fills
- Check if market is open
- Verify symbol is actively trading
- Check for Alpaca API issues

### "Position not found after fill"
**Solution**:
- Wait a few seconds for settlement
- Refresh position list
- Check order status first

---

## 📝 Progress Tracking

### Day 3: Market Orders
- [ ] Create orders subdirectory
- [ ] Implement test_market_orders.py
- [ ] Run test successfully
- [ ] Verify on Alpaca dashboard

### Day 4: Limit Orders
- [ ] Implement test_limit_orders.py
- [ ] Implement test_order_cancellation.py
- [ ] Run tests successfully
- [ ] Document findings

### Day 5: Position Management
- [ ] Create positions subdirectory
- [ ] Implement test_position_tracking.py
- [ ] Implement test_pnl_calculation.py
- [ ] Run tests successfully
- [ ] Verify P&L calculations

---

## 🎯 Success Criteria

Week 1 is complete when:

✅ All configuration tests passing  
✅ All connection tests passing  
✅ Market orders submit and fill correctly  
✅ Limit orders can be placed and canceled  
✅ Positions tracked accurately  
✅ P&L calculated correctly  
✅ All positions closed (no overnight holds)  
✅ Account balance verified  

---

## 📚 Resources

### Alpaca Order Types
- **Market**: Executes immediately at current price
- **Limit**: Executes at specified price or better
- **Stop**: Triggers market order at stop price
- **Stop-Limit**: Triggers limit order at stop price

### Time In Force
- **day**: Valid until market close
- **gtc**: Good 'til canceled
- **ioc**: Immediate or cancel
- **fok**: Fill or kill

### Position States
- **Open**: Position currently held
- **Closing**: Sell order submitted
- **Closed**: Position fully exited

---

## 🚀 Getting Started

Ready to begin Day 3? Run:

```bash
# Create test directories
mkdir -p tests/broker_integration/orders
mkdir -p tests/broker_integration/positions

# Create init files
touch tests/broker_integration/orders/__init__.py
touch tests/broker_integration/positions/__init__.py

# Copy the test template above and start testing!
```

---

**Document Version**: 1.0  
**Last Updated**: October 13, 2025  
**Status**: Ready for Days 3-5 Implementation 🚀
